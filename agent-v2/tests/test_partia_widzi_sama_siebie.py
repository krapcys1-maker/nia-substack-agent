# -*- coding: utf-8 -*-
"""Druga notka partii widzi pierwsza, jeszcze zanim ta wyjdzie.

## Pomiar, ktory to wywolal

10 wrzesnia 2026, produkcja, partia dwoch notek. Tematy pilnowane i naprawde
rozne — odleglosc 0,029. A uderzenie drugie w obu:

    Apparently even policing a woman's pregnancy now needs a machine
    ghostwriter, because human intrusion wasn't efficient enough.

    Apparently even genomics gets a velvet rope: academics enter freely, while
    commercial users are escorted toward Google Cloud.

Ta sama rama retoryczna dwa razy pod rzad. Straznik powtorek pilnuje TEMATU,
wiec przepuscil to bez mrugniecia — powtorka przeniosla sie na sklad zdania.

## Dlaczego kod tego nie widzial

`context.recent_published` bierze sie z dziennika, czyli z notek, ktore JUZ
WYSZLY. Partia powstaje w calosci przed pierwsza publikacja. Druga notka nie
miala jak zobaczyc pierwszej: w chwili jej pisania pierwsza nie istniala
nigdzie poza pamiecia procesu.

To ten sam ksztalt wady, co temat powtarzany w jednej partii — tam poprawilem
wybor materialu, tu trzeba bylo pokazac modelowi wlasny tekst sprzed minuty.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_partia_widzi_sama_siebie.py
"""
import inspect
import json
import sys
from unittest.mock import patch

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


print("=== 1. PODPIS PRZYJMUJE TO, CO NAPISANO PRZED CHWILA ===")
sygnatura = inspect.signature(p.short_form)
sprawdz("short_form ma parametr", "napisane_teraz" in sygnatura.parameters)
sprawdz("i domyslnie jest pusty",
        sygnatura.parameters["napisane_teraz"].default == ())

print()
print("=== 2. TEKST TRAFIA DO PROMPTU NASTEPNEJ NOTKI ===")
# Atrapa modelu: zapisuje KAZDY prompt i oddaje inny tekst za kazdym razem.
prompty = []
odpowiedzi = [
    '{"text":"Apparently even the first note found a frame.\\nSecond beat.\\n'
    'Third beat aimed at somebody.","topic":"a","memory":""}',
    '{"text":"A different opening entirely.\\nSecond beat.\\n'
    'Third beat aimed at somebody.","topic":"b","memory":""}',
]


def _atrapa(role, system, user, **kw):
    prompty.append(user)
    return odpowiedzi[min(len(prompty) - 1, len(odpowiedzi) - 1)]


class _Kursor:
    def execute(self, *a, **k):
        return self

    def fetchone(self, *a, **k):
        return None

    def fetchall(self, *a, **k):
        return []


class _Baza:
    def cursor(self):
        return _Kursor()

    def execute(self, *a, **k):
        return _Kursor()

    def commit(self):
        pass


with patch.object(p.llm, "call", _atrapa), \
     patch.object(p, "_fakt_z_banku", lambda: None), \
     patch.object(p, "_swiat", lambda *a, **k: {}), \
     patch.object(p, "memory", lambda: []), \
     patch.object(p, "memory_state", lambda: {"intro": True}), \
     patch.object(p, "statistics", lambda *a, **k: {}), \
     patch.object(p.preset, "_zapisz_atomowo", lambda *a, **k: None), \
     patch.object(p.config, "DRY_RUN", False):
    wynik = p.notes(_Baza(), None, ile=2)

sprawdz("obie notki powstaly", len(wynik) == 2, len(wynik))
sprawdz("model zostal zapytany dwa razy", len(prompty) == 2, len(prompty))

if len(prompty) == 2:
    # OD `{"material"`, NIE OD PIERWSZEGO NAWIASU. Instrukcja pokazuje modelowi
    # wzor odpowiedzi — `JSON: {"text":...}` — i to on stoi w tekscie pierwszy.
    def kontekst(prompt):
        return json.loads(prompt[prompt.rindex('{"material"'):])

    pierwszy = kontekst(prompty[0])
    drugi = kontekst(prompty[1])
    sprawdz("pierwsza notka nie widzi niczego z partii",
            pierwszy.get("written_moments_ago") == [],
            pierwszy.get("written_moments_ago"))
    widziane = drugi.get("written_moments_ago") or []
    sprawdz("DRUGA WIDZI PIERWSZA", len(widziane) == 1, widziane)
    sprawdz("i widzi jej PELNY tekst, nie temat",
            bool(widziane) and "Apparently even the first note" in widziane[0],
            (widziane or [""])[0][:60])

print()
print("=== 3. INSTRUKCJA MOWI, CZEGO NIE POWTARZAC ===")
# Sam tekst obok nie wystarczy: bez tego zdania model traktuje go jak
# „moja ciaglosc", czyli jako zachete, a nie ostrzezenie.
INSTR = prompty[1] if len(prompty) > 1 else ""
sprawdz("prompt nazywa te teksty po imieniu",
        "written_moments_ago holds pieces written in this same batch" in INSTR)
sprawdz("i mowi, ze chodzi o SKLAD zdania, nie o temat",
        "reuse their SENTENCE SHAPES" in INSTR)
sprawdz("z tym konkretnym przykladem, ktory zawiodl",
        "Apparently even" in INSTR)
sprawdz("i rozciaga regule poza otwarcie",
        "any repeated frame, comparison or closing move" in INSTR)

print()
print("=== 4. STARA CIAGLOSC NIE ZOSTALA ZASTAPIONA ===")
# Kontrdowod: to sa DWIE rozne rzeczy. Dziennik to ciaglosc glosu i wolno
# z niej korzystac; partia to ostrzezenie o sasiedztwie.
sprawdz("dziennik nadal idzie do promptu", "recent_published" in INSTR)
sprawdz("i nadal jest opisany jako WLASNA ciaglosc",
        "YOUR OWN continuity" in INSTR)

print()
print("=== 5. PUSTA ODPOWIEDZ NIE TRAFIA NA LISTE ===")
zrodlo = inspect.getsource(p.notes)
sprawdz("dopisujemy tylko tekst, ktory istnieje",
        'if output.get("text"):' in zrodlo)
sprawdz("lista jest przycinana, zeby prompt nie puchl",
        "[-4:]" in inspect.getsource(p.short_form))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
