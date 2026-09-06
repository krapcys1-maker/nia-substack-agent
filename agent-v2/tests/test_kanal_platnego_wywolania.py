# -*- coding: utf-8 -*-
"""KAZDE platne wywolanie ma trafiac do jakiegos kanalu — i to sprawdza kod, nie ja.

## Po co

`purpose` w tabeli `calls` mowi, CO robil model („comment", „factcheck"), a nie
KOMU to sluzylo. Kolumna `akcja` (patrz `db.AKCJA` i `db.kanal`) mowi to drugie.
Kolumna jest jednak warta tyle, ile jej ZASIEG: 2 wrzesnia 2026 oprzyrzadowanie
bylo wpiete w TRZECH miejscach przy 28 call-site'ach wolajacych platny model.
Zmierzone na siedmiu dobach produkcji (26.08-02.09.2026, 16,9656 USD): 8,49 USD
— 50,1 procent rachunku — nie moglo dostac kanalu ZADNA droga, a kanal pewny,
czyli na kazdej sciezce wywolan, mialo tylko 3,62 USD (21,4 procent). Miara
„na dolara" bez mianownika nie istnieje.

Ten plik jest straznikiem ZASIEGU. Sprawdza, czy kazde miejsce, ktore placi,
lezy na sciezce z kanalem — a sekcja 4 dodatkowo przechodzi cala droge od
dekoratora do kolumny `akcja`, bo dekorator wpisany w zrodle i dekorator
naprawde zalozony na obiekt funkcji to dwie rozne rzeczy.

## Jak

Z DRZEWA SKLADNI (`ast`), nie z `grep`, bo grep znajduje napis, a nie
osiagalnosc. Dla kazdego modulu produkcyjnego (`agent-v2/*.py`) zbieramy:

  * call-site'y `llm.call` / `llm.obraz` / `llm.ratuj_json`;
  * dekoratory `@_na_kanal("...")` / `@stages._na_kanal("...")`;
  * bloki `with db.kanal("...")`;
  * krawedzie wywolan (`stages.write(...)`, `wybierz_fakt(...)`) rozwiazywane
    po module i po zakresie leksykalnym, nie po samej nazwie.

Potem najmniejszy punkt staly: funkcja MA KANAL, gdy ma dekorator albo gdy
KAZDE jej wywolanie w kodzie stoi w kanale (leksykalnie albo przez wolajacego,
ktory sam ma kanal). Warunek jest uniwersalny, wiec cykl bez kanalu i sciezka
zapomniana wychodza jako porazka, a nie jako cisza.

## CZEGO TEN TEST NIE LAPIE — czytaj, zanim mu uwierzysz

1. WYWOLANIE PRZEZ ZMIENNA. `f = stages.write; f(...)`, `getattr(stages, n)`,
   slownik funkcji, `functools.partial` — krawedz nie powstaje. Jedyne takie
   miejsce dzis (`browser.restackuj_w_kanale(ile, lambda n: ocen_restack(...))`)
   jest bezpieczne, bo `ocen_restack` ma WLASNY dekorator, a nie zapozyczony
   kanal wolajacego. To jest powod, dla ktorego etapy dostaly dekoratory
   zamiast nawiasow u wolajacych wszedzie, gdzie sie dalo.
2. LENIWY WYNIK. Funkcja bez dekoratora, ktora ODDAJE generator zbudowany
   w `with db.kanal(...)`, straci znacznik, bo blok konczy sie przed pierwszym
   `next()`. Dlatego `_na_kanal` ma osobna galaz z `yield from` — ale zwykly
   `with` u wolajacego takiej ochrony nie ma. Dzis zaden platny etap nie jest
   generatorem (sekcja 2 to sprawdza).
3. WATKI I ASYNC. `db.AKCJA` to globalna zmienna modulu, nie `ContextVar`.
   Dwa rownolegle przebiegi w JEDNYM procesie wymieszaly by znaczniki. Dzis
   w `agent-v2/*.py` nie ma ani `threading`, ani `asyncio` (sekcja 2).
4. KOD SPOZA `agent-v2/*.py`. Analiza osiagalnosci obejmuje moduly z pierwszego
   poziomu. Sekcja 6 sprawdza osobno, ze glebiej (`pomiary/`,
   `dokumentacja-zrodla/`) nie ma ANI JEDNEGO platnego call-site'a — wiec
   dziura jest zamknieta pytaniem, nie zalozeniem.
5. `if __name__ == "__main__"`. Wywolania z bloku startowego skryptu nie licza
   sie jako „wolajacy bez kanalu" (inaczej kazdy skrypt uruchamiany recznie
   psulby wynik). Sekcja 7 wypisuje te wejscia, zeby nie byly niewidzialne.
6. CZY NAZWA KANALU JEST PRAWDZIWA. Test pilnuje, ze kanal JEST i ze pochodzi
   z zamknietej listy. Nie umie sprawdzic, czy `komentarz@notka` naprawde
   opisuje komentarz pod notka — to zostaje na czytaniu kodu.

BEZ PYTESTA, zero sieci, zero platnych wywolan, produkcja nietknieta.
Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_kanal_platnego_wywolania.py
"""
import ast
import contextlib
import hashlib
import io
import pathlib
import shutil
import sqlite3
import sys
import tempfile
import types

