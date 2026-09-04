# -*- coding: utf-8 -*-
"""Zrzut czytelnikow mowi, KTORA liste naprawde odczytal.

## Co bylo zepsute

`browser.kto_nas_czyta` bierze obserwujacych z zakladki otwartej domyslnie,
a subskrybentow dopiero po KLIKNIECIU w druga zakladke. `zapisz_czytelnikow`
oddawalo `None` tylko wtedy, gdy byl blad I OBIE listy byly puste. Gdy wiec
pekalo samo klikniecie — albo gdy zakladki „Subscribers" po prostu nie bylo,
co nie jest nawet wyjatkiem i konczylo petle po cichu z `blad=None` —
obserwujacy byli juz w wyniku i zrzut szedl na dysk z PUSTA lista
subskrybentow, wygladajac na udany pomiar.

Dlaczego to jest gorsze od braku zrzutu: `wzajemnosc.czytelnicy` datuje ludzi
po NUMERZE zrzutu („kto doszedl po zrzucie zerowym, ten przyszedl po naszej
akcji"). Gdyby okrojony byl zrzut PIERWSZY, caly komplet subskrybentow
dostalby `pierwszy_zrzut > 0` i raport oglosilby ich jako pozyskanych naszym
dzialaniem. Odpowiedz na pytanie wlasciciela „skad biora sie czytelnicy"
stalaby wiec na jednym nieudanym kliknieciu. Sekcja 4 odtwarza to wprost.

## Skad wiadomo, ze niedobor 2 osob na liscie obserwujacych NIE jest ta awaria

Zmierzone 1 wrzesnia 2026 na produkcji, siedem par (licznik `followerCount`
z `wzrost.jsonl` wobec dlugosci listy z `czytelnicy.jsonl`):

    08-31 04:12/04:24   8 / 7        subskrybenci 7 / 7
    08-31 11:38/11:38   9 / 7        subskrybenci 9 / 9
    08-31 17:08/17:08  11 / 9        subskrybenci 9 / 9
    08-31 19:41/19:41  11 / 9        subskrybenci 9 / 9
    08-31 21:54/21:54  11 / 9        subskrybenci 9 / 9
    09-01 00:12/00:13  11 / 9        subskrybenci 9 / 9
    09-01 11:38/11:38  12 / 10       subskrybenci 9 / 9

Subskrybenci zgadzaja sie CO DO JEDNEGO we wszystkich siedmiu parach, wiec
zakladka jako taka dziala. Niedobor jest wylacznie po stronie obserwujacych
i stoi na 2, podczas gdy lista rosnie swobodnie 7 -> 10 — to wyklucza limit
strony (limit dawalby stala DLUGOSC, nie stala roznice).

Rozstrzyga jeden przypadek. „Leonard" ma w produkcyjnym dzienniku zdarzenie
`follow` z 2026-08-31T06:25:10, `followerCount` podskoczyl wtedy z 8 na 9
i juz nie spadl — a na zakladce „Followers" nie ma go w ZADNYM z szesciu
pozniejszych zrzutow, za to jako `leonard896188` stoi na zakladce
„Subscribers" tej samej strony. Uchwyt ma, konta nie skasowal, nasz filtr go
nie tyka. Kto obserwuje I subskrybuje, tego Substack pokazuje wylacznie
w „Subscribers": obie listy sa w kazdym z siedmiu zrzutow ROZLACZNE
(10 + 9 osob, zero czesci wspolnej). Brakujaca dwojka nie jest wiec
nienazwana — to dwie osoby policzone przez licznik, a wypisane obok.

WNIOSEK: zadnego dodatkowego ruchu. Nie ma czego doczytac, a regulamin
Substacka zakazuje `crawls/scrapes/spiders` wprost. Sekcja 3 pokazuje
ZACHOWANIEM, ze to nie nasz odsiew gubi te dwie osoby.

## Co ten test mierzy

ZACHOWANIE `browser.kto_nas_czyta` i `browser.zapisz_czytelnikow` na atrapie
strony; plik zrzutow jest prawdziwy, tylko przekierowany do katalogu
tymczasowego. Zero asercji po tresci zrodel, zero sieci, zero przegladarki.

KONTRDOWOD ODTWARZANY: sekcja 4 puszcza ten sam scenariusz przez
`kto_nas_czyta` i `zapisz_czytelnikow` wyjete z
`git show 6ed4e7d:agent-v2/browser.py` — wersja odniesienia PRZYPIETA DO SHA,
nie do HEAD.

Test nie zalezy od dzisiejszej daty.
"""

