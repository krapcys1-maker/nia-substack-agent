# -*- coding: utf-8 -*-
"""Obserwowanie chodzi przez menu „...", a profilu JUZ OBSERWOWANEGO nie tyka.

## Co bylo zepsute

23 sierpnia 2026 uznano, ze Substack ZDJAL przycisk „Follow" z profili.
Podstawa: szesc profili, slowo „Follow" nie wystepowalo w ich HTML ani razu.
POMIAR BYL PRAWDZIWY, WNIOSEK FALSZYWY — przycisk siedzi w menu pod kolkiem
„..." obok „Subscribe" i „Message", a Substack rysuje to menu DOPIERO PO
KLIKNIECIU. W HTML zamknietej strony go nie ma i byc nie moze.

Wniosek pociagnal za soba trzy wpisy naraz i to one kosztowaly dziewiec dni:

  * `config.FOLLOW_MIESIECZNIE = (0, 0)`  — budzet dnia przestal cokolwiek
    przydzielac obserwacjom,
  * `run.py::obserwuj` — „WYCOFANE 2026-08-23",
  * `norma.NIEWYKONALNE = {"obserwacja": "Substack zdjal przycisk Follow"}` —
    i to jest najgorszy z trzech, bo tabela normy TLUMACZYLA ZERO ZDANIEM,
    KTORE NIE BYLO PRAWDA. Zero z wyjasnieniem przestaje wygladac na problem.

## Pomiar, na ktorym stoi ten test (1 wrzesnia 2026, zywa sesja, serwer)

Menu otwierane przez `button[aria-label="Profile actions"]` (pl: „Działania
w profilu"). Odczyt, zadnej pozycji nie klikniete:

    @publikacja2, @czytelnik7, @czytelnik4   (nieobserwowani)
      Copy link / Share / Send message / Follow / Mute / Block / Report

    @autor1                               (obserwowany)
      Copy link / Share / Unfollow / Manage Subscription / Mute / Block / Report
    @publikacja3                       (obserwowany)
      Copy link / Share / Send message / Unfollow / Manage Subscription /
      Mute / Block / Report
    @publikacja1                             (obserwowany)
      Copy link / Share / Send message / Unfollow / Mute / Block / Report

Ta sama strona z `locale="pl-PL"` (te samo konto, ta sama sesja):
      Skopiuj link / Udostępnij / Wyślij wiadomość / Obserwuj / Wycisz /
      Zablokuj / Zgłoś
      Skopiuj link / Udostępnij / Przestań obserwować / Zarządzaj subskrypcją /
      Wycisz / Zablokuj / Zgłoś

Z tego pomiaru biora sie WSZYSTKIE liczby ponizej: menu ma raz 7, raz 8
pozycji; „Follow" stoi raz na miejscu 4, raz na 3; jezyk jest wlasnoscia
PRZEGLADARKI, nie konta (serwer widzi angielski, wlasciciel polski).

## Co ten test mierzy

ZACHOWANIE, nie tresc zrodla. Atrapa strony odwzorowuje maszyne stanu
zmierzona wyzej: menu jest zamkniete, otwiera sie po kliknieciu kolka,
a klikniecie „Follow" przestawia profil w stan obserwowany i podmienia
pozycje na „Unfollow". Kazda asercja patrzy na to, CO ATRAPA ODNOTOWALA:
ktore wezly zostaly klikniete i co poszlo do dziennika.

## Kontrdowody (odtwarzane, nie cytowane) — i jedna hipoteza

  1. STARA DROGA. `browser._klik_na_profilu` nadal zyje w pliku (obsluguje
     subskrypcje) i JEST doslownie przedpoprawkowa implementacja
     `obserwuj_profil`. Puszczamy ja na tej samej atrapie i pokazujemy, ze
     odchodzi z pustymi rekami — bo na wierzchu strony sa tylko „Subscribe",
     „Message" i kolko.
  2. DOPASOWANIE PO FRAGMENCIE — HIPOTEZA PROJEKTOWA, NIE KONTRDOWOD I NIE
     ZMIERZONA REGRESJA. Produkcja nigdy tak nie wybierala: droga sprzed
     poprawki pyta Playwrighta z `exact=True` (`_klik_na_profilu`), a dzisiejsza
     czyta teksty sama i porownuje przez `==`. Sekcja 10 stawia wiec obok
     siebie PRODUKCJE (`obserwuj_profil` na zmierzonych menu) i regule wyboru
     NAPISANA W TYM TESCIE — i nazywa, ktore jest ktore.
  3. WYCOFANY BUDZET. `stages.budzet_dnia` z `FOLLOW_MIESIECZNIE = (0, 0)`.

Wersje odniesienia sa PRZYPIETE do `64d881a` (stan przed ta praca), nie do
HEAD — kontrdowod mierzony wzgledem HEAD gasnie w chwili commita, ktorego
strzeze.

Zero sieci, zero przegladarki, zero wywolan modelu, zero zapisu do produkcji.
"""

