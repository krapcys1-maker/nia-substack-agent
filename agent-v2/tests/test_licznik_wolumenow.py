"""Licznik dzialan: ile czego wyszlo wobec normy, i alarm gdy jest za malo.

NAJTRUDNIEJSZA DO ZAUWAZENIA KLASA AWARII. Nic sie nie wywala, log wyglada
normalnie, przebieg konczy sie `DONE`, a polowa dzialan nie wychodzi. Zmierzone
na osmiu dniach produkcji, gdy ta kontrola powstawala:

    notki       23 z ~40   58%
    komentarze  44 z ~80   55%
    polubienia  70 z ~104  67%
    restacki     4 z ~12   33%

Nikt tego nie wiedzial przez dwa tygodnie. Dziennik dzialan zapisywal wszystko
od poczatku i nikt go nie czytal; licznik `zrobione` zyl w pamieci jednego
przebiegu, drukowal sie na koncu i ginal razem z nim. Norma bez pomiaru jest
zyczeniem.

Osobno: `id_z_odpowiedzi`. Dziennik zapisywal „wystawilismy notke o trybie
samolotowym" i — osobno — „notka 315733831 zebrala trzy polubienia", bez pola,
po ktorym da sie stwierdzic, czy to ta sama. Braklo jednej rzeczy: z odpowiedzi
Substacka bralismy WYLACZNIE kod HTTP, a tresc z identyfikatorem szla do kosza.
"""
import json
import pathlib
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "agent-v2")
import config    # noqa: E402
import stages    # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


def _kiedy(dni_temu):
    return (datetime.now(timezone.utc) - timedelta(days=dni_temu)).isoformat()


def _dziennik(katalog, wpisy):
    p = pathlib.Path(katalog)
    (p / "dziennik.jsonl").write_text(
        "\n".join(json.dumps(w) for w in wpisy), encoding="utf-8")
    return p


def _z_dziennikiem(wpisy, dni=7):
    with tempfile.TemporaryDirectory() as tmp:
        _zdjecie = config.uzyj_katalogu_danych(_dziennik(tmp, wpisy))
        try:
            return stages.podsumowanie_dzialan(dni)
        finally:
            config.przywroc_katalog_danych(_zdjecie)


print("=== 1. LICZY TO, CO WYSZLO ===")
wpisy = ([{"rodzaj": "notka", "udane": True, "kiedy": _kiedy(1)}] * 10
         + [{"rodzaj": "notka", "udane": False, "kiedy": _kiedy(1)}] * 2
         + [{"rodzaj": "komentarz", "udane": True, "kiedy": _kiedy(2)}]
         * int(config.normy_dzienne()["komentarz"] * 7))
d = _z_dziennikiem(wpisy)
sprawdz("liczy udane", d["notka"]["udane"] == 10, d.get("notka"))
sprawdz("i osobno nieudane", d["notka"]["nieudane"] == 2, d.get("notka"))
sprawdz("dzieli przez liczbe dni", d["notka"]["na_dzien"] == round(10 / 7, 2),
        d["notka"]["na_dzien"])
sprawdz("norma pochodzi z configu",
        d["notka"]["norma"] == config.normy_dzienne()["notka"])
# Tyle komentarzy, ile wynosi norma razy siedem dni — czyli dokladnie 100%.
# LICZBA POCHODZI Z CONFIGU, nie jest wpisana na sztywno: norma zmienila sie
# 30 sierpnia z 10 na 19 i wpisane 70 zaczelo znaczyc 53 procent zamiast stu.
# Test ma sprawdzac, czy licznik dobrze DZIELI, a nie pamietac stara norme.
sprawdz("realizacja liczona wobec normy", d["komentarz"]["realizacja"] == 100,
        d["komentarz"])

