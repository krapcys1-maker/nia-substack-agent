"""Sklada dokumentacje odtworzeniowa z czesci — i GENERUJE te, ktore obiecal.

Uruchomienie: python agent-v2/dokumentacja-zrodla/sklej.py

## Co tu bylo nie tak

Dokument mowil o sobie w czterech miejscach:

    "Wygenerowany ze zrodel przez `ast`, wiec nie da sie go rozjechac z kodem."
    "Wycinki wygenerowane ze zrodel przez `ast`, nie przepisane recznie."

Nic tego nie generowalo. Ten plik importowal wylacznie `pathlib` i `sys`, a slowo
`ast` wystepowalo w nim TYLKO wewnatrz naglowkow wpisywanych do dokumentu — czyli
bylo twierdzeniem w tresci, nie kodem. Cztery "mechaniczne" czesci byly zamrozonymi
zrzutami z 20 sierpnia i rozjechaly sie z kodem w ciagu trzech dni.

To jest ta sama klasa wady, ktora scigamy w samym agencie: obietnica bez pokrycia,
czytana jak gwarancja. Tyle ze tu siedziala w dokumencie, ktorego CALY sens polega
na tym, zeby dalo sie z niego odtworzyc bota.

## Zasada

Czesci MECHANICZNE (spis funkcji, stale, prompty, kod doslownie) sa generowane
przy kazdym uruchomieniu. Czesci ANALITYCZNE (rozdzial_*.md, wstep, wady) sa
pisane recznie i tylko doklejane — bo nikt ich nie wyprowadzi z kodu.

Generator NIE MILCZY, gdy czegos nie znajdzie. Modul spoza spisu, funkcja
wymieniona w KOD_DOSLOWNIE, ktorej juz nie ma, prompt bez opisu — kazde z tych
zdarzen wypisuje ostrzezenie i konczy niezerowym kodem wyjscia. Cicho pominiety
modul to dokladnie ten sam blad co przedtem, tylko wolniejszy.
"""
import ast
import pathlib
import re
import sys

AGENT = pathlib.Path(__file__).resolve().parent.parent
KAT = AGENT / "dokumentacja-zrodla"
CEL = AGENT / "JAK_ZBUDOWANY_JEST_BOT.md"
PROMPTY_KAT = AGENT / "prompts"

NL = "\n"

