"""Caly lancuch wyboru tematu: skaut -> nasycenie -> watki -> pick_topic.

DLACZEGO. Skaut oddal dwanascie tematow i siedem z nich bylo kanonem
internetowego mythbustingu: zraszacze, ktore nie odpalaja wszystkie naraz,
chusteczki „flushable", karta hotelowa przy telefonie, mydlo antybakteryjne,
maszyna z pluszakami, data waznosci na lekach, wodoodpornosc telefonu.
O kazdym z nich sa tysiace tekstow.

AUDYT WYKAZAL TRZY PRZYCZYNY, wszystkie w kodzie, nie w modelu:

1. `pick_topic` sortowal po `ma_przekonanie` jako PIERWSZYM kluczu — a temat
   oklepany ma z definicji najostrzejsze „wszyscy zakladaja", bo dokladnie
   dlatego zostal oklepany. Ranking wybieral wiec cliche z KONSTRUKCJI.
2. `ma_stawke` w ogole nie bylo w tym rankingu. Skaut stawial systemy pod proba
   na czele, a wybor tematu spychal je na sam dol — piec dobrych tematow
   z przebiegu 20 sierpnia nie zostaloby wybranych NIGDY.
3. Skaut liczyl siedem ocen (w tym `originality`), ktorych NIE CZYTALA ani jedna
   linia kodu. Samoocena i tak dryfuje do gornej granicy, wiec nie byla warta
   naprawiania — zostala usunieta i zastapiona faktami do sprawdzenia.

Zamiast oceny: model wymienia, co jego zdaniem JUZ o tym napisano. Uzywamy jego
pamieci przeciw niemu — dostepnosc jest odwrotnoscia sygnalu, ktorego szukamy.
"""
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


def przetworz(topics, ranking=None):
    """Odtwarza petle ze `scout` — te sama, ktora liczy nosnosc i nasycenie."""
    for t in topics:
        wiara = str(t.get("broken_belief") or "").strip()
        t["ma_przekonanie"] = len(wiara.split()) >= 5
        moment = str(t.get("the_moment") or "").strip()
        wynik = str(t.get("open_outcome") or "").strip()
        zapis = str(t.get("governing_record") or "").strip()
        t["ma_stawke"] = (len(moment.split()) >= 4 and len(wynik.split()) >= 4
                          and len(zapis.split()) >= 3)
        t["nosny"] = bool(t["ma_przekonanie"] or t["ma_stawke"])
        juz = t.get("already_written")
        t["ile_juz_napisano"] = len(juz) if isinstance(juz, list) else 0
        t["nasycony"] = t["ile_juz_napisano"] >= config.NASYCENIE_OD_ILU
        w = t.get("threads")
        t["ile_watkow"] = len(w) if isinstance(w, list) else 0
        t["pozycja"] = 0
        prec = t.get("precedents") if isinstance(t.get("precedents"), list) else []
        t["precedensy"] = [q for q in prec if stages._precedens_ok(q)]
        t["ile_precedensow"] = len(t["precedensy"])
        t["zasieg"] = str(t.get("scale") or "").strip().upper()
        t["duzy_zasieg"] = t["zasieg"] in config.ZASIEGI_ARTYKULOWE
        t["na_artykul"] = (t["ile_precedensow"] >= config.PRECEDENSOW_NA_ARTYKUL
                           and t["duzy_zasieg"])
    r = ranking or {}
    for i in r.get("least_written_about", []):
        topics[i]["pozycja"] += 2; topics[i]["swiezy_wg_modelu"] = True
    for i in r.get("most_written_about", []):
        topics[i]["pozycja"] -= 2; topics[i]["oklepany_wg_modelu"] = True
    for i in r.get("richest", []):
        topics[i]["pozycja"] += 1
    for i in r.get("thinnest", []):
        topics[i]["pozycja"] -= 1
    topics.sort(key=lambda t: (not t["nosny"], not t["na_artykul"],
                               -t["pozycja"], t["nasycony"], -t["ile_watkow"]))
    return topics


