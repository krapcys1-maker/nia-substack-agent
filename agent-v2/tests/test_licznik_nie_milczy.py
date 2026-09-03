# -*- coding: utf-8 -*-
"""Dwa miejsca, w ktorych licznik zamilkl o awarii — i nie wolno mu.

CO SIE STALO. Commit `e88b456` naprawial w `norma.py` odwrocony bodziec i
rozdzielal progi. Kontrola znalazla dwie szkody i obie polegaja na tym samym:
cos, co wczesniej krzyczalo, przestalo cokolwiek mowic.

N-A — GALAZ `--dzis` PRZESTALA POKAZYWAC DOBE, W KTOREJ AGENT NIE WSTAL.
Galaz dostala polowe poprawki („mierz PLANEM, nie ambicja"), ale nie dostala do
niej pary — `szacowany` z widoku wielodniowego. Gdy budzetu na dzis nie
zapisano, `znany` bylo False i kazdy wiersz szedl do galezi drukujacej samo
„(plan nieznany; norma X/dobe)". A `budzety.json` powstaje WYLACZNIE wewnatrz
przebiegu (`stages._zapisz_budzet_dnia`), wiec „planu nie zapisano i nie ma
sladu" to nie jest brak wiedzy — to jest podpis doby, w ktorej timer lezal.

Zmierzone (timer lezy caly dzien, wlasciciel o 23:00 UTC odpala `--dzis`, przy
normach `notka=5.0  polubienie=13.0  komentarz=19.0  restack=1.5`):

    PRZED e88b456   notka 0 / 5      0%!!      komentarz 0 / 19     0%!!
    PO   e88b456    notka 0          (plan nieznany; norma 5.00/dobe)
    TERAZ           notka 0 / 4~     0%!!      komentarz 0 / 15~    0%!!

Widok wielodniowy ten sam dzien pokazywal przez caly ten czas `0/4~!!` i
wliczal go do `% PLANU` — dwie polowy jednego commita mowily o tej samej dobie
co innego.

N-B — NOWY PROG OKNA WYCISZAL POZYCJE CALKOWICIE MARTWA.
Bramka `plany[r] >= MIN_PLAN_W_OKNIE_DO_ALARMU` (stala = 10) odcinala od alarmu
i od kodu wyjscia 1 kazda pozycje, ktorej SUMA PLANU w oknie byla mniejsza niz
10. Zmierzone na realnych budzetach (`stages.budzet_dnia`, dwiescie
przesunietych okien):

    subskrypcje  suma planu 2,0 na 7 dni i 3,9 na 14 dni (max 9) — NIGDY 10,
                 wiec martwy blok subskrypcji milczal na zawsze;
    restacki     suma planu na 7 dni: min 8, SREDNIO 10,7, max 14 — prog 10
                 lezal w srodku rozkladu, wiec ta sama martwa pozycja przy
                 `--dni 7` raz krzyczala, a raz milczala (20% okien ponizej),
                 za to przy `--dni 14` (suma 21) krzyczala zawsze.

Dlugosc okna jest wyborem czlowieka, a nie wlasnoscia awarii.

JAK TO ROZSTRZYGNIETO. Bramka zostaje, bo jej powod byl sluszny (przy planie 2
jedna brakujaca sztuka to 50% i alarm od kostki), ale pyta o co innego:
  * ILE SZTUK BRAKUJE, a nie jak duzy byl plan. Na samym progu 60% „plan >= 10"
    znaczy dokladnie „brakuje >= 4 sztuki" — nowa regula jest wiec na progu
    identyczna, a glebiej czulsza, i ZADNEGO alarmu ze starej reguly nie gubi
    (sekcja 5 sprawdza to rachunkiem na 190 x 100 przypadkach);
  * ZERO NIE PODLEGA BRAMCE. Pozycja, ktora przy planie co najmniej jednej
    calej sztuki nie wystawila w calym oknie ANI JEDNEJ, jest martwa tak samo
    przy `--dni 7` co przy `--dni 14`. Prog jednej calej sztuki jest z tego,
    ze budzet zapisuje liczby CALKOWITE: ulamek 0,3 bierze sie z podstawienia
    normy albo z przyciecia dnia biezacego, a przy planie 0,3 zero jest
    zgodnoscia z planem, nie awaria.

KONTRDOWOD JEST ODTWARZANY, NIE OPISANY: `git show e88b456:agent-v2/norma.py`
laduje sie jako drugi modul i przechodzi przez te same scenariusze. Kazda
sekcja pokazuje, ktora liczba byla wtedy inna.

BEZ PYTESTA. Uruchamiac z korzenia repozytorium:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_licznik_nie_milczy.py
Zero platnych wywolan, zero sieci, produkcyjne `data/` nietkniete.

ZEGAR PODMIENIANY W PROCESIE. Caly zestaw przechodzi na szesciu datach:
niedziela, 1. dnia miesiaca, 29 lutego, sylwester, Nowy Rok (okno przechodzi
przez zmiane roku) i PRAWDZIWY cichy dzien wg `config.cichy_dzien` — a jedna z
tych dat jest cicha i pierwsza w miesiacu naraz.
"""
import contextlib
import importlib.util
import io
import json
import pathlib
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "agent-v2")
import config          # noqa: E402
import norma           # noqa: E402