import ast
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile

KORZEN = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(KORZEN / "agent-v2"))

import browser        # noqa: E402
import config         # noqa: E402
import wzajemnosc     # noqa: E402

# HISTORIA JEST WARUNKIEM TEGO TESTU — patrz `historia.py`.
import historia   # noqa: E402
historia.wymaga_historii("6ed4e7d")

ODNIESIENIE = "6ed4e7d"        # wersja SPRZED poprawki, przypieta na stale

zdane = 0
oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


def odcisk(p):
    p = pathlib.Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else "brak"


PILNOWANE = [config.DATA_DIR / "czytelnicy.jsonl",
             config.DATA_DIR / "wzrost.jsonl",
             config.DATA_DIR / "dziennik.jsonl"]
PRZED = {str(p): odcisk(p) for p in PILNOWANE}


# --- ATRAPA STRONY -----------------------------------------------------------
#
# Odwzorowuje dokladnie te czesc Playwrighta, ktorej uzywa `kto_nas_czyta`:
# `goto`, `wait_for_timeout`, `locator(...).all()` i `get_by_role("tab", ...)`
# z `.count()` oraz `.click()`. Zakladka jest STANEM: `locator` oddaje linki
# tej zakladki, ktora jest w tej chwili otwarta — tak jak na zywej stronie.
class Odnosnik:
    def __init__(self, href, tekst):
        self._h, self._t = href, tekst

    def get_attribute(self, _):
        return self._h

    def inner_text(self):
        return self._t


class Lokator:
    def __init__(self, odnosniki):
        self._o = odnosniki

    def all(self):
        return self._o


class Zakladka:
    def __init__(self, strona, jest, wybuch=None):
        self._s, self._jest, self._wybuch = strona, jest, wybuch

    @property
    def first(self):
        return self

    def count(self):
        return 1 if self._jest else 0

    def click(self, timeout=None):
        if self._wybuch:
            raise self._wybuch
        self._s.otwarta = "subskrybenci"


class Strona:
    def __init__(self, obserwujacy, subskrybenci, jest_zakladka=True,
                 wybuch_kliku=None, wybuch_goto=None, wybuch_locatora=None):
        self.linki = {"obserwujacy": obserwujacy, "subskrybenci": subskrybenci}
        self.otwarta = "obserwujacy"
        self._jest = jest_zakladka
        self._klik = wybuch_kliku
        self._goto = wybuch_goto
        self._locator = wybuch_locatora
        self.wejscia = 0

    def goto(self, url, timeout=None, wait_until=None):
        self.wejscia += 1
        if self._goto:
            raise self._goto

    def wait_for_timeout(self, _ms):
        pass

    def locator(self, _selektor):
        if self._locator:
            raise self._locator
        return Lokator(self.linki[self.otwarta])

    def get_by_role(self, _rola, name=None, exact=False):
        return Zakladka(self, self._jest, self._klik)


def link(uchwyt, nazwa=None):
    return Odnosnik("/@%s" % uchwyt, nazwa if nazwa is not None else uchwyt)


OBSERWUJACY = [link("czytelnik2", "Publikacja Drogowa: Founder"),
               link("petrosbountis", "Halina Osma"),
               link("czytelnik3", "Publikacja Lustrzana AI")]
SUBSKRYBENCI = [link("leonard896188", "Leonard"),
                link("chaosengine2026", "Publikacja Chaosu")]
NAWIGACJA = [Odnosnik("/@explore", "Explore"),
             Odnosnik("/@dashboard", "Dashboard")]


ROBOCZY = pathlib.Path(tempfile.mkdtemp())