# --- PRAWDZIWE tematy z przebiegu 20 sierpnia, nie wymyslone -----------------
CLICHE = {
    "title": "Example Article Eight", "kind": "BROKEN_BELIEF",
    "broken_belief": "Everyone assumes wipes labelled flushable break down in "
                     "water the way toilet paper does.",
    "already_written": ["utility companies on fatbergs",
                        "consumer testing of flushable claims",
                        "city sewer department warnings"],
    "threads": ["what the label legally means"],
}
CLICHE2 = {
    "title": "Example Article Seven", "kind": "BROKEN_BELIEF",
    "broken_belief": "Everyone assumes antibacterial soap kills more germs than plain.",
    "already_written": ["regulator ban coverage", "handwashing guidance pieces"],
    "threads": ["what the regulator actually banned"],
}
SWIEZY = {
    "title": "Example Article Sixteen at the Polling Place", "kind": "SYSTEM_UNDER_TEST",
    "the_moment": "a voter arrives and the machines are down",
    "open_outcome": "what happens to my vote if the machine fails while I am using it",
    "governing_record": "election statutes and provisional ballot rules",
    "already_written": [],
    "threads": ["what happens to a vote already cast",
                "who may authorise paper ballots",
                "how long a polling place may stay shut",
                "what happens to the count afterwards"],
}
SWIEZY2 = {
    "title": "The Bet Cut Short", "kind": "SYSTEM_UNDER_TEST",
    "the_moment": "a match you have money on is stopped midway",
    "open_outcome": "do I get my stake back or is it settled on the score so far",
    "governing_record": "sportsbook house rules and regulator codes",
    "already_written": [],
    "threads": ["when a stake is returned", "who decides a match is abandoned"],
}

print("=== 1. NASYCENIE: PAMIEC MODELU UZYTA PRZECIW NIEMU ===")
t = przetworz([dict(CLICHE), dict(SWIEZY)])
sprawdz("próg nasycenia to 2", config.NASYCENIE_OD_ILU == 2, config.NASYCENIE_OD_ILU)
c = next(x for x in t if x["title"] == CLICHE["title"])
s = next(x for x in t if x["title"] == SWIEZY["title"])
sprawdz("cliché rozpoznane jako nasycone", c["nasycony"] is True, c["ile_juz_napisano"])
sprawdz("świeży temat nie jest nasycony", s["nasycony"] is False)
sprawdz("świeży idzie PRZED cliché", t[0]["title"] == SWIEZY["title"],
        [x["title"][:26] for x in t])
# KONTRDOWOD: jeden przypomniany tekst zdarza sie przy kazdym istniejacym
# temacie. Prog jeden zabilby wszystko.
jeden = przetworz([dict(CLICHE, already_written=["jakis tekst"])])[0]
sprawdz("jeden znany tekst NIE wystarcza", jeden["nasycony"] is False)

print()
print("=== 2. WATKI: JEDEN TEMAT NA PIEC ARTYKULOW BIJE PIEC NA JEDEN ===")
sprawdz("cliché ma jeden wątek", c["ile_watkow"] == 1, c["ile_watkow"])
sprawdz("świeży ma cztery", s["ile_watkow"] == 4, s["ile_watkow"])
t = przetworz([dict(SWIEZY2), dict(SWIEZY)])
sprawdz("przy równym nasyceniu wygrywa więcej wątków",
        t[0]["title"] == SWIEZY["title"], [x["title"][:22] for x in t])

print()
print("=== 3. pick_topic — TU SIEDZIAL GLOWNY BLAD ===")
TEMATY = przetworz([dict(CLICHE), dict(CLICHE2), dict(SWIEZY)])
# Wykonalnosc ocenia wszystkie tak samo — chodzi wylacznie o ranking tematow.
OCENY = [{"index": i, "feasible": True, "confidence": 0.8,
          "expected_primary_sources": 3, "depth": "RICH"}
         for i in range(len(TEMATY))]
wybrany, _ = stages.pick_topic(TEMATY, OCENY)
print("    kolejność po przetworzeniu: %s" % [x["title"][:30] for x in TEMATY])
print("    wybrany: %s" % wybrany["title"])
sprawdz("wybiera świeży system, nie cliché",
        wybrany["title"] == SWIEZY["title"], wybrany["title"])

# KONTRDOWOD 1: stary ranking sortowal po ma_przekonanie jako pierwszym kluczu.
# Cliche ma przekonanie, system pod proba NIE MA — wiec stary klucz wybralby
# cliche. Bez tego sprawdzenia test nie odroznia wersji.
po_staremu = sorted(OCENY, key=lambda a: (
    int(bool(TEMATY[a["index"]].get("ma_przekonanie"))),
    a["confidence"]), reverse=True)
