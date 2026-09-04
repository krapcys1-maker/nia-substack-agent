"""Jedyna warstwa miedzy `run.py` a dostawca.

Robi cztery rzeczy: sprawdza warunki przed platnym wywolaniem, wola model,
liczy koszt i zapisuje wywolanie. Bledy przejsciowe ponawia do limitu
`config.PONOWIENIA` (dzis 2, czyli najwyzej trzy proby); nadal nie ma
rezerwacji ani rekoncyliacji. Nazwa `LLM_RETRIES`, ktora stala tu wczesniej,
NIE ISTNIEJE w tym repozytorium — kto szedl ja sprawdzic, trafial wylacznie na
to zdanie. Jesli proces zginie
w polowie wywolania, koszt tej proby nie trafi do logu. Limit dzienny ogranicza
szkode.
"""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any

import anthropic
import httpx

import config
import db


class BudgetExceeded(RuntimeError):
    pass


class PreflightFailed(RuntimeError):
    pass


class Truncated(RuntimeError):
    """Odpowiedź ucięta na suficie tokenów — czytelnie, zamiast błędu JSON-a.

    Pierwszy test seryjny padł na `JSONDecodeError: Expecting ',' delimiter`
    w połowie odpowiedzi DeepSeeka. Przyczyna była o piętro wyżej: prompt prosił
    o więcej, niż mieścił sufit.
    """


def _dostawca(model: str) -> str:
    """Czyj to model. JEDNO miejsce, zeby nie rozjechalo sie z kontrola kluczy.

    Rozstrzyga po prefiksie identyfikatora, tak samo jak rozliczanie stawek
    nizej (`"deepseek" if model.startswith("deepseek") else "anthropic"`).
    Model nieznanego dostawcy oddaje pusty napis i NIE jest blokowany przez
    kontrole wstepna — swiadomie: lepiej dostac blad z API niz zablokowac
    dopisany model, o ktorym ta funkcja jeszcze nie wie.
    """
    if model.startswith("deepseek"):
        return "deepseek"
    if model.startswith("claude"):
        return "anthropic"
    if model.startswith("gpt-") or model.startswith("dall-"):
        return "openai"
    return ""


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


# Etapy, o ktorych juz powiedzielismy, ze ich EFFORT nie dziala.
_EFFORT_BEZ_SKUTKU: set[str] = set()

# Modele, o ktorych brakujacym wpisie w WEB_SEARCH_TOOL juz mowilismy.
_WYSZUKIWANIE_BEZ_WPISU: set[str] = set()


def _narzedzie_wyszukiwania(model: str) -> str:
    """Nazwa narzedzia wyszukiwania; ostrzega RAZ NA PROCES o braku wpisu."""
    nazwa, uwaga = config.narzedzie_wyszukiwania(model)
    if uwaga and model not in _WYSZUKIWANIE_BEZ_WPISU:
        _WYSZUKIWANIE_BEZ_WPISU.add(model)
        print("  [wyszukiwanie] %s" % uwaga, flush=True)
    return nazwa


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
    if model in (config.CLAUDE, config.SONNET):
        usd += web_searches / 1_000 * config.WEB_SEARCH_USD_PER_1K
    return round(usd, 6), bool(price["verified"])


def _log(purpose: str, model: str, tin: int, tout: int, searches: int, usd: float,
         verified: bool) -> None:
    flag = "" if verified else "  [STAWKA NIEPOTWIERDZONA]"
    print(
        f"  [{purpose}] {model}  wej={tin} wyj={tout}"
        f"{f' szukania={searches}' if searches else ''}"
        f"  ${usd:.4f}{flag}",
        flush=True,
    )


