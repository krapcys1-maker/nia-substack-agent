# -*- coding: utf-8 -*-
"""Zaden prompt nie moze UCZYC na przykladach z epoki przedmiotow.

DLACZEGO TO POWSTALO. Konto przestawiono na AI 25 sierpnia i wtedy „przejrzano
wszystkie prompty". 30 sierpnia okazalo sie, ze osiem plikow nadal uczy modelu
na lotnictwie, konklawe, stacji benzynowej, szkolnym autobusie, anodzie na
kadlubie statku i symbolu otwartego sloika. Recznego przegladu nie da sie
powtarzac w kolko, wiec pilnuje tego test.

DLACZEGO TO GROZNE. Model nasladuje PRZYKLAD, nie regule. `restack.md` mowil
wprost, ze paralela z butelki szamponu jest poza tematem — i trzy akapity nizej
dawal jako wzorzec zdanie o regulacjach kosmetycznych. Zywy przebieg
wyprodukowal wtedy paralele o kremie nawilzajacym. Regula byla poprawiona,
przyklady nie.

CO STRAZNIK PRZEOCZYL ZA PIERWSZYM RAZEM (1 wrzesnia, znalezisko dziesiate).
Dwie dziury, obie zamkniete tutaj:

1. SKANOWAL WYLACZNIE `prompts/*.md`. Tymczasem `NOTE_FORMS` z `config.py`
   trafia do promptu notki jako `{form_brief}` i jest promptem w kazdym sensie
   oprocz rozszerzenia pliku. Siedzialy tam trzy formy z epoki przedmiotow
   (butelka w lazience, swiatlo na skrzyzowaniu, numer patentu jako zaczep) —
   3 z 8 pozycji `NOTE_FORM_MIX`, czyli okolo 37% wystawianych notek. Teraz
   `NOTE_FORMS` jest skanowane tak samo jak plik.

2. SZUKAL PODCIAGIEM. „oven" jako podciag lapie „provenance" i „unproven",
   ktore wystepuja w czterech miejscach zupelnie legalnie, wiec slowa tej klasy
   w ogole nie dalo sie dodac. Dopasowanie chodzi teraz po granicy slowa (z
   dopuszczona koncowka liczby mnogiej), dzieki czemu „oven" lapie zegar w
   piekarniku, a nie lapie proweniencji — i przy okazji „tuna" przestalo grozic
   zlapaniem „tunable".

CO JEST DOZWOLONE. Zapisy o WLASNYCH PORAZKACH zostaja i maja zostac: artykul o
symbolu otwartego sloika naprawde powstal i naprawde byl zly, stara regula
grafiki naprawde dala laptop na szarym papierze, a notka naprawde skonczyla sie
odeslaniem czytelnika do okolnika FAA. One ucza, czego NIE robic, i same sie
uniewazniaja. Dlatego kazde takie miejsce jest tu wypisane z osobna — lista
wyjatkow ma byc krotka i widoczna, zeby nikt nie dopisal do niej nowego
przykladu uczacego pod pozorem historii.

CO STRAZNIK PRZEOCZYL ZA DRUGIM RAZEM (1 wrzesnia, kontrola po poprawce).
Trzy rzeczy, wszystkie zamkniete tutaj:

1. `clock` STAL NA LISCIE JAKO FRAZA DWUWYRAZOWA („mains clock"), wiec gole
   `clock` przechodzilo bez sladu — a `warto_pisac.md:140` podawalo modelowi
   POZYTYWNY wzorzec z epoki przedmiotow: „A case where the same event-triggered
   clock governs something in an unrelated industry" jako odpowiedz na pole
   `what_would_rescue_it`. Nie zakaz, nie kontrprzyklad — modelowy przyklad
   dobrej paraleli. Na liscie stoi teraz samo `clock`; „mains clock" bylo jego
   podzbiorem, wiec zniknelo bez straty.

2. `_wzorzec("shelf")` dawal `shelfs?|shelfes?` i nie lapal nieregularnej
   „shelves" — a poprzednia wersja tego testu ASERTOWALA „the shelves of a
   model registry" jako niewinne, czyli zapisywala ta slepa plame jako cecha.
   Wzorzec obsluguje teraz -f/-fe → -ves. Cena jest swiadoma: prompt, ktory
   naprawde potrzebuje „shelves", musi dostac widoczny wpis w WYJATKI — i to
   jest cala konstrukcja tego straznika.

3. `fedreg.md` WROCIL DO SKANOWANIA. Byl zawieszony w calosci, bo „caly prompt
   jest z epoki przedmiotow", a decyzja o losie korpusu Federal Register nalezy
   do wlasciciela. Zawieszenie bylo uczciwe i przez to plik gnil: uczyl na
   „the price on your ticket" i „the bill for your call-out", czyli dokladnie
   na zdaniach, ktore przepisano juz w `ciekawostki.md`. Przyklady przepisano
   na ere AI, wiec plik przechodzi sekcje 1 na normalnych zasadach. Decyzja o
   losie samego korpusu nadal nalezy do wlasciciela — ale nie wymaga trzymania
   gnijacego promptu.

CZEGO TEN TEST CELOWO NIE ZABRANIA. Slowa „patent" nie ma na liscie, choc
padalo w zgloszeniu. W obu miejscach, gdzie wystepuje, jest ZAKAZEM albo
wyliczeniem typow zrodel: `dyskoveria.md` wymienia patent wsrod dokumentow
pierwotnych, a `NOTE_FORMS["LICZBA"]` mowi, ze numer patentu NIE jest liczba,
ktora wolno otworzyc notke. Zakaz nie uczy ksztaltu. Z tego samego powodu na
liscie stoi „your ticket", a nie samo „ticket": `cele.md` wymienia „concert
ticket fees" jako przyklad postu, pod ktorym NIE komentujemy.

BEZ PYTESTA. Serwer go nie ma. Plik uruchamia sie z korzenia repozytorium.
"""
import pathlib
import re
import sys

