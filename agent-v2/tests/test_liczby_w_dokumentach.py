# -*- coding: utf-8 -*-
"""Liczba wpisana recznie w dokumencie ma sie zgadzac z drzewem.

## Po co ten plik istnieje

`docs/TROUBLESHOOTING.md` ma rozdzial 2.7 pod tytulem „Every number in the
original README was out of date" i konczy go zdaniem, ze liczba wklepana
recznie „stops being true at the first change, and nothing watches it".

4 wrzesnia 2026 policzono liczby W TYM repozytorium. Sama liczba funkcji
stala w SZESCIU dokumentach w PIECIU roznych wersjach:

    README.md                    548        docs/ARCHITECTURE.md      529
    docs/CONFIGURATION_MAP.md    548        docs/ARCHITECTURE.md      519
    docs/MAPA_KONFIGURACJI.md    519        docs/PLUGGING_IN...       535

a w drzewie bylo 549. Do tego liczba modulow (23 / 24 / 25 / 27), liczba
testow (122 / 123 / 129 / 140) i liczba promptow (24 / 27). Rozdzial
o nieaktualnych liczbach mial nieaktualne liczby.

## Dlaczego same liczby nie wystarcza

Dwie z tych rozbieznosci NIE BYLY bledem: „27 modulow" liczylo takze
`dokumentacja-zrodla/sklej.py` i `prompts/`, a „140 plikow testowych" liczylo
`platne/` i pomocnikow. Obie definicje sa sensowne — tyle ze zaden dokument
nie mowil, KTORA stosuje, wiec nie dalo sie odroznic pomiaru nieaktualnego od
pomiaru innej rzeczy.

Dlatego kazdy pomiar ma tu REGULE zapisana obok, a nie tylko wartosc.

## Jak to dziala

Kazdy wpis to (plik, wzorzec, nazwy pomiarow). Wzorzec MUSI trafic co
najmniej raz — przepisane zdanie oblewa tak samo jak zla liczba, i o to
chodzi: cichy brak trafienia zamienilby ten plik w kolejna asercje, ktora
nie moze oblac.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_liczby_w_dokumentach.py
"""
import pathlib
import re
import sys

KORZEN = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(KORZEN / "narzedzia"))

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


def _wierszy(pliki) -> int:
    return sum(len(p.read_text(encoding="utf-8").splitlines()) for p in pliki)


AGENT = KORZEN / "agent-v2"
MODULY = sorted(AGENT.glob("*.py"))
TESTY = sorted((AGENT / "tests").glob("test_*.py"))
PLATNE = sorted((AGENT / "tests" / "platne").glob("test_*.py"))
PROMPTY = sorted((AGENT / "prompts").glob("*.md"))

# Liczba funkcji idzie z TEGO SAMEGO generatora, co `docs/FUNCTION_MAP.md`.
# Wlasne liczenie byloby druga definicja tej samej rzeczy — czyli dokladnie
# ta wada, ktora ten plik sciga.
import mapa_funkcji  # noqa: E402

_zebrane = mapa_funkcji.zbierz()
ILE_FUNKCJI = sum(len(z.funkcje) for z, _, _ in _zebrane.values())

POMIARY = {
    "moduly": (len(MODULY),
               "pliki .py lezace BEZPOSREDNIO w agent-v2/ (bez tests/, "
               "bez dokumentacja-zrodla/)"),
    "funkcje": (ILE_FUNKCJI,
                "funkcje i metody w tych modulach, liczone przez "
                "narzedzia/mapa_funkcji.py z drzewa skladni"),
    "testy": (len(TESTY), "pliki agent-v2/tests/test_*.py"),
    "testy_platne": (len(PLATNE), "pliki agent-v2/tests/platne/test_*.py"),
    "prompty": (len(PROMPTY), "pliki agent-v2/prompts/*.md"),
    "wiersze_promptow": (_wierszy(PROMPTY), "wiersze tych plikow"),
    "wiersze_modulow": (_wierszy(MODULY), "wiersze tych modulow"),
}

