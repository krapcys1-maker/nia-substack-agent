# -*- coding: utf-8 -*-
"""Slot obserwacji nie ginie na kims, kogo juz obserwujemy.

## Co bylo zepsute

Blok `run.py::obserwuj` losowal hosty Z CALEJ HISTORII KOMENTARZY, bez zadnego
odsiewu. `browser.obserwuj_profil` na profilu juz obserwowanym zachowywalo sie
poprawnie — czytalo z menu „Unfollow" i NIE KLIKALO NIC — ale oddawalo
`zrobione=False`, a `dopisz_wynik` zapisywalo to jako PORAZKE. Budzet to okolo
jednej obserwacji na dobe, wiec jedno takie losowanie konczylo dzien.

Najgorsze bylo to, co widzial potem licznik: `norma.py` nie mial jak odroznic
„pula sie wyczerpala" od „przycisk znowu zniknal" — czyli od dokladnie tej
pomylki, ktora 23 sierpnia kosztowala dziewiec dni bez ani jednej obserwacji.

Pole `juz_obserwowany` szlo do dziennika i NIE CZYTALO GO NIC w calym repo.

## Pomiar, na ktorym stoi ten test (1 wrzesnia 2026, zywa sesja, serwer)

Odczyt, nic nie klikniete, konto `your-handle`:

    substack.com/@your-handle/following  -> 26 uchwytow
    /api/v1/user/your-handle/public_profile
        visibleSubscriptionsCount = 26

Co do jednego tyle samo, wiec zakladka NIE dokleja podpowiedzi „kogo
obserwowac" i `_ludzie_z_zakladki` czyta z niej sama liste obserwowanych.

    agent-v2/data/gdzie_komentowalismy.json  -> 92 hosty (24 wlasne domeny)
    czesc wspolna po samym `host.split(".")[0]` -> 8 hostow:
      publikacja9, autor3, publikacja19, publikacja18,
      publikacja1, publikacja5, tiffaniedarke, publikacja6

Naprawde wiecej, bo tanie mapowanie nie widzi wlasnych domen
(`www.wlasnadomena.example` -> `autor1`) ani rozjazdow nazw
(`publikacja-b.substack.com` -> konto `publikacja-b`). Osiem z 92 to
juz okolo 13 procent, czyli mniej wiecej jeden dzien na siedem.

## Co ten test mierzy

ZACHOWANIE PRODUKCJI, nie tresc zrodel. Blok `obserwuj` jest wycinany z
`run.py` przez `ast` i URUCHAMIANY na atrapie Substacka; dziennik i pamiec
obserwowanych sa prawdziwe (przekierowane do katalogu tymczasowego), a to,
czy wpis jest porazka, rozstrzyga PRAWDZIWA `norma.wczytaj`.

KONTRDOWOD JEST ODTWARZANY, NIE OPISANY. Sekcja 5a puszcza ten sam scenariusz
przez blok wyjety z `git show 64d881a:agent-v2/run.py` — wersja odniesienia
PRZYPIETA DO SHA, nie do HEAD, bo kontrdowod mierzony wzgledem HEAD gasnie
w chwili commita, ktorego strzeze. Sekcja 5b odtwarza REGULE ZAPISU sprzed
poprawki, a nie plik, i mowi wprost dlaczego: na `64d881a` droga przez menu
nie byla jeszcze zacommitowana, wiec tamten plik nie zna stanu „juz go
obserwujemy" i nie ma z niego czego wyjac.

Zero sieci, zero przegladarki, zero wywolan modelu, zero zapisu do produkcji.
"""

import ast
import hashlib
import io
import json
import pathlib
import random
import subprocess
import sys
import tempfile

KORZEN = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(KORZEN / "agent-v2"))

import browser        # noqa: E402
import config         # noqa: E402
import norma          # noqa: E402
import run            # noqa: E402

