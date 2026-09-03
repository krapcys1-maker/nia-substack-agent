"""Test licznika dziennego: komentarze i polubienia z dziennika, notki z Substacka.

Zadna atrapa. Kazdy przypadek pisze prawdziwy plik dziennika i czyta go tym samym
kodem, ktorego uzywa agent w przebiegu.
"""
import json
import pathlib
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "agent-v2")
import browser  # noqa: E402
import config   # noqa: E402

TERAZ = datetime.now(timezone.utc)
DZIS = TERAZ.strftime("%Y-%m-%d")
WCZORAJ = (TERAZ - timedelta(days=1)).strftime("%Y-%m-%d")

zdane = 0
oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


def wpis(rodzaj, udane=True, data=None, godzina="10:00:00"):
    return json.dumps({"kiedy": "%sT%s+00:00" % (data or DZIS, godzina),
                       "rodzaj": rodzaj, "udane": udane}, ensure_ascii=False)


def ustaw(linie):
    kat = pathlib.Path(tempfile.mkdtemp())
    plik = kat / "dziennik.jsonl"
    plik.write_text("\n".join(linie) + ("\n" if linie else ""), encoding="utf-8")
    browser.DZIENNIK = plik
    return plik


ORYGINAL = browser.DZIENNIK

def tylko(d, *klucze):
    """Porownuje WYBRANE klucze, nie caly slownik.

    Poprzednia wersja sprawdzala rownosc calego slownika, wiec kazdy nowy
    rodzaj dzialania (restacki) wywracal dziewiec asercji naraz, mimo ze
    wszystkie liczby byly poprawne. Test ma pilnowac tego, o co pyta.
    """
    return {k: d.get(k, 0) for k in klucze}


print("=== 1. PODSTAWY ===")

browser.DZIENNIK = pathlib.Path(tempfile.mkdtemp()) / "nie-ma-mnie.jsonl"
w = browser.z_dziennika_dzis()
sprawdz("brak pliku dziennika -> zera, bez wyjatku",
        tylko(w, "komentarze", "lajki") == {"komentarze": 0, "lajki": 0}, w)

ustaw([])
w = browser.z_dziennika_dzis()
sprawdz("pusty dziennik -> zera", tylko(w, "komentarze", "lajki") == {"komentarze": 0, "lajki": 0}, w)

ustaw([wpis("komentarz"), wpis("komentarz"), wpis("polubienie")])
w = browser.z_dziennika_dzis()
sprawdz("liczy dzisiejsze komentarze i polubienia",
        tylko(w, "komentarze", "lajki") == {"komentarze": 2, "lajki": 1}, w)

print()
print("=== 2. CZEGO LICZYC NIE WOLNO ===")

ustaw([wpis("komentarz", udane=False), wpis("polubienie", udane=False)])
w = browser.z_dziennika_dzis()
sprawdz("nieudane dzialania NIE licza sie do normy",
        tylko(w, "komentarze", "lajki") == {"komentarze": 0, "lajki": 0}, w)

ustaw([wpis("komentarz", data=WCZORAJ), wpis("polubienie", data=WCZORAJ)])
w = browser.z_dziennika_dzis()
sprawdz("wczorajsze NIE licza sie do dzisiejszej normy",
        tylko(w, "komentarze", "lajki") == {"komentarze": 0, "lajki": 0}, w)

ustaw([wpis("notka"), wpis("odpowiedz"), wpis("odpowiedz_pod_artykulem"),
       wpis("artykul"), wpis("subskrypcja")])
w = browser.z_dziennika_dzis()
sprawdz("odpowiedzi, notki, artykul i subskrypcja NIE sa komentarzami",
        tylko(w, "komentarze", "lajki") == {"komentarze": 0, "lajki": 0}, w)

print()
print("=== 3. ODPORNOSC — dziennik nie moze zatrzymac przebiegu ===")

ustaw([wpis("komentarz"), "{to nie jest json", wpis("polubienie"),
       "", "   ", "null", "[1,2,3]", wpis("komentarz")])
w = browser.z_dziennika_dzis()
sprawdz("uszkodzone linie pomijane, reszta policzona",
        tylko(w, "komentarze", "lajki") == {"komentarze": 2, "lajki": 1}, w)

