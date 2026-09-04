# -*- coding: utf-8 -*-
"""Slowa, ktore w PROMPCIE znacza, ze uczymy modelu innego zawodu.

## Po co jeden plik zamiast dwoch list

Ta lista istniala w dwoch egzemplarzach. `tests/test_prompty_o_niszy.py` mial
sto pozycji i skanowal nimi wszystkie prompty; `audyt_tematow.py` mial WLASNE
osiem slow i skanowal nimi dziedziny ciekawostek. Dwie listy tego samego
rozjezdzaja sie zawsze — a tutaj rozjechaly sie o czynnik dwanascie, wiec
audyt tematow przepuszczal dziedzine, ktora test promptow by zatrzymal.

To jest dokladnie ta wada, ktora ten projekt sciga wszedzie indziej: uchwyt
konta w dwoch stalych, dostawca rozstrzygany w dwoch miejscach, nazwa jezyka
pod dwiema nazwami. Lista slow niczym sie od nich nie rozni.

## Czym ta lista NIE jest

Nie jest lista slow zakazanych w TRESCI. Bot ma prawo napisac o czymkolwiek,
co miesci sie w jego niszy. Chodzi wylacznie o PROMPTY: przyklad w briefie
uczy modelu zawodu skuteczniej niz regula, wiec brief mowiacy „pisz o {nisza}"
i pokazujacy trzy przyklady z innej dziedziny uczy tej innej dziedziny.

Nie jest tez lista tozsamosci. Uchwyty, nazwiska, adresy i identyfikatory
notek mieszkaja w `dawne-tozsamosci.txt`, ktory jest gitignorowany, bo lista
rzeczy, ktorych nie chcesz opublikowac, sama nie moze byc opublikowana.
Tutaj sa POSPOLITE RZECZOWNIKI — „szampon", „konklawe", „autobus szkolny" —
ktore nie wskazuja na nikogo i sluza za dzialajacy przyklad dla kazdego, kto
to repozytorium sforkuje.

## Wlasna epoka

Kazde konto, ktore zmienilo temat, ma swoja liste. Zaloz
`narzedzia/dawne-slownictwo.txt` (jedno haslo w linii, `#` to komentarz) —
jest gitignorowany i DOKLADA sie do tej listy, a nie ja zastepuje. Brak pliku
nie jest bledem: znaczy „to konto nie mialo poprzedniej epoki".
"""
from __future__ import annotations

import pathlib

KATALOG = pathlib.Path(__file__).resolve().parent
PLIK_LOKALNY = KATALOG / "dawne-slownictwo.txt"

# Slownictwo epok, przez ktore przeszlo TO repozytorium. Zostaje w git jako
# dzialajacy przyklad — i dlatego, ze prompty w tym drzewie nadal moglyby je
# odzyskac przy nieuwaznej edycji.
SPRZED_PRZESTAWIENIA: tuple[str, ...] = (
    "petrol station", "school bus", "school-bus", "tuna", "lighthouse",
    "conclave", "papal", "cardinals", "runway", "boil-water", "shampoo",
    "sunscreen", "traffic light", "crew rest", "airliner", "open-jar",
    "cosmetics", "fuel pump", "fuel-pump", "period-after-opening",
    "airline overbooking", "hotel overbooking", "sacrificial anode",
    "crumple zone", "ship's hull", "aircraft window", "vent hole",
    "bridge weight limit", "supermarket",
    # Dopisane 1 wrzesnia. Kazde z nich stalo w KANONICZNYM PRZYKLADZIE do
    # reguly, nie w zakazie: zegar w piekarniku ilustrowal „fakt zywy",
    # posiadacz zezwolenia i strazak ilustrowali obowiazkowe pole
    # `consequence`, karton na polce w drzwiach lodowki byl jedynym wzorcem
    # „momentu czytelnika", a butelka w lazience i swiatlo na skrzyzowaniu
    # byly wzorcem w `NOTE_FORMS`.
    #
    # `clock`, NIE „mains clock". Fraza dwuwyrazowa przepuszczala gole slowo,
    # a to wlasnie gole `clock` stalo w `warto_pisac.md` jako wzorzec dobrej
    # paraleli. Fraza byla podzbiorem tego slowa, wiec nic nie tracimy.
    "oven", "clock", "your ticket", "call-out", "permit holder",
    "firefighter", "carton", "shelf", "bottle", "junction", "faa",
    # Dopisane 1 wrzesnia wieczorem, po niezaleznym odczycie kodu.
    # TE NIE SA RZECZOWNIKAMI, tylko FRAZAMI RAMUJACYMI — i wlasnie dlatego
    # przelezly przez liste zbudowana ze slownictwa przedmiotow. Nie byly
    # nieaktualnym komentarzem: `synteza.md` definiowala przez „hidden system"
    # pole `main_mechanism`, ktore idzie do promptu pisarza przy KAZDYM
    # artykule, a `ciekawostki.md` i `fedreg.md` kazaly modelowi klasyfikowac
    # kazdy fakt do „everyday area". Instrukcja z poprzedniej epoki dzialala
    # wiec dalej, a test swiecil na zielono.
    "hidden system", "everyday area", "everyday object", "ordinary object",
    # Dopisane po RECZNYM przeczytaniu `pisarz.md` od gory do dolu. Ta lista
    # zbudowana byla ze slow, ktore ZAPAMIETANO z usuwania — wiec przepuszczala
    # to, czego nikt nie usuwal. „SPF" stalo w kanonicznym przykladzie dobrego
    # pierwszego zdania akapitu o ograniczeniach, czyli w miejscu, ktore model
    # czyta przy KAZDYM artykule, a test swiecil na zielono.
    "spf", "sunscreen bottle", "system card", "held-out set",
    "training data", "stochastic parrot", "context window", "chatbot",
)


def wczytaj_lokalne() -> tuple[str, ...]:
    """Slownictwo poprzedniej epoki TEGO konta, jesli operator je podal.

    Brak pliku nie jest bledem — znaczy „nie bylo poprzedniej epoki".
    """
    if not PLIK_LOKALNY.exists():
        return ()
    hasla = []
    for linia in PLIK_LOKALNY.read_text(encoding="utf-8").splitlines():
        linia = linia.strip()
        if linia and not linia.startswith("#"):
            hasla.append(linia.lower())
    return tuple(hasla)


def wszystkie() -> tuple[str, ...]:
    """Lista wbudowana PLUS lokalna, bez powtorzen, w stalej kolejnosci."""
    widziane: dict[str, None] = {}
    for slowo in tuple(SPRZED_PRZESTAWIENIA) + wczytaj_lokalne():
        widziane.setdefault(slowo.lower(), None)
    return tuple(widziane)