sys.path.insert(0, "agent-v2")
import config   # noqa: E402


def _re_escape_ze_zawijaniem(fraza: str) -> str:
    # Docstring SUROWY (r"""), bo `\s` w opisie to niepoprawna sekwencja
    # ucieczki: Python zglasza SyntaxWarning przy kazdym parsowaniu tego
    # pliku, takze w skanach CI, gdzie tonie w nim prawdziwy komunikat.
    r"""Wzorzec na fraze, ktora moze byc przecieta koncem linii.

    `\s+`, NIE spacja. Prompty sa lamane na 79 znakow, wiec nazwa niszy bywa
    rozdzielona nowa linia — pierwsza wersja tego testu oblewala na prompcie,
    ktory temat nazywal poprawnie, tylko w dwoch wierszach.
    """
    return r"\s+".join(re.escape(s) for s in fraza.split())

def _napisy_instrukcyjne(wartosc, klucz: str = ""):
    """Napisy wygladajace na instrukcje dla modelu, z dowolnie zagniezdzonej
    stalej — razem ze sciezka, pod ktora leza.

    Prog czterdziestu znakow i spacji odsiewa identyfikatory, sciezki, nazwy
    modeli i stawki, a przepuszcza kazde zdanie po angielsku. Falszywe
    trafienie kosztuje jeden wpis w WYJATKI; przeoczenie kosztuje polecenie
    z poprzedniej niszy idace do modelu przy kazdej notce.
    """
    if isinstance(wartosc, str):
        if len(wartosc) > 40 and " " in wartosc:
            yield klucz, wartosc
    elif isinstance(wartosc, dict):
        for k, v in wartosc.items():
            yield from _napisy_instrukcyjne(v, "%s[%s]" % (klucz, k))
    elif isinstance(wartosc, (list, tuple)):
        for i, v in enumerate(wartosc):
            yield from _napisy_instrukcyjne(v, "%s[%d]" % (klucz, i))


def _na_zdania(tekst: str) -> list[str]:
    """Brief na zdania, zeby wyjatek zakrywal zdanie, a nie caly brief.

    Tniemy po kropce, wykrzykniku i znaku zapytania ORAZ po zlamaniu linii —
    briefy uzywaja obu. Puste kawalki odpadaja; nic wiecej sie nie dzieje,
    bo skan i tak szuka fraz, a nie zdan poprawnych gramatycznie.
    """
    return [c.strip() for c in re.split(r"(?<=[.!?])\s+|\n+", tekst or "")
            if c.strip()]


