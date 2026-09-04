# -*- coding: utf-8 -*-
"""Czy zaczepieni odwzajemniaja sie, i skad naprawde biora sie czytelnicy.

PO CO TO POWSTALO. `data/czytelnicy.jsonl` byl ZAPISYWANY I NIECZYTANY PRZEZ
NIC. 1 wrzesnia 2026 `grep czytelnicy *.py` oddawal trzy trafienia i wszystkie
w `browser.py`: definicje sciezki (967) i zapis (1069-1070). System zbieral
wiec imienna liste swoich czytelnikow od 31 sierpnia i ani razu nie zestawil
jej z lista osob, ktore sam zaczepil. Kazda decyzja „obserwujmy wiecej" albo
„subskrybujmy mniej" byla podejmowana bez ani jednej wlasnej liczby.

CZYTA WYLACZNIE TO, CO JUZ LEZY NA DYSKU. Zadnego nowego pobierania: regulamin
Substacka zakazuje `crawls/scrapes/spiders`, a agent i tak balansuje na tej
granicy. Zrodla to `dziennik.jsonl` (co zrobilismy i kto na to zareagowal),
`czytelnicy.jsonl` (kto nas czyta, imiennie, z data zrzutu) i `wzrost.jsonl`
(same liczniki). Pomiary pozycji dokladamy z `statystyki.jsonl` przez
`statystyki.podsumowanie`, bo tylko tam jest przypisanie subskrypcji do
KONKRETNEGO wpisu — ale to inny pomiar niz przypisanie do OSOBY i jest tak
podpisany.

CZTERY RZECZY, KTORE TEN MODUL MA ROBIC INACZEJ NIZ ZWYKLY RAPORT

1. BRAK DANYCH MA WYGLADAC NA BRAK DANYCH. Blok obserwacji nie wykonal ANI
   JEDNEJ udanej obserwacji (dziennik: dwie proby, obie 23 sierpnia, obie
   nieudane — „nie ma przycisku obserwacja"). Napisanie „0% odwzajemnien"
   byloby klamstwem, bo mianownik jest zerowy. Dlatego `odsetek` to `None`,
   gdy nie bylo ani jednej udanej proby, i liczba dopiero wtedy, gdy jest co
   dzielic. Ta roznica jest w strukturze danych, nie w zdaniu na koncu.

2. HISTORIA JEST KROTSZA NIZ DZIALANIA. Pierwszy zrzut czytelnikow to
   2026-08-31T04:24Z, a najstarsza udana subskrypcja 2026-08-16T17:53Z —
   czternascie i pol dnia, w ktorych nikt nie patrzyl, kto przyszedl. „Nikt
   sie nie odwzajemnil" znaczy wiec „nikogo takiego nie ma na liscie z 31
   sierpnia i pozniej", a nie „nikt nigdy". Raport podaje ten odstep w dniach
   sam z siebie, zeby nie wymagac tej wiedzy od czytajacego.

3. ZDARZENIE POZYSKANIA NIE JEST DOWODEM WCZESNIEJSZEGO KONTAKTU. To jest
   najwazniejsza poprawka tego pliku i jedyna, ktora zmienia liczbe.
   `rodzaj="skutek"` obejmuje typy `follow` i `free_subscription` — czyli
   powiadomienia „ktos cie zaobserwowal / zasubskrybowal". Liczac je jako
   „slad wczesniejszej interakcji" dostaje sie 11 z 19 naszych czytelnikow,
   co brzmi jak odkrycie i jest kolem: obserwujacy ma w dzienniku zdarzenie
   `follow`, bo jest obserwujacym. Po odjeciu samego pozyskania zostaje
   4 z 19 z prawdziwym kontaktem z trescia (polubienie, odpowiedz, restack),
   7 z 19 z samym zdarzeniem pozyskania i 8 z 19 bez zadnego sladu.
   Typ `scheduled_note_sent` odpada osobno — jego `kto` to my sami
   (nasza wlasna publikacja), 9 zdarzen na 199.

4. ODWZAJEMNIENIE MA KIERUNEK W CZASIE. „Zaczepilismy go i JEST naszym
   czytelnikiem" to nie to samo, co „zaczepilismy go i POTEM sie pojawil".
   Pierwsza wersja tego pliku nie pytala, co bylo pierwsze, wiec zaobserwowanie
   wlasnego obserwujacego meldowalo sie jako „odwzajemnilo sie 1 z 1 (100%)" —
   odpowiedz odwrotna do prawdy, w jedynej liczbie, dla ktorej ten modul
   powstal. Blok obserwacji losuje cele z puli komentarzy, a ta ZACHODZI na
   ludzi juz z nami zwiazanych, wiec nie byl to przypadek brzegowy.
   Dzis kazde trafienie ma jeden z trzech werdyktow: `po` (odwzajemnienie),
   `przed` (byl z nami wczesniej) i `nieorzekalna` (zrzuty zaczynaja sie
   2026-08-31 i o wczesniejszym stanie nie mowia NIC). Trzeci nie jest ani
   sukcesem, ani porazka i nie wchodzi do mianownika.

CZEGO TEN MODUL NIE UMIE I NIE UDAJE, ZE UMIE. Zestawiamy trzy rozne rodzaje
nazw: uchwyt uzytkownika (`@ktos` — tak wygladaja czytelnicy), nazwe
wyswietlana (tak wygladaja reakcje: `skutek.kto` to lista nazw, nie uchwytow)
oraz pole `komu` zaczepionych, ktore jest MIESZANKA DWOCH PRZESTRZENI NAZW.
`browser.uchwyt_publikacji` (browser.py:3907) dla hosta w domenie Substacka
oddaje sama poddomene publikacji (`publikacja-b.substack.com` ->
`publikacja-b`), a dla wlasnej domeny — uchwyt AUTORA z `publishedBylines`
(`www.wlasnadomena.example` -> `autor1`). Polowa celow jest wiec porownywalna
z uchwytami czytelnikow, a polowa nie: autor publikacji `publikacja-b`
moze nas subskrybowac jako ktos zupelnie inaczej nazwany i dopasowanie tego
NIE ZOBACZY. Dlatego kazde zestawienie ma dwie kupki: „na pewno" (rowne
uchwyty) i „niepewne" (nazwa wyswietlana czytelnika po znormalizowaniu rowna
uchwytowi celu). Nigdy nie sklejamy ich w jedna liczbe, a „bez dopasowania"
nie nazywamy „nie odwzajemnil sie".

BEZ SIECI, BEZ MODELI, BEZ ZMIANY STANU KONTA. Sam odczyt plikow.
"""

from __future__ import annotations

import json
import statistics
from datetime import datetime, timedelta, timezone

import config

# --- nazwy plikow -------------------------------------------------------------
#
# Sciezki skladamy PRZY KAZDYM WYWOLANIU z `config.DATA_DIR`, a nie jako stale
# modulu. Powod jest ten sam, co w `statystyki._plik`: stala zamrozona przy
# imporcie nie da sie przekierowac w tescie bez reimportu, a modul bez testu
# jest tu wart tyle, co licznik trzymany w pamieci jednego przebiegu.
#
# Nie bierzemy `browser.DZIENNIK`, mimo ze wskazuje to samo miejsce. `browser`
# ciagnie za soba Playwrighta, a ten raport ma dac sie policzyc wszedzie tam,
# gdzie leza pliki — na maszynie bez przegladarki tez. `alarm.nadaktywnosc`
# sklada te sciezke tak samo i z tego samego powodu.
DZIENNIK = "dziennik.jsonl"
CZYTELNICY = "czytelnicy.jsonl"
WZROST = "wzrost.jsonl"

# Dzien, w ktorym konto przestawiono na BIEZACA nisze. Wszystko wczesniejsze
# zaczepia ludzi z poprzedniej dziedziny i nie mowi nic o dzisiejszej
# publicznosci — zmierzone: 53 z 92 hostow w historii komentarzy pochodzi
# sprzed tej daty.
#
# PRZESTAW TO RAZEM Z NISZA. Data jest wpisana, bo dotyczy JEDNEJ instalacji:
# na swiezym koncie nie ma czego odcinac i wartosc moze zostac dowolnie
# wczesna. Nie jest polem konfiguracji, bo pole, ktore ma sens tylko po
# przestawieniu tematu, kusiloby do ustawiania go „na wszelki wypadek".
KOTWICA_NISZY = "2026-08-25"

# Ponizej tylu obserwacji nie wyciagamy wniosku o czasie odzewu, tylko mowimy,
# ze probka jest za mala. Prog nie jest okragly dla ozdoby: przy n < 10 mediana
# jest jedna z mniej niz dziesieciu wartosci, wiec przesuniecie JEDNEJ
# obserwacji rusza ja o caly decyl. „Srednia z dwoch przypadkow" ma tu wygladac
# na brak odpowiedzi, a nie na odpowiedz.
MIN_PROBKA = 10

# --- klasyfikacja zdarzen z pola `skutek.typ` ---------------------------------
#
# TRZY ROZLACZNE KUBELKI I CZWARTY NA NIEZNANE. Zamkniete listy zamiast reguly
# „wszystko, co nie jest pozyskaniem, jest kontaktem": gdy Substack doda jutro
# nowy typ powiadomienia, ma wpasc do kubelka „nieznane" i zostac WYPISANY
# w raporcie, a nie po cichu podbic liczbe kontaktow z trescia.

# Ktos dotknal tego, co napisalismy. To jest jedyny kubelek, ktory liczy sie
# jako „zetknal sie wczesniej z nasza trescia".
KONTAKT_Z_TRESCIA = frozenset({
    "note_like", "note_reply", "note_restack",
    "comment_like", "comment_reply",
    "post_like", "post_reply",
    "restack", "restack_quote", "naked_restack_reaction",
})

# Samo pozyskanie. NIE jest dowodem wczesniejszego kontaktu — patrz punkt 3
# w docstringu modulu.
POZYSKANIE = frozenset({"follow", "free_subscription", "paid_subscription"})

# Nasze wlasne zdarzenia, ktore Substack wrzuca do tego samego strumienia.
# `kto` jest tu nasza wlasna nazwa, wiec bez tego filtru konto samo sobie
# wychodzi na najwierniejszego czytelnika.
NASZE_ZDARZENIA = frozenset({"scheduled_note_sent"})

# Z jakiego typu reakcji wynika, ktorego kanalu dotknal czlowiek.
KANAL_TYPU = {
    "note_like": "notka", "note_reply": "notka", "note_restack": "notka",
    "restack": "notka", "restack_quote": "notka",
    "naked_restack_reaction": "notka",
    "comment_like": "komentarz", "comment_reply": "komentarz",
    "post_like": "artykul", "post_reply": "artykul",
}