print()
print("=== 2. CUDZE REAKCJE TO NIE NASZE DZIALANIA ===")
# `skutek` to polubienia, ktore ktos dal NAM. Liczenie ich razem z notkami
# dawaloby licznik rosnacy, gdy ktos nas lubi — czyli miare popularnosci
# udajaca miare pracy.
d = _z_dziennikiem([{"rodzaj": "skutek", "typ": "note_like", "udane": True,
                     "kiedy": _kiedy(1)}] * 50
                   + [{"rodzaj": "notka", "udane": True, "kiedy": _kiedy(1)}])
sprawdz("skutki nie sa liczone", "skutek" not in d, sorted(d))
sprawdz("a nasze notki tak", d["notka"]["udane"] == 1)

print()
print("=== 3. OKNO CZASU DZIALA ===")
d = _z_dziennikiem([{"rodzaj": "notka", "udane": True, "kiedy": _kiedy(1)}] * 3
                   + [{"rodzaj": "notka", "udane": True, "kiedy": _kiedy(30)}] * 99)
sprawdz("stare wpisy nie wchodza do okna 7 dni", d["notka"]["udane"] == 3,
        d["notka"]["udane"])
# KONTRDOWOD: przy szerszym oknie MUSZA sie pojawic, inaczej filtr odcina
# wszystko i licznik zawsze pokazuje zero.
d2 = _z_dziennikiem([{"rodzaj": "notka", "udane": True, "kiedy": _kiedy(30)}] * 99,
                    dni=60)
sprawdz("ale przy szerszym oknie owszem", d2["notka"]["udane"] == 99,
        d2["notka"]["udane"])

print()
print("=== 4. RODZAJ BEZ NORMY TEZ JEST WIDOCZNY ===")
d = _z_dziennikiem([{"rodzaj": "odpowiedz", "udane": True, "kiedy": _kiedy(1)}] * 5)
sprawdz("odpowiedzi sa liczone", d["odpowiedz"]["udane"] == 5)
sprawdz("ale bez procentu, bo nie maja kontraktu",
        d["odpowiedz"]["realizacja"] is None, d["odpowiedz"])
# Rodzaj z norma, ktorego W OGOLE nie bylo, ma sie pokazac jako zero —
# to jest wlasnie przypadek „nie komentujemy wcale".
sprawdz("rodzaj z norma, ktorego nie bylo, pokazuje sie jako zero",
        d.get("komentarz", {}).get("udane") == 0 and d["komentarz"]["realizacja"] == 0,
        d.get("komentarz"))

print()
print("=== 5. ALARM MILCZY PRZY NORMIE, KRZYCZY PRZY POLOWIE ===")
import alarm   # noqa: E402

normy = config.normy_dzienne()


def _wolumeny(mnoznik):
    """Dziennik z dzialaniami na `mnoznik` normy przez siedem dni."""
    wpisy = []
    for rodzaj, norma in normy.items():
        for _ in range(int(round(norma * 7 * mnoznik))):
            wpisy.append({"rodzaj": rodzaj, "udane": True, "kiedy": _kiedy(1)})
    with tempfile.TemporaryDirectory() as tmp:
        _zdjecie = config.uzyj_katalogu_danych(_dziennik(tmp, wpisy))
        try:
            return alarm.wolumeny()
        finally:
            config.przywroc_katalog_danych(_zdjecie)


sprawdz("przy 100% normy alarm milczy", _wolumeny(1.0) is None, _wolumeny(1.0))
sprawdz("przy 90% tez — wahania to normalna praca", _wolumeny(0.9) is None)
w = _wolumeny(0.4)
sprawdz("przy 40% alarm mowi", bool(w), w)
sprawdz("i wymienia rodzaje z procentami",
        w and "%" in w and any(r in w for r in normy), (w or "")[:90])
sprawdz("i nazywa rzecz po imieniu: tego nie widac w logu",
        w and "nie widac w logu" in w)
