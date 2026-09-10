# -*- coding: utf-8 -*-
"""Notka ma ksztalt: trzy uderzenia, kazde w swojej linijce.

## Pomiar, ktory to rozstrzygnal

10 wrzesnia 2026, piec notek przyjetych przez wlasciciela wobec dwoch
odrzuconych:

                          uderzen (linii)   slow na uderzenie
    przyjete                    3,2               17,2
    odrzucone                   1,5               46,7

Ta sama laczna dlugosc, zupelnie inny ksztalt. Przyjete to TRZY KROTKIE
LINIE; odrzucone to jeden blok. Kazda przyjeta konczy sie zdaniem wycelowanym
w kogos: „Some of you need a satellite network before you'll listen to
a woman." Odrzucone urywaja sie w polowie mysli.

## Kto to zepsul

Nikt z zewnatrz. Zrobily to dwa zdania, ktore sam wpisalem, obie w dobrej
wierze:

  * w silniku: „Choose your own length: one line can be a complete answer and
    so can a short paragraph" — zgoda na blok;
  * w kartridzu, TUZ NAD piecioma przykladami pokazujacymi uklad:
    „They demonstrate possibilities, not one required order" — kasacja tego,
    co przyklady pokazuja.

To ten sam ksztalt wady, ktory rano znalazlem w glosie artykulu („take their
nerve, not their size"). Poprawilem go tam i przeoczylem tutaj.

Wlasciciel przeczytal wynik i powiedzial, ze trzeba wyciagac Enigme, zeby
zrozumiec, o co chodzi.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_notka_ma_ksztalt.py
"""
import io
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


OSOBOWOSC = io.open("agent-v2/personality.py", encoding="utf-8").read()
WSPOLNY = " ".join(io.open("presety/nia-unfiltered/prompty/glos_wspolny.md",
                           encoding="utf-8").read().split())
KOMENTARZ = " ".join(io.open("presety/nia-unfiltered/prompty/glos_komentarza.md",
                             encoding="utf-8").read().split())

print("=== 1. SILNIK ZAMAWIA KSZTALT, NIE SWOBODE ===")
sprawdz("zgoda na dowolna dlugosc zniknela",
        "Choose your own length" not in OSOBOWOSC)
sprawdz("ksztalt jest nieobowiazkowy? NIE",
        "SHAPE, and it is not optional" in OSOBOWOSC)
sprawdz("trzy albo cztery krotkie linie",
        "three or four SHORT LINES" in OSOBOWOSC)
sprawdz("z prawdziwymi lamaniami wiersza",
        "separated by real line breaks" in OSOBOWOSC)
sprawdz("okolo pietnastu do dwudziestu slow na linie",
        "fifteen to twenty words each" in OSOBOWOSC)

print()
print("=== 2. TRZY UDERZENIA SA NAZWANE ===")
for numer, fraza in ((1, "In a note: THE THING, plainly, in one line"),
                     (2, "THE ABSURDITY, about the PEOPLE"),
                     (3, "A LINE AIMED AT SOMEBODY")):
    sprawdz("uderzenie %d nazwane" % numer, fraza in OSOBOWOSC, fraza)
sprawdz("zart siedzi w uderzeniu drugim",
        "and it is the joke" in OSOBOWOSC)
# UDERZENIE PIERWSZE ROZNI SIE MIEDZY FORMAMI, i to tez jest pomiar.
# 10 wrzesnia 2026 odpowiedz na jedno emoji zaczela sie od „Chaos Engine hits
# me with a single emoji and calls the lock 'fitted, not locked.'" Kartridz
# tego zabranial, a silnik pol zdaniem pozwalal: „What happened, or what they
# said". Silnik stoi blizej zadania i wygral.
sprawdz("w odpowiedzi uderzenie pierwsze to ODPOWIEDZ",
        "YOUR ANSWER, in one line" in OSOBOWOSC)
