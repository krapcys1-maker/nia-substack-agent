# -*- coding: utf-8 -*-
"""Nowsza wersja modelu: wykryta u dostawcy, sprawdzona i nalozona — i tylko taka.

## Pomiar, ktory to wywolal

13 wrzesnia 2026, `GET /models` u trzech dostawcow (listy nizej sa DOSLOWNE).
DeepSeek podawal juz tylko `deepseek-flash` i `deepseek-v4-pro`, a kartridz
serwera mial `deepseek-v4-flash` w dziewietnastu rolach. Stara nazwa jeszcze
odpowiadala — tym samym modelem co `deepseek-flash`, z tym samym odciskiem
systemu — ale na liscie jej nie bylo, a cennik dostawcy nazywa ja „legacy".

## Co ten test sprawdza

1. rozbior nazw z prawdziwych list — dostawca, rodzina, wersja;
2. nastepce na DZISIEJSZYCH listach: flash przechodzi na `deepseek-flash`,
   reszta naszych modeli jest aktualna;
3. nastepce na listach z przyszlosci — i czego wybrac NIE wolno;
4. przelaczenie w calosci: proba na przestawionej konfiguracji, zapis,
   oblana proba, przypiety model, wylaczony przelacznik, brak listy;
5. nakladanie zapisanych zamian przy starcie, z lancuchem i cena;
6. koszt nastepcy liczony bez KeyError i po wlasciwej stawce;
7. wpiecie w `config` i w `run.py`.

BEZ PYTESTA, bez sieci, bez platnych wywolan — proba na zywo jest podstawiona.
Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_wersje_modeli.py
"""
import ast
import io
import json
import pathlib
import sys
import tempfile
import types
from datetime import datetime, timezone

sys.path.insert(0, "agent-v2")
import config          # noqa: E402
import llm             # noqa: E402
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


# --- listy DOSLOWNIE z 13 wrzesnia 2026 ---------------------------------------
DEEPSEEK_DZIS = ["deepseek-flash", "deepseek-v4-pro"]
ANTHROPIC_DZIS = [
    "claude-fable-5", "claude-fable-5-1", "claude-haiku-4-5-20251001",
    "claude-opus-4-5-20251101", "claude-opus-4-6", "claude-opus-4-7",
    "claude-opus-4-8", "claude-opus-5", "claude-sonnet-4-5-20250929",
    "claude-sonnet-4-6", "claude-sonnet-5"]
OPENAI_DZIS = [
    "gpt-3.5-turbo", "gpt-3.5-turbo-0125", "gpt-4", "gpt-4-0613", "gpt-4-turbo",
    "gpt-4-turbo-2024-04-09", "gpt-4.1", "gpt-4.1-2025-04-14", "gpt-4.1-mini",
    "gpt-4.1-mini-2025-04-14", "gpt-4.1-nano", "gpt-4o", "gpt-4o-mini",
    "gpt-4o-mini-search-preview", "gpt-5", "gpt-5-2025-08-07", "gpt-5-chat-latest",
    "gpt-5-codex", "gpt-5-mini", "gpt-5-nano", "gpt-5-pro", "gpt-5.1",
    "gpt-5.1-codex", "gpt-5.1-codex-max", "gpt-5.1-codex-mini", "gpt-5.2",
    "gpt-5.2-pro", "gpt-5.3-codex", "gpt-5.4", "gpt-5.4-mini", "gpt-5.4-nano",
    "gpt-5.4-pro", "gpt-5.5", "gpt-5.5-pro", "gpt-5.6-luna", "gpt-5.6-sol",
    "gpt-5.6-terra", "gpt-6-astra", "gpt-image-1", "gpt-image-1.5", "gpt-image-2",
    "gpt-image-2.5-flare", "gpt-image-2.5-sunburst", "gpt-realtime-2.1",
    "gpt-realtime-2.1-mini"]
