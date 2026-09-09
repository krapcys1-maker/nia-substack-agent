# -*- coding: utf-8 -*-
"""Zrodlo, od ktorego zaczal sie temat, ma dojsc do pisarza albo zatrzymac przebieg.

## Co sie stalo 9 wrzesnia 2026

Artykul 0022 wyszedl na konto NIE NA SWOJ TEMAT.

Bank wybral historie: sto autonomicznych agentow dowodzacych twierdzen
matematycznych, wsrod ktorych samo z siebie pojawilo sie oszustwo, a inne
agenty je zglosily. Pytanie badawcze przebiegu brzmialo wprost: „dlaczego ten
sam jawny wspolny zasob, ktory pozwolil jednemu agentowi rozniesc oszustwo,
uzbraja tez uczciwe agenty, zeby je zlapac".

Lancuch, krok po kroku, kazdy odczytany z produkcji:

  1. `sources.id=9`, `fetched_ok=1` — strona POBRALA SIE poprawnie, a jej
     abstrakt lezal w pliku zadania badawczego w calosci.
  2. `stages.classify` ODRZUCILA ja: `unused_evidence` po klasyfikacji ma trzy
     inne prace, tej nie ma wcale.
  3. Zadne `confirmed_claim` nie nioslo wiec tego adresu, wiec
     `artykul_z_puli` dolozyl zdanie banku ze znacznikiem `not_fetched=True`.
  4. `stages.karta_dla_pisarza` wycina dokladnie takie wpisy.
  5. Pisarz dostal SIEDEM twierdzen o trzech obcych pracach i DZIEWIEC pozycji
     „tego nie ustalono" (`uncertain_claims`, `not_established`,
     `contradictions`). Napisal wiec o niepewnosci — bo to mial przed soba.

Zaplacone: dyskoveria, pobranie, klasyfikacja, synteza, bramka, `gpt-6-astra`
i okladka za 0,20 USD. Wlasciciel przeczytal wynik i zapytal, o czym ten
artykul w ogole jest. Pytanie bylo sluszne.

## Dlaczego to nie byla wina klasyfikatora

POWTORZONE NA PRODUKCJI, to samo zrodlo, to samo pytanie, ten sam model
(`deepseek-v4-flash`, 0,00064 USD): werdykt `PRIMARY`, trafnosc 0,90, OSIEM
wyciagow — wszystkie obecne w dokumencie co do znaku, wsrod nich zdanie
o stu agentach i o tym, jak oszustwo rozeszlo sie przez wspolna biblioteke.

Odrzucenie bylo JEDNORAZOWYM POTKNIECIEM na wywolaniu za szesc dziesiatych
centa. Nic go nie ponowilo i nic nie zauwazylo, ze zniknal wlasnie ten
dokument, dla ktorego caly przebieg powstal.

## Regula, ktorej pilnuje ten plik

Dwie polowy, i obie sa potrzebne:

  * WIODACE ZRODLO PYTAMY DRUGI RAZ. Ulamek centa ratuje przebieg za
    kilkadziesiat. Tylko wiodace — ponawianie kazdego odrzucenia byloby
    placeniem za podwazanie wlasnej bramki.
  * GDY I TAK ODPADNIE, PRZEBIEG STAJE PRZED SYNTEZA. Zatrzymanie jest
    darmowe, temat wraca do puli. Pisanie z resztek to bylo dokladnie to,
    co wypuscilo 0022.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_wiodace_zrodlo_dociera.py
"""
import io
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


WIODACE = "https://arxiv.org/abs/2609.04170"
INNE = "https://arxiv.org/abs/2601.11369"

KORPUS = [
    {"url": WIODACE, "host": "arxiv.org", "title": "Emergent Cheating and Whistleblowing",
     "text": "We report a case study on a research collective of 100 autonomous LLM agents."},
    {"url": INNE, "host": "arxiv.org", "title": "Institutional AI",
     "text": "A public governance graph declares legal states and sanctions."},
]

# Wynik, jaki `_sklasyfikuj_jedno` oddaje dla przyjetego zrodla.
def przyjete(url, traf=0.9):
    return {"url": url, "host": "arxiv.org", "title": "t", "publisher": "",
            "class": "PRIMARY", "relevance": traf, "excerpts": ["x"],
            "numbers": [], "note": ""}


