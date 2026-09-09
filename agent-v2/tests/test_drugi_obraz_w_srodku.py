# -*- coding: utf-8 -*-
"""Drugi obraz stoi w srodku TEKSTU i trafia tam bez znacznika w tresci.

## Skad sie wzial

Polecenie wlasciciela, 9 wrzesnia 2026: dwa obrazy na artykul. Pytal tez
wprost, skad model bedzie wiedzial, gdzie wstawic drugi.

NIE BEDZIE — miejsce wybiera kod, i to jest wybor, nie brak. Znacznik pisany
przez pisarza (`[[IMAGE]]` albo podobny) odrzucono z dwoch policzalnych
powodow:

  * pisarz, ktory ma pamietac o dodatkowym znaczniku, czasem go nie napisze,
    a czasem napisze cztery;
  * `jezyki.ZNACZNIK_SZABLONU` lapie nawias z wielkimi literami jako
    NIEWYPELNIONE POLE SZABLONU. Ta sama bramka 9 wrzesnia odlozyla gotowy,
    oplacony artykul za zwykly odnosnik Markdown. Znacznik obrazu wpadalby
    w nia z definicji, wiec trzeba by budowac wyjatek w kontroli, ktora ma
    wyjatkow nie miec.

## Czego pilnuje ten plik

1. Polowa liczona SLOWAMI, nie akapitami. Przy jednym akapicie na trzysta
   slow i szesciu po dwadziescia srodek listy nie jest srodkiem tekstu.
2. Nigdy przy krawedziach. Obraz tuz pod okladka wyglada jak druga okladka;
   obraz przed ostatnim akapitem rozbija puente, a ostatnia linijka jest
   w tym pismie celowana w kogos.
3. Nigdy w wykazie zrodel ani w naglowku.
4. Krotki tekst nie dostaje drugiego obrazu — zamiast wciskac go na sile.
5. Kotwica jest POCZATKIEM akapitu, bo edytor Substacka sklada wlasne wezly
   i numer `<p>` po wklejeniu HTML-a nie musi sie zgadzac z numerem akapitu.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_drugi_obraz_w_srodku.py
"""
import io
import sys

sys.path.insert(0, "agent-v2")
import config   # noqa: E402
import stages   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


def akapit(n, slowo="slowo"):
    return " ".join([slowo] * n) + "."


print("=== 1. WYKAZ ZRODEL I NAGLOWKI NIE SA TRESCIA ===")
body = ("# Tytul\n\n" + akapit(20) + "\n\n" + akapit(20) +
        "\n\n## Sources\n\n- [cos](https://example.org/a)\n\n- [cos](https://example.org/b)")
ak = stages._akapity_tresci(body)
sprawdz("zostaly tylko akapity tresci", len(ak) == 2, str(len(ak)))
sprawdz("naglowek odpadl", not any(a.startswith("#") for a in ak), str(ak)[:80])
sprawdz("odnosniki ze zrodel odpadly",
        not any("example.org" in a for a in ak), str(ak)[:80])

print()
print("=== 2. KROTKI TEKST NIE DOSTAJE DRUGIEGO OBRAZU ===")
for ile in (0, 1, 2, 3, 4):
    sprawdz("%d akapitow -> brak" % ile,
            stages._miejsce_na_drugi_obraz([akapit(20)] * ile) == -1,
            str(stages._miejsce_na_drugi_obraz([akapit(20)] * ile)))
sprawdz("5 akapitow juz tak",
        stages._miejsce_na_drugi_obraz([akapit(20)] * 5) >= 0)

print()
print("=== 3. POLOWA LICZONA SLOWAMI, NIE AKAPITAMI ===")
# CALY SENS TEJ FUNKCJI. Pierwszy akapit niesie polowe tekstu, wiec srodek
# tekstu jest tuz za nim — a srodek LISTY bylby dopiero przy czwartym.
nierowne = [akapit(300), akapit(20), akapit(20), akapit(20), akapit(20), akapit(20)]
g = stages._miejsce_na_drugi_obraz(nierowne)
sprawdz("nierowne akapity: obraz idzie za dlugim, nie w polowie listy",
        g == 1, "wyszlo %d" % g)
rowne = [akapit(50)] * 8
g = stages._miejsce_na_drugi_obraz(rowne)
sprawdz("rowne akapity: obraz w srodku listy", g in (3, 4), "wyszlo %d" % g)

print()
print("=== 4. NIGDY PRZY KRAWEDZIACH ===")
# Kontrdowod dla sekcji 3: sam pomiar slowami nie wystarczy. Tekst, ktorego
# ostatni akapit niesie polowe slow, wskazalby miejsce TUZ PRZED PUENTA.
na_koncu = [akapit(10), akapit(10), akapit(10), akapit(10), akapit(10), akapit(400)]
g = stages._miejsce_na_drugi_obraz(na_koncu)
sprawdz("polowa na koncu nie wpycha obrazu przed puente",
        g <= len(na_koncu) - 3, "wyszlo %d z %d" % (g, len(na_koncu)))
