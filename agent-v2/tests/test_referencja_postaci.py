# -*- coding: utf-8 -*-
"""Ten sam wzorzec postaci na kazdej okladce — albo czysty powrot do opisu.

## Po co

Sam opis slowny nie buduje rozpoznawalnej postaci. „Ciemne, krotkie, faliste
wlosy, tailorowany garnitur" oddaje za kazdym wywolaniem inna kobiete, a przy
jednej okladce tygodniowo konto nigdy nie zbierze z tego jednej twarzy.
Zmierzone 9 wrzesnia 2026: dwa obrazy tego samego artykulu 0028 nie mialy
w ogole postaci, a te z artykulow wczesniejszych pokazywaly za kazdym razem
kogos innego.

Generator przyjmuje obraz wzorcowy, ale TYLKO na innym adresie:
`/v1/images/generations` nie zna pola z obrazem, a `/v1/images/edits` wymaga
`multipart/form-data`. Projekt nie ma `requests`, wiec cialo skladamy sami.

## Czego pilnuje ten plik

1. Bez pliku NIC SIE NIE ZMIENIA. Wskazana, ale nieistniejaca referencja nie
   moze zabic etapu grafiki — obraz ma powstac z samego opisu, a przebieg ma
   o tym powiedziec. Grafika nigdy nie zabija artykulu.
2. Cialo `multipart` jest skladane poprawnie: granica, pola, plik, zamkniecie.
3. Wzorzec dostaja OBA obrazy. Referencja tylko na okladce zostawilaby drugi
   obraz z inna postacia, czyli nie rozwiazalaby niczego.
4. Sciezka nalezy do KARTRIDZA i rozwiazuje sie wzgledem jego katalogu.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_referencja_postaci.py
"""
import inspect
import io
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "agent-v2")
import config  # noqa: E402
import llm     # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


print("=== 1. CIALO MULTIPART JEST POPRAWNE ===")
PNG = b"\x89PNG\r\n\x1a\n" + b"BINARNE\x00\xff\r\n--DANE"
cialo, typ = llm._multipart(
    {"model": "gpt-image-2", "prompt": "scena", "n": "1"},
    {"image[]": ("referencja.png", PNG)})
granica = typ.split("boundary=")[1]
sprawdz("typ zawiera granice", typ.startswith("multipart/form-data; boundary="))
sprawdz("granica wystepuje w ciele", granica.encode() in cialo)
sprawdz("pole tekstowe ma nazwe", b'name="prompt"' in cialo)
sprawdz("wartosc pola przeszla", b"scena" in cialo)
sprawdz("plik ma nazwe i typ",
        b'filename="referencja.png"' in cialo and b"Content-Type: image/png" in cialo)
sprawdz("dane binarne nietkniete", PNG in cialo, len(cialo))
sprawdz("cialo domkniete znacznikiem konca",
        cialo.rstrip().endswith(b"--"), cialo[-30:])
# GRANICA NIE MOZE TRAFIC W DANE. Stad losowy przyrostek: gdyby byla stala,
# obraz zawierajacy ten ciag rozwalilby zadanie.
c2, t2 = llm._multipart({"a": "b"}, {})
sprawdz("kazde wywolanie ma inna granice",
        t2.split("boundary=")[1] != granica)

print()
print("=== 2. BEZ PLIKU NIC SIE NIE ZMIENIA ===")
sprawdz("`obraz` przyjmuje referencje",
        "referencja" in inspect.signature(llm.obraz).parameters)
sprawdz("i domyslnie jest pusta",
        inspect.signature(llm.obraz).parameters["referencja"].default == "")
zrodlo = io.open("agent-v2/llm.py", encoding="utf-8").read()
sprawdz("brakujacy plik nie rzuca, tylko mowi",
        "referencja wskazana, ale pliku nie ma" in zrodlo)
i = zrodlo.index("_ref = Path(referencja) if referencja else None")
sprawdz("i po ostrzezeniu wraca na stara droge",
        "_ref = None" in zrodlo[i:i + 400], zrodlo[i:i + 400])
sprawdz("stary adres nadal uzywany, gdy nie ma wzorca",
        "v1/images/generations" in zrodlo)
sprawdz("nowy adres tylko z wzorcem", "v1/images/edits" in zrodlo)
# ADRES W CUDZYSLOWIE, nie w komentarzu. Pierwsza wersja szukala samego
# napisu i trafiala w akapit wyjasniajacy, ktory stoi WYZEJ niz kod — wiec
# wycinek byl pusty i sprawdzenie oblewalo bez powodu.
j = zrodlo.index("'https://api.openai.com/v1/images/edits'")
sprawdz("edits stoi pod warunkiem obecnosci pliku",
        "if _ref is not None:" in zrodlo[i:j], zrodlo[i:j][-200:])

