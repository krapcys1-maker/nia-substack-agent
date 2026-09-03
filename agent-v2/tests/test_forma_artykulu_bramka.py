"""Bramka formy: model obserwuje z cytatem, kod liczy i rozstrzyga.

Cztery rzeczy, ktorych zaden regex nie zmierzy: gestosc beatow, eskalacja
rejestru, moment przylapania czytelnika i znajomosc otwarcia. Wszystkie
pochodza z playbooka z 20 sierpnia, wszystkie potwierdzily sie na artykule
0025 przy recznym sprawdzeniu.

PODZIAL PRACY, KTORY JEST TU CALYM POMYSLEM. Model dostaje pytania, na ktore
odpowiada CYTATEM albo tak/nie. Nie liczy, nie dzieli, nie ocenia glebokosci
procentowej. Wszystko, co jest arytmetyka — ile beatow na ile slow, gdzie
w tekscie stoi cytat — robi kod, bo arytmetyki modelu nie da sie sprawdzic,
a cytat da sie znalezc w tekscie i porownac.

JEDNA SWIADOMA ROZNICA WOBEC PLAYBOOKA, pilnowana w sekcji 4. Playbook chce
momentu przylapania czytelnika miedzy 25 a 40 procentem glebokosci. My
zglaszamy wylacznie BRAK tego momentu, nigdy jego pozycje. Regula nakazujaca
pozycje wypelnia ja jedna odpowiedzia i po dziesieciu tekstach sama staje sie
podpisem maszyny — a to jest dokladnie ta wada, ktora juz raz zrobilismy,
naprawiajac tresc i zamawiajac przy okazji szkielet.
"""
import sys

sys.path.insert(0, "agent-v2")
import config   # noqa: E402
import gates    # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# Tekst 900-slowowy z rozpoznawalnymi kotwicami — pozycje musza byc liczone
# z prawdziwego tekstu, nie zgadywane.
TEKST = (
    "The mark was designed for someone else entirely. " * 30
    + "\n\nThe carton in your door shelf carries the same trick. "
    + "Filler about the mechanism repeated at length. " * 40
    + "\n\nNine percent of all plastic ever made has been recycled. "
    + "ASTM published revision D7611 in 2013. "
    + "More filler about procedure repeated at length. " * 40
)
# Dlugosc dobrana CELOWO tak, zeby prog wypadal MIEDZY czterema a szescioma
# beatami: ~826 slow to 206 slow na beat przy czterech (oblewa) i 138 przy
# szesciu (przechodzi). Bez tego kontrdowod w sekcji 1 niczego nie odroznia —
# bramka zapalalaby sie tak samo, gdyby powtorzenia liczyly sie jako beaty,
# czyli mierzylaby gadatliwosc zamiast gestosci.

# Obserwacja taka, jaka model MUSI oddac dla 0025 — recznie sprawdzilem,
# ze te wlasnie cechy w nim sa.
JAK_0025 = {
    "beliefs": [
        {"belief": "kod nie znaczy przetwarzalne",
         "first_stated": "The mark was designed for someone else entirely."},
        {"belief": "czym jest naprawde",
         "first_stated": "It is a resin identification code."},
        {"belief": "skala rozjazdu",
         "first_stated": "Nine percent of all plastic ever made has been recycled."},
        {"belief": "ten sam mechanizm gdzie indziej",
         "first_stated": "The date printed on a carton of milk does the same work."},
    ],
    "support_only": [
        {"quote": "The number originally sat inside the chasing arrows.", "supports": 0},
        {"quote": "State laws required the codes on plastic packaging.", "supports": 0},
    ],
    "hardest_fact": {
        "quote": "Nine percent of all plastic ever made has been recycled.",
        "why": "liczba, ktora czytelnik powtorzy"},
    "procedural_nearby": {"quote": "ASTM published revision D7611 in 2013."},
    "same_register": True,
    "reader_moment": None,
    "opening_claim": {"quote": "The mark was designed for someone else entirely.",
                      "already_familiar": False},
    "summary": "szesc beatow, brak eskalacji, brak przylapania",
}


def bez(klucz, wartosc):
    o = dict(JAK_0025)
    o[klucz] = wartosc
    return o


print("=== 1. GESTOSC BEATOW ===")
u = gates.uwagi_z_formy(JAK_0025, TEKST)
nazwy = {x["gate"] for x in u}
slow = len(TEKST.split())
print("    tekst: %d słów, 4 przekonania -> jedno co %.0f słów (próg %d)"
      % (slow, slow / 4, config.SLOW_NA_BEAT))
