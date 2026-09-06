# -*- coding: utf-8 -*-
"""Porazka ma zostawiac slad — komentarz, odpowiedz, polubienie.

ZMIERZONE 30 sierpnia 2026 na dzienniku produkcji: 11 nieudanych komentarzy
na 92 proby (12 procent) i 7 nieudanych odpowiedzi na 47. Sprawdzone u zrodla
— 0 z 6 sprawdzalnych bylo jednak opublikowanych, wiec to prawdziwa strata.
Kosztowala 0,61 USD, czyli 92 procent calego przepalenia tamtego dnia.

CO NAPRAWDE BYLO NIEWIDOCZNE — SPROSTOWANE 1 WRZESNIA. Pierwsza wersja tego
docstringa twierdzila, ze `pod_rzad_nieudanych("komentarz")` „nie widzial ani
jednej porazki" i ze te 11 z 92 bylo niewidocznych. Nieprawda, i sprawdzilem
to w zrodle: na HEAD `dopisz_wynik("komentarz", ...)` stalo TRZY LINIE po
`potwierdz_komentarz(...)`, wewnatrz galezi wysylkowej i BEZ warunku na
powodzenie. Klasa „kliknelismy, Substack nie pokazuje" byla wiec w dzienniku
od poczatku — to wlasnie z niej pochodzi tamten pomiar.

Naprawde brakowalo TRZECH klas, tych, ktore nie dochodzily do klikniecia:

  - „nie ma pola komentarza pod tym postem" (wczesny return; zdarzylo sie dwa
    razy pierwszego dnia na produkcji — dwie rozne publikacje),
  - brak przycisku wysylki,
  - kazdy wyjatek.

Kosztowaly one: porazke nieuwzgledniona w serii `pod_rzad_zle`, brak powodu
w raporcie i cisze tam, gdzie awaria interfejsu wygladala jak spokojny dzien.
`wystaw_notke` i `_klik_na_profilu` domykaly to w `finally` od dawna.

DRUGA POLOWA TESTU DOTYCZY POLUBIEN: `zapisz_w_dzienniku("polubienie",
udane=True)` szlo w NASTEPNEJ linii po `click()`, wiec wszystkie 151 polubien
w dzienniku na 31 sierpnia bylo „udanych" z definicji. Doktryna z komentarzy
brzmi „Klikniecie przycisku nie jest dowodem" — polubienie bylo jedynym
dzialaniem, ktore jej nie przestrzegalo.

TRZECIA CZESC — SZKODY, KTORE ZROBILA SAMA TA POPRAWKA (sekcje 12-14):

  - zapis w `finally` stal PRZED `page.close()` i nie byl osloniety, wiec
    jeden zly argument zabieral sprzatanie przegladarki (sekcja 12),
  - `potwierdz_polubienie` oddawalo twarde `False` dla wezla, ktory wypadl
    z dokumentu, bo zakladalo, ze `evaluate` wtedy rzuci (sekcja 13),
  - nieudany komentarz karmil `hosty_gdzie_komentarz_nie_wchodzi` niezaleznie
    od tego, czy porazka mowila cokolwiek o hoscie (sekcja 6).

TEN TEST NIE RUSZA SIECI. Podstawia atrape przegladarki i sprawdza, co
naprawde lezy w pliku dziennika — nie to, czy funkcja zostala zawolana.

KONTRDOWODY SA ODTWARZANE, NIE OPISYWANE. Sekcje 12 i 13 wczytuja `browser.py`
DRUGI RAZ jako osobny modul, po odwrotnej latce na zrodle, i puszczaja na nim
ten sam scenariusz. Zmierzone liczby stoja przy tych sekcjach. Sekcja 11
pilnuje tego samego od strony zrodla.

Uruchamiac z korzenia repo, bez pytesta:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_cicha_porazka.py
"""
import json
import pathlib
import shutil
import sys
import tempfile

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


# --- ATRAPA PRZEGLADARKI -----------------------------------------------------
# Oddaje dokladnie tyle, ile `browser.py` od Playwrighta wola: liczbe trafien,
# widocznosc, klikniecie. Nic wiecej nie jest potrzebne, zeby przejsc kazda
# z trzech sciezek wyjscia.

class Brak:
    """Lokator, ktory nic nie dopasowal."""

    def count(self):
        return 0

    def is_visible(self):
        return False

    def nth(self, i):
        return self

    @property
    def first(self):
        return self

    def click(self, **k):
        raise AssertionError("klikniecie w niedopasowany lokator")


class Element:
    def __init__(self, widoczny=True):
        self.widoczny = widoczny
        self.klikniety = False

    def count(self):
        return 1

    def is_visible(self):
        return self.widoczny

    def nth(self, i):
        return self

    @property
    def first(self):
        return self

    def click(self, **k):
        self.klikniety = True

    def scroll_into_view_if_needed(self, **k):
        pass


