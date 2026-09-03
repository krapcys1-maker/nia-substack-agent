# -*- coding: utf-8 -*-
"""Przestawienie katalogu danych ma ruszac KOMPLET sciezek, nie jedna.

CO BYLO ZLE — zmierzone 2 wrzesnia 2026 na tym repozytorium.

`config.DB_PATH` jest liczone RAZ, przy imporcie, z `config.DATA_DIR`. Test,
ktory podstawia `config.DATA_DIR = katalog_tymczasowy`, NIE zmienia przez to
`config.DB_PATH` — ta nadal celuje w produkcyjna baze. Policzone drzewem
skladni: 21 plikow testowych przestawialo `DATA_DIR`, tylko 4 przestawialy
takze `DB_PATH`.

I NIE CHODZI O SAMA BAZE. Stalych liczonych przy imporcie z `DATA_DIR` jest
w tym kodzie 25 poza `config.py` — jedenascie w `stages.py`, siedem
w `browser.py`, reszta w `alarm.py`, `norma.py`, `kanal.py`, `run.py`,
`aktualne_modele.py` i `kopia_subskrybentow.py`. Kazda ma te sama wlasciwosc:
przestawienie `DATA_DIR` po imporcie nie rusza zadnej. Tedy weszly atrapy do
`tematy_przegrane.json` (`stages.PRZEGRANE_TEMATY`) — 294 z 400 wpisow.

ZE TO NIE JEST TEORIA. Sonda na calym zestawie (podmieniony `sqlite3.connect`,
otwarcia produkcji przekierowane, wiec pomiar niczego nie popsul) pokazala TRZY
pliki, ktore JUZ DZIS otwieraja produkcyjna baze:

    test_piec.py         -> stages.znajdz_ciekawostki
    test_pas_wydarzen.py -> stages.znajdz_ciekawostki
                              -> aktualne_modele.pobierz -> db.connect()
    test_martwe_hosty.py -> sqlite3.connect(config.DATA_DIR/"zasiew-produkcji.db")

Zaden z tych plikow nie ma w sobie slowa „connect" w miejscu, ktore to robi,
i zaden nie przestawia `DATA_DIR`. Szkody dzis nie ma tylko dlatego, ze
produkcyjny schemat jest aktualny — zmierzone na kopii: `db.connect()` na
bazie o jedna kolumne starszej dopisuje trzy kolumny, 12288 -> 24576 bajtow,
inny SHA. Kazda nowa pozycja w `db.NOWE_KOLUMNY` uzbraja to od nowa.

CZEGO TEN TEST PILNUJE — reguly, nie listy plikow:

  1. `config.uzyj_katalogu_danych` rusza KAZDA stala pochodna, ktora drzewo
     skladni znajdzie w kodzie produkcyjnym. Nowa stala dopisana jutro
     w `stages.py` jest sprawdzana bez zmiany w tym tescie.
  2. ZADEN plik w `tests/` nie przestawia `DATA_DIR` na piechote.
     To jest bramka, ktora oblewa, gdy ktos doda taki test.
  3. Odmowa otwarcia produkcyjnej bazy jest GLOSNA — wyjatek, nie `return`.

BEZ PYTESTA, zero sieci, zero platnych wywolan, produkcja nietknieta.
Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_komplet_sciezek.py
"""
import ast
import hashlib
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import config      # noqa: E402
import db          # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# --- BRAMKA PRODUKCJA --------------------------------------------------------
# Odcisk CALEGO katalogu danych przed i po. Poprzednim razem wlasnie porownanie
# odciskow wszystkich 68 plikow — a nie czytanie kodu — pokazalo, ze testy pisza
# do produkcji.
KATALOG_DANYCH = pathlib.Path(config.PRODUKCYJNY_KATALOG_DANYCH)
KOD = pathlib.Path("agent-v2")


