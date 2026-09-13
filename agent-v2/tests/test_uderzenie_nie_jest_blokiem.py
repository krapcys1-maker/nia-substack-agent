# -*- coding: utf-8 -*-
"""Za dluga linia idzie na dwie — po kropce, bez przepisywania slow.

## Pomiar, ktory to wywolal

10 wrzesnia 2026, dwie notki z zywego przebiegu, ta sama instrukcja:

    notka 1   58 slow, 3 uderzenia, 19,3 slowa na uderzenie   dobrze
    notka 2   68 slow, 3 uderzenia, 22,7 — PIERWSZE UDERZENIE 32 SLOWA

Instrukcja krotkiej formy mowi wprost: „If a line runs past twenty-five words,
it is two lines". Model jej nie zlamal w tresci — on tylko nie postawil
lamania wiersza. Ta linia na 32 slowa to byly DWA PELNE ZDANIA:

    Simon Willison ran the same pelican SVG prompt across OpenAI's tiers.
    Astra on its cheapest, lowest-reasoning setting drew a better pelican
    than GPT-5.6 Sol at any price, about ten cents a go.

Proszenie modelu drugi raz kosztuje kolejne wywolanie i nadal jest prosba.
Ciecie po kropce nie przepisuje niczego: te same slowa, ta sama kolejnosc,
inny uklad. To jest praca dla kodu.

## Granica, ktorej kod nie przekracza

Jedno zdanie na trzydziesci slow zostaje jak bylo. Polamane w przypadkowym
miejscu czytaloby sie gorzej niz dlugie — poprawka szkodzilaby zamiast pomagac.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_uderzenie_nie_jest_blokiem.py
"""
import ast
import io
import sys

sys.path.insert(0, "agent-v2")
import personality as p        # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# DOKLADNIE TA LINIA, KTORA ZAWIODLA NA ZYWO.
WPADKA = ("Simon Willison ran the same pelican SVG prompt across OpenAI's tiers."
          " Astra on its cheapest, lowest-reasoning setting drew a better pelican"
          " than GPT-5.6 Sol at any price, about ten cents a go.")

print("=== 1. TA WPADKA JUZ SIE NIE ZDARZY ===")
sprawdz("wejscie naprawde bylo za dlugie", len(WPADKA.split()) > 25,
        len(WPADKA.split()))
tekst, ile = p.rozbij_dlugie_uderzenia(WPADKA)
linie = tekst.split("\n")
for l in linie:
    print("     %2d slow | %s" % (len(l.split()), l[:70]))
sprawdz("rozbite na dwa uderzenia", len(linie) == 2, len(linie))
sprawdz("policzone jako jedna poprawka", ile == 1, ile)
sprawdz("kazde uderzenie miesci sie w limicie",
        all(len(l.split()) <= 25 for l in linie),
        [len(l.split()) for l in linie])

print()
print("=== 2. SLOWA ZOSTAJA TE SAME — TO UKLAD, NIE PRZEPISANIE ===")
# To jest cala roznica miedzy ta poprawka a doplaceniem za druga proba.
sprawdz("te same slowa w tej samej kolejnosci",
        tekst.split() == WPADKA.split())
sprawdz("nic nie doszlo", len(tekst.split()) == len(WPADKA.split()))

print()
print("=== 3. KOD NIE TNIE W SRODKU ZDANIA ===")
JEDNO = ("One single sentence that simply keeps going and going without ever"
         " reaching a full stop until it is far past any sensible beat length"
         " for a Note")
sprawdz("jedno dlugie zdanie naprawde przekracza limit",
        len(JEDNO.split()) > 25)
t2, n2 = p.rozbij_dlugie_uderzenia(JEDNO)
sprawdz("zostaje jedna linia", len(t2.split("\n")) == 1)
sprawdz("i nie jest liczone jako poprawka", n2 == 0)
sprawdz("tekst nietkniety", t2 == JEDNO)

print()
print("=== 4. NIC INNEGO NIE JEST RUSZANE ===")
DOBRA = ("The lock is fitted.\nIt is just not locked.\n"
         "Somebody signed off on that and went to lunch.")
sprawdz("notka w ksztalcie przechodzi bez zmian",
        p.rozbij_dlugie_uderzenia(DOBRA) == (DOBRA, 0))
sprawdz("pusty tekst nie wywala", p.rozbij_dlugie_uderzenia("") == ("", 0))
sprawdz("same spacje nie wywalaja", p.rozbij_dlugie_uderzenia("   ")[1] == 0)
# Pusta linia miedzy uderzeniami to uklad autorki — ma przetrwac.
Z_PRZERWA = "First beat here.\n\nSecond beat here."
sprawdz("puste linie zostaja", p.rozbij_dlugie_uderzenia(Z_PRZERWA)[0] == Z_PRZERWA)

print()
print("=== 5. TRZY ZDANIA W BLOKU DAJA TRZY UDERZENIA, NIE JEDNO ===")
TRZY = ("The vendor shipped the feature on a Friday afternoon without a single"
        " test. Nobody noticed for eleven days because the dashboard was green"
        " the whole time. Then a customer in Lisbon asked one obvious question"
        " and the whole thing folded.")
t3, n3 = p.rozbij_dlugie_uderzenia(TRZY)
for l in t3.split("\n"):
    print("     %2d slow | %s" % (len(l.split()), l[:70]))
sprawdz("blok rozlozony na wiecej niz jedno uderzenie",
        len(t3.split("\n")) >= 2, len(t3.split("\n")))
sprawdz("kazde w limicie", all(len(l.split()) <= 25 for l in t3.split("\n")),
        [len(l.split()) for l in t3.split("\n")])
sprawdz("slowa nadal te same", t3.split() == TRZY.split())

print()
print("=== 6. WPIETE W SCIEZKE, KTORA NAPRAWDE PISZE ===")
ZRODLO = io.open("agent-v2/personality.py", encoding="utf-8").read()
CIALO = ""
for w in ast.walk(ast.parse(ZRODLO)):
    if isinstance(w, ast.FunctionDef) and w.name == "short_form":
        CIALO = ast.get_source_segment(ZRODLO, w) or ""
sprawdz("short_form istnieje", bool(CIALO))
sprawdz("i wola rozbicie", "rozbij_dlugie_uderzenia(body)" in CIALO)
# PRZED doklejeniem statystyk: zmierzona liczba jest tekstem programu,
# a nie zdaniem autorki, i nie ma byc przez nas przestawiana.
i_rozbicie = CIALO.find("rozbij_dlugie_uderzenia(body)")
i_staty = CIALO.find('material["statistics"] + "')
sprawdz("rozbicie idzie przed doklejeniem statystyk",
        i_rozbicie >= 0 and i_staty >= 0 and i_rozbicie < i_staty,
        "%d / %d" % (i_rozbicie, i_staty))
sprawdz("liczba poprawek trafia do wyniku",
        '"uderzenia_rozbite": rozbite_uderzenia' in CIALO)
sprawdz("i widac ja w logu", "rozbite za dlugie uderzenia" in CIALO)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
