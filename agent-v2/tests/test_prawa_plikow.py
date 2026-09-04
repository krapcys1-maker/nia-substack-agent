# -*- coding: utf-8 -*-
"""Pliki z cudzymi danymi maja byc czytelne TYLKO dla wlasciciela — od poczatku.

## Po co ten plik istnieje

Dwa pliki w `data/` niosa material, ktorego nie wolno pokazac nikomu innemu
na maszynie:

    kopie/subskrybenci-*.csv   cudze adresy e-mail
    storage-state.json         ciastko sesji, czyli prawo do publikowania

Domyslne prawa na serwerze to 0644 albo 0664 — czytelne dla KAZDEGO konta.

W calym repozytorium byl DOKLADNIE JEDEN `chmod`, przy kopii subskrybentow,
i stal LINIJKE PO `cel.write_text(...)`:

    cel.write_text(tekst, encoding="utf-8")
    cel.chmod(0o600)

Miedzy jednym a drugim istnialo okno, w ktorym plik z cudzymi adresami byl
czytelny dla wszystkich. Komentarz przy tym `chmod` sam nazywal te klase
(„ta sama, co sesja przegladarki zapisana z 0644") — i zamykal jej polowe.
Sesja przegladarki nie miala `chmod` wcale.

## Czego pilnuje

1. `otworz_tylko_dla_wlasciciela` NIE UZYWA `write_text`/`open` — czyli okna
   nie ma z konstrukcji, a nie z ostroznosci. Sprawdzane po AST.
2. KAZDY zapis sesji w `browser.py` ma obok ustawienie praw. Liczba wywolan
   `config.tylko_dla_wlasciciela(SESSION_FILE)` rowna liczbie zapisow.
3. Kopia subskrybentow idzie przez `otworz_tylko_dla_wlasciciela`, a nie przez
   `write_text`.
4. Na systemie POSIX plik naprawde dostaje 0600. Na Windows prawa POSIX nie
   istnieja i test to MOWI, zamiast udawac, ze sprawdzil.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_prawa_plikow.py
"""
import ast
import os
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import config  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


print("=== 1. ZAPIS BEZ OKNA: `os.open` Z PRAWAMI, NIE `write_text` ===")
import inspect  # noqa: E402
import textwrap  # noqa: E402

_zrodlo = textwrap.dedent(inspect.getsource(config.otworz_tylko_dla_wlasciciela))
_drzewo = ast.parse(_zrodlo)
_wolane = {getattr(w.func, "attr", None) or getattr(w.func, "id", None)
           for w in ast.walk(_drzewo) if isinstance(w, ast.Call)}
sprawdz("uzywa `os.open`", "open" in _wolane, sorted(x for x in _wolane if x))
sprawdz("i NIE uzywa `write_text`", "write_text" not in _wolane)
_liczby = [w.value for w in ast.walk(_drzewo)
           if isinstance(w, ast.Constant) and isinstance(w.value, int)
           and not isinstance(w.value, bool)]
sprawdz("prawa 0600 podane przy tworzeniu", 0o600 in _liczby,
        [oct(x) for x in _liczby])

print()
print("=== 2. KAZDY ZAPIS SESJI USTAWIA PRAWA ===")
_br = pathlib.Path("agent-v2/browser.py").read_text(encoding="utf-8")
_zapisow = _br.count("context.storage_state(path=str(SESSION_FILE))")
_praw = _br.count("config.tylko_dla_wlasciciela(SESSION_FILE)")
sprawdz("zapisow sesji jest wiecej niz zero", _zapisow > 0, _zapisow)
sprawdz("i kazdy ma obok ustawienie praw (%d/%d)" % (_praw, _zapisow),
        _praw == _zapisow, (_praw, _zapisow))

print()
print("=== 3. KOPIA SUBSKRYBENTOW NIE IDZIE PRZEZ `write_text` ===")
_ks = pathlib.Path("agent-v2/kopia_subskrybentow.py").read_text(encoding="utf-8")
sprawdz("uzywa `otworz_tylko_dla_wlasciciela`",
        "config.otworz_tylko_dla_wlasciciela" in _ks)
# PO DRZEWIE SKLADNI, NIE PO TEKSCIE. Pierwsza wersja szukala napisu
# `cel.write_text(` i oblala — bo komentarz nad poprawka CYTUJE stary kod
# („BYLO: `cel.write_text(...)`"), i ma go cytowac, bo to jest opis wady.
# Ta sama pomylka, ktora zastapil straznik wzorcow w `test_jezyk_bramek.py`.
_wolania = {getattr(w.func, "attr", None)
            for w in ast.walk(ast.parse(_ks)) if isinstance(w, ast.Call)}
sprawdz("i zaden zapis nie idzie przez `write_text`",
        "write_text" not in _wolania,
        sorted(x for x in _wolania if x))

print()
print("=== 4. PRAWA NA ZYWYM PLIKU ===")
_kat = pathlib.Path(tempfile.mkdtemp(prefix="prawa-"))
try:
    _plik = _kat / "proba.csv"
    with config.otworz_tylko_dla_wlasciciela(_plik) as f:
        f.write("Email,Type\na@b.c,free\n")
    sprawdz("plik ma tresc",
            _plik.read_text(encoding="utf-8").startswith("Email,"))
    if os.name == "posix":
        _tryb = _plik.stat().st_mode & 0o777
        sprawdz("i prawa 0600", _tryb == 0o600, oct(_tryb))
    else:
        # NIE UDAJEMY, ZE SPRAWDZILISMY. Windows nie ma praw POSIX i `stat`
        # zwraca tu 0666 niezaleznie od tego, co podalismy — asercja na tej
        # liczbie byla by asercja o systemie, nie o kodzie.
        print("  ..    prawa POSIX: nie ma ich na tym systemie (%s) —"
              " sekcja 1 sprawdza to po kodzie" % os.name)
finally:
    shutil.rmtree(_kat, ignore_errors=True)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
