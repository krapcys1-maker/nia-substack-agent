# -*- coding: utf-8 -*-
"""Co wolno uznac za dowod PRZECIW HOSTOWI — i co dowodem nie jest.

WADA, KTORA TO ZAMYKA. Commit `e88b456` mial naprawic „awaria po NASZEJ
stronie na zawsze blokuje host" i zrobil dwie rzeczy naraz:

  1. `dopisz_wynik` zaczal klasyfikowac porazke polem `o_hoscie`, liczonym
     WYLACZNIE z flagi `wynik["klikniete"]`,
  2. `wystaw_komentarz` zaczal zapisywac porazke BEZWARUNKOWO w `finally`.

Flaga `klikniete` zapala sie TUZ PO `przycisk.click()`, czyli ZANIM
`potwierdz_komentarz` w ogole zapyta Substacka. A `potwierdz_komentarz` robi
do czterech `api_json`, kazde to `page.goto(..., timeout=READ_TIMEOUT_MS*2)`
i zadne z nich niczego nie polyka. Zlozenie 1 i 2 dalo skutek ODWROTNY do
zamierzonego: kazdy wyjatek powstaly PO klknieciu — timeout nawigacji,
wyzwanie Cloudflare, `TargetClosedError`, gdy wlasciciel zamknie swojego
Chrome'a (a agent podpina sie wlasnie do jego okna i wlasciciel uzywa konta
recznie) — ladowal w dzienniku jako `udane=False, o_hoscie=True`, czyli jako
dowod przeciwko hostowi.

Petla domykala sie sama: sito w `run.py` wycina cele z takiego hosta PRZED
platna ocena, wiec host nie mial jak zdobyc wpisu `udane=True`, ktory jako
jedyny kasuje go z listy. Zdrowa publikacja znikala z puli na pelne
`PAMIEC_MARTWYCH_HOSTOW_DNI` = 14 dni.

POPRAWKA: `o_hoscie` wymaga DWOCH faktow, nie jednego — `klikniete` ORAZ
`potwierdzenie_odpowiedzialo`, ustawianego dopiero wtedy, gdy potwierdzanie
WROCILO z odpowiedzia. Wyjatek w trakcie potwierdzania to „nie wiem", a „nie
wiem" nie skresla nikogo.

CO TEN TEST MIERZY, A CZEGO NIE. Zadnej asercji po tresci zrodla — trzy takie
w tej serii swiecily na zielono nad martwym kodem. Tutaj idzie PRAWDZIWA
`wystaw_komentarz`, PRAWDZIWY `potwierdz_komentarz` i PRAWDZIWY `api_json`;
atrapa jest tylko pod Playwrightem i rzuca dokladnie tam, gdzie rzucaloby
zamkniecie Chrome'a — w `page.goto` wolanym po klknieciu.

KONTRDOWOD (sekcja 7) idzie tym samym scenariuszem przez `browser.py`
wyciagniety z `git show e88b456:agent-v2/browser.py`. Zmierzone:

    STARY e88b456   wyjatek po klknieciu x2 -> o_hoscie [True, True]
                    hosty_gdzie_komentarz_nie_wchodzi() = {'publikacja-c.example'}
                    mozna_komentowac(...)  = False
    Z POPRAWKA      wyjatek po klknieciu x2 -> o_hoscie [False, False]
                    hosty_gdzie_komentarz_nie_wchodzi() = set()
                    mozna_komentowac(...)  = True

    OBIE WERSJE     potwierdzenie „nie ma tego" x2 -> {'publikacja-c.example'}
                    czyli prawdziwa odmowa nadal zamyka host po dwoch razach.

CALY TEN PLIK PUSZCZONY NA DRZEWIE Z `e88b456:agent-v2/browser.py`:
ZDANE 24, OBLANE 13, exit 1. Oblewaja dokladnie te asercje, ktore mierza
rozroznienie — sekcje 1, 3, 5, 6, 7 i polowa 8 — a sekcja 4 („udany komentarz
odzyskuje host") i druga polowa 8 („prawdziwa odmowa zamyka host w OBU
wersjach") przechodza tam TAK SAMO. To drugie jest wazniejsze od pierwszego:
pokazuje, ze poprawka nie polega na wylaczeniu mechanizmu, tylko na zawezeniu
go do jednej klasy dowodu.

Test nie zalezy od dzisiejszej daty: wpisy powstaja w trakcie przebiegu, a
okno `PAMIEC_MARTWYCH_HOSTOW_DNI` liczy sie wzglednie.

PRODUKCJA: bez zmian. Dziennik idzie do katalogu tymczasowego, `podlacz_sie`
jest podmieniona na atrape, nic nie rusza sieci ani modelu.
"""

