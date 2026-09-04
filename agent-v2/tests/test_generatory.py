"""Siatka generatorow i cztery bramki przed wydaniem grosza.

Mielismy 52 DZIEDZINY — odpowiedz na pytanie GDZIE szukac — i zero wzorcow,
czyli zadnej odpowiedzi na pytanie CZEGO. Model dostawal „przyroda, finanse,
prawo" i wracal do tego, co mu wychodzi najlatwiej.

Sprawdzian przydatnosci, ktory zrobilem przed wdrozeniem: szesc naszych
artykulow trafia w PIEC roznych wzorcow ponizej. Siatka pokrywa to, co juz
umiemy, i nazywa kilka, ktorych nie tknelismy.
"""
import re
import pathlib
import sys

sys.path.insert(0, "agent-v2")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import config   # noqa: E402
import wlasna_konfiguracja  # noqa: E402
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


# Asercje o DOSTARCZONYCH wartosciach, pomijane widocznie,
# gdy operator ma wlasne w `konfiguracja.toml`.
sprawdz_nasze = wlasna_konfiguracja.tylko_nasze(sprawdz)


KOMPLET = {
    "fact": "Mains clocks count grid cycles, and a 2018 shortfall left European "
            "clocks six minutes slow.",
    "wrong_belief": "Most people assume the oven clock keeps time by itself",
    "actually": "It counts cycles of the electricity grid, so grid drift moves it",
    "decision": "50 Hz fixed as the synchronous norm, ENTSO-E 1951",
    "consequence": "the clock on your oven",
    "url": "https://www.entsoe.eu/news/2018/03/06/press-release/",
    "domain": "elektrycznosc",
}


def wariant(**zmiany):
    k = dict(KOMPLET)
    k.update(zmiany)
    return k


print("=== 1. SIATKA ISTNIEJE I JEST DUZA ===")
# ZASADA, NIE LICZBA. Stalo tu `== 12` i oblalo sie 25 sierpnia 2026, gdy pod
# wielkie pytania doszly SEEMING i UNBIDDEN — choc REGULA, ktorej ten test
# pilnuje („siatka istnieje i ma setki komorek"), ocalala w calosci. Test
# przypiety do dokladnej liczby betonuje ROZMIAR doktryny i krzyczy przy kazdym
# jej poszerzeniu, tak samo jak test na dokladne brzmienie promptu krzyczy przy
# kazdym przepisaniu. Powod jest zmierzony i zapisany w naglowku
# test_pisarz_zakazy: przy jednej podmianie oblalo sie tam dziewiec testow
# naraz i WSZYSTKIE stare reguly zyly.
sprawdz("co najmniej dwanascie wzorcow", len(config.GENERATORY) >= 12,
        len(config.GENERATORY))
sprawdz("kazdy ma pytanie sondujace",
        all("Probe:" in o for o in config.GENERATORY.values()))
# KONTRDOWOD DO POLUZOWANEJ GRANICY: skoro liczba przestala byc pilnowana, musi
# byc pilnowane to, PO CO byla. Prog `>=` zacheca do dokladania wzorcow na sile,
# a wzorzec bedacy przeformulowaniem sasiada nie powieksza siatki o ani jedna
# uzyteczna komorke — daje tylko dwie drogi do tego samego kandydata.
sprawdz("zaden opis nie jest kopia innego",
        len(set(config.GENERATORY.values())) == len(config.GENERATORY),
        "%d powtorzonych opisow"
        % (len(config.GENERATORY) - len(set(config.GENERATORY.values()))))
sprawdz("kazdy wzorzec naprawde cos opisuje, nie jest sama nazwa",
        all(len(o.split()) >= 15 for o in config.GENERATORY.values()),
        {n: len(o.split()) for n, o in config.GENERATORY.items()
         if len(o.split()) < 15})
komorki = len(config.GENERATORY) * len(config.DZIEDZINY_CIEKAWOSTEK)
print("    siatka: %d wzorcow x %d dziedzin = %d komorek"
      % (len(config.GENERATORY), len(config.DZIEDZINY_CIEKAWOSTEK), komorki))
sprawdz_nasze("siatka ma setki komorek", komorki >= 400, komorki)

