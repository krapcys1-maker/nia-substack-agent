# -*- coding: utf-8 -*-
"""Reagujacy na nasza tresc jest CELEM WPROST — i nie jest odruchem.

## Co bylo zepsute

`run.cele_wedlug_pierwszenstwa` budowalo pule WYLACZNIE z hostow, ktore stoja
w historii naszych komentarzy (`gdzie_komentowalismy.json`). Czlowiek, ktory
zareagowal na nasza tresc, mogl te pule najwyzej PRZESTAWIC — i tylko wtedy,
gdy slug jego nazwy wyswietlanej przypadkiem rownal sie slugowi jakiegos hosta
z tej historii.

Zmierzone 1 wrzesnia 2026 na produkcyjnym dzienniku serwera
(`agent-v2/data/dziennik.jsonl`, 635 wierszy, 199 wpisow `rodzaj="skutek"`,
69 roznych osob w polu `kto`, ZERO wpisow z polem `uchwyty`):

    69 osob zareagowalo na nasza tresc
     7 z nich da sie trafic przez rownosc slugu nazwy ze slugiem hosta
     3 z tych siedmiu przechodza jeszcze odsiew tematyczny
    62 z 69 byly dla doboru celu NIEWIDZIALNE

`browser.dopisz_skutki` zapisuje od 1 wrzesnia obok `kto` takze `uchwyty`.
Ten test sprawdza DRUGA polowe tej naprawy: czy `run.py` naprawde robi z tego
uchwytu cel, czy pole leci do pliku i tam umiera.

## Ile daje nowa pula, policzone na tych samych 69 osobach

    69   osob w polu `kto` (18 dni, 27 nowych w ostatnim tygodniu = 3,9/dobe)
    31   po progu „dwie reakcje ALBO jedna odpowiedz" (26 ma >=2, 21 odpisalo)
    26   po odsianiu tych, ktorzy juz nas czytaja (5 osob)
    20   po odstepie 24 h od ostatniej reakcji
     3   tyle daje mechanizm sprzed tej zmiany

Czyli 20 zamiast 3 — i to jest liczba, ktorej ten test pilnuje ZACHOWANIEM,
a nie asercja po tresci zrodla.

## Dlaczego hamulce, skoro sygnal jest najmocniejszy, jaki mamy

Bo bez nich powstaje maszynka „ty mnie polubiles, ja cie obserwuje", ktora
jest widocznym automatem, a regulamin Substacka wymienia „sztuczna lub
nieautentyczna aktywnosc" jako powod usuwania kont. Liczby z produkcji:

  * `dopisz_skutki` chodzi w bloku 1 tego samego przebiegu, w ktorym bloki
    3c i 3d obserwuja i subskrybuja — kilka minut pozniej, ten sam proces;
  * opoznienie miedzy REAKCJA a jej zapisem: mediana 5,0 h, ale 24 z 199
    zdarzen (12 procent) zapisalo sie w niecala godzine, najszybsze po
    2 minutach;
  * naplyw 3,9 reagujacego na dobe wobec budzetu 0,93 dzialania na dobe
    (0,42 obserwacji + 0,51 subskrypcji wg `config` przez `stages.budzet_dnia`).

Trzy hamulce: odstep 24 h od reakcji, prog „dwie reakcje albo jedna
odpowiedz", wykluczenie tych, ktorzy juz nas czytaja. Plus przeplot, ktory
oddaje co drugi slot hostom z historii — inaczej przy 1,1 wchodzacego na dobe
wobec 0,93 wychodzacego poziom hostow nie zostalby osiagniety ANI RAZU.

## Co ten test mierzy

ZACHOWANIE: kogo naprawde odwiedzono na atrapie Substacka i co wpadlo do
dziennika. Blok `obserwuj` jest wycinany z `run.py` przez `ast`
i URUCHAMIANY; dziennik jest prawdziwy, tylko przekierowany do katalogu
tymczasowego. Zero asercji po tresci zrodla, zero sieci, zero przegladarki,
zero wywolan modelu.

KONTRDOWODY SA ODTWARZANE, NIE OPISANE, i sa dwa, bo sa dwie rozne wady:

  * sekcja 7 puszcza ten sam dziennik i te sama historie przez blok `obserwuj`
    wyjety z `git show 6ed4e7d:agent-v2/run.py` — wersja odniesienia PRZYPIETA
    DO SHA, nigdy do HEAD, bo kontrdowod mierzony wzgledem HEAD gasnie
    w chwili commita, ktorego strzeze. W `6ed4e7d` pula to jeszcze
    `random.shuffle` na CALEJ historii komentarzy: funkcji
    `cele_wedlug_pierwszenstwa` nie ma tam wcale, wiec kontrdowod nie moze byc
    porownaniem rachunkow — jest porownaniem tego, KOGO oba bloki naprawde
    odwiedzily na tych samych danych. Zmierzone: stary idzie do
    `publikacja5` (blog o jedzeniu sprzed przestawienia konta na AI),
    dzisiejszy do `publikacja3` (osoba, ktora dwa razy zareagowala
    na nasza tresc), a jej uchwyt lezal w dzienniku przez caly czas;
  * sekcja 8 odtwarza wersje BEZ HAMULCOW (odstep 0 h, prog 1 reakcji, pusty
    plik czytelnikow) na dzisiejszym kodzie i pokazuje, ze wtedy konto
    obserwuje osobe, ktora polubila nasza notke piec minut wczesniej.
    Tej wersji nie ma w zadnym commicie — i wlasnie dlatego trzeba ja
    odtworzyc, zeby hamulec byl czyms mierzalnym, a nie deklaracja.

Test nie zalezy od dzisiejszej daty: daty reakcji sa liczone wzglednie
(„trzy dni temu", „piec minut temu") w chwili uruchomienia, a daty hostow sa
stalymi porownywanymi ze stala `PRZESTAWIENIE_KONTA_NA_AI`.

PRODUKCJA: bez zmian. Dziennik, plik czytelnikow i pamiec obserwowanych ida do
katalogu tymczasowego; `podlacz_sie` jest atrapa, ktora liczy sesje.
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

KORZEN = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(KORZEN / "agent-v2"))

import browser        # noqa: E402
import config         # noqa: E402
import norma          # noqa: E402
import run            # noqa: E402

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


PILNOWANE = [config.DATA_DIR / "dziennik.jsonl",
             config.DATA_DIR / "czytelnicy.jsonl",
             config.DATA_DIR / "kogo_obserwujemy.json",
             config.DATA_DIR / "gdzie_komentowalismy.json"]
PRZED = {str(p): odcisk(p) for p in PILNOWANE}


# --- CZAS LICZONY WZGLEDNIE --------------------------------------------------
#
# Data w tescie nie moze byc stala, bo hamulec odstepu porownuje sie z „teraz".
# Stala data zaczela by przechodzic albo oblewac zaleznie od dnia uruchomienia
# — a to jest dokladnie ta klasa testu, ktora klamie po pol roku.
def temu(**ile) -> str:
    return (_dt.datetime.now(_dt.timezone.utc)
            - _dt.timedelta(**ile)).isoformat(timespec="seconds")[:19]


DAWNO = lambda: temu(days=3)          # noqa: E731  — poza progiem 24 h
PRZED_CHWILA = lambda: temu(minutes=5)  # noqa: E731  — 12% zdarzen tak wlasnie


def skutek(zdarzenie, typ, kto, uchwyty, kiedy_zdarzenia):
    """Wiersz `skutek` w ksztalcie, ktory zapisuje `browser.dopisz_skutki`."""
    wpis = {"kiedy": temu(minutes=1), "rodzaj": "skutek", "udane": True,
            "zdarzenie": zdarzenie, "typ": typ, "czego": 1,
            "ilu": len(kto), "kto": list(kto),
            "kiedy_zdarzenia": kiedy_zdarzenia}
    if uchwyty is not None:
        wpis["uchwyty"] = list(uchwyty)
    return wpis


# --- ATRAPA SUBSTACKA --------------------------------------------------------
#
# Odwzorowuje pomiar z 1 wrzesnia: na wierzchu profilu sa „Subscribe”,
# „Message” i kolko „...”, a „Follow” siedzi w menu pod kolkiem.
MENU_WOLNY = ["Copy link", "Share", "Send message", "Follow",
              "Mute", "Block", "Report"]
MENU_OBSERWOWANY = ["Copy link", "Share", "Send message", "Unfollow",
                    "Mute", "Block", "Report"]


class Substack:
    def __init__(self, obserwowani=()):
        self.obserwowani = set(obserwowani)
        self.sesje = 0
        self.odwiedzone = []
        self.klikniete = []


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


# --- WYCINANIE BLOKU Z `run.py` ----------------------------------------------
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
    def __init__(self, hosty: dict):
        self.hosty = dict(hosty)

    def _historia(self):
        return dict(self.hosty)


def uruchom_blok(kod_bloku, nazwa, historia, konta, budzet=1,
                 kolejnosc=(), dziennik_wstepny=(), czytelnicy=(),
                 dodatki=None):
    """Puszcza blok na atrapie. Oddaje (konta, wpisy, plik dziennika, wydruk)."""
    katalog = pathlib.Path(tempfile.mkdtemp())
    plik = katalog / "dziennik.jsonl"
    if dziennik_wstepny:
        plik.write_text("".join(json.dumps(w, ensure_ascii=False) + "\n"
                                for w in dziennik_wstepny), encoding="utf-8")
    plik_czyt = katalog / "czytelnicy.jsonl"
    if czytelnicy:
        plik_czyt.write_text("".join(json.dumps(z, ensure_ascii=False) + "\n"
                                     for z in czytelnicy), encoding="utf-8")

    def podlacz():
        konta.sesje += 1
        p = Przegladarka(konta)
        return p, p, p

    def uchwyt_publikacji(host):
        # Zmierzone zachowanie prawdziwej funkcji: dla domeny Substacka nazwa
        # konta to pierwszy czlon hosta i NIE MA zadnego zapytania; dla wlasnej
        # domeny uchwyt wychodzi z API i dlatego tu jest tablica.
        host = (host or "").strip().lower()
        if host.endswith(".substack.com"):
            return host.split(".")[0]
        return {"www.jankowalski.com": "kowalski",
                "www.funduszx.news": "funduszx"}.get(host)

    stare = {k: getattr(browser, k) for k in
             ("podlacz_sie", "wymagaj_sesji", "naprawde_wyslac",
              "uchwyt_publikacji", "DZIENNIK", "OBSERWOWANI", "CZYTELNICY")}
    stary_shuffle = random.shuffle
    stara_norma = norma.DZIENNIK
    try:
        browser.podlacz_sie = podlacz
        browser.wymagaj_sesji = lambda: None
        browser.naprawde_wyslac = lambda w, co: w
        browser.uchwyt_publikacji = uchwyt_publikacji
        browser.DZIENNIK = plik
        browser.CZYTELNICY = plik_czyt
        browser.OBSERWOWANI = katalog / "kogo_obserwujemy.json"
        norma.DZIENNIK = plik
        random.shuffle = lambda lst: lst.sort(
            key=lambda h: kolejnosc.index(h) if h in kolejnosc else 99)

        ns = {"browser": browser, "config": config, "kanal": Kanal(historia),
              "na_teraz": {"follow": budzet, "subskrypcje": budzet},
              "wyslij": True, "rytm_stanu": {},
              "zostal_czas": lambda *a, **k: True,
              "rytm": lambda *a, **k: True, "print": print,
              # `random` — bo blok z `6ed4e7d` woła `random.shuffle` sam.
              "random": random,
              "cele_wedlug_pierwszenstwa": run.cele_wedlug_pierwszenstwa,
              "powod_pustej_puli": run.powod_pustej_puli,
              "kogo_juz_subskrybujemy": run.kogo_juz_subskrybujemy,
              "czy_juz_subskrybujemy": run.czy_juz_subskrybujemy,
              "PRZESTAWIENIE_KONTA_NA_AI": run.PRZESTAWIENIE_KONTA_NA_AI}
        ns.update(dodatki or {})
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


def z_dziennikiem(wpisy, czytelnicy=(), fn=None):
    """Wola `fn()` przy dzienniku i pliku czytelnikow w katalogu tymczasowym."""
    katalog = pathlib.Path(tempfile.mkdtemp())
    plik = katalog / "dziennik.jsonl"
    plik.write_text("".join(json.dumps(w, ensure_ascii=False) + "\n"
                            for w in wpisy), encoding="utf-8")
    plik_czyt = katalog / "czytelnicy.jsonl"
    plik_czyt.write_text("".join(json.dumps(z, ensure_ascii=False) + "\n"
                                 for z in czytelnicy), encoding="utf-8")
    stare = (browser.DZIENNIK, browser.CZYTELNICY)
    stary_shuffle = random.shuffle
    try:
        browser.DZIENNIK = plik
        browser.CZYTELNICY = plik_czyt
        random.shuffle = lambda lst: None       # kolejnosc WEWNATRZ poziomu
        return fn()
    finally:
        random.shuffle = stary_shuffle
        browser.DZIENNIK, browser.CZYTELNICY = stare


# --- DANE ODWZOROWUJACE PRODUKCJE --------------------------------------------
#
# Historia komentarzy: dwa hosty sprzed przestawienia konta na AI i dwa po nim.
# Zadnego z nich nie ma wsrod reagujacych — o to wlasnie chodzi, bo produkcyjne
# 62 z 69 osob tez nie maja w tej historii nic.
HISTORIA = {
    "publikacja5.substack.com": "2026-08-16T13:00:00+00:00",
    "publikacja4.substack.com":          "2026-08-16T13:14:10+00:00",
    "igordziewiaty.substack.com":          "2026-08-31T10:00:00+00:00",
    "www.funduszx.news":                    "2026-08-30T09:00:00+00:00",
}

# Osiem osob odwzorowujacych kazdy przypadek zmierzony na produkcji.
def dziennik_pelny():
    return [
        # PRZECHODZI: dwie reakcje, obie dawno, nie ma jej w historii hostow.
        skutek("note_like:1", "note_like", ["Publikacja Chaosu"],
               ["publikacja3"], DAWNO()),
        skutek("note_like:2", "note_like", ["Publikacja Chaosu"],
               ["publikacja3"], DAWNO()),
        # PRZECHODZI: jedna reakcja, ale to ODPOWIEDZ — czyli ktos pisal.
        skutek("note_reply:3", "note_reply", ["Lech Dwunasty"],
               ["annanowak"], DAWNO()),
        # ODPADA: jedno polubienie i nic wiecej (43 z 69 osob na produkcji).
        skutek("note_like:4", "note_like", ["Publikacja Lustrzana AI"],
               ["publikacja10"], DAWNO()),
        # ODPADA: dwie reakcje, ale najswiezsza sprzed pieciu minut.
        skutek("note_like:5", "note_like", ["Swiezak"], ["swiezak"], DAWNO()),
        skutek("note_like:6", "note_like", ["Swiezak"], ["swiezak"],
               PRZED_CHWILA()),
        # ODPADA: juz nas obserwuje — wpis `follow` mowi to wprost.
        skutek("note_like:7", "note_like", ["Leonard"], ["publikacja11"],
               DAWNO()),
        skutek("follow:8", "follow", ["Leonard"], ["publikacja11"], DAWNO()),
        # ODPADA: dwie reakcje, ale stoi w `czytelnicy.jsonl`.
        skutek("note_like:9", "note_like", ["Halina Osma"],
               ["publikacja7"], DAWNO()),
        skutek("note_like:10", "note_like", ["Halina Osma"],
               ["publikacja7"], DAWNO()),
        # ODPADA: to MY. Substack melduje w tym samym kanale, ze nasza
        # zaplanowana notka poszla — 9 takich zdarzen na produkcji.
        skutek("sched:11", "scheduled_note_sent", ["Your Publication"],
               [config.SUBSTACK_HANDLE], DAWNO()),
        skutek("sched:12", "scheduled_note_sent", ["Your Publication"],
               [config.SUBSTACK_HANDLE], DAWNO()),
        # ODPADA: rozjazd list. Dwie nazwy, jeden uchwyt — nie wiadomo, czyj.
        skutek("note_like:13", "note_like", ["Ktos A", "Ktos B"],
               ["ktosa"], DAWNO()),
        skutek("note_like:14", "note_like", ["Ktos A", "Ktos B"],
               ["ktosa"], DAWNO()),
        # ODPADA: stary wpis bez pola `uchwyty` — 199 takich na produkcji.
        skutek("note_like:15", "note_like", ["Igor Dziewiaty"], None, DAWNO()),
        skutek("note_like:16", "note_like", ["Igor Dziewiaty"], None, DAWNO()),
    ]


CZYTELNICY = [{"kiedy": "2026-09-01T11:38:25+00:00",
               "odczytane": ["obserwujacy", "subskrybenci"], "blad": None,
               "obserwujacy": [{"uchwyt": "publikacja7",
                                "nazwa": "Halina Osma"}],
               "subskrybenci": [{"uchwyt": "publikacja3x",
                                 "nazwa": "ktos inny"}]}]

BLOK_OBSERWUJ = wytnij(zrodlo_run(), "obserwuj")


print("=== 1. REAGUJACY JEST CELEM WPROST, NIE PRZEZ ZBIEG NAZWY ===")
kand, rach = z_dziennikiem(
    dziennik_pelny(), CZYTELNICY,
    fn=lambda: run.cele_wedlug_pierwszenstwa(HISTORIA))
print("    rachunek: %s" % rach)
print("    kandydaci: %s" % kand)
sprawdz("dwoje reagujacych weszlo do puli mimo braku w historii hostow",
        rach["reagujacy"] == 2, rach)
sprawdz("i to sa ci dwoje, ktorzy mieli przejsc",
        {"publikacja3.substack.com", "annanowak.substack.com"} <= set(kand),
        kand)
# Szesc, nie osiem: nasz wlasny uchwyt i uchwyt z rozjazdu list NIE licza sie
# nawet jako kandydaci — nie sa odsiani, tylko nie sa ludzmi do zaczepienia.
sprawdz("szesc uchwytow rozpoznanych z dziennika (bez nas i bez rozjazdu)",
        rach["reagujacy_z_uchwytem"] == 6, rach)

print()
print("=== 2. HAMULCE: KTO NIE WCHODZI I DLACZEGO ===")
sprawdz("jedno polubienie nie wystarcza — prog to dwie reakcje",
        "publikacja10.substack.com" not in kand, kand)
sprawdz("reakcja sprzed pieciu minut CZEKA na odstep",
        "swiezak.substack.com" not in kand, kand)
sprawdz("kto juz nas obserwuje, tego nie zaczepiamy",
        "publikacja11.substack.com" not in kand, kand)
sprawdz("kto stoi w czytelnicy.jsonl, tego tez nie",
        "publikacja7.substack.com" not in kand, kand)
sprawdz("rachunek liczy KAZDY hamulec osobno, a nie jednym workiem",
        (rach["reagujacy_slabi"], rach["reagujacy_swiezy"],
         rach["reagujacy_juz_czyta"]) == (1, 1, 2), rach)

print()
print("=== 3. DWA SPOSOBY NA CEL, KTORY WYGLADA NA ZMIERZONY ===")
sprawdz("MY SAMI nie jestesmy celem, choc stoimy w kanale aktywnosci",
        not any(str(k).startswith(config.SUBSTACK_HANDLE) for k in kand), kand)
sprawdz("rozjazd nazw i uchwytow jest ODRZUCANY, a nie zgadywany",
        "ktosa.substack.com" not in kand, kand)
sprawdz("stary wpis bez pola `uchwyty` nie wywala doboru celu",
        "igordziewiaty.substack.com" in kand, kand)

print()
print("=== 4. PRZEPLOT: POZIOM HOSTOW NIE JEST ZAGLODZONY ===")
# Bez przeplotu obie reakcje staly by przed obydwoma hostami, a przy budzecie
# 0,93 dzialania na dobe i naplywie 1,1 reagujacego na dobe host nie zostalby
# osiagniety nigdy.
pozycje_reakcji = [i for i, h in enumerate(kand)
                   if h in ("publikacja3.substack.com",
                            "annanowak.substack.com")]
print("    kolejnosc: %s" % kand)
sprawdz("pierwszy slot nalezy do reagujacego", pozycje_reakcji[:1] == [0], kand)
sprawdz("ale drugi juz do hosta z historii czytania",
        kand[1] not in ("publikacja3.substack.com",
                        "annanowak.substack.com"), kand)
sprawdz("host, ktory jest JEDNOCZESNIE reagujacym, nie stoi w puli dwa razy",
        len(kand) == len(set(kand)), kand)

print()
print("=== 5. ZACHOWANIE BLOKU: KOGO NAPRAWDE ODWIEDZONO ===")
konta, wpisy, plik, out = uruchom_blok(
    BLOK_OBSERWUJ, "obserwuj", HISTORIA, Substack(),
    kolejnosc=("publikacja3.substack.com",),
    dziennik_wstepny=dziennik_pelny(), czytelnicy=CZYTELNICY)
print("    odwiedzone profile: %s" % konta.odwiedzone)
print("    zaobserwowani: %s" % sorted(konta.obserwowani))
sprawdz("blok wszedl na profil reagujacego, a nie na host z historii",
        konta.odwiedzone == ["publikacja3"], konta.odwiedzone)
sprawdz("i naprawde go zaobserwowal",
        konta.obserwowani == {"publikacja3"}, konta.obserwowani)
sprawdz("JEDNA sesja przegladarki — adres `<uchwyt>.substack.com` nie kosztuje"
        " zapytania o uchwyt", konta.sesje == 1, konta.sesje)
nowe = [w for w in wpisy if w["rodzaj"] == "obserwacja"]
sprawdz("dziennik ma wpis obserwacji na uchwyt, nie na adres",
        len(nowe) == 1 and nowe[0].get("komu") == "publikacja3", nowe)
sprawdz("nikt spoza puli nie zostal odwiedzony",
        "swiezak" not in konta.odwiedzone
        and "publikacja11" not in konta.odwiedzone, konta.odwiedzone)

print()
print("=== 6. PUSTA PULA NADAL MOWI, ILU BYLO NA KAZDYM POZIOMIE ===")
# Sama historia sprzed przestawienia konta ORAZ reagujacy, ktorzy wszyscy
# wpadli w hamulce. Poprawny wynik to zero Z POWODEM.
TYLKO_STARE = {h: k for h, k in HISTORIA.items() if k[:10] < "2026-08-25"}
SAMI_ODRZUCENI = [w for w in dziennik_pelny()
                  if w["kto"][0] in ("Publikacja Lustrzana AI", "Swiezak", "Leonard")]
konta2, wpisy2, plik2, out2 = uruchom_blok(
    BLOK_OBSERWUJ, "obserwuj", TYLKO_STARE, Substack(),
    dziennik_wstepny=SAMI_ODRZUCENI, czytelnicy=CZYTELNICY)
pominiete = [w for w in wpisy2 if w["rodzaj"] == "obserwacja_pominieta"]
print("    powod: %s" % (pominiete[0].get("powod") if pominiete else "BRAK"))
sprawdz("ZERO sesji — nikt nie dostal powiadomienia",
        konta2.sesje == 0 and konta2.odwiedzone == [], konta2.odwiedzone)
sprawdz("ale wpis jest — blok bez sladu wyglada na blok, ktorego nie ma",
        len(pominiete) == 1, wpisy2)
powod = pominiete[0].get("powod") if pominiete else ""
sprawdz("powod niesie liczby POZIOMU HOSTOW",
        "2 sprzed przestawienia" in powod and "0 po nim" in powod, powod)
sprawdz("i liczby POZIOMU REAGUJACYCH, kazdy hamulec osobno",
        "reagujacych z uchwytem 3" in powod
        and "1 juz nas czyta" in powod
        and "1 ponizej progu" in powod
        and "1 mlodszych niz 24 h" in powod, powod)
sprawdz("oraz koncowe zero, ktore nie udaje wyniku",
        "w puli 0" in powod, powod)

print()
print("=== 7. KONTRDOWOD: WERSJA Z %s NIE WIDZI REAGUJACEGO ===" % ODNIESIENIE)
# W `6ed4e7d` pula to `random.shuffle` na CALEJ historii komentarzy — nie ma
# tam ani poziomow, ani reagujacych, ani odsiewu tematycznego. Ten sam dziennik
# z tymi samymi uchwytami lezy tam bezuzyteczny.
konta_st, wpisy_st, _, _ = uruchom_blok(
    wytnij(zrodlo_run(ODNIESIENIE), "obserwuj"), "obserwuj", HISTORIA,
    Substack(), kolejnosc=("publikacja5.substack.com",),
    dziennik_wstepny=dziennik_pelny(), czytelnicy=CZYTELNICY)
print("    STARY blok odwiedzil: %s" % konta_st.odwiedzone)
sprawdz("KONTRDOWOD: stary blok nie wszedl do zadnego reagujacego",
        "publikacja3" not in konta_st.odwiedzone
        and "annanowak" not in konta_st.odwiedzone, konta_st.odwiedzone)
sprawdz("KONTRDOWOD: poszedl za to do bloga sprzed przestawienia konta na AI",
        konta_st.odwiedzone == ["publikacja5"], konta_st.odwiedzone)
konta_dz, _, _, _ = uruchom_blok(
    BLOK_OBSERWUJ, "obserwuj", HISTORIA, Substack(),
    kolejnosc=("publikacja5.substack.com",),
    dziennik_wstepny=dziennik_pelny(), czytelnicy=CZYTELNICY)
print("    DZISIEJSZY blok na tych samych danych: %s" % konta_dz.odwiedzone)
sprawdz("a dzisiejszy na tych samych danych idzie do reagujacego",
        konta_dz.odwiedzone in (["publikacja3"], ["annanowak"]),
        konta_dz.odwiedzone)

print()
print("=== 8. KONTRDOWOD ODTWORZONY: TA SAMA POPRAWKA BEZ HAMULCOW ===")
# Wersji bez hamulcow nie ma w zadnym commicie — powstala by, gdyby uchwyt
# podlaczyc „na wprost". Odtwarzamy ja, zeby hamulec byl mierzalny.
_stary_odstep = run.ODSTEP_OD_REAKCJI_H
_stary_prog = run.MIN_REAKCJI_BEZ_ROZMOWY
try:
    run.ODSTEP_OD_REAKCJI_H = 0
    run.MIN_REAKCJI_BEZ_ROZMOWY = 1
    konta3, wpisy3, _, _ = uruchom_blok(
        BLOK_OBSERWUJ, "obserwuj", HISTORIA, Substack(),
        kolejnosc=("swiezak.substack.com",),
        dziennik_wstepny=[w for w in dziennik_pelny()
                          if w["kto"][0] == "Swiezak"],
        czytelnicy=())
    print("    BEZ HAMULCOW odwiedzil: %s" % konta3.odwiedzone)
    sprawdz("KONTRDOWOD: bez hamulcow konto obserwuje osobe, ktora polubila"
            " nasza notke piec minut wczesniej",
            konta3.odwiedzone == ["swiezak"], konta3.odwiedzone)
finally:
    run.ODSTEP_OD_REAKCJI_H = _stary_odstep
    run.MIN_REAKCJI_BEZ_ROZMOWY = _stary_prog

konta4, wpisy4, _, _ = uruchom_blok(
    BLOK_OBSERWUJ, "obserwuj", HISTORIA, Substack(),
    kolejnosc=("swiezak.substack.com",),
    dziennik_wstepny=[w for w in dziennik_pelny() if w["kto"][0] == "Swiezak"],
    czytelnicy=())
print("    Z HAMULCAMI odwiedzil: %s" % konta4.odwiedzone)
sprawdz("Z HAMULCAMI ta sama osoba nie zostala zaczepiona",
        "swiezak" not in konta4.odwiedzone, konta4.odwiedzone)
sprawdz("a blok mimo to zrobil cos sensownego zamiast stanac",
        konta4.odwiedzone != [], konta4.odwiedzone)

print()
print("=== 9. DROGA PRZYJMUJE ADRES REAGUJACEGO BEZ SIECI ===")
# Prawdziwe funkcje, nie atrapy. `podlacz_sie` rzuca — gdyby ktorakolwiek
# z nich chciala wejsc do sieci dla adresu `<uchwyt>.substack.com`, test to
# pokaze wyjatkiem, a nie domyslem.
_stare_podlacz = browser.podlacz_sie
_stare_wymagaj = browser.wymagaj_sesji


def _nie_wolno():
    raise AssertionError("sesja przegladarki dla adresu reagujacego")


try:
    browser.podlacz_sie = _nie_wolno
    browser.wymagaj_sesji = lambda: None
    sprawdz("uchwyt_publikacji skraca adres do uchwytu bez zapytania",
            browser.uchwyt_publikacji("publikacja3.substack.com")
            == "publikacja3")
    sprawdz("czy_juz_obserwujemy porownuje uchwyt z uchwytem",
            browser.czy_juz_obserwujemy(
                "publikacja3.substack.com",
                {"uchwyty": {"publikacja3": "kiedys"}, "hosty": {}}) is True)
    sprawdz("czy_juz_subskrybujemy tak samo",
            run.czy_juz_subskrybujemy("publikacja3.substack.com",
                                      {"publikacja3"}) is True)
finally:
    browser.podlacz_sie = _stare_podlacz
    browser.wymagaj_sesji = _stare_wymagaj

print()
print("=== PRODUKCJA: bez zmian ===")
for p in PILNOWANE:
    teraz = odcisk(p)
    ok = teraz == PRZED[str(p)]
    print("  %-30s %s" % (p.name, "bez zmian" if ok else "ZMIENIONY"))
    if not ok:
        oblane += 1

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
