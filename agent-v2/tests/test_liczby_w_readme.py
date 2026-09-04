# -*- coding: utf-8 -*-
"""Liczby w README i REPO_MAP musza zgadzac sie z drzewem.

## Po co ten plik istnieje

`docs/TROUBLESHOOTING.md` pozycja 2.7 opisuje, ze KAZDA liczba w oryginalnym
README byla nieaktualna — 11 plikow zamiast 23, 11 231 wierszy zamiast 28 000,
43 zestawy testow zamiast 122. I nazywa to wprost: liczba wpisana recznie,
zeby bylo widac skale, przestaje byc prawdziwa przy pierwszej zmianie, a nikt
tego nie zauwaza, bo nic jej nie pilnuje.

Ten sam dokument podaje trwale rozwiazanie — dopisac sprawdzenie liczb do
zestawu — i przez chwile bylo ono TYLKO w dokumencie. Zmierzone przy nastepnym
przeliczeniu: README mowilo „535 functions" przy 541 w mapie, „123 tests" przy
125 i „12,900 lines" przy 12 985. Trzy liczby, wszystkie z tego samego powodu.

## Czego ten test NIE robi

Nie sprawdza liczb, ktore sa POMIAREM Z PRZESZLOSCI: kosztow, udzialow
procentowych, wynikow testow A/B. Tamte opisuja jeden pomiar w jednym dniu
i nie maja sie zmieniac razem z drzewem — sa datowane w tekscie.

Pilnujemy wylacznie tych liczb, ktore OPISUJA STAN REPOZYTORIUM i da sie je
policzyc teraz.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo.
"""
import pathlib
import re
import subprocess
import sys

KORZEN = pathlib.Path(".").resolve()

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


def sledzone() -> list[str]:
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True,
                         encoding="utf-8")
    return [n for n in out.stdout.splitlines() if n.strip()]


PLIKI = sledzone()
README = pathlib.Path("README.md").read_text(encoding="utf-8")
MAPA = pathlib.Path("docs/FUNCTION_MAP.md").read_text(encoding="utf-8")


def z_mapy(etykieta: str) -> int | None:
    """Liczba z tabeli w `docs/FUNCTION_MAP.md` — pliku GENEROWANEGO.

    Bierzemy ja stamtad, a nie liczymy jeszcze raz wlasnym `ast`, bo dwie
    niezalezne implementacje tego samego licznika to dwa miejsca, ktore moga
    sie rozjechac. Mapa jest generowana i pilnowana przez audyt, wiec jest
    zrodlem prawdy; ten test sprawdza, czy README za nia nadaza.
    """
    m = re.search(r"\| %s \| (\d+) \|" % re.escape(etykieta), MAPA)
    return int(m.group(1)) if m else None


print("=== 1. LICZBY, KTORE OPISUJA DRZEWO ===")

funkcji = z_mapy("functions and methods")
modulow = z_mapy("modules")
sprawdz("mapa funkcji ma tabele licznikow", funkcji is not None and modulow is not None,
        "sprawdz naglowki w narzedzia/mapa_funkcji.py")

if funkcji is not None:
    m = re.search(r"\*\*(\d+) functions\*\*", README)
    sprawdz("README podaje liczbe funkcji", m is not None)
    if m:
        sprawdz("  i zgadza sie z mapa (%s)" % funkcji, int(m.group(1)) == funkcji,
                "README: %s, mapa: %s" % (m.group(1), funkcji))

if modulow is not None:
    m = re.search(r"in (\d+) modules", README)
    if m:
        sprawdz("liczba modulow zgadza sie z mapa (%s)" % modulow,
                int(m.group(1)) == modulow,
                "README: %s, mapa: %s" % (m.group(1), modulow))

testy = [n for n in PLIKI
         if "/tests/" in n and pathlib.Path(n).name.startswith("test_")
         and "/platne/" not in n]
m = re.search(r"(\d+) tests ·", README)
sprawdz("README podaje liczbe testow", m is not None)
if m:
    sprawdz("  i zgadza sie z drzewem (%d)" % len(testy),
            int(m.group(1)) == len(testy),
            "README: %s, plikow test_*.py: %d" % (m.group(1), len(testy)))

jzb = pathlib.Path("agent-v2/JAK_ZBUDOWANY_JEST_BOT.md")
if jzb.exists():
    ile = len(jzb.read_text(encoding="utf-8").splitlines())
    m = re.search(r"JAK_ZBUDOWANY_JEST_BOT\.md` — ([\d,]+) lines", README)
    sprawdz("README podaje dlugosc dokumentu", m is not None)
    if m:
        podane = int(m.group(1).replace(",", ""))
        # TOLERANCJA 50 WIERSZY, I TO JEST SWIADOME. Dokument przebudowuje sie
        # przy kazdej zmianie komentarza w kodzie, wiec wymaganie rownosci co
        # do wiersza kazaloby poprawiac README przy KAZDYM commicie — a wtedy
        # ludzie zaczna to obchodzic zamiast poprawiac.
        sprawdz("  i miesci sie w 50 wierszach od prawdy (%d)" % ile,
                abs(podane - ile) <= 50,
                "README: %d, plik: %d, roznica %d" % (podane, ile, abs(podane - ile)))

print()
print("=== 2. LICZBY W REPO_MAP ===")
rm = pathlib.Path("docs/REPO_MAP.md")
if rm.exists():
    tekst = rm.read_text(encoding="utf-8")
    briefy = [n for n in PLIKI if n.startswith("agent-v2/prompts/")
              and n.endswith(".md") and n.count("/") == 2]
    m = re.search(r"(\d+) briefs, ([\d,]+) lines", tekst)
    sprawdz("REPO_MAP podaje liczbe briefow", m is not None)
    if m:
        sprawdz("  liczba briefow zgadza sie (%d)" % len(briefy),
                int(m.group(1)) == len(briefy),
                "REPO_MAP: %s, plikow: %d" % (m.group(1), len(briefy)))
        linii = sum(len(pathlib.Path(n).read_text(encoding="utf-8").splitlines())
                    for n in briefy)
        podane = int(m.group(2).replace(",", ""))
        sprawdz("  i suma linii (%d)" % linii, podane == linii,
                "REPO_MAP: %d, policzone: %d" % (podane, linii))

    m = re.search(r"(\d+) test_\*\.py", tekst)
    if m:
        sprawdz("REPO_MAP: liczba testow zgadza sie (%d)" % len(testy),
                int(m.group(1)) == len(testy),
                "REPO_MAP: %s, plikow: %d" % (m.group(1), len(testy)))

print()
print("=== 3. KONTRDOWOD: TEST NAPRAWDE UMIE OBLAC ===")
# Bez tego nie wiadomo, czy sekcja 1 przechodzi dlatego, ze liczby sie zgadzaja,
# czy dlatego, ze zadnej nie znalazl.
_falszywy = README.replace("**%d functions**" % (funkcji or 0),
                           "**%d functions**" % ((funkcji or 0) + 7))
_m = re.search(r"\*\*(\d+) functions\*\*", _falszywy)
sprawdz("podmieniona liczba NIE zgadza sie z mapa",
        _m is not None and int(_m.group(1)) != funkcji,
        "kontrdowod nie zadzialal — sprawdz wzorzec")

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
