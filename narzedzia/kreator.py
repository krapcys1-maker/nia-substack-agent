# -*- coding: utf-8 -*-
"""Interactive setup: point this bot at an account, in one sitting.

## What this is

`agent-v2/konfiguracja.toml` is the one file that decides which account the
bot posts to, what it writes about, which model does which job and how much of
everything it does per day. This program writes that file, and `agent-v2/.env`
alongside it, by asking.

It is not a wrapper around a text editor. Every answer is validated with the
SAME validators the loader uses (`konfiguracja.POLA`), so a file this program
writes cannot be one the bot then refuses. Getting that wrong is the ordinary
way a setup tool lies to you: it accepts an answer happily and the failure
arrives an hour later, in a stack trace, in a different module.

## What it deliberately does NOT do

**It never writes an API key into the TOML.** Keys go to `agent-v2/.env`,
which is gitignored. A configuration file that carries secrets is a
configuration file nobody can share, paste into an issue or commit — and
somebody eventually does all three.

**It never echoes a key back.** Not at the prompt, not in the summary, not in
the "here is what I wrote" listing. You get the name and the length.

**It does not touch the style corpus.** That is the one input the code cannot
supply and cannot validate for you — see `agent-v2/prompts/styl/README.md`.

**It does not decide anything.** Every question has a default taken from
`config.py`, and every default is the value the bot ships with. Pressing Enter
through the whole program produces a file that changes nothing except the
account it points at.

## Running it

    python narzedzia/kreator.py                 # ask everything
    python narzedzia/kreator.py --pokaz         # print current values, write nothing
    python narzedzia/kreator.py --z-pliku a.json  # answer from a file, no prompts

`--z-pliku` exists so this program can be tested without a human, and so an
operator setting up several accounts does not have to type the same answers
again. Keys are read from the environment in that mode, never from the JSON.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys

KORZEN = pathlib.Path(__file__).resolve().parent.parent
AGENT = KORZEN / "agent-v2"
sys.path.insert(0, str(AGENT))

import config              # noqa: E402
import konfiguracja        # noqa: E402

PLIK_TOML = AGENT / "konfiguracja.toml"
PLIK_ENV = AGENT / ".env"

# Klucze API: nazwa zmiennej -> (do czego sluzy, czy bez niej bot stoi).
KLUCZE = (
    ("DEEPSEEK_API_KEY", "21 of the 26 model roles", True),
    ("ANTHROPIC_API_KEY", "notes, the article, the repair pass", True),
    ("OPENAI_API_KEY", "article cover images only", False),
)


# --------------------------------------------------------------------------
# Pytanie o jedna wartosc. Kazde przechodzi przez walidator z `konfiguracja`,
# ten sam, ktory potem czyta plik.
# --------------------------------------------------------------------------
class Odpowiadacz:
    """Zrodlo odpowiedzi: czlowiek przy klawiaturze albo plik JSON."""

    def __init__(self, gotowe: dict | None = None, wsad: dict | None = None):
        self.gotowe = gotowe
        self.interaktywnie = gotowe is None
        # WSAD TEMATYCZNY PODMIENIA DOMYSLNA ODPOWIEDZ, nie odpowiedz.
        # Czlowiek widzi ja w nawiasie kwadratowym i moze nadpisac — bo to
        # nadal JEGO publikacja, a wsad jest tylko dobrym punktem wyjscia.
        self.wsad = wsad or {}

    def zapytaj(self, klucz: str, pytanie: str, domyslne, podpowiedz: str = "") -> object:
        if klucz in self.wsad:
            domyslne = self.wsad[klucz]
        if not self.interaktywnie:
            return self.gotowe.get(klucz, domyslne)
        print()
        print("  %s" % pytanie)
        if podpowiedz:
            for linia in podpowiedz.split("\n"):
                print("    %s" % linia)
        print("    [Enter = %s]" % _pokaz(domyslne))
        try:
            surowe = input("    > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  przerwane — nic nie zapisano")
            raise SystemExit(1)
        if not surowe:
            return domyslne
        return _zparsuj(surowe, domyslne)


def _pokaz(v) -> str:
    if isinstance(v, (list, tuple)):
        return ", ".join(str(x) for x in v)
    if isinstance(v, dict):
        return "%d pozycji" % len(v)
    return str(v)


def _zparsuj(surowe: str, wzor):
    """Napis z klawiatury na typ, jaki ma wartosc domyslna.

    KSZTALT BIERZE SIE Z DOMYSLNEJ WARTOSCI, nie z osobnej deklaracji typu.
    Domyslne przychodza z `config.py`, wiec nie da sie tu wpisac typu, ktorego
    kod nie uzywa — a dwie deklaracje tego samego zawsze sie w koncu rozjada.
    """
    if isinstance(wzor, bool):
        return surowe.lower() in {"1", "true", "tak", "t", "yes", "y"}
    if isinstance(wzor, tuple) and len(wzor) == 2 and all(isinstance(x, int) for x in wzor):
        czesci = [c.strip() for c in surowe.replace("-", " ").split() if c.strip()]
        return [int(c) for c in czesci]
    if isinstance(wzor, (list, tuple)):
        return [c.strip() for c in surowe.split(",") if c.strip()]
    if isinstance(wzor, bool):
        return surowe
    if isinstance(wzor, int):
        return int(surowe)
    if isinstance(wzor, float):
        return float(surowe)
    return surowe


def sprawdz(sciezka: str, wartosc):
    """Ten sam walidator, ktorego uzyje loader. Blad = pytanie zadane od nowa."""
    _, walidator = konfiguracja.POLA[sciezka]
    return walidator(wartosc, sciezka)


# --------------------------------------------------------------------------
def zbierz(o: Odpowiadacz) -> dict:
    dane: dict[str, object] = {}

    def pole(sciezka, pytanie, domyslne, podpowiedz=""):
        while True:
            v = o.zapytaj(sciezka, pytanie, domyslne, podpowiedz)
            try:
                dane[sciezka] = sprawdz(sciezka, v)
                return
            except konfiguracja.BledKonfiguracji as exc:
                print("    ! %s" % exc)
                if not o.interaktywnie:
                    raise

    print("=" * 72)
    print(" 1/7  THE ACCOUNT")
    print("=" * 72)
    pole("konto.uchwyt", "Substack handle", config.SUBSTACK_HANDLE,
         "The part before .substack.com. Used for the profile URL,\n"
         "the publication panels and for recognising your own posts.")
    pole("konto.nazwa_marki", "Publication name", config.NAZWA_MARKI,
         "As a reader sees it. Goes into every prompt.")
    pole("konto.strefa_czytelnika", "Reader time zone", config.PUBLISH_TIMEZONE,
         "IANA name, e.g. Europe/Warsaw. Decides WHEN things publish.")
    pole("konto.data_przestawienia",
         "Date this account last changed subject (blank if never)",
         config.DATA_PRZESTAWIENIA,
         "YYYY-MM-DD, or leave blank. Blank is the right answer for a new\n"
         "account and for one that has always written about the same thing.\n"
         "\n"
         "Set it only if this account used to be about something else. The\n"
         "stored pool of article candidates survives a change of subject, and\n"
         "without this date the bot will keep writing up leftovers from the\n"
         "old one. Measured on a real account: of 119 waiting candidates, 65\n"
         "belonged to the previous subject.")

    print()
    print("=" * 72)
    print(" 2/7  THE SUBJECT")
    print("=" * 72)
    pole("temat.nisza", "What is this publication about?", config.NISZA,
         "One sentence, lower case, no full stop. It is pasted into\n"
         "every prompt after the word 'about'.")
    pole("temat.jezyk", "Language of everything published", config.ARTICLE_LANGUAGE,
         "English name, e.g. English, Polish, German. Gates that catch\n"
         "first person and hedging exist per language — see jezyki.py.")
    pole("temat.kat_redakcyjny", "What this publication does WITHIN that subject",
         config.KAT_REDAKCYJNY,
         "Follows the subject after a dash, so start lower case and end\n"
         "with a full stop. This used to be hard-coded into nine prompts\n"
         "as 'what these systems actually do' — which quietly made every\n"
         "account a technology publication.")

    # PRZYKLADY Z NISZY. Kazda lista jest opcjonalna, a pusta ma znaczenie:
    # model dostaje wtedy polecenie, zeby wyprowadzil odpowiednik sam. Pytamy
    # o nie na koncu sekcji tematu, bo wymagaja najwiecej myslenia.
    print()
    print("  Examples from your subject — all optional, all improve quality.")
    print("  Leave any of them empty and the prompt tells the model to work")
    print("  the equivalent out for itself, which is worse than a real list")
    print("  but always about YOUR subject.")
    przyklady: dict[str, list[str]] = {}
    for klucz, pytanie, podpowiedz in (
        ("kanon", "Worn-out claims nobody should repeat",
         "The five or six takes so common that repeating one is not a topic."),
        ("rzeczy", "Things your reader has actually seen or used",
         "Objects and moments, not categories."),
        ("seam", "Places where a rule exists because something went wrong",
         "This is where the long articles come from."),
        ("przekonania", "Beliefs that are widely held and wrong",
         "In the reader's own words, starting 'everyone assumes'."),
        ("precedensy", "Times this subject was tested in public",
         "With a result somebody had to answer for."),
    ):
        v = o.zapytaj("temat.przyklady.%s" % klucz, pytanie,
                      list(config.PRZYKLADY_NISZY.get(klucz, ())),
                      podpowiedz + "\nComma separated. Empty is a valid answer.")
        if v:
            przyklady[klucz] = list(v) if isinstance(v, (list, tuple)) else [str(v)]
    if przyklady:
        dane["temat.przyklady"] = sprawdz("temat.przyklady", przyklady)
    pole("temat.znaki_niszy", "Words that mark a post as being in your subject",
         list(config.ZNAKI_NISZY),
         "Comma separated, stems are fine ('regulat' catches regulation,\n"
         "regulatory, regulated). These do NOT filter anything the bot\n"
         "reads: what counts as on-topic is decided by the model,\n"
         "from prompts/cele.md. They are the yardstick your own\n"
         "search terms below are measured against, so you find out\n"
         "here — and not from an empty run — that the two drifted.")
    # „AT LEAST 19" BYLO NASZA LICZBA, I NIKT JEJ NIE SPRAWDZAL. Napis, ktory
    # stawia wymaganie i go nie egzekwuje, to ta sama wada, co kontrola
    # wygladajaca na zywa: mozna bylo wpisac trzy hasla, przejsc dalej bez
    # slowa i dowiedziec sie o tym dopiero z audytu — albo z pustego przebiegu.
    #
    # Regula niezalezna od NASZEJ niszy jest strukturalna: kazdy przebieg
    # losuje `ILE_HASEL_NA_PRZEBIEG` hasel, wiec pula musi byc od tego
    # istotnie szersza — inaczej za kazdym razem idzie cala i wraca po tych
    # samych kontach.
    _minimum = 3 * config.ILE_HASEL_NA_PRZEBIEG
    pole("temat.hasla_szukania", "Search terms for finding people to talk to",
         list(config.HASLA_SZUKANIA),
         "At least %d — the bot draws %d at random every run, and a pool\n"
         "that small is drawn whole, bringing back the same accounts\n"
         "daily. Cover three different sides of the subject."
         % (_minimum, config.ILE_HASEL_NA_PRZEBIEG))
    _ile = len(dane.get("temat.hasla_szukania") or ())
    if _ile < _minimum:
        print("    ! %d hasel to za waska pula przy %d losowanych na przebieg."
              % (_ile, config.ILE_HASEL_NA_PRZEBIEG))
        print("      Zapisuje, bo szerokosc puli jest twoja decyzja — ale")
        print("      kazdy przebieg wezmie ja w calosci. Audyt tez to zglosi.")
    pole("temat.dziedziny", "Areas to look through for facts",
         list(config.DZIEDZINY_CIEKAWOSTEK),
         "The lens, not the destination. Rotated every run.")
    pole("temat.puste_slowa", "Words that mean nothing in your subject",
         list(config.PUSTE_SLOWA_NISZY),
         "Words so common in your field that two unrelated facts share them.\n"
         "Comma separated, and EMPTY IS THE RIGHT ANSWER to begin with:\n"
         "add a word when you have watched it cause a third false\n"
         "duplicate-alarm, not before.")

    print()
    print("=" * 72)
    print(" 3/7  SOURCES")
    print("=" * 72)
    kanaly = o.zapytaj("zrodla.kanaly_youtube",
                       "YouTube channels to watch, as name=id pairs",
                       "", "Comma separated, e.g. Some Channel=UCxxxx,Other=UCyyyy\n"
                           "Leave empty to keep whatever is configured now.")
    if kanaly:
        slownik = {}
        for kawalek in (kanaly if isinstance(kanaly, list) else str(kanaly).split(",")):
            if "=" in str(kawalek):
                nazwa, ident = str(kawalek).split("=", 1)
                slownik[nazwa.strip()] = ident.strip()
        if slownik:
            dane["zrodla.kanaly_youtube"] = sprawdz("zrodla.kanaly_youtube", slownik)
    pole("zrodla.blokowane_hosty", "Hosts never to cite", list(config.BLOCKED_HOSTS),
         "Aggregators and content farms. Comma separated.")

    print()
    print("=" * 72)
    print(" 4/7  MODELS — 26 roles")
    print("=" * 72)
    print("  Enter alone keeps the shipped assignment for every role.")
    print("  To change some, answer role=model pairs, comma separated.")
    print()
    for rola, model in sorted(config.MODEL_FOR.items()):
        print("    %-20s %s" % (rola, model))
    role = o.zapytaj("modele.role", "Roles to change", "",
                     "e.g. write=claude-opus-5,scout=deepseek-v4-flash")
    if role:
        slownik = {}
        for kawalek in (role if isinstance(role, list) else str(role).split(",")):
            if "=" in str(kawalek):
                r, m = str(kawalek).split("=", 1)
                slownik[r.strip()] = m.strip()
        if slownik:
            obce = sorted(set(slownik) - set(config.MODEL_FOR))
            if obce:
                raise SystemExit("unknown roles: %s\nknown: %s"
                                 % (", ".join(obce), ", ".join(sorted(config.MODEL_FOR))))
            dane["modele.role"] = sprawdz("modele.role", slownik)

    print()
    print("=" * 72)
    print(" 5/7  HOW MUCH, PER DAY")
    print("=" * 72)
    print("  Notes per day is the LENGTH of the mix, not a separate number —")
    print("  a count that can disagree with the mix eventually does.")
    pole("publikowanie.miks_notek", "Note mix (one entry = one note that day)",
         list(config.NOTE_MIX_OTHER_DAY),
         "Comma separated, from: %s" % ", ".join(sorted(config.NOTE_TYPES)))
    pole("wolumeny.komentarze_dziennie", "Comments per day (from, to)",
         list(config.KOMENTARZE_DZIENNIE), "Two numbers. Drawn fresh each day.")
    pole("wolumeny.lajki_dziennie", "Likes per day (from, to)",
         list(config.LAJKI_DZIENNIE))
    pole("wolumeny.restacki_dziennie", "Restacks per day (from, to)",
         list(config.RESTACK_DZIENNIE))
    pole("wolumeny.follow_miesiecznie", "Follows per month (from, to)",
         list(config.FOLLOW_MIESIECZNIE))
    pole("wolumeny.subskrypcje_miesiecznie", "Subscriptions per month (from, to)",
         list(config.SUBSKRYPCJE_MIESIECZNIE))
    pole("wolumeny.przebiegow_dziennie", "Runs per day", config.PRZEBIEGOW_DZIENNIE,
         "How many times the timer starts the agent. The mix above is\n"
         "spread across them.")

    print()
    print("=" * 72)
    print(" 6/7  PUBLISHING")
    print("=" * 72)
    pole("publikowanie.okno_et", "Publishing window, reader's clock (from, to)",
         list(config.OKNO_PUBLIKACJI_ET))
    pole("publikowanie.martwe_godziny_et", "Hours to avoid (from, to)",
         list(config.WORST_NOTE_HOURS), "Measured dead hours for notes.")
    pole("publikowanie.notek_promujacych", "Notes promoting each article",
         config.NOTEK_PROMUJACYCH)
    pole("publikowanie.okno_promocji_dni", "Days an article may still be promoted",
         config.OKNO_PROMOCJI_DNI)
    pole("publikowanie.ciche_dni_wlaczone", "Take quiet days at all?",
         config.CICHE_DNI_WLACZONE,
         "A feed with output every single day reads as automated.")
    pole("publikowanie.cichy_dzien_na_ile", "One quiet day per how many?",
         config.CICHY_DZIEN_NA_ILE)

    print()
    print("=" * 72)
    print(" 7/7  MONEY")
    print("=" * 72)
    print("  The monthly ceiling is the only hard stop in the system.")
    pole("pieniadze.sufit_miesieczny_usd", "Monthly ceiling, USD",
         config.MONTHLY_LIMIT_USD)
    pole("pieniadze.sufit_dzienny_usd", "Daily ceiling, USD", config.DAILY_LIMIT_USD)
    pole("pieniadze.sufit_przebiegu_usd", "Per-run ceiling, USD", config.RUN_LIMIT_USD)

    return dane


# --------------------------------------------------------------------------
def zapisz_toml(dane: dict) -> str:
    """Sklada TOML recznie — `tomllib` czyta, ale nie pisze.

    Pisanie recznie znaczy, ze kazda wartosc musi byc tu zacytowana poprawnie,
    wiec zaraz po zapisie plik jest ODCZYTYWANY z powrotem przez ten sam
    loader, ktorego uzywa bot. Bez tego kreator moglby wyprodukowac plik,
    ktorego bot nie przyjmie — i dowiedzialbys sie o tym przy pierwszym
    uruchomieniu, nie tutaj.
    """
    # JEDEN SERIALIZER, W LOADERZE. Ten plik mial wlasny, ze stala lista
    # sekcji (pomijal `stan_dziedziny` i `harmonogram`, nawet gdy dostal je
    # jako dane) i bez ucieczki nowej linii w napisie — dwuwierszowa nisza
    # dawala TOML, ktorego `tomllib` nie czytal (proby T07 i T08 audytu).
    # `konfiguracja.zapisz_toml` zna kazda sekcje z `POLA` i cytuje poprawnie.
    naglowek = [
        "# Written by narzedzia/kreator.py. Safe to edit by hand afterwards —",
        "# every field is validated on load, and an unknown key is a hard error.",
        "#",
        "# No API keys here, on purpose. They live in agent-v2/.env, which is",
        "# gitignored. This file is meant to be shareable.",
        "#",
        "# To run the bot from this file, turn it into a preset:",
        "#     python narzedzia/presety.py importuj-konfiguracje --nazwa <name>",
    ]
    return konfiguracja.zapisz_toml(dane, naglowek)


def _toml(v) -> str:
    """Zachowane dla zgodnosci z wolajacymi; deleguje do loadera."""
    return konfiguracja.toml_wartosc(v)


def zapisz_env(o: Odpowiadacz) -> list[str]:
    """Klucze API do `.env`. Nigdy do TOML-a, nigdy na ekran."""
    print()
    print("=" * 72)
    print(" KEYS")
    print("=" * 72)
    print("  These go to agent-v2/.env, which is gitignored. Nothing is echoed")
    print("  back and nothing is written into konfiguracja.toml.")

    istniejace: dict[str, str] = {}
    if PLIK_ENV.exists():
        for linia in PLIK_ENV.read_text(encoding="utf-8").splitlines():
            if "=" in linia and not linia.lstrip().startswith("#"):
                k, v = linia.split("=", 1)
                istniejace[k.strip()] = v.strip()

    zebrane = dict(istniejace)
    opis = []
    for nazwa, do_czego, wymagany in KLUCZE:
        if not o.interaktywnie:
            # W trybie nieinteraktywnym klucz bierzemy WYLACZNIE ze srodowiska.
            # Klucz w pliku odpowiedzi to klucz w pliku, ktory ktos skopiuje.
            wartosc = os.environ.get(nazwa, "").strip()
        else:
            juz = istniejace.get(nazwa, "")
            stan = "already set, %d chars" % len(juz) if juz else "not set"
            print()
            print("  %s — %s (%s)" % (nazwa, do_czego, stan))
            if not wymagany:
                print("    Optional. Empty means articles publish without a cover.")
            try:
                wartosc = input("    > ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n  przerwane")
                raise SystemExit(1)
        if wartosc:
            zebrane[nazwa] = wartosc
        stan = zebrane.get(nazwa, "")
        opis.append("%s: %s" % (nazwa, "%d chars" % len(stan) if stan else "EMPTY"))

    for domyslne in (("DRY_RUN", "true"), ("KILL_SWITCH", "false")):
        zebrane.setdefault(*domyslne)

    linie = ["# Written by narzedzia/kreator.py. Never commit this file.",
             "# DRY_RUN stays true until you have read docs/INSTALL.md."]
    for k in sorted(zebrane):
        linie.append("%s=%s" % (k, zebrane[k]))
    PLIK_ENV.write_text("\n".join(linie) + "\n", encoding="utf-8")
    return opis


# --------------------------------------------------------------------------
def pokaz_biezace() -> int:
    print("Current values, as the bot would use them right now:")
    print()
    for sciezka, (stala, _) in sorted(konfiguracja.POLA.items()):
        if stala is None:
            print("  %-38s (handled separately)" % sciezka)
            continue
        print("  %-38s %s" % (sciezka, _pokaz(getattr(config, stala, "?"))))
    print()
    print("konfiguracja.toml: %s" % ("present" if PLIK_TOML.exists() else "absent"))
    print(".env:              %s" % ("present" if PLIK_ENV.exists() else "absent"))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pokaz", action="store_true",
                    help="print current values and exit, writing nothing")
    ap.add_argument("--z-pliku", dest="z_pliku", default="",
                    help="answer from a JSON file instead of asking")
    ap.add_argument("--bez-kluczy", action="store_true",
                    help="skip the keys section (leave .env alone)")
    ap.add_argument("--wsad", default="",
                    help="start from a subject pack (see: python "
                         "narzedzia/pakiety.py)")
    args = ap.parse_args()

    if args.pokaz:
        return pokaz_biezace()

    wsad = None
    if args.wsad:
        sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
        import pakiety                                       # noqa: E402
        try:
            plik = pakiety.znajdz(args.wsad)
            wsad, uwagi = pakiety.waliduj(plik)
        except pakiety.ZlyPakiet as exc:
            print("  ! %s" % exc)
            return 1
        # WSAD MA PRZEJSC TE SAME REGULY, CO KAZDA KONFIGURACJA. Wsad z cudzego
        # pull requesta, ktory lamie regule strukturalna, dalby bota szukajacego
        # po ciasnej puli — i nikt by sie nie dowiedzial przed pierwszym pustym
        # przebiegiem.
        lamie = pakiety.reguly_strukturalne(wsad, config)
        if lamie:
            print("  ! wsad `%s` lamie reguly:" % plik.stem)
            for w in lamie:
                print("      %s" % w)
            return 1
        opis = pakiety.wczytaj(plik)["pack"]
        print()
        print("  WSAD: %s (%s)" % (opis["name"], opis["language"]))
        print("  %s" % opis["description"])
        print("  Kazda wartosc z niego jest DOMYSLNA — mozesz ja nadpisac.")
        for u in uwagi:
            print("    uwaga: %s" % u)

    gotowe = None
    if args.z_pliku:
        gotowe = json.loads(pathlib.Path(args.z_pliku).read_text(encoding="utf-8"))
    o = Odpowiadacz(gotowe, wsad)

    if o.interaktywnie:
        print()
        print("NIA Substack Bot — setup")
        print()
        print("Enter alone keeps the current value, shown in brackets. Nothing is")
        print("written until the last question is answered.")

    dane = zbierz(o)
    tresc = zapisz_toml(dane)
    PLIK_TOML.write_text(tresc, encoding="utf-8")

    # ODCZYT NATYCHMIAST PO ZAPISIE. Kreator, ktory pisze plik odrzucany przez
    # loader, jest gorszy od braku kreatora: wyglada na sukces.
    try:
        wczytane = konfiguracja.wczytaj(PLIK_TOML)
    except konfiguracja.BledKonfiguracji as exc:
        print()
        print("!! the file this program just wrote is not accepted by the loader:")
        print("   %s" % exc)
        print("   left in place for inspection: %s" % PLIK_TOML)
        return 1

    opis_kluczy = [] if args.bez_kluczy else zapisz_env(o)

    print()
    print("=" * 72)
    print(" WRITTEN")
    print("=" * 72)
    print("  %s   %d fields, all accepted by the loader"
          % (PLIK_TOML.relative_to(KORZEN), len(wczytane)))
    for wiersz in opis_kluczy:
        print("  .env  %s" % wiersz)
    print()
    print("  Where each field lands:")
    for sciezka in sorted(wczytane):
        stala = konfiguracja.POLA[sciezka][0]
        print("    %-38s -> config.%s" % (sciezka, stala or "(handled in zastosuj)"))
    print()
    print("=" * 72)
    print(" WHAT THIS PROGRAM CANNOT DO FOR YOU")
    print("=" * 72)
    print("  Three things are left, and none of them is an oversight. Each is")
    print("  something no configuration file can settle.")
    print()
    print("  1. THE SUBSTACK SESSION — a human has to log in.")
    print("     Substack signs you in with a link sent to your email, so the")
    print("     agent on a server has no way to complete it. Worse, a browser")
    print("     started by automation fails the CAPTCHA even for a person:")
    print("     the check scores the whole session, not the click.")
    print("        python agent-v2/browser.py zaloguj")
    print("     Then docs/INSTALL.md step 5 to move the session to a server.")
    print()
    print("  2. THE STYLE CORPUS — it has to be yours.")
    print("     The writer learns its voice from prose you supply. This is")
    print("     not a technical gap: shipping somebody else's writing here")
    print("     is republishing their work. Notes, comments and research all")
    print("     run without it; only the article path stops.")
    print("        agent-v2/prompts/styl/README.md")
    print("        python narzedzia/przypnij_styl.py --pokaz")
    print()
    print("  3. THE AI-DISCLOSURE STATEMENT — the wording is yours to decide.")
    print("     Read agent-v2/prompts/OSWIADCZENIE_AUTORSTWA.md and decide what")
    print("     your account says when asked. Setting it IS automated, and this")
    print("     line used to say otherwise while the code sat unreachable:")
    print("        python agent-v2/browser.py oswiadczenie            # dry")
    print("        python agent-v2/browser.py oswiadczenie --wyslij   # for real")
    print("     Nothing will tell you if you skip it.")
    print()
    print("  One thing this program CAN do, but only once you know where the")
    print("  bot will live on the server:")
    print()
    print("  4. THE SYSTEMD UNITS carry an install path, a system user and your")
    print("     brand name. The copies in agent-v2/systemd/ are templates and")
    print("     still hold the paths of the machine they were written on — a")
    print("     unit copied from there starts in a directory that does not")
    print("     exist and says somebody else's name in `systemctl status`.")
    print("        python narzedzia/jednostki.py --katalog /srv/bot --uzytkownik bot")
    print("     Writes agent-v2/systemd/dla-tej-instalacji/ and prints the")
    print("     three things that must exist on the server before you copy it.")
    print()
    print("  Then, in this order:")
    print("     python agent-v2/alarm.py        # health check: names what is missing")
    print("     python narzedzia/audyt.py       # nothing from another account leaked in")
    print("     docs/INSTALL.md                 # read before DRY_RUN=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
