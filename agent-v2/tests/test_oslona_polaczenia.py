# -*- coding: utf-8 -*-
"""Nieudane podlaczenie nie moze zabrac reszty doby.

## Co sie stalo

9 wrzesnia 2026 o 00:30 padly po kolei subskrypcje, komentarze, dyskusje
i restacki. Kazdy blok tym samym komunikatem:

    Playwright Sync API inside the asyncio loop

Pierwsza proba podlaczenia sie nie udala, a `sync_playwright().start()`
zostal w procesie. Instancja Playwrighta jest jedna na proces, wiec kazdy
NASTEPNY blok dnia probowal ja utworzyc jeszcze raz i padal.

## Dlaczego to bylo latwe do trafienia

Galaz serwerowa `podlacz_sie` wchodzila w `connect_over_cdp` BEZ OSLONY,
podczas gdy galaz lokalna, dziesiec linijek nizej, ma `try/except` z
`p.stop()` od poczatku. Warunek wejscia (`_chrome_odpowiada()`) sprawdza
tylko, czy port cokolwiek odpowiada — Chrome moze odpowiedziec na sprawdzenie
i odmowic polaczenia sekunde pozniej.

## Regula

Kazda galaz, ktora WOLA `sync_playwright().start()`, musi umiec go zatrzymac,
gdy podlaczenie zawiedzie. Nie „powinna" — musi, bo cena jest calodzienna.

BEZ PYTESTA, bez sieci, bez przegladarki. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_oslona_polaczenia.py
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
LINIE = ZRODLO.splitlines()


def cialo(nazwa):
    fn = next(n for n in ast.walk(DRZEWO)
              if isinstance(n, ast.FunctionDef) and n.name == nazwa)
    return fn, "\n".join(LINIE[fn.lineno - 1:fn.end_lineno])


FN, CIALO = cialo("podlacz_sie")

print("=== 1. KAZDY `start()` MA SWOJ `stop()` PRZY AWARII ===")
# Ze SKLADNI, nie z liczenia napisow: pytamy, ile razy funkcja tworzy
# instancje Playwrighta i ile z tych miejsc potrafi ja zatrzymac.
starty = [n.lineno for n in ast.walk(FN)
          if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
          and n.func.attr == "start"]
stopy = [n.lineno for n in ast.walk(FN)
         if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
         and n.func.attr == "stop"]
# TRZY GALEZIE, NIE DWIE — i tego wlasnie nie widzialem, czytajac recznie.
# Pierwsza wersja tego sprawdzenia zakladala dwie i oblala; dopiero wtedy
# wyszlo, ze trzecia (bezglowa, z plikiem sesji) przeciekala tak samo.
sprawdz("funkcja tworzy Playwrighta w trzech galeziach", len(starty) == 3, starty)
sprawdz("i kazda umie go zatrzymac", len(stopy) >= 3, stopy)

# KAZDY `connect_over_cdp` stoi w `try`, ktorego `except` wola `stop()`.
polaczenia = [n for n in ast.walk(FN)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
              and n.func.attr == "connect_over_cdp"]
sprawdz("dwa podlaczenia do Chrome'a", len(polaczenia) == 2, len(polaczenia))
# Trzecia galaz nie PODLACZA sie, tylko URUCHAMIA przegladarke — i przecieka
# nawet latwiej, bo `new_context` czyta plik sesji.
uruchomienia = [n for n in ast.walk(FN)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "launch"]
sprawdz("i jedno uruchomienie bezglowe", len(uruchomienia) == 1, len(uruchomienia))

osloniete = 0
for wezel in ast.walk(FN):
    if not isinstance(wezel, ast.Try):
        continue
    ma_polaczenie = any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr == "connect_over_cdp" for n in ast.walk(wezel))
    ma_stop = any(
        isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
        and n.func.attr == "stop"
        for uchwyt in wezel.handlers for n in ast.walk(uchwyt))
    if ma_polaczenie and ma_stop:
        osloniete += 1
sprawdz("OBA podlaczenia sa w `try` z `stop()` w obsludze bledu",
        osloniete == 2, osloniete)

# I to samo dla galezi bezglowej: `launch` oraz `new_context` w jednym `try`.
osloniete_launch = 0
for wezel in ast.walk(FN):
    if not isinstance(wezel, ast.Try):
        continue
    ma_launch = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "launch" for n in ast.walk(wezel))
    ma_kontekst = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                      and n.func.attr == "new_context" for n in ast.walk(wezel))
    ma_stop = any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                  and n.func.attr == "stop"
                  for uchwyt in wezel.handlers for n in ast.walk(uchwyt))
    if ma_launch and ma_kontekst and ma_stop:
        osloniete_launch += 1
sprawdz("uruchomienie i tworzenie kontekstu tez pod jedna oslona",
        osloniete_launch == 1, osloniete_launch)

print()
print("=== 2. GALAZ SERWEROWA NIE JEST JUZ WYJATKIEM ===")
i_serwer = CIALO.index("if config.TRYB_SERWERA and _chrome_odpowiada():")
i_next = CIALO.index("if config.TRYB_SERWERA or not _chrome_odpowiada():")
galaz = CIALO[i_serwer:i_next]
sprawdz("ma wlasne `try`", "try:" in galaz, galaz[:200])
sprawdz("i zatrzymuje Playwrighta przy bledzie", "p.stop()" in galaz, galaz[-260:])
# WYJATEK LECI DALEJ. Polkniecie zamienialoby awarie polaczenia w ciche
# „nie ma przegladarki", czyli w blad bez sladu.
sprawdz("a wyjatek leci dalej, nie jest polykany",
        "raise" in galaz.split("p.stop()")[1][:60],
        galaz.split("p.stop()")[1][:60])

print()
print("=== 3. POWOD ZAPISANY PRZY KODZIE ===")
# Ta wada juz raz kosztowala cala dobe; nastepny czytelnik ma wiedziec, czemu
# te trzy linijki tu stoja, zanim je uprosci.
sprawdz("kod tlumaczy, co sie stalo o 00:30",
        "reszte doby" in galaz or "Playwright Sync API" in galaz, galaz[:400])

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
