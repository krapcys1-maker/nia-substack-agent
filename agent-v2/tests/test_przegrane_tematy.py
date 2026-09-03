"""Dziennik przegranych tematow: co przegralo, z czym i NA CZYM.

Skaut oddaje dziesiec tematow, wygrywa jeden, dziewiec znikalo bez sladu — do
bazy trafia tylko zwyciezca, a log mowil najwyzej „NA ARTYKUL: 6 z 10". Gdy
skaut oddal ZERO tematow artykulowych, moja pierwsza diagnoza byla bledna:
twierdzilem, ze model nie umie podac precedensow przed researchem, a on podal
wzorcowy w tym samym przebiegu, tylko jeden przy progu dwa. Nie bylo czego
przeczytac, wiec zgadywalem.

To NIE jest `discarded_seeds` z prototypu v3. Tam model relacjonuje wlasne
rozumowanie — samoocena, ktorej nie da sie sprawdzic i ktora wyrownuje sie do
stalej tak samo jak samooceny 1.0 i watki po trzy. Tu powod liczy KOD z tego,
co i tak policzyl, zeby posortowac.

DWIE RZECZY, KTORYCH TEN DZIENNIK ROBIC NIE MOZE, i obie sa tu sprawdzane:
nie moze niczego blokowac (temat bez drugiego precedensu dzis moze go miec za
pol roku) i nie moze zatrzymac przebiegu, gdy zapis sie nie uda.
"""
import ast
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
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


def _dane():
    tematy = [{"title": "Wieza przestaje odpowiadac"},
              {"title": "Nazwisko zmarlego na karcie"},
              {"title": "Karta hotelowa"},
              {"title": "Zraszacze"}]
    oceny = [
        {"index": 0, "feasible": True, "depth": "RICH", "confidence": 0.9,
         "expected_primary_sources": 4},
        {"index": 1, "feasible": True, "depth": "RICH", "confidence": 0.8,
         "expected_primary_sources": 3},
        {"index": 2, "feasible": True, "depth": "SINGLE", "confidence": 0.9,
         "expected_primary_sources": 2},
        {"index": 3, "feasible": True, "depth": "THIN", "confidence": 0.5,
         "expected_primary_sources": 1},
    ]
    for t, o in zip(tematy, oceny):
        t.update({"nosny": True, "na_artykul": o["depth"] == "RICH",
                  "pozycja": 0, "ile_watkow": 3, "nasycony": False})
    return tematy, oceny


def _przebieg(katalog, tematy=None, oceny=None):
    stary = stages.PRZEGRANE_TEMATY
    stages.PRZEGRANE_TEMATY = pathlib.Path(katalog) / "tematy_przegrane.json"
    try:
        t, o = (tematy, oceny) if tematy else _dane()
        wybrany, _ = stages.pick_topic(t, o, run_id=99)
        plik = stages.PRZEGRANE_TEMATY
        wpisy = json.loads(plik.read_text(encoding="utf-8")) if plik.exists() else []
        return wybrany, wpisy
    finally:
        stages.PRZEGRANE_TEMATY = stary


print("=== 1. POWOD NAZYWA SKLADNIK, KTORY ROZSTRZYGNAL ===")
with tempfile.TemporaryDirectory() as tmp:
    wybrany, wpisy = _przebieg(tmp)
    sprawdz("wygral temat artykulowy o najwyzszej pewnosci",
            wybrany["title"] == "Wieza przestaje odpowiadac", wybrany["title"])
    sprawdz("zapisano wszystkich przegranych", len(wpisy) == 3, len(wpisy))
    sprawdz("zwyciezcy NIE ma wsrod przegranych",
            all(w["tytul"] != wybrany["title"] for w in wpisy))
    powody = {w["tytul"]: w["powod"] for w in wpisy}
    sprawdz("temat nieartykulowy przegral na `artykulowy`",
            powody.get("Karta hotelowa", "").startswith("artykulowy:"),
            powody.get("Karta hotelowa"))
    sprawdz("a artykulowy o nizszej pewnosci — na `confidence`",
            powody.get("Nazwisko zmarlego na karcie", "").startswith("confidence:"),
            powody.get("Nazwisko zmarlego na karcie"))
    # Powod ma podawac OBIE wartosci, inaczej nie da sie z niego nic wyliczyc.
    sprawdz("powod podaje wartosc przegranego i zwyciezcy",
            all(" wobec " in w["powod"] for w in wpisy))
    sprawdz("kazdy wpis wie, z kim przegral",
            all(w["wygral"] == wybrany["title"] for w in wpisy))
    sprawdz("i ma run_id oraz date", all(w["run_id"] == 99 and w["kiedy"] for w in wpisy))

