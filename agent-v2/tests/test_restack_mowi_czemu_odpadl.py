# -*- coding: utf-8 -*-
"""Kazdy odpad kandydata na restack zostawia slad, i na koncu jest rachunek.

## Pomiar

Raport normy, produkcja, 7-10 wrzesnia 2026: restacki na 42 procent normy,
przy JEDNEJ nieudanej probie w calym oknie. Czyli nie padaja — po prostu ich
nie ma. W logu, co dzien to samo:

    -- restacki --
      notek w kanale do rozwazenia: 6
      [restack] claude-opus-5  wej=8541 wyj=220  $0.0482
        RESTACK u Benjamin Laval: ...
        podane dalej 1/2

Szesciu kandydatow i JEDNO pytanie do modelu. Pieciu odpadlo przed ocena i nie
zostawilo po sobie ani slowa, bo wszystkie trzy odsiewy konczyly sie golym
`continue`: przycisk niewidoczny, notka nasza, brak odczytanej tresci.

Z zewnatrz wygladalo to na pusty kanal. Kanal pusty nie byl.

## Czego ten test NIE robi

Nie rozstrzyga, ktory z trzech odsiewow zjada kandydatow — tego nie wie nikt,
dopoki nie zmierzy. Pilnuje tylko, zeby nastepny przebieg to POWIEDZIAL, i zeby
nikt nie wrocil do cichego `continue`.

BEZ PYTESTA, bez sieci, bez przegladarki. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_restack_mowi_czemu_odpadl.py
"""
import ast
import io
import sys

sys.path.insert(0, "agent-v2")

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


ZRODLO = io.open("agent-v2/browser.py", encoding="utf-8").read()
CIALO = ""
for w in ast.walk(ast.parse(ZRODLO)):
    if isinstance(w, ast.FunctionDef) and w.name == "restackuj_w_kanale":
        CIALO = ast.get_source_segment(ZRODLO, w) or ""

print("=== 1. TRZY ODSIEWY MOWIA O SOBIE ===")
sprawdz("blok restackow znaleziony", bool(CIALO))
for opis, fraza in (("przycisk niewidoczny", "przycisk niewidoczny"),
                    ("nasza wlasna notka", "to nasza wlasna notka"),
                    ("nie odczytalem tresci", "nie odczytalem tresci notki")):
    sprawdz("mowi o odpadzie: %s" % opis, fraza in CIALO, fraza)

print()
print("=== 2. I KAZDY MA SWOJ LICZNIK ===")
for pole in ("niewidoczne", "nasze", "bez_tresci"):
    sprawdz("licznik %s" % pole, 'wynik["%s"] = wynik.get("%s", 0) + 1'
            % (pole, pole) in CIALO, pole)
# Ten byl juz wczesniej i ma zostac.
sprawdz("poza rewirem nadal liczony", '"poza_rewirem"' in CIALO)

print()
print("=== 3. NA KONIEC JEST RACHUNEK CALEGO BLOKU ===")
# Bez jednego zdania podsumowania trzeba czytac log linia po linii, zeby
# odpowiedziec na pytanie „czemu jeden restack, skoro budzet ma cztery".
sprawdz("rachunek istnieje", '  rachunek: %d znalezionych' in CIALO)
for co in ("niewidocznych", "naszych", "bez tresci", "poza rewirem",
           "ocenionych", "odmow", "podanych dalej"):
    sprawdz("rachunek podaje: %s" % co, co in CIALO, co)
# ZAWSZE, nie tylko w trybie sprawdzenia — inaczej produkcja nadal milczy.
# OSTATNIE `if not wyslij:`, nie pierwsze — w tej funkcji sa dwa, a chodzi
# o to koncowe, ktore drukuje „nie klikam — tryb sprawdzenia".
i_rachunek = CIALO.find('print("  rachunek:')
i_sucha = CIALO.rfind("if not wyslij:")
sprawdz("rachunek stoi PRZED koncowa galezia proby suchej",
        0 <= i_rachunek < i_sucha, "%d / %d" % (i_rachunek, i_sucha))

