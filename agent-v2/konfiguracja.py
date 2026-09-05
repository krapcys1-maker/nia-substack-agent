# -*- coding: utf-8 -*-
"""Wczytanie `konfiguracja.toml` i pol presetu — jeden kontrakt pol, jeden zapis.

## Po co to jest

Do 2026-09-03 przestawienie bota na inne konto i inny temat znaczylo edycje
w kilkudziesieciu miejscach: uchwyt w DWOCH niezaleznych stalych, nisza
w czterech listach, wolumeny w kilkunastu, modele w slowniku na 26 pozycji.
Mapa `docs/MAPA_KONFIGURACJI.md` wyliczyla to co do linii. Ten plik zamyka
czesc pierwsza tamtej listy: wartosci, ktore da sie podac, zamiast ich szukac.

Od 2026-09-05 ten sam kontrakt pol czyta `preset.py`: preset to plik
z naglowkiem `[preset]` i KOMPLETEM pol opisujacych redakcje — temat, styl,
zrodla, modele, wolumeny, harmonogram, pieniadze. `konfiguracja.toml` zostaje
jako sciezka zgodnosci (te same pola, bez naglowka) i da sie go jednym
poleceniem zamienic w preset (`python narzedzia/presety.py importuj-konfiguracje`).

## Czego ten modul NIE robi

**Nie zastepuje `config.py`.** `config.py` zostaje jedynym zrodlem prawdy:
przelicza sufity tokenow, wywodzi sciezki, sprawdza spojnosc. Ten modul tylko
PODAJE mu wartosci. Konfiguracja nie podejmuje decyzji, tylko je zapisuje.

**Nie wystawia wszystkiego.** Trzy rzeczy sa celowo poza plikiem, bo wygladaja
na pola, a sa decyzjami:

  * sufit miesieczny jako „nieograniczony" — to jedyna twarda blokada
    w systemie; furtka `AGENT_V2_NO_LIMIT` juz istnieje i jest zmienna
    srodowiskowa, a nie domyslna wartoscia w pliku;
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

## Trzy zasady dopisane 2026-09-05 (audyt czystosci i presetow)

1. **Walidacja CALOSCI przed pierwszym zapisem.** `zastosuj` liczylo pola
   po kolei i przy nieznanej roli modelu zostawialo juz zmieniona nisze
   (proba T03 audytu). Teraz najpierw powstaje plan zmian, a dopiero gdy
   kazde pole przeszlo, plan idzie do `config`. Zla konfiguracja nie zmienia
   nic.
2. **Liczba notek ma JEDNO znaczenie.** `publikowanie.miks_notek` zmienialo
   tylko zwykly dzien, a dzien artykulu zostawal przy pieciu (proba T04).
   Teraz `wolumeny.notki_dziennie` (albo dlugosc miksu, gdy liczby nie
   podano) wyznacza sloty OBU dni, a notka promujaca artykul zajmuje slot
   w tej kwocie, zamiast ja powiekszac. Zero wylacza notki.
3. **Walidatory znaja dziedzine wartosci, nie tylko typ.** Ujemne komentarze,
   1,5 przebiegu na dobe, godzina 98 i dzien `2026-99-99` przechodzily
   (proba T05). Teraz licznosci sa nieujemnymi liczbami calkowitymi, kwoty
   skonczone i nieujemne, strefa musi istniec w bazie IANA, a data byc dniem
   w kalendarzu.

Wymaga Pythona 3.11 (`tomllib` w bibliotece standardowej). To JEDYNE miejsce
w calym agencie, ktore tego wymaga.
"""
from __future__ import annotations

import copy
import math
import re
import sys
from pathlib import Path
from typing import Any

NAZWA_PLIKU = "konfiguracja.toml"

# Dni tygodnia w postaci, ktora rozumie `OnCalendar=` systemd. Pelne nazwy
# angielskie i skroty sa przyjmowane na wejsciu; wewnatrz jest zawsze skrot.
DNI_TYGODNIA = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_PELNE_DNI = {"monday": "Mon", "tuesday": "Tue", "wednesday": "Wed",
              "thursday": "Thu", "friday": "Fri", "saturday": "Sat",
              "sunday": "Sun"}

# Ktore dni dostaje artykul, gdy preset podaje TYLKO liczbe na tydzien.
# Rozlozone tak, zeby dwa artykuly nie wypadly dzien po dniu; wtorek jest
# pierwszy, bo to dzien z dotychczasowego zegara i jedyny, ktory ma pomiar.
DNI_ARTYKULU_DOMYSLNE = {
    0: (),
    1: ("Tue",),
    2: ("Tue", "Fri"),
    3: ("Mon", "Wed", "Fri"),
    4: ("Mon", "Tue", "Thu", "Fri"),
    5: ("Mon", "Tue", "Wed", "Thu", "Fri"),
    6: ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat"),
    7: DNI_TYGODNIA,
}


class BledKonfiguracji(RuntimeError):
    """Konfiguracja jest zla i przebieg ma sie NIE zaczac."""


# ---------------------------------------------------------------------------
# WALIDATORY. Kazdy oddaje wartosc znormalizowana i przyjmuje wlasny wynik
# (`waliduj(waliduj(x)) == waliduj(x)`), bo te same wartosci ida dwiema drogami:
# z pliku i z wsadu/presetu podawanego jako gotowy obiekt.
# ---------------------------------------------------------------------------
def _napis(v: Any, gdzie: str) -> str:
    if not isinstance(v, str) or not v.strip():
        raise BledKonfiguracji("%s: oczekiwano niepustego napisu, jest %r" % (gdzie, v))
    return v


def _napis_moze_pusty(v: Any, gdzie: str) -> str:
    """Napis, ktory WOLNO zostawic pusty.

    `_napis` odrzuca pustke, bo dla uchwytu czy nazwy marki pusta wartosc jest
    bledem. Tu pustka COS ZNACZY — „zbuduj domyslne z niszy", „bez okladki",
    „bez pisarza zapasowego" — wiec musi przejsc.
    """
    if not isinstance(v, str):
        raise BledKonfiguracji("%s: oczekiwano napisu, jest %r" % (gdzie, v))
    return v.strip()