def _call_claude(
    purpose: str, system: str, user: str, web_search: bool
) -> tuple[str, int, int, int, list[str]]:
    model = config.MODEL_FOR[purpose]
    client = anthropic.Anthropic(
        api_key=config.ANTHROPIC_API_KEY,
        timeout=config.timeout_for(config.MAX_TOKENS[purpose]),
        max_retries=0,  # ponowienie płatnego wywołania to decyzja, nie domyślka
    )
    kwargs: dict[str, Any] = {
        "model": model,
        "max_tokens": config.MAX_TOKENS[purpose],
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }
    # `effort` istnieje na Opusie 5, Sonnecie 5 i Fable 5.
    if purpose in config.EFFORT and model in (config.CLAUDE, config.SONNET,
                                              config.FABLE):
        kwargs["output_config"] = {"effort": config.EFFORT[purpose]}
    if web_search:
        # max_uses JEST OBOWIĄZKOWE. Bez niego model robił 17, potem 31 rund
        # wyszukiwania, a każda runda przesyła całą rozmowę od nowa jako wejście
        # — 164 411 tokenów wejścia i $1,33 za jeden etap. Ograniczona liczba
        # wyszukiwań i tak zwraca dziesięć źródeł.
        kwargs["tools"] = [{
            "type": _narzedzie_wyszukiwania(model),
            "name": "web_search",
            "max_uses": config.DISCOVERY_MAX_SEARCHES,
        }]

    # Strumień zawsze: sufity są duże, a myślenie na Opusie 5 jest domyślnie
    # włączone i liczy się jak wyjście, więc bez strumienia grozi timeout HTTP.
    with client.messages.stream(**kwargs) as stream:
        message = stream.get_final_message()

    if message.stop_reason == "refusal":
        raise PreflightFailed(f"dostawca odmówił: {message.stop_details}")
    if message.stop_reason == "max_tokens":
        raise Truncated(
            f"odpowiedź ucięta na suficie {config.MAX_TOKENS[purpose]} tokenów "
            f"dla etapu {purpose!r} — sufit liczy się z kontraktu w config.py, "
            "więc kontrakt prosi o więcej, niż sufit mieści"
        )

    text = "".join(b.text for b in message.content if b.type == "text")
    searches = 0
    server_tool_use = getattr(message.usage, "server_tool_use", None)
    if server_tool_use is not None:
        searches = getattr(server_tool_use, "web_search_requests", 0) or 0

    # URL-e, które wyszukiwarka NAPRAWDĘ zwróciła. Sam JSON od modelu nie
    # wystarcza: zmyślony adres wygląda w nim identycznie jak prawdziwy, a
    # kosztuje nieudane pobranie i zafałszowany korpus.
    urls: list[str] = []
    for block in message.content:
        if getattr(block, "type", "") != "web_search_tool_result":
            continue
        content = getattr(block, "content", None)
        if not isinstance(content, list):
            continue  # błąd narzędzia zwraca obiekt, nie listę
        for result in content:
            url = getattr(result, "url", None)
            if isinstance(url, str):
                urls.append(url)

    return text, message.usage.input_tokens, message.usage.output_tokens, searches, urls


