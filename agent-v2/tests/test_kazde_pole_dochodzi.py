# -*- coding: utf-8 -*-
"""Kazde pole konfiguracji ma GDZIES DOJSC — a jedno nie dochodzilo nigdzie.

## Po co ten plik istnieje

`konfiguracja.POLA` wiaze sciezke `sekcja.pole` z nazwa stalej w `config.py`.
Wartosc `None` zamiast nazwy znaczy „obsluzone osobno w `zastosuj`", bo pole
trafia gdzie indziej niz do stalej o tej samej nazwie.

`zastosuj` obslugiwalo osobno TRZY takie pola — `publikowanie.miks_notek`,
`temat.przyklady`, `modele.role` — a czwartego, `zrodla.kanaly_youtube`, NIE.
Skutek:

  1. `narzedzia/kreator.py` PYTAL operatora o kanaly YouTube,
  2. wartosc szla do `konfiguracja.toml`,
  3. przechodzila sprawdzenie przy wczytaniu,
  4. i byla cicho wyrzucana.

Bot uzywal dalej `korpus_kanalow.KANALY` — slownika wpisanego w kod. Caly
korpus kanalow byl przez to martwy u kazdego operatora i NIE DALO SIE go
wlaczyc, mimo ze konfigurator o niego pytal.

To jest „pole, ktore wyglada jak ustawienie i nie robi nic" — w samym srodku
tego, po co ten konfigurator powstal. Nie zglaszalo sie NICZYM: plik sie
wczytywal, walidacja przechodzila, `zastosuj` nie protestowalo.

## Czego pilnuje

Jednej rzeczy, wyprowadzonej z `POLA`, a nie z listy: **`zastosuj` MUSI
zameldowac kazde podane pole**. Lista zwracana przez `zastosuj` istnieje po to,
zeby powiedziec, co przestawiono — wiec pole, ktorego w niej nie ma, nie
zostalo przestawione nigdzie.

Nowe pole dopisane jutro z `None` i zapomniane w `zastosuj` oblewa TUTAJ.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_kazde_pole_dochodzi.py
"""
import sys

sys.path.insert(0, "agent-v2")
import config          # noqa: E402
import konfiguracja    # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# Najmniejsza sensowna wartosc dla kazdego sprawdzacza. Nie sa to wartosci
# produkcyjne — chodzi wylacznie o to, zeby przeszly walidacje i dalo sie
# zobaczyc, czy `zastosuj` je zauwazylo.
def _probka(pole: str, sprawdzacz) -> object:
    nazwa = getattr(sprawdzacz, "__name__", "")
    if pole == "publikowanie.miks_notek":
        return [sorted(config.NOTE_TYPES)[0]]
    if pole == "temat.przyklady":
        klucz = sorted(config.PRZYKLADY_NISZY)[0]
        return {klucz: ["probna pozycja"]}
    if pole == "modele.role":
        rola = sorted(config.MODEL_FOR)[0]
        return {rola: config.MODEL_FOR[rola]}
    if nazwa == "_slownik_napisow":
        return {"Probny": "UCprobnyprobnyprobny01"}
    if nazwa == "_slownik_list":
        return {sorted(config.PRZYKLADY_NISZY)[0]: ["probna"]}
    if nazwa == "_lista_napisow":
        return ["probna"]
    if nazwa == "_lista_napisow_moze_pusta":
        return []
    if nazwa == "_widelki":
        return [1, 2]
    if nazwa == "_liczba":
        return 1
    if nazwa == "_prawda":
        return True
    if nazwa == "_data_albo_pusto":
        return ""
    return "probna"


print("=== 1. `zastosuj` MELDUJE KAZDE PODANE POLE ===")
# Podajemy wszystkie pola naraz — tak jak robi to prawdziwy plik konfiguracji.
_dane = {pole: _probka(pole, sprawdzacz)
         for pole, (_, sprawdzacz) in konfiguracja.POLA.items()}

# Sprawdzacze uruchamiamy tak, jak robi to `wczytaj`: wartosc, ktora nie
# przechodzi walidacji, byla by bledem samej probki, a nie badanej wlasnosci.
_gotowe = {}
for pole, wartosc in _dane.items():
    try:
        _gotowe[pole] = konfiguracja.POLA[pole][1](wartosc, "probka: %s" % pole)
    except konfiguracja.BledKonfiguracji as exc:
        sprawdz("probka dla %s przechodzi walidacje" % pole, False, exc)

_stan = {n: getattr(config, n) for n, _ in konfiguracja.POLA.values()
         if n is not None and hasattr(config, n)}
_miks = config.NOTE_MIX_OTHER_DAY
_przyklady = dict(config.PRZYKLADY_NISZY)
_modele = dict(config.MODEL_FOR)
try:
    zmienione = konfiguracja.zastosuj(_gotowe, config)
finally:
    for n, w in _stan.items():
        setattr(config, n, w)
    config.NOTE_MIX_OTHER_DAY = _miks
    config.PRZYKLADY_NISZY.clear()
    config.PRZYKLADY_NISZY.update(_przyklady)
    config.MODEL_FOR.clear()
    config.MODEL_FOR.update(_modele)

_zameldowane = {w.split(" -> ")[0] for w in zmienione}
_zgubione = sorted(set(_gotowe) - _zameldowane)
sprawdz("kazde podane pole jest w wyniku `zastosuj`", not _zgubione, _zgubione)

print()
print("=== 2. POLA Z `None` MAJA WLASNA OBSLUGE ===")
# Te sa najbardziej narazone: `None` znaczy „obsluzone osobno", a „osobno"
# latwo jest przeoczyc. `zrodla.kanaly_youtube` bylo przeoczone.
_osobne = sorted(p for p, (n, _) in konfiguracja.POLA.items() if n is None)
print("  pol obslugiwanych osobno: %d (%s)"
      % (len(_osobne), ", ".join(_osobne) or "zadnego"))
for pole in _osobne:
    sprawdz("  %s dochodzi" % pole, pole in _zameldowane)

print()
print("=== 3. KONTRDOWOD: WYNIK `zastosuj` NAPRAWDE ROZROZNIA ===")
# Bez tego sekcja 1 przechodzilaby takze wtedy, gdyby `zastosuj` meldowalo
# wszystko, co dostalo, niezaleznie od tego, czy cokolwiek przestawilo.
_puste = konfiguracja.zastosuj({}, config)
sprawdz("pusta konfiguracja nie melduje niczego", _puste == [], _puste)
_jedno = {"konto.nazwa_marki": "Probna Marka Kontrolna"}
_stara_marka = config.NAZWA_MARKI
try:
    _wynik = konfiguracja.zastosuj(_jedno, config)
    sprawdz("jedno pole melduje sie raz", len(_wynik) == 1, _wynik)
    sprawdz("i naprawde przestawia stala",
            config.NAZWA_MARKI == "Probna Marka Kontrolna", config.NAZWA_MARKI)
finally:
    config.NAZWA_MARKI = _stara_marka

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
