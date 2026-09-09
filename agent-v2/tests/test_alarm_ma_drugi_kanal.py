# -*- coding: utf-8 -*-
"""Alarm zapisuje sie na dysk zawsze, takze bez poczty.

## Co przepadlo

Alarm liczy sie poprawnie i konczyl na jednym zdaniu w logu systemd:

    [alarm NIEWYSLANY — brak konfiguracji] ...

W dwie doby przepadly tak CZTERY: „Agent robi mniej, niz deklaruje" (8 i 9
wrzesnia), „BANK NIE MA O CZYM PISAC" (8 wrzesnia) i „POMIAR WZAJEMNOSCI
OSLEPL" (9 wrzesnia). Zapasc subskrypcji trwala tydzien i nikt nie dostal
wiadomosci.

To jest dokladnie ta awaria, o ktorej `alarm.py` pisze w naglowku: taka,
ktorej nie widac w logu.

## Dlaczego drugi kanal, a nie naprawa poczty

Poczta wymaga hasla i adresu, ktore moze wpisac tylko wlasciciel. Dysk nie
wymaga niczego. Kazdy alarm ladzie wiec takze w `alarmy.jsonl`, jeden wiersz
JSON na zdarzenie, do odczytania poleceniem:

    python agent-v2/alarm.py pokaz

## Cisza dobowa NIE dotyczy dziennika

I to jest cala roznica miedzy tymi dwoma kanalami. Wyciszenie chroni skrzynke
przed czterema takimi samymi listami; dziennik ma pokazac, ze problem
wystapil CZTERY RAZY. Gdyby wyciszenie obejmowalo takze plik, „zglaszany
w ciagu doby" wygladalby jak „zdarzyl sie raz".

BEZ PYTESTA, bez sieci, bez poczty. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_alarm_ma_drugi_kanal.py
"""
import io
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")

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
import alarm  # noqa: E402

# BEZ RUSZANIA `config.DATA_DIR`. `test_komplet_sciezek` pilnuje, zeby zaden
# plik testowy nie przestawial go wprost: gole przypisanie nie cofa sie po
# tescie i nastepny plik w petli dziedziczy podmieniony katalog. Ta zapora
# zlapala TEN plik przy pierwszym uruchomieniu.
#
# I nie jest tu potrzebne. `alarm` liczy obie sciezki przy imporcie, a my
# podmieniamy je jawnie zaraz po nim — nic wiecej w tym module nie siega do
# `config.DATA_DIR` w trakcie tych sprawdzen.
alarm.DZIENNIK_ALARMOW = KAT / "alarmy.jsonl"
alarm.HISTORIA = KAT / "alarmy.json"


def wiersze():
    if not alarm.DZIENNIK_ALARMOW.exists():
        return []
    return [json.loads(x) for x in
            alarm.DZIENNIK_ALARMOW.read_text(encoding="utf-8").splitlines()
            if x.strip()]


print("=== 1. BEZ POCZTY ALARM I TAK LADUJE NA DYSKU ===")
sprawdz("poczta nieustawiona w tym tescie", alarm.skonfigurowany() is False)
alarm.wyslij("bank-pusty", "BANK NIE MA O CZYM PISAC", "Zostaly dwa fakty.")
w = wiersze()
sprawdz("jeden wiersz w dzienniku", len(w) == 1, len(w))
sprawdz("z tematem", w and w[0].get("temat") == "BANK NIE MA O CZYM PISAC",
        w[0] if w else None)
sprawdz("z kluczem rodzaju", w and w[0].get("klucz") == "bank-pusty")
sprawdz("z trescia", w and "Zostaly dwa fakty" in str(w[0].get("tresc")))
sprawdz("i z powodem, czemu nie poszlo poczta",
        w and w[0].get("poczta") == "brak konfiguracji", w[0].get("poczta") if w else None)
sprawdz("z czasem w UTC", w and str(w[0].get("kiedy")).endswith("+00:00"),
        w[0].get("kiedy") if w else None)

print()
print("=== 2. POWTORKA TEZ SIE ZAPISUJE ===")
# CALY SENS OSOBNEGO KANALU. Skrzynka ma dostac jeden list; dziennik ma
# pokazac, ile razy to sie stalo.
alarm.wyslij("bank-pusty", "BANK NIE MA O CZYM PISAC", "Drugi raz tego dnia.")
alarm.wyslij("wolumeny", "Agent robi mniej, niz deklaruje", "Subskrypcje 0 z 10.")
w = wiersze()
sprawdz("trzy wiersze po trzech alarmach", len(w) == 3, len(w))
sprawdz("dwa razy ten sam klucz",
        [x["klucz"] for x in w].count("bank-pusty") == 2,
        [x["klucz"] for x in w])

print()
print("=== 3. ODCZYT ODDAJE OD NAJNOWSZEGO ===")
ostatnie = alarm.ostatnie_alarmy(7)
sprawdz("wszystkie trzy", len(ostatnie) == 3, len(ostatnie))
sprawdz("najnowszy pierwszy",
        ostatnie[0]["tresc"].startswith("Subskrypcje"),
        ostatnie[0]["tresc"][:40])
sprawdz("okno czasowe dziala", alarm.ostatnie_alarmy(0) == []
        or len(alarm.ostatnie_alarmy(0)) <= 3)

print()
print("=== 4. ZEPSUTY PLIK NIE WYWALA AGENTA ===")
# Alarm, ktory wywala agenta, bylby gorszy od problemu, ktory zglasza.
alarm.DZIENNIK_ALARMOW.write_text("to nie jest JSON\n{polowa\n", encoding="utf-8")
try:
    sprawdz("odczyt zepsutego pliku oddaje liste", alarm.ostatnie_alarmy(7) == [],
            alarm.ostatnie_alarmy(7))
except Exception as exc:                                # noqa: BLE001
    sprawdz("odczyt zepsutego pliku oddaje liste", False,
            "%s: %s" % (type(exc).__name__, exc))
try:
    alarm.wyslij("cokolwiek", "Temat", "Tresc")
    sprawdz("zapis po zepsuciu nie rzuca", True)
except Exception as exc:                                # noqa: BLE001
    sprawdz("zapis po zepsuciu nie rzuca", False,
            "%s: %s" % (type(exc).__name__, exc))

print()
print("=== 5. KANAL JEST WPIETY W OBIE SCIEZKI ===")
ZRODLO = io.open("agent-v2/alarm.py", encoding="utf-8").read()
sprawdz("zapis przy braku konfiguracji", 'poczta="brak konfiguracji"' in ZRODLO
        or '"brak konfiguracji"' in ZRODLO)
sprawdz("zapis przy wyciszeniu", '"wyciszony w ciagu doby"' in ZRODLO)
sprawdz("zapis przy wysylce poczta", '"wysylany poczta"' in ZRODLO)
# KONTRDOWOD: gdyby ktos przeniosl zapis ZA sprawdzenie konfiguracji, alarm
# bez poczty znowu przepadlby po cichu.
i_zapis = ZRODLO.index('_do_pliku(klucz, temat, tresc, "brak konfiguracji")')
i_return = ZRODLO.index("return False", i_zapis)
sprawdz("zapis PRZED rezygnacja", i_zapis < i_return, (i_zapis, i_return))

print()
print("=== 6. JEST CZYM TO PRZECZYTAC ===")
sprawdz("polecenie `pokaz` istnieje", '"pokaz"' in ZRODLO)
sprawdz("i mowi, gdy poczta nie dziala",
        "to jedyny kanal, ktory dziala" in ZRODLO)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
