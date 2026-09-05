# -*- coding: utf-8 -*-
"""Piec notek na dobe nie moze byc pieciema notkami tej samej dlugosci.

## Po co ten plik istnieje

W `komentarz.md` i `odpowiedz.md` stala regula:

    Do not write everything at the same length. That uniformity is itself
    a tell — a person's replies range from four words to a paragraph.

NOTEK ONA NIE OBEJMOWALA. Notka dostawala jeden zakres — globalne pasmo
`NOTE_MIN_WORDS`-`NOTE_MAX_WORDS`, czyli 33-64 — identyczny dla wszystkich
pieciu notek dnia. Model celujacy w srodek podanego zakresu produkowal piec
notek o niemal tej samej dlugosci, dzien po dniu. To jest wzor, ktory staly
czytelnik widzi bez szukania.

## Czego ten plik NIE zmienia, i to jest wazne

**Sufitu.** Te 64 slowa sa ZMIERZONE (65-256 slow wyraznie spada w zaangazowaniu),
wiec podniesienie go byloby wymiana pomiaru na przeczucie. Zmienia sie tylko to,
ze pasmo jest uzywane NA CALEJ SZEROKOSCI zamiast w okolicach srodka.

Podzial idzie za tym, CZYM TYP NOTKI JEST, a nie za losowaniem: sprostowanie ma
jedna rzecz do poprawienia i konczy sie szybko, mysl ma sie gdzie obrocic.
Losowanie dalo by rozrzut, ale rozrzut bez powodu — a wtedy dlugosc przestaje
cokolwiek znaczyc.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_dlugosc_notek.py
"""
import sys

sys.path.insert(0, "agent-v2")
import config  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


print("=== 1. KAZDY PRZEDZIAL MIESCI SIE W PASMIE, KTOREGO PILNUJE BRAMKA ===")
# `stages.notatki` sprawdza `NOTE_MIN_WORDS <= words <= NOTE_MAX_WORDS`.
# Przedzial wychodzacy poza to pasmo produkowalby notki odrzucane przez wlasna
# bramke — czyli placilibysmy za tekst, ktory z gory nie ma prawa przejsc.
for typ, (od, do) in sorted(config.DLUGOSC_NOTKI_WG_TYPU.items()):
    sprawdz("  %-14s %d-%d w pasmie %d-%d"
            % (typ, od, do, config.NOTE_MIN_WORDS, config.NOTE_MAX_WORDS),
            config.NOTE_MIN_WORDS <= od <= do <= config.NOTE_MAX_WORDS)

print()
print("=== 2. DZIEN NAPRAWDE DAJE ROZNE DLUGOSCI ===")
zakresy = [config.dlugosc_notki(t) for t in config.NOTE_MIX_OTHER_DAY]
for typ, (od, do) in zip(config.NOTE_MIX_OTHER_DAY, zakresy):
    print("      %-14s %d-%d" % (typ, od, do))
sprawdz("mix daje wiecej niz jeden zakres", len(set(zakresy)) > 1, set(zakresy))
# I ze rozrzut jest ISTOTNY, a nie kosmetyczny: najkrotsza i najdluzsza notka
# dnia maja sie roznic co najmniej o polowe krotszej.
_naj = min(z[0] for z in zakresy)
_najd = max(z[1] for z in zakresy)
sprawdz("najkrotsza i najdluzsza roznia sie o polowe albo wiecej",
        _najd >= _naj * 1.5, "%d vs %d" % (_naj, _najd))

print()
print("=== 3. NIEZNANY TYP DOSTAJE CALE PASMO, NIE WYWALA SIE ===")
# Operator moze dopisac wlasny typ do miksu. Brak wpisu ma znaczyc „bez
# zawezenia", a nie awarie.
sprawdz("nieznany typ -> pasmo globalne",
        config.dlugosc_notki("CZEGOS_TAKIEGO_NIE_MA")
        == (config.NOTE_MIN_WORDS, config.NOTE_MAX_WORDS))
sprawdz("wielkosc liter nie ma znaczenia",
        config.dlugosc_notki("mysl") == config.dlugosc_notki("MYSL"))

print()
print("=== 4. KAZDY TYP Z MIKSU MA SWOJ PRZEDZIAL ===")
# Typ w miksie bez wpisu dostaje cale pasmo — czyli wraca dokladnie ta wada,
# ktora ten plik naprawia, tyle ze dla jednego typu i po cichu.
for typ in sorted(set(config.NOTE_MIX_OTHER_DAY)):
    sprawdz("  %s ma wlasny przedzial" % typ,
            typ.upper() in config.DLUGOSC_NOTKI_WG_TYPU)

print()
print("=== 5. KONTRDOWOD: CZY TE SPRAWDZENIA COKOLWIEK LAPIA ===")
_zly = (config.NOTE_MIN_WORDS - 5, config.NOTE_MAX_WORDS + 5)
sprawdz("przedzial poza pasmem bylby widziany",
        not (config.NOTE_MIN_WORDS <= _zly[0] <= _zly[1] <= config.NOTE_MAX_WORDS))
sprawdz("jednakowe zakresy byly by widziane",
        len({(33, 64), (33, 64), (33, 64)}) == 1)
sprawdz("a przyciecie naprawde przycina",
        config.dlugosc_notki("SPROSTOWANIE")[0] >= config.NOTE_MIN_WORDS)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