# Rola kazdego modulu. Jedyna rzecz, ktorej nie da sie wyprowadzic z kodu, bo to
# zdanie o TYM, PO CO modul istnieje, a nie o tym, co robi. Kolejnosc ma
# znaczenie: od rozdzielnika w dol, tak jak czyta sie system.
MODULY = [
    ("run.py", "rozdzielnik — ścieżka artykułu i ścieżka dnia"),
    ("stages.py", "wszystkie etapy myślowe; nie dotyka przeglądarki"),
    ("browser.py", "cała styczność z Substackiem; nie woła modelu"),
    ("llm.py", "JEDYNA warstwa dostępu do modeli i liczenia kosztu"),
    ("gates.py", "bramki jakości; żadna nie blokuje"),
    ("db.py", "schemat i zapis"),
    ("jezyki.py", "wzorce bramek zalezne od jezyka; przy jezyku bez wzorcow bramka jest JAWNIE wylaczona zamiast cicho nic nie lapac"),
    ("konfiguracja.py", "wczytanie `konfiguracja.toml` — jeden plik zamiast edycji w kilkudziesieciu miejscach; nie podejmuje decyzji, tylko podaje wartosci do `config.py`"),
    ("preset.py", "preset: caly opis redakcji w jednym pliku, podlaczany i odlaczany jednym poleceniem; odcisk, osobna instancja danych, brama na wejsciu `run.py`"),
    ("kanal.py", "pamięć o cudzych publikacjach"),
    ("alarm.py", "kontrola sesji, zdrowia i alarm do właściciela"),
    ("style.py", "korpus stylu dla pisarza"),
    ("kopia_subskrybentow.py", "kopia jedynego aktywa, którego nie da się odtworzyć"),
    ("config.py", "wszystkie liczby i decyzje w jednym miejscu (patrz ZAŁĄCZNIK B)"),
    ("statystyki.py", "co przyniosła każda pozycja: wejścia, reakcje, subskrypcje"),
    ("bramki.py", "co może zatrzymać treść — wyliczone z drzewa składni, nie spisane z pamięci"),
    ("raport_statystyk.py", "te same dane w tabeli dla człowieka"),
    ("korpus_kanalow.py", "o czym mówi się w tym tygodniu — zaczyn tematów, nigdy źródło"),
    ("aktualne_modele.py", "jakie modele istnieją DZIŚ; pytane na żywo, nie z pamięci"),
    ("artykul_z_puli.py", "artykuł bierze temat z tej samej puli, co notki"),
    ("norma.py", "licznik produkcji: ile agent wystawil wobec normy dziennej"),
    ("audyt_tematow.py", "audyt segmentu tematow na zywych danych: jedenascie etapow, od kanalow po zwrot do puli"),
    ("audyt_researchu.py", "audyt segmentu researchu na zywych danych: dyskoveria, pobieranie, martwe hosty, karta dowodowa"),
    ("audyt_systemu.py", "audyt CALEGO systemu na zywych danych: publikowanie, normy, komentarze, statystyki, artykul, pieniadze, pamiec"),
    ("wzajemnosc.py",
     "czy zaczepieni sie odwzajemniaja: liczy PO naszej akcji, osobno stan nieorzekalny"),
    ("migracja_okno_promocji.py",
     "jednorazowo: data publikacji z dziennika do kolejki promocji"),
]

# Funkcje pokazane w calosci w sekcji VII. Wybor jest REDAKCYJNY — to te, ktorych
# nie da sie zrozumiec z samego opisu, bo cala tresc siedzi w szczegolach albo
# w komentarzu tlumaczacym, co juz raz poszlo zle.
KOD_DOSLOWNIE = [
    "db.record_call", "db.connect", "db._dopisz_brakujace_kolumny",
    # llm.call to JEDYNA warstwa dostepu do modeli — bez niej dokument opisuje
    # system, ktorego serca nie pokazuje. Nie bylo jej tu, wiec ostrzezenie
    # o martwym wpisie EFFORT nie trafilo do dokumentacji w ogole.
    "llm.call", "llm._cost", "llm._preflight", "llm.obraz",
    # discovery przyjmuje `recent_domains` — parametr, ktory przez tygodnie byl
    # przekazywany i nieczytany. Wycinek pokazuje, ze petla jest juz zamknieta.
    "stages.discovery",
    "stages.pick_topic", "stages.warto_pisac", "stages._precedens_ok",
    # Dziennik przegranych tematow: cala tresc siedzi w uzasadnieniu,
    # dlaczego to NIE jest bramka i dlaczego powod liczy kod, nie model.
    "stages.zapisz_przegranych", "stages._powod_przegranej",
    "stages._stale_sygnaly", "stages.losuj_odstep", "stages.bramka_kandydata",
    "stages.budzet_dnia", "stages.artykul_do_promocji", "stages.grafika",
    "gates.deterministic_floors", "gates.uwagi_z_formy", "gates.odcisk_formy",
    "gates.powtorzona_forma", "gates.zapowiedziany_akapit_granic",
    "gates.frazy_z_instrukcji",
    "run.rytm", "run.zmiesci_sie", "run.zostal_czas", "run.zajmij_zamek",
    "run.odmow_publikacji_z_kopii",
    "browser._klik_na_profilu", "browser.restackuj_w_kanale",
    "browser.wypelnij_artykul",
    "kanal._za_niedawno_u_nich",
]

# Placeholder promptu: {pole}, ale NIE {{pole}} — podwojone nawiasy to literalny
# JSON w tresci, ktory `str.format` zamienia na pojedyncze.
POLE = re.compile(r"(?<!\{)\{([a-z_][a-z0-9_]*)\}(?!\})")

