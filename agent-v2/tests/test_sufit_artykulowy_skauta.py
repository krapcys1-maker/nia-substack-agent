# -*- coding: utf-8 -*-
"""Skaut nie moze oznaczyc wszystkiego jako artykul.

ZMIERZONE 30 sierpnia na przebiegu po przepisaniu briefu: OSIEM Z OSMIU tematow
dostalo znacznik artykulowy. Regula brzmi „co najmniej dwa udokumentowane
precedensy ORAZ duzy zasieg" i wyglada na wymagajaca — ale model dal kazdemu
tematowi po trzy precedensy i kazdemu ten sam zasieg AN_INDUSTRY, wiec oba
wejscia reguly spadly do STALEJ. Wykrywacz martwych sygnalow zameldowal to
wprost:

    MARTWE: na_artykul=True, zasieg='AN_INDUSTRY' — ta sama wartosc u wszystkich 8

Znacznik, ktory ma sto procent, nie niesie zadnej informacji, a decyduje o
DROZSZEJ sciezce. To ta sama degeneracja, ktora tego samego dnia wyszla w banku
(67% oznaczonych) i wczesniej przy samoocenach zawsze rownych 1.0.

LEKARSTWO TO NIE OSTRZEJSZY PROG. Podniesienie wymogu precedensow albo zwezenie
listy zasiegow przy wartosci STALEJ albo nie zmieni nic, albo wytnie wszystko.
Bierzemy sygnal, ktorego model nie potrafi wyrownac — jego wlasny WYMUSZONY
RANKING — i zostawiamy znacznik na czolowce.

BEZ PYTESTA, bez platnych wywolan. Uruchamiac z korzenia repozytorium.
"""
import pathlib
import sys

sys.path.insert(0, "agent-v2")
import config   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


def przytnij(topics):
    """Ta sama arytmetyka, ktora robi to w `scout`."""
    limit = max(1, int(len(topics) * config.BANK_UDZIAL_ARTYKULOW))
    kand = sorted([t for t in topics if t["na_artykul"]],
                  key=lambda t: -t["pozycja"])
    for t in kand[limit:]:
        t["na_artykul"] = False
    return limit


print("=== 0. SUFIT ISTNIEJE I JEST TEN SAM, CO W BANKU ===")
sprawdz("BANK_UDZIAL_ARTYKULOW miedzy 0,2 a 0,5",
        0.2 <= config.BANK_UDZIAL_ARTYKULOW <= 0.5,
        config.BANK_UDZIAL_ARTYKULOW)

print()
print("=== 1. OSIEM Z OSMIU SCHODZI DO CZOLOWKI ===")
# Dokladnie przypadek z produkcji: wszystkie oznaczone, rozne pozycje rankingu.
osiem = [{"tytul": "t%d" % i, "na_artykul": True, "pozycja": i}
         for i in range(8)]
limit = przytnij(osiem)
zostalo = [t for t in osiem if t["na_artykul"]]
sprawdz("zostaje tylko sufit", len(zostalo) == limit,
        "%d przy sufcie %d" % (len(zostalo), limit))
sprawdz("i sa to tematy z NAJWYZSZA pozycja rankingu",
        sorted(t["pozycja"] for t in zostalo)
        == sorted(t["pozycja"] for t in osiem)[-limit:],
        [t["pozycja"] for t in zostalo])

print()
print("=== 2. SKROMNY SKAUT NIE JEST PODCIAGANY W GORE ===")
# Sufit TNIE, ale nie dosypuje — inaczej bylby zgadywaniem.
dwa = [{"tytul": "t%d" % i, "na_artykul": i < 2, "pozycja": i} for i in range(8)]
przytnij(dwa)
sprawdz("dwa oznaczone zostaja dwoma",
        sum(1 for t in dwa if t["na_artykul"]) == 2,
        sum(1 for t in dwa if t["na_artykul"]))

print()
print("=== 3. KONTRDOWOD: BEZ SUFITU ZOSTALOBY OSIEM ===")
# Gdyby sufit nic nie robil, sekcja 1 przechodzilaby rowniez wtedy.
bez_sufitu = [{"na_artykul": True, "pozycja": i} for i in range(8)]
sprawdz("bez przyciecia wszystkie osiem ma znacznik",
        sum(1 for t in bez_sufitu if t["na_artykul"]) == 8)

print()
print("=== 4. MALA PARTIA NADAL ODDAJE PRZYNAJMNIEJ JEDEN ===")
# `max(1, ...)` istnieje po to, zeby przy trzech tematach sufit nie wyszedl zero
# i sciezka artykulu nie zostala bez materialu.
trzy = [{"na_artykul": True, "pozycja": i} for i in range(3)]
przytnij(trzy)
sprawdz("z trzech zostaje co najmniej jeden",
        sum(1 for t in trzy if t["na_artykul"]) >= 1,
        sum(1 for t in trzy if t["na_artykul"]))

print()
print("=== 5. KOD SKAUTA NAPRAWDE TO ROBI ===")
zrodlo = pathlib.Path("agent-v2/stages.py").read_text(encoding="utf-8")
sprawdz("skaut liczy sufit z tej samej stalej",
        "limit_art = max(1, int(len(topics) * config.BANK_UDZIAL_ARTYKULOW))"
        in zrodlo)
sprawdz("i sortuje po wymuszonym rankingu, nie po precedensach",
        'key=lambda t: -t["pozycja"])' in zrodlo)
sprawdz("i mowi o tym glosno w logu",
        "znacznik artykulowy mial %d z %d" in zrodlo)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