# --- wczytywanie --------------------------------------------------------------

def wczytaj(nazwa: str) -> list[dict]:
    """Wiersze pliku JSONL z katalogu danych. Uszkodzona linia nie kasuje reszty.

    Ten sam powod, co w `statystyki.wczytaj`: proces zabity w trakcie zapisu
    zostawia linie urwana w polowie, a w tym projekcie SIGTERM w zwloce przed
    notkami uszkodzil siedem przebiegow w ciagu tygodnia.
    """
    plik = config.DATA_DIR / nazwa
    if not plik.exists():
        return []
    try:
        tresc = plik.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    wynik: list[dict] = []
    for linia in tresc.splitlines():
        linia = linia.strip()
        if not linia:
            continue
        try:
            w = json.loads(linia)
        except ValueError:
            continue
        if isinstance(w, dict):
            wynik.append(w)
    return wynik


def _chwila(tekst) -> datetime | None:
    """ISO-8601 na moment w UTC, bez strefy. Zwraca None zamiast rzucac.

    Dziennik miesza dwa formaty w JEDNYM wpisie: `kiedy` ma strefe
    (`2026-08-17T11:23:06+00:00`), a `kiedy_zdarzenia` jej NIE MA
    (`2026-08-16T14:22:21`). Odejmowanie ich od siebie bez tego sprowadzenia
    rzuca TypeError — czyli caly raport pada na pytaniu o czas odzewu.
    """
    if not tekst:
        return None
    try:
        d = datetime.fromisoformat(str(tekst).replace("Z", "+00:00"))
    except ValueError:
        return None
    return d.astimezone(timezone.utc).replace(tzinfo=None) if d.tzinfo else d


def _nazwa(tekst) -> str:
    """Nazwa wyswietlana do porownywania: male litery, jedna spacja."""
    return " ".join(str(tekst or "").lower().split())


def _uchwyt(tekst) -> str:
    """Uchwyt do porownywania: male litery, same znaki alfanumeryczne.

    Substack pozwala na kropki i myslniki w uchwytach publikacji, a nazwy
    wyswietlane maja spacje i interpunkcje — sprowadzenie obu do samych liter
    i cyfr jest jedynym mostem miedzy „Publikacja Podrozna" a
    „publikacjapodrozna". Most jest SLABY i dlatego trafienia przez niego lecza
    do kupki „niepewne", nigdy do „na pewno".
    """
    return "".join(c for c in str(tekst or "").lower() if c.isalnum())


# --- kto nas czyta ------------------------------------------------------------

# Najwieksza roznica czasu, przy ktorej uznajemy zrzut imienny i zapis licznika
# za pomiar tego samego momentu. Oba powstaja w tym samym bloku jednego
# przebiegu i dziela je zwykle kilkanascie sekund; najwiekszy zmierzony odstep
# to 12 minut (31 sierpnia, 04:12:07 wobec 04:24:28). Godzina jest wiec z
# duzym zapasem, a jednoczesnie nie skleja dwoch roznych przebiegow — te dziela
# co najmniej dwie godziny.
POMIAR_TEN_SAM_MOMENT_MIN = 60

GRUPY = ("obserwujacy", "subskrybenci")


def _licznik_z_chwili(kiedy, liczniki: list[dict]) -> dict | None:
    """Zapis `wzrost.jsonl` z tego samego momentu, co zrzut imienny — albo nic."""
    if not kiedy or not liczniki:
        return None
    blisko = min(liczniki,
                 key=lambda w: abs((_chwila(w["kiedy"]) - kiedy).total_seconds()))
    odstep = abs((_chwila(blisko["kiedy"]) - kiedy).total_seconds()) / 60
    return blisko if odstep <= POMIAR_TEN_SAM_MOMENT_MIN else None


def zrzuty_czytelnikow() -> list[dict]:
    """Zrzuty po kolei, KAZDY Z OCENA, CZY NIE JEST OKROJONY.

    ZRZUT OKROJONY WYGLADA JAK UDANY POMIAR I JEST GORSZY OD BRAKU ZRZUTU.
    `browser.kto_nas_czyta` zbiera najpierw obserwujacych, a dopiero potem
    KLIKA w zakladke „Subscribers". Gdy pekniecie trafi w samo klikniecie,
    obserwujacy sa juz w wyniku — a stara bramka `zapisz_czytelnikow` odrzucala
    zrzut dopiero, gdy byl blad I OBIE listy byly puste. Taki zrzut szedl wiec
    na dysk z pusta lista subskrybentow i bez sladu bledu: czytalo sie to jak
    konto, ktore w ciagu pieciu godzin stracilo wszystkich subskrybentow.

    TRZECH SWIADKOW, BO KAZDY Z OSOBNA MA DZIURE:
    (0) `zrzut["odczytane"]` — lista zakladek, ktore naprawde odpowiedzialy.
        To swiadek NAJMOCNIEJSZY, bo pochodzi z samego zapisu, a nie z naszego
        wnioskowania. SIEDEM ZRZUTOW z 31 sierpnia i 1 wrzesnia tego pola NIE
        MA i nie dostanie — brak klucza znaczy „nie wiadomo, co odczytano",
        a nie „nie odczytano nic", i tylko dlatego dwaj pozostali swiadkowie
        sa nadal potrzebni.
    (a) licznik z `wzrost.jsonl` z tej samej chwili mowi, ze grupa jest
        niepusta. Lapie tez awarie, ktorej `odczytane` nie zobaczy: zmiana
        znacznikow na stronie sprawia, ze selektor nie trafia w nikogo,
        zakladka „odpowiada" i oddaje pustke.
    (b) inny zrzut ma w tej grupie kogokolwiek — dziala takze wtedy, gdy
        licznika z tej chwili nie ma.
    Pusta grupa przy braku wszystkich swiadkow to zwykle mlode konto i nie
    alarmujemy.
    """
    surowe = sorted(wczytaj(CZYTELNICY), key=lambda z: str(z.get("kiedy") or ""))
    liczniki = [w for w in wczytaj(WZROST) if _chwila(w.get("kiedy"))]
    najwiecej = {g: max((len(z.get(g) or []) for z in surowe), default=0)
                 for g in GRUPY}
    wynik: list[dict] = []
    for i, z in enumerate(surowe):
        kiedy = _chwila(z.get("kiedy"))
        licznik = _licznik_z_chwili(kiedy, liczniki)
        deklaracja = z.get("odczytane")
        odczytane = deklaracja if isinstance(deklaracja, list) else None
        okrojone: dict[str, str] = {}
        for g in GRUPY:
            if odczytane is not None and g not in odczytane:
                okrojone[g] = "zrzut sam mowi, ze tej zakladki nie odczytal"
                continue
            if len(z.get(g) or []):
                continue
            try:
                ile_liczy = int((licznik or {}).get(g) or 0)
            except (TypeError, ValueError):
                ile_liczy = 0
            if ile_liczy > 0:
                okrojone[g] = ("licznik profilu z tej samej chwili mowi %d"
                               % ile_liczy)
            elif najwiecej[g] > 0:
                okrojone[g] = ("inne zrzuty maja w tej grupie do %d osob"
                               % najwiecej[g])
        wynik.append({"i": i, "kiedy": kiedy, "zrzut": z,
                      "okrojone": okrojone, "okrojony": bool(okrojone)})
    return wynik


def czytelnicy() -> dict[str, dict]:
    """Uchwyt czytelnika -> co o nim wiemy ze zrzutow.

    `pierwszy_zrzut` to NUMER zrzutu, nie data — bo tylko numer mowi, czy
    pojawienie sie da sie datowac. Kto byl juz w zrzucie zerowym, ten mogl
    przyjsc dowolnie wczesniej i jego „kiedy" jest nieznane; kto doszedl
    w zrzucie trzecim, ten przyszedl miedzy zrzutem drugim a trzecim i to
    jest przedzial o znanych koncach.

    `absencja_pewna` MOWI, CZY TEN PRZEDZIAL W OGOLE COS ZNACZY. Zamkniecie od
    dolu opiera sie na jednym zdaniu: „w poprzednim zrzucie GO NIE BYLO". Jesli
    tamten zrzut byl okrojony (patrz `zrzuty_czytelnikow`), to nieobecnosc jest
    pozorna — czlowiek mogl w nim byc i nie zostac zapisany. Bez tego pola
    okrojony PIERWSZY zrzut nadalby wszystkim subskrybentom `pierwszy_zrzut > 0`
    i raport oglosilby ich za datowalnych, budujac na tym odpowiedz.
    """
    zrzuty = zrzuty_czytelnikow()
    ludzie: dict[str, dict] = {}
    for z in zrzuty:
        i, zrzut = z["i"], z["zrzut"]
        for grupa, rola in (("obserwujacy", "obserwujacy"),
                            ("subskrybenci", "subskrybent")):
            for osoba in zrzut.get(grupa) or []:
                if not isinstance(osoba, dict):
                    continue
                u = str(osoba.get("uchwyt") or "").strip()
                if not u:
                    continue
                wpis = ludzie.setdefault(u, {
                    "uchwyt": u, "nazwy": set(), "role": set(),
                    "pierwszy_zrzut": i,
                    "pierwszy_raz": str(zrzut.get("kiedy") or ""),
                    "pierwsza_chwila": z["kiedy"],
                    "ostatni_zrzut": i,
                })
                wpis["nazwy"].add(str(osoba.get("nazwa") or u))
                wpis["role"].add(rola)
                wpis["ostatni_zrzut"] = i
    ostatni = len(zrzuty) - 1
    for wpis in ludzie.values():
        # „Odszedl" znaczy: byl w jakims zrzucie i nie ma go w NAJNOWSZYM —
        # ale tylko wtedy, gdy najnowszy zrzut jest pelny. Z okrojonego
        # „odszedl" znaczyloby „urwal sie klik w zakladke".
        wpis["odszedl"] = (ostatni >= 0 and wpis["ostatni_zrzut"] < ostatni
                           and not zrzuty[ostatni]["okrojony"])
        i = wpis["pierwszy_zrzut"]
        poprzedni = zrzuty[i - 1] if i > 0 else None
        wpis["absencja_chwila"] = poprzedni["kiedy"] if poprzedni else None
        wpis["absencja_pewna"] = bool(poprzedni and poprzedni["kiedy"]
                                      and not poprzedni["okrojony"])
    return ludzie


# --- co bylo pierwsze ---------------------------------------------------------