LISTY_DZIS = {"deepseek": DEEPSEEK_DZIS, "anthropic": ANTHROPIC_DZIS,
              "openai": OPENAI_DZIS}

print("=== 1. ROZBIOR NAZW ===")
for nazwa, dostawca, rodzina, wersja in (
        ("deepseek-v4-flash", "deepseek", "deepseek:flash", (4, 0)),
        ("deepseek-v4.1-pro", "deepseek", "deepseek:pro", (4, 1)),
        ("deepseek-flash", "deepseek", "deepseek:flash", None),
        ("gpt-5.6-sol", "openai", "openai:sol", (5, 6)),
        ("gpt-6-astra", "openai", "openai:astra", (6, 0)),
        ("claude-opus-5", "anthropic", "anthropic:opus", (5, 0)),
        ("claude-fable-5-1", "anthropic", "anthropic:fable", (5, 1)),
        ("claude-opus-4-8", "anthropic", "anthropic:opus", (4, 8)),
        ("claude-haiku-4-5-20251001", "anthropic", "anthropic:haiku", (4, 5))):
    r = wm.rozbierz(nazwa)
    sprawdz("%s -> %s %s" % (nazwa, rodzina, wersja),
            r and (r["dostawca"], r["rodzina"], r["wersja"]) == (dostawca, rodzina, wersja), r)
for obca in ("gpt-5.1-codex-max", "gpt-4.1-2025-04-14", "gpt-image-2.5-flare",
             "deepseek-v4-flash-vision-exp", "gpt-realtime-2.1", "claude-3-haiku-20240307"):
    sprawdz("%s nie jest rodzina, ktora porownujemy" % obca, wm.rozbierz(obca) is None)

print()
print("=== 2. DZISIEJSZE LISTY ===")
nowy, powod = wm.nastepca("deepseek-v4-flash", DEEPSEEK_DZIS)
sprawdz("deepseek-v4-flash -> deepseek-flash", nowy == "deepseek-flash", (nowy, powod))
sprawdz("z powodem: zniknal z listy", "zniknal z listy" in powod, powod)
for aktualny, lista in (("deepseek-v4-pro", DEEPSEEK_DZIS),
                        ("claude-opus-5", ANTHROPIC_DZIS),
                        ("claude-fable-5-1", ANTHROPIC_DZIS),
                        ("claude-sonnet-5", ANTHROPIC_DZIS),
                        ("gpt-5.6-sol", OPENAI_DZIS),
                        ("gpt-6-astra", OPENAI_DZIS)):
    sprawdz("%s jest aktualny" % aktualny, wm.nastepca(aktualny, lista) == (None, "aktualny"),
            wm.nastepca(aktualny, lista))
# KONTRDOWODY NA KOLEJNOSC WERSJI — ta sama lista, starsze modele.
sprawdz("claude-opus-4-8 -> claude-opus-5 (4.8 < 5)",
        wm.nastepca("claude-opus-4-8", ANTHROPIC_DZIS)[0] == "claude-opus-5")
sprawdz("claude-fable-5 -> claude-fable-5-1",
        wm.nastepca("claude-fable-5", ANTHROPIC_DZIS)[0] == "claude-fable-5-1")
sprawdz("gpt-5.6-sol nie skacze na gpt-6-astra (inna rodzina)",
        wm.nastepca("gpt-5.6-sol", OPENAI_DZIS)[0] is None)

print()
print("=== 3. LISTY Z PRZYSZLOSCI ===")
sprawdz("deepseek-v4-pro -> deepseek-v4.1-pro",
        wm.nastepca("deepseek-v4-pro", DEEPSEEK_DZIS + ["deepseek-v4.1-pro"])[0]
        == "deepseek-v4.1-pro")
sprawdz("gpt-5.6-sol -> gpt-6-sol",
        wm.nastepca("gpt-5.6-sol", OPENAI_DZIS + ["gpt-6-sol"])[0] == "gpt-6-sol")