def _call_deepseek_responses(
    purpose: str, system: str, user: str
) -> tuple[str, int, int, int, list[str]]:
    """DeepSeek przez /responses z server-side `web_search`.

    Jedyny tani sposób na dyskoverię. Sprawdzone na żywo: realnie wykonuje
    wyszukiwania i zwraca prawdziwe adresy, w przeciwieństwie do Haiku i Sonneta,
    które wypisywały je z pamięci.
    """
    response = httpx.post(
        f"{config.DEEPSEEK_BASE_URL}/responses",
        headers={"Authorization": f"Bearer {config.DEEPSEEK_API_KEY}"},
        json={
            "model": config.MODEL_FOR[purpose],
            "instructions": system,
            "input": user,
            "tools": [{"type": "web_search"}],
            # `auto`, nie wymuszenie. Wymuszone `{"type": "web_search"}` kazało
            # modelowi wołać narzędzie w kółko — 15 wyszukiwań i ani jednego
            # zdania odpowiedzi. Nakaz szukania siedzi w prompcie.
            "tool_choice": "auto",
            # TWARDEGO LIMITU WYSZUKIWAŃ TU NIE MA I NIE DA SIĘ GO DOŁOŻYĆ.
            # Sprawdzone na żywo 26 sierpnia 2026, bo kusi, żeby przepisać
            # `max_uses` z gałęzi Anthropic:
            #   - `max_uses` — nierozpoznane, zachowuje się jak pole, które
            #     zmyśliłem na próbę (`zmyslone_pole_xyz`): HTTP 200, brak echa,
            #   - `max_tool_calls` — JEST w schemacie odpowiedzi, ale po wysłaniu
            #     wartości 3 wraca jako `None`, czyli wartość nie została
            #     przyjęta.
            # Oba dają HTTP 200, więc samo „nie wywaliło się" niczego tu nie
            # dowodzi. Parametr, który nic nie robi, jest gorszy niż jego brak,
            # bo wygląda jak zabezpieczenie.
            #
            # Stąd `llm.ratuj_json`: skoro nie da się zapobiec rozbieganiu,
            # odzyskujemy to, co już opłacone.
            # BEZ tego model przepala cały budżet wyjścia na rozumowanie
            # i wyszukiwanie, a bloku `message` nigdy nie tworzy: 11 wyszukiwań,
            # status "completed", zero tekstu. Tokeny rozumowania liczą się do
            # `max_output_tokens`, więc musi zostać miejsce na odpowiedź.
            "reasoning": {"effort": config.DEEPSEEK_EFFORT},
            "max_output_tokens": config.MAX_TOKENS[purpose],
        },
        timeout=config.timeout_for(config.MAX_TOKENS[purpose]) * 3,
    )
    response.raise_for_status()
    payload = response.json()

    text_parts: list[str] = []
    urls: list[str] = []
    searches = 0

    def walk(node: Any) -> None:
        nonlocal searches
        if isinstance(node, dict):
            if node.get("type") == "web_search_call":
                searches += 1
            if node.get("type") in {"output_text", "text"} and isinstance(
                node.get("text"), str
            ):
                text_parts.append(node["text"])
            for key, value in node.items():
                if key == "url" and isinstance(value, str):
                    # adresy niosą doklejony fragment #ws_call_id=...
                    urls.append(value.split("#ws_call_id=")[0])
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(payload.get("output", []))
    text = payload.get("output_text") or "".join(text_parts)
    usage = payload.get("usage", {})

    # DeepSeek bywa, że przeszukuje i przeszukuje, a bloku `message` nie tworzy
    # — 14 i 24 wyszukiwania kończyły się odpowiedzią, 36 już nie. Ale adresy
    # z tych wyszukiwań SĄ w odpowiedzi i są opłacone. Zamiast wyrzucać je do
    # kosza i płacić drugi raz, prosimy o sam wybór, bez narzędzi.
    if not text.strip() and urls:
        print(
            f"  [{purpose}] {searches} wyszukiwań bez odpowiedzi — wybieram "
            f"z {len(set(urls))} znalezionych adresów drugim wywołaniem",
            flush=True,
        )
        text, tin2, tout2 = _deepseek_pick_from_urls(purpose, system, user, urls)
        return (
            text,
            int(usage.get("input_tokens", 0)) + tin2,
            int(usage.get("output_tokens", 0)) + tout2,
            searches,
            urls,
        )

    if not text.strip():
        raise Truncated(
            f"DeepSeek wykonał {searches} wyszukiwań i nie zwrócił ani tekstu, "
            f"ani adresów (status={payload.get('status')!r})"
        )
    usage = payload.get("usage", {})
    return (
        text,
        int(usage.get("input_tokens", 0)),
        int(usage.get("output_tokens", 0)),
        searches,
        urls,
    )


def _deepseek_pick_from_urls(
    purpose: str, system: str, user: str, urls: list[str]
) -> tuple[str, int, int]:
    """Drugie, tanie wywołanie: wybierz z adresów, które wyszukiwanie już zwróciło.

    Bez narzędzi, więc nie ma jak zapętlić się w szukaniu.
    """
    unique = list(dict.fromkeys(urls))
    response = httpx.post(
        f"{config.DEEPSEEK_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {config.DEEPSEEK_API_KEY}"},
        json={
            # MODEL Z ROUTINGU, nie zaszyta stala. Bylo tu config.DEEPSEEK, wiec
            # kazdy etap bez wyszukiwania jechal na flashu niezaleznie od tego,
            # co mowil MODEL_FOR — a koszt ksiegowalismy po stawce pro.
            "model": config.MODEL_FOR[purpose],
            "max_tokens": config.MAX_TOKENS[purpose],
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": (
                        f"{user}\n\n---\n\nA search has already been run and returned "
                        f"the addresses below. Do not search again and do not invent "
                        f"any address — choose only from this list, and return the "
                        f"JSON described above.\n\n" + "\n".join(unique)
                    ),
                },
            ],
        },
        timeout=config.timeout_for(config.MAX_TOKENS[purpose]),
    )
    response.raise_for_status()
    payload = response.json()
    usage = payload.get("usage", {})
    return (
        payload["choices"][0]["message"]["content"],
        int(usage.get("prompt_tokens", 0)),
        int(usage.get("completion_tokens", 0)),
    )


