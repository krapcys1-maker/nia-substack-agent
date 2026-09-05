# -*- coding: utf-8 -*-
"""MYSL nie dziedziczy wymogow briefu zbudowanego wokol karty dowodowej.

## Wada, ktora ten plik pilnuje

MYSL to jedyny typ notki BEZ karty dowodowej — jego opis mowi wprost: "NO
EVIDENCE CARD, and therefore NO FACTS: no number, no date, no named company
(...) nothing a reader could look up and find false".

Szedl mimo to przez `notka.md`, ktora jest zbudowana wokol karty i stawia
cztery wymagania niewykonalne bez faktow:

  1. "Break a belief the reader is carrying (...) If you cannot write that
     sentence, this material is trivia" — obalenie wymaga udokumentowanego
     przekonania;
  2. "Every fact comes from the evidence below" — nie ma zadnego "below";
  3. wolno otworzyc pytaniem tylko wtedy, gdy druga polowa odpowiada na nie
     "with a specific piece of evidence";
  4. JSON zada pol `fact_used` i `source_url`.

Czwarte jest najgorsze i dlatego ma tu wlasna sekcje. `fact_used` istnieje
jako ZAPORA PRZED ZMYSLENIEM: model ma nazwac fakt, na ktorym stoi notka.
Postawiona przed typem, ktoremu faktow miec nie wolno, ta sama zapora staje
sie zaproszeniem do wymyslenia faktu — zapora dziala tylko wtedy, gdy jest co
nazwac.

ZMIERZONE NA ZYWO (DeepSeek V4 Flash, 2026-09-05, ten sam material dla obu
promptow): stary brief oddal `fact_used: "No fact used"` — model wypelnil
obowiazkowe pole atrapa, bo puste nie bylo dozwolone. Trzy przebiegi na kazdy
brief: wyjscie srednio 3383 zetony (stary) wobec 1934 (nowy), koszt $0,0024
wobec $0,0014.

## Czego ten plik pilnuje w DRUGA strone

Zeby rozdzielenie nie zabralo `fact_used` POZOSTALYM typom, gdzie zapora
dziala jak nalezy. Sekcja 2 to sprawdza.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_mysl_ma_swoj_brief.py
"""
import pathlib
import sys

sys.path.insert(0, "agent-v2")

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


MYSL = pathlib.Path("agent-v2/prompts/mysl.md").read_text(encoding="utf-8")
NOTKA = pathlib.Path("agent-v2/prompts/notka.md").read_text(encoding="utf-8")
KOD = pathlib.Path("agent-v2/stages.py").read_text(encoding="utf-8")

print("=== 1. BRIEF MYSLI NIE ZADA NICZEGO, CZEGO MYSL NIE MA ===")
sprawdz("nie zada pola fact_used",
        '"fact_used"' not in MYSL, "jest w JSON-ie")
sprawdz("nie zada pola source_url",
        '"source_url"' not in MYSL, "jest w JSON-ie")
sprawdz("nie kaze obalac przekonania czytelnika",
        "Break a belief" not in MYSL)
sprawdz("nie mowi, ze kazdy fakt pochodzi z dowodow ponizej",
        "Every fact comes from the evidence below" not in MYSL)
sprawdz("i mowi WPROST, czemu tych pol nie ma",
        "no `fact_used` field" in MYSL)

print()
print("=== 2. KONTRDOWOD: POZOSTALE TYPY ZAPORE ZACHOWUJA ===")
# Bez tej sekcji test przechodzilby takze wtedy, gdyby ktos skasowal
# `fact_used` ze WSZYSTKICH briefow — a tam, gdzie karta istnieje, to pole
# jest jedynym miejscem, w ktorym model musi wskazac palcem swoj fakt.
sprawdz("notka.md nadal zada fact_used", '"fact_used"' in NOTKA)
sprawdz("notka.md nadal zada source_url", '"source_url"' in NOTKA)
sprawdz("i nadal kaze obalac przekonanie", "Break a belief" in NOTKA)

print()
print("=== 3. KOD NAPRAWDE ROZDZIELA TE DWA BRIEFY ===")
sprawdz("jest galaz po typie MYSL",
        'if str(note_type).upper() == "MYSL":' in KOD)
sprawdz("i wola mysl.md z nazwa wpisana wprost",
        '_prompt(\n            "mysl.md",' in KOD)
sprawdz("a notka.md nadal ma swoje wywolanie",
        '_prompt(\n            "notka.md",' in KOD)
# NAZWA PLIKU MUSI BYC LITERALEM — na tym stoi mapa pochodzenia pol
# w `test_bariera_wstrzykniecia`. Probowalem `_prompt(_szablon, ...)`
# i `_prompt("mysl.md", **pola)`; tamten test zlapal oba skroty.
sprawdz("i nigdzie nie ma nazwy szablonu spod zmiennej",
        "_prompt(_szablon" not in KOD)

print()
print("=== 4. MYSL NIE DOSTAJE FORMY WYMAGAJACEJ FAKTOW ===")
# Druga polowa tej samej wady: brief mogl byc czysty, a przydzial i tak
# kazalby otworzyc notke liczba. Pilnuje tego `test_forma_pasuje_do_typu`,
# tutaj tylko kotwica, zeby obie polowy nie rozjechaly sie po cichu.
import config  # noqa: E402
sprawdz("LICZBA i LISTA sa dla MYSLI zamkniete",
        not ({"LICZBA", "LISTA"} & set(config.formy_dla_typu("MYSL"))),
        config.formy_dla_typu("MYSL"))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