sprawdz("i wprost zakazuje opisu cudzej wypowiedzi",
        "Never a description of" in OSOBOWOSC)
sprawdz("stare pozwolenie na streszczanie zniknelo",
        "What happened, or what they said" not in OSOBOWOSC)
sprawdz("zadnego gestego akapitu", "Never one dense paragraph" in OSOBOWOSC)
# FRAZA NIEROZCIETA. Instrukcja jest sklejana z kilku literalow, wiec
# „past twenty-five words" w PLIKU jest przelamane miedzy nimi, choc
# w gotowym napisie stoi razem. Szukamy czegos, co w zrodle jest ciagle.
sprawdz("dluga linia to dwie linie",
        "it is two lines" in OSOBOWOSC)

print()
print("=== 3. NIC JUZ NIE KASUJE UKLADU PRZYKLADOW ===")
# TO BYLA PRZYCZYNA. Piec przykladow POKAZUJE trzy uderzenia, a zdanie tuz
# nad nimi mowilo, ze uklad nie obowiazuje.
# ZDANIE ZOSTAJE W PLIKU — JAKO CYTAT Z WYJASNIENIA, nie jako polecenie.
# Pierwsza wersja tego sprawdzenia zadala jego calkowitej nieobecnosci
# i oblewala na akapicie, ktory tlumaczy, czemu je usunieto.
i_cytat = WSPOLNY.find("not one required order")
sprawdz("zdanie nie jest juz poleceniem, tylko cytatem",
        i_cytat < 0 or "used to end" in WSPOLNY[max(0, i_cytat - 120):i_cytat],
        WSPOLNY[max(0, i_cytat - 120):i_cytat + 40] if i_cytat >= 0 else "brak")
sprawdz("i wystepuje najwyzej raz",
        WSPOLNY.count("not one required order") <= 1,
        WSPOLNY.count("not one required order"))
sprawdz("uklad nazwany wymaganym",
        "their layout is the shape of a note" in WSPOLNY.lower())
sprawdz("z pomiarem obok", "words per beat" in WSPOLNY)
sprawdz("i z powodem, czemu tamto zdanie szkodzilo",
        "was doing the damage" in WSPOLNY)
# Artykul nadal moze powtarzac ten ciag z dowodami miedzy uderzeniami — ale
# nie moze go porzucic.
sprawdz("dluzsza forma powtarza ciag, a nie porzuca go",
        "never gets to abandon it" in WSPOLNY)

print()
print("=== 4. KOMENTARZ I RESTACK IDA TYM SAMYM RYTMEM ===")
sprawdz("komentarz w tych samych trzech uderzeniach",
        "in the same three beats as a Note" in KOMENTARZ)
sprawdz("jedno zdanie wolno, blok nie",
        "may never be is a paragraph the reader has to untangle" in KOMENTARZ)
sprawdz("przy cierpieniu zadlo zamienia sie w cieplo, ksztalt zostaje",
        "the sting becomes warmth, but the shape stays" in KOMENTARZ)
# RESTACK: to jest ta wpadka, ktora wlasciciel widzial na ekranie — podpis
# odpowiadal na inne pytanie niz to, ktore czytelnik ma przed oczami.
sprawdz("restack odpowiada na ICH post",
        "if their post is a question, your caption answers that question"
        in KOMENTARZ)
sprawdz("i nie streszcza go", "Do not summarise it" in KOMENTARZ)

print()
print("=== 5. STARE POZWOLENIA NIE ZOSTALY OBOK ===")
# Kontrdowod: gdyby zgoda na akapit przetrwala gdziekolwiek, model wybralby
# ja, bo jest latwiejsza.
sprawdz("brak `take a short paragraph if the thought needs it`",
        "take a short paragraph if the thought needs it" not in KOMENTARZ)
sprawdz("brak `Vary rhythm` jako furtki",
        "Vary rhythm" not in OSOBOWOSC)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