sprawdz("claude-opus-5 -> claude-opus-5-1, nie migawka z data",
        wm.nastepca("claude-opus-5", ANTHROPIC_DZIS + ["claude-opus-5-1-20261001",
                                                        "claude-opus-5-1"])[0]
        == "claude-opus-5-1")
sprawdz("sama migawka z data tez jest nastepca",
        wm.nastepca("claude-opus-5", ["claude-opus-5", "claude-opus-5-1-20261001"])[0]
        == "claude-opus-5-1-20261001")
sprawdz("najwyzsza z kilku nowszych",
        wm.nastepca("gpt-5.6-sol", ["gpt-5.6-sol", "gpt-5.7-sol", "gpt-6-sol",
                                    "gpt-5.9-sol"])[0] == "gpt-6-sol")
sprawdz("flash NIGDY nie staje sie pro",
        wm.nastepca("deepseek-v4-flash", ["deepseek-v5-pro"]) [0] is None)
sprawdz("i mowi glosno, ze zniknal bez nastepcy",
        "ZNIKNAL" in wm.nastepca("deepseek-v4-flash", ["deepseek-v5-pro"])[1])
sprawdz("starsza wersja nie jest nastepca",
        wm.nastepca("claude-opus-5", ["claude-opus-4-8"])[0] is None)
sprawdz("alias obok wciaz podawanego modelu NIE przelacza",
        wm.nastepca("deepseek-v4-pro", ["deepseek-v4-pro", "deepseek-pro"])[0] is None)

print()
print("=== 4. PRZELACZENIE W CALOSCI ===")
KATALOG = pathlib.Path(tempfile.mkdtemp())
stary_plik = wm.plik
wm.plik = lambda: KATALOG / "wersje_modeli.json"
STAN = {"role": dict(config.MODEL_FOR),
        "stale": {n: getattr(config, n, None) for n in wm.STALE_Z_MODELEM},
        "flaga": config.MODELE_SAME_NA_NOWSZE, "piny": config.MODELE_NIE_RUSZAJ,
        "proba": wm.sprawdz_na_zywo, "lista": wm.lista_modeli}
wm.lista_modeli = lambda d: (_ for _ in ()).throw(AssertionError("siec w tescie: %s" % d))
proby = []


def ustaw_role():
    config.MODEL_FOR.clear()
    config.MODEL_FOR.update(STAN["role"])
    for n, v in STAN["stale"].items():
        if v is not None:
            setattr(config, n, v)
    config.MODEL_FOR.update({"classify": "deepseek-v4-flash", "wybor": "deepseek-v4-flash",
                             "comment": "deepseek-v4-pro", "note": "gpt-5.6-sol",
                             "restack": "claude-opus-5"})
    config.DEEPSEEK = "deepseek-v4-flash"
    config.MODELE_SAME_NA_NOWSZE = True
    config.MODELE_NIE_RUSZAJ = ()
    (KATALOG / "wersje_modeli.json").unlink(missing_ok=True)
    proby.clear()


def proba_ok(nowy, conn, run_id):
    # PROBA WIDZI KONFIGURACJE JUZ PRZESTAWIONA — tak, jak zobaczy ja produkcja.
    proby.append((nowy, config.MODEL_FOR.get("classify"), config.DEEPSEEK))
    return True, "OK"