# Trzy mozliwe odpowiedzi na pytanie „co bylo pierwsze: nasze dzialanie czy
# jego pojawienie sie". Czwartej nie ma i wlasnie dlatego sa nazwane: bez
# `NIEORZEKALNA` kazdy nierozstrzygniety przypadek wpadal do „odwzajemnil sie".
PO = "po"                      # zaczepilismy, POTEM sie pojawil
PRZED = "przed"                # byl z nami, ZANIM go zaczepilismy
NIEORZEKALNA = "nieorzekalna"  # przedzialy zachodza na siebie


def kolejnosc(wpis: dict, akcja) -> str:
    """Czy czytelnik pojawil sie PO naszym dzialaniu, PRZED nim, czy nie wiadomo.

    O pojawieniu sie wiemy tylko tyle, ze zdarzylo sie w przedziale
    `(P, F]`: P to chwila ostatniego zrzutu, w ktorym GO NIE BYLO, a F —
    pierwszego, w ktorym JEST. Stad trzy stany, a nie dwa:

        akcja <= P            -> PO       (pojawienie sie jest pozniejsze)
        akcja >= F            -> PRZED    (byl juz na liscie)
        P < akcja < F         -> NIEORZEKALNA (dzialanie wpada w przedzial)

    HISTORIA ZACZYNA SIE 2026-08-31 I TO NIE JEST DETAL. Dla kogos z zerowego
    zrzutu P NIE ISTNIEJE — przedzial jest otwarty w lewo do nieskonczonosci.
    Zaczepienie pozniejsze niz zrzut zerowy daje wiec PRZED (na pewno byl
    wczesniej), a wczesniejsze — NIEORZEKALNA, bo o tym, co bylo przed
    31 sierpnia, ten plik nie wie NIC. To NIE jest „brak odwzajemnienia"
    i tym bardziej nie jest odwzajemnieniem.

    Gdy zrzut z chwili P byl okrojony, nieobecnosc jest pozorna i PO nie
    przysluguje (`absencja_pewna` w `czytelnicy`).
    """
    if akcja is None or not wpis.get("pierwsza_chwila"):
        return NIEORZEKALNA
    if (wpis.get("absencja_pewna") and wpis.get("absencja_chwila")
            and akcja <= wpis["absencja_chwila"]):
        return PO
    if akcja >= wpis["pierwsza_chwila"]:
        return PRZED
    return NIEORZEKALNA


def okno_pomiaru() -> dict:
    """Od kiedy do kiedy w ogole widzimy, kto nas czyta.

    Bez tej ramki kazda liczba nizej jest nadinterpretacja: lista czytelnikow
    to nie kronika konta, tylko siedem zdjec z konca sierpnia.
    """
    zrzuty = sorted(wczytaj(CZYTELNICY), key=lambda z: str(z.get("kiedy") or ""))
    if not zrzuty:
        return {"zrzutow": 0, "od": None, "do": None, "dni": None}
    od, do = _chwila(zrzuty[0].get("kiedy")), _chwila(zrzuty[-1].get("kiedy"))
    return {
        "zrzutow": len(zrzuty),
        "od": od, "do": do,
        "dni": (do - od).total_seconds() / 86400 if od and do else None,
    }


def pokrycie() -> dict:
    """Ilu czytelnikow LICZY Substack, a ilu umiemy nazwac po imieniu.

    TA LICZBA OGRANICZA WSZYSTKIE POZOSTALE. `wzrost.jsonl` zapisuje liczniki
    z profilu, `czytelnicy.jsonl` — imienna liste z tej samej chwili. Jesli
    lista jest krotsza od licznika, kazda odpowiedz „ilu z nich" jest liczona
    z niepelnego mianownika i musi to powiedziec.

    ZMIERZONE 1 wrzesnia 2026, siedem par zrzutow: subskrybenci zgadzaja sie
    co do jednego w szesciu parach na siedem, a OBSERWUJACY sa krotsi stale —
    licznik mowi 12, lista oddaje 10 (31 sierpnia 11:38: 9 wobec 7; 17:08:
    11 wobec 9; 1 wrzesnia 11:38: 12 wobec 10). Dwoch obserwujacych nie ma
    wiec nazwiska w zadnym pomiarze i nie da sie ich przypisac do niczego.
    To jest ta sama rozbieznosc, ktora `test_kto_nas_czyta` zanotowal przy
    powstawaniu zapisu („zakladka mowi Followers (8), lista oddaje SIEDEM").
    """
    zrzuty = sorted(wczytaj(CZYTELNICY), key=lambda z: str(z.get("kiedy") or ""))
    liczniki = [w for w in wczytaj(WZROST) if _chwila(w.get("kiedy"))]
    pary = []
    for z in zrzuty:
        kiedy = _chwila(z.get("kiedy"))
        blisko = _licznik_z_chwili(kiedy, liczniki)
        if blisko is None:
            continue
        pary.append({
            "kiedy": kiedy,
            "obserwujacy_licznik": int(blisko.get("obserwujacy") or 0),
            "obserwujacy_z_nazwiska": len(z.get("obserwujacy") or []),
            "subskrybenci_licznik": int(blisko.get("subskrybenci") or 0),
            "subskrybenci_z_nazwiska": len(z.get("subskrybenci") or []),
        })
    if not pary:
        return {"par": 0, "ostatnia": None, "brakuje_obserwujacych": None,
                "brakuje_subskrybentow": None}
    ost = pary[-1]
    return {
        "par": len(pary),
        "ostatnia": ost,
        "brakuje_obserwujacych": ost["obserwujacy_licznik"]
        - ost["obserwujacy_z_nazwiska"],
        "brakuje_subskrybentow": ost["subskrybenci_licznik"]
        - ost["subskrybenci_z_nazwiska"],
    }


# --- 1. kto sie odwzajemnil ---------------------------------------------------

def _pusty_kubel() -> dict:
    """Swiezy komplet licznikow. Funkcja, a nie stala: `dict(STALA)` kopiuje
    plytko i wszystkie kubelki wspoldzielilyby te same listy — subskrypcje
    wpadalyby do obserwacji."""
    return {"udane": [], "nieudane": [], "pominiete": [],
            "prob_przed_kotwica": 0, "prob_od_kotwicy": 0,
            "udane_przed_kotwica": 0, "udane_od_kotwicy": 0}


def zaczepienia() -> dict[str, dict]:
    """Kogo zaczepilismy — osobno udane, nieudane i POMINIETE.

    Trzy liczniki, bo stany naprawde sa trzy, i to jest ta sama decyzja, co
    w `audyt_systemu.policz_rodzaje`. `obserwacja_pominieta` (`udane=True`)
    znaczy „nie klikalem, bo juz go obserwujemy albo nie mial przycisku" —
    zaliczenie tego do prob zawyzaloby mianownik odwzajemnien o dzialania,
    ktorych nigdy nie bylo.

    Pominiecia rozpoznajemy po koncowce `_pominieta`, a nie po zamknietej
    liscie: gdy dojdzie `subskrypcja_pominieta`, ma trafic do wlasciwej kupki
    od pierwszego dnia, a nie po tym, jak ktos zauwazy przekrecony licznik.
    """
    wynik: dict[str, dict] = {}
    for w in wczytaj(DZIENNIK):
        rodzaj = str(w.get("rodzaj") or "")
        pominiecie = rodzaj.endswith("_pominieta")
        klucz = rodzaj[: -len("_pominieta")] if pominiecie else rodzaj
        if klucz not in ("obserwacja", "subskrypcja"):
            continue
        kubel = wynik.setdefault(klucz, _pusty_kubel())
        komu = str(w.get("komu") or "").strip()
        kiedy = str(w.get("kiedy") or "")
        pozycja = {"komu": komu, "kiedy": kiedy,
                   "powod": str(w.get("powod") or "")}
        if pominiecie:
            kubel["pominiete"].append(pozycja)
            continue
        # ERY LICZYMY OD PROB, NIE OD SUKCESOW. Blok obserwacji podjal dwie
        # proby, obie 23 sierpnia i obie nieudane — liczac ery po sukcesach
        # dostawalo sie „0 przed, 0 po", czyli obraz bloku, ktory nigdy nie
        # wstal. Prawda jest inna i wazniejsza: probowal, ale ANI RAZU po
        # przestawieniu konta na AI, wiec jego cisza jest z innego powodu.
        po_kotwicy = kiedy[:10] >= KOTWICA_NISZY
        kubel["prob_od_kotwicy" if po_kotwicy else "prob_przed_kotwica"] += 1
        if w.get("udane"):
            kubel["udane"].append(pozycja)
            kubel["udane_od_kotwicy" if po_kotwicy
                  else "udane_przed_kotwica"] += 1
        else:
            kubel["nieudane"].append(pozycja)
    for klucz in ("obserwacja", "subskrypcja"):
        wynik.setdefault(klucz, _pusty_kubel())
    return wynik


