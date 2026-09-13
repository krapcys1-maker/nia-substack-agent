# -*- coding: utf-8 -*-
"""Rozmowy NIA: kogo cel, komu odpowiedz, jak konczy, jak czesto.

## Pomiar, ktory to wywolal

13 wrzesnia 2026, 31 komentarzy i 13 odpowiedzi z dziennika serwera (8-13
wrzesnia) razem ze statystykami Substacka:

    komentarze pod ARTYKULAMI   14 ze statystykami   18 wyswietlen   srednio 1,3
    komentarze pod NOTKAMI      14 ze statystykami  157 wyswietlen   srednio 11,2
    odpowiedz pod komentarzem   4 z 31

Artykuly mialy po 6-20 dni. Prawie kazdy komentarz konczyl sie zdaniem
wycelowanym w autora — rozmowa zamykala sie na pierwszym ruchu. Wlasciciel:
20-30 komentarzy dziennie, u nas odpowiedz nie pod kazdym komentarzem, czasem
dyskusja i wrazenie, ze z NIA sie rozmawia.

## Co ten test sprawdza

1. rodzaj komentarza (pytanie, niezgoda, rozmowa, zwykly, pusty, spam);
2. decyzje o odpowiedzi: szansa, pamiec decyzji, koniec rozmowy w watku;
3. przerwy wazone — nadal nie krocej niz piec minut;
4. limit rozmow na godzine liczony z dziennika i wpiety w `rytm`;
5. wiek celu: notka 36 godzin, artykul 3 dni;
6. ruch rozmowy i wlasne ostatnie teksty w prompcie komentarza, nie notki;
7. wpiecie w `run.py` i sprawdzanie wersji modeli przy kazdym przebiegu.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_rozmowy_i_odpowiedzi.py
"""
import ast
import io
import json
import pathlib
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "agent-v2")
import browser        # noqa: E402
import config         # noqa: E402
import kanal          # noqa: E402
import personality    # noqa: E402
import run            # noqa: E402
import stages         # noqa: E402
import wersje_modeli  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


TERAZ = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)

print("=== 1. RODZAJ KOMENTARZA ===")
for tekst, gdzie, oczekiwany in (
        ("Great post!", "", "pusty"),
        ("thanks for sharing", "", "pusty"),
        ("\U0001F525\U0001F525", "", "pusty"),
        ("Why would anyone trust that badge then?", "", "pytanie"),
        ("I disagree, the real cost is review time not tokens", "", "niezgoda"),
        ("check out my substack https://someone.substack.com", "", "spam"),
        ("Subscribe to my newsletter for more takes like this one", "", "spam"),
        ("Totally with you on ownership, that is the missing role", "komentarz_obcy",
         "rozmowa"),
        ("This changes how I think about agents in finance", "", "zwykly"),
        ("The part about loops is exactly what our team keeps hitting", "", "zwykly")):
    wynik = stages.rodzaj_komentarza({"tekst": tekst, "gdzie": gdzie})
    sprawdz("%-58s -> %s" % (tekst[:58], oczekiwany), wynik == oczekiwany, wynik)

print()
print("=== 2. DECYZJE O ODPOWIEDZI ===")
KAT = pathlib.Path(tempfile.mkdtemp())
PLIK = KAT / "decyzje.json"


def komentarz(i, tekst, autor="Ktos", url="https://substack.com/note/c-1", gdzie=""):
    return {"id": i, "tekst": tekst, "autor": autor, "url": url, "gdzie": gdzie,
            "pod_id": 1}


# ROZNI AUTORZY — cztery niezalezne komentarze. Ta sama osoba pod tym samym
# tekstem to juz rozmowa z limitem (sprawdzana osobno nizej).
czekaja = [komentarz(1, "Why would anyone trust that badge then?", autor="Ana"),
           komentarz(2, "Great post!", autor="Ben"),
           komentarz(3, "check out my substack https://someone.substack.com", autor="Cid"),
           komentarz(4, "The part about loops is exactly what our team keeps hitting",
                     autor="Dee")]
# Los 0,5: pytanie (90%) i zwykly (60%) tak, pusty (20%) i spam (0%) nie.
wybrane = stages.zdecyduj_o_odpowiedziach(czekaja, zapisuj=True, los=lambda: 0.5,
                                          plik=PLIK, teraz=TERAZ)
sprawdz("przy losie 0,5: pytanie i zwykly dostaja odpowiedz",
        [k["id"] for k in wybrane] == [1, 4], [k["id"] for k in wybrane])
zapis = json.loads(PLIK.read_text(encoding="utf-8"))
sprawdz("wszystkie cztery decyzje zapisane", len(zapis) == 4, list(zapis))
sprawdz("z typem i szansa", zapis["notka:2"]["typ"] == "pusty"
        and zapis["notka:2"]["decyzja"] == "pomin", zapis["notka:2"])

