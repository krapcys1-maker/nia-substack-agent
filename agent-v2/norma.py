"""Ile agent naprawde zrobil, dzien po dniu, wobec normy.

PO CO TO ISTNIEJE. Wlasciciel zobaczyl na Substacku, ze notek jest malo, i
dowiedzial sie o tym SAM — patrzac na profil, nie od systemu. Normy byly
policzone (`config.normy_dzienne`), alarm mial prog (`PROG_ALARMU_WOLUMENU`),
a mimo to przez pietnascie dni realizacja notek stala na 57 procent i nikt
tego nie widzial. Licznik, ktorego nie da sie uruchomic jednym poleceniem,
nie jest licznikiem.

CO POKAZUJE. Wylacznie PRODUKCJE — ile agent wystawil. Odbiór (wyswietlenia,
polubienia od czytelnikow, subskrypcje z pozycji) mieszka w `statystyki.py` i
jest osobnym pytaniem: tam chodzi o to, co przyszlo z powrotem.

ZRODLEM JEST DZIENNIK, nie Substack. To jedyny zapis, w ktorym atrybucja jest
z definicji poprawna — dziennik notuje wylacznie wlasne dzialania. Kanal
profilu pokazuje takze notki pisane recznie przez wlasciciela i wlasnie to
mylenie kosztowalo agenta przydzial: 29 sierpnia profil mial piec notek, z
czego dwie byly bota.

JAK CZYTAC TABELE. `5/10` to zrobione wobec PLANU tego dnia (z `budzety.json`),
nie wobec dzisiejszej normy. Znak zapytania nigdy nie jest zerem: `?` znaczy
„o tym dniu nie wiemy nic", a `5/?` — „wiemy, ile wyszlo, nie wiemy, ile bylo
zaplanowane"; pozycja bez ani jednego zmierzonego dnia ma `-` takze w SREDNIEJ
i w `% NORMY`, nigdy `0`. Tylda (`0/5~`) znaczy „planu nie zapisano i nie ma
sladu przebiegu, wiec plan jest OSZACOWANY z normy dobowej" — to jedyna
liczba w tabeli, ktora nie jest pomiarem. Dzien bez ani jednego wpisu ma wlasny
wiersz i podpis; nie znika z tabeli, bo dzien calkowitej awarii jest jedyna
rzecza, ktorej ten licznik ma NIE przegapic.

DZIEN BIEZACY jest rozliczany z tej czesci planu, ktora POWINNA byla juz wyjsc
o tej porze — z harmonogramu w `systemd/nia-agent.timer`, nie z tego, ile
przebiegow sie odbylo. Inaczej licznik nagradzalby bezczynnosc: doba, w ktorej
nie wyszlo NIC, meldowala do polnocy `% PLANU 100%`, a doba z jedna udana
notka o poranku — 84%.

    python agent-v2/norma.py            # ostatnie 14 dni
    python agent-v2/norma.py --dni 30
    python agent-v2/norma.py --dzis     # sam dzisiejszy stan, krotko
"""
import argparse
import collections
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config  # noqa: E402

DZIENNIK = config.DATA_DIR / "dziennik.jsonl"

# Kolejnosc kolumn: od tego, co wlasciciel sprawdza najczesciej.
RODZAJE = ("notka", "komentarz", "polubienie", "restack", "subskrypcja",
           "obserwacja")

# Pozycje NIEWYKONALNE nie sa porazka i nie moga zanizac wyniku na zawsze.
#
# PUSTE OD 1 WRZESNIA 2026 I TO JEST NAJWAZNIEJSZA ZMIANA W TYM PLIKU.
#
# Stalo tu `{"obserwacja": "Substack zdjal przycisk Follow"}` i przez dziewiec
# dni tabela TLUMACZYLA ZERO ZDANIEM, KTORE NIE BYLO PRAWDA. Skutek jest gorszy
# niz samo zero: zero z wyjasnieniem przestaje wygladac na problem, wiec nikt
# go nie sprawdza. Agent nie obserwowal nikogo przez dziewiec dni i zadna
# rubryka o tym nie krzyczala — bo ta rubryka byla wyciszona recznie.
#
# Pomiar z 23 sierpnia byl dobry: na szesciu profilach slowa „Follow" naprawde
# nie bylo w HTML. Zly byl wniosek. Przycisk siedzi w menu pod kolkiem „...",
# ktore Substack dorysowuje DOPIERO PO KLIKNIECIU — w HTML zamknietej strony
# nie ma go i byc nie moze. Sprawdzone ponownie 1 wrzesnia 2026 na zywej sesji,
# na szesciu profilach; szczegoly i zmierzone etykiety stoja przy
# `browser.obserwuj_profil`.
#
# CO MUSI ZAJSC, ZEBY TU COS WROCILO. Wpis na tej liscie ma sens wylacznie
# wtedy, gdy zdolnosci NIE DA SIE wykonac — a nie wtedy, gdy nie umiemy jej
# wykonac. Roznicy nie rozstrzyga sie czytaniem HTML-a: trzeba otworzyc menu
# i zobaczyc, czego w nim nie ma.
NIEWYKONALNE: dict[str, str] = {}

# KIEDY PROCENT COS ZNACZY — CZTERY LICZBY, CZTERY ROZNE PYTANIA.
#
# Prog 60% stosowany bez wzgledu na wielkosc planu robi z licznika generator
# szumu. `subskrypcja` ma norme 0,53 na dobe, czyli plan okolo 3,7 na tydzien:
# jedna mniej zostawia okolo 73%, ale dwie mniej juz okolo 46%. Tak samo
# restacki: plan 1-2 na dzien, wiec kazdy dzien bez restacka to 0% i wykrzyknik
# w tabeli. `obserwacja` byla przed tym chroniona lista NIEWYKONALNE,
# `subskrypcja` nie byla przez nic.
#
# OD 1 WRZESNIA 2026 NIEWYKONALNE JEST PUSTE, wiec `obserwacja` i `subskrypcja`
# opieraja sie juz WYLACZNIE o te progi — i to jest zamierzone. Oslona ma byc
# prog liczony z planu, a nie reczny wpis mowiacy „tego sie nie da".
#
# ALE UZASADNIENIE, KTORE TU STALO, PRZESTALO BYC PRAWDA TEGO SAMEGO DNIA.
# Stalo: „obserwacja (plan ~1,2 na dobe) (...) blok martwy przez tydzien daje
# okolo 8-9 brakujacych sztuk, czyli wiecej niz `MIN_BRAKOW_W_OKNIE_DO_ALARMU`
# (4), wiec alarm zadziala". Po odwroceniu budzetow (`FOLLOW_MIESIECZNIE`
# 30-44 -> 10-16, `SUBSKRYPCJE_MIESIECZNIE` 6-12 -> 12-20) plan obserwacji to
# 0,433 na dobe, czyli 3,03 na tydzien — PONIZEJ tej bramki, nie powyzej;
# subskrypcji 0,533, czyli 3,73 — takze ponizej. Zmierzone na prawdziwym
# `stages.budzet_dnia`: suma planu w oknie 7 dni to srednio 3,00 obserwacji
# i 3,57 subskrypcji, a `>= 4` osiaga tylko 34% i 53% okien.
#
# BLOK CALKOWICIE MARTWY BUDZI DALEJ — nie ta bramka, tylko
# `MIN_PLAN_W_OKNIE_DO_ALARMU_O_ZERZE`, ktora zera nie tlumi (99% okien
# siedmiodniowych ma plan obserwacji >= 1, 100% dla subskrypcji). Dziura byla
# POMIEDZY: blok POLOWICZNIE martwy. Zmierzone — okno 7 dni, plan 3, wykonane
# 1: `proc` 33% ponizej progu 60, ale `brakuje` = 2 < 4, a `martwa` = False, bo
# `wykonane != 0`. Pozycja szla na liste „ponizej progu, ale za malo brakow" i
# `norma.py` konczyla kodem 0 — czyli glowny kanal umieral po cichu, a licznik
# to tlumaczyl. Ta klasa wady kosztowala juz dziewiec dni.
#
# DLATEGO PROGOW JEST TERAZ CZTERY, a czwarty (`..._O_POLOWIE`) opisuje wprost
# blok polowiczny. Bramka od brakow zostaje nietknieta — nowy warunek tylko
# DOKLADA alarmy, wiec zaden dotychczasowy nie znika.
#
# BYLA TU JEDNA STALA (`MIN_PLAN_DO_ALARMU = 5`) I RZADZILA DWIEMA SKALAMI:
# `_znak` porownywal ja z planem DZIENNYM (jedna kratka tabeli), a alarm na
# dole z SUMA PLANU W CALYM OKNIE. Zmierzone: 7 dni, plan restackow 2/dobe,
# zero wykonanych — tabela przez caly tydzien pokazywala `0/2` BEZ ZNAKU
# (2 < 5), a dol drukowal „PONIZEJ PROGU 60%: restack" (14 >= 5) i zwracal
# kod 1. Docstring `_znak` obiecywal dokladnie odwrotnie: „zeby nie bylo tak,
# ze tabela krzyczy o pozycji, o ktorej alarm swiadomie milczy". Jedna liczba
# nie moze rzadzic obiema skalami, wiec sa osobne i maja rozne nazwy.
#
# TRZECIA DOSZLA, BO BRAMKA ALARMU WYCISZALA POZYCJE MARTWA, a CZWARTA — bo
# wyciszala pozycje POLOWICZNIE martwa. Pytania sa cztery: „czy warto stawiac
# wykrzyknik w tej kratce" (plan JEDNEGO dnia), „czy ten niedobor to juz praca,
# a nie kostka" (ile SZTUK brakuje w oknie), „czy tu w ogole cokolwiek wyszlo"
# (zero, ktore nie podlega bramce) i „czy brakuje wiecej, niz wyszlo" (polowa
# planu przy planie, ktory da sie polowic). Szczegoly przy kazdej ze stalych.
#
# Realne plany dzienne (`stages.budzet_dnia`): notki 5, komentarze 15-23,
# lajki 10-16, restacki 1-2, subskrypcje 0 albo 1, obserwacje 0 albo 1.