def _call_deepseek(purpose: str, system: str, user: str) -> tuple[str, int, int, int]:
    response = httpx.post(
        f"{config.DEEPSEEK_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {config.DEEPSEEK_API_KEY}"},
        json={
            # MODEL Z ROUTINGU, nie zaszyta stala. Bylo tu config.DEEPSEEK, wiec
            # kazdy etap bez wyszukiwania jechal na flashu niezaleznie od tego,
            # co mowil MODEL_FOR — a koszt ksiegowalismy po stawce pro.
            "model": config.MODEL_FOR[purpose],
            "max_tokens": config.MAX_TOKENS[purpose],
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        },
        timeout=config.timeout_for(config.MAX_TOKENS[purpose]),
    )
    response.raise_for_status()
    payload = response.json()
    choice = payload["choices"][0]
    if choice.get("finish_reason") == "length":
        raise Truncated(
            f"odpowiedź ucięta na suficie {config.MAX_TOKENS[purpose]} tokenów "
            f"dla etapu {purpose!r} — bez tego wychodzi z tego niedomknięty JSON"
        )
    usage = payload.get("usage", {})
    trafienia = int(usage.get("prompt_cache_hit_tokens", 0))
    pudla = int(usage.get("prompt_cache_miss_tokens",
                          usage.get("prompt_tokens", 0) - trafienia))
    return (
        payload["choices"][0]["message"]["content"],
        pudla,
        int(usage.get("completion_tokens", 0)),
        0,
        trafienia,
    )


def przejsciowy(exc: BaseException) -> bool:
    """Czy ten błąd ma szansę minąć sam.

    Rozróżnienie, które decyduje o tym, czy ponowienie jest dokończeniem, czy
    paleniem pieniędzy:

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


def _obiekty_json(tekst: str):
    """Kolejne ZBILANSOWANE obiekty JSON w tekscie, od lewej.

    Liczymy nawiasy, pomijajac te wewnatrz napisow i te poprzedzone znakiem
    ucieczki. Dzieki temu obiekt konczy sie tam, gdzie naprawde sie konczy,
    a nie na ostatnim nawiasie w calej odpowiedzi.
    """
    i, n = 0, len(tekst)
    while i < n:
        if tekst[i] != "{":
            i += 1
            continue
        glebokosc, w_napisie, ucieczka = 0, False, False
        for j in range(i, n):
            z = tekst[j]
            if ucieczka:
                ucieczka = False
                continue
            if z == "\\":
                ucieczka = True
                continue
            if z == '"':
                w_napisie = not w_napisie
                continue
            if w_napisie:
                continue
            if z == "{":
                glebokosc += 1
            elif z == "}":
                glebokosc -= 1
                if glebokosc == 0:
                    yield tekst[i:j + 1]
                    i = j + 1
                    break
        else:
            return          # nawias sie nie domknal do konca tekstu
        if glebokosc != 0:
            return


RATUNEK_SYSTEM = (
    "You extract structured data. You are given text somebody already wrote. "
    "Return the JSON object it describes, and nothing else. Do not research, "
    "do not add facts, do not correct anything — only what is already there. "
    "If the text truly contains no usable data, return the empty object {}."
)

RATUNEK_PROSBA = """The text below was produced by a model that was asked for
JSON and returned prose instead. It has already done the work — the findings
are in there, just not in the required shape.

Reshape them into EXACTLY this JSON, using these key names and no others:

%s

Take nothing from your own knowledge: every value must come from the text
below. Leave a field as an empty string when the text does not say. Do not
rename keys, do not add keys, do not wrap the result in anything.

TEXT:

