# -*- coding: utf-8 -*-
"""Wylaczona kontrola faktow ma znaczyc „publikuj bez sprawdzania", nie „nie publikuj".

## Po co ten plik istnieje

Wlasciciel wylaczyl kontrole faktow artykulu po przeczytaniu artykulu 0014
(8 wrzesnia 2026). Powod byl rzeczowy: kontrola zglosila osiem twierdzen do
poprawy, a przy okazji przepuscila zla date wydania poprawki mcp-shell —
i placilo sie za nia plaskim tekstem, bo zgloszone zdania przepisywal potem
najtanszy model we flocie.

## Dwie pulapki, ktorych pilnuje ten test

PIERWSZA: samo wyciecie kontroli daje ZERO ARTYKULOW, nie artykuly
niesprawdzone. `artykul_z_puli` (~1537) odklada artykul bez publikacji, gdy
`safe_to_post` jest falszywe — a bez kontroli nikt tego pola nie ustawia na
prawde. Wylacznik musi wiec oddac `safe_to_post: True`, inaczej wlasciciel
dostaje odwrotnosc tego, o co prosil.

DRUGA: stala musi stac PRZED `_aktywacja_przy_starcie()` w `config`. Pierwsza
wersja miala ja 130 linii NIZEJ — preset ustawiał `False`, a przypisanie
domyslne nadpisywalo to z powrotem na `True` i pole bylo martwe. Zmierzone:
`config.SPRAWDZAJ_FAKTY` oddawal `True` przy `false` w presecie.

Audyt zapisuje `bez_kontroli`, zeby za pol roku nie dalo sie pomylic artykulu
BEZ ZARZUTOW z artykulem, ktorego nikt nie badal.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_wylacznik_kontroli_faktow.py
"""
import sys

sys.path.insert(0, "agent-v2")
import config   # noqa: E402
import stages   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


DRAFT = {"body": "Zdanie autorki, ktorego nikt nie ma prawa tknac.", "title": "T"}
stary = config.SPRAWDZAJ_FAKTY

print("=== 1. WYLACZONA: ARTYKUL WYCHODZI, TEKST NIETKNIETY ===")
config.SPRAWDZAJ_FAKTY = False
d, a = stages.przygotuj_artykul_do_publikacji(None, 1, dict(DRAFT), {}, {})
sprawdz("safe_to_post JEST prawda", a.get("safe_to_post") is True, str(a)[:90])
sprawdz("tekst nietkniety", d["body"] == DRAFT["body"], d["body"][:60])
sprawdz("zero zarzutow", a.get("zarzuty") == [], str(a.get("zarzuty"))[:60])

print()
print("=== 2. BRAK KONTROLI JEST ZAPISANY, NIE PRZEMILCZANY ===")
# Artykul bez zarzutow i artykul niesprawdzony wygladaja w bazie tak samo,
# jesli tego nie zapiszemy. Za pol roku nikt tego nie odtworzy.
sprawdz("audyt mowi `bez_kontroli`", a.get("bez_kontroli") is True, str(a)[:90])
sprawdz("i podaje powod", "wylaczona w kartridzu" in str(a.get("powod") or ""),
        str(a.get("powod"))[:80])

print()
print("=== 3. STALA STOI PRZED AKTYWACJA PRESETU ===")
# Cala poprawka. Ponizej aktywacji pole jest martwe: preset ustawia False,
# a przypisanie domyslne nadpisuje je z powrotem na True.
zrodlo = open("agent-v2/config.py", encoding="utf-8").read()
poz_stala = zrodlo.find("\nSPRAWDZAJ_FAKTY = True")
poz_akt = zrodlo.find("_aktywacja = _aktywacja_przy_starcie()")
sprawdz("stala istnieje", poz_stala >= 0)
sprawdz("aktywacja istnieje", poz_akt >= 0)
sprawdz("STALA PRZED AKTYWACJA", 0 <= poz_stala < poz_akt,
        "stala %d, aktywacja %d" % (poz_stala, poz_akt))

print()
print("=== 4. WLACZONA: NIC SIE NIE ZMIENIA ===")
# Kazdy preset, ktory tego nie przestawi, ma miec kontrole jak dotad.
config.SPRAWDZAJ_FAKTY = True
zawolane = {}


def _atrapa(conn, run_id, body, title):
    zawolane["tak"] = True
    return {"nie_sprawdzone": True}


stara_weryfikacja = stages.zweryfikuj
stages.zweryfikuj = _atrapa
try:
    stages.przygotuj_artykul_do_publikacji(None, 1, dict(DRAFT), {}, {})
finally:
    stages.zweryfikuj = stara_weryfikacja
sprawdz("kontrola zostala wolana", zawolane.get("tak") is True)

print()
print("=== 5. DOMYSLNIE WLACZONA W SILNIKU ===")
# Wylaczenie jest decyzja WLASCICIELA publikacji i ma byc widoczne w jego
# presecie, a nie schowane w silniku.
sprawdz("silnik domyslnie sprawdza", "SPRAWDZAJ_FAKTY = True" in zrodlo)

config.SPRAWDZAJ_FAKTY = stary
print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
