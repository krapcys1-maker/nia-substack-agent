# -*- coding: utf-8 -*-
"""Konta raz zmierzone jako za duze nie zjadaja okna przegladania co dzien.

## Pomiar

11 wrzesnia 2026, czternastu kandydatow z prawdziwej puli, sufit tysiaca
obserwujacych:

    @rubendominguez        353 727
    @bytebytego399569       44 668
    @moderndata101          17 303
    @thetechbubble          15 673
    @valuemomentumportfolio 10 069
    @yournamangupta          3 131
    @systematicstrategies    2 545
    @arthurandthefuture      1 939
    --- miesci sie ---
    @omoore                    149
    @becomingabuilder           35
    @sjbuildswithai              4

Osmiu za duzych, trzech w naszym rozmiarze, trzech bez profilu. Sito dzialalo
poprawnie. Zjadali jednak okno CI SAMI ludzie, mierzeni od nowa kazdej doby —
a subskrypcje staly na zerze przez trzy doby.

## Regula

Konto zmierzone na 353 tysiace nie zejdzie ponizej tysiaca do jutra. Pamietamy
ten pomiar z dziennika i stawiamy takich kandydatow NA KONCU kolejki.

## Czego NIE robimy

Nie skreslamy nikogo na zawsze — przesuwamy. Gdy w puli nie ma nikogo innego,
wracaja i dostaja normalne sprawdzenie rozmiaru.

Nie pamietamy tez „nie ma profilu publicznego (404)". Brak profilu bywa
chwilowy, a „nie wiem" nie jest pomiarem i nie ma sie zapisywac jak pomiar.

BEZ PYTESTA, bez sieci, bez przegladarki. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_pula_subskrypcji_pamieta_rozmiar.py
"""
import ast
import io
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, "agent-v2")
import browser          # noqa: E402
import run              # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


print("=== 1. JEDEN NAPIS, NIE TRZY KOPIE ===")
# Rozjechanie sie tych literalow wylaczyloby odsiew po cichu — ta sama
# pulapka, ktora opisuje `kogo_juz_subskrybujemy`.
sprawdz("stala istnieje w browser", hasattr(browser, "POWOD_ZA_DUZY"))
ZR_RUN = io.open("agent-v2/run.py", encoding="utf-8").read()
# PRZEZ MODUL, NIE PRZEZ IMPORT NA GORZE. `from browser import ...` w `run.py`
# wywracalo import calego modulu tam, gdzie test podstawia atrape pod `browser`
# — zlapane na `test_komentarz_potwierdzony` tego samego dnia.
sprawdz("run siega po nia przez modul",
        ZR_RUN.count("browser.POWOD_ZA_DUZY") >= 2,
        ZR_RUN.count("browser.POWOD_ZA_DUZY"))
sprawdz("i nie importuje jej na gorze",
        "from browser import POWOD_ZA_DUZY" not in ZR_RUN)
ZR_BR = io.open("agent-v2/browser.py", encoding="utf-8").read()
literal = "\"account exceeds the size limit or its size is unknown\""
sprawdz("napis nie jest juz wpisany w run.py", literal not in ZR_RUN)
# W browser.py zostaje RAZ: w definicji stalej. Drugie wystapienie jest
# w komentarzu opisujacym awarie z 8 wrzesnia i to jest cytat, nie kod.
drzewo = ast.parse(ZR_BR)
literaly = [w for w in ast.walk(drzewo)
            if isinstance(w, ast.Constant) and isinstance(w.value, str)
            and w.value == browser.POWOD_ZA_DUZY]
sprawdz("w browser.py dokladnie jeden literal w kodzie",
        len(literaly) == 1, len(literaly))