stary_wybor = TEMATY[po_staremu[0]["index"]]
sprawdz("STARY ranking wziąłby cliché (test rozróżnia)",
        stary_wybor["title"] in (CLICHE["title"], CLICHE2["title"]),
        stary_wybor["title"])
sprawdz("i NIE wziąłby systemu pod próbą",
        not stary_wybor["title"].startswith("The Broken"), stary_wybor["title"])

# KONTRDOWOD 2: temat bez niczego nie moze wygrac z niczym.
PUSTY = przetworz([{"title": "Nic", "kind": "BROKEN_BELIEF", "broken_belief": "x",
                    "already_written": [], "threads": []}])[0]
razem = przetworz([dict(CLICHE), PUSTY])
sprawdz("nienośny ląduje na końcu mimo zerowego nasycenia",
        razem[-1]["title"] == "Nic", [x["title"][:20] for x in razem])

print()
print("=== 2b. PRECEDENSY I ZASIEG — TU SIE DZIELI ARTYKUL OD NOTKI ===")
# Kryterium, ktorego nie bylo w ogole, i przez ktorego brak wychodzily tematy
# wielkosci notki. Sama procedura to notka: „gdy maszyna do glosowania padnie,
# komisja wydaje karty tymczasowe" jest kompletna odpowiedzia w jednym zdaniu.
# Artykul niesie procedura, ktora POWSTALA, BO COS POSZLO NIE TAK — wielokrotnie.
KONKLAWE = {
    "title": "Kiedy nie moga wybrac nastepcy", "kind": "SYSTEM_UNDER_TEST",
    "the_moment": "the chimney everyone watches and no smoke of either colour",
    "open_outcome": "what happens if they cannot agree for months on end",
    "governing_record": "the constitution setting out the ballot procedure",
    "already_written": [], "threads": ["a", "b", "c", "d", "e"],
    "scale": "A_COUNTRY",
    "precedents": [
        {"when": "1268-1271", "what_happened": "the townspeople took the roof off "
         "the building and cut the cardinals down to bread and water",
         "what_changed": "the rule that seals a conclave in one room"},
        {"when": "1996", "what_happened": "a pope rewrote the majority needed "
         "after a fixed number of inconclusive rounds",
         "what_changed": "simple majority allowed, later reversed"},
    ],
}
MASZYNA = {
    "title": "Zepsuta maszyna do glosowania", "kind": "SYSTEM_UNDER_TEST",
    "the_moment": "a machine at the polling place stops working mid-vote",
    "open_outcome": "what happens to the votes already inside the machine",
    "governing_record": "state election administration rules",
    "already_written": [], "threads": ["a", "b", "c", "d", "e"],
    "scale": "A_PLACE",
    "precedents": [],
}
t2 = przetworz([dict(MASZYNA), dict(KONKLAWE)])
k = next(x for x in t2 if x["title"].startswith("Kiedy"))
m = next(x for x in t2 if x["title"].startswith("Zepsuta"))
print("    konklawe: awarie=%d zasieg=%s -> artykul=%s"
      % (k["ile_precedensow"], k["zasieg"], k["na_artykul"]))
print("    maszyna : awarie=%d zasieg=%s -> artykul=%s"
      % (m["ile_precedensow"], m["zasieg"], m["na_artykul"]))
sprawdz("konklawe jest artykulowe", k["na_artykul"] is True)
sprawdz("zepsuta maszyna NIE jest artykulowa", m["na_artykul"] is False)
sprawdz("i idzie za konklawe", t2[0]["title"].startswith("Kiedy"),
        [x["title"][:24] for x in t2])
sprawdz("prog to dwie udokumentowane awarie",
        config.PRECEDENSOW_NA_ARTYKUL == 2, config.PRECEDENSOW_NA_ARTYKUL)

# KONTRDOWOD 1: sama historia bez zasiegu to za malo.
maly = przetworz([dict(KONKLAWE, scale="ONE_PERSON")])[0]
sprawdz("historia bez zasiegu -> nie artykul", maly["na_artykul"] is False)
# KONTRDOWOD 2: sam zasieg bez historii to za malo.
bez_hist = przetworz([dict(KONKLAWE, precedents=[])])[0]
sprawdz("zasieg bez historii -> nie artykul", bez_hist["na_artykul"] is False)

