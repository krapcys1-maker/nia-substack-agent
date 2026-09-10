# -*- coding: utf-8 -*-
"""Zaslonięty przycisk ma dostac zdarzenie, a nie kolejne trzydziesci sekund.

## Po co ten plik istnieje

Od 8 wrzesnia 2026 odpowiedzi przestaly wychodzic na konto: zero porazek przez
trzy poprzednie dni, cztery 8 wrzesnia, trzy w nocy z 8 na 9. Za kazdym razem
ten sam komunikat, slowo w slowo:

    Locator.click: Timeout 30000ms exceeded
    <div class="pencraft pc-display-flex pc-flexDirection-column ..."> …
    from <div id="entry"> … subtree intercepts pointer events

Przycisk BYL znajdowany, byl widoczny i byl wlaczony. Zaslania go panel
Substacka wewnatrz `#entry`, a Playwright — slusznie — odmawia klikniecia
w miejsce, gdzie zdarzenie dostanie kto inny. Ponawial przez trzydziesci
sekund, wiec to nie bylo migniecie: zaslona stoi.

## Czego ten test pilnuje

TRZECH rzeczy, i kazda z nich jest osobnym sposobem, w jaki taka poprawka
psuje sie po cichu:

1. Gdy nikt nie zaslania, nic sie nie zmienia — normalna droga jest pierwsza,
   a awaryjne wyjscie nie ma prawa sie wlaczyc.
2. Gdy zaslania, zdarzenie idzie NA TEN element, ktory juz mamy.
3. Kazdy INNY blad leci dalej. „Przycisku nie ma" i „przycisk zaslonily" to
   dwie rozne sprawy, a poprawka, ktora polyka pierwsza, zamienia brak
   przycisku w cicha porazke bez sladu.

## Czego tu NIE ma i dlaczego

`force=True`. To by nie naprawilo, tylko ukrylo: `force` pomija sprawdzenia
i klika w te same wspolrzedne, czyli trafia dokladnie w zaslaniajacy panel.
Dostalibysmy „klikniete" i zadnej odpowiedzi.

## DLACZEGO SEKCJA 4 NIE SZUKA JUZ NAZW ZMIENNYCH

Dwa razy z rzedu sprawdzenie po nazwie przepuscilo prawdziwe miejsce:

  * restack klikal `page.get_by_role(...).last.click(timeout=8000)` w jednej
    linii, bez zmiennej `przycisk` — testy byly zielone, restack padl na zywo;
  * publikacja ARTYKULU klikala `publikuj.click()`, a wzorzec szukal nazw
    `przycisk` i `wyslac` oraz lokatora `name="Post"`. Artykul uzywa „Send to
    everyone now". Zielono, i jedna zaslona wystarczyla, zeby wyrzucic do kosza
    caly oplacony research.

Nazwa zmiennej to najslabsza rzecz, jaka mozna sprawdzac: autor poprawki ma
pelna swobode jej wyboru, a test milczy. Wiec pytamy inaczej, ze SKLADNI:

    kazda funkcja, ktora zna nazwe przycisku ZATWIERDZAJACEGO
    (Post / Publish / Send / Reply / Restack / Save / Continue i polskie
    odpowiedniki), musi wolac `klik_mimo_zaslony`.

Nowe miejsce publikacji nie da sie dopisac bez tej nazwy — a z nazwa test
oblewa, dopoki klikniecie nie przejdzie przez helper. To jedyna wersja tego
sprawdzenia, ktorej nie da sie ominac przypadkiem.

BEZ PYTESTA, bez sieci, bez przegladarki. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_klik_mimo_zaslony.py
"""
import ast
import io
import sys

sys.path.insert(0, "agent-v2")
import browser  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# KOMUNIKAT PRZEPISANY Z PRODUKCJI, nie wymyslony. Gdyby Playwright zmienil
# to zdanie, ten test ma oblac — bo wtedy rozpoznanie po tresci przestaje
# dzialac i awaryjne wyjscie milczy dokladnie wtedy, gdy jest potrzebne.
ZASLONA = ("Locator.click: Timeout 30000ms exceeded. Call log: - waiting for"
           ' get_by_role("button", name="Post").first - <div class="pencraft'
           ' pc-display-flex pc-flexDirection-column pc-gap-8"></div> from'
           ' <div id="entry"></div> subtree intercepts pointer events'
           " - retrying click action")