# DLA JEDNEJ KRATKI TABELI — porownywany z planem NA TEN DZIEN.
#
# Trzy, bo przy planie 3 jeden brakujacy element to 33%, a przy planie 2 —
# 50%, czyli liczba nieodroznialna od zaokraglenia. NIE PIEC: plan notek to
# `len(config.NOTE_MIX_OTHER_DAY)`, czyli DOKLADNIE 5, wiec prog 5 stawial
# najwazniejsza pozycje licznika na samej granicy — `_znak(0, 4) == ""`, a
# `_znak(0, 5) == "!!"`. Skrocenie tej krotki o JEDEN element wyciszalo
# wykrzykniki przy notkach, czyli przy pozycji, od ktorej caly licznik sie
# zaczal, i nic by tego nie zauwazylo. Przy progu 3 trzeba by skrocic krotke
# z 5 do 2. Granicy pilnuje `tests/test_dzien_awarii.py`.
MIN_PLAN_DZIENNY_DO_ZNAKU = 3

# DLA ALARMU NA DOLE — LICZYMY BRAKUJACE SZTUKI, NIE WIELKOSC PLANU.
#
# Bylo tu `plany[r] >= 10`, czyli bramka na SUME PLANU W OKNIE, i wyciszala
# rzecz, ktorej wyciszyc nie wolno: pozycje CALKOWICIE MARTWA. Zmierzone przy
# realnych budzetach (`stages.budzet_dnia`, dwiescie przesunietych okien):
#
#   * subskrypcje — suma planu 2,0 na 7 dni i 3,9 na 14 dni, NIGDY 10 (przy
#     `--dni 40` dopiero w 62% okien). Blok subskrypcji padajacy na amen
#     (Substack przestawia przycisk, kazda proba nieudana) dawal wiec 0% z
#     planu 4, kod wyjscia 0 i linijke „plan za maly na alarm" — na zawsze;
#   * restacki — suma planu na 7 dni: min 8, srednio 10,7, max 14. Prog 10
#     lezal w SRODKU tego rozkladu, wiec ta sama martwa pozycja przy `--dni 7`
#     raz krzyczala, a raz milczala (20% okien ponizej 10), za to przy
#     `--dni 14` (suma 22) krzyczala zawsze. Dlugosc okna jest wyborem
#     czlowieka, a nie wlasnoscia awarii.
#
# CZTERY BRAKI, BO TYLE ZNACZYLA STARA STALA NA PROGU. „Plan >= 10" przy progu
# 60% to dokladnie „brakuje >= 4 sztuki" (0,4 * 10) — i to zdanie stalo w jej
# wlasnym komentarzu. Liczymy wiec wprost braki: na progu obie reguly daja to
# samo, a im glebiej ponizej progu, tym nowa jest czulsza (przy wykonaniu 20%
# cztery braki to plan 5, nie 10). ZADNEGO alarmu ze starej reguly nowa nie
# gubi: proc < 60 i plan >= 10 daje braki > 4 zawsze.
#
# Cztery, a nie dwie: dwie brakujace sztuki to jeszcze pech losowania (plan
# subskrypcji bywa 2 na tydzien, wiec jedna mniej to 50%), cztery to juz
# czterokrotnie powtorzona porazka.
#
# CO ZOSTAJE ZALEZNE OD OKNA I DLACZEGO TAK MA BYC. Braki sie uzbieraja, wiec
# awaria POLOWICZNA moze milczec na krotkim oknie i odezwac sie na dluzszym:
# subskrypcje wykonane w polowie to 2 braki na 7 dni (cisza) i 4 na 14 (alarm).
# To nie jest ta sama wada, co poprzednio — kierunek jest jednostajny. Dluzsze
# okno moze wynik tylko WZMOCNIC, nigdy wyciszyc, bo braki rosna razem z nim, a
# pozycja MARTWA budzi w kazdym oknie. Stara bramka lamala oba te warunki:
# przy `--dni 7` restacki wypadaly raz nad, raz pod progiem 10.
MIN_BRAKOW_W_OKNIE_DO_ALARMU = 4

# ZERO NIE JEST ZAOKRAGLENIEM MALEGO PLANU — I DLATEGO NIE PODLEGA BRAMCE.
#
# Bramka wyzej ma tlumic wyniki BLISKIE progu, gdzie procent robi sie
# nieodroznialny od kostki. Zero jest skrajnoscia, nie zaokragleniem: pozycja,
# ktora przy niezerowym planie nie wystawila w calym oknie ANI JEDNEJ sztuki,
# nie jest pechem tylko martwym blokiem — i jest taka samo martwa przy `--dni 7`
# co przy `--dni 14`. To jedyny werdykt, ktory nie ma prawa zalezec od okna.
#
# JEDNA CALA SZTUKA, bo plan ponizej jednej to plan, ktorego tego dnia nie ma:
# budzet zapisuje liczby CALKOWITE (`stages.budzet_dnia`), wiec subskrypcje
# maja 0 albo 1 na dobe, a ulamek 0,3 bierze sie z podstawienia normy albo z
# przyciecia dnia biezacego do naleznych przebiegow. Przy planie 0,3 zero jest
# zgodnoscia z planem, a nie awaria. Zmierzone: przy realnych budzetach suma
# planu subskrypcji siega 1 w 91% okien siedmiodniowych i w 100% okien
# czternastodniowych — martwy blok budzi wiec w obu, a nie tylko w dluzszym.
MIN_PLAN_W_OKNIE_DO_ALARMU_O_ZERZE = 1

# BLOK POLOWICZNIE MARTWY — BRAKUJE WIECEJ, NIZ WYSZLO.
#
# TA STALA POWSTALA, BO BRAMKA OD BRAKOW NIE DAWALA SIE OSIAGNAC NA RZADKICH
# KANALACH. „Brakuje >= 4" przy planie tygodniowym 3,0 (obserwacja) i 3,7
# (subskrypcja) jest wieksze niz CALY plan, wiec zaden poziom wykonania poza
# zerem nie mial prawa jej ruszyc. Bramka, ktorej nie da sie osiagnac, nie jest
# filtrem szumu tylko trwalym wyciszeniem — a trwale wyciszenie to dokladnie to,
# czym byla `NIEWYKONALNE` i za co zaplacilismy dziewiec dni bez obserwacji.
#
# ZMIERZONE (okno 7 dni, plan 3, wykonane 1): 33% wykonania, `brakuje` 2,
# `martwa` False. Przed ta stala: cisza i kod wyjscia 0. Po niej: alarm i kod 1.
#
# WARUNEK JEST STRICTE OSTRZEJSZY OD PROGU 60%: „wykonane * 2 <= plan", czyli
# BRAKUJE CO NAJMNIEJ TYLE, ILE WYSZLO. Pas 50-60% zostaje wyciszony, bo przy
# planie 3-6 sztuk rozstrzyga go pojedyncza sztuka i to naprawde jest kostka.
#
# TRZY, A NIE DWIE — I TO JEST TA SAMA GRANICA, CO W `_znak`. Przy planie 2
# „polowa" to jeden brak, czyli dokladnie ten alarm od kostki, dla ktorego
# `MIN_BRAKOW_W_OKNIE_DO_ALARMU` w ogole powstalo („plan subskrypcji bywa 2 na
# tydzien, wiec jedna mniej to 50%"). Przy planie 3 „polowa" to juz dwa braki
# na trzy zaplanowane sztuki.
#
# CO DOKLADNIE DOKLADA, POLICZONE WPROST. Nowy warunek jest OR-em, wiec nie
# gubi zadnego starego alarmu; nowe sa tylko te pary (plan, wykonane), ktore
# mijaly stare bramki: (3,1), (4,1), (4,2), (5,2), (6,3). Wszystkie leza w
# przedziale planu 3-6, czyli dokladnie tam, gdzie wypadaja tygodniowe plany
# obserwacji i subskrypcji — restacki (plan 7 dni: min 8, srednio 10,7) i
# pozostale pozycje budzily sie juz wczesniej brakami. Cisza zostaje tam, gdzie
# ma zostac: (2,1) — jedna sztuka z dwoch — i (7,4) — 57%, czyli o wlos od
# progu.
#
# ZALEZNOSC OD OKNA IDZIE W DOZWOLONYM KIERUNKU. Kanal stojacy trwale na
# polowie planu budzi w KAZDYM oknie, w ktorym plan siega trzech sztuk (dla
# obserwacji: 7 dni w 63% okien, 14 dni w 97%), a dluzsze okno moze go tylko
# wzmocnic — nigdy wyciszyc.
MIN_PLAN_W_OKNIE_DO_ALARMU_O_POLOWIE = 3

