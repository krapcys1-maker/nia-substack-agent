# -*- coding: utf-8 -*-
"""Straznik „czy to nasze konto" ma byc WOLANY, a nie tylko istniec.

## Po co ten plik istnieje

`browser.wlasciwe_konto` istnieje od poczatku i ma docstring, ktory mowi
dokladnie, po co:

    „Czy jestesmy na WLASCIWYM koncie TUZ PRZED PUBLIKACJA. (...) Tresc
     opublikowana z niewlasciwego konta jest bledem, KTOREGO NIE DA SIE
     COFNAC w oczach tych, ktorzy ja zobaczyli."

Skan po calym drzewie — kod, testy, narzedzia — nie znalazl ANI JEDNEJ
wzmianki o tej nazwie poza jej wlasna definicja i wygenerowana mapa funkcji,
ktora wymienia wszystko z definicji. Straznik byl opisany, policzony
i nie chronil niczego.

To jest wada tej samej klasy, co asercja, ktora sie nie wykonuje: kod wyglada
na dzialajacy, bo nikt nie sprawdzil, czy jest osiagalny.

## Czego pilnuje

1. KAZDE WEJSCIE, KTORE COKOLWIEK WYSTAWIA, wola straznika. Lista wejsc jest
   WYPROWADZANA z `bramki.WYSTAWIENIA` (tam juz stoi i sluzy do czegos
   innego), a nie wypisana tutaj drugi raz.
2. Wywolanie stoi WEWNATRZ `try`, nie nad nim — inaczej wyjatek omija
   `finally`, ktore zamyka przegladarke, i zostawia proces Chromium.
3. Straznik odmawia GLOSNO: wyjatek, nie `return False`.
4. Pyta RAZ NA PROCES, nie przy kazdej akcji.
5. KONTRDOWOD: przy nieodpowiadajacym profilu straznik NAPRAWDE rzuca.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_straznik_konta.py
"""
import ast
import pathlib
import sys

sys.path.insert(0, "agent-v2")
import bramki   # noqa: E402
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


ZRODLO = pathlib.Path("agent-v2/browser.py").read_text(encoding="utf-8")
DRZEWO = ast.parse(ZRODLO)

# WEJSCIA WYPROWADZONE, NIE WYPISANE. `bramki.WYSTAWIENIA` juz je zna i sluzy
# do czegos innego — druga lista tych samych nazw rozjechalaby sie przy
# pierwszym dopisanym sposobie wystawiania.
WEJSCIA = {f.name for f in DRZEWO.body
           if isinstance(f, ast.FunctionDef) and f.name in bramki.WYSTAWIENIA}

print("=== 1. KAZDE WEJSCIE WYSTAWIAJACE WOLA STRAZNIKA ===")
print("  wejsc w `browser.py`: %d (%s)"
      % (len(WEJSCIA), ", ".join(sorted(WEJSCIA))))
sprawdz("wejsc jest wiecej niz zero", bool(WEJSCIA), sorted(bramki.WYSTAWIENIA))

# STRAZNIK MOZE STAC O JEDEN POZIOM NIZEJ. `zasubskrybuj` to trzy linijki,
# ktore oddaja robote `_klik_na_profilu` — i to tam siedzi `try`, przegladarka
# i klikniecie. Test pytajacy tylko o cialo wejscia mierzylby SKLADNIE, a nie
# ochrone: pokazywalby brak tam, gdzie ochrona jest, i kazalby dopisac drugie,
# zbedne sprawdzenie.
_FUNKCJE = {f.name: f for f in DRZEWO.body if isinstance(f, ast.FunctionDef)}


def _ma_straznika(f, glebokosc: int = 1) -> bool:
    """Czy ta funkcja wola straznika — sama albo przez funkcje, ktorej ufa."""
    for w in ast.walk(f):
        if (isinstance(w, ast.Call)
                and getattr(w.func, "id", None) == "wymagaj_wlasciwego_konta"):
            return True
    if glebokosc <= 0:
        return False
    for w in ast.walk(f):
        if not isinstance(w, ast.Call):
            continue
        nazwa = getattr(w.func, "id", None)
        pod = _FUNKCJE.get(nazwa) if nazwa else None
        if pod is not None and pod is not f and _ma_straznika(pod, glebokosc - 1):
            return True
    return False


def _try_ze_straznikiem(f):
    """Funkcja (ta albo wywolana przez nia), w ktorej straznik stoi w `try`."""
    for w in ast.walk(f):
        if (isinstance(w, ast.Call)
                and getattr(w.func, "id", None) == "wymagaj_wlasciwego_konta"):
            return f
    for w in ast.walk(f):
        if not isinstance(w, ast.Call):
            continue
        nazwa = getattr(w.func, "id", None)
        pod = _FUNKCJE.get(nazwa) if nazwa else None
        if pod is not None and pod is not f and _ma_straznika(pod, 0):
            return pod
    return None


