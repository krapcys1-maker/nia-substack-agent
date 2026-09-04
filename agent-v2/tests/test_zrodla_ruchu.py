# -*- coding: utf-8 -*-
"""SKAD biora sie zapisy — i dlaczego CISZA nie moze trafic do pliku jako zero.

CO TEN TEST PILNUJE. `browser.zapisz_zrodla_ruchu` czyta dwie tabele zrodel
z panelu naszej publikacji i dopisuje JEDNA linie do `data/zrodla.jsonl`:

    /api/v1/publication/stats/visitor_sources  — RUCH per zrodlo
    /api/v1/publication/stats/growth/sources   — ZAPISY per zrodlo, z notkami

Powstalo, bo kod nazywal „subskrypcjami z artykulu" pole
`stats.signups_within_1_day`, a to jest OKNO CZASOWE (kto zapisal sie w ciagu
doby po wpisie), nie przypisanie zrodla. Przypisanie panel ma — tylko nikt go
nie czytal.

ODPOWIEDZI W TYM PLIKU SA PRZEPISANE Z ZYWEGO PANELU, nie wymyslone. Odczyt
z 2 wrzesnia 2026, okno 2026-08-03 -> 2026-09-02:

    ruch    direct to app 640 wysw / 39 osob, substack app 184/46,
            direct 14/5, email opens 12/6      -> razem 850 wyswietlen, 96 osob
    zapisy  6, w tym 5 z NOTEK: c-900000012 dwa, c-900000009, c-900000010
            i c-900000011 po jednym; 1 z „substack other"

Obie tabele mowia o zapisach TO SAMO (6 i 6) — i to jest jedyna kontrola,
jaka ten odczyt ma z siebie samego.

DLACZEGO TEN TEST MIERZY ZACHOWANIE, A NIE TRESC KODU. Bo pytanie brzmi „co
wyladuje w pliku, gdy API zamilknie", a na to nie odpowiada zaden `grep`.
Ten projekt ma udokumentowany przypadek, w ktorym odpowiedz POPRAWNA I PUSTA
kosztowala DZIEWIEC DNI: 23 sierpnia 2026 na szesciu profilach nie bylo slowa
„Follow", wniosek brzmial „Substack zdjal przycisk", i przez dziewiec dni agent
nie zaobserwowal nikogo — a zero nikomu nie wygladalo na awarie, bo tabela
normy tlumaczyla je tym samym nieprawdziwym zdaniem. Sekcje 3, 4 i 5 sa
wylacznie o tym.

BEZ PYTESTA, zero sieci, zero platnych wywolan, produkcja nietknieta.
Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_zrodla_ruchu.py
"""
import hashlib
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import config   # noqa: E402
import browser  # noqa: E402

zdane = oblane = 0


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


# ODCISK CALEGO `agent-v2/data/` PRZED CZYMKOLWIEK. Ten test pisze do pliku
# jsonl, wiec jedyna rzecza, ktora naprawde musi udowodnic o sobie samym, jest
# to, ze NIE pisze do produkcji — takze przez plik, ktorego wczesniej nie bylo.
PILNOWANE = sorted(x for x in config.DATA_DIR.rglob("*") if x.is_file())
PRZED = {str(p): odcisk(p) for p in PILNOWANE}

KAT = pathlib.Path(tempfile.mkdtemp())

# --- ZYWE ODPOWIEDZI Z 2 WRZESNIA 2026 --------------------------------------

RUCH = {
    "rows": [
        {"source": "direct to app", "source_category": "Direct",
         "views": 640, "users": 39, "free_signup": None, "subscribed": None},
        {"source": "substack app", "source_category": "Substack",
         "views": 184, "users": 46, "free_signup": None, "subscribed": None},
        {"source": "direct", "source_category": "Direct",
         "views": 14, "users": 5, "free_signup": None, "subscribed": None},
        {"source": "email opens", "source_category": "Email",
         "views": 12, "users": 6, "free_signup": None, "subscribed": None},
        {"source": "substack.com", "source_category": "Substack",
         "views": None, "users": None, "free_signup": 1, "subscribed": 0},
        {"source": "substack notes", "source_category": "Substack",
         "views": None, "users": None, "free_signup": 5, "subscribed": 0},
    ],
    "total": 9,
}