import hashlib
import io
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import config          # noqa: E402
import browser         # noqa: E402
# Authenticated-session precondition for these isolated UI fixtures.
# Real identity verification is covered by test_quality_contract.AccountContract.
browser.wymagaj_wlasciwego_konta = lambda page: None
import norma           # noqa: E402
import stages          # noqa: E402

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
             config.DATA_DIR / "kogo_obserwujemy.json"]
PRZED = {str(p): odcisk(p) for p in PILNOWANE}


# --- ZMIERZONE MENU ---------------------------------------------------------
#
# Doslownie to, co oddal odczyt z 1 wrzesnia 2026. Kolejnosc i liczba pozycji
# sa czescia pomiaru, nie ozdoba: na nich stoi asercja, ze wybor nie moze isc
# po numerze pozycji.
MENU_EN_WOLNY = ["Copy link", "Share", "Send message", "Follow",
                 "Mute", "Block", "Report"]
MENU_EN_OBSERWOWANY = ["Copy link", "Share", "Unfollow", "Manage Subscription",
                       "Mute", "Block", "Report"]
MENU_EN_OBSERWOWANY_8 = ["Copy link", "Share", "Send message", "Unfollow",
                         "Manage Subscription", "Mute", "Block", "Report"]
MENU_PL_WOLNY = ["Skopiuj link", "Udostępnij", "Wyślij wiadomość", "Obserwuj",
                 "Wycisz", "Zablokuj", "Zgłoś"]
MENU_PL_OBSERWOWANY = ["Skopiuj link", "Udostępnij", "Przestań obserwować",
                       "Zarządzaj subskrypcją", "Wycisz", "Zablokuj", "Zgłoś"]
# Jezyk, ktorego NIE zmierzylem. Menu bez zadnej znanej pozycji obserwowania
# ma konczyc sie odejsciem z pustymi rekami, a nie klknieciem czegokolwiek —
# w tym samym menu stoja „wycisz", „zablokuj" i „zglos".
MENU_OBCY = ["Kopieren", "Teilen", "Nachricht senden", "Abonnieren",
             "Stummschalten", "Blockieren", "Melden"]


# --- ATRAPA STRONY ----------------------------------------------------------
#
# Odwzorowuje maszyne stanu, nie HTML: menu jest zamkniete, otwiera sie po
# kliknieciu kolka, a klikniecie pozycji obserwowania przestawia profil.
class Wezel:
    def __init__(self, strona, tekst, rodzaj):
        self.strona = strona
        self.tekst = tekst
        self.rodzaj = rodzaj

    def inner_text(self):
        if self.rodzaj == "menuitem" and not self.strona.menu_otwarte:
            raise RuntimeError("menu zamkniete — nie ma czego czytac")
        return self.tekst

    def is_visible(self):
        return self.rodzaj != "brak"

    def count(self):
        # Playwright oddaje z `.first` LOKATOR, ktory sam ma `count()` — i przy
        # pustym wyniku daje zero, zamiast rzucac. `_klik_na_profilu` opiera na
        # tym cala swoja galez „nie ma przycisku", wiec atrapa musi to
        # odwzorowac, a nie wysypac sie IndexError-em.
        return 0 if self.rodzaj == "brak" else 1

    def click(self, timeout=None):
        self.strona.klikniete.append(self.tekst)
        if self.rodzaj == "kolko":
            self.strona.menu_otwarte = True
            return
        if not self.strona.menu_otwarte:
            raise RuntimeError("klikniecie w zamkniete menu")
        if self.tekst in ("Follow", "Obserwuj"):
            self.strona.obserwowany = True
        if self.tekst in ("Unfollow", "Przestań obserwować"):
            self.strona.obserwowany = False
        self.strona.menu_otwarte = False


class Lista:
    """Odpowiednik lokatora Playwrighta: count/first/nth."""

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
    def __init__(self, menu_wolny, menu_obserwowany, obserwowany=False,
                 etykieta_kolka="Profile actions", jest_kolko=True,
                 przyciski_na_wierzchu=("Subscribe", "Message")):
        self.menu_wolny = menu_wolny
        self.menu_obserwowany = menu_obserwowany
        self.obserwowany = obserwowany
        self.etykieta_kolka = etykieta_kolka
        self.jest_kolko = jest_kolko
        self.przyciski_na_wierzchu = list(przyciski_na_wierzchu)
        self.menu_otwarte = False
        self.klikniete = []
        self.zamknieta = False
        self.keyboard = Klawiatura(self)

    def pozycje(self):
        return self.menu_obserwowany if self.obserwowany else self.menu_wolny

    def goto(self, *a, **k):
        pass

    def wait_for_timeout(self, *a):
        pass

    def close(self):
        self.zamknieta = True

    def locator(self, selektor):
        # Jedyny selektor, jakiego uzywa kod: button[aria-label="..."].
        if self.jest_kolko and ('aria-label="%s"' % self.etykieta_kolka) in selektor:
            return Lista([Wezel(self, self.etykieta_kolka, "kolko")])
        return Lista([])

    def get_by_role(self, rola, name=None, exact=False):
        if rola == "menuitem":
            if not self.menu_otwarte:
                return Lista([])
            return Lista([Wezel(self, t, "menuitem") for t in self.pozycje()])
        if rola == "button":
            # Stara droga (`_klik_na_profilu`) pyta o przyciski PO NAZWIE.
            trafione = [n for n in self.przyciski_na_wierzchu
                        if (n == name if exact else (name or "") in n)]
            return Lista([Wezel(self, n, "przycisk") for n in trafione])
        return Lista([])


