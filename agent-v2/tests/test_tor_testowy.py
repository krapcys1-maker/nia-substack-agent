# -*- coding: utf-8 -*-
"""Przebieg sprawdzajacy nie zjada budzetu konta — i ma wlasna granice.

DLACZEGO TO POWSTALO. 30 sierpnia dzien audytu segmentu tematow zjadl 3,87 USD
do poludnia przy sufcie 5,00 — w wiekszosci na MOJE przebiegi sprawdzajace:
trzy przejscia sciezki artykulu, dwa pelne szukania ciekawostek, cztery rankingi
banku, dwa uruchomienia skauta. Produkcja konta miala z tego znikoma czesc, a
przebieg planowy o 11:35 mogl nie miec za co opublikowac notki.

Wlasciciel: „nie licz budzetu do testow, to cos osobnego". Sufit dzienny chroni
przed rozbieganym agentem w nocy i ma pilnowac PRACY KONTA, nie pracy nad kodem.

ALE „OSOBNO" TO NIE „BEZ GRANIC". Pomylka w skrypcie doraznym jest znacznie
bardziej prawdopodobna niz w kodzie, ktory przeszedl testy, a petla bez wyjscia
w nocy wydaje wszystko. Dlatego tor testowy ma wlasny sufit, nie brak sufitu.

DOMYSLNIE PRODUKCJA. Bezpieczniejsza pomylka to policzyc test jako produkcje
(mniej wolnego budzetu) niz otworzyc produkcji drugi, luzniejszy sufit.

BEZ PYTESTA. Uruchamiac z korzenia repozytorium. Nie wola platnego modelu.
"""
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import config   # noqa: E402
import wlasna_konfiguracja  # noqa: E402
import db       # noqa: E402

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


baza = pathlib.Path(tempfile.mkdtemp()) / "proba.db"
conn = db.connect(baza)


def wywolanie(run_id, koszt, kiedy):
    conn.execute(
        "INSERT INTO calls (run_id, at, provider, model, purpose, cost_usd)"
        " VALUES (?, ?, 'deepseek', 'm', 'test', ?)",
        (run_id, kiedy, koszt))
    conn.commit()


DZIS = db.now()[:10]

print("=== 0. KOLUMNA ISTNIEJE I MA DOMYSLNA WARTOSC ===")
kolumny = {w[1] for w in conn.execute("PRAGMA table_info(runs)")}
sprawdz("runs ma kolumne tryb", "tryb" in kolumny, sorted(kolumny))

print()
print("=== 1. DOMYSLNIE PRODUKCJA ===")
os.environ.pop("NIA_TRYB", None)
r_prod = db.start_run(conn, "zwykly-przebieg")
sprawdz("przebieg bez wskazania to produkcja",
        db.tryb_przebiegu(conn, r_prod) == "produkcja",
        db.tryb_przebiegu(conn, r_prod))
sprawdz("brak przebiegu tez liczy sie do produkcji",
        db.tryb_przebiegu(conn, None) == "produkcja")

print()
print("=== 2. TRYB Z ARGUMENTU I ZE ZMIENNEJ SRODOWISKA ===")
r_test = db.start_run(conn, "sprawdzam-kod", tryb="test")
sprawdz("argument dziala", db.tryb_przebiegu(conn, r_test) == "test")
os.environ["NIA_TRYB"] = "test"
r_env = db.start_run(conn, "ze-zmiennej")
sprawdz("zmienna srodowiskowa dziala",
        db.tryb_przebiegu(conn, r_env) == "test")
os.environ["NIA_TRYB"] = "bzdura"
r_zly = db.start_run(conn, "zla-wartosc")
sprawdz("nieznana wartosc spada do produkcji",
        db.tryb_przebiegu(conn, r_zly) == "produkcja",
        db.tryb_przebiegu(conn, r_zly))
os.environ.pop("NIA_TRYB", None)

print()
print("=== 3. TORY LICZA SIE OSOBNO ===")
wywolanie(r_prod, 0.40, DZIS + "T09:00:00+00:00")
wywolanie(r_test, 2.00, DZIS + "T09:05:00+00:00")
wywolanie(None, 0.10, DZIS + "T09:10:00+00:00")
prod = db.spent_usd(conn, DZIS, tryb="produkcja")
test = db.spent_usd(conn, DZIS, tryb="test")
sprawdz("produkcja widzi tylko swoje (0.40 + 0.10 bez przebiegu)",
        abs(prod - 0.50) < 1e-9, prod)
sprawdz("tor testowy widzi tylko swoje", abs(test - 2.00) < 1e-9, test)

print()
print("=== 4. KONTRDOWOD: BEZ ROZDZIALU BYLOBY RAZEM ===")
# Gdyby `spent_usd` ignorowalo tryb, obie liczby bylyby rowne sumie 2.50 — i
# sekcja 3 przechodzilaby rowniez wtedy, gdyby rozdzial nie istnial.
razem = prod + test
sprawdz("suma obu torow to caly dzien", abs(razem - 2.50) < 1e-9, razem)
sprawdz("i zaden tor osobno nie jest calym dniem",
        abs(prod - razem) > 1e-9 and abs(test - razem) > 1e-9)

