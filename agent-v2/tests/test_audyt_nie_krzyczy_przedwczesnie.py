# -*- coding: utf-8 -*-
"""Audyt ma zglaszac POMINIECIE, a nie „jeszcze nie zdazylismy zmierzyc".

## Po co ten plik istnieje

Etap 4 audytu (STATYSTYKI) zglaszal BLAD, gdy jakis rodzaj tresci mial zero
pomiarow. 8 wrzesnia 2026 krzyczal tak na komentarzach — i wady nie bylo:

  - pierwsze UDANE komentarze wyszly w przebiegu nocnym (01:40-03:00),
  - statystyki zbiera sie na POCZATKU przebiegu, nastepny byl za siedem godzin,
  - `browser.nasze_pozycje_do_pomiaru` wolane bez sieci oddawalo je poprawnie,
    co do numeru.

Zero bylo wiec stanem normalnym, a nie usterka. To ta sama klasa wady, ktora
ten plik audytu opisuje przy sobie samym dwa razy: „falszywy alarm uczy
ignorowac alarmy". Etap, ktorego jedynym zadaniem jest zauwazyc dzien, w
ktorym NAPRAWDE przestaniemy mierzyc, traci wartosc, gdy swieci na czerwono
po kazdej publikacji miedzy przebiegami.

## Regula, ktorej pilnuje ten test

Wada jest zdefiniowana CZASEM, nie zerem: pozycja przetrwala ZAKONCZONY pomiar
i nadal jej nie ma. Wystawiona po ostatnim pomiarze czeka w kolejce i jest OK.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_audyt_nie_krzyczy_przedwczesnie.py
"""
import sys

sys.path.insert(0, "agent-v2")
import audyt_systemu  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


def stan(wynik, rodzaj):
    return next((s for r, s, _ in wynik if r == rodzaj), None)


def opis(wynik, rodzaj):
    return next((o for r, _, o in wynik if r == rodzaj), "")


POMIAR = [{"rodzaj": "notka", "id": "1", "kiedy": "2026-09-08T05:00:00"}]

print("=== 1. WYSTAWIONE PO OSTATNIM POMIARZE — CZEKA, NIE JEST WADA ===")
w = audyt_systemu.ocen_pomiary(POMIAR, [
    {"rodzaj": "notka", "udane": True, "nasz_id": "1", "kiedy": "2026-09-08T04:00:00"},
    {"rodzaj": "komentarz", "udane": True, "nasz_id": "9", "kiedy": "2026-09-08T06:00:00"},
])
sprawdz("komentarz z przyszlosci pomiaru to OK", stan(w, "komentarz") == "OK",
        opis(w, "komentarz"))
sprawdz("i opis mowi, ze czeka w kolejce", "w kolejce" in opis(w, "komentarz"),
        opis(w, "komentarz"))
sprawdz("zmierzona notka nadal OK", stan(w, "notka") == "OK", opis(w, "notka"))

print()
print("=== 2. PRZETRWALO ZAKONCZONY POMIAR — TO JEST WADA ===")
w = audyt_systemu.ocen_pomiary(POMIAR, [
    {"rodzaj": "notka", "udane": True, "nasz_id": "1", "kiedy": "2026-09-08T04:00:00"},
    {"rodzaj": "komentarz", "udane": True, "nasz_id": "8", "kiedy": "2026-09-08T03:00:00"},
])
sprawdz("komentarz starszy niz pomiar to BLAD", stan(w, "komentarz") == "BLAD",
        opis(w, "komentarz"))
sprawdz("i opis nazywa go pominietym", "pominiet" in opis(w, "komentarz"),
        opis(w, "komentarz"))

print()
print("=== 3. NIC NIE WYSZLO — TEZ NIE JEST WADA ===")
w = audyt_systemu.ocen_pomiary([], [])
sprawdz("wszystkie rodzaje OK", all(s == "OK" for _, s, _ in w),
        str(w))
sprawdz("opis mowi wprost, ze nie ma czego mierzyc",
        "jeszcze nie wyszlo" in opis(w, "komentarz"), opis(w, "komentarz"))

print()
print("=== 4. RESTACK LICZY SIE JAK NOTKA ===")
# Substack nadaje restackowi wlasny numer notki i tak samo klasyfikuje go
# `browser.nasze_pozycje_do_pomiaru`. Gdyby audyt liczyl go osobno, restack
# bylby wiecznie „niezmierzony", bo w pliku statystyk takiego rodzaju nie ma.
w = audyt_systemu.ocen_pomiary(
    [{"rodzaj": "notka", "id": "7", "kiedy": "2026-09-08T05:00:00"}],
    [{"rodzaj": "restack", "udane": True, "nasz_id": "7", "kiedy": "2026-09-08T04:00:00"}])
sprawdz("restack zmierzony jako notka nie jest pominieciem",
        stan(w, "notka") == "OK", opis(w, "notka"))

print()
print("=== 5. NIEUDANE NIE LICZA SIE WCALE ===")
# Komentarz, ktory nie wyszedl, nie ma numeru i nie ma czego mierzyc.
w = audyt_systemu.ocen_pomiary(POMIAR, [
    {"rodzaj": "komentarz", "udane": False, "nasz_id": None,
     "kiedy": "2026-09-08T03:00:00"}])
sprawdz("nieudany komentarz nie robi z tego bledu", stan(w, "komentarz") == "OK",
        opis(w, "komentarz"))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