# Godziny przebiegow CZYTAMY z jednostki systemd, a nie przepisujemy tutaj.
# `run.py:265-268` nazywa te zasade wprost („powtorzenie ich tutaj zlamaloby
# zasade jednej liczby w jednym miejscu"), a `tests/test_rytm.py:132` juz ten
# plik czyta z Pythona.
ZEGAR = Path(__file__).resolve().parent / "systemd" / "nia-agent.timer"


def budzety_dzienne() -> dict:
    """Ile agent SOBIE ZALOZYL kazdego dnia — z pliku, nie z dzisiejszej konfiguracji.

    WYKONANIE PLANU I AMBICJA TO DWA ROZNE PYTANIA. `config.normy_dzienne()`
    mowi, ile POWINNO wychodzic docelowo; zapisany budzet mowi, ile agent w tym
    dniu w ogole zamierzal. Mierzenie wykonania ambicja daje dwa falszywe
    alarmy naraz: przez pierwsze 30 dni budzet leci dolna polowa widelek
    (rozbieg), a kazda zmiana widelek przepisuje historie wstecz.

    Zmierzone 30 sierpnia: 29 sierpnia agent zalozyl 10 komentarzy i zrobil 6 —
    60% wlasnego planu — a licznik pokazywal 32%, bo widelki zmienily sie tego
    samego dnia z (8,12) na (15,23).
    """
    import json
    plik = config.DATA_DIR / "budzety.json"
    try:
        stan = json.loads(plik.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if not isinstance(stan, dict):
        return {}
    # Przepisujemy na nazwy z dziennika, zeby licznik nie musial tlumaczyc.
    wynik = {}
    for dzien, wpis in stan.items():
        # NARZEDZIE POMIAROWE NIE MOZE UMIERAC NA ZEPSUTYM WPISIE. Ta petla
        # stala POZA `try` z odczytu pliku, wiec wartosc dnia inna niz slownik
        # („2026-08-31": "psu") wywracala caly raport `AttributeError`-em i
        # kasowala wszystkie pozostale liczby.
        if not _poprawna_data(dzien) or not isinstance(wpis, dict):
            continue
        b = wpis.get("budzet")
        # BRAK ZAPISU TO NIE JEST ZAPISANE ZERO. Bylo tu `or {}`, wiec dzien
        # bez klucza „budzet" dostawal PUSTY SLOWNIK — a pusty slownik nie
        # jest `None`, wiec dzien nie dostawal gwiazdki „*plan nieznany", za to
        # wszystkie szesc pozycji ladowalo na liscie „dopisz je do
        # BUDZET_NA_RODZAJ". Rada byla falszywa: te klucze SA w tej mapie
        # (config.py:1671-1678), brakowalo samego zapisu budzetu.
        if not isinstance(b, dict) or not b:
            continue
        # Wartosc nieliczbowa traktujemy jak brak pozycji, a nie jak plan:
        # `plany[r] += "piec"` wywracalo raport `TypeError`-em.
        wynik[dzien] = {
            config.BUDZET_NA_RODZAJ[k]: float(v)
            for k, v in b.items()
            if k in config.BUDZET_NA_RODZAJ
            and isinstance(v, (int, float)) and not isinstance(v, bool)}
    return wynik


def _data(dzien: str):
    """„2026-08-30" -> datetime w UTC. `cichy_dzien` pyta o obiekt, nie napis."""
    return datetime.strptime(dzien, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def _poprawna_data(dzien) -> bool:
    """Czy da sie z tego zrobic date. Zepsuty wpis ma znikac, nie zabijac raport.

    `2026-08-32` (dzien, ktorego nie ma) i `nie-data-x` wywracaly caly licznik
    `ValueError`-em z `_data`, wiec JEDNA zepsuta linia dziennika kasowala
    wszystkie pozostale liczby. Narzedzie pomiarowe ma wtedy pokazac mniej, a
    nie nie pokazac nic.
    """
    if not isinstance(dzien, str):
        return False
    try:
        _data(dzien)
        return True
    except ValueError:
        return False


def wczytaj(dni: int):
    """(zrobione, nieudane) — liczniki per dzien i rodzaj."""
    granica = (datetime.now(timezone.utc) - timedelta(days=dni)).strftime("%Y-%m-%d")
    zrobione = collections.defaultdict(collections.Counter)
    nieudane = collections.defaultdict(collections.Counter)
    if not DZIENNIK.exists():
        return zrobione, nieudane
    with DZIENNIK.open(encoding="utf-8") as plik:
        for linia in plik:
            linia = linia.strip()
            if not linia:
                continue
            try:
                w = json.loads(linia)
            except ValueError:
                continue
            if not isinstance(w, dict) or w.get("rodzaj") not in RODZAJE:
                continue
            dzien = str(w.get("kiedy") or "")[:10]
            if not dzien or dzien < granica or not _poprawna_data(dzien):
                continue
            (zrobione if w.get("udane") else nieudane)[dzien][w["rodzaj"]] += 1
    return zrobione, nieudane


def slad_dziennika(zalozone: dict):
    """(najstarszy znany dzien, zbior dni z JAKIMKOLWIEK wpisem w dzienniku).

    DWIE RZECZY NARAZ, BO OBIE WYMAGAJA PRZECZYTANIA CALEGO PLIKU i obie pytaja
    o to samo: czy tego dnia agent w ogole zyl. `wczytaj` odsiewa rodzaje spoza
    RODZAJE (norma.py:121), a `browser.py:1138` zapisuje takze
    `rodzaj: "artykul"` — wiec doba z opublikowanym artykulem i dwiema
    odpowiedziami wyglada w `zrobione`/`nieudane` na dobe calkowicie martwa.
    Tutaj liczy sie KAZDY poprawny wpis: artykul nie jest mierzony, ale
    dowodzi, ze maszyna wstala, a to rozstrzyga, czy wolno podstawic
    oszacowanie planu.

    PO CO OSOBNA FUNKCJA. Poczatek okna liczyl sie jako `min(znane | {dzis})`,
    gdzie `znane` bylo juz PRZYCIETE do okna — czyli „pierwszy dzien z danymi
    W OKNIE". A to jest dokladnie ten sygnal, ktory calkowita awaria kasuje:
    im dluzej agent nie dziala, tym pozniej zaczyna sie tabela.
    Zmierzone przed poprawka: `--dni 14`, dane tylko z trzech ostatnich dni ->
    tabela miala trzy wiersze, `% PLANU 100%` i podpis `dni: 3`. Jedenastu
    martwych dni nie bylo widac ani wierszem, ani liczba, ani przypisem.
    Koniec okna byl naprawiony, poczatek nadal przesuwal sie z danymi.

    Zakresu i tak nie ciagniemy przed instalacje — dni sprzed niej nie sa
    awaria, tylko nieistnieniem — ale data instalacji ma sie brac z CALEJ
    historii (dziennik + wszystkie zapisane budzety), nie z okna.
    """
    kandydaci = [d for d in zalozone if _poprawna_data(d)]
    ze_sladem = set()
    if DZIENNIK.exists():
        with DZIENNIK.open(encoding="utf-8") as plik:
            for linia in plik:
                linia = linia.strip()
                if not linia:
                    continue
                try:
                    w = json.loads(linia)
                except ValueError:
                    continue
                if not isinstance(w, dict):
                    continue
                dzien = str(w.get("kiedy") or "")[:10]
                if _poprawna_data(dzien):
                    kandydaci.append(dzien)
                    ze_sladem.add(dzien)
    return (min(kandydaci) if kandydaci else None), ze_sladem


def _znak(ile: float, norma: float) -> str:
    """Jak daleko od planu NA TEN DZIEN. Sam PROCENT jest ten sam, co w `alarm.py`.

    Przy planie mniejszym niz MIN_PLAN_DZIENNY_DO_ZNAKU procent nie niesie
    informacji (plan 2, brak jednego = 50%), wiec wykrzyknika nie stawiamy.

    TO NIE JEST TA SAMA BRAMKA, CO NA DOLE RAPORTU, i celowo: tutaj pytamy o
    JEDEN DZIEN, tam o SUME CALEGO OKNA. Wczesniej stala byla jedna i udawala,
    ze rzadzi obiema skalami.

    OBIETNICA JEST WIEC WEZSZA, NIZ BYLA, ale za to prawdziwa. Tabela moze
    milczec tam, gdzie alarm krzyczy: `0/2` restacka jednego dnia nie znaczy
    nic, a `0/21` przez dwa tygodnie znaczy wszystko — to jest cala wartosc
    sumowania. Zakazany jest kierunek ODWROTNY, bo to on uczy ignorowania
    tabeli: pozycja, o ktorej tabela krzyczy codziennie, a alarm milczy, nie
    znika po cichu — dolna linia „ponizej progu, ale za malo brakow na alarm"
    nazywa ja po imieniu razem z planem i liczba brakow, w obu widokach. A
    pozycja, ktora nie wystawila NICZEGO, budzi alarm niezaleznie od tego, jak
    maly byl plan (`MIN_PLAN_W_OKNIE_DO_ALARMU_O_ZERZE`) — a pozycja, ktorej
    brakuje WIECEJ, NIZ WYSZLO, budzi od planu trzech sztuk w oknie
    (`MIN_PLAN_W_OKNIE_DO_ALARMU_O_POLOWIE`), bo bramka od liczby brakow jest
    dla rzadkich kanalow nieosiagalna.

    A `alarm.py` NIE MA zadnej bramki na wielkosc planu: `alarm.wolumeny()`
    filtruje wylacznie po `config.PROG_ALARMU_WOLUMENU` (alarm.py:381), na
    oknie 7 dni z `stages.podsumowanie_dzialan`. Wspolny miedzy tym plikiem a
    `alarm.py` jest wiec sam PROCENT, a nie minimum — i tak to zdanie ma sie
    czytac. Skutek dla wlasciciela: mail o wolumenach nadal potrafi zaalarmowac
    o subskrypcjach (plan ~3,7 na tydzien), o ktorych ten licznik swiadomie
    milczy. Domkniecie tego wymaga zmiany w `alarm.py`, nie tutaj.
    """
    if norma < MIN_PLAN_DZIENNY_DO_ZNAKU:
        return ""
    proc = 100.0 * ile / norma
    if proc >= 90:
        return " "
    return "!" if proc >= config.PROG_ALARMU_WOLUMENU else "!!"


def dni_okna(dni: int, z_wpisami: set, zalozone: dict, najstarszy=None) -> list:
    """Wszystkie dni okna — TAKZE te, w ktorych nie wyszlo NIC.

    NAJPOWAZNIEJSZA WADA TEGO LICZNIKA, znaleziona w audycie. Lista dni
    powstawala jako `sorted(zrobione)`, czyli z kluczy slownika, ktory dostawal
    dzien wylacznie wtedy, gdy tego dnia UDALO SIE co najmniej jedno dzialanie.
    Dzien calkowitej awarii — agent nie wstal albo wszystko poszlo do
    `nieudane` — nie mial wiersza w tabeli i nie wchodzil ani do sredniej, ani
    do procentu wykonania planu.

    Zmierzone na atrapie: piec dni po 5 notek i 10 komentarzy, z czego jeden
    dzien W CALOSCI nieudany. Prawda to 20/25 notek i 40/50 komentarzy, czyli
    80%. Raport pokazywal cztery wiersze, „% PLANU 100%" i podpis „dni: 4" pod
    oknem pieciu dni. Ten sam mechanizm ukrywal dwa ostatnie dni, w ktorych
    agent w ogole sie nie odpalil — tabela konczyla sie po prostu wczesniej.

    Dlatego dni bierzemy z KALENDARZA, nie z danych: CALE zadane okno, od
    `dzis - dni` po dzis. Przed instalacje nie siegamy — dni sprzed niej nie sa
    awaria, tylko nieistnieniem — ale date instalacji podaje
    `slad_dziennika` z CALEJ historii, a nie „pierwszy dzien z danymi w
    oknie": to drugie przesuwalo poczatek tabeli razem z awaria i chowalo
    jedenascie martwych dni z czternastu. Dni z dziennika spoza tego zakresu
    (data z przyszlosci po przestawionym zegarze) dokladamy pojedynczo, zeby
    zepsuta data nie wygenerowala tysiaca pustych wierszy.
    """
    teraz = datetime.now(timezone.utc)
    dzis = teraz.strftime("%Y-%m-%d")
    granica = (teraz - timedelta(days=dni)).strftime("%Y-%m-%d")
    znane = {d for d in z_wpisami if d >= granica}
    znane |= {d for d in zalozone if granica <= d <= dzis}
    # Bez zadnej historii pokazujemy sam dzis — pusta baza to nie jest okno
    # czternastu dni awarii, tylko narzedzie uruchomione przed pierwszym
    # przebiegiem.
    start = najstarszy if najstarszy else dzis
    start = max(start, granica)
    start = min(start, dzis)
    zakres = set()
    biezacy = _data(start)
    koniec = _data(dzis)
    while biezacy <= koniec:
        zakres.add(biezacy.strftime("%Y-%m-%d"))
        biezacy += timedelta(days=1)
    return sorted(zakres | znane)


def _komorka(ile: int, cel, wyciszony: bool, ma_wpisy: bool,
             w_toku: bool, szacowany: bool = False) -> str:
    """Jedna kratka tabeli. `cel is None` znaczy „planu nie znamy".

    `szacowany` dokleja `~`: plan tego dnia nie zostal zapisany i jest
    PODSTAWIONY z normy dobowej. Oszacowanie ma sie roznic od pomiaru w samej
    kratce, bo inaczej wlasciciel czyta zgadniete `0/5` tak samo jak zmierzone.
    """
    if wyciszony:
        return "cisza"
    # BRAK DANYCH MA WYGLADAC NA BRAK DANYCH, NIE NA ZERO. Dzien bez wpisow i
    # bez planu oraz dzisiejszy dzien przed pierwszym przebiegiem to nie sa
    # zera — nie wiemy o nich nic i tak maja sie czytac.
    if w_toku or (not ma_wpisy and cel is None):
        return "?"
    if cel is None:
        return "%d/?" % ile
    tylda = "~" if szacowany else ""
    if cel >= 1:
        return "%d/%.0f%s%s" % (ile, cel, tylda, _znak(ile, cel))
    # Plan ponizej jednego to nie jest liczba, ktora da sie oszacowac — `-~`
    # sugerowaloby oszacowanie tam, gdzie nie ma czego szacowac.
    return "%d" % ile if ile else "-"


def przebiegow_dzis() -> int:
    """Ile przebiegow agenta domknelo sie dzis. Zero, gdy bazy nie ma."""
    try:
        import db
        conn = db.connect()
        dzis = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        (ile,) = conn.execute(
            "SELECT COUNT(*) FROM runs WHERE finished_at LIKE ? AND stage = 'dzien'",
            (dzis + "%",)).fetchone()
        conn.close()
        return int(ile or 0)
    except Exception:
        return 0


def godziny_przebiegow() -> list:
    """Minuty od polnocy UTC, o ktorych systemd odpala agenta.

    Czytane z `nia-agent.timer`, bo tam ta lista juz jest i drugiej byc nie
    moze. Gdy pliku nie ma (uruchomienie poza serwerem, np. na Windows),
    zakladamy rowny rozklad — lepszy od udawania, ze cala doba jest
    rozliczalna od pierwszej minuty.
    """
    minuty = []
    try:
        for linia in ZEGAR.read_text(encoding="utf-8").splitlines():
            linia = linia.strip()
            if not linia.startswith("OnCalendar="):
                continue
            czesci = linia.split("=", 1)[1].split()[-1].split(":")
            minuty.append(int(czesci[0]) * 60 + int(czesci[1]))
    except Exception:
        minuty = []
    if not minuty:
        n = max(1, config.PRZEBIEGOW_DZIENNIE)
        return [round(24 * 60 * (i + 1) / (n + 1.0)) for i in range(n)]
    return sorted(minuty)


def przebiegow_naleznych(teraz=None) -> tuple:
    """(ile przebiegow POWINNO juz oddac swoja czesc, ile ich jest na dobe).

    TO NIE JEST `przebiegow_dzis()` I NIE MOZE NIM BYC. Tamta funkcja liczy
    przebiegi, ktore SIE ODBYLY (`SELECT COUNT(*) ... finished_at LIKE dzis`).
    Uzycie jej jako mianownika odtworzyloby dokladnie te wade, ktora ten kod
    naprawia: maszyna lezy -> zero domknietych przebiegow -> zero oczekiwanych
    -> doba calkowitej awarii znowu niewidoczna. Ile POWINNO sie odbyc, wie
    wylacznie ZEGAR, i tylko on moze to rozstrzygac.

    Przebieg liczy sie jako nalezny dopiero wtedy, gdy zaczal sie NASTEPNY.
    Przebieg TRWA (`config.LIMIT_CZASU_PRZEBIEGU_S` = 9000 s, czyli 2,5 h) i
    rozklada akcje na caly swoj czas, a `RandomizedDelaySec=1500` przesuwa mu
    jeszcze start o do 25 minut — wiec o 11:45, kwadrans po nominalnym starcie
    przebiegu z 11:20, jego notka nie ma prawa istniec i zadanie jej byloby tym
    samym „0%!!" o czwartej rano, ktore galaz `--dzis` juz raz naprawiala.

    Przy harmonogramie 11:20 / 17:00 / 19:20 / 21:30 / 23:40 UTC daje to:
    do 17:00 — 0/5, potem 1/5, od 19:20 — 2/5, od 21:30 — 3/5, od 23:40 — 4/5.
    Ostatni przebieg doby domyka sie juz po polnocy, wiec w obrebie doby nie
    jest liczony; jego czesc wchodzi nazajutrz, gdy dzien jest pelny.
    """
    teraz = teraz or datetime.now(timezone.utc)
    minuty_teraz = teraz.hour * 60 + teraz.minute
    godziny = godziny_przebiegow()
    n = len(godziny)
    nalezne = sum(1 for i in range(n - 1) if minuty_teraz >= godziny[i + 1])
    return nalezne, n


def slad(dni: int) -> int:
    """Gdzie dokladnie psuja sie publikacje — wg pozycji w serii i odstepu.

    PO CO OSOBNY WIDOK. Norma mowi ILE wyszlo, a nie DLACZEGO reszta nie.
    30 sierpnia trzeba bylo odtwarzac pozycje w serii z timestampow dziennika,
    grupujac wpisy po przerwach i zgadujac granice serii — i dopiero to
    pokazalo, ze awaryjnosc potraja sie po pierwszej akcji. Agent zna te liczbe
    w chwili dzialania; teraz ja zapisuje (`nr_w_serii`, `od_poprzedniej_s`),
    a to jest miejsce, w ktorym sie ja czyta.

    Wpisy sprzed 30 sierpnia tych pol nie maja i sa tu pomijane — lepiej
    pokazac mniej niz zmyslic pozycje.
    """
    granica = (datetime.now(timezone.utc) - timedelta(days=dni)).strftime("%Y-%m-%d")
    wpisy = []
    if DZIENNIK.exists():
        with DZIENNIK.open(encoding="utf-8") as plik:
            for linia in plik:
                linia = linia.strip()
                if not linia:
                    continue
                try:
                    w = json.loads(linia)
                except ValueError:
                    continue
                if not isinstance(w, dict) or "nr_w_serii" not in w:
                    continue
                if str(w.get("kiedy") or "")[:10] < granica:
                    continue
                wpisy.append(w)

    if not wpisy:
        print("Brak wpisow ze sladem przebiegu.")
        print("Slad zapisywany jest od 30 sierpnia 2026 — poczekaj na przebieg.")
        return 0

    print("SLAD PRZEBIEGU — %d dzialan z ostatnich %d dni" % (len(wpisy), dni))

    print()
    print("=== AWARYJNOSC WG POZYCJI W SERII ===")
    print("  %-8s %-14s %6s %8s %7s" % ("rodzaj", "ktora z rzedu", "prob",
                                        "porazek", "%"))
    licz: dict = collections.defaultdict(lambda: [0, 0])
    for w in wpisy:
        klucz = (w.get("rodzaj"), min(int(w.get("nr_w_serii") or 1), 5))
        licz[klucz][0] += 1
        licz[klucz][1] += 0 if w.get("udane") else 1
    for (rodzaj, nr), (prob, zle) in sorted(licz.items()):
        etykieta = "%d%s" % (nr, "+" if nr == 5 else "")
        print("  %-8s %-14s %6d %8d %6.0f%%" % (
            rodzaj, etykieta, prob, zle, 100.0 * zle / prob))

    print()
    print("=== AWARYJNOSC WG ODSTEPU OD POPRZEDNIEJ ===")
    # Przedzialy dobrane pod decyzje, ktora jest do podjecia: czy piec minut
    # wystarcza. Pierwsza akcja w przebiegu nie ma odstepu i tu nie wchodzi.
    progi = ((0, 300, "ponizej 5 min"), (300, 600, "5-10 min"),
             (600, 1200, "10-20 min"), (1200, 10 ** 9, "ponad 20 min"))
    kubelki: dict = collections.defaultdict(lambda: [0, 0])
    for w in wpisy:
        sek = w.get("od_poprzedniej_s")
        if sek is None:
            continue
        for dol, gora, nazwa in progi:
            if dol <= sek < gora:
                kubelki[nazwa][0] += 1
                kubelki[nazwa][1] += 0 if w.get("udane") else 1
                break
    if not kubelki:
        print("  (jeszcze zadnej akcji z poprzedniczka w tym samym przebiegu)")
    for _, _, nazwa in progi:
        if nazwa in kubelki:
            prob, zle = kubelki[nazwa]
            print("  %-14s %6d prob %6d porazek %6.0f%%" % (
                nazwa, prob, zle, 100.0 * zle / prob))

    print()
    print("=== NAJCZESTSZE POWODY ===")
    powody: collections.Counter = collections.Counter()
    for w in wpisy:
        if not w.get("udane"):
            powody[str(w.get("powod") or "?")[:58]] += 1
    for powod, ile in powody.most_common(6):
        print("  %3dx  %s" % (ile, powod))
    if not powody:
        print("  (zadnej porazki w tym okresie)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dni", type=int, default=14)
    ap.add_argument("--dzis", action="store_true",
                    help="tylko dzisiejszy stan, jedna linia na rodzaj")
    ap.add_argument("--slad", action="store_true",
                    help="awaryjnosc wg pozycji w serii i odstepu")
    args = ap.parse_args()

    if args.slad:
        return slad(args.dni)

    normy = config.normy_dzienne()
    dni = 1 if args.dzis else args.dni
    zrobione, nieudane = wczytaj(dni)
    # ZANIM COKOLWIEK ZAJRZY DO `zrobione[d]`. To defaultdict — samo czytanie
    # zaklada klucz, wiec zbior „dni, w ktorych cokolwiek zapisano" trzeba
    # zdjac teraz albo nigdy.
    z_wpisami = set(zrobione) | set(nieudane)
    zalozone = budzety_dzienne()
    dzis = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    najstarszy, ze_sladem = slad_dziennika(zalozone)
    kolejne = dni_okna(dni, z_wpisami, zalozone, najstarszy)
    nalezne_dzis, przebiegow = przebiegow_naleznych()

    if args.dzis:
        zrobione_przebiegi = przebiegow_dzis()
        print("STAN NA DZIS (%s, UTC) — po %d z %d przebiegow"
              % (dzis, zrobione_przebiegi, config.PRZEBIEGOW_DZIENNIE))
        if zrobione_przebiegi < config.PRZEBIEGOW_DZIENNIE:
            # BEZ TEGO LICZNIK KLAMIE O CZWARTEJ RANO. Doba UTC zaczyna sie w
            # nocy, pierwszy przebieg idzie po 11:00 — wiec do poludnia kazda
            # pozycja pokazuje "0%!!" i wyglada jak awaria. Licznik, ktory
            # codziennie rano krzyczy bez powodu, uczy ignorowania siebie, a
            # wtedy nie zauwazy sie dnia, w ktorym naprawde cos padlo.
            print("   (norma rozklada sie na caly dzien — do konca zostalo %d)"
                  % (config.PRZEBIEGOW_DZIENNIE - zrobione_przebiegi))
        cicho = config.cichy_dzien()
        if cicho:
            print("   >> DZIS JEST CICHY DZIEN — %s wyciszone celowo, zero nie"
                  " jest tu porazka" % ", ".join(config.CICHY_DZIEN_WYCISZA_RODZAJE))
        # TA SAMA WADA, KTORA WIDOK WIELODNIOWY NAPRAWIL — I ZOSTALA TUTAJ.
        # Ta galaz mierzyla wykonanie `config.normy_dzienne()`, czyli AMBICJA,
        # i nigdy nie zagladala do zapisanego budzetu. Zmierzone na atrapie
        # rozbiegu: plan dnia 8 komentarzy, agent zrobil 8 — czyli 100%
        # wlasnego planu — a `--dzis` pokazywalo „8 / 19  42%!!". Docstring
        # `budzety_dzienne` nazywa te wade po imieniu od 30 sierpnia.
        plan = zalozone.get(dzis)
        # DOBA, W KTOREJ AGENT NIE WSTAL, MA SIE TU CZYTAC TAK SAMO JAK W
        # TABELI — I NIE CZYTALA SIE.
        #
        # Poprawka „mierz PLANEM, nie ambicja" trafila tylko w polowe: widok
        # wielodniowy dostal do niej PARE (`szacowany` — gdy planu nie ma i nie
        # ma zadnego sladu przebiegu, podstawiamy norme i znaczymy `~`), a ta
        # galaz nie. Skutek zmierzony o 23:00 UTC po dobie, w ktorej timer
        # lezal caly dzien: tabela pokazywala `notka 0/4~!!`, a `--dzis`
        # „notka 0 (plan nieznany; norma 5.00/dobe)" — bez procentu, bez `!!` i
        # z naglowkiem „a to NIE jest pomiar wykonania planu", ktory czyta sie
        # jak „nie ma o czym mowic". A `budzety.json` powstaje WYLACZNIE
        # wewnatrz przebiegu, wiec „planu nie zapisano i nie ma sladu" to nie
        # jest brak wiedzy, tylko podpis doby calkowitej awarii.
        #
        # TRZY ROZNE PRZYPADKI, TRZY ROZNE ZDANIA — dokladnie jak w tabeli:
        #   * jest budzet                      -> plan zmierzony;
        #   * brak budzetu, ale JEST slad      -> `plan nieznany` (agent zyl,
        #     planu nie znamy; podstawienie normy byloby mierzeniem AMBICJA);
        #   * brak budzetu i BRAK sladu        -> plan OSZACOWANY z normy.
        bez_sladu = dzis not in ze_sladem
        # ZEGAR ROZSTRZYGA, TAK SAMO JAK W TABELI (`w_toku`). Przed pierwszym
        # naleznym przebiegiem zero nie jest jeszcze porazka i procent bylby tym
        # samym „0%!! o czwartej rano", ktore ta galaz juz raz naprawiala.
        szacowany = plan is None and bez_sladu and nalezne_dzis > 0
        if szacowany:
            plan = {r: normy.get(r, 0) for r in RODZAJE}
        # PRZYCINAMY DO NALEZNYCH PRZEBIEGOW — TAK SAMO JAK `czesciowy` W
        # TABELI I TAK SAMO JAK OBIECUJE NAGLOWEK TEGO PLIKU („dzien biezacy
        # jest rozliczany z tej czesci planu, ktora POWINNA byla juz wyjsc").
        # Ta galaz dzielila przez plan CALODOBOWY, wiec o 11:00 po pierwszym
        # udanym przebiegu meldowala „notka 1 / 5  20%!!" — a doba, w ktorej
        # nie wyszlo nic, milczala. To jest ten sam odwrocony bodziec, ktory
        # tabela juz naprawila: nierobienie niczego wygladalo lepiej niz praca.
        # Przy `nalezne_dzis == 0` nie przycinamy, bo cel przyciety do zera nie
        # jest zadnym rozliczeniem: o tej porze nic jeszcze nie mialo wyjsc i
        # mowi o tym osobna linia („norma rozklada sie na caly dzien"), tak jak
        # w tabeli mowi o tym `?` i podpis „dzien w toku".
        cele = {}
        for r in RODZAJE:
            c = (plan or {}).get(r)
            if c is not None and nalezne_dzis > 0:
                c = c * nalezne_dzis / float(przebiegow)
            cele[r] = c
        przyciete = ((" przyciety do %d z %d naleznych przebiegow"
                      % (nalezne_dzis, przebiegow)) if nalezne_dzis > 0
                     else " (zaden przebieg nie jest jeszcze nalezny)")
        if szacowany:
            print("   >> ANI JEDNEGO SLADU PRZEBIEGU DZIS — budzet powstaje"
                  " wylacznie wewnatrz przebiegu, wiec tak wyglada doba, w"
                  " ktorej agent nie wstal")
            print("   (plan po ukosniku jest OSZACOWANY z normy dobowej (~),"
                  "%s — to jedyna liczba ponizej, ktora nie jest pomiarem)"
                  % przyciete)
        elif plan is None and bez_sladu:
            print("   (planu na dzis jeszcze NIE ZAPISANO i nie ma sladu"
                  " przebiegu, ale zaden przebieg nie jest jeszcze nalezny —"
                  " zero nie jest o tej porze porazka)")
        elif plan is None:
            print("   (planu na dzis NIE ZAPISANO, choc agent dzis dzialal —"
                  " kolumna po ukosniku to norma docelowa, a to NIE jest"
                  " pomiar wykonania planu)")
        else:
            print("   (kolumna po ukosniku to PLAN NA DZIS z budzetu,%s, nie"
                  " norma docelowa)" % przyciete)
        for r in RODZAJE:
            ile = zrobione[dzis][r]
            cel = cele[r]
            znany = cel is not None
            if not znany:
                cel = normy.get(r, 0)
            if cicho and r in config.CICHY_DZIEN_WYCISZA_RODZAJE:
                print("  %-12s %3d      — cichy dzien, nie nadajemy" % (r, ile))
            elif r in NIEWYKONALNE:
                print("  %-12s %3d      — %s" % (r, ile, NIEWYKONALNE[r]))
            elif not znany:
                print("  %-12s %3d      (plan nieznany; norma %.2f/dobe)"
                      % (r, ile, cel))
            elif cel >= 1:
                # Tylda przy planie znaczy to samo, co w kratce tabeli: ta
                # liczba jest PODSTAWIONA z normy, a nie zapisana przez agenta.
                print("  %-12s %3d / %-5s %3.0f%%%s" % (
                    r, ile, "%.0f%s" % (cel, "~" if szacowany else ""),
                    100.0 * ile / cel, _znak(ile, cel)))
            else:
                # Jedno miejsce po przecinku, bo tu z definicji stoi plan
                # MNIEJSZY NIZ JEDEN (0,3 subskrypcji na dobe, jeszcze
                # przyciete do naleznych przebiegow) — „plan na dzis: 0"
                # czytaloby sie jak zero zapisane w budzecie.
                print("  %-12s %3d      (plan na dzis: %.1f%s)"
                      % (r, ile, cel, "~" if szacowany else ""))
        # NIE MILCZYMY O POZYCJACH BEZ ZNAKU — TAKZE TUTAJ. Naglowek pliku
        # obiecuje, ze „osobna linia nazywa je po imieniu razem z wielkoscia
        # planu", a ta galaz tej linii NIE MIALA: przy realnym budzecie
        # restack 0/2 i subskrypcja 0/1 stoja z „0%" bez znaku i bez slowa
        # wyjasnienia, wiec czyta sie to jak przeoczenie licznika.
        # Z `cele`, a nie z surowego budzetu: wykrzyknika nie stawia `_znak` po
        # celu FAKTYCZNIE uzytym w wierszu, wiec lista musi mowic o tej samej
        # liczbie, ktora stoi po ukosniku.
        male = [(r, cele[r]) for r in RODZAJE
                if r not in NIEWYKONALNE and cele[r] is not None
                and 1 <= cele[r] < MIN_PLAN_DZIENNY_DO_ZNAKU]
        if male:
            print("   (bez znaku, bo plan na dzis za maly na procent: %s —"
                  " jeden brak to juz 50%%, wiec wykrzyknik nic by nie znaczyl)"
                  % ", ".join("%s %.0f" % (r, c) for r, c in male))
        return 0

    naglowek = "  %-11s" % "dzien" + "".join("%12s" % r[:11] for r in RODZAJE)
    print("NORMA DZIENNA: " + "  ".join(
        "%s=%.1f" % (r, normy.get(r, 0)) for r in RODZAJE))
    print()
    print(naglowek)
    print("  " + "-" * (len(naglowek) - 2))

    # CICHY DZIEN NIE JEST DNIEM NIEWYKONANEJ NORMY. Srednia liczy sie dla
    # kazdej pozycji z INNEJ liczby dni: notki i restacki tylko z dni, w
    # ktorych mialy prawo wyjsc. Bez tego jeden dzien na osiem zaniza wynik o
    # jedna osma i po miesiacu wyglada to jak trwaly spadek produkcji.
    ciche = {d for d in kolejne if config.cichy_dzien(_data(d))}
    sumy = collections.Counter()
    wykonane = collections.Counter()
    plany = collections.Counter()
    dni_liczone = collections.Counter()
    bez_planu = []
    bez_wpisow = []
    bez_planu_pozycji = set()
    szacowane = []
    zmierzone_dni = 0
    for d in kolejne:
        cicho = d in ciche
        plan_dnia = zalozone.get(d)
        ma_wpisy = d in z_wpisami
        # DZISIAJ JESZCZE TRWA — ALE NIE ROZSTRZYGA O TYM OBECNOSC WPISOW.
        #
        # Bylo tu `d == dzis and not ma_wpisy`, czyli warunek BEZ ZEGARA, i
        # dawal bodziec dokladnie odwrotny do zamierzonego. Zmierzone na tej
        # samej bazie (cztery pelne doby wczesniej, plan notek 5/dobe):
        #   23:00, zero wpisow (cala doba przepadla) -> % PLANU 100%
        #   11:00, jedna notka (pierwszy przebieg poszedl dobrze) ->  84%
        #   11:00, jedna NIEUDANA proba (`z_wpisami` obejmuje nieudane) -> 80%
        # Czyli NIEROBIENIE NICZEGO dawalo raport lepszy niz zrobienie czegos,
        # a jedna nieudana proba o 11:05 wciagala cala dobe do rozliczenia z
        # CALODOBOWEGO planu, gdy zostaly jeszcze cztery przebiegi.
        #
        # Teraz decyduje wylacznie zegar: dzien biezacy rozliczamy z tej czesci
        # planu, ktora POWINNA byla juz wyjsc (`przebiegow_naleznych`), a `?`
        # zostaje tylko dopoki nie jest nalezny zaden przebieg. Przy 23:00 i
        # planie 5 notek daje to cel 3 — wiec doba calkowitej awarii schodzi ze
        # 100% na 87% jeszcze przed polnoca, a poranna notka niczego nie psuje.
        czesciowy = (d == dzis and nalezne_dzis > 0)
        w_toku = (d == dzis and nalezne_dzis <= 0)
        # DOBA, W KTOREJ MASZYNA NAPRAWDE NIE WSTALA. `budzety.json` powstaje
        # wylacznie WEWNATRZ przebiegu, wiec gdy serwer lezal, nie ma ani wpisu,
        # ani budzetu — i dzien wypadal z `% PLANU`. Zmierzone: dwie doby
        # calkowitej awarii z pieciu, a naglowek meldowal `% PLANU 100%`.
        # Skoro planu tego dnia nie znamy, podstawiamy NORME DOBOWA i mowimy
        # wprost, ze to oszacowanie (`~` w kratce, osobna linia na dole).
        # Podstawiamy TYLKO gdy nie ma ani budzetu, ani ZADNEGO sladu w
        # dzienniku — czyli gdy nic nie dowodzi, ze agent tego dnia w ogole
        # zyl. „Zadnego sladu" znaczy tu takze braku artykulu i odpowiedzi,
        # ktorych ten licznik nie mierzy (`ze_sladem`, nie `ma_wpisy`):
        # doba z opublikowanym artykulem NIE jest doba, w ktorej maszyna nie
        # wstala, wiec zmyslanie jej planu byloby zmyslaniem awarii. Dzien,
        # ktory wstal, ale budzetu nie zapisal, dalej pokazuje `N/?` i nie
        # wchodzi do wykonania: tam podstawienie normy byloby powrotem do
        # mierzenia AMBICJA, ktore `budzety_dzienne` nazywa wada od 30 sierpnia.
        szacowany = (plan_dnia is None and d not in ze_sladem and not w_toku)
        if szacowany:
            plan_dnia = {r: normy.get(r, 0) for r in RODZAJE}
            szacowane.append(d)
        elif plan_dnia is None and not w_toku:
            # Dzien W TOKU przed pierwszym naleznym przebiegiem nie ma jeszcze
            # zapisanego budzetu i to jest NORMALNE — `stages.budzet_dnia`
            # zapisuje go dopiero w przebiegu. Wiersz mowi o tym wprost, wiec
            # na liste „brakow" nie trafia.
            bez_planu.append(d)
        if not ma_wpisy and not w_toku:
            bez_wpisow.append(d)
        wiersz = "  %-11s" % d
        dzien_zmierzony = False
        for r in RODZAJE:
            ile = zrobione[d][r]
            wyciszony = cicho and r in config.CICHY_DZIEN_WYCISZA_RODZAJE
            # PLAN TEGO DNIA I TEJ POZYCJI; `None` znaczy „nie wiemy".
            #
            # Bylo tu `.get(r, normy.get(r, 0))`, czyli podstawienie dzisiejszej
            # normy, i zabezpieczenie „liczymy tylko dni, ktorych plan znamy"
            # dzialalo na poziomie DNIA, nie POZYCJI. Zapisany budzet bez
            # jednego klucza — pierwsza nowa pozycja niedopisana do
            # BUDZET_NA_RODZAJ — dostawal wiec zmyslony cel i BYL wliczany, bez
            # gwiazdki. Odtworzone na atrapie: budzet bez `subskrypcje` dawal
            # plan 0,3 z dzisiejszej normy, wykonanie 0% i alarm o pozycji,
            # ktorej agent w ogole na ten dzien nie zaplanowal.
            cel = (plan_dnia or {}).get(r)
            znany = cel is not None
            if plan_dnia is not None and not znany and not szacowany:
                bez_planu_pozycji.add(r)
            # DZIEN BIEZACY ROZLICZAMY Z CZESCI PLANU, NIE Z CALEGO. Patrz
            # `przebiegow_naleznych` — o 21:30 nalezne sa trzy przebiegi z
            # pieciu, wiec plan 5 notek znaczy dzis 3, a nie 5.
            if znany and czesciowy:
                cel = cel * nalezne_dzis / float(przebiegow)
            if not wyciszony and not w_toku:
                # Do sredniej wchodzi dzien, o ktorym cos wiemy: byly wpisy
                # (takze same nieudane) albo byl plan, wiec zero jest pomiarem.
                # DZIEN BIEZACY DO SREDNIEJ NIE WCHODZI: srednia jest „na
                # dobe", a dzisiejsza doba jest niepelna — wliczona zanizalaby
                # ja o tyle, ile przebiegow jeszcze nie bylo. Do `% PLANU`
                # wchodzi, bo tam mianownik jest przyciety do tej samej pory.
                if not czesciowy and (ma_wpisy or znany):
                    sumy[r] += ile
                    dni_liczone[r] += 1
                    dzien_zmierzony = True
                # WYKONANIE LICZYMY TYLKO Z DNI, KTORYCH PLAN ZNAMY ALBO
                # SWIADOMIE OSZACOWALISMY. Dzien, ktory wstal, a planu nie
                # zapisal, nadal wypada — inaczej alarm meldowalby niewykonanie
                # planu, ktorego nikt wtedy nie mial.
                if znany:
                    wykonane[r] += ile
                    plany[r] += cel
            wiersz += "%12s" % _komorka(ile, cel, wyciszony, ma_wpisy, w_toku,
                                        szacowany)
        if dzien_zmierzony:
            zmierzone_dni += 1
        # CICHY DZIEN MOWI, CZEGO NIE NADAJEMY — NIE, ZE NIC SIE NIE DZIALO.
        # Bez tej listy w nawiasie ten sam wiersz nosil `<< cichy dzien` i
        # `<< ANI JEDNEGO WPISU` naraz i czytalo sie to jak sprzecznosc, choc
        # obie etykiety mowia prawde o czym innym: cisza dotyczy notek i
        # restackow, a brak wpisow takze komentarzy i lajkow, ktorych cichy
        # dzien NIE wycisza — i to jest wtedy prawdziwa awaria.
        znaki = ("   << cichy dzien (%s wyciszone)"
                 % ", ".join(config.CICHY_DZIEN_WYCISZA_RODZAJE)) if cicho else ""
        if w_toku:
            znaki += "  << dzien w toku, zaden przebieg jeszcze nie nalezny"
        elif czesciowy:
            znaki += ("  << dzien w toku, rozliczony z %d z %d przebiegow"
                      % (nalezne_dzis, przebiegow))
        if not ma_wpisy and not w_toku:
            # Dwie rozne rzeczy, dwie rozne etykiety. Dzien ze sladem w
            # dzienniku, ale bez wpisu MIERZONEGO rodzaju, to nie jest doba
            # calkowitej awarii — agent cos robil, tylko nie to, co ten
            # licznik liczy (np. wystawil artykul).
            znaki += ("  << zaden MIERZONY wpis" if d in ze_sladem
                      else "  << ANI JEDNEGO WPISU")
        zle = sum((nieudane.get(d) or {}).values())
        if zle:
            # BEZ DATY NIE DA SIE TEGO UZYC. Suma nieudanych prob stala tylko
            # na dole raportu, wiec dzien, w ktorym padlo wszystko, wygladal w
            # tabeli tak samo jak dzien, w ktorym agent nic nie probowal.
            znaki += "  << %d nieudanych prob" % zle
        if plan_dnia is None and not w_toku:
            znaki += "  *plan nieznany"
        print(wiersz + znaki)

    print("  " + "-" * (len(naglowek) - 2))

    def _srednia(r):
        """None, gdy tej pozycji nie zmierzylismy ANI RAZU.

        Bylo `dni_liczone[r] or 1`, czyli dzielenie 0/1 i twarde `0.0` w
        SREDNIEJ, ktore `% NORMY` przenosila dalej jako `0%`. Wychodzil z tego
        raport mowiacy w jednym wierszu „-" (nie wiemy), a dwie linie nizej
        „0% normy" o tej samej pozycji — i to wlasnie o tym zdaniu z
        naglowka pliku („Znak zapytania nigdy nie jest zerem") mial pilnowac.
        """
        return sumy[r] / dni_liczone[r] if dni_liczone[r] else None

    def _wykonanie(r):
        """Ile z tego, co agent SOBIE ZALOZYL, naprawde zrobil."""
        return (100.0 * wykonane[r] / plany[r]) if plany[r] else None

    def _procent_normy(r):
        sr = _srednia(r)
        if sr is None or normy.get(r, 0) < 1:
            return "-"
        return "%.0f%%" % (100.0 * sr / normy[r])

    for etykieta, wart in (
            ("SREDNIA", lambda r: ("%.1f" % _srednia(r)
                                   if _srednia(r) is not None else "-")),
            ("% PLANU", lambda r: ("%.0f%%" % _wykonanie(r)
                                   if _wykonanie(r) is not None else "-")),
            ("% NORMY", _procent_normy)):
        print("  %-11s" % etykieta + "".join("%12s" % wart(r) for r in RODZAJE))

    braki = {r: sum(nieudane[d][r] for d in nieudane) for r in RODZAJE}
    braki = {r: v for r, v in braki.items() if v}
    print()
    # `dni: N` LICZY DNI ZMIERZONE, NIE DLUGOSC OKNA. Bylo `len(kolejne)`, czyli
    # razem z dniem w toku i z dniami `?` — trzy doby po 5 notek plus dzien
    # biezacy dawaly `SREDNIA 5.0` (mianownik 3) i podpis `dni: 4` pod ta sama
    # kreska. Mianownik sredniej i liczba w podpisie musza byc ta sama liczba.
    ogon = ""
    if zmierzone_dni != len(kolejne):
        ogon = " — z okna %d dni; reszta w toku albo bez danych" % len(kolejne)
    print("  dni: %d (%s .. %s)%s"
          % (zmierzone_dni, kolejne[0], kolejne[-1], ogon))
    if bez_wpisow:
        # „NIC" ZNACZY TU „NIC Z MIERZONYCH RODZAJOW". `wczytaj` odsiewa wpisy
        # spoza RODZAJE (norma.py:121), a `browser.py:1138` zapisuje takze
        # `rodzaj: "artykul"` — wiec doba z opublikowanym artykulem i dwiema
        # odpowiedziami ma tu `ma_wpisy=False`. Zdanie „agent nie zapisal nic"
        # bylo o takim dniu po prostu nieprawdziwe.
        print("  DNI BEZ ANI JEDNEGO WPISU: %d (%s) — zadnego wpisu MIERZONYCH"
              " rodzajow (%s); artykuly i odpowiedzi nie sa tu liczone."
              " Tam, gdzie plan byl znany, zero jest wliczone"
              % (len(bez_wpisow), ", ".join(bez_wpisow[:6])
                 + (" ..." if len(bez_wpisow) > 6 else ""),
                 ", ".join(RODZAJE)))
    if braki:
        print("  nieudane proby: %s" % ", ".join(
            "%s %d" % (r, v) for r, v in sorted(braki.items())))
    for r, powod in NIEWYKONALNE.items():
        print("  %s: %s — zero nie jest tu porazka" % (r, powod))

    if ciche:
        print("  ciche dni w oknie: %d (%s) — %s nie licza sie z nich do sredniej"
              % (len(ciche), ", ".join(sorted(ciche)),
                 ", ".join(config.CICHY_DZIEN_WYCISZA_RODZAJE)))

    if szacowane:
        # OSZACOWANIE MA SIE ROZNIC OD POMIARU. Te dni nie maja ani wpisu, ani
        # zapisanego budzetu — `budzety.json` powstaje wylacznie wewnatrz
        # przebiegu, wiec ich brak znaczy „maszyna nie wstala". Bez tej linii i
        # bez `~` w kratce wlasciciel czytalby podstawiona norme jak plan,
        # ktory agent naprawde sobie zalozyl.
        print("  dni bez sladu przebiegu (~): %d (%s) — ani wpisu, ani"
              " zapisanego budzetu, wiec plan jest OSZACOWANY z normy dobowej"
              " (%s). To jedyna pozycja w tabeli, ktora nie jest pomiarem"
              % (len(szacowane), ", ".join(szacowane[:6])
                 + (" ..." if len(szacowane) > 6 else ""),
                 "  ".join("%s=%.1f" % (r, normy.get(r, 0)) for r in RODZAJE)))
    if bez_planu:
        print("  dni bez zapisanego planu, ale ZE SLADEM przebiegu (*): %d —"
              " pokazane jako `?`, NIE licza sie do wykonania planu"
              % len(bez_planu))
    if bez_planu_pozycji:
        # RADA MUSI PASOWAC DO PRZYCZYNY. Bylo tu samo „dopisz je do
        # BUDZET_NA_RODZAJ" i przy pustym zapisie budzetu bylo to zdanie
        # falszywe: wszystkie szesc kluczy TAM JEST (config.py:1671-1678),
        # brakowalo samego zapisu. Pusty budzet nie trafia juz tutaj.
        print("  pozycje bez planu w ZAPISANYM budzecie (?): %s — albo klucza"
              " nie ma w BUDZET_NA_RODZAJ, albo zapisana wartosc nie jest"
              " liczba; tak czy tak pozycja wypada z pomiaru"
              % ", ".join(sorted(bez_planu_pozycji)))

    # ALARM NA WYKONANIU PLANU, NIE NA AMBICJI. Norma mowi, dokad zmierzamy;
    # plan mowi, co agent mial dzis zrobic. Tylko drugie jest pod jego
    # kontrola, a alarm ma budzic wtedy, gdy cos NIE DZIALA — nie wtedy, gdy
    # konto jest mlode albo widelki podniesiono wczoraj.
    ponizej, za_malo_brakow = [], []
    for r in RODZAJE:
        proc = _wykonanie(r)
        if r in NIEWYKONALNE or proc is None:
            continue
        if proc >= config.PROG_ALARMU_WOLUMENU:
            continue
        brakuje = plany[r] - wykonane[r]
        # TRZY POWODY, ZEBY OBUDZIC, I ZADEN Z NICH NIE JEST WIELKOSCIA PLANU.
        #
        # 1. NIC NIE WYSZLO. Zero przy planie co najmniej jednej calej sztuki
        #    to nie zaokraglenie malego planu, tylko martwy blok — i jest
        #    martwy tak samo przy `--dni 7` co przy `--dni 14`. Bramka, ktora
        #    to wyciszala, kasowala jedyna awarie, o ktora ten licznik powstal.
        # 2. BRAKUJE DUZO SZTUK. Skala jest tu inna niz w `_znak` (okno, nie
        #    doba), bo brakow sie uzbiera; procent liczony z dwoch sztuk to
        #    kostka, a nie pomiar.
        # 3. BRAKUJE WIECEJ, NIZ WYSZLO. Punkt 2 jest nieosiagalny dla kanalu,
        #    ktorego CALY plan tygodniowy jest mniejszy niz cztery sztuki
        #    (obserwacja 3,0, subskrypcja 3,7) — a bramka nieosiagalna to
        #    trwale wyciszenie, nie filtr szumu. Powody i rachunek przy
        #    `MIN_PLAN_W_OKNIE_DO_ALARMU_O_POLOWIE`.
        martwa = (wykonane[r] == 0
                  and plany[r] >= MIN_PLAN_W_OKNIE_DO_ALARMU_O_ZERZE)
        polowiczna = (plany[r] >= MIN_PLAN_W_OKNIE_DO_ALARMU_O_POLOWIE
                      and wykonane[r] * 2 <= plany[r])
        (ponizej if martwa or polowiczna
         or brakuje >= MIN_BRAKOW_W_OKNIE_DO_ALARMU
         else za_malo_brakow).append(r)
    if za_malo_brakow:
        print()
        # Jedno miejsce po przecinku, bo plany tych wlasnie pozycji bywaja
        # ulamkowe (subskrypcja 0,3/dobe) i „z planu 0" przy niezerowym planie
        # czytaloby sie jak blad licznika. LICZBA BRAKOW STOI OBOK PROCENTU, bo
        # to ona rozstrzyga o milczeniu — bez niej wlasciciel czytalby „40% i
        # cisza" jako awarie licznika, a nie jako „brakuje poltorej sztuki".
        # POWODOW MILCZENIA JEST TERAZ DWA I OBA MAJA STAC W TEJ LINII. Sama
        # liczba brakow przestala rozstrzygac: pozycja moze tu wisiec takze
        # dlatego, ze wyszlo WIECEJ niz polowa planu. Bez drugiej liczby
        # wlasciciel czytalby „57% i cisza" jak awarie licznika.
        print("  ponizej progu, ale za malo brakow na alarm (< %d w oknie)"
              " i wiecej niz polowa planu: %s"
              % (MIN_BRAKOW_W_OKNIE_DO_ALARMU, ", ".join(
                  "%s %.0f%% z planu %.1f, brakuje %.1f"
                  % (r, _wykonanie(r), plany[r], plany[r] - wykonane[r])
                  for r in za_malo_brakow)))
    if ponizej:
        print()
        print("  PONIZEJ PROGU %d%% WYKONANIA PLANU: %s"
              % (config.PROG_ALARMU_WOLUMENU, ", ".join(ponizej)))
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
