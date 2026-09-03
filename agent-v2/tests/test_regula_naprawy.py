# -*- coding: utf-8 -*-
"""Kiedy naprawe PRZYJAC, kiedy ODRZUCIC, a kiedy powiedziec „nie wiem".

CO BYLO ZLE. Pierwsza wersja reguly porownywala DWIE LICZBY z DWOCH ROZNYCH
wywolan platnej bramki faktow: „ile zarzutow bylo przed" wobec „ile jest po".
Cztery wady naraz, kazda wystarczy sama:

  a) porownywala dwa niezalezne LOSOWANIA, a nie dwa stany;
  b) liczyla SZTUKI zamiast tozsamosci — jedno twierdzenie zaflagowane szumem
     kasowalo realna naprawe, a nowy tekst bywa rozkladany przez bramke na inna
     liczbe twierdzen niz stary, wiec te liczby nie sa porownywalne nawet bez
     szumu;
  c) remis szedl na NIEKORZYSC naprawy — choc koszty sa odwrotne: notka i tak
     idzie w swiat (`safe_to_post = True` bezwarunkowo), wiec odrzucenie
     naprawy nie wstrzymuje publikacji, tylko PUBLIKUJE WERSJE, O KTOREJ WIEMY,
     ZE ZAWIERA FALSZ;
  d) AWARIA bramki uchodzila za sukces. `zweryfikuj` na wyjatku oddaje
     `{"claims": [], "safe_to_post": True}` BEZ klucza `zarzuty` — wiec regula
     liczyla zero zarzutow, zero bylo mniejsze od jedynki, i naprawa szla do
     publikacji NIESPRAWDZONA, zapisana w dzienniku jako sprawdzona.

Wada (d) byla na produkcji. To ta sama klasa bledu, ktora ten projekt tropi od
tygodnia — „zero z wyjasnieniem przestaje wygladac na awarie" — wpisana do
funkcji, ktora powstala po to, zeby nie wychodzila nieprawda.

CO ROBI REGULA DZIS. Pyta o dwie rzeczy OSOBNO: czy zarzut, ktory mial zniknac,
zniknal, i czy przyszlo cos nowego. Placi za trzecie sprawdzenie WYLACZNIE
wtedy, gdy mialaby wyrzucic naprawe — czyli tam, gdzie szum naprawde kosztuje.

TEST MIERZY TAKZE LICZBE WYWOLAN MODELU. Kolejka jest zaskryptowana: wywolanie
ponad skrypt konczy sie wyjatkiem, a krok niezuzyty na koncu tez. Bez tego
„placimy tylko wtedy, gdy trzeba" jest obietnica bez pokrycia.

BEZ PYTESTA, zero sieci, zero platnych wywolan, produkcja nietknieta.
Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_regula_naprawy.py
"""
import json
import sqlite3
import sys

sys.path.insert(0, "agent-v2")
import config      # noqa: E402
import llm         # noqa: E402
import stages      # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


PRAWDZIWE = llm.call
CONN = sqlite3.connect(":memory:")

ORYGINAL = (
    "646 miles. That is how far FirmaA averaged between human takeovers in "
    "California last year. FirmaB went 60,682 under the same DMV programme. "
    "FirmaA's own figure was 2,044 miles the year before, so it got worse "
    "while the state kept counting. Thirty times the takeovers, same year."
)
POPRAWIONY = ORYGINAL.replace("Thirty times", "Ninety-four times")

CEL = {"claim": "FirmaA logged thirty times the takeovers of FirmaB.",
       "status": "refuted",
       "what_the_source_says": "60,682 / 646 = 93.9, the multiple is about 94.",
       "url": "https://dmv.ca.gov/"}
NOWY_ZARZUT = {"claim": "FirmaA is not Uber's robotaxi partner at all.",
               "status": "refuted",
               "what_the_source_says": "Uber committed close to 500M to FirmaA.",
               "url": "https://przyklad-firma-a.test/"}


class Kolejka:
    """Atrapa `llm.call` z dwustronnym kontraktem.

    Wywolanie ponad skrypt to blad. Krok niezuzyty do konca to tez blad.
    Jedno narzedzie odpowiada wiec na oba pytania naraz: „czy zawolano wlasciwa
    liczbe razy" i „czy nie zawolano niepotrzebnie".
    """

    def __init__(self, kroki):
        self.kroki = list(kroki)
        self.zuzyte = []

    def __call__(self, purpose, system, user, **kw):
        if not self.kroki:
            raise AssertionError(
                "WYWOLANIE PONAD SKRYPT: %s (zuzyto juz %s)"
                % (purpose, self.zuzyte))
        etap, odpowiedz = self.kroki.pop(0)
        if etap != purpose:
            raise AssertionError("skrypt czekal na %r, przyszlo %r"
                                 % (etap, purpose))
        self.zuzyte.append(purpose)
        if isinstance(odpowiedz, Exception):
            raise odpowiedz
        return odpowiedz

    def komplet(self):
        return not self.kroki