ostrzezenia: list[str] = []


def ostrzez(tekst: str) -> None:
    ostrzezenia.append(tekst)
    print("  UWAGA: %s" % tekst)


def _pierwsza_linia_docstringa(wezel) -> str:
    d = ast.get_docstring(wezel)
    if not d:
        return "—"
    return d.strip().splitlines()[0].strip()


def _podpis(f) -> str:
    args = [a.arg for a in f.args.args if a.arg not in ("self", "cls")]
    if f.args.vararg:
        args.append("*" + f.args.vararg.arg)
    if f.args.kwarg:
        args.append("**" + f.args.kwarg.arg)
    return "%s(%s)" % (f.name, ", ".join(args))


# --- czesc mechaniczna 1: spis modulow i funkcji ------------------------------

def gen_moduly() -> str:
    wiersze = [""]
    wymienione = {n for n, _ in MODULY}
    istniejace = {p.name for p in AGENT.glob("*.py")}
    for brak in sorted(istniejace - wymienione):
        ostrzez("modul %s istnieje, ale nie ma go w spisie MODULY w sklej.py "
                "— dopisz go z rola, inaczej znika z dokumentacji" % brak)
    for nazwa, rola in MODULY:
        p = AGENT / nazwa
        if not p.exists():
            ostrzez("modul %s jest w spisie, ale pliku nie ma" % nazwa)
            continue
        zrodlo = p.read_text(encoding="utf-8")
        drzewo = ast.parse(zrodlo)
        funkcje = [w for w in drzewo.body
                   if isinstance(w, (ast.FunctionDef, ast.AsyncFunctionDef))]
        klasy = [w for w in drzewo.body if isinstance(w, ast.ClassDef)]
        wiersze += [
            "### `%s` — %s" % (nazwa, rola),
            "",
            "%d wierszy, %d funkcji na poziomie modułu, %d klas"
            % (len(zrodlo.splitlines()), len(funkcje), len(klasy)),
            "",
        ]
        if not funkcje:
            wiersze += ["*(sam moduł danych — patrz ZAŁĄCZNIK B)*", ""]
            continue
        wiersze += ["| funkcja | co robi |", "|---|---|"]
        for f in funkcje:
            wewn = " *(wewn.)*" if f.name.startswith("_") else ""
            wiersze.append("| `%s`%s | %s |"
                           % (_podpis(f), wewn, _pierwsza_linia_docstringa(f)))
        wiersze.append("")
    return NL.join(wiersze)


# --- czesc mechaniczna 2: wszystkie stale konfiguracji ------------------------

def gen_stale() -> str:
    zrodlo = (AGENT / "config.py").read_text(encoding="utf-8")
    linie = zrodlo.splitlines()
    drzewo = ast.parse(zrodlo)
    wiersze = ["", "| stała | wartość | po co |", "|---|---|---|"]
    for w in drzewo.body:
        if not isinstance(w, ast.Assign) or len(w.targets) != 1:
            continue
        cel = w.targets[0]
        if not isinstance(cel, ast.Name) or not cel.id.isupper():
            continue
        wartosc = ast.get_source_segment(zrodlo, w.value) or ""
        wartosc = " ".join(wartosc.split())
        if len(wartosc) > 44:
            wartosc = wartosc[:44]
        # Komentarz stojacy BEZPOSREDNIO nad definicja — to on niesie powod.
        komentarz = []
        i = w.lineno - 2
        while i >= 0 and linie[i].lstrip().startswith("#"):
            komentarz.insert(0, linie[i].lstrip().lstrip("#").strip())
            i -= 1
        opis = " ".join(x for x in komentarz if x)[:140] or "—"
        wiersze.append("| `%s` | `%s` | %s |" % (cel.id, wartosc, opis))
    wiersze.append("")
    return NL.join(wiersze)


