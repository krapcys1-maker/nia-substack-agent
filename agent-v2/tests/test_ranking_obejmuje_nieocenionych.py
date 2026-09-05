# -*- coding: utf-8 -*-
"""Ranking banku obejmuje kandydatow, dla ktorych zostal uruchomiony.

## Wada, ktora ten plik pilnuje

`posortuj_bank` sprawdzalo CALA liste („czy jest ktokolwiek bez rangi"),
a partie do oceny brala jako `wolni = wolni[:ile]` — pierwsze `ile` pozycji.
Kandydat spoza tego okna uruchamial wiec PLATNY ranking, w ktorym go nie bylo,
i po ktorym nadal nie mial rangi.

To nie jest jednorazowa strata, tylko PETLA. Warunek wejscia pozostaje
prawdziwy, wiec kolejny przebieg robi to samo. Odtworzone: 40 ocenionych plus
jeden nowy na koncu, piec przebiegow z rzedu — PIEC platnych wywolan `bank`
i zero postepu. Przy dwoch przebiegach dziennie i ~$0,0105 za wywolanie to
okolo 63 centow miesiecznie palone w kolko, dopoki bank przekracza `ile`
wolnych wpisow.

Po poprawce te same piec przebiegow to JEDNO wywolanie, a nowy kandydat
dostaje range.

ZMIERZONE NA ZYWO 5 wrzesnia 2026 na prawdziwych faktach z przebiegu
finansowego (DeepSeek V4 Flash, $0,0129): fakt bez rangi — inspekcje PCAOB —
dostal range 1, a sedzia odrzucil definicje zerwania kowenantu.

## Czego ten plik pilnuje w DRUGA strone

Ranking jest WZGLEDNY: kandydat sam z siebie nie ma sie wobec czego ustawic.
Poprawka nie moze wiec wycinac samych nieocenionych — ocenieni zostaja
w partii jako punkty odniesienia. Sekcja 3.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_ranking_obejmuje_nieocenionych.py
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import config  # noqa: E402

config.uzyj_katalogu_danych(pathlib.Path(tempfile.mkdtemp()))
import db      # noqa: E402
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


CONN = db.connect()
LICZNIK = {"n": 0, "prompty": []}


def atrapa(ile_w_kolejnosci):
    def call(etap, s, prompt, **k):
        LICZNIK["n"] += 1
        LICZNIK["prompty"].append(prompt)
        return json.dumps({"kolejnosc": list(range(ile_w_kolejnosci)),
                           "wyrzuc": []})
    stages.llm = type("A", (), {"call": staticmethod(call),
                                "parse_json": staticmethod(json.loads)})()


def wpis(tresc, ranga):
    return {"fact": tresc, "status": "nowy", "ranga": ranga, "na_artykul": False,
            "decision": "d" * 20, "consequence": "c" * 20, "domain": "audit",
            "epoka": getattr(config, "EPOKA_KONTA", None)}


def poloz(n_ocenionych, n_nowych):
    w = [wpis("Znany fakt numer %d o audycie" % i, i) for i in range(n_ocenionych)]
    w += [wpis("NOWY fakt numer %d" % i, None) for i in range(n_nowych)]
    stages._zapisz_indeks(w)
    return w


print("=== 1. NOWY SPOZA OKNA TRAFIA DO PARTII ===")
poloz(40, 1)
LICZNIK["n"] = 0; LICZNIK["prompty"] = []
atrapa(40)
stages.posortuj_bank(CONN, 1)
sprawdz("model wolany raz", LICZNIK["n"] == 1, LICZNIK["n"])
sprawdz("NOWY jest w prompcie", "NOWY fakt numer 0" in LICZNIK["prompty"][0])
nowy = [x for x in stages.wczytaj_indeks() if str(x.get("fact")).startswith("NOWY")][0]
sprawdz("i dostal range", nowy.get("ranga") is not None, nowy.get("ranga"))

print()
print("=== 2. KONTRDOWOD: PETLA SIE ZAMYKA ===")
# Bez poprawki warunek wejscia zostawal prawdziwy w nieskonczonosc.
LICZNIK["n"] = 0
for _ in range(5):
    stages.posortuj_bank(CONN, 1)
sprawdz("piec kolejnych przebiegow nie placi juz nic", LICZNIK["n"] == 0,
        LICZNIK["n"])

print()
print("=== 3. OCENIENI ZOSTAJA JAKO PUNKTY ODNIESIENIA ===")
# Ranking jest wzgledny: sam nowy kandydat nie ma sie wobec czego ustawic.
poloz(40, 2)
LICZNIK["n"] = 0; LICZNIK["prompty"] = []
atrapa(40)
stages.posortuj_bank(CONN, 1)
p = LICZNIK["prompty"][0]
sprawdz("obaj nowi w prompcie",
        "NOWY fakt numer 0" in p and "NOWY fakt numer 1" in p)
sprawdz("i towarzysza im znani", "Znany fakt numer" in p)
sprawdz("partia nie przekracza limitu", p.count("id: ") <= 40, p.count("id: "))

print()
print("=== 4. NIEOCENIENI IDA PIERWSI ===")
# Gdyby szli na koncu, przy pelnym banku znowu wypadliby poza okno.
sprawdz("pierwszy w partii to NOWY",
        p.split("fakt: ", 1)[1].startswith("NOWY"),
        p.split("fakt: ", 1)[1][:40])

print()
print("=== 5. BANK BEZ NOWYCH NIE URUCHAMIA RANKINGU ===")
poloz(5, 0)
LICZNIK["n"] = 0
stages.posortuj_bank(CONN, 1)
sprawdz("nic nie zaplacono", LICZNIK["n"] == 0, LICZNIK["n"])

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
