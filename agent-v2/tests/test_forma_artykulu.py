"""Test formy artykulu: zakonczenie i szerokosc drugiego aktu maja sie ZMIENIAC.

Kontrdowod: kazdy test tutaj musi TAKZE wykryc stan sprzed naprawy, czyli
prompt, ktory zamawial jedno stale zakonczenie i "two or three" paraleli.
Dwa artykuly napisane na tamtym prompcie (0017, 0019) wyszly z identycznym
szkieletem — to jest dokladnie to, czego test pilnuje.
"""
import collections
import hashlib
import pathlib
import sys

sys.path.insert(0, "agent-v2")
import config   # noqa: E402
import stages   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


def odcisk(p):
    p = pathlib.Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else "brak"


PILNOWANE = [config.DB_PATH, config.DATA_DIR / "zuzyte_fakty.json",
             config.DATA_DIR / "promocja.json", config.DATA_DIR / "dziennik.jsonl"]
PRZED = {str(p): odcisk(p) for p in PILNOWANE}

PISARZ = (config.PROMPTS_DIR / "pisarz.md").read_text(encoding="utf-8")

print("=== 1. KAZDY RUCH KONCOWY MA OPIS I ODWROTNIE ===")

sprawdz("kazdy ruch z miksu ma opis",
        set(config.RUCH_KONCOWY_MIX) <= set(config.RUCHY_KONCOWE),
        set(config.RUCH_KONCOWY_MIX) - set(config.RUCHY_KONCOWE))
sprawdz("zaden opis nie jest osierocony",
        set(config.RUCHY_KONCOWE) <= set(config.RUCH_KONCOWY_MIX),
        set(config.RUCHY_KONCOWE) - set(config.RUCH_KONCOWY_MIX))
sprawdz("ruchow jest wiecej niz jeden (inaczej to nadal formula)",
        len(set(config.RUCH_KONCOWY_MIX)) >= 4, len(set(config.RUCH_KONCOWY_MIX)))
sprawdz("zaden opis nie jest pusty",
        all(len(v) > 40 for v in config.RUCHY_KONCOWE.values()))

print()
print("=== 2. LOSOWANIE REALNIE ROZNICUJE (kontrdowod: stale zakonczenie) ===")

trafienia = collections.Counter(config.losowy_ruch_koncowy()[0] for _ in range(400))
sprawdz("wypadaja wszystkie ruchy, nie jeden",
        len(trafienia) == len(set(config.RUCH_KONCOWY_MIX)), dict(trafienia))
sprawdz("zaden ruch nie zjada wiekszosci przebiegow",
        max(trafienia.values()) < 260, dict(trafienia))
sprawdz("DO_SPRAWDZENIA (stare, jedyne zakonczenie) to teraz mniejszosc",
        trafienia["DO_SPRAWDZENIA"] < 160, trafienia["DO_SPRAWDZENIA"])

paralele = collections.Counter(
    config.losowa_liczba_paraleli("RICH")[0] for _ in range(400))
sprawdz("liczba paraleli sie zmienia", len(paralele) >= 2, dict(paralele))
sprawdz("jedna rozwinieta paralela wypada realnie czesto",
        paralele[1] >= 60, dict(paralele))
sprawdz("trzy paralele (stare zachowanie) nie sa domyslem",
        paralele[3] < 240, dict(paralele))

krotkie = collections.Counter(
    config.losowa_liczba_paraleli("SINGLE")[0] for _ in range(200))
sprawdz("krotki artykul nigdy nie bierze trzech paraleli",
        3 not in krotkie, dict(krotkie))

print()
print("=== 3. PROMPT NIE ZAMAWIA JUZ JEDNEGO SZKIELETU ===")

sprawdz("prompt ma miejsce na losowany ruch koncowy",
        "{ruch_koncowy}" in PISARZ)
sprawdz("prompt ma miejsce na liczbe paraleli", "{ile_paraleli}" in PISARZ)
sprawdz("znikl stary nakaz 'check for themselves' jako JEDYNE zakonczenie",
        "something the reader can check for themselves, or by naming exactly"
        not in PISARZ)
sprawdz("znikl stary 'Two or three such turns'",
        "Two or three such turns" not in PISARZ)
sprawdz("prompt zakazuje drogowskazu przed paralelami",
        "Once you see this shape" in PISARZ and "signpost" in PISARZ)
sprawdz("prompt zakazuje zapowiadania akapitu o granicach",
        "Do not announce that paragraph" in PISARZ)
