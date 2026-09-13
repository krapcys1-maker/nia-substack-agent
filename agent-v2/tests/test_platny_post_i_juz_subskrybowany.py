# -*- coding: utf-8 -*-
"""Post za paywallem nie dostaje komentarza, a profil juz subskrybowany nie jest porazka.

## Pomiar, ktory to wywolal

Produkcja, 13 wrzesnia 2026, przebieg 78, sprawdzone potem odczytem z API:

1. Post jednej z publikacji z puli celow — zapora
   `mozna_komentowac` przepuscila, bo publikacja ma
   `write_comment_permissions: subscribers`. Sam POST mial
   `audience: only_paid`. Model napisal komentarz, przebieg odczekal
   kwadrans i dopiero wtedy: „nie ma pola komentarza pod tym postem".
2. Profil, ktorego subskrypcja weszla 11 wrzesnia, ale zapisala sie jako
   porazka (przed potwierdzaniem zniknieciem przycisku) — ani „Subscribe",
   ani zadnego napisu „juz subskrybujesz", wiec wpis „nie ma przycisku
   subskrypcja" jako porazka. API profilu oddawalo `isSubscribed: true`.
   Porazka nie zamyka profilu, wiec wracal co przebieg: kilkanascie minut
   przerwy i kolejna porazka dla hamulca.

BEZ PYTESTA, bez sieci, bez przegladarki. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_platny_post_i_juz_subskrybowany.py
"""
import json
import pathlib
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


klikniete = []
zapytania = []


class Przycisk:
    def __init__(self, nazwa, jest):
        self.nazwa, self.jest = nazwa, jest
        self.first = self

    def count(self):
        return 1 if self.jest else 0

    def is_visible(self):
        return self.jest

    def click(self, timeout=None):
        klikniete.append(self.nazwa)


class Strona:
    def __init__(self, dostepne=()):
        self.dostepne = set(dostepne)

    def goto(self, *a, **k):
        pass

    def wait_for_timeout(self, ms):
        pass

    def get_by_role(self, rola, name=None, exact=None):
        return Przycisk(name, name in self.dostepne)

    def get_by_text(self, tekst, exact=None):
        return Przycisk(tekst, tekst in self.dostepne)

    def close(self):
        pass


class Kontekst:
    def __init__(self, strona):
        self.strona = strona

    def new_page(self):
        return self.strona

    def close(self):
        pass

    def stop(self):
        pass


ORYG = (browser.podlacz_sie, browser.wymagaj_sesji, browser.api_json, browser.DZIENNIK,
        browser.naprawde_wyslac, browser.PLATNE_HOSTY, browser.wymagaj_wlasciwego_konta,
        browser.hosty_gdzie_komentarz_nie_wchodzi, config.SUBSKRYPCJE_MAX_ODBIORCOW)


def swiat(odpowiedz_api, przyciski=(), sufit=None):
    """`odpowiedz_api` — slownik oddawany przez API albo wyjatek do rzucenia."""
    klikniete.clear()
    zapytania.clear()
    s = Strona(przyciski)
    browser.wymagaj_sesji = lambda: None
    browser.wymagaj_wlasciwego_konta = lambda page: None
    browser.podlacz_sie = lambda: (Kontekst(s), Kontekst(s), Kontekst(s))
    browser.naprawde_wyslac = lambda wyslij, co: wyslij
    browser.hosty_gdzie_komentarz_nie_wchodzi = lambda: set()
    katalog = pathlib.Path(tempfile.mkdtemp())
    browser.DZIENNIK = katalog / "d.jsonl"
    browser.PLATNE_HOSTY = katalog / "platne.json"
    config.SUBSKRYPCJE_MAX_ODBIORCOW = sufit

    def api(page, sciezka, baza=None):
        zapytania.append(sciezka)
        if isinstance(odpowiedz_api, Exception):
            raise odpowiedz_api
        return odpowiedz_api
    browser.api_json = api


def wpisy():
    if not browser.DZIENNIK.exists():
        return []
    return [json.loads(l) for l in browser.DZIENNIK.read_text(encoding="utf-8")
            .splitlines() if l.strip()]


URL = "https://publikacja-a.example/p/tekst"
HOST = "publikacja-a.example"