def _data_albo_pusto(v: Any, gdzie: str) -> str:
    """Dzien w postaci RRRR-MM-DD albo pusty napis znaczacy „nigdy".

    Sprawdzamy KSZTALT i ISTNIENIE dnia. Data jest porownywana z napisami
    w indeksie leksykograficznie, wiec „2026-8-25" z jedna cyfra miesiaca
    porownuje sie zle i nie daje po sobie zadnego znaku — odrzucamy ja tutaj,
    a nie pol roku pozniej. `2026-99-99` przechodzilo sam wzorzec (proba T05
    audytu) i tez jest odrzucane.
    """
    import datetime as _dt

    if not isinstance(v, str):
        raise BledKonfiguracji("%s: oczekiwano napisu, jest %r" % (gdzie, v))
    if not v:
        return v
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        raise BledKonfiguracji(
            "%s: oczekiwano daty RRRR-MM-DD albo pustego napisu, jest %r"
            % (gdzie, v))
    try:
        _dt.date.fromisoformat(v)
    except ValueError:
        raise BledKonfiguracji("%s: %r nie jest dniem w kalendarzu" % (gdzie, v))
    return v


def _liczba(v: Any, gdzie: str) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise BledKonfiguracji("%s: oczekiwano liczby, jest %r" % (gdzie, v))
    return v


def _kwota(v: Any, gdzie: str) -> float:
    """Kwota w USD: skonczona i nieujemna. Ujemny sufit przechodzil (T05)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise BledKonfiguracji("%s: oczekiwano nieujemnej liczby (kwota w USD), jest %r"
                               % (gdzie, v))
    if not math.isfinite(v) or v < 0:
        raise BledKonfiguracji("%s: kwota musi byc skonczona i nieujemna, jest %r"
                               % (gdzie, v))
    return float(v)


def _calkowita_nieujemna(v: Any, gdzie: str) -> int:
    """Licznosc: ile czego. Zero jest poprawne i znaczy „wylaczone"."""
    if isinstance(v, bool) or not isinstance(v, int):
        raise BledKonfiguracji(
            "%s: oczekiwano nieujemnej liczby calkowitej, jest %r" % (gdzie, v))
    if v < 0:
        raise BledKonfiguracji("%s: liczba nie moze byc ujemna, jest %r" % (gdzie, v))
    return v


def _calkowita_dodatnia(v: Any, gdzie: str) -> int:
    """Licznosc, ktora nie ma sensu jako zero (przebiegi na dobe)."""
    w = _calkowita_nieujemna(v, gdzie)
    if w < 1:
        raise BledKonfiguracji("%s: oczekiwano liczby calkowitej >= 1, jest %r" % (gdzie, v))
    return w


def _prawda(v: Any, gdzie: str) -> bool:
    if not isinstance(v, bool):
        raise BledKonfiguracji("%s: oczekiwano true/false, jest %r" % (gdzie, v))
    return v


def _strefa(v: Any, gdzie: str) -> str:
    """Nazwa strefy IANA, ktora NAPRAWDE istnieje w bazie stref.

    Literowka w strefie wychodzila dopiero w `pora_na_publikacje`, czyli
    w pierwszym przebiegu dnia, jako slad stosu z `zoneinfo`.
    """
    nazwa = _napis(v, gdzie)
    try:
        from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
    except ImportError:                    # pragma: no cover — 3.9+ ma zoneinfo
        return nazwa
    try:
        ZoneInfo(nazwa)
    except ZoneInfoNotFoundError:
        raise BledKonfiguracji(
            "%s: %r nie jest znana strefa czasowa IANA (np. Europe/Warsaw, "
            "America/New_York)" % (gdzie, nazwa))
    except Exception:                      # noqa: BLE001 — brak bazy stref na maszynie
        return nazwa
    return nazwa


def _sekwencja_napisow(v: Any) -> bool:
    """Lista albo krotka napisow — ale NIE sam napis.

    WALIDATOR MA PRZYJMOWAC WLASNY WYNIK. Te funkcje zwracaja krotki, wiec
    dopoki wymagaly `list`, `waliduj(waliduj(x))` sie wywalalo. Dopoki wartosci
    szly jedna droga (TOML -> walidator -> stala), nikt tego nie widzial;
    wyszlo, gdy pojawilo sie drugie zrodlo tych samych pol — wsad tematyczny
    podawany kreatorowi jako domyslne odpowiedzi.

    `str` jest wykluczony celowo: napis tez jest sekwencja i przeszedlby jako
    lista pojedynczych liter. To jest cichy blad, ktory potem wyglada na wade
    modelu.
    """
    return (isinstance(v, (list, tuple)) and not isinstance(v, str)
            and all(isinstance(x, str) for x in v))


def _lista_napisow(v: Any, gdzie: str) -> tuple[str, ...]:
    if not _sekwencja_napisow(v) or not v:
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
    if not _sekwencja_napisow(v):
        raise BledKonfiguracji(
            "%s: oczekiwano listy napisow (pusta jest dozwolona), jest %r"
            % (gdzie, v))
    return tuple(v)


def _widelki(v: Any, gdzie: str) -> tuple[int, int]:
    """Zakres [od, do] nieujemnych liczb calkowitych. `[0, 0]` wylacza dzialanie.

    Wolumeny sa losowane z widelek, nie stale. Ujemna dolna granica
    przechodzila (T05) i dawala `randint` z ujemnym dolem — czyli budzet
    ujemny, ktory `max(0, ...)` po cichu zamienial na zero.
    """
    if (not isinstance(v, (list, tuple)) or len(v) != 2
            or not all(isinstance(x, int) and not isinstance(x, bool) for x in v)):
        raise BledKonfiguracji(
            "%s: oczekiwano dwoch liczb calkowitych [od, do], jest %r" % (gdzie, v))
    if v[0] < 0:
        raise BledKonfiguracji("%s: dolna granica nie moze byc ujemna: %r" % (gdzie, v))
    if v[0] > v[1]:
        raise BledKonfiguracji("%s: dolna granica wieksza od gornej: %r" % (gdzie, v))
    return (v[0], v[1])


