# -*- coding: utf-8 -*-
"""Wybor komentarzy do odpowiedzi nie moze stac na polach, ktorych nikt nie pisze.

`wybierz_do_odpowiedzi` sortowalo kandydatow kluczem
`(reakcje or 0) * 2 + (odpowiedzi or 0) * 3`. `run.py` sklada te liste z trzech
zrodel i zadne nie wypelnia obu pol:

    browser.nieodpowiedziane              -> ani `reakcje`, ani `odpowiedzi`
    browser.odpowiedzi_na_nasze_komentarze -> ani `reakcje`, ani `odpowiedzi`
    browser.komentarze_pod_artykulami     -> `reakcje` tak, `odpowiedzi` nie

Czyli `odpowiedzi` bylo zawsze zerem, a `reakcje` zerem dla dwoch zrodel z
trzech. Sortowanie po samych zerach jest stabilne, wiec kolejnosc zostawala ta
z wejscia — a komunikat mowil „najpierw najzywsze watki".

Wada odpala sie powyzej `WYBIERAJ_POWYZEJ` komentarzy naraz, wiec dzis jeszcze
nie boli. Ten test pilnuje, zeby nie zaczela.
"""
import contextlib
import hashlib
import io
import json
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


PILNOWANE = [config.DB_PATH, config.DATA_DIR / "dziennik.jsonl"]
PRZED = {str(p): odcisk(p) for p in PILNOWANE}

# KSZTALTY WPISOW SKOPIOWANE Z `browser.py` CO DO POLA — o to w tym tescie
# chodzi. Daty sa stale, zeby test nie zalezal od dnia uruchomienia.
POD_ARTYKULAMI = [
    {"pod_czym": "Nasz artykul", "pod_id": 1, "gdzie": "artykul",
     "url": "https://x/p/a", "autor": "czytelnik%02d" % i, "jezyk": "en",
     "tekst": "komentarz pod artykulem %d" % i, "id": 100 + i,
     "data": "2026-08-%02dT10:00:00Z" % (i + 1), "reakcje": i}
    for i in range(1, 21)
]
POD_NOTKAMI = [
    {"pod_czym": "nasza notka", "pod_id": 2, "autor": "rozmowca%d" % i,
     "jezyk": "en", "tekst": "odpowiedz pod nasza notka %d" % i,
     "id": 200 + i, "data": "2026-08-%02dT11:00:00Z" % (i + 1)}
    for i in range(1, 7)
]
U_OBCYCH = [
    {"pod_czym": "nasz komentarz u obcego", "pod_id": 3, "autor": "obcy%d" % i,
     "jezyk": "en", "tekst": "odpowiedzieli nam u siebie %d" % i,
     "id": 300 + i, "gdzie": "komentarz_obcy", "url": "https://y/p/b",
     "kontekst": "our own comment"}
    for i in range(1, 5)
]
WSZYSTKIE = POD_ARTYKULAMI + POD_NOTKAMI + U_OBCYCH


def skad(k):
    return str(k.get("gdzie") or "notka")


print("=== 1. TAK WYGLADAJA DANE NAPRAWDE (zrodlo: browser.py) ===")
sprawdz("zadne zrodlo nie wypelnia `odpowiedzi`",
        all("odpowiedzi" not in k for k in WSZYSTKIE))
sprawdz("`reakcje` ma tylko jedno zrodlo z trzech",
        {skad(k) for k in WSZYSTKIE if "reakcje" in k} == {"artykul"},
        {skad(k) for k in WSZYSTKIE if "reakcje" in k})
_b = pathlib.Path("agent-v2/browser.py").read_text(encoding="utf-8")
sprawdz("i to sie zgadza z browser.py (jedno `reakcje` w zrodlach komentarzy)",
        '"reakcje": k.get("reaction_count") or 0' in _b)

print()
print("=== 2. KONTRDOWOD: STARY KLUCZ SORTOWANIA ===")


def stary_klucz(k):
    return (k.get("reakcje") or 0) * 2 + (k.get("odpowiedzi") or 0) * 3


