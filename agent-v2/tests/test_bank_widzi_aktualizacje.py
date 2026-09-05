# -*- coding: utf-8 -*-
"""Zmiana liczby w znanym zdaniu to nowe ustalenie, nie powtorka.

## Wada, ktora ten plik pilnuje

Bank nie mial pojecia „ten sam temat, nowe ustalenie". Odtworzone 5 wrzesnia
2026 na dwoch zdaniach roznicych sie wylacznie wersja i liczba:

    Acme released Model 5.1 with a context window of 100000 tokens.
    Acme released Model 5.2 with a context window of 200000 tokens.

OBIE warstwy odsiewu uznaly je za to samo:
  * `_klucz_faktu` daje im IDENTYCZNY klucz — celowo usuwa liczby, co jego
    docstring nazywa odpornoscia „na inna liczbe w tym samym zdaniu";
  * `_o_tym_samym` + `_wspolna_kotwica` orzeka blizniaki, bo dziela nazwe.

Kazda z tych regul jest sensowna osobno. Razem odcinaly to, po co istnieje
publikacja o liczbach: moment, w ktorym liczba SIE ZMIENILA. Nowa wersja
produktu, podniesiony prog, nowy wynik pomiaru — wszystko to wygladalo jak
material, ktory juz mamy.

## Czego ten plik pilnuje w DRUGA strone

Zeby rozroznik nie przepuszczal CUDZYCH faktow jako aktualizacji naszego.
Falszywe „to aktualizacja" kasuje prawidlowy wpis i wstawia w jego miejsce
material o czym innym — to jest gorsze niz wada, ktora naprawiamy. Sekcja 2
trzyma trzy przypadki, ktore aktualizacja NIE sa.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_bank_widzi_aktualizacje.py
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import config  # noqa: E402

config.uzyj_katalogu_danych(pathlib.Path(tempfile.mkdtemp()))
import stages  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


A = "Acme released Model 5.1 with a context window of 100000 tokens."
B = "Acme released Model 5.2 with a context window of 200000 tokens."
C = "Acme's Model 5.1 offers a context window of one hundred thousand tokens."
D = "Vega shipped Model 7.0 with a context window of 300000 tokens."
P10 = "The permitted ceiling for a listed body stands at 10 units."
P20 = "The permitted ceiling for a listed body stands at 20 units."

print("=== 1. AKTUALIZACJA JEST ROZPOZNAWANA ===")
sprawdz("nowa wersja produktu", stages._to_aktualizacja(B, A))
sprawdz("podniesiony prog", stages._to_aktualizacja(P20, P10))
# KONTRDOWOD DO SAMEJ WADY: obie warstwy odsiewu nadal uwazaja je za to samo,
# wiec bez `_to_aktualizacja` ten material NIE wszedlby do banku.
sprawdz("a klucz faktu nadal ich nie odroznia",
        stages._klucz_faktu(A) == stages._klucz_faktu(B),
        (stages._klucz_faktu(A), stages._klucz_faktu(B)))
sprawdz("i odsiew po znaczeniu tez nie",
        stages._o_tym_samym(A, B, min_wspolnych=4, prog=0.35)
        and stages._wspolna_kotwica(A, B))

print()
print("=== 2. CO AKTUALIZACJA NIE JEST ===")
sprawdz("ten sam fakt innymi slowami", not stages._to_aktualizacja(C, A), C[:40])
sprawdz("inny produkt o podobnym ksztalcie zdania",
        not stages._to_aktualizacja(D, A), D[:40])
sprawdz("zdanie identyczne", not stages._to_aktualizacja(A, A))
sprawdz("zdanie bez zadnych liczb",
        not stages._to_aktualizacja("The ceiling was raised.",
                                    "The ceiling was lowered."))
sprawdz("wspolna liczba znaczy powtorke",
        not stages._to_aktualizacja(
            "The ceiling stands at 10 units and 20 parts.",
            "The ceiling stands at 10 units and 30 parts."))

print()
print("=== 3. BANK PRZYJMUJE AKTUALIZACJE I WYCOFUJE STARY WPIS ===")


def kand(f):
    return {"fact": f,
            "wrong_belief": "Readers assume the ceiling has never moved at all.",
            "actually": "The ceiling moved and the retender route moved with it.",
            "decision": "The regulator raised the ceiling after a retender review.",
            "consequence": "Your team has to re-plan the schedule.",
            "url": "https://example.org/a", "domena": "przyklad"}


stages.dopisz_kandydatow([kand(P10)])
wynik = stages.dopisz_kandydatow([kand(P20)])
sprawdz("policzona jako aktualizacja", wynik.get("aktualizacje") == 1, wynik)
sprawdz("i nie jako 'juz znane'", wynik.get("znane") == 0, wynik)

indeks = stages.wczytaj_indeks()
wg_tresci = {str(w.get("fact")): w.get("status") for w in indeks}
sprawdz("stary wpis wycofany", wg_tresci.get(P10) == "zastapiony", wg_tresci)
sprawdz("nowy wpis uzywalny", wg_tresci.get(P20) == "nowy", wg_tresci)
# Wycofany nie moze byc podawany do pisania — inaczej „aktualizacja" znaczy
# tylko, ze w banku lezy teraz OBOK siebie stara i nowa liczba.
sprawdz("wycofany nie jest juz 'nowy'", "zastapiony" in wg_tresci.values())

print()
print("=== 4. POWTORKA NADAL NIE WCHODZI ===")
# KONTRDOWOD NA POPRAWKE: gdyby przejscie bylo za szerokie, bank przyjmowalby
# wszystko, co ma jakakolwiek inna liczbe — i odsiew blizniakow przestalby
# cokolwiek znaczyc.
przed = len(stages.wczytaj_indeks())
w2 = stages.dopisz_kandydatow([kand(P20)])
sprawdz("to samo zdanie drugi raz nie wchodzi",
        len(stages.wczytaj_indeks()) == przed, (przed, w2))
sprawdz("i jest policzone jako znane", w2.get("znane") == 1, w2)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
