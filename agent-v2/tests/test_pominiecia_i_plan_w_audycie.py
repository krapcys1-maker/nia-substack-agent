# -*- coding: utf-8 -*-
"""Audyt ma poznawac pominiecia po KONCOWCE i rozliczac z planu po LICZBIE.

Dwie wady jednego dnia i obie z tej samej rodziny: zamknieta lista nazw tam,
gdzie powinna stac regula. 1 wrzesnia 2026 doszedl rodzaj `subskrypcja_pominieta`
i odwrocono budzety (`FOLLOW_MIESIECZNIE` 30-44 -> 10-16,
`SUBSKRYPCJE_MIESIECZNIE` 6-12 -> 12-20). Obie listy zestarzaly sie tego samego
dnia, w ktorym powstaly.

A1 — NOWY RODZAJ WPADAL DO KUBLA „UDANE". `POMINIECIA` bylo krotka
`("obserwacja_pominieta",)`, a `subskrypcja_pominieta` (`run.py:1524` i `1592`,
takze `udane=True`, gdy cel jest juz zasubskrybowany) do niej nie trafil. Wpis,
ktory NIE JEST ani sukcesem, ani porazka, liczyl sie wiec jako sukces —
dokladnie tam, gdzie komentarz nad ta krotka tlumaczy, ze nie wolno. Zmierzone
(4 notki udane, 2 komentarze nieudane, 6 pominietych subskrypcji, ZERO
prawdziwych):

                                       6ed4e7d              dzis
  wiersz o pominieciach           „udane   6" w tabeli   osobna linia
  suma udanych (`sum(udane)`)     10                     4
  „porazki nie dominuja"          OK  (2 < 10/2)         UWAGA (2 < 4/2 falsz)

Werdykt „wychodzi: subskrypcja" byl w OBU wersjach ten sam („UWAGA, 0 od
2026-08-25") i to jest wazne: stary licznik trzymal pominiecia pod WLASNYM
kluczem, wiec zera prawdziwych subskrypcji nie tlumaczyl. Klamala SUMA — a ta
jest mianownikiem progu porazek i bedzie mianownikiem kazdego nastepnego
licznika, ktory po nia siegnie.

Ten sam projekt rozstrzygnal to poprawnie obok, w `wzajemnosc.zaczepienia`
(`wzajemnosc.py:333-341`): pominiecia poznaje sie po koncowce `_pominieta`,
„zeby trafily do wlasciwej kupki od pierwszego dnia, a nie po tym, jak ktos
zauwazy przekrecony licznik".

A2 — `RODZAJE_Z_PLANEM` ROZLICZALO NIE TEN KANAL, CO TRZEBA. Lista zawierala
`obserwacja` i wykluczala `subskrypcja`, a jej wlasne uzasadnienie mowilo
„obserwacja ~1,2 na dobe" i „subskrypcja 0,3 — wiec wiekszosc dni ma plan
ZERO". Po odwroceniu budzetow liczby sie ZAMIENILY: obserwacja 0,433/dobe,
subskrypcja 0,533/dobe. Audyt rozliczal z planu kanal mniejszy — ten, ktory
lista miala wykluczac — a glownego nie rozliczal wcale.

Druga polowa tej samej wady siedziala w `plan_dnia.get(r) or normy.get(r)`:
zapisane ZERO jest falszywe, wiec `or` podstawialo w jego miejsce ulamkowa
NORME i audyt zadal 60% z 0,433 obserwacji od doby, ktorej wlasny plan wynosil
ZERO. Zmierzone na prawdziwym `stages.budzet_dnia` (365 dob): plan obserwacji
jest zerowy w 57,5% dob poza rozbiegiem i 62,7% w rozbiegu, subskrypcji — 48,8%
i 52,3%. W zapisanym `budzety.json` z serwera (17 dob) `follow=0` stoi 9 razy,
`subskrypcje=0` dziesiec razy; 1 wrzesnia obie pozycje maja ZERO. Ponad polowa
raportow niosla wiec UWAGA za dobe, ktora byla ZGODNA z planem.

JAK TO ROZSTRZYGNIETO. Zamiast listy nazw — prog z planu:
`MIN_PLAN_DNIA_DO_ROZLICZENIA` = 1. Rozliczamy kazdy rodzaj z
`RODZAJE_WYCHODZACE`, ktorego plan NA TEN DZIEN to co najmniej jedna cala
sztuka; ponizej jednej „60% planu" nie jest pytaniem, bo wykonanie jest liczba
calkowita. Nastepna zmiana widelek nie wymaga tkniecia tego pliku.

CO TEN TEST MIERZY. Nie tresc zrodla — ZERO asercji typu `"..." in ZRODLO`.
Kazde twierdzenie to RAPORT, ktory `audyt_systemu.main()` naprawde wydrukowal
na podanym dzienniku i budzecie: harness podstawia dziennik, baze i katalog
danych do `tempfile`, uruchamia PRAWDZIWE `main()` i czyta jego wyjscie tak,
jak czyta je czlowiek.

KONTRDOWOD JEST ODTWORZONY, NIE OPISANY: `git show 6ed4e7d:agent-v2/audyt_systemu.py`
ladzi do katalogu tymczasowego i przechodzi PRZEZ TEN SAM harness, na TYCH
SAMYCH danych. Wersja odniesienia jest PRZYPIETA DO SHA `6ed4e7d`, a nie do
`HEAD` — kontrdowod mierzony wzgledem `HEAD` gasnie w chwili commita, ktorego
strzeze.

ZADEN WARUNEK NIE ZNA DZISIEJSZEJ DATY. Dni licza sie z `audyt_systemu.PIVOT`,
ktory jest stala; etap 2 rozlicza „ostatni pelny dzien", wiec dziennik dostaje
dobe tuz po PIVOCIE, a `datetime` w module audytu jest podmieniany w procesie
na cztery kalendarze: niedziele, pierwszy dzien miesiaca, 29 lutego i
PRAWDZIWY cichy dzien wg `config.cichy_dzien`.

BEZ PYTESTA, zero sieci, zero wywolan modelu. Produkcyjna baza, produkcyjny
dziennik i produkcyjne `data/` NIETKNIETE. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_pominiecia_i_plan_w_audycie.py
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
from datetime import datetime, timedelta, timezone

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
             pathlib.Path("agent-v2/norma.py"),
             pathlib.Path("agent-v2/config.py"),
             pathlib.Path("agent-v2/run.py"),
             pathlib.Path("agent-v2/wzajemnosc.py"),
             pathlib.Path(config.DB_PATH),
             config.DATA_DIR / "dziennik.jsonl",
             config.DATA_DIR / "budzety.json"]
PRZED = {str(p): odcisk(p) for p in PILNOWANE}
DATA_PRZED = sorted(p.name for p in config.DATA_DIR.glob("*"))

TERAZ = pathlib.Path("agent-v2/audyt_systemu.py").resolve()

# SHA, NIE `HEAD`: `HEAD` przesuwa sie z commitem, ktorego ten test pilnuje.
POPRZEDNIA_WERSJA = "6ed4e7d"
KAT = pathlib.Path(tempfile.mkdtemp())
STARE = KAT / ("audyt_systemu_%s.py" % POPRZEDNIA_WERSJA)

# HISTORIA JEST WARUNKIEM TEGO TESTU — patrz `historia.py`. Straznik stoi
# PRZED pierwszym wywolaniem gita, bo ponizej git jest wolany juz na
# poziomie modulu i sprawdzenie po fakcie nie zdazyloby zadzialac.
import historia   # noqa: E402
historia.wymaga_historii("6ed4e7d")

STARE.write_bytes(subprocess.check_output(
    ["git", "show", "%s:agent-v2/audyt_systemu.py" % POPRZEDNIA_WERSJA]))

# Baza z trzema tabelami, ktorych `main()` dotyka, i to wylacznie SELECT-ami.
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

import audyt_systemu as _wzorzec   # noqa: E402


# DZIEN DZIENNIKA LICZY SIE ZE STALEJ, NIE Z KALENDARZA. `PIVOT` odsiewa wpisy
# starsze niz przestawienie konta na AI, wiec rozliczany dzien musi byc
# `>= PIVOT`; bierzemy sam PIVOT plus jeden, zeby etap 2 mial pelna dobe.
DZIEN = "%s-%02d" % (_wzorzec.PIVOT[:7], int(_wzorzec.PIVOT[8:]) + 1)
KIEDY = DZIEN + "T10:00:00+00:00"

# KALENDARZE, NA KTORYCH TEST MA PRZEJSC. Audyt pyta o „ostatni pelny dzien"
# wzgledem `datetime.now`, wiec zegar podmieniamy w procesie — inaczej wynik
# zalezalby od tego, ktorego dnia ktos uruchomi test. Cisza brana z PRAWDZIWEJ
# `config.cichy_dzien`.
KALENDARZE = ("2027-08-01",   # niedziela i pierwszy dzien miesiaca naraz
              "2028-02-29",   # dzien przestepny
              "2027-01-01",   # Nowy Rok
              "2027-01-07",   # PRAWDZIWY cichy dzien
              "2027-03-28")   # PRAWDZIWY cichy dzien i niedziela naraz


class Zegar:
    """`audyt_systemu` robi `from datetime import datetime` — podmieniamy nazwe."""

    def __init__(self, teraz):
        self.teraz = teraz

    def now(self, tz=None):
        return self.teraz

    def fromisoformat(self, *a, **k):
        return datetime.fromisoformat(*a, **k)


def wpis(rodzaj, udane=True, dzien=DZIEN, **reszta):
    return dict({"kiedy": dzien + "T10:00:00+00:00", "rodzaj": rodzaj,
                 "udane": udane}, **reszta)


def budzet(**zmiany):
    b = {"notki": 5, "komentarze": 10, "lajki": 12, "restacki": 2,
         "follow": 0, "subskrypcje": 0}
    b.update(zmiany)
    return b


_licznik = [0]


def _zaladuj(sciezka):
    """Swiezy obiekt modulu, zeby `WERDYKTY` nie przechodzily miedzy scenami."""
    _licznik[0] += 1
    nazwa = "audyt_probka_%d" % _licznik[0]
    spec = importlib.util.spec_from_file_location(nazwa, str(sciezka))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nazwa] = mod
    spec.loader.exec_module(mod)
    # `KATALOG` liczy sie z `__file__`, wiec kopia w `tempfile` szukalaby
    # `browser.py` obok siebie. Obie wersje maja czytac ten sam katalog.
    mod.KATALOG = pathlib.Path("agent-v2").resolve()
    return mod


def uruchom(sciezka, wpisy, budzety=None, kalendarz=None):
    """Prawdziwe `main()` na podstawionym dzienniku. Oddaje wydrukowany raport."""
    plik = KAT / "dziennik.jsonl"
    plik.write_text("".join(json.dumps(w, ensure_ascii=False) + "\n"
                            for w in wpisy), encoding="utf-8")
    (KAT / "budzety.json").write_text(
        json.dumps({d: {"budzet": b} for d, b in (budzety or {}).items()}),
        encoding="utf-8")
    mod = _zaladuj(sciezka)
    if kalendarz:
        mod.datetime = Zegar(datetime.strptime(kalendarz, "%Y-%m-%d").replace(
            hour=12, tzinfo=timezone.utc))
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


def rozliczane(kawalek):
    """Ktore rodzaje etap 2 NAPRAWDE rozliczyl z planu — z samego raportu."""
    return sorted(n.split()[1] for n in nazwy(kawalek) if n.startswith("plan "))


# =============================================================================
print("=== 1. TRZY STANY, TRZY LICZNIKI — PO KONCOWCE, NIE PO LISCIE ===")
# `policz_rodzaje` jest jedynym miejscem, w ktorym rozstrzyga sie, czym jest
# wpis — reszta pliku juz tylko sumuje.
_u, _n, _p = _wzorzec.policz_rodzaje(
    [wpis("subskrypcja"), wpis("subskrypcja", udane=False),
     wpis("subskrypcja_pominieta"), wpis("subskrypcja_pominieta"),
     wpis("obserwacja_pominieta"), wpis("notka")])
sprawdz("prawdziwa subskrypcja liczy sie jako udana",
        _u.get("subskrypcja") == 1, dict(_u))
sprawdz("nieudana subskrypcja liczy sie jako nieudana",
        _n.get("subskrypcja") == 1, dict(_n))
sprawdz("`subskrypcja_pominieta` NIE wchodzi do udanych",
        "subskrypcja_pominieta" not in _u, dict(_u))
sprawdz("ani do nieudanych", "subskrypcja_pominieta" not in _n, dict(_n))
sprawdz("ma za to wlasny licznik", _p.get("subskrypcja_pominieta") == 2, dict(_p))
sprawdz("i `obserwacja_pominieta` dalej tam stoi",
        _p.get("obserwacja_pominieta") == 1, dict(_p))
sprawdz("suma udanych to same proby (2), nie wszystkie wpisy z udane=True (5)",
        sum(_u.values()) == 2, sum(_u.values()))
# REGULA, NIE LISTA: rodzaj, ktorego w kodzie nie ma NIGDZIE, ma trafic do
# wlasciwej kupki od pierwszego dnia. To jest cala roznica miedzy krotka a
# koncowka i jedyny sposob, zeby to zmierzyc.
_u2, _n2, _p2 = _wzorzec.policz_rodzaje(
    [wpis("restack_pominieta"), wpis("restack_pominieta"), wpis("restack")])
sprawdz("RODZAJ, KTOREGO NIKT NIE DOPISAL (`restack_pominieta`), tez trafia"
        " do pominiec", _p2.get("restack_pominieta") == 2
        and "restack_pominieta" not in _u2 and "restack_pominieta" not in _n2,
        (dict(_u2), dict(_n2), dict(_p2)))

print()
print("=== 2. SZESC POMINIETYCH SUBSKRYPCJI NIE UDAJE SZESCIU PRAC ===")
# Ten sam dziennik dla obu wersji: 4 notki udane, 2 komentarze nieudane,
# 6 pominietych subskrypcji i ZERO subskrypcji prawdziwych.
PULA = ([wpis("notka")] * 4
        + [wpis("komentarz", udane=False, powod="brak pola")] * 2
        + [wpis("subskrypcja_pominieta", komu="ktos",
                powod="juz go subskrybujemy wedlug dziennika")] * 6)
RAPORT_NOWY, WYJ_NOWY = uruchom(TERAZ, PULA, {DZIEN: budzet()})
RAPORT_STARY, WYJ_STARY = uruchom(STARE, PULA, {DZIEN: budzet()})
E1_NOWY, E1_STARY = wytnij(RAPORT_NOWY, 1, 2), wytnij(RAPORT_STARY, 1, 2)

sprawdz("dzisiejszy audyt przeszedl caly raport bez wyjatku",
        WYJ_NOWY is None, repr(WYJ_NOWY))
sprawdz("wersja %s przeszla ten sam raport bez wyjatku" % POPRZEDNIA_WERSJA,
        WYJ_STARY is None, repr(WYJ_STARY))
sprawdz("2a szesc pominiec NIE robi z zera subskrypcji werdyktu OK",
        stan(E1_NOWY, "wychodzi: subskrypcja") == "UWAGA",
        stan(E1_NOWY, "wychodzi: subskrypcja"))
sprawdz("2b werdykt mowi o ZERZE, a nie o szesciu",
        szczegol(E1_NOWY, "wychodzi: subskrypcja") == "0 od %s" % _wzorzec.PIVOT,
        szczegol(E1_NOWY, "wychodzi: subskrypcja"))
sprawdz("2c raport pokazuje pominiecia osobno, z liczba",
        "pominiecia (ani sukces, ani porazka): subskrypcja_pominieta 6"
        in E1_NOWY, E1_NOWY)
sprawdz("2d i nie stawia ich w kolumnie „udane”",
        "subskrypcja_pominieta udane" not in E1_NOWY, E1_NOWY)
sprawdz("2e KONTRDOWOD: %s stawialo je w kolumnie „udane”, jako osobny rodzaj"
        % POPRZEDNIA_WERSJA,
        "subskrypcja_pominieta udane   6" in E1_STARY, E1_STARY)
# GDZIE DOKLADNIE SIEDZIALA SZKODA — mierzone na samym liczniku obu wersji.
# Werdykt „wychodzi: subskrypcja" NIE zmienial sie, bo stary licznik trzymal
# pominiecia pod WLASNYM kluczem („subskrypcja_pominieta"), a nie pod
# „subskrypcja". Falszywa byla SUMA: `sum(udane.values())` szlo z 4 na 10, a to
# jest mianownik progu porazek (sekcja 3) — i kazdy nastepny licznik, ktory tej
# sumy uzyje.
_STARY_MOD = _zaladuj(STARE)
_su, _sn, _sp = _STARY_MOD.policz_rodzaje(PULA)
_nu, _nn, _np = _wzorzec.policz_rodzaje(PULA)
sprawdz("2f KONTRDOWOD: u %s szesc pominiec bylo szescioma „udanymi” pracami"
        " (suma 10 zamiast 4)" % POPRZEDNIA_WERSJA,
        _su.get("subskrypcja_pominieta") == 6 and sum(_su.values()) == 10
        and not _sp, (dict(_su), dict(_sp)))
sprawdz("2g dzis ta sama pula daje sume prob 4 i szesc pominiec osobno",
        sum(_nu.values()) == 4 and _np.get("subskrypcja_pominieta") == 6,
        (dict(_nu), dict(_np)))

print()
print("=== 3. MIANOWNIK PROGU PORAZEK TO PROBY, NIE WPISY ===")
# Prawda: 2 porazki wobec 4 prac, czyli DOKLADNIE polowa — prog „mniej niz
# polowa" nie jest spelniony. Doliczenie pominiec do udanych robi z tego 2
# wobec 10 i werdykt sie uspokaja.
sprawdz("3a dwie porazki na cztery prace to nie jest „nie dominuja”",
        stan(E1_NOWY, "porazki nie dominuja") == "UWAGA",
        stan(E1_NOWY, "porazki nie dominuja"))
sprawdz("3b KONTRDOWOD: %s meldowalo tu OK, bo pominiecia podnosily mianownik"
        % POPRZEDNIA_WERSJA,
        stan(E1_STARY, "porazki nie dominuja") == "OK",
        stan(E1_STARY, "porazki nie dominuja"))

print()
print("=== 4. POMINIECIE NIE ZALICZA PLANU DNIA ===")
# Budzet zaklada 2 subskrypcje, wychodzi ZERO, a piec razy „juz go
# subskrybujemy". Plan ma byc niewykonany — pominiecie nie jest praca.
_r, _ = uruchom(TERAZ, [wpis("notka")] * 5 + [wpis("komentarz")] * 10
                + [wpis("polubienie")] * 12 + [wpis("restack")] * 2
                + [wpis("subskrypcja_pominieta")] * 5,
                {DZIEN: budzet(subskrypcje=2)})
_e2 = wytnij(_r, 2, 3)
sprawdz("4a plan 2 subskrypcji i piec pominiec to UWAGA, nie OK",
        stan(_e2, "plan subskrypcja w dniu %s" % DZIEN) == "UWAGA"
        and szczegol(_e2, "plan subskrypcja w dniu %s" % DZIEN)
        == "0 z 2 (zalozony)",
        [(s, n, d) for s, n, d in werdykty(_e2) if "subskrypcja" in n])

print()
print("=== 5. Z PLANU ROZLICZA SIE TO, CO MA PLAN — NIE WYPISANA LISTA ===")
# 5A. DOBA JAK 1 WRZESNIA W PRODUKCJI: `follow=0`, `subskrypcje=0`.
PELNY_DZIEN = ([wpis("notka")] * 5 + [wpis("komentarz")] * 10
               + [wpis("polubienie")] * 12 + [wpis("restack")] * 2)
_r0, _ = uruchom(TERAZ, PELNY_DZIEN, {DZIEN: budzet(follow=0, subskrypcje=0)})
_r0s, _ = uruchom(STARE, PELNY_DZIEN, {DZIEN: budzet(follow=0, subskrypcje=0)})
_e0, _e0s = wytnij(_r0, 2, 3), wytnij(_r0s, 2, 3)
sprawdz("5a przy planie ZERO obserwacja nie jest w ogole rozliczana",
        "obserwacja" not in rozliczane(_e0), rozliczane(_e0))
sprawdz("5b ani subskrypcja", "subskrypcja" not in rozliczane(_e0),
        rozliczane(_e0))
sprawdz("5c rozliczaja sie dokladnie te cztery, ktore maja plan >= 1",
        rozliczane(_e0) == ["komentarz", "notka", "polubienie", "restack"],
        rozliczane(_e0))
sprawdz("5d KONTRDOWOD: %s meldowalo UWAGA o obserwacji za dobe, ktorej plan"
        " wynosil ZERO" % POPRZEDNIA_WERSJA,
        stan(_e0s, "plan obserwacja w dniu %s" % DZIEN) == "UWAGA",
        [(s, n, d) for s, n, d in werdykty(_e0s) if "obserwacja" in n])
sprawdz("5e KONTRDOWOD: i podstawialo w miejsce zera ulamkowa NORME (0,43)",
        (szczegol(_e0s, "plan obserwacja w dniu %s" % DZIEN) or "")
        .startswith("0 z 0.43"),
        szczegol(_e0s, "plan obserwacja w dniu %s" % DZIEN))
sprawdz("5f KONTRDOWOD: a glownego kanalu nie rozliczalo wcale",
        "subskrypcja" not in rozliczane(_e0s), rozliczane(_e0s))

# 5B. DOBA, W KTOREJ BUDZET NAPRAWDE DAL OBU KANALOM PO SZTUCE.
_r1, _ = uruchom(TERAZ, PELNY_DZIEN, {DZIEN: budzet(follow=2, subskrypcje=1)})
_r1s, _ = uruchom(STARE, PELNY_DZIEN, {DZIEN: budzet(follow=2, subskrypcje=1)})
_e1, _e1s = wytnij(_r1, 2, 3), wytnij(_r1s, 2, 3)
sprawdz("5g przy planie 2 i 1 rozliczaja sie OBA kanaly",
        rozliczane(_e1) == ["komentarz", "notka", "obserwacja", "polubienie",
                            "restack", "subskrypcja"], rozliczane(_e1))
sprawdz("5h KONTRDOWOD: %s nie rozliczalo subskrypcji nawet przy planie 1"
        % POPRZEDNIA_WERSJA,
        "subskrypcja" not in rozliczane(_e1s), rozliczane(_e1s))
sprawdz("5i zero z planu 2 obserwacji to UWAGA",
        stan(_e1, "plan obserwacja w dniu %s" % DZIEN) == "UWAGA"
        and szczegol(_e1, "plan obserwacja w dniu %s" % DZIEN)
        == "0 z 2 (zalozony)",
        [(s, n, d) for s, n, d in werdykty(_e1) if "obserwacja" in n])

# 5C. TA SAMA REGULA BEZ ZAPISANEGO BUDZETU — wtedy plan bierze sie z normy,
# a norma obu rzadkich kanalow jest MNIEJSZA niz jedna sztuka na dobe.
_r2, _ = uruchom(TERAZ, PELNY_DZIEN, {})
_e2b = wytnij(_r2, 2, 3)
sprawdz("5j bez zapisanego budzetu rozliczaja sie tylko rodzaje o normie >= 1",
        rozliczane(_e2b) == ["komentarz", "notka", "polubienie", "restack"],
        rozliczane(_e2b))
_normy = config.normy_dzienne()
print("    normy dobowe: obserwacja %.3f, subskrypcja %.3f (prog: %d)"
      % (_normy["obserwacja"], _normy["subskrypcja"],
         _wzorzec.MIN_PLAN_DNIA_DO_ROZLICZENIA))
sprawdz("5k i to wynika z LICZB, nie z nazw: obie normy sa ponizej progu",
        _normy["obserwacja"] < _wzorzec.MIN_PLAN_DNIA_DO_ROZLICZENIA
        and _normy["subskrypcja"] < _wzorzec.MIN_PLAN_DNIA_DO_ROZLICZENIA,
        (_normy["obserwacja"], _normy["subskrypcja"]))
sprawdz("5l `odpowiedz` nie rozlicza sie nigdy — nie ma ani budzetu, ani normy",
        "odpowiedz" not in rozliczane(_e1) and "odpowiedz" not in rozliczane(_e0),
        (rozliczane(_e0), rozliczane(_e1)))

print()
print("=== 6. REGULA NIE ZALEZY OD KALENDARZA ===")
# Etap 2 pyta o „ostatni pelny dzien" wzgledem `datetime.now`, wiec zegar
# podmieniamy w procesie. Wynik ma byc ten sam na kazdej z tych dat.
for _kal in KALENDARZE:
    _cicho = config.cichy_dzien(datetime.strptime(DZIEN, "%Y-%m-%d")
                                .replace(tzinfo=timezone.utc))
    _rk, _wyj = uruchom(TERAZ, PELNY_DZIEN,
                        {DZIEN: budzet(follow=0, subskrypcje=0)}, kalendarz=_kal)
    _ek = wytnij(_rk, 2, 3)
    sprawdz("6 [%s] ten sam zestaw rozliczanych rodzajow" % _kal,
            _wyj is None
            and rozliczane(_ek) == ["komentarz", "notka", "polubienie",
                                    "restack"],
            (repr(_wyj), rozliczane(_ek)))
print("    (rozliczany dzien %s wg config.cichy_dzien: %s)"
      % (DZIEN, "CICHY" if _cicho else "zwykly"))

print()
print("=== PRODUKCJA: bez zmian ===")
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