def odwzajemnienie() -> dict[str, dict]:
    """Ilu z zaczepionych pojawilo sie POTEM na naszej liscie czytelnikow.

    SLOWO „POTEM" JEST TU CALA TRESCIA POMIARU. Do 1 wrzesnia 2026 ta funkcja
    uznawala za odwzajemnienie KAZDE zrownanie uchwytu celu z uchwytem
    czytelnika i nie pytala, co bylo pierwsze. Blok obserwacji losuje cele
    z puli komentarzy, a ta zachodzi na ludzi juz z nami zwiazanych, wiec
    wystarczylo zaobserwowac wlasnego obserwujacego, zeby raport zameldowal
    „odwzajemnilo sie na pewno 1 z 1 (100%)". Odtworzone na kopii produkcji:
    `czytelnik1` obserwuje nas od pierwszego zrzutu (31 sierpnia,
    nieprzerwanie przez wszystkie siedem), jedno zaczepienie z 2 wrzesnia daje
    te wlasnie setke — czyli odpowiedz DOKLADNIE ODWROTNA do prawdy, i to
    w jedynej liczbie, dla ktorej ten modul istnieje.

    Kolejnosc rozstrzyga `kolejnosc()` i ma TRZY wyniki, nie dwa. Odwzajemnienie
    to tylko `PO`. `PRZED` znaczy „byl z nami wczesniej" i jest przeciwienstwem
    odwzajemnienia. `NIEORZEKALNA` to stan, w ktorym plik po prostu nie wie —
    i nie wolno go dolaczyc do zadnej z dwoch pozostalych kupek.

    MIANOWNIK TO `orzekalnych`, NIE `udanych`. Zaczepienie, o ktorym nie da sie
    powiedziec, co bylo pierwsze, nie jest ani sukcesem, ani porazka strategii;
    trzymanie go w mianowniku zanizaloby odsetek o przypadki, ktorych nikt nie
    zmierzyl. Gdy orzekalnych jest zero, `odsetek` to `None` — z tego samego
    powodu, dla ktorego jest `None` przy zerze udanych prob: „nikt nie kliknal
    przycisku obserwuj, bo blok nie dzialal" to usterka, a „obserwowanie nie
    przynosi nic" to wniosek strategiczny, i pomylenie ich kosztowaloby miesiac
    pracy w zlym kierunku.

    CZEGO TA FUNKCJA NADAL NIE UMIE: rozroznia ludzi, nie ROLE. Kto obserwowal
    nas przed zaczepieniem i zasubskrybowal po nim, wychodzi tu jako `PRZED` —
    czyli raczej przegapione odwzajemnienie niz wymyslone. Pomylka w te strone
    jest jedyna, na ktora ten modul moze sobie pozwolic.
    """
    ludzie = czytelnicy()
    po_uchwycie = {_uchwyt(u): u for u in ludzie}
    po_nazwie: dict[str, str] = {}
    for u, wpis in ludzie.items():
        for n in wpis["nazwy"]:
            po_nazwie.setdefault(_uchwyt(n), u)

    wynik: dict[str, dict] = {}
    for klucz, kubel in zaczepienia().items():
        pewne, niepewne, bez = [], [], []
        for poz in kubel["udane"]:
            k = _uchwyt(poz["komu"])
            czytelnik = po_uchwycie.get(k) if k else None
            jak = "uchwyt"
            if k and not czytelnik and k in po_nazwie:
                # Uchwyt PUBLIKACJI zderzony z NAZWA WYSWIETLANA czytelnika.
                # Bywa trafne („Publikacja Podrozna" = publikacjapodrozna), ale
                # nazwy wyswietlane sie powtarzaja i nikt ich nie waliduje.
                czytelnik, jak = po_nazwie[k], "nazwa wyswietlana"
            if not czytelnik:
                bez.append(poz)
                continue
            trafienie = {**poz, "czytelnik": czytelnik, "jak": jak,
                         "kolejnosc": kolejnosc(ludzie[czytelnik],
                                                _chwila(poz["kiedy"]))}
            (pewne if jak == "uchwyt" else niepewne).append(trafienie)

        udanych = len(kubel["udane"])
        trafienia = pewne + niepewne
        # ODWZAJEMNIENIE = TRAFIENIE PO UCHWYCIE **I** WE WLASCIWEJ KOLEJNOSCI.
        # Rozdzielone celowo na trzy listy zamiast jednej liczby: „byl
        # wczesniej" i „nie wiadomo" to dwie rozne odpowiedzi i obie sa
        # przeciwienstwem odwzajemnienia, ale tylko pierwsza jest pomiarem.
        odwzajemnili = [t for t in pewne if t["kolejnosc"] == PO]
        odwzajemnili_niepewnie = [t for t in niepewne if t["kolejnosc"] == PO]
        byli_wczesniej = [t for t in trafienia if t["kolejnosc"] == PRZED]
        nieorzekalne = [t for t in trafienia if t["kolejnosc"] == NIEORZEKALNA]
        orzekalnych = udanych - len(nieorzekalne)

        # ODWZAJEMNIENIA LICZONE OSOBNO DLA ERY AI. Cztery z dwunastu udanych
        # subskrypcji sa sprzed 25 sierpnia, czyli z konta o innym temacie —
        # wrzucenie ich do jednego mianownika rozcienczaloby dzisiejsze
        # pytanie o publicznosc AI danymi o blogach kulinarnych.
        def _od_kotwicy(lista):
            return [t for t in lista if str(t["kiedy"])[:10] >= KOTWICA_NISZY]

        orzekalnych_od_kotwicy = (kubel["udane_od_kotwicy"]
                                  - len(_od_kotwicy(nieorzekalne)))
        odwzajemnili_od_kotwicy = _od_kotwicy(odwzajemnili)
        wynik[klucz] = {
            "prob": udanych + len(kubel["nieudane"]),
            "udanych": udanych,
            "nieudanych": len(kubel["nieudane"]),
            "pominietych": len(kubel["pominiete"]),
            "prob_przed_kotwica": kubel["prob_przed_kotwica"],
            "prob_od_kotwicy": kubel["prob_od_kotwicy"],
            "udane_przed_kotwica": kubel["udane_przed_kotwica"],
            "udane_od_kotwicy": kubel["udane_od_kotwicy"],
            # Dopasowania po NAZWACH — bez rozstrzygania kolejnosci.
            "pewne": pewne, "niepewne": niepewne, "bez": bez,
            # Dopasowania po nazwach ORAZ po czasie. To sa liczby do raportu.
            "odwzajemnili": odwzajemnili,
            "odwzajemnili_niepewnie": odwzajemnili_niepewnie,
            "byli_wczesniej": byli_wczesniej,
            "nieorzekalne": nieorzekalne,
            "orzekalnych": orzekalnych,
            "odwzajemnili_od_kotwicy": len(odwzajemnili_od_kotwicy),
            "orzekalnych_od_kotwicy": orzekalnych_od_kotwicy,
            # Mianownik zerowy nie daje zera procent, tylko brak odpowiedzi.
            "odsetek": (len(odwzajemnili) / orzekalnych) if orzekalnych else None,
            "odsetek_od_kotwicy": (len(odwzajemnili_od_kotwicy)
                                   / orzekalnych_od_kotwicy
                                   if orzekalnych_od_kotwicy > 0 else None),
        }
    return wynik


def slepe_okno() -> dict:
    """O ile nasze najstarsze zaczepienie wyprzedza pierwszy zrzut czytelnikow.

    Zmierzone 1 wrzesnia 2026: subskrypcja `publikacja-b` z 16 sierpnia
    17:53Z wobec pierwszego zrzutu 31 sierpnia 04:24Z — 14,4 dnia, w ktorych
    ktos mogl przyjsc i odejsc bez zadnego sladu. Bez tej liczby zdanie
    „0 z 12 sie odwzajemnilo" czyta sie jak „nikt nigdy", a znaczy tylko
    „nikogo takiego nie ma na siedmiu zdjeciach z konca sierpnia".
    """
    okno = okno_pomiaru()
    najstarsze = None
    for kubel in zaczepienia().values():
        for poz in kubel["udane"]:
            ch = _chwila(poz["kiedy"])
            if ch and (najstarsze is None or ch < najstarsze):
                najstarsze = ch
    if not okno["od"] or najstarsze is None:
        return {"dni": None, "najstarsze_zaczepienie": najstarsze,
                "pierwszy_zrzut": okno["od"]}
    return {
        "dni": max(0.0, (okno["od"] - najstarsze).total_seconds() / 86400),
        "najstarsze_zaczepienie": najstarsze,
        "pierwszy_zrzut": okno["od"],
    }


# --- 2. skad przyszli nasi czytelnicy -----------------------------------------

def _reakcje() -> tuple[list[dict], dict[str, int]]:
    """Zdarzenia `skutek` rozdzielone na kubelki plus licznik typow nieznanych."""
    reakcje, nieznane = [], {}
    for w in wczytaj(DZIENNIK):
        if str(w.get("rodzaj") or "") != "skutek":
            continue
        typ = str(w.get("typ") or "")
        if typ in NASZE_ZDARZENIA:
            continue
        if typ not in KONTAKT_Z_TRESCIA and typ not in POZYSKANIE:
            nieznane[typ] = nieznane.get(typ, 0) + 1
            continue
        kto = w.get("kto")
        reakcje.append({
            "typ": typ,
            "kontakt": typ in KONTAKT_Z_TRESCIA,
            "kto": [_nazwa(k) for k in kto] if isinstance(kto, list) else [],
            "kiedy": _chwila(w.get("kiedy_zdarzenia")) or _chwila(w.get("kiedy")),
            "czego": str(w.get("czego")) if w.get("czego") else "",
        })
    return reakcje, nieznane


def skad_przyszli() -> dict:
    """Ilu naszych czytelnikow zetknelo sie wczesniej z nasza trescia.

    TRZY KUPKI, NIE DWIE. „Ma slad" i „nie ma sladu" to podzial, ktory daje
    11 z 19 i jest kolem — patrz punkt 3 w docstringu modulu. Zdarzenie
    `follow` u obserwujacego nie jest sladem wczesniejszej interakcji, tylko
    zapisem samego pozyskania. Rozdzielone: 4 z kontaktem z trescia, 7 z samym
    pozyskaniem, 8 bez niczego (zmierzone 1 wrzesnia 2026).

    KOLEJNOSCI NIE DA SIE USTALIC DLA WSZYSTKICH. Kto byl juz w pierwszym
    zrzucie, ten mogl nas czytac zanim cokolwiek polubil — 14 z 19 osob jest
    w tym stanie (zmierzone 1 wrzesnia 2026) i raport to mowi, zamiast liczyc
    „wczesniej" na wiare. Do tej samej kupki wchodzi kazdy, czyj poprzedni
    zrzut byl OKROJONY: jego nieobecnosc jest pozorna, wiec i „wczesniej"
    bylo by zmyslone.
    """
    ludzie = czytelnicy()
    reakcje, nieznane = _reakcje()

    z_trescia, tylko_pozyskanie, bez_sladu = [], [], []
    nierozstrzygalna = 0
    for u, wpis in sorted(ludzie.items()):
        nazwy = {_nazwa(n) for n in wpis["nazwy"]}
        kontakty = [r for r in reakcje
                    if r["kontakt"] and nazwy & set(r["kto"])]
        pozyskania = [r for r in reakcje
                      if not r["kontakt"] and nazwy & set(r["kto"])]
        # DATOWALNY TO NIE TO SAMO, CO „NIE Z ZEROWEGO ZRZUTU". Zamkniecie
        # przedzialu od dolu opiera sie na nieobecnosci w poprzednim zrzucie,
        # a nieobecnosc w zrzucie OKROJONYM jest pozorna — patrz
        # `zrzuty_czytelnikow`. Okrojony pierwszy zrzut dawalby tu wszystkim
        # subskrybentom falszywa datowalnosc.
        if not wpis["absencja_pewna"]:
            nierozstrzygalna += 1
        if kontakty:
            momenty = [r["kiedy"] for r in kontakty if r["kiedy"]]
            z_trescia.append({
                "uchwyt": u,
                "typy": sorted({r["typ"] for r in kontakty}),
                "ile": len(kontakty),
                "pierwszy_kontakt": min(momenty) if momenty else None,
                "datowalny": wpis["absencja_pewna"],
            })
        elif pozyskania:
            tylko_pozyskanie.append({"uchwyt": u,
                                     "typy": sorted({r["typ"] for r in pozyskania})})
        else:
            bez_sladu.append({"uchwyt": u})
    return {
        "czytelnikow": len(ludzie),
        "z_trescia": z_trescia,
        "tylko_pozyskanie": tylko_pozyskanie,
        "bez_sladu": bez_sladu,
        "nierozstrzygalna_kolejnosc": nierozstrzygalna,
        "typy_nieznane": nieznane,
    }