class Zbior:
    def __init__(self, elementy):
        self.elementy = list(elementy)

    def count(self):
        return len(self.elementy)

    def nth(self, i):
        return self.elementy[i]

    @property
    def first(self):
        return self.elementy[0] if self.elementy else Brak()


class _Mysz:
    def wheel(self, *a):
        pass


class _Klawiatura:
    def __init__(self):
        self.napisane = []

    def type(self, tekst, **k):
        self.napisane.append(tekst)


class Strona:
    def __init__(self, pola=(), przyciski=(), wyjatek_goto=None, evaluate=None):
        self.pola = Zbior(pola)
        self.przyciski = set(przyciski)
        self.wyjatek_goto = wyjatek_goto
        self._evaluate = evaluate
        self.mouse = _Mysz()
        self.keyboard = _Klawiatura()
        self.zamknieta = False

    def goto(self, url, **k):
        if self.wyjatek_goto is not None:
            raise self.wyjatek_goto

    def wait_for_timeout(self, ms):
        pass

    def locator(self, selektor):
        return self.pola if "textarea" in selektor else Brak()

    def get_by_role(self, rola, name=None, exact=False):
        return Element() if name in self.przyciski else Brak()

    def evaluate(self, skrypt, *a):
        return self._evaluate

    def close(self):
        self.zamknieta = True


class _Sterownik:
    def __init__(self):
        self.zatrzymany = False

    def stop(self):
        self.zatrzymany = True


class _Przegladarka:
    def __init__(self):
        self.zamknieta = False

    def close(self):
        self.zamknieta = True


class _Kontekst:
    def __init__(self, strona):
        self.strona = strona

    def new_page(self):
        return self.strona


# Ostatnio wydane atrapy sterownika i przegladarki — sekcja 12 pyta ich, czy
# sprzatanie w ogole doszlo do skutku. Bez tego „wyciek" bylby niesprawdzalny.
_OSTATNIE = {}


def podepnij(strona, modul=None):
    m = modul or browser

    def polacz():
        st, prz = _Sterownik(), _Przegladarka()
        _OSTATNIE["sterownik"], _OSTATNIE["przegladarka"] = st, prz
        _OSTATNIE["strona"] = strona
        return st, prz, _Kontekst(strona)

    m.podlacz_sie = polacz
    return strona


# --- DZIENNIK NA BOKU --------------------------------------------------------
KATALOG = pathlib.Path(tempfile.mkdtemp(prefix="nia-dziennik-"))
browser.DZIENNIK = KATALOG / "dziennik.jsonl"
browser.wymagaj_sesji = lambda: None
browser.config.DRY_RUN = False           # inaczej `naprawde_wyslac` gasi wszystko


def wpisy():
    if not browser.DZIENNIK.exists():
        return []
    return [json.loads(w) for w in
            browser.DZIENNIK.read_text(encoding="utf-8").splitlines() if w.strip()]


def wyczysc():
    if browser.DZIENNIK.exists():
        browser.DZIENNIK.unlink()
    browser._W_SERII.clear()
    browser._OSTATNIA.clear()
    browser._POD_RZAD_ZLE.clear()


ADRES = "https://publikacja-c.example/p/przyklad"
TEKST = "Trzy zdania o czyms konkretnym."


def dopiero_po_wyslaniu(numer):
    """`potwierdz_komentarz` jest wolane DWA RAZY: przed pisaniem (czy juz tam
    nie wisi) i po klknieciu (czy weszlo). Atrapa musi to rozroznic, inaczej
    kazdy sukces wyglada jak duplikat i funkcja wychodzi przed napisaniem."""
    stan = {"przed": True}

    def pytaj(page, url, tekst):
        if stan["przed"]:
            stan["przed"] = False
            return None
        return numer

    return pytaj


def komentarz(strona, **atrapy):
    """Jedno wystawienie komentarza na atrapie. Zwraca wpisy dziennika."""
    podepnij(strona)
    browser.juz_sie_odezwalismy = atrapy.get(
        "juz", lambda page, url: False)
    browser.potwierdz_komentarz = atrapy.get(
        "potwierdz", lambda page, url, tekst: None)
    wynik = browser.wystaw_komentarz(ADRES, TEKST, wyslij=True)
    return wynik, wpisy()


print("=== 1. BRAK POLA KOMENTARZA TRAFIA DO DZIENNIKA ===")
# Wczesny return, ktory na produkcji zdarzyl sie dwa razy pierwszego dnia.
wyczysc()
w, lista = komentarz(Strona(pola=[]))
sprawdz("jest dokladnie jeden wpis", len(lista) == 1, lista)
sprawdz("i to NIEUDANY", bool(lista) and lista[0].get("udane") is False, lista)
sprawdz("z powodem wprost",
        bool(lista) and lista[0].get("powod") == "nie ma pola komentarza pod tym postem",
        lista)