print("    --- co NIE liczy sie jako precedens ---")
for opis, zly in (
    ("bez daty", {"when": "dawno temu", "what_happened": "the town took the roof off the hall",
                  "what_changed": "a rule was written down"}),
    ("bez skutku", {"when": "1271", "what_happened": "the town took the roof off the hall",
                    "what_changed": "nothing came of it"}),
    ("pusty skutek", {"when": "1271", "what_happened": "the town took the roof off the hall",
                      "what_changed": ""}),
    ("sama data", {"when": "1271", "what_happened": "it failed", "what_changed": "a rule"}),
):
    x = przetworz([dict(KONKLAWE, precedents=[zly, zly])])[0]
    sprawdz("  %-14s nie liczy sie" % opis, x["ile_precedensow"] == 0,
            x["ile_precedensow"])

print()
print("=== 3b. WYMUSZONY WYBOR RATUJE ZDEGENEROWANE POLA ===")
# TO JEST NAJWAZNIEJSZA SEKCJA. Na zywym przebiegu model wyrownal OBIE listy
# bezwzgledne: kazdemu tematowi przypisal dokladnie trzy znane teksty i
# dokladnie szesc watkow. Nasycenie i watki przestaly cokolwiek rozrozniac —
# ta sama wada co samooceny wracajace zawsze 1.0, tylko w innym przebraniu.
# Rankingu wyrownac sie nie da, wiec to on musi rozstrzygac.
ROWNE = [dict(CLICHE, title="A", already_written=["x", "y", "z"],
              threads=["1", "2", "3", "4", "5", "6"]),
         dict(CLICHE, title="B", already_written=["x", "y", "z"],
              threads=["1", "2", "3", "4", "5", "6"]),
         dict(CLICHE, title="C", already_written=["x", "y", "z"],
              threads=["1", "2", "3", "4", "5", "6"])]
bez_rankingu = przetworz([dict(x) for x in ROWNE])
sprawdz("przy identycznych polach kolejnosc jest przypadkowa",
        [x["title"] for x in bez_rankingu] == ["A", "B", "C"],
        [x["title"] for x in bez_rankingu])
z_rankingiem = przetworz([dict(x) for x in ROWNE],
                         {"least_written_about": [2], "most_written_about": [0],
                          "richest": [2], "thinnest": [0]})
print("    z wymuszonym wyborem: %s" % [x["title"] for x in z_rankingiem])
sprawdz("wymuszony wybor USTAWIA kolejnosc mimo identycznych pol",
        [x["title"] for x in z_rankingiem] == ["C", "B", "A"],
        [x["title"] for x in z_rankingiem])
sprawdz("najswiezszy wg modelu na czele", z_rankingiem[0]["title"] == "C")
sprawdz("najbardziej oklepany na koncu", z_rankingiem[-1]["title"] == "A")
sprawdz("oznaczenia trafiaja do tematu",
        z_rankingiem[0].get("swiezy_wg_modelu") is True
        and z_rankingiem[-1].get("oklepany_wg_modelu") is True)
# I to samo w pick_topic, bo tam zapada decyzja.
OC = [{"index": i, "feasible": True, "confidence": 0.8,
       "expected_primary_sources": 3, "depth": "RICH"} for i in range(3)]
wyb, _ = stages.pick_topic(z_rankingiem, OC)
sprawdz("pick_topic tez slucha wymuszonego wyboru", wyb["title"] == "C", wyb["title"])

print()
print("=== 4. NOSNOSC NADAL BIJE SWIEZOSC ===")
# Swiezy, ale nienosny temat nie moze wyprzedzic nosnego i oklepanego —
# lepiej napisac znany temat dobrze niz nieznany bez luki i bez stawki.
t = przetworz([dict(CLICHE), dict(PUSTY, already_written=[], threads=[])])
sprawdz("nośne cliché przed nienośną nowością", t[0]["title"] == CLICHE["title"],
        [x["title"][:20] for x in t])

