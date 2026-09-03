# -*- coding: utf-8 -*-
"""Hamulec po serii porazek ma konczyc SWOJ blok, nie trzy nastepne.

CO SIE PSULO. `run.rytm` pyta `browser.pod_rzad_nieudanych(co)`, a ten licznik
(`browser._POD_RZAD_ZLE`) jest slownikiem po RODZAJU dzialania i globalnym dla
calego procesu — zerowanym wylacznie powodzeniem. Tymczasem
`rytm("komentarz", ...)` wolaja CZTERY bloki `run.dzien`:

    komentarze()   run.py  ~766   pisze komentarz pod cudzym artykulem
    dyskusje()     run.py  ~874   wchodzi w dyskusje pod cudza notka
    obserwuj()     run.py  ~955   klika „Follow"
    subskrybuj()   run.py  ~989   klika „Subscribe"

Trzy porazki komentarzy pod rzad konczyly wiec blok komentarzy i NATYCHMIAST
po nim trzy nastepne, ktore nie wykonaly ani jednej wlasnej proby. Obserwowanie
i subskrypcje wrecz NIE MOGA tego licznika podniesc — zapisuja sie jako
`obserwacja` i `subskrypcja` — tylko go czytaja: dziedziczyly cudza porazke
i konczyly sie w milczeniu, bo `rytm` zwracalo False przed pierwszym
klknieciem.

ILE TO KOSZTUJE. Wg pomiaru z `browser.wystaw_odpowiedz` (siedem dni: 29
wpisow `odpowiedz`, z czego 23 to komentarze pod cudzymi notkami) blok
dyskusji daje WIEKSZOSC wypowiedzi agenta — i to on gasl jako pierwszy zaraz
po bloku komentarzy. Poprawka z 31 sierpnia dolozyla do dziennika trzy nowe
klasy porazek (brak pola, brak przycisku, wyjatek), wiec ten licznik zapala
sie teraz czesciej niz dotad — wada z rzadkiej robi sie codzienna. Nic tego
nie sprawdzalo.

CO ZOSTAJE BEZ ZMIAN. Progi: 2 pod rzad podwajaja przerwe, 3 koncza blok.
Hamulec ma sens i chroni przed dobijaniem sie do padnietego Substacka —
zmieniony jest ZASIEG, nie liczba. Przy naprawde padnietym Substacku kazdy
blok wyda teraz do 3 WLASNYCH prob zamiast dziedziczyc cudze; platne sa dwa
bloki z czterech, a ocena celu kosztuje okolo 2,3 centa, czyli najgorszy
przypadek to ~0,07 USD na przebieg.

TEST NIE RUSZA SIECI ANI MODELU: wola `run.rytm` bezposrednio, z podstawionym
`stages` i wylaczonym zegarem.

BEZ PYTESTA, z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_hamulec_per_blok.py
"""
import pathlib
import sys
import types

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


ZRODLO = pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8")

# `rytm` robi `import stages as _s` W SRODKU funkcji, wiec podmiana atrybutu
# modulu nic by nie dala — trzeba podstawic wpis w `sys.modules`. Bez tego
# `odczekaj` naprawde spi 10 minut i test nigdy sie nie konczy (sprawdzone).
SPANE = []
_atrapa_stages = types.ModuleType("stages")
_atrapa_stages.losuj_odstep = lambda co: 600.0
_atrapa_stages.odczekaj = lambda co, ile: SPANE.append(round(ile))
sys.modules["stages"] = _atrapa_stages


def zbuduj_run(zrodlo, nazwa):
    """`run.py` jako osobny modul, z zerowym snem i bez zegara przebiegu."""
    m = types.ModuleType(nazwa)
    m.__dict__["__name__"] = nazwa
    m.__dict__["__file__"] = "agent-v2/run.py"
    exec(compile(zrodlo, "agent-v2/run.py", "exec"), m.__dict__)
    m.spane = SPANE
    m.zostal_czas = lambda na_co="", potrzeba_s=0.0: True
    return m


def porazki(ile, rodzaj="komentarz"):
    """Dopisuje `ile` porazek tego rodzaju do licznika serii w `browser`."""
    for _ in range(ile):
        browser._POD_RZAD_ZLE[rodzaj] = browser._POD_RZAD_ZLE.get(rodzaj, 0) + 1


def wyzeruj():
    browser._POD_RZAD_ZLE.clear()