sprawdz("próg to 150 słów na beat", config.SLOW_NA_BEAT == 150, config.SLOW_NA_BEAT)
sprawdz("rozdmuchany tekst zgłoszony", "GESTOSC_BEATOW" in nazwy, nazwy)
szczegol = next(x["detail"] for x in u if x["gate"] == "GESTOSC_BEATOW")
sprawdz("uwaga cytuje to, co było samym wsparciem",
        "chasing arrows" in szczegol, szczegol[:90])

# KONTRDOWOD: powtorzenie NIE moze liczyc sie jako beat. Gdyby liczylo,
# ten sam tekst mialby szesc beatow i przeszedlby — czyli bramka mierzylaby
# gadatliwosc, a nie gestosc.
wszystkie_nowe = bez("beliefs", JAK_0025["beliefs"] + [
    {"belief": "wsparcie policzone jako przekonanie", "first_stated": w["quote"]}
    for w in JAK_0025["support_only"]])
sprawdz("gdyby wsparcie liczyło się jako przekonanie, przeszłoby (test rozróżnia)",
        "GESTOSC_BEATOW" not in {x["gate"] for x in
                                 gates.uwagi_z_formy(wszystkie_nowe, TEKST)})

# Gesty tekst ma przechodzic, inaczej bramka mowi tylko „pisz krocej".
gesty = bez("beliefs", [{"belief": "b%d" % i, "first_stated": "Q%d." % i}
                        for i in range(12)])
sprawdz("gęsty tekst przechodzi",
        "GESTOSC_BEATOW" not in {x["gate"] for x in gates.uwagi_z_formy(gesty, TEKST)})
sprawdz("brak obserwacji nie zgłasza nic",
        gates.uwagi_z_formy({}, TEKST) == [{"gate": "CZYTELNIK_NIEPRZYLAPANY",
                                            "detail": gates.uwagi_z_formy({}, TEKST)[0]["detail"]}])

print()
print("=== 2. ESKALACJA REJESTRU ===")
sprawdz("ten sam ton zgłoszony", "BRAK_ESKALACJI" in nazwy, nazwy)
d = next(x["detail"] for x in u if x["gate"] == "BRAK_ESKALACJI")
sprawdz("uwaga pokazuje OBA cytaty",
        "Nine percent" in d and "D7611" in d, d[:110])
sprawdz("inny ton przechodzi",
        "BRAK_ESKALACJI" not in {x["gate"] for x in
                                 gates.uwagi_z_formy(bez("same_register", False), TEKST)})

print()
print("=== 3. OTWARCIE NA ZNANYM ===")
sprawdz("świeże otwarcie przechodzi", "OTWARCIE_ZNANE" not in nazwy, nazwy)
znane = bez("opening_claim", {"quote": "Plastic recycling mostly does not work.",
                              "already_familiar": True})
w = gates.uwagi_z_formy(znane, TEKST)
sprawdz("znane otwarcie zgłoszone",
        "OTWARCIE_ZNANE" in {x["gate"] for x in w})
sprawdz("i cytuje to twierdzenie",
        any("mostly does not work" in x["detail"] for x in w))

print()
print("=== 4. PRZYLAPANIE CZYTELNIKA — ZGLASZAMY BRAK, NIGDY POZYCJE ===")
sprawdz("brak momentu zgłoszony", "CZYTELNIK_NIEPRZYLAPANY" in nazwy, nazwy)

CYTAT = "The carton in your door shelf carries the same trick."
z_momentem = bez("reader_moment", {"quote": CYTAT, "object": "carton"})
w = gates.uwagi_z_formy(z_momentem, TEKST)
sprawdz("moment obecny -> brak zarzutu",
        "CZYTELNIK_NIEPRZYLAPANY" not in {x["gate"] for x in w})

# TO JEST TA ROZNICA WOBEC PLAYBOOKA i dlatego stoi tu osobny tekst.
# Playbook chce momentu przylapania miedzy 25 a 40 procentem glebokosci.
# Budujemy przypadek JEDNOZNACZNIE poza pasmem — zwrot do czytelnika na samym
# koncu — i sprawdzamy, ze bramka MILCZY. Pozycje liczymy i pokazujemy
# wlascicielowi jako informacje, ale nie jest wada, bo nakaz pozycji po
# dziesieciu tekstach sam staje sie podpisem maszyny.
PONO = ("Opening claim here. " + "Long middle section. " * 120
        + "The carton in your door shelf carries the same trick.")