print()
print("=== 4b. ODSIEW ZGLASZA, NIE ZABIJA PRZEBIEGU ===")
# Gdy odsiew odrzucil WSZYSTKIE tematy, leciał wyjatek i przebieg umieral —
# wbrew zasadzie obowiazujacej wszedzie indziej w tym potoku (bramki oddaja
# uwagi, nie werdykty). Podejrzenie: dlatego wlasnie `feasible` bylo prawdziwe
# w 6 ocenach na 6 — model nie mial jak powiedziec „nie" tak, zeby system to
# przezyl. Odsiew, ktory nie moze odrzucic, nie jest odsiewem; odsiew, ktory
# zabija przebieg, jest gorszy.
ODRZUCONE = [{"index": i, "feasible": False, "confidence": 0.3 + 0.1 * i,
              "expected_primary_sources": 1, "depth": "THIN"}
             for i in range(len(TEMATY))]
try:
    w, ocena = stages.pick_topic(TEMATY, ODRZUCONE)
    sprawdz("wszystko odrzucone -> nadal jest temat", True)
    sprawdz("i jest oznaczony jako wziety mimo odrzucenia",
            ocena.get("mimo_odrzucenia") is True, ocena)
    sprawdz("wybrano najlepszy z odrzuconych, nie pierwszy z brzegu",
            w["title"] == SWIEZY["title"], w["title"])
except Exception as e:
    sprawdz("wszystko odrzucone -> nadal jest temat", False, repr(e))
# Ale PUSTA lista ocen to co innego: nie ma z czego wybierac.
try:
    stages.pick_topic(TEMATY, [])
    sprawdz("pusta lista ocen nadal jest bledem", False, "przeszlo")
except ValueError:
    sprawdz("pusta lista ocen nadal jest bledem", True)
# I gdy cokolwiek przeszlo, odrzucone NIE moga sie wcisnac.
MIESZANE = [dict(ODRZUCONE[0]), dict(ODRZUCONE[1]),
            {"index": 2, "feasible": True, "confidence": 0.5,
             "expected_primary_sources": 1, "depth": "SINGLE"}]
w2, o2 = stages.pick_topic(TEMATY, MIESZANE)
sprawdz("gdy cokolwiek przeszlo, bierzemy TO",
        o2.get("mimo_odrzucenia") is None and o2["index"] == 2, o2)

print()
print("=== 5. SIEDEM MARTWYCH OCEN USUNIETYCH ===")
p = (config.PROMPTS_DIR / "skaut.md").read_text(encoding="utf-8")
plaski = " ".join(p.split())
for martwa in ("score_breakdown", "visual_potential", "discussion_potential",
               "non_obvious", "universality"):
    sprawdz("prompt nie prosi już o %s" % martwa, martwa not in plaski)
sprawdz("i mówi wprost, czemu je usunięto",
        "Nothing ever read them" in plaski)
zrodlo = open("agent-v2/stages.py", encoding="utf-8").read()
sprawdz("kod nadal ich nie czyta (bo ich nie ma)",
        "score_breakdown" not in zrodlo)

print()
print("=== 6. SKAUT WIE, ZE PIERWSZY POMYSL JEST NAJGORSZY ===")
sprawdz("prompt nazywa gatunek po imieniu", "It is a **genre**" in plaski)
# ZASADA, NIE PRZYKLADY — i to przez dwa przestawienia tematu z rzedu.
# Stalo tu najpierw ("sprinklers", "flushable", "antibacterial"), potem lista
# oklepanych tez o AI. Za kazdym razem test trzymal w sobie temat konta, wiec
# zmiana niszy oblewala go z powodu, ktory nie mial nic wspolnego z kodem —
# dokladnie ta wada, ktora ten projekt usuwa.
#
# Regula jest niezmienna: prompt ma WYMIENIC Z NAZWY zuzyte ujecia, bo ogolne
# „unikaj oczywistosci" nie dziala. Zmienilo sie tylko to, SKAD ta lista
# pochodzi — z konfiguracji (`config.PRZYKLADY_NISZY["kanon"]`), a nie
# z ciala promptu. Sprawdzamy wiec mechanizm, nie slownictwo.
sprawdz("prompt ma miejsce na kanon niszy, a nie wpisany kanon",
        "{kanon_niszy}" in p)
_kanon_wstawiony = stages._pola_wspolne()["kanon_niszy"]
sprawdz("i cos w to miejsce naprawde wchodzi", bool(_kanon_wstawiony.strip()))
# Sprawdzamy na ZLOZONYM promptcie, bo `plaski` trzyma jeszcze `{kanon_niszy}`.
_zlozony = " ".join(p.replace("{kanon_niszy}", _kanon_wstawiony).split())
sprawdz("  a po zlozeniu promptu jest to widoczne",
        " ".join(_kanon_wstawiony.split())[:40] in _zlozony)
