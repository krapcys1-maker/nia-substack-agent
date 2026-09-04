# -*- coding: utf-8 -*-
"""Trzy liczby, ktore wygladaly na pomiar, a nim nie byly.

Ten plik pilnuje trzech wad znalezionych 1 wrzesnia 2026 w `wzajemnosc.py`.
Wszystkie sa jednej rodziny: raport podawal liczbe, ktorej NIKT nie zmierzyl.

W1 — ODWZAJEMNIENIE BEZ KOLEJNOSCI W CZASIE. `odwzajemnienie()` uznawalo za
odwzajemnienie KAZDE zrownanie uchwytu celu z uchwytem czytelnika i nie pytalo,
co bylo pierwsze. Odtworzone na kopii produkcji z 1 wrzesnia (7 zrzutow,
19 czytelnikow, 635 wpisow dziennika): dopisanie JEDNEJ udanej obserwacji
`czytelnik1` — konta, ktore obserwuje nas od pierwszego zrzutu, 31 sierpnia,
nieprzerwanie przez wszystkie siedem — dawalo w raporcie „odwzajemnilo sie na
pewno 1 z 1 (100%)". Odpowiedz dokladnie odwrotna do prawdy, w jedynej liczbie,
dla ktorej ten modul istnieje. Blok obserwacji losuje cele z puli komentarzy,
a ta zachodzi na ludzi juz z nami zwiazanych, wiec to nie byl przypadek
brzegowy, tylko scenariusz na najblizsze dni.
Bliznieczo `kanaly()` przypisywalo kanal „obserwacja"/„subskrypcja" bez
porownania dat, choc galaz obok czas SPRAWDZALA (`r['kiedy'] < granica`).

W2 — ZMIERZONE ZERO NIEODROZNIALNE OD NIEPOLICZONEGO. Tabela pozycyjna brala
z `statystyki.podsumowanie` cztery pola i wyrzucala `pozycje_bez_zasiegu` —
pole, ktore istnieje dokladnie po to, zeby odroznic „zero wejsc" od „nie ma
karty". Zmierzone na produkcji 1 wrzesnia: 16 z 63 komentarzy nie ma kart
zasiegu i zapisuje sie zerem, przy 0 z 6 artykulow. Mianownik komentarzy byl
wiec zawyzony, a porownanie „artykul kontra komentarz" nieuczciwe w jedna
strone.

W3 — UZASADNIENIE KONTROLI NIEPRAWDZIWE O KODZIE, KTORY CYTUJE. Docstring
`pomiar_oslepl()` twierdzil, ze `browser.zapisz_czytelnikow` przy bledzie
„zwraca None i NIE DOPISUJE NIC". Bramka oddawala None TYLKO gdy byl blad
I OBIE listy byly puste, a `kto_nas_czyta` zbiera obserwujacych ZANIM klika
w zakladke „Subscribers" — pekniecie na kliknieciu zapisywalo wiec zrzut
OKROJONY, ktory w pliku wyglada na udany. Kontrola pilnujaca samej swiezosci
milczala. Rownolegle `browser.py` dostal pole `odczytane` (lista zakladek,
ktore odpowiedzialy) i bramke „nic nie odczytane = brak zrzutu"; ten test
sprawdza, ze `wzajemnosc` z tego pola korzysta, ale nie opiera sie na nim
wylacznie — siedem zrzutow z konca sierpnia go nie ma, a zakladka potrafi tez
odpowiedziec i oddac pustke.

KONTRDOWODY SA ODTWORZONE, NIE OPISANE. Regula sprzed kazdej poprawki jest tu
przeliczona na tych samych danych i pokazana obok nowej. Modul `wzajemnosc.py`
NIE ISTNIEJE w `6ed4e7d` (`git cat-file -e` konczy sie „exists on disk, but not
in 6ed4e7d"), wiec starej wersji nie da sie z niego wyciagnac — do SHA
przypiety jest `alarm.py`, ktory w tamtym stanie nie mial ZADNEJ kontroli
pomiaru wzajemnosci i to jest sprawdzane przez URUCHOMIENIE tamtego kodu.

DANE SA ATRAPA. Zrzuty W1 maja daty stale (nie zaleza od dnia uruchomienia),
a zrzuty W3 sa liczone wzgledem `now`, bo tam bada sie kontrole swiezosci.

BEZ SIECI, BEZ MODELI, BEZ PRODUKCYJNEJ BAZY. Z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_kolejnosc_odwzajemnienia.py
"""
import contextlib
import hashlib
import io
import json
import pathlib
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import types
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "agent-v2")
import config      # noqa: E402
import alarm       # noqa: E402
import browser     # noqa: E402
import statystyki  # noqa: E402
import wzajemnosc  # noqa: E402

