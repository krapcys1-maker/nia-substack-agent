
<!--KOD:db.record_call-->
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
```

<!--KOD:db.connect-->
```python
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
```

<!--KOD:db._dopisz_brakujace_kolumny-->
```python
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

<!--KOD:llm.call-->
```python
def call(
    purpose: str,
    system: str,
    user: str,
    *,
    conn: sqlite3.Connection,
    run_id: int | None = None,
    web_search: bool = False,
    collect_urls: list[str] | None = None,
) -> str:
    """Woła model właściwy dla etapu i zapisuje koszt. Zwraca tekst odpowiedzi.

    `collect_urls`, jeśli podane, zostanie wypełnione adresami, które realnie
    zwróciła wyszukiwarka — do sprawdzenia, czy model nie zmyślił URL-a.
    """
    _preflight(purpose, conn, run_id)
    model = config.MODEL_FOR[purpose]

    # DOSTAWCE ROZSTRZYGA `_dostawca`, TAK SAMO JAK KONTROLA KLUCZY.
    #
    # Stalo tu wlasne `"deepseek" if model.startswith("deepseek") else
    # "anthropic"` — czyli DRUGIE miejsce decydujace o tym samym, i o jednego
    # dostawce ubozsze. Dzis nie pekalo tylko dlatego, ze obrazy chodza osobna
    # funkcja (`llm.obraz`), wiec `gpt-image-1.5` nigdy tu nie trafia. Model
    # tekstowy OpenAI dopisany do `MODEL_FOR` poszedlby jednak do Anthropic
    # z jego identyfikatorem, a odpowiedz brzmialaby jak awaria dostawcy.
    #
    # `_dostawca` istnieje dokladnie po to, zeby te dwa miejsca sie nie
    # rozjechaly — i to jest zdanie z jego wlasnego docstringa.
    provider = _dostawca(model)
    if provider not in ("anthropic", "deepseek"):
        raise PreflightFailed(
            "etap %r chodzi na %s, a `call` nie ma sciezki dla dostawcy %r.\n"
            "Obrazy maja wlasna funkcje `llm.obraz`; model tekstowy nowego "
            "dostawcy wymaga galezi tutaj i wpisu w `_dostawca`."
            % (purpose, model, provider or "nieznany"))

    # STALA, KTORA WYGLADA JAK USTAWIENIE. Wpis w EFFORT czyta sie jak decyzja
    # o kosztach, a przy modelu spoza Claude nie robi NIC.
    #
    # Pierwsza wersja tego ostrzezenia stala w `_call_claude` i BYLA MARTWA:
    # do tamtej funkcji nie ma jak wejsc nic spoza Claude, bo `call` rozstrzyga
    # dostawce wyzej. Wykrywacz martwych obietnic sam byl martwa obietnica —
    # i przeszedl testy, bo test szukal napisu w pliku, a nie sprawdzal, czy
    # ten kod da sie w ogole wykonac. Tu, po ustaleniu modelu i przed
    # rozdzieleniem, widac oba przypadki.
    #
    # Raz na proces, nie przy kazdym wywolaniu: chodzi o to, zeby bylo wiadomo,
    # a nie zeby zalac log.
    if (purpose in config.EFFORT and provider != "anthropic"
            and purpose not in _EFFORT_BEZ_SKUTKU):
        _EFFORT_BEZ_SKUTKU.add(purpose)
        print(f"  [effort] {purpose}={config.EFFORT[purpose]} NIE MA SKUTKU"
              f" — etap chodzi na {model}, a to pokretlo dziala tylko na"
              f" modelach Claude (DeepSeek ma DEEPSEEK_EFFORT"
              f"={config.DEEPSEEK_EFFORT})", flush=True)

    if config.DRY_RUN:
        print(f"  [{purpose}] DRY_RUN — wywołanie pominięte", flush=True)
        return ""

    for proba in range(1, config.PONOWIENIA + 2):
        try:
            if provider == "anthropic":
                text, tin, tout, searches, urls = _call_claude(
                    purpose, system, user, web_search)
                cache_hit = 0
            elif web_search:
                text, tin, tout, searches, urls = _call_deepseek_responses(
                    purpose, system, user)
                cache_hit = 0
            else:
                text, tin, tout, searches, cache_hit = _call_deepseek(
                    purpose, system, user)
                urls = []
            if collect_urls is not None:
                collect_urls.extend(urls)
            break
        except Exception as exc:
            if przejsciowy(exc) and proba <= config.PONOWIENIA:
                czekaj = config.PONOWIENIE_ODSTEP_S * 2 ** (proba - 1)
                print(f"  [{purpose}] {type(exc).__name__} — przejściowy, "
                      f"ponawiam za {czekaj}s ({proba}/{config.PONOWIENIA})",
                      flush=True)
                time.sleep(czekaj)
                continue
            # Koszt nieudanego wywołania bywa nieznany. Zapisujemy "nie wiadomo"
            # zamiast zgadywać kwotę — zgadnięta kwota w zapisie finansowym jest
            # gorsza niż jej brak.
            db.record_call(
                conn=conn, run_id=run_id, provider=provider, model=model,
                purpose=purpose, tokens_in=0, tokens_out=0, web_searches=0,
                cost_usd=0.0, price_verified=0, ok=0,
                note=f"{type(exc).__name__}: {exc}"[:500],
            )
            raise

    trafienia = locals().get("cache_hit", 0) or 0
    usd, verified = _cost(model, tin, tout, searches, trafienia)
    db.record_call(
        conn=conn, run_id=run_id, provider=provider, model=model, purpose=purpose,
        tokens_in=tin, tokens_out=tout, cache_hit=trafienia,
        web_searches=searches, cost_usd=usd,
        price_verified=int(verified), ok=1, note=None,
    )
    _log(purpose, model, tin, tout, searches, usd, verified)
    return text
