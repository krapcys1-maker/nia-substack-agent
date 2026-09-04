# -*- coding: utf-8 -*-
"""Wybor celu przestaje byc losem, a budzety ida za skutkiem.

## Co bylo zepsute

`run.py::obserwuj` i `run.py::subskrybuj` robily `random.shuffle` na CALEJ
historii komentarzy. Zero kryteriow: ani wielkosci, ani tematu, ani jezyka,
ani swiezosci. `subskrybuj` nie sprawdzalo dodatkowo, czy juz kogos
subskrybujemy — i nie zostawialo sladu, gdy nie ustalilo uchwytu.

## Pomiary, na ktorych stoi ten test (1 wrzesnia 2026, produkcyjne pliki)

`agent-v2/data/gdzie_komentowalismy.json` (serwer, 6146 B):

    94 hosty razem
    53 z ostatnim komentarzem SPRZED 2026-08-25 (przestawienie konta na AI)
    41 z ostatnim komentarzem OD 2026-08-25

`agent-v2/data/dziennik.jsonl` (serwer, 635 wierszy):

    199 wpisow `rodzaj="skutek"`, 69 roznych osob w polu `kto`
     18 prob `rodzaj="subskrypcja"`, z tego 6 nieudanych
      2 proby `rodzaj="obserwacja"`, obie nieudane (23 sierpnia)

Puszczone przez `run.cele_wedlug_pierwszenstwa` na tych DWOCH plikach:

    rachunek {'wszystkich': 94, 'sprzed_przestawienia': 53,
              'po_przestawieniu': 41, 'ze_skutkiem': 3}
    poziom skutku: igordziewiaty.substack.com, www.ryanpuzycki.com, davidoks.blog
    `kogo_juz_subskrybujemy` -> 14 uchwytow
    tanie sito odsiewa 2 z 41: publikacja-b, tiffaniedarke

`www.ryanpuzycki.com` (-> `puzycki`, zasubskrybowany 30 sierpnia) NIE wpada
w tanie sito, bo to wlasna domena — lapie go dopiero sprawdzenie PO
rozwiazaniu uchwytu i to jest osobno mierzone nizej.

WPIS `skutek` NIE NIESIE UCHWYTU: `browser.dopisz_skutki` ma pod reka caly
obiekt uzytkownika i zapisuje z niego wylacznie `name`. Z 69 osob da sie
zamienic na cel 7 (rownosc slugu nazwy ze slugiem hosta), a przez
`czytelnicy.jsonl` — 11, i akurat te 11 to nasi wlasni czytelnicy. Dlatego
poziom „juz sie zetknal z nasza trescia" jest tu SLABSZY niz w zamysle
i test mierzy dokladnie tyle, ile z niego naprawde wychodzi.

## Co ten test mierzy

ZACHOWANIE PRODUKCJI, nie tresc zrodel. Bloki `obserwuj` i `subskrybuj` sa
wycinane z `run.py` przez `ast` i URUCHAMIANE na atrapie Substacka; dziennik
jest prawdziwy (przekierowany do katalogu tymczasowego), a to, czy wpis liczy
sie jako wykonany albo nieudany, rozstrzyga PRAWDZIWA `norma.wczytaj`.
Budzety licza sie prawdziwym `stages.budzet_dnia`, nie sredniej z widelek.

KONTRDOWOD JEST ODTWARZANY, NIE OPISANY, i PRZYPIETY DO SHA `6ed4e7d`, nie do
HEAD — kontrdowod mierzony wzgledem HEAD gasnie w chwili commita, ktorego
strzeze.

Zero sieci, zero przegladarki, zero wywolan modelu, zero zapisu do produkcji.
Test nie zalezy od dzisiejszej daty: wszystkie daty w danych sa stalymi.
"""

import ast
import datetime as _dt
import hashlib
import io
import json
import pathlib
import random
import subprocess
import sys
import tempfile
import types

KORZEN = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(KORZEN / "agent-v2"))

import browser        # noqa: E402
import config         # noqa: E402
import norma          # noqa: E402
import run            # noqa: E402
import stages         # noqa: E402

# HISTORIA JEST WARUNKIEM TEGO TESTU — patrz `historia.py`.
import historia   # noqa: E402
historia.wymaga_historii("6ed4e7d")

ODNIESIENIE = "6ed4e7d"        # wersja SPRZED poprawki; nigdy HEAD

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


PILNOWANE = [config.DB_PATH,
             config.DATA_DIR / "dziennik.jsonl",
             config.DATA_DIR / "budzety.json",
             config.DATA_DIR / "kogo_obserwujemy.json",
             config.DATA_DIR / "gdzie_komentowalismy.json"]
PRZED = {str(p): odcisk(p) for p in PILNOWANE}


# --- ATRAPA SUBSTACKA --------------------------------------------------------
#
# Jedna atrapa na dwa bloki, bo obie drogi ida przez ten sam profil: „Subscribe"
# lezy na wierzchu strony, „Follow" siedzi w menu pod kolkiem „...". Etykiety
# odwzorowuja pomiar z 1 wrzesnia zapisany w `test_obserwowanie_przez_menu.py`.
MENU_WOLNY = ["Copy link", "Share", "Send message", "Follow",
              "Mute", "Block", "Report"]
MENU_OBSERWOWANY = ["Copy link", "Share", "Send message", "Unfollow",
                    "Mute", "Block", "Report"]