# HISTORIA JEST WARUNKIEM TEGO TESTU — patrz `historia.py`.
import historia   # noqa: E402

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
# Odwzorowuje maszyne stanu zmierzona 1 wrzesnia (pelny zapis pomiaru stoi
# w `test_obserwowanie_przez_menu.py`): menu jest zamkniete, otwiera sie po
# kliknieciu kolka, a pozycja zalezy od tego, czy JUZ obserwujemy to konto.
MENU_WOLNY = ["Copy link", "Share", "Send message", "Follow",
              "Mute", "Block", "Report"]
MENU_OBSERWOWANY = ["Copy link", "Share", "Send message", "Unfollow",
                    "Manage Subscription", "Mute", "Block", "Report"]


class Substack:
    """Prawda o koncie: kogo naprawde obserwujemy i co zostalo dotkniete."""

    def __init__(self, obserwowani=()):
        self.obserwowani = set(obserwowani)
        self.sesje = 0            # ile razy otwarto przegladarke
        self.odwiedzone = []      # na czyim profilu bylismy
        self.klikniete = []       # co klikniete, w kolejnosci


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


# --- WYCINANIE BLOKU `obserwuj` Z `run.py` -----------------------------------
#
# Blok jest funkcja ZAGNIEZDZONA w `dzien()`, wiec nie da sie go zaimportowac.
# Wycinamy go po `ast` i uruchamiamy w przygotowanej przestrzeni nazw — dzieki
# temu test mierzy PRAWDZIWY kod produkcyjny, a nie jego opis.
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


class Kanal:
    """Historia komentarzy — jedyne zrodlo puli. Odwzorowuje `kanal._historia`.

    DATA JEST PO PRZESTAWIENIU KONTA NA AI (`run.PRZESTAWIENIE_KONTA_NA_AI`
    = 2026-08-25), bo od 1 wrzesnia `obserwuj` odsiewa hosty, u ktorych
    ostatni komentarz jest starszy — to osobne kryterium i ma wlasny test
    (`test_wybor_celu.py`). Tutaj mierzymy odsiew po PAMIECI OBSERWOWANYCH,
    wiec pula musi przechodzic przez tamto sito bez ubytku.
    """

    def __init__(self, hosty):
        self.hosty = {h: "2026-08-31T12:00:00+00:00" for h in hosty}

    def _historia(self):
        return dict(self.hosty)


