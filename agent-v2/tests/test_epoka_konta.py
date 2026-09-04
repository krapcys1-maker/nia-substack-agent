# -*- coding: utf-8 -*-
"""Data zmiany tematu konta: jedno zrodlo, czterech czytelnikow, pusta znaczy „nigdy".

## Po co ten plik istnieje

Ten sam dzien byl do 4 wrzesnia 2026 wpisany na sztywno w PIECIU miejscach:

    config.DATA_PRZESTAWIENIA        = "2026-08-25"
    audyt_systemu.PIVOT              = "2026-08-25"
    run.PRZESTAWIENIE_KONTA_NA_AI    = "2026-08-25"
    wzajemnosc.KOTWICA_NISZY         = "2026-08-25"
    raport_statystyk.PIVOT           = "2026-08-25"

Piec kopii jednej wartosci rozjezdza sie zawsze — a tu bylo gorzej niz zwykle
z dwoch powodow.

NAZWA TRZECIEJ NIOSLA NAZWE NISZY (`..._NA_AI`), wiec przy zmianie tematu
trzeba by bylo pamietac o zmianie NAZWY, nie tylko wartosci. Wartosc
przeniesiono do konfiguracji, a nazwe zostawiono z uzasadnieniem „czytaja ja
testy" — czyli test trzymal nazwe niszy w kodzie produkcyjnym. Dzis stala
nazywa sie `PRZESTAWIENIE_KONTA`.

PIATA PRZEZYLA POPRAWKE CZTERECH POZOSTALYCH. Nazywa sie identycznie jak
druga (`PIVOT`), a mimo to jej nie ruszono, bo lista miejsc byla WYPISANA
RECZNIE. Dlatego sekcja 5 nie ma listy: chodzi po modulach i szuka KSZTALTU
„RRRR-MM-DD" przypisanego do stalej. Szosta kopia, dopisana jutro pod dowolna
nazwa, oblewa tam sama.

Dzis wszystkie piec pochodzi z `konfiguracja.toml`, pole
`konto.data_przestawienia`.

## Dlaczego nie wystarczyly testy, ktore juz sa

Filtru po tej dacie pilnowal `test_wybor_celu.py` — i pilnuje nadal, tyle ze
w KOPII BEZ HISTORII ten plik sie nie wykonuje (patrz `tests/historia.py`).
Zmiana samej stalej przechodzila wiec „bez oblanych testow", bo zaden z nich
nie wykonal ani jednej linii. Ten plik nie zaglada do historii i chodzi
wszedzie.

## Czego pilnuje

1. PUSTA DATA ZNACZY „TO KONTO NIE ZMIENIALO TEMATU" i przepuszcza wszystko.
   To jest domyslny stan nowej instalacji i najlatwiejszy do zepsucia: gole
   porownanie `>= ""` dziala przypadkiem, wiec bledna wersja tez przechodzi
   dopoki ktos nie ustawi daty.
2. USTAWIONA DATA TNIE, i to w obie strony — z wlaczajaca granica.
3. WSZYSTKIE MIEJSCA MOWIA TO SAMO. Nie po wartosci stalej, tylko po
   zachowaniu: kazde z nich pytamy o ten sam dzien i zadamy tej samej
   odpowiedzi.
4. I ZADNE NOWE MIEJSCE NIE POWSTAJE PO CICHU — sekcja 5 skanuje moduly po
   ksztalcie daty, wiec nie trzeba pamietac o dopisaniu szostego wpisu tutaj.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_epoka_konta.py
"""
import sys

sys.path.insert(0, "agent-v2")
import config          # noqa: E402
import run             # noqa: E402
import stages          # noqa: E402
import wzajemnosc      # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


def z_data(dzien: str):
    """Ustawia date we WSZYSTKICH trzech miejscach i oddaje funkcje cofajaca.

    `run.PRZESTAWIENIE_KONTA` jest kopia zrobiona przy imporcie, wiec
    samo przestawienie `config` jej nie rusza — i to jest wlasnie ta wlasnosc,
    ktora ten plik ma trzymac pod kontrola.
    """
    stare = (config.DATA_PRZESTAWIENIA, run.PRZESTAWIENIE_KONTA,
             wzajemnosc.KOTWICA_NISZY)
    config.DATA_PRZESTAWIENIA = dzien
    run.PRZESTAWIENIE_KONTA = dzien
    wzajemnosc.KOTWICA_NISZY = dzien

    def cofnij():
        (config.DATA_PRZESTAWIENIA, run.PRZESTAWIENIE_KONTA,
         wzajemnosc.KOTWICA_NISZY) = stare
    return cofnij