import json
import pathlib
import subprocess
import sys
import tempfile
import types

sys.path.insert(0, "agent-v2")
import browser  # noqa: E402
# Authenticated-session precondition for these isolated UI fixtures.
# Real identity verification is covered by test_quality_contract.AccountContract.
browser.wymagaj_wlasciwego_konta = lambda page: None

# HISTORIA JEST WARUNKIEM TEGO TESTU — patrz `historia.py`.
import historia   # noqa: E402

KORZEN = pathlib.Path(__file__).resolve().parents[2]

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# --- ATRAPA PRZEGLADARKI -----------------------------------------------------
# Oddaje tylko to, co `browser.py` od Playwrighta wola. Kluczowa jest jedna
# rzecz: `goto` potrafi rzucic DOPIERO PO klknieciu w przycisk wysylki — tak
# zachowuje sie zamkniety Chrome i tak zachowuje sie timeout nawigacji, gdy
# `potwierdz_komentarz` odpytuje API.

class Brak:
    def count(self):
        return 0

    def is_visible(self):
        return False

    def nth(self, i):
        return self

    @property
    def first(self):
        return self

    def click(self, **k):
        raise AssertionError("klikniecie w niedopasowany lokator")


class Element:
    def __init__(self):
        self.klikniety = False

    def count(self):
        return 1

    def is_visible(self):
        return True

    def nth(self, i):
        return self

    @property
    def first(self):
        return self

    def click(self, **k):
        self.klikniety = True

    def scroll_into_view_if_needed(self, **k):
        pass


class Zbior:
    def __init__(self, elementy):
        self.elementy = list(elementy)

    def count(self):
        return len(self.elementy)

    def nth(self, i):
        return self.elementy[i]

    @property
    def first(self):
        return self.elementy[0] if self.elementy else Brak()


class PrzyciskWysylki(Element):
    """Klik w NIEGO jest granica: od tego momentu `goto` moze rzucac."""

    def __init__(self, strona):
        super().__init__()
        self.strona = strona

    def click(self, **k):
        super().click(**k)
        self.strona.wyslano = True


class Otwieracz(Element):
    """Kontener pola odpowiedzi — klik odslania `[contenteditable=true]`."""

    def __init__(self, strona):
        super().__init__()
        self.strona = strona

    def click(self, **k):
        super().click(**k)
        self.strona.edytowalne = Zbior([Element()])

    def locator(self, selektor):
        return self                     # `xpath=..` — rodzic napisu


class _Mysz:
    def wheel(self, *a):
        pass


class _Klawiatura:
    def __init__(self):
        self.napisane = []

    def type(self, tekst, **k):
        self.napisane.append(tekst)


