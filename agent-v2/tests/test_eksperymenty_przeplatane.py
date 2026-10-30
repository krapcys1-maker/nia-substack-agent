# -*- coding: utf-8 -*-
"""Eksperymenty przeplatane: mechanizm jest, a przy pustym rejestrze NIC nie zmienia.

PO CO TO ISTNIEJE. Porownanie „przed i po" myli zmiane z trendem konta: zasieg
notek zmienia sie z tygodnia na tydzien bez zadnej zmiany w kodzie. Uczciwe
porownanie to dwie grupy w TYM SAMYM okresie — czesc notek ze zmiana, czesc
bez, przydzielone deterministycznie (`stages.ramie`), z ramieniem zapisanym
w dzienniku obok wyniku.

Ten plik pilnuje czterech rzeczy naraz, ZACHOWANIEM, nie odczytem kodu:

  1. PUSTY REJESTR = ZERO ZMIAN. `config.EKSPERYMENTY` jest domyslnie pusty,
     `ramie` oddaje wtedy "", a wpis notki w dzienniku nie dostaje nowego pola.
     To jest warunek wlaczenia mechanizmu do dzialajacego bota.
  2. PRZYDZIAL JEST POWTARZALNY I TRZYMA UDZIAL. Ten sam slot zawsze w tym
     samym ramieniu — inaczej nie da sie go odtworzyc z dziennika — a dwa
     eksperymenty naraz nie mieszaja ramion.
  3. OKNO DAT I PLAN Z KALENDARZA. Eksperyment sam startuje i sam sie konczy;
     ramie z kalendarza liczy okresy od daty startu.
  4. RAMIONA DOCHODZA DO DZIENNIKA. `run.py` przekazuje je do
     `browser.wystaw_notke`, a ta do wpisu — tylko wtedy, gdy sa.

Wartosci przypiete w sekcji 2 sa po to, zeby nikt nie zmienil wzoru losowania
po cichu: ramiona zapisane w dzienniku przed zmiana przestalyby sie zgadzac
z tym, co liczy kod.

BEZ PYTESTA, zero sieci, zero platnych wywolan, produkcja nietknieta.
Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_eksperymenty_przeplatane.py
"""
import ast
import contextlib
import hashlib
import io
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import config      # noqa: E402

# PRAWDZIWE sciezki produkcji zapamietane PRZED przelaczeniem — to one sa
# pilnowane na koncu.
PROD_DB = pathlib.Path(config.DB_PATH)
PROD_DZIENNIK = pathlib.Path(config.DATA_DIR) / "dziennik.jsonl"

KAT = pathlib.Path(tempfile.mkdtemp())
STARE_SCIEZKI = config.uzyj_katalogu_danych(KAT)

import browser     # noqa: E402
import stages      # noqa: E402

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


PILNOWANE = [PROD_DB, PROD_DZIENNIK]
PRZED = {str(p): odcisk(p) for p in PILNOWANE}
REJESTR_DOSTARCZONY = config.EKSPERYMENTY


@contextlib.contextmanager
def rejestr(wpisy):
    """Podstawia `config.EKSPERYMENTY` na czas jednego sprawdzenia."""
    stary = config.EKSPERYMENTY
    config.EKSPERYMENTY = wpisy
    try:
        yield
    finally:
        config.EKSPERYMENTY = stary


DNI = ["2026-10-%02d" % d for d in range(1, 31)]

