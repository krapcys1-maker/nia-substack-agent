"""Zapis wywolania do bazy: kolumna z wartoscia domyslna nie moze wysadzac INSERT-a.

TO NIE JEST TEST TEORETYCZNY. Kosztowal okladke artykulu 0025, ktory poszedl na
zywo bez naglowka graficznego, i o wlos nie kosztowal czegos gorszego.

Co sie stalo: dopisalem do `calls` kolumne `cache_hit INTEGER NOT NULL DEFAULT 0`.
`record_call` wstawial ZAWSZE komplet kolumn, a brakujace pola bral przez
`fields.get(k)` — czyli wpisywal jawny NULL. SQL-owy DEFAULT wtedy nie dziala:
wchodzi tylko wtedy, gdy kolumny w INSERT nie ma WCALE. Kazde wywolanie, ktore
nie podalo `cache_hit`, konczylo sie `IntegrityError`.

Podawalo je jedno miejsce z czterech — udana sciezka tekstowa. Pozostale trzy:
  llm.py:510  udany obraz          -> grafika NIGDY nie mogla sie zapisac
  llm.py:501  nieudany obraz
  llm.py:444  NIEUDANE wywolanie tekstowe

To ostatnie jest grozniejsze niz brak obrazka: gdy wywolanie modelu padalo,
sciezka bledu probowala je zapisac, wywalala sie na tej samej kolumnie i w gore
szedl `IntegrityError` ZAMIAST prawdziwej przyczyny. Awaria API wygladalaby jak
awaria bazy.

Dlatego ten test sprawdza dwie rzeczy naraz: ze poprawka dziala i ze STARY
sposob faktycznie by tu polegl (sekcja 5). Bez tego drugiego test tylko
potwierdzalby moj wlasny model swiata.
"""
import pathlib
import sqlite3
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import config   # noqa: E402

config.DB_PATH = pathlib.Path(tempfile.mkdtemp()) / "zapis.db"
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


conn = db.connect()
run_id = db.start_run(conn, stage="test-zapisu")

print("=== 1. WYWOLANIE BEZ cache_hit ZAPISUJE SIE (to bylo zepsute) ===")
# Doslownie tyle pol, ile podaje `llm.obraz` na udanej sciezce.
try:
    db.record_call(
        conn=conn, run_id=run_id, provider="openai", model="gpt-image-1.5",
        purpose="obraz", tokens_in=0, tokens_out=0, web_searches=0,
        cost_usd=0.19, price_verified=0, ok=1, note="1024x1024")
    sprawdz("obraz zapisuje sie bez wyjatku", True)
except sqlite3.IntegrityError as e:
    sprawdz("obraz zapisuje sie bez wyjatku", False, e)

w = conn.execute("SELECT cache_hit, purpose, cost_usd FROM calls"
                 " WHERE purpose='obraz'").fetchone()
sprawdz("wiersz naprawde jest w bazie", w is not None)
sprawdz("pominiete cache_hit ma wartosc domyslna 0", w and w[0] == 0,
        w[0] if w else "brak")
sprawdz("reszta pol nietknieta", w and abs(w[2] - 0.19) < 1e-9)

print()
print("=== 2. SCIEZKA BLEDU TEZ (tu gubilismy prawdziwa przyczyne) ===")
try:
    db.record_call(
        conn=conn, run_id=run_id, provider="deepseek", model="deepseek-v4-pro",
        purpose="discovery", tokens_in=0, tokens_out=0, web_searches=0,
        cost_usd=0.0, price_verified=0, ok=0,
        note="HTTPError: 529 przeciazenie")
    sprawdz("nieudane wywolanie da sie zapisac", True)
except sqlite3.IntegrityError as e:
    sprawdz("nieudane wywolanie da sie zapisac", False, e)

w = conn.execute("SELECT ok, note FROM calls WHERE purpose='discovery'").fetchone()
sprawdz("zapisalo sie jako nieudane", w and w[0] == 0)
sprawdz("i PRAWDZIWA przyczyna przetrwala", w and "529" in (w[1] or ""),
        w[1] if w else "brak")

