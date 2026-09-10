# -*- coding: utf-8 -*-
"""Darmowe pominiecie nie zjada okna subskrypcji.

## Pomiar, ktory to wywolal

Raport normy, produkcja, 7-10 wrzesnia 2026:

                 notka  komentarz  restack  subskrypcja  obserwacja
    % NORMY       100%       56%      42%           0%         80%
    nieudane        -          7        1            10          -

Subskrypcje stoja na ZERZE trzy doby z rzedu przy normie czterech dziennie.
Blok chodzi, konczy sie bez ani jednej proby i zostawia dziesiec „nieudanych".

## Przyczyna

Sufit odbiorcow to 1000. Sprawdzone na zywo na kandydatach, ktorych pula
podawala tego dnia:

    @guillermoflor        134 438 obserwujacych
    @opinionai            131 684
    @sarahfay              90 381
    @shrivu                 3 758
    @on, @2hourblogger, @departmentofproduct, @agentledco — 404, to publikacje,
                                                            nie profile ludzi

Petla ogladala `kandydaci[:4 + 4]`, czyli DOKLADNIE osiem pozycji, i wszystkie
osiem odpadalo. Kod byl przy tym poprawny co do zasady: pominiecie za rozmiar
jest darmowe — odczyt publicznego JSON-a, bez przegladarki, bez przerwy rytmu
i bez zuzycia slotu, tak mowi komentarz przy samym sprawdzeniu. Okno mierzylo
wiec cos, co nic nie kosztuje, i zamykalo blok przed pierwszym kandydatem we
wlasciwym rozmiarze.

## Czego ten test NIE twierdzi

Nie twierdzi, ze pula jest teraz dobra. Pula pelna kont stokrotnie za duzych to
osobna usterka i naprawia sie ja gdzie indziej. Ten test pilnuje tylko tego,
zeby blok doszedl do kandydata, ktory sie miesci, jesli taki w puli lezy.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_subskrypcje_widza_dalej_niz_osiem.py
"""
import ast
import io
import sys

sys.path.insert(0, "agent-v2")
import config          # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


ZRODLO = io.open("agent-v2/run.py", encoding="utf-8").read()
CIALO = ""
for w in ast.walk(ast.parse(ZRODLO)):
    if isinstance(w, ast.FunctionDef) and w.name == "subskrybuj":
        CIALO = ast.get_source_segment(ZRODLO, w) or ""

print("=== 1. OKNO NIE JEST JUZ PLASTREM OSMIU ===")
sprawdz("blok subskrypcji znaleziony", bool(CIALO))
# PO DRZEWIE SKLADNI, NIE PO NAPISIE. Kod NADAL zawiera te fraze — jako cytat
# w komentarzu, ktory tlumaczy, czemu jej nie ma. Probka szukajaca napisu
# oblewalaby na wyjasnieniu wlasnej poprawki; ten projekt ma juz cztery takie
# wpadki na koncie.
KRAJANIE = [w for w in ast.walk(ast.parse(CIALO))
            if isinstance(w, ast.Subscript)
            and isinstance(w.value, ast.Name) and w.value.id == "kandydaci"
            and isinstance(w.slice, ast.Slice)]
sprawdz("stary plaster zniknal Z KODU", not KRAJANIE, len(KRAJANIE))
sprawdz("ale zostal w komentarzu jako slad",
        "ZAPAS_NA_ODPADY]" in CIALO)
sprawdz("petla idzie po calej puli", "for host in kandydaci:" in CIALO)
sprawdz("z gorna granica ogladania", "limit_ogladania" in CIALO)
sprawdz("granica pochodzi z ustawien",
        "SUBSKRYPCJE_MAKS_OGLADANYCH" in CIALO)
# GRANICA NIGDY PONIZEJ STAREGO OKNA. Gdyby ktos ustawil ja na 2, blok
# zrobilby MNIEJ niz przed poprawka — dlatego bierzemy wieksza z dwoch liczb.
i_lim = CIALO.find("limit_ogladania = ")
sprawdz("i nigdy nie jest mniejsza niz stare okno",
        i_lim >= 0 and "max(" in CIALO[i_lim:i_lim + 60],
        CIALO[i_lim:i_lim + 60] if i_lim >= 0 else "brak")

print()
print("=== 2. GRANICA JEST ROZSADNA ===")
sprawdz("ustawienie istnieje", hasattr(config, "SUBSKRYPCJE_MAKS_OGLADANYCH"))
ile = int(getattr(config, "SUBSKRYPCJE_MAKS_OGLADANYCH", 0))
sprawdz("wieksza niz osiem, ktore zawiodlo", ile > 8, ile)
sprawdz("i nie oznacza obchodzenia calej puli", ile <= 200, ile)

print()
print("=== 3. LICZYMY OBEJRZANYCH, NIE PROBY ===")
# To jest cala roznica: proba kosztuje wejscie na cudzy profil i przerwe
# rytmu, obejrzenie kosztuje odczyt publicznej liczby.
sprawdz("licznik obejrzanych istnieje", "obejrzani += 1" in CIALO)
sprawdz("i przerywa po granicy", "obejrzani >= limit_ogladania" in CIALO)
sprawdz("proby nadal maja wlasny licznik", "proby >= na_teraz" in CIALO)
sprawdz("pominiecie za rozmiar nadal nie jest proba",
        "bez zuzycia proby" in CIALO)

print()
print("=== 4. ZERO Z POWODU MOWI, ZE TO ROZMIAR ===")
# Bez tego dzien wyglada jak brak okazji, a byl to sufit.
sprawdz("liczymy pominietych za rozmiar", "za_duzi += 1" in CIALO)
sprawdz("i mowimy o tym na koniec",
        "przekraczalo sufit" in CIALO)
sprawdz("z nazwaniem sufitu po imieniu",
        "SUBSKRYPCJE_MAX_ODBIORCOW" in CIALO)
sprawdz("i z osobnym zdaniem, gdy nie bylo ani jednej proby",
        "pula nie zawiera kont w naszym rozmiarze" in CIALO)

print()
print("=== 5. RESZTA ZABEZPIECZEN ZOSTAJE ===")
# Kontrdowod: latwo „naprawic" okno tak, ze przy okazji zgubi sie zegar
# przebiegu albo pamiec juz zasubskrybowanych.
sprawdz("zegar przebiegu nadal pytany", 'zostal_czas("subskrypcje")' in CIALO)
sprawdz("pamiec zasubskrybowanych nadal odsiewa",
        "uchwyt in zamkniete" in CIALO)
sprawdz("rytm nadal przed proba", 'rytm("komentarz", "subskrypcje"' in CIALO)
sprawdz("zapas na odpady nadal istnieje", "ZAPAS_NA_ODPADY" in CIALO)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