# KONTRDOWOD: przy PUSTEJ liscie w konfiguracji model nie moze zostac
# z niczym — ma dostac polecenie, zeby wyprowadzil kanon dla wlasnej niszy.
_stary = config.PRZYKLADY_NISZY.get("kanon")
config.PRZYKLADY_NISZY["kanon"] = ()
try:
    _pusty = stages._pola_wspolne()["kanon_niszy"]
    sprawdz("pusta lista daje polecenie, nie pustke", len(_pusty) > 80)
    sprawdz("  i polecenie nazywa nisze po imieniu", config.NISZA in _pusty)
finally:
    config.PRZYKLADY_NISZY["kanon"] = _stary
# KONTRDOWOD: samo slowo "genre" to za malo — bez wyliczenia prompt nie daje
# modelowi nic, czego mialby unikac.
sprawdz("i to wyliczenie, nie ogolnik", plaski.count(",") > 20)
# Drugi kanon, wlasciwy tej dziedzinie: cykl newsowy. Temat "wyszedl nowy
# model" jest tym, co w tym tygodniu pisza wszyscy.
sprawdz("ostrzega tez przed cyklem newsowym",
        "news cycle" in plaski and "late" in plaski)
sprawdz("tłumaczy mechanizm dostępności",
        "Availability is the opposite of the signal" in plaski)
sprawdz("ostrzega przed własną płynnością",
        "if the\ntopic assembled itself instantly" in p
        or "topic assembled itself instantly" in plaski)
sprawdz("wymaga pola already_written", "already_written" in plaski)
sprawdz("wymaga pola threads", "`threads`" in plaski)
sprawdz("zakazuje fałszowania w OBIE strony",
        "Do not fake this in either direction" in plaski)
sprawdz("prompt zamawia wymuszony wybor",
        "rank your own list against itself" in plaski)
sprawdz("i nazywa wprost obserwowana degeneracje",
        "every answer came back with exactly three items" in plaski)
sprawdz("mowi, ze porownania nie da sie wyrownac",
        "A forced comparison cannot" in plaski)
for k in ("most_written_about", "least_written_about", "richest", "thinnest"):
    sprawdz("ranking ma %s" % k, k in plaski)

print()
print("=== 7. KOTWICA TO JUZ NIE TYLKO PRZEDMIOT ===")
# ZASADA: kotwic ma byc TRZY i jedna z nich ma byc wskazana jako najzasobniejsza
# — zeby model nie siadal na najlatwiejszej. Sformulowania zmienily sie razem z
# dziedzina, uklad nie.
sprawdz("dopuszcza rzecz, ktorej czytelnik uzywal",
        "a thing the reader has used" in plaski)
sprawdz("dopuszcza decyzję podjętą WOBEC czytelnika",
        "a decision that was made about them" in plaski)
sprawdz("dopuszcza moment, który wszyscy widzieli",
        "a moment everybody watched happen" in plaski)
sprawdz("i wskazuje, ktora kotwica jest najzasobniejsza",
        "the richest and the least written" in plaski)
# KONTRDOWOD dla calej tej sekcji: czytelnik NIE MA udzialu w opisywanym
# systemie i prompt musi to mowic wprost, inaczej skaut wraca do raportow o
# bledach w konkretnym produkcie.
sprawdz("mowi wprost, ze czytelnik nie ma w tym udzialu",
        "no stake in the particular system" in plaski)
sprawdz("i nazywa wpadke, ktora z tego wynika",
        "a bug report, not a topic" in plaski)

print()
print("=== 8. GLEBOKOSC LICZY SIE TEZ W PIONIE ===")
wyk = (config.PROMPTS_DIR / "wykonalnosc.md").read_text(encoding="utf-8")
plaski_w = " ".join(wyk.split())
sprawdz("RICH da się osiągnąć samymi wątkami",
        "three or more separate questions" in plaski_w)
sprawdz("prompt nazywa starą wadę wprost",
        "Depth was judged here only sideways" in plaski_w)
sprawdz("i daje przykład, który wcześniej wypadał jako THIN",
        "cannot agree" in plaski_w)

