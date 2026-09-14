# -*- coding: utf-8 -*-
"""Wysylamy przyciskiem „Post", nie „…reply rules" ani „View comments", i nie piszemy tam, gdzie nie wejdzie.

## Pomiar, ktory to wywolal

Dziennik systemowy od 5 do 14 wrzesnia 2026, wynik wysylki wg przycisku,
ktory wybral kod:

    'Post'     78 potwierdzonych,  0 porazek
    'Reply'     0 potwierdzonych,  5 porazek
    'Comment'   0 potwierdzonych,  5 porazek

Uklad zywych stron obejrzany bez wpisywania i bez wysylania:

1. Pod notkami publikacji z zasadami odpowiedzi obok pola stoi przycisk
   „<Publikacja> reply rules". `name="Reply"` bez `exact` trafial w niego,
   a „Reply" stalo w kolejce PRZED „Post" — prawdziwe „Post" bylo obok.
2. Pod postem z `write_comment_permissions: subscribers` pola „Post" nie ma,
   gdy nie subskrybujemy publikacji. `name="Comment"` trafial wtedy
   w „View comments (N)". Prawo odczytane z API dla wszystkich komentarzy pod
   postami od 5 wrzesnia: `subscribers` bez subskrypcji 0/7, `everyone` 22/22.

BEZ PYTESTA, bez sieci, bez przegladarki. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_przycisk_wysylki_i_subskrybenci.py
"""
import io
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import browser   # noqa: E402

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
    def __init__(self, nazwy):
        self.nazwy = nazwy
        self.first = self

    def count(self):
        return len(self.nazwy)

    def is_visible(self):
        return bool(self.nazwy)

    def nazwa(self):
        return self.nazwy[0] if self.nazwy else None


class Strona:
    """Dostepna nazwa jak w Playwright: `exact` = cala nazwa, bez niego = fragment bez wielkosci liter."""

    def __init__(self, przyciski):
        self.przyciski = list(przyciski)

    def get_by_role(self, rola, name=None, exact=None):
        if exact:
            return Przycisk([p for p in self.przyciski if p == name])
        return Przycisk([p for p in self.przyciski if name.lower() in p.lower()])


print("=== 1. NOTKA Z ZASADAMI ODPOWIEDZI (uklad z zywej strony) ===")
NOTKA = Strona(["Comment", "New post", "Comment", "The Context Engine reply rules", "Post"])
KOLEJKA_ODPOWIEDZI = ("Post", "Reply", "Odpowiedz", "Opublikuj", "Wyślij")
k, nazwa = browser.przycisk_wysylki(NOTKA, KOLEJKA_ODPOWIEDZI)
sprawdz("wybrany przycisk to „Post\"", nazwa == "Post" and k.nazwa() == "Post", (nazwa, k and k.nazwa()))
# KONTRDOWOD: stara kolejnosc i dopasowanie fragmentem trafialy w zasady.
stary = None
for n in ("Reply", "Odpowiedz", "Post", "Opublikuj", "Wyślij"):
    kand = NOTKA.get_by_role("button", name=n).first
    if kand.count() > 0 and kand.is_visible():
        stary = kand.nazwa()
        break
sprawdz("KONTRDOWOD: stary wybor lapal „…reply rules\"", stary == "The Context Engine reply rules", stary)

print()
print("=== 2. POST TYLKO DLA SUBSKRYBENTOW (uklad z zywej strony) ===")
POST = Strona(["View comments (2)", "View comments (2)", "Comments", "LLMs Research reply rules",
               "View comments (4)"])
k, nazwa = browser.przycisk_wysylki(POST, ("Post", "Opublikuj", "Wyślij", "Skomentuj"))
sprawdz("brak przycisku wysylki: nic nie wybrane", k is None and nazwa is None, nazwa)
stary = None
for n in ("Post", "Opublikuj", "Wyślij", "Comment", "Skomentuj"):
    kand = POST.get_by_role("button", name=n).first
    if kand.count() > 0 and kand.is_visible():
        stary = kand.nazwa()
        break
sprawdz("KONTRDOWOD: stary wybor klikal „View comments\"", stary == "View comments (2)", stary)

k, nazwa = browser.przycisk_wysylki(Strona(["View comments (2)", "Post"]),
                                    ("Post", "Opublikuj", "Wyślij", "Skomentuj"))
sprawdz("zwykly post po wpisaniu: „Post\"", nazwa == "Post", nazwa)
k, nazwa = browser.przycisk_wysylki(Strona(["New post", "Opublikuj"]), ("Post", "Opublikuj"))
sprawdz("„New post\" nie jest „Post\"; polski interfejs dziala", nazwa == "Opublikuj", nazwa)