try:
    ustaw_role()
    wm.sprawdz_na_zywo = proba_ok
    wynik = wm.sprawdz_i_przelacz(None, None, wymus=True, listy=LISTY_DZIS)
    sprawdz("jedna proba, na nastepcy flasha", [p[0] for p in proby] == ["deepseek-flash"],
            proby)
    sprawdz("proba szla na przestawionej roli i stalej",
            proby and proby[0][1:] == ("deepseek-flash", "deepseek-flash"), proby)
    sprawdz("role flasha przestawione", config.MODEL_FOR["classify"] == "deepseek-flash"
            and config.MODEL_FOR["wybor"] == "deepseek-flash", config.MODEL_FOR)
    sprawdz("stala DEEPSEEK tez", config.DEEPSEEK == "deepseek-flash", config.DEEPSEEK)
    sprawdz("pozostale role nietkniete", config.MODEL_FOR["comment"] == "deepseek-v4-pro"
            and config.MODEL_FOR["note"] == "gpt-5.6-sol")
    zapis = json.loads((KATALOG / "wersje_modeli.json").read_text(encoding="utf-8"))
    sprawdz("zamiana zapisana z data i powodem",
            zapis["zamiany"].get("deepseek-v4-flash", {}).get("na") == "deepseek-flash"
            and zapis["zamiany"]["deepseek-v4-flash"].get("od"), zapis)
    sprawdz("zapisane tez listy dostawcow", zapis.get("listy", {}).get("deepseek") == DEEPSEEK_DZIS)

    # RAZ NA DOBE: drugie wywolanie bez `wymus` nie pyta nikogo.
    proby.clear()
    w2 = wm.sprawdz_i_przelacz(None, None)
    sprawdz("drugie sprawdzenie tej samej doby jest pominiete",
            "sprawdzone" in w2.get("pominiete", "") and proby == [], w2)

    # DARMOWY TEST BEZ PODSTAWIONYCH LIST: ani sieci, ani zapisu. Tak wola to
    # prawdziwe `run.dzien()` w trzech innych darmowych testach.
    (KATALOG / "wersje_modeli.json").unlink()
    w_bez = wm.sprawdz_i_przelacz(None, None, wymus=True)
    sprawdz("bez list w darmowym tescie: pominiete, bez sieci",
            "darmowy test" in w_bez.get("pominiete", ""), w_bez)
    sprawdz("i bez zapisu stanu", not (KATALOG / "wersje_modeli.json").exists())

    # OBLANA PROBA — konfiguracja wraca, zamiany nie ma, odrzucenie zapisane.
    ustaw_role()
    wm.sprawdz_na_zywo = lambda nowy, conn, run_id: (False, "HTTPStatusError: 400")
    wm.sprawdz_i_przelacz(None, None, wymus=True, listy=LISTY_DZIS)
    sprawdz("oblana proba przywraca role", config.MODEL_FOR["classify"] == "deepseek-v4-flash",
            config.MODEL_FOR["classify"])
    sprawdz("i stala", config.DEEPSEEK == "deepseek-v4-flash", config.DEEPSEEK)
    zapis = json.loads((KATALOG / "wersje_modeli.json").read_text(encoding="utf-8"))
    sprawdz("bez zamiany", zapis["zamiany"] == {}, zapis["zamiany"])
    sprawdz("z odrzuceniem i powodem",
            "400" in zapis["odrzucone"].get("deepseek-flash", {}).get("powod", ""), zapis)

    # PRZYPIETY — ani proby, ani zamiany.
    ustaw_role()
    config.MODELE_NIE_RUSZAJ = ("deepseek-v4-flash",)
    wm.sprawdz_na_zywo = proba_ok
    w3 = wm.sprawdz_i_przelacz(None, None, wymus=True, listy=LISTY_DZIS)
    sprawdz("przypiety model bez proby", proby == [], proby)
    sprawdz("i bez zamiany", config.MODEL_FOR["classify"] == "deepseek-v4-flash")
    sprawdz("ale raport mowi o nastepcy", any(n == "deepseek-flash" and "przypiety" in o
                                              for _, n, o in w3["raport"]), w3)

    # WYLACZNIK — sam raport, bez proby i bez zapisu.
    ustaw_role()
    config.MODELE_SAME_NA_NOWSZE = False
    w4 = wm.sprawdz_i_przelacz(None, None, wymus=True, listy=LISTY_DZIS)
    sprawdz("wylaczone: bez proby", proby == [], proby)
    sprawdz("wylaczone: bez pliku", not (KATALOG / "wersje_modeli.json").exists())
    sprawdz("wylaczone: raport nadal widzi nastepce",
            any(n == "deepseek-flash" for _, n, _ in w4["raport"]), w4)

    # BRAK LISTY TO „NIE WIEM", NIE WYCOFANIE.
    ustaw_role()
    w5 = wm.sprawdz_i_przelacz(None, None, wymus=True,
                               listy={"deepseek": None, "anthropic": ANTHROPIC_DZIS,
                                      "openai": OPENAI_DZIS})
    sprawdz("bez listy DeepSeeka nic nie przelaczone", proby == []
            and config.MODEL_FOR["classify"] == "deepseek-v4-flash", proby)
    sprawdz("i raport mowi „nie wiem\"", any("nie wiem" in o for _, _, o in w5["raport"]), w5)