# --- 3. ile czasu mija --------------------------------------------------------

def _nasze_pozycje() -> dict[str, dict]:
    """Identyfikator wystawionej tresci -> rodzaj i chwila wystawienia.

    Notka trzyma swoj identyfikator w polu `id` (jako napis), komentarz
    w `nasz_id` (jako liczba). Sprowadzamy oba do napisu, bo `skutek.czego`
    jest liczba i bez tego zestawienie nie trafia w nic.

    ODPOWIEDZI SA TU CELOWO, MIMO ZE DZIS NIC NIE WNOSZA: wpisy `rodzaj=
    "odpowiedz"` nie maja jeszcze pola `nasz_id` (sprawdzone na 54 wpisach
    z 1 wrzesnia — zadna go nie ma), wiec zaden odzew na odpowiedz nie da sie
    do niej podpiac. Gdy `wystaw_odpowiedz` zacznie zapisywac identyfikator,
    ta statystyka zacznie dzialac sama, bez zmiany tutaj. Do tego czasu
    „odpowiedz" po prostu nie pojawia sie w wyniku — i to jest uczciwsze niz
    wiersz z zerem, ktory wygladalby na zmierzone zero.
    """
    pozycje: dict[str, dict] = {}
    for w in wczytaj(DZIENNIK):
        rodzaj = str(w.get("rodzaj") or "")
        ident = w.get("id") if rodzaj == "notka" else w.get("nasz_id")
        if rodzaj not in ("notka", "komentarz", "odpowiedz") or not ident:
            continue
        chwila = _chwila(w.get("kiedy"))
        if chwila:
            pozycje[str(ident)] = {"rodzaj": rodzaj, "kiedy": chwila,
                                   "gdzie": str(w.get("gdzie") or "")}
    return pozycje


def kanal_reakcji(reakcja: dict, pozycje: dict[str, dict]) -> str:
    """Ktorego NASZEGO kanalu dotknal czlowiek — z CELU reakcji, nie z jej typu.

    TYP ZDARZENIA KLAMIE I DA SIE TO POKAZAC LICZBA. Komentarz pod CUDZA NOTKA
    dostaje u Substacka numer z tej samej przestrzeni `c-`, co notka, wiec
    reakcja na niego przychodzi jako `note_like` / `note_reply`. `KANAL_TYPU`
    czyta to jako „notka" i dopisuje cudzy watek do naszego kanalu notek.
    Zmierzone 2 wrzesnia 2026 na produkcyjnym dzienniku: z 79 reakcji, ktore da
    sie podpiac pod nasza pozycje, 17 (9 `note_reply` + 8 `note_like`) dotyczy
    NASZYCH KOMENTARZY POD CUDZYMI NOTKAMI — czyli co piata. Stary podzial calej
    historii mowil „notka 165, komentarz 28"; prawdziwy to „notka 148,
    komentarz@artykul 20, komentarz@notka 17".

    Pytamy najpierw `czego` (numer naszej tresci, ktory `browser` zapisuje przy
    kazdym skutku), a `KANAL_TYPU` zostaje DROGA ZAPASOWA dla reakcji, ktorych
    podpiac sie nie da — bo czesc notek i komentarzy nie ma w dzienniku wlasnego
    numeru. Zapasowa droga daje wtedy odpowiedz z grubsza, a nie zadnej.
    """
    poz = pozycje.get(str(reakcja.get("czego") or ""))
    if not poz:
        return KANAL_TYPU.get(reakcja["typ"], "nieznany")
    if poz["rodzaj"] != "komentarz":
        return poz["rodzaj"]
    return ("komentarz@notka" if "note/" in (poz.get("gdzie") or "")
            else "komentarz@artykul")


def opoznienia() -> dict:
    """Dwa rozne czasy, celowo NIE zsumowane w jeden.

    (a) OD WYSTAWIENIA DO REAKCJI. Zestawiamy `skutek.czego` z identyfikatorem
        naszej notki albo komentarza. Zmierzone 1 wrzesnia: 36 reakcji na
        notki (mediana 0,6 h) i 17 na komentarze (mediana 7,9 h). To jedyna
        probka w tym pliku, ktora w ogole ma wielkosc.

    (b) OD ZACZEPIENIA DO POZYSKANIA. Ilu z tych, ktorych zaczepilismy, stalo
        sie potem czytelnikami i po jakim czasie. Dzis nikt — wiec nie ma
        czego usredniac i raport ma to powiedziec wprost, a nie podac
        „srednia z dwoch przypadkow".

    Sklejenie (a) i (b) w jedna liczbe „czas odzewu" bylo by najgorszym
    mozliwym wynikiem: pierwsze mowi o tempie platformy, drugie o skutecznosci
    strategii, i tylko drugie odpowiada na pytanie wlasciciela.
    """
    pozycje = _nasze_pozycje()
    reakcje, _ = _reakcje()

    wg_rodzaju: dict[str, list[float]] = {}
    for r in reakcje:
        poz = pozycje.get(r["czego"])
        if not poz or not r["kiedy"]:
            continue
        godzin = (r["kiedy"] - poz["kiedy"]).total_seconds() / 3600
        wg_rodzaju.setdefault(poz["rodzaj"], []).append(godzin)

    na_tresc = {}
    for rodzaj, lista in wg_rodzaju.items():
        # UJEMNE OPOZNIENIE znaczy, ze reakcja jest starsza od tresci, na ktora
        # rzekomo odpowiada — albo zegary sie rozjechaly, albo trafilismy
        # w cudzy identyfikator z tej samej puli. Takiej pozycji nie da sie
        # zinterpretowac, wiec nie wchodzi do mediany; ale jest LICZONA
        # i wypisywana, bo cicho wyrzucone dane to ta sama wada, przed ktora
        # broni sie caly ten plik.
        dobre = [g for g in lista if g >= 0]
        if not dobre:
            continue
        na_tresc[rodzaj] = {
            "n": len(dobre),
            "odrzucone_ujemne": len(lista) - len(dobre),
            "mediana_h": statistics.median(dobre),
            "min_h": min(dobre), "max_h": max(dobre),
            "do_24h": sum(1 for g in dobre if g <= 24),
            "wystarczy_na_wniosek": len(dobre) >= MIN_PROBKA,
        }

    # (b) — kto z zaczepionych trafil na liste czytelnikow i kiedy najwczesniej
    # mogl to zrobic. Przedzial, nie punkt: wiemy tylko, ze pojawil sie miedzy
    # dwoma zrzutami, a te dzieli kilka godzin.
    #
    # TYLKO KOLEJNOSC `PO`. Dla kogos, kto byl z nami PRZED zaczepieniem,
    # „opoznienie odzewu" wyszlo by ujemne albo, co gorsza, dodatnie i
    # bezsensowne — mierzyloby czas do zrzutu, ktory tylko potwierdzil stan
    # sprzed naszego dzialania. Odrzucone sa LICZONE, nie wyrzucane po cichu.
    ludzie = czytelnicy()
    zrzuty = sorted(wczytaj(CZYTELNICY), key=lambda z: str(z.get("kiedy") or ""))
    przypadki = []
    odrzucone = {PRZED: 0, NIEORZEKALNA: 0}
    for kubel in odwzajemnienie().values():
        for trafienie in kubel["pewne"] + kubel["niepewne"]:
            wpis = ludzie.get(trafienie["czytelnik"])
            akcja = _chwila(trafienie["kiedy"])
            if not wpis or not akcja:
                continue
            if trafienie["kolejnosc"] != PO:
                odrzucone[trafienie["kolejnosc"]] += 1
                continue
            i = wpis["pierwszy_zrzut"]
            do = _chwila(zrzuty[i].get("kiedy")) if i < len(zrzuty) else None
            od = _chwila(zrzuty[i - 1].get("kiedy")) if i > 0 else None
            przypadki.append({
                "komu": trafienie["komu"], "czytelnik": trafienie["czytelnik"],
                "jak": trafienie["jak"],
                "najwczesniej_h": (od - akcja).total_seconds() / 3600 if od else None,
                "najpozniej_h": (do - akcja).total_seconds() / 3600 if do else None,
                "datowalny": wpis["absencja_pewna"],
            })
    return {
        "na_tresc": na_tresc,
        "na_zaczepienie": {
            "n": len(przypadki),
            "przypadki": przypadki,
            "odrzucone_byli_wczesniej": odrzucone[PRZED],
            "odrzucone_nieorzekalne": odrzucone[NIEORZEKALNA],
            "wystarczy_na_wniosek": len(przypadki) >= MIN_PROBKA,
        },
        "min_probka": MIN_PROBKA,
    }


# --- 4. ktory kanal poprzedza pozyskanie --------------------------------------