sprawdz("prompt zakazuje nazywania materialu 'the excerpts'",
        "The excerpts" in PISARZ and "the published guidance" in PISARZ)
sprawdz("nadal stoi zakaz konczenia podsumowaniem",
        "closing with a summary" in PISARZ)
# ZGODNOSC, NIE BRZMIENIE. Rano zapisalem tu asercje na konkretne zdanie
# i zabetonowala ona bledne rozstrzygniecie: przeczytalem dwie sprzeczne reguly
# i przestawilem te, ktora stala po stronie WIEKSZOSCI. Akapit granic jest
# zalozony w PIECIU miejscach — regula „Say the limits once", cala regula
# o pierwszym zdaniu TEGO akapitu z przykladami, zakaz „do not expand the
# limits paragraph", pole schematu `limits_paragraph_present` czytane
# w run.py, oraz bramka `gates.zapowiedziany_akapit_granic`, ktora bada
# pierwsze zdanie tego akapitu i bez niego nie ma sensu.
#
# Wiec test pyta teraz o to, co naprawde ma byc prawda: zadne zdanie promptu
# nie zakazuje akapitu, ktory piec innych miejsc zaklada.
sprawdz("prompt zamawia JEDEN akapit granic",
        "One paragraph, and only one." in PISARZ
        and "Say the limits once" in PISARZ)
sprawdz("i rzadzi jego POLOZENIEM, nie istnieniem",
        "Put that paragraph where the gap opens" in PISARZ)
sprawdz("zadne zdanie nie zakazuje zbierania granic",
        "Never collect them." not in PISARZ
        and "Put each unknown where it arises, alone." not in PISARZ)
sprawdz("zakaz rozdymania nadal zaklada, ze akapit istnieje",
        "expand the limits paragraph" in PISARZ)
sprawdz("schemat nadal pyta o obecnosc akapitu",
        "limits_paragraph_present" in PISARZ)

print()
print("=== 4. PROMPT SIE RENDERUJE (kontrdowod: KeyError na nowym polu) ===")

ruch_nazwa, ruch_opis = config.losowy_ruch_koncowy()
ile, opis_paraleli = config.losowa_liczba_paraleli("RICH")
try:
    wynik = stages._prompt(
        "pisarz.md",
        language="English", target_words=1075, min_words=950, max_words=1200, kotwica_dlugosci="x",
        style_examples="X", style_positive="Y", style_negative="Z",
        ruch_koncowy_nazwa=ruch_nazwa, ruch_koncowy=ruch_opis,
        ile_paraleli=opis_paraleli, card_json="{}",
        poprzednie_uwagi="(brak)",
    )
    sprawdz("pisarz.md renderuje sie bez wyjatku", True)
    sprawdz("wylosowany ruch trafia do tekstu promptu", ruch_opis[:50] in wynik)
    sprawdz("opis liczby paraleli trafia do tekstu promptu",
            opis_paraleli[:40] in wynik)
    # Szablon wyjscia JSON legalnie zawiera nawiasy po renderowaniu ({{ -> {),
    # wiec nie szukamy nawiasu, tylko NAZW pol, ktore mialy zostac podstawione.
    puste = [f for f in ("ruch_koncowy", "ruch_koncowy_nazwa", "ile_paraleli",
                         "language", "target_words", "max_words", "card_json",
                         "style_examples", "style_positive", "style_negative")
             if "{%s}" % f in wynik]
    sprawdz("zadne pole nie zostalo niepodstawione", not puste, puste)
except Exception as e:
    sprawdz("pisarz.md renderuje sie bez wyjatku", False, repr(e))

print()
print("=== 5. BRAK POLA NADAL JEST BLEDEM, NIE CICHYM PRZEJSCIEM ===")

try:
    stages._prompt(
        "pisarz.md",
        language="English", target_words=1075, min_words=950, max_words=1200, kotwica_dlugosci="x",
        style_examples="X", style_positive="Y", style_negative="Z",
        card_json="{}",
    )
    sprawdz("pominiecie ruchu koncowego wywala prompt", False,
            "przeszlo bez ruchu koncowego — placeholder nie dziala")
except KeyError:
    sprawdz("pominiecie ruchu koncowego wywala prompt", True)

print()
print("=== 6. NIC NIE ZOSTALO DOTKNIETE ===")
for p in PILNOWANE:
    sprawdz("bez zmian: %s" % pathlib.Path(p).name,
            PRZED[str(p)] == odcisk(p))

print()
print("zdane %d, oblane %d" % (zdane, oblane))
sys.exit(1 if oblane else 0)
