# -*- coding: utf-8 -*-
"""Cena nowego modelu z cennika dostawcy — przy zamianie, bez zgadywania.

DLACZEGO TO POWSTALO (26 wrzesnia 2026). `wersje_modeli` przeszedl 22.09
z `claude-opus-5` na `claude-opus-5-5` i z `gpt-5.6-sol` na `gpt-6-sol`.
Nastepcy nie mieli wpisu w cenniku, wiec liczyly sie PODWOJNA stawka
poprzednika: Opus 5.5 po 10/50 USD za milion tokenow (cennik Anthropic: 4/20),
GPT-6 Sol po 8/40 (cennik OpenAI: 2/10). Miesieczny sufit konczyl sie przez to
kilka dni przed koncem miesiaca. Wlasciciel: „napraw, zeby sprawdzalo, jakie ma
ceny model, jak zamienia, albo niech zamienia 1:1".

Wycinki stron nizej sa PRAWDZIWYMI fragmentami cennikow pobranych 26.09.2026
(`platform.claude.com/.../pricing.md` i `developers.openai.com/api/docs/pricing`),
skrocone do potrzebnych wierszy. Test NIE chodzi do sieci.

BEZ PYTESTA. Uruchamiac z korzenia repozytorium:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_cennik_dostawcy.py
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import config            # noqa: E402
import cennik_dostawcy   # noqa: E402
import llm               # noqa: E402
import wersje_modeli as wm  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


ANTHROPIC_MD = """The following table shows pricing for all Claude models:

| Model                 | Base input tokens     | 5m cache writes | 1h cache writes | Cache hits and refreshes | Output tokens          |
| :-------------------- | :-------------------- | :-------------- | :-------------- | :----------------------- | :--------------------- |
| Claude Fable 5.1      | $10 / MTok            | $12.50 / MTok   | $20 / MTok      | $0.25 / MTok<sup>1</sup> | $50 / MTok             |
| Claude Opus 5.5       | $4 / MTok             | $5 / MTok       | $8 / MTok       | $0.20 / MTok<sup>2</sup> | $20 / MTok             |
| Claude Opus 5         | $5 / MTok             | $6.25 / MTok    | $10 / MTok      | $0.50 / MTok             | $25 / MTok             |
| Claude Opus 5.6       | $3 / MTok             | $3.75 / MTok    | $6 / MTok       | $0.30 / MTok             | $15 / MTok             |
| Claude Sonnet 5       | $2 / MTok<sup>3</sup> | $2.50 / MTok    | $4 / MTok       | $0.20 / MTok             | $10 / MTok<sup>3</sup> |

The Batch API allows asynchronous processing with a 50% discount.

