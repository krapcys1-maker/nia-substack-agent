# -*- coding: utf-8 -*-
"""KTO nas obserwuje i subskrybuje — imiennie, z data.

PO CO, SKORO ZNAMY JUZ LICZBY. Bo liczba nie da sie z niczym polaczyc.
31 sierpnia 2026 konto uroslo z czterech subskrybentow do osmiu, a system
wykonal w tym czasie okolo pieciuset dzialan — i nie ma sposobu, zeby
powiedziec, ktore z nich cokolwiek przynioslo.

Majac liste z DATA, mozna zapytac wprost: czy ci, ktorzy nas zaobserwowali,
pojawili sie wczesniej wsrod naszych komentarzy i polubien. To roznica miedzy
„komentowanie dziala" jako przekonaniem a jako pomiarem.

DROGA JEST TA SAMA, CO PRZY KOPII SUBSKRYBENTOW: wlasny panel, wlasna sesja,
`substack.com/@<handle>/followers`. Cztery zgadniete adresy API oddaly puste
odpowiedzi i na tym poprzestalem — powtarzane sondowanie nieudokumentowanych
adresow to jest to, co nasz wlasny kod nazywa scrapingiem.

ZMIERZONE NA ZYWO 31 sierpnia: zakladka mowi „Followers (8)", a lista oddaje
SIEDEM osob. Nie zgaduje, czemu. Zapisujemy jedno i drugie — liczbe z profilu
w `wzrost.jsonl`, imiona w `czytelnicy.jsonl` — zamiast wybierac wygodniejsza.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo.
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import config   # noqa: E402
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


class Odnosnik:
    def __init__(self, href, tekst):
        self._h, self._t = href, tekst

    def get_attribute(self, _):
        return self._h

    def inner_text(self):
        return self._t


class Lokator:
    def __init__(self, odnosniki):
        self._o = odnosniki

    def all(self):
        return self._o


class AtrapaStrony:
    """Udaje strone Playwrighta na tyle, na ile `_ludzie_z_zakladki` jej uzywa."""

    def __init__(self, odnosniki):
        self._o = odnosniki

    def locator(self, _selektor):
        return Lokator(self._o)


# ODNOSNIKI PRZEPISANE Z ZYWEJ STRONY, razem z nawigacja, ktora tam stoi.
STRONA = AtrapaStrony([
    Odnosnik("/@explore", "Explore"),          # nawigacja, nie czlowiek
    Odnosnik("/@dashboard", "Dashboard"),      # nawigacja
    # UCHWYT Z KONFIGURACJI, NIE WPISANY. Atrapa miala tu na sztywno
    # uchwyt dostarczony z kodem, wiec u operatora z wlasnym kontem
    # „my sami" nie bylismy my i odsiew nie mial czego odsiac —
    # test oblewal, choc kod dzialal.
    Odnosnik("/@%s" % config.SUBSTACK_HANDLE, config.NAZWA_MARKI),  # my sami
    Odnosnik("/@czytelnik2", ""),    # awatar — bez tekstu
    Odnosnik("/@czytelnik2", "Publikacja Drogowa: Founder"),
    Odnosnik("/@czytelnik6", "Ewa Piata"),
    Odnosnik("/@czytelnik1?utm=x", "Grzegorz Siodmy"),
    Odnosnik("/@czytelnik3/notes", "Publikacja Lustrzana AI"),
])

print("=== 1. LUDZIE, NIE NAWIGACJA ===")
ludzie = browser._ludzie_z_zakladki(STRONA)
uchwyty = {x["uchwyt"] for x in ludzie}
sprawdz("czterech ludzi odczytanych", len(ludzie) == 4, sorted(uchwyty))
sprawdz("Explore odsiane", "explore" not in uchwyty)
sprawdz("Dashboard odsiany", "dashboard" not in uchwyty)
sprawdz("my sami odsiani", config.SUBSTACK_HANDLE not in uchwyty, uchwyty)

print()
print("=== 2. UCHWYT WYLUSKANY POPRAWNIE ===")
# Bez tego „?utm=x" i „/notes" tworza trzy wpisy dla jednej osoby przy
# kazdym zrzucie — a wtedy porownanie zrzutow miedzy dniami nic nie znaczy.
sprawdz("ogonek zapytania obciety", "czytelnik1" in uchwyty, uchwyty)
sprawdz("sciezka po uchwycie obcieta", "czytelnik3" in uchwyty, uchwyty)

print()
print("=== 3. AWATAR NIE KASUJE NAZWY ===")
# Ta sama osoba jest odnosnikiem dwa razy: raz awatarem (pusty tekst), raz
# nazwa. Gdyby wygrywal ostatni, polowa listy bylaby bezimienna.
lonely = next(x for x in ludzie if x["uchwyt"] == "czytelnik2")
sprawdz("nazwa zachowana mimo pustego awatara",
        lonely["nazwa"] == "Publikacja Drogowa: Founder", lonely)

print()
print("=== 4. BRAK NAZWY SPADA DO UCHWYTU ===")
sam = browser._ludzie_z_zakladki(AtrapaStrony([Odnosnik("/@ktos", "")]))
sprawdz("nazwa = uchwyt, nie pusty napis",
        sam and sam[0]["nazwa"] == "ktos", sam)

print()
print("=== 5. SMIECI NIE WYWALAJA ODCZYTU ===")
# Zrzut jest premia; wyjatek tutaj zabralby caly pomiar statystyk.
class ZlaStrona:
    def locator(self, _):
        raise RuntimeError("odlaczona ramka")


sprawdz("wyjatek strony -> pusta lista, bez podnoszenia",
        browser._ludzie_z_zakladki(ZlaStrona()) == [])
sprawdz("odnosnik bez href -> pomijany",
        browser._ludzie_z_zakladki(
            AtrapaStrony([Odnosnik(None, "x")])) == [])

print()
print("=== 6. ZAPIS TO HISTORIA, NIE OSTATNI STAN ===")
stary = browser.CZYTELNICY
browser.CZYTELNICY = pathlib.Path(tempfile.mkdtemp()) / "czytelnicy.jsonl"
try:
    browser.kto_nas_czyta = lambda page=None: {
        "obserwujacy": [{"uchwyt": "a", "nazwa": "A"}],
        "subskrybenci": [{"uchwyt": "b", "nazwa": "B"}],
        "odczytane": ["obserwujacy", "subskrybenci"], "blad": None}
    z1 = browser.zapisz_czytelnikow()
    z2 = browser.zapisz_czytelnikow()
    linie = browser.CZYTELNICY.read_text(encoding="utf-8").strip().splitlines()
    sprawdz("dwa zrzuty, dwie linie", len(linie) == 2, len(linie))
    sprawdz("zrzut ma date", str(z1.get("kiedy", "")).startswith("20"), z1)
    w = json.loads(linie[0])
    sprawdz("i obie listy", w["obserwujacy"] and w["subskrybenci"], w)

    # ZRZUT, KTORY SIE NIE UDAL, NIE MOZE UDAWAC PUSTEGO KONTA. Zapisana pusta
    # lista wygladalaby pozniej jak dzien, w ktorym wszyscy odeszli.
    browser.kto_nas_czyta = lambda page=None: {
        "obserwujacy": [], "subskrybenci": [], "odczytane": [],
        "blad": "TimeoutError"}
    sprawdz("porazka nie dopisuje pustego zrzutu",
            browser.zapisz_czytelnikow() is None
            and len(browser.CZYTELNICY.read_text(encoding="utf-8")
                    .strip().splitlines()) == 2)
finally:
    browser.CZYTELNICY = stary

print()
print("=== 7. JEDNO WEJSCIE NA STRONE, W POMIARZE ===")
zrodlo = pathlib.Path("agent-v2/browser.py").read_text(encoding="utf-8")
i = zrodlo.index("def nasze_pozycje_do_pomiaru(")
blok = zrodlo[i:zrodlo.index("\ndef ", i + 10)]
sprawdz("pomiar zapisuje czytelnikow", "zapisz_czytelnikow(page)" in blok)
sprawdz("i uzywa OTWARTEJ juz strony, nie nowej sesji",
        "zapisz_czytelnikow(page)" in blok
        and "zapisz_czytelnikow()" not in blok)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
