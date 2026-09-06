# -*- coding: utf-8 -*-
"""Kartridze: podlaczanie i odlaczanie presetow — wejscie operatora.

    python narzedzia/presety.py lista
    python narzedzia/presety.py nowy <nazwa>             # nowy kartridz z presety/SZABLON/
    python narzedzia/presety.py pokaz <nazwa>            # rozwiazane pola, ich pochodzenie, bloki
    python narzedzia/presety.py sprawdz [<nazwa>]        # bledy i uwagi, zero platnych wywolan
    python narzedzia/presety.py podglad <nazwa>          # briefy tak, jak zobaczy je model
    python narzedzia/presety.py podlacz <nazwa> [--instancja <id>]
    python narzedzia/presety.py odlacz
    python narzedzia/presety.py status
    python narzedzia/presety.py importuj-konfiguracje --nazwa <nazwa> [--opis "..."]
    python narzedzia/presety.py eksportuj <nazwa>        # znormalizowany TOML na stdout

Ten program NIE wczytuje aktywnego presetu do wlasnego procesu: przed
importem `config` ustawia `AGENT_V2_BEZ_KONFIGURACJI=1`, wiec pracuje na
neutralnym silniku i kazdy preset przymierza na KOPII. Dzieki temu `pokaz`
i `sprawdz` mowia o kartridzu, a nie o tym, co akurat jest podlaczone —
i dzialaja takze wtedy, gdy podlaczony preset jest zepsuty (`odlacz`, `status`).

Sam silnik czyta wskaznik przy kazdym starcie (`config.py`, koniec pliku).
Po `podlacz`/`odlacz` PROCESY TRZEBA URUCHOMIC OD NOWA — dzialajacy przebieg
trzyma stary kontekst do konca.
"""
from __future__ import annotations

import argparse
import os
import pathlib
import shutil
import subprocess
import sys

KORZEN = pathlib.Path(__file__).resolve().parent.parent
AGENT = KORZEN / "agent-v2"
sys.path.insert(0, str(AGENT))

# NEUTRALNY SILNIK W TYM PROCESIE — patrz naglowek.
os.environ["AGENT_V2_BEZ_KONFIGURACJI"] = "1"

import config          # noqa: E402
import konfiguracja    # noqa: E402
import preset          # noqa: E402

BAZA = dict(config.DOMYSLNE_SILNIKA)


def _wzgl(p: pathlib.Path) -> str:
    try:
        return pathlib.Path(p).resolve().relative_to(KORZEN).as_posix()
    except ValueError:
        return str(p)


def _wiersz(p: pathlib.Path, aktywny: str) -> str:
    nazwa = preset.nazwa_z_pliku(p)
    rodzaj = "katalog" if p.name == preset.NAZWA_PLIKU_PRESETU else "plik"
    try:
        pr = preset.wczytaj(p)
    except preset.BladPresetu as exc:
        return "  %-20s  %-7s  ! %s" % (nazwa, rodzaj, str(exc).splitlines()[0][:70])
    znak = "*" if pr.nazwa == aktywny else " "
    if nazwa == preset.NAZWA_SZABLONU:
        return "%s %-20s  %-7s  szablon — skopiuj: python narzedzia/presety.py nowy <nazwa>" % (
            znak, nazwa, rodzaj)
    return "%s %-20s  %-7s  %s" % (znak, pr.nazwa, rodzaj, (pr.opis or "")[:70])


def cmd_lista(args) -> int:
    pliki = preset.lista(AGENT)
    if not pliki:
        print("Nie ma zadnego presetu w presety/. Zacznij od szablonu:")
        print("  python narzedzia/presety.py nowy <nazwa>")
        return 1
    dane = None
    try:
        dane = preset.czytaj_wskaznik(AGENT)
    except preset.BladPresetu as exc:
        print("  ! wskaznik aktywacji: %s" % exc)
    aktywny = str((dane or {}).get("preset") or "")
    print("KARTRIDZE (* = podlaczony)")
    for p in pliki:
        print(_wiersz(p, aktywny))
    print()
    print("  python narzedzia/presety.py pokaz <nazwa>")
    print("  python narzedzia/presety.py podlacz <nazwa>")
    return 0


