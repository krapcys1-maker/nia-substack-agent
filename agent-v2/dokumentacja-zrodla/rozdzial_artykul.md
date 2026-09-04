### Ścieżka artykułu

Jeden przebieg `python agent-v2/run.py` bez `--dzien` robi dokładnie jedno: produkuje jeden artykuł. Cała ścieżka to czternaście kroków w `main()` (`agent-v2/run.py:645-1055`), z czego dziesięć ma nazwę etapu w krotce `STAGES` (`run.py:24-27`):

```python
STAGES = (
    "scout", "feasibility", "discovery", "fetch",
    "classify", "synthesis", "warto_pisac", "write", "review", "forma",
)
```

Cztery kroki końcowe — bramki, zapis, grafika, publikacja — nie mają nazwy etapu i nie da się na nich zatrzymać przez `--stop-after`.

---

#### Mapa etapów

| # | etap | funkcja | model (`MODEL_FOR`) | sufit tokenów | effort | co produkuje |
|---|------|---------|---------------------|---------------|--------|--------------|
| 1 | `scout` | `stages.scout` (`stages.py:2036`) | `deepseek-v4-pro` | 31 600 | `medium` (**martwy**) | 6 tematów + ranking |
| 2 | `feasibility` | `stages.feasibility` (`stages.py:1905`) + `pick_topic` (`:1929`) | `deepseek-v4-flash` | 31 085 | — | oceny + wybrany temat |
| 3 | `discovery` | `stages.discovery` (`stages.py:1835`) | `deepseek-v4-pro` + web_search | 60 000 | `medium` (**martwy**) | ≤10 adresów |
| 4 | `fetch` | `stages.fetch` (`stages.py:1695`) | brak (HTTP) | — | — | korpus tekstów |
| 5 | `classify` | `stages.classify` (`stages.py:1569`) | `deepseek-v4-flash`, N wywołań | 32 171 | — | fragmenty + liczby |
| 6 | `synthesis` | `stages.synthesis` (`stages.py:1518`) | `deepseek-v4-pro` | 32 948 | `high` (**martwy**) | karta dowodowa |
| 7 | `warto_pisac` | `stages.warto_pisac` (`stages.py:2429`) | `deepseek-v4-pro` | 34 000 | — | werdykt PISZ/DOLOZ/ODLOZ |
| 7b | (przy DOLOZ) | `stages.bibliotekarz` (`stages.py:2288`) | `deepseek-v4-pro` | 40 000 | — | mechanizmy z banku |
| 8 | `write` | `stages.write` (`stages.py:215`) | `claude-fable-5` | 37 600 | `high` (**działa**) | artykuł |
| 9 | `review` | `stages.review` (`stages.py:71`) | `deepseek-v4-pro` | 76 000 | `high` (**martwy**) | rozliczenie zdań |
| 10 | `forma` | `stages.ocen_forme` (`stages.py:90`) | `deepseek-v4-pro` | 52 000 | `high` (**martwy**) | cytaty o kształcie |
| 11 | bramki | `gates.deterministic_floors` (`gates.py:118`) | brak | — | — | lista uwag |
| 12 | zapis | `stages.save` (`stages.py:164`) | brak | — | — | `.md` + `.uwagi.md` + wiersz w `articles` |
| 13 | grafika | `stages.grafika` (`stages.py:457`) | `deepseek-v4-flash` + `gpt-image-1.5` | 32 000 | — | `.png` |
| 14 | publikacja | `browser.wystaw_artykul` (`browser.py:1495`) | brak | — | — | post na Substacku |

**WADA — `EFFORT` jest martwy wszędzie poza pisarzem.** `config.EFFORT` (`config.py:574-581`) ustawia głębokość myślenia dla sześciu etapów, ale `llm._call_claude` przekazuje ją tylko dla modeli Anthropic:

```python
    # `effort` istnieje na Opusie 5, Sonnecie 5 i Fable 5.
    if purpose in config.EFFORT and model in (config.CLAUDE, config.SONNET, config.FABLE):
        kwargs["output_config"] = {"effort": config.EFFORT[purpose]}
```

Pięć z sześciu wpisów (`scout`, `discovery`, `synthesis`, `review`, `forma`) dotyczy etapów jadących na DeepSeeku. Ścieżka `_call_deepseek` (chat/completions) nie wysyła pola rozumowania w ogóle, a `_call_deepseek_responses` wysyła sztywne `config.DEEPSEEK_EFFORT = "low"`. Efekt: `EFFORT["review"] = "high"` nie ma żadnego wpływu na cokolwiek, a plik sugeruje, że ma.

---

#### Rusztowanie wspólne dla wszystkich etapów

##### Zamek i odmowa publikacji z kopii

`main()` najpierw zakłada zamek plikowy (`run.py:86-116`, `data/agent.lock`, `fcntl` na Linuksie, `msvcrt` na Windowsie) — dwa przebiegi naraz to dwa artykuły. Potem, PO `parse_args` i PRZED pierwszym dotknięciem bazy, woła `odmow_publikacji_z_kopii(args.wyslij)` (`run.py:68`), które rzuca `SystemExit`, jeśli obok `config.py` leży plik `TO_JEST_KOPIA_TESTOWA` i podano `--wyslij`.

##### `cached()` — pamięć podręczna etapu

```python
def cached(stage: str, produce: Callable[[], Any], use_cache: bool) -> Any:
    path = CACHE_DIR / f"{stage}.json"
    if use_cache and path.exists():
        print(f"  [{stage}] z pamięci podręcznej — bez opłaty", flush=True)
        return json.loads(path.read_text(encoding="utf-8"))
    value = produce()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    return value
```

`CACHE_DIR = config.DATA_DIR / "cache"`. Zapis jest **bezwarunkowy** — każdy przebieg nadpisuje `cache/<etap>.json`, także bez `--use-cache`.

**WADA — cache nie jest kluczowany tematem.** Plik nazywa się `scout.json`, nie `scout-<run_id>.json`. `--use-cache` po tygodniu odda tematy sprzed tygodnia i wyprodukuje ten sam artykuł drugi raz, bez żadnego ostrzeżenia.

**WADA — `warto_pisac` jest w `STAGES`, ale nie przechodzi przez `cached()`.** Wszystkie pozostałe dziewięć etapów woła się przez `cached(stage, lambda: ..., args.use_cache)`. Etap 7 nie:

```python
            ocena = stages.warto_pisac(conn, run_id, card)
```

Czyli `--stop-after warto_pisac` działa, a `--use-cache` na tym etapie płaci za każdym razem.

##### `_prompt()` — wstrzykiwanie pól do promptu

```python
def _prompt(name: str, **fields: Any) -> str:
    text = (config.PROMPTS_DIR / name).read_text(encoding="utf-8")
    return text.format(**fields)
```

To `str.format`, więc **każdy literalny nawias klamrowy w prompcie musi być podwojony**. Dlatego wszystkie kontrakty JSON w `prompts/*.md` są zapisane jako `{{"topics": [...]}}` — to nie pomyłka, tylko wymóg tej jednej linijki.

##### `llm.call()` — jedyna droga do dostawcy

`llm.call(purpose, system, user, *, conn, run_id, web_search=False, collect_urls=None)` (`llm.py:400-...`) robi po kolei:

1. **`_preflight`** (`llm.py:41`) — sprawdza `KILL_SWITCH`, obecność klucza, obecność sufitu tokenów, sufit przebiegu, limit dzienny i miesięczny.
2. Pętla ponowień `for proba in range(1, config.PONOWIENIA + 2)` — `PONOWIENIA = 2`, odstęp `PONOWIENIE_ODSTEP_S = 8` s z podwajaniem (`8, 16`). Ponawiane są **tylko** błędy przejściowe wg `przejsciowy()` (`llm.py:349`): `httpx.TimeoutException`, `httpx.TransportError`, HTTP 429 i 5xx. `BudgetExceeded`, `PreflightFailed`, `Truncated` i wszystko nierozpoznane są trwałe.
3. `_cost` → `db.record_call` → `_log`.

Sufity pieniężne (`config.py:367-380`):

```python
DAILY_LIMIT_USD = 5.00
MONTHLY_LIMIT_USD = 40.00
PONOWIENIA = 2
PONOWIENIE_ODSTEP_S = 8
RUN_LIMIT_USD = 1.60
```

Sufit przebiegu jest sprawdzany zawsze, także przy `AGENT_V2_NO_LIMIT=1`; dzienny i miesięczny są pomijane przy `NO_LIMIT`.

##### Jak liczony jest koszt

```python
def _cost(model: str, tokens_in: int, tokens_out: int, web_searches: int,
          cache_hit: int = 0) -> tuple[float, bool]:
    if model.startswith("deepseek"):
        stawka = config.stawka_deepseek(model)
        price = {"in": stawka["in"], "out": stawka["out"],
                 "verified": config.PRICING[model]["verified"]}
    else:
        price = config.PRICING[model]
    usd = (tokens_in / 1_000_000 * price["in"]
           + tokens_out / 1_000_000 * price["out"]
           + cache_hit / 1_000_000 * price.get("cache", price["in"]))
    if model in (config.CLAUDE, config.SONNET):
        usd += web_searches / 1_000 * config.WEB_SEARCH_USD_PER_1K
    return round(usd, 6), bool(price["verified"])
```

Stawki (`config.py:263-281`), USD za milion tokenów:

| model | in | out | cache | verified |
|---|---|---|---|---|
| `claude-opus-5` | 5,00 | 25,00 | — | tak |
| `claude-sonnet-5` | 3,00 | 15,00 | — | tak |
| `claude-fable-5` | 10,00 | 50,00 | — | tak |
| `deepseek-v4-flash` | 0,22 | 0,66 | 0,007 | tak |
| `deepseek-v4-pro` | 0,66 | 1,98 | 0,022 | tak |

