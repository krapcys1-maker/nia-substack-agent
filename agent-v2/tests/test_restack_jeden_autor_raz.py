# -*- coding: utf-8 -*-
"""Ten sam autor i ta sama tresc nie ida dalej DWA RAZY W JEDNYM PRZEBIEGU.

## Pomiar, ktory to wywolal

Konto NIA, 3 pazdziernika 2026, przebieg 185 (13:44-16:16). Dwa restacki tej
samej notki „Do you know where your agent's stop button is?" tego samego
autora:

    15:52:00  nasz numer 352011816  zrodlo: „... just now Do you know where..."
    16:16:35  nasz numer 352029911  zrodlo: „... 1m Do you know where..."

Wlasciciel zobaczyl to na koncie jako dwa restacki jednej rzeczy.

## Dwie przyczyny, obie tutaj

1. ODPOCZYNEK AUTORA LICZYL SIE RAZ, PRZED PETLA. Blok bierze
   `kogo_juz_restackowalismy()` na starcie i robi do `ile` restackow. W logu
   z tamtego przebiegu stoi „50 autorow odpoczywa", a w rachunku na koncu
   „0 odpoczywa" przy dwoch wystawionych — bo przy filtrowaniu drugiego
   kandydata pierwszy restack jeszcze sie nie zdarzyl.

2. ODCISK TRESCI NIOSL WIEK NOTKI. Autor wystawil ten sam tekst drugi raz,
   wiec byly to dwa rozne przyciski, a odcisk brany z kontenera zaczynal sie
   od „<autor> just now" i „<autor> 1m". Dwa rozne napisy, wiec ani
   `zrobione_odciski` w tym przebiegu, ani pamiec z dziennika nie mialy jak
   rozpoznac tej samej tresci.

BEZ PYTESTA, bez sieci, bez przegladarki. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_restack_jeden_autor_raz.py
"""
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, "agent-v2")
import browser   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# --- podstawiona strona (jak w `test_restack_petla.py`) ----------------------
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

    @property
    def last(self):
        return FalszywyElement(self.strona, -1)

    def click(self, **k):
        self.strona.kliki.append("menu")


class FalszywaStrona:
    def __init__(self, ile_notek):
        self.ile_notek = ile_notek
        self.przerwy, self.kliki, self.wpisane = [], [], []
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

    class _Mysz:
        def move(self, *a, **k):
            pass

        def wheel(self, *a, **k):
            pass

    mouse = _Mysz()

    def evaluate(self, *a, **k):
        return None

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


def przebieg(notki, ile=2, dziennik_wpisy=(), wyslij=True):
    """Odpala petle na kanale zlozonym z `notki` = [(autor, tekst kontenera)]."""
    strona = FalszywaStrona(len(notki))
    kat = Path(tempfile.mkdtemp())
    oryg = (browser.podlacz_sie, browser.wymagaj_sesji, browser.naprawde_wyslac,
            browser._notka_przy_przycisku, browser._autor_przy_przycisku,
            browser.w_rewirze, browser.DZIENNIK, browser.wymagaj_wlasciwego_konta)
    browser.podlacz_sie = lambda: (Nic(), Nic(), FalszywyKontekst(strona))
    browser.wymagaj_sesji = lambda: None
    browser.wymagaj_wlasciwego_konta = lambda page: None
    browser.naprawde_wyslac = lambda w, r: w
    browser.w_rewirze = lambda tekst: True
    browser.DZIENNIK = kat / "dziennik.jsonl"
    if dziennik_wpisy:
        browser.DZIENNIK.write_text(
            "\n".join(json.dumps(w, ensure_ascii=False) for w in dziennik_wpisy) + "\n",
            encoding="utf-8")

    def _notka(przycisk):
        autor, tekst = notki[getattr(przycisk, "i", 0) % len(notki)]
        return {"tekst": tekst, "autor": autor}

    browser._notka_przy_przycisku = _notka
    browser._autor_przy_przycisku = lambda p: {
        "autor": notki[getattr(p, "i", 0) % len(notki)][0], "uchwyt": "ktos"}

    def decyzja(notka):
        return {"restack": True, "sentence": "Jedno zdanie od nas.", "reason": "warte"}

    try:
        w = browser.restackuj_w_kanale(ile, decyzja, wyslij=wyslij)
    finally:
        (browser.podlacz_sie, browser.wymagaj_sesji, browser.naprawde_wyslac,
         browser._notka_przy_przycisku, browser._autor_przy_przycisku,
         browser.w_rewirze, browser.DZIENNIK, browser.wymagaj_wlasciwego_konta) = oryg
    wpisy = []
    if (kat / "dziennik.jsonl").exists():
        wpisy = [json.loads(l) for l in (kat / "dziennik.jsonl").read_text(
            encoding="utf-8").splitlines() if l.strip()]
    return w, wpisy