PROMPTY = pathlib.Path("agent-v2/prompts")

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# SLOWNICTWO POPRZEDNIEJ EPOKI — JEDNO ZRODLO DLA DWOCH KONTROLI.
#
# Lista stala tutaj i DRUGA, wlasna, stala w `audyt_tematow.py`. Ta miala sto
# pozycji, tamta osiem. Audyt tematow przepuszczal wiec dziedzine, ktora ten
# test by zatrzymal — a obie kontrole swiecily na zielono niezaleznie od
# siebie, wiec nic tego nie pokazywalo. To ta sama wada, co uchwyt konta
# w dwoch stalych: dwie kopie jednej rzeczy rozjezdzaja sie zawsze.
#
# Lista mieszka teraz w `narzedzia/dawne_slownictwo.py`, razem z powodem
# istnienia kazdej pozycji. `wszystkie()` doklada do niej opcjonalny plik
# operatora, wiec konto z INNA poprzednia epoka moze podac swoja.
sys.path.insert(0, "narzedzia")
import dawne_slownictwo                                          # noqa: E402

SPRZED_PRZESTAWIENIA = list(dawne_slownictwo.wszystkie())

# Miejsca, gdzie takie slowo stoi CELOWO. Klucz to etykieta zrodla (nazwa
# pliku promptu albo `config.py:NOTE_FORMS[...]`), wartosc to fragmenty linii,
# ktore wolno przepuscic.
WYJATKI = {
    # WYJATEK GRAFIKI ZDJETY W CALOSCI 4 wrzesnia. `grafika.md` opisuje stara
    # regule dalej — i ma opisywac, zeby jej nikt nie przywrocil — ale robi to
    # przez RODZAJ tematu („publikacja, ktorej tematem BYL sam przedmiot")
    # zamiast przez nazwe poprzedniej niszy. Zapis porazki nie potrzebuje nazwy
    # produktu, zeby uczyc; potrzebuje powodu, dla ktorego regula przestala
    # dzialac. To jest ten sam ruch, co przy `wykonalnosc.md` nizej.
    #
    # WYJATEK RESTACKA ZDJETY TEGO SAMEGO DNIA i to byla powazniejsza sprawa.
    # Stalo tam „a parallel drawn from shampoo bottles or insurance policies is
    # off the subject" — czyli prompt wymienial z nazwy dziedziny, z ktorych
    # NIE WOLNO brac paraleli. Dla konta o ubezpieczeniach ten sam prompt
    # zakazywalby dokladnie wlasciwych paraleli. Akapit sklada sie teraz
    # z `{nisza}`, `{kat_redakcyjny}` i przykladow z konfiguracji.
    # Zapisy wlasnej porazki w `synteza.md` i `warto_pisac.md` (artykul,
    # ktory trzeba bylo skasowac) zniknely 2026-09-05 razem z reszta historii
    # poprzedniego konta w promptach — wiec i wyjatki na nie zniknely.
    # Wyjatek zdjety: `wykonalnosc.md` opisuje te sama porazke bez nazwy
    # produktu („jedno oznaczenie na jednym produkcie"), wiec nie potrzebuje
    # juz przepustki na slownictwo poprzedniej niszy.
    # Zapis wpadki w `NOTE_FORMS[ZACZEP_I_KONKRET]` (odeslanie czytelnika do
    # nazwanego okolnika) zniknal 2026-09-05 razem z reszta historii
    # poprzedniego konta; zostal sam zakaz pracy domowej z kanalu.
}

# Pliki wylaczone ze skanu sekcji 1 — z nazwy i z powodem.
#
# PUSTE OD 1 WRZESNIA. Stal tu `fedreg.md`, zawieszony w calosci jako „caly
# prompt z epoki przedmiotow, czeka na decyzje wlasciciela o korpusie Federal
# Register". Powod zawieszenia byl prawdziwy, a skutek taki, ze plik gnil:
# jeszcze 1 wrzesnia uczyl na przykladach z poprzedniej niszy — rachunkach
# call-out" — tych samych zdaniach, ktore w `ciekawostki.md` przepisano tydzien
# wczesniej. Przyklady przepisano na ere AI, wiec plik wraca do sekcji 1.
# Decyzja, czy korpus Federal Register w ogole zostaje, nadal nalezy do
# wlasciciela i nie zalezy od tego, czy prompt jest aktualny.
ZAWIESZONE: dict[str, str] = {}