sys.path.insert(0, "agent-v2")
import config      # noqa: E402

# BAZA W KATALOGU TYMCZASOWYM, USTAWIONA PRZED `import db`. Sekcja zywa pisze
# prawdziwe wiersze do `calls`; produkcja ma tego nie zobaczyc.
_KAT = pathlib.Path(tempfile.mkdtemp(prefix="kanal-test-"))
config.DB_PATH = _KAT / "kanal.db"
import db          # noqa: E402

KOD = pathlib.Path("agent-v2")
PLATNE = {"call", "obraz", "ratuj_json"}


def odcisk_katalogu(katalog):
    """Jeden SHA z calego drzewa: nazwy plikow i ich tresc."""
    h = hashlib.sha256()
    for p in sorted(pathlib.Path(katalog).rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(katalog)).replace("\\", "/").encode())
            h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()[:16]


# ODCISK BIERZEMY TERAZ, przed czymkolwiek — inaczej mierzylby skutek testu.
PRZED_DATA = odcisk_katalogu(config.AGENT_DIR / "data")

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# ==========================================================================
# PRZYRZAD: analiza drzewa skladni
# ==========================================================================
class _Skan(ast.NodeVisitor):
    def __init__(self, modul):
        self.modul = modul
        self.stos = []
        self.kanaly = []          # aktywne kanaly (dekorator + `with`)
        self.w_main = False
        self.funkcje = {}
        self.platne = []
        self.krawedzie = []

    def qual(self):
        return ("%s.%s" % (self.modul, ".".join(self.stos))
                if self.stos else self.modul)

    def _fun(self, node):
        self.stos.append(node.name)
        q = self.qual()
        kanal = None
        for d in node.decorator_list:
            if (isinstance(d, ast.Call)
                    and getattr(d.func, "attr", getattr(d.func, "id", "")) == "_na_kanal"):
                kanal = (str(d.args[0].value)
                         if d.args and isinstance(d.args[0], ast.Constant) else "?")
        self.funkcje[q] = {
            "modul": self.modul, "nazwa": node.name, "linia": node.lineno,
            "kanal": kanal, "platne": [],
            "generator": any(isinstance(x, (ast.Yield, ast.YieldFrom))
                             for x in ast.walk(node)),
        }
        if kanal:
            self.kanaly.append(kanal)
        self.generic_visit(node)
        if kanal:
            self.kanaly.pop()
        self.stos.pop()

    visit_FunctionDef = _fun
    visit_AsyncFunctionDef = _fun

    def visit_With(self, node):
        nowe = []
        for it in node.items:
            e = it.context_expr
            if (isinstance(e, ast.Call) and isinstance(e.func, ast.Attribute)
                    and e.func.attr == "kanal"
                    and isinstance(e.func.value, ast.Name)
                    and e.func.value.id in ("db", "_db")):
                nowe.append(str(e.args[0].value)
                            if e.args and isinstance(e.args[0], ast.Constant)
                            else "?")
        self.kanaly.extend(nowe)
        self.generic_visit(node)
        for _ in nowe:
            self.kanaly.pop()

    visit_AsyncWith = visit_With

    def visit_If(self, node):
        tekst = ast.unparse(node.test)
        if "__name__" in tekst and "__main__" in tekst:
            byl, self.w_main = self.w_main, True
            self.generic_visit(node)
            self.w_main = byl
        else:
            self.generic_visit(node)

    def visit_Call(self, node):
        f, baza, nazwa = node.func, None, None
        if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
            baza, nazwa = f.value.id, f.attr
        elif isinstance(f, ast.Name):
            nazwa = f.id
        if nazwa in PLATNE and baza in ("llm", "_llm"):
            cel = ""
            if node.args and isinstance(node.args[0], ast.Constant):
                cel = str(node.args[0].value)
            for kw in node.keywords:
                if kw.arg == "purpose" and isinstance(kw.value, ast.Constant):
                    cel = str(kw.value.value)
            wpis = {"modul": self.modul, "linia": node.lineno, "co": nazwa,
                    "purpose": cel or ("obraz" if nazwa == "obraz" else "(zmienna)"),
                    "funkcja": self.qual(), "kanal": list(self.kanaly)}
            self.platne.append(wpis)
            if self.stos:
                self.funkcje[self.qual()]["platne"].append(wpis)
        if nazwa:
            self.krawedzie.append(
                (self.qual() if self.stos else None, nazwa, baza,
                 bool(self.kanaly), self.w_main, node.lineno, self.modul,
                 list(self.stos)))
        self.generic_visit(node)


