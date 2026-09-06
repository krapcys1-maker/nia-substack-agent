# -*- coding: utf-8 -*-
"""Preset: kartridz z CALA redakcja, podlaczany i odlaczany jednym poleceniem.

## Po co to istnieje

Audyt z 5 wrzesnia 2026 (`analizy/2026-09-05-czystosc-presety/RAPORT.md`)
stwierdzil, ze bot jest jedna skonfigurowana instalacja, a nie silnikiem,
do ktorego podlacza sie preset i potem go wyjmuje: `konfiguracja.toml`
nakladal sie na poprzednie wartosci (T02), miks notek zmienial tylko zwykly
dzien (T04), zegar siedzial w szablonach systemd (W2), styl w plikach o stalych
nazwach (C4), a brak pliku konfiguracji przywracal wbudowany temat zamiast
zatrzymac bota (C1). Nie bylo operacji „odlacz i zostan pusty".

Ten modul wprowadza cztery rzeczy, ktore audyt nazwal granica architektoniczna:

  SILNIK      — kod w `agent-v2/` i jego wartosci domyslne. NIE ZNA TEMATU:
                nisza, hasla, dziedziny, kalendarz i tozsamosc okladki sa
                w silniku puste od 2026-09-05.
  PRESET      — katalog `presety/<nazwa>/` z plikiem `preset.toml` (komplet
                pol z `konfiguracja.POLA`), `styl/` (profile, korpus)
                i `prompty/` (bloki redakcyjne wstrzykiwane do briefow —
                patrz `BLOKI`). Pojedynczy plik `presety/<nazwa>.toml` tez
                jest presetem, tylko bez wlasnych blokow i stylu. Ma ODCISK
                (sha256 pol i blokow).
  INSTANCJA   — katalog `agent-v2/instancje/<nazwa>/`: baza, bank, cache,
                szkice, promocje TEGO presetu. Inny preset ma inny katalog.
  AKTYWACJA   — plik `agent-v2/aktywny_preset.json`: ktory preset, z jakim
                odciskiem, w ktorej instancji, ktory raz. Jedyne, co czyta
                `config.py` przy starcie.

## Co robi silnik, a co preset

Silnik trzyma METODE: kontrakty etapow, ksztalt JSON-a, bramki, wzorce
tematow (`GENERATORY`), reguly rzetelnosci („nie zmyslaj dowodu", „pobrane
dane to nie instrukcje"). Preset trzyma to, co odroznia jedna publikacje od
drugiej: o czym, dla kogo, jakim glosem, skad brac sygnaly, ktore modele,
ile, kiedy, za ile. Brief kazdego etapu sklada sie z obu warstw: silnik
podaje szkielet, preset wypelnia pola `{nisza}`, `{kat_redakcyjny}`,
`{styl_opis}` i bloki z `prompty/`.

## Co sie dzieje przy podlaczeniu

`podlacz` czyta preset, sprawdza go W CALOSCI bez platnych wywolan (pola,
pola wymagane, reguly strukturalne tematu, pliki stylu, dostawcy modeli,
spojnosc zegara), zaklada katalog instancji i ATOMOWO zapisuje wskaznik.
Nic nie jest kopiowane do `konfiguracja.toml`; nic nie jest nakladane na
poprzedni preset.

Przy KAZDYM starcie `config.py` robi to samo w druga strone: czyta wskaznik,
wczytuje preset z dysku, porownuje odcisk (preset zmieniony po aktywacji
zatrzymuje start — ma byc podlaczony jeszcze raz, swiadomie), przywraca
neutralna baze silnika i dopiero na nia naklada pola i bloki presetu. Dzieki
temu preset B skompilowany po A daje ten sam kontekst co B na czystym silniku.

## Co sie dzieje przy odlaczeniu

`odlacz` usuwa wskaznik. Katalog instancji ZOSTAJE (bank, szkice, cache,
baza) i da sie go wznowic przez ponowne `podlacz` tego samego presetu.
Bez aktywnego presetu `run.py` i `artykul_z_puli.py` ODMAWIAJA startu —
patrz `wymagaj_aktywnego`. Nie ma stanu „wrocil do wbudowanego tematu",
bo silnik zadnego tematu nie ma.

## Czego ten modul NIE robi

Nie importuje `config` na poziomie modulu — `config.py` importuje JEGO, wiec
kazda funkcja dostaje modul konfiguracji jako argument (`cfg`), tak samo jak
`konfiguracja.zastosuj`. Nie dotyka sieci, modeli ani przegladarki. Nie
przenosi sekretow: klucze zostaja w `.env`, sesja w katalogu danych.

## Uzycie

    python narzedzia/presety.py lista
    python narzedzia/presety.py nowy moj-temat        # z szablonu presety/SZABLON/
    python narzedzia/presety.py sprawdz moj-temat
    python narzedzia/presety.py podlacz moj-temat
    python narzedzia/presety.py status
    python narzedzia/presety.py odlacz

Podglad promptow z presetem, bez podlaczania:  `AGENT_V2_PRESET=presety/ai`.
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
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import konfiguracja

SCHEMA = 1
NAZWA_WSKAZNIKA = "aktywny_preset.json"
NAZWA_KATALOGU_INSTANCJI = "instancje"
NAZWA_KATALOGU_PRESETOW = "presety"
NAZWA_PLIKU_PRESETU = "preset.toml"
NAZWA_SZABLONU = "SZABLON"
NAZWA_DZIENNIKA = "aktywacje.jsonl"
KATALOG_BLOKOW = "prompty"

# Sciezka do presetu (katalog albo plik) podana srodowiskiem — do PODGLADU
# i TESTOW. Ma pierwszenstwo przed wskaznikiem, dziala takze bez `podlacz`
# i nie tworzy wskaznika. Katalog danych to `instancje/podglad-<nazwa>`, zeby
# podglad nie dotykal danych zadnej prawdziwej instancji.
ZMIENNA = "AGENT_V2_PRESET"

# Pola naglowka `[preset]`. Zamkniete: literowka w naglowku tez ma byc bledem.
META_DOZWOLONE = ("nazwa", "opis", "wersja", "schema", "autor", "utworzono",
                  "na_podstawie")
_WZORZEC_NAZWY = re.compile(r"[a-z0-9][a-z0-9._-]{0,62}")

# BLOKI PROMPTOW, KTORE PRESET MOZE DOSTARCZYC (`prompty/<nazwa>.md`).
# Nazwa bloku = nazwa pola w briefie silnika. Kazdy jest opcjonalny; brak
# daje jawne zdanie zastepcze (`stages._pola_wspolne`), nie pustke.
BLOKI: dict[str, str] = {
    "linia_redakcyjna": ("co dla tej publikacji JEST tematem, a co nie, i jakie pytania "
                         "warto stawiac — czytaja skaut, ciekawostki, bank i bramka "
                         "'warto pisac'"),
    "glos_artykulu": "jak ten tytul pisze dlugi tekst — czyta pisarz artykulu",
    "glos_notki": "jak brzmi notka — czytaja briefy notki i mysli",
    "glos_komentarza": "jak brzmi komentarz i odpowiedz — komentarz, odpowiedz, restack",
    "okladka": ("tozsamosc wizualna okladki: blok stylu kopiowany doslownie do promptu "
                "obrazu — czyta brief grafiki"),
    "kogo_szukamy": "pod czyimi postami komentujemy, a pod czyimi nie — czyta wybor celow",
    "oswiadczenie": ("publiczne oswiadczenie o autorstwie pokazywane przy skanie AI — "
                     "ustawienie konta, robione raz"),
}

# POLA, BEZ KTORYCH SILNIK NIE MA CZYM PRACOWAC. Silnik nie ma domyslnego
# tematu, wiec brak ktoregos z nich to nie „zostaw domyslne", tylko pusty
# brief dla modelu.
WYMAGANE: tuple[str, ...] = (
    "konto.uchwyt", "konto.nazwa_marki",
    "temat.nisza", "temat.kat_redakcyjny", "temat.jezyk",
    "temat.znaki_niszy", "temat.hasla_szukania", "temat.dziedziny",
)

# Znacznik pola do uzupelnienia w szablonie. Preset z takim napisem NIE
# przechodzi sprawdzenia — szablonu nie da sie podlaczyc przez pomylke.
ZNACZNIK_UZUPELNIJ = "<<"


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
    katalog: Path | None = None
    bloki: dict[str, str] = field(default_factory=dict)
    zasoby: dict[str, str] = field(default_factory=dict)   # sciezka wzgledna -> sha256 pliku stylu


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


def plik_presetu(sciezka: Path) -> Path:
    """Katalog presetu -> jego `preset.toml`; plik -> ten plik."""
    p = Path(sciezka)
    return p / NAZWA_PLIKU_PRESETU if p.is_dir() else p


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


def odcisk(pola: dict[str, Any], schema: int = SCHEMA,
           bloki: dict[str, str] | None = None,
           zasoby: dict[str, str] | None = None) -> str:
    """SHA-256 pol, blokow I ZASOBOW STYLU.

    Audyt z 6 wrzesnia 2026 (F06): odcisk obejmowal pola i bloki, a pola
    stylu to SCIEZKI — zmiana tresci profilu albo korpusu nie zmieniala
    odcisku (glos podmieniony po cichu), a skopiowanie identycznego
    katalogu pod inna sciezke zmienialo (bo sciezki byly juz bezwzgledne).
    Teraz: pola SUROWE (wzgledne, jak w TOML-u) + bloki + skroty plikow
    stylu z katalogu presetu. Ten sam kartridz ma ten sam odcisk w kazdym
    miejscu; inny profil to inny odcisk.
    """
    tekst = json.dumps({"schema": schema, "pola": _kanoniczne(pola),
                        "bloki": _kanoniczne(bloki or {}),
                        "zasoby": _kanoniczne(zasoby or {})},
                       sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(tekst.encode("utf-8")).hexdigest()


def _wczytaj_bloki(katalog: Path | None) -> dict[str, str]:
    """`prompty/<blok>.md` z katalogu presetu; tylko znane nazwy, tylko niepuste.

    NIEZNANY PLIK JEST BLEDEM — literowka w nazwie bloku dawalaby prompt bez
    tego bloku i nikt by tego nie zauwazyl, bo zdanie zastepcze brzmi
    poprawnie. Naglowek pliku przed pierwszym `---` jest notatka dla czlowieka
    i do promptu NIE IDZIE (ten sam zwyczaj, co `po_ludzku.md`).
    """
    if katalog is None:
        return {}
    kat = Path(katalog) / KATALOG_BLOKOW
    if not kat.is_dir():
        return {}
    bloki: dict[str, str] = {}
    for p in sorted(kat.glob("*.md")):
        if p.stem == "README":
            continue
        if p.stem not in BLOKI:
            raise BladPresetu("%s: nieznany blok promptu %r. Znane: %s"
                              % (kat, p.name, ", ".join(sorted(BLOKI))))
        tekst = p.read_text(encoding="utf-8")
        czesci = tekst.split("\n---\n", 1)
        cialo = (czesci[1] if len(czesci) == 2 else tekst).strip()
        if cialo:
            bloki[p.stem] = cialo
    return bloki


_POLA_SCIEZEK = ("styl.profil_pozytywny", "styl.profil_negatywny", "styl.korpus")
# `repo:style-profiles/X.md` = JAWNY wybor pliku wspolnego z korzenia repozytorium.
# Zwykla sciezka wzgledna w kartridzu znaczy tylko jego katalog (audyt F05).
PRZEDROSTEK_REPO = konfiguracja.PRZEDROSTEK_REPO


def _rozwiaz_sciezki(pola: dict[str, Any], katalog: Path | None) -> dict[str, Any]:
    """Sciezki stylu wzgledem KATALOGU PRESETU, gdy tam leza; inaczej wzgledem repo.

    Preset ma byc przenosny: `styl/profil_pozytywny.md` w jego katalogu
    znaczy ten plik, a nie plik o tej nazwie w korzeniu repozytorium.
    """
    if katalog is None:
        return pola
    wynik = dict(pola)
    for klucz in _POLA_SCIEZEK:
        napis = wynik.get(klucz)
        if not napis or Path(napis).is_absolute() or napis.startswith(PRZEDROSTEK_REPO):
            continue
        # BEZ ZAPASU W REPO (audyt F05): brak pliku w paczce ma byc brakiem
        # pliku, ktory `sprawdz` nazwie po imieniu — a nie okazja, zeby
        # znalezc plik o tej samej nazwie w korzeniu repozytorium.
        wynik[klucz] = (Path(katalog) / napis).resolve().as_posix()
    return wynik


def _zasoby_kartridza(pola: dict[str, Any], katalog: Path | None) -> dict[str, str]:
    """Skroty plikow stylu lezacych W KATALOGU presetu: {sciezka wzgledna: sha256}.

    Tylko pliki z paczki — cudze profile spoza katalogu nie sa jej czescia.
    Przypiecia korpusu (`przypiecia.json` obok niego) tez, bo wybieraja,
    ktore akapity dostaje pisarz.
    """
    if katalog is None:
        return {}
    wynik: dict[str, str] = {}
    for klucz in _POLA_SCIEZEK:
        napis = pola.get(klucz)
        if not napis or Path(napis).is_absolute() or napis.startswith(PRZEDROSTEK_REPO):
            continue
        plik = Path(katalog) / napis
        if plik.is_file():
            wynik[Path(napis).as_posix()] = hashlib.sha256(plik.read_bytes()).hexdigest()
        if klucz == "styl.korpus":
            przypiecia = plik.parent / "przypiecia.json"
            if przypiecia.is_file():
                wynik[(Path(napis).parent / "przypiecia.json").as_posix()] = \
                    hashlib.sha256(przypiecia.read_bytes()).hexdigest()
    return wynik


def wczytaj_tekst(tekst: str, nazwa_pliku: str, plik: Path | None = None,
                  katalog: Path | None = None) -> Preset:
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
    pola_surowe = dict(pola)
    pola = _rozwiaz_sciezki(pola, katalog)
    bloki = _wczytaj_bloki(katalog)
    zasoby = _zasoby_kartridza(pola_surowe, katalog)
    return Preset(nazwa=nazwa, plik=Path(plik) if plik else Path(nazwa_pliku),
                  opis=str(meta.get("opis") or "").strip(),
                  wersja=str(meta.get("wersja") or "").strip(),
                  schema=schema, pola=pola,
                  odcisk=odcisk(pola_surowe, schema, bloki, zasoby),
                  katalog=Path(katalog) if katalog else None, bloki=bloki,
                  zasoby=zasoby)


def wczytaj(sciezka: Path) -> Preset:
    """Preset z katalogu (`presety/<nazwa>/`) albo z pojedynczego pliku."""
    plik = plik_presetu(sciezka)
    if not plik.exists():
        raise BladPresetu("nie ma pliku presetu: %s" % plik)
    katalog = plik.parent if plik.name == NAZWA_PLIKU_PRESETU else None
    return wczytaj_tekst(plik.read_text(encoding="utf-8"), plik.name, plik, katalog)


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


def rozwiaz(preset: Preset, cfg: Any, baza: dict[str, Any] | None = None,
            srodowisko: dict[str, str] | None = None
            ) -> tuple[types.SimpleNamespace, list[str]]:
    """Preset przymierzony na kopii: (kopia po zastosowaniu, meldunki).
    Konto (uchwyt, marka) ze srodowiska instalacji nadpisuje pole `[konto]`,
    tak samo jak robi to `config` przy starcie.
    """
    proba = proba_konfiguracji(cfg, baza)
    try:
        meldunki = konfiguracja.zastosuj(preset.pola, proba)
    except konfiguracja.BledKonfiguracji as exc:
        raise BladPresetu("%s: %s" % (preset.plik.name, exc))
    proba.PRESET_BLOKI = dict(preset.bloki)
    _bez_domyslnego_korpusu(preset, proba)
    nadpisane = konfiguracja.konto_ze_srodowiska(
        proba, os.environ if srodowisko is None else srodowisko)
    if nadpisane:
        meldunki.append("srodowisko -> %s (konto instalacji, nie presetu)" % ", ".join(nadpisane))
    return proba, meldunki


def _bez_domyslnego_korpusu(preset: Preset, cfg: Any) -> None:
    """Pusty `styl.korpus` w kartridzu znaczy BRAK korpusu, nie „ten z katalogu silnika".

    Audyt z 6 wrzesnia 2026 (F05, proba P10): preset B z `korpus = ""`
    i `wymagaj_korpusu = false` dostawal piec akapitow starego korpusu
    z `agent-v2/prompts/styl/`, bo puste pole zostawialo domyslna sciezke
    silnika, a loader ladowal wszystko, co tam lezalo. Kartridz wskazuje
    wiec zawsze swoj katalog: plik, ktorego tam nie ma, to zero przykladow.
    """
    if preset.katalog is None or preset.pola.get("styl.korpus"):
        return
    cfg.STYLE_CORPUS = Path(preset.katalog) / "styl" / "korpus.txt"


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


def _napisy(x: Any):
    """Wszystkie napisy w zagniezdzonej wartosci."""
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for v in x.values():
            yield from _napisy(v)
    elif isinstance(x, (list, tuple)):
        for v in x:
            yield from _napisy(v)


def sprawdz(preset: Preset, cfg: Any, baza: dict[str, Any] | None = None,
            srodowisko: dict[str, str] | None = None,
            do_aktywacji: bool = False) -> tuple[list[str], list[str]]:
    """Reguly PONAD ksztaltem pol. Oddaje (bledy, uwagi). Zero sieci, zero modeli.

    Blad uniemozliwia podlaczenie. Uwaga to rzecz, ktora operator ma zobaczyc
    (brak kanalow, brak bloku, jezyk bez wzorcow bramek, brak klucza
    w srodowisku) — swiadomie wylaczona funkcja nie jest bledem.
    """
    bledy: list[str] = []
    uwagi: list[str] = []
    srodowisko = os.environ if srodowisko is None else srodowisko

    # --- pola wymagane i znaczniki szablonu ---------------------------
    brak = [p for p in WYMAGANE if p not in preset.pola]
    if brak:
        bledy.append("brak pol wymaganych (silnik nie ma dla nich wartosci domyslnych): %s"
                     % ", ".join(brak))
    do_uzupelnienia = sorted({k for k, v in preset.pola.items()
                              if any(ZNACZNIK_UZUPELNIJ in s for s in _napisy(v))})
    if do_uzupelnienia:
        bledy.append("pola z szablonu nadal do uzupelnienia (%s): %s"
                     % (ZNACZNIK_UZUPELNIJ, ", ".join(do_uzupelnienia)))
    for nazwa, tekst in sorted(preset.bloki.items()):
        if ZNACZNIK_UZUPELNIJ in tekst:
            bledy.append("blok prompty/%s.md nadal ma znacznik %s do uzupelnienia"
                         % (nazwa, ZNACZNIK_UZUPELNIJ))
    if bledy:
        return bledy, uwagi

    try:
        proba, _ = rozwiaz(preset, cfg, baza, srodowisko)
    except BladPresetu as exc:
        return [str(exc)], []

    # KONTO INSTALACJI (README: pobierz, wybierz preset, klucze i uchwyt do .env,
    # dziala). Wspolny preset ma placeholder; przy aktywacji to blad, przy
    # samym `sprawdz` — uwaga, zeby dalo sie ocenic preset bez konta.
    problemy_konta = konfiguracja.placeholder_konta(
        getattr(proba, "SUBSTACK_HANDLE", ""), getattr(proba, "NAZWA_MARKI", ""))
    if problemy_konta:
        komunikat = ("konto: %s. Wpisz SUBSTACK_HANDLE=<uchwyt> i NAZWA_MARKI=<nazwa> "
                     "w agent-v2/.env (konto jest instalacji, preset moze byc wspolny)"
                     % "; ".join(problemy_konta))
        (bledy if do_aktywacji else uwagi).append(komunikat)
    # --- temat: reguly strukturalne, wywiedzione ze struktury silnika --
    # Te same, ktore `narzedzia/pakiety.py` stawia wsadom: nie liczby wpisane
    # recznie, tylko wielkosci, ktore MAJA skutek w kodzie.
    hasla = [str(h).lower() for h in getattr(proba, "HASLA_SZUKANIA", ())]
    znaki = [str(z).lower() for z in getattr(proba, "ZNAKI_NISZY", ())]
    ile_na_przebieg = int(getattr(proba, "ILE_HASEL_NA_PRZEBIEG", 5))
    minimum = 3 * ile_na_przebieg
    if len(hasla) < minimum:
        bledy.append("%d hasel szukania przy %d losowanych na przebieg — potrzeba co "
                     "najmniej %d, inaczej kazdy przebieg bierze cala pule i wraca "
                     "po tych samych kontach" % (len(hasla), ile_na_przebieg, minimum))
    poza = [h for h in hasla if not any(z in h for z in znaki)]
    if poza:
        bledy.append("%d hasel nie niesie ZADNEGO znaku niszy (%s) — agent znajdzie "
                     "posty, a regula celow odrzuci je co do jednego; dopisz znak "
                     "albo przeformuluj haslo" % (len(poza), ", ".join(poza[:3])))
    notki = int(getattr(proba, "NOTKI_DZIENNIE", len(getattr(proba, "NOTE_MIX_OTHER_DAY", ()))))
    komorki = len(getattr(proba, "GENERATORY", {})) * len(getattr(proba, "DZIEDZINY_CIEKAWOSTEK", ()))
    if notki > 0 and komorki < 10 * notki:
        bledy.append("siatka daje %d komorek (%d wzorcow x %d dziedzin) przy %d notkach "
                     "na dobe — dopisz dziedziny do co najmniej %d, inaczej ten sam "
                     "wzorzec w tej samej dziedzinie wroci w tym samym tygodniu"
                     % (komorki, len(getattr(proba, "GENERATORY", {})),
                        len(getattr(proba, "DZIEDZINY_CIEKAWOSTEK", ())), notki,
                        -(-10 * notki // max(1, len(getattr(proba, "GENERATORY", {}))))))
    kat = str(getattr(proba, "KAT_REDAKCYJNY", "") or "")
    if kat and not kat.rstrip().endswith("."):
        uwagi.append("temat.kat_redakcyjny nie konczy sie kropka — jest doklejany po "
                     "myslniku za nisza w kazdym briefie")

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

    # --- bloki promptow ------------------------------------------------
    brak_blokow = sorted(set(BLOKI) - set(preset.bloki))
    if preset.katalog is None:
        uwagi.append("preset jednoplikowy: bez katalogu `prompty/` — briefy dostana "
                     "zdania zastepcze zamiast blokow (%s)" % ", ".join(sorted(BLOKI)))
    elif brak_blokow:
        uwagi.append("bez blokow promptow: %s — briefy dostana zdanie zastepcze"
                     % ", ".join(brak_blokow))
    if getattr(proba, "OBRAZ_WLACZONY", True) and "okladka" not in preset.bloki:
        uwagi.append("okladka wlaczona, a bez bloku prompty/okladka.md — obrazy nie "
                     "beda mialy wspolnej tozsamosci wizualnej")

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

    # --- zrodla ------------------------------------------------------
    if not getattr(proba, "KANALY_YOUTUBE", {}) and not getattr(proba, "KANALY_RSS", {}):
        uwagi.append("bez kanalow YouTube i RSS — zaczyn tematow bedzie pusty, skaut "
                     "i szukanie ciekawostek pojda z samej siatki dziedzin")
    przyklady = getattr(proba, "PRZYKLADY_NISZY", {}) or {}
    if not any(przyklady.values()):
        uwagi.append("bez przykladow z niszy — prompty dostana polecenie zastepcze")
    if not getattr(proba, "W_TYM_MIESIACU", {}):
        uwagi.append("bez rytmu roku (temat.rytm_roku) — prompt ciekawostek nie dostanie "
                     "podpowiedzi sezonowej")

    # --- jezyk: ktore bramki beda dzialac ------------------------------
    jezyk = str(getattr(proba, "ARTICLE_LANGUAGE", "English"))
    try:
        import jezyki
        brak_wzorcow = jezyki.brakujace(jezyk)
    except Exception:                                           # noqa: BLE001
        brak_wzorcow = []
    if brak_wzorcow:
        uwagi.append("jezyk %r nie ma wzorcow dla %d bramek (%s) — te bramki beda "
                     "jawnie wylaczone" % (jezyk, len(brak_wzorcow), ", ".join(brak_wzorcow[:4])))
    return bledy, uwagi


# ---------------------------------------------------------------------------
# zastosowanie na zywym module `config`
# ---------------------------------------------------------------------------
def zastosuj(preset: Preset, cfg: Any, baza: dict[str, Any]) -> list[str]:
    """Neutralna baza, potem pola i bloki presetu. Oddaje meldunki `konfiguracja.zastosuj`."""
    konfiguracja.przywroc(cfg, baza)
    try:
        meldunki = konfiguracja.zastosuj(preset.pola, cfg)
    except konfiguracja.BledKonfiguracji as exc:
        raise BladPresetu("%s: %s" % (preset.plik.name, exc))
    bloki = getattr(cfg, "PRESET_BLOKI", None)
    if isinstance(bloki, dict):
        bloki.clear()
        bloki.update(preset.bloki)
    else:
        cfg.PRESET_BLOKI = dict(preset.bloki)
    if preset.bloki:
        meldunki.append("prompty/ -> PRESET_BLOKI (%s)" % ", ".join(sorted(preset.bloki)))
    _bez_domyslnego_korpusu(preset, cfg)
    return meldunki


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


def podlacz(sciezka: Path, agent_dir: Path, cfg: Any, baza: dict[str, Any] | None = None,
            instancja: str | None = None, srodowisko: dict[str, str] | None = None,
            przejmij: bool = False) -> tuple[Aktywacja, list[str]]:
    """Sprawdza preset W CALOSCI i dopiero potem atomowo przelacza wskaznik.

    Oddaje (aktywacja, uwagi). Blad zostawia dotychczasowy wskaznik NIETKNIETY —
    zly preset B nie odlacza dzialajacego A (scenariusz 6 audytu).
    """
    agent_dir = Path(agent_dir).resolve()
    preset = wczytaj(sciezka)
    bledy, uwagi = sprawdz(preset, cfg, baza, srodowisko, do_aktywacji=True)
    if bledy:
        raise BladPresetu("preset %r nie przeszedl sprawdzenia:\n  - %s"
                          % (preset.nazwa, "\n  - ".join(bledy)))
    instancja = (instancja or preset.nazwa).strip()
    if not _WZORZEC_NAZWY.fullmatch(instancja):
        raise BladPresetu("nazwa instancji %r: dozwolone male litery, cyfry, kropka, "
                          "myslnik i podkreslenie" % instancja)
    katalog = katalog_instancji(agent_dir) / instancja
    _sprawdz_wlasciciela(katalog, preset, przejmij,
                         konfiguracja.uchwyt_konta(preset.pola,
                                                   os.environ if srodowisko is None else srodowisko))
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


NAZWA_WLASCICIELA = "wlasciciel.json"


def wlasciciel(katalog: Path) -> dict[str, Any] | None:
    """Manifest wlasciciela katalogu instancji albo None, gdy katalog jest nowy."""
    plik = Path(katalog) / NAZWA_WLASCICIELA
    if not plik.is_file():
        return None
    try:
        dane = json.loads(plik.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return dane if isinstance(dane, dict) else {}


def _sprawdz_wlasciciela(katalog: Path, preset: Preset, przejmij: bool,
                         uchwyt: str | None = None) -> None:
    """Instancja nalezy do JEDNEJ redakcji: tego presetu i tego konta.

    Audyt z 6 wrzesnia 2026 (F03, proba P04): preset B podlaczony z tym
    samym `--instancja`, ktorego uzywal A, czytal bank A i oczekujacy artykul
    A — nazwa katalogu nie byla egzekwowana jako wlasciciel. Teraz katalog
    ma manifest z presetem i uchwytem konta; inny preset albo inne konto
    dostaje odmowe i rade, zeby wziac nowa nazwe. `przejmij=True` to jawna
    decyzja operatora, zapisana w dzienniku instancji.
    """
    if uchwyt is None:
        uchwyt = str(preset.pola.get("konto.uchwyt") or "")
    stary = wlasciciel(katalog)
    if stary is not None and stary:
        obcy = (stary.get("preset") != preset.nazwa
                or str(stary.get("uchwyt") or "") != uchwyt)
        if obcy and not przejmij:
            raise BladPresetu(
                "katalog instancji %s nalezy do presetu %r (konto %r), a podlaczasz "
                "%r (konto %r).\n"
                "Nowa redakcja = nowa instancja: podlacz z --instancja <nowa-nazwa>.\n"
                "Jesli to swiadome przejecie banku i kolejki tamtej redakcji: --przejmij."
                % (katalog.name, stary.get("preset"), stary.get("uchwyt"),
                   preset.nazwa, uchwyt))
        if obcy:
            _dopisz_do_dziennika(katalog, {"zdarzenie": "przejecie",
                                           "z": stary.get("preset"), "na": preset.nazwa})
        elif stary.get("preset") == preset.nazwa and str(stary.get("uchwyt") or "") == uchwyt:
            return
    from datetime import datetime, timezone
    katalog.mkdir(parents=True, exist_ok=True)
    _zapisz_atomowo(Path(katalog) / NAZWA_WLASCICIELA, json.dumps(
        {"preset": preset.nazwa, "uchwyt": uchwyt,
         "utworzono": datetime.now(timezone.utc).isoformat(timespec="seconds")},
        ensure_ascii=False, indent=1) + "\n")


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
Nie masz jeszcze presetu? python narzedzia/presety.py nowy <nazwa>   # z szablonu
Masz stary agent-v2/konfiguracja.toml? Zamien go w preset:
    python narzedzia/presety.py importuj-konfiguracje --nazwa <nazwa>
"""


