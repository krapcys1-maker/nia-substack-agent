# -*- coding: utf-8 -*-
"""Czy raport wzajemnosci liczy to, co trzeba — i czy brak danych wyglada na brak.

CO BYLO PRZED. `data/czytelnicy.jsonl` byl ZAPISYWANY I NIECZYTANY PRZEZ NIC.
1 wrzesnia 2026 `grep czytelnicy agent-v2/*.py` oddawal trzy trafienia, wszystkie
w `browser.py`: sciezka (967) i zapis (1069-1070). System zbieral imienna liste
swoich czytelnikow od 31 sierpnia i ani razu nie zestawil jej z lista osob,
ktore sam zaczepil.

TRZY RZECZY, KTORE TEN TEST PILNUJE — kazda dlatego, ze bez niej raport
klamalby w sposob wygodny.

1. BRAK PROB TO NIE ZERO PROCENT. Blok obserwacji ma w dzienniku dwie proby,
   obie z 23 sierpnia i obie nieudane („nie ma przycisku obserwacja"), czyli
   ZERO udanych obserwacji w calej historii. „0% odwzajemnien" bylo by tu
   klamstwem o strategii, a prawda jest o usterce. Mierzymy to na wartosci
   `odsetek`: `None` przy zerowym mianowniku, liczba przy niezerowym.

2. ZDARZENIE POZYSKANIA NIE JEST DOWODEM WCZESNIEJSZEGO KONTAKTU. `skutek`
   obejmuje typy `follow` i `free_subscription`, czyli powiadomienia „ktos cie
   zaobserwowal". Naiwna regula „kazdy skutek z pasujaca nazwa to slad
   interakcji" daje na produkcyjnych danych 11 z 19 naszych czytelnikow —
   liczba, ktora brzmi jak odkrycie i jest kolem: obserwujacy ma zdarzenie
   `follow`, bo jest obserwujacym. Po odjeciu samego pozyskania zostaje
   4 z 19. KONTRDOWOD ponizej odtwarza naiwna regule na tych samych danych
   i pokazuje obie liczby obok siebie — na atrapie wychodzi 12 wobec 4, bo
   atrapa ma dodatkowo jedno zdarzenie typu, ktorego nie znamy. Na produkcji
   takiego typu nie bylo i dlatego tam ta sama regula dawala rowno 11.

3. POMINIECIE NIE JEST PROBA. `obserwacja_pominieta` zapisuje sie z
   `udane=True` i znaczy „nie klikalem, bo juz go obserwujemy" — zaliczone do
   prob zawyzaloby mianownik o dzialania, ktorych nie bylo.

KONTRDOWOD DRUGI JEST PRZYPIETY DO SHA `6ed4e7d`, NIE DO `HEAD`. Wersja
odniesienia to `git show 6ed4e7d:agent-v2/alarm.py` — ostatni stan sprzed tej
zmiany. Przypiecie do HEAD gasi kontrdowod przy pierwszym wlasnym commicie
i wlasnie na tym przejechalismy sie w tej sesji (`64d881a`).

DANE SA ATRAPA O PRODUKCYJNYCH PROPORCJACH, nie kopia produkcji: 19 czytelnikow
(4 z kontaktem z trescia, 7 z samym pozyskaniem, 8 bez sladu), 18 prob
subskrypcji (12 udanych: 4 sprzed przestawienia konta na AI, 8 po), 2 nieudane
proby obserwacji. Te same liczby, co zmierzone 1 wrzesnia 2026 na serwerze.

BEZ SIECI, BEZ MODELI, BEZ PRODUKCYJNEJ BAZY. Z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_wzajemnosc.py
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
import config     # noqa: E402
import alarm      # noqa: E402
import browser    # noqa: E402
import wzajemnosc  # noqa: E402

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


# ODCISKI BIERZEMY, ZANIM PODMIENIMY `config.DATA_DIR`. Po podmianie
# `config.DATA_DIR / "dziennik.jsonl"` wskazuje katalog tymczasowy i sekcja
# „PRODUKCJA: bez zmian" pilnowalaby wlasnej atrapy.
PILNOWANE = [config.DB_PATH,
             config.DATA_DIR / "dziennik.jsonl",
             config.DATA_DIR / "czytelnicy.jsonl",
             config.DATA_DIR / "wzrost.jsonl",
             config.DATA_DIR / "statystyki.jsonl"]
PRZED = {str(p): odcisk(p) for p in PILNOWANE}

ZDJECIE_SCIEZEK = None
ORYG_DZIENNIK = browser.DZIENNIK
ORYG_POLACZENIE = alarm._polaczenie
KAT = pathlib.Path(tempfile.mkdtemp(prefix="wzajemnosc-"))


def baza_w_pamieci():
    """Pusta baza z tabelami, ktorych `alarm.przeglad` dotyka na koncu."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE calls (at TEXT, cost_usd REAL)")
    conn.execute("CREATE TABLE runs (status TEXT, started_at TEXT)")
    return conn


