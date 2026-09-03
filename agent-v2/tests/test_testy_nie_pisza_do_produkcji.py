# -*- coding: utf-8 -*-
"""Darmowy test nie ma prawa dopisywac do produkcyjnych danych.

CO BYLO ZLE, zmierzone na serwerze 2 wrzesnia 2026. Plik
`agent-v2/data/tematy_przegrane.json` mial 400 wpisow — czyli dokladnie sufit
`ILE_PRZEGRANYCH_TRZYMAMY` — z czego 294 to byly ATRAPY Z TESTOW:

    49 x "A"
    49 x "B"
    49 x "The Soap That Says Antibacterial"
    49 x "The Wipe That Says Flushable"
    49 x "Example Article Six"
    49 x "The Chatbot That Remembers You"

Droga byla krotka i niewidoczna: `test_wybor_tematu.py` wola `stages.pick_topic`,
ta wola `zapisz_przegranych`, a sciezka szla ze stalej modulowej liczonej
z `config.DATA_DIR`. Zaden test tego nie zauwazyl, bo zaden nie pytal.
Wykrylo to dopiero porownanie odciskow WSZYSTKICH 68 plikow w `agent-v2/data/`
przed uruchomieniem zestawu i po nim — jeden plik na 68, ale ten jeden byl
dziennikiem, ktory w trzech czwartych skladal sie z atrap.

Szkoda byla wylacznie diagnostyczna: nic tego pliku nie czyta przy decyzjach.
Ale dziennik diagnostyczny wypelniony atrapami nie jest diagnostyka, tylko
falszywym poczuciem, ze cos sie mierzy. I prawdziwe przegrane tematy zostaly
z bufora bezpowrotnie wypchniete.

CZEGO TEN TEST PILNUJE: nie tego jednego pliku, tylko REGULY. `config.W_TESCIE`
rozpoznaje darmowy test po sciezce uruchomionego programu, a `zapisz_przegranych`
odmawia zapisu, gdy cel lezy w prawdziwym katalogu danych.

BEZ PYTESTA, zero sieci, zero platnych wywolan, produkcja nietknieta.
Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_testy_nie_pisza_do_produkcji.py
"""
import io
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import config      # noqa: E402
import stages      # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


PRZEGRANI = [{"title": "A", "why": "atrapa"}, {"title": "B", "why": "atrapa"}]
PRAWDZIWA_SCIEZKA = stages.PRZEGRANE_TEMATY

print("=== 1. TEN PROCES JEST ROZPOZNANY JAKO DARMOWY TEST ===")
sprawdz("`config.W_TESCIE` jest prawdziwe", config.W_TESCIE is True,
        "argv[0]=%r" % sys.argv[0])

print()
print("=== 2. ZAPIS DO PRODUKCYJNEGO DZIENNIKA JEST ODMOWIONY ===")
# Mierzymy PO SKUTKU, nie po tym, ze funkcja cos wypisala: bierzemy odcisk
# prawdziwego pliku przed i po.
przed = (PRAWDZIWA_SCIEZKA.read_bytes()
         if PRAWDZIWA_SCIEZKA.exists() else b"(nie ma)")
ile = stages.zapisz_przegranych(list(PRZEGRANI))
po = (PRAWDZIWA_SCIEZKA.read_bytes()
      if PRAWDZIWA_SCIEZKA.exists() else b"(nie ma)")
sprawdz("oddaje zero dopisanych", ile == 0, ile)
sprawdz("i plik produkcyjny jest BIT W BIT taki sam", przed == po,
        "dlugosc %d -> %d" % (len(przed), len(po)))

print()
print("=== 3. ALE DO KATALOGU TESTOWEGO PISZE NORMALNIE ===")
# Inaczej zapora bylaby nie ochrona, tylko wylaczeniem funkcji w testach —
# i nikt nigdy nie zmierzylby, czy `zapisz_przegranych` w ogole dziala.
katalog = pathlib.Path(tempfile.mkdtemp(prefix="przegrani-test-"))
stary = stages.PRZEGRANE_TEMATY
stages.PRZEGRANE_TEMATY = katalog / "tematy_przegrane.json"
try:
    ile = stages.zapisz_przegranych(list(PRZEGRANI))
    sprawdz("dopisane do katalogu testowego", ile == len(PRZEGRANI), ile)
    sprawdz("plik naprawde powstal", stages.PRZEGRANE_TEMATY.exists())
    if stages.PRZEGRANE_TEMATY.exists():
        dane = json.loads(io.open(stages.PRZEGRANE_TEMATY, encoding="utf-8").read())
        wpisy = dane if isinstance(dane, list) else (dane.get("tematy") or [])
        sprawdz("i niesie oba tematy", len(wpisy) == len(PRZEGRANI), len(wpisy))
finally:
    stages.PRZEGRANE_TEMATY = stary

print()
print("=== 4. ROZPOZNAWANIE PRODUKCYJNEJ SCIEZKI ===")
prawdziwy = config.AGENT_DIR / "data"
for opis, sciezka, oczekiwane in (
    ("prawdziwy katalog danych", prawdziwy / "tematy_przegrane.json", True),
    ("katalog tymczasowy", katalog / "tematy_przegrane.json", False),
    ("podkatalog produkcji", prawdziwy / "articles" / "x.json", False),
):
    sprawdz("%-26s -> produkcja: %s" % (opis, oczekiwane),
            stages._pisze_do_produkcji(sciezka) is oczekiwane)

print()
print("=== 5. KONTRDOWOD: BEZ ZAPORY ZAPIS BY POSZEDL ===")
# Gdyby odmowa brala sie z czegos innego niz nasza zapora (np. z pustej listy),
# test przechodzilby, nie mierzac niczego. Opuszczamy flage i sprawdzamy, ze
# ta sama sciezka kodu NAPRAWDE pisze — do katalogu testowego, nie do produkcji.
stages.PRZEGRANE_TEMATY = katalog / "kontrdowod.json"
config.W_TESCIE = False
try:
    ile = stages.zapisz_przegranych(list(PRZEGRANI))
finally:
    config.W_TESCIE = True
    stages.PRZEGRANE_TEMATY = PRAWDZIWA_SCIEZKA
sprawdz("z opuszczona flaga funkcja pisze", ile == len(PRZEGRANI), ile)

print()
print("=== 6. PRODUKCJA NIETKNIETA PRZEZ CALY TEN PLIK ===")
koniec = (PRAWDZIWA_SCIEZKA.read_bytes()
          if PRAWDZIWA_SCIEZKA.exists() else b"(nie ma)")
sprawdz("prawdziwy dziennik bit w bit jak na starcie", przed == koniec,
        "dlugosc %d -> %d" % (len(przed), len(koniec)))

print()
print("=" * 62)
print("ZDANE: %d    OBLANE: %d" % (zdane, oblane))
sys.exit(1 if oblane else 0)
