# -*- coding: utf-8 -*-
"""Jednostki systemd DLA TEJ INSTALACJI — sciezka, uzytkownik i marka z konfiguracji.

## Po co to istnieje

`agent-v2/systemd/*.service` mialy wpisane na sztywno trzy rzeczy, ktore naleza
do INSTALACJI, a nie do bota:

    WorkingDirectory=/home/ubuntu/nia-substack-bot          (x3)
    ExecStart=/home/ubuntu/nia-substack-bot/.venv/bin/...   (x3)
    User=ubuntu                                             (x3)
    Description=Your Publication — agent                     (x6)

Konto skonfigurowane wlasna nazwa i postawione w innym katalogu dostawalo wiec
szesc plikow, ktore albo nie startuja, albo w `systemctl status` przedstawiaja
sie cudza nazwa. Konfigurator pytal o nazwe marki i nic z nia w tym miejscu nie
robil — a to jest to samo, co `FETCH_USER_AGENT` przed poprawka: wartosc
z konfiguracji, ktora nie dochodzi tam, gdzie jest widoczna.

## Czym to NIE jest

To nie jest druga kopia jednostek. Pliki w `agent-v2/systemd/` sa ZRODLEM
i to one sa czytane przez testy (`test_czas.py`, `test_rytm.py`,
`test_jednostki_systemd.py`) oraz przez `norma.py`. Ten program tylko je
PRZEPISUJE, podstawiajac trzy wartosci, i robi to za kazdym uruchomieniem —
wynik jest wytworem, nie drugim zrodlem. Katalog wynikowy jest w `.gitignore`.

## Co dokladnie podstawia

  * KATALOG INSTALACJI — wszedzie, gdzie w szablonie stoi `WorkingDirectory`.
    Podstawiamy przez zamiane NAPISU, a nie przez przepisanie jednej linii, bo
    ta sama sciezka stoi takze w `ExecStart` (raz jako katalog, raz jako
    `.venv/bin/python`) i rozjazd miedzy nimi daje usluge, ktora startuje
    w dobrym katalogu i wola nieistniejacego Pythona.
  * UZYTKOWNIKA — linia `User=`.
  * MARKE — czesc `Description=` przed „ — ". Wszystkie szesc jednostek ma ten
    sam ksztalt `MARKA — rola` wlasnie po to, zeby nie trzeba tu bylo listy
    wyjatkow.

Nazwy PLIKOW zostaja. Zmiana ich wymagalaby zmiany w `test_czas.py`,
`test_rytm.py` i w `docs/INSTALL.md`, a nic za to nie daje: systemd nie wiaze
nazwy jednostki z niczym poza para `.service`/`.timer`, a `norma.py` szuka
zegara po TRESCI (`ExecStart` wolajacy `run.py`), nie po nazwie.

## Uruchomienie

    python narzedzia/jednostki.py                 # do agent-v2/systemd/dla-tej-instalacji/
    python narzedzia/jednostki.py --katalog /srv/bot --uzytkownik bot
    python narzedzia/jednostki.py --pokaz         # wypisz na ekran, nie zapisuj

Bez argumentow katalog instalacji to korzen repozytorium, a uzytkownik — ten,
ktory stoi w szablonie. Sluzy to jednemu: zeby dalo sie zobaczyc, co wyjdzie,
zanim poda sie prawdziwe wartosci.
"""
from __future__ import annotations

import argparse
import pathlib
import sys

KORZEN = pathlib.Path(__file__).resolve().parent.parent
SZABLONY = KORZEN / "agent-v2" / "systemd"
DOMYSLNY_WYNIK = SZABLONY / "dla-tej-instalacji"

sys.path.insert(0, str(KORZEN / "agent-v2"))


def _wartosc(tresc: str, klucz: str) -> str:
    """Wartosc pierwszej linii `klucz=...`, albo pusty napis."""
    for linia in tresc.splitlines():
        if linia.startswith(klucz + "="):
            return linia.split("=", 1)[1].strip()
    return ""


def katalog_szablonu() -> str:
    """Katalog instalacji wpisany w szablony — do podmiany.

    Bierzemy go z `WorkingDirectory` PIERWSZEJ uslugi, ktora go ma, i zadamy
    potem, zeby wszystkie mialy ten sam. Szablony z dwoma roznymi katalogami
    znaczylyby, ze ktos poprawil jeden plik z trzech — a wtedy podstawianie
    napisu przemilczaloby polowe roboty.
    """
    katalogi = set()
    for p in sorted(SZABLONY.glob("*.service")):
        w = _wartosc(p.read_text(encoding="utf-8"), "WorkingDirectory")
        if w:
            katalogi.add(w)
    if len(katalogi) > 1:
        raise SystemExit(
            "szablony podaja ROZNE katalogi instalacji: %s\n"
            "Podstawianie napisu przemilczaloby czesc z nich — zrownaj je "
            "recznie w agent-v2/systemd/." % ", ".join(sorted(katalogi)))
    return katalogi.pop() if katalogi else ""


def uzytkownik_szablonu() -> str:
    for p in sorted(SZABLONY.glob("*.service")):
        u = _wartosc(p.read_text(encoding="utf-8"), "User")
        if u:
            return u
    return ""


