# -*- coding: utf-8 -*-
"""Role, ktore musza szukac w sieci, chodza na modelu, ktory NAPRAWDE szuka — a brak wyszukiwan jest glosny.

## Pomiar, ktory to wywolal

14 wrzesnia 2026, cztery minimalne wywolania DeepSeek `/responses` z narzedziem
`web_search`, na serwerze:

    deepseek-flash, tool_choice auto          0 wyszukiwan, odpowiedz zmyslona
    deepseek-v4-flash (API oddaje flash)      0 wyszukiwan, model mysli, ze jest maj
    deepseek-flash, narzedzie wymuszone       wywolanie wypisane tekstem, niewykonane
    deepseek-v4-pro, tool_choice auto         7 wyszukiwan, poprawny adres

W tabeli `calls` od 10 wrzesnia kazde wywolanie tematow (`curiosity`), researchu
artykulu (`discovery`), sprawdzania faktow i stanu modeli mialo ZERO wyszukiwan
— przez cztery dni, bez slowa w logu.

## 28 wrzesnia 2026: Flash szuka inna droga

Ten sam V4.1 Flash przez endpoint DeepSeeka zgodny z API Anthropic szuka
naprawde, wiec kazde wywolanie DeepSeeka z siecia idzie teraz przez
`llm._call_deepseek_z_siecia`, role z wyszukiwarka wrocily na Flasha, a lista
modeli bez wyszukiwarki jest pusta. Straznik zostaje na nastepna podmiane.

## Co ten test sprawdza

1. `napraw_role_wyszukiwania` przestawia role z wyszukiwarka z modelu bez niej
   i nie rusza pozostalych (na modelu wymyslonym — lista jest dzis pusta);
2. po zaladowaniu konfiguracji role z wyszukiwarka stoja na Flashu, zaden
   na modelu, ktory nie szuka, a naprawa idzie PO presecie i PO zamianach wersji;
3. `llm.call` z wyszukiwarka, ktore nie wykonalo wyszukiwania, mowi o tym
   glosno — i tylko w rolach, dla ktorych wyszukiwanie jest caloscia;
4. nowa droga: adres endpointu Anthropic, narzedzie i limit, liczba wyszukiwan
   i adresy Z ODPOWIEDZI SERWERA (nie z tekstu), zuzycie zapisane takze przy
   ucieciu, a wywolanie z siecia nie idzie juz na `/responses`.

BEZ PYTESTA, bez sieci, bez platnych wywolan (transport podmieniony).
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_wyszukiwarka_na_modelu_ktory_szuka.py
"""
import contextlib
import io
import pathlib
import sys
import tempfile
import types

sys.path.insert(0, "agent-v2")
import config  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


print("=== 1. NAPRAWA ROL (straznik) ===")
cfg = types.SimpleNamespace(
    ROLE_Z_WYSZUKIWARKA=config.ROLE_Z_WYSZUKIWARKA,
    MODELE_BEZ_WYSZUKIWARKI=("model-bez-szukania", "stara-nazwa-bez-szukania"),
    MODEL_WYSZUKIWARKI=config.MODEL_WYSZUKIWARKI,
    MODEL_FOR={"curiosity": "model-bez-szukania", "discovery": "stara-nazwa-bez-szukania",
               "factcheck": "deepseek-flash", "comment": "model-bez-szukania"})
zmiany = config.napraw_role_wyszukiwania(cfg)
sprawdz("tematy z modelu bez szukania na model z wyszukiwarka",
        cfg.MODEL_FOR["curiosity"] == config.MODEL_WYSZUKIWARKI, cfg.MODEL_FOR)
