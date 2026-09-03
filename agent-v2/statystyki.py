"""Statystyki wystawionych pozycji: kto to zobaczyl i co z tego wyniklo.

Wlasciciel pyta o jedna rzecz: ile osob weszlo z KONKRETNEJ notki, restacka
albo artykulu i ile z nich zaczelo subskrybowac lub obserwowac. Dziennik
dzialan (`dziennik.jsonl`) tego nie wie — zapisuje, ze notka wyszla, i na tym
konczy pomoc. Odpowiedz jest w `/api/v1/note_stats/c-{ID}`, w karcie
`interactions`: opis endpointu wprost wymienia subscribes i follows jako
interakcje.

ZMIERZONE NA ZYWO, notka 321505067 (ta sama probka stoi w tescie):

    wyswietlenia 17
    powierzchnie  Feed 8, Other 5, Permalinks 3, Profile page 1   (razem 17)
    odbiorcy      Unconnected 8, Subscribers 1, Followers 0
    interakcje    6 = Like 4 + Reply 2

Trzy rzeczy z tego pomiaru zdecydowaly o ksztalcie modulu:

1. Karta `audience` NIE odpowiada na pytanie wlasciciela. „Subscribers 1"
   znaczy „jeden subskrybent to zobaczyl", a nie „jedna osoba sie zapisala".
   Pomylenie tych dwoch liczb daloby raport chwalacy sie konwersja, ktorej nie
   bylo. Subskrypcje i obserwacje czytamy WYLACZNIE z karty `interactions`.

2. Tytuly w `interactions` naleza do Substacka, nie do nas. Widzielismy dwa
   ("Like", "Reply"), opis endpointu wymienia osiem. Nieznany tytul NIE MOZE
   wywalac parsera ani wypadac po cichu: sygnal, ktorego nie widzimy, nie
   istnieje — dokladnie tak przez siedem dni „nie istnialy" nieudane
   obserwacje, bo blok bez przycisku odchodzil bez wpisu.

3. `lastUpdatedAt` rusza sie mniej wiecej raz na godzine. Pomiar co pol godziny
   dopisze dwie linie z tym samym polem `zmierzone` — i tylko po nim da sie
   odroznic realny przyrost od powtornego odczytania tej samej liczby.

Plik `data/statystyki.jsonl` trzyma JEDNA LINIE NA POMIAR, nie na pozycje.
Statystyki rosna w czasie; nadpisywanie ostatniej wartosci kasuje jedyna rzecz,
ktora mowi, czy notka zbiera dalej, czy umarla po godzinie.

W tym pliku nie ma ani jednej funkcji chodzacej do sieci — celowo. JSON-a
pobiera `browser.api_json(page, "/api/v1/note_stats/c-321505067")`, a wszystko
ponizej dziala bez przegladarki, wiec test jest darmowy, szybki i nie dotyka
konta.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import config

NAZWA_PLIKU = "statystyki.jsonl"

# Tytul interakcji -> stale pole rekordu. Klucze male, bo o wielkosci liter ani
# o liczbie mnogiej w tych tytulach nie decydujemy my.
#
# ZMIERZONE sa tylko "Like" i "Reply" (notka 321505067, 4 i 2). Reszta pochodzi
# z opisu endpointu, a formy mnogie dopisane sa dlatego, ze kosztuja jedna
# linijke, a brak mapowania nie wyglada jak blad: raport pokazalby po prostu
# zero subskrypcji, czyli tez liczbe — i nikt by jej nie zakwestionowal.
#
# Ta tabela NIE JEST FILTREM. Kazdy tytul, znany czy nie, trafia do slownika
# `interakcje`; tabela decyduje wylacznie o tym, ktore liczby dostaja wlasne
# pole na wierzchu rekordu, zeby raport nie musial zgadywac pisowni.
POLA_INTERAKCJI = {
    "like": "polubienia", "likes": "polubienia",
    "reply": "odpowiedzi", "replies": "odpowiedzi",
    "restack": "restacki", "restacks": "restacki",
    "subscribe": "subskrypcje", "subscribes": "subskrypcje",
    "subscription": "subskrypcje", "subscriptions": "subskrypcje",
    "follow": "obserwacje", "follows": "obserwacje",
    "link click": "klikniecia_w_link", "link clicks": "klikniecia_w_link",
}

# Pola liczbowe, ktore rekord ma ZAWSZE, takze gdy karty nie bylo. Brak karty
# daje zero, a nie brak klucza: raport, ktory raz dostaje slownik z polem
# `subskrypcje`, a raz bez, wywala sie na pierwszej pozycji, ktorej nikt nie
# polubil — czyli na najczestszym przypadku.
POLA_ZEROWE = ("polubienia", "odpowiedzi", "restacki", "subskrypcje",
               "obserwacje", "klikniecia_w_link")


# --- parsowanie (bez sieci) ---------------------------------------------------

def _liczba(x) -> int:
    """Cokolwiek z API -> int. Nigdy nie rzuca.

    `value` bywa None (karta juz jest, licznika jeszcze nie ma) i bywa napisem —
    Substack formatuje wieksze liczby przecinkiem ("1,204"). Jeden wyjatek
    `int(None)` w parserze statystyk zabralby caly przebieg, a statystyki sa
    dodatkiem: agent ma dzialac dalej takze wtedy, gdy ich nie ma.

    Czego tu NIE MA: skrotow typu "1.2K". Przy zmierzonych wolumenach (17
    wyswietlen na notke) Substack oddaje liczby wprost, wiec zgadywanie ksztaltu
    skrotu byloby norma bez pomiaru. Gdyby kiedys przyszedl, wpadnie na 0 i
    zobaczymy to jako pozycje bez wyswietlen mimo interakcji.
    """
    # bool jest podklasa int-a. `True` zliczone jako jedno wyswietlenie to
    # liczba wygladajaca na pomiar, a bedaca literowka w API.
    if isinstance(x, bool):
        return 0
    if isinstance(x, (int, float)):
        return int(x)
    if isinstance(x, str):
        # PROCENT TO NIE LICZNIK. Stalo tu `.rstrip("%")`, czyli "47%" wracalo
        # jako 47 — a probka z API MA obok pole `percent`, wiec ksztalt
        # procentowy w tym slowniku istnieje i moze kiedys trafic do `value`.
        # Skutek bylby cichy i wiarygodny: notka z 17 wyswietleniami
        # pokazywalaby 76 wejsc z powierzchni (47+29) i 50 polubien zamiast 4.
        # Liczba wygladajaca rozsadnie, ktorej nikt nie zakwestionuje — czyli
        # najgorsza klasa bledu, jaka ten projekt zna.
        #
        # Udzialu NIE PRZELICZAMY na sztuki, bo do tego trzeba by znac
        # podstawe, a jesli API oddaje procent w polu wartosci, to znaczy, ze
        # zmienilo kontrakt i trzeba na to spojrzec, a nie zgadywac.
        czysty = x.strip()
        if czysty.endswith("%"):
            return 0
        czyste = czysty.replace(",", "").replace(" ", "")
        try:
            return int(float(czyste))
        except ValueError:
            return 0
    return 0


def _karty(dane) -> dict:
    """`cards` -> {cardId: karta}. Odporne na `cards` = None i wpisy bez id.

    `cards` jako None to nie hipoteza: endpoint odpowiada takze na notki, ktore
    nie zebraly jeszcze zadnego wyswietlenia, a wtedy nie ma czego rysowac.
    """
    wynik: dict[str, dict] = {}
    if not isinstance(dane, dict):
        return wynik
    karty = dane.get("cards")
    if not isinstance(karty, list):
        return wynik
    for k in karty:
        if isinstance(k, dict) and isinstance(k.get("cardId"), str):
            wynik[k["cardId"]] = k
    return wynik


def _pozycje(karta) -> dict:
    """`items` listCarda -> {tytul: liczba}, w kolejnosci z API.

    Powtorzony tytul jest DODAWANY, nie nadpisywany. Gdyby lista kiedys
    przyszla w dwoch kawalkach, nadpisanie pokazaloby ostatni kawalek jako
    calosc — czyli liczbe mniejsza od prawdy, wygladajaca na prawdziwa.
    """
    wynik: dict[str, int] = {}
    if not isinstance(karta, dict):
        return wynik
    items = karta.get("items")
    if not isinstance(items, list):
        return wynik
    for it in items:
        if not isinstance(it, dict):
            continue
        tytul = it.get("title")
        if not isinstance(tytul, str) or not tytul.strip():
            continue
        tytul = tytul.strip()
        wynik[tytul] = wynik.get(tytul, 0) + _liczba(it.get("value"))
    return wynik


def _suma(karta) -> int:
    """Liczba zbiorcza z karty: `value`, `count`, `total`, naglowek, suma pozycji.

    Zmierzona jest WARTOSC (17 wyswietlen, 6 interakcji), nie nazwa pola, pod
    ktorym stoi — probka przyszla do mnie opisana, nie zrzucona. Zamiast wybrac
    jedno miejsce i przy pomylce cicho raportowac zero, czytamy po kolei
    miejsca, ktore w tym API wystepuja; dla karty `interactions` suma stoi w
    `headers[0]["value"]` i wynosila 6.

    Ostatnia deska: suma pozycji. Dla probki 321505067 zgadza sie z naglowkiem
    (Like 4 + Reply 2 = 6), wiec nie jest to inna liczba, tylko ta sama liczona
    inaczej.
    """
    if not isinstance(karta, dict):
        return 0
    for pole in ("value", "count", "total"):
        if karta.get(pole) is not None:
            return _liczba(karta[pole])
    naglowki = karta.get("headers")
    if isinstance(naglowki, list) and naglowki:
        pierwszy = naglowki[0]
        if isinstance(pierwszy, dict) and pierwszy.get("value") is not None:
            return _liczba(pierwszy["value"])
    return sum(_pozycje(karta).values())


def z_kart(dane: dict) -> dict:
    """Odpowiedz `/api/v1/note_stats/c-{ID}` -> plaski rekord o stalych kluczach.

    Cala funkcja jest czysta: bierze slownik, oddaje slownik, nie dotyka ani
    sieci, ani dysku. Dzieki temu jedyna czesc, ktora naprawde moze sie pomylic
    w liczeniu, jest w calosci testowalna bez przegladarki.

    Klucze zawsze te same, niezaleznie od tego, ilu kart brakuje:
        wyswietlenia, powierzchnie, odbiorcy, interakcje, interakcje_razem,
        polubienia, odpowiedzi, restacki, subskrypcje, obserwacje,
        klikniecia_w_link, zmierzone, wystawione

    `interakcje_razem` to naglowek karty, czyli liczba OD SUBSTACKA, podczas gdy
    `interakcje` sumuja sie z pozycji. Trzymamy obie, bo ich roznica jest
    jedynym sygnalem, ze lista pozycji czegos nie pokazala.
    """
    karty = _karty(dane)

    powierzchnie = _pozycje(karty.get("surfaces"))
    odbiorcy = _pozycje(karty.get("audience"))
    interakcje = _pozycje(karty.get("interactions"))

    # WYSWIETLENIA: karta zbiorcza ALBO suma powierzchni, ktorekolwiek wieksze.
    #
    # Zmierzone recznie 25 sierpnia na dwunastu notkach. Dla dojrzalych obie
    # liczby zgadzaly sie co do jednego: 26=26, 19=19, 14=14, 12=12. Ale notka
    # wystawiona tego samego dnia miala w karcie zbiorczej ZERO, a w rozbiciu
    # po powierzchniach osiem — czyli raport pokazywal wpis bez ani jednego
    # wejscia, ktory realnie mial osiem.
    #
    # Powod jest zapisany wyzej przy `_suma`: nazwy pola z liczba wyswietlen
    # nie mielismy zmierzonej, wiec czytamy po kolei kilka kandydatow. Przy
    # swiezej notce karta zbiorcza najwyrazniej jeszcze zadnego z nich nie
    # niesie, a rozbicie juz tak.
    #
    # Bierzemy wieksza. Powierzchnie to te same wyswietlenia w rozbiciu, wiec
    # ich suma NIE MOZE przekroczyc calosci — a gdy przekracza, to znaczy, ze
    # calosci wlasnie nie znamy.
    _z_karty = _suma(karty.get("impressions"))
    _z_powierzchni = sum(powierzchnie.values())
    rekord: dict = {
        "wyswietlenia": max(_z_karty, _z_powierzchni),
        "powierzchnie": powierzchnie,
        "odbiorcy": odbiorcy,
        "interakcje": interakcje,
        "interakcje_razem": _suma(karty.get("interactions")),
    }
    for pole in POLA_ZEROWE:
        rekord[pole] = 0
    for tytul, ile in interakcje.items():
        pole = POLA_INTERAKCJI.get(tytul.lower())
        if pole:
            rekord[pole] += ile
        # Tytul spoza tabeli nie ma wlasnego pola i to jest cala kara: siedzi
        # dalej w `interakcje`, wiec suma sie zgadza, a nowy rodzaj interakcji
        # zobaczymy w pliku, zamiast dowiedziec sie o nim z wyjatku.

    zmierzone = dane.get("lastUpdatedAt") if isinstance(dane, dict) else None
    rekord["zmierzone"] = zmierzone if isinstance(zmierzone, str) else ""

    # LICZNIKI Z KARTY `note` — JEDYNE, KTORE SA ZAWSZE.
    #
    # ZMIERZONE 31 sierpnia na zywym koncie. Komentarz pod cudzym ARTYKULEM
    # dostaje z tej koncowki JEDNA karte (`note`), a nie piec, gdy nie zebral
    # ani jednego wejscia:
    #
    #     bez kart:  ['note']
    #     z kartami: ['note', 'impressionValues', 'surfaces', 'audience',
    #                 'interactions']
    #
    # Z 52 naszych komentarzy 37 mialo sama karte podgladu. Dotad zapisywalismy
    # dla nich same zera i nie dalo sie odroznic „nikt nie zobaczyl" od „nie
    # wiemy".
    #
    # A KARTA `note` NIESIE LICZNIKI ZAWSZE — `like_count`, `restack_count`,
    # `reply_count` — takze wtedy, gdy kart statystyk brak. Czytalismy ja
    # wylacznie po date wystawienia i wyrzucalismy reszte.
    #
    # Karta zbiorcza ma pierwszenstwo, gdy jest: pochodzi z panelu statystyk
    # i bywa pelniejsza. Liczniki `note` sa DROGA ZAPASOWA, nie nadpisaniem.
    _n = _karty(dane).get("note")
    for _klucz in ("note", "note"):
        _n = _n.get(_klucz) if isinstance(_n, dict) else None
    if isinstance(_n, dict):
        for _pole, _skad in (("polubienia", "like_count"),
                             ("restacki", "restack_count"),
                             ("odpowiedzi", "reply_count")):
            if not rekord.get(_pole):
                rekord[_pole] = _liczba(_n.get(_skad))

    # CZY SUBSTACK W OGOLE POLICZYL ZASIEG. Bez tego pola raport nie odrozni
    # „zero wejsc" od „nie ma karty" — a to ta sama pomylka, przez ktora
    # zapisany wiersz zerowy wygladal jak dzien, w ktorym wszyscy odeszli.
    rekord["ma_karty_zasiegu"] = bool(karty.get("impressions")
                                      or karty.get("surfaces")
                                      or karty.get("impressionValues"))

    # KIEDY TO WYSTAWILISMY — bez tego pomiaru nie da sie z niczym porownac.
    #
    # `zmierzone` mowi, kiedy PYTALISMY, i to jest zupelnie inna data: pomiary
    # sa zawsze swieze, takze te notek sprzed miesiaca. Przy probie rozdzielenia
    # epoki AI od epoki o ukrytych systemach trzeba bylo laczyc kazda pozycje
    # z dziennikiem po numerze — a dziennik numerow starszych notek nie ma
    # (z 29 wystawionych mial SZESC). Dziesieciu notek na 37 nie dalo sie
    # przypisac do zadnej epoki.
    #
    # Substack podaje te date w karcie `note`, obok tresci. Zapisujemy ja
    # przy KAZDYM pomiarze, wiec plik statystyk przestaje zalezec od tego,
    # czy nasza wlasna ksiegowosc zapamietala numer.
    # `or {}` CHRONI PRZED PUSTA WARTOSCIA, NIE PRZED ZLYM TYPEM. Pierwsza
    # wersja szla lancuchem `.get(...) or {}` i wywalala sie AttributeError,
    # gdy `note` bylo napisem zamiast slownika — a wyjatek tutaj zabralby caly
    # pomiar, bo statystyki sa dodatkiem, nie warunkiem dzialania.
    wystawione = _karty(dane).get("note")
    for klucz in ("note", "note", "timestamp"):
        if not isinstance(wystawione, dict):
            wystawione = None
            break
        wystawione = wystawione.get(klucz)
    rekord["wystawione"] = wystawione if isinstance(wystawione, str) else ""
    return rekord


# --- historia pomiarow --------------------------------------------------------

def _plik():
    """Sciezka liczona przy KAZDYM wywolaniu, nie raz przy imporcie.

    `browser.DZIENNIK` jest stala modulu i przez to nie da sie go przekierowac
    w tescie bez reimportu; `stages.py` sklada te sama sciezke za kazdym razem
    i to ta wersja jest testowalna. Powtarzamy wariant testowalny, bo modul bez
    testu jest tu wart tyle, co licznik trzymany w pamieci jednego przebiegu.
    """
    return config.DATA_DIR / NAZWA_PLIKU


def zapisz(rodzaj: str, identyfikator: str, rekord: dict, tekst: str = "") -> None:
    """Dopisuje JEDEN pomiar. Nigdy nie przerywa dzialania agenta.

    `rodzaj` to "notka", "restack" albo "artykul". Nie odrzucamy innych: zapis,
    ktory ocenia dane wejsciowe, potrafi wyrzucic jedyna kopie pomiaru, a plik
    jest tylko do czytania przez nas.

    Jedna linia na pomiar. Ta sama notka zmierzona dziesiec razy to dziesiec
    linii i tak ma byc — dopiero z nich widac, czy 17 wyswietlen to koniec, czy
    polowa drogi.
    """
    try:
        wpis = dict(rekord) if isinstance(rekord, dict) else {}
        # Pola opisowe nadpisuja rekord, a nie odwrotnie. Gdyby w API pojawila
        # sie kiedys karta o tytule "rodzaj" albo "id", linia przestalaby byc
        # odnajdywalna po rodzaju i identyfikatorze — czyli po jedynych dwoch
        # rzeczach, po ktorych ten plik sie w ogole czyta.
        wpis.update({
            "kiedy": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "rodzaj": str(rodzaj),
            "id": str(identyfikator),
            # Skrot, nie tresc: to pole sluzy rozpoznaniu pozycji w raporcie
            # („ta o sloiku szamponu"), a pelny tekst i tak lezy w dzienniku
            # dzialan. Bez skrotu plik rosnie o notke na kazdy odczyt.
            "tekst": (tekst or "")[:200],
        })
        plik = _plik()
        plik.parent.mkdir(parents=True, exist_ok=True)
        with open(plik, "a", encoding="utf-8") as f:
            # `default=str` zamiast wyjatku: jedna nieserializowalna wartosc
            # z nieznanej karty nie moze skasowac calego pomiaru.
            f.write(json.dumps(wpis, ensure_ascii=False, default=str) + "\n")
    except Exception as e:
        # Glosniej niz `browser.zapisz_w_dzienniku`, ktore milczy calkiem.
        # Brak wpisu w dzienniku dzialan widac po zerowym liczniku wolumenow;
        # brak pomiaru statystyk nie ma ZADNEGO objawu — plik bez linii wyglada
        # identycznie jak konto, ktore jeszcze nic nie wystawilo.
        try:
            print("[statystyki] nie zapisalem pomiaru %s %s: %s"
                  % (rodzaj, identyfikator, e))
        except Exception:
            pass


def wczytaj(rodzaj: str | None = None) -> list[dict]:
    """Wszystkie pomiary z pliku, w kolejnosci zapisu. Uszkodzone linie pomija.

    Linia ucieta w polowie to nie hipoteza: proces ginacy w trakcie zapisu
    zostawia dokladnie taki slad, a w tym projekcie SIGTERM w zwloce przed
    notkami uszkodzil siedem przebiegow w ciagu tygodnia (`df3de64`). Jedna
    polowiczna linia nie moze skasowac historii wszystkich pozostalych.

    Plik czytamy z `errors="replace"` z tego samego powodu: przerwany zapis
    potrafi zostawic pol znaku UTF-8, a `UnicodeDecodeError` na calym pliku
    zabralby dane, ktore sa czytelne w 99 liniach na 100.
    """
    plik = _plik()
    if not plik.exists():
        return []
    wynik: list[dict] = []
    try:
        tresc = plik.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    for linia in tresc.splitlines():
        linia = linia.strip()
        if not linia:
            continue
        try:
            w = json.loads(linia)
        except ValueError:
            continue
        if not isinstance(w, dict):
            continue
        if rodzaj and w.get("rodzaj") != rodzaj:
            continue
        wynik.append(w)
    return wynik


def najnowsze_per_pozycja(rodzaj: str | None = None) -> dict:
    """{identyfikator: ostatni pomiar}. To sie czyta przy raporcie.

    „Ostatni" znaczy NAJPOZNIEJSZE `kiedy`, a nie „ostatnia linia w pliku".
    Roznica jest realna: pomiary dopisuja sie z roznych blokow jednego
    przebiegu, a przebiegi potrafia sie na siebie nasunac (sama zwloka przed
    notkami trwa minuty), wiec kolejnosc linii nie jest gwarantowana
    kolejnoscia czasu. Znaczniki sa w ISO-8601 UTC, wiec porownanie napisow
    jest porownaniem chwil; przy identycznym `kiedy` wygrywa pozniejsza linia.

    UWAGA na klucz: identyfikator notki pochodzi z innej puli niz identyfikator
    artykulu (comment id kontra post id), wiec przy `rodzaj=None` teoretycznie
    moga sie zderzyc. Gdy to ma znaczenie, podaj `rodzaj`.
    """
    najnowsze: dict[str, dict] = {}
    for w in wczytaj(rodzaj):
        klucz = str(w.get("id") or "")
        if not klucz:
            continue
        stary = najnowsze.get(klucz)
        if stary is None or str(w.get("kiedy") or "") >= str(stary.get("kiedy") or ""):
            najnowsze[klucz] = w
    return najnowsze


def podsumowanie(rodzaj: str | None = None) -> dict:
    """Sumy i srednie PO POZYCJACH, nie po pomiarach.

    To jest jedyne miejsce, w ktorym ten modul moze sklamac w sposob niewidoczny.
    Notka mierzona co godzine przez dziesiec godzin daje dziesiec linii po 17
    wyswietlen; suma po liniach to 170 i wyglada jak sukces. Dlatego sumujemy
    `najnowsze_per_pozycja`, a `pomiary` raportujemy osobno — zeby roznica
    miedzy 1 pozycja a 10 pomiarami byla widoczna, a nie ukryta.

    `najlepsza` wybiera po subskrypcjach, przy remisie po wyswietleniach — bo
    pytanie wlasciciela brzmi „co przynioslo ludzi", a nie „co bylo widoczne".
    Obserwacje sumujemy osobno: Substack liczy je jako inna interakcje niz
    subskrypcje i sklejenie ich zatarloby, ktora droga ktos naprawde przyszedl.
    """
    pozycje = najnowsze_per_pozycja(rodzaj)
    lista = list(pozycje.values())

    def _suma_pola(pole: str) -> int:
        return sum(_liczba(p.get(pole)) for p in lista)

    wyswietlenia = _suma_pola("wyswietlenia")
    najlepsza = None
    if lista:
        klucz, poz = max(
            pozycje.items(),
            key=lambda kv: (_liczba(kv[1].get("subskrypcje")),
                            _liczba(kv[1].get("wyswietlenia"))))
        najlepsza = {
            "id": klucz,
            "rodzaj": poz.get("rodzaj", ""),
            "tekst": poz.get("tekst", ""),
            "subskrypcje": _liczba(poz.get("subskrypcje")),
            "obserwacje": _liczba(poz.get("obserwacje")),
            "wyswietlenia": _liczba(poz.get("wyswietlenia")),
        }
    # Pozycje, dla ktorych Substack POLICZYL zasieg. Rekordy sprzed
    # 31 sierpnia 2026 nie maja tego pola — traktujemy je jak zmierzone,
    # bo inaczej cala historia wypadlaby z mianownika.
    zmierzone_zasiegiem = [p for p in lista
                           if p.get("ma_karty_zasiegu", True)]
    return {
        "pozycje": len(lista),
        # Liczba linii, nie pozycji. Stoi obok celowo: gdy ktos zobaczy 1
        # pozycje i 10 pomiarow, nie zapyta, czemu suma nie rosnie.
        "pomiary": len(wczytaj(rodzaj)),
        "wyswietlenia": wyswietlenia,
        "polubienia": _suma_pola("polubienia"),
        "odpowiedzi": _suma_pola("odpowiedzi"),
        "restacki": _suma_pola("restacki"),
        "subskrypcje": _suma_pola("subskrypcje"),
        "obserwacje": _suma_pola("obserwacje"),
        # KLIKNIECIA W LINK BYLY PARSOWANE, ZAPISYWANE I NIGDZIE NIE CZYTANE.
        # A to jedyne pole odpowiadajace wprost na pytanie „ile osob WESZLO
        # z tej notki" — bez niego notka z czterdziestoma kliknieciami i zerem
        # subskrypcji jest w raporcie nieodrozninalna od notki, ktorej nikt nie
        # tknal. Sygnal, ktorego nie widzimy, nie istnieje.
        "klikniecia_w_link": _suma_pola("klikniecia_w_link"),
        # SPRAWDZENIE SPOJNOSCI, nie ozdoba. `interakcje_razem` to suma OD
        # SUBSTACKA, a nizej sumujemy pozycje z listy. Roznica znaczy, ze lista
        # czegos nie pokazala — nowego rodzaju interakcji albo zmiany kontraktu
        # API. Dotad ta liczba byla wyliczana i wyrzucana, czyli byla martwa
        # obietnica: docstring twierdzil, ze to nasz jedyny sygnal ostrzegawczy,
        # a nikt go nie czytal.
        "interakcje_razem": _suma_pola("interakcje_razem"),
        "interakcje_z_pozycji": sum(
            sum(_liczba(v) for v in (p.get("interakcje") or {}).values())
            for p in lista),
        # DZIELIMY PRZEZ ZMIERZONE, NIE PRZEZ WSZYSTKIE.
        #
        # Substack nie liczy zasiegu wpisow, ktore nic nie zebraly — takie
        # dostaja JEDNA karte zamiast pieciu i zapisuja sie z zerem. Zmierzone
        # na produkcji: 37 z 52 komentarzy. Wliczanie ich do mianownika
        # zanizalo srednia okolo trzy i pol raza i czytalo sie jak „nasze
        # komentarze nie maja zasiegu", podczas gdy czesc z nich po prostu nie
        # zostala policzona.
        #
        # `ma_karty_zasiegu` powstalo wlasnie po to i do tej pory nie bylo
        # czytane NIGDZIE poza testami — sygnal wytworzony i wyrzucony,
        # dziesiaty raz ten ksztalt.
        "srednia_wyswietlen": round(
            wyswietlenia / len(zmierzone_zasiegiem), 2)
        if zmierzone_zasiegiem else 0.0,
        "pozycje_bez_zasiegu": len(lista) - len(zmierzone_zasiegiem),
        "najlepsza": najlepsza,
    }