# Prog jest stala, nie liczba w kodzie kontroli.
sprawdz("prog stoi w configu", isinstance(config.PROG_ALARMU_WOLUMENU, int))
# Pusty dziennik to brak danych, nie alarm o zerze — inaczej pierwszy dzien
# po instalacji zawsze krzyczy.
with tempfile.TemporaryDirectory() as tmp:
    _zdjecie = config.uzyj_katalogu_danych(pathlib.Path(tmp))
    try:
        sprawdz("pusty dziennik to cisza, nie alarm", alarm.wolumeny() is None)
    finally:
        config.przywroc_katalog_danych(_zdjecie)

print()
print("=== 6. ID NOTKI Z ODPOWIEDZI SUBSTACKA ===")
import browser   # noqa: E402


class Odp:
    def __init__(self, status, dane=None, rzuca=False):
        self.status, self._dane, self._rzuca = status, dane, rzuca

    def json(self):
        if self._rzuca:
            raise ValueError("nie JSON")
        return self._dane


sprawdz("czyta id z korzenia", browser.id_z_odpowiedzi([Odp(200, {"id": 318233860})])
        == "318233860")
sprawdz("i z zagniezdzenia `comment`",
        browser.id_z_odpowiedzi([Odp(200, {"comment": {"id": 7}})]) == "7")
sprawdz("i z `item`", browser.id_z_odpowiedzi([Odp(200, {"item": {"id": 9}})]) == "9")
# KONTRDOWODY: brak id nie moze byc bledem — notka wyszla albo nie wyszla
# niezaleznie od tego, czy umiemy ja pozniej odnalezc.
sprawdz("odpowiedz 500 jest pomijana", browser.id_z_odpowiedzi([Odp(500, {"id": 1})]) == "")
sprawdz("nieparsowalna tresc nie wywala",
        browser.id_z_odpowiedzi([Odp(200, None, rzuca=True)]) == "")
sprawdz("brak pola id oddaje pusty napis",
        browser.id_z_odpowiedzi([Odp(200, {"co_innego": 1})]) == "")
sprawdz("pusta lista tez", browser.id_z_odpowiedzi([]) == "")
sprawdz("bierze pierwsza dobra, gdy jest kilka odpowiedzi",
        browser.id_z_odpowiedzi([Odp(500, {"id": 1}), Odp(200, {"id": 2})]) == "2")

zrodlo = pathlib.Path("agent-v2/browser.py").read_text(encoding="utf-8")
sprawdz("id trafia do dziennika przy notce",
        'dopisz_wynik("notka"' in zrodlo and 'id=wynik["id"]' in zrodlo)
sprawdz("i log mowi, gdy id sie nie udalo odczytac",
        "NIE ODCZYTANY" in zrodlo)
# Ciala odpowiedzi czytamy PO odczekaniu, nie w callbacku zdarzenia.
sprawdz("nasluch zbiera odpowiedzi, nie same kody",
        "odpowiedzi.append(r)" in zrodlo and "kody.append(r.status)" not in zrodlo)

print()
print("=== 7. POWODY PORAZEK SA ZAPISYWANE I GRUPOWANE ===")
# Sam licznik mowi „3 nieudane komentarze" i na tym konczy pomoc. Do niedawna
# odpowiedzi na „dlaczego" nie bylo w ogole: porazki albo szly tylko do logu
# przebiegu (polubienia, restacki), albo nie zostawialy sladu, bo zapis do
# dziennika stal WEWNATRZ `try`, a wyjatek byl lapany nizej.
wpisy = (
    [{"rodzaj": "komentarz", "udane": False, "kiedy": _kiedy(1),
      "powod": "TimeoutError: locator.click"}] * 3
    + [{"rodzaj": "komentarz", "udane": False, "kiedy": _kiedy(2),
        "powod": "TimeoutError: inny adres, ta sama klasa"}] * 2
    + [{"rodzaj": "polubienie", "udane": False, "kiedy": _kiedy(1),
        "powod": "nie znalazlem przycisku wysylki"}]
    + [{"rodzaj": "notka", "udane": True, "kiedy": _kiedy(1)}]
)
with tempfile.TemporaryDirectory() as tmp:
    _zdjecie = config.uzyj_katalogu_danych(_dziennik(tmp, wpisy))
    try:
        powody = stages.powody_porazek(7)
    finally:
        config.przywroc_katalog_danych(_zdjecie)
