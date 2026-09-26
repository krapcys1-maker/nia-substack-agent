# -*- coding: utf-8 -*-
"""Dwa boty nie moga odpisywac sobie bez konca.

SKAD TO SIE WZIELO. 26 wrzesnia 2026 wlasciciel pokazal zrzuty: pod dwoma
artykulami NIA ona i drugi bot tego samego wlasciciela odpisywali sobie na
zmiane przez piec dni. Zmierzone na drzewie komentarzy z API: pod artykulem
„I'd like the songwriter's definition of fair" JEDEN komentarz tamtego bota
urosl do 41 — 20 odpowiedzi NIA i 20 jego. Slowa wlasciciela: dialog jest
wskazany, ale to „wyglada totalnie jak 2 boty zapetlone".

DWIE WADY, OBIE W `browser.py`:

  1. `odpowiedzi_na_nasze_komentarze` pytala tylko, czy na TE wiadomosc juz
     odpisalismy. Kazda odpowiedz drugiej strony byla nowa, wiec rozmowa
     z automatem nie konczyla sie nigdy. Teraz liczymy NASZE odpowiedzi
     w calej galezi rozmowy (`ancestor_path`), z limitem.
  2. `komentarze_pod_artykulami` patrzyla na sam wierzch drzewa, a odpowiedzi
     wisza pietro nizej — komentarz, na ktory odpisalismy dwadziescia razy,
     dalej wygladal na czekajacy. To ta droga dala 20 odpowiedzi NIA pod
     jednym komentarzem.

Drzewo w atrapie to KSZTALT prawdziwego drzewa z 26 wrzesnia (numery, sciezki
przodkow i daty), bez tresci. Drugi bot wystepuje pod numerem zastepczym.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_petla_rozmowy.py
"""
import sys

sys.path.insert(0, "agent-v2")
import browser  # noqa: E402
import config   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


NIA, BOT, CZLOWIEK = 547272980, 700000001, 111222333
POST = 215164012

# (numer, autor, ancestor_path, data) — w kolejnosci wypowiedzi.
ROZMOWA = [
    (334906206, BOT, "", "2026-09-11T17:50:02"),
    (335148999, NIA, "334906206", "2026-09-12T00:41:01"),
    (335377103, BOT, "334906206.335148999", "2026-09-12T11:38:51"),
    (335441036, NIA, "334906206", "2026-09-12T13:39:36"),
    (335450240, NIA, "334906206.335148999.335377103", "2026-09-12T13:54:53"),
    (335578060, BOT, "334906206.335148999.335377103.335450240", "2026-09-12T17:11:46"),
    (335583919, BOT, "334906206.335441036", "2026-09-12T17:20:41"),
    (335831290, NIA, "334906206", "2026-09-13T00:41:56"),
    (335834872, NIA, "334906206.335148999.335377103.335450240.335578060", "2026-09-13T00:50:09"),
    (336055554, NIA, "334906206", "2026-09-13T11:23:32"),
    (336059844, BOT, "334906206.336055554", "2026-09-13T11:33:16"),
    (336064856, BOT, "334906206.335148999.335377103.335450240.335578060.335834872", "2026-09-13T11:44:06"),
    (336068318, BOT, "334906206.335831290", "2026-09-13T11:51:22"),
    (336135396, NIA, "334906206", "2026-09-13T13:49:21"),
    (336142956, NIA, "334906206.335831290.336068318", "2026-09-13T14:01:26"),
    (336270992, BOT, "334906206.335831290.336068318.336142956", "2026-09-13T17:06:48"),
    (336353909, NIA, "334906206", "2026-09-13T19:07:01"),
    (336371209, BOT, "334906206.336135396", "2026-09-13T19:33:20"),
    (336381731, BOT, "334906206.336353909", "2026-09-13T19:49:21"),
    (336458386, NIA, "334906206", "2026-09-13T21:53:32"),
    (336515617, BOT, "334906206.336458386", "2026-09-13T23:46:39"),
    (336537869, NIA, "334906206", "2026-09-14T00:36:32"),
    (336774692, NIA, "334906206", "2026-09-14T11:07:40"),
    (336783959, BOT, "334906206.336537869", "2026-09-14T11:26:17"),
    (336791280, BOT, "334906206.336774692", "2026-09-14T11:40:44"),
    (336875984, NIA, "334906206", "2026-09-14T13:52:54"),
    (337025933, BOT, "334906206.336875984", "2026-09-14T17:07:08"),
    (337226197, NIA, "334906206", "2026-09-14T21:49:31"),
    (337295353, BOT, "334906206.337226197", "2026-09-14T23:52:40"),
    (337316959, NIA, "334906206", "2026-09-15T00:35:15"),
    (337569976, NIA, "334906206", "2026-09-15T11:19:38"),
    (337577715, BOT, "334906206.337569976", "2026-09-15T11:34:01"),
    (337586367, BOT, "334906206.337316959", "2026-09-15T11:49:28"),
    (337668346, NIA, "334906206", "2026-09-15T13:53:46"),
    (337823663, BOT, "334906206.337668346", "2026-09-15T17:15:12"),
    (337911272, NIA, "334906206", "2026-09-15T19:08:55"),
    (337927895, BOT, "334906206.337911272", "2026-09-15T19:31:49"),
    (338043861, NIA, "334906206", "2026-09-15T22:26:03"),
    (338088534, BOT, "334906206.338043861", "2026-09-15T23:49:17"),
    (338117552, NIA, "334906206", "2026-09-16T00:48:32"),
    (338384720, BOT, "334906206.338117552", "2026-09-16T11:56:02"),
]
KORZEN = "334906206"


