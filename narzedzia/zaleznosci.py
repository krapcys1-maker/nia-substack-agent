# -*- coding: utf-8 -*-
"""Prawdziwa lista zaleznosci — z DRZEWA SKLADNI importow, nie z pamieci.

Po co osobne narzedzie na cos tak prostego: `requirements.txt` w tym
repozytorium nie istnial wcale, a pierwsza wersja, ktora napisalem z pamieci,
wymieniala `openai` i `requests`. Ani jeden, ani drugi nie jest importowany
w agent-v2 — okladka artykulu idzie przez `httpx` prosto na endpoint OpenAI,
bez SDK. Lista spisana z pamieci klamie, i to jest dokladnie ta klasa bledu,
przed ktora ten projekt ostrzega w kazdym innym miejscu.

Rozdziela PROD od TESTOW, bo to rozroznienie ma tu znaczenie pieniezne:
`pytest` jest importowany wylacznie w `agent-v2/tests/`, a atrapy w
`conftest.py` sa jedyna rzecza, ktora oddziela darmowy test od zaplaconego
wywolania modelu.

Uruchomienie:
    python narzedzia/zaleznosci.py            # tabela
    python narzedzia/zaleznosci.py --sprawdz  # czy requirements.txt sie zgadza
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys

KORZEN = pathlib.Path(__file__).resolve().parent.parent
KOD = KORZEN / "agent-v2"

# Nazwa importu nie zawsze rowna sie nazwie pakietu na PyPI.
NA_PYPI = {
    "dotenv": "python-dotenv",
}


# MODULY, KTORE SA W BIBLIOTECE STANDARDOWEJ DOPIERO OD NOWSZEGO PYTHONA.
#
# `sys.stdlib_module_names` opisuje INTERPRETER, KTORY WLASNIE CHODZI. Na 3.12
# `tomllib` jest w nim i wszystko sie zgadza; na 3.10 go nie ma, wiec narzedzie
# uznalo go za pakiet z PyPI i zazadalo wpisania do `requirements.txt` — a on
# nie istnieje na PyPI pod ta nazwa.
#
# ZLAPALO TO DOPIERO CI, w macierzy 3.10/3.12. Lokalnie chodze na 3.12 i przez
# to nie mialem szansy tego zobaczyc — dokladnie ten rodzaj wady, do ktorego
# macierz wersji sluzy.
#
# `konfiguracja.py` importuje `tomllib` WARUNKOWO i sam sprawdza wersje, wiec
# na 3.10 bot dziala; nie dziala tylko `konfiguracja.toml`, i mowi o tym wprost.
STDLIB_OD_NOWSZEGO = {
    "tomllib": "3.11",
}


def zbierz() -> dict[str, dict[str, set[str]]]:
    # WLASNE MODULY TO TAKZE POMOCNIKI W `tests/`. Pierwsza wersja brala pod
    # uwage tylko `agent-v2/*.py`, wiec `tests/historia.py` — lokalny modul,
    # ktory testy importuja po nazwie — zostal zgloszony jako BRAKUJACY PAKIET
    # z PyPI. Narzedzie majace pilnowac listy zaleznosci samo dopisalo do niej
    # rzecz, ktorej nie da sie zainstalowac.
    wlasne = {p.stem for p in KOD.rglob("*.py")}
    std = set(sys.stdlib_module_names)
    zew: dict[str, dict[str, set[str]]] = {}
    for p in sorted(KOD.rglob("*.py")):
        czy_test = "tests" in p.parts
        drzewo = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        for n in ast.walk(drzewo):
            if isinstance(n, ast.Import):
                mods = [a.name.split(".")[0] for a in n.names]
            elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
                mods = [n.module.split(".")[0]]
            else:
                continue
            for m in mods:
                if (m in std or m in wlasne or m.startswith("_")
                        or m in STDLIB_OD_NOWSZEGO):
                    continue
                wpis = zew.setdefault(m, {"prod": set(), "test": set()})
                wpis["test" if czy_test else "prod"].add(
                    str(p.relative_to(KORZEN)).replace("\\", "/"))
    return zew


def z_requirements(nazwa: str) -> set[str]:
    plik = KORZEN / nazwa
    if not plik.exists():
        return set()
    out = set()
    for linia in plik.read_text(encoding="utf-8").splitlines():
        linia = linia.split("#")[0].strip()
        if not linia or linia.startswith("-"):
            continue
        out.add(re.split(r"[<>=!\[]", linia)[0].strip().lower())
    return out


def main() -> int:
    zew = zbierz()
    prod = {NA_PYPI.get(m, m) for m, d in zew.items() if d["prod"]}
    tylko_test = {NA_PYPI.get(m, m) for m, d in zew.items() if not d["prod"]}

    print("%-16s %-11s %s" % ("pakiet", "gdzie", "przykladowy importujacy"))
    print("-" * 78)
    for m in sorted(zew):
        d = zew[m]
        gdzie = "PROD" if d["prod"] else "tylko test"
        print("%-16s %-11s %s" % (NA_PYPI.get(m, m), gdzie,
                                  sorted(d["prod"] or d["test"])[0]))
    print()
    print("produkcyjne: %s" % ", ".join(sorted(prod)))
    print("do testow:   %s" % (", ".join(sorted(tylko_test)) or "—"))

    if "--sprawdz" not in sys.argv:
        return 0

    print()
    zle = 0
    zadeklarowane = z_requirements("requirements.txt")
    brak = {p.lower() for p in prod} - zadeklarowane
    nadmiar = zadeklarowane - {p.lower() for p in prod}
    for nazwa, zbior in (("BRAK w requirements.txt", brak),
                         ("NADMIAR w requirements.txt (nic tego nie importuje)",
                          nadmiar)):
        if zbior:
            print("  BLAD  %s: %s" % (nazwa, ", ".join(sorted(zbior))))
            zle += 1
    dev = z_requirements("requirements-dev.txt")
    brak_dev = {p.lower() for p in tylko_test} - dev
    if brak_dev:
        print("  BLAD  BRAK w requirements-dev.txt: %s" % ", ".join(sorted(brak_dev)))
        zle += 1
    print("  OK    requirements.txt zgadza sie z importami" if not zle
          else "  %d niezgodnosci" % zle)
    return 1 if zle else 0


if __name__ == "__main__":
    sys.exit(main())