browser.DZIENNIK = pathlib.Path(tempfile.mkdtemp())   # katalog, nie plik
try:
    w = browser.z_dziennika_dzis()
    sprawdz("nieczytelny dziennik -> zera zamiast wyjatku",
            tylko(w, "komentarze", "lajki") == {"komentarze": 0, "lajki": 0}, w)
except Exception as exc:
    sprawdz("nieczytelny dziennik -> zera zamiast wyjatku", False,
            "polecial %s" % type(exc).__name__)

ustaw([json.dumps({"kiedy": "%sT10:00:00+00:00" % DZIS, "rodzaj": "komentarz"})])
w = browser.z_dziennika_dzis()
sprawdz("wpis bez pola 'udane' traktowany jako nieudany",
        tylko(w, "komentarze", "lajki") == {"komentarze": 0, "lajki": 0}, w)

print()
print("=== 4. CZY TEST W OGOLE WYKRYWA TEN BLAD ===")
print("    (kontrdowod: liczymy tak, jak liczyl STARY kod — z kanalu profilu)")

ustaw([wpis("komentarz") for _ in range(16)])


def zostalo_wg(juz, budzet):
    """Dokladnie to wyrazenie, ktorego uzywa run.py."""
    return {k: max(0, budzet[k] - juz.get(k, 0))
            for k in ("notki", "komentarze", "lajki")}


budzet = {"notki": 5, "komentarze": 16, "lajki": 14}

stary = zostalo_wg({"notki": 2, "komentarze": 0, "lajki": 0}, budzet)
sprawdz("STARY licznik po 16 komentarzach nadal chce 16 wiecej",
        stary["komentarze"] == 16, stary)

nowy_juz = {"notki": 2, **browser.z_dziennika_dzis()}
nowy = zostalo_wg(nowy_juz, budzet)
sprawdz("NOWY licznik po wyczerpaniu normy chce 0",
        nowy["komentarze"] == 0, nowy)
sprawdz("test rozroznia stary kod od nowego",
        stary["komentarze"] != nowy["komentarze"])

print()
print("=== 5. ILE PRZEBIEGOW ZOSTALO ===")

import db      # noqa: E402
import run     # noqa: E402


def bazka(zamkniete_dzis=0, przerwane_dzis=0, zamkniete_wczoraj=0):
    conn = db.connect(pathlib.Path(tempfile.mkdtemp()) / "t.db")
    for i in range(zamkniete_dzis):
        conn.execute("INSERT INTO runs (started_at, finished_at, status, stage)"
                     " VALUES (?, ?, 'DONE', 'dzien')",
                     ("%sT0%s:00:00+00:00" % (DZIS, i), "%sT0%s:30:00+00:00" % (DZIS, i)))
    for i in range(przerwane_dzis):
        conn.execute("INSERT INTO runs (started_at, status, stage)"
                     " VALUES (?, 'RUNNING', 'dzien')", ("%sT08:00:00+00:00" % DZIS,))
    for i in range(zamkniete_wczoraj):
        conn.execute("INSERT INTO runs (started_at, finished_at, status, stage)"
                     " VALUES (?, ?, 'DONE', 'dzien')",
                     ("%sT08:00:00+00:00" % WCZORAJ, "%sT08:30:00+00:00" % WCZORAJ))
    conn.commit()
    return conn


N = config.PRZEBIEGOW_DZIENNIE
sprawdz("przed pierwszym przebiegiem zostalo %s" % N,
        run.ile_przebiegow_zostalo(bazka()) == N)
sprawdz("po jednym zamknietym zostalo %s" % (N - 1),
        run.ile_przebiegow_zostalo(bazka(zamkniete_dzis=1)) == N - 1)
sprawdz("przy ostatnim zostalo 1",
        run.ile_przebiegow_zostalo(bazka(zamkniete_dzis=N - 1)) == 1)
sprawdz("nadprogramowy przebieg nie schodzi do zera (dzielenie przez zero)",
        run.ile_przebiegow_zostalo(bazka(zamkniete_dzis=N + 5)) == 1)
sprawdz("przebieg PRZERWANY nie zabiera slotu — kolejny go nadrobi",
        run.ile_przebiegow_zostalo(bazka(przerwane_dzis=2)) == N)
sprawdz("wczorajsze przebiegi nie licza sie do dzis",
        run.ile_przebiegow_zostalo(bazka(zamkniete_wczoraj=9)) == N)

print()
print("=== 6. CALA DOBA — czy norma sie domyka ===")


