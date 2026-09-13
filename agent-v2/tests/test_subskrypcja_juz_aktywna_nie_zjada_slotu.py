# -*- coding: utf-8 -*-
"""Profil, ktory juz subskrybujemy, zostaje zapamietany i nie zjada slotu.

## Pomiar, ktory to wywolal

Produkcja, 12 wrzesnia 2026, przebieg z 13:30 — cztery proby subskrypcji:

    (przerwa 13.6 min przed kolejnym działaniem)
    darmowa subskrypcja juz aktywna — nie zmieniam planu
    (przerwa 7.5 min przed kolejnym działaniem)
    przycisk: 'Subscribe'  (subskrypcja)
    ZROBIONE
    (przerwa 10.0 min przed kolejnym działaniem)
    darmowa subskrypcja juz aktywna — nie zmieniam planu

Dzien skonczony na 2/4. Dwa sloty poszly na profile, ktore same odpowiedzialy,
ze juz je subskrybujemy.

## Dwie usterki w jednym miejscu

1. `_klik_na_profilu` wracal z tej galezi BEZ WPISU w dzienniku. Przeglad
   dziennika od 7 wrzesnia: 14 udanych subskrypcji, 105 pominiec za rozmiar,
   8 porazek — i ani jednego slowa o tych dwoch wejsciach. A
   `kogo_juz_subskrybujemy` zamyka tylko to, co w dzienniku stoi.
2. Blok w `run.py` w ogole nie czytal wyniku `zasubskrybuj`. Kazde wejscie
   bylo `proby += 1`, wiec profil, ktory niczego nie przyjal, zjadal slot
   tak samo jak subskrypcja, ktora weszla.

BEZ PYTESTA, bez sieci, bez przegladarki. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_subskrypcja_juz_aktywna_nie_zjada_slotu.py
"""
import ast
import io
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import browser   # noqa: E402
import config    # noqa: E402
import run       # noqa: E402

browser.wymagaj_wlasciwego_konta = lambda page: None

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
    def __init__(self, dostepne):
        self.dostepne = dostepne

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


def wpisy():
    if not browser.DZIENNIK.exists():
        return []
    return [json.loads(l) for l in browser.DZIENNIK.read_text(encoding="utf-8")
            .splitlines() if l.strip()]


oryg = (browser.podlacz_sie, browser.wymagaj_sesji, browser.DZIENNIK,
        browser.naprawde_wyslac)


def ustaw(dostepne):
    klikniete.clear()
    s = Strona(dostepne)
    browser.wymagaj_sesji = lambda: None
    browser.podlacz_sie = lambda: (Kontekst(s), Kontekst(s), Kontekst(s))
    browser.naprawde_wyslac = lambda wyslij, co: wyslij
    browser.DZIENNIK = pathlib.Path(tempfile.mkdtemp()) / "d.jsonl"


try:
    print("=== 1. PROFIL MOWI „JUZ SUBSKRYBUJESZ\" — WPIS ZOSTAJE ===")
    ustaw({"Upgrade", "Message"})
    w = browser.zasubskrybuj("juznasz", wyslij=True)
    sprawdz("wynik mowi, ze to juz nasza subskrypcja",
            w.get("juz_subskrybowany") and w.get("pominiete"), w)
    sprawdz("z powodem ze stalej", w.get("powod") == browser.POWOD_JUZ_SUBSKRYBOWANY,
            w.get("powod"))
    sprawdz("niczego nie kliknieto", klikniete == [], klikniete)
    d = wpisy()
    sprawdz("w dzienniku jest dokladnie jeden wpis", len(d) == 1, d)
    sprawdz("to pominiecie, nie subskrypcja (nie liczy sie do normy)",
            d and d[0].get("rodzaj") == "subskrypcja_pominieta", d)
    sprawdz("z uchwytem i powodem",
            d and d[0].get("komu") == "juznasz"
            and d[0].get("powod") == browser.POWOD_JUZ_SUBSKRYBOWANY, d)

    # KONTRDOWOD: tryb sprawdzenia nie pisze do dziennika.
    ustaw({"Upgrade", "Message"})
    browser.zasubskrybuj("juznasz", wyslij=False)
    sprawdz("proba sucha nie zostawia wpisu", wpisy() == [], wpisy())

    # KONTRDOWOD: zwykly profil nadal subskrybuje normalnie. Rozmiar sprawdza
    # sie z JSON-a, wiec wylaczamy sufit — ten test nie jest o rozmiarze.
    sufit = config.SUBSKRYPCJE_MAX_ODBIORCOW
    config.SUBSKRYPCJE_MAX_ODBIORCOW = None
    try:
        ustaw({"Subscribe", "Message"})
        w = browser.zasubskrybuj("nowy", wyslij=True)
    finally:
        config.SUBSKRYPCJE_MAX_ODBIORCOW = sufit
    sprawdz("profil bez subskrypcji dostaje klikniecie 'Subscribe'",
            klikniete == ["Subscribe"], klikniete)
    sprawdz("i nie jest oznaczony jako juz nasz", not w.get("juz_subskrybowany"), w)

    print()
    print("=== 2. PAMIEC CZYTA TEN WPIS ===")
    browser.DZIENNIK = pathlib.Path(tempfile.mkdtemp()) / "d.jsonl"
    browser.DZIENNIK.write_text("\n".join(json.dumps(x) for x in [
        {"rodzaj": "subskrypcja_pominieta", "udane": True, "komu": "juznasz",
         "powod": browser.POWOD_JUZ_SUBSKRYBOWANY},
        {"rodzaj": "subskrypcja_pominieta", "udane": True, "komu": "wielki",
         "powod": browser.POWOD_ZA_DUZY},
        {"rodzaj": "subskrypcja", "udane": True, "komu": "zrobiony"},
        {"rodzaj": "subskrypcja", "udane": False, "komu": "timeout",
         "powod": "TimeoutError: Timeout"},
    ]) + "\n", encoding="utf-8")
    zamkniete = run.kogo_juz_subskrybujemy()
    sprawdz("profil „juz subskrybujesz\" jest zamkniety", "juznasz" in zamkniete,
            zamkniete)
    sprawdz("udana subskrypcja nadal zamyka", "zrobiony" in zamkniete, zamkniete)
    # KONTRDOWODY — pamiec nie moze zamykac za duzo.
    sprawdz("za duzy NIE jest zamkniety na zawsze (tym sie zajmuje znane_za_duze)",
            "wielki" not in zamkniete, zamkniete)
    sprawdz("awaria po naszej stronie NIE zamyka", "timeout" not in zamkniete,
            zamkniete)
