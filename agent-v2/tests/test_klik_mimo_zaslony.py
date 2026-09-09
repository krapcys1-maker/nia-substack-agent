# -*- coding: utf-8 -*-
"""Zaslonięty przycisk ma dostac zdarzenie, a nie kolejne trzydziesci sekund.

## Po co ten plik istnieje

Od 8 wrzesnia 2026 odpowiedzi przestaly wychodzic na konto: zero porazek przez
trzy poprzednie dni, cztery 8 wrzesnia, trzy w nocy z 8 na 9. Za kazdym razem
ten sam komunikat, slowo w slowo:

    Locator.click: Timeout 30000ms exceeded
    <div class="pencraft pc-display-flex pc-flexDirection-column ..."> …
    from <div id="entry"> … subtree intercepts pointer events

Przycisk BYL znajdowany, byl widoczny i byl wlaczony. Zaslania go panel
Substacka wewnatrz `#entry`, a Playwright — slusznie — odmawia klikniecia
w miejsce, gdzie zdarzenie dostanie kto inny. Ponawial przez trzydziesci
sekund, wiec to nie bylo migniecie: zaslona stoi.

Notki, komentarze i restacki wychodzily w tym czasie normalnie. Wada dotyczy
jednego widoku.

## Czego ten test pilnuje

TRZECH rzeczy, i kazda z nich jest osobnym sposobem, w jaki taka poprawka
psuje sie po cichu:

1. Gdy nikt nie zaslania, nic sie nie zmienia — normalna droga jest pierwsza,
   a awaryjne wyjscie nie ma prawa sie wlaczyc.
2. Gdy zaslania, zdarzenie idzie NA TEN element, ktory juz mamy.
3. Kazdy INNY blad leci dalej. „Przycisku nie ma" i „przycisk zaslonily" to
   dwie rozne sprawy, a poprawka, ktora polyka pierwsza, zamienia brak
   przycisku w cicha porazke bez sladu.

## Czego tu NIE ma i dlaczego

`force=True`. To by nie naprawilo, tylko ukrylo: `force` pomija sprawdzenia
i klika w te same wspolrzedne, czyli trafia dokladnie w zaslaniajacy panel.
Dostalibysmy „klikniete" i zadnej odpowiedzi.

BEZ PYTESTA, bez sieci, bez przegladarki. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_klik_mimo_zaslony.py
"""
import sys

sys.path.insert(0, "agent-v2")
import browser  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# KOMUNIKAT PRZEPISANY Z PRODUKCJI, nie wymyslony. Gdyby Playwright zmienil
# to zdanie, ten test ma oblac — bo wtedy rozpoznanie po tresci przestaje
# dzialac i awaryjne wyjscie milczy dokladnie wtedy, gdy jest potrzebne.
ZASLONA = ("Locator.click: Timeout 30000ms exceeded. Call log: - waiting for"
           ' get_by_role("button", name="Post").first - <div class="pencraft'
           ' pc-display-flex pc-flexDirection-column pc-gap-8"></div> from'
           ' <div id="entry"></div> subtree intercepts pointer events'
           " - retrying click action")

INNY_BLAD = ("Locator.click: Timeout 30000ms exceeded. Call log: - waiting for"
             " element to be visible, enabled and stable")


class Zwykly:
    def __init__(self):
        self.klikniety = False

    def click(self):
        self.klikniety = True

    def evaluate(self, js):
        raise AssertionError("awaryjne wyjscie wlaczylo sie bez powodu")


class Zaslonietty:
    def __init__(self):
        self.js = None

    def click(self):
        raise Exception(ZASLONA)

    def evaluate(self, js):
        self.js = js


class Nieobecny:
    def click(self):
        raise Exception(INNY_BLAD)

    def evaluate(self, js):
        raise AssertionError("polknelismy blad, ktory nie jest zaslona")


print("=== 1. BEZ ZASLONY NIC SIE NIE ZMIENIA ===")
z = Zwykly()
droga = browser.klik_mimo_zaslony(z)
sprawdz("normalny klik wykonany", z.klikniety is True)
sprawdz("droga zapisana jako zwykla", droga == "zwykly", droga)

print()
print("=== 2. ZASLONA: ZDARZENIE IDZIE WPROST NA ELEMENT ===")
z = Zaslonietty()
droga = browser.klik_mimo_zaslony(z, "odpowiedz")
sprawdz("droga zapisana jako awaryjna", droga == "mimo zaslony", droga)
sprawdz("zdarzenie poszlo na TEN element", z.js == "el => el.click()", str(z.js))
# Wspolrzedne sa wlasnie tym, czego nie chcemy uzywac: pod nimi siedzi panel.
sprawdz("nie uzyto wspolrzednych ani force",
        "force" not in str(z.js) and "mouse" not in str(z.js), str(z.js))

print()
print("=== 3. KAZDY INNY BLAD LECI DALEJ ===")
# Poprawka, ktora polyka „przycisku nie ma", zamienia brak przycisku w cicha
# porazke bez sladu w dzienniku.
try:
    browser.klik_mimo_zaslony(Nieobecny())
    sprawdz("inny blad przekazany dalej", False, "zostal polkniety")
except AssertionError:
    raise
except Exception as exc:
    sprawdz("inny blad przekazany dalej", "visible, enabled and stable" in str(exc),
            str(exc)[:70])

print()
print("=== 4. SCIEZKA ODPOWIEDZI UZYWA TEJ DROGI ===")
# Gdyby ktos przywrocil goly `przycisk.click()`, wszystkie testy wyzej nadal
# przechodzilyby, a odpowiedzi znowu przestalyby wychodzic.
# CZTERY MIEJSCA, NIE JEDNO. Pierwsza wersja tego sprawdzenia szukala jednego
# wycinka po napisie „wpisane w pole odpowiedzi" — a ten napis pada w DWOCH
# funkcjach (odpowiedz pod notka i odpowiedz pod naszym artykulem), wiec test
# ogladal nie te sciezke, ktora poprawilem, i oblewal z niewlasciwego powodu.
#
# Liczymy wiec wszystkie klikniecia przycisku publikacji w pliku. Padalo tylko
# jedno z nich, ale funkcja jest dowodnie bezczynna, gdy klik przechodzi
# (sekcja 1), a ta sama zaslona przy notce albo komentarzu zabralaby kontu
# chleb powszedni.
import re as _re
zrodlo = open("agent-v2/browser.py", encoding="utf-8").read()
# CIALO SAMEGO HELPERA WYLACZONE Z LICZENIA. Jedno gole `przycisk.click()`
# stoi w nim i ma stac: to jest ta normalna droga, ktora probujemy najpierw.
_od = zrodlo.index("def klik_mimo_zaslony")
_do = zrodlo.index("def konto_za_duze")
poza_helperem = zrodlo[:_od] + zrodlo[_do:]
gole = _re.findall(r"^\s+(?:przycisk|wyslac)\.click\(\)\s*$", poza_helperem, _re.M)
przez_helper = zrodlo.count("klik_mimo_zaslony(")
sprawdz("zero golych klikniec przycisku publikacji", not gole,
        "zostalo %d: %s" % (len(gole), gole))
sprawdz("wszystkie ida przez helper (definicja + cztery wywolania)",
        przez_helper >= 5, "wystapien: %d" % przez_helper)
sprawdz("droga trafia do dziennika",
        zrodlo.count("droga_klikniecia") >= 4,
        "wystapien: %d" % zrodlo.count("droga_klikniecia"))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