class Przegladarka:
    def __init__(self, strona):
        self.strona = strona

    def new_page(self):
        return self.strona

    def close(self):
        pass

    def stop(self):
        pass


def uruchom(strona, wyslij=True, funkcja=None):
    """Puszcza `obserwuj_profil` (albo inna) na atrapie i zbiera dziennik.

    DWIE DROGI ZAPISU, BO OD 1 WRZESNIA SA DWIE. Zwykle dzialanie idzie przez
    `dopisz_wynik` (udane/nieudane), a stan „juz go obserwujemy" — przez
    `zapisz_w_dzienniku` z wlasnym rodzajem, bo nie jest ani jednym, ani
    drugim. Atrapa lapie obie, inaczej test przestalby widziec polowe zdarzen.

    `OBSERWOWANI` idzie do katalogu tymczasowego: `obserwuj_profil` dopisuje
    tam kazdego, kogo zaobserwowal, a to jest plik produkcyjny.
    """
    dziennik = []
    stare = (browser.podlacz_sie, browser.wymagaj_sesji, browser.dopisz_wynik,
             browser.naprawde_wyslac, browser.zapisz_w_dzienniku,
             browser.OBSERWOWANI)
    browser.podlacz_sie = lambda: (Przegladarka(strona), Przegladarka(strona),
                                   Przegladarka(strona))
    browser.wymagaj_sesji = lambda: None
    browser.naprawde_wyslac = lambda w, co: w
    browser.OBSERWOWANI = (pathlib.Path(tempfile.mkdtemp())
                           / "kogo_obserwujemy.json")
    browser.dopisz_wynik = lambda rodzaj, wynik, **szcz: dziennik.append(
        {"rodzaj": rodzaj,
         "udane": bool(wynik.get("wyslane") or wynik.get("zrobione")),
         "powod": wynik.get("blad") or wynik.get("powod") or "", **szcz})
    browser.zapisz_w_dzienniku = lambda rodzaj, **szcz: dziennik.append(
        {"rodzaj": rodzaj, "powod": "", **szcz})
    buf = io.StringIO()
    stare_out = sys.stdout
    sys.stdout = buf
    try:
        wynik = (funkcja or browser.obserwuj_profil)("ktos", wyslij=wyslij)
    finally:
        sys.stdout = stare_out
        (browser.podlacz_sie, browser.wymagaj_sesji, browser.dopisz_wynik,
         browser.naprawde_wyslac, browser.zapisz_w_dzienniku,
         browser.OBSERWOWANI) = stare
    return wynik, dziennik, buf.getvalue()


print("=== 1. PROFIL NIEOBSERWOWANY, MENU PO ANGIELSKU ===")
s = Strona(MENU_EN_WOLNY, MENU_EN_OBSERWOWANY)
w, dz, out = uruchom(s)
print("    klikniete: %s" % s.klikniete)
sprawdz("kolko „...” zostalo otwarte",
        "Profile actions" in s.klikniete, s.klikniete)
sprawdz("klikneta zostala pozycja „Follow”",
        "Follow" in s.klikniete, s.klikniete)
sprawdz("i NIC poza kolkiem i „Follow”",
        [k for k in s.klikniete if k not in ("Profile actions", "Follow")] == [],
        s.klikniete)
sprawdz("„Mute”/„Block”/„Report” nietkniete",
        not ({"Mute", "Block", "Report"} & set(s.klikniete)), s.klikniete)
sprawdz("wynik: zrobione", w["zrobione"] is True, w)
sprawdz("wynik: POTWIERDZONE odczytem menu, nie samym klknieciem",
        w["potwierdzone"] is True, w)
sprawdz("profil naprawde przeszedl w stan obserwowany", s.obserwowany is True)
sprawdz("dziennik ma jeden wpis i jest udany",
        len(dz) == 1 and dz[0]["udane"] is True, dz)


print()
print("=== 2. TO SAMO MENU PO POLSKU ===")
# Jezyk jest wlasnoscia przegladarki, nie konta: serwer widzi angielski,
# wlasciciel polski, a chodzi po TYM SAMYM koncie.
s = Strona(MENU_PL_WOLNY, MENU_PL_OBSERWOWANY,
           etykieta_kolka="Działania w profilu")
