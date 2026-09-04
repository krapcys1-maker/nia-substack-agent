# -*- coding: utf-8 -*-
"""Polskie wzorce bramek: co maja lapac i czego lapac NIE WOLNO.

## Po co ten test istnieje

`temat.jezyk = "Polish"` dawal bota, ktory pisze po polsku przy OSMIU
wylaczonych bramkach. Modul `jezyki.py` krzyczal o tym przy kazdym przebiegu,
wiec awaria nie byla cicha — ale nie byla tez naprawiona. Wybor jezyka
dzialal w polowie: tekst wychodzil po polsku, kontrola jakosci nie istniala.

## Dlaczego POLOWA tego pliku to zdania, ktore maja PRZEJSC

Wzorzec, ktory lapie wszystko, jest tak samo bezuzyteczny jak wzorzec, ktory
nie lapie niczego — z ta roznica, ze wyglada na dzialajacy. Przy angielskich
wzorcach to juz raz kosztowalo: moja „rownowazna" wersja `NIEISTNIEJACE_BADANIE`
lapala „in a shelf-life study at 8 stopni", czyli szczegol z karty dowodowej.

W polskim jest na to jedna konkretna pulapka i stoi nizej jako osobna sekcja:
koncowka `-lem` to NIE tylko pierwsza osoba czasownika. Tak samo konczy sie
narzednik rzeczownikow — „stolem", „cialem", „dzialem", „zespolem", „kolem",
„czolem", „poslem", „orlem". Wzorzec `\\w+lem` zlapalby wiec zdania bez ani
jednej pierwszej osoby, a takich zdan w tekscie o normach i przepisach jest
pelno.

BEZ PYTESTA, bez platnych wywolan. Uruchamiac z korzenia repozytorium.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path("agent-v2").resolve()))

import jezyki   # noqa: E402

zdane = 0
oblane = 0


def sprawdz(opis, warunek, dodatek=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % opis)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (opis, dodatek))


JEZYK = "Polish"

# (bramka, zdanie, czy_ma_zlapac)
PROBKI = [
    # --- ZMYSLONE_PRZEZYCIE -------------------------------------------
    ("ZMYSLONE_PRZEZYCIE", "Widzialem to na wlasne oczy w sklepie.", True),
    ("ZMYSLONE_PRZEZYCIE", "Widziałam etykietę z inną datą.", True),
    ("ZMYSLONE_PRZEZYCIE", "Kupilem ten produkt w zeszlym tygodniu.", True),
    ("ZMYSLONE_PRZEZYCIE", "Rozmawialem z inspektorem sanitarnym.", True),
    ("ZMYSLONE_PRZEZYCIE", "Moja żona pracuje w takim zakładzie.", True),
    ("ZMYSLONE_PRZEZYCIE", "Kiedy bylem w tamtej fabryce, linia stala.", True),
    ("ZMYSLONE_PRZEZYCIE", "Pamiętam, jak zmieniano te przepisy.", True),
    # --- i teraz to, czego lapac NIE WOLNO ----------------------------
    ("ZMYSLONE_PRZEZYCIE", "Norma zostala przyjeta jednoglosnie.", False),
    ("ZMYSLONE_PRZEZYCIE", "Producent odpowiada calym swoim majatkiem.", False),
    ("ZMYSLONE_PRZEZYCIE", "Badanie przeprowadzono zgodnie z dzialem trzecim.", False),
    ("ZMYSLONE_PRZEZYCIE", "Probka byla mierzona pod katem prostym, nie kolem.", False),
    ("ZMYSLONE_PRZEZYCIE", "Zespolem kierowal wtedy inny urzad.", False),
    ("ZMYSLONE_PRZEZYCIE", "Za stolem siedzialo pieciu przedstawicieli branzy.", False),
    ("ZMYSLONE_PRZEZYCIE", "Przepis stal sie obowiazkowy w 2019 roku.", False),

    # --- NIEISTNIEJACE_BADANIE ----------------------------------------
    ("NIEISTNIEJACE_BADANIE", "Wedlug badan produkt traci wartosc po tygodniu.", True),
    ("NIEISTNIEJACE_BADANIE", "Badania pokazuja, ze konsumenci nie czytaja etykiet.", True),
    ("NIEISTNIEJACE_BADANIE", "Naukowcy odkryli nowy szlak metaboliczny.", True),
    ("NIEISTNIEJACE_BADANIE", "Eksperci twierdza, ze norma jest za luzna.", True),
    ("NIEISTNIEJACE_BADANIE", "Z badan wynika cos przeciwnego.", True),
    # nazwane zrodlo ma przechodzic
    ("NIEISTNIEJACE_BADANIE",
     "W badaniu trwalosci przy 8 stopniach probka wytrzymala 14 dni.", False),
    ("NIEISTNIEJACE_BADANIE",
     "Raport panstwowej inspekcji z marca podaje 312 kontroli.", False),

    # --- ZASTRZEZENIE -------------------------------------------------
    ("ZASTRZEZENIE", "Moim zdaniem to rozroznienie jest sztuczne.", True),
    ("ZASTRZEZENIE", "Wydaje mi sie, ze chodzi o co innego.", True),
    ("ZASTRZEZENIE", "Podejrzewam, ze zapis powstal po jednej sprawie.", True),
    ("ZASTRZEZENIE", "To osobna kwestia i nie rozstrzyga jej ten dokument.", True),
    ("ZASTRZEZENIE", "Rozporzadzenie rozstrzyga to wprost w paragrafie 4.", False),
    ("ZASTRZEZENIE", "Zdaniem sadu przepis nie mial zastosowania.", False),

    # --- POWSCIAGLIWOSC -----------------------------------------------
    ("POWSCIAGLIWOSC", "Nie bede spekulowac, co bylo dalej.", True),
    ("POWSCIAGLIWOSC", "Nie zamierzam zgadywac liczby kontroli.", True),
    ("POWSCIAGLIWOSC", "Dokument nie podaje liczby kontroli.", False),

    # --- ZAKAZANE_OTWARCIA (kotwiczone na poczatku linii) -------------
    ("ZAKAZANE_OTWARCIA", "Odwroc opakowanie i przeczytaj sklad.", True),
    ("ZAKAZANE_OTWARCIA", "Nastepnym razem sprawdz date na wieczku.", True),
    ("ZAKAZANE_OTWARCIA", "Wiekszosc ludzi zaklada, ze data znaczy zepsucie.", True),
    ("ZAKAZANE_OTWARCIA", "Wyobraz sobie kontrole w piatek po poludniu.", True),
    ("ZAKAZANE_OTWARCIA", "Data na wieczku nie znaczy tego, co wszyscy sadza.", False),
    ("ZAKAZANE_OTWARCIA", "Inspekcja odwrocila decyzje po odwolaniu.", False),

    # --- NIBY_ZRODLO --------------------------------------------------
    ("NIBY_ZRODLO", "Podobno kontrole odbywaja sie raz na trzy lata.", True),
    ("NIBY_ZRODLO", "Szacuje sie, ze dotyczy to polowy zakladow.", True),
    ("NIBY_ZRODLO", "W jednym z badan wyszlo 40 procent.", True),
    ("NIBY_ZRODLO", "Wedlug szacunkow branzy koszt to 2 mln.", True),
    ("NIBY_ZRODLO", "Inspekcja podaje, ze kontrole odbywaja sie co trzy lata.", False),
]

print("=== 1. WZORCE LAPIA TO, PO CO ISTNIEJA ===")
for bramka, zdanie, ma_zlapac in PROBKI:
    if not ma_zlapac:
        continue
    w = jezyki.wzorzec(bramka, JEZYK)
    sprawdz("%-22s %s" % (bramka, zdanie[:44]), bool(w.search(zdanie)))

print()
print("=== 2. I NIE LAPIA TEGO, CZEGO NIE WOLNO ===")
print("    (wzorzec lapiacy wszystko jest bezuzyteczny tak samo, jak zaden —")
print("     tylko wyglada na dzialajacy)")
for bramka, zdanie, ma_zlapac in PROBKI:
    if ma_zlapac:
        continue
    w = jezyki.wzorzec(bramka, JEZYK)
    trafienie = w.search(zdanie)
    sprawdz("%-22s %s" % (bramka, zdanie[:44]), not trafienie,
            "zlapalo %r" % (trafienie.group(0) if trafienie else ""))

print()
print("=== 3. PULAPKA KONCOWKI -LEM: NARZEDNIK TO NIE PIERWSZA OSOBA ===")
# Gdyby ktos kiedys „uproscil" wzorzec do `\w+lem`, te siedem zdan zaczeloby
# byc zglaszane jako zmyslone przezycie. Kazde z nich jest zwyklym zdaniem
# o normach, a takich w tej niszy jest wiekszosc.
PULAPKA = ("stolem", "cialem", "dzialem", "zespolem", "kolem", "czolem", "poslem")
w = jezyki.wzorzec("ZMYSLONE_PRZEZYCIE", JEZYK)
for slowo in PULAPKA:
    zdanie = "Sprawa zostala rozstrzygnieta przed %s w 2019 roku." % slowo
    sprawdz("  %-10s nie jest pierwsza osoba" % slowo, not w.search(zdanie))

print()
print("=== 4. KOMPLET WOBEC ANGIELSKIEGO ===")
brak = jezyki.brakujace(JEZYK)
sprawdz("polski ma wszystkie bramki, co angielski", not brak, brak)
sprawdz("i jest na liscie znanych jezykow", JEZYK in jezyki.znane_jezyki(),
        jezyki.znane_jezyki())

print()
print("=== 5. KONTRDOWOD: NIEZNANY JEZYK NADAL KRZYCZY ===")
# Bez tego nie wiadomo, czy sekcja 1 przechodzi dlatego, ze wzorce dzialaja,
# czy dlatego, ze cokolwiek zwracaja.
w_obcy = jezyki.wzorzec("ZMYSLONE_PRZEZYCIE", "Klingon")
sprawdz("nieznany jezyk daje wzorzec, ktory nie lapie NICZEGO",
        not w_obcy.search("Widzialem to na wlasne oczy."))
# LICZBA WYPROWADZONA Z REJESTRU, NIE WPISANA. Stalo tu `== 8` — a osiem to
# byla liczba wpisow w tamtym dniu. Dopisanie dziewiatego wzorca
# (`ZWROT_DO_CZYTELNIKA`) obleło ten wiersz, mimo ze niczego nie zepsulo:
# asercja pilnowala LICZNIKA, a miala pilnowac tego, ze nieznany jezyk zglasza
# BRAK WSZYSTKIEGO. Te sama wade ma kazda inna reczna liczba w tym repo.
_ile_wpisow = len(jezyki.WZORCE["English"]) + len(jezyki.FRAZY["English"])
sprawdz("i zglasza pelny brak (%d pozycji)" % _ile_wpisow,
        len(jezyki.brakujace("Klingon")) == _ile_wpisow,
        jezyki.brakujace("Klingon"))

print()
print("=== 6. KONTRDOWOD: ANGIELSKIE WZORCE NIE LAPIA POLSKIEGO ===")
# Dowod, ze polska sekcja nie jest ozdoba: bez niej te zdania przechodzily.
w_ang = jezyki.wzorzec("ZMYSLONE_PRZEZYCIE", "English")
for zdanie in ("Widzialem to na wlasne oczy w sklepie.",
               "Moja żona pracuje w takim zakładzie."):
    sprawdz("angielski wzorzec przepuszcza %r" % zdanie[:34],
            not w_ang.search(zdanie))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
