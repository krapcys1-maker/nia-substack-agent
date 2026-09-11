# -*- coding: utf-8 -*-
"""Wykrywanie AI naprawde zostaje wylaczone, a nie tylko klikniete w prozne.

## Co bylo nie tak

Ustawienie `wylacz_wykrywanie_ai` bylo wlaczone od dawna, a kod szukal na
stronie ustawien publikacji przyciskow o napisach „Wyłącz wykrywanie AI" oraz
„Turn off AI detection".

Substack pisze na tym przycisku **„Disable AI detection"** — widac to na
zrzucie strony ustawien z 11 wrzesnia 2026, sekcja „Text Analysis", tuz pod
„Scan for AI text". Zaden z dwoch szukanych napisow nie pasowal, wiec petla
konczyla sie bez klikniecia I BEZ SLOWA W LOGU.

Zmierzone na artykule opublikowanym tego dnia: w calym logu publikacji fraza
„wykrywanie AI" nie pada ani razu.

## Dowod, ze zadzialalo

Po klinieciu ten sam przycisk zmienia napis na „Re-enable AI detection" — tez
ze zrzutu wlasciciela. Funkcja to sprawdza, zamiast ufac wlasnemu klinieciu.
Ten sam napis chroni przed wlaczeniem wykrywania Z POWROTEM przy ponownym
wejsciu na te strone.

BEZ PYTESTA, bez sieci, bez przegladarki. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_wykrywanie_ai_naprawde_wylaczone.py
"""
import ast
import io
import sys

sys.path.insert(0, "agent-v2")
import browser          # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


class Przycisk:
    def __init__(self, strona, nazwa, widoczny=True):
        self.strona, self.nazwa, self.widoczny = strona, nazwa, widoczny

    @property
    def first(self):
        return self

    def count(self):
        return 1 if self.nazwa in self.strona.napisy else 0

    def is_visible(self):
        return self.widoczny and self.nazwa in self.strona.napisy

    def click(self, **k):
        self.strona.kliknieto.append(self.nazwa)
        # Substack podmienia napis na przeciwny — dokladnie to widac
        # na dwoch zrzutach wlasciciela.
        if self.nazwa == "Disable AI detection":
            self.strona.napisy.discard("Disable AI detection")
            self.strona.napisy.add("Re-enable AI detection")

    def evaluate(self, *a, **k):
        self.click()


class Strona:
    def __init__(self, napisy):
        self.napisy = set(napisy)
        self.kliknieto = []

    def get_by_role(self, rola, name=None, **k):
        return Przycisk(self, name)

    def wait_for_timeout(self, ms):
        pass


print("=== 1. PRZYCISK Z PRAWDZIWYM NAPISEM ZOSTAJE KLIKNIETY ===")
s = Strona({"Scan for AI text", "Disable AI detection", "Send to everyone now"})
wynik = browser.wylacz_wykrywanie_ai(s)
sprawdz("kliknieto wlasciwy przycisk",
        s.kliknieto == ["Disable AI detection"], s.kliknieto)
sprawdz("i potwierdzono zmiana napisu", wynik == "wylaczone", wynik)
sprawdz("na stronie stoi teraz Re-enable",
        "Re-enable AI detection" in s.napisy)

print()
print("=== 2. STARE NAPISY NADAL DZIALAJA ===")
# Substack zmienia slownictwo; poprzednie warianty maja zostac.
for napis in ("Wyłącz wykrywanie AI", "Turn off AI detection"):
    s2 = Strona({napis})
    browser.wylacz_wykrywanie_ai(s2)
    sprawdz("obsluzony napis %r" % napis, s2.kliknieto == [napis], s2.kliknieto)

print()
print("=== 3. JUZ WYLACZONE — NIE WLACZAMY Z POWROTEM ===")
# To jest ta wada, ktora latwo wprowadzic „naprawiajac" napisy: przycisk
# w stanie `Re-enable` klikniety drugi raz WLACZA wykrywanie.
s3 = Strona({"Scan for AI text", "Re-enable AI detection"})
wynik3 = browser.wylacz_wykrywanie_ai(s3)
sprawdz("nic nie kliknieto", s3.kliknieto == [], s3.kliknieto)
sprawdz("i powiedziano, ze juz jest wylaczone",
        wynik3 == "juz_wylaczone", wynik3)

print()
print("=== 4. BRAK PRZYCISKU MOWI O SOBIE ===")
# Cisza byla cala przyczyna tej wpadki: kod nie klikal i nie skarzyl sie.
s4 = Strona({"Scan for AI text"})
wynik4 = browser.wylacz_wykrywanie_ai(s4)
sprawdz("nic nie kliknieto", s4.kliknieto == [])
sprawdz("wynik nazywa problem", wynik4 == "nie_znalazlem", wynik4)

print()
print("=== 5. KLIKNIETE BEZ ZMIANY NAPISU TO TEZ WYNIK ===")
class StronaUparta(Strona):
    def get_by_role(self, rola, name=None, **k):
        p = Przycisk(self, name)
        if name == "Disable AI detection":
            p.click = lambda **k: self.kliknieto.append(name)   # napis zostaje
        return p


s5 = StronaUparta({"Disable AI detection"})
wynik5 = browser.wylacz_wykrywanie_ai(s5)
sprawdz("klikniecie odnotowane", s5.kliknieto == ["Disable AI detection"])
sprawdz("ale nie udajemy sukcesu",
        wynik5 == "klikniete_bez_potwierdzenia", wynik5)

print()
print("=== 6. WPIETE W PUBLIKACJE ARTYKULU ===")
ZRODLO = io.open("agent-v2/browser.py", encoding="utf-8").read()
CIALO = ""
for w in ast.walk(ast.parse(ZRODLO)):
    if isinstance(w, ast.FunctionDef) and w.name == "wystaw_artykul":
        CIALO = ast.get_source_segment(ZRODLO, w) or ""
sprawdz("publikacja wola te funkcje", "wylacz_wykrywanie_ai(page)" in CIALO)
sprawdz("tylko gdy ustawienie na to pozwala",
        "config.WYLACZ_WYKRYWANIE_AI" in CIALO)
sprawdz("wynik trafia do dziennika", 'wynik["wykrywanie_ai"]' in CIALO)
# Kolejnosc: NAJPIERW wylaczenie, POTEM przycisk publikacji. Odwrotnie
# klikaloby sie w ustawienie juz opublikowanego tekstu.
i_ai = CIALO.find("wylacz_wykrywanie_ai(page)")
i_pub = CIALO.find("Send to everyone now")
sprawdz("wylaczenie PRZED publikacja", 0 <= i_ai < i_pub,
        "%d / %d" % (i_ai, i_pub))
sprawdz("klikniecie idzie przez helper od zaslon",
        "klik_mimo_zaslony(k, \"wylaczenie wykrywania AI\"" in ZRODLO)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
