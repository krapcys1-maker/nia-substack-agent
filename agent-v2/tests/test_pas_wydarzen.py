# -*- coding: utf-8 -*-
"""Wielkie wydarzenie omija sufit banku — a jego brak nie omija.

DLACZEGO TO POWSTALO. Wlasciciel: „jak wychodzi nowy model albo jest duze
wydarzenie AI, to musi miec pierwszenstwo przed wszystkim". Sufit banku
(`bank_pelny`) istnieje po to, zeby zapas nie rosl bez konca — ale przy pelnym
banku szukanie jest POMIJANE, wiec bez tego pasa wielkie wydarzenie nie
weszloby do potoku przez caly tydzien.

Ta galaz nie wykonala sie ani razu na produkcji: przez trzy dni obserwacji
korpus nie mial wydarzenia spelniajacego prog (trzy rozne kanaly, nie starsze
niz cztery doby), a bank bywal pelny. Sciezka nieprzetestowana to sciezka,
ktora dziala do pierwszego uzycia.

CO TO NIE JEST. Wydarzenie daje PIERWSZENSTWO W KOLEJCE, nigdy zwolnienia z
jakosci. Tresc przechodzi te same bramki co zawsze — to sprawdzaja inne pliki.
Tutaj chodzi wylacznie o to, czy pas w ogole przepuszcza.

KONTRDOWOD. Sam fakt, ze z wydarzeniem szukanie rusza, nie dowodzi niczego —
moglby ruszac zawsze, a sufit byc martwy. Dlatego sprawdzamy trzy kombinacje:
wydarzenie + pelny bank, brak wydarzenia + pelny bank, brak wydarzenia + pusty.

BEZ PYTESTA i BEZ PLATNYCH WYWOLAN — `llm.call` podmieniony na atrape.
"""
import json
import pathlib
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "agent-v2")
import config           # noqa: E402
import korpus_kanalow   # noqa: E402
import stages           # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


SWIEZY = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%d")

FAKT = {
    "fact": ("A named laboratory published the evaluation it ran before "
             "shipping, and the report names who could have stopped the "
             "release."),
    "wrong_belief": "People assume nobody inside can stop a launch.",
    "actually": "A named committee can, and the report says so.",
    "decision": ("A decision: the safety committee holds a documented veto "
                 "over the release date."),
    "consequence": ("The release you were waiting for moved by weeks because of that veto, and your provider bill moved with it."),
    "url": "https://example.org/report", "source_date": SWIEZY,
    "control_date": SWIEZY, "control_url": "https://example.org/report",
    "control_verdict": "CONFIRMS", "control_fact": "checked today, unchanged",
    "domain": "how a model is trained and who signs off",
}

WYDARZENIE = [{"o_czym": ["titan", "seven", "inference"], "kanalow": 3,
               "kanaly": ["a", "b", "c"],
               "tytuly": ["titan seven changes inference pricing"],
               "data": datetime.now(timezone.utc).strftime("%Y-%m-%d")}]

katalog = pathlib.Path(tempfile.mkdtemp())
_stary_indeks = stages.INDEKS_KANDYDATOW
_stare_call = stages.llm.call
_stary_zaczyn = stages.zaczyn_z_kanalow
_stare_wyd = korpus_kanalow.wielkie_wydarzenia
_stary_korpus = korpus_kanalow.korpus_kanalow
_stary_pelny = stages.bank_pelny
_stare_zuzyte = stages.wczytaj_zuzyte
_stara_pamiec_wyd = stages.WYDARZENIA_OBSLUZONE

# CALY KATALOG DANYCH, a nie tylko te stale, ktore widac ponizej.
# `znajdz_ciekawostki` schodzi przez `aktualne_modele.pobierz` do `db.connect()`,
# a `config.DB_PATH` jest liczone przy imporcie — wiec bez tego przekierowania
# ten test otwieral PRODUKCYJNA baze. Zmierzone sonda 2 wrzesnia 2026.
_zdjecie_sciezek = config.uzyj_katalogu_danych(katalog)

stages.INDEKS_KANDYDATOW = katalog / "indeks.json"
stages.INDEKS_KANDYDATOW.write_text("[]", encoding="utf-8")
# PAMIEC WYDARZEN TEZ DO KATALOGU TYMCZASOWEGO.
#
# Od 1 wrzesnia 2026 `znajdz_ciekawostki` zapamietuje, o ktorych wydarzeniach
# juz dobieralo material — inaczej jedno zdarzenie otwieralo furtke przy kazdym
# z pieciu przebiegow dziennie (zmierzone: szesc pelnych szukan w trzy dni o tej
# samej premierze ACME 5.3, okolo 13,6 USD miesiecznie).
#
# Bez tej podmiany test pisal do PRODUKCYJNEGO `data/wydarzenia_obsluzone.json`
# i sam stawal sie zalezny od kolejnosci: pierwszy przebieg zapamietywal swoje
# zdarzenie-atrape, drugi juz nie przebijal sufitu banku — bo kod SLUSZNIE uznal
# je za znane. Test oblewal, a kod byl w porzadku.
stages.WYDARZENIA_OBSLUZONE = katalog / "wydarzenia.json"
stages.llm.call = lambda *a, **kw: json.dumps({"facts": [FAKT]})
stages.zaczyn_z_kanalow = lambda *a, **kw: "(brak w tescie)"
korpus_kanalow.korpus_kanalow = lambda *a, **kw: []
stages.wczytaj_zuzyte = lambda *a, **kw: []