def _wzorzec(slowo):
    """Granica slowa, z koncowka liczby mnogiej — regularna i nieregularna.

    Bez granicy „oven" lapie „provenance", a „tuna" lapie „tunable" — czyli
    slow tej klasy nie dalo sie dodac do listy. Bez koncowki mnogiej „bottle"
    przepuszcza „shampoo bottles".

    NIEREGULARNA MNOGA -f/-fe → -ves. Bez tego „shelf" dawalo `shelfs?|shelfes?`
    i przepuszczalo „shelves" — czyli jedyna forme, w jakiej to slowo naprawde
    wystepuje w zdaniu o polkach. Slowo, ktore lapie tylko forme nieuzywana,
    jest na liscie na niby.
    """
    rdzen = re.escape(slowo)
    warianty = [rdzen + r"(?:e?s)?"]
    if slowo.endswith("fe"):
        warianty.append(re.escape(slowo[:-2]) + "ves")
    elif slowo.endswith("f"):
        warianty.append(re.escape(slowo[:-1]) + "ves")
    return re.compile(r"(?<![a-z])(?:" + "|".join(warianty) + r")(?![a-z])")


WZORCE = [(s, _wzorzec(s)) for s in SPRZED_PRZESTAWIENIA]


def trafienia_w_linii(linia):
    male = linia.lower()
    return [s for s, w in WZORCE if w.search(male)]


def zrodla():
    """Wszystko, co jedzie do modelu jako prompt — nie tylko pliki .md."""
    for plik in sorted(PROMPTY.glob("*.md")):
        yield plik.name, plik.read_text(encoding="utf-8").splitlines()
    # NOTE_FORMS jedzie do promptu notki jako `{form_brief}`. To prompt.
    #
    # DZIELIMY NA ZDANIA, I TO NIE JEST KOSMETYKA. Skan pomija LINIE, w ktorej
    # stoi fragment z listy wyjatkow. Gdy caly dwudziestolinijkowy brief byl
    # jedna „linia", jeden wyjatek — zapis prawdziwej wpadki, chroniony
    # slusznie — przykrywal wszystko inne w tym samym briefie. Zmierzone
    # 4 wrzesnia 2026: `ZACZEP_I_KONKRET` niosl obok chronionego zapisu takze
    # polecenie z poprzedniej niszy, idace do modelu przy KAZDEJ notce tej
    # formy. Po podziale wyjatek zakrywa jedno zdanie, tak jak w plikach
    # promptow.
    for nazwa in sorted(config.NOTE_FORMS):
        yield ("config.py:NOTE_FORMS[%s]" % nazwa,
               _na_zdania(config.NOTE_FORMS[nazwa]))

    # A TERAZ CALA RESZTA CONFIGU, BEZ RECZNEJ LISTY.
    #
    # Trzy razy z rzedu ta sama wada w tym samym pliku: skanowal tylko
    # `prompts/*.md`, potem dopisano `NOTE_FORMS`, potem `GENERATORY`. A do
    # promptow ida tak samo `NOTE_TYPES`, `KSZTALTY_MYSLI`,
    # `POSTAWY_KOMENTARZA`, `OTWARCIA`, `RUCHY_KONCOWE` i `DZIEDZINY_
    # CIEKAWOSTEK`. Recznej listy nie da sie utrzymac — to jest zdanie
    # z doktryny tego projektu i wlasnie zebralo trzeci dowod.
    #
    # Bierzemy KAZDA stala z `config.py`, ktora wyglada jak instrukcja dla
    # modelu: napis dluzszy niz 40 znakow, ze spacja, w stalej pisanej
    # WIELKIMI LITERAMI. Nowa stala dopisana jutro trafi pod skan sama.
    for nazwa in sorted(dir(config)):
        if not nazwa.isupper() or nazwa.startswith("_"):
            continue
        wartosc = getattr(config, nazwa)
        for klucz, tekst in _napisy_instrukcyjne(wartosc):
            yield ("config.py:%s%s" % (nazwa, klucz)), _na_zdania(tekst)


WSZYSTKIE = list(zrodla())
NAZWY_ZRODEL = [n for n, _ in WSZYSTKIE]

print("=== 0. TEST, KTORY NIC NIE CZYTA, PRZECHODZI ZAWSZE ===")
sprawdz("znalazlem prompty do sprawdzenia (%d)" % len(NAZWY_ZRODEL),
        len(NAZWY_ZRODEL) >= 15)
sprawdz("wsrod nich formy notek z config.py (%d)"
        % sum(1 for n in NAZWY_ZRODEL if n.startswith("config.py")),
        sum(1 for n in NAZWY_ZRODEL if n.startswith("config.py")) >= 8)
sprawdz("kazda forma z NOTE_FORM_MIX jest skanowana",
        all("config.py:NOTE_FORMS[%s]" % f in NAZWY_ZRODEL
            for f in config.NOTE_FORM_MIX),
        [f for f in config.NOTE_FORM_MIX
         if "config.py:NOTE_FORMS[%s]" % f not in NAZWY_ZRODEL])