class Substack:
    """Prawda o koncie: kogo obserwujemy, kogo subskrybujemy, co dotkniete."""

    def __init__(self, obserwowani=(), zasubskrybowani=()):
        self.obserwowani = set(obserwowani)
        self.zasubskrybowani = set(zasubskrybowani)
        self.sesje = 0
        self.odwiedzone = []
        self.klikniete = []


class Przycisk:
    """„Subscribe" na wierzchu profilu. Znika po klknieciu — jak u Substacka."""

    def __init__(self, strona, tekst):
        self.strona, self.tekst = strona, tekst

    def _jest(self):
        return self.strona.handle not in self.strona.konta.zasubskrybowani

    def count(self):
        return 1 if self._jest() else 0

    def is_visible(self):
        return self._jest()

    def click(self, timeout=None):
        self.strona.konta.klikniete.append(self.tekst)
        self.strona.konta.zasubskrybowani.add(self.strona.handle)


class Wezel:
    def __init__(self, strona, tekst, rodzaj):
        self.strona, self.tekst, self.rodzaj = strona, tekst, rodzaj

    def inner_text(self):
        return self.tekst

    def count(self):
        return 0 if self.rodzaj == "brak" else 1

    def is_visible(self):
        return self.rodzaj != "brak"

    def click(self, timeout=None):
        self.strona.konta.klikniete.append(self.tekst)
        if self.rodzaj == "kolko":
            self.strona.menu_otwarte = True
            return
        if self.tekst in ("Follow", "Obserwuj"):
            self.strona.konta.obserwowani.add(self.strona.handle)
        if self.tekst in ("Unfollow", "Przestań obserwować"):
            self.strona.konta.obserwowani.discard(self.strona.handle)
        self.strona.menu_otwarte = False


class Lista:
    def __init__(self, wezly):
        self.wezly = wezly

    def count(self):
        return len(self.wezly)

    @property
    def first(self):
        return self.wezly[0] if self.wezly else Wezel(None, "", "brak")

    def nth(self, i):
        return self.wezly[i] if i < len(self.wezly) else Wezel(None, "", "brak")


class Klawiatura:
    def __init__(self, strona):
        self.strona = strona

    def press(self, klawisz):
        if klawisz == "Escape":
            self.strona.menu_otwarte = False


class Strona:
    def __init__(self, konta):
        self.konta = konta
        self.handle = ""
        self.menu_otwarte = False
        self.keyboard = Klawiatura(self)

    def goto(self, url, **k):
        self.handle = str(url).split("/@", 1)[-1].split("/")[0]
        self.menu_otwarte = False
        self.konta.odwiedzone.append(self.handle)

    def wait_for_timeout(self, *a):
        pass

    def close(self):
        pass

    def locator(self, selektor):
        if 'aria-label="Profile actions"' in selektor:
            return Lista([Wezel(self, "Profile actions", "kolko")])
        return Lista([])

    def get_by_role(self, rola, name=None, exact=False):
        if rola == "button" and name in ("Subscribe", "Subskrybuj"):
            p = Przycisk(self, name)
            return Lista([p] if p.count() else [])
        if rola == "menuitem" and self.menu_otwarte:
            pozycje = (MENU_OBSERWOWANY if self.handle in self.konta.obserwowani
                       else MENU_WOLNY)
            return Lista([Wezel(self, t, "menuitem") for t in pozycje])
        return Lista([])


class Przegladarka:
    def __init__(self, konta):
        self.konta = konta

    def new_page(self):
        return Strona(self.konta)

    def close(self):
        pass

    def stop(self):
        pass


# --- WYCINANIE BLOKOW Z `run.py` ---------------------------------------------
#
# Bloki sa funkcjami ZAGNIEZDZONYMI w `dzien()`, wiec nie da sie ich
# zaimportowac. Wycinamy je po `ast` i uruchamiamy w przygotowanej przestrzeni
# nazw — dzieki temu test mierzy PRAWDZIWY kod produkcyjny, a nie jego opis.
def zrodlo_run(commit=None) -> str:
    if commit is None:
        return (KORZEN / "agent-v2" / "run.py").read_text(encoding="utf-8")
    proc = subprocess.run(["git", "-C", str(KORZEN), "show",
                           "%s:agent-v2/run.py" % commit], capture_output=True)
    if proc.returncode != 0:
        raise SystemExit("nie dostalem run.py z %s: %s"
                         % (commit, proc.stderr.decode("utf-8", "replace")[:200]))
    return proc.stdout.decode("utf-8")


def wytnij(src: str, nazwa: str) -> str:
    for w in ast.walk(ast.parse(src)):
        if isinstance(w, ast.FunctionDef) and w.name == nazwa:
            linie = src.splitlines()[w.lineno - 1:w.end_lineno]
            wciecie = len(linie[0]) - len(linie[0].lstrip())
            return "\n".join(x[wciecie:] if x[:wciecie].strip() == "" else x
                             for x in linie)
    raise SystemExit("nie znalazlem funkcji %s" % nazwa)


def stale_z_commita(commit: str, *nazwy) -> dict:
    """Wartosci stalych `config.py` z ZAPISANEJ wersji. Bez importowania jej."""
    proc = subprocess.run(["git", "-C", str(KORZEN), "show",
                           "%s:agent-v2/config.py" % commit], capture_output=True)
    if proc.returncode != 0:
        raise SystemExit("nie dostalem config.py z %s" % commit)
    drzewo = ast.parse(proc.stdout.decode("utf-8"))
    wynik = {}
    for w in drzewo.body:
        if isinstance(w, ast.Assign) and len(w.targets) == 1 \
                and isinstance(w.targets[0], ast.Name) \
                and w.targets[0].id in nazwy:
            wynik[w.targets[0].id] = ast.literal_eval(w.value)
    brak = set(nazwy) - set(wynik)
    if brak:
        raise SystemExit("brak stalych %s w %s" % (sorted(brak), commit))
    return wynik


