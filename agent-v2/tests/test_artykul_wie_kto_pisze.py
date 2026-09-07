# -*- coding: utf-8 -*-
"""Artykul ma wiedziec, kto go pisze — a pisal go „anonymous editorial brand".

## Po co ten plik istnieje

ZNALEZIONE AUDYTEM 7 wrzesnia 2026, po calym dniu poprawiania glosu NOTEK.
Pisarz artykulu dostawal `WRITER_SYSTEM` zaczynajacy sie od „You write for the
anonymous editorial brand" i NIGDY nie widzial bloku `linia_redakcyjna` —
kotwicy, ktora opisuje, kim ona jest. Krotkie formy dostawaly ja przez
`personality._system` od poczatku.

Wyszlo z tego cos gorszego niz nierowna jakosc: dwie formy tego samego konta
pisaly DWIE ROZNE OSOBY, bo tylko jedna z nich wiedziala, ze jest osoba. I to
akurat w formie najdrozszej (rzad 0,57 USD za sztuke) oraz jedynej z pelnym
potokiem dowodowym, wiec brak glosu widac tam najmocniej.

Wady tej klasy nie znajdzie sie, czytajac WYNIK modelu — tylko sprawdzajac, co
model DOSTAJE. Ten plik sprawdza wejscie.

## Czego pilnuje

ANONIMOWA MARKA ZOSTAJE BEZ PERSONY. Kartridze `ai` i `hidden-bill` publikuja
bezosobowo i tak ma byc; gdyby ten test tego nie trzymal, poprawka do NIA
zmienilaby glos kont, ktore o zadna osobowosc nie prosily.

DOWOD MA OSTATNIE SLOWO. Tozsamosc mowi, JAK pisze; karta dowodowa mowi, CO
wolno twierdzic. Zdanie o karcie stoi na koncu i ma tam zostac.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_artykul_wie_kto_pisze.py
"""
import sys

sys.path.insert(0, "agent-v2")
import config  # noqa: E402
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


KOTWICA = "You are NIA. You are she. Wzorcowa kotwica tozsamosci do proby."

stara_persona = config.PERSONA_WLACZONA
stare_bloki = dict(getattr(config, "PRESET_BLOKI", None) or {})
try:
    print("=== 1. Z PERSONA: ARTYKUL NIESIE TOZSAMOSC ===")
    config.PERSONA_WLACZONA = True
    config.PRESET_BLOKI = {**stare_bloki, "linia_redakcyjna": KOTWICA}
    s = stages.system_pisarza()
    sprawdz("kotwica jest w systemie artykulu", KOTWICA in s, s[:120])
    sprawdz("NIE zaczyna sie od anonimowej marki",
            not s.startswith("You write for the anonymous"), s[:80])
    sprawdz("mowi wprost, ze to ona jest autorka",
            "not an anonymous brand" in s, s[:150])
    # DOWOD MA OSTATNIE SLOWO — patrz naglowek.
    sprawdz("zdanie o karcie dowodowej jest ostatnie",
            s.rstrip().endswith("no prose around it."), s[-90:])
    sprawdz("zasada faktow nie zniknela",
            "only what the supplied evidence card establishes" in s)
    sprawdz("marka nadal nazwana", config.NAZWA_MARKI in s)

    print()
    print("=== 2. BEZ PERSONY: ANONIMOWA MARKA ZOSTAJE ===")
    # `ai` i `hidden-bill` publikuja bezosobowo i nie prosily o zadna osobowosc.
    config.PERSONA_WLACZONA = False
    sprawdz("wraca dokladnie stary WRITER_SYSTEM",
            stages.system_pisarza() == stages.WRITER_SYSTEM)
    sprawdz("i nie ma w nim kotwicy", KOTWICA not in stages.system_pisarza())

    print()
    print("=== 3. PERSONA BEZ KOTWICY NIE WYWRACA PRZEBIEGU ===")
    # Kartridz z persona, ale bez bloku `linia_redakcyjna`: artykul ma powstac.
    config.PERSONA_WLACZONA = True
    config.PRESET_BLOKI = {**stare_bloki, "linia_redakcyjna": ""}
    sprawdz("pusty blok -> stary system, bez wyjatku",
            stages.system_pisarza() == stages.WRITER_SYSTEM)
    config.PRESET_BLOKI = {}
    sprawdz("brak bloku w ogole -> stary system",
            stages.system_pisarza() == stages.WRITER_SYSTEM)
finally:
    config.PERSONA_WLACZONA = stara_persona
    config.PRESET_BLOKI = stare_bloki

print()
print("=== 4. NIKT NIE WOLA JUZ STALEJ Z POMINIECIEM FUNKCJI ===")
# Kontrdowod: funkcja moglaby byc idealna i nieuzywana.
import io  # noqa: E402
zrodlo = io.open("agent-v2/stages.py", encoding="utf-8").read()
sprawdz("pisarz artykulu wola `system_pisarza()`",
        'llm.call("write", system_pisarza()' in zrodlo)
sprawdz("i nie zostalo wywolanie na golej stalej",
        'llm.call("write", WRITER_SYSTEM' not in zrodlo)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
