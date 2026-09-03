# -*- coding: utf-8 -*-
"""Kanal, ktory umiera POLOWICZNIE, ma budzic tak samo jak kanal martwy.

CO BYLO. 1 wrzesnia 2026 odwrocono budzety: `FOLLOW_MIESIECZNIE` 30-44 -> 10-16,
`SUBSKRYPCJE_MIESIECZNIE` 6-12 -> 12-20. Uzasadnienie pustej listy
`norma.NIEWYKONALNE` stalo sie przez to NIEPRAWDZIWE. Stalo tam: „obserwacja
(plan ~1,2 na dobe) (...) blok martwy przez tydzien daje okolo 8-9 brakujacych
sztuk, czyli wiecej niz `MIN_BRAKOW_W_OKNIE_DO_ALARMU` (4), wiec alarm
zadziala."

ZMIERZONE PO ZMIANIE (`config.normy_dzienne`): obserwacja 0,433/dobe = 3,03 na
tydzien, subskrypcja 0,533/dobe = 3,73 — OBIE PONIZEJ bramki czterech brakow,
nie powyzej. Na prawdziwym `stages.budzet_dnia` (ziarno z daty, 365 dob) suma
planu w oknie 7 dni to srednio 3,00 obserwacji i 3,57 subskrypcji, a `>= 4`
osiaga tylko 34% i 53% okien.

CO Z TEGO WYNIKALO. Bramka „brakuje >= 4" byla dla obu kanalow NIEOSIAGALNA:
caly ich tygodniowy plan jest mniejszy niz cztery sztuki, wiec zaden poziom
wykonania poza zerem nie mial prawa jej ruszyc. Blok CALKOWICIE martwy budzil
dalej (`MIN_PLAN_W_OKNIE_DO_ALARMU_O_ZERZE` zera nie tlumi), ale blok
POLOWICZNIE martwy nie budzil nigdy. Zmierzony scenariusz ciszy — okno 7 dni,
plan 3, wykonane 1:

                                  6ed4e7d              dzis
  % PLANU w tabeli                33%                  33%
  liczba brakow                   2  (< 4)             2  (< 4)
  `martwa`                        False (wykonane 1)   False
  werdykt                         „za malo brakow"     PONIZEJ PROGU
  kod wyjscia `norma.py`          0                    1

Bramka nieosiagalna nie jest filtrem szumu, tylko trwalym wyciszeniem — czyli
tym samym, czym byla `NIEWYKONALNE`, za ktora zaplacilismy dziewiec dni bez ani
jednej obserwacji. Narzedzie pomiarowe tlumaczylo zero zamiast je zglosic.

JAK TO ROZSTRZYGNIETO. Bramka od brakow zostaje NIETKNIETA (4), a doszedl
trzeci powod do obudzenia: `MIN_PLAN_W_OKNIE_DO_ALARMU_O_POLOWIE` = 3 —
„brakuje co najmniej tyle, ile wyszlo" przy planie co najmniej trzech sztuk w
oknie. Warunek jest OR-em, wiec zaden dotychczasowy alarm nie znika; nowe sa
tylko pary (plan, wykonane) (3,1), (4,1), (4,2), (5,2), (6,3) — wszystkie w
przedziale planu 3-6, czyli dokladnie tam, gdzie wypadaja tygodniowe plany
obserwacji i subskrypcji. Trzy, a nie dwie, bo przy planie 2 „polowa" to jeden
brak, czyli DOKLADNIE ten alarm od kostki, dla ktorego prog czterech brakow
powstal — i on nadal milczy (sekcja 4).

CO TEN TEST MIERZY. Wylacznie ZACHOWANIE: kod wyjscia `norma.main()` i to, czy
pozycja stoi w linii „PONIZEJ PROGU" czy w linii „za malo brakow". ZERO asercji
po tresci zrodla.

KONTRDOWOD JEST ODTWORZONY, NIE OPISANY: `git show 6ed4e7d:agent-v2/norma.py`
laduje sie obok jako drugi modul i przechodzi przez TE SAME dzienniki. Wersja
odniesienia jest PRZYPIETA DO SHA `6ed4e7d`, nie do `HEAD` — kontrdowod
mierzony wzgledem `HEAD` gasnie w chwili commita, ktorego strzeze.

ZEGAR PODMIENIANY W PROCESIE, wiec zadna asercja nie zna dzisiejszej daty. Caly
zestaw przechodzi na szesciu datach: niedziela i 1. dnia miesiaca naraz, 29
lutego, sylwester, Nowy Rok (okno siega poprzedniego roku) oraz DWA prawdziwe
ciche dni wg `config.cichy_dzien` (jeden z nich jest cicha niedziela).

BEZ PYTESTA, zero sieci, zero wywolan modelu. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_polowicznie_martwy_kanal.py
"""
import contextlib
import hashlib
import importlib.util
import io
import json
import pathlib
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
historia.wymaga_historii("6ed4e7d")

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