print()
print("=== RANKING SKAUTA: BEZ POWTORZEN I Z WAGA POZYCJI ===")
# Komentarz w stages.py nazywa wymuszony ranking JEDYNYM sygnalem, ktorego
# model nie umie wyrownac — i wlasnie ten sygnal byl policzony dwa razy zle.
#
# 1. Filtr sprawdzal tylko ZAKRES indeksu, nie deduplikowal. Ranking [0,0,0]
#    dawal tematowi zero SZESC punktow, [2,2,2,2,2] — dziesiec. Wynik zalezal
#    od tego, czy model powtorzyl liczbe.
# 2. Kolejnosc byla wyrzucana: przy [0,1,2] wszystkie trzy dostawaly po tyle
#    samo. Model odpowiada uporzadkowana lista, a my czytalismy ja jak zbior.
import pathlib     # noqa: E402

_st = pathlib.Path("agent-v2/stages.py").read_text(encoding="utf-8")
sprawdz("indeksy() deduplikuje", "i not in bez_powtorzen" in _st)
# KOD NIE MOZE WIEDZIEC O MODELU WIECEJ, NIZ MU POWIEDZIANO. Wazenie pozycja
# zaklada, ze listy sa uporzadkowane — a prompt tego wczesniej NIE zamawial,
# mowil tylko „exactly three indices". Zalozenie niepokryte kontraktem to
# zgadywanie, nawet gdy trafne.
_sk = pathlib.Path("agent-v2/prompts/skaut.md").read_text(encoding="utf-8")
sprawdz("prompt zamawia KOLEJNOSC w rankingu",
        "Order each triple, strongest case first" in _sk)
sprawdz("i zakazuje powtorzen w liscie", "no index may repeat" in _sk)
sprawdz("i istnieje wazenie pozycja", "def wazenie(" in _st)
sprawdz("wagi malejaca z pozycja", "sila * (len(lista) - pozycja)" in _st)


def _pozycje(ranking, n=6):
    """Odtwarza logike rankingu z stages.py na czystych danych."""
    topics = [{"pozycja": 0} for _ in range(n)]
    r = ranking

    def indeksy(klucz):
        v = r.get(klucz)
        if not isinstance(v, list):
            return []
        out = []
        for x in v:
            if not isinstance(x, (int, float)):
                continue
            i = int(x)
            if 0 <= i < n and i not in out:
                out.append(i)
        return out

    def wazenie(klucz, sila):
        lista = indeksy(klucz)
        for poz, i in enumerate(lista):
            topics[i]["pozycja"] += sila * (len(lista) - poz)

    wazenie("least_written_about", 2)
    wazenie("most_written_about", -2)
    wazenie("richest", 1)
    wazenie("thinnest", -1)
    return [t["pozycja"] for t in topics]


# KOLEJNOSC MA ZNACZYC. To jest cala tresc naprawy numer dwa.
w = _pozycje({"least_written_about": [2, 1, 0]})
sprawdz("ranking [2,1,0] daje malejaco: temat 2 > 1 > 0",
        w[2] > w[1] > w[0], w)
w = _pozycje({"least_written_about": [0, 1, 2]})
sprawdz("i odwrotnie przy [0,1,2]", w[0] > w[1] > w[2], w)

# POWTORZENIE NIE MOZE MNOZYC. To jest naprawa numer jeden.
sprawdz("[0,0,0] daje tyle samo co [0]",
        _pozycje({"least_written_about": [0, 0, 0]})
        == _pozycje({"least_written_about": [0]}),
        _pozycje({"least_written_about": [0, 0, 0]}))
sprawdz("piec powtorzen tez nie pompuje",
        max(_pozycje({"least_written_about": [2] * 5})) == 2,
        _pozycje({"least_written_about": [2] * 5}))

# KONTRDOWOD: stara logika MUSI dawac inny wynik, inaczej naprawa byla zbedna
# i test niczego nie pilnuje.
def _po_staremu(ranking, n=6):
    topics = [0] * n
    for i in ranking.get("least_written_about", []):
        if isinstance(i, (int, float)) and 0 <= int(i) < n:
            topics[int(i)] += 2
    return topics


sprawdz("stara logika pompowala powtorzenia do szesciu",
        max(_po_staremu({"least_written_about": [0, 0, 0]})) == 6)
sprawdz("i gubila kolejnosc — trzy rozne dostawaly po tyle samo",
        len(set(x for x in _po_staremu({"least_written_about": [0, 1, 2]}) if x)) == 1)

