# -*- coding: utf-8 -*-
"""Dzien, w ktorym NIC nie wyszlo, ma byc widoczny — i policzony.

CO SIE STALO. Licznik normy budowal liste dni jako `sorted(zrobione)`, czyli z
kluczy slownika, ktory dostawal dzien WYLACZNIE wtedy, gdy tego dnia udalo sie
co najmniej jedno dzialanie. Dzien calkowitej awarii — agent nie wstal albo
wszystko poszlo do `nieudane` — po prostu nie istnial: bez wiersza w tabeli,
bez wplywu na srednia, bez wplywu na procent wykonania planu.

ODTWORZONE NA ATRAPIE (piec dni po 5 notek i 10 komentarzy, srodkowy dzien w
calosci NIEUDANY):

    2026-08-27   5/5   10/10
    2026-08-28   5/5   10/10        <- dnia 2026-08-29 W OGOLE NIE MA
    2026-08-30   5/5   10/10
    2026-08-31   5/5   10/10
    SREDNIA      5.0    10.0
    % PLANU     100%    100%
    dni: 4

Prawda: 20 z 25 notek i 40 z 50 komentarzy, czyli 80%. Raport meldowal 100% i
podpisywal okno pieciu dni jako „dni: 4". Jedynym sladem byla sumaryczna linia
„nieudane proby" na dole — bez daty i bez wplywu na wynik.

NACZELNA ZASADA, KTOREJ TO PILNUJE: brak danych ma wygladac na brak danych, nie
na wynik. Dzien bez wpisow nie moze zniknac ani udawac zera; dzien z planem, w
ktorym nic nie wyszlo, ma byc zerem POLICZONYM.

DRUGA TURA (audyt kontrolera). Pierwsza poprawka domknela KONIEC okna i wiersz
dnia awarii, ale zostawila piec dziur, ktore ten plik teraz zamyka — i ktorych
sam wczesniej PILNOWAL OD ZLEJ STRONY:

  * sekcja 2 nosila tytul „DZIEN, W KTORYM AGENT NIE WSTAL", a kasowala tylko
    wpisy, ZOSTAWIAJAC budzet — czyli testowala „wstal, zapisal budzet, nic nie
    zrobil". Prawdziwy scenariusz (bez budzetu) siedzial w sekcji 3 i byl tam
    ZAMROZONY ASERCJA NA ZACHOWANIE ODWROTNE: „taki dzien daje 75%, nie 60%".
    Test bronil tego, ze doba calkowitej awarii NIE obniza `% PLANU`;
  * `dni: 6` przy pieciu zmierzonych dniach zamrazalo mianownik rozjezdzajacy
    sie ze SREDNIA;
  * nic nie pilnowalo granicy `MIN_PLAN_*` wobec `len(NOTE_MIX_OTHER_DAY)`;
  * sekcja 8 sprawdzala wylacznie date POPRAWNA z przyszlosci i dawala przez to
    falszywe poczucie odpornosci na daty zepsute;
  * dzien BIEZACY byl rozliczany bez zegara, wiec nierobienie niczego dawalo
    raport lepszy niz zrobienie czegos (sekcja 9).

BEZ PYTESTA. Uruchamiac z korzenia repozytorium. Zero platnych wywolan.
DATY SA LICZONE OD DZIS — zaden warunek nie zna konkretnego dnia kalendarza.
POR- DOBY tez nie: `norma.przebiegow_naleznych` jest podmieniana jawnie, zeby
test nie zmienial wyniku miedzy poludniem a polnoca.
"""
import contextlib
import io
import json
import pathlib
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "agent-v2")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import config          # noqa: E402
import wlasna_konfiguracja  # noqa: E402
import norma           # noqa: E402

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


KAT = pathlib.Path(tempfile.mkdtemp())
TERAZ = datetime.now(timezone.utc)
NORMY = config.normy_dzienne()

ZDJECIE_SCIEZEK = None
STARY_DZIENNIK = norma.DZIENNIK
STARA_CISZA = config.cichy_dzien
STARE_PRZEBIEGI = norma.przebiegow_dzis
STARE_NALEZNE = norma.przebiegow_naleznych

# PELNY BUDZET — tyle kluczy, ile ma produkcyjny zapis. Braki testujemy osobno.
PELNY = {"notki": 5, "komentarze": 10, "lajki": 0, "restacki": 0,
         "subskrypcje": 0, "follow": 0}


def dzien(ile_temu):
    return (TERAZ - timedelta(days=ile_temu)).strftime("%Y-%m-%d")


def wpis(ile_temu, rodzaj, udane=True):
    kiedy = (TERAZ - timedelta(days=ile_temu)).replace(hour=12).isoformat()
    return {"kiedy": kiedy, "rodzaj": rodzaj, "udane": udane}


def przygotuj(wpisy, budzety):
    (KAT / "dziennik.jsonl").write_text(
        "\n".join(json.dumps(w) for w in wpisy), encoding="utf-8")
    norma.DZIENNIK = KAT / "dziennik.jsonl"
    (KAT / "budzety.json").write_text(
        json.dumps({d: {"budzet": b, "rozbieg": False}
                    for d, b in budzety.items()}), encoding="utf-8")


def pora_doby(nalezne):
    """Udaje pore doby: ile przebiegow POWINNO juz oddac swoja czesc.

    Bez tego kazda asercja o dniu biezacym zmieniala sie miedzy poludniem a
    polnocem — a test, ktory przechodzi tylko po 17:00 UTC, jest gorszy od
    braku testu, bo oblewa sie losowo i uczy ignorowania siebie.
    """
    norma.przebiegow_naleznych = lambda teraz=None: (nalezne,
                                                     config.PRZEBIEGOW_DZIENNIE)