def odcisk(p):
    p = pathlib.Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else "brak"


PILNOWANE = [pathlib.Path("agent-v2/norma.py"),
             pathlib.Path("agent-v2/audyt_systemu.py"),
             pathlib.Path("agent-v2/config.py"),
             pathlib.Path("agent-v2/stages.py"),
             pathlib.Path(config.DB_PATH),
             config.DATA_DIR / "dziennik.jsonl",
             config.DATA_DIR / "budzety.json"]
PRZED = {str(p): odcisk(p) for p in PILNOWANE}
DATA_PRZED = sorted(p.name for p in config.DATA_DIR.glob("*"))

KAT = pathlib.Path(tempfile.mkdtemp())
ZDJECIE_SCIEZEK = None
STARA_CISZA = config.cichy_dzien
PRZEBIEGI = config.PRZEBIEGOW_DZIENNIE

# SHA, NIE `HEAD`. `HEAD` przesuwa sie z commitem, ktorego ten test pilnuje,
# wiec kontrdowod zgaslby dokladnie w chwili, w ktorej zaczyna byc potrzebny.
POPRZEDNIA_WERSJA = "6ed4e7d"

# DATY, NA KTORYCH TEST MA PRZEJSC — kazda juz raz wysadzila jakis test w tym
# repozytorium albo jest oczywistym kandydatem. Cisza brana z PRAWDZIWEJ
# `config.cichy_dzien`, a nie ustawiana recznie.
DATY = ("2027-08-01",   # niedziela i pierwszy dzien miesiaca naraz
        "2028-02-29",   # dzien przestepny
        "2027-12-31",   # sylwester
        "2027-01-01",   # Nowy Rok — okno siega poprzedniego roku
        "2027-01-07",   # PRAWDZIWY cichy dzien (czwartek)
        "2027-03-28")   # PRAWDZIWY cichy dzien i niedziela naraz


class Zegar:
    """Podmiana `datetime` W PROCESIE, nie w systemie.

    `norma` robi `from datetime import datetime`, wiec wystarczy podmienic
    nazwe w module. Bez tego kazda asercja o „dzis" zalezalaby od tego, ktorego
    dnia ktos uruchomi test.
    """

    def __init__(self, teraz):
        self.teraz = teraz

    def now(self, tz=None):
        return self.teraz

    def strptime(self, *a, **k):
        return datetime.strptime(*a, **k)


def zaladuj_stary(sciezka):
    spec = importlib.util.spec_from_file_location(
        "norma_%s" % POPRZEDNIA_WERSJA, str(sciezka))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def przygotuj(wpisy, budzety):
    (KAT / "dziennik.jsonl").write_text(
        "\n".join(json.dumps(w) for w in wpisy), encoding="utf-8")
    (KAT / "budzety.json").write_text(
        json.dumps({d: {"budzet": b, "rozbieg": False}
                    for d, b in budzety.items()}), encoding="utf-8")


def podepnij(mod, moment, nalezne=0):
    """Zegar, pora doby i sciezki — dla OBU modulow tak samo."""
    mod.DZIENNIK = KAT / "dziennik.jsonl"
    mod.datetime = Zegar(moment)
    mod.przebiegow_dzis = lambda: 0
    mod.przebiegow_naleznych = lambda teraz=None: (nalezne, PRZEBIEGI)


def uruchom(mod, *argv):
    """(kod wyjscia, wydruk). Mierzymy KOD i WYPISANE LINIE, nie zrodlo."""
    stare_argv = sys.argv
    sys.argv = ["norma.py"] + list(argv)
    bufor = io.StringIO()
    try:
        with contextlib.redirect_stdout(bufor):
            kod = mod.main()
    finally:
        sys.argv = stare_argv
    return kod, bufor.getvalue()


