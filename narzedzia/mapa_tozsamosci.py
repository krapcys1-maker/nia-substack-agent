# -*- coding: utf-8 -*-
"""Generator `docs/IDENTITY_MAP.md` — GDZIE fizycznie siedzi tozsamosc konta.

## Po co, skoro jest juz mapa konfiguracji

`docs/PLUGGING_IN_AN_ACCOUNT.md` mowi, JAKIE POLA sa do ustawienia. Nie mowi,
GDZIE W DRZEWIE te wartosci laduja ani — co wazniejsze — czego ZADNE POLE nie
obsluguje. Konfigurator buduje sie z tej drugiej wiedzy.

Ten plik szuka w drzewie **wartosci**, nie nazw pol: bierze biezaca nazwe
marki, nisze, jezyk i uchwyt z `config`, po czym pokazuje KAZDE miejsce, gdzie
te napisy wystepuja — z plikiem i linia. Wynik dzieli na trzy kategorie:

  POLE      wartosc przyszla z konfiguracji i zmieni sie razem z nia
  WSTRZYK   plik ma `{nisza}` / `{marka}` / `{language}`, wiec tez sie zmieni
  RECZNIE   napis wpisany w tresc — TEGO KONFIGURATOR NIE RUSZY

Trzecia kategoria jest jedynym powodem, dla ktorego ten generator istnieje.
Reczna lista takich miejsc rozjezdza sie z kodem przy pierwszej zmianie, a to
w tym repozytorium juz kosztowalo: nazwa poprzedniego konta przezyla cale
czyszczenie i pierwsze wydanie publiczne, bo byla rozbita miedzy dwa literaly
i nie bylo jej na zadnej liscie.

## Czego ten generator NIE zrobi

Nie znajdzie tozsamosci, ktorej nie potrafi rozpoznac po biezacej wartosci.
Jesli marka nazywa sie „Your Publication", a gdzies stoi jej stara nazwa,
to szuka jej `narzedzia/audyt.py` — z lista spoza repozytorium.

Uruchomienie:  python narzedzia/mapa_tozsamosci.py
"""
from __future__ import annotations

import ast
import pathlib
import os
import re
import subprocess
import sys

KORZEN = pathlib.Path(__file__).resolve().parent.parent
WYNIK = KORZEN / "docs" / "IDENTITY_MAP.md"
sys.path.insert(0, str(KORZEN / "agent-v2"))

# MAPA OPISUJE DOSTARCZONE WARTOSCI, NIGDY TWOJEGO KONTA.
#
# `config.py` na koncu wczytuje `konfiguracja.toml`, jesli istnieje — wiec
# generator uruchomiony u operatora wypisywal do `docs/IDENTITY_MAP.md` JEGO
# uchwyt, JEGO marke i JEGO nisze. Zlapane na goracym uczynku: mapa
# w repozytorium zaczela opisywac konto testowe, ktorym sprawdzalem kreator,
# i poszlaby tak do commita.
#
# To jest dokladnie ta wada, ktora ten plik ma tropic — tozsamosc konta
# wchodzaca tam, gdzie nie powinna — tylko popelniona przez narzedzie.
os.environ["AGENT_V2_BEZ_KONFIGURACJI"] = "1"

import config          # noqa: E402
import konfiguracja    # noqa: E402

POMIN_SUFIKSY = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".pdf", ".db", ".pyc"}

# Katalogi, ktorych nie opisujemy: wynik generatorow i wlasne narzedzia.
POMIN_KATALOGI = ("agent-v2/dokumentacja-zrodla/", "docs/", "narzedzia/")

# Pola wstrzykiwane do promptow — plik z nimi zmieni sie razem z konfiguracja.
WSTRZYKIWANE = ("{nisza}", "{marka}", "{language}")


def sledzone() -> list[pathlib.Path]:
    out = subprocess.run(["git", "-C", str(KORZEN), "ls-files"],
                         capture_output=True, text=True, encoding="utf-8")
    return [KORZEN / n for n in out.stdout.splitlines() if n.strip()]


def wzgledna(p: pathlib.Path) -> str:
    return str(p.relative_to(KORZEN)).replace("\\", "/")


def z_konfiguracji() -> dict[str, str]:
    """Nazwa stalej -> pole w konfiguracja.toml, ktore ja ustawia."""
    return {stala: pole for pole, (stala, _) in konfiguracja.POLA.items()
            if stala is not None}


def szukaj(wartosc: str, etykieta: str, pliki: list[tuple[pathlib.Path, str]]
           ) -> list[tuple[str, int, str]]:
    """Kazde wystapienie wartosci, z dopuszczonym zawinieciem wiersza."""
    if not wartosc or len(wartosc) < 4:
        return []
    wz = re.compile(r"\s+".join(re.escape(s) for s in wartosc.split()),
                    re.IGNORECASE)
    trafienia = []
    for p, t in pliki:
        for m in wz.finditer(t):
            linia = t.count("\n", 0, m.start()) + 1
            kontekst = t.splitlines()[linia - 1].strip()
            trafienia.append((wzgledna(p), linia, kontekst[:88]))
    return trafienia