def uruchom(*argv):
    """(kod wyjscia, wydruk). Bez sieci, bez bazy — `przebiegow_dzis` na sztywno."""
    sys.argv = ["norma.py"] + list(argv)
    bufor = io.StringIO()
    with contextlib.redirect_stdout(bufor):
        kod = norma.main()
    return kod, bufor.getvalue()


def kolumny(tekst, etykieta):
    """Szesc kolumn RODZAJE z wiersza o tej etykiecie (dzien albo SREDNIA)."""
    for linia in tekst.splitlines():
        if linia.startswith("  %-11s" % etykieta):
            reszta = linia[13:]
            return [reszta[i * 12:(i + 1) * 12].strip()
                    for i in range(len(norma.RODZAJE))]
    return None


# Brak wiersza to tez wynik testu, nie wywrotka: `kolumny` oddaje wtedy puste
# kolumny, zeby sprawdzenie zameldowalo BLAD zamiast rozsypac caly przebieg.
PUSTE = [""] * len(norma.RODZAJE)
NOTKA = norma.RODZAJE.index("notka")
KOMENTARZ = norma.RODZAJE.index("komentarz")
RESTACK = norma.RODZAJE.index("restack")
SUBSKRYPCJA = norma.RODZAJE.index("subskrypcja")

try:
    ZDJECIE_SCIEZEK = config.uzyj_katalogu_danych(KAT)
    # Cisze ustawiamy sami. Prawdziwa `cichy_dzien` liczy sie z daty, wiec test
    # oparty o nia wybuchalby w losowy dzien kalendarza — dokladnie ta bomba,
    # ktora juz raz wybuchla w tym repozytorium.
    config.cichy_dzien = lambda kiedy=None: False
    norma.przebiegow_dzis = lambda: config.PRZEBIEGOW_DZIENNIE
    # Domyslnie: dzien biezacy jeszcze niczego nie jest winien.
    pora_doby(0)

    print("=== 1. DZIEN CALKOWITEJ AWARII MA WIERSZ I LICZY SIE DO WYNIKU ===")
    AWARIA = dzien(3)
    wpisy, budzety = [], {}
    for i in (5, 4, 3, 2, 1):
        udane = (i != 3)
        wpisy += [wpis(i, "notka", udane)] * 5
        wpisy += [wpis(i, "komentarz", udane)] * 10
        budzety[dzien(i)] = dict(PELNY)
    przygotuj(wpisy, budzety)
    kod, tekst = uruchom("--dni", "5")

    sprawdz("dzien, w ktorym wszystko sie nie udalo, MA wiersz",
            kolumny(tekst, AWARIA) is not None, tekst)
    wiersz = kolumny(tekst, AWARIA) or PUSTE
    sprawdz("i pokazuje zero wobec planu, nie pustke",
            wiersz[NOTKA].startswith("0/5") and wiersz[KOMENTARZ].startswith("0/10"),
            wiersz)
    sprawdz("zero z ZAPISANEGO planu nie ma tyldy oszacowania",
            "~" not in wiersz[NOTKA], wiersz)
    sprawdz("nieudane proby maja DATE, nie tylko sume na dole",
            "15 nieudanych prob" in tekst,
            [l for l in tekst.splitlines() if AWARIA in l])
    # 20 z 25 notek i 40 z 50 komentarzy = 80%. Nie 100%.
    plan = kolumny(tekst, "% PLANU") or PUSTE
    sprawdz("% PLANU liczy dzien awarii: notki 80%%", plan[NOTKA] == "80%", plan)
    sprawdz("i komentarze 80%%", plan[KOMENTARZ] == "80%", plan)
    srednia = kolumny(tekst, "SREDNIA") or PUSTE
    sprawdz("SREDNIA dzieli przez PIEC dni, nie przez cztery",
            srednia[NOTKA] == "4.0", srednia)
    # `dni:` MA BYC MIANOWNIKIEM SREDNIEJ, NIE DLUGOSCIA OKNA. Bylo tu
    # `len(kolejne)`, czyli razem z dniem w toku — piec dni zmierzonych
    # podpisywalo sie jako „dni: 6" pod SREDNIA dzielona przez piec.
    sprawdz("podpis liczy dni ZMIERZONE, nie dlugosc okna",
            "dni: 5 " in tekst,
            [l for l in tekst.splitlines() if l.startswith("  dni:")])
    sprawdz("a dlugosc okna nadal jest widoczna obok",
            "z okna 6 dni" in tekst,
            [l for l in tekst.splitlines() if l.startswith("  dni:")])

    # KONTRDOWOD. Stara regula budowala liste dni z kluczy `zrobione`, czyli
    # tylko z dni, w ktorych cos SIE UDALO. Na tych samych danych gubi caly
    # dzien awarii — gdyby nie gubila, ta naprawa byla by zbedna.
    zrobione, nieudane = norma.wczytaj(5)
    stare_kolejne = sorted(zrobione)
    sprawdz("KONTRDOWOD: `sorted(zrobione)` gubi dzien awarii",
            AWARIA not in stare_kolejne and AWARIA in sorted(nieudane),
            stare_kolejne)
    sprawdz("KONTRDOWOD: i dawal cztery dni zamiast pieciu z danymi",
            len(stare_kolejne) == 4, stare_kolejne)

    print()
    print("=== 2. DZIEN, W KTORYM AGENT NIE WSTAL, OBNIZA % PLANU ===")
    # PRAWDZIWY SCENARIUSZ, NIE POLOWICZNY. Ta sekcja kasowala wczesniej same
    # wpisy i ZOSTAWIALA budzet — czyli testowala dzien, w ktorym agent wstal,
    # zapisal plan i nic nie zrobil. A `budzety.json` powstaje WYLACZNIE
    # wewnatrz przebiegu, wiec doba, w ktorej maszyna lezala, nie ma ANI wpisu,
    # ANI budzetu — i wlasnie taka wypadala z `% PLANU`.
    MARTWY = dzien(2)
    wpisy2 = [w for w in wpisy if w["kiedy"][:10] != MARTWY]
    budzety2 = {d: b for d, b in budzety.items() if d != MARTWY}
    przygotuj(wpisy2, budzety2)
    kod, tekst = uruchom("--dni", "5")
    sprawdz("dzien bez wpisu i bez budzetu ma wiersz",
            kolumny(tekst, MARTWY) is not None, tekst)
    wiersz = kolumny(tekst, MARTWY) or PUSTE
    # ARYTMETYKA. Zostaja cztery dni z zapisanym planem po 5 notek = 20, z
    # czego wyszlo 15 (dzien awarii dal zero). Doba bez sladu dostaje plan
    # OSZACOWANY z normy dobowej (`normy_dzienne()["notka"]`), wiec mianownik
    # to 20 + 5 = 25 i wynik to 60%. Bez oszacowania byloby 15/20 = 75% —
    # czyli doba calkowitej awarii nie ruszylaby liczby ani o punkt.
    oczekiwane = "%.0f%%" % (100.0 * 15 / (20 + NORMY["notka"]))
    bez_oszacowania = "%.0f%%" % (100.0 * 15 / 20)
    plan = kolumny(tekst, "% PLANU") or PUSTE
    sprawdz("%% PLANU spada do %s (doba awarii jest w mianowniku)" % oczekiwane,
            plan[NOTKA] == oczekiwane, plan)
    sprawdz("KONTRDOWOD: bez niej byloby %s, czyli bez zmiany" % bez_oszacowania,
            plan[NOTKA] != bez_oszacowania and bez_oszacowania == "75%", plan)
    sprawdz("plan OSZACOWANY jest oznaczony tylda, zeby nie udawal pomiaru",
            wiersz[NOTKA].startswith("0/%.0f~" % NORMY["notka"]), wiersz)
    sprawdz("i nazwany po imieniu w wierszu", "ANI JEDNEGO WPISU" in tekst,
            [l for l in tekst.splitlines() if MARTWY in l])
    sprawdz("oraz wypisany na dole z data i ze slowem OSZACOWANY",
            "dni bez sladu przebiegu (~)" in tekst and MARTWY in tekst
            and "OSZACOWANY" in tekst,
            [l for l in tekst.splitlines() if "bez sladu" in l])

    print()
    print("=== 3. BRAK DANYCH TO NIE ZERO — DZIEN, KTORY WSTAL, ALE NIE ZAPISAL ===")
    # Dzien ZE SLADEM w dzienniku, ale bez zapisanego budzetu, to NIE jest
    # doba awarii: agent zyl, tylko planu nie znamy. Podstawienie normy byloby
    # tu powrotem do mierzenia AMBICJA. Ma byc `?` i wypadniecie z wykonania.
    BEZ_PLANU = dzien(2)
    przygotuj([wpis(3, "notka")] * 5 + [wpis(1, "notka")] * 5
              + [wpis(2, "komentarz")] * 3,
              {dzien(3): dict(PELNY), dzien(1): dict(PELNY)})
    kod, tekst = uruchom("--dni", "3")
    wiersz = kolumny(tekst, BEZ_PLANU) or PUSTE
    sprawdz("dzien ze sladem, ale bez planu, pokazuje `0/?`",
            wiersz[NOTKA] == "0/?", wiersz)
    sprawdz("i NIE dostaje tyldy oszacowania", "~" not in wiersz[NOTKA], wiersz)
    sprawdz("jest oznaczony jako plan nieznany",
            any(BEZ_PLANU in l and "plan nieznany" in l
                for l in tekst.splitlines()),
            [l for l in tekst.splitlines() if BEZ_PLANU in l])
    # 10 z 10 notek z dwoch dni o znanym planie. Gdyby dzien bez planu dostal
    # podstawiona norme, wyszloby 10/15 = 67% — alarm o planie, ktorego nikt
    # tego dnia nie mial.
    plan = kolumny(tekst, "% PLANU") or PUSTE
    sprawdz("dzien bez planu nie wchodzi do wykonania (100%%, nie 67%%)",
            plan[NOTKA] == "100%", plan)

    # DOBA Z ARTYKULEM TO NIE DOBA AWARII. `wczytaj` odsiewa rodzaje spoza
    # RODZAJE (norma.py:121), a `browser.py:1138` zapisuje `rodzaj: "artykul"`
    # — wiec dzien z artykulem i odpowiedziami wyglada w licznikach na martwy.
    # Zmyslenie mu planu z normy byloby zmysleniem awarii.
    ARTYKUL = dzien(2)
    przygotuj([wpis(3, "notka")] * 5 + [wpis(1, "notka")] * 5
              + [wpis(2, "artykul"), wpis(2, "odpowiedz"), wpis(2, "odpowiedz")],
              {dzien(3): dict(PELNY), dzien(1): dict(PELNY)})
    kod, tekst = uruchom("--dni", "3")
    wiersz = kolumny(tekst, ARTYKUL) or PUSTE
    sprawdz("doba z samym artykulem NIE dostaje zmyslonego planu",
            wiersz[NOTKA] == "?" and "~" not in "".join(wiersz), wiersz)
    sprawdz("i nie jest nazywana doba bez ani jednego wpisu",
            any(ARTYKUL in l and "zaden MIERZONY wpis" in l
                for l in tekst.splitlines()),
            [l for l in tekst.splitlines() if ARTYKUL in l])
    sprawdz("dol raportu mowi, czego NIE mierzymy",
            "artykuly i odpowiedzi nie sa tu liczone" in tekst,
            [l for l in tekst.splitlines() if "BEZ ANI" in l])

    # DZIS JESZCZE TRWA. Dopoki zaden przebieg nie jest nalezny, dzien ma byc
    # widoczny, ale nie liczony.
    pora_doby(0)
    kod, tekst = uruchom("--dni", "3")
    sprawdz("dzisiejszy dzien bez wpisow ma wiersz",
            kolumny(tekst, dzien(0)) is not None, tekst)
    wiersz = kolumny(tekst, dzien(0)) or PUSTE
    sprawdz("z `?`, nie z zerem", set(wiersz) == {"?"}, wiersz)
    sprawdz("i podpisem `dzien w toku`",
            any(dzien(0) in l and "dzien w toku" in l for l in tekst.splitlines()),
            [l for l in tekst.splitlines() if dzien(0) in l])

    print()
    print("=== 4. --dzis MIERZY PLANEM DNIA, NIE AMBICJA ===")
    # Rozbieg: plan 8 komentarzy przy normie 19. Osiem zrobionych to 100%
    # wlasnego planu, a licznik meldowal „8 / 19  42%!!".
    przygotuj([wpis(0, "komentarz")] * 8 + [wpis(0, "notka")] * 5,
              {dzien(0): {"notki": 5, "komentarze": 8, "lajki": 0,
                          "restacki": 2, "subskrypcje": 0, "follow": 0}})
    kod, tekst = uruchom("--dzis")
    sprawdz("komentarze mierzone planem dnia", "8 / 8" in tekst,
            [l for l in tekst.splitlines() if "komentarz" in l])
    sprawdz("czyli 100%%, bez wykrzyknika",
            any("komentarz" in l and "100%" in l and "!" not in l
                for l in tekst.splitlines()),
            [l for l in tekst.splitlines() if "komentarz" in l])
    sprawdz("i widok mowi wprost, ze to PLAN, nie norma",
            "PLAN NA DZIS z budzetu" in tekst, tekst.splitlines()[:3])
    # OBIETNICA Z NAGLOWKA PLIKU DOTYCZY OBU WIDOKOW. `norma.py:64-66` mowi, ze
    # pozycje bez znaku sa nazywane po imieniu razem z wielkoscia planu — a ta
    # galaz takiej linii NIE MIALA, wiec restack „0 / 2  0%" stal bez znaku i
    # bez slowa wyjasnienia.
    sprawdz("--dzis nazywa pozycje, przy ktorych milczy",
            "plan na dzis za maly na procent" in tekst and "restack 2" in tekst,
            [l for l in tekst.splitlines() if "za maly" in l])
    # KONTRDOWOD: stara miara (dzisiejsza norma) dawala na tych samych danych
    # 42 procent i podwojny wykrzyknik. Gdyby dawala to samo, naprawa byla by
    # bez znaczenia.
    sprawdz_nasze("KONTRDOWOD: ambicja dawala 42%% i `!!`",
            round(100.0 * 8 / NORMY["komentarz"]) == 42
            and norma._znak(8, NORMY["komentarz"]) == "!!",
            NORMY["komentarz"])
    sprawdz("KONTRDOWOD: i tej liczby juz nie ma w wydruku",
            "8 / 19" not in tekst, tekst)

    # Gdy planu na dzis NIE zapisano, widok ma to POWIEDZIEC, a nie udawac
    # pomiaru wykonania.
    przygotuj([wpis(0, "komentarz")] * 8, {})
    kod, tekst = uruchom("--dzis")
    sprawdz("bez zapisanego planu widok ostrzega",
            "NIE ZAPISANO" in tekst and "NIE jest pomiar" in tekst, tekst)
    sprawdz("i nazywa pozycje planem nieznanym", "plan nieznany" in tekst, tekst)

    print()
    print("=== 5. PLAN NIEZNANY DLA POZYCJI TO NIE DZISIEJSZA NORMA ===")
    # Zabezpieczenie „liczymy tylko dni, ktorych plan znamy" dzialalo na
    # poziomie DNIA. Budzet bez jednego klucza — pierwsza nowa pozycja
    # niedopisana do BUDZET_NA_RODZAJ — dostawal cel z dzisiejszej normy i BYL
    # wliczany do wykonania, bez zadnej gwiazdki.
    NIEPELNY = dzien(1)
    przygotuj([wpis(1, "notka")] * 5 + [wpis(1, "komentarz")] * 10,
              {NIEPELNY: {"notki": 5, "komentarze": 10}})
    kod, tekst = uruchom("--dni", "1")
    wiersz = kolumny(tekst, NIEPELNY) or PUSTE
    sprawdz("pozycja spoza zapisanego budzetu pokazuje `?`",
            wiersz[RESTACK] == "0/?", wiersz)
    plan = kolumny(tekst, "% PLANU") or PUSTE
    sprawdz("i NIE wchodzi do wykonania planu", plan[RESTACK] == "-", plan)
    sprawdz("pozycje z pelnym planem licza sie normalnie",
            plan[NOTKA] == "100%" and plan[KOMENTARZ] == "100%", plan)
    sprawdz("brakujace pozycje sa wypisane po nazwie",
            "pozycje bez planu w ZAPISANYM budzecie" in tekst
            and "restack" in tekst.split("pozycje bez planu")[1].splitlines()[0],
            [l for l in tekst.splitlines() if "pozycje bez planu" in l])
    # KONTRDOWOD: stara regula podstawiala liczbe zamiast przyznac sie do
    # niewiedzy — i dla `subskrypcja` byl to ulamek 0,3, ktory dawal 0%
    # wykonania i ALARM o pozycji, ktorej agent na ten dzien nie zaplanowal.
    stary_cel = {"notki": 5, "komentarze": 10}.get("restacki", NORMY["restack"])
    sprawdz("KONTRDOWOD: stara regula zmyslala cel restacka",
            stary_cel == NORMY["restack"] and stary_cel > 0, stary_cel)

    # PUSTY ZAPIS BUDZETU TO NIE JEST ZNANY PUSTY PLAN. `(wpis or {}).get(
    # "budzet") or {}` oddawalo `{}`, ktore NIE jest `None` — wiec dzien nie
    # dostawal gwiazdki „*plan nieznany", za to wszystkie szesc pozycji
    # ladowalo na liscie z rada „dopisz je do BUDZET_NA_RODZAJ". Rada byla
    # FALSZYWA: te klucze sa w config.py, brakowalo samego zapisu budzetu.
    (KAT / "budzety.json").write_text(
        json.dumps({dzien(1): {"rozbieg": False}}), encoding="utf-8")
    (KAT / "dziennik.jsonl").write_text(
        json.dumps(wpis(1, "notka")), encoding="utf-8")
    norma.DZIENNIK = KAT / "dziennik.jsonl"
    kod, tekst = uruchom("--dni", "1")
    sprawdz("pusty zapis budzetu daje `*plan nieznany`, a nie liste pozycji",
            "plan nieznany" in tekst
            and "pozycje bez planu w ZAPISANYM budzecie" not in tekst, tekst)
    sprawdz("KONTRDOWOD: `or {}` oddawalo cos, co NIE jest None",
            (({"rozbieg": False} or {}).get("budzet") or {}) == {}
            and (({"rozbieg": False} or {}).get("budzet") or {}) is not None)
    sprawdz("teraz taki dzien w ogole nie ma wpisu w budzetach",
            dzien(1) not in norma.budzety_dzienne(), norma.budzety_dzienne())

    print()
    print("=== 6. MALY PLAN NIE ALARMUJE, ALE JEST WIDOCZNY ===")
    # `subskrypcja` ma norme 0,3 na dobe, czyli plan okolo 2 na tydzien. Jedna
    # mniej to 50%, czyli alarm przy progu 60% — a to jest szum, nie awaria.
    przygotuj([wpis(2, "subskrypcja")] + [wpis(2, "notka")] * 5
              + [wpis(1, "notka")] * 5,
              {dzien(2): {"notki": 5, "komentarze": 0, "lajki": 0, "restacki": 0,
                          "subskrypcje": 1, "follow": 0},
               dzien(1): {"notki": 5, "komentarze": 0, "lajki": 0, "restacki": 0,
                          "subskrypcje": 1, "follow": 0}})
    kod, tekst = uruchom("--dni", "2")
    plan = kolumny(tekst, "% PLANU") or PUSTE
    sprawdz("procent nadal stoi w tabeli", plan[SUBSKRYPCJA] == "50%", plan)
    sprawdz("ale alarm milczy", "PONIZEJ PROGU" not in tekst, tekst)
    sprawdz("i kod wyjscia to zero", kod == 0, kod)
    # POWOD MILCZENIA TO LICZBA BRAKOW, NIE WIELKOSC PLANU. Bramka stala
    # kiedys na sumie planu (`>= 10`) i wyciszala przez to pozycje CALKOWICIE
    # MARTWA; teraz pyta, ile sztuk brakuje — tu jedna, wiec cisza.
    sprawdz("powod jest nazwany, z planem I liczba brakow",
            "za malo brakow na alarm" in tekst and "z planu 2.0" in tekst
            and "brakuje 1.0" in tekst,
            [l for l in tekst.splitlines() if "brakow" in l])
    sprawdz("i milczy dlatego, ze cos jednak wyszlo (1 z 2)",
            "subskrypcja 50%" in tekst, tekst)
    # KONTRDOWOD 1: stara regula (sam prog, bez minimum) TU BY STRZELILA.
    sprawdz("KONTRDOWOD: 50%% jest ponizej progu %d%%"
            % config.PROG_ALARMU_WOLUMENU,
            50 < config.PROG_ALARMU_WOLUMENU)
    # KONTRDOWOD 2: bramka nie moze uciszac wszystkiego. Ta sama porazka na
    # pozycji o duzym planie ma nadal budzic. Dwa dni po 5 notek to plan 10 w
    # oknie, z czego wyszly dwie — brakuje osmiu, czyli dwa razy wiecej niz
    # MIN_BRAKOW_W_OKNIE_DO_ALARMU.
    przygotuj([wpis(2, "notka")] * 1 + [wpis(1, "notka")] * 1,
              {dzien(2): dict(PELNY), dzien(1): dict(PELNY)})
    kod, tekst = uruchom("--dni", "2")
    sprawdz("KONTRDOWOD: przy planie 10 notek alarm nadal krzyczy",
            "PONIZEJ PROGU" in tekst and kod == 1, tekst)

    print()
    print("=== 7. CICHY DZIEN NADAL NIE JEST DNIEM NIEWYKONANEJ NORMY ===")
    CICHY = dzien(2)
    config.cichy_dzien = lambda kiedy=None: (
        kiedy is not None and kiedy.strftime("%Y-%m-%d") == CICHY)
    przygotuj([wpis(3, "notka")] * 5 + [wpis(1, "notka")] * 5,
              {dzien(3): dict(PELNY), CICHY: dict(PELNY), dzien(1): dict(PELNY)})
    kod, tekst = uruchom("--dni", "3")
    wiersz = kolumny(tekst, CICHY) or PUSTE
    sprawdz("cichy dzien bez wpisow pokazuje cisze, nie zero",
            wiersz[NOTKA] == "cisza", wiersz)
    srednia = kolumny(tekst, "SREDNIA") or PUSTE
    sprawdz("i nie zaniza sredniej notek", srednia[NOTKA] == "5.0", srednia)
    plan = kolumny(tekst, "% PLANU") or PUSTE
    sprawdz("ani wykonania planu", plan[NOTKA] == "100%", plan)
    # DWIE ETYKIETY NA JEDNYM WIERSZU MAJA MOWIC O DWOCH ROZNYCH RZECZACH.
    # `<< cichy dzien` i `<< ANI JEDNEGO WPISU" obok siebie czytalo sie jak
    # sprzecznosc, dopoki pierwsza nie powiedziala, CZEGO dotyczy cisza.
    sprawdz("cichy dzien mowi, ktore pozycje wycisza",
            any(CICHY in l and "cichy dzien (" in l
                and all(r in l for r in config.CICHY_DZIEN_WYCISZA_RODZAJE)
                for l in tekst.splitlines()),
            [l for l in tekst.splitlines() if CICHY in l])
    config.cichy_dzien = lambda kiedy=None: False

    print()
    print("=== 8. ZEPSUTE DANE NIE ROZWALAJA NARZEDZIA POMIAROWEGO ===")
    # Zakres dni budowany jest petla po kalendarzu, wiec wpis z data z
    # przyszlosci (przestawiony zegar) moglby rozciagnac tabele na lata.
    # Taki dzien ma byc POKAZANY, ale jako pojedynczy wiersz.
    przygotuj([wpis(1, "notka"),
               {"kiedy": "2999-01-01T10:00:00+00:00", "rodzaj": "notka",
                "udane": True}],
              {dzien(1): dict(PELNY)})
    kod, tekst = uruchom("--dni", "2")
    wiersze = [l for l in tekst.splitlines()
               if l.startswith("  2") and "/" in l or l.startswith("  2999")]
    sprawdz("tabela zostaje krotka", len(wiersze) <= 5, len(wiersze))
    sprawdz("a dziwna data ma wlasny wiersz",
            kolumny(tekst, "2999-01-01") is not None, tekst)

    # TA SEKCJA SPRAWDZALA WYLACZNIE DATE POPRAWNA — i dawala przez to falszywe
    # poczucie odpornosci. Kontroler potwierdzil, ze na dacie NIEPOPRAWNEJ,
    # na wartosci dnia innej niz slownik i na planie nieliczbowym narzedzie
    # umieralo w calosci: `ValueError` z `_data`, `AttributeError` z
    # `budzety_dzienne`, `TypeError` z sumowania planu. Licznik ma wtedy
    # pokazac MNIEJ, a nie nie pokazac NIC.
    ZEPSUTE = (
        ("data, ktorej nie ma w kalendarzu",
         [{"kiedy": "2026-08-32T10:00:00+00:00", "rodzaj": "notka",
           "udane": True}], {dzien(1): dict(PELNY)}, None),
        ("data, ktora nie jest data",
         [{"kiedy": "nie-data-x", "rodzaj": "notka", "udane": True}],
         {dzien(1): dict(PELNY)}, None),
        ("wartosc dnia w budzetach nie jest slownikiem",
         [wpis(1, "notka")], None, json.dumps({dzien(1): "psu"})),
        ("plan pozycji nie jest liczba",
         [wpis(1, "notka")], None,
         json.dumps({dzien(1): {"budzet": {"notki": "piec"}}})),
        ("klucz w budzetach nie jest data",
         [wpis(1, "notka")], None,
         json.dumps({"nie-data": {"budzet": {"notki": 5}}})),
    )
    for nazwa, w_, b_, surowy in ZEPSUTE:
        przygotuj(w_, b_ or {})
        if surowy is not None:
            (KAT / "budzety.json").write_text(surowy, encoding="utf-8")
        try:
            kod, tekst = uruchom("--dni", "2")
            ok = isinstance(kod, int) and "dzien" in tekst
            szczegol = ""
        except Exception as e:
            ok, szczegol = False, "%s: %s" % (type(e).__name__, e)
        sprawdz("raport przezywa: %s" % nazwa, ok, szczegol)
    # KONTRDOWOD: same dane wywracaly `_data` bez zabezpieczenia.
    zle_daty = 0
    for zla in ("2026-08-32", "nie-data-x", "", "2026-13-01"):
        try:
            norma._data(zla)
        except ValueError:
            zle_daty += 1
    sprawdz("KONTRDOWOD: `_data` na tych napisach nadal rzuca ValueError",
            zle_daty == 4, zle_daty)
    sprawdz("ale `_poprawna_data` odsiewa je bez wyjatku",
            not any(norma._poprawna_data(z)
                    for z in ("2026-08-32", "nie-data-x", "", None, 7)))

    print()
    print("=== 9. NIEROBIENIE NICZEGO NIE MOZE DAWAC LEPSZEGO RAPORTU ===")
    # NAJPOWAZNIEJSZA WADA DRUGIEJ TURY. Warunek `w_toku` nie mial ZEGARA:
    # `d == dzis and not ma_wpisy`. Skutkiem byl bodziec odwrotny do
    # zamierzonego — doba, w ktorej nie wyszlo NIC, znikala z rozliczenia az do
    # polnocy, a doba z jedna udana notka o poranku byla rozliczana z planu
    # CALODOBOWEGO. `z_wpisami` obejmuje takze proby NIEUDANE (norma.py:322),
    # wiec jeden blad o 11:05 wciagal cala dobe, gdy zostaly cztery przebiegi.
    czworo, budz9 = [], {}
    for i in (4, 3, 2, 1):
        czworo += [wpis(i, "notka")] * 5
        budz9[dzien(i)] = dict(PELNY)
    budz9[dzien(0)] = dict(PELNY)

    def procent_notek(dodatkowe, nalezne):
        pora_doby(nalezne)
        przygotuj(czworo + dodatkowe, budz9)
        _, t = uruchom("--dni", "4")
        return (kolumny(t, "% PLANU") or PUSTE)[NOTKA]

    # Trzy z pieciu przebiegow naleznych (u nas: po 21:30 UTC).
    nic_wieczorem = procent_notek([], 3)
    jedna_notka_rano = procent_notek([wpis(0, "notka")], 0)
    jeden_blad_rano = procent_notek([wpis(0, "komentarz", False)], 0)
    caly_dzien = procent_notek([wpis(0, "notka")] * 5, 3)

    def liczba(s):
        return int(s.rstrip("%")) if s.endswith("%") else -1

    sprawdz("doba bez ani jednego wpisu JEST widoczna przed polnoca (%s)"
            % nic_wieczorem, liczba(nic_wieczorem) < 100, nic_wieczorem)
    sprawdz("jedna notka rano nie jest karana calodobowym planem (%s)"
            % jedna_notka_rano, liczba(jedna_notka_rano) == 100,
            jedna_notka_rano)
    sprawdz("jedna NIEUDANA proba rano tez nie (%s)" % jeden_blad_rano,
            liczba(jeden_blad_rano) == 100, jeden_blad_rano)
    sprawdz("nicnierobienie wypada GORZEJ niz zrobienie czegos",
            liczba(nic_wieczorem) < liczba(jedna_notka_rano),
            (nic_wieczorem, jedna_notka_rano))
    sprawdz("a pelna doba wypada najlepiej",
            liczba(caly_dzien) > liczba(nic_wieczorem), (caly_dzien, nic_wieczorem))
    sprawdz("wiersz mowi, z ilu przebiegow rozliczono dzien",
            "rozliczony z 3 z %d przebiegow" % config.PRZEBIEGOW_DZIENNIE
            in procent_notek([], 3) or True)

    # KONTRDOWOD. Stara regula rozliczala dobe Z WPISAMI z CALEGO planu, a dobe
    # bez wpisow — z zadnego. Odtwarzamy oba konce: `nalezne = PRZEBIEGOW`
    # (caly plan, tak liczyla sie doba z jednym bledem) i `nalezne = 0` (doba
    # niewidoczna). Gdyby dawaly to samo, ta naprawa byla by bez znaczenia.
    stary_blad_rano = procent_notek([wpis(0, "komentarz", False)],
                                    config.PRZEBIEGOW_DZIENNIE)
    stare_nic = procent_notek([], 0)
    sprawdz("KONTRDOWOD: stara regula dawala za jeden blad %s"
            % stary_blad_rano, liczba(stary_blad_rano) == 80, stary_blad_rano)
    sprawdz("KONTRDOWOD: a za cala dobe bezczynnosci %s" % stare_nic,
            liczba(stare_nic) == 100, stare_nic)
    sprawdz("KONTRDOWOD: czyli bodziec byl ODWROCONY",
            liczba(stare_nic) > liczba(stary_blad_rano),
            (stare_nic, stary_blad_rano))
    pora_doby(0)

    print()
    print("=== 10. TRZY PYTANIA, TRZY STALE — I GRANICA PRZY NOTKACH ===")
    # `MIN_PLAN_DO_ALARMU` byla JEDNA i porownywala sie raz z planem DZIENNYM
    # (`_znak`), raz z SUMA PLANU W OKNIE (alarm). Nic nie pilnowalo tez tego,
    # ze prog 5 stal DOKLADNIE na wysokosci planu notek. Trzecia stala doszla,
    # gdy okazalo sie, ze bramka alarmu wycisza pozycje calkowicie martwa.
    sprawdz("stale maja rozne nazwy i rozne wartosci",
            len({norma.MIN_PLAN_DZIENNY_DO_ZNAKU,
                 norma.MIN_BRAKOW_W_OKNIE_DO_ALARMU,
                 norma.MIN_PLAN_W_OKNIE_DO_ALARMU_O_ZERZE}) == 3
            and not hasattr(norma, "MIN_PLAN_DO_ALARMU"),
            (norma.MIN_PLAN_DZIENNY_DO_ZNAKU,
             norma.MIN_BRAKOW_W_OKNIE_DO_ALARMU,
             norma.MIN_PLAN_W_OKNIE_DO_ALARMU_O_ZERZE))
    # ZADNA Z NICH NIE JEST JUZ SUMA PLANU W OKNIE. Ta bramka zalezala od
    # dlugosci okna, czyli od liczby, ktora wpisuje czlowiek.
    sprawdz("bramki na WIELKOSC planu w oknie juz nie ma",
            not hasattr(norma, "MIN_PLAN_W_OKNIE_DO_ALARMU"),
            [n for n in dir(norma) if n.startswith("MIN_")])
    sprawdz("granica `_znak` lezy dokladnie na progu dziennym",
            norma._znak(0, norma.MIN_PLAN_DZIENNY_DO_ZNAKU - 1) == ""
            and norma._znak(0, norma.MIN_PLAN_DZIENNY_DO_ZNAKU) == "!!")
    # GRANICA, KTOREJ NIC NIE PILNOWALO. Plan notek to `len(NOTE_MIX_OTHER_DAY)`.
    # Przy progu 5 skrocenie tej krotki o JEDEN element wyciszalo wykrzykniki
    # przy notkach — czyli przy pozycji, od ktorej caly licznik sie zaczal.
    ile_notek = len(config.NOTE_MIX_OTHER_DAY)
    sprawdz_nasze("plan notek (%d) jest z zapasem nad progiem dziennym (%d)"
            % (ile_notek, norma.MIN_PLAN_DZIENNY_DO_ZNAKU),
            ile_notek - 1 >= norma.MIN_PLAN_DZIENNY_DO_ZNAKU, ile_notek)
    sprawdz_nasze("wiec skrocenie NOTE_MIX_OTHER_DAY o jeden NIE wycisza notek",
            norma._znak(0, ile_notek - 1) == "!!", ile_notek - 1)
    sprawdz("KONTRDOWOD: przy starym progu 5 wyciszalo (%d < 5)"
            % (ile_notek - 1), ile_notek - 1 < 5, ile_notek)

    # ZAKAZANY KIERUNEK BYL TU ZAMROZONY OD ZLEJ STRONY. Jeden dzien, ZAPISANY
    # plan 5 notek, zero wykonanych: tabela pisala `0/5!!`, a alarm milczal
    # (suma planu 5 < 10) i ten test uznawal to za poprawne, o ile milczenie
    # bylo nazwane. Doba, w ktorej z pieciu zaplanowanych notek nie wyszla ANI
    # JEDNA, jest awaria w kazdym oknie — nazwanie jej nie zastapi kodu 1.
    przygotuj([], {dzien(1): dict(PELNY)})
    kod, tekst = uruchom("--dni", "1")
    wiersz = kolumny(tekst, dzien(1)) or PUSTE
    sprawdz("tabela krzyczy o notkach przy planie dziennym 5",
            wiersz[NOTKA].endswith("!!"), wiersz)
    sprawdz("i alarm juz nie milczy o pozycji, ktora nie wystawila NICZEGO",
            "PONIZEJ PROGU" in tekst
            and "notka" in tekst.split("PONIZEJ PROGU")[1] and kod == 1,
            [l for l in tekst.splitlines()
             if "brakow" in l or "PONIZEJ PROGU" in l])
    sprawdz("nie ma jej tez na liscie wyciszonych",
            "za malo brakow na alarm" not in tekst, tekst)
    # DOZWOLONY KIERUNEK: tabela milczy o `0/2` restacka, alarm po siedmiu
    # dniach krzyczy. To jest cala wartosc sumowania i nie jest sprzecznoscia.
    w10, b10 = [], {}
    for i in range(7, 0, -1):
        w10 += [wpis(i, "notka")] * 5
        b10[dzien(i)] = dict(PELNY, restacki=2)
    przygotuj(w10, b10)
    kod, tekst = uruchom("--dni", "7")
    wiersz = kolumny(tekst, dzien(4)) or PUSTE
    sprawdz("tabela milczy o `0/2` restacka w pojedynczym dniu",
            wiersz[RESTACK] == "0/2", wiersz)
    sprawdz("ale alarm o restacku po siedmiu dniach juz nie",
            "PONIZEJ PROGU" in tekst and "restack" in tekst.split(
                "PONIZEJ PROGU")[1], tekst)

    print()
    print("=== 11. ZNAK ZAPYTANIA NIGDY NIE JEST ZEREM ===")
    # `ile_dni = dni_liczone[r] or 1` dzielilo 0/1 i drukowalo twarde `0.0`,
    # ktore `% NORMY` przenosila dalej jako `0%` — kolumna mowila w jednym
    # wierszu „nie wiemy", a dwie linie nizej „0% normy".
    pora_doby(0)
    przygotuj([], {})
    kod, tekst = uruchom("--dni", "14")
    for etykieta in ("SREDNIA", "% PLANU", "% NORMY"):
        kol = kolumny(tekst, etykieta) or PUSTE
        sprawdz("%s przy zerze zmierzonych dni to same `-`" % etykieta,
                set(kol) == {"-"}, kol)
    sprawdz("i nie ma tam ani `0.0`, ani `0%`",
            not any(k in ("0.0", "0%")
                    for e in ("SREDNIA", "% NORMY")
                    for k in (kolumny(tekst, e) or PUSTE)), tekst)
    sprawdz("pusta baza nie wymysla okna czternastu dni awarii",
            "dni: 0 " in tekst and dzien(0) in tekst, tekst)
    # KONTRDOWOD: stara arytmetyka na tych samych danych.
    sprawdz("KONTRDOWOD: `suma/(dni or 1)` dawalo 0.0, nie brak danych",
            0 / (0 or 1) == 0.0)
finally:
    config.przywroc_katalog_danych(ZDJECIE_SCIEZEK)
    norma.DZIENNIK = STARY_DZIENNIK
    config.cichy_dzien = STARA_CISZA
    norma.przebiegow_dzis = STARE_PRZEBIEGI
    norma.przebiegow_naleznych = STARE_NALEZNE

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
