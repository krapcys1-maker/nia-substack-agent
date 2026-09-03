# -*- coding: utf-8 -*-
"""Premiera modelu ma byc widoczna W DNIU PREMIERY — i tylko wtedy.

DLACZEGO TO POWSTALO. 2 wrzesnia 2026 wyszedl Fable 5.1. Sprawdzone na zywym
korpusie: wykrywacz oddal jedno wydarzenie i byla to premiera ACME 5.3 sprzed
kilkunastu dni. O Fable 5.1 mowily tego dnia DWA kanaly (Kanal Newsowy, Kanal
Produktowy), a wspolne mialy dokladnie dwa slowa: „fable" i „5.1". Regula fali
wymaga TRZECH kanalow, wiec milczala; reszta tytulu to szum, u kazdego inny.

CO TEN PLIK MIERZY. Wylacznie ZACHOWANIE funkcji: podaje sie korpus, oglada
liste wydarzen. Zadnego czytania kodu zrodlowego, zadnej atrapy modelu, zero
sieci i zero pieniedzy — bo caly sens tego sygnalu polega na tym, ze liczy go
KOD, a nie model.

KONTRDOWOD JEST WAZNIEJSZY OD DOWODU. Wykrywacz, ktory strzela zawsze, przejdzie
kazdy test „czy wykrywa". Dlatego wiekszosc przypadkow ponizej to przypadki
NEGATYWNE: jeden kanal, numer juz znany, dwa kanaly bez numeru, rzecz sprzed
dziesieciu dni, korpus pusty, korpus samych roznych tematow.
"""
import sys
from datetime import datetime, timedelta, timezone

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


def dzien(wstecz=0):
    return (datetime.now(timezone.utc)
            - timedelta(days=wstecz)).strftime("%Y-%m-%d")


def poz(temat, kanal, wstecz=0):
    return {"temat": temat, "kanal": kanal, "data": dzien(wstecz)}


def etykiety(wyd):
    return [set(w["o_czym"]) for w in wyd]


def jest(wyd, *slowa):
    return any(set(slowa) <= e for e in etykiety(wyd))


# CZTERY TYTULY O FABLE Z TRZECH KANALOW. Kanal Newsowy mowi dwa razy — to celowe,
# bo prog dotyczy KANALOW, nie filmow.
FABLE_3_KANALY = [
    poz("Fable 5.1 just smoked ASTRA", "Kanal Newsowy"),
    poz("Anthropic went (Mythos/Fable 5.1)", "Kanal Produktowy"),
    poz("Fable 5.1 and the price of a single token", "Kanal Wyjasniajacy"),
    poz("Why Fable 5.1 broke my whole evaluation harness", "Kanal Newsowy"),
]

print("=== 1. CZTERY TYTULY O FABLE Z TRZECH KANALOW — WYKRYWA ===")
wyd = korpus_kanalow.wielkie_wydarzenia(FABLE_3_KANALY)
sprawdz("cos wykryte", bool(wyd), wyd)
sprawdz("i jest to Fable 5.1, nie cokolwiek", jest(wyd, "fable", "5.1"),
        etykiety(wyd))
sprawdz("etykieta niesie NAZWE, nie sam numer — inaczej dwie rozne premiery"
        " o tym samym numerze zlepia sie w jedno zdarzenie",
        all("fable" in w["o_czym"] for w in wyd if "5.1" in w["o_czym"]),
        etykiety(wyd))
sprawdz("liczba kanalow to liczba KANALOW, nie filmow",
        all(w["kanalow"] == 3 for w in wyd), wyd)

print()
print("=== 2. TE SAME CZTERY TYTULY, ALE Z JEDNEGO KANALU — NIE WYKRYWA ===")
jeden = [{**p, "kanal": "Kanal Newsowy"} for p in FABLE_3_KANALY]
wyd = korpus_kanalow.wielkie_wydarzenia(jeden)
sprawdz("pusta lista", wyd == [], wyd)

print()
print("=== 3. TYTULY SPRZED DZIESIECIU DNI — NIE WYKRYWA ===")
stare = [{**p, "data": dzien(10)} for p in FABLE_3_KANALY]
wyd = korpus_kanalow.wielkie_wydarzenia(stare)
sprawdz("pusta lista", wyd == [], wyd)

print()
print("=== 4. KORPUS PUSTY — PUSTA LISTA, BEZ WYJATKU ===")
for opis, wejscie in [("[]", []), ("None", None),
                      ("pozycje bez daty", [{"temat": "Fable 5.1 is out",
                                             "kanal": "a"}]),
                      ("pozycje bez kanalu", [{"temat": "Fable 5.1 is out",
                                               "data": dzien()}]),
                      ("smiec", [{}, {"temat": None, "kanal": "a", "data": dzien()}])]:
    try:
        wynik = korpus_kanalow.wielkie_wydarzenia(wejscie)
        sprawdz("%s -> pusta lista, bez wyjatku" % opis, wynik == [], wynik)
    except Exception as exc:
        sprawdz("%s -> pusta lista, bez wyjatku" % opis, False,
                "%s: %s" % (type(exc).__name__, exc))