def analizuj(katalog):
    """Wszystko, czego potrzeba do werdyktu, z jednego przejscia po plikach."""
    pliki = sorted(pathlib.Path(katalog).glob("*.py"))
    nazwy = {p.stem for p in pliki}
    funkcje, platne, krawedzie, aliasy = {}, [], [], {}
    for p in pliki:
        drzewo = ast.parse(p.read_text(encoding="utf-8"))
        a = {}
        for n in ast.walk(drzewo):
            if isinstance(n, ast.Import):
                for al in n.names:
                    if al.name in nazwy:
                        a[al.asname or al.name] = al.name
        aliasy[p.stem] = a
        s = _Skan(p.stem)
        s.visit(drzewo)
        funkcje.update(s.funkcje)
        platne.extend(s.platne)
        krawedzie.extend(s.krawedzie)
    return {"funkcje": funkcje, "platne": platne, "krawedzie": krawedzie,
            "aliasy": aliasy, "moduly": nazwy}


def _rozwiaz(dane, modul, stos, baza, nazwa):
    """Kwalifikowana nazwa wolanej funkcji albo None.

    Bez tego kroku graf klamie: `f.write(...)` na uchwycie pliku wygladalby
    jak wywolanie `stages.write` i wciagnalby pisarza artykulu do czterech
    obcych funkcji.
    """
    if baza is None:
        for i in range(len(stos), -1, -1):
            q = ".".join([modul] + stos[:i] + [nazwa])
            if q in dane["funkcje"]:
                return q
        return None
    m = dane["aliasy"].get(modul, {}).get(baza, baza)
    q = "%s.%s" % (m, nazwa)
    return q if (m in dane["moduly"] and q in dane["funkcje"]) else None


def werdykt(katalog):
    """Dla kazdej funkcji: ma kanal / dziedziczy / martwa / BEZ KANALU."""
    dane = analizuj(katalog)
    wolania = {}
    for (skad, nazwa, baza, w_kanale, w_main, linia, modul, stos) in dane["krawedzie"]:
        cel = _rozwiaz(dane, modul, stos, baza, nazwa)
        if cel is not None:
            wolania.setdefault(cel, []).append((skad, w_kanale, w_main, modul, linia))
    pokryte = {q for q, f in dane["funkcje"].items() if f["kanal"]}
    zmiana = True
    while zmiana:                       # najmniejszy punkt staly
        zmiana = False
        for q in dane["funkcje"]:
            if q in pokryte:
                continue
            zywe = [w for w in wolania.get(q, []) if not w[2]]
            if zywe and all(w[1] or (w[0] is not None and w[0] in pokryte)
                            for w in zywe):
                pokryte.add(q)
                zmiana = True
    stany = {}
    for q in sorted({w["funkcja"] for w in dane["platne"]}):
        f = dane["funkcje"].get(q, {})
        zywe = [w for w in wolania.get(q, []) if not w[2]]
        z_main = [w for w in wolania.get(q, []) if w[2]]
        # KOLEJNOSC ODWROCONA 2026-09-03. Stalo tu sprawdzenie dekoratora
        # PRZED sprawdzeniem, czy ktokolwiek te funkcje wola — wiec funkcja
        # z `@_na_kanal(...)` i zerem wolajacych raportowala sie jako zdrowa.
        #
        # ZNALEZIONE NA `stages.kandydaci_z_fedreg` (etap `fedreg`,
        # deepseek-v4-flash). Zero wywolan w kodzie produkcyjnym — jedyne
        # wywolania sa w `tests/platne/test_fedreg_pelna_sciezka.py` i w liscie
        # oczekiwan tego pliku. Test wypisywal `KANAL:bank` i przechodzil,
        # a `config.MODEL_FOR["fedreg"]` byl ustawieniem bez skutku.
        #
        # To jest dokladnie ta klasa bledu, ktora ten projekt nazywa w
        # DOKTRYNA.md paragraf 12: test zielony nad kodem martwym. Straznik
        # przed nia chroniacy sam ja mial.
        #
        # Teraz brak wolajacych wygrywa z dekoratorem. Dekorator mowi, GDZIE
        # ksiegowac koszt; nie mowi, ze cokolwiek ten koszt ponosi.
        #
        # WARUNEK NIE MOZE PYTAC O `pokryte`. Pierwsza proba poprawki brzmiala
        # `not zywe and q not in pokryte` i nie zmieniala NIC, bo `pokryte`
        # jest ZASIEWANE dekoratorami piec linii wyzej:
        #     pokryte = {q for q, f in dane["funkcje"].items() if f["kanal"]}
        # czyli funkcja z dekoratorem byla w `pokryte` od poczatku i drugi
        # czlon warunku zawsze byl falszem. Poprawka wygladala na zrobiona
        # i nie robila nic — ta sama klasa bledu, ktora ma lapac.
        #
        # Wlasciwe pytanie brzmi: czy cokolwiek ja wola (`zywe`) i czy nie
        # jest recznym wejsciem z `__main__` (`z_main`). Nic wiecej.
        if not zywe and not z_main:
            stan = "MARTWE"
        elif f.get("kanal"):
            stan = "KANAL:%s" % f["kanal"]
        elif q in pokryte:
            stan = "dziedziczy"
        else:
            stan = "BEZ KANALU"
        stany[q] = {"stan": stan, "wolania": zywe, "main": z_main,
                    "purpose": sorted({w["purpose"] for w in f.get("platne", [])}),
                    "generator": f.get("generator"), "kanal": f.get("kanal")}
    return dane, wolania, pokryte, stany


