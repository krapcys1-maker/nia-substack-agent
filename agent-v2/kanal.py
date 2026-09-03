"""Kanal czytelnika — jedyne zrodlo celow do komentowania.

Osobny plik, bo to jest CZYTANIE CUDZYCH tresci przez zalogowana sesje, a nie
publikowanie: browser.py rosl juz do tysiaca linii i mieszanie w nim odczytu
z dzialaniem utrudnialo czytanie obu.
"""

from __future__ import annotations

from typing import Any

import browser
import config

HISTORIA_KOMENTARZY = config.DATA_DIR / "gdzie_komentowalismy.json"


def _historia() -> dict:
    import json

    if not HISTORIA_KOMENTARZY.exists():
        return {}
    try:
        return json.loads(HISTORIA_KOMENTARZY.read_text(encoding="utf-8"))
    except ValueError:
        return {}


def zapamietaj_komentarz(post: dict) -> None:
    """Odnotowuje, u kogo dzis komentowalismy."""
    import json
    from datetime import datetime, timezone

    h = _historia()
    h[klucz_publikacji(post)] = datetime.now(timezone.utc).isoformat()
    HISTORIA_KOMENTARZY.parent.mkdir(parents=True, exist_ok=True)
    HISTORIA_KOMENTARZY.write_text(json.dumps(h, ensure_ascii=False, indent=1),
                                   encoding="utf-8")


def klucz_publikacji(post: dict) -> str:
    """Kim jest autor posta. Z ADRESU, bo nazwa publikacji bywa pusta w kanale."""
    from urllib.parse import urlparse

    return urlparse(post.get("url") or "").netloc or (post.get("pub") or "?")


def _wiek_minut(data: str) -> float:
    from datetime import datetime, timezone

    try:
        kiedy = datetime.fromisoformat(str(data).replace("Z", "+00:00"))
    except ValueError:
        return 1e9        # nieznana data = traktujemy jak stary, nie blokujemy
    return (datetime.now(timezone.utc) - kiedy).total_seconds() / 60


def _za_swiezy(post: dict, widelki: tuple[int, int] | None = None) -> bool:
    """Czy post jest na tyle swiezy, ze komentarz wygladalby jak czujka bota.

    Widelki sa ROZNE dla artykulu i dla notki, bo te dwie rzeczy zyja w innym
    tempie. Artykul czyta sie tygodniami, notka gasnie tego samego dnia.
    """
    import random

    prog = random.uniform(*(widelki or config.MIN_WIEK_POSTA_MIN))
    return _wiek_minut(post.get("data", "")) < prog


def wartosc_celu(x: dict) -> tuple:
    """Klucz sortowania celow: WCZESNIE przed GLOSNO.

    Sortowalismy malejaco po `reakcje * 2 + komentarze * 3`, czyli im wiekszy
    tlok, tym wyzej. Dla konta z kilkoma czytelnikami to jest odwrotnie, niz
    trzeba: pod tekstem ze 126 komentarzami nasza uwaga nie zostanie przeczytana
    przez nikogo, a caly koszt jej napisania i tak ponosimy.

    Wiec najpierw teksty, ktore maja ZYWA PUBLICZNOSC, ale jeszcze malo
    komentarzy — tam da sie byc jednym z pierwszych glosow. Zatloczone zostaja
    na koncu, jako uzupelnienie, a nie jako pierwszy wybor.
    """
    kom = int(x.get("komentarze") or 0)
    rea = int(x.get("reakcje") or 0)
    jest_tlok = kom > config.KOMFORTOWO_KOMENTARZY
    # W grupie „jeszcze jest miejsce" wygrywa najzywsza publicznosc.
    # W grupie „tlok" wygrywa ten, gdzie tloku najmniej.
    return (1 if jest_tlok else 0, kom if jest_tlok else -rea)


def _za_niedawno_u_nich(post: dict) -> bool:
    """Czy komentowalismy u tej publikacji w ostatnich dniach."""
    from datetime import datetime, timedelta, timezone

    ostatnio = _historia().get(klucz_publikacji(post))
    if not ostatnio:
        return False
    try:
        kiedy = datetime.fromisoformat(ostatnio)
    except ValueError:
        return False
    return (datetime.now(timezone.utc) - kiedy) < timedelta(
        days=config.ODSTEP_DNI_NA_PUBLIKACJE)

