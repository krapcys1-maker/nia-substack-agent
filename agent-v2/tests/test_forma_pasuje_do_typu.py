# -*- coding: utf-8 -*-
"""Notka nie dostaje formy, ktorej jej typ nie ma czym wypelnic.

## Wada, ktora ten plik pilnuje

Forma byla losowana z CALEJ osemki, bez ogladania sie na typ:

    formy = [config.NOTE_FORM_MIX[(_dryf + od + i) % len(config.NOTE_FORM_MIX)]
             for i in range(len(typy))]

Komentarz przy tym wyliczeniu mowi wprost, ze celem jest, by "po osmiu dniach
kazda para typ-forma zdazyla wystapic". Tak sie dzialo — takze dla par, ktorych
wykonac SIE NIE DA:

  * MYSL:   "NO EVIDENCE CARD, and therefore NO FACTS: no number, no date,
             no named company (...) nothing a reader could look up"
  * LICZBA: "Open with the number itself, alone on the first line"
  * LISTA:  "EVERY line must carry a fact the previous line did not"

Model dostawal w jednym prompcie zakaz faktow i nakaz faktu. Zmierzone
symulacja roku kalendarzowego przed poprawka: 273 z 3597 par (7,6%).

## Czego ten plik pilnuje w DRUGA strone

Zeby lekarstwo nie bylo gorsze od choroby. Latwo "naprawic" to tak, ze MYSL
dostaje na stale jedna forme, albo ze wszystkie typy trafiaja do tej samej
zawezonej listy — i monotonia, ktorej dryf mial zapobiegac, wraca innymi
drzwiami. Sekcje 3 i 4 sprawdzaja, ze pozostale typy nie stracily ani jednej
formy i ze kazda ZGODNA para nadal wystepuje.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_forma_pasuje_do_typu.py
"""
import pathlib
import sys
import tempfile
from collections import Counter

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


WYMAGAJA_FAKTOW = ("LICZBA", "LISTA")


def rok(dobierz):
    """Symuluje rok przydzialow. `dobierz(typ, i, dzien, od)` oddaje forme."""
    pary = Counter()
    for dzien in range(1, 366):
        numer = dzien % 7
        mix = (config.NOTE_MIX_ARTICLE_DAY if numer == 6
               else config.NOTE_MIX_OTHER_DAY)
        typy = tuple(mix[(numer + i) % len(mix)] for i in range(len(mix)))
        for od in range(3):
            for i, typ in enumerate(typy):
                pary[(typ, dobierz(typ, i, dzien, od))] += 1
    return pary


print("=== 1. MYSL NIGDY NIE DOSTAJE FORMY WYMAGAJACEJ FAKTOW ===")
teraz = rok(lambda typ, i, d, od:
            config.formy_dla_typu(typ)[(d + od + i) % len(config.formy_dla_typu(typ))])
zle = {k: v for k, v in teraz.items() if k[0] == "MYSL" and k[1] in WYMAGAJA_FAKTOW}
sprawdz("przez caly rok ani razu", not zle, zle)

print()
print("=== 2. KONTRDOWOD: STARA FORMULA TO ROBILA ===")
# Bez tej sekcji test przechodzilby takze wtedy, gdyby ktos usunal MYSL z mixu
# albo LICZBE z form — czyli gdyby "naprawil" objaw, kasujac dane.
staro = rok(lambda typ, i, d, od:
            config.NOTE_FORM_MIX[(d + od + i) % len(config.NOTE_FORM_MIX)])
bylo = sum(v for k, v in staro.items()
           if k[0] == "MYSL" and k[1] in WYMAGAJA_FAKTOW)
wszystkie = sum(staro.values())
sprawdz("stara formula produkowala te pary", bylo > 0, bylo)
print("        (%d z %d par = %.1f%% — tyle znikneło)"
      % (bylo, wszystkie, 100 * bylo / wszystkie))

print()
print("=== 3. POZOSTALE TYPY NIE STRACILY ANI JEDNEJ FORMY ===")
for typ in set(config.NOTE_MIX_OTHER_DAY) | set(config.NOTE_MIX_ARTICLE_DAY):
    dozwolone = config.formy_dla_typu(typ)
    if typ == "MYSL":
        sprawdz("%-12s ma o dwie formy mniej" % typ,
                len(dozwolone) == len(config.NOTE_FORM_MIX) - 2, dozwolone)
    else:
        sprawdz("%-12s ma wszystkie %d form" % (typ, len(config.NOTE_FORM_MIX)),
                len(dozwolone) == len(config.NOTE_FORM_MIX), dozwolone)

print()
print("=== 4. DRYF ZYJE: KAZDA ZGODNA PARA NADAL WYSTEPUJE ===")
brakujace = []
for typ in set(config.NOTE_MIX_OTHER_DAY) | set(config.NOTE_MIX_ARTICLE_DAY):
    for forma in config.formy_dla_typu(typ):
        if teraz[(typ, forma)] == 0:
            brakujace.append((typ, forma))
sprawdz("zadna zgodna para nie wypadla z obiegu", not brakujace, brakujace)

print()
print("=== 5. FORMA LICZONA PO PODMIANIE NA ARTYKUL ===")
# Kolejnosc zaczela miec znaczenie dopiero, gdy forma zaczela zalezec od typu:
# `typy[0]` bywa podmieniane na ARTYKUL, wiec liczac wczesniej, dobieralibysmy
# forme do typu, ktorego juz nie ma.
zrodlo = pathlib.Path("agent-v2/stages.py").read_text(encoding="utf-8")
po_podmianie = zrodlo.split('typy[0] = "ARTYKUL"', 1)
sprawdz("podmiana na ARTYKUL istnieje", len(po_podmianie) == 2)
sprawdz("a formy licza sie PO niej",
        "config.formy_dla_typu(_typ)" in po_podmianie[1])
sprawdz("i nie ma juz starego wyliczenia z calej osemki",
        "config.NOTE_FORM_MIX[(_dryf" not in zrodlo)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