def doba(dzielnik_stary=False):
    """Symuluje pelny dzien: kazdy przebieg dobiera i zapisuje w dzienniku."""
    conn = db.connect(pathlib.Path(tempfile.mkdtemp()) / "d.db")
    wykonane = {"notki": 0, "komentarze": 0, "lajki": 0}
    for nr in range(config.PRZEBIEGOW_DZIENNIE):
        # NOTKI TEZ IDA PRZEZ DZIENNIK — od 30 sierpnia 2026 to jedyne zrodlo
        # licznika. Wczesniej symulacja podawala je osobno:
        #     juz = {"notki": wykonane["notki"], **browser.z_dziennika_dzis()}
        # i gdy `z_dziennika_dzis` zaczelo zwracac `notki`, rozpakowanie
        # NADPISYWALO symulowana liczbe zerem — kazdy przebieg bral pelny
        # budzet i doba dawala 9 notek zamiast 5. Ten sam wzorzec siedzial w
        # kodzie produkcyjnym (`wynik = {"notki": 0, **z_dziennika_dzis()}`).
        ustaw([wpis("notka") for _ in range(wykonane["notki"])]
              + [wpis("komentarz") for _ in range(wykonane["komentarze"])]
              + [wpis("polubienie") for _ in range(wykonane["lajki"])])
        juz = browser.z_dziennika_dzis()
        zost = zostalo_wg(juz, budzet)
        dziel = config.PRZEBIEGOW_DZIENNIE if dzielnik_stary \
            else run.ile_przebiegow_zostalo(conn)
        wziete = {k: (max(1, round(v / dziel)) if v else 0) for k, v in zost.items()}
        for k in wykonane:
            wykonane[k] += wziete[k]
        print("    przebieg %s: dzielnik=%s  bierze notki=%s komentarze=%s lajki=%s"
              % (nr + 1, dziel, wziete["notki"], wziete["komentarze"], wziete["lajki"]))
        conn.execute("INSERT INTO runs (started_at, finished_at, status, stage)"
                     " VALUES (?, ?, 'DONE', 'dzien')",
                     ("%sT0%s:00:00+00:00" % (DZIS, nr), "%sT0%s:30:00+00:00" % (DZIS, nr)))
        conn.commit()
    return wykonane


print("  --- dzielnik STARY (wszystkie przebiegi) ---")
stary_dzien = doba(dzielnik_stary=True)
print("  --- dzielnik NOWY (pozostale przebiegi) ---")
nowy_dzien = doba()
print()
print("    budzet: %s" % budzet)
print("    stary:  %s" % stary_dzien)
print("    nowy:   %s" % nowy_dzien)

sprawdz("STARY dzielnik zanizal komentarze (%s < %s)"
        % (stary_dzien["komentarze"], budzet["komentarze"]),
        stary_dzien["komentarze"] < budzet["komentarze"])
sprawdz("NOWY dzielnik domyka norme komentarzy dokladnie (%s = %s)"
        % (nowy_dzien["komentarze"], budzet["komentarze"]),
        nowy_dzien["komentarze"] == budzet["komentarze"])
sprawdz("NOWY dzielnik domyka norme notek (%s = %s)"
        % (nowy_dzien["notki"], budzet["notki"]),
        nowy_dzien["notki"] == budzet["notki"])
sprawdz("NOWY dzielnik domyka norme polubien (%s = %s)"
        % (nowy_dzien["lajki"], budzet["lajki"]),
        nowy_dzien["lajki"] == budzet["lajki"])
sprawdz("nowy nie przekracza budzetu w zadnej kategorii",
        all(nowy_dzien[k] <= budzet[k] for k in budzet))

print()
print("=== 7. WIDELKI WLASCICIELA — 15-20 komentarzy, 12-20 polubien ===")

for komentarzy in range(config.KOMENTARZE_DZIENNIE[0], config.KOMENTARZE_DZIENNIE[1] + 1):
    budzet = {"notki": 5, "komentarze": komentarzy, "lajki": 14}
    wynik_doby = doba()["komentarze"]
    sprawdz("budzet %s komentarzy -> dzien konczy na %s" % (komentarzy, wynik_doby),
            wynik_doby == komentarzy, "powinno byc %s" % komentarzy)

budzet = {"notki": 5, "komentarze": 16, "lajki": 14}

