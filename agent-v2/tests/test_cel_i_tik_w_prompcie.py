# -*- coding: utf-8 -*-
"""Dwie rzeczy, ktore kod WIEDZIAL i nigdy nie powiedzial modelowi.

1. `co_dodamy` — `wybierz_cele` zapisuje przy kazdym przyjetym celu jedno
   konkretne zdanie o tym, co MY mamy tu do dodania. `prompts/cele.md` czyni z
   tego trzeci warunek dopuszczenia celu: „If you cannot say concretely what
   you would add, the answer is no". Grep po repozytorium: pole bylo zapisywane
   w jednej linii i czytane w ZERU. Komentarz pisal sie od zera, nie wiedzac,
   za co ten post zostal wybrany.

2. Tik „nie X. Y." — `candidates.sort` w `note()` ma dwa kryteria: powtorzone
   otwarcie i ten tik. Otwarcia dostaly zamiennik w prompcie
   (`ostatnie_otwarcia_json`), po czym `NOTE_CANDIDATES` spadlo do JEDNEGO —
   a sortowanie listy jednoelementowej nie robi nic. Tik, zmierzony w 16 z 30
   wystawionych notek (53%), nie byl wiec pilnowany przez nic: prompt nie
   wspominal o nim ani slowem.
"""
import contextlib
import hashlib
import io
import json
import pathlib
import sys

sys.path.insert(0, "agent-v2")
import config   # noqa: E402
import stages   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


def odcisk(p):
    p = pathlib.Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else "brak"


PILNOWANE = [config.DB_PATH, config.DATA_DIR / "dziennik.jsonl"]
PRZED = {str(p): odcisk(p) for p in PILNOWANE}

widziane = {}
# CO ATRAPA ODDAJE MODELOWI DO PRZETLUMACZENIA. Do 2 wrzesnia ten plik
# podmienial takze `llm.parse_json` na lambde ignorujaca `raw` — czyli omijal
# jedyna funkcje, ktora tlumaczy odpowiedz modelu na ksztalt oczekiwany przez
# kod. Trzydziesci linii obslugi prozy wokol JSON-a, ktorej wlasny docstring
# podaje koszt awarii („dwadziescia wyszukiwan i 0,13 USD, po czym oddalo
# zero"), nie bylo w tescie dotkniete ani razu.
#
# Teraz podmieniamy WYLACZNIE `call` i oddajemy `json.dumps({...})`.
odpowiedz = {"tresc": "{}"}


def odpowiada(dane):
    """Ustawia, co atrapa modelu odda w SUROWEJ postaci.

    Z PROZA WOKOL JSON-A, i to z nawiasem w srodku — bo dokladnie na tym
    `parse_json` raz juz poleglo: naiwny wycinek „od pierwszego { do
    ostatniego }" lapal nawias ze zdania i caly etap przepadal.
    """
    odpowiedz["tresc"] = (
        "Working on it. I will return one object {like this} and nothing else."
        "\n\n" + json.dumps(dane, ensure_ascii=False)
        + "\n\nThat is the whole answer.")


def przechwyc_prompt(rodzaj, system, prompt, conn=None, run_id=None, **k):
    widziane["prompt"] = prompt
    return odpowiedz["tresc"]


ORYG_CALL, ORYG_PARSE = stages.llm.call, stages.llm.parse_json
ORYG_WERYF = stages.zweryfikuj
ORYG_TEKSTY, ORYG_OTWARCIA = stages.teksty_ostatnich_notek, stages.ostatnie_otwarcia

CO_DODAMY = ("The post treats the model's refusal as a safety decision; the "
             "provider's own docs call it a routing fallback.")

print("=== 1. `co_dodamy` POWSTAJE PRZY WYBORZE CELU ===")
zrodlo = pathlib.Path("agent-v2/stages.py").read_text(encoding="utf-8")
sprawdz("wybierz_cele zapisuje pole", '"co_dodamy": o.get("what_i_would_add"' in zrodlo)
_cele = (config.PROMPTS_DIR / "cele.md").read_text(encoding="utf-8")
sprawdz("i prompt celow czyni z tego warunek dopuszczenia",
        "If you cannot say concretely what you would add" in _cele)

