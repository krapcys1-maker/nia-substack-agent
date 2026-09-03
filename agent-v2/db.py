"""Baza: cztery tabele, waskie migracje kolumn, zero triggerow i limitow CHECK.

Nowa baza powstaje z `CREATE TABLE IF NOT EXISTS` przy starcie, a istniejaca
dostaje brakujace kolumny przez `_dopisz_brakujace_kolumny`. Nie ma drabiny
wersji ani przepisywania danych, bo poprzedni agent mial 42 migracje i to one
blokowaly produkcje, nie brak funkcji.

Limitow nie ma w `CHECK`-ach celowo: limit przypiety w schemacie to drugie
miejsce, w ktorym zyje ta sama liczba, a wtedy podniesienie jej w kodzie wywala
produkcje (stary agent: `attempt_no IN (1,2)` w osmiu tabelach, 1,84 USD do kosza).
"""

from __future__ import annotations

import contextlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import config

# KTORE DZIALANIE PLACI ZA TO WYWOLANIE. `purpose` mowi, CO robi model
# („comment", „factcheck"), ale nie mowi, KOMU to sluzy: jedno `llm.call`
# z `purpose="comment"` obsluguje i komentarze pod cudzymi artykulami, i te pod
# notkami, a jedno `factcheck` sprawdza notke, komentarz albo artykul.
#
# Zmierzone 2 wrzesnia 2026: 3,4562 z 16,2817 USD tygodnia (21 procent
# rachunku) nie da sie przypisac do zadnego kanalu. Bez tego zadna miara
# „na dolara" nie istnieje — mozna policzyc licznik i nie ma mianownika.
#
# Znacznik ustawia sie NAWIASEM (`with db.kanal(...)`), a nie parametrem przy
# kazdym wywolaniu, bo wywolan sa dziesiatki, a blokow pracy piec. Zapis idzie
# przez `record_call`, wiec obejmuje takze sciezki bledu i obraz — czyli
# dokladnie te miejsca, ktore przy parametrze zostalyby zapomniane.
AKCJA = ""


@contextlib.contextmanager
def kanal(nazwa: str):
    """Na czas bloku kazde zapisane wywolanie dostaje `akcja = nazwa`.

    Przywraca poprzednia wartosc w `finally`, wiec wyjatek w srodku bloku nie
    zostawia znacznika przyklejonego do nastepnych wywolan.
    """
    global AKCJA
    poprzednia = AKCJA
    AKCJA = str(nazwa or "")
    try:
        yield
    finally:
        AKCJA = poprzednia

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at  TEXT NOT NULL,
    finished_at TEXT,
    status      TEXT NOT NULL,          -- RUNNING / DONE / FAILED
    stage       TEXT,                   -- na czym stanęło
    cost_usd    REAL NOT NULL DEFAULT 0,
    note        TEXT
);

CREATE TABLE IF NOT EXISTS calls (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id         INTEGER,
    at             TEXT NOT NULL,
    provider       TEXT NOT NULL,       -- anthropic / deepseek
    model          TEXT NOT NULL,
    purpose        TEXT NOT NULL,       -- scout / discovery / write / ...
    tokens_in      INTEGER NOT NULL DEFAULT 0,
    tokens_out     INTEGER NOT NULL DEFAULT 0,
    -- Trafienia w cache byly LICZONE do kosztu i nigdzie nie zapisywane, wiec
    -- nie dalo sie sprawdzic, czy w ogole trafiamy. To ma znaczenie, bo cache
    -- jest 30x tanszy od zwyklego wejscia ($0,022 wobec $0,66 u pro), a nasza
    -- najdrozsza pozycja — dyskoveria — przesyla cala rozmowe w kazdej rundzie.
    -- Bez tej kolumny nie da sie odroznic „prefiks peka" od „prefiks trafia,
    -- a cena bierze sie skadinad".
    cache_hit      INTEGER NOT NULL DEFAULT 0,
    web_searches   INTEGER NOT NULL DEFAULT 0,
    cost_usd       REAL NOT NULL DEFAULT 0,
    price_verified INTEGER NOT NULL DEFAULT 1,  -- 0 = stawka niepotwierdzona
    ok             INTEGER NOT NULL DEFAULT 1,
    note           TEXT
);