def _godziny(v: Any, gdzie: str) -> tuple[int, int]:
    """Para godzin doby [od, do] w zakresie 0-24. Godzina 98 przechodzila (T05)."""
    dol, gora = _widelki(v, gdzie)
    if gora > 24:
        raise BledKonfiguracji("%s: godzina doby miesci sie w 0-24, jest %r" % (gdzie, v))
    return (dol, gora)


def _godzina_utc(v: Any, gdzie: str) -> str:
    """Godzina zegara `HH:MM` w UTC — postac, ktora rozumie `OnCalendar=`."""
    napis = _napis(v, gdzie).strip()
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", napis)
    if not m or not (0 <= int(m.group(1)) <= 23 and 0 <= int(m.group(2)) <= 59):
        raise BledKonfiguracji("%s: oczekiwano godziny HH:MM (UTC), jest %r" % (gdzie, v))
    return "%02d:%s" % (int(m.group(1)), m.group(2))


def _lista_godzin_utc(v: Any, gdzie: str) -> tuple[str, ...]:
    """Niepusta lista godzin `HH:MM` bez powtorzen, w kolejnosci doby."""
    if not _sekwencja_napisow(v) or not v:
        raise BledKonfiguracji(
            "%s: oczekiwano niepustej listy godzin HH:MM, jest %r" % (gdzie, v))
    godziny = tuple(_godzina_utc(x, gdzie) for x in v)
    if len(set(godziny)) != len(godziny):
        raise BledKonfiguracji("%s: godziny sie powtarzaja: %r" % (gdzie, v))
    return tuple(sorted(godziny))


def _dzien_tygodnia(v: Any, gdzie: str) -> str:
    napis = _napis(v, gdzie).strip()
    klucz = napis.lower()
    if klucz in _PELNE_DNI:
        return _PELNE_DNI[klucz]
    for d in DNI_TYGODNIA:
        if d.lower() == klucz:
            return d
    raise BledKonfiguracji(
        "%s: %r nie jest dniem tygodnia (dozwolone: %s)"
        % (gdzie, v, ", ".join(DNI_TYGODNIA)))


def _lista_dni_tygodnia(v: Any, gdzie: str) -> tuple[str, ...]:
    """Lista dni tygodnia; pusta znaczy „bez artykulow"."""
    if not _sekwencja_napisow(v):
        raise BledKonfiguracji(
            "%s: oczekiwano listy dni tygodnia (pusta jest dozwolona), jest %r"
            % (gdzie, v))
    dni = tuple(_dzien_tygodnia(x, gdzie) for x in v)
    if len(set(dni)) != len(dni):
        raise BledKonfiguracji("%s: dni sie powtarzaja: %r" % (gdzie, v))
    return tuple(d for d in DNI_TYGODNIA if d in dni)


def _sciezka(v: Any, gdzie: str) -> str:
    """Sciezka do pliku wzgledem korzenia repozytorium (albo bezwzgledna).

    Sam napis, nie `Path`: TOML nie ma typu sciezki, a rozwiazanie wzgledem
    korzenia robi `zastosuj`, bo tylko tam znany jest `config.REPO_ROOT`.
    """
    napis = _napis(v, gdzie).strip().replace("\\", "/")
    return napis


def _sciezka_moze_pusta(v: Any, gdzie: str) -> str:
    napis = _napis_moze_pusty(v, gdzie)
    return napis.replace("\\", "/") if napis else ""


def _slownik_list(v: Any, gdzie: str) -> dict[str, tuple[str, ...]]:
    """Tablica `klucz = [napisy]`. Pusta lista jest DOZWOLONA i coś znaczy.

    Przy `_lista_napisow` pusta lista jest błędem, bo pole, które nic nie
    wnosi, zwykle znaczy literówkę. Tu jest odwrotnie: pusta lista przykładów
    to świadome „nie mam czym tego wypełnić", a `stages._blok_przykladow`
    wstawia wtedy polecenie, żeby model wyprowadził odpowiednik sam.

    PRZYJMUJE WLASNY WYNIK: oddaje krotki i przyjmuje krotki. Poprzednia
    wersja przyjmowala tylko listy, wiec ponowna walidacja tej samej wartosci
    (kreator, preset) oblewala na wlasnym wyniku (proba T06 audytu).
    """
    if not isinstance(v, dict):
        raise BledKonfiguracji("%s: oczekiwano tablicy klucz = [napisy], jest %r"
                               % (gdzie, v))
    wynik = {}
    for klucz, lista in v.items():
        if not _sekwencja_napisow(lista):
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


