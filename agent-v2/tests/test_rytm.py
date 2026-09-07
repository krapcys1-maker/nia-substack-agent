"""Test rytmu publikacji: notki nie moga wychodzic parami."""
import pathlib
import statistics
import sys

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


# Asercje o DOSTARCZONYCH wartosciach, pomijane widocznie,
# gdy operator ma wlasne w `konfiguracja.toml`.
sprawdz_nasze = wlasna_konfiguracja.tylko_nasze(sprawdz)


print("=== 1. ODSTEP MIEDZY NOTKAMI ===")
dol, gora = config.ODSTEPY["notka"]
print("    %s-%s min (bylo 10-25)" % (dol // 60, gora // 60))
# PRZYCIETE 30 sierpnia 2026 z 45-90 na 35-65 min. Prog nie zostal ROZLUZNIONY
# dla wygody — zostal PRZELICZONY, bo poprzedni czynil norme nieosiagalna:
# budzet na notki w przebiegu to 81 min, dwie notki przy odstepie 68 min
# potrzebowaly 76 min, a zwloka przed pierwsza notka zjadala kolejne 20.
# 96 min przy budzecie 81 znaczy, ze druga notka nie miala prawa wyjsc — i przez
# pietnascie dni nie wychodzila (2,9 notki dziennie przy normie 5).
#
# To, czego ten test pilnuje, sie NIE zmienilo: odstep ma byc na tyle dlugi, zeby
# notki nie wychodzily parami kilkanascie minut po sobie. Pol godziny do godziny
# to nadal czlowiek wracajacy do tematu, a nie przebieg widoczny na osi czasu.
sprawdz("dolna granica co najmniej 30 min", dol >= 1800, dol)
sprawdz("gorna co najmniej 60 min", gora >= 3600, gora)
sprawdz("STARY odstep 10-25 min dawal pary (test rozroznia)", dol > 1500)
# DWIE NOTKI MUSZA SIE ZMIESCIC — to jest wlasciwy prog, a nie sama liczba minut.
# Bez tego sprawdzenia mozna znowu wydluzyc odstep i cicho wrocic do 57 procent.
_budzet = (config.LIMIT_CZASU_PRZEBIEGU_S - config.ZAPAS_CZASU_S)     * config.UDZIAL_CZASU_NA_NOTKI
_zwloka = sum(config.ZWLOKA_PRZED_NOTKAMI) / 2
_dwie = 2 * config.CZAS_DZIALANIA_S + (dol + gora) / 2
sprawdz("dwie notki mieszcza sie w budzecie PO odjeciu zwloki",
        _dwie <= _budzet - _zwloka,
        "potrzeba %.0f min, zostaje %.0f min" % (_dwie / 60, (_budzet - _zwloka) / 60))

# KOMENTARZE WYDLUZONE, nie skrocone — decyzja wlasciciela z 30 sierpnia:
# „co najmniej 5 min opoznienia po komentarzu, zeby nie wygladal jak bot
# nakurwiajacy 10 komentarzy w 10 sekund". Dolna granica byla 3 min i to za
# malo widac na osi czasu przy serii komentarzy.
sprawdz("komentarz ma co najmniej 5 min odstepu",
        config.ODSTEPY["komentarz"][0] >= 300, config.ODSTEPY["komentarz"])
sprawdz("i nadal jest krotszy niz notka (to inna czynnosc)",
        config.ODSTEPY["komentarz"][1] < config.ODSTEPY["notka"][0],
        (config.ODSTEPY["komentarz"], config.ODSTEPY["notka"]))
# ODPOWIEDZI TEZ, i to nie jest ozdoba tej reguly. Komentarze pod NOTKAMI ida
# sciezka `wystaw_odpowiedz`, wiec odstep "odpowiedz" rzadzi wlasnie tym, co sie
# psulo najbardziej: 30 procent porazek pod notkami wobec 7 pod postami.
# Zmierzone po pozycji w serii: 10% przy pierwszej akcji, 31% przy drugiej,
# 50% przy czwartej — przy odstepie srednio czterech minut.
sprawdz("odpowiedz ma co najmniej 5 min odstepu",
        config.ODSTEPY["odpowiedz"][0] >= 300, config.ODSTEPY["odpowiedz"])
sprawdz("kazda wypowiedz do czlowieka ma co najmniej 5 min",
        min(config.ODSTEPY[k][0] for k in ("komentarz", "odpowiedz")) >= 300,
        {k: config.ODSTEPY[k] for k in ("komentarz", "odpowiedz")})
sprawdz("polubienia nadal najkrotsze",
        config.ODSTEPY["lajk"][1] < config.ODSTEPY["komentarz"][0])

print()
print("=== 2. ZWLOKA PRZED PIERWSZA NOTKA ===")
zd, zg = config.ZWLOKA_PRZED_NOTKAMI
print("    0-%s min" % (zg // 60))
sprawdz("zwloka istnieje", zg > 0)
# PRZYCIETE 30 sierpnia 2026 z 40 na 15 min. Zadanie zwloki to ROZMYCIE
# MINUTY STARTU, a nie dlugosc sama w sobie — kwadrans losowego przesuniecia
# ukrywa moment startu tak samo dobrze jak czterdziesci minut. Roznica jest w
# cenie: zwloka szla z budzetu notek, o czym planista nie wiedzial, i to ona
# wypychala druga notke poza przebieg.
sprawdz("zwloka rozmywa start (co najmniej 10 min w gorze)", zg >= 600, zg)
sprawdz("ale nie zjada juz miejsca na druga notke",
        sum(config.ZWLOKA_PRZED_NOTKAMI) / 2 <= 900,
        config.ZWLOKA_PRZED_NOTKAMI)
sprawdz("moze byc zerowa (nie zawsze czekamy)", zd == 0, zd)

print()
print("=== 3. CZY WSZYSTKO MIESCI SIE W CZASIE PRZEBIEGU ===")
budzet_czasu = config.LIMIT_CZASU_PRZEBIEGU_S - config.ZAPAS_CZASU_S
najgorszy = zg + gora            # zwloka + jeden odstep miedzy dwiema notkami
print("    najgorszy przypadek: %s min, budzet przebiegu: %s min"
      % (najgorszy // 60, budzet_czasu // 60))
sprawdz("dwie notki mieszcza sie w najgorszym razie", najgorszy < budzet_czasu,
        "%s >= %s" % (najgorszy, budzet_czasu))
sprawdz("trzy notki juz NIE musza sie zmiescic — od tego jest zostal_czas",
        zg + 2 * gora > budzet_czasu)

print()
print("=== 4. SYMULACJA DNIA: CZY ZNIKAJA PARY ===")
import random  # noqa: E402

random.seed(3)
STARTY = [11 * 60 + 20, 19 * 60 + 20, 23 * 60 + 40]   # UTC, w minutach


def dzien(odstep, zwloka):
    czasy = []
    for start in STARTY:
        t = start + random.uniform(0, 25) + random.uniform(*zwloka) / 60
        for _ in range(2):
            czasy.append(t % (24 * 60))
            t += random.uniform(*odstep) / 60
    return sorted(czasy)


def najkrotszy_odstep(czasy):
    return min(b - a for a, b in zip(czasy, czasy[1:]))


stare = [najkrotszy_odstep(dzien((600, 1500), (0, 0))) for _ in range(200)]
nowe = [najkrotszy_odstep(dzien(config.ODSTEPY["notka"],
                                config.ZWLOKA_PRZED_NOTKAMI)) for _ in range(200)]
print("    STARY: najkrotszy odstep w dniu, mediana %.0f min" % statistics.median(stare))
print("    NOWY:  najkrotszy odstep w dniu, mediana %.0f min" % statistics.median(nowe))
sprawdz("stary rytm dawal pary ponizej 30 min",
        statistics.median(stare) < 30, statistics.median(stare))
sprawdz("nowy rytm nie daje par ponizej 40 min",
        statistics.median(nowe) >= 40, statistics.median(nowe))
sprawdz("poprawa co najmniej dwukrotna",
        statistics.median(nowe) > 2 * statistics.median(stare))

print()
print("=== 5. GODZINY ZOSTAJA TE, KTORE WYBRALISMY ===")
zegar = pathlib.Path("agent-v2/systemd/nia-agent.timer").read_text(encoding="utf-8")
for g in ("11:20:00", "19:20:00", "23:40:00"):
    sprawdz("zegar nadal ma %s UTC" % g, g in zegar)
sprawdz_nasze("okno publikacji nietkniete", config.OKNO_PUBLIKACJI_ET == (6, 22),
        config.OKNO_PUBLIKACJI_ET)

zrodlo = pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8")
sprawdz("run.py stosuje zwloke", "ZWLOKA_PRZED_NOTKAMI" in zrodlo)
sprawdz("zwloka TYLKO przy prawdziwym wystawianiu",
        "if wyslij and not config.PERSONA_WLACZONA:" in zrodlo.split("ZWLOKA_PRZED_NOTKAMI")[0][-260:])

print()
print("=== 6. PLAN PRZYCIETY DO ZEGARA ===")

import time as _t  # noqa: E402
import run as _run  # noqa: E402

budzet = config.LIMIT_CZASU_PRZEBIEGU_S - config.ZAPAS_CZASU_S
_run._KONIEC_CZASU = _t.time() + budzet
n = _run.zmiesci_sie("notka", 4, config.UDZIAL_CZASU_NA_NOTKI)
# NA PRZEBIEG PRZYPADA TERAZ OKOLO CZTERECH KOMENTARZY, nie czternascie:
# norma poszla z 10 na 19 dziennie, ale przebiegow jest piec zamiast trzech, a
# odstep wzrosl z 3-8 na 5-15 min. Pytanie „czy czternascie wejdzie w jeden
# przebieg" przestalo cokolwiek znaczyc — czternascie przy dziesieciominutowym
# odstepie to trzy godziny i wejsc NIE MA prawa.
import math as _m   # noqa: E402
na_przebieg = _m.ceil(sum(config.KOMENTARZE_DZIENNIE) / 2 / config.PRZEBIEGOW_DZIENNIE)
k = _run.zmiesci_sie("komentarz", na_przebieg)
print("    pelny przebieg (%s min): notki %s/4, komentarze %s/%s"
      % (budzet // 60, n, k, na_przebieg))
sprawdz("cztery notki NIE mieszcza sie w przebiegu", n < 4, n)
sprawdz("ale dwie sie mieszcza (dzien ma 5 notek na %d przebiegow)"
        % config.PRZEBIEGOW_DZIENNIE, n >= 2, n)
sprawdz("dzienna porcja komentarzy wchodzi w przebieg w calosci",
        k == na_przebieg, "%s z %s" % (k, na_przebieg))
# KONTRDOWOD: przy starym odstepie 3-8 min i czternastu na przebieg pytanie bylo
# latwe. Sprawdzamy, ze nowy odstep NAPRAWDE ogranicza — inaczej test niczego
# nie pilnuje.
sprawdz("a czternascie komentarzy juz NIE (test rozroznia)",
        _run.zmiesci_sie("komentarz", 14) < 14)

_run._KONIEC_CZASU = _t.time() + 600
sprawdz("gdy zostalo 10 min, notek prawie nie ma",
        _run.zmiesci_sie("notka", 4, config.UDZIAL_CZASU_NA_NOTKI) <= 1)
sprawdz("i komentarzy tez", _run.zmiesci_sie("komentarz", 14) <= 2)

_run._KONIEC_CZASU = _t.time() + 60
sprawdz("przy sekundach do konca nie obiecujemy nic ponad jedno",
        _run.zmiesci_sie("notka", 4, config.UDZIAL_CZASU_NA_NOTKI) <= 1)

_run._KONIEC_CZASU = None
sprawdz("uruchomienie reczne bez limitu nic nie przycina",
        _run.zmiesci_sie("notka", 4, 0.6) == 4)
sprawdz("zero zostaje zerem", _run.zmiesci_sie("notka", 0, 0.6) == 0)

# KONTRDOWOD: formula liczaca przerwe PO KAZDYM dzialaniu dawala o polowe za malo
_run._KONIEC_CZASU = _t.time() + budzet
odstep = sum(config.ODSTEPY["notka"]) / 2
zostalo = budzet * config.UDZIAL_CZASU_NA_NOTKI
zle = int(zostalo // (odstep + config.CZAS_DZIALANIA_S))
dobrze = _run.zmiesci_sie("notka", 4, config.UDZIAL_CZASU_NA_NOTKI)
print("    stara formula (przerwa po kazdej): %s, poprawna (n-1 przerw): %s"
      % (zle, dobrze))
sprawdz("poprawka n-1 przerw naprawde zmienia wynik (test rozroznia)",
        dobrze > zle, (dobrze, zle))

zrodlo = pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8")
sprawdz("dzien() przycina plan do czasu", 'zmiesci_sie("notka"' in zrodlo)
sprawdz("notki maja pierwszenstwo, ale nie caly przebieg",
        "UDZIAL_CZASU_NA_NOTKI" in zrodlo)

print()
print("=== WYNIK: %s zdanych, %s oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
