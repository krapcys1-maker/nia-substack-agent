# -*- coding: utf-8 -*-
"""Skaut wybiera temat artykulu — musi widziec opisy, nie same tytuly.

## Po co ten plik istnieje

`scout` wolal `zaczyn_z_kanalow()` bez argumentow, wiec dostawal DWADZIESCIA
SZESC SAMYCH TYTULOW i z nich wybieral temat najdrozszej formy tego konta.

Ten sam modul mowi o tytulach dwa razy i za kazdym razem to samo:
`tematy_do_porownania` pisze wprost, ze tytul „potrafi nie miec ANI JEDNEGO
slowa wspolnego z tym, o czym artykul naprawde jest", a `oczysc` zdejmuje
z niego obietnice, bo naglowek sprzedaje, a nie opisuje. Skaut dostawal wiec
material, ktory reszta silnika uznaje za niewiarygodny.

## Co to dalo, zmierzone na zywych kanalach 8 wrzesnia 2026

Ten sam skaut, ten sam preset, te same dziewietnascie kanalow, jedna zmiana:

  bez skrotow   wejscie  9190 tok.   wyjscie 24880 tok.   0,01844 USD
  ze skrotami   wejscie 10274 tok.   wyjscie 23580 tok.   0,01782 USD

Wejscie uroslo o 1084 tokeny — tyle, ile przewidywal rachunek. Dwa tematy
z szostki wyszly wylacznie z opisow i nie mialy szans z samego tytulu:
„The token price trap" (dlaczego cena za token nie mowi, ile kosztuje
zadanie) i „Who signs the machine's report?" (policja i raport pisany przez
model).

## Regula, ktorej pilnuje ten test

`scout` prosi o skroty. Bez sieci i bez platnego wywolania: podmieniamy
`zaczyn_z_kanalow` i `llm.call`, i sprawdzamy, o co skaut poprosil.

BEZ PYTESTA. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_skaut_widzi_opisy.py
"""
import json
import sys

sys.path.insert(0, "agent-v2")
import llm       # noqa: E402
import stages    # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# --- ATRAPY: zero sieci, zero pieniedzy ---------------------------------------
zapis = {}


def _zaczyn(ile=26, ze_skrotem=False, max_dni=14, **reszta):
    zapis["ile"] = ile
    zapis["ze_skrotem"] = ze_skrotem
    zapis["max_dni"] = max_dni
    zapis.update(reszta)
    return "- [2026-09-08] Kanal — Tytul\n    Opis pod tytulem."


ODPOWIEDZ = json.dumps({"topics": [{
    "title": "Temat", "question": "Pytanie?",
    "broken_belief": "ludzie sadza ze cos jest inaczej niz jest",
    "the_moment": "-", "zaczyn": "-"}]})


def _call(rola, system, prompt, **reszta):
    zapis["prompt"] = prompt
    return ODPOWIEDZ


stages.zaczyn_z_kanalow = _zaczyn
llm.call = _call
stages.recent_angles = lambda conn, limit=None: []
stages.pytania_dla_skauta = lambda: []

print("=== 1. SKAUT PROSI O SKROTY ===")
stages.scout(None, run_id=1, count=6)
sprawdz("wolanie ma ze_skrotem=True", zapis.get("ze_skrotem") is True,
        "dostal %r" % zapis.get("ze_skrotem"))
sprawdz("i opis trafil do promptu", "Opis pod tytulem." in zapis.get("prompt", ""),
        zapis.get("prompt", "")[:70])

print()
print("=== 2. OKNO SWIEZOSCI ZOSTAJE ===")
# Skrot bez okna dawalby opisy sprzed pol roku — gorzej niz sam tytul,
# bo brzmialyby aktualnie.
sprawdz("max_dni nadal ustawione", zapis.get("max_dni") == 14,
        "dostal %r" % zapis.get("max_dni"))

print()
print("=== 3. PRZEBIEG JEST ZAPISANY W DECYZJACH ===")
# `zaczyn_z_kanalow` zapisuje wybor pozycji tylko wtedy, gdy zna `run_id`.
# Bez tego nie da sie pozniej odpowiedziec, czego skaut NIE dostal.
sprawdz("run_id przekazany", zapis.get("run_id") == 1,
        "dostal %r" % zapis.get("run_id"))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