# ==========================================================================
# 1. INWENTARZ: kazdy platny call-site lezy na sciezce z kanalem
# ==========================================================================
# JEDYNE FUNKCJE, KTORYCH NIKT NIE WOLA. Martwy kod nie wydaje pieniedzy, ale
# nie moze byc cicha furtka: lista jest jawna, wiec dopisanie NOWEGO platnego
# etapu „na pozniej" tez obleje ten test i wymusi decyzje o kanale.
BEZ_WOLAJACYCH = {
    "stages.kandydaci_z_fedreg":
        "wyciaga kandydatow z preambuly przepisu (Federal Register). ZERO "
        "wywolan w kodzie produkcyjnym — wola go tylko `tests/platne/"
        "test_fedreg_pelna_sciezka.py`. Sciezka jest napisana, zmierzona "
        "($0,0048 za uzytecznego kandydata wobec $0,0514 za wywolanie "
        "`curiosity`) i NIGDY NIE WPIETA w zaden przebieg. Do decyzji "
        "wlasciciela: wpiac w `run.dzien` obok banku albo skasowac razem "
        "z `korpus_fedreg`, `prompts/fedreg.md` i wpisem w MODEL_FOR.",
    "stages.sprawdz_fakty":
        "szuka faktow do KOMENTARZA; zero wywolan w calym repozytorium "
        "(takze w tests/). Gdy wroci do uzycia, kanal ma ustawic WOLAJACY — "
        "komentarz pod artykulem i pod notka to dwa rozne kanaly.",
}

# ZAMKNIETA LISTA KANALOW. Bez niej `Artykul`, `article` i `artykuly` zylyby
# obok siebie i zadne zapytanie po `akcja` nie zsumowaloby sie do calosci.
KANALY = {
    "artykul": "caly lancuch tekstu: skaut, wykonalnosc, discovery, klasyfikacja,"
               " synteza, warto_pisac, bibliotekarz, pisarz, recenzja, forma,"
               " grafika, sprawdzenie faktow artykulu",
    "notka": "notki dnia razem z ich materialem i sedzia banku",
    "komentarz@artykul": "komentarze pod cudzymi ARTYKULAMI: wybor celow, tekst,"
                         " sprawdzenie faktow, naprawa",
    "komentarz@notka": "to samo pod cudzymi NOTKAMI",
    "odpowiedz": "odpowiedzi pod naszymi wlasnymi tresciami",
    "restack": "ocena, czy podac cudza notke dalej",
    "bank": "uzupelnianie banku kandydatow poza notkami (Federal Register)",
}

print("=== 1. KAZDE PLATNE WYWOLANIE MA KANAL ===")
DANE, WOLANIA, POKRYTE, STANY = werdykt(KOD)
print("    call-site'ow platnych: %d w %d funkcjach, w %d modulach"
      % (len(DANE["platne"]), len(STANY),
         len({w["modul"] for w in DANE["platne"]})))
print()
print("    %-42s %-18s %s" % ("funkcja", "stan", "purpose"))
for q, s in sorted(STANY.items()):
    print("    %-42s %-18s %s" % (q, s["stan"], ", ".join(s["purpose"])))
print()

bez_kanalu = sorted(q for q, s in STANY.items() if s["stan"] == "BEZ KANALU")
for q in bez_kanalu:
    for (skad, wk, wm, modul, linia) in STANY[q]["wolania"]:
        if not (wk or skad in POKRYTE):
            print("       %s <- %s:%d (%s) bez kanalu" % (q, modul, linia, skad))
sprawdz("zaden platny call-site nie jest osiagalny bez kanalu",
        not bez_kanalu, bez_kanalu)

martwe = sorted(q for q, s in STANY.items() if s["stan"] == "MARTWE")
sprawdz("lista funkcji bez wolajacych jest DOKLADNIE ta z opisu",
        martwe == sorted(BEZ_WOLAJACYCH), martwe)
for q in martwe:
    if q in BEZ_WOLAJACYCH:
        print("       (%s: %s)" % (q, BEZ_WOLAJACYCH[q][:70]))

uzyte = {s["kanal"] for s in STANY.values() if s["kanal"]}
uzyte |= {k for w in DANE["platne"] for k in w["kanal"]}
# kanaly z `with db.kanal(...)` w miejscach, ktore same nie sa platne
for p in sorted(KOD.glob("*.py")):
    for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr in ("kanal", "_na_kanal")
                and n.args and isinstance(n.args[0], ast.Constant)):
            uzyte.add(str(n.args[0].value))
