# -*- coding: utf-8 -*-
"""Ilu nas czyta — laczna liczba, zapisywana w czasie.

CZEGO NIE MIELISMY. System zapisywal:
  - subskrypcje przypisane do KONKRETNEGO wpisu (pole `subskrypcje`),
  - wlasne WYCHODZACE subskrypcje („my subskrybujemy kogos") — 18 wpisow
    w dzienniku pod nazwa `rodzaj: subskrypcja`, co latwo pomylic z czyms
    odwrotnym.

LACZNEJ liczby NASZYCH subskrybentow w czasie nie zapisywal nikt. Jedyny slad
to kopia listy z 23 sierpnia 2026 — cztery osoby — i nic pozniej. Krzywa
4 -> 8 z panelu Substacka zyla wylacznie u Substacka.

Cel calego systemu to wzrost konta, a jedyna liczba, ktora ten wzrost mierzy
wprost, nie byla nigdzie zapisywana.

ZERO DODATKOWYCH ZAPYTAN: `/api/v1/user/<handle>/public_profile` wolamy i tak
przy kazdym pomiarze, zeby dostac numer profilu. Te liczby juz tam sa —
zmierzone 31 sierpnia:

    subscriberCountNumber 7, followerCount 8,
    visibleSubscriptionsCount 28, primaryPublicationRecommendationCount 0

DWIE LICZBY NA SUBSKRYBENTOW, BO SUBSTACK PODAJE DWIE: panel wydawcy mowil 8,
profil 7, a zakladka wymieniala siedem osob (osma to najpewniej wlasciciel).
Zapisujemy obie zamiast wybierac, ktora jest „prawdziwa".

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo.
"""
import json
import pathlib
import sys
import tempfile

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


# ODPOWIEDZ PRZEPISANA Z ZYWEGO PROFILU, nie wymyslona.
PROFIL = {
    "id": 900000005,
    "handle": "your-handle",
    "subscriberCountNumber": 7,
    "rough_num_free_subscribers_int": 1,
    "followerCount": 8,
    "visibleSubscriptionsCount": 28,
    "primaryPublicationRecommendationCount": 0,
    "bio": "Writing about AI agents...",
}

stary = browser.WZROST
browser.WZROST = pathlib.Path(tempfile.mkdtemp()) / "wzrost.jsonl"

try:
    print("=== 1. LICZBY TRAFIAJA DO REKORDU ===")
    s = browser.zapisz_wzrost_konta(PROFIL)
    sprawdz("subskrybenci", s and s["subskrybenci"] == 7, s)
    sprawdz("obserwujacy", s and s["obserwujacy"] == 8, s)
    sprawdz("nasze wychodzace subskrypcje", s and s["nasze_subskrypcje"] == 28)
    sprawdz("nasze rekomendacje", s and s["nasze_rekomendacje"] == 0)
    sprawdz("druga liczba subskrybentow tez zapisana",
            s and "subskrybenci_darmowi" in s, sorted(s or {}))
    sprawdz("i data pomiaru", s and str(s.get("kiedy", "")).startswith("20"))

    print()
    print("=== 2. TO HISTORIA, NIE OSTATNIA WARTOSC ===")
    # Bez historii nie ma krzywej, a pytanie brzmi „czy ROSNIE", nie „ile jest".
    browser.zapisz_wzrost_konta(dict(PROFIL, subscriberCountNumber=9,
                                     followerCount=11))
    linie = browser.WZROST.read_text(encoding="utf-8").strip().splitlines()
    sprawdz("drugi zapis dopisany, nie nadpisany", len(linie) == 2, len(linie))
    ost = json.loads(linie[-1])
    sprawdz("nowa wartosc na koncu", ost["subskrybenci"] == 9, ost)
    pierwszy = json.loads(linie[0])
    sprawdz("stara wartosc zachowana", pierwszy["subskrybenci"] == 7, pierwszy)

    print()
    print("=== 3. SMIECI NIE PSUJA POMIARU ===")
    # Zapis jest premia, pomiar wazniejszy — tak samo jak przy autorze
    # polubionego wpisu. Wyjatek tutaj zabralby cala reszte przebiegu.
    for opis, dane in (("None", None), ("napis", "cos"), ("lista", [1, 2]),
                       ("pusty slownik", {})):
        try:
            wy = browser.zapisz_wzrost_konta(dane)
            ok = wy is None or isinstance(wy, dict)
        except Exception as exc:
            ok = False
            opis += " (WYJATEK %s)" % type(exc).__name__
        sprawdz("  %s -> bez wyjatku" % opis, ok)
    # ZERO Z NIEUDANEGO ODCZYTU NIE MOZE TRAFIC DO SZEREGU. Pierwsza wersja
    # tego testu zatwierdzala odwrotnie („pusty slownik daje zera") i produkcja
    # dostala dwa wiersze z samymi zerami — audyt policzyl z nich
    # „subskrybentow -7" godzine pozniej. Wiersz zerowy jest nie do odroznienia
    # od dnia, w ktorym wszyscy odeszli.
    przed = len(browser.WZROST.read_text(encoding="utf-8").strip().splitlines())
    sprawdz("pusty profil nie daje wiersza",
            browser.zapisz_wzrost_konta({}) is None)
    sprawdz("profil bez licznikow tez nie",
            browser.zapisz_wzrost_konta({"id": 1, "handle": "x"}) is None)
    sprawdz("i nic nie dopisalo sie do pliku",
            len(browser.WZROST.read_text(encoding="utf-8")
                .strip().splitlines()) == przed)
    # KONTRDOWOD: jeden niezerowy licznik wystarczy, zeby wiersz powstal —
    # inaczej zgubilibysmy dzien, w ktorym naprawde spadlo do zera.
    sprawdz("ale jeden prawdziwy licznik juz tak",
            (browser.zapisz_wzrost_konta({"followerCount": 3}) or {})
            .get("obserwujacy") == 3)

    print()
    print("=== 4. WPIETE TAM, GDZIE PROFIL I TAK JEST CZYTANY ===")
    # Zadnego dodatkowego zapytania: te liczby przychodza w odpowiedzi,
    # ktora i tak wlasnie dostalismy.
    zrodlo = pathlib.Path("agent-v2/browser.py").read_text(encoding="utf-8")
    i = zrodlo.index("def nasze_pozycje_do_pomiaru(")
    blok = zrodlo[i:zrodlo.index("\ndef ", i + 10)]
    sprawdz("pomiar zapisuje wzrost", "zapisz_wzrost_konta(profil)" in blok)
    sprawdz("i robi to z TEJ SAMEJ odpowiedzi profilu",
            blok.index("public_profile") < blok.index("zapisz_wzrost_konta"))
    sprawdz("nie ma drugiego zapytania o profil",
            blok.count("public_profile") == 1, blok.count("public_profile"))

    print()
    print("=== 5. KONTRDOWOD: BEZ TEGO NIE MA CZEGO NARYSOWAC ===")
    # Gdyby wzrost dalo sie odczytac z tego, co juz zbieramy, ta poprawka
    # bylaby zbedna. Pole `subskrypcje` w statystykach liczy przypisania do
    # WPISU — sumowanie ich nie daje stanu konta, bo nie kazdy subskrybent
    # przyszedl z jakiegokolwiek wpisu.
    import statystyki
    sprawdz("rekord statystyk nie ma laczej liczby subskrybentow",
            "subskrybenci" not in statystyki.z_kart({}),
            sorted(statystyki.z_kart({})))
finally:
    browser.WZROST = stary

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
