# -*- coding: utf-8 -*-
"""Odcisk glosu: te same miary na kazdym tekscie, pasmo z tekstow przyjetych przez wlasciciela.

## Po co to istnieje

„Glos jest nierowny" nie jest pomiarem. Wlasciciel raz policzyl recznie, czym
przyjety artykul rozni sie od dwoch odrzuconych: slowa na zdanie, krotkie
akapity, zdania do czytelnika, asekuracje, zargon, linki w tresci, atrybucje
na sto slow, zdania o byciu AI. Ta tabela stala w bloku glosu kartridza i byla
najkonkretniejsza rzecza, jaka o glosie NIA zapisano — tyle ze policzona raz,
recznie, na trzech tekstach. Ten skrypt liczy to samo na KAZDYM tekscie, tym
samym sposobem, wiec dwa teksty da sie porownac, a jeden da sie porownac
z tym, co wlasciciel przyjal.

## Czym to NIE jest

Nie jest bramka. Reguly na forme („kazdy tekst konczy sie zwrotem do
czytelnika") po dziesieciu tekstach staja sie podpisem maszyny — ten projekt
juz to zmierzyl (`gates.py`, `ostatnie_uwagi`). Odcisk jest OBSERWACJA dla
czlowieka: pokazuje, po ktorej stronie pasma lezy tekst, i ktore zdania
policzyl, zeby dalo sie sprawdzic, czy policzyl slusznie. Decyzja zostaje
u wlasciciela; jego werdykty ida do wzorca, a wzorzec wyznacza pasmo.

Liczby z tego skryptu NIE MUSZA zgadzac sie co do jednego z reczna tabela:
reczny licznik uznawal „niewyjasniony" zargon i „zwrot do czytelnika" wedle
wlasnego osadu, ktorego kod nie ma. Liczy sie to, ze ta sama miarka lezy na
kazdym tekscie. `--kalibracja` pokazuje obie kolumny obok siebie.

## Wzorzec

Katalog `styl/wzorzec/` w kartridzu (domyslnie: aktywnego presetu). Kazdy
plik zaczyna sie wierszem `forma: notka|artykul|rozmowa`, a probki oddziela
naglowek `## `. Wiersze `Reader:` (pytanie w rozmowie), `Source:` i wiersze
bedace samym `[podpisem linku]` nie sa tekstem NIA i nie wchodza do pomiaru.
Pasmo dla kazdej miary = od najmniejszej do najwiekszej wartosci wsrod probek
tej samej formy. Wzorzec zawiera WYLACZNIE teksty, ktore wlasciciel przyjal.

## Uzycie (z korzenia repozytorium)

  python narzedzia/odcisk_glosu.py PLIK [PLIK ...]     odcisk plikow wobec pasma
  python narzedzia/odcisk_glosu.py --wzorzec-pokaz     odciski probek wzorca i pasma
  python narzedzia/odcisk_glosu.py --kalibracja        przyjety artykul wobec recznej tabeli
  python narzedzia/odcisk_glosu.py --z-instancji [--ostatnie N]
                                                       trend: artykuly i szkice notek aktywnej instancji
  --wzorzec KATALOG   inny wzorzec niz `styl/wzorzec` aktywnego presetu
  --forma FORMA       wymus forme porownania (domyslnie z nazwy pliku albo dlugosci)
  --zdania            wypisz zdania, ktore policzono (asekuracje, atrybucje, zargon, AI)
  --json              wynik jako JSON, jeden obiekt na tekst

Bez sieci i bez wywolan modelu. Nie zapisuje niczego.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from proba_glosu import IMPERATIVES, REVIEWER_WORDS, STRONG_WORDS, _addressed, _last_sentence  # noqa: E402

FORMY = ("notka", "artykul", "rozmowa")

# Zwroty asekuracji — jezyk raportu, ktory NIE MOWI, co autorka mysli. Nie ma
# tu „apparently" ani „allegedly": pierwsze u NIA jest sarkazmem (przyjety
# artykul ma je cztery razy i wlasciciel policzyl zero asekuracji), drugie
# jest atrybucja, nie asekuracja.
ASEKURACJE = (
    "it seems", "seems to", "seem to", "appears to", "appear to", "arguably",
    "perhaps", "maybe", "to some extent", "to a degree", "somewhat",
    "in some ways", "in a sense", "it is possible", "it's possible", "may well",
    "might be", "could be argued", "one could argue", "is likely to",
    "are likely to", "it remains to be seen", "it is unclear", "it's unclear",
    "not entirely clear", "broadly speaking", "generally speaking",
    "at least in part", "for what it's worth", "more or less", "sort of",
    "kind of", "if anything", "in theory", "on paper at least", "presumably",
    "ostensibly", "supposedly", "it is worth noting", "it's worth noting",
    "it should be noted", "to be fair", "in fairness",
    # Jezyk ograniczen materialu, ktory wlasciciel policzyl jako asekuracje
    # w odrzuconym artykule o konstytucji agentow: „the supplied evidence
    # doesn't establish whether...", „not a claim that...", „hypothetical".
    "doesn't establish", "does not establish", "not established", "cannot settle",
    "can't settle", "whether or not", "isn't clear", "is not clear",
    "not a claim that", "hypothetical", "we don't know", "no way to know",
    "hard to say", "hard to tell", "might work", "may be to", "may not",
    "it depends", "at best,", "at worst,", "would need to", "worth taking seriously",
)

# Slowa z rejestru karty dowodowej i prezentacji. „sandbox" celowo NIE JEST na
# liscie: przyjety artykul uzywa go cztery razy i za kazdym razem tlumaczy,
# a wlasciciel policzyl jeden niewyjasniony termin — „execution", i ten tu jest.
ZARGON = (
    "baseline", "regime", "incidence", "runtime", "manifest", "framework",
    "orchestration", "orchestrate", "pipeline", "latency", "throughput",
    "inference", "benchmark", "deployment", "endpoint", "telemetry",
    "execution", "heuristic", "stochastic", "deterministic", "architecture",
    "tokenisation", "tokenization", "embedding", "embeddings", "agentic",
    "workflow", "workflows", "governance", "alignment", "mitigation",
    "threat model", "attack surface", "privilege escalation", "instantiate",
    "parameterise", "parametrize", "paradigm", "leverage", "ecosystem",
    "stakeholder", "stakeholders", "scalable", "scalability", "robustness",
    "modality", "multimodal", "interoperability", "provenance", "guardrail",
    "guardrails", "optimisation", "optimization", "granular", "actionable",
    "synergy", "utilise", "utilize",
)

# Atrybucje: liczone PO ZDANIACH, nie po trafieniach — „documentation says"
# to jedna atrybucja, nie dwie. „advisory" samo w sobie nie jest atrybucja
# (mozna napisac „the advisory doesn't show", nie przypisujac nikomu zdania).
ATRYBUCJE = (
    "according to", r"\bsays\b", r"\bsaid\b", r"\bdescribes\b", r"\bdescribed\b",
    r"\breports\b", r"\breported\b", r"\bclaims\b", r"\bclaimed\b",
    r"\bstates\b", r"\bstated\b", r"\bwrote\b", r"\bwrites\b",
    r"\bannounced\b", r"\bannounces\b", r"\btold\b", "puts it", "in its words",
    "in their words", r"\bper the\b", "as reported", "the write-up",
    r"\bnotes that\b", r"\bnoted that\b", r"\badmits\b", r"\badmitted\b",
    r"\bconfirms\b", r"\bconfirmed\b", r"\bexplains\b", r"\bexplained\b",
)

# Zdanie o byciu AI: pierwsza osoba + slowo o maszynie w tym samym zdaniu.
PIERWSZA_OSOBA = re.compile(r"\b(i|i'm|i've|i'd|i'll|me|my|myself)\b", re.IGNORECASE)
SLOWA_O_MASZYNIE = re.compile(
    r"\b(an? ai\b|(i'm|i am|as|being) ai\b|ai (woman|agent|writer|girl|with a personality)\b|"
    r"software|language model|a bot\b|a machine\b|an algorithm|artificial intelligence|"
    r"a program\b|a chatbot)",
    re.IGNORECASE)
ZWROT_DO_CZYTELNIKA = re.compile(r"\b(you|your|yours|yourself|yourselves|let's|lets)\b", re.IGNORECASE)
TA_SAMA_KONSTRUKCJA = re.compile(r"that'?s not [^.!?]+[.!?]\s+that'?s\b", re.IGNORECASE)
LINK = re.compile(r"https?://\S+|\bwww\.\S+", re.IGNORECASE)
PODPIS_LINKU = re.compile(r"^\s*\[[^\]]+\]\s*$")
ROZKAZY = IMPERATIVES | {
    "check", "picture", "please", "consider", "notice", "think", "spend",
    "compare", "bring", "wait", "stay", "listen", "note", "start", "send",
    "move", "hold", "get", "find", "run", "use", "write", "add", "drop",
    "forget", "ignore", "skip", "sit", "let", "put", "make", "try", "do",
    "go", "read", "credit", "say", "ask", "watch", "call", "stop", "pay",
    "name", "look", "give", "take", "leave", "remember", "keep", "tell",
    "show", "answer", "explain", "count", "spare", "imagine", "open", "close",
    "pick", "choose", "treat", "buy", "sell", "believe", "trust", "test",
}

# Reczna tabela wlasciciela dla PRZYJETEGO artykulu — do `--kalibracja`.
TABELA_WLASCICIELA = {
    "slow_na_zdanie": 9, "akapity_krotkie": 5, "do_czytelnika": 9,
    "asekuracje": 0, "zargon": 1, "linki": 0, "atrybucje_na_100": 0.31,
    "zdania_o_ai": 1,
}

# Miary, ktorych NADMIAR czytal sie u wlasciciela jako „raport, nie glos".
MIARY_RAPORTU = ("asekuracje", "zargon", "linki", "atrybucje_na_100",
                 "zdania_o_ai", "slowa_recenzenta", "ta_sama_konstrukcja")
# Miary, ktore mowia, ze w tekscie JEST osoba.
MIARY_GLOSU = ("do_czytelnika_na_100", "pierwsza_osoba_udzial",
               "akapity_krotkie_udzial", "slow_na_zdanie")
MIARY_PASMA = MIARY_RAPORTU + MIARY_GLOSU


# ---------------------------------------------------------------- tekst
def akapity(tekst: str) -> list[str]:
    return [a.strip() for a in re.split(r"\n\s*\n", tekst.strip()) if a.strip()]


def zdania(tekst: str) -> list[str]:
    """Zdania po kropce, wykrzykniku albo pytajniku; cudzyslow po znaku zostaje przy zdaniu."""
    plaski = " ".join(tekst.split())
    # Dwa look-behindy o STALEJ szerokosci (znak konca zdania, albo znak konca
    # zdania i cudzyslow/nawias) — `re` nie przyjmuje look-behindu ze znakiem
    # opcjonalnym.
    czesci = re.split(r"(?:(?<=[.!?])|(?<=[.!?][\"'”’)]))\s+(?=[\"'“‘(]?[A-Z0-9])", plaski)
    return [z.strip() for z in czesci if z.strip()]


def slowa(tekst: str) -> int:
    return len(tekst.split())


def cialo_artykulu(tekst: str) -> tuple[str, str, str]:
    """(tytul, podtytul, tresc) z pliku artykulu; lista zrodel i stopka z data odpadaja."""
    linie = tekst.replace("\r\n", "\n").split("\n")
    tytul = podtytul = ""
    reszta: list[str] = []
    for linia in linie:
        s = linia.strip()
        if not tytul and s.startswith("# "):
            tytul = s[2:].strip()
            continue
        if tytul and not podtytul and not any(r.strip() for r in reszta) \
                and s.startswith("*") and s.endswith("*") and len(s) > 2:
            podtytul = s.strip("*").strip()
            reszta = []
            continue
        if not reszta and not s:
            continue
        reszta.append(linia)
    tresc = "\n".join(reszta)
    for znacznik in ("\n## Sources", "\n## Źródła", "\n## Zrodla"):
        if znacznik in tresc:
            tresc = tresc.split(znacznik, 1)[0]
    tresc = re.sub(r"(?m)^Figures checked against sources to .*$", "", tresc)
    tresc = re.sub(r"(?m)^---\s*$", "", tresc)
    return tytul, podtytul, tresc.strip()


def tekst_probki(surowy: str) -> str:
    """Tekst NIA z probki wzorca: bez pytan czytelnika, zrodel i podpisow linkow."""
    wynik = []
    for linia in surowy.replace("\r\n", "\n").split("\n"):
        s = linia.strip()
        if s.startswith("Reader:") or s.startswith("Source:") or s.startswith("Czytelnik:"):
            continue
        if PODPIS_LINKU.match(s):
            continue
        wynik.append(linia)
    return "\n".join(wynik).strip()


# ---------------------------------------------------------------- miary
def _zdanie_zawiera(zdanie: str, wzorce) -> bool:
    low = zdanie.lower()
    for w in wzorce:
        if w.startswith("\\b") or w.endswith("\\b"):
            if re.search(w, low):
                return True
        elif w in low:
            return True
    return False


def _rozkaz(zdanie: str) -> bool:
    m = re.match(r"^[\"'“‘(]?([a-z']+)", zdanie.lower())
    return bool(m and m.group(1) in ROZKAZY)


def odcisk(tekst: str, forma: str = "") -> dict:
    """Wszystkie miary jednego tekstu. Deterministyczne: ten sam tekst, ten sam wynik."""
    tekst = tekst.replace("\r\n", "\n")
    aka = akapity(tekst)
    zd = zdania(tekst)
    n_slow = max(1, slowa(tekst))
    n_zdan = max(1, len(zd))
    low = tekst.lower()

    asekuracje = [z for z in zd if _zdanie_zawiera(z, ASEKURACJE)]
    zargon_slowa = sorted({w for w in ZARGON if re.search(r"\b%s\b" % re.escape(w), low)})
    zargon_zdania = [z for z in zd if any(re.search(r"\b%s\b" % re.escape(w), z.lower()) for w in zargon_slowa)]
    linki = LINK.findall(tekst)
    atrybucje = [z for z in zd if _zdanie_zawiera(z, ATRYBUCJE)]
    o_ai = [z for z in zd if PIERWSZA_OSOBA.search(z) and SLOWA_O_MASZYNIE.search(z)]
    zwroty_you = [z for z in zd if ZWROT_DO_CZYTELNIKA.search(z)]
    rozkazy = [z for z in zd if _rozkaz(z) and not ZWROT_DO_CZYTELNIKA.search(z)]
    do_czyt = zwroty_you + rozkazy
    przekl = sum(low.count(w) for w in STRONG_WORDS)
    recenzent = [w for w in REVIEWER_WORDS if w in low]
    pierwsza = [z for z in zd if PIERWSZA_OSOBA.search(z)]
    krotkie = [a for a in aka if slowa(a) < 12]
    konstrukcja = len(TA_SAMA_KONSTRUKCJA.findall(tekst))

    return {
        "forma": forma,
        "slowa": n_slow if tekst.strip() else 0,
        "zdania": len(zd),
        "akapity": len(aka),
        "slow_na_zdanie": round(n_slow / n_zdan, 1),
        "akapity_krotkie": len(krotkie),
        "akapity_krotkie_udzial": round(100.0 * len(krotkie) / max(1, len(aka)), 1),
        "do_czytelnika": len(do_czyt),
        "zwroty_you": len(zwroty_you),
        "rozkazy": len(rozkazy),
        "do_czytelnika_na_100": round(100.0 * len(do_czyt) / n_slow, 2),
        "asekuracje": len(asekuracje),
        "zargon": len(zargon_zdania),
        "zargon_slowa": zargon_slowa,
        "linki": len(linki),
        "atrybucje": len(atrybucje),
        "atrybucje_na_100": round(100.0 * len(atrybucje) / n_slow, 2),
        "zdania_o_ai": len(o_ai),
        "przeklenstwa": przekl,
        "slowa_recenzenta": len(recenzent),
        "pierwsza_osoba_udzial": round(100.0 * len(pierwsza) / n_zdan, 1),
        "koniec_wycelowany": _addressed(_last_sentence(tekst)),
        "ta_sama_konstrukcja": konstrukcja,
        "wykrzykniki": tekst.count("!"),
        "_zdania": {"asekuracje": asekuracje, "atrybucje": atrybucje,
                    "zargon": zargon_zdania, "zdania_o_ai": o_ai,
                    "do_czytelnika": do_czyt, "slowa_recenzenta": recenzent},
    }


# ---------------------------------------------------------------- wzorzec
def wczytaj_wzorzec(katalog: Path) -> list[dict]:
    """Probki z plikow `*.md` katalogu: {plik, tytul, forma, tekst}."""
    probki: list[dict] = []
    for plik in sorted(Path(katalog).glob("*.md")):
        if plik.name.upper() == "README.MD":
            continue
        tekst = plik.read_text(encoding="utf-8").replace("\r\n", "\n")
        m = re.search(r"(?m)^forma:\s*(\w+)\s*$", tekst)
        forma = (m.group(1).lower() if m else "")
        if forma not in FORMY:
            raise ValueError("%s: brak wiersza `forma: notka|artykul|rozmowa`" % plik)
        if forma == "artykul":
            # Jeden plik = jeden artykul. Naglowki `## ` W artykule (np. lista
            # zrodel) nie sa probkami; `cialo_artykulu` odcina liste i stopke.
            czesci = re.split(r"(?m)^## +", tekst, maxsplit=1)
        else:
            czesci = re.split(r"(?m)^## +", tekst)
        for czesc in czesci[1:]:
            naglowek, _, cialo = czesc.partition("\n")
            if naglowek.strip().lower() in ("sources", "źródła", "zrodla"):
                continue
            t = tekst_probki(cialo)
            if forma == "artykul":
                t = cialo_artykulu(t)[2] if t.lstrip().startswith("# ") else cialo_artykulu("# x\n\n" + t)[2]
            if t:
                probki.append({"plik": plik.name, "tytul": naglowek.strip(), "forma": forma, "tekst": t})
    if not probki:
        raise ValueError("wzorzec %s nie ma zadnej probki (naglowki `## ` w plikach z `forma:`)" % katalog)
    return probki


LICZNIKI = ("asekuracje", "zargon", "linki", "zdania_o_ai", "slowa_recenzenta", "ta_sama_konstrukcja")


def _z_tolerancja(miara: str, lo: float, hi: float) -> tuple[float, float]:
    """Pasmo z zapasem, bo wzorzec ma kilka probek, nie tysiac.

    Liczniki (asekuracje, linki, zdania o AI...) dostaja o JEDEN wiecej niz
    najwieksza przyjeta wartosc — jeden wiecej niz wlasciciel przyjal nie jest
    jeszcze raportem. Miary ciagle dostaja po 20 % rozpietosci z kazdej strony,
    a przy jednej probce (rozpietosc zero) 10 % wartosci; w dol nigdy ponizej zera.
    """
    if miara in LICZNIKI:
        return (0.0, hi + 1)
    zapas = max(0.2 * (hi - lo), 0.1 * abs(hi), 0.05)
    sufit = 100.0 if miara.endswith("_udzial") else float("inf")
    return (round(max(0.0, lo - zapas), 2), round(min(sufit, hi + zapas), 2))


def pasma(probki: list[dict]) -> dict[str, dict[str, tuple[float, float]]]:
    """Dla kazdej formy: miara -> (min, max) po probkach tej formy, z tolerancja `_z_tolerancja`."""
    wynik: dict[str, dict[str, tuple[float, float]]] = {}
    for forma in FORMY:
        odciski = [odcisk(p["tekst"], forma) for p in probki if p["forma"] == forma]
        if not odciski:
            continue
        wynik[forma] = {m: _z_tolerancja(m, min(o[m] for o in odciski), max(o[m] for o in odciski))
                        for m in MIARY_PASMA}
        wynik[forma]["_ile"] = (len(odciski), len(odciski))
        wynik[forma]["_koniec_wycelowany"] = (sum(1 for o in odciski if o["koniec_wycelowany"]), len(odciski))
    return wynik


def ocen(o: dict, pasmo: dict[str, tuple[float, float]]) -> dict[str, str]:
    """Miara -> `w pasmie` | `ponizej` | `powyzej` (miary raportu: `powyzej` = jak w odrzuconych)."""
    wynik = {}
    for m in MIARY_PASMA:
        lo, hi = pasmo[m]
        v = o[m]
        wynik[m] = "w pasmie" if lo <= v <= hi else ("ponizej" if v < lo else "powyzej")
    return wynik


def forma_z_nazwy(sciezka: Path, tekst: str) -> str:
    n = sciezka.name.lower()
    if "notk" in n or "note" in n:
        return "notka"
    if "rozmow" in n or "chat" in n or "conversation" in n:
        return "rozmowa"
    if "artyk" in n or "article" in n or sciezka.suffix == ".md" and tekst.lstrip().startswith("# "):
        return "artykul"
    return "artykul" if slowa(tekst) > 250 else "notka"


# ---------------------------------------------------------------- wydruk
def _wiersz(nazwa: str, v, status: str = "", pasmo=None) -> str:
    zakres = "" if pasmo is None else "  [%s .. %s]" % (pasmo[0], pasmo[1])
    return "  %-24s %8s   %-9s%s" % (nazwa, v, status, zakres)


def wypisz(nazwa: str, o: dict, pasmo: dict | None, zdania_tez: bool = False) -> None:
    print("== %s  (%s: %d slow, %d zdan, %d akapitow)" % (nazwa, o["forma"] or "?", o["slowa"], o["zdania"], o["akapity"]))
    oceny = ocen(o, pasmo) if pasmo else {}
    print("  -- raport, nie glos (powyzej pasma = jak w odrzuconych):")
    for m in MIARY_RAPORTU:
        print(_wiersz(m, o[m], oceny.get(m, ""), pasmo.get(m) if pasmo else None))
    print("  -- osoba w tekscie:")
    for m in MIARY_GLOSU:
        print(_wiersz(m, o[m], oceny.get(m, ""), pasmo.get(m) if pasmo else None))
    dodatkowe = "  przeklenstwa %d, wykrzykniki %d, zwroty `you` %d, rozkazy %d, koniec wycelowany: %s" % (
        o["przeklenstwa"], o["wykrzykniki"], o["zwroty_you"], o["rozkazy"],
        "tak" if o["koniec_wycelowany"] else "nie")
    if pasmo and "_koniec_wycelowany" in pasmo:
        dodatkowe += " (wzorzec: %d/%d)" % pasmo["_koniec_wycelowany"]
    print(dodatkowe)
    if o["zargon_slowa"]:
        print("  zargon z listy: %s" % ", ".join(o["zargon_slowa"]))
    if oceny:
        w = sum(1 for s in oceny.values() if s == "w pasmie")
        print("  W PASMIE: %d z %d miar" % (w, len(oceny)))
    if zdania_tez:
        for klucz in ("asekuracje", "atrybucje", "zargon", "zdania_o_ai"):
            for z in o["_zdania"][klucz]:
                print("    [%s] %s" % (klucz, z[:160]))
    print()


def _bez_zdan(o: dict) -> dict:
    return {k: v for k, v in o.items() if not k.startswith("_")}


# ---------------------------------------------------------------- instancja
def _katalog_wzorca_z_presetu() -> Path | None:
    try:
        import config                                             # noqa: PLC0415
    except Exception:                                             # noqa: BLE001
        return None
    preset = getattr(config, "PRESET", None)
    katalog = getattr(preset, "katalog", None)
    return Path(katalog) / "styl" / "wzorzec" if katalog else None


def teksty_z_instancji(ostatnie: int) -> list[dict]:
    """Artykuly (`articles/*.md`) i szkice notek (`persona-drafts/*.json`) aktywnej instancji, po dacie."""
    import config                                                 # noqa: PLC0415
    dane = Path(config.DATA_DIR)
    wynik: list[dict] = []
    for plik in sorted((dane / "articles").glob("*.md")):
        if plik.name.endswith(".uwagi.md"):
            continue
        tytul, _, tresc = cialo_artykulu(plik.read_text(encoding="utf-8"))
        kiedy = datetime.fromtimestamp(plik.stat().st_mtime, tz=timezone.utc)
        wynik.append({"kiedy": kiedy, "nazwa": plik.name, "forma": "artykul", "tekst": tresc, "tytul": tytul})
    for plik in (dane / "persona-drafts").glob("*.json"):
        try:
            rekord = json.loads(plik.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(rekord, dict) or rekord.get("kind", "note") != "note":
            continue
        tekst = str(rekord.get("text") or "").strip()
        if not tekst:
            continue
        kiedy = None
        if rekord.get("created_at"):
            try:
                kiedy = datetime.fromisoformat(str(rekord["created_at"]))
            except ValueError:
                kiedy = None
        if kiedy is None:
            kiedy = datetime.fromtimestamp(plik.stat().st_mtime, tz=timezone.utc)
        if kiedy.tzinfo is None:
            kiedy = kiedy.replace(tzinfo=timezone.utc)
        wynik.append({"kiedy": kiedy, "nazwa": plik.name, "forma": "notka", "tekst": tekst,
                      "tytul": str(rekord.get("topic") or "")[:60], "status": rekord.get("status")})
    wynik.sort(key=lambda r: r["kiedy"])
    return wynik[-ostatnie:] if ostatnie else wynik


def trend(rekordy: list[dict], pas: dict, jako_json: bool) -> None:
    if jako_json:
        for r in rekordy:
            o = odcisk(r["tekst"], r["forma"])
            print(json.dumps({"kiedy": r["kiedy"].isoformat(), "nazwa": r["nazwa"], "forma": r["forma"],
                              "odcisk": _bez_zdan(o),
                              "ocena": ocen(o, pas[r["forma"]]) if r["forma"] in pas else {}},
                             ensure_ascii=False))
        return
    print("%-17s %-8s %5s %6s %5s %5s %6s %5s %5s %6s  %s" % (
        "kiedy", "forma", "slowa", "s/zd", "asek", "zarg", "atr/100", "AI", "linki", "pasmo", "tytul"))
    for r in rekordy:
        o = odcisk(r["tekst"], r["forma"])
        w = ""
        if r["forma"] in pas:
            oceny = ocen(o, pas[r["forma"]])
            w = "%d/%d" % (sum(1 for s in oceny.values() if s == "w pasmie"), len(oceny))
        print("%-17s %-8s %5d %6s %5d %5d %6s %5d %5d %6s  %s" % (
            r["kiedy"].strftime("%Y-%m-%d %H:%M"), r["forma"], o["slowa"], o["slow_na_zdanie"],
            o["asekuracje"], o["zargon"], o["atrybucje_na_100"], o["zdania_o_ai"], o["linki"], w,
            r.get("tytul", "")[:48]))


# ---------------------------------------------------------------- main
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Odcisk glosu wobec wzorca przyjetych tekstow.")
    parser.add_argument("pliki", nargs="*", help="teksty do zmierzenia (.md albo .txt)")
    parser.add_argument("--wzorzec", help="katalog wzorca (domyslnie styl/wzorzec aktywnego presetu)")
    parser.add_argument("--wzorzec-pokaz", action="store_true", help="odciski probek wzorca i pasma")
    parser.add_argument("--kalibracja", action="store_true", help="przyjety artykul wobec recznej tabeli wlasciciela")
    parser.add_argument("--z-instancji", action="store_true", help="trend po artykulach i szkicach notek aktywnej instancji")
    parser.add_argument("--ostatnie", type=int, default=0, help="ile ostatnich tekstow instancji (0 = wszystkie)")
    parser.add_argument("--forma", choices=FORMY, help="wymus forme porownania")
    parser.add_argument("--zdania", action="store_true", help="wypisz policzone zdania")
    parser.add_argument("--json", action="store_true", help="wynik jako JSON")
    args = parser.parse_args(argv)

    katalog = Path(args.wzorzec) if args.wzorzec else _katalog_wzorca_z_presetu()
    if katalog is None or not katalog.is_dir():
        parser.error("nie znajduje wzorca: podaj --wzorzec KATALOG albo podlacz preset ze `styl/wzorzec/`")
    probki = wczytaj_wzorzec(katalog)
    pas = pasma(probki)

    if args.wzorzec_pokaz:
        for p in probki:
            o = odcisk(p["tekst"], p["forma"])
            if args.json:
                print(json.dumps({"probka": p["tytul"], "plik": p["plik"], "odcisk": _bez_zdan(o)}, ensure_ascii=False))
            else:
                wypisz("%s: %s" % (p["plik"], p["tytul"]), o, pas.get(p["forma"]), args.zdania)
        if not args.json:
            for forma, pasmo in pas.items():
                print("== pasmo %s (%d probek):" % (forma, pasmo["_ile"][0]))
                for m in MIARY_PASMA:
                    print(_wiersz(m, "", "", pasmo[m]))
                print()
        return 0

    if args.kalibracja:
        artykuly = [p for p in probki if p["forma"] == "artykul"]
        if not artykuly:
            parser.error("wzorzec nie ma artykulu")
        o = odcisk(artykuly[0]["tekst"], "artykul")
        print("kalibracja na: %s (%d slow)" % (artykuly[0]["tytul"], o["slowa"]))
        print("  %-20s %10s %10s" % ("miara", "wlasciciel", "skrypt"))
        rozne = 0
        for m, v in TABELA_WLASCICIELA.items():
            zgoda = abs(float(o[m]) - float(v)) <= (0.1 if isinstance(v, float) else 1)
            rozne += 0 if zgoda else 1
            print("  %-20s %10s %10s %s" % (m, v, o[m], "" if zgoda else "  <- roznica"))
        print("miary zgodne z reczna tabela (tolerancja 1 albo 0,1): %d z %d"
              % (len(TABELA_WLASCICIELA) - rozne, len(TABELA_WLASCICIELA)))
        print("  (do_czytelnika = zwroty `you` %d + rozkazy %d; reczna tabela liczyla wezej,"
              " wedle osadu, ktorego kod nie ma)" % (o["zwroty_you"], o["rozkazy"]))
        if args.zdania:
            wypisz(artykuly[0]["tytul"], o, pas.get("artykul"), True)
        return 0

    if args.z_instancji:
        rekordy = teksty_z_instancji(args.ostatnie)
        if not rekordy:
            print("instancja nie ma jeszcze artykulow ani szkicow notek")
            return 0
        trend(rekordy, pas, args.json)
        return 0

    if not args.pliki:
        parser.error("podaj pliki do zmierzenia albo --wzorzec-pokaz / --kalibracja / --z-instancji")
    for nazwa in args.pliki:
        sciezka = Path(nazwa)
        surowy = sciezka.read_text(encoding="utf-8")
        forma = args.forma or forma_z_nazwy(sciezka, surowy)
        tekst = cialo_artykulu(surowy)[2] if forma == "artykul" else tekst_probki(surowy)
        o = odcisk(tekst, forma)
        if args.json:
            print(json.dumps({"plik": str(sciezka), "odcisk": _bez_zdan(o),
                              "ocena": ocen(o, pas[forma]) if forma in pas else {}}, ensure_ascii=False))
        else:
            wypisz(str(sciezka), o, pas.get(forma), args.zdania)
            if forma not in pas:
                print("  (wzorzec nie ma probek formy %s — bez pasma)" % forma)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
