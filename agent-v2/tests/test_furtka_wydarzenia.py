# -*- coding: utf-8 -*-
"""Furtka wydarzenia zamyka sie DOPIERO, gdy material naprawde wrocil.

CO BYLO ZLE, zmierzone na produkcji 2 wrzesnia 2026:

  09:43:48 UTC  serwer pobral poprawke wykrywania premier
  09:44:51 UTC  `wydarzenia_obsluzone.json` dostal wpis "5.1,fable": "2026-09-02"
  platnych wywolan tego dnia do 11:34:  ZERO
  pozycji o Fable w banku (69 pozycji):  ZERO
  przebieg o 11:34 wypisal: "wszystkie juz obsluzone wczesniej"

Czyli: recznie uruchomione sprawdzenie po wdrozeniu weszlo w galaz wydarzenia,
odhaczylo premiere Fable 5.1 jako obsluzona i wyszlo BEZ materialu. Znacznik
notowal ZAMIAR, nie skutek — `_zapamietaj_wydarzenia` stalo PRZED szukaniem.

Dlaczego to znaczy STRACONE, a nie odlozone: `WYDARZENIE_WAZNE_DNI = 2`, a okno
swiezosci korpusu to cztery doby. Znacznik przestaje blokowac dokladnie wtedy,
gdy filmy o premierze wypadaja z okna.

TO JEST TA SAMA KLASA BLEDU, co "nieudana publikacja ksiegowana jako sukces"
(naprawiona tego samego dnia rano): stan zapisany z gory, zanim wiadomo, czy
cokolwiek z tego wyszlo.

KONTRDOWOD JEST ODTWARZANY, NIE OPISYWANY. Test importuje PRAWDZIWY stary
`stages.py` z commita `426d9ea` i pokazuje, ze na nim awaria zachodzi, a na
dzisiejszym kodzie nie. Stary kod jest przypiety do SHA, NIE do HEAD — test
mierzony wobec HEAD gasnie przy wlasnym commicie i ten projekt juz raz na to
wpadl (`64d881a`).

BEZ PYTESTA, zero sieci, zero platnych wywolan, produkcja nietknieta.
Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_furtka_wydarzenia.py
"""
import hashlib
import importlib.util
import json
import pathlib
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "agent-v2")
import config      # noqa: E402
import stages      # noqa: E402
import llm         # noqa: E402

# HISTORIA JEST WARUNKIEM TEGO TESTU. Kontrdowod ponizej odtwarza sie
# z commita sprzed naprawy, wiec w kopii z historia zalozona od nowa
# nie ma z czego go odtworzyc. Pominiecie jest wtedy JAWNE, zamiast
# wywalac sie w polowie pliku na `CalledProcessError`.
import historia   # noqa: E402
historia.wymaga_historii("426d9ea")

STARY_SHA = "426d9ea"       # ostatni commit PRZED ta poprawka
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
             config.DATA_DIR / "wydarzenia_obsluzone.json",
             config.DATA_DIR / "indeks_kandydatow.json"]
PRZED = {str(p): odcisk(p) for p in PILNOWANE}

KAT = pathlib.Path(tempfile.mkdtemp())
DZIS = datetime.now(timezone.utc).date().isoformat()
FABLE = {"o_czym": ["5.1", "fable"], "kanalow": 2,
         "kanaly": ["Kanal Newsowy", "Kanal Produktowy"],
         "tytuly": ["Fable 5.1 just smoked ASTRA"], "premiera": True}

FAKT = {"fact": "Something verifiable happened.", "url": "https://example.org/a",
        "domain": "example.org", "wrong_belief": "b", "actually": "c"}


def baza():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE calls (id INTEGER PRIMARY KEY, run_id INTEGER,"
              " at TEXT, purpose TEXT)")
    return c


def zaladuj_stary():
    """Prawdziwy `stages.py` z commita sprzed poprawki, jako osobny modul."""
    zrodlo = subprocess.run(
        ["git", "show", "%s:agent-v2/stages.py" % STARY_SHA],
        capture_output=True, check=True).stdout.decode("utf-8")
    plik = KAT / "stages_stary.py"
    plik.write_bytes(zrodlo.encode("utf-8"))
    spec = importlib.util.spec_from_file_location("stages_stary", plik)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["stages_stary"] = mod
    spec.loader.exec_module(mod)
    return mod


