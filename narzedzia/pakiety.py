# -*- coding: utf-8 -*-
"""Wsady tematyczne: gotowy temat do podpiecia, jeden plik na dziedzine.

## Po co to istnieje

Najtrudniejsza czesc zakladania tego bota nie jest techniczna. Klucze API
wkleja sie w minute, a potem kreator pyta o dwadziescia piec hasel szukania,
dwadziescia znakow niszy i trzydziesci dziedzin — i to jest miejsce, w ktorym
czlowiek utyka na godzine albo wpisuje cokolwiek i dostaje bota, ktory szuka
nie tego, czego trzeba. W logu wyglada to potem na wybrednosc modelu
(„warte komentarza: 0/15"), a jest zla konfiguracja tematu.

Wsad to ten material zrobiony raz, porzadnie, przez kogos kto zna dziedzine.

## Czego wsad NIE zawiera, i to jest cala rzecz

TEMAT I ZRODLA. Nic wiecej. Nie ma w nim uchwytu konta, sufitow pieniedzy,
wolumenow ani wyboru modeli — bo wsad przychodzi z zewnatrz, od obcej osoby,
przez pull requesta. Plik od kogos innego nie moze ustawic Twojego konta ani
Twojego budzetu, nawet przez pomylke. Lista pol jest tu ZAMKNIETA i sprawdzana:
klucz spoza `temat.*` i `zrodla.*` zatrzymuje wczytanie.

## Jak sprawdzamy, ze wsad jest dobry

Tymi samymi walidatorami, ktorych uzywa loader (`konfiguracja.POLA`) — nie
druga kopia regul, bo dwie kopie tej samej reguly to dwie rozne reguly.
Do tego reguly STRUKTURALNE, niezalezne od dziedziny:

  * pula hasel szersza niz jeden przebieg (3 x `ILE_HASEL_NA_PRZEBIEG`),
    inaczej kazdy przebieg bierze ja w calosci i wraca po tych samych kontach;
  * kazde haslo niesie znak niszy Z TEGO SAMEGO PLIKU, inaczej agent znajduje
    posty, a `prompts/cele.md` odrzuca je co do jednego;
  * siatka wzorcow x dziedzin daje co najmniej 10 komorek na notke na dobe.

Uzycie:
    python narzedzia/pakiety.py                     # lista wsadow
    python narzedzia/pakiety.py --pokaz ai          # co jest w srodku
    python narzedzia/pakiety.py --sprawdz           # zwaliduj wszystkie
    python narzedzia/pakiety.py --zastosuj ai       # wpisz do konfiguracji
"""
from __future__ import annotations

import pathlib
import sys

KORZEN = pathlib.Path(__file__).resolve().parent.parent
KATALOG = KORZEN / "packs"
sys.path.insert(0, str(KORZEN / "agent-v2"))

import konfiguracja  # noqa: E402

# POLA, KTORE WSAD MOZE USTAWIC. Zamkniete celowo — patrz naglowek.
DOZWOLONE_SEKCJE = ("temat", "zrodla")

# Pola opisujace SAM WSAD, nie konfiguracje bota.
METADANE = ("name", "language", "description", "author", "added", "source")


class ZlyPakiet(Exception):
    """Wsad, ktorego nie przyjmujemy. Komunikat ma mowic, co poprawic."""


def _tomllib():
    if sys.version_info < (3, 11):
        raise ZlyPakiet(
            "czytanie wsadow wymaga Pythona 3.11 lub nowszego (masz %d.%d) — "
            "`tomllib` wszedl do biblioteki standardowej dopiero tam"
            % (sys.version_info[0], sys.version_info[1]))
    import tomllib
    return tomllib


def lista() -> list[pathlib.Path]:
    """Wszystkie wsady, posortowane. Brak katalogu = pusta lista."""
    if not KATALOG.is_dir():
        return []
    return sorted(p for p in KATALOG.glob("*.toml"))