def uruchom_blok(mod_browser, kod_bloku, hosty, obserwowani_na_substacku,
                 pamiec=None, budzet=1, kolejnosc=()):
    """Puszcza blok `obserwuj` na atrapie i oddaje (Substack, dziennik, pamiec).

    Dziennik i pamiec sa PRAWDZIWE — tylko przekierowane do katalogu
    tymczasowego. `random.shuffle` zastapione ustaleniem kolejnosci, bo
    `set()` w bloku ma kolejnosc zalezna od `PYTHONHASHSEED`, a test nie moze
    zalezec od losu ani od dnia.
    """
    konta = Substack(obserwowani_na_substacku)

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
        return {"www.wlasnadomena.example": "autor1"}.get(host)

    katalog = pathlib.Path(tempfile.mkdtemp())
    stare = {k: getattr(mod_browser, k) for k in
             ("podlacz_sie", "wymagaj_sesji", "naprawde_wyslac",
              "uchwyt_publikacji", "DZIENNIK")}
    ma_pamiec = hasattr(mod_browser, "OBSERWOWANI")
    if ma_pamiec:
        stare["OBSERWOWANI"] = mod_browser.OBSERWOWANI
    stary_shuffle = random.shuffle
    stara_norma = norma.DZIENNIK
    try:
        mod_browser.podlacz_sie = podlacz
        mod_browser.wymagaj_sesji = lambda: None
        mod_browser.naprawde_wyslac = lambda w, co: w
        mod_browser.uchwyt_publikacji = uchwyt_publikacji
        mod_browser.DZIENNIK = katalog / "dziennik.jsonl"
        norma.DZIENNIK = katalog / "dziennik.jsonl"
        if ma_pamiec:
            mod_browser.OBSERWOWANI = katalog / "kogo_obserwujemy.json"
            if pamiec:
                mod_browser.OBSERWOWANI.write_text(
                    json.dumps(pamiec, ensure_ascii=False), encoding="utf-8")
        random.shuffle = lambda lst: lst.sort(
            key=lambda h: kolejnosc.index(h) if h in kolejnosc else 99)

        ns = {"browser": mod_browser, "config": config, "kanal": Kanal(hosty),
              "na_teraz": {"follow": budzet}, "wyslij": True,
              "rytm_stanu": {}, "zostal_czas": lambda *a, **k: True,
              "rytm": lambda *a, **k: True, "print": print,
              # Pomocnicy z poziomu modulu `run` — blok jest funkcja
              # zagniezdzona, wiec normalnie widzi je przez globals() modulu.
              # Wersja z `64d881a` ich nie wola, wiec obie sciezki dzialaja.
              "cele_wedlug_pierwszenstwa": run.cele_wedlug_pierwszenstwa,
              "powod_pustej_puli": run.powod_pustej_puli,
              "PRZESTAWIENIE_KONTA_NA_AI": run.PRZESTAWIENIE_KONTA_NA_AI}
        exec(compile(kod_bloku, "run.py::obserwuj", "exec"), ns)
        buf, stare_out = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            ns["obserwuj"]()
        finally:
            sys.stdout = stare_out
        wpisy = []
        if (katalog / "dziennik.jsonl").exists():
            wpisy = [json.loads(x) for x in
                     (katalog / "dziennik.jsonl").read_text(
                         encoding="utf-8").splitlines() if x.strip()]
        pam = (json.loads((katalog / "kogo_obserwujemy.json").read_text(
            encoding="utf-8"))
            if ma_pamiec and (katalog / "kogo_obserwujemy.json").exists() else {})
        return konta, wpisy, pam, katalog / "dziennik.jsonl", buf.getvalue()
    finally:
        random.shuffle = stary_shuffle
        norma.DZIENNIK = stara_norma
        for k, v in stare.items():
            setattr(mod_browser, k, v)


def licz_norma(plik_dziennika):
    """(wykonane, nieudane) obserwacji wedlug PRAWDZIWEJ `norma.wczytaj`."""
    stara = norma.DZIENNIK
    try:
        norma.DZIENNIK = plik_dziennika
        zrobione, nieudane = norma.wczytaj(14)
        _, ze_sladem = norma.slad_dziennika({})
        return (sum(d["obserwacja"] for d in zrobione.values()),
                sum(d["obserwacja"] for d in nieudane.values()),
                len(ze_sladem))
    finally:
        norma.DZIENNIK = stara


# Pula z pomiaru: dwa konta, ktore JUZ obserwujemy (jedno przez wlasna domene,
# tak jak `www.wlasnadomena.example`), i jedno wolne.
PULA = ["publikacja1.substack.com", "www.wlasnadomena.example", "publikacja2.substack.com"]
NA_SUBSTACKU = {"publikacja1", "autor1"}
BLOK_TERAZ = wytnij(zrodlo_run(), "obserwuj")