try:
    print("=== 0. ATRAPY SA TYM, ZA CO JE BIORE ===")
    ok, powod = stages.swiezosc_faktu(FAKT)
    sprawdz("atrapowy fakt przechodzi bramke swiezosci", ok, powod)
    ok, powod = stages.bramka_kandydata(FAKT)
    sprawdz("i bramke kandydata", ok, powod)

    print()
    print("=== 1. PELNY BANK BEZ WYDARZENIA — NIE SZUKAMY ===")
    korpus_kanalow.wielkie_wydarzenia = lambda *a, **kw: []
    stages.bank_pelny = lambda: True
    stages.INDEKS_KANDYDATOW.write_text("[]", encoding="utf-8")
    wynik = stages.znajdz_ciekawostki(None, None)
    sprawdz("nic nie oddane", wynik == [], wynik)
    sprawdz("i nic nie dopisane do indeksu",
            json.loads(stages.INDEKS_KANDYDATOW.read_text(encoding="utf-8")) == [])

    print()
    print("=== 2. PELNY BANK Z WYDARZENIEM — SZUKAMY MIMO SUFITU ===")
    korpus_kanalow.wielkie_wydarzenia = lambda *a, **kw: list(WYDARZENIE)
    stages.bank_pelny = lambda: True
    stages.INDEKS_KANDYDATOW.write_text("[]", encoding="utf-8")
    wynik = stages.znajdz_ciekawostki(None, None)
    sprawdz("wydarzenie przebilo sufit", len(wynik) == 1, wynik)
    w_indeksie = json.loads(stages.INDEKS_KANDYDATOW.read_text(encoding="utf-8"))
    sprawdz("i fakt trafil do banku", len(w_indeksie) == 1, len(w_indeksie))

    print()
    print("=== 3. PUSTY BANK BEZ WYDARZENIA — SZUKAMY NORMALNIE ===")
    # Bez tego sekcja 1 moglaby przechodzic dlatego, ze szukanie jest zepsute.
    korpus_kanalow.wielkie_wydarzenia = lambda *a, **kw: []
    stages.bank_pelny = lambda: False
    stages.INDEKS_KANDYDATOW.write_text("[]", encoding="utf-8")
    wynik = stages.znajdz_ciekawostki(None, None)
    sprawdz("zwykle szukanie dziala", len(wynik) == 1, wynik)

    print()
    print("=== 4. PROG WYDARZENIA JEST PRAWDZIWYM PROGIEM ===")
    # Pas ma sie otwierac na WYDARZENIE, nie na kazdy naglowek. To sprawdza
    # samego wykrywacza, bo to on decyduje, czy pas w ogole sie odezwie.
    korpus_kanalow.wielkie_wydarzenia = _stare_wyd
    dzis = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    dawno = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
    trzy = [{"temat": "titan seven release changes inference pricing",
             "kanal": c, "data": dzis} for c in "abc"]
    sprawdz("trzy kanaly dzis — to jest wydarzenie",
            bool(korpus_kanalow.wielkie_wydarzenia(trzy)))
    sprawdz("dwa kanaly — nie", not korpus_kanalow.wielkie_wydarzenia(trzy[:2]))
    sprawdz("trzy kanaly sprzed miesiaca — nie",
            not korpus_kanalow.wielkie_wydarzenia(
                [{**w, "data": dawno} for w in trzy]))
    jeden_glosny = [{"temat": "everything changed today believe me",
                     "kanal": "a", "data": dzis}]
    sprawdz("jeden kanal krzyczacy — nie",
            not korpus_kanalow.wielkie_wydarzenia(jeden_glosny))
finally:
    stages.WYDARZENIA_OBSLUZONE = _stara_pamiec_wyd
    stages.INDEKS_KANDYDATOW = _stary_indeks
    stages.llm.call = _stare_call
    stages.zaczyn_z_kanalow = _stary_zaczyn
    stages.bank_pelny = _stary_pelny
    stages.wczytaj_zuzyte = _stare_zuzyte
    config.przywroc_katalog_danych(_zdjecie_sciezek)
    korpus_kanalow.wielkie_wydarzenia = _stare_wyd
    korpus_kanalow.korpus_kanalow = _stary_korpus

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