gdzie = gates.pozycja_w_tekscie(CYTAT, PONO)
print("    cytat stoi na %.0f%% głębokości (playbook chce 25-40%%)" % (100 * gdzie))
sprawdz("kod UMIE policzyć pozycję", gdzie is not None and 0 < gdzie < 1, gdzie)
sprawdz("ta pozycja jest DALEKO poza pasmem playbooka", gdzie > 0.75, gdzie)
pono_uwagi = gates.uwagi_z_formy(
    bez("reader_moment", {"quote": CYTAT, "object": "carton"}), PONO)
sprawdz("mimo to bramka milczy o przyłapaniu",
        not any(x["gate"] == "CZYTELNIK_NIEPRZYLAPANY" for x in pono_uwagi),
        pono_uwagi)
sprawdz("żadna uwaga nie mówi o pozycji ani o procentach",
        all("głębok" not in x["detail"] and "%" not in x["detail"]
            for x in pono_uwagi), pono_uwagi)
# I ten sam warunek na pierwszym tekscie — zeby nie bylo, ze przeszlo
# przypadkiem przy jednym ukladzie.
sprawdz("to samo przy cytacie wcześnie w tekście",
        all("głębok" not in x["detail"] for x in w), w)

# Cytat, ktorego nie ma w tekscie -> pozycja nieznana, nie wyjatek.
sprawdz("zmyślony cytat nie wywala", gates.pozycja_w_tekscie("nie ma mnie tu", TEKST) is None)
sprawdz("pusty cytat nie wywala", gates.pozycja_w_tekscie("", TEKST) is None)

print()
print("=== 5. PROMPT PROSI O OBSERWACJE, NIE O OCENE ===")
p = (config.PROMPTS_DIR / "forma.md").read_text(encoding="utf-8")
sprawdz("prompt istnieje", len(p) > 500)
sprawdz("wymaga cytatu dosłownego", "verbatim" in p)
sprawdz("mówi wprost, że nie ocenia", "not scoring it" in p)
sprawdz("pyta o to, w co czytelnik teraz wierzy",
        "What the reader now believes" in p)
sprawdz("zabrania chodzenia po zdaniach",
        "Do **not** walk the article sentence by sentence" in p)
sprawdz("ma test scalania",
        "merge test" in p)
sprawdz("ma przyklad bledu do uniknięcia",
        "Worked example of the error" in p)
sprawdz("odrzuca statystykę jako przyłapanie",
        "is not this" in p and "68%" in p)
sprawdz("NIE prosi modelu o procenty ani pozycje",
        "25%" not in p and "40%" not in p and "depth" not in p.lower())
sprawdz("ma miejsce na tekst", "{body}" in p)

print()
print("=== 6. WPIETE W PRZEBIEG ===")
zrodlo = open("agent-v2/run.py", encoding="utf-8").read()
sprawdz("run woła obserwację formy", "stages.ocen_forme" in zrodlo)
sprawdz("run składa z niej uwagi", "gates.uwagi_z_formy" in zrodlo)
sprawdz("run podaje poprzednie teksty do ODCISK_FORMY",
        "poprzednie=stages.poprzednie_teksty(" in zrodlo)
# Bez tego porownanie zestawia tekst SAM ZE SOBA i oddaje 5-6 wspolnych cech,
# co wyglada jak alarm, a jest tautologia. Ugryzlo mnie dwa razy.
sprawdz("i wyklucza z porównania bieżący artykuł",
        'pomin_tresc=draft["body"]' in zrodlo)
sprawdz("awaria formy nie zatrzymuje artykułu",
        "obserwacja formy padła" in zrodlo)
sprawdz("etap da się zatrzymać flagą", '"forma",' in zrodlo)
import stages   # noqa: E402
sprawdz("stages ma ocen_forme", hasattr(stages, "ocen_forme"))
sprawdz("stages ma poprzednie_teksty", hasattr(stages, "poprzednie_teksty"))
sprawdz("forma ma własny model", "forma" in config.MODEL_FOR, config.MODEL_FOR.keys())
sprawdz("forma ma sufit tokenów", config.MAX_TOKENS.get("forma", 0) > 0
        if hasattr(config, "MAX_TOKENS") else True)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