def wymagaj_aktywnego(cfg: Any, co: str = "ten przebieg") -> Aktywacja | None:
    """Brama na wejsciu `run.py` i `artykul_z_puli.py`: bez presetu nie ma pracy.

    W DARMOWYM TESCIE bramy nie ma — testy podstawiaja atrapy pod `stages`,
    `db` i `browser` i wolaja `main()` bez zadnego presetu, a zapora
    `config.WOLNO_WOLAC_MODEL` i tak nie pusci ich do platnego wywolania.
    Brama chroni PRODUKCJE: zegar, ktory odpala `run.py --dzien --wyslij`
    po odlaczeniu presetu, ma dostac odmowe, nie pusty temat.
    """
    if getattr(cfg, "W_TESCIE", False):
        return getattr(cfg, "PRESET_AKTYWACJA", None)
    akt = getattr(cfg, "PRESET_AKTYWACJA", None)
    if akt is None:
        raise BrakPresetu(KOMUNIKAT_BRAKU % co)
    powod = aktywacja_nadal_wazna(cfg)
    if powod:
        raise BrakPresetu("%s — %s.\nUruchom proces od nowa po `podlacz`; "
                          "stary kontekst nie ma juz prawa pracowac." % (co, powod))
    return akt


def tylko_podglad(cfg: Any) -> bool:
    """Aktywacja ze zmiennej AGENT_V2_PRESET to podglad: bez platnych wywolan i publikacji.

    Audyt z 6 wrzesnia 2026 (F02, proby P03 i P19): zmienna omijala
    znaczenie „odlaczono" — proces ze zmienna mial pelny kontekst, a
    `status` mowil „brak aktywnego presetu". Sam start jest dozwolony
    (podglad promptow, test), ale `llm._preflight` i `browser.naprawde_wyslac`
    odmawiaja: pieniadze i konto wymagaja aktywacji wskaznikiem.
    """
    akt = getattr(cfg, "PRESET_AKTYWACJA", None)
    return akt is not None and getattr(akt, "zrodlo", "") == "srodowisko"


