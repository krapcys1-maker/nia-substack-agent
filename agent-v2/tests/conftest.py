# -*- coding: utf-8 -*-
"""Zabezpieczenie przed przypadkowym uruchomieniem PLATNYCH testow.

DLACZEGO TO POWSTALO — z mojej wlasnej wpadki, 30 sierpnia. Uruchomilem
`pytest tests/` zeby sprawdzic dwa nowe pliki. `tests/platne/test_integracja.py`
nie ma funkcji testowych: caly przebieg dnia siedzi w CIELE MODULU, wiec sama
zbiorka testow go WYKONALA — z prawdziwymi kluczami z lokalnego `.env`.
Tym razem przebieg padl, zanim cokolwiek zaplacil (ostatnie platne wywolanie w
lokalnej bazie bylo z 25 sierpnia), ale to byl przypadek, nie zabezpieczenie.

Dokumentacja ostrzegala przed dokladnie tym: „ktos, kto puszczy
`pytest agent-v2/tests/` rekurencyjnie, wejdzie w `platne/test_integracja.py`
i zaplaci". Ostrzezenie w dokumencie nie jest bramka. To jest bramka.

Zeby uruchomic platne, trzeba powiedziec to wprost:

    pytest tests/platne --platne
"""
from __future__ import annotations

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--platne", action="store_true", default=False,
        help="pozwol uruchomic testy z tests/platne — WYDAJA PRAWDZIWE PIENIADZE",
    )


def pytest_ignore_collect(collection_path, config):
    """Nie DOTYKAJ platnych bez zgody.

    Uzywamy `ignore_collect`, a nie `skip`, celowo: pominiecie dziala dopiero
    po zaimportowaniu modulu, a tu caly koszt siedzi wlasnie w imporcie.
    Trzeba nie otworzyc pliku wcale.
    """
    if config.getoption("--platne"):
        return False
    return "platne" in collection_path.parts
