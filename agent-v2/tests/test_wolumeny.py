"""Ile agent naprawde robi na koncie — i czy budzet da sie wydac.

Przeglad z 20 sierpnia 2026 na wlasnych danych. Do tej pory widelki byly
liczbami wzietymi z wyobrazenia o tempie czlowieka. Dziennik za piec dni
pokazal cos innego:

    lajki        9,6/dzien   przy budzecie 12-20
    komentarze   7,0/dzien   przy budzecie 15-20
    restacki     0,4/dzien   przy budzecie 2-4
    obserwacje   0,0/dzien   przy budzecie 30-44 MIESIECZNIE

Ostatnia linijka to nie niedobor, tylko martwy blok. Przyczyna nie byla
w liczbie, tylko w KOLEJNOSCI: zegar przebiegu sprawdzaja bloki od odpowiedzi
po subskrypcje, a polubienia i restacki nie patrza na niego wcale. Gdy czas
sie konczyl, wypadaly dokladnie te bloki, ktore byly wobec zegara uczciwe —
a obserwowanie stalo za komentarzami, czyli za jedynym blokiem potrafiacym
zjesc caly budzet czasu.

Budzet, ktorego nie da sie wydac, nie jest budzetem: klamie w logu, psuje
dzielenie normy na przebiegi i ukrywa, ze cos w ogole nie chodzi.
"""
import re
import pathlib
import sys

sys.path.insert(0, "agent-v2")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import config   # noqa: E402
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


# Asercje o DOSTARCZONYCH wartosciach, pomijane widocznie,
# gdy operator ma wlasne w `konfiguracja.toml`.
sprawdz_nasze = wlasna_konfiguracja.tylko_nasze(sprawdz)


# Zmierzone srednie z dziennika, 16-20 sierpnia. Sluza za punkt odniesienia:
# widelki maja OPISYWAC to, co agent robi, a nie zyczyc sobie tego.
ZMIERZONE = {"lajki": 9.6, "komentarze": 7.0, "restacki": 0.4,
             "obserwacje": 0.0, "notki": 3.0}

print("=== 1. WIDELKI NIE MOGA BYC ODERWANE OD WYKONANIA ===")
POROWNANIA = [
    ("lajki", config.LAJKI_DZIENNIE, ZMIERZONE["lajki"]),
    ("komentarze", config.KOMENTARZE_DZIENNIE, ZMIERZONE["komentarze"]),
    ("restacki", config.RESTACK_DZIENNIE, ZMIERZONE["restacki"]),
]
for nazwa, (dol, gora), zmierzone in POROWNANIA:
    print("    %-11s widelki %s-%-3s   zmierzone %.1f" % (nazwa, dol, gora, zmierzone))
    # Dolna granica ma byc w zasiegu. Gorna moze byc ambitna, ale nie o rzad
    # wielkosci — inaczej dzielenie normy na przebiegi liczy fikcje.
    sprawdz("  %-11s górna granica w granicach rozsądku" % nazwa,
            gora <= max(4, zmierzone * 4), (gora, zmierzone))

print()
print("=== 2. KONKRETNE DECYZJE Z 20 SIERPNIA ===")
sprawdz_nasze("lajki 10-16 (było 12-20)", config.LAJKI_DZIENNIE == (10, 16),
        config.LAJKI_DZIENNIE)
# PODNIESIONE 30 sierpnia 2026 decyzja wlasciciela do 15-23. Argument z 20
# sierpnia brzmial „osiemnascie komentarzy dziennie to podpis bota" — i byl
# sluszny wobec OWCZESNYCH odstepow 3-8 min. Wlasciciel przeformulowal go
# trafniej: bot poznaje sie nie po LICZBIE, tylko po tym, ze wystawia je jeden
# po drugim. Razem z ta zmiana odstep poszedl na 5-15 min, a przebiegow jest
# piec zamiast trzech, wiec 19 komentarzy rozklada sie na ~190 minut.
sprawdz_nasze("komentarze 15-23 (bylo 8-12)", config.KOMENTARZE_DZIENNIE == (15, 23),
        config.KOMENTARZE_DZIENNIE)
sprawdz_nasze("i odstep urosl razem z liczba — inaczej to byloby seria",
        config.ODSTEPY["komentarz"][0] >= 300, config.ODSTEPY["komentarz"])
sprawdz_nasze("restacki 1-2 (było 2-4)", config.RESTACK_DZIENNIE == (1, 2),
        config.RESTACK_DZIENNIE)