def cmd_nowy(args) -> int:
    nazwa = args.nazwa.strip()
    if not preset._WZORZEC_NAZWY.fullmatch(nazwa):
        print("nazwa %r: dozwolone male litery, cyfry, kropka, myslnik i podkreslenie" % nazwa)
        return 1
    szablon = preset.katalog_presetow(AGENT) / preset.NAZWA_SZABLONU
    if not (szablon / preset.NAZWA_PLIKU_PRESETU).is_file():
        print("brak szablonu: %s" % szablon)
        return 1
    cel = preset.katalog_presetow(AGENT) / nazwa
    if cel.exists():
        print("%s juz istnieje" % _wzgl(cel))
        return 1
    shutil.copytree(szablon, cel)
    plik = cel / preset.NAZWA_PLIKU_PRESETU
    tekst = plik.read_text(encoding="utf-8").replace('nazwa = "<<nazwa-presetu>>"',
                                                     'nazwa = %s' % konfiguracja.toml_wartosc(nazwa))
    plik.write_text(tekst, encoding="utf-8")
    print("utworzono %s/ z szablonu" % _wzgl(cel))
    print()
    print("DALEJ:")
    print("  1. wypelnij kazde <<...>> w %s" % _wzgl(plik))
    print("  2. wypelnij albo usun pliki w %s/prompty/ i %s/styl/" % (_wzgl(cel), _wzgl(cel)))
    print("  3. python narzedzia/presety.py sprawdz %s" % nazwa)
    print("  4. python narzedzia/presety.py podglad %s" % nazwa)
    print("  5. python narzedzia/presety.py podlacz %s" % nazwa)
    print()
    print("Kartridz w gicie nie laduje (presety/* jest ignorowane) — konto zostaje u Ciebie.")
    return 0


def _pokaz_wartosc(v) -> str:
    if isinstance(v, dict):
        return "%d pozycji" % len(v)
    if isinstance(v, (list, tuple)):
        if len(v) <= 6:
            return ", ".join(str(x) for x in v) or "(pusto)"
        return "%d pozycji: %s, ..." % (len(v), ", ".join(str(x) for x in v[:3]))
    tekst = str(v)
    return tekst if len(tekst) <= 88 else tekst[:85] + "..."