class Klasyfikator:
    """Atrapa `_sklasyfikuj_jedno` z zapisem, o co i ile razy pytano."""

    def __init__(self, odrzuc_za_pierwszym=(), odrzucaj_zawsze=()):
        self.odrzuc_za_pierwszym = set(odrzuc_za_pierwszym)
        self.odrzucaj_zawsze = set(odrzucaj_zawsze)
        self.pytania = []

    def __call__(self, conn, run_id, question, source):
        url = source.get("url")
        self.pytania.append(url)
        if url in self.odrzucaj_zawsze:
            return None
        if url in self.odrzuc_za_pierwszym and self.pytania.count(url) == 1:
            return None
        return przyjete(url)


stary = stages._sklasyfikuj_jedno
try:
    print("=== 1. WIODACE ZRODLO ODRZUCONE RAZ — PYTAMY DRUGI RAZ ===")
    k = Klasyfikator(odrzuc_za_pierwszym={WIODACE})
    stages._sklasyfikuj_jedno = k
    wynik = stages.classify(None, 1, "pytanie", KORPUS, wiodacy_url=WIODACE)
    adresy = [s["url"] for s in wynik]
    sprawdz("wiodace zrodlo jest w wyniku", WIODACE in adresy, str(adresy))
    sprawdz("zapytano o nie dwa razy", k.pytania.count(WIODACE) == 2, str(k.pytania))
    sprawdz("o pozostale tylko raz", k.pytania.count(INNE) == 1, str(k.pytania))
    sprawdz("drugie zrodlo nie zginelo przy okazji", INNE in adresy, str(adresy))

    print()
    print("=== 2. NIE PONAWIAMY, GDY WIODACE PRZESZLO ZA PIERWSZYM RAZEM ===")
    # Kontrdowod dla sekcji 1. Ponawianie zawsze byloby placeniem drugi raz za
    # kazdy artykul, a nie ratunkiem.
    k = Klasyfikator()
    stages._sklasyfikuj_jedno = k
    stages.classify(None, 1, "pytanie", KORPUS, wiodacy_url=WIODACE)
    sprawdz("zero dodatkowych wywolan", len(k.pytania) == 2, str(k.pytania))

    print()
    print("=== 3. NIE PONAWIAMY CUDZYCH ODRZUCEN ===")
    # Odrzucenie zrodla, ktore NIE jest wiodace, to zwykla praca klasyfikatora.
    k = Klasyfikator(odrzuc_za_pierwszym={INNE})
    stages._sklasyfikuj_jedno = k
    wynik = stages.classify(None, 1, "pytanie", KORPUS, wiodacy_url=WIODACE)
    sprawdz("odrzucone zrodlo poboczne nie wraca",
            INNE not in [s["url"] for s in wynik], str([s["url"] for s in wynik]))
    sprawdz("i nie zaplacilismy za drugie pytanie o nie",
            k.pytania.count(INNE) == 1, str(k.pytania))

    print()
    print("=== 4. BEZ `wiodacy_url` NIC SIE NIE ZMIENIA ===")
    # `run.py` wola `classify` bez tego argumentu i ma dzialac jak dotad.
    k = Klasyfikator(odrzuc_za_pierwszym={WIODACE})
    stages._sklasyfikuj_jedno = k
    wynik = stages.classify(None, 1, "pytanie", KORPUS)
    sprawdz("stara sciezka nie ponawia", len(k.pytania) == 2, str(k.pytania))
    sprawdz("i oddaje to, co przeszlo", [s["url"] for s in wynik] == [INNE],
            str([s["url"] for s in wynik]))

    print()
    print("=== 5. DRUGIE ODRZUCENIE NIE JEST UKRYWANE ===")
    k = Klasyfikator(odrzucaj_zawsze={WIODACE})
    stages._sklasyfikuj_jedno = k
    wynik = stages.classify(None, 1, "pytanie", KORPUS, wiodacy_url=WIODACE)
    sprawdz("pytano dwa razy i tyle", k.pytania.count(WIODACE) == 2, str(k.pytania))
    sprawdz("wiodacego nie ma w wyniku",
            WIODACE not in [s["url"] for s in wynik], str([s["url"] for s in wynik]))
    # Karta zapasowa NIE JEST rozwiazaniem: `classify` nie ma prawa udawac, ze
    # cos znalazla. Decyzje podejmuje sciezka artykulu — sekcja 6.
    sprawdz("reszta materialu zostaje oddana", [s["url"] for s in wynik] == [INNE],
            str([s["url"] for s in wynik]))