# --- czesc mechaniczna 3: kod doslownie ---------------------------------------

def _zrodlo_funkcji(modul: str, nazwa: str) -> str | None:
    p = AGENT / (modul + ".py")
    if not p.exists():
        return None
    zrodlo = p.read_text(encoding="utf-8")
    for w in ast.walk(ast.parse(zrodlo)):
        if isinstance(w, (ast.FunctionDef, ast.AsyncFunctionDef)) and w.name == nazwa:
            return ast.get_source_segment(zrodlo, w)
    return None


def gen_kod() -> str:
    wiersze = [""]
    for wpis in KOD_DOSLOWNIE:
        modul, _, nazwa = wpis.partition(".")
        tresc = _zrodlo_funkcji(modul, nazwa)
        if tresc is None:
            ostrzez("KOD_DOSLOWNIE wymienia %s, ale takiej funkcji juz nie ma "
                    "— usun wpis albo popraw nazwe" % wpis)
            continue
        wiersze += ["<!--KOD:%s-->" % wpis, "```python", tresc, "```", ""]
    return NL.join(wiersze)


# --- czesc mechaniczna 4: prompty ---------------------------------------------

def _pola_promptu(tresc: str) -> list[str]:
    return sorted(set(POLE.findall(tresc)))


def _kontrakt_wyjscia(tresc: str) -> str:
    """Ostatnia linia zaczynajaca sie od `{{` — to jest kontrakt JSON-a."""
    for linia in reversed(tresc.splitlines()):
        if linia.strip().startswith("{{"):
            return linia.strip()
    return ""


def _prompty() -> list[tuple[str, str]]:
    """Wszystkie pliki z prompts/, w kolejnosci NIEZALEZNEJ OD SYSTEMU.

    Bylo `sorted(PROMPTY_KAT.glob(...))`, czyli sortowanie obiektow Path —
    a te na Windowsie porownuja sie BEZ UWZGLEDNIENIA WIELKOSCI LITER, na
    Linuksie z uwzglednieniem. Ten sam generator dawal wiec dwa rozne
    dokumenty na dwoch maszynach i test „przebudowa niczego nie zmienia"
    przechodzil lokalnie, a oblewal na serwerze. Sortujemy po nazwie jako
    napisie, bo napisy porownuja sie wszedzie tak samo.
    """
    return [(f.name, f.read_text(encoding="utf-8"))
            for f in sorted(PROMPTY_KAT.glob("*.md"), key=lambda f: f.name)]


def _czytane_przez_kod() -> set[str]:
    """Ktore pliki z prompts/ wystepuja doslownie w kodzie agenta.

    Prosty test na obecnosc nazwy w zrodle. Wystarcza, bo prompty laduje sie
    przez `_prompt("nazwa.md", ...)`, a plik, ktorego nazwa nie pada nigdzie,
    nie ma jak zostac wczytany.
    """
    zrodla = "".join(f.read_text(encoding="utf-8") for f in AGENT.glob("*.py"))
    return {n for n, _ in _prompty() if n in zrodla}


def gen_prompty() -> str:
    czytane = _czytane_przez_kod()
    wiersze = [""]
    for nazwa, tresc in _prompty():
        if nazwa not in czytane:
            continue
        pola = _pola_promptu(tresc)
        wiersze += [
            "#### `%s` (%d wierszy)" % (nazwa, len(tresc.splitlines())),
            "",
            "**Pola wejściowe:** %s"
            % (", ".join("`%s`" % p for p in pola) if pola else "*(brak)*"),
            "",
        ]
        kontrakt = _kontrakt_wyjscia(tresc)
        if kontrakt:
            wiersze += ["**Kontrakt wyjścia:**", "", "```json", kontrakt, "```", ""]
    return NL.join(wiersze)


