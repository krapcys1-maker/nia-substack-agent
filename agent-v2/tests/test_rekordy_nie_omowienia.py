# -*- coding: utf-8 -*-
"""Research liczy DOKUMENTY PIERWOTNE, nie pozycje na liscie.

ZMIERZONE na trzynastu przebiegach z dokladnie jednym wywolaniem dyskoverii —
tylko takie, bo przy kilku wywolaniach na przebieg zrodel nie da sie przypisac
do wywolania i pierwsza wersja tego pomiaru byla przez to zniekształcona.

    najkrotsze szukanie (15,9 wyszukiwan):  7,5 zrodel, z czego 5,1 pierwotnych
    najdluzsze szukanie (28,0 wyszukiwan): 10,0 zrodel, z czego 3,0 pierwotne

Siedemdziesiat szesc procent wiecej szukania kupilo CZTERDZIESCI PROCENT MNIEJ
rekordow. W skrajnych przypadkach: 11 wyszukiwan dalo dziesiec pierwotnych na
dziesiec, a 25 wyszukiwan jedno na dziewiec.

PRZYCZYNA JEST W ZAMOWIENIU, nie w modelu. Prompt kazal zwrocic DZIESIEC zrodel,
z czego tylko DWA musialy byc pierwotne. Model szukal wiec, az uzbieral dziesiec
pozycji — a gdy dokumenty sie konczyly, dopychal liste omowieniami. Dluzsze
szukanie to nie bylo szukanie lepiej, tylko dopychanie do liczby.

DWIE POPRAWKI:
  1. Prompt liczy rekordy: dziesiatka to SUFIT, nie cel; pierwotne maja byc
     WIEKSZOSCIA; dopisanie zrodla, zeby dobic do liczby, jest wprost zakazane.
  2. Druga runda odpala sie takze przy BRAKU REKORDOW, nie tylko przy chudym
     korpusie — i wtedy prosi wylacznie o dokumenty pierwotne. Wczesniej korpus
     dziewieciu zrodel z jednym pierwotnym nie odpalal jej nigdy, bo dziewiec to
     duzo wiecej niz prog czterech.

BEZ PYTESTA, bez platnych wywolan. Uruchamiac z korzenia repozytorium.
"""
import pathlib
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


print("=== 1. PROMPT LICZY REKORDY, NIE POZYCJE ===")
# BEZ ZAWIJANIA WIERSZY. Prompty sa lamane na 79 znakow, a kod na 79 tez —
# wiec kazde zdanie dluzsze niz polowa linii bywa przeciete. Pierwsza wersja
# tego pliku oblewala na frazach, ktore SA w plikach, tylko w dwoch wierszach.
# Ta sama lekcja co przy „this subject" tego samego dnia.
def plaski(tekst: str) -> str:
    return " ".join(tekst.split())


brief = plaski(pathlib.Path("agent-v2/prompts/dyskoveria.md")
               .read_text(encoding="utf-8"))
sprawdz("mowi, ze liczba pozycji to sufit, nie cel",
        "ceiling, not a target" in brief)
sprawdz("zada, zeby pierwotne byly wiekszoscia",
        "MAJORITY" in brief)
sprawdz("zakazuje dopychania do liczby",
        "Never add a source to reach a number" in brief)
sprawdz("i podaje pomiar, a nie sama zasade",
        "5.1 were primary" in brief and "3.0 were primary" in brief)
sprawdz("mowi wprost, ze krotka lista rekordow jest dobra",
        "Six primary sources and" in brief)

print()
print("=== 2. DRUGA RUNDA WIDZI BRAK REKORDOW ===")
zrodlo = pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8")
zrodlo_plaski = plaski(zrodlo)
sprawdz("liczy pierwotne w korpusie",
        'pierwotnych = sum(1 for s in corpus if s.get("class") == "PRIMARY")'
        in zrodlo)
sprawdz("odpala sie takze bez rekordow, nie tylko przy chudym korpusie",
        "if za_chudo or bez_rekordow:" in zrodlo)
sprawdz("i wtedy prosi wylacznie o pierwotne",
        "tylko_pierwotne=bez_rekordow" in zrodlo)

print()
print("=== 3. KONTRDOWOD: WARUNEK NA SAMEJ LICZBIE BY TEGO NIE ZLAPAL ===")
# Prawdziwy przypadek z produkcji: dziewiec pobranych, jedno pierwotne.
korpus = ([{"class": "PRIMARY"}] + [{"class": "SUPPORTING"}] * 8)
za_chudo = len(korpus) < config.MIN_ZRODEL_DO_PISANIA
bez_rekordow = (sum(1 for s in korpus if s["class"] == "PRIMARY")
                < config.MIN_PRIMARY_SOURCES)
sprawdz("stary warunek (sama liczba) NIE odpala", not za_chudo)
sprawdz("nowy warunek (brak rekordow) odpala", bez_rekordow)
sprawdz("razem: druga runda rusza", za_chudo or bez_rekordow)

# I odwrotnie — korpus zdrowy nie ma odpalac drugiej rundy.
zdrowy = [{"class": "PRIMARY"}] * 4 + [{"class": "SUPPORTING"}] * 2
sprawdz("zdrowy korpus NIE odpala drugiej rundy",
        not (len(zdrowy) < config.MIN_ZRODEL_DO_PISANIA
             or sum(1 for s in zdrowy if s["class"] == "PRIMARY")
             < config.MIN_PRIMARY_SOURCES))

print()
print("=== 4. TRYB TYLKO-PIERWOTNE ZMIENIA PYTANIE ===")
import inspect   # noqa: E402
sprawdz("discovery przyjmuje tylko_pierwotne",
        "tylko_pierwotne" in inspect.signature(stages.discovery).parameters)
kod = plaski(inspect.getsource(stages.discovery))
sprawdz("i dokleja polecenie o rekordach",
        "SECOND ROUND" in kod and "PRIMARY records only" in kod)
sprawdz("mowiac wprost, ze mniej jest w porzadku",
        "Fewer is fine" in kod)

print()
print("=== 5. PROGI SA SPOJNE ===")
sprawdz("sufit pozycji wiekszy niz prog pierwotnych",
        config.DISCOVERY_MAX_RESULTS > config.MIN_PRIMARY_SOURCES,
        "%s > %s" % (config.DISCOVERY_MAX_RESULTS, config.MIN_PRIMARY_SOURCES))
sprawdz("prog pisania nie jest wyzszy od sufitu pozycji",
        config.MIN_ZRODEL_DO_PISANIA <= config.DISCOVERY_MAX_RESULTS,
        "%s <= %s" % (config.MIN_ZRODEL_DO_PISANIA,
                      config.DISCOVERY_MAX_RESULTS))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
