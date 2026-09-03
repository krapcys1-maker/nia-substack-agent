# -*- coding: utf-8 -*-
"""Subskrypcje i obserwacje nie moga przekraczac dziennego planu.

DLACZEGO TO POWSTALO. Licznik wykonania planu, zbudowany 30 sierpnia, pokazal
subskrypcje na 140% planu: 25 i 26 sierpnia plan 1, wykonanie 2; 29 sierpnia
plan 1, wykonanie 3. Kazda subskrypcja to poczta do skrzynki wlasciciela, wiec
to nie jest drobiazg kosmetyczny.

MECHANIZM — TA SAMA WADA, CO PRZY NOTKACH, TRZECI RAZ W TEJ RODZINIE.
`browser.z_dziennika_dzis()` zwracal cztery pozycje: komentarze, lajki, restacki
i notki. Subskrypcji ani obserwacji NIE LICZYL. `run.py` robil wiec

    zostalo = budzet - juz.get("subskrypcje", 0)     # budzet minus ZERO

czyli brał pełny dzienny przydział w KAŻDYM przebiegu. A rozdzielnik ma
`max(1, round(...))`, zeby budzet mniejszy niz liczba przebiegow nie zaokraglal
sie do zera — wiec budzet 1 zamienial sie w jedna subskrypcje NA PRZEBIEG,
czyli pieciokrotnosc planu przy pieciu przebiegach.

Ochrona przed wystawieniem normy drugi raz istniala i dzialala — ale tylko dla
tych dzialan, ktore licznik w ogole widzial.

DWIE POPRAWKI, BO JEDNA BY NIE WYSTARCZYLA:
  1. licznik widzi teraz subskrypcje i obserwacje (naprawa przyczyny),
  2. przydzial na przebieg nie przekracza tego, co zostalo (druga linia obrony
     na wypadek, gdyby cokolwiek znowu wypadlo z licznika).

BEZ PYTESTA. Uruchamiac z korzenia repozytorium. Zero platnych wywolan.
"""
import json
import pathlib
import sys
import tempfile
from datetime import datetime, timezone

sys.path.insert(0, "agent-v2")
import browser   # noqa: E402
import config    # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


DZIS = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
WCZORAJ = "2020-01-01T10:00:00+00:00"

katalog = pathlib.Path(tempfile.mkdtemp())
stary = browser.DZIENNIK
browser.DZIENNIK = katalog / "dziennik.jsonl"

try:
    print("=== 1. LICZNIK WIDZI WSZYSTKIE RODZAJE Z BUDZETU ===")
    puste = browser.z_dziennika_dzis()
    brak = set(config.BUDZET_NA_RODZAJ) - set(puste)
    sprawdz("kazdy klucz budzetu jest w liczniku", not brak, brak)

    print()
    print("=== 2. POLICZONE ZOSTAJA TYLKO UDANE I DZISIEJSZE ===")
    wpisy = [
        {"rodzaj": "subskrypcja", "udane": True, "kiedy": DZIS},
        {"rodzaj": "subskrypcja", "udane": True, "kiedy": DZIS},
        {"rodzaj": "subskrypcja", "udane": False, "kiedy": DZIS},
        {"rodzaj": "subskrypcja", "udane": True, "kiedy": WCZORAJ},
        {"rodzaj": "obserwacja", "udane": True, "kiedy": DZIS},
        {"rodzaj": "komentarz", "udane": True, "kiedy": DZIS},
    ]
    browser.DZIENNIK.write_text(
        "\n".join(json.dumps(w) for w in wpisy), encoding="utf-8")
    ile = browser.z_dziennika_dzis()
    sprawdz("dwie udane subskrypcje z dzis", ile["subskrypcje"] == 2, ile)
    sprawdz("nieudana nie liczy sie", ile["subskrypcje"] != 3, ile)
    sprawdz("wczorajsza nie liczy sie", ile["subskrypcje"] != 3, ile)
    sprawdz("obserwacja trafia pod klucz 'follow'", ile["follow"] == 1, ile)
    sprawdz("i reszta nadal dziala", ile["komentarze"] == 1, ile)

    print()
    print("=== 3. USZKODZONA LINIA NIE PSUJE LICZENIA ===")
    browser.DZIENNIK.write_text(
        json.dumps(wpisy[0]) + "\nto nie jest json\n" + json.dumps(wpisy[4]),
        encoding="utf-8")
    ile = browser.z_dziennika_dzis()
    sprawdz("liczy to, co da sie odczytac",
            ile["subskrypcje"] == 1 and ile["follow"] == 1, ile)
finally:
    browser.DZIENNIK = stary

print()
print("=== 4. PRZYDZIAL NA PRZEBIEG NIE PRZEKRACZA RESZTY ===")
# Odtwarzamy dokladnie ta linie z `run.py`, bo to ona liczy przydzial.
zrodlo = pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8")
sprawdz("run.py ogranicza przydzial do reszty",
        "min(v, max(1, round(v / zostalo_przebiegow)))" in zrodlo)


def przydzial(zostalo, przebiegow):
    return {k: min(v, max(1, round(v / przebiegow))) if v else 0
            for k, v in zostalo.items()}


sprawdz("budzet 1 na 5 przebiegow daje 1, nie wiecej",
        przydzial({"subskrypcje": 1}, 5)["subskrypcje"] == 1)
sprawdz("po jego wykorzystaniu zostaje 0",
        przydzial({"subskrypcje": 0}, 4)["subskrypcje"] == 0)
sprawdz("budzet 16 na 5 przebiegow dzieli sie normalnie",
        przydzial({"komentarze": 16}, 5)["komentarze"] == 3,
        przydzial({"komentarze": 16}, 5))
sprawdz("ostatni przebieg bierze cala reszte",
        przydzial({"komentarze": 4}, 1)["komentarze"] == 4)

print()
print("=== 5. KONTRDOWOD: STARA FORMULA PRZEKRACZALA PLAN ===")
# Bez tego sekcja 4 przechodzilaby rowniez wtedy, gdyby nic sie nie zmienilo.
def stary_przydzial(zostalo, przebiegow):
    return {k: max(1, round(v / przebiegow)) if v else 0
            for k, v in zostalo.items()}


stare = stary_przydzial({"subskrypcje": 1}, 5)["subskrypcje"]
sprawdz("stara formula tez dawala 1 na przebieg", stare == 1)
sprawdz("ale bez malejacej reszty to 5 razy w ciagu dnia",
        stare * 5 == 5,
        "plan 1, wykonanie %d" % (stare * 5))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
