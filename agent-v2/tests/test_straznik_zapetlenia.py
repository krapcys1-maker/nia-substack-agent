# -*- coding: utf-8 -*-
"""Straznik zapetlenia: jedyna rzecz miedzy petla a banem konta — i bez testu.

## Po co ten plik istnieje

`alarm.nadaktywnosc()` liczy dzialania z ostatnich 24 godzin i krzyczy, gdy jest
ich wiecej niz sufit. Jego wlasny docstring mowi, ze pierwsza wersja
„nigdy niczego nie zobaczyla": sufit zostal realnie przekroczony dwa razy
(141 dzialan jednego dnia, 81 drugiego), a w pliku alarmow nie ma ani jednego
wpisu. Powod: liczyla kubelek „dzisiaj" kalendarzowo, a alarm chodzi RANO,
zanim ruszy pierwszy przebieg.

Poprawka (okno kroczace) weszla — i nadal nie bylo ani jednego testu na
funkcje, ktora jest jedynym zabezpieczeniem przed banem konta. Ten plik to
nadrabia.

## Druga wada, znaleziona przy czytaniu 4 wrzesnia 2026

Granica okna byla NAPISEM z `isoformat()`, a wpisy porownywano tekstowo.
Napis niesie przesuniecie strefy, ale porownanie tekstowe go nie stosuje —
patrzy na cyfry tak, jak stoja. Zmierzone na obu wersjach obok siebie: wpis
sprzed 23 godzin zapisany w `-05:00` WYPADAL Z OKNA (straznik liczyl mniej, niz
bylo), a wpis sprzed 25 godzin zapisany w `+02:00` do okna wchodzil.

Dzis nic w tym repozytorium nie zapisuje czasu w innej strefie niz UTC — ale to
jest zgoda, ktorej nic nie pilnowalo, w jedynej funkcji stojacej miedzy petla
a banem konta.

## Czego pilnuje

1. WPISY Z OKNA SIE LICZA, SPRZED OKNA NIE.
2. FORMAT ZNACZNIKA CZASU NIE ROZSTRZYGA. Ten sam moment zapisany ze strefa,
   z `Z` i bez strefy ma dac ten sam wynik.
2b. PRZESUNIECIE STREFY INNE NIZ UTC — i to jest wlasciwy kontrdowod na
   porownanie tekstowe, bo punkt 2 nim NIE JEST (przy wpisie sprzed godziny
   obie wersje daja to samo). Zmierzone: wpis sprzed 23 h zapisany w `-05:00`
   WYPADAL Z OKNA, a sprzed 25 h w `+02:00` do niego wchodzil.
3. WPIS Z NIECZYTELNA DATA LICZY SIE. Przy pytaniu „czy cos sie zapetlilo"
   bezpieczniej policzyc za duzo niz za malo — cisza wyglada tak samo jak
   spokoj.
4. NIEUDANE PROBY I `skutek` NIE LICZA SIE. Ban bierze sie z tego, co wyszlo
   w swiat.
5. ALARM MA PROG — sam pod sufitem milczy, tuz nad nim krzyczy.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_straznik_zapetlenia.py
"""
import json
import pathlib
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "agent-v2")
import config  # noqa: E402

# KATALOG DANYCH PODMIENIONY PRZED IMPORTEM `alarm`, bo to on decyduje, ktory
# `dziennik.jsonl` czytamy. Darmowy test nie dotyka produkcyjnych danych.
#
# PRZEZ `uzyj_katalogu_danych`, NIE PRZEZ GOLE PRZYPISANIE. Pierwsza wersja tego
# pliku robila `config.DATA_DIR = _KATALOG` i oblala `test_komplet_sciezek.py`
# sekcja 3 — bramke, ktora ten projekt postawil wlasnie na to: z `DATA_DIR`
# liczy sie CALY komplet sciezek (`DB_PATH`, `ARTICLES_DIR`, stale w innych
# modulach), wiec gole przypisanie przestawia jedna z nich, a reszta dalej
# celuje w produkcje. Bramka zadzialala na swiezym pliku od razu.
_KATALOG = pathlib.Path(tempfile.mkdtemp(prefix="straznik-"))
_STARE_SCIEZKI = config.uzyj_katalogu_danych(_KATALOG)

import alarm  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


TERAZ = datetime.now(timezone.utc)


def wpis(godzin_temu: float, udane=True, rodzaj="notka", format_czasu="strefa"):
    chwila = TERAZ - timedelta(hours=godzin_temu)
    if format_czasu == "strefa":
        kiedy = chwila.isoformat(timespec="seconds")
    elif format_czasu == "zulu":
        kiedy = chwila.replace(tzinfo=None).isoformat(timespec="seconds") + "Z"
    elif format_czasu == "bez_strefy":
        kiedy = chwila.replace(tzinfo=None).isoformat(timespec="seconds")
    else:
        kiedy = format_czasu
    return {"kiedy": kiedy, "rodzaj": rodzaj, "udane": udane}


def zapisz(wpisy):
    plik = _KATALOG / "dziennik.jsonl"
    plik.write_text("".join(json.dumps(w, ensure_ascii=False) + "\n"
                            for w in wpisy), encoding="utf-8")