def aktywacja_nadal_wazna(cfg: Any) -> str:
    """Pusty napis, gdy aktywacja z pamieci procesu nadal stoi we wskazniku; inaczej powod.

    Audyt z 6 wrzesnia 2026 (F01, proby P02 i P17): `odlacz` usuwal wskaznik,
    ale pracujacy proces mial preset w pamieci i brama pytala tylko o obiekt
    w pamieci. To jest generacja aktywacji: wskaznik zniknal albo wskazuje
    inny preset/instancje = stary proces traci prawo do kolejnego kosztu
    i kolejnej publikacji. Sprawdzane przed KAZDYM platnym wywolaniem
    i przed kazdym zapisem na koncie — jeden maly plik JSON do odczytu.
    """
    akt = getattr(cfg, "PRESET_AKTYWACJA", None)
    if akt is None or getattr(akt, "zrodlo", "") != "wskaznik":
        return ""
    # Katalog agenta z konfiguracji, a bez niej — z katalogu danych aktywacji
    # (`agent-v2/instancje/<nazwa>`): kontekst testowy bez AGENT_DIR nie moze
    # trafic do prawdziwego wskaznika tego repozytorium.
    agent_dir = getattr(cfg, "AGENT_DIR", None)
    if agent_dir is None:
        agent_dir = Path(akt.katalog_danych).resolve().parent.parent
    try:
        dane = czytaj_wskaznik(Path(agent_dir))
    except BladPresetu as exc:
        return "wskaznik aktywacji jest nieczytelny (%s)" % exc
    if dane is None:
        return "preset %r zostal odlaczony po starcie tego procesu" % akt.preset.nazwa
    if (str(dane.get("odcisk") or "") != akt.preset.odcisk
            or str(dane.get("instancja") or "") != akt.instancja):
        return ("aktywacja zmienila sie po starcie tego procesu: wskaznik ma %r/%r, "
                "proces ma %r/%r" % (dane.get("preset"), dane.get("instancja"),
                                    akt.preset.nazwa, akt.instancja))
    return ""


