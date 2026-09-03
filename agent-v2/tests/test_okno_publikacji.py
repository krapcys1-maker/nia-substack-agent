# -*- coding: utf-8 -*-
"""Okno publikacji wycisza NOTKI, nie komentarze — i nie blokuje calego przebiegu.

CO SIE DZIALO 31 sierpnia 2026. Przebieg o 17:00 UTC znalazl DZIEWIEC celow
wartych komentarza — najlepszy wynik od przestawienia konta na AI, zaraz po
wymianie hasel wyszukiwania:

    [cele] warte komentarza: 9/23
     notki: 0
     komentarze: 0

Nie wystawil ANI JEDNEGO. Powod stal w logu linijke wyzej:

    okno publikacji: NIE — 13:00 u czytelnikow — najgorsze okno wg researchu

DWIE OSOBNE WADY W JEDNEJ LINIJCE.

1. `WORST_NOTE_HOURS = (12, 13)` ET blokowalo publikacje. Przebieg o 17:00 UTC
   to 13:00 ET, czyli DOKLADNIE ta godzina — wiec blokowal sie CODZIENNIE.
   Jeden z pieciu przebiegow, 20% dziennej zdolnosci, kazdego dnia.

   A regula stala na wlasnym zaprzeczeniu: komentarz w `config.py` mowi
   wprost, ze NASZE WLASNE ZRODLA SIE NIE ZGADZAJA — jedno wskazuje 6-8 ET,
   drugie 15-18 ET. Egzekwowalismy godziny, o ktorych sami piszemy, ze nie
   wiemy.

2. Okno wyciszalo KOMENTARZE razem z notkami. Jego wlasne uzasadnienie brzmi:
   „nowe tresci konkuruja o miejsce w kanale, a tekst wrzucony gdy publicznosc
   spi traci pierwsze godziny widocznosci". To jest prawda o NOTCE — naszej
   tresci na naszym profilu. Komentarz stoi pod CUDZYM tekstem i jego
   widocznosc zalezy od ruchu na tamtym poscie.

Decyzja wlasciciela: „nawet za cene wypuszczania poza oknami, bo tak to do
konca swiata bedziemy sie bawic z czekaniem na agenta i jego okno".

CZEGO TA POPRAWKA NIE RUSZA: progu snu. To inne twierdzenie i lepiej
uzasadnione — o 23:00 u czytelnikow nadal nie nadajemy.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo.
"""
import pathlib
import sys
from datetime import datetime, timezone

sys.path.insert(0, "agent-v2")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
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


# Asercje o DOSTARCZONYCH wartosciach, pomijane widocznie.
sprawdz_nasze = wlasna_konfiguracja.tylko_nasze(sprawdz)


def o(h, m=0, dzien=31):
    return datetime(2026, 8, dzien, h, m, tzinfo=timezone.utc)


print("=== 1. ILE Z PIECIU PRZEBIEGOW MOZE W OGOLE PUBLIKOWAC ===")
# To jest cala tresc naprawy: harmonogram ma dzialac w calosci.
#
# ALE „W CALOSCI" ZALEZY OD TRZECH RZECZY NARAZ, i dwie z nich sa polami
# konfiguracji: godziny w zegarach systemd (UTC, stale), okno publikacji
# (`OKNO_PUBLIKACJI_ET`) i strefa czytelnika (`PUBLISH_TIMEZONE`). Przy
# dostarczonych wartosciach wszystkie piec miesci sie w oknie. Przy oknie
# 7-21 w Europe/Warsaw — trzy ostatnie juz nie, bo 19:20 UTC to 21:20 na
# miejscu.
#
# Test nie oblewa z tego powodu, bo to nie jest awaria kodu. Ale MOWI, ile
# przebiegow tracisz, bo tego nie widac znikad indziej: przebieg po prostu
# nie wystawia notki i nie ma o tym wiersza w zadnym raporcie.
PRZEBIEGI_UTC = ((11, 20), (17, 0), (19, 20), (21, 30), (23, 40))
moga, nie_moga = [], []
for h, m in PRZEBIEGI_UTC:
    wolno, powod = config.pora_na_publikacje(o(h, m))
    (moga if wolno else nie_moga).append(("%02d:%02d" % (h, m), powod))

for kiedy, _ in moga:
    print("  OK    %s UTC moze publikowac" % kiedy)
for kiedy, powod in nie_moga:
    print("  -     %s UTC NIE moze:  %s" % (kiedy, powod))