jako_slownik = {(r, p): n for r, p, n in powody}
sprawdz("porazki sa liczone", bool(powody), powody)
# Dwa rozne timeouty tej samej klasy maja sie ZLICZYC, inaczej kazdy blad
# z innym adresem bylby osobna pozycja i lista przestalaby grupowac.
sprawdz("ten sam rodzaj bledu jest grupowany",
        jako_slownik.get(("komentarz", "TimeoutError")) == 5, powody)
sprawdz("inny rodzaj dzialania osobno",
        jako_slownik.get(("polubienie", "nie znalazlem przycisku wysylki")) == 1,
        powody)
sprawdz("najczestszy powod jest pierwszy", powody[0][2] == 5, powody[0])
# KONTRDOWODY: sukcesy i cudze reakcje nie moga wpasc na te liste.
sprawdz("udane dzialania nie sa powodem porazki",
        all(r != "notka" for r, _, _ in powody), powody)
with tempfile.TemporaryDirectory() as tmp:
    _zdjecie = config.uzyj_katalogu_danych(
        _dziennik(tmp, [{"rodzaj": "skutek", "udane": False,
                         "kiedy": _kiedy(1), "powod": "x"}]))
    try:
        sprawdz("cudze reakcje nie sa naszymi porazkami",
                stages.powody_porazek(7) == [])
    finally:
        config.przywroc_katalog_danych(_zdjecie)
# Porazka bez zapisanego powodu ma byc WIDOCZNA jako brak powodu, nie pominieta.
with tempfile.TemporaryDirectory() as tmp:
    _zdjecie = config.uzyj_katalogu_danych(
        _dziennik(tmp, [{"rodzaj": "notka", "udane": False,
                         "kiedy": _kiedy(1)}]))
    try:
        w = stages.powody_porazek(7)
        sprawdz("porazka bez powodu nadal sie liczy",
                w and w[0][1] == "nie zapisano powodu", w)
    finally:
        config.przywroc_katalog_danych(_zdjecie)

print()
print("=== 8. KAZDE DZIALANIE ZOSTAWIA SLAD, TAKZE NIEUDANE ===")
zr = pathlib.Path("agent-v2/browser.py").read_text(encoding="utf-8")
sprawdz("jest pomocnik zapisujacy takze porazke", "def dopisz_wynik(" in zr)
sprawdz("zapis jest idempotentny", '_zapisane' in zr)
sprawdz("i dokleja powod", 'szczegoly["powod"]' in zr)
sprawdz("nazywa brak przycisku po imieniu",
        "nie znalazlem przycisku wysylki" in zr)
# NAJWAZNIEJSZE: notka ma trafic do dziennika takze wtedy, gdy poleci wyjatek
# albo gdy nie bylo przycisku — domkniecie stoi w `finally`.
sprawdz("notka domykana takze przy wyjatku",
        zr.count('dopisz_wynik("notka", wynik') >= 2,
        zr.count('dopisz_wynik("notka", wynik'))
# Polubienia i restacki: porazka pojedynczego kliknnięcia tez ma slad.
sprawdz("polubienie zapisuje porazke",
        'zapisz_w_dzienniku("polubienie", udane=False' in zr)
sprawdz("restack zapisuje porazke",
        'zapisz_w_dzienniku("restack", udane=False' in zr)
# KONTRDOWOD: nie moze zostac zadnego zapisu, ktory omija pomocnika przy
# dzialaniach publikujacych tresc.
for rodzaj in ("notka", "komentarz", "odpowiedz", "artykul"):
    sprawdz("  %s idzie przez pomocnika" % rodzaj,
            ('zapisz_w_dzienniku("%s", udane=' % rodzaj) not in zr)

