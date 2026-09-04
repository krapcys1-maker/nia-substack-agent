"""Tematy z kanalow, ktore robia dokladnie to, co ma robic nasza publikacja.

DLACZEGO TO ZRODLO, A NIE ARXIV. Zbudowalem korpus odkryc naukowych i wlasciciel
odrzucil jego plon jednym zdaniem — tokamak go nie interesuje. Wybral natomiast
z listy kanalow: chip z zywych komorek mozgowych, agenci ustalajacy wlasny
protokol, model bijacy najlepsze, ktorego autora nikt nie zna, Claude ktory
przegral 650 razy i pobil rekord czlowieka.

Roznica nie jest w dziedzinie, tylko w tym, ze kazdy z tych tematow **da sie
opowiedziec komus przy stole**. Praca o rownowadze plazmy nie da sie, choc jest
lepsza nauka. Kanaly z tej dziedziny robia ten dobor od lat i maja na nim
liczniki — wiec
zamiast zgadywac, co jest ciekawe, czytamy, co ONI wybrali.

CZEGO STAD NIE BIERZEMY. Naglowkow. „This Will Change EVERYTHING" obiecuje rzecz,
ktorej nie pokryje zaden dokument, a bramka faktograficzna ja zatrzyma — i dobrze,
bo to jedyna roznica miedzy nami a generatorem hype'u. Bierzemy ZDARZENIE, ktore
za naglowkiem stoi, i sami je sprawdzamy: przez `kod_odpowiada`, przez wlasny
pomiar, przez dokument.

DOSTEP. Kanaly YouTube maja publiczny kanal RSS, ktory NIE przechodzi przez
sciane zgody — a strona kanalu przechodzi i dlatego jej nie uzywamy. RSS oddaje
ostatnie ~15 filmow: tytul, date, adres. Nic wiecej nie potrzeba.
"""

from __future__ import annotations

import re
from typing import Any
from xml.etree import ElementTree as ET

import config

RSS = "https://www.youtube.com/feeds/videos.xml"
NS = {"a": "http://www.w3.org/2005/Atom"}

# Identyfikatory ustalone przez wyszukiwarke (strony statystyk kanalow), bo
# youtube.com/@uchwyt przekierowuje na zgode. Sprawdzone: kazdy oddaje RSS 200.
KANALY = {
    # ====================================================================
    # PRZYKLAD I JEDNOCZESNIE PUSTE MIEJSCE. Tu wchodza identyfikatory
    # kanalow YouTube, ktore robia w TWOJEJ niszy dobor tematow — czyli
    # ktore od lat wybieraja, o czym warto mowic, i maja na tym liczniki.
    #
    # Slownik jest CELOWO PUSTY. Poprzednia zawartosc byla lista trzynastu
    # prawdziwych, nazwanych kanalow z jednej konkretnej niszy i wyszla przy
    # czyszczeniu repozytorium razem z resztą tozsamosci.
    #
    # PUSTY SLOWNIK NIE ZABIJA PRZEBIEGU — sprawdzone uruchomieniem:
    # `stages.zaczyn_z_kanalow` oddaje wtedy jawny tekst "(nothing fetched
    # today)", a prompt radzi sobie sama siatka dziedzin. Notka bez zaczynu
    # jest mniej aktualna; brak notki jest gorszy.
    #
    # JAK ZDOBYC IDENTYFIKATOR: youtube.com/@uchwyt przekierowuje na sciane
    # zgody i nie oddaje niczego, a oEmbed dziala tylko dla FILMOW. Dziala
    # zapytanie HTTP z ciasteczkiem zgody `CONSENT=YES+cb...` i `SOCS=CAI`,
    # a potem regex na `"externalId":"(UC...)"` w HTML. Sam kanal RSS zgody
    # NIE wymaga — jest potrzebna wylacznie do jednorazowego ustalenia
    # identyfikatora.
    #
    # Ksztalt wpisu:  "Nazwa kanalu": "UCxxxxxxxxxxxxxxxxxxxxxx",
    # ====================================================================
}

# JAK ZDOBYWA SIE IDENTYFIKATOR KANALU, bo to kosztowalo pol godziny.
# youtube.com/@uchwyt przekierowuje na sciane zgody i nie oddaje niczego;
# oEmbed dziala tylko dla FILMOW, nie dla kanalow (404); przegladarka nie
# wystawia przyciskow zgody w drzewie dostepnosci.
#
# Dziala: zwykle zapytanie HTTP z ciasteczkiem zgody `CONSENT=YES+cb...`
# i `SOCS=CAI`, a potem regex na `"externalId":"(UC...)"` w HTML. Wlasciciel
# zatwierdzil przejscie przez zgode wprost.
#
# Sam kanal RSS zgody NIE wymaga — potrzebna jest wylacznie do jednorazowego
# ustalenia identyfikatora nowego kanalu.

