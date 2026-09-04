# -*- coding: utf-8 -*-
"""Polubienie ma zapisywac, CZYJ wpis polubilismy.

ZMIERZONE W DZIENNIKU 31 sierpnia 2026: polubienia zapisywaly sie jako
`{kiedy, rodzaj, udane}` i NIC WIECEJ.

    polubien w dzienniku:   151
    komentarzy:              95

To nasze NAJCZESTSZE dzialanie i jedyne, o ktorym nie wiedzielismy zupelnie
nic poza tym, ze bylo. Ma to takie samo znaczenie, co przy komentarzach:
konto o AI, ktore lajkuje pod rezerwa paliwowa, wydaje najczestszy gest na
publicznosc bez powodu, zeby nas obserwowac.

I gorzej: bez zapisu nie dalo sie tego nawet ZMIERZYC. Audyt „czy nie
wygladamy jak bot" mogl policzyc komentarze i o polubieniach nie mial pojecia.

ZMIERZONE PRZED NAPISANIEM KODU, nie po. Rozpoznanie na zywym kanale
sprawdzilo, czy autor jest w ogole osiagalny z przycisku „Like":

    0: poziom 1   Genie                        /@publikacja2
    1: poziom 1   LonnieSly                    /@czytelnik5
    2: poziom 1   Ewa Piata  /@czytelnik6
    3: poziom 1   Robert M. Hamburger          /@hamburgersstand
    4: poziom 1   Allen R.                     /@allenras
    ODCZYTANYCH: 5 z 5

Autor stoi jeden poziom nad przyciskiem. Dopiero majac ten pomiar warto bylo
cokolwiek pisac.

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


class AtrapaPrzycisku:
    """Udaje przycisk Playwrighta — oddaje to, co oddalby prawdziwy DOM."""

    def __init__(self, odpowiedz):
        self._odp = odpowiedz

    def evaluate(self, _skrypt):
        if isinstance(self._odp, Exception):
            raise self._odp
        return self._odp


print("=== 1. ODCZYT AUTORA ===")
kto = browser._autor_przy_przycisku(
    AtrapaPrzycisku({"href": "/@publikacja2", "tekst": "Genie"}))
sprawdz("nazwa odczytana", kto and kto["nazwa"] == "Genie", kto)
sprawdz("uchwyt wyluskany z adresu", kto and kto["uchwyt"] == "publikacja2", kto)

# PRAWDZIWY ZNAK NOWEJ LINII, nie backslash i litera. Pierwsza wersja tego
# atrapy miala w tekscie dwa znaki `\` i `n` i test slusznie oblal —
# `.split()` nie ma czego rozdzielic. Zapis przez `chr(10)` nie da sie
# przypadkiem zescapowac po drodze.
dlugi = browser._autor_przy_przycisku(AtrapaPrzycisku(
    {"href": "/@czytelnik6",
     "tekst": "  Ewa" + chr(10) + "  Piata  "}))
sprawdz("biale znaki sklejone w jedna nazwe",
        dlugi and dlugi["nazwa"] == "Ewa Piata", dlugi)

print()
print("=== 2. BRAK AUTORA ZNACZY 'NIE WIEM', NIE 'PRZERWIJ' ===")
# Zapis jest premia; samo polubienie wazniejsze. Wyjatek tutaj zabralby
# wszystkie pozostale polubienia w przebiegu.
sprawdz("null z DOM-u -> None",
        browser._autor_przy_przycisku(AtrapaPrzycisku(None)) is None)
sprawdz("wyjatek przegladarki -> None, bez podnoszenia",
        browser._autor_przy_przycisku(
            AtrapaPrzycisku(RuntimeError("odlaczony element"))) is None)
sprawdz("pusty slownik -> None",
        browser._autor_przy_przycisku(
            AtrapaPrzycisku({"href": "", "tekst": ""})) is None)

print()
print("=== 3. SAM UCHWYT WYSTARCZY ===")
# Zdarza sie odnosnik bez widocznego tekstu. Uchwyt jest wtedy jedyna
# informacja, jaka mamy — i lepsza niz nic.
sam = browser._autor_przy_przycisku(
    AtrapaPrzycisku({"href": "/@czytelnik5", "tekst": ""}))
sprawdz("nazwa spada do uchwytu", sam and sam["nazwa"] == "czytelnik5", sam)

print()
print("=== 4. WPIETE W POLUBIENIA ===")
zrodlo = pathlib.Path("agent-v2/browser.py").read_text(encoding="utf-8")
i = zrodlo.index("def polub_w_kanale(")
blok = zrodlo[i:zrodlo.index("\ndef ", i + 10)]
sprawdz("polubienie pyta o autora", "_autor_przy_przycisku(kandydat)" in blok)
sprawdz("i zapisuje go do dziennika", '"publikacja": kto["nazwa"]' in blok)
sprawdz("razem z uchwytem", '"komu": kto["uchwyt"]' in blok)
sprawdz("odczyt idzie PRZED klikniecie",
        blok.index("_autor_przy_przycisku(kandydat)")
        < blok.index("kandydat.click"))

print()
print("=== 5. KONTRDOWOD: STARY ZAPIS NIC NIE NIOSL ===")
# Gdyby test przechodzil takze na kodzie sprzed poprawki, nie mierzylby nic.
sprawdz("nie ma juz golego zapisu bez autora",
        'zapisz_w_dzienniku("polubienie", udane=True)\n' not in blok,
        "goly zapis nadal w kodzie")
sprawdz("porazka nadal sie zapisuje z powodem",
        'zapisz_w_dzienniku("polubienie", udane=False, powod=powod)' in blok)

print()
print("=== 6. TRYB SUCHY NADAL NIE KLIKA ===")
# Odczyt autora dzieje sie przed rozgalezieniem, wiec musi byc nieszkodliwy.
sprawdz("bez zgody wychodzimy przed klikaniem",
        blok.index("if not wyslij:") < blok.index("kandydat.click"))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