class Kanal:
    """Historia komentarzy — jedyne zrodlo puli. Odwzorowuje `kanal._historia`.

    Wartosc to data OSTATNIEGO komentarza, bo `kanal.zapamietaj_komentarz`
    nadpisuje ja przy kazdym kolejnym. Na tym stoi caly odsiew tematyczny.
    """

    def __init__(self, hosty: dict):
        self.hosty = dict(hosty)

    def _historia(self):
        return dict(self.hosty)


def uruchom_blok(kod_bloku, nazwa, historia, konta, budzet=1,
                 kolejnosc=(), dziennik_wstepny=(), pamiec=None):
    """Puszcza blok na atrapie. Oddaje (konta, wpisy, plik dziennika, wydruk).

    Dziennik jest PRAWDZIWY — tylko przekierowany do katalogu tymczasowego.
    `random.shuffle` zastapione ustaleniem kolejnosci, bo test nie moze zalezec
    od losu; kolejnosc POZIOMOW rozstrzyga sam kod, nie ta podmiana.
    """
    katalog = pathlib.Path(tempfile.mkdtemp())
    plik = katalog / "dziennik.jsonl"
    if dziennik_wstepny:
        plik.write_text("".join(json.dumps(w, ensure_ascii=False) + "\n"
                                for w in dziennik_wstepny), encoding="utf-8")

    def podlacz():
        konta.sesje += 1
        p = Przegladarka(konta)
        return p, p, p

    def uchwyt_publikacji(host):
        # Zmierzone zachowanie prawdziwej funkcji: dla domeny Substacka nazwa
        # konta to pierwszy czlon hosta, dla wlasnej domeny wychodzi z API.
        host = (host or "").strip().lower()
        if host.endswith(".substack.com"):
            return host.split(".")[0]
        return {"www.ryanpuzycki.com": "puzycki",
                "www.a16z.news": "a16z",
                "www.wlasnadomena.example": "autor1"}.get(host)

    stare = {k: getattr(browser, k) for k in
             ("podlacz_sie", "wymagaj_sesji", "naprawde_wyslac",
              "uchwyt_publikacji", "DZIENNIK", "OBSERWOWANI")}
    stary_shuffle = random.shuffle
    stara_norma = norma.DZIENNIK
    try:
        browser.podlacz_sie = podlacz
        browser.wymagaj_sesji = lambda: None
        browser.naprawde_wyslac = lambda w, co: w
        browser.uchwyt_publikacji = uchwyt_publikacji
        browser.DZIENNIK = plik
        browser.OBSERWOWANI = katalog / "kogo_obserwujemy.json"
        if pamiec:
            browser.OBSERWOWANI.write_text(json.dumps(pamiec, ensure_ascii=False),
                                           encoding="utf-8")
        norma.DZIENNIK = plik
        random.shuffle = lambda lst: lst.sort(
            key=lambda h: kolejnosc.index(h) if h in kolejnosc else 99)

        ns = {"browser": browser, "config": config, "kanal": Kanal(historia),
              "na_teraz": {"follow": budzet, "subskrypcje": budzet},
              "wyslij": True, "rytm_stanu": {},
              "zostal_czas": lambda *a, **k: True,
              "rytm": lambda *a, **k: True, "print": print,
              # Pomocnicy z poziomu modulu `run` — blok jest funkcja
              # zagniezdzona, wiec normalnie widzi je przez globals() modulu.
              "cele_wedlug_pierwszenstwa": run.cele_wedlug_pierwszenstwa,
              "powod_pustej_puli": run.powod_pustej_puli,
              "kogo_juz_subskrybujemy": run.kogo_juz_subskrybujemy,
              "czy_juz_subskrybujemy": run.czy_juz_subskrybujemy,
              "PRZESTAWIENIE_KONTA_NA_AI": run.PRZESTAWIENIE_KONTA_NA_AI}
        exec(compile(kod_bloku, "run.py::%s" % nazwa, "exec"), ns)
        buf, stare_out = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            ns[nazwa]()
        finally:
            sys.stdout = stare_out
        wpisy = []
        if plik.exists():
            wpisy = [json.loads(x) for x in
                     plik.read_text(encoding="utf-8").splitlines() if x.strip()]
        return konta, wpisy, plik, buf.getvalue()
    finally:
        random.shuffle = stary_shuffle
        norma.DZIENNIK = stara_norma
        for k, v in stare.items():
            setattr(browser, k, v)


def licz_norma(plik_dziennika, rodzaj):
    """(wykonane, nieudane, dni ze sladem) wedlug PRAWDZIWEJ `norma.wczytaj`."""
    stara = norma.DZIENNIK
    try:
        norma.DZIENNIK = plik_dziennika
        zrobione, nieudane = norma.wczytaj(14)
        _, ze_sladem = norma.slad_dziennika({})
        return (sum(d[rodzaj] for d in zrobione.values()),
                sum(d[rodzaj] for d in nieudane.values()),
                len(ze_sladem))
    finally:
        norma.DZIENNIK = stara


