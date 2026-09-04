# -*- coding: utf-8 -*-
"""Wyczerpany budzet ma ZATRZYMAC przebieg, a nie wyciszyc kontrole.

CO SIE ZEPSULO. Commit `e88b456` opakowal `warto_pisac`, `write` i `review`
w `except Exception`. `llm.BudgetExceeded` i `llm.PreflightFailed` dziedzicza
po `RuntimeError`, wiec te trzy oslony polykaly rowniez wyczerpany budzet
(`RUN_LIMIT_USD` 1,60 / `DAILY_LIMIT_USD`) i wylacznik `KILL_SWITCH=true` —
czyli jedyne dwa wyjatki, ktore zatrzymywaly przebieg przed publikacja.

Komentarz nad oslona recenzji mowil „artykul idzie do szuflady". Szuflady tam
nie ma: `systemd/nia-artykul.service` wola `artykul_z_puli.py --wyslij`, wiec
kod idzie dalej przez `stages.save`, `stages.grafika`, `stages.zweryfikuj` do
`browser.wystaw_artykul(..., wyslij=True)`.

DLACZEGO TO BYLA PUBLIKACJA BEZ ANI JEDNEJ KONTROLI. `stages.zweryfikuj` na
TYM SAMYM bledzie budzetu oddawalo `safe_to_post: True` z uzasadnieniem
„puszczam na pierwszej siatce" — a pierwsza siatka to recenzja, ktora przed
chwila padla po cichu. Sekcja 1 mierzy to na PRAWDZIWYM `stages.zweryfikuj`
z prawdziwym `llm.BudgetExceeded`, nie na wyobrazeniu.

AKTUALIZACJA Z 1 WRZESNIA 2026 — `stages.zweryfikuj` TEZ ZOSTALO NAPRAWIONE.
`llm.BudgetExceeded` i `llm.PreflightFailed` ida teraz z tej funkcji na wylot
(patrz `stages.PRZERYWAJA` i `test_pusty_budzet_nie_sprawdza.py`). To zmienia
wynik kontrdowodu w tym pliku, i to jest zmiana na lepsze: e88b456 nadal brnie
przez padnieta recenzje do zapisu i okladki, ale NIE PUBLIKUJE JUZ, bo
zatrzymuje je wspolna ostatnia bramka. Sekcje 3, 6 i 7 mierza wiec dzis dwie
rzeczy naraz: ze stara wersja brnela dalej (jej wada) i ze dzis konczy sie to
wyjatkiem zamiast wystawieniem (naprawa bramki). Historyczne liczby ponizej
zostaja jako zapis tego, co bylo mierzone, zanim bramka zostala naprawiona.

SCENARIUSZ, KTORY TO ODTWARZA. Pisarz stoi na `claude-fable-5` (~0,76 USD przy
suficie przebiegu 1,60 USD), wiec `llm._preflight` przepuszcza pisanie i
wywraca sie dopiero na recenzji.

ZMIERZONE — ten sam harness, dwie wersje pliku, budzet padajacy na recenzji:

    e88b456 (do 1 wrzesnia):
              warto_pisac -> write -> review -> ocen_forme -> save ->
              grafika -> zweryfikuj -> wystaw_artykul      (wyjatek: brak, kod 0)
    e88b456 (dzis, po naprawie `stages.zweryfikuj`):
              warto_pisac -> write -> review -> ocen_forme -> save ->
              grafika -> zweryfikuj                        (BudgetExceeded)
    teraz:    warto_pisac -> write -> review               (BudgetExceeded)

DRUGA AKTUALIZACJA, 1 WRZESNIA 2026 — GOTOWY TEKST MA PRZEZYC, ALE ZADEN ETAP
GO NIE ZAPISUJE. Do tej pory naprawiona wersja urywala sie na recenzji i
gotowy tekst — okolo 0,76 USD za samo pisanie — nie trafial nawet na dysk.
Wlasciciel zdecydowal: zapisac, nie wyrzucac; zapis jest darmowy.

Ratunek pisze plik SAM, bez `stages.save`, do katalogu siostrzanego wobec
`ARTICLES_DIR` i BEZ wiersza w `articles` — dlatego slad etapow konczy sie na
recenzji, dokladnie tak jak przed dolozeniem ratunku. Powod jest osobny i
zmierzony w `test_ratunek_tekstu.py`: zapis przez `stages.save` wpuszczal
niesprawdzony tekst do korpusu i psul szesciu czytelnikow, ktorzy nie filtruja
po statusie.

Roznica wobec e88b456 jest mierzalna i zmierzona: stara wersja wola po
recenzji `ocen_forme`, `grafika` i `zweryfikuj`, czyli TRZY platne wywolania
przy koncie, ktore nie ma juz na jedno; naprawiona nie wola ani jednego.

Roznice, wszystkie policzone przez ten plik:

                                          e88b456        po naprawie
    wystaw_artykul(wyslij=True)           WOLANE(*)      nie wolane
    wyjatek z `_napisz_i_zapisz`          brak, kod 0(*) BudgetExceeded
    platne etapy po padnietej recenzji    3              0
    dochodzi do `grafika`                 TAK            NIE
    stages.write przy budzecie na write   2 razy         1 raz
    MODEL_FOR["write"] po awarii pisarza  claude-opus-5  claude-fable-5
    budzet na `ocen_forme`                brnie do konca zatrzymuje na formie
    KILL_SWITCH na recenzji               brnie do konca zatrzymuje na recenzji

(*) zmierzone przed 1 wrzesnia 2026, gdy `stages.zweryfikuj` przepuszczalo
    pusty budzet. Dzis ta sama stara wersja pliku brnie tak samo daleko, ale
    konczy sie `BudgetExceeded` z bramki zamiast wystawieniem — i wlasnie to
    mierza dzis sekcje 3, 6 i 7.

CALY TEN PLIK PUSZCZONY W MIEJSCU PRODUKCJI, przemierzony 1 wrzesnia 2026 po
dolozeniu zapisu ratunkowego (`git show <SHA>:agent-v2/artykul_z_puli.py`
w miejscu pliku, potem przywrocenie — odcisk sha256 sprawdzony):

    e88b456 (regresja polykajaca budzet):   29 zdanych, 7 OBLANYCH
    64d881a (przed zapisem ratunkowym):     34 zdane,   2 OBLANE
    drzewo teraz:                           36 zdanych, 0 oblanych

Te dwie oblane na `64d881a` to dokladnie sekcje 2 i 6: przed zmiana przebieg
urywal sie na recenzji bez zapisu, wiec gotowy tekst przepadal. Sekcje 9 i 10
przechodza we wszystkich trzech — `main` wady nie mial, tylko wyjatek do niego
nie docieral. (Poprzedni pomiar, sprzed naprawy `stages.zweryfikuj` i sprzed
ratunku, dawal na e88b456 23 zdane i 8 oblanych przy innym zestawie asercji.)

Powtorka pisarza na Opusie jest osobna szkoda: e88b456 przy budzecie na
`warto_pisac` albo na `write` placilo za pisarza DWA razy (~0,76 USD kazde,
drugi raz na DROZSZYM modelu) i tak konczylo `BudgetExceeded` — publikacji tam
nie bylo, byl podwojony wydatek. Publikacja bez recenzji zaczyna sie dopiero,
gdy budzet wyczerpie sie NA recenzji albo pozniej (sekcje 3, 6, 7).

TEST MIERZY ZACHOWANIE, NIE TRESC ZRODLA. Zero asercji typu `"..." in ZRODLO`
— trzy takie testy swiecily w tej sesji na zielono nad kodem, ktory w
produkcji nie robil nic. Tutaj kazde twierdzenie to wynik wywolania
`_napisz_i_zapisz` na atrapie `stages`/`gates`/`browser` i sprawdzenie, czy
`browser.wystaw_artykul` zostal zawolany.

BEZ PYTESTA, zero platnych wywolan, zero sieci. Uruchamiac z korzenia:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_budzet_nie_publikuje.py
Kontrdowod jest ODTWORZONY: `git show e88b456:agent-v2/artykul_z_puli.py` ladzi
do katalogu tymczasowego i przechodzi PRZEZ TEN SAM harness. Zaden warunek nie
zna dzisiejszej daty.
"""
import contextlib
import hashlib
import importlib.util
import io
import pathlib
import subprocess
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import config          # noqa: E402
import llm             # noqa: E402
import stages as prawdziwe_stages   # noqa: E402