print()
print("=== 2. WZORCE SIE ROTUJA (jednolity ksztalt to podpis maszyny) ===")
losowania = [tuple(sorted(config.losowe_generatory())) for _ in range(40)]
sprawdz("nie zawsze te same cztery", len(set(losowania)) > 5, len(set(losowania)))
sprawdz("zawsze tyle, ile zamowiono",
        all(len(l) == config.ILE_GENERATOROW_NA_PRZEBIEG for l in losowania))
uzyte = {g for l in losowania for g in l}
sprawdz("z czasem wypadaja wszystkie", uzyte == set(config.GENERATORY),
        set(config.GENERATORY) - uzyte)

print()
print("=== 3. NASZE ARTYKULY MAPUJA SIE NA WZORCE (sprawdzian przydatnosci) ===")
NASZE = {"0014 okno w samolocie": "MARGIN", "0016 symbol kosmetyczny": "BOUNDARY",
         "0017 blokada karty": "BOUNDARY", "0019 zolte swiatlo": "CONFESSION",
         "przyklad kolor autobusu": "DECIDER", "przyklad wskaznik": "MEASUREMENT"}
for tytul, gen in NASZE.items():
    sprawdz("%-26s -> %s" % (tytul, gen), gen in config.GENERATORY)
sprawdz("szesc artykulow trafia w piec roznych wzorcow",
        len(set(NASZE.values())) == 5, set(NASZE.values()))

print()
print("=== 4. BRAMKA 1: NAZWANY DECYDENT Z DATA ===")
sprawdz("komplet przechodzi", stages.bramka_kandydata(KOMPLET)[0])
for opis, k in (("bez decydenta", wariant(decision="")),
                ("decydent bez daty", wariant(decision="ustalone przez komitet")),
                ("zjawisko fizyczne", wariant(decision="nikt, tak dziala fizyka"))):
    ok, powod = stages.bramka_kandydata(k)
    sprawdz("%-22s odpada" % opis, not ok, powod)

print()
print("=== 5. BRAMKA 2: NIEWIEDZA TO NIE PRZEKONANIE ===")
# Najostrzejsza regula w calym potoku. „Wiekszosc nie wie" produkuje trivie:
# skoro nikt nie ma zdania, nie ma czego zlamac i nie ma na co odpowiedziec.
for zdanie in ("Most people do not know how this works",
               "Most readers have never heard of this symbol",
               "Readers are unaware of the rule behind it"):
    ok, powod = stages.bramka_kandydata(wariant(wrong_belief=zdanie))
    sprawdz("odrzuca: %s" % zdanie[:42], not ok, powod)
ok, _ = stages.bramka_kandydata(
    wariant(wrong_belief="Most people assume SPF 50 blocks twice as much as SPF 25"))
sprawdz("ale prawdziwe przekonanie przechodzi", ok)

print()
print("=== 6. BRAMKI 3 I 4: KONTAKT I SPRAWDZALNOSC ===")
sprawdz("bez skutku w reku odpada",
        not stages.bramka_kandydata(wariant(consequence=""))[0])
sprawdz("bez zrodla odpada", not stages.bramka_kandydata(wariant(url="brak"))[0])

print()
print("=== 7. SEZONOWOSC ===")
from datetime import datetime, timezone   # noqa: E402
sprawdz("kazdy miesiac ma rzeczy w reku",
        all(config.co_teraz_w_reku(datetime(2026, m, 15, tzinfo=timezone.utc))
            for m in range(1, 13)))
sierpien = config.co_teraz_w_reku(datetime(2026, 8, 15, tzinfo=timezone.utc))
styczen = config.co_teraz_w_reku(datetime(2026, 1, 15, tzinfo=timezone.utc))
sprawdz("sierpien to nie styczen", sierpien != styczen)
# ZASADA, NIE SLOWO. Stalo tu "sierpien wymienia krem z filtrem" i
# "pazdziernik wymienia ogrzewanie" — przypiete do rzeczy, o ktorych konto
# wtedy pisalo. Po zmianie dziedziny na AI (25 sierpnia 2026) oba sie oblaly,
# choc REGULA ocalala w calosci: podpowiedz sezonowa ma byc konkretna, rozna
# w kazdym miesiacu i ma mowic, gdzie patrzec. Test pyta wiec o to.
_miesiace = [config.co_teraz_w_reku(datetime(2026, m, 15, tzinfo=timezone.utc))
             for m in range(1, 13)]
sprawdz("kazdy miesiac mowi cos konkretnego (nie jedno slowo)",
        all(len(x.split()) >= 4 for x in _miesiace),
        [len(x.split()) for x in _miesiace])
