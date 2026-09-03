"""Dokumentacja odtworzeniowa ma byc GENEROWANA, nie przepisywana.

Dokument JAK_ZBUDOWANY_JEST_BOT.md mowil o sobie w czterech miejscach:

    "Wygenerowany ze zrodel przez `ast`, wiec nie da sie go rozjechac z kodem."

Nic tego nie generowalo. `sklej.py` importowal wylacznie `pathlib` i `sys`,
a slowo `ast` wystepowalo w nim TYLKO wewnatrz naglowkow wpisywanych do
dokumentu — bylo twierdzeniem w tresci, nie kodem. Cztery czesci mechaniczne
byly zamrozonymi zrzutami i rozjechaly sie z kodem w ciagu trzech dni: nie
bylo w nich ani `rytm`, ani `losuj_odstep`, ani `_stale_sygnaly`, ani nowego
poziomu dlugosci THIN.

To jest ta sama klasa wady, ktora scigamy w agencie — obietnica bez pokrycia,
czytana jak gwarancja — tyle ze w dokumencie, ktorego CALY sens polega na tym,
zeby dalo sie z niego odtworzyc bota.

NAJWAZNIEJSZA ASERCJA jest ostatnia: zlozenie dokumentu na nowo nie moze
niczego zmienic. Jesli zmienia — dokument w repozytorium jest starszy niz kod
i ktos zapomnial go przebudowac.
"""
import pathlib
import subprocess
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


SKLEJ = pathlib.Path("agent-v2/dokumentacja-zrodla/sklej.py")
PAPER = pathlib.Path("agent-v2/JAK_ZBUDOWANY_JEST_BOT.md")
sklej_src = SKLEJ.read_text(encoding="utf-8")

print("=== 1. GENERATOR NAPRAWDE GENERUJE ===")
sprawdz("sklej.py importuje ast", "\nimport ast" in sklej_src)
# KONTRDOWOD dla poprzedniej wersji: samo slowo `ast` w pliku nic nie znaczylo,
# bo stalo w napisie wpisywanym do dokumentu. Wymagamy UZYCIA.
sprawdz("i naprawde go uzywa, nie tylko wspomina",
        "ast.parse(" in sklej_src and "ast.get_source_segment(" in sklej_src)
sprawdz("czyta pliki .py z katalogu agenta", 'AGENT.glob("*.py")' in sklej_src)
sprawdz("i katalog promptow", "PROMPTY_KAT.glob" in sklej_src)
for czesc in ("moduly.md", "stale.md", "kod.md", "prompty.md",
              "zalacznik_prompty.md"):
    sprawdz("generuje %s" % czesc, '"%s"' % czesc in sklej_src)

print()
print("=== 2. NIC NIE ZNIKA PO CICHU ===")
# Modul, ktorego nie ma w spisie, MUSI zostac zgloszony. Cicho pominiety modul
# to ten sam blad co przedtem, tylko wolniejszy.
sprawdz("nieznany modul jest zglaszany", "nie ma go w spisie MODULY" in sklej_src)
sprawdz("znikniona funkcja z KOD_DOSLOWNIE tez",
        "takiej funkcji juz nie ma" in sklej_src)
sprawdz("i ostrzezenia zmieniaja kod wyjscia", "if ostrzezenia:" in sklej_src)

# Kazdy modul .py agenta ma byc w spisie — inaczej wypada z dokumentacji.
import importlib.util   # noqa: E402
spec = importlib.util.spec_from_file_location("sklej", SKLEJ)
sklej = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sklej)
wymienione = {n for n, _ in sklej.MODULY}
istniejace = {p.name for p in pathlib.Path("agent-v2").glob("*.py")}
sprawdz("kazdy modul agenta jest w spisie", istniejace <= wymienione,
        sorted(istniejace - wymienione))
sprawdz("i spis nie wymienia plikow, ktorych nie ma", wymienione <= istniejace,
        sorted(wymienione - istniejace))
# Kazda funkcja z KOD_DOSLOWNIE musi istniec.
brakujace = [w for w in sklej.KOD_DOSLOWNIE
             if sklej._zrodlo_funkcji(*w.split(".", 1)) is None]
sprawdz("kazda funkcja z KOD_DOSLOWNIE istnieje", not brakujace, brakujace)