# HISTORIA JEST WARUNKIEM TEGO TESTU. Kontrdowod ponizej odtwarza sie
# z commita sprzed naprawy, wiec w kopii z historia zalozona od nowa
# nie ma z czego go odtworzyc. Pominiecie jest wtedy JAWNE, zamiast
# wywalac sie w polowie pliku na `CalledProcessError`.
import historia   # noqa: E402
historia.wymaga_historii("e88b456")

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
             pathlib.Path("agent-v2/run.py"),
             pathlib.Path("agent-v2/llm.py"),
             pathlib.Path(config.DB_PATH),
             config.DATA_DIR / "dziennik.jsonl"]
PRZED = {str(p): odcisk(p) for p in PILNOWANE}

ZRODLO_TERAZ = pathlib.Path("agent-v2/artykul_z_puli.py").resolve()

# --- kopia sprzed naprawy, ODTWORZONA, nie opisana ------------------------
KAT = pathlib.Path(tempfile.mkdtemp())
STARE = KAT / "artykul_z_puli_e88b456.py"
STARE.write_bytes(subprocess.check_output(
    ["git", "show", "e88b456:agent-v2/artykul_z_puli.py"]))

# Etapy PLATNE w kolejnosci, w jakiej wola je `_napisz_i_zapisz`. Gdy budzet
# wyczerpie sie na ktoryms, `llm._preflight` wywraca KAZDE nastepne wywolanie —
# wiec atrapa tez, inaczej modelowalaby dzien, ktory nie istnieje.
PLATNE = ["warto_pisac", "write", "review", "ocen_forme", "zweryfikuj"]