| Model                 | Batch input  | Batch output  |
| :-------------------- | :----------- | :------------ |
| Claude Opus 5.5       | $2 / MTok    | $10 / MTok    |
| Claude Haiku 6        | $0.50 / MTok | $2.50 / MTok  |
"""

OPENAI_HTML = """<div>Standard Batch Flex Fast mode Standard Short context Long context
<table><tr><th>Model</th><th>Input</th><th>Cached input</th><th>Cache writes</th><th>Output</th>
<th>Input</th><th>Cached input</th><th>Cache writes</th><th>Output</th></tr>
<tr><td>gpt-6-astra</td><td>$10.00</td><td>$1.00</td><td>$12.50</td><td>$50.00</td><td>$20.00</td><td>$2.00</td><td>$25.00</td><td>$75.00</td></tr>
<tr><td>gpt-6-sol</td><td>$2.00</td><td>$0.20</td><td>$2.50</td><td>$10.00</td><td>$4.00</td><td>$0.40</td><td>$5.00</td><td>$15.00</td></tr>
<tr><td>gpt-7-sol</td><td>$8.00</td><td>$0.80</td><td>$10.00</td><td>$40.00</td><td>$16.00</td><td>$1.60</td><td>$20.00</td><td>$60.00</td></tr>
</table>
Cyber models Our latest Daybreak models. Prices per 1M tokens. Short context Long context
<table><tr><th>Model</th><th>Input</th><th>Cached input</th><th>Cache writes</th><th>Output</th>
<th>Input</th><th>Cached input</th><th>Cache writes</th><th>Output</th></tr>
<tr><td>gpt-5.6-sol</td><td>$4.00</td><td>$0.40</td><td>$5.00</td><td>$20.00</td><td>$8.00</td><td>$0.80</td><td>$10.00</td><td>$30.00</td></tr>
</table>
All models Batch Short context Long context
<table><tr><th>Model</th><th>Input</th><th>Cached input</th><th>Cache writes</th><th>Output</th></tr>
<tr><td>gpt-6-sol</td><td>$1.00</td><td>$0.10</td><td>$1.25</td><td>$5.00</td></tr>
</table></div>"""


def strona(url):
    return ANTHROPIC_MD if "claude" in url else OPENAI_HTML


print("=== 1. CENNIK ANTHROPIC: PIERWSZA TABELA, WLASCIWE KOLUMNY ===")
sprawdz("Opus 5.5: 4 / cache 0,20 / 20",
        cennik_dostawcy.z_cennika_anthropic(ANTHROPIC_MD, "claude-opus-5-5")
        == {"in": 4.0, "cache": 0.2, "out": 20.0})
sprawdz("data na koncu nie zmienia nazwy",
        cennik_dostawcy.z_cennika_anthropic(ANTHROPIC_MD, "claude-opus-5-5-20260901")
        == {"in": 4.0, "cache": 0.2, "out": 20.0})
sprawdz("przypis <sup> nie psuje liczby (Sonnet 5: 2 / 10)",
        cennik_dostawcy.z_cennika_anthropic(ANTHROPIC_MD, "claude-sonnet-5")
        == {"in": 2.0, "cache": 0.2, "out": 10.0})
sprawdz("KONTRDOWOD: model tylko w tabeli batch nie dostaje ceny batch",
        cennik_dostawcy.z_cennika_anthropic(ANTHROPIC_MD, "claude-haiku-6") is None)
sprawdz("KONTRDOWOD: przestawione kolumny — parser odmawia",
        cennik_dostawcy.z_cennika_anthropic(ANTHROPIC_MD.replace(
            "| Base input tokens     | 5m cache writes", "| Output tokens     | 5m cache writes"),
            "claude-opus-5-5") is None)

print()
print("=== 2. CENNIK OPENAI: TRYB STANDARDOWY, KROTKI KONTEKST ===")
sprawdz("GPT-6 Sol: 2 / 0,20 / 10 (nie batch 1/5, nie dlugi kontekst 4/15)",
        cennik_dostawcy.z_cennika_openai(OPENAI_HTML, "gpt-6-sol")
        == {"in": 2.0, "cache": 0.2, "out": 10.0})
sprawdz("GPT-5.6 Sol: 4 / 0,40 / 20 (tabela Daybreak)",
        cennik_dostawcy.z_cennika_openai(OPENAI_HTML, "gpt-5.6-sol")
        == {"in": 4.0, "cache": 0.4, "out": 20.0})
sprawdz("KONTRDOWOD: „gpt-6-sol-pro” to nie „gpt-6-sol”",
        cennik_dostawcy.z_cennika_openai(OPENAI_HTML, "gpt-6-sol-pro") is None)

print()
print("=== 3. LICZBY I AWARIE ===")
sprawdz("wejscie drozsze od wyjscia to nie cennik",
        not cennik_dostawcy.wiarygodna({"in": 20, "out": 4}))
sprawdz("KONTRDOWOD: dwadziescia razy drozej od poprzednika — odrzucone",
        not cennik_dostawcy.wiarygodna({"in": 100, "out": 500}, {"in": 5, "out": 25}))


def _pada(url):
    raise TimeoutError("nie odpowiada")


sprawdz("siec padla: brak ceny z powodem, bez wyjatku",
        cennik_dostawcy.stawka_u_dostawcy("gpt-6-sol", pobierz=_pada)[0] is None)
sprawdz("DeepSeek i obrazy: cennika nie czytamy",
        cennik_dostawcy.stawka_u_dostawcy("deepseek-flash", pobierz=strona)[0] is None
        and cennik_dostawcy.stawka_u_dostawcy("gpt-image-2", pobierz=strona)[0] is None)
sprawdz("darmowy test nie idzie do sieci nawet bez atrapy",
        cennik_dostawcy.stawka_u_dostawcy("claude-opus-5-5")[0] is None)

print()
print("=== 4. CENNIK SILNIKA: NASTEPCY Z 22.09 PO CENIE DOSTAWCY ===")
sprawdz("Opus 5.5: 4/20, cache 0,20",
        {k: config.PRICING["claude-opus-5-5"][k] for k in ("in", "out", "cache")}
        == {"in": 4.0, "out": 20.0, "cache": 0.2})
sprawdz("GPT-6 Sol: 2/10, cache 0,20",
        {k: config.PRICING["gpt-6-sol"][k] for k in ("in", "out", "cache")}
        == {"in": 2.0, "out": 10.0, "cache": 0.2})
# Koszt liczony tak, jak liczy go produkcja: 10 tys. wejscia, 2 tys. wyjscia,
# 5 tys. trafien w cache. Cache Opusa 5.5 to 0,05 wejscia — jawna stawka
# z cennika wygrywa z mnoznikiem 0,1 w `_cost`.
usd, _ = llm._cost("claude-opus-5-5", 10_000, 2_000, 0, cache_hit=5_000)
sprawdz("Opus 5.5 w ksiegach: 0,0810 USD (bylo 0,2025 przy x2 i cache 0,1)",
        abs(usd - 0.081) < 1e-9, usd)
usd, _ = llm._cost("gpt-6-sol", 10_000, 2_000, 0, cache_hit=5_000)
sprawdz("GPT-6 Sol w ksiegach: 0,0410 USD", abs(usd - 0.041) < 1e-9, usd)

print()
print("=== 5. ZAMIANA SPRAWDZA CENE PRZED PLATNA PROBA ===")
KATALOG = pathlib.Path(tempfile.mkdtemp())
STAN = {"plik": wm.plik, "proba": wm.sprawdz_na_zywo, "pobierz": cennik_dostawcy._pobierz,
        "role": dict(config.MODEL_FOR),
        "stale": {n: getattr(config, n, None) for n in wm.STALE_Z_MODELEM},
        "flaga": config.MODELE_SAME_NA_NOWSZE, "piny": config.MODELE_NIE_RUSZAJ,
        "ceny": set(config.PRICING)}
proby = []
try:
    wm.plik = lambda: KATALOG / "wersje_modeli.json"
    wm.sprawdz_na_zywo = lambda nowy, conn, run_id: (proby.append(nowy) or (True, "OK"))
    cennik_dostawcy._pobierz = strona
    config.MODEL_FOR.clear()
    config.MODEL_FOR.update({"restack": "claude-opus-5", "note": "gpt-5.6-sol",
                             "classify": "deepseek-flash"})
    for n in wm.STALE_ZAPASOWE:
        setattr(config, n, None)
    config.CLAUDE, config.GPT_SOL, config.DEEPSEEK = "claude-opus-5", "gpt-5.6-sol", "deepseek-flash"
    config.MODELE_SAME_NA_NOWSZE, config.MODELE_NIE_RUSZAJ = True, ()
    listy = {"anthropic": ["claude-opus-5", "claude-opus-5-6"],
             "openai": ["gpt-5.6-sol", "gpt-7-sol"], "deepseek": ["deepseek-flash"]}
    wynik = wm.sprawdz_i_przelacz(None, None, wymus=True, listy=listy)
    zapis = json.loads((KATALOG / "wersje_modeli.json").read_text(encoding="utf-8"))
    sprawdz("tanszy Opus 5.6 (3/15) przelaczony",
            config.MODEL_FOR["restack"] == "claude-opus-5-6", config.MODEL_FOR)
    sprawdz("  po cenie z cennika, nie 1:1 i nie x2",
            {k: config.PRICING["claude-opus-5-6"][k] for k in ("in", "out", "cache")}
            == {"in": 3.0, "out": 15.0, "cache": 0.3}, config.PRICING.get("claude-opus-5-6"))
    sprawdz("  cena zapisana przy zamianie",
            zapis["zamiany"]["claude-opus-5"].get("cena") == {"in": 3.0, "out": 15.0, "cache": 0.3},
            zapis["zamiany"].get("claude-opus-5"))
    sprawdz("drozszy GPT-7 Sol (8/40 wobec 4/20) NIE wchodzi sam",
            config.MODEL_FOR["note"] == "gpt-5.6-sol" and "gpt-5.6-sol" not in zapis["zamiany"],
            zapis["zamiany"])
    sprawdz("  i nie placimy za jego probe", "gpt-7-sol" not in proby, proby)
    sprawdz("  a raport mowi o decyzji wlasciciela",
            any("drozszy" in o and "wlasciciela" in o for _, _, o in wynik["raport"]), wynik)
finally:
    wm.plik, wm.sprawdz_na_zywo = STAN["plik"], STAN["proba"]
    cennik_dostawcy._pobierz = STAN["pobierz"]
    config.MODEL_FOR.clear()
    config.MODEL_FOR.update(STAN["role"])
    for n, v in STAN["stale"].items():
        setattr(config, n, v)
    config.MODELE_SAME_NA_NOWSZE, config.MODELE_NIE_RUSZAJ = STAN["flaga"], STAN["piny"]
    for nazwa in set(config.PRICING) - STAN["ceny"]:
        config.PRICING.pop(nazwa)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
