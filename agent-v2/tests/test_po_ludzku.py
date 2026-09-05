# -*- coding: utf-8 -*-
"""Blok „nie brzmij jak maszyna" ma byc WSTRZYKIWANY, nie kopiowany.

## Po co ten plik istnieje

`prompts/po_ludzku.md` przez tygodnie opisywal sam siebie jako dolaczany do
promptow komentarza, odpowiedzi i notki — i nie byl dolaczany do niczego. Jego
wlasny naglowek przyznaje sie do tego wprost: „TO BYLA NIEPRAWDA — sprawdzone
drzewem skladni: nazwa `po_ludzku.md` nie pada w zadnej linii kodu".

Reguly przepisano wiec RECZNIE do trzech briefow. Zmierzone przed poprawka:
15 akapitow powtorzonych miedzy plikami, okolo 4 900 znakow nadmiaru
wysylanych przy kazdym wywolaniu — i, co gorsze od znakow, cztery kopie jednej
reguly, ktore rozjada sie tak samo, jak rozjechala sie tu data przestawienia
(piec kopii) i lista slow pustych (cztery).

## Czego pilnuje

Obu stron naraz, bo pilnowanie jednej nic nie daje:

  1. plik ZAWIERA sekcje, ktore deklarujemy jako wspolne;
  2. briefy JUZ ICH NIE MAJA u siebie — inaczej wstrzykniecie zdublowaloby
     tresc zamiast ja zastapic;
  3. zlozony prompt ma kazda z nich DOKLADNIE RAZ;
  4. naglowek pliku (notatka dla czlowieka) do promptu NIE WCHODZI.

Sekcje `Openers and closers` i `Register` sa CELOWO poza blokiem: roznia sie
miedzy plikami, a scalenie ich byloby zgadywaniem, ktora wersja jest wlasciwa.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_po_ludzku.py
"""
import pathlib
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


BRIEFY = ("komentarz.md", "notka.md", "odpowiedz.md")
BLOK = stages._blok_po_ludzku()

print("=== 1. BLOK ZAWIERA DOKLADNIE TO, CO DEKLARUJEMY ===")
w_bloku = re.findall(r"^## (.+)$", BLOK, re.M)
sprawdz("sekcje bloku = SEKCJE_WSPOLNE",
        w_bloku == list(config_sekcje := list(stages.SEKCJE_WSPOLNE)),
        (w_bloku, config_sekcje))
sprawdz("blok nie jest pusty", len(BLOK) > 200, len(BLOK))

print()
print("=== 2. NAGLOWEK PLIKU NIE WCHODZI DO PROMPTU ===")
# Naglowek to notatka dla czlowieka o tym, ze plik jest dolaczany. Gdyby
# wchodzil, model dostawalby instrukcje o wlasnej infrastrukturze.
zrodlo = (config.PROMPTS_DIR / "po_ludzku.md").read_text(encoding="utf-8")
sprawdz("plik ma poziomia kreske oddzielajaca naglowek", "\n---\n" in zrodlo)
for fraza in ("WSTRZYKIWANE PRZEZ", "notatką dla człowieka", "MATERIAŁ"):
    if fraza in zrodlo:
        sprawdz("  naglowek '%s' nie trafia do bloku" % fraza[:24],
                fraza not in BLOK)

print()
print("=== 3. BRIEFY NIE MAJA JUZ TYCH SEKCJI U SIEBIE ===")
for nazwa in BRIEFY:
    tekst = (config.PROMPTS_DIR / nazwa).read_text(encoding="utf-8")
    sprawdz("  %s wola {po_ludzku}" % nazwa, "{po_ludzku}" in tekst)
    for sekcja in stages.SEKCJE_WSPOLNE:
        sprawdz("  %s nie ma juz '%s'" % (nazwa, sekcja[:28]),
                ("\n## " + sekcja + "\n") not in tekst)

print()
print("=== 4. ZLOZONY PROMPT MA KAZDA SEKCJE DOKLADNIE RAZ ===")
# To jest asercja, ktora lapie ZLA POLOWE poprawki: wstrzyknelismy blok,
# ale zapomnielismy wyciac kopie.
_atrapy = dict(min_words=33, max_words=64, note_type="CIEKAWOSTKA",
               type_brief="x", note_form="PROSTA", form_brief="x",
               evidence="{}", ostatnie_otwarcia_json="[]",
               pytania_czytelnikow="", kanon_niszy="", przekonania_niszy="",
               rzeczy_czytelnika="", obszary_seam="")
zlozony = stages._prompt("notka.md", **_atrapy)
for sekcja in stages.SEKCJE_WSPOLNE:
    sprawdz("  '%s' raz" % sekcja[:34],
            zlozony.count("## " + sekcja) == 1,
            zlozony.count("## " + sekcja))

print()
print("=== 5. KONTRDOWOD: CZY TO COKOLWIEK LAPIE ===")
# Bez tego caly plik przechodzilby takze wtedy, gdyby nie badal niczego.
sprawdz("sekcja spoza listy NIE jest wstrzykiwana",
        "## Openers and closers" not in BLOK)
sprawdz("...a w pliku zrodlowym nadal jest",
        "## Openers and closers" in zrodlo)
_udawany = "## Punctuation: this is the strongest tell in short text\nx\n"
sprawdz("podwojenie sekcji byloby widziane",
        (zlozony + _udawany).count(
            "## Punctuation: this is the strongest tell in short text") == 2)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