KARTA = {"working_thesis": "Kto ustawil ten uklad i za czyje pieniadze.",
         "confirmed_claims": [{"claim": "x", "evidence": "y",
                               "url": "https://example.org/a"}],
         "source_dates": {"newest": "2026-08-20", "oldest": "2026-08-01"}}
BRIEF = {"title": "Example Article Twelve",
         "question": "Who decided the device reports its own reading?"}
TRESC = " ".join(["word"] * 650)


class AtrapaStages:
    """Atrapa etapow. Jedyne, co udaje, to wywolania do modelu.

    `zweryfikuj` NIE jest udawane — wola PRAWDZIWE `stages.zweryfikuj` z
    podmienionym `llm.call`. Inaczej test dowodzilby wylacznie tego, jak sobie
    wyobrazam ostatnia bramke, a to ona decyduje o publikacji.
    """

    # Czyste funkcje (bez sieci, modelu i bazy) ida do PRAWDZIWEGO `stages` —
    # atrapowanie ich zamienialoby test w sprawdzanie wlasnej atrapy.
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

    def __init__(self, slad, pada_na, fabryka, budzet_wyczerpany):
        self.slad = slad
        self.pada_na = pada_na
        self.fabryka = fabryka
        self.budzet = budzet_wyczerpany
        self._od = PLATNE.index(pada_na) if pada_na in PLATNE else len(PLATNE)
        self._padlo = 0

    def _moze_paso(self, etap):
        if etap == self.pada_na:
            self._padlo += 1
            # ZWYKLA AWARIA PADA RAZ. Zly JSON to jedno nieudane wywolanie, a
            # nie stan konta — inaczej „powtorka pisarza" nie mialaby jak sie
            # udac w zadnym tescie i mierzylibysmy wylacznie sama atrape.
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
        return {"title": BRIEF["title"], "subtitle": "podtytul", "body": TRESC}

    def review(self, conn, run_id, card, draft):
        self._licz("review")
        return {"sentences": [], "unsupported_facts": [], "summary": "czysto"}

    def ocen_forme(self, conn, run_id, draft):
        self._licz("ocen_forme")
        return {"beliefs": [], "support_only": [], "reader_moment": {}}

    def zweryfikuj(self, conn, run_id, tekst, kontekst=""):
        self.slad.append("zweryfikuj")
        if not self._moze_paso("zweryfikuj"):
            return {"claims": [], "safe_to_post": True, "verdict": "przechodzi"}
        # PRAWDZIWA bramka, prawdziwy wyjatek — patrz docstring klasy.
        stary = llm.call
        llm.call = _rzucaj(self.fabryka)
        try:
            return prawdziwe_stages.zweryfikuj(conn, run_id, tekst, kontekst)
        finally:
            llm.call = stary

    # --- etapy bezplatne, tylko zeby lancuch mial czym oddychac ---
    def poprzednie_teksty(self, pomin_tresc=""):
        return []

    def swiezosc_karty(self, card):
        return []

    def bank_fragmentow(self, conn):
        return []

    def save(self, conn, run_id, brief, card, draft, status, blokada, notatki):
        self.slad.append("save")
        return KAT / "0099-artykul.md"

    def grafika(self, conn, run_id, draft, sciezka_artykulu=None):
        self.slad.append("grafika")


