"""Ustawienia, ktore wygladaja jak decyzje, a nie robia nic.

Piec usterek jednej rodziny. Trzy pierwsze zmierzone na produkcji, dwie
ostatnie znalezione odczytem kodu — ta roznica jest wazna i wlasnie tego ten
plik pilnuje: usterka zmierzona i usterka utajona to nie to samo.

1. EFFORT ma szesc wpisow i przez trzydziesci dni dotarl do API DOKLADNIE
   JEDEN. Cztery etapy chodza na DeepSeeku, ktory tego pokretla nie czyta,
   a piaty (`forma`) nie wywolal sie ani razu. Wpis czyta sie jak decyzja
   o kosztach i nie robi nic — i nie widac tego nigdzie.

2. Limit MIESIECZNY byl egzekwowany twardym wyjatkiem przed kazdym platnym
   wywolaniem, ale nikt o nim nie ostrzegal. Pierwszym sygnalem bylby agent
   padajacy w polowie artykulu: research oplacony, tekstu nie ma.

3. Okladka powstawala WEWNATRZ galezi `--wyslij`. Kazdy przebieg bez
   publikacji zapisywal artykul bez okladki, a sciezka graficzna sprawdzala
   sie wylacznie na zywo, za prawdziwe pieniadze. Dlatego okladka zgubiona
   przez usterke zapisu wywolan wyszla na jaw dopiero po fakcie.

4. Wybor narzedzia wyszukiwania czytal slownik po nazwie modelu. Model bez
   osobnego wpisu powodowal `KeyError` dopiero w srodku platnego lancucha.

5. `--stop-after` przyjmowal etapy `review` i `forma`, ale po zadnym nie bylo
   zatrzymania; z `--wyslij` przebieg publikowal mimo polecenia stop.
"""
import pathlib
import sys

sys.path.insert(0, "agent-v2")
import config   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


run_src = pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8")
llm_src = pathlib.Path("agent-v2/llm.py").read_text(encoding="utf-8")
alarm_src = pathlib.Path("agent-v2/alarm.py").read_text(encoding="utf-8")

print("=== 1. MARTWY WPIS EFFORT MOWI O SOBIE ===")
sprawdz("EFFORT nadal wyraza intencje dla wszystkich etapow",
        len(config.EFFORT) >= 6, sorted(config.EFFORT))

# TEN TEST BYL LUSTREM. Sprawdzal `"NIE MA SKUTKU" in llm_src`, czyli obecnosc
# NAPISU w pliku — i przechodzil, chociaz ostrzezenie stalo w `_call_claude`,
# do ktorej nie ma jak wejsc nic spoza Claude. Wykrywacz martwych obietnic sam
# byl martwa obietnica. Teraz wolamy `llm.call` naprawde i patrzymy, co wypisze.
import contextlib   # noqa: E402
import io           # noqa: E402
import sqlite3      # noqa: E402
import tempfile     # noqa: E402

import db           # noqa: E402
import llm          # noqa: E402


