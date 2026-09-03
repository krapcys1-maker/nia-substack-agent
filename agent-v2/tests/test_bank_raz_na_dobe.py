# -*- coding: utf-8 -*-
"""Bank ma sie uzupelniac RAZ NA DOBE, a wydarzenie ma otwierac furtke RAZ.

CO BYLO ZLE, zmierzone na produkcji 1 wrzesnia 2026:

  przez 3 dni:  6 razy "wielkie wydarzenie"  ->  6 pelnych szukan
                0 razy "bank pelny"          ->  bramka nie zatrzymala ANI RAZU
  za kazdym razem to samo zdarzenie: "5.3, acme" (premiera ACME sprzed kilku dni)

Sufit banku (`BANK_MAKS_WOLNYCH = 20`) mial to zatrzymywac. Nie zatrzymal,
bo stal jako `elif` pod galezia wydarzenia — a wydarzenie bylo wykrywane przy
KAZDYM z pieciu przebiegow dziennie i bylo wciaz to samo. Bank mial wtedy
58 wolnych pozycji z 69, czyli 58 pomyslow lezalo NIEUZYTYCH.

Cena, z tabeli `calls` (8 dni ery AI): 46 wywolan, srednio 266 517 tokenow
wejscia i 14,6 wyszukan w sieci na wywolanie, razem 3,65 USD — okolo
13,6 USD miesiecznie przy calym rachunku okolo 41 USD.

CZEGO TA POPRAWKA NIE ZABIERA. Pierwszenstwo wydarzenia ZOSTAJE. Wlasciciel:
„chce napisac o tym w tym samym dniu, max dzien po". NOWE zdarzenie przebija
limit dobowy tak jak dotad. Zmienia sie tylko to, ze o TYM SAMYM zdarzeniu
dobieramy material raz, a nie przy kazdym przebiegu.

TEST MIERZY ZACHOWANIE: czy model zostal zawolany. `llm.call` jest podmieniony
na funkcje, ktora RZUCA — wiec kazde niepotrzebne wywolanie wywala test, a nie
przechodzi niezauwazone. Zero asercji po tresci zrodla.

BEZ PYTESTA, zero sieci, zero platnych wywolan, produkcja nietknieta.
Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_bank_raz_na_dobe.py
"""
import hashlib
import io
import json
import pathlib
import sqlite3
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "agent-v2")
import config      # noqa: E402
import stages      # noqa: E402
import llm         # noqa: E402

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


PILNOWANE = [pathlib.Path(config.DB_PATH),
             config.DATA_DIR / "dziennik.jsonl",
             config.DATA_DIR / "wydarzenia_obsluzone.json"]
PRZED = {str(p): odcisk(p) for p in PILNOWANE}

DZIS = datetime.now(timezone.utc).date().isoformat()
ACME = {"o_czym": ["acme", "5.3"]}
ACME_INACZEJ = {"o_czym": ["5.3", "ACME"]}     # ta sama premiera, inna kolejnosc
INNE = {"o_czym": ["opus", "6"]}


def baza_z_przebiegami(ile_dzis: int) -> sqlite3.Connection:
    """Baza w pamieci z `ile_dzis` PRZEBIEGAMI, ktore dzis dobieraly do banku.

    Kazdy przebieg dostaje po dwa wywolania — bo jedno wejscie w
    `znajdz_ciekawostki` potrafi wolac model kilka razy i licznik ma liczyc
    PRZEBIEGI, nie wywolania.
    """
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE calls (id INTEGER PRIMARY KEY, run_id INT,"
              " at TEXT, purpose TEXT)")
    for r in range(ile_dzis):
        for _ in range(2):
            c.execute("INSERT INTO calls (run_id, at, purpose) VALUES (?,?,?)",
                      (100 + r, DZIS + "T10:00:00+00:00", "curiosity"))
    # Wczorajsze wywolania nie moga sie liczyc do dzisiejszego limitu.
    wczoraj = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
    for r in range(5):
        c.execute("INSERT INTO calls (run_id, at, purpose) VALUES (?,?,?)",
                  (200 + r, wczoraj + "T10:00:00+00:00", "curiosity"))
    return c


