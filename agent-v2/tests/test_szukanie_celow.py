# -*- coding: utf-8 -*-
"""Agent ma szukac celow WE WLASNEJ NISZY i szukac ich, AZ ZNAJDZIE.

DWIE WADY, JEDNA UKRYTA POD DRUGA.

1. HASLA WYSZUKIWANIA BYLY Z EPOKI PRZEDMIOTOW — dziesiaty raz ta sama
   choroba w jednej sesji. Wszystkie osiemnascie opisywalo poprzednie pismo:

       "food labeling rules", "packaging regulation", "building codes
       regulation", "transport standards", "product recall", "zoning"...

   ANI JEDNO nie dotyczylo AI. Piec dni po przestawieniu konta, po poprawieniu
   dwudziestu blokow w dziewieciu promptach, po wyczyszczeniu banku tematow
   i po zaostrzeniu reguly celow — hasel nikt nie tknal.

   SKUTEK BYL ODWROTNY DO WYGLADU. Agent szukal „przepisow o etykietowaniu
   zywnosci", dostawal posty o etykietowaniu zywnosci, a regula `cele.md`
   POPRAWNIE je odrzucala, bo nie dotycza AI. W logu wygladalo to na
   wybrednosc modelu:

       [cele] warte komentarza: 0/15
       [cele] warte komentarza: 1/13

   a bylo szukaniem nie tego, czego trzeba.

2. JEDNA PULA, JEDNA OCENA, KONIEC. Jesli z trzynastu kandydatow przechodzil
   jeden, wychodzil JEDEN komentarz — przy planie pietnastu. Przebieg nie
   probowal drugi raz.

Wlasciciel: „niech szuka celi (...) i niech szuka az znajdzie i komentuje".

CO TA POPRAWKA CELOWO ZOSTAWIA BEZ ZMIAN: odstepy. Wiecej celow to nie
szybsze pisanie — `rytm()` nadal trzyma 5-15 minut miedzy komentarzami,
a `ODSTEP_DNI_NA_PUBLIKACJE` cztery dni na te sama publikacje. Wlasciciel byl
jednoznaczny juz wczesniej: „nie chodzi o LICZBE, tylko o ODSTEPY".

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo.
"""
import pathlib
import sys

sys.path.insert(0, "agent-v2")
sys.path.insert(0, "agent-v2/tests")
import config  # noqa: E402
import wlasna_konfiguracja  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# ASERCJE O NASZYCH WARTOSCIACH, nie o regulach. Przy wlasnej konfiguracji
# wypisuja sie z myslnikiem zamiast OK — pominiete sa widoczne, nie ciche.
sprawdz_nasze = wlasna_konfiguracja.tylko_nasze(sprawdz)


print("=== 0. SILNIK NIE MA WLASNYCH HASEL — HASLA SA W KARTRIDZU ===")
# Od 2026-09-06 `config.HASLA_SZUKANIA` i `config.ZNAKI_NISZY` sa w silniku
# PUSTE. Temat przychodzi z kartridza (`presety/<nazwa>/`), wiec ten test
# mierzy hasla kartridza `ai`, a od silnika wymaga jednego: zeby nie mial
# zadnego tematu, ktory wlaczalby sie po odlaczeniu kartridza.
import preset  # noqa: E402

sprawdz("silnik nie ma hasel szukania", config.DOMYSLNE_SILNIKA.get("HASLA_SZUKANIA") == (),
        config.DOMYSLNE_SILNIKA.get("HASLA_SZUKANIA"))
sprawdz("silnik nie ma znakow niszy", config.DOMYSLNE_SILNIKA.get("ZNAKI_NISZY") == ())
KARTRIDZ = preset.wczytaj(pathlib.Path("presety/ai"))

print()
print("=== 1. HASLA SZUKANIA MIESZCZA SIE W ZNAKACH NISZY ===")
hasla = [str(h).lower() for h in KARTRIDZ.pola.get("temat.hasla_szukania", ())]
# Lista slow, po ktorych poznajemy rewir. Jawna i krotka, zeby dalo sie
# ja przeczytac i zakwestionowac — a nie zgadywac, co test uznaje za „w niszy".
# ZNAKI IDA Z TEGO SAMEGO KARTRIDZA co hasla. Do 2026-09-03 stala tu
# wpisana lista slow o jednej konkretnej niszy — czyli test, ktory mial
# pilnowac SPOJNOSCI rewiru z nisza, w rzeczywistosci betonowal nisze.
ZNAKI = tuple(str(z).lower() for z in KARTRIDZ.pola.get("temat.znaki_niszy", ()))