print("=== 1. PAMIEC OBSERWOWANYCH: CZYTANIE, ZAPIS, SAMOLECZENIE ===")
_kat = pathlib.Path(tempfile.mkdtemp())
_stare_obs = browser.OBSERWOWANI
try:
    browser.OBSERWOWANI = _kat / "kogo_obserwujemy.json"
    sprawdz("brak pliku to pusta pamiec, nie wyjatek",
            browser.kogo_obserwujemy() == {"zrzut": None, "uchwyty": {},
                                           "hosty": {}})
    browser.OBSERWOWANI.write_text("{to nie jest json", encoding="utf-8")
    sprawdz("plik zepsuty tez nie wywala bloku",
            browser.kogo_obserwujemy()["uchwyty"] == {})

    browser.OBSERWOWANI.unlink()
    browser.zapamietaj_obserwowanego("autor1", host="www.wlasnadomena.example")
    sprawdz("zapamietany uchwyt",
            "autor1" in browser.kogo_obserwujemy()["uchwyty"])
    sprawdz("i host, z ktorego sie wzial — bo pula jest lista hostow",
            browser.czy_juz_obserwujemy("www.wlasnadomena.example") is True)
    sprawdz("konto w domenie Substacka rozpoznane bez mapy hostow",
            browser.czy_juz_obserwujemy("publikacja1.substack.com",
                                        {"uchwyty": {"publikacja1": "x"},
                                         "hosty": {}}) is True)
    sprawdz("nieznany host: przy watpliwosci probujemy",
            browser.czy_juz_obserwujemy("publikacja2.substack.com") is False)

    # ZRZUT ZE STRONY `/following` — ta sama funkcja, ktora czyta zakladke
    # obserwujacych. 26 uchwytow zmierzonych na zywo; tu trzy, zeby dalo sie
    # policzyc palcem.
    class Odnosnik:
        def __init__(self, href, tekst):
            self.href, self.tekst = href, tekst

        def get_attribute(self, _):
            return self.href

        def inner_text(self):
            return self.tekst

    class StronaZakladki:
        def __init__(self, odnosniki):
            self._o = odnosniki

        def goto(self, *a, **k):
            pass

        def wait_for_timeout(self, *a):
            pass

        def locator(self, _):
            class L:
                def __init__(s, o):
                    s._o = o

                def all(s):
                    return s._o
            return L(self._o)

    ilu = browser.odswiez_kogo_obserwujemy(StronaZakladki([
        Odnosnik("/@publikacja1", "Publikacja 1"),
        Odnosnik("/@autor1", "Dr. Robert W. Malone"),
        Odnosnik("/@autor3", "Autor 3")]))
    sprawdz("zrzut odczytal trzech", ilu == 3, ilu)
    sprawdz("mapa hostow przezyla zrzut",
            browser.czy_juz_obserwujemy("www.wlasnadomena.example") is True)

    # SAMOLECZENIE: wlasciciel odobserwowal Malone'a recznie. Zrzut przepisuje
    # liste w calosci, wiec host MUSI wrocic do puli sam — inaczej pamiec
    # kasowalaby kandydatow na zawsze.
    ilu2 = browser.odswiez_kogo_obserwujemy(StronaZakladki([
        Odnosnik("/@publikacja1", "Publikacja 1"),
        Odnosnik("/@autor3", "Autor 3")]))
    sprawdz("po odobserwowaniu zostaje dwoch", ilu2 == 2, ilu2)
    sprawdz("a host wraca do puli",
            browser.czy_juz_obserwujemy("www.wlasnadomena.example") is False)

    # PUSTY ODCZYT NIE KASUJE PAMIECI — inaczej jedna awaria strony
    # odblokowalaby cala pule i dzien poszedlby na powtorki.
    ile3 = browser.odswiez_kogo_obserwujemy(StronaZakladki([]))
    sprawdz("pusta zakladka nie kasuje pamieci",
            ile3 == 0 and browser.czy_juz_obserwujemy(
                "publikacja1.substack.com") is True)
finally:
    browser.OBSERWOWANI = _stare_obs


print()
print("=== 2. ODSIEW PRZED LOSOWANIEM: OBSERWOWANY NIE WCHODZI DO PULI ===")
# Pamiec zna oba konta, ktore juz obserwujemy. Kolejnosc losowania ustawiona
# tak, ze BEZ odsiewu padloby wlasnie na nie — czyli dokladnie ten przypadek,
# ktory zjadal dzien.
pamiec_pelna = {"zrzut": "2026-09-01T00:00:00+00:00",
                "uchwyty": {"publikacja1": "2026-09-01T00:00:00+00:00",
                            "autor1": "2026-09-01T00:00:00+00:00"},
                "hosty": {"www.wlasnadomena.example": "autor1"}}
