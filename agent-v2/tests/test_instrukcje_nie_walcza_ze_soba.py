# -*- coding: utf-8 -*-
"""Instrukcje dla pisarza nie moga sobie przeczyc — bo wtedy wygrywa nudna.

## Skad ten plik

9 wrzesnia 2026, po dwoch odrzuconych artykulach, przeczytano CALY zestaw
instrukcji naraz — silnik i kartridz — i znaleziono kilkanascie miejsc, gdzie
jedno polecenie zabrania tego, czego drugie wymaga. Model dostajacy dwa
sprzeczne polecenia wybiera bezpieczniejsze, a bezpieczniejsze jest zawsze
to nudne. Stad tekst poprawny, oplacony i bez osoby w srodku.

Najgorsza sprzecznosc byla WLASNA POPRAWKA sprzed kilku godzin. Brief pisarza
dostal zdanie:

    „before any judgement, any joke and any figure, tell them what actually
    happened"

a wspolny glos w kartridzu mowi:

    „The opening can already be funny. You do not owe the reader a neutral
    briefing before you are allowed to sound like yourself."

Poprawka mial rozwiazac problem „czytelnik nie wie, o czym to jest" i przy
okazji kazala pisarce byc plaska, zanim wolno jej byc soba. Dokladnie to, na
co wlasciciel narzeka od tygodnia.

## Czego pilnuje ten plik

Kazde sprawdzenie to jedna para instrukcji, ktore stały ze soba w sprzecznosci
i zostaly pogodzone. Plik NIE ocenia, czy tekst brzmi jak NIA — tego nie da sie
sprawdzic bez czytania artykulu. Pilnuje czegos wezszego i sprawdzalnego:
zeby zaden prompt nie kazal jej znowu byc kims innym.

Czyta PLIKI, nie zlozony prompt, bo kartridz produkcyjny (`nia-serwer`) nie
jest w gicie, a publiczny (`nia-unfiltered`) jest — i to on jest wzorem.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_instrukcje_nie_walcza_ze_soba.py
"""
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


def czytaj(p):
    """Plik ZE SPLASZCZONYMI bialymi znakami.

    Markdown lamie wiersze tam, gdzie wypadnie, wiec sprawdzenie szukajace
    frazy dluzszej niz pol linijki oblewa z powodu, ktory nie ma nic wspolnego
    z trescia. Pierwsza wersja tego pliku oblala tak PIEC razy z rzedu i za
    kazdym razem zdanie bylo na miejscu.
    """
    return " ".join(io.open(p, encoding="utf-8").read().split())


def wersja_surowa(p):
    return io.open(p, encoding="utf-8").read()


PISARZ = czytaj("agent-v2/prompts/pisarz_persona.md")
SYNTEZA = czytaj("agent-v2/prompts/synteza.md")
RECENZENT = czytaj("agent-v2/prompts/recenzent.md")
STAGES = czytaj("agent-v2/stages.py")
PULA = czytaj("agent-v2/artykul_z_puli.py")
GLOS_ART = czytaj("presety/nia-unfiltered/prompty/glos_artykulu.md")
GLOS_WSP = czytaj("presety/nia-unfiltered/prompty/glos_wspolny.md")
PRESET = czytaj("presety/nia-unfiltered/preset.toml")
OSOBOWOSC = czytaj("agent-v2/personality.py")

print("=== 1. SCENA NAJPIERW, ALE NIE KOSZTEM GLOSU ===")
# Sprzecznosc numer jeden i wlasna. Zakaz zartu przed opisem sytuacji kazal
# napisac sprawozdanie, a dopiero potem wpuscic autorke.
sprawdz("zakaz zartu przed scena zniknal",
        "before any judgement, any joke" not in PISARZ)
sprawdz("wymog zrozumienia zostal",
        "the situation has to reach them early and whole" in PISARZ)
sprawdz("i wprost mowi, ze to nie jest regula o tonie",
        "not about tone" in PISARZ and "never asks you to be flat first" in PISARZ)
sprawdz("glos od pierwszego slowa",
        "Tell the story in your voice from the first word" in PISARZ)
# Druga strona tej samej pary: kartridz nadal pozwala otworzyc zartem.
sprawdz("kartridz nadal pozwala otworzyc zartem",
        "The opening can already be funny" in GLOS_WSP)

print()
print("=== 2. PYTANIA POMOCNICZE Z HISTORII, NIE Z SZABLONU ===")
# Staly zestaw („uklad, kto go ustawil, ile kosztuje, gdzie jeszcze chodzi")
# zamienial kazdy temat w ten sam artykul o instytucjach.
sprawdz("staly szkielet eseju zniknal",
        "what is the arrangement, who set it up" not in PULA)
sprawdz("pierwsze pytanie to zawsze co sie stalo",
        "the FIRST one is always what actually happened" in PULA)
sprawdz("i jest powiedziane, czemu szablon szkodzi",
        "same article about institutions" in PULA)

print()
print("=== 3. JEDNA HISTORIA WYSTARCZY ===")
# `glos_artykulu` mowi „one incident and a few supported facts are enough",
# a bramka glebokosci zadala drugiego aktu ALBO zasiegu poza jedno miejsce.
sprawdz("kartridz nadal mowi, ze jedno zdarzenie wystarczy",
        "one incident and a few supported facts are enough" in GLOS_ART)
sprawdz("drugi akt moze byc WEWNATRZ zdarzenia",
        "A turn INSIDE the same event counts" in PULA)
sprawdz("bramka opisana tak samo jak prompt",
        "zwrot wewnatrz tego" in PULA and "sto agentow" in PULA)