# HISTORIA JEST WARUNKIEM TEGO TESTU. Kontrdowod ponizej odtwarza sie
# z commita sprzed naprawy, wiec w kopii z historia zalozona od nowa
# nie ma z czego go odtworzyc. Pominiecie jest wtedy JAWNE, zamiast
# wywalac sie w polowie pliku na `CalledProcessError`.
import historia   # noqa: E402
historia.wymaga_historii("e88b456")

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


KAT = pathlib.Path(tempfile.mkdtemp())
ZDJECIE_SCIEZEK = None
STARA_CISZA = config.cichy_dzien
NORMY = config.normy_dzienne()
PRZEBIEGI = config.PRZEBIEGOW_DZIENNIE

NOTKA = norma.RODZAJE.index("notka")
KOMENTARZ = norma.RODZAJE.index("komentarz")
RESTACK = norma.RODZAJE.index("restack")
SUBSKRYPCJA = norma.RODZAJE.index("subskrypcja")
PUSTE = [""] * len(norma.RODZAJE)

# DATY, NA KTORYCH TEST MA PRZEJSC. Kazda z nich juz raz wysadzila jakis test w
# tym repozytorium albo jest oczywistym kandydatem: niedziela, granica miesiaca,
# dzien przestepny, granica roku (okno cofa sie do poprzedniego roku) i dzien,
# ktory `config.cichy_dzien` NAPRAWDE uznaje za cichy — 2027-03-28 jest cicha
# niedziela, a 2027-03-01 cichym pierwszym dniem miesiaca.
DATY = ("2027-08-01",   # niedziela, pierwszy dzien miesiaca
        "2028-02-29",   # dzien przestepny
        "2027-12-31",   # sylwester
        "2027-01-01",   # Nowy Rok — okno siega poprzedniego roku
        "2027-01-07",   # PRAWDZIWY cichy dzien (czwartek)
        "2027-03-28")   # PRAWDZIWY cichy dzien i niedziela naraz


class Zegar:
    """Podmiana `datetime` W PROCESIE, nie w systemie.

    `norma` robi `from datetime import datetime`, wiec wystarczy podmienic
    nazwe w module. Klasa oddaje tylko to, czego `norma` uzywa: `now` i
    `strptime`. Bez tego kazda asercja o „dzis" zalezalaby od tego, ktorego
    dnia i o ktorej godzinie ktos uruchomi test.
    """

    def __init__(self, teraz):
        self.teraz = teraz

    def now(self, tz=None):
        return self.teraz

    def strptime(self, *a, **k):
        return datetime.strptime(*a, **k)


def zaladuj_stary(sciezka_zrodla):
    """Modul z commita e88b456, obok aktualnego. Kontrdowod ma sie ODTWORZYC."""
    spec = importlib.util.spec_from_file_location("norma_e88b456",
                                                  str(sciezka_zrodla))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def przygotuj(wpisy, budzety):
    (KAT / "dziennik.jsonl").write_text(
        "\n".join(json.dumps(w) for w in wpisy), encoding="utf-8")
    (KAT / "budzety.json").write_text(
        json.dumps({d: {"budzet": b, "rozbieg": False}
                    for d, b in budzety.items()}), encoding="utf-8")