# --- DANE Z POMIARU ----------------------------------------------------------
#
# Osiem hostow odwzorowujacych proporcje produkcji: cztery sprzed przestawienia
# konta (tematy z tamtego okresu), cztery po nim, w tym jeden juz
# zasubskrybowany w domenie Substacka i jeden juz zasubskrybowany na wlasnej
# domenie — bo te dwa lapia sie na dwoch ROZNYCH etapach odsiewu.
HISTORIA = {
    # sprzed 2026-08-25 — jedzenie, zdrowie, moda, literatura
    "thebuttergirlfriend.substack.com": "2026-08-16T13:00:00+00:00",
    "publikacja4.substack.com":          "2026-08-16T13:14:10+00:00",
    "dagmarabeine.substack.com":        "2026-08-16T16:21:21+00:00",
    "writersartistsyearbook.substack.com": "2026-08-23T07:00:00+00:00",
    # od 2026-08-25 wlacznie
    "igordziewiaty.substack.com":     "2026-08-31T10:00:00+00:00",
    "www.a16z.news":               "2026-08-30T09:00:00+00:00",
    "publikacja-b.substack.com": "2026-08-29T20:17:52+00:00",
    "www.ryanpuzycki.com":         "2026-08-28T11:00:00+00:00",
}
TYLKO_STARE = {h: k for h, k in HISTORIA.items() if k[:10] < "2026-08-25"}

# Trzy prawdziwe wiersze z produkcyjnego dziennika, przepisane co do pola.
DZIENNIK_WSTEPNY = [
    {"kiedy": "2026-08-16T17:53:00+00:00", "rodzaj": "subskrypcja",
     "udane": True, "komu": "publikacja-b"},
    {"kiedy": "2026-08-30T11:53:32+00:00", "rodzaj": "subskrypcja",
     "udane": True, "komu": "puzycki"},
    # Osoba, ktora zareagowala na nasza tresc. Uchwytu tu NIE MA — jest tylko
    # nazwa, i to jest cala slabosc tego poziomu.
    {"kiedy": "2026-08-31T11:38:09+00:00", "rodzaj": "skutek", "udane": True,
     "zdarzenie": "note_like:327008677", "typ": "note_like", "czego": 327008677,
     "ilu": 1, "kto": ["Igor Dziewiaty"], "kiedy_zdarzenia": "2026-08-31T02:04:35"},
]

BLOK_OBSERWUJ = wytnij(zrodlo_run(), "obserwuj")
BLOK_SUBSKRYBUJ = wytnij(zrodlo_run(), "subskrybuj")


print("=== 1. KRYTERIUM DOBORU: DATA JEST TWARDA, SKUTEK PODNOSI ===")
_kat = pathlib.Path(tempfile.mkdtemp())
_stary_dziennik = browser.DZIENNIK
_stary_shuffle = random.shuffle
try:
    browser.DZIENNIK = _kat / "dziennik.jsonl"
    browser.DZIENNIK.write_text(
        "".join(json.dumps(w, ensure_ascii=False) + "\n"
                for w in DZIENNIK_WSTEPNY), encoding="utf-8")
    random.shuffle = lambda lst: None          # kolejnosc wewnatrz poziomu
    kand, rach = run.cele_wedlug_pierwszenstwa(HISTORIA)
    print("    rachunek: %s" % rach)
    print("    kandydaci: %s" % kand)
    sprawdz("rachunek liczy oba poziomy osobno",
            (rach["wszystkich"], rach["sprzed_przestawienia"],
             rach["po_przestawieniu"]) == (8, 4, 4), rach)
    sprawdz("ZADEN host sprzed przestawienia konta nie wchodzi do puli",
            not (set(kand) & set(TYLKO_STARE)), kand)
    sprawdz("wszystkie cztery po przestawieniu wchodza", len(kand) == 4, kand)
    sprawdz("host z reakcja na nasza tresc stoi PIERWSZY",
            kand[0] == "igordziewiaty.substack.com", kand)
    sprawdz("i jest policzony jako poziom pierwszy",
            rach["ze_skutkiem"] == 1, rach)

    # NASZ WLASNY HOST NIGDY NIE JEST CELEM — zabezpieczenie sprzed poprawki,
    # ktore musi przezyc zmiane kryterium.
    z_naszym = dict(HISTORIA)
    z_naszym["%s.substack.com" % config.SUBSTACK_HANDLE] = "2026-08-31T10:00:00"
    kand2, _ = run.cele_wedlug_pierwszenstwa(z_naszym)
    sprawdz("wlasny host odsiany mimo swiezej daty",
            "%s.substack.com" % config.SUBSTACK_HANDLE not in kand2, kand2)

    # DATA NIECZYTELNA TO NIE JEST ZGODA. Host bez daty wypada, bo cena
    # pomylki jest niesymetryczna: mail do kogos, kogo przestalismy czytac,
    # jest drozszy niz jeden kandydat mniej w puli, ktora rosnie codziennie.
    kand3, rach3 = run.cele_wedlug_pierwszenstwa({"ktos.substack.com": None,
                                                  "inny.substack.com": ""})
    sprawdz("host bez czytelnej daty wypada, a nie wpada",
            kand3 == [] and rach3["sprzed_przestawienia"] == 2, (kand3, rach3))

    # SLABOSC POZIOMU PIERWSZEGO, ZMIERZONA WPROST. Wpis `skutek` niesie samo
    # `kto` (nazwe), wiec osoba, ktorej nazwa nie sklada sie na host, jest dla
    # doboru celu niewidzialna — mimo ze to najmocniejszy sygnal, jaki mamy.
    browser.DZIENNIK.write_text(json.dumps(
        {"kiedy": "2026-08-31T11:38:09+00:00", "rodzaj": "skutek",
         "udane": True, "zdarzenie": "note_like:1", "typ": "note_like",
         "kto": ["Publikacja Chaosu"], "ilu": 1}, ensure_ascii=False) + "\n",
        encoding="utf-8")
    _, rach4 = run.cele_wedlug_pierwszenstwa(HISTORIA)
    sprawdz("osoba, ktorej nazwa nie jest hostem, NIE podnosi nikogo",
            rach4["ze_skutkiem"] == 0, rach4)
    sprawdz("a slugi z dziennika i tak sa wczytane",
            "chaosengine" in run.kogo_juz_dotknelismy(),
            sorted(run.kogo_juz_dotknelismy()))
