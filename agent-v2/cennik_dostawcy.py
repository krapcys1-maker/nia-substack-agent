# -*- coding: utf-8 -*-
"""Stawka modelu z OFICJALNEGO cennika dostawcy — sprawdzana przy zamianie modelu.

PO CO. `wersje_modeli.py` sam przechodzi na nowsza wersje modelu w tej samej
rodzinie, a nastepca nie ma wpisu w `config.PRICING`. Dostawcy nie podaja cen
w liscie modeli: `GET /models` u Anthropic, OpenAI i DeepSeeka oddaje same
nazwy. Do 26 wrzesnia 2026 nastepca bez wpisu dostawal wiec PODWOJNA stawke
poprzednika — celowo zawyzona, zeby straznik budzetu stanal za wczesnie, a nie
za pozno. Zmierzone tego dnia na koncie serwera: od zamian z 22 wrzesnia
`claude-opus-5-5` szedl po 10/50 USD za milion tokenow (cennik: 4/20),
a `gpt-6-sol` po 8/40 (cennik: 2/10). W ksiegach bylo 2,5 i 4 razy wiecej, niz
kosztowalo, i miesieczny sufit konczyl sie kilka dni przed koncem miesiaca.
Wlasciciel: sprawdzac cene przy zamianie, a gdy sie nie da — liczyc 1:1.

SKAD CENA. Ze strony cennika SAMEGO DOSTAWCY, zwyklym GET, bez klucza:
  - Anthropic: dokumentacja w markdownie, pierwsza tabela z nazwa modelu
    („| Claude Opus 5.5 | $4 / MTok | ... | $20 / MTok |");
  - OpenAI: strona cennika API, pierwszy wiersz z identyfikatorem modelu
    (tryb standardowy, krotki kontekst).
NIE Z POSREDNIKA. OpenRouter podawal 26.09.2026 dla `gpt-5.6-sol` 2/10 USD,
a OpenAI na swojej stronie 4/20 — lista posrednika nie jest cennikiem dostawcy.

CZEGO NIE CZYTA. DeepSeeka (taryfa szczytowa i trafienia w cache — liczy je
`config.stawka_deepseek`) i modeli obrazow (cena za obraz, nie za token). Dla
nich oddaje `None`, a wolajacy liczy nastepce jak poprzednika (1:1).

NIGDY NIE PODNOSI WYJATKU. Nieodczytany cennik to „nie wiem", a nie awaria
przebiegu — wolajacy ma wtedy stawke poprzednika.
"""
from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from typing import Any, Callable

ADRESY = {
    "anthropic": "https://platform.claude.com/docs/en/about-claude/pricing.md",
    "openai": "https://developers.openai.com/api/docs/pricing",
}

# Naglowki tabel, ktore umiemy czytac. Gdy dostawca zmieni kolejnosc kolumn,
# parser odmawia zamiast wziac wyjscie za wejscie.
NAGLOWEK_ANTHROPIC = ("model", "base input", "5m cache", "1h cache",
                      "cache hits", "output")
NAGLOWEK_OPENAI = "Input Cached input Cache writes Output"


def dostawca_modelu(model: str) -> str | None:
    """Dostawca, ktorego cennik umiemy odczytac; None dla reszty."""
    m = str(model or "").lower()
    if m.startswith("claude-"):
        return "anthropic"
    if m.startswith("gpt-") and not m.startswith("gpt-image"):
        return "openai"
    return None


def _kwota(tekst: str) -> float | None:
    m = re.search(r"\$\s*([0-9]+(?:\.[0-9]+)?)", str(tekst or ""))
    return float(m.group(1)) if m else None


def nazwa_anthropic(model: str) -> str | None:
    """`claude-opus-5-5` -> „Claude Opus 5.5"; data na koncu nie zmienia nazwy."""
    m = re.fullmatch(r"claude-([a-z]+)-(\d+)(?:-(\d{1,2}))?(?:-\d{8})?",
                     str(model or "").lower())
    if not m:
        return None
    linia, a, b = m.groups()
    return "Claude %s %s%s" % (linia.capitalize(), a, "." + b if b else "")


def z_cennika_anthropic(md: str, model: str) -> dict[str, float] | None:
    """Stawka z tabeli cen modeli w dokumentacji Anthropic; None, gdy nie ma."""
    nazwa = nazwa_anthropic(model)
    if not nazwa:
        return None
    naglowek = ""
    for wiersz in str(md or "").splitlines():
        if not wiersz.lstrip().startswith("|"):
            continue
        kom = [k.strip() for k in wiersz.strip().strip("|").split("|")]
        if kom and kom[0].lower() == "model":
            naglowek = " | ".join(k.lower() for k in kom)
            continue
        if not kom or kom[0] != nazwa:
            continue
        # PIERWSZA tabela z tym modelem to cennik podstawowy; kolejne (batch,
        # tryb szybki) maja mniej kolumn albo inny naglowek i sa odrzucane.
        if len(kom) != 6 or not all(n in naglowek for n in NAGLOWEK_ANTHROPIC):
            return None
        liczby = [_kwota(k) for k in kom[1:]]
        if any(x is None for x in liczby):
            return None
        return {"in": liczby[0], "cache": liczby[3], "out": liczby[4]}
    return None


