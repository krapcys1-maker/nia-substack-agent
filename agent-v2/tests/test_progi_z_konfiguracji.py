# -*- coding: utf-8 -*-
"""Prog alarmu ma isc za konfiguracja, a nie za pamiecia tego, kto go wpisal.

## Po co ten plik istnieje

Ten sam ksztalt wady zebral w tym repozytorium juz trzy przypadki:

    alarm.MAX_DZIALAN_DZIENNIE = 60      # „suma norm to ~39,5, wiec 1,52x"
    audyt_systemu:  DAILY_LIMIT_USD <= 5.0
    config.sufit_dnia():  return 10.00 if ... else 5.00

Za kazdym razem liczba jest POCHODNA pola konfiguracji, policzona raz, przez
czlowieka, dla jednego konta. Komentarz przy pierwszej z nich sam podawal
rachunek — czyli autor WIEDZIAL, ze to pochodna, i mimo to zapisal wynik
zamiast dzialania.

Skutek jest niesymetryczny i cichy w obie strony:

  * konto z WIEKSZA norma dostaje alarm o zapetleniu kazdego dobrego dnia
    — a alarm, ktory wyje bez powodu, przestaje byc czytany;
  * konto z MNIEJSZA norma nie dostaje go nigdy, bo przy normie 12 dzialan
    trzeba by pieciokrotnosci planu, zeby przekroczyc 60.

Druga jest grozniejsza, bo wyglada dokladnie tak samo jak spokoj.

## Czego pilnuje

1. SUFIT IDZIE ZA NORMAMI. Podnosimy widelki i zadamy, zeby sufit wzrosl.
2. PODLOGA DZIALA. Konto o smiesznie malej normie nie dostaje sufitu 9.
3. PROPORCJA JEST ZACHOWANA — sufit jest wielokrotnoscia planu, a nie liczba
   przypadkowo wieksza.
4. W CIELE FUNKCJI NIE MA WPISANEJ LICZBY DZIALAN (sprawdzane po AST, bo
   docstring cytuje stare wartosci i ma je cytowac).
5. PROG AUDYTU SUFITU DZIENNEGO tez jest porownaniem dwoch pol, a nie liczby.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_progi_z_konfiguracji.py
"""
import ast
import inspect
import sys
import textwrap

sys.path.insert(0, "agent-v2")
import alarm   # noqa: E402
import config  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


def _liczby_w_ciele(fn) -> list:
    """Stale liczbowe w ciele funkcji, z pominieciem docstringa.

    Po AST, a nie po tekscie: docstringi w tym repozytorium CYTUJA stare,
    wpisane wartosci — i maja je cytowac, bo to jest opis wady.
    """
    drzewo = ast.parse(textwrap.dedent(inspect.getsource(fn))).body[0]
    cialo = [w for w in drzewo.body
             if not (isinstance(w, ast.Expr)
                     and isinstance(w.value, ast.Constant)
                     and isinstance(w.value.value, str))]
    return [w.value for g in cialo for w in ast.walk(g)
            if isinstance(w, ast.Constant)
            and isinstance(w.value, (int, float))
            and not isinstance(w.value, bool)]


print("=== 1. SUFIT DZIALAN IDZIE ZA NORMAMI ===")
suma = sum(config.normy_dzienne().values())
sufit = alarm.max_dzialan_dziennie()
sprawdz("sufit jest liczba dodatnia", isinstance(sufit, int) and sufit > 0, sufit)
sprawdz("i jest wiekszy od sumy norm", sufit > suma, (sufit, round(suma, 1)))
sprawdz("i nie jest absurdalnie wiekszy (< 4x planu)", sufit < 4 * suma,
        (sufit, round(suma, 1)))

print()
print("=== 2. INNE NORMY — INNY SUFIT ===")
# Podmieniamy samo `normy_dzienne`, bo droga od widelek do norm biegnie przez
# kilka pol i test o progu nie ma jej odtwarzac.
_prawdziwe = config.normy_dzienne
try:
    config.normy_dzienne = lambda: {"notka": 100.0, "komentarz": 200.0}
    duzy = alarm.max_dzialan_dziennie()
    sprawdz("przy normie 300 sufit rosnie", duzy > sufit, (duzy, sufit))
    sprawdz("i jest okolo poltorakrotnoscia planu",
            abs(duzy - 450) <= 1, duzy)

    config.normy_dzienne = lambda: {"notka": 2.0, "komentarz": 4.0}
    maly = alarm.max_dzialan_dziennie()
    # PODLOGA. Poltorakrotnosc szesciu to dziewiec, a dziewiec dzialan na dobe
    # nie jest zapetleniem w zadnym sensie.
    sprawdz("przy smiesznie malej normie dziala podloga",
            maly == alarm.MIN_SUFIT_DZIALAN, (maly, alarm.MIN_SUFIT_DZIALAN))

    config.normy_dzienne = lambda: {}
    sprawdz("przy braku norm tez podloga, nie zero",
            alarm.max_dzialan_dziennie() == alarm.MIN_SUFIT_DZIALAN,
            alarm.max_dzialan_dziennie())
finally:
    config.normy_dzienne = _prawdziwe

print()
print("=== 3. W CIELE FUNKCJI NIE MA WPISANEJ LICZBY DZIALAN ===")
_liczby = _liczby_w_ciele(alarm.max_dzialan_dziennie)
sprawdz("zadnej stalej liczbowej w ciele", not _liczby, _liczby)
_nazwy = {w.id for w in ast.walk(
    ast.parse(textwrap.dedent(inspect.getsource(alarm.max_dzialan_dziennie))))
    if isinstance(w, ast.Name)}
sprawdz("czyta mnoznik z modulu", "MNOZNIK_SUFITU_DZIALAN" in _nazwy, sorted(_nazwy))
sprawdz("i podloge z modulu", "MIN_SUFIT_DZIALAN" in _nazwy, sorted(_nazwy))

print()
print("=== 4. PROG AUDYTU SUFITU DZIENNEGO TO POROWNANIE DWOCH POL ===")
# Stalo tam `config.DAILY_LIMIT_USD <= 5.0` — czyli domyslny sufit bazowy
# wpisany drugi raz. Konto z sufitem 8 USD mialo UWAGA kazdego dnia swojego
# zycia, konto z sufitem 3 — nigdy, nawet w dniu podniesienia.
import pathlib  # noqa: E402
_zrodlo = pathlib.Path("agent-v2/audyt_systemu.py").read_text(encoding="utf-8")
sprawdz("audyt porownuje z SUFIT_DZIENNY_BAZOWY",
        "config.DAILY_LIMIT_USD <= config.SUFIT_DZIENNY_BAZOWY" in _zrodlo)
sprawdz("i nie ma tam wpisanej kwoty 5.0",
        "config.DAILY_LIMIT_USD <= 5.0" not in _zrodlo)

print()
print("=== 5. KONTRDOWOD: TEST ROZROZNIA POCHODNA OD STALEJ ===")
# Bez tego sekcja 2 przechodzilaby takze wtedy, gdyby `max_dzialan_dziennie`
# zawsze oddawalo te sama liczbe — pokazujemy, ze DWIE rozne normy daja DWIE
# rozne odpowiedzi, a nie jedna.
_a = _b = None
try:
    config.normy_dzienne = lambda: {"x": 40.0}
    _a = alarm.max_dzialan_dziennie()
    config.normy_dzienne = lambda: {"x": 80.0}
    _b = alarm.max_dzialan_dziennie()
finally:
    config.normy_dzienne = _prawdziwe
sprawdz("dwie normy, dwa rozne sufity", _a != _b and _b > _a, (_a, _b))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