def miary(ruch, subskrypcje, szereg=None):
    """`metrics` w ksztalcie, w jakim oddaje je panel."""
    return [{"name": "Traffic", "timeseries": szereg or [], "total": ruch},
            {"name": "Subscribers", "timeseries": szereg or [],
             "total": subskrypcje},
            {"name": "Revenue", "timeseries": [], "total": 0}]


def notka(ident, ile):
    return {"source": "c-%s" % ident, "sourceName": "Your Publication: …",
            "originalSourceName": "substack notes: c-%s" % ident,
            "category": "Substack", "noteId": int(ident),
            "metrics": miary(0, ile), "children": []}


# Drzewo przepisane z zywej odpowiedzi. `timeseries` skrocone wszedzie POZA
# galezia „substack other" — tam zostaje w calosci NIE przez przypadek: jej
# szereg zaczyna sie od 6, a `total` wynosi 1, wiec kod czytajacy ostatnia
# (albo pierwsza) wartosc szeregu zamiast `total` oddalby zla liczbe i ten
# jeden wezel to wylapie.
ZAPISY = {
    "sourceMetrics": [
        {"source": "substack", "sourceName": "Substack",
         "originalSourceName": "substack", "category": "Substack",
         "metrics": miary(28, 6),
         "children": [
             {"source": "substack other", "sourceName": "Other",
              "originalSourceName": "substack other", "category": "Substack",
              "metrics": [
                  {"name": "Traffic",
                   "timeseries": [{"date": "2026/09/02", "value": 28},
                                  {"date": "2026/09/02", "value": 0}],
                   "total": 28},
                  {"name": "Subscribers",
                   "timeseries": [{"date": "2026/09/02", "value": 6},
                                  {"date": "2026/09/02", "value": 1}],
                   "total": 1},
                  {"name": "Revenue", "timeseries": [], "total": 0}],
              "children": []},
             {"source": "trackbacks", "sourceName": "Trackbacks",
              "category": "Substack", "metrics": miary(0, 0), "children": []},
             {"source": "recommendations", "sourceName": "Recommendations",
              "category": "Substack", "metrics": miary(0, 0), "children": []},
             {"source": "notes", "sourceName": "Notes", "category": "Substack",
              "metrics": miary(0, 5),
              "children": [notka("900000009", 1), notka("900000010", 1),
                           notka("900000011", 1), notka("900000012", 2)]},
         ]},
        {"source": "direct", "sourceName": "Direct", "category": "Direct",
         "metrics": miary(2, 0), "children": []},
        {"source": "direct to app", "sourceName": "Direct to App",
         "category": "Direct", "metrics": miary(34, 0), "children": []},
    ],
    "totals": [{"name": "traffic", "total": 64},
               {"name": "subscribers", "total": 6},
               {"name": "revenue", "total": 0}],
}


class Strona:
    """Atrapa strony. `api_json` jest podmieniony, wiec nic z niej nie wola."""


def odpowiadaj(ruch, zapisy):
    """Podmienia `api_json`: co ma oddac na ktore z dwoch zapytan."""
    def _api(page, sciezka, baza=None):
        if not str(baza or "").startswith("https://%s." % config.SUBSTACK_HANDLE):
            # ADRES BAZOWY JEST OBOWIAZKOWY: oba te adresy naleza do NASZEJ
            # publikacji, a `api_json` bez `baza` pyta substack.com i oddaje
            # cisze. Ta sama pomylka kosztowala juz raz „46 pozycji i ZERO
            # artykulow" w pomiarze.
            raise AssertionError("zapytanie poszlo pod baze %r" % baza)
        wart = ruch if "visitor_sources" in sciezka else zapisy
        if isinstance(wart, Exception):
            raise wart
        return wart
    return _api


def linie():
    if not browser.ZRODLA.exists():
        return []
    return [x for x in browser.ZRODLA.read_text(encoding="utf-8").splitlines()
            if x.strip()]


stare_api = browser.api_json
stare_zrodla = browser.ZRODLA
stara_sesja = browser.wymagaj_sesji
stare_podlacz = browser.podlacz_sie
browser.ZRODLA = KAT / "zrodla.jsonl"

