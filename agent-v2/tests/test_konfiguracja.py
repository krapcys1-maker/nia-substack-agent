# -*- coding: utf-8 -*-
"""`konfiguracja.toml` NAPRAWDE steruje botem, a zla wartosc zatrzymuje start.

## Po co

Plik konfiguracji, ktory po cichu ignoruje literowke w nazwie pola, jest GORSZY
od jego braku: bot chodzi, robi co innego, niz napisano, i nikt tego nie
zauwaza. To ta sama klasa bledu, ktora ten projekt zna z innej strony — stala
udajaca zabezpieczenie i test zielony nad martwym kodem.

Ten plik sprawdza trzy rzeczy i w tej kolejnosci:

  1. wartosc z pliku NAPRAWDE dochodzi do stalej w `config`, a nie tylko daje
     sie wczytac;
  2. kazdy bledny ksztalt wartosci ORAZ nieznane pole ZATRZYMUJA start;
  3. KONTRDOWOD: bez pliku nic sie nie zmienia, wiec test mierzy dzialanie
     konfiguracji, a nie przypadkowa zgodnosc wartosci domyslnych.

## Czego NIE sprawdza

Nie sprawdza, czy wartosci sa MADRE — `HASLA_SZUKANIA` o wlasciwym ksztalcie,
ale bez sensu, przejda tutaj i zostana zlapane przez `test_szukanie_celow`.
Podzial jest celowy: tu ksztalt, tam tresc.
"""
from __future__ import annotations

import pathlib
import sys
import tempfile

KORZEN = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KORZEN))

import config          # noqa: E402
import konfiguracja    # noqa: E402

# TOML W BIBLIOTECE STANDARDOWEJ JEST OD 3.11. Na 3.10 `konfiguracja.wczytaj`
# swiadomie ODMAWIA z czytelnym komunikatem — i to jest zachowanie poprawne,
# bo bot ma chodzic na 3.10 bez pliku konfiguracji. Test nie moze wiec udawac,
# ze go sprawdzil: pomija sie JAWNIE, tak samo jak testy siegajace po historie.
#
# Zlapala to macierz wersji w CI. Lokalnie chodze na 3.12 i nie mialem szansy
# tego zobaczyc.
if sys.version_info < (3, 11):
    print("=== POMINIETE: `tomllib` jest w bibliotece standardowej od 3.11 ===")
    print("    masz %d.%d, wiec `konfiguracja.toml` jest tu niedostepny"
          % (sys.version_info[0], sys.version_info[1]))
    print("    Sam bot dziala na 3.10 — bez pliku konfiguracji, na wartosciach")
    print("    domyslnych z config.py. To nie jest wada.")
    raise SystemExit(0)

zdane = oblane = 0


def sprawdz(nazwa: str, warunek: bool, szczegol: object = "") -> None:
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


class Atrapa:
    """Namiastka modulu `config` — zeby test nie ruszal prawdziwego."""

    def __init__(self) -> None:
        self.SUBSTACK_HANDLE = "stary-uchwyt"
        self.NAZWA_MARKI = "Stara Marka"
        self.NISZA = "stara nisza"
        self.ARTICLE_LANGUAGE = "English"
        self.KOMENTARZE_DZIENNIE = (15, 23)
        self.MONTHLY_LIMIT_USD = 40.0
        self.MODEL_FOR = {"note": "model-a", "comment": "model-b"}
        self.NOTE_TYPES = {"CIEKAWOSTKA": 1, "MYSL": 1, "DYSKUSJA": 1}
        self.NOTE_MIX_OTHER_DAY = ("CIEKAWOSTKA",)