def cmd_pokaz(args) -> int:
    plik = preset.znajdz(args.nazwa, AGENT)
    pr = preset.wczytaj(plik)
    proba, meldunki = preset.rozwiaz(pr, config, BAZA)
    skad = preset.pochodzenie(pr, config, BAZA)
    print("KARTRIDZ %s   (%s)" % (pr.nazwa, _wzgl(plik)))
    if pr.opis:
        print("  %s" % pr.opis)
    print("  odcisk: %s   pol w pliku: %d   blokow promptow: %d"
          % (pr.odcisk[:16], len(pr.pola), len(pr.bloki)))
    print()
    print("ROZWIAZANE STALE (preset = z kartridza, silnik = domyslne)")
    for nazwa in konfiguracja.STALE_KONTA:
        if nazwa in ("MODEL_FOR", "PRESET_BLOKI") or not hasattr(proba, nazwa):
            continue
        print("  %-7s %-26s %s" % (skad.get(nazwa, "?"), nazwa,
                                   _pokaz_wartosc(getattr(proba, nazwa))))
    print()
    print("ROLE MODELI")
    for rola, model in sorted(getattr(proba, "MODEL_FOR", {}).items()):
        print("  %-7s %-20s %s" % (skad.get("MODEL_FOR[%s]" % rola, "?"), rola, model))
    print()
    print("BLOKI PROMPTOW (prompty/*.md)")
    for nazwa, opis in preset.BLOKI.items():
        stan = "%d znakow" % len(pr.bloki[nazwa]) if nazwa in pr.bloki else "brak (zdanie zastepcze)"
        print("  %-18s %-28s %s" % (nazwa, stan, opis[:60]))
    print()
    print("PLAN")
    print("  notki na dobe: %d   zwykly dzien: %s" % (
        getattr(proba, "NOTKI_DZIENNIE", 0), ", ".join(proba.NOTE_MIX_OTHER_DAY) or "-"))
    print("  dzien artykulu: %s" % (", ".join(proba.NOTE_MIX_ARTICLE_DAY) or "-"))
    print("  artykuly na tydzien: %d   dni: %s   godzina UTC: %s" % (
        proba.ARTYKULY_TYGODNIOWO, ", ".join(proba.DNI_ARTYKULU) or "-",
        proba.GODZINA_ARTYKULU_UTC))
    print("  przebiegi na dobe: %d   zegar UTC: %s" % (
        proba.PRZEBIEGOW_DZIENNIE, ", ".join(proba.GODZINY_PRZEBIEGOW_UTC)))
    print("  komentarze %s  polubienia %s  restacki %s  obserwacje/mies %s  subskrypcje/mies %s"
          % (proba.KOMENTARZE_DZIENNIE, proba.LAJKI_DZIENNIE, proba.RESTACK_DZIENNIE,
             proba.FOLLOW_MIESIECZNIE, proba.SUBSKRYPCJE_MIESIECZNIE))
    print("  sufity USD: miesiac %.2f  doba %.2f  przebieg %.2f" % (
        proba.MONTHLY_LIMIT_USD, proba.SUFIT_DZIENNY_BAZOWY, proba.RUN_LIMIT_USD))
    print("  okladka: %s   pisarz zapasowy: %s" % (
        proba.IMAGE_MODEL if proba.OBRAZ_WLACZONY else "wylaczona",
        proba.ZAPASOWY_PISARZ or "brak (zatrzymanie)"))
    print("  zrodla: %d kanalow YouTube, %d kanalow RSS, %d hostow preferowanych" % (
        len(proba.KANALY_YOUTUBE), len(proba.KANALY_RSS), len(proba.DOMENY_PREFEROWANE)))
    print("  styl: %s | %s | korpus: %s (%s)" % (
        pathlib.Path(proba.STYLE_PROFILE_POSITIVE).name,
        pathlib.Path(proba.STYLE_PROFILE_NEGATIVE).name,
        proba.STYLE_CORPUS, "wymagany" if proba.STYL_WYMAGAJ_KORPUSU else "opcjonalny"))
    bledy, uwagi = preset.sprawdz(pr, config, BAZA)
    _wypisz_sprawdzenie(bledy, uwagi)
    return 1 if bledy else 0


def _wypisz_sprawdzenie(bledy, uwagi) -> None:
    print()
    if bledy:
        print("BLEDY (kartridz nie zostanie podlaczony):")
        for b in bledy:
            print("  - %s" % b)
    else:
        print("BLEDY: brak")
    if uwagi:
        print("UWAGI (do przeczytania, nie blokuja):")
        for u in uwagi:
            print("  - %s" % u)


def cmd_sprawdz(args) -> int:
    pliki = [preset.znajdz(args.nazwa, AGENT)] if args.nazwa else preset.lista(AGENT)
    zle = 0
    for p in pliki:
        nazwa = preset.nazwa_z_pliku(p)
        try:
            pr = preset.wczytaj(p)
        except preset.BladPresetu as exc:
            zle += 1
            print("BLAD  %s\n  %s" % (nazwa, exc))
            continue
        bledy, uwagi = preset.sprawdz(pr, config, BAZA)
        print("%s %s   odcisk %s" % ("BLAD " if bledy else "OK   ", pr.nazwa, pr.odcisk[:12]))
        for b in bledy:
            print("    - %s" % b)
        for u in uwagi:
            print("    . %s" % u)
        zle += 1 if bledy else 0
    print()
    print("=== %d kartridzy, %d do poprawy ===" % (len(pliki), zle))
    return 1 if zle else 0