# PAMIEC: drugi przebieg z losem, ktory przepuscilby wszystko, nie zmienia nic.
wybrane2 = stages.zdecyduj_o_odpowiedziach(czekaja, zapisuj=True, los=lambda: 0.0,
                                           plik=PLIK, teraz=TERAZ + timedelta(hours=3))
sprawdz("kolejny przebieg nie losuje od nowa — pusty i spam nadal pominiete",
        [k["id"] for k in wybrane2] == [1, 4], [k["id"] for k in wybrane2])

# KONTRDOWOD: bez zapisu (proba sucha) nic nie zostaje w pliku.
PLIK_SUCHY = KAT / "sucha.json"
stages.zdecyduj_o_odpowiedziach(czekaja, zapisuj=False, los=lambda: 0.5,
                                plik=PLIK_SUCHY, teraz=TERAZ)
sprawdz("proba sucha niczego nie przesadza", not PLIK_SUCHY.exists())

# ROZMOWA W WATKU MA KONIEC: ta sama osoba, ten sam tekst.
PLIK_W = KAT / "watek.json"
watek = [komentarz(10 + n, "Totally with you on ownership, that is the missing role",
                   autor="Kai", url="https://x.substack.com/p/a", gdzie="komentarz_obcy")
         for n in range(4)]
decyzje = []
for n, k in enumerate(watek):
    decyzje.append(bool(stages.zdecyduj_o_odpowiedziach(
        [k], zapisuj=True, los=lambda: 0.35, plik=PLIK_W,
        teraz=TERAZ + timedelta(hours=n))))
sprawdz("pierwsza odpowiedz w watku: tak (70%)", decyzje[0], decyzje)
sprawdz("druga: tak, ale juz przy mniejszej szansie (40%)", decyzje[1], decyzje)
sprawdz("trzecia i czwarta: nie — rozmowa ma koniec", decyzje[2:] == [False, False],
        decyzje)
inny = stages.zdecyduj_o_odpowiedziach(
    [komentarz(99, "Totally with you on ownership, that is the missing role",
               autor="Kai", url="https://x.substack.com/p/INNY", gdzie="komentarz_obcy")],
    zapisuj=True, los=lambda: 0.35, plik=PLIK_W, teraz=TERAZ + timedelta(hours=5))
sprawdz("ta sama osoba pod INNYM tekstem to nowa rozmowa", bool(inny))

# MILCZENIE MODELU zmienia decyzje na „pomin".
stages.zapamietaj_decyzje(czekaja[0], "pomin", "model nie mial nic do dodania",
                          zapisuj=True, plik=PLIK)
wybrane3 = stages.zdecyduj_o_odpowiedziach(czekaja, zapisuj=True, los=lambda: 0.0,
                                           plik=PLIK, teraz=TERAZ)
sprawdz("komentarz, przy ktorym model zamilkl, nie wraca", [k["id"] for k in wybrane3] == [4],
        [k["id"] for k in wybrane3])

# SPRZATANIE: decyzje starsze niz 30 dni wypadaja przy zapisie.
stary = {"notka:777": {"decyzja": "pomin", "kiedy": (TERAZ - timedelta(days=40)).isoformat()}}
PLIK_S = KAT / "stare.json"
PLIK_S.write_text(json.dumps(stary), encoding="utf-8")
stages.zdecyduj_o_odpowiedziach([komentarz(5, "Why is that so?")], zapisuj=True,
                                los=lambda: 0.0, plik=PLIK_S, teraz=TERAZ)
sprawdz("stare decyzje wypadaja z pliku",
        "notka:777" not in json.loads(PLIK_S.read_text(encoding="utf-8")))

# DARMOWY TEST BEZ WLASNEGO LOSU I PLIKU: wszyscy poza spamem, bez zapisu.
wybrane4 = stages.zdecyduj_o_odpowiedziach(czekaja, zapisuj=True)
sprawdz("w darmowym tescie bez losu odpowiedz dostaja wszyscy poza spamem",
        [k["id"] for k in wybrane4] == [1, 2, 4], [k["id"] for k in wybrane4])
# (Zapis do danych instancji w darmowym tescie pilnuje odcisk katalogu
# w `test_kanal_platnego_wywolania.py`, ktory puszcza prawdziwe `run.dzien()`.)

print()
print("=== 3. PRZERWY WAZONE ===")
import random  # noqa: E402

random.seed(13)
probki = [stages.losuj_odstep("komentarz") for _ in range(4000)]
sprawdz("komentarz nigdy krocej niz 5 min (decyzja wlasciciela)", min(probki) >= 300,
        min(probki))