def _co_wypisze(purpose):
    """Odpala `llm.call` w DRY_RUN i oddaje to, co poszlo na ekran."""
    # `ignore_cleanup_errors` — WINDOWS. Odkad kontrola kluczy przepuszcza
    # ten etap az do zapisu w bazie, `llm.call` dopisuje wiersz do `calls`
    # i sqlite trzyma uchwyt pliku dluzej niz `conn.close()`. Na Linuksie
    # skasowanie otwartego pliku jest legalne, na Windowsie rzuca
    # PermissionError JUZ PO tym, jak test przeszedl wszystkie asercje.
    # Wczesniej tego nie bylo widac, bo wywolanie przerywalo sie przed
    # zapisem — czyli sprzatanie nigdy nie mialo czego kasowac.
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        conn = db.connect(pathlib.Path(tmp) / "t.db")
        run_id = db.start_run(conn)
        llm._EFFORT_BEZ_SKUTKU.clear()
        stary = config.DRY_RUN
        config.DRY_RUN = True
        # ATRAPY KLUCZY. Ten test mierzy, co `llm.call` WYPISUJE, a nie czy
        # potrafi sie uwierzytelnic. Do 2026-09-03 przechodzil bez nich tylko
        # dlatego, ze kontrola wstepna porownywala identyfikatory modeli i nie
        # obejmowala `deepseek-v4-pro` — czyli test korzystal z tej samej luki,
        # ktora byla wada. Po jej zamknieciu klucz jest wymagany, a `DRY_RUN`
        # kilkanascie linii nizej i tak konczy wywolanie przed siecia.
        stare_klucze = (config.ANTHROPIC_API_KEY, config.DEEPSEEK_API_KEY,
                        config.OPENAI_API_KEY)
        config.ANTHROPIC_API_KEY = config.ANTHROPIC_API_KEY or "atrapa-testu"
        config.DEEPSEEK_API_KEY = config.DEEPSEEK_API_KEY or "atrapa-testu"
        config.OPENAI_API_KEY = config.OPENAI_API_KEY or "atrapa-testu"
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                llm.call(purpose, "s", "u", conn=conn, run_id=run_id)
        finally:
            config.DRY_RUN = stary
            (config.ANTHROPIC_API_KEY, config.DEEPSEEK_API_KEY,
             config.OPENAI_API_KEY) = stare_klucze
            conn.close()
        return buf.getvalue()


deepseekowe = [p for p in config.EFFORT
               if config.MODEL_FOR.get(p, "").startswith("deepseek")]
claudowe = [p for p in config.EFFORT
            if not config.MODEL_FOR.get(p, "").startswith("deepseek")]
sprawdz("sa etapy z EFFORT chodzace na DeepSeeku", bool(deepseekowe), deepseekowe)
sprawdz("i sa chodzace na Claude", bool(claudowe), claudowe)

if deepseekowe:
    wyjscie = _co_wypisze(deepseekowe[0])
    sprawdz("etap deepseekowy DOSTAJE ostrzezenie (naprawde, nie w napisie)",
            "NIE MA SKUTKU" in wyjscie, repr(wyjscie[:160]))
    sprawdz("i ostrzezenie nazywa model", config.MODEL_FOR[deepseekowe[0]] in wyjscie)
if claudowe:
    # KONTRDOWOD: tam, gdzie pokretlo DZIALA, nie wolno straszyc.
    sprawdz("etap claudowy NIE dostaje ostrzezenia",
            "NIE MA SKUTKU" not in _co_wypisze(claudowe[0]))
# Raz na proces: drugie wywolanie tego samego etapu ma juz milczec.
if deepseekowe:
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp2:
        c2 = db.connect(pathlib.Path(tmp2) / "t.db")
        r2 = db.start_run(c2)
        llm._EFFORT_BEZ_SKUTKU.clear()
        st = config.DRY_RUN
        config.DRY_RUN = True
        # ATRAPY KLUCZY, ten sam powod co w `_co_wypisze` wyzej: mierzymy, co
        # `llm.call` WYPISUJE, a nie czy potrafi sie uwierzytelnic.
        _stare = (config.ANTHROPIC_API_KEY, config.DEEPSEEK_API_KEY,
                  config.OPENAI_API_KEY)
        config.ANTHROPIC_API_KEY = config.ANTHROPIC_API_KEY or "atrapa-testu"
        config.DEEPSEEK_API_KEY = config.DEEPSEEK_API_KEY or "atrapa-testu"
        config.OPENAI_API_KEY = config.OPENAI_API_KEY or "atrapa-testu"
        b1, b2 = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(b1):
            llm.call(deepseekowe[0], "s", "u", conn=c2, run_id=r2)
        with contextlib.redirect_stdout(b2):
            llm.call(deepseekowe[0], "s", "u", conn=c2, run_id=r2)
        config.DRY_RUN = st
        (config.ANTHROPIC_API_KEY, config.DEEPSEEK_API_KEY,
         config.OPENAI_API_KEY) = _stare
        c2.close()
        sprawdz("pierwsze wywolanie mowi", "NIE MA SKUTKU" in b1.getvalue())
        sprawdz("drugie juz milczy", "NIE MA SKUTKU" not in b2.getvalue())