sprawdz("z adresem — bez niego host nie policzy sie do niczego",
        bool(lista) and lista[0].get("gdzie") == ADRES, lista)
sprawdz("rodzaj to komentarz, wiec licznik go widzi",
        bool(lista) and lista[0].get("rodzaj") == "komentarz", lista)

print()
print("=== 2. WYJATEK TEZ ZOSTAWIA SLAD ===")
wyczysc()
w, lista = komentarz(Strona(wyjatek_goto=RuntimeError("Timeout 15000ms")))
sprawdz("wyjatek zapisany", len(lista) == 1, lista)
sprawdz("powod niesie typ i tresc bledu",
        bool(lista) and "RuntimeError" in str(lista[0].get("powod")), lista)
sprawdz("i nadal jest nieudany",
        bool(lista) and lista[0].get("udane") is False, lista)

print()
print("=== 3. BRAK PRZYCISKU WYSYLKI — NAJCZESTSZA AWARIA OBCEGO INTERFEJSU ===")
wyczysc()
w, lista = komentarz(Strona(pola=[Element()], przyciski=()))
sprawdz("wpisalismy tekst, ale nie bylo czym wyslac",
        w["wpisane"] is True and w["wyslane"] is False, w)
sprawdz("porazka w dzienniku", len(lista) == 1, lista)
sprawdz("powod nazwany po imieniu",
        bool(lista) and lista[0].get("powod") == "nie znalazlem przycisku wysylki",
        lista)

print()
print("=== 4. SUKCES ZAPISUJE SIE RAZ, NIE DWA ===")
# `finally` domyka tylko to, czego sciezka sukcesu nie zdazyla zapisac —
# inaczej kazdy udany komentarz liczylby sie podwojnie w dziennym budzecie.
wyczysc()
w, lista = komentarz(Strona(pola=[Element()], przyciski=("Post",)),
                     potwierdz=dopiero_po_wyslaniu(987654))
sprawdz("dokladnie jeden wpis", len(lista) == 1, lista)
sprawdz("udany", bool(lista) and lista[0].get("udane") is True, lista)
sprawdz("z numerem naszego komentarza",
        bool(lista) and lista[0].get("nasz_id") == 987654, lista)

print()
print("=== 5. POMINIETY KOMENTARZ NIE JEST KOMENTARZEM ===")
# `juz_sie_odezwalismy` oddaje True TAKZE wtedy, gdy nie odczytalo naszego id
# („nie wiem, czyli nie ryzykuje"). Zapisanie tego jako udanego komentarza
# wymyslaloby dzialanie, ktorego nie bylo, i zjadalo slot z dziennego licznika
# — jedynego, jaki dla komentarzy mamy.
wyczysc()
w, lista = komentarz(Strona(pola=[Element()], przyciski=("Post",)),
                     juz=lambda page, url: True)
sprawdz("pominiecie nie tworzy wpisu", lista == [], lista)
sprawdz("ale funkcja mowi, ze pominela", w.get("pominiete") is True, w)

print()
print("=== 6. SYGNALY, KTORE PRZEZ TO BYLY MARTWE, ZNOWU DZIALAJA ===")
wyczysc()
komentarz(Strona(pola=[]))
sprawdz("po pierwszej porazce licznik serii wynosi 1",
        browser.pod_rzad_nieudanych("komentarz") == 1,
        browser.pod_rzad_nieudanych("komentarz"))
komentarz(Strona(pola=[]))
sprawdz("po drugiej — 2, wiec `run.rytm` podwoi przerwe",
        browser.pod_rzad_nieudanych("komentarz") == 2,
        browser.pod_rzad_nieudanych("komentarz"))

# DWIE PORAZKI TO ZA MALO, JESLI NIE MOWIA NIC O HOSCIE.
# „Nie ma pola komentarza" znaczy, ze cos poszlo nie tak po drodze — moze
# u nich, moze u nas. Host skresla dopiero porazka PO KLKNIECIU. Bez tego
# rozroznienia dwa nasze timeouty zamykaly publikacje na zawsze, a zdjecie
# jej z listy wymagalo UDANEGO komentarza, ktorego zapora juz nie przepuszcza.
sprawdz("dwie porazki bez klikniecia NIE skreslaja hosta",
        "publikacja-c.example" not in browser.hosty_gdzie_komentarz_nie_wchodzi(),
        browser.hosty_gdzie_komentarz_nie_wchodzi())

# A teraz dwie porazki, ktore o hoscie mowia: przycisk byl, klik poszedl,
# a Substack komentarza nie pokazuje.
komentarz(Strona(pola=[Element()], przyciski=("Post",)))
komentarz(Strona(pola=[Element()], przyciski=("Post",)))
lista = wpisy()
sprawdz("wpis po klknieciu niesie `o_hoscie`",
        [w.get("o_hoscie") for w in lista][-1] is True, lista[-1:])
