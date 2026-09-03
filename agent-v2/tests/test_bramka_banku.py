# -*- coding: utf-8 -*-
"""Kod sprawdza powody wyrzucenia i tnie znacznik artykulowy.

DWIE WADY ZMIERZONE NA ZYWYCH PRZEBIEGACH 30 SIERPNIA.

1. ZAKAZ W PROMPCIE PRZEGRAL DWA RAZY Z RZEDU. `bank.md` ma caly akapit
   zabraniajacy wyrzucania „za to, ze szeroko opisane, ze to premiera produktu
   albo ze mniej ciekawe niz sasiedzi", z opisem konkretnej straty: uklad
   scalony zaprojektowany w dziewiec miesiecy poszedl do kosza razem z
   komunikatem prasowym. Model wyrzucil DOKLADNIE TEN SAM fakt drugi raz,
   slowami „a widely covered product launch, not a finding". Dwa z trzech
   odrzucen lamaly reguly wlasnego promptu.

   Wiec powod przestaje byc zdaniem, a staje sie KODEM z trzech. I jeden z tych
   trzech kod potrafi sprawdzic sam: `bramka_kandydata` juz zmierzyla, ze pole
   `decision` opisuje mechanizm, wiec odrzucenie „brak mechanizmu" przeczy
   sprawdzeniu, ktore kod wykonal i zapisal.

2. ZNACZNIK ARTYKULOWY DEGENEROWAL DO STALEJ. Pytany po kolei „czy to unioslo
   by artykul", model mowil tak prawie zawsze: 7 z 13 (54%) i 14 z 21 (67%),
   przy prompcie mowiacym wprost „wiekszosc kandydatow to notki". Znacznik u
   dwoch trzecich banku nie niesie informacji, a decyduje, co idzie na drozsza
   sciezke. Kod bierze wiec KOLEJNOSC, ktorej model nie potrafi zdegenerowac.

BEZ PYTESTA. Uruchamiac z korzenia repozytorium. Zaden test tutaj nie wola
platnego modelu — `llm.call` jest podmieniony na atrape.
"""
import json
import pathlib
import sys
import tempfile
from datetime import datetime, timezone

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


MECHANIZM = ("A decision: the company chose to spend nine months designing "
             "its own inference chip rather than buying one")

katalog = pathlib.Path(tempfile.mkdtemp())
_stary_indeks = stages.INDEKS_KANDYDATOW
_stare_call = stages.llm.call
stages.INDEKS_KANDYDATOW = katalog / "indeks.json"

odpowiedz = {"tresc": ""}


def _atrapa_call(*a, **kw):
    return odpowiedz["tresc"]


stages.llm.call = _atrapa_call


def kandydat(nr, decision=MECHANIZM):
    return {"fact": "Candidate number %d about a named arrangement" % nr,
            "status": "nowy",
            "kiedy": datetime.now(timezone.utc).isoformat(),
            "decision": decision, "actually": "", "wrong_belief": "",
            "consequence": "", "url": "https://example.org/%d" % nr,
            "source_date": "2026-08-20", "domain": "test"}


def ustaw(ile, decisions=None):
    poz = [kandydat(i, (decisions or {}).get(i, MECHANIZM)) for i in range(ile)]
    stages.INDEKS_KANDYDATOW.write_text(json.dumps(poz, ensure_ascii=False),
                                        encoding="utf-8")


def odpowiedz_modelu(ile, oceny):
    odpowiedz["tresc"] = json.dumps(
        {"kolejnosc": list(range(ile)), "oceny": oceny})


def stan():
    poz = json.loads(stages.INDEKS_KANDYDATOW.read_text(encoding="utf-8"))
    return {k["fact"]: k for k in poz}