# I sprawdzenie, ze ostrzezenie NIE wrocilo do funkcji, ktora go nie widzi.
import ast as _ast   # noqa: E402
for _w in _ast.walk(_ast.parse(llm_src)):
    if isinstance(_w, _ast.FunctionDef) and _w.name == "_call_claude":
        _seg = _ast.get_source_segment(llm_src, _w) or ""
        sprawdz("ostrzezenia nie ma w _call_claude (tam jest nieosiagalne)",
                "NIE MA SKUTKU" not in _seg)
# KONTRDOWOD: samo ostrzezenie nie moze zastapic dzialania tam, gdzie pokretlo
# DZIALA. Model Claude ma nadal dostawac output_config.
sprawdz("na Claude pokretlo nadal dziala",
        'kwargs["output_config"] = {"effort": config.EFFORT[purpose]}' in llm_src)
sprawdz("i komentarz nazywa granice: to pokretlo tylko dla Claude",
        "POKRETLO WYLACZNIE DLA MODELI CLAUDE"
        in pathlib.Path("agent-v2/config.py").read_text(encoding="utf-8"))
# DeepSeek ma osobne, JEDNO pokretlo i ma nim zostac.
sprawdz("DeepSeek ma swoje osobne ustawienie",
        isinstance(config.DEEPSEEK_EFFORT, str) and config.DEEPSEEK_EFFORT)

print()
print("=== 2. LIMIT MIESIECZNY: OSTRZEGA, ZANIM ZATRZYMA ===")
sprawdz("alarm patrzy tez na miesiac", "MONTHLY_LIMIT_USD" in alarm_src)
sprawdz("i mowi, ile dni zostalo", "zostalo_dni" in alarm_src)
# Prog dzienny liczy sie teraz z `sufit_dnia(dzien)`, a nie ze stalej
# `DAILY_LIMIT_USD`. Powod: alarm patrzy takze na WCZORAJ, a wczoraj sufit
# mogl byc inny (podniesienie wygasa samo o polnocy). 31 sierpnia alarm
# doniosl „Wczoraj wydane $7.22 przy suficie $5.0" w dniu, w ktorym
# obowiazywal sufit dziesieciu dolarow.
sprawdz("prog miesieczny jest nizszy niz dzienny",
        "MONTHLY_LIMIT_USD * 0.75" in alarm_src
        and "sufit * 0.9" in alarm_src)
sprawdz("sufit dzienny brany z TAMTEGO dnia, nie z dzisiaj",
        "config.sufit_dnia(dzien)" in alarm_src)
# NIE ZACZYNAJ TEGO, CZEGO NIE SKONCZYSZ — ta sama zasada co przy przerwach.
sprawdz("artykul nie startuje, gdy miesiac nie udzwignie calego",
        "MIESIAC NA WYCZERPANIU" in run_src)
sprawdz("i porownuje sie z kosztem CALEGO przebiegu, nie jednego wywolania",
        "config.RUN_LIMIT_USD" in run_src.split("MIESIAC NA WYCZERPANIU")[0][-700:])
sprawdz("limity sa uporzadkowane: przebieg < doba < miesiac",
        config.RUN_LIMIT_USD < config.DAILY_LIMIT_USD < config.MONTHLY_LIMIT_USD,
        (config.RUN_LIMIT_USD, config.DAILY_LIMIT_USD, config.MONTHLY_LIMIT_USD))
# KONTRDOWOD: doba musi udzwignac co najmniej jeden caly artykul, inaczej
# artykul nie powstalby NIGDY, a agent milczalby o przyczynie.
sprawdz("doba udzwignie caly artykul",
        config.DAILY_LIMIT_USD >= config.RUN_LIMIT_USD * 2,
        (config.DAILY_LIMIT_USD, config.RUN_LIMIT_USD))

