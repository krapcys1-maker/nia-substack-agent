# -*- coding: utf-8 -*-
"""Kazdy odpad kandydata na restack zostawia slad, i na koncu jest rachunek.

## Pomiar

Raport normy, produkcja, 7-10 wrzesnia 2026: restacki na 42 procent normy,
przy JEDNEJ nieudanej probie w calym oknie. Czyli nie padaja — po prostu ich
nie ma. W logu, co dzien to samo:

    -- restacki --
      notek w kanale do rozwazenia: 6
      [restack] claude-opus-5  wej=8541 wyj=220  $0.0482
        RESTACK u Benjamin Laval: ...
        podane dalej 1/2

Szesciu kandydatow i JEDNO pytanie do modelu. Pieciu odpadlo przed ocena i nie
zostawilo po sobie ani slowa, bo wszystkie trzy odsiewy konczyly sie golym
`continue`: przycisk niewidoczny, notka nasza, brak odczytanej tresci.

Z zewnatrz wygladalo to na pusty kanal. Kanal pusty nie byl.

## Czego ten test NIE robi

Nie rozstrzyga, ktory z trzech odsiewow zjada kandydatow — tego nie wie nikt,
dopoki nie zmierzy. Pilnuje tylko, zeby nastepny przebieg to POWIEDZIAL, i zeby
nikt nie wrocil do cichego `continue`.

BEZ PYTESTA, bez sieci, bez przegladarki. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_restack_mowi_czemu_odpadl.py
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
CIALO = ""
for w in ast.walk(ast.parse(ZRODLO)):
    if isinstance(w, ast.FunctionDef) and w.name == "restackuj_w_kanale":
        CIALO = ast.get_source_segment(ZRODLO, w) or ""

print("=== 1. TRZY ODSIEWY MOWIA O SOBIE ===")
sprawdz("blok restackow znaleziony", bool(CIALO))
for opis, fraza in (("przycisk niewidoczny", "przycisk niewidoczny"),
                    ("nasza wlasna notka", "to nasza wlasna notka"),
                    ("nie odczytalem tresci", "nie odczytalem tresci notki")):
    sprawdz("mowi o odpadzie: %s" % opis, fraza in CIALO, fraza)

print()
print("=== 2. I KAZDY MA SWOJ LICZNIK ===")
for pole in ("niewidoczne", "nasze", "bez_tresci"):
    sprawdz("licznik %s" % pole, 'wynik["%s"] = wynik.get("%s", 0) + 1'
            % (pole, pole) in CIALO, pole)
# Ten byl juz wczesniej i ma zostac.
sprawdz("poza rewirem nadal liczony", '"poza_rewirem"' in CIALO)

print()
print("=== 3. NA KONIEC JEST RACHUNEK CALEGO BLOKU ===")
# Bez jednego zdania podsumowania trzeba czytac log linia po linii, zeby
# odpowiedziec na pytanie „czemu jeden restack, skoro budzet ma cztery".
sprawdz("rachunek istnieje", '  rachunek: %d znalezionych' in CIALO)
for co in ("niewidocznych", "naszych", "bez tresci", "poza rewirem",
           "ocenionych", "odmow", "podanych dalej"):
    sprawdz("rachunek podaje: %s" % co, co in CIALO, co)
# ZAWSZE, nie tylko w trybie sprawdzenia — inaczej produkcja nadal milczy.
# OSTATNIE `if not wyslij:`, nie pierwsze — w tej funkcji sa dwa, a chodzi
# o to koncowe, ktore drukuje „nie klikam — tryb sprawdzenia".
i_rachunek = CIALO.find('print("  rachunek:')
i_sucha = CIALO.rfind("if not wyslij:")
sprawdz("rachunek stoi PRZED koncowa galezia proby suchej",
        0 <= i_rachunek < i_sucha, "%d / %d" % (i_rachunek, i_sucha))

print()
print("=== 4. ZADEN ODSIEW NIE ZOSTAL CICHY ===")
# Kontrdowod po drzewie skladni: szukamy `continue`, po ktorym w tym samym
# bloku nie ma zadnego `print`. Napis by tu nie wystarczyl — komentarze
# w tym pliku same zawieraja slowo `continue`.
drzewo = ast.parse(CIALO)
ciche = 0
for wezel in ast.walk(drzewo):
    for pole in ("body", "orelse", "finalbody"):
        blok = getattr(wezel, pole, None)
        if not isinstance(blok, list):
            continue
        for nr, krok in enumerate(blok):
            if not isinstance(krok, ast.Continue):
                continue
            poprzednie = blok[:nr]
            mowi = any(isinstance(x, ast.Expr) and isinstance(x.value, ast.Call)
                       and isinstance(x.value.func, ast.Name)
                       and x.value.func.id == "print"
                       for x in poprzednie)
            # GALAZ PROBY SUCHEJ NIE JEST ODSIEWEM. `if not wyslij: continue`
            # stoi TUZ POD wydrukowana decyzja („RESTACK u …") i znaczy tylko
            # tyle, ze w trybie sprawdzenia nie klikamy. Liczenie jej jako
            # cichego odpadu kazaloby dopisac tam zbedne zdanie do logu.
            proba_sucha = (isinstance(wezel, ast.If)
                           and "wyslij" in ast.dump(wezel.test))
            if not mowi and not proba_sucha:
                ciche += 1
sprawdz("nie ma `continue` bez slowa wyjasnienia", ciche == 0, ciche)

print()
print("=== 5. NIC INNEGO NIE ZOSTALO PRZY OKAZJI RUSZONE ===")
sprawdz("odstep nadal PRZED kolejnym restackiem",
        'if wynik["restackowane"]:' in CIALO)
sprawdz("norma nadal przerywa petle", 'wynik["restackowane"] >= ile' in CIALO)
sprawdz("odmowa modelu nadal zapisywana", 'wynik["odmowy"].append' in CIALO)
sprawdz("porazka nadal idzie do dziennika",
        'zapisz_w_dzienniku("restack", udane=False' in CIALO)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