def cmd_podlacz(args) -> int:
    plik = preset.znajdz(args.nazwa, AGENT)
    poprzedni = None
    try:
        poprzedni = preset.czytaj_wskaznik(AGENT)
    except preset.BladPresetu:
        poprzedni = {"preset": "(nieczytelny wskaznik)"}
    try:
        akt, uwagi = preset.podlacz(plik, AGENT, config, BAZA, instancja=args.instancja,
                                    przejmij=bool(getattr(args, "przejmij", False)))
    except preset.BladPresetu as exc:
        print("NIE PODLACZONO: %s" % exc)
        if poprzedni:
            print("Poprzedni preset %r zostaje podlaczony bez zmian."
                  % poprzedni.get("preset"))
        return 1
    print("PODLACZONO %s" % akt.preset.nazwa)
    print("  plik:       %s" % _wzgl(akt.preset.plik))
    print("  odcisk:     %s" % akt.preset.odcisk[:16])
    print("  instancja:  %s   (aktywacja nr %d)" % (akt.instancja, akt.numer))
    print("  dane:       %s" % _wzgl(akt.katalog_danych))
    print("  bloki:      %s" % (", ".join(sorted(akt.preset.bloki)) or "brak"))
    if poprzedni and poprzedni.get("preset") != akt.preset.nazwa:
        print("  poprzedni:  %s — jego dane zostaja w swojej instancji, nietkniete"
              % poprzedni.get("preset"))
    for u in uwagi:
        print("  uwaga: %s" % u)
    print()
    print("DALEJ:")
    print("  1. zatrzymaj pracujace procesy i uruchom je od nowa — kontekst czyta sie przy starcie")
    print("  2. python narzedzia/jednostki.py --katalog <sciezka na serwerze> --uzytkownik <user>")
    print("     (zegary powstaja z harmonogramu tego kartridza)")
    print("  3. python agent-v2/alarm.py    # kontrola zdrowia z nowym kontekstem")
    return 0


def cmd_odlacz(args) -> int:
    dane = preset.odlacz(AGENT)
    if dane is None:
        print("Nic nie bylo podlaczone.")
        return 0
    print("ODLACZONO %s" % dane.get("preset", "?"))
    print("  dane instancji zostaja: %s" % dane.get("katalog_danych", "?"))
    print("  silnik bez kartridza ODMAWIA startu (run.py, artykul_z_puli.py).")
    print("  Zatrzymaj zegary: sudo systemctl disable --now nia-agent.timer nia-artykul.timer")
    return 0


def cmd_status(args) -> int:
    import os as _os
    if (_os.environ.get(preset.ZMIENNA) or "").strip():
        print("UWAGA: w srodowisku jest %s=%s — procesy z ta zmienna dzialaja w trybie "
              "PODGLADU (bez platnych wywolan i bez publikacji), niezaleznie od wskaznika."
              % (preset.ZMIENNA, _os.environ.get(preset.ZMIENNA)))
    try:
        dane = preset.czytaj_wskaznik(AGENT)
    except preset.BladPresetu as exc:
        print("WSKAZNIK ZEPSUTY: %s" % exc)
        return 1
    if dane is None:
        print("BRAK AKTYWNEGO PRESETU — silnik nie wystartuje.")
        if (AGENT / konfiguracja.NAZWA_PLIKU).exists():
            print("  Jest agent-v2/konfiguracja.toml (przy kartridzu NIE jest czytany).")
            print("  Zamien go w preset: python narzedzia/presety.py importuj-konfiguracje "
                  "--nazwa <nazwa>")
        print("  Podlacz kartridz: python narzedzia/presety.py lista")
        return 1
    print("AKTYWNY KARTRIDZ: %s" % dane.get("preset"))
    print("  plik:       %s" % dane.get("plik"))
    print("  instancja:  %s   (aktywacja nr %s, od %s)"
          % (dane.get("instancja"), dane.get("numer"), dane.get("aktywowano")))
    print("  dane:       %s" % dane.get("katalog_danych"))
    try:
        akt = preset.aktywacja(AGENT, srodowisko={})
        print("  odcisk:     %s — zgodny z plikami" % str(dane.get("odcisk"))[:16])
        bledy, uwagi = preset.sprawdz(akt.preset, config, BAZA)
        _wypisz_sprawdzenie(bledy, uwagi)
        return 1 if bledy else 0
    except preset.BladPresetu as exc:
        print("  ! %s" % exc)
        return 1


