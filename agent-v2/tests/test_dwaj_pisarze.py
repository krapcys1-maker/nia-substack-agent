# -*- coding: utf-8 -*-
"""Notki pisza DWAJ pisarze na zmiane, a dziennik wie KTORY.

PO CO TO ISTNIEJE. Notka na Opusie kosztuje 0,084 USD, na DeepSeeku pro 0,010 —
osiem razy taniej. Slepa proba z 19 sierpnia 2026 pokazala, ze przy notkach
wlasciciel NIE ROZPOZNAL drozszego modelu (Fable kontra Opus 2:2 na dziewieciu
parach, piec wygranych na dziewiec to rzut moneta). Podzial pol na pol jest wiec
jednoczesnie oszczednoscia i TESTEM: po dwoch tygodniach dziennik powie, czy
notki jednego pisarza zbieraja wiecej niz drugiego.

Zeby to powiedzial, musza zajsc TRZY rzeczy naraz — i kazda jest tu sprawdzana
ZACHOWANIEM, nie odczytem kodu:

  1. wybor pisarza idzie na zmiane i liczy sie w skali DOBY, nie przebiegu;
  2. kandydat niesie nazwe modelu, ktory go napisal;
  3. `wystaw_notke` przekazuje ja do dziennika, bo tam stoja wyniki.

Bez trzeciej mielibysmy dwie kolumny KOSZTOW w tabeli `calls` i zero mozliwosci
porownania SKUTKU — a to jest cala rzecz, dla ktorej ten podzial powstal.

BEZ PYTESTA, zero sieci, zero platnych wywolan, produkcja nietknieta.
Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_dwaj_pisarze.py
"""
import hashlib
import io
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import config      # noqa: E402

# PRAWDZIWE sciezki produkcji zapamietane PRZED przelaczeniem — to one sa
# pilnowane na koncu. Ksztaltu zdjecia z `uzyj_katalogu_danych` nie zakladamy.
PROD_DB = pathlib.Path(config.DB_PATH)
PROD_DZIENNIK = pathlib.Path(config.DATA_DIR) / "dziennik.jsonl"

KAT = pathlib.Path(tempfile.mkdtemp())
STARE_SCIEZKI = config.uzyj_katalogu_danych(KAT)

import browser     # noqa: E402
import llm         # noqa: E402
import stages      # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


def odcisk(p):
    p = pathlib.Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else "brak"


PILNOWANE = [PROD_DB, PROD_DZIENNIK]
PRZED = {str(p): odcisk(p) for p in PILNOWANE}

FAKT = {"fact": "Something checkable happened in 2026.", "url": "https://example.org/a",
        "domain": "example.org", "wrong_belief": "b", "actually": "c",
        "source_date": "2026-09-01"}

print("=== 1. DWA ETAPY, DWA MODELE, TEN SAM KONTRAKT ===")
sprawdz("etap `note` chodzi na innym modelu niz `note_tani`",
        config.MODEL_FOR["note"] != config.MODEL_TANI_NOTKI
        if hasattr(config, "MODEL_TANI_NOTKI")
        else config.MODEL_FOR["note"] != config.MODEL_FOR["note_tani"],
        (config.MODEL_FOR["note"], config.MODEL_FOR["note_tani"]))
sprawdz("oba maja sufit tokenow (bez tego `_preflight` odmawia)",
        config.MAX_TOKENS.get("note_tani") == config.MAX_TOKENS.get("note"),
        (config.MAX_TOKENS.get("note"), config.MAX_TOKENS.get("note_tani")))
sprawdz("oba maja stawke, wiec koszt sie policzy",
        config.MODEL_FOR["note_tani"] in config.PRICING,
        config.MODEL_FOR["note_tani"])

print()
print("=== 2. KANDYDAT NIESIE NAZWE SWOJEGO PISARZA ===")
widziane = {"etapy": []}


def atrapa_modelu(etap, system, user, conn=None, run_id=None, **k):
    widziane["etapy"].append(etap)
    return json.dumps({"note": "x " * 40, "words": 40})