# WYCOFANE 2026-08-23, ODWIESZONE 2026-09-01 — BO WNIOSEK BYL FALSZYWY.
#
# Stalo tu `== (0, 0)` z uzasadnieniem „Substack zdjal przycisk «Follow» ze
# stron profilowych; zmierzone na szesciu profilach: wszedzie «Subscribe»
# i «Message», slowa «Follow» nie ma w HTML ani razu". POMIAR BYL PRAWDZIWY,
# WNIOSEK FALSZYWY: przycisk siedzi w menu pod kolkiem „...", ktore Substack
# rysuje DOPIERO PO KLIKNIECIU, wiec w HTML zamknietej strony go nie ma i byc
# nie moze. Czytanie HTML-a nie moglo tego rozstrzygnac.
#
# Zmierzone ponownie 2026-09-01 na zywej sesji: menu oddaje „Follow" tam,
# gdzie nie obserwujemy, i „Unfollow" tam, gdzie obserwujemy. Pelny pomiar
# i szescioro sprawdzonych profili stoja w
# `tests/test_obserwowanie_przez_menu.py`.
#
# TEN TEST PILNOWAL WYCOFANIA PRZEZ DZIEWIEC DNI I DLATEGO ZOSTAJE — tylko
# odwrocony. Zero w tej stali kosztowalo dziewiec dni bez ani jednej
# obserwacji, a nie wygladalo na awarie, bo `norma.NIEWYKONALNE` tlumaczylo
# powstale zero tym samym nieprawdziwym zdaniem.
#
# LICZBY ZMIENIONE 1 WRZESNIA 2026 — TEGO SAMEGO DNIA, DECYZJA WLASCICIELA.
# Sam fakt „nie jest zero" zostaje pilnowany, ale wielkosci ida za SKUTKIEM,
# a nie za naszym kosztem: subskrypcja ma 11,5% konwersji zwrotnej, obserwacja
# 3,4%, a nasi wlasni czytelnicy nie przyszli z ANI JEDNEJ subskrypcji, ktora
# dalismy (0 z 19). Caly rachunek stoi przy `config.SUBSKRYPCJE_MIESIECZNIE`.
sprawdz_nasze("obserwacje 10-16/mies — przycisk jest, ale to slabszy kanal",
        config.FOLLOW_MIESIECZNIE == (10, 16), config.FOLLOW_MIESIECZNIE)
sprawdz_nasze("subskrypcje 12-20/mies — kanal, ktory jako jedyny konwertuje",
        config.SUBSKRYPCJE_MIESIECZNIE == (12, 20),
        config.SUBSKRYPCJE_MIESIECZNIE)
sprawdz_nasze("i to subskrypcji jest WIECEJ, bo za to placi sie skutkiem",
        sum(config.SUBSKRYPCJE_MIESIECZNIE) > sum(config.FOLLOW_MIESIECZNIE),
        (config.SUBSKRYPCJE_MIESIECZNIE, config.FOLLOW_MIESIECZNIE))
sprawdz("KONTRDOWOD: stary uklad (30,44)+(6,12) mial to dokladnie odwrotnie",
        not (sum((6, 12)) > sum((30, 44))))
sprawdz_nasze("notki nietknięte — to silnik wzrostu",
        len(config.NOTE_MIX_OTHER_DAY) == 5, len(config.NOTE_MIX_OTHER_DAY))

print()
print("=== 3. KAZDE WIDELKI MAJA SENS JAKO WIDELKI ===")
for nazwa in ("LAJKI_DZIENNIE", "KOMENTARZE_DZIENNIE", "RESTACK_DZIENNIE",
              "FOLLOW_MIESIECZNIE", "SUBSKRYPCJE_MIESIECZNIE"):
    dol, gora = getattr(config, nazwa)
    # ZERO JEST DOZWOLONE, ale tylko jako (0, 0) — czyli zdolnosc swiadomie
    # wylaczona. Widelki w rodzaju (0, 5) albo (5, 0) to zawsze literowka,
    # a nie decyzja, i te loop ma dalej lapac.
    wylaczone = (dol, gora) == (0, 0)
    sprawdz("%-24s dół <= góra, oba > 0 albo jawne (0, 0)" % nazwa,
            wylaczone or 0 < dol <= gora, (dol, gora))
    if wylaczone:
        # Wylaczona zdolnosc musi miec napisany POWOD przy stalej. Bez tego
        # zero jest nieodroznialne od pomylki i za pol roku nikt nie bedzie
        # wiedzial, czy to decyzja, czy ktos zjechal palcem.
        zrodlo_cfg = pathlib.Path("agent-v2/config.py").read_text(encoding="utf-8")
        blok = zrodlo_cfg[:zrodlo_cfg.index(nazwa + " = ")]
        akapit = blok.rsplit(chr(10) + chr(10), 1)[-1]
        sprawdz("%-24s zero ma napisany powod tuz obok" % nazwa,
                akapit.count("#") >= 3 and len(akapit) > 200, len(akapit))

