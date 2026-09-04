# -*- coding: utf-8 -*-
"""Pusty budzet ma ZATRZYMAC wyjscie, a nie wyciszyc ostatnia bramke.

CO BYLO ZLE. `stages.zweryfikuj` przy zlapanym wyjatku oddawalo
`{"safe_to_post": True, "verdict": "... puszczam na pierwszej siatce"}`.
Uzasadnienie („zepsuta weryfikacja nie jest dowodem falszu") jest prawdziwe
dla zlego JSON-a albo padnietego wyszukiwania — model poszedl, poszukal i nie
umial oddac wyniku. NIE jest prawdziwe dla pustego konta: `llm.BudgetExceeded`
i `llm.PreflightFailed` dziedzicza po `RuntimeError`, wiec `except Exception`
lapalo je razem ze zlym JSON-em, a wtedy weryfikacja sie NIE ODBYLA i odbyc
sie nie mogla. „Sprawdzilem i nie wiem" to nie to samo, co „nie sprawdzilem".

ZASIEG BYL SZERSZY NIZ ARTYKUL. `zweryfikuj` jest ostatnia bramka na TRZECH
sciezkach:

    notka      stages.note      -> run.dzien/notki()     -> browser.wystaw_notke
    komentarz  stages.comment_on-> run.dzien/komentarze() -> browser.wystaw_komentarz
    artykul    run.main --wyslij                          -> browser.wystaw_artykul

Przy wyczerpanym budzecie albo `KILL_SWITCH=true` wszystkie trzy wychodzily
BEZ ANI JEDNEGO sprawdzenia faktow, tlumaczac sie siatka, ktora chwile
wczesniej padla na tym samym bledzie.

ZMIERZONE TYM PLIKIEM — ten sam harness, dwa drzewa (e88b456 i po naprawie).
Wszystkie liczby ponizej sa wynikiem uruchomienia, nie oszacowaniem:

                                              e88b456            po naprawie
    notka: kandydat z safe_to_post=True       TAK             zaden
    notka: browser.wystaw_notke               1 wystawienie   0
    komentarz: kandydat z safe_to_post=True   TAK             zaden
    komentarz: browser.wystaw_komentarz       1 wystawienie   0
    KILL_SWITCH, notka                        1 wystawienie   0
    KILL_SWITCH, komentarz                    1 wystawienie   0
    KILL_SWITCH, artykul (run.main --wyslij)  1 wystawienie   0
    budzet pada na recenzji: wystaw_artykul   1 wystawienie   0
    `dzien` konczy sie                        bez wyjatku     PreflightFailed
    artykul: db.finish_run                    1x DONE         1x FAILED
                                              „zatrzymany po  „PreflightFailed:
                                               etapie forma"   KILL_SWITCH…"
    budzet pada na pisarzu: stages.write       2 wywolania     1 wywolanie

Werdykt, ktorym e88b456 tlumaczyl publikacje notki i komentarza, brzmial doslownie:
„weryfikacja nie doszla do skutku (limit dzienny toru 'produkcja' wyczerpany:
5.0100 / 5.0 USD) — puszczam na pierwszej siatce".

CALY TEN PLIK NA KOPII DRZEWA `git archive e88b456 agent-v2` (czyli `stages.py`
i `run.py` z `git show HEAD:...`, uruchomione z tego samego harnessu):
    18 zdanych, 15 OBLANYCH.
Na drzewie po naprawie:
    33 zdane, 0 oblanych.

CZEGO TEST PILNUJE W DRUGA STRONE. Zwykly `ValueError` z `llm.call` (zly JSON
recenzenta) ma sie zachowywac DOKLADNIE jak dotad — notka i komentarz maja
wyjsc, bo zepsuta weryfikacja nadal nie jest dowodem falszu. Sekcja 5 mierzy
to na obu drzewach i wymaga IDENTYCZNEGO wyniku.

TEST MIERZY ZACHOWANIE, NIE TRESC ZRODLA. Zero asercji `"..." in ZRODLO`:
kazde twierdzenie to wynik uruchomienia prawdziwego `stages.note`,
`stages.comment_on`, `stages.zweryfikuj` i prawdziwego `run.dzien` /
`run.main` na atrapach przegladarki, kanalu i bazy. Publikacja jest liczona
tam, gdzie naprawde zachodzi: w wywolaniach `browser.wystaw_*`.

ZERO SIECI, ZERO PLATNYCH WYWOLAN: `llm.call` jest podmieniony na funkcje,
ktora albo oddaje gotowy JSON, albo rzuca prawdziwym `llm.BudgetExceeded` /
`llm.PreflightFailed` wzietym z `llm`, a nie z wlasnej klasy — inaczej test
bylby tautologia. Zaden warunek nie zna dzisiejszej daty: `cichy_dzien`
i `pora_na_publikacje` sa ustalone w atrapie configu.

BEZ PYTESTA, z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_pusty_budzet_nie_sprawdza.py
"""
import contextlib
import hashlib
import io
import json
import pathlib
import subprocess
import sys
import tempfile
import types

sys.path.insert(0, "agent-v2")
import config      # noqa: E402
import llm         # noqa: E402

# HISTORIA JEST WARUNKIEM TEGO TESTU — patrz `historia.py`.
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