def sklejone(pliki: list[tuple[pathlib.Path, str]], wartosc: str
             ) -> list[tuple[str, int, str]]:
    """Wartosc widoczna dopiero PO sklejeniu literalow — grep jej nie widzi."""
    wz = re.compile(r"\s+".join(re.escape(s) for s in wartosc.split()), re.I)
    out = []
    for p, t in pliki:
        if p.suffix != ".py":
            continue
        try:
            drzewo = ast.parse(t, filename=str(p))
        except SyntaxError:
            continue
        for n in ast.walk(drzewo):
            if not isinstance(n, ast.Assign):
                continue
            try:
                v = ast.literal_eval(n.value)
            except Exception:                          # noqa: BLE001
                continue
            if isinstance(v, str) and wz.search(v):
                # czy grep po zrodle TEZ by to znalazl?
                zrodlo = ast.get_source_segment(t, n) or ""
                if not wz.search(zrodlo):
                    out.append((wzgledna(p), n.lineno,
                                ast.unparse(n.targets[0]) + " = ...sklejone..."))
    return out


def rodzaj(plik: str, linia: int, kontekst: str, pole: str | None,
           z_polem: set[str]) -> tuple[str, bool]:
    """Jak ta wartosc sie tam znalazla i CZY trzeba ja ruszyc reka.

    Rozroznienie jest tu cala wartoscia dokumentu. Pierwsza wersja liczyla
    razem atrapy testow, komentarze, jednostki systemd i dokumentacje
    generowana — czyli „55 miejsc do edycji", z czego wiekszosc edytuje sie
    sama albo nie ma znaczenia. Liczba, ktora straszy i nie informuje, jest
    gorsza od jej braku.
    """
    if plik.endswith("agent-v2/config.py"):
        return ("**FIELD**" if pole else "constant, no field"), False
    if plik.endswith("JAK_ZBUDOWANY_JEST_BOT.md"):
        return "GENERATED — rebuilds itself", False
    if plik.endswith("konfiguracja.example.toml"):
        return "TEMPLATE — this is the file you copy", False
    if "/tests/" in plik:
        return "test fixture", False
    if plik.endswith((".service", ".timer")):
        return "**BY HAND** — systemd unit", True
    if kontekst.lstrip().startswith(("#", "//", "*")):
        return "comment — harmless, but stale", False
    if plik in z_polem:
        return "**INJECTED** — follows the field", False
    return "**BY HAND**", True