print()
print("=== 3. DOKUMENT W REPOZYTORIUM JEST AKTUALNY ===")
# To jest cala pointa. Skladamy na nowo i porownujemy z tym, co lezy w repo.
# TEST NIE ZMIENIA REPOZYTORIUM. `sklej.py` pisze prosto do sledzonych plikow —
# i nie tylko do dokumentu koncowego, ale takze do KAZDEJ czesci mechanicznej w
# `dokumentacja-zrodla/`. Samo sprawdzenie zostawialo wiec brudne drzewo, a na
# serwerze brudne drzewo BLOKUJE NASTEPNE WDROZENIE (`git merge --ff-only`
# odmawia). Zdarzylo sie to 30 sierpnia: testy przeszly 52/52 i tym samym
# uniemozliwily wgranie kolejnej wersji, bo odbudowaly dokumentacje.
#
# Wykrywamy nieaktualnosc i PRZYWRACAMY stan sprzed — wszystkich plikow, nie
# jednego. Odbudowa jest robota czlowieka przed commitem, nie skutkiem ubocznym
# testu. Liste bierzemy z samego generatora, zeby nie rozjechala sie, gdy ktos
# dolozy nowa czesc.
_dotykane = [PAPER] + [sklej.KAT / n for n in sklej.GENERATORY]
_kopie = {p: p.read_text(encoding="utf-8") for p in _dotykane if p.exists()}

przed = PAPER.read_text(encoding="utf-8")
wynik = subprocess.run([sys.executable, str(SKLEJ)],
                       capture_output=True, text=True)
po = PAPER.read_text(encoding="utf-8")

_zmienione = [p.name for p, tresc in _kopie.items()
              if p.read_text(encoding="utf-8") != tresc]
for p, tresc in _kopie.items():
    if p.read_text(encoding="utf-8") != tresc:
        p.write_text(tresc, encoding="utf-8")
sprawdz("skladanie konczy sie bez ostrzezen", wynik.returncode == 0,
        wynik.stdout[-400:])
sprawdz("przebudowa NICZEGO nie zmienia — dokumentacja jest aktualna",
        not _zmienione,
        "nieaktualne: %s; uruchom: python agent-v2/dokumentacja-zrodla/sklej.py"
        % ", ".join(_zmienione))

print()
print("=== 4. TRESC ODPOWIADA DZISIEJSZEMU KODOWI ===")
# Kilka rzeczy, ktorych w starym dokumencie NIE BYLO, choc byly juz w kodzie.
# Gdyby generator dzialal pozornie, te asercje by tego nie przepuscily.
for co, gdzie in (("def rytm", "run.rytm"), ("losuj_odstep", "stages.losuj_odstep"),
                  ("_stale_sygnaly", "stages._stale_sygnaly"),
                  ("ostatnie_domeny", "stages.discovery")):
    sprawdz("dokument zna %s" % gdzie, co in po, co)
sprawdz("i zna poziom dlugosci THIN", '"THIN":' in po)
# Prompty maja byc te, ktore naprawde dostaje model.
skaut = pathlib.Path("agent-v2/prompts/skaut.md").read_text(encoding="utf-8")
probka = [l for l in skaut.splitlines() if len(l.strip()) > 60][3]
sprawdz("zalacznik promptow ma aktualna tresc skauta", probka.strip() in po,
        probka[:70])

print()
print("=== 5. TEN SAM WYNIK NA KAZDYM SYSTEMIE ===")
# Bylo `sorted(PROMPTY_KAT.glob("*.md"))`, czyli sortowanie obiektow Path.
# Na Windowsie porownuja sie one BEZ UWZGLEDNIENIA WIELKOSCI LITER, na Linuksie
# z uwzglednieniem — wiec ten sam generator dawal dwa rozne dokumenty na dwoch
# maszynach. Test „przebudowa niczego nie zmienia" przechodzil lokalnie
# i oblewal na serwerze, co jest najgorszym rodzajem testu: takim, ktory uczy,
# ze czerwony wynik to pewnie srodowisko.
sprawdz("prompty sortuja sie po nazwie jako napisie, nie po Path",
        "key=lambda f: f.name" in sklej_src)
nazwy = [n for n, _ in sklej._prompty()]
sprawdz("i wynik jest posortowany wlasnie tak", nazwy == sorted(nazwy), nazwy[:4])
# KONTRDOWOD: gdyby porzadek zalezal od wielkosci liter, pliki PISANE WERSALIKAMI
# wyladowalyby w innym miejscu niz reszta. Sprawdzamy, ze siedza na poczatku,
# czyli tam, gdzie stawia je porzadek ASCII — jednakowo wszedzie.
wersaliki = [n for n in nazwy if n[0].isupper()]
sprawdz("pliki WERSALIKAMI stoja na poczatku, jak w ASCII",
        bool(wersaliki) and nazwy[:len(wersaliki)] == wersaliki, nazwy[:6])

