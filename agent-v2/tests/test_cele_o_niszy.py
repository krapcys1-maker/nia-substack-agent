# -*- coding: utf-8 -*-
"""Komentujemy tam, gdzie czytelnik ma powod nas obserwowac.

ZMIERZONE na 82 udanych komentarzach z tygodnia:

    82 komentarze  ->  3 odpowiedzi   (4%)
    z 30 postow o AI bylo 4-6

Reszta to bylo etykietowanie zywnosci, rezerwa paliwowa USA, korespondencyjni
przyjaciele, odpornosc na odre, transport kontenerowy, Ksiega Henocha, oplaty
za bilety. Kazdy z tych komentarzy mogl byc doskonaly i nie przyniesc nic, bo
ktos czytajacy o rezerwie paliwowej nie ma powodu chciec publikacji o AI.

Rozklad byl przy tym prawie plaski — po jednym komentarzu na publikacje, po
kilkudziesieciu roznych newsletterach. Nikt nie widzial nas dwa razy.

PRZYCZYNA BYLA NAPISANA WPROST W REGULE. Prompt nazywal konto publikacja o AI,
ale zadne z dwoch kryteriow nie wymagalo, zeby POST byl o AI — a pierwsze wprost
to rozszerzalo: „It does not have to be the post's subject". Model stosowal
regule POPRAWNIE: pod rezerwa paliwowa jest system i mamy co dodac, wiec dwa
razy tak. To resztka po epoce przedmiotow, ta sama klasa co dziewiec promptow
poprawionych tego samego dnia.

CZEGO TA POPRAWKA NIE ROBI. Nie rusza `ODSTEP_DNI_NA_PUBLIKACJE` — wlasciciel
byl jednoznaczny: „nie chce zeby jak bot wygladac, on nie ma nakurwiac na jednym
profilu". Odstep zostaje. Rozpoznawalnosc ma sie brac z WEZSZEJ PULI odwiedzanej
w tym samym rytmie, nie z czestszego pisania w jednym miejscu.

BEZ PYTESTA, bez sieci. Uruchamiac z korzenia repozytorium.
"""
import pathlib
import sys

sys.path.insert(0, "agent-v2")
import config   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


brief = " ".join(pathlib.Path("agent-v2/prompts/cele.md")
                 .read_text(encoding="utf-8").split())

print("=== 1. PYTANIE O CZYTELNIKA JEST PIERWSZE ===")
sprawdz("kryteria sa trzy, nie dwa",
        "yes to all three" in brief and "yes to both" not in brief)
# ASERCJA PRZEPIETA NA CONFIG. Stala tu wpisana nazwa niszy — czyli
# test pilnujacy KOLEJNOSCI kryteriow mial wpisana nisze i oblewal sie przy
# kazdej jej zmianie z powodu, ktory nie ma nic wspolnego z kolejnoscia.
# NISZA JEST POLEM, nie wpisana nazwa — `stages._prompt` wstrzykuje ja do
# kazdego promptu. Test pyta wiec o KSZTALT zdania, nie o jego wypelnienie.
sprawdz("pierwsze pyta o powod czytelnika",
        "reason to follow a publication about {nisza}" in brief
        or "reason to follow a publication about %s" % config.NISZA in brief)
sprawdz("i stoi PRZED pytaniem o mechanizm",
        brief.index("reason to follow a publication")
        < brief.index("Is there a system underneath"))

print()
print("=== 2. STARA REGULA ZNIKNELA ===")
# To ona wpuszczala rezerwe paliwowa: „nie musi byc tematem posta".
sprawdz("nie ma juz 'does not have to be the post's subject'",
        "does not have to be the post's subject" not in brief
        or "The old rule said" in brief)
sprawdz("a jesli jest, to jako opis BLEDU",
        "The old rule said" in brief)