sprawdz("a wpis bez klikniecia niesie `o_hoscie` FALSE",
        [w.get("o_hoscie") for w in lista][0] is False, lista[:1])
martwe = browser.hosty_gdzie_komentarz_nie_wchodzi()
sprawdz("host po dwoch klknieciach bez potwierdzenia trafia na liste martwych",
        "publikacja-c.example" in martwe, martwe)

# Jedno udane wystawienie zeruje serie i zdejmuje host z listy.
komentarz(Strona(pola=[Element()], przyciski=("Post",)),
          potwierdz=dopiero_po_wyslaniu(111))
sprawdz("powodzenie zeruje serie porazek",
        browser.pod_rzad_nieudanych("komentarz") == 0,
        browser.pod_rzad_nieudanych("komentarz"))
sprawdz("i zdejmuje host z listy martwych",
        "publikacja-c.example" not in browser.hosty_gdzie_komentarz_nie_wchodzi(),
        browser.hosty_gdzie_komentarz_nie_wchodzi())

print()
print("=== 7. ODPOWIEDZ W WATKU — TA SAMA DZIURA ===")
wyczysc()
podepnij(Strona(wyjatek_goto=RuntimeError("Timeout 15000ms")))
# `None`, nie `False`: `potwierdz_odpowiedz` oddaje od 1 wrzesnia 2026
# NUMER naszej odpowiedzi albo `None`. Atrapa oddajaca `False` opisywala
# funkcje, ktorej juz nie ma.
browser.potwierdz_odpowiedz = lambda page, nid, tekst: None
browser.wystaw_odpowiedz(900000007, TEKST, wyslij=True)
lista = wpisy()
sprawdz("nieudana odpowiedz jest w dzienniku", len(lista) == 1, lista)
sprawdz("pod rodzajem `odpowiedz`",
        bool(lista) and lista[0].get("rodzaj") == "odpowiedz", lista)
sprawdz("z adresem notki",
        bool(lista) and lista[0].get("gdzie") == "note/c-900000007", lista)

# Ta sama funkcja obsluguje wejscie w CUDZA dyskusje i wtedy jest komentarzem
# dla licznika wolumenow — porazka musi trafic do tej samej kategorii.
wyczysc()
podepnij(Strona(wyjatek_goto=RuntimeError("Timeout 15000ms")))
browser.wystaw_odpowiedz(999, TEKST, wyslij=True, rodzaj="komentarz")
lista = wpisy()
sprawdz("wejscie w cudza dyskusje liczy sie jako komentarz",
        bool(lista) and lista[0].get("rodzaj") == "komentarz", lista)

print()
print("=== 8. ODPOWIEDZ POD NASZYM ARTYKULEM ===")
# Tu brak sladu bolal najbardziej: ktos napisal pod NASZYM tekstem i nie
# dostal odpowiedzi, a dziennik wygladal, jakbysmy nie probowali.
wyczysc()
podepnij(Strona(evaluate=-1))            # -1 = nie znalazlem przycisku odpowiedzi
browser.wystaw_odpowiedz_pod_artykulem(
    "https://your-handle.substack.com/p/tekst", "Ktos", TEKST, wyslij=True)
lista = wpisy()
sprawdz("porazka zapisana", len(lista) == 1, lista)
sprawdz("z rodzajem osobnym dla tej sciezki",
        bool(lista) and lista[0].get("rodzaj") == "odpowiedz_pod_artykulem", lista)
sprawdz("i z tym, komu nie odpowiedzielismy",
        bool(lista) and lista[0].get("komu") == "Ktos", lista)