# ASERCJA, KTORA OBOWIAZUJE ZAWSZE: przynajmniej jeden przebieg musi umiec
# publikowac. Zero znaczy konto, ktore nigdy nic nie wystawi — a to juz jest
# awaria konfiguracji i ma byc czerwona.
sprawdz("co najmniej jeden przebieg moze publikowac", bool(moga),
        "okno %s w %s nie obejmuje ZADNEJ z godzin przebiegow — konto nigdy "
        "nie wystawi notki" % (config.OKNO_PUBLIKACJI_ET, config.PUBLISH_TIMEZONE))
if nie_moga and moga:
    print("    UWAGA: %d z %d przebiegow nie wystawi notki przy oknie %s"
          % (len(nie_moga), len(PRZEBIEGI_UTC), config.OKNO_PUBLIKACJI_ET))
    print("    w strefie %s. Zegary systemd chodza w UTC i sa stale;"
          % config.PUBLISH_TIMEZONE)
    print("    okno przesuwa sie razem ze strefa czytelnika. Poszerz okno")
    print("    albo przestaw godziny w agent-v2/systemd/*.timer.")

# A TO JEST ASERCJA O DOSTARCZONYCH WARTOSCIACH: przy nich przechodza wszystkie.
sprawdz_nasze("i przy dostarczonym oknie przechodza WSZYSTKIE PIEC",
              len(moga) == len(PRZEBIEGI_UTC),
              "przechodzi %d z %d" % (len(moga), len(PRZEBIEGI_UTC)))

print()
print("=== 2. GODZINA 13:00 ET — TA, KTORA BLOKOWALA CODZIENNIE ===")
wolno, powod = config.pora_na_publikacje(o(17, 0))
sprawdz("nie blokuje", wolno, powod)
# Obie asercje ponizej dotycza DOSTARCZONYCH martwych godzin (12-13 ET).
# Przy wlasnych 17:00 UTC nie wypada w martwej godzinie, wiec powod jej nie
# wymienia — i sluszznie.
sprawdz_nasze("ale nadal jest odnotowana w powodzie",
              "slabsza" in powod, powod)
sprawdz_nasze("stala nadal istnieje jako zapis ustalen",
              config.WORST_NOTE_HOURS == (12, 13), config.WORST_NOTE_HOURS)
# A TO OBOWIAZUJE ZAWSZE: martwe godziny NIE MOGA blokowac — maja tylko
# trafiac do powodu. Ta wada kosztowala jeden z pieciu przebiegow dziennie.
_h_martwa = (config.WORST_NOTE_HOURS[0] + 24 - 2) % 24
sprawdz("martwa godzina nadal nie BLOKUJE, tylko sie odnotowuje",
        all(config.pora_na_publikacje(o(g, 0))[0]
            or "spi" in config.pora_na_publikacje(o(g, 0))[1]
            for g in range(24)),
        "jakas godzina blokuje z powodu innego niz sen")

print()
print("=== 3. PROG SNU ZOSTAJE — TO INNE TWIERDZENIE ===")
# Poprawka mogla latwo znies wszystko. Nie ma.
# GODZINY SA W STREFIE CZYTELNIKA, wiec konkretne wartosci UTC zaleza od
# `PUBLISH_TIMEZONE`. Przy dostarczonej (America/New_York) 03:00 UTC to
# 23:00 na miejscu; przy Europe/Warsaw to 05:00 rano i wyciszac nie musi.
for h, opis in ((3, "23:00 ET"), (5, "01:00 ET"), (9, "05:00 ET")):
    wolno, powod = config.pora_na_publikacje(o(h, 0, dzien=31))
    sprawdz_nasze("  %02d:00 UTC (%s) nadal wyciszone" % (h, opis),
                  not wolno, powod)

