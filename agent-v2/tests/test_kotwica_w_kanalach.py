# -*- coding: utf-8 -*-
"""Trzy czwarte tematow ma wychodzic z kanalow — i to liczy KOD.

DLACZEGO TO POWSTALO — dwie obserwacje wlasciciela, ktore okazaly sie jedna wada.

  „te tematy sa za bardzo dookola ai, czemu?"
  „ma to byc 75% z tych kanalow yt"

ZMIERZONE na pelnym przebiegu dwudziestu tematow: z kanalow pochodzilo PIEC
(25%), z pytan czytelnikow dwa, z pamieci modelu trzynascie. A pamiec dala
niemal wylacznie historie sadowe — wszystkie osiem tematow artykulowych bylo
pozwem, nakazem regulatora, ugoda albo wytyczna izby. Ani jeden nie mowil o
tym, co sama rzecz robi; rzecz byla okolicznoscia, a instytucja tematem.

To sa dwie strony jednego problemu, bo kanaly sa jedynym zrodlem mowiacym
o RZECZY SAMEJ: co powstalo, ile kosztuje, wobec czego jest mierzone i co sie
zmienilo miedzy dwoma wersjami.

DEKLARACJA MODELU TO SYGNAL, NIE DOWOD. Pole `zaczyn` sprawdzamy wobec
prawdziwej listy tym samym rozmytym porownaniem, ktorego uzywa wykrywacz
powtorek. Model, ktory wpisze kotwice, jakiej nie uzyl, nie awansuje w
kolejce — i jest to wypisane w logu.

PROG, NIE OBCIECIE. Ponizej kwoty mowimy glosno, ale nie kasujemy tematow:
tydzien, w ktorym kanaly mowia samymi naglowkami („AGI by December"), jest
mozliwy i nie jest wina skauta. Lista przycieta do kwoty byloby gorsza od
pelnej z uczciwa adnotacja.

BEZ PYTESTA, bez platnych wywolan. Uruchamiac z korzenia repozytorium.
"""
import contextlib
import io
import json
import sys

sys.path.insert(0, "agent-v2")
import config          # noqa: E402
import korpus_kanalow  # noqa: E402
import stages          # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


KORPUS = [
    {"temat": "openai custom inference chip built with broadcom", "kanal": "a",
     "data": "2026-08-30"},
    {"temat": "context window benchmark contamination found in evaluation set",
     "kanal": "b", "data": "2026-08-30"},
    {"temat": "minimax model feels fast and cheap on long documents",
     "kanal": "c", "data": "2026-08-29"},
]

# Temat oparty o pierwsza pozycje korpusu.
Z_KANALU = {
    "title": "The Chip Built in Nine Months",
    "question": "What did the custom inference chip built with Broadcom change "
                "about who sets the price of a token?",
    "kind": "BROKEN_BELIEF", "scale": "AN_INDUSTRY",
    "zaczyn": "openai custom inference chip built with broadcom",
    "broken_belief": "Everyone assumes the chip changes what the model can do.",
    "precedents": [], "threads": [], "already_written": [],
}
# Temat z pamieci — nic wspolnego z korpusem.
Z_PAMIECI = {
    "title": "The Tenant Screening Report",
    "question": "When a rental application is refused by an algorithmic "
                "screening report, what must the landlord disclose?",
    "kind": "SYSTEM_UNDER_TEST", "scale": "AN_INDUSTRY", "zaczyn": "",
    "the_moment": "A renter is refused a flat by a screening report.",
    "precedents": [], "threads": [], "already_written": [],
}
# Temat, ktory DEKLARUJE kotwice, ale jej nie uzyl.
KLAMIE = dict(Z_PAMIECI, title="The Report That Claimed an Anchor",
              zaczyn="openai custom inference chip built with broadcom")

print("=== 0. ATRAPY SA TYM, ZA CO JE BIORE ===")
PROG = {"min_wspolnych": 2, "prog": 0.12}
tekst_kan = " ".join(str(Z_KANALU.get(k) or "") for k in
                     ("title", "question", "broken_belief", "zaczyn"))
tekst_pam = " ".join(str(Z_PAMIECI.get(k) or "") for k in
                     ("title", "question", "the_moment", "zaczyn"))