sprawdz("i nigdy dluzej niz 30 min", max(probki) <= 1800, max(probki))
dlugie = sum(1 for p in probki if p >= 1080) / len(probki)
sprawdz("okolo co dziesiata przerwa dluga (18-30 min)", 0.07 <= dlugie <= 0.13, dlugie)
srednia = sum(probki) / len(probki)
sprawdz("srednia blisko wyliczonej", abs(srednia - stages.sredni_odstep("komentarz")) < 25,
        (srednia, stages.sredni_odstep("komentarz")))
sprawdz("odpowiedz tez nie krocej niz 5 min",
        min(stages.losuj_odstep("odpowiedz") for _ in range(2000)) >= 300)
sprawdz("notka bez koszykow: dalej widelki", 2100 <= stages.losuj_odstep("notka") <= 3900)
sprawdz("srednia notki to srodek widelek", stages.sredni_odstep("notka") == 3000)

print()
print("=== 4. LIMIT ROZMOW NA GODZINE ===")
DZ = KAT / "dziennik.jsonl"
stary_dziennik = browser.DZIENNIK
browser.DZIENNIK = DZ
teraz_ts = TERAZ.timestamp()


def dziennik(*minuty_temu, rodzaj="komentarz"):
    DZ.write_text("\n".join(json.dumps({
        "kiedy": (TERAZ - timedelta(minutes=m)).isoformat(), "rodzaj": rodzaj,
        "udane": True}) for m in minuty_temu) + "\n", encoding="utf-8")


try:
    dziennik(50, 40, 30, 10)
    czekaj = run._do_konca_limitu_rozmow(teraz_ts)
    sprawdz("4 rozmowy w godzinie: czekamy, az najstarsza wypadnie (~10 min)",
            590 <= czekaj <= 660, czekaj)
    dziennik(50, 30, 10)
    sprawdz("3 rozmowy: nie czekamy", run._do_konca_limitu_rozmow(teraz_ts) == 0.0)
    dziennik(90, 80, 70, 10)
    sprawdz("starsze niz godzina sie nie licza", run._do_konca_limitu_rozmow(teraz_ts) == 0.0)
    dziennik(50, 40, 30, 10, rodzaj="notka")
    sprawdz("notki sie nie licza", run._do_konca_limitu_rozmow(teraz_ts) == 0.0)

    # W `rytm`: przerwa wydluzona, gdy limit jest pelny. W darmowym tescie
    # limit jest wylaczony, wiec podnosimy flage na czas tego sprawdzenia.
    dziennik(50, 40, 30, 10)
    oryg = (config.W_TESCIE, stages.losuj_odstep, stages.odczekaj,
            run._pod_rzad_w_bloku, run._do_konca_limitu_rozmow)
    przespane = []
    config.W_TESCIE = False
    stages.losuj_odstep = lambda co: 300.0
    stages.odczekaj = lambda co, ile=None: przespane.append(ile)
    run._pod_rzad_w_bloku = lambda co, na_co: 0
    run._do_konca_limitu_rozmow = lambda teraz=None: 615.0
    run._KONIEC_CZASU = None
    try:
        sprawdz("rytm przepuszcza", run.rytm("komentarz", "komentarze", {"komentarz": True}))
        sprawdz("ale przerwa wydluzona do konca limitu", przespane == [615.0], przespane)
        przespane.clear()
        run.rytm("notka", "notki", {"notka": True})
        sprawdz("notka limitu rozmow nie dotyczy", przespane == [300.0], przespane)
    finally:
        (config.W_TESCIE, stages.losuj_odstep, stages.odczekaj,
         run._pod_rzad_w_bloku, run._do_konca_limitu_rozmow) = oryg
finally:
    browser.DZIENNIK = stary_dziennik

print()
print("=== 5. WIEK CELU ===")


def sprzed(godzin):
    return (datetime.now(timezone.utc) - timedelta(hours=godzin)).isoformat()


sprawdz("notka sprzed 20 h przechodzi", not kanal._za_stary({"rodzaj": "notka", "data": sprzed(20)}))
sprawdz("notka sprzed 40 h odpada", kanal._za_stary({"rodzaj": "notka", "data": sprzed(40)}))
sprawdz("artykul sprzed 2 dni przechodzi", not kanal._za_stary({"rodzaj": "post", "data": sprzed(48)}))
sprawdz("artykul sprzed 4 dni odpada", kanal._za_stary({"rodzaj": "post", "data": sprzed(96)}))
sprawdz("notka bez daty nie odpada", not kanal._za_stary({"rodzaj": "notka", "data": ""}))