# --- POLUBIENIA --------------------------------------------------------------
class Lajk:
    """Przycisk polubienia — atrapa, ktora umie oddac OBA zachowania Reacta.

    `zmienia`          — czy klik cokolwiek w przycisku zmienia.
    `w_dokumencie`     — czy wezel nadal wisi w DOM po klknieciu. False oddaje
                         to, co robi Playwright na wezle ODPIETYM: NIE RZUCA,
                         tylko czyta go dalej ze sterty JS i oddaje STARE
                         atrybuty. Dokladnie to zachowanie kontroler zarzucil
                         naszemu kodowi i dokladnie ono dawalo `po == przed`,
                         czyli twarde „nie udalo sie" przy polubieniu, ktore
                         weszlo. Skrypt, ktory sam pyta o `isConnected`, dostaje
                         tu `None`; skrypt bez tego pytania dostaje stara
                         wartosc — i wtedy test oblewa, o to chodzi.
    `kontekst_zyje`    — False oddaje drugie zachowanie: zniszczony kontekst
                         wykonania (nawigacja), przy ktorym `evaluate` NAPRAWDE
                         rzuca.

    Atrapa nie koduje juz zalozenia, ktorego nikt nie zmierzyl. Oba zachowania
    sa tu obok siebie i oba MUSZA konczyc sie „nie wiem".
    """

    def __init__(self, autor="Genie", zmienia=True, w_dokumencie=True,
                 kontekst_zyje=True):
        self.autor = autor
        self.zmienia = zmienia
        self.w_dokumencie = w_dokumencie
        self.kontekst_zyje = kontekst_zyje
        self.klikniety = False

    def is_visible(self):
        return True

    def scroll_into_view_if_needed(self, **k):
        pass

    def element_handle(self, **k):
        return self

    def click(self, **k):
        self.klikniety = True

    def _stan(self):
        return "po|klikniecie" if (self.klikniety and self.zmienia) else "przed"

    def evaluate(self, skrypt, *a):
        if "parentElement" in skrypt:            # pytanie o autora
            return {"href": "/@publikacja2", "tekst": self.autor}
        if not self.kontekst_zyje:               # nawigacja zabila kontekst
            raise RuntimeError("Execution context was destroyed")
        if not self.w_dokumencie:
            # Wezel odpiety, ale zywy. Odpowiada „nie wiem" TYLKO temu skryptowi,
            # ktory o to zapytal; kazdy inny dostaje stan sprzed podmiany.
            return None if "isConnected" in skrypt else "przed"
        return self._stan()


class StronaKanalu:
    def __init__(self, lajki):
        self.lajki = Zbior(lajki)
        self.zamknieta = False

    def goto(self, url, **k):
        pass

    def wait_for_timeout(self, ms):
        pass

    def get_by_role(self, rola, name=None, exact=False):
        return self.lajki if name == "Like" else Brak()

    def close(self):
        self.zamknieta = True


print()
print("=== 9. POLUBIENIE BEZ POTWIERDZENIA NIE JEST POLUBIENIEM ===")
wyczysc()
lajki = [Lajk(zmienia=True), Lajk(zmienia=False), Lajk(w_dokumencie=False)]
podepnij(StronaKanalu(lajki))
# ATRAPY PRZYCISKOW NIE MAJA TRESCI NOTKI, a filtr rewiru (`browser.w_rewirze`)
# bez tresci odrzuca przy niepustych znakach niszy — ktore w darmowym tescie
# przychodza z lokalnego `konfiguracja.toml` operatora. Ten test mierzy
# potwierdzanie klikniecia, nie temat: znaki puste jak w silniku bez kartridza.
import config  # noqa: E402
config.ZNAKI_NISZY = ()
w = browser.polub_w_kanale(3, wyslij=True)
lista = wpisy()
sprawdz("wszystkie trzy przyciski klikniete",
        all(l.klikniety for l in lajki), [l.klikniety for l in lajki])
sprawdz("policzone tylko dwa — ten, ktory sie nie drgnal, odpada",
        w["polubione"] == 2, w)
sprawdz("trzy wpisy, bo porazka tez jest wpisem", len(lista) == 3, lista)
udane = [x for x in lista if x.get("udane")]
sprawdz("dwa udane", len(udane) == 2, udane)
sprawdz("pierwsze POTWIERDZONE zmiana stanu",
        bool(udane) and udane[0].get("potwierdzone") is True, udane)
sprawdz("drugie zapisane jako niepotwierdzone, ale policzone",
        len(udane) > 1 and udane[1].get("potwierdzone") is False, udane)
zle = [x for x in lista if not x.get("udane")]
sprawdz("porazka nazwana po imieniu",
        bool(zle) and zle[0].get("powod") == "przycisk nie zmienil stanu po klknieciu",
        zle)
sprawdz("i nadal wiemy, czyj to byl wpis",
        bool(zle) and zle[0].get("komu") == "publikacja2", zle)

print()
print("=== 10. NIEPEWNOSC NA KORZYSC POLUBIENIA ===")
# Falszywe „nie udalo sie" zaniza jedyny licznik lajkow, jaki mamy, wiec
# nastepny przebieg bierze pelny dzienny przydzial od nowa. Falszywe „udalo
# sie" kosztuje jeden slot. Progi sa niesymetryczne swiadomie.
sprawdz("brak stanu PRZED -> nie wiem", browser.potwierdz_polubienie(
    Lajk(), None) is None)
sprawdz("zniszczony kontekst (wyjatek) -> nie wiem", browser.potwierdz_polubienie(
    Lajk(kontekst_zyje=False), "przed") is None)
sprawdz("stan bez zmian -> twarde NIE",
        browser.potwierdz_polubienie(Lajk(zmienia=False), "przed") is False)
klikniety = Lajk(zmienia=True)
klikniety.click()
sprawdz("stan zmieniony -> TAK",
        browser.potwierdz_polubienie(klikniety, "przed") is True)
sprawdz("uchwyt None nie wywraca odczytu",
        browser._stan_przycisku(None) is None)

