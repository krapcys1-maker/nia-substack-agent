# -*- coding: utf-8 -*-
"""Odpowiedz pod artykulem: kontrolka nazywa sie `Comment`, pole to edytor.

## Co bylo zepsute

Pod artykulem o zamku dwoje czytelnikow napisalo komentarz. NIA odpowiedziala
obojgu — model napisal odpowiedzi i zaplacilismy za nie — po czym obie proby
skonczyly sie tak:

    nie znalazlem przycisku odpowiedzi

Zero na dwie. Kod sam pisze o sobie, ze „male konto zyje z rozmowy".

## Dwie przyczyny, obie odczytane z ukladu strony

Po nieudanej probie zapisalismy `dom-odpowiedzi.html` i przejrzeli go zamiast
zgadywac dalej. Wyszlo, ze szukanie bylo zle na dwa sposoby naraz:

  1. NAZWA. Kod pytal o „Reply". W calym dokumencie to slowo pada
     w interfejsie RAZ, jako `Leave a reply...` w polu nowego komentarza pod
     artykulem — przy pojedynczym komentarzu nie ma go wcale. Wiersz akcji to
     ikony BEZ TEKSTU, rozpoznawalne po `aria-label`: `Like`, `Comment`,
     `More options`. Odpowiedz otwiera `Comment`.
  2. KSZTALT. Kod wymagal elementu BEZ DZIECI o takim tekscie, a przycisk
     zawiera `<svg>`.

Po naprawie wyszla trzecia, tej samej klasy: `page.locator("textarea")` czekal
dziesiec sekund i padal, bo Substack rysuje tu ProseMirror, czyli
`div[contenteditable="true"]` — ten sam widget, ktory obsluguje juz
`wypelnij_artykul`.

## Sprawdzone na zywo

9 wrzesnia 2026, artykul o zamku, komentarz „Chaos Engine", `wyslij=False`:

    przycisk odpowiedzi znaleziony przy komentarzu 'Chaos Engine'
        (aria-label w kontenerze autora)
    wpisane w pole odpowiedzi (edytor tiptap): 5 slow
    (nie wysylam — tryb sprawdzenia)

BEZ PYTESTA, bez sieci, bez przegladarki. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_przycisk_odpowiedzi.py
"""
import ast
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


ZRODLO = io.open("agent-v2/browser.py", encoding="utf-8").read()
DRZEWO = ast.parse(ZRODLO)
LINIE = ZRODLO.splitlines()
FN = next(n for n in ast.walk(DRZEWO)
          if isinstance(n, ast.FunctionDef)
          and n.name == "wystaw_odpowiedz_pod_artykulem")
CIALO = "\n".join(LINIE[FN.lineno - 1:FN.end_lineno])

print("=== 1. SZUKAMY NAZWY, KTORA TA KONTROLKA NAPRAWDE MA ===")
sprawdz("`comment` jest wsrod etykiet", "comment|odpowiedz" in CIALO or
        "reply|comment" in CIALO, "brak `comment` w zestawie")
sprawdz("etykiety w jednym miejscu, nie trzy razy osobno",
        CIALO.count("ETYKIETY = re.compile") == 1,
        CIALO.count("ETYKIETY = re.compile"))
sprawdz("polskie odpowiedniki zostaly",
        "odpowiedz" in CIALO and "komentarz" in CIALO)
# KONTRDOWOD: gdyby ktos wrocil do samego „reply", ten wiersz ma oblac.
i = CIALO.index("ETYKIETY = re.compile")
sprawdz("zestaw nie jest juz samym `reply`",
        "comment" in CIALO[i:i + 120], CIALO[i:i + 120])

print()
print("=== 2. KOTWICA TO AUTOR, ZEBY NIE TRAFIC W CUDZY WATEK ===")
sprawdz("szukamy odnosnika z nazwiskiem autora",
        'get_by_role("link", name=autor)' in CIALO)
sprawdz("i idziemy w gore do NAJBLIZSZEGO przodka z kontrolka",
        "for poziom in range(1, 8)" in CIALO)
sprawdz("przerywamy na pierwszym trafieniu",
        CIALO.count("przycisk, skad = kand.first") >= 1)

print()
print("=== 3. TRZY DROGI, W KOLEJNOSCI OD NAJPEWNIEJSZEJ ===")
i1 = CIALO.index("aria-label w kontenerze autora")
i2 = CIALO.index("tekst w kontenerze autora")
i3 = CIALO.index("odleglosc od nazwiska")
sprawdz("rola, potem tekst, potem odleglosc", i1 < i2 < i3, (i1, i2, i3))
sprawdz("heurystyka czyta aria-label, nie sam tekst",
        "getAttribute('aria-label')" in CIALO)

