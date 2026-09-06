# -*- coding: utf-8 -*-
"""Factcheck, ktory dostal narracje zamiast JSON-a, ratuje werdykt drugim tanim wywolaniem.

## Po co ten plik istnieje

Zmierzone 2026-09-06 (artykul 0006 kartridza `ai`): sprawdzenie faktow
artykulu zrobilo 19 wyszukiwan za $0,123, a odpowiedz zaczynala sie od
„I'll analyze the factual claims in this text" zamiast od nawiasu. Parser
rzucil, `zweryfikuj` oddalo „weryfikacja nie doszla do skutku" i caly
research przepadl. Ciekawostki mialy juz od dawna `llm.ratuj_json` na ten
przypadek (drugie wywolanie BEZ wyszukiwania, na tym, co model znalazl);
factcheck nie mial. Teraz ma.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_ratunek_weryfikacji.py
"""
import json
import sys

sys.path.insert(0, "agent-v2")
import llm     # noqa: E402
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


NARRACJA = ("I'll analyze the factual claims in this text and search for each. "
            "Let me identify the key claims: the signature in July 2026 is confirmed "
            "by the announcement; the 190 signatories figure is confirmed.")
JSON_DOBRY = json.dumps({
    "claims": [
        {"claim": "signed in July 2026", "status": "confirmed",
         "url": "https://example.org/a", "source_date": "2026-07-01", "what_the_source_says": ""},
        {"claim": "about 190 signatories", "status": "refuted",
         "url": "https://example.org/b", "source_date": "2026-07-02",
         "what_the_source_says": "the page lists 120"},
    ],
    "safe_to_post": False, "verdict": "one claim refuted",
})

ORYG_CALL, ORYG_RATUJ = llm.call, llm.ratuj_json
wolania = {"call": 0, "ratuj": 0}
try:
    print("=== 1. NARRACJA + UDANY RATUNEK = WERDYKT Z TWIERDZENIAMI ===")

    def call_narracja(purpose, system, user, **k):
        wolania["call"] += 1
        return NARRACJA

    def ratuj_ok(purpose, tekst, ksztalt, **k):
        wolania["ratuj"] += 1
        sprawdz("ratunek dostaje NARRACJE modelu, nie prompt", tekst == NARRACJA)
        sprawdz("i ksztalt weryfikacji z polem claims", '"claims"' in ksztalt and '"safe_to_post"' in ksztalt)
        return JSON_DOBRY

    llm.call, llm.ratuj_json = call_narracja, ratuj_ok
    w = stages.zweryfikuj(None, 0, "Anthropic signed the code in July 2026 with about 190 signatories.")
    sprawdz("factcheck wolany raz, ratunek raz", wolania == {"call": 1, "ratuj": 1}, wolania)
    sprawdz("werdykt NIE jest oznaczony jako nie-sprawdzone", not w.get("nie_sprawdzone"), w.get("verdict"))
    sprawdz("twierdzenia z ratunku sa w wyniku", len(w.get("claims") or []) == 2, w.get("claims"))
    sprawdz("obalone twierdzenie staje sie zarzutem",
            any("190" in str(z) for z in (w.get("zarzuty") or [])), w.get("zarzuty"))

    print()
    print("=== 2. KONTRDOWOD: RATUNEK TEZ BEZ JSON-A = JAWNE NIE-SPRAWDZONE ===")
    wolania.update(call=0, ratuj=0)

    def ratuj_zle(purpose, tekst, ksztalt, **k):
        wolania["ratuj"] += 1
        return "still no json here"

    llm.ratuj_json = ratuj_zle
    w2 = stages.zweryfikuj(None, 0, "Anthropic signed the code in July 2026.")
    sprawdz("ratunek probowany", wolania["ratuj"] == 1, wolania)
    sprawdz("wynik mowi wprost, ze nie sprawdzono", w2.get("nie_sprawdzone") is True, w2)
    sprawdz("i nie udaje zarzutow", w2.get("zarzuty") == [], w2.get("zarzuty"))
    sprawdz("puszcza na pierwszej siatce (nie blokuje z powodu wlasnej awarii)", w2.get("safe_to_post") is True)

    print()
    print("=== 3. JSON OD RAZU = BEZ RATUNKU ===")
    wolania.update(call=0, ratuj=0)
    llm.call = lambda purpose, system, user, **k: JSON_DOBRY
    llm.ratuj_json = ratuj_zle
    w3 = stages.zweryfikuj(None, 0, "Anthropic signed the code in July 2026 with about 190 signatories.")
    sprawdz("ratunek NIE wolany, gdy odpowiedz jest JSON-em", wolania["ratuj"] == 0, wolania)
    sprawdz("i werdykt ten sam", len(w3.get("claims") or []) == 2)
finally:
    llm.call, llm.ratuj_json = ORYG_CALL, ORYG_RATUJ

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