obce = sorted(uzyte - set(KANALY))
sprawdz("wszystkie nazwy kanalow pochodza z zamknietej listy", not obce, obce)
print("       uzywane kanaly: %s" % ", ".join(sorted(uzyte)))

# ==========================================================================
# 2. ZALOZENIA, NA KTORYCH STOI TA ANALIZA
# ==========================================================================
print()
print("=== 2. ZALOZENIA PRZYRZADU (bez nich sekcja 1 klamie) ===")
gen = sorted(q for q, s in STANY.items() if s["generator"])
sprawdz("zaden platny etap nie jest generatorem (leniwy wynik gubi znacznik)",
        not gen, gen)

zrodla = {p.name: p.read_text(encoding="utf-8") for p in KOD.glob("*.py")}
watki = sorted(n for n, t in zrodla.items()
               if "import threading" in t or "import asyncio" in t
               or "concurrent.futures" in t)
sprawdz("zaden modul produkcyjny nie odpala watkow (AKCJA to globalna zmienna)",
        watki == ["call_runtime.py"] and "import db" not in zrodla["call_runtime.py"], watki)

sprawdz("`db.record_call` doklada `akcja` sam, a nie u wolajacych",
        'fields.setdefault("akcja", AKCJA)' in zrodla["db.py"])
sprawdz("`_na_kanal` stoi PRZED pierwszym uzyciem w stages.py",
        zrodla["stages.py"].index("def _na_kanal(")
        < zrodla["stages.py"].index('@_na_kanal("'))

# ==========================================================================
# 3. KONTRDOWOD: przyrzad musi UMIEC oblac
# ==========================================================================
print()
print("=== 3. KONTRDOWOD — na zepsutym kodzie ten test MA padac ===")
# Bez tej sekcji zielony wynik znaczylby tylko tyle, ze funkcja `werdykt`
# cokolwiek zwrocila. Kopiujemy drzewo, psujemy jedna rzecz na raz i pytamy.
KOPIA = _KAT / "kopia-kodu"
KOPIA.mkdir()
for p in KOD.glob("*.py"):
    shutil.copy2(p, KOPIA / p.name)

# 3a. zdjety dekorator z etapu wolanego z DWOCH miejsc bez kanalu
oryginal = (KOPIA / "stages.py").read_text(encoding="utf-8")
(KOPIA / "stages.py").write_text(
    oryginal.replace('@_na_kanal("artykul")\ndef write(', "def write(", 1),
    encoding="utf-8")
_, _, _, s3a = werdykt(KOPIA)
sprawdz("zdjecie dekoratora z `write` daje BEZ KANALU",
        s3a.get("stages.write", {}).get("stan") == "BEZ KANALU",
        s3a.get("stages.write", {}).get("stan"))
(KOPIA / "stages.py").write_text(oryginal, encoding="utf-8")

# 3b. nowy platny etap dopisany bez kanalu i wolany ze sciezki artykulu
(KOPIA / "stages.py").write_text(
    oryginal + '\n\ndef nowy_etap(conn, run_id):\n'
    '    return llm.call("nowy", "S", "P", conn=conn, run_id=run_id)\n',
    encoding="utf-8")
run_kopia = (KOPIA / "run.py").read_text(encoding="utf-8")
(KOPIA / "run.py").write_text(
    run_kopia.replace("def main() -> int:",
                      "def main() -> int:\n    stages.nowy_etap(None, 0)", 1),
    encoding="utf-8")
_, _, _, s3b = werdykt(KOPIA)
sprawdz("nowy platny etap wolany bez kanalu daje BEZ KANALU",
        s3b.get("stages.nowy_etap", {}).get("stan") == "BEZ KANALU",
        s3b.get("stages.nowy_etap", {}).get("stan"))

# 3c. ten sam nowy etap, ale NIEWOLANY — ma wyjsc jako MARTWE spoza listy
(KOPIA / "run.py").write_text(run_kopia, encoding="utf-8")
_, _, _, s3c = werdykt(KOPIA)
sprawdz("nowy platny etap bez wolajacych wypada spoza listy BEZ_WOLAJACYCH",
        sorted(q for q, s in s3c.items() if s["stan"] == "MARTWE")
        != sorted(BEZ_WOLAJACYCH))

# 3d. znacznik postawiony obok, a nie wokol wywolania
(KOPIA / "stages.py").write_text(oryginal, encoding="utf-8")
(KOPIA / "run.py").write_text(
    run_kopia.replace(
        '    @stages._na_kanal("komentarz@artykul")\n    def komentarze()',
        "    def komentarze()", 1), encoding="utf-8")
_, _, _, s3d = werdykt(KOPIA)
sprawdz("zdjecie dekoratora z bloku `komentarze` obala kanal `wybierz_cele`",
        s3d.get("stages.wybierz_cele", {}).get("stan") == "BEZ KANALU",
        s3d.get("stages.wybierz_cele", {}).get("stan"))
