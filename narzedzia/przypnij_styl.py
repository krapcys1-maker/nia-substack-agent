# -*- coding: utf-8 -*-
"""Przypina korpus stylu: liczy skroty i zapisuje `przypiecia.json`.

## Po co to istnieje

Korpus stylu jest jedyna rzecza, ktora odroznia to konto od tysiaca innych,
i `style.py` odmawia pracy, jesli korpus nie zgadza sie z przypietym skrotem.
To zabezpieczenie jest sluszne i zostaje. Problem byl inny: SAM KORPUS lezal
w repozytorium.

Do 2026-09-03 w `agent-v2/prompts/styl/` lezalo 9383 slowa cudzej,
opublikowanej publicystyki — felietony konkretnego autora, przepisane co do
znaku — a repozytorium jest publiczne. To nie jest kwestia higieny nazw:
to rozpowszechnianie cudzego utworu. Korpus wyszedl wiec z gita, a razem
z nim skroty, ktore go opisywaly.

## Jak sie tego uzywa

  1. Wrzuc plik `.txt` z tekstami, ktorych glos ma nasladowac pisarz —
     WLASNYMI albo takimi, do ktorych masz prawa (domena publiczna, CC BY).
     Akapity oddzielone pusta linia. Miejsce: `styl/korpus.txt` w katalogu
     kartridza (pole `styl.korpus` w preset.toml) albo, bez kartridza,
     `agent-v2/prompts/styl/`.
  2. Uruchom `python narzedzia/przypnij_styl.py --korpus presety/<nazwa>/styl/korpus.txt --pokaz`,
     zeby zobaczyc ponumerowane akapity z dlugosciami.
  3. Wybierz po jednym akapicie na funkcje retoryczna i uruchom:

     python narzedzia/przypnij_styl.py --korpus ... --wybor OPENING=65,MECHANISM=60,...

     Zapisze `przypiecia.json` obok korpusu. Korpus w `agent-v2/prompts/styl/`
     jest w `.gitignore`; korpus kartridza jest w gicie tylko wtedy, gdy
     licencja tekstow na to pozwala — i wtedy obok lezy manifest zrodel.

## Czego to NIE robi

Nie wybiera akapitow za ciebie. Ktory fragment pokazuje otwarcie, a ktory
kontrargument, jest decyzja redakcyjna i narzedzie nie ma o niej pojecia.
Bez `--wybor` program tylko pokazuje kandydatow i konczy.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

KORZEN = pathlib.Path(__file__).resolve().parent.parent
KATALOG = KORZEN / "agent-v2" / "prompts" / "styl"
NAZWA_PRZYPIEC = "przypiecia.json"

# Funkcje retoryczne, ktorych pisarz oczekuje. Kolejnosc ma znaczenie tylko
# dla wypisu; `style.py` czyta je po nazwie.
FUNKCJE = ("OPENING", "CONCRETE_TO_SYSTEM", "MECHANISM", "COUNTERARGUMENT",
           "ENDING")

MIN_ZNAKOW = 150
MAX_ZNAKOW = 900


def bajty_kanoniczne(raw: bytes) -> bytes:
    """Ta sama normalizacja, ktorej uzywa `style.bajty_kanoniczne`.

    Tylko zakonczenia linii. Kazda inna roznica bajtowa ma zatrzymac pisarza —
    korpus podmieniony po cichu to glos, na ktory nikt sie nie zgodzil.
    """
    return raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def akapity(raw: bytes) -> tuple[str, ...]:
    tekst = bajty_kanoniczne(raw).decode("utf-8")
    bloki = [b.strip() for b in tekst.split("\n\n")]
    return tuple(b for b in bloki if b)


def znajdz_korpus(wskazany: str = "") -> pathlib.Path:
    """Korpus wskazany wprost (`--korpus`) albo jedyny .txt w katalogu domyslnym."""
    if wskazany:
        plik = pathlib.Path(wskazany)
        if not plik.is_file():
            sys.exit("Nie ma takiego korpusu: %s" % plik)
        return plik.resolve()
    pliki = sorted(p for p in KATALOG.glob("*.txt") if p.is_file())
    if not pliki:
        sys.exit(
            "Nie ma korpusu stylu w %s\n"
            "Wrzuc tam plik .txt z tekstami, ktorych glos ma nasladowac pisarz —\n"
            "wlasnymi albo takimi, do ktorych masz prawa. Akapity oddzielone\n"
            "pusta linia. Szczegoly: %s/README.md" % (KATALOG, KATALOG))
    if len(pliki) > 1:
        sys.exit("W %s lezy wiecej niz jeden .txt: %s\nZostaw jeden."
                 % (KATALOG, ", ".join(p.name for p in pliki)))
    return pliki[0]


def _wzgledna(p: pathlib.Path) -> str:
    try:
        return str(p.relative_to(KORZEN))
    except ValueError:
        return str(p)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pokaz", action="store_true",
                    help="wypisz ponumerowane akapity i zakoncz")
    ap.add_argument("--wybor", default="",
                    help="FUNKCJA=numer, po przecinku, dla kazdej z: %s"
                         % ", ".join(FUNKCJE))
    ap.add_argument("--korpus", default="",
                    help="sciezka do korpusu (.txt); domyslnie jedyny .txt w %s"
                         % KATALOG.relative_to(KORZEN))
    args = ap.parse_args()

    plik = znajdz_korpus(args.korpus)
    raw = plik.read_bytes()
    bloki = akapity(raw)
    print("korpus: %s" % _wzgledna(plik))
    print("akapitow: %d" % len(bloki))

    if args.pokaz or not args.wybor:
        print()
        print("Kandydaci (tylko te miedzy %d a %d znakami nadaja sie na przyklad):"
              % (MIN_ZNAKOW, MAX_ZNAKOW))
        for i, b in enumerate(bloki):
            if not MIN_ZNAKOW <= len(b) <= MAX_ZNAKOW:
                continue
            pierwsza = " ".join(b.split())[:96]
            print("  %4d  %4d zn.  %s" % (i, len(b), pierwsza))
        if not args.wybor:
            print()
            print("Teraz wybierz po jednym na funkcje, np.:")
            print("  python narzedzia/przypnij_styl.py --wybor %s"
                  % ",".join("%s=<numer>" % f for f in FUNKCJE))
        return 0

    wybor: dict[str, int] = {}
    for kawalek in args.wybor.split(","):
        if "=" not in kawalek:
            sys.exit("--wybor: oczekiwano FUNKCJA=numer, jest %r" % kawalek)
        nazwa, numer = kawalek.split("=", 1)
        nazwa = nazwa.strip().upper()
        if nazwa not in FUNKCJE:
            sys.exit("--wybor: nieznana funkcja %r. Znane: %s"
                     % (nazwa, ", ".join(FUNKCJE)))
        try:
            wybor[nazwa] = int(numer)
        except ValueError:
            sys.exit("--wybor: %r nie jest numerem akapitu" % numer)

    brak = [f for f in FUNKCJE if f not in wybor]
    if brak:
        sys.exit("--wybor: brakuje funkcji: %s\n"
                 "Pisarz oczekuje wszystkich pieciu." % ", ".join(brak))

    przyklady = []
    for funkcja in FUNKCJE:
        i = wybor[funkcja]
        if not 0 <= i < len(bloki):
            sys.exit("%s=%d: korpus ma %d akapitow (0-%d)"
                     % (funkcja, i, len(bloki), len(bloki) - 1))
        tekst = bloki[i]
        if not MIN_ZNAKOW <= len(tekst) <= MAX_ZNAKOW:
            sys.exit("%s=%d: akapit ma %d znakow, poza %d-%d.\n"
                     "Fragment ma pokazywac RUCH, nie byc fraza do przepisania."
                     % (funkcja, i, len(tekst), MIN_ZNAKOW, MAX_ZNAKOW))
        przyklady.append({
            "funkcja": funkcja,
            "akapit": i,
            "skrot": hashlib.sha256(tekst.encode("utf-8")).hexdigest()[:10],
        })

    dane = {
        "plik": plik.name,
        "korpus_sha256": hashlib.sha256(bajty_kanoniczne(raw)).hexdigest(),
        "akapitow": len(bloki),
        "przyklady": przyklady,
    }
    # PRZYPIECIA LEZA OBOK KORPUSU — tak je znajduje `style._plik_przypiec()`.
    cel = plik.parent / NAZWA_PRZYPIEC
    cel.write_text(json.dumps(dane, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print()
    print("zapisano %s" % _wzgledna(cel))
    print("  korpus_sha256: %s" % dane["korpus_sha256"])
    for p in przyklady:
        print("  %-20s akapit %4d  skrot %s" % (p["funkcja"], p["akapit"], p["skrot"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
