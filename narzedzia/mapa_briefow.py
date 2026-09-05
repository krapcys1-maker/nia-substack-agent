# -*- coding: utf-8 -*-
"""Mapa powiazan: co robi kazdy brief, kto go wola i CO Z JEGO WYNIKU CZYTA KOD.

## Po co to istnieje

Mapy w tym repozytorium odpowiadaly na pytanie „gdzie to jest". Nie
odpowiadaly na pytanie, ktore ma znaczenie: **za co dana rzecz odpowiada
i co od niej zalezy**.

Zmierzone przed napisaniem tego pliku: `docs/REPO_MAP.md` opisuje
`ciekawostki.md` czterema slowami („facts worth a note"). Nie mowi, ze to
JEDYNY etap znajdujacy fakty, ze zalezy od niego takze temat artykulu, ani
ktora bramka czyta jego wynik. `docs/FUNCTION_MAP.md` ma te informacje, ale
rozsypana na dziewietnastu wierszach — obraz trzeba zlozyc samemu, a wtedy
mapa nie jest mapa.

## Pytanie, na ktore ta mapa odpowiada

Dla kazdego pola, ktorego brief zada od modelu: **czy cokolwiek je czyta**.

  * czyta BRAMKA        — pole jest nosne. Wyciecie zmienia zachowanie bota.
  * czyta jakis kod     — pole jest uzywane, ale nikt nie sprawdza jego tresci.
  * nie czyta NIKT      — placimy za tokeny wyjscia i za miejsce w brief, i nic
                          z tego nie wynika. To jest material do zdjecia.

Bez tego podzialu skracanie promptow jest zgadywaniem, a zgadywanie przy
promptach kosztuje jakosc, ktorej nie widac od razu.

## Skad bierze dane

Wszystko z drzewa skladni i z tekstu briefow; nic z listy pisanej recznie —
lista pisana recznie jest zawsze o jeden wpis krotsza.

  * wolajacy   — funkcja, w ktorej stoi `_prompt("plik.md", ...)`
  * rola       — pierwszy `llm.call("rola", ...)` w tej samej funkcji
  * pola       — nazwy z sekcji `## Output` SAMEGO BRIEFU, bo tam widzi je model
  * czytelnicy — kazde `x.get("pole")` i `x["pole"]` w modulach agenta

Uzycie:
    python narzedzia/mapa_briefow.py            # pisze docs/BRIEF_MAP.md
    python narzedzia/mapa_briefow.py --pokaz    # tylko na ekran
"""
from __future__ import annotations

import ast
import collections
import pathlib
import re
import sys

KORZEN = pathlib.Path(__file__).resolve().parent.parent
PROMPTY = KORZEN / "agent-v2" / "prompts"
MODULY = sorted((KORZEN / "agent-v2").glob("*.py"))

# FUNKCJE, KTORE SA BRAMKA, a nie zwyklym czytelnikiem pola. Bramka odrzuca,
# blokuje albo trwale znakuje. Funkcja, ktora pole tylko przepisuje dalej,
# niczego nie egzekwuje — wpisanie jej tutaj zamienilaby te mape w spis
# wystapien, czyli w to, czym `FUNCTION_MAP` juz jest.
BRAMKI = {
    "bramka_kandydata", "swiezosc_faktu", "swiezosc_karty", "bez_wstrzykniecia",
    "_podloga_z_pamieci", "_zapora_notki", "_zapora_komentarza", "ocen_restack",
    "deterministic_floors", "numbers_outside_corpus", "statystyki_bez_zrodla",
    "zastrzezenia", "zakazane_otwarcie", "niewiadome_na_koncu", "odcisk_formy",
    "powtorzona_forma", "uwagi_z_formy", "pozycja_w_tekscie",
    "szerokosc_podstawy", "frazy_z_instrukcji", "zapowiedziany_akapit_granic",
    "verdict", "zweryfikuj", "napraw_obalone", "ocen_forme",
}

# Nazwy, ktore w JSON-ie sa POJEMNIKIEM, nie polem faktu.
POJEMNIKI = {"facts", "sentences", "claims", "topics", "targets", "candidates",
             "assessments", "choices", "groups", "beliefs", "sources",
             "confirmed_claims", "uncertain_claims", "oceny", "members"}