# Kontrdowod: bramka ma NADAL lapac fakt kompletny w jednym zdaniu.
sprawdz("fakt na jedno zdanie nadal jest notka",
        "kompletny w JEDNYM ZDANIU" in PULA)

print()
print("=== 4. ANALOGIA NIE JEST CENA ZA BYCIE CIEKAWYM ===")
sprawdz("synteza nie rozstrzyga juz o ciekawosci analogia",
        "field that decides whether the article is interesting" not in SYNTEZA)
sprawdz("wolno zostawic puste", "Leave this empty when the honest answer" in SYNTEZA)
sprawdz("jedna historia to caly artykul",
        "One story told well is a whole article" in SYNTEZA)

print()
print("=== 5. ILUSTRACJA TO NIE TWIERDZENIE O INNEJ BRANZY ===")
# Synteza mowila „they need no sources", recenzent slusznie zada zrodla dla
# porownania z inna branza. Obie racje, dwa rozne byty.
sprawdz("synteza ogranicza pozwolenie do tego pola",
        "that permission stops at this field" in SYNTEZA)
sprawdz("i nazywa roznice wprost",
        "needs no source and never will" in SYNTEZA and '"banks do this too"' in SYNTEZA)
sprawdz("recenzent nadal zada zrodla dla porownania z branza",
        "comparison with another industry needs its own source" in RECENZENT)

print()
print("=== 6. RECENZENT WIE, KIM JEST AUTORKA ===")
# Zglosil „Writing is rather my thing" jako fakt bez pokrycia, a przez
# `ostatnie_uwagi` zarzut wracal do nastepnego pisarza.
sprawdz("recenzent dostaje oswiadczenie", "oswiadczenie=_oswiadczenie" in STAGES)
sprawdz("brak oswiadczenia nie blokuje recenzji",
        "(no disclosure supplied)" in STAGES)
sprawdz("prompt recenzenta ma sekcje o autorce",
        "{oswiadczenie}" in RECENZENT and "as established fact" in RECENZENT.lower())
sprawdz("pierwsza osoba wynikajaca z oswiadczenia jest POPARTA",
        "is SUPPORTED" in RECENZENT)
sprawdz("wymyslone kolezanki to PROSE, nie falsz",
        "class them PROSE" in RECENZENT)

print()
print("=== 7. UWAGI O KSZTALCIE NIE WRACAJA JAKO POLECENIA ===")
for gate in ("BRAK_ESKALACJI", "CZYTELNIK_NIEPRZYLAPANY", "OTWARCIE_ZNANE"):
    i = STAGES.index('if m.group(1) in ("DLUGOSC"')
    sprawdz("%s nie wraca do pisarza" % gate, gate in STAGES[i:i + 400],
            STAGES[i:i + 400])
sprawdz("FAKT_BEZ_POKRYCIA nadal wraca",
        "FAKT_BEZ_POKRYCIA" not in STAGES[STAGES.index('if m.group(1) in ("DLUGOSC"'):
                                          STAGES.index('if m.group(1) in ("DLUGOSC"') + 400])

print()
print("=== 8. RUBRYKA ZAPRASZA, NIE PRZYDZIELA NASTROJU ===")
sprawdz("kartridz nadal mowi, ze rubryka to nie przydzial nastroju",
        "not a mood assignment" in GLOS_WSP)
sprawdz("zniklo: Grudging is the correct register",
        "Grudging is the correct register" not in PRESET)
sprawdz("zniklo: Properly annoyed, not wry",
        "Properly annoyed, not wry" not in PRESET)
sprawdz("zniklo: stop being funny first",
        "stop being funny first" not in PRESET)
sprawdz("ale czlowiek nadal jest wazniejszy od zartu",
        "The person comes before the joke" in PRESET)

print()
print("=== 9. PUENTA TO MOZLIWOSC ===")
sprawdz("nie ma juz nakazu celowania w kogos",
        "The last line is aimed at somebody" not in GLOS_ART)
sprawdz("mocna puenta nadal polecana", "It is not a quota" in GLOS_ART)
sprawdz("i podany powod, czemu nakaz szkodzil",
        "hunting for somebody to tell off" in GLOS_ART)
sprawdz("zakaz podsumowania i moralu zostaje",
        "Never a summary, never a moral" in GLOS_ART)

print()
print("=== 10. WAZNOSC ZASTRZEZENIA, NIE JEGO DLUGOSC ===")
# Wlasna reguła sprzed kilku godzin: „zastrzezenie, ktore potrzebuje wlasnego
# akapitu, jest zbedne". Dlugosc wyjasnienia nie mowi nic o waznosci.
sprawdz("test po dlugosci zniknal",
        "would need its own paragraph to explain is a qualification" not in GLOS_ART)
sprawdz("test po znaczeniu wszedl",
        "would think something different without it" in GLOS_ART)
sprawdz("wazne zastrzezenie dostaje swoj akapit",
        "gets its paragraph" in GLOS_ART)

print()
print("=== 11. ZAKAZ DOTYCZY ZMYSLONYCH TESTOW ===")
sprawdz("wolno powiedziec o tescie zapisanym w kontekscie",
        "the supplied context does not record" in OSOBOWOSC)
sprawdz("i nadal nie wolno zmyslic wlasnego",
        "never invent facts" in OSOBOWOSC)

print()
print("=== 12. STOPKA: KOD USUWA, NIE DODAJE ===")
sprawdz("prompt persony juz nie obiecuje stopki",
        "code adds the source-date footer" not in PISARZ)
sprawdz("i mowi prawde o tym, co robi kod",
        "code strips it if it appears" in PISARZ)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
raise SystemExit(1 if oblane else 0)