def w_niszy(h: str) -> bool:
    return any(z in h for z in ZNAKI)


poza = [h for h in hasla if not w_niszy(h)]
# KOMUNIKAT MA MOWIC, CO ZROBIC. To nie jest asercja o NASZYCH haslach —
# regula obowiazuje kazda konfiguracje, bo jej zlamanie ma zmierzony skutek:
# agent szuka po haslach, dostaje posty, po czym `cele.md` odrzuca je
# wszystkie jako spoza rewiru. W logu wyglada to na wybrednosc modelu
# („warte komentarza: 0/15"), a jest szukaniem nie tego, czego trzeba.
#
# Sama lista trafien nic nie mowila operatorowi, ktory dopiero co wpisal
# swoje hasla. Teraz mowi, ktorego znaku brakuje.
if poza:
    print("    %d hasel nie zawiera ZADNEGO znaku z temat.znaki_niszy kartridza:" % len(poza))
    for h in poza[:12]:
        print("      %s" % h)
    print("    Znaki, ktore masz: %s" % ", ".join(ZNAKI))
    print("    Napraw jedno z dwojga:")
    print("      * dopisz do `temat.znaki_niszy` rdzen wspolny tym haslom")
    print("        (np. 'food' zlapie wszystkie haslo o zywnosci), albo")
    print("      * przeformuluj hasla tak, zeby niosly znak, ktory juz masz.")
    print("    Skutek zaniechania jest zmierzony: agent znajduje posty,")
    print("    a regula rewiru odrzuca je co do jednego.")
sprawdz("kazde haslo kartridza dotyczy jego niszy", not poza,
        "%d poza: %s" % (len(poza), ", ".join(poza[:4])) if poza else "")

# HASLA WYRAZNIE ODRZUCONE PRZEZ WLASCICIELA. Lista jest teraz w configu
# (`HASLA_ODRZUCONE`), bo zalezy od niszy: haslo, ktore w jednej publikacji
# jest balastem, w innej jest rdzeniem. Puste znaczy „nic nie odrzucono".
for zle in getattr(config, "HASLA_ODRZUCONE", ()):
    sprawdz("  zniknelo: %s" % zle,
            not any(zle in h for h in hasla))

print()
print("=== 2. PULA JEST SZERSZA NIZ JEDNA NISZA ===")
# Sam rdzen niszy w kazdym hasle nie wystarczy: dwadziescia hasel o tym samym
# daje te sama garstke kont. Rewir ma obejmowac takze to, co nisza ZMIENIA.
# REGULA DLA KAZDEGO JEST STRUKTURALNA, nie liczbowa: przebieg losuje
# `ILE_HASEL_NA_PRZEBIEG` hasel, wiec pula ma byc od tego istotnie szersza.
# Rowna albo mniejsza idzie za kazdym razem CALA i przyprowadza te sama
# garstke kont — czyli dokladnie to, przed czym ta sekcja stoi.
_minimum = 3 * config.ILE_HASEL_NA_PRZEBIEG
sprawdz("pula jest szersza niz jeden przebieg (>= %d)" % _minimum,
        len(hasla) >= _minimum,
        "%d hasel przy %d losowanych na przebieg"
        % (len(hasla), config.ILE_HASEL_NA_PRZEBIEG))
# TRZY STRONY TEMATU: dwadziescia hasel o jednym daje te sama garstke kont,
# co trzy. Strony wynikaja ze znakow KARTRIDZA (pomiar, pieniadze,
# odpowiedzialnosc), a nie z mapy w silniku — silnik nie ma zadnej.
sprawdz("silnik nie ma mapy rewiru", config.DOMYSLNE_SILNIKA.get("OBSZARY_REWIRU") == {})
_strony = {"pomiar": ("benchmark", "eval", "hallucinat", "reproduc"),
           "pieniadze": ("token", "gpu", "compute", "chip", "training"),
           "odpowiedzialnosc": ("regulat", "ai act", "copyright", "licen", "liabil")}
for obszar, slowa in _strony.items():
    sprawdz("  rewir kartridza obejmuje: %s" % obszar,
            any(any(s in h for s in slowa) for h in hasla))

