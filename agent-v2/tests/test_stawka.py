"""Druga droga do artykulu: nierozstrzygniety wynik zamiast zlamanego przekonania.

DLACZEGO TO POWSTALO. Cztery pytania odsiewu opisuja rzecz JUZ ROZSTRZYGNIETA:
przekonanie, ktore jest bledne, decyzje, ktora zapadla, liczbe, ktora zmierzono.
To sa pytania zamkniete — a luka informacyjna z definicji sie nasyca.
Loewenstein pisze to wprost: konsumpcja informacji jest nagradzajaca, ale po
zdobyciu wystarczajacej ilosci ciekawosc SPADA.

Pismo zbudowane wylacznie na pytaniach zamknietych produkuje wiec czytelnikow
ZASPOKOJONYCH I ODCHODZACYCH. Wlasciciel nazwal to krocej: „nie wiem, czy lody
sa zimne — tak — i mozna jebnac historie lodow, ale to bedzie nudne".

Do tego dwa znaleziska z literatury, ktore uderzaja w zalozenie, ze samo
„mylisz sie" niesie tekst:
  - informacja ZGODNA z przekonaniami jest udostepniana czesciej, mimo ze jest
    najmniej zaskakujaca (223 tweety, ~4400 podajacych dalej, n=226 i n=301);
    manipulowana nowosc nie przewidywala udostepnien w ogole,
  - osobista i spoleczna ISTOTNOSC zwieksza chec podania dalej przyczynowo
    (szesc badan plus preрejestrowany eksperyment).

Dlatego zlamane przekonanie ZOSTAJE — wzielo sie z prawdziwej porazki i dziala —
ale przestaje byc jedyna droga.

WARUNEK, KTORY ODDZIELA TO OD WROZENIA, jest jeden i twardy: karta musi niesc
SPISANA REGULE rozstrzygajaca wynik. Bez niej nie przechodzi, chocby pytanie
brzmialo najdramatyczniej. Tego pilnuje sekcja 3 i to jest najwazniejsza czesc
tego pliku.
"""
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


# --- podstawiamy model: sprawdzamy KOD skladajacy werdykt, nie dostawce ------
# PODSTAWIAMY WYLACZNIE `call`. Do 2 wrzesnia `parse_json` bylo tu wlasnym
# `json.loads` — czyli omijalo prawdziwa funkcje tlumaczaca odpowiedz modelu
# na ksztalt oczekiwany przez kod (trzydziesci linii obslugi prozy wokol
# JSON-a, ktorych awaria kosztowala „dwadziescia wyszukiwan i 0,13 USD, po
# czym oddalo zero"). Atrapa oddaje wiec tekst w takim ksztalcie, w jakim
# oddaje go model z wlaczonym wyszukiwaniem, a rozbiera go PRAWDZIWY
# `llm.parse_json`.
import llm as _prawdziwy_llm   # noqa: E402


class FalszywyLLM:
    odpowiedz: dict = {}
    parse_json = staticmethod(_prawdziwy_llm.parse_json)

    @staticmethod
    def call(*a, **k):
        import json
        return ("Let me weigh the card — I will return {one object} only.\n\n"
                + json.dumps(FalszywyLLM.odpowiedz)
                + "\n\nThat is my reading of what the record supports.")


def odsiew(**pola):
    """Odpala prawdziwy `warto_pisac` na podstawionej obserwacji modelu."""
    baza = {
        "contradicted_belief": {"present": False, "the_belief": "", "evidence": ""},
        "named_decider": {"present": False, "evidence": ""},
        "felt_number": {"present": False, "evidence": ""},
        "second_domain": {"present": False, "evidence": ""},
        "unsettled_outcome": {"present": False, "the_question": "",
                              "the_situation": "", "governed_by": ""},
        "what_would_rescue_it": "", "one_line_verdict": "",
    }
    baza.update(pola)
    FalszywyLLM.odpowiedz = baza
    oryg = stages.llm
    stages.llm = FalszywyLLM
    try:
        return stages.warto_pisac(None, 0, {"working_thesis": "x"})
    finally:
        stages.llm = oryg