def alarmuje(tekst, rodzaj):
    """Czy pozycja stoi na liscie BUDZACEJ (a nie na liscie wyciszonych)."""
    return "PONIZEJ PROGU" in tekst and rodzaj in tekst.split("PONIZEJ PROGU")[1]


def wyciszona(tekst, rodzaj):
    """Czy pozycja stoi na liscie wyciszonych („za malo brakow")."""
    if "za malo brakow" not in tekst:
        return False
    return rodzaj in tekst.split("za malo brakow")[1].split("\n")[0]


def budzet_dnia(**zmiany):
    """Realny ksztalt zapisu `stages._zapisz_budzet_dnia` — wszystkie klucze."""
    b = {"notki": 5, "komentarze": 19, "lajki": 13, "restacki": 1,
         "subskrypcje": 0, "follow": 0}
    b.update(zmiany)
    return b


def przebieg_dnia(dzien, budzet, pomin=()):
    """Wpisy dziennika: dokladnie tyle udanych, ile mowi plan."""
    wpisy = []
    for klucz, ile in budzet.items():
        rodzaj = config.BUDZET_NA_RODZAJ[klucz]
        if rodzaj in pomin or rodzaj not in norma.RODZAJE:
            continue
        for _ in range(int(ile)):
            wpisy.append({"kiedy": dzien + "T12:00:00+00:00",
                          "rodzaj": rodzaj, "udane": True})
    return wpisy


def scena(moment, rodzaj, plan, wykonane, klucz):
    """Okno, w ktorym POZYCJA `rodzaj` ma w sumie plan `plan` i `wykonane`.

    Jeden dzien = jedna sztuka planu, zeby suma w oknie byla dokladnie ta,
    o ktora pytamy — bez zgadywania, co wylosowal budzet. Reszta pozycji jest
    wykonana w calosci, wiec kod wyjscia mowi WYLACZNIE o pozycji badanej.
    """
    wpisy, budzety = [], {}
    for i in range(1, plan + 1):
        dzien = (moment - timedelta(days=i)).strftime("%Y-%m-%d")
        b = budzet_dnia(**{klucz: 1})
        budzety[dzien] = b
        wpisy += przebieg_dnia(dzien, b, pomin=(rodzaj,))
        if i <= wykonane:
            wpisy.append({"kiedy": dzien + "T12:00:00+00:00",
                          "rodzaj": rodzaj, "udane": True})
    return wpisy, budzety


def werdykt(mod, moment, rodzaj, plan, wykonane, klucz):
    """(kod wyjscia, czy budzi, czy wyciszona) — trzy zmierzone fakty."""
    przygotuj(*scena(moment, rodzaj, plan, wykonane, klucz))
    podepnij(mod, moment, nalezne=0)
    kod, tekst = uruchom(mod, "--dni", str(plan + 1))
    return kod, alarmuje(tekst, rodzaj), wyciszona(tekst, rodzaj), tekst


# Plany tygodniowe, na ktorych stoi cala ta poprawka — liczone z PRAWDZIWEJ
# `config.normy_dzienne()`, zeby test zestarzal sie razem z widelkami, a nie
# przepisywal ich do wlasnej kopii.
NORMY = config.normy_dzienne()
TYDZIEN_OBS = NORMY["obserwacja"] * 7
TYDZIEN_SUB = NORMY["subskrypcja"] * 7