na_poczatku = [akapit(400), akapit(10), akapit(10), akapit(10), akapit(10), akapit(10)]
g = stages._miejsce_na_drugi_obraz(na_poczatku)
sprawdz("i nie wpycha go tuz pod okladke", g >= 1, "wyszlo %d" % g)
for n in range(5, 25):
    g = stages._miejsce_na_drugi_obraz([akapit(30)] * n)
    if not (1 <= g <= n - 3):
        sprawdz("krawedzie trzymaja sie przy %d akapitach" % n, False,
                "wyszlo %d" % g)
        break
else:
    sprawdz("krawedzie trzymaja sie dla 5-24 akapitow", True)

print()
print("=== 5. PRESET MOZE ZAMOWIC JEDEN OBRAZ ===")
stare = getattr(config, "OBRAZY_NA_ARTYKUL", 2)
try:
    sprawdz("domyslnie dwa", int(stare) == 2, str(stare))
    config.OBRAZY_NA_ARTYKUL = 1
    w = stages.grafika_srodek(None, 1, {"title": "t", "body": "\n\n".join([akapit(30)] * 8)})
    sprawdz("przy jednym: zero platnych wywolan",
            w.get("pominieta") == "preset zamawia jeden obraz", str(w))
    config.OBRAZY_NA_ARTYKUL = stare
    stary_w = config.OBRAZ_WLACZONY
    config.OBRAZ_WLACZONY = False
    w = stages.grafika_srodek(None, 1, {"title": "t", "body": "\n\n".join([akapit(30)] * 8)})
    sprawdz("wylaczone obrazy wylaczaja tez drugi", "pominieta" in w, str(w))
    config.OBRAZ_WLACZONY = stary_w
finally:
    config.OBRAZY_NA_ARTYKUL = stare

print()
print("=== 6. ZA KROTKI TEKST NIE PLACI ZA OBRAZ ===")
w = stages.grafika_srodek(None, 1, {"title": "t", "body": akapit(30) + "\n\n" + akapit(30)})
sprawdz("trzy akapity: pominiete bez wywolania",
        w.get("pominieta") == "za malo akapitow", str(w))

print()
print("=== 7. PUBLIKACJA UMIE WSTAWIC OBRAZ W SRODEK ===")
br = io.open("agent-v2/browser.py", encoding="utf-8").read()
sprawdz("jest karetka za akapitem", "_JS_KARETKA_ZA_AKAPITEM" in br)
sprawdz("szuka POCZATKU akapitu, nie dowolnego wystapienia",
        "startsWith(szukane)" in br)
sprawdz("karetka ladzie na KONCU akapitu", "zakres.collapse(false)" in br)
sprawdz("bez kotwicy nie wkleja na slepo",
        "pomijam (%s)" in br or "pomijam" in br)
sprawdz("wystaw_artykul szuka pliku -2.png", '"-2.png"' in br)
sprawdz("i kotwicy obok niego", '"-2.txt"' in br)
# KOLEJNOSC: srodek przed okladka. Okladka dokladana na gore przesuwa wezly,
# wsrod ktorych szukamy kotwicy.
i_srodek = br.index("ŚRODEK PRZED OKŁADKĄ")
i_okladka = br.index('page.keyboard.press("Control+Home")', i_srodek)
sprawdz("srodek wklejany PRZED okladka", i_srodek < i_okladka)

print()
print("=== 8. ZNACZNIKA W TRESCI NIE MA I NIE MA BYC ===")
# Gdyby ktos wrocil do pomyslu ze znacznikiem, ten wiersz oblewa razem
# z bramka szablonu, ktora go zlapie.
import jezyki  # noqa: E402
import gates   # noqa: E402
sprawdz("bramka szablonu nadal lapie nawias z wielkich liter",
        gates.artefakty_w_tekscie("Tekst.\n\n[[IMAGE]]\n\nDalej.") != [])
# Nazwa moze paść w OPISIE (i pada — w docstringu `grafika_srodek`, ktory
# tlumaczy, czemu tej drogi nie wybrano). Nie moze byc NAPISEM, ktorego kod
# szuka w tresci. Pytamy wiec skladni, nie tekstu pliku.
import ast  # noqa: E402
drzewo = ast.parse(io.open("agent-v2/stages.py", encoding="utf-8").read())
krotkie = [n.value for n in ast.walk(drzewo)
           if isinstance(n, ast.Constant) and isinstance(n.value, str)
           and len(n.value) < 60]
sprawdz("zaden krotki napis w kodzie nie jest znacznikiem obrazu",
        not [k for k in krotkie if "[[" in k and "]]" in k],
        str([k for k in krotkie if "[[" in k])[:90])

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