def kanaly() -> dict:
    """Co poprzedzilo pojawienie sie czytelnika — osobowo i pozycyjnie.

    DWA POMIARY, DWA MIANOWNIKI, JEDEN NIE ZASTEPUJE DRUGIEGO.

    OSOBOWO liczymy tylko tych, ktorych pojawienie sie DA SIE DATOWAC — czyli
    doszli miedzy dwoma zrzutami. Kto byl w zrzucie zerowym, ten mogl przyjsc
    kiedykolwiek i przypisanie mu kanalu byloby zmysleniem. Zmierzone
    1 wrzesnia: 5 osob datowalnych z 19, i zadnej z nich nie poprzedza w
    dzienniku zaden nasz kontakt. To jest odpowiedz „nie wiadomo", a nie
    „zadnym kanalem".

    POZYCYJNIE to przypisanie SUBSTACKA, brane z `statystyki.jsonl`: ile
    subskrypcji serwis przypisal ktorej pozycji. Mowi o wpisie, nie o
    czlowieku, i nie da sie z niego wyczytac, kto konkretnie przyszedl —
    ale jest jedynym zrodlem, ktore w ogole cos przypisuje. Niesiemy przy nim
    `bez_zasiegu`, bo Substack NIE LICZY zasiegu wpisow, ktore nic nie zebraly:
    zmierzone 1 wrzesnia 2026 — 16 z 63 komentarzy nie ma kart zasiegu, przy
    0 z 6 artykulow i 0 z 47 notek. I jest to DOLNA granica: rekordy sprzed
    31 sierpnia nie maja jeszcze pola `ma_karty_zasiegu` i licza sie jako
    zmierzone. Bez tej kolumny 63 pozycje komentarzy stoja w tabeli obok
    6 pozycji artykulow tak, jakby policzono je tak samo.
    """
    ludzie = czytelnicy()
    reakcje, _ = _reakcje()
    # RAZ, PRZED PETLA. Wewnatrz petli ta funkcja czytalaby caly dziennik dla
    # kazdego czytelnika z osobna.
    pozycje = _nasze_pozycje()
    zrzuty = sorted(wczytaj(CZYTELNICY), key=lambda z: str(z.get("kiedy") or ""))
    zaczepieni: dict[str, list[tuple[str, object]]] = {}
    for klucz, kubel in zaczepienia().items():
        for poz in kubel["udane"]:
            zaczepieni.setdefault(_uchwyt(poz["komu"]), []).append(
                (klucz, _chwila(poz["kiedy"])))

    osobowo: dict[str, int] = {}
    datowalni = []
    for u, wpis in sorted(ludzie.items()):
        # Nieobecnosc w zrzucie OKROJONYM nie jest nieobecnoscia — takiej
        # osoby nie datujemy, choc numer zrzutu wyglada zachecajaco.
        if not wpis["absencja_pewna"]:
            continue
        granica = _chwila(zrzuty[wpis["pierwszy_zrzut"]].get("kiedy"))
        nazwy = {_nazwa(n) for n in wpis["nazwy"]}
        wczesniej = [r for r in reakcje
                     if r["kontakt"] and nazwy & set(r["kto"])
                     and r["kiedy"] and granica and r["kiedy"] < granica]
        # TA GALAZ SPRAWDZA CZAS, SIOSTRZANA DO 1 WRZESNIA 2026 NIE SPRAWDZALA.
        # Zaczepienie POZNIEJSZE niz pojawienie sie czytelnika nie moze go
        # poprzedzac — a wlasnie tak dzialalo przypisanie kanalu „obserwacja"
        # / „subskrypcja": wystarczylo, ze kiedykolwiek zaczepilismy ten
        # uchwyt, i kanal byl przyznany wstecz.
        zaczepienia_wczesniej = [z for z in zaczepieni.get(_uchwyt(u), [])
                                 if z[1] and granica and z[1] < granica]
        if wczesniej:
            ostatnia = max(wczesniej, key=lambda r: r["kiedy"])
            kanal = kanal_reakcji(ostatnia, pozycje)
        elif zaczepienia_wczesniej:
            kanal = max(zaczepienia_wczesniej, key=lambda z: z[1])[0]
        else:
            kanal = "nieznany"
        osobowo[kanal] = osobowo.get(kanal, 0) + 1
        datowalni.append({"uchwyt": u, "kanal": kanal,
                          "role": sorted(wpis["role"])})

    pozycyjnie = None
    try:
        import statystyki

        pozycyjnie = {}
        for rodzaj in ("artykul", "notka", "komentarz", "odpowiedz", "restack"):
            p = statystyki.podsumowanie(rodzaj)
            if p.get("pozycje"):
                # `pozycje_bez_zasiegu` BYLO LICZONE I WYRZUCANE TUTAJ.
                # `statystyki.py` wystawia je dokladnie po to, zeby raport
                # odroznil „zero wejsc" od „nie ma karty"; bez niego mianownik
                # tabeli byl zawyzony o wszystko, czego Substack nie policzyl
                # (16 z 63 komentarzy 1 wrzesnia 2026), a wiersz komentarzy
                # czytal sie jak „nasze komentarze nie maja zasiegu".
                bez = p.get("pozycje_bez_zasiegu", 0)
                pozycyjnie[rodzaj] = {
                    "pozycje": p["pozycje"],
                    "bez_zasiegu": bez,
                    "zmierzone": p["pozycje"] - bez,
                    "wyswietlenia": p["wyswietlenia"],
                    "subskrypcje": p["subskrypcje"],
                    "obserwacje": p["obserwacje"],
                }
    except Exception:
        # Pomiary pozycji sa DODATKIEM. Gdy `statystyki` nie da sie wczytac,
        # raport ma dalej odpowiadac na trzy pozostale pytania.
        pozycyjnie = None

    return {
        "osobowo": osobowo,
        "datowalnych": len(datowalni),
        "wszystkich_czytelnikow": len(ludzie),
        "szczegoly": datowalni,
        "pozycyjnie": pozycyjnie,
    }


# --- kontrola dla alarmu ------------------------------------------------------

# Po ilu dniach bez zrzutu uznajemy, ze pomiar oslepl. Zmierzone tempo: siedem
# zrzutow w 31 godzinach, czyli mniej wiecej co piec godzin (zrzut powstaje
# w bloku pomiarowym kazdego z pieciu dziennych przebiegow). Trzy doby to
# okolo pietnastu przebiegow z rzedu bez zapisu — to juz nie zly dzien, tylko
# awaria. Alarm chodzi o 07:00 UTC, a najswiezszy zrzut jest wtedy z okolo
# 00:13 tej samej doby, wiec prog nie ociera sie o normalna prace.
ZRZUT_STARSZY_NIZ_DNI = 3


def pomiar_oslepl() -> str | None:
    """Czy w ogole mamy z czego liczyc wzajemnosc.

    NAJCICHSZA AWARIA TEGO POMIARU TO NIE BRAK ZRZUTU, TYLKO ZRZUT OKROJONY.
    Docstring tej funkcji do 1 wrzesnia 2026 twierdzil, ze
    `browser.zapisz_czytelnikow` „przy bledzie zwraca None i NIE DOPISUJE NIC",
    wiec plik po nieudanym zrzucie wyglada jak plik po zrzucie niezleconym.
    NIEPRAWDA — i to nieprawda o kodzie, ktory ta kontrola cytowala. Bramka
    oddawala None TYLKO gdy byl blad **I OBIE** listy byly puste, a
    `kto_nas_czyta` zbiera obserwujacych ZANIM klika w zakladke „Subscribers".
    Pekniecie na samym kliknieciu zostawialo wiec obserwujacych w wyniku,
    a zrzut ZAPISYWAL SIE z pusta lista subskrybentow i bez zadnego sladu.
    Kontrola pilnujaca wylacznie swiezosci pliku przepuszczala to bez slowa:
    plik jest dzisiejszy, a pomiar polowicznie slepy.

    OD 1 WRZESNIA `browser` ZAPISUJE POLE `odczytane` i odrzuca zrzut, w
    ktorym nie odpowiedziala ZADNA zakladka. To zamyka droge dopisywania
    nowych zrzutow okrojonych, ale NIE zamyka sprawy tutaj: siedmiu zrzutow
    z 31 sierpnia i 1 wrzesnia to pole nie dotyczy, a zakladka moze tez
    odpowiedziec i oddac pustke (zmiana znacznikow na stronie). Dlatego
    `zrzuty_czytelnikow` pyta trzech swiadkow, a nie jednego.

    Skutek nie konczy sie na jednej brakujacej liczbie. Okrojony zrzut PIERWSZY
    nadaje wszystkim subskrybentom `pierwszy_zrzut > 0`, czyli pozorna
    datowalnosc — i raport zaczyna na tym budowac odpowiedz o kolejnosci
    zdarzen. Dlatego `czytelnicy()` nie ufa nieobecnosci w takim zrzucie,
    a ta kontrola o nim krzyczy.

    KOLEJNOSC PYTAN: brak pliku, brak dat, zrzut przeterminowany, zrzut
    okrojony. Kazde nastepne ma sens dopiero, gdy poprzednie odpadlo.
    """
    zrzuty = wczytaj(CZYTELNICY)
    if not zrzuty:
        return ("nie ma ANI JEDNEGO zrzutu listy czytelnikow (%s). Bez niego "
                "nie da sie powiedziec, czy ktokolwiek z zaczepionych sie "
                "odwzajemnil — a to jedyny pomiar, ktory to rozstrzyga."
                % (config.DATA_DIR / CZYTELNICY))
    ostatni = max((_chwila(z.get("kiedy")) for z in zrzuty
                   if _chwila(z.get("kiedy"))), default=None)
    if ostatni is None:
        return ("plik czytelnikow ma %d linii, ale zadna nie ma czytelnej daty "
                "— pomiar wzajemnosci jest slepy." % len(zrzuty))
    dni = (datetime.now(timezone.utc).replace(tzinfo=None) - ostatni).days
    if dni > ZRZUT_STARSZY_NIZ_DNI:
        return ("ostatni zrzut listy czytelnikow ma %d dni (%s), a zrzut "
                "powstaje przy kazdym przebiegu. Cos przestalo go zapisywac "
                "i pomiar wzajemnosci slepnie."
                % (dni, ostatni.strftime("%Y-%m-%d %H:%M")))

    # ALARMUJEMY O OKROJENIU Z OSTATNICH `ZRZUT_STARSZY_NIZ_DNI` DNI, nie
    # o kazdym w historii. Okrojenie jest szkoda TRWALA — zabiera kolejnosc
    # zdarzen wokol siebie na zawsze — ale alarm ma budzic do rzeczy, ktora da
    # sie jeszcze zrobic: sprawdzic zakladke, powtorzyc zrzut. Po tym oknie
    # zostaje w raporcie (`naglowek`, `raport`), gdzie stoi bez terminu
    # waznosci, zamiast codziennie budzic mailem o czyms sprzed miesiaca.
    # To ten sam prog, co przy swiezosci, i celowo: „zrzutu nie ma" i „zrzut
    # jest polowiczny" to ta sama awaria widziana z dwoch stron.
    wszystkie = zrzuty_czytelnikow()
    granica = (datetime.now(timezone.utc).replace(tzinfo=None)
               - timedelta(days=ZRZUT_STARSZY_NIZ_DNI))
    swieze_okrojone = [z for z in wszystkie
                       if z["okrojony"] and z["kiedy"] and z["kiedy"] >= granica]
    if swieze_okrojone:
        ost = swieze_okrojone[-1]
        ile_okrojonych = sum(1 for z in wszystkie if z["okrojony"])
        return ("zrzut listy czytelnikow z %s jest OKROJONY: %s. Zrzut zapisal "
                "sie mimo to i w pliku wyglada na udany — tak konczy sie "
                "pekniecie na jednej zakladce. Okrojonych zrzutow jest %d z "
                "%d; kazdy z nich zabiera pomiarowi kolejnosc zdarzen wokol "
                "siebie, a nie tylko jedna liczbe."
                % (ost["kiedy"].strftime("%Y-%m-%d %H:%M"),
                   "; ".join("ZERO osob w grupie `%s` (%s)" % (g, powod)
                             for g, powod in sorted(ost["okrojone"].items())),
                   ile_okrojonych, len(wszystkie)))
    return None


