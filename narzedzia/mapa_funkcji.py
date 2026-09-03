# -*- coding: utf-8 -*-
"""Generator `docs/MAPA_FUNKCJI.md` — pelny spis funkcji agenta, z DRZEWA SKLADNI.

W tym projekcie obowiazuje zasada „grep w zrodle nie jest dowodem, ze kod
dziala", wiec ten generator nie szuka napisow. Dla kazdego modulu produkcyjnego
(`agent-v2/*.py`) czyta `ast` i wypisuje:

  * kazda funkcje i metode: nazwa, linia, sygnatura, pierwsze zdanie docstringa;
  * czy wola platny model (`llm.call` / `llm.obraz` / `llm.ratuj_json`) i z jakim
    etapem (`purpose`) — czyli gdzie dokladnie wychodza pieniadze;
  * czy dotyka przegladarki (Playwright) — czyli co jest wrosniete w Substacka;
  * czy dotyka bazy;
  * KTO JA WOLA — krawedzie wywolan rozwiazane po module i po nazwie.

Funkcja bez wolajacych dostaje znacznik `MARTWA?`. To jest PODEJRZENIE, nie
werdykt: wywolanie przez zmienna, `getattr`, slownik funkcji albo
`functools.partial` nie tworzy krawedzi, a wejscia z systemd i `main()` sa
bez wolajacych z definicji. Werdykt dla PLATNYCH wywolan wydaje
`agent-v2/tests/test_kanal_platnego_wywolania.py`, ktory liczy to ostrozniej
i ma wpisana zamknieta liste znanych wyjatkow.

Uruchomienie:  python narzedzia/mapa_funkcji.py
"""
from __future__ import annotations

import ast
import pathlib
import sys
from collections import defaultdict

KORZEN = pathlib.Path(__file__).resolve().parent.parent
KOD = KORZEN / "agent-v2"
WYNIK = KORZEN / "docs" / "FUNCTION_MAP.md"

PLATNE = {"call", "obraz", "ratuj_json"}

# Co odpalaja timery systemd — korzenie drzewa osiagalnosci.
WEJSCIA = {
    "run.py": "`nia-agent.timer`, piec razy na dobe: `run.py --dzien --wyslij`",
    "alarm.py": "`nia-alarm.timer`, raz na dobe 07:00 UTC: `alarm.py`",
    "artykul_z_puli.py": "`nia-artykul.timer`, wtorek 14:00 UTC: `artykul_z_puli.py --wyslij`",
}

# Jednozdaniowy opis modulu do naglowka rozdzialu. Bierzemy z docstringa pliku,
# a to tylko zapasowa etykieta roli, gdy docstringa nie ma.
ROLE = {
    "config": "jedyne zrodlo prawdy o ustawieniach",
    "run": "przebieg dnia i przebieg artykulu",
    "stages": "wszystkie etapy modelu",
    "browser": "cala warstwa Substacka",
    "llm": "transport do dostawcow modeli i ksiegowanie kosztu",
    "db": "schemat bazy i zapis",
    "gates": "bramki deterministyczne po napisaniu",
}


def sygnatura(w: ast.AST) -> str:
    a = w.args
    czesci: list[str] = []
    for arg in a.posonlyargs + a.args:
        czesci.append(arg.arg)
    if a.vararg:
        czesci.append("*" + a.vararg.arg)
    for arg in a.kwonlyargs:
        czesci.append(arg.arg)
    if a.kwarg:
        czesci.append("**" + a.kwarg.arg)
    return "(%s)" % ", ".join(czesci)


def pierwsze_zdanie(w: ast.AST) -> str:
    """Pierwsze zdanie docstringa — tyle, ile miesci sie w komorce tabeli."""
    d = ast.get_docstring(w) or ""
    d = " ".join(d.split())
    if not d:
        return ""
    for k in (". ", "? ", "! "):
        if k in d[:400]:
            d = d[: d.index(k) + 1]
            break
    return d[:220]