def _rzucaj(fabryka):
    def _f(*a, **k):
        raise fabryka()
    return _f


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
    """Wczytuje BADANY plik pod wlasna nazwa, zeby obie wersje mogly zyc naraz.

    `config`, `db`, `llm` i `stages` siedza juz w `sys.modules`, wiec `import`
    w badanym pliku bierze je stamtad i nic z dysku nie doczytuje. `llm`
    zostaje PRAWDZIWY: to z niego badany kod bierze klasy wyjatkow, a podmiana
    ich na wlasne zamienilaby test w tautologie.
    """
    _licznik[0] += 1
    nazwa = "azp_pod_testem_%d" % _licznik[0]
    spec = importlib.util.spec_from_file_location(nazwa, str(sciezka))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[nazwa] = mod
    spec.loader.exec_module(mod)
    return mod


def przebieg(sciezka, pada_na, fabryka, budzet_wyczerpany=True):
    """Jeden przebieg `_napisz_i_zapisz` na atrapach. Oddaje, CO sie stalo."""
    slad = []
    st = AtrapaStages(slad, pada_na, fabryka, budzet_wyczerpany)
    br = AtrapaBrowser(slad)
    stare_moduly = {k: sys.modules.get(k) for k in ("gates", "browser")}
    stary_argv = sys.argv[:]
    stary_model = dict(config.MODEL_FOR)
    # KATALOG NA CZAS PRZEBIEGU — INACZEJ RATUNEK PISZE DO PRODUKCJI.
    # `AtrapaStages.save` jest atrapa i nic nie zapisuje, wiec do 1 wrzesnia
    # ten harness nie dotykal dysku wcale. Ratunek pisze PRAWDZIWE pliki i
    # liczy swoj katalog z `config.ARTICLES_DIR.parent` — bez tej podmiany
    # zostawial komplet w `agent-v2/data/artykuly-przerwane/`. Zmierzone: po
    # jednym przebiegu tego pliku lezaly tam cztery pliki z atrapy.
    stary_kat = config.ARTICLES_DIR
    korzen = pathlib.Path(tempfile.mkdtemp())
    (korzen / "articles").mkdir()
    config.ARTICLES_DIR = korzen / "articles"
    sys.modules["gates"] = AtrapaGates()
    sys.modules["browser"] = br
    sys.argv = ["artykul_z_puli.py", "--wyslij"]
    mod = zaladuj(sciezka)
    mod.stages = st
    wyjatek = None
    kod = None
    try:
        with contextlib.redirect_stdout(io.StringIO()) as buf:
            kod = mod._napisz_i_zapisz(object(), 4242, dict(BRIEF), dict(KARTA))
    except BaseException as exc:   # noqa: BLE001 — mierzymy, co wylatuje
        wyjatek = exc
    finally:
        # MODEL ODCZYTANY PRZED PRZYWROCENIEM. `config.MODEL_FOR` to ten sam
        # slownik, ktory badany plik przestawia na Opusa — sprawdzanie go po
        # sprzataniu dawaloby zawsze wartosc wyjsciowa, czyli asercje o niczym.
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
    ratkat = korzen / "artykuly-przerwane"
    return {"slad": slad, "wyjatek": wyjatek, "kod": kod,
            "wystawienia": br.wystawienia, "ekran": buf.getvalue(),
            "model_po": model_po, "modul": mod, "korzen": korzen,
            "ratunek": sorted(ratkat.glob("*.md")) if ratkat.exists() else []}


