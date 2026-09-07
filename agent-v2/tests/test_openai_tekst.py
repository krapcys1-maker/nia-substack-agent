# -*- coding: utf-8 -*-
"""Sciezka tekstowa OpenAI: zadanie ma dobry ksztalt, a tokeny nie licza sie dwa razy.

## Po co ten plik istnieje

`OPENAI_API_KEY` sluzyl do 7 wrzesnia 2026 WYLACZNIE do grafik i tak byl
opisany w `config`. Modele `gpt-5.6` sa jednak tansze od pisarza notek
(Sol 4/20 USD za milion wobec 10/50 u Fable), wiec wlasciciel poprosil
o probe i sciezka powstala.

## Czego pilnuje ten plik

CACHE LICZONY DWA RAZY. To jest pulapka, ktora nie zglasza sie sama: OpenAI
podaje w `usage.input_tokens` liczbe RAZEM z trafieniami w cache, a `_cost`
mnozy `tokens_in` przez pelna stawke i dolicza `cache_hit` OSOBNO po stawce
cache. Oddanie surowego `input_tokens` policzyloby trafienia dwa razy i to po
zlej cenie — rachunek rosnie, nic nie wybucha, nikt nie zauwaza. DeepSeek
rozwiazuje to tak samo (`prompt_cache_miss_tokens`), wiec konwencja jest
jedna dla calego silnika i tutaj ma byc zachowana.

WYSILEK BEZ TLUMACZENIA NAZW. Skala silnika (`low`...`max`) jest podzbiorem
skali OpenAI, wiec zadnego mapowania nie ma. Test tego pilnuje, bo dopisanie
slownika „na wszelki wypadek" jest kuszace i byloby miejscem na cicha
pomylke. Gdy preset nie ustawil wysilku, pola nie wysylamy wcale — model ma
wtedy wlasna wartosc domyslna, lepsza niz nasza zgadnieta.

BRAK NARZEDZI. Wyszukiwanie po stronie serwera jest tu niepotrzebne
i platne — dyskoveria chodzi na DeepSeeku, ktory robi to taniej.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_openai_tekst.py
"""
import json
import sys
import types

sys.path.insert(0, "agent-v2")
import config  # noqa: E402
import llm     # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


ZDARZENIA = [
    'data: {"type": "response.output_text.delta", "delta": "nie"}',
    'data: {"type": "response.output_text.delta", "delta": "wazne"}',
    'data: ' + json.dumps({
        "type": "response.completed",
        "response": {
            "output_text": "gotowy tekst",
            "output": [],
            "usage": {"input_tokens": 5000, "output_tokens": 400,
                      "input_tokens_details": {"cached_tokens": 3800}},
        },
    }),
    "data: [DONE]",
]


class _Odpowiedz:
    def __init__(self, zapis):
        self.zapis = zapis

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def raise_for_status(self):
        pass

    def iter_lines(self):
        return iter(ZDARZENIA)


def wywolaj(purpose="note"):
    """Wywoluje sciezke z podstawionym httpx i runtime; oddaje (wynik, zadanie)."""
    zapis = {}

    def stream(metoda, url, headers=None, json=None, timeout=None):
        zapis.update(metoda=metoda, url=url, headers=headers or {}, json=json or {})
        return _Odpowiedz(zapis)

    stary_httpx, stary_runtime = llm.httpx, llm.runtime
    udawany = types.SimpleNamespace(
        stream=stream, Timeout=lambda *a, **k: None,
        RemoteProtocolError=stary_httpx.RemoteProtocolError)
    llm.httpx = udawany
    llm.runtime = types.SimpleNamespace(
        observe=lambda: None, watch=lambda *a: None, check=lambda: None,
        capture=lambda *a, **k: None, token_limit=lambda n: n)
    try:
        return llm._call_openai_responses(purpose, "SYSTEM", "USER"), zapis
    finally:
        llm.httpx, llm.runtime = stary_httpx, stary_runtime


print("=== 0. WALIDATOR KARTRIDZA ZNA TE SAMA LISTE CO `call` ===")
# ROZJAZD ZDARZYL SIE NAPRAWDE, tego samego dnia: `call` przyjmowalo juz
# `openai`, a `preset.sprawdz` trzymalo wlasna kopie listy i odrzucalo kartridz
# slowami „obslugiwane: anthropic, deepseek". Bramka dzialala poprawnie i byla
# nieaktualna — najgorsze polaczenie, bo wyglada na blad operatora.
import preset  # noqa: E402
sprawdz("obie strony czytaja jedna liste",
        tuple(preset._dostawcy_tekstu()) == tuple(llm.DOSTAWCY_TEKSTU),
        "%s vs %s" % (preset._dostawcy_tekstu(), llm.DOSTAWCY_TEKSTU))