def odciski():
    wynik = {}
    if not KATALOG_DANYCH.exists():
        return wynik
    for p in sorted(KATALOG_DANYCH.rglob("*")):
        if p.is_file() and "__pycache__" not in p.parts:
            try:
                wynik[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
            except OSError:
                wynik[str(p)] = "(nieczytelny)"
    return wynik


PRZED = odciski()


# --- drzewo skladni ----------------------------------------------------------

def drzewo(sciezka):
    return ast.parse(sciezka.read_text(encoding="utf-8"), filename=str(sciezka))


def czyta_data_dir(wyrazenie):
    """Czy to wyrazenie liczy sie z `DATA_DIR`."""
    for w in ast.walk(wyrazenie):
        if isinstance(w, ast.Attribute) and w.attr == "DATA_DIR":
            return True
        if isinstance(w, ast.Name) and w.id == "DATA_DIR":
            return True
    return False


def stale_pochodne(sciezka):
    """Stale liczone PRZY IMPORCIE z `DATA_DIR` — tylko poziom modulu."""
    nazwy = []
    for node in drzewo(sciezka).body:
        if isinstance(node, ast.Assign):
            cele = [t.id for t in node.targets if isinstance(t, ast.Name)]
            wart = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            cele, wart = [node.target.id], node.value
        else:
            continue
        if cele and wart is not None and czyta_data_dir(wart):
            nazwy.append(cele[0])
    return nazwy


def przypisania_data_dir(sciezka):
    """Miejsca, gdzie plik USTAWIA `<cos>.DATA_DIR = ...`."""
    linie = []
    for node in ast.walk(drzewo(sciezka)):
        cele = []
        if isinstance(node, ast.Assign):
            for t in node.targets:
                cele.extend(t.elts if isinstance(t, (ast.Tuple, ast.List)) else [t])
        elif isinstance(node, ast.AnnAssign):
            cele = [node.target]
        elif isinstance(node, ast.Call):
            f = node.func
            nazwa_f = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if nazwa_f == "setattr" and len(node.args) >= 2:
                a = node.args[1]
                if isinstance(a, ast.Constant) and a.value == "DATA_DIR":
                    linie.append(node.lineno)
            continue
        for c in cele:
            # TYLKO atrybut modulu (`config.DATA_DIR`). Gole `DATA_DIR = ...`
            # w ciele klasy-atrapy to wlasny obiekt testu, nie nasz config.
            if isinstance(c, ast.Attribute) and c.attr == "DATA_DIR":
                linie.append(node.lineno)
    return sorted(set(linie))


print("=== 1. JEDNO WYWOLANIE RUSZA KOMPLET SCIEZEK POCHODNYCH ===")
# Lista bierze sie z DRZEWA SKLADNI kodu produkcyjnego, nie z recznego spisu:
# spis trzeba pamietac zaktualizowac, a ten projekt ma udokumentowane, ze
# prosba w dokumencie nie jest bramka.
oczekiwane = {}
for p in sorted(KOD.glob("*.py")):
    nazwy = [n for n in stale_pochodne(p) if n != "DATA_DIR"]
    if nazwy and p.stem != "config":
        oczekiwane[p.stem] = nazwy

sprawdz("drzewo znalazlo stale pochodne w kodzie produkcyjnym",
        len(oczekiwane) >= 6, sorted(oczekiwane))

moduly = {}
for nazwa in sorted(oczekiwane):
    try:
        moduly[nazwa] = __import__(nazwa)
    except Exception as exc:                      # noqa: BLE001
        sprawdz("import %s" % nazwa, False, exc)

KAT = pathlib.Path(tempfile.mkdtemp(prefix="komplet-"))
przed_ruchem = {}
for nazwa, mod in moduly.items():
    for stala in oczekiwane[nazwa]:
        if hasattr(mod, stala):
            przed_ruchem[(nazwa, stala)] = getattr(mod, stala)

stare = config.uzyj_katalogu_danych(KAT)
try:
    nie_ruszone = []
    for (nazwa, stala), wartosc in sorted(przed_ruchem.items()):
        teraz = getattr(moduly[nazwa], stala)
        if KAT not in pathlib.Path(teraz).parents and pathlib.Path(teraz) != KAT:
            nie_ruszone.append("%s.%s -> %s" % (nazwa, stala, teraz))
    sprawdz("wszystkie %d stalych pochodnych przeniesione" % len(przed_ruchem),
            not nie_ruszone, nie_ruszone)
    sprawdz("`config.DB_PATH` w katalogu testowym",
            config.DB_PATH.parent == KAT, config.DB_PATH)
    sprawdz("`config.ARTICLES_DIR` w katalogu testowym",
            config.ARTICLES_DIR.parent == KAT, config.ARTICLES_DIR)
    sprawdz("`config.DATA_DIR` w katalogu testowym",
            config.DATA_DIR == KAT, config.DATA_DIR)
    # Sciezki, ktore NIE sa danymi konta, maja zostac nietkniete: inaczej
    # przekierowanie zabieraloby testom prompty i korpus stylu.
    sprawdz("`PROMPTS_DIR` nietkniety",
            config.PROMPTS_DIR == config.AGENT_DIR / "prompts", config.PROMPTS_DIR)
    sprawdz("`STYLE_CORPUS` nietkniety",
            config.STYLE_CORPUS.parent.parent == config.AGENT_DIR / "prompts",
            config.STYLE_CORPUS)
finally:
    config.przywroc_katalog_danych(stare)

print()
print("=== 2. PRZYWROCENIE ODDAJE KAZDA SCIEZKE ===")
# Bez tego nastepny plik w petli dziedziczy podmieniony katalog i mierzy
# co innego, niz mysli.
zle = []
for (nazwa, stala), wartosc in sorted(przed_ruchem.items()):
    if getattr(moduly[nazwa], stala) != wartosc:
        zle.append("%s.%s" % (nazwa, stala))
sprawdz("wszystkie stale wrocily na miejsce", not zle, zle)
sprawdz("`config.DB_PATH` wrocila do produkcji",
        config.pod_produkcyjnymi_danymi(config.DB_PATH), config.DB_PATH)

print()
print("=== 3. ZADEN TEST NIE PRZESTAWIA `DATA_DIR` NA PIECHOTE ===")
# TO JEST TA BRAMKA. Oblewa, gdy ktos doda test podstawiajacy sam `DATA_DIR`.
# TEN plik jest jedynym wyjatkiem i to nie jest furtka: sekcja 5 MUSI odtworzyc
# stary sposob, zeby pokazac, ze bez poprawki baza celowala w produkcje.
# Kontrdowod, ktory nie moze uzyc bledu, ktory obala, nie jest kontrdowodem.
JA = pathlib.Path(__file__).name

winni = {}
for p in sorted((KOD / "tests").glob("test_*.py")):
    if p.name == JA:
        continue
    linie = przypisania_data_dir(p)
    if linie:
        winni[p.name] = linie
sprawdz("zaden plik testowy nie ustawia `.DATA_DIR` wprost",
        not winni,
        "; ".join("%s:%s" % (k, v) for k, v in sorted(winni.items())))

# Ta sama pulapka przepisana do PODSTAWKI dla podprocesu jest tak samo grozna,
# a drzewo skladni jej nie widzi — to zwykly napis.
w_napisach = {}
for p in sorted((KOD / "tests").glob("test_*.py")):
    if p.name == JA:
        continue
    trafienia = []
    for node in ast.walk(drzewo(p)):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if "DATA_DIR =" in node.value or "DATA_DIR=" in node.value:
                trafienia.append(node.lineno)
    if trafienia:
        w_napisach[p.name] = sorted(set(trafienia))
sprawdz("ani w podstawkach dla podprocesow",
        not w_napisach,
        "; ".join("%s:%s" % (k, v) for k, v in sorted(w_napisach.items())))

print()
print("=== 4. ODMOWA OTWARCIA PRODUKCYJNEJ BAZY JEST GLOSNA ===")
sprawdz("ten proces jest rozpoznany jako darmowy test",
        config.W_TESCIE is True, "argv[0]=%r" % sys.argv[0])
sprawdz("`WOLNO_TKNAC_PRODUKCYJNA_BAZE` jest opuszczone",
        config.WOLNO_TKNAC_PRODUKCYJNA_BAZE is False)

wyjatek = None
try:
    db.connect(config.DB_PATH).close()
except db.ProdukcyjnaBazaWTescie as exc:
    wyjatek = exc
except Exception as exc:                          # noqa: BLE001
    wyjatek = exc
sprawdz("`db.connect()` na produkcji RZUCA WYJATEK",
        isinstance(wyjatek, db.ProdukcyjnaBazaWTescie), type(wyjatek).__name__)
sprawdz("i wyjatek mowi, jak to naprawic",
        "uzyj_katalogu_danych" in str(wyjatek), str(wyjatek)[:80])

# Rozpoznajemy takze podkatalog — baza przeniesiona o poziom nizej nie moze
# wymknac sie zaporze po cichu.
for opis, sciezka, oczekiwany in (
    ("prawdziwa baza", KATALOG_DANYCH / "agent-v2.db", True),
    ("podkatalog produkcji", KATALOG_DANYCH / "articles" / "x.db", True),
    ("sam katalog danych", KATALOG_DANYCH, True),
    ("katalog tymczasowy", KAT / "agent-v2.db", False),
):
    sprawdz("%-22s -> produkcja: %s" % (opis, oczekiwany),
            config.pod_produkcyjnymi_danymi(sciezka) is oczekiwany)

# A do katalogu testowego ma otwierac normalnie — inaczej zapora nie jest
# ochrona, tylko wylaczeniem bazy w testach.
stare = config.uzyj_katalogu_danych(KAT)
try:
    conn = db.connect()
    conn.execute("SELECT COUNT(*) FROM runs").fetchone()
    conn.close()
    poszlo = True
except Exception as exc:                          # noqa: BLE001
    poszlo = False
    print("      (%s)" % exc)
finally:
    config.przywroc_katalog_danych(stare)
sprawdz("a do katalogu testowego otwiera normalnie", poszlo)

print()
print("=== 5. KONTRDOWOD: TAK WYGLADALO TO PRZED POPRAWKA ===")
# Odtwarzamy stary sposob — podstawienie SAMEGO `DATA_DIR` — i pokazujemy, ze
# `DB_PATH` zostaje wycelowana w produkcje. Bez tej sekcji sekcja 1 moglaby
# przechodzic dlatego, ze `DB_PATH` i tak nigdy nie byla produkcyjna.
kat2 = pathlib.Path(tempfile.mkdtemp(prefix="kontrdowod-"))
oryg_data, oryg_db = config.DATA_DIR, config.DB_PATH
try:
    config.DATA_DIR = kat2                        # stary sposob, na piechote
    sprawdz("po samym `DATA_DIR` baza NADAL celuje w produkcje",
            config.pod_produkcyjnymi_danymi(config.DB_PATH), config.DB_PATH)
    sprawdz("czyli `DB_PATH` nie poszla za `DATA_DIR`",
            config.DB_PATH.parent != kat2, config.DB_PATH)
    # I dopiero zapora zamienia ten cichy zapis w glosny blad.
    zlapane = None
    try:
        db.connect().close()
    except db.ProdukcyjnaBazaWTescie as exc:
        zlapane = exc
    sprawdz("i dopiero zapora to zatrzymuje", zlapane is not None)
finally:
    config.DATA_DIR, config.DB_PATH = oryg_data, oryg_db

# Druga polowa kontrdowodu: z podniesiona dzwignia zapora PRZEPUSZCZA. Gdyby
# odmowa brala sie z czegos innego niz nasz warunek, ta sekcja by tego nie
# odroznila.
config.WOLNO_TKNAC_PRODUKCYJNA_BAZE = True
try:
    db._odmow_produkcji(config.DB_PATH)
    przepuszcza = True
except Exception:                                 # noqa: BLE001
    przepuszcza = False
finally:
    config.WOLNO_TKNAC_PRODUKCYJNA_BAZE = False
sprawdz("z podniesiona dzwignia zapora przepuszcza", przepuszcza)

print()
print("=== 6. PRODUKCJA NIETKNIETA PRZEZ CALY TEN PLIK ===")
PO = odciski()
doszly = sorted(set(PO) - set(PRZED))
znikly = sorted(set(PRZED) - set(PO))
zmienione = sorted(k for k in set(PRZED) & set(PO) if PRZED[k] != PO[k])
sprawdz("zaden plik w `data/` nie zmienil odcisku", not zmienione, zmienione)
sprawdz("zaden nie doszedl", not doszly, doszly)
sprawdz("zaden nie znikl", not znikly, znikly)
sprawdz("policzone na %d plikach" % len(PRZED), len(PRZED) > 0)

print()
print("=" * 62)
print("ZDANE: %d    OBLANE: %d" % (zdane, oblane))
sys.exit(1 if oblane else 0)