class Wadliwa:
    def get_by_role(self, *a, **k):
        raise RuntimeError("strona zniknela")


sprawdz("wyjatek strony nie wywraca wysylki", browser.przycisk_wysylki(Wadliwa(), ("Post",)) == (None, None))

print()
print("=== 3. OBIE WYSYLKI UZYWAJA TEGO WYBORU, „Comment\" ZNIKA Z KOLEJKI ===")
ZR = io.open("agent-v2/browser.py", encoding="utf-8").read()


def cialo(nazwa):
    start = ZR.find("\ndef %s(" % nazwa)
    koniec = ZR.find("\ndef ", start + 1)
    return ZR[start:koniec]


for funkcja in ("wystaw_odpowiedz", "wystaw_komentarz"):
    c = cialo(funkcja)
    sprawdz("%s wybiera przez `przycisk_wysylki`" % funkcja, "przycisk_wysylki(" in c)
    sprawdz("%s nie szuka juz przycisku fragmentem nazwy" % funkcja,
            'get_by_role("button", name=nazwa).first' not in c)
    sprawdz("%s czysci pole, gdy nie ma czym wyslac" % funkcja,
            "if wyslij and przycisk is None:" in c and "oproznij_pole(" in c.split("if wyslij and przycisk is None:")[1][:600])
sprawdz("komentarz pod postem nie probuje „Comment\"",
        '"Comment"' not in cialo("wystaw_komentarz").split("przycisk_wysylki(")[1][:120])

print()
print("=== 4. ZAPORA: KOMENTARZE TYLKO DLA SUBSKRYBENTOW ===")


class K:
    def __init__(self):
        self.first = self

    def new_page(self):
        return self

    def close(self):
        pass

    def stop(self):
        pass


ORYG = (browser.podlacz_sie, browser.wymagaj_sesji, browser.api_json, browser.PLATNE_HOSTY,
        browser.hosty_gdzie_komentarz_nie_wchodzi)
zapytania = []


def swiat(post, profile):
    zapytania.clear()
    browser.wymagaj_sesji = lambda: None
    browser.podlacz_sie = lambda: (K(), K(), K())
    browser.hosty_gdzie_komentarz_nie_wchodzi = lambda: set()
    browser.PLATNE_HOSTY = pathlib.Path(tempfile.mkdtemp()) / "platne.json"

    def api(page, sciezka, baza=None):
        zapytania.append(sciezka)
        if sciezka.startswith("/api/v1/posts/"):
            return post
        for uchwyt, profil in profile.items():
            if sciezka == "/api/v1/user/%s/public_profile" % uchwyt:
                return profil
        return None
    browser.api_json = api


URL = "https://publikacja-a.example/p/tekst"
POST_SUB = {"id": 1, "publication_id": 77, "write_comment_permissions": "subscribers",
            "audience": "everyone", "publishedBylines": [{"handle": "autor-a"}]}
try:
    swiat(POST_SUB, {"autor-a": {"isSubscribed": False, "primaryPublication": {"id": 77}}})
    sprawdz("subskrybenci, a my nie subskrybujemy: nie piszemy", browser.mozna_komentowac(URL) is False)
    sprawdz("host NIE zapamietany jako platny (subskrypcja moze przyjsc)",
            "publikacja-a.example" not in browser.hosty_tylko_dla_placacych())
    swiat(POST_SUB, {"autor-a": {"isSubscribed": True, "primaryPublication": {"id": 77}}})
    sprawdz("subskrybenci i subskrybujemy te publikacje: piszemy", browser.mozna_komentowac(URL) is True)
    swiat(POST_SUB, {"autor-a": {"isSubscribed": True, "primaryPublication": {"id": 99}}})
    sprawdz("subskrybujemy INNA publikacje autora: nie piszemy", browser.mozna_komentowac(URL) is False)
    swiat(POST_SUB, {})
    sprawdz("profil nie odpowiada: nie piszemy (prawo znane, subskrypcji brak dowodu)",
            browser.mozna_komentowac(URL) is False)
    swiat(dict(POST_SUB, publishedBylines=[]), {})
    sprawdz("brak autora w API: nie piszemy", browser.mozna_komentowac(URL) is False)
    swiat(dict(POST_SUB, write_comment_permissions="everyone"), {})
    sprawdz("KONTRDOWOD: `everyone` bez pytania o profil", browser.mozna_komentowac(URL) is True
            and not any("/user/" in z for z in zapytania), zapytania)
finally:
    (browser.podlacz_sie, browser.wymagaj_sesji, browser.api_json, browser.PLATNE_HOSTY,
     browser.hosty_gdzie_komentarz_nie_wchodzi) = ORYG

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