finally:
    random.shuffle = _stary_shuffle
    browser.DZIENNIK = _stary_dziennik


print()
print("=== 2. OBSERWACJA: HOST SPRZED PRZESTAWIENIA NIE DOSTAJE MAILA ===")
# Pula ma WYLACZNIE hosty sprzed przestawienia konta. Obserwacja wysyla
# powiadomienie mailem, a nasza lista obserwowanych jest publiczna — wiec
# poprawnym wynikiem jest ZERO Z POWODEM, nie „to wezmy kogokolwiek".
konta, wpisy, plik, out = uruchom_blok(
    BLOK_OBSERWUJ, "obserwuj", TYLKO_STARE, Substack(),
    kolejnosc=tuple(TYLKO_STARE))
print("    odwiedzone profile: %s" % konta.odwiedzone)
print("    wpisy: %s" % [(w["rodzaj"], w.get("udane")) for w in wpisy])
sprawdz("ZERO sesji przegladarki — nikt nie dostal powiadomienia",
        konta.sesje == 0 and konta.odwiedzone == [], konta.odwiedzone)
sprawdz("nikogo nie zaobserwowalismy", konta.obserwowani == set(),
        konta.obserwowani)
sprawdz("ale wpis jest — blok bez sladu wyglada na blok, ktorego nie ma",
        [w["rodzaj"] for w in wpisy] == ["obserwacja_pominieta"], wpisy)
sprawdz("powod niesie LICZBY, nie ogolnik",
        "4 sprzed przestawienia" in (wpisy[0].get("powod") or "")
        and "0 po nim" in (wpisy[0].get("powod") or ""), wpisy)
wyk, nieud, dni = licz_norma(plik, "obserwacja")
print("    norma.wczytaj -> wykonane=%d nieudane=%d dni=%d" % (wyk, nieud, dni))
sprawdz("licznik nie liczy tego ani do wykonanych, ani do nieudanych",
        (wyk, nieud) == (0, 0), (wyk, nieud))
sprawdz("ale dzien ma slad", dni == 1, dni)

# A GDY W PULI JEST KTOS SWIEZY — blok ma isc po niego, i to po tego z reakcja.
konta, wpisy, plik, out = uruchom_blok(
    BLOK_OBSERWUJ, "obserwuj", HISTORIA, Substack(),
    kolejnosc=tuple(HISTORIA), dziennik_wstepny=DZIENNIK_WSTEPNY)
print("    odwiedzone profile: %s" % konta.odwiedzone)
sprawdz("weszlismy na JEDEN profil i to ten z reakcja na nasza tresc",
        konta.odwiedzone == ["igordziewiaty"], konta.odwiedzone)
sprawdz("obserwacja weszla", "igordziewiaty" in konta.obserwowani,
        konta.obserwowani)
wyk, nieud, _ = licz_norma(plik, "obserwacja")
sprawdz("i licznik widzi JEDNA wykonana obserwacje, zero porazek",
        (wyk, nieud) == (1, 0), (wyk, nieud))


print()
print("=== 3. SUBSKRYPCJA: DUBEL NIE ZJADA SLOTU ===")
# `publikacja-b` jest w domenie Substacka, wiec lapie go TANIE sito —
# jeszcze zanim ktokolwiek otworzy przegladarke. Pula ma tylko jego, wiec
# poprawnym wynikiem jest wpis „pula wyczerpana", a nie proba.
konta, wpisy, plik, out = uruchom_blok(
    BLOK_SUBSKRYBUJ, "subskrybuj",
    {"publikacja-b.substack.com": "2026-08-29T20:17:52+00:00"},
    Substack(zasubskrybowani={"publikacja-b"}),
    kolejnosc=("publikacja-b.substack.com",),
    dziennik_wstepny=DZIENNIK_WSTEPNY)
print("    odwiedzone profile: %s" % konta.odwiedzone)
print("    wpisy: %s" % [(w["rodzaj"], w.get("udane")) for w in wpisy[3:]])
sprawdz("TANIE SITO: zero sesji przegladarki na juz zasubskrybowanym",
        konta.sesje == 0 and konta.odwiedzone == [], konta.odwiedzone)
sprawdz("wpis o pominieciu jest i nie jest porazka",
        [w["rodzaj"] for w in wpisy[3:]] == ["subskrypcja_pominieta"]
        and wpisy[-1].get("udane") is True, wpisy[3:])
wyk, nieud, dni = licz_norma(plik, "subskrypcja")
print("    norma.wczytaj -> wykonane=%d nieudane=%d dni=%d" % (wyk, nieud, dni))
sprawdz("NOWY RODZAJ JEST POZA `norma.RODZAJE` — ani sukces, ani porazka",
        "subskrypcja_pominieta" not in norma.RODZAJE, norma.RODZAJE)
