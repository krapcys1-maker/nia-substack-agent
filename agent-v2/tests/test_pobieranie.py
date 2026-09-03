"""Test drugiego podejscia do pobierania — przez przegladarke.

Polowa zrodel przepadala i to bylo waskie gardlo jakosci artykulow.
"""
import inspect
import pathlib
import sys

sys.path.insert(0, "agent-v2")
import config   # noqa: E402
import db       # noqa: E402
import stages   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


print("=== 1. CO IDZIE DO DRUGIEGO PODEJSCIA, A CO NIE ===")
src = inspect.getsource(stages.fetch)
sprawdz("brak tresci -> do przegladarki",
        'reason.startswith("za mało treści")' in src)
sprawdz("404 NIE idzie do przegladarki (adres nie istnieje)",
        'reason.startswith("HTTP")' not in src)
pomoc = inspect.getsource(stages._dobierz_przegladarka)
sprawdz("odmowa hosta pozostaje odmowa takze w przegladarce",
        "REFUSAL_PHRASES" in pomoc)
sprawdz("zasada zapisana wprost w kodzie", "nie omijamy jej narzedziem" in pomoc)

print()
print("=== 2. ZACHOWANIE BEZ PRZEGLADARKI I NA BLEDACH ===")
import tempfile  # noqa: E402
conn = db.connect(pathlib.Path(tempfile.mkdtemp()) / "t.db")
sprawdz("pusta lista -> nic nie robi i nie wola przegladarki",
        stages._dobierz_przegladarka(conn, 1, [], []) == [])

import browser  # noqa: E402
oryg = browser.read_pages
try:
    browser.read_pages = lambda urls: (_ for _ in ()).throw(RuntimeError("padlo"))
    wynik = stages._dobierz_przegladarka(
        conn, 1, [{"url": "https://x.example/a", "host": "x.example"}], [])
    sprawdz("awaria przegladarki nie wywala etapu", wynik == [], wynik)

    # Odzyskanie: strona daje tresc dopiero w przegladarce
    DLUGI = "Rule text. " * 200
    browser.read_pages = lambda urls: [
        {"url": u, "text": DLUGI, "title": "t", "error": None} for u in urls]
    zrodlo = {"url": "https://mtf.mastercard.com.au/x", "host": "mtf.mastercard.com.au",
              "class": "PRIMARY", "title": "Rulebook"}
    conn.execute("INSERT INTO sources (run_id, at, url, domain, fetched_ok, fail_reason)"
                 " VALUES (?,?,?,?,?,?)", (1, db.now(), zrodlo["url"], zrodlo["host"],
                                           0, "za mało treści (0 znaków)"))
    conn.commit()
    wynik = stages._dobierz_przegladarka(conn, 1, [zrodlo], [])
    sprawdz("strona rysowana JS-em zostaje ODZYSKANA", len(wynik) == 1, wynik)
    sprawdz("odzyskana niesie tresc", len(wynik[0].get("text", "")) > 500)
    sprawdz("zachowuje klase zrodla", wynik[0].get("class") == "PRIMARY")
    stan = conn.execute("SELECT fetched_ok, fail_reason FROM sources WHERE url=?",
                        (zrodlo["url"],)).fetchone()
    sprawdz("zapis w bazie poprawiony na udany", stan[0] == 1, tuple(stan))

    # Odmowa: przegladarka tez nie omija blokady
    browser.read_pages = lambda urls: [
        {"url": u, "text": (list(config.REFUSAL_PHRASES)[0] + " ") * 80,
         "title": "", "error": None} for u in urls]
    wynik = stages._dobierz_przegladarka(
        conn, 1, [{"url": "https://blok.example/x", "host": "blok.example"}], [])
    sprawdz("host, ktory odmawia automatowi, NADAL odmawia", wynik == [], wynik)

    # Pusto i w przegladarce
    browser.read_pages = lambda urls: [
        {"url": u, "text": "", "title": "", "error": None} for u in urls]
    sprawdz("pusto takze w przegladarce -> nie udajemy sukcesu",
            stages._dobierz_przegladarka(
                conn, 1, [{"url": "https://p.example/x", "host": "p.example"}], []) == [])
finally:
    browser.read_pages = oryg

print()
print("=== 3. CO TO ZMIENIA NA DANYCH Z PRAWDZIWEGO PRZEBIEGU ===")
# proba 1: 6 znalezionych, 3 pobrane, 2 pierwotne; dwa padly na "0 znakow"
print("    bylo:  6 znalezionych -> 3 pobrane (2 x pusto, 1 x 404)")
print("    gdyby przegladarka odzyskala te dwa: 5 z 6")
sprawdz("prog zrodel pierwotnych to %s" % config.MIN_PRIMARY_SOURCES,
        config.MIN_PRIMARY_SOURCES >= 2)
# TU STALO `sprawdz("dwa odzyskane zrodla to roznica miedzy 2 a 4 dokumentami",
# True)` — asercja z warunkiem `True`, ktora nie mogla oblac nigdy. Liczyla sie
# do „zdanych" i nie pilnowala niczego. To jest zdanie o danych z przebiegu,
# nie twierdzenie o kodzie, wiec nalezy do wydruku, nie do licznika.
print("    dwa odzyskane źródła to różnica między 2 a 4 dokumentami")

print()
print("=== WYNIK: %s zdanych, %s oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