PODGLAD_SKRYPT = r'''
import json, pathlib, string, sys
sys.path.insert(0, %(agent)r)
import config, stages, style

class Domyslne(dict):
    def __missing__(self, k):
        return "<" + k + ">"

def render(nazwa):
    tekst = (config.PROMPTS_DIR / nazwa).read_text(encoding="utf-8")
    pola = Domyslne(stages._pola_wspolne())
    # PRZYPIETE PRZYKLADY STYLU renderowane tak, jak robi to stages.write():
    # podglad ma pokazac to, co pisarz naprawde dostanie, a nie znacznik.
    przyklady = style.przyklady_albo_pusto()
    pola["style_examples"] = (chr(10) * 2).join(
        "### " + e["function"] + chr(10) + e["text"] for e in przyklady
    ) or "(no pinned style examples for this publication)"
    return tekst.format_map(pola)

print("=" * 72)
print("KARTRIDZ %%s  instancja %%s  dane %%s" %% (
    config.PRESET.nazwa if config.PRESET else "-", config.INSTANCJA, config.DATA_DIR))
print("bloki z kartridza: %%s" %% (", ".join(sorted(config.PRESET_BLOKI)) or "brak"))
print("=" * 72)
print()
print("--- SCOUT_SYSTEM ---")
print(stages.SCOUT_SYSTEM)
print()
print("--- CURIOSITY_SYSTEM ---")
print(stages.CURIOSITY_SYSTEM)
print()
print("--- WRITER_SYSTEM ---")
print(stages.WRITER_SYSTEM)
print()
print("--- POLA WSPOLNE (bez bloku po_ludzku) ---")
for k, v in stages._pola_wspolne().items():
    if k == "po_ludzku":
        continue
    print("  %%-18s %%s" %% (k, str(v).replace(chr(10), " | ")[:160]))
print()
print("--- PROFILE STYLU ---")
poz, neg = style.load_profiles()
print(poz.splitlines()[0], "|", neg.splitlines()[0])
print("korpus:", config.STYLE_CORPUS, "| przyklady:", len(style.przyklady_albo_pusto()))
for nazwa in %(pliki)r:
    print()
    print("#" * 72)
    print("# %%s  (pola zadania jako <nazwa>)" %% nazwa)
    print("#" * 72)
    print(render(nazwa))
'''


def cmd_podglad(args) -> int:
    plik = preset.znajdz(args.nazwa, AGENT)
    pliki = args.prompty or ["skaut.md", "notka.md", "pisarz.md", "komentarz.md", "grafika.md"]
    srodowisko = dict(os.environ)
    srodowisko.pop("AGENT_V2_BEZ_KONFIGURACJI", None)
    srodowisko[preset.ZMIENNA] = str(plik)
    srodowisko["PYTHONIOENCODING"] = "utf-8"
    kod = PODGLAD_SKRYPT % {"agent": str(AGENT), "pliki": pliki}
    wynik = subprocess.run([sys.executable, "-c", kod], cwd=str(KORZEN), env=srodowisko,
                           capture_output=True, text=True, encoding="utf-8")
    sys.stdout.write(wynik.stdout)
    if wynik.returncode != 0:
        sys.stdout.write(wynik.stderr[-3000:])
    return wynik.returncode