(KOPIA / "run.py").write_text(run_kopia, encoding="utf-8")

# 3e. The shared article preparation owns the factcheck channel.
# Remove that scope in a disposable source copy and verify the detector notices.
import textwrap
stages_tree = ast.parse(oryginal)
helper = next(n for n in stages_tree.body if isinstance(n, ast.FunctionDef) and n.name == 'przygotuj_artykul_do_publikacji')
scope = next(n for n in helper.body if isinstance(n, ast.With))
lines = oryginal.splitlines(keepends=True)
body = ''.join(lines[scope.lineno:scope.end_lineno])
changed = ''.join(lines[:scope.lineno-1]) + textwrap.dedent(body).replace('\n', '\n    ')
# Preserve the function's base indentation without altering the following functions.
changed = ''.join(lines[:scope.lineno-1]) + ''.join(line[4:] if line.startswith('    ') else line for line in lines[scope.lineno:scope.end_lineno]) + ''.join(lines[scope.end_lineno:])
(KOPIA / 'stages.py').write_text(changed, encoding='utf-8')
_, _, _, s3e = werdykt(KOPIA)
sprawdz('shared preparation without its channel is detected',
        s3e.get('stages.zweryfikuj', {}).get('stan') == 'BEZ KANALU', s3e.get('stages.zweryfikuj'))
(KOPIA / 'stages.py').write_text(oryginal, encoding='utf-8')

_, _, _, s3f = werdykt(KOPIA)
sprawdz("po cofnieciu wszystkich uszkodzen kopia znowu jest czysta",
        not [q for q, s in s3f.items() if s["stan"] == "BEZ KANALU"])

# ==========================================================================
# 4. ZYWO: dekorator naprawde stawia znacznik, ktory naprawde ladzie w bazie
# ==========================================================================
print()
print("=== 4. ZYWO — od dekoratora do kolumny `akcja` ===")
# Sekcje 1-3 czytaja zrodlo. Zrodlo mowi, ze `@_na_kanal` tam stoi; NIE mowi,
# ze obiekt funkcji naprawde jest opakowany i ze znacznik dochodzi do INSERT-a.
# Trzy razy w tym repozytorium test przechodzil na kodzie martwym.
import stages    # noqa: E402

CONN = db.connect()
RUN = db.start_run(CONN, stage="test-kanalu")


def zapisz_probke(purpose):
    """Dokladnie te pola, ktore podaje udana sciezka tekstowa w `llm.call`."""
    db.record_call(conn=CONN, run_id=RUN, provider="atrapa", model="atrapa",
                   purpose=purpose, tokens_in=0, tokens_out=0, cache_hit=0,
                   web_searches=0, cost_usd=0.0, price_verified=0, ok=1, note="")


def przez_opakowanie(funkcja, purpose):
    """Wola PRAWDZIWE opakowanie `_na_kanal`, podmieniajac tylko jego srodek.

    Podmiana idzie przez komorke domkniecia (`f`), wiec wykonuje sie caly
    `with db.kanal(nazwa)` z prawdziwej funkcji — nie jej kopia i nie napis
    ze zrodla. Sygnatury etapow sa rozne, a to podejscie ich nie dotyka.
    """
    wolne = funkcja.__code__.co_freevars
    if "f" not in wolne or funkcja.__closure__ is None:
        return "NIE OPAKOWANA"
    i = wolne.index("f")
    komorka = funkcja.__closure__[i]
    stara = komorka.cell_contents
    komorka.cell_contents = lambda *a, **k: zapisz_probke(purpose)
    try:
        funkcja()
    finally:
        komorka.cell_contents = stara
    w = CONN.execute("SELECT akcja FROM calls WHERE purpose = ?",
                     (purpose,)).fetchone()
    return w["akcja"] if w else "BRAK WIERSZA"


OCZEKIWANE = {
    "artykul": ["scout", "feasibility", "discovery", "classify", "synthesis",
                "warto_pisac", "bibliotekarz", "write", "review", "ocen_forme",
                "grafika"],
    "notka": ["notki_dnia"],
    "odpowiedz": ["wybierz_do_odpowiedzi", "reply_to"],
    "restack": ["ocen_restack"],
    "bank": ["kandydaci_z_fedreg"],
}
for kanal, nazwy in sorted(OCZEKIWANE.items()):
    for nazwa in nazwy:
        widziany = przez_opakowanie(getattr(stages, nazwa), "probka-" + nazwa)
        sprawdz("stages.%-22s ksieguje na %-18s" % (nazwa, kanal),
                widziany == kanal, widziany)

sprawdz("po wyjsciu z bloku znacznik wraca do pustego", db.AKCJA == "")
zapisz_probke("probka-bez-kanalu")
w = CONN.execute("SELECT akcja FROM calls WHERE purpose = 'probka-bez-kanalu'"
                 ).fetchone()
sprawdz("KONTRDOWOD: wywolanie POZA kanalem ma `akcja` puste",
        w and w["akcja"] == "", w["akcja"] if w else "brak")