# HISTORIA JEST WARUNKIEM TEGO TESTU. Kontrdowod ponizej odtwarza sie
# z commita sprzed naprawy, wiec w kopii z historia zalozona od nowa
# nie ma z czego go odtworzyc. Pominiecie jest wtedy JAWNE, zamiast
# wywalac sie w polowie pliku na `CalledProcessError`.
import historia   # noqa: E402

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


# ODCISKI PRZED PODMIANA `config.DATA_DIR` — po niej pilnowalibysmy atrapy.
PILNOWANE = [config.DB_PATH,
             config.DATA_DIR / "dziennik.jsonl",
             config.DATA_DIR / "czytelnicy.jsonl",
             config.DATA_DIR / "wzrost.jsonl",
             config.DATA_DIR / "statystyki.jsonl"]
PRZED = {str(p): odcisk(p) for p in PILNOWANE}

ZDJECIE_SCIEZEK = None
ORYG_DZIENNIK = browser.DZIENNIK
ORYG_POLACZENIE = alarm._polaczenie
KAT = pathlib.Path(tempfile.mkdtemp(prefix="kolejnosc-"))


def baza_w_pamieci():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE calls (at TEXT, cost_usd REAL)")
    conn.execute("CREATE TABLE runs (status TEXT, started_at TEXT)")
    return conn


def osoby(*uchwyty):
    return [{"uchwyt": u, "nazwa": u.upper()} for u in uchwyty]


def zaczepienie(rodzaj, komu, kiedy, udane=True):
    return {"kiedy": kiedy, "rodzaj": rodzaj, "udane": udane, "komu": komu}


def zapisz(dziennik, zrzuty, wzrost=None, staty=None):
    (KAT / "dziennik.jsonl").write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in dziennik) + "\n",
        encoding="utf-8")
    (KAT / "czytelnicy.jsonl").write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in zrzuty) + "\n",
        encoding="utf-8")
    for nazwa, dane in (("wzrost.jsonl", wzrost), ("statystyki.jsonl", staty)):
        plik = KAT / nazwa
        if dane is None:
            plik.unlink(missing_ok=True)
        else:
            plik.write_text(
                "\n".join(json.dumps(x, ensure_ascii=False) for x in dane) + "\n",
                encoding="utf-8")
    config.uzyj_katalogu_danych(KAT)
    browser.DZIENNIK = KAT / "dziennik.jsonl"


ZDJECIE_SCIEZEK = config.uzyj_katalogu_danych(KAT)
browser.DZIENNIK = KAT / "dziennik.jsonl"
alarm._polaczenie = baza_w_pamieci

# --- ATRAPA DO W1 -------------------------------------------------------------
#
# Trzy zrzuty o STALYCH datach. `stalybywalec` i `wiernysub` sa w zrzucie
# zerowym, czyli mogli byc z nami dowolnie dlugo wczesniej. `nowy` i `spozniony`
# dochodza dopiero w trzecim — tylko ich pojawienie sie da sie datowac.
S0, S1, S2 = ("2026-08-31T04:24:28+00:00", "2026-08-31T17:08:23+00:00",
              "2026-09-01T00:13:04+00:00")
ZRZUTY_W1 = [
    {"kiedy": S0, "obserwujacy": osoby("stalybywalec"),
     "subskrybenci": osoby("wiernysub")},
    {"kiedy": S1, "obserwujacy": osoby("stalybywalec"),
     "subskrybenci": osoby("wiernysub")},
    {"kiedy": S2, "obserwujacy": osoby("stalybywalec", "nowy", "spozniony"),
     "subskrybenci": osoby("wiernysub")},
]

DZIENNIK_W1 = [
    # PRZED: obserwujacy nas od zrzutu zerowego, zaczepiony PO ostatnim zrzucie.
    # To jest wierna kopia scenariusza `czytelnik1` z produkcji.
    zaczepienie("obserwacja", "stalybywalec", "2026-09-01T09:00:00+00:00"),
    # PO: zaczepiony 31 sierpnia o 12:00, czyli PRZED zrzutem, w ktorym go
    # jeszcze nie ma (17:08) — pojawia sie dopiero w nastepnym. Jedyne
    # prawdziwe odwzajemnienie w tym pliku.
    zaczepienie("obserwacja", "nowy", "2026-08-31T12:00:00+00:00"),
    # NIEORZEKALNA: subskrypcja z 16 sierpnia, czyli sprzed CALEJ historii
    # zrzutow. O tym, kto byl z nami przed 31 sierpnia, ten plik nie wie nic.
    zaczepienie("subskrypcja", "wiernysub", "2026-08-16T17:53:00+00:00"),
    # PRZED, ale przez kanaly: zaczepiony 09:00, a byl na liscie juz o 00:13.
    zaczepienie("subskrypcja", "spozniony", "2026-09-01T09:00:00+00:00"),
    zaczepienie("obserwacja", "ktosbezkonta", "2026-08-31T12:00:00+00:00", False),
]