def uruchom(modul, plik_pamieci, fakty_z_modelu):
    """Jedno wejscie w `znajdz_ciekawostki` z atrapami. Oddaje tresc pliku."""
    import aktualne_modele
    import korpus_kanalow
    oryg = (llm.call, korpus_kanalow.korpus_kanalow,
            korpus_kanalow.wielkie_wydarzenia, aktualne_modele.pobierz,
            aktualne_modele.jako_tekst, modul.dopisz_kandydatow,
            modul.WYDARZENIA_OBSLUZONE)
    try:
        modul.WYDARZENIA_OBSLUZONE = plik_pamieci
        modul.dopisz_kandydatow = lambda *a, **k: None     # produkcja nietknieta
        korpus_kanalow.korpus_kanalow = lambda *a, **k: []
        korpus_kanalow.wielkie_wydarzenia = lambda *a, **k: [dict(FABLE)]
        aktualne_modele.pobierz = lambda *a, **k: []
        aktualne_modele.jako_tekst = lambda *a, **k: ""
        llm.call = lambda *a, **k: json.dumps({"facts": fakty_z_modelu})
        try:
            modul.znajdz_ciekawostki(baza(), 1, ile=2)
        except Exception as exc:           # awaria etapu nie jest tematem testu
            print("    (etap rzucil %s — dla tego testu bez znaczenia)"
                  % type(exc).__name__)
    finally:
        (llm.call, korpus_kanalow.korpus_kanalow,
         korpus_kanalow.wielkie_wydarzenia, aktualne_modele.pobierz,
         aktualne_modele.jako_tekst, modul.dopisz_kandydatow,
         modul.WYDARZENIA_OBSLUZONE) = oryg
    try:
        return json.loads(plik_pamieci.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


print("=== 1. KONTRDOWOD NA PRAWDZIWYM STARYM KODZIE (%s) ===" % STARY_SHA)
stary = zaladuj_stary()
p1 = KAT / "stary.json"
stan = uruchom(stary, p1, [])       # model nie oddaje materialu — jak 2 wrzesnia
sprawdz("stary kod ODHACZA wydarzenie mimo ZERA materialu (awaria odtworzona)",
        "5.1,fable" in stan, stan)

print()
print("=== 2. DZISIEJSZY KOD W TEJ SAMEJ SYTUACJI ===")
p2 = KAT / "nowy.json"
stan2 = uruchom(stages, p2, [])
# Wpis MOZE powstac — ale jako PROBA, nie jako obsluzenie. Pytamy wiec
# o zachowanie (`_nowe_wydarzenia`), a nie o obecnosc klucza w pliku:
# to samo pytanie zada produkcja przy nastepnym przebiegu.
wpis2 = stan2.get("5.1,fable")
sprawdz("material nie wrocil, wiec znacznik nie moze mowic, ze wrocil",
        wpis2 is None or int((wpis2 or {}).get("ile") or 0) == 0, wpis2)
oryg2 = stages.WYDARZENIA_OBSLUZONE
try:
    stages.WYDARZENIA_OBSLUZONE = p2
    n2, _ = stages._nowe_wydarzenia([dict(FABLE)])
    sprawdz("furtka ZOSTAJE OTWARTA — wydarzenie nadal NOWE", len(n2) == 1, n2)
finally:
    stages.WYDARZENIA_OBSLUZONE = oryg2

print()
print("=== 3. GDY MATERIAL WROCIL — FURTKA SIE ZAMYKA ===")
p3 = KAT / "udany.json"
stan3 = uruchom(stages, p3, [dict(FAKT),
                             dict(FAKT, url="https://example.org/b",
                                  fact="Second one.")])
wpis = stan3.get("5.1,fable")
sprawdz("wydarzenie odhaczone", bool(wpis), stan3)
sprawdz("znacznik niesie DOWOD: ile faktow wrocilo",
        isinstance(wpis, dict) and int(wpis.get("ile") or 0) > 0, wpis)
sprawdz("i date", isinstance(wpis, dict) and wpis.get("kiedy") == DZIS, wpis)

print()
print("=== 4. WPIS Z ZEREM NIE ZAMYKA FURTKI (druga linia obrony) ===")
p4 = KAT / "zero.json"
oryg_pamiec = stages.WYDARZENIA_OBSLUZONE
try:
    stages.WYDARZENIA_OBSLUZONE = p4
    p4.write_text(json.dumps({"5.1,fable": {"kiedy": DZIS, "ile": 0}}),
                  encoding="utf-8")
    n4, _ = stages._nowe_wydarzenia([dict(FABLE)])
    sprawdz("wpis z ile=0 znaczy NIEOBSLUZONE", len(n4) == 1, n4)

    p4.write_text(json.dumps({"5.1,fable": {"kiedy": DZIS, "ile": 5}}),
                  encoding="utf-8")
    n5, _ = stages._nowe_wydarzenia([dict(FABLE)])
    sprawdz("wpis z ile=5 zamyka furtke", n5 == [], n5)

    print()
    print("=== 5. STARY FORMAT PLIKU CZYTA SIE NADAL (bez migracji) ===")
    p4.write_text(json.dumps({"5.1,fable": DZIS}), encoding="utf-8")
    n6, _ = stages._nowe_wydarzenia([dict(FABLE)])
    sprawdz("sam napis z data nadal zamyka furtke", n6 == [], n6)
    dawno = (datetime.now(timezone.utc)
             - timedelta(days=config.WYDARZENIE_WAZNE_DNI + 1)).date().isoformat()
    p4.write_text(json.dumps({"5.1,fable": dawno}), encoding="utf-8")
    n7, _ = stages._nowe_wydarzenia([dict(FABLE)])
    sprawdz("stary wpis sprzed okna znowu przepuszcza", len(n7) == 1, n7)
finally:
    stages.WYDARZENIA_OBSLUZONE = oryg_pamiec

print()
print("=== PRODUKCJA ===")
zle = 0
for p in PILNOWANE:
    ok = odcisk(p) == PRZED[str(p)]
    zle += 0 if ok else 1
    stan_p = ("nie istnial i nie istnieje" if odcisk(p) == "brak"
              else ("bez zmian" if ok else "ZMIENIONA"))
    print("  %-28s %s" % (pathlib.Path(p).name, stan_p))

print()
print("=== WYNIK: %d zdanych, %d oblanych%s ===" %
      (zdane, oblane, ", PRODUKCJA RUSZONA" if zle else ""))
sys.exit(1 if (oblane or zle) else 0)