print()
# WERDYKT MOWI, CO NAPRAWDE SPRAWDZA. Brzmial „ZADEN PROMPT NIE UCZY NA
# PRZEDMIOTACH" — a to jest twierdzenie o KOMPLETNOSCI, ktorego zamknieta lista
# slow nigdy nie udowodni. 1 wrzesnia niezalezny odczyt kodu pokazal, ze przy
# zielonym tescie `synteza.md` wciaz definiowala `main_mechanism` jako „hidden
# system", a dwa inne prompty kazaly klasyfikowac fakty do „everyday area".
# Zielone „zaden prompt nie uczy" znaczylo wtedy tyle, co „nie znalazlem slowa
# z mojej niepelnej listy" — i to ma byc napisane wprost.
print("=== 1. ZADEN PROMPT NIE ZAWIERA SLOWA Z LISTY EPOKI PRZEDMIOTOW ===")
wszystkie_trafienia = []
for etykieta, linie in WSZYSTKIE:
    if etykieta in ZAWIESZONE:
        continue
    dozwolone = WYJATKI.get(etykieta, ())
    for nr, linia in enumerate(linie, 1):
        if any(w in linia for w in dozwolone):
            continue
        znalezione = trafienia_w_linii(linia)
        if znalezione:
            wszystkie_trafienia.append("%s:%d %r" % (etykieta, nr,
                                                     znalezione[0]))
sprawdz("zaden prompt nie zawiera slowa z listy (to NIE dowod kompletnosci)",
        not wszystkie_trafienia,
        "; ".join(wszystkie_trafienia[:6]))

print()
print("=== 2. WYKRYWACZ NAPRAWDE COS WYKRYWA ===")
# KONTRDOWOD. Test szukajacy slow, ktorych juz nigdzie nie ma, przechodzilby
# rowniez wtedy, gdyby byl zepsuty. Sprawdzamy go na probce.
PROBKA = ["Everyone assumes the petrol station is holding their money.",
          "The papal conclave is the clean example.",
          "Aviation and cosmetics counts.",
          "everyone believes their oven clock keeps time",
          "Not \"firefighters get the differential\" but the bill for "
          "your call-out.",
          "\"The carton in your door shelf\" is this.",
          "a bottle in their bathroom, the light at their own junction",
          "pull up any FAA advisory circular",
          # KONTRDOWOD DO POPRAWKI LICZBY MNOGIEJ. Do 1 wrzesnia to zdanie
          # bylo tu ASERTOWANE JAKO NIEWINNE, bo `shelfs?|shelfes?` nie lapie
          # „shelves" — czyli test zapisywal wlasna slepa plame jako cecha.
          # Teraz jest po drugiej stronie: „shelf" na liscie ma znaczyc „shelf
          # w kazdej liczbie", a prompt, ktory tego slowa naprawde potrzebuje,
          # dostaje widoczny wpis w WYJATKI.
          "the shelves of a model registry, sorted by date",
          # Gole `clock` — do 1 wrzesnia na liscie stala tylko fraza „mains
          # clock", wiec ten wzorzec z `warto_pisac.md` przechodzil bez sladu.
          "the same event-triggered clock governs an unrelated industry"]
zlapane = sum(1 for w in PROBKA if trafienia_w_linii(w))
sprawdz("lapie wszystkie dziesiec zdan z probki", zlapane == len(PROBKA),
        [w[:40] for w in PROBKA if not trafienia_w_linii(w)])
sprawdz("i nie lapie zdania o naszym temacie",
        not trafienia_w_linii(
            "A model refusing a request is decided by a filter."))
# Pulapka granicy slowa — to przez nia „oven" nie moglo wczesniej wejsc.
# „shelved" zostaje niewinne: mnoga -ves nie jest imieslowem -ved.
for niewinne in ("provenance marks, disclosure duties",
                 "do not fail a text because it is unproven",
                 "a tunable parameter in the serving stack",
                 "a shelved proposal from the safety team",
                 "clockwise rotation of the evaluation set"):
    sprawdz("  nie lapie niewinnego: %s" % niewinne[:38],
            not trafienia_w_linii(niewinne), trafienia_w_linii(niewinne))