def zrzuc(strona, plik):
    """Puszcza PRODUKCYJNY `zapisz_czytelnikow` na atrapie i oddaje wynik."""
    stary = browser.CZYTELNICY
    try:
        browser.CZYTELNICY = pathlib.Path(plik)
        return browser.zapisz_czytelnikow(strona)
    finally:
        browser.CZYTELNICY = stary


def linie(plik):
    p = pathlib.Path(plik)
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines()
            if l.strip()]


print("=== 1. ZRZUT PELNY MOWI, ZE JEST PELNY ===")
pelna = Strona(NAWIGACJA + OBSERWUJACY, NAWIGACJA + SUBSKRYBENCI)
kto = browser.kto_nas_czyta(pelna)
sprawdz("obie zakladki odczytane",
        kto["odczytane"] == ["obserwujacy", "subskrybenci"], kto["odczytane"])
sprawdz("i obie listy niepuste",
        len(kto["obserwujacy"]) == 3 and len(kto["subskrybenci"]) == 2, kto)
z1 = zrzuc(pelna, ROBOCZY / "pelny.jsonl")
sprawdz("zrzut zapisany z etykieta",
        z1 and z1["odczytane"] == ["obserwujacy", "subskrybenci"], z1)

print()
print("=== 2. ZRZUT OKROJONY ZAPISUJE SIE JAKO OKROJONY ===")

print("  -- 2a. pekniete klikniecie w zakladke --")
padl_klik = Strona(NAWIGACJA + OBSERWUJACY, NAWIGACJA + SUBSKRYBENCI,
                   wybuch_kliku=TimeoutError("Timeout 10000ms exceeded"))
kto2 = browser.kto_nas_czyta(padl_klik)
sprawdz("obserwujacy sa, bo zdazyli sie odczytac",
        len(kto2["obserwujacy"]) == 3, kto2["obserwujacy"])
sprawdz("subskrybentow nie ma", kto2["subskrybenci"] == [], kto2)
sprawdz("i ZRZUT TO MOWI: odczytana tylko jedna zakladka",
        kto2["odczytane"] == ["obserwujacy"], kto2["odczytane"])
plik2 = ROBOCZY / "okrojony.jsonl"
z2 = zrzuc(padl_klik, plik2)
sprawdz("okrojony zrzut nadal sie zapisuje (dane obserwujacych nie ginie)",
        z2 is not None and len(linie(plik2)) == 1, z2)
sprawdz("ale w PLIKU widac, czego nie odczytano",
        linie(plik2)[0].get("odczytane") == ["obserwujacy"], linie(plik2))

print("  -- 2b. zakladki 'Subscribers' w ogole nie ma --")
# To NIE JEST wyjatek: stara petla konczyla sie po cichu i `blad` zostawal
# `None`, wiec zrzut wygladal na w pelni udany.
bez_zakladki = Strona(NAWIGACJA + OBSERWUJACY, NAWIGACJA + SUBSKRYBENCI,
                      jest_zakladka=False)
kto3 = browser.kto_nas_czyta(bez_zakladki)
sprawdz("odczytani tylko obserwujacy",
        kto3["odczytane"] == ["obserwujacy"], kto3["odczytane"])
sprawdz("i powod jest nazwany, a nie milczy",
        bool(kto3["blad"]), kto3["blad"])

print("  -- 2c. nic nie wstalo: brak zrzutu, nie pusty zrzut --")
padla_strona = Strona([], [], wybuch_goto=RuntimeError("net::ERR_ABORTED"))
kto4 = browser.kto_nas_czyta(padla_strona)
sprawdz("zadna zakladka nie odczytana", kto4["odczytane"] == [], kto4)
plik4 = ROBOCZY / "nic.jsonl"
sprawdz("i nic nie ladzie na dysku",
        zrzuc(padla_strona, plik4) is None and linie(plik4) == [])

print("  -- 2d. konto NAPRAWDE puste to co innego niz awaria --")
puste = Strona(list(NAWIGACJA), list(NAWIGACJA))
kto5 = browser.kto_nas_czyta(puste)
sprawdz("obie zakladki odczytane, obie puste",
        kto5["odczytane"] == ["obserwujacy", "subskrybenci"]
        and kto5["obserwujacy"] == [] and kto5["subskrybenci"] == [], kto5)
