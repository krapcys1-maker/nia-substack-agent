# -*- coding: utf-8 -*-
"""Stala wyprowadzona z pola konfiguracji ma sie zmieniac RAZEM Z NIM.

## Po co ten plik istnieje

`config.py` wczytuje `konfiguracja.toml` na SAMYM KONCU. Kazda stala wyliczona
wyzej z pola konfiguracji trzyma wiec wartosc DOMYSLNA — i nic tego nie zglasza,
bo wartosc domyslna jest poprawna sama w sobie.

Ten plik opisuje te pulapke od dawna przy `DB_PATH`: „liczone RAZ, przy
imporcie; test, ktory podstawia `DATA_DIR`, NIE zmienia przez to `DB_PATH`".
Tam poprawka polegala na przejsciu po zaimportowanych modulach. Tutaj chodzi
o cos wezszego i wczesniejszego: stale w SAMYM `config.py`.

ZNALEZIONE 4 wrzesnia 2026 na `FETCH_USER_AGENT` — naglowku, ktory widzi KAZDA
odwiedzona strona i ktory jest jedynym miejscem, gdzie bot przedstawia sie
z nazwy. Skladany z `NAZWA_MARKI`, wyliczany piecset linii przed wczytaniem
konfiguracji: konto z wlasna nazwa przedstawialoby sie nazwa domyslna.

## Czego ten test NIE robi

Nie sprawdza wszystkich pol konfiguracji — sprawdza WSZYSTKIE STALE, ktore
mozna wyprowadzic, na jednym polu, ktore da sie ustawic bez skutkow ubocznych
(`konto.nazwa_marki`). Podstawiamy tam napis, ktorego nie ma nigdzie indziej
w repozytorium, i zadamy, zeby zadna stala w `config` nie niosla juz wartosci
domyslnej „Your Publication".

To lapie CALA KLASE, a nie jedna stala: nowa pochodna dopisana jutro i liczona
w zlym miejscu obleje tutaj, nie na produkcji.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_pochodne_po_konfiguracji.py
"""
import importlib
import pathlib
import shutil
import sys

sys.path.insert(0, "agent-v2")

PLIK = pathlib.Path("agent-v2/konfiguracja.toml")
MARKA = "Probna Marka Testowa"
ZNACZNIK = "ProbnaMarkaTestowa"

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# KOPIA ZAPASOWA CUDZEGO PLIKU. Operator moze miec wlasna konfiguracje i test
# nie ma prawa jej skasowac — to ta sama zasada, co „darmowy test nie dotyka
# produkcyjnych danych".
kopia = None
if PLIK.exists():
    kopia = PLIK.with_suffix(".toml.przed-testem")
    shutil.copy2(PLIK, kopia)

try:
    PLIK.write_text('[konto]\nnazwa_marki = "%s"\n' % MARKA, encoding="utf-8")

    import config
    importlib.reload(config)

    print("=== 1. KONFIGURACJA W OGOLE WESZLA ===")
    sprawdz("NAZWA_MARKI wzieta z pliku", config.NAZWA_MARKI == MARKA,
            config.NAZWA_MARKI)

    print()
    print("=== 2. ZADNA STALA NIE TRZYMA JUZ WARTOSCI DOMYSLNEJ ===")
    # Szukamy po WARTOSCI, nie po nazwie stalej — lista nazw wymagalaby
    # pamietania o dopisywaniu do niej, a to jest dokladnie ta wada, ktora
    # ten projekt sciga.
    zostaly = []
    for nazwa in dir(config):
        if not nazwa.isupper() or nazwa.startswith("_"):
            continue
        wartosc = getattr(config, nazwa)
        if isinstance(wartosc, str) and ("Your Publication" in wartosc
                                         or "YourPublication" in wartosc):
            zostaly.append("%s=%r" % (nazwa, wartosc[:70]))
    sprawdz("zadna stala nie niesie domyslnej nazwy marki", not zostaly,
            "; ".join(zostaly))

    print()
    print("=== 3. NAGLOWEK KLIENTA NAPRAWDE SIE ZMIENIL ===")
    # Nazwana wprost, bo to ona ujawnila cala klase i jest widoczna na zewnatrz:
    # kazda odwiedzona strona zobaczy ten napis w logu.
    sprawdz("FETCH_USER_AGENT niesie skonfigurowana marke",
            ZNACZNIK in config.FETCH_USER_AGENT, config.FETCH_USER_AGENT)
    sprawdz("i nadal wyglada jak poprawny User-Agent",
            config.FETCH_USER_AGENT.startswith("Mozilla/5.0 (compatible;")
            and config.FETCH_USER_AGENT.endswith(")"),
            config.FETCH_USER_AGENT)
    sprawdz("bez spacji w samym znaczniku",
            " " not in config.FETCH_USER_AGENT.split(";")[1].strip(),
            config.FETCH_USER_AGENT)

    print()
    print("=== 4. KONTRDOWOD: TEST ROZROZNIA ===")
    # Bez tego sekcja 2 przechodzilaby takze wtedy, gdyby szukala wartosci,
    # ktorej w kodzie nie ma nigdy. Pokazujemy, ze przy DOMYSLNEJ konfiguracji
    # ta sama wartosc W STALEJ JEST.
    PLIK.unlink()
    importlib.reload(config)
    sprawdz("bez pliku konfiguracji marka wraca do domyslnej",
            config.NAZWA_MARKI == "Your Publication", config.NAZWA_MARKI)
    sprawdz("i wtedy naglowek NIESIE wartosc domyslna",
            "YourPublication" in config.FETCH_USER_AGENT,
            config.FETCH_USER_AGENT)

finally:
    if PLIK.exists():
        PLIK.unlink()
    if kopia is not None:
        shutil.move(str(kopia), str(PLIK))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