```

<!--KOD:llm._cost-->
```python
def _cost(model: str, tokens_in: int, tokens_out: int, web_searches: int,
          cache_hit: int = 0) -> tuple[float, bool]:
    # DeepSeek liczy od 2026-08-16 wg pory doby, wiec stawke bierzemy na moment
    # wywolania, a nie ze stalej. Roznica miedzy szczytem a reszta doby to
    # dwukrotnosc — na tyle duzo, ze usrednianie zafalszowaloby zapis.
    if model.startswith("deepseek"):
        stawka = config.stawka_deepseek(model)
        # KLUCZ `cache` TEZ, i to nie jest kosmetyka. Bez niego linijka nizej
        # robi `price.get("cache", price["in"])` i wycenia trafienia w cache
        # stawka WEJSCIOWA — czyli trzydziestokrotnie za drogo u pro ($0,66
        # zamiast $0,022).
        #
        # `stawka_deepseek` zwraca ten klucz swiadomie i ma przy nim komentarz
        # o tej samej pomylce. Poprawka zatrzymala sie jednak w polowie drogi:
        # funkcja zaczela go oddawac, a `_cost` nadal go nie przepisywal, wiec
        # nic sie nie zmienilo. Blad zglosilem jako naprawiony, a nie byl.
        price = {"in": stawka["in"], "out": stawka["out"],
                 "cache": stawka["cache"],
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
    #
    # PO DOSTAWCY, NIE PO DWOCH IDENTYFIKATORACH. Stalo tu
    # `model in (config.CLAUDE, config.SONNET)` — czyli dokladnie ten sam
    # ksztalt, ktory `_preflight` naprawil kilkadziesiat linii wyzej, pod
    # naglowkiem „KONTROLA PO DOSTAWCY, NIE PO IDENTYFIKATORZE MODELU".
    # Poprawka objela kontrole kluczy i zatrzymala sie przed wycena.
    #
    # Zdanie w komentarzu mowi „cennikiem Anthropic", a warunek wymienial dwa
    # modele z trzech: `FABLE` (claude-fable-5-1, etap `write`) wypadal. Dzis
    # zaden etap Anthropic nie wola z wyszukiwaniem, wiec galaz nie klamie —
    # ale wybor modelu jest POLEM KONFIGURACJI (`modele.*`). Konto, ktore
    # ustawi `discovery` na Claude, dostaje wyszukiwanie NIEDOLICZONE do
    # kosztu: zapis finansowy zanizony, a sufity dzienny i miesieczny licza
    # z tego zanizonego zapisu.
    if _dostawca(model) == "anthropic":
        usd += web_searches / 1_000 * config.WEB_SEARCH_USD_PER_1K
    return round(usd, 6), bool(price["verified"])
```

<!--KOD:llm._preflight-->
```python
def _preflight(purpose: str, conn: sqlite3.Connection, run_id: int | None) -> None:
    """Warunki, które decydują, czy wywołanie może się w ogóle udać.

    Sprawdzane ZANIM pójdą pieniądze. Jedno zaniedbanie tej zasady kosztowało
    starego agenta 0,85 USD na eksperymencie niemożliwym od pierwszej sekundy.
    """
    if config.KILL_SWITCH:
        raise PreflightFailed("KILL_SWITCH=true — wywołania wstrzymane")

    # ZAPORA PRZED PLATNYM WYWOLANIEM Z DARMOWEGO TESTU. Patrz
    # `config._w_darmowym_tescie`: `tests/conftest.py` dziala tylko pod
    # pytestem, a darmowe testy chodza petla po plikach, w ktorej conftest
    # nie wykonuje sie wcale. Test bez atrapy placil wiec prawdziwymi
    # pienedzmi, a jedynym sladem byl wiersz w `calls`.
    #
    # Stoi TU, a nie w atrapach: atrapa, ktorej ktos zapomnial podstawic,
    # nie moze byc tym, co pilnuje, czy ktos ja podstawil.
    # `DRY_RUN` WYJETY SPOD ZAPORY, i to nie jest ustepstwo: kilkanascie linii
    # nizej `call` konczy sie na `DRY_RUN` zwracajac pusty napis, ZANIM
    # dotknie sieci. Nie ma tam czego blokowac, a testy uzywaja tej sciezki,
    # zeby sprawdzic, co `call` WYPISUJE — inaczej ostrzezenia o martwych
    # ustawieniach nie dalyby sie zmierzyc inaczej niz szukaniem napisu w
    # zrodle, czyli tak, jak ten projekt WLASNIE przestal robic.
    if not config.WOLNO_WOLAC_MODEL and not config.DRY_RUN:
        raise PreflightFailed(
            "wywolanie modelu z darmowego testu (%s) — podstaw atrape pod "
            "`llm.call` albo przenies test do tests/platne/" % purpose)

    model = config.MODEL_FOR[purpose]

    # KONTROLA PO DOSTAWCY, NIE PO IDENTYFIKATORZE MODELU.
    #
    # Stalo tu `model == config.CLAUDE` i `model == config.DEEPSEEK`, czyli
    # porownanie z DWOMA konkretnymi napisami. Modeli jest piec:
    #   claude-opus-5      CLAUDE       — objety
    #   claude-fable-5-1   FABLE        — NIEOBJETY, a to caly artykul
    #   deepseek-v4-flash  DEEPSEEK     — objety
    #   deepseek-v4-pro    DEEPSEEK_PRO — NIEOBJETY, a to JEDENASCIE etapow:
    #                                     scout, discovery, synthesis, review,
    #                                     forma, note_tani, comment, reply,
    #                                     naprawa_komentarza, wybor,
    #                                     bibliotekarz, warto_pisac, restack
    #   gpt-image-1.5      IMAGE_MODEL  — objety
    #
    # Skutek zmierzony: przy pustych kluczach kontrola zatrzymywala 12 rol
    # z 26. Pozostale 14 szlo do sieci i wywracalo sie dopiero na odpowiedzi
    # HTTP, wiec komunikat mowil o transporcie zamiast o brakujacym kluczu.
    # Diagnoza „awaria dostawcy" przy dzialajacym `curiosity` kosztuje godzine
    # szukania nie tam, gdzie trzeba.
    #
    # Nowa wersja pyta o DOSTAWCE przez `_dostawca`, tak samo jak rozliczanie
    # stawek nizej — wiec dopisanie szostego modelu nie wymaga juz pamietania
    # o tym miejscu.
    _klucz = {
        "anthropic": ("ANTHROPIC_API_KEY", config.ANTHROPIC_API_KEY),
        "deepseek": ("DEEPSEEK_API_KEY", config.DEEPSEEK_API_KEY),
        "openai": ("OPENAI_API_KEY", config.OPENAI_API_KEY),
    }.get(_dostawca(model))
    if _klucz and not _klucz[1]:
        raise PreflightFailed(
            "brak %s w .env — etap %r chodzi na %s"
            % (_klucz[0], purpose, model))

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

    # KAZDY TOR MA WLASNY SUFIT. Przebieg sprawdzajacy nie zjada budzetu konta,
    # ale tez nie jest bez granic — „bez limitu na testy" konczy sie petla,
    # ktora w nocy wydaje wszystko. Patrz `db.start_run`.
    tryb = db.tryb_przebiegu(conn, run_id)
    sufit_dnia = (config.TEST_LIMIT_USD if tryb == "test"
                  else config.DAILY_LIMIT_USD)
    spent_today = db.spent_usd(conn, today, tryb=tryb)
    if spent_today >= sufit_dnia:
        raise BudgetExceeded(
            f"limit dzienny toru {tryb!r} wyczerpany: "
            f"{spent_today:.4f} / {sufit_dnia} USD"
        )

    # SUFIT MIESIECZNY LICZY OBA TORY RAZEM. Miesiac chroni rachunek, nie
    # rozdzial obowiazkow — pieniadze wychodza z tej samej karty.
    spent_month = (db.spent_usd(conn, month, tryb="produkcja")
                   + db.spent_usd(conn, month, tryb="test"))
    if spent_month >= config.MONTHLY_LIMIT_USD:
        raise BudgetExceeded(
            f"limit miesięczny wyczerpany: {spent_month:.4f} / {config.MONTHLY_LIMIT_USD} USD"
        )
```

<!--KOD:llm.obraz-->
```python
def obraz(
    opis: str, *, conn: sqlite3.Connection, run_id: int | None = None
) -> bytes:
    """Generuje grafikę do artykułu i zapisuje jej koszt tam, gdzie resztę.

    Obraz idzie przez tę samą warstwę co tekst nie dla elegancji, tylko dlatego,
    że inaczej wypadłby z licznika: wyłącznik, limit na przebieg i dzienny sufit
    wydatków siedzą w `_preflight`, a nie w każdym wywołaniu z osobna.
    """
    _preflight("obraz", conn, run_id)
    if config.DRY_RUN:
        print("  [obraz] DRY_RUN — wywołanie pominięte", flush=True)
        return b""
    if not config.OPENAI_API_KEY:
        raise RuntimeError("brak OPENAI_API_KEY")

    import base64
    import urllib.request

    zadanie = json.dumps({
        "model": config.IMAGE_MODEL,
        "prompt": opis,
        "size": config.IMAGE_SIZE,
        "quality": config.IMAGE_QUALITY,
        "n": 1,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.openai.com/v1/images/generations",
        data=zadanie,
        headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}",
                 "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=config.IMAGE_TIMEOUT_S) as odp:
            dane = json.loads(odp.read().decode("utf-8"))
        surowy = dane["data"][0]["b64_json"]
    except Exception as exc:
        db.record_call(
            conn=conn, run_id=run_id, provider="openai", model=config.IMAGE_MODEL,
            purpose="obraz", tokens_in=0, tokens_out=0, web_searches=0,
            cost_usd=0.0, price_verified=0, ok=0,
            note=f"{type(exc).__name__}: {exc}"[:500],
        )
        raise

    usd = config.IMAGE_PRICE_USD
    db.record_call(
        conn=conn, run_id=run_id, provider="openai", model=config.IMAGE_MODEL,
        purpose="obraz", tokens_in=0, tokens_out=0, web_searches=0,
        cost_usd=usd, price_verified=0, ok=1, note=config.IMAGE_SIZE,
    )
    print(f"  [obraz] {config.IMAGE_MODEL}  {config.IMAGE_SIZE}  ~${usd:.4f}", flush=True)
    return base64.b64decode(surowy)
```

<!--KOD:stages.discovery-->
```python
def discovery(
    conn: sqlite3.Connection, run_id: int, question: str,
    recent_domains: list[str], tylko_pierwotne: bool = False,
) -> list[dict[str, Any]]:
    """Etap 3 — dyskoveria zrodel (DeepSeek V4 Pro + web_search dostawcy).

    `tylko_pierwotne` sluzy DRUGIEJ RUNDZIE. Zmierzone na trzynastu przebiegach:
    dyskoveria dopycha liste do dziesieciu pozycji, a gdy dokumenty pierwotne sie
    koncza, dopycha ja omowieniami — przebiegi z najdluzszym szukaniem mialy
    SREDNIO 3,0 zrodla pierwotne wobec 5,1 przy najkrotszym. Druga runda ma wiec
    dobierac REKORDY, a nie kolejne teksty o rekordach.
    """
    martwe = hosty_ktore_nigdy_nie_dzialaly(conn)
    if martwe:
        print("  [dyskoveria] pomijam hosty bez ani jednego udanego pobrania: %s"
              % ", ".join(martwe[:8]), flush=True)
    prompt = _prompt(
        "dyskoveria.md",
        question=(question if not tylko_pierwotne
                  else NOWA_LINIA.join([
                      question, "",
                      "SECOND ROUND — WE ALREADY HAVE COMMENTARY."
                      " Return PRIMARY records only:"
                      " the regulation, the filing, the dataset,"
                      " the study, the standard, the company's own statement."
                      " A source that is not the record itself is of no use"
                      " here, however good it is. Fewer is fine; none is an"
                      " honest answer."])),
        max_results=config.DISCOVERY_MAX_RESULTS,
        max_searches=config.DISCOVERY_MAX_SEARCHES,
        min_primary=config.MIN_PRIMARY_SOURCES,
        min_why=config.MIN_WHY_SOURCES,
        blocked_hosts=", ".join(list(config.BLOCKED_HOSTS) + martwe),
        # DOMENY OSTATNICH ARTYKULOW. Baza liczyla je co przebieg
        # (`db.recent_domains`), przekazywalismy je tu w parametrze — i nie
        # czytala ich ani jedna linia. Docstring w db.py obiecywal „wejscie do
        # reguly roznorodnosci", ktorej nie bylo nigdzie.
        #
        # To PREFERENCJA, nie bramka. Twardy zakaz zlozony z pozostalymi
        # filtrami (martwe hosty, BLOCKED_HOSTS, adresy spoza wynikow
        # wyszukiwania) potrafilby wyzerowac liste zrodel i wywalic przebieg
        # PO oplaceniu researchu — a przy MIN_PRIMARY_SOURCES ten sam
        # regulator czesto jest jedynym miejscem, gdzie dokument w ogole lezy.
        #
        # Sformulowanie ZAKAZUJE nawyku, nie NAKAZUJE pozycji — regula
        # nakazujaca pozycje po dziesieciu tekstach sama staje sie podpisem
        # maszyny (ta sama zasada co w gates.py).
        ostatnie_domeny=(", ".join(
            d for d in (recent_domains or [])[:15]
            if d and d.strip() == d and " " not in d
        ) or "(none yet - this is the first article of this account)"),
    )
    real_urls: list[str] = []
    text = llm.call(
        "discovery", DISCOVERY_SYSTEM, prompt,
        conn=conn, run_id=run_id, web_search=True, collect_urls=real_urls,
    )
    try:
        data = llm.parse_json(text)
    except Exception:
        # TEN SAM RATUNEK, CO PRZY CIEKAWOSTKACH, i tu jest potrzebniejszy.
        # Zmierzone 26 sierpnia na calej historii bazy: `discovery` robi
        # SREDNIO 20,2 wyszukiwania na wywolanie (maks. 32) wobec 14,4 przy
        # ciekawostkach, a kosztuje 4,61 USD — drugi wydatek po pisaniu.
        # Przepalone wywolanie dyskoverii jest wiec drozsze niz przepalona
        # ciekawostka i tak samo odzyskiwalne: material zostal znaleziony,
        # tylko oddany zdaniami.
        print("  [dyskoveria] brak JSON — probuje odzyskac z tekstu", flush=True)
        ratunek = llm.ratuj_json(
            "discovery", text, KSZTALT_DYSKOVERII,
            conn=conn, run_id=run_id)
        if not ratunek:
            raise
        data = llm.parse_json(ratunek)
    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError(f"dyskoveria nie zwróciła źródeł: {text[:300]!r}")

    # Brak wyników wyszukiwania znaczy, że model NIE SZUKAŁ i podaje adresy
    # z pamięci. Zamykamy się, a nie otwieramy: pierwsza wersja tego filtru
    # miała warunek „jeśli są wyniki, sprawdzaj", więc przy zerze wyników
    # przepuściła dziesięć zmyślonych adresów, z których pobrały się trzy,
    # a klasyfikacja odrzuciła wszystkie.
    if not real_urls:
        raise ValueError(
            "dyskoveria nie wykonała ani jednego wyszukiwania — zwrócone adresy "
            "pochodzą z pamięci modelu, nie z sieci"
        )
    real_hosts = {_host(u) for u in real_urls}
    kept: list[dict[str, Any]] = []
    spoza = 0
    for source in sources:
        url = source.get("url", "")
        host = _host(url)
        if not url.startswith("http"):
            continue
        if host in config.BLOCKED_HOSTS or any(host.endswith(b) for b in config.BLOCKED_HOSTS):
            print(f"  [dyskoveria] pomijam {host} — host blokuje automaty", flush=True)
            continue
        # ADRES SPOZA WYNIKOW WYSZUKIWANIA: nie odrzucamy, tylko oznaczamy
        # i limitujemy.
        #
        # Filtr porownywal HOSTY i przez to blokowal dokladnie te zrodla, po
        # ktore prompt kaze siegac. Zlapane na przebiegu 25 sierpnia: model
        # oddal oryginalne sledztwo duzej redakcji, tekst drugiej, dwa raporty
        # organizacji badawczej, dokument organizacji miedzynarodowej i jeden
        # dokument branzowy — wszystkie SZESC odrzucone, bo akurat to
        # wyszukiwanie nie zwrocilo niczego z tych domen. Same dokumenty
        # pierwotne, czyli dokladnie to, po co ten etap istnieje.
        #
        # Powod filtru jest realny i zostaje: raz przepuscil dziesiec zmyslonych
        # adresow. Ale test byl nie ten. Pytal "czy wyszukiwarka to zwrocila",
        # a pytanie brzmi "czy to istnieje" — i na to odpowiada POBRANIE, nie
        # wyszukiwarka. Zmyslony adres nie ma czego oddac.
        #
        # Limit trzy, bo z tamtych dziesieciu zmyslonych trzy jednak sie
        # pobraly (strony oddajace 200 na nieistniejacej sciezce). Klasyfikacja
        # je wtedy odrzucila — druga siatka trzyma — ale nie ma po co jej
        # zasypywac. Trzy wystarcza na metaanalize, raport i wyrok.
        if real_hosts and host not in real_hosts:
            if spoza >= MAKS_SPOZA_WYSZUKIWANIA:
                print(f"  [dyskoveria] pomijam {url} — spoza wyszukiwania, "
                      f"limit {MAKS_SPOZA_WYSZUKIWANIA} wykorzystany", flush=True)
                continue
            spoza += 1
            source["spoza_wyszukiwania"] = True
            print(f"  [dyskoveria] {host} spoza wyszukiwania — przepuszczam, "
                  f"rozstrzygnie pobranie ({spoza}/{MAKS_SPOZA_WYSZUKIWANIA})",
                  flush=True)
        source["host"] = host
        kept.append(source)

    print(
        f"  [dyskoveria] {len(real_urls)} wyników wyszukiwania -> "
        f"{len(sources)} zaproponowanych -> {len(kept)} po filtrze",
        flush=True,
    )
    if not kept:
        raise ValueError("dyskoveria nie zwróciła ani jednego wiarygodnego adresu")
    return kept
```

<!--KOD:stages.pick_topic-->
```python
def pick_topic(
    topics: list[dict[str, Any]], assessments: list[dict[str, Any]],
    run_id: int | None = None, wczesniejsze: list[str] | None = None
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Wybiera temat leksykograficznie wedlug dziewieciu kryteriow.

    Kolejnosc to: niepowtorzenie, nosnosc, artykulowosc, ranking modelu,
    swiezosc, watki, glebokosc, pewnosc i liczba zrodel.

    Glebokosc idzie przed pewnoscia, bo dobrze udokumentowany temat bez drugiego
    aktu daje artykul poprawny i nudny — a to jest gorsze niz temat nieco slabiej
    udokumentowany, ktory ma o czym opowiadac. THIN nie jest odrzucany z miejsca,
    tylko laduje na koncu kolejki: siegamy po niego dopiero, gdy nie ma nic
    lepszego, i wtedy dostaje najkrotsza forme.
    """
    waga = {"RICH": 2, "SINGLE": 1, "THIN": 0}

    def temat(a: dict[str, Any]) -> dict[str, Any]:
        i = int(a.get("index", -1))
        return topics[i] if 0 <= i < len(topics) else {}

    def nosny(a: dict[str, Any]) -> int:
        """Czy temat niesie KTORAKOLWIEK z dwoch rzeczy: przekonanie albo stawke.

        Bylo tu `ma_przekonanie` i tylko ono — wiec temat drugiego rodzaju,
        ktory skaut swiadomie stawia na czele, wracal tutaj na sam dol. Piec
        dobrych tematow z przebiegu 20 sierpnia nie zostaloby wybranych nigdy.
        """
        t = temat(a)
        return int(bool(t.get("nosny", t.get("ma_przekonanie"))))

    def swiezy(a: dict[str, Any]) -> int:
        """Czy tego jeszcze nie opisano gdzie indziej.

        TO JEST PIATY KLUCZ: po niepowtorzeniu, nosnosci, artykulowosci i
        rankingu modelu. To takze powod, dla ktorego ranking w ogole przepisano.
        Temat oklepany ma z definicji NAJOSTRZEJSZE „wszyscy zakladaja" — bo
        dokladnie dlatego zostal oklepany. Ranking oparty na sile zlamanego
        przekonania wybieral wiec KANON obalania mitow w danej dziedzinie:
        te cztery czy piec rzeczy, o ktorych napisano juz tysiac tekstow
        i ktore kazdy zna wlasnie z nich.
        """
        return int(not temat(a).get("nasycony", False))

    def wlasny_ranking(a: dict[str, Any]) -> int:
        """Gdzie model postawil ten temat wsrod SWOICH wlasnych propozycji.

        Listy bezwzgledne model wyrownuje — kazdemu tematowi przypisal po trzy
        znane teksty i po szesc watkow, wiec ani nasycenie, ani watki niczego
        nie rozrozinialy. Wymuszonego wyboru wyrownac sie nie da, wiec to on
        idzie pierwszy.
        """
        return int(temat(a).get("pozycja", 0))

    def watki(a: dict[str, Any]) -> int:
        """Ile osobnych pytan niesie temat. Jeden watek to notka, nie artykul."""
        return int(temat(a).get("ile_watkow", 0))

    def artykulowy(a: dict[str, Any]) -> int:
        """Czy temat ma udokumentowana historie awarii I zasieg poza jedno
        miejsce. Sama procedura to notka: kompletna odpowiedz w jednym zdaniu,
        ktorej rozbicie na podpunkty daje rozdmuchana notke, a nie artykul.

        Idzie zaraz po nosnosci i PRZED wlasnym rankingiem modelu, bo tu nie
        chodzi o to, ktory temat jest ciekawszy, tylko ktory w ogole nadaje sie
        na te dlugosc.
        """
        return int(bool(temat(a).get("na_artykul")))

    def niepowtorzony(a: dict[str, Any]) -> int:
        """Czy tego tematu nie opisalismy juz pod inna nazwa.

        Sprawdzenie W KODZIE, bo prosba w prompcie zawiodla w sposob mozliwy
        do zmierzenia: 25 sierpnia rano poszedl artykul o pewnej sprawie,
        a po poludniu ten sam skaut — z tym tytulem na liscie zakazanych —
        zaproponowal „Example Article Six" i wygral ranking. TA SAMA sprawa,
        te same zrodla, przemianowany tytul.

        Porownujemy TYTUL RAZEM Z PYTANIEM, bo tytul bywa metafora („Convicted
        by Deadline"), a pytanie nazywa rzecz wprost. Prog ostry, ten sam co
        miedzy dniami przy notkach — luzny blokowalby tematy sasiadujace, a
        temat sasiadujacy to jeszcze nie powtorka.

        Nie odrzucamy, tylko spychamy na koniec kolejki. Gdy caly przebieg
        oddaje same powtorki, lepiej napisac powtorke niz nic — research jest
        juz oplacony, a zasada wlasciciela mowi, ze artykul ma powstac.
        """
        if not wczesniejsze:
            return 1
        t_ = temat(a)
        opis = "%s %s" % (t_.get("title") or "", t_.get("question") or "")
        return int(not any(
            _o_tym_samym(opis, w, **POWTORKA_TEMATU)
            for w in wczesniejsze if w))

    def kolejnosc(a: dict[str, Any]):
        # NIEPOWTORZONY PRZED NOSNYM — i to jest zmiana po audycie.
        #
        # Bylo odwrotnie, wiec temat juz opisany wygrywal z nowym, jesli tylko
        # mial stawke. Odtworzone na prawdziwym artykule z bazy: agent po raz
        # DRUGI napisalby o tej samej sprawie, a w uwagach zobaczylbys "nosny:
        # 0 wobec 1" — bo powod przegranej zatrzymuje sie na pierwszej roznicy
        # i o powtorce nie bylo ani slowa.
        #
        # Nosnosc jest w praktyce prawie zawsze prawdziwa: w jedynej realnej
        # probce mialo ja wszystkie szesc tematow. Przesuniecie jej o jedno
        # miejsce nic wiec nie kosztuje, a zamyka wade, na ktora wlasciciel
        # zwracal uwage trzy razy jednego dnia.
        return (niepowtorzony(a),
                nosny(a),
                artykulowy(a),
                wlasny_ranking(a),
                swiezy(a),
                watki(a),
                waga.get(str(a.get("depth", "RICH")).upper(), 1),
                a.get("confidence", 0),
                a.get("expected_primary_sources", 0))

    if wczesniejsze:
        zepchniete = [temat(a).get("title") for a in assessments
                      if a.get("feasible") and not niepowtorzony(a)]
        if zepchniete:
            print("  [tematy] juz o tym pisalismy, na koniec kolejki: %s"
                  % ", ".join(str(x)[:40] for x in zepchniete if x), flush=True)

    # MARTWE POLA ODSIEWU — meldujemy je tak samo, jak u skauta.
    #
    # Zmierzone 30 sierpnia: `feasible` bylo True w SZESCIU ocenach na szesc,
    # czyli filtr ponizej nie odfiltrowywal niczego. Reszta pol rozroznia
    # naprawde (`confidence` 0,85-0,55, `depth` RICH/SINGLE/THIN, `parallels`
    # puste u polowy), wiec wybor nie jest losowy — ale linijka, ktora WYGLADA
    # na bramke i nia nie jest, jest gorsza niz jej brak: log wyglada na
    # przesiany, a kolejnosc na przemyslana.
    #
    # Nie przebudowuje tu promptu, bo nie mam dowodu, ze wybor jest zly —
    # a dzis raz juz podjalem decyzje na zle dobranym materiale. Melduje.
    martwe_oceny = _stale_sygnaly(assessments, ("feasible", "depth",
                                                "confidence",
                                                "expected_primary_sources"))
    if martwe_oceny:
        print("  [odsiew] MARTWE W TYM PRZEBIEGU (ta sama wartosc u wszystkich"
              " %d, wiec nic nie rozroznily): %s"
              % (len(assessments), ", ".join(martwe_oceny)), flush=True)

    ranked = sorted((a for a in assessments if a.get("feasible")),
                    key=kolejnosc, reverse=True)
    if len(ranked) == len(assessments) and assessments:
        print("  [odsiew] `feasible` przepuscilo WSZYSTKIE %d — kolejnosc"
              " bierze sie z rankingu, nie z tego filtru" % len(assessments),
              flush=True)
    if not ranked:
        # ODSIEW ZGLASZA, NIE BLOKUJE — tak jak wszystko inne w tym potoku.
        # Wczesniej leciał tu wyjatek i przebieg umieral. Zasada wlasciciela
        # mowi co innego: skoro temat zostal wybrany, a research oplacony,
        # artykul MA powstac; bramki oddaja uwagi, nie werdykty.
        #
        # Podejrzewam zreszta, ze to wlasnie dlatego `feasible` bylo prawdziwe
        # w 6 ocenach na 6: model nie mial jak powiedziec „nie" tak, zeby
        # system to przezyl, wiec nie mowil. Odsiew, ktory nie moze odrzucic,
        # nie jest odsiewem — a odsiew, ktory zabija przebieg, jest gorszy.
        wszystkie = sorted(assessments, key=kolejnosc, reverse=True)
        if not wszystkie:
            raise ValueError("odsiew nie oddal zadnej oceny")
        ranked = wszystkie[:1]
        print("  [odsiew] ZADEN temat nie przeszedl wykonalnosci — biore "
              "najlepszy z odrzuconych i zapisuje to w uwagach", flush=True)
        ranked[0]["mimo_odrzucenia"] = True
    best = ranked[0]

    # DZIEWIEC TEMATOW NA DZIESIEC ZNIKALO BEZ SLADU. Do bazy trafia tylko
    # zwyciezca, wiec przy nastepnej diagnozie nie bylo czego czytac.
    klucz_zwyciezcy = kolejnosc(best)
    przegrani = []
    for a in ranked[1:]:
        i = int(a.get("index", -1))
        przegrani.append({
            "tytul": str(temat(a).get("title") or "")[:200],
            "powod": _powod_przegranej(klucz_zwyciezcy, kolejnosc(a)),
            "wygral": str(temat(best).get("title") or "")[:200],
            "na_artykul": bool(temat(a).get("na_artykul")),
            "index": i,
        })
    ile = zapisz_przegranych(przegrani, run_id)
    if ile:
        print("  [tematy] %d przegranych zapisanych z powodem; "
              "najblizszy: %s" % (ile, przegrani[0]["powod"]), flush=True)

    index = int(best.get("index", 0))
    if not 0 <= index < len(topics):
        raise ValueError(f"odsiew wskazał nieistniejący temat: {index}")
    return topics[index], best
```

<!--KOD:stages.warto_pisac-->
```python
def warto_pisac(
    conn: sqlite3.Connection, run_id: int, card: dict[str, Any],
) -> dict[str, Any]:
    """Etap przed pisarzem: czy jest tu luka, ktora obcy poczuje.

    Model OBSERWUJE cztery rzeczy i cytuje dowod z karty; werdykt sklada KOD.
    O oceny liczbowe nie pytamy — stary agent nauczyl nas, ze kazdy score
    wraca 1.0, wiec prog byl dekoracja. Tu kazde pytanie jest tak-nie
    i wymaga cytatu, a to da sie sprawdzic.

    Werdykty:
      PISZ   — jest zlamane przekonanie i co najmniej dwa z trzech filarow
      DOLOZ  — jest zlamane przekonanie, ale materialu za malo: szukamy pary
      ODLOZ  — nie ma zlamanego przekonania, czyli nie ma luki
    """
    # KARTA SZLA TU UCIETA W POLOWIE ZDANIA. Limit 14000 znakow nie mial przy
    # sobie zadnego pomiaru, a audyt policzyl, ze ucinal 7 z 8 kart — model
    # dostawal skladniowo zepsuty JSON bez zadnego znacznika, ze czegos brakuje,
    # i na tym podejmowal decyzje "pisac czy nie". Pisarz i recenzent dostaja
    # karte w calosci, wiec bramka byla jedynym etapem sadzacym po urywku.
    #
    # Zamiast ciac na sztywno: probujemy calosci, a gdy naprawde jest za duza,
    # ucinamy NAJDLUZSZE listy, nie ogon dokumentu. Konstrukcja karty jest
    # wtedy nienaruszona, a to ona niesie decyzje.
    _pelna = json.dumps(card, ensure_ascii=False, indent=2)
    if len(_pelna) > 14000:
        _skrocona = dict(card)
        for _pole in ("confirmed_claims", "citable_numbers",
                      "parallel_mechanisms", "uncertain_claims"):
            _lista = _skrocona.get(_pole)
            if isinstance(_lista, list) and len(_lista) > 6:
                _skrocona[_pole] = _lista[:6]
                _skrocona["_uwaga_%s" % _pole] = (
                    "skrocone z %d pozycji, zeby karta zmiescila sie w limicie"
                    % len(_lista))
        _pelna = json.dumps(_skrocona, ensure_ascii=False, indent=2)
        print("  [warto_pisac] karta skrocona z %d znakow — przycieto listy, "
              "nie ogon" % len(json.dumps(card, ensure_ascii=False, indent=2)),
              flush=True)

    surowy = llm.call(
        "warto_pisac", WORTH_SYSTEM,
        _prompt("warto_pisac.md", card_json=_pelna[:14000]),
        conn=conn, run_id=run_id,
    )
    o = llm.parse_json(surowy)

    def jest(klucz: str) -> bool:
        blok = o.get(klucz)
        return bool(isinstance(blok, dict) and blok.get("present"))

    przekonanie = jest("contradicted_belief")
    # Deklaracja bez tresci to nie deklaracja. Model musi UMIEC nazwac przekonanie.
    tresc = str((o.get("contradicted_belief") or {}).get("the_belief", "")).strip()
    if przekonanie and len(tresc.split()) < 4:
        przekonanie = False
        o.setdefault("uwagi_kodu", []).append(
            "zaznaczono zlamane przekonanie, ale nie umiano go nazwac — nie liczy sie")

    filary = {"named_decider": jest("named_decider"),
              "felt_number": jest("felt_number"),
              "second_domain": jest("second_domain")}
    ile_filarow = sum(filary.values())

    # --- DRUGA DROGA: NIEROZSTRZYGNIETY WYNIK ------------------------------
    # Cztery pytania powyzej opisuja rzecz JUZ ROZSTRZYGNIETA: przekonanie, ktore
    # jest bledne, decyzje, ktora zapadla, liczbe, ktora zmierzono. To sa pytania
    # zamkniete — a luka informacyjna z definicji sie nasyca. Loewenstein pisze
    # to wprost: konsumpcja informacji jest nagradzajaca, ale po zdobyciu
    # wystarczajacej ilosci ciekawosc SPADA. Pismo zbudowane wylacznie na
    # pytaniach zamknietych produkuje czytelnikow zaspokojonych i odchodzacych.
    #
    # Dlatego jest druga droga. Warunek, ktory oddziela ja od wrozenia, jest
    # jeden i twardy: karta musi niesc SPISANA REGULE rozstrzygajaca ten wynik.
    # Bez niej to spekulacja i nie przechodzi.
    stawka_blok = o.get("unsettled_outcome") or {}
    stawka = bool(isinstance(stawka_blok, dict) and stawka_blok.get("present"))
    pytanie = str(stawka_blok.get("the_question", "")).strip()
    regula = str(stawka_blok.get("governed_by", "")).strip()

    if stawka and len(pytanie.split()) < 4:
        stawka = False
        o.setdefault("uwagi_kodu", []).append(
            "zaznaczono nierozstrzygniety wynik, ale nie umiano nazwac pytania")
    if stawka and len(regula.split()) < 3:
        stawka = False
        o.setdefault("uwagi_kodu", []).append(
            "wynik bez spisanej reguly, ktora go rozstrzyga — to wrozenie, nie tekst")
    elif stawka and _ZAPRZECZENIE.match(regula):
        # Model, ktory uczciwie odpowiada „nic tego nie rozstrzyga, po prostu
        # nikt tego nie zapisal", opisuje LUKE W NASZEJ WIEDZY, a nie stawke.
        # Sam licznik slow tego nie zlapie, bo takie zdanie jest dluzsze niz
        # nazwa prawdziwej procedury. Rozroznienie nalezy do modelu i prompt
        # mowi je wprost, ale kod nie moze przepuszczac odpowiedzi, ktora
        # ZAPRZECZA sama sobie w pierwszych slowach.
        stawka = False
        o.setdefault("uwagi_kodu", []).append(
            "pole reguly zaprzecza istnieniu reguly (%r) — to luka w wiedzy, "
            "nie nierozstrzygniety wynik" % regula[:70])

    droga_przekonania = przekonanie and ile_filarow >= MIN_FILAROW_POZA_PRZEKONANIEM
    # Stawka potrzebuje nazwanego decydenta. Regula, ktorej nikt nie ustanowil,
    # to zjawisko, a nie procedura — i wtedy nie ma czego wystawiac na probe.
    droga_stawki = stawka and filary["named_decider"]

    if droga_przekonania and droga_stawki:
        werdykt, powod = "PISZ", (
            "obie drogi: zlamane przekonanie + %d z 3 filarow ORAZ "
            "nierozstrzygniety wynik ze spisana regula" % ile_filarow)
    elif droga_przekonania:
        werdykt, powod = "PISZ", "zlamane przekonanie + %d z 3 filarow" % ile_filarow
    elif droga_stawki:
        werdykt, powod = "PISZ", (
            "nierozstrzygniety wynik + spisana regula, ktora go rozstrzyga "
            "(droga stawki, bez zlamanego przekonania)")
    elif przekonanie:
        werdykt, powod = "DOLOZ", (
            "zlamane przekonanie jest, ale tylko %d z 3 filarow — szukamy pary "
            "w banku zanim to pojdzie do pisarza" % ile_filarow)
    elif stawka:
        werdykt, powod = "DOLOZ", (
            "jest nierozstrzygniety wynik, ale nikt nie ustanowil reguly — "
            "szukamy w banku, kto to rozstrzyga")
    else:
        werdykt, powod = "ODLOZ", (
            "ani przekonania do zlamania, ani nierozstrzygnietego wyniku — "
            "czytelnik nie ma ani luki do zamkniecia, ani stawki do sledzenia")

    o["przekonanie"] = przekonanie
    o["stawka"] = stawka
    o["filary"] = filary
    o["ile_filarow"] = ile_filarow
    o["werdykt"] = werdykt
    o["powod"] = powod
    return o
```

<!--KOD:stages._precedens_ok-->
```python
def _precedens_ok(p: Any) -> bool:
    """Czy ten wpis to naprawde precedens, a nie wypelniacz.

    Musi niesc TRZY rzeczy naraz: zdarzenie, date i skutek. Kazda z osobna da
    sie wypelnic pustym slowem — tak jak model wypelnil watki szescioma
    sztukami na kazdy temat, a znane teksty trzema.

    `what_changed` jest najwazniejsze i o nim najlatwiej zapomniec: caly sens
    precedensu polega na tym, ze regulamin jest BLIZNA. Zdarzenie, po ktorym
    nic sie nie zmienilo, to anegdota — ciekawa, ale nie ona niesie tysiac slow.
    """
    if not isinstance(p, dict):
        return False
    if len(str(p.get("what_happened") or "").split()) < 5:
        return False
    if not re.search(r"\d{3,4}", str(p.get("when") or "")):
        return False              # „dawno temu" to nie jest data
    zmiana = str(p.get("what_changed") or "").strip()
    if len(zmiana.split()) < 3:
        return False
    return not re.match(r"^\W*(nothing|none|no\s|nic|brak)", zmiana, re.I)
```

<!--KOD:stages.zapisz_przegranych-->
```python
def zapisz_przegranych(przegrani: list[dict[str, Any]],
                       run_id: int | None = None) -> int:
    """Dopisuje do dziennika tematy, ktore NIE wygraly, z powodem przegranej.

    DARMOWY TEST TU NIE PISZE. `test_wybor_tematu.py` wola `pick_topic`, ta wola
    te funkcje, a sciezka szla z `config.DATA_DIR` — wiec kazde uruchomienie
    zestawu dopisywalo atrapy do PRODUKCYJNEGO dziennika. Zmierzone 2 wrzesnia
    2026: 294 z 400 wpisow na serwerze to byly atrapy, a prawdziwe przegrane
    tematy zostaly z bufora wypchniete. Nic tego pliku nie czyta przy decyzjach,
    wiec szkoda byla wylacznie diagnostyczna — ale dziennik, ktory w trzech
    czwartych sklada sie z atrap, nie jest juz diagnostyka.

    DIAGNOSTYKA, NIE BRAMKA. Nic tego pliku nie czyta przy wyborze tematu
    i tak ma zostac. Powod jest konkretny: temat odrzucony dzis, bo brakowalo
    mu drugiego precedensu, moze go miec za pol roku, gdy pojawi sie nowy
    dokument. Indeks kandydatow na NOTKI dziala inaczej — tam odrzucenie jest
    ostateczne, bo martwy fakt zostaje martwy — i ta roznica jest celowa.

    Po co to w ogole. Skaut oddaje dziesiec tematow, wygrywa jeden, dziewiec
    znikalo bez sladu: do bazy trafia tylko zwyciezca, a log mowil najwyzej
    „NA ARTYKUL: 6 z 10". Gdy skaut oddal ZERO tematow artykulowych, moja
    pierwsza diagnoza byla bledna — twierdzilem, ze model nie umie podac
    precedensow przed researchem, a on podal wzorcowy w tym samym przebiegu,
    tylko jeden przy progu dwa. Z tym dziennikiem widac to od razu.
    """
    if not przegrani:
        return 0
    if config.W_TESCIE and _pisze_do_produkcji(PRZEGRANE_TEMATY):
        print("  [przegrani] darmowy test — nie dopisuje do produkcyjnego dziennika",
              flush=True)
        return 0
    try:
        stare = json.loads(PRZEGRANE_TEMATY.read_text(encoding="utf-8"))
        stare = [w for w in stare if isinstance(w, dict)] if isinstance(stare, list) else []
    except (OSError, ValueError):
        stare = []      # Uszkodzony dziennik to pusty dziennik, nie awaria.
    for p in przegrani:
        p["run_id"] = run_id
        p["kiedy"] = db.now()
    wszystko = (stare + przegrani)[-ILE_PRZEGRANYCH_TRZYMAMY:]
    try:
        PRZEGRANE_TEMATY.parent.mkdir(parents=True, exist_ok=True)
        PRZEGRANE_TEMATY.write_text(
            json.dumps(wszystko, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError as exc:
        # Dziennik diagnostyczny NIE MOZE zatrzymac przebiegu. Artykul jest
        # wazniejszy od notatki o tym, dlaczego inny temat go nie zostal.
        print("  [tematy] nie zapisalem dziennika przegranych: %s" % exc, flush=True)
        return 0
    return len(przegrani)
```

<!--KOD:stages._powod_przegranej-->
```python
def _powod_przegranej(klucz_zwyciezcy, klucz_tematu) -> str:
    """Ktory skladnik klucza sortowania ROZSTRZYGNAL, i jakimi wartosciami.

    Nie „temat byl gorszy", tylko „przegral na `artykulowy`: 0 wobec 1".
    Powod liczy KOD z tego, co i tak policzyl, zeby posortowac — nie model
    o sobie samym. To jest cala roznica wobec `discarded_seeds` z prototypu:
    samoocena modelu jest niesprawdzalna i wyrownuje sie do stalej, a to tutaj
    jest odczytem z rzeczywistej decyzji.
    """
    for nazwa, u_zwyciezcy, u_tematu in zip(SKLADNIKI_KLUCZA, klucz_zwyciezcy,
                                            klucz_tematu):
        if u_zwyciezcy != u_tematu:
            return "%s: %s wobec %s" % (nazwa, u_tematu, u_zwyciezcy)
    return "remis na calym kluczu — zadecydowala kolejnosc z modelu"
```

<!--KOD:stages._stale_sygnaly-->
```python
def _stale_sygnaly(topics: list[dict], pola: tuple[str, ...]) -> list[str]:
    """Ktore z pol mialy TE SAMA wartosc u WSZYSTKICH kandydatow.

    Trzeci raz ta sama wada, wiec tym razem wykrywacz zostaje w kodzie zamiast
    w komentarzu. Samooceny wracaly zawsze 1.0. Watki — zawsze szesc. Znane
    teksty — zawsze trzy. Za kazdym razem pole bylo czytane, sortowanie z niego
    korzystalo, testy przechodzily, a sygnal nie rozrozinial NICZEGO, bo mial
    u wszystkich te sama wartosc. Martwy sygnal tego rodzaju jest gorszy niz
    brak pola: log wyglada na bogaty, kolejnosc na przemyslana.

    Pole stale u wszystkich kandydatow to zero informacji — niezaleznie od
    tego, czy stala jest wysoka czy niska. Nie zgaduje przyczyny (moze model
    wyrownuje, moze prompt zle pyta) i niczego nie blokuje; wypisuje fakt,
    zeby nastepnym razem nie trzeba bylo tego wypatrzec golym okiem w logu.
    """
    if len(topics) < 2:
        return []
    martwe = []
    for pole in pola:
        wartosci = {repr(t.get(pole)) for t in topics}
        if len(wartosci) == 1:
            martwe.append("%s=%s" % (pole, wartosci.pop()))
    return martwe
```

<!--KOD:stages.losuj_odstep-->
```python
def losuj_odstep(co: str = "") -> float:
    """Losuje przerwę, ale jej NIE odsypia.

    Rozdzielone, bo wywołujący musi znać długość przerwy ZANIM w nią wejdzie.
    Przebieg 28 zginął dokładnie na tym: `odczekaj` losowało 86 minut i od razu
    zasypiało, a na zegarze przebiegu zostało dwadzieścia. Systemd ubił proces
    w środku snu, w drugim z ośmiu bloków — sześć pozostałych nie wykonało się
    w ogóle. Kto ma zdecydować, czy przerwa się zmieści, musi najpierw
    zobaczyć liczbę.
    """
    import random

    dol, gora = config.ODSTEPY.get(co, config.ODSTEP_MIEDZY_DZIALANIAMI)
    return random.uniform(dol, gora)
```

<!--KOD:stages.bramka_kandydata-->
```python
def bramka_kandydata(k: dict[str, Any]) -> tuple[bool, str]:
    """Czy z tego da sie zrobic notke. Sprawdza KOD, nie model.

    Regula jest jedna i ta sama, co przy artykulach: da sie zapisac zlamane
    przekonanie w formie „wiekszosc sadzi X, naprawde Y"? Jesli nie — to jest
    ciekawostka, a ciekawostka jest zamknieta: mozna ja polubic i nie da sie
    na nia odpowiedziec, wiec nie rosnie.

    Do tego para decyzja-skutek. Decyzja bez skutku, ktory czytelnik trzyma
    w reku, to historia administracji. Skutek bez decyzji to ciekawostka.
    Notka istnieje dopiero tam, gdzie udokumentowana decyzja wyprodukowala
    rzecz, ktora ktos ma przy sobie.
    """
    wiara = str(k.get("wrong_belief") or "").strip()
    naprawde = str(k.get("actually") or "").strip()

    # BRAMKA 1 — NAZWANY DECYDENT Z DATA. To jest cala premisa pisma: „jaka
    # decyzja, przepis albo interes za tym stoi". Zabija „dlaczego niebo jest
    # niebieskie" jednym ruchem, bo nikt tego nie zdecydowal.
    # ROK JEST WYMAGANY TYLKO OD DECYZJI, nie od kazdego mechanizmu.
    #
    # Ta bramka powstala, gdy pole nazywalo sie „kto zdecydowal i kiedy" i
    # rzeczywiscie kazdy dopuszczalny mechanizm mial date. 30 sierpnia 2026
    # doktryna sie rozszerzyla: mechanizmem jest tez POMIAR (kto zmierzyl i co
    # wyszlo), OGRANICZENIE (co w budowie albo matematyce to wymusza) i
    # KOMPROMIS. Bramka o tym nie wiedziala i zostala sprzecznoscia, ktora sam
    # wprowadzilem, zmieniajac prompt i nie zagladajac do kodu.
    #
    # OGRANICZENIE NIE MA ROKU Z DEFINICJI. Zmierzone na 173 kandydatach:
    # DWADZIESCIA DZIEWIEC odrzucen „decydent bez daty" dotyczylo faktow, w
    # ktorych roku nie ma w ZADNYM polu — bo go nie moze byc. Byly to
    # ograniczenia wynikajace z budowy rzeczy albo z matematyki: cos dziala
    # tak, a nie inaczej, i nikt tego nie postanowil w zadnym dniu. To sa
    # najlepsze tematy tego pisma, odrzucane za to, ze nikt ich nie podpisal.
    #
    # Odrzucenie jest OSTATECZNE, wiec kazdy taki fakt przepadl na zawsze.
    decyzja = str(k.get("decision") or "").strip()

    # MECHANIZM MA BYC OPISANY, NIE WSKAZANY GESTEM — i to jest wlasciwy
    # rozroznik, ktorego szukalem trzy razy w zlym miejscu.
    #
    # Prog szesciu slow, nie dwoch. Zmierzone na zywych danych 30 sierpnia:
    #   ODPADA (3-4 slowa, machniecie reka):
    #     „ustalone przez komitet"          — nikt nienazwany, nic konkretnego
    #     „nikt, tak dziala fizyka"         — wprost brak mechanizmu
    #   PRZECHODZI (12-20 slow, opis):
    #     „Each supplier picks its own set-up — the parts, the tolerance, the
    #      batch size, how much is kept in stock"
    #     „The system returns a ranked list of candidates, never a certainty,
    #      so a wrong match is an artefact of the ranking"
    #     „A named team measured it on 500+ real cases at one site"
    #
    # Dlugosc rozdziela je czysto, a lista slow kluczowych nie rozdzielala ich
    # ani razu: probowalem slow decyzyjnych (zlapala „chose" w zaprzeczeniu) i
    # slow niedecyzyjnych (przepuscila trzy z pieciu falszywych odrzucen).
    # Opis mechanizmu po prostu MUSI byc dluzszy niz gest — to wlasnosc rzeczy,
    # nie slownictwa.
    if len(decyzja.split()) < 6:
        return False, ("mechanizm wskazany gestem, nie opisany: %r"
                       % decyzja[:60])
    # I jawne przyznanie, ze mechanizmu nie ma. Dluga wersja „nikogo tu nie ma"
    # przeszlaby przez sam prog dlugosci.
    if re.search(r"\b(nobody|no one|nothing|not decided by anyone|"
                 r"nikt|nie zdecydowal)\b", decyzja, re.I):
        return False, ("nikt tego nie sprawil — to zjawisko, nie mechanizm: %r"
                       % decyzja[:60])
    # WYMOG ROKU ZNIESIONY 30 sierpnia 2026, po dwoch nieudanych probach
    # zwezenia go — i to jest lekcja o metodzie, nie o tej jednej regule.
    #
    # Rok byl PROXY NA AKTUALNOSC z czasow, gdy pole nazywalo sie „kto
    # zdecydowal i kiedy", a jedynym dopuszczalnym mechanizmem byla decyzja.
    # Dzis aktualnosc mierzy DOKUMENT KONTROLNY (`swiezosc_faktu`): pyta wprost,
    # co musialoby sie zmienic, zeby twierdzenie przestalo byc prawdziwe, i
    # sprawdza date tego dokumentu. Trzymanie prymitywnego zamiennika obok
    # prawdziwego pomiaru to jest sposob, w jaki dorobilismy sie 30 falszywych
    # odrzucen na 32.
    #
    # PROBOWALEM GO ZWEZIC DWA RAZY I DWA RAZY PRZEGRALEM ZE SLOWNIKIEM:
    #   - wersja z lista slow decyzyjnych odrzucila zdanie „the architecture
    #     forces it; NOBODY CHOSE it", bo zlapala „chose" W ZAPRZECZENIU,
    #   - wersja z lista slow niedecyzyjnych odrzucila na ZYWYCH danych trzy
    #     z pieciu nowych kandydatow — wszystkie trzy byly opisami OGRANICZEN
    #     albo KOMPROMISOW, czyli dokladnie tym materialem, na ktorym nam
    #     zalezy najbardziej.
    # Wzorzec slownikowy na tekscie swobodnym zawsze bedzie dziurawy w te
    # strone, w ktora akurat nie patrzylem. To ta sama wada, co `\byour\b`.
    #
    # CO ZOSTAJE ZAMIAST NIEGO: wymog dwoch slow wyzej (zabija „nikt tego nie
    # zdecydowal"), zlamane przekonanie, skutek w drugiej osobie, sprawdzalnosc
    # — i dokument kontrolny, ktory robi to, do czego rok byl zastepnikiem.

    # BRAMKA 2 — ZLAMANE PRZEKONANIE. Najostrzejsza regula w calym potoku:
    # „wiekszosc nie wie" to NIE JEST przekonanie, tylko niewiedza, a niewiedza
    # produkuje ciekawostki. X musi byc twierdzeniem, ktorego czytelnik BRONILBY,
    # gdyby mu zaprzeczyc. Ten sam werdykt trzy razy niezaleznie: ta bramka,
    # bramka `warto_pisac` i wlasciciel, ktory usunal jedyny artykul zdjety po
    # publikacji — bo o jego temacie nikt nie mial zadnego zdania, wiec nie
    # bylo czego lamac.
    if len(wiara.split()) < MIN_SLOW_POLOWY:
        return False, "brak przekonania do zlamania — to ciekawostka, nie notka"
    if re.search(r"\b(don'?t know|do not know|never heard|are unaware|not aware|"
                 r"nikt nie wie|malo kto wie)\b", wiara, re.IGNORECASE):
        return False, ("niewiedza to nie przekonanie — czytelnik musi czegos "
                       "BRONIC, a nie tego nie znac: %r" % wiara[:60])
    if len(naprawde.split()) < MIN_SLOW_POLOWY:
        return False, "jest przekonanie, ale nie ma co mu przeciwstawic"

    # BRAMKA 3 — KONTAKT. Czytelnik ma tego dotykac, nie podziwiac z daleka.
    skutek = str(k.get("consequence") or "").strip()
    if not skutek:
        return False, "decyzja bez skutku, ktory czytelnik trzyma w reku"

    # I MUSI TO BYC ZWYKLY CZLOWIEK, NIE FACHOWIEC. Pierwszy przebieg na
    # rejestrze rozporzadzen wypuscil szesc kandydatow na szesc: cztery zmiany
    # stawek i oplat dla waskich grup zawodowych, jeden dodatek branzowy i —
    # najlepszy z nich — zmiana formatowania naglowka w samym rejestrze. Kazdy
    # mial decydenta, date, zlamane przekonanie i skutek, i zaden nie nadawal
    # sie do publikacji, bo przekonanie trzyma BRANZA, a nie czytelnik.
    #
    # Zero odrzucen na prawdziwych danych bylo zreszta samo w sobie ostrzezeniem:
    # bramka, ktora nigdy nie zagryzla, nie jest bramka.
    # Sprawdzenie jest STRUKTURALNE, nie slownikowe, bo lista slow branzowych
    # jest z natury dziurawa — przepuscila i dodatek dla waskiej grupy
    # zawodowej, i zmiane formatowania naglowka w samym rejestrze.
    #
    # Roznica miedzy dobrym a zlym skutkiem jest inna: dobry nazywa RZECZ,
    # ktora czytelnik ma, zly nazywa OSOBE, ktorej dotyczy przepis.
    #   dobrze: rzecz, ktora czytelnik ma pod reka i moze na nia
    #           spojrzec — nazwana konkretnie, nie kategoria
    #   zle:    „the holder of a category-three regional permit",
    #           „grade-nine seasonal staff assigned to controlled operations"
    #
    # Wymog DRUGIEJ OSOBY wymusza odpowiedz na pytanie CO MA CZYTELNIK zamiast
    # KOGO TO DOTYCZY. Prompt zamawia dokladnie taka forme, wiec to nie jest
    # zgadywanka — to sprawdzenie, czy model wykonal polecenie.
    #
    # SZUKALO SAMEGO „your" I TO BYLA WADA NA JEDNA LITERE. Zmierzone 30
    # sierpnia 2026 na 173 kandydatach z produkcji: SZESNASCIE odrzucen z
    # powodem „brak slowa 'your'" dotyczylo zdan pisanych w drugiej osobie —
    # rzeczy z wlasnej niszy, nazwane tak, jak czytelnik ich uzywa — nie
    # kategoria, tylko egzemplarz, ktory ma przed soba: „the entry-level job
    # you apply for". To jest DOKLADNIE forma, ktorej ta bramka zada,
    # odrzucana przez brak litery „r".
    #
    # Slowo w slowo: `\byour\b` nie lapie „you", a rzeczy nazwane przez
    # czytelnika w drugiej osobie czesto stoja wlasnie z „you". Wzorzec
    # wymienia teraz wszystkie formy.
    #
    # Zginal na tym najlepszy material, jaki potok znalazl. Odrzucenie jest
    # OSTATECZNE — wpis dostaje status „odrzucony" na zawsze — wiec te fakty
    # nie wracaja nigdy.
    #
    # BRAMKA SIE NIE ROZLUZNIA: oba pierwotne kontrprzyklady, ktore ja
    # wywolaly — „the holder of a category-three regional permit" i „grade-nine
    # seasonal staff" — nadal nie zawieraja zadnej drugiej osoby.
    if not re.search(r"\byou\b|\byour\b|\byou're\b|\byours\b|\byourself\b",
                     skutek, re.IGNORECASE):
        return False, ("skutek nazywa kogos, nie rzecz czytelnika (brak drugiej"
                       " osoby): %r" % skutek[:70])

    # BRAMKA 4 — SPRAWDZALNOSC. Jesli nie umiemy nazwac, GDZIE mieszka
    # odpowiedz, to weryfikacja padnie pozniej — a wtedy research bedzie juz
    # oplacony. Adres wystarcza za wskazanie rodzaju dokumentu.
    if not str(k.get("url") or "").startswith("http"):
        return False, "brak zrodla"

    czysty, powod = bez_wstrzykniecia("%s %s %s" % (wiara, naprawde, k.get("fact", "")))
    if not czysty:
        return False, "zapora: %s" % powod
    return True, ""
```

<!--KOD:stages.budzet_dnia-->
```python
def budzet_dnia(conn: sqlite3.Connection) -> dict[str, int]:
    """Ile czego agent może dziś zrobić — losowane z widełek, nie stałe.

    Stała liczba dziennie wygląda jak robot, bo człowiek nie ma normy: raz
    przeczyta pół kanału, raz nic. Losujemy osobno na każdy dzień, a przez
    pierwszy miesiąc trzymamy się dolnej połowy — nowe konto z jednym artykułem,
    które nagle obserwuje dwadzieścia osób, wygląda dokładnie jak farma.
    """
    import random
    from datetime import datetime, timezone

    rozbieg = _wiek_konta_w_dniach(conn) < config.ROZBIEG_DNI

    # LOSUJEMY RAZ NA DOBE, NIE RAZ NA PRZEBIEG.
    #
    # Ziarno bierze sie z daty, wiec wszystkie przebiegi tego samego dnia
    # licza TEN SAM budzet, a kazdy kolejny dzien inny. Bez pliku, bez tabeli,
    # bez stanu do odtwarzania po awarii — data jest wszystkim, czego trzeba.
    #
    # Dotad kazdy przebieg losowal osobno i dzielil wynik przez liczbe
    # pozostalych przebiegow. Przy malych widelkach to zjadalo cala reszte:
    # budzet 1 restack podzielony na trzy przebiegi daje zero, zero i jeden —
    # i tak samo nastepnego dnia. Zmierzone na dzienniku: restacki wychodzily
    # 1, 1, 1, 1, odchylenie standardowe ZERO. Dzien po dniu ta sama liczba
    # to jest dokladnie ten podpis maszyny, ktorego unikamy.
    dzis = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    los = random.Random("%s|nia-budzet-dnia" % dzis)

    def losuj(widelki: tuple[int, int]) -> int:
        dol, gora = widelki
        if rozbieg:
            # ROZBIEG MA OBNIZAC SREDNIA, NIE ZABIJAC LOSOWANIE.
            # Bylo `gora = dol + (gora - dol) // 2` i przy widelkach szerokosci
            # jeden — (1, 2) dla restackow — dawalo to `1 + 0 = 1`, czyli
            # randint(1, 1). Kazde waskie widelki byly w rozbiegu STALA.
            polowa = dol + (gora - dol) // 2
            gora = min(gora, max(polowa, dol + 1)) if gora > dol else gora
        return los.randint(dol, gora)

    # Miesięczne przeliczamy na dzień, żeby wszystko było jedną walutą; ułamek
    # rozstrzyga losowanie, więc w skali miesiąca wychodzi zadana liczba.
    def z_miesiaca(widelki: tuple[int, int]) -> int:
        dziennie = losuj(widelki) / 30.0
        return int(dziennie) + (1 if los.random() < dziennie % 1 else 0)

    budzet = {
        # Notki nie sa losowane: rozklad tygodnia ma ich piec na dzien i to jest
        # kontrakt, a nie widelki. Sa w budzecie, zeby liczyc je tak samo jak
        # reszte przy dzieleniu dnia na przebiegi.
        "notki": len(config.NOTE_MIX_OTHER_DAY),
        "lajki": losuj(config.LAJKI_DZIENNIE),
        "komentarze": losuj(config.KOMENTARZE_DZIENNIE),
        "follow": z_miesiaca(config.FOLLOW_MIESIECZNIE),
        "subskrypcje": z_miesiaca(config.SUBSKRYPCJE_MIESIECZNIE),
        "restacki": losuj(config.RESTACK_DZIENNIE),
    }
    print(f"  [budżet dnia{' — rozbieg' if rozbieg else ''}] "
          + "  ".join(f"{k}={v}" for k, v in budzet.items()), flush=True)
    _zapisz_budzet_dnia(dzis, budzet, rozbieg)
    return budzet
```

<!--KOD:stages.artykul_do_promocji-->
```python
def artykul_do_promocji() -> dict[str, Any] | None:
    """Artykul, ktory dzis czeka na notke promujaca — najwyzej JEDNA na dobe.

    Wlasciciel: trzy notki na artykul, po jednej dziennie, trzy dni z rzedu
    ZARAZ po publikacji.

    NAJSWIEZSZY IDZIE PIERWSZY. Wczesniej pytalismy kolejke w kolejnosci
    wstawiania, wiec swiezo opublikowany artykul czekal za kazdym starszym,
    ktory nie wybral jeszcze swoich dni. Realnie: tekst opublikowany 19 sierpnia
    dostalby pierwsza notke promujaca okolo 29 sierpnia — z linkiem juz zimnym i
    artykulem dawno zepchnietym w dol kanalu. Slowo „po artykule" znaczy zaraz
    po nim, wiec kolejnosc idzie od konca listy, a `zapisz_do_promocji` dopisuje
    na koniec.

    Trzy dni z rzedu wychodza z tego same: dopoki artykul ma niewybrane dni,
    jest najswiezszy i wraca nastepnego dnia. Gdy dzien wypadnie — cichy dzien,
    wyczerpany przydzial notek — artykul nie przepada, tylko dobiera swoj dzien
    pozniej. Lepsze to niz zgubiona notka.

    JEDNA NA DOBE ZNACZY JEDNA, NIE JEDNA NA ARTYKUL. Wczesniej warunek
    „promowany dzis" tylko POMIJAL ten artykul i szedl dalej po liscie. Ta
    funkcja jest wolana raz na przebieg, a przebiegow jest piec dziennie —
    wiec drugi przebieg dostawal nastepny artykul z kolejki, a kolejne mogly
    tego samego dnia wystawic jeszcze trzy notki promujace inne teksty. Kolejka
    nigdy nie byla na tyle pelna, zeby to wyszlo na jaw, ale regula brzmi
    „jedna notka po artykule dziennie" i to jest caly dzien, nie jeden wiersz.
    """
    from datetime import datetime, timedelta, timezone

    dzis = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    kolejka = wczytaj_promocje()
    if any(a.get("ostatnia") == dzis for a in kolejka):
        return None             # dzisiejsza notka promujaca juz poszla
    granica = (datetime.now(timezone.utc)
               - timedelta(days=config.OKNO_PROMOCJI_DNI)).strftime("%Y-%m-%d")
    for a in reversed(kolejka):
        if a.get("wystawione", 0) >= config.NOTEK_PROMUJACYCH:
            continue
        # OKNO WAZNOSCI. Wpis bez `dodane` pochodzi sprzed tej reguly, wiec z
        # definicji nie jest dzisiejszy — traktujemy go jak przeterminowany.
        # To nie jest ostroznosc na wyrost: wlasnie takie wpisy zostaly w
        # kolejce po przestawieniu konta na nowa nisze i to one wystawilyby
        # notke promujaca artykul z poprzedniej.
        if str(a.get("dodane") or "") < granica:
            continue
        # ZAKWESTIONOWANY NIE WRACA. Patrz `zakwestionuj_promocje` — jedno „nie"
        # od sprawdzenia faktow zdejmuje artykul z kolejki na stale, bo inaczej
        # kolejny przebieg po prostu losuje jeszcze raz.
        if a.get("zakwestionowany"):
            continue
        return a
    return None
```

<!--KOD:stages.grafika-->
```python
def grafika(
    conn: sqlite3.Connection, run_id: int, draft: dict[str, Any],
    sciezka_artykulu: Path | None = None,
) -> dict[str, Any]:
    """Nagłówek graficzny artykułu.

    Rozpoznawalność bierze się z powtarzalności PALETY, ŚWIATŁA I NASTROJU,
    przepisywanych dosłownie z `prompts/grafika.md`. Model wybiera SCENĘ i
    kadr; tożsamość wizualna zmienia się w jednym miejscu, nie osobno przy
    każdym artykule.

    Powtarzalność szła kiedyś dalej: model wybierał jeden PRZEDMIOT, zawsze
    wyizolowany, zawsze na szarym papierze. To była reguła napisana pod
    jedną konkretną niszę, w której pojedynczy przedmiot na tle czytał się
    jak eksponat. Po przestawieniu konta ta sama reguła dawała okładki
    poprawne wobec briefu i martwe. Scena odpowiada na pytania, na które
    eksponat nie mógł: gdzie to jest i co się tu przed chwilą działo.
    """
    # GRAFIKA NIGDY NIE ZABIJA ARTYKUŁU. Zasada właściciela mówi wprost: gdy
    # temat jest wybrany, a research zrobiony i opłacony, artykuł MUSI powstać.
    # Nagłówek jest ozdobą, artykuł produktem — więc gdy zabraknie budżetu na
    # obraz albo padnie OpenAI, wychodzi artykuł bez grafiki, a nie nic.
    try:
        prompt = _prompt(
            "grafika.md",
            title=draft.get("title", ""),
            body=draft.get("body", "")[:6000],
        )
        brief = llm.parse_json(
            llm.call("grafika", IMAGE_SYSTEM, prompt, conn=conn, run_id=run_id)
        )
        opis = brief.get("prompt") or ""
        if not opis:
            raise ValueError("brief graficzny bez promptu")
        print(f"  [grafika] przedmiot: {brief.get('subject', '')}", flush=True)

        dane = llm.obraz(opis, conn=conn, run_id=run_id)
    except Exception as exc:
        # TREŚĆ wyjątku, nie sama nazwa klasy. Gdy grafika artykułu padła
        # na `IntegrityError`, log powiedział tylko tyle — a przyczyna („NOT NULL
        # constraint failed: calls.cache_hit") siedziała w zjedzonym komunikacie
        # i trzeba jej było szukać po kodzie. Awaria, która nie mówi na co padła,
        # kosztuje drugi raz.
        print(f"  [grafika] NIE POWSTAŁA ({type(exc).__name__}: {exc}) — "
              f"artykuł wychodzi bez nagłówka", flush=True)
        return {"blad": f"{type(exc).__name__}: {exc}"[:200]}
    if not dane:
        return brief   # DRY_RUN
    cel = (sciezka_artykulu.with_suffix(".png") if sciezka_artykulu
           else config.ARTICLES_DIR / f"{run_id:04d}-naglowek.png")
    # ZAPIS TEZ POD OSLONA — bez tego obietnica u gory („GRAFIKA NIGDY NIE
    # ZABIJA ARTYKULU") byla nieprawdziwa. Osloniete bylo generowanie obrazka,
    # a `mkdir` i `write_bytes` stały POZA `try`, wiec pelny dysk albo brak
    # praw leczial na wylot i zatrzymywal przebieg PRZED publikacja — czyli
    # brak czterech centow na obrazek wyrzucal do kosza research za czterdziesci
    # dolarow, dokladnie to, czemu ta oslona mial zapobiegac.
    # Znalezione 1 wrzesnia 2026 niezaleznym odczytem kodu, nie testem.
    try:
        cel.parent.mkdir(parents=True, exist_ok=True)
        cel.write_bytes(dane)
    except OSError as exc:
        print(f"  [grafika] NIE ZAPISANA ({type(exc).__name__}: {exc}) — "
              f"artykuł wychodzi bez nagłówka", flush=True)
        return {"blad": f"{type(exc).__name__}: {exc}"[:200]}
    brief["plik"] = str(cel)
    print(f"  [grafika] zapisana: {cel.name}  {len(dane) // 1024} KB", flush=True)
    return brief
```

<!--KOD:gates.deterministic_floors-->
```python
def deterministic_floors(body: str, card: dict[str, Any],
                         poprzednie: list[str] | None = None
                         ) -> list[dict[str, str]]:
    """Podłogi bez modelu: 0 USD, milisekundy, zero wywołań.

    `poprzednie` to treści kilku ostatnich artykułów — potrzebne wyłącznie
    bramce `ODCISK_FORMY`. Bez nich reszta działa jak dotąd, więc stary
    sposób wywołania nadal jest poprawny.
    """
    findings: list[dict[str, str]] = []

    for match in FABRICATED_EXPERIENCE.finditer(body):
        findings.append({
            "gate": "ZMYSLONE_PRZEZYCIE",
            "detail": body[max(0, match.start() - 60):match.end() + 60].strip(),
        })
    for match in VAGUE_STUDY.finditer(body):
        findings.append({
            "gate": "NIEISTNIEJACE_BADANIE",
            "detail": body[max(0, match.start() - 60):match.end() + 60].strip(),
        })
    # DWIE UWAGI, NIE JEDNA. Liczba z faktu z puli NIE jest zmyślona — stoi w
    # rekordzie, który ma URL i datę i przeszedł bramkę świeżości. Nie jest
    # jednak w niczym, co pobraliśmy. Wrzucenie jej do korpusu uciszało
    # kontrolę; wrzucenie jej pod `LICZBA_SPOZA_KORPUSU` kazałoby komunikatowi
    # kłamać („nie występuje w materiale dowodowym"). Własna uwaga mówi prawdę
    # i podpowiada, co z nią zrobić.
    _z_puli = _digit_tokens(json.dumps(_niepobrane(card), ensure_ascii=False))
    for token in numbers_outside_corpus(body, card):
        if token in _z_puli:
            findings.append({
                "gate": "LICZBA_TYLKO_Z_PULI",
                "detail": (f"liczba {token!r} stoi wyłącznie na fakcie z puli "
                           "— tego dokumentu nikt nie pobrał, sprawdź ją w źródle"),
            })
        else:
            findings.append({
                "gate": "LICZBA_SPOZA_KORPUSU",
                "detail": f"liczba {token!r} nie występuje w materiale dowodowym",
            })
    for fraza in frazy_z_instrukcji(body):
        findings.append({
            "gate": "FRAZA_Z_INSTRUKCJI",
            "detail": f"{fraza!r} — zdanie z promptu, nie z myślenia",
        })
    zapowiedz = zapowiedziany_akapit_granic(body)
    if zapowiedz:
        findings.append({
            "gate": "ZAPOWIEDZ_GRANIC",
            "detail": "akapit o granicach zapowiada sam siebie: %r" % zapowiedz,
        })
    ile, hosty = szerokosc_podstawy(card)
    if ile < 2:
        findings.append({
            "gate": "WASKA_PODSTAWA",
            "detail": (f"artykuł stoi na {ile} źródle ({', '.join(hosty) or 'brak'})"
                       " — czytelnik zobaczy jeden odnośnik pod tekstem"),
        })

    # --- podlogi z playbooka (2026-08-20) --------------------------------
    zastrz = zastrzezenia(body)
    if len(zastrz) > config.BUDZET_ZASTRZEZEN:
        findings.append({
            "gate": "BUDZET_ZASTRZEZEN",
            "detail": "%d zastrzeżeń przy budżecie %d: %s"
                      % (len(zastrz), config.BUDZET_ZASTRZEZEN,
                         ", ".join(repr(z) for z in zastrz[:6])),
        })
    for m in POWSCIAGLIWOSC.finditer(body):
        findings.append({
            "gate": "OBWIESZCZONA_POWSCIAGLIWOSC",
            "detail": "%r — lukę nazywa się wprost, bez zapowiadania cnoty"
                      % body[max(0, m.start() - 40):m.end() + 20].strip(),
        })
    otwarcie = zakazane_otwarcie(body)
    if otwarcie:
        findings.append({
            "gate": "ZAKAZANE_OTWARCIE",
            "detail": "każe czytelnikowi iść coś obejrzeć: %r" % otwarcie,
        })
    for zdanie in statystyki_bez_zrodla(body):
        findings.append({
            "gate": "STATYSTYKA_BEZ_ZRODLA",
            "detail": "liczba bez przypisu: %r" % zdanie,
        })
    granice = niewiadome_na_koncu(body)
    if granice:
        findings.append({
            "gate": "NIEWIADOME_NA_KONCU",
            "detail": "zbiorcza lista granic w ostatniej trzeciej — %s" % granice,
        })
    ksztalt = powtorzona_forma(body, poprzednie or [])
    if ksztalt:
        findings.append({"gate": "ODCISK_FORMY", "detail": ksztalt})
    return findings
```

<!--KOD:gates.uwagi_z_formy-->
```python
def uwagi_z_formy(obserwacja: dict[str, Any], body: str) -> list[dict[str, str]]:
    """Zamienia obserwacje modelu w uwagi. MODEL OBSERWUJE, KOD ROZSTRZYGA.

    Model oddaje cytaty i odpowiedzi tak/nie. Liczenie beatów, dzielenie przez
    długość i szukanie pozycji w tekście robimy tutaj, bo to arytmetyka, a
    arytmetyka modelu jest niesprawdzalna.

    JEDNA SWIADOMA ROZNICA WOBEC PLAYBOOKA. Playbook chce, zeby moment
    przylapania czytelnika stal miedzy 25 a 40 procentem glebokosci. Nie
    zglaszamy pozycji — zglaszamy wylacznie BRAK. Powod: regula nakazujaca
    pozycje wypelnia ja jedna odpowiedzia i po dziesieciu tekstach sama staje
    sie podpisem maszyny, a to jest dokladnie ta wada, ktora juz raz zrobilismy,
    naprawiajac tresc i zamawiajac przy okazji szkielet. Pozycje LICZYMY i
    zapisujemy jako informacje dla wlasciciela, ale nie jest wada.
    """
    uwagi: list[dict[str, str]] = []
    korpus = body.split(config.NAGLOWEK_ZRODEL)[0]
    slow = max(1, len(korpus.split()))

    przekonania = obserwacja.get("beliefs") or []
    wsparcie = obserwacja.get("support_only") or []
    if przekonania:
        na_beat = slow / max(1, len(przekonania))
        if na_beat > config.SLOW_NA_BEAT:
            powtorki = [str(w.get("quote", ""))[:70] for w in wsparcie]
            uwagi.append({
                "gate": "GESTOSC_BEATOW",
                "detail": ("%d przekonań na %d słów — jedno co %.0f słów "
                           "przy progu %d; samo wsparcie: %s"
                           % (len(przekonania), slow, na_beat,
                              config.SLOW_NA_BEAT,
                              " | ".join(powtorki[:3]) or "brak")),
            })

    if obserwacja.get("same_register") is True:
        twardy = (obserwacja.get("hardest_fact") or {}).get("quote", "")
        proceduralne = (obserwacja.get("procedural_nearby") or {}).get("quote", "")
        uwagi.append({
            "gate": "BRAK_ESKALACJI",
            "detail": ("najmocniejszy fakt idzie tym samym tonem co szczegół "
                       "proceduralny — %r obok %r"
                       % (twardy[:80], proceduralne[:70])),
        })

    moment = obserwacja.get("reader_moment")
    if not moment or not (moment or {}).get("quote"):
        uwagi.append({
            # TRESC KOMUNIKATU OPISYWALA KONTRAKT, KTOREGO JUZ NIE MA.
            # `forma.md` przestal wymagac fizycznego przedmiotu („It does not
            # have to be a thing they can pick up"), bo w wielu niszach wiekszosc
            # artykulow zadnego nie ma; bramka sprawdza wylacznie obecnosc
            # `quote`. Zachowanie sie nie zmienilo, ale wlasciciel czytajacy
            # `.uwagi.md` dostawal opis reguly z epoki przedmiotow.
            "gate": "CZYTELNIK_NIEPRZYLAPANY",
            "detail": ("nigdzie nie ma zwrotu do TEGO czytelnika z jedna "
                       "rzecza z jego wlasnego zycia — odpowiedz, ktora dostal, "
                       "cena, ktora zaplacil, decyzja o nim; statystyka o "
                       "innych to nie to"),
        })

    otwarcie = obserwacja.get("opening_claim") or {}
    if otwarcie.get("already_familiar"):
        uwagi.append({
            "gate": "OTWARCIE_ZNANE",
            "detail": ("pierwszy akapit stoi na twierdzeniu, które czytelnik "
                       "zna: %r" % str(otwarcie.get("quote", ""))[:90]),
        })
    return uwagi
```

<!--KOD:gates.odcisk_formy-->
```python
def odcisk_formy(body: str) -> dict[str, Any]:
    """Zgrubny szkielet tekstu — do porownania z poprzednimi, nie do oceny.

    Cechy sa CELOWO zgrubne. Nie chodzi o to, zeby dwa teksty roznily sie
    w szczegolach, tylko zeby nie mialy tego samego ksztaltu: tego samego
    otwarcia, tego samego miejsca na zwrot do czytelnika, tej samej dlugosci
    i tego samego rozkladu akapitow.

    Powod istnienia tej funkcji: dokladamy kilkadziesiat regul dotyczacych
    formy. Kazda z osobna poprawia tekst, wszystkie razem moga wyprodukowac
    szablon — a to jest ta sama wada, ktora juz raz zrobilismy, naprawiajac
    tresc i zamawiajac przy okazji szkielet.
    """
    korpus = body.split(config.NAGLOWEK_ZRODEL)[0]
    akapity = _akapity(body)
    slowa = korpus.split()

    def kubelek(u: float | None) -> str:
        if u is None:
            return "brak"
        return ("0-25", "25-50", "50-75", "75-100")[min(3, int(u * 4))]

    # WZORZEC Z REJESTRU, NIE WPISANY. Stalo tu `r"\byou(r)?\b"` — angielszczyzna
    # na sztywno w module, ktorego wszystkie pozostale wzorce ida przez
    # `jezyki.wzorzec(..., config.ARTICLE_LANGUAGE)`. Przy innym jezyku ta cecha
    # przyjmowala „brak" DLA KAZDEGO tekstu, a cecha stala zgadza sie zawsze:
    # `powtorzona_forma` wymaga pieciu z szesciu wlasnie dlatego, ze „cztery
    # zdarzaja sie przypadkiem", wiec faktyczny prog spadal do czterech
    # z pieciu prawdziwych cech.
    #
    # `jezyki.brakujace()` nie mialo jak tego zauwazyc: porownuje jezyki
    # z angielskim SPISEM, a tego wzorca w spisie nie bylo. Straznik dawal
    # zielone swiatlo o sobie samym.
    ty = ZWROT_DO_CZYTELNIKA.search(korpus)
    granice = niewiadome_na_koncu(body)

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

<!--KOD:gates.powtorzona_forma-->
```python
def powtorzona_forma(body: str, poprzednie: list[str],
                     prog: int = 5) -> str:
    """Czy ten tekst ma ksztalt ktoregos z poprzednich.

    `prog` to ile z szesciu cech musi sie zgodzic, zeby uznac ksztalt za
    powtorzony. Piec z szesciu, bo cztery zdarzaja sie przypadkiem przy
    tak zgrubnych kubelkach, a szesc zlapaloby dopiero blizniaka.
    """
    if not poprzednie:
        return ""
    moj = odcisk_formy(body)
    najlepsze, ktory = 0, -1
    trzon = " ".join(body.split())
    for i, inny in enumerate(poprzednie):
        # TEN SAM TEKST TO NIE POWTORZONA FORMA, tylko ten sam plik. W
        # przebiegu bramka woła się przed zapisem, więc do porównania nie
        # trafia — ale opieranie poprawności na kolejności dwóch linijek
        # w innym module jest za cienkie. Przy pierwszym uruchomieniu na
        # zapisanym już artykule wychodzi 6 z 6 cech i wygląda jak alarm.
        if " ".join(inny.split()) == trzon:
            continue
        wspolne = sum(1 for k, v in moj.items() if odcisk_formy(inny).get(k) == v)
        if wspolne > najlepsze:
            najlepsze, ktory = wspolne, i
    if najlepsze < prog:
        return ""
    return ("ten sam szkielet co %d. z ostatnich tekstów — %d z %d cech "
            "wspólnych (%s)" % (ktory + 1, najlepsze, len(moj),
                                ", ".join("%s=%s" % (k, v) for k, v in moj.items())))
```

<!--KOD:gates.zapowiedziany_akapit_granic-->
```python
def zapowiedziany_akapit_granic(body: str) -> str:
    """Czy akapit o granicach zaczyna sie od zdania o samym sobie.

    Zakazywanie konkretnych fraz nie dziala: przy kazdym zakazie nastepny
    artykul znajdowal nowy sposob na to samo. Trzy zaobserwowane warianty
    tej samej wady, kolejno: „a few things this evidence does not settle",
    „what the record here does not establish deserves saying once",
    „what the regulation and the proposed rule leave open is worth stating
    plainly".

    Wiec sprawdzamy STRUKTURE: zdanie otwierajace akapit, ktory wylicza
    granice, ma zaczynac sie od granicy, nie od zapowiedzi. Szukamy akapitow
    mowiacych o tym, czego zapis NIE ustala, i patrzymy na ich pierwsze zdanie.
    """
    for akapit in re.split(r"\n\s*\n", body):
        a = akapit.strip()
        if len(a.split()) < 25:
            continue
        # Czy to w ogole akapit o granicach.
        niski = a.lower()
        if not any(z in niski for z in ("does not", "do not", "not establish",
                                        "leaves open", "not settled", "nothing here")):
            continue
        pierwsze = re.split(r"(?<=[.!?])\s+", a)[0]
        # Tylko POCZATEK zdania. Zdanie moze legalnie wspomniec o zapisie
        # w drugiej polowie — "converting it into minutes is the reader's
        # invention, not the record's" jest poprawne i konkretne. Wada polega
        # na tym, ze zdanie ZACZYNA sie od mowienia o akapicie.
        poczatek = " ".join(pierwsze.lower().split()[:10])
        if any(w in poczatek for w in _META_GRANIC):
            return pierwsze[:150]
    return ""
```

<!--KOD:gates.frazy_z_instrukcji-->
```python
def frazy_z_instrukcji(body: str, dlugosc: int = 6) -> list[str]:
    """Czy pisarz wklein do tekstu wlasne polecenie.

    W jednym z tekstow wyszlo „in the simplest sentence that is still true" — dokladnie
    tak, jak stoi w `pisarz.md`. Czytelnik tego nie rozpozna, ale to nie jest
    zdanie z myslenia, tylko echo instrukcji, i wracajac w kolejnych tekstach
    staje sie podpisem maszyny.

    Porownujemy ciagi szesciu slow. Prompt to sam metatekst, wiec kazde takie
    pokrycie jest przeciekiem, nie zbiegiem okolicznosci — a sprawdzenie samo
    sie utrzymuje, gdy prompt sie zmieni.
    """
    def slowa_z(tekst: str) -> list[str]:
        r"""Slowa tekstu — LITERY W SENSIE UNICODE, nie alfabet angielski.

        Stalo tu `[a-z]+`. W jezyku z diakrytykami kazda litera z ogonkiem
        rozcinala slowo na dwa kawalki — w prompcie i w tekscie w INNYCH
        miejscach — wiec ciagi szesciu slow przestawaly sie zgadzac i bramka
        nie zglaszala juz NICZEGO. Ta sama cicha awaria, dla ktorej powstal
        `jezyki.py`; ten wzorzec siedzial w `re.findall`, wiec ani rejestr,
        ani straznik wzorcow go nie widzial.

        `[^\W\d_]+` znaczy „ciag liter": bez cyfr, bez podkreslenia, bez
        interpunkcji, ZE wszystkimi alfabetami. Dla angielskiego po `lower()`
        daje dokladnie to samo, co `[a-z]+`.
        """
        return re.findall(r"[^\W\d_]+", tekst.lower(), re.UNICODE)

    def ciagi(slowa: list[str]) -> list[tuple[str, ...]]:
        return [tuple(slowa[i:i + dlugosc])
                for i in range(len(slowa) - dlugosc + 1)]

    try:
        instrukcja = (config.PROMPTS_DIR / "pisarz.md").read_text(encoding="utf-8")
    except OSError:
        return []
    z_promptu = set(ciagi(slowa_z(instrukcja)))
    slowa = slowa_z(body)
    trafione = [i for i, c in enumerate(ciagi(slowa)) if c in z_promptu]

    # Jedna wklejka daje kilka zachodzacych na siebie ciagow. Skladamy je
    # z powrotem w jedna, najdluzsza fraze — inaczej jeden blad wyglada jak piec.
    trafienia: list[str] = []
    i = 0
    while i < len(trafione):
        koniec = i
        while koniec + 1 < len(trafione) and trafione[koniec + 1] == trafione[koniec] + 1:
            koniec += 1
        fraza = " ".join(slowa[trafione[i]:trafione[koniec] + dlugosc])
        if fraza not in trafienia:
            trafienia.append(fraza)
        i = koniec + 1
    return trafienia
```

<!--KOD:run.rytm-->
```python
def rytm(co: str, na_co: str, stan: dict) -> bool:
    """Przerwa MIEDZY dwoma dzialaniami tego samego rodzaju.

    Trzeci raz ta sama wada, tym razem zamknieta w jednym miejscu dla wszystkich
    blokow. Przerwa byla odsypiana PO dzialaniu, wiec:

      1. po OSTATNIEJ notce w bloku agent spal jeszcze 45-90 minut, choc nie
         mial juz czego robic — to jest dokladnie ta sama usterka, ktora
         naprawilem wczesniej dla restackow i ktorej wtedy nie poszukalem
         nigdzie indziej;
      2. sen zaczynal sie BEZ pytania, czy sie zmiesci. `zostal_czas` mowilo
         tylko „czy zostala jakakolwiek sekunda", wiec przepuszczalo
         dziewiecdziesieciominutowa przerwe przy dwudziestu minutach na zegarze.

    Teraz przerwa jest najpierw losowana, potem sprawdzana wobec konca
    przebiegu, i dopiero wtedy odsypiana — a pierwsze dzialanie w przebiegu nie
    czeka na nic, bo nie ma na co.

    Ta sama funkcja trzyma HAMULEC po serii porazek, liczony PER BLOK (`na_co`),
    nie per rodzaj dzialania — patrz `_BAZA_HAMULCA` i `_pod_rzad_w_bloku`.
    """
    import stages as _s

    # BAZA HAMULCA ZAPISUJE SIE TU, PRZED wczesnym wyjsciem — patrz
    # `_pod_rzad_w_bloku`. Blok ma liczyc od stanu, w jakim go zastal, a nie od
    # stanu po swojej wlasnej pierwszej probie.
    pod_rzad = _pod_rzad_w_bloku(co, na_co)

    if not stan.get(co):
        return zostal_czas(na_co)
    przerwa = _s.losuj_odstep(co)

    # WYCOFANIE PO SERII PORAZEK — reakcja W TRAKCIE, nie dopiero w analizie.
    #
    # Zmierzone 30 sierpnia na sciezce notkowej: pierwsza akcja w serii psula
    # sie w 10 procentach, druga w 31, czwarta w 50. Przy takim rozkladzie
    # czwarta proba pod rzad jest rzutem moneta za oplacony tekst, a przebieg
    # szedl dalej, bo nikt nie liczyl porazek POD RZAD.
    #
    # Dwie z rzedu: podwajamy przerwe. Tempo jest jedyna zmienna, ktora
    # pokrywa sie z awaryjnoscia, wiec zwolnienie jest jedyna rzecza, ktora
    # mozemy zrobic natychmiast i bez zgadywania przyczyny.
    # Trzy z rzedu: konczymy ten blok. Nie kasujemy dnia — kolejny przebieg
    # zaczyna z czystym licznikiem i moze sie okazac, ze to bylo chwilowe.
    if pod_rzad >= 3:
        print("  [wycofanie] %s: trzy porazki pod rzad — koncze blok %s,"
              " nastepny przebieg sprobuje od nowa" % (co, na_co), flush=True)
        return False
    if pod_rzad >= 2:
        przerwa *= 2
        print("  [wycofanie] %s: dwie porazki pod rzad — przerwa %.0f min"
              " zamiast zwyklej" % (co, przerwa / 60), flush=True)

    if not zostal_czas(na_co, przerwa):
        return False
    _s.odczekaj(co, przerwa)
    return True
```

<!--KOD:run.zmiesci_sie-->
```python
def zmiesci_sie(rodzaj: str, ile: int, udzial: float = 1.0) -> int:
    """Ile z zaplanowanych dzialan NAPRAWDE zmiesci sie w czasie przebiegu.

    Rozdzielnik dzielil dzienna norme, nie patrzac na zegar. Po wydluzeniu
    odstepow miedzy notkami do 45-90 minut wieczorna rutyna dostala cztery notki
    — od trzech do szesciu godzin samego czekania przy budzecie 2h15. Zdazyla
    jedna i do komentarzy nie doszla w ogole.

    Obietnica, ktorej nie da sie dotrzymac, jest gorsza od mniejszej: blokuje
    reszte przebiegu. Lepiej wystawic dwie notki i czternascie komentarzy niz
    obiecac cztery notki i nie zrobic nic poza jedna.
    """
    import time

    if _KONIEC_CZASU is None or ile <= 0:
        return ile
    dol, gora = config.ODSTEPY.get(rodzaj, config.ODSTEP_MIEDZY_DZIALANIAMI)
    odstep = (dol + gora) / 2
    zostalo = max(0.0, _KONIEC_CZASU - time.time()) * udzial

    # PRZERW JEST O JEDNA MNIEJ NIZ DZIALAN. Przy dwoch notkach czekamy raz, nie
    # dwa — pierwsza wersja liczyla przerwe po kazdej i wychodzilo o polowe za malo.
    def potrzeba(n: int) -> float:
        return n * config.CZAS_DZIALANIA_S + max(0, n - 1) * odstep

    mozliwe = ile
    while mozliwe > 0 and potrzeba(mozliwe) > zostalo:
        mozliwe -= 1
    if mozliwe < ile:
        print(f"  [czas] {rodzaj}: {ile} sie nie zmiesci, biore {mozliwe}"
              f" (odstep ~{odstep / 60:.0f} min, zostalo {zostalo / 60:.0f} min)",
              flush=True)
    return mozliwe
```

<!--KOD:run.zostal_czas-->
```python
def zostal_czas(na_co: str = "", potrzeba_s: float = 0.0) -> bool:
    """Czy zdazymy jeszcze cokolwiek zrobic przed koncem czasu przebiegu.

    Systemd tnie przebieg po `TimeoutStartSec` i robi to SIGTERM-em w dowolnym
    momencie — takze w polowie wpisywania komentarza. Zdarzylo sie naprawde:
    przebieg z szesnastoma komentarzami do wystawienia zostal ubity po 2,5 h.
    Lepiej skonczyc dzien krocej niz zostac przerwanym w srodku dzialania,
    ktorego nie da sie cofnac.
    """
    import time

    if _KONIEC_CZASU is None:
        return True
    zostalo = _KONIEC_CZASU - time.time()
    if zostalo > potrzeba_s:
        return True
    if potrzeba_s:
        print(f"  czas przebiegu wyczerpany — odpuszczam {na_co or 'reszte'}"
              f" (przerwa {potrzeba_s / 60:.0f} min nie zmiesci sie"
              f" w {max(0.0, zostalo) / 60:.0f} min; dokoncze w nastepnym"
              f" przebiegu)", flush=True)
    else:
        print(f"  czas przebiegu wyczerpany — odpuszczam {na_co or 'reszte'}"
              f" (dokoncze w nastepnym przebiegu)", flush=True)
    return False
```

<!--KOD:run.zajmij_zamek-->
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

<!--KOD:run.odmow_publikacji_z_kopii-->
```python
def odmow_publikacji_z_kopii(wyslij: bool) -> None:
    """Kopia testowa nie ma prawa nic opublikowac. Nigdy.

    Wlasciciel: „nie odpalaj go na produkcji, wersja v2 ma byc jako test".
    Sama dyscyplina nie wystarczy — wystarczy raz dopisac `--wyslij` z pamieci
    miesnowej i eksperyment wyjdzie na zywe konto, czego nie da sie cofnac.
    Wiec kopia testowa nosi plik-znacznik obok `config.py`, a ten plik odbiera
    jej prawo publikowania. Produkcja znacznika nie ma i dziala normalnie.
    """
    if wyslij and ZNACZNIK_KOPII_TESTOWEJ.exists():
        raise SystemExit(
            "ODMOWA: to jest kopia testowa (%s), a --wyslij publikuje NA ZYWO. "
            "Produkcja stoi w ~/nia-substack-bot na galezi main. "
            "Jesli naprawde chcesz publikowac stad, usun ten plik swiadomie."
            % ZNACZNIK_KOPII_TESTOWEJ
        )
```

<!--KOD:browser._klik_na_profilu-->
```python
def _klik_na_profilu(handle: str, napisy: tuple[str, ...], rodzaj: str,
                     wyslij: bool) -> dict[str, Any]:
    """Klika JEDEN konkretny przycisk na cudzym profilu — i tylko jego.

    OBSERWOWANIE I SUBSKRYPCJA TO DWIE ROZNE RZECZY. Obserwowanie sprawia, ze
    czyjes notki pojawiaja sie w naszym kanale; subskrypcja przysyla jego teksty
    MAILEM do skrzynki wlasciciela. Biezace widelki sa osobne: 10-16 obserwacji
    miesiecznie i 12-20 subskrypcji.

    Jedna funkcja probowala kolejno „Subscribe", „Subskrybuj", „Follow",
    „Obserwuj" i brala pierwszy znaleziony. Na profilu Substacka „Subscribe" jest
    zawsze, wiec do „Follow" nie dochodzilo NIGDY — kazda z czterech prob
    w logach kliknela subskrypcje. Agent subskrybowal w tempie obserwacji.

    Gdy wlasciwego przycisku nie ma, nie robimy NIC. Klikniecie „w zastepstwie"
    to dokladnie ten blad, ktory to spowodowal.

    TA FUNKCJA OBSLUGUJE JUZ TYLKO SUBSKRYPCJE. Rozdzielenie napisow bylo
    konieczne, ale NIEWYSTARCZAJACE: obserwowania nie da sie tu zrobic zadnym
    zestawem napisow, bo przycisku obserwowania NIE MA na wierzchu strony —
    siedzi w menu pod kolkiem „...". Zmierzone 1 wrzesnia 2026: w naglowku
    profilu sa dokladnie trzy przyciski — „Subscribe", „Message" i kolko
    z `aria-label="Profile actions"`. Obserwowanie ma wiec wlasna droge,
    patrz `obserwuj_profil`.
    """
    wyslij = naprawde_wyslac(wyslij, rodzaj)
    wymagaj_sesji()
    p, browser, context = podlacz_sie()
    page = context.new_page()
    wynik: dict[str, Any] = {"handle": handle, "zrobione": False, "blad": None}
    try:
        # NIE TO KONTO = NIE KLIKAMY. `zasubskrybuj` idzie ta droga
        # i jako jedyne wejscie wystawiajace nie mialo straznika —
        # zlapal to `test_straznik_konta.py`, ktory liste wejsc
        # WYPROWADZA z `bramki.WYSTAWIENIA` zamiast ja wypisywac.
        if wyslij:
            wymagaj_wlasciwego_konta(page)
        page.goto(f"https://substack.com/@{handle}", timeout=READ_TIMEOUT_MS * 2,
                  wait_until="domcontentloaded")
        page.wait_for_timeout(SETTLE_MS + 4000)
        for nazwa in napisy:
            k = page.get_by_role("button", name=nazwa, exact=True).first
            if k.count() == 0 or not k.is_visible():
                continue
            print(f"  przycisk: {nazwa!r}  ({rodzaj})", flush=True)
            if not wyslij:
                print("  (nie klikam — tryb sprawdzenia)", flush=True)
                return wynik
            k.click(timeout=10_000)
            page.wait_for_timeout(5000)
            # Po kliknieciu napis zmienia sie na stan przeciwny.
            wynik["zrobione"] = k.count() == 0 or not k.is_visible()
            dopisz_wynik(rodzaj, wynik, komu=handle)
            print("  ZROBIONE" if wynik["zrobione"]
                  else "  KLIKNIETE, ALE STAN SIE NIE ZMIENIL", flush=True)
            return wynik
        wynik["blad"] = f"nie ma przycisku {rodzaj} u {handle}"
        print(f"  {wynik['blad']} — nie klikam nic innego", flush=True)
    except Exception as exc:
        wynik["blad"] = f"{type(exc).__name__}: {exc}"[:200]
        print(f"  BŁĄD: {wynik['blad']}", flush=True)
    finally:
        # BRAK PRZYCISKU TO TEZ WYNIK i musi zostawic slad. Bez tego blok
        # obserwacji, ktory nie znalazl ani jednego przycisku „Follow" przez
        # siedem dni, wygladal w dzienniku jak blok, ktory sie nie odbyl —
        # a on sie odbywal, chodzil po profilach i za kazdym razem odchodzil
        # z pustymi rekami. Tego nie da sie naprawic, czego nie widac.
        if wyslij:
            dopisz_wynik(rodzaj, wynik, komu=handle)
        page.close()
        browser.close()
        p.stop()
    return wynik
```

<!--KOD:browser.restackuj_w_kanale-->
```python
def restackuj_w_kanale(
    ile: int, decyzja, wyslij: bool = False,
) -> dict[str, Any]:
    """Podaje dalej cudze notki z wlasnym zdaniem.

    `decyzja` to funkcja (notka: dict) -> dict, ktora oddaje
    {"restack": bool, "sentence": str, "reason": str}. Decyzja siedzi POZA ta
    funkcja, bo tu jest tylko klikanie — a o tym, czy warto, decyduje etap
    `stages.ocen_restack`, ktory da sie przetestowac bez przegladarki.

    Sciezka ustalona na zywym Substacku, nie zgadnieta:
      przycisk `Restack` ma aria-haspopup="menu", wiec NIE restackuje od razu,
      tylko rozwija menu z pozycjami `Restack`, `Restack with a note`
      i `View restacks`. Bierzemy druga — samo podanie dalej bez zdania nic
      nie wnosi, a to zdanie jest calym sensem tej akcji.

    Odstepy sa dluzsze niz przy polubieniach (10-30 min), bo restack wymaga
    PRZECZYTANIA cudzej notki. Cztery restacki w dwie minuty to nie jest
    czytanie i widac to na profilu tak samo, jak widac bylo notki parami.
    """
    import random

    wyslij = naprawde_wyslac(wyslij, "restacki")
    wymagaj_sesji()
    p, browser, context = podlacz_sie()
    page = context.new_page()
    wynik: dict[str, Any] = {"znalezione": 0, "rozwazone": 0, "restackowane": 0,
                             "odmowy": [], "blad": None}
    try:
        # NIE TO KONTO = NIE WYSTAWIAMY. Straznik `wlasciwe_konto`
        # istnial od poczatku, opisany jako kontrola tuz przed
        # publikacja, i NIE BYL WOLANY ANI RAZU — sprawdzone skanem
        # po calym drzewie. Raz na proces, tylko przy wysylce.
        #
        # WEWNATRZ `try`, nie nad nim: `finally` zamyka strone,
        # przegladarke i Playwrighta, a wyjatek rzucony wyzej
        # zostawilby proces Chromium przy zyciu.
        if wyslij:
            wymagaj_wlasciwego_konta(page)
        page.goto("https://substack.com/", timeout=READ_TIMEOUT_MS * 2,
                  wait_until="domcontentloaded")
        page.wait_for_timeout(SETTLE_MS + 6000)

        przyciski = page.get_by_role("button", name="Restack")
        wynik["znalezione"] = przyciski.count()
        print(f"  notek w kanale do rozwazenia: {wynik['znalezione']}", flush=True)

        for i in range(min(ile * 4, przyciski.count())):
            if wynik["restackowane"] >= ile:
                break
            kandydat = przyciski.nth(i)
            try:
                if not kandydat.is_visible():
                    continue
                # Tresc notki bierzemy z KONTENERA wokol przycisku. Bez niej
                # decyzja bylaby losowaniem, a nie ocena.
                notka = _notka_przy_przycisku(kandydat)
                if not notka.get("tekst"):
                    continue
                wynik["rozwazone"] += 1
                ocena = decyzja(notka)
                if not ocena.get("restack"):
                    powod = str(ocena.get("reason", ""))[:90]
                    wynik["odmowy"].append(powod)
                    print(f"    pomijam: {powod}", flush=True)
                    continue

                zdanie = ocena["sentence"]
                print(f"    RESTACK u {notka.get('autor', '?')[:24]}: {zdanie[:90]}",
                      flush=True)
                if not wyslij:
                    wynik["restackowane"] += 1
                    continue

                # ODSTEP STOI PRZED KOLEJNYM RESTACKIEM, NIE PO POPRZEDNIM.
                # Wczesniej czekalo sie na koncu ciala petli, a warunek wyjscia
                # sprawdza sie dopiero na gorze nastepnego obrotu — wiec agent
                # po wykonaniu normy spal jeszcze 10-30 minut z otwarta
                # przegladarka i dopiero wtedy wychodzil. Przy limicie jednego
                # restacka na przebieg, czyli w typowym przypadku, kazda taka
                # przerwa byla pusta w calosci.
                #
                # Samo „przerwij po wykonaniu normy" NIE WYSTARCZALO i zlapal to
                # dopiero test: gdy w kanale bylo mniej notek niz wynosil budzet,
                # norma nie byla wykonana, wiec petla i tak zasypiala, a zaraz
                # potem konczyla sie z braku kandydatow. Odstep postawiony PRZED
                # dziala w obu przypadkach, bo czeka tylko ten, kto naprawde ma
                # zaraz kliknac.
                if wynik["restackowane"]:
                    page.wait_for_timeout(
                        int(random.uniform(*config.ODSTEPY["restack"]) * 1000))

                kandydat.scroll_into_view_if_needed(timeout=8000)
                kandydat.click(timeout=8000)
                page.wait_for_timeout(1500)
                page.get_by_role("menuitem", name="Restack with a note").click(
                    timeout=8000)
                page.wait_for_timeout(SETTLE_MS)
                pole = page.get_by_role("textbox").last
                pole.click(timeout=8000)
                pole.type(zdanie, delay=random.randint(18, 45))
                page.wait_for_timeout(1200)
                # Substack nazywa przycisk wyslania "Post" — szukamy go
                # WEWNATRZ okna, nie w calym kanale, zeby nie trafic w cudzy.
                page.get_by_role("button", name="Post").last.click(timeout=8000)
                page.wait_for_timeout(SETTLE_MS + 2000)
                wynik["restackowane"] += 1
                # Restack tworzy NOWA notke z wlasnym numerem. Bez niego
                # restack byl jedyna forma publikacji, ktorej nie dalo sie
                # zmierzyc — a to najcenniejszy sygnal, jaki mamy: w badaniu
                # 9 641 notek restack konwertowal dwunastokrotnie lepiej niz
                # polubienie.
                numer_restacka = ""
                try:
                    numer_restacka = numer_naszej_notki(page, zdanie, prob=2)
                except Exception:
                    pass
                # OTWARTE, SWIADOMIE NIETKNIETE: `udane=True` ponizej opiera sie
                # na samym lancuchu klikniec, a nie na potwierdzeniu. To jest ta
                # sama doktryna „klikniecie nie jest dowodem", ktora obowiazuje
                # przy komentarzu, notce, odpowiedzi i — od 31 sierpnia — przy
                # polubieniu. Restack zostaje jedynym dzialaniem, ktore jej nie
                # przestrzega, i wiem o tym.
                #
                # DLACZEGO NIE ZAMYKAM TEGO TERAZ. Jedyny sygnal, jaki mam pod
                # reka, to `numer_restacka` — i on juz jest w dzienniku, w polu
                # `id`. Pusty `id` znaczy tylko tyle, ze nie odnalazlem notki na
                # profilu przy `prob=2`, czyli w dwoch podejsciach z jedna
                # osmiosekundowa przerwa. Jak zawodny jest taki odczyt, wiadomo
                # z pomiaru poprzedniego mechanizmu: `id_z_odpowiedzi` trafil
                # numer 6 razy na 29 notek. Gdybym na tej podstawie postawil
                # `udane=False`, restacki masowo znikalyby z licznika, a licznik
                # z dziennika jest dla nich jedyny — Substack nie oddaje ich
                # zadnym endpointem. Falszywe „nie udalo sie" kosztuje tu cala
                # dzienna norme, falszywe „udalo sie" jeden slot (patrz
                # `potwierdz_polubienie`), wiec zgadywanie jest drozsze niz
                # opisane ryzyko.
                #
                # CO ZAMKNELOBY SPRAWE: policzyc na produkcji, w ilu wpisach
                # `restack` pole `id` jest niepuste. Jesli wychodzi blisko 100
                # procent, `id` nadaje sie na warunek i wtedy — dopiero wtedy —
                # `udane` powinno od niego zalezec. Nie zgaduje, jak Substack
                # nazywa stan przycisku po restacku, i nie ruszam tego bez tej
                # liczby.
                zapisz_w_dzienniku("restack", udane=True,
                                   komu=notka.get("autor", ""),
                                   slow=len(zdanie.split()),
                                   tekst=zdanie[:300], id=numer_restacka)
                print(f"    podane dalej {wynik['restackowane']}/{ile}", flush=True)
            except Exception as exc:
                # Tak samo jak przy polubieniach: porazka szla do logu i nigdzie
                # indziej. Restacki chodza na 33% normy — bez tego wpisu nie ma
                # jak stwierdzic, czy to brak kandydatow w kanale, czy zmieniony
                # interfejs Substacka.
                powod = f"{type(exc).__name__}: {exc}"[:140]
                print(f"    (pominiete: {type(exc).__name__}: {exc}"[:150] + ")",
                      flush=True)
                zapisz_w_dzienniku("restack", udane=False, powod=powod,
                                   komu=notka.get("autor", ""))
                try:
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(600)
                except Exception:
                    pass
        if not wyslij:
            print(f"  (nie klikam — tryb sprawdzenia; podalbym dalej"
                  f" {wynik['restackowane']})", flush=True)
    except Exception as exc:
        wynik["blad"] = f"{type(exc).__name__}: {exc}"[:200]
        print(f"  BŁĄD: {wynik['blad']}", flush=True)
    finally:
        page.close()
        browser.close()
        p.stop()
    return wynik
```

<!--KOD:browser.wypelnij_artykul-->
```python
def wypelnij_artykul(page, artykul: dict[str, Any], obraz: Path | None) -> None:
    """Wkłada tytuł, podtytuł, grafikę i treść do otwartego edytora.

    Grafika idzie W TREŚĆ, na samą górę — tak, jak robi to właściciel ręcznie.
    Szukałem osobnego slotu okładki i była to droga naokoło: obraz wklejony do
    treści edytor sam wysyła na swój serwer i sam robi z niego podgląd.
    """
    import base64

    page.locator("textarea.page-title").first.fill(artykul["tytul"])
    page.wait_for_timeout(400)
    if artykul.get("podtytul"):
        page.locator("textarea.subtitle").first.fill(artykul["podtytul"])
        page.wait_for_timeout(400)

    edytor = page.locator(".tiptap").first
    edytor.click()
    page.wait_for_timeout(400)
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    page.wait_for_timeout(400)

    # Treść wklejamy jako HTML, nie wpisujemy: ProseMirror gubi przy wpisywaniu
    # linki w źródłach, a nazwane źródła to obietnica z oświadczenia o AI.
    page.evaluate(_JS_WKLEJ_HTML, [artykul["html"]])
    page.wait_for_timeout(3000)
    print(f"  wklejona treść: {len(edytor.inner_text().split())} słów, "
          f"{page.locator('.tiptap a').count()} węzłów linkowych", flush=True)

    if obraz and obraz.exists():
        edytor.click()
        page.keyboard.press("Control+Home")
        page.wait_for_timeout(500)
        page.evaluate(_JS_WKLEJ_OBRAZ,
                      [base64.b64encode(obraz.read_bytes()).decode()])
        for _ in range(20):   # wysyłka na serwer Substacka trwa
            page.wait_for_timeout(1500)
            if page.locator(".tiptap img").count():
                break
        wgrany = page.locator(".tiptap img").count() > 0
        print(f"  grafika: {'wgrana' if wgrany else 'NIE WESZŁA'}", flush=True)

    wstaw_przycisk_subskrypcji(page)
```

<!--KOD:kanal._za_niedawno_u_nich-->
```python
def _za_niedawno_u_nich(post: dict) -> bool:
    """Czy komentowalismy u tej publikacji w ostatnich dniach."""
    from datetime import datetime, timedelta, timezone

    ostatnio = _historia().get(klucz_publikacji(post))
    if not ostatnio:
        return False
    try:
        kiedy = datetime.fromisoformat(ostatnio)
    except ValueError:
        return False
    return (datetime.now(timezone.utc) - kiedy) < timedelta(
        days=config.ODSTEP_DNI_NA_PUBLIKACJE)
```