print()
print("=== 2. NAZWY SKLADNIKOW ZGADZAJA SIE Z KLUCZEM SORTOWANIA ===")
# Rozjazd miedzy krotka `kolejnosc` a lista SKLADNIKI_KLUCZA dalby powod
# wskazujacy na NIEWLASCIWE pole — czyli klamstwo w dzienniku, ktory sluzy
# wylacznie do diagnozy. Liczymy elementy krotki wprost ze zrodla.
_src = pathlib.Path("agent-v2/stages.py").read_text(encoding="utf-8")
_ile = None
for _w in ast.walk(ast.parse(_src)):
    if isinstance(_w, ast.FunctionDef) and _w.name == "kolejnosc":
        for _r in ast.walk(_w):
            if isinstance(_r, ast.Return) and isinstance(_r.value, ast.Tuple):
                _ile = len(_r.value.elts)
sprawdz("znalazlem krotke sortujaca", _ile is not None, _ile)
sprawdz("i ma tyle elementow, ile nazw",
        _ile == len(stages.SKLADNIKI_KLUCZA),
        "krotka=%s nazwy=%d" % (_ile, len(stages.SKLADNIKI_KLUCZA)))

print()
print("=== 3. DZIENNIK NIE JEST BRAMKA ===")
# Temat odrzucony dzis, bo brakowalo mu drugiego precedensu, moze go miec za
# pol roku. Indeks kandydatow na NOTKI dziala odwrotnie i to jest celowe.
# Nie liczymy wystapien "na oko" — sprawdzamy, gdzie SIEDZA. Kazde odwolanie
# do dziennika ma byc w `zapisz_przegranych` albo w samej definicji sciezki.
# Odwolanie gdziekolwiek indziej znaczy, ze ktos zaczal go czytac przy decyzji.
_w_zapisie = 0
for _f in ast.walk(ast.parse(_src)):
    if isinstance(_f, ast.FunctionDef) and _f.name == "zapisz_przegranych":
        _w_zapisie = (ast.get_source_segment(_src, _f) or "").count("PRZEGRANE_TEMATY")
_poza = _src.count("PRZEGRANE_TEMATY") - _w_zapisie - 1   # -1: definicja sciezki
sprawdz("poza funkcja zapisu nikt dziennika nie dotyka", _poza == 0,
        "%d odwolan poza `zapisz_przegranych`" % _poza)
sprawdz("a funkcja zapisu naprawde go uzywa", _w_zapisie >= 2, _w_zapisie)
sprawdz("zapis jest jedynym miejscem, ktore go dotyka",
        "PRZEGRANE_TEMATY.read_text" in _src
        and _src.count("PRZEGRANE_TEMATY.read_text") == 1)
# KONTRDOWOD: ten sam temat podany drugi raz musi nadal moc WYGRAC.
with tempfile.TemporaryDirectory() as tmp:
    _przebieg(tmp)                       # runda 1 — „Karta hotelowa" przegrywa
    t, o = _dane()
    tylko_karta = [t[2]]
    ocena = [dict(o[2], index=0)]
    stary = stages.PRZEGRANE_TEMATY
    stages.PRZEGRANE_TEMATY = pathlib.Path(tmp) / "tematy_przegrane.json"
    try:
        wybrany2, _ = stages.pick_topic(tylko_karta, ocena, run_id=100)
    finally:
        stages.PRZEGRANE_TEMATY = stary
    sprawdz("temat, ktory raz przegral, moze pozniej wygrac",
            wybrany2["title"] == "Karta hotelowa", wybrany2["title"])

