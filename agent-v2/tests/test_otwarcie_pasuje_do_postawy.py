# -*- coding: utf-8 -*-
"""Komentarz nie dostaje otwarcia, ktorego jego postawa nie moze wykonac.

## Wada, ktora ten plik pilnuje

`losowa_postawa()` i `losowe_otwarcie()` byly losowane NIEZALEZNIE, wiec
komentarz potrafil dostac w jednym prompcie dwa polecenia naraz:

    postawa CIEKAWOSC:  "You are not correcting the author"
    otwarcie:           "Start with the objection: say plainly where you
                         part company."

Zmierzone na wagach z `config`: cztery takie pary to 8,2% komentarzy.

Gorsze bylo to, czego nie widac. Otwarcie „Start by naming what the piece got
right, then the part it skipped" JEST ruchem KOREKTA — a KOREKTA ma wage 1,
najnizsza w calej tabeli, i jej wlasny opis mowi dlaczego: „Used by default
it becomes a tic". Waga dawala temu ruchowi 3,1% komentarzy, a otwarcie
zamawialo go w 12,5%: cztery razy czesciej, tylnymi drzwiami, omijajac wage,
ktora istnieje wylacznie po to, zeby ten ruch byl rzadki.

Po poprawce: ruch korekty schodzi do 1,2%, sprzecznych par jest 0%.

## Czego ten plik pilnuje w DRUGA strone

Zeby zadna postawa nie stracila wiekszosci otwarc — inaczej monotonia, ktorej
losowanie mialo zapobiegac, wraca innymi drzwiami. Sekcja 3.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_otwarcie_pasuje_do_postawy.py
"""
import collections
import pathlib
import random
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


print("=== 1. SPRZECZNE PARY NIE POWSTAJA ===")
NIE_ZGADZAJA_SIE = ("SPRZECIW", "KOREKTA")
for postawa in config.POSTAWY_KOMENTARZA:
    wolno = config.otwarcia_dla_postawy(postawa)
    if postawa not in NIE_ZGADZAJA_SIE:
        sprawdz("%-22s nie dostaje otwarcia od sprzeciwu" % postawa,
                config.OTWARCIE_SPRZECIWU not in wolno)
sprawdz("CIEKAWOSC nie dostaje ruchu korekty",
        config.OTWARCIE_KOREKTY not in config.otwarcia_dla_postawy("CIEKAWOSC"))
sprawdz("ZGODA tez nie",
        config.OTWARCIE_KOREKTY not in
        config.otwarcia_dla_postawy("ZGODA_Z_DOPOWIEDZENIEM"))

print()
print("=== 2. WAGA KOREKTY ZNOWU COS ZNACZY ===")
random.seed(7)
N = 100000
lic = collections.Counter()
for _ in range(N):
    postawa, _ = config.losowa_postawa()
    o = config.losowe_otwarcie(postawa)
    if o == config.OTWARCIE_KOREKTY:
        lic["korekta"] += 1
    if o == config.OTWARCIE_SPRZECIWU and postawa not in NIE_ZGADZAJA_SIE:
        lic["sprzeczne"] += 1
udzial = 100.0 * lic["korekta"] / N
print("    ruch korekty przez otwarcie: %.1f%%" % udzial)
sprawdz("ruch korekty znacznie ponizej 12,5%", udzial < 5.0, udzial)
sprawdz("i zadnej sprzecznej pary", lic["sprzeczne"] == 0, lic["sprzeczne"])
# KONTRDOWOD: bez ograniczenia byloby to 1/8 wszystkich przebiegow.
sprawdz("(kontrola: otwarc jest 8, wiec bez reguly byloby 12,5%)",
        len(config.OTWARCIA) == 8, len(config.OTWARCIA))

print()
print("=== 3. ZADNA POSTAWA NIE ZOSTALA ZAGLODZONA ===")
# Latwo „naprawic" sprzecznosci tak, ze postawie zostaje jedno otwarcie —
# i monotonia, ktorej losowanie mialo zapobiegac, wraca innymi drzwiami.
for postawa in config.POSTAWY_KOMENTARZA:
    ile = len(config.otwarcia_dla_postawy(postawa))
    sprawdz("%-22s ma %d z %d otwarc" % (postawa, ile, len(config.OTWARCIA)),
            ile >= len(config.OTWARCIA) - 2, ile)

print()
print("=== 4. KOD NAPRAWDE PODAJE POSTAWE ===")
ZR = pathlib.Path("agent-v2/stages.py").read_text(encoding="utf-8")
sprawdz("comment_on wola losowe_otwarcie(postawa)",
        "config.losowe_otwarcie(postawa)" in ZR)
sprawdz("i robi to PO wylosowaniu postawy",
        ZR.index("postawa, postawa_opis = config.losowa_postawa()")
        < ZR.index("config.losowe_otwarcie(postawa)"))
# `reply_to` postawy nie ma, wiec wola bez argumentu i dostaje pelna osemke —
# to jest stan zastany, nie regres, i ma byc widoczny.
sprawdz("odpowiedz nadal wola bez postawy (nie ma jej)",
        "otwarcie=config.losowe_otwarcie()," in ZR)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