# Ksztalt pliku. Klucz to sciezka `sekcja.pole`, wartosc to (nazwa stalej
# w config.py, sprawdzacz). Zamknieta lista, bo nieznany klucz ma byc bledem.
#
# `None` jako nazwa stalej znaczy: pole jest obslugiwane osobno w `zastosuj`,
# bo trafia gdzie indziej niz do stalej o tej samej nazwie albo wchodzi w
# zaleznosc z innym polem (liczba notek i miks, godziny i liczba przebiegow,
# dni artykulu i liczba na tydzien). `tests/test_kazde_pole_dochodzi.py`
# pilnuje, ze kazde takie pole jest w `zastosuj` NAPRAWDE obsluzone.
POLA: dict[str, tuple[str | None, Any]] = {
    # --- konto ---------------------------------------------------------
    "konto.uchwyt": ("SUBSTACK_HANDLE", _napis),
    "konto.nazwa_marki": ("NAZWA_MARKI", _napis),
    "konto.strefa_czytelnika": ("PUBLISH_TIMEZONE", _strefa),
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

    # --- stan dziedziny ------------------------------------------------
    # Czy raz na dobe pytac swiata, co w tej dziedzinie jest AKTUALNE. Kosztuje
    # jedno wywolanie z wyszukiwaniem; dziedzina, ktora nie zmienia sie
    # z tygodnia na tydzien, moze to wylaczyc.
    "stan_dziedziny.pytaj": ("STAN_DZIEDZINY_PYTAJ", _prawda),
    # O CO pytac. Puste znaczy „zbuduj z niszy" — patrz
    # `config.pytanie_o_stan_dziedziny`.
    "stan_dziedziny.o_co_pytac": ("STAN_DZIEDZINY_PYTANIE", _napis_moze_pusty),

    # --- zrodla --------------------------------------------------------
    "zrodla.kanaly_youtube": ("KANALY_YOUTUBE", _slownik_napisow),
    "zrodla.blokowane_hosty": ("BLOCKED_HOSTS", _lista_napisow),

    # --- styl (2026-09-05) ---------------------------------------------
    # Glos redakcji byl wspolnym zestawem plikow o stalych nazwach: pierwszy
    # `.txt` w jednym katalogu i dwa profile z `style-profiles/`. Preset nie
    # mial jak wskazac innego korpusu ani innych profili (C4 audytu).
    #
    # `opis` to glos opisany slowami — wstrzykiwany do briefow pisarza, notki,
    # komentarza i odpowiedzi jako `{styl_opis}`. Pusty znaczy „bez uwag
    # dodatkowych", a NIE „bez stylu": profile i korpus dzialaja jak dotad.
    "styl.opis": ("STYL_OPIS", _napis_moze_pusty),
    # Sciezki wzgledem korzenia repozytorium. Rozwiazywane w `zastosuj`.
    "styl.profil_pozytywny": (None, _sciezka),
    "styl.profil_negatywny": (None, _sciezka),
    # Plik korpusu (`.txt`, akapity oddzielone pusta linia). Pusty = domyslny
    # katalog `agent-v2/prompts/styl/`.
    "styl.korpus": (None, _sciezka_moze_pusta),
    # Czy pisarz artykulow ma ODMOWIC bez przypietego korpusu (tak bylo
    # zawsze), czy pisac z samych profili i opisu. Preset, ktory dopiero
    # zaczyna, moze uczciwie wybrac drugie — patrz `style.przyklady_albo_pusto`.
    "styl.wymagaj_korpusu": ("STYL_WYMAGAJ_KORPUSU", _prawda),

    # --- modele --------------------------------------------------------
    "modele.role": (None, _slownik_napisow),
    # Model okladki. Pusty napis WYLACZA okladke; podany ustawia NARAZ
    # `IMAGE_MODEL` i `MODEL_FOR["obraz"]`, bo do 2026-09-05 zmiana roli
    # zostawiala stary model w ladunku zadania (proba T15 audytu).
    "modele.obraz": (None, _napis_moze_pusty),
    # Na jaki model wraca pisarz artykulu po awarii skonfigurowanego. Pusty
    # znaczy „nie wracaj, zatrzymaj sie". Do 2026-09-05 bylo wpisane w kod.
    "modele.zapasowy_pisarz": ("ZAPASOWY_PISARZ", _napis_moze_pusty),

    # --- wolumeny ------------------------------------------------------
    # LICZBA NOTEK NA DOBE — jedna dla zwyklego dnia i dnia artykulu. Zero
    # wylacza notki. Gdy nie podana, wynika z dlugosci `publikowanie.miks_notek`.
    "wolumeny.notki_dziennie": (None, _calkowita_nieujemna),
    # ILE ARTYKULOW NA TYDZIEN. Zero wylacza sciezke artykulu (zegar, promocje,
    # `artykul_z_puli`). Dni wybiera `harmonogram.dni_artykulu`, a gdy ich nie
    # podano — `DNI_ARTYKULU_DOMYSLNE`.
    "wolumeny.artykuly_tygodniowo": (None, _calkowita_nieujemna),
    "wolumeny.komentarze_dziennie": ("KOMENTARZE_DZIENNIE", _widelki),
    "wolumeny.lajki_dziennie": ("LAJKI_DZIENNIE", _widelki),
    "wolumeny.restacki_dziennie": ("RESTACK_DZIENNIE", _widelki),
    "wolumeny.follow_miesiecznie": ("FOLLOW_MIESIECZNIE", _widelki),
    "wolumeny.subskrypcje_miesiecznie": ("SUBSKRYPCJE_MIESIECZNIE", _widelki),
    # Musi zgadzac sie z liczba godzin zegara; gdy podano tylko liczbe,
    # godziny sa dobierane z domyslnego zegara — patrz `_rozloz_godziny`.
    "wolumeny.przebiegow_dziennie": (None, _calkowita_dodatnia),

    # --- harmonogram (2026-09-05) --------------------------------------
    # Zegar byl poza konfiguracja: piec godzin w szablonie `nia-agent.timer`
    # i wtorek w `nia-artykul.timer`, a `narzedzia/jednostki.py` podstawialo
    # tylko katalog, uzytkownika i marke (W2 audytu). Teraz jednostki
    # powstaja z TYCH pol — `config.zegar_agenta_on_calendar()`.
    "harmonogram.godziny_przebiegow_utc": (None, _lista_godzin_utc),
    "harmonogram.dni_artykulu": (None, _lista_dni_tygodnia),
    "harmonogram.godzina_artykulu_utc": ("GODZINA_ARTYKULU_UTC", _godzina_utc),

    # --- pieniadze -----------------------------------------------------
    "pieniadze.sufit_miesieczny_usd": ("MONTHLY_LIMIT_USD", _kwota),
    # CELUJE W SUFIT BAZOWY, NIE W `DAILY_LIMIT_USD`. Ten drugi jest POCHODNA
    # na dzis (baza albo baza razy mnoznik w dniu podniesienia) i przeliczany
    # po wczytaniu konfiguracji — ustawianie go wprost kasowaloby podniesienie
    # albo naliczalo je drugi raz.
    "pieniadze.sufit_dzienny_usd": ("SUFIT_DZIENNY_BAZOWY", _kwota),
    # Dzien, na ktory sufit jest podniesiony `SUFIT_PODNIESIONY_RAZY` razy.
    # Pusty (domyslnie) znaczy „bez podniesienia"; wygasa sam nastepnego dnia.
    "pieniadze.sufit_podniesiony_na": ("SUFIT_PODNIESIONY_NA",
                                      _data_albo_pusto),
    "pieniadze.sufit_przebiegu_usd": ("RUN_LIMIT_USD", _kwota),

    # --- publikowanie --------------------------------------------------
    "publikowanie.okno_et": ("OKNO_PUBLIKACJI_ET", _godziny),
    "publikowanie.martwe_godziny_et": ("WORST_NOTE_HOURS", _godziny),
    "publikowanie.notek_promujacych": ("NOTEK_PROMUJACYCH", _calkowita_nieujemna),
    "publikowanie.okno_promocji_dni": ("OKNO_PROMOCJI_DNI", _calkowita_nieujemna),
    # PROPORCJE TYPOW NOTEK. Sloty dnia wypelniaja sie ta lista cyklicznie;
    # liczbe slotow daje `wolumeny.notki_dziennie`, a gdy jej nie podano —
    # dlugosc tej listy (tak jak do 2026-09-05). Kazda pozycja musi byc
    # kluczem z `config.NOTE_TYPES`.
    "publikowanie.miks_notek": (None, _lista_napisow),
    "publikowanie.ciche_dni_wlaczone": ("CICHE_DNI_WLACZONE", _prawda),
    "publikowanie.cichy_dzien_na_ile": ("CICHY_DZIEN_NA_ILE", _calkowita_nieujemna),
}