class Strona:
    def __init__(self, przyciski=("Post",), wyjatek_po_wysylce=None,
                 wchodzi=False, napis_odpowiedzi="Leave a reply"):
        self.przyciski = set(przyciski)
        self.wyjatek_po_wysylce = wyjatek_po_wysylce
        self.wchodzi = wchodzi          # czy Substack pokaze nasz tekst
        self.napis_odpowiedzi = napis_odpowiedzi
        self.wyslano = False
        self.mouse = _Mysz()
        self.keyboard = _Klawiatura()
        self.pola = Zbior([Element()])
        self.edytowalne = Zbior([])
        self.zamknieta = False
        self.ostatni = ""
        self.goto_po_wysylce = 0

    def goto(self, url, **k):
        if self.wyslano:
            self.goto_po_wysylce += 1
            if self.wyjatek_po_wysylce is not None:
                raise self.wyjatek_po_wysylce
        self.ostatni = url

    def wait_for_timeout(self, ms):
        pass

    def inner_text(self, selektor):
        url = self.ostatni
        widac = self.wyslano and self.wchodzi
        if "/api/v1/reader/comment/" in url:
            galezie = [{"id": 555001, "body": TEKST}] if widac else []
            return json.dumps({"commentBranches": galezie})
        if "/comments" in url and "/api/v1/post/" in url:
            return json.dumps([{"id": 987654, "body": TEKST}] if widac else [])
        if "/api/v1/posts/" in url:
            # Bez `write_comment_permissions` o wartosci platnej — inaczej
            # `mozna_komentowac` odmawialoby z zupelnie innego powodu i
            # sekcja 1 mierzylaby nie to, co trzeba.
            return json.dumps({"id": 4242, "write_comment_permissions": "everyone"})
        return "{}"

    def locator(self, selektor):
        if "textarea" in selektor:
            return self.pola
        if "contenteditable" in selektor:
            return self.edytowalne
        if "data-nia" in selektor:
            return Zbior([Otwieracz(self)])
        return Brak()

    def get_by_role(self, rola, name=None, exact=False):
        return PrzyciskWysylki(self) if name in self.przyciski else Brak()

    def get_by_text(self, napis, exact=False):
        return Zbior([Otwieracz(self)]) if napis == self.napis_odpowiedzi else Brak()

    def evaluate(self, skrypt, *a):
        return 0                        # „przycisk odpowiedzi znaleziony"

    def close(self):
        self.zamknieta = True


class _Sterownik:
    def stop(self):
        pass


class _Przegladarka:
    def close(self):
        pass


class _Kontekst:
    def __init__(self, strona):
        self.strona = strona

    def new_page(self):
        return self.strona


def podepnij(strona, modul):
    modul.podlacz_sie = lambda: (_Sterownik(), _Przegladarka(), _Kontekst(strona))
    return strona


# --- DZIENNIK NA BOKU --------------------------------------------------------
KATALOG = pathlib.Path(tempfile.mkdtemp(prefix="nia-dowod-"))
DZIENNIK = KATALOG / "dziennik.jsonl"
TEKST = "Trzy zdania o czyms konkretnym."
HOST = "publikacja-c.example"


def przygotuj(modul):
    modul.DZIENNIK = DZIENNIK
    modul.wymagaj_sesji = lambda: None
    modul.config.DRY_RUN = False
    return modul


def wpisy():
    if not DZIENNIK.exists():
        return []
    return [json.loads(w) for w in
            DZIENNIK.read_text(encoding="utf-8").splitlines() if w.strip()]


def wyczysc(modul):
    if DZIENNIK.exists():
        DZIENNIK.unlink()
    modul._W_SERII.clear()
    modul._OSTATNIA.clear()
    modul._POD_RZAD_ZLE.clear()


def komentarz(modul, sciezka, *, wyjatek=None, wchodzi=False):
    """Jedno wystawienie komentarza. Prawdziwe `potwierdz_komentarz`."""
    strona = podepnij(Strona(wyjatek_po_wysylce=wyjatek, wchodzi=wchodzi), modul)
    modul.juz_sie_odezwalismy = lambda page, url: False
    wynik = modul.wystaw_komentarz("https://%s/p/%s" % (HOST, sciezka), TEKST,
                                   wyslij=True)
    return wynik, strona


def o_hoscie():
    return [w.get("o_hoscie") for w in wpisy()]


TIMEOUT = TimeoutError("Timeout 30000ms exceeded navigating to /api/v1/posts/a")
ZAMKNIETY = RuntimeError("TargetClosedError: Target page has been closed")

przygotuj(browser)