w, dz, out = uruchom(s)
print("    klikniete: %s" % s.klikniete)
sprawdz("kolko po polsku tez zostaje znalezione",
        "Działania w profilu" in s.klikniete, s.klikniete)
sprawdz("klikneta zostala pozycja „Obserwuj”",
        "Obserwuj" in s.klikniete, s.klikniete)
sprawdz("wynik: zrobione i potwierdzone",
        w["zrobione"] is True and w["potwierdzone"] is True, w)
sprawdz("dziennik udany", len(dz) == 1 and dz[0]["udane"] is True, dz)


print()
print("=== 3. PROFIL JUZ OBSERWOWANY — NIE WOLNO KLIKNAC NICZEGO ===")
# Najwazniejszy scenariusz w tym pliku. „Unfollow" zawiera w sobie „Follow",
# wiec dopasowanie po fragmencie ODOBSERWOWALOBY kogos w bloku, ktory ma
# obserwowac. Sprawdzamy oba menu obserwowane ze zmierzonych: 7-pozycyjne
# (@autor1) i 8-pozycyjne (@publikacja3).
for nazwa, menu in (("7 pozycji, @autor1", MENU_EN_OBSERWOWANY),
                    ("8 pozycji, @publikacja3", MENU_EN_OBSERWOWANY_8),
                    ("po polsku, @autor1", MENU_PL_OBSERWOWANY)):
    etykieta = ("Działania w profilu" if "polsku" in nazwa
                else "Profile actions")
    s = Strona([], menu, obserwowany=True, etykieta_kolka=etykieta)
    w, dz, out = uruchom(s)
    print("    [%s] klikniete: %s" % (nazwa, s.klikniete))
    sprawdz("[%s] NIE klikniete nic poza kolkiem" % nazwa,
            [k for k in s.klikniete if k != etykieta] == [], s.klikniete)
    sprawdz("[%s] nadal obserwowany (nikt nie zostal odobserwowany)" % nazwa,
            s.obserwowany is True)
    sprawdz("[%s] wynik mowi wprost: juz obserwowany" % nazwa,
            w["juz_obserwowany"] is True and w["zrobione"] is False, w)
    # ZAPIS JEST OSOBNYM RODZAJEM, NIE PORAZKA. Do 1 wrzesnia szlo to do
    # dziennika jako nieudana `obserwacja` — czyli tak samo, jak wygladalo
    # zniknieciecie przycisku, ktore kosztowalo dziewiec dni. Pelny pomiar
    # tego, co widzi z tego licznik, stoi w `test_pula_obserwacji.py`.
    sprawdz("[%s] slad w dzienniku istnieje i niesie powod" % nazwa,
            len(dz) == 1 and "juz obserwujemy" in dz[0]["powod"], dz)
    sprawdz("[%s] i NIE jest porazka obserwacji" % nazwa,
            dz[0]["rodzaj"] == "obserwacja_pominieta"
            and dz[0]["udane"] is True, dz)


print()
print("=== 4. MENU W JEZYKU, KTOREGO NIE ZMIERZYLEM ===")
s = Strona(MENU_OBCY, MENU_OBCY)
w, dz, out = uruchom(s)
print("    klikniete: %s" % s.klikniete)
sprawdz("nie klikniete nic poza kolkiem",
        [k for k in s.klikniete if k != "Profile actions"] == [], s.klikniete)
sprawdz("w szczegolnosci nie „Blockieren” ani „Melden”",
        not ({"Blockieren", "Melden", "Stummschalten"} & set(s.klikniete)),
        s.klikniete)
sprawdz("nie klikneta zostala tez „Abonnieren” (subskrypcja to co innego)",
        "Abonnieren" not in s.klikniete, s.klikniete)
sprawdz("wynik: nieudany, z powodem wymieniajacym, co bylo w menu",
        w["zrobione"] is False and "Stummschalten" in (w["blad"] or ""), w)
sprawdz("PORAZKA ZOSTAWIA SLAD — to ta dziura, przez ktora dziewiec dni"
        " zer wygladalo na blok, ktory sie nie odbywa",
        len(dz) == 1 and dz[0]["udane"] is False, dz)


print()
print("=== 5. BRAK KOLKA „...” W OGOLE ===")
s = Strona(MENU_EN_WOLNY, MENU_EN_OBSERWOWANY, jest_kolko=False)
w, dz, out = uruchom(s)
sprawdz("nie klikniete nic", s.klikniete == [], s.klikniete)
sprawdz("wynik nieudany, z powodem", w["zrobione"] is False and w["blad"], w)
sprawdz("i slad w dzienniku", len(dz) == 1 and dz[0]["udane"] is False, dz)


print()
print("=== 6. TRYB SPRAWDZENIA (wyslij=False) NIE KLIKA POZYCJI ===")
s = Strona(MENU_EN_WOLNY, MENU_EN_OBSERWOWANY)
w, dz, out = uruchom(s, wyslij=False)
print("    klikniete: %s" % s.klikniete)
sprawdz("kolko owszem — menu trzeba otworzyc, zeby cokolwiek zobaczyc",
        s.klikniete == ["Profile actions"], s.klikniete)
