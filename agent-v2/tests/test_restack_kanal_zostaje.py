# -*- coding: utf-8 -*-
"""Po restacku kanal zostaje pod petla — numer notki czytamy w osobnej karcie.

## Pomiar, ktory to rozstrzygnal

12 wrzesnia 2026, oba przebiegi dnia na produkcji:

    notek w kanale do rozwazenia: 15
    RESTACK u Kai Marek ...
    podane dalej 1/3
    (nie ma juz nowych notek do rozwazenia)

Pietnascie notek, budzet trzech, jeden restack. Tak samo 7-10 wrzesnia:
„dokladnie jeden na przebieg".

## Przyczyna

Po kliknieciu „Post" petla pyta o numer naszej nowej notki:
`numer_naszej_notki(page, ...)`. Ta funkcja czyta API przez `api_json`,
a `api_json` WCHODZI na adres JSON (`page.goto`), bo z serwera `fetch` wraca
403. Karta, na ktorej stal kanal, pokazywala wiec JSON, a nastepny obrot
petli liczyl zero przyciskow „Restack".

Proba sucha tego nie widzi, bo o numer nie pyta. Istniejacy test petli tez
nie, bo jego atrapa strony nie umie `inner_text`, wiec `numer_naszej_notki`
wywalal sie cicho, zanim cokolwiek przeszedl.

## Co ta atrapa robi inaczej

Strona NAPRAWDE zmienia zawartosc przy `goto`: adres z `/api/` pokazuje JSON
i zero przyciskow, adres kanalu pokazuje notki. JSON jest prawdziwy w ksztalcie,
wiec `numer_naszej_notki` przechodzi cala droge i znajduje numer.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_restack_kanal_zostaje.py
"""
import json
import sys

sys.path.insert(0, "agent-v2")
import browser   # noqa: E402
import config    # noqa: E402

browser.wymagaj_wlasciwego_konta = lambda page: None
config.ZNAKI_NISZY = ()
# ATRAPA ZNAJDUJE NUMER, wiec bez tego restack zapisalby sie do prawdziwej
# pamieci persony operatora. Test ma nie dotykac zadnego pliku z danymi.
config.PERSONA_WLACZONA = False
KANAL = "https://substack.com/"
NASZE_ID = 777

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


class Przycisk:
    def __init__(self, strona, i):
        self.strona, self.i = strona, i

    def is_visible(self):
        return self.strona.na_kanale and self.i < self.strona.widoczne

    def scroll_into_view_if_needed(self, **k):
        pass

    def click(self, **k):
        if not self.is_visible():
            raise RuntimeError("Timeout: przycisku nie ma na stronie")
        self.strona.kliki.append(self.i)


class Pole:
    """`textbox.last`, `menuitem`, `button Post` — wszystko poza kanalem."""

    def __init__(self, strona):
        self.strona = strona

    @property
    def last(self):
        return self

    def click(self, **k):
        pass

    def type(self, tekst, **k):
        self.strona.wpisane.append(tekst)
        self.strona.ostatni_tekst = tekst

    def is_visible(self):
        return True

    def count(self):
        return 1


class Przyciski:
    def __init__(self, strona):
        self.strona = strona

    def count(self):
        return self.strona.widoczne if self.strona.na_kanale else 0

    def nth(self, i):
        return Przycisk(self.strona, i)