print()
print("=== 5. KORPUS SAMYCH ROZNYCH TEMATOW — PUSTA LISTA ===")
rozne = [
    poz("A chip grown from living brain cells learned to fly", "Kanal Analityczny"),
    poz("Export controls are quietly reshaping compute", "Kanal Rozmow"),
    poz("Why local speech synthesis suddenly got usable", "Kanal Praktyczny"),
    poz("The dashboard that writes itself from one prompt", "Kanal Przegladowy"),
    poz("Agents negotiated their own protocol overnight", "Kanal Naukowy"),
    poz("What a court filing reveals about training data", "Kanal Wyjasniajacy"),
]
wyd = korpus_kanalow.wielkie_wydarzenia(rozne)
sprawdz("pusta lista", wyd == [], wyd)

print()
print("=== 6. PRAWDZIWY KSZTALT PREMIERY: DWA KANALY, WSPOLNE TYLKO")
print("       NAZWA I NOWY NUMER — WYKRYWA ===")
# To jest przypadek, ktory 2 wrzesnia 2026 przeszedl bokiem: dwa kanaly,
# a wspolne slowa to dokladnie {fable, 5.1}. Regula fali wymaga trzech kanalow.
dwa = [
    poz("Fable 5.1 just smoked ASTRA", "Kanal Newsowy"),
    poz("Anthropic went (Mythos/Fable 5.1)", "Kanal Produktowy"),
]
wyd = korpus_kanalow.wielkie_wydarzenia(dwa)
sprawdz("wykryte", jest(wyd, "fable", "5.1"), etykiety(wyd))
sprawdz("oznaczone jako premiera", any(w.get("premiera") for w in wyd), wyd)

print()
print("=== 7. TEN SAM KSZTALT, ALE NUMER JUZ ZNANY — NIE WYKRYWA ===")
# Numer wersji, o ktorym korpus mowil PRZED oknem, nie jest premiera. Bez tego
# warunku kazda druga wzmianka o starym modelu przestawialaby kolejke.
znany = dwa + [
    poz("Fable 5.1 hands-on, three weeks later", "Kanal Techniczny", 20),
    poz("Everything we know about Fable 5.1 so far", "Kanal Wyjasniajacy", 25),
]
wyd = korpus_kanalow.wielkie_wydarzenia(znany)
sprawdz("pusta lista", wyd == [], wyd)

print()
print("=== 8. DWA KANALY BEZ NUMERU WERSJI — NADAL NIE WYDARZENIE ===")
# Doktryna zostaje: „jeden kanal krzyczacy to naglowek, nie wydarzenie", a dwa
# kanaly o wspolnym motywie to wciaz za malo. Wyjatek dotyczy WYLACZNIE nowego
# numeru wydania, bo tylko on jest sprawdzalny poza naglowkiem.
bez_numeru = [
    poz("Titan release changes inference pricing", "Kanal Newsowy"),
    poz("Inference pricing after the Titan release", "Kanal Produktowy"),
]
sprawdz("pusta lista", korpus_kanalow.wielkie_wydarzenia(bez_numeru) == [],
        korpus_kanalow.wielkie_wydarzenia(bez_numeru))

print()
print("=== 9. JEDEN KANAL Z NOWYM NUMEREM — NIE WYKRYWA ===")
sprawdz("pusta lista", korpus_kanalow.wielkie_wydarzenia(dwa[:1]) == [],
        korpus_kanalow.wielkie_wydarzenia(dwa[:1]))

print()
print("=== 10. ROK TO NIE NUMER WERSJI ===")
rok = [
    poz("AGI 2026 is the only thing anyone talks about", "Kanal Newsowy"),
    poz("Why AGI 2026 predictions keep sliding", "Kanal Newsowy"),
]
sprawdz("rok 2026 u dwoch kanalow to nie premiera",
        korpus_kanalow.wielkie_wydarzenia(rok) == [],
        korpus_kanalow.wielkie_wydarzenia(rok))

print()
print("=== 11. TRZY KANALY, ALE TYLKO JEDEN SWIEZY — NIE WYKRYWA ===")
# Regresja na blad, ktory przepuscil premiere sprzed siedemnastu dni: swiezosc
# byla liczona przez NAJNOWSZY film grupy, wiec trzy kanaly rozrzucone na trzy
# miesiace przechodzily dzieki jednemu dzisiejszemu filmowi.
kulawa = [
    poz("Titan seven release changes inference pricing", "Kanal Newsowy", 0),
    poz("Titan seven release changes inference pricing", "Kanal Zbiorczy", 12),
    poz("Titan seven release changes inference pricing", "Kanal Przegladowy", 30),
]
sprawdz("pusta lista", korpus_kanalow.wielkie_wydarzenia(kulawa) == [],
        korpus_kanalow.wielkie_wydarzenia(kulawa))
sprawdz("ale trzy SWIEZE kanaly to nadal wydarzenie",
        bool(korpus_kanalow.wielkie_wydarzenia(
            [{**p, "data": dzien(1)} for p in kulawa])))

print()
print("=== 12. WYKRYWACZ NICZEGO NIE BLOKUJE ===")
# Cokolwiek wejdzie, wychodzi lista — funkcja nie ma prawa zatrzymac przebiegu.
for opis, wejscie in [("normalny korpus", FABLE_3_KANALY),
                      ("cichy dzien", rozne), ("pustka", [])]:
    wynik = korpus_kanalow.wielkie_wydarzenia(wejscie)
    sprawdz("%s -> lista, kazdy wpis ma komplet pol" % opis,
            isinstance(wynik, list) and all(
                {"o_czym", "kanalow", "kanaly", "tytuly", "data", "premiera"}
                <= set(w) for w in wynik), wynik)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