print()
print("=== 3. GRANICA JEST NARYSOWANA, NIE DOMYSLNA ===")
# Bez wyliczenia przypadkow „wezej" zamienia sie w „tylko jesli tytul nazywa
# temat wprost".
#
# WYLICZENIE, NIE JEGO TRESC. Stalo tu „hiring, pricing, moderation" oraz
# „software, data, platforms" — przypadki opisane pod jedna, konkretna nisze.
# Test oblewal wiec przy kazdym przestawieniu tematu, chociaz regula jest
# niezmienna: granica ma byc NARYSOWANA kilkoma przypadkami, nie zostawiona
# domyslnosci. Sprawdzamy strukture i ten jeden przypadek, ktory z zalozenia
# stoi poza nisza, zeby pokazac, gdzie granica przebiega.
for przypadek in ("the post is about our subject itself",
                  "the same mechanism is doing the",
                  "the wider field our subject sits inside",
                  "a fuel reserve, a shipping route, a food label"):
    sprawdz("  wymieniony przypadek: %s" % przypadek[:34], przypadek in brief)
sprawdz("mowi wprost, ze tytul nie musi nazywac tematu",
        "does NOT mean the post must" in brief)

print()
print("=== 4. STOI NA POMIARZE ===")
sprawdz("podaje liczbe komentarzy i odpowiedzi",
        "82 comments went out and 3 came back" in brief)
sprawdz("i przyklady tego, co odpadalo",
        "food labelling" in brief and "Book of Enoch" in brief)

print()
print("=== 5. ODSTEPU NIE RUSZAMY ===")
# Decyzja wlasciciela. Sprawdzamy, ze wartosc stoi i ze prompt jej nie podwaza.
sprawdz("ODSTEP_DNI_NA_PUBLIKACJE nadal istnieje",
        getattr(config, "ODSTEP_DNI_NA_PUBLIKACJE", 0) >= 1,
        config.ODSTEP_DNI_NA_PUBLIKACJE)
sprawdz("i jest odstepem kilkudniowym, nie godzinowym",
        config.ODSTEP_DNI_NA_PUBLIKACJE >= 3,
        config.ODSTEP_DNI_NA_PUBLIKACJE)
sprawdz("prompt mowi, ze powrot jest DOBRY, nie podejrzany",
        "Returning to a publication we have been in before is good" in brief)
sprawdz("i ze odstep nie jest do wazenia przez model",
        "not yours to weigh" in brief)

print()
print("=== 6. STARE ZABEZPIECZENIA NIE ZGINELY ===")
for zakaz in ("gambling", "Horoscopes", "Personal grief",
              "correction of the author's personal experience"):
    sprawdz("  nadal odmawiamy: %s" % zakaz[:34], zakaz in brief)
sprawdz("milczenie nadal jest normalna odpowiedzia",
        "Most of them will not be" in brief)

print()
print("=== 7. REJESTR: ZIOMEK, NIE PROFESOR ===")
# Wlasciciel, po przeczytaniu prawdziwych komentarzy: „ma nie brzmiec jak
# profesor fizyki, bardziej jak dobry ziomek, ktory sie zna na AI".
#
# Trzy z ostatnich siedmiu komentarzy nie mialy W ZDANIU ZADNEGO CZLOWIEKA:
#   „Stargate announced $500 billion over four years on January 21, 2025."
# a jeden byl wykladem z trzema numerami artykulow GDPR, otwartym od korekty.
kom = " ".join(pathlib.Path("agent-v2/prompts/komentarz.md")
               .read_text(encoding="utf-8").split())
sprawdz("prompt zada, zeby ktos byl w zdaniu",
        "Somebody is in the sentence" in kom)
sprawdz("zada jednego faktu, nie trzech",
        "One fact, not three" in kom)
sprawdz("zabrania otwierania od korekty",
        "Do not open by telling them they are wrong" in kom)
sprawdz("i zada powiedzenia, CZEMU to lada",
        "Say why it lands" in kom)
sprawdz("numery artykulow tylko gdy sa sednem",
        "when the number IS the point" in kom)
sprawdz("stoi na prawdziwych przykladach, nie na zasadzie",
        "Stargate announced" in kom and "GDPR Article 22" in kom)
sprawdz("ale nie zamienia bezposredniosci na uprzejmosc",
        "blunt is not the same as formal" in kom)
sprawdz("i nie kasuje zgody na 'nie wiem'",
        "I don't know" in kom)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