JS_KANAL = """
() => null
"""


def posty_z_kanalu(ile: int = 25) -> list[dict[str, Any]]:
    """Ostatnie posty z kanalu czytelnika, z liczba komentarzy i reakcji."""
    browser.wymagaj_sesji()
    p, br, ctx = browser.podlacz_sie()
    page = ctx.new_page()
    try:
        dane = browser.api_json(page, "/api/v1/reader/posts") or {}
        posty = []
        odrzucone = {"swieze": 0, "za_czesto": 0}
        for x in (dane.get("posts") or [])[:ile]:
            if not isinstance(x, dict):
                continue
            # NASZE wlasne teksty wypadaja od razu. Kanal czytelnika pokazuje
            # tez nas samych, a wybor celow przy pierwszym uruchomieniu uznal
            # nasz artykul o jajkach za wart skomentowania — agent
            # komentowalby sam siebie.
            adres = x.get("canonical_url") or ""
            if config.SUBSTACK_HANDLE in adres:
                continue
            kandydat = {
                "tytul": (x.get("title") or "")[:120],
                "opis": (x.get("subtitle") or x.get("description") or "")[:300],
                "pub": ((x.get("publication") or {}).get("name") or ""),
                "komentarze": x.get("comment_count") or 0,
                "reakcje": x.get("reaction_count") or 0,
                "url": x.get("canonical_url") or "",
                "data": x.get("post_date") or "",   # pelna, do liczenia wieku
                "skad": "kanal czytelnika",
                "rodzaj": "post",
            }
            # DWA SITA, oba o ZACHOWANIU, nie o tresci.
            if _za_swiezy(kandydat):
                odrzucone["swieze"] += 1
                continue
            if _za_niedawno_u_nich(kandydat):
                odrzucone["za_czesto"] += 1
                continue
            posty.append(kandydat)
        # NOWI LUDZIE NAJPIERW. Cztery dni odstepu chronia przed nachodzeniem
        # tej samej osoby, ale nie robia z nas kogos, kto poznaje nowych.
        # Konto, ktore krazy miedzy pieciona znajomymi nazwiskami, nie rosnie —
        # a wlasnie o nowych ludzi nam chodzi.
        znani = set(_historia())
        posty.sort(key=lambda x: klucz_publikacji(x) in znani)
        nowi = sum(1 for x in posty if klucz_publikacji(x) not in znani)

        print(f"  [kanał] postów: {len(posty)}   nowych autorów: {nowi}"
              f"   odrzucone: {odrzucone['swieze']} za świeżych,"
              f" {odrzucone['za_czesto']} bo niedawno tam komentowaliśmy",
              flush=True)
        return posty
    finally:
        page.close()
        br.close()
        p.stop()


def notki_z_kanalu(ile: int = 25) -> list[dict]:
    """Cudze notki, pod ktorymi mozna wejsc w dyskusje.

    Dla swiezego konta to najwazniejsze miejsce: pod notkami toczy sie rozmowa,
    a kanal Substacka promuje watki, ktore zyja. Komentarz pod artykulem czyta
    kilka osob; sensowna uwaga pod zywa notka trafia do calego jej watku.
    """
    browser.wymagaj_sesji()
    p, br, ctx = browser.podlacz_sie()
    page = ctx.new_page()
    try:
        dane = browser.api_json(page, "/api/v1/reader/feed?tab=for-you&type=base") or {}
        notki = []
        odrzucone = 0
        for x in (dane.get("items") or [])[:ile * 2]:
            c = (x or {}).get("comment") or {}
            if not c.get("body") or c.get("post_id"):
                continue                     # to nie notka, tylko komentarz
            if c.get("handle") == config.SUBSTACK_HANDLE:
                continue                     # nasza wlasna
            kandydat = {
                "id": c.get("id"), "autor": c.get("name") or "",
                "handle": c.get("handle") or "",
                "tekst": (c.get("body") or "")[:1200],
                "reakcje": c.get("reaction_count") or 0,
                "odpowiedzi": c.get("children_count") or 0,
                "data": c.get("date") or "",
                "url": f"https://substack.com/note/c-{c.get('id')}",
                "rodzaj": "notka",
            }
            if _za_swiezy(kandydat, config.MIN_WIEK_NOTKI_MIN):
                odrzucone += 1
                continue
            notki.append(kandydat)
        # Najzywsze najpierw: tam nasza uwaga zostanie przeczytana.
        # Pod notkami liczy sie to samo co pod artykulami: zywa publicznosc,
        # ale jeszcze miejsce, zeby nasza uwaga zostala przeczytana.
        notki.sort(key=lambda n: wartosc_celu(
            {"komentarze": n["odpowiedzi"], "reakcje": n["reakcje"]}))
        print(f"  [notki innych] {len(notki)} do rozwazenia"
              f"   ({odrzucone} odrzuconych jako za swieze)", flush=True)
        return notki[:ile]
    finally:
        page.close()
        br.close()
        p.stop()