print()
print("=== 3. PODANE cache_hit NADAL SIE ZAPISUJE ===")
db.record_call(
    conn=conn, run_id=run_id, provider="deepseek", model="deepseek-v4-pro",
    purpose="write", tokens_in=1000, tokens_out=200, cache_hit=768,
    web_searches=0, cost_usd=0.01, price_verified=1, ok=1, note="")
w = conn.execute("SELECT cache_hit FROM calls WHERE purpose='write'").fetchone()
sprawdz("trafienia w cache zapisuja sie, gdy sa", w and w[0] == 768,
        w[0] if w else "brak")

print()
print("=== 4. KAZDE MIEJSCE Z llm.py PRZECHODZI NA ZYWYCH POLACH ===")
# Zamiast zgadywac, bierzemy zestawy pol wprost z czterech wywolan w llm.py.
ZESTAWY = {
    "llm:444 blad tekstowy": dict(
        provider="anthropic", model="claude-opus-5", purpose="note",
        tokens_in=0, tokens_out=0, web_searches=0, cost_usd=0.0,
        price_verified=1, ok=0, note="TimeoutError"),
    "llm:454 udany tekst": dict(
        provider="anthropic", model="claude-opus-5", purpose="note",
        tokens_in=900, tokens_out=120, cache_hit=0, web_searches=0,
        cost_usd=0.02, price_verified=1, ok=1, note=""),
    "llm:501 blad obrazu": dict(
        provider="openai", model="gpt-image-1.5", purpose="obraz",
        tokens_in=0, tokens_out=0, web_searches=0, cost_usd=0.0,
        price_verified=0, ok=0, note="HTTPError: 400"),
    "llm:510 udany obraz": dict(
        provider="openai", model="gpt-image-1.5", purpose="obraz",
        tokens_in=0, tokens_out=0, web_searches=0, cost_usd=0.19,
        price_verified=0, ok=1, note="1024x1024"),
}
for nazwa, pola in ZESTAWY.items():
    try:
        db.record_call(conn=conn, run_id=run_id, **pola)
        sprawdz("%-24s zapisuje sie" % nazwa, True)
    except sqlite3.IntegrityError as e:
        sprawdz("%-24s zapisuje sie" % nazwa, False, e)

brak = conn.execute("SELECT COUNT(*) FROM calls WHERE cache_hit IS NULL").fetchone()[0]
sprawdz("ZADEN wiersz nie ma NULL w cache_hit", brak == 0, brak)

print()
print("=== 5. KONTRDOWOD: STARY SPOSOB TU POLEGA ===")
# Bez tego test potwierdzalby tylko moja poprawke, a nie rzeczywistosc.
# Odtwarzamy stary INSERT doslownie: pelna lista kolumn, brakujace jako NULL.
STARE_KOLUMNY = ("run_id", "provider", "model", "purpose", "tokens_in",
                 "tokens_out", "cache_hit", "web_searches", "cost_usd",
                 "price_verified", "ok", "note")
pola_obrazu = dict(run_id=run_id, provider="openai", model="gpt-image-1.5",
                   purpose="obraz", tokens_in=0, tokens_out=0, web_searches=0,
                   cost_usd=0.19, price_verified=0, ok=1, note="1024x1024")
try:
    conn.execute(
        "INSERT INTO calls (at, %s) VALUES (?, %s)"
        % (", ".join(STARE_KOLUMNY), ", ".join("?" * len(STARE_KOLUMNY))),
        [db.now(), *(pola_obrazu.get(k) for k in STARE_KOLUMNY)])
    sprawdz("stary sposob faktycznie padal na tym samym", False,
            "przeszedl — test NIE odroznia wersji, jest bezwartosciowy")
except sqlite3.IntegrityError as e:
    sprawdz("stary sposob faktycznie padal na tym samym", True)
    print("        (%s)" % e)
conn.rollback()