def zestaw(data_dzis, stary):
    """Caly zestaw sprawdzen dla JEDNEJ daty kalendarza."""
    moment = datetime.strptime(data_dzis, "%Y-%m-%d").replace(
        hour=23, tzinfo=timezone.utc)
    config.cichy_dzien = lambda kiedy=None: STARA_CISZA(kiedy or moment)
    cicho_dzis = STARA_CISZA(moment)
    # Pozycje badane NIE SA wyciszane przez cichy dzien — inaczej wynik
    # zalezalby od tego, czy data wypadla cicha.
    assert "obserwacja" not in config.CICHY_DZIEN_WYCISZA_RODZAJE
    assert "subskrypcja" not in config.CICHY_DZIEN_WYCISZA_RODZAJE

    print()
    print("--- %s (%s%s) ---"
          % (data_dzis, moment.strftime("%a"),
             ", CICHY DZIEN" if cicho_dzis else ""))

    # === 1. OBSERWACJE POLOWICZNIE MARTWE: PLAN 3, WYSZLA JEDNA ==============
    # Dokladnie tygodniowy plan obserwacji po zmianie widelek (3,03).
    kod, budzi, cisza, tekst = werdykt(norma, moment, "obserwacja", 3, 1, "follow")
    sprawdz("1a plan 3, wykonana 1 — obserwacja BUDZI i kod wyjscia to 1",
            kod == 1 and budzi and not cisza,
            [l for l in tekst.splitlines() if "PONIZEJ" in l or "brakow" in l])
    kod_s, budzi_s, cisza_s, tekst_s = werdykt(
        stary, moment, "obserwacja", 3, 1, "follow")
    sprawdz("1b KONTRDOWOD: %s milczal (kod 0) i wyciszal ja jako „za malo"
            " brakow”" % POPRZEDNIA_WERSJA,
            kod_s == 0 and not budzi_s and cisza_s,
            [l for l in tekst_s.splitlines() if "PONIZEJ" in l or "brakow" in l])

    # === 2. TO SAMO NA SUBSKRYPCJACH — GLOWNYM KANALE PO ZMIANIE ============
    kod, budzi, cisza, tekst = werdykt(
        norma, moment, "subskrypcja", 4, 2, "subskrypcje")
    sprawdz("2a plan 4, wykonane 2 — subskrypcja BUDZI i kod wyjscia to 1",
            kod == 1 and budzi and not cisza,
            [l for l in tekst.splitlines() if "PONIZEJ" in l or "brakow" in l])
    kod_s, budzi_s, cisza_s, tekst_s = werdykt(
        stary, moment, "subskrypcja", 4, 2, "subskrypcje")
    sprawdz("2b KONTRDOWOD: %s milczal takze o glownym kanale"
            % POPRZEDNIA_WERSJA,
            kod_s == 0 and not budzi_s and cisza_s,
            [l for l in tekst_s.splitlines() if "PONIZEJ" in l or "brakow" in l])

    # === 3. BLOK CALKOWICIE MARTWY BUDZIL I BUDZI DALEJ ======================
    # Ta droga byla poprawna juz przedtem i naprawa nie miala prawa jej ruszyc.
    for mod, etyk in ((norma, "dzis"), (stary, POPRZEDNIA_WERSJA)):
        kod, budzi, _, tekst = werdykt(mod, moment, "obserwacja", 3, 0, "follow")
        sprawdz("3 [%s] zero z planu 3 budzi (bramka ZERA, nie brakow)" % etyk,
                kod == 1 and budzi,
                [l for l in tekst.splitlines() if "PONIZEJ" in l])

    # === 4. ALARM OD KOSTKI NADAL MILCZY =====================================
    # To jest cala racja bytu bramki brakow: „plan subskrypcji bywa 2 na
    # tydzien, wiec jedna mniej to 50%". Nowy warunek NIE MA prawa jej obudzic.
    kod, budzi, cisza, tekst = werdykt(
        norma, moment, "subskrypcja", 2, 1, "subskrypcje")
    sprawdz("4a jedna sztuka z dwoch (50%) NADAL nie budzi — kod 0",
            kod == 0 and not budzi and cisza,
            [l for l in tekst.splitlines() if "PONIZEJ" in l or "brakow" in l])
    # I pas tuz pod progiem: 4 z 7 to 57%, czyli ponizej 60, ale WIECEJ niz
    # polowa planu. Tu tez ma byc cisza.
    kod, budzi, cisza, tekst = werdykt(
        norma, moment, "subskrypcja", 7, 4, "subskrypcje")
    sprawdz("4b 4 z 7 (57%) — ponizej progu, ale wiecej niz polowa: cisza",
            kod == 0 and not budzi and cisza,
            [l for l in tekst.splitlines() if "PONIZEJ" in l or "brakow" in l])

    # === 5. KANAL, KTORY DZIALA, NIE DOSTAJE ANI SLOWA ======================
    kod, budzi, _, tekst = werdykt(
        norma, moment, "subskrypcja", 4, 3, "subskrypcje")
    sprawdz("5 3 z 4 (75%) — zaden alarm, kod 0", kod == 0 and not budzi,
            [l for l in tekst.splitlines() if "PONIZEJ" in l or "brakow" in l])

    # === 6. TA SAMA AWARIA W DWOCH OKNACH — JEDEN WERDYKT ===================
    # Dlugosc okna jest wyborem czlowieka, a nie wlasnoscia awarii. Kanal
    # stojacy trwale na polowie planu ma budzic w obu.
    #
    # WIDELKI DOBRANE TAK, JAK WYPADA NAPRAWDE: plan subskrypcji rzadszy niz
    # jeden na dobe (zmierzone 0,533), wiec w oknie 7 dni wychodzi plan 3, a w
    # oknie 14 — plan 5. OBA leza w przedziale, w ktorym bramka czterech brakow
    # jeszcze nie siega (brakuje 2 i 3), wiec kazda roznica miedzy oknami
    # nalezy do nowego warunku, a nie do starego.
    PLANOWE = (1, 3, 6, 9, 12)     # doby z planem 1 subskrypcji
    UDANE = (1, 9)                 # jedna w oknie 7, druga dopiero w oknie 14
    wpisy, budzety = [], {}
    for i in range(1, 15):
        dzien = (moment - timedelta(days=i)).strftime("%Y-%m-%d")
        b = budzet_dnia(subskrypcje=1 if i in PLANOWE else 0)
        budzety[dzien] = b
        wpisy += przebieg_dnia(dzien, b, pomin=("subskrypcja",))
        if i in UDANE:
            wpisy.append({"kiedy": dzien + "T12:00:00+00:00",
                          "rodzaj": "subskrypcja", "udane": True})
    przygotuj(wpisy, budzety)
    wynik = {}
    for okno in (7, 14):
        podepnij(norma, moment, nalezne=0)
        kod, tekst = uruchom(norma, "--dni", str(okno))
        podepnij(stary, moment, nalezne=0)
        kod_s, tekst_s = uruchom(stary, "--dni", str(okno))
        wynik[okno] = ((kod, alarmuje(tekst, "subskrypcja")),
                       (kod_s, alarmuje(tekst_s, "subskrypcja")))
    sprawdz("6a polowa planu budzi w oknie 7 (plan 3, wyszla 1) i w oknie 14"
            " (plan 5, wyszly 2) TAK SAMO",
            wynik[7][0] == (1, True) and wynik[14][0] == (1, True), wynik)
    sprawdz("6b KONTRDOWOD: %s milczal w obu oknach — brakuje 2 i 3, czyli"
            " ponizej bramki czterech brakow" % POPRZEDNIA_WERSJA,
            wynik[7][1] == (0, False) and wynik[14][1] == (0, False), wynik)