SUFIT = alarm.max_dzialan_dziennie()

try:
    print("=== 1. OKNO KROCZACE: WPISY Z DOBY LICZA SIE, STARSZE NIE ===")
    zapisz([wpis(1) for _ in range(SUFIT + 5)])
    sprawdz("ponad sufit w ostatniej dobie -> alarm",
            alarm.nadaktywnosc() is not None)
    zapisz([wpis(30) for _ in range(SUFIT + 5)])
    sprawdz("te same wpisy sprzed 30 godzin -> cisza",
            alarm.nadaktywnosc() is None, alarm.nadaktywnosc())

    print()
    print("=== 2. FORMAT ZNACZNIKA CZASU NIE ROZSTRZYGA ===")
    for opis in ("strefa", "zulu", "bez_strefy"):
        zapisz([wpis(1, format_czasu=opis) for _ in range(SUFIT + 5)])
        sprawdz("format %-11s -> alarm" % opis,
                alarm.nadaktywnosc() is not None)
        zapisz([wpis(30, format_czasu=opis) for _ in range(SUFIT + 5)])
        sprawdz("format %-11s, sprzed 30 h -> cisza" % opis,
                alarm.nadaktywnosc() is None)

    print()
    print("=== 2b. PRZESUNIECIE STREFY — TU POROWNANIE TEKSTOWE SIE MYLILO ===")
    # TO JEST WLASCIWY KONTRDOWOD, a trzy sprawdzenia wyzej nim NIE SA:
    # przy wpisie sprzed godziny napis bez strefy i tak wypada po granicy, bo
    # roznica przypada na dzien, a nie na koncowke. Zmierzone na obu wersjach
    # obok siebie:
    #
    #   wpis sprzed 25 h zapisany w +02:00   tekstowo: LICZY   po dacie: nie
    #   wpis sprzed 23 h zapisany w -05:00   tekstowo: nie     po dacie: LICZY
    #
    # Druga linia jest ta grozna: dzialanie sprzed 23 godzin WYPADALO Z OKNA,
    # czyli jedyny straznik miedzy petla a banem liczyl mniej, niz bylo.
    def _w_strefie(godzin_temu, przesuniecie_h):
        chwila = (TERAZ - timedelta(hours=godzin_temu)).astimezone(
            timezone(timedelta(hours=przesuniecie_h)))
        return {"kiedy": chwila.isoformat(timespec="seconds"),
                "rodzaj": "notka", "udane": True}

    zapisz([_w_strefie(23, -5) for _ in range(SUFIT + 5)])
    sprawdz("sprzed 23 h w strefie -05:00 -> alarm (tekstowo: cisza)",
            alarm.nadaktywnosc() is not None)
    zapisz([_w_strefie(25, +2) for _ in range(SUFIT + 5)])
    sprawdz("sprzed 25 h w strefie +02:00 -> cisza (tekstowo: alarm)",
            alarm.nadaktywnosc() is None, alarm.nadaktywnosc())

    print()
    print("=== 3. NIECZYTELNA DATA LICZY SIE, A NIE WYPADA PO CICHU ===")
    zapisz([wpis(1, format_czasu="psu") for _ in range(SUFIT + 5)])
    sprawdz("wpisy z data nie do odczytania -> alarm",
            alarm.nadaktywnosc() is not None)

    print()
    print("=== 4. LICZYMY TO, CO WYSZLO W SWIAT ===")
    zapisz([wpis(1, udane=False) for _ in range(SUFIT + 5)])
    sprawdz("same NIEUDANE proby -> cisza", alarm.nadaktywnosc() is None)
    zapisz([wpis(1, rodzaj="skutek") for _ in range(SUFIT + 5)])
    sprawdz("same wpisy `skutek` -> cisza", alarm.nadaktywnosc() is None)
    zapisz([wpis(1, rodzaj="") for _ in range(SUFIT + 5)])
    sprawdz("wpisy bez rodzaju -> cisza", alarm.nadaktywnosc() is None)

    print()
    print("=== 5. PROG DZIALA W OBIE STRONY ===")
    zapisz([wpis(1) for _ in range(SUFIT)])
    sprawdz("dokladnie sufit -> cisza", alarm.nadaktywnosc() is None,
            alarm.nadaktywnosc())
    zapisz([wpis(1) for _ in range(SUFIT + 1)])
    tresc = alarm.nadaktywnosc()
    sprawdz("sufit + 1 -> alarm", tresc is not None)
    sprawdz("i alarm podaje obie liczby",
            bool(tresc) and str(SUFIT) in tresc and str(SUFIT + 1) in tresc,
            tresc)

    print()
    print("=== 6. BRAK PLIKU TO NIE JEST ALARM ===")
    (_KATALOG / "dziennik.jsonl").unlink()
    sprawdz("bez dziennika -> cisza", alarm.nadaktywnosc() is None)
finally:
    config.przywroc_katalog_danych(_STARE_SCIEZKI)
    shutil.rmtree(_KATALOG, ignore_errors=True)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