def komentarz(numer, autor, sciezka, data, post=POST):
    return {"id": numer, "user_id": autor, "ancestor_path": sciezka,
            "post_id": post, "date": data + "Z", "body": "x",
            "name": {BOT: "Drugi bot", NIA: "NIA"}.get(autor, "Czytelnik")}


def drzewo(wiersze, post=POST):
    """Buduje drzewo `children` tak, jak oddaje je `/post/<id>/comments`."""
    wezly = {w[0]: dict(komentarz(*w, post=post), children=[]) for w in wiersze}
    gora = []
    for numer, _, sciezka, _ in wiersze:
        rodzic = sciezka.split(".")[-1] if sciezka else None
        if rodzic and int(rodzic) in wezly:
            wezly[int(rodzic)]["children"].append(wezly[numer])
        else:
            gora.append(wezly[numer])
    return gora


PLASKIE = [komentarz(*w) for w in ROZMOWA]
STARE = (config.MAKS_ODPOWIEDZI_W_ROZMOWIE,
         config.MAKS_ODPOWIEDZI_KONTU_SIOSTRZANEMU, config.KONTA_SIOSTRZANE)

print("=== 1. KORZEN ROZMOWY ===")
sprawdz("komentarz najwyzszego poziomu jest wlasnym korzeniem",
        browser.korzen_rozmowy(PLASKIE[0]) == KORZEN)
sprawdz("odpowiedz pod cudzym komentarzem nalezy do jego galezi",
        browser.korzen_rozmowy(PLASKIE[1]) == KORZEN)
sprawdz("szosty poziom w glab nadal ma ten sam korzen",
        browser.korzen_rozmowy(PLASKIE[11]) == KORZEN)
# Pod notka pierwszym przodkiem jest SAMA notka (sprawdzone na zywym watku).
pod_notka = {"id": 341194970, "ancestor_path": "340495981", "post_id": None}
sprawdz("komentarz wprost pod notka zaczyna wlasna rozmowe",
        browser.korzen_rozmowy(pod_notka) == "341194970")
glebiej = {"id": 5, "ancestor_path": "340495981.341194970", "post_id": None}
sprawdz("odpowiedz na komentarz pod notka nalezy do niego, nie do calej notki",
        browser.korzen_rozmowy(glebiej) == "341194970")

print()
print("=== 2. ZYWE DRZEWO: ILE RAZY KAZDY ODPISAL ===")
plaskie = [c for k in drzewo(ROZMOWA) for c in browser._plaskie(k)]
sprawdz("drzewo rozwija sie do 41 komentarzy", len(plaskie) == 41, len(plaskie))
sprawdz("odpowiedzi NIA w tej rozmowie: 20",
        browser.nasze_odpowiedzi_w_rozmowie(plaskie, KORZEN, NIA) == 20,
        browser.nasze_odpowiedzi_w_rozmowie(plaskie, KORZEN, NIA))
sprawdz("odpowiedzi drugiego bota w tej rozmowie: 20",
        browser.nasze_odpowiedzi_w_rozmowie(plaskie, KORZEN, BOT) == 20)
sprawdz("komentarz otwierajacy nie jest liczony jako odpowiedz",
        browser.nasze_odpowiedzi_w_rozmowie(plaskie[:1], KORZEN, BOT) == 0)

print()
print("=== 3. TA SAMA ROZMOWA Z LIMITEM ===")
# Symulacja gra za OBA boty naraz, a kazdy z nich widzi drugiego jako
# siostrzanego — tak, jak ustawia to `KONTA_SIOSTRZANE` w `.env` kazdej kopii.
config.KONTA_SIOSTRZANE = frozenset({NIA, BOT})


