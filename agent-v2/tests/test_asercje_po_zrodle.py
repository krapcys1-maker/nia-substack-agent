# -*- coding: utf-8 -*-
"""Asercja szukajaca napisu w KODZIE nie moze przechodzic na KOMENTARZU.

## Po co ten plik istnieje

W zestawie jest 138 asercji o ksztalcie:

    zrodlo = pathlib.Path("agent-v2/cos.py").read_text(...)
    sprawdz("...", "jakis napis" in zrodlo)

Czesc z nich jest w porzadku: sprawdzaja, ze RAPORT drukuje dana kolumne albo
ze prompt niesie zdanie kontraktu. Ale trzy razy w tym audycie taka asercja
PRZEZYLA ZNIKNIECIE TEGO, CZEGO PILNOWALA — bo poprawka zostawila w komentarzu
cytat starego kodu, a asercja pyta o TEKST PLIKU, nie o kod:

  * `test_jezyk_bramek`: „zaden wzorzec nie zostal na sztywno" sprawdzalo
    dokladny tekst JEDNEGO wzorca; dwa inne stały tam caly czas;
  * `test_cudze_dane`: „skrypt ustawia prawa po zapisie" przechodzilo, bo
    `chmod(0o600)` siedzi w komentarzu OPISUJACYM usunieta wade;
  * `test_obietnice_bez_pokrycia`: „alarm liczy sufit z `sufit_dnia`" pyta,
    czy w `alarm.py` WYSTEPUJE NAPIS — a nie, jaka liczba z tego wychodzi;
  * `test_obserwacje`: DWIE asercje o osobnych budzetach przechodzily na
    komentarzu opisujacym poprawke z 20 sierpnia; kod bierze dzis oba
    przydzialy jednym wyrazeniem. Znalazl je ten plik, nie czlowiek.

## Ile ich jest naprawde

Pierwszy pomiar tego pliku dal 95 trafien na 140 i BYL BLEDNY: odsiew laczyl
tokeny przez nowy wiersz, wiec zaden napis dluzszy niz jeden token nie mial
prawa sie znalezc. Po poprawce (zamazywanie zakresow zamiast sklejania) zostalo
DZIEWIEC, z czego osiem to asercje pilnujace UZASADNIENIA — patrz nizej.

Liczba, ktora wyglada na pomiar i nim nie jest, to dokladnie ta wada, ktora ten
plik sciga. Zapisana, zeby nastepny czytelnik wiedzial, ze byla.

## Czego pilnuje

JEDNEJ RZECZY, ktorej nie da sie obejsc komentarzem: dla kazdej asercji
`"<napis>" in <tekst pliku .py>` napis MUSI wystepowac w KODZIE tego pliku,
a nie wylacznie w komentarzach i docstringach.

Kod odsiewamy przez `tokenize` — komentarze i napisy dokumentacyjne wypadaja,
reszta zostaje. To jest to samo pytanie, ktore zadaje czytajacy czlowiek
(„czy ten kod tam JEST"), tylko zadane maszynie.

## Czego ten plik NIE robi

Nie zabrania asercji po tekscie zrodla. Bywaja sluszne — naglowek kolumny
w raporcie albo zdanie kontraktu w prompcie to NAPRAWDE napisy. Pilnuje
wylacznie tego, zeby napis o kodzie znajdowal sie w kodzie.

Nie sprawdza tez plikow innych niz `.py`: w prompcie i w dokumencie CALY plik
jest trescia, wiec pytanie „czy to jest komentarz" nie ma tam sensu.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_asercje_po_zrodle.py
"""
import ast
import io
import pathlib
import tokenize

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