# --- raport -------------------------------------------------------------------

def _procent(licznik: int, mianownik: int) -> str:
    return "%d%%" % round(100 * licznik / mianownik) if mianownik else "brak mianownika"


def naglowek() -> list[str]:
    """Jeden wiersz bez zrzutow albo cztery do szesciu. Liczby z mianownikiem."""
    linie = []
    okno = okno_pomiaru()
    if not okno["zrzutow"]:
        return ["  BRAK ZRZUTOW LISTY CZYTELNIKOW — nie ma z czego liczyc "
                "wzajemnosci."]
    odw = odwzajemnienie()
    for klucz in ("obserwacja", "subskrypcja"):
        d = odw[klucz]
        if not d["udanych"]:
            linie.append(
                "  %-12s ANI JEDNEJ UDANEJ PROBY (%d nieudanych, %d pominietych)"
                " — to nie jest zero procent, to brak pomiaru"
                % (klucz, d["nieudanych"], d["pominietych"]))
        elif not d["orzekalnych"]:
            linie.append(
                "  %-12s %d udanych prob i ZADNEJ orzekalnej — kazdy trafiony"
                " byl z nami, zanim zaczela sie historia zrzutow"
                % (klucz, d["udanych"]))
        else:
            linie.append(
                "  %-12s odwzajemnilo sie %d z %d orzekalnych (%s); byli"
                " wczesniej %d, nieorzekalnych %d, niepewnych %d"
                % (klucz, len(d["odwzajemnili"]), d["orzekalnych"],
                   _procent(len(d["odwzajemnili"]), d["orzekalnych"]),
                   len(d["byli_wczesniej"]), len(d["nieorzekalne"]),
                   len(d["niepewne"])))
    skad = skad_przyszli()
    linie.append(
        "  czytelnicy   %d osob: %d z kontaktem z trescia, %d z samym "
        "zdarzeniem pozyskania, %d bez sladu"
        % (skad["czytelnikow"], len(skad["z_trescia"]),
           len(skad["tylko_pozyskanie"]), len(skad["bez_sladu"])))
    linie.append(
        "  pomiar       %d zrzutow, %.1f dnia historii — wszystko wczesniejsze "
        "jest niewidoczne" % (okno["zrzutow"], okno["dni"] or 0.0))
    pok = pokrycie()
    if pok["ostatnia"] and (pok["brakuje_obserwujacych"]
                            or pok["brakuje_subskrybentow"]):
        o = pok["ostatnia"]
        linie.append(
            "  ! niepelne   licznik profilu mowi %d obserwujacych i %d "
            "subskrybentow, z nazwiska znamy %d i %d"
            % (o["obserwujacy_licznik"], o["subskrybenci_licznik"],
               o["obserwujacy_z_nazwiska"], o["subskrybenci_z_nazwiska"]))
    okrojone = [z for z in zrzuty_czytelnikow() if z["okrojony"]]
    if okrojone:
        linie.append(
            "  ! okrojone   %d z %d zrzutow ma PUSTA grupe, ktora nie powinna"
            " byc pusta (ostatni taki: %s) — kolejnosc zdarzen wokol nich jest"
            " nieorzekalna"
            % (len(okrojone), okno["zrzutow"],
               okrojone[-1]["kiedy"].strftime("%Y-%m-%d %H:%M")
               if okrojone[-1]["kiedy"] else "bez daty"))
    return linie