# --- material: nasze wlasne tematy, nie wymyslone ----------------------------
KOD_ZYWICY = dict(
    contradicted_belief={"present": True,
                         "the_belief": "The triangle with a number means this "
                                       "item can be recycled.",
                         "evidence": "ASTM says it identifies resin only"},
    named_decider={"present": True, "evidence": "Society of the Plastics Industry, 1988"},
    felt_number={"present": True, "evidence": "9% of plastics ever recycled"},
    second_domain={"present": True, "evidence": "milk carton date"},
    # Kluczowe: kod zywicy JEST rozstrzygniety. To, czego nie wiemy — co sie
    # dzieje z konkretnym pojemnikiem — to luka w NASZEJ wiedzy, nie stawka.
    unsettled_outcome={"present": False, "the_question": "", "the_situation": "",
                       "governed_by": "nothing in the card leaves an outcome open; "
                                      "the code's meaning is settled"},
)

KONKLAWE = dict(
    # Bez zlamanego przekonania — celowo, bo o to chodzi w tej drodze.
    contradicted_belief={"present": False, "the_belief": "", "evidence": ""},
    named_decider={"present": True,
                   "evidence": "the apostolic constitution governing the vacancy"},
    felt_number={"present": False, "evidence": ""},
    second_domain={"present": False, "evidence": ""},
    unsettled_outcome={
        "present": True,
        "the_question": "What happens if they cannot agree on a successor for months?",
        "the_situation": "the chimney everyone watches, and no smoke of either colour",
        "governed_by": "the constitution setting out the ballot procedure and what "
                       "changes after a fixed number of inconclusive rounds"},
)

print("=== 1. STARA DROGA DZIALA BEZ ZMIAN ===")
w = odsiew(**KOD_ZYWICY)
print("    %s — %s" % (w["werdykt"], w["powod"][:74]))
sprawdz("kod żywicy nadal PISZ", w["werdykt"] == "PISZ", w["werdykt"])
sprawdz("przez drogę przekonania, nie stawki", "przekonanie" in w["powod"], w["powod"])
sprawdz("i stawki nie ma", w["stawka"] is False, w["stawka"])

print()
print("=== 2. NOWA DROGA: STAWKA BEZ ZLAMANEGO PRZEKONANIA ===")
w = odsiew(**KONKLAWE)
print("    %s — %s" % (w["werdykt"], w["powod"][:74]))
sprawdz("konklawe przechodzi", w["werdykt"] == "PISZ", w["werdykt"])
sprawdz("mimo braku złamanego przekonania", w["przekonanie"] is False)
sprawdz("i mimo jednego filaru", w["ile_filarow"] == 1, w["ile_filarow"])
sprawdz("powód wskazuje drogę stawki", "stawki" in w["powod"], w["powod"])

# KONTRDOWOD: przed zmiana ten sam temat byl ODLOZ. Bez tego sprawdzenia test
# nie odroznia wersji — moglby przechodzic z zupelnie innego powodu.
sprawdz("STARA logika odłożyłaby go (test rozróżnia)",
        not (w["przekonanie"] and w["ile_filarow"] >= 2))

print()
print("=== 3. WARUNEK, KTORY ODDZIELA TO OD WROZENIA ===")
# Najwazniejsza sekcja. Dramatyczne pytanie BEZ spisanej reguly nie przechodzi.
wrozenie = dict(KONKLAWE)
wrozenie["unsettled_outcome"] = {
    "present": True,
    "the_question": "What would happen if China attacked with nuclear weapons?",
    "the_situation": "an attack nobody has seen",
    "governed_by": ""}
w = odsiew(**wrozenie)
print("    %s — %s" % (w["werdykt"], w["powod"][:78]))
sprawdz("wynik bez spisanej reguły NIE przechodzi", w["werdykt"] != "PISZ",
        w["werdykt"])
sprawdz("kod nazywa to wróżeniem",
        any("wrozenie" in u for u in w.get("uwagi_kodu", [])), w.get("uwagi_kodu"))
sprawdz("stawka nie liczy się bez reguły", w["stawka"] is False)