print()
print("=== 9. BOT NIE MOZE WYGLADAC JAK BOT ===")
# Czlowiek nie ma normy: raz przeczyta pol kanalu, raz nic. Stala liczba
# dziennie jest podpisem maszyny widocznym na osi czasu bez zadnej analizy.
#
# Zmierzone na dzienniku produkcji: restacki wychodzily 1, 1, 1, 1 —
# ODCHYLENIE STANDARDOWE ZERO. Przyczyna byla arytmetyczna, nie losowa:
# regula rozbiegu `gora = dol + (gora - dol) // 2` przy widelkach (1, 2)
# dawala `1 + 0 = 1`, czyli randint(1, 1). Kazde widelki szerokosci jeden
# byly w rozbiegu STALA.
import inspect   # noqa: E402

zrodlo_budzetu = inspect.getsource(stages.budzet_dnia)
sprawdz("rozbieg nie zapada widelek w punkt",
        "max(polowa, dol + 1)" in zrodlo_budzetu)
sprawdz("i budzet losuje sie raz na dobe, z ziarnem z daty",
        "nia-budzet-dnia" in zrodlo_budzetu)


def _rozbieg(dol, gora):
    """Odtwarza regule rozbiegu z kodu."""
    polowa = dol + (gora - dol) // 2
    return (dol, min(gora, max(polowa, dol + 1))) if gora > dol else (dol, gora)


for nazwa, widelki in (("restacki", config.RESTACK_DZIENNIE),
                       ("lajki", config.LAJKI_DZIENNIE),
                       ("komentarze", config.KOMENTARZE_DZIENNIE)):
    d, g = _rozbieg(*widelki)
    sprawdz("  %s maja w rozbiegu WIECEJ NIZ JEDNA mozliwosc" % nazwa, g > d,
            "(%d, %d)" % (d, g))
