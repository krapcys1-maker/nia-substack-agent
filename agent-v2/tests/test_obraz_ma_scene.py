# -*- coding: utf-8 -*-
"""Pusty pokoj to nie scena, a drugi obraz nie powtarza pierwszego.

## Skad ten plik

9 wrzesnia 2026, artykul 0028. Oba obrazy wyszly jako puste wnetrza: biurko,
krzeslo, monitor, pomaranczowy kabel, nikogo. Byly poprawne wobec palety
i kompozycji i byly martwe. Drugi tak bardzo przypominal pierwszy, ze dalo sie
je zamienic miejscami i nikt by nie zauwazyl.

Dwie przyczyny, obie w kodzie, obie policzalne:

  1. `grafika_srodek` dostawala TRZY AKAPITY (`okolica`), podczas gdy okladka
     dostawala caly artykul. Model nie wiedzial, o czym jest tekst.
  2. Nic nie mowilo drugiemu obrazowi, co juz pokazala okladka. Dwa niezalezne
     wywolania na tym samym artykule zbiegly sie do tej samej sceny.

Trzecia przyczyna byla w brief'ie: nigdzie nie stalo, ze na obrazie ma sie coc
DZIAC. „Scena" bez czlowieka i bez ruchu to zdjecie mebli.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_obraz_ma_scene.py
"""
import inspect
import io
import sys

sys.path.insert(0, "agent-v2")
import stages  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


BRIEF = " ".join(io.open("agent-v2/prompts/grafika.md", encoding="utf-8").read().split())
ST = io.open("agent-v2/stages.py", encoding="utf-8").read()
PULA = io.open("agent-v2/artykul_z_puli.py", encoding="utf-8").read()

print("=== 1. BRIEF ZADA, ZEBY COS SIE DZIALO ===")
sprawdz("pusty pokoj nazwany wprost", "An empty room is not a scene" in BRIEF)
sprawdz("wymagany czlowiek albo widoczne dzialanie",
        "a person, or unmistakable evidence of an action in progress" in BRIEF)
sprawdz("test, ktory model ma sobie zadac",
        "what happens two seconds later" in BRIEF)
sprawdz("puste wnetrze to tlo, nie temat",
        "these are backgrounds, never the subject" in BRIEF)

print()
print("=== 2. DRUGI OBRAZ WIE, CO POKAZALA OKLADKA ===")
sprawdz("brief ma miejsce na opis okladki", "{juz_pokazane}" in BRIEF)
sprawdz("i naglowek, ktory mowi po co", "Do not draw the same picture twice" in BRIEF)
sprawdz("`grafika_srodek` przyjmuje `unikaj`",
        "unikaj" in inspect.signature(stages.grafika_srodek).parameters)
sprawdz("sciezka artykulu przekazuje temat okladki",
        'unikaj=str((_okladka or {}).get("subject")' in PULA)
sprawdz("i bierze go z wyniku okladki, nie zgaduje",
        "_okladka = stages.grafika(" in PULA)

print()
print("=== 3. OBA WYWOLANIA WYPELNIAJA POLE — INACZEJ KEYERROR ===")
# `_prompt` uzywa `.format(**pola)`. Placeholder bez wartosci wywala CALY etap
# grafiki, a nie tylko psuje opis.
sprawdz("okladka podaje `juz_pokazane`",
        ST.count("juz_pokazane=") >= 2, ST.count("juz_pokazane="))
# GRANICE FUNKCJI ZE SKLADNI, nie z odleglosci w znakach. Pierwsza wersja
# ciela `ST[j:j+4000]` i nie siegala do wywolania, bo docstring
# `grafika_srodek` ma ponad piec tysiecy znakow.
import ast as _ast  # noqa: E402
_drzewo = _ast.parse(ST)
_linie = ST.splitlines()


def _cialo(nazwa):
    fn = next(n for n in _ast.walk(_drzewo)
              if isinstance(n, _ast.FunctionDef) and n.name == nazwa)
    return "\n".join(_linie[fn.lineno - 1:fn.end_lineno])


sprawdz("okladka ma je w swoim ciele", "juz_pokazane=" in _cialo("grafika"))
sprawdz("srodek ma je w swoim ciele", "juz_pokazane=" in _cialo("grafika_srodek"))

print()
print("=== 4. SRODEK DOSTAJE CALY ARTYKUL, NIE TRZY AKAPITY ===")
sprawdz("caly tekst idzie do briefu", 'draft.get("body", ""))[:5000]' in ST)
sprawdz("a fragment jest WSKAZANY, nie jedyny",
        "THE PASSAGE THIS IMAGE SITS BESIDE" in ST)
# KONTRDOWOD: gdyby ktos wrocil do samej okolicy, obraz znowu przestalby
# wiedziec, o czym jest artykul.
sprawdz("sama `okolica` nie jest juz calym cialem briefu",
        "body=okolica[:6000]" not in ST)

print()
print("=== 5. KARTRIDZ: KTOS JEST W KADRZE ===")
OKL = " ".join(io.open("presety/nia-unfiltered/prompty/okladka.md",
                       encoding="utf-8").read().split())
sprawdz("ktos jest prawie na kazdym obrazie",
        "Somebody is in almost every image" in OKL)
sprawdz("brak ludzi to wyjatek wymagajacy powodu",
        "needs a reason far better than" in OKL)
sprawdz("gdy NIA nie pasuje, wchodzi bohater historii",
        "put whoever the story is about there instead" in OKL)
# KONTRDOWOD: stara zgoda na obraz bez niej nie moze wrocic milczkiem.
sprawdz("stare `does not have to be in every cover` zniklo",
        "does not have to be in every cover" not in OKL)

print()
print("=== 6. LICZBA OBRAZOW SIE NIE ZMIENILA ===")
# Wlasciciel zapytal wprost, czy generujemy piec i wyrzucamy trzy. Nie.
# Dwa wywolania na artykul, po 0,20 USD, bez odrzucania.
import config  # noqa: E402
sprawdz("dwa obrazy na artykul", int(config.OBRAZY_NA_ARTYKUL) == 2,
        config.OBRAZY_NA_ARTYKUL)
sprawdz("i dokladnie dwa wywolania w sciezce artykulu",
        PULA.count("stages.grafika(") == 1 and PULA.count("stages.grafika_srodek(") == 1,
        (PULA.count("stages.grafika("), PULA.count("stages.grafika_srodek(")))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