finally:
    config.MODEL_FOR.clear()
    config.MODEL_FOR.update(STAN["role"])
    for n, v in STAN["stale"].items():
        if v is not None:
            setattr(config, n, v)
    config.MODELE_SAME_NA_NOWSZE, config.MODELE_NIE_RUSZAJ = STAN["flaga"], STAN["piny"]
    wm.sprawdz_na_zywo, wm.lista_modeli = STAN["proba"], STAN["lista"]

print()
print("=== 5. NAKLADANIE ZAPISANYCH ZAMIAN PRZY STARCIE ===")


def atrapa_cfg():
    return types.SimpleNamespace(
        MODEL_FOR={"classify": "deepseek-v4-flash", "note": "gpt-5.6-sol",
                   "write": "gpt-6-astra", "obraz": "gpt-image-2"},
        PRICING={"deepseek-v4-flash": {"in": 0.22, "out": 0.66, "cache": 0.007, "verified": True},
                 "gpt-5.6-sol": {"in": 4.0, "out": 20.0, "cache": 0.4, "verified": False},
                 "gpt-6-astra": {"in": 10.0, "out": 50.0, "cache": 1.0, "verified": False}},
        WEB_SEARCH_TOOL={}, STAWKI_PRZED_PODWYZKA={}, DEEPSEEK="deepseek-v4-flash",
        GPT_SOL="gpt-5.6-sol", MODELE_SAME_NA_NOWSZE=True, MODELE_NIE_RUSZAJ=())


def zapisz_zamiany(zamiany):
    (KATALOG / "wersje_modeli.json").write_text(
        json.dumps({"zamiany": zamiany, "odrzucone": {}}), encoding="utf-8")


zapisz_zamiany({"deepseek-v4-flash": {"na": "deepseek-flash"},
                "gpt-5.6-sol": {"na": "gpt-6-sol"}, "gpt-6-sol": {"na": "gpt-6.1-sol"}})
cfg = atrapa_cfg()
zrobione = wm.zastosuj(cfg)
sprawdz("flash nalozony", cfg.MODEL_FOR["classify"] == "deepseek-flash", cfg.MODEL_FOR)
sprawdz("lancuch sol -> 6 -> 6.1 idzie do konca", cfg.MODEL_FOR["note"] == "gpt-6.1-sol"
        and cfg.GPT_SOL == "gpt-6.1-sol", cfg.MODEL_FOR)
sprawdz("model poza zamianami nietkniety", cfg.MODEL_FOR["write"] == "gpt-6-astra")
sprawdz("nieznana cena nastepcy liczona PODWOJNIE i niepotwierdzona",
        cfg.PRICING.get("gpt-6.1-sol") == {"in": 8.0, "out": 40.0, "cache": 0.8,
                                           "verified": False}, cfg.PRICING.get("gpt-6.1-sol"))
sprawdz("zamiany wypisane", ("deepseek-v4-flash", "deepseek-flash") in zrobione, zrobione)

