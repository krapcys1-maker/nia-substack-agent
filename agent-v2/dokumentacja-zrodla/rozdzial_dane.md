> **UWAGA REDAKCYJNA.** Ten rozdział powstał w audycie 2026-08-20 i opisuje stan
> **zastany**. Pięć wad, które opisuje, naprawiono jeszcze tego samego dnia —
> miejsca te są oznaczone w tekście. Opisy zostawiono w całości, bo pokazują
> klasę błędu, a nie tylko jego wystąpienie.

### Baza, dysk, koszty i operacje

Ten rozdział opisuje wszystko, co agent zapisuje na trwałe, ile to kosztuje i jak jest uruchamiane. Liczby pochodzą z produkcyjnej bazy `~/nia-substack-bot/agent-v2/data/agent-v2.db` odczytanej 2026-08-20 w trybie read-only oraz z `systemctl cat` na serwerze `SERWER_IP`.

---

### 1. Schemat bazy — cztery tabele

Cały schemat mieści się w jednym stringu w `agent-v2/db.py` i zakłada się sam przy każdym otwarciu połączenia. Nagłówek pliku mówi wprost, dlaczego:

```python
"""Baza: cztery tabele, zero migracji, zero triggerów, zero CHECK-ów z limitami.

Schemat powstaje z `CREATE TABLE IF NOT EXISTS` przy starcie. Zmiana schematu to
zmiana tego pliku — nie ma drabiny wersji, bo poprzedni agent miał 42 migracje
i to one blokowały produkcję, nie brak funkcji.

Limitów nie ma w `CHECK`-ach celowo: limit przypięty w schemacie to drugie
miejsce, w którym żyje ta sama liczba, a wtedy podniesienie jej w kodzie wywala
produkcję (stary agent: `attempt_no IN (1,2)` w ośmiu tabelach, 1,84 USD do kosza).
"""
```

Stan produkcji w chwili pisania: **28 przebiegów, 591 wywołań modeli, 6 artykułów, 104 źródła**. Plik bazy ma 262 144 bajty (64 strony po 4096), tryb dziennika `delete` — nie WAL.

#### `runs` — jeden wiersz na uruchomienie procesu

| kolumna | typ | po co jest |
|---|---|---|
| `id` | INTEGER PK AUTOINCREMENT | numer przebiegu; jest też **prefiksem nazwy pliku artykułu** (`NNNN-...md`), więc numeracja artykułów na dysku to numeracja przebiegów, nie artykułów |
| `started_at` | TEXT NOT NULL | ISO 8601 UTC z sekundową precyzją; wejście do kontroli ciszy w `alarm.cisza()` |
| `finished_at` | TEXT | NULL dopóki przebieg trwa — po tym poznaje się przebieg wiszący |
| `status` | TEXT NOT NULL | komentarz w schemacie mówi `RUNNING / DONE / FAILED` |
| `stage` | TEXT | na czym stanęło: `dzien`, `review`, `fetch`, `write`, `kontrola` |
| `cost_usd` | REAL NOT NULL DEFAULT 0 | **nie jest sumowane przyrostowo** — przeliczane raz, w `finish_run`, zapytaniem po `calls` |
| `note` | TEXT | powód zakończenia; przy porażce leci tu nazwa klasy wyjątku i komunikat |

**WADA.** Komentarz przy `status` wymienia trzy wartości, a produkcja ma cztery. Piąta wartość, `STALE`, jest wpisywana przez `alarm.zawieszone()` i w bazie jest jej pięć sztuk (przebiegi 1, 2, 6, 18, 22). Rozkład realny: 18 × `DONE`, 5 × `STALE`, 5 × `FAILED`. Komentarz w schemacie opisuje system, który nie istnieje — dokładnie ten sam błąd, który `config.py` piętnuje u poprzedniego agenta.

**WADA.** W `alarm.sprawdz_przebiegi_i_ostrzez` warunek brzmi `if all(r["status"] not in ("DONE", "SAVED") for r in ostatnie)`. `SAVED` nigdy nie jest statusem przebiegu — to status **artykułu**, z zupełnie innej tabeli. Gałąź jest martwa i myląca; ktokolwiek ją czyta, wnioskuje o istnieniu stanu, którego kod nigdy nie zapisuje.

#### `calls` — jeden wiersz na płatne wywołanie modelu

```python
CREATE TABLE IF NOT EXISTS calls (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id         INTEGER,
    at             TEXT NOT NULL,
    provider       TEXT NOT NULL,       -- anthropic / deepseek
    model          TEXT NOT NULL,
    purpose        TEXT NOT NULL,       -- scout / discovery / write / ...
    tokens_in      INTEGER NOT NULL DEFAULT 0,
    tokens_out     INTEGER NOT NULL DEFAULT 0,
    cache_hit      INTEGER NOT NULL DEFAULT 0,
    web_searches   INTEGER NOT NULL DEFAULT 0,
    cost_usd       REAL NOT NULL DEFAULT 0,
    price_verified INTEGER NOT NULL DEFAULT 1,  -- 0 = stawka niepotwierdzona
    ok             INTEGER NOT NULL DEFAULT 1,
    note           TEXT
);
```

Uzasadnienie `cache_hit` stoi w schemacie i jest warte przytoczenia w całości, bo tłumaczy, po co w ogóle dokładano kolumnę do działającej bazy:

```python
    -- Trafienia w cache byly LICZONE do kosztu i nigdzie nie zapisywane, wiec
    -- nie dalo sie sprawdzic, czy w ogole trafiamy. To ma znaczenie, bo cache
    -- jest 30x tanszy od zwyklego wejscia ($0,022 wobec $0,66 u pro), a nasza
    -- najdrozsza pozycja — dyskoveria — przesyla cala rozmowe w kazdej rundzie.
    -- Bez tej kolumny nie da sie odroznic „prefiks peka" od „prefiks trafia,
    -- a cena bierze sie skadinad".
```

- `provider` jest **wyliczany, nie podawany**: `provider = "deepseek" if model.startswith("deepseek") else "anthropic"`. Grafiki wpisują `"openai"` jawnie w `llm.obraz`.
- `price_verified` = 0 znaczy „koszt policzony stawką, której nie ma na fakturze". W całej produkcji jest **3 takich wierszy i wszystkie to `obraz`/`gpt-image-1.5`** — reszta cennika została odtworzona z rachunku.
- `ok` = 0 to wywołanie, które padło. W produkcji jest **zero takich wierszy** na 591.

**WADA.** Zero wierszy z `ok = 0` przy pięciu przebiegach `FAILED` znaczy, że ścieżka zapisu porażki w `llm.call` nigdy nie zadziałała na produkcji — bo przebiegi padały *poza* warstwą modelu (brakujący import `trafilatura`, niezgodny hash korpusu stylu, SIGTERM). Najczulszy fragment kodu finansowego jest więc w produkcji nieprzetestowany; jedyne, co go sprawdza, to testy.

**WADA.** `web_searches` miesza dwa różne zdarzenia. U Anthropic wyszukiwanie jest płatne osobno ($10/1000) i doliczane w `_cost`; u DeepSeeka mieści się w tokenach i **nie jest doliczane**. W bazie leży 1015 wyszukiwań i wszystkie są DeepSeekowe, czyli darmowe — ale sama kolumna tego nie mówi. Ktoś, kto policzy `SUM(web_searches) * 0.01`, dostanie 10,15 USD kosztu, którego nie było.

**Brak indeksów.** W bazie nie ma ani jednego `CREATE INDEX`. `_preflight` przed **każdym płatnym wywołaniem** robi trzy zapytania agregujące po `calls`: sumę dla `run_id`, sumę dla doby i sumę dla miesiąca. Przy 591 wierszach to nie ma znaczenia; przy 100 tysiącach będą to trzy pełne skany tabeli przed każdym pytaniem do modelu. Brak indeksu na `calls.run_id` i `calls.at` jest długiem, nie decyzją — nigdzie nie jest uzasadniony.

#### `articles` — artykuł w szufladzie

| kolumna | po co jest |
|---|---|
| `id`, `run_id` | powiązanie z przebiegiem, bez klucza obcego |
| `created_at` | ISO UTC |
| `topic` | temat wybrany przez skauta |
| `title`, `body` | tekst; w produkcji `length(body)` mieści się w 6250–6879 znaków |
| `evidence` | karta dowodowa jako JSON — twierdzenia z cytatami i adresami |
| `status` | `SAVED` / `BLOCKED` |
| `blocked_by` | która bramka zatrzymała |
| `notes` | uwagi niesblokujące, JSON |

