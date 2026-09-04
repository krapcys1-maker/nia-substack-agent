"""Test pieciu poprawek. Kazda z kontrdowodem: sprawdzamy takze, ze test
wykrywa STARE zachowanie, bo test przechodzacy na zepsutym kodzie nic nie wart.

Nic nie publikuje. Produkcja nietknieta — pilnowana odciskami na koncu.
"""
import hashlib
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import browser   # noqa: E402
import config    # noqa: E402
import wlasna_konfiguracja  # noqa: E402
import stages    # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# Asercje o DOSTARCZONYCH wartosciach, pomijane widocznie,
# gdy operator ma wlasne w `konfiguracja.toml`.
sprawdz_nasze = wlasna_konfiguracja.tylko_nasze(sprawdz)


def odcisk(p):
    p = pathlib.Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else "brak"


PILNOWANE = [config.DB_PATH, config.DATA_DIR / "zuzyte_fakty.json",
             config.DATA_DIR / "promocja.json", config.DATA_DIR / "dziennik.jsonl"]
PRZED = {str(p): odcisk(p) for p in PILNOWANE}

# =====================================================================
print("=== 1. POTWIERDZANIE KOMENTARZA POD NOTKA (stary kod pytal zly adres) ===")

pytania = []


class FalszywaStrona:
    def wait_for_timeout(self, ms):
        pass


def podstaw_api(odpowiedzi):
    """Podmienia api_json tak, zeby zapisywal, o CO pytamy."""
    def falszywe(page, sciezka, baza=None):
        pytania.append((sciezka, baza))
        for wzor, wynik in odpowiedzi.items():
            if wzor in sciezka:
                return wynik
        return None
    return falszywe


oryg_api = browser.api_json
NASZ = "The cutoff is cleaner on paper than in the air"
try:
    browser.api_json = podstaw_api({
        "/replies": {"commentBranches": [{"comment": {"body": NASZ, "user_id": 1}}]},
    })
    pytania.clear()
    wynik = browser.potwierdz_komentarz(
        FalszywaStrona(), "https://substack.com/note/c-900000007", NASZ)
    sprawdz("komentarz pod notka POTWIERDZONY", bool(wynik), wynik)
    sprawdz("oddaje numer komentarza, nie samo tak", wynik == -1, wynik)
    sprawdz("nie pyta juz o /api/v1/posts/ (to bylo zrodlo bledu)",
            not any("/api/v1/posts/" in s for s, _ in pytania), pytania)
    sprawdz("pyta wlasciwy endpoint watku",
            any("/reader/comment/900000007/replies" in s for s, _ in pytania), pytania)

    # Kontrdowod: gdyby w watku nie bylo naszego tekstu, ma zwrocic False.
    browser.api_json = podstaw_api({"/replies": {"commentBranches": []}})
    sprawdz("pusty watek -> NIE potwierdza (test rozroznia)",
            browser.potwierdz_komentarz(
                FalszywaStrona(), "https://substack.com/note/c-1", NASZ) is None)

    # ZNALEZIONY Z NUMEREM: numer ma wrocic, bo po nim laczymy skutki.
    browser.api_json = podstaw_api({
        "/replies": {"commentBranches": [
            {"comment": {"body": NASZ, "user_id": 1, "id": 424242}}]}})
    sprawdz("oddaje prawdziwy numer, gdy API go poda",
            browser.potwierdz_komentarz(
                FalszywaStrona(), "https://substack.com/note/c-9", NASZ) == 424242)

    # Artykul ma isc STARA sciezka — nie wolno jej zepsuc.
    pytania.clear()
    browser.api_json = podstaw_api({
        "/api/v1/posts/": {"id": 999},
        "/comments": {"comments": [{"body": NASZ}]},
    })
    wynik = browser.potwierdz_komentarz(
        FalszywaStrona(), "https://www.publikacja-c.example/p/jakis-tekst", NASZ)
    sprawdz("komentarz pod ARTYKULEM nadal potwierdzany", bool(wynik), wynik)
    sprawdz("dla artykulu nadal pyta /api/v1/posts/",
            any("/api/v1/posts/" in s for s, _ in pytania), pytania)
    sprawdz("pyta domeny AUTORA, nie substack.com",
            any(b and "publikacja-c" in b for _, b in pytania), pytania)
finally:
    browser.api_json = oryg_api

# =====================================================================
print()
print("=== 2. POMIJANIE PUBLIKACJI TYLKO DLA PLACACYCH ===")