PILNOWANE = [pathlib.Path("agent-v2/stages.py"),
             pathlib.Path("agent-v2/run.py"),
             pathlib.Path("agent-v2/llm.py"),
             pathlib.Path("agent-v2/artykul_z_puli.py"),
             pathlib.Path(config.DB_PATH),
             config.DATA_DIR / "dziennik.jsonl",
             config.DATA_DIR / "promocja.json"]
PRZED = {str(p): odcisk(p) for p in PILNOWANE}

KAT = pathlib.Path(tempfile.mkdtemp())


PRZED_NAPRAWA = "e88b456"  # commit audytowy, stan sprzed tej poprawki


def z_gita(sciezka):
# PRZYPIETY SHA, NIE `HEAD`. Ten test oblal sie na serwerze zaraz po
# wypchnieciu poprawki: `git show HEAD:` po commicie pokazuje juz KOD
# NAPRAWIONY, wiec kontrdowod porownywal naprawe z naprawa i wszystkie
# dziesiec asercji „przed naprawa bylo zle" oblewalo sie z automatu.
# Test mierzacy sie wzgledem `HEAD` traci sens w chwili commita,
# ktorego strzeze — dlatego wersja odniesienia jest tu wpisana na sztywno.
    return subprocess.check_output(
        ["git", "show", "%s:%s" % (PRZED_NAPRAWA, sciezka)])


# Dwa drzewa: to na dysku i to sprzed naprawy. Kontrdowod jest ODTWORZONY, nie opisany.
DRZEWA = {
    "teraz": {"stages": pathlib.Path("agent-v2/stages.py").read_bytes(),
              "run": pathlib.Path("agent-v2/run.py").read_bytes()},
    "PRZED": {"stages": z_gita("agent-v2/stages.py"),
             "run": z_gita("agent-v2/run.py")},
}


# --- wyjatki, ktorymi bedziemy przewracac wywolania ------------------------
def budzet():
    return llm.BudgetExceeded(
        "limit dzienny toru 'produkcja' wyczerpany: 5.0100 / 5.0 USD")


def wylacznik():
    return llm.PreflightFailed("KILL_SWITCH=true — wywolania wstrzymane")


def zly_json():
    return ValueError("Extra data: line 1 column 1866")


# Notka miesci sie w 33-64 slowach (`config.NOTE_MIN_WORDS/MAX`), nie ma adresu
# ani wzmianki `@`, wiec przechodzi `bez_wstrzykniecia`; komentarz nie powoluje
# sie na wlasne przezycie ani na „a recent study", wiec przechodzi
# `_podloga_z_pamieci`. Chodzi o to, zeby jedyna rzecza, ktora moze je
# zatrzymac, bylo sprawdzenie faktow.
NOTKA = ("The label on that meter is not a measurement. It is a permission "
         "slip written by the agency that also writes the exemptions, and the "
         "number printed on it was chosen before anyone ever took a reading.")
KOMENTARZ = ("The filing says the ceiling was set by the same office that "
             "grants the waivers, which makes the ceiling a negotiating "
             "position rather than a limit.")


def odpowiedz_modelu(cel):
    """Co `llm.call` oddaje, gdy ma sie udac."""
    if cel == "note":
        return json.dumps({"note": NOTKA, "why_this": "x"})
    if cel == "comment":
        return json.dumps({"comment": KOMENTARZ, "what_it_adds": "x"})
    if cel == "factcheck":
        # Wszystko potwierdzone: gdyby bramka NAPRAWDE zadzialala, przepuszcza.
        return json.dumps({"claims": [{"claim": "x", "status": "confirmed",
                                       "what_the_source_says": "y",
                                       "url": "https://example.org/a"}]})
    return json.dumps({})


def podmien_llm(pada_na, fabryka):
    """`llm.call`, ktory wywraca sie na WYBRANYM etapie, reszte oddaje gotowa.

    `pada_na=None` znaczy: nic nie pada — potrzebne do sekcji kontrolnej,
    ktora pokazuje, ze bez wyjatku obie sciezki naprawde publikuja.
    """
    def _call(purpose, *a, **k):
        if pada_na is not None and purpose == pada_na:
            raise fabryka()
        return odpowiedz_modelu(purpose)
    return _call


@contextlib.contextmanager
def llm_pada(pada_na, fabryka):
    stary = llm.call
    llm.call = podmien_llm(pada_na, fabryka)
    try:
        yield
    finally:
        llm.call = stary


# --- ladowanie obu drzew ---------------------------------------------------
_nr = [0]


def zbuduj(zrodlo, nazwa_pliku, nazwa):
    """Wykonuje zrodlo jako osobny modul, nie ruszajac tego z `sys.modules`."""
    _nr[0] += 1
    m = types.ModuleType("%s_%d" % (nazwa, _nr[0]))
    m.__dict__["__name__"] = m.__name__      # zeby nie odpalic `__main__`
    m.__dict__["__file__"] = nazwa_pliku
    exec(compile(zrodlo, nazwa_pliku, "exec"), m.__dict__)
    return m


# `wstaw_date_zrodel` i `usun_obalone` sa CZYSTE — nie wolaja modelu, sieci ani
# bazy. Atrapy oddaja je prawdziwemu `stages`: gdyby je udawac, test sprawdzalby
# wlasna atrape zamiast kodu, ktory decyduje o tresci idacej na Substacka.
_CZYSTY = zbuduj(DRZEWA["teraz"]["stages"], "agent-v2/stages.py", "stages_czyste")


