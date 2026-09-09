# -*- coding: utf-8 -*-
"""Odnosnik w tekscie nie jest niewypelnionym polem szablonu.

## Po co ten plik istnieje

9 wrzesnia 2026 gotowy artykul zostal ODLOZONY BEZ PUBLIKACJI po zaplaceniu za
bank, dyskoverie z pietnastoma wyszukiwaniami, pobranie zrodla, klasyfikacje,
synteze, bramke „warto pisac", pisarza i recenzje:

    -- ZATRZYMANY: artefakty w tekscie --
       [ARTEFAKT_SZABLONU] znacznik szablonu: …In the [Institutional AI
       study](https://arxiv.org/abs/2601.11369)…

## Przyczyna, ktora widac dopiero razem

Wzorzec mial lapac `[INSERT DATE]` i podobne — nawias z SAMYMI wielkimi
literami:

    \\[[A-Z][A-Z _]{2,40}\\]

`jezyki.wzorzec` kompiluje jednak KAZDY wzorzec z `re.IGNORECASE`. Pod tym
przelacznikiem `[A-Z]` przestaje znaczyc „wielka litera" i caly czlon zmienia
sie w „dowolny ciag liter i spacji w nawiasie kwadratowym" — czyli w tekst
KAZDEGO odnosnika Markdown.

Dwie decyzje osobno rozsadne: wzorzec pisany z mysla o wielkosci liter i jedna
wspolna kompilacja bez rozroznienia. Razem zamykaja publikacje artykulu, ktory
cytuje zrodlo — a cytowanie zrodel jest obowiazkiem tego konta.

Wada byla w SILNIKU, wiec dotyczyla kazdego presetu, nie tylko NIA.

## Regula, ktorej pilnuje ten test

Placeholder ma byc lapany, odnosnik ma przechodzic. Zakres wielkosci liter
przywraca `(?-i:...)` przy tym jednym czlonie; reszta wzorca zostaje
niewrazliwa, bo `todo` i `tbd` pisze sie roznie.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_link_to_nie_placeholder.py
"""
import sys

sys.path.insert(0, "agent-v2")
import config   # noqa: E402
import gates    # noqa: E402
import jezyki   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# PRZEPISANE Z ODLOZONEGO ARTYKULU 0022, nie wymyslone.
Z_ODNOSNIKIEM = ("Your agent constitution sounds rather grand. In the "
                 "[Institutional AI study](https://arxiv.org/abs/2601.11369), "
                 "a protocol was agreed and then quietly ignored.")

print("=== 1. ODNOSNIK PRZECHODZI ===")
sprawdz("artykul z odnosnikiem nie jest zatrzymywany",
        gates.artefakty_w_tekscie(Z_ODNOSNIKIEM) == [],
        str(gates.artefakty_w_tekscie(Z_ODNOSNIKIEM))[:120])

for tekst in ("See [the agents took over](https://example.org/a) for the record.",
              "Read [what the maintainer actually merged](https://example.org/b).",
              "[A short one](https://example.org/c) opens the paragraph."):
    sprawdz("przechodzi: %s" % tekst[:44],
            gates.artefakty_w_tekscie(tekst) == [],
            str(gates.artefakty_w_tekscie(tekst))[:100])

print()
print("=== 2. PLACEHOLDER NADAL LAPANY ===")
# Kontrdowod. Poprawka, ktora przepuszcza odnosniki KOSZTEM placeholderow,
# jest gorsza od wady: niewypelnione pole poszloby na konto.
for tekst, co in (("Data publikacji: [INSERT DATE].", "[INSERT DATE]"),
                  ("Liczba subskrybentow: [TBD].", "[TBD]"),
                  ("TODO: dopisac liczbe.", "TODO"),
                  ("TBD before publishing.", "TBD"),
                  ("Wpisz tu [uzupelnic date] i gotowe.", "[uzupelnic ...]"),
                  ("Sed ut lorem ipsum dolor sit.", "lorem ipsum"),
                  ("Wartosc: [PLACEHOLDER VALUE].", "[PLACEHOLDER VALUE]"),
                  ("Termin: [INSERT_DATE_HERE].", "[INSERT_DATE_HERE]")):
    sprawdz("lapie %s" % co, gates.artefakty_w_tekscie(tekst) != [], tekst)

print()
print("=== 3. WZORZEC NADAL JEST NIEWRAZLIWY TAM, GDZIE MA BYC ===")
# `todo` i `tbd` pisze sie roznie, wiec te czlony MUSZA zostac bez rozroznienia.
# Gdyby ktos naprawil wade, wylaczajac IGNORECASE dla calego wzorca, ten test
# ma oblac.
for tekst in ("[todo: dopisac]", "[Todo: dopisac]", "[TODO: dopisac]",
              "[placeholder for the number]", "Lorem Ipsum dolor"):
    sprawdz("lapie mimo wielkosci liter: %s" % tekst[:34],
            gates.artefakty_w_tekscie(tekst) != [], tekst)

print()
print("=== 4. OBA JEZYKI MAJA TE SAMA POPRAWKE ===")
# Wzorzec stoi w `jezyki.WZORCE` osobno dla angielskiego i polskiego. Poprawka
# tylko w jednym oddaloby wade drugiemu kartridzowi.
zrodlo = open("agent-v2/jezyki.py", encoding="utf-8").read()
sprawdz("dwa wystapienia z przywroconym zakresem",
        zrodlo.count("(?-i:[A-Z][A-Z _]{2,40})") == 2,
        "wystapien: %d" % zrodlo.count("(?-i:[A-Z][A-Z _]{2,40})"))
sprawdz("zero wystapien starego, wrazliwego na IGNORECASE",
        "|\\[[A-Z][A-Z _]{2,40}\\]|" not in zrodlo)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
