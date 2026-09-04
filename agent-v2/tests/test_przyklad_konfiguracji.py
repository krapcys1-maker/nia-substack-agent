# -*- coding: utf-8 -*-
"""Pole, ktorego nie ma w pliku przykladowym, nie zostanie ustawione nigdy.

## Po co ten plik istnieje

`konfiguracja.POLA` jest zamknieta lista pol, a `konfiguracja.example.toml`
jest tym, co czlowiek kopiuje i edytuje. Rozjechanie sie tych dwoch rzeczy nie
daje zadnego bledu: plik konfiguracyjny jest opcjonalny i kazde pole z osobna
tez, wiec brakujace pole to po prostu wartosc domyslna. Pole istnieje w kodzie,
jest walidowane, ma podpowiedz w kreatorze — i nikt go nigdy nie poda, bo nie
widzial, ze mozna.

Zmierzone 2026-09-04, po dopisaniu trzech pol: `temat.kat_redakcyjny`,
`temat.puste_slowa` i `temat.przyklady` byly w `POLA`, w `config.py`
i w `narzedzia/kreator.py`, a w pliku przykladowym nie bylo zadnego z nich.
Dwa z nich powstaly wlasnie po to, zeby naprawic prompty wpisane na sztywno —
czyli poprawka byla kompletna wszedzie poza jedynym miejscem, do ktorego
zaglada uzytkownik.

## Czego ten test NIE robi

Nie sprawdza WARTOSCI w przykladzie. Przyklad ma byc czytelny, nie poprawny
dla czyjegos konta; jego wartosci sa celowo neutralne. Sprawdzamy wylacznie
OBECNOSC klucza i to, ze caly plik wczytuje sie bez bledu — bo przyklad,
ktorego loader nie przyjmuje, jest gorszy niz brak przykladu.

Nie sprawdza tez kierunku odwrotnego z rownym rygorem: klucz w przykladzie,
ktorego nie ma w `POLA`, loader i tak odrzuci glosno przy pierwszym
uruchomieniu. Mimo to sprawdzamy i to, bo „glosno przy pierwszym uruchomieniu"
znaczy „u kogos innego, nie u nas".

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_przyklad_konfiguracji.py
"""
import pathlib
import sys

sys.path.insert(0, "agent-v2/tests")
import wlasna_konfiguracja  # noqa: E402
wlasna_konfiguracja.pomin_gdy_bez_tomllib(
    "czy plik przykladowy ma komplet pol")

import tomllib

sys.path.insert(0, "agent-v2")
import konfiguracja      # noqa: E402

PRZYKLAD = pathlib.Path("konfiguracja.example.toml")

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


def splaszcz(drzewo: dict, przedrostek: str = "") -> dict:
    """`{"temat": {"nisza": ...}}` na `{"temat.nisza": ...}`.

    Zatrzymuje sie na pierwszym poziomie, ktory `POLA` uznaje za pole. Bez tego
    `temat.przyklady` — ktore JEST polem i jest tablica — rozsypaloby sie na
    `temat.przyklady.kanon` i piec kluczy nie do rozpoznania.
    """
    plaskie = {}
    for klucz, wartosc in drzewo.items():
        sciezka = "%s.%s" % (przedrostek, klucz) if przedrostek else klucz
        if isinstance(wartosc, dict) and sciezka not in konfiguracja.POLA:
            plaskie.update(splaszcz(wartosc, sciezka))
        else:
            plaskie[sciezka] = wartosc
    return plaskie


print("=== PLIK PRZYKLADOWY POKRYWA LISTE POL ===")

sprawdz("konfiguracja.example.toml istnieje", PRZYKLAD.exists())
if not PRZYKLAD.exists():
    raise SystemExit(1)

surowe = PRZYKLAD.read_text(encoding="utf-8")

try:
    drzewo = tomllib.loads(surowe)
    zle_toml = ""
except tomllib.TOMLDecodeError as exc:
    drzewo, zle_toml = {}, str(exc)
sprawdz("przyklad jest poprawnym TOML-em", not zle_toml, zle_toml)

plaskie = splaszcz(drzewo)

brakuje = sorted(set(konfiguracja.POLA) - set(plaskie))
sprawdz("kazde pole z POLA stoi w przykladzie", not brakuje,
        "brakuje: %s" % ", ".join(brakuje))

nadmiar = sorted(set(plaskie) - set(konfiguracja.POLA))
sprawdz("przyklad nie ma pol spoza POLA", not nadmiar,
        "nieznane: %s" % ", ".join(nadmiar))

# Kazda wartosc przechodzi przez TEN SAM walidator, ktorego uzyje loader.
# Przyklad, ktory sie nie waliduje, jest pulapka zastawiona na nowa osobe:
# skopiowala plik dokladnie tak, jak kazano, i dostala blad konfiguracji.
zle = []
for sciezka, wartosc in sorted(plaskie.items()):
    if sciezka not in konfiguracja.POLA:
        continue
    _, walidator = konfiguracja.POLA[sciezka]
    try:
        walidator(wartosc, sciezka)
    except konfiguracja.BledKonfiguracji as exc:
        zle.append(str(exc))
sprawdz("kazda wartosc w przykladzie przechodzi walidacje", not zle,
        "; ".join(zle[:3]))

# --- KONTRDOWOD -----------------------------------------------------------
# Test, ktory tylko przeglada obecne pola, wyglada tak samo jak test, ktory
# nie sprawdza niczego. Zmyslamy wiec pole, ktorego w przykladzie NIE MA,
# i zadamy, zeby ta sama logika je zglosila.
print()
print("=== KONTRDOWOD: wykrywa brak, ktorego nie ma naprawde ===")
udawane = dict(konfiguracja.POLA)
udawane["temat.pole_ktorego_nie_ma"] = ("NIC", lambda v, g: v)
brak_udawany = sorted(set(udawane) - set(plaskie))
sprawdz("brakujace pole zostaje zauwazone",
        brak_udawany == ["temat.pole_ktorego_nie_ma"], brak_udawany)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