print()
print("=== 3. WZORZEC DOSTAJA OBA OBRAZY ===")
st = io.open("agent-v2/stages.py", encoding="utf-8").read()
sprawdz("dwa wywolania generatora", st.count("llm.obraz(opis") == 2,
        st.count("llm.obraz(opis"))
sprawdz("oba podaja referencje", st.count("referencja=str(getattr(config") == 2,
        st.count("referencja=str(getattr(config"))

print()
print("=== 4. SCIEZKA NALEZY DO KARTRIDZA ===")
sprawdz("silnik ma pustą wartosc domyslna",
        hasattr(config, "OBRAZ_REFERENCJA"))
kf = io.open("agent-v2/konfiguracja.py", encoding="utf-8").read()
sprawdz("pole jest w schemacie presetu", '"styl.referencja"' in kf)
sprawdz("i mapuje sie na stala silnika", "OBRAZ_REFERENCJA" in kf)
pr = io.open("agent-v2/preset.py", encoding="utf-8").read()
sprawdz("rozwiazywana wzgledem katalogu kartridza",
        '"styl.referencja"' in pr and "_POLA_SCIEZEK" in pr)

print()
print("=== 5. KTORY ADRES NAPRAWDE ZOSTAJE WYWOLANY ===")
# PIERWSZA WERSJA TEJ SEKCJI NIE MIERZYLA NICZEGO. Wolala `llm.obraz`
# z `DRY_RUN = True`, a ten warunek konczy funkcje ZANIM kod dojdzie do
# referencji — wiec test przechodzilby tak samo z poprawka i bez niej.
#
# Teraz podstawiamy siec i patrzymy, pod jaki adres poszlo zadanie.
import base64 as _b64          # noqa: E402
import json as _js            # noqa: E402
import urllib.request as _url  # noqa: E402

ODPOWIEDZ = _js.dumps({"data": [{"b64_json": _b64.b64encode(b"OBRAZ").decode()}],
                       "usage": {}}).encode("utf-8")


class _Odp:
    def read(self):
        return ODPOWIEDZ

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _przechwyc():
    """Podstawia siec i ksiegowanie; oddaje liste adresow, pod ktore poszlo."""
    adresy = []

    def urlopen(req, timeout=None):
        adresy.append(req.full_url)
        return _Odp()

    stare = (_url.urlopen, llm._preflight, llm._reserve_attempt,
             llm._settle_image, llm.runtime.watch, llm.runtime.invoke)
    _url.urlopen = urlopen
    llm._preflight = lambda *a, **k: None
    llm._reserve_attempt = lambda *a, **k: (1, None, None)
    llm._settle_image = lambda *a, **k: 0.2
    llm.runtime.watch = lambda *a, **k: None
    llm.runtime.invoke = lambda stan, fn: fn()
    return adresy, stare


def _przywroc(stare):
    (_url.urlopen, llm._preflight, llm._reserve_attempt,
     llm._settle_image, llm.runtime.watch, llm.runtime.invoke) = stare


stary_dry = config.DRY_RUN
config.DRY_RUN = False
try:
    # BEZ REFERENCJI — stary adres.
    adresy, stare = _przechwyc()
    try:
        llm.obraz("scena", conn=None, run_id=None)
    finally:
        _przywroc(stare)
    sprawdz("bez wzorca idzie na `generations`",
            adresy and adresy[-1].endswith("/v1/images/generations"), adresy)

    # ZE WSKAZANA, ALE NIEISTNIEJACA — te sama droga, bez wyjatku.
    with tempfile.TemporaryDirectory() as kat:
        brak = str(Path(kat) / "nie-ma-mnie.png")
        adresy, stare = _przechwyc()
        try:
            llm.obraz("scena", conn=None, run_id=None, referencja=brak)
        finally:
            _przywroc(stare)
        sprawdz("brakujacy plik nie przerywa i wraca na `generations`",
                adresy and adresy[-1].endswith("/v1/images/generations"), adresy)

        # Z ISTNIEJACYM PLIKIEM — nowy adres.
        jest = Path(kat) / "referencja.png"
        jest.write_bytes(b"\x89PNG\r\n\x1a\nWZORZEC")
        adresy, stare = _przechwyc()
        try:
            wynik = llm.obraz("scena", conn=None, run_id=None, referencja=str(jest))
        finally:
            _przywroc(stare)
        sprawdz("z wzorcem idzie na `edits`",
                adresy and adresy[-1].endswith("/v1/images/edits"), adresy)
        sprawdz("i oddaje obraz, nie pustke", wynik == b"OBRAZ", repr(wynik)[:40])
finally:
    config.DRY_RUN = stary_dry

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