print()
print("=== 4. DZIENNIK NIE MOZE ZATRZYMAC PRZEBIEGU ===")
# Artykul jest wazniejszy od notatki o tym, dlaczego inny temat nim nie zostal.
stary = stages.PRZEGRANE_TEMATY
# SCIEZKA, KTORA NIE ZAPISZE SIE NIGDZIE. Bylo tu "Z:/nie-ma-takiego-dysku" —
# na Windowsie faktycznie nie ma takiego dysku, ale na Linuksie "Z:" to zwykla,
# legalna nazwa katalogu. Zapis sie tam UDAWAL, a asercja obok twierdzila, ze
# byl nieudany: test przechodzil na serwerze nie dlatego, ze kod przezyl awarie,
# tylko dlatego, ze awarii nie bylo. Zostawial przy okazji smiec w repozytorium.
#
# Katalog nie moze powstac POD PLIKIEM i to jest prawda na obu systemach.
with tempfile.TemporaryDirectory() as tmp:
    zapora = pathlib.Path(tmp) / "to-jest-plik"
    zapora.write_text("nie katalog", encoding="utf-8")
    try:
        stages.PRZEGRANE_TEMATY = zapora / "x.json"
        t, o = _dane()
        wybrany3, _ = stages.pick_topic(t, o, run_id=101)
        sprawdz("nieudany zapis nie przerywa wyboru tematu", True)
        sprawdz("i temat jest ten sam co przy udanym zapisie",
                wybrany3["title"] == "Wieza przestaje odpowiadac")
        # KONTRDOWOD: gdyby zapis jednak przeszedl, test bada cos innego niz
        # mysli — i ma o tym powiedziec, zamiast zaliczyc sie po cichu.
        sprawdz("zapis NAPRAWDE sie nie udal (inaczej to nie ten test)",
                not (zapora / "x.json").exists() and zapora.is_file())
    except Exception as exc:
        sprawdz("nieudany zapis nie przerywa wyboru tematu", False,
                "%s: %s" % (type(exc).__name__, exc))
    finally:
        stages.PRZEGRANE_TEMATY = stary

with tempfile.TemporaryDirectory() as tmp:
    uszkodzony = pathlib.Path(tmp) / "tematy_przegrane.json"
    uszkodzony.write_text("to nie jest JSON {{{", encoding="utf-8")
    stary = stages.PRZEGRANE_TEMATY
    stages.PRZEGRANE_TEMATY = uszkodzony
    try:
        ile = stages.zapisz_przegranych([{"tytul": "x", "powod": "y"}], run_id=1)
        sprawdz("uszkodzony dziennik to pusty dziennik, nie awaria", ile == 1)
        sprawdz("i zostaje nadpisany poprawnym",
                len(json.loads(uszkodzony.read_text(encoding="utf-8"))) == 1)
    finally:
        stages.PRZEGRANE_TEMATY = stary

print()
print("=== 5. DZIENNIK NIE ROSNIE BEZ KONCA ===")
with tempfile.TemporaryDirectory() as tmp:
    stary = stages.PRZEGRANE_TEMATY
    stages.PRZEGRANE_TEMATY = pathlib.Path(tmp) / "d.json"
    try:
        for _ in range(30):
            stages.zapisz_przegranych(
                [{"tytul": "t%d" % i, "powod": "p"} for i in range(30)], run_id=1)
        ile = len(json.loads(stages.PRZEGRANE_TEMATY.read_text(encoding="utf-8")))
    finally:
        stages.PRZEGRANE_TEMATY = stary
    sprawdz("trzymamy sufit wpisow", ile == stages.ILE_PRZEGRANYCH_TRZYMAMY, ile)
sprawdz("pusta lista nie tworzy pliku", stages.zapisz_przegranych([]) == 0)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