def naiwnie(kubel):
    """REGULA SPRZED POPRAWKI: zrownanie uchwytow to odwzajemnienie.

    Dokladnie to robila `odwzajemnienie()` do 1 wrzesnia 2026 — brala liste
    dopasowan po uchwycie i dzielila przez liczbe udanych prob, nie pytajac
    ani razu, co bylo pierwsze.
    """
    udanych = kubel["udanych"]
    return len(kubel["pewne"]), udanych, (len(kubel["pewne"]) / udanych
                                          if udanych else None)


try:
    print("=== 1. ODWZAJEMNIENIE MA KIERUNEK W CZASIE (W1) ===")
    zapisz(DZIENNIK_W1, ZRZUTY_W1)
    odw = wzajemnosc.odwzajemnienie()
    obs, sub = odw["obserwacja"], odw["subskrypcja"]
    werdykty = {t["komu"]: t["kolejnosc"]
                for k in ("obserwacja", "subskrypcja")
                for t in odw[k]["pewne"] + odw[k]["niepewne"]}
    print("    werdykty: %s" % werdykty)
    sprawdz("obserwujacy od zrzutu zerowego, zaczepiony pozniej -> PRZED",
            werdykty.get("stalybywalec") == wzajemnosc.PRZED, werdykty)
    sprawdz("zaczepiony przed zrzutem, w ktorym go nie ma -> PO",
            werdykty.get("nowy") == wzajemnosc.PO, werdykty)
    sprawdz("zaczepiony przed CALA historia zrzutow -> NIEORZEKALNA",
            werdykty.get("wiernysub") == wzajemnosc.NIEORZEKALNA, werdykty)
    sprawdz("obserwacja: 1 odwzajemnienie z 2 orzekalnych (50%)",
            (len(obs["odwzajemnili"]), obs["orzekalnych"], obs["odsetek"])
            == (1, 2, 0.5),
            (obs["odwzajemnili"], obs["orzekalnych"], obs["odsetek"]))
    sprawdz("obserwacja: „byl wczesniej\" liczony osobno, nie jako sukces",
            len(obs["byli_wczesniej"]) == 1,
            [t["komu"] for t in obs["byli_wczesniej"]])
    sprawdz("subskrypcja: 0 z 1 orzekalnych, bo jedna proba nieorzekalna",
            (len(sub["odwzajemnili"]), sub["orzekalnych"],
             len(sub["nieorzekalne"])) == (0, 1, 1),
            (sub["odwzajemnili"], sub["orzekalnych"], sub["nieorzekalne"]))
    sprawdz("nieorzekalne WYPADAJA z mianownika, a nie licza sie jako porazka",
            sub["orzekalnych"] == sub["udanych"] - len(sub["nieorzekalne"]),
            (sub["orzekalnych"], sub["udanych"]))

    print("    KONTRDOWOD — regula sprzed poprawki na TYCH SAMYCH danych:")
    for klucz, d in (("obserwacja", obs), ("subskrypcja", sub)):
        stare = naiwnie(d)
        print("      %-12s STARA: %d z %d (%s)   NOWA: %d z %d orzekalnych"
              % (klucz, stare[0], stare[1],
                 "%d%%" % round(100 * stare[2]) if stare[2] is not None else "-",
                 len(d["odwzajemnili"]), d["orzekalnych"]))
    sprawdz("KONTRDOWOD: stara regula meldowala 2 z 2 (100%) obserwacji",
            naiwnie(obs) == (2, 2, 1.0), naiwnie(obs))
    sprawdz("KONTRDOWOD: i 2 z 2 (100%) subskrypcji",
            naiwnie(sub) == (2, 2, 1.0), naiwnie(sub))
    sprawdz("KONTRDOWOD: nowa regula daje INNE liczby (1 z 2 i 0 z 1)",
            (len(obs["odwzajemnili"]), len(sub["odwzajemnili"])) == (1, 0))

    print()
    print("=== 1b. TO SAMO WIDAC W WYDRUKU, NIE TYLKO W SLOWNIKU ===")
    tekst = "\n".join(wzajemnosc.raport())
    sprawdz("raport podaje odsetek z mianownika ORZEKALNYCH",
            "odwzajemnilo sie na pewno 1 z 2 orzekalnych (50%)" in tekst,
            [l for l in tekst.splitlines() if "orzekalnych" in l])
    sprawdz("raport nazywa „byl wczesniej\" odwrotnoscia odwzajemnienia",
            "byli z nami JUZ PRZED zaczepieniem: 1" in tekst,
            [l for l in tekst.splitlines() if "PRZED zaczepieniem" in l])
    sprawdz("raport pokazuje werdykt przy KAZDYM trafieniu",
            "kolejnosc: PRZED" in tekst and "kolejnosc: PO" in tekst
            and "kolejnosc: NIEORZEKALNA" in tekst,
            [l for l in tekst.splitlines() if "kolejnosc:" in l])
    sprawdz("naglowek dla alarmu tez podaje mianownik orzekalnych",
            any("orzekalnych" in l for l in wzajemnosc.naglowek()),
            wzajemnosc.naglowek())

    print()
    print("=== 2. KANALY: SIOSTRZANA GALAZ TEZ PATRZY NA ZEGAR (W1) ===")
    kan = wzajemnosc.kanaly()
    kanaly_osob = {s["uchwyt"]: s["kanal"] for s in kan["szczegoly"]}
    print("    %s   datowalnych %d z %d"
          % (kanaly_osob, kan["datowalnych"], kan["wszystkich_czytelnikow"]))
    sprawdz("zaczepienie PRZED pojawieniem sie nadal daje kanal",
            kanaly_osob.get("nowy") == "obserwacja", kanaly_osob)
    sprawdz("zaczepienie PO pojawieniu sie NIE daje juz kanalu",
            kanaly_osob.get("spozniony") == "nieznany", kanaly_osob)
    # KONTRDOWOD: regula sprzed poprawki brala sam fakt zaczepienia, bez daty.
    stary_kanal = {}
    for u in kanaly_osob:
        trafienia = [w for w in DZIENNIK_W1
                     if w["udane"] and w["komu"] == u]
        stary_kanal[u] = trafienia[0]["rodzaj"] if trafienia else "nieznany"
    print("    KONTRDOWOD: stara regula %s" % stary_kanal)
    sprawdz("KONTRDOWOD: stara regula dawala „subskrypcja\" spoznionemu",
            stary_kanal.get("spozniony") == "subskrypcja", stary_kanal)

    print()
    print("=== 3. TABELA POZYCYJNA POKAZUJE, CZEGO SUBSTACK NIE POLICZYL (W2) ===")
    # Scenariusz zmierzony: 10 komentarzy, 3 z kartami zasiegu (razem 75
    # wyswietlen i 2 subskrypcje), 7 bez kart — zapisanych zerem, bo Substack
    # ich nie policzyl. Do tego 2 artykuly, oba policzone.
    STATY = ([{"kiedy": "2026-09-01T10:00:00+00:00", "rodzaj": "komentarz",
               "id": "k%d" % i, "wyswietlenia": 25, "subskrypcje": 1 if i < 2 else 0,
               "obserwacje": 0, "ma_karty_zasiegu": True} for i in range(3)]
             + [{"kiedy": "2026-09-01T10:00:00+00:00", "rodzaj": "komentarz",
                 "id": "k%d" % i, "wyswietlenia": 0, "subskrypcje": 0,
                 "obserwacje": 0, "ma_karty_zasiegu": False}
                for i in range(3, 10)]
             + [{"kiedy": "2026-09-01T10:00:00+00:00", "rodzaj": "artykul",
                 "id": "a%d" % i, "wyswietlenia": 50, "subskrypcje": 1,
                 "obserwacje": 0, "ma_karty_zasiegu": True} for i in range(2)])
    zapisz(DZIENNIK_W1, ZRZUTY_W1, staty=STATY)
    poz = wzajemnosc.kanaly()["pozycyjnie"]
    print("    %s" % poz)
    sprawdz("komentarze: 10 pozycji, ale zmierzone tylko 3",
            (poz["komentarz"]["pozycje"], poz["komentarz"]["zmierzone"],
             poz["komentarz"]["bez_zasiegu"]) == (10, 3, 7), poz["komentarz"])
    sprawdz("artykuly: policzone wszystkie",
            (poz["artykul"]["pozycje"], poz["artykul"]["bez_zasiegu"]) == (2, 0),
            poz["artykul"])
    tekst2 = "\n".join(wzajemnosc.raport())
    sprawdz("wydruk mowi, ile pozycji Substack POLICZYL",
            "10 pozycji, POLICZONYCH PRZEZ SUBSTACK   3 (bez kart zasiegu  7)"
            in tekst2, [l for l in tekst2.splitlines() if "POLICZONYCH" in l])
    sprawdz("wydruk nazywa porownanie kanalow niesprawiedliwym",
            "NIESPRAWIEDLIWE W JEDNA STRONE" in tekst2
            and "`komentarz` (7 z 10 niepoliczonych)" in tekst2,
            [l for l in tekst2.splitlines() if "niepoliczonych" in l])
    sprawdz("i wskazuje kanal, ktory ma karty do wszystkiego",
            "Karty dla WSZYSTKICH swoich pozycji maja: `artykul`" in tekst2,
            [l for l in tekst2.splitlines() if "WSZYSTKICH" in l])
    # KONTRDOWOD: rzut tabeli sprzed poprawki bral cztery pola i gubil piate.
    stara_tabela = {k: statystyki.podsumowanie(k)[k2]
                    for k in ("komentarz",)
                    for k2 in ("pozycje",)}
    print("    KONTRDOWOD: stara tabela drukowala „%d pozycji, %d wyswietlen"
          " -> %d subskrypcji\", nie mowiac o 7 niepoliczonych"
          % (stara_tabela["komentarz"],
             statystyki.podsumowanie("komentarz")["wyswietlenia"],
             statystyki.podsumowanie("komentarz")["subskrypcje"]))
    sprawdz("KONTRDOWOD: stary mianownik byl 10 zamiast 3 (zawyzony 3,3x)",
            stara_tabela["komentarz"] == 10
            and poz["komentarz"]["zmierzone"] == 3,
            (stara_tabela, poz["komentarz"]))

    print()
    print("=== 4. ZRZUT OKROJONY JEST WYKRYWANY, A NIE BRANY ZA UDANY (W3) ===")
    # Zrzuty liczone wzglednie, bo tu bada sie kontrole swiezosci. Srodkowy
    # zrzut ma PUSTA liste subskrybentow — dokladnie tak wyglada zapis po
    # pekniecu na kliknieciu w zakladke „Subscribers".
    def kiedy(godzin_temu):
        return (datetime.now(timezone.utc)
                - timedelta(hours=godzin_temu)).isoformat(timespec="seconds")

    T12, T6, T1 = kiedy(12), kiedy(6), kiedy(1)
    ZRZUTY_W3 = [
        {"kiedy": T12, "obserwujacy": osoby("stalybywalec"),
         "subskrybenci": osoby("wiernysub")},
        {"kiedy": T6, "obserwujacy": osoby("stalybywalec"),
         "subskrybenci": []},
        {"kiedy": T1, "obserwujacy": osoby("stalybywalec"),
         "subskrybenci": osoby("wiernysub", "swiezy")},
    ]
    DZIENNIK_W3 = [zaczepienie("subskrypcja", "swiezy", kiedy(8))]
    zapisz(DZIENNIK_W3, ZRZUTY_W3)
    zrzuty = wzajemnosc.zrzuty_czytelnikow()
    print("    okrojone: %s" % [(i, z["okrojone"]) for i, z in enumerate(zrzuty)
                                if z["okrojony"]])
    sprawdz("srodkowy zrzut rozpoznany jako okrojony",
            [z["okrojony"] for z in zrzuty] == [False, True, False],
            [z["okrojony"] for z in zrzuty])
    sprawdz("i wiadomo, KTORA grupa znikla",
            list(zrzuty[1]["okrojone"]) == ["subskrybenci"],
            zrzuty[1]["okrojone"])
    komunikat = wzajemnosc.pomiar_oslepl()
    print("    pomiar_oslepl -> %s" % komunikat)
    sprawdz("kontrola alarmuje, choc plik jest DZISIEJSZY",
            bool(komunikat) and "OKROJONY" in komunikat, komunikat)
    sprawdz("komunikat podaje swiadka, na ktorym sie opiera",
            "inne zrzuty" in (komunikat or ""), komunikat)

    # DRUGORZEDNY SKUTEK: nieobecnosc w okrojonym zrzucie jest pozorna, wiec
    # zaczepienie sprzed niego NIE jest dowodem odwzajemnienia.
    trafienia = wzajemnosc.odwzajemnienie()["subskrypcja"]
    sprawdz("zaczepienie przed OKROJONYM zrzutem nie daje odwzajemnienia",
            (len(trafienia["odwzajemnili"]), len(trafienia["nieorzekalne"]))
            == (0, 1),
            (trafienia["odwzajemnili"], trafienia["nieorzekalne"]))
    sprawdz("czlowiek po okrojonym zrzucie nie jest datowalny",
            wzajemnosc.kanaly()["datowalnych"] == 0,
            wzajemnosc.kanaly()["szczegoly"])
    # KONTRDOWOD: stara regula datowalnosci to samo „pierwszy_zrzut > 0".
    ludzie = wzajemnosc.czytelnicy()
    stara_datowalnosc = sorted(u for u, w in ludzie.items()
                               if w["pierwszy_zrzut"] > 0)
    print("    KONTRDOWOD: stara regula datowala %s, nowa %s"
          % (stara_datowalnosc,
             sorted(u for u, w in ludzie.items() if w["absencja_pewna"])))
    sprawdz("KONTRDOWOD: stara regula uznawala `swiezy` za datowalnego",
            stara_datowalnosc == ["swiezy"], stara_datowalnosc)

    print()
    print("=== 4b. LICZNIK PROFILU JAKO DRUGI, NIEZALEZNY SWIADEK ===")
    # Gdy zakladka jest zepsuta OD POCZATKU, zaden inny zrzut nie ma w tej
    # grupie nikogo — i wtedy jedynym swiadkiem jest licznik z `wzrost.jsonl`.
    ZRZUTY_PUSTE = [
        {"kiedy": T6, "obserwujacy": osoby("stalybywalec"), "subskrybenci": []},
        {"kiedy": T1, "obserwujacy": osoby("stalybywalec"), "subskrybenci": []},
    ]
    zapisz(DZIENNIK_W3, ZRZUTY_PUSTE, wzrost=[
        {"kiedy": T6, "obserwujacy": 1, "subskrybenci": 9},
        {"kiedy": T1, "obserwujacy": 1, "subskrybenci": 9}])
    k2 = wzajemnosc.pomiar_oslepl()
    print("    pomiar_oslepl -> %s" % k2)
    sprawdz("pusta grupa wbrew licznikowi profilu tez jest okrojeniem",
            bool(k2) and "licznik profilu" in k2, k2)
    # A konto, ktore po prostu nie ma jeszcze subskrybentow, NIE alarmuje —
    # inaczej kontrola krzyczalaby przez pierwszy tydzien istnienia konta.
    zapisz(DZIENNIK_W3, ZRZUTY_PUSTE, wzrost=[
        {"kiedy": T6, "obserwujacy": 1, "subskrybenci": 0},
        {"kiedy": T1, "obserwujacy": 1, "subskrybenci": 0}])
    sprawdz("mlode konto bez subskrybentow nie alarmuje",
            wzajemnosc.pomiar_oslepl() is None, wzajemnosc.pomiar_oslepl())

    print()
    print("=== 4c. STARE OKROJENIE ZOSTAJE W RAPORCIE, ALE NIE BUDZI MAILEM ===")
    # Alarm ma budzic do rzeczy, ktora da sie jeszcze zrobic. Okrojenie sprzed
    # trzech tygodni jest szkoda trwala i nalezy do raportu, a nie do poczty —
    # inaczej ten sam mail przychodzilby codziennie do konca istnienia pliku.
    STARE = (datetime.now(timezone.utc) - timedelta(days=20)).isoformat(
        timespec="seconds")
    zapisz(DZIENNIK_W3, [
        {"kiedy": STARE, "obserwujacy": osoby("stalybywalec"),
         "subskrybenci": []},
        {"kiedy": T6, "obserwujacy": osoby("stalybywalec"),
         "subskrybenci": osoby("wiernysub")},
        {"kiedy": T1, "obserwujacy": osoby("stalybywalec"),
         "subskrybenci": osoby("wiernysub")}])
    sprawdz("okrojenie sprzed 20 dni nie alarmuje (prog: %d dni)"
            % wzajemnosc.ZRZUT_STARSZY_NIZ_DNI,
            wzajemnosc.pomiar_oslepl() is None, wzajemnosc.pomiar_oslepl())
    sprawdz("ale nadal jest widoczne w naglowku codziennej kontroli",
            any("okrojone" in l for l in wzajemnosc.naglowek()),
            wzajemnosc.naglowek())
    sprawdz("i w pelnym raporcie, z data i uzasadnieniem",
            "ZRZUTY OKROJONE: 1 z 3" in "\n".join(wzajemnosc.raport()),
            [l for l in wzajemnosc.raport() if "OKROJON" in l])

    print()
    print("=== 4d. ZRZUT, KTORY SAM MOWI, CZEGO NIE ODCZYTAL ===")
    # `browser.zapisz_czytelnikow` zapisuje od 1 wrzesnia pole `odczytane`
    # z nazwami zakladek, ktore naprawde odpowiedzialy. To swiadek mocniejszy
    # od naszego wnioskowania i dziala nawet wtedy, gdy zadnego innego sladu
    # nie ma: ani licznika, ani drugiego zrzutu z ludzmi w tej grupie.
    zapisz(DZIENNIK_W3, [
        {"kiedy": T6, "obserwujacy": osoby("stalybywalec"), "subskrybenci": [],
         "odczytane": ["obserwujacy"]},
        {"kiedy": T1, "obserwujacy": osoby("stalybywalec"), "subskrybenci": [],
         "odczytane": ["obserwujacy"]}])
    k3 = wzajemnosc.pomiar_oslepl()
    print("    pomiar_oslepl -> %s" % (k3 or "")[:120])
    sprawdz("brak zakladki w `odczytane` wystarcza za caly dowod",
            bool(k3) and "sam mowi" in k3, k3)
    # A ten sam ksztalt danych z PELNA deklaracja to zmierzone zero: konto,
    # ktore naprawde nie ma jeszcze subskrybentow, nie moze wygladac na awarie.
    zapisz(DZIENNIK_W3, [
        {"kiedy": T6, "obserwujacy": osoby("stalybywalec"), "subskrybenci": [],
         "odczytane": ["obserwujacy", "subskrybenci"]},
        {"kiedy": T1, "obserwujacy": osoby("stalybywalec"), "subskrybenci": [],
         "odczytane": ["obserwujacy", "subskrybenci"]}])
    sprawdz("obie zakladki odczytane i puste to ZMIERZONE zero, nie awaria",
            wzajemnosc.pomiar_oslepl() is None, wzajemnosc.pomiar_oslepl())
    # ZGODNOSC WSTECZ: siedem zrzutow z konca sierpnia tego pola nie ma. Brak
    # klucza ma znaczyc „nie wiadomo", a nie „nie odczytano nic" — inaczej caly
    # dotychczasowy plik zostalby uznany za okrojony.
    zapisz(DZIENNIK_W3, [
        {"kiedy": T6, "obserwujacy": osoby("stalybywalec"),
         "subskrybenci": osoby("wiernysub")},
        {"kiedy": T1, "obserwujacy": osoby("stalybywalec"),
         "subskrybenci": osoby("wiernysub")}])
    sprawdz("zrzut bez pola `odczytane` nie jest z gory podejrzany",
            all(not z["okrojony"] for z in wzajemnosc.zrzuty_czytelnikow()),
            [z["okrojone"] for z in wzajemnosc.zrzuty_czytelnikow()])

    print()
    # HISTORIA JEST WARUNKIEM TYLKO TEGO, CO PONIZEJ.
    #
    # Guard stal w naglowku pliku, wiec w kopii z historia zalozona
    # od nowa gasl CALY test, a nie ten jeden blok, ktory naprawde
    # potrzebuje starej wersji. Policzone 4 wrzesnia 2026: 617
    # asercji w 17 plikach nie wykonywalo sie ani razu — i zestaw
    # wygladal na zdany, bo pominiecie konczy sie kodem 0.
    #
    # `SystemExit` nie dziedziczy po `Exception`, wiec przechodzi
    # przez oslony tego pliku i wykonuje `finally` — sprzatanie
    # po tescie dzieje sie normalnie.
    historia.wymaga_historii("6ed4e7d", zdane=zdane, oblane=oblane)

    print("=== 5. KONTRDOWOD PRZYPIETY DO 6ed4e7d (NIE DO HEAD) ===")
    SHA = "6ed4e7d"
    brak = subprocess.run(["git", "cat-file", "-e",
                           "%s:agent-v2/wzajemnosc.py" % SHA],
                          capture_output=True, cwd=".")
    sprawdz("w %s nie ma jeszcze `wzajemnosc.py` — starej wersji nie da sie"
            " stamtad wziac" % SHA, brak.returncode != 0, brak.returncode)
    stare_zrodlo = subprocess.run(
        ["git", "show", "%s:agent-v2/alarm.py" % SHA],
        capture_output=True, cwd=".").stdout.decode("utf-8")
    sprawdz("ale `alarm.py` z %s daje sie wyciagnac" % SHA,
            len(stare_zrodlo) > 1000, len(stare_zrodlo))
    stary_modul = types.ModuleType("alarm_%s" % SHA)
    stary_modul.__dict__["__file__"] = "agent-v2/alarm.py"
    exec(compile(stare_zrodlo, "agent-v2/alarm.py(%s)" % SHA, "exec"),
         stary_modul.__dict__)
    stary_modul._polaczenie = baza_w_pamieci
    # ZADNEGO WYSYLANIA POCZTY — ani ze starej wersji, ani z nowej.
    wyslane = []
    stary_modul.wyslij = lambda k, t, tr: wyslane.append(("stary", k)) or True
    oryg_wyslij = alarm.wyslij
    alarm.wyslij = lambda k, t, tr: wyslane.append(("nowy", k)) or True

    zapisz(DZIENNIK_W3, ZRZUTY_W3)   # znowu okrojony srodkowy zrzut

    def kontrola(modul):
        bufor = io.StringIO()
        with contextlib.redirect_stdout(bufor):
            znalezione = modul.sprawdz_wszystko()
        return znalezione, bufor.getvalue()

    try:
        stare_znaleziska, stary_tekst = kontrola(stary_modul)
        nowe_znaleziska, nowy_tekst = kontrola(alarm)
    finally:
        alarm.wyslij = oryg_wyslij
    sprawdz("KONTRDOWOD: %s nie zglasza ANI SLOWA o pomiarze wzajemnosci" % SHA,
            not any("wzajemnosc" in z for z in stare_znaleziska)
            and "pomiar-wzajemnosci" not in stary_tekst,
            stare_znaleziska)
    sprawdz("KONTRDOWOD: %s nie zauwaza okrojonego zrzutu" % SHA,
            "OKROJONY" not in stary_tekst and "okrojon" not in stary_tekst,
            stary_tekst[-400:])
    sprawdz("nowa wersja zglasza okrojony zrzut jako znalezisko",
            any("pomiar-wzajemnosci" in z and "OKROJONY" in z
                for z in nowe_znaleziska), nowe_znaleziska)
    sprawdz("i robi to w sciezce BEZ ARGUMENTOW, czyli tej z zegara",
            "pomiar-wzajemnosci" in nowy_tekst, nowy_tekst[-600:])
    sprawdz("zadna z wersji nie wyslala poczty poza atrape",
            all(k[0] in ("stary", "nowy") for k in wyslane), wyslane)

    print()
    print("=== 6. STARA REGULA SWIEZOSCI PRZEPUSCILABY TEN ZRZUT ===")
    # Kontrola sprzed poprawki pytala WYLACZNIE o wiek najnowszego zrzutu.
    def stara_kontrola():
        zrzuty_ = wzajemnosc.wczytaj(wzajemnosc.CZYTELNICY)
        if not zrzuty_:
            return "brak pliku"
        ostatni = max((wzajemnosc._chwila(z.get("kiedy")) for z in zrzuty_
                       if wzajemnosc._chwila(z.get("kiedy"))), default=None)
        if ostatni is None:
            return "brak dat"
        dni = (datetime.now(timezone.utc).replace(tzinfo=None) - ostatni).days
        return ("stary" if dni > wzajemnosc.ZRZUT_STARSZY_NIZ_DNI else None)

    print("    STARA: %s    NOWA: %s"
          % (stara_kontrola(), (wzajemnosc.pomiar_oslepl() or "")[:60]))
    sprawdz("KONTRDOWOD: stara regula milczy na okrojonym zrzucie",
            stara_kontrola() is None, stara_kontrola())
    sprawdz("nowa regula na tych samych danych alarmuje",
            bool(wzajemnosc.pomiar_oslepl()), wzajemnosc.pomiar_oslepl())
finally:
    config.przywroc_katalog_danych(ZDJECIE_SCIEZEK)
    browser.DZIENNIK = ORYG_DZIENNIK
    alarm._polaczenie = ORYG_POLACZENIE
    shutil.rmtree(KAT, ignore_errors=True)

print()
print("=== PRODUKCJA: bez zmian ===")
zle = 0
for p in PILNOWANE:
    ok = odcisk(p) == PRZED[str(p)]
    zle += 0 if ok else 1
    print("  %-24s %s" % (pathlib.Path(p).name,
                          "bez zmian" if ok else "ZMIENIONA"))

print()
print("=== WYNIK: %d zdanych, %d oblanych%s ===" %
      (zdane, oblane, ", PRODUKCJA RUSZONA" if zle else ""))
sys.exit(1 if (oblane or zle) else 0)