def para(wersja):
    """`stages` i `run` z jednego drzewa, spiete ze soba.

    `run.py` robi `import stages` przy wykonaniu, wiec podstawiamy nasza kopie
    do `sys.modules` na czas exec-a — inaczej `run` sprzed naprawy pracowalby na
    `stages` z dysku i kontrdowod nie mierzylby tego, co trzeba.
    """
    st = zbuduj(DRZEWA[wersja]["stages"], "agent-v2/stages.py", "stages_%s" % wersja)
    # Notki i otwarcia z dysku/bazy nie maja tu nic do rzeczy — zerujemy je,
    # zeby test nie zalezal od tego, co konto wystawilo wczoraj.
    st.ostatnie_otwarcia = lambda *a, **k: []
    st.teksty_ostatnich_notek = lambda *a, **k: []

    # POLA WSPOLNE DLA WERSJI SPRZED ICH ISTNIENIA.
    #
    # Kontrdowod laduje KOD z commita sprzed naprawy, ale puszcza go na
    # DZISIEJSZYCH plikach promptow — bo prompty czyta z dysku przez
    # `config.PROMPTS_DIR`, a nie z tamtego commita. Odkad prompty uzywaja
    # `{nisza}`, `{marka}` i `{language}`, stary `_prompt` wywracal sie na
    # `KeyError`, a kontrdowod CICHO nic nie pokazywal: wszystkie asercje
    # „przed naprawa bylo zle" oblewaly sie, bo stara wersja nie zdazyla nic
    # zrobic. Awaria wygladala jak wada kodu i byla wada TESTU.
    #
    # Podstawiamy staremu modulowi te same pola, ktore dzisiejszy `_prompt`
    # wstrzykuje sam. Kontrdowod dotyczy BUDZETU, nie pol promptu — a mieszanie
    # starego kodu z nowymi promptami to cena, jaka placi kazdy test siegajacy
    # po wersje odniesienia do historii.
    #
    # LISTA POL NIE MOZE BYC PRZEPISANA RECZNIE. Stalo tu na sztywno
    # {"nisza", "marka", "language"} — i przy nastepnym rozszerzeniu pol
    # wspolnych (kat redakcyjny plus piec list przykladow z niszy) kontrdowod
    # ucichl DOKLADNIE TAK SAMO: szesc asercji „przed naprawa bylo zle"
    # oblalo sie, bo stary `_prompt` wywracal sie na `KeyError`, zanim zdazyl
    # cokolwiek zrobic. Ten sam blad, ktory komentarz wyzej juz raz opisal.
    # Bierzemy wiec pola z DZISIEJSZEGO modulu, zeby lista nie mogla sie
    # rozjechac po raz trzeci.
    if not hasattr(st, "_pola_wspolne"):
        import stages as _stages_z_dysku
        _wspolne = _stages_z_dysku._pola_wspolne()
        _stary_prompt = st._prompt

        def _prompt_z_polami(nazwa, **pola):
            return _stary_prompt(nazwa, **{**_wspolne, **pola})

        st._prompt = _prompt_z_polami
    stary = sys.modules.get("stages")
    sys.modules["stages"] = st
    try:
        rn = zbuduj(DRZEWA[wersja]["run"], "agent-v2/run.py", "run_%s" % wersja)
    finally:
        if stary is None:
            sys.modules.pop("stages", None)
        else:
            sys.modules["stages"] = stary
    return st, rn


def modul(nazwa, **pola):
    m = types.ModuleType(nazwa)
    for k, v in pola.items():
        setattr(m, k, v)
    return m


class Slad:
    def __init__(self):
        self.notki = []
        self.komentarze = []
        self.artykuly = []
        self.zamkniecia = []


class Konfig:
    """Prawdziwy config, ale bez zegara i kalendarza."""

    def __init__(self, kat):
        self._kat = kat

    DATA_DIR = None

    def __getattr__(self, nazwa):
        if nazwa == "DATA_DIR":
            return self._kat
        return getattr(config, nazwa)

    def cichy_dzien(self, *a, **k):
        return False

    def pora_na_publikacje(self):
        return True, "test"


class FalszywyKursor:
    def fetchone(self):
        return {"total": 0.0, "n": 0}


class FalszywaBaza:
    """Tyle bazy, ile dotyka `run.main` i `run._summary`."""

    def __init__(self, slad):
        self.slad = slad

    # jako `db`
    def connect(self, *a, **k):
        return self

    def start_run(self, conn, *a, **k):
        return 4242

    def finish_run(self, conn, run_id, status, stage=None, uwaga=None):
        self.slad.zamkniecia.append({"status": status, "stage": stage,
                                     "uwaga": uwaga})

    def spent_usd(self, conn, miesiac):
        return 0.0

    def recent_domains(self, conn, ile):
        return []

    # jako `conn`
    def execute(self, *a, **k):
        return FalszywyKursor()

    def close(self):
        # `run.main` zamyka polaczenie w `finally`. Brak tej metody zamienial
        # KAZDE zakonczenie przebiegu w `AttributeError` i chowal prawdziwy
        # wyjatek — czyli test mierzylby wlasna atrape, nie kod.
        pass

    def kanal(self, nazwa):
        # ZNACZNIK KANALU (`db.AKCJA`) — `run.main` opakowuje nim sprawdzenie
        # faktow artykulu. Oddajemy PRAWDZIWY menedzer kontekstu, bo wlasna,
        # pusta wersja cicho zdjelaby znacznik i ten test przestalby chodzic
        # po tym samym kodzie, co produkcja. Znacznik nie dotyka dysku: to
        # zmienna modulu `db`.
        import db as _db
        return _db.kanal(nazwa)


