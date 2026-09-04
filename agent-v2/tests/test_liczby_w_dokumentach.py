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

## Dlaczego to jest JEDEN plik, a nie dwa

`test_liczby_w_readme.py` robil to samo od wczesniej — na RECZNIE WYPISANEJ
liscie dwoch dokumentow. Pozostale cztery miejsca byly poza jego zasiegiem
i rozjechaly sie o trzydziesci funkcji. Sam docstring tamtego pliku mowil, ze
recepta z `TROUBLESHOOTING.md` „przez chwile byla TYLKO w dokumencie" —
i skonczyla jako sprawdzenie dwoch dokumentow z szesciu.

Zostawienie obu bylo by trzecim przykladem tej samej wady w jednym dniu:
liczyly funkcje INACZEJ (jedna z `zbierz()`, druga z tabeli w wygenerowanym
`FUNCTION_MAP.md`) i juz dawaly rozne wyniki. Tamten plik zostal usuniety,
a jego jedyne wlasne sprawdzenie — dlugosc dokumentu sklejanego — jest tutaj
w sekcji 3.

## Jak to dziala

Kazdy wpis to (plik, wzorzec, nazwy pomiarow). Wzorzec MUSI trafic co
najmniej raz — przepisane zdanie oblewa tak samo jak zla liczba, i o to
chodzi: cichy brak trafienia zamienilby ten plik w kolejna asercje, ktora
nie moze oblac.

## Poprawianie

    python agent-v2/tests/test_liczby_w_dokumentach.py --popraw

Przepisuje liczby w dokumentach na te z drzewa i konczy zwyklym sprawdzeniem.
Jest to jedyna praktyczna droga do spelnienia tej zasady: bez niej kazda
dopisana funkcja kosztuje szesc recznych poprawek, a taki koszt sprawia, ze
sprawdzenie zaczyna sie obchodzic, zamiast je spelniac.

