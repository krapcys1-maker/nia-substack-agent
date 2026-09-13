# -*- coding: utf-8 -*-
"""Gdy dostawca urywa odpowiedz, w logu ma stac POWOD, nie poczatek zdarzenia.

## Wpadka

10 wrzesnia 2026 pisarz artykulu padl DWA RAZY, za kazdym razem tak:

    [awaria] pisarz (gpt-6-astra) padl: OpenAI /responses zglosil blad:
    {"type": "response.incomplete", "response": {"id": "resp_01a99c34...",
    "object": "response", "created_at": 1789017683, "status": "incomplete",
    "background": false, "completed_at": null, "error": null,
    "frequency_penalty": 0.0, "incomplete_details": {"reason": "

Komunikat urywa sie DOKLADNIE na wartosci pola `reason` — jedynym miejscu,
ktore mowi cokolwiek o przyczynie. Powod: kod robil
`json.dumps(response.error or error or zdarzenie)[:300]`, a przy
`response.incomplete` zadne z dwoch pierwszych pol nie istnieje. Zrzucalismy
wiec cale zdarzenie i ucinali je na trzystu znakach, ktore w calosci zajmuja
identyfikatory i domyslne ustawienia.

Dwie awarie platnego etapu, obie nie do zdiagnozowania.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_powod_urwania_widac.py
"""
import ast
import io
import json
import sys

sys.path.insert(0, "agent-v2")
import llm             # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# DOKLADNIE TEN KSZTALT, KTORY PRZYSZEDL Z OPENAI.
ZDARZENIE = {
    "type": "response.incomplete",
    "response": {
        "id": "resp_01a99c3480859d2b006aa23e5382b487d2adae811f418aab4a",
        "object": "response",
        "created_at": 1789017683,
        "status": "incomplete",
        "background": False,
        "completed_at": None,
        "error": None,
        "frequency_penalty": 0.0,
        "incomplete_details": {"reason": "max_output_tokens"},
        "usage": {"output_tokens": 37750},
    },
}

print("=== 1. POWOD JEST WIDOCZNY ===")
opis = llm._powod_urwania(ZDARZENIE)
print("     %s" % opis)
sprawdz("powod urwania w komunikacie", "max_output_tokens" in opis, opis[:90])
sprawdz("i miesci sie w limicie", len(opis) <= 300, len(opis))
sprawdz("liczba tokenow wyjscia tez", "37750" in opis, opis[:90])

print()
print("=== 2. KONTRDOWOD: STARY SPOSOB TEGO NIE POKAZYWAL ===")
# Ten sam limit, ta sama tresc — roznica jest w tym, CO wybieramy do zrzucenia.
stary = json.dumps(ZDARZENIE.get("response", {}).get("error")
                   or ZDARZENIE.get("error") or ZDARZENIE)[:300]
sprawdz("stary sposob gubil powod", "max_output_tokens" not in stary)
sprawdz("i urywal sie na polu reason", stary.rstrip().endswith('"reason": "')
        or '"reason"' in stary[-40:], stary[-46:])

print()
print("=== 3. PRAWDZIWY BLAD NADAL IDZIE W CALOSCI ===")
Z_BLEDEM = {"type": "response.failed",
            "response": {"error": {"code": "rate_limit_exceeded",
                                   "message": "slow down"}}}
opis2 = llm._powod_urwania(Z_BLEDEM)
sprawdz("kod bledu widoczny", "rate_limit_exceeded" in opis2, opis2[:80])
sprawdz("i tresc bledu tez", "slow down" in opis2, opis2[:80])

print()
print("=== 4. ZDARZENIE BEZ NICZEGO NIE WYWALA ===")
for puste in ({}, {"type": "error"}, {"response": None}, {"response": {}}):
    try:
        llm._powod_urwania(puste)
        sprawdz("puste zdarzenie %r przechodzi" % (puste,), True)
    except Exception as exc:                      # noqa: BLE001
        sprawdz("puste zdarzenie %r przechodzi" % (puste,), False,
                type(exc).__name__)

print()
print("=== 5. OBA MIEJSCA W llm.py IDA PRZEZ POMOCNIKA ===")
# Sciezka OpenAI wystepuje DWA razy — dla dwoch ksztaltow strumienia. Gdyby
# poprawke wpisac tylko w jedno, druga awaria nadal bylaby nieczytelna.
ZRODLO = io.open("agent-v2/llm.py", encoding="utf-8").read()
sprawdz("pomocnik istnieje", "def _powod_urwania(" in ZRODLO)
sprawdz("wolany dwa razy", ZRODLO.count("_powod_urwania(zdarzenie)") == 2,
        ZRODLO.count("_powod_urwania(zdarzenie)"))
sprawdz("stary zrzut calego zdarzenia zniknal",
        'or zdarzenie.get("error") or zdarzenie)[:300]' not in ZRODLO)
# Kontrdowod dla samej reguly: obie galezie nadal reaguja na te same typy.
sprawdz("oba miejsca nadal lapia response.incomplete",
        ZRODLO.count('"response.failed", "response.incomplete", "error"') == 2,
        ZRODLO.count('"response.failed", "response.incomplete", "error"'))
drzewo = ast.parse(ZRODLO)
sprawdz("i plik nadal sie parsuje", bool(drzewo.body))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