# Naglowkowa oprawa do zdjecia. Zostawiamy ZDARZENIE, wyrzucamy obietnice.
OPRAWA = (
    # NAWIAS Z LICZBA ZOSTAJE — tam siedzi numer wersji, czyli jedyne slowo,
    # ktore przy premierze modelu maja wspolne rozne kanaly. Zmierzone na
    # zywym korpusie: tytul postaci „<Firma> went CRAZY (<Model>)" traci
    # nawias, potem slowo pisane wersalikami, zostaje „<Firma> went" — dwa
    # slowa przy progu czterech, wiec CALA pozycja wypada z korpusu.
    # A byl to jedyny DRUGI kanal, ktory tego dnia mowil o tej premierze.
    r"\s*\((?![^)]*\d)[^)]*\)\s*$", r"\s*\[(?![^\]]*\d)[^\]]*\]\s*$",
    r"\b(this )?(will |just )?change(s|d)? everything\b",
    r"\b(insane|shocking\w*|crazy|wild|unbelievable|mind-?blowing)\b",
    r"\bcritical warning\b", r"\bpanicking\b", r"\byou won'?t believe\b",
    r"^\s*(BREAKING|URGENT|WOW)[:\s-]+", r"\s*[\U0001F300-\U0001FAFF]\s*",
)

# Tytuly, ktore nie sa zdarzeniem tylko trescia kanalu — nie nasza sprawa.
NIE_TEMAT = re.compile(
    r"\b(how to|tutorial|my (setup|workflow|system)|behind the scenes|BTS|"
    r"i built|build a business|giveaway|q&a|ama|livestream|podcast #\d)\b"
    r"|\bthe .{0,20} situation\b"
    # TRESCI PRODUKTOWE I PORADNIKI. Pierwszy przebieg przepuscil trzy
    # tytuly tej klasy: „<narzedzie> can do X for you", „N Use Cases That
    # Feel Like <cos>", „You NEED to try this" — to sa recenzje
    # narzedzi, nie zdarzenia, i nie ma o czym pisac.
    r"|\b(use cases?|you need to try|saves? (so much )?time|is so easy|"
    r"hands-?on|first look|i tested|top \d+|\d+ (best|new|open-source))\b"
    # KLIPY Z WYWIADU. Kanaly rozmow tna jedna rozmowe na kilkanascie kawalkow
    # i kazdy ma w tytule „X and Y" — dziesiec pozycji dziennie z jednego
    # materialu zalewa liste i wypycha wszystko inne.
    r"|\b\w+\s+and\s+(Kanal Wywiadow|Kanal Rozmow)\b",
    re.IGNORECASE,
)


def oczysc(tytul: str) -> str:
    """Zdejmuje obietnice, zostawia zdarzenie."""
    t = tytul
    for w in OPRAWA:
        t = re.sub(w, " ", t, flags=re.IGNORECASE)
    t = re.sub(r"\s{2,}", " ", t).strip(" .,-–—…")
    return t


def przetworz(wpisy: list[tuple[str, Any]]) -> list[dict[str, Any]]:
    """(nazwa_kanalu, element) -> kandydaci. Czysta funkcja, testowalna."""
    widziane: set[str] = set()
    out: list[dict[str, Any]] = []
    for kanal, e in wpisy or []:
        t = e.find("a:title", NS)
        if t is None or not (t.text or "").strip():
            continue
        surowy = " ".join(t.text.split())
        if NIE_TEMAT.search(surowy):
            continue
        czysty = oczysc(surowy)
        if len(czysty.split()) < 4:
            continue
        klucz = re.sub(r"[^a-z0-9 ]", "", czysty.lower())[:60]
        if klucz in widziane:
            continue
        widziane.add(klucz)
        link = e.find("a:link", NS)
        out.append({
            "temat": czysty,
            "surowy": surowy,
            "kanal": kanal,
            "data": (e.find("a:published", NS).text or "")[:10]
                    if e.find("a:published", NS) is not None else "",
            "url": link.get("href") if link is not None else "",
            "rola": "zdarzenie do sprawdzenia; naglowka nie kopiujemy",
        })
    out.sort(key=lambda x: x["data"], reverse=True)
    return out


