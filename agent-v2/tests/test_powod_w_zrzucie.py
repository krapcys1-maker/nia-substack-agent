# -*- coding: utf-8 -*-
"""Zrzut czytelnikow mowi nie tylko CO odczytano, ale i DLACZEGO sie nie udalo.

## Co bylo zepsute

`browser.zapisz_czytelnikow` zapisuje pole `odczytane` — liste zakladek, ktore
naprawde odpowiedzialy. To wystarcza, zeby odroznic zrzut okrojony od pelnego,
i NIE wystarcza, zeby powiedziec, co sie stalo. `kto_nas_czyta` rozroznia trzy
przyczyny i wszystkie trzy wygladaly w pliku identycznie — jako krotsza lista:

  * `"nie ma zakladki Subscribers"` — Substack przerysowal profil,
  * `"TimeoutError: ..."` — strona nie wstala,
  * niepowodzenie odczytu odnosnikow na juz otwartej zakladce.

Pierwsza z nich wymaga poprawki kodu, dwie pozostale to awaria jednorazowa,
po ktorej wystarczy nastepny przebieg. Bez zapisanego powodu nie da sie ich
odroznic — a `czytelnicy.jsonl` ma na produkcji siedem zrzutow i jest jedynym
zrodlem odpowiedzi na pytanie „skad biora sie czytelnicy".

## Zgodnosc wstecz, ktorej ten test pilnuje

Siedem istniejacych zrzutow (31 sierpnia i 1 wrzesnia 2026) nie ma pola `blad`
i nie dostanie go nigdy — plik jest dopisywany, nie przepisywany. Ich brak ma
znaczyc „NIE WIADOMO", a nie „nie bylo bledu". Dlatego pole jest zapisywane
ZAWSZE, takze z wartoscia `None`: inaczej brak klucza znaczylby dwie rozne
rzeczy naraz i nowe zrzuty bez bledu bylyby nie do odroznienia od starych.

## Co ten test mierzy

ZACHOWANIE `browser.zapisz_czytelnikow`: co naprawde wpada do pliku przy trzech
roznych odpowiedziach profilu. `kto_nas_czyta` jest podmieniona na atrape,
bo to ona chodzi do sieci; zapis idzie prawdziwym kodem do pliku w katalogu
tymczasowym. Zero asercji po tresci zrodla, zero sieci, zero przegladarki.

KONTRDOWOD JEST ODTWORZONY, NIE OPISANY, i PRZYPIETY DO SHA `6ed4e7d`, nigdy
do HEAD. Ta wersja `zapisz_czytelnikow` jest wycinana z
`git show 6ed4e7d:agent-v2/browser.py` i puszczana na TYCH SAMYCH trzech
odpowiedziach.

Test nie zalezy od dzisiejszej daty: nie porownuje zadnej daty, a `kiedy`
w zrzucie jest tylko odczytywane jako obecne.

PRODUKCJA: bez zmian. `CZYTELNICY` wskazuje katalog tymczasowy.
"""

import ast
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile

KORZEN = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(KORZEN / "agent-v2"))

import browser        # noqa: E402
import config         # noqa: E402

# HISTORIA JEST WARUNKIEM TEGO TESTU — patrz `historia.py`.
import historia   # noqa: E402
historia.wymaga_historii("6ed4e7d")

ODNIESIENIE = "6ed4e7d"        # wersja SPRZED poprawki; nigdy HEAD

zdane = 0
oblane = 0


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


PILNOWANE = [config.DATA_DIR / "czytelnicy.jsonl",
             config.DATA_DIR / "dziennik.jsonl"]
PRZED = {str(p): odcisk(p) for p in PILNOWANE}


# --- TRZY ODPOWIEDZI PROFILU, ODWZOROWANE Z `kto_nas_czyta` ------------------
LUDZIE = [{"uchwyt": "publikacja11", "nazwa": "Jedenasty"}]

