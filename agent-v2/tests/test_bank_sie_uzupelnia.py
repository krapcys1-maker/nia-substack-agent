# -*- coding: utf-8 -*-
"""Bank tematow dobiera sie sam, ze swiezych naglowkow — zanim notki i artykul go wyczerpia.

## Pomiar, ktory to wywolal

Serwer, 14 wrzesnia 2026, dzien przed artykulem: 25 wpisow w banku, 4 wolne,
1 oznaczony na artykul. Ostatnie dopisanie 11 wrzesnia. `znajdz_ciekawostki`
wolala tylko stara sciezka notek (konto od 7 wrzesnia pisze persona) i artykul
— przy CALKIEM pustym banku. Notki persony z banku biora, wpis wygasa po
`BANK_MAKS_DNI`, wiec zapas mogl tylko malec. W logu kazdego przebiegu notek:
„wolnych 4, zostawiam 3, biore 1".

Tego samego dnia korpus kanalow mial 398 wpisow z 19 kanalow, 115 z ostatniego
tygodnia — a do promptu szly w kolejnosci korpusu, z oknem czternastu dni.

## Co ten test sprawdza

1. `zapas_banku` liczy tylko to, co da sie wziac, i NICZEGO nie zapisuje;
2. `uzupelnij_bank` szuka, gdy zapas ponizej celu (wolnych albo na artykul),
   i nie szuka, gdy jest w porzadku; sortuje bank tylko po nowym materiale;
   awaria sedziego nie wywraca bloku; nie wola `wez_kandydatow`;
3. naglowki z kanalow ida od najswiezszych, a szukanie tematow bierze okno
   `KANALY_DNI_DLA_BANKU`;
4. blok `bank` stoi w dniu miedzy odpowiedziami a notkami i nie placi w probie
   suchej.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_bank_sie_uzupelnia.py
"""
import ast
import io
import json
import pathlib
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "agent-v2")
import config   # noqa: E402
import stages   # noqa: E402

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
TERAZ = datetime.now(timezone.utc)


def wpis(status="nowy", na_artykul=False, dni_temu=1, wazny_dni=6):
    return {"fact": "fakt %s" % len(str(dni_temu)), "status": status, "na_artykul": na_artykul,
            "kiedy": (TERAZ - timedelta(days=dni_temu)).isoformat(timespec="seconds"),
            "wazny_do": (TERAZ + timedelta(days=wazny_dni)).strftime("%Y-%m-%d %H:%M")}


def ustaw_bank(wpisy):
    stages.INDEKS_KANDYDATOW.write_text(json.dumps(wpisy, ensure_ascii=False), encoding="utf-8")


ORYG = (stages.INDEKS_KANDYDATOW, stages.znajdz_ciekawostki, stages.posortuj_bank,
        stages.wez_kandydatow, config.BANK_CEL_WOLNYCH, config.BANK_CEL_NA_ARTYKUL,
        config.DATA_PRZESTAWIENIA)
wolania = {"szukanie": 0, "sedzia": 0}

try:
    stages.INDEKS_KANDYDATOW = KAT / "indeks_kandydatow.json"
    config.DATA_PRZESTAWIENIA = ""
    config.BANK_CEL_WOLNYCH = 12
    config.BANK_CEL_NA_ARTYKUL = 2

    def nie_wolno(*a, **k):
        raise AssertionError("uzupelnianie banku nie moze wyjmowac kandydatow")
    stages.wez_kandydatow = nie_wolno

    print("=== 1. ZAPAS LICZY TYLKO TO, CO DA SIE WZIAC, I NICZEGO NIE ZAPISUJE ===")
    ustaw_bank([wpis(), wpis(na_artykul=True), wpis(status="uzyty"),
                wpis(status="odrzucony"), wpis(wazny_dni=-1)])
    przed = stages.INDEKS_KANDYDATOW.read_bytes()
    z = stages.zapas_banku()
    sprawdz("wolne w terminie: 2 (uzyty, odrzucony i po terminie sie nie licza)",
            z["wolnych"] == 2, z)
    sprawdz("na artykul: 1", z["na_artykul"] == 1, z)
    sprawdz("plik banku nietkniety", stages.INDEKS_KANDYDATOW.read_bytes() == przed)

    print()
    print("=== 2. SZUKA PONIZEJ CELU, NIE SZUKA POWYZEJ ===")

    def swiat(znalezione=("nowy fakt",), sedzia_pada=False, po_szukaniu=None):
        wolania.update(szukanie=0, sedzia=0)

        def szukaj(conn, run_id, *a, **k):
            wolania["szukanie"] += 1
            if po_szukaniu is not None:
                ustaw_bank(po_szukaniu)
            return [{"fact": f} for f in znalezione]

        def sedzia(conn, run_id=None, *a, **k):
            wolania["sedzia"] += 1
            if sedzia_pada:
                raise RuntimeError("sedzia padl")
            return {"ocenione": 1, "wyrzucone": 0}
        stages.znajdz_ciekawostki = szukaj
        stages.posortuj_bank = sedzia

    ustaw_bank([wpis() for _ in range(10)] + [wpis(na_artykul=True) for _ in range(2)])
    swiat()
    w = stages.uzupelnij_bank(None, None)
    sprawdz("12 wolnych, 2 na artykul: nie szuka", wolania["szukanie"] == 0 and w["dobrane"] == 0, (wolania, w))

    ustaw_bank([wpis() for _ in range(3)] + [wpis(na_artykul=True)])
    swiat(po_szukaniu=[wpis() for _ in range(9)] + [wpis(na_artykul=True) for _ in range(3)])
    w = stages.uzupelnij_bank(None, None)
    sprawdz("4 wolne (stan z serwera): szuka raz", wolania["szukanie"] == 1, wolania)
    sprawdz("i sortuje bank po nowym materiale", wolania["sedzia"] == 1, wolania)
    sprawdz("wynik mowi, ile jest po dobraniu", w["wolnych"] == 12 and w["na_artykul"] == 3 and w["dobrane"] == 1, w)

    ustaw_bank([wpis() for _ in range(14)] + [wpis(na_artykul=True)])
    swiat()
    stages.uzupelnij_bank(None, None)
    sprawdz("dosc wolnych, ale jeden na artykul: szuka", wolania["szukanie"] == 1, wolania)

    ustaw_bank([wpis()])
    swiat(znalezione=())
    w = stages.uzupelnij_bank(None, None)
    sprawdz("szukanie nic nie dalo (limit dobowy): bez sedziego", wolania["sedzia"] == 0 and w["dobrane"] == 0, (wolania, w))

    ustaw_bank([wpis()])
    swiat(sedzia_pada=True)
    try:
        w = stages.uzupelnij_bank(None, None)
        sprawdz("sedzia padl: blok nie wywraca przebiegu", w["dobrane"] == 1, w)
    except Exception as exc:
        sprawdz("sedzia padl: blok nie wywraca przebiegu", False, exc)
