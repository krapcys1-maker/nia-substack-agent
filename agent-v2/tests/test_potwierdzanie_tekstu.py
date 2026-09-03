# -*- coding: utf-8 -*-
"""Potwierdzenie musi znalezc nasz tekst, gdy edytor podmieni apostrofy.

CO SIE DZIALO. Dwanascie komentarzy na sto i dwanascie odpowiedzi na
piecdziesiat trzy konczylo sie w dzienniku jako „Substack nie potwierdzil,
ze wyszlo". Sprawdzone NA ZYWO 31 sierpnia 2026 — trzy takie odpowiedzi:

    note 326237724  NASZA ODPOWIEDZ JEST: TAK
    note 326230402  NASZA ODPOWIEDZ JEST: TAK
    note 325184756  NASZA ODPOWIEDZ JEST: TAK

Wszystkie trzy BYLY na Substacku. Nie zawodzilo wystawianie, tylko
POTWIERDZANIE.

PRZYCZYNA: porownanie doslowne pierwszych 60 znakow. Piszemy prosty apostrof,
a ProseMirror zapisuje typograficzny — `doesn't` nigdy nie trafialo w
`doesn’t`.

ZMIERZONE, NIE ZGADNIETE:
    nieudane: 75% ma apostrof albo cudzyslow w pierwszych 60 znakach
    udane:    17%

KOSZT BYL PODWOJNY. Dziennik pokazywal porazki, ktorych nie bylo, wiec
wykonanie planu wygladalo gorzej niz jest — a to ta sama liczba, na ktorej
stoi alarm „agent robi mniej, niz deklaruje".

Nie grozilo natomiast podwojnym komentarzem: `juz_sie_odezwalismy` pyta
Substacka, a nie naszej ksiegowosci. Sprawdzone osobno.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo.
"""
import pathlib
import sys

sys.path.insert(0, "agent-v2")
import browser  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


APOSTROF = chr(0x2019)      # '
CUDZ_L = chr(0x201C)        # "
CUDZ_P = chr(0x201D)        # "
MYSLNIK = chr(0x2014)       # —
WIELOKROPEK = chr(0x2026)   # …
NIELAMIACA = chr(0x00A0)

print("=== 1. PRAWDZIWY PRZYPADEK Z PRODUKCJI ===")
# Doslowny tekst odpowiedzi, ktora poszla, a zostala zapisana jako nieudana.
nasz = "I'm not claiming linear scaling in either direction."
ich = "I" + APOSTROF + "m not claiming linear scaling in either direction."
sprawdz("doslownie NIE pasuje — to jest ta wada", nasz not in ich)
sprawdz("po normalizacji pasuje",
        browser.plaski(nasz) in browser.plaski(ich))

print()
print("=== 2. POZOSTALE PODMIANY EDYTORA ===")
for opis, u_nas, u_nich in (
        ("cudzyslowy", '"just."', CUDZ_L + "just." + CUDZ_P),
        ("myslnik", "reasoning - it makes", "reasoning " + MYSLNIK + " it makes"),
        ("wielokropek", "and so on...", "and so on" + WIELOKROPEK),
        ("spacja nielamiaca", "the agent state", "the" + NIELAMIACA + "agent state")):
    sprawdz("  %s" % opis,
            browser.plaski(u_nas) in browser.plaski(u_nich),
            (u_nas, u_nich))

print()
print("=== 3. NORMALIZACJA NIE ZMIENIA ZNACZENIA ===")
# Gdyby sprowadzala wszystko do jednego, potwierdzalaby CUDZE teksty.
sprawdz("rozne zdania nadal rozne",
        browser.plaski("Sharing weights doesn't help")
        not in browser.plaski("Sharing data does help"))
sprawdz("puste wejscie nie wywala", browser.plaski(None) == "")
sprawdz("wielokrotne spacje sklejone",
        browser.plaski("a   b" + chr(10) + " c") == "a b c")

print()
print("=== 4. WPIETE WE WSZYSTKIE CZTERY POTWIERDZENIA ===")
# Notka, artykul, odpowiedz i komentarz porownywaly tekst tak samo — wiec
# wszystkie cztery mialy te sama slabosc.
zrodlo = pathlib.Path("agent-v2/browser.py").read_text(encoding="utf-8")
sprawdz("probki skladane przez `plaski`",
        zrodlo.count("probka = plaski(") == 4,
        zrodlo.count("probka = plaski("))
sprawdz("nie zostalo stare porownanie po samych spacjach",
        'probka = " ".join(tekst.split())' not in zrodlo
        and 'probka = " ".join(tytul.split())' not in zrodlo)
# I DRUGA STRONA POROWNANIA TEZ. Normalizacja tylko naszego tekstu nic nie da,
# bo to Substack wstawia znaki typograficzne.
# `plaski(_json.dumps` STALO TU DO 1 WRZESNIA 2026 i zniklo NIE dlatego, ze
# normalizacja przestala byc potrzebna, tylko dlatego, ze zniknal caly ten
# sposob sprawdzania. `potwierdz_odpowiedz` zamienialo odpowiedz API z powrotem
# na napis przez `json.dumps` i szukalo w nim naszego tekstu — a numer naszego
# komentarza, lezacy w tej samej odpowiedzi, przestawal przy tym byc danymi.
# Kosztowalo to 43 udane komentarze bez pola `nasz_id`. Dzis ta funkcja chodzi
# po `commentBranches` jak `potwierdz_komentarz` i normalizuje przez
# `plaski(c.get("body"))`, ktore ta lista sprawdza nizej.
for gdzie in ("plaski(tresc)", "plaski(x.get(", "plaski(c.get("):
    sprawdz("  druga strona tez normalizowana: %s" % gdzie, gdzie in zrodlo)
# WASKO, BO `json.dumps` MA W TYM PLIKU UCZCIWA PRACE — zapisuje dziennik,
# pamiec i liste platnych hostow (szesc miejsc). Zakaz dotyczy jednego idiomu:
# POROWNYWANIA tresci z odpowiedzia API zamieniona w napis. Pierwsza wersja tej
# asercji zabraniala `json.dumps` w ogole i oblewala na wlasnym zapisie pliku.
sprawdz("  i nikt nie porownuje tresci z odpowiedzia przepuszczona przez napis",
        "plaski(_json.dumps" not in zrodlo and "plaski(json.dumps" not in zrodlo,
        "numer komentarza znowu przestaje byc danymi")

print()
print("=== 5. KONTRDOWOD: BEZ NORMALIZACJI TEST MUSI POLEC ===")
# Gdyby porownanie po samych spacjach wystarczalo, ta poprawka bylaby zbedna.
po_staremu = " ".join(nasz.split())[:60] in " ".join(ich.split())
sprawdz("stare porownanie nie znajduje tekstu, ktory TAM JEST",
        not po_staremu)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