# KONTRDOWOD: stara regula MUSI zapadac sie dla restackow, inaczej naprawa
# byla zbedna i ten test niczego nie pilnuje.
_dol, _gora = config.RESTACK_DZIENNIE
sprawdz("stara regula zapadala sie dla restackow",
        _dol + (_gora - _dol) // 2 == _dol)
# Rozbieg ma nadal OBNIZAC srednia — to jest jego cala funkcja.
_d, _g = _rozbieg(*config.LAJKI_DZIENNIE)
sprawdz("rozbieg nadal scina gore", _g < config.LAJKI_DZIENNIE[1], (_d, _g))

# TEN SAM DZIEN = TEN SAM BUDZET, kolejne dni = rozne.
import datetime as _dt   # noqa: E402
import random as _r      # noqa: E402


def _budzet(data, widelki):
    return _r.Random("%s|nia-budzet-dnia" % data).randint(*widelki)


sprawdz("trzy przebiegi tego samego dnia licza to samo",
        len({_budzet("2026-09-15", (1, 2)) for _ in range(3)}) == 1)
seria = [_budzet((_dt.date(2026, 9, 1) + _dt.timedelta(days=i)).isoformat(), (1, 2))
         for i in range(60)]
sprawdz("a przez 60 dni wypadaja obie wartosci", len(set(seria)) == 2,
        sorted(set(seria)))
sprawdz("i zadna nie dominuje razaco", 15 <= seria.count(1) <= 45,
        "%d razy 1 na 60" % seria.count(1))

# LICZNIK MIERZY, NIE STERUJE. Norma to srodek widelek i sluzy WYLACZNIE
# porownaniu — gdyby agent do niej dazyl, sam by sie wyprostowal w stala.
sprawdz("norma to srodek widelek, nie cel",
        config.normy_dzienne()["restack"] == sum(config.RESTACK_DZIENNIE) / 2)
sprawdz("i nic w potoku jej nie czyta",
        "normy_dzienne" not in pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8"))

print()
print("=== 10. NAZWY NORM ZGADZAJA SIE Z NAZWAMI W DZIENNIKU ===")
# MOJ WLASNY BLAD, zlapany godzine po napisaniu licznika. Norma nazywala sie
# "follow", a `browser.obserwuj_profil` zapisuje "obserwacja" — licznik
# porownywal wiec norme z NICZYM i pokazal 0% przy bloku, ktory dziala.
# Falszywy alarm z narzedzia, ktore ma lapac falszywe spokoje, jest gorszy
# niz brak narzedzia.
import ast as _ast2   # noqa: E402

_br = pathlib.Path("agent-v2/browser.py").read_text(encoding="utf-8")
_rodzaje = set()
for _w in _ast2.walk(_ast2.parse(_br)):
    if not isinstance(_w, _ast2.Call):
        continue
    _nazwa = getattr(_w.func, "id", "")
    # `dopisz_wynik("notka", ...)` i `zapisz_w_dzienniku("polubienie", ...)`
    if _nazwa in ("dopisz_wynik", "zapisz_w_dzienniku") and _w.args:
        if isinstance(_w.args[0], _ast2.Constant) and isinstance(_w.args[0].value, str):
            _rodzaje.add(_w.args[0].value)
    # `_klik_na_profilu(handle, napisy, "obserwacja", wyslij)` — rodzaj trzeci.
    if _nazwa == "_klik_na_profilu" and len(_w.args) >= 3:
        if isinstance(_w.args[2], _ast2.Constant) and isinstance(_w.args[2].value, str):
            _rodzaje.add(_w.args[2].value)

sprawdz("znalazlem rodzaje zapisywane w kodzie", len(_rodzaje) >= 6, sorted(_rodzaje))
_bez_pokrycia = sorted(set(config.normy_dzienne()) - _rodzaje)
sprawdz("kazda norma ma odpowiadajacy rodzaj w dzienniku",
        not _bez_pokrycia, _bez_pokrycia)
# KONTRDOWOD: gdyby wykrywacz zbieral wszystko jak leci, powyzsze przeszloby
# zawsze. Nazwa, ktorej w kodzie NIE MA, musi zostac wychwycona.
sprawdz("nazwa spoza kodu bylaby zlapana", "follow" not in _rodzaje, sorted(_rodzaje))

print()
print("=== 11. BRAK PRZYCISKU TO TEZ WYNIK ===")
# Blok obserwacji chodzil po profilach przez siedem dni, za kazdym razem nie
# znajdowal przycisku „Follow" i odchodzil z pustymi rekami — BEZ WPISU.
# W dzienniku wygladalo to jak blok, ktory sie nie odbyl. Tego nie da sie
# naprawic, czego nie widac.
sprawdz("brak przycisku domykany w `finally`",
        _br.count("dopisz_wynik(rodzaj, wynik, komu=handle)") >= 2,
        _br.count("dopisz_wynik(rodzaj, wynik, komu=handle)"))
sprawdz("i powod nazywa brakujacy przycisk",
        'f"nie ma przycisku {rodzaj} u {handle}"' in _br)

print()
print("=== 12. PRACA POD NORMA KOMENTARZY LICZY SIE JAKO KOMENTARZ ===")
# Wejscie w dyskusje pod CUDZA notka to komentarz: bierze miejsce z dziennego
# budzetu komentarzy, zjada rytm komentarzy i jest ta sama praca co komentarz
# pod cudzym artykulem. Do dziennika szlo jednak jako `odpowiedz`, czyli do
# kategorii BEZ normy — bo obsluguje je ta sama funkcja, co odpowiadanie u
# siebie w watku.
#
# Zmierzone na produkcji, siedem dni: 29 wpisow `odpowiedz`, z czego 23 mialy
# kontekst cudzego celu, czyli byly komentarzami. Licznik raportowal 30%
# realizacji normy komentarzy; realnie bylo 63%. Alarm „agent robi mniej niz
# deklaruje" w tej czesci nie mowil o agencie, tylko o wlasnym bledzie.
import ast as _ast

_run = pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8")
_drzewo = _ast.parse(_run)

def _znajdz(nazwa, wezel):
    for w in _ast.walk(wezel):
        if isinstance(w, (_ast.FunctionDef, _ast.AsyncFunctionDef)) and w.name == nazwa:
            return w
    return None

def _rodzaj_w(wezel):
    """Jakie `rodzaj=` przekazuja wywolania wystaw_odpowiedz w tym wezle."""
    z = []
    for w in _ast.walk(wezel):
        if not isinstance(w, _ast.Call):
            continue
        f = w.func
        if not (isinstance(f, _ast.Attribute) and f.attr == "wystaw_odpowiedz"):
            continue
        podane = None
        for kw in w.keywords:
            if kw.arg == "rodzaj" and isinstance(kw.value, _ast.Constant):
                podane = kw.value.value
        z.append(podane)
    return z

_dyskusje = _znajdz("dyskusje", _drzewo)
sprawdz("blok dyskusji istnieje w cyklu", _dyskusje is not None)

_w_dyskusjach = _rodzaj_w(_dyskusje) if _dyskusje else []
sprawdz("dyskusje wystawiaja dokladnie jedna odpowiedz", len(_w_dyskusjach) == 1,
        _w_dyskusjach)
sprawdz("i mowia, ze to KOMENTARZ", _w_dyskusjach == ["komentarz"], _w_dyskusjach)

_normy = config.normy_dzienne()
sprawdz("a `komentarz` ma dzienna norme, wiec licznik to zobaczy",
        _normy.get("komentarz"), _normy.get("komentarz"))

# KONTRDOWOD 1: gdyby ktos naprawil to przez zmiane DOMYSLNEJ wartosci w
# browser.py, odpowiadanie we wlasnym watku tez zaczeloby sie liczyc jako
# komentarz i licznik zawyzalby zamiast zanizac. Odpowiedzi u siebie MUSZA
# zostac bez normy.
_odpowiedzi = _znajdz("odpowiedzi", _drzewo)
if _odpowiedzi is None:
    # blok odpowiedzi bywa pisany bez wlasnej funkcji — wtedy szukamy poza
    # dyskusjami, po calym pliku
    _wszystkie = _rodzaj_w(_drzewo)
    _poza = [x for x in _wszystkie if x != "komentarz"]
    sprawdz("odpowiedzi we wlasnych watkach zostaja bez `rodzaj=komentarz`",
            _poza == [None], _wszystkie)
else:
    sprawdz("odpowiedzi we wlasnych watkach zostaja bez `rodzaj=komentarz`",
            _rodzaj_w(_odpowiedzi) == [None], _rodzaj_w(_odpowiedzi))

# KONTRDOWOD 2: sam wykrywacz musi widziec brak parametru jako brak. Gdyby
# `_rodzaj_w` zwracalo cokolwiek prawdziwego dla wywolania bez `rodzaj=`,
# oba sprawdzenia wyzej przechodzilyby zawsze.
_probka = _ast.parse("browser.wystaw_odpowiedz(1, 'x', wyslij=True)")
sprawdz("wywolanie bez `rodzaj=` czyta sie jako brak", _rodzaj_w(_probka) == [None],
        _rodzaj_w(_probka))

# I strona przegladarki: parametr musi realnie dojechac do dziennika, a nie
# tylko stac w sygnaturze.
sprawdz("browser przyjmuje `rodzaj` w wystaw_odpowiedz",
        'rodzaj: str = "odpowiedz"' in _br)
sprawdz("i zapisuje wlasnie jego, nie stala",
        "dopisz_wynik(rodzaj, wynik," in _br)
sprawdz("stara stala zniknela z tego zapisu",
        'dopisz_wynik("odpowiedz", wynik,' not in _br)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
