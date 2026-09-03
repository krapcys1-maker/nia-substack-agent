"""Historia porazek ma wracac do dyskoverii.

Powod: `fda.gov` przepadl 3 razy na 3, a artykul o SPF dotyczyl przepisow FDA.
Najwazniejsze zrodlo bylo systemowo nieosiagalne, a slot w limicie dziesieciu
adresow i tak byl na nie wydawany — bo tabela `sources` zapisywala porazki
od poczatku i nikt ich nigdy nie czytal.
"""
import sqlite3
import sys

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


def baza(wiersze):
    """Baza w pamieci. Trzeci element to powod porazki, domyslnie blokada."""
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE sources (id INTEGER PRIMARY KEY, run_id INT, at TEXT,"
              " url TEXT, domain TEXT, title TEXT, source_class TEXT,"
              " fetched_ok INT, fail_reason TEXT)")
    for w in wiersze:
        domena, udane = w[0], w[1]
        powod = w[2] if len(w) > 2 else ("HTTP 403" if not udane else None)
        c.execute("INSERT INTO sources (at, url, domain, fetched_ok, fail_reason)"
                  " VALUES ('t', 'u', ?, ?, ?)", (domena, udane, powod))
    return c


print("=== 1. HOST, KTORY NIGDY NIE ZADZIALAL, TRAFIA NA LISTE ===")
c = baza([("fda.gov", 0), ("fda.gov", 0), ("fda.gov", 0),
          ("law.cornell.edu", 1), ("law.cornell.edu", 1)])
lista = stages.hosty_ktore_nigdy_nie_dzialaly(c)
sprawdz("fda.gov na liscie", "fda.gov" in lista, lista)
sprawdz("law.cornell.edu NIE na liscie", "law.cornell.edu" not in lista, lista)

print()
print("=== 2. PROG DWOCH PROB — JEDNA WPADKA TO NIE WLASCIWOSC HOSTA ===")
c = baza([("chwilowa-awaria.gov", 0)])
sprawdz("jedna porazka nie skresla hosta",
        stages.hosty_ktore_nigdy_nie_dzialaly(c) == [],
        stages.hosty_ktore_nigdy_nie_dzialaly(c))
c = baza([("chwilowa-awaria.gov", 0), ("chwilowa-awaria.gov", 0)])
sprawdz("dwie porazki juz tak",
        "chwilowa-awaria.gov" in stages.hosty_ktore_nigdy_nie_dzialaly(c))

print()
print("=== 3. JEDNO UDANE POBRANIE RATUJE HOSTA (kontrdowod) ===")
c = baza([("czasem-dziala.gov", 0), ("czasem-dziala.gov", 0),
          ("czasem-dziala.gov", 0), ("czasem-dziala.gov", 1)])
sprawdz("host z jednym sukcesem na cztery proby zostaje",
        stages.hosty_ktore_nigdy_nie_dzialaly(c) == [],
        stages.hosty_ktore_nigdy_nie_dzialaly(c))

print()
print("=== 4. BRAK TABELI NIE WYWALA ETAPU ===")
pusta = sqlite3.connect(":memory:")
sprawdz("baza bez tabeli sources oddaje pusta liste",
        stages.hosty_ktore_nigdy_nie_dzialaly(pusta) == [])

print()
print("=== 6. PORAZKA NA PUSTEJ TRESCI NIE SKRESLA HOSTA ===")
# Byly to niemal wylacznie PDF-y, ktorych wtedy nie umielismy czytac.
# easa.europa.eu wypadl 2 na 2 wlasnie tak — a po dodaniu obslugi PDF-ow
# oddal 94 tys. znakow specyfikacji certyfikacyjnych.
c = baza([("easa.europa.eu", 0, "za malo tresci (0 znakow)"),
          ("easa.europa.eu", 0, "tez pusto w przegladarce (0 znakow)")])
sprawdz("host padajacy na PDF-ach NIE jest martwy",
        stages.hosty_ktore_nigdy_nie_dzialaly(c) == [],
        stages.hosty_ktore_nigdy_nie_dzialaly(c))

c = baza([("blokuje.gov", 0, "HTTP 403"), ("blokuje.gov", 0, "host odmowil automatowi")])
sprawdz("ale host, ktory nas BLOKUJE, nadal jest",
        "blokuje.gov" in stages.hosty_ktore_nigdy_nie_dzialaly(c))

c = baza([("mieszany.gov", 0, "HTTP 401"), ("mieszany.gov", 0, "za malo tresci (0 znakow)")])
sprawdz("jedna blokada plus jedno puste to za malo",
        stages.hosty_ktore_nigdy_nie_dzialaly(c) == [],
        stages.hosty_ktore_nigdy_nie_dzialaly(c))

print()
print("=== 5. NA PRAWDZIWEJ HISTORII ===")
import config   # noqa: E402
# TA SEKCJA CELOWO SIEGA DO PRODUKCJI i tak ma zostac: cala jej wartosc polega
# na tym, ze liczy sie na PRAWDZIWEJ historii zrodel, a nie na atrapie.
# Przekierowanie na katalog tymczasowy zabraloby jej sens.
#
# Ale otwieramy TYLKO DO ODCZYTU (`mode=ro`), bo zwykle `sqlite3.connect`
# otwiera do zapisu i ZAKLADA plik, gdy go nie ma — czyli test potrafilby
# zostawic smiec w produkcyjnym katalogu danych. Brak pliku nadal konczy sie
# wyjatkiem i pominieciem sekcji, dokladnie jak przedtem.
try:
    _zasiew = (config.DATA_DIR / "zasiew-produkcji.db").resolve()
    prod = sqlite3.connect("%s?mode=ro" % _zasiew.as_uri(), uri=True)
    prod.execute("SELECT 1 FROM sources LIMIT 1")
except Exception:
    prod = None
if prod is None:
    print("  (brak lokalnej kopii produkcji — pomijam)")
else:
    lista = stages.hosty_ktore_nigdy_nie_dzialaly(prod)
    print("  wykryte martwe hosty: %s" % (", ".join(lista) or "brak"))
    sprawdz("fda.gov wykryty na prawdziwych danych", "fda.gov" in lista, lista)
    dobre = {"law.cornell.edu", "legislation.gov.uk", "patents.google.com"}
    sprawdz("zadne dzialajace zrodlo nie trafilo na liste",
            not (dobre & set(lista)), dobre & set(lista))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
