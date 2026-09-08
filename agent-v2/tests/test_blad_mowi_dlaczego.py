# -*- coding: utf-8 -*-
"""Zapis awarii ma niesc POWOD, nie sam naglowek.

## Po co ten plik istnieje

8 wrzesnia 2026 odpowiedzi przestaly sie publikowac: trzy porazki tego dnia,
zero przez trzy poprzednie. W dzienniku produkcyjnym zostawalo dokladnie tyle:

    TimeoutError: Locator.click: Timeout 30000ms exceeded.
    Call log:
      - waiting for get_by_role("button", name="Post").first
        - locator resolved to <button tabindex="0" type="button" data-testid="comp

i urwane w polowie atrybutu. Bo `browser` obcinal `[:200]` OD POCZATKU,
a Playwright pisze diagnoze na KONCU: „element is not stable", „element
intercepts pointer events", „element is not enabled".

Naglowek mowi, ZE nie kliknelo. Ogon mowi, DLACZEGO. Wyrzucalismy ogon —
i przez to kazda taka awaria wymagala, zeby czlowiek wszedl do przegladarki
i zobaczyl rzecz, ktora biblioteka juz nam powiedziala.

BEZ PYTESTA, bez sieci, bez przegladarki. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_blad_mowi_dlaczego.py
"""
import sys

sys.path.insert(0, "agent-v2")
import browser  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


class TimeoutError_(Exception):
    pass


# --- PRAWDZIWY KSZTALT KOMUNIKATU PLAYWRIGHTA --------------------------------
PRAWDZIWY = TimeoutError_(
    "Locator.click: Timeout 30000ms exceeded.\n"
    "Call log:\n"
    "  - waiting for get_by_role(\"button\", name=\"Post\").first\n"
    "    - locator resolved to <button tabindex=\"0\" type=\"button\" "
    "data-testid=\"composer-post-button\" class=\"button-9f8a6c primary\">Post</button>\n"
    "  - attempting click action\n"
    "    - waiting for element to be visible, enabled and stable\n"
    "    - element is visible, enabled and stable\n"
    "    - scrolling into view if needed\n"
    "    - done scrolling\n"
    "    - element intercepts pointer events\n"
    "  - retrying click action\n")

print("=== 1. POWOD PRZEZYWA, NAGLOWEK ZOSTAJE ===")
w = browser.opis_bledu(PRAWDZIWY)
sprawdz("jest nazwa wyjatku", w.startswith("TimeoutError_"), w[:60])
sprawdz("jest naglowek o tym, ZE nie kliknelo", "Timeout 30000ms exceeded" in w,
        w[:80])
sprawdz("JEST POWOD z konca", "intercepts pointer events" in w, w[-90:])
sprawdz("miesci sie w limicie", len(w) <= browser.DLUGOSC_OPISU_BLEDU,
        "%d znakow" % len(w))

print()
print("=== 2. TAK BYLO PRZED POPRAWKA — DLA PORZADKU ===")
stary = ("%s: %s" % (type(PRAWDZIWY).__name__, PRAWDZIWY))[:200]
sprawdz("stary zapis GUBIL powod", "intercepts pointer events" not in stary,
        stary[-60:])
sprawdz("i urywal sie w srodku znacznika", len(stary) == 200 and ">" not in stary[-60:],
        repr(stary[-24:]))

print()
print("=== 3. KROTKI KOMUNIKAT ZOSTAJE NIETKNIETY ===")
# Regula, ktora przepisuje kazdy blad, utrudnia czytanie tych prostych.
krotki = ValueError("nie ma przycisku Post")
sprawdz("krotki bez zmian", browser.opis_bledu(krotki) == "ValueError: nie ma przycisku Post",
        browser.opis_bledu(krotki))

print()
print("=== 4. PRZYPADKI GRANICZNE NIE WYWALAJA FUNKCJI ===")
sprawdz("pusty komunikat", browser.opis_bledu(ValueError("")) == "ValueError:",
        repr(browser.opis_bledu(ValueError(""))))
sprawdz("same nowe linie", browser.opis_bledu(ValueError("\n\n\n")).startswith("ValueError"),
        repr(browser.opis_bledu(ValueError("\n\n\n"))))
dlugi = browser.opis_bledu(ValueError("x" * 5000))
sprawdz("jedna dluga linia przycieta do limitu",
        len(dlugi) <= browser.DLUGOSC_OPISU_BLEDU, "%d znakow" % len(dlugi))

print()
print("=== 5. ZADNE MIEJSCE NIE ZOSTALO PRZY STARYM OBCIECIU ===")
zrodlo = open("agent-v2/browser.py", encoding="utf-8").read()
sprawdz("zero starych obciec bledu",
        'f"{type(exc).__name__}: {exc}"[:200]' not in zrodlo)
sprawdz("wszystkie ida przez opis_bledu", zrodlo.count("opis_bledu(exc)") >= 14,
        "%d miejsc" % zrodlo.count("opis_bledu(exc)"))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
