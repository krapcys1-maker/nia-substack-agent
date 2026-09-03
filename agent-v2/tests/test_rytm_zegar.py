"""Przerwa miedzy dzialaniami wobec zegara przebiegu.

Przebieg 28 zginal tak: systemd wyslal SIGTERM w srodku `time.sleep(5166)`
w bloku NOTEK, czyli w drugim z osmiu blokow. Szesc pozostalych — obserwowanie,
subskrypcje, komentarze, dyskusje, polubienia, restacki — nie wykonalo sie
w ogole. To samo zabilo przebieg 24. Dwa z szesciu ostatnich przebiegow.

Zlozyly sie na to dwie rzeczy i obie sa tu sprawdzane osobno:

1. `zostal_czas` pytalo „czy zostala jakakolwiek sekunda", a nie „czy starczy
   na to, co za chwile zrobie". Przepuszczalo wiec dziewiecdziesieciominutowy
   sen przy dwudziestu minutach na zegarze.

2. Przerwa byla odsypiana PO dzialaniu, wiec po ostatniej notce w bloku agent
   spal jeszcze 45-90 minut, nie majac juz czego robic. To jest DOKLADNIE ta
   sama usterka, ktora naprawilem wczesniej dla restackow (`test_restack_petla`)
   i ktorej wtedy nie poszukalem nigdzie indziej. Szukam teraz.

KONTRDOWOD. Kazdy przypadek sprawdza tez zachowanie SPRZED naprawy — inaczej
test jest lustrem i przejdzie tak samo na zepsutym kodzie.
"""
import sys
import time

sys.path.insert(0, "agent-v2")
import config    # noqa: E402
import run       # noqa: E402
import stages    # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


class Spanie:
    """Podstawiony sen: zapisuje, ile by spal, ale nie spi."""

    def __init__(self):
        self.przerwy = []

    def __call__(self, co="", ile=None):
        self.przerwy.append(float(stages.losuj_odstep(co) if ile is None else ile))

    @property
    def suma(self):
        return sum(self.przerwy)


def z_zegarem(zostalo_s, praca):
    """Uruchamia `praca` tak, jakby do konca przebiegu zostalo `zostalo_s`."""
    stary_koniec, stary_sen = run._KONIEC_CZASU, stages.odczekaj
    sen = Spanie()
    run._KONIEC_CZASU = time.time() + zostalo_s
    stages.odczekaj = sen
    try:
        return praca(), sen
    finally:
        run._KONIEC_CZASU, stages.odczekaj = stary_koniec, stary_sen


print("=== 1. LOSOWANIE ODSTEPU NIE MOZE BYC SPANIEM ===")
# Rozdzielenie jest cala podstawa naprawy: kto ma zdecydowac, czy przerwa sie
# zmiesci, musi najpierw zobaczyc liczbe. Gdyby `losuj_odstep` spalo, ten test
# trwalby czterdziesci pieciu minut — i to jest tu kontrdowod.
start = time.time()
proby = [stages.losuj_odstep("notka") for _ in range(200)]
sprawdz("losowanie jest natychmiastowe", time.time() - start < 1.0,
        "%.2f s" % (time.time() - start))
dol, gora = config.ODSTEPY["notka"]
sprawdz("i miesci sie w widelkach z configu",
        all(dol <= p <= gora for p in proby), (min(proby), max(proby)))
sprawdz("i naprawde losuje, a nie zwraca stalej", len(set(proby)) > 150,
        len(set(proby)))
sprawdz("nieznany rodzaj dostaje odstep domyslny",
        config.ODSTEP_MIEDZY_DZIALANIAMI[0]
        <= stages.losuj_odstep("czegos-takiego-nie-ma")
        <= config.ODSTEP_MIEDZY_DZIALANIAMI[1])