oryg_podlacz, oryg_sesja = browser.podlacz_sie, browser.wymagaj_sesji


class Nic:
    def new_page(self):
        return self

    def close(self):
        pass

    def stop(self):
        pass


def podstaw_przegladarke():
    browser.wymagaj_sesji = lambda: None
    browser.podlacz_sie = lambda: (Nic(), Nic(), Nic())


try:
    podstaw_przegladarke()
    for prawo, oczekiwane in (("only_paid", False), ("only_founding", False),
                              ("none", False), ("everyone", True),
                              ("all_subscribers", True), (None, True)):
        browser.api_json = podstaw_api({"/api/v1/posts/":
                                        {"id": 1, "write_comment_permissions": prawo}})
        wynik = browser.mozna_komentowac("https://www.publikacja-c.example/p/x")
        sprawdz("write_comment_permissions=%-16r -> %s" % (prawo, oczekiwane),
                wynik is oczekiwane, wynik)

    browser.api_json = podstaw_api({})          # API milczy
    sprawdz("gdy API milczy, PROBUJEMY (nie zamykamy sobie ust)",
            browser.mozna_komentowac("https://x.substack.com/p/y") is True)
    sprawdz("pod notka zawsze wolno",
            browser.mozna_komentowac("https://substack.com/note/c-5") is True)
finally:
    browser.api_json = oryg_api
    browser.podlacz_sie, browser.wymagaj_sesji = oryg_podlacz, oryg_sesja

# =====================================================================
print()
print("=== 3. NAZWA PUBLIKACJI Z WLASNEJ DOMENY (stary kod dawal 'www') ===")

try:
    podstaw_przegladarke()
    browser.api_json = podstaw_api({"/api/v1/posts": [
        {"publishedBylines": [{"handle": "mattstoller"}]}]})
    for host, oczekiwane in (("www.publikacja-d.example", "mattstoller"),
                             ("publikacja9.substack.com", "publikacja9"),
                             ("foo.substack.com", "foo")):
        wynik = browser.uchwyt_publikacji(host)
        sprawdz("%-36s -> %r" % (host, oczekiwane), wynik == oczekiwane, wynik)
        sprawdz("   ... i na pewno NIE 'www'", wynik != "www", wynik)

    browser.api_json = podstaw_api({})          # nic nie wiadomo
    sprawdz("gdy nie da sie ustalic -> None, zamiast zgadywac",
            browser.uchwyt_publikacji("www.cos.com") is None)
    sprawdz("pusty host -> None", browser.uchwyt_publikacji("") is None)

    # Kontrdowod: stary sposob na tych samych danych.
    sprawdz("STARY sposob dawalby 'www' (test rozroznia)",
            "www.publikacja-d.example".split(".")[0] == "www")
finally:
    browser.api_json = oryg_api
    browser.podlacz_sie, browser.wymagaj_sesji = oryg_podlacz, oryg_sesja

# =====================================================================
print()
print("=== 4. ODPOWIEDZI NA NASZE KOMENTARZE U OBCYCH ===")

KANAL = {
    "activityItems": [
        {"type": "comment_reply", "comment_id": 900, "target_comment_id": 100,
         "target_post_id": 7, "created_at": "2026-08-16T14:22:21.000Z",
         "recent_sender_ids": [900000004]},
        {"type": "comment_reply", "comment_id": 901, "target_comment_id": 101,
         "target_post_id": 7, "created_at": "2026-08-16T10:00:00.000Z",
         "recent_sender_ids": [900000004]},
        {"type": "note_reply", "comment_id": 902, "target_comment_id": 102,
         "created_at": "2026-08-16T12:09:28.000Z", "recent_sender_ids": [5]},
        # Nasza odpowiedz w tym watku jest STARSZA od ich pytania — czyli
        # odpowiadalismy komus innemu, a to pytanie nadal wisi.
        {"type": "comment_reply", "comment_id": 903, "target_comment_id": 100,
         "target_post_id": 7, "created_at": "2026-08-16T16:00:00.000Z",
         "recent_sender_ids": [900000004]},
        {"type": "note_like", "comment_id": None, "target_comment_id": 103,
         "created_at": "2026-08-16T09:00:00.000Z"},
        {"type": "follow", "created_at": "2026-08-16T21:27:27.000Z"},
    ],
    "comments": [
        {"id": 100, "body": "Morris wanted workers to reconnect with craft",
         "user_id": 900000005},
        {"id": 101, "body": "nasz drugi komentarz", "user_id": 900000005},
        {"id": 900, "body": "Yes, exactly! There was an inherent disconnect",
         "name": "Designer", "language": "en", "user_id": 900000004},
        {"id": 901, "body": "a tu juz odpisalismy", "name": "Ktos", "user_id": 900000004},
        {"id": 903, "body": "a to pytanie nadal wisi", "name": "Inny",
         "language": "en", "user_id": 900000004},
    ],
    "users": [{"id": 900000004, "name": "Designer"}],
    "posts": [{"id": 7, "title": "Design Study #4",
               "canonical_url": "https://publikacja9.substack.com/p/design-study-4"}],
}