# Slowa, ktore nie odrozniaja jednego wydarzenia od drugiego. Bez nich jedno
# slowo powtarzajace sie w calej dziedzinie laczyloby w jedno wydarzenie cala
# tablice kanalow.
#
# CZWARTA KOPIA TEJ SAMEJ LISTY. Trzy poprzednie (`stages`) scalono
# 3 wrzesnia 2026 w `config.PUSTE_SLOWA_NISZY`; ta przezyla, bo nazywa sie
# `_TLO`, a szukano po nazwie `PUSTE_SLOWA`. Trzymala osiem slow jednej
# dziedziny wpisanych na sztywno — u konta o czymkolwiek innym osiem slow bez
# znaczenia, a jego wlasne slowa-tlo nadal laczace wszystko ze wszystkim.
#
# ROZDZIELONE TAK SAMO, JAK W `stages`: czesc ogolna jest wlasnoscia jezyka
# i zostaje w kodzie, czesc dziedzinowa przychodzi z konfiguracji.
_TLO_OGOLNE = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for",
    "with", "is", "are", "was", "were", "it", "its", "this", "that", "you",
    "your", "we", "our", "just", "now", "new", "how", "why", "what", "than",
    "from", "has", "have", "can", "will", "about", "more", "most", "first",
}
_TLO = _TLO_OGOLNE | {s.lower() for s in getattr(config, "PUSTE_SLOWA_NISZY", ())}


def _rdzen(temat: str) -> set[str]:
    """Slowa nosne tytulu — do porownywania, czy dwa kanaly mowia o tym samym."""
    return {s for s in re.findall(r"[a-z0-9][a-z0-9\-\.]{2,}", temat.lower())
            if s not in _TLO}


# Rok to nie numer wersji. Bez tego wyzwalacz premiery bral „AGI 2026" u dwoch
# kanalow za premiere modelu o numerze 2026.
_ROK = re.compile(r"^(19|20)\d\d$")


def _numer_wersji(slowo: str) -> bool:
    """Czy token wyglada na numer wydania: ma cyfre i nie jest rokiem.

    „5.1", „5.3", „gpt-6", „4.6" — tak. „2026", „claude", „agents" — nie.
    """
    return any(c.isdigit() for c in slowo) and not _ROK.match(slowo)