print()
print("=== 3. OKLADKA POWSTAJE Z ARTYKULEM, NIE Z PUBLIKACJA ===")
przed_publikacja = run_src.split("if args.wyslij:")
sprawdz("galaz publikacji istnieje", len(przed_publikacja) >= 2)
# Grafika ma stac PRZED galezia publikacji — czyli w czesci wspolnej.
i_graf = run_src.find("stages.grafika(")
i_wyslij = run_src.find("if args.wyslij:\n            import browser")
sprawdz("grafika jest wolana", i_graf > 0)
sprawdz("i stoi PRZED galezia publikacji", 0 < i_graf < i_wyslij,
        (i_graf, i_wyslij))
# KONTRDOWOD: przeniesienie nie moze zabrac jej wciecia funkcji — gdyby
# wyladowala na poziomie modulu, wolalaby sie przy imporcie.
linia_graf = next(l for l in run_src.splitlines() if "stages.grafika(" in l)
sprawdz("z wcieciem ciala funkcji, nie modulu",
        linia_graf.startswith("        stages.grafika("), repr(linia_graf[:24]))
# OBIETNICA MIERZONA NA DRZEWIE SKLADNI, NIE PO NAPISIE.
#
# Stalo tu `"NIGDY nie zatrzymuje" in run_src`. Jedyne wystapienie tego napisu
# w `run.py` to KOMENTARZ nad wywolaniem — wiec mozna bylo usunac oslone
# `try/except` i zostawic komentarz, a test przechodzilby dalej, podczas gdy
# padnieta grafika zabijalaby artykul za czterdziesci dolarow researchu.
#
# Pytamy wiec o to, co naprawde chroni: czy wywolanie `stages.grafika` stoi
# wewnatrz bloku `try` z obsluga wyjatku, i czy sama `grafika` lapie awarie
# u siebie. Komentarz tego nie spelni.
import ast as _ast_g
_drzewo_run = _ast_g.parse(run_src)
_wolania = [n for n in _ast_g.walk(_drzewo_run) if isinstance(n, _ast_g.Call)
            and getattr(getattr(n.func, "value", None), "id", "") == "stages"
            and getattr(n.func, "attr", "") == "grafika"]
sprawdz("wywolanie grafiki jest w drzewie", len(_wolania) == 1, len(_wolania))
_oslonione = []
for _t in [n for n in _ast_g.walk(_drzewo_run) if isinstance(n, _ast_g.Try) and n.handlers]:
    _oslonione += [w for w in _wolania if any(w is c for c in _ast_g.walk(_t))]
sprawdz("i stoi POD try z obsluga wyjatku", len(_oslonione) == len(_wolania),
        "oslonionych %d z %d" % (len(_oslonione), len(_wolania)))

_drzewo_st = _ast_g.parse(pathlib.Path("agent-v2/stages.py").read_text(encoding="utf-8"))
_graf = next((n for n in _ast_g.walk(_drzewo_st)
              if isinstance(n, _ast_g.FunctionDef) and n.name == "grafika"), None)
sprawdz("`stages.grafika` istnieje", _graf is not None)
_lapie = [h for t in _ast_g.walk(_graf or _ast_g.Module(body=[], type_ignores=[]))
          if isinstance(t, _ast_g.Try) for h in t.handlers] if _graf else []
sprawdz("i sama lapie awarie u siebie", len(_lapie) >= 2,
        "blokow obslugi: %d" % len(_lapie))

print()
print("=== 4. KAZDY MODEL ANTHROPIC UMIE SZUKAC ===")
# Bylo `config.WEB_SEARCH_TOOL[model]` — surowy odczyt ze slownika, ktory mial
# wpisy tylko dla dwoch modeli. Trzeci, `claude-fable-5`, to ten, NA KTORYM
# CHODZI PISARZ. KeyError wypadalby w srodku platnego wywolania, po oplaceniu
# wszystkich wczesniejszych etapow — czyli w najdrozszym mozliwym miejscu.
sprawdz("kazdy model Claude z routingu ma wpis albo galaz awaryjna",
        all(config.narzedzie_wyszukiwania(m)[0]
            for m in (config.CLAUDE, config.SONNET, config.FABLE)))
for m in (config.CLAUDE, config.SONNET, config.FABLE):
    sprawdz("  %s bez ostrzezenia (ma wlasny wpis)" % m,
            config.narzedzie_wyszukiwania(m)[1] == "")
