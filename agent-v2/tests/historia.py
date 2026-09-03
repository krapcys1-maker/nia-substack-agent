# -*- coding: utf-8 -*-
"""Dostep do wersji odniesienia z historii repozytorium — z jawnym pominieciem.

## Po co to istnieje

Dziewietnascie testow w tym katalogu odtwarza KONTRDOWOD: biora plik sprzed
naprawy prosto z historii gita i sprawdzaja, ze na tamtej wersji test naprawde
pada. Regula stoi w `DOKTRYNA.md` paragraf 12 i jest kupiona drogo:

  > Kontrdowod musi byc odtworzony, nie opisany, a wersja odniesienia przypieta
  > do konkretnego SHA — NIGDY do `HEAD`. Test mierzacy sie wzgledem `HEAD`
  > gasnie w chwili commita, ktorego strzeze.

Skutek uboczny tej reguly: **te testy zaleza od historii TEGO repozytorium**.
W kopii zalozonej od nowa — a taka jest kazde wydanie publiczne, w ktorym
historia zostala odcieta — `git show <SHA>` trafia w commit, ktorego nie ma.

Do 2026-09-03 konczylo sie to `CalledProcessError` albo `AttributeError`
w polowie pliku, czyli awaria, ktora wyglada jak wada kodu i nie mowi
czytajacemu nic o przyczynie. To jest ten sam rodzaj cichej pulapki, przed
ktorym ostrzega caly ten projekt — tylko odwrocony: nie test zielony nad
martwym kodem, a test czerwony nad kodem zdrowym.

## Co ten modul robi

`wymaga_historii(*sha)` sprawdza, czy podane commity sa osiagalne. Gdy nie sa,
wypisuje CO i DLACZEGO zostalo pominiete i konczy proces kodem 0 — pominiecie
jest jawne i policzalne, a nie udawane przejscie.

Nie jest to obejscie reguly. Reguła obowiazuje tam, gdzie historia istnieje;
tam, gdzie jej nie ma, kontrdowodu po prostu NIE DA SIE odtworzyc i lepiej
powiedziec to wprost niz wywalic sie na pol drogi.
"""
from __future__ import annotations

import subprocess
import sys


def commit_istnieje(sha: str) -> bool:
    """Czy ten commit jest osiagalny w bierzacym repozytorium."""
    try:
        wynik = subprocess.run(
            ["git", "cat-file", "-e", "%s^{commit}" % sha],
            capture_output=True,
        )
    except (OSError, subprocess.SubprocessError):
        return False          # brak gita to tez brak historii
    return wynik.returncode == 0


def wymaga_historii(*sha: str) -> None:
    """Konczy przebieg z kodem 0 i jawnym powodem, gdy brakuje ktoregos SHA.

    Wolane na gorze testu, PRZED pierwsza asercja — zeby pominiecie bylo
    widoczne w calosci, a nie po polowie zdanych sprawdzen.
    """
    brakuje = [s for s in sha if not commit_istnieje(s)]
    if not brakuje:
        return
    print("=== POMINIETE: brak wersji odniesienia w historii ===")
    print("    szukane commity: %s" % ", ".join(brakuje))
    print("    Ten test odtwarza kontrdowod z historii tego repozytorium")
    print("    (DOKTRYNA.md paragraf 12). W kopii z historia zalozona od nowa")
    print("    tych commitow nie ma, wiec kontrdowodu NIE DA SIE odtworzyc.")
    print("    To nie jest wada kodu i nie jest przejscie testu — to brak")
    print("    materialu do pomiaru.")
    print()
    print("    Zeby go uruchomic, potrzebujesz repozytorium z pelna historia.")
    sys.exit(0)