def podstaw(tresc: str, katalog_stary: str, katalog_nowy: str,
            uzytkownik_stary: str, uzytkownik_nowy: str, marka: str) -> str:
    """Jedna jednostka z podstawionymi trzema wartosciami."""
    if katalog_stary and katalog_nowy and katalog_stary != katalog_nowy:
        tresc = tresc.replace(katalog_stary, katalog_nowy)
    if uzytkownik_stary and uzytkownik_nowy and uzytkownik_stary != uzytkownik_nowy:
        tresc = "\n".join(
            ("User=" + uzytkownik_nowy) if w.startswith("User=") else w
            for w in tresc.split("\n"))
    if marka:
        wyjscie = []
        for w in tresc.split("\n"):
            if w.startswith("Description=") and " — " in w:
                rola = w.split(" — ", 1)[1]
                wyjscie.append("Description=%s — %s" % (marka, rola))
            else:
                wyjscie.append(w)
        tresc = "\n".join(wyjscie)
    return tresc


def zbuduj(katalog: str, uzytkownik: str, marka: str) -> dict[str, str]:
    """Nazwa pliku -> tresc jednostki dla tej instalacji."""
    stary_katalog = katalog_szablonu()
    stary_uzytkownik = uzytkownik_szablonu()
    wynik = {}
    for p in sorted(SZABLONY.iterdir()):
        if p.suffix not in (".service", ".timer") or not p.is_file():
            continue
        wynik[p.name] = podstaw(p.read_text(encoding="utf-8"),
                                stary_katalog, katalog,
                                stary_uzytkownik, uzytkownik, marka)
    return wynik


def main() -> int:
    import config  # noqa: E402  — po sys.path

    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--katalog", default=str(KORZEN),
                    help="katalog instalacji na serwerze (domyslnie: korzen repo)")
    ap.add_argument("--uzytkownik", default="",
                    help="uzytkownik systemowy (domyslnie: ten z szablonu)")
    ap.add_argument("--marka", default="",
                    help="nazwa w Description (domyslnie: konto.nazwa_marki)")
    ap.add_argument("--wynik", default=str(DOMYSLNY_WYNIK),
                    help="katalog wynikowy")
    ap.add_argument("--pokaz", action="store_true",
                    help="wypisz na ekran i nie zapisuj niczego")
    args = ap.parse_args()

    katalog = args.katalog.replace("\\", "/").rstrip("/")

    # GIT BASH NA WINDOWS PRZEPISUJE SCIEZKI W ARGUMENTACH, i robi to ZANIM
    # ten program cokolwiek zobaczy: `--katalog /srv/bot` dochodzi tu jako
    # `C:/Program Files/Git/srv/bot`. Jednostka wychodzi wtedy skladniowo
    # poprawna i cicho zla — a to najgorszy rodzaj bledu w pliku, ktory ktos
    # skopiuje na serwer i wlaczy. Sprawdzamy odcisk palca tej zamiany.
    if "/Git/" in katalog or katalog.lower().startswith("c:/program files"):
        print("!! SCIEZKA WYGLADA NA PRZEPISANA PRZEZ GIT BASH:")
        print("     %s" % katalog)
        print("   Uruchom to samo z `MSYS_NO_PATHCONV=1` na poczatku wiersza,")
        print("   albo podaj sciezke z podwojnym ukosnikiem (`//srv/bot`).")
        print("   Nic nie zapisano.")
        return 1
    uzytkownik = args.uzytkownik or uzytkownik_szablonu()
    marka = args.marka or config.NAZWA_MARKI

    jednostki = zbuduj(katalog, uzytkownik, marka)
    if not jednostki:
        print("nie ma z czego budowac: %s jest puste" % SZABLONY)
        return 1

    if args.pokaz:
        for nazwa, tresc in jednostki.items():
            print("=" * 72)
            print("# %s" % nazwa)
            print("=" * 72)
            print(tresc)
        return 0

    kat = pathlib.Path(args.wynik)
    kat.mkdir(parents=True, exist_ok=True)
    for nazwa, tresc in jednostki.items():
        (kat / nazwa).write_text(tresc, encoding="utf-8")

    print("zapisano %d jednostek w %s" % (len(jednostki), kat))
    print()
    print("  katalog instalacji : %s" % katalog)
    print("  uzytkownik         : %s" % (uzytkownik or "(z szablonu)"))
    print("  marka w Description: %s" % marka)
    print()
    print("SPRAWDZ PRZED WGRANIEM — te trzy rzeczy musza istniec NA SERWERZE:")
    print("  %s/.venv/bin/python" % katalog)
    print("  %s/agent-v2/run.py" % katalog)
    print("  uzytkownik %s ma prawo czytac %s" % (uzytkownik or "?", katalog))
    print()
    print("Potem, na serwerze:")
    print("  sudo cp %s/* /etc/systemd/system/" % kat)
    print("  sudo systemctl daemon-reload")
    print("  sudo systemctl enable --now %s"
          % " ".join(sorted(n for n in jednostki if n.endswith(".timer"))))
    print()
    print("  NIE `enable` uslug (`.service`) — sa typu oneshot i maja jedno")
    print("  wejscie: swoj zegar. Patrz komentarz w agent-v2/systemd/.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