def swiat_dnia(slad, st):
    """Atrapy, ktorych dotyka `run.dzien` — plus PRAWDZIWE `note`/`comment_on`."""
    fake_browser = modul(
        "browser",
        ile_dzis_wystawione=lambda: {},
        dopisz_skutki=lambda: None,
        statystyki_pozycji=lambda: None,
        nieodpowiedziane=lambda: [],
        komentarze_pod_artykulami=lambda: [],
        odpowiedzi_na_nasze_komentarze=lambda: [],
        hosty_tylko_dla_placacych=lambda: set(),
        hosty_gdzie_komentarz_nie_wchodzi=lambda: set(),
        mozna_komentowac=lambda url: True,
        read_pages=lambda urls: [{"url": u, "title": "Kto podpisuje wyjatek",
                                  "text": "tresc cudzego posta"} for u in urls],
        # `typ` i `forma` doszly 1 wrzesnia 2026: dziennik zapisywal przy notce
        # tylko dlugosc i tresc, wiec nie dalo sie zmierzyc, czy formy w ogole
        # sie roznicuja. Atrapa je przyjmuje i ZAPISUJE — inaczej test milczalby
        # o tym, ze produkcja przestala je przekazywac.
        # `model` OD 2 WRZESNIA 2026: notki pisza dwaj pisarze na zmiane, wiec
        # dziennik dostaje nazwe tego, ktory napisal. Atrapa przyjmuje i ZAPISUJE
        # to pole z tego samego powodu, co `typ` i `forma` — zeby test krzyknal,
        # gdyby produkcja przestala je przekazywac.
        wystaw_notke=lambda tekst, wyslij=False, typ="", forma="", model="": (
            slad.notki.append({"tekst": tekst, "wyslij": wyslij,
                               "typ": typ, "forma": forma, "model": model})
            or {"wyslane": True, "blad": None}),
        wystaw_komentarz=lambda url, tekst, wyslij=False, kontekst=None: (
            slad.komentarze.append({"url": url, "tekst": tekst, "wyslij": wyslij})
            or {"wpisane": True, "wyslane": True, "blad": None}),
        wystaw_odpowiedz=lambda *a, **k: {"wpisane": True, "wyslane": True},
        wystaw_odpowiedz_pod_artykulem=lambda *a, **k: {"wyslane": True},
        zapomnij_platny_host=lambda host: None,
        polub_w_kanale=lambda ile, wyslij=False: {"polubione": 0},
        restackuj_w_kanale=lambda ile, ocen, wyslij=False: {"restackowane": 0},
        uchwyt_publikacji=lambda host: "",
        zasubskrybuj=lambda uchwyt, wyslij=False: None,
    )
    fake_kanal = modul(
        "kanal",
        szukaj_nowych=lambda: [
            {"rodzaj": "post", "url": "https://example.org/p/a", "pub": "example.org",
             "tytul": "Kto podpisuje wyjatek", "opis": "o tym, kto podpisuje",
             "komentarze": 3, "reakcje": 9, "data": "", "skad": "test"}],
        posty_z_kanalu=lambda ile=25: [],
        notki_z_kanalu=lambda: [],
        zapamietaj_komentarz=lambda post: None,
        _historia=lambda: {},
        _wiek_minut=lambda data: 1000.0,
    )
    fake_alarm = modul("alarm", sprawdz_sesje_i_ostrzez=lambda: None)
    fake_kopia = modul("kopia_subskrybentow", main=lambda: None)

    def notki_dnia(conn, run_id, ile=1, od=0, ciekawostki=None):
        # Opakowanie `note()` — dokladnie tak, jak robi to produkcja: jeden
        # material, jedno wywolanie, wynik oddany `run.dzien` bez zmian.
        # PRAWDZIWE jest to, co decyduje: `note` razem z `zweryfikuj` w srodku.
        wynik = st.note(conn, run_id, "MYSL",
                        {"fact": {"fact": "Wyjatek podpisuje ten sam urzad.",
                                  "url": "https://example.org/rule"}})
        wynik["fakt"] = None
        return [wynik]

    def _bez_kanalu(nazwa):
        """Dekorator dla drzewa PRZED, w ktorym kanalow jeszcze nie bylo."""
        return lambda f: f

    fake_stages = modul(
        "stages",
        # PRAWDZIWY dekorator kanalu — bloki `komentarze` i `dyskusje`
        # w `run.py` sa nim opakowane (patrz `FalszywaBaza.kanal`). Drzewo
        # PRZED pochodzi sprzed tej zmiany i swojego `run.py` nim nie dekoruje,
        # wiec dostaje wersje pusta. Odwrotna pomylka — nowy `run.py` bez
        # `_na_kanal` — nadal wywala sie glosno i tak ma byc.
        _na_kanal=getattr(st, "_na_kanal", _bez_kanalu),
        wstaw_date_zrodel=_CZYSTY.wstaw_date_zrodel,
        budzet_dnia=lambda conn: {"notki": 1, "komentarze": 1, "lajki": 0,
                                  "restacki": 0, "follow": 0, "subskrypcje": 0},
        notki_dnia=notki_dnia,
        zapisz_zuzyte=lambda co: None,
        odhacz_promocje=lambda url, tekst="": None,
        zakwestionuj_promocje=lambda url, powod: None,
        wybierz_cele=lambda conn, run_id, lista: list(lista),
        comment_on=st.comment_on,          # PRAWDZIWY, razem z `zweryfikuj`
        zbierz_pytania=lambda czekaja: None,
        wybierz_do_odpowiedzi=lambda conn, run_id, lista: list(lista),
        reply_to=st.reply_to,
    )
    return fake_browser, fake_kanal, fake_alarm, fake_kopia, fake_stages


