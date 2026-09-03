# -*- coding: utf-8 -*-
"""Audyt calosci ma liczyc obserwacje jak kazdy inny rodzaj — i nie tlumaczyc zera.

CO BYLO. 23 sierpnia 2026 zmierzono, ze slowa „Follow" nie ma w HTML profilu
Substacka. POMIAR BYL DOBRY. Wniosek — „przycisku nie ma" — byl falszywy: menu
z ta pozycja Substack dorysowuje dopiero po kliknieciu
`button[aria-label="Profile actions"]`, wiec w HTML zamknietej strony byc go nie
moze. Zmierzone ponownie 1 wrzesnia 2026 na zywej sesji (sam odczyt, zero
klikniec): `Copy link / Share / Send message / Follow / Mute / Block / Report`,
a na profilu juz obserwowanym w miejscu „Follow" stoi „Unfollow".

Zdanie ze zlego wniosku trafilo do DWOCH miejsc. `norma.NIEWYKONALNE` zdjeto 1
wrzesnia; `audyt_systemu.py` nadal drukowal wlasny werdykt „obserwacje (follow)
— znane ograniczenie" ze szczegolem „brak przycisku w sesji". Tam bylo gorzej
niz gdziekolwiek indziej, bo jedynym produktem tego pliku jest raport dla
czlowieka: zero z wyjasnieniem przestaje wygladac na problem i nikt go nie
sprawdza.

CO TEN TEST MIERZY. Nie tresc zrodla — ZERO asercji typu `"..." in ZRODLO`.
Kazde twierdzenie to RAPORT, ktory `audyt_systemu.main()` naprawde wydrukowal
na podanym dzienniku: harness podstawia dziennik, baze i katalog danych do
`tempfile`, uruchamia PRAWDZIWE `main()` i czyta jego wyjscie tak, jak czyta je
czlowiek.

KONTRDOWOD JEST ODTWORZONY, NIE OPISANY: `git show
64d881a:agent-v2/audyt_systemu.py` ladzi do katalogu tymczasowego i przechodzi
PRZEZ TEN SAM harness, na TYM SAMYM dzienniku. Wersja odniesienia jest
PRZYPIETA DO SHA `64d881a`, a nie do `HEAD` — kontrdowod mierzony wzgledem
`HEAD` gasnie w chwili commita, ktorego strzeze.

ZMIERZONA ROZNICA (sekcje 2, 5 i 7, dziennik: 4 notki udane, 2 komentarze
nieudane, 6 wpisow `obserwacja_pominieta`):

                                          64d881a              dzis
  wiersz o pominieciach              „udane   6"          osobna linia
  werdykt o obserwacjach             „znane ograniczenie" „wychodzi: obserwacja"
  szczegol tego werdyktu             „brak przycisku…"    „0 od 2026-08-25"
  „porazki nie dominuja"             OK  (2 < 10/2)       UWAGA (2 < 4/2 falsz)
  obserwacje w planie dnia (etap 2)  nie ma              „plan obserwacja…"

Trzecia i czwarta linia to jedna wada w dwoch przebraniach: szesc pominiec —
czyli szesc razy „ten profil juz obserwujemy" — udawalo szesc wykonanych prac,
raz w kolumnie „udane", raz w mianowniku progu porazek.

DLACZEGO POMINIECIE STOI OSOBNO, A NIE W ZADNEJ Z KOLUMN. `obserwacja_pominieta`
zapisuje sie z `udane=True`, ale niczego nie wystawia: profil byl juz
obserwowany (`browser.py`, menu pokazuje „Unfollow"), cala pula hostow z
historii komentarzy jest juz obserwowana albo wszyscy wylosowani byli znani z
pamieci (`run.py`). Slotu dnia to nie zjada, wiec blok probuje dalej. Wliczone
do udanych — tlumaczyloby zero dokladnie tak, jak robilo to zdanie o przycisku.
Wliczone do nieudanych — zanizaloby wynik za stan poprawny.

BEZ PYTESTA, zero sieci, zero wywolan modelu. Produkcyjna baza, produkcyjny
dziennik i produkcyjne `data/` NIETKNIETE (`browser.DZIENNIK`, `browser.WZROST`,
`config.DB_PATH` i `config.DATA_DIR` podmieniane na `tempfile` i przywracane w
`finally`; sekcja PRODUKCJA sprawdza odciski). Zaden warunek nie zna dzisiejszej
daty: dni dziennika licza sie z `audyt_systemu.PIVOT`, ktory jest stala.

Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_obserwacje_w_audycie.py
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import pathlib
import re
import sqlite3
import subprocess
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import browser   # noqa: E402
import config    # noqa: E402

zdane = oblane = 0


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


PILNOWANE = [pathlib.Path("agent-v2/audyt_systemu.py"),
             pathlib.Path("agent-v2/browser.py"),
             pathlib.Path("agent-v2/norma.py"),
             pathlib.Path("agent-v2/config.py"),
             pathlib.Path("agent-v2/run.py"),
             pathlib.Path(config.DB_PATH),
             config.DATA_DIR / "dziennik.jsonl",
             config.DATA_DIR / "kogo_obserwujemy.json"]
PRZED = {str(p): odcisk(p) for p in PILNOWANE}
DATA_PRZED = sorted(p.name for p in config.DATA_DIR.glob("*"))

TERAZ = pathlib.Path("agent-v2/audyt_systemu.py").resolve()

# --- wersja sprzed zmiany, ODTWORZONA, nie opisana ---------------------------
# SHA, nie `HEAD`: `HEAD` przesuwa sie z commitem, ktorego ten test pilnuje, wiec
# kontrdowod zgaslby dokladnie w chwili, w ktorej zaczyna byc potrzebny.
POPRZEDNIA_WERSJA = "64d881a"
KAT = pathlib.Path(tempfile.mkdtemp())
STARE = KAT / ("audyt_systemu_%s.py" % POPRZEDNIA_WERSJA)

# HISTORIA JEST WARUNKIEM TEGO TESTU — patrz `historia.py`. Straznik stoi
# PRZED pierwszym wywolaniem gita, bo ponizej git jest wolany juz na
# poziomie modulu i sprawdzenie po fakcie nie zdazyloby zadzialac.
import historia   # noqa: E402
historia.wymaga_historii("64d881a")

STARE.write_bytes(subprocess.check_output(
    ["git", "show", "%s:agent-v2/audyt_systemu.py" % POPRZEDNIA_WERSJA]))

# Baza z trzema tabelami, ktorych `main()` dotyka, i to wylacznie SELECT-ami
# (`articles`, `PRAGMA table_info(runs)`, `calls` z JOIN-em na `runs`). Pusta
# wystarczy: etapy 5-7 wypisza swoje BLEDY, a ten test o nie nie pyta.
DB = KAT / "atrapa.db"
_c = sqlite3.connect(str(DB))
_c.executescript(
    "CREATE TABLE articles (id INTEGER PRIMARY KEY, title TEXT, body TEXT,"
    " notes TEXT, created_at TEXT);"
    "CREATE TABLE runs (id INTEGER PRIMARY KEY, tryb TEXT, stage TEXT,"
    " finished_at TEXT);"
    "CREATE TABLE calls (id INTEGER PRIMARY KEY, run_id INTEGER, at TEXT,"
    " cost_usd REAL);")
_c.commit()
_c.close()

# DZIEN DZIENNIKA LICZY SIE ZE STALEJ, NIE Z KALENDARZA. `audyt_systemu.PIVOT`
# odsiewa wpisy starsze niz przestawienie konta na AI, wiec dzien musi byc
# `>= PIVOT`; bierzemy sam PIVOT plus jeden, zeby etap 2 mial pelna dobe do
# rozliczenia. Zadna asercja nizej nie pyta, ktory dzis jest dzien.
import audyt_systemu as _wzorzec   # noqa: E402

DZIEN = "%s-%02d" % (_wzorzec.PIVOT[:7], int(_wzorzec.PIVOT[8:]) + 1)
KIEDY = DZIEN + "T10:00:00+00:00"

# Plan dnia PODSTAWIONY, a nie wziety z produkcji: `norma.budzety_dzienne`
# czyta `config.DATA_DIR/budzety.json`, a produkcyjny plik zmienia sie z
# przebiegami i test przestalby byc powtarzalny.
(KAT / "budzety.json").write_text(json.dumps({DZIEN: {"budzet": {
    "notki": 5, "komentarze": 10, "lajki": 12, "restacki": 2,
    "follow": 2, "subskrypcje": 1}}}), encoding="utf-8")


def wpis(rodzaj, udane=True, **reszta):
    return dict({"kiedy": KIEDY, "rodzaj": rodzaj, "udane": udane}, **reszta)


_licznik = [0]


def _zaladuj(sciezka):
    """Swiezy obiekt modulu, zeby `WERDYKTY` nie przechodzily miedzy scenariuszami."""
    _licznik[0] += 1
    nazwa = "audyt_probka_%d" % _licznik[0]
    spec = importlib.util.spec_from_file_location(nazwa, str(sciezka))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nazwa] = mod
    spec.loader.exec_module(mod)
    # `KATALOG` liczy sie z `__file__`, wiec kopia w `tempfile` szukalaby
    # `browser.py` obok siebie i etap 4 padlby na odczycie. Wskazujemy ten sam
    # katalog, ktory ma wersja dzisiejsza — inaczej obie wersje czytalyby co
    # innego i porownanie nie byloby porownaniem.
    mod.KATALOG = pathlib.Path("agent-v2").resolve()
    return mod


def uruchom(sciezka, wpisy):
    """Prawdziwe `main()` na podstawionym dzienniku. Oddaje wydrukowany raport."""
    plik = KAT / "dziennik.jsonl"
    plik.write_text("".join(json.dumps(w, ensure_ascii=False) + "\n"
                            for w in wpisy), encoding="utf-8")
    mod = _zaladuj(sciezka)
    stare = (browser.DZIENNIK, browser.WZROST)
    zdjecie = config.uzyj_katalogu_danych(KAT)
    config.DB_PATH = DB
    browser.DZIENNIK = plik
    browser.WZROST = KAT / "brak-wzrostu.jsonl"
    buf = io.StringIO()
    wyjatek = None
    try:
        with contextlib.redirect_stdout(buf):
            mod.main()
    except BaseException as exc:      # noqa: BLE001 — raport i tak czytamy
        wyjatek = exc
    finally:
        browser.DZIENNIK, browser.WZROST = stare
        config.przywroc_katalog_danych(zdjecie)
    return buf.getvalue(), wyjatek


def wytnij(raport, od, do=None):
    a = raport.find("ETAP %d" % od)
    b = raport.find("ETAP %d" % do) if do else -1
    return raport[a if a >= 0 else 0: b if b > 0 else len(raport)]


WERDYKT = re.compile(r"^  >> (\S+)\s+(.+)$")


def werdykty(kawalek):
    """[(stan, nazwa, szczegol)] — dokladnie tak, jak stoi w raporcie."""
    wynik = []
    for linia in kawalek.splitlines():
        m = WERDYKT.match(linia.rstrip())
        if not m:
            continue
        czesci = re.split(r"   +", m.group(2), maxsplit=1)
        wynik.append((m.group(1), czesci[0].strip(),
                      czesci[1].strip() if len(czesci) > 1 else ""))
    return wynik


def nazwy(kawalek):
    return [n for _, n, _ in werdykty(kawalek)]


def stan(kawalek, nazwa):
    for s, n, _ in werdykty(kawalek):
        if n == nazwa:
            return s
    return None


def szczegol(kawalek, nazwa):
    for _, n, s in werdykty(kawalek):
        if n == nazwa:
            return s
    return None


# Ten sam dziennik dla obu wersji: 4 notki udane, 2 komentarze nieudane,
# 6 pominietych obserwacji i ZERO obserwacji prawdziwych.
PULA_Z_POMINIECIAMI = (
    [wpis("notka")] * 4
    + [wpis("komentarz", udane=False, powod="brak pola")] * 2
    + [wpis("obserwacja_pominieta", komu="ktos", juz_obserwowany=True,
            powod="juz obserwujemy ktos — menu pokazuje 'Unfollow'")] * 6)

RAPORT_NOWY, WYJ_NOWY = uruchom(TERAZ, PULA_Z_POMINIECIAMI)
RAPORT_STARY, WYJ_STARY = uruchom(STARE, PULA_Z_POMINIECIAMI)
E1_NOWY, E1_STARY = wytnij(RAPORT_NOWY, 1, 2), wytnij(RAPORT_STARY, 1, 2)
E2_NOWY, E2_STARY = wytnij(RAPORT_NOWY, 2, 3), wytnij(RAPORT_STARY, 2, 3)

print("=== 0. HARNESS ===")
sprawdz("dzisiejszy audyt przeszedl caly raport bez wyjatku",
        WYJ_NOWY is None, repr(WYJ_NOWY))
sprawdz("wersja %s przeszla ten sam raport bez wyjatku" % POPRZEDNIA_WERSJA,
        WYJ_STARY is None, repr(WYJ_STARY))

print()
print("=== 1. TRZY STANY, TRZY LICZNIKI ===")
# `policz_rodzaje` jest jedynym miejscem, w ktorym rozstrzyga sie, czym jest
# wpis — reszta pliku juz tylko sumuje. Dlatego pytamy o nia wprost.
_u, _n, _p = _wzorzec.policz_rodzaje(
    [wpis("notka"), wpis("obserwacja"), wpis("obserwacja", udane=False),
     wpis("obserwacja_pominieta"), wpis("obserwacja_pominieta")])
sprawdz("prawdziwa obserwacja liczy sie jako udana", _u.get("obserwacja") == 1,
        dict(_u))
sprawdz("nieudana obserwacja liczy sie jako nieudana",
        _n.get("obserwacja") == 1, dict(_n))
sprawdz("pominiecie nie wchodzi do udanych",
        "obserwacja_pominieta" not in _u, dict(_u))
sprawdz("pominiecie nie wchodzi do nieudanych",
        "obserwacja_pominieta" not in _n, dict(_n))
sprawdz("pominiecia maja wlasny licznik",
        _p.get("obserwacja_pominieta") == 2, dict(_p))
sprawdz("suma udanych to same proby, nie wszystkie wpisy z udane=True",
        sum(_u.values()) == 2, sum(_u.values()))

print()
print("=== 2. POMINIECIE NIE UDAJE SUKCESU ===")
sprawdz("szesc pominiec NIE robi z zera obserwacji werdyktu OK",
        stan(E1_NOWY, "wychodzi: obserwacja") == "UWAGA",
        stan(E1_NOWY, "wychodzi: obserwacja"))
sprawdz("werdykt mowi o ZERZE, a nie o szesciu",
        szczegol(E1_NOWY, "wychodzi: obserwacja") == "0 od %s" % _wzorzec.PIVOT,
        szczegol(E1_NOWY, "wychodzi: obserwacja"))
sprawdz("raport pokazuje pominiecia osobno, z liczba",
        "pominiecia (ani sukces, ani porazka): obserwacja_pominieta 6" in E1_NOWY,
        E1_NOWY)
sprawdz("i nie stawia ich w kolumnie „udane”",
        "obserwacja_pominieta udane" not in E1_NOWY, E1_NOWY)
# KONTRDOWOD do tej sekcji.
sprawdz("KONTRDOWOD: %s stawialo pominiecia w kolumnie „udane”"
        % POPRZEDNIA_WERSJA,
        "obserwacja_pominieta udane   6" in E1_STARY, E1_STARY)

print()
print("=== 3. POMINIECIE NIE UDAJE PORAZKI ===")
# Dziennik BEZ ani jednej porazki, za to z pominieciami. Gdyby pominiecie
# liczylo sie jako nieudane, werdykt o porazkach by sie odezwal i zszedlby na
# UWAGA za dzien, w ktorym wszystko poszlo zgodnie z projektem.
_bez_porazek, _ = uruchom(TERAZ, [wpis("notka")] * 3
                          + [wpis("obserwacja_pominieta")] * 5)
_e1 = wytnij(_bez_porazek, 1, 2)
sprawdz("bez prawdziwych porazek werdykt o porazkach w ogole nie pada",
        "porazki nie dominuja" not in nazwy(_e1), nazwy(_e1))
sprawdz("i zaden rodzaj nie dostaje pominiec do kolumny „nieudane”",
        "obserwacja_pominieta udane" not in _e1, _e1)

print()
print("=== 4. OBSERWACJA JEST W ZWYKLEJ PETLI, BEZ WLASNEGO ZDANIA ===")
_oczekiwane = ["wychodzi: %s" % r for r in _wzorzec.RODZAJE_WYCHODZACE]
sprawdz("etap 1 wystawia werdykt dla KAZDEGO rodzaju z jednej listy",
        nazwy(E1_NOWY) == _oczekiwane + ["porazki nie dominuja"],
        nazwy(E1_NOWY))
sprawdz("obserwacja jest na tej liscie",
        "obserwacja" in _wzorzec.RODZAJE_WYCHODZACE, _wzorzec.RODZAJE_WYCHODZACE)
# „Bez specjalnego zdania" znaczy: szczegol obserwacji ma DOKLADNIE ten sam
# ksztalt, co szczegol notki. To jest cala roznica miedzy pozycja w petli a
# pozycja z wlasnym akapitem.
_ksztalt = re.compile(r"^\d+ od %s$" % re.escape(_wzorzec.PIVOT))
_zle = [(n, s) for _, n, s in werdykty(E1_NOWY)
        if n.startswith("wychodzi: ") and not _ksztalt.match(s)]
sprawdz("kazdy z tych werdyktow ma ten sam ksztalt szczegolu", not _zle, _zle)
# Ta sama rzecz na dzienniku, w ktorym obserwacje NAPRAWDE wyszly.
_z_obserwacjami, _ = uruchom(TERAZ, [wpis("notka")] * 3 + [wpis("obserwacja")] * 2)
_e1o = wytnij(_z_obserwacjami, 1, 2)
sprawdz("dwie prawdziwe obserwacje daja OK, tak jak przy kazdym innym rodzaju",
        stan(_e1o, "wychodzi: obserwacja") == "OK"
        and szczegol(_e1o, "wychodzi: obserwacja") == "2 od %s" % _wzorzec.PIVOT,
        (stan(_e1o, "wychodzi: obserwacja"),
         szczegol(_e1o, "wychodzi: obserwacja")))

print()
print("=== 5. MIANOWNIK PROGU PORAZEK TO PROBY, NIE WPISY ===")
# Ten sam dziennik w obu wersjach: 4 udane, 2 nieudane, 6 pominiec.
# Prawda: 2 porazki wobec 4 prac, czyli DOKLADNIE polowa — prog „mniej niz
# polowa" nie jest spelniony. Doliczenie pominiec do udanych robi z tego 2
# wobec 10 i werdykt sie uspokaja.
sprawdz("dzis: dwie porazki na cztery prace to juz nie jest „nie dominuja”",
        stan(E1_NOWY, "porazki nie dominuja") == "UWAGA",
        stan(E1_NOWY, "porazki nie dominuja"))
sprawdz("KONTRDOWOD: %s meldowalo tu OK, bo pominiecia podnosily mianownik"
        % POPRZEDNIA_WERSJA,
        stan(E1_STARY, "porazki nie dominuja") == "OK",
        stan(E1_STARY, "porazki nie dominuja"))

print()
print("=== 6. PLAN DNIA TAKZE OBEJMUJE OBSERWACJE ===")
_plan = sorted(n.split()[1] for n in nazwy(E2_NOWY) if n.startswith("plan "))
# LISTA RODZAJOW ZNIKLA 1 WRZESNIA 2026 PO POLUDNIU — rozstrzyga PLAN DNIA.
# `RODZAJE_Z_PLANEM` byla wypisana recznie i zestarzala sie tego samego dnia,
# w ktorym powstala (odwrocone budzety: obserwacja 0,433/dobe, subskrypcja
# 0,533). Dzis rozliczamy kazdy rodzaj, ktoremu budzet dal co najmniej jedna
# cala sztuke — a budzet tej doby (`follow=2`, `subskrypcje=1`) dal ja obu.
# Powody i zmierzone liczby: `tests/test_pominiecia_i_plan_w_audycie.py`.
_budzet_doby = {"notki": 5, "komentarze": 10, "lajki": 12, "restacki": 2,
                "follow": 2, "subskrypcje": 1}
_oczekiwane_z_planem = sorted(
    config.BUDZET_NA_RODZAJ[k] for k, v in _budzet_doby.items()
    if v >= _wzorzec.MIN_PLAN_DNIA_DO_ROZLICZENIA)
sprawdz("etap 2 rozlicza z planu dokladnie te rodzaje, ktorym budzet dal"
        " co najmniej jedna cala sztuke",
        _plan == _oczekiwane_z_planem, (_plan, _oczekiwane_z_planem))
sprawdz("a obserwacja jest wsrod nich, bo budzet dal jej 2",
        "obserwacja" in _plan, _plan)
sprawdz("plan 2 obserwacji i zero wykonanych to UWAGA, nie cisza",
        stan(E2_NOWY, "plan obserwacja w dniu %s" % DZIEN) == "UWAGA",
        [(s, n, d) for s, n, d in werdykty(E2_NOWY) if "obserwacja" in n])
_plan_stary = sorted(n.split()[1] for n in nazwy(E2_STARY) if n.startswith("plan "))
sprawdz("KONTRDOWOD: %s nie rozliczalo obserwacji z planu wcale"
        % POPRZEDNIA_WERSJA,
        "obserwacja" not in _plan_stary, _plan_stary)

print()
print("=== 7. ZERO NIE JEST JUZ TLUMACZONE ZDANIEM O PRZYCISKU ===")
# Sedno calej poprawki. Sprawdzamy RAPORT, bo raport jest jedynym produktem
# tego pliku — nie zrodlo.
sprawdz("KONTRDOWOD: %s drukowalo werdykt o „znanym ograniczeniu”"
        % POPRZEDNIA_WERSJA,
        any("znane ograniczenie" in n for n in nazwy(E1_STARY)), nazwy(E1_STARY))
sprawdz("KONTRDOWOD: i tlumaczylo zero brakiem przycisku w sesji",
        "brak przycisku w sesji" in E1_STARY, E1_STARY)
sprawdz("KONTRDOWOD: nie mialo przy tym werdyktu „wychodzi: obserwacja”",
        "wychodzi: obserwacja" not in nazwy(E1_STARY), nazwy(E1_STARY))
sprawdz("dzis zadne zdanie o przycisku w raporcie nie pada",
        "przycisk" not in RAPORT_NOWY.lower(),
        [l for l in RAPORT_NOWY.splitlines() if "przycisk" in l.lower()])
sprawdz("i zaden werdykt nie zapowiada ograniczenia",
        not any("ograniczenie" in n for n in nazwy(RAPORT_NOWY)),
        [n for n in nazwy(RAPORT_NOWY) if "ograniczenie" in n])

print()
print("=== PRODUKCJA ===")
zle = 0
for p in PILNOWANE:
    ok = odcisk(p) == PRZED[str(p)]
    zle += 0 if ok else 1
    print("  %-26s %s" % (pathlib.Path(p).name,
                          "bez zmian" if ok else "ZMIENIONY"))
_data_po = sorted(p.name for p in config.DATA_DIR.glob("*"))
zle += 0 if _data_po == DATA_PRZED else 1
print("  %-26s %s" % ("data/", "bez zmian (%d pozycji)" % len(_data_po)
                      if _data_po == DATA_PRZED else "ZMIENIONY"))

print()
print("=== WYNIK: %d zdanych, %d oblanych%s ===" %
      (zdane, oblane, ", PRODUKCJA RUSZONA" if zle else ""))
sys.exit(1 if (oblane or zle) else 0)