ORYG_CALL = llm.call
ORYG_WERYF = stages.zweryfikuj
ORYG_TEKSTY = stages.teksty_ostatnich_notek
ORYG_OTWARCIA = stages.ostatnie_otwarcia
try:
    llm.call = atrapa_modelu
    stages.zweryfikuj = lambda *a, **k: {"claims": [], "safe_to_post": True}
    stages.teksty_ostatnich_notek = lambda ile=40: []
    stages.ostatnie_otwarcia = lambda rodzaj="notka", ile=8: []

    with io.StringIO() as cichy:
        import contextlib
        with contextlib.redirect_stdout(cichy):
            drogi = stages.note(None, 0, "MYSL", {"fact": dict(FAKT)}, etap="note")
            tani = stages.note(None, 0, "MYSL", {"fact": dict(FAKT)}, etap="note_tani")

    sprawdz("notka z etapu `note` wie, ze pisal ja %s" % config.MODEL_FOR["note"],
            drogi["candidates"][0].get("model") == config.MODEL_FOR["note"],
            drogi["candidates"][0].get("model"))
    sprawdz("notka z etapu `note_tani` wie, ze pisal ja %s"
            % config.MODEL_FOR["note_tani"],
            tani["candidates"][0].get("model") == config.MODEL_FOR["note_tani"],
            tani["candidates"][0].get("model"))
    sprawdz("i model NAPRAWDE dostal osobny etap, nie ten sam dwa razy",
            widziane["etapy"][:1] == ["note"] and "note_tani" in widziane["etapy"],
            widziane["etapy"])
finally:
    llm.call = ORYG_CALL
    stages.zweryfikuj = ORYG_WERYF
    stages.teksty_ostatnich_notek = ORYG_TEKSTY
    stages.ostatnie_otwarcia = ORYG_OTWARCIA

print()
print("=== 3. NA ZMIANE, I LICZONE W SKALI DOBY ===")


def kto_pisze(od: int, nr: int) -> str:
    """Odwzorowanie reguly z `notki_dnia` — pilnowane asercjami nizej."""
    return "note" if (od + nr) % 2 == 0 else "note_tani"


kolejnosc = [kto_pisze(od, 0) for od in range(5)]
sprawdz("piec notek doby idzie na zmiane",
        kolejnosc == ["note", "note_tani", "note", "note_tani", "note"],
        kolejnosc)
sprawdz("drugi przebieg dnia NIE zaczyna od nowa (inaczej caly dzien"
        " szedlby jednym modelem)",
        kto_pisze(2, 0) == "note" and kto_pisze(3, 0) == "note_tani",
        (kto_pisze(2, 0), kto_pisze(3, 0)))

# KONTRDOWOD: gdyby numer liczyl sie w skali PRZEBIEGU, kazdy przebieg
# zaczynalby od `note` — i przy dwoch notkach na przebieg DeepSeek nie napisalby
# nigdy wiecej niz co druga, a przy jednej notce na przebieg NIGDY.
w_skali_przebiegu = [("note" if nr % 2 == 0 else "note_tani") for nr in [0, 0, 0, 0, 0]]
sprawdz("KONTRDOWOD: liczone w skali przebiegu dalo by piec razy ten sam model",
        set(w_skali_przebiegu) == {"note"}, w_skali_przebiegu)

zrodlo = pathlib.Path("agent-v2/stages.py").read_text(encoding="utf-8")
sprawdz("i tak wlasnie liczy to kod produkcyjny (doba + numer notki)",
        '"note" if (od + nr + _doba) % 2 == 0 else "note_tani"' in zrodlo)

print()
print("=== 3b. PISARZ NIE MOZE BYC PRZYPIETY DO RODZAJU NOTKI ===")
# `NOTE_MIX_OTHER_DAY` ma STALA kolejnosc, wiec bez przesuniecia co dobe pisarz
# dostawalby zawsze te same rodzaje — a porownanie po dwoch tygodniach
# mierzyloby RODZAJ, nie pisarza. Zlapane 3 wrzesnia 2026 na pierwszej parze
# notek z produkcji: DeepSeek dostal SPROSTOWANIE, Opus MYSL.
import collections  # noqa: E402

MIKS = config.NOTE_MIX_OTHER_DAY


def rozklad(z_przesunieciem: bool) -> dict:
    par = collections.Counter()
    for doba in range(14):
        for i, typ in enumerate(MIKS):
            e = "note" if (i + (doba if z_przesunieciem else 0)) % 2 == 0 else "note_tani"
            par[(e, typ)] += 1
    return par


bez, z_nim = rozklad(False), rozklad(True)
typy = list(dict.fromkeys(MIKS))
sprawdz("KONTRDOWOD: bez przesuniecia jeden pisarz NIGDY nie pisze"
        " niektorych rodzajow",
        any(bez[("note", t)] == 0 or bez[("note_tani", t)] == 0 for t in typy),
        {t: (bez[("note", t)], bez[("note_tani", t)]) for t in typy})
