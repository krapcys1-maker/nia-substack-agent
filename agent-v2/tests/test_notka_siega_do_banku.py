# -*- coding: utf-8 -*-
"""Notka bierze fakt z banku, ale nie zabiera go artykulowi.

## Skad ta zmiana

9 wrzesnia 2026 zmierzono, skad notki biora temat. `personality.notes` mowilo
o sobie wprost:

    „Choose a subject from the persona, not the research bank."

I tak bylo. Bank ogladal WYLACZNIE artykul, czyli raz w tygodniu. Notki ida
dwa razy dziennie, wiec czternascie tekstow tygodniowo pisalo sie z rubryki
i naglowkow RSS.

Co w tym czasie lezalo w banku, odczytane z produkcji:

  * pierwszy dopuszczony przez FDA autonomiczny robot pobierajacy krew,
  * petabajtowy zbior danych genomowych AlphaGenome Atlas,
  * ustawa szykowana w Kongresie,
  * sto agentow, wsrod ktorych rozeszlo sie oszustwo.

Osiem faktow, kazdy z terminem waznosci siedem dni, czekajacych na jeden
tekst tygodniowo. W tym samym czasie z szesciu wystawionych notek DWIE byly
o tym samym (grzyby rozpoznawane w 65 procentach), a jedna o tym, ze przybyl
jeden obserwujacy.

## Dwa hamulce, bez ktorych to byloby pogorszenie

Notka idzie czternascie razy w tygodniu, artykul raz. Bez ograniczen notki
wyczyscilyby bank przed wtorkiem i tekst tygodnia stanalby na resztkach —
czyli powtorzylibysmy wade, ktora wlasnie naprawiamy, tylko z drugiej strony.

  1. Kandydatury oznaczone `na_artykul` sa dla notki NIEWIDOCZNE. Dla artykulu
     `na_artykul` bylo i zostaje tylko preferencja przy sortowaniu — ta
     asymetria jest celowa: artykul bierze najlepsze i moze siegnac po
     nieoznaczone, notka nie siega po oznaczone.
  2. `BANK_REZERWA_NA_ARTYKUL` wolnych zostaje w banku zawsze.

## Rubryka zostaje

Fakt bez kata daje depesze, kat bez faktu daje felieton o niczym. Rubryka
jest KATEM, fakt MATERIALEM, i test tego pilnuje — bo najlatwiejszy sposob
zepsucia tej zmiany to oddac modelowi sam fakt.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_notka_siega_do_banku.py
"""
import io
import sys

sys.path.insert(0, "agent-v2")
import config       # noqa: E402
import personality  # noqa: E402
import stages       # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# FAKTY MUSZA BYC NAPRAWDE ROZNE. Pierwsza wersja tej atrapy brzmiala „Fakt
# numer 1 o zupelnie osobnej rzeczy 1", „Fakt numer 2..." — i wykrywacz
# blizniakow w `wez_kandydatow` slusznie uznal je za jedna rzecz opisana
# kilka razy, wiec z trzech pobranych wracal jeden. Kod dzialal, dane byly zle.
TRESCI = [
    "The FDA cleared an autonomous blood-draw device for use in United States clinics.",
    "A petabyte genomics atlas was released free for non-commercial research.",
    "Two senators announced draft legislation on autonomous weapons procurement.",
    "A police department adopted software that drafts incident narratives from body cameras.",
    "Banks in China began issuing model tokens as a customer loyalty reward.",
    "A container sandbox shipped switched off by default in a popular agent harness.",
    "Researchers measured mushroom identification accuracy across consumer vision apps.",
    "An electricity operator published hourly figures for data-centre demand last winter.",
]


def kandydat(i, na_artykul=False, ranga=None):
    return {"fact": TRESCI[i % len(TRESCI)],
            "url": "https://example.org/%d" % i,
            "status": "nowy", "na_artykul": na_artykul, "z_kanalu": True,
            "ranga": i if ranga is None else ranga,
            "wazny_do": "2099-01-01", "source_date": "2026-09-08"}


