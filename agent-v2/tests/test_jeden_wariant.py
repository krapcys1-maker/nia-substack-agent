"""Jeden wariant notki zamiast trzech — najwieksza oszczednosc w systemie.

Trzy warianty istnialy TYLKO po to, zeby po napisaniu wybrac ten, ktory nie
powtarza pierwszego slowa poprzednich notek. Czyli placilismy za dwa wyrzucone
teksty, zeby zalatwic cos, o czym wystarczylo modelowi POWIEDZIEC.

Przy pieciu notkach dziennie roznica to 28 dolarow miesiecznie — wiecej niz
kosztuje cala reszta agenta razem wzieta.

Warunek konieczny: model MUSI dostac liste ostatnich otwarc. Bez tego jeden
wariant znaczy brak jakiejkolwiek ochrony przed powtorzonym otwarciem, a nie
oszczednosc.
"""
import json
import re
import sys

sys.path.insert(0, "agent-v2")
import config   # noqa: E402
import stages   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


print("=== 1. PISZEMY JEDEN, NIE TRZY ===")
sprawdz("NOTE_CANDIDATES = 1", config.NOTE_CANDIDATES == 1, config.NOTE_CANDIDATES)

print()
print("=== 2. WARUNEK KONIECZNY: MODEL ZNA OSTATNIE OTWARCIA ===")
# Bez tego jeden wariant to nie oszczednosc, tylko utrata ochrony.
tekst = (config.PROMPTS_DIR / "notka.md").read_text(encoding="utf-8")
sprawdz("prompt ma miejsce na otwarcia", "{ostatnie_otwarcia_json}" in tekst)
sprawdz("prompt zakazuje ich uzycia", "Do not open with any of" in tekst)
sprawdz("prompt tlumaczy, czemu to widac",
        "left edge" in tekst, "brak uzasadnienia — model zignoruje sucha regule")
zrodlo = open("agent-v2/stages.py", encoding="utf-8").read()
sprawdz("etap notki PRZEKAZUJE otwarcia do promptu",
        "ostatnie_otwarcia_json=" in zrodlo)

print()
print("=== 3. PROMPT SIE RENDERUJE I NIESIE OTWARCIA ===")
try:
    gotowy = stages._prompt(
        "notka.md", language="English", min_words=33, max_words=64,
        note_type="CIEKAWOSTKA", type_brief="x", note_form="LICZBA",
        form_brief="y", evidence="{}",
        ostatnie_otwarcia_json=json.dumps(["six", "washing", "your"]))
    sprawdz("renderuje sie bez wyjatku", True)
    for slowo in ("six", "washing", "your"):
        sprawdz("otwarcie %r trafia do tekstu" % slowo, slowo in gotowy)
    sprawdz("nie zostalo niepodstawione pole",
            not re.search(r"\{(ostatnie_otwarcia_json|evidence|note_form)\}", gotowy))
except Exception as e:
    sprawdz("renderuje sie bez wyjatku", False, repr(e))

print()
print("=== 4. POMINIECIE OTWARC JEST BLEDEM, NIE CICHYM PRZEJSCIEM ===")
# Kontrdowod: gdyby pole bylo opcjonalne, ktos usunalby je przy nastepnej
# zmianie i jeden wariant zostalby bez ochrony.
try:
    stages._prompt("notka.md", language="English", min_words=33, max_words=64,
                   note_type="CIEKAWOSTKA", type_brief="x", note_form="LICZBA",
                   form_brief="y", evidence="{}")
    sprawdz("brak otwarc wywala prompt", False, "przeszlo bez otwarc")
except KeyError:
    sprawdz("brak otwarc wywala prompt", True)

print()
print("=== 5. SORTOWNIK W KODZIE ZOSTAJE JAKO DRUGA SIATKA ===")
sprawdz("ostatnie_otwarcia nadal istnieje", hasattr(stages, "ostatnie_otwarcia"))
sprawdz("i nadal jest uzywane w kodzie", "zajete_otwarcia" in zrodlo)

print()
print("=== 6. ILE TO OSZCZEDZA (na zmierzonych stawkach) ===")
# Zmierzone na slepych testach, nie przeliczone z cennika.
ZA_WYWOLANIE = {"Fable": 0.2803 / 3, "Opus 5": 0.1214 / 3, "DeepSeek-pro": 0.0296 / 3}
for nazwa, k in ZA_WYWOLANIE.items():
    trzy, jeden = k * 3 * 150, k * 150
    print("    %-14s 3 warianty $%6.2f  ->  1 wariant $%6.2f   oszczednosc $%6.2f"
          % (nazwa, trzy, jeden, trzy - jeden))
sprawdz("oszczednosc przy Fable przekracza 25 USD",
        ZA_WYWOLANIE["Fable"] * 2 * 150 > 25)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