sprawdz("research ze starej nazwy tez", cfg.MODEL_FOR["discovery"] == config.MODEL_WYSZUKIWARKI, cfg.MODEL_FOR)
sprawdz("rola na modelu, ktory szuka, nietknieta", cfg.MODEL_FOR["factcheck"] == "deepseek-flash")
sprawdz("komentarz (bez wyszukiwarki) nietkniety", cfg.MODEL_FOR["comment"] == "model-bez-szukania")
sprawdz("zmiany oddane do wypisania", sorted(z[0] for z in zmiany) == ["curiosity", "discovery"], zmiany)
sprawdz("model wyszukiwarki sam nie jest na liscie bez wyszukiwarki",
        config.MODEL_WYSZUKIWARKI not in config.MODELE_BEZ_WYSZUKIWARKI)
sprawdz("od 28.09 Flash NIE jest na liscie bez wyszukiwarki (szuka droga Anthropic)",
        config.DEEPSEEK_FLASH not in config.MODELE_BEZ_WYSZUKIWARKI
        and config.DEEPSEEK not in config.MODELE_BEZ_WYSZUKIWARKI, config.MODELE_BEZ_WYSZUKIWARKI)

print()
print("=== 2. KONFIGURACJA PO ZALADOWANIU ===")
zle = {r: config.MODEL_FOR.get(r) for r in config.ROLE_Z_WYSZUKIWARKA
       if config.MODEL_FOR.get(r) in config.MODELE_BEZ_WYSZUKIWARKI}
sprawdz("zadna rola z wyszukiwarka na modelu, ktory nie szuka", not zle, zle)
na_flashu = {r: config.MODEL_FOR.get(r) for r in config.ROLE_Z_WYSZUKIWARKA}
sprawdz("role z wyszukiwarka domyslnie na Flashu",
        all(m == config.DEEPSEEK_FLASH for m in na_flashu.values()), na_flashu)
ZR = io.open("agent-v2/config.py", encoding="utf-8").read()
i_preset = ZR.find("_preset.zastosuj(")
i_zamiany = ZR.find("_wersje_modeli.zastosuj(")
i_naprawa = ZR.find("in napraw_role_wyszukiwania():")
sprawdz("naprawa po presecie i po zamianach wersji", 0 < i_preset < i_zamiany < i_naprawa,
        (i_preset, i_zamiany, i_naprawa))

print()
print("=== 3. BRAK WYSZUKIWAN JEST GLOSNY ===")
config.uzyj_katalogu_danych(pathlib.Path(tempfile.mkdtemp()))
config.DRY_RUN = False
config.WOLNO_WOLAC_MODEL = True
config.DEEPSEEK_API_KEY = "test-key"
import db   # noqa: E402
import llm  # noqa: E402

CONN = db.connect()
RUN = db.start_run(CONN, "test-wyszukiwarki")
prawdziwa_droga = llm._call_deepseek_z_siecia


def wywolaj(rola, wyszukan, web_search=True):
    llm._call_deepseek_z_siecia = lambda *a, **k: ('{"facts": []}', 100, 50, wyszukan, [])
    llm._call_deepseek_responses = lambda *a, **k: (_ for _ in ()).throw(
        AssertionError("wywolanie z siecia poszlo na /responses"))
    llm._call_deepseek = lambda *a, **k: ('{"facts": []}', 100, 50, 0, 0)
    bufor = io.StringIO()
    stary = config.MODEL_FOR.get(rola)
    config.MODEL_FOR[rola] = config.DEEPSEEK_FLASH
    try:
        with contextlib.redirect_stdout(bufor):
            llm.call(rola, "system", "user", conn=CONN, run_id=RUN, web_search=web_search)
    finally:
        if stary is None:
            config.MODEL_FOR.pop(rola, None)
        else:
            config.MODEL_FOR[rola] = stary
    return bufor.getvalue()


wyjscie = wywolaj("curiosity", 0)
sprawdz("tematy bez ani jednego wyszukiwania: ostrzezenie w logu",
        "[wyszukiwarka] UWAGA: curiosity" in wyjscie, wyjscie[-300:])
wyjscie = wywolaj("curiosity", 5)
sprawdz("tematy z wyszukiwaniami: cisza", "[wyszukiwarka]" not in wyjscie, wyjscie[-300:])
wyjscie = wywolaj("reply", 0)
sprawdz("odpowiedz (wyszukiwanie opcjonalne) bez wyszukiwan: cisza",
        "[wyszukiwarka]" not in wyjscie, wyjscie[-300:])