def gen_zalacznik_prompty() -> str:
    wiersze = [
        "",
        "## ZALACZNIK A — WSZYSTKIE PROMPTY W CALOSCI",
        "",
        "Prompty sa ladowane przez `stages._prompt(nazwa, **pola)`, ktore robi",
        "`str.format` — dlatego **kazdy nawias klamrowy w tresci JSON-a jest podwojony**",
        "(`{{\"klucz\": ...}}`), a pola wejsciowe stoja w pojedynczych (`{card_json}`).",
        "",
        "Wygenerowany z katalogu `prompts/` przy skladaniu dokumentu, wiec nie da sie",
        "go rozjechac z tym, co naprawde dostaje model.",
        "",
        "### A.1. Prompty robocze",
        "",
        "---",
        "",
    ]
    czytane = _czytane_przez_kod()
    nieczytane = [(n, t) for n, t in _prompty() if n not in czytane]
    for nazwa, tresc in [(n, t) for n, t in _prompty() if n in czytane]:
        pola = _pola_promptu(tresc)
        wiersze += [
            "#### `prompts/%s`" % nazwa,
            "",
            "**%d wierszy.** Pola wejsciowe: %s"
            % (len(tresc.splitlines()),
               ", ".join("`%s`" % p for p in pola) if pola else "*(brak)*"),
            "",
            "````markdown",
            tresc.rstrip(),
            "````",
            "",
            "---",
            "",
        ]
    if nieczytane:
        # PLIKI, KTORE LEZA W prompts/, A NIE SA PROMPTAMI. Dokument
        # przedstawial je wczesniej jako „prompty robocze" z adnotacja „pola
        # wejsciowe: brak" — czyli kazdy odtwarzajacy bota szukalby miejsca,
        # w ktorym sa wolane. Nie ma takiego miejsca. To notatki wlasciciela
        # i tak maja byc opisane.
        wiersze += [
            "### A.2. Pliki w `prompts/`, ktorych kod NIE czyta",
            "",
            "Nazwa zadnego z nich nie pada w zrodlach agenta, wiec nie ma jak",
            "trafic do modelu. Leza tu jako notatki i zasady dla czlowieka —",
            "nie szukaj miejsca, w ktorym sa wolane, bo takiego nie ma.",
            "",
        ]
        for nazwa, tresc in nieczytane:
            wiersze += ["- `prompts/%s` (%d wierszy)"
                        % (nazwa, len(tresc.splitlines()))]
        wiersze.append("")
    return NL.join(wiersze)


GENERATORY = {
    "moduly.md": gen_moduly,
    "stale.md": gen_stale,
    "kod.md": gen_kod,
    "prompty.md": gen_prompty,
    "zalacznik_prompty.md": gen_zalacznik_prompty,
}


def _liczby() -> dict[str, str]:
    """Liczby, ktore w dokumencie MUSZA pochodzic z kodu, a nie z pamieci.

    Sekcja I podawala 10 171 wierszy, sekcja II tego samego dokumentu inna
    liczbe — obie o tym samym bocie, w odleglosci trzystu wierszy. Liczba
    wpisana recznie w dokumencie o kodzie rozjedzie sie zawsze; pytanie tylko
    kiedy. Wiec jej tam nie wpisujemy.
    """
    pliki = sorted(AGENT.glob("*.py"))
    wierszy = sum(len(f.read_text(encoding="utf-8").splitlines()) for f in pliki)
    testy = sorted((AGENT / "tests").glob("test_*.py"))
    sprawdzen = sum(f.read_text(encoding="utf-8").count("sprawdz(") for f in testy)

    def ile_wierszy(nazwa: str) -> str:
        f = AGENT / nazwa
        return str(len(f.read_text(encoding="utf-8").splitlines())) if f.exists() else "?"

    return {
        "{{ile_plikow}}": str(len(pliki)),
        "{{ile_wierszy}}": "%d %03d" % divmod(wierszy, 1000) if wierszy >= 1000
                           else str(wierszy),
        "{{ile_zestawow}}": str(len(testy)),
        "{{ile_sprawdzen}}": str(sprawdzen),
        "{{wiersze_style}}": ile_wierszy("style.py"),
        "{{wiersze_kopii}}": ile_wierszy("kopia_subskrybentow.py"),
    }


