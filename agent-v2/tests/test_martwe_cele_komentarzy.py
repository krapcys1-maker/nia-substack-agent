# -*- coding: utf-8 -*-
"""Host, u ktorego komentarz nigdy nie wchodzi, przestaje kosztowac.

TA SAMA WADA, CO PRZY ZRODLACH, w innym miejscu. `hosty_ktore_nigdy_nie_
dzialaly` powstalo, bo porazki pobierania byly zapisywane od poczatku i nigdy
nie wracaly do dyskoverii — `fda.gov` przepadl 3 razy na 3, a slot w limicie
dziesieciu adresow i tak byl na niego wydawany. Dziennik zapisuje nieudane
komentarze RAZEM Z ADRESEM od poczatku i nikt ich nie czytal.

ZMIERZONE 30 sierpnia 2026: 11 nieudanych komentarzy z 92 prob (12 procent),
7 odpowiedzi z 47. Sprawdzone u zrodla — 0 z 6 sprawdzalnych bylo jednak
opublikowanych, wiec to prawdziwa strata, nie blad rozpoznania. Kosztowalo
0,61 USD, czyli 92 procent calego przepalenia agenta.

DLACZEGO ZAPORA NIE WYSTARCZALA. `mozna_komentowac` pyta Substacka o pole
`write_comment_permissions` i przy watpliwosci odpowiada TAK — z uzasadnieniem
„blad w te strone kosztuje jedno nieudane klikniecie". To nieprawda: zapora
stoi PRZED `read_pages` i `comment_on`, wiec falszywe „tak" kosztuje trzy
warianty komentarza plus sprawdzenie faktow, okolo 2,3 centa.

PODZIAL PRACY ZOSTAJE CELOWY: optymizm wobec hosta NIEZNANEGO jest sluszny,
bo blad w druga strone zamyka agentowi usta wszedzie tam, gdzie pole ma
wartosc, ktorej nie znamy. Nowe jest tylko to, ze optymizm kosztuje jedna
probe, a nie dziesiata.

--- DRUGA POLOWA: SZKODY, KTORE ZROBILA POPRAWKA Z 31 SIERPNIA ---------------

Odkad porazki trafiaja do dziennika z KAZDEJ galezi `wystaw_komentarz`, sam
nieudany wpis z adresem przestal byc dowodem czegokolwiek o hoscie: timeout,
padnieta sesja i zamkniety Chrome zapisuja sie tak samo jak odmowa Substacka.
A ta lista jest TWARDA BRAMKA — `mozna_komentowac` odmawia przed proba,
`run.dzien` odsiewa cel przed ocena — wiec zamkniety host nie ma jak zdobyc
udanego komentarza, ktory by go zdjal. Petla domykala sie na zawsze, bo
dziennik nie jest nigdzie przycinany ani rotowany.

Dwa uszczelnienia, oba sprawdzane nizej i oba z kontrdowodem:

  - `o_hoscie` w kazdym nieudanym wpisie (sekcje 6-8): licza sie WYLACZNIE
    porazki po klknieciu w przycisk wysylki, czyli ta jedna klasa, ktora
    karmila liste przed 1 wrzesnia;
  - okno `PAMIEC_MARTWYCH_HOSTOW_DNI = 14` (sekcje 9-10): to jest jedyna droga
    ZEJSCIA z listy inna niz udany komentarz. Po zamknieciu hosta przestajemy
    do niego chodzic, wiec nowych wpisow nie ma — a gdy stare wypadna z okna,
    licznik spada ponizej progu i host wraca sam.

TEST NIE ZALEZY OD DZISIEJSZEJ DATY: wszystkie znaczniki czasu sa liczone
wzgledem `datetime.now(timezone.utc)` w chwili uruchomienia.

BEZ PYTESTA, z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_martwe_cele_komentarzy.py
"""
import json
import pathlib
import sys
import tempfile
import types
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "agent-v2")
import browser   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


KAT = pathlib.Path(tempfile.mkdtemp())
ORYG_DZIENNIK = browser.DZIENNIK
ORYG_PLATNE = browser.PLATNE_HOSTY


def zapisz(*wpisy):
    plik = KAT / "dziennik.jsonl"
    plik.write_text("\n".join(json.dumps(w) for w in wpisy), encoding="utf-8")
    browser.DZIENNIK = plik


