# -*- coding: utf-8 -*-
"""Wsad tematyczny przychodzi OD OBCEJ OSOBY. Sprawdzamy go jak obcy plik.

## Po co ten plik istnieje

`packs/*.toml` to material, ktory ma przychodzic przez pull requesty od ludzi
spoza projektu. To zmienia rachunek ryzyka: dotad kazdy plik konfiguracyjny
pisal ktos, kto ma juz dostep do tego drzewa.

Wsad musi wiec spelniac trzy rzeczy naraz, i kazda ma tu sekcje:

  1. NIE MOZE USTAWIC NICZEGO POZA TEMATEM I ZRODLAMI. Plik od obcej osoby,
     ktory ustawia uchwyt konta, sufit pieniedzy albo model, jest w tym
     projekcie niedopuszczalny — takze jako pomylka.
  2. MUSI PRZEJSC TE SAME WALIDATORY, co `konfiguracja.toml`. Bez drugiej
     implementacji regul: dwie kopie tej samej reguly to dwie rozne reguly.
  3. MUSI PRZEJSC REGULY STRUKTURALNE, ktore stawiamy kazdej konfiguracji —
     pula hasel szersza niz jeden przebieg, hasla trzymajace sie znakow niszy,
     siatka z zapasem. Wsad, ktory je lamie, daje bota szukajacego po ciasnej
     puli, a dowiedzialby sie o tym dopiero pierwszy pusty przebieg.

## I czwarta, osobna: WSADY NIE RUSZAJA CZYSTEJ BAZY

To jest warunek, na ktorym w ogole zgodzilismy sie je dodac. Zaden modul
agenta nie ma prawa czytac `packs/` — katalog jest material dla KREATORA,
a nie zrodlem wartosci dla bota. Gdyby ktos kiedys wpial go w `config.py`
„dla wygody", czysta baza przestalaby byc czysta i nikt by tego nie zauwazyl.
Sekcja 4 pilnuje wlasnie tego.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_pakiety.py
"""
import pathlib
import sys

sys.path.insert(0, "agent-v2/tests")
import wlasna_konfiguracja  # noqa: E402

wlasna_konfiguracja.pomin_gdy_bez_tomllib("czy wsady tematyczne sa poprawne")

sys.path.insert(0, "agent-v2")
sys.path.insert(0, "narzedzia")
import config    # noqa: E402
import pakiety   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


WSADY = pakiety.lista()

print("=== 1. KAZDY WSAD SIE WCZYTUJE I MA OPIS ===")
sprawdz("katalog packs/ nie jest pusty", bool(WSADY), len(WSADY))
wczytane = {}
for p in WSADY:
    try:
        wczytane[p] = pakiety.wczytaj(p)
        sprawdz("  %s" % p.stem, True)
    except pakiety.ZlyPakiet as exc:
        sprawdz("  %s" % p.stem, False, str(exc).splitlines()[0])

print()
print("=== 2. WSAD NIE USTAWIA NICZEGO POZA TEMATEM I ZRODLAMI ===")
# To jest warunek bezpieczenstwa, nie porzadku. Plik od obcej osoby nie moze
# dotknac konta ani pieniedzy — nawet przez pomylke autora.
for p, dane in wczytane.items():
    obce = sorted(set(dane) - {"pack"} - set(pakiety.DOZWOLONE_SEKCJE))
    sprawdz("  %s ma tylko %s" % (p.stem, "/".join(pakiety.DOZWOLONE_SEKCJE)),
            not obce, obce)

print()
print("=== 3. WARTOSCI PRZECHODZA WALIDATORY LOADERA I REGULY STRUKTURALNE ===")
for p in wczytane:
    try:
        gotowe, _uwagi = pakiety.waliduj(p)
    except pakiety.ZlyPakiet as exc:
        sprawdz("  %s: walidacja" % p.stem, False, str(exc).splitlines()[0])
        continue
    sprawdz("  %s: walidacja" % p.stem, True)
    lamie = pakiety.reguly_strukturalne(gotowe, config)
    sprawdz("  %s: reguly strukturalne" % p.stem, not lamie,
            ("\n        " + "\n        ".join(lamie)) if lamie else "")

print()
print("=== 4. WSADY NIE RUSZAJA CZYSTEJ BAZY ===")
# WARUNEK, NA KTORYM TE PLIKI W OGOLE ISTNIEJA. `packs/` jest materialem dla
# kreatora, nie zrodlem wartosci dla bota. Gdyby ktos wpial go w `config.py`
# „dla wygody", czysta baza przestalaby byc czysta i nikt by tego nie zobaczyl.
KOD_AGENTA = sorted(pathlib.Path("agent-v2").glob("*.py"))
czytajace = []
for m in KOD_AGENTA:
    tekst = m.read_text(encoding="utf-8")
    if "packs/" in tekst or "import pakiety" in tekst:
        czytajace.append(m.name)
sprawdz("zaden modul agenta nie siega do packs/", not czytajace, czytajace)

# I ze wartosci domyslne sa nadal wartosciami z `config.py`, a nie z wsadu.
# Bez tego powyzsze przechodziloby takze wtedy, gdyby wsad byl wpiety inaczej.
_pierwszy = pakiety.waliduj(WSADY[0])[0] if WSADY else {}
_nisza_wsadu = str(_pierwszy.get("temat.nisza") or "")
# Silnik nie ma niszy w ogole (pusta od 2026-09-05), wiec zaden wsad nie moze
# byc jego „domyslna" — asercja pilnuje, ze to sie nie odwroci.
# Mierzymy ZDJECIE SILNIKA (`DOMYSLNE_SILNIKA`), nie `config.NISZA`: darmowy
# test nadal wczytuje `konfiguracja.toml` operatora, wiec `config.NISZA` moze
# byc niepusta na jego maszynie — a pytanie jest o silnik, nie o operatora.
_nisza_silnika = config.DOMYSLNE_SILNIKA.get("NISZA")
sprawdz("NISZA silnika jest pusta i nie pochodzi z zadnego wsadu",
        _nisza_silnika == "" and all(
            str(pakiety.waliduj(p)[0].get("temat.nisza") or "") != _nisza_silnika
            for p in WSADY),
        config.NISZA)

print()
print("=== 5. KONTRDOWOD: CZY TE SPRAWDZENIA COKOLWIEK LAPIA ===")
# Bez tego caly plik przechodzilby takze wtedy, gdyby nie badal niczego.
_zly = {"pack": {"name": "x", "language": "English", "description": "x"},
        "temat": {"nisza": "x"},
        "pieniadze": {"sufit_dzienny_usd": 999.0}}
_ma_obce = sorted(set(_zly) - {"pack"} - set(pakiety.DOZWOLONE_SEKCJE))
sprawdz("wsad z sekcja `pieniadze` jest widziany jako zly",
        _ma_obce == ["pieniadze"], _ma_obce)

# Ciasna pula MUSI polec na regule strukturalnej.
_ciasny = {"temat.hasla_szukania": ("bread regulation",),
           "temat.znaki_niszy": ("regulat",),
           "temat.dziedziny": ("x",)}
sprawdz("wsad z jednym haslem lamie reguly",
        bool(pakiety.reguly_strukturalne(_ciasny, config)))

# A poprawny NIE lamie — inaczej regula odrzucalaby wszystko.
_dobry, _ = pakiety.waliduj(WSADY[0])
sprawdz("a prawdziwy wsad ich nie lamie",
        not pakiety.reguly_strukturalne(_dobry, config))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