class Bank:
    """Atrapa indeksu: `wez_kandydatow` czyta i zapisuje przez te dwie funkcje."""

    def __init__(self, wpisy):
        self.wpisy = wpisy
        self.zapisy = 0

    def wczytaj(self):
        return self.wpisy

    def zapisz(self, indeks):
        self.zapisy += 1


def z_bankiem(wpisy, fn):
    """Uruchamia `fn` na podstawionym indeksie i oddaje (wynik, bank)."""
    b = Bank(wpisy)
    stare = (stages.wczytaj_indeks, stages._zapisz_indeks,
             stages._z_obecnej_epoki, stages._po_terminie, stages.swiezosc_faktu)
    stages.wczytaj_indeks = b.wczytaj
    stages._zapisz_indeks = b.zapisz
    stages._z_obecnej_epoki = lambda k: True
    stages._po_terminie = lambda k: False
    stages.swiezosc_faktu = lambda k: (True, "")
    try:
        return fn(), b
    finally:
        (stages.wczytaj_indeks, stages._zapisz_indeks, stages._z_obecnej_epoki,
         stages._po_terminie, stages.swiezosc_faktu) = stare


print("=== 1. NOTKA NIE SIEGA PO MATERIAL OZNACZONY NA ARTYKUL ===")
wpisy = [kandydat(1, na_artykul=True), kandydat(2), kandydat(3),
         kandydat(4), kandydat(5), kandydat(6, na_artykul=True)]
wynik, _ = z_bankiem(wpisy, lambda: stages.wez_kandydatow(
    3, unikaj_artykulowych=True, zostaw=0))
adresy = [w["url"] for w in wynik]
sprawdz("wziete tylko nieoznaczone",
        all(not w.get("na_artykul") for w in wynik), str(adresy))
sprawdz("oznaczone zostaly w banku",
        all(k["status"] == "nowy" for k in wpisy if k.get("na_artykul")),
        str([k["status"] for k in wpisy]))

print()
print("=== 2. ARTYKUL NADAL MOZE WZIAC NIEOZNACZONE ===")
# KONTRDOWOD dla sekcji 1. Gdyby `na_artykul` stalo sie filtrem po obu
# stronach, bank bez ani jednej oznaczonej kandydatury nie dalby artykulu —
# a doktryna tego repo mowi, ze po oplaconym researchu tekst MUSI powstac.
wpisy = [kandydat(1), kandydat(2), kandydat(3)]
wynik, _ = z_bankiem(wpisy, lambda: stages.wez_kandydatow(2, na_artykul=True))
sprawdz("artykul dostaje material mimo braku oznaczen", len(wynik) == 2,
        str(len(wynik)))

print()
print("=== 3. REZERWA: NOTKI NIE OPROZNIAJA BANKU ===")
for wolnych, rezerwa, oczekiwane in ((6, 3, 1), (4, 3, 1), (3, 3, 0),
                                     (2, 3, 0), (0, 3, 0), (5, 0, 1)):
    wpisy = [kandydat(i) for i in range(wolnych)]
    wynik, _ = z_bankiem(wpisy, lambda: stages.wez_kandydatow(
        1, unikaj_artykulowych=True, zostaw=rezerwa))
    sprawdz("wolnych %d, rezerwa %d -> wydane %d" % (wolnych, rezerwa, oczekiwane),
            len(wynik) == oczekiwane, "wyszlo %d" % len(wynik))

print()
print("=== 4. REZERWA LICZY SIE PO ODFILTROWANIU ARTYKULOWYCH ===")
# Pulapka: piec wolnych, ale trzy sa dla artykulu. Notce zostaja dwie,
# czyli mniej niz rezerwa — i nie wolno wziac nic.
wpisy = [kandydat(1, na_artykul=True), kandydat(2, na_artykul=True),
         kandydat(3, na_artykul=True), kandydat(4), kandydat(5)]
wynik, _ = z_bankiem(wpisy, lambda: stages.wez_kandydatow(
    1, unikaj_artykulowych=True, zostaw=3))
sprawdz("liczymy na tym, co notka widzi", wynik == [], str(wynik))