print("=== 1. PUSTA DATA PRZEPUSZCZA WSZYSTKO ===")
cofnij = z_data("")
try:
    sprawdz("stages: wpis sprzed lat przechodzi",
            stages._z_obecnej_epoki({"kiedy": "2019-01-01T00:00:00+00:00"}))
    sprawdz("stages: wpis bez daty tez przechodzi",
            stages._z_obecnej_epoki({}))
    sprawdz("run: wpis sprzed lat przechodzi",
            run._po_zmianie_tematu("2019-01-01T00:00:00+00:00"))
    sprawdz("run: pusta wartosc tez przechodzi",
            run._po_zmianie_tematu(""))
    sprawdz("wzajemnosc: wpis sprzed lat przechodzi",
            wzajemnosc.po_zmianie_tematu("2019-01-01T00:00:00+00:00"))
finally:
    cofnij()

print()
print("=== 2. USTAWIONA DATA TNIE — I GRANICA JEST WLACZAJACA ===")
cofnij = z_data("2026-08-25")
try:
    for opis, dzien, ma_przejsc in (
            ("dzien przed granica", "2026-08-24T23:59:00+00:00", False),
            ("dzien granicy",       "2026-08-25T00:00:00+00:00", True),
            ("dzien po granicy",    "2026-08-26T10:00:00+00:00", True),
            ("rok wczesniej",       "2025-08-26T10:00:00+00:00", False)):
        sprawdz("stages: %-20s -> %s" % (opis, ma_przejsc),
                stages._z_obecnej_epoki({"kiedy": dzien}) is ma_przejsc, dzien)
        sprawdz("run:    %-20s -> %s" % (opis, ma_przejsc),
                run._po_zmianie_tematu(dzien) is ma_przejsc, dzien)
        sprawdz("wzaj:   %-20s -> %s" % (opis, ma_przejsc),
                wzajemnosc.po_zmianie_tematu(dzien) is ma_przejsc, dzien)

    # WPIS BEZ DATY NIE PRZECHODZI, gdy granica jest ustawiona. Cena pomylki
    # jest niesymetryczna: przepuszczony wpis z poprzedniej epoki to notka
    # o cudzym temacie, odrzucony — jeden kandydat mniej w spizarni.
    sprawdz("stages: wpis BEZ daty odpada, gdy granica stoi",
            stages._z_obecnej_epoki({}) is False)
finally:
    cofnij()

print()
print("=== 3. TRZY MIEJSCA, JEDNA ODPOWIEDZ ===")
# Nie porownujemy wartosci stalych — porownujemy ZACHOWANIE. Stala da sie
# skopiowac i zapomniec; zachowanie rozjedzie sie od razu.
cofnij = z_data("2026-08-25")
try:
    import importlib

    import audyt_systemu
    importlib.reload(audyt_systemu)
    sprawdz("wzajemnosc.KOTWICA_NISZY bierze date z konfiguracji",
            wzajemnosc.KOTWICA_NISZY == config.DATA_PRZESTAWIENIA,
            (wzajemnosc.KOTWICA_NISZY, config.DATA_PRZESTAWIENIA))
    sprawdz("audyt_systemu.PIVOT bierze date z konfiguracji",
            audyt_systemu.PIVOT == config.DATA_PRZESTAWIENIA,
            (audyt_systemu.PIVOT, config.DATA_PRZESTAWIENIA))
    stary = "2026-08-24T10:00:00+00:00"
    nowy = "2026-08-26T10:00:00+00:00"
    sprawdz("stages i run zgadzaja sie na wpisie starym",
            stages._z_obecnej_epoki({"kiedy": stary})
            == run._po_zmianie_tematu(stary) is False)
    sprawdz("stages i run zgadzaja sie na wpisie nowym",
            stages._z_obecnej_epoki({"kiedy": nowy})
            == run._po_zmianie_tematu(nowy) is True)
finally:
    cofnij()
    import importlib as _il

    import audyt_systemu as _as
    _il.reload(_as)

print()
print("=== 4. KONTRDOWOD: BEZ TEJ LOGIKI TEST BY NIE ROZROZNIL ===")
# Test, ktory tylko wola funkcje i patrzy, czy nie rzuca, wyglada tak samo jak
# test mierzacy cokolwiek. Pokazujemy wprost, ze ta sama data daje ROZNE
# odpowiedzi zaleznie od granicy — czyli ze funkcja w ogole na nia patrzy.
DZIEN = "2026-08-24T10:00:00+00:00"
cofnij = z_data("")
try:
    bez_granicy = stages._z_obecnej_epoki({"kiedy": DZIEN})