WATKI = {
    # 900: nikt z nas nie odpisal po ich odpowiedzi -> CZEKA
    "/reader/comment/900/replies": {"commentBranches": []},
    # 901: odpisalismy PO ich odpowiedzi -> pomijamy.
    # `body` jest KONIECZNE: _plaskie pomija wpisy bez tresci, wiec bez niego
    # test udawalby, ze odpowiedzi nie ma, i sprawdzalby nie to co trzeba.
    "/reader/comment/901/replies": {"commentBranches": [
        {"comment": {"user_id": 900000005, "body": "nasza odpowiedz",
                     "date": "2026-08-16T11:00:00.000Z"}}]},
    # 902: ktos odpisal PRZED nasza ostatnia wypowiedzia w innym watku —
    # nasza starsza odpowiedz NIE moze zaliczyc nowszego pytania.
    "/reader/comment/903/replies": {"commentBranches": [
        {"comment": {"user_id": 900000005, "body": "stara nasza odpowiedz",
                     "date": "2026-08-15T09:00:00.000Z"}}]},
}

try:
    podstaw_przegladarke()

    def api_kanalu(page, sciezka, baza=None):
        if "public_profile" in sciezka:
            return {"id": 900000005}
        if "activity-feed-web" in sciezka:
            return KANAL
        for wzor, wynik in WATKI.items():
            if wzor in sciezka:
                return wynik
        return None

    browser.api_json = api_kanalu
    czekaja = browser.odpowiedzi_na_nasze_komentarze()
    sprawdz("znajduje dokladnie 2 czekajace odpowiedzi (900 i 903)",
            sorted(c["pod_id"] for c in czekaja) == [900, 903],
            [c.get("pod_id") for c in czekaja])
    sprawdz("nasza STARSZA odpowiedz nie zalicza nowszego pytania (903)",
            any(c["pod_id"] == 903 for c in czekaja))
    if czekaja:
        c = [x for x in czekaja if x["pod_id"] == 900][0]
        sprawdz("to odpowiedz od Designer", c["autor"] == "Designer", c["autor"])
        sprawdz("odpowiadamy ICH komentarzowi (900), nie swojemu (100)",
                c["pod_id"] == 900, c["pod_id"])
        sprawdz("niesie nasz komentarz jako kontekst",
                "Morris" in c["pod_czym"], c["pod_czym"][:40])
        sprawdz("niesie adres posta",
                "design-study-4" in (c["url"] or ""), c["url"])
        sprawdz("kontekst mowi, ze to komentarz pod cudzym tekstem",
                "our own comment" in c["kontekst"], c["kontekst"])
        sprawdz("jezyk przepisany z oryginalu", c["jezyk"] == "en", c["jezyk"])
    sprawdz("POMIJA te, na ktore juz odpisalismy",
            all(c["pod_id"] != 901 for c in czekaja))
    sprawdz("NIE bierze note_reply (to robi nieodpowiedziane)",
            all(c["pod_id"] != 902 for c in czekaja))
    sprawdz("NIE bierze polubien ani obserwacji",
            all(c["pod_id"] not in (None, 103) for c in czekaja))

    # Kontrdowod: gdyby kanal nie mial zdarzen, ma byc pusto — nie wymyslac.
    KANAL_PUSTY = dict(KANAL, activityItems=[])
    browser.api_json = lambda page, sciezka, baza=None: (
        {"id": 900000005} if "public_profile" in sciezka
        else KANAL_PUSTY if "activity-feed-web" in sciezka else None)
    sprawdz("pusty kanal -> pusta lista", browser.odpowiedzi_na_nasze_komentarze() == [])

    browser.api_json = lambda page, sciezka, baza=None: (_ for _ in ()).throw(
        RuntimeError("padlo"))
    sprawdz("awaria kanalu nie wywala przebiegu",
            browser.odpowiedzi_na_nasze_komentarze() == [])