PELNY = {"obserwujacy": LUDZIE, "subskrybenci": LUDZIE,
         "odczytane": ["obserwujacy", "subskrybenci"], "blad": None}
OKROJONY = {"obserwujacy": LUDZIE, "subskrybenci": [],
            "odczytane": ["obserwujacy"],
            "blad": "nie ma zakladki Subscribers"}
MARTWY = {"obserwujacy": [], "subskrybenci": [], "odczytane": [],
          "blad": "TimeoutError: strona nie wstala"}

# Zrzut sprzed poprawki — dokladnie taki ksztalt maja cztery z siedmiu wierszy
# na produkcji: ani `odczytane`, ani `blad`.
ZRZUT_STARY = {"kiedy": "2026-08-31T11:38:25+00:00",
               "obserwujacy": LUDZIE, "subskrybenci": LUDZIE}


def zapisz(fn, odpowiedz, plik):
    """Puszcza podana wersje `zapisz_czytelnikow` na jednej odpowiedzi profilu."""
    stare = (browser.CZYTELNICY, browser.kto_nas_czyta)
    try:
        browser.CZYTELNICY = plik
        browser.kto_nas_czyta = lambda page=None: dict(odpowiedz)
        return fn()
    finally:
        browser.CZYTELNICY, browser.kto_nas_czyta = stare


def wiersze(plik):
    if not plik.exists():
        return []
    return [json.loads(x) for x in
            plik.read_text(encoding="utf-8").splitlines() if x.strip()]


def wersja_z_commita(commit: str):
    """`zapisz_czytelnikow` z ZAPISANEJ wersji, wolajaca dzisiejszy `browser`.

    Wycinamy sama funkcje i uruchamiamy ja w przestrzeni nazw dzisiejszego
    modulu — dzieki temu porownujemy DWIE WERSJE ZAPISU na tym samym pliku
    i tej samej atrapie odpowiedzi, a nie dwa rozne swiaty.
    """
    proc = subprocess.run(["git", "-C", str(KORZEN), "show",
                           "%s:agent-v2/browser.py" % commit],
                          capture_output=True)
    if proc.returncode != 0:
        raise SystemExit("nie dostalem browser.py z %s" % commit)
    src = proc.stdout.decode("utf-8")
    for w in ast.walk(ast.parse(src)):
        if isinstance(w, ast.FunctionDef) and w.name == "zapisz_czytelnikow":
            linie = src.splitlines()[w.lineno - 1:w.end_lineno]
            kod = "\n".join(linie)
            ns = {}
            exec(compile(kod, "browser.py@%s" % commit, "exec"),
                 browser.__dict__, ns)
            return ns["zapisz_czytelnikow"]
    raise SystemExit("nie znalazlem zapisz_czytelnikow w %s" % commit)


print("=== 1. ZRZUT BEZ BLEDU MOWI TO WPROST, A NIE MILCZENIEM ===")
kat = pathlib.Path(tempfile.mkdtemp())
plik = kat / "czytelnicy.jsonl"
zapisz(browser.zapisz_czytelnikow, PELNY, plik)
w = wiersze(plik)
print("    zrzut: %s" % json.dumps(w[0], ensure_ascii=False))
sprawdz("klucz `blad` JEST, choc bledu nie bylo",
        "blad" in w[0] and w[0]["blad"] is None, w)
sprawdz("obie zakladki odczytane", w[0]["odczytane"]
        == ["obserwujacy", "subskrybenci"], w)

print()
print("=== 2. ZRZUT OKROJONY MOWI, DLACZEGO ===")
kat2 = pathlib.Path(tempfile.mkdtemp())
plik2 = kat2 / "czytelnicy.jsonl"
zapisz(browser.zapisz_czytelnikow, OKROJONY, plik2)
w2 = wiersze(plik2)
print("    zrzut: %s" % json.dumps(w2[0], ensure_ascii=False))
sprawdz("powod jest w pliku, a nie tylko w logu przebiegu",
        w2[0].get("blad") == "nie ma zakladki Subscribers", w2)