class Zbieracz(ast.NodeVisitor):
    """Jeden modul: funkcje, ich cechy i wychodzace krawedzie wywolan."""

    def __init__(self, modul: str) -> None:
        self.modul = modul
        self.stos: list[str] = []
        self.funkcje: dict[str, dict] = {}

    def _wejdz(self, w, klasa: bool = False) -> None:
        nazwa = ".".join(self.stos + [w.name])
        if not klasa:
            self.funkcje[nazwa] = {
                "linia": w.lineno,
                "sygnatura": sygnatura(w),
                "opis": pierwsze_zdanie(w),
                "platne": [],
                "przegladarka": False,
                "baza": False,
                "wola": set(),      # `modul.nazwa` z jawnego wywolania
                "nazwy": set(),     # SAME identyfikatory, takze bez nawiasu
            }
        self.stos.append(w.name)
        for dziecko in w.body:
            self.visit(dziecko)
        self.stos.pop()
        if not klasa:
            self._skanuj(w, nazwa)

    def _skanuj(self, w, nazwa: str) -> None:
        dane = self.funkcje[nazwa]
        for n in ast.walk(w):
            # SAMA NAZWA TEZ SIE LICZY. `KONTROLE = (cisza, dysk, koszt)` i
            # `polecenia = {"sesja": sprawdz_sesje}` to prawdziwe uzycia
            # funkcji — bez ani jednego nawiasu. Liczenie wylacznie wywolan
            # oznaczalo 108 funkcji jako martwe, z czego prawie wszystkie zyly.
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                dane["nazwy"].add(n.id)
            if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name):
                if n.value.id in ("page", "context"):
                    dane["przegladarka"] = True
                if n.value.id == "conn" and n.attr in ("execute", "executemany"):
                    dane["baza"] = True
            if isinstance(n, ast.Call):
                f = n.func
                if isinstance(f, ast.Attribute) and isinstance(f.value, ast.Name):
                    obiekt, metoda = f.value.id, f.attr
                    if obiekt == "llm" and metoda in PLATNE:
                        dane["platne"].append(self._purpose(n))
                    if obiekt == "db":
                        dane["baza"] = True
                    if obiekt in ("browser", "sync_playwright"):
                        dane["przegladarka"] = True
                    dane["wola"].add("%s.%s" % (obiekt, metoda))
                elif isinstance(f, ast.Name):
                    dane["wola"].add("%s.%s" % (self.modul, f.id))

    @staticmethod
    def _purpose(n: ast.Call) -> str:
        for kw in n.keywords:
            if kw.arg == "purpose" and isinstance(kw.value, ast.Constant):
                return str(kw.value.value)
        for a in n.args:
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                return a.value
        return "(zmienna)"

    def visit_FunctionDef(self, w):        # noqa: N802
        self._wejdz(w)

    def visit_AsyncFunctionDef(self, w):   # noqa: N802
        self._wejdz(w)

    def visit_ClassDef(self, w):           # noqa: N802
        self._wejdz(w, klasa=True)


def nazwy_z_poziomu_modulu(drzewo: ast.AST) -> set[str]:
    """Identyfikatory uzyte POZA cialem jakiejkolwiek funkcji.

    Tu siedza tablice dyspozytorskie: `KONTROLE = (cisza, dysk, koszt)`
    i `POLECENIA = {"sesja": sprawdz_sesje}`. Bez tego kazda taka funkcja
    wygladalaby na martwa.
    """
    out: set[str] = set()
    for n in ast.iter_child_nodes(drzewo):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        for x in ast.walk(n):
            if isinstance(x, ast.Name) and isinstance(x.ctx, ast.Load):
                out.add(x.id)
    return out


def zbierz() -> dict[str, tuple[Zbieracz, str, set[str]]]:
    out: dict[str, tuple[Zbieracz, str, set[str]]] = {}
    for p in sorted(KOD.glob("*.py")):
        drzewo = ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        z = Zbieracz(p.stem)
        z.visit(drzewo)
        opis = pierwsze_zdanie(drzewo) or ROLE.get(p.stem, "")
        out[p.stem] = (z, opis, nazwy_z_poziomu_modulu(drzewo))
    return out


def krawedzie(moduly: dict[str, tuple[Zbieracz, str, set[str]]]) -> dict[str, set[str]]:
    """Kto uzywa kogo, po pelnej nazwie `modul.funkcja`.

    Nazwe rozwiazujemy w trzech krokach, od najwezszego zakresu:
      1. funkcja zagniezdzona w tej samej funkcji (`dzien.notki` widziane
         z `dzien`) — bo domkniecie wola sasiada po samej nazwie;
      2. funkcja z tego samego modulu;
      3. jawne `modul.nazwa` z innego modulu.
    """
    wszystkie = {"%s.%s" % (m, f) for m, (z, _, _) in moduly.items() for f in z.funkcje}
    uzywajacy: dict[str, set[str]] = defaultdict(set)

    def dopisz(cel: str, skad: str) -> None:
        if cel in wszystkie and cel != skad:
            uzywajacy[cel].add(skad)

    def rozwiaz(m: str, zakres: str, nazwa: str, skad: str) -> None:
        czesci = zakres.split(".") if zakres else []
        while czesci:                       # 1. w gore po zakresach leksykalnych
            kandydat = "%s.%s.%s" % (m, ".".join(czesci), nazwa)
            if kandydat in wszystkie:
                dopisz(kandydat, skad)
                return
            czesci.pop()
        dopisz("%s.%s" % (m, nazwa), skad)  # 2. gora modulu

    for m, (z, _, gorne) in moduly.items():
        # uzycia z poziomu modulu: `KONTROLE = (cisza, dysk)`
        for nazwa in gorne:
            dopisz("%s.%s" % (m, nazwa), "%s (poziom modulu)" % m)
        for f, dane in z.funkcje.items():
            skad = "%s.%s" % (m, f)
            for cel in dane["wola"]:        # 3. jawne `modul.nazwa`
                dopisz(cel, skad)
            for nazwa in dane["nazwy"]:
                rozwiaz(m, f, nazwa, skad)
    return uzywajacy


