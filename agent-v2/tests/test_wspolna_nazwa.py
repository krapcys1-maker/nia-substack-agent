# -*- coding: utf-8 -*-
"""Trzy notki o tym samym modelu w jeden dzien — „plaskosc", o ktorej mowil wlasciciel.

CO WYSZLO 31 sierpnia 2026. Piec notek, z tego TRZY o modelu ACME-5.3-Flash:

    12:40  „On ACME-5.3 Flash, the run that passes a flaky task is the longer
            one only 46% of the time."
    19:58  „Ox Alpha (...) was Zhipu's ACME-5.3-Flash, served entirely from
            a cluster of more than 100,000 Chinese-made chips."
    22:09  „ACME-5.3-Flash charges $0.15 per million input tokens and still
            scores 57 on the Artificial Analysis Intelligence Index."

Trzy rozne ustalenia — o powtorzeniach, o chinskich ukladach, o cenie. Ale
czytelnik nie widzi trzech ustalen. Widzi trzy notki o tym samym modelu
w ciagu jednego dnia.

WYKRYWACZ UZNAL KAZDA PARE ZA ROZNA. `_o_tym_samym` liczy wspolne rdzenie
i ich udzial; tu wspolnych bylo cztery, a udzial ponizej progu — bo kazda
notka mowila o czym innym INNYMI slowami. Dwie z nich dzielily przy tym
DOSLOWNIE token `acme-5.3-flash`.

BANK BYL PELEN BLIZNIAKOW, co to napedzalo. Zmierzone tego samego dnia na
53 wpisach po przestawieniu konta:

    ACME-5.3        8 wpisow        Ox Alpha        4
    Papryczka       7               Spirit Airlines 3
    PortalModeli   5               FirmaD     3

Wykrywacz bliźniakow W PARTII istnial i dzialal (`_dzielą_rzadkie`), ale byl
funkcja LOKALNA w `wez_kandydatow` — sciezka notek go nie widziala, a
porownanie MIEDZY DNIAMI szlo wylacznie po slowach.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo.
"""
import pathlib
import sys

sys.path.insert(0, "agent-v2")
import stages  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# PRAWDZIWE TEKSTY Z PRODUKCJI, skrocone. Nie wymyslone.
ACME_A = ("On ACME-5.3 Flash, the run that passes a flaky task is the longer one "
         "only 46% of the time. Worse than a coin flip.")
ACME_B = ("Ox Alpha, the anonymous model that swept OpenRouter's usage charts, "
         "was Zhipu's ACME-5.3-Flash, served from Chinese-made chips.")
ACME_C = ("Cheap models are supposed to be worse models. ACME-5.3-Flash charges "
         "$0.15 per million input tokens and still scores 57.")
INNA = ("A model's refusal is not a rule. It's a single direction in its "
        "weights, and subtracting that direction removes refusing altogether.")
OSOBISTA = ("Two paragraphs. That's how much of any answer I skip before I "
            "start reading. Somewhere in the last year the model trained me.")

print("=== 1. TRZY NOTKI O NAZWIE WLASNEJ SA ROZPOZNANE JAKO TO SAMO ===")
for opis, a, b in (("12:40 vs 19:58", ACME_A, ACME_B),
                   ("19:58 vs 22:09", ACME_B, ACME_C),
                   ("12:40 vs 22:09", ACME_A, ACME_C)):
    sprawdz("  %s" % opis, stages.wspolna_nazwa(a, b) == "acme53",
            stages.wspolna_nazwa(a, b))

print()
print("=== 2. MYSLNIK I SPACJA TO TA SAMA NAZWA ===")
# To bylo sedno: `ACME-5.3-Flash` (jeden token) wobec `ACME-5.3 Flash` (dwa).
sprawdz("`ACME-5.3-Flash` daje rdzen acme53",
        "acme53" in stages.nazwy_wlasne("ACME-5.3-Flash charges $0.15"))
sprawdz("`ACME-5.3 Flash` tez",
        "acme53" in stages.nazwy_wlasne("On ACME-5.3 Flash, the run"))