plik5 = ROBOCZY / "puste.jsonl"
sprawdz("pusty, ale ODCZYTANY zrzut zostaje zapisany",
        zrzuc(puste, plik5) is not None and len(linie(plik5)) == 1)

print()
print("=== 2e. PUSTA LISTA A PADNIETY ODCZYT — DWIE ROZNE RZECZY ===")
# Do 1 wrzesnia `_ludzie_z_zakladki` oddawalo `[]` w obu przypadkach i nie
# bylo jak ich rozroznic. To wlasnie ta nierozroznialnosc pozwalala zrzutowi
# okrojonemu udawac udany.
zla = Strona([], [], wybuch_locatora=RuntimeError("odlaczona ramka"))
sprawdz("wyjatek strony -> (pusto, NIE odczytano)",
        browser._ludzie_z_zakladki_ze_stanem(zla) == ([], False))
sprawdz("zakladka bez ludzi -> (pusto, odczytano)",
        browser._ludzie_z_zakladki_ze_stanem(
            Strona(list(NAWIGACJA), [])) == ([], True))
sprawdz("stare wejscie `_ludzie_z_zakladki` dalej oddaje sama liste",
        browser._ludzie_z_zakladki(zla) == []
        and len(browser._ludzie_z_zakladki(
            Strona(NAWIGACJA + OBSERWUJACY, []))) == 3)

print()
print("=== 3. TO NIE NASZ ODSIEW GUBI DWIE OSOBY (B2) ===")
# Gdyby niedobor bral sie z limitu albo z filtru po naszej stronie, ta lista
# by sie skrocila. Dwanascie osob to WIECEJ niz najdluzszy zmierzony zrzut
# produkcyjny (10 obserwujacych, 1 wrzesnia).
duzo = [link("konto%02d" % i, "Konto %d" % i) for i in range(12)]
powtorki = [Odnosnik("/@konto03", ""),            # awatar bez tekstu
            Odnosnik("/@konto04?utm=share", "Konto 4"),
            Odnosnik("/@konto05/notes", "Konto 5")]
szeroka = Strona(NAWIGACJA + duzo + powtorki, [])
ludzie, ok = browser._ludzie_z_zakladki_ze_stanem(szeroka)
sprawdz("dwanascie osob wchodzi w calosci, nic nie ucieto",
        ok and len(ludzie) == 12, len(ludzie))
sprawdz("a nawigacja dalej wypada",
        not {"explore", "dashboard"} & {x["uchwyt"] for x in ludzie})
# I druga polowa dowodu: NASZ kod nie zna reguly „subskrybenta nie pokazuj
# wsrod obserwujacych". Ta sama osoba na obu zakladkach wychodzi na obu.
obie = Strona(NAWIGACJA + [link("leonard896188", "Leonard")],
              NAWIGACJA + [link("leonard896188", "Leonard")])
kto6 = browser.kto_nas_czyta(obie)
sprawdz("ta sama osoba na obu zakladkach jest w obu listach",
        [x["uchwyt"] for x in kto6["obserwujacy"]] == ["leonard896188"]
        and [x["uchwyt"] for x in kto6["subskrybenci"]] == ["leonard896188"],
        kto6)

print()
print("=== 4. KONTRDOWOD: WERSJA Z %s I CO Z NIEJ WYCHODZI ===" % ODNIESIENIE)


def zrodlo_browser(commit):
    proc = subprocess.run(["git", "-C", str(KORZEN), "show",
                           "%s:agent-v2/browser.py" % commit],
                          capture_output=True)
    if proc.returncode != 0:
        raise SystemExit("nie dostalem browser.py z %s: %s"
                         % (commit, proc.stderr.decode("utf-8", "replace")[:200]))
    return proc.stdout.decode("utf-8")


def wytnij(src, nazwa):
    for w in ast.walk(ast.parse(src)):
        if isinstance(w, ast.FunctionDef) and w.name == nazwa:
            linijki = src.splitlines()[w.lineno - 1:w.end_lineno]
            wciecie = len(linijki[0]) - len(linijki[0].lstrip())
            return "\n".join(x[wciecie:] if x[:wciecie].strip() == "" else x
                             for x in linijki)
    raise SystemExit("nie znalazlem funkcji %s" % nazwa)