Sześć artykułów, **wszystkie `SAVED`, wszystkie `blocked_by = NULL`**. Ścieżka `BLOCKED` w produkcji nigdy się nie wykonała — co jest spójne z zasadą zapisaną w `config.py` („NIC NIE BLOKUJE… artykuł powstaje zawsze i trafia do szuflady"), ale znaczy też, że dwie z czterech kolumn tej tabeli są w produkcji martwe.

#### `sources` — źródła znalezione i pobrane

| kolumna | po co jest |
|---|---|
| `url`, `domain` | `domain` osobno, bo karmi regułę różnorodności |
| `title` | nazwa do przypisu w pliku `.md` |
| `source_class` | `PRIMARY` / `SUPPORTING` / `ODPAD` |
| `fetched_ok` | 0/1 |
| `fail_reason` | dlaczego się nie udało |

Produkcja: 104 źródła, **75 różnych domen**, 71 pobranych, **33 nieudane (31,7%)**. Rozkład powodów:

| powód | ile |
|---|---|
| HTTP 403 | 10 |
| też pusto w przeglądarce (0 znaków) | 8 |
| za mało treści (0 znaków) | 3 |
| odzyskane w przeglądarce | 3 |
| HTTP 404 | 3 |
| HTTP 401 | 3 |
| host odmówił automatowi | 2 |
| za mało treści (116 znaków) | 1 |

Klasy: `PRIMARY` 62, `SUPPORTING` 42, **`ODPAD` — zero**.

**WADA.** `ODPAD` jest udokumentowany w schemacie i nigdy nie jest zapisywany. Ta sama choroba co przy `runs.status`: komentarz obiecuje wartość, której kod nie produkuje.

**WADA.** `fail_reason` bywa wypełniony przy **udanym** pobraniu — trzy wiersze mają powód „odzyskane w przeglądarce", czyli notatkę o sukcesie w kolumnie nazwanej „powód porażki". Filtr `WHERE fail_reason IS NOT NULL` daje więc 33 wiersze, a realnych porażek jest 30.

**WADA w regule różnorodności.** `db.recent_domains` ma karmić zasadę „nie stawiaj kolejnego artykułu na tych samych domenach":

```python
    rows = conn.execute(
        "SELECT DISTINCT s.domain FROM sources s"
        " JOIN articles a ON a.run_id = s.run_id"
        " WHERE a.status = 'SAVED'"
        " AND a.run_id IN (SELECT run_id FROM articles WHERE status = 'SAVED'"
        "                  ORDER BY id DESC LIMIT ?)",
        (limit,),
    ).fetchall()
```

Złączenie idzie po `run_id`, a nie po tym, których źródeł artykuł faktycznie użył. Zwracane są więc **wszystkie domeny odkryte w przebiegu**, łącznie z tymi, które zwróciły 403 i nigdy nie zostały przeczytane. Przy 31,7% nieudanych pobrań blokujemy sobie domeny, z których ani razu nie skorzystaliśmy.

**Brak kluczy obcych.** `calls.run_id`, `articles.run_id`, `sources.run_id` nie mają `REFERENCES runs(id)`. To wynika wprost z zasady „zero migracji, zero triggerów". Konsekwencja: osierocone wiersze są możliwe. W produkcji nie ma ani jednego wywołania z `run_id IS NULL`.

---

### 2. Brak migracji — jak dokładane są kolumny

Nie ma drabiny wersji. Jest jeden słownik i jedna funkcja:

```python
# Kolumny dopisane do `calls` PO tym, jak baza produkcyjna juz istniala.
# `CREATE TABLE IF NOT EXISTS` istniejacej tabeli NIE rusza, wiec bez tego
# pierwszy zapis do starej bazy konczy sie bledem „no such column".
#
# To nie jest system migracji i ma nim nie byc — projekt stoi na zasadzie
# „zmiana schematu to nowa kolumna z wartoscia domyslna, nigdy przepisywanie
# danych". Ta funkcja robi dokladnie tyle i ani kroku wiecej.
NOWE_KOLUMNY = {
    "calls": {"cache_hit": "INTEGER NOT NULL DEFAULT 0"},
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
```

Wywoływana jest przy **każdym** otwarciu połączenia, zaraz po `executescript(SCHEMA)`:

```python
def connect(path: Path | None = None) -> sqlite3.Connection:
    """Otwiera bazę i zakłada schemat, jeśli go nie ma."""
    db_path = path or config.DB_PATH
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _dopisz_brakujace_kolumny(conn)
    conn.commit()
    return conn
```

Że to zadziałało, widać w produkcji gołym okiem — `sqlite_master` pokazuje `cache_hit` **doklejone za `note`, poza wcięciem reszty**, dokładnie tak, jak zostawia to `ALTER TABLE`:

```sql
    ok             INTEGER NOT NULL DEFAULT 1,
    note           TEXT
, cache_hit INTEGER NOT NULL DEFAULT 0)
```

`PRAGMA table_info(calls)` potwierdza: `cache_hit` ma indeks 13, czyli jest ostatnia, mimo że w `SCHEMA` stoi na pozycji 8. **Baza produkcyjna i świeżo założona baza mają tę samą treść w innej kolejności kolumn.** Każdy kod polegający na pozycji kolumny (`row[8]`) zachowa się na nich inaczej. `db.py` konsekwentnie używa `sqlite3.Row` i nazw, więc problem jest utajony, ale realny.

**WADA — cichy błąd.** `except sqlite3.Error` wypisuje komunikat i idzie dalej. Jeśli `ALTER TABLE` się nie uda (baza tylko do odczytu, zajęta przez inny proces), `connect()` **zwróci działające połączenie do bazy bez kolumny**, a awaria wyjdzie dopiero przy pierwszym `INSERT`, w innym miejscu i pod inną nazwą. Komunikat leci na `stdout` serwera, którego — jak sam `alarm.py` przyznaje w nagłówku — nikt nie czyta.

**WADA — słownik rośnie w nieskończoność.** `NOWE_KOLUMNY` nie ma mechanizmu wygaszania wpisów. Za rok będzie tam kilkanaście kolumn, z których wszystkie od dawna istnieją w każdej bazie, a `PRAGMA table_info` będzie wołane dla każdej z nich przy każdym starcie procesu. Nie ma też nic, co pilnuje **spójności `SCHEMA` z `NOWE_KOLUMNY`** — dopisanie kolumny tylko do `SCHEMA` (bez wpisu w słowniku) daje działającą nową bazę i zepsutą starą; dopisanie tylko do słownika daje odwrotnie. Te dwa miejsca muszą być zmieniane parami, ręcznie, i nic tego nie sprawdza.

---

### 3. Pułapka `record_call`: DEFAULT nie działa przy jawnym NULL

To jest najkosztowniejszy błąd w całej warstwie danych i najmniej oczywisty. Docstring opisuje go w całości:

```python
def record_call(conn: sqlite3.Connection, **fields: Any) -> None:
    """Zapisuje wywołanie, wstawiając TYLKO te kolumny, które ktoś podał.

    Wcześniej lista kolumn była stała, a brakujące pola szły jako `fields.get(k)`
    — czyli jawny NULL. SQL-owe `DEFAULT 0` wtedy NIE dziala: default wchodzi
    tylko wtedy, gdy kolumny w INSERT nie ma wcale, a nie gdy jest z NULL-em.
    Skutkiem był `IntegrityError: NOT NULL constraint failed` u każdego, kto nie
    podał kompletu.

    Kosztowało to okładkę jednego artykułu i — groźniej — przykrywało prawdziwe
    błędy API: gdy wywołanie tekstowe padało, ścieżka błędu próbowała je zapisać,
    wywalała się na tej samej kolumnie i to `IntegrityError` szedł w górę zamiast
    prawdziwej przyczyny.

    Dlatego poprawka siedzi TUTAJ, a nie w czterech miejscach wołających:
    następna kolumna dopisana do `calls` z wartością domyślną ma zadziałać sama,
    bez obchodzenia wszystkich wywołań.
    """
    keys = [k for k in (
        "run_id", "provider", "model", "purpose", "tokens_in", "tokens_out",
        "cache_hit", "web_searches", "cost_usd", "price_verified", "ok", "note",
    ) if k in fields]
    conn.execute(
        f"INSERT INTO calls (at, {', '.join(keys)})"
        f" VALUES (?, {', '.join('?' * len(keys))})",
        [now(), *(fields[k] for k in keys)],
    )
    conn.commit()
```

Mechanika w jednym zdaniu: `INSERT INTO calls (cache_hit) VALUES (NULL)` **nie jest** tym samym co `INSERT INTO calls (...)` bez `cache_hit`. W pierwszym wypadku SQLite wstawia NULL i uderza w `NOT NULL`; w drugim sięga po `DEFAULT 0`. Stary kod robił pierwsze, bo `fields.get(k)` zwraca `None` dla brakujących kluczy.

Konsekwencje były trzy i tylko pierwsza była widoczna:

1. **Okładka jednego artykułu nie powstała.** Ścieżka `llm.obraz` nie podawała `cache_hit`, więc `INSERT` padał po opłaceniu grafiki u OpenAI. Artykuł wyszedł bez nagłówka.
2. **Prawdziwa przyczyna błędu była zjadana.** Ścieżka porażki w `llm.call` sama woła `record_call`. Gdy padało wywołanie tekstowe, obsługa błędu wywalała się na tej samej kolumnie i w górę szedł `IntegrityError` — a nie odmowa dostawcy, zły klucz czy timeout. Awaria kłamała o tym, na co padła.
3. **Log mówił za mało, żeby to znaleźć.** Naprawa objęła też komunikat w `stages.py`:

```python
    except Exception as exc:
        # TREŚĆ wyjątku, nie sama nazwa klasy. Gdy grafika artykułu padła
        # na `IntegrityError`, log powiedział tylko tyle — a przyczyna („NOT NULL
        # constraint failed: calls.cache_hit") siedziała w zjedzonym komunikacie
        # i trzeba jej było szukać po kodzie. Awaria, która nie mówi na co padła,
        # kosztuje drugi raz.
        print(f"  [grafika] NIE POWSTAŁA ({type(exc).__name__}: {exc}) — "
              f"artykuł wychodzi bez nagłówka", flush=True)
```

Umiejscowienie poprawki jest słuszne: gdyby siedziała w czterech miejscach wołających, następna dopisana kolumna zepsułaby wszystkie cztery od nowa.

**WADA — poprawka zamienia głośną awarię na cichą.** Lista `keys` jest **filtrem, nie kontraktem**. Literówka w nazwie argumentu nie jest błędem: `record_call(conn=conn, cost_used=0.53, ...)` przejdzie bez słowa i zapisze wiersz z `cost_usd = 0` z `DEFAULT`. Przedtem brak pola wywalał proces; teraz brak pola **fałszuje księgi**. W zapisie finansowym to jest gorsza wymiana niż wygląda, a nic — ani asercja, ani test, ani `price_verified` — tego nie łapie.

**WADA — kolumny `NOT NULL` bez `DEFAULT` nadal wysadzają.** `provider`, `model`, `purpose` nie mają wartości domyślnej. Pominięcie któregoś z nich to dalej `IntegrityError`, tyle że teraz o kolumnę, której nie ma w `INSERT`. Docstring obiecuje, że „następna kolumna z wartością domyślną zadziała sama" — i to jest prawda tylko dla kolumn z wartością domyślną.

---

### 4. Wszystko, co leży na dysku w `data/`

Katalog `data/` jest w całości poza gitem (`.gitignore`: `data/*` z jednym wyjątkiem `!data/.gitkeep`). Zajmuje **8,0 MB** na dysku, na którym z 96 GB wolne jest 90 GB (7% zajęcia).

| plik / katalog | rozmiar | co zawiera | kto pisze | kto czyta | przycinanie |
|---|---|---|---|---|---|
| `agent-v2.db` | 256 KB | cztery tabele, cała historia kosztów | `db.py` przy każdym wywołaniu i etapie | `llm._preflight`, `alarm.*`, raporty | **brak** |
| `agent-v2-przed-v2-20260819-1949.db` | 212 KB | kopia sprzed przejścia na v2 (24 przebiegi, 519 wywołań) | ręcznie | nikt | **brak** |
| `agent-v2.db.przed-poprawka-statusu` | 32 KB | kopia sprzed poprawki statusów (4 przebiegi, 64 wywołania) | ręcznie | nikt | **brak** |
| `agent.db` | **0 B** | pusty | nieznane | nikt | — |
| `zasiew-produkcji.db` | **0 B** | pusty | nieznane | nikt | — |
| `articles/` | **7,2 MB** | `NNNN-slug.md`, `NNNN-slug.png`, `NNNN-slug.uwagi.md` | `stages.save`, `stages` (grafika) | właściciel, `stages` przy liczeniu dorobku | **brak** |
| `cache/` | 160 KB | `scout/feasibility/discovery/fetch/classify/synthesis/write/review.json` | `run.cached` | `run.cached` przy `--use-cache` | nadpisywane, nie rosną |
| `dziennik.jsonl` | 44 KB / 173 wiersze | jeden JSON na działanie w świecie: notka, komentarz, odpowiedź, polubienie, skutek | `browser.zapisz_w_dzienniku` (dopisywanie) | `alarm.przeglad`, `stages` (ostatnie otwarcia), `browser.z_dziennika_dzis` | **brak** |
| `zuzyte_fakty.json` | 9,0 KB / 40 wpisów | zdania-fakty już wykorzystane w notkach | `stages.zapisz_zuzyte` | `stages.wczytaj_zuzyte`, `alarm.powtorki` | **tak** — do `CURIOSITY_MEMORY * 3` = 180 |
| `indeks_kandydatow.json` | 18 KB / 16 wpisów | kandydaci tematów | `stages` (indeks) | `stages` | **tak** — `indeks[-600:]` |
| `promocja.json` | 6,9 KB / 4 wpisy | opublikowane artykuły do promowania notkami, każdy z `tekst[:9000]` | `stages.zapisz_do_promocji` | `stages.artykul_do_promocji` | **brak** |
| `promocja.json.przed-naprawa` | 15 KB | kopia sprzed naprawy kolejki | ręcznie | nikt | — |
| `zuzyte_fakty.json.przed-naprawa` | 8,0 KB | kopia sprzed naprawy kształtu wpisów | ręcznie | nikt | — |
| `gdzie_komentowalismy.json` | 3,1 KB / 47 kluczy | domena → znacznik czasu ostatniego komentarza | `kanal.zapamietaj_komentarz` | `kanal` przy wyborze celu | **brak** |
| `alarmy.json` | 62 B / 1 klucz | rodzaj alarmu → kiedy ostatnio poszedł | `alarm._zapisz` | `alarm._ostatnio` | **brak** (rośnie o klucz na rodzaj) |
| `storage-state.json` | 21 668 B, tryb **0600** | sesja Substacka (ciasteczka) | `browser.py sesja` na komputerze właściciela | `browser.podlacz_sie` | **brak** |
| `storage-state-serwer.json` | 21 668 B, tryb **0600** (do 2026-08-20 bylo 0644) | ta sama sesja | ręcznie skopiowane | — | **brak** |
| `agent.lock` | 7 B | PID przebiegu trzymającego zamek | `run.zajmij_zamek` | `wdroz.sh` przez `flock -n` | nadpisywane |
| `kopie/` | **NIE ISTNIALO do 2026-08-20; od tego dnia pilnuje tego `alarm.kopia_subskrybentow`** | kopie listy subskrybentów | `kopia_subskrybentow.py` | człowiek | `ILE_KOPII = 30` |

**WADA — okładki są całym dyskiem.** 7,2 MB z 8,0 MB katalogu to trzy pliki PNG: 3,0 MB, 2,3 MB i 1,9 MB. `gpt-image-1.5` w `1536x1024` przy `quality="high"` daje 2–3 MB na obraz i nic tych plików nigdy nie usuwa. Przy czterech artykułach miesięcznie to ~10 MB/miesiąc — przy 90 GB wolnego miejsca nieszkodliwe przez lata, ale jest to jedyna pozycja rosnąca liniowo bez żadnego limitu, a `alarm.dysk()` zareaguje dopiero przy 80%.

**WADA — dwa zerobajtowe pliki bazy.** `agent.db` (0 B, 19 sierpnia) i `zasiew-produkcji.db` (0 B, 19 sierpnia). `agent.db` to nazwa bazy **poprzedniego** agenta. Leżą w katalogu produkcyjnym, nic ich nie czyta i nic nie tłumaczy, skąd się wzięły. Zerobajtowy plik SQLite jest poprawną pustą bazą — jeśli kiedykolwiek jakaś ścieżka spadnie na domyślną nazwę `agent.db`, `db.connect()` **z powodzeniem założy w nim schemat** i agent będzie pisał do pustej bazy bez jednego słowa błędu.

**WADA — sesja byla czytelna dla wszystkich (NAPRAWIONE 2026-08-20).** `storage-state.json` ma tryb `0600`, a jego bliźniacza kopia `storage-state-serwer.json` miała `0644`. Oba pliki mają identyczny rozmiar 21 668 bajtów, czyli to ta sama sesja. Plik sesji jest w praktyce hasłem do konta na Substacku: kto go skopiuje, jest zalogowany. Jedna z dwóch kopii tego samego sekretu jest światoczytelna.

**WADA — pięć plików kopii zapasowych w katalogu roboczym.** `*.przed-naprawa`, `*.przed-poprawka-statusu`, `agent-v2-przed-v2-*.db`. Żaden nie ma daty wygaśnięcia ani właściciela. Katalog roboczy agenta pełni funkcję archiwum, a archiwum nie ma rotacji.

**WADA — dziennik rośnie i jest czytany w całości.** `dziennik.jsonl` to append-only i nic go nie przycina. `alarm.przeglad` oraz funkcja odczytująca ostatnie otwarcia notek robią `plik.read_text(...).splitlines()` — czyli wczytują **cały** plik do pamięci, żeby wziąć z niego ostatnie N wpisów. Przy 173 wierszach po pięciu dniach to 44 KB; po roku będzie to kilkanaście MB wczytywanych przy każdym przebiegu, żeby odczytać dwadzieścia ostatnich linii.

Zapis jest za to zrobiony poprawnie — nigdy nie przerywa agenta:

```python
    try:
        wpis = {"kiedy": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "rodzaj": rodzaj, **szczegoly}
        DZIENNIK.parent.mkdir(parents=True, exist_ok=True)
        with open(DZIENNIK, "a", encoding="utf-8") as f:
            f.write(_json.dumps(wpis, ensure_ascii=False) + "\n")
    except Exception:
        pass
```

Przycinanie tam, gdzie jest, jest jednowierszowe:

```python
def zapisz_zuzyte(nowe: list[Any]) -> None:
    """Pamięć zużytych ciekawostek — poza bazą, bo budżet to cztery tabele."""
    wszystkie = wczytaj_zuzyte() + [t for t in map(tekst_faktu, nowe) if t]
    ZUZYTE_FAKTY.parent.mkdir(parents=True, exist_ok=True)
    ZUZYTE_FAKTY.write_text(
        json.dumps(wszystkie[-config.CURIOSITY_MEMORY * 3:], ensure_ascii=False,
                   indent=1),
        encoding="utf-8",
    )
```

Ten plik ma też własną historię awarii, opisaną w kodzie: fakt bywa słownikiem `{"fact": ..., "url": ...}`, a bywa samym zdaniem. Słownik, który tam wpadł, wywalał `_klucz_faktu` przy następnym szukaniu — bo słownik nie ma `.lower()` — i cicho zabierał cały blok notek. Zdarzyło się 17 sierpnia; naprawa (`tekst_faktu`) sprząta **przy odczycie**, nie tylko przy zapisie, więc leczy też pliki już popsute.

---

### 5. Warstwa modeli: cennik, mnożnik szczytu, cache, liczenie kosztu

Cennik jest w `config.py`, w USD za milion tokenów. `verified` znaczy „odtworzone z faktury", nie „przepisane z cennika":

```python
PRICING = {
    CLAUDE: {"in": 5.00, "out": 25.00, "verified": True},
    SONNET: {"in": 3.00, "out": 15.00, "verified": True},
    FABLE: {"in": 10.00, "out": 50.00, "verified": True},
    # STAWKI POTWIERDZONE FAKTURA (15-19 sierpnia 2026). Dziesiec wierszy
    # rozliczenia odtworzonych co do centa, wiec `verified` znaczy tu wreszcie
    # to, co powinno: rozliczone z rachunkiem, nie przepisane z cennika.
    #
    # Co bylo zle wczesniej i czemu trudno bylo to zobaczyc: mnozniki taryfy
    # wykalibrowano na WYJSCIU (0,87 x 2,28 = 1,98 — trafione co do grosza)
    # i ten sam mnoznik zastosowano do wejscia i cache. A rodzaje tokenow
    # podrozaly ROZNIE: wejscie 1,52x, wyjscie 2,28x, cache 6,07x. Skutek:
    # wejscie zawyzone o polowe, cache zanizone prawie trzykrotnie.
    #
    # "in" to stawka cache MISS; trafienia w cache licza sie osobno po "cache"
    # — dostawca podaje ich liczbe w kazdej odpowiedzi, wiec nie zgadujemy.
    DEEPSEEK: {"in": 0.22, "out": 0.66, "cache": 0.007, "verified": True},
    DEEPSEEK_PRO: {"in": 0.66, "out": 1.98, "cache": 0.022, "verified": True},
}
```

#### Taryfa szczytowa DeepSeeka

```python
TARYFA_SZCZYTOWA_OD = "2026-08-16T16:00:00+00:00"
GODZINY_SZCZYTU_UTC = frozenset(range(1, 4)) | frozenset(range(6, 10))

# Mnozniki wzgledem stawek wyzej, po wejsciu nowej taryfy.
# Szczyt to DOKLADNIE dwukrotnosc bazy, jednakowo dla wejscia, wyjscia
# i cache. Sprawdzone na fakturze: 1,32/0,66, 3,96/1,98, 0,044/0,022.
MNOZNIK_SZCZYT = 2.0
MNOZNIK_POZA_SZCZYTEM = 1.0   # baza to juz stawka po podwyzce


def stawka_deepseek(model: str, kiedy=None) -> dict[str, float]:
    """Stawka DeepSeeka z uwzglednieniem pory doby po wejsciu nowej taryfy."""
    from datetime import datetime, timezone

    baza = PRICING[model]
    kiedy = kiedy or datetime.now(timezone.utc)
    if kiedy < datetime.fromisoformat(TARYFA_SZCZYTOWA_OD):
        # Przed podwyzka. Zostawiamy do liczenia historii, nie do biezacych
        # wywolan — te i tak dzieja sie po tej dacie.
        stare = STAWKI_PRZED_PODWYZKA[model]
        return {"in": stare["in"], "out": stare["out"], "cache": stare["cache"],
                "szczyt": None}
    m = (MNOZNIK_SZCZYT if kiedy.hour in GODZINY_SZCZYTU_UTC
         else MNOZNIK_POZA_SZCZYTEM)
    # CACHE TEZ. Brak tego klucza sprawial, ze `_cost` siegalo po stawke
    # wejsciowa i liczylo trafienia w cache 45 razy drozej, niz sa — a to
    # najliczniejszy rodzaj tokenow, jaki mamy.
    return {"in": round(baza["in"] * m, 6), "out": round(baza["out"] * m, 6),
            "cache": round(baza["cache"] * m, 6),
            "szczyt": kiedy.hour in GODZINY_SZCZYTU_UTC}
```

Szczyt to godziny **01:00–03:59 i 06:00–09:59 UTC**. Wniosek zapisany w komentarzu — „agent ma pracować POZA SZCZYTEM, to darmowa połowa rachunku za przesunięcie godziny" — jest przełożony na harmonogram: zegary chodzą o 11:20, 19:20 i 23:40 UTC oraz we wtorki o 14:00 UTC. Żadna z tych godzin nie jest szczytem.

Ale eksperymenty uruchamiane ręcznie już tak. Rozkład wydatków DeepSeeka według godziny UTC z produkcji:

| godzina UTC | wywołań | koszt | szczyt? |
|---|---|---|---|
| 00 | 35 | $0,4210 | nie |
| **01** | **2** | **$0,0095** | **tak** |
| **03** | **44** | **$1,1842** | **tak** |
| 04 | 34 | $0,3112 | nie |
| **08** | **15** | **$1,0536** | **tak** |
| 11 | 42 | $0,3452 | nie |
| 12 | 55 | $0,3629 | nie |
| 13 | 29 | $0,1629 | nie |
| 14 | 13 | $0,3909 | nie |
| 15 | 45 | $0,3700 | nie |
| 16 | 54 | $0,4812 | nie |
| 17 | 30 | $0,1922 | nie |
| 18 | 17 | $0,2540 | nie |
| 19 | 26 | $0,4642 | nie |
| 20 | 48 | $0,6342 | nie |
| 21 | 52 | $0,2929 | nie |
| 22 | 25 | $0,1532 | nie |
| 23 | 12 | $0,3640 | nie |

**61 wywołań za $2,2473 poszło po podwójnej stawce** — czyli około **$1,12 nadpłaty**, ponad 10% całego dotychczasowego rachunku. Wszystkie z uruchomień ręcznych: test A/B dyskoverii o 03:36–04:08 (przebieg 21) i seria artykułowa o 08:0x (przebiegi 12–14).

**WADA.** Harmonogram unika szczytu, ale **nic nie ostrzega człowieka**, który odpala `run.py` ręcznie o 03:40. `config.w_szczycie()` istnieje i zwraca dokładnie tę informację, ale `_preflight` jej nie woła i nigdzie nie pada zdanie „płacisz teraz podwójnie".

#### Jak liczony jest koszt

```python
def _cost(model: str, tokens_in: int, tokens_out: int, web_searches: int,
          cache_hit: int = 0) -> tuple[float, bool]:
    # DeepSeek liczy od 2026-08-16 wg pory doby, wiec stawke bierzemy na moment
    # wywolania, a nie ze stalej. Roznica miedzy szczytem a reszta doby to
    # dwukrotnosc — na tyle duzo, ze usrednianie zafalszowaloby zapis.
    if model.startswith("deepseek"):
        stawka = config.stawka_deepseek(model)
        price = {"in": stawka["in"], "out": stawka["out"],
                 "verified": config.PRICING[model]["verified"]}
    else:
        price = config.PRICING[model]
    # Trafienia w cache platne osobno i ~120x taniej. `tokens_in` liczymy jako
    # miss, bo tak podaje je dostawca po odjeciu trafien.
    usd = (tokens_in / 1_000_000 * price["in"]
           + tokens_out / 1_000_000 * price["out"]
           + cache_hit / 1_000_000 * price.get("cache", price["in"]))
    # Osobna opłata za wyszukiwanie jest cennikiem Anthropic. U DeepSeeka
    # wyszukiwanie mieści się w tokenach — doliczanie tu $10/1000 zawyżałoby
    # zapis finansowy, a zmyślonej kwoty w księgach być nie może.
    if model in (config.CLAUDE, config.SONNET):
        usd += web_searches / 1_000 * config.WEB_SEARCH_USD_PER_1K
    return round(usd, 6), bool(price["verified"])
```

**BŁĄD W `_cost`, którego nie widać — NAPRAWIONY 2026-08-20.**
Poniższy opis dotyczy stanu sprzed poprawki; `_cost` przepisuje teraz
klucz `cache` ze `stawka_deepseek`. Zostawiony w całości, bo pokazuje
klasę błędu: poprawka zatrzymała się w połowie drogi, a raport mówił,
że jest cała. Słownik `price` budowany dla DeepSeeka ma tylko klucze `in`, `out`, `verified` — **`cache` nie jest przepisywane**. Linia `price.get("cache", price["in"])` sięga więc po stawkę wejściową i liczy trafienia w cache **trzydzieści razy drożej**, niż wynosi stawka cache ($0,66 zamiast $0,022 u pro). Cała robota `stawka_deepseek`, która świadomie zwraca klucz `"cache"` (i której komentarz mówi wprost, że jego brak „liczył trafienia 45 razy drożej"), jest w tym miejscu wyrzucana do kosza. Skala szkody: 78 848 tokenów trafionych w cache w całej bazie → naliczone ~$0,033 zamiast ~$0,0011, czyli **około 3 centów zawyżenia**. Finansowo nic; jako zapis — koszt liczony stawką, która nie odpowiada niczemu na fakturze, a `price_verified` mimo to stoi na 1.

**Skutek uboczny tego samego wiersza dla Anthropic.** `PRICING[CLAUDE]` też nie ma klucza `cache`, więc gdyby ścieżka Anthropic kiedykolwiek zwróciła trafienia w cache, byłyby one liczone po $5/mln zamiast po stawce cache. Dziś nie strzela, bo `llm.call` twardo ustawia `cache_hit = 0` dla Anthropic — ale to jest wyłącznik na jeden wiersz od zniknięcia.

#### Skąd biorą się trafienia w cache

Tylko DeepSeek na `/chat/completions` (bez wyszukiwania) zwraca je jawnie:

```python
    usage = payload.get("usage", {})
    trafienia = int(usage.get("prompt_cache_hit_tokens", 0))
    pudla = int(usage.get("prompt_cache_miss_tokens",
                          usage.get("prompt_tokens", 0) - trafienia))
```

Produkcja: **45 wywołań ma niezerowe trafienia, razem 78 848 tokenów z cache przy 49 204 tokenach pudeł** — czyli w tych wywołaniach 61,6% wejścia to trafienia. Rozkład:

| etap | trafienia | pudła | wywołań |
|---|---|---|---|
| `comment` | 69 120 | 26 331 | 30 |
| `classify` | 2 560 | 12 625 | 5 |
| `restack` | 2 304 | 558 | 3 |
| `cele` | 2 048 | 3 621 | 4 |
| `warto_pisac` | 1 152 | 2 055 | 1 |
| `feasibility` | 1 024 | 295 | 1 |
| `review` | 640 | 3 719 | 1 |

Odpowiedź na pytanie, dla którego dołożono kolumnę, brzmi więc: **prefiks trafia, ale prawie wyłącznie na komentarzach** — bo tam ten sam długi system prompt jedzie kilkanaście razy pod rząd. Dyskoveria, czyli pozycja, dla której cache miałby największą wartość, ma **zero trafień**, bo idzie przez `/responses`, a ta ścieżka w ogóle nie ustawia `cache_hit`.

---

### 6. Sufity tokenów i skąd wzięły się konkretne liczby

Zasada jest zapisana w nagłówku `config.py`:

> Sufity tokenów są WYLICZANE z kontraktów, a nie wpisywane obok nich. Sufit wpisany ręcznie obok promptu proszącego o więcej, niż się w nim mieści, uciął odpowiedź DeepSeeka w połowie JSON-a przy pierwszym teście seryjnym.

Przelicznik:

```python
CHARS_PER_TOKEN = 3.5
JSON_OVERHEAD_TOKENS = 1200

def _tokens_for(chars: int) -> int:
    return int(chars / CHARS_PER_TOKEN) + JSON_OVERHEAD_TOKENS
```

Wybrane pozycje i ich rodowód (wszystko cytowane z kodu):

```python
MAX_TOKENS = {
    # 6 tematow: tytul, pytanie, ZLAMANE PRZEKONANIE, skad sie bierze, oceny
    "scout": _tokens_for(TOPIC_COUNT * 1400),
    "feasibility": _tokens_for(TOPIC_COUNT * 1100),
    "discovery": 32000,
    "classify": _tokens_for(
        CLASSIFY_MAX_EXCERPTS * CLASSIFY_MAX_EXCERPT_CHARS + 2000
    ),
    "synthesis": _tokens_for(
        CARD_MAX_CONFIRMED * (CARD_MAX_CLAIM_CHARS + CLASSIFY_MAX_EXCERPT_CHARS)
        + CARD_MAX_NUMBERS * 200
        + 4000
    ),
    "write": _tokens_for(MAX_WORDS * 7) + 6000,
    "review": 48000,
    ...
}
```

Przy `TOPIC_COUNT = 6`, `CLASSIFY_MAX_EXCERPTS = 12`, `CLASSIFY_MAX_EXCERPT_CHARS = 700`, `CARD_MAX_CONFIRMED = 8`, `CARD_MAX_CLAIM_CHARS = 240`, `CARD_MAX_NUMBERS = 8`, `MAX_WORDS = 1200` daje to: `scout` 3600, `feasibility` 3085, `classify` 4200, `synthesis` 5000, `write` 9600.

Cztery liczby mają historię awarii zapisaną obok:

- **`feasibility`, 1100 znaków na temat, nie 500.** „PODNIESIONE z 500 na 1100 znakow po realnym przebiegu: odkad temat niesie `broken_belief` i `why_they_believe_it`, odsiew ma wiecej do przeczytania i wiecej do powiedzenia, i ucielo mu odpowiedz w polowie JSON-a."
- **`discovery`, 32 000 na sztywno.** „Dyskoveria dostaje budżet z zapasem, bo DeepSeek liczy do niego tokeny rozumowania KAŻDEJ rundy wyszukiwania. Przy ciasnym budżecie kończył szukanie i nigdy nie tworzył bloku `message`: 26 wyszukiwań, status »completed«, zero tekstu."
- **`review`, 48 000.** „Recenzja rozlicza KAŻDE zdanie i jest najdroższa w tokenach wyjścia: DeepSeek dawał tu 19-22 tys. tokenów, a przy 28 764 ucięło go na żywo i straciliśmy główny sygnał jakości."
- **`THINKING_HEADROOM_TOKENS = 28000`.** „28 tys., nie 16. Zmierzone na realnych przebiegach: DeepSeek-pro rozumuje 16-19 tys. tokenow przy zadaniach WIELOELEMENTOWYCH (szesc tematow, szesc ocen, szesc celow) niezaleznie od objetosci samej tresci. Przy zapasie rownym 16 tys. margines wynosil 1,15-1,21x, czyli zaden."

Zapas doliczany jest **do wszystkiego**, tysiąc linii niżej w tym samym pliku:

```python
# Zapas na myślenie dostają WSZYSTKIE etapy, nie tylko Claude'owe: modele
# DeepSeek v4 też rozumują, a tokeny rozumowania liczą się do sufitu wyjścia.
# Odsiew ucięło na 2057 tokenach dokładnie z tego powodu.
MAX_TOKENS = {
    purpose: ceiling + THINKING_HEADROOM_TOKENS
    for purpose, ceiling in MAX_TOKENS.items()
}
```

**WADA — słownik `MAX_TOKENS` istnieje w dwóch wersjach pod tą samą nazwą, w odległości ~700 linii.** Czytający wersję pierwszą (linia 588) widzi `"restack": 3000`. Realny sufit wysłany do dostawcy to **31 000**. Efektywne sufity: `scout` 31 600, `feasibility` 31 085, `discovery` 60 000, `write` 37 600, `review` **76 000**. Dla dużych etapów zapas jest rozsądny; dla `restack`, gdzie kontrakt to jedno zdanie do 40 słów, zapas jest **dziesięciokrotnością kontraktu**. Sufit rzeczywiście nic nie kosztuje, dopóki nie zostanie zużyty — ale przestaje pełnić funkcję sufitu.

Sufit wchodzi też do terminu HTTP:

```python
MS_PER_OUTPUT_TOKEN = 16.08
TIMEOUT_MARGIN = 1.5
MAX_TIMEOUT_S = 300


def timeout_for(max_tokens: int) -> float:
    """Termin w sekundach, który realnie pokrywa podany sufit tokenów.

    Ograniczony twardo: wyliczenie z sufitu dawało 965 sekund, a przy
    wyszukiwaniu razy trzy — 48 minut na JEDNO wywołanie. Jedno zawieszenie
    blokowałoby cały dzień, a `systemd` ubiłby przebieg po godzinie w połowie
    roboty. Lepiej stracić jedną notkę niż resztę dnia.
    """
    return min(round(max_tokens * MS_PER_OUTPUT_TOKEN / 1000 * TIMEOUT_MARGIN, 1),
               MAX_TIMEOUT_S)
```

Stała `16,08 ms/token` pochodzi z pomiaru: „mediana 16,08 ms na token wyjściowy (19 rozliczonych przebiegów, R² 0,98)". Uzasadnienie istnienia funkcji: „Poprzedni agent ustawił 60 s przy suficie 4096 tokenów, co jest arytmetycznie niemożliwe (65,9 s potrzebne)."

**WADA — obietnica funkcji jest złamana przez jej własny clamp.** Docstring mówi „termin, który realnie pokrywa podany sufit". Dla `review` (76 000 tokenów) wyliczenie daje 1833 s, a `min()` obcina to do **300 s**. Termin pokrywa więc 12 400 tokenów z 76 000, czyli 16% sufitu. To jest świadomy wybór („lepiej stracić jedną notkę niż resztę dnia"), ale nazwa i docstring nadal twierdzą co innego, a próg, poniżej którego obietnica jeszcze obowiązuje (12 437 tokenów), nie jest nigdzie nazwany. Wszystkie etapy poza `restack`-owym rzędem wielkości są dziś ponad tym progiem.

`_preflight` wymaga sufitu dla każdego etapu i ma jedną furtkę:

```python
    if purpose not in config.MAX_TOKENS and purpose not in config.BEZ_TOKENOW:
        raise PreflightFailed(f"brak sufitu tokenów dla etapu {purpose!r}")
```

`BEZ_TOKENOW = {"obraz"}`, bo generator obrazu nie ma sufitu tokenów, a wpisanie tam liczby byłoby „zmyśloną wartością w pliku, który ma być jedynym źródłem prawdy".

---

### 7. Wyłącznik, limit na przebieg, dzienny sufit

Wszystkie trzy siedzą w jednej funkcji, wołanej **przed** każdym płatnym wywołaniem — także przed generowaniem obrazu:

```python
def _preflight(purpose: str, conn: sqlite3.Connection, run_id: int | None) -> None:
    """Warunki, które decydują, czy wywołanie może się w ogóle udać.

    Sprawdzane ZANIM pójdą pieniądze. Jedno zaniedbanie tej zasady kosztowało
    starego agenta 0,85 USD na eksperymencie niemożliwym od pierwszej sekundy.
    """
    if config.KILL_SWITCH:
        raise PreflightFailed("KILL_SWITCH=true — wywołania wstrzymane")

    model = config.MODEL_FOR[purpose]
    if model == config.CLAUDE and not config.ANTHROPIC_API_KEY:
        raise PreflightFailed("brak ANTHROPIC_API_KEY w .env")
    if model == config.DEEPSEEK and not config.DEEPSEEK_API_KEY:
        raise PreflightFailed("brak DEEPSEEK_API_KEY w .env")
    if model == config.IMAGE_MODEL and not config.OPENAI_API_KEY:
        raise PreflightFailed("brak OPENAI_API_KEY w .env")

    if purpose not in config.MAX_TOKENS and purpose not in config.BEZ_TOKENOW:
        raise PreflightFailed(f"brak sufitu tokenów dla etapu {purpose!r}")

    # Sufit na jeden przebieg obowiązuje ZAWSZE, także w trybie bez limitu.
    if run_id is not None:
        row = conn.execute(
            "SELECT COALESCE(SUM(cost_usd), 0) AS s FROM calls WHERE run_id = ?",
            (run_id,),
        ).fetchone()
        if float(row["s"]) >= config.RUN_LIMIT_USD:
            raise BudgetExceeded(
                f"przebieg wydał już ${float(row['s']):.4f} przy suficie "
                f"${config.RUN_LIMIT_USD} — zatrzymuję przed etapem {purpose!r}"
            )

    if config.NO_LIMIT:
        return

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    month = today[:7]
    spent_today = db.spent_usd(conn, today)
    spent_month = db.spent_usd(conn, month)
    if spent_today >= config.DAILY_LIMIT_USD:
        raise BudgetExceeded(
            f"limit dzienny wyczerpany: {spent_today:.4f} / {config.DAILY_LIMIT_USD} USD"
        )
    if spent_month >= config.MONTHLY_LIMIT_USD:
        raise BudgetExceeded(
            f"limit miesięczny wyczerpany: {spent_month:.4f} / {config.MONTHLY_LIMIT_USD} USD"
        )
```

Wartości:

```python
DAILY_LIMIT_USD = 5.00
MONTHLY_LIMIT_USD = 40.00

# Sufit na JEDEN przebieg. Działa ZAWSZE, także przy AGENT_V2_NO_LIMIT=1.
# „Bez limitu na budowę" miało znaczyć „nie blokuj eksperymentów", a nie
# „pozwól jednemu przebiegowi kosztować 2 USD". Przebieg 16 kosztował $1,92,
# z czego $1,33 poszło na 31 niepotrzebnych rund wyszukiwania.
PONOWIENIA = 2
PONOWIENIE_ODSTEP_S = 8

RUN_LIMIT_USD = 1.60
```

Sumowanie wydatków jest prefiksowe po ISO 8601 UTC, bez drugiej reprezentacji czasu:

```python
def spent_usd(conn: sqlite3.Connection, since_prefix: str) -> float:
    """Suma kosztów od znacznika czasu zaczynającego się danym prefiksem.

    `since_prefix` to `YYYY-MM-DD` dla doby albo `YYYY-MM` dla miesiąca — daty są
    zapisane w ISO 8601 UTC, więc porównanie prefiksem wystarczy i nie wymaga
    drugiej reprezentacji czasu w bazie.
    """
    row = conn.execute(
        "SELECT COALESCE(SUM(cost_usd), 0) AS total FROM calls WHERE at LIKE ?",
        (f"{since_prefix}%",),
    ).fetchone()
    return float(row["total"])
```

Tryby przełącza się zmiennymi środowiskowymi:

```python
DRY_RUN = _env("DRY_RUN", "false").lower() in {"1", "true", "yes"}
KILL_SWITCH = _env("KILL_SWITCH", "false").lower() in {"1", "true", "yes"}
NO_LIMIT = _env("AGENT_V2_NO_LIMIT", "0").lower() in {"1", "true", "yes"}
```

**WADA — wszystkie trzy limity są „zatrzymaj po", a nie „nigdy nie przekrocz".** Kontrola sprawdza wydatek **już zaksięgowany** i przepuszcza kolejne wywołanie w całości. Skoro pojedyncze wywołanie `write` na Fable kosztuje w produkcji do $0,65, a `discovery` do $0,55, przebieg stojący na $1,59 może legalnie skończyć na $2,24 — przy „suficie" $1,60. To samo w skali doby: przy stanie $4,99 rusza jeszcze pełny etap.

**WADA — `KILL_SWITCH` jest czytany raz, przy imporcie.** Ustawienie `KILL_SWITCH=true` w `.env` **nie zatrzymuje trwającego przebiegu** — proces ma już wartość w pamięci. Ponieważ jednostki są typu `oneshot`, wyłącznik zadziała dopiero przy następnym odpaleniu zegara, czyli w najgorszym razie za kilkanaście godzin. Prawdziwy „stop teraz" to `systemctl stop nia-agent.service`, i nigdzie to nie jest napisane.

**WADA — limit miesięczny jest ustawiony poniżej realnego spalania.** Sześć dni produkcji (15–20 sierpnia) to **$11,0037**, czyli $1,83 dziennie. Ekstrapolacja na pełny miesiąc daje ~$57, a `MONTHLY_LIMIT_USD` wynosi 40. Przy utrzymaniu tempa agent zamilkłby około 22. dnia miesiąca — i to nie z awarii, tylko z limitu, który nikt nie porównał z pomiarem. Bufor jest większy, niż wygląda, bo dwa najdroższe dni to praca rozwojowa, nie przebiegi z zegara (patrz sekcja 8) — ale liczba w `config.py` nie została zestawiona z niczym.

Ponowienia mają własną, ostrą definicję tego, co wolno powtórzyć:

```python
def przejsciowy(exc: BaseException) -> bool:
    """Czy ten błąd ma szansę minąć sam.

    PRZEJŚCIOWE — wywołanie się NIE ODBYŁO albo dostawca chwilowo nie dał rady:
    zerwana sieć, przekroczony czas, 429, 5xx. Ponowienie takiego wywołania nie
    jest decyzją, tylko dokończeniem tego, co miało się zdarzyć.

    TRWAŁE — wywołanie się odbyło i skończyło źle: odmowa dostawcy, zły klucz,
    przekroczony budżet, odpowiedź ucięta na suficie. Powtórzy się identycznie,
    więc ponawianie kosztuje i nie zmienia nic.
    """
    if isinstance(exc, (BudgetExceeded, PreflightFailed, Truncated)):
        return False
    if isinstance(exc, (httpx.TimeoutException, httpx.TransportError)):
        return True
    kod = getattr(exc, "status_code", None) or getattr(
        getattr(exc, "response", None), "status_code", None)
    if isinstance(kod, int):
        return kod == 429 or 500 <= kod < 600
    # Nierozpoznany błąd traktujemy jak trwały: lepiej nie zapłacić drugi raz
    # za coś, czego nie rozumiemy.
    return False
```

Klient Anthropic dostaje `max_retries=0` z komentarzem „ponowienie płatnego wywołania to decyzja, nie domyślka" — biblioteka nie ma prawa wydać pieniędzy bez wiedzy tej warstwy.

**Znana, przyjęta dziura.** Nagłówek `llm.py`: „Bez rezerwacji, bez rekoncyliacji, bez ponowień — świadomy kompromis: jeśli proces zginie w połowie wywołania, koszt tego wywołania nie trafi do logu. Limit dzienny ogranicza szkodę." W produkcji zginęły w ten sposób dwa przebiegi (24 i 28, oba `KeyboardInterrupt: przerwany sygnalem SIGTERM`), więc dziura jest realna, choć przy sekundowych oknach mało prawdopodobna.

---

### 8. Zmierzone koszty

Wszystko poniżej to `agent-v2.db` na produkcji, 591 wywołań, **suma $11,0037**.

#### Według etapu i modelu

| etap | model | wywołań | tok. wej. | tok. wyj. | cache | szukań | koszt | średnia |
|---|---|---|---|---|---|---|---|---|
| `write` | claude-fable-5 | 7 | 61 200 | 53 514 | 0 | 0 | **$3,2877** | $0,4697 |
| `discovery` | deepseek-v4-pro | 11 | 1 849 527 | 175 134 | 0 | 239 | **$2,8860** | $0,2624 |
| `comment` | deepseek-v4-pro | 189 | 146 045 | 368 212 | 69 120 | 0 | $1,1590 | $0,0061 |
| `factcheck` | deepseek-v4-flash | 113 | 2 671 909 | 284 614 | 0 | 538 | $0,8017 | $0,0071 |
| `curiosity` | deepseek-v4-flash | 12 | 2 301 323 | 242 059 | 0 | 165 | $0,6647 | $0,0554 |
| `note` | deepseek-v4-pro | 105 | 25 668 | 190 443 | 0 | 0 | $0,4012 | $0,0038 |
| `discovery` | deepseek-v4-flash | 3 | 539 332 | 51 617 | 0 | 64 | $0,3443 | $0,1148 |
| `review` | deepseek-v4-pro | 6 | 20 990 | 126 341 | 640 | 0 | $0,3104 | $0,0517 |
| `classify` | deepseek-v4-flash | 71 | 253 751 | 173 676 | 2 560 | 0 | $0,2677 | $0,0038 |
| `synthesis` | deepseek-v4-pro | 7 | 26 488 | 67 031 | 0 | 0 | $0,1756 | $0,0251 |
| `note` | **claude-opus-5** | 3 | 9 479 | 4 053 | 0 | 0 | $0,1487 | **$0,0496** |
| `cele` | deepseek-v4-flash | 24 | 24 241 | 208 250 | 2 048 | 0 | $0,1358 | $0,0057 |
| `scout` | deepseek-v4-pro | 7 | 4 907 | 48 013 | 0 | 0 | $0,1277 | $0,0183 |
| `obraz` | gpt-image-1.5 | 3 | — | — | — | — | $0,1200 | $0,0400 |
| `reply` | deepseek-v4-pro | 15 | 75 110 | 7 091 | 0 | 9 | $0,0741 | $0,0049 |
| `feasibility` | deepseek-v4-flash | 7 | 5 307 | 85 431 | 1 024 | 0 | $0,0677 | $0,0097 |
| `restack` | deepseek-v4-pro | 3 | 558 | 4 208 | 2 304 | 0 | $0,0150 | $0,0050 |
| `warto_pisac` | deepseek-v4-pro | 1 | 2 055 | 3 946 | 1 152 | 0 | $0,0099 | $0,0099 |
| `grafika` | deepseek-v4-flash | 4 | 7 896 | 4 735 | 0 | 0 | $0,0065 | $0,0016 |

Według dostawcy: **deepseek-v4-pro $5,1588** (344 wywołania), **claude-fable-5 $3,2877** (7), **deepseek-v4-flash $2,2885** (234), **claude-opus-5 $0,1487** (3), **gpt-image-1.5 $0,1200** (3).

Trzy rzeczy widać od razu:

1. **Siedem wywołań pisarza to 30% całego rachunku.** Fable kosztuje $10/$50 za milion i pisze ~7,6 tys. tokenów wyjścia na artykuł. Zapisana w `config.py` decyzja z 19 sierpnia — notki z Fable na Opusa, artykuł zostaje na Fable — jest tego bezpośrednią konsekwencją: „Razem z zejsciem na jeden wariant: $42,05 -> $6,07 miesiecznie za notki."
2. **Dyskoveria to drugie 29%, i płaci za wejście, nie za wyjście.** 1,85 mln tokenów wejścia przy 175 tys. wyjścia, bo każda runda wyszukiwania przesyła całą rozmowę od nowa. Zmierzone w komentarzu: „31 rund → 7 organizacji, 6 pierwotnych, $1,33 (bez limitu, przeciek); 6 rund → 1 organizacja, 0 pierwotnych, $0,53 (za mało). Koszt krańcowy ~$0,09 za rundę." Stąd `DISCOVERY_MAX_SEARCHES = 8` i twarde `max_uses` w narzędziu.
3. **Notka na Opusie kosztuje 13× tyle, co notka na DeepSeeku-pro** ($0,0496 wobec $0,0038). Trzy sztuki, wszystkie po 19 sierpnia — to jest cena decyzji podjętej po dwóch ślepych testach.

#### Koszt artykułu

Sześć przebiegów, które wyprodukowały artykuł:

| przebieg | artykuł | wywołań | koszt |
|---|---|---|---|
| 14 | Example Article Nine | 4 | $0,4164 |
| 16 | The Clock You Start Yourself | 15 | **$0,9622** |
| 17 | The Gas You Didn't Buy | 9 | $0,7397 |
| 19 | Example Article Eleven Is a Local Calculation… | 13 | $0,6667 |
| 20 | Example Article Twenty-One | 10 | $0,7796 |
| 25 | The Number on the Bottom of the Bottle… | 15 | $0,8264 |

**Średnia $0,7318, min $0,4164, max $0,9622.** Sufit `RUN_LIMIT_USD = 1,60` daje więc ~2× zapasu nad najdroższym realnym artykułem.

Pełny rozkład przebiegu 25 (najbardziej kompletnego, z grafiką) pokazuje, gdzie idą pieniądze:

| etap | model | wej. | wyj. | cache | szukań | koszt |
|---|---|---|---|---|---|---|
| `scout` | pro | 1 590 | 8 800 | 0 | 0 | $0,0185 |
| `feasibility` | flash | 295 | 19 906 | 1 024 | 0 | $0,0134 |
| `discovery` | pro | 219 151 | 21 215 | 0 | 26 | $0,1866 |
| `classify` ×7 | flash | 17 313 | 21 290 | 2 560 | 0 | $0,0185 |
| `synthesis` | pro | 6 603 | 11 108 | 0 | 0 | $0,0264 |
| `warto_pisac` | pro | 2 055 | 3 946 | 1 152 | 0 | $0,0099 |
| **`write`** | **fable** | 10 160 | 8 141 | 0 | 0 | **$0,5087** |
| `review` | pro | 3 719 | 20 301 | 640 | 0 | $0,0431 |
| `grafika` | flash | 2 147 | 1 419 | 0 | 0 | $0,0014 |

`write` to **61,6% tego przebiegu**. Wszystko przed pisarzem — wybór tematu, odsiew, znalezienie i przeczytanie dziesięciu źródeł, karta dowodowa, bramka ciekawości — kosztuje razem $0,2733.

#### Koszt dnia

Przebiegi `--dzien` (notki, komentarze, odpowiedzi, restacki), bez artykułu:

| przebieg | wywołań | koszt |
|---|---|---|
| 4 | 43 | $0,1246 |
| 5 | 59 | $0,1890 |
| 7 | 18 | $0,1158 |
| 8 | 31 | $0,2527 |
| 9 | 48 | $0,5547 |
| 10 | 43 | $0,3303 |
| 15 | 22 | $0,2099 |
| 26 | 24 | $0,2532 |
| 27 | 28 | $0,1809 |

**Mediana $0,2099, średnia $0,2457.** Przy trzech przebiegach dziennie z zegara daje to ~$0,74/dobę na aktywność społecznościową plus ~$0,73 za tygodniowy artykuł — czyli około **$25/miesiąc** przy obecnej konfiguracji.

Rozkład jednego pełnego dnia (przebieg 27, 28 wywołań): `comment` 18 × $0,1248, `factcheck` 6 × $0,0331, `cele` 2 × $0,0135, `restack` 2 × $0,0095. Sprawdzanie faktów pod komentarzami to jedna trzecia liczby wywołań komentarzy — każdy komentarz jest weryfikowany osobno.

#### Koszt kalendarzowy

| doba (UTC) | wywołań | koszt |
|---|---|---|
| 2026-08-15 | 21 | $0,0858 |
| 2026-08-16 | 201 | $0,9180 |
| 2026-08-17 | 122 | $1,1377 |
| 2026-08-18 | 99 | **$4,1799** |
| 2026-08-19 | 115 | **$4,3277** |
| 2026-08-20 | 33 | $0,3546 |

18 i 19 sierpnia to dni rozwojowe: sześć uruchomień ścieżki artykułowej, test A/B dyskoverii (przebieg 21, $1,3628) i porównanie pisarzy (przebieg 23, $0,9281). Oba dni zmieściły się pod `DAILY_LIMIT_USD = 5,00`, ale 19 sierpnia zabrakło **67 centów** do limitu.

**WADA — alarm kosztowy nie zadziałał w dniu, w którym powinien.** `alarm.koszt()` bije przy `wydane > DAILY_LIMIT_USD * 0.9`, czyli przy $4,50. 19 sierpnia zamknął się na $4,3277 — 17 centów pod progiem. Zegar alarmu chodzi raz na dobę o 07:00 UTC, więc i tak zmierzyłby dobę już zamkniętą. `alarmy.json` na produkcji zawiera **jeden klucz**: `{"kontrola-zawieszone": "2026-08-20T07:05:58.780645+00:00"}` — żaden alarm kosztowy, sesyjny ani dyskowy nigdy nie poszedł.

**Straty policzalne, których nie widać w tabeli etapów:**

- Przebieg 12: `FAILED` na etapie `fetch`, **$0,5898 zapłacone**, powód `ModuleNotFoundError: No module named 'trafilatura'`. Potok przeszedł wybór tematu, odsiew i dyskoverię, po czym przewrócił się na brakującej bibliotece serwera.
- Przebieg 13: `FAILED` na `write`, **$0,3855 zapłacone**, powód `StyleError: korpus stylu nie zgadza się z przypiętym hashem`.
- ~**$1,12** nadpłaty za wywołania DeepSeeka w godzinach szczytowych (sekcja 5).

Razem **~$2,10 z $11,00 (19%)** poszło na coś, co nie wyprodukowało tekstu.

---

### 9. Operacje

#### Maszyna

VPS Ubuntu, 6 rdzeni, 11 GB RAM, dysk 96 GB (6,4 GB zajęte, **7%**), uptime 5 dni. Python **3.14.4** w `.venv`. Katalog: `/home/ubuntu/nia-substack-bot`, gałąź `main`, drzewo czyste.

#### Zegary systemd

Trzy zegary, wszystkie `enabled`. Wszystkie jednostki leżą w repozytorium w `agent-v2/systemd/` i są kopiowane do `/etc/systemd/system/` przez `wdroz.sh`.

**`nia-agent.timer`** — dzień agenta, trzy razy na dobę:

```ini
OnCalendar=*-*-* 11:20:00
OnCalendar=*-*-* 19:20:00
OnCalendar=*-*-* 23:40:00
Persistent=true
RandomizedDelaySec=1500
```

Uzasadnienie godzin stoi w samej jednostce: „Badanie na 9 641 notkach: najgorsze okno tygodnia to 8:00-12:00 ET… Nasz przebieg o 15:00 UTC to bylo dokladnie 11:00 ET, czyli srodek najgorszego okna." Rozrzut 1500 s (25 min) daje realne okna 11:20–11:45, 19:20–19:45 i 23:40–00:05 UTC — po czasie nowojorskim (UTC-4) odpowiednio 07:20–07:45, 15:20–15:45 i 19:40–20:05. Żadne z nich nie wpada w `GODZINY_SZCZYTU_UTC`, czyli harmonogram jest jednocześnie strategią redakcyjną i strategią cenową.

**`nia-agent.service`**:

```ini
[Service]
Type=oneshot
User=ubuntu
WorkingDirectory=/home/ubuntu/nia-substack-bot
Environment=AGENT_V2_SERVER=1
Environment=PYTHONUNBUFFERED=1
MemoryMax=3G
ExecStart=/home/ubuntu/nia-substack-bot/.venv/bin/python agent-v2/run.py --dzien --wyslij
TimeoutStartSec=9000
```

Z komentarzy w pliku: `MemoryMax=3G`, bo „Chromium potrafi rosnac przy dlugich przebiegach, a OOM zabija agenta bez sladu w logu". `TimeoutStartSec=9000` (2,5 h), bo „przebieg trwa okolo godziny: same przerwy miedzy dzialaniami to ~42 minuty, bo agent czeka po ludzku (10-25 min po notce)". Brak `Restart=` jest jawną decyzją: „Automatyczny restart po bledzie oznaczalby ponawianie platnych wywolan bez nadzoru — a to najprostsza droga do rachunku, ktorego nikt nie zamowil."

**Ten sufit został właśnie trafiony.** Przebieg 28 wystartował 2026-08-20 o 11:38:58 i skończył o 14:08:57 — **dokładnie 2 h 29 min 59 s**, z `KeyboardInterrupt: przerwany sygnalem SIGTERM`. Ślad z `journalctl` pokazuje, gdzie zginął:

```
File "…/agent-v2/run.py", line 398, in notki
    stages.odczekaj("notka")
File "…/agent-v2/stages.py", line 599, in odczekaj
    time.sleep(ile)
File "…/agent-v2/run.py", line 621, in podnies
    raise KeyboardInterrupt(f"przerwany sygnalem {signal.Signals(numer).name}")
```

**WADA.** Agent został ubity przez systemd w środku ludzkiej przerwy między notkami, tracąc $0,1737 i resztę dnia. Sufit 2,5 h był liczony na przebieg „około godziny" z „~42 min przerw", ale nic nie pilnuje, żeby suma losowanych przerw (10–25 min po każdej notce, pięć notek dziennie) zmieściła się pod nim. Przy pechowych losowaniach przerwy same zjadają ponad dwie godziny. Kod nie wie, ile ma czasu.

**`nia-artykul.timer`** — artykuł tygodniowy:

```ini
# WTOREK 14:00 UTC = 10:00 rano u czytelnikow w Nowym Jorku.
OnCalendar=Tue *-*-* 14:00:00
Persistent=true
RandomizedDelaySec=900
```

Komentarz zamyka temat świadomie: „Research o godzinach wysylki newsletterow (MailerLite, 2,1 mln kampanii): szczyt otwarc miedzy 8 a 11 rano czasu ODBIORCY, a roznica miedzy dniami tygodnia to okolo JEDEN punkt procentowy… Wybieramy sensowna pore i przestajemy ja optymalizowac."

**`nia-artykul.service`** różni się od dziennego jednym: `ExecStart=… run.py --wyslij` (bez `--dzien`), `TimeoutStartSec=5400` (1,5 h), `MemoryMax=3G`.

**`nia-alarm.timer` / `nia-alarm.service`** — kontrola raz na dobę:

```ini
OnCalendar=*-*-* 07:00:00
Persistent=true
RandomizedDelaySec=600
```
```ini
ExecStart=/home/ubuntu/nia-substack-bot/.venv/bin/python agent-v2/alarm.py
TimeoutStartSec=600
```

`Persistent=true` we wszystkich trzech zegarach oznacza, że przebieg opuszczony przez wyłączony serwer odpali się natychmiast po starcie.

**WADA — `nia-agent.service` ma sekcję `[Install]`.** Zawiera `WantedBy=multi-user.target`, mimo że jest to zadanie jednorazowe wyzwalane wyłącznie z zegara. Obecnie stan to `disabled`, więc nic złego się nie dzieje — ale `systemctl enable nia-agent.service` (naturalny odruch przy „włączaniu agenta") sprawi, że **płatny, publikujący przebieg wystartuje przy każdym starcie systemu**, obok zegara. Dwie pozostałe usługi są `static`, czyli zrobione poprawnie; ta jedna wyłamuje się z wzorca w kierunku ryzykownym.

Poza tym na serwerze stoi zaplecze przeglądarkowe: `nia-vnc.service` (Xvfb `:1` 1440×900 + fluxbox + `x11vnc -nopw -localhost -rfbport 5900`) i `nia-chrome.service` (Chrome na `DISPLAY=:1` z `--remote-debugging-port=9222`, otwarty na stronie logowania Substacka). Służą wyłącznie do ręcznego odnowienia sesji. `-nopw` jest bezpieczne tylko dzięki `-localhost` — dostęp wymaga tunelu SSH.

#### Zamek

Jeden przebieg naraz, blokada na poziomie systemu plików:

```python
def zajmij_zamek():
    """Nie pozwala dwóm przebiegom działać naraz.

    Na serwerze harmonogram odpali agenta o stałej godzinie niezależnie od tego,
    czy poprzedni przebieg się skończył. Dwa procesy naraz to dwa razy ten sam
    artykuł i dwa razy ta sama notka — a tego nie da się cofnąć. To nie jest
    kwestia „czy", tylko „kiedy", więc zamek jest przed pierwszym uruchomieniem
    z harmonogramu, nie po pierwszej wpadce.

    Zamek trzyma system plików, nie my: przy zabiciu procesu blokada znika sama,
    więc nie zostawia po sobie zakleszczenia, które trzeba by odblokowywać ręcznie.
    """
    sciezka = config.DATA_DIR / "agent.lock"
    sciezka.parent.mkdir(parents=True, exist_ok=True)
    uchwyt = open(sciezka, "w", encoding="utf-8")
    try:
        try:                      # Linux, czyli serwer
            import fcntl
            fcntl.flock(uchwyt, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except ImportError:       # Windows, czyli komputer właściciela
            import msvcrt
            msvcrt.locking(uchwyt.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        uchwyt.close()
        raise JuzDziala(
            f"Inny przebieg już działa (zamek: {sciezka}). Kończę bez zmian."
        ) from None
    uchwyt.write(f"{os.getpid()}\n")
    uchwyt.flush()
    return uchwyt
```

Uchwyt jest trzymany do końca procesu (`_zamek = zajmij_zamek()` w `run.py`). W chwili pisania `agent.lock` zawiera `250486` — PID przebiegu 28, ubitego przez systemd. Blokada zniknęła razem z procesem; **w pliku została nieaktualna liczba**, co jest bez znaczenia dla działania, ale mylące przy diagnozie: treść pliku nie mówi, czy zamek jest zajęty. Źródłem prawdy jest `flock`, nie zawartość — i `wdroz.sh` pyta poprawnie:

```bash
ZAMEK="agent-v2/data/agent.lock"
if [ -e "$ZAMEK" ] && ! flock -n "$ZAMEK" -c true 2>/dev/null; then
    echo "  PRZEBIEG TRWA (zamek zajety) — nie wdrazam, sprobuj po jego zakonczeniu"
    exit 1
fi
```

Osobne zabezpieczenie chroni przed publikacją z kopii testowej:

```python
ZNACZNIK_KOPII_TESTOWEJ = config.AGENT_DIR / "TO_JEST_KOPIA_TESTOWA"


def odmow_publikacji_z_kopii(wyslij: bool) -> None:
    if wyslij and ZNACZNIK_KOPII_TESTOWEJ.exists():
        raise SystemExit(
            "ODMOWA: to jest kopia testowa (%s), a --wyslij publikuje NA ZYWO. "
            ...
        )
```

#### Alarm

`alarm.py` robi dwie rzeczy: pilnuje sesji Substacka i uruchamia siedem kontroli zdrowia (siódma dodana 2026-08-20). Filozofia z nagłówka:

> Najgroźniejsza awaria nie polega na tym, że coś padnie — polega na tym, że WSZYSTKO ŚWIECI NA ZIELONO, a agent milczy od trzech dni albo publikuje bzdury.

Kontrole i progi:

| kontrola | co sprawdza | próg |
|---|---|---|
| `cisza()` | `MAX(started_at)` w `runs` | `CISZA_ALARMOWA_H = 26` |
| `zawieszone()` | przebiegi `RUNNING` starsze niż 3 h — **i zamyka je** jako `STALE` | 3 h |
| `dysk()` | `shutil.disk_usage(DATA_DIR)` | ostrzeżenie 80%, alarm 92% |
| `nadaktywnosc()` | wywołania `note`/`comment`/`reply` dzisiaj | `MAX_DZIALAN_DZIENNIE = 60` |
| `koszt()` | `db.spent_usd(dziś)` | 90% × $5,00 = $4,50 |
| `powtorki()` | powtórzone klucze w 30 ostatnich faktach | >20% |

Wyciszanie: jeden klucz = jeden rodzaj problemu, `CISZA_GODZIN = 24`. Uzasadnienie: „kanał, który dzwoni co godzinę, przestaje być czytany po dwóch dniach — a wtedy jest gorszy niż jego brak." Kanał to SMTP (Gmail), a hasło aplikacji jest oczyszczane ze spacji, bo „Google pokazuje haslo aplikacji w czterech grupach po cztery znaki i ludzie wklejaja je ze spacjami".

`wyslij()` nigdy nie rzuca wyjątkiem — „alarm, który wywala agenta, byłby gorszy od problemu, który zgłasza".

**WADA — `zawieszone()` pisze do bazy, którą może właśnie trzymać przebieg.** Kontrola woła `db.finish_run` (czyli `UPDATE` + `commit`) o 07:00–07:10 UTC. Przebiegi dzienne startują o 11:20/19:20/23:40 i mogą trwać 2,5 h, więc okno 23:40 + 2,5 h sięga 02:10 — kolizji dziś nie ma, ale margines wynosi niecałe pięć godzin i nikt go nie pilnuje. Baza jest w trybie `delete` (nie WAL), więc pisarz blokuje wszystkich; domyślny `busy_timeout` w `sqlite3` to 5 sekund, po których leci `database is locked`. Kontrola zdrowia, która pada na blokadzie, zgłasza „kontrola sama padla" i idzie dalej — czyli po cichu.

**WADA — kontrola `nadaktywnosc()` używa innej funkcji czasu niż reszta kodu.** `db.spent_usd` filtruje `at LIKE 'YYYY-MM-DD%'`, a `nadaktywnosc` — `date(at) = ?`. Obie działają na ISO UTC i dają ten sam wynik, ale są to dwie różne umowy o formacie kolumny w jednym projekcie. Ta pierwsza przestanie działać, jeśli ktokolwiek kiedyś zapisze czas ze strefą inną niż UTC; ta druga zniesie to bez szmeru. Sprzeczność jest ukryta.

Odrębne polecenie `python agent-v2/alarm.py przeglad [dni]` łączy dziennik z bazą i odpowiada na pytania, których monitoring nie zada: ile odpowiedzi przypada na jedno działanie (osobno komentarze, osobno notki — **nigdy sumowane z polubieniami**, i to jest w kodzie uzasadnione redakcyjnie), czy opłaca się komentować wcześnie (`KOMFORTOWO_KOMENTARZY = 25`), które hasła wyszukiwania przynoszą rozmowy.

#### Kopia subskrybentów

`kopia_subskrybentow.py` chroni jedyne aktywo nie do odtworzenia:

> Teksty, karty dowodowe, okladki i cala historia kosztow powstaja lokalnie i leza w gicie. Lista subskrybentow nie: zyje wylacznie u Substacka. Przy tempie 6-12 subskrypcji miesiecznie sto osob to okolo jedenastu miesiecy pracy systemu, a regulamin pozwala zamknac konto natychmiast i w wylacznej ocenie Substacka.

Dlaczego to nie chodzi samo, jest udokumentowane jako decyzja, nie brak:

> Szukalem endpointu i go nie znalazlem. `/api/v1/subscriber/csv` i dwa podobne zwracaja 404. `/api/v1/subscriptions/page_v2`, ktorego uzywa panel, oddaje NASZE SUBSKRYPCJE… Przestalem szukac swiadomie. Powtarzane sondowanie nieudokumentowanych adresow to dokladnie to, co regulamin Substacka nazywa scrapingiem, a tu probujemy konto ZABEZPIECZYC, nie narazic.

Procedura ręczna: Dashboard → Subscribers → Export → plik do `data/kopie/przychodzace/` → `python agent-v2/kopia_subskrybentow.py`. Skrypt sprawdza, czy to naprawdę CSV z kolumną `email` (a nie strona HTML z nieudanego eksportu), liczy wiersze, porównuje z poprzednią kopią i alarmuje przy spadku powyżej `ALARM_SPADEK = 20` procent. Retencja `ILE_KOPII = 30`.

**WADA — najpoważniejsza w całym rozdziale. Kopii nie było ani jednej (CZĘŚCIOWO NAPRAWIONE 2026-08-20: dodano kontrolę alarmową; sam eksport pozostaje krokiem ręcznym właściciela).** Katalog `~/nia-substack-bot/agent-v2/data/kopie/` **nie istnieje na serwerze**. Skrypt nigdy nie został uruchomiony. Jedyne aktywo opisane w kodzie jako niemożliwe do odtworzenia jest w stu procentach niezabezpieczone. Dodatkowo:

- Kopia jest **wyłącznie ręczna** i nie ma dla niej zegara systemd — a zegary są tym, co w tym projekcie zamienia zamiar w działanie. Trzy zegary pilnują treści i zdrowia; zero pilnuje jedynego nieodtwarzalnego aktywa.
- Nic o tym nie alarmuje. `alarm.sprawdz_wszystko()` ma sześć kontroli i żadna nie pyta „kiedy ostatnio robiono kopię listy". Kontrola ciszy zauważy milczącego agenta po 26 godzinach; brak kopii subskrybentów nie zostanie zauważony nigdy, aż do dnia, w którym będzie potrzebna.

Skrypt sam ostrzega o tym, co produkuje: „te pliki zawieraja cudze adresy e-mail. Katalog `data/` jest poza gitem i ma tam zostac."

#### Wdrożenie

`wdroz.sh` to `git pull` z siecią bezpieczeństwa. Kolejność: sprawdź zamek → `git fetch` → `merge --ff-only` → **sprawdź, czy nowa wersja wstaje** (import wszystkich modułów + asercje na kompletność konfiguracji) → **sprawdź, czy sesja Substacka nadal działa** (`browser.podlacz_sie` + `wlasciwe_konto`, timeout 180 s) → skopiuj jednostki systemd → `daemon-reload`. Przy każdej porażce: `git reset -q --hard "$POPRZEDNIA"`.

**WADA — wdrożenie nie instaluje zależności i nie uruchamia testów.** W skrypcie nie ma `pip install -r requirements.txt` ani `pytest`. To jest dokładnie ta dziura, przez którą na serwerze zabrakło `trafilatura`: przebieg 12 zapłacił **$0,5898** za wybór tematu, odsiew i dyskoverię, po czym padł na `import trafilatura` w środku etapu `fetch`. Komentarz w `requirements.txt` przyznaje to wprost: „BRAKOWALO GO na serwerze i wyszlo dopiero przy pierwszym prawdziwym uruchomieniu sciezki artykulu… Zaden test tego nie zlapal, bo wszystkie sprawdzaly moduly agenta, a nie ten jeden import w srodku funkcji." Kontrola „czy nowa wersja wstaje" importuje `config, db, llm, stages, browser, kanal, alarm, gates, style, run` — a `trafilatura` jest importowana leniwie, wewnątrz funkcji, więc ta kontrola jej nie dotknie. Poprawka do `requirements.txt` weszła; luka w `wdroz.sh` została.

---

### 10. Jak odtworzyć środowisko od zera

Poniższe odtwarza działającego agenta na czystym VPS-ie. Kolejność ma znaczenie.

**1. System i kod.**
```bash
sudo apt update && sudo apt install -y python3.14 python3.14-venv git
git clone <repo> ~/nia-substack-bot
cd ~/nia-substack-bot
python3.14 -m venv .venv
.venv/bin/pip install -r agent-v2/requirements.txt
.venv/bin/python -m playwright install chromium
.venv/bin/python -m playwright install-deps chromium     # tylko Linux
```

Przypięte wersje z `requirements.txt`: `anthropic==0.116.0`, `httpx==0.28.1`, `python-dotenv==1.2.2`, `playwright==1.62.0`, `trafilatura==2.2.0`, `pypdf==6.1.1`. Wersje są przypięte celowo — „serwer ma zachowywac sie tak samo jak ten komputer, a nie tak, jak akurat wypadnie w dniu instalacji". OpenAI nie ma pakietu: grafiki idą przez `urllib` ze standardowej biblioteki.

**2. Sekrety.** Plik `.env` w **katalogu głównym repozytorium** (na produkcji: 857 B, tryb `0600`). `config.py` czyta oba miejsca, agenta pierwsze:

```python
load_dotenv(ENV_PATH)
# Zapasowo .env z katalogu głównego repozytorium: właściciel dopisał klucz
# OpenAI tam, a agent szukał go tylko u siebie i widział "BRAK". Sekret ma leżeć
# w jednym miejscu, więc zamiast kopiować go w dwa pliki, czytamy oba. Bez
# `override` — plik agenta zawsze wygrywa.
load_dotenv(REPO_ROOT / ".env", override=False)
```

Wymagane klucze: `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, `OPENAI_API_KEY` (tylko grafiki), `ALARM_EMAIL_TO`, `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`. Opcjonalnie `DRY_RUN`, `KILL_SWITCH`, `AGENT_V2_NO_LIMIT`, `AGENT_V2_CHEAP`, `AGENT_V2_WRITER`, `AGENT_V2_SERVER`.

**WADA — `.env` na produkcji zawiera martwe klucze poprzedniego agenta**, w tym `ANTHROPIC_MODEL_FAST`, `ANTHROPIC_MODEL_QUALITY`, `PRICE_INPUT_USD_PER_MTOK`, `PRICE_OUTPUT_USD_PER_MTOK`, `PRICE_CACHE_READ_USD_PER_MTOK`, `PRICE_CACHE_WRITE_USD_PER_MTOK`, `PRICE_WEB_SEARCH_USD_PER_1K`. `config.py` **nie czyta żadnego z nich** — cennik żyje w `PRICING`. Są to więc ceny w dwóch miejscach, z których jedno jest niewidzialne, a drugie prawdziwe: dokładnie ten wzorzec, który nagłówek `config.py` nazywa główną chorobą poprzedniego agenta („22 pary liczb »stała w kodzie kontra zdanie w prompcie« i nikt ich nigdy nie porównał"). Do usunięcia.

**3. Dane.** Nic nie trzeba tworzyć. `data/` jest w `.gitignore`, a `db.connect()` zakłada katalog i schemat przy pierwszym otwarciu. Świeża baza od razu ma `cache_hit` w `SCHEMA`, więc `_dopisz_brakujace_kolumny` nie zrobi nic.

**4. Sesja Substacka — jedyny krok, którego nie da się zautomatyzować.** Na komputerze z ekranem: zaloguj się w Chrome, uruchom `python agent-v2/browser.py sesja`, skopiuj `data/storage-state.json` na serwer. Alternatywnie przez zdalny pulpit na serwerze (`nia-vnc` + `nia-chrome` przez tunel SSH na porcie 5900). **Nadaj `chmod 600`** — na produkcji jedna z dwóch kopii tego pliku miała `0644` do 2026-08-20 (poprawione).

**5. Zegary.**
```bash
sudo cp agent-v2/systemd/*.service agent-v2/systemd/*.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now nia-agent.timer nia-alarm.timer nia-artykul.timer
```
**Nie** `enable nia-agent.service` — patrz WADA w sekcji 9.

**6. Weryfikacja przed pierwszym płatnym uruchomieniem.** W tej kolejności:
```bash
DRY_RUN=true .venv/bin/python agent-v2/run.py --dzien        # łańcuch bez opłat
AGENT_V2_CHEAP=1 .venv/bin/python agent-v2/run.py            # hydraulika za grosze
.venv/bin/python agent-v2/alarm.py test                      # czy alarmy dochodzą
.venv/bin/python agent-v2/alarm.py                           # sesja + sześć kontroli
```
`CHEAP_MODE` jest wprost opisany jako narzędzie do testowania hydrauliki, nie jakości: „Przebieg kosztuje wtedy grosze zamiast ~1 USD. NIE służy do oceny jakości tekstu, bo produktem jest to, co napisze Opus."

**7. Kopia testowa.** Jeśli to nie jest produkcja, połóż obok `config.py` pusty plik `TO_JEST_KOPIA_TESTOWA`. Odbiera on prawo do `--wyslij` bezwarunkowo.

**8. Kopia subskrybentów.** Załóż `data/kopie/przychodzace/` i wykonaj pierwszy eksport z Substacka **tego samego dnia**, w którym stawiasz środowisko. To jedyna rzecz z tej listy, której odtworzenie od zera jest niemożliwe.

#### Co przeżywa odtworzenie, a co nie

| aktywo | odtwarzalne? | skąd |
|---|---|---|
| kod, konfiguracja, prompty, korpus stylu | **tak** | git |
| schemat bazy | **tak** | `db.SCHEMA` przy pierwszym połączeniu |
| pliki `.md` artykułów | **tak** | git repo właściciela / `data/articles/` |
| okładki `.png` | nie, ale odtwarzalne za $0,04/szt. | ponowne wygenerowanie |
| historia kosztów, źródeł, przebiegów | **nie** | tylko `agent-v2.db` — kopiuj plik |
| `zuzyte_fakty.json`, `dziennik.jsonl`, `promocja.json` | **nie** | tylko `data/` — bez nich agent zacznie się powtarzać i zgubi kolejkę promocji |
| `storage-state.json` | **nie** | wymaga interaktywnego logowania człowieka |
| **lista subskrybentów** | **nie** | wyłącznie ręczny eksport z Substacka |

Ostatnie dwa wiersze to jedyne miejsca, w których odtworzenie środowiska wymaga człowieka. Pierwszy z nich jest pilnowany przez zegar alarmowy i wysyła maile na 7 dni przed wygaśnięciem. Drugi nie jest pilnowany przez nic.