def wielkie_wydarzenia(korpus: list[dict[str, Any]], min_kanalow: int = 3,
                       min_wspolnych: int = 2, swiezosc_dni: int = 4,
                       min_kanalow_premiery: int = 2) -> list[dict[str, Any]]:
    """Rzeczy, o ktorych mowi NARAZ kilka roznych kanalow.

    PO CO. Wlasciciel: „jak wychodzi nowy model albo jest duze wydarzenie AI,
    to musi miec pierwszenstwo przed wszystkim".

    To stoi w napieciu z regula, ktora skaut i bank maja od poczatku: „wyszedl
    nowy model" nie jest tematem, tylko tym, co w tym tygodniu pisza wszyscy.
    Regula jest sluszna — bez niej stajemy sie jednym z pieciuset kanalow
    opisujacych premiere.

    Napiecie znika, gdy rozdzielic OKAZJE od TEMATU. Wydarzenie mowi nam, KIEDY
    czytelnik patrzy w te strone; nie mowi, CO mamy napisac. Tresc nadal musi
    przejsc te same bramki — mechanizm, zlamane przekonanie, sprawdzalnosc.
    Wykrycie wydarzenia daje wiec PIERWSZENSTWO W KOLEJCE, nigdy zwolnienia
    z jakosci. Ta funkcja NICZEGO NIE BLOKUJE: pusta lista znaczy „spokojny
    dzien", a nie „stop".

    SYGNAL JEST OBIEKTYWNY I LICZY GO KOD, nie model. Sa dwa i celowo mierza
    co innego:

    1. FALA — ten sam rdzen tematu u co najmniej `min_kanalow` ROZNYCH
       kanalow, i KAZDY z tych kanalow ma film nie starszy niz `swiezosc_dni`.
       Jeden kanal krzyczacy „EVERYTHING CHANGED" to nie wydarzenie, tylko
       naglowek.

    2. PREMIERA — NOWY numer wersji u co najmniej `min_kanalow_premiery`
       ROZNYCH kanalow w tym samym oknie. Powod jest zmierzony: w dniu
       premiery jedynym slowem wspolnym dla kanalow jest NAZWA I NUMER, bo
       reszta tytulu to szum, u kazdego inny — a regula fali wymaga wtedy
       dwoch wspolnych slow i dlatego milczy. 2 wrzesnia 2026 o Fable 5.1
       mowily tego dnia dwa kanaly (Kanal Newsowy, Kanal Produktowy) i wspolne mialy
       dokladnie {fable, 5.1}; wykrywacz oddal zero.

       Nie jest to obnizenie progu do dwoch kanalow, bo warunki sa trzy naraz:
       token musi miec CYFRE i nie byc rokiem, NIE MOZE wystepowac w korpusie
       sprzed okna, i musza go miec DWA rozne kanaly. Zmierzone na 64 dniach
       korpusu: ten wyzwalacz odpalil sie dwa razy, obydwa to premiera Fable
       5.1. Doktryna „jeden kanal to nie wydarzenie" zostaje nietknieta —
       swiadek nadal musi byc wiecej niz jeden.

    NOWOSC LICZYMY WZGLEDEM PODANEGO KORPUSU, wiec te funkcje wola sie na
    PELNYM korpusie (`korpus_kanalow(200)`), nigdy na przycietym: w korpusie
    bez historii kazdy numer wersji wyglada na nowy.
    """
    from datetime import datetime as _d, timedelta as _td, timezone as _tz
    granica = (_d.now(_tz.utc) - _td(days=swiezosc_dni)).strftime("%Y-%m-%d")

    # PIERWSZENSTWO PRZYSLUGUJE TEMU, CO DZIEJE SIE TERAZ — i liczy sie to
    # NA POZYCJE, nie na grupe. Poprzednia wersja sprawdzala swiezosc przez
    # `max(data)` calej grupy, wiec trzy kanaly rozrzucone na trzy miesiace
    # przechodzily dzieki jednemu swiezemu filmowi. Tak przeszlo JEDYNE
    # wykrycie w historii tej funkcji: grupa ACME 5.3 miala filmy z 15, 26 i 30
    # sierpnia oraz 1 wrzesnia — rozpietosc 17 dni przy oknie czterech.
    # Rzecz, o ktorej trzy kanaly mowily dwa tygodnie temu, jest historia,
    # a nie powodem, zeby przestawiac kolejke.
    swieze = [p for p in (korpus or []) if (p.get("data") or "") >= granica]
    if not swieze:
        return []

    # --- 1. FALA: ten sam rdzen u wielu kanalow, kazdy w oknie ---
    grupy: list[dict[str, Any]] = []
    for poz in swieze:
        rdzen = _rdzen(poz.get("temat") or "")
        if len(rdzen) < min_wspolnych:
            continue
        for g in grupy:
            if len(g["rdzen"] & rdzen) >= min_wspolnych:
                g["pozycje"].append(poz)
                g["kanaly"].add(poz.get("kanal", ""))
                g["rdzen"] &= rdzen or g["rdzen"]
                break
        else:
            grupy.append({"rdzen": rdzen, "pozycje": [poz], "premiera": False,
                          "kanaly": {poz.get("kanal", "")}})

    # --- 2. PREMIERA: numer wersji, ktorego wczesniej w korpusie nie bylo ---
    # Pozycja bez daty liczy sie do historii, nie do okna — czyli w razie
    # watpliwosci wyzwalacz MILCZY, zamiast strzelac.
    znane: set[str] = set()
    for p in korpus or []:
        if (p.get("data") or "") < granica:
            znane |= _rdzen(p.get("temat") or "")
    premiery: dict[str, list[dict[str, Any]]] = {}
    for p in swieze:
        for s in _rdzen(p.get("temat") or ""):
            if s not in znane and _numer_wersji(s):
                premiery.setdefault(s, []).append(p)
    for _s, pozycje in sorted(premiery.items()):
        kanaly = {p.get("kanal", "") for p in pozycje}
        if len(kanaly) < min_kanalow_premiery:
            continue
        # ETYKIETA TO CZESC WSPOLNA TYTULOW, NIE SAM NUMER. `stages` robi
        # z niej klucz pamieci zdarzen, wiec gole „5.1" zlepiloby dwie rozne
        # premiery o tym samym numerze w jedno i druga nigdy nie otworzylaby
        # furtki. „5.1, fable" jest jednoznaczne.
        wspolne = set.intersection(*[_rdzen(p.get("temat") or "")
                                     for p in pozycje])
        grupy.append({"rdzen": wspolne or {_s}, "pozycje": pozycje,
                      "premiera": True, "kanaly": kanaly})

    # JEDNO ZDARZENIE = JEDEN WPIS. Kazdy wpis kosztuje, bo `stages` otwiera
    # platne szukanie raz na KAZDY nowy klucz zdarzenia (~0,23 USD). Skleic
    # trzeba dwa przypadki: premiera zlapana juz przez fale, oraz dwa numery
    # z tych samych tytulow („fable 5.1" i „5.1"), ktore daja te sama etykiete.
    pokryte = {id(p) for g in grupy
               if not g["premiera"] and len(g["kanaly"]) >= min_kanalow
               for p in g["pozycje"]}
    wyniki: list[dict[str, Any]] = []
    widziane: set[tuple[str, ...]] = set()
    for g in grupy:
        if len(g["kanaly"]) < (min_kanalow_premiery if g["premiera"]
                               else min_kanalow):
            continue
        if g["premiera"] and all(id(p) in pokryte for p in g["pozycje"]):
            continue
        o_czym = sorted(g["rdzen"])[:6]
        if tuple(o_czym) in widziane:
            continue
        widziane.add(tuple(o_czym))
        wyniki.append({"o_czym": o_czym,
                       "kanalow": len(g["kanaly"]),
                       "kanaly": sorted(g["kanaly"]),
                       "tytuly": [p.get("temat") or "" for p in g["pozycje"][:4]],
                       "data": max((p.get("data") or "") for p in g["pozycje"]),
                       "premiera": g["premiera"]})

    # Premiera przed fala — wlasciciel chce pisac o nowym modelu tego samego
    # dnia; fala o rzeczy o tydzien starszej moze poczekac na drugie miejsce.
    wyniki.sort(key=lambda w: w["data"], reverse=True)
    wyniki.sort(key=lambda w: (not w["premiera"], -w["kanalow"]))
    return wyniki


