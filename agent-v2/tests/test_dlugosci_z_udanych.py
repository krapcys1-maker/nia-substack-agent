# -*- coding: utf-8 -*-
"""Statystyka dlugosci wypowiedzi ma liczyc teksty, ktore NAPRAWDE wyszly.

`alarm.przeglad` drukuje sekcje „DLUGOSCI WYPOWIEDZI" i pyta w niej o jedno:
czy nasze wypowiedzi nie sa podejrzanie rowne, bo jednolita dlugosc jest jednym
z tropow bota (`if pstdev < 8: ! ZA ROWNO`).

Do 1 wrzesnia liczyla `slow` ze WSZYSTKICH wpisow dziennika. Dopoki dziennik
zapisywal niemal wylacznie sukcesy, roznica byla zadna. Poprawka z 31 sierpnia
kaze zapisywac porazki z KAZDEJ galezi — a nieudany wpis tez niesie `slow`, bo
tekst zostal napisany i oplacony, tylko nigdzie nie wyszedl. Rozklad zaczal
wiec opisywac dlugosci, ktorych nikt nigdy nie przeczytal.

SKALA: zmierzone 30 sierpnia 2026 — 11 nieudanych komentarzy na 92 proby, czyli
12 procent probki. I nie sa to wpisy losowe: porazki kupia sie na koncu serii
(pierwsza akcja psula sie w 10 procentach, czwarta w 50), a `wystaw_komentarz`
przy wczesnym wyjsciu zapisuje `slow` tekstu, ktory nigdy nie zostal wpisany
w pole. To ta sama klasa wady, ktora naprawialismy w `srednia_wyswietlen`:
mierzyc to, co istnieje. Sasiednia funkcja `alarm._co_z_tego_wyszlo` filtruje
po `udane` od dawna — ta jedna sekcja nie.

TEST NIE RUSZA SIECI ANI PRODUKCYJNEJ BAZY: podstawia dziennik w katalogu
tymczasowym i polaczenie do bazy w pamieci.

BEZ PYTESTA, z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_dlugosci_z_udanych.py
"""
import contextlib
import io
import json
import pathlib
import re
import sqlite3
import sys
import tempfile
import types
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "agent-v2")
import alarm     # noqa: E402
import browser   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


KAT = pathlib.Path(tempfile.mkdtemp())
ORYG_DZIENNIK = browser.DZIENNIK
ORYG_POLACZENIE = alarm._polaczenie


