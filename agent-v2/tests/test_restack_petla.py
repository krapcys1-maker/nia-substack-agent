"""Petla restackow: odstep ma dzielic restacki, a nie ciagnac sie po ostatnim.

Test decyzji (`test_restack.py`) sprawdza, CZY podac dalej. Ten sprawdza, co
robi petla klikajaca — a konkretnie jedna rzecz, ktora zobaczylem dopiero na
zywym przebiegu i ktorej zaden test nie lapal.

Odstep miedzy restackami to 10-30 minut i jest uzasadniony: restack wymaga
przeczytania cudzej notki, a cztery restacki w dwie minuty widac na profilu.
Tyle ze `page.wait_for_timeout(...)` stal na koncu ciala petli, a warunek
wyjscia (`restackowane >= ile`) sprawdza sie dopiero na GORZE nastepnego
obrotu. Po wykonaniu normy agent spal wiec jeszcze do polgodziny z otwarta
przegladarka i dopiero potem wychodzil.

Przy `ile=1` — czyli w typowym dodatnim przydziale, bo budzet 1-2 restacki
rozklada sie na piec przebiegow — KAZDA taka przerwa byla w calosci pusta.
W przebiegu, w ktorym to zobaczylem, blok obserwowania zostal wczesniej
odpuszczony ZE WZGLEDU NA BRAK CZASU.

Petla siedzi w Playwrightcie, wiec strona jest podstawiona. Podstawiamy tylko
to, czego petla dotyka, i liczymy przerwy dluzsze niz minuta — reszta
`wait_for_timeout` w tej funkcji to setki milisekund na ustanie sie strony.
"""
import sys

sys.path.insert(0, "agent-v2")
import browser   # noqa: E402
import config    # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


DLUGIE_MS = 60_000        # granica: przerwa "ludzka", nie techniczna


class FalszywyElement:
    def __init__(self, strona, i):
        self.strona, self.i = strona, i

    def is_visible(self):
        return True

    def count(self):
        return 1

    def scroll_into_view_if_needed(self, **k):
        pass

    def click(self, **k):
        self.strona.kliki.append(self.i)

    def type(self, tekst, **k):
        self.strona.wpisane.append(tekst)


class FalszywaLista:
    def __init__(self, strona, ile):
        self.strona, self.ile = strona, ile

    def count(self):
        return self.ile

    def nth(self, i):
        return FalszywyElement(self.strona, i)

    # `get_by_role("textbox").last` i `get_by_role("button", name="Post").last`
    @property
    def last(self):
        return FalszywyElement(self.strona, -1)

    def click(self, **k):
        self.strona.kliki.append("menu")


class FalszywaStrona:
    def __init__(self, ile_notek):
        self.ile_notek = ile_notek
        self.przerwy = []      # wszystkie wait_for_timeout w ms
        self.kliki = []
        self.wpisane = []
        self.keyboard = self

    def goto(self, *a, **k):
        pass

    def wait_for_timeout(self, ms):
        self.przerwy.append(ms)

    def get_by_role(self, rola, name=None, **k):
        if rola == "button" and name == "Restack":
            return FalszywaLista(self, self.ile_notek)
        return FalszywaLista(self, 1)

    def press(self, *a, **k):
        pass

    def close(self):
        pass


class FalszywyKontekst:
    def __init__(self, strona):
        self.strona = strona

    def new_page(self):
        return self.strona


class Nic:
    def close(self):
        pass

    def stop(self):
        pass


def przebieg(ile, ile_notek, zgody):
    """Odpala petle na podstawionej stronie. `zgody` = ile notek dostaje TAK."""
    strona = FalszywaStrona(ile_notek)
    oryg = (browser.podlacz_sie, browser.wymagaj_sesji,
            browser.naprawde_wyslac, browser._notka_przy_przycisku,
            browser.zapisz_w_dzienniku)
    browser.podlacz_sie = lambda: (Nic(), Nic(), FalszywyKontekst(strona))
    browser.wymagaj_sesji = lambda: None
    browser.naprawde_wyslac = lambda w, r: w
    browser._notka_przy_przycisku = lambda p: {"tekst": "Cudza notka o czyms.",
                                               "autor": "Ktos"}
    browser.zapisz_w_dzienniku = lambda *a, **k: None
    licznik = {"n": 0}

    def decyzja(notka):
        licznik["n"] += 1
        if licznik["n"] <= zgody:
            return {"restack": True, "sentence": "Jedno zdanie od nas.",
                    "reason": "warte"}
        return {"restack": False, "sentence": "", "reason": "nic nie wnosi"}

    try:
        w = browser.restackuj_w_kanale(ile, decyzja, wyslij=True)
    finally:
        (browser.podlacz_sie, browser.wymagaj_sesji, browser.naprawde_wyslac,
         browser._notka_przy_przycisku, browser.zapisz_w_dzienniku) = oryg
    return w, strona


