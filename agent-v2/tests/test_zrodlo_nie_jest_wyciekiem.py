# -*- coding: utf-8 -*-
"""Adres, ktory sami podalismy, nie kasuje gotowej notki.

## Wpadka, 10 wrzesnia 2026

Partia dwoch notek. Pierwsza wrocila ze statusem `empty_or_invalid_text`
i przebieg wydrukowal „pierwsza notka pusta — nie wystawiam". Nie byla pusta.
W pliku roboczym stalo:

    Anil Madhavapeddy fixed a path-traversal bug in cohttp with a public PR.
    About ten minutes later his live server was being probed for that exact
    pattern. (https://anil.recoil.org/notes/rumour-is-the-exploit)

    The disclosure "embargo" now lasts roughly as long as it takes a maintainer
    to make coffee.

    His own agent wrote a working exploit from a rough description in under
    a minute. Funny how the agent is always "he" when it's picking a lock.

Trzy uderzenia, zadlo na koncu, temat z banku ze zrodlem. Zaplacone 0,16 USD.
Do kosza.

## Dwie moje wlasne instrukcje, kasujace sie nawzajem

Instrukcja notki z faktem, dopisana 9 wrzesnia, mowi wprost:

    Name the source in passing when it earns a mention; the URL may go in
    the text.

`_valid` odrzucal KAZDY tekst, w ktorym pada `https://`. Model zrobil
dokladnie to, o co go poprosilismy, i za to wylecial.

## Granica poprawki

Zakaz zostaje dla wszystkiego innego. Chodzilo w nim o adresy WYMYSLONE
i o zaczepianie ludzi po nazwie — nie o zrodlo, ktore sami wybralismy,
sprawdzilismy i podalismy w materiale.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_zrodlo_nie_jest_wyciekiem.py
"""
import ast
import io
import sys

sys.path.insert(0, "agent-v2")
import personality as p        # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


URL = "https://anil.recoil.org/notes/rumour-is-the-exploit"
# DOKLADNIE TA NOTKA, KTORA WYLECIALA.
NOTKA = ("Anil Madhavapeddy fixed a path-traversal bug in cohttp with a public"
         " PR. About ten minutes later his live server was being probed for"
         " that exact pattern. (%s)\n\n"
         "The disclosure \"embargo\" now lasts roughly as long as it takes"
         " a maintainer to make coffee.\n\n"
         "His own agent wrote a working exploit from a rough description in"
         " under a minute. Funny how the agent is always \"he\" when it is"
         " picking a lock." % URL)

print("=== 1. TA NOTKA JUZ NIE WYLECI ===")
sprawdz("bez pozwolenia nadal odpada (tak bylo)",
        p._valid(NOTKA, 600) is False)
sprawdz("z NASZYM adresem przechodzi",
        p._valid(NOTKA, 600, dozwolone_adresy=(URL,)) is True)

print()
print("=== 2. POZWOLENIE JEST WASKIE ===")
# Kontrdowod: gdyby wystarczylo „jest jakis dozwolony adres", model moglby
# wkleic dowolny wymyslony link i przejsc.
OBCY = NOTKA.replace(URL, "https://zmyslony-adres.example/cos")
sprawdz("adres WYMYSLONY nadal odpada",
        p._valid(OBCY, 600, dozwolone_adresy=(URL,)) is False)
sprawdz("adres e-mail nadal odpada",
        p._valid("Write to kontakt@przyklad.pl about it.", 600,
                 dozwolone_adresy=(URL,)) is False)
sprawdz("zaczepka po nazwie nadal odpada",
        p._valid("Ask @somebody what they think.", 600,
                 dozwolone_adresy=(URL,)) is False)
sprawdz("www bez protokolu nadal odpada",
        p._valid("Go to www.przyklad.pl and see.", 600,
                 dozwolone_adresy=(URL,)) is False)
sprawdz("nasz adres obok wymyslonego nie ratuje calosci",
        p._valid(NOTKA + " see also https://inny.example", 600,
                 dozwolone_adresy=(URL,)) is False)

print()
print("=== 3. RESZTA BRAMEK NIE ZOSTALA PRZY OKAZJI OTWARTA ===")
sprawdz("pusty tekst nadal odpada", p._valid("", 600, (URL,)) is False)
sprawdz("za dlugi tekst nadal odpada",
        p._valid(" ".join(["slowo"] * 601), 600, (URL,)) is False)
sprawdz("brak listy adresow nic nie psuje",
        p._valid("A clean short note about nothing much.", 600) is True)
sprawdz("pusty adres na liscie nie otwiera furtki",
        p._valid("See https://cokolwiek.example now.", 600,
                 dozwolone_adresy=("",)) is False)

print()
print("=== 4. WPIETE TAM, GDZIE SIE PLACI ===")
ZRODLO = io.open("agent-v2/personality.py", encoding="utf-8").read()
CIALO = ""
for w in ast.walk(ast.parse(ZRODLO)):
    if isinstance(w, ast.FunctionDef) and w.name == "short_form":
        CIALO = ast.get_source_segment(ZRODLO, w) or ""
sprawdz("short_form podaje adres zrodla do sprawdzenia",
        "dozwolone_adresy=" in CIALO)
sprawdz("i bierze go z faktu, nie skadinad",
        'material.get("fact") or {}).get("url"' in CIALO)
# Podpowiedz do pamieci ma WLASNY, ostrzejszy zakaz i ma taka zostac:
# tam adres nie niesie nic, a pamiec zyje dlugo.
sprawdz("pamiec nadal bez adresow",
        'not _valid(hint, 30)' in CIALO and 'https?://", hint)' in CIALO)

print()
print("=== 5. INSTRUKCJA I BRAMKA MOWIA TO SAMO ===")
# To jest sedno wpadki: jedno zdanie pozwalalo, drugie zabranialo.
sprawdz("instrukcja nadal pozwala nazwac zrodlo",
        "the URL may go in the text" in ZRODLO)
i_poz = ZRODLO.find("the URL may go in the text")
sprawdz("i bramka o tym wie",
        "dozwolone_adresy" in ZRODLO and i_poz > 0)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