# Sekcje w kolejnosci, w jakiej czlowiek je czyta — do zapisu presetu.
KOLEJNOSC_SEKCJI = ("konto", "temat", "stan_dziedziny", "zrodla", "styl",
                    "modele", "wolumeny", "harmonogram", "publikowanie",
                    "pieniadze")

# STALE OPISUJACE KONTO — komplet tego, co preset moze przestawic. Zdjecie
# tych stalych zrobione PRZED wczytaniem czegokolwiek to „neutralna baza",
# od ktorej kompiluje sie kazdy preset. Bez tego preset B dziedziczyl kanaly,
# przyklady i pisarza presetu A (proba T02 audytu).
#
# Wyprowadzone z `POLA`, nie przepisane: pole dopisane jutro wchodzi tu samo.
# Reszta to stale, ktore `zastosuj` ustawia POSREDNIO.
STALE_KONTA: tuple[str, ...] = tuple(sorted(
    {n for n, _ in POLA.values() if n} | {
        "NOTE_MIX_OTHER_DAY", "NOTE_MIX_ARTICLE_DAY", "NOTKI_DZIENNIE",
        "PRZYKLADY_NISZY", "MODEL_FOR", "IMAGE_MODEL", "OBRAZ_WLACZONY",
        "STYLE_CORPUS", "STYLE_PROFILE_POSITIVE", "STYLE_PROFILE_NEGATIVE",
        "PRZEBIEGOW_DZIENNIE", "GODZINY_PRZEBIEGOW_UTC",
        "ARTYKULY_TYGODNIOWO", "DNI_ARTYKULU",
    }))


def sciezka(agent_dir: Path) -> Path:
    return agent_dir / NAZWA_PLIKU


def splaszcz(dane: dict[str, Any], nazwa: str) -> dict[str, Any]:
    """`{"temat": {"nisza": ...}}` na `{"temat.nisza": ...}` — jeden poziom."""
    plaskie: dict[str, Any] = {}
    for sekcja, zawartosc in dane.items():
        if not isinstance(zawartosc, dict):
            raise BledKonfiguracji(
                "%s: `%s` musi byc sekcja [%s], jest %r"
                % (nazwa, sekcja, sekcja, zawartosc))
        for pole, wartosc in zawartosc.items():
            plaskie["%s.%s" % (sekcja, pole)] = wartosc
    return plaskie


def sprawdz_plaskie(plaskie: dict[str, Any], nazwa: str) -> dict[str, Any]:
    """Nieznane pole to blad; kazde znane przechodzi przez swoj walidator.

    Wspolne dla `konfiguracja.toml`, wsadow tematycznych i presetow — jedna
    implementacja regul, nie trzy kopie.
    """
    obce = sorted(set(plaskie) - set(POLA))
    if obce:
        raise BledKonfiguracji(
            "%s: nieznane pola: %s\nZnane pola: %s\n(literowka w nazwie pola to "
            "najczestszy sposob, w jaki konfiguracja nie dziala bez sladu — "
            "dlatego jest to blad, a nie ciche pominiecie)"
            % (nazwa, ", ".join(obce), ", ".join(sorted(POLA))))
    return {k: POLA[k][1](v, "%s: %s" % (nazwa, k)) for k, v in plaskie.items()}


def wczytaj_tekst(tekst: str, nazwa: str) -> dict[str, Any]:
    """Surowy TOML (napis) -> zwalidowane pola plaskie. Wymaga Pythona 3.11."""
    if sys.version_info < (3, 11):
        raise BledKonfiguracji(
            "%s istnieje, ale czytanie TOML-a wymaga Pythona 3.11 lub nowszego "
            "(masz %d.%d). Usun plik albo podnies wersje Pythona."
            % (nazwa, sys.version_info[0], sys.version_info[1]))
    import tomllib

    try:
        dane = tomllib.loads(tekst)
    except Exception as exc:                       # noqa: BLE001
        raise BledKonfiguracji(
            "%s jest nieczytelny (%s: %s). Nie zgaduje, co autor mial na mysli "
            "— popraw plik albo go usun." % (nazwa, type(exc).__name__, exc))
    return sprawdz_plaskie(splaszcz(dane, nazwa), nazwa)


def wczytaj(plik: Path) -> dict[str, Any]:
    """Surowa zawartosc pliku, sprawdzona co do ksztaltu. Brak pliku = pusto."""
    if not plik.exists():
        return {}
    return wczytaj_tekst(plik.read_text(encoding="utf-8"), plik.name)