print()
print("=== 2. I TRAFIA DO PROMPTU KOMENTARZA ===")
try:
    stages.llm.call = przechwyc_prompt
    odpowiada({"comment": None, "reason_if_silent": "nic do dodania"})
    stages.zweryfikuj = lambda *a, **k: {"claims": [], "safe_to_post": True}
    with contextlib.redirect_stdout(io.StringIO()):
        stages.comment_on(None, 0, {"url": "https://x/p/a", "title": "T",
                                    "text": "cudzy tekst posta", "author": "A",
                                    "co_dodamy": CO_DODAMY})
    z_polem = widziane["prompt"]
    sprawdz("zdanie o tym, co dodajemy, jest w prompcie", CO_DODAMY in z_polem)
    sprawdz("i jest opisane jako NASZA notatka, nie jako tresc autora",
            "WHY THIS POST WAS SELECTED" in z_polem)
    # CISZA PRZESTALA BYC OPCJA — 2 wrzesnia 2026. Do tego dnia prompt mowil
    # „stay silent instead", czyli sam oferowal modelowi wyjscie bez publikacji.
    # Doktryna mowi odwrotnie: co zaplanowane, to wychodzi, lepiej z bledem niz
    # wcale. To bylo tez jedyne, co blokowalo przekazanie notatki do promptu.
    sprawdz("BEZ pozwolenia na milczenie", "stay silent" not in z_polem)
    sprawdz("i z jawnym poleceniem, zeby napisac cokolwiek",
            "but write something" in z_polem)
    sprawdz("cudzy tekst nadal jest w prompcie", "cudzy tekst posta" in z_polem)

    # KONTRDOWOD: bez pola prompt wyglada dokladnie jak przed poprawka.
    with contextlib.redirect_stdout(io.StringIO()):
        stages.comment_on(None, 0, {"url": "https://x/p/a", "title": "T",
                                    "text": "cudzy tekst posta", "author": "A"})
    bez_pola = widziane["prompt"]
    sprawdz("KONTRDOWOD: bez `co_dodamy` nie dopisujemy nic",
            "WHY THIS POST WAS SELECTED" not in bez_pola)
    sprawdz("i wtedy prompt jest krotszy", len(bez_pola) < len(z_polem),
            (len(bez_pola), len(z_polem)))

    print()
    print('=== 3. TIK „nie X. Y.” IDZIE DO MODELU JAKO JEGO WLASNE ZDANIA ===')
    NASZE_Z_TIKIEM = [
        "It was a cost-cutting move, not a tradition.",
        "A quarter less oxygen is a weight decision, not bad luck.",
        "The number is not a measurement, it is a band.",
    ]
    stages.teksty_ostatnich_notek = lambda ile=40: list(NASZE_Z_TIKIEM)
    stages.ostatnie_otwarcia = lambda rodzaj="notka", ile=8: []
    odpowiada({"note": "x " * 40, "words": 40})
    with contextlib.redirect_stdout(io.StringIO()):
        stages.note(None, 0, "MYSL", {"o_czym_sie_mowi": "x"})
    z_tikiem = widziane["prompt"]
    sprawdz("prompt nazywa ruch podpisem konta",
            "signature" in z_tikiem and "16 of our last" in z_tikiem)
    for z in NASZE_Z_TIKIEM:
        sprawdz("i pokazuje wlasne zdanie: %s" % z[:38], z in z_tikiem)

    # KONTRDOWOD 1: gdy w ostatnich notkach tiku nie ma, nie dopisujemy nic —
    # inaczej model dostawalby zarzut bez dowodu przy kazdej notce.
    stages.teksty_ostatnich_notek = lambda ile=40: [
        "The model does not keep the conversation. Every turn ships it back."]
    with contextlib.redirect_stdout(io.StringIO()):
        stages.note(None, 0, "MYSL", {"o_czym_sie_mowi": "x"})
    sprawdz("KONTRDOWOD: czyste notki -> zadnego dopisku",
            "signature" not in widziane["prompt"])
    # KONTRDOWOD 2: sam prompt notki nadal nie mowi o tym ruchu ani slowa,
    # wiec to jest jedyne miejsce, w ktorym model sie o nim dowiaduje.
    _n = (config.PROMPTS_DIR / "notka.md").read_text(encoding="utf-8")
    sprawdz("KONTRDOWOD: prompts/notka.md nadal o tiku milczy",
            "not a tradition" not in _n and "signature" not in _n)

    print()
    print("=== 4. SORTOWANIE PO TIKU JEST DZIS MARTWE — I DLATEGO TO POWSTALO ===")
    sprawdz("kandydat notki jest JEDEN", config.NOTE_CANDIDATES == 1,
            config.NOTE_CANDIDATES)
    jeden = [{"note": "The queue is not the answer, it is the wait."}]
    posortowany = sorted(jeden, key=lambda d: stages.kuplet_korygujacy(d["note"]))
    sprawdz("sortowanie listy jednoelementowej niczego nie zmienia",
            posortowany == jeden)
    sprawdz("chociaz tik w tym zdaniu JEST",
            stages.kuplet_korygujacy(jeden[0]["note"]))

    print()
    print("=== 5. LOG NIE KLAMIE O TYM, CO ZA CHWILE ZROBI ===")
    stages.teksty_ostatnich_notek = lambda ile=40: []
    stages.ostatnie_otwarcia = lambda rodzaj="notka", ile=8: ["the"]
    odpowiada({"note": "The " + "word " * 40, "words": 41})
    bufor = io.StringIO()
    with contextlib.redirect_stdout(bufor):
        wynik = stages.note(None, 0, "CIEKAWOSTKA", {"fact": {"fact": "x"}})
    log = bufor.getvalue()
    sprawdz('komunikat mowi o JEDNYM kandydacie, nie o „wszystkich”',
            "kandydat zaczyna jak poprzednie notki" in log, log)
    sprawdz("i mowi wprost, ze notka i tak idzie", "wystawiam mimo to" in log, log)
    sprawdz("bo naprawde idzie",
            wynik["candidates"][0].get("safe_to_post") is True,
            wynik["candidates"][0].get("safe_to_post"))
    sprawdz("KONTRDOWOD: stare zdanie zniknelo z kodu",
            "(wszyscy kandydaci zaczynaja jak poprzednie notki)" not in zrodlo)