# LICZBY BEZWZGLEDNE ZALEZALYBY OD KALENDARZA: `norma.wczytaj(14)` ma okno
# 14 dni, a wpisy wstepne sa datowane na sierpien. Mierzymy wiec to, co ten
# przebieg DOLOZYL, i to jest dokladnie pytanie, o ktore chodzi.
NIEUD_DUBEL = nieud
sprawdz("pominiecie nie dolozylo ANI JEDNEJ porazki", nieud == 0, nieud)

# WLASNA DOMENA: `www.ryanpuzycki.com` -> `puzycki`. Tanie sito go nie widzi
# (nie ma mapy host->uchwyt), wiec kosztuje jedno zapytanie o uchwyt — ale NIE
# kosztuje slotu: blok bierze nastepnego kandydata i subskrybuje jego.
konta, wpisy, plik, out = uruchom_blok(
    BLOK_SUBSKRYBUJ, "subskrybuj",
    {"www.ryanpuzycki.com": "2026-08-28T11:00:00+00:00",
     "www.a16z.news": "2026-08-30T09:00:00+00:00"},
    Substack(zasubskrybowani={"puzycki"}),
    kolejnosc=("www.ryanpuzycki.com", "www.a16z.news"),
    dziennik_wstepny=DZIENNIK_WSTEPNY)
print("    odwiedzone profile: %s" % konta.odwiedzone)
print("    klikniete: %s" % konta.klikniete)
sprawdz("na profil juz zasubskrybowanego NIE weszlismy",
        "puzycki" not in konta.odwiedzone, konta.odwiedzone)
sprawdz("SLOT NIE PRZEPADL: nastepny kandydat zostal zasubskrybowany",
        "a16z" in konta.zasubskrybowani, konta.zasubskrybowani)
sprawdz("i to jedna subskrypcja, nie dwie", konta.klikniete == ["Subscribe"],
        konta.klikniete)
wyk, nieud, _ = licz_norma(plik, "subskrypcja")
print("    norma.wczytaj -> wykonane=%d nieudane=%d" % (wyk, nieud))
sprawdz("licznik zapisal nowa subskrypcje i zadnej porazki",
        wyk >= 1 and nieud == 0, (wyk, nieud))

# NIEUSTALONY UCHWYT ZOSTAWIA SLAD. Do 1 wrzesnia byl tu cichy `continue`
# i trzy proby zapisane jako `komu='www'` nie mowily, o ktory adres chodzilo.
konta, wpisy, plik, out = uruchom_blok(
    BLOK_SUBSKRYBUJ, "subskrybuj",
    {"nieznana.domena.example": "2026-08-30T09:00:00+00:00"},
    Substack(), kolejnosc=("nieznana.domena.example",))
sprawdz("host bez uchwytu zapisuje PORAZKE Z ADRESEM, nie cisze",
        [w["rodzaj"] for w in wpisy] == ["subskrypcja"]
        and wpisy[0].get("udane") is False
        and wpisy[0].get("komu") == "nieznana.domena.example", wpisy)
# ADRES JEST W `komu`, NIE W `powod`, I TO NIE JEST NASZ WYBOR.
# `browser.dopisz_wynik` NADPISUJE `powod` przekazany przez wolajacego, bo
# przy `udane=False` wylicza go sobie sam z pol `wynik`. Blok `obserwuj` traci
# na tym swoje „nie ustalilem konta autora dla ..." dokladnie tak samo, od
# 1 wrzesnia. Zapisujemy to tutaj jako ZMIERZONY FAKT o cudzym pliku, zeby nie
# udawac, ze przekazany powod gdziekolwiek dolatuje.
sprawdz("zmierzony skutek cudzego `dopisz_wynik`: powod wolajacego przepada",
        wpisy[0].get("powod") == browser.POWOD_HOST_NIE_POKAZUJE, wpisy)
sprawdz("ale wpis NIE obciaza hosta — to awaria po naszej stronie",
        wpisy[0].get("o_hoscie") is False, wpisy)

# ODMOWA PROFILU JEST PAMIETANA. Konto, ktore odpowiedzialo „nie ma przycisku
# subskrypcja", nie wraca do puli — to jest dokladnie wpis, ktory 25 sierpnia
# powstal na `publikacja-b`.
_kat = pathlib.Path(tempfile.mkdtemp())
_stary_dziennik = browser.DZIENNIK
try:
    browser.DZIENNIK = _kat / "dziennik.jsonl"
    browser.DZIENNIK.write_text(json.dumps(
        {"kiedy": "2026-08-25T11:38:21+00:00", "rodzaj": "subskrypcja",
         "udane": False, "komu": "publikacja-b",
         "powod": "nie ma przycisku subskrypcja u publikacja-b"},
        ensure_ascii=False) + "\n", encoding="utf-8")
    zamk = run.kogo_juz_subskrybujemy()
    sprawdz("odmowa „nie ma przycisku subskrypcja” zamyka konto",
            "publikacja-b" in zamk, zamk)
    # ALE „NIE WIEM" NIE JEST DOWODEM: timeout albo zamkniety Chrome to awaria
    # po NASZEJ stronie i nie moze skreslac konta na zawsze.
    browser.DZIENNIK.write_text(json.dumps(
        {"kiedy": "2026-08-25T11:38:21+00:00", "rodzaj": "subskrypcja",
         "udane": False, "komu": "ktostam",
         "powod": "TimeoutError: page.goto"}, ensure_ascii=False) + "\n",
        encoding="utf-8")
    zamk = run.kogo_juz_subskrybujemy()
    sprawdz("awaria po naszej stronie NIE zamyka konta",
            "ktostam" not in zamk, zamk)