DeepSeek ma taryfę dobową (`stawka_deepseek`, `config.py:305`): od `2026-08-16T16:00:00+00:00` w godzinach `GODZINY_SZCZYTU_UTC = frozenset(range(1, 4)) | frozenset(range(6, 10))` mnożnik `MNOZNIK_SZCZYT = 2.0`, poza nimi `1.0`. Wyszukiwanie po stronie Anthropic to `WEB_SEARCH_USD_PER_1K = 10.00`; u DeepSeeka mieści się w tokenach i **nie jest doliczane**.

##### Jak liczone są sufity tokenów

Dwustopniowo. Najpierw kontrakt (`config.py:588-...`):

```python
def _tokens_for(chars: int) -> int:
    return int(chars / CHARS_PER_TOKEN) + JSON_OVERHEAD_TOKENS
```

`CHARS_PER_TOKEN = 3.5`, `JSON_OVERHEAD_TOKENS = 1200`. Potem, na końcu pliku (`config.py:1307-1310`), **cały słownik jest przeliczany**:

```python
MAX_TOKENS = {
    purpose: ceiling + THINKING_HEADROOM_TOKENS
    for purpose, ceiling in MAX_TOKENS.items()
}
```

`THINKING_HEADROOM_TOKENS = 28000`. To dlatego `review` ma realnie 76 000, a nie 48 000. Czytając samą pierwszą definicję dostaje się liczby o 28 tys. za małe — to jedna z pułapek tego pliku.

**WADA — `timeout_for()` jest martwe dla całej ścieżki artykułu.** `config.timeout_for` (`config.py:1330`) obiecuje termin pokrywający sufit tokenów: `max_tokens * 16.08 ms * 1.5`. Ale `MAX_TIMEOUT_S = 300`, a najmniejszy sufit na tej ścieżce to 31 085 tokenów → wyliczenie daje 750 s → obcięte do 300. **Każdy** etap artykułu dostaje ten sam termin 300 s (dyskoveria u DeepSeeka `× 3` = 900 s). Komentarz „Termin musi pokryć własny sufit tokenów" nie opisuje już niczego.

**WADA — `_preflight` sprawdza klucze tylko dla trzech z sześciu modeli.**

```python
    if model == config.CLAUDE and not config.ANTHROPIC_API_KEY:
        raise PreflightFailed("brak ANTHROPIC_API_KEY w .env")
    if model == config.DEEPSEEK and not config.DEEPSEEK_API_KEY:
        raise PreflightFailed("brak DEEPSEEK_API_KEY w .env")
```

`config.DEEPSEEK` to `"deepseek-v4-flash"`. Etapy jadące na `deepseek-v4-pro` (skaut, dyskoveria, synteza, warto_pisac, recenzja, forma, bibliotekarz) **nie mają sprawdzenia klucza**. Tak samo `write` na `claude-fable-5`. Brak klucza wychodzi dopiero jako błąd dostawcy w środku etapu, czyli dokładnie tam, gdzie preflight miał go nie wpuścić.

---

#### Etap 1 — skaut tematów

**Funkcja:** `stages.scout` (`stages.py:2036`), wołana z `run.py:698`.
**Model:** `deepseek-v4-pro`, sufit **31 600**, effort `medium` (martwy).
**Wywołanie w `run.py`:**

```python
        stage = "scout"
        topics = cached(stage, lambda: stages.scout(conn, run_id, args.topics), args.use_cache)
```

##### Wejście

Dwa pola do promptu `skaut.md`:

- `{count}` — `args.topics`, domyślnie `6`;
- `{history_json}` — `recent_angles(conn)` (`stages.py:35`): `topic` z ostatnich `DIVERSITY_LOOKBACK = 5` wierszy `articles`, **plus** wszystkie tytuły z `wczytaj_promocje()` (czyli z tego, co naprawdę poszło w świat), plus dobitka z `prompts/historia_startowa.json`, jeśli wciąż jest mniej niż 5;
- `{pytania_czytelnikow}` — `pytania_dla_skauta()` (`stages.py:2605`), do 6 najświeższych pytań z `data/pytania_czytelnikow.json`, albo dosłownie `(zadne jeszcze nie wplynelo)`.

##### Kontrakt JSON (dosłownie z `prompts/skaut.md`)

```
{{"topics": [ ... ], "ranking": {{"most_written_about": [<3 indices>], "least_written_about": [<3 indices>], "richest": [<3 indices>], "thinnest": [<3 indices>]}}}}
```

Pola wspólne każdego tematu: `title`, `question`, `kind` (`"BROKEN_BELIEF"` albo `"SYSTEM_UNDER_TEST"`), `already_written`, `scale`, `precedents`, `threads`. Dla `BROKEN_BELIEF` dodatkowo `broken_belief` i `why_they_believe_it`; dla `SYSTEM_UNDER_TEST` — `the_moment`, `open_outcome`, `governing_record`.

`scale` to dokładnie jedno z: `ONE_PERSON`, `A_PLACE`, `AN_INDUSTRY`, `A_COUNTRY`.

`precedents` to lista obiektów:

```
{{"when": "<roughly when>", "what_happened": "<what people saw, in one sentence>", "what_changed": "<the rule or practice that came out of it, or 'nothing'>"}}
```

Prompt zawiera też wyraźny zakaz: *„Do not include scores"* — bo poprzedni agent dostawał w kółko 1.0.

##### Co robi kod po odpowiedzi

Kod **nie ufa deklaracjom modelu i przelicza wszystko sam**. Dla każdego tematu:

```python
        wiara = str(t.get("broken_belief") or "").strip()
        t["ma_przekonanie"] = len(wiara.split()) >= 5
        ...
        moment = str(t.get("the_moment") or "").strip()
        wynik = str(t.get("open_outcome") or "").strip()
        zapis = str(t.get("governing_record") or "").strip()
        t["ma_stawke"] = (len(moment.split()) >= 4 and len(wynik.split()) >= 4
                          and len(zapis.split()) >= 3)
        ...
        t["nosny"] = bool(t["ma_przekonanie"] or t["ma_stawke"])
        juz = t.get("already_written")
        t["ile_juz_napisano"] = len(juz) if isinstance(juz, list) else 0
        t["nasycony"] = t["ile_juz_napisano"] >= config.NASYCENIE_OD_ILU
        t["pozycja"] = 0
        w = t.get("threads")
        t["ile_watkow"] = len(w) if isinstance(w, list) else 0
        prec = t.get("precedents")
        prec = prec if isinstance(prec, list) else []
        t["precedensy"] = [p for p in prec if _precedens_ok(p)]
        t["ile_precedensow"] = len(t["precedensy"])
        t["zasieg"] = str(t.get("scale") or "").strip().upper()
        t["duzy_zasieg"] = t["zasieg"] in config.ZASIEGI_ARTYKULOWE
        t["na_artykul"] = (t["ile_precedensow"] >= config.PRECEDENSOW_NA_ARTYKUL
                           and t["duzy_zasieg"])
```

`_precedens_ok` (`stages.py:2771`) odsiewa wypełniacze — wymaga trzech rzeczy naraz:

```python
    if len(str(p.get("what_happened") or "").split()) < 5:
        return False
    if not re.search(r"\d{3,4}", str(p.get("when") or "")):
        return False              # „dawno temu" to nie jest data
    zmiana = str(p.get("what_changed") or "").strip()
    if len(zmiana.split()) < 3:
        return False
    return not re.match(r"^\W*(nothing|none|no\s|nic|brak)", zmiana, re.I)
```

Ranking modelu przekłada się na `pozycja`:

```python
    for i in indeksy("least_written_about"):
        topics[i]["pozycja"] += 2
        topics[i]["swiezy_wg_modelu"] = True
    for i in indeksy("most_written_about"):
        topics[i]["pozycja"] -= 2
        topics[i]["oklepany_wg_modelu"] = True
    for i in indeksy("richest"):
        topics[i]["pozycja"] += 1
    for i in indeksy("thinnest"):
        topics[i]["pozycja"] -= 1
```

Na koniec kolejność, **bez odrzucania czegokolwiek**:

```python
    topics.sort(key=lambda t: (not t["nosny"], not t["na_artykul"],
                               -t["pozycja"], t["nasycony"], -t["ile_watkow"]))
```

##### Progi

| stała | wartość | plik |
|---|---|---|
| `TOPIC_COUNT` | `6` | `config.py:387` |
| `DIVERSITY_LOOKBACK` | `5` | `config.py:388` |
| `NASYCENIE_OD_ILU` | `2` | `config.py:498` |
| `PRECEDENSOW_NA_ARTYKUL` | `2` | `config.py:516` |
| `ZASIEGI_ARTYKULOWE` | `("AN_INDUSTRY", "A_COUNTRY")` | `config.py:526` |

##### Do bazy / na dysk

Nic poza wierszem w `calls` i plikiem `data/cache/scout.json`.

**WADA — `--topics` nie rusza sufitu.** `MAX_TOKENS["scout"]` liczy się z `config.TOPIC_COUNT * 1400`, czyli sztywno z szóstki. `--topics 12` prosi model o dwa razy więcej przy tym samym suficie; ratuje to wyłącznie zapas 28 000 tokenów, nie arytmetyka.

---

#### Etap 2 — odsiew wykonalności i wybór tematu

**Funkcje:** `stages.feasibility` (`stages.py:1905`) i `stages.pick_topic` (`stages.py:1929`), wołane z `run.py:705-710`.
**Model:** `deepseek-v4-flash`, sufit **31 085**, bez effortu.

##### Wejście

Tylko `{topics_json}` — i to okrojone do trzech pól:

```python
    compact = [
        {"index": i, "title": t.get("title"), "question": t.get("question")}
        for i, t in enumerate(topics)
    ]
```

**Uwaga architektoniczna:** odsiew **nie widzi** `precedents`, `scale`, `threads`, `already_written` ani rankingu. Ocenia `depth` na podstawie samego tytułu i pytania, choć prompt każe mu wprost patrzeć na „the topic's own `threads` list". Model fizycznie tej listy nie dostaje.

##### Kontrakt JSON (dosłownie z `prompts/wykonalnosc.md`)

