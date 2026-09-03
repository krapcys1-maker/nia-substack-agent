# -*- coding: utf-8 -*-
"""Korpus kanalow pobiera sie RAZ na przebieg, nie dwa razy.

DLACZEGO TO POWSTALO. W logu zywego przebiegu 30 sierpnia linia
    [kanaly] 180 filmow z 13 kanalow -> 156 tematow
pojawiala sie DWUKROTNIE, kilkanascie sekund po sobie. Przebieg wola
`korpus_kanalow()` w dwoch miejscach — raz po zaczyn do promptu ciekawostek,
raz po wykrywacz wielkich wydarzen — a kazde wywolanie odpytywalo wszystkie
trzynascie kanalow od nowa. Dwadziescia szesc zapytan HTTP zamiast trzynastu,
za kazdym razem, przy kazdym przebiegu.

CO PILNUJEMY, poza samym zapasem:
  - zapas trzyma PELNA liste, nie przycieta do `ile` — inaczej wywolanie po 26
    tematow zatrulo by pozniejsze wywolanie po 200, ktorego potrzebuje
    wykrywacz wydarzen;
  - PUSTKI NIE ZAPAMIETUJEMY — sieciowa wpadka wyciszylaby kanaly na pol
    godziny, a prompt dostalby „(nothing fetched today)" mimo dzialajacej sieci;
  - zapas ma TERMIN — proces dnia trwa ponad godzine i nie ma patrzec na
    kanaly sprzed calego cyklu.

KONTRDOWOD. Sprawdzenie drugie pokazuje, ze bez waznego zapasu siec JEST
dotykana — inaczej caly plik przechodzilby rowniez wtedy, gdyby zapas nie
dzialal, a `korpus_kanalow` po prostu nic nie robil.

BEZ PYTESTA. Uruchamiac z korzenia repozytorium.
"""
import sys
import types

sys.path.insert(0, "agent-v2")
import korpus_kanalow   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# --- atrapa sieci, ktora LICZY dotkniecia ------------------------------------
siegniecia = {"ile": 0}


class _Odpowiedz:
    status_code = 404
    content = b""


class _Klient:
    def __init__(self, **kw):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get(self, *a, **kw):
        siegniecia["ile"] += 1
        return _Odpowiedz()


_atrapa = types.ModuleType("httpx")
_atrapa.Client = _Klient
sys.modules["httpx"] = _atrapa

# Wpisy udajace przetworzony korpus. Ksztalt jak z `przetworz`.
FALSZYWE = [{"temat": "topic number %d about model training" % i,
             "surowy": "TOPIC %d" % i, "kanal": "kanal%d" % (i % 3),
             "kiedy": "2026-08-30"} for i in range(40)]


def _ustaw_zapas(kiedy):
    korpus_kanalow._ZAPAS["wpisy"] = list(FALSZYWE)
    korpus_kanalow._ZAPAS["kiedy"] = kiedy


# KANALY SA ATRAPA, NIE PRODUKCYJNE. Ten test mierzy WAZNOSC ZAPASU: ile razy
# kod siega do sieci przy zapasie swiezym, pustym i przeterminowanym. Liczba
# zapytan rowna sie liczbie kanalow, wiec przy pustym `KANALY` w konfiguracji
# wychodzila zawsze zero i dwie sekcje oblewaly sie z powodu KONFIGURACJI,
# a nie kodu. Test podstawia wiec wlasne kanaly i oddaje produkcyjne na koniec.
_KANALY_PRODUKCYJNE = dict(korpus_kanalow.KANALY)
korpus_kanalow.KANALY.clear()
korpus_kanalow.KANALY.update({
    "Atrapa A": "UC00000000000000000000A",
    "Atrapa B": "UC00000000000000000000B",
})

print("=== 1. WAZNY ZAPAS NIE DOTYKA SIECI ===")
import time   # noqa: E402

siegniecia["ile"] = 0
_ustaw_zapas(time.time())
wynik = korpus_kanalow.korpus_kanalow(5)
sprawdz("zero zapytan HTTP", siegniecia["ile"] == 0, siegniecia["ile"])
sprawdz("oddaje z zapasu", [w["temat"] for w in wynik]
        == [w["temat"] for w in FALSZYWE[:5]])
sprawdz("i tnie do zadanej liczby", len(wynik) == 5, len(wynik))

print()
print("=== 2. ZAPAS TRZYMA PELNA LISTE, NIE PRZYCIETA ===")
# To jest wada, ktora zapas latwo wprowadza: pierwsze wywolanie po 26 tematow
# zapisuje 26, a wykrywacz wydarzen prosi pozniej o 200 i dostaje 26.
siegniecia["ile"] = 0
_ustaw_zapas(time.time())
korpus_kanalow.korpus_kanalow(5)
drugie = korpus_kanalow.korpus_kanalow(40)
sprawdz("po wzieciu 5 nadal mozna wziac 40", len(drugie) == 40, len(drugie))
sprawdz("nadal bez sieci", siegniecia["ile"] == 0, siegniecia["ile"])

print()
print("=== 3. KONTRDOWOD: BEZ WAZNEGO ZAPASU SIEC JEST DOTYKANA ===")
siegniecia["ile"] = 0
korpus_kanalow._ZAPAS["wpisy"] = None
korpus_kanalow._ZAPAS["kiedy"] = 0.0
korpus_kanalow.korpus_kanalow(5)
sprawdz("odpytal kazdy kanal", siegniecia["ile"] == len(korpus_kanalow.KANALY),
        "%d zapytan przy %d kanalach"
        % (siegniecia["ile"], len(korpus_kanalow.KANALY)))

print()
print("=== 4. PRZETERMINOWANY ZAPAS NIE JEST UZYWANY ===")
siegniecia["ile"] = 0
_ustaw_zapas(time.time() - korpus_kanalow.ZAPAS_WAZNY_S - 60)
korpus_kanalow.korpus_kanalow(5)
sprawdz("stary zapas pominiety, siec dotknieta", siegniecia["ile"] > 0,
        siegniecia["ile"])

print()
print("=== 5. PUSTKI NIE ZAPAMIETUJEMY ===")
# Wszystkie kanaly oddaja 404, wiec `przetworz` da pusta liste. Gdyby zapas
# zapisal pustke, nastepne wywolanie oddaloby zero BEZ proby pobrania — i
# kanaly milczalyby przez pol godziny mimo dzialajacej sieci.
korpus_kanalow._ZAPAS["wpisy"] = None
korpus_kanalow._ZAPAS["kiedy"] = 0.0
korpus_kanalow.korpus_kanalow(5)
sprawdz("pusty wynik nie trafil do zapasu",
        korpus_kanalow._ZAPAS["wpisy"] is None,
        korpus_kanalow._ZAPAS["wpisy"])
siegniecia["ile"] = 0
korpus_kanalow.korpus_kanalow(5)
sprawdz("wiec nastepne wywolanie znowu probuje", siegniecia["ile"] > 0,
        siegniecia["ile"])

print()
print("=== 6. TERMIN JEST ROZSADNY ===")
sprawdz("zapas wazny miedzy 5 a 60 minut",
        300 <= korpus_kanalow.ZAPAS_WAZNY_S <= 3600,
        korpus_kanalow.ZAPAS_WAZNY_S)

print()
korpus_kanalow.KANALY.clear()
korpus_kanalow.KANALY.update(_KANALY_PRODUKCYJNE)

print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
