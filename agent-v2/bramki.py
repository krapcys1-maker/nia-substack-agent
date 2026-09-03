# -*- coding: utf-8 -*-
"""Co moze zatrzymac tresc — wyliczone z kodu, nie spisane z pamieci.

PO CO TO POWSTALO. 2 wrzesnia 2026 wlasciciel zadal najprostsze pytanie, jakie
mozna zadac o tego agenta: „czy cos sie blokuje?". Odpowiedz zajela pol godziny
i wymagala czterech rownoleglych agentow czytajacych kod — mimo ze repozytorium
ma mape na 12 774 wiersze, doktryne i dwa audyty.

Powod jest prosty: te dokumenty opisuja, Z CZEGO bot jest zbudowany. Nie
odpowiadaja na pytanie, CO MOZE ZATRZYMAC TRESC. A to jest pytanie zadawane
najczesciej i jedyne, ktore w tym projekcie naprawde boli — bo zasada brzmi:
NIC SIE NIE BLOKUJE, nic nie czeka na czlowieka, lepiej zeby wyszlo cos
niejasnego, niz zeby nie wyszlo nic.

DLACZEGO PRZYRZAD, A NIE DOKUMENT. Dokument opisujacy bramki bylby prawdziwy
w dniu napisania i falszywy tydzien pozniej. Ten sam dzien dostarczyl dwoch
dowodow: zdanie o przycisku Follow bylo cytowane przez dziewiec dni po tym, jak
przestalo byc prawda, a pomiar pytajnikow w notkach opieral sie na polu, ktore
kod obcinal. Lista wyliczana z DRZEWA SKLADNI nie moze sie rozjechac z kodem,
bo jest kodem odczytanym.

CZEGO TO NIE ROBI. Nie ocenia, czy bramka jest sluszna — pokazuje, ze istnieje,
gdzie stoi i co ja wlacza. Ocena nalezy do czlowieka.

Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/bramki.py
    PYTHONIOENCODING=utf-8 python agent-v2/bramki.py --pelne   (z trescia warunkow)
"""
from __future__ import annotations

import ast
import io
import sys
from pathlib import Path

KORZEN = Path(__file__).resolve().parent

# Pliki, w ktorych moze stac cokolwiek zatrzymujacego tresc.
PLIKI = ("stages.py", "run.py", "browser.py", "artykul_z_puli.py")

# Funkcje, ktorych wywolanie ZNACZY „tresc idzie w swiat". Wszystko, co stoi
# miedzy decyzja a nimi, jest potencjalna bramka.
WYSTAWIENIA = ("wystaw_notke", "wystaw_komentarz", "wystaw_odpowiedz",
               "wystaw_artykul", "wystaw_odpowiedz_pod_artykulem",
               "polub", "restack", "obserwuj_autora", "subskrybuj_autora")


def _zrodlo(nazwa: str) -> tuple[str, ast.Module] | None:
    p = KORZEN / nazwa
    if not p.exists():
        return None
    tekst = p.read_text(encoding="utf-8")
    try:
        return tekst, ast.parse(tekst)
    except SyntaxError as exc:
        print("  !! %s nie parsuje sie: %s" % (nazwa, exc))
        return None


def _komentarz_nad(linie: list[str], nr: int, ile: int = 6) -> str:
    """Ostatnia linia komentarza nad wskazanym wierszem — zwykle uzasadnienie."""
    out = []
    i = nr - 2                     # nr jest 1-indeksowane
    while i >= 0 and len(out) < ile:
        l = linie[i].strip()
        if l.startswith("#"):
            out.append(l.lstrip("# ").strip())
            i -= 1
            continue
        break
    return " ".join(reversed(out))[:150]