print("=== 1. WYJATEK PO KLKNIECIU TO `NIE WIEM`, NIE DOWOD PRZECIW HOSTOWI ===")
# Dwa rozne posty, jeden host. Wlasciciel zamknal Chrome w trakcie przebiegu
# — a agent podpina sie wlasnie do jego okna.
wyczysc(browser)
w1, s1 = komentarz(browser, "a", wyjatek=TIMEOUT)
w2, s2 = komentarz(browser, "b", wyjatek=ZAMKNIETY)
lista = wpisy()

sprawdz("klik naprawde poszedl przed wyjatkiem",
        w1.get("klikniete") is True and w2.get("klikniete") is True, (w1, w2))
sprawdz("i wyjatek padl dopiero w potwierdzaniu",
        s1.goto_po_wysylce == 1 and s2.goto_po_wysylce == 1,
        (s1.goto_po_wysylce, s2.goto_po_wysylce))
sprawdz("obie porazki SA w dzienniku", len(lista) == 2, lista)
sprawdz("obie jako nieudane",
        [w.get("udane") for w in lista] == [False, False], lista)
sprawdz("powod niesie typ bledu",
        all(w.get("powod", "").split(":")[0] in ("TimeoutError", "RuntimeError")
            for w in lista), [w.get("powod") for w in lista])
sprawdz("dziennik nie zaklamuje, ze nie kliknelismy",
        [w.get("klikniete") for w in lista] == [True, True], lista)
sprawdz("ale ZADNA nie jest dowodem przeciw hostowi",
        o_hoscie() == [False, False], o_hoscie())
martwe = browser.hosty_gdzie_komentarz_nie_wchodzi()
sprawdz("host zyje", martwe == set(), martwe)
podepnij(Strona(), browser)
sprawdz("i wolno tam jeszcze raz napisac",
        browser.mozna_komentowac("https://%s/p/c" % HOST) is True)

print()
print("=== 2. `KLIKNIETE, A SUBSTACK NIE POKAZUJE` NADAL ZAMYKA HOST ===")
# To jest ta jedna klasa, ktora o hoscie mowi — i ta, ktora poprawka miala
# zachowac. Potwierdzanie WROCILO, tylko z odpowiedzia „nie ma tego".
wyczysc(browser)
w1, s1 = komentarz(browser, "a")
sprawdz("po jednej odmowie host jeszcze zyje",
        browser.hosty_gdzie_komentarz_nie_wchodzi() == set(),
        browser.hosty_gdzie_komentarz_nie_wchodzi())
w2, s2 = komentarz(browser, "b")
lista = wpisy()
sprawdz("potwierdzanie doszlo do konca",
        w1.get("potwierdzenie_odpowiedzialo") is True
        and w2.get("potwierdzenie_odpowiedzialo") is True, (w1, w2))
sprawdz("obie porazki w dzienniku i obie o hoscie",
        len(lista) == 2 and o_hoscie() == [True, True], lista)
martwe = browser.hosty_gdzie_komentarz_nie_wchodzi()
sprawdz("po DWOCH odmowach host jest zamkniety", martwe == {HOST}, martwe)
sprawdz("i nie placimy za trzeci raz",
        browser.mozna_komentowac("https://%s/p/c" % HOST) is False)

print()
print("=== 3. NASZ WYJATEK NIE DOKLADA SIE DO CUDZEGO RACHUNKU ===")
# Jedna prawdziwa odmowa + jeden nasz wyjatek to nadal JEDEN dowod, nie dwa.
# Prog dwoch prob istnieje po to, zeby awaria po drugiej stronie nie wystarczyla.
wyczysc(browser)
komentarz(browser, "a")                       # odmowa Substacka
komentarz(browser, "b", wyjatek=ZAMKNIETY)    # nasza awaria
sprawdz("dwa wpisy nieudane, ale tylko jeden o hoscie",
        o_hoscie() == [True, False], o_hoscie())
martwe = browser.hosty_gdzie_komentarz_nie_wchodzi()
sprawdz("wiec host zyje", martwe == set(), martwe)