# A TO OBOWIAZUJE PRZY KAZDEJ STREFIE: godziny poza oknem maja byc wyciszone,
# i to wlasnie z powodu snu publicznosci. Liczymy je z konfiguracji.
_od, _do = config.OKNO_PUBLIKACJI_ET
_poza = [g for g in range(24) if not (_od <= g < _do)]
_wyciszone = [g for g in _poza
              if not config.pora_na_publikacje(
                  o((g - int(o(12, 0).astimezone(
                      __import__("zoneinfo").ZoneInfo(config.PUBLISH_TIMEZONE)
                  ).utcoffset().total_seconds() // 3600)) % 24, 0))[0]]
sprawdz("kazda godzina poza oknem jest wyciszona",
        len(_wyciszone) == len(_poza),
        "wyciszone %d z %d godzin poza oknem %s"
        % (len(_wyciszone), len(_poza), config.OKNO_PUBLIKACJI_ET))
sprawdz("i powod mowi o spiacej publicznosci",
        "spi" in config.pora_na_publikacje(o(3, 0))[1])

print()
print("=== 4. OKNO DOTYCZY NOTEK, NIE KOMENTARZY ===")
rp = pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8")

# MIERZONE NA DRZEWIE SKLADNI, NIE W OKNIE 1800 ZNAKOW.
#
# Stalo tu ciecie zrodla na sztywne okno od `wolno, powod = ...` i szukanie
# w nim napisow. Wada, ktorej ten plik pilnuje, blokowala JEDEN Z PIECIU
# PRZEBIEGOW CODZIENNIE — najdrozsza z opisanych w repozytorium — a wystarczylo
# zapisac ja inaczej (`na_teraz['komentarze']=0`, petla po kluczach) albo
# przesunac kod o 1800 znakow, zeby test zamilkl.
#
# Pytamy wiec o GALAZ, nie o odleglosc w znakach: znajdujemy `if`, ktorego
# warunek dotyczy `wolno`, i patrzymy, co ta galaz PRZYPISUJE.
import ast as _ast_o
_drzewo = _ast_o.parse(rp)

def _klucz(cel):
    """Nazwa klucza w `na_teraz[...]`, albo None."""
    if not isinstance(cel, _ast_o.Subscript):
        return None
    if getattr(cel.value, "id", "") != "na_teraz":
        return None
    s = cel.slice
    return s.value if isinstance(s, _ast_o.Constant) else None

_galezie = [n for n in _ast_o.walk(_drzewo) if isinstance(n, _ast_o.If)
            and any(getattr(x, "id", "") == "wolno" for x in _ast_o.walk(n.test))]
sprawdz("galaz okna publikacji istnieje w drzewie", len(_galezie) >= 1,
        len(_galezie))

_zerowane = set()
for _g in _galezie:
    for _n in _ast_o.walk(_g):
        if isinstance(_n, _ast_o.Assign):
            for _c in _n.targets:
                k = _klucz(_c)
                if k and isinstance(_n.value, _ast_o.Constant) and _n.value.value == 0:
                    _zerowane.add(k)
sprawdz("poza oknem notki ida na zero", "notki" in _zerowane, sorted(_zerowane))
sprawdz("a komentarze NIE sa zerowane", "komentarze" not in _zerowane,
        "zerowane w galezi okna: %s" % sorted(_zerowane))

# KONTRDOWOD: gdyby wykrywacz nie widzial przypisan, obie asercje przechodzilyby
# pusto. Sprawdzamy, ze widzi CHOC JEDNO.
sprawdz("wykrywacz naprawde widzi przypisania", bool(_zerowane), _zerowane)
sprawdz("i widac to w logu przebiegu",
        "komentarze IDA" in rp)

print()
print("=== 5. UZASADNIENIE JEST W KODZIE, NIE TYLKO W COMMICIE ===")
# Zeby ktos za miesiac nie „przywrocil" bramki jako oczywistej.
cfg = pathlib.Path("agent-v2/config.py").read_text(encoding="utf-8")
sprawdz("kod podaje koszt blokady", "20% dziennej zdolnosci" in cfg)
sprawdz("i mowi, ze zrodla sie nie zgadzaly",
        "NASZE WLASNE ZRODLA SIE NIE ZGADZAJA" in cfg)
sprawdz("run.py tlumaczy, czemu komentarz to nie notka",
        "pod CUDZYM tekstem" in rp)

print()
print("=== 6. KONTRDOWOD: STARA REGULA MUSIALA TU BLOKOWAC ===")
# Gdyby 13:00 ET przechodzilo takze przed poprawka, nie bylo by czego naprawiac.
from zoneinfo import ZoneInfo  # noqa: E402
et = o(17, 0).astimezone(ZoneInfo(config.PUBLISH_TIMEZONE))
# KONTRDOWOD PRZYPIETY DO DOSTARCZONEJ STREFY. 17:00 UTC to 13:00
# tylko w America/New_York; opisuje konkretny incydent z produkcji.
sprawdz_nasze("17:00 UTC to naprawde 13:00 ET", et.hour == 13, et.hour)
sprawdz_nasze("a 13 jest na liscie najgorszych godzin",
        et.hour in config.WORST_NOTE_HOURS)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