try:
    print("=== 0. ATRAPA NAPRAWDE PROSI O SKASOWANIE ===")
    # Bez tego caly plik moglby przechodzic dlatego, ze model o nic nie prosil.
    ustaw(4)
    odpowiedz_modelu(4, [
        {"id": 0, "wyrzuc": True, "kod_wyrzucenia": stages.POWODY_WYRZUCENIA[0],
         "powod_wyrzucenia": "o regulacji lekow", "na_artykul": False},
        {"id": 1, "wyrzuc": False, "kod_wyrzucenia": "", "na_artykul": False},
        {"id": 2, "wyrzuc": False, "kod_wyrzucenia": "", "na_artykul": False},
        {"id": 3, "wyrzuc": False, "kod_wyrzucenia": "", "na_artykul": False}])
    wynik = stages.posortuj_bank(None, None)
    # KOD IDZIE Z CONFIGU. Stal tu wpisany na sztywno kod jednej niszy, czyli
    # test pilnujacy BRAMKI mial nisze w ciele i oblewal sie przy jej zmianie.
    sprawdz("legalny powod %s kasuje" % stages.POWODY_WYRZUCENIA[0],
            wynik["wyrzucone"] == 1, wynik)
    sprawdz("i kandydat ma status odrzucony",
            stan()["Candidate number 0 about a named arrangement"]["status"]
            == "odrzucony")

    print()
    print("=== 1. POWOD SPOZA LISTY NIE KASUJE ===")
    # To jest przypadek z produkcji: „a widely covered product launch".
    ustaw(4)
    odpowiedz_modelu(4, [
        {"id": 0, "wyrzuc": True, "kod_wyrzucenia": "WIDELY_COVERED",
         "powod_wyrzucenia": "a widely covered product launch, not a finding",
         "na_artykul": False},
        {"id": 1, "wyrzuc": False, "kod_wyrzucenia": "", "na_artykul": False},
        {"id": 2, "wyrzuc": False, "kod_wyrzucenia": "", "na_artykul": False},
        {"id": 3, "wyrzuc": False, "kod_wyrzucenia": "", "na_artykul": False}])
    wynik = stages.posortuj_bank(None, None)
    sprawdz("nic nie skasowane", wynik["wyrzucone"] == 0, wynik)
    sprawdz("kandydat nadal nowy",
            stan()["Candidate number 0 about a named arrangement"]["status"]
            == "nowy")

    print()
    print("=== 2. PUSTY KOD TEZ NIE KASUJE ===")
    ustaw(4)
    odpowiedz_modelu(4, [
        {"id": 0, "wyrzuc": True, "kod_wyrzucenia": "",
         "powod_wyrzucenia": "slabszy niz sasiedzi", "na_artykul": False},
        {"id": 1, "wyrzuc": False, "na_artykul": False},
        {"id": 2, "wyrzuc": False, "na_artykul": False},
        {"id": 3, "wyrzuc": False, "na_artykul": False}])
    sprawdz("nic nie skasowane", stages.posortuj_bank(None, None)["wyrzucone"] == 0)

    print()
    print("=== 3. NO_MECHANISM PRZECZY POMIAROWI KODU ===")
    # `bramka_kandydata` juz zmierzyla to pole. Kod ma swoj pomiar.
    ustaw(4)
    odpowiedz_modelu(4, [
        {"id": 0, "wyrzuc": True, "kod_wyrzucenia": "NO_MECHANISM",
         "powod_wyrzucenia": "brak mechanizmu", "na_artykul": False},
        {"id": 1, "wyrzuc": False, "na_artykul": False},
        {"id": 2, "wyrzuc": False, "na_artykul": False},
        {"id": 3, "wyrzuc": False, "na_artykul": False}])
    sprawdz("z opisanym mechanizmem NIE kasuje",
            stages.posortuj_bank(None, None)["wyrzucone"] == 0)

    print()
    print("=== 4. ALE PRZY PUSTYM `decision` KASUJE ===")
    # Kontrdowod do sekcji 3: gdyby NO_MECHANISM bylo martwe zawsze, sekcja 3
    # niczego by nie dowodzila.
    ustaw(4, decisions={0: ""})
    odpowiedz_modelu(4, [
        {"id": 0, "wyrzuc": True, "kod_wyrzucenia": "NO_MECHANISM",
         "powod_wyrzucenia": "brak mechanizmu", "na_artykul": False},
        {"id": 1, "wyrzuc": False, "na_artykul": False},
        {"id": 2, "wyrzuc": False, "na_artykul": False},
        {"id": 3, "wyrzuc": False, "na_artykul": False}])
    sprawdz("bez mechanizmu kasuje",
            stages.posortuj_bank(None, None)["wyrzucone"] == 1)
    ustaw(4, decisions={0: "nobody decided"})
    odpowiedz_modelu(4, [
        {"id": 0, "wyrzuc": True, "kod_wyrzucenia": "NO_MECHANISM",
         "powod_wyrzucenia": "gest zamiast mechanizmu", "na_artykul": False},
        {"id": 1, "wyrzuc": False, "na_artykul": False},
        {"id": 2, "wyrzuc": False, "na_artykul": False},
        {"id": 3, "wyrzuc": False, "na_artykul": False}])
    sprawdz("krotki gest tez kasuje",
            stages.posortuj_bank(None, None)["wyrzucone"] == 1)

    print()
    print("=== 5. SUFIT ZNACZNIKA ARTYKULOWEGO ===")
    ustaw(10)
    odpowiedz_modelu(10, [{"id": i, "wyrzuc": False, "na_artykul": True,
                           "dlaczego_mocny": "x"} for i in range(10)])
    stages.posortuj_bank(None, None)
    po = list(stan().values())
    art = [k for k in po if k.get("na_artykul")]
    limit = max(1, int(10 * config.BANK_UDZIAL_ARTYKULOW))
    sprawdz("model chcial 10, zostaje %d" % limit, len(art) == limit,
            len(art))
    sprawdz("zostaly te z czola kolejnosci",
            sorted(k["ranga"] for k in art) == list(range(limit)),
            sorted(k["ranga"] for k in art))

    print()
    print("=== 6. SKROMNY MODEL NIE JEST PODCIAGANY W GORE ===")
    # Sufit tnie, ale nie dosypuje. Gdyby dosypywal, byloby to zgadywanie.
    ustaw(10)
    odpowiedz_modelu(10, [{"id": i, "wyrzuc": False,
                           "na_artykul": i == 4, "dlaczego_mocny": "x"}
                          for i in range(10)])
    stages.posortuj_bank(None, None)
    art = [k for k in stan().values() if k.get("na_artykul")]
    sprawdz("jeden oznaczony zostaje jednym", len(art) == 1, len(art))

    print()
    print("=== 7. ZAPORA NA MASOWE KASOWANIE NADAL DZIALA ===")
    ustaw(6, decisions={i: "" for i in range(6)})
    odpowiedz_modelu(6, [{"id": i, "wyrzuc": True,
                          "kod_wyrzucenia": "NO_MECHANISM",
                          "powod_wyrzucenia": "brak", "na_artykul": False}
                         for i in range(6)])
    sprawdz("proba skasowania calej partii nic nie kasuje",
            stages.posortuj_bank(None, None)["wyrzucone"] == 0)
finally:
    stages.INDEKS_KANDYDATOW = _stary_indeks
    stages.llm.call = _stare_call

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