def tylko_reakcje(k):
    return (k.get("reakcje") or 0) * 2


po_staremu = sorted(WSZYSTKIE, key=stary_klucz, reverse=True)[
    : config.MAX_ODPOWIEDZI_DUZE * 3]
sprawdz("czlon `odpowiedzi` nie zmienial NICZEGO (same zera)",
        [id(k) for k in sorted(WSZYSTKIE, key=stary_klucz, reverse=True)]
        == [id(k) for k in sorted(WSZYSTKIE, key=tylko_reakcje, reverse=True)])
sprawdz("stary wybor wycinal cale zrodlo `komentarz_obcy`",
        not any(skad(k) == "komentarz_obcy" for k in po_staremu),
        {skad(k) for k in po_staremu})
sprawdz("a to zrodlo browser.py nazywa najgorszym miejscem na milczenie",
        "najgorsze mozliwe miejsce na milczenie" in _b)

print()
print("=== 3. NOWY WYBOR: PO ROWNO Z KAZDEGO MIEJSCA ROZMOWY ===")
wybrane = stages._po_rowno_ze_zrodel(WSZYSTKIE, config.MAX_ODPOWIEDZI_DUZE * 3)
sprawdz("bierze dokladnie tyle, ile wolno", len(wybrane) == 24, len(wybrane))
sprawdz("wszystkie trzy zrodla sa reprezentowane",
        {skad(k) for k in wybrane} == {"artykul", "notka", "komentarz_obcy"},
        {skad(k) for k in wybrane})
sprawdz("male zrodla wchodza W CALOSCI",
        len([k for k in wybrane if skad(k) == "komentarz_obcy"]) == 4
        and len([k for k in wybrane if skad(k) == "notka"]) == 6,
        [len([k for k in wybrane if skad(k) == s])
         for s in ("artykul", "notka", "komentarz_obcy")])
sprawdz("pierwsze trzy pozycje to po jednej z kazdego zrodla",
        {skad(k) for k in wybrane[:3]} == {"artykul", "notka", "komentarz_obcy"},
        [skad(k) for k in wybrane[:3]])
sprawdz("wewnatrz zrodla nadal wygrywa najzywszy watek",
        [k["reakcje"] for k in wybrane if skad(k) == "artykul"][:3] == [20, 19, 18],
        [k["reakcje"] for k in wybrane if skad(k) == "artykul"][:3])
sprawdz("a przy braku reakcji rozstrzyga swiezosc",
        [k["id"] for k in wybrane if skad(k) == "notka"][:2] == [206, 205],
        [k["id"] for k in wybrane if skad(k) == "notka"][:2])
# Nic nie ginie i nic sie nie dubluje.
sprawdz("zaden wpis nie wystepuje dwa razy",
        len({k["id"] for k in wybrane}) == len(wybrane))
sprawdz("krotka lista przechodzi w calosci",
        len(stages._po_rowno_ze_zrodel(WSZYSTKIE, 100)) == len(WSZYSTKIE),
        len(stages._po_rowno_ze_zrodel(WSZYSTKIE, 100)))
sprawdz("pusta lista nie wywala", stages._po_rowno_ze_zrodel([], 5) == [])

print()
print("=== 4. MODEL NIE DOSTAJE JUZ MARTWYCH ZER ===")
sprawdz("zrodlo bez pomiaru reakcji nie dostaje dopisku",
        stages._ile_reakcji(POD_NOTKAMI[0]) == "",
        stages._ile_reakcji(POD_NOTKAMI[0]))
sprawdz("zrodlo z pomiarem dostaje liczbe",
        stages._ile_reakcji(POD_ARTYKULAMI[0]) == " (reakcji: 1)",
        stages._ile_reakcji(POD_ARTYKULAMI[0]))
sprawdz("KONTRDOWOD: stary opis pisal zero tam, gdzie nikt nie liczyl",
        " (reakcji: %d)" % (POD_NOTKAMI[0].get("reakcje", 0)) == " (reakcji: 0)")

print()
print("=== 5. CALY ETAP, Z PODSTAWIONYM MODELEM ===")
widziane = {}