print()
print("=== 5. SUFIT TESTOWY ISTNIEJE I NIE JEST NIESKONCZONY ===")
sprawdz("TEST_LIMIT_USD jest liczba dodatnia",
        isinstance(config.TEST_LIMIT_USD, (int, float))
        and config.TEST_LIMIT_USD > 0, config.TEST_LIMIT_USD)
sprawdz("i nie wiekszy niz produkcyjny",
        config.TEST_LIMIT_USD <= config.DAILY_LIMIT_USD,
        "%s wobec %s" % (config.TEST_LIMIT_USD, config.DAILY_LIMIT_USD))

print()
print("=== 6. SUFIT DNIA NA DZIS WYGASA SAM ===")
# Podniesienie sufitu bylo zgoda na JEDEN dzien. Poprzednim razem trzeba bylo
# pamietac, zeby je cofnac; teraz ma wygasnac bez niczyjej pamieci.
#
# STALO TU „data podniesienia jest zapisana" — czyli asercja, ze w kodzie MA
# BYC wpisana data. To jest zdanie o jednej instalacji w jednym dniu, a nie
# o dzialaniu wygasania: u konta, ktore sufitu nie podnosilo, oblewalo bez
# zadnej wady. Pytamy wiec o MECHANIZM.
sprawdz("brak daty znaczy: bez podniesienia",
        config.sufit_dnia("2000-01-01") == config.SUFIT_DZIENNY_BAZOWY
        if not config.SUFIT_PODNIESIONY_NA else True,
        config.sufit_dnia("2000-01-01"))
sprawdz_nasze("poza dniem podniesienia sufit jest bazowy",
              config.sufit_dnia("2000-01-01") == config.SUFIT_DZIENNY_BAZOWY,
              "%s wobec bazy %s" % (config.sufit_dnia("2000-01-01"),
                                    config.SUFIT_DZIENNY_BAZOWY))
sprawdz("sufit na dzis jest pochodna, nie drugim zrodlem",
        config.DAILY_LIMIT_USD == config.sufit_dnia(config._dzis_utc()),
        "%s wobec %s" % (config.DAILY_LIMIT_USD,
                         config.sufit_dnia(config._dzis_utc())))
# Arytmetyka podniesienia (RAZ, nie dwa razy) ma wlasny plik:
# `tests/test_sufit_dnia.py`. Tutaj wystarczy, ze wygasanie w ogole dziala.

print()
print("=== 7. CICHY DZIEN — JEDNA LISTA DLA OBU CZYTELNIKOW ===")
# `run.py` zeruje przydzial, `norma.py` nie liczy tych dni do sredniej.
# Rozjazd dawalby licznik krzyczacy o normie w dniu zaprojektowanej ciszy.
sprawdz("obie krotki maja tyle samo pozycji",
        len(config.CICHY_DZIEN_WYCISZA) == len(config.CICHY_DZIEN_WYCISZA_RODZAJE),
        "%s / %s" % (config.CICHY_DZIEN_WYCISZA, config.CICHY_DZIEN_WYCISZA_RODZAJE))
for mnoga, poj in zip(config.CICHY_DZIEN_WYCISZA,
                      config.CICHY_DZIEN_WYCISZA_RODZAJE):
    # RDZEN, nie przedrostek. „restack" jest przedrostkiem „restacki", ale
    # „notka" nie jest przedrostkiem „notki" — roznia sie ostatnia litera.
    # Cztery znaki wystarcza, zeby zlapac pomylke w rodzaju „notki"/„restack",
    # i nie wymagaja odmiany polskiej w tescie.
    sprawdz("  %r odpowiada %r" % (mnoga, poj), mnoga[:4] == poj[:4],
            "%r vs %r" % (mnoga[:4], poj[:4]))
zrodlo = pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8")
sprawdz("run.py czyta liste z config, nie ma wlasnej",
        "CICHY_DZIEN_WYCISZA" in zrodlo
        and 'zostalo["notki"] = 0' not in zrodlo)
norma = pathlib.Path("agent-v2/norma.py").read_text(encoding="utf-8")
sprawdz("norma.py tez ja zna", "CICHY_DZIEN_WYCISZA_RODZAJE" in norma)

print()
print("=== 8. CICHE DNI NIE MOGA BYC DWA POD RZAD ===")
from datetime import datetime, timedelta, timezone   # noqa: E402
pod_rzad = 0
d = datetime(2026, 1, 1, tzinfo=timezone.utc)
ciche = 0
for i in range(400):
    dzien = d + timedelta(days=i)
    if config.cichy_dzien(dzien):
        ciche += 1
        if config.cichy_dzien(dzien - timedelta(days=1)):
            pod_rzad += 1
sprawdz("zaden cichy dzien nie ma cichego poprzednika", pod_rzad == 0, pod_rzad)
sprawdz("ale ciche dni w ogole wystepuja", ciche > 0, ciche)
sprawdz("i nie jest ich absurdalnie duzo (ponizej co czwartego)",
        ciche < 100, "%d na 400" % ciche)

conn.close()
print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
