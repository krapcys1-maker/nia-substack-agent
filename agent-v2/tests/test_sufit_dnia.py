# -*- coding: utf-8 -*-
"""Sufit dzienny: jedna baza, jeden mnoznik, podwyzka naliczona RAZ.

## Po co ten plik istnieje

Sufit podniesiony na jeden dzien pracy przy wlascicielu byl liczony DWA RAZY:

    DAILY_LIMIT_USD = SUFIT_DZIENNY_BAZOWY * 2.0   (w dniu podniesienia)
    sufit_dnia(dzis) = DAILY_LIMIT_USD * SUFIT_PODNIESIONY_RAZY

czyli w dniu podniesienia sufit wychodzil CZTERY razy wiekszy od bazowego —
i to akurat tego dnia, w ktorym pieniedzy pilnuje sie najuwazniej.

Wada powstala z POPRAWKI. `sufit_dnia()` mialo wpisane `return 10.00 if ...
else 5.00` — dwie kwoty obok pola konfiguracji, ktore mowi to samo. Poprawka
zdjela wpisane kwoty i siegnela po `DAILY_LIMIT_USD` — nie zauwazywszy, ze on
JEST JUZ po podniesieniu.

Nie oblal tego zaden test, bo `SUFIT_PODNIESIONY_NA` trzymalo date PRZESZLA
(„2026-08-30"), wiec galaz podwyzki nie wykonala sie ani razu — ani na
produkcji, ani w zadnym przebiegu testow. To ten sam ksztalt, co „617 asercji,
ktore nie wykonuja sie ani razu": kod wyglada na dzialajacy, bo nikt nie
sprawdzil, czy w ogole jest wywolywany.

## Czego pilnuje

1. ZWYKLY DZIEN = BAZA. Bez tego pusty `SUFIT_PODNIESIONY_NA` moglby
   przypadkiem trafic w dzien („" == ""[:10] jest prawdziwe dla pustego
   argumentu) i podniesc sufit kazdemu, kto zapyta o pusta date.
2. DZIEN PODNIESIENIA = BAZA RAZY MNOZNIK, DOKLADNIE RAZ.
3. INNY DZIEN NIZ PODNIESIENIE = BAZA, takze gdy pytamy o wczoraj.
4. `DAILY_LIMIT_USD` JEST POCHODNA, nie drugim zrodlem: rowna sie
   `sufit_dnia(dzis)`.
5. SUFIT BAZOWY IDZIE Z KONFIGURACJI — konto z innym sufitem dostaje inne
   liczby we wszystkich czterech punktach wyzej.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_sufit_dnia.py
"""
import sys

sys.path.insert(0, "agent-v2")
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


DZIS = config._dzis_utc()
_stan = (config.SUFIT_DZIENNY_BAZOWY, config.SUFIT_PODNIESIONY_NA,
         config.DAILY_LIMIT_USD)


def ustaw(baza, podniesiony_na):
    config.SUFIT_DZIENNY_BAZOWY = baza
    config.SUFIT_PODNIESIONY_NA = podniesiony_na
    config.DAILY_LIMIT_USD = config.sufit_dnia(DZIS)