def dzien(wersja, pada_na, fabryka):
    """Prawdziwy `run.dzien(wyslij=True)`. Oddaje, CO poszlo w swiat."""
    slad = Slad()
    st, rn = para(wersja)
    fb, fk, fa, fkop, fs = swiat_dnia(slad, st)
    stare = {n: sys.modules.get(n)
             for n in ("browser", "kanal", "alarm", "kopia_subskrybentow")}
    sys.modules["browser"] = fb
    sys.modules["kanal"] = fk
    sys.modules["alarm"] = fa
    sys.modules["kopia_subskrybentow"] = fkop
    wyjatek = None
    try:
        rn.stages = fs
        rn.config = Konfig(KAT)
        rn.ile_przebiegow_zostalo = lambda conn: 1
        rn.zmiesci_sie = lambda rodzaj, ile, udzial=1.0: ile
        # `potrzeba_s > 0` pyta wylacznie ozdobna zwloka przed pierwsza notka
        # (`config.ZWLOKA_PRZED_NOTKAMI`, do ~34 minut `time.sleep`). Produkcja
        # ja pomija, gdy sie nie miesci w czasie — my mowimy, ze nigdy sie nie
        # miesci. Reszta pytan (`potrzeba_s == 0`) przechodzi normalnie.
        rn.zostal_czas = lambda na_co="", potrzeba_s=0.0: potrzeba_s == 0.0
        rn.rytm = lambda co, na_co, stan: True      # zero snu, zero zegara
        bufor = io.StringIO()
        try:
            with contextlib.redirect_stdout(bufor), \
                    contextlib.redirect_stderr(io.StringIO()), \
                    llm_pada(pada_na, fabryka):
                rn.dzien(FalszywaBaza(slad), 1, wyslij=True)
        except BaseException as exc:      # noqa: BLE001 — mierzymy, co wylatuje
            wyjatek = exc
    finally:
        for n, v in stare.items():
            if v is None:
                sys.modules.pop(n, None)
            else:
                sys.modules[n] = v
    return {"slad": slad, "wyjatek": wyjatek, "ekran": bufor.getvalue()}


# --- sciezka artykulu: prawdziwy `run.main()` z `--wyslij` ------------------
KARTA = {"working_thesis": "Kto ustawil ten sufit i za czyje pieniadze.",
         "main_mechanism": "m",
         "confirmed_claims": [{"claim": "x", "evidence": "y",
                               "url": "https://example.org/a"}],
         "citable_numbers": [],
         "source_dates": {"newest": "2026-08-20", "oldest": "2026-08-01"}}
TEMAT = {"title": "Example Article Fourteen", "index": 0,
         "question": "Who set the ceiling and who grants the waiver?"}
KORPUS = [{"url": "https://example.org/a", "host": "example.org",
           "class": "PRIMARY", "title": "t", "text": "x" * 4000,
           "excerpts": ["fragment"], "numbers": ["12"]}] * 4
TRESC = " ".join(["word"] * 650)


def stages_artykulu(slad, st):
    """Atrapa etapow artykulu. Prawdziwy zostaje ten, ktory decyduje.

    Cztery etapy oslonione w `run.py` (`warto_pisac`, `write`, `review`,
    `forma`) MUSZA naprawde dotknac `llm.call`, inaczej `pada_na` nigdy by na
    nich nie wystrzelilo i sekcja 6 mierzylaby atrape zamiast oslony.
    """
    def _platny(cel):
        llm.call(cel, "system", "prompt")

    def warto_pisac(conn, run_id, card):
        _platny("warto_pisac")
        return {"werdykt": "PISZ", "powod": "jest luka", "ile_filarow": 3,
                "przekonanie": True,
                "filary": {"named_decider": True, "felt_number": True,
                           "second_domain": True},
                "contradicted_belief": {"the_belief": "b"}}

    def write(conn, run_id, card, glebokosc):
        _platny("write")
        return {"title": TEMAT["title"], "subtitle": "s", "body": TRESC,
                "limits_paragraph_present": True}

    def review(conn, run_id, card, draft):
        _platny("review")
        return {"sentences": [], "unsupported_facts": [], "summary": "czysto"}

    def ocen_forme(conn, run_id, draft):
        _platny("forma")
        return {"beliefs": [], "support_only": [], "reader_moment": {}}

    return modul(
        "stages",
        wstaw_date_zrodel=_CZYSTY.wstaw_date_zrodel,
        scout=lambda conn, run_id, ile: [dict(TEMAT)],
        feasibility=lambda conn, run_id, tematy: [
            {"index": 0, "feasible": True, "confidence": 0.9,
             "expected_primary_sources": 4, "note": "ok"}],
        pick_topic=lambda tematy, oceny, run_id, wczesniejsze=(): (
            dict(TEMAT), {"depth": "RICH", "note": "ok", "confidence": 0.9}),
        tematy_do_porownania=lambda conn: [],
        ostatnie_notki=lambda ile=1000: [],
        discovery=lambda conn, run_id, pytanie, recent, tylko_pierwotne=False: [],
        fetch=lambda conn, run_id, zrodla: list(KORPUS),
        classify=lambda conn, run_id, pytanie, korpus: list(KORPUS),
        synthesis=lambda conn, run_id, pytanie, dowody: dict(KARTA),
        fallback_card=lambda pytanie, dowody: dict(KARTA),
        warto_pisac=warto_pisac,
        bank_fragmentow=lambda conn: [],
        write=write,
        review=review,
        ocen_forme=ocen_forme,
        poprzednie_teksty=lambda pomin_tresc="": [],
        swiezosc_karty=lambda card: [],
        save=lambda *a, **k: KAT / "0099-artykul.md",
        grafika=lambda *a, **k: None,
        zweryfikuj=st.zweryfikuj,          # PRAWDZIWA ostatnia bramka
    )