# --- ATRAPA DANYCH ------------------------------------------------------------
#
# Uchwyty i nazwy sa zmyslone, ale UKLAD jest produkcyjny: nazwa wyswietlana
# czytelnika nie ma nic wspolnego z jego uchwytem, a `skutek.kto` to LISTA NAZW
# WYSWIETLANYCH, nie uchwytow. Na tym polega cala trudnosc zestawiania i test
# bylby bez wartosci, gdyby uzywal wszedzie tego samego napisu.

KONTAKT = [("czyt01", "Ada Pierwsza"), ("czyt02", "Borys Drugi"),
           ("czyt03", "Cyryl Trzeci"), ("czyt04", "Dorota Czwarta")]
POZYSKANIE = [("czyt%02d" % i, "Osoba %d" % i) for i in range(5, 12)]
BEZ_SLADU = [("czyt%02d" % i, "Nikt %d" % i) for i in range(12, 20)]
WSZYSCY = dict(KONTAKT + POZYSKANIE + BEZ_SLADU)


def _os(uchwyty):
    return [{"uchwyt": u, "nazwa": WSZYSCY[u]} for u in uchwyty]


# Trzy zrzuty. Kto jest w ZEROWYM, tego pojawienia sie nie da datowac — mogl
# przyjsc kiedykolwiek wczesniej. Datowalni sa tylko ci, ktorzy doszli pozniej.
ZRZUTY = [
    {"kiedy": "2026-08-31T04:24:28+00:00",
     "obserwujacy": _os(["czyt01", "czyt02", "czyt05", "czyt06", "czyt07",
                         "czyt12", "czyt13", "czyt14", "czyt15"]),
     "subskrybenci": _os(["czyt03", "czyt08", "czyt09", "czyt10", "czyt11",
                          "czyt16", "czyt17"])},
    {"kiedy": "2026-08-31T11:38:23+00:00",
     "obserwujacy": _os(["czyt01", "czyt02", "czyt05", "czyt06", "czyt07",
                         "czyt12", "czyt13", "czyt14", "czyt15"]),
     "subskrybenci": _os(["czyt03", "czyt08", "czyt09", "czyt10", "czyt11",
                          "czyt16", "czyt17", "czyt04"])},
    {"kiedy": "2026-09-01T00:13:04+00:00",
     "obserwujacy": _os(["czyt01", "czyt02", "czyt05", "czyt06", "czyt07",
                         "czyt12", "czyt13", "czyt14", "czyt15",
                         "czyt18", "czyt19"]),
     "subskrybenci": _os(["czyt03", "czyt08", "czyt09", "czyt10", "czyt11",
                          "czyt16", "czyt17", "czyt04"])},
]


def skutek(typ, kto, kiedy_zdarzenia, czego=None):
    return {"kiedy": "2026-09-01T11:38:09+00:00", "rodzaj": "skutek",
            "udane": True, "zdarzenie": "%s:%s" % (typ, czego or "x"),
            "typ": typ, "czego": czego, "ilu": len(kto), "kto": kto,
            "kiedy_zdarzenia": kiedy_zdarzenia}


def zaczepienie(rodzaj, komu, kiedy, udane=True, powod=""):
    w = {"kiedy": kiedy, "rodzaj": rodzaj, "udane": udane, "komu": komu}
    if powod:
        w["powod"] = powod
    return w