print()
print("=== 3. WYKRYWACZ SIEGA DO CONFIGU, NIE TYLKO DO PLIKOW ===")
# Bez tego sekcja 1 moglaby przechodzic dlatego, ze niczego z configu nie
# przeczytala. Bierzemy miejsce, o ktorym WIEMY, ze trafienie tam jest —
# zapis wlasnej porazki z FAA — i zadamy, zeby surowy wykrywacz je widzial.
# KONTRDOWOD PRZEZ ZATRUCIE, BO BRIEF JEST JUZ CZYSTY. Poprzednia wersja
# brala slowo, o ktorym „wiemy, ze tam jest" — a to znaczylo, ze kontrdowod
# zyl tylko dopoki prompt niosl slownictwo poprzedniej niszy. Sprzatniecie
# promptu wywalalo test, ktory to sprzatanie mial pilnowac.
#
# Bierzemy PRAWDZIWA wartosc z `config.py`, doklejamy do niej jedno slowo
# z listy i zadamy, zeby wykrywacz je zobaczyl. To dowodzi dokladnie tego,
# o co chodzi — ze skan siega do configu i dziala na jego tresci — i nie
# wymaga, zeby cokolwiek brudnego w tym configu zostalo.
_zatrute = config.NOTE_FORMS["ZACZEP_I_KONKRET"] + " Open the system card."
sprawdz("surowy wykrywacz widzi slowo z listy w wartosci z config.py",
        "system card" in trafienia_w_linii(_zatrute),
        trafienia_w_linii(_zatrute))
sprawdz("a ta sama wartosc BEZ dopisku jest czysta",
        not trafienia_w_linii(config.NOTE_FORMS["ZACZEP_I_KONKRET"]),
        trafienia_w_linii(config.NOTE_FORMS["ZACZEP_I_KONKRET"]))
sprawdz("a z wyjatkiem to samo miejsce przechodzi",
        not any(t.startswith("config.py:NOTE_FORMS[ZACZEP_I_KONKRET]")
                for t in wszystkie_trafienia))

print()
print("=== 4. LISTA WYJATKOW NIE ZGNILA ===")
# Wyjatek, ktory juz nic nie przepuszcza, ma zniknac. Inaczej lista rosnie i po
# roku przepuszcza wszystko, bo nikt nie pamieta, ktory wpis do czego byl.
martwe = []
tresci = {etykieta: "\n".join(linie) for etykieta, linie in WSZYSTKIE}
for nazwa, fragmenty in WYJATKI.items():
    if nazwa not in tresci:
        martwe.append("%s — zrodla nie ma" % nazwa)
        continue
    for f in fragmenty:
        if f not in tresci[nazwa]:
            martwe.append("%s — %r juz nie wystepuje" % (nazwa, f))
sprawdz("kazdy wyjatek nadal cos przepuszcza", not martwe, "; ".join(martwe))

print()
print("=== 5. ZAWIESZONE PLIKI SA ZAWIESZONE, NIE ZAPOMNIANE ===")
if not ZAWIESZONE:
    # PUSTA LISTA NIE MOZE BYC CICHA. Petla po pustym slowniku przechodzi
    # zawsze i o niczym nie mowi — a to jest dokladnie wada, ktora sekcja 0
    # nazywa. Skoro nikt nie jest zawieszony, zadamy dowodu, ze sekcja 1
    # naprawde czytala WSZYSTKIE pliki promptow, lacznie z tym, ktory byl
    # zawieszony do 1 wrzesnia.
    pliki = {p.name for p in PROMPTY.glob("*.md")}
    sprawdz("nikt nie jest zawieszony — sekcja 1 czyta kazdy plik promptu",
            pliki <= set(NAZWY_ZRODEL), sorted(pliki - set(NAZWY_ZRODEL)))
    sprawdz("w tym fedreg.md, zawieszony do 1 wrzesnia",
            "fedreg.md" in NAZWY_ZRODEL)
    sprawdz("i fedreg.md nie ma linii ze slowem z listy",
            not [linia for linia in (PROMPTY / "fedreg.md")
                 .read_text(encoding="utf-8").splitlines()
                 if trafienia_w_linii(linia)],
            [linia[:60] for linia in (PROMPTY / "fedreg.md")
             .read_text(encoding="utf-8").splitlines()
             if trafienia_w_linii(linia)])