def wczytaj_tekst(tekst: str) -> dict:
    """Wczytuje konfiguracje z napisu, przez prawdziwy plik na dysku."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        plik = pathlib.Path(tmp) / konfiguracja.NAZWA_PLIKU
        plik.write_text(tekst, encoding="utf-8")
        return konfiguracja.wczytaj(plik)


def oblewa(tekst: str) -> str | None:
    """Oddaje komunikat bledu albo None, gdy przeszlo."""
    try:
        dane = wczytaj_tekst(tekst)
        konfiguracja.zastosuj(dane, Atrapa())
        return None
    except konfiguracja.BledKonfiguracji as exc:
        return str(exc)


print("=== 1. WARTOSC Z PLIKU DOCHODZI DO STALEJ ===")
cfg = Atrapa()
dane = wczytaj_tekst('''
[konto]
uchwyt = "nowy-uchwyt"
nazwa_marki = "Nowa Marka"

[temat]
nisza = "nowa nisza"

[wolumeny]
komentarze_dziennie = [3, 7]

[pieniadze]
sufit_miesieczny_usd = 12.5

[modele]
role = { note = "inny-model" }

[publikowanie]
miks_notek = ["CIEKAWOSTKA", "MYSL"]
''')
zmienione = konfiguracja.zastosuj(dane, cfg)

sprawdz("uchwyt konta", cfg.SUBSTACK_HANDLE == "nowy-uchwyt", cfg.SUBSTACK_HANDLE)
sprawdz("nazwa marki", cfg.NAZWA_MARKI == "Nowa Marka", cfg.NAZWA_MARKI)
sprawdz("nisza", cfg.NISZA == "nowa nisza", cfg.NISZA)
sprawdz("widelki wolumenu", cfg.KOMENTARZE_DZIENNIE == (3, 7), cfg.KOMENTARZE_DZIENNIE)
sprawdz("sufit miesieczny", cfg.MONTHLY_LIMIT_USD == 12.5, cfg.MONTHLY_LIMIT_USD)
sprawdz("pole NIEPODANE zostaje nietkniete",
        cfg.ARTICLE_LANGUAGE == "English", cfg.ARTICLE_LANGUAGE)

print()
print("=== 2. MODELE NAKLADAJA SIE, A NIE ZASTEPUJA SLOWNIKA ===")
# Podanie jednej roli nie moze skasowac dwudziestu pieciu pozostalych — to
# najlatwiejszy sposob na bota, ktory po zmianie jednego modelu nie ma reszty.
sprawdz("podana rola zmieniona", cfg.MODEL_FOR["note"] == "inny-model",
        cfg.MODEL_FOR)
sprawdz("niepodana rola ZOSTAJE", cfg.MODEL_FOR["comment"] == "model-b",
        cfg.MODEL_FOR)

print()
print("=== 3. LICZBA NOTEK TO DLUGOSC MIKSU, NIE OSOBNA STALA ===")
sprawdz("miks przestawiony", cfg.NOTE_MIX_OTHER_DAY == ("CIEKAWOSTKA", "MYSL"),
        cfg.NOTE_MIX_OTHER_DAY)
sprawdz("czyli dwie notki na dobe", len(cfg.NOTE_MIX_OTHER_DAY) == 2)
sprawdz("i raport mowi ILE", any("2 notek na dobe" in z for z in zmienione),
        zmienione)

print()
print("=== 4. BLEDNA WARTOSC ZATRZYMUJE START ===")
przypadki = [
    ("nieznane pole", '[konto]\nuchwyyt = "x"\n', "nieznane pola"),
    ("nieznana sekcja", '[konnto]\nuchwyt = "x"\n', "nieznane pola"),
    ("pusty napis", '[konto]\nuchwyt = ""\n', "niepustego napisu"),
    ("napis zamiast liczby", '[pieniadze]\nsufit_dzienny_usd = "duzo"\n', "liczby"),
    ("liczba zamiast napisu", '[temat]\nnisza = 7\n', "napisu"),
    ("widelki o trzech liczbach",
     "[wolumeny]\nlajki_dziennie = [1, 2, 3]\n", "dwoch liczb"),
    ("widelki odwrotnie",
     "[wolumeny]\nlajki_dziennie = [9, 2]\n", "wieksza od gornej"),
    ("pusta lista", "[temat]\nznaki_niszy = []\n", "niepustej listy"),
    ("liczby zamiast napisow w liscie",
     "[temat]\nhasla_szukania = [1, 2]\n", "niepustej listy"),
    ("true zamiast liczby",
     "[publikowanie]\nnotek_promujacych = true\n", "liczby"),
    ("nieznany etap modelu",
     '[modele]\nrole = { nie_ma_takiego = "x" }\n', "nieznane etapy"),
    ("nieznany typ notki",
     '[publikowanie]\nmiks_notek = ["ZMYSLONY"]\n', "nieznane typy notek"),
    ("nieczytalny TOML", "[konto\nuchwyt =\n", "nieczytelny"),
]
for nazwa, tekst, fragment in przypadki:
    komunikat = oblewa(tekst)
    sprawdz("  %s -> zatrzymuje" % nazwa, komunikat is not None)
    sprawdz("  %s -> komunikat mowi CO" % nazwa,
            bool(komunikat) and fragment in komunikat,
            (komunikat or "")[:110])

print()
print("=== 5. KOMUNIKAT PODPOWIADA, CO BYLO DOZWOLONE ===")
# Blad, ktory mowi tylko „zle", kosztuje tyle samo co brak bledu.
k = oblewa('[konto]\nuchwyyt = "x"\n') or ""
sprawdz("nieznane pole wypisuje LISTE znanych", "Znane pola:" in k, k[:120])
k2 = oblewa('[modele]\nrole = { nie_ma = "x" }\n') or ""
sprawdz("nieznany etap wypisuje LISTE etapow", "Znane etapy:" in k2, k2[:120])

print()
print("=== 6. KONTRDOWOD: BEZ PLIKU NIC SIE NIE ZMIENIA ===")
# Bez tego caly plik moglby przechodzic dlatego, ze wartosci domyslne
# przypadkiem zgadzaja sie z tymi w atrapie.
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    brak = konfiguracja.wczytaj(pathlib.Path(tmp) / "nie-ma-takiego.toml")
sprawdz("brak pliku daje pusta konfiguracje", brak == {}, brak)

czysty = Atrapa()
przed = (czysty.SUBSTACK_HANDLE, czysty.NISZA, dict(czysty.MODEL_FOR),
         czysty.NOTE_MIX_OTHER_DAY)
sprawdz("i `zastosuj` na pustce nie rusza NICZEGO",
        konfiguracja.zastosuj({}, czysty) == []
        and (czysty.SUBSTACK_HANDLE, czysty.NISZA, dict(czysty.MODEL_FOR),
             czysty.NOTE_MIX_OTHER_DAY) == przed)

print()
print("=== 7. PRAWDZIWY config JEST SPOJNY Z TYM MODULEM ===")
# Nazwy stalych w `POLA` musza istniec w `config`, inaczej konfiguracja
# tworzylaby nowe stale, ktorych nikt nie czyta — czyli pola bez skutku.
brakujace = [nazwa for nazwa, _ in konfiguracja.POLA.values()
             if nazwa is not None and not hasattr(config, nazwa)]
sprawdz("kazde pole wskazuje na ISTNIEJACA stala config", not brakujace,
        brakujace)

sprawdz("plik przykladowy istnieje",
        (KORZEN.parent / "konfiguracja.example.toml").exists())

# Przykladowy plik musi sie wczytywac — inaczej pierwsza rzecz, ktora robi
# nowy uzytkownik (kopiuje przyklad), oblewa sie na starcie.
przyklad = KORZEN.parent / "konfiguracja.example.toml"
if przyklad.exists():
    try:
        dane_p = konfiguracja.wczytaj(przyklad)
        blad = None
    except konfiguracja.BledKonfiguracji as exc:
        dane_p, blad = {}, str(exc)
    sprawdz("plik przykladowy WCZYTUJE SIE bez bledu", blad is None, blad)
    sprawdz("i podaje co najmniej 15 pol", len(dane_p) >= 15, len(dane_p))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