print()
print("=== 4. UDANY KOMENTARZ NADAL ZDEJMUJE HOST Z LISTY ===")
wyczysc(browser)
komentarz(browser, "a")
komentarz(browser, "b")
sprawdz("host zamkniety", browser.hosty_gdzie_komentarz_nie_wchodzi() == {HOST})
w, _ = komentarz(browser, "c", wchodzi=True)
sprawdz("trzeci komentarz naprawde wszedl",
        w.get("wyslane") is True and w.get("id") == 987654, w)
sprawdz("host odzyskany", browser.hosty_gdzie_komentarz_nie_wchodzi() == set(),
        browser.hosty_gdzie_komentarz_nie_wchodzi())
sprawdz("i seria porazek wyzerowana",
        browser.pod_rzad_nieudanych("komentarz") == 0,
        browser.pod_rzad_nieudanych("komentarz"))

print()
print("=== 5. ODPOWIEDZ W WATKU — TEN SAM WZORZEC, TA SAMA POPRAWKA ===")
# `wystaw_odpowiedz` tez ustawiala `klikniete` przed potwierdzaniem.
# Dzis jej wpisy maja `gdzie=note/c-...`, wiec `hosty_gdzie_komentarz_nie_
# wchodzi` je pomija (filtr `startswith("http")`) — ale pole `o_hoscie` i tak
# ladowalo w dzienniku klamiac, a to ten sam material na te sama pomylke.


def odpowiedz(modul, note_id, *, wyjatek=None, wchodzi=False):
    strona = podepnij(Strona(przyciski=("Post",), wyjatek_po_wysylce=wyjatek,
                             wchodzi=wchodzi), modul)
    return modul.wystaw_odpowiedz(note_id, TEKST, wyslij=True), strona


wyczysc(browser)
w, s = odpowiedz(browser, 900000007, wyjatek=ZAMKNIETY)
lista = wpisy()
sprawdz("odpowiedz doszla do klikniecia", w.get("klikniete") is True, w)
sprawdz("porazka zapisana", len(lista) == 1 and lista[0].get("udane") is False,
        lista)
sprawdz("wyjatek po klknieciu NIE jest dowodem o hoscie",
        o_hoscie() == [False], lista)

wyczysc(browser)
odpowiedz(browser, 900000007)
sprawdz("a `kliknelismy, nie ma tego w watku` — jest",
        o_hoscie() == [True], wpisy())

wyczysc(browser)
w, s = odpowiedz(browser, 900000007, wchodzi=True)
sprawdz("udana odpowiedz nadal sie potwierdza",
        w.get("wyslane") is True and wpisy()[0].get("udane") is True, w)

print()
print("=== 6. ODPOWIEDZ POD NASZYM ARTYKULEM — TO SAMO ===")


def pod_artykulem(modul, sciezka, *, wyjatek=None, wchodzi=False):
    strona = podepnij(Strona(przyciski=("Post",), wyjatek_po_wysylce=wyjatek,
                             wchodzi=wchodzi), modul)
    return modul.wystaw_odpowiedz_pod_artykulem(
        "https://your-handle.substack.com/p/%s" % sciezka,
        "Ktos", TEKST, wyslij=True), strona


wyczysc(browser)
w, s = pod_artykulem(browser, "nasz", wyjatek=TIMEOUT)
sprawdz("klik poszedl", w.get("klikniete") is True, w)
sprawdz("porazka zapisana i NIE o hoscie",
        len(wpisy()) == 1 and o_hoscie() == [False], wpisy())

wyczysc(browser)
pod_artykulem(browser, "nasz")
sprawdz("a odmowa potwierdzania — o hoscie", o_hoscie() == [True], wpisy())