KAT = pathlib.Path(tempfile.mkdtemp())
ORYG_PAMIEC = stages.WYDARZENIA_OBSLUZONE
ORYG_CALL = llm.call
ORYG_BANK = stages.bank_pelny


def model_zabroniony(*a, **k):
    raise AssertionError("model zostal zawolany, a nie powinien")


try:
    stages.WYDARZENIA_OBSLUZONE = KAT / "wydarzenia.json"
    llm.call = model_zabroniony

    print("=== 1. LICZNIK LICZY PRZEBIEGI, NIE WYWOLANIA ===")
    sprawdz("zero przebiegow dzis", stages._przebiegi_z_bankiem_dzis(
        baza_z_przebiegami(0)) == 0)
    sprawdz("jeden przebieg (dwa wywolania) liczy sie jako JEDEN",
            stages._przebiegi_z_bankiem_dzis(baza_z_przebiegami(1)) == 1)
    sprawdz("trzy przebiegi to trzy", stages._przebiegi_z_bankiem_dzis(
        baza_z_przebiegami(3)) == 3)
    sprawdz("wczorajsze wywolania nie licza sie do dzisiaj",
            stages._przebiegi_z_bankiem_dzis(baza_z_przebiegami(0)) == 0)

    print()
    print("=== 2. TO SAMO WYDARZENIE OTWIERA FURTKE RAZ ===")
    nowe, znane = stages._nowe_wydarzenia([ACME])
    sprawdz("pierwszy raz: zdarzenie jest NOWE", len(nowe) == 1, nowe)
    stages._zapamietaj_wydarzenia(nowe, znane, 8)  # 8 faktow wrocilo
    nowe2, _ = stages._nowe_wydarzenia([ACME])
    sprawdz("drugi raz: to samo zdarzenie NIE jest juz nowe",
            nowe2 == [], nowe2)
    nowe3, _ = stages._nowe_wydarzenia([ACME_INACZEJ])
    sprawdz("inna kolejnosc slow to WCIAZ to samo zdarzenie",
            nowe3 == [], nowe3)
    nowe4, znane4 = stages._nowe_wydarzenia([ACME, INNE])
    sprawdz("ale INNE zdarzenie przechodzi", len(nowe4) == 1
            and stages._rdzen_wydarzenia(nowe4[0]) == "6,opus", nowe4)

    print()
    print("=== 3. PAMIEC WYGASA PO OKNIE — TEMAT MOZE ODZYC ===")
    stara = KAT / "wydarzenia.json"
    dawno = (datetime.now(timezone.utc)
             - timedelta(days=config.WYDARZENIE_WAZNE_DNI + 1)).date().isoformat()
    stara.write_text(json.dumps({"5.3,acme": dawno}), encoding="utf-8")
    nowe5, _ = stages._nowe_wydarzenia([ACME])
    sprawdz("zdarzenie sprzed %d dni znowu jest nowe"
            % (config.WYDARZENIE_WAZNE_DNI + 1), len(nowe5) == 1, nowe5)
    wczoraj = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
    stara.write_text(json.dumps({"5.3,acme": wczoraj}), encoding="utf-8")
    nowe6, _ = stages._nowe_wydarzenia([ACME])
    sprawdz("ale wczorajsze jeszcze NIE (okno %d dni)"
            % config.WYDARZENIE_WAZNE_DNI, nowe6 == [], nowe6)

    print()
    print("=== 4. ZACHOWANIE: MODEL NIE JEST WOLANY, GDY NIE TRZEBA ===")
    # Zdarzen brak, dzis juz dobieralismy -> ma wyjsc pusto i BEZ modelu.
    stara.write_text(json.dumps({}), encoding="utf-8")
    stages.bank_pelny = lambda: False        # sufit banku NIE jest tu powodem
    import korpus_kanalow                    # noqa: E402
    oryg_korpus = korpus_kanalow.korpus_kanalow
    oryg_wyd = korpus_kanalow.wielkie_wydarzenia
    try:
        korpus_kanalow.korpus_kanalow = lambda *a, **k: []
        korpus_kanalow.wielkie_wydarzenia = lambda *a, **k: []
        wynik = stages.znajdz_ciekawostki(baza_z_przebiegami(1), 1)
        sprawdz("dzis juz dobieralismy -> pusto, model NIE wolany", wynik == [],
                wynik)

        # Ten sam stan, ale bank pelny i zero przebiegow -> tez pusto.
        stages.bank_pelny = lambda: True
        wynik2 = stages.znajdz_ciekawostki(baza_z_przebiegami(0), 1)
        sprawdz("bank pelny i brak zdarzen -> pusto, model NIE wolany",
                wynik2 == [], wynik2)

        # NOWE zdarzenie ma przebic limit dobowy — model DOSTAJE szanse.
        # DOWODEM JEST LICZNIK WYWOLAN, nie zlapany wyjatek: etap lapie bledy
        # modelu szeroko (`except Exception` przy `llm.call`), wiec z samego
        # wyjatku nie da sie wnioskowac, czy do wywolania w ogole doszlo.
        stages.bank_pelny = lambda: True
        korpus_kanalow.wielkie_wydarzenia = lambda *a, **k: [dict(INNE)]
        licznik = {"n": 0}

        def liczacy(*a, **k):
            # LICZYMY TYLKO SZUKANIE DO BANKU. Jedno wejscie w etap wola model
            # DWA razy: raz po stan modeli (`aktualne_modele`), raz po material
            # (`curiosity`). Liczenie obu dawalo 2, 6, 6 zamiast 1, 3, 3 —
            # i wygladalo jak zepsuta bramka, choc bramka dzialala.
            if a and a[0] == "curiosity":
                licznik["n"] += 1
                raise RuntimeError("model niedostepny")   # material NIE wraca
            return "{}"

        llm.call = liczacy
        stages.znajdz_ciekawostki(baza_z_przebiegami(5), 1)
        sprawdz("NOWE zdarzenie przebija limit dobowy i pelny bank",
                licznik["n"] == 1, licznik)

        # OD 2 WRZESNIA 2026 nieudana proba NIE zamyka furtki — znacznik
        # notuje SKUTEK, nie zamiar (`test_furtka_wydarzenia.py`). Ale liczba
        # prob jest ograniczona, zeby padajace szukanie nie chodzilo przy
        # kazdym z pieciu przebiegow dziennie.
        for _ in range(config.WYDARZENIE_PROB_MAKS - 1):
            stages.znajdz_ciekawostki(baza_z_przebiegami(5), 1)
        sprawdz("nieudane proby dostaja szanse az do limitu (%d)"
                % config.WYDARZENIE_PROB_MAKS,
                licznik["n"] == config.WYDARZENIE_PROB_MAKS, licznik)

        stages.znajdz_ciekawostki(baza_z_przebiegami(5), 1)
        sprawdz("po limicie prob furtka sie zamyka — model NIE wolany",
                licznik["n"] == config.WYDARZENIE_PROB_MAKS, licznik)
    finally:
        korpus_kanalow.korpus_kanalow = oryg_korpus
        korpus_kanalow.wielkie_wydarzenia = oryg_wyd
finally:
    stages.WYDARZENIA_OBSLUZONE = ORYG_PAMIEC
    llm.call = ORYG_CALL
    stages.bank_pelny = ORYG_BANK

print()
print("=== PRODUKCJA ===")
zle = 0
for p in PILNOWANE:
    ok = odcisk(p) == PRZED[str(p)]
    zle += 0 if ok else 1
    print("  %-28s %s" % (pathlib.Path(p).name, "bez zmian" if ok else "ZMIENIONA"))

print()
print("=== WYNIK: %d zdanych, %d oblanych%s ===" %
      (zdane, oblane, ", PRODUKCJA RUSZONA" if zle else ""))
sys.exit(1 if (oblane or zle) else 0)
