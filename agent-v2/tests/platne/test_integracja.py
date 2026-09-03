"""Prawdziwy przebieg dnia BEZ publikowania, na kopii bazy.

Sprawdza to, czego testy jednostkowe nie dotknely: czy `dzien()` naprawde
wola nowy rozdzielnik i czy caly przebieg przechodzi od poczatku do konca.
Produkcja ma zostac nietknieta — pilnujemy tego przed i po.
"""
import hashlib
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import browser  # noqa: E402
import config   # noqa: E402
import db       # noqa: E402
import run      # noqa: E402


def odcisk(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()[:16] \
        if pathlib.Path(p).exists() else "brak"


PILNOWANE = [config.DB_PATH,
             config.DATA_DIR / "zuzyte_fakty.json",
             config.DATA_DIR / "promocja.json",
             config.DATA_DIR / "dziennik.jsonl"]
PRZED = {str(p): odcisk(p) for p in PILNOWANE}
print("=== ODCISKI PRODUKCJI PRZED TESTEM ===")
for k, v in PRZED.items():
    print("  %-28s %s" % (pathlib.Path(k).name, v))

kopie = {}
for p in PILNOWANE:
    if pathlib.Path(p).exists():
        kopie[str(p)] = pathlib.Path(tempfile.mkdtemp()) / pathlib.Path(p).name
        shutil.copy2(p, kopie[str(p)])

katalog = pathlib.Path(tempfile.mkdtemp())
kopia_bazy = katalog / "kopia.db"
shutil.copy2(config.DB_PATH, kopia_bazy)
oryg_connect = db.connect
oryg_dziennik = browser.DZIENNIK
oryg_okno = config.OKNO_PUBLIKACJI_ET
oryg_odstepy = dict(config.ODSTEPY)
browser.DZIENNIK = katalog / "dziennik-testowy.jsonl"
db.connect = lambda path=None: oryg_connect(kopia_bazy)
sys.argv = ["run.py", "--dzien"]        # BEZ --wyslij

# Test o 03:30 czasu czytelnikow trafil poza okno publikacji i ominal cala
# sciezke notek i komentarzy — czyli dokladnie to, co sprawdzamy. Otwieramy
# okno na czas testu, zeby przebieg poszedl ta sama droga co o 11:26 UTC.
config.OKNO_PUBLIKACJI_ET = (0, 24)

# ODSTEPY SKROCONE DO SEKUND. Bez tego test byl NIEUZYWALNY: notki maja
# rozstep 45-90 minut, wiec pelny dzien chodzil godzinami i palil pieniadze
# na API, a ja musialem go ubijac. Przez to pelny przebieg dnia — jedyna
# rzecz, ktorej testy jednostkowe nie dotykaja — nie byl pokryty NICZYM.
#
# CZEGO TEN TEST PRZEZ TO NIE SPRAWDZA, i trzeba to powiedziec wprost:
# `zmiesci_sie` liczy budzet czasu wlasnie z ODSTEPY, wiec przy dwoch
# sekundach wszystko sie miesci i przycinanie nigdy nie zagryzie. Nie da sie
# tego uratowac skalowaniem, bo wywolania modeli trwaja tyle, ile trwaja,
# i nie skrocza sie razem z przerwami.
#
# To jest swiadomy podzial pracy: przycinanie do zegara ma wlasny test
# (`test_czas`, 17 asercji na samej funkcji), a TEN test odpowiada na inne
# pytanie — czy caly dzien przechodzi od poczatku do konca, czy rozdzielnik
# wola wlasciwe etapy i czy produkcja zostaje nietknieta.
config.ODSTEPY = {k: (1, 3) for k in oryg_odstepy}
print()
print("  okno publikacji na czas testu: %s (normalnie %s)"
      % (config.OKNO_PUBLIKACJI_ET, oryg_okno))
print("  odstepy skrocone do 1-3 s (normalnie notka %s s)"
      % (oryg_odstepy.get("notka"),))

print()
print("=== PRAWDZIWY PRZEBIEG DNIA, BEZ PUBLIKOWANIA ===")
kod = None
try:
    kod = run.main()
    blad = None
except BaseException as exc:
    blad = "%s: %s" % (type(exc).__name__, exc)
finally:
    db.connect = oryg_connect
    browser.DZIENNIK = oryg_dziennik
    config.OKNO_PUBLIKACJI_ET = oryg_okno
    config.ODSTEPY = oryg_odstepy

print()
print("=== WYNIK PRZEBIEGU ===")
print("  kod wyjscia:", kod)
print("  wyjatek:    ", blad or "brak")

sprawdzarka = oryg_connect(kopia_bazy)
wiersze = list(sprawdzarka.execute(
    "SELECT id, status, stage, note FROM runs ORDER BY id DESC LIMIT 1"))
print("  ostatni przebieg w kopii bazy:", wiersze[0] if wiersze else "brak")

print()
print("=== CZY PRODUKCJA NIETKNIETA ===")
zle = 0
for p in PILNOWANE:
    teraz = odcisk(p)
    ok = teraz == PRZED[str(p)]
    zle += 0 if ok else 1
    print("  %-28s %s" % (pathlib.Path(p).name, "bez zmian" if ok
                          else "ZMIENIONA (%s -> %s)" % (PRZED[str(p)], teraz)))

for zrodlo, kopia in kopie.items():
    if odcisk(zrodlo) != PRZED[zrodlo]:
        shutil.copy2(kopia, zrodlo)
        print("  przywrocono z kopii:", pathlib.Path(zrodlo).name)

print()
udane = blad is None and zle == 0 and wiersze and wiersze[0][1] == "DONE"
print("=== %s ===" % ("PRZEBIEG PRZESZEDL, PRODUKCJA NIETKNIETA" if udane
                      else "COS NIE GRA — patrz wyzej"))
sys.exit(0 if udane else 1)