print()
print("=== 7. WPISY, KTORE ZDAZYL NAPISAC ZEPSUTY KOD ===")
# Poprawka w kodzie nie dosiega dziennika. Przez jeden dzien `e88b456`
# zapisywal `o_hoscie=True` takze przy NASZYCH wyjatkach, a takie wpisy leza
# na dysku przez cale 14 dni i host nie ma jak sie z nich wybronic: sito
# w `run.py` wycina go PRZED ocena, wiec `udane=True` jest poza zasiegiem.
# Wpis sam sie zdradza — `o_hoscie=True` przy powodzie „TargetClosedError" nie
# da sie pogodzic z definicja tego pola.
wyczysc(browser)


def wpis(host, powod, dni_temu=1.0):
    from datetime import datetime, timedelta, timezone
    kiedy = (datetime.now(timezone.utc)
             - timedelta(days=dni_temu)).isoformat(timespec="seconds")
    with open(DZIENNIK, "a", encoding="utf-8") as f:
        f.write(json.dumps({"kiedy": kiedy, "rodzaj": "komentarz",
                            "udane": False, "gdzie": "https://%s/p/x" % host,
                            "o_hoscie": True, "powod": powod},
                           ensure_ascii=False) + "\n")


wpis("zatruty.com", "TimeoutError: Timeout 30000ms exceeded")
wpis("zatruty.com", "RuntimeError: TargetClosedError: Target page has been closed")
sprawdz("dwa wpisy `o_hoscie` z powodem-wyjatkiem nie zamykaja hosta",
        browser.hosty_gdzie_komentarz_nie_wchodzi() == set(),
        browser.hosty_gdzie_komentarz_nie_wchodzi())

# A wpisy tej samej, starej generacji, ktore mowia o hoscie NAPRAWDE, licza
# sie dalej — inaczej „naprawa" polegalaby na wyrzuceniu calej pamieci.
#
# Napis wpisany tu z reki, a nie wziety z modulu: dziennik na dysku zna tylko
# napis, wiec test ma go pilnowac, a nie powtarzac za kodem. Osobna asercja
# sprawdza, ze kod i dziennik nadal mowia to samo.
POWOD_ODMOWY = "Substack nie potwierdzil, ze wyszlo"
sprawdz("stala w kodzie zgadza sie z napisem, ktory lezy w dzienniku",
        getattr(browser, "POWOD_HOST_NIE_POKAZUJE", None) == POWOD_ODMOWY,
        getattr(browser, "POWOD_HOST_NIE_POKAZUJE", "BRAK STALEJ"))
wpis("odmowil.com", POWOD_ODMOWY)
wpis("odmowil.com", POWOD_ODMOWY)
sprawdz("ale dwie prawdziwe odmowy z tego samego dnia — owszem",
        browser.hosty_gdzie_komentarz_nie_wchodzi() == {"odmowil.com"},
        browser.hosty_gdzie_komentarz_nie_wchodzi())

print()
# HISTORIA JEST WARUNKIEM TYLKO TEGO, CO PONIZEJ.
#
# Guard stal w naglowku pliku, wiec w kopii z historia zalozona
# od nowa gasl CALY test, a nie ten jeden blok, ktory naprawde
# potrzebuje starej wersji. Policzone 4 wrzesnia 2026: 617
# asercji w 17 plikach nie wykonywalo sie ani razu — i zestaw
# wygladal na zdany, bo pominiecie konczy sie kodem 0.
#
# `SystemExit` nie dziedziczy po `Exception`, wiec przechodzi
# przez oslony tego pliku i wykonuje `finally` — sprzatanie
# po tescie dzieje sie normalnie.
historia.wymaga_historii("e88b456", zdane=zdane, oblane=oblane)

print("=== 8. KONTRDOWOD: TEN SAM SCENARIUSZ NA `e88b456` ===")