konta, wpisy, pam, plik, out = uruchom_blok(
    browser, BLOK_TERAZ, PULA, NA_SUBSTACKU, pamiec=pamiec_pelna,
    kolejnosc=("publikacja1.substack.com", "www.wlasnadomena.example",
               "publikacja2.substack.com"))
print("    odwiedzone profile: %s" % konta.odwiedzone)
print("    klikniete: %s" % konta.klikniete)
sprawdz("weszlismy na JEDEN profil i to ten wolny",
        konta.odwiedzone == ["publikacja2"], konta.odwiedzone)
sprawdz("obserwacja weszla", "publikacja2" in konta.obserwowani, konta.obserwowani)
sprawdz("nikt nie zostal odobserwowany",
        {"publikacja1", "autor1"} <= konta.obserwowani, konta.obserwowani)
sprawdz("jeden wpis w dzienniku i jest udana obserwacja",
        len(wpisy) == 1 and wpisy[0]["rodzaj"] == "obserwacja"
        and wpisy[0]["udane"] is True, wpisy)
sprawdz("zaobserwowany trafil do pamieci razem ze swoim hostem",
        pam["uchwyty"].get("publikacja2")
        and pam["hosty"].get("publikacja2.substack.com") == "publikacja2", pam)


print()
print("=== 3. PAMIEC MOZE BYC PUSTA — SLOT I TAK NIE PRZEPADA ===")
# Pierwszy dzien po wdrozeniu: pliku pamieci nie ma jeszcze wcale. Blok trafia
# na obserwowanego, czyta to z menu i bierze NASTEPNEGO — bo „juz obserwujemy"
# nie jest proba.
konta, wpisy, pam, plik, out = uruchom_blok(
    browser, BLOK_TERAZ, PULA, NA_SUBSTACKU, pamiec=None,
    kolejnosc=("publikacja1.substack.com", "www.wlasnadomena.example",
               "publikacja2.substack.com"))
print("    odwiedzone profile: %s" % konta.odwiedzone)
print("    wpisy: %s" % [(w["rodzaj"], w.get("udane")) for w in wpisy])
sprawdz("weszlismy na obserwowanego, ale nie klikneli nic poza kolkiem",
        [k for k in konta.klikniete if k not in ("Profile actions", "Follow")]
        == [], konta.klikniete)
sprawdz("nikt nie zostal odobserwowany",
        {"publikacja1", "autor1"} <= konta.obserwowani, konta.obserwowani)
sprawdz("DZIEN NIE PRZEPADL: wolny profil zostal zaobserwowany",
        "publikacja2" in konta.obserwowani, konta.obserwowani)
sprawdz("budzet 1 nadal znaczy JEDNA obserwacje",
        len([w for w in wpisy
             if w["rodzaj"] == "obserwacja" and w["udane"]]) == 1, wpisy)
sprawdz("a pominiecia zapisaly sie osobnym rodzajem",
        [w["rodzaj"] for w in wpisy].count("obserwacja_pominieta") >= 1, wpisy)
sprawdz("pominiety host trafil do pamieci, wiec jutro odsieje sie taniej",
        pam["hosty"].get("publikacja1.substack.com") == "publikacja1", pam)

# NAJWAZNIEJSZA ASERCJA W PLIKU: co z tego widzi licznik.
wykonane, nieudane, dni = licz_norma(plik)
print("    norma.wczytaj -> obserwacje wykonane=%d nieudane=%d, dni ze sladem=%d"
      % (wykonane, nieudane, dni))
sprawdz("licznik widzi JEDNA wykonana obserwacje", wykonane == 1, wykonane)
sprawdz("i ANI JEDNEJ porazki — „juz obserwujemy” nia nie jest",
        nieudane == 0, nieudane)
