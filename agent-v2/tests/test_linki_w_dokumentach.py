# -*- coding: utf-8 -*-
"""Link do pliku, ktorego nie ma, jest w tym repozytorium wada produktu.

## Po co ten plik istnieje

Polowa tego, co dostaje ktos z zewnatrz, to dokumentacja: `README.md` odsyla
do dziesieciu dokumentow, one odsylaja do siebie nawzajem i do plikow w kodzie.
Martwy odnosnik nie zglasza sie NICZYM — GitHub pokazuje 404 dopiero temu, kto
w niego kliknie, czyli pierwszemu czytelnikowi z zewnatrz, i to po tym, jak
uwierzyl, ze reszta zostala sprawdzona.

To ta sama rodzina, co liczby w dokumentach (`test_liczby_w_dokumentach.py`):
twierdzenie postawione dla ludzi spoza projektu, ktorego nikt nie przelicza.
Roznica jest tylko taka, ze liczba klamie po cichu, a link klamie glosno.

Zmierzone przy zakladaniu tego pliku: 40 odnosnikow lokalnych, wszystkie zywe.
Wartosc tego testu nie jest wiec w tym, co znalazl dzisiaj, tylko w tym, ze
przy nastepnej zmianie nazwy pliku ktos sie dowie ZANIM wypchnie.

## Czego ten test NIE robi

Nie odpytuje sieci. Adresy `http(s)://` sa pomijane swiadomie: sprawdzanie ich
wymagaloby wyjscia na zewnatrz przy kazdym przebiegu, a zestaw ma chodzic bez
sieci i bez pieniedzy. Cudza strona, ktora dzis odpowiada, i tak moze zniknac
jutro — to nie jest cos, co da sie utrzymac testem.

Nie sprawdza tez kotwic (`#naglowek`) w obrebie pliku. Sprawdza sciezke.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_linki_w_dokumentach.py
"""
import pathlib
import re
import sys

KORZEN = pathlib.Path(__file__).resolve().parent.parent.parent

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# `[tekst](cel)` — bierzemy tylko cel, ucinamy kotwice.
ODNOSNIK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def dokumenty() -> list[pathlib.Path]:
    """Wszystkie `.md` widoczne dla kogos z zewnatrz.

    Katalog `dokumentacja-zrodla/` jest wlaczony celowo: to z niego powstaje
    sklejony dokument, wiec martwy link tam trafia potem do 13 tysiecy wierszy,
    ktore czyta sie jako calosc.
    """
    out = []
    for wzor in ("*.md", "docs/*.md", "agent-v2/*.md",
                 "agent-v2/prompts/*.md", "agent-v2/dokumentacja-zrodla/*.md"):
        out += sorted(KORZEN.glob(wzor))
    return out


def bez_blokow_kodu(tekst: str) -> str:
    """Wycina bloki ``` — to, co w nich stoi, NIE JEST odnosnikiem.

    Pierwsza wersja tego pliku zglosila dwa „martwe linki": `[...]({url})`
    w PRZYKLADZIE KODU wewnatrz dokumentacji. `{url}` to miejsce na wartosc
    w f-stringu, nie sciezka — czyli test oskarzal poprawny kod o wade, ktorej
    nie ma. Straznik z falszywymi alarmami zostaje wylaczony pierwszego dnia,
    dokladnie tak samo jak audyt oblewajacy na poprawnej instalacji.

    Zamazujemy zawartosc blokow spacjami, zeby numery wierszy w komunikacie
    dalej sie zgadzaly.
    """
    wynik, w_bloku = [], False
    for linia in tekst.split(chr(10)):
        if linia.lstrip().startswith("```"):
            w_bloku = not w_bloku
            wynik.append("")
            continue
        wynik.append("" if w_bloku else linia)
    return chr(10).join(wynik)


print("=== 1. KAZDY ODNOSNIK LOKALNY PROWADZI DO ISTNIEJACEGO PLIKU ===")
martwe = []
zbadane = 0
zewnetrzne = 0
for md in dokumenty():
    try:
        tekst = md.read_text(encoding="utf-8")
    except OSError:
        continue
    for m in ODNOSNIK.finditer(bez_blokow_kodu(tekst)):
        cel = m.group(1).strip()
        # Adresy sieciowe, kotwice w tym samym pliku i schematy pomijamy.
        if cel.startswith(("http://", "https://", "mailto:", "#")):
            zewnetrzne += 1
            continue
        # Nawias w tytule odnosnika potrafi zjesc domkniecie — takie cele
        # zawieraja spacje i nie sa sciezkami. Nie oskarzamy ich.
        sciezka = cel.split("#")[0].split(" ")[0].strip()
        if not sciezka:
            continue
        zbadane += 1
        if not (md.parent / sciezka).resolve().exists():
            martwe.append("%s -> %s" % (md.relative_to(KORZEN).as_posix(), cel))

print("    odnosnikow lokalnych: %d, sieciowych (pominietych): %d"
      % (zbadane, zewnetrzne))
sprawdz("zaden nie prowadzi do nieistniejacego pliku", not martwe,
        ("\n        " + "\n        ".join(sorted(set(martwe))[:10]))
        if martwe else "")

print()
print("=== 2. README ODSYLA DO TEGO, CO OBIECUJE ===")
# Dokumenty wymienione w README z nazwy sa dla kogos z zewnatrz jedyna mapa.
readme = (KORZEN / "README.md").read_text(encoding="utf-8")
for obowiazkowy in ("docs/INSTALL.md", "docs/ARCHITECTURE.md",
                    "docs/REPO_MAP.md", "docs/TROUBLESHOOTING.md",
                    "LICENSE"):
    sprawdz("  README wymienia %s" % obowiazkowy, obowiazkowy in readme)
    sprawdz("  ...i plik istnieje", (KORZEN / obowiazkowy).exists())

print()
print("=== 3. KONTRDOWOD: CZY TEN TEST W OGOLE COKOLWIEK ZOBACZY ===")
# Bez tego przechodzilby takze wtedy, gdyby wzorzec nie pasowal do niczego.
PROBKA = ("patrz [instalacja](docs/INSTALL.md), [nic](docs/NIE-MA-TEGO.md) "
          "oraz [sieć](https://example.org/x)")
cele = [m.group(1) for m in ODNOSNIK.finditer(PROBKA)]
sprawdz("wzorzec zdejmuje wszystkie trzy cele", len(cele) == 3, cele)
lokalne = [c for c in cele if not c.startswith("http")]
sprawdz("i odroznia lokalne od sieciowych", len(lokalne) == 2, lokalne)
sprawdz("martwy cel jest widziany jako martwy",
        not (KORZEN / "docs/NIE-MA-TEGO.md").exists())
sprawdz("a zywy jako zywy", (KORZEN / "docs/INSTALL.md").exists())

# I ze bloki kodu SA pomijane — bez tego sekcja 1 oskarzalaby
# przyklady kodu o martwe linki (`[...]({url})` w f-stringu).
_z_blokiem = ("tekst [zywy](docs/INSTALL.md)" + chr(10)
              + "```" + chr(10) + "[x]({url})" + chr(10) + "```")
sprawdz("odnosnik w bloku kodu NIE jest liczony",
        [m.group(1) for m in ODNOSNIK.finditer(
            bez_blokow_kodu(_z_blokiem))] == ["docs/INSTALL.md"])

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