bez_straznika = []
poza_try = []
for f in DRZEWO.body:
    if not isinstance(f, ast.FunctionDef) or f.name not in WEJSCIA:
        continue
    if not _ma_straznika(f):
        bez_straznika.append(f.name)
        continue
    f = _try_ze_straznikiem(f) or f
    wolania = [w for w in ast.walk(f) if isinstance(w, ast.Call)
               and getattr(w.func, "id", None) == "wymagaj_wlasciwego_konta"]
    # 2. WEWNATRZ `try`. Wyjatek rzucony nad nim omija `finally`, ktore zamyka
    #    przegladarke — i zostawia proces Chromium przy zyciu.
    proba = next((x for x in f.body if isinstance(x, ast.Try)), None)
    if proba is None:
        poza_try.append("%s (brak `try`)" % f.name)
        continue
    w_try = any(w in ast.walk(proba) for w in wolania)
    if not w_try:
        poza_try.append(f.name)

sprawdz("kazde wejscie wola straznika", not bez_straznika, bez_straznika)

print()
print("=== 2. WYWOLANIE STOI WEWNATRZ `try` ===")
sprawdz("zadne nie stoi nad `try`", not poza_try, poza_try)

print()
print("=== 3. STRAZNIK ODMAWIA GLOSNO ===")
_str = ast.parse(ZRODLO)
_fn = next(f for f in _str.body
           if isinstance(f, ast.FunctionDef) and f.name == "wymagaj_wlasciwego_konta")
_rzuca = [w for w in ast.walk(_fn) if isinstance(w, ast.Raise)]
sprawdz("rzuca wyjatek, a nie zwraca falsz", bool(_rzuca), len(_rzuca))
sprawdz("i ma wlasny typ wyjatku", hasattr(browser, "NieToKonto"))

print()
print("=== 4. PYTA RAZ NA PROCES ===")
# Podstawiamy `api_json`, bo straznik pyta profilu WPROST — patrz jego
# docstring: musi odroznic „inny uchwyt" od „brak odpowiedzi", a `wlasciwe_konto`
# skleja oba w jeden falsz.
_ile = [0]
_prawdziwe = browser.api_json


def _api_nasze(page, sciezka, **k):
    _ile[0] += 1
    return {"handle": browser.PROFIL_HANDLE}


browser._KONTO_SPRAWDZONE = False
try:
    browser.api_json = _api_nasze
    browser.wymagaj_wlasciwego_konta(None)
    browser.wymagaj_wlasciwego_konta(None)
    browser.wymagaj_wlasciwego_konta(None)
    sprawdz("trzy wywolania, jedno pytanie", _ile[0] == 1, _ile[0])
finally:
    browser.api_json = _prawdziwe
    browser._KONTO_SPRAWDZONE = False

print()
print("=== 5. TRZY STANY: MY / NIE MY / NIE WIADOMO ===")
# „Nie wiadomo" NIE MOZE znaczyc „nie to konto". Pierwsza wersja straznika nie
# robila tej roznicy i oblala jedenascie testow z wlasnymi atrapami strony:
# atrapa milczaca w tej sprawie mowila „NieToKonto".


def _api_cudze(page, sciezka, **k):
    return {"handle": "ktos-zupelnie-inny"}


def _api_milczy(page, sciezka, **k):
    return None


def _api_pada(page, sciezka, **k):
    raise RuntimeError("siec padla")


try:
    browser.api_json = _api_cudze
    browser._KONTO_SPRAWDZONE = False
    try:
        browser.wymagaj_wlasciwego_konta(None)
        sprawdz("CUDZY uchwyt -> wyjatek", False, "przeszlo bez wyjatku")
    except browser.NieToKonto as exc:
        sprawdz("CUDZY uchwyt -> wyjatek", True)
        sprawdz("i komunikat podaje OBA uchwyty",
                "ktos-zupelnie-inny" in str(exc)
                and browser.PROFIL_HANDLE in str(exc), str(exc)[:90])

    for nazwa, atrapa in (("brak odpowiedzi", _api_milczy),
                          ("wyjatek z sieci", _api_pada)):
        browser.api_json = atrapa
        browser._KONTO_SPRAWDZONE = False
        try:
            browser.wymagaj_wlasciwego_konta(None)
            sprawdz("%-16s -> idziemy dalej" % nazwa, True)
        except browser.NieToKonto:
            sprawdz("%-16s -> idziemy dalej" % nazwa, False,
                    "zatrzymal przebieg, choc niczego nie stwierdzil")
        sprawdz("%-16s -> i NIE zapamietuje sprawdzenia" % nazwa,
                browser._KONTO_SPRAWDZONE is False)
finally:
    browser.api_json = _prawdziwe
    browser._KONTO_SPRAWDZONE = False

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