sprawdz("a dzien nadal ma slad, wiec nie wyglada na dobe martwa",
        dni == 1, dni)
WYKONANE_3, NIEUDANE_3 = wykonane, nieudane   # sekcje nizej porownuja sie z tym


print()
print("=== 4. CALA PULA JUZ OBSERWOWANA: STAN POPRAWNY, ALE ZE SLADEM ===")
konta, wpisy, pam, plik, out = uruchom_blok(
    browser, BLOK_TERAZ, ["publikacja1.substack.com", "www.wlasnadomena.example"],
    NA_SUBSTACKU, pamiec=pamiec_pelna,
    kolejnosc=("publikacja1.substack.com", "www.wlasnadomena.example"))
sprawdz("ZERO sesji przegladarki — odsiew dziala bez wchodzenia na profile",
        konta.sesje == 0 and konta.odwiedzone == [], konta.odwiedzone)
sprawdz("ale wpis jest, bo blok bez sladu wyglada na blok, ktorego nie ma",
        len(wpisy) == 1 and wpisy[0]["rodzaj"] == "obserwacja_pominieta", wpisy)
sprawdz("i niesie powod mowiacy o wyczerpanej puli",
        "pula wyczerpana" in (wpisy[0].get("powod") or ""), wpisy)
wykonane, nieudane, dni = licz_norma(plik)
print("    norma.wczytaj -> wykonane=%d nieudane=%d, dni ze sladem=%d"
      % (wykonane, nieudane, dni))
sprawdz("licznik nie liczy tego ani do wykonanych, ani do nieudanych",
        (wykonane, nieudane) == (0, 0), (wykonane, nieudane))
sprawdz("ale dzien ma slad w dzienniku", dni == 1, dni)


print()
# HISTORIA JEST WARUNKIEM TYLKO TEGO, CO PONIZEJ.
#
# Guard stal w naglowku pliku, wiec w kopii z historia zalozona
# od nowa gasl CALY test — a nie ten jeden blok, ktory naprawde
# potrzebuje starej wersji pliku. Policzone 4 wrzesnia 2026:
# 617 asercji w 17 plikach nie wykonywalo sie ani razu, a zestaw
# wygladal na zdany, bo pominiecie konczy sie kodem 0.
historia.wymaga_historii("64d881a", zdane=zdane, oblane=oblane)

print("=== 5a. KONTRDOWOD: BLOK Z `64d881a`, DZISIEJSZY `browser` ===")
# CO DOKLADNIE JEST TU MIERZONE — bo od tego zalezy, czy liczba nizej cokolwiek
# znaczy. Blok pochodzi z `git show 64d881a:agent-v2/run.py`, a `browser` jest
# DZISIEJSZY. Roznica miedzy tym przebiegiem a sekcja 3 to WYLACZNIE zmiana
# w `run.py`: brak odsiewu puli i `kandydaci[:budzet]` zamiast liczenia prob.
# Wszystko inne — menu, odczyt „Unfollow", zapis do dziennika — jest to samo.
BLOK_STARY = wytnij(zrodlo_run("64d881a"), "obserwuj")
s_konta, s_wpisy, s_pam, s_plik, s_out = uruchom_blok(
    browser, BLOK_STARY, PULA, NA_SUBSTACKU, pamiec=None,
    kolejnosc=("publikacja1.substack.com", "www.wlasnadomena.example",
               "publikacja2.substack.com"))
print("    STARY BLOK: odwiedzone=%s wpisy=%s"
      % (s_konta.odwiedzone, [(w["rodzaj"], w.get("udane")) for w in s_wpisy]))
s_wykonane, s_nieudane, s_dni = licz_norma(s_plik)
print("    STARY BLOK: norma -> wykonane=%d nieudane=%d"
      % (s_wykonane, s_nieudane))
sprawdz("KONTRDOWOD: stary blok konczyl na pierwszym wylosowanym",
        s_konta.odwiedzone == ["publikacja1"], s_konta.odwiedzone)