# I to samo z regula, ale bez nazwanego decydenta: regula, ktorej nikt nie
# ustanowil, to zjawisko, a nie procedura — nie ma czego wystawiac na probe.
bez_decydenta = dict(KONKLAWE)
bez_decydenta["named_decider"] = {"present": False, "evidence": "nobody named"}
w = odsiew(**bez_decydenta)
sprawdz("stawka bez nazwanego decydenta -> DOLOZ, nie PISZ",
        w["werdykt"] == "DOLOZ", w["werdykt"])
sprawdz("i powód mówi, że szukamy, kto rozstrzyga",
        "kto to rozstrzyga" in w["powod"], w["powod"])

print()
print("=== 4. LUKA W NASZEJ WIEDZY TO NIE JEST STAWKA ===")
# Rozroznienie, na ktorym stoi cala ta droga. „Nikt nie sledzi, gdzie trafia
# pojemnik" znaczy: odpowiedz istnieje, nikt jej nie zapisal. To nie stawka.
niewiedza = dict(KOD_ZYWICY)
niewiedza["contradicted_belief"] = {"present": False, "the_belief": "", "evidence": ""}
niewiedza["unsettled_outcome"] = {
    "present": True,
    "the_question": "Where does any particular container actually end up?",
    "the_situation": "a bin nobody follows",
    "governed_by": "nothing decides it; it simply is not recorded anywhere"}
w = odsiew(**niewiedza)
print("    %s — %s" % (w["werdykt"], w["powod"][:74]))
# Model odpowiedzial UCZCIWIE: „nic tego nie rozstrzyga, po prostu nikt tego
# nie zapisal". Sam licznik slow tego nie zlapie, bo takie zdanie jest dluzsze
# niz nazwa prawdziwej procedury — a jednak opisuje BRAK reguly. Kod nie moze
# przepuszczac odpowiedzi, ktora zaprzecza sama sobie w pierwszych slowach.
sprawdz("uczciwe „nic tego nie rozstrzyga” NIE przechodzi",
        w["werdykt"] != "PISZ", w["werdykt"])
sprawdz("kod nazywa to luką w wiedzy",
        any("luka w wiedzy" in u for u in w.get("uwagi_kodu", [])), w.get("uwagi_kodu"))

# KONTRDOWOD dla samej siatki na zaprzeczenia: PRAWDZIWA regula, ktora zawiera
# slowo „nothing" w srodku, musi przejsc. Inaczej siatka lapalaby po slowie,
# a nie po sensie.
z_nothing = dict(KONKLAWE)
z_nothing["unsettled_outcome"] = dict(
    KONKLAWE["unsettled_outcome"],
    governed_by="the rules say nothing changes until the thirty-fourth ballot")
sprawdz("regula ze slowem „nothing” w srodku przechodzi",
        odsiew(**z_nothing)["werdykt"] == "PISZ",
        odsiew(**z_nothing)["werdykt"])
for zle in ("nothing decides it; it is simply not recorded",
            "no written procedure covers this at all",
            "there is no rule in the card about it",
            "nobody has set this down anywhere"):
    zz = dict(KONKLAWE)
    zz["unsettled_outcome"] = dict(KONKLAWE["unsettled_outcome"], governed_by=zle)
    sprawdz("odrzuca: %s" % zle[:38], odsiew(**zz)["werdykt"] != "PISZ")

# Rozroznienie nalezy przede wszystkim do modelu, bo wymaga czytania —
# prompt musi wiec mowic je wprost.
p = (config.PROMPTS_DIR / "warto_pisac.md").read_text(encoding="utf-8")
plaski = " ".join(p.split())
sprawdz("prompt wprost odróżnia niewiedzę od stawki",
        "is NOT an unsettled outcome" in plaski, "brak zdania w promptcie")
sprawdz("prompt daje przykład tej pomyłki",
        "leaves your hand" in plaski or "went unrecorded" in plaski)

print()
print("=== 5. GDY NIE MA ANI JEDNEGO, ANI DRUGIEGO ===")
w = odsiew()
sprawdz("pusta karta -> ODLOZ", w["werdykt"] == "ODLOZ", w["werdykt"])
sprawdz("powód wymienia OBA braki",
        "przekonania" in w["powod"] and "wyniku" in w["powod"], w["powod"])