def artykul(wersja, pada_na, fabryka):
    """Prawdziwy `run.main()` na `--wyslij`. Oddaje, CO poszlo w swiat."""
    slad = Slad()
    st, rn = para(wersja)
    baza = FalszywaBaza(slad)
    fake_browser = modul(
        "browser",
        wystaw_artykul=lambda sciezka, wyslij=False: (
            slad.artykuly.append({"sciezka": str(sciezka), "wyslij": wyslij})
            or {"wyslane": True, "blad": None}),
    )
    fake_gates = modul(
        "gates",
        deterministic_floors=lambda tresc, card, poprzednie=None: [],
        uwagi_z_formy=lambda forma, tresc: [],
        verdict=lambda uwagi: ("SAVED", ""),
        pozycja_w_tekscie=lambda moment, tresc: None,
    )
    stary_browser = sys.modules.get("browser")
    sys.modules["browser"] = fake_browser
    stary_argv = sys.argv[:]
    wyjatek = kod = None
    try:
        rn.stages = stages_artykulu(slad, st)
        rn.db = baza
        rn.gates = fake_gates
        rn.CACHE_DIR = KAT / "cache"
        rn.zajmij_zamek = lambda: None                  # zero zamka na produkcji
        rn.odmow_publikacji_z_kopii = lambda wyslij: None
        rn._sygnal_ma_zostawic_slad = lambda: None      # zero grzebania w sygnalach
        sys.argv = ["run.py", "--wyslij"]
        bufor = io.StringIO()
        try:
            with contextlib.redirect_stdout(bufor), \
                    contextlib.redirect_stderr(io.StringIO()), \
                    llm_pada(pada_na, fabryka):
                kod = rn.main()
        except BaseException as exc:      # noqa: BLE001
            wyjatek = exc
    finally:
        sys.argv = stary_argv
        if stary_browser is None:
            sys.modules.pop("browser", None)
        else:
            sys.modules["browser"] = stary_browser
    return {"slad": slad, "wyjatek": wyjatek, "kod": kod,
            "ekran": bufor.getvalue()}


def bezpieczne(wynik):
    """Ilu kandydatow wyszlo z `safe_to_post=True`."""
    return [k for k in wynik.get("candidates", []) if k.get("safe_to_post")]


# =========================================================================
print("=== 0. KONTROLA: bez wyjatku obie sciezki NAPRAWDE publikuja ===")
# Bez tego caly test moglby swiecic na zielono dlatego, ze atrapy nigdy nic nie
# wystawiaja — a wtedy „zero publikacji" nie znaczyloby nic.
k0 = dzien("teraz", None, budzet)
sprawdz("notka wychodzi, gdy weryfikacja dziala",
        len(k0["slad"].notki) == 1, k0["slad"].notki)
sprawdz("komentarz wychodzi, gdy weryfikacja dziala",
        len(k0["slad"].komentarze) == 1, k0["slad"].komentarze)
a0 = artykul("teraz", None, budzet)
sprawdz("artykul wychodzi, gdy weryfikacja dziala",
        [w for w in a0["slad"].artykuly if w["wyslij"] is True],
        a0["slad"].artykuly)

print()
print("=== 1. BUDZET PADA W WYSZUKIWANIU — NOTKA ===")
n1 = {w: dzien(w, "factcheck", budzet) for w in ("teraz", "PRZED")}
sprawdz("teraz: nic nie poszlo na Substacka",
        n1["teraz"]["slad"].notki == [], n1["teraz"]["slad"].notki)
sprawdz("KONTRDOWOD: przed naprawa notka SZLA bez sprawdzenia faktow",
        n1["PRZED"]["slad"].notki != [], n1["PRZED"]["slad"].notki)

# To samo mierzone o pietro nizej: na samym `stages.note`, bez `run.dzien`.
for wersja in ("teraz", "PRZED"):
    st, _ = para(wersja)
    wyjatek = wynik = None
    with contextlib.redirect_stdout(io.StringIO()), llm_pada("factcheck", budzet):
        try:
            wynik = st.note(object(), 1, "MYSL", {"fact": {"fact": "f"}})
        except BaseException as exc:   # noqa: BLE001
            wyjatek = exc
    if wersja == "teraz":
        sprawdz("teraz: `note` nie oddaje ZADNEGO kandydata z safe_to_post=True",
                wynik is None or bezpieczne(wynik) == [],
                wynik if wynik else type(wyjatek).__name__)
        sprawdz("teraz: BudgetExceeded leci z `note` na wylot",
                isinstance(wyjatek, llm.BudgetExceeded),
                type(wyjatek).__name__)
    else:
        sprawdz("KONTRDOWOD: przed naprawa `note` oddawalo safe_to_post=True",
                wynik is not None and bezpieczne(wynik) != [], wynik)