print()
print("=== 6. PLIK, KTOREGO KOD NIE CZYTA, NIE UDAJE PROMPTU ===")
# Cztery pliki w prompts/ nie sa wolane znikad. Dokument przedstawial je jako
# „prompty robocze" z adnotacja „pola wejsciowe: brak" — czyli kazdy
# odtwarzajacy bota szukalby miejsca, w ktorym sa wolane. Nie ma takiego.
czytane = sklej._czytane_przez_kod()
nieczytane = [n for n in nazwy if n not in czytane]
sprawdz("generator odroznia czytane od nieczytanych", bool(czytane))
if nieczytane:
    sprawdz("i dokument nazywa je osobno",
            "A.2. Pliki w `prompts/`, ktorych kod NIE czyta" in po)
    for n in nieczytane:
        sprawdz("  %s jest w sekcji A.2, nie wsrod promptow" % n,
                ("`prompts/%s` (" % n) in po)
# KONTRDOWOD: plik, ktory kod NAPRAWDE czyta, nie moze wpasc do A.2.
sprawdz("prompt uzywany zostaje wsrod roboczych",
        "skaut.md" in czytane, sorted(czytane)[:5])

print()
print("=== 7. ROZDZIALY RECZNE NIE POKAZUJA KODU, KTOREGO KOD ZAKAZUJE ===")
# Sekcje mechaniczne sa generowane i rozjechac sie nie moga. Rozdzialy
# analityczne sa pisane recznie — i wlasnie one starzeja sie po cichu.
#
# Piec wydrukow w rozdziale IV pokazywalo `stages.odczekaj(...)` na koncu petli,
# czyli przerwe PO dzialaniu. Odtworzenie ich literalnie daje kod, ktory po
# ostatniej notce spi jeszcze 45-90 minut i zasypia bez pytania, czy sen sie
# zmiesci — te dwie wady uciely przebiegi 24, 28, 30 i 34.
#
# Wydruk, ktory NIE PRZESZEDLBY testow tego repozytorium, nie ma prawa stac
# w dokumencie uczacym, jak ten kod napisac.
RECZNE = sorted(pathlib.Path("agent-v2/dokumentacja-zrodla").glob("rozdzial_*.md"))
RECZNE += [pathlib.Path("agent-v2/dokumentacja-zrodla/wstep.md"),
           pathlib.Path("agent-v2/dokumentacja-zrodla/wady.md")]
sprawdz("rozdzialy reczne istnieja", len(RECZNE) >= 5, len(RECZNE))

# (wzorzec, dlaczego zakazany, gdzie stoi prawda)
ZAKAZANE = [
    ('                stages.odczekaj(',
     "przerwa PO dzialaniu w petli bloku — tak zginely cztery przebiegi",
     "run.rytm, wolany PRZED dzialaniem"),
    ('def zostal_czas(na_co: str = "") -> bool:',
     "sygnatura bez `potrzeba_s` — bez niej rytm nie ma jak zapytac,"
     " czy przerwa sie zmiesci",
     "run.py:141"),
    ("    if zostalo > 0:",
     "stary warunek: „czy zostala jakakolwiek sekunda\" zamiast"
     " „czy starczy na to, co za chwile zrobie\"",
     "run.zostal_czas"),
    ("tylko przy `--wyslij`",
     "okladka powstaje w kazdym przebiegu, przed galezia publikacji",
     "run.py:1134"),
]
znalezione = []
for plik in RECZNE:
    if not plik.exists():
        continue
    tresc = plik.read_text(encoding="utf-8")
    for wzorzec, powod, prawda in ZAKAZANE:
        if wzorzec in tresc:
            znalezione.append("%s -> %r (%s; prawda: %s)"
                              % (plik.name, wzorzec[:44], powod, prawda))
sprawdz("zaden rozdzial reczny nie pokazuje zakazanego wzorca",
        not znalezione, znalezione[:3])

# KONTRDOWOD dla samego testu: wzorce musza byc takie, ktore DA SIE znalezc.
# Test szukajacy czegos, czego nigdy nie bylo, przechodzi zawsze i nie chroni
# przed niczym. Sprawdzamy je na tresci, ktora je zawiera.
udawany = "\n".join(w for w, _, _ in ZAKAZANE)
zlapane = sum(1 for w, _, _ in ZAKAZANE if w in udawany)
sprawdz("wykrywacz lapie wszystkie cztery wzorce na probce",
        zlapane == len(ZAKAZANE), "%d z %d" % (zlapane, len(ZAKAZANE)))

# Sekcja VII jest generowana, wiec TAM te wzorce moga wystapic tylko wtedy,
# gdy sa w kodzie. Sprawdzamy, ze nie sa.
run_src = pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8")
sprawdz("i sam kod ich nie zawiera",
        "stages.odczekaj(" not in run_src and "if zostalo > 0:" not in run_src)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
