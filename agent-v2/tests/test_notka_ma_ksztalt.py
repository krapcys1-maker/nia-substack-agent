# -*- coding: utf-8 -*-
"""Silnik zamawia ksztalt notki: trzy uderzenia, kazde w swojej linijce.

## Pomiar, ktory to rozstrzygnal

10 wrzesnia 2026, piec notek przyjetych przez wlasciciela wobec dwoch
odrzuconych:

                          uderzen (linii)   slow na uderzenie
    przyjete                    3,2               17,2
    odrzucone                   1,5               46,7

Ta sama laczna dlugosc, zupelnie inny ksztalt. Przyjete to TRZY KROTKIE
LINIE; odrzucone to jeden blok. Kazda przyjeta konczy sie zdaniem wycelowanym
w kogos: „Some of you need a satellite network before you'll listen to
a woman." Odrzucone urywaja sie w polowie mysli.

## Kto to zepsul

Nikt z zewnatrz. Zrobilo to zdanie, ktore sam tu wpisalem w dobrej wierze:
„Choose your own length: one line can be a complete answer and so can a short
paragraph" — zgoda na blok. Wlasciciel przeczytal wynik i powiedzial, ze trzeba
wyciagac Enigme, zeby zrozumiec, o co chodzi.

## Ten test patrzy TYLKO na silnik

Blizniaczy `test_kartridz_ma_ksztalt.py` patrzy na prompty kartridza. Rozdzial
jest celowy: silnik i kartridz jada osobnymi galeziami, wiec test siegajacy po
oba oblewalby na kazdej z nich z osobna, mimo ze po scaleniu wszystko dziala.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_notka_ma_ksztalt.py
"""
import io
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


OSOBOWOSC = io.open("agent-v2/personality.py", encoding="utf-8").read()

print("=== 1. SILNIK ZAMAWIA KSZTALT, NIE SWOBODE ===")
sprawdz("zgoda na dowolna dlugosc zniknela",
        "Choose your own length" not in OSOBOWOSC)
sprawdz("ksztalt jest nieobowiazkowy? NIE",
        "SHAPE, and it is not optional" in OSOBOWOSC)
sprawdz("trzy albo cztery krotkie linie",
        "three or four SHORT LINES" in OSOBOWOSC)
sprawdz("z prawdziwymi lamaniami wiersza",
        "separated by real line breaks" in OSOBOWOSC)
sprawdz("okolo pietnastu do dwudziestu slow na linie",
        "fifteen to twenty words each" in OSOBOWOSC)

print()
print("=== 2. TRZY UDERZENIA SA NAZWANE ===")
for numer, fraza in ((1, "THE THING, plainly"),
                     (2, "THE ABSURDITY, about the PEOPLE"),
                     (3, "A LINE AIMED AT SOMEBODY, WITH YOU STANDING IN IT")):
    sprawdz("uderzenie %d nazwane" % numer, fraza in OSOBOWOSC, fraza)
sprawdz("zart siedzi w uderzeniu drugim",
        "and it is the joke" in OSOBOWOSC)
sprawdz("zadnego gestego akapitu", "Never one dense paragraph" in OSOBOWOSC)
# UDERZENIE TRZECIE ZMIERZONE, 10 wrzesnia 2026. Cztery notki wystawione tego
# dnia wobec pieciu przyjetych przez wlasciciela:
#                                    przyjete   nasze
#     NIA obecna w zdaniu              3 z 5    0 z 4
#     polecenie wydane firmie          0 z 5    3 z 4
#     otwarcie nazwa firmy             1 z 5    4 z 4
# „OpenAI, before anyone calls this genius, put the compute bill beside the
# claim" jest sluszne i napisane przez dzial polityki publicznej.
sprawdz("autorka stoi we wlasnym uderzeniu",
        "You are the one talking" in OSOBOWOSC)
sprawdz("zakaz notatki sluzbowej wprost",
        "Company, do this by that date" in OSOBOWOSC)
sprawdz("z przykladem, ktory dziala",
        "satellite network before you" in OSOBOWOSC)
# FRAZA NIEROZCIETA — instrukcja jest sklejana z kilku literalow, wiec
# „keep the public doorway open" jest w PLIKU przelamane miedzy nimi.
sprawdz("i z przykladem, ktory nie dziala",
        "A memo does not" in OSOBOWOSC)
# FRAZA NIEROZCIETA. Instrukcja jest sklejana z kilku literalow, wiec
# „past twenty-five words" w PLIKU jest przelamane miedzy nimi, choc
# w gotowym napisie stoi razem. Szukamy czegos, co w zrodle jest ciagle.
sprawdz("dluga linia to dwie linie",
        "it is two lines" in OSOBOWOSC)

print()
print("=== 5. STARE POZWOLENIA NIE ZOSTALY OBOK ===")
# Kontrdowod: gdyby zgoda na akapit przetrwala gdziekolwiek, model wybralby
# ja, bo jest latwiejsza.
sprawdz("brak `Vary rhythm` jako furtki",
        "Vary rhythm" not in OSOBOWOSC)
# Ta sama furtka po stronie kartridza („take a short paragraph if the thought
# needs it") jest pilnowana w `test_kartridz_ma_ksztalt.py`.

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