sprawdz("miesiace sie nie powtarzaja", len(set(_miesiace)) == 12,
        len(set(_miesiace)))
# KONTRDOWOD: gdyby podpowiedzi byly ogolnikami w rodzaju "AI news", powyzsze
# przeszloby. Wymagamy, zeby kazdy miesiac niosl RZECZOWNIKI z tej dziedziny,
# a nie sama nazwe dziedziny.
_puste = [x for x in _miesiace if "AI" in x and len(set(x.lower().split())) < 6]
sprawdz("zadna podpowiedz nie jest ogolnikiem", not _puste, _puste)

print()
print("=== 8. PROMPT NIESIE OBIE OSIE I SEZON ===")
tekst = (config.PROMPTS_DIR / "ciekawostki.md").read_text(encoding="utf-8")
for pole in ("{dziedziny}", "{generatory}", "{w_reku}", "{miesiac}"):
    sprawdz("prompt ma %s" % pole, pole in tekst)
sprawdz("prompt tlumaczy, po co druga os",
        "They do not tell you what you are looking" in tekst)
sprawdz("prompt zamawia nadprodukcje",
        config.KANDYDATOW_NA_PRZEBIEG >= 20, config.KANDYDATOW_NA_PRZEBIEG)

print()
print("=== 8b. TRZECIA OS: FAKT POD WIELKIM PYTANIEM ===")
# POMIAR, KTORY TO WYMUSIL (25 sierpnia 2026): przebieg oddal cztery dobre
# fakty — ukryty koszt w jednej rodzinie modeli, cztery ceny jednego modelu,
# SystemBadawczy, radiolodzy przy mammografii — kazdy z decydentem i data, i ZERO
# z czterech pod pytaniem, ktore czytelnik zadaje sam z siebie.
#
# ZASADA, NIE BRZMIENIE. Kazde sprawdzenie ma liste dopuszczalnych sformulowan,
# bo sekcja bedzie przepisywana, a pilnujemy mysli, nie zdania.
sekcje = tekst.split("\n## ")
_pyt = [s for s in sekcje if "question" in s.split("\n")[0].lower()]
sprawdz("prompt ma sekcje o wielkich pytaniach", bool(_pyt),
        [s.split("\n")[0][:40] for s in sekcje])
if _pyt:
    S = " ".join(_pyt[0].split())
    # TU JEST CALA STAWKA TEJ OSI. Wielkie pytanie brzmi jak gotowy temat
    # i kusi, zeby fakt pod nim byl opinia — a konto ma zapisana wpadke
    # z fabrykacja („everyone assumes" dorabiane, gdy karta nie niosla polowki).
    # Sekcja, ktora zachwala pytania i NIE powtarza wymogu zrodla, otwiera
    # dokladnie ten kanal.
    for opis, warianty in (
        ("wymog zrodla powtorzony przy pytaniach",
         ("still needs a source", "needs a source", "The question is a frame")),
        ("pytanie samo w sobie nie jest materialem",
         ("never the question on its own", "question, then evidence",
          "a debate, not a fact")),
        ("pola wyjscia obowiazuja tak samo",
         ("`decision` and `consequence`", "names no decider")),
    ):
        trafione = [w for w in warianty if w in S]
        sprawdz("  %-44s" % opis, bool(trafione), "zadne z: %s" % (warianty,))
    # KONTRDOWOD, I TO ON JEST TU NAJWAZNIEJSZY: sama zacheta do wielkich pytan
    # bez ograniczenia zamienia trzecia os w KONTYNGENT, a kontyngent na forme
    # jest podpisem maszyny — ta sama wpadka co dwa artykuly o identycznym
    # szkielecie po naprawie szamponu (19 sierpnia). Sekcja musi mowic wprost,
    # ze caly przebieg pod wielkimi pytaniami jest wada, nie sukcesem.
    _limit = ("not the batch", "as narrow as a run", "One or two in a batch")
    sprawdz("  os NIE jest kontyngentem na caly przebieg",
            any(w in S for w in _limit), "zadne z: %s" % (_limit,))
    # I nie moze udawac zamknietej listy — wlasciciel podal PRZYKLADY RODZAJU.
    _rodzaj = ("examples of a KIND", "not a list to work through",
               "is not better for appearing here")
    sprawdz("  pytania podane jako rodzaj, nie lista do odhaczenia",
            any(w in S for w in _rodzaj), "zadne z: %s" % (_rodzaj,))