# ---------------------------------------------------------------------------
# katalog presetow
# ---------------------------------------------------------------------------
def lista(agent_dir: Path) -> list[Path]:
    """Presety w `presety/`: katalogi z `preset.toml` i pojedyncze pliki `.toml`.

    Szablon (`SZABLON/`) tez jest na liscie — `sprawdz` pokazuje, ze nie da
    sie go podlaczyc, dopoki nie zostanie uzupelniony.
    """
    kat = katalog_presetow(agent_dir)
    if not kat.is_dir():
        return []
    wynik = [p / NAZWA_PLIKU_PRESETU for p in sorted(kat.iterdir())
             if p.is_dir() and (p / NAZWA_PLIKU_PRESETU).is_file()]
    wynik += sorted(p for p in kat.glob("*.toml") if p.is_file())
    return wynik


def nazwa_z_pliku(plik: Path) -> str:
    """Nazwa presetu z jego polozenia: katalog albo nazwa pliku."""
    plik = Path(plik)
    return plik.parent.name if plik.name == NAZWA_PLIKU_PRESETU else plik.stem


def znajdz(nazwa: str, agent_dir: Path) -> Path:
    """Preset po nazwie (katalog przed plikiem) albo po sciezce."""
    p = Path(nazwa)
    if p.exists() and (p.is_dir() or p.suffix == ".toml"):
        return plik_presetu(p.resolve())
    kandydaci = [x for x in lista(agent_dir) if nazwa_z_pliku(x) == nazwa]
    if not kandydaci:
        raise BladPresetu("nie ma presetu %r. Dostepne: %s"
                          % (nazwa, ", ".join(nazwa_z_pliku(x) for x in lista(agent_dir))
                             or "(brak)"))
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

    Bez sekretow, bez pamieci instancji — tylko rozwiazane pola. Bloki
    promptow zostaja w katalogu presetu; eksport TOML-a ich nie niesie,
    o czym mowi naglowek.
    """
    meta = {"nazwa": preset.nazwa, "schema": preset.schema}
    if preset.opis:
        meta["opis"] = preset.opis
    if preset.wersja:
        meta["wersja"] = preset.wersja
    naglowek = ["# Eksport presetu %r — bez kluczy, sesji i pamieci instancji."
                % preset.nazwa,
                "# odcisk: %s" % preset.odcisk]
    if preset.bloki:
        naglowek.append("# bloki promptow (%s) leza w katalogu presetu, nie w tym pliku"
                        % ", ".join(sorted(preset.bloki)))
    return konfiguracja.zapisz_toml(preset.pola, naglowek, {"preset": meta})