def podepnij(mod, moment, nalezne, przebiegi_dzis=0):
    """Zegar, pora doby i sciezki — dla OBU modulow tak samo."""
    mod.DZIENNIK = KAT / "dziennik.jsonl"
    mod.datetime = Zegar(moment)
    mod.przebiegow_dzis = lambda: przebiegi_dzis
    mod.przebiegow_naleznych = lambda teraz=None: (nalezne, PRZEBIEGI)


def uruchom(mod, *argv):
    """(kod wyjscia, wydruk). Mierzymy WYPISANE LICZBY i KOD, nie zrodlo."""
    stare_argv = sys.argv
    sys.argv = ["norma.py"] + list(argv)
    bufor = io.StringIO()
    try:
        with contextlib.redirect_stdout(bufor):
            kod = mod.main()
    finally:
        sys.argv = stare_argv
    return kod, bufor.getvalue()


WIERSZ_DZIS = re.compile(r"^ {2}(\S+)\s+(\d+) / (\S+)\s+(\d+)%(.*)$")


def wiersz_dzis(tekst, rodzaj):
    """(zrobione, plan, procent, znak) z `--dzis` albo None, gdy BEZ PROCENTU.

    None jest tu wynikiem, a nie awaria parsera: dokladnie tak wygladala doba
    bez sladu po e88b456 — wiersz bez procentu i bez wykrzyknika.
    """
    for linia in tekst.splitlines():
        m = WIERSZ_DZIS.match(linia)
        if m and m.group(1) == rodzaj:
            return (int(m.group(2)), m.group(3), int(m.group(4)),
                    m.group(5).strip())
    return None


def surowy_wiersz(tekst, rodzaj):
    for linia in tekst.splitlines():
        if linia.startswith("  %-12s" % rodzaj):
            return linia.rstrip()
    return "(brak wiersza %s)" % rodzaj


def kolumny(tekst, etykieta):
    for linia in tekst.splitlines():
        if linia.startswith("  %-11s" % etykieta):
            reszta = linia[13:]
            return [reszta[i * 12:(i + 1) * 12].strip()
                    for i in range(len(norma.RODZAJE))]
    return None


KRATKA = re.compile(r"^(\d+)/([\d.]+~?)(.*)$")


def kratka(tekst, dzien, indeks):
    """(zrobione, plan, znak) z kratki tabeli — do porownania z `--dzis`."""
    kol = (kolumny(tekst, dzien) or PUSTE)[indeks]
    m = KRATKA.match(kol)
    return (int(m.group(1)), m.group(2), m.group(3).strip()) if m else None


def alarmuje(tekst, rodzaj):
    """Czy pozycja jest na liscie budzacej (a nie na liscie wyciszonych)."""
    return "PONIZEJ PROGU" in tekst and rodzaj in tekst.split("PONIZEJ PROGU")[1]


def pelny_budzet(**zmiany):
    b = {"notki": 5, "komentarze": 19, "lajki": 13, "restacki": 1,
         "subskrypcje": 0, "follow": 0}
    b.update(zmiany)
    return b


def przebieg_dnia(dzien, budzet, udane=True, pomin=()):
    """Wpisy dziennika: dokladnie tyle, ile plan — albo NIEUDANE."""
    wpisy = []
    for klucz, ile in budzet.items():
        rodzaj = config.BUDZET_NA_RODZAJ[klucz]
        if rodzaj in pomin or rodzaj not in norma.RODZAJE:
            continue
        for _ in range(int(ile)):
            wpisy.append({"kiedy": dzien + "T12:00:00+00:00",
                          "rodzaj": rodzaj, "udane": udane})
    return wpisy