sprawdz("KONTRDOWOD: i nie zaobserwowal NIKOGO tego dnia",
        "publikacja2" not in s_konta.obserwowani, s_konta.obserwowani)
sprawdz("KONTRDOWOD: licznik widzial ZERO obserwacji", s_wykonane == 0,
        s_wykonane)
sprawdz("a ten sam dzien z dzisiejszym blokiem dal JEDNA (sekcja 3)",
        WYKONANE_3 == 1 and s_wykonane == 0, (WYKONANE_3, s_wykonane))


print()
print("=== 5b. KONTRDOWOD: ODTWORZONA REGULA ZAPISU SPRZED POPRAWKI ===")
# TU REFERENCJA JEST INNA I TRZEBA TO POWIEDZIEC WPROST. Na `64d881a` droga
# przez menu NIE BYLA JESZCZE ZACOMMITOWANA (`obserwuj_profil` to tam jeden
# wiersz: `_klik_na_profilu(...)`), wiec nie da sie z tego pliku wyjac starego
# ZAPISU dla stanu „juz obserwujemy" — tamten kod tego stanu w ogole nie
# rozpoznawal. Odtwarzamy wiec REGULE, nie plik: wynik o tym samym ksztalcie,
# co przed poprawka (powod w polu `blad`, `zrobione=False`), podany
# PRAWDZIWEJ `browser.dopisz_wynik`. Werdykt wydaje produkcyjna
# `norma.wczytaj`, a po drugiej stronie stoi prawdziwe `obserwuj_profil`
# puszczone na tym samym zdarzeniu.
def jeden_profil(handle="publikacja1"):
    """Prawdziwe `obserwuj_profil` na profilu, ktory JUZ obserwujemy."""
    konta = Substack({handle})
    katalog = pathlib.Path(tempfile.mkdtemp())
    stare = {k: getattr(browser, k) for k in
             ("podlacz_sie", "wymagaj_sesji", "naprawde_wyslac", "DZIENNIK",
              "OBSERWOWANI")}
    try:
        browser.podlacz_sie = lambda: (Przegladarka(konta),) * 3
        browser.wymagaj_sesji = lambda: None
        browser.naprawde_wyslac = lambda w, co: w
        browser.DZIENNIK = katalog / "dziennik.jsonl"
        browser.OBSERWOWANI = katalog / "kogo_obserwujemy.json"
        buf, so = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            wynik = browser.obserwuj_profil(handle, wyslij=True)
        finally:
            sys.stdout = so
        wpisy_ = [json.loads(x) for x in (katalog / "dziennik.jsonl").read_text(
            encoding="utf-8").splitlines() if x.strip()]
        return wynik, wpisy_, katalog / "dziennik.jsonl", konta
    finally:
        for k, v in stare.items():
            setattr(browser, k, v)


w_dzis, dz_dzis, plik_dzis, konta_dzis = jeden_profil()
_kat = pathlib.Path(tempfile.mkdtemp())
_stary_dziennik = browser.DZIENNIK
try:
    browser.DZIENNIK = _kat / "stara-regula.jsonl"
    browser.dopisz_wynik(
        "obserwacja",
        {"handle": "publikacja1", "zrobione": False,
         "blad": "juz obserwujemy publikacja1 — menu pokazuje 'Unfollow'"},
        komu="publikacja1")
    dz_stare = [json.loads(x) for x in browser.DZIENNIK.read_text(
        encoding="utf-8").splitlines() if x.strip()]
    st_wykonane, st_nieudane, _ = licz_norma(browser.DZIENNIK)
finally:
    browser.DZIENNIK = _stary_dziennik
dzis_wykonane, dzis_nieudane, _ = licz_norma(plik_dzis)
print("    TO SAMO ZDARZENIE: profil, ktorego juz obserwujemy")
print("      STARA REGULA: %s -> norma wykonane=%d nieudane=%d"
      % ([(w["rodzaj"], w["udane"]) for w in dz_stare],
         st_wykonane, st_nieudane))
