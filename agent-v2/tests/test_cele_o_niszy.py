# -*- coding: utf-8 -*-
"""Komentujemy tam, gdzie czytelnik ma powod nas obserwowac.

ZMIERZONE na 82 udanych komentarzach z tygodnia:

    82 komentarze          ->  3 odpowiedzi   (4%)
    30 z nich pod postami z NASZEJ niszy  ->  4-6% odpowiedzi

Pozostale piecdziesiat dwa poszly pod teksty o rzeczach, ktorych ta publikacja
nie dotyka wcale — od etykiet na zywnosci po historie starozytna. Kazdy z tych
komentarzy mogl byc doskonaly i nie przyniesc nic: ktos czytajacy o czym innym
nie ma powodu chciec akurat nas.

Rozklad byl przy tym prawie plaski — po jednym komentarzu na publikacje, po
kilkudziesieciu roznych newsletterach. Nikt nie widzial nas dwa razy.

PRZYCZYNA BYLA NAPISANA WPROST W REGULE. Prompt nazywal konto publikacja o swojej
niszy, ale zadne z dwoch kryteriow nie wymagalo, zeby POST tez byl z tej niszy —
a pierwsze wprost to rozszerzalo: „It does not have to be the post's subject".
Model stosowal regule POPRAWNIE: pod dowolnym tekstem da sie znalezc watek,
w ktorym mamy co dodac, wiec odpowiadal „tak" dwa razy z trzech. To ta sama
klasa wady, co przyklady z poprzedniej niszy w dziewieciu promptach, poprawione
tego samego dnia.

CZEGO TA POPRAWKA NIE ROBI. Nie rusza `ODSTEP_DNI_NA_PUBLIKACJE`. Decyzja
wlasciciela jest jednoznaczna: konto ma nie wygladac jak bot, wiec nie wolno mu
zageszczac obecnosci w jednym miejscu. Odstep zostaje. Rozpoznawalnosc ma sie
brac z WEZSZEJ PULI odwiedzanej w tym samym rytmie, nie z czestszego pisania
w jednym miejscu.

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
        "does not have to be the post's subject" not in brief)
# ZASADA BEZ HISTORII. Stalo tu „a jesli jest, to jako opis BLEDU" z frazą
# „The old rule said" — prompt czystego bota nie opowiada, jak brzmiala jego
# poprzednia wersja; niesie regule, ktora z tamtej poprawki wynikla.
sprawdz("nazywanie mechanizmu nie jest samo w sobie powodem",
        "Being able to name a mechanism is not a reason to comment" in brief)

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
print("=== 4. MOWI, CZEMU DOBRY KOMENTARZ POD OBCYM TEMATEM NIC NIE DAJE ===")
# ZASADA, NIE POMIAR. Stal tu wynik z jednego tygodnia jednego konta („82
# comments went out and 3 came back") i lista tematow, pod ktorymi tamto konto
# komentowalo. Prompt czystego bota nie niesie historii cudzego konta; niesie
# regule, ktora z tej historii wynikla — i to jej pilnujemy.
sprawdz("komentarz moze byc swietny i nic nie przyniesc",
        "A comment can be excellent and still bring nothing" in brief)
sprawdz("bo czytelnik czego innego nie ma powodu nas chciec",
        "has no reason to want us" in brief)

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
# Przyklady z opublikowanych komentarzy poprzedniego konta wyszly z promptu
# razem z reszta jego historii. Pilnujemy zdania, ktore je zastapilo.
sprawdz("nazywa wprost, czym rejestr NIE jest",
        "Not a lecture, not a citation, not a database row" in kom)
sprawdz("ale nie zamienia bezposredniosci na uprzejmosc",
        "blunt is not the same as formal" in kom)
sprawdz("i nie kasuje zgody na 'nie wiem'",
        "I don't know" in kom)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
