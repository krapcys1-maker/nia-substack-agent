# -*- coding: utf-8 -*-
"""Jednostki systemd musza dac sie ustawic pod cudza instalacje.

## Po co ten plik istnieje

`agent-v2/systemd/*.service` mialy wpisane na sztywno trzy rzeczy nalezace do
INSTALACJI, nie do bota: katalog (`/home/ubuntu/...`, w trzech plikach po dwa
razy), uzytkownika (`User=ubuntu`) i marke w `Description=`. Konfigurator pytal
o nazwe marki i nic z nia tutaj nie robil — czyli konto skonfigurowane wlasna
nazwa dostawalo szesc plikow, ktore albo nie startuja, albo w `systemctl
status` przedstawiaja sie cudza nazwa.

Ta sama klasa, co `FETCH_USER_AGENT` przed poprawka: wartosc z konfiguracji,
ktora nie dochodzi tam, gdzie jest widoczna na zewnatrz. Roznica jest taka, ze
`.service` nie jest ani kodem, ani dokumentacja, wiec zaden skan po tych
katalogach nie chodzil.

## Czego pilnuje

1. WSZYSTKIE SZESC JEDNOSTEK MA `Description=MARKA — rola`. To nie jest
   kosmetyka: podstawianie marki bierze czesc przed „ — ", wiec jednostka
   o innym ksztalcie po cichu zachowalaby stara nazwe. Trzy z szesciu mialy
   wlasnie taki inny ksztalt („Zegar agenta NIA").
2. SZABLONY SA SPOJNE: jeden katalog instalacji i jeden uzytkownik we
   wszystkich uslugach. Dwa rozne katalogi znaczylyby, ze ktos poprawil jeden
   plik z trzech, a podstawianie napisu przemilczaloby reszte.
3. PO PODSTAWIENIU NIE ZOSTAJE ANI JEDEN SLAD STAREJ INSTALACJI — ani katalogu,
   ani uzytkownika, ani domyslnej marki. Sprawdzane na wartosciach, ktorych
   w repozytorium nie ma nigdzie indziej.
4. KATALOG PODSTAWIA SIE TAKZE W `ExecStart`. Rozjazd miedzy `WorkingDirectory`
   a `ExecStart` daje usluge, ktora startuje w dobrym katalogu i wola
   nieistniejacego Pythona — a `systemctl status` pokazuje wtedy blad
   o Pythonie, nie o konfiguracji.
5. KONTRDOWOD: bez podstawienia te same asercje oblewaja. Bez tego caly plik
   przechodzilby takze wtedy, gdyby `podstaw()` zwracalo wejscie bez zmian.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_jednostki_dla_instalacji.py
"""
import pathlib
import sys

sys.path.insert(0, "narzedzia")
import jednostki  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# Wartosci, ktorych w repozytorium nie ma nigdzie indziej — zeby „nie zostal
# slad" znaczylo naprawde to, a nie „przypadkiem sie nie trafilo".
KATALOG = "/opt/probny-katalog-instalacji"
UZYTKOWNIK = "probnyuzytkownik"
MARKA = "Probna Marka Jednostkowa"

KAT = pathlib.Path("agent-v2/systemd")

print("=== 1. KAZDA JEDNOSTKA MA OPIS W KSZTALCIE `MARKA — rola` ===")
pliki = sorted(p for p in KAT.iterdir()
               if p.suffix in (".service", ".timer") and p.is_file())
sprawdz("jednostki w ogole sa", len(pliki) >= 6, len(pliki))
for p in pliki:
    opisy = [w for w in p.read_text(encoding="utf-8").splitlines()
             if w.startswith("Description=")]
    sprawdz("%s ma dokladnie jeden Description" % p.name, len(opisy) == 1, opisy)
    if opisy:
        sprawdz("%s: opis ma ksztalt `MARKA — rola`" % p.name,
                " — " in opisy[0], opisy[0])

print()
print("=== 2. SZABLONY SA SPOJNE ===")
katalogi, uzytkownicy = set(), set()
for p in sorted(KAT.glob("*.service")):
    tresc = p.read_text(encoding="utf-8")
    k = jednostki._wartosc(tresc, "WorkingDirectory")
    u = jednostki._wartosc(tresc, "User")
    if k:
        katalogi.add(k)
    if u:
        uzytkownicy.add(u)
sprawdz("jeden katalog instalacji we wszystkich uslugach",
        len(katalogi) == 1, sorted(katalogi))
sprawdz("jeden uzytkownik we wszystkich uslugach",
        len(uzytkownicy) == 1, sorted(uzytkownicy))

print()
print("=== 3. PO PODSTAWIENIU NIE ZOSTAJE SLAD STAREJ INSTALACJI ===")
stary_katalog = jednostki.katalog_szablonu()
stary_uzytkownik = jednostki.uzytkownik_szablonu()
zbudowane = jednostki.zbuduj(KATALOG, UZYTKOWNIK, MARKA)
sprawdz("zbudowano tyle samo plikow, co szablonow",
        len(zbudowane) == len(pliki), (len(zbudowane), len(pliki)))
for nazwa, tresc in sorted(zbudowane.items()):
    sprawdz("%s: nie ma starego katalogu" % nazwa,
            stary_katalog not in tresc, stary_katalog)
    sprawdz("%s: nie ma starego uzytkownika" % nazwa,
            ("User=" + stary_uzytkownik) not in tresc, stary_uzytkownik)
    sprawdz("%s: nie ma domyslnej marki" % nazwa,
            "Your Publication" not in tresc)
    sprawdz("%s: niesie nowa marke" % nazwa, MARKA in tresc)

print()
print("=== 4. KATALOG PODSTAWIA SIE TAKZE W ExecStart ===")
# To jest ten sam blad, co dwie kopie jednej wartosci: `WorkingDirectory`
# poprawiony, `ExecStart` nie — usluga startuje w dobrym katalogu i wola
# nieistniejacego Pythona.
for nazwa, tresc in sorted(zbudowane.items()):
    if not nazwa.endswith(".service"):
        continue
    exec_linie = [w for w in tresc.splitlines() if w.startswith("ExecStart=")]
    sprawdz("%s ma ExecStart" % nazwa, len(exec_linie) == 1, exec_linie)
    for w in exec_linie:
        sprawdz("%s: ExecStart wskazuje nowy katalog" % nazwa,
                w.startswith("ExecStart=" + KATALOG + "/"), w[:80])
    sprawdz("%s: WorkingDirectory zgadza sie z ExecStart" % nazwa,
            jednostki._wartosc(tresc, "WorkingDirectory") == KATALOG,
            jednostki._wartosc(tresc, "WorkingDirectory"))

print()
print("=== 5. KONTRDOWOD: BEZ PODSTAWIENIA TE ASERCJE OBLEWAJA ===")
# Bez tego caly plik przechodzilby takze wtedy, gdyby `podstaw()` oddawalo
# wejscie nietkniete — a wtedy nie mierzylby niczego.
bez_zmian = jednostki.zbuduj(stary_katalog, stary_uzytkownik, "")
_zostal_katalog = any(stary_katalog in t for t in bez_zmian.values())
_zostala_marka = any("Your Publication" in t for t in bez_zmian.values())
sprawdz("przy tych samych wartosciach stary katalog ZOSTAJE", _zostal_katalog)
sprawdz("i domyslna marka ZOSTAJE", _zostala_marka)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