print("=== 0. ODSTEP JEST NAPRAWDE DLUGI (inaczej test nic nie znaczy) ===")
dol, gora = config.ODSTEPY["restack"]
print("    ODSTEPY['restack'] = %s-%s s" % (dol, gora))
sprawdz("dolna granica to co najmniej 5 minut", dol >= 300, dol)

print()
print("=== 1. JEDEN RESTACK, NORMA WYKONANA — ZERO DLUGICH PRZERW ===")
# To jest przypadek z produkcji: dodatni przydzial z budzetu 1-2 restacki
# rozlozonego na piec przebiegow wynosi 1.
w, s = przebieg(ile=1, ile_notek=4, zgody=1)
dlugie = [p for p in s.przerwy if p > DLUGIE_MS]
sprawdz("restack sie wykonal", w["restackowane"] == 1, w)
sprawdz("ZADNEJ dlugiej przerwy po ostatnim restacku", dlugie == [], dlugie)
print("    przerwy w ms: %s" % s.przerwy)

print()
print("=== 2. DWA RESTACKI — DOKLADNIE JEDNA PRZERWA, MIEDZY NIMI ===")
# Kontrdowod dla sekcji 1: gdyby poprawka usunela odstep CALKIEM, restacki
# szlyby jeden po drugim w kilka sekund — czyli dokladnie to, przed czym
# odstep miał chronic. Test musi odroznic „nie ma po ostatnim" od „nie ma
# wcale".
w, s = przebieg(ile=2, ile_notek=6, zgody=2)
dlugie = [p for p in s.przerwy if p > DLUGIE_MS]
sprawdz("oba restacki sie wykonaly", w["restackowane"] == 2, w)
sprawdz("dokladnie JEDNA dluga przerwa (miedzy, nie po)", len(dlugie) == 1, dlugie)
sprawdz("i miesci sie w widelkach", dlugie and dol * 1000 <= dlugie[0] <= gora * 1000,
        dlugie)

print()
print("=== 3. TRZY RESTACKI — DWIE PRZERWY ===")
w, s = przebieg(ile=3, ile_notek=8, zgody=3)
dlugie = [p for p in s.przerwy if p > DLUGIE_MS]
sprawdz("trzy wykonane", w["restackowane"] == 3, w)
sprawdz("przerw jest o jedna mniej niz restackow", len(dlugie) == 2, dlugie)

print()
print("=== 4. SAME ODMOWY — MILCZENIE NIC NIE KOSZTUJE ===")
w, s = przebieg(ile=2, ile_notek=5, zgody=0)
dlugie = [p for p in s.przerwy if p > DLUGIE_MS]
sprawdz("nic nie poszlo dalej", w["restackowane"] == 0, w)
sprawdz("odmowy sa zapisane", len(w["odmowy"]) > 0, w["odmowy"])
sprawdz("i zadnej dlugiej przerwy", dlugie == [], dlugie)

print()
print("=== 5. MNIEJ NOTEK NIZ BUDZET — NIE CZEKAMY ZA NIEISTNIEJACE ===")
w, s = przebieg(ile=3, ile_notek=1, zgody=3)
dlugie = [p for p in s.przerwy if p > DLUGIE_MS]
sprawdz("jedna notka, jeden restack", w["restackowane"] == 1, w)
sprawdz("brak przerwy, bo nie ma na co czekac", dlugie == [], dlugie)

print()
print("=== 6. ILE CZASU TO ODDAJE ===")
sredni = (dol + gora) / 2
print("    przebieg z 1 restackiem: oszczedza srednio %.0f min" % (sredni / 60))
print("    dzien z 4 przebiegami:   do %.0f min mniej bezczynnej przegladarki"
      % (4 * sredni / 60))
sprawdz("oszczednosc przekracza kwadrans na przebieg", sredni / 60 > 15, sredni / 60)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