try:
    print("=== 1. PUSTY REJESTR = WSZYSTKO JAK ZAWSZE ===")
    sprawdz("rejestr jest domyslnie pusty",
            REJESTR_DOSTARCZONY == {}, REJESTR_DOSTARCZONY)
    puste = {stages.ramie(n, m, d) for n in ("cokolwiek", "inny")
             for m in range(6) for d in DNI}
    sprawdz("bez wpisu `ramie` oddaje \"\" dla kazdej nazwy, slotu i dnia",
            puste == {""}, puste)
    with rejestr(None):
        sprawdz("rejestr ustawiony na None tez nie wywraca bota",
                stages.ramie("cokolwiek", 0, "2026-10-12") == "")
    with rejestr({"inny": 1.0}):
        sprawdz("wpis o innej nazwie nie obejmuje pytanego eksperymentu",
                stages.ramie("cokolwiek", 0, "2026-10-12") == "")

    print()
    print("=== 2. PRZYDZIAL POWTARZALNY, UDZIAL TRZYMANY ===")
    with rejestr({"wzor": 0.5}):
        pierwsze = [stages.ramie("wzor", m, d) for d in DNI for m in range(40)]
        drugie = [stages.ramie("wzor", m, d) for d in DNI for m in range(40)]
        sprawdz("ten sam slot = to samo ramie przy kazdym wywolaniu",
                pierwsze == drugie)
        sprawdz("ramiona to tylko \"on\" i \"off\"",
                set(pierwsze) == {"on", "off"}, set(pierwsze))
        # PRZYPIETE WARTOSCI — wzor sha256(nazwa|dzien|miejsce), pierwsze
        # 8 cyfr szesnastkowych / 2^32. Policzone raz i zapisane tutaj.
        przypiete = [stages.ramie("wzor", m, "2026-10-12") for m in range(4)]
        sprawdz("przypiete ramiona dnia 2026-10-12, sloty 0-3",
                przypiete == ["on", "off", "on", "on"], przypiete)
        sprawdz("przypiete ramie slotu 0 nastepnego dnia",
                stages.ramie("wzor", 0, "2026-10-13") == "on")
        sprawdz("klucz tekstowy zamiast numeru (np. cel komentarza)",
                stages.ramie("wzor", "cel@autor-1", "2026-10-12") == "off")
        sprawdz("znacznik czasu daje to samo ramie co sama data",
                stages.ramie("wzor", 3, "2026-10-12T23:59:00+00:00")
                == stages.ramie("wzor", 3, "2026-10-12"))
    with rejestr({"wzor": 0.2}):
        sprawdz("prog dziala w obie strony: los 0,155 i 0,197 -> on, 0,297 -> off",
                [stages.ramie("wzor", m, "2026-10-12") for m in (0, 2, 3)]
                == ["on", "on", "off"])

    with rejestr({"siedem": 0.7}):
        ramiona = [stages.ramie("siedem", m, d) for d in DNI for m in range(100)]
        udzial = ramiona.count("on") / len(ramiona)
        sprawdz("udzial 0,7 daje 0,7 +-0,03 na %d slotach" % len(ramiona),
                abs(udzial - 0.7) < 0.03, round(udzial, 3))
    with rejestr({"zero": 0.0, "jeden": 1.0}):
        sprawdz("udzial 0 = zawsze \"off\"",
                {stages.ramie("zero", m, d) for d in DNI for m in range(10)} == {"off"})
        sprawdz("udzial 1 = zawsze \"on\"",
                {stages.ramie("jeden", m, d) for d in DNI for m in range(10)} == {"on"})

    # DWA EKSPERYMENTY NARAZ. Gdyby oba losowaly z tego samego (dzien, slot),
    # „on" jednego byloby zawsze „on" drugiego i skutku nie dalo sie rozdzielic.
    with rejestr({"a": 0.5, "b": {"udzial": 0.5}}):
        pary = [(stages.ramie("a", m, d), stages.ramie("b", m, d))
                for d in DNI for m in range(100)]
        oba = sum(1 for x in pary if x == ("on", "on")) / len(pary)
        zgodne = sum(1 for x, y in pary if x == y) / len(pary)
        sprawdz("dwa eksperymenty nie mieszaja ramion: oba \"on\" ~ 0,25",
                abs(oba - 0.25) < 0.03, round(oba, 3))
        sprawdz("i zgadzaja sie w ~polowie slotow, nie zawsze",
                abs(zgodne - 0.5) < 0.04, round(zgodne, 3))

    print()
    print("=== 3. OKNO DAT I PLAN Z KALENDARZA ===")
    with rejestr({"okno": {"udzial": 1.0, "od": "2026-10-10", "do": "2026-10-20"}}):
        sprawdz("dzien przed startem: eksperymentu nie ma",
                stages.ramie("okno", 0, "2026-10-09") == "")
        sprawdz("pierwszy i ostatni dzien okna: trwa",
                stages.ramie("okno", 0, "2026-10-10") == "on"
                and stages.ramie("okno", 0, "2026-10-20") == "on")
        sprawdz("dzien po koncu: eksperyment sam sie skonczyl",
                stages.ramie("okno", 0, "2026-10-21") == "")
    with rejestr({"dni": {"plan": ["on", "off"], "okres_dni": 1, "od": "2026-10-01"}}):
        sprawdz("plan dzienny: na przemian od daty startu",
                [stages.ramie("dni", 0, d) for d in DNI[:4]] == ["on", "off", "on", "off"])
        sprawdz("w planie slot nie ma znaczenia — cala doba w jednym ramieniu",
                {stages.ramie("dni", m, "2026-10-02") for m in range(10)} == {"off"})
    with rejestr({"tyg": {"plan": ["on", "off", "off", "on"], "okres_dni": 7,
                          "od": "2026-10-01", "do": "2026-11-30"}}):
        tygodnie = [stages.ramie("tyg", 0, d) for d in
                    ("2026-10-01", "2026-10-07", "2026-10-08", "2026-10-15",
                     "2026-10-22", "2026-10-29")]
        sprawdz("plan tygodniowy: okres k dostaje plan[k % dlugosc]",
                tygodnie == ["on", "on", "off", "off", "on", "on"], tygodnie)
    with rejestr({"bez_startu": {"plan": ["on", "off"], "okres_dni": 1}}):
        sprawdz("plan bez daty startu nie trwa (brak okresu zero)",
                stages.ramie("bez_startu", 0, "2026-10-12") == "")

    print()
    print("=== 4. RAMIONA DOCHODZA DO DZIENNIKA — I TYLKO WTEDY, GDY SA ===")
    zapisane = []

    def atrapa_dziennika(rodzaj, wynik, **szczegoly):
        zapisane.append(dict(szczegoly, rodzaj=rodzaj))

    class _Strona:
        """Padnie DOPIERO w `goto`, czyli juz wewnatrz `try` — wtedy wpis
        robi `finally`, ta sama droga co przy kazdej porazce publikacji."""

        def goto(self, *a, **k):
            raise RuntimeError("przegladarka niedostepna w tescie")

        def close(self, *a, **k):
            return None

        def __getattr__(self, _):
            return lambda *a, **k: None

    class _Kontekst:
        def new_page(self):
            return _Strona()

        def __getattr__(self, _):
            return lambda *a, **k: None

    PODMIANY = {
        "dopisz_wynik": atrapa_dziennika,
        "wymagaj_sesji": lambda *a, **k: None,
        "wymagaj_wlasciwego_konta": lambda *a, **k: None,
        "potwierdz_notke": lambda *a, **k: False,
        # DARMOWY TEST NIE MA PRAWA PUBLIKOWAC i `naprawde_wyslac` slusznie
        # na to nie pozwala — ale wtedy galaz zapisu do dziennika w ogole sie
        # nie wykonuje. Przegladarka jest atrapa, wiec nic nie ma dokad wyjsc.
        "naprawde_wyslac": lambda wyslij, co: True,
        "podlacz_sie": lambda *a, **k: (_Kontekst(), _Kontekst(), _Kontekst()),
    }
    ORYGINALY = {n: getattr(browser, n) for n in PODMIANY}

    def wystaw(**k):
        zapisane.clear()
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                browser.wystaw_notke("tekst probny", wyslij=True, typ="MYSL",
                                     forma="PROSTA", model="pisarz-testowy", **k)
            except Exception:
                pass
        return zapisane[-1] if zapisane else {}

    try:
        for n, f in PODMIANY.items():
            setattr(browser, n, f)
        bez = wystaw()
        sprawdz("wpis bez eksperymentu powstal (atrapa trafiona)",
                bez.get("rodzaj") == "notka" and bez.get("model") == "pisarz-testowy",
                bez)
        sprawdz("bez eksperymentu wpis NIE ma pola `eksperymenty`",
                "eksperymenty" not in bez, sorted(bez))
        sprawdz("pusty slownik ramion tez go nie dodaje",
                "eksperymenty" not in wystaw(eksperymenty={}))
        ramiona = {"wzor": "on", "drugi": "off"}
        z = wystaw(eksperymenty=ramiona)
        sprawdz("ramiona notki ida do wpisu w dzienniku",
                z.get("eksperymenty") == {"wzor": "on", "drugi": "off"},
                z.get("eksperymenty"))
        sprawdz("a reszta wpisu jest taka jak bez eksperymentu",
                {k: v for k, v in z.items() if k != "eksperymenty"} == bez,
                sorted(set(z) ^ set(bez)))
        ramiona["wzor"] = "off"
        sprawdz("wpis trzyma kopie — pozniejsza zmiana slownika go nie rusza",
                z.get("eksperymenty", {}).get("wzor") == "on")
    finally:
        for n, f in ORYGINALY.items():
            setattr(browser, n, f)

    # RUN.PY PRZEKAZUJE RAMIONA NOTKI. Sprawdzane na drzewie skladni wywolania
    # publikujacego `gotowe[0]` — tego samego, ktore niesie pole `model`.
    drzewo = ast.parse(pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8"))
    wolania = [w for w in ast.walk(drzewo)
               if isinstance(w, ast.Call)
               and getattr(w.func, "attr", None) == "wystaw_notke"
               and w.args and "gotowe[0]" in ast.unparse(w.args[0])]
    sprawdz("run.py ma jedno wywolanie publikujace notke z banku",
            len(wolania) == 1, len(wolania))
    slowa = {k.arg: ast.unparse(k.value) for w in wolania for k in w.keywords}
    sprawdz("i przekazuje w nim `eksperymenty=n.get('eksperymenty')`",
            slowa.get("eksperymenty") == "n.get('eksperymenty')",
            slowa.get("eksperymenty"))
finally:
    config.przywroc_katalog_danych(STARE_SCIEZKI)

print()
print("=== PRODUKCJA ===")
zle = 0
for p in PILNOWANE:
    ok = odcisk(p) == PRZED[str(p)]
    zle += 0 if ok else 1
    print("  %-28s %s" % (pathlib.Path(p).name,
                          "nie istnial i nie istnieje" if odcisk(p) == "brak"
                          else ("bez zmian" if ok else "ZMIENIONA")))

print()
print("=== WYNIK: %d zdanych, %d oblanych%s ===" %
      (zdane, oblane, ", PRODUKCJA RUSZONA" if zle else ""))
sys.exit(1 if (oblane or zle) else 0)
