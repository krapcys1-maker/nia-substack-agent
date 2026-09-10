# -*- coding: utf-8 -*-
"""Proba sucha nie zostawia tekstu na koncie, a prawdziwy wpis nie dokleja sie
do cudzej wersji roboczej.

## Co to wylapuje — TO WYSZLO NA KONTO

10 wrzesnia 2026, pod naszym wlasnym artykulem o zamku, w odpowiedzi
czytelnikowi:

    proba sucha, nic nie wychodziproba suSomeone got a prompt back from
    Chaos Engine and that's the whole review.cha, nic nie wychodzi

„proba sucha, nic nie wychodzi" to tekst probny z wywolania `wyslij=False`.
Zlozyly sie na to dwie wady, obie w `browser.py`:

  1. proba z `wyslij=False` PISALA w prawdziwe pole i tam to zostawiala.
     Substack trzyma wersje robocza, wiec tekst czekal — dwa razy, bo probe
     puscilem dwa razy;
  2. prawdziwa odpowiedz szla `page.keyboard.type` BEZ CZYSZCZENIA, czyli
     w miejsce karetki: w srodek slowa „proba su|cha".

Wlasciciel skasowal to recznie i napisal, ze nie wie, co to bylo.

BEZ PYTESTA, bez sieci, bez przegladarki. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_proba_nie_zostawia_sladu.py
"""
import ast
import io
import sys

sys.path.insert(0, "agent-v2")

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


ZRODLO = io.open("agent-v2/browser.py", encoding="utf-8").read()
DRZEWO = ast.parse(ZRODLO)


def cialo(nazwa):
    for w in ast.walk(DRZEWO):
        if isinstance(w, ast.FunctionDef) and w.name == nazwa:
            return ast.get_source_segment(ZRODLO, w) or ""
    return ""


# Cztery miejsca, w ktorych piszemy w zywe pole na koncie. Piate — publikacja
# artykulu — nie jest polem rozmowy i szkic jest tam ZAMIERZONY.
PISZACE = ("wystaw_odpowiedz_pod_artykulem", "wystaw_odpowiedz",
           "wystaw_notke", "wystaw_komentarz")

print("=== 1. NIKT NIE PISZE W POLE NA SLEPO ===")
for nazwa in PISZACE:
    zrodlo = cialo(nazwa)
    sprawdz("%s istnieje" % nazwa, bool(zrodlo))
    if not zrodlo:
        continue
    sprawdz("  %s idzie przez wpisz_w_puste_pole" % nazwa,
            "wpisz_w_puste_pole(" in zrodlo)
    # KONTRDOWOD: gdyby stare pisanie zostalo obok, model kodu wybralby je,
    # bo jest krotsze — a wada wroci cicho.
    sprawdz("  %s nie pisze juz wprost z klawiatury" % nazwa,
            "keyboard.type(tekst" not in zrodlo)

print()
print("=== 2. PROBA SUCHA SPRZATA PO SOBIE ===")
for nazwa in PISZACE:
    zrodlo = cialo(nazwa)
    if not zrodlo:
        continue
    # Szukamy galezi `elif not wyslij:` i sprzatania w niej.
    i = zrodlo.find("elif not wyslij:")
    ogon = zrodlo[i:i + 500] if i >= 0 else ""
    sprawdz("  %s ma galaz proby suchej" % nazwa, i >= 0)
    sprawdz("  %s czysci pole w probie suchej" % nazwa,
            "oproznij_pole(" in ogon, ogon[:90])

print()
print("=== 3. HELPER ROBI TRZY RZECZY, NIE JEDNA ===")
h = cialo("wpisz_w_puste_pole")
sprawdz("helper istnieje", bool(h))
sprawdz("najpierw czysci", h.find("oproznij_pole(") >= 0
        and h.find("oproznij_pole(") < h.find("keyboard.type("))
sprawdz("potem pisze", "keyboard.type(tekst" in h)
sprawdz("i sprawdza, co naprawde stoi w polu", "_tresc_pola(pole)" in h)
sprawdz("porownuje po golym tekscie, nie znak w znak",
        "plaski(w_polu) != plaski(tekst)" in h)
sprawdz("i mowi o tym glosno", "w polu stoi co innego" in h)

o = cialo("oproznij_pole")
sprawdz("czyszczenie istnieje", bool(o))
sprawdz("zaznacza wszystko", "Control+a" in o)
sprawdz("i kasuje", "Delete" in o and "Backspace" in o)
sprawdz("ponawia, bo edytor bywa uparty", "for _ in range(" in o)
sprawdz("oddaje prawde o wyniku, nie zalozenie",
        "puste = not _tresc_pola(pole).strip()" in o)

c = cialo("_tresc_pola")
sprawdz("czytanie pola obsluguje i textarea, i edytor",
        "el.value" in c and "innerText" in c)

print()
print("=== 4. DZIENNIK WIE, CZY POLE ZGADZALO SIE Z TEKSTEM ===")
# Bez tego pomiar jest bezwartosciowy: dotad drukowalismy „wpisane: 12 słów",
# liczac slowa TEKSTU, nie zawartosci pola. Wpadka byla niewidoczna w logu.
for nazwa in PISZACE:
    zrodlo = cialo(nazwa)
    if not zrodlo:
        continue
    sprawdz("  %s zapisuje zgodnosc z polem" % nazwa,
            'wynik["zgodne_z_polem"]' in zrodlo)

print()
print("=== 5. PUBLIKACJA ARTYKULU NIE ZOSTALA PRZY OKAZJI ZEPSUTA ===")
# Tam szkic JEST celem proby suchej — artykul nie jest rozmowa i nikt go
# nie zobaczy przed wyslaniem.
a = cialo("publikuj_artykul") or ZRODLO
sprawdz("proba sucha artykulu nadal zostawia szkic",
        "szkic zapisany" in a)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