sprawdz("i pelna postac zostaje przy zapisie z myslnikiem",
        "acme53flash" in stages.nazwy_wlasne("ACME-5.3-Flash charges"))

print()
print("=== 3. ROZNE TEMATY ZOSTAJA ROZNE ===")
# Poprawka, ktora blokuje wszystko, jest gorsza od wady: przy realizacji
# normy notek 63% falszywy alarm kosztuje notke.
for opis, a, b in (("ACME vs abliteracja", ACME_A, INNA),
                   ("ACME vs osobista", ACME_A, OSOBISTA),
                   ("abliteracja vs osobista", INNA, OSOBISTA)):
    sprawdz("  %s -> rozne" % opis, not stages.wspolna_nazwa(a, b),
            stages.wspolna_nazwa(a, b))

print()
print("=== 4. POCZATEK ZDANIA NIE JEST NAZWA WLASNA ===")
# „Cheap models are supposed..." oddawalo `cheap` jako nazwe, wiec dwa
# dowolne teksty zaczynajace sie tym samym slowem wygladaly na blizniaki.
sprawdz("`Cheap` na poczatku zdania odsiane",
        "cheap" not in stages.nazwy_wlasne(ACME_C), sorted(stages.nazwy_wlasne(ACME_C)))
sprawdz("dwa teksty od tego samego slowa to nie blizniaki",
        not stages.wspolna_nazwa("Cheap tricks never work. The point is simple.",
                                 "Cheap talk is what this industry runs on."))
# ALE nazwa z cyfra albo wielka litera w srodku liczy sie takze na poczatku.
sprawdz("`GPT-5` na poczatku zdania nadal jest nazwa",
        "gpt5" in stages.nazwy_wlasne("GPT-5 changed the default. Nothing else did."))

print()
print("=== 5. RZADKOSC LICZONA W KORPUSIE ===")
# Nazwa, ktora pada w polowie naszych notek („OpenAI"), nie odroznia niczego.
korpus = ["OpenAI said this. " * 2, "OpenAI said that.", "OpenAI again.",
          "Something about Papryczka chips."]
sprawdz("czesta nazwa nie blokuje",
        not stages.wspolna_nazwa("OpenAI raised prices", "OpenAI hired someone",
                                 korpus))
sprawdz("rzadka nazwa blokuje",
        stages.wspolna_nazwa("The Papryczka chip is inference-only",
                             "Nvidia lost to Papryczka on watts", korpus)
        == "papryczka")

# OGRANICZENIE, KTORE PRZYJMUJEMY SWIADOMIE. Nazwa stojaca WYLACZNIE na
# poczatku zdania przepada — „Papryczka beat the GB200" nie odda `papryczka`.
# To cena za odsianie „Cheap", „Three", „Same" i kazdego innego pierwszego
# slowa. Przy notce na 50-60 slow nazwa pada zwykle takze w srodku zdania,
# a falszywe trafienie kosztuje notke: przy realizacji normy 63% to nie
# jest darmowe. Test zapisuje to jako ZNANE, nie udaje, ze nie istnieje.
sprawdz("nazwa tylko na poczatku zdania przepada (znane ograniczenie)",
        not stages.wspolna_nazwa("The Papryczka chip is inference-only",
                                 "Papryczka beat the GB200", korpus))
sprawdz("bez korpusu wystarczy sama wspolna nazwa",
        stages.wspolna_nazwa("OpenAI raised prices", "OpenAI hired someone")
        == "openai")

print()
print("=== 6. WPIETE W WYBOR NOTKI, MIEDZY DNIAMI ===")
zrodlo = pathlib.Path("agent-v2/stages.py").read_text(encoding="utf-8")
i = zrodlo.index("def wybierz_material(")
blok = zrodlo[i:zrodlo.index("\ndef ", i + 10)]
sprawdz("wybor notki pyta o wspolna nazwe", "wspolna_nazwa(" in blok)
sprawdz("i robi to po sprawdzeniu slow, nie zamiast",
        blok.index("POROWNANIE_MIEDZY_DNIAMI") < blok.index("wspolna_nazwa("))
