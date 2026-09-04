# -*- coding: utf-8 -*-
"""Straznik dla testow, ktore opisuja DOSTARCZONA konfiguracje, nie kod.

## Problem, ktory to rozwiazuje

Czesc testow w tym zestawie nie sprawdza, czy kod dziala. Sprawdza, czy
DECYZJA zapisana w `config.py` nadal tam stoi: ze lajkow jest 10-16, ze okno
publikacji to 6-22, ze obserwacji jest mniej niz subskrypcji. Kazdy taki test
ma w komentarzu, dlaczego wlasnie tyle — i to jest cenne, bo inaczej liczby
przesuwaja sie po cichu.

Ale te testy oblewaja, gdy ktos ustawi WLASNE wartosci w `konfiguracja.toml`.
Zmierzone: konto przestawione kreatorem na inny temat, inny jezyk i wlasze
wolumeny daje 19 czerwonych testow, z ktorych ANI JEDEN nie mowi o awarii.
Operator, ktory pierwszy raz uruchamia zestaw po konfiguracji, nie ma jak
odroznic „zepsulem instalacje" od „zmienilem liczbe i test o niej pamieta".

Czerwony zestaw, ktory nic nie znaczy, jest gorszy od braku zestawu: uczy,
zeby na niego nie patrzec.

## Co ten modul robi

`pomin_gdy_wlasna(powod)` konczy test czysto (kod 0) z wyjasnieniem, gdy
`agent-v2/konfiguracja.toml` istnieje. Bez tego pliku — czyli u nas i w CI —
test biegnie normalnie i pilnuje dostarczonych wartosci tak jak dotad.

## Czego to NIE usprawiedliwia

To NIE jest sposob na uciszenie testu, ktory oblewa. Wolno go uzyc wylacznie
tam, gdzie asercja dotyczy WARTOSCI podanej przez uzytkownika. Test sprawdzajacy
zachowanie kodu przy dowolnej wartosci ma dzialac zawsze — i wiekszosc takich
testow poprawiono tak, zeby czytaly `config`, zamiast miec liczbe wpisana
w ciele.
"""
from __future__ import annotations

import pathlib
import sys

PLIK = pathlib.Path("agent-v2/konfiguracja.toml")


def wlasna() -> bool:
    return PLIK.exists()


def tylko_nasze(sprawdz):
    """Owija `sprawdz` w wersje pomijana przy wlasnej konfiguracji.

    Uzycie w tescie:

        sprawdz_nasze = wlasna_konfiguracja.tylko_nasze(sprawdz)
        sprawdz_nasze("lajki 10-16", config.LAJKI_DZIENNIE == (10, 16))

    POMINIETA ASERCJA JEST WIDOCZNA, nie cicha: wypisuje sie z myslnikiem
    zamiast OK, wiec w wyniku widac, ile twierdzen o dostarczonych wartosciach
    nie zostalo sprawdzonych. Cicho przechodzaca asercja bylaby gorsza od
    oblanej — udawalaby dowod.
    """
    def sprawdz_nasze(nazwa, warunek=None, szczegol=""):
        if wlasna():
            print("  -     %s   (wlasna konfiguracja, nie sprawdzam)" % nazwa)
            return
        sprawdz(nazwa, warunek, szczegol)
    return sprawdz_nasze


def pomin_gdy_wlasna(powod: str) -> None:
    """Konczy przebieg kodem 0, gdy operator ma wlasna konfiguracje."""
    if not wlasna():
        return
    print("  POMINIETY: %s" % powod)
    print("  Powod: istnieje %s, wiec wartosci w `config.py` sa juz tylko"
          % PLIK)
    print("  wartosciami DOMYSLNYMI, a nie tym, czym bot naprawde jedzie.")
    print("  Ten test opisuje decyzje o dostarczonych liczbach; twoje wlasne")
    print("  liczby sa twoja decyzja i nie ma ich z czym porownac.")
    print()
    print("=== POMINIETY (wlasna konfiguracja) ===")
    sys.exit(0)


def pomin_gdy_bez_tomllib(co_bada: str) -> None:
    """Konczy przebieg kodem 0 na Pythonie starszym niz 3.11.

    `tomllib` wszedl do biblioteki standardowej w 3.11, a 3.10 jest nadal
    wspieranym minimum dla samego bota — `konfiguracja.toml` jest dodatkiem,
    nie warunkiem dzialania. Test badajacy ten plik nie ma wiec na 3.10 czego
    badac i MA to powiedziec, zamiast konczyc sie sladem stosu.

    Czerwone CI przy poprawnym kodzie uczy ignorowania CI — dokladnie tak samo
    jak audyt oblewajacy na poprawnej instalacji.
    """
    if sys.version_info >= (3, 11):
        return
    print("  POMINIETY: %s" % co_bada)
    print("  Powod: `tomllib` jest od Pythona 3.11, a tu chodzi %d.%d."
          % (sys.version_info[0], sys.version_info[1]))
    print("  To NIE jest wada kodu: 3.10 to wspierane minimum dla bota,")
    print("  a `konfiguracja.toml` jest dodatkiem wymagajacym 3.11.")
    print()
    print("=== POMINIETY (brak tomllib) ===")
    sys.exit(0)