def czytaj(nazwa: str) -> str:
    p = KAT / nazwa
    if not p.exists():
        ostrzez("BRAK CZESCI: %s" % nazwa)
        return NL + "> *(brakuje sekcji `%s` — dokument niekompletny)*" % nazwa + NL
    tresc = p.read_text(encoding="utf-8").rstrip() + NL
    for znacznik, wartosc in _liczby().items():
        tresc = tresc.replace(znacznik, wartosc)
    return tresc


CZESCI = [
    ("wstep", "wstep.md"),
    ("moduly", "moduly.md"),
    ("artykul", "rozdzial_artykul.md"),
    ("dzien", "rozdzial_dzien.md"),
    ("bramki", "rozdzial_bramki.md"),
    ("dane", "rozdzial_dane.md"),
    ("kod", "kod.md"),
    ("wady", "wady.md"),
    ("zal_prompty", "zalacznik_prompty.md"),
    ("zal_stale", "stale.md"),
    ("zal_dysk", "zalacznik_dysk.md"),
]

NAGLOWKI = {
    "moduly": [
        "", "## II. Spis modulow i funkcji", "",
        "Wygenerowany ze zrodel przez `ast` przy kazdym skladaniu dokumentu,",
        "wiec nie da sie go rozjechac z kodem.",
        "",
    ],
    "artykul": ["", "## III. Sciezka artykulu — dziesiec etapow", ""],
    "dzien": ["", "## IV. Sciezka dnia i styk z Substackiem", ""],
    "bramki": ["", "## V. Bramki i kontrola jakosci", ""],
    "dane": ["", "## VI. Dane, dysk, koszty i operacje", ""],
    "kod": [
        "", "## VII. Kluczowy kod doslownie", "",
        "Wycinki wyciete ze zrodel przez `ast` przy kazdym skladaniu dokumentu,",
        "nie przepisane recznie. Kazdy blok poprzedza znacznik",
        "`<!--KOD:modul.funkcja-->`.",
        "",
    ],
    "zal_stale": [
        "", "## ZALACZNIK B — WSZYSTKIE STALE KONFIGURACJI", "",
        "Wygenerowany z `config.py` przy kazdym skladaniu dokumentu: nazwa,",
        "wartosc i komentarz stojacy bezposrednio nad definicja.",
        "",
    ],
}


def main() -> int:
    print("== skladanie dokumentacji odtworzeniowej ==")
    print()
    print("  generuje czesci mechaniczne ze zrodel:")
    for nazwa, generator in GENERATORY.items():
        tresc = generator().rstrip() + NL
        (KAT / nazwa).write_text(tresc, encoding="utf-8")
        print("    %-24s %6d wierszy" % (nazwa, len(tresc.splitlines())))
    print()

    czesci = []
    for klucz, plik in CZESCI:
        tresc = czytaj(plik)
        naglowek = NL.join(NAGLOWKI.get(klucz, []))
        czesci.append((naglowek + NL if naglowek else "") + tresc)
    dokument = NL.join(czesci)
    # Znacznik, ktorego nikt nie podstawil, to liczba, ktorej w dokumencie
    # nie ma — a wyglada jak literowka, nie jak brak.
    import re as _re
    for osierocony in sorted(set(_re.findall(r"\{\{[a-z_]+\}\}", dokument))):
        ostrzez("znacznik %s nie zostal podstawiony — dopisz go do _liczby()"
                % osierocony)
    CEL.write_text(dokument, encoding="utf-8")
    print("  zapisano %s" % CEL.name)
    print("    wierszy: %d" % len(dokument.splitlines()))
    print("    znakow:  %d" % len(dokument))
    if ostrzezenia:
        print()
        print("  %d OSTRZEZEN — dokument powstal, ale czegos w nim brakuje."
              % len(ostrzezenia))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