INNY_BLAD = ("Locator.click: Timeout 30000ms exceeded. Call log: - waiting for"
             " element to be visible, enabled and stable")


class Zwykly:
    def __init__(self):
        self.klikniety = False

    def click(self):
        self.klikniety = True

    def evaluate(self, js):
        raise AssertionError("awaryjne wyjscie wlaczylo sie bez powodu")


class Zaslonietty:
    def __init__(self):
        self.js = None

    def click(self):
        raise Exception(ZASLONA)

    def evaluate(self, js):
        self.js = js


class Nieobecny:
    def click(self):
        raise Exception(INNY_BLAD)

    def evaluate(self, js):
        raise AssertionError("polknelismy blad, ktory nie jest zaslona")


print("=== 1. BEZ ZASLONY NIC SIE NIE ZMIENIA ===")
z = Zwykly()
droga = browser.klik_mimo_zaslony(z)
sprawdz("normalny klik wykonany", z.klikniety is True)
sprawdz("droga zapisana jako zwykla", droga == "zwykly", droga)

print()
print("=== 2. ZASLONA: ZDARZENIE IDZIE WPROST NA ELEMENT ===")
z = Zaslonietty()
droga = browser.klik_mimo_zaslony(z, "odpowiedz")
sprawdz("droga zapisana jako awaryjna", droga == "mimo zaslony", droga)
sprawdz("zdarzenie poszlo na TEN element", z.js == "el => el.click()", str(z.js))
# Wspolrzedne sa wlasnie tym, czego nie chcemy uzywac: pod nimi siedzi panel.
sprawdz("nie uzyto wspolrzednych ani force",
        "force" not in str(z.js) and "mouse" not in str(z.js), str(z.js))

print()
print("=== 3. KAZDY INNY BLAD LECI DALEJ ===")
# Poprawka, ktora polyka „przycisku nie ma", zamienia brak przycisku w cicha
# porazke bez sladu w dzienniku.
try:
    browser.klik_mimo_zaslony(Nieobecny())
    sprawdz("inny blad przekazany dalej", False, "zostal polkniety")
except AssertionError:
    raise
except Exception as exc:
    sprawdz("inny blad przekazany dalej", "visible, enabled and stable" in str(exc),
            str(exc)[:70])

print()
print("=== 4. KAZDA FUNKCJA, KTORA ZNA PRZYCISK ZATWIERDZAJACY, IDZIE PRZEZ HELPER ===")
# Pytanie zadane SKLADNI, nie nazwom zmiennych. Patrz naglowek pliku: dwie
# wczesniejsze wersje tego sprawdzenia szukaly nazw i dwa razy przepuscily
# prawdziwe miejsce.
ZATWIERDZAJA = ("Post", "Publish", "Send", "Reply", "Restack", "Save",
                "Continue", "Subscribe",
                "Opublikuj", "Odpowiedz", "Zapisz", "Kontynuuj",
                "Wyslij", "Wyślij", "Subskrybuj")

zrodlo = io.open("agent-v2/browser.py", encoding="utf-8").read()
drzewo = ast.parse(zrodlo)


def zna_przycisk(fn):
    """Czy w ciele funkcji pada nazwa przycisku, ktory cos ZATWIERDZA."""
    for w in ast.walk(fn):
        if isinstance(w, ast.Constant) and isinstance(w.value, str):
            t = w.value
            if any(t == s or t.startswith(s + " ") for s in ZATWIERDZAJA):
                return t
    return None


def przez_helper(fn):
    return any(isinstance(w, ast.Call) and isinstance(w.func, ast.Name)
               and w.func.id == "klik_mimo_zaslony" for w in ast.walk(fn))


# Sam helper zna slowo „Post" wylacznie z wlasnego opisu bledu i klika na goło
# z definicji — to jest ta normalna droga, ktora probujemy najpierw.
POZA_REGULA = {"klik_mimo_zaslony"}