# WEZEL ODPIETY OD DOKUMENTU, ALE ZYWY — sedno zarzutu kontrolera. Playwright
# na takim wezle nie rzuca; czyta go dalej i oddaje STARE atrybuty. Odczyt musi
# powiedziec „nie wiem", a nie „bez zmian" — inaczej polubienie, ktore weszlo,
# przepada razem ze slotem z dziennego przydzialu.
odpiety = Lajk(zmienia=True, w_dokumencie=False)
odpiety.click()
sprawdz("odpiety wezel -> `nie wiem`, NIE `bez zmian`",
        browser.potwierdz_polubienie(odpiety, "przed") is None,
        browser.potwierdz_polubienie(odpiety, "przed"))
sprawdz("odczyt stanu odpietego wezla oddaje None",
        browser._stan_przycisku(odpiety) is None,
        browser._stan_przycisku(odpiety))
# I odwrotnie: wezel W dokumencie nadal musi dawac twarda odpowiedz, inaczej
# uszczelnienie zamienilo by kazde polubienie w „nie wiem" i sekcja 9 bylaby
# pusta.
sprawdz("wezel w dokumencie nadal odpowiada twardo",
        browser.potwierdz_polubienie(Lajk(zmienia=False), "przed") is False)

print()
print("=== 11. KONTRDOWOD: NA KODZIE SPRZED POPRAWKI TO BY NIE PRZESZLO ===")
zrodlo = pathlib.Path("agent-v2/browser.py").read_text(encoding="utf-8")


def blok(nazwa):
    i = zrodlo.index("def %s(" % nazwa)
    return zrodlo[i:zrodlo.index("\ndef ", i + 10)]


def domkniecie(nazwa):
    b = blok(nazwa)
    return b[b.index("    finally:"):]


sprawdz("komentarz domyka zapis w `finally`",
        'dopisz_wynik("komentarz", wynik' in domkniecie("wystaw_komentarz"),
        "finally nadal tylko zamyka przegladarke")
sprawdz("odpowiedz domyka zapis w `finally`",
        "dopisz_wynik(rodzaj, wynik" in domkniecie("wystaw_odpowiedz"),
        "finally nadal tylko zamyka przegladarke")
sprawdz("odpowiedz pod artykulem domyka zapis w `finally`",
        'dopisz_wynik("odpowiedz_pod_artykulem", wynik' in
        domkniecie("wystaw_odpowiedz_pod_artykulem"),
        "finally nadal tylko zamyka przegladarke")

lajk = blok("polub_w_kanale")
sprawdz("nie ma juz zapisu polubienia zaraz po klknieciu",
        'kandydat.click(timeout=8000)\n                wynik["polubione"] += 1'
        not in zrodlo, "stary zapis bez potwierdzenia nadal w kodzie")
sprawdz("potwierdzenie stoi MIEDZY klknieciem a zapisem",
        lajk.index("kandydat.click")
        < lajk.index("potwierdz_polubienie(uchwyt, przed)")
        < lajk.index('zapisz_w_dzienniku("polubienie", udane=True'))
sprawdz("stan czytamy z uchwytu wezla, nie z lokatora po nazwie",
        "_uchwyt_wezla(kandydat)" in lajk)

# Like i Unlike wystepuja obok siebie w rzeczywistym kanale. Wyszukiwanie
# czesciowe cofaloby juz wykonane polubienie.
class KanalZPolubionym(StronaKanalu):
    def get_by_role(self, rola, name=None, exact=False):
        if name == "Like":
            return Zbior([nowe_polubienie] if exact else [juz_polubione, nowe_polubienie])
        return Brak()


wyczysc()
juz_polubione, nowe_polubienie = Lajk(), Lajk()
podepnij(KanalZPolubionym([juz_polubione, nowe_polubienie]))
wynik_lajka = browser.polub_w_kanale(1, wyslij=True)
sprawdz("juz polubiony wpis pozostaje polubiony", not juz_polubione.klikniety)
sprawdz("nowy wpis dostaje polubienie", nowe_polubienie.klikniety)
sprawdz("jedna nowa akcja w dzienniku", len(wpisy()) == 1 and wynik_lajka["polubione"] == 1)

# Restack zostaje nietkniety — ale z opisem otwartego ryzyka, nie w milczeniu.
restack = blok("restackuj_w_kanale")
sprawdz("restack ma jawna notatke o braku potwierdzenia",
        "OTWARTE, SWIADOMIE NIETKNIETE" in restack
        and 'zapisz_w_dzienniku("restack", udane=True' in restack,
        "albo zgadnieto potwierdzenie, albo znikl opis ryzyka")