def zestaw(data_dzis, stary):
    """Caly zestaw sprawdzen dla JEDNEJ daty kalendarza."""
    moment = datetime.strptime(data_dzis, "%Y-%m-%d").replace(
        hour=23, tzinfo=timezone.utc)

    def dzien(ile_temu):
        return (moment - timedelta(days=ile_temu)).strftime("%Y-%m-%d")

    # Cisza liczona z PRAWDZIWEJ funkcji, ale zawsze wzgledem podmienionego
    # zegara: `norma` pyta ja raz bez argumentu (`--dzis`), raz z data (tabela).
    config.cichy_dzien = lambda kiedy=None: STARA_CISZA(kiedy or moment)
    cicho_dzis = STARA_CISZA(moment)
    # Pozycja, ktorej cichy dzien NIE wycisza — na niej stawiamy asercje o
    # dobie awarii, zeby wynik nie zalezal od tego, czy data jest cicha.
    assert "komentarz" not in config.CICHY_DZIEN_WYCISZA_RODZAJE

    print()
    print("--- %s (%s%s) ---"
          % (data_dzis, moment.strftime("%a"),
             ", CICHY DZIEN" if cicho_dzis else ""))

    # === N-A. DOBA BEZ SLADU: `--dzis` MA MOWIC TO SAMO, CO TABELA ===========
    # Cztery pelne doby wczesniej, dzis timer nie wstal ani razu: ani wpisu,
    # ani budzetu. Pora: 23:00 UTC, czyli 4 z 5 przebiegow juz naleznych.
    wpisy, budzety = [], {}
    for i in (4, 3, 2, 1):
        b = pelny_budzet()
        budzety[dzien(i)] = b
        wpisy += przebieg_dnia(dzien(i), b)
    przygotuj(wpisy, budzety)

    for mod, etykieta in ((norma, "TERAZ"), (stary, "e88b456")):
        podepnij(mod, moment, nalezne=4)
    _, tabela = uruchom(norma, "--dni", "5")
    _, dzis_txt = uruchom(norma, "--dzis")
    _, stary_dzis = uruchom(stary, "--dzis")

    w_tabeli = kratka(tabela, data_dzis, KOMENTARZ)
    w_dzis = wiersz_dzis(dzis_txt, "komentarz")
    sprawdz("A1 doba bez sladu ma w `--dzis` PROCENT (a nie sam licznik)",
            w_dzis is not None, surowy_wiersz(dzis_txt, "komentarz"))
    sprawdz("A2 KONTRDOWOD: e88b456 nie drukowal tam zadnego procentu",
            wiersz_dzis(stary_dzis, "komentarz") is None,
            surowy_wiersz(stary_dzis, "komentarz"))
    sprawdz("A3 procent to 0 i znak to `!!` — jak w kratce tabeli",
            w_dzis and w_dzis[2] == 0 and w_dzis[3] == "!!"
            and w_tabeli and w_tabeli[2] == "!!", (w_dzis, w_tabeli))
    sprawdz("A4 plan jest TA SAMA liczba co w tabeli i tak samo oznaczony (~)",
            w_dzis and w_tabeli and w_dzis[1] == w_tabeli[1]
            and w_dzis[1].endswith("~"), (w_dzis, w_tabeli))
    # 19 komentarzy normy przycietych do 4 z 5 naleznych przebiegow = 15,2.
    sprawdz("A5 i jest to norma przycieta do naleznych przebiegow (%.0f)"
            % (NORMY["komentarz"] * 4 / PRZEBIEGI),
            w_dzis and w_dzis[1] == "%.0f~" % (NORMY["komentarz"] * 4 / PRZEBIEGI),
            w_dzis)
    sprawdz("A6 `--dzis` nazywa dobe po imieniu, a nie 'plan nieznany'",
            "ANI JEDNEGO SLADU PRZEBIEGU" in dzis_txt
            and "OSZACOWANY" in dzis_txt
            and "plan nieznany" not in dzis_txt, dzis_txt.splitlines()[:6])
    sprawdz("A7 KONTRDOWOD: e88b456 pisal tam 'plan nieznany'",
            "plan nieznany" in stary_dzis
            and "ANI JEDNEGO SLADU" not in stary_dzis,
            [l for l in stary_dzis.splitlines() if "plan" in l][:3])
    if cicho_dzis:
        sprawdz("A8 cichy dzien nadal wycisza notki w OBU widokach",
                "cichy dzien" in surowy_wiersz(dzis_txt, "notka")
                and (kolumny(tabela, data_dzis) or PUSTE)[NOTKA] == "cisza",
                (surowy_wiersz(dzis_txt, "notka"),
                 kolumny(tabela, data_dzis)))
    else:
        sprawdz("A8 notki tez dostaja procent i `!!`",
                (wiersz_dzis(dzis_txt, "notka") or (0, "", -1, ""))[3] == "!!",
                surowy_wiersz(dzis_txt, "notka"))

    # === N-A. I ZADNEGO ODWROCONEGO BODZCA PRZY OKAZJI ======================
    # O 11:00 nie jest nalezny ZADEN przebieg, wiec zero nie jest jeszcze
    # porazka — tabela pokazuje `?`, a `--dzis` nie ma prawa krzyczec.
    podepnij(norma, moment, nalezne=0)
    _, rano = uruchom(norma, "--dzis")
    sprawdz("A9 przed pierwszym naleznym przebiegiem `--dzis` NIE krzyczy",
            wiersz_dzis(rano, "komentarz") is None
            and "zaden przebieg nie jest jeszcze nalezny" in rano,
            surowy_wiersz(rano, "komentarz"))

    # O 17:00 nalezny jest jeden przebieg z pieciu. Doba, w ktorej wyszla
    # dokladnie jedna piata planu, JEST na czas; doba bez sladu jest na zerze.
    # Bez przyciecia planu w `--dzis` bylo odwrotnie niz w tabeli: praca
    # dostawala „1 / 5  20%!!", a bezczynnosc — cisze.
    b_dzis = pelny_budzet()
    przygotuj(wpisy + przebieg_dnia(data_dzis, {"notki": 1, "komentarze": 4}),
              dict(budzety, **{data_dzis: b_dzis}))
    podepnij(norma, moment, nalezne=1, przebiegi_dzis=1)
    _, praca = uruchom(norma, "--dzis")
    podepnij(stary, moment, nalezne=1, przebiegi_dzis=1)
    _, stara_praca = uruchom(stary, "--dzis")
    przygotuj(wpisy, budzety)
    podepnij(norma, moment, nalezne=1)
    _, martwa = uruchom(norma, "--dzis")

    p_praca = wiersz_dzis(praca, "komentarz")
    p_martwa = wiersz_dzis(martwa, "komentarz")
    # 19 komentarzy planu na cala dobe, po pierwszym z pieciu przebiegow
    # nalezne sa 3,8 — wiec cztery wystawione to 105%, czyli praca NA CZAS.
    sprawdz("A10 doba na czas (4 z 19 po pierwszym z pieciu przebiegow)"
            " nie dostaje wykrzyknika",
            p_praca and p_praca[2] >= 100 and p_praca[3] == "",
            surowy_wiersz(praca, "komentarz"))
    sprawdz("A11 doba bez sladu o tej samej porze = 0%!!",
            p_martwa and p_martwa[2] == 0 and p_martwa[3] == "!!",
            surowy_wiersz(martwa, "komentarz"))
    sprawdz("A12 czyli praca wypada LEPIEJ niz bezczynnosc",
            p_praca and p_martwa and p_praca[2] > p_martwa[2],
            (p_praca, p_martwa))
    sprawdz("A13 KONTRDOWOD: e88b456 karal te sama prace znakiem [%s]"
            % (wiersz_dzis(stara_praca, "komentarz") or ("?",) * 4)[3],
            (wiersz_dzis(stara_praca, "komentarz") or (0, "", 0, ""))[3] == "!!"
            and wiersz_dzis(martwa, "komentarz") is not None,
            surowy_wiersz(stara_praca, "komentarz"))

    # === N-B1. MARTWY BLOK SUBSKRYPCJI BUDZI W KAZDYM OKNIE ==================
    # Substack przestawia przycisk: kazda proba subskrypcji nieudana przez 14
    # dni, cala reszta na 100%. Plan subskrypcji: 1 co drugi dzien, czyli 7 w
    # oknie 14 dni i 3-4 w oknie 7 dni — realistycznie (zmierzona srednia to
    # 3,9 i 2,0), i ZAWSZE ponizej starej bramki 10.
    wpisy, budzety, plan_sub = [], {}, {7: 0.0, 14: 0.0}
    for i in range(1, 15):
        b = pelny_budzet(subskrypcje=1 if i % 2 else 0)
        budzety[dzien(i)] = b
        wpisy += przebieg_dnia(dzien(i), b, pomin=("subskrypcja",))
        wpisy += [{"kiedy": dzien(i) + "T12:00:00+00:00",
                   "rodzaj": "subskrypcja", "udane": False}] * b["subskrypcje"]
        for okno in (7, 14):
            if i <= okno:
                plan_sub[okno] += b["subskrypcje"]
    przygotuj(wpisy, budzety)
    podepnij(norma, moment, nalezne=0)
    podepnij(stary, moment, nalezne=0)

    werdykty, stare_werdykty = {}, {}
    for okno in (7, 14):
        kod, tekst = uruchom(norma, "--dni", str(okno))
        werdykty[okno] = (kod, alarmuje(tekst, "subskrypcja"), tekst)
        kod_s, tekst_s = uruchom(stary, "--dni", str(okno))
        stare_werdykty[okno] = (kod_s, alarmuje(tekst_s, "subskrypcja"))
    sprawdz("B1 martwe subskrypcje budza przy `--dni 14` (plan %.0f)"
            % plan_sub[14],
            werdykty[14][0] == 1 and werdykty[14][1],
            [l for l in werdykty[14][2].splitlines()
             if "PONIZEJ" in l or "brakow" in l])
    sprawdz("B2 i tak samo przy `--dni 7` (plan %.0f)" % plan_sub[7],
            werdykty[7][0] == 1 and werdykty[7][1],
            [l for l in werdykty[7][2].splitlines()
             if "PONIZEJ" in l or "brakow" in l])
    sprawdz("B3 ten sam werdykt w obu oknach",
            werdykty[7][:2] == werdykty[14][:2],
            (werdykty[7][:2], werdykty[14][:2]))
    sprawdz("B4 KONTRDOWOD: e88b456 milczal w OBU oknach i oddawal kod 0",
            stare_werdykty[7] == (0, False) and stare_werdykty[14] == (0, False),
            (stare_werdykty[7], stare_werdykty[14]))
    sprawdz("B5 KONTRDOWOD: bo suma planu (%.0f i %.0f) nie siegala 10"
            % (plan_sub[7], plan_sub[14]),
            plan_sub[7] < 10 and plan_sub[14] < 10, plan_sub)

    # === N-B2. TA SAMA AWARIA, DWA OKNA, JEDEN WERDYKT =======================
    # Martwe restacki. Plan dobrany tak, jak wypada NAPRAWDE: suma na 7 dni
    # ponizej 10 (zmierzone min 8, srednio 10,7), suma na 14 dni powyzej.
    # Stara bramka rozcinala przez to jedna awarie na dwa werdykty.
    plan_restack = {7: 0.0, 14: 0.0}
    wpisy, budzety = [], {}
    for i in range(1, 15):
        b = pelny_budzet(restacki=1 if i <= 7 and i % 3 else 2)
        budzety[dzien(i)] = b
        wpisy += przebieg_dnia(dzien(i), b, pomin=("restack",))
        wpisy += [{"kiedy": dzien(i) + "T12:00:00+00:00",
                   "rodzaj": "restack", "udane": False}] * b["restacki"]
        for okno in (7, 14):
            if i <= okno and not STARA_CISZA(
                    datetime.strptime(dzien(i), "%Y-%m-%d").replace(
                        tzinfo=timezone.utc)):
                plan_restack[okno] += b["restacki"]
    przygotuj(wpisy, budzety)

    werdykty, stare_werdykty = {}, {}
    for okno in (7, 14):
        kod, tekst = uruchom(norma, "--dni", str(okno))
        werdykty[okno] = (kod, alarmuje(tekst, "restack"))
        kod_s, tekst_s = uruchom(stary, "--dni", str(okno))
        stare_werdykty[okno] = (kod_s, alarmuje(tekst_s, "restack"))
    sprawdz("B6 martwe restacki budza w obu oknach (plan %.0f i %.0f)"
            % (plan_restack[7], plan_restack[14]),
            werdykty[7] == (1, True) and werdykty[14] == (1, True), werdykty)
    sprawdz("B7 KONTRDOWOD: e88b456 dawal DWA ROZNE werdykty na tej samej"
            " awarii (7 dni: %s, 14 dni: %s)"
            % (stare_werdykty[7], stare_werdykty[14]),
            stare_werdykty[7] == (0, False) and stare_werdykty[14] == (1, True),
            (stare_werdykty, plan_restack))

    # === N-B3. DOBA CALKOWICIE MARTWA PRZY `--dni 1` ==========================
    # Pusta baza, zaden slad, 2 z 5 przebiegow naleznych (okolo 19:20 UTC):
    # plan jest oszacowany z normy i przyciety — notka 2,0, komentarz 7,6,
    # polubienie 5,2, restack 0,6, subskrypcja 0,12. Wszystko na zerze. ZADNA z
    # tych sum nie siega 10, wiec stara bramka wyciszala CALA dobe awarii i
    # oddawala kod 0 — o dobie, w ktorej nie wyszlo absolutnie nic.
    przygotuj([], {})
    podepnij(norma, moment, nalezne=2)
    podepnij(stary, moment, nalezne=2)
    kod, tekst = uruchom(norma, "--dni", "1")
    kod_s, tekst_s = uruchom(stary, "--dni", "1")
    sprawdz("B8 doba bez zadnego sladu daje kod 1", kod == 1, tekst)
    sprawdz("B9 i wymienia po imieniu pozycje, ktore nie daly nic",
            alarmuje(tekst, "komentarz") and alarmuje(tekst, "polubienie")
            and (cicho_dzis or alarmuje(tekst, "notka")),
            [l for l in tekst.splitlines() if "PONIZEJ" in l])
    sprawdz("B10 KONTRDOWOD: e88b456 oddawal na tej samej dobie kod 0",
            kod_s == 0 and "PONIZEJ PROGU" not in tekst_s,
            [l for l in tekst_s.splitlines() if "maly" in l or "PONIZEJ" in l])
    sprawdz("B11 KONTRDOWOD: i wyciszal komentarze planem 7.6 < 10",
            "za maly na alarm" in tekst_s and "komentarz" in tekst_s.split(
                "za maly na alarm")[1].splitlines()[0],
            [l for l in tekst_s.splitlines() if "maly" in l])

    # === N-B4. BRAMKA NADAL TLUMI TO, PO CO POWSTALA =========================
    # Plan subskrypcji 2 w oknie, wyszla jedna: 50% — ponizej progu 60%, ale
    # brakuje JEDNEJ sztuki. To jest kostka, nie awaria, i alarm ma milczec.
    wpisy, budzety = [], {}
    for i in (1, 2):
        b = pelny_budzet(subskrypcje=1)
        budzety[dzien(i)] = b
        wpisy += przebieg_dnia(dzien(i), b, pomin=("subskrypcja",))
    wpisy += [{"kiedy": dzien(1) + "T12:00:00+00:00",
               "rodzaj": "subskrypcja", "udane": True}]
    przygotuj(wpisy, budzety)
    podepnij(norma, moment, nalezne=0)
    kod, tekst = uruchom(norma, "--dni", "2")
    sprawdz("B12 jedna brakujaca sztuka z dwoch NIE budzi (kod 0)",
            kod == 0 and not alarmuje(tekst, "subskrypcja"),
            [l for l in tekst.splitlines() if "PONIZEJ" in l or "brakow" in l])
    sprawdz("B13 ale procent stoi w tabeli, a powod milczenia jest nazwany",
            (kolumny(tekst, "% PLANU") or PUSTE)[SUBSKRYPCJA] == "50%"
            and "za malo brakow na alarm" in tekst
            and "brakuje 1.0" in tekst,
            [l for l in tekst.splitlines() if "brakow" in l])
    # I ta sama pozycja przy ZEROWYM wykonaniu juz budzi — to jest cala roznica
    # miedzy „brakuje jednej" a „nie wyszlo nic".
    przygotuj([w for w in wpisy if w["rodzaj"] != "subskrypcja"], budzety)
    kod, tekst = uruchom(norma, "--dni", "2")
    sprawdz("B14 ale zero z tego samego planu 2 juz budzi",
            kod == 1 and alarmuje(tekst, "subskrypcja"),
            [l for l in tekst.splitlines() if "PONIZEJ" in l or "brakow" in l])

    # Plan PONIZEJ jednej calej sztuki to plan, ktorego tego dnia nie ma —
    # budzet zapisuje liczby calkowite, wiec 0,3 bierze sie z normy albo z
    # przyciecia doby. Zero jest wtedy zgodnoscia z planem.
    przygotuj([], {})
    podepnij(norma, moment, nalezne=1)
    kod, tekst = uruchom(norma, "--dni", "1")
    sprawdz("B15 pozycja z planem ponizej jednej sztuki (subskrypcja %.2f)"
            " nie budzi" % (NORMY["subskrypcja"] / PRZEBIEGI),
            not alarmuje(tekst, "subskrypcja")
            and "subskrypcja" in tekst.split("za malo brakow")[-1][:200],
            [l for l in tekst.splitlines() if "brakow" in l or "PONIZEJ" in l])


