# -*- coding: utf-8 -*-
"""Preset: jeden plik z CALA redakcja, podlaczany i odlaczany jednym poleceniem.

## Po co to istnieje

Audyt z 5 wrzesnia 2026 (`analizy/2026-09-05-czystosc-presety/RAPORT.md`)
stwierdzil, ze bot jest jedna skonfigurowana instalacja, a nie silnikiem,
do ktorego podlacza sie preset i potem go wyjmuje: `konfiguracja.toml`
nakladal sie na poprzednie wartosci (T02), miks notek zmienial tylko zwykly
dzien (T04), zegar siedzial w szablonach systemd (W2), styl w plikach o stalych
nazwach (C4), a brak pliku konfiguracji przywracal wbudowany temat zamiast
zatrzymac bota (C1). Nie bylo operacji „odlacz i zostan pusty".

Ten modul wprowadza cztery rzeczy, ktore audyt nazwal granica architektoniczna:

  SILNIK      — kod w `agent-v2/` i jego wartosci domyslne. Nie zna konta.
  PRESET      — plik `presety/<nazwa>.toml`: naglowek `[preset]` plus komplet
                pol z `konfiguracja.POLA` (temat, styl, zrodla, modele,
                wolumeny, harmonogram, pieniadze). Ma ODCISK (sha256 pol).
  INSTANCJA   — katalog `agent-v2/instancje/<nazwa>/`: baza, bank, cache,
                szkice, promocje TEGO presetu. Inny preset ma inny katalog.
  AKTYWACJA   — plik `agent-v2/aktywny_preset.json`: ktory preset, z jakim
                odciskiem, w ktorej instancji, ktory raz. Jedyne, co czyta
                `config.py` przy starcie.

## Co sie dzieje przy podlaczeniu

`podlacz` czyta preset, sprawdza go W CALOSCI bez platnych wywolan (pola,
pliki stylu, dostawcy modeli, spojnosc zegara), zaklada katalog instancji
i ATOMOWO zapisuje wskaznik aktywacji. Nic nie jest kopiowane do
`konfiguracja.toml`; nic nie jest nakladane na poprzedni preset.

Przy KAZDYM starcie `config.py` robi to samo w druga strone: czyta wskaznik,
wczytuje preset z pliku, porownuje odcisk (preset zmieniony po aktywacji
zatrzymuje start — ma byc podlaczony jeszcze raz, swiadomie), przywraca
neutralna baze silnika i dopiero na nia naklada pola presetu. Dzieki temu
preset B skompilowany po A daje ten sam kontekst co B na czystym silniku.

## Co sie dzieje przy odlaczeniu

`odlacz` usuwa wskaznik. Katalog instancji ZOSTAJE (bank, szkice, cache,
baza) i da sie go wznowic przez ponowne `podlacz` tego samego presetu.
Bez aktywnego presetu `run.py` i `artykul_z_puli.py` ODMAWIAJA startu —
patrz `wymagaj_aktywnego`. Nie ma juz stanu „wrocil do wbudowanego tematu".

## Czego ten modul NIE robi

Nie importuje `config` na poziomie modulu — `config.py` importuje JEGO, wiec
kazda funkcja dostaje modul konfiguracji jako argument (`cfg`), tak samo jak
`konfiguracja.zastosuj`. Nie dotyka sieci, modeli ani przegladarki. Nie
przenosi sekretow: klucze zostaja w `.env`, sesja w katalogu danych.

## Uzycie

    python narzedzia/presety.py lista
    python narzedzia/presety.py sprawdz ai
    python narzedzia/presety.py podlacz ai
    python narzedzia/presety.py status
    python narzedzia/presety.py odlacz

Podglad promptow z presetem, bez podlaczania:  `AGENT_V2_PRESET=presety/ai.toml`.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import sys
import tempfile
import types
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import konfiguracja

SCHEMA = 1
NAZWA_WSKAZNIKA = "aktywny_preset.json"
NAZWA_KATALOGU_INSTANCJI = "instancje"
NAZWA_KATALOGU_PRESETOW = "presety"
NAZWA_PRZYKLADOW = "przyklady"
NAZWA_DZIENNIKA = "aktywacje.jsonl"

# Sciezka do pliku presetu podana srodowiskiem — do PODGLADU i TESTOW. Ma
# pierwszenstwo przed wskaznikiem, dziala takze bez `podlacz` i nie tworzy
# wskaznika. Katalog danych to `instancje/podglad-<nazwa>`, zeby podglad nie
# dotykal danych zadnej prawdziwej instancji.
ZMIENNA = "AGENT_V2_PRESET"

# Pola naglowka `[preset]`. Zamkniete: literowka w naglowku tez ma byc bledem.
META_DOZWOLONE = ("nazwa", "opis", "wersja", "schema", "autor", "utworzono",
                  "na_podstawie")
_WZORZEC_NAZWY = re.compile(r"[a-z0-9][a-z0-9._-]{0,62}")


class BladPresetu(RuntimeError):
    """Preset jest zly i NIE MA byc podlaczony ani uruchomiony."""


class BrakPresetu(RuntimeError):
    """Nic nie jest podlaczone — silnik nie ma na czym pracowac."""


@dataclass(frozen=True)
class Preset:
    nazwa: str
    plik: Path
    opis: str
    wersja: str
    schema: int
    pola: dict[str, Any]
    odcisk: str


@dataclass(frozen=True)
class Aktywacja:
    preset: Preset
    instancja: str
    katalog_danych: Path
    numer: int
    aktywowano: str
    zrodlo: str            # "wskaznik" albo "srodowisko"


# ---------------------------------------------------------------------------
# sciezki
# ---------------------------------------------------------------------------
def korzen(agent_dir: Path) -> Path:
    return Path(agent_dir).resolve().parent


def katalog_presetow(agent_dir: Path) -> Path:
    return korzen(agent_dir) / NAZWA_KATALOGU_PRESETOW


def katalog_instancji(agent_dir: Path) -> Path:
    return Path(agent_dir).resolve() / NAZWA_KATALOGU_INSTANCJI


def wskaznik(agent_dir: Path) -> Path:
    return Path(agent_dir).resolve() / NAZWA_WSKAZNIKA


def _wzgledna(p: Path, baza: Path) -> str:
    """Sciezka wzgledem `baza` (posix), a gdy lezy poza nia — bezwzgledna."""
    try:
        return Path(p).resolve().relative_to(Path(baza).resolve()).as_posix()
    except ValueError:
        return Path(p).resolve().as_posix()


def _bezwzgledna(napis: str, baza: Path) -> Path:
    p = Path(napis)
    return p if p.is_absolute() else Path(baza).resolve() / p


# ---------------------------------------------------------------------------
# odcisk i wczytanie
# ---------------------------------------------------------------------------
def _kanoniczne(x: Any) -> Any:
    if isinstance(x, dict):
        return {str(k): _kanoniczne(v) for k, v in sorted(x.items())}
    if isinstance(x, (list, tuple)):
        return [_kanoniczne(v) for v in x]
    if isinstance(x, Path):
        return x.as_posix()
    return x


def odcisk(pola: dict[str, Any], schema: int = SCHEMA) -> str:
    """SHA-256 rozwiazanych pol. Zmiana dowolnej wartosci zmienia odcisk."""
    tekst = json.dumps({"schema": schema, "pola": _kanoniczne(pola)},
                       sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(tekst.encode("utf-8")).hexdigest()


def wczytaj_tekst(tekst: str, nazwa_pliku: str, plik: Path | None = None) -> Preset:
    """Tekst TOML presetu -> `Preset`. Kazdy blad to `BladPresetu`."""
    if sys.version_info < (3, 11):
        raise BladPresetu(
            "%s: czytanie presetu wymaga Pythona 3.11 lub nowszego (masz %d.%d)"
            % (nazwa_pliku, sys.version_info[0], sys.version_info[1]))
    import tomllib

    try:
        dane = tomllib.loads(tekst)
    except Exception as exc:                                    # noqa: BLE001
        raise BladPresetu("%s nie jest poprawnym TOML-em (%s: %s)"
                          % (nazwa_pliku, type(exc).__name__, exc))
    meta = dane.get("preset")
    if not isinstance(meta, dict):
        raise BladPresetu(
            "%s nie ma sekcji [preset]. Plik bez naglowka jest zwykla "
            "konfiguracja — zamien go poleceniem `python narzedzia/presety.py "
            "importuj-konfiguracje --nazwa <nazwa>`." % nazwa_pliku)
    obce = sorted(set(meta) - set(META_DOZWOLONE))
    if obce:
        raise BladPresetu("%s: [preset] ma pola spoza listy: %s (dozwolone: %s)"
                          % (nazwa_pliku, ", ".join(obce), ", ".join(META_DOZWOLONE)))
    nazwa = str(meta.get("nazwa") or "").strip()
    if not _WZORZEC_NAZWY.fullmatch(nazwa):
        raise BladPresetu(
            "%s: [preset].nazwa = %r — dozwolone male litery, cyfry, kropka, "
            "myslnik i podkreslenie (nazwa jest tez nazwa katalogu instancji)"
            % (nazwa_pliku, nazwa))
    schema = meta.get("schema", SCHEMA)
    if isinstance(schema, bool) or not isinstance(schema, int) or schema != SCHEMA:
        raise BladPresetu("%s: [preset].schema = %r, a ten silnik czyta schema = %d"
                          % (nazwa_pliku, schema, SCHEMA))
    for pole in ("opis", "wersja", "autor", "utworzono", "na_podstawie"):
        if pole in meta and not isinstance(meta[pole], str):
            raise BladPresetu("%s: [preset].%s musi byc napisem" % (nazwa_pliku, pole))

    reszta = {k: v for k, v in dane.items() if k != "preset"}
    try:
        pola = konfiguracja.sprawdz_plaskie(
            konfiguracja.splaszcz(reszta, nazwa_pliku), nazwa_pliku)
    except konfiguracja.BledKonfiguracji as exc:
        raise BladPresetu(str(exc))
    return Preset(nazwa=nazwa, plik=Path(plik) if plik else Path(nazwa_pliku),
                  opis=str(meta.get("opis") or "").strip(),
                  wersja=str(meta.get("wersja") or "").strip(),
                  schema=schema, pola=pola, odcisk=odcisk(pola, schema))


def wczytaj(plik: Path) -> Preset:
    plik = Path(plik)
    if not plik.exists():
        raise BladPresetu("nie ma pliku presetu: %s" % plik)
    return wczytaj_tekst(plik.read_text(encoding="utf-8"), plik.name, plik)


# ---------------------------------------------------------------------------
# proba zastosowania — na KOPII konfiguracji, nie na zywym module
# ---------------------------------------------------------------------------
def proba_konfiguracji(cfg: Any, baza: dict[str, Any] | None = None) -> types.SimpleNamespace:
    """Kopia stalych `config` do bezpiecznego przymierzenia presetu.

    Kazda stala WIELKIMI literami jest kopiowana glebo; funkcje i moduly
    zostaja za burta. `baza` (zdjecie neutralnego silnika) nadpisuje stale
    konta, zeby proba nie dziedziczyla niczego po aktywnym presecie.
    """
    proba = types.SimpleNamespace()
    for nazwa in dir(cfg):
        if not nazwa.isupper() or nazwa.startswith("_"):
            continue
        wartosc = getattr(cfg, nazwa)
        if isinstance(wartosc, types.ModuleType) or callable(wartosc):
            continue
        try:
            setattr(proba, nazwa, copy.deepcopy(wartosc))
        except Exception:                                       # noqa: BLE001
            continue
    for nazwa in ("REPO_ROOT", "AGENT_DIR"):
        if hasattr(cfg, nazwa):
            setattr(proba, nazwa, getattr(cfg, nazwa))
    if baza:
        konfiguracja.przywroc(proba, baza)
    return proba


def rozwiaz(preset: Preset, cfg: Any, baza: dict[str, Any] | None = None
            ) -> tuple[types.SimpleNamespace, list[str]]:
    """Preset przymierzony na kopii: (kopia po zastosowaniu, meldunki)."""
    proba = proba_konfiguracji(cfg, baza)
    try:
        meldunki = konfiguracja.zastosuj(preset.pola, proba)
    except konfiguracja.BledKonfiguracji as exc:
        raise BladPresetu("%s: %s" % (preset.plik.name, exc))
    return proba, meldunki


def pochodzenie(preset: Preset, cfg: Any, baza: dict[str, Any]) -> dict[str, str]:
    """Skad kazda stala konta bierze wartosc: „preset" albo „silnik".

    To jest odpowiedz na K7 audytu: operator widzi, ktore role, listy
    i liczby pochodza z jego pliku, a ktore z domyslnych silnika.
    """
    proba, _ = rozwiaz(preset, cfg, baza)
    wynik = {}
    for nazwa in konfiguracja.STALE_KONTA:
        if not hasattr(proba, nazwa):
            continue
        po = getattr(proba, nazwa)
        przed = baza.get(nazwa)
        if isinstance(po, dict) and isinstance(przed, dict):
            for klucz in sorted(set(po) | set(przed)):
                wynik["%s[%s]" % (nazwa, klucz)] = (
                    "preset" if po.get(klucz) != przed.get(klucz) else "silnik")
            # Calosc slownika tez ma odpowiedz: „preset", gdy zmienil sie
            # choc jeden klucz — kanaly i przyklady sa czytane jako calosc.
            wynik[nazwa] = "preset" if _kanoniczne(po) != _kanoniczne(przed) else "silnik"
        else:
            wynik[nazwa] = "preset" if _kanoniczne(po) != _kanoniczne(przed) else "silnik"
    return wynik


def _dostawca(model: str) -> str:
    """Dostawca po prefiksie — TA SAMA regula co `llm._dostawca`.

    Importowana z `llm`, gdy sie da; kopia lokalna tylko wtedy, gdy `llm` nie
    da sie zaimportowac (brak pakietu `anthropic` na maszynie operatora).
    """
    try:
        import llm
        return llm._dostawca(model)
    except Exception:                                           # noqa: BLE001
        if model.startswith("deepseek"):
            return "deepseek"
        if model.startswith("claude"):
            return "anthropic"
        if model.startswith("gpt-") or model.startswith("dall-"):
            return "openai"
        return ""


def sprawdz(preset: Preset, cfg: Any, baza: dict[str, Any] | None = None,
            srodowisko: dict[str, str] | None = None) -> tuple[list[str], list[str]]:
    """Reguly PONAD ksztaltem pol. Oddaje (bledy, uwagi). Zero sieci, zero modeli.

    Blad uniemozliwia podlaczenie. Uwaga to rzecz, ktora operator ma zobaczyc
    (brak kanalow, brak przykladow, jezyk bez wzorcow bramek, brak klucza
    w srodowisku) — swiadomie wylaczona funkcja nie jest bledem.
    """
    bledy: list[str] = []
    uwagi: list[str] = []
    srodowisko = os.environ if srodowisko is None else srodowisko
    try:
        proba, _ = rozwiaz(preset, cfg, baza)
    except BladPresetu as exc:
        return [str(exc)], []

    # --- styl: pliki musza istniec, korpus wedle deklaracji ------------
    for nazwa, opis in (("STYLE_PROFILE_POSITIVE", "profil pozytywny stylu"),
                        ("STYLE_PROFILE_NEGATIVE", "profil negatywny stylu")):
        p = getattr(proba, nazwa, None)
        if p is None or not Path(p).is_file():
            bledy.append("%s nie istnieje: %s" % (opis, p))
    korpus = Path(getattr(proba, "STYLE_CORPUS", ""))
    wymagaj = bool(getattr(proba, "STYL_WYMAGAJ_KORPUSU", True))
    if "styl.korpus" in preset.pola and preset.pola["styl.korpus"] and not korpus.is_file():
        bledy.append("styl.korpus wskazuje plik, ktorego nie ma: %s" % korpus)
    elif wymagaj and not korpus.is_file():
        bledy.append("styl.wymagaj_korpusu = true, a korpusu nie ma (%s). Wrzuc "
                     "plik .txt i przypnij go (`python narzedzia/przypnij_styl.py`), "
                     "albo ustaw styl.wymagaj_korpusu = false" % korpus)
    elif korpus.is_file() and not (korpus.parent / "przypiecia.json").is_file():
        (bledy if wymagaj else uwagi).append(
            "korpus stylu nie jest przypiety (brak %s) — "
            "`python narzedzia/przypnij_styl.py --pokaz`" % (korpus.parent / "przypiecia.json"))
    if not korpus.is_file() and not wymagaj:
        uwagi.append("bez korpusu stylu: pisarz artykulu dostanie same profile "
                     "i opis glosu (`styl.opis`)")
    if not str(getattr(proba, "STYL_OPIS", "") or "").strip():
        uwagi.append("styl.opis jest pusty — glos redakcji opisuja tylko profile")

    # --- modele: kazda rola musi miec dostawce, ktorego silnik obsluguje ----
    klucze = {"anthropic": "ANTHROPIC_API_KEY", "deepseek": "DEEPSEEK_API_KEY",
              "openai": "OPENAI_API_KEY"}
    brak_klucza: set[str] = set()
    for rola, model in sorted(getattr(proba, "MODEL_FOR", {}).items()):
        dostawca = _dostawca(str(model))
        if rola == "obraz":
            if getattr(proba, "OBRAZ_WLACZONY", True) and dostawca != "openai":
                bledy.append("modele: okladka %r nie jest modelem OpenAI Images — "
                             "`llm.obraz` nie ma innej sciezki; ustaw modele.obraz = \"\", "
                             "zeby wylaczyc okladke" % model)
            elif getattr(proba, "OBRAZ_WLACZONY", True) and not srodowisko.get(
                    "OPENAI_API_KEY", "").strip():
                brak_klucza.add("OPENAI_API_KEY (okladka)")
            continue
        if dostawca not in ("anthropic", "deepseek"):
            bledy.append("modele.role: %s = %r — `llm.call` nie ma sciezki dla "
                         "dostawcy %r (obslugiwane: anthropic, deepseek)"
                         % (rola, model, dostawca or "nieznany"))
        elif not srodowisko.get(klucze[dostawca], "").strip():
            brak_klucza.add(klucze[dostawca])
    zapasowy = str(getattr(proba, "ZAPASOWY_PISARZ", "") or "")
    if zapasowy and _dostawca(zapasowy) not in ("anthropic", "deepseek"):
        bledy.append("modele.zapasowy_pisarz = %r — brak sciezki dostawcy" % zapasowy)
    if brak_klucza:
        uwagi.append("brak w srodowisku: %s — podaj przed pierwszym przebiegiem "
                     "(agent-v2/.env)" % ", ".join(sorted(brak_klucza)))

    # --- harmonogram i wolumeny --------------------------------------
    godziny = tuple(getattr(proba, "GODZINY_PRZEBIEGOW_UTC", ()) or ())
    if len(godziny) != int(getattr(proba, "PRZEBIEGOW_DZIENNIE", 0)):
        bledy.append("liczba przebiegow (%d) nie zgadza sie z zegarem (%s)"
                     % (getattr(proba, "PRZEBIEGOW_DZIENNIE", 0), ", ".join(godziny)))
    dni = tuple(getattr(proba, "DNI_ARTYKULU", ()) or ())
    artykuly = int(getattr(proba, "ARTYKULY_TYGODNIOWO", 0))
    if len(dni) != artykuly:
        bledy.append("artykuly na tydzien (%d) nie zgadzaja sie z dniami (%s)"
                     % (artykuly, ", ".join(dni) or "brak"))
    notki = int(getattr(proba, "NOTKI_DZIENNIE", len(getattr(proba, "NOTE_MIX_OTHER_DAY", ()))))
    if artykuly == 0:
        uwagi.append("artykuly wylaczone (0 na tydzien): zegar artykulu nie powstanie, "
                     "promocja nie ma czego promowac")
    elif notki == 0:
        uwagi.append("notki wylaczone przy wlaczonych artykulach — notka promujaca "
                     "artykul nie ma slotu")
    if notki == 0:
        uwagi.append("notki wylaczone (0 na dobe)")
    for nazwa, opis in (("KOMENTARZE_DZIENNIE", "komentarze"), ("LAJKI_DZIENNIE", "polubienia"),
                        ("RESTACK_DZIENNIE", "restacki"), ("FOLLOW_MIESIECZNIE", "obserwacje"),
                        ("SUBSKRYPCJE_MIESIECZNIE", "subskrypcje")):
        widelki = tuple(getattr(proba, nazwa, (0, 0)))
        if widelki[1] == 0:
            uwagi.append("%s wylaczone" % opis)
    if artykuly and float(getattr(proba, "SUFIT_DZIENNY_BAZOWY", 0)) < 2 * float(
            getattr(proba, "RUN_LIMIT_USD", 0)):
        uwagi.append("sufit dzienny %.2f USD nie zmiesci dwoch przebiegow po %.2f — "
                     "artykul moze nie powstac w dniu z rutyna dnia"
                     % (getattr(proba, "SUFIT_DZIENNY_BAZOWY", 0),
                        getattr(proba, "RUN_LIMIT_USD", 0)))

    # --- temat i zrodla ----------------------------------------------
    if not getattr(proba, "KANALY_YOUTUBE", {}):
        uwagi.append("bez kanalow YouTube — zaczyn tematow z kanalow bedzie pusty")
    przyklady = getattr(proba, "PRZYKLADY_NISZY", {}) or {}
    if not any(przyklady.values()):
        uwagi.append("bez przykladow z niszy — prompty dostana polecenie zastepcze")
    ile_hasel = len(getattr(proba, "HASLA_SZUKANIA", ()))
    minimum = 3 * int(getattr(proba, "ILE_HASEL_NA_PRZEBIEG", 5))
    if ile_hasel < minimum:
        uwagi.append("%d hasel szukania przy %d losowanych na przebieg — pula ponizej %d "
                     "wraca po tych samych kontach" % (
                         ile_hasel, getattr(proba, "ILE_HASEL_NA_PRZEBIEG", 5), minimum))
    znaki = [z.lower() for z in getattr(proba, "ZNAKI_NISZY", ())]
    poza = [h for h in getattr(proba, "HASLA_SZUKANIA", ())
            if not any(z in h.lower() for z in znaki)]
    if poza:
        uwagi.append("%d hasel bez zadnego znaku niszy (%s)" % (len(poza), ", ".join(poza[:3])))

    # --- jezyk: ktore bramki beda dzialac ------------------------------
    jezyk = str(getattr(proba, "ARTICLE_LANGUAGE", "English"))
    try:
        import jezyki
        brak = jezyki.brakujace(jezyk)
    except Exception:                                           # noqa: BLE001
        brak = []
    if brak:
        uwagi.append("jezyk %r nie ma wzorcow dla %d bramek (%s) — te bramki beda "
                     "jawnie wylaczone" % (jezyk, len(brak), ", ".join(brak[:4])))
    return bledy, uwagi


# ---------------------------------------------------------------------------
# zastosowanie na zywym module `config`
# ---------------------------------------------------------------------------
def zastosuj(preset: Preset, cfg: Any, baza: dict[str, Any]) -> list[str]:
    """Neutralna baza, potem preset. Oddaje meldunki `konfiguracja.zastosuj`."""
    konfiguracja.przywroc(cfg, baza)
    try:
        return konfiguracja.zastosuj(preset.pola, cfg)
    except konfiguracja.BledKonfiguracji as exc:
        raise BladPresetu("%s: %s" % (preset.plik.name, exc))


# ---------------------------------------------------------------------------
# aktywacja: wskaznik na dysku
# ---------------------------------------------------------------------------
def _zapisz_atomowo(plik: Path, tekst: str) -> None:
    plik.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=plik.name + ".", suffix=".tmp", dir=str(plik.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(tekst)
        os.replace(tmp, plik)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _teraz() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _dopisz_do_dziennika(katalog: Path, wpis: dict[str, Any]) -> int:
    """Dziennik aktywacji instancji; oddaje numer TEJ aktywacji."""
    katalog.mkdir(parents=True, exist_ok=True)
    dziennik = katalog / NAZWA_DZIENNIKA
    numer = 0
    if dziennik.exists():
        for linia in dziennik.read_text(encoding="utf-8").splitlines():
            if linia.strip():
                numer += 1
    numer += 1
    wpis = {"numer": numer, "kiedy": _teraz(), **wpis}
    with dziennik.open("a", encoding="utf-8") as f:
        f.write(json.dumps(wpis, ensure_ascii=False) + "\n")
    return numer


def czytaj_wskaznik(agent_dir: Path) -> dict[str, Any] | None:
    """Surowa tresc wskaznika (bez wczytywania presetu) albo None."""
    w = wskaznik(agent_dir)
    if not w.exists():
        return None
    try:
        dane = json.loads(w.read_text(encoding="utf-8"))
    except Exception as exc:                                    # noqa: BLE001
        raise BladPresetu("%s jest nieczytelny (%s: %s) — `python narzedzia/presety.py "
                          "odlacz` i podlacz preset od nowa" % (w, type(exc).__name__, exc))
    if not isinstance(dane, dict) or not dane.get("plik"):
        raise BladPresetu("%s nie ma pola `plik` — odlacz i podlacz preset od nowa" % w)
    return dane


def aktywacja(agent_dir: Path, srodowisko: dict[str, str] | None = None) -> Aktywacja | None:
    """Co jest podlaczone. `None` = nic. Zly wskaznik albo zmieniony preset = wyjatek.

    Kolejnosc: zmienna srodowiskowa (podglad/test), potem wskaznik.
    """
    srodowisko = os.environ if srodowisko is None else srodowisko
    agent_dir = Path(agent_dir).resolve()
    sciezka = (srodowisko.get(ZMIENNA) or "").strip()
    if sciezka:
        preset = wczytaj(_bezwzgledna(sciezka, korzen(agent_dir)))
        instancja = "podglad-" + preset.nazwa
        return Aktywacja(preset=preset, instancja=instancja,
                         katalog_danych=katalog_instancji(agent_dir) / instancja,
                         numer=0, aktywowano="", zrodlo="srodowisko")
    dane = czytaj_wskaznik(agent_dir)
    if dane is None:
        return None
    plik = _bezwzgledna(str(dane["plik"]), korzen(agent_dir))
    preset = wczytaj(plik)
    if preset.odcisk != str(dane.get("odcisk") or ""):
        raise BladPresetu(
            "preset %r zmienil sie po aktywacji (odcisk %s, a podlaczono %s).\n"
            "To celowe: zmiana pliku pod pracujacym botem nie wchodzi po cichu.\n"
            "Podlacz go ponownie: python narzedzia/presety.py podlacz %s"
            % (preset.nazwa, preset.odcisk[:12], str(dane.get("odcisk") or "")[:12],
               preset.nazwa))
    instancja = str(dane.get("instancja") or preset.nazwa)
    katalog = _bezwzgledna(str(dane.get("katalog_danych")
                               or "agent-v2/%s/%s" % (NAZWA_KATALOGU_INSTANCJI, instancja)),
                           korzen(agent_dir))
    return Aktywacja(preset=preset, instancja=instancja, katalog_danych=katalog,
                     numer=int(dane.get("numer") or 0),
                     aktywowano=str(dane.get("aktywowano") or ""), zrodlo="wskaznik")


def podlacz(plik: Path, agent_dir: Path, cfg: Any, baza: dict[str, Any] | None = None,
            instancja: str | None = None, srodowisko: dict[str, str] | None = None
            ) -> tuple[Aktywacja, list[str]]:
    """Sprawdza preset W CALOSCI i dopiero potem atomowo przelacza wskaznik.

    Oddaje (aktywacja, uwagi). Blad zostawia dotychczasowy wskaznik NIETKNIETY —
    zly preset B nie odlacza dzialajacego A (scenariusz 6 audytu).
    """
    agent_dir = Path(agent_dir).resolve()
    preset = wczytaj(plik)
    bledy, uwagi = sprawdz(preset, cfg, baza, srodowisko)
    if bledy:
        raise BladPresetu("preset %r nie przeszedl sprawdzenia:\n  - %s"
                          % (preset.nazwa, "\n  - ".join(bledy)))
    instancja = (instancja or preset.nazwa).strip()
    if not _WZORZEC_NAZWY.fullmatch(instancja):
        raise BladPresetu("nazwa instancji %r: dozwolone male litery, cyfry, kropka, "
                          "myslnik i podkreslenie" % instancja)
    katalog = katalog_instancji(agent_dir) / instancja
    numer = _dopisz_do_dziennika(katalog, {"zdarzenie": "podlacz", "preset": preset.nazwa,
                                           "odcisk": preset.odcisk,
                                           "plik": _wzgledna(preset.plik, korzen(agent_dir))})
    kiedy = _teraz()
    dane = {
        "schema": SCHEMA,
        "preset": preset.nazwa,
        "plik": _wzgledna(preset.plik, korzen(agent_dir)),
        "odcisk": preset.odcisk,
        "instancja": instancja,
        "katalog_danych": _wzgledna(katalog, korzen(agent_dir)),
        "numer": numer,
        "aktywowano": kiedy,
    }
    _zapisz_atomowo(wskaznik(agent_dir), json.dumps(dane, ensure_ascii=False, indent=1) + "\n")
    return Aktywacja(preset=preset, instancja=instancja, katalog_danych=katalog,
                     numer=numer, aktywowano=kiedy, zrodlo="wskaznik"), uwagi


def odlacz(agent_dir: Path) -> dict[str, Any] | None:
    """Usuwa wskaznik. Oddaje jego tresc (co bylo podlaczone) albo None.

    Dziala takze przy zepsutym presecie — czyta wskaznik surowo, bez
    wczytywania pliku presetu, bo odlaczenie ma byc mozliwe zawsze.
    """
    agent_dir = Path(agent_dir).resolve()
    w = wskaznik(agent_dir)
    if not w.exists():
        return None
    try:
        dane = json.loads(w.read_text(encoding="utf-8"))
        if not isinstance(dane, dict):
            dane = {}
    except Exception:                                           # noqa: BLE001
        dane = {}
    if dane.get("katalog_danych"):
        try:
            _dopisz_do_dziennika(_bezwzgledna(str(dane["katalog_danych"]), korzen(agent_dir)),
                                 {"zdarzenie": "odlacz", "preset": dane.get("preset"),
                                  "odcisk": dane.get("odcisk")})
        except OSError:
            pass
    w.unlink()
    return dane


KOMUNIKAT_BRAKU = """\
BRAK AKTYWNEGO PRESETU — %s nie ma na czym pracowac.