def klika(fn):
    """Czy funkcja NAPRAWDE klika — golym `.click` albo przez helper.

    Sam `.click` przestal wystarczac 10 wrzesnia 2026. `wystaw_komentarz`
    klikalo wtedy DWA razy w to samo pole: raz u siebie, raz w srodku
    `wpisz_w_puste_pole`, ktore czysci pole przed pisaniem. Zbedne klikniecie
    poszlo, w funkcji nie zostal zaden goly `.click` — i ta regula przestala
    ja widziec, choc przycisk „Post" nadal klika, tyle ze przez helper.

    Wynik byl gorszy niz oblany test: `wystaw_komentarz` wypadlo z listy
    OBJETYCH i trafilo miedzy posrednikow, czyli regula przestala jej
    pilnowac. Straznik, ktory milknie przy poprawce, jest gorszy od braku
    straznika, bo wyglada na spelniony.
    """
    return any((isinstance(w, ast.Attribute) and w.attr == "click")
               or (isinstance(w, ast.Call) and isinstance(w.func, ast.Name)
                   and w.func.id == "klik_mimo_zaslony")
               for w in ast.walk(fn))


winne = []
objete = []
posrednicy = []
for fn in [n for n in ast.walk(drzewo) if isinstance(n, ast.FunctionDef)]:
    if fn.name in POZA_REGULA:
        continue
    etykieta = zna_przycisk(fn)
    if etykieta is None:
        continue
    # FUNKCJA, KTORA ZNA ETYKIETE, ALE SAMA NIE KLIKA, tylko podaje ja dalej
    # (`zasubskrybuj` → `_klik_na_profilu`). Zadanie helpera od niej byloby
    # zadaniem czegos, czego nie robi. Klikacz, do ktorego deleguje, jest
    # sprawdzany osobno nizej — po nazwie, bo etykiety dostaje ARGUMENTEM
    # i ta regula sama z siebie nigdy by tam nie zajrzala.
    if not klika(fn):
        posrednicy.append(fn.name)
        continue
    objete.append(fn.name)
    if not przez_helper(fn):
        winne.append("%s (linia %d, %r)" % (fn.name, fn.lineno, etykieta))

sprawdz("zadna funkcja z przyciskiem zatwierdzajacym nie klika na golo",
        not winne, "; ".join(winne))
# KONTRDOWOD DLA SAMEJ REGULY: gdyby wykaz nazw przestal cokolwiek lapac
# (literowka, zmiana slownictwa Substacka), sprawdzenie wyzej przechodziloby
# zawsze i nie pilnowaloby niczego.
sprawdz("regula obejmuje wszystkie sciezki publikacji",
        len(objete) >= 8, "objetych funkcji: %d — %s" % (len(objete), objete))
for musi in ("wystaw_notke", "wystaw_komentarz", "wystaw_odpowiedz",
             "wystaw_artykul", "restackuj_w_kanale"):
    sprawdz("objeta: %s" % musi, musi in objete, str(objete))

# KLIKACZ, KTORY DOSTAJE ETYKIETY ARGUMENTEM. `_klik_na_profilu` klika
# „Subscribe" i „Follow", ale nie ma tych slow w swoim ciele — przychodza
# z `zasubskrybuj` i `obserwuj`. Regula po etykiecie jest tu slepa z zalozenia,
# wiec pytamy o niego wprost.
z_argumentem = [n for n in ast.walk(drzewo)
                if isinstance(n, ast.FunctionDef) and n.name == "_klik_na_profilu"]
sprawdz("klikacz profilu istnieje", len(z_argumentem) == 1, str(len(z_argumentem)))
sprawdz("klikacz profilu tez idzie przez helper",
        bool(z_argumentem) and przez_helper(z_argumentem[0]),
        "nie wola klik_mimo_zaslony")
sprawdz("posrednicy rozpoznani, nie oskarzeni",
        "zasubskrybuj" in posrednicy, str(posrednicy))

print()
print("=== 5. DROGA TRAFIA DO DZIENNIKA ===")
# Bez tego nie da sie zauwazyc dnia, w ktorym Substack zdejmie zaslone — ani
# dnia, w ktorym zaslona pojawi sie wszedzie.
sprawdz("droga zapisywana przy publikacjach",
        zrodlo.count("droga_klikniecia") >= 6,
        "wystapien: %d" % zrodlo.count("droga_klikniecia"))
sprawdz("helper wolany co najmniej dziesiec razy",
        zrodlo.count("klik_mimo_zaslony(") >= 10,
        "wystapien: %d" % zrodlo.count("klik_mimo_zaslony("))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
