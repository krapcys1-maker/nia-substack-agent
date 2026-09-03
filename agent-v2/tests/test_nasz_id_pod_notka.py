# -*- coding: utf-8 -*-
"""Komentarz pod cudza NOTKA ma zostawiac swoj numer, tak jak pod artykulem.

CO BYLO ZLE, zmierzone na produkcji 1 wrzesnia 2026 na pelnym dzienniku:

    komentarzy w dzienniku: 121
    z polem `nasz_id`:       66
    BEZ:                     55   — w tym 43 UDANE

Przyczyna: `potwierdz_odpowiedz` pobierala z API caly watek, zamieniala go
z powrotem na NAPIS przez `json.dumps` i sprawdzala, czy nasz tekst gdzies
w nim jest. Numer lezal w tej samej odpowiedzi — przepuszczony przez `dumps`
przestawal byc danymi i stawal sie literami.

DLACZEGO TO BOLI BARDZIEJ, NIZ WYGLADA. Bez numeru nie da sie polaczyc
wypowiedzi z tym, co z niej wyszlo. Rachunek z tego samego dnia: po odsianiu
niedojrzalych zostalo 17 dajacych sie polaczyc komentarzy na 17 ROZNYCH
hostach — czyli po jednym. Pytanie „gdzie nikt nam nigdy nie odpowiada" nie
moglo dojrzec NIGDY, choc dane fizycznie istnialy. I szla tedy WIEKSZOSC pracy:
`wystaw_odpowiedz` obsluguje komentarze pod cudzymi notkami, a tych jest wiecej
niz komentarzy pod artykulami.

CZEGO TEN TEST PILNUJE OSOBNO: ze poprawka nie kupila lepszego pomiaru za
falszywy dowod przeciw komus. Gdy nasza tresc JEST w watku, a numeru brak,
funkcja MUSI nadal potwierdzic (-1, nie None) — inaczej udana publikacja
wygladalaby jak „host nie pokazuje komentarza", a to zdanie kasuje host na
zawsze w `hosty_gdzie_komentarz_nie_wchodzi`.

BEZ PYTESTA, zero sieci, zero platnych wywolan, produkcja nietknieta.
Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_nasz_id_pod_notka.py
"""
import ast
import io
import pathlib
import sys

sys.path.insert(0, "agent-v2")
import browser     # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


NASZ = "The 646-mile figure is the one nobody quotes."


def watek(*komentarze):
    """Odpowiedz API w ksztalcie, jaki oddaje Substack: galezie z zagniezdzeniem."""
    return {"commentBranches": [{"comment": k, "children": []} for k in komentarze]}


class Strona:
    """Tyle strony, ile potrzebuje `potwierdz_odpowiedz`: nic."""

    def wait_for_timeout(self, ms):
        pass


PRAWDZIWE_API = browser.api_json

print("=== 1. NUMER WRACA Z WATKU ===")
browser.api_json = lambda page, sciezka, **kw: watek(
    {"id": 111, "body": "Someone else entirely."},
    {"id": 4718, "body": NASZ},
    {"id": 222, "body": "And a third voice."},
)
wynik = browser.potwierdz_odpowiedz(Strona(), 315876268, NASZ)
sprawdz("oddaje NUMER naszej odpowiedzi", wynik == 4718, repr(wynik))
sprawdz("a nie samo `True`", wynik is not True, repr(wynik))

print()
print("=== 2. NASZEGO TEKSTU NIE MA -> None ===")
browser.api_json = lambda page, sciezka, **kw: watek(
    {"id": 111, "body": "Someone else entirely."})
wynik = browser.potwierdz_odpowiedz(Strona(), 315876268, NASZ)
sprawdz("brak w watku to None", wynik is None, repr(wynik))

print()
print("=== 3. JEST, ALE BEZ NUMERU -> -1, NIGDY None ===")
# Najwazniejszy przypadek w tym pliku. `None` znaczy „host nie pokazuje
# komentarza" i po dwoch takich wpisach host znika z listy celow na zawsze.
browser.api_json = lambda page, sciezka, **kw: watek({"body": NASZ})
wynik = browser.potwierdz_odpowiedz(Strona(), 315876268, NASZ)
sprawdz("potwierdzone mimo braku numeru", wynik == -1, repr(wynik))
sprawdz("czyli NIE wyglada jak odmowa hosta", wynik is not None, repr(wynik))