def factcheck(*claims):
    return json.dumps({"claims": list(claims)})


NAPRAWA_OK = json.dumps({"text": POPRAWIONY, "co_zmienione": "thirty -> 94"})


def audyt_wejsciowy(*claims):
    """Audyt oryginalu w ksztalcie, jaki oddaje `zweryfikuj`."""
    blok = [c for c in claims if c.get("status") != "confirmed"]
    return {"claims": list(claims), "zarzuty": blok, "nie_sprawdzone": False,
            "safe_to_post": not blok, "verdict": "test"}


def uruchom(kroki, audyt=None):
    """Odpala naprawe na zadanym skrypcie. Oddaje (wynik, kolejka)."""
    k = Kolejka(kroki)
    llm.call = k
    stages._NAPRAW_ZUZYTE.clear()
    wynik = stages.napraw_obalone(
        CONN, 1, ORYGINAL, audyt or audyt_wejsciowy(CEL),
        kontekst="Substack note, type SPROSTOWANIE",
        min_slow=config.NOTE_MIN_WORDS, max_slow=config.NOTE_MAX_WORDS,
        etap="naprawa", zapora=stages._zapora_notki)
    return wynik, k


print("=== 1. CEL NAPRAWIONY, ZERO NOWYCH -> PRZYJETA, BEZ DOPLATY ===")
r, k = uruchom([("naprawa", NAPRAWA_OK),
                ("factcheck", factcheck({"claim": "x", "status": "confirmed"}))])
sprawdz("przyjeta", r is not None)
sprawdz("oddany tekst to poprawiony", bool(r) and r["tekst"] == POPRAWIONY)
sprawdz("DWA wywolania, nie trzy", k.zuzyte == ["naprawa", "factcheck"], k.zuzyte)
sprawdz("skrypt zuzyty do konca", k.komplet())

print()
print("=== 2. CEL NADAL STOI -> ODRZUCONA, TEZ BEZ DOPLATY ===")
# Nie pytamy o szum, tylko stwierdzamy, ze naprawa nie zrobila tego, po co
# powstala. Trzecie sprawdzenie byloby tu wydatkiem bez pytania.
r, k = uruchom([("naprawa", NAPRAWA_OK), ("factcheck", factcheck(dict(CEL)))])
sprawdz("odrzucona", r is None)
sprawdz("DWA wywolania — bez potwierdzania",
        k.zuzyte == ["naprawa", "factcheck"], k.zuzyte)

print()
print("=== 3. CEL NAPRAWIONY, ALE DOSZEDL NOWY ZARZUT -> I TAK PRZYJETA ===")
# Przypadek ZMIERZONY NA ZYWO 2 wrzesnia. Wersja posrednia doplacala tu za
# trzecie sprawdzenie, zeby ustalic, czy nowy zarzut to migniecie. Zdjete
# decyzja wlasciciela: „to nie apteka".
#
# Rachunek jest prosty i jest po jego stronie. Oryginal zawiera falsz NA PEWNO
# — wlasnie go obalilismy. Naprawa stoi na materiale dowodowym i tylko jedno
# losowanie bramki zarzuca jej cos innego. Wybor oryginalu znaczylby
# publikowanie pewnej nieprawdy w obawie przed niepewna.
r, k = uruchom([("naprawa", NAPRAWA_OK),
                ("factcheck", factcheck(dict(NOWY_ZARZUT)))])
sprawdz("przyjeta mimo nowego zarzutu", r is not None)
sprawdz("DWA wywolania — zadnego doplacania",
        k.zuzyte == ["naprawa", "factcheck"], k.zuzyte)
sprawdz("ale nowy zarzut jest POLICZONY, nie przemilczany",
        bool(r) and r["nowych"] == 1, r)
sprawdz("i zapis mowi, ze tekst byl sprawdzony",
        bool(r) and r["sprawdzona"] is True, r)

print()
print("=== 4. AWARIA BRAMKI -> NAPRAWA IDZIE, ALE ZAPIS O TYM MOWI ===")
# Ta sciezka byla na produkcji ZEPSUTA i to inaczej, niz wyglada teraz.
# Tamten blad polegal na tym, ze awaria bramki LICZYLA SIE JAKO CZYSTY WYNIK:
# `zweryfikuj` oddawalo `claims: []` bez klucza `zarzuty`, kod liczyl zero
# zarzutow i wpisywal do dziennika „sprawdzone". Dzis decyzja jest ta sama,
# ale JAWNA — i zapis niesie, ze sprawdzenia nie bylo.
r, k = uruchom([("naprawa", NAPRAWA_OK),
                ("factcheck", RuntimeError("dostawca padl"))])
sprawdz("naprawa idzie", r is not None)
sprawdz("ale zapis mowi, ze NIE byla sprawdzona",
        bool(r) and r["sprawdzona"] is False, r)