sprawdz("ale „Follow” NIE", "Follow" not in s.klikniete, s.klikniete)
sprawdz("profil nietkniety", s.obserwowany is False)
sprawdz("i zadnego wpisu w dzienniku", dz == [], dz)


print()
print("=== 7. KLIK BEZ SKUTKU: MENU NADAL PROPONUJE OBSERWOWANIE ===")
# Ta cala sesja to naprawianie miejsc, gdzie klikniecie zapisywalo sie jako
# sukces bez sprawdzenia. Atrapa, ktora klikniecie POCHLANIA (przycisk sie
# nie przestawia), musi dac twarde „nie udalo sie".


class StronaGluchaNaKlik(Strona):
    def pozycje(self):
        return self.menu_wolny          # zawsze „Follow", cokolwiek klikniemy


s = StronaGluchaNaKlik(MENU_EN_WOLNY, MENU_EN_OBSERWOWANY)
w, dz, out = uruchom(s)
print("    klikniete: %s  potwierdzone=%r" % (s.klikniete, w["potwierdzone"]))
sprawdz("„Follow” zostalo klikniete", "Follow" in s.klikniete, s.klikniete)
sprawdz("ale potwierdzenie mowi FALSE, nie True",
        w["potwierdzone"] is False, w)
sprawdz("wiec wynik jest NIEUDANY mimo klikniecia",
        w["zrobione"] is False, w)
sprawdz("i dziennik zapisuje porazke, a nie sukces",
        len(dz) == 1 and dz[0]["udane"] is False, dz)


print()
print("=== 8. MENU NIE ODPOWIADA PO KLIKNIECIU: NIEPEWNOSC NA KORZYSC ===")
# `potwierdz_obserwacje` oddaje None, gdy menu nie ma ANI pozycji obserwowania,
# ANI odobserwowania. Prog jest niesymetryczny swiadomie — falszywe „nie udalo
# sie" moze kosztowac zaplanowana obserwacje z dnia, w ktorym przydzial wynosi
# jeden. Przy 10-16/mies plan to ~0,43 na dobe, czyli obserwacja mniej wiecej
# co drugi dzien; falszywe „udalo sie" kosztuje jeden slot. None ma jednak byc
# WIDOCZNE w dzienniku, a nie zniknac w „udane".


class StronaNiemaPoKliku(Strona):
    def pozycje(self):
        return self.menu_wolny if not self.obserwowany else ["Copy link", "Share"]


s = StronaNiemaPoKliku(MENU_EN_WOLNY, [])
w, dz, out = uruchom(s)
print("    potwierdzone=%r  zrobione=%r" % (w["potwierdzone"], w["zrobione"]))
sprawdz("potwierdzenie oddaje None, nie False", w["potwierdzone"] is None, w)
sprawdz("niepewnosc liczy sie NA KORZYSC obserwacji",
        w["zrobione"] is True, w)
sprawdz("ale dziennik niesie potwierdzone=None, wiec widac roznice",
        len(dz) == 1 and dz[0]["potwierdzone"] is None, dz)


print()
print("=== 9. KONTRDOWOD 1: STARA DROGA NA TEJ SAMEJ ATRAPIE ===")
# `_klik_na_profilu` nadal zyje w pliku (obsluguje subskrypcje) i JEST
# doslownie przedpoprawkowa implementacja `obserwuj_profil` sprzed 64d881a:
#     return _klik_na_profilu(handle, ("Follow", "Obserwuj"), "obserwacja", ...)
# Nie trzeba jej odtwarzac latka — wystarczy zawolac.
s = Strona(MENU_EN_WOLNY, MENU_EN_OBSERWOWANY)
stara = lambda h, wyslij=False: browser._klik_na_profilu(  # noqa: E731
    h, ("Follow", "Obserwuj"), "obserwacja", wyslij)
w_st, dz_st, out_st = uruchom(s, funkcja=stara)
print("    STARA DROGA: klikniete=%s zrobione=%r blad=%r"
      % (s.klikniete, w_st["zrobione"], w_st["blad"]))
sprawdz("KONTRDOWOD: stara droga NIE klikala niczego",
        s.klikniete == [], s.klikniete)
sprawdz("KONTRDOWOD: i oddawala „nie ma przycisku”",
        w_st["zrobione"] is False and "nie ma przycisku" in (w_st["blad"] or ""),
        w_st)
sprawdz("KONTRDOWOD: profil zostawal nieobserwowany", s.obserwowany is False)
# A nowa droga na TEJ SAMEJ atrapie obserwuje — czyli roznice robi poprawka,
# a nie atrapa.
s2 = Strona(MENU_EN_WOLNY, MENU_EN_OBSERWOWANY)
w_nowa, _, _ = uruchom(s2)
sprawdz("a nowa droga na tej samej atrapie obserwuje",
        w_nowa["zrobione"] is True and s2.obserwowany is True, w_nowa)