```
{{"assessments": [{{"index": <0-based index of the topic>, "feasible": true|false, "confidence": 0.0-1.0, "expected_primary_sources": <integer>, "depth": "RICH"|"SINGLE"|"THIN", "parallels": ["<other domain where the same mechanism appears>"], "note": "<one sentence: where the record most likely lives, or why it does not>"}}]}}
```

##### Co robi kod

`feasibility` tylko waliduje kształt:

```python
    assessments = data.get("assessments")
    if not isinstance(assessments, list) or not assessments:
        raise ValueError(f"odsiew nie zwrócił ocen: {text[:300]!r}")
    return assessments
```

Cała decyzja siedzi w `pick_topic`. Klucz sortowania — kolejność ma znaczenie i jest udokumentowana w docstringach:

```python
    def kolejnosc(a: dict[str, Any]):
        return (nosny(a),
                artykulowy(a),
                wlasny_ranking(a),
                swiezy(a),
                watki(a),
                waga.get(str(a.get("depth", "RICH")).upper(), 1),
                a.get("confidence", 0),
                a.get("expected_primary_sources", 0))

    ranked = sorted((a for a in assessments if a.get("feasible")),
                    key=kolejnosc, reverse=True)
```

`waga = {"RICH": 2, "SINGLE": 1, "THIN": 0}`. Czyli głębokość jest dopiero **szóstym** kryterium — przed nią idą nośność, artykułowość, własny ranking modelu, świeżość i liczba wątków, wszystkie wyliczone przez kod ze skauta.

Gdy nic nie przeszło:

```python
        wszystkie = sorted(assessments, key=kolejnosc, reverse=True)
        if not wszystkie:
            raise ValueError("odsiew nie oddal zadnej oceny")
        ranked = wszystkie[:1]
        print("  [odsiew] ZADEN temat nie przeszedl wykonalnosci — biore "
              "najlepszy z odrzuconych i zapisuje to w uwagach", flush=True)
        ranked[0]["mimo_odrzucenia"] = True
```

Zwraca `(topic, verdict)`. Z `verdict` używane jest dalej **tylko** `depth`.

**WADA — `artykulowy` jest zdefiniowana dwa razy w tej samej funkcji.** `stages.py:1969` i `stages.py:1993`. Ciała identyczne, więc skutków nie ma, ale pierwsza definicja jest martwa, a jej docstring różni się od drugiej — czytelnik dostaje dwie wersje uzasadnienia tego samego kryterium.

**WADA — flaga `mimo_odrzucenia` nigdzie nie trafia.** Komentarz mówi „zapisuje to w uwagach". Kod ustawia pole na słowniku `assessment`, który po wyjściu z `pick_topic` żyje jako `verdict` w `main()` — i z `verdict` czytany jest wyłącznie `depth`. Do `notes` w `save()` to nigdy nie dociera; właściciel się nie dowie.

---

#### Etap 3 — dyskoveria źródeł

**Funkcja:** `stages.discovery` (`stages.py:1835`), wołana z `run.py:724-729`.
**Model:** `deepseek-v4-pro` przez `/responses` z `web_search`, sufit **60 000**, reasoning effort `low` (z `DEEPSEEK_EFFORT`, nie z `EFFORT`).

##### Wejście

```python
    prompt = _prompt(
        "dyskoveria.md",
        question=question,
        max_results=config.DISCOVERY_MAX_RESULTS,
        max_searches=config.DISCOVERY_MAX_SEARCHES,
        min_primary=config.MIN_PRIMARY_SOURCES,
        # ... min_why, blocked_hosts ...
        # OSTATNIE_DOMENY JEST OBOWIAZKOWE. Prompt ma placeholder
        # {ostatnie_domeny}; pominiecie go daje KeyError w `str.format`
        # — czyli PO oplaceniu skauta i odsiewu.
        ostatnie_domeny=...,
        min_why=config.MIN_WHY_SOURCES,
        blocked_hosts=", ".join(list(config.BLOCKED_HOSTS) + martwe),
    )
```

`martwe` pochodzi z `hosty_ktore_nigdy_nie_dzialaly(conn)` (`stages.py:1794`) — hosty z ≥2 realnymi porażkami i zerem sukcesów w tabeli `sources`, przy czym porażki „za mało treści" i PDF-owe są z zapytania SQL **wykluczone** (bo to były braki naszej strony, nie blokady hosta).

##### Kontrakt JSON (dosłownie z `prompts/dyskoveria.md`)

```
{{"sources": [{{"url": "...", "title": "...", "publisher": "...", "class": "PRIMARY"|"SUPPORTING", "answers_why": true, "has_numbers": true, "note": "..."}}]}}
```

##### Co robi kod

Najważniejsza obrona całego potoku — sprawdzenie, czy model **naprawdę szukał**:

```python
    real_urls: list[str] = []
    text = llm.call(
        "discovery", DISCOVERY_SYSTEM, prompt,
        conn=conn, run_id=run_id, web_search=True, collect_urls=real_urls,
    )
    data = llm.parse_json(text)
    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError(f"dyskoveria nie zwróciła źródeł: {text[:300]!r}")

    if not real_urls:
        raise ValueError(
            "dyskoveria nie wykonała ani jednego wyszukiwania — zwrócone adresy "
            "pochodzą z pamięci modelu, nie z sieci"
        )
    real_hosts = {_host(u) for u in real_urls}
    kept: list[dict[str, Any]] = []
    for source in sources:
        url = source.get("url", "")
        host = _host(url)
        if not url.startswith("http"):
            continue
        if host in config.BLOCKED_HOSTS or any(host.endswith(b) for b in config.BLOCKED_HOSTS):
            print(f"  [dyskoveria] pomijam {host} — host blokuje automaty", flush=True)
            continue
        if real_hosts and host not in real_hosts:
            print(f"  [dyskoveria] pomijam {url} — spoza wyników wyszukiwania", flush=True)
            continue
        source["host"] = host
        kept.append(source)
```

`real_urls` wypełnia `llm.call` przez `collect_urls` — z bloków `web_search_tool_result` (Anthropic) albo z rekurencyjnego przejścia po `output` (DeepSeek, z obcięciem `#ws_call_id=`).

Zauważ: filtr działa na poziomie **hosta**, nie adresu. Model może więc podać nieistniejący `.../foo/bar` pod domeną, którą wyszukiwarka zwróciła, i przejdzie.

##### Progi

| stała | wartość |
|---|---|
| `DISCOVERY_MAX_RESULTS` | `10` |
| `DISCOVERY_MAX_SEARCHES` | `8` |
| `MIN_PRIMARY_SOURCES` | `2` |
| `MIN_WHY_SOURCES` | `2` |
| `BLOCKED_HOSTS` | `federalregister.gov, regulations.gov, congress.gov, ecfr.gov, sciencedirect.com, tandfonline.com, academia.edu, researchgate.net` |

##### Do bazy

Nic — zapis do `sources` robi dopiero etap 4.

**~~WADA — reguła różnorodności domen jest liczona i wyrzucana.~~ ZAMKNIĘTE 23 sierpnia.** Zapytanie SQL wykonywało się co przebieg, wynik szedł do `discovery` czwartym argumentem i **nie był czytany ani razu** — a docstring obiecywał „wejście do reguły różnorodności". Dziś domeny trafiają do promptu jako `ostatnie_domeny`, jako **preferencja, nie bramka**: twardy filtr hostów potrafiłby wyzerować listę źródeł i wywalić przebieg **po** opłaceniu researchu, bo przy `MIN_PRIMARY_SOURCES` ten sam regulator bywa jedynym miejscem, gdzie dokument leży. Sformułowanie zakazuje **nawyku**, nie nakazuje pozycji.

**~~WADA — `WEB_SEARCH_TOOL` nie zna Fable.~~ ZAMKNIĘTE 23 sierpnia.** Słownik miał tylko `CLAUDE` i `SONNET`, a `llm._call_claude` robił `config.WEB_SEARCH_TOOL[model]` — czyli `KeyError` w środku płatnej ścieżki dla każdego modelu Anthropic spoza słownika. Wpisu dla Fable nie było, choć to **na nim chodzi pisarz**. Dziś: `FABLE` dopisany, a odczyt idzie przez `config.narzedzie_wyszukiwania(model)`, które nieznanemu modelowi daje najnowszą znaną wersję narzędzia i **głośne ostrzeżenie raz na proces**. Źle zgadnięta wersja kończy się błędem od API, który widać; `KeyError` w połowie płatnej ścieżki widać dużo gorzej.

---

#### Etap 4 — pobranie stron

**Funkcja:** `stages.fetch` (`stages.py:1695`), wołana z `run.py:753`. Zero modeli, 0 USD.

##### Pętla główna

```python
            try:
                response = client.get(url)
                body = response.text
                if response.status_code >= 400:
                    reason = f"HTTP {response.status_code}"
                elif _to_pdf(response, url):
                    text = _tekst_z_pdf(response.content)
                    if not text:
                        reason = "PDF bez warstwy tekstowej (skan?)"
                else:
                    text = trafilatura.extract(body, include_comments=False) or ""
                    lowered = text.lower()
                    if any(phrase in lowered for phrase in config.REFUSAL_PHRASES):
                        reason = "host odmówił automatowi"
                    elif len(text) < config.FETCH_MIN_CHARS:
                        reason = f"za mało treści ({len(text)} znaków)"
            except Exception as exc:
                reason = f"{type(exc).__name__}"
```

Klient: `httpx.Client(timeout=config.FETCH_TIMEOUT_S, follow_redirects=True, headers={"User-Agent": config.FETCH_USER_AGENT})`.

- `FETCH_TIMEOUT_S = 30.0`
- `FETCH_MIN_CHARS = 400`
- `FETCH_USER_AGENT = "Mozilla/5.0 (compatible; YourPublication/1.0; +editorial research)"`
- `REFUSAL_PHRASES` (`config.py`) — 9 fraz: `"you have been blocked"`, `"access denied"`, `"are you a robot"`, `"verify you are human"`, `"enable javascript and cookies"`, `"unusual traffic"`, `"captcha"`, `"request has been flagged"`, `"programmatic access to these sites is limited"`.