def budzet():
    return llm.BudgetExceeded(
        "limit dzienny toru 'produkcja' wyczerpany: 5.0100 / 5.0 USD")


def wylacznik():
    return llm.PreflightFailed("KILL_SWITCH=true — wywolania wstrzymane")


def zwykla():
    return ValueError("Extra data: line 1 column 1866")


print("=== 1. OSTATNIA BRAMKA: PUSTY BUDZET NIE, ZLY JSON TAK ===")
# Mierzone na PRAWDZIWYM `stages.zweryfikuj`, nie na atrapie: to ostatnia
# bramka przed `browser.wystaw_artykul` i to ona decyduje.


def _bramka_gdy(fabryka):
    """(wynik, wyjatek) prawdziwego `zweryfikuj` przy danej awarii `llm.call`."""
    stary = llm.call
    llm.call = _rzucaj(fabryka)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return prawdziwe_stages.zweryfikuj(object(), 1, TRESC, "tytul"), None
    except BaseException as exc:      # noqa: BLE001 — mierzymy, co wylatuje
        return None, exc
    finally:
        llm.call = stary


audyt, wyjatek = _bramka_gdy(budzet)
sprawdz("prawdziwe `zweryfikuj` przy BudgetExceeded NIE oddaje safe_to_post=True",
        audyt is None or audyt.get("safe_to_post") is not True, audyt)
sprawdz("...bo przerwanie idzie z bramki na wylot (naprawa z 1 wrzesnia)",
        isinstance(wyjatek, llm.BudgetExceeded), type(wyjatek).__name__)
audyt_zly, _ = _bramka_gdy(zwykla)
sprawdz("zwykla awaria nadal przepuszcza i tlumaczy sie pierwsza siatka",
        audyt_zly is not None and audyt_zly.get("safe_to_post") is True
        and "pierwszej siatce" in str(audyt_zly.get("verdict", "")), audyt_zly)
sprawdz("BudgetExceeded naprawde dziedziczy po Exception",
        issubclass(llm.BudgetExceeded, Exception)
        and issubclass(llm.PreflightFailed, Exception))

print()
print("=== 2. BUDZET PADA NA RECENZJI — PRODUKCJA ===")
teraz = przebieg(ZRODLO_TERAZ, "review", budzet)
sprawdz("nic nie poszlo na Substacka",
        teraz["wystawienia"] == [], teraz["wystawienia"])
sprawdz("wyjatek wychodzi z `_napisz_i_zapisz` na wylot",
        isinstance(teraz["wyjatek"], llm.BudgetExceeded),
        type(teraz["wyjatek"]).__name__)
# ZMIANA KONTRAKTU Z 1 WRZESNIA 2026 — ta asercja brzmiala „nie brnie do
# zapisu" i pilnowala `"save" not in slad`. Wlasciciel zdecydowal odwrotnie:
# gotowy tekst, za ktory zaplacono okolo 0,76 USD, ma trafic NA DYSK, bo zapis
# jest darmowy. Nie zmienilo sie natomiast NIC z tego, czego ten plik pilnuje
# naprawde: `grafika` i `zweryfikuj` wolaja modele, wiec przy pustym budzecie
# nadal nie wolno ich tknac, a `wystaw_artykul` stoi za `raise`.
# Ratunek i jego ramka blokujaca sa mierzone w `test_ratunek_tekstu.py`.
sprawdz("zatrzymuje sie NA recenzji: zaden platny etap dalej nie rusza",
        "grafika" not in teraz["slad"] and "zweryfikuj" not in teraz["slad"],
        teraz["slad"])
