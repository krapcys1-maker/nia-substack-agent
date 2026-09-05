# -*- coding: utf-8 -*-
"""Sciezka artykulu czyta ocene „na artykul", za ktora zaplacilismy.

## Wada, ktora ten plik pilnuje

Sedzia banku dostaje w prompcie polecenie zaznaczenia, ktore fakty uniosa
dluga forme, i `na_artykul` jest zapisywane przy KAZDYM wpisie indeksu. Nie
czytal go nikt:

  * `wez_kandydatow` sortowalo po `(not z_kanalu, ranga)`;
  * `artykul_z_puli.wybierz_fakt` bralo pierwszy fakt bez kolizji z historia.

Platna ocena szla wiec do pliku i tam zostawala. Zmierzone na PRAWDZIWYM
banku z przebiegu finansowego (4 wpisy, jeden oznaczony `na_artykul=True`):
stara kolejnosc oddawala definicje ujawnienia o kontynuacji dzialalnosci
(`na_artykul=False`, ranga 0), nowa oddaje rotacje firm audytorskich w UE —
czyli ten jeden wpis, ktory sedzia uznal za material na dluga forme.

## Czego ten plik pilnuje w DRUGA strone

PREFERENCJA, NIE FILTR. Gdy zaden kandydat nie jest oznaczony, artykul ma
powstac mimo to: doktryna tego repo mowi wprost, ze po oplaconym researchu
tekst MUSI powstac, a odsiew do zera zamienilby brak oceny w brak artykulu.
Sekcja 3. I sekcja 2: sciezka NOTEK ma zostac nietknieta, bo tam ranga jest
wlasciwym kryterium.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_artykul_bierze_kandydata_na_artykul.py
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import config  # noqa: E402

config.uzyj_katalogu_danych(pathlib.Path(tempfile.mkdtemp()))
import stages  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


def wpis(nazwa, ranga, art, kanal=False):
    return {"fact": nazwa, "status": "nowy", "ranga": ranga,
            "na_artykul": art, "z_kanalu": kanal,
            "wrong_belief": "x" * 20, "actually": "y" * 20,
            "decision": "z" * 20, "url": "https://example.org/a",
            "epoka": getattr(config, "EPOKA_KONTA", None)}


def poloz(wpisy):
    for w in wpisy:
        w["status"] = "nowy"
    stages._zapisz_indeks(list(wpisy))


# Kolejnosc jak w prawdziwym banku: najlepsza ranga NIE jest kandydatem
# na artykul — inaczej test przechodzilby przypadkiem.
BANK = [wpis("Definicja ujawnienia, ranga najlepsza", 0, False),
        wpis("Rotacja firm audytorskich w UE", 2, True),
        wpis("Zerwanie kowenantu kredytowego", 3, False),
        wpis("Inspekcje PCAOB 2025", 1, False)]

print("=== 1. SCIEZKA ARTYKULU BIERZE OZNACZONEGO ===")
poloz(BANK)
w = stages.wez_kandydatow(4, na_artykul=True)
sprawdz("pierwszy ma na_artykul=True", w[0].get("na_artykul") is True,
        (w[0].get("fact"), w[0].get("na_artykul")))
sprawdz("i nie jest to ten o najlepszej randze",
        w[0].get("ranga") != 0, w[0].get("ranga"))

print()
print("=== 2. SCIEZKA NOTEK NIETKNIETA ===")
# KONTRDOWOD: bez tej sekcji test przechodzilby takze wtedy, gdyby ktos
# przestawil na `na_artykul` CALY bank — a wtedy notki dostawalyby material
# dobierany pod inna forme.
poloz(BANK)
n = stages.wez_kandydatow(4)
sprawdz("notki nadal biora po randze", n[0].get("ranga") == 0,
        (n[0].get("fact"), n[0].get("ranga")))
sprawdz("czyli inny wpis niz artykul", n[0].get("fact") != w[0].get("fact"))

print()
print("=== 3. BRAK OZNACZONYCH NIE ZATRZYMUJE ARTYKULU ===")
BEZ = [wpis("Pierwszy", 0, False), wpis("Drugi", 1, False)]
poloz(BEZ)
b = stages.wez_kandydatow(2, na_artykul=True)
sprawdz("artykul i tak dostaje material", len(b) == 2, len(b))
sprawdz("w kolejnosci rangi", b[0].get("ranga") == 0, b[0].get("ranga"))

print()
print("=== 4. KANAL NADAL ROZSTRZYGA REMIS WSROD OZNACZONYCH ===")
DWA = [wpis("Oznaczony bez kanalu", 0, True, kanal=False),
       wpis("Oznaczony z kanalu", 5, True, kanal=True),
       wpis("Nieoznaczony z kanalu", 0, False, kanal=True)]
poloz(DWA)
d = stages.wez_kandydatow(3, na_artykul=True)
sprawdz("pierwszy jest oznaczony", d[0].get("na_artykul") is True, d[0].get("fact"))
sprawdz("i sposrod oznaczonych wygral ten z kanalu",
        d[0].get("z_kanalu") is True, d[0].get("fact"))

print()
print("=== 5. KOD ARTYKULU NAPRAWDE O TO PROSI ===")
ZR = pathlib.Path("agent-v2/artykul_z_puli.py").read_text(encoding="utf-8")
sprawdz("wybierz_fakt wola z na_artykul=True",
        "stages.wez_kandydatow(ile, na_artykul=True)" in ZR)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