print()
print("=== 9. ETAP PRZEKAZUJE WZORCE DO PROMPTU ===")
zrodlo = open("agent-v2/stages.py", encoding="utf-8").read()
sprawdz("znajdz_ciekawostki losuje wzorce", "config.losowe_generatory()" in zrodlo)
sprawdz("i podaje sezon", "co_teraz_w_reku" in zrodlo)
# KONTRAKT PROMPT <-> KOD, sprawdzany w obie strony.
#
# Stala tu lista pol wpisana recznie i to bylo zle w sposob, ktory zlapala
# dopiero produkcja: 25 sierpnia prompt dostal pole `dzis` (dzisiejsza data,
# zeby model nie pisal o modelach sprzed dwoch lat), kod go nie podawal, i
# `format()` wywalal sie na `KeyError`. Test przechodzil, bo renderowal prompt
# WLASNA lista pol zamiast tej, ktorej uzywa kod.
#
# Teraz obie listy sa CZYTANE: jedna z pliku promptu, druga z wywolania w
# stages.py. Zgadzaja sie albo test pada.
import string as _string
import ast as _ast

_tekst_promptu = (config.PROMPTS_DIR / "ciekawostki.md").read_text(encoding="utf-8")
_pola_promptu = {f for _, f, _, _ in _string.Formatter().parse(_tekst_promptu) if f}

_drzewo = _ast.parse(zrodlo)
_pola_kodu = set()
for _w in _ast.walk(_drzewo):
    if not isinstance(_w, _ast.Call):
        continue
    _f = _w.func
    _nazwa = _f.attr if isinstance(_f, _ast.Attribute) else getattr(_f, "id", "")
    if _nazwa != "_prompt" or not _w.args:
        continue
    _pierwszy = _w.args[0]
    if isinstance(_pierwszy, _ast.Constant) and _pierwszy.value == "ciekawostki.md":
        _pola_kodu = {kw.arg for kw in _w.keywords if kw.arg}

sprawdz("znalazlem wywolanie promptu ciekawostek w kodzie", bool(_pola_kodu),
        sorted(_pola_kodu))
# POLA WSPOLNE nie sa podawane przy wywolaniu — wstrzykuje je `_prompt`
# z configu, zeby prompt mogl siegnac po nisze bez pytania miejsca wywolania
# o pozwolenie. Test musi o nich wiedziec, inaczej zglosilby je jako brakujace
# przy pierwszym prompcie, ktory uzyje `{nisza}`.
_WSPOLNE = set(stages._pola_wspolne())
_brakuje = sorted(_pola_promptu - _pola_kodu - _WSPOLNE)
sprawdz("kod podaje KAZDE pole, ktorego prompt zada", not _brakuje,
        "brakuje: %s" % _brakuje)
# POLA WSPOLNE nie moga byc "zbedne". `_prompt` wstrzykuje je do KAZDEGO
# promptu, wiec prompt, ktory ich nie uzywa, jest normalny — a nie bledny.
# Liczy sie tylko to, czego kod podaje JAWNIE, a prompt o to nie prosi.
_zbedne = sorted(_pola_kodu - _pola_promptu - _WSPOLNE)
sprawdz("i nie podaje pol, ktorych prompt nie ma", not _zbedne,
        "zbedne: %s" % _zbedne)

# KONTRDOWOD: sam wykrywacz musi cokolwiek znajdowac. Gdyby `_pola_promptu`
# bylo puste, oba sprawdzenia wyzej przechodzilyby zawsze i niczego nie
# pilnowaly.
sprawdz("prompt naprawde ma pola do podstawienia", len(_pola_promptu) >= 4,
        sorted(_pola_promptu))

try:
    g = config.losowe_generatory()
    gotowy = stages._prompt(
        "ciekawostki.md",
        **{k: ("- transport" if k == "dziedziny" else
               "\n".join("**%s** — %s" % (x, config.GENERATORY[x]) for x in g)
               if k == "generatory" else "X")
           for k in _pola_promptu})
    sprawdz("prompt renderuje sie bez wyjatku", True)
    sprawdz("wzorce trafiaja do tekstu", any(x in gotowy for x in g))
    sprawdz("nie zostalo niepodstawione pole",
            not re.search(r"\{[a-z_]+\}", gotowy))
except Exception as e:
    sprawdz("prompt renderuje sie bez wyjatku", False, repr(e))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