finally:
    browser.DZIENNIK = _stary_dziennik


print()
print("=== 4. BUDZETY: LICZONE PRAWDZIWYM `stages.budzet_dnia` ===")
#
# NIE SREDNIA Z WIDELEK. `z_miesiaca` dzieli wylosowana liczbe przez 30
# i rozstrzyga ulamek osobnym losowaniem, a rozbieg scina gorna polowe widelek
# — zadnej z tych dwoch rzeczy nie widac po samym `sum(widelki)/2`.


class _Conn:
    """Tyle bazy, ile potrzebuje `_wiek_konta_w_dniach`."""

    def __init__(self, start):
        self.start = start

    def execute(self, _q):
        start = self.start

        class R:
            def fetchone(self_):
                return {"s": start}
        return R()


def wolumen(follow, subskrypcje, dni, wiek_start):
    """Ile dzialan na miesiac oddaje PRAWDZIWY `stages.budzet_dnia`."""
    prawdziwy = sys.modules["datetime"]
    fake = types.ModuleType("datetime")

    class FakeDT(_dt.datetime):
        _teraz = None

        @classmethod
        def now(cls, tz=None):
            return cls._teraz

    fake.datetime, fake.timezone, fake.timedelta = (
        FakeDT, _dt.timezone, _dt.timedelta)
    stare = (config.FOLLOW_MIESIECZNIE, config.SUBSKRYPCJE_MIESIECZNIE,
             stages.BUDZETY)
    katalog = pathlib.Path(tempfile.mkdtemp())
    suma = {"follow": 0, "subskrypcje": 0}
    try:
        config.FOLLOW_MIESIECZNIE = follow
        config.SUBSKRYPCJE_MIESIECZNIE = subskrypcje
        stages.BUDZETY = katalog / "budzety.json"
        # DATA JEST USTALONA, NIE DZISIEJSZA — inaczej test mierzylby kalendarz.
        baza = _dt.datetime(2026, 9, 1, 12, 0, tzinfo=_dt.timezone.utc)
        for i in range(dni):
            dzien = baza + _dt.timedelta(days=i)
            FakeDT._teraz = dzien
            conn = _Conn((dzien - _dt.timedelta(days=wiek_start + i)).isoformat())
            sys.modules["datetime"] = fake
            try:
                buf, so = io.StringIO(), sys.stdout
                sys.stdout = buf
                try:
                    b = stages.budzet_dnia(conn)
                finally:
                    sys.stdout = so
            finally:
                sys.modules["datetime"] = prawdziwy
            suma["follow"] += b["follow"]
            suma["subskrypcje"] += b["subskrypcje"]
            stages.BUDZETY.unlink()
        return (suma["follow"] / dni * 30, suma["subskrypcje"] / dni * 30)
    finally:
        (config.FOLLOW_MIESIECZNIE, config.SUBSKRYPCJE_MIESIECZNIE,
         stages.BUDZETY) = stare
        sys.modules["datetime"] = prawdziwy


# Wspolczynniki z cudzego eksperymentu na 120 kontach (POSZLAKA, jeden autor):
# obserwacja -> 3,4% subskrypcji zwrotnych, subskrypcja -> 11,5%.
ZWROT_OBSERWACJA, ZWROT_SUBSKRYPCJA = 0.034, 0.115


def wynik(f, s):
    return f * ZWROT_OBSERWACJA + s * ZWROT_SUBSKRYPCJA


f_dzis, s_dzis = wolumen(config.FOLLOW_MIESIECZNIE,
                         config.SUBSKRYPCJE_MIESIECZNIE, 365, 400)
f_roz, s_roz = wolumen(config.FOLLOW_MIESIECZNIE,
                       config.SUBSKRYPCJE_MIESIECZNIE, 30, 0)
print("    poza rozbiegiem: follow=%.2f/mies  subskrypcje=%.2f/mies"
      "  dzialan=%.1f  oczekiwani=%.2f"
      % (f_dzis, s_dzis, f_dzis + s_dzis, wynik(f_dzis, s_dzis)))
print("    w rozbiegu:      follow=%.2f/mies  subskrypcje=%.2f/mies"
      "  dzialan=%.1f  oczekiwani=%.2f"
      % (f_roz, s_roz, f_roz + s_roz, wynik(f_roz, s_roz)))
sprawdz("subskrypcje sa teraz LICZNIEJSZE od obserwacji", s_dzis > f_dzis,
        (f_dzis, s_dzis))
sprawdz("takze w rozbiegu, gdzie widelki sa scinane", s_roz > f_roz,
        (f_roz, s_roz))
sprawdz("obserwacje zeszly ponizej 15 na miesiac", f_dzis < 15, f_dzis)
sprawdz("norma dzienna liczy sie z tych samych stalych, bez drugiej listy",
        abs(config.normy_dzienne()["subskrypcja"]
            - sum(config.SUBSKRYPCJE_MIESIECZNIE) / 2 / 30) < 1e-9,
        config.normy_dzienne())


