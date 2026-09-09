# -*- coding: utf-8 -*-
"""Model, ktory pominal pole, nie powiedzial „nie". Pytamy raz jeszcze.

## Co sie stalo 9 wrzesnia 2026

Przebieg artykulu odrzucil CZTERY fakty z rzedu i skonczyl bez tekstu:

    ODPADA: ani drugiego aktu, ani zasiegu poza jedno miejsce
    >> po 4 probach zaden fakt nie uniesie artykulu — nie pisze.

Powtorzenie DOKLADNIE tego samego wywolania na tym samym fakcie — banki
w Chinach wydajace karty kredytowe z tokenami modeli zamiast punktow — oddalo
`beyond_one_place` na dwadziescia szesc slow:

    „Agricultural Bank's Kimi card and China Merchants' MiniMax card show the
    arrangement is not unique to one bank or AI company"

W przebiegu to pole bylo puste. Temat mial zasieg przez caly czas; tani model
raz go wpisal, a raz nie.

To ta sama wada, ktora tego samego ranka skasowala temat artykulu 0022 na
klasyfikacji, i ta sama odpowiedz: jedno ponowienie za 0,002 USD zamiast
wyrzucenia dobrego tematu do kosza.

## Granica ponowienia

Ponawiamy WYLACZNIE, gdy OBA pola sa puste. To znaczy „model nie
odpowiedzial". Gdy wpisal zdanie i bramka uznala je za za slabe, to jest jego
werdykt — pytanie drugi raz byloby placeniem za podwazanie wlasnej bramki,
dokladnie tak samo, jak przy ratunku wiodacego zrodla.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_puste_pole_to_nie_odmowa.py
"""
import ast
import io
import sys

sys.path.insert(0, "agent-v2")
import artykul_z_puli as art   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


print("=== 1. PUSTE POLE ODROZNIONE OD ODPOWIEDZI ===")
sprawdz("oba puste to brak odpowiedzi", art._pola_glebi_puste({}) is True)
sprawdz("same biale znaki tez",
        art._pola_glebi_puste({"second_act": "  ", "beyond_one_place": ""}) is True)
sprawdz("wpisany drugi akt to odpowiedz",
        art._pola_glebi_puste({"second_act": "Firma zmienila kurs w sierpniu."}) is False)
sprawdz("wpisany zasieg to odpowiedz",
        art._pola_glebi_puste({"beyond_one_place": "Trzy banki w dwoch krajach."}) is False)
# GRANICA. Krotkie „none" JEST odpowiedzia modelu — bramka je odrzuci, ale to
# jest werdykt, nie milczenie, wiec ponowienia nie ma.
sprawdz("slowo `none` to odpowiedz, nie milczenie",
        art._pola_glebi_puste({"second_act": "none"}) is False)

print()
print("=== 2. BRAMKA SIE NIE ZMIENILA ===")
# Kontrdowod: ponowienie nie moze byc po cichu poluzowaniem progu.
sprawdz("pusty brief nadal odpada", art.uniesie_artykul({})[0] is False)
sprawdz("krotki wypelniacz nadal odpada",
        art.uniesie_artykul({"second_act": "none"})[0] is False)
sprawdz("prawdziwy zasieg przechodzi",
        art.uniesie_artykul(
            {"beyond_one_place": "Trzy inne banki w dwoch krajach robia to samo."})[0] is True)
sprawdz("prawdziwy drugi akt przechodzi",
        art.uniesie_artykul(
            {"second_act": "Po skardze regulator otworzyl postepowanie."})[0] is True)

print()
print("=== 3. PONOWIENIE JEST W OBU MIEJSCACH, GDZIE PADA BRAMKA ===")
# Petla pyta o glebie DWA razy: raz dla pierwszego faktu, raz dla kazdego
# nastepnego. Poprawka tylko w jednym miejscu naprawialaby polowe przebiegow.
zrodlo = io.open("agent-v2/artykul_z_puli.py", encoding="utf-8").read()
drzewo = ast.parse(zrodlo)
fn = next(n for n in ast.walk(drzewo)
          if isinstance(n, ast.FunctionDef) and n.name == "_przebieg")
bramki = [n.lineno for n in ast.walk(fn)
          if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
          and n.func.id == "uniesie_artykul"]
puste = [n.lineno for n in ast.walk(fn)
         if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
         and n.func.id == "_pola_glebi_puste"]
sprawdz("bramka pada co najmniej dwa razy", len(bramki) >= 2, str(bramki))
sprawdz("i ponowienie tez", len(puste) >= 2, str(puste))
sprawdz("kazde ponowienie stoi przy jakiejs bramce",
        all(any(abs(l - b) < 25 for b in bramki) for l in puste),
        "puste %s, bramki %s" % (puste, bramki))

print()
print("=== 4. PONAWIAMY BRIEF, NIE CALY RESEARCH ===")
# Ponowienie ma kosztowac 0,002 USD, a nie caly przebieg. Miedzy bramka
# a ponowieniem nie moze stanac nic platnego poza `temat_z_faktu`.
i = zrodlo.index("oba pola glebi puste")
wycinek = zrodlo[i:i + 320]
sprawdz("ponawiane jest `temat_z_faktu`", "temat_z_faktu(conn, run_id, fakt)" in wycinek,
        wycinek[:120])
for drogie in ("discovery", "fetch", "classify", "synthesis", "stages.write"):
    sprawdz("i nic drogiego obok: %s" % drogie, drogie not in wycinek)

print()
print("=== 5. PONOWIENIE JEST WIDOCZNE W DZIENNIKU ===")
# Ciche drugie wywolanie to rachunek, ktorego nikt nie umie wytlumaczyc.
sprawdz("przebieg mowi, ze pyta drugi raz",
        zrodlo.count("pytam raz jeszcze o ten sam fakt") == 2,
        zrodlo.count("pytam raz jeszcze o ten sam fakt"))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