# ==========================================================================
# 5. ZYWO: prawdziwe `run.dzien()` na atrapach — dwa kanaly komentarzy
# ==========================================================================
print()
print("=== 5. ZYWO — `run.dzien()` ksieguje komentarze na wlasciwe kanaly ===")
# Dekoratory blokow `komentarze` i `dyskusje` siedza WEWNATRZ `dzien()`, wiec
# z zewnatrz nie da sie ich dotknac inaczej niz uruchamiajac przebieg.


def modul(nazwa, **atrybuty):
    m = types.ModuleType(nazwa)
    for k, v in atrybuty.items():
        setattr(m, k, v)
    return m


ZOBACZONE = []          # (etap, akcja) — znacznik w chwili platnego wywolania


def _swiat():
    fake_browser = modul(
        "browser",
        ile_dzis_wystawione=lambda: {},
        dopisz_skutki=lambda: None,
        statystyki_pozycji=lambda: None,
        nieodpowiedziane=lambda: [],
        komentarze_pod_artykulami=lambda: [],
        odpowiedzi_na_nasze_komentarze=lambda: [],
        hosty_tylko_dla_placacych=lambda: set(),
        hosty_gdzie_komentarz_nie_wchodzi=lambda: set(),
        mozna_komentowac=lambda url: True,
        read_pages=lambda urls: [{"url": u, "title": "t", "text": "tresc"}
                                 for u in urls],
        wystaw_komentarz=lambda *a, **k: {"wpisane": True, "wyslane": True},
        wystaw_odpowiedz=lambda *a, **k: {"wpisane": True, "wyslane": True},
        wystaw_odpowiedz_pod_artykulem=lambda *a, **k: {"wyslane": True},
        zapomnij_platny_host=lambda host: None,
        polub_w_kanale=lambda ile, wyslij=False: {"polubione": 0},
        restackuj_w_kanale=lambda ile, ocen, wyslij=False: {"restackowane": 0},
        uchwyt_publikacji=lambda host: "",
        zasubskrybuj=lambda uchwyt, wyslij=False: None,
    )
    fake_kanal = modul(
        "kanal",
        szukaj_nowych=lambda: [
            {"rodzaj": "post", "url": "https://a.example/p/a", "pub": "a.example",
             "tytul": "A", "opis": "o", "komentarze": 3, "reakcje": 9,
             "data": "", "skad": "test"},
            # NOTKA idzie tym samym zrodlem — blok `komentarze` ma ja odsiac,
            # a blok `dyskusje` podniesc. Dwa kanaly z jednej puli.
            {"rodzaj": "notka", "id": 7, "url": "https://substack.com/note/c-7",
             "pub": "b.example", "tytul": "N", "opis": "tresc notki",
             "komentarze": 2, "reakcje": 5, "data": "", "skad": "test"}],
        posty_z_kanalu=lambda ile=25: [],
        notki_z_kanalu=lambda: [],
        zapamietaj_komentarz=lambda post: None,
        _historia=lambda: {},
        _wiek_minut=lambda data: 1000.0,
    )

    def slad(etap):
        def f(*a, **k):
            ZOBACZONE.append((etap, db.AKCJA))
            zapisz_probke("dzien-" + etap + "-" + (db.AKCJA or "puste"))
            if etap == "wybierz_cele":
                return list(a[2])
            return {"candidates": [{"comment": "x", "safe_to_post": True}],
                    "otwarcie": "x", "postawa": "CIEKAWOSC"}
        return f

    fake_stages = modul(
        "stages",
        _na_kanal=stages._na_kanal,          # PRAWDZIWY dekorator
        budzet_dnia=lambda conn: {"notki": 0, "komentarze": 2, "lajki": 0,
                                  "restacki": 0, "follow": 0, "subskrypcje": 0},
        wybierz_cele=slad("wybierz_cele"),
        comment_on=slad("comment_on"),
        zbierz_pytania=lambda czekaja: None,
        wybierz_do_odpowiedzi=lambda conn, run_id, lista: list(lista),
        reply_to=lambda conn, run_id, co, ctx: {"candidates": []},
        niewystawiony_artykul=lambda: None,
    )
    kat = pathlib.Path(tempfile.mkdtemp(prefix="kanal-dzien-"))
    (kat / "kopie").mkdir()
    (kat / "kopie" / "subskrybenci-test.csv").write_text("x", encoding="utf-8")

    class Konfig:
        DATA_DIR = kat

        def __getattr__(self, nazwa):
            return getattr(config, nazwa)

        def cichy_dzien(self):
            return False

        def pora_na_publikacje(self):
            return True, "test"

    return (fake_browser, fake_kanal, modul("alarm",
                                            sprawdz_sesje_i_ostrzez=lambda: None),
            modul("kopia_subskrybentow", main=lambda: None),
            fake_stages, Konfig())


fb, fk, fa, fkop, fs, fc = _swiat()
stare = {n: sys.modules.get(n)
         for n in ("browser", "kanal", "alarm", "kopia_subskrybentow")}