# ---------------------------------------------------------------------------
# ZDJECIE I PRZYWROCENIE — neutralna baza dla presetow.
# ---------------------------------------------------------------------------
def zdjecie(cfg: Any) -> dict[str, Any]:
    """Kopia stalych konta z modulu `config`, do pozniejszego przywrocenia.

    Slowniki i listy sa kopiowane glebo, bo `zastosuj` zmienia `MODEL_FOR`
    i `PRZYKLADY_NISZY` w miejscu.
    """
    return {n: copy.deepcopy(getattr(cfg, n)) for n in STALE_KONTA if hasattr(cfg, n)}


def przywroc(cfg: Any, zdj: dict[str, Any]) -> None:
    """Przywraca stan ze `zdjecie`. Slowniki W MIEJSCU, bo inne moduly trzymaja
    do nich odwolania (`config.MODEL_FOR` czyta `llm` przy kazdym wywolaniu)."""
    for nazwa, wartosc in zdj.items():
        biezaca = getattr(cfg, nazwa, None)
        if isinstance(biezaca, dict) and isinstance(wartosc, dict):
            biezaca.clear()
            biezaca.update(copy.deepcopy(wartosc))
        else:
            setattr(cfg, nazwa, copy.deepcopy(wartosc))


# ---------------------------------------------------------------------------
# ZASTOSOWANIE — plan najpierw, zapis potem.
# ---------------------------------------------------------------------------
def _rozloz_godziny(ile: int, baza: tuple[str, ...]) -> tuple[str, ...]:
    """Godziny zegara dla `ile` przebiegow, gdy preset podal tylko liczbe.

    Bierze podzbior zegara domyslnego rozlozony po jego szerokosci (dwa
    przebiegi z pieciu to pierwszy i ostatni, nie dwa pierwsze); powyzej
    dlugosci bazy rozklada rowno miedzy 06:00 a 23:00 UTC.
    """
    if ile <= 0:
        return ()
    if baza and ile <= len(baza):
        if ile == 1:
            return (baza[len(baza) // 2],)
        krok = (len(baza) - 1) / (ile - 1)
        return tuple(baza[round(i * krok)] for i in range(ile))
    poczatek, koniec = 6 * 60, 23 * 60
    krok = (koniec - poczatek) / max(1, ile - 1)
    return tuple("%02d:%02d" % divmod(int(poczatek + i * krok), 60) for i in range(ile))


def _sciezka_w_repo(cfg: Any, napis: str) -> Path:
    p = Path(napis)
    return p if p.is_absolute() else Path(getattr(cfg, "REPO_ROOT", ".")) / p


def _plan(dane: dict[str, Any], cfg: Any) -> tuple[dict[str, Any], dict[str, dict], list[str]]:
    """Co przestawic — policzone W CALOSCI, zanim cokolwiek zostanie zapisane.

    Oddaje (stale do ustawienia, slowniki do nalozenia, meldunki). Kazde
    podane pole ma dokladnie jeden meldunek `sekcja.pole -> ...`, bo
    `tests/test_kazde_pole_dochodzi.py` po tych meldunkach sprawdza, ze zadne
    pole nie ginie po drodze.
    """
    ustaw: dict[str, Any] = {}
    slowniki: dict[str, dict] = {}
    meldunki: list[str] = []

    for klucz, wartosc in sorted(dane.items()):
        nazwa = POLA[klucz][0]
        if nazwa is None:
            continue                                # obsluzone nizej
        ustaw[nazwa] = wartosc
        meldunki.append("%s -> %s" % (klucz, nazwa))

    # --- notki: jedna liczba dla obu rodzajow dnia ---------------------
    miks = dane.get("publikowanie.miks_notek")
    ile_notek = dane.get("wolumeny.notki_dziennie")
    if miks is not None:
        obce = sorted(set(miks) - set(cfg.NOTE_TYPES))
        if obce:
            raise BledKonfiguracji(
                "publikowanie.miks_notek: nieznane typy notek: %s\n"
                "Znane typy: %s"
                % (", ".join(obce), ", ".join(sorted(cfg.NOTE_TYPES))))
    artykulow_tyg = dane.get("wolumeny.artykuly_tygodniowo")
    dni_art = dane.get("harmonogram.dni_artykulu")
    if artykulow_tyg is not None and dni_art is not None and len(dni_art) != artykulow_tyg:
        raise BledKonfiguracji(
            "wolumeny.artykuly_tygodniowo = %d, a harmonogram.dni_artykulu ma %d dni "
            "(%s) — podaj jedno albo zgodne oba"
            % (artykulow_tyg, len(dni_art), ", ".join(dni_art) or "brak"))
    if artykulow_tyg is not None and artykulow_tyg > 7:
        raise BledKonfiguracji(
            "wolumeny.artykuly_tygodniowo = %d — tydzien ma siedem dni" % artykulow_tyg)
    if dni_art is not None:
        ustaw["DNI_ARTYKULU"] = tuple(dni_art)
        ustaw["ARTYKULY_TYGODNIOWO"] = len(dni_art)
        meldunki.append("harmonogram.dni_artykulu -> DNI_ARTYKULU (%d na tydzien)"
                        % len(dni_art))
        if artykulow_tyg is not None:
            meldunki.append("wolumeny.artykuly_tygodniowo -> ARTYKULY_TYGODNIOWO")
    elif artykulow_tyg is not None:
        ustaw["ARTYKULY_TYGODNIOWO"] = artykulow_tyg
        ustaw["DNI_ARTYKULU"] = DNI_ARTYKULU_DOMYSLNE[artykulow_tyg]
        meldunki.append("wolumeny.artykuly_tygodniowo -> ARTYKULY_TYGODNIOWO "
                        "(dni: %s)" % (", ".join(ustaw["DNI_ARTYKULU"]) or "zadne"))
    artykuly_w_ogole = ustaw.get("ARTYKULY_TYGODNIOWO",
                                 getattr(cfg, "ARTYKULY_TYGODNIOWO", 1)) > 0

    if miks is not None or ile_notek is not None:
        typy = tuple(miks) if miks is not None else tuple(
            getattr(cfg, "NOTE_MIX_OTHER_DAY", ()) or ())
        if not typy:
            typy = ("CIEKAWOSTKA",)
        ile = ile_notek if ile_notek is not None else len(typy)
        zwykly = tuple(typy[i % len(typy)] for i in range(ile))
        # SLOT PROMOCJI MIESCI SIE W KWOCIE. Przy pieciu notkach dzien artykulu
        # mial dwie promujace i trzy zwykle; ta proporcja zostaje (2 z 5),
        # a przy mniejszej kwocie promuje jedna notka. Bez artykulow nie ma
        # dnia artykulu i obie listy sa rowne.
        promuj = 0 if (ile == 0 or not artykuly_w_ogole) else max(1, ile * 2 // 5)
        reszta = tuple(t for t in zwykly if t != "ARTYKUL")[: ile - promuj]
        dzien_art = ("ARTYKUL",) * promuj + reszta
        ustaw["NOTE_MIX_OTHER_DAY"] = zwykly
        ustaw["NOTE_MIX_ARTICLE_DAY"] = dzien_art
        ustaw["NOTKI_DZIENNIE"] = ile
        if miks is not None:
            meldunki.append("publikowanie.miks_notek -> NOTE_MIX_OTHER_DAY "
                            "(%d notek na dobe)" % ile)
        if ile_notek is not None:
            meldunki.append("wolumeny.notki_dziennie -> NOTE_MIX_OTHER_DAY, "
                            "NOTE_MIX_ARTICLE_DAY (%d slotow, %d promujacych "
                            "w dniu artykulu)" % (ile, promuj))

    # --- przyklady z niszy: nakladane NA ISTNIEJACE ----------------------
    # Podanie jednej listy nie kasuje czterech pozostalych; pusta lista
    # CZYSCI swoja pozycje. Nieznany klucz jest bledem — literowka w nazwie
    # listy oznaczalaby prompt bez przykladow i nikt by tego nie zauwazyl,
    # bo model dostalby wtedy po cichu polecenie zastepcze.
    przyklady = dane.get("temat.przyklady")
    if przyklady is not None:
        obce = sorted(set(przyklady) - set(cfg.PRZYKLADY_NISZY))
        if obce:
            raise BledKonfiguracji(
                "temat.przyklady: nieznane listy: %s\nZnane: %s"
                % (", ".join(obce), ", ".join(sorted(cfg.PRZYKLADY_NISZY))))
        slowniki["PRZYKLADY_NISZY"] = {k: tuple(v) for k, v in przyklady.items()}
        meldunki.append("temat.przyklady -> PRZYKLADY_NISZY (%d list, %d pozycji)"
                        % (len(przyklady), sum(len(v) for v in przyklady.values())))

    # --- modele: role, okladka, pisarz zapasowy ------------------------
    role = dane.get("modele.role")
    if role is not None:
        obce = sorted(set(role) - set(cfg.MODEL_FOR))
        if obce:
            raise BledKonfiguracji(
                "modele.role: nieznane etapy: %s\nZnane etapy: %s"
                % (", ".join(obce), ", ".join(sorted(cfg.MODEL_FOR))))
        slowniki["MODEL_FOR"] = dict(role)
        meldunki.append("modele.role -> MODEL_FOR (%d rol)" % len(role))
        if "obraz" in role and "modele.obraz" not in dane:
            # ROLA I MODEL OBRAZU RAZEM. `llm.obraz` czyta `IMAGE_MODEL`,
            # a kontrola wstepna `MODEL_FOR["obraz"]` — rozjazd znaczyl, ze
            # operator „wybieral" model, ktorego zadanie nie uzywalo.
            ustaw["IMAGE_MODEL"] = role["obraz"]
            ustaw["OBRAZ_WLACZONY"] = True
    obraz = dane.get("modele.obraz")
    if obraz is not None:
        if obraz:
            ustaw["IMAGE_MODEL"] = obraz
            slowniki.setdefault("MODEL_FOR", {})["obraz"] = obraz
            ustaw["OBRAZ_WLACZONY"] = True
            meldunki.append("modele.obraz -> IMAGE_MODEL, MODEL_FOR[obraz]")
        else:
            ustaw["OBRAZ_WLACZONY"] = False
            meldunki.append("modele.obraz -> OBRAZ_WLACZONY = False (bez okladki)")

    # --- styl: sciezki wzgledem korzenia repozytorium -------------------
    for klucz, stala in (("styl.profil_pozytywny", "STYLE_PROFILE_POSITIVE"),
                         ("styl.profil_negatywny", "STYLE_PROFILE_NEGATIVE")):
        if klucz in dane:
            ustaw[stala] = _sciezka_w_repo(cfg, dane[klucz])
            meldunki.append("%s -> %s" % (klucz, stala))
    if "styl.korpus" in dane:
        if dane["styl.korpus"]:
            ustaw["STYLE_CORPUS"] = _sciezka_w_repo(cfg, dane["styl.korpus"])
            meldunki.append("styl.korpus -> STYLE_CORPUS")
        else:
            meldunki.append("styl.korpus -> STYLE_CORPUS (pusty: katalog domyslny)")

    # --- harmonogram: godziny zegara i liczba przebiegow ---------------
    godziny = dane.get("harmonogram.godziny_przebiegow_utc")
    przebiegow = dane.get("wolumeny.przebiegow_dziennie")
    if godziny is not None and przebiegow is not None and len(godziny) != przebiegow:
        raise BledKonfiguracji(
            "wolumeny.przebiegow_dziennie = %d, a harmonogram.godziny_przebiegow_utc "
            "ma %d godzin (%s) — podaj jedno albo zgodne oba"
            % (przebiegow, len(godziny), ", ".join(godziny)))
    if godziny is not None:
        ustaw["GODZINY_PRZEBIEGOW_UTC"] = tuple(godziny)
        ustaw["PRZEBIEGOW_DZIENNIE"] = len(godziny)
        meldunki.append("harmonogram.godziny_przebiegow_utc -> GODZINY_PRZEBIEGOW_UTC "
                        "(%d przebiegow na dobe)" % len(godziny))
        if przebiegow is not None:
            meldunki.append("wolumeny.przebiegow_dziennie -> PRZEBIEGOW_DZIENNIE")
    elif przebiegow is not None:
        ustaw["PRZEBIEGOW_DZIENNIE"] = przebiegow
        baza = tuple(getattr(cfg, "GODZINY_PRZEBIEGOW_UTC", ()) or ())
        if len(baza) != przebiegow:
            ustaw["GODZINY_PRZEBIEGOW_UTC"] = _rozloz_godziny(przebiegow, baza)
        meldunki.append("wolumeny.przebiegow_dziennie -> PRZEBIEGOW_DZIENNIE "
                        "(zegar: %s)" % ", ".join(
                            ustaw.get("GODZINY_PRZEBIEGOW_UTC", baza)))

    return ustaw, slowniki, meldunki


def zastosuj(dane: dict[str, Any], cfg: Any) -> list[str]:
    """Wklada wartosci do modulu `config`. Oddaje liste tego, co przestawiono.

    ATOMOWO: najpierw plan calosci (kazdy blad wychodzi tutaj, zanim cokolwiek
    zostanie zapisane), potem zapis. Zla konfiguracja zostawia `config`
    dokladnie takim, jakim go zastala.
    """
    if not dane:
        return []
    ustaw, slowniki, meldunki = _plan(dane, cfg)
    # KOPIE, NIE TE SAME OBIEKTY. Slownik kanalow wstawiony do `config` wprost
    # z pol presetu byl potem czyszczony W MIEJSCU przez `przywroc` przy
    # nastepnym presecie — i pola presetu A pustoszaly razem z nim. Preset ma
    # zostac niezmienny; `config` dostaje wlasne egzemplarze.
    for nazwa, wartosc in ustaw.items():
        setattr(cfg, nazwa, copy.deepcopy(wartosc))
    for nazwa, zmiany in slowniki.items():
        getattr(cfg, nazwa).update(copy.deepcopy(zmiany))
    return meldunki


# ---------------------------------------------------------------------------
# ZEGAR — linie `OnCalendar=` z pol harmonogramu. Czyste funkcje, bo czyta je
# `narzedzia/jednostki.py` takze na KOPII konfiguracji (`preset.proba_konfiguracji`),
# ktora nie ma funkcji z `config.py`.
# ---------------------------------------------------------------------------
def on_calendar_agenta(godziny) -> list[str]:
    """Zegar rutyny dnia: jedna linia na godzine UTC."""
    return ["*-*-* %s:00" % g for g in (godziny or ())]


def on_calendar_artykulu(dni, godzina: str, ile: int) -> list[str]:
    """Zegar artykulu; pusta lista, gdy artykulow nie ma."""
    if int(ile or 0) <= 0 or not dni:
        return []
    return ["%s *-*-* %s:00" % (",".join(dni), godzina)]


# ---------------------------------------------------------------------------
# ZAPIS — TOML z pol plaskich, z poprawnym cytowaniem napisow.
# ---------------------------------------------------------------------------
def _toml_napis(v: str) -> str:
    """Napis w cudzyslowie z ucieczkami. Nowa linia w niszy dawala plik, ktorego
    `tomllib` nie czytal (proba T08 audytu)."""
    return '"%s"' % (v.replace("\\", "\\\\").replace('"', '\\"')
                     .replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t"))


def toml_wartosc(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        return repr(v)
    if isinstance(v, Path):
        return _toml_napis(str(v).replace("\\", "/"))
    if isinstance(v, dict):
        if not v:
            return "{ }"
        return "{ %s }" % ", ".join("%s = %s" % (_toml_napis(k), toml_wartosc(x))
                                    for k, x in v.items())
    if isinstance(v, (list, tuple)):
        return "[%s]" % ", ".join(toml_wartosc(x) for x in v)
    return _toml_napis(str(v))


def zapisz_toml(dane: dict[str, Any], naglowek: list[str] | None = None,
                sekcje_dodatkowe: dict[str, dict[str, Any]] | None = None) -> str:
    """Pola plaskie -> tekst TOML. `sekcje_dodatkowe` (np. `[preset]`) ida na poczatek.

    `temat.przyklady` wychodzi jako podtabela `[temat.przyklady]`, bo tablica
    w jednej linii z pieciu list jest nieczytelna.
    """
    linie = list(naglowek or [])
    for nazwa, zawartosc in (sekcje_dodatkowe or {}).items():
        linie.append("")
        linie.append("[%s]" % nazwa)
        for pole, wartosc in zawartosc.items():
            linie.append("%s = %s" % (pole, toml_wartosc(wartosc)))
    sekcje: dict[str, list[tuple[str, Any]]] = {}
    for sciezka_pola, wartosc in dane.items():
        sekcja, pole = sciezka_pola.split(".", 1)
        sekcje.setdefault(sekcja, []).append((pole, wartosc))
    kolejnosc = list(KOLEJNOSC_SEKCJI) + sorted(set(sekcje) - set(KOLEJNOSC_SEKCJI))
    for sekcja in kolejnosc:
        if sekcja not in sekcje:
            continue
        linie.append("")
        linie.append("[%s]" % sekcja)
        podtabele = []
        for pole, wartosc in sorted(sekcje[sekcja]):
            if isinstance(wartosc, dict) and any(
                    isinstance(x, (list, tuple)) for x in wartosc.values()):
                podtabele.append((pole, wartosc))
                continue
            linie.append("%s = %s" % (pole, toml_wartosc(wartosc)))
        for pole, wartosc in podtabele:
            linie.append("")
            linie.append("[%s.%s]" % (sekcja, pole))
            for k, x in wartosc.items():
                linie.append("%s = %s" % (k, toml_wartosc(x)))
    return "\n".join(linie) + "\n"
