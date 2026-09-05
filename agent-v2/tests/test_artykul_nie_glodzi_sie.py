# -*- coding: utf-8 -*-
"""Artykul tygodniowy nie moze przepasc przez limit ustawiony dla notek.

## Wada, ktora ten plik pilnuje

Zmierzone na zegarze produkcyjnym: notki chodza o 07:00, 11:20, 17:00, 19:20,
21:30 i 23:40; artykul we WTOREK o 14:00. Dwa przebiegi notek ida wiec PRZED
artykulem.

`SZUKANIE_BANKU_NA_DOBE = 1` to jedno szukanie na dobe, liczone z tabeli
`calls` i wspolne dla wszystkiego. Artykul nie mial z niego zadnego
zwolnienia — sprawdzone drzewem skladni: stala miala trzy wystapienia i zadne
nie rozrozniało wolajacego.

Skutek przy pustym banku we wtorek:

    fakty = stages.wez_kandydatow(ile)          # spizarnia pusta
    fakty = stages.znajdz_ciekawostki(...)      # oddaje [] przez limit
    raise ValueError("pula ciekawostek pusta")  # NIE MA ARTYKULU W TYM TYGODNIU

`zalegly_artykul` tego nie ratuje: on ratuje tekst, ktory POWSTAL, a tutaj nie
powstalo nic.

Rachunek byl odwrotny do zamierzonego. Limit oszczedzal jedno szukanie
(~0,06 USD wejscia) i potrafil kosztowac caly artykul (~1,50 USD plus tydzien
publikacji). Pusty bank we wtorek nie jest egzotyka — wystarczy tydzien,
w ktorym notki zjadly zapas, albo odsiew blizniakow odrzucil reszte.

## Czego ten plik pilnuje w DRUGA strone

Zeby zwolnienie nie rozlalo sie na notki. Tam limit ma sens: pusty zapas
kosztuje jedna notke z pieciu, a nie caly tydzien. Test bez tej drugiej
polowy przechodzilby takze wtedy, gdyby ktos zwolnil z limitu wszystko.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_artykul_nie_glodzi_sie.py
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import config  # noqa: E402

config.uzyj_katalogu_danych(pathlib.Path(tempfile.mkdtemp()))

import db       # noqa: E402
import stages   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


CONN = db.connect()

# Stan, ktory zabijal artykul: limit dobowy WYCZERPANY, bank pusty.
stages._przebiegi_z_bankiem_dzis = lambda c: config.SZUKANIE_BANKU_NA_DOBE
stages.bank_pelny = lambda: False


class DoszloDoSzukania(Exception):
    """Rzucane zamiast platnego wywolania — znaczy „doszlo tak daleko"."""


def _zapora(*a, **k):
    raise DoszloDoSzukania()


stages.llm = type("Atrapa", (), {
    "call": staticmethod(_zapora),
    "parse_json": staticmethod(lambda x: {}),
})()


def probuj(**kw) -> str:
    """'szukalo' albo 'nie szukalo' — bez wydania grosza."""
    try:
        stages.znajdz_ciekawostki(CONN, 1, ile=3, **kw)
    except DoszloDoSzukania:
        return "szukalo"
    except Exception as exc:                                     # noqa: BLE001
        # `znajdz_ciekawostki` lapie wyjatki modelu u siebie i oddaje pusta
        # liste, wiec „doszlo do szukania" poznajemy po LICZNIKU, nie po
        # wyjatku, ktory do nas nie dolatuje.
        return "blad: %s" % type(exc).__name__
    return "nie szukalo"


print("=== 1. SCIEZKA ARTYKULU SZUKA MIMO WYCZERPANEGO LIMITU ===")
# Licznik, bo funkcja lapie wyjatki modelu u siebie.
licznik = {"n": 0}
_stary = stages.llm.call


def _liczaca(*a, **k):
    licznik["n"] += 1
    raise DoszloDoSzukania()


stages.llm = type("Atrapa", (), {
    "call": staticmethod(_liczaca),
    "parse_json": staticmethod(lambda x: {}),
})()

licznik["n"] = 0
stages.znajdz_ciekawostki(CONN, 1, ile=3, na_artykul=True)
sprawdz("artykul doszedl do szukania", licznik["n"] > 0, licznik["n"])

print()
print("=== 2. SCIEZKA NOTEK NADAL RESPEKTUJE LIMIT ===")
# KONTRDOWOD NA POPRAWCE: bez tego test przechodzilby takze wtedy, gdyby ktos
# zwolnil z limitu wszystko, a wtedy piec przebiegow dziennie szukaloby piec
# razy i limit przestalby cokolwiek znaczyc.
licznik["n"] = 0
wynik = stages.znajdz_ciekawostki(CONN, 1, ile=3)
sprawdz("notki NIE doszly do szukania", licznik["n"] == 0, licznik["n"])
sprawdz("i oddaly pusta liste", wynik == [], wynik)

print()
print("=== 3. PELNY BANK NIE ZATRZYMUJE ARTYKULU — I TAK MA BYC ===")
# TA ASERCJA BYLA NAJPIERW ODWROTNA i to test mial racje, ze zapytal, ale JA
# mialem zla odpowiedz. Napisalem „pelny bank zatrzymuje takze artykul", test
# oblal, i dopiero wtedy przesledzilem sciezke do konca.
#
# Artykul dochodzi do `znajdz_ciekawostki` WYLACZNIE wtedy, gdy `wez_kandydatow`
# oddalo nic. Jesli bank jest przy tym „pelny" (>= BANK_MAKS_WOLNYCH wolnych),
# to znaczy, ze te wpisy sa nie do uzycia: przeterminowane albo zderzone jako
# blizniaki. Bank pelny NIEUZYTECZNEGO materialu to nie jest powod, zeby
# odpuscic tygodniowy artykul.
#
# Odwrotnie tez sie zgadza: gdy bank jest pelny i UZYTECZNY, `wez_kandydatow`
# odda material i do tej linii nikt nie dojdzie. Zwolnienie nie kupuje wiec
# ani jednego zbednego szukania.
stages.bank_pelny = lambda: True
licznik["n"] = 0
stages.znajdz_ciekawostki(CONN, 1, ile=3, na_artykul=True)
sprawdz("pelny, ale nieuzyteczny bank nie blokuje artykulu",
        licznik["n"] > 0, licznik["n"])
# A notki przy pelnym banku nadal nie szukaja — tam pelny bank znaczy „jest
# z czego brac", bo notki nie przechodza przez `wez_kandydatow` po drodze tutaj.
licznik["n"] = 0
wynik = stages.znajdz_ciekawostki(CONN, 1, ile=3)
sprawdz("a notki przy pelnym banku nadal nie szukaja",
        licznik["n"] == 0 and wynik == [], (licznik["n"], wynik))
stages.bank_pelny = lambda: False

print()
print("=== 4. SCIEZKA ARTYKULU NAPRAWDE PODAJE TE FLAGE ===")
# Bez tego wszystko wyzej moze byc prawda, a produkcja i tak glodzi artykul —
# bo `artykul_z_puli` wolalby bez `na_artykul`.
zrodlo = pathlib.Path("agent-v2/artykul_z_puli.py").read_text(encoding="utf-8")
sprawdz("artykul_z_puli wola z na_artykul=True",
        "na_artykul=True" in zrodlo)
sprawdz("i robi to przy znajdz_ciekawostki",
        "znajdz_ciekawostki" in zrodlo
        and "na_artykul=True" in zrodlo.split("znajdz_ciekawostki", 1)[1][:200])

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
