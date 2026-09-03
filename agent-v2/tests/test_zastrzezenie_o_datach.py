# -*- coding: utf-8 -*-
"""Pisarz nie moze twierdzic, ze ZRODLO jest bez daty.

CO SIE STALO 30 SIERPNIA. Przebieg na zywo napisal artykul „The Guardrails Were
Off Because That Was the Test" — 1123 slowa, research z zrodel pierwotnych,
recenzja przeszla, okladka wygenerowana. Bramka faktow przed publikacja
ODMOWILA, i mialo to jeden powod:

    karta:  „the other sources are undated IN THE EXCERPTS"
    tekst:  „the OpenAI, Hugging Face and CyberScoop accounts ARE UNDATED"

Karta byla ostrozna. Pisarz skreslil trzy slowa i zamienil zdanie o NASZYM
MATERIALE w zdanie o CUDZYCH DOKUMENTACH. Sprawdzacz otworzyl te strony,
znalazl na nich daty i zablokowal publikacje:

    „Every substantive claim about the incidents is confirmed by primary
     sources (...) but the text asserts as fact that only METR's investigation
     carries an explicit publication date (...) a claim the record contradicts"

Zginal caly artykul — research, pisanie, obraz i sprawdzenie — przez zdanie,
ktore nie dotyczylo nawet tematu, tylko naszego wlasnego zaplecza.

TO NIE BYL PIERWSZY RAZ. Artykul 10 napisal „several of the official texts
behind them carry no publication date" — ten sam ksztalt, tylko wtedy nikt tego
nie sprawdzil. Z trzech artykulow, ktore w ogole relacjonowaly te note, dwa
podnioosly ostrozne zdanie karty do twierdzenia o swiecie.

REGULA ZABRANIA WADY, NIE PRZEPISUJE KSZTALTU. Nie mowimy pisarzowi, jakie
zdanie ma napisac — mowimy, czego nie wolno twierdzic, bo tego nie widzial.
To ta sama zasada, co przy „the fastest available" wobec „the fastest of the
four the paper tested".

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo.
"""
import pathlib
import sys

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


brief = " ".join(pathlib.Path("agent-v2/prompts/pisarz.md")
                 .read_text(encoding="utf-8").split())

print("=== 1. ZAKAZ JEST WPROST, NIE DOMYSLNY ===")
sprawdz("prompt zabrania mowic, ze zrodlo JEST bez daty",
        "Never say a source IS undated" in brief)
sprawdz("i podaje powod: widzielismy wyciag, nie zrodlo",
        "you have seen an excerpt of it" in brief.lower())

print()
print("=== 2. STOI NA TYM, CO SIE STALO, A NIE NA ZASADZIE ===")
# Regula bez kosztu jest rada. Ta ma cene: jeden artykul.
sprawdz("podaje oba zdania — ostrozne i za szerokie",
        "undated in the excerpts" in brief
        and "accounts are undated" in brief)
sprawdz("i mowi, czym to sie skonczylo",
        "refused to publish" in brief)

print()
print("=== 3. DAJE, CO WOLNO POWIEDZIEC ZAMIAST TEGO ===")
# Sam zakaz zamyka temat: pisarz pominalby zastrzezenie w ogole, a ukrycie
# go jest gorsze niz wiek materialu — tak mowi zdanie obok w tym samym
# briefie. Wiec zakaz musi miec wyjscie.
for wolno in ("the excerpt carries no date",
              "the URL gives a month but no day",
              "the page we pulled did not say when it was written"):
    sprawdz("  wolno: %s" % wolno[:44], wolno in brief)
sprawdz("i nazywa je MNIEJSZYM twierdzeniem, nie slabszym",
        "let it be the smaller claim" in brief)

print()
print("=== 4. NIE ZABILO REGULY, KTORA MIALO WZMOCNIC ===")
# Zastrzezenie ma NADAL byc podane. Gdyby poprawka wyciszyla cala note,
# zamienilibysmy jeden blad na drugi — a ukrycie wieku jest gorsze.
sprawdz("nota o wieku nadal trafia do czytelnika",
        "the reader is told once, plainly" in brief)
sprawdz("i nadal jest nazwana prawem czytelnika",
        "the reader's right to weigh" in brief)
# 1 wrzesnia 2026: stopke z data pisze teraz KOD (`stages.wstaw_date_zrodel`),
# a prompt ma modelowi tego ZABRANIAC. Trzy artykuly z rzedu zablokowala bramka
# faktow za te jedna linijke — model przepisywal date z pamieci, choc karta ma
# ja w `source_dates["newest"]`, a kod czyta to pole w czterech miejscach.
# Ostatni raz audyt napisal w tym samym zdaniu, ze wszystkie twierdzenia
# merytoryczne sa potwierdzone, i mimo to obalil caly tekst.
sprawdz("prompt ZABRANIA modelowi pisac stopke z data",
        "Do not write a datestamp" in brief)
sprawdz("i mowi, ze doda ja kod",
        "written by code" in brief and "will be stripped" in brief)
sprawdz("ale daty WEWNATRZ argumentu zostaja u modelu",
        "Dates inside the argument are still yours" in brief)

print()
print("=== 5. KONTRDOWOD: PROMPT SPRZED POPRAWKI MUSI TU POLEC ===")
# Bez tego test nie dowodzi niczego. Odtwarzamy stara wersje akapitu —
# tylko to, co bylo — i sprawdzamy, ze sekcja 1 na niej nie przechodzi.
stary = (" ".join("""
  **And if `source_dates.note` says the material is old, the reader is told
  once, plainly, in your own words.** A piece about this subject resting on
  nothing newer than last year is a piece with a caveat, and hiding the caveat
  is worse than the age. This is the one place where saying how you know is not
  narrating the research — it is the reader's right to weigh what they are
  reading.
""".split()))
sprawdz("stara wersja NIE zawiera zakazu",
        "Never say a source IS undated" not in stary)
sprawdz("ale zawiera zdanie, ktore poprawka zostawila",
        "the reader's right to weigh" in stary)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