# (plik, wzorzec, nazwy pomiarow — po jednej na grupe we wzorcu)
MIEJSCA = [
    ("README.md",
     r"\*\*(\d+) functions\*\* in (\d+) modules", ("funkcje", "moduly")),
    ("README.md", r"(\d+) tests · ", ("testy",)),
    ("docs/ARCHITECTURE.md",
     r"(\d+) functions with line numbers", ("funkcje",)),
    ("docs/ARCHITECTURE.md",
     r"Measured across the (\d+) functions", ("funkcje",)),
    ("docs/ARCHITECTURE.md",
     r"(\d+) prompt files, read from disk", ("prompty",)),
    ("docs/ARCHITECTURE.md",
     r"(\d+) free tests, (\d+) paid ones", ("testy", "testy_platne")),
    ("docs/CONFIGURATION_MAP.md",
     r"Measured across (\d+) functions in (\d+) modules",
     ("funkcje", "moduly")),
    ("docs/MAPA_KONFIGURACJI.md",
     r"(\d+) funkcji w (\d+) modułach", ("funkcje", "moduly")),
    ("docs/PLUGGING_IN_AN_ACCOUNT.md",
     r"FUNCTION_MAP\.md\) — (\d+) functions", ("funkcje",)),
    ("docs/REPO_MAP.md", r"(\d+) test_\*\.py", ("testy",)),
    ("docs/REPO_MAP.md", r"the (\d+) that cost money", ("testy_platne",)),
    ("docs/REPO_MAP.md",
     r"(\d+) briefs, (\d+) lines", ("prompty", "wiersze_promptow")),
    ("docs/REPO_MAP.md", r"Tests — (\d+) files", ("testy",)),
    # Dokument wygenerowany — sprawdzamy, czy szablon NAPRAWDE sie podstawil.
    # `{{ile_zestawow}}` w zrodle nie jest dowodem, ze cos z tego wyszlo.
    ("agent-v2/JAK_ZBUDOWANY_JEST_BOT.md",
     r"(\d+) zestawów\s+testów", ("testy",)),
]

print("=== 1. POMIARY Z DRZEWA ===")
for nazwa, (wartosc, regula) in sorted(POMIARY.items()):
    print("  %-18s %6d   (%s)" % (nazwa, wartosc, regula))
sprawdz("kazdy pomiar jest dodatni",
        all(w > 0 for w, _ in POMIARY.values()),
        {k: w for k, (w, _) in POMIARY.items() if w <= 0})

print()
print("=== 2. DOKUMENTY MOWIA TO SAMO, CO DRZEWO ===")
for plik, wzorzec, nazwy in MIEJSCA:
    p = KORZEN / plik
    if not p.exists():
        sprawdz("%s istnieje" % plik, False)
        continue
    tresc = p.read_text(encoding="utf-8")
    trafienia = re.findall(wzorzec, tresc)
    # BRAK TRAFIENIA JEST BLEDEM, nie cisza. Zdanie przepisane inaczej
    # zabralo by ten wpis spod kontroli, a licznik zdanych ani drgnal.
    sprawdz("%s: wzorzec %s w ogole trafia" % (plik, wzorzec[:34]),
            bool(trafienia))
    for t in trafienia:
        grupy = t if isinstance(t, tuple) else (t,)
        for wartosc, nazwa in zip(grupy, nazwy):
            oczek = POMIARY[nazwa][0]
            sprawdz("%s: %s = %s" % (plik, nazwa, oczek),
                    int(wartosc) == oczek,
                    "w dokumencie %s, w drzewie %d" % (wartosc, oczek))

print()
print("=== 3. KONTRDOWOD: WZORZEC NAPRAWDE PATRZY NA LICZBE ===")
# Bez tego caly plik moglby przechodzic na wzorcach, ktore trafiaja w cokolwiek.
_probka = "all **1 functions** in 1 modules"
_m = re.findall(r"\*\*(\d+) functions\*\* in (\d+) modules", _probka)
sprawdz("wzorzec zdejmuje obie liczby", _m == [("1", "1")], _m)
sprawdz("i nie trafia w zdanie bez liczb",
        not re.findall(r"\*\*(\d+) functions\*\* in (\d+) modules",
                       "all functions in modules"))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
