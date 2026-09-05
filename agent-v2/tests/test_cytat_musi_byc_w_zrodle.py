# -*- coding: utf-8 -*-
"""Fragment jest dowodem, gdy stoi w dokumencie — nie gdy model tak powiedzial.

## Wada, ktora ten plik pilnuje

Caly dowod na doslownosc cytatu brzmial:

    excerpts = [e for e in data.get("excerpts", []) if isinstance(e, str) and e.strip()]

czyli „to niepusty napis". `klasyfikacja.md` bardzo dokladnie opisuje obowiazek
kopiowania slowo w slowo — i to byla cala ochrona.

Odtworzone 5 wrzesnia 2026: dokument mowiacy „The only documented number is 12"
oddawal fragment „A study found 97 percent effectiveness", a klasyfikacja
zachowywala go jako dowod klasy PRIMARY.

Fragment, ktorego w dokumencie nie ma, jest GORSZY niz brak fragmentu: idzie
dalej z etykieta zrodla, wchodzi do karty jako `evidence`, do banku jako
material do ponownego uzycia, a kazdy nastepny etap traktuje go jak cytat.

## Czego ten plik pilnuje w DRUGA strone

Zeby sprawdzenie nie wyrzucalo PRAWDZIWYCH cytatow. Normalizujemy dokladnie
to, co drukarnia zmienia bez pytania — rodzaj cudzyslowu, dlugosc myslnika,
spacje nierozdzielajace, wielokropek. NIE ruszamy cyfr, jednostek, przeczen
ani wielkosci liter: gdyby ruszac, „12" i „21" zaczelyby byc tym samym, a po
to wlasnie to sprawdzenie istnieje. Sekcje 2 i 3.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_cytat_musi_byc_w_zrodle.py
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import config  # noqa: E402

config.uzyj_katalogu_danych(pathlib.Path(tempfile.mkdtemp()))
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


DOK = ("The only documented number is 12.  The registry \u2014 updated in 2026 "
       "\u2014 says the cap is \u201cten years\u201d and not more.\n\n"
       "No independent measurement was published.")

print("=== 1. ZMYSLONY CYTAT ODPADA ===")
sprawdz("cytatu, ktorego nie ma, nie przyjmujemy",
        not stages._jest_w_dokumencie("A study found 97 percent effectiveness.", DOK))
sprawdz("takze gdy brzmi jak zdanie z dokumentu",
        not stages._jest_w_dokumencie("An independent measurement was published.", DOK))

print()
print("=== 2. PRAWDZIWY CYTAT PRZECHODZI, TAKZE PO ZMIANIE TYPOGRAFII ===")
sprawdz("doslownie", stages._jest_w_dokumencie("The only documented number is 12.", DOK))
sprawdz("zlamany innym miejscem na spacje",
        stages._jest_w_dokumencie("The only documented\n   number is 12.", DOK))
sprawdz("proste cudzyslowy zamiast drukarskich",
        stages._jest_w_dokumencie('the cap is "ten years" and not more', DOK))
sprawdz("zwykly myslnik zamiast pauzy",
        stages._jest_w_dokumencie("The registry - updated in 2026 - says", DOK))

print()
print("=== 3. CZEGO NIE WOLNO NORMALIZOWAC ===")
# KONTRDOWOD NA POPRAWKE: gdyby normalizacja siegala dalej, sprawdzenie
# przestaloby chronic przed dokladnie ta awaria, dla ktorej powstalo.
sprawdz("przestawione cyfry to INNY cytat",
        not stages._jest_w_dokumencie("The only documented number is 21.", DOK))
sprawdz("usuniete przeczenie to INNY cytat",
        not stages._jest_w_dokumencie("the cap is \u201cten years\u201d and more", DOK))
sprawdz("inna wielkosc liter to INNY cytat",
        not stages._jest_w_dokumencie("the only documented number is 12.", DOK))

print()
print("=== 4. KOD NAPRAWDE Z TEGO KORZYSTA ===")
ZR = pathlib.Path("agent-v2/stages.py").read_text(encoding="utf-8")
sprawdz("classify sprawdza kazdy fragment",
        "if _jest_w_dokumencie(e, text):" in ZR)
sprawdz("i nie przyjmuje juz samego 'niepusty napis'",
        'excerpts = [e for e in data.get("excerpts", []) if isinstance(e, str)' not in ZR)
sprawdz("odrzucone sa widoczne w dzienniku",
        "NIE MA w dokumencie" in ZR)

print()
print("=== 5. LIMITY KLASYFIKACJI SA EGZEKWOWANE ===")
# Ta sama rodzina co w dyskoverii: stala szla do promptu i na tym sie konczyla.
sprawdz("liczba fragmentow przycinana",
        "excerpts = excerpts[:config.CLASSIFY_MAX_EXCERPTS]" in ZR)
sprawdz("dlugosc fragmentu przycinana",
        "e[:config.CLASSIFY_MAX_EXCERPT_CHARS] for e in excerpts" in ZR)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