finally:
    (browser.podlacz_sie, browser.wymagaj_sesji, browser.DZIENNIK,
     browser.naprawde_wyslac) = oryg

print()
print("=== 3. BLOK W run.py CZYTA WYNIK I NIE LICZY POMINIECIA JAKO PROBY ===")
ZRODLO = io.open("agent-v2/run.py", encoding="utf-8").read()
CIALO = ""
for w in ast.walk(ast.parse(ZRODLO)):
    if isinstance(w, ast.FunctionDef) and w.name == "subskrybuj":
        CIALO = ast.get_source_segment(ZRODLO, w) or ""
drzewo = ast.parse(CIALO)
sprawdz("blok subskrypcji znaleziony", bool(CIALO))


def _wola_zasubskrybuj(wezel):
    return any(isinstance(x, ast.Call) and isinstance(x.func, ast.Attribute)
               and x.func.attr == "zasubskrybuj" for x in ast.walk(wezel))


# PO DRZEWIE SKLADNI: wynik wywolania ma trafic do zmiennej. Samodzielne
# wyrazenie `browser.zasubskrybuj(...)` to dokladnie ta usterka.
gole = [x for x in ast.walk(drzewo)
        if isinstance(x, ast.Expr) and _wola_zasubskrybuj(x)]
przypisane = [x for x in ast.walk(drzewo)
              if isinstance(x, ast.Assign) and _wola_zasubskrybuj(x)]
sprawdz("wynik zasubskrybuj nie jest wyrzucany", not gole, len(gole))
sprawdz("tylko trafia do zmiennej", len(przypisane) == 1, len(przypisane))

# Galaz `if <wynik>.get("pominiete")` konczy sie `continue`, a `proby += 1`
# stoi dopiero PO niej.
galaz = None
for x in ast.walk(drzewo):
    if (isinstance(x, ast.If) and "pominiete" in ast.dump(x.test)
            and any(isinstance(k, ast.Continue) for k in x.body)):
        galaz = x
sprawdz("jest galaz pominiecia z `continue`", galaz is not None)
if galaz is not None:
    w_galezi = ast.dump(ast.Module(body=galaz.body, type_ignores=[]))
    sprawdz("galaz NIE liczy proby", "proby" not in w_galezi)
    sprawdz("galaz zapamietuje uchwyt na reszte przebiegu",
            "zamkniete" in w_galezi)
    sprawdz("i mowi, co sie stalo, zanim pojdzie dalej",
            any(isinstance(k, ast.Expr) and isinstance(k.value, ast.Call)
                and getattr(k.value.func, "id", "") == "print"
                for k in galaz.body))
    linia_galezi = galaz.lineno
    linie_proby = [x.lineno for x in ast.walk(drzewo)
                   if isinstance(x, ast.AugAssign)
                   and getattr(x.target, "id", "") == "proby"]
    sprawdz("`proby += 1` przy wysylce stoi po galezi pominiecia",
            any(l > linia_galezi for l in linie_proby), (linia_galezi, linie_proby))

# PRZERWA: po wejsciu, ktore niczego nie kliknelo, nastepny kandydat nie czeka
# drugi raz — ale przerwa przed pierwszym wejsciem zostaje.
sprawdz("rytm nadal stoi przed wejsciem na profil",
        'rytm("komentarz", "subskrypcje"' in CIALO)
sprawdz("i jest pomijany tylko po odczekanej, pustej przerwie",
        "przerwa_odczekana" in CIALO)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