try:
    ZDJECIE_SCIEZEK = config.uzyj_katalogu_danych(KAT)
    zrodlo = KAT / "norma_e88b456.py"
    try:
        zrodlo.write_bytes(subprocess.check_output(
            ["git", "show", "e88b456:agent-v2/norma.py"]))
        stary = zaladuj_stary(zrodlo)
    except Exception as e:                       # pragma: no cover
        stary = None
        sprawdz("KONTRDOWOD da sie odtworzyc z `git show e88b456`", False,
                "%s: %s" % (type(e).__name__, e))
    if stary is not None:
        sprawdz("kontrdowod zaladowany z commita e88b456",
                hasattr(stary, "MIN_PLAN_W_OKNIE_DO_ALARMU")
                and stary.MIN_PLAN_W_OKNIE_DO_ALARMU == 10,
                getattr(stary, "MIN_PLAN_W_OKNIE_DO_ALARMU", None))
        for data in DATY:
            zestaw(data, stary)

        print()
        print("--- rachunek: nowa regula NIE GUBI zadnego starego alarmu ---")
        # Stary warunek: proc < 60 i plan >= 10. Nowy: proc < 60 i (zero przy
        # planie >= 1 albo braki >= 4). Na progu 60% „plan 10" to dokladnie
        # „braki 4", wiec kazdy stary alarm ma braki > 4 — sprawdzone wprost.
        #
        # `getattr` z domyslna None, a nie kropka: ten sam plik uruchamia sie
        # takze na kopii drzewa ze starym `norma.py` (kontrdowod ma OBLEWAC), a
        # wyjatek na brakujacej stalej zastapilby wynik testu wywrotka.
        prog_zera = getattr(norma, "MIN_PLAN_W_OKNIE_DO_ALARMU_O_ZERZE", None)
        prog_brakow = getattr(norma, "MIN_BRAKOW_W_OKNIE_DO_ALARMU", None)
        sprawdz("obie nowe stale istnieja",
                prog_zera is not None and prog_brakow is not None,
                (prog_zera, prog_brakow))
        zgubione, nowe = [], []
        if prog_zera is not None and prog_brakow is not None:
            for plan in range(10, 200):
                for wykonane in range(0, plan + 1):
                    if 100.0 * wykonane / plan >= config.PROG_ALARMU_WOLUMENU:
                        continue
                    braki = plan - wykonane
                    if not ((wykonane == 0 and plan >= prog_zera)
                            or braki >= prog_brakow):
                        zgubione.append((plan, wykonane))
            # I odwrotnie: nowa regula budzi TAKZE tam, gdzie stara milczala —
            # inaczej ta naprawa nie mialaby zadnego skutku.
            nowe = [(plan, wykonane)
                    for plan in range(1, 10) for wykonane in range(0, plan + 1)
                    if 100.0 * wykonane / plan < config.PROG_ALARMU_WOLUMENU
                    and (wykonane == 0 or plan - wykonane >= prog_brakow)]
        sprawdz("zaden przypadek budzacy stara bramke nie zamilkl (%d par)"
                % (190 * 100),
                prog_zera is not None and not zgubione, zgubione[:5])
        sprawdz("a przy planie mniejszym niz 10 budzi w %d przypadkach"
                % len(nowe), len(nowe) >= 20, len(nowe))
finally:
    config.przywroc_katalog_danych(ZDJECIE_SCIEZEK)
    config.cichy_dzien = STARA_CISZA

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