# Korpus zbudowany w tym procesie, i kiedy. Trzynascie zapytan HTTP na kanaly
# YouTube'a nie jest darmowe w czasie, a przebieg wola te funkcje DWA RAZY:
# raz po zaczyn do promptu ciekawostek, raz po wykrywacz wielkich wydarzen.
# Zmierzone 30 sierpnia: w logu jednego przebiegu linia „180 filmow z 13
# kanalow" pojawiala sie dwukrotnie, kilkanascie sekund po sobie.
#
# TERMIN, NIE WIECZNOSC. Przebieg dnia potrafi trwac ponad godzine, wiec zapas
# bez terminu oznaczalby, ze pod koniec cyklu patrzymy na kanaly sprzed 90
# minut. Pol godziny to kompromis: w jednym przebiegu pobieramy raz, a proces
# dlugowieczny i tak sie odswiezy.
_ZAPAS: dict[str, Any] = {"kiedy": 0.0, "wpisy": None}
ZAPAS_WAZNY_S = 1800


def korpus_kanalow(ile: int = 30) -> list[dict[str, Any]]:
    import time

    import httpx

    import config

    # Zapas trzyma PELNA liste, a nie przyciete `ile` — inaczej wywolanie po 26
    # tematow zatrulo by pozniejsze wywolanie po 200, ktorego potrzebuje
    # wykrywacz wydarzen.
    if (_ZAPAS["wpisy"] is not None
            and time.time() - _ZAPAS["kiedy"] < ZAPAS_WAZNY_S):
        return list(_ZAPAS["wpisy"])[:ile]

    wpisy: list[tuple[str, Any]] = []
    with httpx.Client(timeout=config.FETCH_TIMEOUT_S, follow_redirects=True,
                      headers={"User-Agent": config.FETCH_USER_AGENT}) as c:
        for nazwa, cid in KANALY.items():
            try:
                r = c.get(RSS, params={"channel_id": cid})
                if r.status_code != 200:
                    print("  [kanaly] %s: HTTP %s" % (nazwa, r.status_code), flush=True)
                    continue
                for e in ET.fromstring(r.content).findall("a:entry", NS):
                    wpisy.append((nazwa, e))
            except Exception as exc:
                print("  [kanaly] %s: %s" % (nazwa, type(exc).__name__), flush=True)
    k = przetworz(wpisy)
    print("  [kanaly] %d filmow z %d kanalow -> %d tematow"
          % (len(wpisy), len(KANALY), len(k)), flush=True)
    # Zapas zapisujemy TYLKO wtedy, gdy cos przyszlo. Zapamietanie pustki po
    # sieciowej wpadce wyciszyloby kanaly na pol godziny, a prompt dostalby
    # „(nothing fetched today)" mimo dzialajacej sieci.
    if k:
        _ZAPAS["wpisy"] = list(k)
        _ZAPAS["kiedy"] = time.time()
    return k[:ile]


if __name__ == "__main__":
    import pathlib
    import sys
    sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
    for x in korpus_kanalow():
        print("  [%s] %-18s %s" % (x["data"], x["kanal"][:18], x["temat"][:66]))