# Nowe uszczelnienia, kazde z powodem opisanym w zrodle.
sprawdz("zapis w `finally` komentarza jest osloniety `try`",
        domkniecie("wystaw_komentarz").index("try:")
        < domkniecie("wystaw_komentarz").index('dopisz_wynik("komentarz"'),
        "zapis nadal moze zabrac sprzatanie")
sprawdz("odczyt stanu przycisku pyta o `isConnected`",
        "isConnected" in zrodlo.split("_STAN_PRZYCISKU = ")[1][:400],
        "skrypt nadal opiera sie na tym, ze cos rzuci")
sprawdz("dopisz_wynik klasyfikuje porazke polem `o_hoscie`",
        'szczegoly["o_hoscie"]' in blok("dopisz_wynik"),
        "porazka znowu nie mowi, o kim jest")
sprawdz("pamiec martwych hostow ma okno czasowe",
        "PAMIEC_MARTWYCH_HOSTOW_DNI" in zrodlo
        and "granica" in blok("hosty_gdzie_komentarz_nie_wchodzi"),
        "lista znowu czyta dziennik od poczatku dziejow")


# --- 12. ZAPIS W `finally` NIE MOZE ZABRAC SPRZATANIA -----------------------
def stary_browser(nazwa, *latki):
    """`browser.py` z odwrotna latka, wczytany jako OSOBNY modul.

    Kontrdowod odtwarzany, nie opisywany: ten sam scenariusz idzie raz przez
    kod z poprawka i raz przez kod bez niej, a test porownuje wynik.
    """
    import types

    src = pathlib.Path("agent-v2/browser.py").read_text(encoding="utf-8")
    for nowe, dawne in latki:
        assert src.count(nowe) >= 1, "latka odwrotna nie ma czego cofnac"
        src = src.replace(nowe, dawne)
    m = types.ModuleType(nazwa)
    m.__dict__["__name__"] = nazwa
    m.__dict__["__file__"] = "agent-v2/browser.py"
    exec(compile(src, "agent-v2/browser.py", "exec"), m.__dict__)
    m.DZIENNIK = browser.DZIENNIK
    m.wymagaj_sesji = lambda: None
    m.config.DRY_RUN = False
    return m


def sprzatanie(modul, tekst):
    """Puszcza `wystaw_komentarz` i oddaje, co zostalo posprzatane."""
    podepnij(Strona(pola=[Element()], przyciski=("Post",)), modul=modul)
    modul.juz_sie_odezwalismy = lambda page, url: False
    modul.potwierdz_komentarz = lambda page, url, t: None
    blad = None
    try:
        modul.wystaw_komentarz(ADRES, tekst, wyslij=True)
    except Exception as exc:
        blad = type(exc).__name__
    return (blad, _OSTATNIE["strona"].zamknieta,
            _OSTATNIE["przegladarka"].zamknieta,
            _OSTATNIE["sterownik"].zatrzymany)


print()
print("=== 12. ZLY ARGUMENT ZAPISU NIE MOZE ZOSTAWIC OTWARTEGO CHROME ===")
# `tekst`, ktory nie jest napisem, wywraca `len(tekst.split())` — a to wolanie
# stoi w `finally` PRZED `page.close()`. Zmierzone side-by-side ponizej:
# bez oslony `page.close()`, `browser.close()` i `p.stop()` NIE WYKONUJA SIE
# WCALE, czyli strona Chrome i proces sterownika ciekna na reszte przebiegu.
# Osiagalnosc z produkcji niska — ale to jest ta klasa wady, po ktorej agent
# zostawia po sobie kilkanascie procesow i nikt nie wie dlaczego.
wyczysc()
nowy = sprzatanie(browser, 12345)
print("    Z POPRAWKA:      blad=%s strona=%s przegladarka=%s sterownik=%s" % nowy)

wyczysc()
# Literal `[:1200]` MUSI byc taki sam jak w `browser.py`. Byl tu `[:300]`
# i latka odwrotna przestala miec co cofac w chwili, gdy podniesiono
# obciecie — czyli kontrdowod cicho przestal byc kontrdowodem.
bez_oslony = stary_browser(
    "browser_bez_oslony",
    ("""        try:
            if wyslij and not wynik.get("pominiete"):
                dopisz_wynik("komentarz", wynik, gdzie=url,
                             slow=len(tekst.split()), tekst=tekst[:1200],
                             nasz_id=wynik.get("id"), **(kontekst or {}))
        except Exception as exc:
            print("  (nie zapisalem komentarza do dziennika: %s)"
                  % type(exc).__name__, flush=True)
""",
     """        if wyslij and not wynik.get("pominiete"):
            dopisz_wynik("komentarz", wynik, gdzie=url,
                         slow=len(tekst.split()), tekst=tekst[:1200],
                         nasz_id=wynik.get("id"), **(kontekst or {}))
"""))
stary = sprzatanie(bez_oslony, 12345)
print("    BEZ OSLONY:      blad=%s strona=%s przegladarka=%s sterownik=%s" % stary)