def dziennik_produkcyjny():
    """Dziennik o proporcjach zmierzonych 1 wrzesnia 2026."""
    w = []

    # DWIE PROBY OBSERWACJI, OBIE NIEUDANE, OBIE SPRZED PRZESTAWIENIA NA AI.
    w.append(zaczepienie("obserwacja", "writersartistsyearbook",
                         "2026-08-23T07:56:16+00:00", False,
                         "nie ma przycisku obserwacja"))
    w.append(zaczepienie("obserwacja", "thebuttergirlfriend",
                         "2026-08-23T11:50:03+00:00", False,
                         "nie ma przycisku obserwacja"))

    # 18 PROB SUBSKRYPCJI: 12 udanych (4 sprzed 25 sierpnia, 8 po), 6 nieudanych.
    for i, dzien in enumerate(("16", "17", "17", "19")):
        w.append(zaczepienie("subskrypcja", "celstary%d" % i,
                             "2026-08-%sT12:00:00+00:00" % dzien))
    for i, dzien in enumerate(("25", "25", "26", "26", "29", "29", "29", "30")):
        w.append(zaczepienie("subskrypcja", "celnowy%d" % i,
                             "2026-08-%sT12:00:00+00:00" % dzien))
    for dzien in ("16", "16", "16"):
        w.append(zaczepienie("subskrypcja", "www",
                             "2026-08-%sT13:00:00+00:00" % dzien, False))
    for cel, dzien in (("theweeklyscrapbook", "25"), ("newyorker", "26"),
                       ("post", "26")):
        w.append(zaczepienie("subskrypcja", cel,
                             "2026-08-%sT14:00:00+00:00" % dzien, False,
                             "nie ma przycisku subskrypcja"))

    # NASZE POZYCJE plus reakcje na nie — material na pytanie o czas odzewu.
    # 12 reakcji na notki (prog probki to 10, wiec wniosek wolno wyciagnac)
    # i 3 na komentarze (ponizej progu — ma powiedziec, ze probka za mala).
    for i in range(12):
        ident = "70000%02d" % i
        w.append({"kiedy": "2026-08-28T10:00:00+00:00", "rodzaj": "notka",
                  "udane": True, "slow": 40, "tekst": "x", "id": ident})
        w.append(skutek("note_like", ["Ada Pierwsza"],
                        "2026-08-28T12:00:00", int(ident)))
    for i in range(3):
        ident = 8000000 + i
        w.append({"kiedy": "2026-08-28T10:00:00+00:00", "rodzaj": "komentarz",
                  "udane": True, "slow": 30, "tekst": "x",
                  "gdzie": "https://obcy.substack.com/p/a", "nasz_id": ident})
        w.append(skutek("comment_like", ["Borys Drugi"],
                        "2026-08-29T10:00:00", ident))

    # KONTAKT Z TRESCIA dla czterech osob. Dorota (czyt04) dostaje go PRZED
    # zrzutem, w ktorym sie pojawia — tylko dzieki temu da sie jej przypisac
    # kanal, i tylko ona jest w tym zestawie datowalna.
    w.append(skutek("note_reply", ["Cyryl Trzeci"], "2026-08-26T09:55:29"))
    w.append(skutek("restack", ["Dorota Czwarta"], "2026-08-31T05:10:00"))
    w.append(skutek("note_like", ["Dorota Czwarta"], "2026-08-31T06:20:00"))

    # SIEDEM OSOB, KTORYCH JEDYNY SLAD TO SAMO POZYSKANIE. To jest cala
    # roznica miedzy 11 z 19 a 4 z 19.
    for uchwyt, nazwa in POZYSKANIE[:4]:
        w.append(skutek("follow", [nazwa], "2026-08-30T08:00:00"))
    for uchwyt, nazwa in POZYSKANIE[4:]:
        w.append(skutek("free_subscription", [nazwa], "2026-08-30T09:00:00"))

    # NASZE WLASNE ZDARZENIE w tym samym strumieniu. Bez odsiania konto samo
    # sobie wychodzi na czytelnika.
    w.append(skutek("scheduled_note_sent", ["Your Publication"],
                    "2026-08-30T10:00:00"))
    # TYP, KTOREGO NIE ZNAMY. Ma trafic do „nieznanych", a nie podbic kontakty.
    w.append(skutek("cos_czego_nie_znam", ["Nikt 12"], "2026-08-30T11:00:00"))
    return w


def zapisz(dziennik, zrzuty=ZRZUTY, wzrost=None):
    (KAT / "dziennik.jsonl").write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in dziennik) + "\n",
        encoding="utf-8")
    (KAT / "czytelnicy.jsonl").write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in zrzuty) + "\n",
        encoding="utf-8")
    plik_wzrostu = KAT / "wzrost.jsonl"
    if wzrost is None:
        plik_wzrostu.unlink(missing_ok=True)
    else:
        plik_wzrostu.write_text(
            "\n".join(json.dumps(x, ensure_ascii=False) for x in wzrost) + "\n",
            encoding="utf-8")
    config.uzyj_katalogu_danych(KAT)
    browser.DZIENNIK = KAT / "dziennik.jsonl"


ZDJECIE_SCIEZEK = config.uzyj_katalogu_danych(KAT)
browser.DZIENNIK = KAT / "dziennik.jsonl"
alarm._polaczenie = baza_w_pamieci