try:
    print("=== 1. POPRAWNA ODPOWIEDZ ZAPISUJE WIERSZ ===")
    browser.api_json = odpowiadaj(RUCH, ZAPISY)
    w = browser.zapisz_zrodla_ruchu(page=Strona())
    p = (w or {}).get("podsumowanie") or {}
    sprawdz("wiersz powstal", len(linie()) == 1, linie())
    sprawdz("obie polowy odczytane",
            (w or {}).get("odczytane") == ["ruch", "zapisy"], w and w.get("odczytane"))
    sprawdz("bez bledu", (w or {}).get("blad") is None, w and w.get("blad"))
    sprawdz("znacznik czasu UTC", str((w or {}).get("kiedy", "")).startswith("20")
            and "+00:00" in str((w or {}).get("kiedy")), w and w.get("kiedy"))
    okno = (w or {}).get("okno") or {}
    sprawdz("okno ma poczatek, koniec i dlugosc",
            okno.get("dni") == 30 and okno.get("od") < okno.get("do"), okno)
    sprawdz("wyswietlenia 850", p.get("wyswietlenia") == 850, p)
    sprawdz("osoby 96", p.get("osoby") == 96, p)
    sprawdz("zapisy z tabeli ruchu 6", p.get("zapisy_z_ruchu") == 6, p)
    sprawdz("zapisy z drzewa wzrostu 6", p.get("zapisy_ze_wzrostu") == 6, p)
    sprawdz("i oba adresy mowia to samo", p.get("zapisy_zgodne") is True, p)
    sprawdz("piec zapisow rozbite na CZTERY notki",
            p.get("zapisy_per_notka") == {"900000009": 1, "900000010": 1,
                                          "900000011": 1, "900000012": 2},
            p.get("zapisy_per_notka"))
    # 64 wobec 850 — panel liczy tu cos innego niz `visitor_sources`. Nie wiemy
    # czego i nie zgadujemy; zapisujemy obie, bo rozjazd sam w sobie informuje.
    sprawdz("druga, niezgodna liczba ruchu tez zapisana",
            p.get("ruch_ze_wzrostu") == 64, p)

    print()
    print("=== 1a. SUROWE LICZBY ZOSTAJA W PLIKU ===")
    # Podsumowanie jest wygoda; surowa odpowiedz jest jedyna czescia wiersza,
    # ktora przezyje przemianowanie pol po stronie Substacka.
    z_pliku = json.loads(linie()[0])
    sprawdz("surowa tabela ruchu w calosci", z_pliku.get("ruch") == RUCH)
    sprawdz("surowe drzewo zapisow w calosci", z_pliku.get("zapisy") == ZAPISY)
    sprawdz("da sie z niego przeliczyc zapisy bez ponownego odczytu",
            browser._zapisy_ogolem(z_pliku["zapisy"]) == 6)

    print()
    print("=== 2. TO SZEREG CZASOWY, NIE OSTATNIA WARTOSC ===")
    # Sens tej funkcji polega na tym, ze za tydzien bedzie siedem wierszy,
    # a nie na tych szesciu zapisach.
    browser.api_json = odpowiadaj(dict(RUCH, total=11), ZAPISY)
    browser.zapisz_zrodla_ruchu(page=Strona())
    sprawdz("drugi odczyt DOPISANY, nie nadpisany", len(linie()) == 2, len(linie()))
    sprawdz("pierwszy wiersz nietkniety",
            json.loads(linie()[0])["ruch"]["total"] == 9)
    sprawdz("drugi niesie nowa wartosc",
            json.loads(linie()[1])["ruch"]["total"] == 11)

    print()
    print("=== 3. ODPOWIEDZ POPRAWNA I PUSTA NIE ZAPISUJE ZERA ===")
    przed = len(linie())
    browser.api_json = odpowiadaj({"rows": [], "total": 0},
                                  {"sourceMetrics": [], "totals": []})
    pusty = browser.zapisz_zrodla_ruchu(page=Strona())
    sprawdz("pusta odpowiedz nie daje wiersza", pusty is None, pusty)
    sprawdz("i nic sie nie dopisalo", len(linie()) == przed, len(linie()))

    # POLOWA CISZY TEZ JEST CISZA. Gdy odpowiada tylko jedna tabela, wiersz
    # powstaje — ale liczba z tej drugiej ma byc `null`, nie 0. Zero znaczyloby
    # „zmierzylismy i nikt sie nie zapisal", a tego nie zmierzylismy.
    browser.api_json = odpowiadaj(RUCH, {"sourceMetrics": [], "totals": []})
    polowa = browser.zapisz_zrodla_ruchu(page=Strona()) or {}
    pp = polowa.get("podsumowanie") or {}
    sprawdz("polowiczny odczyt zapisuje sie", len(linie()) == przed + 1)
    sprawdz("i mowi, ktora polowa odpowiedziala",
            polowa.get("odczytane") == ["ruch"], polowa.get("odczytane"))
    sprawdz("brakujaca liczba to null, NIE zero",
            pp.get("zapisy_ze_wzrostu") is None, pp)
    sprawdz("rozbicie na notki tez null, nie pusty slownik",
            pp.get("zapisy_per_notka") is None, pp)
    sprawdz("kontrola krzyzowa nie udaje zgodnosci",
            pp.get("zapisy_zgodne") is None, pp)
    sprawdz("powod zapisany przy wierszu",
            "zapisy" in (polowa.get("blad") or {}), polowa.get("blad"))

    print()
    print("=== 4. 403, WYJATEK I BRAK SESJI NIE RZUCAJA ===")
    przed = len(linie())
    # 403 ze strona wyzwania: `api_json` oddaje wtedy `None`, bo tresc nie jest
    # JSON-em. `None` to „nie wiem", nie „zero".
    for opis, ruch_, zapisy_ in (
            ("403 na obu (None)", None, None),
            ("403 na jednej", RUCH, None),
            ("wyjatek nawigacji", TimeoutError("timeout"), TimeoutError("t")),
            ("odpowiedz nie tego typu", "Just a moment...", [1, 2, 3]),
            ("odpowiedz to liczba", 0, 0)):
        try:
            browser.api_json = odpowiadaj(ruch_, zapisy_)
            wy = browser.zapisz_zrodla_ruchu(page=Strona())
            ok = wy is None or isinstance(wy, dict)
        except BaseException as exc:            # takze SystemExit
            ok = False
            opis += " (RZUCILO %s)" % type(exc).__name__
        sprawdz("  %s -> bez wyjatku" % opis, ok)
    sprawdz("zaden z nich nie zapisal zera poza jednym polowicznym",
            len(linie()) == przed + 1, len(linie()) - przed)

    # BRAK SESJI. `wymagaj_sesji` rzuca `SystemExit`, a to NIE jest `Exception`
    # — samo `except Exception` przepuscilo by je i pomiar zabralby caly
    # przebieg. Tu funkcja otwiera sesje SAMA (page=None).
    przed = len(linie())

    def brak_sesji():
        raise SystemExit("Brak sesji Substacka.")

    browser.wymagaj_sesji = brak_sesji
    browser.podlacz_sie = lambda: (_ for _ in ()).throw(
        AssertionError("nie wolno tu dojsc"))
    try:
        wy = browser.zapisz_zrodla_ruchu()
        ok, opis = wy is None, wy
    except BaseException as exc:
        ok, opis = False, "RZUCILO %s" % type(exc).__name__
    sprawdz("brak sesji nie wywala przebiegu i nie zapisuje nic", ok, opis)

    browser.wymagaj_sesji = lambda: None
    browser.podlacz_sie = lambda: (_ for _ in ()).throw(
        RuntimeError("Chrome nie odpowiada"))
    try:
        wy = browser.zapisz_zrodla_ruchu()
        ok, opis = wy is None, wy
    except BaseException as exc:
        ok, opis = False, "RZUCILO %s" % type(exc).__name__
    sprawdz("padnieta przegladarka tez nie", ok, opis)
    sprawdz("i nadal ani jednej nowej linii", len(linie()) == przed, len(linie()))
    browser.wymagaj_sesji = stara_sesja
    browser.podlacz_sie = stare_podlacz

    print()
    print("=== 5. ZMIANA KSZTALTU: SUROWE ZOSTAJE, SUMY SA NULL ===")
    # Gdyby Substack przemianowal pola, wiersz ma nadal powstac — bo surowych
    # liczb nie da sie odzyskac pozniej, okno mija. Ale WYLICZONE sumy musza
    # wtedy mowic „nie wiem", a nie „zero".
    przed = len(linie())
    INNY = {"sourceMetrics": [{"source": "substack",
                               "wskazniki": [{"nazwa": "Zapisy", "razem": 6}],
                               "children": []}],
            "podsumowania": [{"nazwa": "zapisy", "razem": 6}]}
    browser.api_json = odpowiadaj({"wiersze": [{"zrodlo": "notes", "zapisy": 5}]},
                                  INNY)
    inny = browser.zapisz_zrodla_ruchu(page=Strona()) or {}
    ip = inny.get("podsumowanie") or {}
    sprawdz("wiersz mimo nieznanego ksztaltu powstal", len(linie()) == przed + 1)
    sprawdz("surowa odpowiedz zachowana w calosci",
            json.loads(linie()[-1]).get("zapisy") == INNY)
    sprawdz("suma zapisow to null, nie zero",
            ip.get("zapisy_ze_wzrostu") is None, ip)
    sprawdz("wyswietlenia to null, nie zero",
            ip.get("wyswietlenia") is None, ip)
    sprawdz("kontrola krzyzowa milczy, zamiast oglaszac zgodnosc",
            ip.get("zapisy_zgodne") is None, ip)

    print()
    print("=== 6. KONTRDOWOD: PRAWDZIWE ZERO MA SIE ZAPISAC ===")
    # Bramka z sekcji 3 odrzuca PUSTKE, nie zera. Dzien, w ktorym tabela ma
    # wiersze, a w nich same zera, JEST pomiarem — i gdyby wypadal z pliku,
    # zgubilibysmy dokladnie ten dzien, w ktorym ruch naprawde ustal.
    przed = len(linie())
    MARTWY = {"rows": [{"source": "direct", "source_category": "Direct",
                        "views": 0, "users": 0, "free_signup": 0,
                        "subscribed": 0}], "total": 1}
    browser.api_json = odpowiadaj(MARTWY, {"sourceMetrics": [],
                                           "totals": [{"name": "subscribers",
                                                       "total": 0}]})
    martwy = browser.zapisz_zrodla_ruchu(page=Strona()) or {}
    mp = martwy.get("podsumowanie") or {}
    sprawdz("wiersz z samymi zerami, ale REALNYMI, zapisany",
            len(linie()) == przed + 1, len(linie()) - przed)
    sprawdz("i zera sa zerami, nie nullami",
            mp.get("wyswietlenia") == 0 and mp.get("zapisy_z_ruchu") == 0, mp)

    print()
    print("=== 6a. LICZBA IDZIE Z `total`, NIE Z KONCA SZEREGU ===")
    # Galaz „substack other" ma szereg [6, 1] i `total` 1. Kod czytajacy szereg
    # zamiast `total` oddalby 6 — czyli szesciokrotnie zawyzyl jedno zrodlo
    # i rozbil zgodnosc obu adresow, ktora jest tu jedyna kontrola.
    galaz = ZAPISY["sourceMetrics"][0]["children"][0]
    sprawdz("galaz substack other -> 1 zapis, nie 6",
            browser._zapisy_wezla(galaz) == 1, browser._zapisy_wezla(galaz))

    print()
    print("=== 7. KONTRDOWOD: STARE POLE NIE ODPOWIADA NA TO PYTANIE ===")
    # Gdyby przypisanie zrodla dalo sie odczytac z tego, co juz zbieramy, ta
    # funkcja byla by zbedna. `signups_within_1_day` z panelu wydawcy liczy
    # OKNO CZASOWE i nie zna slowa „notka" — w rekordzie statystyk artykulu
    # nie ma ani zrodla, ani numeru notki.
    import statystyki
    rekord = statystyki.z_kart({})
    sprawdz("rekord statystyk nie ma zrodla zapisu",
            not [k for k in rekord if "zrodl" in k], sorted(rekord))
