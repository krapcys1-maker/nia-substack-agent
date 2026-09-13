"""Czy dostawca ma juz nowsza wersje modelu, na ktorym chodzimy — i przejscie na nia.

## Skad to

13 wrzesnia 2026 lista modeli DeepSeeka (`GET /models`) brzmiala:

    deepseek-flash, deepseek-v4-pro

Kartridz serwera mial `deepseek-v4-flash` w dziewietnastu rolach, a tej nazwy na
liscie juz nie bylo. Proba na zywo, dwa wywolania po 11 tokenow:

    deepseek-flash    -> odpowiada model: deepseek-flash   (odcisk aeb56401…)
    deepseek-v4-flash -> odpowiada model: deepseek-flash   (odcisk aeb56401…)

Cennik dostawcy tego samego dnia: `deepseek-flash` to DeepSeek-V4.1-Flash,
a stare nazwy sa „still accepted". Bot pisal wiec nowym modelem pod stara
nazwa, ksiegowal go po starej stawce, a w dniu, w ktorym alias zniknie,
dziewietnascie rol padloby naraz — bez slowa o przyczynie.

## Co robi

Na starcie kazdego przebiegu (dnia i artykulu), albo na zadanie:

1. pyta dostawcow o liste modeli — zwykle GET, za darmo;
2. dla kazdego modelu, ktorego UZYWAMY, szuka nastepcy w TEJ SAMEJ rodzinie:
   nowszej wersji (`deepseek-v4-pro` -> `deepseek-v4.1-pro`, `claude-opus-5`
   -> `claude-opus-5-1`, `gpt-5.6-sol` -> `gpt-6-sol`) albo — gdy naszego
   modelu na liscie juz nie ma — nazwy bez numeru, ktora dostawca podaje w tej
   rodzinie (`deepseek-v4-flash` -> `deepseek-flash`);
3. sprawdza nastepce NA ZYWO ta sama droga, ktora pojdzie produkcja:
   `llm.call` z kontrola budzetu, klucza i aktywacji oraz zapisem kosztu;
4. dopiero po udanej probie zapisuje zamiane w danych instancji.

Zamiany naklada `zastosuj` przy starcie kazdego procesu, zaraz po presecie.

## Czego NIE robi

- Nie przeskakuje miedzy rodzinami. Flash nie staje sie pro, sol nie staje sie
  astra, opus nie staje sie fable — to sa inne ceny i inne decyzje wlasciciela.
- Nie sklada identyfikatorow. Bierze wylacznie to, co dostawca wypisal.
- Nie czyta bledu sieci jako wycofania. Brak listy to „nie wiem".
- Nie rusza modeli z `config.MODELE_NIE_RUSZAJ`, a przy
  `config.MODELE_SAME_NA_NOWSZE = False` tylko raportuje.
- Nie zgaduje ceny w dol. Nastepca bez wpisu w `PRICING` jest liczony po
  PODWOJNEJ stawce poprzednika, oznaczonej jako niepotwierdzona — zawyzony
  koszt zatrzyma budzet wczesniej, zanizony pozwolilby go przekroczyc.

Wiersz polecen (z korzenia repo):

    python agent-v2/wersje_modeli.py              # raport, bez przelaczania i bez kosztu
    python agent-v2/wersje_modeli.py --przelacz   # sprawdz, przetestuj, przelacz
    python agent-v2/wersje_modeli.py --cofnij deepseek-v4-flash
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# BEZ `import config` NA GORZE. `config` naklada zamiany na samym koncu swojego
# importu i wtedy importuje ten modul. Gdyby ten modul importowal `config`
# u siebie na gorze, to proces, ktory zaczyna od `import wersje_modeli`,
# dostalby w `config` pol-zaladowany modul bez `zastosuj` — sprawdzone:
# „partially initialized module 'wersje_modeli' has no attribute 'zastosuj'".
# Kazda funkcja siega po `config` sama, kiedy juz jest zaladowany.

# PRZY KAZDYM PRZEBIEGU, NIE RAZ NA DOBE — decyzja wlasciciela z 13 wrzesnia
# 2026: nowy model ma wchodzic od razu. Pytanie o liste nic nie kosztuje.
# Najblizsze okna przebiegow stoja 2 h 40 min od siebie (11:00 i 13:40 UTC),
# wiec dwie godziny waznosci znacza „kazdy przebieg pyta"; dzien i artykul nie
# chodza naraz, bo biora ten sam zamek.
WAZNE_GODZIN = 2

# Rola, na ktorej idzie proba nastepcy. Ma wlasny sufit tokenow i jest
# mechaniczna (bez myslenia na DeepSeeku) — patrz `config.MAX_TOKENS`.
ROLA_PROBY = "nowszy_model"

# STALE Z NAZWA MODELU, KTORE KOD POROWNUJE WPROST. `llm._call_claude` wysyla
# `effort` tylko wtedy, gdy `model in (config.CLAUDE, config.SONNET,
# config.FABLE)`, a `llm._cost` liczy cache Fable po `model == config.FABLE`.
# Zamiana samego `MODEL_FOR` dalaby wiec model, ktory chodzi, ale bez effortu
# i z bledna stawka cache. `FABLE_5` i `IMAGE_MODEL` swiadomie poza lista:
# pierwszy trzyma historie porownan, drugi to inna linia produktow.
STALE_Z_MODELEM = (
    "CLAUDE", "SONNET", "FABLE", "GPT_SOL", "GPT_TERRA", "GPT_LUNA", "GPT_ASTRA",
    "DEEPSEEK", "DEEPSEEK_PRO", "MODEL_ZAPASOWY_WYSZUKIWANIA", "ZAPASOWY_PISARZ",
)

# ZAPASOWE MODELE CHODZA NAPRAWDE, choc nie stoja w zadnej roli: na nie wraca
# pisarz i wyszukiwanie po awarii. Pozostale stale z listy wyzej sa tylko
# nazwami — sprawdzanie ich placiloby za probe modelu, ktorego nic nie wola.
STALE_ZAPASOWE = ("MODEL_ZAPASOWY_WYSZUKIWANIA", "ZAPASOWY_PISARZ")

# RODZINA = dostawca + nazwa linii; WERSJA = liczby. Wzory pisane pod nazwy,
# ktore dostawcy NAPRAWDE podawali 13 wrzesnia 2026 (lista w tescie), a nie pod
# ogolna teorie nazewnictwa. Nazwy z doklejonym czyms jeszcze
# (`gpt-5.1-codex-max`, `deepseek-v4-flash-vision-exp`, `gpt-4.1-2025-04-14`)
# nie pasuja do zadnego wzoru i sa pomijane — to nie sa nastepcy naszych modeli.
_WZORY = (
    ("deepseek", re.compile(
        r"^deepseek-v(?P<a>\d+)(?:\.(?P<b>\d+))?-(?P<linia>flash|pro)$")),
    ("deepseek", re.compile(r"^deepseek-(?P<linia>flash|pro)$")),
    ("openai", re.compile(r"^gpt-(?P<a>\d+)(?:\.(?P<b>\d+))?-(?P<linia>[a-z]+)$")),
    ("anthropic", re.compile(
        r"^claude-(?P<linia>[a-z]+)-(?P<a>\d+)(?:-(?P<b>\d{1,2}))?"
        r"(?:-(?P<data>\d{8}))?$")),
)


def plik() -> Path:
    """Stan w danych INSTANCJI — kazde konto ma wlasne zamiany i wlasna historie."""
    import config
    return Path(config.DATA_DIR) / "wersje_modeli.json"


def rozbierz(model: str) -> dict[str, Any] | None:
    """Dostawca, rodzina i wersja z nazwy modelu; None, gdy nazwa nie pasuje.

    Wersja `None` znaczy nazwe BEZ NUMERU (`deepseek-flash`) — dostawca trzyma
    pod nia biezaca wersje linii i sam ja przesuwa.
    """
    for dostawca, wzor in _WZORY:
        m = wzor.match(str(model or ""))
        if not m:
            continue
        g = m.groupdict()
        wersja = None if g.get("a") is None else (int(g["a"]), int(g.get("b") or 0))
        return {"dostawca": dostawca, "rodzina": "%s:%s" % (dostawca, g["linia"]),
                "wersja": wersja, "data": g.get("data") or ""}
    return None


def nastepca(model: str, lista: list[str]) -> tuple[str | None, str]:
    """(nastepca albo None, dlaczego) — tylko z tej samej rodziny i tylko z listy."""
    ja = rozbierz(model)
    if ja is None:
        return None, "nie umiem odczytac wersji z nazwy %s" % model
    nowsze = []
    for inny in lista:
        on = rozbierz(inny)
        if (inny == model or on is None or on["rodzina"] != ja["rodzina"]
                or on["wersja"] is None or ja["wersja"] is None):
            continue
        if on["wersja"] > ja["wersja"]:
            # Ta sama wersja z data i bez daty: bierzemy nazwe bez daty, bo
            # dostawca przesuwa ja o poprawki, a migawka z data stoi w miejscu.
            nowsze.append((on["wersja"], 0 if not on["data"] else -1, inny))
    if nowsze:
        wersja, _, nowy = max(nowsze)
        return nowy, "nowsza wersja w tej samej rodzinie (%s)" % ".".join(map(str, wersja))
    if model in lista:
        return None, "aktualny"
    aliasy = sorted(inny for inny in lista
                    if (rozbierz(inny) or {}).get("rodzina") == ja["rodzina"]
                    and rozbierz(inny)["wersja"] is None)
    if aliasy:
        return aliasy[0], ("%s zniknal z listy dostawcy, ktory podaje w tej rodzinie %s"
                           % (model, aliasy[0]))
    return None, "%s ZNIKNAL Z LISTY DOSTAWCY i nie ma nastepcy w rodzinie" % model


def modele_w_uzyciu(cfg=None) -> set[str]:
    """Modele tekstowe, na ktorych naprawde chodzimy: role plus modele zapasowe."""
    if cfg is None:
        import config as cfg
    uzywane = {str(m) for rola, m in cfg.MODEL_FOR.items()
               if m and rola not in ("obraz", ROLA_PROBY)}
    uzywane |= {str(getattr(cfg, n)) for n in STALE_ZAPASOWE
                if isinstance(getattr(cfg, n, None), str) and getattr(cfg, n)}
    return {m for m in uzywane if rozbierz(m) is not None}


def lista_modeli(dostawca: str) -> list[str] | None:
    """Identyfikatory, ktore dostawca dzis podaje. None = nie wiem (brak klucza, siec)."""
    import config
    try:
        if dostawca == "anthropic":
            if not config.ANTHROPIC_API_KEY:
                return None
            import anthropic
            klient = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY,
                                         timeout=30.0, max_retries=2)
            # Strona iterowana wprost stronicuje sama.
            return sorted(str(m.id) for m in klient.models.list())
        import httpx
        adres, klucz = {
            "deepseek": (config.DEEPSEEK_BASE_URL, config.DEEPSEEK_API_KEY),
            "openai": (config.OPENAI_BASE_URL, config.OPENAI_API_KEY),
        }[dostawca]
        if not klucz:
            return None
        odp = httpx.get("%s/models" % adres.rstrip("/"),
                        headers={"Authorization": "Bearer %s" % klucz}, timeout=30.0)
        odp.raise_for_status()
        return sorted(str(m["id"]) for m in odp.json().get("data", []) if m.get("id"))
    except Exception as exc:                                  # noqa: BLE001
        print("  [modele] lista %s niedostepna: %s" % (dostawca, type(exc).__name__),
              flush=True)
        return None


def zarejestruj(cfg, stary: str, nowy: str) -> None:
    """Cennik i narzedzie wyszukiwania dla nastepcy, zanim cokolwiek go zawola.

    `llm._reserve_attempt` bierze `config.PRICING[model]` przed kazdym
    wywolaniem — model bez wpisu to KeyError w polowie platnej sciezki.
    """
    if nowy not in cfg.PRICING:
        cena = dict(cfg.PRICING[stary])
        for klucz in ("in", "out", "cache"):
            if klucz in cena:
                cena[klucz] = cena[klucz] * 2
        cena["verified"] = False
        cfg.PRICING[nowy] = cena
        print("  [modele] %s nie ma stawki w cenniku — licze po PODWOJNEJ stawce %s,"
              " dopoki nikt nie wpisze prawdziwej" % (nowy, stary), flush=True)
    for slownik in ("WEB_SEARCH_TOOL", "STAWKI_PRZED_PODWYZKA"):
        s = getattr(cfg, slownik, None)
        if isinstance(s, dict) and stary in s and nowy not in s:
            s[nowy] = s[stary]


def przestaw(cfg, stary: str, nowy: str) -> list[str]:
    """Kazde miejsce, w ktorym stoi `stary`, dostaje `nowy`. Oddaje liste miejsc."""
    zarejestruj(cfg, stary, nowy)
    miejsca = []
    for rola, model in list(cfg.MODEL_FOR.items()):
        if model == stary:
            cfg.MODEL_FOR[rola] = nowy
            miejsca.append("MODEL_FOR[%s]" % rola)
    for nazwa in STALE_Z_MODELEM:
        if getattr(cfg, nazwa, None) == stary:
            setattr(cfg, nazwa, nowy)
            miejsca.append(nazwa)
    return miejsca


def wczytaj() -> dict[str, Any]:
    try:
        dane = json.loads(plik().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        dane = {}
    if not isinstance(dane, dict):
        dane = {}
    dane.setdefault("zamiany", {})
    dane.setdefault("odrzucone", {})
    return dane


def zapisz(dane: dict[str, Any]) -> None:
    sciezka = plik()
    sciezka.parent.mkdir(parents=True, exist_ok=True)
    tymczasowy = sciezka.with_suffix(".json.tmp")
    tymczasowy.write_text(json.dumps(dane, ensure_ascii=False, indent=2), encoding="utf-8")
    tymczasowy.replace(sciezka)


def _koniec_lancucha(zamiany: dict[str, Any], model: str) -> str:
    """a -> b, a pozniej b -> c: model `a` ma trafic od razu na `c`."""
    widziane = {model}
    while model in zamiany and zamiany[model].get("na"):
        model = zamiany[model]["na"]
        if model in widziane:
            break
        widziane.add(model)
    return model


def zastosuj(cfg=None) -> list[tuple[str, str]]:
    """Naklada zapisane zamiany na zaladowana konfiguracje. Bez sieci i bez kosztu."""
    if cfg is None:
        import config as cfg
    if not getattr(cfg, "MODELE_SAME_NA_NOWSZE", True):
        return []
    zamiany = wczytaj()["zamiany"]
    przypiete = set(getattr(cfg, "MODELE_NIE_RUSZAJ", ()) or ())
    zrobione = []
    for stary in sorted(zamiany):
        nowy = _koniec_lancucha(zamiany, stary)
        if nowy == stary or stary in przypiete:
            continue
        if stary not in cfg.PRICING and nowy not in cfg.PRICING:
            continue
        if stary not in cfg.PRICING:
            # Poprzednik zniknal z cennika silnika — nastepca musi miec wlasny wpis.
            cfg.PRICING[stary] = dict(cfg.PRICING[nowy])
        if przestaw(cfg, stary, nowy):
            zrobione.append((stary, nowy))
    return zrobione


def sprawdz_na_zywo(nowy: str, *, conn, run_id: int | None) -> tuple[bool, str]:
    """Jedno male wywolanie nastepcy przez `llm.call` — ta sama droga co produkcja."""
    import config
    import llm

    poprzedni = config.MODEL_FOR.get(ROLA_PROBY)
    config.MODEL_FOR[ROLA_PROBY] = nowy
    try:
        tekst = llm.call(ROLA_PROBY, "You are a connectivity check. Answer with one word.",
                         "Reply with the single word OK.", conn=conn, run_id=run_id)
    except Exception as exc:                                  # noqa: BLE001
        return False, ("%s: %s" % (type(exc).__name__, exc))[:300]
    finally:
        if poprzedni is None:
            config.MODEL_FOR.pop(ROLA_PROBY, None)
        else:
            config.MODEL_FOR[ROLA_PROBY] = poprzedni
    if not str(tekst or "").strip():
        return False, "pusta odpowiedz (DRY_RUN albo model nic nie oddal)"
    return True, str(tekst).strip()[:60]


def sprawdz_i_przelacz(conn, run_id: int | None = None, *, wymus: bool = False,
                       przelaczaj: bool = True, listy: dict | None = None) -> dict[str, Any]:
    """Raz na dobe: listy dostawcow, nastepcy, proba na zywo, zapis zamian.

    `listy` podstawia test; w produkcji zawsze pytamy dostawcow.
    """
    import config

    dane = wczytaj()
    teraz = datetime.now(timezone.utc)
    ostatnio = dane.get("sprawdzono")
    if not wymus and ostatnio:
        try:
            if teraz - datetime.fromisoformat(ostatnio) < timedelta(hours=WAZNE_GODZIN):
                return {"pominiete": "sprawdzone %s" % ostatnio, "raport": []}
        except ValueError:
            pass
    # DARMOWY TEST NIE PYTA DOSTAWCOW I NIE PISZE STANU KONTA. Zmierzone przy
    # wpinaniu: trzy darmowe testy puszczaja prawdziwe `run.dzien()` na atrapach
    # i to wywolanie wyslalo z nich `GET /models` do dwoch dostawcow, a potem
    # zapisalo `wersje_modeli.json` w `agent-v2/data/` — co zlapal odcisk
    # katalogu w `test_kanal_platnego_wywolania.py`. Test, ktory chce
    # sprawdzic ten mechanizm, podstawia `listy` sam.
    if listy is None and not getattr(config, "WOLNO_WOLAC_MODEL", True):
        return {"pominiete": "darmowy test — bez sieci i bez zapisu", "raport": []}
    if not getattr(config, "MODELE_SAME_NA_NOWSZE", True):
        przelaczaj = False
    przypiete = set(getattr(config, "MODELE_NIE_RUSZAJ", ()) or ())
    pobrane: dict[str, list[str] | None] = dict(listy or {})
    raport: list[tuple[str, str | None, str]] = []
    for model in sorted(modele_w_uzyciu(config)):
        dostawca = rozbierz(model)["dostawca"]
        if dostawca not in pobrane:
            pobrane[dostawca] = lista_modeli(dostawca)
        lista = pobrane[dostawca]
        if lista is None:
            raport.append((model, None, "lista dostawcy niedostepna — nie wiem"))
            continue
        nowy, powod = nastepca(model, lista)
        if not nowy:
            raport.append((model, None, powod))
            continue
        if model in przypiete:
            raport.append((model, nowy, "przypiety, nie przelaczam (%s)" % powod))
            continue
        if not przelaczaj:
            raport.append((model, nowy, "do przelaczenia: %s" % powod))
            continue
        # PROBA NA KONFIGURACJI JUZ PRZESTAWIONEJ. Dopiero wtedy stale wolane
        # wprost (effort, stawka cache) wskazuja nastepce i proba sprawdza to,
        # co pojdzie w produkcji. Oblana proba przywraca role i stale.
        role, stale = dict(config.MODEL_FOR), {n: getattr(config, n, None)
                                               for n in STALE_Z_MODELEM}
        przestaw(config, model, nowy)
        # WLASNY KANAL KOSZTOW. Proba nie sluzy zadnej notce ani komentarzowi,
        # wiec ksiegowana pod ktoryms z nich zawyzalaby jego koszt. Kanal
        # stoi TUTAJ, przy wywolaniu — tak widzi go `test_kanal_platnego_wywolania`.
        import db
        with db.kanal("modele"):
            ok, szczegol = sprawdz_na_zywo(nowy, conn=conn, run_id=run_id)
        if not ok:
            config.MODEL_FOR.clear()
            config.MODEL_FOR.update(role)
            for nazwa, wartosc in stale.items():
                if wartosc is not None:
                    setattr(config, nazwa, wartosc)
            dane["odrzucone"][nowy] = {"zamiast": model, "kiedy": teraz.isoformat(
                timespec="seconds"), "powod": szczegol}
            raport.append((model, None, "nastepca %s oblal probe: %s" % (nowy, szczegol)))
            continue
        dane["zamiany"][model] = {"na": nowy, "od": teraz.isoformat(timespec="seconds"),
                                  "powod": powod, "proba": szczegol}
        dane["odrzucone"].pop(nowy, None)
        raport.append((model, nowy, "PRZELACZONE: %s" % powod))
    dane["sprawdzono"] = teraz.isoformat(timespec="seconds")
    dane["listy"] = {k: v for k, v in pobrane.items() if v is not None}
    if przelaczaj:
        zapisz(dane)
    for model, nowy, opis in raport:
        if opis != "aktualny":
            print("  [modele] %s%s: %s" % (model, " -> %s" % nowy if nowy else "", opis),
                  flush=True)
    aktualnych = sum(1 for _, _, opis in raport if opis == "aktualny")
    print("  [modele] sprawdzone %d modeli, aktualnych %d" % (len(raport), aktualnych),
          flush=True)
    return {"raport": raport}


def cofnij(model: str) -> bool:
    """Usuwa zamiane `model -> ...`. Nastepny start procesu chodzi po staremu."""
    dane = wczytaj()
    if model not in dane["zamiany"]:
        return False
    dane["zamiany"].pop(model)
    zapisz(dane)
    return True


def main(argv: list[str] | None = None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--przelacz", action="store_true",
                    help="sprawdz nastepcow na zywo i zapisz zamiany (male wywolania)")
    ap.add_argument("--cofnij", metavar="MODEL", help="usun zapisana zamiane tego modelu")
    args = ap.parse_args(argv)
    if args.cofnij:
        print("cofnieta" if cofnij(args.cofnij) else "nie bylo takiej zamiany")
        return 0
    zamiany = wczytaj()["zamiany"]
    for stary, wpis in sorted(zamiany.items()):
        print("  zapisana zamiana: %s -> %s (od %s; %s)"
              % (stary, wpis.get("na"), wpis.get("od"), wpis.get("powod")))
    if not args.przelacz:
        sprawdz_i_przelacz(None, None, wymus=True, przelaczaj=False)
        return 0
    import db

    conn = db.connect()
    run_id = db.start_run(conn, stage="wersje_modeli")
    try:
        sprawdz_i_przelacz(conn, run_id, wymus=True, przelaczaj=True)
    except BaseException as exc:
        db.finish_run(conn, run_id, "FAILED", "wersje_modeli", repr(exc)[:400])
        raise
    db.finish_run(conn, run_id, "DONE", "wersje_modeli", "")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