print()
print("=== 2. DZIENNIK ODDAJE ZMIERZONYCH ZA DUZYCH ===")
with tempfile.TemporaryDirectory() as kat:
    plik = Path(kat) / "dziennik.jsonl"
    wpisy = [
        {"rodzaj": "subskrypcja_pominieta", "komu": "rubendominguez",
         "powod": browser.POWOD_ZA_DUZY},
        {"rodzaj": "subskrypcja_pominieta", "komu": "@Moderndata101",
         "powod": browser.POWOD_ZA_DUZY},
        {"rodzaj": "obserwacja_pominieta", "komu": "thetechbubble",
         "powod": browser.POWOD_ZA_DUZY},
        # 404 to NIE pomiar — nie ma go zapamietac.
        {"rodzaj": "subskrypcja_pominieta", "komu": "jamwithai",
         "powod": "nie ustalilem konta autora dla jamwithai.substack.com"},
        # Udana subskrypcja to inna sprawa, pilnuje jej `kogo_juz_subskrybujemy`.
        {"rodzaj": "subskrypcja", "komu": "omoore", "udane": True},
    ]
    plik.write_text("\n".join(json.dumps(w) for w in wpisy) + "\n",
                    encoding="utf-8")
    with patch.object(browser, "DZIENNIK", plik):
        duzi = run.znane_za_duze()
    sprawdz("zapamietani za duzi", duzi == {"rubendominguez", "moderndata101",
                                            "thetechbubble"}, sorted(duzi))
    sprawdz("malpa i wielkosc liter nie maja znaczenia",
            "moderndata101" in duzi)
    sprawdz("brak profilu NIE jest pamietany", "jamwithai" not in duzi)
    sprawdz("udana subskrypcja to nie rozmiar", "omoore" not in duzi)

print()
print("=== 3. BRAK DZIENNIKA TO PUSTA WIEDZA, NIE AWARIA ===")
with tempfile.TemporaryDirectory() as kat:
    with patch.object(browser, "DZIENNIK", Path(kat) / "nie-ma.jsonl"):
        sprawdz("pusty zbior bez wyjatku", run.znane_za_duze() == set())
with tempfile.TemporaryDirectory() as kat:
    plik = Path(kat) / "dziennik.jsonl"
    plik.write_text("{to nie jest json\n\n{}\n", encoding="utf-8")
    with patch.object(browser, "DZIENNIK", plik):
        sprawdz("zepsute linie pomijane", run.znane_za_duze() == set())

print()
print("=== 4. BLOK SUBSKRYPCJI PRZESUWA, A NIE WYRZUCA ===")
CIALO = ""
for w in ast.walk(ast.parse(ZR_RUN)):
    if isinstance(w, ast.FunctionDef) and w.name == "subskrybuj":
        CIALO = ast.get_source_segment(ZR_RUN, w) or ""
sprawdz("blok pyta o zmierzonych", "znane_za_duze()" in CIALO)
sprawdz("dzieli pule na swiezych i znanych",
        "swiezi" in CIALO and "znani" in CIALO)
sprawdz("i SKLEJA je z powrotem, nie odsiewa",
        "kandydaci = swiezi + znani" in CIALO)
sprawdz("mowi o tym w logu", "ida na koniec kolejki" in CIALO)
# KONTRDOWOD: gdyby to byl odsiew, chuda pula konczylaby sie zerem mimo
# kandydatow, ktorzy mogli w miedzyczasie stracic obserwujacych.
sprawdz("nigdzie nie ma odsiewu po tej liscie",
        "if _slug_hosta(h) not in duzi]" in CIALO
        and "kandydaci = [h for h in kandydaci if _slug_hosta(h) not in duzi]"
        not in CIALO)

print()
print("=== 5. SUFIT NADAL PYTA O AKTUALNY ROZMIAR ===")
# Pamiec przestawia KOLEJNOSC. Decyzje podejmuje nadal publiczny licznik.
sprawdz("sprawdzenie rozmiaru zostalo", "browser.konto_za_duze(uchwyt)" in CIALO)
sprawdz("i nadal nie zjada proby", "bez zuzycia proby" in CIALO)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