print("      DZISIEJSZA  : %s -> norma wykonane=%d nieudane=%d"
      % ([(w["rodzaj"], w["udane"]) for w in dz_dzis],
         dzis_wykonane, dzis_nieudane))
sprawdz("dzisiejsza droga NIE KLIKA nic poza kolkiem",
        konta_dzis.klikniete == ["Profile actions"], konta_dzis.klikniete)
sprawdz("i nikt nie zostal odobserwowany",
        konta_dzis.obserwowani == {"publikacja1"}, konta_dzis.obserwowani)
sprawdz("KONTRDOWOD: stara regula zapisywala to jako NIEUDANA obserwacje",
        dz_stare[0]["rodzaj"] == "obserwacja"
        and dz_stare[0]["udane"] is False, dz_stare)
sprawdz("KONTRDOWOD: i licznik liczyl to jako porazke",
        (st_wykonane, st_nieudane) == (0, 1), (st_wykonane, st_nieudane))
sprawdz("czyli bylo nie do odroznienia od „przycisk znowu zniknal”",
        st_nieudane == 1)
sprawdz("dzisiaj to samo zdarzenie daje ZERO porazek w liczniku",
        (dzis_wykonane, dzis_nieudane) == (0, 0),
        (dzis_wykonane, dzis_nieudane))
sprawdz("a `juz_obserwowany` mowi wprost, co sie stalo",
        w_dzis["juz_obserwowany"] is True and w_dzis["zrobione"] is False,
        w_dzis)

print()
print("=== 6. SYGNAL `juz_obserwowany` JEST CZYTANY, A NIE WYRZUCANY ===")
# Wada, ktora tepimy w calym tym audycie: sygnal produkowany i ignorowany.
# Mierzymy to ZACHOWANIEM: gdyby blok go nie czytal, po trafieniu na
# obserwowanego skonczylby dzien (sekcja 3 pokazuje, ze nie konczy), a pamiec
# nie dostalaby ani jednego wpisu z tego przebiegu.
konta, wpisy, pam, plik, out = uruchom_blok(
    browser, BLOK_TERAZ, ["publikacja1.substack.com"], NA_SUBSTACKU,
    pamiec=None, kolejnosc=("publikacja1.substack.com",))
sprawdz("odczyt „Unfollow” z menu zamienia sie w wpis do pamieci",
        pam.get("hosty", {}).get("publikacja1.substack.com") == "publikacja1",
        pam)
sprawdz("i w JEDEN wpis dziennika, ktory nie jest porazka",
        [w["rodzaj"] for w in wpisy] == ["obserwacja_pominieta"], wpisy)

# A GDY POMINIECIE IDZIE Z SAMEJ PAMIECI, nie z menu — nikt nic nie zapisal,
# wiec dzien musi dostac swoje podsumowanie. Wlasna domena, ktorej mapy hostow
# jeszcze nie ma, ale uchwyt jest znany: dokladnie przypadek `www.wlasnadomena.example`.
konta, wpisy, pam, plik, out = uruchom_blok(
    browser, BLOK_TERAZ, ["www.wlasnadomena.example"], NA_SUBSTACKU,
    pamiec={"zrzut": None, "uchwyty": {"autor1": "2026-09-01T00:00:00+00:00"},
            "hosty": {}},
    kolejnosc=("www.wlasnadomena.example",))
sprawdz("pominiecie z pamieci nie wchodzi nawet na profil",
        konta.odwiedzone == [], konta.odwiedzone)
sprawdz("ale dzien i tak ma slad, bo nikt inny go nie zostawil",
        [w["rodzaj"] for w in wpisy] == ["obserwacja_pominieta"], wpisy)
sprawdz("i mapa host->uchwyt jest juz zapisana na jutro",
        pam["hosty"].get("www.wlasnadomena.example") == "autor1", pam)


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