print()
print("=== 4. ZADEN ODSIEW NIE ZOSTAL CICHY ===")
# Kontrdowod po drzewie skladni: szukamy `continue`, po ktorym w tym samym
# bloku nie ma zadnego `print`. Napis by tu nie wystarczyl — komentarze
# w tym pliku same zawieraja slowo `continue`.
#
# DWA MIEJSCA SA WYLACZONE I OBA Z POWODU.
#
# 1. PETLA WYBORU KANDYDATA. Ona tylko SZUKA pierwszej notki, ktorej jeszcze
#    nie obsluzylismy. Przewijanie listy nie jest decyzja o niczyjej notce
#    i nie ma czego zglaszac; odsiewy zaczynaja sie po wybraniu kandydata.
# 2. GALAZ PROBY SUCHEJ. `if not wyslij: continue` stoi TUZ POD wydrukowana
#    decyzja („RESTACK u …") i znaczy tylko tyle, ze nie klikamy.
drzewo = ast.parse(CIALO)


def _wnetrza(wezel):
    """Wszystkie `continue` lezace WEWNATRZ tego wezla."""
    return {id(w) for w in ast.walk(wezel) if isinstance(w, ast.Continue)}


wyjete = set()
for wezel in ast.walk(drzewo):
    zrzut = ast.dump(wezel)
    if isinstance(wezel, ast.For) and "zrobione_odciski" in zrzut             and "odcisk_kandydata" in zrzut:
        wyjete |= _wnetrza(wezel)
    if isinstance(wezel, ast.If) and "wyslij" in ast.dump(wezel.test):
        wyjete |= _wnetrza(wezel)

ciche = 0
for wezel in ast.walk(drzewo):
    for pole in ("body", "orelse", "finalbody"):
        blok = getattr(wezel, pole, None)
        if not isinstance(blok, list):
            continue
        for nr, krok in enumerate(blok):
            if not isinstance(krok, ast.Continue) or id(krok) in wyjete:
                continue
            mowi = any(isinstance(x, ast.Expr) and isinstance(x.value, ast.Call)
                       and isinstance(x.value.func, ast.Name)
                       and x.value.func.id == "print"
                       for x in blok[:nr])
            if not mowi:
                ciche += 1
sprawdz("nie ma `continue` bez slowa wyjasnienia", ciche == 0, ciche)
# KONTRDOWOD DLA SAMEGO WYKRYWACZA: gdyby wylaczenia byly za szerokie,
# nie zlapalby juz niczego. Sprawdzamy go na probce z cichym odpadem.
PROBKA = """
def f(xs):
    for x in xs:
        if not x:
            continue
        print("mam")
"""
_ciche_probki = 0
for _w in ast.walk(ast.parse(PROBKA)):
    for _p in ("body", "orelse"):
        _b = getattr(_w, _p, None)
        if not isinstance(_b, list):
            continue
        for _n, _k in enumerate(_b):
            if isinstance(_k, ast.Continue) and not any(
                    isinstance(x, ast.Expr) and isinstance(x.value, ast.Call)
                    and isinstance(x.value.func, ast.Name)
                    and x.value.func.id == "print" for x in _b[:_n]):
                _ciche_probki += 1
sprawdz("wykrywacz nadal lapie cichy odpad na probce", _ciche_probki == 1,
        _ciche_probki)

print()
print("=== 5. NIC INNEGO NIE ZOSTALO PRZY OKAZJI RUSZONE ===")
sprawdz("odstep nadal PRZED kolejnym restackiem",
        'if wynik["restackowane"]:' in CIALO)
sprawdz("norma nadal przerywa petle",
        'wynik["restackowane"] < ile' in CIALO
        or 'wynik["restackowane"] >= ile' in CIALO)
# PO RESTACKU LISTA JEST POBIERANA OD NOWA — patrz pomiar w naglowku pliku.
sprawdz("lista pobierana od nowa po kazdym obrocie",
        "przyciski.count()" in CIALO.split("zrobione_odciski")[1][:900]
        if "zrobione_odciski" in CIALO else False)
sprawdz("obsluzonych poznajemy po odcisku tresci, nie po numerze",
        "zrobione_odciski.add(" in CIALO)
sprawdz("i petla ma wlasny sufit obrotow", "MAKS_OBROTOW" in CIALO)
sprawdz("odmowa modelu nadal zapisywana", 'wynik["odmowy"].append' in CIALO)
sprawdz("porazka nadal idzie do dziennika",
        'zapisz_w_dzienniku("restack", udane=False' in CIALO)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