sprawdz("i jest w niej openai", "openai" in llm.DOSTAWCY_TEKSTU,
        str(llm.DOSTAWCY_TEKSTU))

print()
print("=== 1. DOSTAWCA I STAWKI ===")
sprawdz("gpt- rozpoznany jako openai", llm._dostawca("gpt-5.6-sol") == "openai",
        llm._dostawca("gpt-5.6-sol"))
cennik = config.PRICING.get(config.GPT_SOL) or {}
sprawdz("Sol ma stawke wejscia i wyjscia",
        cennik.get("in") == 4.00 and cennik.get("out") == 20.00, str(cennik))
sprawdz("i OSOBNA stawke cache, bez ktorej trafienia liczylyby sie po pelnej cenie",
        cennik.get("cache") == 0.40, str(cennik))
sprawdz("stawka jest oznaczona jako niepotwierdzona faktura",
        cennik.get("verified") is False, str(cennik))

print()
print("=== 2. KSZTALT ZADANIA ===")
stare_modele = dict(config.MODEL_FOR)
stary_effort = dict(config.EFFORT)
# KLUCZE WARTOWNICZE, a nie te z instalacji. Pierwsza wersja sprawdzala naglowek
# przeciwko `config.OPENAI_API_KEY` — czyli przechodzila na maszynie z kluczem
# i oblewala na CI, gdzie go nie ma. Dwie rozne wartosci sa tez mocniejszym
# dowodem: pokazuja, ze naglowek niesie klucz OPENAI, a nie ANTHROPIC.
stary_openai, stary_anthropic = config.OPENAI_API_KEY, config.ANTHROPIC_API_KEY
config.OPENAI_API_KEY = "sk-test-OPENAI-wartownik"
config.ANTHROPIC_API_KEY = "sk-test-ANTHROPIC-wartownik"
try:
    config.MODEL_FOR["note"] = config.GPT_SOL
    config.EFFORT["note"] = "low"
    (tekst, pudla, wyjscie, szukania, trafienia), zad = wywolaj()
    body = zad["json"]
    sprawdz("idzie na /responses", zad["url"].endswith("/responses"), zad["url"])
    naglowek = zad["headers"].get("Authorization", "")
    sprawdz("naglowek niesie klucz OpenAI",
            naglowek == "Bearer sk-test-OPENAI-wartownik", naglowek)
    sprawdz("i na pewno NIE klucz Anthropica",
            "ANTHROPIC" not in naglowek, naglowek)
    sprawdz("system idzie jako instructions", body.get("instructions") == "SYSTEM")
    sprawdz("prompt idzie jako input", body.get("input") == "USER")
    sprawdz("strumien wlaczony", body.get("stream") is True)
    sprawdz("wysilek przechodzi BEZ tlumaczenia nazw",
            body.get("reasoning") == {"effort": "low"}, str(body.get("reasoning")))
    sprawdz("zadnych narzedzi — wyszukiwanie chodzi na DeepSeeku",
            "tools" not in body, str(list(body)))

    print()
    print("=== 3. TOKENY: TRAFIENIA NIE LICZA SIE DWA RAZY ===")
    sprawdz("tekst z response.completed, nie z delt", tekst == "gotowy tekst", tekst)
    sprawdz("wejscie pomniejszone o cache (5000 - 3800)", pudla == 1200, pudla)
    sprawdz("trafienia oddane osobno", trafienia == 3800, trafienia)
    sprawdz("wyjscie bez zmian", wyjscie == 400, wyjscie)
    sprawdz("zero wyszukiwan", szukania == 0, szukania)
    # KONTRDOWOD: gdyby ktos oddal surowe `input_tokens`, ta suma bylaby wieksza
    # od prawdziwego zuzycia o cale trafienia — i nikt by tego nie zobaczyl.
    sprawdz("suma pudel i trafien zgadza sie z input_tokens",
            pudla + trafienia == 5000, pudla + trafienia)

    print()
    print("=== 4. BEZ WYSILKU W PRESECIE POLA NIE WYSYLAMY ===")
    config.EFFORT.pop("note", None)
    (_, _, _, _, _), zad2 = wywolaj()
    sprawdz("brak `reasoning`, model bierze swoja domyslna",
            "reasoning" not in zad2["json"], str(list(zad2["json"])))
finally:
    config.MODEL_FOR.clear()
    config.MODEL_FOR.update(stare_modele)
    config.EFFORT.clear()
    config.EFFORT.update(stary_effort)
    config.OPENAI_API_KEY, config.ANTHROPIC_API_KEY = stary_openai, stary_anthropic

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
