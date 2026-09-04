# -*- coding: utf-8 -*-
"""Wyciaganie JSON-a z odpowiedzi modelu — i jedna decyzja, ktora jest OTWARTA.

## Po co ten plik istnieje

`llm.parse_json` miala DRUGA PETLE, ktora nie mogla zwrocic niczego:

    for k in kandydaci:                                  # pierwsza: po kolei
        try: return json.loads(k)
        except ValueError: continue
    for k in sorted(kandydaci, key=len, reverse=True):    # druga: to samo,
        try: return json.loads(k)                         # inna kolejnosc
        except ValueError: continue

Do drugiej dochodzi sie wylacznie wtedy, gdy ZADEN kandydat sie nie sparsowal —
a wtedy przesortowanie tej samej listy nie zmienia niczego. Kod wygladal jak
zabezpieczenie i nie byl nim ani razu.

## Decyzja, ktorej ten plik NIE podejmuje

Komentarz przy martwej petli opisywal zachowanie, ktorego kod nie ma:
„krotkie obiekty na poczatku bywaja fragmentem instrukcji, ktory model
przepisal" — czyli argument za braniem NAJDLUZSZEGO. Kod bierze PIERWSZY.

Roznica ujawnia sie tylko wtedy, gdy parsuja sie DWA obiekty, a wtedy istnieje
przypadek przeciwny: poprawna odpowiedz, po ktorej idzie dluzszy blok
przykladu. Ktory zdarza sie czesciej, rozstrzyga pomiar na prawdziwych
odpowiedziach modelu — nie przeczucie. Ten plik PRZYPINA dzisiejsze zachowanie,
zeby zmiana nie przeszla po cichu, i nazywa je otwartym pytaniem.

## Czego pilnuje

1. Obiekt otoczony proza wychodzi caly.
2. Nawias w prozie NIE przesuwa granicy — to jest wada, dla ktorej cale to
   liczenie nawiasow powstalo (`Extra data: line 1 column 1866`).
3. Pierwszy NIEPOPRAWNY obiekt nie kasuje poprawnego, ktory stoi za nim.
4. Blok ```json``` sie zdejmuje.
5. Brak JSON-a to `ValueError`, a nie None ani pusty slownik — wolajacy ma
   wtedy do wyboru `ratuj_json` albo rezygnacje i obie decyzje naleza do niego.
6. PRZYPIETE, OTWARTE: przy dwoch poprawnych obiektach wygrywa PIERWSZY.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_parse_json.py
"""
import sys

sys.path.insert(0, "agent-v2")
import llm  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


print("=== 1. OBIEKT W PROZIE ===")
sprawdz("proza z obu stron", llm.parse_json('wstep {"a": 1} ogon') == {"a": 1})
sprawdz("sam obiekt", llm.parse_json('{"a": 1}') == {"a": 1})
sprawdz("zagniezdzony wychodzi caly",
        llm.parse_json('x {"a": {"b": [1, 2]}} y') == {"a": {"b": [1, 2]}})

print()
print("=== 2. NAWIAS W PROZIE NIE PRZESUWA GRANICY ===")
# TA WADA KOSZTOWALA DWADZIESCIA WYSZUKIWAN I 0,13 USD. Stary kod bral wycinek
# od PIERWSZEGO `{` do OSTATNIEGO `}`, wiec kazdy nawias w komentarzu modelu
# przesuwal granice i caly etap przepadal.
sprawdz("nawias klamrowy w tekscie po obiekcie",
        llm.parse_json('{"a": 1} a teraz } zostal sam') == {"a": 1})
sprawdz("nawias w NAPISIE wewnatrz obiektu",
        llm.parse_json('{"a": "ma } w srodku"}') == {"a": "ma } w srodku"})
sprawdz("znak ucieczki przed cudzyslowem",
        llm.parse_json(r'{"a": "cudzyslow \" i } klamra"}')
        == {"a": 'cudzyslow " i } klamra'})

print()
print("=== 3. ZEPSUTY OBIEKT NIE KASUJE POPRAWNEGO ZA NIM ===")
sprawdz("pierwszy zepsuty, drugi dobry",
        llm.parse_json('wstep {"zly": } potem {"dobry": 2}') == {"dobry": 2})

print()
print("=== 4. BLOK KODU SIE ZDEJMUJE ===")
sprawdz("```json ... ```",
        llm.parse_json('```json\n{"a": 1}\n```') == {"a": 1})
sprawdz("``` bez nazwy jezyka",
        llm.parse_json('```\n{"a": 1}\n```') == {"a": 1})

print()
print("=== 5. BRAK JSON-A TO WYJATEK, NIE CISZA ===")
for tekst in ("nic tu nie ma", "", "{niedomkniety", '{"zly": }'):
    try:
        wynik = llm.parse_json(tekst)
        sprawdz("%r -> ValueError" % tekst[:24], False, wynik)
    except ValueError:
        sprawdz("%r -> ValueError" % tekst[:24], True)

print()
print("=== 6. PRZYPIETE, ALE OTWARTE: WYGRYWA PIERWSZY, NIE NAJDLUZSZY ===")
# Nie twierdzimy, ze to jest wlasciwy wybor — twierdzimy, ze taki jest DZIS.
# Zmiana na „najdluzszy" ma oblac tutaj i zostac przemyslana, a nie przejsc
# po cichu przy okazji innej poprawki.
_dwa = '{"krotki": 1} i {"dluzszy": {"x": 2, "y": 3}}'
sprawdz("przy dwoch poprawnych wygrywa pierwszy",
        llm.parse_json(_dwa) == {"krotki": 1}, llm.parse_json(_dwa))

print()
print("=== 7. KONTRDOWOD: TEST ROZROZNIA OBIEKTY ===")
# Bez tego sekcja 6 przechodzilaby takze wtedy, gdyby `_obiekty_json` widzialo
# tylko jeden obiekt i pytanie o „pierwszy" nie mialo sensu.
sprawdz("wejscie z sekcji 6 ma DWA zbilansowane obiekty",
        len(list(llm._obiekty_json(_dwa))) == 2,
        list(llm._obiekty_json(_dwa)))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