Frazy odmowy sprawdzane są w **wydobytym tekście**, nie w surowym HTML — bo surowy HTML Substacka niesie `captcha_site_key` w formularzu logowania i kontrola na HTML-u uznawała za zablokowane strony, które nikogo nie blokują.

##### PDF

`_to_pdf` (`stages.py:2610`) pyta po kolei: nagłówek `content-type`, końcówkę adresu, pierwsze 5 bajtów `b"%PDF-"`. `_tekst_z_pdf` (`stages.py:2629`) czyta `pypdf`, maksymalnie **40 stron**, skleja i normalizuje puste wiersze. Skan bez warstwy tekstowej oddaje pustkę — OCR-u nie ma.

##### Drugie podejście w przeglądarce

Strony odrzucone **wyłącznie** z powodu „za mało treści" trafiają do `_dobierz_przegladarka` (`stages.py:1639`), który woła `browser.read_pages(...)`. Odmowy i 404 tam nie idą — to zasada projektu:

> NIE dotyczy odmow ani bledow 404. Host, ktory mowi automatowi „nie", dostaje „nie" — to zasada projektu i nie omijamy jej narzedziem.

##### Zapis do bazy

Każdy adres, udany czy nie, dostaje wiersz:

```python
            conn.execute(
                "INSERT INTO sources (run_id, at, url, domain, title, source_class,"
                " fetched_ok, fail_reason) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (run_id, db.now(), url, host, source.get("title"),
                 source.get("class"), int(ok), reason),
            )
```

Przeglądarka później **aktualizuje** ten wiersz (`UPDATE sources SET fetched_ok = ?, fail_reason = ?`), wpisując przy sukcesie `fail_reason = "odzyskane w przeglądarce"` mimo `fetched_ok = 1`.

##### Twarda ściana

```python
    if not fetched:
        raise ValueError("nie pobrano ani jednej strony — nie ma z czego pisać")
```

##### Druga runda dyskoverii

W `run.py:766-790`, jeśli korpus jest chudy:

```python
        if len(corpus) < config.MIN_ZRODEL_DO_PISANIA:
            print(f"\n-- za chudo ({len(corpus)} < {config.MIN_ZRODEL_DO_PISANIA})"
                  " — druga runda --", flush=True)
            try:
                juz_mamy = {s.get("host") or s.get("url", "") for s in corpus}
                dodatkowe = [
                    s for s in stages.discovery(conn, run_id, topic["question"],
                                                recent)
                    if (s.get("host") or s.get("url", "")) not in juz_mamy
                ]
                if dodatkowe:
                    dobrane = stages.fetch(conn, run_id, dodatkowe)
                    corpus = corpus + dobrane
```

`MIN_ZRODEL_DO_PISANIA = 4`. Dedup jest po **hoście**, więc drugi, inny dokument z tej samej domeny zostanie odrzucony jako duplikat. Awaria drugiej rundy jest łapana i przebieg leci dalej.

**WADA — `_dobierz_przegladarka` ma nieużywany parametr `juz_mamy`.** Sygnatura `(conn, run_id, brakujace, juz_mamy)`, wołanie `_dobierz_przegladarka(conn, run_id, do_przegladarki, fetched)`, w ciele ani jednego użycia. Sugeruje deduplikację, której nie ma.

---

#### Etap 5 — klasyfikacja i wyciąg fragmentów

**Funkcja:** `stages.classify` (`stages.py:1569`), wołana z `run.py:798-802`.
**Model:** `deepseek-v4-flash`, sufit **32 171**, **jedno wywołanie na źródło**.

##### Wejście na źródło

```python
        text = source.get("text", "")[: config.CLASSIFY_MAX_INPUT_CHARS]
        prompt = _prompt(
            "klasyfikacja.md",
            question=question,
            title=source.get("title", ""),
            publisher=source.get("publisher", ""),
            url=source.get("url", ""),
            text=text,
            max_excerpts=config.CLASSIFY_MAX_EXCERPTS,
            max_excerpt_chars=config.CLASSIFY_MAX_EXCERPT_CHARS,
        )
```

`CLASSIFY_MAX_INPUT_CHARS = 90_000`, `CLASSIFY_MAX_EXCERPTS = 12`, `CLASSIFY_MAX_EXCERPT_CHARS = 700`.

##### Kontrakt JSON (dosłownie z `prompts/klasyfikacja.md`)

```
{{"class": "PRIMARY"|"SUPPORTING"|"ODPAD", "relevance": 0.0, "excerpts": ["..."], "numbers": ["..."], "note": "<one sentence on what this document is>"}}
```

##### Co robi kod

Awaria pojedynczego źródła nie zabija etapu:

```python
        try:
            raw = llm.call("classify", CLASSIFY_SYSTEM, prompt, conn=conn, run_id=run_id)
            data = llm.parse_json(raw)
        except Exception as exc:
            print(f"  [klasyfikacja] {source.get('host')} — pominięty: {exc}", flush=True)
            continue
```

Odrzucenie tylko na dwóch warunkach — **`relevance` nie jest bramką**:

```python
        if klass == "ODPAD" or not excerpts:
            continue
        kept.append({
            "url": source.get("url"),
            "host": source.get("host"),
            "title": source.get("title"),
            "publisher": source.get("publisher"),
            "class": klass,
            "relevance": relevance,
            "excerpts": excerpts,
            "numbers": [n for n in data.get("numbers", []) if isinstance(n, str)],
            "note": data.get("note", ""),
        })

    kept.sort(key=lambda s: s["relevance"], reverse=True)
```

Powód jest zapisany w kodzie: próg trafności był bramką przez jeden przebieg i wyrzucił pracę o atmosferze modyfikowanej na szpinaku — siedem liczb, trafność 0,20 od modelu, a to dosłownie był temat artykułu.

Twarda ściana: `if not kept: raise ValueError("klasyfikacja odrzuciła wszystko — nie ma materiału")`. Niedobór źródeł pierwotnych jest tylko wypisywany.

##### Do bazy

Nic bezpośrednio — wynik jedzie dalej w pamięci i osiądzie w `articles.evidence` jako `unused_evidence`.

---

#### Etap 6 — synteza (karta dowodowa)

**Funkcja:** `stages.synthesis` (`stages.py:1518`), wołana z `run.py:818-823`.
**Model:** `deepseek-v4-pro`, sufit **32 948**, effort `high` (martwy).

Od tego miejsca w `run.py` obowiązuje reguła:

> Od tego miejsca artykuł MUSI powstać. Temat jest wybrany, research zrobiony i opłacony — żaden dalszy etap nie ma prawa zabić przebiegu.

Dlatego synteza jest w `try/except`:

```python
        try:
            card = cached(
                stage,
                lambda: stages.synthesis(conn, run_id, topic["question"], evidence),
                args.use_cache,
            )
        except Exception as exc:
            print(f"  [awaria] synteza padła ({exc}) — składam kartę z dowodów", flush=True)
            card = stages.fallback_card(topic["question"], evidence)
```

##### Wejście

`{question}` oraz `{evidence_json}` — okrojone do siedmiu pól na źródło:

```python
    payload = [
        {
            "url": s["url"], "publisher": s.get("publisher"), "title": s.get("title"),
            "class": s["class"], "excerpts": s["excerpts"], "numbers": s["numbers"],
        }
        for s in evidence
    ]
```

Plus siedem liczb kontraktowych: `min_confirmed=5`, `max_confirmed=8`, `min_numbers=3`, `max_numbers=8`, `max_uncertain=3`, `max_contradictions=3`, `max_claim_chars=240`.

##### Kontrakt JSON (dosłownie z `prompts/synteza.md`)

```
{{"working_thesis": "...", "main_mechanism": "...", "confirmed_claims": [{{"claim": "...", "evidence": "<verbatim excerpt>", "url": "..."}}], "citable_numbers": [{{"value": "...", "means": "...", "url": "..."}}], "parallel_mechanisms": [{{"domain": "...", "how_it_matches": "<one sentence: the same logic doing the same work>"}}], "uncertain_claims": ["..."], "contradictions": ["..."], "not_established": ["..."]}}
```

##### Co robi kod

Nadmiar jest **przycinany**, niedobór tylko zgłaszany:

```python
    if len(claims) < config.CARD_MIN_CONFIRMED:
        print(
            f"  [uwaga] karta ma {len(claims)} potwierdzonych twierdzeń, "
            f"spodziewane {config.CARD_MIN_CONFIRMED} — artykuł będzie chudszy",
            flush=True,
        )
    card["confirmed_claims"] = claims[: config.CARD_MAX_CONFIRMED]
    card["citable_numbers"] = numbers[: config.CARD_MAX_NUMBERS]
```

##### Karta awaryjna

`fallback_card` (`stages.py:1480`) składa kartę mechanicznie — pierwszy fragment z każdego źródła jako `claim`, wszystkie liczby, pusty `main_mechanism`, `_fallback: True` i szczere `not_established`:

```python
        "not_established": [
            "This card was assembled mechanically because the synthesis step "
            "failed; nothing here has been weighed against anything else."
        ],
```

**Uwaga:** `fallback_card` **nie zwraca `parallel_mechanisms`**. Pisarz dostaje wtedy kartę bez drugiego aktu, a prompt każe mu w takim wypadku pisać krótko — ale `dlugosc_dla(glebokosc)` nadal poda cel z odsiewu, np. 1075 słów.

---

#### Etap 7 — bramka ciekawości („czy jest tu luka")

**Funkcja:** `stages.warto_pisac` (`stages.py:2429`), wołana z `run.py:855`.
**Model:** `deepseek-v4-pro`, sufit **34 000**, bez effortu.

Bramka stoi **przed** pisarzem, bo po nim byłoby za późno. Nic nie blokuje — werdykt `DOLOZ` wysyła do banku, a nie zatrzymuje.

##### Wejście

Jedno pole, przycięte na sztywno:

```python
        _prompt("warto_pisac.md",
                card_json=json.dumps(card, ensure_ascii=False, indent=2)[:14000]),
```