cfg = atrapa_cfg()
cfg.MODELE_NIE_RUSZAJ = ("gpt-5.6-sol",)
wm.zastosuj(cfg)
sprawdz("przypiety przy starcie tez zostaje", cfg.MODEL_FOR["note"] == "gpt-5.6-sol")
cfg = atrapa_cfg()
cfg.MODELE_SAME_NA_NOWSZE = False
sprawdz("wylaczony przelacznik: zero zamian", wm.zastosuj(cfg) == []
        and cfg.MODEL_FOR["classify"] == "deepseek-v4-flash")
wm.plik = stary_plik

print()
print("=== 6. KOSZT NASTEPCY ===")
sprawdz("V4.1 Flash ma wpis w cenniku silnika", "deepseek-flash" in config.PRICING)
# Niedziela 13 wrzesnia 2026, 12:00 UTC — poza szczytem.
poza = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
usd, _ = llm._cost("deepseek-flash", 1_000_000, 1_000_000, 0, 1_000_000, when=poza)
sprawdz("milion wej + milion wyj + milion cache = 0,15 + 0,60 + 0,003",
        abs(usd - 0.753) < 1e-6, usd)
wtorek_szczyt = datetime(2026, 9, 15, 7, 0, tzinfo=timezone.utc)
usd_s, _ = llm._cost("deepseek-flash", 1_000_000, 0, 0, when=wtorek_szczyt)
sprawdz("w szczycie (wtorek 07:00) wejscie dwa razy drozsze", abs(usd_s - 0.30) < 1e-6, usd_s)
sprawdz("taniej niz V4 po staremu", config.PRICING["deepseek-flash"]["in"]
        < config.PRICING["deepseek-v4-flash"]["in"])

print()
print("=== 7. WPIECIE ===")
sprawdz("rola proby istnieje", wm.ROLA_PROBY in config.MODEL_FOR)
sprawdz("rola proby ma sufit dajacy sensowny termin",
        config.timeout_for(config.MAX_TOKENS[wm.ROLA_PROBY]) >= 20,
        config.timeout_for(config.MAX_TOKENS[wm.ROLA_PROBY]))
sprawdz("proba bez myslenia na DeepSeeku", wm.ROLA_PROBY in config.DEEPSEEK_BEZ_MYSLENIA)
sprawdz("darmowy test nie dostaje zamian z danych instancji", config.ZAMIANY_MODELI == [])
ZR_CONFIG = io.open("agent-v2/config.py", encoding="utf-8").read()
sprawdz("zamiany nakladane PO presecie",
        0 <= ZR_CONFIG.find("_preset.zastosuj(") < ZR_CONFIG.find("_wersje_modeli.zastosuj("))
ZR_RUN = io.open("agent-v2/run.py", encoding="utf-8").read()
CIALO = ""
for w in ast.walk(ast.parse(ZR_RUN)):
    if isinstance(w, ast.FunctionDef) and w.name == "dzien":
        CIALO = ast.get_source_segment(ZR_RUN, w) or ""
i_spr = CIALO.find("wersje_modeli.sprawdz_i_przelacz(")
sprawdz("dzien pracy sprawdza wersje", i_spr >= 0)
sprawdz("przed pierwszym budzetem i blokiem", 0 <= i_spr < CIALO.find("stages.budzet_dnia("))
# Sprawdzenie w `try`, zeby awaria listy nie zatrzymala dnia.
opakowane = False
for w in ast.walk(ast.parse(CIALO)):
    if isinstance(w, ast.Try) and "sprawdz_i_przelacz" in ast.dump(ast.Module(body=w.body, type_ignores=[])):
        opakowane = bool(w.handlers)
sprawdz("i jest w try — awaria nie zatrzymuje dnia", opakowane)
ZR_WM = io.open("agent-v2/wersje_modeli.py", encoding="utf-8").read()
sprawdz("proba nastepcy idzie we wlasnym kanale kosztow",
        'db.kanal("modele")' in ZR_WM)
sprawdz("modul nie importuje config na gorze (petla importow)",
        not any(isinstance(w, ast.Import) and any(a.name == "config" for a in w.names)
                for w in ast.parse(ZR_WM).body))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