def ile_wypowiedzi(limit_dla):
    """Odtwarza rozmowe po kolei i zatrzymuje ja na pierwszej odpowiedzi,
    ktorej limit juz by nie przepuscil. Oddaje, ile wypowiedzi by padlo."""
    padlo = [PLASKIE[0]]
    for c in PLASKIE[1:]:
        mowi, rozmowca = c["user_id"], BOT if c["user_id"] == NIA else NIA
        if browser.nasze_odpowiedzi_w_rozmowie(padlo, KORZEN, mowi) >= limit_dla(rozmowca):
            return len(padlo)
        padlo.append(c)
    return len(padlo)


sprawdz("z drugim botem: 3 wypowiedzi zamiast 41",
        ile_wypowiedzi(browser.limit_rozmowy) == 3, ile_wypowiedzi(browser.limit_rozmowy))
# NIA odpisala tu dwa razy z rzedu (13:39 i 13:54), wiec jej druga odpowiedz
# wyczerpuje limit juz przy czwartej wypowiedzi.
sprawdz("gdyby oba konta mialy limit czlowieka: 4 wypowiedzi",
        ile_wypowiedzi(lambda _: config.MAKS_ODPOWIEDZI_W_ROZMOWIE) == 4,
        ile_wypowiedzi(lambda _: config.MAKS_ODPOWIEDZI_W_ROZMOWIE))
sprawdz("KONTRDOWOD: bez limitu rozmowa idzie do konca, 41",
        ile_wypowiedzi(lambda _: 10 ** 6) == 41)

# --- atrapa przegladarki i API ---------------------------------------------


class _Nic:
    def __getattr__(self, nazwa):
        return lambda *a, **k: _Nic()


wolania = []


def podepnij(odpowiedzi):
    def api(page, sciezka, baza=None):
        wolania.append((sciezka, baza))
        for wzorzec, dane in odpowiedzi:
            if wzorzec in sciezka:
                return dane
        return None
    browser.api_json = api
    browser.podlacz_sie = lambda *a, **k: (_Nic(), _Nic(), _Nic())
    browser.wymagaj_sesji = lambda *a, **k: None


STARE_API = browser.api_json
STARE_POLACZ, STARA_SESJA = browser.podlacz_sie, browser.wymagaj_sesji

# Zdarzenie `comment_reply` tak, jak przychodzi z `activity-feed-web`: ostatnia
# odpowiedz drugiego bota na odpowiedz NIA — i obok swieza rozmowa z czlowiekiem.
OSTATNIA_BOTA = komentarz(338384720, BOT, "334906206.338117552", "2026-09-16T11:56:02")
CZLOWIEK_ODP = komentarz(900000002, CZLOWIEK, "900000001", "2026-09-26T10:00:00", post=777)
KANAL = {
    "activityItems": [
        {"type": "comment_reply", "comment_id": 338384720,
         "target_comment_id": 338117552, "target_post_id": POST,
         "created_at": "2026-09-16T11:56:02.000Z"},
        {"type": "comment_reply", "comment_id": 900000002,
         "target_comment_id": 900000001, "target_post_id": 777,
         "created_at": "2026-09-26T10:00:00.000Z"},
    ],
    "comments": [OSTATNIA_BOTA, CZLOWIEK_ODP, PLASKIE[39],
                 komentarz(900000001, NIA, "", "2026-09-26T09:00:00", post=777)],
    "posts": [{"id": POST, "title": "I'd like the songwriter's definition of fair",
               "canonical_url": "https://nia1503032.substack.com/p/id-like-the-songwriters-definition"},
              {"id": 777, "title": "Czyjs tekst",
               "canonical_url": "https://ktos.substack.com/p/czyjs-tekst"}],
    "users": [],
}
ODPOWIEDZI_KANALU = [
    ("/public_profile", {"id": NIA}),
    ("activity-feed-web", KANAL),
    # Pod ich wiadomoscia nic od nas nie ma — stare sito przepuszcza obie.
    ("/replies", {"commentBranches": []}),
    ("/post/%d/comments" % POST, drzewo(ROZMOWA)),
    ("/post/777/comments", drzewo([(900000001, NIA, "", "2026-09-26T09:00:00"),
                                   (900000002, CZLOWIEK, "900000001", "2026-09-26T10:00:00")],
                                  post=777)),
]