print()
print("=== 2. BUDZET PADA W WYSZUKIWANIU — KOMENTARZ ===")
sprawdz("teraz: nic nie poszlo pod cudzy post",
        n1["teraz"]["slad"].komentarze == [], n1["teraz"]["slad"].komentarze)
sprawdz("KONTRDOWOD: przed naprawa komentarz SZEDL bez sprawdzenia faktow",
        n1["PRZED"]["slad"].komentarze != [], n1["PRZED"]["slad"].komentarze)

for wersja in ("teraz", "PRZED"):
    st, _ = para(wersja)
    wyjatek = wynik = None
    with contextlib.redirect_stdout(io.StringIO()), llm_pada("factcheck", budzet):
        try:
            wynik = st.comment_on(object(), 1,
                                  {"title": "t", "text": "cudzy tekst",
                                   "url": "https://example.org/p/a"})
        except BaseException as exc:   # noqa: BLE001
            wyjatek = exc
    if wersja == "teraz":
        sprawdz("teraz: `comment_on` nie oddaje kandydata z safe_to_post=True",
                wynik is None or bezpieczne(wynik) == [],
                wynik if wynik else type(wyjatek).__name__)
    else:
        sprawdz("KONTRDOWOD: przed naprawa `comment_on` oddawalo safe_to_post=True",
                wynik is not None and bezpieczne(wynik) != [], wynik)

print()
print("=== 3. WYLACZNIK (KILL_SWITCH) — ZADNA Z TRZECH SCIEZEK NIE PUBLIKUJE ===")
w3 = {w: dzien(w, "factcheck", wylacznik) for w in ("teraz", "PRZED")}
a3 = {w: artykul(w, "factcheck", wylacznik) for w in ("teraz", "PRZED")}
sprawdz("teraz: notka nie wychodzi", w3["teraz"]["slad"].notki == [],
        w3["teraz"]["slad"].notki)
sprawdz("teraz: komentarz nie wychodzi", w3["teraz"]["slad"].komentarze == [],
        w3["teraz"]["slad"].komentarze)
sprawdz("teraz: artykul nie wychodzi", a3["teraz"]["slad"].artykuly == [],
        a3["teraz"]["slad"].artykuly)
sprawdz("teraz: PreflightFailed dochodzi do `main` jako wyjatek",
        isinstance(a3["teraz"]["wyjatek"], llm.PreflightFailed)
        or a3["teraz"]["kod"] == 1,
        (type(a3["teraz"]["wyjatek"]).__name__, a3["teraz"]["kod"]))
sprawdz("KONTRDOWOD: przed naprawa przy wylaczonych wywolaniach wychodzila notka",
        w3["PRZED"]["slad"].notki != [], w3["PRZED"]["slad"].notki)
sprawdz("KONTRDOWOD: i komentarz", w3["PRZED"]["slad"].komentarze != [],
        w3["PRZED"]["slad"].komentarze)
sprawdz("KONTRDOWOD: i artykul", a3["PRZED"]["slad"].artykuly != [],
        a3["PRZED"]["slad"].artykuly)

print()
print("=== 4. PRZEBIEG SIE ZAMYKA — ZERO WIERSZY W RUNNING ===")
# Sciezka artykulu: `main` ma zewnetrzny `except Exception`, ktory zapisuje
# FAILED. Sciezka dnia: `main` ma `except BaseException` przy `--dzien`.
sprawdz("artykul: `finish_run` wykonalo sie DOKLADNIE raz",
        len(a3["teraz"]["slad"].zamkniecia) == 1,
        a3["teraz"]["slad"].zamkniecia)
sprawdz("artykul: zamkniecie ma status FAILED",
        a3["teraz"]["slad"].zamkniecia
        and a3["teraz"]["slad"].zamkniecia[0]["status"] == "FAILED",
        a3["teraz"]["slad"].zamkniecia)
sprawdz("artykul: uwaga niesie nazwe wyjatku, wiec alarm wie, na co patrzy",
        a3["teraz"]["slad"].zamkniecia
        and "PreflightFailed" in str(a3["teraz"]["slad"].zamkniecia[0]["uwaga"]),
        a3["teraz"]["slad"].zamkniecia)
sprawdz("dzien: przerwanie wychodzi z `dzien` na wylot, wiec `main` zapisze FAILED",
        isinstance(w3["teraz"]["wyjatek"], llm.PreflightFailed),
        type(w3["teraz"]["wyjatek"]).__name__)
sprawdz("KONTRDOWOD: przed naprawa `dzien` konczyl sie bez wyjatku, czyli DONE",
        w3["PRZED"]["wyjatek"] is None, type(w3["PRZED"]["wyjatek"]).__name__)