# --- rachunek na siatce (plan, wykonane), ZMIERZONY, nie wyliczony ----------
def siatka(mod, moment):
    """Zbior par (plan, wykonane), przy ktorych modul NAPRAWDE budzi."""
    budzi = set()
    for plan in range(1, 8):
        for wykonane in range(0, plan + 1):
            kod, alarm, _, _ = werdykt(
                mod, moment, "subskrypcja", plan, wykonane, "subskrypcje")
            if alarm:
                budzi.add((plan, wykonane))
                assert kod == 1, (plan, wykonane, kod)
    return budzi


try:
    ZDJECIE_SCIEZEK = config.uzyj_katalogu_danych(KAT)
    zrodlo = KAT / ("norma_%s.py" % POPRZEDNIA_WERSJA)
    try:
        zrodlo.write_bytes(subprocess.check_output(
            ["git", "show", "%s:agent-v2/norma.py" % POPRZEDNIA_WERSJA]))
        stary = zaladuj_stary(zrodlo)
    except Exception as e:                       # pragma: no cover
        stary = None
        sprawdz("KONTRDOWOD da sie odtworzyc z `git show %s`"
                % POPRZEDNIA_WERSJA, False, "%s: %s" % (type(e).__name__, e))

    if stary is not None:
        print("=== 0. WERSJA ODNIESIENIA ===")
        # Kontrdowod ma byc wersja SPRZED poprawki — mierzone po zachowaniu
        # stalych, nie po tresci pliku.
        sprawdz("wersja %s nie zna jeszcze progu polowy" % POPRZEDNIA_WERSJA,
                not hasattr(stary, "MIN_PLAN_W_OKNIE_DO_ALARMU_O_POLOWIE"),
                getattr(stary, "MIN_PLAN_W_OKNIE_DO_ALARMU_O_POLOWIE", None))
        sprawdz("a dzisiejsza go ma i wynosi 3",
                norma.MIN_PLAN_W_OKNIE_DO_ALARMU_O_POLOWIE == 3,
                norma.MIN_PLAN_W_OKNIE_DO_ALARMU_O_POLOWIE)
        sprawdz("bramka brakow zostala NIETKNIETA (4)",
                norma.MIN_BRAKOW_W_OKNIE_DO_ALARMU
                == stary.MIN_BRAKOW_W_OKNIE_DO_ALARMU == 4,
                (norma.MIN_BRAKOW_W_OKNIE_DO_ALARMU,
                 stary.MIN_BRAKOW_W_OKNIE_DO_ALARMU))
        print("    plan tygodniowy: obserwacja %.2f, subskrypcja %.2f"
              " (bramka brakow: %d)"
              % (TYDZIEN_OBS, TYDZIEN_SUB, norma.MIN_BRAKOW_W_OKNIE_DO_ALARMU))
        sprawdz("LICZBA, PRZEZ KTORA TA WADA ISTNIALA: caly tygodniowy plan"
                " obserwacji (%.2f) jest MNIEJSZY niz bramka brakow (%d)"
                % (TYDZIEN_OBS, norma.MIN_BRAKOW_W_OKNIE_DO_ALARMU),
                TYDZIEN_OBS < norma.MIN_BRAKOW_W_OKNIE_DO_ALARMU, TYDZIEN_OBS)
        sprawdz("to samo dla subskrypcji (%.2f), czyli glownego kanalu"
                % TYDZIEN_SUB,
                TYDZIEN_SUB < norma.MIN_BRAKOW_W_OKNIE_DO_ALARMU, TYDZIEN_SUB)

        for data in DATY:
            zestaw(data, stary)

        print()
        print("--- rachunek na siatce (plan, wykonane): 1..7 x 0..plan ---")
        moment = datetime.strptime(DATY[0], "%Y-%m-%d").replace(
            hour=23, tzinfo=timezone.utc)
        config.cichy_dzien = lambda kiedy=None: STARA_CISZA(kiedy or moment)
        nowa, dawna = siatka(norma, moment), siatka(stary, moment)
        zgubione = sorted(dawna - nowa)
        dolozone = sorted(nowa - dawna)
        print("    budzi dzis: %d par, budzilo %s: %d par"
              % (len(nowa), POPRZEDNIA_WERSJA, len(dawna)))
        sprawdz("zaden alarm z wersji %s nie zamilkl" % POPRZEDNIA_WERSJA,
                not zgubione, zgubione)
        sprawdz("a dolozone pary to dokladnie (3,1), (4,1), (4,2), (5,2), (6,3)"
                " — czyli plan 3-6, tam gdzie leza obserwacje i subskrypcje",
                dolozone == [(3, 1), (4, 1), (4, 2), (5, 2), (6, 3)], dolozone)
        sprawdz("i zadna z nich nie ma planu 2 — alarm od kostki zostal cichy",
                all(p >= 3 for p, _ in dolozone), dolozone)
finally:
    config.przywroc_katalog_danych(ZDJECIE_SCIEZEK)
    config.cichy_dzien = STARA_CISZA

print()
print("=== PRODUKCJA: bez zmian ===")
zle = 0
for p in PILNOWANE:
    ok = odcisk(p) == PRZED[str(p)]
    zle += 0 if ok else 1
    print("  %-26s %s" % (pathlib.Path(p).name,
                          "bez zmian" if ok else "ZMIENIONY"))
_data_po = sorted(p.name for p in config.DATA_DIR.glob("*"))
zle += 0 if _data_po == DATA_PRZED else 1
print("  %-26s %s" % ("data/", "bez zmian (%d pozycji)" % len(_data_po)
                      if _data_po == DATA_PRZED else "ZMIENIONY"))

print()
print("=== WYNIK: %d zdanych, %d oblanych%s ==="
      % (zdane, oblane, ", PRODUKCJA RUSZONA" if zle else ""))
sys.exit(1 if (oblane or zle) else 0)