sprawdz("i nie udaje, ze policzyl zarzuty",
        bool(r) and r["obalonych_po"] is None, r)
sprawdz("dwa wywolania", k.zuzyte == ["naprawa", "factcheck"], k.zuzyte)

# KONTRDOWOD: pokazujemy, ze awaryjny wynik NADAL wygladalby na czysty,
# gdyby czytac go tak, jak czytal go kod z 1 wrzesnia.
llm.call = lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("padl"))
awaria = stages.zweryfikuj(CONN, 1, "cokolwiek", "test")
sprawdz("awaryjny wynik niesie jawne `nie_sprawdzone`",
        awaria.get("nie_sprawdzone") is True, awaria)
sprawdz("bo bez tej flagi wygladalby na czystosc",
        awaria.get("zarzuty") == [] and awaria.get("safe_to_post") is True,
        awaria)

print()
print("=== 6. STATUS SPOZA CZTERECH WARTOSCI NIE PRZECHODZI CICHO ===")
# `str(c.get("status") or "")` zamienia None, "REFUTED" i "maybe" w cos, co nie
# pasuje do zadnej galezi — i wtedy twierdzenie po prostu NIE JEST zarzutem.
# Sprawdzamy, ze bramka klasyfikuje je po LICZBIE, a nie po wierze w etykiete.
for etykieta, status, czy_blokuje in (
        ("wielkie litery", "REFUTED", True),
        ("brak statusu", None, True),
        ("wymyslony status", "maybe", True),
        ("jawne confirmed", "confirmed", False)):
    llm.call = lambda *a, _s=status, **kw: json.dumps({"claims": [
        {"claim": "The figure was 1,234 in 2025.", "status": _s,
         "what_the_source_says": "nie znaleziono"}]})
    out = stages.zweryfikuj(CONN, 1, "tekst", "test")
    ma = bool(out.get("zarzuty"))
    sprawdz("%-16s -> %s" % (etykieta, "zarzut" if czy_blokuje else "przechodzi"),
            ma is czy_blokuje,
            "status=%r, zarzutow=%d" % (status, len(out.get("zarzuty") or [])))

print()
print("=== 7. SPOJNOSC WEWNETRZNA WYNIKU BRAMKI ===")
llm.call = lambda *a, **kw: json.dumps({"claims": [
    {"claim": "FirmaB went 60,682 miles.", "status": "confirmed"},
    {"claim": "FirmaA logged thirty times as many.", "status": "refuted",
     "what_the_source_says": "about 94"},
    {"claim": "Regulators care about this.", "status": "unverified"}]})
out = stages.zweryfikuj(CONN, 1, "tekst", "test")
sprawdz("zarzuty sa podzbiorem twierdzen",
        all(z in out["claims"] for z in out["zarzuty"]))
sprawdz("niepuste zarzuty => safe_to_post jest FALSE, nie tylko falsywe",
        out["safe_to_post"] is False, out["safe_to_post"])
sprawdz("potwierdzone nie jest zarzutem",
        all(z.get("status") != "confirmed" for z in out["zarzuty"]))
sprawdz("teza bez liczby przechodzi",
        not any("Regulators" in str(z.get("claim")) for z in out["zarzuty"]))

print()
print("=== 8. TOZSAMOSC ZARZUTU: ZACHOWAWCZO W JEDNA STRONE ===")
# Blad „rozne uznane za to samo" przepuszcza swiezy falsz jako juz znany.
# Blad w druga strone kosztuje jedno dodatkowe sprawdzenie. Dlatego zgoda
# musi byc mocna.
for opis, a, b, oczekiwane in (
    ("ten sam fakt, inne slowa laczace",
     {"claim": "FirmaA logged thirty times the takeovers of FirmaB",
      "what_the_source_says": "60,682 / 646 = 93.9"},
     {"claim": "FirmaA had thirty times the takeovers as FirmaB",
      "what_the_source_says": "60682 646 93.9"}, True),
    ("ta sama liczba, INNY fakt",
     {"claim": "The policy was standardised in 1946", "url": "https://x/"},
     {"claim": "The print run reached 1946 copies", "url": "https://x/"}, False),
    ("identyczna teza bez zadnej liczby",
     {"claim": "Regulators never publish the raw logs"},
     {"claim": "Regulators never publish the raw logs"}, True),
    ("rozne tezy bez liczb",
     {"claim": "Regulators never publish the raw logs"},
     {"claim": "Manufacturers release quarterly safety notes"}, False),
):
    sprawdz("%-34s -> %s" % (opis, oczekiwane),
            stages._ten_sam_zarzut(a, b) is oczekiwane)

llm.call = PRAWDZIWE

print()
print("=" * 62)
print("ZDANE: %d    OBLANE: %d" % (zdane, oblane))
sys.exit(1 if oblane else 0)
