# -*- coding: utf-8 -*-
"""Przebieg artykulu bez `--wyslij` sprawdza droge na Substacka, nie tylko plik.

## Co bylo nie tak

Do 10 wrzesnia 2026 `artykul_z_puli.py` bez `--wyslij` konczyl na pliku .md
i NIE DOTYKAL przegladarki ani razu:

    >> bez --wyslij: artykul zostaje na dysku

Cala druga polowa drogi — zalozenie postu, wklejenie tresci, wgranie dwoch
obrazow, przycisk subskrypcji, odnalezienie przycisku publikacji — nie byla
wiec sprawdzana NIGDY. Pierwszy raz dowiadywalismy sie o niej dopiero
w prawdziwej publikacji, po oplaceniu researchu, pisania i dwoch obrazow
(zmierzone tego dnia: 1,15 USD za sam artykul 0056).

Wlasciciel nazwal to precyzyjnie: „przyjdzie do publikacji i sie nie
opublikuje".

## Ze to bylo o jedno wywolanie stad

Tego samego wieczoru, na gotowym pliku 0056:

    wklejona tresc: 1107 slow, 4 wezlow linkowych
    grafika w srodku: wgrana
    grafika: wgrana
    przycisk subskrypcji wstawiony
    przycisk publikacji: 'Send to everyone now'
    (nie wysylam — tryb sprawdzenia; szkic zapisany)
    szkic https://nia1503032.substack.com/publish/post/215158291

Szkic NIE JEST publikacja: nikt go nie widzi, nie idzie mail, nie ma go
w kanale. Za to po przebiegu wiadomo, czy tekst da sie wystawic.

BEZ PYTESTA, bez sieci, bez przegladarki. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_proba_artykulu_dochodzi_do_substacka.py
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


ZRODLO = io.open("agent-v2/artykul_z_puli.py", encoding="utf-8").read()
i = ZRODLO.find('if "--wyslij" not in sys.argv:')
OGON = ZRODLO[i:i + 2600] if i >= 0 else ""

print("=== 1. PROBA IDZIE DO SUBSTACKA ===")
sprawdz("bramka `--wyslij` istnieje", bool(OGON))
sprawdz("proba wola wystawienie artykulu",
        "_browser.wystaw_artykul(sciezka, wyslij=False)" in OGON)
sprawdz("i mowi, ze nic nie wychodzi w swiat",
        "nic nie wychodzi" in OGON)
sprawdz("podaje adres szkicu", '_w["szkic"]' in OGON)

print()
print("=== 2. PRZYCISK PUBLIKACJI JEST SPRAWDZANY ===")
# To jedyna czesc, ktorej sam szkic nie dowodzi, a od niej zalezy, czy
# prawdziwy przebieg cokolwiek wystawi.
sprawdz("pytamy o przycisk publikacji", '_w.get("przycisk_widoczny")' in OGON)
sprawdz("i mowimy wprost, co znaczy jego brak",
        "prawdziwy przebieg by nie wystawil" in OGON)

print()
print("=== 3. STARA DROGA ZOSTAJE POD WLASNA NAZWA ===")
# Praca bez zalogowanej sesji Substacka nadal musi byc mozliwa.
sprawdz("jest `--tylko-plik`", '"--tylko-plik" in sys.argv' in OGON)
sprawdz("i zostawia sam plik", "artykul zostaje na dysku" in OGON)

print()
print("=== 4. AWARIA SZKICU NIE KASUJE ARTYKULU ===")
# Plik jest juz napisany i oplacony. Nieudane zalozenie szkicu ma o tym
# powiedziec, a nie wywalic przebieg.
sprawdz("zakladanie szkicu jest oslonione", "except Exception as exc:" in OGON)
sprawdz("i mowi, gdzie lezy plik", "plik lezy w %s" in OGON)
sprawdz("przebieg konczy sie spokojnie", OGON.count("return 0") >= 2,
        OGON.count("return 0"))

print()
print("=== 5. PUBLIKACJA NADAL WYMAGA `--wyslij` ===")
# KONTRDOWOD: gdyby proba zaczela wysylac, ten test bylby najgorszym
# mozliwym testem — chwalilby dokladnie te wade, ktora ma pilnowac.
sprawdz("proba nigdy nie wola wysylki",
        "wystaw_artykul(sciezka, wyslij=True)" not in OGON)
DRZEWO = ast.parse(ZRODLO)
wysylki = [w for w in ast.walk(DRZEWO)
           if isinstance(w, ast.Call)
           and isinstance(w.func, ast.Attribute)
           and w.func.attr == "wystaw_artykul"
           and any(k.arg == "wyslij" and getattr(k.value, "value", None) is True
                   for k in w.keywords)]
sprawdz("wysylka artykulu istnieje dokladnie raz w calym pliku",
        len(wysylki) == 1, len(wysylki))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