print()
print("=== 10. HIPOTEZA PROJEKTOWA: DOPASOWANIE PO FRAGMENCIE ===")
# CZYM TA SEKCJA NIE JEST — bo do 1 wrzesnia 2026 udawala co innego. Nazywala
# sie „KONTRDOWOD 2", meldowala „3 na 3 ofiary" i brzmiala jak zmierzona
# regresja, a porownywala DWIE FUNKCJE NAPISANE CZTERY LINIE WYZEJ W SAMYM
# TESCIE. Czesc „przez ZACHOWANIE" klikala w wezel wlasnej atrapy i sprawdzala,
# ze atrapa przestawila swoje wlasne pole. Kod produkcyjny nie wykonywal sie
# tam ani razu — a liczba „3 na 3" sugerowala pomiar.
#
# I NIE MA CZEGO ODTWARZAC: wyboru po fragmencie NIGDY w produkcji nie bylo.
# Droga sprzed poprawki (`_klik_na_profilu`, nadal w pliku, patrz sekcja 9)
# pyta Playwrighta z `exact=True`, a droga dzisiejsza czyta teksty sama
# i porownuje przez `==`. Zagrozenie jest PROJEKTOWE, nie historyczne:
# `exact=False` to domyslka Playwrighta, a „Unfollow" zawiera w sobie „Follow",
# wiec pierwsza wersja nowego kodu latwo moglaby ja odziedziczyc. Wybor przez
# rownosc jest poprawny i ta sekcja niczego w nim nie zmienia.
#
# Dlatego stoja tu obok siebie dwie rozne rzeczy i kazda jest nazwana:
#   PRODUKCJA — `obserwuj_profil` puszczone na zmierzonych menu profili
#               OBSERWOWANYCH; liczy sie to, co odnotowala atrapa.
#   HIPOTEZA  — regula wyboru napisana w tym tescie, na tych samych menu;
#               mowi, co by sie stalo, GDYBY ktos ja tak napisal.
def wybierz_fragmentem(pozycje):
    """HIPOTETYCZNA regula. Nie ma jej w `browser.py` i nigdy nie bylo."""
    return next((i for i, t in enumerate(pozycje)
                 if any(n.lower() in t.lower()
                        for n in browser.OBSERWUJ_POZYCJE)), None)


for nazwa, menu, etykieta, hipoteza_trafia in (
        ("@autor1", MENU_EN_OBSERWOWANY, "Profile actions", True),
        ("@publikacja3", MENU_EN_OBSERWOWANY_8, "Profile actions", True),
        ("@publikacja1", ["Copy link", "Share", "Send message", "Unfollow",
                           "Mute", "Block", "Report"], "Profile actions", True),
        # PO POLSKU HIPOTETYCZNA REGULA NIE TRAFIA W NIC i to jest ciekawsze
        # niz gdyby trafiala: „Przestań obserwować" nie zawiera w sobie slowa
        # „Obserwuj", wiec cale zagrozenie jest ZALEZNE OD JEZYKA INTERFEJSU —
        # a jezyk jest wlasnoscia przegladarki, nie konta (patrz naglowek).
        # Wybor przez rownosc nie zalezy od niczego takiego i dlatego zostaje.
        ("@autor1 po polsku", MENU_PL_OBSERWOWANY, "Działania w profilu",
         False)):
    # PRODUKCJA: prawdziwa funkcja, prawdziwa atrapa strony.
    s = Strona([], menu, obserwowany=True, etykieta_kolka=etykieta)
    w, dz, out = uruchom(s)
    i_frag = wybierz_fragmentem(menu)
    trafiona = menu[i_frag] if i_frag is not None else None
    print("    %-24s PRODUKCJA klikneta=%s   HIPOTEZA wskazuje -> %r"
          % (nazwa, [k for k in s.klikniete if k != etykieta], trafiona))
    sprawdz("[%s] PRODUKCJA nie klika ANI JEDNEJ pozycji menu" % nazwa,
            [k for k in s.klikniete if k != etykieta] == [], s.klikniete)
    sprawdz("[%s] PRODUKCJA zostawia profil obserwowanym" % nazwa,
            s.obserwowany is True and w["juz_obserwowany"] is True, w)
    sprawdz("[%s] HIPOTEZA: %s" % (nazwa, "trafilaby w pozycje odobserwowujaca"
                                   if hipoteza_trafia
                                   else "nie trafia w nic — zagrozenie jest"
                                        " zalezne od jezyka"),
            (trafiona in browser.JUZ_OBSERWUJEMY_POZYCJE) is hipoteza_trafia,
            trafiona)


print()
print("=== 11. WYCOFANIE ZDJETE WE WSZYSTKICH TRZECH MIEJSCACH ===")
sprawdz("config.FOLLOW_MIESIECZNIE nie jest juz (0, 0)",
        config.FOLLOW_MIESIECZNIE != (0, 0), config.FOLLOW_MIESIECZNIE)