try:
    print()
    print("=== 4. ODPOWIEDZI NA NASZE KOMENTARZE ===")
    config.KONTA_SIOSTRZANE = frozenset({BOT})
    podepnij(ODPOWIEDZI_KANALU)
    czekaja = browser.odpowiedzi_na_nasze_komentarze()
    numery = [c["id"] for c in czekaja]
    sprawdz("drugi bot po dwudziestu wymianach nie dostaje odpowiedzi",
            338384720 not in numery, numery)
    sprawdz("swieza rozmowa z czlowiekiem nadal dostaje odpowiedz",
            900000002 in numery, numery)
    sprawdz("drzewo posta czytane z publikacji, do ktorej nalezy",
            ("/api/v1/post/%d/comments?all_comments=true" % POST,
             "https://nia1503032.substack.com") in wolania,
            [w for w in wolania if "/post/" in w[0]])

    config.MAKS_ODPOWIEDZI_W_ROZMOWIE = 10 ** 6
    config.KONTA_SIOSTRZANE = frozenset()
    numery = [c["id"] for c in browser.odpowiedzi_na_nasze_komentarze()]
    sprawdz("KONTRDOWOD: bez limitu drugi bot dostalby dwudziesta pierwsza odpowiedz",
            338384720 in numery, numery)
    config.MAKS_ODPOWIEDZI_W_ROZMOWIE, _, config.KONTA_SIOSTRZANE = STARE

    print()
    print("=== 5. KOMENTARZE POD WLASNYM ARTYKULEM ===")
    podepnij([("/public_profile", {"id": NIA}),
              ("/api/v1/posts", [{"id": POST, "comment_count": 41,
                                  "title": "I'd like the songwriter's definition of fair",
                                  "canonical_url": "https://x.substack.com/p/y"}]),
              ("/comments", drzewo(ROZMOWA))])
    czekaja = browser.komentarze_pod_artykulami()
    sprawdz("komentarz, pod ktorym juz odpisano, nie czeka drugi raz",
            not czekaja, [c["id"] for c in czekaja])
    # KONTRDOWOD na samym wierzchu drzewa: tak liczyla stara wersja.
    podepnij([("/public_profile", {"id": NIA}),
              ("/api/v1/posts", [{"id": POST, "comment_count": 1, "title": "t",
                                  "canonical_url": "https://x.substack.com/p/y"}]),
              ("/comments", drzewo(ROZMOWA[:1]))])
    czekaja = browser.komentarze_pod_artykulami()
    sprawdz("komentarz bez odpowiedzi nadal czeka", [c["id"] for c in czekaja] == [334906206],
            [c["id"] for c in czekaja])

    print()
    print("=== 6. ODPOWIEDZI POD NASZA NOTKA ===")
    config.KONTA_SIOSTRZANE = frozenset({BOT})
    NOTKA = 400000000

    def watek_notki(wiersze):
        # Pod notka odpisujemy w polu pod cala notka: nasze wypowiedzi to
        # RODZENSTWO ich komentarzy, kazda we wlasnej galezi.
        return {"commentBranches": [
            {"comment": komentarz(n, a, str(NOTKA), d, post=None), "descendantComments": []}
            for n, a, d in wiersze]}

    def kto_czeka(wiersze):
        podepnij([("/public_profile", {"id": NIA}),
                  ("/reader/feed/profile", {"items": [{"comment": {
                      "id": NOTKA, "body": "nasza notka", "children_count": len(wiersze)}}]}),
                  ("/replies", watek_notki(wiersze))])
        return [c["id"] for c in browser.nieodpowiedziane()]

    sprawdz("pierwsze slowo czytelnika czeka na odpowiedz",
            kto_czeka([(1, CZLOWIEK, "2026-09-26T08:00:00")]) == [1])
    sprawdz("po jednej wymianie czytelnik dostaje druga odpowiedz",
            kto_czeka([(1, CZLOWIEK, "2026-09-26T08:00:00"), (2, NIA, "2026-09-26T09:00:00"),
                       (3, CZLOWIEK, "2026-09-26T10:00:00")]) == [3])
    sprawdz("po dwoch naszych odpowiedziach ostatnie slowo zostaje przy nim",
            kto_czeka([(1, CZLOWIEK, "2026-09-26T08:00:00"), (2, NIA, "2026-09-26T09:00:00"),
                       (3, CZLOWIEK, "2026-09-26T10:00:00"), (4, NIA, "2026-09-26T11:00:00"),
                       (5, CZLOWIEK, "2026-09-26T12:00:00")]) == [])
    sprawdz("drugi bot dostaje jedna odpowiedz, nie dwie",
            kto_czeka([(1, BOT, "2026-09-26T08:00:00"), (2, NIA, "2026-09-26T09:00:00"),
                       (3, BOT, "2026-09-26T10:00:00")]) == [])
finally:
    browser.api_json = STARE_API
    browser.podlacz_sie, browser.wymagaj_sesji = STARE_POLACZ, STARA_SESJA
    (config.MAKS_ODPOWIEDZI_W_ROZMOWIE, config.MAKS_ODPOWIEDZI_KONTU_SIOSTRZANEMU,
     config.KONTA_SIOSTRZANE) = STARE

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
