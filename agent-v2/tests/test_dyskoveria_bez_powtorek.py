# -*- coding: utf-8 -*-
"""Dyskoveria nie oddaje tego samego adresu dwa razy ani wiecej, niz wolno.

## Wada, ktora ten plik pilnuje

`config.DISCOVERY_MAX_RESULTS` szedl do promptu jako `{max_results}` i na tym
sie konczyl. Kod nie przycinal listy ANI RAZU i nie scalal powtorzonych
adresow — `return kept` oddawal wszystko, co przeszlo filtr hostow.

To nie jest wada kosmetyczna, bo nizej nikt tego nie nadrabia. `fetch` idzie
`for source in sources` bez odsiewu, wiec kazda kopia adresu to:

  * osobne pobranie TEJ SAMEJ strony,
  * osobny wpis w korpusie, czyli wieksze wejscie do PLATNEJ klasyfikacji,
  * osobne czekanie `ODSTEP_TEN_SAM_HOST_S` — kopie dziela host, wiec odstep
    chroniacy cudzy serwer mnozy sie tu za nic.

Odtworzone 5 wrzesnia 2026: przy limicie 10 przechodzilo 15 pozycji, wszystkie
wskazujace jeden URL.

## Czego ten plik pilnuje w DRUGA strone

Zeby przyciecie nie zjadalo dokumentow, po ktore prompt kaze siegac. Bierzemy
POCZATEK listy, bo docstring `discovery` opisuje mechanizm odwrotny: „gdy
dokumenty pierwotne sie koncza, dopycha liste omowieniami" — nadmiar jest
wiec ogonem, nie czolem. Sekcja 3 sprawdza, ze kolejnosc zostaje zachowana.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_dyskoveria_bez_powtorek.py
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


def atrapa(pozycje, znalezione):
    """Model oddaje `pozycje`; wyszukiwarka „znalazla" adresy `znalezione`."""
    def call(*a, **k):
        # `collect_urls` to lista, do ktorej transport dopisuje adresy
        # znalezione NAPRAWDE. Pusta znaczy „model nie szukal" i discovery
        # slusznie sie wtedy zamyka — ta zapora zostaje nietknieta.
        kolekcja = k.get("collect_urls")
        if kolekcja is not None:
            kolekcja.extend(znalezione)
        return json.dumps({"sources": pozycje})

    stages.llm = type("Atrapa", (), {
        "call": staticmethod(call),
        "parse_json": staticmethod(json.loads),
    })()


def zrodlo(u, i):
    return {"url": u, "title": "Raport %d" % i, "publisher": "Example",
            "why": "bo odpowiada na pytanie", "klasa": "PRIMARY"}


print("=== 1. POWTORZONY ADRES LICZY SIE RAZ ===")
atrapa([zrodlo("https://example.org/raport", i) for i in range(15)],
       ["https://example.org/raport"])
w = stages.discovery(CONN, 1, "Pytanie testowe", [])
sprawdz("oddana jedna pozycja", len(w) == 1, len(w))
sprawdz("i jest to ten adres", w[0]["url"] == "https://example.org/raport", w)

print()
print("=== 2. LIMIT Z KONFIGURACJI JEST EGZEKWOWANY ===")
ile = config.DISCOVERY_MAX_RESULTS
adresy = ["https://example.org/dok%d" % i for i in range(ile + 5)]
atrapa([zrodlo(u, i) for i, u in enumerate(adresy)], adresy)
w2 = stages.discovery(CONN, 1, "Pytanie testowe", [])
sprawdz("nie wiecej niz DISCOVERY_MAX_RESULTS", len(w2) == ile, (len(w2), ile))
# KONTRDOWOD: bez przyciecia byloby ich ile+5, wiec test cos znaczy tylko
# wtedy, gdy atrapa naprawde podala nadmiar.
sprawdz("(atrapa podala nadmiar)", len(adresy) > ile, len(adresy))

print()
print("=== 3. PRZYCINAMY OGON, NIE CZOLO ===")
sprawdz("zostaja pierwsze pozycje",
        [s["url"] for s in w2] == adresy[:ile], [s["url"] for s in w2][:3])

print()
print("=== 4. ZAPORA 'MODEL NIE SZUKAL' ZOSTAJE ===")
# Bez tej sekcji latwo „naprawic" limit tak, ze przy okazji rozbroi sie
# sprawdzenie, ktore chroni przed adresami z pamieci modelu.
atrapa([zrodlo("https://example.org/x", 0)], [])
try:
    stages.discovery(CONN, 1, "Pytanie testowe", [])
    sprawdz("brak wynikow wyszukiwania nadal zatrzymuje", False, "przepuscilo")
except ValueError as exc:
    sprawdz("brak wynikow wyszukiwania nadal zatrzymuje",
            "nie wykonała ani jednego wyszukiwania" in str(exc), str(exc)[:60])

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
