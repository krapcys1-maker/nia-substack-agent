# -*- coding: utf-8 -*-
"""Darmowy test nie ma prawa wydac pieniedzy — i nie moze na to liczyc.

CO BYLO ZLE. `tests/conftest.py` chroni przed platnymi testami TYLKO POD
PYTESTEM. A darmowe testy tego repozytorium chodza petla po plikach, tak jak
mowi `tests/URUCHOM.md`:

    for t in agent-v2/tests/test_*.py; do python "$t"; done

W tej petli conftest NIE WYKONUJE SIE WCALE. Test, ktory zapomni podstawic
atrape pod `llm.call`, siega wiec po prawdziwy klucz z `.env` i placi. Na
serwerze, gdzie klucze sa prawdziwe, jedynym sladem jest wiersz w tabeli
`calls`, ktorego nikt nie oglada — czyli awaria wygladajaca jak spokojny dzien.

To ta sama klasa bledu, ktora opisuje sam conftest: „ostrzezenie w dokumencie
nie jest bramka". Conftest byl bramka dla pytesta i dokumentem dla petli.

GDZIE STOI ZAPORA. W `llm._preflight`, czyli tam, gdzie juz mieszkaja wszystkie
warunki sprawdzane ZANIM pojda pieniadze. Nie w atrapach: atrapa, ktorej ktos
zapomnial podstawic, nie moze byc tym, co pilnuje, czy ktos ja podstawil.

PO CZYM POZNAJE. Po SCIEZCE uruchomionego programu, nie po zmiennej
srodowiskowej — zmienna trzeba pamietac, a sciezka jest faktem.

BEZ PYTESTA, zero sieci, zero platnych wywolan, produkcja nietknieta.
Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_zapora_platnych_wywolan.py
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import config      # noqa: E402
import db          # noqa: E402
import llm         # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# PRAWDZIWA BAZA W KATALOGU TYMCZASOWYM, nie `:memory:` bez schematu: sufit
# budzetu pyta tabele `calls`, wiec goła baza wywala sie na `OperationalError`
# ZANIM dojdzie do czegokolwiek, co ten test mierzy.
_KATALOG = tempfile.mkdtemp(prefix="zapora-test-")
CONN = db.connect(pathlib.Path(_KATALOG) / "t.db")

# `DRY_RUN` USTAWIAMY, NIE ZAKLADAMY. Pierwsza wersja tego pliku brala go z
# `.env` i przechodzila obok wlasnego przedmiotu: na maszynie wlasciciela
# `DRY_RUN=true`, wiec zapora byla POMIJANA i test mierzyl cos zupelnie innego
# niz na serwerze, gdzie jest wylaczony. Test zalezny od srodowiska klamie tym
# ciszej, im rzadziej ktos porownuje obie maszyny.
config.DRY_RUN = False

print("=== 1. TEN PLIK JEST DARMOWYM TESTEM I WIE O TYM ===")
# Najmocniejsza asercja w pliku: nie opisuje reguly, tylko WLASNE polozenie.
sprawdz("`WOLNO_WOLAC_MODEL` jest wylaczone dla tego procesu",
        config.WOLNO_WOLAC_MODEL is False,
        "argv[0]=%r" % sys.argv[0])

print()
print("=== 2. PROBA WYWOLANIA MODELU KONCZY SIE JAWNYM BLEDEM ===")
# Nie cichym pominieciem i nie pusta odpowiedzia — takie „zero z wyjasnieniem"
# jest w tym repozytorium osobna klasa dlugu.
try:
    llm.call("note", "s", "u", conn=CONN, run_id=None)
    sprawdz("wywolanie przerwane", False, "przeszlo bez bledu")
except llm.PreflightFailed as exc:
    sprawdz("wywolanie przerwane", True)
    sprawdz("blad mowi, CO zrobic", "atrape" in str(exc) and "platne" in str(exc),
            str(exc))
except Exception as exc:                              # noqa: BLE001
    sprawdz("wywolanie przerwane", False, "inny wyjatek: %s" % type(exc).__name__)

print()
print("=== 3. `DRY_RUN` PRZECHODZI, BO TAM NIE MA CZEGO BLOKOWAC ===")
# `call` konczy sie na DRY_RUN pustym napisem, ZANIM dotknie sieci. Testy
# uzywaja tej sciezki, zeby zmierzyc, co `call` WYPISUJE — bez niej ostrzezen
# o martwych ustawieniach nie dalo by sie sprawdzic inaczej niz szukaniem
# napisu w zrodle.
config.DRY_RUN = True
try:
    wynik = llm.call("note", "s", "u", conn=CONN, run_id=None)
    sprawdz("DRY_RUN nie jest blokowany", wynik == "", repr(wynik))
except Exception as exc:                              # noqa: BLE001
    sprawdz("DRY_RUN nie jest blokowany", False,
            "%s: %s" % (type(exc).__name__, exc))
finally:
    config.DRY_RUN = False

print()
print("=== 4. TESTY PLATNE MAJA PLACIC I PRZECHODZA ===")
korzen = pathlib.Path(config.AGENT_DIR)
for opis, sciezka, oczekiwane in (
    ("darmowy test", korzen / "tests" / "test_cos.py", True),
    ("test platny", korzen / "tests" / "platne" / "test_integracja.py", False),
    ("zwykly przebieg agenta", korzen / "run.py", False),
    ("skrypt audytowy", korzen / "audyt_systemu.py", False),
):
    stary_argv = sys.argv[0]
    sys.argv[0] = str(sciezka)
    try:
        wykryte = config._w_darmowym_tescie()
    finally:
        sys.argv[0] = stary_argv
    sprawdz("%-24s -> blokowany: %s" % (opis, oczekiwane),
            wykryte is oczekiwane, "wykryte=%s" % wykryte)

print()
print("=== 5. KONTRDOWOD: BEZ ZAPORY WYWOLANIE SZLOBY DALEJ ===")
# Gdyby zapora byla ozdobna, ten sam kod z podniesiona flaga tez by sie
# zatrzymal — i test przechodzilby, nie mierzac niczego.
#
# WOLAMY `_preflight`, NIE `call`, I TO JEST CALA POINTA TEGO KOMENTARZA.
# Pierwsza wersja podnosila flage i wolala `llm.call` — czyli KONTRDOWOD
# ZAPLACIL: 0,0043 USD za wywolanie Opusa, w darmowym tescie, dokladnie tym,
# czemu ta zapora ma zapobiegac. Test pilnujacy, zeby nikt nie placil, sam
# zaplacil przy pierwszym uruchomieniu.
#
# `_preflight` sprawdza wszystkie warunki i NIE DOTYKA SIECI, wiec mierzy
# dokladnie to, o co pytamy: czy zatrzymuje nas nasza zapora, czy juz co innego.
config.WOLNO_WOLAC_MODEL = True
try:
    llm._preflight("note", CONN, None)
    dalej = "przeszlo"
except llm.PreflightFailed as exc:
    dalej = str(exc)
except Exception as exc:                              # noqa: BLE001
    dalej = "%s: %s" % (type(exc).__name__, exc)
finally:
    config.WOLNO_WOLAC_MODEL = False
sprawdz("z podniesiona flaga zatrzymuje nas juz CO INNEGO",
        "darmowego testu" not in dalej, dalej[:120])

print()
print("=" * 62)
print("ZDANE: %d    OBLANE: %d" % (zdane, oblane))
sys.exit(1 if oblane else 0)