sprawdz("...i po recenzji nie rusza ZADEN etap — nawet darmowy `save`",
        teraz["slad"] == ["warto_pisac", "write", "review"], teraz["slad"])
sprawdz("...a mimo to gotowy tekst jest na dysku: ratunek pisze plik sam,"
        " poza `ARTICLES_DIR` i bez wiersza w `articles`",
        len(teraz["ratunek"]) == 1
        and list((teraz["korzen"] / "articles").glob("*")) == [],
        [p.name for p in teraz["korzen"].glob("*")])

print()
print("=== 3. KONTRDOWOD ODTWORZONY: e88b456 NA TYM SAMYM HARNESSIE ===")
stare = przebieg(STARE, "review", budzet)
sprawdz("KONTRDOWOD: przed naprawa przebieg BRNAL przez padnieta recenzje"
        " az do zapisu i okladki",
        "save" in stare["slad"] and "grafika" in stare["slad"], stare["slad"])
sprawdz("KONTRDOWOD: i stawal dopiero przed ostatnia bramka, ktora recenzji"
        " nie zastepuje",
        "zweryfikuj" in stare["slad"]
        and stare["slad"].index("zweryfikuj") > stare["slad"].index("review"),
        stare["slad"])
# DO 1 WRZESNIA 2026 TA BRAMKA GO PRZEPUSZCZALA i tu stalo `wystawienia != []`.
# Po naprawie `stages.zweryfikuj` stara wersja pliku dochodzi w to samo miejsce,
# ale konczy sie wyjatkiem — czyli druga siatka lapie to, czego pierwsza nie
# zdazyla. Rozroznienie miedzy „brnie dalej" a „publikuje" zostaje widoczne.
sprawdz("DZIS: ta sama stara wersja NIE publikuje — zatrzymuje ja bramka",
        stare["wystawienia"] == []
        and isinstance(stare["wyjatek"], llm.BudgetExceeded),
        (stare["wystawienia"], type(stare["wyjatek"]).__name__))
sprawdz("a naprawiona wersja konczy o TRZY PLATNE etapy wczesniej — i nie"
        " wola nawet `save`",
        len(teraz["slad"]) < len(stare["slad"])
        and [e for e in stare["slad"] if e not in teraz["slad"]]
        == ["ocen_forme", "save", "grafika", "zweryfikuj"],
        (teraz["slad"], stare["slad"]))
print("       slad e88b456: %s" % " -> ".join(stare["slad"]))
print("       slad teraz:   %s" % " -> ".join(teraz["slad"]))

print()
print("=== 4. BUDZET PADA NA BRAMCE CIEKAWOSCI ===")
# Tu e88b456 NIE publikowalo — i to jest wynik, nie porazka testu. Polkniecie
# bramki przenosilo blad na pisarza, ktory po powtorce wyrzucal wyjatek juz
# nieoslonietego. Szkoda byla wiec inna: DWA oplacone wywolania pisarza przy
# koncie, ktore nie ma juz na jedno. Publikacja bez recenzji zaczyna sie
# dopiero od sekcji 3 i 6, czyli gdy budzet konczy sie NA recenzji albo pozniej.
t4 = przebieg(ZRODLO_TERAZ, "warto_pisac", budzet)
s4 = przebieg(STARE, "warto_pisac", budzet)
sprawdz("teraz: pisarz w ogole nie rusza", "write" not in t4["slad"], t4["slad"])
sprawdz("teraz: nic nie wychodzi na zewnatrz", t4["wystawienia"] == [])
sprawdz("teraz: BudgetExceeded na wylot",
        isinstance(t4["wyjatek"], llm.BudgetExceeded))