Silnik nie ma wbudowanego tematu, stylu ani planu. Zeby ruszyc:
    python narzedzia/presety.py lista              # co jest do podlaczenia
    python narzedzia/presety.py sprawdz <nazwa>    # czy preset jest kompletny
    python narzedzia/presety.py podlacz <nazwa>    # podlacz (nowa instancja albo wznowienie)
Masz stary agent-v2/konfiguracja.toml? Zamien go w preset:
    python narzedzia/presety.py importuj-konfiguracje --nazwa <nazwa>
"""


def wymagaj_aktywnego(cfg: Any, co: str = "ten przebieg") -> Aktywacja | None:
    """Brama na wejsciu `run.py` i `artykul_z_puli.py`: bez presetu nie ma pracy.

    W DARMOWYM TESCIE bramy nie ma — testy podstawiaja atrapy pod `stages`,
    `db` i `browser` i wolaja `main()` bez zadnego presetu, a zapora
    `config.WOLNO_WOLAC_MODEL` i tak nie pusci ich do platnego wywolania.
    Brama chroni PRODUKCJE: zegar, ktory odpala `run.py --dzien --wyslij`
    po odlaczeniu presetu, ma dostac odmowe, nie wbudowany temat.
    """
    if getattr(cfg, "W_TESCIE", False):
        return getattr(cfg, "PRESET_AKTYWACJA", None)
    akt = getattr(cfg, "PRESET_AKTYWACJA", None)
    if akt is None:
        raise BrakPresetu(KOMUNIKAT_BRAKU % co)
    return akt


# ---------------------------------------------------------------------------
# katalog presetow
# ---------------------------------------------------------------------------
def lista(agent_dir: Path) -> list[Path]:
    """Presety operatora (`presety/*.toml`) i przyklady (`presety/przyklady/`)."""
    kat = katalog_presetow(agent_dir)
    wlasne = sorted(p for p in kat.glob("*.toml") if p.is_file()) if kat.is_dir() else []
    przyklady_kat = kat / NAZWA_PRZYKLADOW
    przyklady = (sorted(p for p in przyklady_kat.glob("*.toml") if p.is_file())
                 if przyklady_kat.is_dir() else [])
    return wlasne + przyklady


def znajdz(nazwa: str, agent_dir: Path) -> Path:
    """Preset po nazwie (wlasne przed przykladami) albo po sciezce do pliku."""
    p = Path(nazwa)
    if p.suffix == ".toml" and p.exists():
        return p.resolve()
    kandydaci = [x for x in lista(agent_dir) if x.stem == nazwa]
    if not kandydaci:
        raise BladPresetu("nie ma presetu %r. Dostepne: %s"
                          % (nazwa, ", ".join(x.stem for x in lista(agent_dir)) or "(brak)"))
    return kandydaci[0]


def z_konfiguracji(tekst_toml: str, nazwa: str, opis: str = "") -> str:
    """Stary `konfiguracja.toml` -> tekst presetu (naglowek + oryginal, z komentarzami).

    Nie przepisuje wartosci: komentarze operatora zostaja tam, gdzie byly.
    Wynik ma byc od razu wczytany przez `wczytaj_tekst`, zeby literowka
    wyszla teraz, a nie przy pierwszym przebiegu.
    """
    if not _WZORZEC_NAZWY.fullmatch(nazwa):
        raise BladPresetu("nazwa presetu %r: dozwolone male litery, cyfry, kropka, "
                          "myslnik i podkreslenie" % nazwa)
    naglowek = [
        "# Preset zbudowany z agent-v2/konfiguracja.toml przez narzedzia/presety.py.",
        "# Naglowek [preset] jest jedyna nowa rzecza; reszta to Twoj plik bez zmian.",
        "[preset]",
        "nazwa = %s" % konfiguracja.toml_wartosc(nazwa),
        "opis = %s" % konfiguracja.toml_wartosc(opis or "z konfiguracja.toml"),
        "schema = %d" % SCHEMA,
        "na_podstawie = \"konfiguracja.toml\"",
        "utworzono = %s" % konfiguracja.toml_wartosc(_teraz()[:10]),
        "",
    ]
    return "\n".join(naglowek) + tekst_toml.rstrip("\n") + "\n"


def eksportuj(preset: Preset) -> str:
    """Preset w postaci znormalizowanej (te same pola, ten sam odcisk po wczytaniu).

    Bez sekretow, bez pamieci instancji — tylko rozwiazane pola. Import
    tego tekstu do pustego silnika daje ten sam odcisk (scenariusz 12).
    """
    meta = {"nazwa": preset.nazwa, "schema": preset.schema}
    if preset.opis:
        meta["opis"] = preset.opis
    if preset.wersja:
        meta["wersja"] = preset.wersja
    naglowek = ["# Eksport presetu %r — bez kluczy, sesji i pamieci instancji."
                % preset.nazwa,
                "# odcisk: %s" % preset.odcisk]
    return konfiguracja.zapisz_toml(preset.pola, naglowek, {"preset": meta})