print()
print("=== 4. NOWA DROGA: ENDPOINT ZGODNY Z API ANTHROPIC ===")
llm._call_deepseek_z_siecia = prawdziwa_droga
wyslane: list[dict] = []


class Odpowiedz:
    def __init__(self, dane):
        self._dane = dane

    def raise_for_status(self):
        pass

    def json(self):
        return self._dane


def atrapa_klienta(dane):
    class Klient:
        def __init__(self, *a, **k):
            pass

        def post(self, url, headers=None, json=None):
            wyslane.append({"url": url, "headers": headers, "json": json})
            return Odpowiedz(dane)

        def close(self):
            pass
    return Klient


DANE = {"stop_reason": "end_turn",
        "content": [{"type": "server_tool_use", "name": "web_search"},
                    {"type": "web_search_tool_result",
                     "content": [{"type": "web_search_result", "url": "https://example.org/a"},
                                 {"type": "web_search_result", "url": "https://example.org/b"}]},
                    {"type": "text", "text": '{"facts": [], "zrodlo": "https://zmyslony.example/x"}'}],
        "usage": {"input_tokens": 1200, "output_tokens": 300, "cache_read_input_tokens": 400,
                  "server_tool_use": {"web_search_requests": 2}}}
stary_klient = llm.httpx.Client
llm.httpx.Client = atrapa_klienta(DANE)
try:
    tekst, tin, tout, szukan, adresy = llm._call_deepseek_z_siecia("curiosity", "system", "user")
finally:
    llm.httpx.Client = stary_klient
w = wyslane[-1]
sprawdz("adres: endpoint DeepSeeka zgodny z API Anthropic",
        w["url"] == "https://api.deepseek.com/anthropic/v1/messages", w["url"])
sprawdz("klucz w naglowku x-api-key", (w["headers"] or {}).get("x-api-key") == "test-key")
narz = (w["json"] or {}).get("tools") or [{}]
sprawdz("narzedzie web_search_20250305 z limitem wyszukiwan",
        narz[0].get("type") == "web_search_20250305" and narz[0].get("max_uses") == config.DISCOVERY_MAX_SEARCHES,
        narz)
sprawdz("model z routingu roli (curiosity na Flashu)",
        (w["json"] or {}).get("model") == config.MODEL_FOR["curiosity"], (w["json"] or {}).get("model"))
sprawdz("liczba wyszukiwan z usage serwera", szukan == 2, szukan)
sprawdz("adresy z wynikow wyszukiwarki, NIE z tekstu modelu",
        adresy == ["https://example.org/a", "https://example.org/b"], adresy)
sprawdz("tokeny: wejscie i wyjscie z usage", (tin, tout) == (1200, 300), (tin, tout))
sprawdz("tekst odpowiedzi z blokow text", tekst.startswith('{"facts"'), tekst[:40])

# UCIECIE: zuzycie ma byc zapisane w stanie proby, zanim poleci wyjatek.
import call_runtime  # noqa: E402

stan = call_runtime.Attempt(1000, float("inf"))
token = call_runtime.CURRENT.set(stan)
llm.httpx.Client = atrapa_klienta(dict(DANE, stop_reason="max_tokens"))
try:
    try:
        llm._call_deepseek_z_siecia("curiosity", "system", "user")
        uciete = False
    except llm.Truncated:
        uciete = True
finally:
    llm.httpx.Client = stary_klient
    call_runtime.CURRENT.reset(token)
sprawdz("ucieta odpowiedz: wyjatek Truncated", uciete)
sprawdz("KONTRDOWOD: zaplacone zuzycie ucietej odpowiedzi zapisane (wejscie, cache, wyszukiwania)",
        stan.usage.get("tokens_in") == 1200 and stan.usage.get("cache_hit") == 400
        and stan.usage.get("web_searches") == 2, stan.usage)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