finally:
    browser.api_json = stare_api
    browser.ZRODLA = stare_zrodla
    browser.wymagaj_sesji = stara_sesja
    browser.podlacz_sie = stare_podlacz

print()
print("=== PRODUKCJA ===")
zle = 0
for p in PILNOWANE:
    ok = odcisk(p) == PRZED[str(p)]
    zle += 0 if ok else 1
    if not ok:
        print("  %-28s ZMIENIONA" % pathlib.Path(p).name)
nowe = [x for x in config.DATA_DIR.rglob("*")
        if x.is_file() and str(x) not in PRZED]
zle += len(nowe)
for x in nowe:
    print("  %-28s POWSTALA W PRODUKCJI" % x.name)
print("  %d plikow w agent-v2/data/ %s" %
      (len(PILNOWANE), "bez zmian" if not zle else "RUSZONYCH"))
print("  zrodla.jsonl w produkcji: %s"
      % ("nie ma i nie powstalo" if not (config.DATA_DIR / "zrodla.jsonl").exists()
         else "ISTNIEJE"))

print()
print("=== WYNIK: %d zdanych, %d oblanych%s ===" %
      (zdane, oblane, ", PRODUKCJA RUSZONA" if zle else ""))
sys.exit(1 if (oblane or zle) else 0)