sprawdz("temat z kanalu naprawde zderza sie z korpusem",
        any(stages._o_tym_samym(tekst_kan, w["temat"], **PROG) for w in KORPUS))
sprawdz("temat z pamieci NIE zderza sie z korpusem",
        not any(stages._o_tym_samym(tekst_pam, w["temat"], **PROG)
                for w in KORPUS))

print()
print("=== 1. PROG ISTNIEJE I JEST TYM, O CO PROSZONO ===")
sprawdz("SKAUT_UDZIAL_Z_KANALOW = 0.75",
        abs(config.SKAUT_UDZIAL_Z_KANALOW - 0.75) < 1e-9,
        config.SKAUT_UDZIAL_Z_KANALOW)

print()
print("=== 2. BRIEF ZADA KOTWICY I MOWI, ZE JEST LICZONA ===")
brief = open("agent-v2/prompts/skaut.md", encoding="utf-8").read()
sprawdz("brief nazywa kwote", "75%" in brief)
sprawdz("brief opisuje pole zaczyn", "`zaczyn`" in brief)
sprawdz("brief mowi, ze kod to sprawdza",
        "checked by code" in brief or "verified against the actual list" in brief)
sprawdz("brief pozwala przyznac sie do chudego tygodnia",
        "thin" in brief and "fabricated anchor" in brief)

print()
print("=== 3. PRECEDENS NIE MUSI BYC POZWEM ===")
# To druga polowa tej samej wady: dopoki precedens znaczyl „kiedy ktos pozwal",
# kazdy artykul musial byc historia sadowa.
sprawdz("brief mowi wprost, ze precedens to nie tylko sprawa sadowa",
        "DOES NOT HAVE TO BE A LAWSUIT" in brief)
# LISTA PRZYKLADOW WYSZLA Z PROMPTU DO KONFIGURACJI. Stalo tu wyliczenie
# („benchmark", „retracted", „between two versions") wziete z poprzedniej
# niszy — czyli test pilnowal, zeby prompt mowil o TAMTYM temacie. Regula,
# ktorej naprawde pilnujemy, jest inna i niezalezna od dziedziny: obok zdania
# „to nie musi byc pozew" MUSI stac konkretna lista alternatyw, bo samo
# zaprzeczenie nie mowi modelowi, czego szukac.
sprawdz("i zaraz potem daje konkretna liste alternatyw",
        "{precedensy_niszy}" in brief)
_alternatywy = stages._pola_wspolne()["precedensy_niszy"]
sprawdz("  ktora nie jest pusta", len(_alternatywy.strip()) > 40)
sprawdz("  i nazywa ksztalt zmiany, nie tylko zdarzenie",
        "the default was reversed" in brief)

print()
print("=== 4. KOD MIERZY KOTWICE, NIE WIERZY DEKLARACJI ===")
zrodlo = open("agent-v2/stages.py", encoding="utf-8").read()
sprawdz("i porownuje z progiem z konfiguracji",
        "SKAUT_UDZIAL_Z_KANALOW" in zrodlo)
sprawdz("kotwica wchodzi na czolo klucza sortowania",
        'key=lambda t: (not t.get("z_kanalu")' in zrodlo)
sprawdz("falszywa deklaracja jest wypisywana",
        "kotwica deklarowana, ale nieznaleziona" in zrodlo)
sprawdz("ponizej progu mowimy glosno", "PONIZEJ PROGU KOTWIC" in zrodlo)


