# -*- coding: utf-8 -*-
"""Publikacja tylko dla placacych ma byc odsiana PRZED oplacona ocena.

ZMIERZONE w dzienniku systemowym z siedmiu dni: CZTERDZIESCI DWA razy padlo
„komentarze tylko dla placacych" — i za kazdym razem PO tym, jak model ocenil
cel i wzial za to pieniadze, oraz po uruchomieniu przegladarki, zeby o to
zapytac. Jeden przebieg wygladal tak:

    [cele] warte komentarza: 4/24
    only_paid — odpuszczam    x3
    komentarze: 1             (zaplanowano 3)

Trzy z czterech wybranych celow byly nie do skomentowania. Plan mowil trzy,
wyszedl jeden — i to jest jedna z przyczyn, dla ktorych komentarze stoja na 47%
wykonania planu.

DZIEWIATY RAZ TEGO SAMEGO KSZTALTU: sygnal policzony i wyrzucony. Odmowa byla
tylko DRUKOWANA, wiec ta sama platna publikacja wracala do puli przy kazdym
przebiegu.

JEDNA OBSERWACJA WYSTARCZY, inaczej niz przy nieudanych komentarzach, gdzie prog
to dwie proby. Tam jedno niepowodzenie moze byc awaria po drugiej stronie; tutaj
API oddaje USTAWIENIE publikacji. Zapis jest odwracalny: udane wystawienie
kasuje host z listy, wiec zmiana ustawien u wydawcy odblokowuje go sama.

BEZ PYTESTA, bez sieci i bez platnych wywolan. Uruchamiac z korzenia repo.
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import browser   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


katalog = pathlib.Path(tempfile.mkdtemp())
stary = browser.PLATNE_HOSTY
browser.PLATNE_HOSTY = katalog / "platne.json"

try:
    print("=== 1. PUSTA PAMIEC NIE WYWALA SIE ===")
    sprawdz("brak pliku daje pusty zbior",
            browser.hosty_tylko_dla_placacych() == set())
    browser.PLATNE_HOSTY.write_text("to nie jest json", encoding="utf-8")
    sprawdz("uszkodzony plik tez",
            browser.hosty_tylko_dla_placacych() == set())
    browser.PLATNE_HOSTY.unlink()

    print()
    print("=== 2. JEDNA OBSERWACJA WYSTARCZY ===")
    browser.zapamietaj_platny_host("slowboring.com", "only_paid")
    sprawdz("host zapamietany po pierwszym razie",
            "slowboring.com" in browser.hosty_tylko_dla_placacych())
    stan = json.loads(browser.PLATNE_HOSTY.read_text(encoding="utf-8"))
    sprawdz("z powodem i data",
            stan["slowboring.com"]["prawo"] == "only_paid"
            and stan["slowboring.com"]["kiedy"],
            stan["slowboring.com"])

    print()
    print("=== 3. WWW NIE TWORZY DRUGIEGO WPISU ===")
    browser.zapamietaj_platny_host("www.slowboring.com", "only_paid")
    sprawdz("ten sam host mimo przedrostka",
            len(browser.hosty_tylko_dla_placacych()) == 1,
            browser.hosty_tylko_dla_placacych())

    print()
    print("=== 4. UDANY KOMENTARZ KASUJE HOST ===")
    # Wydawca moze zmienic ustawienia. Pamiec ma go wtedy puscic sama.
    browser.zapamietaj_platny_host("thebignewsletter.com", "only_founding")
    sprawdz("dwa hosty na liscie",
            len(browser.hosty_tylko_dla_placacych()) == 2)
    browser.zapomnij_platny_host("www.thebignewsletter.com")
    sprawdz("po udanym komentarzu zostaje jeden",
            browser.hosty_tylko_dla_placacych() == {"slowboring.com"},
            browser.hosty_tylko_dla_placacych())
    browser.zapomnij_platny_host("nie-bylo-takiego.com")
    sprawdz("kasowanie nieistniejacego nie psuje pliku",
            browser.hosty_tylko_dla_placacych() == {"slowboring.com"})

    print()
    print("=== 5. ODSIEW DZIALA NA PULI CELOW ===")
    from urllib.parse import urlparse
    platne = browser.hosty_tylko_dla_placacych()

    def odsiej(pula):
        return [x for x in pula
                if urlparse(x["url"]).netloc.lower().removeprefix("www.")
                not in platne]

    pula = [
        {"url": "https://slowboring.com/p/jeden"},
        {"url": "https://www.slowboring.com/p/dwa"},
        {"url": "https://otwarty.substack.com/p/trzy"},
        {"url": "https://inny.example.com/p/cztery"},
    ]
    zostalo = odsiej(pula)
    sprawdz("platny host wypada, takze z www", len(zostalo) == 2,
            [x["url"] for x in zostalo])
    sprawdz("otwarte zostaja",
            all("slowboring" not in x["url"] for x in zostalo))

    print()
    print("=== 6. KONTRDOWOD: BEZ PAMIECI NIC NIE JEST ODSIANE ===")
    # Gdyby sekcja 5 przechodzila takze przy pustej pamieci, nie dowodzilaby nic.
    puste = set()
    bez = [x for x in pula
           if urlparse(x["url"]).netloc.lower().removeprefix("www.") not in puste]
    sprawdz("przy pustej pamieci zostaja wszystkie cztery", len(bez) == 4)
finally:
    pass

print()
print("=== 6b. ZAPIS NAPRAWDE TWORZY PLIK ===")
# TA SEKCJA ISTNIEJE Z POWODU. Pierwsza wersja `zapamietaj_platny_host` wolala
# `now()`, ktorego w browser.py NIE MA — a caly zapis stoi w `try/except`, bo
# „pamiec jest premia, nie warunkiem". Osłona zamienila wiec BLAD w wypisane
# ostrzezenie i funkcja po cichu nie robila nic. Sprawdzamy SKUTEK, nie to, ze
# wywolanie sie nie wywalilo.
browser.PLATNE_HOSTY = katalog / "skutek.json"
browser.zapamietaj_platny_host("sprawdzam.example", "only_paid")
sprawdz("plik naprawde powstal", browser.PLATNE_HOSTY.exists())
sprawdz("i host w nim jest",
        "sprawdzam.example" in browser.hosty_tylko_dla_placacych())
browser.PLATNE_HOSTY = stary

print()
print("=== 7. WPIETE W PRZEBIEG WE WLASCIWYM MIEJSCU ===")
rp = pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8")
sprawdz("run.py odsiewa platne", "hosty_tylko_dla_placacych()" in rp)
sprawdz("i robi to PRZED ocena celow",
        rp.index("hosty_tylko_dla_placacych()")
        < rp.index("stages.wybierz_cele(conn, run_id, unikalne)"),
        "kolejnosc wywolan w run.py")
sprawdz("udany komentarz kasuje host", "zapomnij_platny_host" in rp)
bp = pathlib.Path("agent-v2/browser.py").read_text(encoding="utf-8")
sprawdz("a odmowa go zapamietuje", "zapamietaj_platny_host(host, prawo)" in bp)
sprawdz("log podaje teraz hosta, nie sam powod",
        '{host}: komentarze tylko dla placacych' in bp)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