sprawdz("norma.NIEWYKONALNE nie tlumaczy juz zera obserwacji",
        "obserwacja" not in norma.NIEWYKONALNE, norma.NIEWYKONALNE)
sprawdz("norma.normy liczy obserwacje z tej samej stalej",
        abs(config.normy_dzienne()["obserwacja"]
            - sum(config.FOLLOW_MIESIECZNIE) / 2 / 30) < 1e-9,
        config.normy_dzienne()["obserwacja"])

# Budzet dnia: mierzymy ZACHOWANIE `stages.budzet_dnia`, nie tresc config.
#
# PYTANIE MUSIALO ZMIENIC SKALE 1 wrzesnia 2026, i to nie jest oslabienie
# testu. Stalo tu „budzet obserwacji jest DODATNI" liczone z JEDNEJ doby, bo
# przy (30,44) kazdy dzien mial co najmniej jedna obserwacje: randint(30,44)/30
# to [1,00; 1,47], wiec `int()` dawal 1 dla kazdego ziarna. Widelki zeszly do
# (10,16) — decyzja wlasciciela, uzasadnienie i caly rachunek stoja przy
# `config.FOLLOW_MIESIECZNIE` — czyli [0,33; 0,53], gdzie ZERO W DANEJ DOBIE
# JEST POPRAWNYM WYNIKIEM, a nie wycofaniem zdolnosci. Asercja o jednej dobie
# mierzylaby od tej pory kalendarz.
#
# Skala, na ktorej to pytanie nadal cos znaczy, to MIESIAC — bo taka jest
# stala. Sumujemy wiec 30 kolejnych dob przez PRAWDZIWE `budzet_dnia`,
# podstawiajac date (ziarno bierze sie z niej), i pytamy o to samo co
# przedtem: czy blok ma cokolwiek do zrobienia.
zapisy = []
stare_zapisz = stages._zapisz_budzet_dnia
stare_wiek = stages._wiek_konta_w_dniach
stages._zapisz_budzet_dnia = lambda *a, **k: zapisy.append(a)


def _miesiac_budzetow():
    """Suma 30 kolejnych dob z prawdziwego `budzet_dnia`. Data USTALONA.

    `budzet_dnia` czyta date przez `from datetime import datetime` WEWNATRZ
    funkcji, wiec siega do `sys.modules` — podmieniamy wiec caly modul na czas
    wywolania. Dzieki temu test nie zalezy od dnia, w ktorym go uruchomiono.
    """
    import datetime as _dt
    import types as _types

    prawdziwy = sys.modules["datetime"]
    fake = _types.ModuleType("datetime")

    class _FakeDT(_dt.datetime):
        _teraz = None

        @classmethod
        def now(cls, tz=None):
            return cls._teraz

    fake.datetime, fake.timezone, fake.timedelta = (
        _FakeDT, _dt.timezone, _dt.timedelta)
    suma = {"follow": 0, "subskrypcje": 0}
    baza = _dt.datetime(2026, 9, 1, 12, 0, tzinfo=_dt.timezone.utc)
    for i in range(30):
        _FakeDT._teraz = baza + _dt.timedelta(days=i)
        sys.modules["datetime"] = fake
        try:
            buf = io.StringIO()
            so, sys.stdout = sys.stdout, buf
            try:
                b = stages.budzet_dnia(None)
            finally:
                sys.stdout = so
        finally:
            sys.modules["datetime"] = prawdziwy
        suma["follow"] += b["follow"]
        suma["subskrypcje"] += b["subskrypcje"]
    return suma


try:
    for opis, wiek in (("konto dojrzale", 999), ("rozbieg", 1)):
        stages._wiek_konta_w_dniach = lambda conn, _w=wiek: _w
        m = _miesiac_budzetow()
        print("    [%s] miesiac: follow=%d subskrypcje=%d"
              % (opis, m["follow"], m["subskrypcje"]))
        sprawdz("[%s] miesieczny budzet obserwacji jest DODATNI" % opis,
                m["follow"] >= 1, m)
        # NOWA ASERCJA, KTOREJ TU BYC NIE MOGLO: od 1 wrzesnia subskrypcje maja
        # byc LICZNIEJSZE od obserwacji, bo to one konwertuja (11,5% wobec
        # 3,4%). Przedtem stala mowila odwrotnie i nikt tego nie mierzyl.
        sprawdz("[%s] subskrypcji jest wiecej niz obserwacji" % opis,
                m["subskrypcje"] > m["follow"], m)

        # KONTRDOWOD 3: te sama funkcja z wycofana stala.
        stara_stala = config.FOLLOW_MIESIECZNIE
        config.FOLLOW_MIESIECZNIE = (0, 0)
        try:
            m0 = _miesiac_budzetow()
        finally:
            config.FOLLOW_MIESIECZNIE = stara_stala
        print("    [%s] KONTRDOWOD (0,0): follow w miesiacu=%d"
              % (opis, m0["follow"]))
        sprawdz("[%s] KONTRDOWOD: przy (0, 0) CALY MIESIAC byl ZEROWY" % opis,
                m0["follow"] == 0, m0)