print()
print("=== 6. OBIE DROGI NARAZ ===")
obie = dict(KOD_ZYWICY)
obie["unsettled_outcome"] = KONKLAWE["unsettled_outcome"]
w = odsiew(**obie)
sprawdz("PISZ", w["werdykt"] == "PISZ")
sprawdz("powód mówi o obu drogach", "obie drogi" in w["powod"], w["powod"])

print()
print("=== 7. SKAUT PROPONUJE OBA RODZAJE ===")
s = (config.PROMPTS_DIR / "skaut.md").read_text(encoding="utf-8")
plaski_s = " ".join(s.split())
sprawdz("prompt ma drugi rodzaj tematu",
        "a system about to be tested" in plaski_s)
sprawdz("nazywa go w kontrakcie wyjścia", '"SYSTEM_UNDER_TEST"' in plaski_s)
sprawdz("wymaga trzech pól", all(x in plaski_s for x in
                                 ("the_moment", "open_outcome", "governing_record")))
sprawdz("stawia warunek spisanej procedury",
        "Condition three is the whole guard" in plaski_s)
sprawdz("zabrania wróżenia wprost",
        "we do not publish fortune-telling" in plaski_s)
sprawdz("i nadal zabrania nazywania instytucji",
        "narrows the search to what you happen to recall" in plaski_s)
sprawdz("nadal wymaga mieszanki, nie samych systemów",
        "do not make every topic the same kind" in plaski_s)
# Skaut oddal 0 tematow artykulowych z 10, wiec prompt musi teraz ZADAC
# systemow, a nie tylko ich dopuszczac. Przyczyna zera nie byla w modelu:
# caly prompt kazal mu szukac zwyklych przedmiotow, a systemy z historia
# byly doklejone na koncu — szukal w zlym miejscu.
sprawdz("prompt ZADA polowy systemow, nie tylko ich dopuszcza",
        "At least half your list must be" in plaski_s)
sprawdz("i trzech z dwoma precedensami",
        "must carry two or more precedents each" in plaski_s)
sprawdz("ale zostawia miejsce na zlamane przekonania",
        "Keep at least two" in plaski_s)
sprawdz("pokazuje, GDZIE takich tematow szukac",
        "scar tissue" in plaski_s and "Mine it" in plaski_s)
# ZASADA, NIE BRZMIENIE. Ten warunek byl przypiety do jednego zdania
# („prescriptive limits on duty hours") i pekl, gdy przyklad lotniczy zastapiono
# przykladem z naszej dziedziny. Regula stala nietknieta, test nie. Sprawdzamy
# wiec, czy wzor JEST WYPELNIONY — trzy pola z trescia — a nie co w nim stoi.
_wzor = s.split("when:", 1)[-1][:900] if "when:" in s else ""
sprawdz("daje wypelniony przyklad precedensu",
        "what_happened:" in _wzor and "what_changed:" in _wzor
        and len(_wzor.split("what_changed:", 1)[-1].strip()) > 40)
sprawdz("nazywa oba tryby porazki",
        "**Too small.**" in plaski_s and "**Too vague.**" in plaski_s)

print()
print("=== 8. KOD SKAUTA STAWIA OBA RODZAJE NA CZELE KOLEJKI ===")
TEMATY = [
    {"title": "bez niczego", "kind": "BROKEN_BELIEF", "broken_belief": "krotkie"},
    {"title": "system pod proba", "kind": "SYSTEM_UNDER_TEST",
     "the_moment": "a market falling hard in one session",
     "open_outcome": "who stops the trading and for how long",
     "governing_record": "the exchange halt rules"},
    {"title": "zlamane przekonanie", "kind": "BROKEN_BELIEF",
     "broken_belief": "Everyone assumes the yellow light lasts the same everywhere"},
]
# Odtwarzamy dokladnie petle z `topics_from_scout` — bez wolania modelu.
for t in TEMATY:
    wiara = str(t.get("broken_belief") or "").strip()
    t["ma_przekonanie"] = len(wiara.split()) >= 5
    moment = str(t.get("the_moment") or "").strip()
    wynik = str(t.get("open_outcome") or "").strip()
    zapis = str(t.get("governing_record") or "").strip()
    t["ma_stawke"] = (len(moment.split()) >= 4 and len(wynik.split()) >= 4
                      and len(zapis.split()) >= 3)
    t["nosny"] = bool(t["ma_przekonanie"] or t["ma_stawke"])