try:
    print("=== 1. POST ZA PAYWALLEM: ODMOWA PRZED PISANIEM ===")
    swiat({"id": 1, "write_comment_permissions": "subscribers", "audience": "only_paid"})
    sprawdz("post only_paid przy publikacji otwartej na komentarze: nie piszemy",
            browser.mozna_komentowac(URL) is False)
    sprawdz("host NIE zapamietany jako platny (nastepny post moze byc darmowy)",
            HOST not in browser.hosty_tylko_dla_placacych(),
            browser.hosty_tylko_dla_placacych())
    swiat({"id": 1, "write_comment_permissions": "everyone", "audience": "founding"})
    sprawdz("post dla zalozycieli: tez nie", browser.mozna_komentowac(URL) is False)
    # KONTRDOWODY — zapora nie moze zamknac tego, co otwarte.
    swiat({"id": 1, "write_comment_permissions": "subscribers", "audience": "everyone"})
    sprawdz("post dla wszystkich: piszemy", browser.mozna_komentowac(URL) is True)
    swiat({"id": 1, "write_comment_permissions": "everyone"})
    sprawdz("brak pola audience: przy watpliwosci TAK", browser.mozna_komentowac(URL) is True)
    swiat({"id": 1, "write_comment_permissions": "only_paid", "audience": "everyone"})
    sprawdz("platna PUBLIKACJA nadal odmowa", browser.mozna_komentowac(URL) is False)
    sprawdz("i nadal zapamietana (to ustawienie publikacji)",
            HOST in browser.hosty_tylko_dla_placacych(), browser.hosty_tylko_dla_placacych())

    print()
    print("=== 2. BEZ PRZYCISKU, A API MOWI „SUBSKRYBUJESZ\" ===")
    swiat({"isSubscribed": True}, przyciski={"Message"})
    w = browser.zasubskrybuj("autor-b", wyslij=True)
    sprawdz("wynik: juz nasza subskrypcja, pominiete",
            w.get("juz_subskrybowany") and w.get("pominiete"), w)
    sprawdz("bez bledu", not w.get("blad"), w.get("blad"))
    sprawdz("niczego nie kliknieto", klikniete == [], klikniete)
    d = wpisy()
    sprawdz("w dzienniku jedno pominiecie z powodem „juz subskrybowany\"",
            len(d) == 1 and d[0].get("rodzaj") == "subskrypcja_pominieta"
            and d[0].get("powod") == browser.POWOD_JUZ_SUBSKRYBOWANY, d)

    swiat({"isSubscribed": True}, przyciski={"Message"})
    browser.zasubskrybuj("autor-b", wyslij=False)
    sprawdz("proba sucha nie pisze do dziennika", wpisy() == [], wpisy())

    # SUFIT ODBIORCOW WLACZONY: profil jest juz pobrany, drugiego zapytania nie ma.
    swiat({"isSubscribed": True, "subscriberCountNumber": 268, "followerCount": 712},
          przyciski={"Message"}, sufit=10_000)
    w = browser.zasubskrybuj("autor-b", wyslij=True)
    sprawdz("z sufitem: tez rozpoznane jako nasza", w.get("juz_subskrybowany"), w)
    sprawdz("i API zapytane RAZ (profil z sufitu uzyty ponownie)",
            len(zapytania) == 1, zapytania)

    print()
    print("=== 3. KONTRDOWODY: PRAWDZIWY BRAK PRZYCISKU ZOSTAJE PORAZKA ===")
    swiat({"isSubscribed": False}, przyciski={"Message"})
    w = browser.zasubskrybuj("ktos", wyslij=True)
    sprawdz("API mowi „nie subskrybujesz\": blad zostaje",
            w.get("blad", "").startswith("nie ma przycisku"), w)
    d = wpisy()
    sprawdz("i porazka w dzienniku",
            len(d) == 1 and d[0].get("rodzaj") == "subskrypcja" and not d[0].get("udane"), d)

    swiat(RuntimeError("api padlo"), przyciski={"Message"})
    w = browser.zasubskrybuj("ktos", wyslij=True)
    sprawdz("API padlo: nie wywraca sie, zostaje „nie ma przycisku\"",
            w.get("blad", "").startswith("nie ma przycisku"), w)

    swiat({"isSubscribed": True}, przyciski={"Subscribe", "Message"})
    w = browser.zasubskrybuj("nowy", wyslij=True)
    sprawdz("zwykla droga z przyciskiem: klikniecie jak dotad",
            klikniete[:1] == ["Subscribe"], klikniete)
    sprawdz("i bez dodatkowego zapytania do API", zapytania == [], zapytania)
finally:
    (browser.podlacz_sie, browser.wymagaj_sesji, browser.api_json, browser.DZIENNIK,
     browser.naprawde_wyslac, browser.PLATNE_HOSTY, browser.wymagaj_wlasciwego_konta,
     browser.hosty_gdzie_komentarz_nie_wchodzi, config.SUBSKRYPCJE_MAX_ODBIORCOW) = ORYG

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