class Strona:
    """Jedna karta przegladarki. `goto` zmienia to, co na niej jest."""

    def __init__(self, swiat, notek_na_start, notek_max):
        self.swiat = swiat
        self.adres = "about:blank"
        self.historia = []
        self.na_kanale = False
        self.start, self.max = notek_na_start, notek_max
        self.widoczne = 0
        self.kliki, self.wpisane = [], []
        self.ostatni_tekst = ""
        self.keyboard = self
        self.mouse = self
        self.zamknieta = False

    # --- nawigacja ---
    def goto(self, adres, **k):
        self.adres = adres
        self.historia.append(adres)
        self.swiat.wejscia.append(adres)
        self.na_kanale = "/api/" not in adres
        self.widoczne = self.start if self.na_kanale else 0

    def inner_text(self, selektor):
        if "/public_profile" in self.adres:
            return json.dumps({"id": NASZE_ID})
        if "/reader/feed/profile/" in self.adres:
            return json.dumps({"items": [
                {"comment": {"id": 90000 + n, "body": t}}
                for n, t in enumerate(self.swiat.opublikowane)]})
        return "<html>kanal</html>"

    # --- przewijanie doklada notki, jak na Substacku ---
    def wheel(self, *a, **k):
        if self.na_kanale:
            self.widoczne = min(self.max, self.widoczne + 5)

    def move(self, *a, **k):
        pass

    def evaluate(self, *a, **k):
        return None

    def press(self, *a, **k):
        pass

    def wait_for_timeout(self, ms):
        pass

    def get_by_role(self, rola, name=None, **k):
        if rola == "button" and name == "Restack":
            return Przyciski(self)
        if rola == "button" and name == "Post":
            swiat = self.swiat

            class Wyslij(Pole):
                def click(self_, **kk):
                    swiat.opublikowane.append(self.ostatni_tekst)
            return Wyslij(self)
        return Pole(self)

    def close(self):
        self.zamknieta = True


class Swiat:
    def __init__(self, notek_na_start=15, notek_max=15):
        self.wejscia, self.opublikowane = [], []
        self.karty = []
        self.notek_na_start, self.notek_max = notek_na_start, notek_max

    def new_page(self):
        k = Strona(self, self.notek_na_start, self.notek_max)
        self.karty.append(k)
        return k


class Nic:
    def close(self):
        pass

    def stop(self):
        pass


def przebieg(ile, zgody=99, notek_na_start=15, notek_max=15, podmien_numer=None):
    swiat = Swiat(notek_na_start, notek_max)
    dziennik = []
    oryg = (browser.podlacz_sie, browser.wymagaj_sesji, browser.naprawde_wyslac,
            browser._notka_przy_przycisku, browser._autor_przy_przycisku,
            browser.zapisz_w_dzienniku, browser.kogo_juz_restackowalismy,
            browser.klik_mimo_zaslony, browser.numer_naszej_notki,
            config.ODSTEPY.get("restack"))
    browser.podlacz_sie = lambda: (Nic(), Nic(), swiat)
    browser.wymagaj_sesji = lambda: None
    browser.naprawde_wyslac = lambda w, r: w
    browser._notka_przy_przycisku = lambda p: {
        "tekst": "Cudza notka numer %d o czyms zupelnie innym." % p.i,
        "autor": "Autor %d" % p.i}
    browser._autor_przy_przycisku = lambda p: {"uchwyt": "autor%d" % p.i,
                                               "autor": "Autor %d" % p.i}
    browser.zapisz_w_dzienniku = lambda *a, **k: dziennik.append((a, k))
    browser.kogo_juz_restackowalismy = lambda *a, **k: set()
    browser.klik_mimo_zaslony = lambda przycisk, nazwa, timeout=8000: przycisk.click()
    config.ODSTEPY["restack"] = (0, 0)
    if podmien_numer:
        browser.numer_naszej_notki = podmien_numer(oryg[8], swiat)
    licznik = {"n": 0}

    def decyzja(notka):
        licznik["n"] += 1
        if licznik["n"] <= zgody:
            return {"restack": True, "reason": "warte",
                    "sentence": "Nasze zdanie numer %d." % licznik["n"]}
        return {"restack": False, "sentence": "", "reason": "nic nie wnosi"}

    try:
        wynik = browser.restackuj_w_kanale(ile, decyzja, wyslij=True, url=KANAL)
    finally:
        (browser.podlacz_sie, browser.wymagaj_sesji, browser.naprawde_wyslac,
         browser._notka_przy_przycisku, browser._autor_przy_przycisku,
         browser.zapisz_w_dzienniku, browser.kogo_juz_restackowalismy,
         browser.klik_mimo_zaslony, browser.numer_naszej_notki,
         config.ODSTEPY["restack"]) = oryg
    return wynik, swiat, dziennik