sprawdz("KONTRDOWOD: e88b456 placilo za pisarza DWA razy, zanim padlo",
        s4["slad"].count("write") == 2, s4["slad"])

print()
print("=== 5. POWTORKA PISARZA NA OPUSIE NIE PODWAJA WYDATKU ===")
t5 = przebieg(ZRODLO_TERAZ, "write", budzet)
s5 = przebieg(STARE, "write", budzet)
sprawdz("teraz: `stages.write` wolane DOKLADNIE raz",
        t5["slad"].count("write") == 1, t5["slad"])
sprawdz("teraz: model pisarza nie zostal przestawiony na Opusa",
        t5["model_po"] != config.CLAUDE, t5["model_po"])
sprawdz("teraz: nic nie wychodzi na zewnatrz", t5["wystawienia"] == [])
sprawdz("KONTRDOWOD: e88b456 wolalo pisarza DWA razy przy pustym budzecie",
        s5["slad"].count("write") == 2 and s5["model_po"] == config.CLAUDE,
        (s5["slad"], s5["model_po"]))
sprawdz("KONTRDOWOD: i tak konczylo BudgetExceeded — drugie 0,76 USD za nic",
        isinstance(s5["wyjatek"], llm.BudgetExceeded),
        type(s5["wyjatek"]).__name__)

print()
print("=== 6. BUDZET PADA DOPIERO NA OBSERWACJI FORMY ===")
t6 = przebieg(ZRODLO_TERAZ, "ocen_forme", budzet)
s6 = przebieg(STARE, "ocen_forme", budzet)
# Tak samo jak w sekcji 2: „przed zapisem" zastapione przez „przed KAZDYM
# NASTEPNYM PLATNYM etapem". Tekst byl juz napisany i oplacony, wiec od
# 1 wrzesnia 2026 ratunek zapisuje go rowniez tutaj.
sprawdz("teraz: recenzja przeszla, ale forma zatrzymuje przed okladka i"
        " sprawdzeniem faktow",
        t6["wystawienia"] == [] and "grafika" not in t6["slad"]
        and "zweryfikuj" not in t6["slad"], t6["slad"])
sprawdz("KONTRDOWOD: e88b456 brnelo do zapisu i okladki takze w tym wariancie",
        "save" in s6["slad"] and "grafika" in s6["slad"], s6["slad"])
sprawdz("KONTRDOWOD: i dopiero ostatnia bramka je dzis zatrzymuje",
        s6["wystawienia"] == []
        and isinstance(s6["wyjatek"], llm.BudgetExceeded),
        (s6["wystawienia"], type(s6["wyjatek"]).__name__))

print()
print("=== 7. WYLACZNIK KILL_SWITCH ZACHOWUJE SIE TAK SAMO ===")
t7 = przebieg(ZRODLO_TERAZ, "review", wylacznik)
s7 = przebieg(STARE, "review", wylacznik)
sprawdz("teraz: PreflightFailed na wylot, zero publikacji",
        isinstance(t7["wyjatek"], llm.PreflightFailed)
        and t7["wystawienia"] == [], type(t7["wyjatek"]).__name__)
sprawdz("KONTRDOWOD: e88b456 brnelo do zapisu przy wlaczonym wylaczniku",
        "save" in s7["slad"] and "grafika" in s7["slad"], s7["slad"])
sprawdz("KONTRDOWOD: i dzis konczy sie PreflightFailed z bramki, nie publikacja",
        s7["wystawienia"] == []
        and isinstance(s7["wyjatek"], llm.PreflightFailed),
        (s7["wystawienia"], type(s7["wyjatek"]).__name__))

print()
print("=== 8. ZWYKLA AWARIA ETAPU NADAL JEST POLYKANA (nie przesadzilem) ===")
# Zly JSON z recenzenta to awaria JEDNEGO wywolania. Budzet po niej istnieje,
# `zweryfikuj` dziala naprawde, wiec artykul ma isc — dokladnie jak dotad.
t8 = przebieg(ZRODLO_TERAZ, "review", zwykla, budzet_wyczerpany=False)
s8 = przebieg(STARE, "review", zwykla, budzet_wyczerpany=False)
sprawdz("teraz: ValueError polkniety, artykul zapisany i wystawiony",
        t8["wyjatek"] is None and t8["wystawienia"] != [], t8["slad"])