def main() -> int:
    pliki = []
    for p in sledzone():
        if p.suffix.lower() in POMIN_SUFIKSY or not p.is_file():
            continue
        w = wzgledna(p)
        if w.startswith(POMIN_KATALOGI):
            continue
        try:
            pliki.append((p, p.read_text(encoding="utf-8")))
        except (UnicodeDecodeError, OSError):
            continue

    z_konf = z_konfiguracji()
    # JEZYK MA WLASNA LISTE, NIE WYSZUKIWANIE. Wartosc „English" wystepuje
    # w zwyklej prozie i jako klucz slownika, wiec szukanie po niej dawalo
    # 15 trafien, z ktorych ani jedno nie bylo miejscem do edycji — szum
    # zaglaszajacy szesc prawdziwych pozycji. Mapa podajaca 21 miejsc zamiast
    # 6 jest gorsza od jej braku, bo uczy pomijania calej listy.
    MIEJSCA_JEZYKA = [
        ("agent-v2/config.py", "ARTICLE_LANGUAGE =",
         "**FIELD** — the value itself"),
        ("agent-v2/stages.py", '"language": config.ARTICLE_LANGUAGE',
         "**INJECTED** into all 24 prompts as `{language}`"),
        ("agent-v2/jezyki.py", '"English": {',
         "**BY HAND** — gate patterns per language; a language with no entry "
         "here has its gates switched off, and says so on every run"),
        ("agent-v2/browser.py", "locale=",
         "**BY HAND** — browser UI locale, so text selectors match"),
    ]

    RZECZY = [
        ("nazwa marki", config.NAZWA_MARKI, "NAZWA_MARKI"),
        ("nisza", config.NISZA, "NISZA"),
        ("uchwyt konta", config.SUBSTACK_HANDLE, "SUBSTACK_HANDLE"),
    ]

    L: list[str] = []
    A = L.append
    A("# Identity map — where the account's identity physically lives\n")
    A("**Generated** by `python narzedzia/mapa_tozsamosci.py`. Do not edit.\n")
    A("`PLUGGING_IN_AN_ACCOUNT.md` lists the fields you set.")
    A("This file answers the other question: **where each value actually lands,**")
    A("and — the part that matters for building a configurator — **what no field")
    A("reaches at all.**\n")
    A("It searches for the *current values* rather than for field names, so a")
    A("place that hard-codes the publication name shows up here even if nobody")
    A("remembered to write it down. That is the point: the hand-written list of")
    A("such places went stale once already, and the previous account name")
    A("survived a full clean-up because it was split across two string literals")
    A("and appeared on no list.\n")
    A("| marker | meaning |")
    A("|---|---|")
    A("| **FIELD** | the value came from `konfiguracja.toml` and changes with it |")
    A("| **INJECTED** | the file uses `{nisza}` / `{marka}` / `{language}`, so it follows too |")
    A("| **BY HAND** | the string is written into the text — **no field reaches this** |")
    A("")

    razem_recznie = 0
    do_reki: list[tuple[str, str, int, str]] = []
    for etykieta, wartosc, stala in RZECZY:
        pole = z_konf.get(stala)
        A("---\n")
        A("## %s — `%s`\n" % (etykieta, wartosc))
        A("Constant `config.%s`%s\n"
          % (stala, ", set by `%s`" % pole if pole else " — **no config field**"))

        traf = szukaj(wartosc, etykieta, pliki)
        skl = sklejone(pliki, wartosc)

        # plik, ktory ma pole wstrzykiwane, zmieni sie sam
        z_polem = {w for w, t in ((wzgledna(p), t) for p, t in pliki)
                   if any(x in t for x in WSTRZYKIWANE)}

        if not traf and not skl:
            A("Appears nowhere in the tree outside `config.py` — nothing to")
            A("hand-edit.\n")
            continue

        A("| file | line | how | context |")
        A("|---|---|---|---|")
        for plik, linia, kontekst in sorted(traf):
            jak, liczy_sie = rodzaj(plik, linia, kontekst, pole, z_polem)
            if liczy_sie:
                razem_recznie += 1
                do_reki.append((etykieta, plik, linia, kontekst))
            A("| `%s` | %d | %s | `%s` |"
              % (plik, linia, jak, kontekst.replace("|", "\\|")))
        for plik, linia, kontekst in sorted(skl):
            razem_recznie += 1
            do_reki.append((etykieta, plik, linia, "SKLEJONY LITERAL"))
            A("| `%s` | %d | **BY HAND, split literal** | `%s` |"
              % (plik, linia, kontekst.replace("|", "\\|")))
        A("")

    # --- jezyk, osobno i jawnie ---------------------------------------
    A("---\n")
    A("## language — `%s`\n" % config.ARTICLE_LANGUAGE)
    A("Constant `config.ARTICLE_LANGUAGE`, set by `temat.jezyk`.\n")
    A("Not searched by value: `English` occurs in ordinary prose (`England`,")
    A("`English Muffin` in the style corpus) and as a dictionary key, so a text")
    A("search returned 15 hits of which **none** was a place to edit. These are")
    A("the places where the language is actually decided, each checked below to")
    A("confirm it still exists:\n")
    A("| file | how | what |")
    A("|---|---|---|")
    for plik, marker, opis in MIEJSCA_JEZYKA:
        sciezka = KORZEN / plik
        jest = sciezka.exists() and marker in sciezka.read_text(encoding="utf-8")
        A("| `%s` | %s | %s |"
          % (plik, opis, "confirmed present" if jest
             else "**MISSING — rerun the generator, this map is stale**"))
        if not jest:
            razem_recznie += 1
            do_reki.append(("language", plik, 0,
                            "expected marker %r not found" % marker))
    A("")
    A("The worked examples inside `agent-v2/prompts/*.md` are in English")
    A("regardless of this field. The model follows `{language}`; the examples")
    A("do not follow anything.\n")

    A("---\n")
    A("## What no field reaches\n")
    if do_reki:
        A("**%d places** need a human hand when the account changes."
          % razem_recznie)
        A("Everything else either follows `konfiguracja.toml`, regenerates")
        A("itself, or is a test fixture that no live run reads.\n")
        A("| what | file | line | context |")
        A("|---|---|---|---|")
        for etykieta, plik, linia, kontekst in sorted(do_reki):
            A("| %s | `%s` | %d | `%s` |"
              % (etykieta, plik, linia, kontekst.replace("|", "\\|")[:70]))
        A("")
    else:
        A("**Nothing.** Every occurrence follows a field, regenerates itself,")
        A("or is a test fixture.\n")
    A("The `systemd` unit descriptions are per-installation by nature,")
    A("like `WorkingDirectory` and `User` in the same files. You edit those")
    A("three together when you deploy; `docs/INSTALL.md` step 7 says so.")
    A("")
    A("Known and deliberate, not counted above because no field could reach")
    A("them:")
    A("")
    A("* the worked examples inside `agent-v2/prompts/*.md` are in English")
    A("  regardless of `temat.jezyk`. The model follows `{language}`; the")
    A("  examples do not follow anything.")
    A("* `agent-v2/jezyki.py` holds gate patterns per language. A language")
    A("  with no entry there has its gates switched off — loudly, every run.")
    A("")
    A("This file is GENERATED, so the list above cannot go stale the way the")
    A("hand-written one did.")

    WYNIK.parent.mkdir(parents=True, exist_ok=True)
    WYNIK.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("zapisano %s" % WYNIK.relative_to(KORZEN))
    print("  miejsc BY HAND (zadne pole ich nie siega): %d" % razem_recznie)
    return 0


if __name__ == "__main__":
    sys.exit(main())