for nazwa, powod in ZAWIESZONE.items():
    sciezka = PROMPTY / nazwa
    sprawdz("%s nadal istnieje" % nazwa, sciezka.exists())
    if not sciezka.exists():
        continue
    tresc = sciezka.read_text(encoding="utf-8")
    ile = sum(1 for linia in tresc.splitlines() if trafienia_w_linii(linia))
    # Gdyby ktos plik POPRAWIL, wpis ma zniknac stad, a plik wrocic do
    # sekcji 1. Zawieszenie bez powodu jest cicha zgoda.
    sprawdz("%s nadal jest z epoki przedmiotow (%d linii)" % (nazwa, ile),
            ile >= 1)
    print("        DO DECYZJI WLASCICIELA: %s" % powod)

print()
print("=== 6. PROMPTY TEMATYCZNE NAZYWAJA TEMAT KONTA ===")
# Zawijanie wiersza obsluguje `_re_escape_ze_zawijaniem` u gory pliku.
# PROMPT MA NAZYWAC TEMAT — ale od 2026-09-03 robi to POLEM `{nisza}`,
# a nie wpisana nazwa. Zdanie o niszy przestalo byc tekstem do przepisania
# przy kazdej zmianie konta i stalo sie podstawieniem, wiec test przyjmuje
# obie postaci: pole ALBO wpisana nazwe.
#
# Sprawdzenie zostaje, bo pytanie sie nie zmienilo: czy prompt w ogole mowi
# modelowi, o czym jest to konto. Prompt bez tego zdania — z polem czy bez —
# zostawia model bez tematu.
# SILNIK NIE MA NISZY (pusta od 2026-09-05), wiec wzorzec to samo pole
# `{nisza}` — pusty napis w alternatywie pasowalby do wszystkiego i test
# przechodzilby nad promptem, ktory tematu nie nazywa wcale.
_WZORZEC_NISZY = ("%s|%s" % (_re_escape_ze_zawijaniem(config.NISZA), re.escape("{nisza}"))
                  if config.NISZA else re.escape("{nisza}"))

for nazwa in ("skaut.md", "ciekawostki.md", "bank.md", "warto_pisac.md"):
    sciezka = PROMPTY / nazwa
    if not sciezka.exists():
        sprawdz("%s istnieje" % nazwa, False)
        continue
    male = sciezka.read_text(encoding="utf-8").lower()
    sprawdz("%s nazywa temat konta" % nazwa,
            # NISZA IDZIE Z CONFIGU. Stal tu wzorzec na jedna konkretna
            # nisze, wiec test „prompt nazywa temat konta" w praktyce
            # wymagal, zeby tym tematem byl ten jeden. Zawijanie wiersza
            # nadal dopuszczone: prompty sa lamane na 79 znakow, wiec
            # nazwa niszy bywa przecieta koncem linii.
            bool(re.search(_WZORZEC_NISZY, male)))

print()
print("=== 7. NAPRAWY Z 1 WRZESNIA NIE DAJA SIE CICHO COFNAC ===")
# Sekcja 1 pilnuje slow. Ta pilnuje REGUL, ktore te slowa trzymaly — bo samo
# wyciecie slowa nie przywraca dzialania bramce, ktora zadala przedmiotu.
skaut = " ".join((PROMPTY / "skaut.md").read_text(encoding="utf-8").split())
sprawdz("skaut: `scale` mowi o wiazacym SKUTKU, nie o zasiegu technologii",
        "Judge who the OUTCOME binds" in skaut)
sprawdz("skaut: AN_INDUSTRY nazwane jako nadmiernie zglaszane",
        "gets over-claimed" in skaut)
sprawdz("skaut: enum nazywa sytuacje z tego pola",
        all(s in skaut for s in ("one applicant", "one employer",
                                 "moderates")))

forma = " ".join((PROMPTY / "forma.md").read_text(encoding="utf-8").split())
sprawdz("forma: moment czytelnika NIE zada fizycznego przedmiotu",
        "holding **one concrete object**" not in forma
        and "one specific thing out of their own life" in forma)
sprawdz("forma: mowi wprost, ze przedmiot nie jest wymagany",
        "It does not have to be a thing they can pick up" in forma)
sprawdz("forma: ale ogolne 'ty' nadal nie przechodzi",
        "A generic second person is also not this" in forma)

klas = " ".join((PROMPTY / "klasyfikacja.md").read_text(encoding="utf-8")
                .split())