print()
print("=== 2. ZOSTAL_CZAS PYTA O TYLE, ILE TRZEBA ===")
_, _ = z_zegarem(1200, lambda: None)          # rozgrzewka helpera
wynik, _ = z_zegarem(1200, lambda: run.zostal_czas("notki", 5400))
sprawdz("20 min na zegarze NIE starcza na przerwe 90 min", wynik is False)
wynik, _ = z_zegarem(7200, lambda: run.zostal_czas("notki", 5400))
sprawdz("2 h na zegarze starczy", wynik is True)
# KONTRDOWOD: dokladnie to, co robil stary kod — pytanie bez wymagania.
# Musi nadal zwracac True, bo inne miejsca legalnie z tego korzystaja.
wynik, _ = z_zegarem(1, lambda: run.zostal_czas("cokolwiek"))
sprawdz("bez podanej potrzeby wystarcza jedna sekunda (stare zachowanie zyje)",
        wynik is True)
wynik, _ = z_zegarem(-5, lambda: run.zostal_czas("cokolwiek"))
sprawdz("ale po czasie juz nie", wynik is False)
run._KONIEC_CZASU = None
sprawdz("bez ustawionego konca nic nie blokujemy",
        run.zostal_czas("x", 10 ** 9) is True)

print()
print("=== 3. PIERWSZE DZIALANIE NIE CZEKA NA NIC ===")
stan = {}
wynik, sen = z_zegarem(7200, lambda: run.rytm("notka", "notki", stan))
sprawdz("pierwsza notka rusza od razu", wynik is True)
sprawdz("i nie przespala ani sekundy", sen.przerwy == [], sen.przerwy)

print()
print("=== 4. PRZERWA JEST MIEDZY DZIALANIAMI, NIE PO OSTATNIM ===")
stan = {"notka": True}
wynik, sen = z_zegarem(7200, lambda: run.rytm("notka", "notki", stan))
sprawdz("druga notka czeka", wynik is True and len(sen.przerwy) == 1, sen.przerwy)
sprawdz("i czeka tyle, ile mowi config",
        dol <= sen.przerwy[0] <= gora if sen.przerwy else False, sen.przerwy)

# ISTOTA NAPRAWY: gdy przerwa sie nie miesci, agent NIE zasypia i konczy blok.
stan = {"notka": True}
wynik, sen = z_zegarem(1200, lambda: run.rytm("notka", "notki", stan))
sprawdz("przy 20 min na zegarze blok sie konczy", wynik is False)
sprawdz("I ANI SEKUNDY SNU — to jest cala roznica wobec przebiegu 28",
        sen.przerwy == [], sen.przerwy)

print()
print("=== 5. SCENARIUSZ PRZEBIEGU 28, KROK PO KROKU ===")
# Notki 45-90 min. Zegar przebiegu to 9000 s minus 900 s zapasu = 8100 s.
# Stary kod: sprawdz (jest czas) -> wystaw -> spij 86 min -> SIGTERM.
stan = {}
przespane = []
for numer in range(1, 6):
    wynik, sen = z_zegarem(8100 - sum(przespane) - numer * config.CZAS_DZIALANIA_S,
                           lambda: run.rytm("notka", "notki", stan))
    if not wynik:
        break
    przespane.extend(sen.przerwy)
    stan["notka"] = True
sprawdz("agent zatrzymuje sie sam, zanim zegar go utnie",
        sum(przespane) <= 8100, "%.0f s snu" % sum(przespane))
sprawdz("i zdazyl wystawic wiecej niz jedna notke", numer > 1, numer)

print()
print("=== 6. ZADEN BLOK NIE ZOSTAL Z PRZERWA NA KONCU ===")
import pathlib   # noqa: E402
zrodlo = pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8")
sprawdz("run.py nie wola juz odczekaj bezposrednio",
        "stages.odczekaj(" not in zrodlo)
# Sprawdzamy KAZDY blok z osobna, bo naprawa jednego i przeoczenie reszty to
# dokladnie to, co zdarzylo sie przy restackach.
for blok in ("odpowiedzi", "notki", "komentarze", "dyskusje", "obserwowanie",
             "subskrypcje"):
    sprawdz("blok %s pyta o rytm" % blok, 'rytm_stanu)' in zrodlo
            and '"%s", rytm_stanu' % blok in zrodlo)
