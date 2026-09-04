"""Kolejka promocji: trzy notki na artykul, po jednej dziennie, NAJSWIEZSZY pierwszy.

Decyzja wlasciciela z 20 sierpnia 2026: „promocja ma byc jedna notka po
artykule dziennie, trzy dni z rzedu".

Wczesniej bylo piec notek i kolejka szla w kolejnosci WSTAWIANIA. Skutek widac
bylo na zywych danych: artykul opublikowany 19 sierpnia stal w pliku za dwoma
starszymi, ktore nie wybraly jeszcze swoich dni, wiec pierwsza notke promujaca
dostalby okolo 29 sierpnia — z linkiem zimnym i tekstem dawno zepchnietym w dol
kanalu. Slowo „po artykule" znaczy zaraz po nim.

Przy okazji wyszla druga rzecz, ktorej nie szukalem. Warunek „ten artykul byl
juz dzis promowany" tylko POMIJAL go i szedl dalej po liscie. Funkcja jest
wolana raz na przebieg, a przebiegow jest piec dziennie — wiec kolejne
cztery przebiegi mogly brac nastepne artykuly z kolejki i tego samego dnia
wystawiac dalsze notki promujace. Nigdy sie to nie ujawnilo, bo kolejka nie
byla dosc pelna. Regula mowi „jedna dziennie" i to jest caly dzien, nie
jeden wiersz pliku.
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import config   # noqa: E402
import wlasna_konfiguracja  # noqa: E402
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


# Asercje o DOSTARCZONYCH wartosciach, pomijane widocznie,
# gdy operator ma wlasne w `konfiguracja.toml`.
sprawdz_nasze = wlasna_konfiguracja.tylko_nasze(sprawdz)


KAT = pathlib.Path(tempfile.mkdtemp())
ORYG = stages.PROMOCJA
stages.PROMOCJA = KAT / "promocja.json"


def ustaw(*wpisy):
    """Kolejka w kolejnosci WSTAWIANIA: pierwszy argument = najstarszy."""
    stages.PROMOCJA.write_text(json.dumps(list(wpisy), ensure_ascii=False),
                               encoding="utf-8")


def _dzis(przesuniecie=0):
    from datetime import datetime, timedelta, timezone
    return (datetime.now(timezone.utc)
            + timedelta(days=przesuniecie)).strftime("%Y-%m-%d")


def wpis(tytul, wystawione=0, ostatnia=None, dodane=None):
    # `dodane` domyslnie DZISIAJ: te przypadki badaja kolejnosc i liczniki, a
    # nie okno waznosci, wiec maja byc swieze. Okno ma wlasna sekcje nizej.
    return {"url": "https://x/p/%s" % tytul.lower().replace(" ", "-"),
            "tytul": tytul, "tekst": "tresc", "wystawione": wystawione,
            "ostatnia": ostatnia,
            "dodane": dodane if dodane is not None else _dzis()}


try:
    print("=== 1. TRZY, NIE PIEC ===")
    sprawdz_nasze("NOTEK_PROMUJACYCH = 3", config.NOTEK_PROMUJACYCH == 3,
            config.NOTEK_PROMUJACYCH)

    print()
    print("=== 2. NAJSWIEZSZY IDZIE PIERWSZY ===")
    # Doslownie stan produkcji z 19 sierpnia: dwa starsze bez ani jednej notki,
    # swiezy artykul dopisany na koncu.
    ustaw(wpis("Example Article Three", wystawione=3),
          wpis("Example Article Nine"),
          wpis("The Clock"),
          wpis("The Bottle"))
    w = stages.artykul_do_promocji()
    sprawdz("wybrany jest NAJSWIEZSZY", w and w["tytul"] == "The Bottle",
            w and w["tytul"])

    # KONTRDOWOD: stary sposob (kolejnosc wstawiania) wzialby Example Article Nine,
    # czyli tekst sprzed dwoch dni. Bez tego test nie odroznialby wersji.
    stary = next((a for a in stages.wczytaj_promocje()
                  if a.get("wystawione", 0) < config.NOTEK_PROMUJACYCH), None)
    sprawdz("stary sposob wzialby starszy tekst (test rozroznia)",
            stary and stary["tytul"] == "Example Article Nine", stary and stary["tytul"])

    print()
    print("=== 3. TYLE DNI Z RZEDU NA TYM SAMYM ARTYKULE, ILE MOWI KONFIGURACJA ===")
    ustaw(wpis("The Bottle"))
    dni = []
    # ILE DNI — Z KONFIGURACJI, NIE Z LICZBY WPISANEJ W TESCIE. Stalo tu
    # `range(4)` i porownanie z trojka, wiec test twierdzil „trzy dni"
    # zamiast „dokladnie tyle, ile mowi NOTEK_PROMUJACYCH". Po ustawieniu
    # dwoch oblewal, chociaz kod dzialal poprawnie — a wlasnie ta wlasnosc
    # kodu warto pilnowac i jest prawdziwa dla kazdej wartosci.
    ile_dni = config.NOTEK_PROMUJACYCH
    for _ in range(ile_dni + 1):
        w = stages.artykul_do_promocji()
        if w is None:
            dni.append(None)
            continue
        dni.append(w["tytul"])
        stages.odhacz_promocje(w["url"])
        # UPLYW DOBY. `odhacz_promocje` stempluje dzisiejsza date, a nowy
        # warunek „czy cokolwiek szlo dzis" porownuje wlasnie z dzisiejsza —
        # wiec zeby zasymulowac nastepny dzien, cofamy stempel w przeszlosc.
        # To jedyna rzecz, ktora tu udajemy: licznik `wystawione` rosnie
        # naprawde i to on ma zatrzymac promocje po trzecim dniu.
        dane = stages.wczytaj_promocje()
        for a in dane:
            a["ostatnia"] = "2026-01-01"
        stages.PROMOCJA.write_text(json.dumps(dane, ensure_ascii=False),
                                   encoding="utf-8")
    print("    kolejne dni: %s" % dni)
    sprawdz("promowany przez DOKLADNIE %d dni" % ile_dni,
            dni[:ile_dni] == ["The Bottle"] * ile_dni, dni)
    sprawdz("a nastepnego juz nie", dni[ile_dni] is None, dni[ile_dni])
    licznik = stages.wczytaj_promocje()[0]["wystawione"]
    sprawdz("licznik doszedl do %d" % ile_dni, licznik == ile_dni, licznik)

    print()
    print("=== 4. JEDNA NA DOBE ZNACZY JEDNA, NIE JEDNA NA ARTYKUL ===")
    # Piec przebiegow dziennie wola te funkcje piec razy. Gdy pierwszy juz
    # wystawil notke, pozostale maja MILCZEC — nawet jesli w kolejce czeka inny
    # artykul z niewybranymi dniami.
    from datetime import datetime, timezone   # noqa: E402
    dzis = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ustaw(wpis("Starszy", wystawione=1),
          wpis("Nowszy", wystawione=1, ostatnia=dzis))
    w = stages.artykul_do_promocji()
    sprawdz("po dzisiejszej notce nie ma drugiej", w is None,
            w and w["tytul"])

    # KONTRDOWOD: stary warunek tylko pomijal wiersz, wiec oddalby „Starszy".
    dane = stages.wczytaj_promocje()
    po_staremu = next((a for a in dane
                       if a.get("wystawione", 0) < config.NOTEK_PROMUJACYCH
                       and a.get("ostatnia") != dzis), None)
    sprawdz("stary sposob wystawilby DRUGA notke tego dnia (test rozroznia)",
            po_staremu and po_staremu["tytul"] == "Starszy",
            po_staremu and po_staremu["tytul"])

    print()
    print("=== 5. PRZYPADKI BRZEGOWE ===")
    ustaw()
    sprawdz("pusta kolejka nie wywala", stages.artykul_do_promocji() is None)
    stages.PROMOCJA.unlink(missing_ok=True)
    sprawdz("brak pliku nie wywala", stages.artykul_do_promocji() is None)
    ustaw(wpis("Wyczerpany", wystawione=3), wpis("Tez", wystawione=5))
    sprawdz("wszystkie wyczerpane -> nic", stages.artykul_do_promocji() is None)

    print()
    print("=== 6. NOWY ARTYKUL PRZEJMUJE KOLEJKE OD ZARAZ ===")
    # Publikacja w trakcie trzech dni starszego tekstu: nowy jest swiezszy,
    # wiec od nastepnego dnia promujemy jego. To jest wybor, nie usterka —
    # zimny link nie zyskuje na czekaniu, a swiezy traci.
    ustaw(wpis("Wczorajszy", wystawione=1))
    stages.zapisz_do_promocji("https://x/p/dzisiejszy", "Dzisiejszy", "tresc")
    w = stages.artykul_do_promocji()
    sprawdz("nowy artykul wchodzi przed niedokonczony starszy",
            w and w["tytul"] == "Dzisiejszy", w and w["tytul"])

    print()
    print("=== 7. OKNO WAZNOSCI: STARY ARTYKUL PRZESTAJE BYC PROMOWANY ===")
    # Zmierzone 26 sierpnia na produkcji. Konto zmienilo temat, ale w kolejce
    # zostaly cztery teksty z poprzedniej epoki, dwa z niewybranymi dniami.
    # Nic ich nie usuwalo, bo jedynym warunkiem wyjscia bylo wybranie trzech
    # notek. Po wyczerpaniu biezacego artykulu kanal wystawilby notke
    # promujaca tekst sprzed tygodnia, o czym innym niz pisze dzisiaj.
    sprawdz_nasze("OKNO_PROMOCJI_DNI istnieje", config.OKNO_PROMOCJI_DNI == 7,
            getattr(config, "OKNO_PROMOCJI_DNI", "brak"))

    ustaw(wpis("Stary artykul", wystawione=1,
               dodane=_dzis(-config.OKNO_PROMOCJI_DNI - 1)))
    sprawdz("artykul spoza okna nie jest promowany",
            stages.artykul_do_promocji() is None,
            (stages.artykul_do_promocji() or {}).get("tytul"))

    # KONTRDOWOD: przed poprawka jedynym warunkiem bylo `wystawione`, wiec ten
    # sam wpis zostalby wybrany. Bez tego sprawdzenia test nie odrozniac wersji.
    po_staremu = next((a for a in reversed(stages.wczytaj_promocje())
                       if a.get("wystawione", 0) < config.NOTEK_PROMUJACYCH),
                      None)
    sprawdz("stary sposob wystawilby stary artykul (test rozroznia)",
            po_staremu and po_staremu["tytul"] == "Stary artykul",
            po_staremu and po_staremu["tytul"])

    # GRANICA JEST WLACZAJACA: ostatni dzien okna jeszcze promuje.
    ustaw(wpis("Ostatni dzien", dodane=_dzis(-config.OKNO_PROMOCJI_DNI)))
    w = stages.artykul_do_promocji()
    sprawdz("w ostatnim dniu okna jeszcze promujemy",
            w and w["tytul"] == "Ostatni dzien", w and w["tytul"])

    # WPIS BEZ `dodane` pochodzi sprzed tej reguly — traktujemy jak stary.
    stary_format = {"url": "https://x/p/legacy", "tytul": "Bez daty",
                    "tekst": "tresc", "wystawione": 0, "ostatnia": None}
    ustaw(stary_format)
    sprawdz("wpis bez `dodane` nie jest promowany",
            stages.artykul_do_promocji() is None,
            (stages.artykul_do_promocji() or {}).get("tytul"))

    # ...ale swiezy artykul dopisany OBOK niego nadal dziala. Okno ma odcinac
    # przeterminowane, nie zatrzymywac kolejki.
    ustaw(stary_format)
    stages.zapisz_do_promocji("https://x/p/swiezy", "Swiezy", "tresc")
    w = stages.artykul_do_promocji()
    sprawdz("swiezy obok przeterminowanego dziala",
            w and w["tytul"] == "Swiezy", w and w["tytul"])
    sprawdz("i zapis stempluje `dodane`",
            stages.wczytaj_promocje()[-1].get("dodane") == _dzis(),
            stages.wczytaj_promocje()[-1].get("dodane"))

    print()
    print("=== 8. JEDNO NIE OD FAKTOW ZDEJMUJE ARTYKUL NA STALE ===")
    # Zmierzone na zywo. Notka promujaca „Example Article One" odpadla
    # o 21:44 przy 13 wyszukiwaniach — glowna teza artykulu okazala sie
    # nieprawdziwa. Werdykt wyrzucono. O 00:43 nastepny przebieg napisal
    # INNA notke o tym samym, dostal 22 wyszukiwania i PRZEPUSCIL. Falsz
    # wyszedl w swiat. Bramka losowa, ktora wraca nazajutrz po nowe losowanie,
    # jest tylko zwloka przed przepuszczeniem.
    ustaw(wpis("Watermark"))
    przed = stages.artykul_do_promocji()
    sprawdz("przed zakwestionowaniem artykul jest w kolejce",
            przed and przed["tytul"] == "Watermark", przed and przed["tytul"])

    stages.zakwestionuj_promocje(przed["url"], "centralna teza jest bledna")
    sprawdz("po zakwestionowaniu nie wraca",
            stages.artykul_do_promocji() is None,
            (stages.artykul_do_promocji() or {}).get("tytul"))

    zapis = stages.wczytaj_promocje()[0]
    sprawdz("powod zostaje zapisany",
            "bledna" in str(zapis.get("powod_zakwestionowania")),
            zapis.get("powod_zakwestionowania"))
    sprawdz("i data tez", bool(zapis.get("zakwestionowany")),
            zapis.get("zakwestionowany"))

    # KONTRDOWOD: przed poprawka liczyly sie tylko `wystawione` i okno, wiec ten
    # sam wpis zostalby wybrany nastepnego dnia — i to jest dokladnie to, co
    # sie stalo na produkcji.
    po_staremu = next((a for a in reversed(stages.wczytaj_promocje())
                       if a.get("wystawione", 0) < config.NOTEK_PROMUJACYCH
                       and str(a.get("dodane") or "") >= _dzis(-config.OKNO_PROMOCJI_DNI)),
                      None)
    sprawdz("stary sposob promowalby go dalej (test rozroznia)",
            po_staremu and po_staremu["tytul"] == "Watermark",
            po_staremu and po_staremu["tytul"])

    # Zakwestionowanie NIE moze zatrzymywac calej kolejki.
    ustaw(wpis("Zly"), wpis("Dobry"))
    kolejka = stages.wczytaj_promocje()
    stages.zakwestionuj_promocje(kolejka[1]["url"], "cos nie gra")
    w = stages.artykul_do_promocji()
    sprawdz("inny artykul nadal przechodzi",
            w and w["tytul"] == "Zly", w and w["tytul"])

    # Nieznany adres nie moze wywalic przebiegu ani niczego popsuc.
    stages.zakwestionuj_promocje("https://x/p/nie-ma-takiego", "nieistotne")
    sprawdz("nieznany adres nie psuje pliku",
            len(stages.wczytaj_promocje()) == 2,
            len(stages.wczytaj_promocje()))
finally:
    stages.PROMOCJA = ORYG

print()
print("=== TRZY NOTKI PROMUJACE NIE MOGA POWTARZAC TEGO SAMEGO ===")
# Zmierzone na dzienniku produkcji: trzy notki promujace tamten artykul, z trzech
# kolejnych dni, nioslY te sama fraze „ASTM, which maintains the standard, says"
# i ten sam „68% of Americans". Karta promocyjna to CALY TEKST ARTYKULU podawany
# bez zmian, wiec model co dzien wybieral z niego to samo.
#
# Indeks `zuzyte_fakty` tego nie lapal i lapac nie mogl — on pilnuje ciekawostek
# z puli faktow, a promocja przez te pule nie przechodzi w ogole.
import json as _json         # noqa: E402
import tempfile as _tmp      # noqa: E402

with _tmp.TemporaryDirectory() as _kat:
    _stary = stages.PROMOCJA
    stages.PROMOCJA = pathlib.Path(_kat) / "promocja.json"
    try:
        stages.PROMOCJA.write_text(_json.dumps(
            [{"url": "u1", "tytul": "T", "tekst": "tresc", "wystawione": 0}]),
            encoding="utf-8")
        stages.odhacz_promocje("u1", "Pierwsza notka: ASTM i 68 procent.")
        stages.odhacz_promocje("u1", "Druga notka: zupelnie co innego.")
        _d = _json.loads(stages.PROMOCJA.read_text(encoding="utf-8"))[0]
        sprawdz("dzien promocji nadal sie liczy", _d["wystawione"] == 2, _d)
        sprawdz("i tresc kazdej notki jest zapamietana",
                len(_d.get("powiedziane") or []) == 2, _d.get("powiedziane"))
        sprawdz("w kolejnosci, w jakiej wyszly",
                _d["powiedziane"][0].startswith("Pierwsza"), _d.get("powiedziane"))
        # KONTRDOWOD: odhaczenie BEZ tresci nie moze dopisywac pustych wpisow —
        # inaczej lista rosnie o nic i model dostaje szum.
        stages.odhacz_promocje("u1", "")
        _d2 = _json.loads(stages.PROMOCJA.read_text(encoding="utf-8"))[0]
        sprawdz("puste odhaczenie nie dopisuje wpisu",
                len(_d2["powiedziane"]) == 2, _d2["powiedziane"])
        sprawdz("ale dzien i tak sie liczy", _d2["wystawione"] == 3)
    finally:
        stages.PROMOCJA = _stary

# Karta promocyjna MUSI niesc te pamiec do modelu, inaczej zapis jest ozdoba.
_st = pathlib.Path("agent-v2/stages.py").read_text(encoding="utf-8")
sprawdz("karta promocyjna niesie juz powiedziane",
        '"already_said_in_earlier_notes"' in _st)
_run = pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8")
sprawdz("i run.py przekazuje tresc przy odhaczaniu",
        "odhacz_promocje(" in _run and 'gotowe[0].get("note")' in _run)
# I prompt musi tego ZAKAZYWAC — samo podanie pola nic nie znaczy.
_n = pathlib.Path("agent-v2/prompts/notka.md").read_text(encoding="utf-8")
sprawdz("prompt zakazuje powtarzania wydanych zdan",
        "already_said_in_earlier_notes" in _n and "those sentences are" in _n)
sprawdz("i nazywa, jak to wyglada z zewnatrz",
        "working through a backlog" in _n)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