print()
print("=== 8. PRZEBIEG PRZERWANY — czy dzien sie nadrabia ===")

conn = db.connect(pathlib.Path(tempfile.mkdtemp()) / "p.db")
conn.execute("INSERT INTO runs (started_at, status, stage)"
             " VALUES (?, 'RUNNING', 'dzien')", ("%sT03:40:00+00:00" % DZIS,))
conn.commit()
ustaw([])
zost = zostalo_wg({"notki": 0, **browser.z_dziennika_dzis()}, budzet)
dziel = run.ile_przebiegow_zostalo(conn)
sprawdz("po wywalonym przebiegu dzielnik nadal %s, wiec norma sie nadrobi" % N,
        dziel == N, dziel)

conn.execute("INSERT INTO runs (started_at, finished_at, status, stage)"
             " VALUES (?, ?, 'FAILED', 'dzien')",
             ("%sT03:41:00+00:00" % DZIS, "%sT03:42:00+00:00" % DZIS))
conn.commit()
# TA ASERCJA UTRWALALA WADE. Do 2 wrzesnia 2026 pilnowala, zeby przebieg
# `FAILED` NIE zabieral slotu — a to wlasnie przez to ostatni przebieg doby
# dzielil reszte pracy przez dwa zamiast przez jeden. Zmierzone uruchomieniem
# przy budzecie 20: jedna porazka zostawiala 4 z 20 niewykonane, dwie — 8 z 20.
sprawdz("przebieg zapisany jako FAILED ZABIERA slot — bez tego ostatni przebieg"
        " dnia dzieli reszte przez dwa i zostawia polowe",
        run.ile_przebiegow_zostalo(conn) == N - 1, run.ile_przebiegow_zostalo(conn))

print()
print("=== 9. CZY WYWALONY PRZEBIEG ZAPISUJE SIE JAKO FAILED ===")
print("    (bez atrapy: uruchamiamy prawdziwe main() z podstawionym dzien())")

import argparse  # noqa: E402

testowa_baza = pathlib.Path(tempfile.mkdtemp()) / "m.db"
oryg_dzien, oryg_connect, oryg_argv = run.dzien, db.connect, sys.argv
oryg_summary = run._summary


def wybuchowy(conn, run_id, wyslij):
    raise KeyError("notki")


try:
    run.dzien = wybuchowy
    run._summary = lambda *a, **k: None
    db.connect = lambda path=None: oryg_connect(testowa_baza)
    # Wlasny katalog danych, czyli wlasny zamek — inaczej test bierze
    # zamek produkcyjny i pada, gdy agent akurat pracuje.
    _zdjecie_dane = config.uzyj_katalogu_danych(testowa_baza.parent)
    sys.argv = ["run.py", "--dzien"]
    try:
        run.main()
        polecial = False
    except KeyError:
        polecial = True
    sprawdz("wyjatek z dnia leci dalej, nie jest polykany", polecial)
    sprawdzarka = oryg_connect(testowa_baza)
    wiersze = list(sprawdzarka.execute(
        "SELECT status, note FROM runs WHERE stage='dzien'"))
    sprawdz("wywalony przebieg ma status FAILED, nie DONE",
            wiersze and wiersze[-1][0] == "FAILED",
            wiersze[-1] if wiersze else "brak wiersza")
    sprawdz("zapisany powod wywalki",
            wiersze and "KeyError" in (wiersze[-1][1] or ""),
            wiersze[-1][1] if wiersze else "")

    def spokojny(conn, run_id, wyslij):
        return 0

    run.dzien = spokojny
    run.main()
    sprawdzarka = oryg_connect(testowa_baza)
    wiersze = list(sprawdzarka.execute(
        "SELECT status FROM runs WHERE stage='dzien' ORDER BY id"))
    sprawdz("udany przebieg nadal ma DONE",
            wiersze and wiersze[-1][0] == "DONE",
            wiersze[-1] if wiersze else "brak")
    sprawdz("baza rozroznia udany od wywalonego",
            [w[0] for w in wiersze] == ["FAILED", "DONE"], [w[0] for w in wiersze])
finally:
    run.dzien, db.connect, sys.argv = oryg_dzien, oryg_connect, oryg_argv
    config.przywroc_katalog_danych(_zdjecie_dane)
    run._summary = oryg_summary

browser.DZIENNIK = ORYGINAL
print()
print("=== WYNIK: %s zdanych, %s oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