sprawdz("z przesunieciem KAZDY pisarz dostaje KAZDY rodzaj",
        all(z_nim[("note", t)] and z_nim[("note_tani", t)] for t in typy),
        {t: (z_nim[("note", t)], z_nim[("note_tani", t)]) for t in typy})
sprawdz("i dostaja ich po rowno (roznica najwyzej o jeden)",
        all(abs(z_nim[("note", t)] - z_nim[("note_tani", t)]) <= 1 for t in typy),
        {t: (z_nim[("note", t)], z_nim[("note_tani", t)]) for t in typy})

print()
print("=== 4. DZIENNIK DOSTAJE NAZWE MODELU ===")
zapisane = {}


def atrapa_dziennika(rodzaj, wynik, **szczegoly):
    zapisane["rodzaj"] = rodzaj
    zapisane.update(szczegoly)


ORYG_DOPISZ = browser.dopisz_wynik
ORYG_SESJA = browser.wymagaj_sesji
ORYG_PODLACZ = browser.podlacz_sie
ORYG_WYSLAC = browser.naprawde_wyslac
try:
    browser.dopisz_wynik = atrapa_dziennika
    browser.wymagaj_sesji = lambda *a, **k: None
    # DARMOWY TEST NIE MA PRAWA PUBLIKOWAC i `naprawde_wyslac` slusznie na to
    # nie pozwala — ale wtedy gałąź zapisu do dziennika w ogole sie nie wykonuje.
    # Podmieniamy WYLACZNIE te decyzje, zeby wejsc w prawdziwa sciezke;
    # przegladarka i tak jest atrapa, wiec nic nie ma dokad wyjsc.
    browser.naprawde_wyslac = lambda wyslij, co: True

    class _Strona:
        """Padnie DOPIERO w `goto`, czyli juz wewnatrz `try` — inaczej `finally`
        z zapisem do dziennika nigdy by sie nie wykonalo."""

        def goto(self, *a, **k):
            raise RuntimeError("przegladarka niedostepna w tescie")

        def close(self, *a, **k):
            return None

        def __getattr__(self, _):
            return lambda *a, **k: None

    class _Kontekst:
        def new_page(self):
            return _Strona()

        def __getattr__(self, _):
            return lambda *a, **k: None

    browser.podlacz_sie = lambda *a, **k: (_Kontekst(), _Kontekst(), _Kontekst())
    with io.StringIO() as cichy:
        import contextlib
        with contextlib.redirect_stdout(cichy):
            try:
                browser.wystaw_notke("tekst probny", wyslij=True, typ="MYSL",
                                     forma="PROSTA", model="deepseek-v4-pro")
            except Exception:
                pass
    sprawdz("wpis w dzienniku niesie pole `model`",
            zapisane.get("model") == "deepseek-v4-pro", zapisane.get("model"))
    sprawdz("i nadal niesie typ oraz forme",
            zapisane.get("typ") == "MYSL" and zapisane.get("forma") == "PROSTA",
            (zapisane.get("typ"), zapisane.get("forma")))
finally:
    browser.dopisz_wynik = ORYG_DOPISZ
    browser.wymagaj_sesji = ORYG_SESJA
    browser.podlacz_sie = ORYG_PODLACZ
    browser.naprawde_wyslac = ORYG_WYSLAC

print()
print("=== 5. RUN.PY PRZEKAZUJE MODEL Z KANDYDATA ===")
_run = pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8")
sprawdz("`wystaw_notke` dostaje model wybranego kandydata",
        'model=gotowe[0].get("model", "")' in _run)

print()
print("=== PRODUKCJA ===")
zle = 0
for p in PILNOWANE:
    ok = odcisk(p) == PRZED[str(p)]
    zle += 0 if ok else 1
    print("  %-28s %s" % (pathlib.Path(p).name,
                          "nie istnial i nie istnieje" if odcisk(p) == "brak"
                          else ("bez zmian" if ok else "ZMIENIONA")))

config.przywroc_katalog_danych(STARE_SCIEZKI)
print()
print("=== WYNIK: %d zdanych, %d oblanych%s ===" %
      (zdane, oblane, ", PRODUKCJA RUSZONA" if zle else ""))
sys.exit(1 if (oblane or zle) else 0)