def drzewa() -> dict[str, ast.Module]:
    out = {}
    for p in MODULY:
        try:
            out[p.name] = ast.parse(p.read_text(encoding="utf-8"))
        except SyntaxError:
            print("  ! %s nie parsuje sie — pomijam" % p.name, file=sys.stderr)
    return out


def _funkcje(drzewo: ast.Module):
    for w in ast.walk(drzewo):
        if isinstance(w, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield w


def pola_briefu(p: pathlib.Path) -> list[str]:
    """Pola z sekcji `## Output` — czyli to, co brief KAZE modelowi oddac."""
    t = p.read_text(encoding="utf-8")
    if "## Output" not in t:
        return []
    blok = t.split("## Output", 1)[1][:1600]
    return sorted({x for x in re.findall(r'"([a-z_]{2,30})"\s*:', blok)
                   if x not in POJEMNIKI})


def wolajacy(dr) -> dict[str, list[tuple[str, str, str]]]:
    """brief -> [(modul, funkcja, rola modelu)]"""
    out: dict[str, list] = {}
    for nazwa_modulu, drzewo in dr.items():
        for f in _funkcje(drzewo):
            briefy, role = [], []
            for n in ast.walk(f):
                if not isinstance(n, ast.Call):
                    continue
                nazwa = getattr(n.func, "id", None) or getattr(n.func, "attr", None)
                if nazwa == "_prompt" and n.args:
                    a = n.args[0]
                    if isinstance(a, ast.Constant) and str(a.value).endswith(".md"):
                        briefy.append(str(a.value))
                elif nazwa == "call" and n.args:
                    a = n.args[0]
                    if isinstance(a, ast.Constant) and isinstance(a.value, str):
                        role.append(a.value)
            for b in briefy:
                out.setdefault(b, []).append(
                    (nazwa_modulu.replace(".py", ""), f.name,
                     role[0] if role else "—"))
    return out


def czytelnicy_pol(dr) -> dict[str, set[str]]:
    """pole -> {modul.funkcja, ktore je czytaja}

    Liczymy `x.get("pole")` i `x["pole"]`. To jest przyblizenie w JEDNA strone:
    pole moze byc czytane przez zmienna, ktorej tu nie widac. Dlatego wynik
    „nikt nie czyta" jest PODEJRZENIEM do sprawdzenia, a nie wyrokiem — i tak
    jest opisany w gotowej mapie.
    """
    out: dict[str, set[str]] = collections.defaultdict(set)
    for nazwa_modulu, drzewo in dr.items():
        modul = nazwa_modulu.replace(".py", "")
        for f in _funkcje(drzewo):
            for n in ast.walk(f):
                pole = None
                if (isinstance(n, ast.Call)
                        and getattr(n.func, "attr", "") == "get"
                        and n.args and isinstance(n.args[0], ast.Constant)
                        and isinstance(n.args[0].value, str)):
                    pole = n.args[0].value
                elif (isinstance(n, ast.Subscript)
                      and isinstance(n.slice, ast.Constant)
                      and isinstance(n.slice.value, str)):
                    pole = n.slice.value
                if pole:
                    out[pole].add("%s.%s" % (modul, f.name))
    return out


def nazwy_posrednie(dr) -> dict[str, set[str]]:
    """Pole czytane PRZEZ POMOCNIKA, ktoremu nazwa idzie jako argument-napis.

    Bez tego skan klamie na najwiekszym briefie w repo. `skaut.md` zada pieciu
    pol; cztery z nich czyta `wazenie("least_written_about", 2)` — nazwa jest
    ARGUMENTEM, wiec szukanie po `.get("x")` i `x["x"]` nie widzi jej wcale
    i wszystkie cztery wychodzily jako martwe.

    Falszywy alarm w te strone jest tu grozniejszy od przeoczenia: na jego
    podstawie ktos wycialby z briefu pole, ktore pracuje. Bierzemy wiec KAZDY
    napis stojacy jako argument wywolania i traktujemy trafienie jako
    „czytane posrednio" — z nazwa funkcji, zeby dalo sie sprawdzic recznie.
    """
    out: dict[str, set[str]] = collections.defaultdict(set)
    for nazwa_modulu, drzewo in dr.items():
        modul = nazwa_modulu.replace(".py", "")
        # Krotki stoja tez w naglowku petli `for a, b in ((..., "pole"), ...)`,
        # czyli poza wywolaniem. Chodzimy po CALYM module.
        for n in ast.walk(drzewo):
            if isinstance(n, (ast.Tuple, ast.List)):
                for e in n.elts:
                    if isinstance(e, (ast.Tuple, ast.List)):
                        for x in e.elts:
                            if (isinstance(x, ast.Constant)
                                    and isinstance(x.value, str)
                                    and re.fullmatch(r"[a-z_]{2,30}", x.value)):
                                out[x.value].add("%s (para klucz-etykieta)" % modul)
        for f in _funkcje(drzewo):
            for n in ast.walk(f):
                if not isinstance(n, ast.Call):
                    continue
                kandydaci = list(n.args) + [k.value for k in n.keywords]
                for a in list(kandydaci):
                    # PARY (etykieta, klucz) W KROTCE. `run.py` drukuje karte
                    # petla po `(("sprzecznosci", "contradictions"), ...)`
                    # i siega `card.get(key)` — klucz jest zmienna, wiec ani
                    # `.get("x")`, ani argument-napis go nie widzi. Bez tego
                    # `contradictions` wychodzilo jako martwe, a jest drukowane
                    # wlascicielowi przy kazdym artykule.
                    if isinstance(a, (ast.Tuple, ast.List)):
                        kandydaci.extend(a.elts)
                for a in kandydaci:
                    if (isinstance(a, ast.Constant)
                            and isinstance(a.value, str)
                            and re.fullmatch(r"[a-z_]{2,30}", a.value)):
                        out[a.value].add("%s.%s" % (modul, f.name))
    return out


def rusztowanie() -> dict[tuple[str, str], str]:
    """Pola, ktorych kod SWIADOMIE nie czyta — z zapisanym powodem.

    `tests/test_martwe_sygnaly.py` trzyma ten rejestr od dawna i kazdy wpis
    wymaga uzasadnienia. Bez zajrzenia tutaj ta mapa zglaszalaby jako wade
    OSIEMNASCIE decyzji, ktore ktos podjal swiadomie i opisal — czyli robilaby
    dokladnie to, co ten projekt tropi u siebie od tygodni: alarm nad
    poprawnym stanem, po ktorym przestaje sie czytac alarmy.

    Zmierzone: z dwudziestu pol bez czytelnika osiemnascie ma tu wpis. Cala
    wartosc tej kolumny jest w pozostalych dwoch.
    """
    plik = KORZEN / "agent-v2" / "tests" / "test_martwe_sygnaly.py"
    try:
        drzewo = ast.parse(plik.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return {}
    out: dict[tuple[str, str], str] = {}
    for w in ast.walk(drzewo):
        if not (isinstance(w, ast.Assign) and any(
                isinstance(c, ast.Name) and c.id == "RUSZTOWANIE"
                for c in w.targets)):
            continue
        if not isinstance(w.value, ast.Dict):
            continue
        for k, v in zip(w.value.keys, w.value.values):
            if not (isinstance(k, ast.Constant) and isinstance(v, ast.Dict)):
                continue
            for kk, vv in zip(v.keys, v.values):
                try:
                    out[(k.value, kk.value)] = str(ast.literal_eval(vv))
                except Exception:                                # noqa: BLE001
                    out[(k.value, kk.value)] = ""
    return out


def buduj() -> str:
    dr = drzewa()
    wolania = wolajacy(dr)
    czytelnicy = czytelnicy_pol(dr)
    posrednie = nazwy_posrednie(dr)
    swiadome = rusztowanie()
    pliki = sorted(PROMPTY.glob("*.md"))

    def klasa(pole: str) -> tuple[str, list[str]]:
        kto = sorted(czytelnicy.get(pole, ()))
        bramki = [k for k in kto if k.split(".")[-1] in BRAMKI]
        if bramki:
            return "BRAMKA", bramki
        if kto:
            return "czytane", kto
        posr = sorted(posrednie.get(pole, ()))
        if posr:
            return "posrednio", posr
        return "NIKT", []

    def powod(brief: str, pole: str) -> str:
        """Zapisany powod, dla ktorego tego pola nikt nie czyta."""
        return swiadome.get((brief, pole), "")

    def ocen(brief: str, pole: str):
        k, kto = klasa(pole)
        if k == "NIKT" and powod(brief, pole):
            return "swiadome", [powod(brief, pole)[:80]]
        return k, kto

    w = ["# Brief map — what each brief is responsible for",
         "",
         "**Generated — do not edit by hand.** `python narzedzia/mapa_briefow.py`",
         "",
         "The other maps answer *where things are*. This one answers **what each",
         "brief is responsible for, and what depends on it** — specifically, for",
         "every field a brief tells the model to return: does anything read it?",
         "",
         "| verdict | meaning |",
         "|---|---|",
         "| **gate** | a gate reads it. Load-bearing: removing it changes what the bot does |",
         "| used | some code reads it, but nothing checks its content |",
         "| used (by name) | read through a helper that takes the field name as"
         " a string argument — verify by hand before cutting |",
         "| **nobody** | no reader found. We pay output tokens and brief space for it |",
         "",
         "The last verdict is a **suspicion, not a ruling**: a field can be read",
         "through a variable this scan cannot see. Check before cutting.",
         "",
         "## Briefs",
         "",
         "| brief | lines | called by | model role | fields | gate | used | nobody |",
         "|---|---|---|---|---|---|---|---|"]

    szczegoly = []
    for p in pliki:
        linie = len(p.read_text(encoding="utf-8").splitlines())
        pola = pola_briefu(p)
        wpisy = wolania.get(p.name, [])
        if not wpisy:
            w.append("| `%s` | %d | **nothing** | — | %d | — | — | — |"
                     % (p.name, linie, len(pola)))
            continue
        modul, fun, rola = wpisy[0]
        licz = collections.Counter(ocen(p.name, x)[0] for x in pola)
        w.append("| `%s` | %d | `%s.%s`%s | `%s` | %d | %d | %d | %s |" % (
            p.name, linie, modul, fun,
            (" *(+%d)*" % (len(wpisy) - 1)) if len(wpisy) > 1 else "",
            rola, len(pola), licz["BRAMKA"],
            licz["czytane"] + licz["posrednio"] + licz["swiadome"],
            ("**%d**" % licz["NIKT"]) if licz["NIKT"] else "0"))

        if pola:
            szczegoly.append("### `%s`\n" % p.name)
            szczegoly.append("| field | verdict | read by |")
            szczegoly.append("|---|---|---|")
            for x in pola:
                k, kto = ocen(p.name, x)
                szczegoly.append("| `%s` | %s | %s |" % (
                    x,
                    {"BRAMKA": "**gate**", "czytane": "used",
                     "posrednio": "used (by name)",
                     "swiadome": "unread, on purpose",
                     "NIKT": "**nobody, unexplained**"}[k],
                    ", ".join("`%s`" % y for y in kto[:4]) or "—"))
            szczegoly.append("")

    w += ["", "## Field by field", ""] + szczegoly

    sieroty = [p.name for p in pliki if p.name not in wolania]
    w += ["## Briefs nothing calls", ""]
    w += ([("- `%s`" % s) for s in sieroty] if sieroty
          else ["Every brief has a caller."])
    w += ["",
          "A brief with no caller is not automatically dead — it can be reference",
          "material injected into another prompt, which is what `po_ludzku.md` is.",
          "But this is also how a brief that *should* be called stops being called",
          "and nobody notices: that file spent weeks describing itself as injected",
          "while its name appeared in no line of code.",
          ""]
    return "\n".join(w)


if __name__ == "__main__":
    tekst = buduj()
    if "--pokaz" in sys.argv:
        print(tekst)
    else:
        cel = KORZEN / "docs" / "BRIEF_MAP.md"
        cel.write_text(tekst + "\n", encoding="utf-8")
        print("zapisano %s" % cel)
