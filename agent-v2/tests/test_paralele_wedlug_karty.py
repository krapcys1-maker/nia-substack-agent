# -*- coding: utf-8 -*-
"""Artykul nie dostaje polecenia porownania, ktorego karta nie uniesie.

## Wada, ktora ten plik pilnuje

`losowa_liczba_paraleli(glebokosc)` brala TYLKO glebokosc i nigdy nie ogladala
karty. Wagi nie mialy zera na ZADNEJ glebokosci — RICH `{1: 4, 2: 4, 3: 3}`,
reszta `{1: 5, 2: 3}` — a slownik `OPIS_LICZBY_PARALELI` zaczynal sie od
jedynki. Zero bylo wiec nie tyle rzadkie, co NIEWYRAZALNE.

Skutek: artykul z `parallel_mechanisms: []` i tak dostawal polecenie w rodzaju
"ONE parallel, developed properly — two paragraphs on a single other domain".
Model nie ma z czego tego zrobic. Zostaje wymyslenie drugiej dziedziny — czyli
najslabiej udokumentowany fragment tekstu powstaje NA ZAMOWIENIE, a sprawdzacz
faktow lapie go dopiero po oplaceniu calego artykulu.

## Czego ten plik pilnuje w DRUGA strone

Zeby sufit nie zjadl porownan tam, gdzie material jest. Karta z trzema
mechanizmami ma nadal moc dostac trzy; sekcja 3 to sprawdza. Inaczej latwo
"naprawic" wade tak, ze paralele znikaja z artykulow, ktore stac na wiecej.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_paralele_wedlug_karty.py
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import config  # noqa: E402

config.uzyj_katalogu_danych(pathlib.Path(tempfile.mkdtemp()))

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


PROB = 300

print("=== 1. PUSTA KARTA -> ZERO PARALELI, ZAWSZE ===")
wyniki = {config.losowa_liczba_paraleli(g, dostepne=0)[0]
          for g in ("RICH", "SINGLE", "THIN") for _ in range(PROB)}
sprawdz("na kazdej glebokosci wychodzi 0", wyniki == {0}, wyniki)
opis = config.losowa_liczba_paraleli("RICH", dostepne=0)[1]
sprawdz("i zero ma wlasny opis, nie pustke", bool(opis.strip()))
sprawdz("ktory mowi wprost: bez porownania", "NO outside parallel" in opis,
        opis[:60])

print()
print("=== 2. KONTRDOWOD: BEZ SUFITU ZERO NIE WYCHODZI NIGDY ===")
# Bez tej sekcji test przechodzilby takze wtedy, gdyby ktos ustawil zero na
# stale — a wtedy artykul z materialem na trzy porownania nie dostalby zadnego.
bez_sufitu = {config.losowa_liczba_paraleli(g)[0]
              for g in ("RICH", "SINGLE", "THIN") for _ in range(PROB)}
sprawdz("stare wywolanie nadal nie umie oddac zera", 0 not in bez_sufitu,
        sorted(bez_sufitu))
sprawdz("i to wlasnie `dostepne` je zmienia", bez_sufitu != {0}, sorted(bez_sufitu))

print()
print("=== 3. BOGATA KARTA NIE TRACI POROWNAN ===")
trzy = {config.losowa_liczba_paraleli("RICH", dostepne=3)[0] for _ in range(PROB)}
sprawdz("przy trzech mechanizmach wypada takze 3", 3 in trzy, sorted(trzy))
sprawdz("i nigdy wiecej niz karta niesie", max(trzy) <= 3, sorted(trzy))
jeden = {config.losowa_liczba_paraleli("RICH", dostepne=1)[0] for _ in range(PROB)}
sprawdz("przy jednym mechanizmie nigdy nie zamawiamy dwoch", jeden == {1},
        sorted(jeden))

print()
print("=== 4. PISARZ NAPRAWDE PODAJE TEN SUFIT ===")
# Bez tego wszystko wyzej moze byc prawda, a produkcja i tak zamawia paralele
# z powietrza — bo `write` wolalby bez `dostepne`.
zrodlo = pathlib.Path("agent-v2/stages.py").read_text(encoding="utf-8")
sprawdz("write wola z dostepne=", "losowa_liczba_paraleli(\n        glebokosc, dostepne=" in zrodlo)
sprawdz("i liczy je z parallel_mechanisms karty",
        'dostepne=len(card.get("parallel_mechanisms") or [])' in zrodlo)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