%s
"""


def ratuj_json(purpose: str, tekst: str, ksztalt: str, *, conn,
               run_id=None) -> str:
    """Drugie podejście do odpowiedzi, która nie zawierała JSON-a.

    DLACZEGO TO ISTNIEJE — POMIAR, NIE PRZECZUCIE. W siedem dni cztery
    wywołania `curiosity` oddały tokeny i nie oddały JSON-a: 0,1273 / 0,1132 /
    0,0915 / 0,0341 USD, razem 0,3661 — czternaście procent budżetu tego etapu.
    Wejście rosło do 355–477 tysięcy tokenów, bo każda runda wyszukiwania
    przesyła całą rozmowę od nowa, i model gubił wątek zamiast zamknąć
    odpowiedź.

    NAPRAWA NA DRUGIEJ ŚCIEŻCE JUŻ BYŁA i to jest tu najważniejsze. Gałąź
    Anthropic ma `max_uses` i komentarz opisujący dokładnie ten objaw. Ale
    `curiosity` chodzi na DeepSeeku przez `/responses`, gdzie twardego limitu
    wyszukiwań nie ma — więc naprawa nigdy tego etapu nie dotyczyła.

    Ratunek nie zapobiega przepaleniu; ODZYSKUJE to, co już zapłacone. Model
    naprawdę znalazł materiał, tylko oddał go zdaniami. Drugie wywołanie
    dostaje ten tekst BEZ NARZĘDZIA WYSZUKIWANIA — nie ma jak szukać dalej,
    więc musi odpowiedzieć. Koszt rzędu paru dziesiątych centa wobec dziesięciu
    centów, które inaczej przepadają w całości.

    `ksztalt` JEST OBOWIĄZKOWY i to jest poprawka po teście na żywym modelu.
    Pierwsza wersja mówiła tylko „zwróć JSON, o który proszono" — a model nigdy
    tamtej prośby nie widział. Oddał poprawny JSON pod kluczem `findings`
    zamiast `facts`, więc wołający wyciągnął z niego ZERO pozycji. Naprawa
    wyglądała na działającą i nie dawała nic; kosztowało to 0,0019 USD, żeby
    się dowiedzieć. Kształt musi przyjść z miejsca wołania, bo tylko ono wie,
    o co pytał pierwotny prompt.

    Zwraca surowy tekst drugiego wywołania. Gdy i on zawiedzie, oddaje pusty
    napis — wołający zachowuje się wtedy tak, jak dotąd przy braku JSON-a.
    """
    if not (tekst or "").strip():
        return ""
    try:
        return call(purpose, RATUNEK_SYSTEM,
                    RATUNEK_PROSBA % (ksztalt, tekst[:60_000]),
                    conn=conn, run_id=run_id, web_search=False)
    except Exception as exc:
        print("  [ratunek] nie udało się odzyskać JSON-a (%s: %s)"
              % (type(exc).__name__, str(exc)[:100]), flush=True)
        return ""


def parse_json(text: str) -> Any:
    """Wyciąga obiekt JSON z odpowiedzi modelu.

    DWIE AWARIE Z JEDNEGO DNIA, obie kosztowne i obie ciche az do wyjatku.
    25 sierpnia 2026: `warto_pisac` padlo na `Extra data: line 1 column 1866`,
    a szukanie ciekawostek na `brak JSON w odpowiedzi: "I'll work the grid..."`.
    To drugie kosztowalo dwadziescia wyszukiwan i 0,13 USD, po czym oddalo zero.

    Przyczyna byla jedna: bralismy wycinek od PIERWSZEGO `{` do OSTATNIEGO `}`.
    Model z wlaczonym wyszukiwaniem pisze zdanie o tym, co zaraz zrobi, potem
    JSON, czasem jeszcze komentarz na koncu — a kazdy nawias w tej prozie
    przesuwal granice wycinka. Wystarczyl jeden, zeby caly etap przepadl.

    Teraz szukamy ZBILANSOWANYCH obiektow i bierzemy pierwszy, ktory sie
    parsuje. Gdyby zaden — probujemy najdluzszego, bo model bywa ucina wczesny
    fragment przykladu ze swojego wlasnego promptu.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
        cleaned = cleaned.rsplit("```", 1)[0]

    kandydaci = list(_obiekty_json(cleaned))
    for k in kandydaci:
        try:
            return json.loads(k)
        except ValueError:
            continue
    # Najdluzszy jako ostatnia szansa: krotkie obiekty na poczatku bywaja
    # fragmentem instrukcji, ktory model przepisal, zanim odpowiedzial.
    for k in sorted(kandydaci, key=len, reverse=True):
        try:
            return json.loads(k)
        except ValueError:
            continue
    raise ValueError(f"brak JSON w odpowiedzi: {text[:200]!r}")