# KONTRDOWOD: nieznany model NIE moze wywalic przebiegu, ale MUSI byc slyszalny.
nazwa, uwaga = config.narzedzie_wyszukiwania("claude-czegos-takiego-nie-ma")
sprawdz("nieznany model dostaje narzedzie zamiast wyjatku", bool(nazwa))
sprawdz("i glosne ostrzezenie", "nie ma wpisu w WEB_SEARCH_TOOL" in uwaga)
sprawdz("llm nie czyta juz slownika wprost",
        "config.WEB_SEARCH_TOOL[" not in llm_src)
sprawdz("tylko przez funkcje", "_narzedzie_wyszukiwania(model)" in llm_src)
sprawdz("i mowi o braku raz na proces", "_WYSZUKIWANIE_BEZ_WPISU" in llm_src)
# Kazdy model uzywany przez etapy z web_search musi byc obslugiwany.
modele_z_routingu = {m for m in config.MODEL_FOR.values()
                     if m.startswith("claude")}
sprawdz("zaden model z routingu nie wywala sie na wyszukiwaniu",
        all(config.narzedzie_wyszukiwania(m)[0] for m in modele_z_routingu),
        sorted(modele_z_routingu))

print()
print("=== 5. --stop-after ZATRZYMUJE NA KAZDYM ETAPIE, KTORY PRZYJMUJE ===")
# `review` i `forma` byly w STAGES, wiec argparse przyjmowal je jako
# `--stop-after` bez slowa sprzeciwu — a po nich NIE BYLO ani jednego
# sprawdzenia. `--stop-after review --wyslij` szedl do konca i PUBLIKOWAL.
#
# Flaga, ktora ma zatrzymac przed publikacja, a publikuje, jest gorsza od jej
# braku: brak widac od razu, cicha bezczynnosc dopiero po fakcie — czyli po
# opublikowaniu tekstu, ktory mial poczekac.
import ast as _a   # noqa: E402
import re as _r    # noqa: E402

drzewo_run = _a.parse(run_src)
STAGES = None
for _w in drzewo_run.body:
    if (isinstance(_w, _a.Assign) and len(_w.targets) == 1
            and isinstance(_w.targets[0], _a.Name)
            and _w.targets[0].id == "STAGES"):
        STAGES = [e.value for e in _w.value.elts]
sprawdz("STAGES istnieje i nie jest pusta", bool(STAGES), STAGES)

# Ktory etap ma po sobie sprawdzenie: idziemy liniami, tak jak wykonuje sie kod.
biezacy, honorowane = None, set()
for _l in run_src.splitlines():
    _m = _r.search(r'^\s*stage = "([a-z_]+)"', _l)
    if _m:
        biezacy = _m.group(1)
    if "args.stop_after ==" in _l:
        # Sprawdzenie moze porownywac ze zmienna `stage` albo z nazwa wprost.
        _n = _r.search(r'args\.stop_after == "([a-z_]+)"', _l)
        honorowane.add(_n.group(1) if _n else biezacy)

if STAGES:
    bez_zatrzymania = [e for e in STAGES if e not in honorowane]
    sprawdz("kazdy etap z STAGES da sie zatrzymac", not bez_zatrzymania,
            bez_zatrzymania)
    # KONTRDOWOD: test bylby pusty, gdyby `honorowane` bylo puste albo gdyby
    # zbieral nazwy spoza STAGES. Wymagamy realnego pokrycia.
    sprawdz("i sprawdzen jest tyle, ile etapow", len(honorowane) >= len(STAGES),
            "%d wobec %d" % (len(honorowane), len(STAGES)))
    sprawdz("dwa etapy, ktore wczesniej wypadaly, sa objete",
            {"review", "forma"} <= honorowane, sorted(honorowane))
# Argparse nie moze przyjmowac nazwy, ktorej nie ma w STAGES — inaczej wracamy
# do punktu wyjscia inna droga.
sprawdz("lista wyboru argparse to dokladnie STAGES",
        "choices=STAGES" in run_src or "choices=list(STAGES)" in run_src)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