def wczytaj(plik: pathlib.Path) -> dict:
    """Surowa zawartosc wsadu, po sprawdzeniu KSZTALTU.

    Sprawdzamy tu tylko to, co dotyczy pliku jako wsadu: obecnosc metadanych
    i brak pol spoza dozwolonych sekcji. WARTOSCI sprawdza `waliduj`, bo to
    robota walidatorow loadera i nie chcemy ich drugiej kopii.
    """
    tomllib = _tomllib()
    try:
        dane = tomllib.loads(plik.read_text(encoding="utf-8"))
    except Exception as exc:                                # noqa: BLE001
        raise ZlyPakiet("%s nie jest poprawnym TOML-em (%s: %s)"
                        % (plik.name, type(exc).__name__, exc))

    opis = dane.get("pack")
    if not isinstance(opis, dict):
        raise ZlyPakiet(
            "%s nie ma sekcji [pack]. Wsad bez opisu jest nie do odroznienia "
            "od cudzej konfiguracji, ktora ktos wrzucil przez pomylke."
            % plik.name)
    for wymagane in ("name", "language", "description"):
        if not str(opis.get(wymagane) or "").strip():
            raise ZlyPakiet("%s: [pack] nie ma pola `%s`"
                            % (plik.name, wymagane))
    obce = sorted(set(opis) - set(METADANE))
    if obce:
        raise ZlyPakiet("%s: [pack] ma pola spoza listy: %s (dozwolone: %s)"
                        % (plik.name, ", ".join(obce), ", ".join(METADANE)))

    # SEKCJE SPOZA LISTY ZATRZYMUJA WCZYTANIE. Wsad przychodzi od obcej osoby;
    # plik, ktory moglby ustawic uchwyt konta albo sufit pieniedzy, jest tu
    # niedopuszczalny nawet jako pomylka.
    nadmiar = sorted(set(dane) - {"pack"} - set(DOZWOLONE_SEKCJE))
    if nadmiar:
        raise ZlyPakiet(
            "%s ma sekcje, ktorych wsad ustawiac NIE MOZE: %s.\n"
            "Wsad opisuje TEMAT i ZRODLA. Konto, pieniadze, wolumeny i modele "
            "sa decyzja osoby, ktora go uzywa." % (plik.name, ", ".join(nadmiar)))
    return dane


def plaskie(dane: dict) -> dict:
    """Zawartosc wsadu jako `sekcja.pole` — w postaci, ktorej uzywa loader."""
    out: dict[str, object] = {}
    for sekcja in DOZWOLONE_SEKCJE:
        zawartosc = dane.get(sekcja)
        if not isinstance(zawartosc, dict):
            continue
        for pole, wartosc in zawartosc.items():
            out["%s.%s" % (sekcja, pole)] = wartosc
    return out


def waliduj(plik: pathlib.Path) -> tuple[dict, list[str]]:
    """Zwraca (wartosci, uwagi). Blad twardy podnosi `ZlyPakiet`.

    Wartosci ida przez TE SAME walidatory, co `konfiguracja.toml` — bez drugiej
    implementacji regul. Uwagi to rzeczy, ktore nie sa bledem pliku, ale
    czlowiek powinien je zobaczyc.
    """
    dane = wczytaj(plik)
    pola = plaskie(dane)
    nieznane = sorted(set(pola) - set(konfiguracja.POLA))
    if nieznane:
        raise ZlyPakiet(
            "%s: pola, ktorych ten bot nie zna: %s.\n"
            "Literowka w nazwie pola jest gorsza od jego braku — cicho nic by "
            "nie ustawila." % (plik.name, ", ".join(nieznane)))

    gotowe: dict[str, object] = {}
    for sciezka, wartosc in pola.items():
        _stala, walidator = konfiguracja.POLA[sciezka]
        try:
            gotowe[sciezka] = walidator(wartosc, sciezka)
        except konfiguracja.BledKonfiguracji as exc:
            raise ZlyPakiet("%s: %s" % (plik.name, exc))

    uwagi = []
    if not gotowe.get("temat.przyklady"):
        uwagi.append("bez `[temat.przyklady]` — prompty dostana mniej"
                     " zaczepien, ale wszystko dziala")
    if not gotowe.get("zrodla.kanaly_youtube"):
        uwagi.append("bez kanalow YouTube — korpus kanalow bedzie pusty")
    return gotowe, uwagi


def reguly_strukturalne(gotowe: dict, cfg) -> list[str]:
    """Reguly niezalezne od dziedziny. Zwraca liste zlaman (pusta = dobrze).

    KAZDA wywodzi sie ze STRUKTURY, nie z liczby wpisanej recznie — inaczej
    powtorzylibysmy blad, ktory ten projekt juz raz popelnil: prog z jednej
    instalacji podany jako prawo natury (patrz `test_przyklad_przechodzi_reguly`).
    """
    zle = []
    hasla = [str(h).lower() for h in gotowe.get("temat.hasla_szukania", ())]
    znaki = [str(z).lower() for z in gotowe.get("temat.znaki_niszy", ())]
    dziedziny = list(gotowe.get("temat.dziedziny", ()))

    minimum = 3 * cfg.ILE_HASEL_NA_PRZEBIEG
    if len(hasla) < minimum:
        zle.append("%d hasel przy %d losowanych na przebieg — potrzeba co "
                   "najmniej %d, inaczej kazdy przebieg bierze cala pule "
                   "i wraca po tych samych kontach"
                   % (len(hasla), cfg.ILE_HASEL_NA_PRZEBIEG, minimum))
    poza = [h for h in hasla if not any(z in h for z in znaki)]
    if poza:
        zle.append("%d hasel nie niesie ZADNEGO znaku niszy z tego pliku (%s) "
                   "— agent znajdzie posty, a regula celow odrzuci je co do "
                   "jednego" % (len(poza), ", ".join(poza[:3])))
    komorki = len(cfg.GENERATORY) * max(1, len(dziedziny))
    na_dobe = max(1, len(cfg.NOTE_MIX_OTHER_DAY))
    if komorki < 10 * na_dobe:
        zle.append("siatka daje %d komorek (%d wzorcow x %d dziedzin) przy %d "
                   "notkach na dobe — dopisz dziedziny, inaczej ten sam wzorzec "
                   "w tej samej dziedzinie wroci w tym samym tygodniu"
                   % (komorki, len(cfg.GENERATORY), len(dziedziny), na_dobe))
    return zle