finally:
    cofnij()
cofnij = z_data("2026-08-25")
try:
    z_granica = stages._z_obecnej_epoki({"kiedy": DZIEN})
finally:
    cofnij()
sprawdz("ta sama data, dwie rozne odpowiedzi",
        (bez_granicy, z_granica) == (True, False), (bez_granicy, z_granica))

print()
print("=== 5. ZADEN MODUL NIE TRZYMA DATY WPISANEJ NA SZTYWNO ===")
# TU JEST WLASCIWA POPRAWKA, a sekcje wyzej sa tylko jej sprawdzeniem.
#
# Cztery pierwsze kopie tej daty znaleziono, bo ktos ich SZUKAL PO NAZWIE.
# Piata (`raport_statystyk.PIVOT`) miala nazwe IDENTYCZNA z druga i mimo to
# przezyla poprawke, ktora druga naprawiala — bo lista miejsc byla wypisana
# recznie, a reczna lista jest zawsze o jedno krotsza. To zdanie pada w tym
# repozytorium po raz czwarty i za czwartym razem przestajemy pisac liste.
#
# SZUKAMY KSZTALTU, NIE NAZWY: napis wygladajacy jak „RRRR-MM-DD" przypisany
# do stalej na poziomie modulu. Falszywych trafien nie ma — data w kodzie tego
# bota nie ma innych zastosowan niz kotwica albo prog — a szosta kopia,
# dopisana jutro pod dowolna nazwa, oblewa TUTAJ, zanim ktokolwiek zauwazy
# rozjazd na produkcji.
import ast as _ast          # noqa: E402
import pathlib as _pathlib  # noqa: E402


def _wyglada_jak_data(n: str) -> bool:
    """RRRR-MM-DD, sprawdzone znak po znaku.

    Bez wyrazenia regularnego celowo: wzorzec z odwrotnymi ukosnikami jest
    jedyna czescia tej sekcji, ktora moglaby sie zepsuc przy przenoszeniu,
    a pytanie jest na tyle proste, ze nie potrzebuje wzorca.
    """
    return (len(n) == 10 and n[4] == "-" and n[7] == "-"
            and n[:4].isdigit() and n[5:7].isdigit() and n[8:].isdigit())


def _stale_bedace_data(zrodlo: str) -> list[tuple[str, int, str]]:
    """Stale modulu, ktorych wartoscia jest napis wygladajacy jak data."""
    out = []
    for w in _ast.parse(zrodlo).body:
        if not isinstance(w, (_ast.Assign, _ast.AnnAssign)):
            continue
        cele = w.targets if isinstance(w, _ast.Assign) else [w.target]
        wart = w.value
        napisy = []
        if isinstance(wart, _ast.Constant) and isinstance(wart.value, str):
            napisy = [wart.value]
        elif isinstance(wart, (_ast.Tuple, _ast.List, _ast.Set)):
            napisy = [e.value for e in wart.elts
                      if isinstance(e, _ast.Constant)
                      and isinstance(e.value, str)]
        nazwy = ",".join(c.id for c in cele if isinstance(c, _ast.Name))
        for n in napisy:
            if _wyglada_jak_data(n):
                out.append((nazwy, w.lineno, n))
    return out


_znalezione = []
for _p in sorted(_pathlib.Path("agent-v2").glob("*.py")):
    for _nazwa, _linia, _wartosc in _stale_bedace_data(
            _p.read_text(encoding="utf-8")):
        _znalezione.append("%s:%d %s = %s" % (_p.name, _linia, _nazwa, _wartosc))
sprawdz("zadna stala modulu nie jest data", not _znalezione,
        "; ".join(_znalezione))

# KONTRDOWOD: skan MUSI umiec taka stala znalezc. Bez tego przechodzilby
# takze wtedy, gdyby sprawdzanie ksztaltu bylo zepsute i nie lapalo niczego.
_probka = "KOTWICA = '2026-08-25'\nINNA = 'nie data'\nLICZBA = 7\n"
sprawdz("skan lapie date wpisana na sztywno",
        [x[0] for x in _stale_bedace_data(_probka)] == ["KOTWICA"],
        _stale_bedace_data(_probka))
sprawdz("i nie lapie napisu, ktory data nie jest",
        not _wyglada_jak_data("2026-8-25")
        and not _wyglada_jak_data("RRRR-MM-DD"))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
