# -*- coding: utf-8 -*-
"""Raport normy liczy dzien po harmonogramie presetu, nie po szablonie zegara.

## Pomiar

Serwer, 13 wrzesnia 2026, 05:10 UTC:

    STAN NA DZIS (2026-09-13, UTC) — po 1 z 5 przebiegow
       (norma rozklada sie na caly dzien — do konca zostalo 4)

Zainstalowany `nia2-agent.timer` odpala 00:30 i 13:30. Preset mowi to samo:
`GODZINY_PRZEBIEGOW_UTC = ('00:30', '13:30')`. Raport czytal jednak
`agent-v2/systemd/nia-agent.timer`, czyli SZABLON z repozytorium — z pieciu
godzinami sprzed przestawienia. Do konca dnia zostal jeden przebieg, a raport
mowil o czterech, i tak samo mylil sie przy „ile powinno juz byc zrobione".

BEZ PYTESTA, bez sieci. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_norma_zna_harmonogram_presetu.py
"""
import pathlib
import sys
import tempfile
from datetime import datetime, timezone

sys.path.insert(0, "agent-v2")
import config   # noqa: E402
import norma    # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# Szablon taki, jaki lezy na serwerze: piec starych godzin.
SZABLON = pathlib.Path(tempfile.mkdtemp()) / "nia-agent.timer"
SZABLON.write_text("[Timer]\n" + "".join(
    "OnCalendar=*-*-* %s:00\n" % g
    for g in ("11:20", "17:00", "19:20", "21:30", "23:40")), encoding="utf-8")

oryg = (norma.ZEGAR, config.GODZINY_PRZEBIEGOW_UTC)


def o(godz, minuta):
    return datetime(2026, 9, 13, godz, minuta, tzinfo=timezone.utc)


try:
    norma.ZEGAR = SZABLON
    config.GODZINY_PRZEBIEGOW_UTC = ("00:30", "13:30")

    print("=== 1. GODZINY Z PRESETU ===")
    g = norma.godziny_przebiegow()
    sprawdz("dwa przebiegi, 00:30 i 13:30", g == [30, 810], g)
    sprawdz("oznaczone jako odczytane, nie zgadniete", norma.ZEGAR_ODCZYTANY is True)

    print()
    print("=== 2. ILE JEST NALEZNE O KTOREJ ===")
    # Przebieg nalezny dopiero, gdy zaczal sie NASTEPNY — zasada z docstringu
    # `przebiegow_naleznych`, tu nieruszana.
    sprawdz("05:10 — zaden jeszcze nie nalezny, z dwoch",
            norma.przebiegow_naleznych(o(5, 10)) == (0, 2),
            norma.przebiegow_naleznych(o(5, 10)))
    sprawdz("14:00 — nalezny jeden z dwoch",
            norma.przebiegow_naleznych(o(14, 0)) == (1, 2),
            norma.przebiegow_naleznych(o(14, 0)))
    # KONTRDOWOD: tak liczyl raport na serwerze, czytajac szablon.
    config.GODZINY_PRZEBIEGOW_UTC = ()
    sprawdz("bez godzin w presecie wraca stara piatka z szablonu",
            norma.przebiegow_naleznych(o(14, 0))[1] == 5,
            norma.przebiegow_naleznych(o(14, 0)))

    print()
    print("=== 3. ZEPSUTY WPIS NIE WYWRACA RAPORTU ===")
    config.GODZINY_PRZEBIEGOW_UTC = ("00:30", "pol do trzeciej")
    g = norma.godziny_przebiegow()
    sprawdz("nieczytelna godzina -> zapas z jednostki, bez wyjatku",
            g == [680, 1020, 1160, 1290, 1420], g)
    config.GODZINY_PRZEBIEGOW_UTC = ()
    norma.ZEGAR = pathlib.Path(tempfile.mkdtemp()) / "brak.timer"
    g = norma.godziny_przebiegow()
    sprawdz("ani presetu, ani jednostki -> rowny rozklad, oznaczony jako zgadniety",
            len(g) == max(1, config.PRZEBIEGOW_DZIENNIE)
            and norma.ZEGAR_ODCZYTANY is False, (g, norma.ZEGAR_ODCZYTANY))
finally:
    norma.ZEGAR, config.GODZINY_PRZEBIEGOW_UTC = oryg

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