def modul_z_commita(commit):
    """`browser.py` sprzed poprawki, wczytany jako OSOBNY modul.

    Kontrdowod odtwarzany, nie opisywany: ten sam scenariusz idzie raz przez
    kod z poprawka i raz przez kod bez niej, a test porownuje wyniki.
    """
    proc = subprocess.run(["git", "-C", str(KORZEN), "show",
                           "%s:agent-v2/browser.py" % commit],
                          capture_output=True)
    if proc.returncode != 0:
        raise SystemExit("nie dostalem %s z gita: %s"
                         % (commit, proc.stderr.decode("utf-8", "replace")[:200]))
    src = proc.stdout.decode("utf-8")
    m = types.ModuleType("browser_%s" % commit)
    m.__dict__["__name__"] = "browser_%s" % commit
    m.__dict__["__file__"] = "agent-v2/browser.py"
    exec(compile(src, "agent-v2/browser.py(%s)" % commit, "exec"), m.__dict__)
    return przygotuj(m)


stary = modul_z_commita("e88b456")

wyczysc(stary)
komentarz(stary, "a", wyjatek=TIMEOUT)
komentarz(stary, "b", wyjatek=ZAMKNIETY)
stare_o_hoscie = o_hoscie()
stare_martwe = stary.hosty_gdzie_komentarz_nie_wchodzi()
podepnij(Strona(), stary)
stare_wolno = stary.mozna_komentowac("https://%s/p/c" % HOST)

wyczysc(browser)
komentarz(browser, "a", wyjatek=TIMEOUT)
komentarz(browser, "b", wyjatek=ZAMKNIETY)
nowe_o_hoscie = o_hoscie()
nowe_martwe = browser.hosty_gdzie_komentarz_nie_wchodzi()
podepnij(Strona(), browser)
nowe_wolno = browser.mozna_komentowac("https://%s/p/c" % HOST)

print("    WYJATEK PO KLKNIECIU x2, jeden host, dwa rozne posty:")
print("      STARY e88b456: o_hoscie=%s martwe=%s mozna_komentowac=%s"
      % (stare_o_hoscie, stare_martwe or set(), stare_wolno))
print("      Z POPRAWKA   : o_hoscie=%s martwe=%s mozna_komentowac=%s"
      % (nowe_o_hoscie, nowe_martwe or set(), nowe_wolno))

sprawdz("KONTRDOWOD: stary uznawal NASZ wyjatek za dowod o hoscie",
        stare_o_hoscie == [True, True], stare_o_hoscie)
sprawdz("KONTRDOWOD: i zamykal zdrowy host na 14 dni",
        stare_martwe == {HOST}, stare_martwe)
sprawdz("KONTRDOWOD: i przestawal za niego placic",
        stare_wolno is False, stare_wolno)
sprawdz("z poprawka ten sam scenariusz hosta nie tyka",
        nowe_o_hoscie == [False, False] and nowe_martwe == set()
        and nowe_wolno is True, (nowe_o_hoscie, nowe_martwe, nowe_wolno))

# A TERAZ DRUGA STRONA: to, co poprawka miala ZACHOWAC. Prawdziwa odmowa
# musi zamykac host w OBU wersjach — inaczej „naprawilbym" ja przez wylaczenie.
wyczysc(stary)
komentarz(stary, "a")
komentarz(stary, "b")
stare_odmowy = stary.hosty_gdzie_komentarz_nie_wchodzi()

wyczysc(browser)
komentarz(browser, "a")
komentarz(browser, "b")
nowe_odmowy = browser.hosty_gdzie_komentarz_nie_wchodzi()

print("    POTWIERDZENIE `NIE MA TEGO` x2:")
print("      STARY e88b456: martwe=%s" % (stare_odmowy or set()))
print("      Z POPRAWKA   : martwe=%s" % (nowe_odmowy or set()))
sprawdz("prawdziwa odmowa zamyka host w starej wersji",
        stare_odmowy == {HOST}, stare_odmowy)
sprawdz("i tak samo w nowej — poprawka niczego nie wylaczyla",
        nowe_odmowy == {HOST}, nowe_odmowy)

print()
print("=== PRODUKCJA: bez zmian ===")
print("  dziennik testu: %s" % DZIENNIK)
print("  `podlacz_sie` podmieniona na atrape, zero wywolan sieci i modelu")

print()
print("ZDANE: %d   OBLANE: %d" % (zdane, oblane))
sys.exit(1 if oblane else 0)
