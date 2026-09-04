# -*- coding: utf-8 -*-
"""Rekomendacje: wybieramy SAMI, nie z propozycji Substacka.

CO POKAZALO ROZPOZNANIE NA ZYWO 30 SIERPNIA 2026. Ekran
`/publish/recommendations` podsuwa dziesiec publikacji „ktore moze Pan/Pani
chciec polecic". Z tych dziesieciu JEDNA dotykala AI:

    Publikacja Budowlana, Publikacja Miejska, mandates, Publikacja Wlasnej Domeny,
    Publikacja 1, It's Publikacja Srodowiskowa with Klara Jedenasta,
    Publikacja Umyslowa on Money, Publikacja Raportowa, Publikacja Kulinarna,
    People of Interest

Substack liczy je z historii czytania konta, a ta pochodzi sprzed
przestawienia na AI — ta sama skaza, co w banku tematow i w dziewieciu
promptach, tylko po stronie Substacka, gdzie nie da sie jej wyczyscic inaczej
niz czytajac nowe rzeczy. Publikacja polecajaca newsletter z zupelnie innej
dziedziny to
dokladnie ten „wyglad bota", ktorego wlasciciel nie chce.

DLACZEGO NIE „PO PROSTU NIE KLIKAJMY PROPOZYCJI". Bo okno „Dodaj
rekomendacje" ma pole „Wyszukaj osobe lub publikacje...", wiec mozemy wskazac
kogo chcemy. Pierwsze rozpoznanie tego NIE ZOBACZYLO — zajrzalo po 3,5 sekundy
i zdazylo znalezc tylko pole opisu. Wniosek „nie da sie wybrac samemu" byl
falszywy i utrzymal sie do momentu, w ktorym spojrzalem drugi raz z dluzszym
czekaniem. Stad `wait_for_timeout(6000)` w kodzie i ta uwaga tutaj.

Rekomendacja jest PUBLICZNA I TRWALA: stawia nasza nazwe obok cudzej na
stronie powitalnej i w pasku bocznym, a Substack pokazuje ja nowym
subskrybentom przy zapisie. Dlatego domyslnie NIE zatwierdza.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo.
"""
import pathlib
import sys

sys.path.insert(0, "agent-v2")
import browser  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


zrodlo = pathlib.Path("agent-v2/browser.py").read_text(encoding="utf-8")
i = zrodlo.index("def polec_publikacje(")
blok = zrodlo[i:zrodlo.index("\ndef ", i + 10)]

print("=== 1. DOMYSLNIE NIE ZATWIERDZA ===")
# Ta sama ostroznosc, co przy notce: „notki nie da sie cofnac w oczach tych,
# ktorzy ja zobaczyli". Rekomendacja zostaje w ustawieniach na stale.
sprawdz("sygnatura ma wyslij=False",
        "def polec_publikacje(fraza: str, powod: str,\n"
        "                     wyslij: bool = False)" in zrodlo)
sprawdz("przechodzi przez wspolne sito DRY_RUN",
        'naprawde_wyslac(wyslij, "rekomendacja")' in blok)
sprawdz("bez zgody konczy przed zatwierdzeniem",
        "if not wyslij:" in blok
        and blok.index("if not wyslij:") < blok.index("zatwierdz.click"))

print()
print("=== 2. SZUKAMY SAMI, NIE BIERZEMY Z PROPOZYCJI ===")
sprawdz("uzywa pola wyszukiwania", "get_by_role(\"combobox\")" in blok)
sprawdz("wpisuje przekazana fraze", "szukajka.fill(fraza" in blok)
sprawdz("nie klika przycisków 'Poleć' z listy propozycji",
        "Poleć" not in blok)

print()
print("=== 3. NIE KLIKA 'W ZASTEPSTWIE' ===")
# Blad, przez ktory agent subskrybowal zamiast obserwowac: jedna funkcja
# probowala kolejno kilku napisow i brala pierwszy znaleziony.
sprawdz("trafienie musi zawierac szukana fraze",
        "re.escape(fraza" in blok)
sprawdz("gdy nie znajdzie — melduje blad zamiast klikac cokolwiek",
        "wyszukiwarka nie znalazla" in blok)

print()
print("=== 4. OPIS JEST WYMAGANY PRZEZ SUBSTACKA ===")
# Okno oznacza go „Wymagane". Polecenie bez powodu to sam podpis.
sprawdz("wypelnia pole opisu", "opis.fill(powod" in blok)
sprawdz("i szuka go po podpowiedzi, nie po pozycji",
        "get_by_placeholder" in blok)

print()
print("=== 5. SPRAWDZA SKUTEK, NIE BRAK WYJATKU ===")
# Lekcja z pamieci platnych hostow: oslona `try` zamienila blad w wypisane
# ostrzezenie i funkcja po cichu nie robila nic. Tu porownujemy liste PRZED
# i PO — jedyny dowod, ze cokolwiek przybylo.
sprawdz("czyta liste przed", "przed = {" in blok)
sprawdz("i po", "po = {" in blok)
sprawdz("wynik stoi na roznicy liczb", "len(po) > len(przed)" in blok)
sprawdz("a nie na tym, ze klikniecie przeszlo",
        'wynik["zrobione"] = True' not in blok)

print()
print("=== 6. ZAPISUJE DO DZIENNIKA ===")
sprawdz("udana rekomendacja zostawia slad",
        'dopisz_wynik("rekomendacja"' in blok)

print()
print("=== 7. OKNO POTRZEBUJE CZASU — TO JEST ZMIERZONE ===")
# 3,5 s to za malo: pierwsze rozpoznanie nie zobaczylo wyszukiwarki i dalo
# falszywy wniosek, ze nie da sie wybrac samemu.
sprawdz("czeka co najmniej 6 s na okno", "wait_for_timeout(6000)" in blok)
sprawdz("i mowi w kodzie, czemu akurat tyle",
        "OKNO POTRZEBUJE CZASU" in blok)

print()
print("=== 8. ODCZYT LISTY DZIALA OSOBNO ===")
# Zeby dalo sie zapytac „kogo polecamy" bez otwierania okna dodawania.
sprawdz("jest `kogo_polecamy`", "def kogo_polecamy(" in zrodlo)
sprawdz("czyta z API, nie z pamieci",
        "recommendations/from/" in zrodlo)
sprawdz("i nie zaklada, ze numer publikacji jest wpisany na sztywno",
        "9973418" not in zrodlo)

print()
print("=== 9. SKAZA PROPOZYCJI JEST OPISANA W KODZIE ===")
# Zeby ktos, kto tu zajrzy za miesiac, nie „uproscil" tego do klikania
# gotowej listy.
sprawdz("kod wymienia, co Substack podsuwal",
        "Publikacja Kulinarna" in blok and "Publikacja Budowlana" in blok)
sprawdz("i nazywa przyczyne",
        "historii czytania" in blok)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
