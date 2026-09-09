# -*- coding: utf-8 -*-
"""Pominiecie po rozmiarze konta nie moze kosztowac przerwy, proby ani przebiegu.

## Po co ten plik istnieje

Przebieg dnia 8 wrzesnia 2026 trwal 116 minut i zrobil JEDNA notke oraz JEDEN
komentarz. Restacki — norma cztery na dobe — nie wyszly wcale, bo przebieg do
nich nie dotarl. Czas poszedl na piec podejsc do subskrypcji, z ktorych kazde
konczylo sie tym samym zdaniem: „account exceeds the size limit or its size is
unknown". Kazde placilo najpierw PELNA przerwe rytmu i zuzywalo jeden z
czterech dziennych slotow — okolo szescdziesieciu pieciu minut na odczytanie
publicznej liczby.

## I co ta poprawka zepsula, zanim zadzialala

Pierwsza wersja sita wolala `podlacz_sie()`, czyli startowala Playwrighta DRUGI
RAZ w procesie, ktory juz go mial. Noc z 8 na 9 wrzesnia:

    [subskrypcje] nie sprawdzilem rozmiaru @addyo (Error)
    [subskrypcje] blok padl: Playwright Sync API inside the asyncio loop
    [komentarze]  blok padl: to samo
    [dyskusje]    blok padl: to samo

Dzien zamknal sie z jedna notka, ZEREM komentarzy i ZEREM restackow. `except`
zlapal pierwszy blad i przebieg poszedl dalej, wiec z zewnatrz wygladalo to na
drobiazg — a proces byl juz nie do uratowania. Sito, ktore mialo oszczedzic
kwadrans, kosztowalo caly wieczor.

## Trzy reguly, ktorych pilnuje ten plik

1. Sufit sprawdzamy PRZED przerwa, nie po niej.
2. Sito idzie ZWYKLYM HTTP i nie ma prawa dotknac przegladarki.
3. Straznik przy samym przycisku zostaje — tanie sito wolno pomylic w strone
   „wpusc", ostatnie slowo ma ten przy przycisku.

BEZ PYTESTA, bez sieci, bez przegladarki. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_pominiecie_bez_kosztu.py
"""
import json
import re
import sys
import urllib.error
import urllib.request

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


class _Odpowiedz:
    """Atrapa `urlopen` — obiekt kontekstowy z metoda `read`, jak prawdziwy."""

    def __init__(self, dane):
        self._dane = dane

    def read(self):
        return json.dumps(self._dane).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


# POLA TAKIE, JAKIE CZYTA `personality.small_account`: `subscriberCountNumber`
# i `followerCount`. Zmyslone `subscriberCount` przechodziloby jako „rozmiar
# nieznany", czyli test zdawalby z niewlasciwego powodu.
DUZE = {"subscriberCountNumber": 50000}
MALE = {"subscriberCountNumber": 12}
DUZE_PO_OBSERWUJACYCH = {"followerCount": 44537}

stary_limit = config.SUBSKRYPCJE_MAX_ODBIORCOW
stary_urlopen = urllib.request.urlopen

print("=== 1. BEZ SUFITU NIC NIE ODSIEWAMY ===")
config.SUBSKRYPCJE_MAX_ODBIORCOW = None
sprawdz("brak limitu = nie za duze", browser.konto_za_duze("ktokolwiek") is False)

print()
print("=== 2. Z SUFITEM ROZSTRZYGA ROZMIAR ===")
config.SUBSKRYPCJE_MAX_ODBIORCOW = 1000
urllib.request.urlopen = lambda *a, **k: _Odpowiedz(DUZE)
sprawdz("konto ponad sufitem odsiane", browser.konto_za_duze("gigant") is True)
urllib.request.urlopen = lambda *a, **k: _Odpowiedz(DUZE_PO_OBSERWUJACYCH)
sprawdz("liczy sie takze liczba obserwujacych",
        browser.konto_za_duze("gigant2") is True)
urllib.request.urlopen = lambda *a, **k: _Odpowiedz(MALE)
sprawdz("konto ponizej sufitu przepuszczone", browser.konto_za_duze("maly") is False)

print()
print("=== 3. BRAK PROFILU TO ODPOWIEDZ, AWARIA SIECI TO NIE ===")
# 404 znaczy „pod tym uchwytem nie ma konta o mierzalnym rozmiarze" — straznik
# przy przycisku odrzucilby je z tego samego powodu, wiec nie ma po co tam isc
# i placic za to przerwe. Timeout znaczy tylko tyle, ze nie wiemy — a chwilowa
# awaria sieci nie moze po cichu odsiewac kandydatow.


def _404(*a, **k):
    raise urllib.error.HTTPError("u", 404, "brak", None, None)


def _padnij(*a, **k):
    raise TimeoutError("siec")


urllib.request.urlopen = _404
sprawdz("404 odsiewa", browser.konto_za_duze("kogo-nie-ma") is True)
urllib.request.urlopen = _padnij
sprawdz("timeout PRZEPUSZCZA do straznika",
        browser.konto_za_duze("chwilowy-blad") is False)

urllib.request.urlopen = stary_urlopen
config.SUBSKRYPCJE_MAX_ODBIORCOW = stary_limit

print()
print("=== 4. SITO NIE MA PRAWA DOTKNAC PRZEGLADARKI ===")
# To jest ta sekcja, ktorej brak kosztowal komentarze i restacki jednej nocy.
zrodlo_b = open("agent-v2/browser.py", encoding="utf-8").read()
cialo = zrodlo_b.split("def konto_za_duze")[1].split("def _klik_na_profilu")[0]
kod = [l for l in cialo.splitlines() if l.strip() and not l.strip().startswith("#")]
kod = " ".join(kod)
sprawdz("zero wywolan podlacz_sie()", not re.search(r"podlacz_sie\s*\(", kod),
        "sito znowu startuje Playwrighta")
sprawdz("zero wywolan api_json()", not re.search(r"api_json\s*\(", kod),
        "api_json chodzi przez strone przegladarki")
sprawdz("idzie zwyklym HTTP", "urlopen" in kod, kod[:90])

print()
print("=== 5. SPRAWDZENIE STOI PRZED PRZERWA, NIE PO NIEJ ===")
# Gdyby ktos przestawil te dwie linie z powrotem, wszystkie testy wyzej nadal
# przechodzilyby, a przebieg znowu placilby kwadrans za publiczna liczbe.
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
print("=== 6. STRAZNIK PRZY PRZYCISKU ZOSTAJE ===")
# Tanie sito nie zastepuje ostatniego slowa. Gdyby ktos usunal straznika,
# jeden blad sieci wystarczylby, zeby zasubskrybowac konto z limitu.
sprawdz("straznik nadal czyta rozmiar przy przycisku",
        "exceeds the size limit" in zrodlo_b
        and zrodlo_b.count("small_account(") >= 2,
        "wystapien small_account: %d" % zrodlo_b.count("small_account("))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