def szukaj_nowych(ile: int = 20) -> list[dict]:
    """Szuka NOWYCH kont wyszukiwarka Substacka, poza naszym kregiem.

    Wlasciciel postawil sprawe jasno: agent ma szukac nowych kont, a nie
    komentowac wciaz u tych samych. Kanal czytelnika pokazuje wylacznie to,
    co juz znamy — jedenascie publikacji, ktore same z siebie nikogo nowego nie
    przyprowadza.

    Wyszukiwarka oddaje posty i notki spoza kregu. Filtrujemy je tak samo jak
    kanal: nie swieze, nie u tych, u ktorych niedawno bylismy, nie u nas.
    """
    import random

    browser.wymagaj_sesji()
    hasla = random.sample(list(config.HASLA_SZUKANIA),
                          k=min(config.ILE_HASEL_NA_PRZEBIEG,
                                len(config.HASLA_SZUKANIA)))
    p, br, ctx = browser.podlacz_sie()
    page = ctx.new_page()
    znalezione: dict[str, dict] = {}
    odrzucone = {"swieze": 0, "za_czesto": 0, "nasze": 0}
    try:
        for haslo in hasla:
            dane = browser.api_json(
                page, "/api/v1/top/search?query="
                      + haslo.replace(" ", "+") + "&fromSuggestedSearch=false") or {}
            for x in (dane.get("items") or []):
                post = (x or {}).get("post") or {}
                kom = (x or {}).get("comment") or {}
                pub = (x or {}).get("publication") or {}
                if post.get("title") and post.get("canonical_url"):
                    kandydat = {
                        "tytul": post.get("title", "")[:120],
                        "opis": (post.get("subtitle") or post.get("description") or "")[:300],
                        "pub": pub.get("name") or pub.get("subdomain") or "",
                        "komentarze": post.get("comment_count") or 0,
                        "reakcje": post.get("reaction_count") or 0,
                        "url": post.get("canonical_url"),
                        "data": post.get("post_date") or "",
                        "skad": f"szukanie: {haslo}",
                        "rodzaj": "post",
                    }
                elif kom.get("body") and not kom.get("post_id"):
                    kandydat = {
                        "tytul": (kom.get("body") or "")[:120],
                        "opis": (kom.get("body") or "")[:600],
                        "pub": kom.get("name") or kom.get("handle") or "",
                        "komentarze": kom.get("children_count") or 0,
                        "reakcje": kom.get("reaction_count") or 0,
                        "url": f"https://substack.com/note/c-{kom.get('id')}",
                        "id": kom.get("id"),
                        "data": kom.get("date") or "",
                        "skad": f"szukanie: {haslo}",
                        "rodzaj": "notka",
                    }
                else:
                    continue

                if config.SUBSTACK_HANDLE in (kandydat["url"] or ""):
                    odrzucone["nasze"] += 1
                    continue
                if _za_swiezy(kandydat,
                              config.MIN_WIEK_NOTKI_MIN
                              if kandydat["rodzaj"] == "notka" else None):
                    odrzucone["swieze"] += 1
                    continue
                if _za_niedawno_u_nich(kandydat):
                    odrzucone["za_czesto"] += 1
                    continue
                znalezione[kandydat["url"]] = kandydat

        wynik = sorted(znalezione.values(), key=wartosc_celu)[:ile]
        print(f"  [szukanie] hasla: {', '.join(hasla)}", flush=True)
        print(f"  [szukanie] nowych celow: {len(wynik)}"
              f"   (odrzucone: {odrzucone['swieze']} świeżych,"
              f" {odrzucone['za_czesto']} znanych, {odrzucone['nasze']} naszych)",
              flush=True)
        return wynik
    finally:
        page.close()
        br.close()
        p.stop()