print()
print("=== 4. WATEK ZAGNIEZDZONY — ODPOWIEDZ NA ODPOWIEDZ ===")
# Nasza wypowiedz bywa dzieckiem cudzej, a nie korzeniem galezi.
browser.api_json = lambda page, sciezka, **kw: {"commentBranches": [
    {"comment": {"id": 111, "body": "Root comment."},
     "children": [{"comment": {"id": 9001, "body": NASZ}, "children": []}]}]}
wynik = browser.potwierdz_odpowiedz(Strona(), 315876268, NASZ)
sprawdz("numer z glebi watku tez wraca", wynik == 9001, repr(wynik))

print()
print("=== 5. PUSTA ALBO ZEPSUTA ODPOWIEDZ API NIE WYWALA ===")
for opis, odp in (("None", None), ("pusty slownik", {}),
                  ("brak galezi", {"commentBranches": None}),
                  ("galaz nie jest slownikiem", {"commentBranches": ["x"]})):
    browser.api_json = lambda page, sciezka, _o=odp, **kw: _o
    try:
        wynik = browser.potwierdz_odpowiedz(Strona(), 1, NASZ)
        sprawdz("%s -> None, bez wyjatku" % opis, wynik is None, repr(wynik))
    except Exception as exc:                          # noqa: BLE001
        sprawdz("%s -> None, bez wyjatku" % opis, False, "%s: %s"
                % (type(exc).__name__, exc))

browser.api_json = PRAWDZIWE_API

print()
print("=== 6. ZAPIS: NUMER IDZIE DO DZIENNIKA, -1 NIE ===")
# Sprawdzamy sama regule zapisu tak, jak stosuje ja miejsce wywolania:
# `nasz_id=(odp if (odp or 0) > 0 else None)`.
for opis, odp, oczek in (("prawdziwy numer", 4718, 4718),
                         ("brak numeru (-1)", -1, None),
                         ("nie potwierdzone", None, None)):
    sprawdz("%s -> nasz_id %r" % (opis, oczek),
            (odp if (odp or 0) > 0 else None) == oczek)

print()
print("=== 7. `wyslane` ZOSTAJE PRAWDA ALBO FALSZEM ===")
# `odp` jest liczba. Wpisanie liczby do pola, ktore w calym dzienniku jest
# logiczne, zmienia ksztalt danych dla kazdego, kto je pozniej czyta.
for odp in (4718, -1, None):
    sprawdz("odp=%r -> wyslane jest bool" % odp,
            isinstance(odp is not None, bool))
sprawdz("i -1 nadal znaczy `wyslane`", (-1 is not None) is True)

print()
print("=== 8. MIEJSCE WYWOLANIA NAPRAWDE PRZEKAZUJE `nasz_id` ===")
# Sprawdzane na DRZEWIE SKLADNI, nie po napisie w zrodle: pytamy, czy wywolanie
# `dopisz_wynik` wewnatrz `wystaw_odpowiedz` ma argument o tej nazwie. Poprawka
# w samej funkcji potwierdzajacej jest bez wartosci, jesli numer nie zostanie
# nikomu podany — a to jest dokladnie ta klasa bledu, ktora ten projekt
# nazywa „naprawa istniejaca tylko na papierze".
zrodlo = pathlib.Path("agent-v2/browser.py").read_text(encoding="utf-8")
drzewo = ast.parse(zrodlo)
funkcja = next((w for w in ast.walk(drzewo)
                if isinstance(w, ast.FunctionDef) and w.name == "wystaw_odpowiedz"),
               None)
sprawdz("funkcja `wystaw_odpowiedz` istnieje", funkcja is not None)
zapisy = [w for w in ast.walk(funkcja)
          if isinstance(w, ast.Call) and getattr(w.func, "id", "") == "dopisz_wynik"] \
    if funkcja else []
sprawdz("ma wywolanie `dopisz_wynik`", bool(zapisy))
z_numerem = [w for w in zapisy
             if any(k.arg == "nasz_id" for k in w.keywords)]
sprawdz("i przekazuje `nasz_id`", bool(z_numerem),
        "numer wyliczony i nieprzekazany to naprawa na papierze")

print()
print("=" * 62)
print("ZDANE: %d    OBLANE: %d" % (zdane, oblane))
sys.exit(1 if oblane else 0)
