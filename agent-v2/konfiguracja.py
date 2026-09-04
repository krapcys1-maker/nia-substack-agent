# -*- coding: utf-8 -*-
"""Wczytanie `konfiguracja.toml` — jeden plik zamiast polowania po 88 plikach.

## Po co to jest

Do 2026-09-03 przestawienie bota na inne konto i inny temat znaczylo edycje
w kilkudziesieciu miejscach: uchwyt w DWOCH niezaleznych stalych, nisza
w czterech listach, wolumeny w kilkunastu, modele w slowniku na 26 pozycji.
Mapa `docs/MAPA_KONFIGURACJI.md` wyliczyla to co do linii. Ten plik zamyka
czesc pierwsza tamtej listy: wartosci, ktore da sie podac, zamiast ich szukac.

## Czego ten modul NIE robi

**Nie zastepuje `config.py`.** `config.py` zostaje jedynym zrodlem prawdy:
przelicza sufity tokenow, wywodzi sciezki, sprawdza spojnosc. Ten modul tylko
PODAJE mu wartosci. Konfiguracja nie podejmuje decyzji, tylko je zapisuje.

**Nie wystawia wszystkiego.** Trzy rzeczy sa celowo poza plikiem, bo wygladaja
na pola, a sa decyzjami:

  * sufit miesieczny jako „nieograniczony" — to jedyna twarda blokada
    w systemie; furtka `AGENT_V2_NO_LIMIT` juz istnieje i jest zmienna
    srodowiskowa, a nie domyslna wartoscia w pliku. Stalo tu `NIA_NO_LIMIT`
    — nazwa, ktorej nie czyta ANI JEDNA linia w tym repozytorium, ta sama
    klasa co `NIA_SERVER` w komunikacie `browser.py`;
  * progi bramek (`SLOW_NA_BEAT`, `BUDZET_ZASTRZEZEN`, `MIN_ZRODEL_DO_PISANIA`)
    — to wyniki pomiarow na konkretnych tekstach; wystawione jako suwaki
    zostana pokrecone w strone „mniej blokuje", bo tak zawsze idzie;
  * `WYLACZ_WYKRYWANIE_AI` — w `config.py` stoi wprost, ze to „wybor publiczny,
    nie ustawienie techniczne". Zostaje tam, razem z uzasadnieniem.

## Jak dziala

Plik jest OPCJONALNY. Jego brak znaczy „zostaw wartosci z `config.py`", wiec
istniejaca instalacja nie zmienia zachowania przez samo pojawienie sie tego
modulu.

Kazde pole jest sprawdzane przy wczytaniu i **oblewa glosno**, a nie po cichu:
zla wartosc w konfiguracji ma zatrzymac start, a nie wyjsc na jaw po tygodniu
jako dziwne zachowanie. Nieznany klucz tez jest bledem — literowka w nazwie
pola jest najczestszym sposobem, w jaki konfiguracja „nie dziala" bez sladu.

Wymaga Pythona 3.11 (`tomllib` w bibliotece standardowej). To JEDYNE miejsce
w calym agencie, ktore tego wymaga.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

NAZWA_PLIKU = "konfiguracja.toml"


class BledKonfiguracji(RuntimeError):
    """Konfiguracja jest zla i przebieg ma sie NIE zaczac."""


# Ksztalt pliku. Klucz to sciezka `sekcja.pole`, wartosc to (nazwa stalej
# w config.py, sprawdzacz). Zamknieta lista, bo nieznany klucz ma byc bledem.
#
# `None` jako nazwa stalej znaczy: pole jest obslugiwane osobno w `zastosuj`,
# bo trafia gdzie indziej niz do stalej o tej samej nazwie.
def _napis(v: Any, gdzie: str) -> str:
    if not isinstance(v, str) or not v.strip():
        raise BledKonfiguracji("%s: oczekiwano niepustego napisu, jest %r" % (gdzie, v))
    return v


def _data_albo_pusto(v: Any, gdzie: str) -> str:
    """Dzien w postaci RRRR-MM-DD albo pusty napis znaczacy „nigdy".

    Sprawdzamy KSZTALT, nie istnienie takiego dnia w kalendarzu. Data jest
    porownywana z napisami w indeksie leksykograficznie, wiec „2026-8-25"
    z jedna cyfra miesiaca porownuje sie zle i nie daje po sobie zadnego
    znaku — odrzucamy ja tutaj, a nie pol roku pozniej.
    """
    import re as _re
    if not isinstance(v, str):
        raise BledKonfiguracji("%s: oczekiwano napisu, jest %r" % (gdzie, v))
    if v and not _re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        raise BledKonfiguracji(
            "%s: oczekiwano daty RRRR-MM-DD albo pustego napisu, jest %r"
            % (gdzie, v))
    return v


def _liczba(v: Any, gdzie: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise BledKonfiguracji("%s: oczekiwano liczby, jest %r" % (gdzie, v))
    return v


def _prawda(v: Any, gdzie: str) -> bool:
    if not isinstance(v, bool):
        raise BledKonfiguracji("%s: oczekiwano true/false, jest %r" % (gdzie, v))
    return v


def _lista_napisow(v: Any, gdzie: str) -> tuple[str, ...]:
    if not isinstance(v, list) or not v or not all(isinstance(x, str) for x in v):
        raise BledKonfiguracji(
            "%s: oczekiwano niepustej listy napisow, jest %r" % (gdzie, v))
    return tuple(v)


def _lista_napisow_moze_pusta(v: Any, gdzie: str) -> tuple[str, ...]:
    """Lista napisow, w ktorej PUSTA jest poprawna odpowiedzia.

    Rozne od `_lista_napisow` dokladnie jednym warunkiem i to nie jest
    drobiazg. Tam pusta lista jest bledem, bo pole, ktore nic nie wnosi,
    zwykle znaczy literowke w nazwie klucza. Tu pusta lista to swiadome
    „jeszcze nic tu nie nalezy" — i jest to jedyny stan, w ktorym nowa
    instalacja moze byc uczciwie.
    """
    if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
        raise BledKonfiguracji(
            "%s: oczekiwano listy napisow (pusta jest dozwolona), jest %r"
            % (gdzie, v))
    return tuple(v)


def _widelki(v: Any, gdzie: str) -> tuple[int, int]:
    """Zakres [od, do]. Wolumeny sa losowane z widelek, nie stale."""
    if (not isinstance(v, list) or len(v) != 2
            or not all(isinstance(x, int) and not isinstance(x, bool) for x in v)):
        raise BledKonfiguracji(
            "%s: oczekiwano dwoch liczb calkowitych [od, do], jest %r" % (gdzie, v))
    if v[0] > v[1]:
        raise BledKonfiguracji("%s: dolna granica wieksza od gornej: %r" % (gdzie, v))
    return (v[0], v[1])


def _slownik_list(v: Any, gdzie: str) -> dict[str, tuple[str, ...]]:
    """Tablica `klucz = [napisy]`. Pusta lista jest DOZWOLONA i coś znaczy.

    Przy `_lista_napisow` pusta lista jest błędem, bo pole, które nic nie
    wnosi, zwykle znaczy literówkę. Tu jest odwrotnie: pusta lista przykładów
    to świadome „nie mam czym tego wypełnić", a `stages._blok_przykladow`
    wstawia wtedy polecenie, żeby model wyprowadził odpowiednik sam.
    """
    if not isinstance(v, dict):
        raise BledKonfiguracji("%s: oczekiwano tablicy klucz = [napisy], jest %r"
                               % (gdzie, v))
    wynik = {}
    for klucz, lista in v.items():
        if not isinstance(lista, list) or not all(isinstance(x, str) for x in lista):
            raise BledKonfiguracji("%s.%s: oczekiwano listy napisow, jest %r"
                                   % (gdzie, klucz, lista))
        wynik[klucz] = tuple(lista)
    return wynik


def _slownik_napisow(v: Any, gdzie: str) -> dict[str, str]:
    if not isinstance(v, dict) or not all(
            isinstance(k, str) and isinstance(x, str) for k, x in v.items()):
        raise BledKonfiguracji(
            "%s: oczekiwano tablicy napis = napis, jest %r" % (gdzie, v))
    return dict(v)


POLA: dict[str, tuple[str | None, Any]] = {
    # --- konto ---------------------------------------------------------
    "konto.uchwyt": ("SUBSTACK_HANDLE", _napis),
    "konto.nazwa_marki": ("NAZWA_MARKI", _napis),
    "konto.strefa_czytelnika": ("PUBLISH_TIMEZONE", _napis),
    # RRRR-MM-DD albo pusty napis — patrz `config.DATA_PRZESTAWIENIA`.
    "konto.data_przestawienia": ("DATA_PRZESTAWIENIA", _data_albo_pusto),

    # --- temat ---------------------------------------------------------
    "temat.nisza": ("NISZA", _napis),
    "temat.jezyk": ("ARTICLE_LANGUAGE", _napis),
    "temat.kat_redakcyjny": ("KAT_REDAKCYJNY", _napis),
    "temat.znaki_niszy": ("ZNAKI_NISZY", _lista_napisow),
    "temat.hasla_szukania": ("HASLA_SZUKANIA", _lista_napisow),
    "temat.dziedziny": ("DZIEDZINY_CIEKAWOSTEK", _lista_napisow),
    # Slowa, ktore w tej niszy padaja wszedzie — patrz `config.PUSTE_SLOWA_NISZY`.
    "temat.puste_slowa": ("PUSTE_SLOWA_NISZY", _lista_napisow_moze_pusta),
    # Przyklady z niszy wstrzykiwane w prompty. Tablica tablic, bo kazda
    # z pieciu list trafia w INNE miejsce briefu — patrz `stages._pola_wspolne`.
    "temat.przyklady": (None, _slownik_list),

    # --- zrodla --------------------------------------------------------
    # WSKAZUJE NA STALA, NIE NA `None`. Stalo tu `(None, ...)`, czyli
    # „obsluzone osobno w `zastosuj`" — a `zastosuj` tego pola NIE
    # OBSLUGIWALO. Konfigurator pytal o kanaly, operator odpowiadal, wartosc
    # szla do pliku, przechodzila sprawdzenie i byla cicho wyrzucana.
    "zrodla.kanaly_youtube": ("KANALY_YOUTUBE", _slownik_napisow),
    "zrodla.blokowane_hosty": ("BLOCKED_HOSTS", _lista_napisow),

    # --- modele --------------------------------------------------------
    "modele.role": (None, _slownik_napisow),

    # --- wolumeny ------------------------------------------------------
    "wolumeny.komentarze_dziennie": ("KOMENTARZE_DZIENNIE", _widelki),
    "wolumeny.lajki_dziennie": ("LAJKI_DZIENNIE", _widelki),
    "wolumeny.restacki_dziennie": ("RESTACK_DZIENNIE", _widelki),
    "wolumeny.follow_miesiecznie": ("FOLLOW_MIESIECZNIE", _widelki),
    "wolumeny.subskrypcje_miesiecznie": ("SUBSKRYPCJE_MIESIECZNIE", _widelki),
    "wolumeny.przebiegow_dziennie": ("PRZEBIEGOW_DZIENNIE", _liczba),

    # --- pieniadze -----------------------------------------------------
    "pieniadze.sufit_miesieczny_usd": ("MONTHLY_LIMIT_USD", _liczba),
    # CELUJE W SUFIT BAZOWY, NIE W `DAILY_LIMIT_USD`. Ten drugi jest POCHODNA
    # na dzis (baza albo baza razy mnoznik w dniu podniesienia) i przeliczany
    # po wczytaniu konfiguracji — ustawianie go wprost kasowaloby podniesienie
    # albo naliczalo je drugi raz.
    "pieniadze.sufit_dzienny_usd": ("SUFIT_DZIENNY_BAZOWY", _liczba),
    # Dzien, na ktory sufit jest podniesiony `SUFIT_PODNIESIONY_RAZY` razy.
    # Pusty (domyslnie) znaczy „bez podniesienia"; wygasa sam nastepnego dnia.
    "pieniadze.sufit_podniesiony_na": ("SUFIT_PODNIESIONY_NA",
                                      _data_albo_pusto),
    "pieniadze.sufit_przebiegu_usd": ("RUN_LIMIT_USD", _liczba),

    # --- publikowanie --------------------------------------------------
    "publikowanie.okno_et": ("OKNO_PUBLIKACJI_ET", _widelki),
    "publikowanie.martwe_godziny_et": ("WORST_NOTE_HOURS", _widelki),
    "publikowanie.notek_promujacych": ("NOTEK_PROMUJACYCH", _liczba),
    "publikowanie.okno_promocji_dni": ("OKNO_PROMOCJI_DNI", _liczba),
    # LICZBA NOTEK NA DOBE WYNIKA Z DLUGOSCI TEJ LISTY i tylko z niej.
    # `config.py` ostrzega wprost, ze osobna stala „ile notek dziennie" kusila
    # do rozjazdu z miksem — wiec konfiguracja podaje MIKS, a liczba jest jego
    # dlugoscia. Kazda pozycja musi byc kluczem z `config.NOTE_TYPES`.
    "publikowanie.miks_notek": (None, _lista_napisow),
    "publikowanie.ciche_dni_wlaczone": ("CICHE_DNI_WLACZONE", _prawda),
    "publikowanie.cichy_dzien_na_ile": ("CICHY_DZIEN_NA_ILE", _liczba),
}


def sciezka(agent_dir: Path) -> Path:
    return agent_dir / NAZWA_PLIKU


def wczytaj(plik: Path) -> dict[str, Any]:
    """Surowa zawartosc pliku, sprawdzona co do ksztaltu. Brak pliku = pusto."""
    if not plik.exists():
        return {}
    if sys.version_info < (3, 11):
        raise BledKonfiguracji(
            "%s istnieje, ale czytanie TOML-a wymaga Pythona 3.11 lub nowszego "
            "(masz %d.%d). Usun plik albo podnies wersje Pythona."
            % (plik.name, sys.version_info[0], sys.version_info[1]))
    import tomllib

    try:
        dane = tomllib.loads(plik.read_text(encoding="utf-8"))
    except Exception as exc:                       # noqa: BLE001
        raise BledKonfiguracji(
            "%s jest nieczytelny (%s: %s). Nie zgaduje, co autor mial na mysli "
            "— popraw plik albo go usun." % (plik.name, type(exc).__name__, exc))

    plaskie: dict[str, Any] = {}
    for sekcja, zawartosc in dane.items():
        if not isinstance(zawartosc, dict):
            raise BledKonfiguracji(
                "%s: `%s` musi byc sekcja [%s], jest %r"
                % (plik.name, sekcja, sekcja, zawartosc))
        for pole, wartosc in zawartosc.items():
            plaskie["%s.%s" % (sekcja, pole)] = wartosc

    obce = sorted(set(plaskie) - set(POLA))
    if obce:
        raise BledKonfiguracji(
            "%s: nieznane pola: %s\nZnane pola: %s\n(literowka w nazwie pola to "
            "najczestszy sposob, w jaki konfiguracja nie dziala bez sladu — "
            "dlatego jest to blad, a nie ciche pominiecie)"
            % (plik.name, ", ".join(obce), ", ".join(sorted(POLA))))

    return {k: POLA[k][1](v, "%s: %s" % (plik.name, k)) for k, v in plaskie.items()}


def zastosuj(dane: dict[str, Any], cfg: Any) -> list[str]:
    """Wklada wartosci do modulu `config`. Oddaje liste tego, co przestawiono."""
    if not dane:
        return []
    zmienione = []
    for klucz, wartosc in sorted(dane.items()):
        nazwa = POLA[klucz][0]
        if nazwa is None:
            continue                                # obsluzone nizej
        setattr(cfg, nazwa, wartosc)
        zmienione.append("%s -> %s" % (klucz, nazwa))

    # Miks notek: sprawdzany wobec znanych typow, bo literowka daje po cichu
    # mniej notek dziennie, a nie blad.
    miks = dane.get("publikowanie.miks_notek")
    if miks:
        obce = sorted(set(miks) - set(cfg.NOTE_TYPES))
        if obce:
            raise BledKonfiguracji(
                "publikowanie.miks_notek: nieznane typy notek: %s\n"
                "Znane typy: %s"
                % (", ".join(obce), ", ".join(sorted(cfg.NOTE_TYPES))))
        cfg.NOTE_MIX_OTHER_DAY = tuple(miks)
        zmienione.append("publikowanie.miks_notek -> NOTE_MIX_OTHER_DAY "
                         "(%d notek na dobe)" % len(miks))

    # Przyklady z niszy: nakladane NA ISTNIEJACE, zeby podanie jednej listy
    # nie kasowalo czterech pozostalych. Nieznany klucz jest bledem — literowka
    # w nazwie listy oznaczalaby prompt bez przykladow i nikt by tego nie
    # zauwazyl, bo model dostalby wtedy po cichu polecenie zastepcze.
    przyklady = dane.get("temat.przyklady")
    if przyklady:
        obce = sorted(set(przyklady) - set(cfg.PRZYKLADY_NISZY))
        if obce:
            raise BledKonfiguracji(
                "temat.przyklady: nieznane listy: %s\nZnane: %s"
                % (", ".join(obce), ", ".join(sorted(cfg.PRZYKLADY_NISZY))))
        cfg.PRZYKLADY_NISZY.update(przyklady)
        zmienione.append("temat.przyklady -> PRZYKLADY_NISZY (%d list, %d pozycji)"
                         % (len(przyklady), sum(len(v) for v in przyklady.values())))

    # Modele: slownik rola -> model, nakladany NA ISTNIEJACY `MODEL_FOR`,
    # zeby podanie jednej roli nie kasowalo dwudziestu pieciu pozostalych.
    role = dane.get("modele.role")
    if role:
        obce = sorted(set(role) - set(cfg.MODEL_FOR))
        if obce:
            raise BledKonfiguracji(
                "modele.role: nieznane etapy: %s\nZnane etapy: %s"
                % (", ".join(obce), ", ".join(sorted(cfg.MODEL_FOR))))
        cfg.MODEL_FOR.update(role)
        zmienione.append("modele.role -> MODEL_FOR (%d rol)" % len(role))

    return zmienione