AUTOR = "The Agent Stack | AI Workflows"
TRESC = ("Do you know where your agent's stop button is? Find it the same evening"
         " you set the switch, not the night it eats your inbox.")
NOTKA_TERAZ = "%s just now %s" % (AUTOR, TRESC)
NOTKA_MINUTE = "%s 1m %s" % (AUTOR, TRESC)

print("=== 1. ODCISK NIE ZALEZY OD WIEKU NOTKI ===")
sprawdz('„just now" i „1m" daja ten sam odcisk',
        browser._odcisk_notki(NOTKA_TERAZ) == browser._odcisk_notki(NOTKA_MINUTE),
        (browser._odcisk_notki(NOTKA_TERAZ), browser._odcisk_notki(NOTKA_MINUTE)))
sprawdz('„8h" i „Subscribe" tez znikaja',
        browser._odcisk_notki("%s 8h Subscribe %s" % (AUTOR, TRESC))
        == browser._odcisk_notki(NOTKA_TERAZ))
sprawdz("inna tresc to inny odcisk",
        browser._odcisk_notki(NOTKA_TERAZ)
        != browser._odcisk_notki("%s 1m Zupelnie co innego o czym innym." % AUTOR))
# KONTRDOWOD: tresc DALEJ w notce zostaje nietknieta — „5 m" bywa trescia.
dluga = AUTOR + " 1m " + "x" * 40 + " the rover drove 5 m"
sprawdz("liczby w tresci (poza naglowkiem) zostaja",
        "5 m" in browser._odcisk_notki(dluga), browser._odcisk_notki(dluga))
sprawdz("pusty tekst to pusty odcisk", browser._odcisk_notki("") == "")

print()
print("=== 2. DWIE TE SAME NOTKI W JEDNYM PRZEBIEGU: JEDEN RESTACK ===")
w, wpisy = przebieg([(AUTOR, NOTKA_TERAZ), (AUTOR, NOTKA_MINUTE)], ile=2)
sprawdz("podane dalej dokladnie raz", w["restackowane"] == 1, w)
# Duplikat odpada juz przy SKANIE kanalu (ten sam odcisk), wiec nie trafia
# nawet do oceny — za duplikat nie placimy modelowi ani grosza.
sprawdz("duplikat nie doszedl do oceny", w["rozwazone"] == 1, w)
udane = [x for x in wpisy if x.get("rodzaj") == "restack" and x.get("udane")]
sprawdz("w dzienniku jeden udany restack", len(udane) == 1, wpisy)
sprawdz("i zapisany odcisk jest bez wieku",
        udane and udane[0].get("zrodlo") == browser._odcisk_notki(NOTKA_TERAZ),
        udane and udane[0].get("zrodlo"))

print()
print("=== 3. TEN SAM AUTOR, INNA NOTKA — TEZ RAZ NA PRZEBIEG ===")
w, _ = przebieg([(AUTOR, NOTKA_TERAZ), (AUTOR, "%s 2h Zupelnie inna mysl tego samego autora." % AUTOR)], ile=2)
sprawdz("drugi tekst tego samego autora czeka na inny dzien",
        w["restackowane"] == 1 and w.get("odpoczywa") == 1, w)

print()
print("=== 4. KONTRDOWOD: ROZNI AUTORZY IDA DALEJ NORMALNIE ===")
w, wpisy = przebieg([("Autor A", "Autor A 1m Pierwsza cudza mysl o agentach."),
                     ("Autor B", "Autor B 3h Druga cudza mysl, calkiem inna.")], ile=2)
sprawdz("dwa restacki, zero odpoczywajacych",
        w["restackowane"] == 2 and not w.get("odpoczywa"), w)

print()
print("=== 5. PAMIEC Z DZIENNIKA: STARE WPISY Z WIEKIEM NADAL BLOKUJA ===")
wczoraj = datetime.now(timezone.utc).isoformat(timespec="seconds")
stary_wpis = {"kiedy": wczoraj, "rodzaj": "restack", "udane": True, "komu": "Kto Inny",
              "zrodlo": browser.plaski(NOTKA_TERAZ)[:120]}     # postac sprzed poprawki
w, _ = przebieg([(AUTOR, NOTKA_MINUTE)], ile=1, dziennik_wpisy=[stary_wpis])
sprawdz("ta sama tresc z innym wiekiem nie wraca",
        w["restackowane"] == 0 and w.get("odpoczywa") == 1, w)

print()
print("=== 6. PROBA SUCHA LICZY TAK SAMO ===")
# Tryb sprawdzenia nie wysyla, ale MA pokazywac, co poszloby w swiat. Bez
# odpoczynku w tej galezi raport obiecywalby dwa restacki jednego autora.
w, _ = przebieg([(AUTOR, NOTKA_TERAZ),
                 (AUTOR, "%s 2h Zupelnie inna mysl tego samego autora." % AUTOR)],
                ile=2, wyslij=False)
sprawdz("proba sucha tez oddaje jeden", w["restackowane"] == 1, w)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