##### Kontrakt JSON (dosłownie z `prompts/warto_pisac.md`)

```
{{"contradicted_belief": {{"present": true|false, "the_belief": "<the reader's wrong belief in their own words, or empty string>", "evidence": "<what in the card breaks it, or why nothing does>"}}, "named_decider": {{"present": true|false, "evidence": "<who, from the card, or why nobody is named>"}}, "felt_number": {{"present": true|false, "evidence": "<the figure and what it measures, or why the only figures are labels>"}}, "second_domain": {{"present": true|false, "evidence": "<the other field, or why the parallels stay inside one industry>"}}, "unsettled_outcome": {{"present": true|false, "the_question": "<the open question in the reader's own words, or empty string>", "the_situation": "<what the reader pictures, or empty string>", "governed_by": "<the written rule from the card that decides it, quoted or named — or why nothing in the card governs it>"}}, "what_would_rescue_it": "<one sentence naming the shape of the missing piece>", "one_line_verdict": "<one sentence on what this card actually has>"}}
```

##### Co robi kod — model obserwuje, kod rozstrzyga

Deklaracje bez treści są kasowane:

```python
    przekonanie = jest("contradicted_belief")
    tresc = str((o.get("contradicted_belief") or {}).get("the_belief", "")).strip()
    if przekonanie and len(tresc.split()) < 4:
        przekonanie = False
        o.setdefault("uwagi_kodu", []).append(
            "zaznaczono zlamane przekonanie, ale nie umiano go nazwac — nie liczy sie")
```

Druga droga (nierozstrzygnięty wynik) ma trzy sprawdzenia, w tym antywzorzec na zaprzeczenie:

```python
    if stawka and len(pytanie.split()) < 4:
        stawka = False
        ...
    if stawka and len(regula.split()) < 3:
        stawka = False
        ...
    elif stawka and _ZAPRZECZENIE.match(regula):
        stawka = False
```

`_ZAPRZECZENIE` (`stages.py:2414`) kotwiczy na **początku** zdania, żeby „the rules say nothing happens until the third round" nie wpadło w sieć:

```python
_ZAPRZECZENIE = re.compile(
    r"^\W*(nothing|nobody|none|no\s+(written|rule|record|document|procedure|law|"
    r"statute|one\b)|not\s+(recorded|written|governed|decided|established)|"
    r"there\s+is\s+no|there\s+are\s+no|neither|the\s+card\s+does\s+not|"
    r"nic\b|brak\b)",
    re.IGNORECASE,
)
```

Werdykt składa się z dwóch dróg:

```python
    droga_przekonania = przekonanie and ile_filarow >= MIN_FILAROW_POZA_PRZEKONANIEM
    droga_stawki = stawka and filary["named_decider"]
```

`MIN_FILAROW_POZA_PRZEKONANIEM = 2` (`stages.py:2426`), filary to `named_decider`, `felt_number`, `second_domain`.

| warunek | werdykt |
|---|---|
| obie drogi | `PISZ` |
| droga przekonania (przekonanie + ≥2 filary) | `PISZ` |
| droga stawki (stawka + nazwany decydent) | `PISZ` |
| samo przekonanie, <2 filary | `DOLOZ` |
| sama stawka bez decydenta | `DOLOZ` |
| ani jedno, ani drugie | `ODLOZ` |

##### Co robi `run.py` z werdyktem

```python
            if ocena["werdykt"] == "DOLOZ":
                print("   szukam pary w banku...", flush=True)
                bank = stages.bank_fragmentow(conn)
                if not bank:
                    print("   bank pusty — pisarz dostaje karte jak jest", flush=True)
                else:
                    grupy = stages.bibliotekarz(conn, run_id, bank).get("groups") or []
                    dolozone = [{"domain": ", ".join(g.get("dziedziny", [])),
                                 "mechanism": g.get("mechanism", ""), "z_banku": True}
                                for g in grupy[:2]]
                    if dolozone:
                        card.setdefault("parallel_mechanisms", []).extend(dolozone)
            card["ocena_ciekawosci"] = ocena
```

`bank_fragmentow` (`stages.py:2248`) czyta **wszystkie** wiersze `articles`, wyciąga `evidence.unused_evidence[*].excerpts`, odrzuca fragmenty krótsze niż 60 znaków. `bibliotekarz` (`stages.py:2288`) grupuje je po mechanizmie i kod weryfikuje grupy — model proponuje, kod sprawdza:

```python
        if len(czlonkowie) >= 2 and len(dziedziny) >= 2:
            przyjete.append(grupa)
```

**WADA — `ODLOZ` nic nie odkłada.** Werdykt nazywa się „ODLOZ", prompt mówi *„whether it must wait for company from the archive"*, a kod przy `ODLOZ` **nie robi nic** — nie sięga do banku, nie zapisuje tematu na później, nie ostrzega inaczej niż `print`. Artykuł jedzie do pisarza tak samo jak przy `PISZ`. Jedyne, co się dzieje, to wpis do `card["ocena_ciekawosci"]`.

**WADA — dołożone mechanizmy mają inny kształt niż reszta listy.** Synteza produkuje `{"domain": ..., "how_it_matches": ...}`, a bank dokłada `{"domain": ..., "mechanism": ..., "z_banku": True}`. Klucz `how_it_matches` znika, `mechanism` jest nowy. Pisarz dostaje w jednej liście dwa różne schematy i musi się domyślić.

**WADA — `WYMAGANE_ZLAMANE_PRZEKONANIE = True` (`stages.py:2424`) nie jest przez nic czytane.** Stała z komentarzem o „warunku koniecznym" nie występuje nigdzie poza własną definicją; logikę realizuje bezpośrednio `droga_przekonania`.

---

#### Etap 8 — pisarz

**Funkcja:** `stages.write` (`stages.py:215`), wołana z `run.py:900-903`.
**Model:** `claude-fable-5`, sufit **37 600**, effort **`high` — jedyny działający**.

##### Przygotowanie wejścia

```python
    dl = config.dlugosc_dla(glebokosc)
    ruch_nazwa, ruch_opis = config.losowy_ruch_koncowy()
    ile_paraleli, opis_paraleli = config.losowa_liczba_paraleli(glebokosc)
```

`glebokosc` bierze się z odsiewu: `glebokosc = str(verdict.get("depth") or "RICH").upper()`.

`DLUGOSC_WG_GLEBOKOSCI` (`config.py:452-458`):

```python
DLUGOSC_WG_GLEBOKOSCI = {
    "RICH":   {"cel": 1075, "min": 900, "max": 1250},
    "SINGLE": {"cel": 650,  "min": 480, "max": 820},
}
```

Losowanie zamknięcia — sześć równoprawnych ruchów (`RUCH_KONCOWY_MIX`, `config.py:1418`): `DO_SPRAWDZENIA`, `KTO_NA_TYM_STOI`, `POWROT_DO_ZACZEPU`, `GDZIE_KONCZY_SIE_ZAPIS`, `CENA_MECHANIZMU`, `GDYBY_INACZEJ`. Losowanie szerokości drugiego aktu (`ILE_PARALELI_WAGI = {1: 4, 2: 4, 3: 3}`, a poza RICH `{1: 5, 2: 3}`).

Powód losowania jest zapisany w kodzie i to jest sedno tego etapu:

> Dwa teksty napisane zaraz po poprzedniej poprawce mialy identyczny szkielet, bo prompt zamawial go doslownie: ten sam drogowskaz, trzy paralele, to samo zamkniecie. Powtarzalna forma zdradza maszyne tak samo jak powtarzana tresc.

##### Korpus stylu

```python
    import style

    examples = style.load_examples()
    positive, negative = style.load_profiles()
    rendered = "\n\n".join(
        f"### {e['function']}\n{e['text']}" for e in examples
    )
```

`style.load_examples()` (`style.py:53`) **odmawia**, jeśli SHA-256 korpusu nie zgadza się z `config.STYLE_CORPUS_SHA256`, a potem sprawdza jeszcze skrót każdego z pięciu przypiętych akapitów (`APPROVED_EXAMPLES`: `OPENING`/65, `CONCRETE_TO_SYSTEM`/45, `MECHANISM`/60, `COUNTERARGUMENT`/70, `ENDING`/76) i ich długość (150–900 znaków). Awaria stylu = awaria pisarza.

##### Pełne wejście do promptu

```python
    prompt = _prompt(
        "pisarz.md",
        language=config.ARTICLE_LANGUAGE,
        target_words=dl["cel"],
        min_words=dl["min"],
        max_words=dl["max"],
        style_examples=rendered,
        style_positive=positive,
        style_negative=negative,
        ruch_koncowy_nazwa=ruch_nazwa,
        ruch_koncowy=ruch_opis,
        ile_paraleli=opis_paraleli,
        card_json=json.dumps(card, ensure_ascii=False, indent=2),
    )
```

`ARTICLE_LANGUAGE = "English"`.

##### Kontrakt JSON (dosłownie z `prompts/pisarz.md`)

```
{{"title": "<the published headline>", "subtitle": "<one line>", "body": "<the article, plain text with blank lines between paragraphs>", "numbers_used": ["<each figure you wrote, exactly as written>"], "limits_paragraph_present": true|false}}
```

##### Co robi kod

```python
    text = llm.call("write", WRITER_SYSTEM, prompt, conn=conn, run_id=run_id)
    draft = llm.parse_json(text)
    if not draft.get("body"):
        raise ValueError("pisarz nie zwrócił treści")
    return draft
```

Jedno powtórzenie w `run.py`:

```python
        except Exception as exc:
            print(
                f"  [awaria] pisarz ({config.MODEL_FOR['write']}) padł: {exc}"
                f" — powtarzam na {config.CLAUDE}",
                flush=True,
            )
            config.MODEL_FOR["write"] = config.CLAUDE
            draft = stages.write(conn, run_id, card, glebokosc)
```

