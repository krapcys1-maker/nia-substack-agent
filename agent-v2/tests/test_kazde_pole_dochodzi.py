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
import io
import re
import tokenize
import pathlib
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
print("=== 4. A CZY KTOKOLWIEK TE STALA POTEM CZYTA ===")
# DRUGIE OGNIWO TEGO SAMEGO LANCUCHA. Sekcja 1 pilnuje, ze wartosc DOJDZIE do
# stalej. Tu pytamy, czy stala ma potem czytelnika w kodzie agenta — bo pole,
# ktore dochodzi donikad, jest dokladnie tak samo martwe jak pole, ktore nie
# dochodzi wcale, i wyglada tak samo dobrze.
#
# Tak przeszla `ZNAKI_NISZY`: pytana, walidowana, meldowana, ustawiana — i
# czytana wylacznie przez audyt, kreator, jeden test i dokumentacje.
#
# CZYTELNIKIEM JEST MODUL AGENTA, nie narzedzie i nie test. `narzedzia/` sluzy
# operatorowi, testy sluza nam; ani jedno, ani drugie nie zmienia tego, co bot
# robi w internecie. Liczy sie takze uzycie wewnatrz samego `config.py` (poza
# definicja) — stamtad ida wyprowadzone sufity i sciezki.
#
# KOMENTARZE ODSIEWAMY. Zdanie o stalej nie jest jej uzyciem; bez tego akapit
# opisujacy pole zwalnialby je z pytania.


def _bez_komentarzy(tekst: str) -> str:
    wiersze = tekst.split(chr(10))
    try:
        strumien = tokenize.generate_tokens(io.StringIO(tekst).readline)
        for typ, _n, (w1, k1), (w2, k2), _l in strumien:
            if typ != tokenize.COMMENT:
                continue
            for nr in range(w1, w2 + 1):
                if nr - 1 >= len(wiersze):
                    break
                linia = wiersze[nr - 1]
                od = k1 if nr == w1 else 0
                do = k2 if nr == w2 else len(linia)
                wiersze[nr - 1] = linia[:od] + " " * max(0, do - od) + linia[do:]
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return tekst
    return chr(10).join(wiersze)


# POLA BEZ CZYTELNIKA, KTORE ZOSTAJA SWIADOMIE. Kazdy wpis wymaga powodu.
BEZ_CZYTELNIKA_ZOSTAJA = {
    "ZNAKI_NISZY": "RUBRYKA, NIE FILTR — po tej liscie audyt, kreator i "
                   "`test_szukanie_celow.py` oceniaja, czy HASLA_SZUKANIA "
                   "trzymaja sie tematu, ktory operator sam opisal. O tym, "
                   "czy KONKRETNY post jest na temat, decyduje model wedlug "
                   "`prompts/cele.md`. Cztery miejsca twierdzily kiedys, ze "
                   "ta lista filtruje cudze posty — nie filtruje.",
}

_moduly = [p for p in pathlib.Path("agent-v2").glob("*.py")
           if p.name != "konfiguracja.py"]
_tresc = {p.name: _bez_komentarzy(p.read_text(encoding="utf-8"))
          for p in _moduly}
_cfg = _tresc.pop("config.py")


def _ma_czytelnika(stala: str) -> bool:
    wzorzec = r"\b%s\b" % re.escape(stala)
    if any(re.search(wzorzec, t) for t in _tresc.values()):
        return True
    # Uzycie WEWNATRZ `config.py` poza sama definicja tez sie liczy — stamtad
    # ida wyprowadzone sufity i sciezki (np. `MAX_WORDS` w budzecie tokenow).
    return len(re.findall(wzorzec, _cfg)) > 1


_sieroty = []
for _sciezka, (_stala, _w) in sorted(konfiguracja.POLA.items()):
    if not _stala or _stala in BEZ_CZYTELNIKA_ZOSTAJA:
        continue
    if not _ma_czytelnika(_stala):
        _sieroty.append("%s -> %s" % (_sciezka, _stala))
print("    pol z nazwana stala: %d, zwolnionych z powodem: %d"
      % (sum(1 for _s, (_k, _v) in konfiguracja.POLA.items() if _k),
         len(BEZ_CZYTELNIKA_ZOSTAJA)))
sprawdz("kazde pole ma czytelnika w kodzie agenta", not _sieroty, _sieroty)

# KONTRDOWOD: skan musi umiec zobaczyc sierote. Bez tego przechodzilby takze
# wtedy, gdyby wzorzec nie pasowal do niczego.
sprawdz("nazwa, ktorej nigdzie nie ma, jest widziana jako sierota",
        not _ma_czytelnika("STALA_KTOREJ_NIE_MA_W_ZADNYM_MODULE"))
sprawdz("a stala z prawdziwym czytelnikiem nie jest",
        _ma_czytelnika("ODSTEP_DNI_NA_PUBLIKACJE"))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
