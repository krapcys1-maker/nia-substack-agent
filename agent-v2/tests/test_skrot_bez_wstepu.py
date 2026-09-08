# -*- coding: utf-8 -*-
"""Skrot ma niesc wydarzenie, a nie zaproszenie do subskrypcji.

## Po co ten plik istnieje

`_skrot` tnie pierwsze 300 znakow opisu z RSS. Zmierzone 8 wrzesnia 2026 na
dziewietnastu zywych kanalach: szesnascie zaczyna od tresci, a trzy stawiaja
na poczatku siebie.

  Import AI     okolo 180 z 300 znakow to masthead i prosba o subskrypcje,
                jedyna informacja pada tuz przed nozem
  Pluralistic   opis ma 24 328 znakow i otwiera go spis tresci
  Show HN       380 znakow samych adresow i licznikow, zero zdania o rzeczy

Pisarka notek dostawala wiec akapit reklamy zamiast materialu i nie miala
z czego niczego wytlumaczyc.

## Regula, ktorej pilnuje ten test

Obcinamy zdania TYLKO od poczatku i TYLKO dopoki sa wstepem. Pierwsze zdanie
niosace tresc zatrzymuje ciecie — dlatego tekst, w ktorym slowo „subscribe"
pada w SRODKU historii, musi przezyc w calosci. Gdy nie zostaje nic, oddajemy
pusty napis: sam tytul jest uczciwszy niz adres URL podany jako streszczenie.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_skrot_bez_wstepu.py
"""
import sys

sys.path.insert(0, "agent-v2")
import korpus_kanalow  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


bez = korpus_kanalow._bez_wstepu

# --- TEKSTY POBRANE Z ZYWYCH KANALOW 8 WRZESNIA 2026 -------------------------
IMPORT_AI = (
    "Welcome to Import AI, a newsletter about AI research. Import AI runs on "
    "arXiv, cappuccinos, and feedback from readers. If you’d like to "
    "support this, please subscribe. Subscribe now Researchers discover "
    "another OpenAI agent emergent communication incident: “Less severe, "
    "but worrying”")

SHOW_HN = ("Article URL: https://github.com/erqeon/mu Comments URL: "
           "https://news.ycombinator.com/item?id=49608465 Points: 1 "
           "# Comments: 1")

PLURALISTIC = ("Today's links How corporate America built a better Roach "
               "Motel: Hostages beat customers every day. Hey look at this: "
               "Delights to delectate.")

IEEE = ("You sit down and put your arm in the cradle. You press a button. "
        "The machine takes it from there.")

REGISTER = ("Even the best model gets fungus identification right just 65% of "
            "the time - talk about a false friend")

print("=== 1. IMPORT AI: MASTHEAD I PROSBA O SUBSKRYPCJE LECA ===")
w = bez(IMPORT_AI)
sprawdz("nie zaczyna sie od powitania", not w.lower().startswith("welcome"), w[:60])
sprawdz("zniknelo 'Subscribe now'", "subscribe now" not in w.lower(), w[:60])
sprawdz("zniknely cappuccinos z mastheadu", "cappuccino" not in w.lower(), w[:60])
sprawdz("zostala prawdziwa informacja", "Researchers discover" in w, w[:60])
sprawdz("i zaczyna sie od niej", w.startswith("Researchers discover"), w[:60])

print()
print("=== 2. SHOW HN: SAME ADRESY TO BRAK SKROTU, NIE SKROT ===")
w = bez(SHOW_HN)
sprawdz("oddaje pusty napis", w == "", repr(w[:60]))

print()
print("=== 3. PLURALISTIC: SPIS TRESCI LECI, PIERWSZA POZYCJA ZOSTAJE ===")
w = bez(PLURALISTIC)
sprawdz("nie zaczyna sie od naglowka spisu",
        not w.lower().startswith("today"), w[:60])
sprawdz("zostala tresc pierwszej pozycji", "Roach Motel" in w, w[:60])

print()
print("=== 4. SZESNASCIE POZOSTALYCH KANALOW BEZ ZMIANY ===")
# Regula, ktora poprawia trzy kanaly kosztem szesnastu, jest gorsza od zadnej.
sprawdz("IEEE Spectrum nietkniete", bez(IEEE) == IEEE, bez(IEEE)[:60])
sprawdz("The Register nietkniete", bez(REGISTER) == REGISTER, bez(REGISTER)[:60])

print()
print("=== 5. 'SUBSCRIBE' W SRODKU HISTORII MUSI PRZEZYC ===")
# To jest wlasciwy powod, dla ktorego ciecie idzie od poczatku i zatrzymuje sie
# na pierwszym prawdziwym zdaniu. Notka o buncie czytelnikow Substacka jest
# dokladnie tym materialem, po ktory to konto siega najchetniej.
HISTORIA = ("Readers revolted after the paper moved its archive behind a "
            "paywall. Subscribe now, the banner said, and forty thousand "
            "people did the opposite.")
sprawdz("caly tekst przezyl", bez(HISTORIA) == HISTORIA, bez(HISTORIA)[:70])

print()
print("=== 6. PRZYPADKI GRANICZNE NIE WYWALAJA FUNKCJI ===")
sprawdz("pusty napis", bez("") == "")
sprawdz("None traktowane jak pustka", bez(None) == "")
sprawdz("sam wstep bez kropki oddaje pustke",
        bez("Welcome to Import AI, a newsletter about AI research") == "",
        repr(bez("Welcome to Import AI, a newsletter about AI research")))
sprawdz("biale znaki zwijane", bez("  dwa   slowa  ") == "dwa slowa",
        repr(bez("  dwa   slowa  ")))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