ZRODLO_STARE = zrodlo_browser(ODNIESIENIE)
przestrzen = dict(browser.__dict__)
for nazwa in ("_ludzie_z_zakladki", "kto_nas_czyta", "zapisz_czytelnikow"):
    exec(compile(wytnij(ZRODLO_STARE, nazwa), "<%s:browser.py>" % ODNIESIENIE,
                 "exec"), przestrzen)
stary_plik = ROBOCZY / "stary.jsonl"
przestrzen["CZYTELNICY"] = stary_plik

padl_klik_st = Strona(NAWIGACJA + OBSERWUJACY, NAWIGACJA + SUBSKRYBENCI,
                      wybuch_kliku=TimeoutError("Timeout 10000ms exceeded"))
stary_zrzut = przestrzen["zapisz_czytelnikow"](padl_klik_st)
sprawdz("stara wersja tez zapisuje okrojony zrzut", stary_zrzut is not None)
sprawdz("ale bez ANI JEDNEGO sladu, ze cos nie wyszlo (test rozroznia)",
        "odczytane" not in (linie(stary_plik)[0] if linie(stary_plik) else {}),
        linie(stary_plik))
sprawdz("i z pusta lista subskrybentow, nie do odroznienia od pustego konta",
        linie(stary_plik)[0]["subskrybenci"] == [], linie(stary_plik))
# Na tej samej stronie stara wersja bez zakladki milczala calkiem.
przestrzen["CZYTELNICY"] = ROBOCZY / "stary2.jsonl"
kto_st = przestrzen["kto_nas_czyta"](
    Strona(NAWIGACJA + OBSERWUJACY, NAWIGACJA + SUBSKRYBENCI,
           jest_zakladka=False))
sprawdz("brak zakladki: stara wersja nie zglaszala nawet bledu",
        kto_st["blad"] is None, kto_st)

print()
print("=== 4b. CO Z TEGO WYCHODZI W RAPORCIE WZAJEMNOSCI ===")
# Okrojony zrzut jako PIERWSZY, pelny jako drugi. `wzajemnosc.czytelnicy`
# datuje po numerze zrzutu, wiec kazdy subskrybent dostaje `pierwszy_zrzut=1`
# — czyli „pojawil sie po naszej akcji". To jest zdanie, ktore raport
# stawialby na jednym nieudanym kliknieciu.
UDAWANA = pathlib.Path(tempfile.mkdtemp())
with (UDAWANA / "czytelnicy.jsonl").open("w", encoding="utf-8") as f:
    okrojony = dict(linie(stary_plik)[0])
    okrojony["kiedy"] = "2026-08-31T04:24:28+00:00"
    f.write(json.dumps(okrojony, ensure_ascii=False) + "\n")
    f.write(json.dumps({"kiedy": "2026-08-31T11:38:23+00:00",
                        "obserwujacy": [{"uchwyt": "petrosbountis",
                                         "nazwa": "Halina Osma"}],
                        "subskrybenci": [{"uchwyt": "leonard896188",
                                          "nazwa": "Leonard"},
                                         {"uchwyt": "chaosengine2026",
                                          "nazwa": "Publikacja Chaosu"}]},
                       ensure_ascii=False) + "\n")
_zdjecie_data = wzajemnosc.config.uzyj_katalogu_danych(UDAWANA)
try:
    ludzie_w = wzajemnosc.czytelnicy()
    subskrybenci = {u: w for u, w in ludzie_w.items() if "subskrybent" in w["role"]}
    sprawdz("KAZDY subskrybent wyglada na pozyskanego po naszej akcji"
            " (test rozroznia)",
            subskrybenci
            and all(w["pierwszy_zrzut"] > 0 for w in subskrybenci.values()),
            {u: w["pierwszy_zrzut"] for u, w in subskrybenci.items()})
    sprawdz("a to nieprawda: obaj byli juz w zrzucie zerowym, tylko go nie"
            " odczytano", len(subskrybenci) == 2, sorted(subskrybenci))