sprawdz("stan rytmu jest wspolny dla calego przebiegu",
        "rytm_stanu: dict[str, bool] = {}" in zrodlo)
# KONTRDOWOD dla samego testu: gdyby `rytm` nie bylo nigdzie wolane, powyzsze
# przeszloby na samych komentarzach. Wymagamy wywolan w kodzie wykonywalnym.
sprawdz("i rytm jest wolany co najmniej szesc razy",
        zrodlo.count("if not rytm(") >= 6, zrodlo.count("if not rytm("))

print()
print("=== 7. ZWLOKA PRZED PIERWSZA NOTKA TEZ PYTA ZEGAR ===")
# Naprawa siostrzana do sekcji 4: tamta zamknela sen MIEDZY notkami (rytm()
# pyta zegar przed kazda przerwa), ale ZWLOKA_PRZED_NOTKAMI to INNY time.sleep,
# w innym miejscu tej samej funkcji notki(), i mial dokladnie ta sama dziure —
# zabil jedyna zaplanowana notke przebiegu z 19.08 (proces zginal 14,5 min
# w 34-minutowa zwloke). Sprawdzane strukturalnie po AST, nie grepem: musi
# istniec 'if zostal_czas(...)' obejmujacy WLASNIE ten time.sleep(ile), a nie
# gdziekolwiek w pliku (samo istnienie zostal_czas() gdzie indziej nic nie
# mowi o TYM konkretnym wywolaniu).
import ast   # noqa: E402

drzewo = ast.parse(zrodlo)
notki_fn = next(w for w in ast.walk(drzewo)
                if isinstance(w, ast.FunctionDef) and w.name == "notki")


def _strazcy_dla(funkcja, nazwa_zmiennej):
    sleepy = [n for n in ast.walk(funkcja)
              if isinstance(n, ast.Call)
              and isinstance(n.func, ast.Attribute) and n.func.attr == "sleep"
              and len(n.args) == 1 and isinstance(n.args[0], ast.Name)
              and n.args[0].id == nazwa_zmiennej]
    if not sleepy:
        return None, []
    linia = sleepy[0].lineno
    strazcy = [n for n in ast.walk(funkcja)
               if isinstance(n, ast.If)
               and isinstance(n.test, ast.Call)
               and getattr(n.test.func, "id", "") == "zostal_czas"
               and n.body and n.body[0].lineno <= linia <= n.body[-1].end_lineno]
    return sleepy[0], strazcy


sleepy_ile, strazcy = _strazcy_dla(notki_fn, "ile")
sprawdz("blok notek ma dokladnie jeden time.sleep(ile)", sleepy_ile is not None)
sprawdz("i jest wewnatrz 'if zostal_czas(...)' — nie goly sleep",
        len(strazcy) >= 1, sleepy_ile.lineno if sleepy_ile else None)
if strazcy:
    arg = strazcy[0].test.args[0] if strazcy[0].test.args else None
    sprawdz("straznik dostaje etykiete zwiazana ze zwloka/notkami",
            isinstance(arg, ast.Constant)
            and ("notk" in arg.value or "zwlok" in arg.value), getattr(arg, "value", None))

# KONTRDOWOD: ten sam wykrywacz na SYNTETYCZNYM fragmencie starego wzorca
# (goly sleep, bez strazy) musi powiedziec "brak straznika" — inaczej test
# przeszedlby tak samo na zepsutym kodzie.
STARY_WZORZEC = '''
def notki():
    if wyslij:
        ile = 123
        print("zwloka")
        time.sleep(ile)
'''
stara_fn = next(w for w in ast.walk(ast.parse(STARY_WZORZEC))
                if isinstance(w, ast.FunctionDef) and w.name == "notki")
_, stare_strazcy = _strazcy_dla(stara_fn, "ile")
sprawdz("KONTRDOWOD: stary, nieoslonieniy wzorzec zostaje wykryty jako zly",
        len(stare_strazcy) == 0, len(stare_strazcy))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