try:
    print("=== 1. BRAK PROB TO BRAK ODPOWIEDZI, NIE ZERO PROCENT ===")
    zapisz(dziennik_produkcyjny())
    odw = wzajemnosc.odwzajemnienie()
    obs, sub = odw["obserwacja"], odw["subskrypcja"]
    print("    obserwacja: %s" % {k: obs[k] for k in
                                  ("prob", "udanych", "nieudanych", "odsetek")})
    sprawdz("obserwacja: dwie proby policzone", obs["prob"] == 2, obs["prob"])
    sprawdz("obserwacja: zero udanych", obs["udanych"] == 0, obs["udanych"])
    sprawdz("obserwacja: odsetek to None, a nie 0.0 — brak mianownika",
            obs["odsetek"] is None, obs["odsetek"])
    sprawdz("subskrypcja: 18 prob, 12 udanych",
            (sub["prob"], sub["udanych"]) == (18, 12),
            (sub["prob"], sub["udanych"]))
    sprawdz("subskrypcja: odsetek JEST liczba, bo mianownik niezerowy",
            sub["odsetek"] == 0.0, sub["odsetek"])
    sprawdz("subskrypcja: nikt z zaczepionych nie jest naszym czytelnikiem",
            (len(sub["pewne"]), len(sub["niepewne"]), len(sub["bez"]))
            == (0, 0, 12),
            (len(sub["pewne"]), len(sub["niepewne"]), len(sub["bez"])))

    print()
    print("=== 2. TA SAMA LICZBA 0 ZNACZY DWIE ROZNE RZECZY ===")
    # Dokladamy JEDNA udana obserwacje, ktorej cel nie jest naszym czytelnikiem.
    # Wynik odwzajemnien nadal jest zerowy, ale teraz to jest POMIAR, nie brak
    # pomiaru — i te dwa stany musza sie roznic w danych, nie tylko w zdaniu.
    zapisz(dziennik_produkcyjny()
           + [zaczepienie("obserwacja", "ktostam",
                          "2026-08-30T09:00:00+00:00")])
    obs2 = wzajemnosc.odwzajemnienie()["obserwacja"]
    sprawdz("po jednej udanej probie odsetek przestaje byc None",
            obs2["odsetek"] == 0.0, obs2["odsetek"])
    sprawdz("i to jest INNA wartosc niz przy braku prob",
            obs["odsetek"] != obs2["odsetek"],
            (obs["odsetek"], obs2["odsetek"]))

    print()
    print("=== 3. POMINIECIE NIE JEST PROBA ===")
    zapisz(dziennik_produkcyjny()
           + [{"kiedy": "2026-08-30T10:00:00+00:00",
               "rodzaj": "obserwacja_pominieta", "udane": True,
               "komu": "juz_obserwowany", "powod": "juz go obserwujemy"}
              for _ in range(5)])
    obs3 = wzajemnosc.odwzajemnienie()["obserwacja"]
    sprawdz("piec pominiec nie podbilo liczby prob",
            obs3["prob"] == 2, obs3["prob"])
    sprawdz("ale sa policzone osobno i widoczne",
            obs3["pominietych"] == 5, obs3["pominietych"])
    sprawdz("i nadal nie ma mianownika", obs3["odsetek"] is None,
            obs3["odsetek"])

    print()
    print("=== 4. „NA PEWNO\" I „NIEPEWNE\" NIE SA SKLEJONE ===")
    # Trzy udane obserwacje: jedna trafia w UCHWYT czytelnika (pewne), druga
    # tylko w jego NAZWE WYSWIETLANA po znormalizowaniu (niepewne — uchwyt
    # publikacji i uchwyt uzytkownika to dwie rozne przestrzenie nazw),
    # trzecia w nikogo.
    zapisz(dziennik_produkcyjny() + [
        zaczepienie("obserwacja", "czyt01", "2026-08-30T09:00:00+00:00"),
        zaczepienie("obserwacja", "adapierwsza", "2026-08-30T09:30:00+00:00"),
        zaczepienie("obserwacja", "nikt-taki", "2026-08-30T10:00:00+00:00"),
    ])
    obs4 = wzajemnosc.odwzajemnienie()["obserwacja"]
    print("    pewne=%d niepewne=%d bez=%d odsetek=%s"
          % (len(obs4["pewne"]), len(obs4["niepewne"]), len(obs4["bez"]),
             obs4["odsetek"]))
    sprawdz("trafienie po uchwycie idzie do „na pewno\"",
            [t["komu"] for t in obs4["pewne"]] == ["czyt01"], obs4["pewne"])
    sprawdz("trafienie po nazwie wyswietlanej idzie do „niepewne\"",
            [t["komu"] for t in obs4["niepewne"]] == ["adapierwsza"],
            obs4["niepewne"])
    # SAMO TRAFIENIE W NAZWE TO JESZCZE NIE ODWZAJEMNIENIE. Obie te obserwacje
    # sa z 30 sierpnia, a `czyt01` jest w zrzucie ZEROWYM z 31 sierpnia — czyli
    # mogl byc naszym czytelnikiem na dlugo przed zaczepieniem i historia
    # zrzutow tego nie rozstrzyga. Do 1 wrzesnia 2026 wychodzil stad odsetek
    # 1/3; dzis oba trafienia sa NIEORZEKALNE i wypadaja z mianownika, wiec
    # zostaje jedna orzekalna proba („nikt-taki", ktory nie jest czytelnikiem)
    # i 0 odwzajemnien z 1. Kolejnosc ma wlasny test:
    # tests/test_kolejnosc_odwzajemnienia.py.
    sprawdz("odwzajemnienie wymaga KOLEJNOSCI, nie tylko nazwy (0 z 1)",
            (len(obs4["odwzajemnili"]), obs4["orzekalnych"],
             obs4["odsetek"]) == (0, 1, 0.0),
            (obs4["odwzajemnili"], obs4["orzekalnych"], obs4["odsetek"]))
    sprawdz("oba trafienia sa nieorzekalne, bo czyt01 jest w zrzucie zerowym",
            len(obs4["nieorzekalne"]) == 2,
            [(t["komu"], t["kolejnosc"]) for t in obs4["nieorzekalne"]])

    print()
    print("=== 5. ERY KONTA SA ROZDZIELONE ===")
    zapisz(dziennik_produkcyjny())
    sub5 = wzajemnosc.odwzajemnienie()["subskrypcja"]
    obs5 = wzajemnosc.odwzajemnienie()["obserwacja"]
    print("    subskrypcje: prob %d przed / %d po; udanych %d przed / %d po"
          % (sub5["prob_przed_kotwica"], sub5["prob_od_kotwicy"],
             sub5["udane_przed_kotwica"], sub5["udane_od_kotwicy"]))
    sprawdz("subskrypcje: 7 prob sprzed 2026-08-25, 11 po",
            (sub5["prob_przed_kotwica"], sub5["prob_od_kotwicy"]) == (7, 11),
            (sub5["prob_przed_kotwica"], sub5["prob_od_kotwicy"]))
    sprawdz("subskrypcje: 4 udane sprzed, 8 po",
            (sub5["udane_przed_kotwica"], sub5["udane_od_kotwicy"]) == (4, 8),
            (sub5["udane_przed_kotwica"], sub5["udane_od_kotwicy"]))
    sprawdz("obserwacje: obie proby sprzed przestawienia na AI, ZERO po",
            (obs5["prob_przed_kotwica"], obs5["prob_od_kotwicy"]) == (2, 0),
            (obs5["prob_przed_kotwica"], obs5["prob_od_kotwicy"]))

    print()
    print("=== 6. TRZY KUPKI CZYTELNIKOW, NIE DWIE (KONTRDOWOD ODTWORZONY) ===")
    skad = wzajemnosc.skad_przyszli()
    print("    z trescia=%d  tylko pozyskanie=%d  bez sladu=%d  razem=%d"
          % (len(skad["z_trescia"]), len(skad["tylko_pozyskanie"]),
             len(skad["bez_sladu"]), skad["czytelnikow"]))
    sprawdz("wszyscy czytelnicy policzeni raz (19)",
            skad["czytelnikow"] == 19, skad["czytelnikow"])
    sprawdz("kupki sumuja sie do calosci",
            len(skad["z_trescia"]) + len(skad["tylko_pozyskanie"])
            + len(skad["bez_sladu"]) == 19)
    sprawdz("z kontaktem z TRESCIA: 4 z 19",
            len(skad["z_trescia"]) == 4, len(skad["z_trescia"]))
    sprawdz("z samym zdarzeniem pozyskania: 7 z 19",
            len(skad["tylko_pozyskanie"]) == 7, len(skad["tylko_pozyskanie"]))
    sprawdz("bez zadnego sladu: 8 z 19",
            len(skad["bez_sladu"]) == 8, len(skad["bez_sladu"]))
    sprawdz("nasze wlasne zdarzenie nie robi z nas czytelnika",
            "Your Publication" not in
            {o["uchwyt"] for o in skad["z_trescia"]})
    sprawdz("typ, ktorego nie znamy, jest WYPISANY, a nie policzony",
            skad["typy_nieznane"] == {"cos_czego_nie_znam": 1},
            skad["typy_nieznane"])
    sprawdz("osoba z samym nieznanym typem ma zostac bez sladu",
            "czyt12" in {o["uchwyt"] for o in skad["bez_sladu"]})
    sprawdz("kolejnosci nie da sie ustalic dla 16 z 19",
            skad["nierozstrzygalna_kolejnosc"] == 16,
            skad["nierozstrzygalna_kolejnosc"])


    def naiwnie():
        """REGULA SPRZED POPRAWKI: kazdy `skutek` z pasujaca nazwa to slad.

        Ta wersja nie odrozniala powiadomienia „ktos cie zaobserwowal" od
        polubienia — i to jest cala roznica miedzy 11 z 19 a 4 z 19.
        """
        wpisy = [json.loads(l) for l in
                 (KAT / "dziennik.jsonl").read_text(encoding="utf-8").splitlines()
                 if l.strip()]
        nazwy = set()
        for w in wpisy:
            if w.get("rodzaj") == "skutek":
                nazwy.update(str(k).lower() for k in (w.get("kto") or []))
        ludzie = wzajemnosc.czytelnicy()
        return sum(1 for wpis in ludzie.values()
                   if {str(n).lower() for n in wpis["nazwy"]} & nazwy)

    stara_liczba = naiwnie()
    print("    STARA REGULA: %d z 19    NOWA REGULA: %d z 19"
          % (stara_liczba, len(skad["z_trescia"])))
    # 12 = 4 z prawdziwym kontaktem + 7 z samym pozyskaniem + 1 z typem,
    # ktorego nikt nie zna. Na produkcji ta sama regula dawala 11, bo zadnego
    # nieznanego typu tam nie bylo — atrapa dodaje go celowo, zeby pokazac,    # ze naiwna regula przecieka DWOMA dziurami, nie jedna.
    sprawdz("KONTRDOWOD: naiwna regula daje 12 z 19 (4+7+1)",
            stara_liczba == 12, stara_liczba)
    sprawdz("KONTRDOWOD: w tym 7 osob, ktorych jedynym sladem jest samo"
            " pozyskanie",
            stara_liczba - len(skad["z_trescia"]) - 1
            == len(skad["tylko_pozyskanie"]),
            (stara_liczba, len(skad["tylko_pozyskanie"])))
    sprawdz("KONTRDOWOD: i jest to INNA liczba niz nowa (12 wobec 4)",
            stara_liczba != len(skad["z_trescia"]),
            (stara_liczba, len(skad["z_trescia"])))

    print()
    print("=== 7. CZAS ODZEWU: PROBKA ZA MALA MA BYC NAZWANA ===")
    op = wzajemnosc.opoznienia()
    print("    %s" % {r: (d["n"], round(d["mediana_h"], 1),
                          d["wystarczy_na_wniosek"])
                      for r, d in sorted(op["na_tresc"].items())})
    sprawdz("reakcje na notki policzone (12, prog %d)" % op["min_probka"],
            op["na_tresc"]["notka"]["n"] == 12, op["na_tresc"].get("notka"))
    sprawdz("przy 12 obserwacjach wniosek wolno wyciagnac",
            op["na_tresc"]["notka"]["wystarczy_na_wniosek"] is True)
    sprawdz("przy 3 obserwacjach na komentarzach — NIE wolno",
            op["na_tresc"]["komentarz"]["n"] == 3
            and op["na_tresc"]["komentarz"]["wystarczy_na_wniosek"] is False,
            op["na_tresc"].get("komentarz"))
    sprawdz("mediana odzewu na notke liczona z godzin (2 h)",
            abs(op["na_tresc"]["notka"]["mediana_h"] - 2.0) < 1e-6,
            op["na_tresc"]["notka"]["mediana_h"])
    sprawdz("zero pozyskan z zaczepien — nie ma czego usredniac",
            op["na_zaczepienie"]["n"] == 0, op["na_zaczepienie"])

    print()
    print("=== 8. KANAL PRZYPISUJEMY TYLKO DATOWALNYM ===")
    kan = wzajemnosc.kanaly()
    print("    datowalnych %d z %d, kanaly %s"
          % (kan["datowalnych"], kan["wszystkich_czytelnikow"], kan["osobowo"]))
    sprawdz("datowalni to tylko ci, ktorzy doszli po pierwszym zrzucie (3 z 19)",
            (kan["datowalnych"], kan["wszystkich_czytelnikow"]) == (3, 19),
            (kan["datowalnych"], kan["wszystkich_czytelnikow"]))
    sprawdz("osoba z restackiem przed swoim zrzutem dostaje kanal „notka\"",
            kan["osobowo"].get("notka") == 1, kan["osobowo"])
    sprawdz("dwie osoby bez sladu zostaja „nieznany\", a nie zerem",
            kan["osobowo"].get("nieznany") == 2, kan["osobowo"])
    sprawdz("brak pliku statystyk nie wywala raportu",
            not kan["pozycyjnie"], kan["pozycyjnie"])

    print()
    print("=== 8b. LICZNIK PROFILU WOBEC IMION: MIANOWNIK BYWA ZANIZONY ===")
    # Zmierzone 1 wrzesnia na produkcji: licznik mowi 12 obserwujacych, imienna
    # lista oddaje 10. Dwoch ludzi nie da sie przypisac do niczego, bo nie
    # znamy ich nazwisk — i raport ma o tym powiedziec, zamiast liczyc
    # „z 10" tak, jakby to bylo wszystko.
    OSTATNI = ZRZUTY[-1]["kiedy"]
    zapisz(dziennik_produkcyjny(), ZRZUTY, [
        {"kiedy": OSTATNI, "obserwujacy": 13, "subskrybenci": 8}])
    pok = wzajemnosc.pokrycie()
    print("    %s" % {k: v for k, v in pok.items() if k != "ostatnia"})
    sprawdz("para pomiarow z tej samej chwili zostala zestawiona",
            pok["par"] == 1, pok["par"])
    sprawdz("licznik 13 wobec 11 imion -> brakuje 2 obserwujacych",
            pok["brakuje_obserwujacych"] == 2, pok["brakuje_obserwujacych"])
    sprawdz("licznik 8 wobec 8 imion -> subskrybenci pokryci w calosci",
            pok["brakuje_subskrybentow"] == 0, pok["brakuje_subskrybentow"])
    sprawdz("naglowek codziennej kontroli krzyczy o niepelnej liscie",
            any("niepelne" in l for l in wzajemnosc.naglowek()),
            wzajemnosc.naglowek())

    # Zapis licznika sprzed doby to INNY przebieg i nie wolno go zestawiac
    # z dzisiejszym zrzutem imiennym — inaczej „brakuje 5" znaczyloby tylko
    # tyle, ze konto uroslo od wczoraj.
    zapisz(dziennik_produkcyjny(), ZRZUTY, [
        {"kiedy": "2026-08-30T00:13:04+00:00", "obserwujacy": 13,
         "subskrybenci": 8}])
    sprawdz("licznik sprzed doby NIE jest parowany z dzisiejszym zrzutem",
            wzajemnosc.pokrycie()["par"] == 0, wzajemnosc.pokrycie())
    zapisz(dziennik_produkcyjny(), ZRZUTY, None)
    sprawdz("brak pliku wzrostu nie wywala raportu",
            wzajemnosc.pokrycie()["par"] == 0
            and len(wzajemnosc.raport()) > 10)

    print()
    print("=== 9. KONTROLA SLEPOTY POMIARU ===")
    swiezy = [{"kiedy": (datetime.now(timezone.utc)
                         - timedelta(hours=6)).isoformat(timespec="seconds"),
               "obserwujacy": _os(["czyt01"]), "subskrybenci": []}]
    zapisz(dziennik_produkcyjny(), swiezy)
    sprawdz("swiezy zrzut nie alarmuje", wzajemnosc.pomiar_oslepl() is None,
            wzajemnosc.pomiar_oslepl())
    stary = [{"kiedy": (datetime.now(timezone.utc)
                        - timedelta(days=wzajemnosc.ZRZUT_STARSZY_NIZ_DNI + 7))
              .isoformat(timespec="seconds"),
              "obserwujacy": _os(["czyt01"]), "subskrybenci": []}]
    zapisz(dziennik_produkcyjny(), stary)
    komunikat = wzajemnosc.pomiar_oslepl()
    sprawdz("zrzut sprzed %d dni alarmuje"
            % (wzajemnosc.ZRZUT_STARSZY_NIZ_DNI + 7), bool(komunikat), komunikat)
    (KAT / "czytelnicy.jsonl").unlink()
    sprawdz("brak pliku alarmuje", bool(wzajemnosc.pomiar_oslepl()))
    sprawdz("alarm.py pyta o to samo, co modul",
            alarm.pomiar_wzajemnosci() == wzajemnosc.pomiar_oslepl())

    print()
    print("=== 10. RAPORT BEZ DANYCH MOWI „BRAK POMIARU\", A NIE ZERA ===")
    tekst_pusty = "\n".join(wzajemnosc.raport())
    sprawdz("bez pliku czytelnikow raport nie podaje ZADNEGO procentu",
            "%" not in tekst_pusty, tekst_pusty[-300:])
    sprawdz("i nazywa to brakiem pomiaru",
            "brak pomiaru" in tekst_pusty, tekst_pusty[-300:])

    print()
    print("=== 11. KONTRDOWOD PRZYPIETY DO 6ed4e7d (NIE DO HEAD) ===")
    # Sprawdzian jest behawioralny: uchwyt `czyt01` wystepuje WYLACZNIE
    # w `czytelnicy.jsonl`. Jesli pojawi sie w wydruku, znaczy to, ze ta wersja
    # ten plik OTWORZYLA. Wersja z 6ed4e7d nie otwierala go nigdy.
    zapisz(dziennik_produkcyjny())
    SHA = "6ed4e7d"
    stare_zrodlo = subprocess.run(
        ["git", "show", "%s:agent-v2/alarm.py" % SHA],
        capture_output=True, cwd=".").stdout.decode("utf-8")
    sprawdz("wersja odniesienia %s daje sie wyciagnac z gita" % SHA,
            len(stare_zrodlo) > 1000, len(stare_zrodlo))
    sprawdz("i jest to INNY plik niz dzisiejszy (jest co porownywac)",
            stare_zrodlo != pathlib.Path("agent-v2/alarm.py").read_text(
                encoding="utf-8"))

    stary_modul = types.ModuleType("alarm_%s" % SHA)
    stary_modul.__dict__["__file__"] = "agent-v2/alarm.py"
    exec(compile(stare_zrodlo, "agent-v2/alarm.py(%s)" % SHA, "exec"),
         stary_modul.__dict__)
    stary_modul._polaczenie = baza_w_pamieci

    def wydruk_przegladu(modul):
        bufor = io.StringIO()
        with contextlib.redirect_stdout(bufor):
            # `dni=1` CELOWO: caly dziennik atrapy jest starszy, wiec stare
            # sekcje sa puste, a wzajemnosc i tak liczy sie z calej historii.
            # Dzieki temu test nie zalezy od dzisiejszej daty.
            modul.przeglad(dni=1)
        return bufor.getvalue()

    tekst_stary = wydruk_przegladu(stary_modul)
    tekst_nowy = wydruk_przegladu(alarm)
    sprawdz("KONTRDOWOD: %s nie wypisuje ANI JEDNEGO czytelnika" % SHA,
            "czyt01" not in tekst_stary, tekst_stary[-400:])
    sprawdz("KONTRDOWOD: %s nie odpowiada, ilu z 12 sie odwzajemnilo" % SHA,
            "0 z 12" not in tekst_stary, tekst_stary[-400:])
    sprawdz("nowa wersja czyta liste czytelnikow", "czyt01" in tekst_nowy,
            tekst_nowy[-600:])
    sprawdz("nowa wersja podaje odwzajemnienia z mianownikiem",
            "0 z 12" in tekst_nowy, tekst_nowy[-900:])
    sprawdz("nowa wersja nie nazywa braku prob zerem procent",
            "ANI JEDNEJ udanej proby" in tekst_nowy, tekst_nowy[:900])

    print()
    print("=== 12. WZAJEMNOSC JEST W SCIEZCE Z ZEGARA, NIE TYLKO W PRZEGLADZIE ===")
    # `nia-alarm.timer` odpala `python agent-v2/alarm.py` BEZ ARGUMENTOW, czyli
    # `sprawdz_wszystko`. `przeglad` i `norma.py` nie chodza z zadnego zegara —
    # ich wynik czyta wylacznie czlowiek, ktory sam po niego siegnie.
    wyslane = []
    oryg_wyslij = alarm.wyslij
    alarm.wyslij = lambda k, t, tr: wyslane.append(k) or True
    try:
        bufor = io.StringIO()
        with contextlib.redirect_stdout(bufor):
            alarm.sprawdz_wszystko()
        tekst_kontroli = bufor.getvalue()
    finally:
        alarm.wyslij = oryg_wyslij
    sprawdz("codzienna kontrola wypisuje liczby wzajemnosci",
            "czytelnicy" in tekst_kontroli and "19 osob" in tekst_kontroli,
            tekst_kontroli[:900])
    sprawdz("i nazywa brak prob obserwacji brakiem pomiaru",
            "ANI JEDNEJ UDANEJ PROBY" in tekst_kontroli, tekst_kontroli[:900])
    sprawdz("kontrola slepoty pomiaru jest na liscie kontroli",
            "pomiar-wzajemnosci" in tekst_kontroli, tekst_kontroli[-900:])
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
