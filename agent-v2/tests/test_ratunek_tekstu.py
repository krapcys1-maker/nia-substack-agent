# -*- coding: utf-8 -*-
"""Pusty budzet ma URATOWAC gotowy tekst — nie publikujac go i NIE WCHODZAC
do korpusu, po ktorym globuje i selectuje reszta systemu.

CO BYLO ZLE, RUNDA PIERWSZA. W `artykul_z_puli.py` `stages.review` stoi w linii
~1215, a zapis dopiero ~1291. Gdy budzet (`RUN_LIMIT_USD` 1,60 /
`DAILY_LIMIT_USD`) albo `KILL_SWITCH=true` przerywa NA RECENZJI, `raise` leci
PRZED zapisem — wiec gotowy artykul, za ktory zaplacono okolo 0,76 USD za samo
pisanie na Fable, nie trafial nawet na dysk.

CO BYLO ZLE, RUNDA DRUGA — i o tym jest wiekszosc tego pliku. Pierwszy ratunek
wolal `stages.save`, czyli pisal do `config.ARTICLES_DIR` i wstawial wiersz do
`articles`. Tekst przezywal i od razu zaczynal byc liczony jako ARTYKUL przez
szesciu czytelnikow, z ktorych ZADEN nie filtruje po statusie. Zmierzone w tym
pliku, na prawdziwych funkcjach, katalogu i bazie w `tempfile`:

                                              korpus   + ratunek    + ratunek
                                              4 art.   do articles  obok (dzis)
  stages.ostatnie_uwagi — zarzutow do pisarza     6          3           6
  stages.poprzednie_teksty — tekstow do formy     4          4           4
    w tym: czy najstarszy jest jeszcze w oknie   TAK        NIE         TAK
  gates.powtorzona_forma na blizniaku          6 z 6      MILCZY      6 z 6
  stages.tematy_do_porownania — pamiec powtorek   4          5           4
    czy temat uratowanego jest juz „spalony"      NIE       TAK         NIE
  stages.recent_angles — katow przybylo           —         +1           0
  audyt_systemu: bramek padajacych zawsze         1          0           1
  wierszy w `articles`                            4          5           4
  plikow w `ARTICLES_DIR`                         8         10           8

Trzeci slupek to stan po tej zmianie i jest RUBRYKA W RUBRYKE rowny pierwszemu.
O to chodzilo: nie o to, gdzie plik lezy, tylko o to, ze czytelnicy go nie
widza.

Najostrzejszy jest wiersz czwarty i osmy:
  `gates.powtorzona_forma` — uratowany plik zajmowal jedno z czterech miejsc
    (`ILE_TEKSTOW_DO_POROWNANIA_FORMY`) i wypychal z okna artykul, ktorego
    szkielet nowy tekst powtarzal 6 cechami na 6. Sam odezwac sie nie mogl:
    ramka blokujaca przestawia `gates.odcisk_formy` w DWOCH cechach z szesciu
    (`otwarcie` = „>" zamiast pierwszego slowa akapitu, `liczba_w_otwarciu`
    = True, bo w ramce stoi „0,76 USD"), a prog to piec z szesciu.
  `audyt_systemu.py:323/330/334` — kontrdowod na martwa bramke ginal NA STALE.
    `:323` liczy kazdy artykul z niepustymi `notes` (uratowany ma zawsze dwie),
    `:330` przy zliczaniu bramek pomija dokladnie `DLUGOSC` i `RECENZJA`.
    Mianownik rosl, licznik nie, wiec warunku `i == z_uwagami` nie spelnialaby
    juz zadna bramka — dopoki wiersz siedzi w `articles`, czyli zawsze.

DECYZJA: ratunek pisze komplet plikow do katalogu SIOSTRZANEGO wobec
`ARTICLES_DIR` (`data/artykuly-przerwane/`) i NIE WSTAWIA WIERSZA DO `articles`.
`_ratuj_tekst` nie dostaje juz nawet `conn` — funkcja bez uchwytu do bazy nie
ma jak niczego do niej dopisac. Cena jest jedna i jawna: `bank_fragmentow`
czyta `articles.evidence`, wiec nie zobaczy `unused_evidence` z tej karty.
Dlatego karta ladzie obok tekstu jako `.karta.json`, w ksztalcie, ktory czyta
`--z-karty` — material nie jest skasowany, tylko czeka na czlowieka.

CZEGO TO NIE ZMIENIA, i to jest wazniejsze. Regresja `e88b456` — `except
Exception` polykajace `llm.BudgetExceeded` i `llm.PreflightFailed` — o wlos nie
wypuscila artykulu bez recenzji na Substacka. Ratunek NIE MOZE otworzyc tej
drogi z powrotem: `stages.grafika` i `stages.zweryfikuj` wolaja modele, wiec
przy pustym budzecie nie wolno ich nawet probowac, a `browser.wystaw_artykul`
stoi za `raise` i ma pozostac nieosiagalny.

                                      64d881a       do articles   dzis
    wystaw_artykul(wyslij=True)       nie wolane    nie wolane    nie wolane
    stages.grafika                    nie wolane    nie wolane    nie wolane
    stages.zweryfikuj                 nie wolane    nie wolane    nie wolane
    wyjatek z `_napisz_i_zapisz`      BudgetExc.    BudgetExc.    BudgetExc.
    `finish_run` po `main`            1x ERROR      1x ERROR      1x ERROR
    tekst na dysku                    NIE           TAK           TAK
    plikow w `ARTICLES_DIR`           0             2             0
    wierszy w `articles`              0             1             0

TEST MIERZY ZACHOWANIE, NIE TRESC ZRODLA. Zero asercji typu `"..." in ZRODLO`.
Kazde twierdzenie to wynik wywolania na atrapach etapow PLATNYCH i sprawdzenie,
co naprawde powstalo:
  ramke w pliku czyta PRAWDZIWY `browser.rozbierz_artykul`, wiec „blokujaca"
    znaczy zmierzone, a nie zadeklarowane;
  cztery skutki uboczne mierza PRAWDZIWE `stages.ostatnie_uwagi`,
    `stages.poprzednie_teksty`, `stages.tematy_do_porownania`,
    `stages.recent_angles` i `gates.powtorzona_forma` — na tym samym katalogu
    i tej samej bazie, PRZED ratunkiem i PO nim;
  wariant odrzucony (zapis do `ARTICLES_DIR` przez `stages.save`) jest
    ODTWORZONY, nie opisany — te same prawdziwe funkcje pokazuja, co by sie
    stalo. Jedyny wyjatek to arytmetyka `audyt_systemu.py:320-334`, przepisana
    do `kontrdowod_audytu`, bo `audyt_systemu.main()` czyta produkcyjna baze
    i wola `browser`.

BEZ PYTESTA, zero platnych wywolan, zero sieci, produkcyjna baza i produkcyjny
katalog artykulow NIETKNIETE (`config.ARTICLES_DIR` podmieniany na podkatalog
w `tempfile` i przywracany w `finally`; katalog ratunku liczy sie z niego, wiec
przestawia sie tym samym ruchem). Uruchamiac z korzenia:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_ratunek_tekstu.py

KONTRDOWOD JEST ODTWORZONY, nie opisany: `git show
64d881a:agent-v2/artykul_z_puli.py` ladzi do katalogu tymczasowego i przechodzi
PRZEZ TEN SAM harness. Wersja odniesienia jest PRZYPIETA DO SHA `64d881a`, a
nie do `HEAD` — test mierzacy sie wzgledem `HEAD` traci sens w chwili commita,
ktorego strzeze. Zaden warunek nie zna dzisiejszej daty; znaczniki czasu plikow
sa ustawiane na sztywno (`ZEGAR`), bo `ostatnie_uwagi` sortuje po `mtime`, a
dwa pliki zapisane w tej samej milisekundzie daly by kolejnosc losowa.
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from collections import Counter

sys.path.insert(0, "agent-v2")
import browser as prawdziwy_browser   # noqa: E402
import config                         # noqa: E402
import db as prawdziwe_db             # noqa: E402
import gates as prawdziwe_gates       # noqa: E402
import llm                            # noqa: E402
import stages as prawdziwe_stages     # noqa: E402

# HISTORIA JEST WARUNKIEM TEGO TESTU. Kontrdowod ponizej odtwarza sie
# z commita sprzed naprawy, wiec w kopii z historia zalozona od nowa
# nie ma z czego go odtworzyc. Pominiecie jest wtedy JAWNE, zamiast
# wywalac sie w polowie pliku na `CalledProcessError`.
import historia   # noqa: E402
historia.wymaga_historii("64d881a")

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


PILNOWANE = [pathlib.Path("agent-v2/artykul_z_puli.py"),
             pathlib.Path("agent-v2/stages.py"),
             pathlib.Path("agent-v2/gates.py"),
             pathlib.Path("agent-v2/browser.py"),
             pathlib.Path("agent-v2/db.py"),
             pathlib.Path("agent-v2/config.py"),
             pathlib.Path("agent-v2/audyt_systemu.py"),
             pathlib.Path(config.DB_PATH),
             config.DATA_DIR / "dziennik.jsonl"]
PRZED = {str(p): odcisk(p) for p in PILNOWANE}
ARTYKULY_PRZED = sorted(p.name for p in config.ARTICLES_DIR.glob("*"))
KATALOG_RATUNKU_PROD = config.ARTICLES_DIR.parent / "artykuly-przerwane"
RATUNEK_PROD_PRZED = (sorted(p.name for p in KATALOG_RATUNKU_PROD.glob("*"))
                      if KATALOG_RATUNKU_PROD.exists() else None)

ZRODLO_TERAZ = pathlib.Path("agent-v2/artykul_z_puli.py").resolve()

# --- wersja sprzed zmiany, ODTWORZONA, nie opisana -------------------------
# SHA, nie `HEAD`: `HEAD` przesuwa sie z commitem, ktory ten test strzeze, wiec
# kontrdowod zgaslby dokladnie w chwili, w ktorej zaczyna byc potrzebny.
POPRZEDNIA_WERSJA = "64d881a"
KAT = pathlib.Path(tempfile.mkdtemp())
STARE = KAT / ("artykul_z_puli_%s.py" % POPRZEDNIA_WERSJA)
STARE.write_bytes(subprocess.check_output(
    ["git", "show", "%s:agent-v2/artykul_z_puli.py" % POPRZEDNIA_WERSJA]))

# Znacznik czasu wpisywany plikom na sztywno. `stages.ostatnie_uwagi` sortuje
# po `mtime`, a cztery pliki zapisane w tej samej milisekundzie ustawilyby sie
# w kolejnosci systemu plikow — czyli raz tak, raz tak. Stala, nie „teraz":
# test nie ma prawa zalezec od dzisiejszej daty.
ZEGAR = 1_700_000_000

# Etapy PLATNE w kolejnosci, w jakiej wola je `_napisz_i_zapisz`. Gdy budzet
# wyczerpie sie na ktoryms, `llm._preflight` wywraca KAZDE nastepne wywolanie —
# wiec atrapa tez, inaczej modelowalaby dzien, ktory nie istnieje.
PLATNE = ["warto_pisac", "write", "review", "ocen_forme", "grafika", "zweryfikuj"]

KARTA = {"working_thesis": "Kto ustawil ten uklad i za czyje pieniadze.",
         "confirmed_claims": [{"claim": "x", "evidence": "y",
                               "url": "https://przyklad.example/a"}],
         "unused_evidence": [{"url": "https://przyklad.example/b",
                              "excerpts": ["Fragment dosc dlugi, zeby bank go"
                                           " przyjal, bo prog to szescdziesiat"
                                           " znakow i tyle."]}],
         "source_dates": {"newest": "2026-08-20", "oldest": "2026-08-01"}}
BRIEF = {"title": "The Meter That Reads Itself",
         "question": "Who decided the meter reads itself?"}
TYTUL = "The Meter That Reads Itself"
# 650 slow, czyli pasmo SINGLE — tyle wlasnie kosztuje okolo 0,76 USD pisania.
# Slowa musza byc ROZNE, zeby dalo sie sprawdzic, ze na dysk trafil TEN tekst,
# a nie jego kawalek: powtarzane „word" pasowaloby do dowolnego wycinka.
TRESC = " ".join("slowo%d" % i for i in range(650))


def _rzucaj(fabryka):
    def _f(*a, **k):
        raise fabryka()
    return _f


class AtrapaStages:
    """Atrapa etapow PLATNYCH. `save` jest prawdziwe — patrz naglowek pliku."""

    # Czyste funkcje ida do PRAWDZIWEGO `stages` — nie wolaja modelu ani bazy.
    @staticmethod
    def wstaw_date_zrodel(tekst, card):
        import stages as _s
        return _s.wstaw_date_zrodel(tekst, card)

    # ZNACZNIK NIEWYSTAWIONEGO ARTYKULU — czyste operacje na pliku, wiec ida
    # do prawdziwego `stages` zgodnie z zasada opisana wyzej. Produkcji nie
    # tkna: `zapamietaj_niewystawiony` ma wlasna zapore na `config.W_TESCIE`.
    @staticmethod
    def zapamietaj_niewystawiony(sciezka, powod):
        import stages as _s
        return _s.zapamietaj_niewystawiony(sciezka, powod)

    @staticmethod
    def zapomnij_niewystawiony():
        import stages as _s
        return _s.zapomnij_niewystawiony()

    @staticmethod
    def niewystawiony_artykul():
        import stages as _s
        return _s.niewystawiony_artykul()

    @staticmethod
    def odnotuj_probe_artykulu(powod):
        import stages as _s
        return _s.odnotuj_probe_artykulu(powod)

    def __init__(self, slad, pada_na, fabryka, budzet_wyczerpany, conn):
        self.slad = slad
        self.pada_na = pada_na
        self.fabryka = fabryka
        self.budzet = budzet_wyczerpany
        self.conn = conn
        self.zapisy = []
        self._od = PLATNE.index(pada_na) if pada_na in PLATNE else len(PLATNE)
        self._padlo = 0

    def _moze_paso(self, etap):
        if etap == self.pada_na:
            self._padlo += 1
            # ZWYKLA AWARIA PADA RAZ — zly JSON to jedno nieudane wywolanie, a
            # nie stan konta. Inaczej „powtorka pisarza" nie mialaby jak sie
            # udac i mierzylibysmy wylacznie sama atrape.
            return self.budzet or self._padlo == 1
        return self.budzet and PLATNE.index(etap) > self._od

    def _licz(self, etap):
        self.slad.append(etap)
        if self._moze_paso(etap):
            raise self.fabryka()

    # --- etapy platne ---
    def warto_pisac(self, conn, run_id, card):
        self._licz("warto_pisac")
        return {"werdykt": "PISZ", "ile_filarow": 3, "powod": "jest luka",
                "filary": {"named_decider": True, "felt_number": True,
                           "second_domain": True},
                "przekonanie": True, "stawka": True}

    def write(self, conn, run_id, card, glebokosc):
        self._licz("write")
        return {"title": TYTUL, "subtitle": "podtytul", "body": TRESC}

    def review(self, conn, run_id, card, draft):
        self._licz("review")
        return {"sentences": [], "unsupported_facts": [],
                "summary": "recenzja czysta"}

    def ocen_forme(self, conn, run_id, draft):
        self._licz("ocen_forme")
        return {"beliefs": [], "support_only": [], "reader_moment": {}}

    def grafika(self, conn, run_id, draft, sciezka_artykulu=None):
        self._licz("grafika")

    def zweryfikuj(self, conn, run_id, tekst, kontekst=""):
        self._licz("zweryfikuj")
        return {"claims": [], "safe_to_post": True, "verdict": "przechodzi"}

    # --- etapy bezplatne ---
    def poprzednie_teksty(self, pomin_tresc=""):
        return []

    def swiezosc_karty(self, card):
        return []

    def bank_fragmentow(self, conn):
        return []

    def save(self, conn, run_id, brief, card, draft, status, blokada, notatki):
        """PRAWDZIWY zapis — plik, wiersz w `articles`, prawdziwy status.

        Gdyby to byla atrapa oddajaca sciezke, test dowodzilby wylacznie tego,
        ze kod wola funkcje o nazwie `save`. Pytanie brzmi „czy tekst jest na
        dysku i czy da sie go opublikowac", a na to odpowiada tylko plik.
        """
        self.slad.append("save")
        self.zapisy.append({"status": status, "blokada": blokada,
                            "notatki": notatki})
        return prawdziwe_stages.save(self.conn, run_id, brief, card, draft,
                                     status, blokada, notatki)


class AtrapaGates:
    def deterministic_floors(self, tresc, card, poprzednie=None):
        return []

    def uwagi_z_formy(self, forma, tresc):
        return []

    def verdict(self, uwagi):
        return "SAVED", ""

    def pozycja_w_tekscie(self, moment, tresc):
        return None


class AtrapaBrowser:
    def __init__(self, slad):
        self.slad = slad
        self.wystawienia = []

    def wystaw_artykul(self, sciezka, wyslij=False):
        self.slad.append("wystaw_artykul")
        self.wystawienia.append({"sciezka": str(sciezka), "wyslij": wyslij})
        return {"wyslane": True, "blad": None}


class AtrapaDb:
    def __init__(self):
        self.zamkniecia = []

    def connect(self):
        return object()

    def start_run(self, conn, nazwa):
        return 4242

    def finish_run(self, conn, run_id, status, etap=None, uwaga=None):
        self.zamkniecia.append({"status": status, "etap": etap, "uwaga": uwaga})


_licznik = [0]


def zaladuj(sciezka):
    """Wczytuje BADANY plik pod wlasna nazwa, zeby obie wersje zyly naraz.

    `config`, `db`, `llm` i `stages` siedza juz w `sys.modules`, wiec `import`
    w badanym pliku bierze je stamtad. `llm` zostaje PRAWDZIWY: to z niego
    badany kod bierze klasy wyjatkow, a podmiana ich na wlasne zamienilaby
    test w tautologie.
    """
    _licznik[0] += 1
    nazwa = "azp_ratunek_%d" % _licznik[0]
    spec = importlib.util.spec_from_file_location(nazwa, str(sciezka))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nazwa] = mod
    spec.loader.exec_module(mod)
    return mod


def nowy_teren():
    """Katalog artykulow i katalog ratunku POD JEDNYM korzeniem tymczasowym.

    `_katalog_ratunku` liczy sie z `ARTICLES_DIR.parent`, wiec wystarczy, ze
    katalog artykulow jest PODKATALOGIEM tymczasowego — jedno przestawienie
    przenosi oba i nie ma jak zapisac czegokolwiek do produkcyjnego `data/`.
    """
    korzen = pathlib.Path(tempfile.mkdtemp())
    (korzen / "articles").mkdir()
    return korzen


_run_id = [90]


def przebieg(sciezka, pada_na, fabryka, budzet_wyczerpany=True, wyslij=True):
    """Jeden `_napisz_i_zapisz` na SWOIM terenie i SWOJEJ bazie."""
    _run_id[0] += 1
    run_id = _run_id[0]
    korzen = nowy_teren()
    conn = prawdziwe_db.connect(korzen / "t.db")
    slad = []
    st = AtrapaStages(slad, pada_na, fabryka, budzet_wyczerpany, conn)
    br = AtrapaBrowser(slad)
    stare_moduly = {k: sys.modules.get(k) for k in ("gates", "browser")}
    stary_argv = sys.argv[:]
    stary_model = dict(config.MODEL_FOR)
    stary_kat = config.ARTICLES_DIR
    sys.modules["gates"] = AtrapaGates()
    sys.modules["browser"] = br
    sys.argv = ["artykul_z_puli.py"] + (["--wyslij"] if wyslij else [])
    config.ARTICLES_DIR = korzen / "articles"
    mod = zaladuj(sciezka)
    mod.stages = st
    wyjatek = None
    kod = None
    try:
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            kod = mod._napisz_i_zapisz(conn, run_id, dict(BRIEF), dict(KARTA))
    except BaseException as exc:   # noqa: BLE001 — mierzymy, co wylatuje
        wyjatek = exc
    finally:
        model_po = config.MODEL_FOR.get("write")
        config.ARTICLES_DIR = stary_kat
        sys.argv = stary_argv
        config.MODEL_FOR.clear()
        config.MODEL_FOR.update(stary_model)
        for k, v in stare_moduly.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v
    wiersze = [dict(r) for r in conn.execute(
        "SELECT run_id, title, body, status, blocked_by, notes FROM articles")]
    conn.close()
    kat = korzen / "articles"
    ratkat = korzen / "artykuly-przerwane"
    md = sorted(p for p in kat.glob("*.md") if not p.name.endswith(".uwagi.md"))
    ratunek = sorted(ratkat.glob("*.md")) if ratkat.exists() else []
    return {"slad": slad, "wyjatek": wyjatek, "kod": kod, "kat": kat,
            "korzen": korzen, "ratkat": ratkat, "ratunek": ratunek,
            "wystawienia": br.wystawienia, "ekran": buf.getvalue(),
            "model_po": model_po, "zapisy": st.zapisy, "wiersze": wiersze,
            "md": md, "run_id": run_id, "modul": mod,
            "uwagi": sorted(kat.glob("*.uwagi.md"))}


def tresc_pliku(pliki):
    """Tresc pierwszego pliku albo pusty napis.

    KONTRDOWOD MA DAWAC LICZBE, NIE STOS. Na wersji sprzed zmiany zaden plik
    nie powstaje, wiec `pliki[0]` rzucaloby IndexError i caly przebieg
    konczylby sie wywrotka w polowie — zamiast policzonymi oblanymi asercjami,
    ktore dopiero pokazuja, ILE rzeczy ta zmiana zalatwia.
    """
    return pliki[0].read_text(encoding="utf-8") if pliki else ""


def szkic(pliki):
    """PRAWDZIWY `browser.rozbierz_artykul` albo pusty szkic, gdy pliku brak."""
    if not pliki:
        return {"tytul": "", "podtytul": "", "html": ""}
    return prawdziwy_browser.rozbierz_artykul(pliki[0])


def pierwszy(lista, domyslne=None):
    return lista[0] if lista else (domyslne if domyslne is not None else {})


def budzet():
    return llm.BudgetExceeded(
        "limit dzienny toru 'produkcja' wyczerpany: 5.0100 / 5.0 USD")


def wylacznik():
    return llm.PreflightFailed("KILL_SWITCH=true — wywolania wstrzymane")


def zwykla():
    return ValueError("Extra data: line 1 column 1866")


print("=== 1. BUDZET PADA NA RECENZJI — TEKST MA PRZEZYC ===")
teraz = przebieg(ZRODLO_TERAZ, "review", budzet)

# (a) NIENARUSZALNE: nic nie poszlo na zewnatrz.
sprawdz("(a) `browser.wystaw_artykul` nie zostal zawolany ANI RAZU",
        teraz["wystawienia"] == [] and "wystaw_artykul" not in teraz["slad"],
        teraz["wystawienia"])
# (d) grafika i zweryfikuj wolaja modele — przy pustym budzecie ani jednego.
sprawdz("(d) `stages.grafika` nie zostalo zawolane",
        "grafika" not in teraz["slad"], teraz["slad"])
sprawdz("(d) `stages.zweryfikuj` nie zostalo zawolane",
        "zweryfikuj" not in teraz["slad"], teraz["slad"])
# (b) tekst na dysku — ale NIE w katalogu artykulow.
sprawdz("(b) plik z tekstem ISTNIEJE na dysku", len(teraz["ratunek"]) == 1,
        [p.name for p in teraz["ratunek"]])
sprawdz("(b) i lezy POZA katalogiem artykulow — ten zostal PUSTY",
        sorted(p.name for p in teraz["kat"].glob("*")) == [],
        [p.name for p in teraz["kat"].glob("*")])
TEKST = tresc_pliku(teraz["ratunek"])
sprawdz("(b) i niesie CALY uratowany tekst, nie ogryzek",
        TRESC in " ".join(TEKST.split()),
        "%d slow w pliku" % len(TEKST.split()))
sprawdz("(b) razem z sekcja `## Sources`, wiec da sie sprawdzic zrodla",
        "https://przyklad.example/a" in TEKST, TEKST[-200:])
sprawdz("(b) `stages.save` nie zostalo zawolane ANI RAZU — ratunek nie tyka"
        " bazy", "save" not in teraz["slad"] and teraz["zapisy"] == [],
        teraz["slad"])

print()
print("=== 2. ADNOTACJA JEST JAWNA I NAPRAWDE BLOKUJE ===")
sprawdz("(c) PIERWSZA linia pliku mowi NIE PUBLIKOWAC",
        TEKST.splitlines()[:1] and TEKST.splitlines()[0].startswith(
            "# NIE PUBLIKOWAC"), TEKST.splitlines()[:1])
sprawdz("(c) adnotacja niesie POWOD przerwania z nazwa wyjatku",
        "BudgetExceeded" in TEKST and "recenzji" in TEKST,
        TEKST[:400])
sprawdz("(c) i mowi wprost, ze tekst jest niesprawdzony",
        "NIESPRAWDZONY" in TEKST, TEKST[:400])
sprawdz("(c) wylicza kontrole, ktorych NIE bylo — z recenzja na czele",
        "recenzja" in TEKST and "sprawdzenie faktow" in TEKST, TEKST[:600])
# NAJWAZNIEJSZE W TEJ SEKCJI: „blokujaca" zmierzone, nie zadeklarowane.
# `browser.rozbierz_artykul` bierze pierwsza linie pliku jako TYTUL, wiec
# dopoki ramka stoi, reczne wystawienie tego pliku wyszloby z tytulem
# „NIE PUBLIKOWAC..." — awaria widoczna z ekranu, a nie cicha.
rozebrany = szkic(teraz["ratunek"])
sprawdz("(c) PRAWDZIWY `browser.rozbierz_artykul` widzi tytul NIE PUBLIKOWAC",
        rozebrany["tytul"].startswith("NIE PUBLIKOWAC"), rozebrany["tytul"])
sprawdz("(c) czyli wlasciwy tytul NIE jest tytulem szkicu",
        rozebrany["tytul"] != TYTUL, rozebrany["tytul"])
sprawdz("(c) ale sam tekst w szkicu nadal by byl — ramka nic nie kasuje",
        "slowo649" in rozebrany["html"], rozebrany["html"][-160:])

print()
print("=== 3. DA SIE TO ZNALEZC — TRZY DROGI, NIE ZERO ===")
# Plik bez czytelnika to ten sam sygnal produkowany i wyrzucany, ktory tepimy
# w calym tym audycie. Skoro tekst wyszedl z katalogu artykulow, musi byc
# powiedziane, GDZIE jest — inaczej ratunek jest tylko innym rodzajem kosza.
sprawdz("(1) log przebiegu podaje pelna sciezke pliku",
        str(teraz["ratunek"][0]) in teraz["ekran"] if teraz["ratunek"] else False,
        teraz["ekran"][-400:])
sprawdz("(1) i mowi wprost, gdzie szukac",
        "SZUKAJ TEGO W:" in teraz["ekran"] and str(teraz["ratkat"])
        in teraz["ekran"], teraz["ekran"][-400:])
sprawdz("(2) ramka w pliku podaje katalog, w ktorym plik lezy",
        str(teraz["ratkat"]) in TEKST, TEKST[:900])
SPIS_P = teraz["ratkat"] / "CZYTAJ_TO.txt"
sprawdz("(3) w katalogu lezy spis, ktory tlumaczy, co to za pliki",
        SPIS_P.exists(), [p.name for p in teraz["ratkat"].glob("*")])
SPIS_T = SPIS_P.read_text(encoding="utf-8") if SPIS_P.exists() else ""
sprawdz("(3) spis mowi, ze nic stad NIE PRZESZLO kontroli",
        "NICZEGO NIE PRZESZEDL" in SPIS_T, SPIS_T[:300])
sprawdz("(3) i podaje komende odzysku przez `--z-karty`",
        "--z-karty" in SPIS_T and "karta_do_zatwierdzenia.json" in SPIS_T,
        SPIS_T[-500:])
# Uwagi i karta obok tekstu. Karta jest jedyna rekompensata za brak wiersza
# w `articles`: `bank_fragmentow` czyta `articles.evidence`, wiec bez niej
# `unused_evidence` przepadloby razem z wierszem.
UWAGI_P = teraz["ratunek"][0].with_suffix(".uwagi.txt") if teraz["ratunek"] else pathlib.Path("brak")
KARTA_P = teraz["ratunek"][0].with_suffix(".karta.json") if teraz["ratunek"] else pathlib.Path("brak")
sprawdz("uwagi wewnetrzne leza obok, jako `.uwagi.txt` (NIE `.uwagi.md`)",
        UWAGI_P.exists()
        and not list(teraz["ratkat"].glob("*.uwagi.md")),
        [p.name for p in teraz["ratkat"].glob("*")])
UWAGI_T = UWAGI_P.read_text(encoding="utf-8") if UWAGI_P.exists() else ""
sprawdz("i niosa status razem z powodem",
        "NIESPRAWDZONY" in UWAGI_T and "BudgetExceeded" in UWAGI_T,
        UWAGI_T[:300])
sprawdz("karta lezy obok w ksztalcie, ktory czyta `--z-karty`",
        KARTA_P.exists()
        and set(json.loads(KARTA_P.read_text(encoding="utf-8"))) == {"card",
                                                                     "brief"},
        KARTA_P.name)
sprawdz("i niesie `unused_evidence`, czyli material, po ktory siega bank",
        KARTA_P.exists() and json.loads(
            KARTA_P.read_text(encoding="utf-8"))["card"].get("unused_evidence"),
        KARTA_P.name)
sprawdz("`articles` zostalo PUSTE — zaden wiersz nie powstal",
        teraz["wiersze"] == [], teraz["wiersze"])

print()
print("=== 4. CZTERY SKUTKI UBOCZNE: PRAWDZIWI CZYTELNICY, PRZED I PO ===")


def kontrdowod_audytu(conn):
    """Arytmetyka `audyt_systemu.py:320-334`, przepisana.

    Jedyne miejsce w tym pliku, gdzie czytelnik jest odtworzony, a nie wolany:
    `audyt_systemu.main()` to jedna funkcja na 400 linii, ktora otwiera
    PRODUKCYJNA baze (`config.DB_PATH`) i wola `browser` oraz `statystyki`.
    Odtworzone jest DOKLADNIE to, co decyduje: `z_uwagami` rosnie za kazdy
    artykul z niepustymi `notes`, a licznik bramek pomija `DLUGOSC` i
    `RECENZJA`. Wynik `stale` to lista bramek padajacych przy KAZDYM artykule
    — czyli kontrdowod na bramke martwa. Pusta lista znaczy „kontrdowod nie ma
    czego zglosic", i wlasnie ta pustke uratowany wiersz robil na stale.
    """
    art = list(conn.execute("SELECT id, title, body, notes, created_at"
                            " FROM articles ORDER BY id"))
    uwagi = Counter()
    z_uwagami = 0
    for a in art:
        try:
            n = json.loads(a["notes"] or "[]")
        except ValueError:
            continue
        if not n:
            continue
        z_uwagami += 1
        for g in {str(x.get("gate")) for x in n if isinstance(x, dict)}:
            if g not in ("DLUGOSC", "RECENZJA"):
                uwagi[g] += 1
    return {"z_uwagami": z_uwagami,
            "stale": sorted(g for g, i in uwagi.items()
                            if z_uwagami >= 4 and i == z_uwagami)}


def akapity(pierwsze, ile, slow, liczba, ty, granica, rdzen="slowo"):
    """Tekst o STEROWANYM szkielecie — material dla `gates.odcisk_formy`.

    Odcisk liczy szesc zgrubnych cech: pierwsze slowo akapitu, czy w pierwszych
    piecdziesieciu slowach jest liczba, gdzie pada „you", czy tekst konczy sie
    niewiadoma, ile akapitow (//3) i ile slow (//200). Zeby pokazac, ze
    uratowany plik WYPYCHA z okna tekst, ktory bramka by zlapala, trzeba
    dwoch tekstow o tym samym szkielecie i trzech o roznych — a nie losowego
    materialu, ktory raz sie zgodzi, raz nie.

    `rdzen` zmienia SLOWA, nie szkielet. Blizniak musi miec inne slowa, bo
    `poprzednie_teksty(pomin_tresc=...)` odsiewa plik, ktorego pierwsze 300
    znakow zgadza sie z ocenianym tekstem — i przy wspolnym rdzeniu wycinal
    z okna wlasnie ten artykul, ktory bramka miala zlapac.
    """
    czesci = []
    for i in range(ile):
        s = [pierwsze] if i == 0 else ["potem"]
        s += ["%s%s" % (rdzen, chr(97 + (j % 20))) for j in range(slow)]
        if i == 0 and liczba:
            s.insert(3, "1998")
        if i == 1 and ty:
            s.insert(2, "you")
        czesci.append(" ".join(s))
    if granica:
        czesci.append("Nobody knows what happens next, and the record does"
                      " not say.")
    return "\n\n".join(czesci)


# Cztery artykuly korpusu. Pierwszy ma szkielet, ktory nowy tekst powtarza;
# trzy pozostale maja rozne. Kazdy niesie bramke ODCISK_FORMY, zeby kontrdowod
# audytu mial co zglosic (bramka padajaca przy KAZDYM z czterech).
KORPUS = [
    ("Alpha One", "the automated meter reading", akapity("The", 6, 60, False, False, False),
     [{"gate": "ODCISK_FORMY", "detail": "ten sam szkielet co 2."}]),
    ("Beta Two", "kenyan annotators pay floor", akapity("Nobody", 12, 30, True, True, True),
     [{"gate": "ODCISK_FORMY", "detail": "ten sam szkielet co 1."}]),
    ("Gamma Three", "targeting system output rate", akapity("Meanwhile", 3, 200, True, True, False),
     [{"gate": "ODCISK_FORMY", "detail": "ten sam szkielet co 4."},
      {"gate": "FAKT_BEZ_POKRYCIA", "detail": "zdanie o udziale rynkowym"},
      {"gate": "ZASTRZEZENIE", "detail": "dwa zastrzezenia zamiast jednego"}]),
    ("Delta Four", "university entry level hiring study", akapity("Someone", 15, 20, True, False, True),
     [{"gate": "ODCISK_FORMY", "detail": "ten sam szkielet co 3."},
      {"gate": "KUPLET_KORYGUJACY", "detail": "nie X, tylko Y"},
      {"gate": "TIK", "detail": "trzy zdania z tym samym rytmem"}]),
]
# Blizniak pierwszego artykulu CO DO FORMY, ale nie co do slow — inaczej
# `gates.powtorzona_forma` uznaloby go za ten sam plik i przemilczalo.
BLIZNIAK = akapity("The", 6, 62, False, False, False, rdzen="inne")

KORZEN4 = nowy_teren()
KAT4 = KORZEN4 / "articles"
RAT4 = KORZEN4 / "artykuly-przerwane"
CONN4 = prawdziwe_db.connect(KORZEN4 / "t.db")
_stary4 = config.ARTICLES_DIR
config.ARTICLES_DIR = KAT4
try:
    for i, (tytul, temat, tresc, notatki) in enumerate(KORPUS, start=1):
        p = prawdziwe_stages.save(
            CONN4, i, {"title": temat}, {"confirmed_claims": []},
            {"title": tytul, "subtitle": "podtytul", "body": tresc},
            "SAVED", "", notatki)
        # Czas na sztywno i rosnaco — `ostatnie_uwagi` sortuje po `mtime`.
        for q in (p, p.with_suffix(".uwagi.md")):
            os.utime(q, (ZEGAR + i, ZEGAR + i))

    def zmierz(etykieta):
        wynik = {
            "uwagi_do_pisarza": prawdziwe_stages.ostatnie_uwagi(),
            "teksty_do_formy": prawdziwe_stages.poprzednie_teksty(
                pomin_tresc=BLIZNIAK),
            "pamiec_powtorek": prawdziwe_stages.tematy_do_porownania(CONN4),
            "katy": prawdziwe_stages.recent_angles(CONN4),
            "wiersze": [tuple(r) for r in CONN4.execute(
                "SELECT id, title, body, notes, created_at FROM articles"
                " ORDER BY id")],
            "audyt": kontrdowod_audytu(CONN4),
        }
        wynik["sygnal_formy"] = prawdziwe_gates.powtorzona_forma(
            BLIZNIAK, wynik["teksty_do_formy"])
        wynik["temat_spalony"] = any(
            w and prawdziwe_stages._o_tym_samym(
                "meters " + TYTUL.lower() + " " + TRESC[:200], w,
                **prawdziwe_stages.POWTORKA_TEMATU)
            for w in wynik["pamiec_powtorek"])
        print("       %-14s zarzutow %d | tekstow %d | pamiec %d | katy %d |"
              " wierszy %d | bramek zawsze %d | sygnal formy %s"
              % (etykieta,
                 len([x for x in wynik["uwagi_do_pisarza"].splitlines() if x]),
                 len(wynik["teksty_do_formy"]), len(wynik["pamiec_powtorek"]),
                 len(wynik["katy"]), len(wynik["wiersze"]),
                 len(wynik["audyt"]["stale"]),
                 "JEST" if wynik["sygnal_formy"] else "MILCZY"))
        return wynik

    A = zmierz("sam korpus:")
    PLIKI_A = sorted(p.name for p in KAT4.glob("*"))

    # --- RATUNEK, TAK JAK DZIS ------------------------------------------
    mod4 = zaladuj(ZRODLO_TERAZ)
    mod4._ratuj_tekst(91, dict(BRIEF), dict(KARTA),
                      {"title": TYTUL, "subtitle": "podtytul", "body": TRESC},
                      "recenzji", budzet())
    B = zmierz("po ratunku:")
    PLIKI_B = sorted(p.name for p in KAT4.glob("*"))

    # --- WARIANT ODRZUCONY: to samo, ale przez `stages.save` -------------
    # Odtworzone, nie opisane: PRAWDZIWY `stages.save` do `ARTICLES_DIR` plus
    # ta sama ramka na poczatku pliku. Dokladnie to robil ratunek przed ta
    # zmiana i dokladnie to psulo szesciu czytelnikow.
    _powod = "Przebieg przerwany na etapie recenzji: BudgetExceeded: limit"
    _p = prawdziwe_stages.save(
        CONN4, 91, dict(BRIEF), dict(KARTA),
        {"title": TYTUL, "subtitle": "podtytul", "body": TRESC},
        mod4.STATUS_URATOWANY, _powod,
        [{"gate": "RECENZJA", "detail": "NIE ODBYLA SIE — " + _powod},
         {"gate": "DLUGOSC", "detail": "%d slow" % len(TRESC.split())}])
    _p.write_text(mod4._ramka(_powod, ["recenzja", "obserwacja formy",
                                       "bramki jakosci",
                                       "sprawdzenie faktow przed publikacja"],
                              KAT4) + _p.read_text(encoding="utf-8"),
                  encoding="utf-8")
    for q in (_p, _p.with_suffix(".uwagi.md")):
        os.utime(q, (ZEGAR + 9, ZEGAR + 9))
    C = zmierz("do articles:")
finally:
    config.ARTICLES_DIR = _stary4

# (1) petla zwrotna do pisarza
sprawdz("(1) `stages.ostatnie_uwagi` oddaje DOKLADNIE to samo, co przed"
        " ratunkiem",
        B["uwagi_do_pisarza"] == A["uwagi_do_pisarza"],
        (A["uwagi_do_pisarza"], B["uwagi_do_pisarza"]))
sprawdz("(1) KONTRDOWOD: zapis do `ARTICLES_DIR` scinal zarzuty z %d do %d"
        % (len([x for x in A["uwagi_do_pisarza"].splitlines() if x]),
           len([x for x in C["uwagi_do_pisarza"].splitlines() if x])),
        C["uwagi_do_pisarza"] != A["uwagi_do_pisarza"]
        and len(C["uwagi_do_pisarza"].splitlines())
        < len(A["uwagi_do_pisarza"].splitlines()),
        C["uwagi_do_pisarza"])

# (2) bramka ODCISK_FORMY
sprawdz("(2) `stages.poprzednie_teksty` oddaje te same cztery teksty",
        B["teksty_do_formy"] == A["teksty_do_formy"],
        [len(A["teksty_do_formy"]), len(B["teksty_do_formy"])])
sprawdz("(2) i `gates.powtorzona_forma` nadal LAPIE powtorzony szkielet",
        B["sygnal_formy"] and B["sygnal_formy"] == A["sygnal_formy"],
        (A["sygnal_formy"][:80], B["sygnal_formy"][:80]))
sprawdz("(2) KONTRDOWOD: zapis do `ARTICLES_DIR` wypychal z okna tekst, ktory"
        " bramka lapala — sygnal MILKNIE",
        A["sygnal_formy"] and not C["sygnal_formy"],
        (A["sygnal_formy"][:80], repr(C["sygnal_formy"])))
sprawdz("(2) KONTRDOWOD: bo uratowany zajmowal jedno z czterech miejsc",
        len(C["teksty_do_formy"]) == len(A["teksty_do_formy"]) == 4
        and C["teksty_do_formy"] != A["teksty_do_formy"],
        len(C["teksty_do_formy"]))

# (3) kontrdowod audytu na martwa bramke
sprawdz("(3) `articles` widziane oczami audytu jest CO DO WIERSZA takie samo",
        B["wiersze"] == A["wiersze"], (len(A["wiersze"]), len(B["wiersze"])))
sprawdz("(3) wiec kontrdowod na martwa bramke nadal sie odzywa: %s"
        % (A["audyt"]["stale"] or "—"),
        B["audyt"] == A["audyt"] and A["audyt"]["stale"],
        (A["audyt"], B["audyt"]))
sprawdz("(3) KONTRDOWOD: jeden wiersz z `ARTICLES_DIR` rozbrajal go NA STALE",
        C["audyt"]["stale"] == []
        and C["audyt"]["z_uwagami"] == A["audyt"]["z_uwagami"] + 1,
        (A["audyt"], C["audyt"]))

# (4) pamiec powtorek tematu
sprawdz("(4) `stages.tematy_do_porownania` oddaje te same %d pozycji"
        % len(A["pamiec_powtorek"]),
        B["pamiec_powtorek"] == A["pamiec_powtorek"],
        (len(A["pamiec_powtorek"]), len(B["pamiec_powtorek"])))
sprawdz("(4) i temat uratowanego tekstu NIE jest spalony",
        not B["temat_spalony"] and not A["temat_spalony"],
        (A["temat_spalony"], B["temat_spalony"]))
sprawdz("(4) KONTRDOWOD: wiersz w `articles` spalal ten temat na zawsze",
        C["temat_spalony"] and len(C["pamiec_powtorek"])
        == len(A["pamiec_powtorek"]) + 1,
        (C["temat_spalony"], len(C["pamiec_powtorek"])))

# (5) i (6) — dwa czytelniki, ktorych kontrola nie wymienila, a ktorzy tez
# czytaja `articles` bez filtra statusu.
sprawdz("(5) `stages.recent_angles` oddaje te same katy",
        B["katy"] == A["katy"], (len(A["katy"]), len(B["katy"])))
sprawdz("(5) KONTRDOWOD: wiersz zajmowal jedno z pieciu miejsc",
        len(C["katy"]) == len(A["katy"]) + 1, (len(A["katy"]), len(C["katy"])))
sprawdz("(6) plikow w `ARTICLES_DIR` przybylo ZERO (%d przed, %d po)"
        % (len(PLIKI_A), len(PLIKI_B)),
        PLIKI_B == PLIKI_A, (PLIKI_A, PLIKI_B))
sprawdz("(6) a caly komplet ratunku lezy obok, w osobnym katalogu",
        len(list(RAT4.glob("*.md"))) == 1 and (RAT4 / "CZYTAJ_TO.txt").exists(),
        [p.name for p in RAT4.glob("*")])
CONN4.close()

print()
print("=== 5. KONTRDOWOD ODTWORZONY: %s NA TYM SAMYM HARNESSIE ==="
      % POPRZEDNIA_WERSJA)
stare = przebieg(STARE, "review", budzet)
sprawdz("KONTRDOWOD: przed zmiana zaden plik nie powstawal — tekst PRZEPADAL",
        stare["ratunek"] == [] and list(stare["kat"].glob("*")) == [],
        [p.name for p in stare["korzen"].glob("*")])
sprawdz("KONTRDOWOD: i zaden wiersz nie trafial do `articles`",
        stare["wiersze"] == [], stare["wiersze"])
sprawdz("KONTRDOWOD: a slad urywal sie na recenzji, bez `save`",
        "save" not in stare["slad"], stare["slad"])
# WSZYSTKO POZOSTALE MA BYC IDENTYCZNE. Ratunek ma dokladac zapis i nic wiecej.
sprawdz("stara i nowa wersja tak samo NIE publikuja",
        stare["wystawienia"] == [] == teraz["wystawienia"],
        (stare["wystawienia"], teraz["wystawienia"]))
sprawdz("obie tak samo nie tykaja `grafika` ani `zweryfikuj`",
        [e for e in stare["slad"] if e in ("grafika", "zweryfikuj")]
        == [e for e in teraz["slad"] if e in ("grafika", "zweryfikuj")] == [],
        (stare["slad"], teraz["slad"]))
sprawdz("obie wypuszczaja ten sam wyjatek na wylot",
        type(stare["wyjatek"]) is type(teraz["wyjatek"]) is llm.BudgetExceeded,
        (type(stare["wyjatek"]).__name__, type(teraz["wyjatek"]).__name__))
sprawdz("slad etapow jest CO DO KROKU ten sam — ratunek nie wola niczego",
        teraz["slad"] == stare["slad"], (stare["slad"], teraz["slad"]))
print("       slad %s: %s" % (POPRZEDNIA_WERSJA, " -> ".join(stare["slad"])))
print("       slad teraz:   %s" % " -> ".join(teraz["slad"]))
print("       plikow w katalogu artykulow: %s -> %d, teraz -> %d"
      % (POPRZEDNIA_WERSJA, len(list(stare["kat"].glob("*"))),
         len(list(teraz["kat"].glob("*")))))
print("       plikow w katalogu ratunku:   %s -> %d, teraz -> %d"
      % (POPRZEDNIA_WERSJA,
         len(list(stare["ratkat"].glob("*"))) if stare["ratkat"].exists() else 0,
         len(list(teraz["ratkat"].glob("*")))))

print()
print("=== 6. PRZERWANIE PRZED NAPISANIEM TEKSTU: ZERO PLIKOW ===")
# Nie ma czego ratowac, a pusty plik jest gorszy niz brak: kaze czlowiekowi
# otworzyc go i przekonac sie, ze nic w nim nie ma.
for etap in ("warto_pisac", "write"):
    p = przebieg(ZRODLO_TERAZ, etap, budzet)
    s = przebieg(STARE, etap, budzet)
    sprawdz("budzet pada na `%s`: zaden plik nie powstaje NIGDZIE" % etap,
            list(p["kat"].glob("*")) == [] and not p["ratkat"].exists(),
            [x.name for x in p["korzen"].glob("*")])
    sprawdz("budzet pada na `%s`: zaden wiersz w `articles`" % etap,
            p["wiersze"] == [], p["wiersze"])
    sprawdz("budzet pada na `%s`: nic nie idzie na zewnatrz" % etap,
            p["wystawienia"] == [] and isinstance(p["wyjatek"],
                                                  llm.BudgetExceeded),
            (p["wystawienia"], type(p["wyjatek"]).__name__))
    sprawdz("budzet pada na `%s`: zachowanie identyczne jak w %s"
            % (etap, POPRZEDNIA_WERSJA),
            p["slad"] == s["slad"] and p["wiersze"] == s["wiersze"],
            (p["slad"], s["slad"]))

print()
print("=== 7. PRZERWANIE PO RECENZJI, NA OBSERWACJI FORMY ===")
# Tekst jest napisany i oplacony tak samo, wiec ratujemy tak samo — ale
# ostrzezenie ma mowic PRAWDE: recenzja tu przeszla.
t7 = przebieg(ZRODLO_TERAZ, "ocen_forme", budzet)
sprawdz("tekst uratowany rowniez tutaj", len(t7["ratunek"]) == 1,
        [p.name for p in t7["ratunek"]])
T7 = tresc_pliku(t7["ratunek"])
sprawdz("nic nie poszlo na zewnatrz, grafiki i weryfikacji nie ruszono",
        t7["wystawienia"] == []
        and not [e for e in t7["slad"] if e in ("grafika", "zweryfikuj")],
        t7["slad"])
sprawdz("katalog artykulow nadal pusty, `articles` nadal puste",
        list(t7["kat"].glob("*")) == [] and t7["wiersze"] == [],
        (list(t7["kat"].glob("*")), t7["wiersze"]))
sprawdz("ramka nadal blokuje", T7.startswith("# NIE PUBLIKOWAC"),
        T7.splitlines()[:1])
sprawdz("ale NIE klamie, ze recenzji nie bylo",
        "Kontrole, ktore sie NIE odbyly: obserwacja formy" in T7,
        T7[:600])
U7 = (t7["ratunek"][0].with_suffix(".uwagi.txt").read_text(encoding="utf-8")
      if t7["ratunek"] else "")
sprawdz("a notatka RECENZJA niesie jej prawdziwe podsumowanie",
        "recenzja czysta" in U7, U7[:400])
U1 = UWAGI_T
sprawdz("KONTRDOWOD: przy przerwaniu NA recenzji ta sama notatka mowi"
        " „NIE ODBYLA SIE\"",
        "NIE ODBYLA SIE" in U1 and "NIE ODBYLA SIE" not in U7,
        (U1[:200], U7[:200]))
s7 = przebieg(STARE, "ocen_forme", budzet)
sprawdz("KONTRDOWOD: przed zmiana i tu przepadalo wszystko",
        s7["ratunek"] == [] and s7["wiersze"] == [], s7["slad"])

print()
print("=== 8. WYLACZNIK KILL_SWITCH ZACHOWUJE SIE TAK SAMO ===")
t8 = przebieg(ZRODLO_TERAZ, "review", wylacznik)
sprawdz("PreflightFailed leci na wylot, zero publikacji",
        isinstance(t8["wyjatek"], llm.PreflightFailed)
        and t8["wystawienia"] == [], type(t8["wyjatek"]).__name__)
T8 = tresc_pliku(t8["ratunek"])
sprawdz("tekst uratowany, ramka stoi",
        len(t8["ratunek"]) == 1 and T8.startswith("# NIE PUBLIKOWAC"),
        [p.name for p in t8["ratunek"]])
sprawdz("adnotacja niesie nazwe TEGO wyjatku, nie budzetu",
        "PreflightFailed" in T8, T8[:300])

print()
print("=== 9. ZDROWY PRZEBIEG NIETKNIETY (nie przesadzilem) ===")
# Zla odpowiedz recenzenta to awaria JEDNEGO wywolania. Budzet po niej
# istnieje, wiec artykul ma isc — z normalnym statusem, BEZ ramki, do
# `ARTICLES_DIR` i z wierszem w `articles`, tak jak zawsze.
t9 = przebieg(ZRODLO_TERAZ, "review", zwykla, budzet_wyczerpany=False)
sprawdz("zwykly ValueError nadal polykany, artykul wystawiony",
        t9["wyjatek"] is None and t9["wystawienia"] != [], t9["slad"])
sprawdz("i przeszedl przez `grafika` oraz `zweryfikuj`",
        "grafika" in t9["slad"] and "zweryfikuj" in t9["slad"], t9["slad"])
T9 = tresc_pliku(t9["md"])
sprawdz("plik lezy w katalogu ARTYKULOW, a katalog ratunku nie powstal",
        len(t9["md"]) == 1 and not t9["ratkat"].exists(),
        [p.name for p in t9["korzen"].glob("*")])
sprawdz("plik NIE ma ramki blokujacej", not T9.startswith("# NIE PUBLIKOWAC"),
        T9.splitlines()[:1])
sprawdz("i `rozbierz_artykul` widzi wlasciwy tytul",
        szkic(t9["md"])["tytul"] == TYTUL, szkic(t9["md"])["tytul"])
sprawdz("status w bazie to `SAVED`",
        [w["status"] for w in t9["wiersze"]] == ["SAVED"], t9["wiersze"])
s9 = przebieg(STARE, "review", zwykla, budzet_wyczerpany=False)
sprawdz("KONTRDOWOD: zdrowy przebieg zachowuje sie IDENTYCZNIE jak w %s"
        % POPRZEDNIA_WERSJA,
        t9["slad"] == s9["slad"]
        and [w["status"] for w in t9["wiersze"]]
        == [w["status"] for w in s9["wiersze"]],
        (t9["slad"], s9["slad"]))

print()
print("=== 10. PRZEBIEG NADAL KONCZY SIE BLEDEM, A SLAD PO TEKSCIE ZOSTAJE ===")
# `main` ma zamknac przebieg RAZ, jako ERROR, i przepuscic wyjatek dalej.
# Ratunek nie ma prawa tego zmienic — inaczej zegar systemd uznalby dzien za
# udany, a alarm nie zobaczylby niczego.


def przez_main(uratowane):
    mod = zaladuj(ZRODLO_TERAZ)
    atrapa_db = AtrapaDb()
    mod.db = atrapa_db
    mod._przebieg = _rzucaj(budzet)
    mod.URATOWANE[:] = [pathlib.Path(x) for x in uratowane]
    wyszlo = None
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            mod.main()
    except BaseException as exc:   # noqa: BLE001
        wyszlo = exc
    return atrapa_db.zamkniecia, wyszlo


zam, wyszlo = przez_main([])
sprawdz("(e) `finish_run` wykonalo sie DOKLADNIE raz", len(zam) == 1, zam)
sprawdz("(e) status zamkniecia to ERROR",
        zam and zam[0]["status"] == "ERROR", zam)
sprawdz("(e) uwaga niesie nazwe wyjatku, wiec alarm wie, na co patrzy",
        zam and "BudgetExceeded" in str(zam[0]["uwaga"]), zam)
sprawdz("(e) i wyjatek leci dalej, wiec kod wyjscia procesu nie jest zerem",
        isinstance(wyszlo, llm.BudgetExceeded), type(wyszlo).__name__)
zam2, _ = przez_main([KAT / "0091-the-meter-that-reads-itself.md"])
UW2 = str(pierwszy(zam2, {}).get("uwaga") or "")
sprawdz("gdy tekst uratowano, `runs.note` niesie NAZWE PLIKU — jedyny slad"
        " w bazie", "0091-the-meter-that-reads-itself.md" in UW2, UW2)
# `alarm.sprawdz_przebiegi_i_ostrzez` (alarm.py:158) wkleja note do maila
# przycieta do 120 znakow. Nazwa pliku ma sie w tym zmiescic RAZEM z nazwa
# wyjatku — inaczej wlasciciel dostaje mail, ktory o uratowanym tekscie milczy.
sprawdz("i miesci sie w 120 znakach, ktore alarm wklei do maila",
        "0091-the-meter-that-reads-itself.md" in UW2[:120]
        and "BudgetExceeded" in UW2[:120], UW2[:120])
sprawdz("cala uwaga nadal miesci sie w 200 znakach", len(UW2) <= 200, len(UW2))

print()
print("=== 11. AWARIA SAMEGO RATUNKU NIE PODMIENIA WYJATKU ===")
# Gdyby zapis sie wywrocil (dysk pelny, katalog tylko do odczytu), z przebiegu
# wyszedlby `OSError` zamiast `BudgetExceeded` — alarm i `finish_run` patrza na
# NAZWE wyjatku, wiec przerwanie budzetowe zniknelo by z dziennika. Ratunek ma
# byc dodatkiem, nigdy nowym zrodlem awarii.
mod11 = zaladuj(ZRODLO_TERAZ)
mod11._katalog_ratunku = _rzucaj(lambda: OSError("dysk pelny"))
_korzen11 = nowy_teren()
_conn11 = prawdziwe_db.connect(_korzen11 / "t.db")
_st11 = AtrapaStages([], "review", budzet, True, _conn11)
mod11.stages = _st11
_stary11 = config.ARTICLES_DIR
config.ARTICLES_DIR = _korzen11 / "articles"
sys.modules["gates"] = AtrapaGates()
_w11 = None
try:
    with contextlib.redirect_stdout(io.StringIO()) as _buf11:
        mod11._napisz_i_zapisz(_conn11, 95, dict(BRIEF), dict(KARTA))
except BaseException as exc:   # noqa: BLE001
    _w11 = exc
finally:
    config.ARTICLES_DIR = _stary11
    sys.modules.pop("gates", None)
    _conn11.close()
sprawdz("z przebiegu nadal wychodzi BudgetExceeded, a nie blad zapisu",
        isinstance(_w11, llm.BudgetExceeded), type(_w11).__name__)
sprawdz("i ekran mowi glosno, ze tekst przepadl",
        "ZAPIS SIE NIE UDAL" in _buf11.getvalue(),
        _buf11.getvalue()[-300:])

print()
print("=== 12. PUSTY TEKST NIE ZOSTAWIA PUSTEJ SKORUPY ===")
# `stages.write` albo oddaje caly obiekt, albo rzuca — ale gdyby kiedys oddal
# szkielet bez tresci, ratunek ma NIC nie zapisac. Pusty plik z ramka kaze
# czlowiekowi otworzyc go i przekonac sie, ze nie ma w nim tekstu.
mod12 = zaladuj(ZRODLO_TERAZ)
_korzen12 = nowy_teren()
_stary12 = config.ARTICLES_DIR
config.ARTICLES_DIR = _korzen12 / "articles"
try:
    with contextlib.redirect_stdout(io.StringIO()) as _buf12:
        mod12._ratuj_tekst(96, dict(BRIEF), dict(KARTA),
                           {"title": TYTUL, "subtitle": "x", "body": "   "},
                           "recenzji", budzet())
finally:
    config.ARTICLES_DIR = _stary12
sprawdz("pusta tresc: zaden plik nie powstaje",
        not (_korzen12 / "artykuly-przerwane").exists()
        and list((_korzen12 / "articles").glob("*")) == [],
        [p.name for p in _korzen12.glob("*")])
sprawdz("i mowi o tym glosno",
        "nie ma tekstu do uratowania" in _buf12.getvalue(),
        _buf12.getvalue())
sprawdz("`URATOWANE` zostaje puste, wiec `runs.note` nie sklamie",
        mod12.URATOWANE == [], mod12.URATOWANE)

print()
print("=== PRODUKCJA ===")
zle = 0
for p in PILNOWANE:
    ok = odcisk(p) == PRZED[str(p)]
    zle += 0 if ok else 1
    print("  %-24s %s" % (pathlib.Path(p).name,
                          "bez zmian" if ok else "ZMIENIONA"))
_po = sorted(x.name for x in config.ARTICLES_DIR.glob("*"))
zle += 0 if _po == ARTYKULY_PRZED else 1
print("  %-24s %s" % ("data/articles/",
                      "bez zmian (%d plikow)" % len(_po) if _po == ARTYKULY_PRZED
                      else "ZMIENIONY"))
_rat_po = (sorted(x.name for x in KATALOG_RATUNKU_PROD.glob("*"))
           if KATALOG_RATUNKU_PROD.exists() else None)
zle += 0 if _rat_po == RATUNEK_PROD_PRZED else 1
print("  %-24s %s" % ("data/artykuly-przerwane/",
                      "nie istnieje" if _rat_po is None
                      else ("bez zmian (%d plikow)" % len(_rat_po)
                            if _rat_po == RATUNEK_PROD_PRZED else "ZMIENIONY")))

print()
print("=== WYNIK: %d zdanych, %d oblanych%s ===" %
      (zdane, oblane, ", PRODUKCJA RUSZONA" if zle else ""))
sys.exit(1 if (oblane or zle) else 0)