sprawdz("korzysta z TEKSTOW, nie z gotowych rdzeni",
        "teksty_wczesniej" in blok)
sprawdz("i mowi w logu, co pominal", "[notki] pomijam" in blok)

print()
print("=== 7. DZIALANIE W KSZTALCIE, KTORY WOLA PRODUKCJA ===")
# TU BYLA WADA TEGO TESTU, ZLAPANA PRZEZ AUDYT GODZINE PO NAPISANIU.
#
# Pierwsza wersja podawala TEKSTY w parametrze `wczesniej` — i przechodzila.
# Ale produkcja podaje tam `pamiec_wystawionych()`, czyli `list[frozenset]`
# (odciski, nie teksty, i slusznie: tokenizowanie 10 000 notek przy kazdym
# porownaniu to 1,86 s zamiast 0,005 s). Kod filtrowal `isinstance(u, str)`,
# wiec w produkcji dostawal ZAWSZE pusta liste i caly wykrywacz byl martwy.
#
# Test dowodzil dzialania ksztaltu, ktorego produkcja nie uzywa — dokladnie
# to, co ten projekt nazywa „test z atrapa mowi, ze cos jest wolane; nie
# mowi, czy oddaje cokolwiek uzytecznego".
#
# Dlatego kazde wywolanie ponizej wyglada TAK SAMO jak w `notki_dnia`:
# odciski w `wczesniej`, teksty osobnym parametrem.
def _odciski(*teksty):
    return [frozenset(stages._slowa(x)) for x in teksty]


wynik = stages.wybierz_material(
    [{"domain": "AI", "fact": ACME_B},
     {"domain": "AI", "fact": "Roughly 1200 agents traded 70,000 messages."}],
    unikaj=[], wczesniej=_odciski(ACME_A, INNA), teksty=[ACME_A, INNA])
sprawdz("wzial temat o agentach, nie drugi raz o ACME",
        wynik and "1200 agents" in str(wynik.get("fact")), wynik)
# KONTRDOWOD: bez notki o ACME w pamieci ten sam kandydat ma przejsc.
wynik2 = stages.wybierz_material(
    [{"domain": "AI", "fact": ACME_B}], unikaj=[],
    wczesniej=_odciski(INNA), teksty=[INNA])
sprawdz("a bez ACME w pamieci bierze go normalnie",
        wynik2 and "Ox Alpha" in str(wynik2.get("fact")), wynik2)

# SAME ODCISKI, BEZ TEKSTOW — dokladnie to, co bylo w produkcji przed
# poprawka. Ma przepuscic, bo z odciskow nazwy wlasnej nie da sie odczytac;
# ta linijka istnieje po to, zeby bylo widac, CZEGO odciski nie umieja.
wynik3 = stages.wybierz_material(
    [{"domain": "AI", "fact": ACME_B}], unikaj=[], wczesniej=_odciski(ACME_A))
sprawdz("same odciski nie niosa nazwy — i test to POKAZUJE",
        wynik3 and "Ox Alpha" in str(wynik3.get("fact")), wynik3)

# DZISIEJSZE NOTKI (`unikaj`) TEZ SA POROWNYWANE. Trzy notki o ACME wyszly
# W CIAGU JEDNEGO DNIA, wiec sama pamiec z poprzednich dni nie wystarczy.
wynik4 = stages.wybierz_material(
    [{"domain": "AI", "fact": ACME_B},
     {"domain": "AI", "fact": "Roughly 1200 agents traded 70,000 messages."}],
    unikaj=[ACME_A], wczesniej=[])
sprawdz("powtorka w obrebie JEDNEGO dnia tez jest lapana",
        wynik4 and "1200 agents" in str(wynik4.get("fact")), wynik4)

print()
print("=== 8. TEKSTY NOTEK MAJA SKAD PRZYJSC ===")
sprawdz("jest `teksty_ostatnich_notek`",
        hasattr(stages, "teksty_ostatnich_notek"))
sprawdz("i produkcja ja wola",
        "teksty=teksty_notek" in pathlib.Path("agent-v2/stages.py")
        .read_text(encoding="utf-8"))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