sprawdz("i widac, ze subskrybentow NIE odczytano",
        w2[0]["odczytane"] == ["obserwujacy"], w2)
sprawdz("pusta lista subskrybentow nie udaje konta bez subskrybentow",
        w2[0]["subskrybenci"] == [] and w2[0].get("blad"), w2)

print()
print("=== 3. NIC NIE ODCZYTANE TO NADAL BRAK ZRZUTU ===")
kat3 = pathlib.Path(tempfile.mkdtemp())
plik3 = kat3 / "czytelnicy.jsonl"
wynik3 = zapisz(browser.zapisz_czytelnikow, MARTWY, plik3)
sprawdz("przebieg, w ktorym strona nie wstala, nie zostawia zrzutu",
        wynik3 is None and wiersze(plik3) == [], wiersze(plik3))

print()
print("=== 4. ZGODNOSC WSTECZ: SIEDEM STARYCH ZRZUTOW BEZ ZMIAN ===")
kat4 = pathlib.Path(tempfile.mkdtemp())
plik4 = kat4 / "czytelnicy.jsonl"
plik4.write_text(json.dumps(ZRZUT_STARY, ensure_ascii=False) + "\n",
                 encoding="utf-8")
przed = plik4.read_text(encoding="utf-8")
zapisz(browser.zapisz_czytelnikow, OKROJONY, plik4)
teraz = plik4.read_text(encoding="utf-8")
w4 = wiersze(plik4)
sprawdz("stary wiersz nie zostal ruszony ani o znak",
        teraz.startswith(przed), teraz[:120])
sprawdz("i nadal nie ma klucza `blad` — czyli „nie wiadomo”",
        "blad" not in w4[0], w4[0])
sprawdz("czytajacy z wartoscia zapasowa dostaje „nie wiadomo”, a nie „bez bledu”",
        w4[0].get("blad", "nie wiadomo") == "nie wiadomo", w4[0])
sprawdz("a nowy wiersz obok niesie powod",
        w4[1].get("blad") == "nie ma zakladki Subscribers", w4[1])

print()
print("=== 5. KONTRDOWOD: WERSJA Z %s NIE ZAPISUJE POWODU ===" % ODNIESIENIE)
stara = wersja_z_commita(ODNIESIENIE)
kat5 = pathlib.Path(tempfile.mkdtemp())
plik5 = kat5 / "czytelnicy.jsonl"
zapisz(stara, OKROJONY, plik5)
zapisz(stara, PELNY, plik5)
w5 = wiersze(plik5)
print("    STARY zrzut okrojony: %s" % json.dumps(w5[0], ensure_ascii=False))
sprawdz("KONTRDOWOD: stara wersja nie zapisuje ani slowa o przyczynie",
        "blad" not in w5[0], w5[0])
sprawdz("KONTRDOWOD: zrzut okrojony jest u niej NIE DO ODROZNIENIA od pelnego",
        set(w5[0]) == set(w5[1]), (w5[0], w5[1]))
sprawdz("KONTRDOWOD: i wyglada jak konto, ktore po prostu nie ma"
        " subskrybentow", w5[0]["subskrybenci"] == [], w5[0])
kat6 = pathlib.Path(tempfile.mkdtemp())
plik6 = kat6 / "czytelnicy.jsonl"
zapisz(browser.zapisz_czytelnikow, OKROJONY, plik6)
zapisz(browser.zapisz_czytelnikow, PELNY, plik6)
w6 = wiersze(plik6)
sprawdz("DZIS te same dwie odpowiedzi daja dwa ROZNE wiersze",
        w6[0].get("blad") != w6[1].get("blad"),
        (w6[0].get("blad"), w6[1].get("blad")))

print()
print("=== PRODUKCJA: bez zmian ===")
for p in PILNOWANE:
    t = odcisk(p)
    ok = t == PRZED[str(p)]
    print("  %-30s %s" % (p.name, "bez zmian" if ok else "ZMIENIONY"))
    if not ok:
        oblane += 1

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