finally:
    (stages.INDEKS_KANDYDATOW, stages.znajdz_ciekawostki, stages.posortuj_bank,
     stages.wez_kandydatow, config.BANK_CEL_WOLNYCH, config.BANK_CEL_NA_ARTYKUL,
     config.DATA_PRZESTAWIENIA) = ORYG

print()
print("=== 3. NAGLOWKI OD NAJSWIEZSZYCH, OKNO TYGODNIA DLA BANKU ===")


def d(dni):
    return (TERAZ - timedelta(days=dni)).date().isoformat()


KORPUS = [
    {"kanal": "Stary kanal", "temat": "AI agent story from long ago", "data": d(12), "url": "https://a/1", "skrot": "s"},
    {"kanal": "Stary kanal", "temat": "AI agent story older", "data": d(10), "url": "https://a/2", "skrot": "s"},
    {"kanal": "Kanal B", "temat": "AI model launch last week", "data": d(5), "url": "https://b/1", "skrot": "s"},
    {"kanal": "Kanal B", "temat": "AI model pricing yesterday", "data": d(1), "url": "https://b/2", "skrot": "s"},
    {"kanal": "Kanal C", "temat": "AI agent benchmark today", "data": d(0), "url": "https://c/1", "skrot": "s"},
    {"kanal": "Kanal C", "temat": "AI lab paper three days ago", "data": d(3), "url": "https://c/2", "skrot": "s"},
]
import korpus_kanalow  # noqa: E402
import personality     # noqa: E402

ORYG2 = (korpus_kanalow.korpus_kanalow, config.PERSONA_WLACZONA, config.ZNAKI_NISZY, personality._injection)
try:
    korpus_kanalow.korpus_kanalow = lambda ile=26, **k: [dict(w) for w in KORPUS]
    config.PERSONA_WLACZONA = True
    config.ZNAKI_NISZY = ("ai",)
    personality._injection = lambda tekst: False
    tekst = stages.zaczyn_z_kanalow(ile=6, max_dni=14)
    daty = [l.split("]")[0].split("[")[-1] for l in tekst.splitlines() if l.startswith("- [")]
    sprawdz("pierwszy naglowek to dzisiejszy", daty[:1] == [d(0)], daty)
    sprawdz("kazdy kanal oddaje najpierw swoj najswiezszy",
            daty[:3] == [d(0), d(1), d(10)], daty)
    # KONTRDOWOD: stara kolejnosc (korpus) dawala na poczatku wpis sprzed 12 dni.
    sprawdz("KONTRDOWOD: korpus zaczyna sie od wpisu sprzed 12 dni", KORPUS[0]["data"] == d(12))
    tydzien = stages.zaczyn_z_kanalow(ile=6, max_dni=config.KANALY_DNI_DLA_BANKU)
    sprawdz("okno tygodnia wycina wpisy sprzed 10 i 12 dni",
            d(12) not in tydzien and d(10) not in tydzien and d(5) in tydzien, tydzien)
finally:
    (korpus_kanalow.korpus_kanalow, config.PERSONA_WLACZONA, config.ZNAKI_NISZY, personality._injection) = ORYG2

ZR = io.open("agent-v2/stages.py", encoding="utf-8").read()
cialo = ZR[ZR.find("\ndef znajdz_ciekawostki("):ZR.find("\ndef ", ZR.find("\ndef znajdz_ciekawostki(") + 1)]
sprawdz("szukanie tematow bierze naglowki z okna `KANALY_DNI_DLA_BANKU`",
        "max_dni=config.KANALY_DNI_DLA_BANKU" in cialo)

print()
print("=== 4. BLOK W DNIU ===")
RUN = io.open("agent-v2/run.py", encoding="utf-8").read()
DZIEN = ""
for w in ast.walk(ast.parse(RUN)):
    if isinstance(w, ast.FunctionDef) and w.name == "dzien":
        DZIEN = ast.get_source_segment(RUN, w) or ""
sprawdz("blok bank miedzy odpowiedziami a notkami",
        '("odpowiedzi", odpowiedzi), ("bank", bank),' in DZIEN
        and DZIEN.find('("bank", bank)') < DZIEN.find('("notki", notki)'))
blok = DZIEN[DZIEN.find("def bank() -> None:"):DZIEN.find("for nazwa, robota in")]
sprawdz("proba sucha nie placi za szukanie",
        "if not wyslij:" in blok and blok.find("if not wyslij:") < blok.find("uzupelnij_bank("), blok[:300])

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