def kiedy(dni_temu=0.0):
    """Znacznik czasu liczony OD TERAZ — test ma dzialac takze za rok."""
    return (datetime.now(timezone.utc)
            - timedelta(days=dni_temu)).isoformat(timespec="seconds")


def k(host, udane, rodzaj="komentarz", dni_temu=1.0, o_hoscie=None):
    """Wpis dziennika. `o_hoscie=None` = wpis STAREGO ksztaltu, bez tego pola."""
    w = {"kiedy": kiedy(dni_temu), "rodzaj": rodzaj, "udane": udane,
         "gdzie": "https://%s/p/cos" % host}
    if not udane and o_hoscie is not None:
        w["o_hoscie"] = o_hoscie
    return w


# Skrot na najczestszy przypadek: porazka, ktora NAPRAWDE mowi o hoscie.
#
# `powod` NIE JEST OZDOBA. Wpis produkcyjny z `o_hoscie=True` zawsze niesie
# wlasnie ten powod — inne powody znacza wyjatek po naszej stronie, a takiego
# wpisu czytelnik nie liczy (patrz `hosty_gdzie_komentarz_nie_wchodzi`).
# Atrapa bez `powod` udawalaby ksztalt, ktory w dzienniku nie wystepuje.
def zle(host, dni_temu=1.0):
    w = k(host, False, dni_temu=dni_temu, o_hoscie=True)
    w["powod"] = browser.POWOD_HOST_NIE_POKAZUJE
    return w


