# -*- coding: utf-8 -*-
"""Pominiecie subskrypcji nie liczy sie jak nieudana proba.

## Co pokazywal dziennik

Od tygodnia: subskrypcje 0 na 10. Wygladalo to na dziesiec nieudanych prob.

W przebiegu z 9 wrzesnia 13:30 UTC bylo OSIEM POMINIEC I ZERO PROB. Nikt
nigdzie nie wszedl i nikt niczego nie kliknal: dla kazdego kandydata
odczytalismy publiczna liczbe odbiorcow, zobaczylismy, ze przekracza sufit,
i odeszlismy.

Zapisywalo sie to jednak przez `dopisz_wynik("subskrypcja", {})` — z pustym
wynikiem, czyli jako NIEUDANA SUBSKRYPCJA. Skutek byl podwojny:

  * licznik „porazek pod rzad" rosl do osmiu bez ani jednego klikniecia,
    wiec hamulec zaczynal blokowac blok, ktory nic zlego nie zrobil;
  * alarm o wolumenach liczyl pominiecia jako niewykonana norme.

Kod przeczyl przy tym wlasnemu komentarzowi, ktory stoi dwie linijki wyzej
i mowi wprost: „POMINIECIE NIE JEST PROBA — odczytalismy publiczna liczbe
i odeszlismy".

## Wzorzec juz istnial

`subskrypcja_pominieta` z `udane=True` stoi POZA `norma.RODZAJE`, wiec nie
liczy sie ani do wykonanych, ani do nieudanych, i nie zjada slotu. Uzywaly go
juz duble (`run.py`) i sito rozmiaru w `browser._klik_na_profilu`. Dwa
pozostale miejsca w `run.py` go nie uzywaly.

BEZ PYTESTA, bez sieci, bez przegladarki. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_pominiecie_to_nie_porazka.py
"""
import ast
import io
import sys

sys.path.insert(0, "agent-v2")
import norma  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


RUN = io.open("agent-v2/run.py", encoding="utf-8").read()
BROWSER = io.open("agent-v2/browser.py", encoding="utf-8").read()

print("=== 1. POMINIECIE STOI POZA NORMA ===")
# Gdyby ktos dopisal ten rodzaj do `RODZAJE`, poprawka odwrocilaby sie
# w druga strone: pominiecia zaczelyby sie liczyc jako WYKONANA praca.
sprawdz("`subskrypcja` liczy sie do normy", "subskrypcja" in norma.RODZAJE)
sprawdz("`subskrypcja_pominieta` NIE liczy sie do normy",
        "subskrypcja_pominieta" not in norma.RODZAJE, sorted(norma.RODZAJE))
sprawdz("tak samo jak pominiecie obserwacji",
        "obserwacja_pominieta" not in norma.RODZAJE)

print()
print("=== 2. ZADNE POMINIECIE NIE ZAPISUJE SIE JAKO SUBSKRYPCJA ===")
# Pytamy SKLADNI: czy gdziekolwiek w `run.py` stoi `dopisz_wynik` z rodzajem
# „subskrypcja" i PUSTYM wynikiem. Pusty wynik znaczy porazke.
drzewo = ast.parse(RUN)
winne = []
for wezel in ast.walk(drzewo):
    if not (isinstance(wezel, ast.Call) and isinstance(wezel.func, ast.Attribute)
            and wezel.func.attr == "dopisz_wynik"):
        continue
    if len(wezel.args) < 2:
        continue
    rodzaj, wynik = wezel.args[0], wezel.args[1]
    if (isinstance(rodzaj, ast.Constant) and rodzaj.value == "subskrypcja"
            and isinstance(wynik, ast.Dict) and not wynik.keys):
        winne.append(wezel.lineno)
sprawdz("zero zapisow `dopisz_wynik('subskrypcja', {})`", not winne,
        "linie: %s" % winne)

print()
print("=== 3. KAZDE POMINIECIE MA WLASCIWY RODZAJ I `udane=True` ===")
# ZE SKLADNI, NIE Z `find`. Pierwsza wersja szukala komunikatu „nie ustalilem
# konta autora" i trafiala w BLOK OBSERWACJI, bo oba bloki niosa to samo
# zdanie. Oblala — i wlasnie dzieki temu wyszlo, ze obserwacja ma dokladnie
# ta sama wade, o ktorej audyt nie wspominal.
POMINIECIA = ("subskrypcja_pominieta", "obserwacja_pominieta")
zapisy = []
for wezel in ast.walk(drzewo):
    if not (isinstance(wezel, ast.Call) and isinstance(wezel.func, ast.Attribute)
            and wezel.func.attr == "zapisz_w_dzienniku"):
        continue
    if not (wezel.args and isinstance(wezel.args[0], ast.Constant)
            and wezel.args[0].value in POMINIECIA):
        continue
    udane = next((k.value for k in wezel.keywords if k.arg == "udane"), None)
    zapisy.append((wezel.lineno, wezel.args[0].value,
                   isinstance(udane, ast.Constant) and udane.value is True))

sprawdz("oba rodzaje pominiec sa uzywane",
        {r for _, r, _ in zapisy} == set(POMINIECIA),
        sorted({r for _, r, _ in zapisy}))
sprawdz("kazde pominiecie z `udane=True`",
        all(ok for _, _, ok in zapisy),
        [(l, r) for l, r, ok in zapisy if not ok])
sprawdz("pominiec jest co najmniej cztery", len(zapisy) >= 4,
        [(l, r) for l, r, _ in zapisy])

print()
print("=== 4. SLAD ZOSTAJE — POMINIECIE NIE JEST CISZA ===")
# Druga strona tej samej zasady. Dzien bez ani jednej proby ma powiedziec
# DLACZEGO; gdybysmy przestali zapisywac cokolwiek, blok wygladalby z zewnatrz
# na blok, ktorego nie ma.
LINIE_RUN = RUN.splitlines()
for linia, rodzaj, _ in zapisy:
    okno = "\n".join(LINIE_RUN[linia - 1:linia + 6])
    ma_powod = "powod=" in okno
    sprawdz("%s (linia %d) zapisuje powod" % (rodzaj, linia), ma_powod,
            okno[:120])

print()
print("=== 5. PRZEGLADARKA ROBILA TO POPRAWNIE OD DAWNA ===")
# Kontrdowod, ze to nie jest nowa konwencja wymyslona przy tej poprawce.
sprawdz("`_klik_na_profilu` zapisuje pominiecie tak samo",
        'zapisz_w_dzienniku("subskrypcja_pominieta", udane=True' in BROWSER)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