def baza_w_pamieci():
    """Pusta baza z dwiema tabelami, ktorych `przeglad` dotyka na koncu."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE calls (at TEXT, cost_usd REAL)")
    conn.execute("CREATE TABLE runs (status TEXT, started_at TEXT)")
    return conn


alarm._polaczenie = baza_w_pamieci


def wpis(rodzaj, udane, slow):
    return {"kiedy": (datetime.now(timezone.utc)
                      - timedelta(hours=1)).isoformat(timespec="seconds"),
            "rodzaj": rodzaj, "udane": udane, "slow": slow,
            "gdzie": "https://przyklad.com/p/x"}


def zapisz(wpisy):
    plik = KAT / "dziennik.jsonl"
    plik.write_text("\n".join(json.dumps(w) for w in wpisy), encoding="utf-8")
    browser.DZIENNIK = plik


def dlugosci(modul=alarm):
    """Uruchamia `przeglad` i wyciaga z wydruku liczby sekcji DLUGOSCI."""
    bufor = io.StringIO()
    with contextlib.redirect_stdout(bufor):
        modul.przeglad(dni=3)
    tekst = bufor.getvalue()
    m = re.search(r"od (\d+) do (\d+) slow, srednia (\d+)", tekst)
    return (None if not m else
            {"min": int(m.group(1)), "max": int(m.group(2)),
             "srednia": int(m.group(3))}, tekst)


# Trzy UDANE po 40 slow i trzy NIEUDANE po 400. Liczone razem daja srednia 220
# i rozstrzal 40-400; liczone poprawnie — same czterdziestki.
UDANE = [wpis("komentarz", True, 40) for _ in range(3)]
NIEUDANE = [wpis("komentarz", False, 400) for _ in range(3)]

try:
    print("=== 1. NIEUDANE TEKSTY NIE WCHODZA DO ROZKLADU ===")
    zapisz(UDANE + NIEUDANE)
    wynik, tekst = dlugosci()
    print("    zmierzone: %s" % wynik)
    sprawdz("sekcja w ogole sie drukuje (test cokolwiek mierzy)",
            wynik is not None, tekst[-300:])
    sprawdz("srednia liczona tylko z udanych (40, nie 220)",
            wynik and wynik["srednia"] == 40, wynik)
    sprawdz("i rozstrzal tez (40-40, nie 40-400)",
            wynik and (wynik["min"], wynik["max"]) == (40, 40), wynik)

    print()
    print("=== 2. NIEUDANE NADAL SA WIDOCZNE — TYLKO NIE W TEJ STATYSTYCE ===")
    # Poprawka ma odciac je z JEDNEGO zestawienia, nie schowac je z raportu.
    # Sekcja „CO SIE NIE UDALO" to jedyne miejsce, gdzie wlasciciel je widzi.
    sprawdz("licznik rodzajow nadal mowi o nieudanych",
            "NIEUDANYCH: 3" in tekst, tekst[:400])
    sprawdz("i jest osobna sekcja z porazkami",
            "CO SIE NIE UDALO (3)" in tekst, tekst[:600])

    print()
    print("=== 3. SAME PORAZKI = BRAK ROZKLADU, NIE ZMYSLONY ROZKLAD ===")
    # Dzien, w ktorym nic nie wyszlo, nie ma czego mierzyc. Wypisanie
    # „srednia 400 slow" bylo by tam czysta fikcja.
    zapisz(NIEUDANE)
    wynik, tekst = dlugosci()
    sprawdz("brak udanych -> sekcji DLUGOSCI nie ma wcale",
            wynik is None, wynik)
    sprawdz("ale porazki nadal widac", "NIEUDANYCH: 3" in tekst, tekst[:400])

    print()
    print("=== 4. ALARM O ROWNEJ DLUGOSCI LICZY SIE Z TEGO SAMEGO ===")
    # `pstdev < 8` to trop bota. Trzy udane po 40 slow sa rowne — i to ma
    # zapalic ostrzezenie. Doklejenie do nich nieudanych czterysetek rozdymalo
    # odchylenie i GASILO alarm, ktory powinien byl sie zapalic.
    zapisz(UDANE)
    _, tekst_rowne = dlugosci()
    sprawdz("same rowne udane zapalaja ostrzezenie",
            "ZA ROWNO" in tekst_rowne, tekst_rowne[-400:])
    zapisz(UDANE + NIEUDANE)
    _, tekst_mieszane = dlugosci()
    sprawdz("i porazki tego ostrzezenia juz nie gasza",
            "ZA ROWNO" in tekst_mieszane, tekst_mieszane[-400:])

    print()
    print("=== 5. KONTRDOWOD: NA KODZIE SPRZED POPRAWKI WYCHODZILO CO INNEGO ===")
    zrodlo = pathlib.Path("agent-v2/alarm.py").read_text(encoding="utf-8")
    stare = zrodlo.replace(
        '    dlugosci = [w["slow"] for w in wpisy\n'
        '                if w.get("udane") and isinstance(w.get("slow"), int)]',
        '    dlugosci = [w["slow"] for w in wpisy'
        ' if isinstance(w.get("slow"), int)]')
    sprawdz("latka odwrotna ma co cofnac", stare != zrodlo)
    m = types.ModuleType("alarm_sprzed")
    m.__dict__["__name__"] = "alarm_sprzed"
    m.__dict__["__file__"] = "agent-v2/alarm.py"
    exec(compile(stare, "agent-v2/alarm.py", "exec"), m.__dict__)
    m._polaczenie = baza_w_pamieci

    zapisz(UDANE + NIEUDANE)
    wynik_stary, tekst_stary = dlugosci(m)
    print("    STARY KOD: %s" % wynik_stary)
    sprawdz("KONTRDOWOD: stary kod liczyl srednia 220 z tekstow, ktore nie wyszly",
            wynik_stary and wynik_stary["srednia"] == 220, wynik_stary)
    sprawdz("KONTRDOWOD: i rozstrzal 40-400", wynik_stary
            and (wynik_stary["min"], wynik_stary["max"]) == (40, 400),
            wynik_stary)
    sprawdz("KONTRDOWOD: przez co gasil alarm o rownej dlugosci",
            "ZA ROWNO" not in tekst_stary, tekst_stary[-400:])
finally:
    browser.DZIENNIK = ORYG_DZIENNIK
    alarm._polaczenie = ORYG_POLACZENIE

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