def _rodzic_funkcji(drzewo: ast.Module) -> dict[int, str]:
    """Mapa: numer wiersza -> nazwa funkcji, w ktorej ten wiersz lezy."""
    mapa: dict[int, str] = {}
    for w in ast.walk(drzewo):
        if isinstance(w, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for nr in range(w.lineno, (w.end_lineno or w.lineno) + 1):
                mapa.setdefault(nr, w.name)
    return mapa


def wstrzymania_publikacji(pelne: bool = False) -> list[dict]:
    """Kazde miejsce, ktore ustawia `safe_to_post` na falsz."""
    out = []
    for nazwa in PLIKI:
        z = _zrodlo(nazwa)
        if not z:
            continue
        tekst, drzewo = z
        linie = tekst.split("\n")
        gdzie = _rodzic_funkcji(drzewo)
        for w in ast.walk(drzewo):
            if not isinstance(w, ast.Assign):
                continue
            for cel in w.targets:
                if (isinstance(cel, ast.Subscript)
                        and isinstance(cel.slice, ast.Constant)
                        and cel.slice.value == "safe_to_post"):
                    wartosc = ast.unparse(w.value)
                    if wartosc in ("True",):
                        continue
                    out.append({
                        "plik": nazwa, "linia": w.lineno,
                        "funkcja": gdzie.get(w.lineno, "(modul)"),
                        "wartosc": wartosc,
                        "powod": _komentarz_nad(linie, w.lineno),
                    })
    return out


def warunki_przed_wystawieniem(pelne: bool = False) -> list[dict]:
    """Kazde wystawienie tresci i warunki, pod ktorymi stoi.

    Idziemy od wywolania W GORE po rodzicach i zbieramy `if`-y. To pokazuje,
    co musi byc prawda, zeby tresc w ogole wyszla.
    """
    out = []
    for nazwa in PLIKI:
        z = _zrodlo(nazwa)
        if not z:
            continue
        tekst, drzewo = z
        gdzie = _rodzic_funkcji(drzewo)
        # rodzice, zeby dalo sie isc w gore
        rodzic: dict[int, ast.AST] = {}
        for w in ast.walk(drzewo):
            for dziecko in ast.iter_child_nodes(w):
                rodzic[id(dziecko)] = w
        for w in ast.walk(drzewo):
            if not isinstance(w, ast.Call):
                continue
            f = w.func
            nazwa_f = getattr(f, "attr", None) or getattr(f, "id", None)
            if nazwa_f not in WYSTAWIENIA:
                continue
            if gdzie.get(w.lineno, "").startswith(nazwa_f):
                continue          # sama definicja, nie wywolanie z zewnatrz
            warunki = []
            biezacy: ast.AST | None = w
            while biezacy is not None:
                biezacy = rodzic.get(id(biezacy))
                if isinstance(biezacy, ast.If):
                    warunki.append(ast.unparse(biezacy.test)[:110])
                if isinstance(biezacy, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    break
            out.append({
                "plik": nazwa, "linia": w.lineno,
                "co": nazwa_f,
                "funkcja": gdzie.get(w.lineno, "(modul)"),
                "warunki": list(reversed(warunki)),
            })
    return out


def przerwania_w_petlach() -> list[dict]:
    """`continue` i `return` w petlach po kandydatach — czyli „ten odpada"."""
    out = []
    for nazwa in PLIKI:
        z = _zrodlo(nazwa)
        if not z:
            continue
        tekst, drzewo = z
        linie = tekst.split("\n")
        gdzie = _rodzic_funkcji(drzewo)
        # WARUNEK, NIE KOMENTARZ. Pierwsza wersja pokazywala komentarz nad
        # `continue` i przy kazdym wpisie wypisywala „(bez komentarza)" — bo
        # uzasadnienie w tym repozytorium stoi nad `if`, a nie nad samym
        # odrzuceniem. Pytanie brzmi „co odrzuca", wiec odpowiedzia jest
        # WARUNEK, ktory do `continue` doprowadzil.
        rodzic: dict[int, ast.AST] = {}
        for w in ast.walk(drzewo):
            for dziecko in ast.iter_child_nodes(w):
                rodzic[id(dziecko)] = w

        for w in ast.walk(drzewo):
            if not isinstance(w, ast.For):
                continue
            cel = ast.unparse(w.target)
            zrodlo_petli = ast.unparse(w.iter)[:60]
            if not any(s in zrodlo_petli for s in
                       ("candidates", "kandyd", "cele", "gotowe", "dobre")):
                continue
            for n in ast.walk(w):
                if not isinstance(n, ast.Continue):
                    continue
                warunek = ""
                biezacy: ast.AST | None = n
                while biezacy is not None and not warunek:
                    biezacy = rodzic.get(id(biezacy))
                    if isinstance(biezacy, ast.If):
                        warunek = ast.unparse(biezacy.test)[:100]
                    elif isinstance(biezacy, ast.For):
                        break
                out.append({
                    "plik": nazwa, "linia": n.lineno,
                    "funkcja": gdzie.get(n.lineno, "(modul)"),
                    "petla": "for %s in %s" % (cel, zrodlo_petli),
                    "powod": ("odrzuca gdy: %s" % warunek) if warunek
                             else (_komentarz_nad(linie, n.lineno)
                                   or "(bezwarunkowe)"),
                })
    return out


def raport(pelne: bool = False) -> str:
    linie: list[str] = []
    d = linie.append
    d("=" * 78)
    d("CO MOZE ZATRZYMAC TRESC — wyliczone z drzewa skladni, %d plikow"
      % len(PLIKI))
    d("=" * 78)

    w = wstrzymania_publikacji()
    d("")
    d("## 1. MIEJSCA USTAWIAJACE `safe_to_post` NA FALSZ  (%d)" % len(w))
    d("")
    if not w:
        d("   ZADNE. Nic nie odbiera tresci prawa do publikacji.")
    for x in w:
        d("   %s:%-5d  w %s" % (x["plik"], x["linia"], x["funkcja"]))
        d("       wartosc: %s" % x["wartosc"])
        if x["powod"]:
            d("       powod:   %s" % x["powod"])
        d("")

    p = przerwania_w_petlach()
    d("## 2. KANDYDAT ODRZUCANY W PETLI (`continue`)  (%d)" % len(p))
    d("")
    for x in p:
        d("   %s:%-5d  w %s   [%s]" % (x["plik"], x["linia"], x["funkcja"],
                                       x["petla"]))
        d("       %s" % x["powod"][:120])
    if not p:
        d("   ZADNE.")
    d("")

    c = warunki_przed_wystawieniem()
    d("## 3. WYSTAWIENIA I WARUNKI, POD KTORYMI STOJA  (%d)" % len(c))
    d("")
    for x in c:
        d("   %s:%-5d  %s()  w %s" % (x["plik"], x["linia"], x["co"],
                                      x["funkcja"]))
        for war in x["warunki"]:
            d("       if %s" % war)
        if not x["warunki"]:
            d("       (bez warunku — wywolanie bezwarunkowe)")
    d("")
    d("=" * 78)
    d("CZEGO TA LISTA NIE MOWI: czy bramka jest SLUSZNA. Pokazuje, ze istnieje,")
    d("gdzie stoi i co ja wlacza. Ocena nalezy do czlowieka.")
    d("=" * 78)
    return "\n".join(linie)


if __name__ == "__main__":
    print(raport("--pelne" in sys.argv))
