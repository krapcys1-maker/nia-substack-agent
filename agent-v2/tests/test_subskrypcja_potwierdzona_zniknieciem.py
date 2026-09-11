# -*- coding: utf-8 -*-
"""Subskrypcja jest potwierdzona zniknieciem przycisku, nie napisem „Subscribed".

## Pomiar

11 wrzesnia 2026 dwie subskrypcje zapisaly sie jako PORAZKA z powodem „brak
potwierdzenia darmowej subskrypcji na profilu". Sprawdzone tego samego dnia na
zywych profilach, przyciski widziane dokladnie:

    @becomingabuilder   zasubskrybowany dzis   -> ['Manage']
    @mattgrawitch       zasubskrybowany dzis   -> ['Manage']
    @rubendominguez     nigdy nie probowany    -> ['Subscribe', 'Manage']
    @omoore             nigdy nie probowany    -> ['Subscribe', 'Manage']

Obie subskrypcje NAPRAWDE WESZLY. Kod szukal napisu „Subscribed",
„Subskrybujesz", „Subskrybowano" albo „Upgrade" — Substack nie pisze zadnego
z nich.

Skutek byl podwojny: norma pokazywala zero przy dwoch wykonanych, a
`kogo_juz_subskrybujemy` zamyka uchwyt tylko przy `udane=True`, wiec agent
wszedlby na te same profile jeszcze raz.

## Czego pomiar NIE pokazal

Ze „Manage" jest dowodem. Stoi takze na profilach, ktorych NIE subskrybujemy —
kontrdowod obalil pierwsza wersje tej poprawki, zanim weszla. Dowodem jest
BRAK przycisku „Subscribe", i tak samo potwierdza sie juz obserwowanie.

BEZ PYTESTA, bez sieci, bez przegladarki. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_subskrypcja_potwierdzona_zniknieciem.py
"""
import ast
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


ZRODLO = io.open("agent-v2/browser.py", encoding="utf-8").read()
CIALO = ""
for w in ast.walk(ast.parse(ZRODLO)):
    if isinstance(w, ast.FunctionDef) and w.name == "_klik_na_profilu":
        CIALO = ast.get_source_segment(ZRODLO, w) or ""

print("=== 1. POTWIERDZA ZNIKNIECIE PRZYCISKU ===")
sprawdz("funkcja znaleziona", bool(CIALO))
sprawdz("sprawdzamy, czy przycisk jeszcze stoi", "zostal = any(" in CIALO)
sprawdz("i to po napisach, z ktorymi weszlismy",
        "for etykieta in napisy)" in CIALO)
sprawdz("brak przycisku znaczy zrobione", "(not zostal) or any(" in CIALO)

print()
print("=== 2. STARE NAPISY ZOSTAJA JAKO DRUGA DROGA ===")
# Substack moze je kiedys wprowadzic; nowa droga ma DOKLADAC, nie zabierac.
sprawdz("lista pozytywnych napisow zostala",
        "subscription_labels" in CIALO)
for etykieta in ("Subscribed", "Subskrybujesz", "Upgrade"):
    sprawdz("  nadal akceptowany: %s" % etykieta, etykieta in ZRODLO)

print()
print('=== 3. „Manage” NIE JEST DOWODEM ===')
# KONTRDOWOD, ktory obalil pierwsza wersje poprawki: „Manage" stoi takze na
# profilach, ktorych nie subskrybujemy (@rubendominguez, @omoore).
drzewo = ast.parse(ZRODLO)
manage = [w for w in ast.walk(drzewo)
          if isinstance(w, ast.Constant) and isinstance(w.value, str)
          and w.value == "Manage"]
sprawdz('nigdzie nie uznajemy „Manage” za potwierdzenie', not manage,
        len(manage))
sprawdz("ale pomiar zostal zapisany obok kodu",
        "'Subscribe','Manage'" in CIALO and "@becomingabuilder" in CIALO)

print()
print("=== 4. KOMUNIKAT MOWI, CO SIE NAPRAWDE STALO ===")
# „brak potwierdzenia" brzmialo jak „nie wiem". Teraz zdanie nazywa stan.
sprawdz("nowy komunikat nazywa stan",
        "przycisk subskrypcji nadal stoi na profilu" in CIALO)
sprawdz("stary, mylacy komunikat zniknal",
        "brak potwierdzenia darmowej subskrypcji" not in CIALO)

print()
print("=== 5. OBSERWOWANIE ROBILO TO TAK OD POCZATKU ===")
# Ta sama zasada w galezi `else` — i to ona byla wzorem.
sprawdz("obserwowanie potwierdza tak samo",
        'wynik["zrobione"] = k.count() == 0 or not k.is_visible()' in CIALO)

print()
print("=== 6. WYWOLANIE PODAJE TE SAME NAPISY ===")
# Gdyby wywolujacy podal inne napisy niz te, ktorych szukamy po klinieciu,
# potwierdzenie mierzyloby co innego niz klikniecie.
i = ZRODLO.find("_klik_na_profilu(handle, (")
sprawdz('subskrypcja wchodzi z „Subscribe”',
        '_klik_na_profilu(handle, ("Subscribe", "Subskrybuj"), "subskrypcja"'
        in ZRODLO)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
