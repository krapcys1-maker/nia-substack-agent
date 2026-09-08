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
  - PUSTKI NIE ZAPAMIETUJEMY w pamieci procesu; osobny zapas dyskowy
    respektuje przerwe po bledzie HTTP i ponawia pobranie po jej uplywie;
  - zapas ma TERMIN — proces dnia trwa ponad godzine i nie ma patrzec na
    kanaly sprzed calego cyklu.

KONTRDOWOD. Sprawdzenie drugie pokazuje, ze bez waznego zapasu siec JEST
dotykana — inaczej caly plik przechodzilby rowniez wtedy, gdyby zapas nie
dzialal, a `korpus_kanalow` po prostu nic nie robil.

BEZ PYTESTA. Uruchamiac z korzenia repozytorium.
"""
import sys
import types
import tempfile
from pathlib import Path
from unittest.mock import patch
from httpx import Timeout

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
_atrapa.Timeout = Timeout
sys.modules["httpx"] = _atrapa

# Wpisy udajace przetworzony korpus. Ksztalt jak z `przetworz`.
FALSZYWE = [{"temat": "topic number %d about model training" % i,
             "surowy": "TOPIC %d" % i, "kanal": "kanal%d" % (i % 3),
             "kiedy": "2026-08-30"} for i in range(40)]


def _ustaw_zapas(kiedy):
    korpus_kanalow._ZAPAS["wpisy"] = list(FALSZYWE)
    korpus_kanalow._ZAPAS["kiedy"] = kiedy
    korpus_kanalow._ZAPAS["key"] = korpus_kanalow._cache_key()


# KANALY SA ATRAPA, NIE PRODUKCYJNE. Ten test mierzy WAZNOSC ZAPASU: ile razy
# kod siega do sieci przy zapasie swiezym, pustym i przeterminowanym. Liczba
# zapytan rowna sie liczbie kanalow, wiec przy pustym `KANALY` w konfiguracji
# wychodzila zawsze zero i dwie sekcje oblewaly sie z powodu KONFIGURACJI,
# a nie kodu. Test podstawia wiec wlasne kanaly i oddaje produkcyjne na koniec.
_KANALY_PRODUKCYJNE = dict(korpus_kanalow.config.KANALY_YOUTUBE)
_DANE_PRODUKCYJNE = korpus_kanalow.config.DATA_DIR
_DANE_TESTU = tempfile.TemporaryDirectory()
korpus_kanalow.config.DATA_DIR = Path(_DANE_TESTU.name)
korpus_kanalow.config.KANALY_YOUTUBE.clear()
korpus_kanalow.config.KANALY_YOUTUBE.update({
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
sprawdz("odpytal kazdy kanal", siegniecia["ile"] == len(korpus_kanalow.config.KANALY_YOUTUBE),
        "%d zapytan przy %d kanalach"
        % (siegniecia["ile"], len(korpus_kanalow.config.KANALY_YOUTUBE)))

print()
print("=== 4. PRZETERMINOWANY ZAPAS NIE JEST UZYWANY ===")
siegniecia["ile"] = 0
_ustaw_zapas(time.time() - korpus_kanalow.ZAPAS_WAZNY_S - 60)
# Pierwszy blad wyznaczyl 5 minut przerwy; uplyw TTL oznacza tez jej koniec.
pozniej = time.time() + korpus_kanalow.ZAPAS_WAZNY_S + 60
with patch('feed_cache.time.time', return_value=pozniej):
    korpus_kanalow.korpus_kanalow(5)
sprawdz("stary zapas pominiety, siec dotknieta", siegniecia["ile"] > 0,
        siegniecia["ile"])

print()
print("=== 5. PUSTKI NIE ZAPAMIETUJEMY ===")
# Pusta lista nie zastepuje korpusu. Ponowne HTTP respektuje jednak backoff,
# zeby kolejne etapy nie odpytywaly tego samego niedzialajacego serwera.
korpus_kanalow._ZAPAS["wpisy"] = None
korpus_kanalow._ZAPAS["kiedy"] = 0.0
korpus_kanalow.korpus_kanalow(5)
sprawdz("pusty wynik nie trafil do zapasu",
        korpus_kanalow._ZAPAS["wpisy"] is None,
        korpus_kanalow._ZAPAS["wpisy"])
siegniecia["ile"] = 0
korpus_kanalow.korpus_kanalow(5)
sprawdz("kolejne wywolanie respektuje przerwe po HTTP 404", siegniecia["ile"] == 0,
        siegniecia["ile"])
with patch('feed_cache.time.time', return_value=pozniej + 3600):
    korpus_kanalow.korpus_kanalow(5)
sprawdz("po przerwie znowu probuje kazdego kanalu",
        siegniecia["ile"] == len(korpus_kanalow.config.KANALY_YOUTUBE), siegniecia["ile"])

print()
print("=== 6. TERMIN JEST ROZSADNY ===")
sprawdz("zapas wazny miedzy 5 a 60 minut",
        300 <= korpus_kanalow.ZAPAS_WAZNY_S <= 3600,
        korpus_kanalow.ZAPAS_WAZNY_S)

print()
korpus_kanalow.config.KANALY_YOUTUBE.clear()
korpus_kanalow.config.KANALY_YOUTUBE.update(_KANALY_PRODUKCYJNE)
korpus_kanalow.config.DATA_DIR = _DANE_PRODUKCYJNE
_DANE_TESTU.cleanup()

print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