**WADA — `min_words`/`max_words` z kontraktu nie są przez nic sprawdzane.** `numbers_used` i `limits_paragraph_present` też nie. `limits_paragraph_present` jest wypisywane na ekran i nic więcej; `numbers_used` nie jest czytane **nigdzie** — kontrolę liczb robi `gates.numbers_outside_corpus` na własnym tokenizerze, ignorując deklarację modelu.

**WADA — `run.py` wypisuje inne liczby, niż dostał pisarz.**

```python
        print(
            f"   długość: {words} słów "
            f"(cel {config.TARGET_WORDS}, zakres {config.MIN_WORDS}-{config.MAX_WORDS})",
            flush=True,
        )
```

`TARGET_WORDS = 1075`, `MIN_WORDS = 950`, `MAX_WORDS = 1200` to stałe globalne. Pisarz dostał `dl["cel"]/dl["min"]/dl["max"]`. Dla tematu `SINGLE` prompt mówi „650 słów, 480-820", a log mówi „cel 1075, zakres 950-1200" — czyli poprawny artykuł 650-słowowy wygląda w logu na o połowę za krótki.

**WADA — `THIN` dostaje długość `RICH`.** `DLUGOSC_WG_GLEBOKOSCI` nie ma klucza `"THIN"`, a `dlugosc_dla` robi `.get(..., DLUGOSC_WG_GLEBOKOSCI["RICH"])`. Docstring `pick_topic` obiecuje wprost: *„siegamy po niego dopiero, gdy nie ma nic lepszego, i wtedy dostaje najkrotsza forme"*. Kod daje mu najdłuższą. To jest dokładnie ta wada, dla której skalowanie długości w ogóle powstało (artykuł o symbolu otwartego słoiczka: materiał na 300 słów, cel 1075).

**WADA — podmiana modelu przy awarii jest trwała i sprzeczna z konfiguracją.** `config.MODEL_FOR["write"] = config.CLAUDE` mutuje globalny słownik na resztę procesu. Komentarz uzasadnia to tym, że „Opus jest sprawdzonym pisarzem tego potoku", podczas gdy `config.py` od 2026-08-19 mówi, że produktem jest Fable, bo A/B dotyczył całego tekstu. Dodatkowo: jeśli pisarz padł na `BudgetExceeded` (sufit przebiegu 1,60 USD), powtórka padnie identycznie — `przejsciowy()` klasyfikuje ten błąd jako trwały, ale ta pętla jest poza `llm.py` i tego rozróżnienia nie robi.

---

#### Etap 9 — recenzja

**Funkcja:** `stages.review` (`stages.py:71`), wołana z `run.py:935-937`.
**Model:** `deepseek-v4-pro`, sufit **76 000** (najwyższy w systemie), effort `high` (martwy).

##### Wejście

```python
    prompt = _prompt(
        "recenzent.md",
        card_json=json.dumps(card, ensure_ascii=False, indent=2),
        body=draft["body"],
    )
```

Karta jest tu **pełna** — łącznie z `ocena_ciekawosci` dopisaną w etapie 7.

##### Kontrakt JSON (dosłownie z `prompts/recenzent.md`)

```
{{"sentences": [{{"text": "<the sentence, verbatim>", "class": "FACT"|"INFERENCE"|"PROSE", "supported": true|false, "why": "<only when class is FACT and supported is false: what is asserted and what the card lacks>"}}], "unsupported_facts": [{{"text": "...", "why": "..."}}], "summary": "<one sentence>"}}
```

##### Co robi kod — składanie z dwóch źródeł

Awaria nie blokuje:

```python
        except Exception as exc:
            print(f"  [awaria] recenzja padła ({exc}) — zapisuję bez niej", flush=True)
            report = {"sentences": [], "unsupported_facts": [],
                      "summary": f"recenzja niedostępna: {type(exc).__name__}"}
```

Najważniejszy fragment całego etapu — nie ufamy, że model poprawnie przepisze własny wynik w drugie miejsce:

```python
        unsupported = list(report.get("unsupported_facts", []) or [])
        znane = {str(x.get("text", ""))[:60] for x in unsupported}
        dopisane = 0
        for s in sentences:
            if s.get("class") != "FACT" or s.get("supported") is not False:
                continue
            if str(s.get("text", ""))[:60] in znane:
                continue
            unsupported.append({"text": s.get("text", ""),
                                "why": s.get("why", "")})
            dopisane += 1
```

Zwróć uwagę na `is not False` — `supported: null` albo brak pola **nie** liczy się jako niepokryte. Tylko jawne `false`.

Statystyka klas:

```python
        counts = {k: sum(1 for s in sentences if s.get("class") == k)
                  for k in ("FACT", "INFERENCE", "PROSE")}
```

##### Do bazy

`report["summary"]` trafia do `notes` jako wpis `{"gate": "RECENZJA", ...}`; każde niepokryte zdanie jako `{"gate": "FAKT_BEZ_POKRYCIA", "detail": ...}`.

---

#### Etap 10 — obserwacja formy

**Funkcja:** `stages.ocen_forme` (`stages.py:90`), wołana z `run.py:986-987`.
**Model:** `deepseek-v4-pro`, sufit **52 000**, effort `high` (martwy).

Osobne wywołanie od recenzji **celowo**: recenzent ma wprost chronić wnioskowanie przed zgłoszeniem, a ta bramka liczy m.in. zastrzeżenia — złączone tępiłyby się nawzajem.

##### Wejście

Tylko `{body}` — bez karty. Model nie ma jak sprawdzić faktów i nie ma tego robić.

##### Kontrakt JSON (dosłownie z `prompts/forma.md`)

```
{{"beliefs": [{{"belief": "<in your own words, one sentence>", "first_stated": "<verbatim sentence from the article>"}}], "support_only": [{{"quote": "<verbatim sentence>", "supports": <index into beliefs>}}], "hardest_fact": {{"quote": "<verbatim>", "why": "<one clause>"}}, "procedural_nearby": {{"quote": "<verbatim>"}}, "same_register": true|false, "reader_moment": {{"quote": "<verbatim>", "object": "<the thing the reader holds>"}}, "opening_claim": {{"quote": "<verbatim>", "already_familiar": true|false}}, "summary": "<one sentence>"}}
```

##### Co robi kod

W `run.py` — wyłącznie wypisanie na ekran, w tym pozycja momentu przyłapania:

```python
            moment = (forma.get("reader_moment") or {}).get("quote", "")
            gdzie = gates.pozycja_w_tekscie(moment, draft["body"])
```

Cała arytmetyka jest w `gates.uwagi_z_formy` (`gates.py:324`) — patrz etap 11. Awaria daje `forma = {}`.

---

#### Etap 11 — bramki (nic nie blokuje)

**Funkcje:** `gates.deterministic_floors` (`gates.py:118`) i `gates.uwagi_z_formy` (`gates.py:324`), wołane z `run.py:1005-1010`.
**Model:** żaden. 0 USD, milisekundy.

```python
        findings = gates.deterministic_floors(
            draft["body"], card, poprzednie=stages.poprzednie_teksty(pomin_tresc=draft["body"]))
        findings.extend(gates.uwagi_z_formy(forma, draft["body"]))
        for item in unsupported:
            findings.append({"gate": "FAKT_BEZ_POKRYCIA", "detail": item.get("text", "")})
```

##### Dwanaście podłóg deterministycznych

| bramka | co łapie | próg / mechanizm |
|---|---|---|
| `ZMYSLONE_PRZEZYCIE` | `FABRICATED_EXPERIENCE` — `I stood/visited/watched/…`, `last week, I`, `my wife/…` | każde trafienie |
| `NIEISTNIEJACE_BADANIE` | `VAGUE_STUDY` — `according to a recent study`, `studies have shown`, `experts say` | każde trafienie |
| `LICZBA_SPOZA_KORPUSU` | token cyfrowy z tekstu, którego nie ma w JSON-ie karty | każde trafienie |
| `FRAZA_Z_INSTRUKCJI` | ciąg 6 słów wspólny z `pisarz.md` | `dlugosc = 6` |
| `ZAPOWIEDZ_GRANIC` | akapit o granicach zaczynający się od zdania o sobie samym | `_META_GRANIC` w pierwszych 10 słowach |
| `WASKA_PODSTAWA` | liczba różnych hostów w `confirmed_claims` | `< 2` |
| `BUDZET_ZASTRZEZEN` | `my reading`, `I think`, `in my view`, `is a separate question` | `> config.BUDZET_ZASTRZEZEN` = `1` |
| `OBWIESZCZONA_POWSCIAGLIWOSC` | `I will not invent/speculate/guess…` | każde trafienie |
| `ZAKAZANE_OTWARCIE` | pierwsze zdanie typu `Turn over…`, `Next time you…`, `We all know…` | `ZAKAZANE_OTWARCIA.match` |
| `STATYSTYKA_BEZ_ZRODLA` | zdanie z `in one survey`/`reportedly`/`some estimates` **i** cyfrą | oba naraz |
| `NIEWIADOME_NA_KONCU` | akapit z ≥2 sygnałami niewiadomej w ostatniej trzeciej | `glebokosc >= 2/3` |
| `ODCISK_FORMY` | ten sam szkielet co poprzedni tekst | `prog = 5` z 6 cech |

`odcisk_formy` (`gates.py:257`) to sześć celowo zgrubnych cech:

```python
    return {
        "otwarcie": (akapity[0].split()[0].lower().strip('"“,.')
                     if akapity else ""),
        "liczba_w_otwarciu": bool(DIGITS.search(" ".join(slowa[:50]))),
        "pozycja_ty": kubelek(ty.start() / max(1, len(korpus)) if ty else None),
        "granice_na_koncu": bool(granice),
        "akapitow": len(akapity) // 3,
        "dlugosc": len(slowa) // 200,
    }
```

Materiał porównawczy to `stages.poprzednie_teksty` (`stages.py:111`) — `ILE_TEKSTOW_DO_POROWNANIA_FORMY = 4` ostatnich plików `.md` z `ARTICLES_DIR`, z pominięciem `.uwagi.md` i z pominięciem pliku, którego pierwsze 300 znaków treści zgadza się z ocenianym tekstem.