def main() -> int:
    moduly = zbierz()
    uzywajacy = krawedzie(moduly)
    wszystkie = [(m, f, d) for m, (z, _, _g) in moduly.items()
                 for f, d in z.funkcje.items()]
    razem = len(wszystkie)
    platnych = sum(1 for _, _, d in wszystkie if d["platne"])
    z_www = sum(1 for _, _, d in wszystkie if d["przegladarka"])
    z_baza = sum(1 for _, _, d in wszystkie if d["baza"])

    L: list[str] = []
    A = L.append
    A("# Mapa funkcji — pelny spis\n")
    A("Plik **generowany**: `python narzedzia/mapa_funkcji.py`. Nie edytuj go recznie.")
    A("Zrodlem jest **drzewo skladni** modulow, nie grep po napisach.\n")
    A("Zakres: wylacznie `agent-v2/*.py`, czyli to, co odpalaja timery systemd.")
    A("`archiwum/` jest poza mapa — nie stoi na zadnej zywej sciezce.\n")

    A("## Liczby\n")
    A("| co | ile |")
    A("|---|---|")
    A("| modulow | %d |" % len(moduly))
    A("| funkcji i metod razem | %d |" % razem)
    A("| funkcji wolajacych platny model | %d |" % platnych)
    A("| funkcji dotykajacych przegladarki | %d |" % z_www)
    A("| funkcji dotykajacych bazy | %d |" % z_baza)
    A("")

    A("## Legenda\n")
    A("| znacznik | znaczy |")
    A("|---|---|")
    A("| **$**(etap) | wola platny model; w nawiasie `purpose`, po ktorym rozlicza sie koszt w tabeli `calls` |")
    A("| WWW | dotyka przegladarki (`page.*`, `context.*`, `browser.*`) — czyli warstwy Substacka |")
    A("| DB | czyta albo pisze baze |")
    A("| MARTWA? | zadna krawedz wywolania w `agent-v2/*.py` na nia nie wskazuje |")
    A("")
    A("`MARTWA?` to **podejrzenie, nie werdykt**. Wywolanie przez zmienna,")
    A("`getattr`, slownik funkcji albo `functools.partial` nie tworzy krawedzi,")
    A("a `main()` i wejscia z systemd sa bez wolajacych z definicji. Dla platnych")
    A("wywolan werdykt wydaje `agent-v2/tests/test_kanal_platnego_wywolania.py`.\n")

    A("## Spis modulow\n")
    A("| modul | funkcji | platnych | WWW | DB | rola |")
    A("|---|---|---|---|---|---|")
    for m in sorted(moduly):
        z, opis, _g = moduly[m]
        if not z.funkcje:
            continue
        d = list(z.funkcje.values())
        A("| [`%s.py`](#agent-v2%s-py) | %d | %d | %d | %d | %s |"
          % (m, m.replace("_", "-"), len(d),
             sum(1 for x in d if x["platne"]),
             sum(1 for x in d if x["przegladarka"]),
             sum(1 for x in d if x["baza"]),
             (opis or "—").replace("|", "\\|")[:110]))
    A("")

    for m in sorted(moduly):
        z, opis, _g = moduly[m]
        if not z.funkcje:
            continue
        A("---\n")
        A('<a id="agent-v2%s-py"></a>' % m.replace("_", "-"))
        A("## `agent-v2/%s.py`\n" % m)
        if opis:
            A("%s\n" % opis)
        plik = "%s.py" % m
        if plik in WEJSCIA:
            A("**Wejscie produkcyjne:** %s\n" % WEJSCIA[plik])
        A("%d funkcji.\n" % len(z.funkcje))
        A("| linia | funkcja | znaczniki | co robi | wolana przez |")
        A("|---|---|---|---|---|")
        for nazwa in sorted(z.funkcje, key=lambda n: z.funkcje[n]["linia"]):
            d = z.funkcje[nazwa]
            pelna = "%s.%s" % (m, nazwa)
            znaki = []
            if d["platne"]:
                znaki.append("**$**(%s)" % ", ".join(sorted(set(d["platne"]))))
            if d["przegladarka"]:
                znaki.append("WWW")
            if d["baza"]:
                znaki.append("DB")
            kto = sorted(uzywajacy.get(pelna, ()))
            if not kto:
                znaki.append("MARTWA?")
            kto_txt = ", ".join("`%s`" % k for k in kto[:4])
            if len(kto) > 4:
                kto_txt += " *(+%d)*" % (len(kto) - 4)
            A("| %d | `%s%s` | %s | %s | %s |"
              % (d["linia"], nazwa, d["sygnatura"], " ".join(znaki) or "—",
                 (d["opis"] or "—").replace("|", "\\|"), kto_txt or "—"))
        A("")

    WYNIK.parent.mkdir(parents=True, exist_ok=True)
    WYNIK.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("zapisano %s" % WYNIK.relative_to(KORZEN))
    print("  %d modulow, %d funkcji, %d platnych, %d z przegladarka, %d z baza"
          % (len(moduly), razem, platnych, z_www, z_baza))
    return 0


if __name__ == "__main__":
    sys.exit(main())