def raport() -> list[str]:
    """Pelna odpowiedz na cztery pytania. Kazda liczba z mianownikiem."""
    L: list[str] = []
    okno = okno_pomiaru()
    L.append("")
    L.append("=== WZAJEMNOSC: KTO NAS CZYTA WOBEC TEGO, KOGO ZACZEPILISMY ===")
    if not okno["zrzutow"]:
        L.append("  Brak pliku %s — nie ma ani jednego zrzutu listy czytelnikow."
                 % CZYTELNICY)
        L.append("  Zadne z czterech pytan nie ma dzis odpowiedzi. To nie jest"
                 " wynik zerowy, tylko brak pomiaru.")
        return L

    L.append("  ZASIEG POMIARU: %d zrzutow, od %s do %s (%.1f dnia)."
             % (okno["zrzutow"], okno["od"].strftime("%Y-%m-%d %H:%M"),
                okno["do"].strftime("%Y-%m-%d %H:%M"), okno["dni"] or 0.0))
    slepe = slepe_okno()
    if slepe["dni"]:
        L.append("  UWAGA: najstarsze zaczepienie (%s) wyprzedza pierwszy zrzut"
                 " o %.1f dnia."
                 % (slepe["najstarsze_zaczepienie"].strftime("%Y-%m-%d"),
                    slepe["dni"]))
        L.append("  Kto w tym oknie przyszedl i odszedl, nie zostawil sladu"
                 " NIGDZIE. „Nikt sie nie odwzajemnil\" znaczy tu")
        L.append("  „nikogo takiego nie ma na tych zrzutach\", a nie „nikt"
                 " nigdy\".")
    okrojone = [z for z in zrzuty_czytelnikow() if z["okrojony"]]
    if okrojone:
        L.append("  ZRZUTY OKROJONE: %d z %d. Zrzut zapisuje sie takze wtedy,"
                 " gdy pekl klik w zakladke — z jedna" % (len(okrojone),
                                                          okno["zrzutow"]))
        L.append("  grupa pusta i bez sladu bledu w pliku. Wyglada jak pomiar,"
                 " a jest polowa pomiaru.")
        for z in okrojone:
            L.append("    %s  %s"
                     % (z["kiedy"].strftime("%Y-%m-%d %H:%M") if z["kiedy"]
                        else "bez daty",
                        "; ".join("grupa `%s` PUSTA, choc %s" % (g, powod)
                                  for g, powod in sorted(z["okrojone"].items()))))
        L.append("  Nikogo, kto pojawil sie zaraz po takim zrzucie, NIE"
                 " datujemy: jego nieobecnosc byla pozorna.")
    pok = pokrycie()
    if pok["ostatnia"]:
        o = pok["ostatnia"]
        L.append("  POKRYCIE LISTY (licznik profilu wobec imion, %d par"
                 " pomiarow):" % pok["par"])
        L.append("    obserwujacy  licznik %d, z nazwiska %d  (brakuje %d)"
                 % (o["obserwujacy_licznik"], o["obserwujacy_z_nazwiska"],
                    pok["brakuje_obserwujacych"]))
        L.append("    subskrybenci licznik %d, z nazwiska %d  (brakuje %d)"
                 % (o["subskrybenci_licznik"], o["subskrybenci_z_nazwiska"],
                    pok["brakuje_subskrybentow"]))
        if pok["brakuje_obserwujacych"] or pok["brakuje_subskrybentow"]:
            L.append("    KAZDA LICZBA NIZEJ MA WIEC ZANIZONY MIANOWNIK o tyle"
                     " osob — nie da sie ich")
            L.append("    przypisac do niczego, bo nie znamy ich imion.")

    # --- 1 -------------------------------------------------------------------
    L.append("")
    L.append("--- 1. ILU ZACZEPIONYCH SIE ODWZAJEMNILO ---")
    odw = odwzajemnienie()
    for klucz in ("obserwacja", "subskrypcja"):
        d = odw[klucz]
        L.append("  %s:" % klucz.upper())
        L.append("    prob %d (udanych %d, nieudanych %d, pominietych %d)"
                 % (d["prob"], d["udanych"], d["nieudanych"], d["pominietych"]))
        if not d["udanych"]:
            L.append("    ODPOWIEDZ: nie bylo ANI JEDNEJ udanej proby, wiec"
                     " pytanie nie ma mianownika.")
            L.append("    To NIE jest „0% odwzajemnien\" — to brak pomiaru.")
        else:
            if d["orzekalnych"]:
                L.append("    odwzajemnilo sie na pewno %d z %d orzekalnych"
                         " (%s)"
                         % (len(d["odwzajemnili"]), d["orzekalnych"],
                            _procent(len(d["odwzajemnili"]),
                                     d["orzekalnych"])))
            else:
                L.append("    ORZEKALNYCH ZERO z %d udanych prob — nie ma"
                         " mianownika, wiec nie podaje procentu."
                         % d["udanych"])
            L.append("    byli z nami JUZ PRZED zaczepieniem: %d  (to nie jest"
                     " odwzajemnienie, tylko jego odwrotnosc)"
                     % len(d["byli_wczesniej"]))
            L.append("    nieorzekalna kolejnosc: %d  (zrzuty nie"
                     " rozstrzygaja, co bylo pierwsze; historia zaczyna sie"
                     " %s)"
                     % (len(d["nieorzekalne"]),
                        okno["od"].strftime("%Y-%m-%d")))
            L.append("    niepewnych dopasowan %d (z tego we wlasciwej"
                     " kolejnosci %d), bez dopasowania %d"
                     % (len(d["niepewne"]), len(d["odwzajemnili_niepewnie"]),
                        len(d["bez"])))
            for t in d["pewne"] + d["niepewne"]:
                L.append("      %-28s -> %-28s (po: %-17s kolejnosc: %s)"
                         % (t["komu"], t["czytelnik"], t["jak"],
                            t["kolejnosc"].upper()))
            L.append("    KOLEJNOSC ZNACZY: PO = zaczepilismy, potem sie"
                     " pojawil (jedyne odwzajemnienie); PRZED = byl")
            L.append("    z nami wczesniej; NIEORZEKALNA = zrzuty nie siegaja"
                     " tak daleko, zeby to rozstrzygnac.")
            L.append("    „bez dopasowania\" NIE znaczy „nie odwzajemnil sie\":"
                     " cel bywa poddomena PUBLIKACJI,")
            L.append("    a czytelnik jest zawsze uchwytem UZYTKOWNIKA — ta"
                     " sama osoba moze miec oba rozne.")
        L.append("    proby wg ery konta: %d przed przestawieniem na AI (%s),"
                 " %d po"
                 % (d["prob_przed_kotwica"], KOTWICA_NISZY, d["prob_od_kotwicy"]))
        if d["udane_od_kotwicy"] and d["orzekalnych_od_kotwicy"] > 0:
            L.append("    z samej ery AI: odwzajemnilo sie %d z %d orzekalnych"
                     " (%s), przy %d udanych probach"
                     % (d["odwzajemnili_od_kotwicy"],
                        d["orzekalnych_od_kotwicy"],
                        _procent(d["odwzajemnili_od_kotwicy"],
                                 d["orzekalnych_od_kotwicy"]),
                        d["udane_od_kotwicy"]))
        elif d["udane_od_kotwicy"]:
            L.append("    z ery AI zadnej udanej proby nie da sie orzec —"
                     " wszyscy trafieni byli z nami wczesniej albo")
            L.append("    poza zasiegiem zrzutow. %d udanych prob, ZERO"
                     " orzekalnych." % d["udane_od_kotwicy"])
        elif d["prob_od_kotwicy"]:
            L.append("    z ery AI nie ma ANI JEDNEJ udanej proby — dzisiejszej"
                     " publicznosci ten kanal nie dotknal.")
        else:
            L.append("    PO PRZESTAWIENIU KONTA NA AI NIE BYLO ANI JEDNEJ"
                     " PROBY. Cisza tego kanalu nie jest wynikiem,")
            L.append("    tylko brakiem dzialania.")

    # --- 2 -------------------------------------------------------------------
    L.append("")
    L.append("--- 2. CZY NASI CZYTELNICY ZETKNELI SIE WCZESNIEJ Z TRESCIA ---")
    skad = skad_przyszli()
    n = skad["czytelnikow"]
    L.append("  czytelnikow na wszystkich zrzutach: %d" % n)
    L.append("    z kontaktem z trescia (polubienie/odpowiedz/restack): %d z %d (%s)"
             % (len(skad["z_trescia"]), n, _procent(len(skad["z_trescia"]), n)))
    L.append("    tylko zdarzenie pozyskania (follow/subscribe): %d z %d"
             % (len(skad["tylko_pozyskanie"]), n))
    L.append("    bez zadnego sladu: %d z %d" % (len(skad["bez_sladu"]), n))
    L.append("  DLACZEGO TRZY KUPKI, A NIE DWIE: `skutek` zawiera tez typy"
             " `follow` i `free_subscription`,")
    L.append("  czyli powiadomienia o SAMYM POZYSKANIU. Liczac je jako"
             " „wczesniejszy kontakt\" dostaje sie")
    L.append("  %d z %d, co jest kolem — obserwujacy ma zdarzenie `follow`,"
             " bo jest obserwujacym."
             % (len(skad["z_trescia"]) + len(skad["tylko_pozyskanie"]), n))
    for osoba in skad["z_trescia"]:
        L.append("    %-30s reakcji %-4d %s%s"
                 % (osoba["uchwyt"], osoba["ile"], ",".join(osoba["typy"]),
                    "" if osoba["datowalny"] else "  (kolejnosc nierozstrzygalna)"))
    if skad["nierozstrzygalna_kolejnosc"]:
        L.append("  UWAGA: %d z %d osob bylo juz w PIERWSZYM zrzucie, wiec nie"
                 " wiadomo, czy kontakt byl przed"
                 % (skad["nierozstrzygalna_kolejnosc"], n))
        L.append("  zapisaniem sie, czy po. Slowo „wczesniej\" jest dla nich"
                 " nieweryfikowalne.")
    if skad["typy_nieznane"]:
        L.append("  TYPY ZDARZEN, KTORYCH NIE UMIEM ZAKLASYFIKOWAC (nie licze"
                 " ich do niczego): %s"
                 % ", ".join("%s %d" % kv for kv in sorted(skad["typy_nieznane"].items())))

    # --- 3 -------------------------------------------------------------------
    L.append("")
    L.append("--- 3. ILE CZASU MIJA MIEDZY DZIALANIEM A ODZEWEM ---")
    op = opoznienia()
    L.append("  (a) od wystawienia tresci do reakcji:")
    if not op["na_tresc"]:
        L.append("    zadnej reakcji nie da sie polaczyc z konkretna nasza"
                 " pozycja — nie ma czego mierzyc.")
    for rodzaj, d in sorted(op["na_tresc"].items()):
        ocena = ("" if d["wystarczy_na_wniosek"]
                 else "   PROBKA ZA MALA NA WNIOSEK (prog %d)" % op["min_probka"])
        L.append("    %-11s n=%-4d mediana %.1f h (od %.1f do %.1f), do doby"
                 " %d z %d%s"
                 % (rodzaj, d["n"], d["mediana_h"], d["min_h"], d["max_h"],
                    d["do_24h"], d["n"], ocena))
        if d["odrzucone_ujemne"]:
            L.append("      (odrzucone %d reakcji starszych od tresci, na"
                     " ktora odpowiadaja — nie do zinterpretowania)"
                     % d["odrzucone_ujemne"])
    L.append("  (b) od naszego zaczepienia do pojawienia sie w liscie"
             " czytelnikow:")
    zac = op["na_zaczepienie"]
    if zac["odrzucone_byli_wczesniej"] or zac["odrzucone_nieorzekalne"]:
        L.append("    (poza pomiarem: %d trafien w ludzi, ktorzy byli z nami"
                 " PRZED zaczepieniem, i %d o nieorzekalnej"
                 % (zac["odrzucone_byli_wczesniej"],
                    zac["odrzucone_nieorzekalne"]))
        L.append("    kolejnosci — dla nich „czas odzewu\" nie ma sensu, bo"
                 " odzewu nie bylo.")
    if not zac["n"]:
        L.append("    ZERO przypadkow. Nie ma czego usredniac i nie podaje"
                 " zadnej liczby.")
        L.append("    Nie znaczy to „odzew trwa dlugo\" — znaczy „nie zdarzyl"
                 " sie ani raz w oknie pomiaru\".")
    else:
        for p in zac["przypadki"]:
            if p["datowalny"] and p["najwczesniej_h"] is not None:
                L.append("    %s -> %s: miedzy %.0f a %.0f godzin po naszym"
                         " dzialaniu"
                         % (p["komu"], p["czytelnik"], p["najwczesniej_h"],
                            p["najpozniej_h"]))
            else:
                L.append("    %s -> %s: byl juz w pierwszym zrzucie, opoznienia"
                         " nie da sie policzyc"
                         % (p["komu"], p["czytelnik"]))
        if not zac["wystarczy_na_wniosek"]:
            L.append("    PROBKA ZA MALA NA WNIOSEK: %d przypadkow przy progu"
                     " %d." % (zac["n"], op["min_probka"]))

    # --- 4 -------------------------------------------------------------------
    L.append("")
    L.append("--- 4. KTORY KANAL POPRZEDZA POZYSKANIE ---")
    kan = kanaly()
    L.append("  OSOBOWO (tylko ci, ktorych pojawienie sie da sie datowac:"
             " %d z %d):"
             % (kan["datowalnych"], kan["wszystkich_czytelnikow"]))
    if not kan["datowalnych"]:
        L.append("    zaden czytelnik nie doszedl po pierwszym zrzucie — nie ma"
                 " czego przypisywac.")
    for kanal, ile in sorted(kan["osobowo"].items(), key=lambda kv: -kv[1]):
        L.append("    %-12s %d" % (kanal, ile))
    if kan["osobowo"].get("nieznany") == kan["datowalnych"] and kan["datowalnych"]:
        L.append("    ZADNEMU z nich nie poprzedza w dzienniku nasz kontakt."
                 " Odpowiedz brzmi „nie wiadomo\",")
        L.append("    a nie „zadnym kanalem\".")
    if kan["pozycyjnie"]:
        L.append("  POZYCYJNIE (przypisanie SAMEGO SUBSTACKA, per wpis, nie per"
                 " osoba):")
        suma = 0
        for rodzaj, d in sorted(kan["pozycyjnie"].items(),
                                key=lambda kv: -kv[1]["subskrypcje"]):
            suma += d["subskrypcje"]
            L.append("    %-11s %3d pozycji, POLICZONYCH PRZEZ SUBSTACK %3d"
                     " (bez kart zasiegu %2d), %5d wyswietlen -> %d"
                     " subskrypcji, %d obserwacji"
                     % (rodzaj, d["pozycje"], d["zmierzone"], d["bez_zasiegu"],
                        d["wyswietlenia"], d["subskrypcje"], d["obserwacje"]))
        bez = {r: d for r, d in kan["pozycyjnie"].items() if d["bez_zasiegu"]}
        if bez:
            # DLACZEGO TO STOI TAK BLISKO TABELI. Pozycja bez karty zasiegu
            # zapisuje sie zerem, wiec podnosi mianownik i nie podnosi
            # licznika. Kanal, ktorego Substack nie liczy (komentarze), wychodzi
            # wtedy slabszy od kanalu, ktory liczy zawsze (artykuly) — nie
            # dlatego, ze jest slabszy, tylko dlatego, ze jest niepoliczony.
            najgorszy = max(bez.items(),
                            key=lambda kv: kv[1]["bez_zasiegu"] / kv[1]["pozycje"])
            pelne = [r for r, d in kan["pozycyjnie"].items()
                     if not d["bez_zasiegu"]]
            L.append("    UWAGA: %d pozycji w tej tabeli Substack W OGOLE NIE"
                     " POLICZYL — nie maja kart zasiegu i wchodza"
                     % sum(d["bez_zasiegu"] for d in bez.values()))
            L.append("    do niej z zerem. Najbardziej dotkniety kanal: `%s`"
                     " (%d z %d niepoliczonych)."
                     % (najgorszy[0], najgorszy[1]["bez_zasiegu"],
                        najgorszy[1]["pozycje"]))
            if pelne:
                L.append("    Karty dla WSZYSTKICH swoich pozycji maja: %s."
                         % ", ".join("`%s`" % r for r in sorted(pelne)))
            L.append("    POROWNANIE KANALOW JEST WIEC NIESPRAWIEDLIWE W JEDNA"
                     " STRONE i nie wolno z tej tabeli czytac")
            L.append("    „komentarz jest slabszy od artykulu\" — mozna czytac"
                     " tylko „komentarzy nikt nie policzyl\".")
        L.append("    suma przypisan %d wobec %d osob na liscie czytelnikow —"
                 " reszta nie jest przypisana"
                 % (suma, kan["wszystkich_czytelnikow"]))
        L.append("    do zadnej pozycji. To jest inny pomiar niz osobowy"
                 " i nie zastepuje go.")
    return L


def main() -> None:
    for linia in raport():
        print(linia)
    ostrzezenie = pomiar_oslepl()
    if ostrzezenie:
        print("\n  ! %s" % ostrzezenie)


if __name__ == "__main__":
    main()