print()
print("=== 5. ZWYKLA AWARIA WERYFIKACJI NADAL PRZEPUSZCZA (nie przesadzilem) ===")
# `ValueError` z `llm.parse_json` to awaria JEDNEGO wywolania: model poszedl,
# poszukal i oddal smiec. Budzet po niej istnieje, wiec „zepsuta weryfikacja
# nie jest dowodem falszu" ma dalej obowiazywac — i obowiazuje tak samo na
# obu drzewach.
z5 = {w: dzien(w, "factcheck", zly_json) for w in ("teraz", "PRZED")}
sprawdz("teraz: notka przy zlym JSON-ie nadal wychodzi",
        len(z5["teraz"]["slad"].notki) == 1, z5["teraz"]["slad"].notki)
sprawdz("teraz: komentarz przy zlym JSON-ie nadal wychodzi",
        len(z5["teraz"]["slad"].komentarze) == 1, z5["teraz"]["slad"].komentarze)
sprawdz("zachowanie IDENTYCZNE jak przed naprawa — nic tu nie zmieniono",
        (len(z5["teraz"]["slad"].notki), len(z5["teraz"]["slad"].komentarze))
        == (len(z5["PRZED"]["slad"].notki), len(z5["PRZED"]["slad"].komentarze)),
        (z5["teraz"]["slad"].notki, z5["PRZED"]["slad"].notki))
a5 = {w: artykul(w, "factcheck", zly_json) for w in ("teraz", "PRZED")}
sprawdz("artykul przy zlym JSON-ie nadal wychodzi, tak jak przed naprawa",
        [x["wyslij"] for x in a5["teraz"]["slad"].artykuly]
        == [x["wyslij"] for x in a5["PRZED"]["slad"].artykuly] != [],
        (a5["teraz"]["slad"].artykuly, a5["PRZED"]["slad"].artykuly))

print()
print("=== 6. BUDZET PADA NA RECENZJI ARTYKULU — CZTERY OSLONY W run.py ===")
# Recenzja jest polykana celowo (nic nie blokuje), ale na sciezce `--wyslij`
# za nia stoi `zweryfikuj` i `browser.wystaw_artykul`. Polkniecie budzetu tutaj
# to publikacja bez ani jednej dzialajacej kontroli.
r6 = {w: artykul(w, "review", budzet) for w in ("teraz", "PRZED")}
sprawdz("teraz: artykul nie wychodzi, gdy budzet padl na recenzji",
        r6["teraz"]["slad"].artykuly == [], r6["teraz"]["slad"].artykuly)
sprawdz("teraz: przebieg zamkniety raz, jako FAILED",
        len(r6["teraz"]["slad"].zamkniecia) == 1
        and r6["teraz"]["slad"].zamkniecia[0]["status"] == "FAILED",
        r6["teraz"]["slad"].zamkniecia)
sprawdz("KONTRDOWOD: przed naprawa szedl na Substacka mimo padnietej recenzji",
        [x for x in r6["PRZED"]["slad"].artykuly if x["wyslij"] is True],
        r6["PRZED"]["slad"].artykuly)

print()
print("=== 7. BUDZET PADA NA PISARZU — POWTORKA NA OPUSIE NIE RUSZA ===")
# `run.py` przy awarii pisarza powtarza na Opusie, ktory jest DROZSZY od tego,
# co wlasnie padlo. Przy pustym budzecie to drugie 0,76 USD za nic.
licznik = {"teraz": 0, "PRZED": 0}
for wersja in ("teraz", "PRZED"):
    stary_model = dict(config.MODEL_FOR)
    st, rn = para(wersja)
    slad = Slad()
    fs = stages_artykulu(slad, st)
    prawdziwy_write = fs.write

    def liczacy_write(conn, run_id, card, glebokosc, _w=wersja, _p=prawdziwy_write):
        licznik[_w] += 1
        raise budzet()

    fs.write = liczacy_write
    fake_gates = modul("gates",
                       deterministic_floors=lambda t, c, poprzednie=None: [],
                       uwagi_z_formy=lambda f, t: [],
                       verdict=lambda u: ("SAVED", ""),
                       pozycja_w_tekscie=lambda m, t: None)
    stary_browser = sys.modules.get("browser")
    sys.modules["browser"] = modul(
        "browser", wystaw_artykul=lambda s, wyslij=False: (
            slad.artykuly.append({"sciezka": str(s), "wyslij": wyslij})
            or {"wyslane": True, "blad": None}))
    stary_argv = sys.argv[:]
    try:
        rn.stages = fs
        rn.db = FalszywaBaza(slad)
        rn.gates = fake_gates
        rn.CACHE_DIR = KAT / "cache7"
        rn.zajmij_zamek = lambda: None
        rn.odmow_publikacji_z_kopii = lambda wyslij: None
        rn._sygnal_ma_zostawic_slad = lambda: None
        sys.argv = ["run.py", "--wyslij"]
        with contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()), \
                llm_pada(None, budzet):
            try:
                rn.main()
            except BaseException:   # noqa: BLE001
                pass
    finally:
        sys.argv = stary_argv
        if stary_browser is None:
            sys.modules.pop("browser", None)
        else:
            sys.modules["browser"] = stary_browser
        config.MODEL_FOR.clear()
        config.MODEL_FOR.update(stary_model)

sprawdz("teraz: `stages.write` wolany DOKLADNIE raz przy pustym budzecie",
        licznik["teraz"] == 1, licznik)
sprawdz("KONTRDOWOD: przed naprawa pisarz szedl DWA razy, drugi na drozszym modelu",
        licznik["PRZED"] == 2, licznik)

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