TEMATY.sort(key=lambda t: not t["nosny"])
print("    kolejność: %s" % [t["title"] for t in TEMATY])
sprawdz("system pod próbą liczy się jako nośny",
        any(t["nosny"] and t["kind"] == "SYSTEM_UNDER_TEST" for t in TEMATY))
sprawdz("temat bez niczego ląduje na końcu",
        TEMATY[-1]["title"] == "bez niczego", TEMATY[-1]["title"])
# KONTRDOWOD: stara logika sortowala po SAMYM przekonaniu, wiec system pod
# proba spadalby na koniec razem z pustym tematem i nie powstalby nigdy.
po_staremu = sorted(TEMATY, key=lambda t: not t["ma_przekonanie"])
sprawdz("stara logika zepchnęłaby system na koniec (test rozróżnia)",
        po_staremu[-1]["kind"] == "SYSTEM_UNDER_TEST"
        or po_staremu.index(next(t for t in TEMATY if t["kind"] == "SYSTEM_UNDER_TEST")) > 0,
        [t["title"] for t in po_staremu])

print()
print("=== 9. ZRODLO KODU ZGADZA SIE Z TESTEM ===")
zrodlo = open("agent-v2/stages.py", encoding="utf-8").read()
sprawdz("stages liczy nośność z obu rzeczy", '"nosny"' in zrodlo)
sprawdz("stages ma drogę stawki", "droga_stawki" in zrodlo)

# URUCHOMIONE, NIE WYGREPOWANE. Do 2 wrzesnia stała tu cała linia źródła —
# `'droga_stawki = stawka and filary["named_decider"]' in zrodlo`. Taka
# asercja przechodzi także wtedy, gdy warunek wyląduje w gałęzi, do której
# `warto_pisac` nie dochodzi, a oblewa przy każdej zmianie odstępu.
#
# Pytamy więc prawdziwy `warto_pisac` o werdykt. Podmieniamy WYŁĄCZNIE
# `llm.call` i oddajemy `json.dumps({...})`, żeby prawdziwy `llm.parse_json`
# został w torze. Zero sieci, zero płatnych wywołań.
import contextlib   # noqa: E402
import io           # noqa: E402
import json         # noqa: E402


def werdykt_stawki(nazwany_decydent):
    """Karta z nierozstrzygniętym wynikiem i spisaną regułą; decydent zmienny."""
    odpowiedz = {
        "contradicted_belief": {"present": False},
        "named_decider": {"present": nazwany_decydent,
                          "who": "The Assembly's rapporteur"},
        "felt_number": {"present": False},
        "second_domain": {"present": False},
        "unsettled_outcome": {
            "present": True,
            "the_question": "Whether the disclosure duty covers screening "
                            "reports at all",
            "governed_by": "FCRA adverse action notice rule"},
    }
    oryg = stages.llm.call
    stages.llm.call = lambda *a, **k: json.dumps(odpowiedz)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return stages.warto_pisac(None, 0, {"tytul": "karta testowa"})
    finally:
        stages.llm.call = oryg


z_decydentem = werdykt_stawki(True)
bez_decydenta = werdykt_stawki(False)
sprawdz("stawka Z nazwanym decydentem otwiera drogę do pisania",
        z_decydentem["werdykt"] == "PISZ", z_decydentem["werdykt"])
sprawdz("i powód nazywa to drogą stawki",
        "droga stawki" in z_decydentem["powod"], z_decydentem["powod"])
sprawdz("i wymaga nazwanego decydenta — bez niego drogi stawki NIE MA",
        bez_decydenta["werdykt"] == "DOLOZ", bez_decydenta["werdykt"])
# KONTRDOWOD: wynik sam w sobie został rozpoznany w OBU przypadkach, więc
# różnicę robi wyłącznie decydent, a nie odrzucenie całej stawki.
sprawdz("KONTRDOWOD: sama stawka jest widziana w obu przypadkach",
        z_decydentem["stawka"] is True and bez_decydenta["stawka"] is True,
        (z_decydentem["stawka"], bez_decydenta["stawka"]))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