print("=== 1. TRZY RESTACKI Z PIETNASTU NOTEK, NIE JEDEN ===")
w, swiat, dziennik = przebieg(ile=3)
sprawdz("wszystkie trzy podane dalej", w["restackowane"] == 3, w)
sprawdz("i trzy naprawde opublikowane", len(swiat.opublikowane) == 3,
        swiat.opublikowane)
udane = [k for a, k in dziennik if a and a[0] == "restack" and k.get("udane")]
sprawdz("dziennik ma trzy udane wpisy", len(udane) == 3, dziennik)

print()
print("=== 2. NUMER JEST ODCZYTANY — OSOBNA KARTA NAPRAWDE PYTA API ===")
# Kontrdowod na „naprawione przez to, ze numer przestal byc czytany":
# wszystkie trzy wpisy maja numer z kanalu profilu.
numery = [k.get("id") for k in udane]
sprawdz("kazdy restack ma numer", all(numery) and len(numery) == 3, numery)
kanal = swiat.karty[0]
sprawdz("karta kanalu ani razu nie weszla na adres API",
        kanal.historia and not any("/api/" in a for a in kanal.historia),
        kanal.historia)
sprawdz("pytania o API szly innymi kartami",
        any("/api/" in a for k in swiat.karty[1:] for a in k.historia),
        [k.historia for k in swiat.karty])
sprawdz("te karty sa zamkniete", all(k.zamknieta for k in swiat.karty[1:]),
        [k.zamknieta for k in swiat.karty[1:]])
sprawdz("kanal wczytany tylko raz — nic go nie wyrzucilo",
        swiat.wejscia.count(KANAL) == 1, swiat.wejscia)

print()
print("=== 3. KONTRDOWOD: ATRAPA ODTWARZA PRODUKCJE ===")
# Ten sam przebieg, ale numer czytany NA KARCIE KANALU — tak jak bylo od
# 4 do 13 wrzesnia. Gdyby atrapa tego nie lapala, sekcja 1 niczego by nie
# dowodzila. Bez siatki doladowania petla konczy na jednym; z siatka wraca
# na kanal i idzie dalej, wiec liczymy WEJSCIA na kanal.
def na_karcie_kanalu(prawdziwy, swiat):
    return lambda strona, tekst, prob=4: prawdziwy(swiat.karty[0], tekst, prob=prob)


w, swiat, dziennik = przebieg(ile=3, podmien_numer=na_karcie_kanalu)
sprawdz("stara droga wyrzuca kanal ze strony",
        any("/api/" in a for a in swiat.wejscia[1:]), swiat.wejscia)
sprawdz("i petla musi na niego wracac (siatka doladowania dziala)",
        swiat.wejscia.count(KANAL) >= 2, swiat.wejscia)

print()
print("=== 4. KANAL WYCZERPANY: NAJPIERW GLEBIEJ, BEZ NOWEGO WEJSCIA ===")
# Dwanascie odmow na starcie, a przewijanie doklada notek do 30. Petla ma
# przewinac dalej na tej samej stronie, a nie wchodzic od nowa.
w, swiat, dziennik = przebieg(ile=2, zgody=0, notek_na_start=12, notek_max=30)
sprawdz("odmowy przekroczyly pierwszy ekran", w["rozwazone"] > 12, w["rozwazone"])
sprawdz("bez ponownego wejscia na kanal", swiat.wejscia.count(KANAL) == 1,
        swiat.wejscia)

print()
print("=== 5. PUSTY KANAL NIE KRECI SIE W KOLKO ===")
w, swiat, dziennik = przebieg(ile=3, zgody=0, notek_na_start=4, notek_max=4)
sprawdz("nic nie podane dalej", w["restackowane"] == 0, w)
sprawdz("najwyzej dwa ponowne wejscia", swiat.wejscia.count(KANAL) <= 3,
        swiat.wejscia)
sprawdz("kazda notka oceniona raz", w["rozwazone"] == 4, w["rozwazone"])

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