finally:
    stages._zapisz_budzet_dnia = stare_zapisz
    stages._wiek_konta_w_dniach = stare_wiek
sprawdz("i nic nie poszlo do pliku budzetow (atrapa przechwycila zapis)",
        len(zapisy) == 120, len(zapisy))


print()
print("=== 12. NORMA PRZESTAJE UCISZAC OBSERWACJE ===")
# Zero z wyjasnieniem przestaje wygladac na problem. Sprawdzamy ZACHOWANIE
# `_znak` i bramki alarmu, a nie tresc slownika.
sprawdz("NIEWYKONALNE jest puste — zadna pozycja nie ma recznej oslony",
        norma.NIEWYKONALNE == {}, norma.NIEWYKONALNE)
# KTORA BRAMKA ALARMU LAPIE MARTWY BLOK — SPRAWDZONE PONOWNIE 1 WRZESNIA 2026.
#
# Stalo tu, ze tydzien bez obserwacji przekracza `MIN_BRAKOW_W_OKNIE_DO_ALARMU`
# (4). Przy planie 1,2 na dobe tak bylo: 8,4 braku. Po obnizeniu widelek do
# (10,16) plan to 0,43 na dobe, czyli 3,03 braku na tydzien — PONIZEJ tej
# bramki. Gdyby to byla jedyna droga, obnizenie widelek uciszyloby alarm,
# ktory kosztowal dziewiec dni.
#
# NIE JEST JEDYNA i to trzeba mierzyc, a nie zakladac. `norma.py` budzi z DWOCH
# powodow (linie „martwa = ..."), a drugi z nich nie patrzy na liczbe brakow:
# ZERO wykonanych przy planie w oknie >= `MIN_PLAN_W_OKNIE_DO_ALARMU_O_ZERZE`
# (1) to martwy blok niezaleznie od dlugosci okna. Plan tygodniowy 3,03 mija
# ten prog trzykrotnie, wiec tydzien bez ani jednej obserwacji nadal budzi.
tydzien_obserwacji = config.normy_dzienne()["obserwacja"] * 7
print("    plan obserwacji na 7 dni: %.2f  (prog zera: %d, prog brakow: %d)"
      % (tydzien_obserwacji, norma.MIN_PLAN_W_OKNIE_DO_ALARMU_O_ZERZE,
         norma.MIN_BRAKOW_W_OKNIE_DO_ALARMU))
sprawdz("tydzien bez ani jednej obserwacji nadal budzi alarm — bramka ZERA",
        tydzien_obserwacji >= norma.MIN_PLAN_W_OKNIE_DO_ALARMU_O_ZERZE,
        tydzien_obserwacji)
sprawdz("to samo dla subskrypcji, ktorych jest teraz wiecej",
        config.normy_dzienne()["subskrypcja"] * 7
        >= norma.MIN_PLAN_W_OKNIE_DO_ALARMU_O_ZERZE,
        config.normy_dzienne()["subskrypcja"] * 7)


print()
print("=== 13. SUBSKRYPCJA ZOSTALA PRZY SWOJEJ DRODZE ===")
# Rozdzielenie obserwacji i subskrypcji bylo poprzednia poprawka i nie wolno
# go cofnac przy okazji tej. Subskrypcja nadal chodzi przyciskiem na wierzchu.
s = Strona(MENU_EN_WOLNY, MENU_EN_OBSERWOWANY)
w_sub, dz_sub, _ = uruchom(s, funkcja=lambda h, wyslij=False:
                           browser.zasubskrybuj(h, wyslij))
print("    klikniete: %s" % s.klikniete)
sprawdz("subskrypcja klika „Subscribe” na wierzchu",
        s.klikniete == ["Subscribe"], s.klikniete)
sprawdz("i nie otwiera menu profilu",
        "Profile actions" not in s.klikniete, s.klikniete)
sprawdz("wpis w dzienniku ma rodzaj „subskrypcja”, nie „obserwacja”",
        len(dz_sub) == 1 and dz_sub[0]["rodzaj"] == "subskrypcja", dz_sub)


print()
print("=== PRODUKCJA: bez zmian ===")
zle = 0
for p in PILNOWANE:
    t = odcisk(p)
    ok = t == PRZED[str(p)]
    zle += 0 if ok else 1
    print("  %-28s %s" % (pathlib.Path(p).name, "bez zmian" if ok else "ZMIENIONA"))

print()
print("=== WYNIK: %d zdanych, %d oblanych%s ===" %
      (zdane, oblane, ", PRODUKCJA RUSZONA" if zle else ""))
sys.exit(1 if (oblane or zle) else 0)