def z_cennika_openai(strona: str, model: str) -> dict[str, float] | None:
    """Stawka z pierwszego wiersza modelu na stronie cennika OpenAI."""
    tekst = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", str(strona or ""))))
    m = re.search(r"(?<![\w.-])%s \$([0-9.]+) \$([0-9.]+) \$([0-9.]+) \$([0-9.]+)"
                  % re.escape(str(model)), tekst)
    if not m:
        return None
    # NAGLOWEK TEJ TABELI, nie cudzej: ostatni „Model ..." przed wierszem musi
    # miec kolumny w tej kolejnosci, inaczej czwarta liczba nie jest wyjsciem.
    naglowek = tekst[:m.start()].rsplit("Model ", 1)[-1]
    if not naglowek.startswith(NAGLOWEK_OPENAI):
        return None
    wej, cache, _zapis, wyj = (float(x) for x in m.groups())
    return {"in": wej, "cache": cache, "out": wyj}


def wiarygodna(cena: dict[str, Any] | None,
               wzor: dict[str, Any] | None = None) -> bool:
    """Czy liczby wygladaja na cennik: wejscie < wyjscie, cache <= wejscie,
    i nie dziesiec razy dalej od poprzednika w obie strony."""
    if not cena:
        return False
    try:
        wej, wyj = float(cena["in"]), float(cena["out"])
        cache = float(cena.get("cache", 0.0))
    except (KeyError, TypeError, ValueError):
        return False
    if not (0 < wej < wyj) or not (0 <= cache <= wej):
        return False
    if wzor:
        try:
            stosunek = (wej + wyj) / (float(wzor["in"]) + float(wzor["out"]))
        except (KeyError, TypeError, ValueError, ZeroDivisionError):
            return True
        return 0.1 <= stosunek <= 10
    return True


def podwyzka(cena: dict[str, Any], wzor: dict[str, Any]) -> float:
    """O ile nastepca drozszy od poprzednika (0.25 = o 25%), po wejsciu + wyjsciu."""
    try:
        return ((float(cena["in"]) + float(cena["out"]))
                / (float(wzor["in"]) + float(wzor["out"])) - 1.0)
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return 0.0


def _pobierz(url: str) -> str:
    import httpx

    import config
    # DARMOWY TEST NIE IDZIE DO SIECI. Test podaje wlasna strone przez
    # `pobierz=`; bez niej dostaje „nie wiem" i nastepca liczy sie 1:1.
    if config.W_TESCIE:
        raise RuntimeError("darmowy test bez sieci")
    with httpx.Client(timeout=config.FETCH_TIMEOUT_S, follow_redirects=True,
                      headers={"User-Agent": config.FETCH_USER_AGENT}) as c:
        r = c.get(url)
        if r.status_code != 200:
            raise RuntimeError("HTTP %s" % r.status_code)
        return r.text


def stawka_u_dostawcy(model: str, wzor: dict[str, Any] | None = None,
                      pobierz: Callable[[str], str] | None = None
                      ) -> tuple[dict[str, float] | None, str]:
    """(stawka, zrodlo) z cennika dostawcy albo (None, powod). Bez wyjatkow.

    `wzor` to stawka poprzednika — sluzy tylko do odrzucenia liczb nie z tego
    swiata (zly wiersz, zmieniona tabela), nie do zgadywania.
    """
    dostawca = dostawca_modelu(model)
    if dostawca not in ADRESY:
        return None, "cennika %s nie odczytujemy" % model
    try:
        tresc = (pobierz or _pobierz)(ADRESY[dostawca])
    except Exception as exc:
        return None, "cennik %s nie odpowiedzial (%s)" % (dostawca, type(exc).__name__)
    czytaj = z_cennika_anthropic if dostawca == "anthropic" else z_cennika_openai
    try:
        cena = czytaj(tresc, model)
    except Exception as exc:
        return None, "cennik %s nieczytelny (%s)" % (dostawca, type(exc).__name__)
    if cena is None:
        return None, "w cenniku %s nie ma %s" % (dostawca, model)
    if not wiarygodna(cena, wzor):
        return None, "cennik %s: liczby dla %s niewiarygodne (%s)" % (dostawca, model, cena)
    return cena, "cennik %s %s" % (
        dostawca, datetime.now(timezone.utc).strftime("%Y-%m-%d"))