class Przebieg:
    """Odtwarza dokladnie ten ciag wolan, ktory robi `run.dzien`.

    Jeden wspolny `rytm_stanu` na caly przebieg (tak jest w `dzien()`), bloki
    wchodza po kolei, a `dzialaj` odpowiada jednej probie: `rytm` -> akcja ->
    wynik. Bez tego test mierzylby wolania w kolejnosci, ktora w produkcji nie
    wystepuje — a wlasnie na kolejnosci stoi caly hamulec.
    """

    def __init__(self, m):
        self.m = m
        self.stan = {}
        self.m._BAZA_HAMULCA.clear()
        browser._POD_RZAD_ZLE.clear()
        SPANE.clear()

    def probuj(self, na_co, udane, co="komentarz"):
        """Jedna proba w bloku. Oddaje False, gdy hamulec zamknal blok."""
        if not self.m.rytm(co, na_co, self.stan):
            return False
        self.stan[co] = True
        browser._POD_RZAD_ZLE[co] = (0 if udane
                                     else browser._POD_RZAD_ZLE.get(co, 0) + 1)
        return True

    def wolno(self, na_co, co="komentarz"):
        """Czy blok w ogole moze zaczac/kontynuowac — bez wykonywania proby."""
        return self.m.rytm(co, na_co, self.stan)


print("=== 1. HAMULEC DZIALA — I NIE WOLNO GO ZGUBIC ===")
# Najpierw dowod, ze hamulec w ogole jest. Gdyby poprawka go rozbroila, cala
# reszta testu byla by o niczym: agent dobijalby sie do padnietego Substacka.
p = Przebieg(zbuduj_run(ZRODLO, "run_h1"))
sprawdz("pierwsza proba idzie bez przeszkod", p.probuj("komentarze", False))
sprawdz("druga tez", p.probuj("komentarze", False))
sprawdz("i przerwa jest jeszcze zwykla (600 s)", SPANE[-1] == 600, SPANE)
sprawdz("trzecia — nadal wolno, ale wolniej", p.probuj("komentarze", False))
sprawdz("bo przerwa jest PODWOJONA (600 -> 1200 s)", SPANE[-1] == 1200, SPANE)
sprawdz("czwartej juz nie ma — trzy porazki koncza blok",
        p.wolno("komentarze") is False)

print()
print("=== 2. SUKCES ZERUJE SERIE I ODBLOKOWUJE BLOK ===")
# `dopisz_wynik` zeruje licznik kazdym powodzeniem. Blok, ktory po dwoch
# porazkach dostal jeden sukces, musi liczyc od nowa — inaczej hamulec byl by
# jednorazowym wylacznikiem na caly przebieg.
p = Przebieg(zbuduj_run(ZRODLO, "run_h2"))
p.probuj("komentarze", False)
p.probuj("komentarze", False)
sprawdz("po dwoch porazkach przerwa byla podwojona", SPANE == [600], SPANE)
sprawdz("trzecia proba sie udaje", p.probuj("komentarze", True))
sprawdz("przerwa PRZED nia byla jeszcze podwojona", SPANE[-1] == 1200, SPANE)
sprawdz("wiec kolejna porazka nie konczy bloku",
        p.probuj("komentarze", False))
sprawdz("a przerwa wrocila do zwyklej — sukces wyzerowal serie",
        SPANE[-1] == 600, SPANE)
sprawdz("i jeszcze jedna sie miesci", p.probuj("komentarze", False))

print()
print("=== 3. PORAZKI JEDNEGO BLOKU NIE KONCZA NASTEPNEGO ===")
# SEDNO. Trzy nieudane komentarze koncza blok komentarzy — i tyle. Blok
# dyskusji ma wlasny licznik i zaczyna od zera, bo swoich porazek jeszcze nie
# mial. Obserwowanie i subskrypcje tym bardziej: one tego licznika nawet nie
# podnosza (zapisuja sie jako `obserwacja`/`subskrypcja`), tylko go czytaly.
p = Przebieg(zbuduj_run(ZRODLO, "run_h3"))
for _ in range(3):
    p.probuj("komentarze", False)
sprawdz("blok komentarzy sie konczy", p.wolno("komentarze") is False)
sprawdz("ale dyskusje ida dalej", p.wolno("dyskusje") is True)
sprawdz("obserwowanie idzie dalej", p.wolno("obserwowanie") is True)
sprawdz("subskrypcje ida dalej", p.wolno("subskrypcje") is True)

print()
print("=== 4. ALE WLASNE PORAZKI BLOK LICZY OD SWOJEGO WEJSCIA ===")
# Hamulec ma dzialac w kazdym bloku osobno, a nie znikac. Dyskusje, ktore po
# wejsciu zaliczyly trzy WLASNE porazki, tez musza sie skonczyc — inaczej
# przeniesienie zasiegu byloby po prostu wylaczeniem ochrony.
#
# NOWY PRZEBIEG, bo baza bloku powstaje przy jego PIERWSZYM wolaniu `rytm`.
# W `run.dzien` bloki ida po kolei i kazdy woła `rytm` dopiero wtedy, gdy
# przychodzi jego kolej — tutaj odtwarzamy dokladnie ta kolejnosc:
# komentarze (3 porazki) -> dyskusje (3 porazki) -> obserwowanie.
p = Przebieg(zbuduj_run(ZRODLO, "run_h4"))
for _ in range(3):
    p.probuj("komentarze", False)