print()
print("=== 6. KOLUMNY BEZ WARTOSCI DOMYSLNEJ NADAL MUSZA BYC PODANE ===")
# Poprawka nie moze zamienic sie w cicha zgode na dziury: `provider`, `model`
# i `purpose` sa NOT NULL bez DEFAULT, wiec ich pominiecie ma nadal krzyczec.
try:
    db.record_call(conn=conn, run_id=run_id, purpose="sierota", tokens_in=1)
    sprawdz("brak provider/model nadal jest bledem", False, "przeszlo po cichu")
except sqlite3.IntegrityError:
    sprawdz("brak provider/model nadal jest bledem", True)
conn.rollback()

print()
print("=== 7. PRODUKCJA NIETKNIETA ===")
sprawdz("baza testu to nie produkcja", "tmp" in str(config.DB_PATH).lower()
        or "temp" in str(config.DB_PATH).lower(), config.DB_PATH)

print()
print("=== ODPOWIEDZ MODELU Z PROZA WOKOL JSON-A ===")
# DWIE AWARIE Z JEDNEGO DNIA, 25 sierpnia 2026:
#   warto_pisac       -> JSONDecodeError: Extra data: line 1 column 1866
#   znajdz_ciekawostki -> brak JSON w odpowiedzi: "I'll work the grid across..."
# To drugie kosztowalo dwadziescia wyszukiwan i 0,13 USD, po czym oddalo zero.
#
# Przyczyna byla jedna: parser bral wycinek od PIERWSZEGO nawiasu otwierajacego
# do OSTATNIEGO zamykajacego. Model z wlaczonym wyszukiwaniem pisze zdanie o
# tym, co zaraz zrobi, potem JSON, czasem komentarz na koncu — i kazdy nawias
# w tej prozie przesuwal granice wycinka.
import llm as _llm   # noqa: E402

_PROBKI = [
    ('{"a": 1}', {"a": 1}, "goly JSON"),
    ("```json" + chr(10) + '{"a": 1}' + chr(10) + "```", {"a": 1}, "w plocie"),
    ("I will work the grid.{\"a\": 1}", {"a": 1}, "proza przed"),
    ('{"a": 1}' + chr(10) + "That is my answer.", {"a": 1},
     "proza po — to bylo Extra data"),
    ("Here {is} my answer: {\"a\": 1}", {"a": 1}, "nawias w prozie przed"),
    ('{"a": 1} and also {"b": 2}', {"a": 1}, "dwa obiekty, bierze pierwszy"),
    ('{"t": "brace } inside"}', {"t": "brace } inside"}, "nawias w napisie"),
    ('{"a": {"b": [1,2]}}', {"a": {"b": [1, 2]}}, "zagniezdzony"),
]
for _tekst, _oczek, _opis in _PROBKI:
    try:
        _w = _llm.parse_json(_tekst)
    except Exception as _e:
        _w = "%s: %s" % (type(_e).__name__, _e)
    sprawdz(_opis, _w == _oczek, _w)

# KONTRDOWOD 1: proza BEZ zadnego JSON-a nadal musi rzucac. Bez tego parser
# zwracalby cokolwiek i etap szedlby dalej z pusta karta.
try:
    _llm.parse_json("zadnego jsona tu nie ma")
    sprawdz("proza bez JSON nadal rzuca wyjatek", False, "nie rzucil")
except ValueError:
    sprawdz("proza bez JSON nadal rzuca wyjatek", True)

# KONTRDOWOD 2: stary sposob — od pierwszego do ostatniego nawiasu — MUSI
# oblewac sie na probce, ktora dzis przechodzi. Inaczej test niczego nie mierzy.
import json as _json
_stary_by_padl = False
# Probka musi zawierac nawias PO JSON-ie, bo dopiero wtedy stary wycinek
# „od pierwszego do ostatniego" siega za koniec obiektu. Sama proza bez
# nawiasu starego parsera nie lamala — i wlasnie dlatego pierwsza wersja tego
# kontrdowodu byla bezwartosciowa.
_probka = '{"a": 1} and also {"b": 2}'
_i, _j = _probka.find("{"), _probka.rfind("}")
try:
    _json.loads(_probka[_i:_j + 1])
except ValueError:
    _stary_by_padl = True
sprawdz("stary parser oblalby sie na tej samej probce", _stary_by_padl)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