finally:
    browser.api_json = oryg_api
    browser.podlacz_sie, browser.wymagaj_sesji = oryg_podlacz, oryg_sesja

# =====================================================================
print()
print("=== 5. PULA FAKTOW: znaleziony to nie zuzyty ===")

import inspect  # noqa: E402

# Sprawdzamy ZACHOWANIE, nie tresc pliku: pierwsza wersja tego testu szukala
# napisu "zapisz_zuzyte" i oblewala, bo napis zostal w komentarzu tlumaczacym,
# czemu wywolania juz tam nie ma. Test ma pytac co kod ROBI.
kat = pathlib.Path(tempfile.mkdtemp())
oryg_plik, oryg_llm = stages.ZUZYTE_FAKTY, stages.llm.call
# CALY KATALOG DANYCH, nie sam plik zuzytych faktow. `znajdz_ciekawostki` schodzi
# przez `aktualne_modele.pobierz` do `db.connect()`, a bez przekierowania to jest
# PRODUKCYJNA baza — zmierzone sonda 2 wrzesnia 2026 — bo `config.DB_PATH` jest
# liczone przy imporcie i samo podstawienie `DATA_DIR` by go nie ruszylo.
_zdjecie_sciezek = config.uzyj_katalogu_danych(kat)
stages.ZUZYTE_FAKTY = kat / "zuzyte.json"
try:
    stages.llm.call = lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError("nie wolam modelu w tescie"))
    try:
        stages.znajdz_ciekawostki(None, 0)
    except Exception:
        pass
    sprawdz("znajdz_ciekawostki nie tworzy pliku zuzytych faktow",
            not stages.ZUZYTE_FAKTY.exists(), odcisk(stages.ZUZYTE_FAKTY))

    stages.zapisz_zuzyte(["fakt o windach"])
    sprawdz("zapisz_zuzyte nadal dziala, gdy ktos je swiadomie wola",
            "windach" in stages.ZUZYTE_FAKTY.read_text(encoding="utf-8"))
    sprawdz("zapisany fakt jest potem widziany jako zuzyty",
            any("windach" in t for t in stages.wczytaj_zuzyte()))
finally:
    stages.ZUZYTE_FAKTY, stages.llm.call = oryg_plik, oryg_llm
    config.przywroc_katalog_danych(_zdjecie_sciezek)

zrodlo_run = pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8")
sprawdz("run.py odhacza fakt dopiero po potwierdzonej publikacji",
        'wynik.get("wyslane") and n.get("fakt")' in zrodlo_run)

# Rozdzial rodzajow notek miedzy przebiegi
MIX = list(config.NOTE_MIX_OTHER_DAY)
print("    sklad dnia: %s" % MIX)
zebrane, juz = [], 0
for ile in (2, 2, 1):
    kawalek = MIX[juz: juz + ile]
    zebrane += kawalek
    print("    przebieg: od=%s ile=%s -> %s" % (juz, ile, kawalek))
    juz += ile
sprawdz("trzy przebiegi odtwarzaja CALY sklad dnia", zebrane == MIX, zebrane)
sprawdz("w ciagu dnia sa rozne rodzaje notek, nie same CIEKAWOSTKI",
        len(set(zebrane)) > 1, set(zebrane))
stare = MIX[:2] + MIX[:2] + MIX[:1]
sprawdz_nasze("STARY wycinek dawalby same %r (test rozroznia)" % MIX[0],
        len(set(stare)) == 1 and stare != zebrane, set(stare))

sygn = inspect.signature(stages.notki_dnia).parameters
sprawdz("notki_dnia przyjmuje 'ile' i 'od'", "ile" in sygn and "od" in sygn)

# =====================================================================
print()
print("=== PRODUKCJA NIETKNIETA ===")
zle = 0
for p in PILNOWANE:
    teraz = odcisk(p)
    ok = teraz == PRZED[str(p)]
    zle += 0 if ok else 1
    print("  %-24s %s" % (pathlib.Path(p).name, "bez zmian" if ok else "ZMIENIONA"))

print()
print("=== WYNIK: %s zdanych, %s oblanych%s ===" %
      (zdane, oblane, ", PRODUKCJA RUSZONA" if zle else ""))
sys.exit(1 if (oblane or zle) else 0)