finally:
    stages._sklasyfikuj_jedno = stary

print()
print("=== 6. SCIEZKA ARTYKULU STAJE PRZED SYNTEZA, NIE PO PISARZU ===")
# Kolejnosc jest cala wartoscia tej bramki. Zatrzymanie PO syntezie kosztuje
# synteze; zatrzymanie po pisarzu kosztuje `gpt-6-astra`; zatrzymanie po
# okladce kosztuje 0,20 USD za obraz do tekstu, ktory nie wyjdzie.
art = io.open("agent-v2/artykul_z_puli.py", encoding="utf-8").read()
i_klas = art.index("stages.classify(conn, run_id, brief[\"question\"], corpus")
i_stop = art.index("ZATRZYMANY: wiodące źródło", i_klas)
i_synt = art.index("stages.synthesis(", i_klas)
i_pis = art.index("stages.write(", i_klas)
i_graf = art.index("stages.grafika(", i_klas)
sprawdz("bramka PO klasyfikacji", i_stop > i_klas)
sprawdz("bramka PRZED synteza", i_stop < i_synt)
sprawdz("bramka PRZED pisarzem", i_stop < i_pis)
sprawdz("bramka PRZED okladka", i_stop < i_graf)
sprawdz("wiodacy adres podany klasyfikacji z nazwy",
        "wiodacy_url=wiodace" in art)
sprawdz("bierzemy go z tego pola, ktore wypelnia bank",
        'brief.get("zrodlo_faktu")' in art)
sprawdz("zatrzymanie ma wlasny kod wyjscia, nie ciche zero",
        art[i_stop:i_stop + 1400].count("KOD_ZATRZYMANY") == 1,
        art[i_stop:i_stop + 1400].count("KOD_ZATRZYMANY"))

sprawdz("bramka pyta, czy zrodlo BYLO w korpusie",
        "_bylo_w_korpusie" in art)

print()
print("=== 6b. ADRES, KTOREGO NIGDY NIE POBRANO, NIE ZATRZYMUJE ARTYKULU ===")
# ZLAPANE PRZEZ TEST, NIE PRZEZ ODCZYT. Pierwsza wersja tej bramki pytala
# tylko „czy wiodacy adres jest w `evidence`" i zatrzymywala takze wtedy, gdy
# tego adresu NIGDY nie bylo w korpusie.
#
# A to jest normalny przebieg: dyskoveria szuka zrodel do PYTANIA, nie do tego
# jednego linku, wiec artykul czesto stoi na innych, pobranych dokumentach.
# Dla takiego przypadku istnieje wpis `not_fetched` i on zostaje.
# Bez tego zawezenia bramka zatrzymywalaby wiekszosc artykulow — czyli
# poprawka na jeden zepsuty przebieg zepsulaby wszystkie pozostale.
i_war = art.index("_bylo_w_korpusie = any(")
sprawdz("porownuje z KORPUSEM, nie z dowodami",
        "for c in corpus" in art[i_war:i_war + 160], art[i_war:i_war + 160])
i_if = art.index("if (wiodace and _bylo_w_korpusie", i_war)
sprawdz("i oba warunki musza zajsc naraz",
        "not any(" in art[i_if:i_if + 220], art[i_if:i_if + 220])

print()
print("=== 7. TO, CO WYCIELA TEMAT Z KARTY, NADAL DZIALA ===")
# `karta_dla_pisarza` usuwa wpisy `not_fetched` i TO JEST SLUSZNE: taki wpis
# nie jest wyciagiem z pobranego dokumentu. Poprawka nie rozbraja tej reguly,
# tylko sprawia, ze wiodace zrodlo nie musi z niej korzystac.
karta = {"confirmed_claims": [
    {"claim": "dolozone przez bank", "url": WIODACE, "not_fetched": True},
    {"claim": "prawdziwy wyciag", "url": INNE},
]}
po = stages.karta_dla_pisarza(karta)
sprawdz("wpis `not_fetched` nadal nie idzie do pisarza",
        [c["claim"] for c in po["confirmed_claims"]] == ["prawdziwy wyciag"],
        str(po["confirmed_claims"]))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