##### Cztery uwagi z obserwacji formy

| bramka | warunek |
|---|---|
| `GESTOSC_BEATOW` | `slow / len(beliefs) > config.SLOW_NA_BEAT` (`= 150`) |
| `BRAK_ESKALACJI` | `obserwacja.get("same_register") is True` |
| `CZYTELNIK_NIEPRZYLAPANY` | brak `reader_moment.quote` |
| `OTWARCIE_ZNANE` | `opening_claim.already_familiar` prawdziwe |

Świadoma decyzja zapisana w docstringu `uwagi_z_formy`: pozycja momentu przyłapania jest **liczona i wypisywana, ale nie jest wadą** — bo reguła nakazująca pozycję po dziesięciu tekstach sama staje się podpisem maszyny.

##### Werdykt

```python
def verdict(findings: list[dict[str, str]]) -> tuple[str, str | None]:
    return "SAVED", None
```

Zawsze. Uzasadnienie: *„Zablokowany artykuł to czysta strata 1,30 USD researchu i zero informacji w zamian."*

**WADA — nagłówek `gates.py` opisuje system, którego nie ma.** Pierwsza linia pliku brzmi „Cztery bramki, które blokują. Reszta to notatki." Bramek jest dwanaście deterministycznych plus cztery obserwacyjne, a **żadna nie blokuje** — `verdict()` zwraca `("SAVED", None)` bezwarunkowo. Ten sam nieaktualny opis siedzi też w `config.py` przy `# --- bramki jakości ---` („Te cztery są zgłaszane właścicielowi") oraz w komentarzu do kolumny `articles.blocked_by` („która z czterech bramek").

**WADA — „korpus" dla kontroli liczb jest szerszy, niż nazwa sugeruje.** `numbers_outside_corpus` porównuje z `json.dumps(card)`, a `card` w tym momencie zawiera już `ocena_ciekawosci` (wypowiedź modelu z etapu 7, z cytatami) i ewentualne `parallel_mechanisms` z banku. Każda liczba, którą przypadkiem zacytował sobie bramkarz ciekawości, staje się „obecna w materiale dowodowym".

**WADA — ta sama kontrola daje fałszywe alarmy na formatowaniu.** `DIGITS = re.compile(r"\d[\d.,]*")` traktuje `2,989,787` jako jeden token. Jeśli karta niesie `2989787`, a pisarz sformatował liczbę z przecinkami (co `config.py` chwali przy notkach jako zaletę Fable), bramka zgłosi liczbę spoza korpusu.

**WADA — kolejność dwóch linijek jest nośna i nieudokumentowana.** `card["unused_evidence"] = [...]` jest przypisywane **po** `deterministic_floors`. Gdyby ktoś przesunął tę linijkę wyżej (np. porządkując kod), do „korpusu" liczb weszłyby wszystkie fragmenty ze wszystkich odrzuconych źródeł i bramka `LICZBA_SPOZA_KORPUSU` przestałaby cokolwiek łapać. Nic w kodzie nie ostrzega przed tą zależnością.

**WADA — `frazy_z_instrukcji` czyta prompt z niewypełnionymi polami.** Funkcja otwiera `pisarz.md` surowy, więc porównuje tylko statyczny tekst instrukcji. Fragmenty korpusu stylu, które realnie trafiły do promptu przez `{style_examples}`, oraz opis ruchu końcowego z `{ruch_koncowy}` **nie są sprawdzane** — a to właśnie one są najbliżej „frazy do przepisania".

**WADA — `powtorzona_forma` liczy odcisk poprzedniego tekstu sześć razy.**

```python
        wspolne = sum(1 for k, v in moj.items() if odcisk_formy(inny).get(k) == v)
```

`odcisk_formy(inny)` jest w generatorze, więc wykonuje się raz na każdy z sześciu kluczy, dla każdego z czterech poprzednich tekstów — 24 przeliczenia zamiast 4. Wynik poprawny, praca zbędna.

---

#### Etap 12 — zapis

**Funkcja:** `stages.save` (`stages.py:164`), wołana z `run.py:1024`.

##### Wejście

```python
        notes = [*findings,
                 {"gate": "DLUGOSC", "detail": f"{len(draft['body'].split())} słów"},
                 {"gate": "RECENZJA", "detail": report.get("summary", "")}]
        card["unused_evidence"] = [
            {"url": s["url"], "publisher": s.get("publisher"), "excerpts": s["excerpts"],
             "numbers": s["numbers"]}
            for s in evidence
        ]
        path = stages.save(conn, run_id, topic, card, draft, status, blocked_by, notes)
```

##### Plik artykułu

```python
    slug = re.sub(r"[^a-z0-9]+", "-", (draft.get("title") or "artykul").lower()).strip("-")
    path = config.ARTICLES_DIR / f"{run_id:04d}-{slug[:60]}.md"
    urls = list(dict.fromkeys(
        c.get("url") for c in card.get("confirmed_claims", []) if c.get("url")
    ))
    path.write_text(
        f"# {draft.get('title', '')}\n\n*{draft.get('subtitle', '')}*\n\n"
        f"{draft['body']}\n\n---\n\n## Sources\n\n"
        + "\n".join(f"- [{_nazwa_zrodla(conn, url)}]({url})" for url in urls)
        + "\n",
        encoding="utf-8",
    )
```

`_nazwa_zrodla` (`stages.py:142`) podmienia goły adres na tytuł z tabeli `sources`, przycięty do 90 znaków, w formacie `Tytuł — host`; bez tytułu zostaje sam host.

##### Plik uwag

```python
    if status != "SAVED" or blocked_by or notes:
        path.with_suffix(".uwagi.md").write_text(
            f"# Uwagi wewnętrzne — {draft.get('title', '')}\n\n"
            f"Status: {status}" + (f" — {blocked_by}" if blocked_by else "") + "\n\n"
            + "\n".join(f"- {n}" for n in notes) + "\n",
            encoding="utf-8",
        )
```

Warunek jest zawsze prawdziwy — `notes` zawiera co najmniej `DLUGOSC` i `RECENZJA`.

##### Wiersz w bazie

```python
    conn.execute(
        "INSERT INTO articles (run_id, created_at, topic, title, body, evidence,"
        " status, blocked_by, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (run_id, db.now(), topic.get("title"), draft.get("title"), draft["body"],
         json.dumps(card, ensure_ascii=False), status, blocked_by,
         json.dumps(notes, ensure_ascii=False)),
    )
    conn.commit()
```

`articles.evidence` to **pełna karta** — z `unused_evidence`, `ocena_ciekawosci` i wszystkim, co dopisały etapy 7 i 11. To jest jedyne miejsce, z którego bank fragmentów cokolwiek czyta.

**WADA — sekcja `## Sources` pomija źródła, z których wzięto tylko liczby.** Lista buduje się wyłącznie z `confirmed_claims[*].url`. Źródło, które dało `citable_numbers`, ale nie weszło do potwierdzonych twierdzeń, nie pojawi się pod tekstem. Oświadczenie o AI obiecuje czytelnikowi źródła do sprawdzenia — a liczba jest tym, co czytelnik najczęściej chce sprawdzić.

**WADA — slug nie może być pusty, ale może być bezsensowny.** `re.sub(r"[^a-z0-9]+", "-", ...)` na tytule nieanglojęzycznym albo złożonym z samej interpunkcji da pustą nazwę po `.strip("-")`, czyli plik `0027-.md`. Nic tego nie sprawdza.

---

#### Etap 13 — grafika

**Funkcja:** `stages.grafika` (`stages.py:457`), wołana **zawsze** — bezpośrednio po `stages.save`, **przed** gałęzią `--wyslij`.

> **Poprawione 23 sierpnia.** Wywołanie stało wcześniej *wewnątrz* gałęzi
> `if args.wyslij:`, więc każdy przebieg bez publikacji zapisywał na dysk
> artykuł **bez okładki**, a cała ścieżka graficzna sprawdzała się wyłącznie
> na żywo, za prawdziwe pieniądze i przy prawdziwej publikacji. Nie było ani
> jednego przebiegu, w którym mogła zepsuć się bezpiecznie — i dlatego
> okładka zgubiona przez usterkę zapisu wywołań wyszła na jaw dopiero po
> fakcie. **Nie przenoś tego z powrotem do gałęzi publikacji.**
**Modele:** brief u `deepseek-v4-flash` (sufit **32 000**), obraz u `gpt-image-1.5`.

```python
IMAGE_MODEL = "gpt-image-1.5"
IMAGE_SIZE = "1536x1024"
IMAGE_QUALITY = "high"
IMAGE_PRICE_USD = 0.04   # cennik sierpien 2026, NIEPOTWIERDZONY na fakturze
IMAGE_TIMEOUT_S = 300
```

##### Wejście

```python
        prompt = _prompt(
            "grafika.md",
            title=draft.get("title", ""),
            body=draft.get("body", "")[:6000],
        )
```

##### Kontrakt JSON (dosłownie z `prompts/grafika.md`)

```
{{"subject": "<the object, in a few words>", "why_this_object": "<one sentence tying it to the article's mechanism>", "prompt": "<the full image prompt: your subject sentence first, then the style block below copied word for word>"}}
```

Blok stylu jest w prompcie **do przepisania dosłownie** — model wybiera przedmiot, nigdy sposób pokazania. Reguła: „A symbol is not an object" — przy artykule o oznaczeniu fotografuje się rzecz, która je nosi, nie sam piktogram.

##### Co robi kod

Cały etap jest w jednym `try` i **nigdy nie zabija artykułu**:

```python
    except Exception as exc:
        print(f"  [grafika] NIE POWSTAŁA ({type(exc).__name__}: {exc}) — "
              f"artykuł wychodzi bez nagłówka", flush=True)
        return {"blad": f"{type(exc).__name__}: {exc}"[:200]}
```

Zapis pliku:

```python
    cel = (sciezka_artykulu.with_suffix(".png") if sciezka_artykulu
           else config.ARTICLES_DIR / f"{run_id:04d}-naglowek.png")
    cel.parent.mkdir(parents=True, exist_ok=True)
    cel.write_bytes(dane)
    brief["plik"] = str(cel)
```

`llm.obraz` (`llm.py:...`) idzie przez `_preflight("obraz", ...)` — dlatego wyłącznik, sufit przebiegu i limit dzienny obejmują też obrazek. `BEZ_TOKENOW = {"obraz"}` zwalnia ten etap z wymogu posiadania sufitu tokenów.

##### Do bazy

Wiersz w `calls` z `purpose="obraz"`, `cost_usd = 0.04`, `price_verified = 0`, `note = "1536x1024"`.

**~~WADA — grafika nie powstaje bez `--wyslij`.~~ ZAMKNIĘTE 23 sierpnia.** Wywołanie siedziało wewnątrz `if args.wyslij:`, więc przebieg do szuflady — ten domyślny, o którym mówi cały docstring modułu — **nigdy** nie generował nagłówka, a właściciel oglądający `.md` nie widział okładki, na którą ma się wypowiedzieć przed publikacją. Gorsze było jednak co innego: **nie istniał ani jeden przebieg, w którym ścieżka graficzna mogła zepsuć się bezpiecznie**. Sprawdzała się wyłącznie na żywo, przy prawdziwej publikacji i za prawdziwe pieniądze — dlatego okładka zgubiona przez usterkę zapisu wywołań wyszła na jaw dopiero po fakcie. Dziś `stages.grafika` stoi przed gałęzią publikacji i nadal nie ma prawa zatrzymać artykułu.

---

#### Etap 14 — publikacja

```python
        if args.wyslij:
            import browser

        # ZAWSZE, PRZED galezia publikacji — patrz run.py:1134.
        stages.grafika(conn, run_id, draft, sciezka_artykulu=path)

        if args.wyslij:
            print("\n-- publikacja --", flush=True)
            wynik = browser.wystaw_artykul(path, wyslij=True)
            print(f">> {'OPUBLIKOWANY' if wynik.get('wyslane') else 'NIE POSZEDŁ'}"
                  f"{'  ' + str(wynik.get('blad')) if wynik.get('blad') else ''}",
                  flush=True)
```

`browser.wystaw_artykul` (`browser.py:1495`):

1. `naprawde_wyslac(wyslij, "artykul")` — druga, niezależna zgoda.
2. `rozbierz_artykul(path)` (`browser.py:1139`) — rozkłada `.md` na tytuł (pierwsza linia po `# `), podtytuł (pierwsza linia w `*…*`) i **HTML**, bo ProseMirror gubi linki przy wpisywaniu znak po znaku.
3. `sciezka_png` domyślnie `path.with_suffix(".png")`, jeśli istnieje — czyli dokładnie plik, który zapisała grafika.
4. Sprawdzenie, czy artykuł o tym tytule już nie jest opublikowany (`potwierdz_artykul`) — zabezpieczenie przed dublem.
5. Nowy szkic pod `https://{SUBSTACK_HANDLE}.substack.com/publish/post?type=newsletter` (`SUBSTACK_HANDLE = "your-handle"`), wypełnienie, `Kontynuuj/Continue/Weiter`.
6. `WYLACZ_WYKRYWANIE_AI = True` — klika przycisk „Wyłącz wykrywanie AI" dla tego posta.
7. Publikacja, `potwierdz_artykul` po 15 s, wpis do dziennika.
8. Po potwierdzeniu:

```python
                adres = potwierdz_adres_artykulu(page, artykul["tytul"])
                stages.zapisz_do_promocji(adres, artykul["tytul"],
                                          bez_znacznikow(artykul.get("html", ""))[:2000])
```

Adres bierze się **od Substacka**, nie zgaduje z tytułu — slug bywa skracany, a zgadnięty adres żył na przekierowaniu 302.

Wpis w `data/promocja.json` domyka pętlę: `recent_angles` (etap 1) czyta tę listę, żeby skaut nie zaproponował po raz drugi tematu, który już poszedł w świat.

---

#### Zamknięcie przebiegu

```python
    except Exception as exc:
        db.finish_run(conn, run_id, "FAILED", stage, f"{type(exc).__name__}: {exc}"[:500])
        print(f"\n!! stanęło na etapie {stage}: {type(exc).__name__}: {exc}", file=sys.stderr)
        traceback.print_exc()
        _summary(conn, run_id)
        return 1
    finally:
        conn.close()
```

`_done` zapisuje `DONE` z notatką `zatrzymany po etapie {stage}`, `_summary` wypisuje sumę z `calls`.

**Uwaga:** `stage` w chwili sukcesu ma wartość `"forma"` — ostatnią przypisaną. Przebieg zakończony pełną publikacją zapisuje się w `runs` jako „zatrzymany po etapie forma", co jest nieprawdą o czterech ostatnich krokach.

---

#### Co trafia do bazy i na dysk — zbiorczo

| miejsce | co | kiedy |
|---|---|---|
| `runs` | jeden wiersz: `started_at`, `status`, `stage`, `cost_usd`, `note` | start i koniec |
| `calls` | jeden wiersz na wywołanie: `provider`, `model`, `purpose`, `tokens_in/out`, `cache_hit`, `web_searches`, `cost_usd`, `price_verified`, `ok`, `note` | każde wywołanie, także nieudane (z zerami i treścią wyjątku) |
| `sources` | jeden wiersz na adres z dyskoverii: `url`, `domain`, `title`, `source_class`, `fetched_ok`, `fail_reason` | etap 4 |
| `articles` | jeden wiersz: `topic`, `title`, `body`, `evidence` (pełna karta JSON), `status`, `blocked_by`, `notes` | etap 12 |
| `data/cache/<etap>.json` | wynik etapu | każdy z 9 cache'owanych etapów |
| `data/articles/NNNN-slug.md` | gotowy do wklejenia artykuł + `## Sources` | etap 12 |
| `data/articles/NNNN-slug.uwagi.md` | status + wszystkie uwagi bramek | etap 12 |
| `data/articles/NNNN-slug.png` | nagłówek | etap 13, **każdy przebieg** |
| `data/promocja.json` | adres, tytuł, 2000 znaków tekstu | etap 14, po potwierdzeniu |
| `data/agent.lock` | PID | start |

Schemat bazy to cztery tabele bez migracji (`db.py:22-80`), zakładane przez `CREATE TABLE IF NOT EXISTS` przy każdym połączeniu, plus jedyny wyjątek — `_dopisz_brakujace_kolumny` dokładający `calls.cache_hit` do baz sprzed jej wprowadzenia.

---

#### Zbiorcza lista wad tej ścieżki

1. **`EFFORT` martwy dla 5 z 6 etapów** — działa tylko dla `write` (Fable). Reszta jedzie na DeepSeeku, który tego pola nie dostaje.
2. **`timeout_for()` martwe** — `MAX_TIMEOUT_S = 300` obcina wszystkie sufity; obietnica „termin pokrywa sufit tokenów" nie obowiązuje nigdzie na tej ścieżce.
3. **`_preflight` nie sprawdza kluczy dla `deepseek-v4-pro`, `claude-fable-5` ani `claude-sonnet-5`** — czyli dla ośmiu z jedenastu wywołań w przebiegu artykułu.
4. **Reguła różnorodności domen liczona i wyrzucana** — `recent_domains` jest nieużywanym parametrem `discovery`.
5. **`warto_pisac` poza `cached()`** mimo obecności w `STAGES` — `--use-cache` płaci za ten etap co raz.
6. **Cache etapów nie jest kluczowany tematem** — `--use-cache` po czasie odtworzy stary artykuł.
7. **`THIN` dostaje długość `RICH`** — brak klucza w `DLUGOSC_WG_GLEBOKOSCI`, wbrew docstringowi `pick_topic`.
8. **`run.py` wypisuje globalny zakres długości**, nie ten podany pisarzowi — log kłamie przy każdym artykule `SINGLE`.
9. **`ODLOZ` nic nie odkłada** — werdykt jest wyłącznie napisem.
10. **Dołożone z banku paralele mają inny kształt** (`mechanism` zamiast `how_it_matches`).
11. **`numbers_used` i `limits_paragraph_present` nie są przez nic czytane** — kontrakt pisarza ma dwa martwe pola.
12. **Kontrola liczb porównuje z całą kartą**, łącznie z `ocena_ciekawosci`, i myli się na formatowaniu tysięcy.
13. **Kolejność `unused_evidence` vs. bramki jest nośna i nieudokumentowana.**
14. **`frazy_z_instrukcji` nie widzi wstrzykniętych fragmentów stylu ani opisu ruchu końcowego.**
15. **`## Sources` pomija źródła wnoszące same liczby.**
16. ~~**Grafika nie powstaje bez `--wyslij`**~~ — **zamknięte 23 sierpnia**, okładka powstaje w każdym przebiegu.
17. **Podmiana pisarza na Opusa przy awarii jest trwała** i sprzeczna z bieżącą decyzją konfiguracyjną; przy `BudgetExceeded` powtórka jest gwarantowaną stratą.
18. **`artykulowy` zdefiniowana dwa razy w `pick_topic`**, z rozbieżnymi docstringami.
19. **`mimo_odrzucenia` nie dociera do uwag** mimo komentarza, że dociera.
20. **Nagłówki `gates.py`, `config.py` i komentarz `articles.blocked_by` mówią o „czterech bramkach, które blokują"** — bramek jest szesnaście i żadna nie blokuje.
21. **`WYMAGANE_ZLAMANE_PRZEKONANIE` nieużywane.**
22. **`_dobierz_przegladarka` ma nieużywany parametr `juz_mamy`.**
23. **`--topics` nie skaluje sufitu tokenów skauta.**
24. **`runs.stage` po udanej publikacji zapisuje `forma`** — cztery ostatnie kroki nie mają odzwierciedlenia w dzienniku.
25. **`WEB_SEARCH_TOOL` nie zna Fable** — `KeyError` czeka na pierwszą zmianę modelu dyskoverii.