# Smieci nie moga niczego wywrocic ani przemycic.
sprawdz("indeks poza zakresem jest odrzucany",
        _pozycje({"least_written_about": [99, 0]})[0] > 0)
sprawdz("napis w liscie nie wywala", _pozycje({"least_written_about": ["a", 1]})[1] > 0)
sprawdz("brak rankingu to same zera", _pozycje({}) == [0] * 6)
# Kierunki zostaja przeciwne: oklepany schodzi w dol.
sprawdz("most_written_about odejmuje",
        _pozycje({"most_written_about": [3]})[3] < 0)

print()
print("=== TEMAT NIE WRACA POD INNA NAZWA ===")
# ZLAPANE NA ZYWYM PRZEBIEGU. Rano powstal artykul o automatycznym odbieraniu
# uprawnien. Po poludniu ten sam skaut, majac ten tytul na liscie zakazanych
# w prompcie, zaproponowal ten sam temat pod inna nazwa — i wybor padl na niego.
#
# ATRAPA WYMIENIONA przy czyszczeniu repozytorium. Stala tu prawdziwa tresc
# opublikowanego artykulu razem z nazwiskiem osoby i kwota z jej sprawy.
# Wymyslona para zachowuje wlasnosc, ktora ten test MIERZY: cztery wspolne
# rdzenie miedzy poprzednim artykulem a kandydatem, przy dwoch u tematu
# sasiedniego. Bez tego prog nie odrozniałby powtorki od sasiada.
#
# Regula roznorodnosci byla PROSBA W PROMPCIE. Prosba nie jest gwarancja — ta
# lekcja jest w projekcie zapisana juz przy otwarciach notek.
_POPRZEDNI = ("The Licence Revoked Before Any Appeal Was Heard "
              "An automated scoring system revoked a driving licence and set the "
              "appeal window running from the date of the notice, not the date it "
              "arrived. The notice was posted to an address the holder had left "
              "two years earlier. By the time an appeal was possible the automated "
              "revocation had already been treated as final.")

_POWTORKA = {"title": "Example Article Fifteen The Notice Arrived",
             "question": "What happens when an automated system revokes a licence and "
                         "the appeal window runs out before anyone is told?",
             "nosny": True, "na_artykul": True, "pozycja": 5, "nasycony": False}
_INNY = {"title": "Example Article Thirteen",
         "question": "What does a model keeping memory of you change about what it is?",
         "nosny": True, "na_artykul": True, "pozycja": 0, "nasycony": False}
_OCENY = [{"index": 0, "feasible": True, "confidence": 0.95},
          {"index": 1, "feasible": True, "confidence": 0.70}]

_wybrany, _ = stages.pick_topic([_POWTORKA, _INNY], _OCENY, 1,
                                wczesniejsze=[_POPRZEDNI])
sprawdz("powtorzony temat NIE zostaje wybrany",
        _wybrany.get("title") == "Example Article Thirteen",
        _wybrany.get("title"))

# KONTRDOWOD: bez pamieci wygrywa powtorka — czyli test mierzy TE zmiane,
# a nie przypadkowa kolejnosc. Powtorka ma tu wyzsza `pozycja` wlasnie po to.
_bez, _ = stages.pick_topic([_POWTORKA, _INNY], _OCENY, 1)
sprawdz("a bez pamieci wygralaby (tak powstala wpadka)",
        _bez.get("title") == "Example Article Fifteen The Notice Arrived",
        _bez.get("title"))

# Prog musi rozrozniac powtorke od tematu sasiadujacego. Zmierzone na 7
# artykulach: powtorka 4 wspolne rdzenie, najblizszy inny temat 2.
sprawdz("temat sasiadujacy NIE jest uznany za powtorke",
        not stages._o_tym_samym(
            "The Stop That Happens When the Machines Outrun the Humans "
            "What triggers a trading halt when algorithms move faster than people?",
            _POPRZEDNI, **stages.POWTORKA_TEMATU))
sprawdz("prog powtorki jest osobny od progu miedzy dniami",
        stages.POWTORKA_TEMATU != stages.POROWNANIE_MIEDZY_DNIAMI,
        (stages.POWTORKA_TEMATU, stages.POROWNANIE_MIEDZY_DNIAMI))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
