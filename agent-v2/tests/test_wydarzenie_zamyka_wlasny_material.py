# -*- coding: utf-8 -*-
"""Wydarzenie zamyka material O NIM, nie material o czymkolwiek.

## Wada, ktora ten plik pilnuje

`_zapamietaj_wydarzenia(nowe, znane, ile)` wpisywalo `int(ile)` KAZDEMU
wydarzeniu z listy, a `ile` to bylo `len(fakty)` — laczna liczba faktow
z partii. Dwa wykryte wydarzenia i osiem faktow wylacznie o pierwszym
zamykalo OBA.

Odtworzone: `orion 5.1` i `vega zestaw` obie zapisane z `ile: 8`, obie
przestaly byc nowe, mimo ze o Vedze nie wrocilo nic.

Kosztem jest PRZEGAPIONA PREMIERA. Furtka wydarzen istnieje po to, zeby bot
ruszyl za czyms, o czym mowi kilka kanalow naraz; zamkniecie jej cudzym
materialem znaczy, ze temat przepada bez ANI JEDNEJ proby — a pamiec wygasa
dopiero po `WYDARZENIE_WAZNE_DNI`.

## Czego ten plik pilnuje w DRUGA strone

Zeby dopasowanie nie bylo zbyt luzne. Przy wydarzeniu `["vega", "zestaw"]`
samo slowo „zestaw" pasuje do niemal kazdego faktu z naszej niszy i zamykaloby
furtke tak samo skutecznie jak stary blad — tylko ciszej. Stad wymog DWOCH
slow (albo jednego, gdy wydarzenie ma tylko jedno). Sekcje 2 i 3.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_wydarzenie_zamyka_wlasny_material.py
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import config  # noqa: E402

config.uzyj_katalogu_danych(pathlib.Path(tempfile.mkdtemp()))
import stages  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


def fakt(tresc, dziedzina="przyklad"):
    return {"fact": tresc, "actually": "", "wrong_belief": "",
            "decision": "", "consequence": "", "domain": dziedzina}


ORION = {"o_czym": ["orion", "5.1"], "kanalow": 3, "tytuly": ["Orion 5.1 launch"]}
VEGA = {"o_czym": ["vega", "zestaw"], "kanalow": 2, "tytuly": ["Vega zestaw"]}

print("=== 1. OBCY MATERIAL NIE ZAMYKA WYDARZENIA ===")
fakty = [fakt("Orion 5.1 shipped with a doubled context window.")] * 8
nowe, znane = stages._nowe_wydarzenia([ORION, VEGA])
sprawdz("oba wykryte jako nowe", len(nowe) == 2, len(nowe))
stages._zapamietaj_wydarzenia(nowe, znane, len(fakty), fakty)
nowe2, _ = stages._nowe_wydarzenia([ORION, VEGA])
zostaly = [", ".join(w.get("o_czym") or []) for w in nowe2]
sprawdz("Vega nadal czeka na swoja szanse", "vega, zestaw" in zostaly, zostaly)
sprawdz("a Orion zamkniety", "orion, 5.1" not in zostaly, zostaly)

print()
print("=== 2. WLASNY MATERIAL ZAMYKA ===")
config.uzyj_katalogu_danych(pathlib.Path(tempfile.mkdtemp()))
wlasne = [fakt("The Vega zestaw logs every override it applies.")] * 3
nowe, znane = stages._nowe_wydarzenia([VEGA])
stages._zapamietaj_wydarzenia(nowe, znane, len(wlasne), wlasne)
nowe2, _ = stages._nowe_wydarzenia([VEGA])
sprawdz("po wlasnym materiale przestaje byc nowe", not nowe2, len(nowe2))

print()
print("=== 3. JEDNO WSPOLNE SLOWO TO ZA MALO ===")
# KONTRDOWOD NA POPRAWKE: gdyby wystarczylo jedno trafienie, slowo wspolne calej niszy z niemal
# kazdego naszego faktu zamykalby furtke rownie skutecznie jak stary blad.
config.uzyj_katalogu_danych(pathlib.Path(tempfile.mkdtemp()))
ogolne = [fakt("A zestaw of unrelated items is reviewed yearly.")] * 5
nowe, znane = stages._nowe_wydarzenia([VEGA])
stages._zapamietaj_wydarzenia(nowe, znane, len(ogolne), ogolne)
nowe2, _ = stages._nowe_wydarzenia([VEGA])
sprawdz("samo slowo z niszy nie zamyka", len(nowe2) == 1, len(nowe2))
sprawdz("dopasowanie odrzuca taki fakt",
        not stages._wydarzenie_w_fakcie(VEGA, ogolne[0]))
sprawdz("a przyjmuje fakt z obydwoma slowami",
        stages._wydarzenie_w_fakcie(VEGA, wlasne[0]))

print()
print("=== 4. WYDARZENIE JEDNOSLOWNE POTRZEBUJE JEDNEGO ===")
JEDNO = {"o_czym": ["orion"], "kanalow": 2, "tytuly": ["Orion"]}
sprawdz("jedno slowo wystarcza, gdy wydarzenie ma jedno",
        stages._wydarzenie_w_fakcie(JEDNO, fakt("Orion shipped today.")))
sprawdz("ale obcy fakt nadal odpada",
        not stages._wydarzenie_w_fakcie(JEDNO, fakt("Vega shipped today.")))

print()
print("=== 5. STARY PODPIS NADAL DZIALA ===")
# `_zapamietaj_wydarzenia(..., 0)` na sciezce awaryjnej ma dalej znaczyc
# „nic nie wrocilo" i NIE zamykac furtki.
config.uzyj_katalogu_danych(pathlib.Path(tempfile.mkdtemp()))
nowe, znane = stages._nowe_wydarzenia([ORION])
stages._zapamietaj_wydarzenia(nowe, znane, 0)
nowe2, _ = stages._nowe_wydarzenia([ORION])
sprawdz("zero nie zamyka furtki", len(nowe2) == 1, len(nowe2))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