print()
print("=== 4. RESTACK JEST NAJRZADSZY ZE WSZYSTKIEGO ===")
# Bo jako jedyny stawia NASZE nazwisko obok cudzego tekstu.
sprawdz("restacków mniej niż lajków",
        config.RESTACK_DZIENNIE[1] < config.LAJKI_DZIENNIE[0],
        (config.RESTACK_DZIENNIE, config.LAJKI_DZIENNIE))
sprawdz("restacków mniej niż komentarzy",
        config.RESTACK_DZIENNIE[1] < config.KOMENTARZE_DZIENNIE[0],
        (config.RESTACK_DZIENNIE, config.KOMENTARZE_DZIENNIE))

print()
print("=== 5. KOLEJNOSC BLOKOW — TU SIEDZIALO ZERO OBSERWACJI ===")
zrodlo = open("agent-v2/run.py", encoding="utf-8").read()
m = re.search(r"for nazwa, robota in \((.*?)\):", zrodlo, re.S)
sprawdz("pętla bloków istnieje", m is not None)
kolejnosc = re.findall(r'\("(\w+)",', m.group(1)) if m else []
print("    %s" % " -> ".join(kolejnosc))
sprawdz("wszystkie osiem bloków", len(kolejnosc) == 8, kolejnosc)

i = {n: k for k, n in enumerate(kolejnosc)}
sprawdz("obserwowanie PRZED komentarzami",
        i.get("obserwowanie", 99) < i.get("komentarze", -1), i)
sprawdz("subskrypcje PRZED komentarzami",
        i.get("subskrypcje", 99) < i.get("komentarze", -1), i)
# KONTRDOWOD: to jest dokladnie ta kolejnosc, ktora byla wczesniej i dawala
# zero obserwacji. Bez tego sprawdzenia test nie odroznia wersji.
STARA = ["odpowiedzi", "notki", "komentarze", "dyskusje", "obserwowanie",
         "subskrypcje", "polubienia", "restacki"]
sprawdz("to NIE jest stara kolejność (test rozróżnia)", kolejnosc != STARA,
        kolejnosc)

print()
print("=== 6. CO ZOSTAJE NA SWOIM MIEJSCU I DLACZEGO ===")
sprawdz("odpowiedzi pierwsze — to zobowiązanie wobec czytelnika",
        kolejnosc and kolejnosc[0] == "odpowiedzi", kolejnosc[:1])
sprawdz("notki drugie — to nasza własna treść",
        len(kolejnosc) > 1 and kolejnosc[1] == "notki", kolejnosc[:2])
sprawdz("restacki ostatnie — niosą najwięcej ryzyka",
        kolejnosc and kolejnosc[-1] == "restacki", kolejnosc[-1:])

print()
print("=== 7. BLOKI TANIE IDA PRZED DROGIMI ===")
# Obserwacja i subskrypcja to jedno wejscie na profil, zero wywolan modelu.
# Komentarz to pobranie strony, trzy warianty i sprawdzenie faktow (~3 centy).
TANIE = {"obserwowanie", "subskrypcje", "polubienia"}
DROGIE = {"komentarze", "dyskusje"}
najdrozszy_tani = max((i[n] for n in TANIE if n in i), default=99)
pierwszy_drogi = min((i[n] for n in DROGIE if n in i), default=-1)
sprawdz("co najmniej jeden tani blok wyprzedza drogie",
        min((i[n] for n in TANIE if n in i), default=99) < pierwszy_drogi, i)

print()
print("=== 8. ILE TO KOSZTUJE MIESIECZNIE ===")
# Zmierzone na produkcji: komentarz to trzy warianty + factcheck ~ 3 centy.
ZA_KOMENTARZ = 0.03
for opis, ile in (("było (8-12/dzień)", 10.0),
                  ("jest (15-23/dzień)", sum(config.KOMENTARZE_DZIENNIE) / 2)):
    print("    %-22s %5.1f/dzień -> $%5.2f miesięcznie" % (opis, ile, ile * 30 * ZA_KOMENTARZ))
# KOSZT MA BYC ZNANY, NIE MINIMALNY. Wlasciciel swiadomie podniosl norme, wiec
# test przestaje bronic oszczednosci, a zaczyna bronic tego, zeby rachunek nie
# uciekl bez decyzji: 19/dobe to ~17 USD miesiecznie i to jest gorna granica,
# ktora ma sie nie przesunac po cichu.
_miesiecznie = sum(config.KOMENTARZE_DZIENNIE) / 2 * 30 * ZA_KOMENTARZ
sprawdz("miesieczny koszt komentarzy ponizej 25 USD", _miesiecznie < 25,
        "$%.2f" % _miesiecznie)
sprawdz("i miesci sie w sufucie miesiecznym",
        _miesiecznie < config.MONTHLY_LIMIT_USD,
        "$%.2f z $%.2f" % (_miesiecznie, config.MONTHLY_LIMIT_USD))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