CREATE TABLE IF NOT EXISTS articles (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id       INTEGER,
    created_at   TEXT NOT NULL,
    topic        TEXT,
    title        TEXT,
    body         TEXT,
    evidence     TEXT,                  -- karta dowodowa, JSON
    status       TEXT NOT NULL,         -- SAVED / BLOCKED
    blocked_by   TEXT,                  -- która z czterech bramek
    notes        TEXT                   -- niesblokujące uwagi, JSON
);

CREATE TABLE IF NOT EXISTS sources (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id       INTEGER,
    at           TEXT NOT NULL,
    url          TEXT NOT NULL,
    domain       TEXT NOT NULL,         -- do reguły różnorodności
    title        TEXT,
    source_class TEXT,                  -- PRIMARY / SUPPORTING / ODPAD
    fetched_ok   INTEGER NOT NULL DEFAULT 0,
    fail_reason  TEXT                   -- np. blokada botów
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class ProdukcyjnaBazaWTescie(RuntimeError):
    """Darmowy test probowal otworzyc produkcyjna baze."""


def _odmow_produkcji(db_path: Path) -> None:
    """GLOSNA odmowa: wyjatek, nie ciche pominiecie.

    DLACZEGO WYJATEK, A NIE `return`. Ciche pominiecie kosztowalo juz ten
    projekt dziewiec dni — bramka faktow „przepuszczala" artykul i nikt nie
    wiedzial, ze cokolwiek sie stalo. Test, ktory po cichu dostaje pusta baze
    zamiast tej, o ktora prosil, przechodzi na zielono i NIC nie mierzy.
    Wyjatek zatrzymuje ten plik i pokazuje palcem, co poprawic.

    DLACZEGO TO W OGOLE STRZELA. `config.DB_PATH` jest liczone raz, przy
    imporcie. Test, ktory podstawia sam `config.DATA_DIR`, nie rusza `DB_PATH`
    — wiec `db.connect()` idzie do produkcji. Zmierzone 2 wrzesnia 2026:
    `stages.znajdz_ciekawostki` -> `aktualne_modele.pobierz` -> `db.connect()`
    otwieralo PRODUKCYJNA baze z `test_piec.py` i `test_pas_wydarzen.py`,
    a zaden z tych plikow nie ma w sobie slowa „connect".

    Dzis to nie niszczy danych tylko dlatego, ze produkcyjny schemat jest
    aktualny. Na bazie o jedna kolumne starszej ten sam przebieg dopisuje
    kolumny: zmierzone na kopii — trzy `ALTER TABLE`, 12288 -> 24576 bajtow,
    inny SHA. Kazda nowa kolumna w `NOWE_KOLUMNY` uzbraja to od nowa.
    """
    if not config.W_TESCIE:
        return
    if getattr(config, "WOLNO_TKNAC_PRODUKCYJNA_BAZE", False):
        return
    if not config.pod_produkcyjnymi_danymi(db_path):
        return
    raise ProdukcyjnaBazaWTescie(
        "Darmowy test probuje otworzyc PRODUKCYJNA baze:\n"
        "    %s\n\n"
        "Prawie na pewno przestawiles `config.DATA_DIR` bez `config.DB_PATH`.\n"
        "`DB_PATH` jest liczone RAZ przy imporcie, wiec samo `DATA_DIR` go nie rusza.\n\n"
        "Popraw tak — jedno wywolanie przestawia komplet sciezek:\n"
        "    stare = config.uzyj_katalogu_danych(katalog_tymczasowy)\n"
        "    try:\n"
        "        ...\n"
        "    finally:\n"
        "        config.przywroc_katalog_danych(stare)\n\n"
        "Jesli ten test NAPRAWDE ma dotknac produkcji, powiedz to wprost:\n"
        "    config.WOLNO_TKNAC_PRODUKCYJNA_BAZE = True"
        % db_path
    )


def connect(path: Path | None = None) -> sqlite3.Connection:
    """Otwiera bazę i zakłada schemat, jeśli go nie ma."""
    db_path = Path(path) if path is not None else Path(config.DB_PATH)
    _odmow_produkcji(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _dopisz_brakujace_kolumny(conn)
    conn.commit()
    return conn


# Kolumny dopisane do `calls` PO tym, jak baza produkcyjna juz istniala.
# `CREATE TABLE IF NOT EXISTS` istniejacej tabeli NIE rusza, wiec bez tego
# pierwszy zapis do starej bazy konczy sie bledem „no such column".
#
# To jest celowo waski system migracji: „zmiana schematu to nowa kolumna z
# wartoscia domyslna, nigdy przepisywanie danych". Funkcja robi dokladnie tyle
# i ani kroku wiecej; nie utrzymuje wersji ani migracji danych.
NOWE_KOLUMNY = {
    "calls": {"cache_hit": "INTEGER NOT NULL DEFAULT 0",
              # KTORE DZIALANIE ZA TO ZAPLACILO — patrz `AKCJA` i `kanal`.
              "akcja": "TEXT NOT NULL DEFAULT ''"},
    # TOR PRZEBIEGU. „produkcja" to praca konta, „test" to sprawdzanie kodu.
    # Domyslnie produkcja, bo bezpieczniejsza pomylka to policzyc test jako
    # produkcje (mniej wolnego budzetu) niz odwrotnie.
    "runs": {"tryb": "TEXT NOT NULL DEFAULT 'produkcja'"},
}


def _dopisz_brakujace_kolumny(conn: sqlite3.Connection) -> None:
    for tabela, kolumny in NOWE_KOLUMNY.items():
        try:
            maja = {w[1] for w in conn.execute("PRAGMA table_info(%s)" % tabela)}
        except sqlite3.Error:
            continue
        for nazwa, typ in kolumny.items():
            if nazwa not in maja:
                try:
                    conn.execute("ALTER TABLE %s ADD COLUMN %s %s"
                                 % (tabela, nazwa, typ))
                    print("  [baza] dopisano kolumne %s.%s" % (tabela, nazwa),
                          flush=True)
                except sqlite3.Error as exc:
                    print("  [baza] nie dopisalem %s.%s: %s" % (tabela, nazwa, exc),
                          flush=True)


def start_run(conn: sqlite3.Connection, stage: str = "start",
              tryb: str | None = None) -> int:
    """Nowy przebieg. `tryb` to „produkcja" albo „test".

    TOR TESTOWY ISTNIEJE, ZEBY SPRAWDZANIE NIE JADLO SUFITU KONTA. 30 sierpnia
    dzien audytu segmentu tematow zjadl 3,87 USD do poludnia — w wiekszosci na
    MOJE przebiegi sprawdzajace, nie na notki i komentarze. Sufit dzienny
    chroni przed rozbieganym agentem w nocy i ma pilnowac PRACY KONTA, a nie
    pracy nad kodem.

    Tryb bierze sie z jawnego argumentu albo ze zmiennej `NIA_TRYB`. Domyslnie
    produkcja — bezpieczniejsza pomylka to policzyc test jako produkcje niz
    otworzyc produkcji drugi, luzniejszy sufit.
    """
    import os
    wybrany = (tryb or os.environ.get("NIA_TRYB") or "produkcja").strip().lower()
    if wybrany not in ("produkcja", "test"):
        wybrany = "produkcja"
    cur = conn.execute(
        "INSERT INTO runs (started_at, status, stage, tryb) VALUES (?, 'RUNNING', ?, ?)",
        (now(), stage, wybrany),
    )
    conn.commit()
    return int(cur.lastrowid)


def tryb_przebiegu(conn: sqlite3.Connection, run_id: int | None) -> str:
    """Tor, do ktorego nalezy przebieg. Bez przebiegu — produkcja."""
    if run_id is None:
        return "produkcja"
    try:
        w = conn.execute("SELECT tryb FROM runs WHERE id = ?", (run_id,)).fetchone()
    except sqlite3.Error:
        return "produkcja"
    return (w["tryb"] if w and w["tryb"] else "produkcja")


def finish_run(
    conn: sqlite3.Connection, run_id: int, status: str, stage: str, note: str = ""
) -> None:
    conn.execute(
        "UPDATE runs SET finished_at = ?, status = ?, stage = ?, note = ?,"
        " cost_usd = (SELECT COALESCE(SUM(cost_usd), 0) FROM calls WHERE run_id = ?)"
        " WHERE id = ?",
        (now(), status, stage, note, run_id, run_id),
    )
    conn.commit()


def record_call(conn: sqlite3.Connection, **fields: Any) -> None:
    """Zapisuje wywołanie, wstawiając TYLKO te kolumny, które ktoś podał.

    Wcześniej lista kolumn była stała, a brakujące pola szły jako `fields.get(k)`
    — czyli jawny NULL. SQL-owe `DEFAULT 0` wtedy NIE dziala: default wchodzi
    tylko wtedy, gdy kolumny w INSERT nie ma wcale, a nie gdy jest z NULL-em.
    Skutkiem był `IntegrityError: NOT NULL constraint failed` u każdego, kto nie
    podał kompletu.

    Kosztowało to okładkę artykułu 0025 i — groźniej — przykrywało prawdziwe
    błędy API: gdy wywołanie tekstowe padało, ścieżka błędu próbowała je zapisać,
    wywalała się na tej samej kolumnie i to `IntegrityError` szedł w górę zamiast
    prawdziwej przyczyny.

    Dlatego poprawka siedzi TUTAJ, a nie w czterech miejscach wołających:
    następna kolumna dopisana do `calls` z wartością domyślną ma zadziałać sama,
    bez obchodzenia wszystkich wywołań.
    """
    # Znacznik dzialania dokladamy TUTAJ, a nie u wolajacych: inaczej sciezki
    # bledu i `obraz` — czyli te wywolania, o ktorych latwo zapomniec — byly by
    # jedynymi bez przypisania do kanalu.
    fields.setdefault("akcja", AKCJA)
    keys = [k for k in (
        "run_id", "provider", "model", "purpose", "tokens_in", "tokens_out",
        "cache_hit", "web_searches", "cost_usd", "price_verified", "ok", "note",
        "akcja",
    ) if k in fields]
    conn.execute(
        f"INSERT INTO calls (at, {', '.join(keys)})"
        f" VALUES (?, {', '.join('?' * len(keys))})",
        [now(), *(fields[k] for k in keys)],
    )
    conn.commit()


def spent_usd(conn: sqlite3.Connection, since_prefix: str,
              tryb: str = "produkcja") -> float:
    """Suma kosztów od znacznika czasu zaczynającego się danym prefiksem.

    `since_prefix` to `YYYY-MM-DD` dla doby albo `YYYY-MM` dla miesiąca — daty są
    zapisane w ISO 8601 UTC, więc porównanie prefiksem wystarczy i nie wymaga
    drugiej reprezentacji czasu w bazie.

    `tryb` ODDZIELA PRACE KONTA OD PRACY NAD KODEM. Sufit dzienny chroni przed
    rozbieganym agentem w nocy; przebiegi sprawdzajace nie maja go zjadac.
    Wywolanie bez przebiegu liczy sie do produkcji — bezpieczniejsza pomylka.
    """
    row = conn.execute(
        """SELECT COALESCE(SUM(c.cost_usd), 0) AS total
             FROM calls c
             LEFT JOIN runs r ON r.id = c.run_id
            WHERE c.at LIKE ?
              AND COALESCE(r.tryb, 'produkcja') = ?""",
        (f"{since_prefix}%", tryb),
    ).fetchone()
    return float(row["total"])


def recent_domains(conn: sqlite3.Connection, limit: int) -> list[str]:
    """Domeny z ostatnich N artykułów — wejście do reguły różnorodności."""
    rows = conn.execute(
        "SELECT DISTINCT s.domain FROM sources s"
        " JOIN articles a ON a.run_id = s.run_id"
        " WHERE a.status = 'SAVED'"
        " AND a.run_id IN (SELECT run_id FROM articles WHERE status = 'SAVED'"
        "                  ORDER BY id DESC LIMIT ?)",
        (limit,),
    ).fetchall()
    return [r["domain"] for r in rows]
