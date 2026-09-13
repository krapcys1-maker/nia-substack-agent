# -*- coding: utf-8 -*-
"""Dwie notki jednej partii nie moga byc o tym samym.

## Pomiar, ktory to wywolal

10 wrzesnia 2026. Trzy kolejne generacje notek — kazda osobnym wywolaniem
`personality.notes(ile=1)` — daly TRZY NOTKI O TYM SAMYM: chinscy specjalisci
po studiach uczacy modeli za grosze. Bank nie byl chudy; wszystkie trzy fakty
lezaly obok siebie na tej samej polce.

## Przyczyna, ukladowa a nie przypadkowa

`fakt_na_notke` wolalo `wez_kandydatow(1, ...)` i braolo pozycje pierwsza.

Straznik blizniakow W ISTNIEJE w `wez_kandydatow` i jest dobry — tylko
porownuje kandydatow MIEDZY SOBA w jednej partii. Przy `ile=1` partia ma
jednego czlonka, wiec straznik nie ma czego z czym porownac i nie strzela ani
razu. Trzy wywolania to trzy partie po jednym.

`wybierz_material` robi dokladnie to, czego brakowalo, i istnieje od
17 sierpnia: odrzuca fakt zderzajacy sie z dzisiejszymi notkami, z pamiecia
wszystkich wystawionych i po wspolnej nazwie wlasnej. Sciezka artykulu i
`notki_dnia` przez nia ida. Sciezka z 9 wrzesnia — ta, ktora sam dopisalem —
jej nie wolala.

To ten sam ksztalt wady co dwie notki o grzybach 23 i 24 sierpnia: sygnal
wytworzony i wyrzucony.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_notki_nie_o_tym_samym.py
"""
import sys
from unittest.mock import patch

sys.path.insert(0, "agent-v2")
import stages           # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# Bank jak ten prawdziwy z 10 wrzesnia: trzy pozycje o jednej rzeczy stoja
# obok siebie na gorze, roznorodnosc lezy nizej.
BANK = [
    {"fact": "Chinese graduates with engineering degrees are labelling training"
             " data for AI firms at roughly two dollars an hour, according to"
             " a labour survey.",
     "domain": "labour", "ranga": 0},
    {"fact": "Underemployed Chinese professionals now make up a majority of the"
             " annotation workforce training large language models, the same"
             " survey found.",
     "domain": "labour", "ranga": 1},
    {"fact": "A Chinese data-labelling contractor pays postgraduate annotators"
             " per task rather than per hour, pushing effective pay below the"
             " local minimum wage.",
     "domain": "labour", "ranga": 2},
    {"fact": "The FDA cleared the first autonomous blood-drawing robot for use"
             " in outpatient clinics after a trial on 1,100 patients.",
     "domain": "medicine", "ranga": 3},
    {"fact": "A petabyte-scale genomic dataset was released to researchers"
             " without the consent framework its donors were promised.",
     "domain": "genomics", "ranga": 4},
    {"fact": "A bill in Congress would require disclosure of compute spend"
             " above a threshold for any model offered to the public.",
     "domain": "policy", "ranga": 5},
]

print("=== 1. TRZY NOTKI POD RZAD NIE WYCHODZA O TYM SAMYM ===")
zwrocone = []
wydane = []


def _wez(ile=1, **_kw):
    """Atrapa banku: oddaje `ile` pierwszych WOLNYCH, jak prawdziwa."""
    wolni = [k for k in BANK if k not in wydane]
    partia = wolni[:ile]
    wydane.extend(partia)
    return partia


def _zwroc(kandydaci):
    zwrocone.append(list(kandydaci))          # PARTIAMI, nie na jedna kupe
    for k in kandydaci:
        if k in wydane:
            wydane.remove(k)
    return len(kandydaci)


stages.zapomnij_fakty_przebiegu()
with patch.object(stages, "wez_kandydatow", _wez), \
     patch.object(stages, "zwroc_kandydatow", _zwroc), \
     patch.object(stages, "pamiec_wystawionych", lambda: []), \
     patch.object(stages, "teksty_ostatnich_notek", lambda *a, **k: []):
    wybory = [stages.fakt_na_notke() for _ in range(3)]

for i, w in enumerate(wybory, 1):
    print("     %d. %s" % (i, (w or {}).get("fact", "BRAK")[:72]))

sprawdz("kazda notka dostala fakt", all(w for w in wybory))
dziedziny = [(w or {}).get("domain") for w in wybory]
sprawdz("trzy rozne dziedziny, nie trzy razy jedna",
        len(set(dziedziny)) == 3, dziedziny)
# TO JEST TA WPADKA: pierwsza i druga pozycja banku to ta sama rzecz.
sprawdz("druga notka NIE wziela sasiada z tej samej polki",
        (wybory[1] or {}).get("domain") != (wybory[0] or {}).get("domain"),
        "%s / %s" % (dziedziny[0], dziedziny[1]))