def uruchom_skauta(tematy, korpus=KORPUS):
    """PRAWDZIWY `stages.scout` na atrapie modelu. Oddaje (kolejnosc, log).

    Podmieniamy WYLACZNIE `llm.call` i oddajemy `json.dumps({...})` — prawdziwy
    `llm.parse_json` zostaje w torze, bo to on tlumaczy odpowiedz modelu na
    ksztalt, ktorego oczekuje kod. Zero sieci, zero platnych wywolan.
    """
    oryg = (stages.recent_angles, stages.pytania_dla_skauta,
            stages.zaczyn_z_kanalow, stages.llm.call,
            korpus_kanalow.korpus_kanalow)
    stages.recent_angles = lambda conn, limit=None: []
    stages.pytania_dla_skauta = lambda ile=6: []
    stages.zaczyn_z_kanalow = lambda ile=26: "(atrapa)"
    korpus_kanalow.korpus_kanalow = lambda ile=200: [dict(w) for w in korpus]
    stages.llm.call = lambda *a, **k: json.dumps(
        {"topics": [dict(t) for t in tematy],
         "ranking": {"least_written_about": list(range(len(tematy)))}})
    bufor = io.StringIO()
    try:
        with contextlib.redirect_stdout(bufor):
            wynik = stages.scout(None, 0, count=len(tematy))
    finally:
        (stages.recent_angles, stages.pytania_dla_skauta,
         stages.zaczyn_z_kanalow, stages.llm.call,
         korpus_kanalow.korpus_kanalow) = oryg
    return wynik, bufor.getvalue()


# ZACHOWANIE, NIE GREP. Do 2 wrzesnia stalo tu `"z kanalow: %d z %d" in zrodlo`
# — a ten sam napis jest DRUGI RAZ w etapie ciekawostek (`stages.py`, blok
# `[ciekawostki]`). Asercja trafiala wiec w cudzy `print` i przechodzilaby
# takze wtedy, gdyby skaut przestal cokolwiek liczyc.
kolejnosc, log = uruchom_skauta([Z_KANALU, Z_PAMIECI])
sprawdz("skaut liczy udzial z kanalow — i mowi to WLASNYM glosem",
        "[skaut] z kanalow: 1 z 2" in log, log)
sprawdz("i podaje przy tym prog wlasciciela",
        "prog %.0f%%" % (100 * config.SKAUT_UDZIAL_Z_KANALOW) in log, log)

# PROG, NIE OBCIECIE — mierzone, nie odczytane z komentarza. Oba tematy sa
# z pamieci (drugi DEKLARUJE kotwice, ktorej nie uzyl), czyli 0% wobec progu
# 75%. Skaut ma o tym powiedziec glosno i ODDAC KOMPLET.
ponizej, log_ponizej = uruchom_skauta([Z_PAMIECI, KLAMIE])
sprawdz("na 0% kotwic skaut naprawde jest ponizej progu",
        "[skaut] PONIZEJ PROGU KOTWIC" in log_ponizej, log_ponizej)
sprawdz("ale NIE kasujemy tematow — wraca komplet",
        sorted(t["title"] for t in ponizej)
        == sorted(t["title"] for t in (Z_PAMIECI, KLAMIE)),
        [t["title"] for t in ponizej])
sprawdz("i przy pelnym komplecie kotwic tez nic nie ginie",
        len(uruchom_skauta([Z_KANALU])[0]) == 1)

print()
print("=== 5. SORTOWANIE STAWIA ZAKOTWICZONE NA CZELE ===")
def klucz(t):
    return (not t.get("z_kanalu"), not t["nosny"], not t["na_artykul"],
            -t["pozycja"], t["nasycony"], -t["ile_watkow"])


baza = {"nosny": True, "na_artykul": False, "pozycja": 0,
        "nasycony": False, "ile_watkow": 4}
a = dict(baza, tytul="z kanalu", z_kanalu=True, pozycja=0)
b = dict(baza, tytul="z pamieci, mocniejszy", z_kanalu=False, pozycja=9,
         na_artykul=True)
posortowane = sorted([b, a], key=klucz)
sprawdz("zakotwiczony wyprzedza mocniejszy z pamieci",
        posortowane[0]["tytul"] == "z kanalu",
        [x["tytul"] for x in posortowane])

print()
print("=== 6. KONTRDOWOD: BEZ KOTWICY WYGRYWA TEN Z PAMIECI ===")
# Gdyby kotwica nic nie zmieniala, sekcja 5 przechodzilaby rowniez wtedy.
def klucz_bez(t):
    return (not t["nosny"], not t["na_artykul"], -t["pozycja"],
            t["nasycony"], -t["ile_watkow"])


sprawdz("stara kolejnosc stawiala z pamieci pierwszy",
        sorted([b, a], key=klucz_bez)[0]["tytul"] == "z pamieci, mocniejszy",
        [x["tytul"] for x in sorted([b, a], key=klucz_bez)])

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
