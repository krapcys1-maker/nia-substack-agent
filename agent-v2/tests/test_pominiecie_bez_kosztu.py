# -*- coding: utf-8 -*-
"""Pominiecie po rozmiarze konta nie moze kosztowac przerwy ani proby.

## Po co ten plik istnieje

Przebieg dnia 8 wrzesnia 2026 trwal 116 minut i zrobil JEDNA notke oraz JEDEN
komentarz. Restacki — norma cztery na dobe — nie wyszly wcale, bo przebieg do
nich nie dotarl. Czas poszedl na to:

  14:40  subskrypcja POMINIETA   "account exceeds the size limit..."
  14:52  subskrypcja POMINIETA   to samo
  15:07  subskrypcja POMINIETA   to samo
  15:15  subskrypcja NIEUDANA

Kazde pominiecie placilo najpierw PELNA przerwe rytmu (5-15 min, po serii
porazek dwa razy tyle) i zuzywalo jeden z czterech dziennych slotow. Piec
pominiec razy okolo trzynastu minut to okolo szescdziesieciu pieciu minut —
dokladnie tyle, ile zabraklo na restacki.

A rozmiar publicznosci stoi w publicznym JSON-ie `/api/v1/user/<handle>/
public_profile` i kosztuje sekunde. Kolejnosc byla odwrotna do ceny: najpierw
placilismy, potem sprawdzali, czy warto bylo.

## Regula, ktorej pilnuje ten test

Sufit odbiorcow sprawdzamy PRZED przerwa. Pominiete konto nie zuzywa proby,
bo nie weszlismy na zadna strone — odczytalismy publiczna liczbe i odeszlismy.
Straznik przy samym przycisku ZOSTAJE: tanie sito wolno pomylic w strone
„wpusc", ostatnie slowo ma ten przy przycisku.

BEZ PYTESTA, bez sieci, bez przegladarki. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_pominiecie_bez_kosztu.py
"""
import re
import sys

sys.path.insert(0, "agent-v2")
import browser  # noqa: E402
import config   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# POLA TAKIE, JAKIE CZYTA `personality.small_account`: `subscriberCountNumber`
# i `followerCount`. Zmyslone `subscriberCount` przechodziloby jako „rozmiar
# nieznany", czyli test zdawalby z niewlasciwego powodu.
DUZE = {"subscriberCountNumber": 50000}
MALE = {"subscriberCountNumber": 12}

print("=== 1. BEZ SUFITU NIC NIE ODSIEWAMY ===")
stary_limit = config.SUBSKRYPCJE_MAX_ODBIORCOW
config.SUBSKRYPCJE_MAX_ODBIORCOW = None
sprawdz("brak limitu = nie za duze", browser.konto_za_duze("ktokolwiek") is False)

print()
print("=== 2. Z SUFITEM ROZSTRZYGA ROZMIAR ===")
config.SUBSKRYPCJE_MAX_ODBIORCOW = 1000
stary_podlacz, stary_api = browser.podlacz_sie, browser.api_json


class _Strona:
    def close(self):
        pass


class _Kontekst:
    def new_page(self):
        return _Strona()


browser.podlacz_sie = lambda: (None, None, _Kontekst())

browser.api_json = lambda strona, sciezka: DUZE
sprawdz("konto ponad sufitem odsiane", browser.konto_za_duze("gigant") is True)

browser.api_json = lambda strona, sciezka: MALE
sprawdz("konto ponizej sufitu przepuszczone", browser.konto_za_duze("maly") is False)

print()
print("=== 3. AWARIA SITA NIE ZATRZYMUJE BLOKU ===")
# Sito, ktore przy bledzie sieci mowi „za duze", wygasza caly blok subskrypcji
# na cichu. Przy bledzie puszczamy dalej — straznik przy przycisku i tak
# sprawdzi, a tam pomylka kosztuje najwyzej jedna probe.


def _pada(strona, sciezka):
    raise RuntimeError("siec padla")


browser.api_json = _pada
sprawdz("blad sieci = przepuszczamy do straznika",
        browser.konto_za_duze("nieznany") is False)

browser.podlacz_sie, browser.api_json = stary_podlacz, stary_api
config.SUBSKRYPCJE_MAX_ODBIORCOW = stary_limit

print()
print("=== 4. SPRAWDZENIE STOI PRZED PRZERWA, NIE PO NIEJ ===")
# To jest cala poprawka. Gdyby ktos przestawil te dwie linie z powrotem,
# wszystkie testy wyzej nadal przechodzilyby, a przebieg znowu placilby
# kwadrans za odczytanie publicznej liczby.
zrodlo = open("agent-v2/run.py", encoding="utf-8").read()
blok = zrodlo[zrodlo.index("na_teraz[\"subskrypcje\"] + ZAPAS_NA_ODPADY"):]
# KONIEC BLOKU NA WYWOLANIU, NIE NA `proby += 1`. Pierwsza wersja tego testu
# konczyla wycinek na tym drugim — a ten napis pada takze w KOMENTARZU tuz
# nad nim, wiec blok urywal sie przed kodem i wszystkie trzy sprawdzenia
# nizej dawaly -1. Zdawaly tylko dlatego, ze niczego nie znajdowaly.
blok = blok[:blok.index("browser.zasubskrybuj(")]
poz_sito = blok.find("konto_za_duze")
poz_rytm = blok.find('rytm("komentarz", "subskrypcje"')
sprawdz("sito jest w bloku subskrypcji", poz_sito >= 0)
sprawdz("przerwa jest w bloku subskrypcji", poz_rytm >= 0)
sprawdz("SITO PRZED PRZERWA", 0 <= poz_sito < poz_rytm,
        "sito %d, przerwa %d" % (poz_sito, poz_rytm))

print()
print("=== 5. STRAZNIK PRZY PRZYCISKU ZOSTAJE ===")
# Tanie sito nie zastepuje ostatniego slowa. Gdyby ktos usunal straznika,
# jeden blad sieci wystarczylby, zeby zasubskrybowac konto z limitu.
zrodlo_b = open("agent-v2/browser.py", encoding="utf-8").read()
sprawdz("straznik nadal czyta rozmiar przy przycisku",
        "exceeds the size limit" in zrodlo_b
        and zrodlo_b.count("small_account(") >= 2,
        "wystapien small_account: %d" % zrodlo_b.count("small_account("))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