print()
print("=== 3. WIECEJ HASEL NA PRZEBIEG ===")
# Trzy z osiemnastu to jedna szosta rewiru na raz — przy zaostrzonej regule
# celow waska pula zamieniala sie w zero kandydatow.
sprawdz("na przebieg idzie wiecej niz 3 hasla",
        config.ILE_HASEL_NA_PRZEBIEG > 3, config.ILE_HASEL_NA_PRZEBIEG)
sprawdz("ale nie cala pula naraz — zostaje co losowac",
        config.ILE_HASEL_NA_PRZEBIEG < len(hasla))

print()
print("=== 4. SZUKA, AZ ZNAJDZIE — I MA GDZIE PRZESTAC ===")
rp = pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8")
sprawdz("przebieg dobiera kolejne partie celow",
        "runda %d szukania" in rp)
sprawdz("warunkiem jest NIEDOBOR wobec planu",
        'len(cele) < na_teraz["komentarze"]' in rp)
sprawdz("jest sufit rund", "config.RUNDY_SZUKANIA_CELOW" in rp)
sprawdz("i sufit stoi w configu, nie w kodzie przebiegu",
        isinstance(getattr(config, "RUNDY_SZUKANIA_CELOW", None), int)
        and config.RUNDY_SZUKANIA_CELOW >= 2,
        getattr(config, "RUNDY_SZUKANIA_CELOW", None))
sprawdz("czas przebiegu nadal przerywa szukanie",
        'zostal_czas("komentarze")' in rp.split("runda %d szukania")[0][-900:])
# BEZ TEGO PETLA MIELILABY TO SAMO. Wyszukiwarka oddaje skonczona pule;
# runda bez ani jednego nowego adresu znaczy, ze kolejna tez nic nie doda.
sprawdz("runda bez nowych adresow konczy szukanie",
        "nie oddaje juz nic nowego" in rp)

print()
print("=== 5. NIE POWTARZAMY TYCH SAMYCH CELOW ===")
sprawdz("nowe partie sa filtrowane przez `widziane`",
        'x["url"] not in widziane' in rp)
sprawdz("i platne publikacje odsiewane takze w kolejnych rundach",
        rp.count("not in platne") >= 2, rp.count("not in platne"))

print()
print("=== 6. ODSTEPY ZOSTAJA NIETKNIETE ===")
# To jest ta czesc, ktorej poprawka NIE MOZE ruszyc. Wlasciciel: „nie chodzi
# o LICZBE, tylko o ODSTEPY" i „nie ma nakurwiac na jednym profilu".
sprawdz("odstep dni na te sama publikacje bez zmian",
        config.ODSTEP_DNI_NA_PUBLIKACJE >= 4,
        config.ODSTEP_DNI_NA_PUBLIKACJE)
sprawdz("rytm miedzy komentarzami nadal obowiazuje",
        'rytm("komentarz", "komentarze", rytm_stanu)' in rp)
dolny, gorny = config.ODSTEPY["komentarz"]
sprawdz("i jest liczony w minutach, nie sekundach",
        dolny >= 240, (dolny, gorny))

print()
print("=== 7. KONTRDOWOD: STARA PULA MUSI TU POLEC ===")
# KONTRDOWOD MUSI BYC NIEZALEZNY OD NISZY. Stala tu lista hasel poprzedniego
# pisma i to bylo pulapka: po zmianie niszy „stara pula" stala sie NOWA pula
# i kontrdowod zaczal przeczyc sam sobie. Bierzemy wiec pule, ktora jest poza
# KAZDYM rewirem technicznym — sito ma odrzucac to, co nie nalezy do niszy,
# a nie to, co przypadkiem bylo poprzednim tematem.
POZA_KAZDYM_REWIREM = ("celebrity divorce rumours", "last night's match score",
                       "horoscope for tomorrow", "best holiday beaches",
                       "which cafe has the nicest cake")
sprawdz("nic spoza rewiru nie przechodzi sita niszy",
        not any(w_niszy(h) for h in POZA_KAZDYM_REWIREM),
        [h for h in POZA_KAZDYM_REWIREM if w_niszy(h)])
# Druga polowa kontrdowodu — sito nie odrzuca WSZYSTKIEGO. Dla cudzej
# konfiguracji mowi to samo, co sekcja 1, i tam jest powiedziane z instrukcja,
# co zrobic; tu wystarczy raz.
sprawdz("a wszystkie hasla kartridza przechodza",
        all(w_niszy(h) for h in hasla),
        [h for h in hasla if not w_niszy(h)])

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