finally:
    wzajemnosc.config.przywroc_katalog_danych(_zdjecie_data)

print()
print("=== 5. ZGODNOSC WSTECZ: SIEDEM ZRZUTOW BEZ TEGO POLA ===")
# Siedem zrzutow z produkcji nie ma pola `odczytane` i nigdy nie dostanie.
# Ksztalt przepisany z `data/czytelnicy.jsonl` (31 sierpnia — 1 wrzesnia),
# skrocony do dwoch osob na grupe; klucze te same, co na produkcji.
STARE = pathlib.Path(tempfile.mkdtemp())
with (STARE / "czytelnicy.jsonl").open("w", encoding="utf-8") as f:
    for i, kiedy in enumerate(("2026-08-31T04:24:28+00:00",
                               "2026-08-31T11:38:23+00:00",
                               "2026-08-31T17:08:23+00:00",
                               "2026-08-31T19:41:23+00:00",
                               "2026-08-31T21:54:22+00:00",
                               "2026-09-01T00:13:04+00:00",
                               "2026-09-01T11:38:25+00:00")):
        f.write(json.dumps({
            "kiedy": kiedy,
            "obserwujacy": [{"uchwyt": "petrosbountis", "nazwa": "Halina Osma"},
                            {"uchwyt": "czytelnik3", "nazwa": "Publikacja Lustrzana AI"}],
            "subskrybenci": [{"uchwyt": "chaosengine2026", "nazwa": "Publikacja Chaosu"}]
            + ([{"uchwyt": "leonard896188", "nazwa": "Leonard"}] if i else []),
        }, ensure_ascii=False) + "\n")
_zdjecie_data = wzajemnosc.config.uzyj_katalogu_danych(STARE)
try:
    starzy = wzajemnosc.czytelnicy()
    sprawdz("stary ksztalt czyta sie bez wyjatku i bez ubytku",
            len(starzy) == 4, sorted(starzy))
    sprawdz("i dalej daje te sama odpowiedz o dacie pojawienia sie",
            starzy["leonard896188"]["pierwszy_zrzut"] == 1
            and starzy["chaosengine2026"]["pierwszy_zrzut"] == 0, starzy)
    if hasattr(wzajemnosc, "zrzuty_czytelnikow"):
        oceny = wzajemnosc.zrzuty_czytelnikow()
        sprawdz("i ocena zrzutow tez przezywa brak pola",
                len(oceny) == 7, len(oceny))
finally:
    wzajemnosc.config.przywroc_katalog_danych(_zdjecie_data)

# Odwrotny kierunek: nowe pole nie moze niczego przestawic czytajacym.
NOWE = pathlib.Path(tempfile.mkdtemp())
with (NOWE / "czytelnicy.jsonl").open("w", encoding="utf-8") as f:
    for l in (STARE / "czytelnicy.jsonl").read_text(encoding="utf-8").splitlines():
        w = json.loads(l)
        w["odczytane"] = ["obserwujacy", "subskrybenci"]
        f.write(json.dumps(w, ensure_ascii=False) + "\n")
_zdjecie_data = wzajemnosc.config.uzyj_katalogu_danych(NOWE)
try:
    nowi = wzajemnosc.czytelnicy()
    sprawdz("nowy ksztalt daje DOKLADNIE ten sam wynik, co stary",
            {u: w["pierwszy_zrzut"] for u, w in nowi.items()}
            == {u: w["pierwszy_zrzut"] for u, w in starzy.items()},
            (sorted(nowi), sorted(starzy)))
finally:
    wzajemnosc.config.przywroc_katalog_danych(_zdjecie_data)

print()
print("=== PRODUKCJA: bez zmian ===")
zle = 0
for p in PILNOWANE:
    t = odcisk(p)
    ok_p = t == PRZED[str(p)]
    zle += 0 if ok_p else 1
    print("  %-30s %s" % (pathlib.Path(p).name,
                          "bez zmian" if ok_p else "ZMIENIONA"))

print()
print("=== WYNIK: %d zdanych, %d oblanych%s ===" %
      (zdane, oblane, ", PRODUKCJA RUSZONA" if zle else ""))
sys.exit(1 if (oblane or zle) else 0)