sprawdz("teraz: i przeszedl przez `zweryfikuj`, a nie obok",
        "zweryfikuj" in t8["slad"], t8["slad"])
sprawdz("zachowanie identyczne jak w e88b456 — nic tu nie zmieniono",
        [w["wyslij"] for w in t8["wystawienia"]]
        == [w["wyslij"] for w in s8["wystawienia"]],
        (t8["wystawienia"], s8["wystawienia"]))
t8b = przebieg(ZRODLO_TERAZ, "write", zwykla, budzet_wyczerpany=False)
sprawdz("teraz: powtorka pisarza na Opusie DZIALA, gdy to nie budzet",
        t8b["slad"].count("write") == 2 and t8b["wyjatek"] is None,
        t8b["slad"])

print()
print("=== 9. `main` ZAMYKA PRZEBIEG JAKO ERROR PO PRZEPUSZCZONYM WYJATKU ===")
mod = zaladuj(ZRODLO_TERAZ)
atrapa_db = AtrapaDb()
mod.db = atrapa_db
mod._przebieg = _rzucaj(budzet)
wyszlo = None
try:
    with contextlib.redirect_stdout(io.StringIO()):
        mod.main()
except BaseException as exc:   # noqa: BLE001
    wyszlo = exc
sprawdz("`finish_run` wykonalo sie dokladnie raz",
        len(atrapa_db.zamkniecia) == 1, atrapa_db.zamkniecia)
sprawdz("zamkniecie ma status ERROR",
        atrapa_db.zamkniecia and atrapa_db.zamkniecia[0]["status"] == "ERROR",
        atrapa_db.zamkniecia)
sprawdz("uwaga niesie nazwe wyjatku, wiec alarm wie, na co patrzy",
        atrapa_db.zamkniecia
        and "BudgetExceeded" in str(atrapa_db.zamkniecia[0]["uwaga"]),
        atrapa_db.zamkniecia)
sprawdz("i wyjatek leci dalej, wiec kod wyjscia procesu nie jest zerem",
        isinstance(wyszlo, llm.BudgetExceeded), type(wyszlo).__name__)

print()
print("=== 10. WADA ZASTANA W `run.py` — JUZ NAPRAWIONA, TU TYLKO NAZWANA ===")
# `run.py` mial DOKLADNIE te same cztery oslony (`warto_pisac`, `write`,
# `review`, `forma`) i te sama wade — ale wpisal je tam wczesniejszy commit,
# nie `e88b456`, wiec to byl dlug zastany, nie regres. Ta asercja pilnuje
# wlasnie tego rozroznienia i zostaje jako zapis pochodzenia wady.
# Naprawa i jej pomiar: `test_pusty_budzet_nie_sprawdza.py`, sekcje 6 i 7.
_diff = subprocess.check_output(
    ["git", "show", "e88b456", "--", "agent-v2/run.py"]).decode("utf-8", "replace")
_ruszone = [l for l in _diff.splitlines()
            if l.startswith(("+", "-")) and "except Exception" in l]
sprawdz("e88b456 nie tknal zadnej oslony w `run.py` — to dlug zastany",
        _ruszone == [], _ruszone)

print()
print("=== PRODUKCJA ===")
zle = 0
for p in PILNOWANE:
    ok = odcisk(p) == PRZED[str(p)]
    zle += 0 if ok else 1
    print("  %-24s %s" % (pathlib.Path(p).name,
                          "bez zmian" if ok else "ZMIENIONA"))

print()
print("=== WYNIK: %d zdanych, %d oblanych%s ===" %
      (zdane, oblane, ", PRODUKCJA RUSZONA" if zle else ""))
sys.exit(1 if (oblane or zle) else 0)