print()
print("=== 5a. KONTRDOWOD: BLOK `subskrybuj` Z `%s` ===" % ODNIESIENIE)
# CO DOKLADNIE JEST TU MIERZONE. Blok pochodzi z `git show
# %s:agent-v2/run.py`, a `browser`, `norma` i atrapa sa DZISIEJSZE. Roznica
# miedzy tym przebiegiem a sekcja 3 to WYLACZNIE zmiana w `run.py`.
BLOK_STARY = wytnij(zrodlo_run(ODNIESIENIE), "subskrybuj")
s_konta, s_wpisy, s_plik, s_out = uruchom_blok(
    BLOK_STARY, "subskrybuj",
    {"publikacja-b.substack.com": "2026-08-29T20:17:52+00:00"},
    Substack(zasubskrybowani={"publikacja-b"}),
    kolejnosc=("publikacja-b.substack.com",),
    dziennik_wstepny=DZIENNIK_WSTEPNY)
print("    STARY BLOK: odwiedzone=%s  wpisy=%s"
      % (s_konta.odwiedzone,
         [(w["rodzaj"], w.get("udane")) for w in s_wpisy[3:]]))
s_wyk, s_nieud, _ = licz_norma(s_plik, "subskrypcja")
print("    STARY BLOK: norma -> wykonane=%d nieudane=%d" % (s_wyk, s_nieud))
sprawdz("KONTRDOWOD: stary blok WCHODZIL na konto juz zasubskrybowane",
        s_konta.odwiedzone == ["publikacja-b"], s_konta.odwiedzone)
sprawdz("KONTRDOWOD: i zapisywal to jako PORAZKE subskrypcji",
        s_nieud == 1, (s_wyk, s_nieud))
sprawdz("a dzisiejszy blok na tych samych danych nie wchodzil nigdzie"
        " i nie zapisal porazki", NIEUD_DUBEL == 0 and s_nieud == 1,
        (NIEUD_DUBEL, s_nieud))

# DRUGI KONTRDOWOD: ODSIEW TEMATYCZNY. Pula ma wylacznie hosty sprzed
# przestawienia konta na AI — stary blok idzie i wysyla im powiadomienie.
s2_konta, s2_wpisy, s2_plik, _ = uruchom_blok(
    BLOK_STARY, "subskrybuj", TYLKO_STARE, Substack(),
    kolejnosc=tuple(TYLKO_STARE))
print("    STARY BLOK na samych starych hostach: odwiedzone=%s"
      % s2_konta.odwiedzone)
sprawdz("KONTRDOWOD: stary blok subskrybowal blog sprzed przestawienia konta",
        s2_konta.zasubskrybowani and set(s2_konta.odwiedzone) <= {
            h.split(".")[0] for h in TYLKO_STARE},
        (s2_konta.odwiedzone, s2_konta.zasubskrybowani))

s3_konta, s3_wpisy, s3_plik, _ = uruchom_blok(
    wytnij(zrodlo_run(ODNIESIENIE), "obserwuj"), "obserwuj",
    TYLKO_STARE, Substack(), kolejnosc=tuple(TYLKO_STARE))
print("    STARY `obserwuj` na samych starych hostach: odwiedzone=%s"
      % s3_konta.odwiedzone)
sprawdz("KONTRDOWOD: stary `obserwuj` tez wysylal maila blogowi sprzed"
        " przestawienia", len(s3_konta.obserwowani) == 1, s3_konta.obserwowani)


print()
print("=== 5b. KONTRDOWOD: STALE Z `%s` PRZEZ TEN SAM RACHUNEK ===" % ODNIESIENIE)
stare_stale = stale_z_commita(ODNIESIENIE, "FOLLOW_MIESIECZNIE",
                              "SUBSKRYPCJE_MIESIECZNIE")
print("    stale z %s: %s" % (ODNIESIENIE, stare_stale))
f_st, s_st = wolumen(stare_stale["FOLLOW_MIESIECZNIE"],
                     stare_stale["SUBSKRYPCJE_MIESIECZNIE"], 365, 400)
print("    STARE: follow=%.2f  subskrypcje=%.2f  dzialan=%.1f  oczekiwani=%.2f"
      % (f_st, s_st, f_st + s_st, wynik(f_st, s_st)))
print("    NOWE:  follow=%.2f  subskrypcje=%.2f  dzialan=%.1f  oczekiwani=%.2f"
      % (f_dzis, s_dzis, f_dzis + s_dzis, wynik(f_dzis, s_dzis)))
sprawdz("KONTRDOWOD: stare stale robily 3,4x wiecej obserwacji niz subskrypcji",
        f_st > 4 * s_st, (f_st, s_st))
sprawdz("KONTRDOWOD: i wymagaly wyraznie WIECEJ dzialan",
        (f_st + s_st) > 1.4 * (f_dzis + s_dzis), (f_st + s_st, f_dzis + s_dzis))
sprawdz("po co to bylo: OCZEKIWANY WYNIK zostaje ten sam (roznica < 10%)",
        abs(wynik(f_st, s_st) - wynik(f_dzis, s_dzis))
        < 0.10 * wynik(f_st, s_st),
        (wynik(f_st, s_st), wynik(f_dzis, s_dzis)))


print()
print("=== PRODUKCJA: bez zmian ===")
zle = 0
for p in PILNOWANE:
    t = odcisk(p)
    ok = t == PRZED[str(p)]
    zle += 0 if ok else 1
    print("  %-30s %s" % (pathlib.Path(p).name,
                          "bez zmian" if ok else "ZMIENIONA"))

print()
print("=== WYNIK: %d zdanych, %d oblanych%s ===" %
      (zdane, oblane, ", PRODUKCJA RUSZONA" if zle else ""))
sys.exit(1 if (oblane or zle) else 0)