# PO WLASNOSCI, NIE PO SLOWACH Z JEDNEJ NISZY — czyli dokladnie to, o czym
# mowi komentarz dwie asercje nizej, a czego ta asercja nie robila.
#
# Wymagala doslownie „model or dataset size". To jest miara Z JEDNEJ DZIEDZINY,
# wiec test WYMUSZAL slad tematu w prompcie czystego rdzenia — i wystrzelil,
# gdy ten slad usunieto. Straznik czystosci, ktory kaze byc nieczystym.
#
# Wlasnoscia, ktorej ta lista naprawde broni, jest SZEROKOSC: model ma nie
# przegapic liczby dlatego, ze nie wyglada jak liczba, ktorej sie spodziewal.
# Liczymy wiec rodzaje miar, nie ich nazwy.
_rodzaje = ("percentage", "count", "duration", "price", "rate", "threshold",
            "score", "size", "wait", "cost", "headcount", "fine")
_ile = sum(1 for r in _rodzaje if r in klas)
sprawdz("klasyfikacja: lista liczb obejmuje wiele ROZNYCH rodzajow miar",
        _ile >= 8, "%d z %d rodzajow" % (_ile, len(_rodzaje)))
sprawdz("klasyfikacja: i mowi wprost, ze rodzaj nie ma znaczenia",
        "whatever it counts" in klas)
sprawdz("klasyfikacja: oraz zabrania pomijania nieoczekiwanych",
        "Do not skip one because it does not look like" in klas)

scena = config.NOTE_FORMS["SCENA"]
zaczep = config.NOTE_FORMS["ZACZEP_I_KONKRET"]
# ASERCJE PO WLASNOSCI, NIE PO SLOWACH Z JEDNEJ NISZY. Stalo tu
# `"what is on their screen" in scena` — czyli test WYMAGAL, zeby brief
# nazywal ekran, i przy koncie o czym innym oblewalby z powodu niezwiazanego
# z kodem. Pilnujemy tego, co ta poprawka naprawde zmienila: scena zaczyna
# sie od tego, co czytelnik ma PRZED SOBA TERAZ, i nie wymaga przedmiotu
# w rece.
sprawdz("NOTE_FORMS/SCENA nie zaczyna sie od trzymanego przedmiotu",
        "the thing they are holding" not in scena
        and "in front of them right now" in scena)
sprawdz("NOTE_FORMS/SCENA nadal zada JEDNEJ rzeczy czytelnika",
        "ONE thing and theirs" in scena)
sprawdz("NOTE_FORMS/ZACZEP_I_KONKRET zada rzeczy JUZ obecnej w zyciu",
        "MUST ALREADY BE IN THEIR LIFE" in zaczep)
# Zakaz ma dotyczyc KAZDEGO dokumentu, nie jednego rodzaju. Stalo tu
# `"open a model card" in zaczep`, czyli test kazal trzymac w prompcie nazwe
# dokumentu z poprzedniej niszy.
sprawdz("NOTE_FORMS/ZACZEP_I_KONKRET zakazuje odsylania do DOWOLNEGO dokumentu",
        "technical document" in zaczep and "homework" in zaczep)
# Wlasnosc, nie przyklad: forma ma podac co najmniej dwa PRZYKLADY WIELKOSCI
# i odroznic je od etykiety zrobionej z cyfr.
_liczba = config.NOTE_FORMS["LICZBA"]
sprawdz("NOTE_FORMS/LICZBA daje magnitudy, ktore obcy czuje",
        "eleven seconds" in _liczba and "a label that happens to be made of"
        " digits" in _liczba)

# --- przepisane 1 wrzesnia, po kontroli -------------------------------------
# Sekcja 1 pilnuje, ze slowa znikly. Ta pilnuje, ze SENS zostal — bo przyklad
# wyciety i niezastapiony to nie jest naprawa, tylko dziura w prompcie.
warto = " ".join((PROMPTY / "warto_pisac.md").read_text(encoding="utf-8")
                 .split())
sprawdz("warto_pisac: przyklad ratunku nadal mowi o TYM SAMYM mechanizmie "
        "w niepowiazanej branzy",
        "governs something in an unrelated industry" in warto, warto[-400:])
sprawdz("warto_pisac: i nadal odrzuca 'More sources'",
        '"More sources" is not' in warto)

fedreg = " ".join((PROMPTY / "fedreg.md").read_text(encoding="utf-8").split())
sprawdz("fedreg: nadal zamawia forme z 'your'",
        'using the word "your"' in fedreg)
sprawdz("fedreg: nadal odsiewa przekonania zawodowca",
        "would somebody with no connection to this industry hold this belief?"
        in fedreg)
sprawdz("fedreg: przyklad 'your' jest z tego pola, nie z biletu",
        "your rejection notice" in fedreg or "your claim was cut" in fedreg,
        fedreg[1200:1900])

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