finally:
    stages.llm.call, stages.llm.parse_json = ORYG_CALL, ORYG_PARSE
    stages.zweryfikuj = ORYG_WERYF
    stages.teksty_ostatnich_notek, stages.ostatnie_otwarcia = ORYG_TEKSTY, ORYG_OTWARCIA

print()
print("=== 6. CZEGO BRAKUJE POZA TYM PLIKIEM ===")
# `run.py` podaje do `comment_on` strone z `read_pages` ({url, text, title,
# error}), wiec `co_dodamy` gubi sie ZANIM dojdzie do stages.py. Naprawa jest
# jednolinijkowa i nalezy do wlasciciela `run.py` — tutaj tylko o niej mowimy,
# bo test, ktory jej wymaga, oblewalby sie do czasu tamtej zmiany.
_run = pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8")
print("  UWAGA  run.py %s przekazuje `co_dodamy` do comment_on"
      % ("juz" if "co_dodamy" in _run else "JESZCZE NIE"))
print("         potrzebne: stages.comment_on(conn, run_id,")
print("                        {**strony[0], \"co_dodamy\": cel.get(\"co_dodamy\", \"\")})")
sprawdz("stages.py jest gotowy na to pole (czyta je, nie tylko zapisuje)",
        'post.get("co_dodamy")' in zrodlo)

print()
print("=== PRODUKCJA ===")
zle = 0
for p in PILNOWANE:
    ok = odcisk(p) == PRZED[str(p)]
    zle += 0 if ok else 1
    print("  %-24s %s" % (pathlib.Path(p).name, "bez zmian" if ok else "ZMIENIONA"))

print()
print("=== WYNIK: %d zdanych, %d oblanych%s ===" %
      (zdane, oblane, ", PRODUKCJA RUSZONA" if zle else ""))
sys.exit(1 if (oblane or zle) else 0)