sys.modules.update({"browser": fb, "kanal": fk, "alarm": fa,
                    "kopia_subskrybentow": fkop})
try:
    m = types.ModuleType("run_pod_testem")
    m.__dict__["__name__"] = "run_pod_testem"
    m.__dict__["__file__"] = "agent-v2/run.py"
    exec(compile(zrodla["run.py"], "agent-v2/run.py", "exec"), m.__dict__)
    m.stages = fs
    m.config = fc
    m.ile_przebiegow_zostalo = lambda conn: 1
    m.zmiesci_sie = lambda rodzaj, ile, udzial=1.0: ile
    m.zostal_czas = lambda na_co="", potrzeba_s=0.0: True
    m.rytm = lambda co, na_co, stan: True
    bufor = io.StringIO()
    with contextlib.redirect_stdout(bufor):
        m.dzien(None, 1, wyslij=True)
finally:
    for n, v in stare.items():
        if v is None:
            sys.modules.pop(n, None)
        else:
            sys.modules[n] = v

print("       zobaczone: %s" % ZOBACZONE)
sprawdz("przebieg w ogole dotknal platnych etapow (test cokolwiek mierzy)",
        len(ZOBACZONE) >= 4, ZOBACZONE)
for etap in ("wybierz_cele", "comment_on"):
    widziane = {a for (e, a) in ZOBACZONE if e == etap}
    sprawdz("%s widzi OBA kanaly komentarzy i zaden inny" % etap,
            widziane == {"komentarz@artykul", "komentarz@notka"}, widziane)
puste = [e for (e, a) in ZOBACZONE if not a]
sprawdz("ani jedno wywolanie w dniu nie poszlo bez znacznika", not puste, puste)
w = CONN.execute("SELECT COUNT(*) AS n FROM calls WHERE purpose LIKE 'dzien-%'"
                 " AND akcja = ''").fetchone()
sprawdz("i w bazie nie ma po nich pustej `akcja`", w["n"] == 0, w["n"])

# ==========================================================================
# 6. NIC NIE PLACI POZA MODULAMI, KTORE ANALIZUJEMY
# ==========================================================================
print()
print("=== 6. POZA `agent-v2/*.py` NIE MA PLATNYCH WYWOLAN ===")
poza = []
for p in sorted(pathlib.Path("agent-v2").rglob("*.py")):
    wzgl = p.relative_to("agent-v2")
    if len(wzgl.parts) == 1 or wzgl.parts[0] in ("tests", "__pycache__"):
        continue
    for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
        if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr in PLATNE
                and getattr(n.func.value, "id", None) in ("llm", "_llm")):
            poza.append("%s:%d" % (wzgl, n.lineno))
sprawdz("zaden podkatalog produkcyjny nie wola modelu", not poza, poza)

# ==========================================================================
# 7. WEJSCIA RECZNE — widoczne, nie ukryte
# ==========================================================================
print()
print("=== 7. CO WOLA SIE Z `if __name__ == \"__main__\"` ===")
# Te wywolania sa poza analiza osiagalnosci (patrz „czego nie lapie", punkt 5):
# gdyby liczyly sie jako wolajacy bez kanalu, kazdy skrypt uruchamiany recznie
# psulby wynik. Nie moga jednak byc niewidzialne, bo to JEDYNA droga, ktora
# placi bez kanalu — wiec lista jest zamknieta i nowa pozycja obleje test.
RECZNE = {
    "aktualne_modele.pobierz":
        "`python agent-v2/aktualne_modele.py --wymus` — reczne odswiezenie "
        "listy modeli. W przebiegu agenta ta funkcja idzie przez "
        "`znajdz_ciekawostki` i kanal dziedziczy; uruchomiona z reki nie "
        "sluzy zadnej notce ani artykulowi, wiec nie ma czego dziedziczyc.",
}
for q, s in sorted(STANY.items()):
    for (skad, wk, wm, modul_, linia) in s["main"]:
        print("       %s <- %s:%d (blok startowy skryptu)" % (q, modul_, linia))
recznie = sorted({q for q, s in STANY.items() if s["main"]})
sprawdz("lista platnych wejsc recznych jest DOKLADNIE ta z opisu",
        recznie == sorted(RECZNE), recznie)

# ==========================================================================
# 8. PRODUKCJA NIETKNIETA
# ==========================================================================
print()
print("=== 8. PRODUKCJA ===")
PO = odcisk_katalogu(config.AGENT_DIR / "data")
sprawdz("agent-v2/data/ ma ten sam odcisk, co przed testem", PO == PRZED_DATA,
        "%s -> %s" % (PRZED_DATA, PO))
sprawdz("baza testu to NIE produkcja",
        "temp" in str(config.DB_PATH).lower() or "tmp" in str(config.DB_PATH).lower(),
        config.DB_PATH)

CONN.close()
shutil.rmtree(_KAT, ignore_errors=True)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
