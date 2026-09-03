"""Bramka bibliotekarza MUSI odrzucac. Na zywym banku odrzucila zero grup,
wiec dowodu nie ma — a bramka, ktora nigdy nie zagryzla, moze nie dzialac.
Podajemy jej wiec grupy spreparowane tak, zeby MUSIALA je odrzucic."""
import sys, types
sys.path.insert(0, "agent-v2")
import stages, llm   # noqa: E402

zdane = oblane = 0
def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1; print("  OK    %s" % nazwa)
    else:
        oblane += 1; print("  BLAD  %s   %s" % (nazwa, szczegol))

BANK = [
    {"id": 0, "text": "x"*80, "publisher": "a.gov", "url": "https://a.gov", "kiedy": "2026-08-01", "z_artykulu": "A"},
    {"id": 1, "text": "y"*80, "publisher": "b.gov", "url": "https://b.gov", "kiedy": "2026-08-01", "z_artykulu": "A"},
    {"id": 2, "text": "z"*80, "publisher": "c.org", "url": "https://c.org", "kiedy": "2026-08-01", "z_artykulu": "B"},
]

def podstaw(odpowiedz):
    stages.llm = types.SimpleNamespace(
        call=lambda *a, **k: odpowiedz, parse_json=llm.parse_json)

import json
print("=== 1. JEDNA DZIEDZINA — MA ODPASC ===")
podstaw(json.dumps({"groups": [{"mechanism": "m", "members": [
    {"id": 0, "domain": "traffic engineering"},
    {"id": 1, "domain": "Traffic Engineering"}]}], "loners": [2], "note": ""}))
w = stages.bibliotekarz(None, 0, BANK)
sprawdz("grupa z jednej dziedziny odrzucona", len(w["groups"]) == 0, w["groups"])
sprawdz("odrzucona z podanym powodem",
        w["odrzucone_grupy"] and "jedna dziedzina" in w["odrzucone_grupy"][0]["powod_odrzucenia"],
        w["odrzucone_grupy"])
sprawdz("wielkosc liter nie robi z jednej dziedziny dwoch",
        w["odrzucone_grupy"][0]["dziedziny"] == ["traffic engineering"],
        w["odrzucone_grupy"][0]["dziedziny"])

print()
print("=== 2. DWIE ROZNE DZIEDZINY — MA PRZEJSC ===")
podstaw(json.dumps({"groups": [{"mechanism": "m", "members": [
    {"id": 0, "domain": "aviation"}, {"id": 2, "domain": "payments"}]}], "loners": [1], "note": ""}))
w = stages.bibliotekarz(None, 0, BANK)
sprawdz("grupa z dwoch dziedzin przyjeta", len(w["groups"]) == 1, w)

print()
print("=== 3. ZMYSLONE ID — MA WYPASC Z GRUPY ===")
podstaw(json.dumps({"groups": [{"mechanism": "m", "members": [
    {"id": 0, "domain": "aviation"}, {"id": 999, "domain": "payments"}]}], "loners": [], "note": ""}))
w = stages.bibliotekarz(None, 0, BANK)
sprawdz("fragment spoza banku usuniety", len(w["groups"]) == 0, w["groups"])
sprawdz("po usunieciu zostal jeden — za malo",
        w["odrzucone_grupy"] and len(w["odrzucone_grupy"][0]["members"]) == 1,
        w["odrzucone_grupy"])

print()
print("=== 4. PUSTA DZIEDZINA NIE LICZY SIE JAKO DRUGA ===")
podstaw(json.dumps({"groups": [{"mechanism": "m", "members": [
    {"id": 0, "domain": "aviation"}, {"id": 1, "domain": "  "}]}], "loners": [], "note": ""}))
w = stages.bibliotekarz(None, 0, BANK)
sprawdz("pusta dziedzina odrzucona", len(w["groups"]) == 0, w["groups"])

print()
print("=== 5. PUSTY BANK NIE WYWALA ETAPU ===")
w = stages.bibliotekarz(None, 0, [])
sprawdz("pusty bank oddaje pusty wynik", w["groups"] == [] and "pusty" in w["note"], w)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