sprawdz("z poprawka strona Chrome zostaje zamknieta", nowy[1] is True, nowy)
sprawdz("z poprawka przegladarka zostaje zamknieta", nowy[2] is True, nowy)
sprawdz("z poprawka sterownik zostaje zatrzymany", nowy[3] is True, nowy)
sprawdz("KONTRDOWOD: bez oslony wyjatek ucieka z `finally`",
        stary[0] == "AttributeError", stary)
sprawdz("KONTRDOWOD: i strona zostaje otwarta", stary[1] is False, stary)
sprawdz("KONTRDOWOD: i przegladarka zostaje otwarta", stary[2] is False, stary)
sprawdz("KONTRDOWOD: i sterownik nie jest zatrzymany", stary[3] is False, stary)

print()
print("=== 13. KONTRDOWOD: BEZ `isConnected` ODPIETY WEZEL DAWAL TWARDE NIE ===")
# Zarzut kontrolera brzmial: `ElementHandle.evaluate` na wezle ODPIETYM od
# dokumentu w Playwrighcie NIE RZUCA — wezel zyje w stercie JS i oddaje stare
# atrybuty. Nie zgadujemy, czy tak jest: usuwamy z kodu pytanie o `isConnected`
# i patrzymy, co wtedy wychodzi na atrapie, ktora takie zachowanie odtwarza.
bez_pytania = stary_browser(
    "browser_bez_isconnected",
    ("  if (!el.isConnected) return null;\n", ""))
odp1 = Lajk(zmienia=True, w_dokumencie=False)
odp1.click()
odp2 = Lajk(zmienia=True, w_dokumencie=False)
odp2.click()
print("    Z PYTANIEM: %r     BEZ PYTANIA: %r"
      % (browser.potwierdz_polubienie(odp1, "przed"),
         bez_pytania.potwierdz_polubienie(odp2, "przed")))
sprawdz("KONTRDOWOD: bez `isConnected` wychodzi twarde False",
        bez_pytania.potwierdz_polubienie(odp2, "przed") is False,
        bez_pytania.potwierdz_polubienie(odp2, "przed"))
sprawdz("a z pytaniem — `nie wiem`",
        browser.potwierdz_polubienie(odp1, "przed") is None)

print()
print("=== 14. KONTRDOWOD: BEZ `o_hoscie` NASZ TIMEOUT ZABIJAL HOST ===")
# Dokladnie scenariusz kontrolera: dwa wyjatki po NASZEJ stronie, dwa rozne
# posty, jeden host. Z poprawka host zyje, bez niej — jest martwy.
bez_klasyfikacji = stary_browser(
    "browser_bez_o_hoscie",
    ('        szczegoly["klikniete"] = bool(wynik.get("klikniete"))\n'
     '        szczegoly["o_hoscie"] = bool(wynik.get("klikniete")\n'
     '                                     and wynik.get("potwierdzenie_odpowiedzialo"))\n',
     ""),
    ('            elif w.get("o_hoscie")'
     ' and w.get("powod") == POWOD_HOST_NIE_POKAZUJE:\n', "            else:\n"))


def dwa_timeouty(modul):
    modul.DZIENNIK.unlink(missing_ok=True)
    modul._W_SERII.clear()
    modul._OSTATNIA.clear()
    modul._POD_RZAD_ZLE.clear()
    for adres, wyjatek in (("https://publikacja-c.example/p/a", TimeoutError("Timeout")),
                           ("https://publikacja-c.example/p/b",
                            RuntimeError("TargetClosedError"))):
        podepnij(Strona(wyjatek_goto=wyjatek), modul=modul)
        modul.juz_sie_odezwalismy = lambda page, url: False
        modul.potwierdz_komentarz = lambda page, url, t: None
        modul.wystaw_komentarz(adres, TEKST, wyslij=True)
    return modul.hosty_gdzie_komentarz_nie_wchodzi()


wyczysc()
z_poprawka = dwa_timeouty(browser)
bez_klasyfikacji.DZIENNIK = browser.DZIENNIK
wyczysc()
bez_niej = dwa_timeouty(bez_klasyfikacji)
print("    Z POPRAWKA: %s     BEZ NIEJ: %s" % (z_poprawka or set(), bez_niej))
sprawdz("dwa NASZE wyjatki nie skreslaja hosta", z_poprawka == set(), z_poprawka)
sprawdz("KONTRDOWOD: bez klasyfikacji host jest martwy",
        "publikacja-c.example" in bez_niej, bez_niej)
# I dowod, ze wpisy jednak powstaly — inaczej sekcja mierzylaby pusty dziennik.
sprawdz("a wpisy o obu porazkach i tak sa w dzienniku", len(wpisy()) == 2, wpisy())

wyczysc()
shutil.rmtree(KATALOG, ignore_errors=True)
print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