try:
    print("=== 1. BEZ PODNIESIENIA KAZDY DZIEN MA SUFIT BAZOWY ===")
    ustaw(5.00, "")
    for dzien in (DZIS, "2020-01-01", "2099-12-31", ""):
        sprawdz("sufit_dnia(%r) == baza" % dzien,
                config.sufit_dnia(dzien) == 5.00, config.sufit_dnia(dzien))
    sprawdz("DAILY_LIMIT_USD tez", config.DAILY_LIMIT_USD == 5.00,
            config.DAILY_LIMIT_USD)

    print()
    print("=== 2. W DNIU PODNIESIENIA — RAZ, NIE DWA RAZY ===")
    ustaw(5.00, DZIS)
    oczekiwany = 5.00 * config.SUFIT_PODNIESIONY_RAZY
    sprawdz("sufit_dnia(dzis) == baza * mnoznik",
            config.sufit_dnia(DZIS) == oczekiwany,
            "%s, oczekiwano %s" % (config.sufit_dnia(DZIS), oczekiwany))
    # KONTRDOWOD NA SAMA WADE: podwojne naliczenie dawalo tu czterokrotnosc.
    sprawdz("i NIE jest to czterokrotnosc bazy",
            config.sufit_dnia(DZIS) != 5.00 * config.SUFIT_PODNIESIONY_RAZY ** 2,
            config.sufit_dnia(DZIS))
    sprawdz("DAILY_LIMIT_USD rowna sie sufit_dnia(dzis)",
            config.DAILY_LIMIT_USD == config.sufit_dnia(DZIS),
            (config.DAILY_LIMIT_USD, config.sufit_dnia(DZIS)))

    print()
    print("=== 3. INNY DZIEN NIZ PODNIESIENIE WRACA DO BAZY ===")
    # To jest powod istnienia `sufit_dnia`: alarm patrzy na WCZORAJ.
    for dzien in ("2020-01-01", "2099-12-31"):
        sprawdz("sufit_dnia(%s) == baza" % dzien,
                config.sufit_dnia(dzien) == 5.00, config.sufit_dnia(dzien))
    sprawdz("pusta data nie trafia w dzien podniesienia",
            config.sufit_dnia("") == 5.00, config.sufit_dnia(""))

    print()
    print("=== 4. INNY SUFIT BAZOWY — WSZYSTKIE LICZBY IDA ZA NIM ===")
    # Wpisana kwota rozjechalaby sie tutaj: konto z sufitem 3 USD dostawaloby
    # alarm dopiero po piatym, a konto z sufitem 20 — codziennie o niczym.
    ustaw(3.00, "")
    sprawdz("zwykly dzien przy bazie 3", config.sufit_dnia(DZIS) == 3.00,
            config.sufit_dnia(DZIS))
    ustaw(3.00, DZIS)
    sprawdz("dzien podniesienia przy bazie 3",
            config.sufit_dnia(DZIS) == 3.00 * config.SUFIT_PODNIESIONY_RAZY,
            config.sufit_dnia(DZIS))
    sprawdz("i wczoraj nadal 3", config.sufit_dnia("2020-01-01") == 3.00,
            config.sufit_dnia("2020-01-01"))

    print()
    print("=== 5. ZADNA KWOTA NIE JEST WPISANA W `sufit_dnia` ===")
    # Szukamy po ZRODLE, bo to jedyny sposob odroznic „liczy z pola" od
    # „przypadkiem daje te sama liczbe, co pole".
    # BEZ DOKUMENTACJI. Docstring tej funkcji CYTUJE stare, wpisane kwoty
    # („stalo tu `return 10.00 if ... else 5.00`") — i ma je cytowac, bo to
    # jest opis wady. Liczymy wiec po DRZEWIE SKLADNI ciala, nie po tekscie.
    import ast as _ast
    import inspect
    import textwrap
    zrodlo = inspect.getsource(config.sufit_dnia)
    drzewo = _ast.parse(textwrap.dedent(zrodlo)).body[0]
    cialo = [w for w in drzewo.body
             if not (isinstance(w, _ast.Expr)
                     and isinstance(w.value, _ast.Constant)
                     and isinstance(w.value.value, str))]
    liczby = [w.value for g in cialo for w in _ast.walk(g)
              if isinstance(w, _ast.Constant) and isinstance(w.value, (int, float))
              and not isinstance(w.value, bool)]
    # `[:10]` jest krojeniem napisu, nie kwota — jedyna dopuszczona liczba.
    kwoty = [x for x in liczby if x != 10]
    sprawdz("w ciele funkcji nie ma zadnej kwoty", not kwoty, kwoty)
    nazwy = {w.id for g in cialo for w in _ast.walk(g) if isinstance(w, _ast.Name)}
    sprawdz("i czyta sufit bazowy", "SUFIT_DZIENNY_BAZOWY" in nazwy, sorted(nazwy))
    sprawdz("a NIE pochodna na dzis", "DAILY_LIMIT_USD" not in nazwy,
            sorted(nazwy))
finally:
    (config.SUFIT_DZIENNY_BAZOWY, config.SUFIT_PODNIESIONY_NA,
     config.DAILY_LIMIT_USD) = _stan

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