print()
print("=== 6. RUCH ROZMOWY I WLASNE OSTATNIE TEKSTY W PROMPCIE ===")
sprawdz("ruch z wag: los 0,1 -> puenta", personality.ruch_rozmowy("comment", 0.1) == "puenta")
sprawdz("los 0,7 -> pytanie", personality.ruch_rozmowy("comment", 0.7) == "pytanie")
sprawdz("los 0,95 -> krotko", personality.ruch_rozmowy("comment", 0.95) == "krotko")
sprawdz("odpowiedz czesciej pyta niz komentarz",
        dict(config.RUCHY_ROZMOWY["reply"])["pytanie"]
        > dict(config.RUCHY_ROZMOWY["comment"])["pytanie"])

browser.DZIENNIK = DZ
DZ.write_text("\n".join(json.dumps(w) for w in (
    {"rodzaj": "komentarz", "udane": True, "tekst": "Stary komentarz o paragonie"},
    {"rodzaj": "notka", "udane": True, "tekst": "notka, nie rozmowa"},
    {"rodzaj": "odpowiedz", "udane": False, "tekst": "nieudana odpowiedz"},
    {"rodzaj": "odpowiedz", "udane": True, "tekst": "Ostatnia odpowiedz"})) + "\n",
    encoding="utf-8")
try:
    wlasne = personality.ostatnie_wlasne_rozmowy()
    sprawdz("z dziennika tylko udane komentarze i odpowiedzi, w kolejnosci",
            wlasne == ["Stary komentarz o paragonie", "Ostatnia odpowiedz"], wlasne)

    zlapane = {}
    oryg_call = personality.llm.call

    def atrapa_llm(role, system, user, **kw):
        zlapane.setdefault(role, []).append(user)
        return json.dumps({"text": "", "topic": ""})

    personality.llm.call = atrapa_llm
    # JEDYNA POPRAWNA DROGA do podstawienia katalogu danych — patrz
    # `test_komplet_sciezek.py`. Szkice persony trafia do katalogu testu.
    stare_dane = config.uzyj_katalogu_danych(KAT / "dane")
    try:
        personality.short_form(None, None, "comment",
                               {"text": "Someone wrote about agent loops.", "author": "Kai"})
        personality.short_form(None, None, "note", {"text": "A fact."})
    finally:
        personality.llm.call = oryg_call
        config.przywroc_katalog_danych(stare_dane)
    prompt_k = (zlapane.get("comment") or [""])[0]
    prompt_n = (zlapane.get("note") or [""])[0]
    sprawdz("komentarz dostaje ruch rozmowy", '"this_move"' in prompt_k, prompt_k[-300:])
    sprawdz("i wlasne ostatnie teksty", "Ostatnia odpowiedz" in prompt_k)
    sprawdz("instrukcja ruchu stoi PO ksztalcie (wygrywa pozniejsza)",
            0 <= prompt_k.find("three or four SHORT LINES")
            < prompt_k.find("context.this_move decides"))
    sprawdz("pytanie nie moze byc pytaniem z szablonu", "never 'what do you think?'" in prompt_k)
    sprawdz("notka NIE dostaje ruchu rozmowy", prompt_n and '"this_move"' not in prompt_n,
            prompt_n[-200:])
finally:
    browser.DZIENNIK = stary_dziennik

print()
print("=== 7. WPIECIE ===")
ZR = io.open("agent-v2/run.py", encoding="utf-8").read()
CIALO = {}
for w in ast.walk(ast.parse(ZR)):
    if isinstance(w, ast.FunctionDef) and w.name in ("odpowiedzi", "komentarze", "zmiesci_sie"):
        CIALO[w.name] = ast.get_source_segment(ZR, w) or ""
o = CIALO.get("odpowiedzi", "")
sprawdz("odpowiedzi: decyzja PRZED wyborem modelem",
        0 <= o.find("stages.zdecyduj_o_odpowiedziach(") < o.find("stages.wybierz_do_odpowiedzi("))
sprawdz("odpowiedzi: zapis tylko przy wysylce", "zapisuj=wyslij" in o)
sprawdz("odpowiedzi: milczenie modelu zapamietane", "stages.zapamietaj_decyzje(" in o)
k = CIALO.get("komentarze", "")
sprawdz("komentarze pod artykulami biora tylko udzial przydzialu",
        "UDZIAL_KOMENTARZY_POD_ARTYKULAMI" in k and "cele[: limit_artykulow]" in k)
sprawdz("zmiesci_sie liczy srednia z koszykow",
        "stages.sredni_odstep(" in CIALO.get("zmiesci_sie", ""))
sprawdz("wersje modeli sprawdzane przy kazdym przebiegu (najwyzej co 3 h)",
        wersje_modeli.WAZNE_GODZIN <= 3, wersje_modeli.WAZNE_GODZIN)
sprawdz("limit rozmow wylaczony w darmowym tescie", "W_TESCIE" in ZR.split("def rytm(")[1][:4000])

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