def cmd_importuj(args) -> int:
    zrodlo = pathlib.Path(args.plik) if args.plik else AGENT / konfiguracja.NAZWA_PLIKU
    if not zrodlo.exists():
        print("nie ma %s" % zrodlo)
        return 1
    tekst = preset.z_konfiguracji(zrodlo.read_text(encoding="utf-8"), args.nazwa, args.opis)
    pr = preset.wczytaj_tekst(tekst, zrodlo.name)          # literowka wychodzi TERAZ
    cel = preset.katalog_presetow(AGENT) / args.nazwa / preset.NAZWA_PLIKU_PRESETU
    if cel.exists() and not args.nadpisz:
        print("%s juz istnieje — dodaj --nadpisz, zeby go zastapic" % _wzgl(cel))
        return 1
    cel.parent.mkdir(parents=True, exist_ok=True)
    cel.write_text(tekst, encoding="utf-8")
    print("zapisano %s  (%d pol, odcisk %s)" % (_wzgl(cel), len(pr.pola), pr.odcisk[:12]))
    print("  bez prompty/ i styl/ — dodaj je z presety/SZABLON/, jesli chcesz wlasne bloki i profile")
    bledy, uwagi = preset.sprawdz(preset.wczytaj(cel), config, BAZA)
    _wypisz_sprawdzenie(bledy, uwagi)
    print()
    print("Podlacz: python narzedzia/presety.py podlacz %s" % args.nazwa)
    return 1 if bledy else 0


def cmd_eksportuj(args) -> int:
    pr = preset.wczytaj(preset.znajdz(args.nazwa, AGENT))
    sys.stdout.write(preset.eksportuj(pr))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="polecenie")
    sub.add_parser("lista").set_defaults(f=cmd_lista)
    p = sub.add_parser("nowy"); p.add_argument("nazwa"); p.set_defaults(f=cmd_nowy)
    p = sub.add_parser("pokaz"); p.add_argument("nazwa"); p.set_defaults(f=cmd_pokaz)
    p = sub.add_parser("sprawdz"); p.add_argument("nazwa", nargs="?"); p.set_defaults(f=cmd_sprawdz)
    p = sub.add_parser("podlacz"); p.add_argument("nazwa")
    p.add_argument("--instancja", default=None,
                   help="identyfikator instancji (domyslnie: nazwa presetu; inna nazwa = "
                        "swiezy katalog danych)")
    p.set_defaults(f=cmd_podlacz)
    sub.add_parser("odlacz").set_defaults(f=cmd_odlacz)
    sub.add_parser("status").set_defaults(f=cmd_status)
    p.add_argument("--przejmij", action="store_true",
                   help="przejmij istniejacy katalog instancji innego presetu lub konta "
                        "(domyslnie odmowa: nowa redakcja = nowa instancja)")
    p = sub.add_parser("podglad"); p.add_argument("nazwa")
    p.add_argument("--prompty", nargs="*", default=None,
                   help="ktore briefy wyrenderowac (domyslnie skaut, notka, pisarz, komentarz, grafika)")
    p.set_defaults(f=cmd_podglad)
    p = sub.add_parser("importuj-konfiguracje"); p.add_argument("--nazwa", required=True)
    p.add_argument("--opis", default="")
    p.add_argument("--plik", default="", help="domyslnie agent-v2/konfiguracja.toml")
    p.add_argument("--nadpisz", action="store_true")
    p.set_defaults(f=cmd_importuj)
    p = sub.add_parser("eksportuj"); p.add_argument("nazwa"); p.set_defaults(f=cmd_eksportuj)
    args = ap.parse_args(argv)
    if not args.polecenie:
        ap.print_help()
        return 1
    try:
        return args.f(args)
    except preset.BladPresetu as exc:
        print("BLAD: %s" % exc)
        return 1


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:                                           # noqa: BLE001
        pass
    raise SystemExit(main())