print()
print("=== 2. NIEWYKORZYSTANI WRACAJA DO BANKU ===")
# Sciezka artykulu spalila kiedys 32 oplacone kandydatury na cztery teksty,
# bo `wez_kandydatow` znaczy jako uzyte WSZYSTKO, co wyda.
sprawdz("zwrot w ogole sie odbyl", bool(zwrocone))
sprawdz("kazda z trzech notek cos zwrocila", len(zwrocone) == 3, len(zwrocone))
sprawdz("wrocilo wiecej, niz zuzylismy",
        sum(len(p) for p in zwrocone) >= 3)
# PARAMI, NIE NA JEDNA KUPE. Kandydat zwrocony przy notce pierwszej i uzyty
# przy drugiej JEST w obu listach i to jest poprawne — bank ma go oddac,
# a nastepna notka ma prawo po niego siegnac. Wada bylaby wtedy, gdyby ten
# sam wybor zostal w tym samym wywolaniu i wydany, i zwrocony.
for nr, (wybor, partia) in enumerate(zip(wybory, zwrocone), 1):
    sprawdz("  notka %d: wybrany nie wrocil do banku" % nr,
            wybor is not None and not any(k is wybor for k in partia))

print()
print("=== 3. PAMIEC WYDANYCH ISTNIEJE I DA SIE JA WYCZYSCIC ===")
# Pamiec permanentna zna tylko notki, ktore JUZ WYSZLY. Partia pisze sie
# w calosci przed pierwsza publikacja, wiec przy drugiej notce dziennik
# jeszcze o pierwszej nie wie — to jedyne miejsce, ktore o niej wie.
sprawdz("lista wydanych w tym przebiegu istnieje",
        hasattr(stages, "_FAKTY_TEGO_PRZEBIEGU"))
sprawdz("i po trzech notkach ma trzy pozycje",
        len(stages._FAKTY_TEGO_PRZEBIEGU) == 3,
        len(stages._FAKTY_TEGO_PRZEBIEGU))
stages.zapomnij_fakty_przebiegu()
sprawdz("czyszczenie dziala", not stages._FAKTY_TEGO_PRZEBIEGU)

print()
print("=== 4. BANK CHUDY NADAL ODDAJE NOTKE ===")
# Kontrdowod: ochrona przed powtorka nie ma prawa zabic notki. Gdy bank ma
# jedna pozycje, ma ja oddac — notka z rubryki bez faktu jest gorsza, ale
# BRAK NOTKI jest najgorszy.
stages.zapomnij_fakty_przebiegu()
with patch.object(stages, "wez_kandydatow", lambda *a, **k: [BANK[0]]), \
     patch.object(stages, "zwroc_kandydatow", lambda k: len(k)), \
     patch.object(stages, "pamiec_wystawionych", lambda: []), \
     patch.object(stages, "teksty_ostatnich_notek", lambda *a, **k: []):
    jeden = stages.fakt_na_notke()
sprawdz("jedyny kandydat wychodzi, a nie przepada", bool(jeden))

print()
print("=== 5. PUSTY BANK TO NADAL NOTKA Z RUBRYKI, NIE AWARIA ===")
stages.zapomnij_fakty_przebiegu()
with patch.object(stages, "wez_kandydatow", lambda *a, **k: []):
    sprawdz("pusty bank oddaje None bez wyjatku",
            stages.fakt_na_notke() is None)
with patch.object(stages, "wez_kandydatow",
                  lambda *a, **k: (_ for _ in ()).throw(RuntimeError("zepsuty plik"))):
    sprawdz("zepsuty bank tez oddaje None bez wyjatku",
            stages.fakt_na_notke() is None)

print()
print("=== 6. WYBOR IDZIE PRZEZ ISTNIEJACY MECHANIZM, NIE PRZEZ NOWY ===")
import ast, io   # noqa: E402
ZRODLO = io.open("agent-v2/stages.py", encoding="utf-8").read()
CIALO = ""
for w in ast.walk(ast.parse(ZRODLO)):
    if isinstance(w, ast.FunctionDef) and w.name == "fakt_na_notke":
        CIALO = ast.get_source_segment(ZRODLO, w) or ""
sprawdz("wola wybierz_material", "wybierz_material(" in CIALO)
sprawdz("podaje pamiec wystawionych", "pamiec_wystawionych()" in CIALO)
sprawdz("podaje teksty ostatnich notek", "teksty_ostatnich_notek()" in CIALO)
sprawdz("bierze wiecej niz jednego kandydata",
        "wez_kandydatow(\n            6," in CIALO or "wez_kandydatow(6" in CIALO
        or "        wziete = wez_kandydatow(\n            6," in CIALO,
        CIALO[CIALO.find("wez_kandydatow"):][:60])
sprawdz("i zwraca reszte", "zwroc_kandydatow(" in CIALO)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
