# -*- coding: utf-8 -*-
"""Cytat ma niesc CALE twierdzenie, razem z okolicznoscia.

ZMIERZONE RECZNIE na 93 twierdzeniach z dwunastu kart. Cztery dopisywaly
okolicznosc, ktorej cytat nie zawiera:

    twierdzenie: „...zrecenzowac inne zgloszenie ZANIM WYNIKI ZOSTANA
                 OPUBLIKOWANE"
    cytat      : „Each submitter is required to review at least one other
                 submission."  — prawda, i ani slowa o momencie

    twierdzenie: „numery pojawiaja sie, bo STANOWE PRAWA TEGO WYMAGALY,
                 uchwalone w 39 stanach"
    cytat      : „The laws eventually passed in 39 states."  — ktore prawa i
                 czego wymagaly, w zdaniu nie ma

    twierdzenie: „...i obejma TYLKO NIEWIELKA CZESC deepfake'ow"
    cytat      : mowi o roli w ZMNIEJSZANIU ich liczby — inne zdanie w tym
                 samym plaszczu

    twierdzenie: „PRZED OSTATECZNYM GLOSOWANIEM federacja scenarzystow..."
    cytat      : stanowisko federacji, bez daty i bez glosowania

Kazde z nich jest prawdopodobnie prawdziwe gdzies w swoim dokumencie — i to
jest cala pulapka. Sprawdzenie przechodzi, bo cytat ISTNIEJE, a nikt nie
zauwaza, ze nie SIEGA. W sierpniu kosztowalo to artykul: blok cytatu od
lobbystow wydrukowany jako ustalenie komisji, gdzie kazdy fragment naprawde
stal w dokumencie.

DLACZEGO NIE MA TU BRAMKI KODOWEJ. Moja miara — slowa nosne obecne w
twierdzeniu, nieobecne w cytacie — dala na prawdziwych danych 15 trafien, z
czego DZIEWIEC falszywych: „shall" wobec „must", „until" wobec „before",
„don't" wobec „do not", „each of the 48 states" wobec „all 48 states", jedno
po chinsku. Szescdziesiat procent falszywych alarmow. Bramka na takim sygnale
wyrzucalaby dwa dobre twierdzenia na kazde zle, a odrzucenie jest w tym potoku
trwale. Zostaje regula w prompcie — z pomiarem, bo regula bez przykladu jest
w tym projekcie martwa.

BEZ PYTESTA, bez platnych wywolan. Uruchamiac z korzenia repozytorium.
"""
import pathlib
import re
import sys

sys.path.insert(0, "agent-v2")

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


def plaski(t):
    return " ".join(t.split())


brief = plaski(pathlib.Path("agent-v2/prompts/synteza.md")
               .read_text(encoding="utf-8"))

print("=== 1. REGULA JEST W PROMPCIE ===")
sprawdz("zada, zeby cytat niosl okolicznosc",
        "MUST CARRY THE WHOLE CLAIM" in brief)
sprawdz("wymienia, o jakie okolicznosci chodzi",
        all(s in brief for s in ("timing", "exclusivity", "obligation",
                                 "quantity")))
sprawdz("daje pytanie kontrolne do zadania sobie",
        "would it still say what I just wrote" in brief)
sprawdz("i mowi, co zrobic przy braku pokrycia",
        "drop the circumstance from the claim" in brief)

print()
print("=== 2. REGULA STOI NA POMIARZE, NIE NA PRZEKONANIU ===")
sprawdz("podaje liczbe z pomiaru",
        "four cards in ninety-three claims" in brief)
for wzor in ("BEFORE RESULTS ARE RELEASED", "STATE LAWS REQUIRED THEM",
             "ONLY A SMALL PORTION", "BEFORE THE FINAL VOTE"):
    sprawdz("  wpisany przyklad: %s" % wzor.lower()[:34], wzor in brief)

print()
print("=== 3. NAZYWA PULAPKE, NIE TYLKO ZAKAZUJE ===")
# Regula, ktora mowi „nie rob tak", jest slabsza od takiej, ktora mowi
# DLACZEGO sprawdzenie tego nie lapie.
sprawdz("mowi, ze sprawdzenie przechodzi mimo wady",
        "the check passes because the quote EXISTS" in brief)
sprawdz("i przypomina, co to kosztowalo",
        "In August this cost us an article" in brief)

print()
print("=== 4. STARE REGULY NIE ZGINELY PRZY OKAZJI ===")
sprawdz("nadal zada doslownego cytatu",
        "If you cannot quote the support verbatim" in brief)
sprawdz("nadal zada adresu",
        "the URL it came from" in brief)
sprawdz("nadal pilnuje, czyja jest liczba",
        "say WHOSE number it is" in brief)
# BEZ WIELKOSCI LITER. „Do not convert" zaczyna zdanie, wiec ma wielka litere;
# sprawdzenie przypiete do malej pekalo na prompcie, ktory regule ZAWIERA.
sprawdz("nadal zakazuje przeliczania liczb",
        "do not convert" in brief.lower() and "do not average" in brief.lower())

print()
print("=== 5. KONTRDOWOD: SUROWA MIARA MA DUZO FALSZYWYCH TRAFIEN ===")
# To jest powod, dla ktorego NIE ma tu bramki kodowej. Gdyby miara byla dobra,
# regula w prompcie bylaby drugim wyborem.
NOSNE = re.compile(r"\b(before|after|only|must|required|all|each|not)\b", re.I)


def brakujace(claim, cytat):
    return ({w.lower() for w in NOSNE.findall(claim)}
            - {w.lower() for w in NOSNE.findall(cytat)})


pary_niewinne = [
    ("Some products do not need either label.",
     "Some products don't need either of these labels."),
    ("...drew officials from all 48 states.",
     "...drew officials from each of the then 48 states."),
    ("The information must be provided in a clear manner.",
     "The information shall be provided in a clear manner."),
]
falszywe = sum(1 for c, e in pary_niewinne if brakujace(c, e))
sprawdz("surowa miara alarmuje na synonimach i skrotach",
        falszywe == len(pary_niewinne),
        "%d z %d" % (falszywe, len(pary_niewinne)))

pary_prawdziwe = [
    ("...must review another submission before results are released.",
     "Each submitter is required to review at least one other submission."),
]
lapie = sum(1 for c, e in pary_prawdziwe if brakujace(c, e))
sprawdz("i owszem, lapie tez prawdziwa nadinterpretacje", lapie == 1)
sprawdz("czyli sama nie nadaje sie na bramke — stad regula w prompcie",
        falszywe > lapie)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