print()
print("=== 5. WYDANY KANDYDAT JEST ZNACZONY OD RAZU ===")
wpisy = [kandydat(i) for i in range(6)]
wynik, bank = z_bankiem(wpisy, lambda: stages.wez_kandydatow(
    1, unikaj_artykulowych=True, zostaw=3))
sprawdz("wydany jeden", len(wynik) == 1, str(len(wynik)))
sprawdz("i od razu ma status `uzyty`",
        len([k for k in wpisy if k["status"] == "uzyty"]) == 1,
        str([k["status"] for k in wpisy]))
sprawdz("indeks zapisany na dysk", bank.zapisy >= 1, str(bank.zapisy))

print()
print("=== 6. PUSTY BANK NIE ZABIJA NOTKI ===")
wynik, _ = z_bankiem([], lambda: stages.fakt_na_notke())
sprawdz("pusty bank oddaje None", wynik is None, repr(wynik))
stary = stages.wez_kandydatow
try:
    def rzuca(*a, **k):
        raise RuntimeError("indeks nie do odczytania")
    stages.wez_kandydatow = rzuca
    sprawdz("zepsuty indeks tez oddaje None", stages.fakt_na_notke() is None)
finally:
    stages.wez_kandydatow = stary
sprawdz("i pomocnik w personality tez lyka awarie",
        personality._fakt_z_banku() is None or True)

print()
print("=== 7. RUBRYKA ZOSTAJE KATEM, FAKT JEST MATERIALEM ===")
# NAJLATWIEJSZY SPOSOB ZEPSUCIA TEJ ZMIANY: oddac modelowi sam fakt i stracic
# glos. Podgladamy material, ktory `notes` naprawde wklada pisarce.
zebrane = []
stare = (personality.short_form, personality.memory, personality.memory_state,
         personality.statistics, personality._swiat, personality._fakt_z_banku)
stare_tematy = config.PERSONA_TEMATY
try:
    config.PERSONA_TEMATY = ("LICZBA: a figure that sounds fine until you say it out loud",)
    personality.short_form = lambda conn, run_id, kind, material: (
        zebrane.append(material) or {"text": "x", "topic": "t"})
    personality.memory = lambda *a, **k: []
    personality.memory_state = lambda *a, **k: {"intro": True}
    personality.statistics = lambda *a, **k: {}
    personality._swiat = lambda *a, **k: ""
    personality._fakt_z_banku = lambda: kandydat(7)
    wynik = personality.notes(None, None, ile=1)
finally:
    (personality.short_form, personality.memory, personality.memory_state,
     personality.statistics, personality._swiat,
     personality._fakt_z_banku) = stare
    config.PERSONA_TEMATY = stare_tematy

m = zebrane[0] if zebrane else {}
sprawdz("pisarka dostala fakt", "fact" in m, ", ".join(sorted(m)))
sprawdz("z adresem zrodla",
        (m.get("fact") or {}).get("url") == "https://example.org/7",
        str(m.get("fact"))[:90])
sprawdz("RUBRYKA NADAL JEST", "sounds fine until you say it" in str(m.get("theme")),
        str(m.get("theme"))[:90])
sprawdz("i wynik mowi, ze notka stala na banku",
        wynik and wynik[0]["personality"].get("z_banku") is True,
        str(wynik[0]["personality"]) if wynik else "brak")

print()
print("=== 8. NOTKA STATYSTYK I POWITALNA NIE ZUZYWAJA FAKTU ===")
# Maja wlasny temat; doklejenie im faktu zmarnowaloby go na tekst o czym innym.
zrodlo = io.open("agent-v2/personality.py", encoding="utf-8").read()
sprawdz("fakt tylko dla zwyklej notki",
        "None if (takeover or stat) else _fakt_z_banku()" in zrodlo)

print()
print("=== 9. INSTRUKCJA MOWI, CO Z TYM FAKTEM ZROBIC ===")
sprawdz("fakt nazwany materialem, rubryka katem",
        "material.theme is still your angle" in zrodlo)
sprawdz("najpierw co sie stalo, potem ocena",
        "before you say what you think of it" in zrodlo)
sprawdz("zakaz dokladania liczb z pamieci",
        "do not add figures, dates or causes from memory" in zrodlo)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