Po poprawce przebuduj dokument sklejany:
`python agent-v2/dokumentacja-zrodla/sklej.py`.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_liczby_w_dokumentach.py
"""
import ast
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

def _ile_bramek() -> int:
    """Ile bramek NAPRAWDE chodzi na gotowym tekscie — z grafu wywolan.

    README podawal 16 i nikt tego nie przeliczal; prawdziwa liczba to 12.
    Recznie utrzymywana liczba w tekscie dla ludzi z zewnatrz to ta sama wada,
    ktora zdjelismy z tabeli „Honest notes": wspomnienie po pomiarze.

    Liczymy domkniecie: bierzemy funkcje z `gates.py` wolane z INNYCH modulow,
    dokladamy to, co one wolaja wewnatrz `gates.py`, i odejmujemy agregatory —
    `deterministic_floors` zbiera wyniki, `verdict` wydaje werdykt; zadna
    z nich nie jest osobnym sprawdzeniem tekstu.
    """
    zrodlo_g = (AGENT / "gates.py").read_text(encoding="utf-8")
    drzewo = ast.parse(zrodlo_g)
    publiczne = {w.name for w in drzewo.body
                 if isinstance(w, ast.FunctionDef) and not w.name.startswith("_")}
    wewnetrzne = {
        w.name: {n.func.id for n in ast.walk(w)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                 and n.func.id in publiczne}
        for w in drzewo.body if isinstance(w, ast.FunctionDef)
    }
    z_zewnatrz = set()
    for p in AGENT.glob("*.py"):
        if p.name == "gates.py":
            continue
        tekst = p.read_text(encoding="utf-8")
        z_zewnatrz |= {n for n in publiczne
                       if re.search(r"gates\.%s\s*\(" % n, tekst)}
    zywe, kolejka = set(), list(z_zewnatrz)
    while kolejka:
        n = kolejka.pop()
        if n in zywe:
            continue
        zywe.add(n)
        kolejka += list(wewnetrzne.get(n, ()))
    return len(zywe - {"deterministic_floors", "verdict"})


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
    "bramki": (_ile_bramek(),
               "funkcje z gates.py, ktore NAPRAWDE chodza na gotowym tekscie "
               "— wywiedzione z grafu wywolan, bez agregatorow"),
}

# (plik, wzorzec, nazwy pomiarow — po jednej na grupe we wzorcu)
MIEJSCA = [
    ("README.md",
     r"\*\*(\d+) functions\*\* in (\d+) modules", ("funkcje", "moduly")),
    ("README.md", r"(\d+) tests · ", ("testy",)),
    # „16 gates" stalo w dwoch miejscach README i nikt tego nie
    # przeliczal. Prawdziwa liczba, z grafu wywolan, to 12.
    ("README.md", r"(\d+) gates on every finished text", ("bramki",)),
    ("README.md", r"(\d+) deterministic gates", ("bramki",)),
    # Akapit „Honest notes". Stala tam tabela z liczbami przejsc
    # (102/103/104), ktorej nikt nie przeliczal — zdryfowala do 102
    # przy prawdziwych 137. Zostala jedna liczba i jest liczona
    # z drzewa.
    ("README.md", r"of (\d+) test files", ("testy",)),
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

# --- POPRAWIANIE (--popraw) -------------------------------------------------
#
# Test wie, GDZIE kazda liczba stoi i ILE powinna wynosic. Bez tej galezi kazda
# dopisana funkcja kosztuje szesc recznych poprawek w szesciu dokumentach —
# a koszt jest tym, co sprawia, ze sprawdzenie zaczyna sie obchodzic zamiast
# spelniac. Sprawdzanie zostaje domyslne; poprawka wymaga flagi.
if "--popraw" in sys.argv:
    zmienione = 0
    for plik, wzorzec, nazwy in MIEJSCA:
        p = KORZEN / plik
        if not p.exists():
            continue
        tresc = p.read_text(encoding="utf-8")

        def _popraw(m, nazwy=nazwy):
            caly = m.group(0)
            for i, nazwa in enumerate(nazwy, start=1):
                stara = m.group(i)
                nowa = str(POMIARY[nazwa][0])
                if stara != nowa:
                    # Podmieniamy TYLKO w obrebie trafienia i tylko pierwsze
                    # wystapienie tej liczby — inaczej „25" w slowie „255"
                    # albo druga liczba o tej samej wartosci ucierpialaby razem.
                    caly = caly.replace(stara, nowa, 1)
            return caly

        nowa_tresc = re.sub(wzorzec, _popraw, tresc)
        if nowa_tresc != tresc:
            p.write_text(nowa_tresc, encoding="utf-8")
            zmienione += 1
            print("  poprawione  %s" % plik)
    # DLUGOSC DOKUMENTU SKLEJANEGO — poprawiana tak samo, choc nie stoi
    # w `MIEJSCA` (ma wlasna tolerancje, wiec nie jest zwyklym porownaniem).
    # Bez tej galezi byla JEDYNA liczba, ktorej nie dalo sie poprawic jedna
    # komenda — i jedyna, ktora sie rozjechala.
    _jzb = KORZEN / "agent-v2/JAK_ZBUDOWANY_JEST_BOT.md"
    _readme = KORZEN / "README.md"
    if _jzb.exists() and _readme.exists():
        _ile = len(_jzb.read_text(encoding="utf-8").splitlines())
        _tresc = _readme.read_text(encoding="utf-8")
        _nowa = re.sub(r"(JAK_ZBUDOWANY_JEST_BOT\.md` — )[\d,]+( lines)",
                       lambda m: m.group(1) + format(_ile, ",") + m.group(2),
                       _tresc)
        if _nowa != _tresc:
            _readme.write_text(_nowa, encoding="utf-8")
            zmienione += 1
            print("  poprawione  README.md (dlugosc dokumentu sklejanego)")
    print("  zmienionych plikow: %d" % zmienione)
    print("  PRZEBUDUJ dokument sklejany:"
          " python agent-v2/dokumentacja-zrodla/sklej.py")
    print()

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
print("=== 3. DLUGOSC DOKUMENTU SKLEJANEGO ===")
# PRZENIESIONE z `test_liczby_w_readme.py`, ktory to sprawdzal jako jedyny.
# TOLERANCJA 50 WIERSZY, I TO JEST SWIADOME: dokument przebudowuje sie przy
# kazdej zmianie komentarza w kodzie, wiec wymaganie rownosci co do wiersza
# kazaloby poprawiac README przy KAZDYM commicie — a wtedy ludzie zaczna to
# obchodzic zamiast poprawiac. Liczba ma mowic o skali, nie o wersji.
_jzb = KORZEN / "agent-v2/JAK_ZBUDOWANY_JEST_BOT.md"
if _jzb.exists():
    _ile = len(_jzb.read_text(encoding="utf-8").splitlines())
    _m = re.search(r"JAK_ZBUDOWANY_JEST_BOT\.md` — ([\d,]+) lines",
                   (KORZEN / "README.md").read_text(encoding="utf-8"))
    sprawdz("README podaje dlugosc dokumentu sklejanego", _m is not None)
    if _m:
        _podane = int(_m.group(1).replace(",", ""))
        sprawdz("i miesci sie w 50 wierszach od prawdy (%d)" % _ile,
                abs(_podane - _ile) <= 50,
                "README: %d, plik: %d, roznica %d"
                % (_podane, _ile, abs(_podane - _ile)))

print()
print("=== 4. KONTRDOWOD: WZORZEC NAPRAWDE PATRZY NA LICZBE ===")
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