try:
    print("=== 1. DWIE PORAZKI I ZERO SUKCESOW ZDEJMUJA HOST ===")
    zapisz(zle("slowboring.com"), zle("slowboring.com"))
    sprawdz("host z dwiema porazkami odpada",
            "slowboring.com" in browser.hosty_gdzie_komentarz_nie_wchodzi(),
            browser.hosty_gdzie_komentarz_nie_wchodzi())

    print()
    print("=== 2. JEDNA PORAZKA TO ZA MALO ===")
    # Prog dwoch prob, nie jednej — tak samo jak przy zrodlach: jedno
    # niepowodzenie to awaria po drugiej stronie, dwa z rzedu to wlasciwosc
    # hosta. Skreslanie po pierwszej pomylce zamykaloby agentowi usta.
    zapisz(zle("nowy.com"))
    sprawdz("po jednej probie host zostaje",
            "nowy.com" not in browser.hosty_gdzie_komentarz_nie_wchodzi())

    print()
    print("=== 3. JEDEN SUKCES KASUJE HOST Z LISTY ===")
    # Wydawca moze zmienic ustawienia. Lista ma pamietac, kto nas nie wpuszcza,
    # a nie karac dozywotnio — jedno udane wystawienie odblokowuje host samo.
    zapisz(zle("czasem.com"), zle("czasem.com"), k("czasem.com", True))
    sprawdz("host z jednym sukcesem wraca",
            "czasem.com" not in browser.hosty_gdzie_komentarz_nie_wchodzi(),
            browser.hosty_gdzie_komentarz_nie_wchodzi())

    print()
    print("=== 4. NOTKI SIE NIE LICZA ===")
    # Pod notkami komentuje kazdy i nie ma tam hosta w tym sensie. Wpis notki
    # ma w `gdzie` cos w rodzaju "note/c-123", nie adres.
    zapisz({"kiedy": kiedy(1), "rodzaj": "komentarz", "udane": False,
            "o_hoscie": True, "gdzie": "note/c-322783482"},
           {"kiedy": kiedy(1), "rodzaj": "komentarz", "udane": False,
            "o_hoscie": True, "gdzie": "note/c-322783483"})
    sprawdz("wpisy notek nie tworza martwego hosta",
            browser.hosty_gdzie_komentarz_nie_wchodzi() == set(),
            browser.hosty_gdzie_komentarz_nie_wchodzi())

    print()
    print("=== 5. TYLKO KOMENTARZE, NIE INNE RODZAJE ===")
    zapisz(zle("inne.com")  | {"rodzaj": "polubienie"},
           zle("inne.com") | {"rodzaj": "polubienie"})
    sprawdz("nieudane polubienia nie blokuja komentowania",
            "inne.com" not in browser.hosty_gdzie_komentarz_nie_wchodzi())

    print()
    print("=== 6. NASZA AWARIA NIE JEST WADA HOSTA ===")
    # SCENARIUSZ KONTROLERA, odtworzony na wpisach: dwa razy padlismy sami
    # (timeout, zamkniety Chrome), dwa rozne posty, jeden host. Zanim doszlo
    # rozroznienie, dawalo to {'slowboring.com'} i `mozna_komentowac` = False
    # — czyli publikacje z pomiaru 30 sierpnia agent skreslal za WLASNE awarie.
    zapisz(k("slowboring.com", False, o_hoscie=False),
           k("slowboring.com", False, o_hoscie=False))
    sprawdz("dwa nasze wyjatki nie skreslaja hosta",
            browser.hosty_gdzie_komentarz_nie_wchodzi() == set(),
            browser.hosty_gdzie_komentarz_nie_wchodzi())
    # Mieszanka: jedna nasza awaria plus jedna odmowa hosta to nadal JEDNA
    # przeslanka o hoscie, czyli za malo.
    zapisz(k("mieszane.com", False, o_hoscie=False), zle("mieszane.com"))
    sprawdz("jedna nasza awaria + jedna odmowa hosta to wciaz za malo",
            "mieszane.com" not in browser.hosty_gdzie_komentarz_nie_wchodzi(),
            browser.hosty_gdzie_komentarz_nie_wchodzi())

    print()
    print("=== 7. STARE WPISY, BEZ POLA `o_hoscie`, NIE LICZA SIE ===")
    # Decyzja, nie przeoczenie. Przed 1 wrzesnia zapis stal wylacznie w galezi
    # „kliknelismy i nie potwierdzilo", wiec kuszace bylo uznac stary wpis za
    # dowod na hosta. Ale poprawka lezala w drzewie roboczym, zanim ktokolwiek
    # ja przejrzal — czesc wpisow bez tego pola moze juz byc zwyklym timeoutem,
    # a z samego wpisu tych dwoch zrodel nie odroznimy. Uznanie ich za dowod
    # odtworzyloby wade na danych, ktore juz leza na dysku.
    zapisz(k("stary.com", False), k("stary.com", False))
    sprawdz("dwa wpisy starego ksztaltu nie skreslaja hosta",
            "stary.com" not in browser.hosty_gdzie_komentarz_nie_wchodzi(),
            browser.hosty_gdzie_komentarz_nie_wchodzi())
    # Koszt tej ostroznosci jest policzalny: JEDNA dodatkowa proba na host.
    # Po niej powstaje wpis nowego ksztaltu i wystarczy jeszcze jeden.
    zapisz(k("stary.com", False), k("stary.com", False),
           zle("stary.com"), zle("stary.com"))
    sprawdz("ale dwa nowe wpisy juz wystarcza",
            "stary.com" in browser.hosty_gdzie_komentarz_nie_wchodzi(),
            browser.hosty_gdzie_komentarz_nie_wchodzi())

    print()
    print("=== 8. OKNO CZASOWE: WPIS SPRZED ROKU NIC NIE BLOKUJE ===")
    print("    okno = %d dni" % browser.PAMIEC_MARTWYCH_HOSTOW_DNI)
    zapisz(zle("dawno.com", dni_temu=365), zle("dawno.com", dni_temu=364))
    sprawdz("dwie porazki sprzed roku nie blokuja dzis",
            "dawno.com" not in browser.hosty_gdzie_komentarz_nie_wchodzi(),
            browser.hosty_gdzie_komentarz_nie_wchodzi())
    # Granica liczona od TERAZ, nie od stalej daty.
    okno = browser.PAMIEC_MARTWYCH_HOSTOW_DNI
    zapisz(zle("swieze.com", dni_temu=okno - 1),
           zle("swieze.com", dni_temu=okno - 0.5))
    sprawdz("dwie porazki tuz PRZED granica nadal blokuja",
            "swieze.com" in browser.hosty_gdzie_komentarz_nie_wchodzi(),
            browser.hosty_gdzie_komentarz_nie_wchodzi())
    zapisz(zle("zbyt_stare.com", dni_temu=okno + 1),
           zle("zbyt_stare.com", dni_temu=okno + 2))
    sprawdz("te same dwie porazki tuz ZA granica juz nie",
            "zbyt_stare.com" not in browser.hosty_gdzie_komentarz_nie_wchodzi(),
            browser.hosty_gdzie_komentarz_nie_wchodzi())
    # Sukces tez sie starzeje: stare powodzenie nie moze unieważnić swiezej
    # odmowy, bo wydawca mogl w miedzyczasie zamknac komentarze.
    zapisz(k("zmienil.com", True, dni_temu=okno + 5),
           zle("zmienil.com", dni_temu=1), zle("zmienil.com", dni_temu=2))
    sprawdz("stary sukces nie ratuje hosta, ktory dzis odmawia",
            "zmienil.com" in browser.hosty_gdzie_komentarz_nie_wchodzi(),
            browser.hosty_gdzie_komentarz_nie_wchodzi())

    print()
    print("=== 9. Z LISTY DA SIE ZEJSC BEZ UDANEGO KOMENTARZA ===")
    # To jest sedno: wejscie na liste BLOKUJE proby, wiec droga wyjscia przez
    # „udany komentarz" jest niedostepna. Okno jest jedyna, jaka zostaje.
    # Odtwarzamy caly cykl na jednym hoscie: martwy dzis -> po wygasnieciu
    # wpisow zywy, bez ani jednego nowego dzialania z naszej strony.
    zapisz(zle("wraca.com", dni_temu=0.1), zle("wraca.com", dni_temu=0.2))
    teraz = browser.hosty_gdzie_komentarz_nie_wchodzi()
    sprawdz("dzis host jest zamkniety", "wraca.com" in teraz, teraz)
    sprawdz("i zapora go NIE wpuszcza",
            browser.mozna_komentowac("https://wraca.com/p/x") is False)
    # Te same dwa wpisy, tylko starsze o cale okno. Zadnego nowego dzialania.
    zapisz(zle("wraca.com", dni_temu=okno + 0.1),
           zle("wraca.com", dni_temu=okno + 0.2))
    pozniej = browser.hosty_gdzie_komentarz_nie_wchodzi()
    sprawdz("po wygasnieciu okna host wraca sam", "wraca.com" not in pozniej,
            pozniej)

    print()
    print("=== 10. HOST Z `www.` — ZAPORA I DZIENNIK MUSZA SIE ZGADZAC ===")
    # Cala pamiec martwych hostow stoi na tym, ze klucz z dziennika i klucz
    # z zapory powstaja TAK SAMO. `hosty_gdzie_komentarz_nie_wchodzi` bierze
    # surowe `netloc.lower()`, bez zdejmowania `www.`, i dokladnie to samo robi
    # `mozna_komentowac` oraz sito w `run.dzien`. Nikt tego dotad nie dotknal
    # zadnym adresem z `www.`, a to na tym stoi zdanie z komentarza w `run.py`:
    # „inna normalizacja odsialaby tutaj co innego, niz odrzuci zapora".
    zapisz(zle("www.malone.news"), zle("www.malone.news"))
    lista = browser.hosty_gdzie_komentarz_nie_wchodzi()
    sprawdz("klucz z dziennika zachowuje `www.`", "www.malone.news" in lista,
            lista)
    sprawdz("zapora odrzuca adres z `www.`",
            browser.mozna_komentowac("https://www.malone.news/p/x") is False)
    # Adres bez `www.` to dla obu stron INNY host — i to jest spojne, nie
    # przypadkowe: skoro zapora i sito licza tak samo, nigdy sie nie rozjada.
    # Nic nie tracimy, bo Substack serwuje publikacje pod jedna forma adresu,
    # a my bierzemy adresy z jego wlasnych odpowiedzi.
    sprawdz("adres bez `www.` nie dziedziczy blokady (zapora i sito licza tak samo)",
            "malone.news" not in lista, lista)

    print()
    print("=== 11. PAMIEC PLATNYCH HOSTOW ZDEJMUJE `www.` — I W OBIE STRONY ===")
    # Tu normalizacja jest ODWROTNA i tez nikt jej nie dotykal adresem z `www.`.
    # `zapamietaj_platny_host` i `zapomnij_platny_host` robia
    # `.removeprefix("www.")`, a sito platnych w `run.dzien` — tak samo.
    browser.PLATNE_HOSTY = KAT / "platne.json"
    browser.PLATNE_HOSTY.write_text("{}", encoding="utf-8")
    browser.zapamietaj_platny_host("www.thebignewsletter.com", "only_paid")
    platne = browser.hosty_tylko_dla_placacych()
    sprawdz("zapamietany host traci `www.`",
            platne == {"thebignewsletter.com"}, platne)
    browser.zapomnij_platny_host("www.thebignewsletter.com")
    sprawdz("i zdejmuje sie go tez adresem z `www.`",
            browser.hosty_tylko_dla_placacych() == set(),
            browser.hosty_tylko_dla_placacych())

    print()
    print("=== 12. KONTRDOWOD: BEZ TYCH DWOCH RZECZY WYCHODZI CO INNEGO ===")
    # Odwrotna latka na zrodle `browser.py`, wczytanym jako osobny modul.
    # Ten sam dziennik idzie raz przez kod z poprawka i raz przez kod bez niej.
    zrodlo = pathlib.Path("agent-v2/browser.py").read_text(encoding="utf-8")

    def bez(nazwa, *latki):
        src = zrodlo
        for nowe, dawne in latki:
            sprawdz("latka odwrotna ma co cofnac: %s" % nazwa,
                    src.count(nowe) >= 1, "0 trafien")
            src = src.replace(nowe, dawne)
        m = types.ModuleType(nazwa)
        m.__dict__["__name__"] = nazwa
        m.__dict__["__file__"] = "agent-v2/browser.py"
        exec(compile(src, "agent-v2/browser.py", "exec"), m.__dict__)
        m.DZIENNIK = browser.DZIENNIK
        return m

    bez_okna = bez("browser_bez_okna",
                   ("            if kiedy < granica:\n                continue\n",
                    ""))
    bez_klas = bez("browser_bez_klasyfikacji",
                   ('            elif w.get("o_hoscie")'
                    ' and w.get("powod") == POWOD_HOST_NIE_POKAZUJE:\n',
                    "            else:\n"))

    # (a) wpis sprzed roku
    zapisz(zle("dawno.com", dni_temu=365), zle("dawno.com", dni_temu=364))
    print("    sprzed roku — z oknem: %s   bez okna: %s"
          % (browser.hosty_gdzie_komentarz_nie_wchodzi() or set(),
             bez_okna.hosty_gdzie_komentarz_nie_wchodzi()))
    sprawdz("KONTRDOWOD: bez okna wpis sprzed roku blokuje dzis",
            "dawno.com" in bez_okna.hosty_gdzie_komentarz_nie_wchodzi(),
            bez_okna.hosty_gdzie_komentarz_nie_wchodzi())

    # (b) nasze wlasne awarie
    zapisz(k("slowboring.com", False, o_hoscie=False),
           k("slowboring.com", False, o_hoscie=False))
    print("    nasze awarie — z klasyfikacja: %s   bez niej: %s"
          % (browser.hosty_gdzie_komentarz_nie_wchodzi() or set(),
             bez_klas.hosty_gdzie_komentarz_nie_wchodzi()))
    sprawdz("KONTRDOWOD: bez klasyfikacji nasz timeout zabija host",
            "slowboring.com" in bez_klas.hosty_gdzie_komentarz_nie_wchodzi(),
            bez_klas.hosty_gdzie_komentarz_nie_wchodzi())

    # (c) stare wpisy — bez klasyfikacji zostaly by uznane za wade hosta
    zapisz(k("stary.com", False), k("stary.com", False))
    sprawdz("KONTRDOWOD: bez klasyfikacji stary wpis tez zabija host",
            "stary.com" in bez_klas.hosty_gdzie_komentarz_nie_wchodzi(),
            bez_klas.hosty_gdzie_komentarz_nie_wchodzi())

    print()
    print("=== 13. ZAPORA NAPRAWDE Z NIEJ KORZYSTA ===")
    src = pathlib.Path("agent-v2/browser.py").read_text(encoding="utf-8")
    poczatek = src.find("def mozna_komentowac")
    ciało = src[poczatek:poczatek + 1600]
    sprawdz("mozna_komentowac pyta o pamiec hostow",
            "hosty_gdzie_komentarz_nie_wchodzi()" in ciało, ciało[:300])
    sprawdz("i robi to PRZED wejsciem do sieci",
            ciało.find("hosty_gdzie_komentarz_nie_wchodzi()")
            < ciało.find("wymagaj_sesji()"),
            "kolejnosc odwrotna")
    sprawdz("okno jest nazwana stala, nie liczba w locie",
            "PAMIEC_MARTWYCH_HOSTOW_DNI = 14" in src, "okno zmienione bez opisu")
finally:
    browser.DZIENNIK = ORYG_DZIENNIK
    browser.PLATNE_HOSTY = ORYG_PLATNE

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