# PODMIENIAMY TYLKO `call`, A ODPOWIEDZ ODDAJEMY SUROWA. Do 2 wrzesnia ten
# plik podmienial takze `llm.parse_json` na lambde ignorujaca `raw` — czyli
# omijal jedyna funkcje, ktora tlumaczy odpowiedz modelu na ksztalt oczekiwany
# przez kod. Tu jeszcze doklada sie proza, ktora model z wlaczonym
# wyszukiwaniem pisze WOKOL JSON-a; wlasnie na niej `parse_json` raz juz
# poleglo (dwadziescia wyszukiwan i 0,13 USD, po czym oddalo zero). Atrapa
# odtwarza wiec ten ksztalt, a nie sam czysty slownik.
ODPOWIEDZ_MODELU = (
    "I'll look through the replies and return one object {like this}.\n\n"
    + json.dumps({"choices": [{"index": i, "rank": i} for i in range(8)],
                  "skipped_because": "reszta to podziekowania"})
    + "\n\nThat covers the threads with an actual question in them.")


def call(rodzaj, system, prompt, conn=None, run_id=None, **k):
    widziane["prompt"] = prompt
    return ODPOWIEDZ_MODELU


ORYG = (stages.llm.call, stages.llm.parse_json)
try:
    stages.llm.call = call
    _log = io.StringIO()
    with contextlib.redirect_stdout(_log):
        wynik = stages.wybierz_do_odpowiedzi(None, 0, list(WSZYSTKIE))
    print(_log.getvalue(), end="")
    # ODPOWIEDZ MODELU MA BYC NAPRAWDE ZROZUMIANA. Bez tego caly ten blok
    # przechodzi rowniez wtedy, gdy `parse_json` sie wywroci: etap lapie
    # wyjatek i „bierze najstarsze", a asercje nizej nie odrozniaja wyboru
    # modelu od tego zapasu. Wlasnie tak wygladala awaria z 25 sierpnia —
    # zero z wyjasnieniem przestaje wygladac na awarie.
    sprawdz("odpowiedz modelu zostala ROZEBRANA, a nie odpuszczona",
            "[wybor] nie wyszedl" not in _log.getvalue(),
            _log.getvalue().strip().splitlines()[-1:])
    sprawdz("i to wybor modelu, nie zapas 'biore najstarsze'",
            "reszta to podziekowania" in _log.getvalue(),
            _log.getvalue().strip().splitlines()[-1:])
    sprawdz("oddaje nie wiecej niz limit duzego dnia",
            len(wynik) <= config.MAX_ODPOWIEDZI_DUZE, len(wynik))
    sprawdz("i wsrod wybranych sa wszystkie trzy miejsca rozmowy",
            {skad(k) for k in wynik} == {"artykul", "notka", "komentarz_obcy"},
            {skad(k) for k in wynik})
    sprawdz("prompt nie zawiera ani jednego martwego `(reakcji: 0)`",
            "(reakcji: 0)" not in widziane["prompt"],
            widziane["prompt"][:200])
    sprawdz("ale niesie reakcje tam, gdzie sa mierzone",
            "(reakcji: 20)" in widziane["prompt"])
    # Male konto nadal odpowiada KAZDEMU — tego progu nie ruszamy.
    male = WSZYSTKIE[:3]
    sprawdz("przy trzech komentarzach odpowiadamy wszystkim",
            stages.wybierz_do_odpowiedzi(None, 0, list(male)) == male)
finally:
    stages.llm.call, stages.llm.parse_json = ORYG

print()
print("=== PRODUKCJA ===")
zle = 0
for p in PILNOWANE:
    ok = odcisk(p) == PRZED[str(p)]
    zle += 0 if ok else 1
    print("  %-24s %s" % (pathlib.Path(p).name, "bez zmian" if ok else "ZMIENIONA"))

print()
print("=== WYNIK: %d zdanych, %d oblanych%s ===" %
      (zdane, oblane, ", PRODUKCJA RUSZONA" if zle else ""))
sys.exit(1 if (oblane or zle) else 0)
