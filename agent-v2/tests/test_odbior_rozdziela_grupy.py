# -*- coding: utf-8 -*-
"""Pomiar odbioru albo rozdziela notki, albo mowi, ze ich nie rozdziela.

## Dwie wady, ktore ten plik pilnuje

PIERWSZA — `NameError`, odtworzony uruchomieniem 5 wrzesnia 2026.
`import statystyki` stal w zasiegu LOKALNYM funkcji `co_zadzialalo`, a
`statystyki._liczba` wola `_tabela_odbioru`, funkcja obok. Wyzwalaczem sa
POMIARY CZYTELNIKOW: dopoki `najnowsze_per_pozycja` oddaje pustke,
`co_zadzialalo` konczy na wczesniejszym `return` i nikt tego nie widzi.
Pierwsza notka z polubieniem wywracala ranking banku, a `posortuj_bank`
lapal wyjatek jako „nieudany ranking" i szedl dalej ze stara kolejnoscia —
wiec sedzia banku milkl dokladnie wtedy, gdy zaczynal byc cos wart.

DRUGA — te same notki po obu stronach. Stalo `posort[:ile]` i `posort[-ile:]`,
wiec przy liczbie notek nie wiekszej niz `ile` oba wycinki byly cala lista.
Odtworzone: cztery notki, domyslne `ile=6`, te same cztery wiersze pod
„THESE LANDED" i pod „THESE DID NOT". To gorsze niz brak pomiaru — pusty
zbior niczego nie twierdzi, a ten twierdzil dwie rzeczy naraz.

Sama rozlacznosc nie wystarczyla: przy wynikach 6, 4, 4, 2 podzial na pol
stawial dwie notki z TYM SAMYM wynikiem po przeciwnych stronach.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_odbior_rozdziela_grupy.py
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import config  # noqa: E402

config.uzyj_katalogu_danych(pathlib.Path(tempfile.mkdtemp()))
import stages       # noqa: E402
import statystyki   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


def ustaw(pomiary):
    statystyki.najnowsze_per_pozycja = lambda co: {
        "n%d" % i: {"tekst": "Notka %d" % i, "polubienia": p, "odpowiedzi": o,
                    "wyswietlenia": 100, "kiedy": "2026-09-01"}
        for i, (p, o) in enumerate(pomiary)}


def wiersze(tekst, naglowek):
    if naglowek not in tekst:
        return []
    ogon = tekst.split(naglowek, 1)[1]
    out = []
    for l in ogon.splitlines():
        if not l.strip():
            if out:
                break
            continue
        if l.endswith(":"):
            break
        out.append(l.strip())
    return out


print("=== 1. POMIARY CZYTELNIKOW NIE WYWRACAJA RANKINGU ===")
ustaw([(9, 3), (8, 2), (1, 0), (0, 0)])
try:
    tekst = stages.co_zadzialalo(6)
    sprawdz("co_zadzialalo przezylo niepuste pomiary", True)
except Exception as exc:                                     # noqa: BLE001
    tekst = ""
    sprawdz("co_zadzialalo przezylo niepuste pomiary", False,
            "%s: %s" % (type(exc).__name__, exc))
# KONTRDOWOD: import MUSI byc widoczny dla obu funkcji, nie tylko dla jednej.
zrodlo = pathlib.Path("agent-v2/stages.py").read_text(encoding="utf-8")
_glowa = zrodlo[:zrodlo.index("def ")]
sprawdz("import statystyki stoi w zasiegu modulu",
        "\nimport statystyki" in _glowa)
sprawdz("i nie ma juz kopii w zasiegu lokalnym",
        "        import statystyki" not in zrodlo)

print()
print("=== 2. GRUPY SA ROZLACZNE ===")
gora = wiersze(tekst, "THESE LANDED:")
dol = wiersze(tekst, "THESE DID NOT:")
sprawdz("obie grupy niepuste", bool(gora) and bool(dol), (len(gora), len(dol)))
sprawdz("zadna notka nie jest w obu", not (set(gora) & set(dol)),
        sorted(set(gora) & set(dol)))
sprawdz("razem nie wiecej niz zmierzonych", len(gora) + len(dol) <= 4,
        (len(gora), len(dol)))

print()
print("=== 3. REMIS NA GRANICY ZWEZA GRUPY, NIE ROZSTRZYGA GO ===")
# 6, 4, 4, 2: podzial na pol stawialby dwie czworki po przeciwnych stronach.
ustaw([(3, 1), (1, 1), (4, 0), (2, 0)])
t2 = stages.co_zadzialalo(6)
g2, d2 = wiersze(t2, "THESE LANDED:"), wiersze(t2, "THESE DID NOT:")
sprawdz("grupy zwezone do jednej pozycji", len(g2) == 1 and len(d2) == 1,
        (len(g2), len(d2)))
sprawdz("po gornej stronie stoi najlepsza", "3 likes, 1 replies" in g2[0], g2)
sprawdz("po dolnej najslabsza", "2 likes, 0 replies" in d2[0], d2)
sprawdz("zadna notka z remisem nie zostala osadzona",
        not any("4 likes" in w or "1 likes" in w for w in g2 + d2), g2 + d2)

print()
print("=== 4. BRAK ROZDZIELENIA MOWI O SOBIE WPROST ===")
ustaw([(0, 0), (0, 0), (0, 0), (0, 0)])
t3 = stages.co_zadzialalo(6)
sprawdz("nie powstaja dwie grupy z szumu", "THESE LANDED" not in t3, t3[:60])
sprawdz("i tekst mowi, ze pomiar nie rozdziela",
        "do not separate" in t3, t3[:80])
# KONTRDOWOD: to NIE moze byc ta sama odpowiedz, co przy braku pomiarow —
# „nie ma pomiarow" i „pomiary nie rozrozniaja" to dwa rozne stany konta.
sprawdz("i to inny komunikat niz brak pomiarow",
        "(no measurements available yet)" != t3)

print()
print("=== 5. WYRAZNA ROZNICA NADAL DAJE PELNE GRUPY ===")
ustaw([(9, 3), (8, 2), (7, 2), (1, 0), (0, 0), (0, 1)])
t4 = stages.co_zadzialalo(6)
g4, d4 = wiersze(t4, "THESE LANDED:"), wiersze(t4, "THESE DID NOT:")
sprawdz("przy szesciu notkach po trzy", len(g4) == 3 and len(d4) == 3,
        (len(g4), len(d4)))
sprawdz("nadal rozlaczne", not (set(g4) & set(d4)))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