def znajdz(nazwa: str) -> pathlib.Path:
    """Wsad po nazwie pliku albo po jej poczatku. Niejednoznaczne = blad."""
    kandydaci = [p for p in lista()
                 if p.stem == nazwa or p.stem.startswith(nazwa)]
    if not kandydaci:
        raise ZlyPakiet("nie ma wsadu `%s`. Dostepne: %s"
                        % (nazwa, ", ".join(p.stem for p in lista()) or "(brak)"))
    if len(kandydaci) > 1 and not any(p.stem == nazwa for p in kandydaci):
        raise ZlyPakiet("`%s` pasuje do kilku: %s"
                        % (nazwa, ", ".join(p.stem for p in kandydaci)))
    return next((p for p in kandydaci if p.stem == nazwa), kandydaci[0])


# --------------------------------------------------------------------------
def _wiersz_listy(p: pathlib.Path) -> str:
    try:
        dane = wczytaj(p)
    except ZlyPakiet as exc:
        return "  %-32s  ! %s" % (p.stem, str(exc).splitlines()[0][:70])
    opis = dane["pack"]
    hasla = len((dane.get("temat") or {}).get("hasla_szukania") or ())
    dziedzin = len((dane.get("temat") or {}).get("dziedziny") or ())
    return ("  %-32s  %-10s %2d hasel, %2d dziedzin\n      %s"
            % (p.stem, opis.get("language", "?"), hasla, dziedzin,
               str(opis.get("description", ""))[:88]))


def main(argv: list[str]) -> int:
    if not lista():
        print("Nie ma katalogu `packs/` albo jest pusty.")
        print("Wsad to jeden plik TOML z tematem — patrz packs/README.md")
        return 1

    if "--sprawdz" in argv:
        import config                                       # noqa: E402
        zle = 0
        for p in lista():
            try:
                gotowe, uwagi = waliduj(p)
                lamie = reguly_strukturalne(gotowe, config)
            except ZlyPakiet as exc:
                zle += 1
                print("  BLAD  %s" % p.stem)
                for w in str(exc).splitlines():
                    print("        %s" % w)
                continue
            if lamie:
                zle += 1
                print("  BLAD  %s" % p.stem)
                for w in lamie:
                    print("        %s" % w)
            else:
                print("  OK    %-30s %s" % (p.stem, "; ".join(uwagi)))
        print()
        print("=== %d wsadow, %d do poprawy ===" % (len(lista()), zle))
        return 1 if zle else 0

    if "--pokaz" in argv:
        nazwa = argv[argv.index("--pokaz") + 1]
        p = znajdz(nazwa)
        print(p.read_text(encoding="utf-8"))
        return 0

    if "--zastosuj" in argv:
        nazwa = argv[argv.index("--zastosuj") + 1]
        p = znajdz(nazwa)
        gotowe, _uwagi = waliduj(p)
        cel = KORZEN / "agent-v2" / "konfiguracja.toml"
        print("Wsad `%s` wpisalby do %s:" % (p.stem, cel))
        for sciezka in sorted(gotowe):
            wartosc = gotowe[sciezka]
            ile = len(wartosc) if isinstance(wartosc, (list, tuple, dict)) else 1
            print("   %-30s %s" % (sciezka, "%d pozycji" % ile
                                   if ile > 1 else repr(wartosc)[:60]))
        print()
        print("NIE ROBIE TEGO SAM. Wsad daje TEMAT, a plik konfiguracyjny ma")
        print("takze konto, pieniadze i wolumeny — nadpisanie go w ciemno")
        print("skasowaloby cudze decyzje. Wlascza go kreator:")
        print("   python narzedzia/kreator.py --wsad %s" % p.stem)
        return 0

    print("WSADY TEMATYCZNE — gotowy temat do podpiecia")
    print()
    for p in lista():
        print(_wiersz_listy(p))
    print()
    print("  python narzedzia/pakiety.py --pokaz <nazwa>")
    print("  python narzedzia/kreator.py --wsad <nazwa>")
    print()
    print("Wlasny wsad: packs/README.md mowi, co musi w nim byc i dlaczego.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except ZlyPakiet as exc:
        print("BLAD: %s" % exc)
        raise SystemExit(1)