def kod_bez_komentarzy(tekst: str) -> str:
    """Kod pliku bez komentarzy i bez napisow dokumentacyjnych.

    `tokenize` rozstrzyga to tak samo, jak Python: komentarz to `COMMENT`,
    a docstring to `STRING` stojacy samodzielnie w wyrazeniu. Napisy UZYTE
    w kodzie (komunikaty, klucze, wzorce) ZOSTAJA — bo one sa kodem.
    """
    # WYCINAMY MIEJSCA, NIE SKLEJAMY TOKENOW. Pierwsza wersja laczyla tokeny
    # przez nowy wiersz — czyli niszczyla uklad tekstu, wiec ZADEN napis
    # dluzszy niz jeden token nie mial prawa sie znalezc. Wynik: 95 rzekomych
    # trafien na 140 zbadanych asercji, wszystkie falszywe; sprawdzone recznie
    # na `data["safe_to_post"] = False`, ktore w `stages.py` JEST.
    #
    # To jest ta sama klasa wady, ktora ten plik ma lapac — narzedzie
    # produkujace liczbe wygladajaca na pomiar — wiec zostaje opisana, a nie
    # tylko naprawiona.
    #
    # Zostawiamy plik bajt w bajt i ZAMAZUJEMY spacjami dokladnie te zakresy,
    # ktore sa komentarzem albo docstringiem. Uklad reszty zostaje nietkniety.
    try:
        tokeny = list(tokenize.generate_tokens(io.StringIO(tekst).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return tekst          # w razie watpliwosci nie oskarzamy
    docstringi = set()
    try:
        for w in ast.walk(ast.parse(tekst)):
            if isinstance(w, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                              ast.ClassDef)) and w.body:
                pierwszy = w.body[0]
                if (isinstance(pierwszy, ast.Expr)
                        and isinstance(pierwszy.value, ast.Constant)
                        and isinstance(pierwszy.value.value, str)):
                    docstringi.add((pierwszy.lineno, pierwszy.col_offset))
    except SyntaxError:
        pass
    wiersze = tekst.split(chr(10))
    for typ, _napis, (w1, k1), (w2, k2), _ in tokeny:
        if typ == tokenize.COMMENT:
            pass
        elif typ == tokenize.STRING and (w1, k1) in docstringi:
            pass
        else:
            continue
        for nr in range(w1, w2 + 1):
            if nr - 1 >= len(wiersze):
                break
            linia = wiersze[nr - 1]
            od = k1 if nr == w1 else 0
            do = k2 if nr == w2 else len(linia)
            wiersze[nr - 1] = linia[:od] + " " * max(0, do - od) + linia[do:]
    return chr(10).join(wiersze)


def asercje_po_zrodle(plik: pathlib.Path):
    """(linia, sciezka pliku, szukany napis) dla `"<napis>" in <tekst .py>`."""
    try:
        drzewo = ast.parse(plik.read_text(encoding="utf-8"))
    except (SyntaxError, OSError):
        return
    zrodla: dict[str, str] = {}
    for w in ast.walk(drzewo):
        if not (isinstance(w, ast.Assign) and isinstance(w.value, ast.Call)):
            continue
        if getattr(w.value.func, "attr", None) != "read_text":
            continue
        wyrazenie = ast.unparse(w.value)
        sciezki = [s for s in ast.walk(w.value)
                   if isinstance(s, ast.Constant) and isinstance(s.value, str)
                   and s.value.endswith(".py")]
        if not sciezki:
            continue
        for c in w.targets:
            if isinstance(c, ast.Name):
                zrodla[c.id] = sciezki[-1].value
        del wyrazenie
    for w in ast.walk(drzewo):
        if not (isinstance(w, ast.Compare) and len(w.ops) == 1
                and isinstance(w.ops[0], ast.In)):
            continue
        lewa, prawa = w.left, w.comparators[0]
        if (isinstance(lewa, ast.Constant) and isinstance(lewa.value, str)
                and isinstance(prawa, ast.Name) and prawa.id in zrodla):
            yield w.lineno, zrodla[prawa.id], lewa.value


KORZEN = pathlib.Path(".")
_kod_pliku: dict[str, str] = {}


def kod(sciezka: str) -> str:
    if sciezka not in _kod_pliku:
        p = KORZEN / sciezka
        _kod_pliku[sciezka] = (kod_bez_komentarzy(p.read_text(encoding="utf-8"))
                               if p.exists() else "")
    return _kod_pliku[sciezka]


def wyglada_na_kod(napis: str) -> bool:
    """Czy ten napis jest CYTATEM KODU, czy zdaniem o powodzie.

    Rozroznienie jest konieczne, bo w tym projekcie sa DWIE rozne asercje
    o tym samym ksztalcie:

      * „czy ten kod tam jest"      — i ta ma prawo oblac, gdy kod zniknal;
      * „czy powod jest zapisany"   — i ta ma przechodzic wlasnie na
        komentarzu, bo komentarz jest jej przedmiotem.

    Straznik oblewajacy na drugiej klasie zostalby wylaczony pierwszego dnia.
    Napis o kodzie ma ksztalt kodu: nawias wywolania, indeks, przypisanie albo
    kropka miedzy identyfikatorami. Zdanie po polsku nie ma nic z tego.
    """
    import re as _re
    if _re.search(r"[a-zA-Z_]\w*\s*\(", napis):        # wywolanie
        return True
    if _re.search(r"[a-zA-Z_]\w*\s*\[", napis):        # indeks
        return True
    if _re.search(r"[a-zA-Z_]\w*\s*=[^=]", napis):     # przypisanie
        return True
    if _re.search(r"\b[a-z_]\w*\.[a-z_]\w*\b", napis):  # kropka
        return True
    return False


print("=== 1. NAPIS O KODZIE MA BYC W KODZIE, NIE W KOMENTARZU ===")
tylko_w_prozie = []
o_uzasadnieniu = []
zbadane = 0
for plik in sorted(pathlib.Path("agent-v2/tests").glob("test_*.py")):
    if plik.name == pathlib.Path(__file__).name:
        continue
    for linia, cel, napis in asercje_po_zrodle(plik):
        tresc_kodu = kod(cel)
        if not tresc_kodu:
            continue
        zbadane += 1
        if napis in tresc_kodu:
            continue
        # Nie ma go w kodzie. Czy jest w pliku w ogole?
        caly = (KORZEN / cel).read_text(encoding="utf-8")
        if napis not in caly:
            continue
        opis = "%s:%d szuka %r w %s" % (plik.name, linia, napis[:44], cel)
        if wyglada_na_kod(napis):
            tylko_w_prozie.append(opis + " — kod zniknal, zostal cytat")
        else:
            o_uzasadnieniu.append(opis)

print("  zbadanych asercji: %d" % zbadane)
if o_uzasadnieniu:
    # NIE SA BLEDEM. Pilnuja, ze POWOD jest zapisany obok kodu — a to w tym
    # projekcie osobna, swiadoma praktyka. Wypisujemy je, zeby bylo widac,
    # ile ich jest i czego dotycza.
    print("  asercji pilnujacych UZASADNIENIA (komentarz jest ich przedmiotem):"
          " %d" % len(o_uzasadnieniu))
    for x in o_uzasadnieniu:
        print("      %s" % x)
sprawdz("zaden CYTAT KODU nie przezyl zniknięcia tego kodu",
        not tylko_w_prozie, "\n        " + "\n        ".join(tylko_w_prozie))

print()
print("=== 2. KONTRDOWOD: ODSIEW KOMENTARZY NAPRAWDE DZIALA ===")
# Bez tego sekcja 1 przechodzilaby takze wtedy, gdyby `kod_bez_komentarzy`
# oddawalo caly plik — a wtedy nie mierzylaby niczego.
_probka = (
    'x = 1  # tajnehaslowkomentarzu\n'
    'def f():\n'
    '    """tajnehaslowdocstringu"""\n'
    '    return "tajnehaslowkodzie"\n'
)
_kod = kod_bez_komentarzy(_probka)
sprawdz("napis z komentarza odpada", "tajnehaslowkomentarzu" not in _kod)
sprawdz("napis z docstringa odpada", "tajnehaslowdocstringu" not in _kod)
sprawdz("napis UZYTY w kodzie zostaje", "tajnehaslowkodzie" in _kod)
# I ze rozroznienie „kod czy proza" naprawde rozroznia — bez tego sekcja 1
# moglaby przechodzic dlatego, ze wszystko uznaje za proze.
sprawdz("cytat kodu rozpoznany jako kod",
        wyglada_na_kod('budzet["follow"]')
        and wyglada_na_kod("stages.discovery(conn)")
        and wyglada_na_kod('data["x"] = False'))
sprawdz("zdanie o powodzie NIE jest kodem",
        not wyglada_na_kod("najgorsze mozliwe miejsce na milczenie")
        and not wyglada_na_kod("TYLKO ADNOTACJA, nie blokada"))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
