# -*- coding: utf-8 -*-
"""Cel komentarza ma gorna granice wieku — rozmowa pod notka sprzed miesiaca juz sie skonczyla.

## Po co ten plik istnieje

Zmierzone 2026-09-05 na zywym przebiegu kartridza `ai` (konto testowe):
pierwszy komentarz na zywo poszedl pod notke sprzed 30 dni (43 662 minuty),
znaleziona szukaniem po hasle „customer service chatbot failures". Filtry
wieku znaly tylko DOLNA granice (nie komentuj pod czyms sprzed kwadransa —
to wyglada na czatowanie na wpis). Gornej nie bylo, wiec wygrywal cel
z najwieksza liczba reakcji, choccby zebral je miesiac temu.

`config.MAKS_WIEK_CELU_DNI` obowiazuje w trzech miejscach, ktore oddaja cele:
kanal postow, kanal notek i szukanie po haslach. Nieznana data nie blokuje —
tak jak przy dolnej granicy.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_wiek_celu.py
"""
import pathlib
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "agent-v2")
import config  # noqa: E402
import kanal   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


def sprzed(dni: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=dni)).isoformat()


print("=== 1. GRANICA DZIALA NA DACIE ===")
sprawdz("stala istnieje i jest dodatnia", isinstance(config.MAKS_WIEK_CELU_DNI, int)
        and config.MAKS_WIEK_CELU_DNI > 0, config.MAKS_WIEK_CELU_DNI)
sprawdz("cel sprzed 30 dni jest za stary (przypadek z 2026-09-05)",
        kanal._za_stary({"data": sprzed(30.3)}))
sprawdz("cel sprzed 5 dni przechodzi", not kanal._za_stary({"data": sprzed(5)}))
sprawdz("cel dokladnie na granicy przechodzi",
        not kanal._za_stary({"data": sprzed(config.MAKS_WIEK_CELU_DNI - 0.01)}))
sprawdz("cel o dzien za granica odpada",
        kanal._za_stary({"data": sprzed(config.MAKS_WIEK_CELU_DNI + 1)}))
sprawdz("nieznana data NIE blokuje (brak daty to nie dowod starosci)",
        not kanal._za_stary({"data": ""}) and not kanal._za_stary({}))
sprawdz("data z Z na koncu tez sie liczy",
        kanal._za_stary({"data": (datetime.now(timezone.utc) - timedelta(days=40))
                         .strftime("%Y-%m-%dT%H:%M:%SZ")}))

print()
print("=== 2. WPIETE WE WSZYSTKIE TRZY ZRODLA CELOW ===")
zrodlo = pathlib.Path("agent-v2/kanal.py").read_text(encoding="utf-8")


def blok(nazwa: str) -> str:
    i = zrodlo.index("def %s(" % nazwa)
    koniec = zrodlo.find("\ndef ", i + 10)          # ostatnia funkcja pliku nie ma nastepnej
    return zrodlo[i:] if koniec == -1 else zrodlo[i:koniec]


for f in ("posty_z_kanalu", "notki_z_kanalu", "szukaj_nowych"):
    b = blok(f)
    # szukanie po haslach odklada kandydata do slownika, kanaly do listy
    dodanie = "append(kandydat)" if "append(kandydat)" in b else 'znalezione[kandydat["url"]] = kandydat'
    sprawdz("%s odsiewa za stare przed dodaniem do wyniku" % f,
            "_za_stary(kandydat)" in b and dodanie in b
            and b.index("_za_stary(kandydat)") < b.index(dodanie), dodanie)
_szukanie = zrodlo[zrodlo.index("nowych celow") - 4000:zrodlo.index("nowych celow")]
sprawdz("szukanie po haslach odsiewa za stare", "_za_stary(kandydat)" in _szukanie)
sprawdz("i mowi w logu, ile odrzucilo jako stare", "za starych" in zrodlo and "za stare" in zrodlo)

print()
print("=== 3. KONTRDOWOD: DOLNA GRANICA NIE ZALATWIALA TEGO ===")
# Dolna granica pyta „czy za swieze?" — cel sprzed miesiaca przechodzil ja zawsze.
sprawdz("cel sprzed 30 dni NIE jest za swiezy (stara regula go przepuszczala)",
        not kanal._za_swiezy({"data": sprzed(30.3)}))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