print()
print("=== 4. POLE ODPOWIEDZI: EDYTOR PRZED `textarea` ===")
# PORZADEK MIERZONY NA WPISACH LISTY, nie na dowolnym wystapieniu napisu.
# Pierwsza wersja szukala `page.locator("textarea")` i trafiala w KOMENTARZ,
# ktory tlumaczy, czemu to pole nie dziala — a komentarz stoi wyzej niz kod.
i_tiptap = CIALO.index('("edytor tiptap"')
i_edytor = CIALO.index('("edytor contenteditable"')
i_area = CIALO.index('("pole tekstowe"')
sprawdz("edytor sprawdzany PRZED polem tekstowym", i_edytor < i_area,
        (i_edytor, i_area))
sprawdz("tiptap najpierw", i_tiptap < i_edytor, (i_tiptap, i_edytor))
sprawdz("`textarea` zostaje jako ostatnia droga",
        "pole tekstowe" in CIALO)
sprawdz("wiadomo, ktora droga zadzialala",
        'wynik["skad_pole"]' in CIALO and 'wynik["skad_przycisk"]' in CIALO)

print()
print("=== 5. PORAZKA ZOSTAWIA UKLAD STRONY DO OBEJRZENIA ===")
# Bez tego kazda nastepna naprawa znowu bylaby zgadywaniem. Ten plik powstal
# WYLACZNIE dlatego, ze zrzut dalo sie przeczytac.
sprawdz("brak przycisku zapisuje zrzut", "dom-odpowiedzi.html" in CIALO)
sprawdz("brak pola tez", "dom-pole-odpowiedzi.html" in CIALO)
sprawdz("i zapis nie moze wywalic przebiegu",
        CIALO.count("except Exception:                          # noqa: BLE001") >= 1
        or CIALO.count("except Exception:") >= 3)

print()
print("=== 6. NIC SIE NIE WYSYLA W TRYBIE SPRAWDZENIA ===")
sprawdz("wysylka nadal za `naprawde_wyslac`",
        "naprawde_wyslac(wyslij" in CIALO)
# PRZED PIERWSZYM WEJSCIEM NA STRONE, nie „w pierwszych 400 znakach": ten
# licznik mierzyl dlugosc docstringu, a nie kolejnosc kodu.
i_w = CIALO.index("naprawde_wyslac(wyslij")
i_goto = CIALO.index("page.goto(")
sprawdz("i stoi przed pierwszym wejsciem na strone", i_w < i_goto,
        (i_w, i_goto))

print()
print("=== POLE ODPOWIEDZI: CZEKAMY, AZ SIE ZAMONTUJE ===")
# ZMIERZONE NA PRODUKCJI 10 wrzesnia 2026, odpowiedz pod naszym artykulem:
#     przycisk odpowiedzi znaleziony przy komentarzu 'Chaos Engine'
#     BLAD: TimeoutError: Locator.click ... waiting for locator("textarea").first
# Trzy drogi do pola sprawdzaly sie w JEDNYM obrocie, tuz po klinieciu.
# Substack montuje edytor tiptap asynchronicznie, wiec zadna jeszcze nie
# istniala i szukanie spadalo na `textarea`, ktorej tam nie ma wcale.
# Tego samego dnia rano ta sama funkcja znalazla tiptap bez trudu — to wyscig,
# nie brak drogi.
import ast as _ast
_ZR = io.open("agent-v2/browser.py", encoding="utf-8").read()
_C = ""
for _w in _ast.walk(_ast.parse(_ZR)):
    if isinstance(_w, _ast.FunctionDef) and _w.name == "wystaw_odpowiedz_pod_artykulem":
        _C = _ast.get_source_segment(_ZR, _w) or ""
sprawdz("szukanie pola ponawia sie", "for podejscie in range(" in _C)
sprawdz("z przerwa miedzy podejsciami",
        "page.wait_for_timeout(1500)" in _C)
sprawdz("kolejnosc drog bez zmian",
        _C.find("edytor tiptap") < _C.find("edytor contenteditable") < _C.find("pole tekstowe"))
sprawdz("ostatnia deska nadal na koncu", "ostatnia deska" in _C)
sprawdz("i mowi, gdy pole pojawilo sie z opoznieniem",
        "pole odpowiedzi pojawilo sie po" in _C)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