for _ in range(3):
    p.probuj("dyskusje", False)
sprawdz("dyskusje po trzech wlasnych porazkach tez sie koncza",
        p.wolno("dyskusje") is False)
sprawdz("a obserwowanie, ktore wchodzi dopiero teraz, idzie dalej",
        p.wolno("obserwowanie") is True)
sprawdz("licznik globalny naprawde stoi na szesciu (test cokolwiek mierzy)",
        browser.pod_rzad_nieudanych("komentarz") == 6,
        browser.pod_rzad_nieudanych("komentarz"))

print()
print("=== 5. PROG NIE PRZESUWA SIE PRZEZ WLASNA PIERWSZA PROBE ===")
# Pulapka, ktora ten test wylapal w pierwszej wersji poprawki: baza zapisywana
# przy DRUGIM wolaniu `rytm` brala juz wlasna porazke bloku za cudzy dlug
# i prog przesuwal sie z trzech porazek na cztery. Baza musi powstac PRZED
# wczesnym wyjsciem („pierwsze dzialanie w przebiegu nie czeka na nic").
p = Przebieg(zbuduj_run(ZRODLO, "run_h5"))
udane_proby = sum(1 for _ in range(6) if p.probuj("komentarze", False))
print("    prob przepuszczonych, gdy KAZDA sie psula: %d" % udane_proby)
sprawdz("dokladnie trzy proby, nie cztery", udane_proby == 3, udane_proby)

print()
print("=== 6. BAZY NIE PRZECHODZA MIEDZY PRZEBIEGAMI ===")
# `dzien()` bywa wolane wiecej niz raz w jednym procesie. Baza to stan JEDNEGO
# przebiegu; nastepny ma zaczac z czystym kontem, tak jak mowi komunikat
# wycofania („nastepny przebieg sprobuje od nowa").
m6 = zbuduj_run(ZRODLO, "run_h6")
p = Przebieg(m6)
for _ in range(3):
    p.probuj("komentarze", False)
sprawdz("blok stoi na koncu przebiegu", p.wolno("komentarze") is False)
sprawdz("dzien() czysci bazy hamulca",
        "_BAZA_HAMULCA.clear()" in ZRODLO, "bazy przezyja przebieg")
p2 = Przebieg(m6)                     # tak zaczyna sie nastepny przebieg
sprawdz("nastepny przebieg zaczyna blok od nowa",
        p2.wolno("komentarze") is True)

print()
print("=== 7. KONTRDOWOD: NA KODZIE SPRZED POPRAWKI TO PRZECIEKALO ===")
# Odwrotna latka: hamulec znowu czyta licznik globalny po rodzaju.
stary_zrodlo = ZRODLO.replace(
    "    pod_rzad = _pod_rzad_w_bloku(co, na_co)\n",
    "    import browser as _b\n    pod_rzad = _b.pod_rzad_nieudanych(co)\n")
sprawdz("latka odwrotna ma co cofnac", stary_zrodlo != ZRODLO)


def po_trzech_porazkach_komentarzy(zrodlo, nazwa):
    p = Przebieg(zbuduj_run(zrodlo, nazwa))
    for _ in range(3):
        p.probuj("komentarze", False)
    return {n: p.wolno(n) for n in ("komentarze", "dyskusje",
                                    "obserwowanie", "subskrypcje")}


wynik_stary = po_trzech_porazkach_komentarzy(stary_zrodlo, "run_stary_hamulec")
print("    STARY KOD po 3 porazkach komentarzy: %s" % wynik_stary)
sprawdz("KONTRDOWOD: stary hamulec konczyl takze blok dyskusji",
        wynik_stary["dyskusje"] is False, wynik_stary)
sprawdz("KONTRDOWOD: i obserwowanie", wynik_stary["obserwowanie"] is False,
        wynik_stary)
sprawdz("KONTRDOWOD: i subskrypcje", wynik_stary["subskrypcje"] is False,
        wynik_stary)

wynik_nowy = po_trzech_porazkach_komentarzy(ZRODLO, "run_h7")
print("    NOWY KOD  po 3 porazkach komentarzy: %s" % wynik_nowy)
sprawdz("nowy kod konczy TYLKO blok, ktory sie psul",
        wynik_nowy == {"komentarze": False, "dyskusje": True,
                       "obserwowanie": True, "subskrypcje": True},
        wynik_nowy)

print()
print("=== 8. ZRODLO MOWI, DLACZEGO ===")
sprawdz("progi zostaly te same (2 i 3)",
        "pod_rzad >= 3" in ZRODLO and "pod_rzad >= 2" in ZRODLO)
sprawdz("wycofanie nadal jest slyszalne w logu", "[wycofanie]" in ZRODLO)
sprawdz("komunikat mowi, KTORY blok sie konczy",
        "koncze blok %s" in ZRODLO, "log znowu nie mowi, co zgaslo")

wyzeruj()
print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
