"""Jedno polecenie uruchamiające — to samo lokalnie i na serwerze.

    python agent-v2/run.py
    python agent-v2/run.py --stop-after scout
    python agent-v2/run.py --use-cache          # nie płać drugi raz za etap N-1

Bez interaktywnych promptów: na serwerze nie ma komu odpowiedzieć. Logi na
stdout, żeby harmonogram je przechwycił.
"""

from __future__ import annotations

import argparse
import os
import json
import sys
import traceback
from typing import Any, Callable

import config
import db
import gates
import llm
import preset
import stages

# DWA WYJATKI, KTORE NIE SA AWARIA JEDNEGO WYWOLANIA, TYLKO STANEM KONTA.
#
# `llm.BudgetExceeded` i `llm.PreflightFailed` dziedzicza po `RuntimeError`,
# wiec kazde `except Exception` ponizej lapalo je razem ze zlym JSON-em.
# `PreflightFailed` leci z `KILL_SWITCH=true`, braku klucza API, braku sufitu
# tokenow i odmowy dostawcy; `BudgetExceeded` z sufitu przebiegu (1,60 USD),
# dziennego sufitu toru i miesiecznego.
#
# WADA ZASTANA, NIE REGRES: `git show e88b456 -- agent-v2/run.py` nie tknal
# zadnej z czterech oslon ponizej. Ale ekspozycja byla ta sama, co w
# `artykul_z_puli.py`: sciezka `--wyslij` prowadzi przez `save`, `grafika`
# i `zweryfikuj` prosto do `browser.wystaw_artykul(path, wyslij=True)`, a
# `stages.zweryfikuj` na tym samym bledzie budzetu oddawalo `safe_to_post:
# True`. Cztery polkniete bramki plus przepuszczajaca piata to publikacja
# bez ani jednej dzialajacej kontroli.
#
# Krotka jest DOKLADNIE ta sama, co w `artykul_z_puli.PRZERYWAJA`
# i `stages.PRZERYWAJA` — trzy pliki maja mowic to samo. Bierzemy klasy
# z `llm`, a nie ze `stages`, bo testy podmieniaja `stages` na atrape.
#
# `llm.Truncated` NIE jest tu wymieniony celowo: odpowiedz ucieta na suficie
# tokenow to awaria JEDNEGO wywolania, po ktorej budzet nadal istnieje —
# i to wlasnie ona ma prawo isc dalej z wartoscia zapasowa.
PRZERYWAJA = (llm.BudgetExceeded, llm.PreflightFailed)

STAGES = (
    "scout", "feasibility", "discovery", "fetch",
    "classify", "synthesis", "warto_pisac", "write", "review", "forma",
)

CACHE_DIR = config.DATA_DIR / "cache"


def _utf8_stdout() -> None:
    """Konsola Windows domyślnie cp1252 i wywala się na polskich znakach.

    Serwer ma UTF-8, więc bez tego błąd wychodzi wyłącznie na jednym z tych
    dwóch komputerów — czyli najgorszy możliwy rodzaj błędu.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


_CACHE_CONTEXT = {}


def cached(stage: str, produce: Callable[[], Any], use_cache: bool) -> Any:
    import inspect, result_cache
    from pathlib import Path
    closure = inspect.getclosurevars(produce).nonlocals
    inputs = {k: v for k, v in closure.items() if k not in ('conn', 'run_id')}
    for name, value in inputs.items():
        if isinstance(value, argparse.Namespace):
            inputs[name] = {k: v for k, v in vars(value).items()
                            if k not in ('use_cache', 'stop_after', 'wyslij')}
    preset_hash = config.PRESET.odcisk if getattr(config, 'PRESET', None) else 'none'
    key = result_cache.digest({'stage': stage, 'preset': preset_hash,
        'inputs': inputs, 'arguments': _CACHE_CONTEXT, 'models': config.MODEL_FOR,
        'effort': config.EFFORT, 'tokens': config.MAX_TOKENS,
        'producer': [produce.__code__.co_code.hex(), repr(produce.__code__.co_consts)],
        'code': result_cache.code_fingerprint(Path(__file__).parent)})
    path = CACHE_DIR / (stage + '.' + key + '.json')
    value = result_cache.read(path, config.CACHE_MAX_AGE_S) if use_cache else None
    if value is not None:
        print(f'  [{stage}] z pamięci podręcznej — bez opłaty', flush=True)
        return value
    value = produce()
    result_cache.write(path, value)
    return value


class JuzDziala(RuntimeError):
    pass


ZNACZNIK_KOPII_TESTOWEJ = config.AGENT_DIR / "TO_JEST_KOPIA_TESTOWA"


def odmow_publikacji_z_kopii(wyslij: bool) -> None:
    """Kopia testowa nie ma prawa nic opublikowac. Nigdy.

    Wlasciciel: „nie odpalaj go na produkcji, wersja v2 ma byc jako test".
    Sama dyscyplina nie wystarczy — wystarczy raz dopisac `--wyslij` z pamieci
    miesnowej i eksperyment wyjdzie na zywe konto, czego nie da sie cofnac.
    Wiec kopia testowa nosi plik-znacznik obok `config.py`, a ten plik odbiera
    jej prawo publikowania. Produkcja znacznika nie ma i dziala normalnie.
    """
    if wyslij and ZNACZNIK_KOPII_TESTOWEJ.exists():
        raise SystemExit(
            "ODMOWA: to jest kopia testowa (%s), a --wyslij publikuje NA ZYWO. "
            "Produkcja stoi w ~/nia-substack-bot na galezi main. "
            "Jesli naprawde chcesz publikowac stad, usun ten plik swiadomie."
            % ZNACZNIK_KOPII_TESTOWEJ
        )


def zajmij_zamek():
    """Nie pozwala dwóm przebiegom działać naraz.

    Na serwerze harmonogram odpali agenta o stałej godzinie niezależnie od tego,
    czy poprzedni przebieg się skończył. Dwa procesy naraz to dwa razy ten sam
    artykuł i dwa razy ta sama notka — a tego nie da się cofnąć. To nie jest
    kwestia „czy", tylko „kiedy", więc zamek jest przed pierwszym uruchomieniem
    z harmonogramu, nie po pierwszej wpadce.

    Zamek trzyma system plików, nie my: przy zabiciu procesu blokada znika sama,
    więc nie zostawia po sobie zakleszczenia, które trzeba by odblokowywać ręcznie.
    """
    sciezka = config.DATA_DIR / "agent.lock"
    sciezka.parent.mkdir(parents=True, exist_ok=True)
    uchwyt = open(sciezka, "a+", encoding="utf-8")
    uchwyt.seek(0)
    try:
        try:                      # Linux, czyli serwer
            import fcntl
            fcntl.flock(uchwyt, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except ImportError:       # Windows, czyli komputer właściciela
            import msvcrt
            msvcrt.locking(uchwyt.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        uchwyt.close()
        raise JuzDziala(
            f"Inny przebieg już działa (zamek: {sciezka}). Kończę bez zmian."
        ) from None
    uchwyt.seek(0)
    uchwyt.truncate()
    uchwyt.write(f"{os.getpid()}\n")
    uchwyt.flush()
    return uchwyt


def opis_celu(cel: dict) -> dict:
    """Co wiedzielismy o celu w chwili pisania — do dziennika.

    Te liczby juz mamy w reku przy wyborze celu i dotad je wyrzucalismy. Bez nich
    przeglad po kilku dniach mowi tylko „napisano osiemnascie komentarzy", a nie
    umie odpowiedziec na jedyne pytanie, ktore cos zmienia: czy komentarz jako
    piaty wraca czesciej niz jako piecdziesiaty i ktore hasla przynosza rozmowy.
    """
    import kanal

    return {
        "publikacja": (cel.get("pub") or "")[:80],
        "skad": (cel.get("skad") or "")[:60],
        # Ilu bylo przed nami. To jest ta liczba, o ktora chodzi najbardziej.
        "komentarzy_przed": int(cel.get("komentarze") or 0),
        "reakcje_celu": int(cel.get("reakcje") or 0),
        "wiek_celu_min": round(kanal._wiek_minut(cel.get("data", "")), 1),
    }


_KONIEC_CZASU: float | None = None


def zostal_czas(na_co: str = "", potrzeba_s: float = 0.0) -> bool:
    """Czy zdazymy jeszcze cokolwiek zrobic przed koncem czasu przebiegu.

    Systemd tnie przebieg po `TimeoutStartSec` i robi to SIGTERM-em w dowolnym
    momencie — takze w polowie wpisywania komentarza. Zdarzylo sie naprawde:
    przebieg z szesnastoma komentarzami do wystawienia zostal ubity po 2,5 h.
    Lepiej skonczyc dzien krocej niz zostac przerwanym w srodku dzialania,
    ktorego nie da sie cofnac.
    """
    import time

    if _KONIEC_CZASU is None:
        return True
    zostalo = _KONIEC_CZASU - time.time()
    if zostalo > potrzeba_s:
        return True
    if potrzeba_s:
        print(f"  czas przebiegu wyczerpany — odpuszczam {na_co or 'reszte'}"
              f" (przerwa {potrzeba_s / 60:.0f} min nie zmiesci sie"
              f" w {max(0.0, zostalo) / 60:.0f} min; dokoncze w nastepnym"
              f" przebiegu)", flush=True)
    else:
        print(f"  czas przebiegu wyczerpany — odpuszczam {na_co or 'reszte'}"
              f" (dokoncze w nastepnym przebiegu)", flush=True)
    return False


# HAMULEC LICZY SIE PER BLOK, NIE PER RODZAJ DZIALANIA.
#
# `browser._POD_RZAD_ZLE` jest slownikiem po RODZAJU i globalnym dla procesu, a
# zerowanym wylacznie powodzeniem. Tymczasem `rytm("komentarz", ...)` wola nie
# tylko blok komentarzy, ale takze dyskusje pod cudzymi notkami, obserwowanie
# i subskrypcje — cztery bloki na jednym liczniku. Trzy nieudane komentarze pod
# rzad konczyly wiec blok komentarzy i NATYCHMIAST po nim trzy nastepne, ktore
# nie wykonaly ani jednej proby. Obserwowanie i subskrypcje wrecz nie moga tego
# licznika podniesc (zapisuja sie jako `obserwacja`/`subskrypcja`), tylko go
# czytaja — dziedziczyly cudza porazke i konczyly sie w milczeniu, bo `rytm`
# zwracalo False jeszcze przed pierwszym klknieciem.
#
# ILE TO KOSZTOWALO. Wg pomiaru z `browser.wystaw_odpowiedz` (siedem dni:
# 29 wpisow `odpowiedz`, z czego 23 to komentarze pod cudzymi notkami) blok
# dyskusji daje WIEKSZOSC wypowiedzi agenta — i to on gasl jako pierwszy po
# bloku komentarzy. Nowe klasy porazek z 1 wrzesnia (brak pola, brak przycisku,
# wyjatek) trafiaja teraz do dziennika, wiec ten licznik zapala sie czesciej
# niz dotad i wada z cichej robi sie codzienna.
#
# ILE KOSZTUJE ZMIANA. Przy naprawde padnietym Substacku kazdy blok wyda teraz
# do 3 wlasnych prob, zanim sie wycofa, zamiast dziedziczyc cudze. Platne sa
# tylko dwa z czterech blokow (komentarze i dyskusje pisza tekst modelem;
# obserwowanie i subskrypcje to samo klikanie), a ocena jednego celu kosztuje
# okolo 2,3 centa — czyli najgorszy przypadek to 3 dodatkowe proby, ~0,07 USD
# na przebieg. Za to blok, ktory dziala, nie ginie przez blok, ktory nie
# dziala.
#
# PROG ZOSTAJE TEN SAM: 2 pod rzad podwajaja przerwe, 3 koncza blok. Zmieniam
# ZASIEG, nie liczbe — hamulec ma sens i chroni przed dobijaniem sie do
# padnietego Substacka, tylko ma to robic tam, gdzie naprawde sie psuje.
_BAZA_HAMULCA: dict[str, int] = {}


def _pod_rzad_w_bloku(co: str, na_co: str) -> int:
    """Ile porazek pod rzad naliczyl TEN blok, odkad sie zaczal.

    Odejmujemy stan licznika z chwili PIERWSZEGO wejscia w blok. Baza zapisuje
    sie wiec zanim blok cokolwiek zrobil — takze wtedy, gdy `rytm` wychodzi
    wczesniej („pierwsze dzialanie w przebiegu nie czeka na nic"). Zapisana
    dopiero przy drugim wolaniu bralaby juz wlasna porazke tego bloku za cudzy
    dlug i prog przesunalby sie z trzech porazek na cztery.

    Powodzenie zeruje licznik globalnie, wiec gdy biezaca wartosc spadnie
    ponizej zapisanej bazy, baza traci sens i wraca do zera — inaczej blok po
    sukcesie liczylby porazki od wartosci ujemnej i hamulec nie zadzialalby
    juz nigdy.
    """
    import browser as _b

    biezacy = _b.pod_rzad_nieudanych(co)
    baza = _BAZA_HAMULCA.setdefault(na_co, biezacy)
    if biezacy < baza:
        baza = _BAZA_HAMULCA[na_co] = 0
    return biezacy - baza


def rytm(co: str, na_co: str, stan: dict) -> bool:
    """Przerwa MIEDZY dwoma dzialaniami tego samego rodzaju.

    Trzeci raz ta sama wada, tym razem zamknieta w jednym miejscu dla wszystkich
    blokow. Przerwa byla odsypiana PO dzialaniu, wiec:

      1. po OSTATNIEJ notce w bloku agent spal jeszcze 45-90 minut, choc nie
         mial juz czego robic — to jest dokladnie ta sama usterka, ktora
         naprawilem wczesniej dla restackow i ktorej wtedy nie poszukalem
         nigdzie indziej;
      2. sen zaczynal sie BEZ pytania, czy sie zmiesci. `zostal_czas` mowilo
         tylko „czy zostala jakakolwiek sekunda", wiec przepuszczalo
         dziewiecdziesieciominutowa przerwe przy dwudziestu minutach na zegarze.

    Teraz przerwa jest najpierw losowana, potem sprawdzana wobec konca
    przebiegu, i dopiero wtedy odsypiana — a pierwsze dzialanie w przebiegu nie
    czeka na nic, bo nie ma na co.

    Ta sama funkcja trzyma HAMULEC po serii porazek, liczony PER BLOK (`na_co`),
    nie per rodzaj dzialania — patrz `_BAZA_HAMULCA` i `_pod_rzad_w_bloku`.
    """
    import stages as _s

    # BAZA HAMULCA ZAPISUJE SIE TU, PRZED wczesnym wyjsciem — patrz
    # `_pod_rzad_w_bloku`. Blok ma liczyc od stanu, w jakim go zastal, a nie od
    # stanu po swojej wlasnej pierwszej probie.
    pod_rzad = _pod_rzad_w_bloku(co, na_co)

    if not stan.get(co):
        return zostal_czas(na_co)
    przerwa = _s.losuj_odstep(co)

    # WYCOFANIE PO SERII PORAZEK — reakcja W TRAKCIE, nie dopiero w analizie.
    #
    # Zmierzone 30 sierpnia na sciezce notkowej: pierwsza akcja w serii psula
    # sie w 10 procentach, druga w 31, czwarta w 50. Przy takim rozkladzie
    # czwarta proba pod rzad jest rzutem moneta za oplacony tekst, a przebieg
    # szedl dalej, bo nikt nie liczyl porazek POD RZAD.
    #
    # Dwie z rzedu: podwajamy przerwe. Tempo jest jedyna zmienna, ktora
    # pokrywa sie z awaryjnoscia, wiec zwolnienie jest jedyna rzecza, ktora
    # mozemy zrobic natychmiast i bez zgadywania przyczyny.
    # Trzy z rzedu: konczymy ten blok. Nie kasujemy dnia — kolejny przebieg
    # zaczyna z czystym licznikiem i moze sie okazac, ze to bylo chwilowe.
    if pod_rzad >= 3:
        print("  [wycofanie] %s: trzy porazki pod rzad — koncze blok %s,"
              " nastepny przebieg sprobuje od nowa" % (co, na_co), flush=True)
        return False
    if pod_rzad >= 2:
        przerwa *= 2
        print("  [wycofanie] %s: dwie porazki pod rzad — przerwa %.0f min"
              " zamiast zwyklej" % (co, przerwa / 60), flush=True)

    if not zostal_czas(na_co, przerwa):
        return False
    _s.odczekaj(co, przerwa)
    return True


def zmiesci_sie(rodzaj: str, ile: int, udzial: float = 1.0) -> int:
    """Ile z zaplanowanych dzialan NAPRAWDE zmiesci sie w czasie przebiegu.

    Rozdzielnik dzielil dzienna norme, nie patrzac na zegar. Po wydluzeniu
    odstepow miedzy notkami do 45-90 minut wieczorna rutyna dostala cztery notki
    — od trzech do szesciu godzin samego czekania przy budzecie 2h15. Zdazyla
    jedna i do komentarzy nie doszla w ogole.

    Obietnica, ktorej nie da sie dotrzymac, jest gorsza od mniejszej: blokuje
    reszte przebiegu. Lepiej wystawic dwie notki i czternascie komentarzy niz
    obiecac cztery notki i nie zrobic nic poza jedna.
    """
    import time

    if _KONIEC_CZASU is None or ile <= 0:
        return ile
    dol, gora = config.ODSTEPY.get(rodzaj, config.ODSTEP_MIEDZY_DZIALANIAMI)
    odstep = (dol + gora) / 2
    zostalo = max(0.0, _KONIEC_CZASU - time.time()) * udzial

    # PRZERW JEST O JEDNA MNIEJ NIZ DZIALAN. Przy dwoch notkach czekamy raz, nie
    # dwa — pierwsza wersja liczyla przerwe po kazdej i wychodzilo o polowe za malo.
    def potrzeba(n: int) -> float:
        return n * config.CZAS_DZIALANIA_S + max(0, n - 1) * odstep

    mozliwe = ile
    while mozliwe > 0 and potrzeba(mozliwe) > zostalo:
        mozliwe -= 1
    if mozliwe < ile:
        print(f"  [czas] {rodzaj}: {ile} sie nie zmiesci, biore {mozliwe}"
              f" (odstep ~{odstep / 60:.0f} min, zostalo {zostalo / 60:.0f} min)",
              flush=True)
    return mozliwe


def ile_przebiegow_zostalo(conn) -> int:
    """Ile przebiegow dnia jeszcze bedzie, wliczajac biezacy.

    Sluzy do dzielenia dziennej normy. Liczymy przebiegi ZAKONCZONE dzis, wiec
    ten, ktory wlasnie trwa, jeszcze sie nie liczy — i dobrze, bo ma cos wziac.

    Przebieg PRZERWANY LICZY SIE TAK SAMO jak udany, i to jest cala pointa.
    Odwrotna regula („FAILED nie zabiera slotu") brzmiala jak nadrabianie, a
    dzialala na odwrot: skoro nie podbijala `zamkniete`, to `5 - zamkniete` bylo
    WIEKSZE i kolejne przebiegi braly MNIEJ. Zmierzone uruchomieniem tej funkcji
    na spreparowanych stanach 2 wrzesnia 2026, przy budzecie 20 komentarzy:
    0 porazek -> 0/20 niewykonane, 1 porazka -> 4/20, 2 porazki -> 8/20,
    3 porazki -> 12/20. Na produkcji zaszlo to 19 sierpnia: ostatni przebieg
    doby podzielil 15 pozostalych komentarzy przez dwa i zostawil siedem.
    Odtworzone na 60 przebiegach: dzielnik byl za duzy w 7 z nich.

    Liczy sie kazdy przebieg ZAKONCZONY — DONE, FAILED albo zamkniety przez
    kontrole zdrowia (`STALE`, trzecia klasa, o ktorej stara regula nie
    wspominala). Biezacy ma `finished_at` puste, wiec sam siebie nie policzy
    i nadal ma co wziac.

    LICZYMY PO OBU DATACH, nie tylko po `finished_at`. Termin 23:40 dostaje do
    25 minut losowego opoznienia (`RandomizedDelaySec=1500`), wiec startuje
    nawet o 00:05 nastepnej doby — zmierzone: 31.08 o 00:00:45, 01.09 o
    00:12:40, a koniec po polnocy wypadl w 9 z 15 nocy. Suma obu warunkow nie
    pozwala takiemu przebiegowi zniknac z zadnej z dwoch dob.

    Nie pytamy systemd o harmonogram, choc to on odpala agenta. Godziny sa w pliku
    `.timer` i powtorzenie ich tutaj zlamaloby zasade jednej liczby w jednym
    miejscu — a rozjazd miedzy nimi wychodzilby dopiero po zmianie harmonogramu.
    """
    from datetime import datetime, timezone

    dzis = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        (zamkniete,) = conn.execute(
            "SELECT COUNT(*) FROM runs WHERE stage = 'dzien'"
            " AND finished_at IS NOT NULL"
            " AND (started_at LIKE ? OR finished_at LIKE ?)",
            (f"{dzis}%", f"{dzis}%")).fetchone()
    except Exception:
        zamkniete = 0             # licznik nie moze zatrzymac przebiegu
    return max(1, config.PRZEBIEGOW_DZIENNIE - int(zamkniete))


# --- KRYTERIUM DOBORU CELU ---------------------------------------------------
#
# DZIEN, W KTORYM KONTO PRZESTALO PISAC O CZYM INNYM. Historia komentarzy
# `gdzie_komentowalismy.json` pamieta WSZYSTKO, co bylo przed zmiana tematu —
# zmierzone 1 wrzesnia 2026: 94 hosty, z czego 53 (58 procent) ma ostatni
# komentarz sprzed tej daty i naleza do zupelnie innych dziedzin.
#
# TE 53 NIE SA NEUTRALNYM TLEM PULI. Obserwowanie wysyla im powiadomienie
# mailem, ktore sciaga ich na nasz profil — a nasza lista obserwowanych jest
# publiczna i Substack nie daje jej ukryc (subskrypcje maja ustawienie
# prywatnosci, obserwacje nie). Losowanie z calosci znaczylo wiec: w 58
# przypadkach na 100 zapraszamy na wlasny profil kogos, kto czytal u nas
# o czym innym, i zostawiamy po sobie publiczny slad.
#
# TRZECIA KOPIA TEJ SAMEJ DATY — i najgorsza z pieciu. Stala trzymala
# „2026-08-25" wpisane na sztywno, przy `config.DATA_PRZESTAWIENIA`,
# `audyt_systemu.PIVOT`, `wzajemnosc.KOTWICA_NISZY` i `raport_statystyk.PIVOT`
# z ta sama wartoscia.
#
# NAZWA NIOSLA NAZWE NISZY — `PRZESTAWIENIE_KONTA`. U konta o czymkolwiek
# innym kod czytalo sie jak zdanie nieprawdziwe, a przy zmianie tematu trzeba by
# bylo pamietac o zmianie NAZWY, nie tylko wartosci. Wartosc przeniesiono do
# konfiguracji 4 wrzesnia, ale nazwe zostawiono z uzasadnieniem „czytaja ja
# testy" — czyli test trzymal nazwe niszy w kodzie produkcyjnym. Testy sa
# nasze i zostaly przepisane.
#
# Pusty napis znaczy „to konto nie zmienialo tematu" i wtedy CALA historia
# liczy sie jako biezaca — patrz `_po_zmianie_tematu`.
PRZESTAWIENIE_KONTA = config.DATA_PRZESTAWIENIA


def _po_zmianie_tematu(kiedy) -> bool:
    """Czy ten wpis jest z obecnej epoki konta.

    Jedno miejsce dla wszystkich pytajacych — ta sama poprawka, co
    `stages._z_obecnej_epoki`. Pusta data znaczy „nie bylo zmiany tematu",
    wiec wszystko jest biezace.
    """
    if not PRZESTAWIENIE_KONTA:
        return True
    return str(kiedy or "")[:10] >= PRZESTAWIENIE_KONTA

# NAJKROTSZY ZMIERZONY ZBIEG NAZWY Z HOSTEM TO `publikacja2` — 7 znakow. Prog 6
# jest wiec ponizej wszystkiego, co dzis dziala, i odcina wylacznie zbiegi
# tak krotkie, ze byly by przypadkiem (np. osoba „Post" i host `post.substack.com`,
# ktory naprawde jest w naszej historii).
MIN_DLUGOSC_ZBIEGU = 6

# --- HAMULEC NA ODRUCH „TY MNIE POLUBILES, JA CIE OBSERWUJE" -----------------
#
# Odkad `browser.dopisz_skutki` zapisuje UCHWYT reagujacego, ten czlowiek moze
# byc celem WPROST. To zdejmuje sufit z poziomu pierwszego — i dokladnie
# dlatego wymaga hamulca, ktorego przedtem nie bylo po co stawiac.
#
# CO SIE STANIE BEZ HAMULCA, POLICZONE NA PRODUKCJI (1 wrzesnia 2026,
# `agent-v2/data/dziennik.jsonl`, 635 wierszy, 199 wpisow `skutek`):
#
#   * `dopisz_skutki` chodzi w bloku 1 tego samego przebiegu, w ktorym bloki
#     3c i 3d obserwuja i subskrybuja — kilka minut pozniej, ten sam proces;
#   * opoznienie miedzy REAKCJA a jej zapisem: mediana 5,0 h, ale 24 z 199
#     zdarzen (12 procent) zapisalo sie w niecala godzine, najszybsze po
#     2 minutach. Czyli co osma reakcja bylaby odwzajemniona obserwacja
#     w ciagu godziny, a czasem w ciagu minut;
#   * naplyw nowych reagujacych: 69 osob w 18 dni, 27 w ostatnich 7 dniach,
#     czyli 3,9 na dobe. Budzet dzialan na cudzych profilach to
#     0,42 obserwacji + 0,51 subskrypcji = 0,93 na dobe (`config`,
#     przepuszczone przez `stages.budzet_dnia`).
#
# 3,9 wchodzi, 0,93 wychodzi — bez hamulca poziom reagujacych nie oproznilby
# sie NIGDY, a poziom hostow z naszej wlasnej historii czytania nie zostalby
# osiagniety ANI RAZU. Konto odpowiadalo by obserwacja na kazde polubienie
# i na nic innego. To jest ta „sztuczna lub nieautentyczna aktywnosc", ktora
# w regulaminie Substacka stoi jako powod usuwania kont.
#
# TRZY HAMULCE, KAZDY Z WLASNA LICZBA, ZADEN NIE UDAJE CZLOWIEKA.
#
# 1. ODSTEP. Reagujacy wchodzi do puli dopiero, gdy jego reakcja ma co
#    najmniej dobe. Prog jest DLUZSZY niz nasze wlasne opoznienie zapisu
#    (97 procent zdarzen zapisuje sie w mniej niz 24 h), wiec nikt nie moze
#    byc zaczepiony w tym przebiegu, ktory go zobaczyl — a to jedyny odruch,
#    ktory naprawde widac z zewnatrz.
# 2. PROG SYGNALU. Jedno polubienie to najtansza rzecz na Substacku i samo
#    bywa zaczepka. Zadamy DWOCH reakcji albo JEDNEJ, ktora wymagala pisania
#    (odpowiedz pod nasza notka albo pod naszym komentarzem). Zmierzone na
#    tych samych 69 osobach: 26 ma dwie reakcje lub wiecej, 21 nam
#    odpowiedzialo, suma zbiorow to 31 — czyli prog odsiewa 38 z 69.
# 3. NIE ZACZEPIAMY TYCH, KTORZY JUZ NAS CZYTAJA. Piec osob z tych 69 to
#    wpis `typ="follow"` (zaobserwowali NAS), piec to `free_subscription`
#    (zasubskrybowali NAS); dodatkowo 19 uchwytow stoi w `czytelnicy.jsonl`.
#    Obserwacja zwrotna w te strone nie poszerza zasiegu ani o jedna osobe,
#    a wyglada dokladnie jak automat odwzajemniajacy.
#
# ILE ZOSTAJE. Na produkcyjnych 69 osobach: 31 po progu, 26 po odsianiu
# naszych czytelnikow, 20 po odstepie doby. Naplyw spada z 3,9 na 1,1 na dobe
# — nadal wiecej niz budzet 0,93, dlatego dochodzi jeszcze PRZEPLOT (patrz
# `cele_wedlug_pierwszenstwa`), ktory oddaje co drugi slot hostom z historii.
ODSTEP_OD_REAKCJI_H = 24
MIN_REAKCJI_BEZ_ROZMOWY = 2

# Zdarzenia, ktore znacza „ta osoba nam ODPISALA", a nie „kliknela". Nazwy sa
# Substacka: `note_reply` pod nasza notka, `comment_reply` pod naszym
# komentarzem. Dopasowanie po fragmencie, bo lista zamknieta juz raz zawiodla
# w tym samym pliku — patrz komentarz o `note_restack` w `dopisz_skutki`.
FRAGMENT_ROZMOWY = "reply"

# Zdarzenia, ktore znacza „ta osoba juz nas czyta". Wtedy nie ma czego
# zdobywac: obserwacja zwrotna nie poszerza zasiegu, tylko domyka petle.
REAKCJE_JUZ_CZYTA = ("follow", "free_subscription", "paid_subscription")


def _slug(tekst: str) -> str:
    """Nazwa do porownywania: same litery i cyfry ASCII, malymi.

    Znaki spoza ASCII wypadaja celowo. Nazwa wyswietlana potrafi niesc
    imie zapisane rodzimym pismem w nawiasie obok zapisu lacinskiego, a host
    tej samej osoby ma w adresie sam zapis lacinski. Bez odsiania znakow
    spoza ASCII te dwa napisy nigdy by sie nie zeszly.
    """
    import re

    return re.sub(r"[^a-z0-9]", "", str(tekst or "").lower())


def _slug_hosta(host: str) -> str:
    """Pierwszy czlon adresu jako slug: `www.imienazwisko.com` -> `imienazwisko`."""
    h = str(host or "").strip().lower().rstrip("/")
    if h.startswith("www."):
        h = h[4:]
    return _slug(h.split(".")[0])


def _reakcje_z_dziennika() -> tuple[set[str], dict[str, dict]]:
    """Jeden przebieg po dzienniku, dwie odpowiedzi o tych samych ludziach.

    Oddaje `(slugi_nazw, po_uchwycie)`:

      * `slugi_nazw` — do STAREJ drogi, ktora zestawia nazwe wyswietlana ze
        slugiem hosta z historii komentarzy. Ta droga trafia 7 osob z 69 —
        ale to ZASIEG PRZYRZADU, NIE ZBIEZNOSC, i kto cytuje „7 z 69" jako
        miare wplywu komentarzy, cytuje slepote tego sita. Zmierzone
        2 wrzesnia 2026: na 10 parach (nazwa, uchwyt), ktore znamy z pola
        `uchwyty`, rownosc slug(nazwa) == slug(hosta) trafia 5 razy na 10
        (`publikacja3` to „Publikacja Chaosu", `theaioperators` to „Norbert
        Saad", „Thor" wypada na progu dlugosci). Porownanie nazwy reagujacego
        z polem `publikacja` z dziennika — ktore trzyma NAZWE publikacji,
        a nie host — daje 26 z 73. Najwiekszy reagujacy, „Publikacja Chaosu"
        (112 z 279 zetkniec, 40 procent), JEST publikacja, pod ktora
        komentowalismy 29 sierpnia, a stary przyrzad go nie widzi.
        Droga zostaje, bo dziala takze dla 199 wpisow sprzed 1 wrzesnia 2026,
        ktore uchwytu nie maja i nigdy nie dostana (`dopisz_skutki` pomija
        zdarzenia juz zapisane, wiec historii nie da sie uzupelnic wstecz);
      * `po_uchwycie` — {uchwyt: {"ile", "rozmowa", "juz_czyta", "ostatnia"}},
        czyli NOWA droga: reagujacy jako cel wprost.

    TRZY STANY POLA `uchwyty`, I KAZDY ZNACZY CO INNEGO. Brak klucza to wpis
    sprzed poprawki („nie wiem"), `[]` to zdarzenie bez nadawcow, a `None`
    w srodku listy to jeden konkretny czlowiek, ktorego uchwytu Substack nie
    podal. Zaden z tych trzech nie jest bledem i zaden nie moze wywalic
    doboru celu — wiec czytamy defensywnie i po prostu pomijamy.

    NAZWA I UCHWYT SA PARAMI Z KONSTRUKCJI, ale ufamy temu tylko wtedy, gdy
    obie listy maja te sama dlugosc. `browser.dopisz_skutki` buduje je z jednej
    listy par, wiec rowna dlugosc jest tam gwarantowana; nierowna oznacza wpis
    z innego zrodla albo recznie ruszany plik, a wtedy `kto[i]` i `uchwyty[i]`
    moglyby byc roznymi osobami. Cel wygladajacy na zmierzony, a nie bedacy
    nim, jest gorszy od braku celu — patrz `tests/test_uchwyt_reakcji.py`.
    """
    import json as _json

    import browser

    slugi: set[str] = set()
    po_uchwycie: dict[str, dict] = {}
    moj = _slug(config.SUBSTACK_HANDLE)
    try:
        if not browser.DZIENNIK.exists():
            return slugi, po_uchwycie
        for linia in browser.DZIENNIK.read_text(encoding="utf-8").splitlines():
            linia = linia.strip()
            if not linia:
                continue
            try:
                wpis = _json.loads(linia)
            except ValueError:
                continue          # jedna zepsuta linia nie psuje calej reszty
            if not isinstance(wpis, dict) or wpis.get("rodzaj") != "skutek":
                continue
            kto = list(wpis.get("kto") or [])
            for nazwa in kto:
                s = _slug(nazwa)
                if len(s) >= MIN_DLUGOSC_ZBIEGU:
                    slugi.add(s)
            uchwyty = wpis.get("uchwyty")
            if not isinstance(uchwyty, list) or len(uchwyty) != len(kto):
                continue          # stary wpis albo rozjazd — nie zgadujemy
            typ = str(wpis.get("typ") or "")
            kiedy = str(wpis.get("kiedy_zdarzenia") or wpis.get("kiedy") or "")
            for uchwyt in uchwyty:
                uchwyt = str(uchwyt or "").strip().lstrip("@")
                if not uchwyt:
                    continue      # `None` znaczy „tej osoby nie umiem nazwac"
                # MY SAMI JESTESMY W TYM KANALE. Zmierzone na produkcji:
                # 9 zdarzen `scheduled_note_sent` ma w polu `kto` wpisane
                # „Your Publication", czyli nas — Substack melduje w tym
                # samym kanale, ze nasza zaplanowana notka poszla. Dopoki cel
                # wychodzil z rownosci nazwy z hostem, bronil nas przed tym
                # odsiew `host == moj_host`; przy uchwycie WPROST agent
                # probowalby zaobserwowac wlasny profil.
                if _slug(uchwyt) == moj:
                    continue
                stan = po_uchwycie.setdefault(
                    uchwyt, {"ile": 0, "rozmowa": False,
                             "juz_czyta": False, "ostatnia": ""})
                stan["ile"] += 1
                if FRAGMENT_ROZMOWY in typ:
                    stan["rozmowa"] = True
                if typ in REAKCJE_JUZ_CZYTA:
                    stan["juz_czyta"] = True
                if kiedy > stan["ostatnia"]:
                    stan["ostatnia"] = kiedy
    except OSError:
        pass                      # brak dziennika to pusta wiedza, nie awaria
    return slugi, po_uchwycie


def kogo_juz_dotknelismy() -> set[str]:
    """Slugi nazw ludzi, ktorzy zareagowali na NASZA tresc — z dziennika.

    ## Po co ta droga zostaje, skoro reagujacy ma juz uchwyt

    Bo 199 wpisow `skutek` sprzed 1 wrzesnia 2026 uchwytu NIE MA i nie
    dostanie: `browser.dopisz_skutki` pomija zdarzenia, ktore juz zapisal, wiec
    kanalu aktywnosci nie da sie odczytac po raz drugi po to samo. Te 69 osob
    zostaje wiec na zawsze widoczne wylacznie przez nazwe — i ta droga trafia
    z nich 7, z czego po odsiewie tematycznym 3.

    Wpisy `rodzaj="skutek"` to jedyna zmierzona przeslanka, jaka mamy o tym,
    skad biora sie czytelnicy: 11 z 19 naszych czytelnikow zostawilo wczesniej
    taki slad, a 0 z 19 to konto, ktore MY zasubskrybowalismy.

    CO TA DROGA UMIE, A CZEGO NIE. Umie tylko PODNIESC host, ktory i tak jest
    w historii naszych komentarzy — nie potrafi zrobic celu z osoby, ktorej
    nazwa nie sklada sie na adres. Nowa droga (`reagujacy_jako_cele`) potrafi,
    bo dostaje uchwyt wprost. Obie zyja obok siebie i licza sie osobno
    w `rachunek`, zeby bylo widac, ktora naprawde cos daje.
    """
    return _reakcje_z_dziennika()[0]


def nasi_czytelnicy() -> set[str]:
    """Uchwyty ludzi, ktorzy JUZ nas czytaja — z `czytelnicy.jsonl`. Tylko odczyt.

    Po co: zaczepianie ich nie poszerza zasiegu ani o jedna osobe, a wyglada
    dokladnie jak automat odwzajemniajacy — patrz hamulec nr 3 przy
    `ODSTEP_OD_REAKCJI_H`.

    SUMA ZE WSZYSTKICH ZRZUTOW, NIE OSTATNI. Kto raz nas czytal, ten nas zna;
    zniknieciecie z ostatniego zrzutu znaczy najczesciej, ze przeszedl miedzy
    zakladkami (Substack pokazuje osobe obserwujaca I subskrybujaca wylacznie
    w „Subscribers" — zmierzone na przypadku „Jedenasty", patrz
    `browser.kto_nas_czyta`), a nie ze przestal nas czytac.

    ZRZUT OKROJONY NIE JEST DOWODEM NA NIEOBECNOSC, ale nam to nie szkodzi:
    ta funkcja buduje sume, wiec brakujaca zakladka moze najwyzej NIE DODAC
    kogos, kogo dodal inny zrzut. Blad w te strone kosztuje jedno wejscie na
    profil; blad w druga skreslalby cel bez powodu.
    """
    import json as _json

    import browser

    uchwyty: set[str] = set()
    try:
        if not browser.CZYTELNICY.exists():
            return uchwyty
        for linia in browser.CZYTELNICY.read_text(encoding="utf-8").splitlines():
            linia = linia.strip()
            if not linia:
                continue
            try:
                zrzut = _json.loads(linia)
            except ValueError:
                continue
            if not isinstance(zrzut, dict):
                continue
            for grupa in ("obserwujacy", "subskrybenci"):
                for osoba in zrzut.get(grupa) or []:
                    if not isinstance(osoba, dict):
                        continue
                    u = str(osoba.get("uchwyt") or "").strip().lstrip("@")
                    if u:
                        uchwyty.add(u)
    except OSError:
        pass                      # brak pliku to pusta wiedza, nie awaria
    return uchwyty


def reagujacy_jako_cele() -> tuple[list[str], dict]:
    """Ludzie, ktorzy zareagowali na nasza tresc, jako CELE WPROST. Zero sieci.

    Oddaje `(adresy, rachunek)`. Adres ma postac `<uchwyt>.substack.com`,
    i to jest decyzja, nie skrot — uzasadnienie nizej.

    ## Dlaczego reagujacy wchodzi do puli, a nie tylko podnosi kogos w niej

    Do 1 wrzesnia 2026 poziom pierwszy tylko PODNOSIL hosty, ktore i tak byly
    w historii naszych komentarzy. Znaczylo to, ze osoba, ktora polubila nasza
    notke, ale pod ktorej publikacja nigdy nie komentowalismy, byla dla doboru
    celu niewidzialna — zmierzone: 62 z 69 takich osob. Uchwyt zmienia to
    wprost: mamy czym ja zaadresowac, wiec nie ma po co udawac, ze jej nie ma.

    ODSIEW TEMATYCZNY JEJ NIE DOTYCZY, i to tez jest swiadome. Granica
    `PRZESTAWIENIE_KONTA` pyta „czy czytalismy ich PO tym, jak konto
    zmienilo temat" — bo host z historii moze pochodzic sprzed zmiany
    tematu. Reagujacy nie ma tego problemu: on zareagowal na TE tresc, ktora
    konto wystawia dzis. Sam jest swiezszym dowodem niz data komentarza.

    ## Dlaczego adres, a nie sam uchwyt

    Cala dalsza droga w `obserwuj` i `subskrybuj` bierze HOST i sama wyprowadza
    z niego uchwyt. Wsadzenie golego uchwytu do tej listy weszlo by w
    `browser.uchwyt_publikacji("igordziewiaty")`, ktore dla nazwy bez kropki
    otwiera sesje przegladarki i pyta `https://igordziewiaty/api/v1/posts` —
    czyli adres, ktorego nie ma. Postac `<uchwyt>.substack.com` przechodzi
    natomiast przez cala droge BEZ ANI JEDNEGO ZAPYTANIA:
    `uchwyt_publikacji` skraca ja z powrotem do uchwytu jednym `split`,
    `czy_juz_obserwujemy` i `czy_juz_subskrybujemy` porownuja uchwyt
    z uchwytem, a `obserwuj_profil` i `zasubskrybuj` i tak ida na
    `substack.com/@uchwyt`. POD SAM TEN ADRES NIC NIGDY NIE WCHODZI — jest
    formatem wewnetrznym, nie obietnica, ze taka publikacja istnieje.

    CO Z TEGO WYNIKA I CZEGO NIE UDAJE. Reagujacy, ktory nie ma wlasnej
    publikacji, nie ma tez przycisku „Subscribe" — blok subskrypcji wejdzie
    u niego raz, zapisze „nie ma przycisku subskrypcja" i `kogo_juz_subskrybujemy`
    zamknie go na zawsze. Kosztuje to JEDNO wejscie na profil, raz na osobe,
    i jest dokladnie tym samym, co dzis kosztuje `publikacja18`. Obserwowanie
    dziala u kazdego, bo nie wymaga publikacji.
    """
    from datetime import datetime, timedelta, timezone

    _, po_uchwycie = _reakcje_z_dziennika()
    czytelnicy = nasi_czytelnicy()
    granica = (datetime.now(timezone.utc)
               - timedelta(hours=ODSTEP_OD_REAKCJI_H)).isoformat()[:19]

    slabi = swiezy = juz_czytaja = 0
    adresy: list[str] = []
    for uchwyt, stan in sorted(po_uchwycie.items()):
        if stan["juz_czyta"] or uchwyt in czytelnicy:
            juz_czytaja += 1
            continue
        if stan["ile"] < MIN_REAKCJI_BEZ_ROZMOWY and not stan["rozmowa"]:
            slabi += 1
            continue
        # ODSTEP LICZY SIE OD REAKCJI, NIE OD JEJ ZAPISU. `kiedy_zdarzenia` to
        # czas, ktory widzi czlowiek po drugiej stronie; `kiedy` to godzina
        # naszego przebiegu i o niej on nie wie nic. Reakcja bez czytelnej daty
        # CZEKA — brak daty nie moze byc przepustka, bo to jedyny warunek,
        # ktory stoi miedzy nami a odruchem.
        if not stan["ostatnia"] or stan["ostatnia"][:19] > granica:
            swiezy += 1
            continue
        adresy.append("%s.substack.com" % uchwyt)
    return adresy, {
        "reagujacy_z_uchwytem": len(po_uchwycie),
        "reagujacy_juz_czyta": juz_czytaja,
        "reagujacy_slabi": slabi,
        "reagujacy_swiezy": swiezy,
        "reagujacy": len(adresy),
        # PROGI JADA W RACHUNKU, A NIE JAKO GLOBALNE STALE. Bloki `obserwuj`
        # i `subskrybuj` sa w testach WYCINANE z `run.py` przez `ast`
        # i uruchamiane w wasskiej przestrzeni nazw — kazda stala, po ktora
        # blok siega bezposrednio, musi tam byc dopisana recznie i cicho
        # wywraca test przy nastepnej zmianie. Liczba, ktora blok tylko
        # drukuje, ma isc razem z reszta rachunku.
        "odstep_h": ODSTEP_OD_REAKCJI_H,
        "prog_reakcji": MIN_REAKCJI_BEZ_ROZMOWY,
    }


def _przeplot(pierwsza: list[str], druga: list[str]) -> list[str]:
    """Na przemian z dwoch list; gdy jedna sie konczy, druga idzie dalej.

    Nie `pierwsza + druga`, bo przy budzecie 0,93 dzialania na dobe i naplywie
    1,1 reagujacego na dobe druga lista nie zostalaby osiagnieta nigdy — patrz
    rachunek przy `cele_wedlug_pierwszenstwa`.
    """
    wynik: list[str] = []
    for i in range(max(len(pierwsza), len(druga))):
        if i < len(pierwsza):
            wynik.append(pierwsza[i])
        if i < len(druga):
            wynik.append(druga[i])
    return wynik


def cele_wedlug_pierwszenstwa(historia: dict) -> tuple[list[str], dict]:
    """Hosty do zaczepienia, w kolejnosci pierwszenstwa. Zero sieci.

    Zwraca `(kandydaci, rachunek)`. `rachunek` jest po to, zeby blok mial co
    wydrukowac i czym uzasadnic ZERO — pusta pula z podanym powodem jest
    uczciwa, pusta pula bez powodu wyglada jak blok, ktory sie nie odbyl.

    ## Co bylo przedtem

    `random.shuffle` na CALEJ historii komentarzy. Zadnego kryterium: ani
    wielkosci, ani tematu, ani jezyka, ani swiezosci. Skutek zmierzony
    1 wrzesnia 2026: z 12 kont, ktorym dalismy subskrypcje, odwzajemnilo sie
    zero, a mediana ich wielkosci to ~5300 subskrybentow (skrajne 348 000
    i 111 000) — czyli los systematycznie prowadzil nas do duzych kont, dla
    ktorych jestesmy szumem.

    ## Trzy poziomy, z czego jeden jest twardy, a jeden slabszy niz w zamysle

    0. WPROST: czlowiek, ktory zareagowal na nasza tresc i ma zapisany uchwyt
       (`reagujacy_jako_cele`). To nie jest juz podnoszenie kogos z puli, tylko
       ROZSZERZENIE puli o ludzi, ktorych w niej nigdy nie bylo — 62 z 69
       reagujacych nie ma w historii naszych komentarzy zadnego hosta.
    1. NAJMOCNIEJ Z HOSTOW: host, ktorego nazwa zgadza sie z kims, kto juz
       zareagowal na nasza tresc (`kogo_juz_dotknelismy` — i tam stoi, ile
       z tego naprawde da sie wyprowadzic: 7 osob z 69).
    2. POTEM: host z komentarzem od `PRZESTAWIENIE_KONTA` wlacznie.
       41 z 94 hostow na dzien wdrozenia.
    3. NIGDY: host, ktorego OSTATNI komentarz jest starszy. 53 z 94.

    ## Poziom 0 NIE zjada calej puli, i to jest osobna decyzja

    Reagujacych przybywa 3,9 na dobe, a po hamulcach 1,1 (patrz
    `ODSTEP_OD_REAKCJI_H`). Budzet dzialan na cudzych profilach to 0,93 na
    dobe. Gdyby poziom 0 szedl w calosci przed hostami, poziom 2 nie zostalby
    osiagniety ANI RAZU — konto przestaloby obserwowac kogokolwiek, kogo
    naprawde czyta, i odpowiadaloby wylacznie na reakcje.

    Dlatego pula powstaje PRZEPLOTEM: reagujacy, host, reagujacy, host.
    Pierwszy slot nadal nalezy do reagujacego (to najmocniejszy sygnal, jaki
    mamy), ale co drugi wraca do historii czytania — przy budzecie ponizej
    jednego dzialania na dobe znaczy to mniej wiecej co drugi dzien. Gdy
    ktorakolwiek lista sie konczy, druga idzie dalej bez przerw.

    Poziom 3 dziala dokladnie tak, bo `kanal.zapamietaj_komentarz` NADPISUJE
    date przy kazdym komentarzu. Wartosc jest wiec zawsze data OSTATNIEGO
    komentarza, a `data < granica` znaczy „nie komentowalismy tam ani razu po
    przestawieniu konta" — bez potrzeby trzymania calej historii dat.

    HOST BEZ CZYTELNEJ DATY TEZ WYPADA. Nie dlatego, ze cos o nim wiemy, tylko
    dlatego, ze nie wiemy nic: cena pomylki jest niesymetryczna. Falszywe
    odsianie kosztuje jednego kandydata z puli, ktora i tak rosnie o okolo
    piec hostow dziennie; falszywe dopuszczenie wysyla maila komus, kogo
    przestalismy czytac.

    LOS ZOSTAJE, ALE JUZ TYLKO WEWNATRZ POZIOMU. Stala kolejnosc byla by tu
    gorsza niz los: agent codziennie zaczynalby od tego samego konca listy,
    a rowny rytm to jedyny podpis automatu, ktorego Substack nie musi nawet
    szukac. Los rozstrzyga wiec remisy w obrebie poziomu, a nie to, ktory
    poziom idzie pierwszy.
    """
    import random

    moj_host = "%s.substack.com" % config.SUBSTACK_HANDLE
    po, przed = [], []
    for host, kiedy in (historia or {}).items():
        if not host or host == moj_host:
            continue
        if _po_zmianie_tematu(kiedy):
            po.append(host)
        else:
            przed.append(host)

    reagujacy, rachunek = reagujacy_jako_cele()
    # TEN SAM CZLOWIEK NIE MOZE STAC W PULI DWA RAZY. `igordziewiaty` jest
    # jednoczesnie reagujacym i hostem `igordziewiaty.substack.com` z historii
    # komentarzy — bez tego odsiewu poszedlby przez dwa poziomy naraz i zjadl
    # dwa sloty na jednym profilu. Porownujemy slugiem, bo host z historii bywa
    # wlasna domena (`www.jankowalski.com` to `kowalski`... i akurat tam slug
    # NIE zbiega sie z uchwytem — dlatego to sito lapie tylko czesc, a reszte
    # domyka `czy_juz_obserwujemy` po rozwiazaniu uchwytu).
    juz_w_reakcjach = {_slug_hosta(a) for a in reagujacy}
    # LICZBY DO `rachunek` BIERZEMY SPRZED ODSIEWU DUBLI. Inaczej pusta pula
    # tlumaczylaby sie krotsza historia, niz naprawde mamy — a to jest ta sama
    # klasa klamstwa, przed ktora broni `powod_pustej_puli`.
    ilu_po, ilu_przed = len(po), len(przed)
    po_odsianiu = [h for h in po if _slug_hosta(h) not in juz_w_reakcjach]
    zdublowani = ilu_po - len(po_odsianiu)
    po = po_odsianiu

    dotkneli = kogo_juz_dotknelismy()
    ze_skutkiem = [h for h in po if _slug_hosta(h) in dotkneli]
    reszta = [h for h in po if _slug_hosta(h) not in dotkneli]
    # LOS ZOSTAJE, ALE JUZ TYLKO WEWNATRZ POZIOMU — takze wsrod reagujacych.
    # Kolejnosc „od najswiezszej reakcji" byla by tu najgorsza z mozliwych:
    # to dokladnie ten wzorzec, ktory hamulce maja rozbroic.
    random.shuffle(reagujacy)
    random.shuffle(ze_skutkiem)
    random.shuffle(reszta)
    hosty = ze_skutkiem + reszta
    rachunek.update({
        "wszystkich": ilu_po + ilu_przed,
        "sprzed_przestawienia": ilu_przed,
        "po_przestawieniu": ilu_po,
        "ze_skutkiem": len(ze_skutkiem),
        "zdublowani": zdublowani,
    })
    return _przeplot(reagujacy, hosty), rachunek


def powod_pustej_puli(rachunek: dict) -> str:
    """Zdanie do dziennika, gdy po odsianiu nie zostal nikt.

    Zero z powodem jest uczciwe; zero udajace wynik nie jest. A powod musi
    niesc LICZBY, bo za pol roku nikt nie odtworzy, czy pula byla pusta, bo
    historia byla krotka, czy dlatego, ze cala wpadla w odsiew tematyczny.

    PO ROZSZERZENIU PULI ZDANIE MUSI MIEC OBA POZIOMY. Od 1 wrzesnia 2026
    kandydat moze przyjsc z historii komentarzy ALBO z reakcji na nasza tresc,
    i kazdy z tych dwoch ma wlasny odsiew. Zero mowiace tylko o hostach
    byloby juz zerem bez powodu — czyli dokladnie tym, przed czym ta funkcja
    powstala, tylko o jedno pietro wyzej.
    """
    return ("pula pusta po odsianiu: %d hostow w historii, %d sprzed"
            " zmiany tematu konta (%s), %d po niej"
            "; reagujacych z uchwytem %d, z tego %d juz nas czyta,"
            " %d ponizej progu %d reakcji (bez odpowiedzi),"
            " %d mlodszych niz %d h, w puli %d"
            % (rachunek.get("wszystkich", 0),
               rachunek.get("sprzed_przestawienia", 0),
               PRZESTAWIENIE_KONTA,
               rachunek.get("po_przestawieniu", 0),
               rachunek.get("reagujacy_z_uchwytem", 0),
               rachunek.get("reagujacy_juz_czyta", 0),
               rachunek.get("reagujacy_slabi", 0), MIN_REAKCJI_BEZ_ROZMOWY,
               rachunek.get("reagujacy_swiezy", 0), ODSTEP_OD_REAKCJI_H,
               rachunek.get("reagujacy", 0)))


def kogo_juz_subskrybujemy() -> set[str]:
    """Uchwyty, na ktore subskrypcja NIE MA JUZ CO wysylac. Z dziennika, bez sieci.

    ## Co to kosztowalo

    `subskrybuj` nie sprawdzalo niczego. Zmierzone 1 wrzesnia 2026 na
    produkcyjnym dzienniku: 18 prob subskrypcji, 6 w kosz. Jedna z nich to
    `publikacja-b` — konto zasubskrybowane 16 sierpnia, na ktore agent
    wszedl ponownie 25 sierpnia i zapisal porazke „nie ma przycisku
    subskrypcja". Przycisku nie bylo, bo mowil juz „Subscribed".

    ## Dwa rodzaje wpisow i dlaczego oba znacza to samo dla planu dnia

    * `udane=True` — subskrypcja weszla. Druga jest bezcelowa.
    * `udane=False` z powodem „nie ma przycisku subskrypcja" — profil
      ODPOWIEDZIAL, tylko nie tym, czego chcielismy. Tak wyglada i konto juz
      zasubskrybowane (`publikacja-b`), i publikacja duzej redakcji, ktora
      przycisku Substacka nie ma wcale. W obu przypadkach kolejne wejscie da
      dokladnie ten sam wynik.

    POWODOW INNYCH NIE BIERZEMY, i to jest cala ostroznosc tej funkcji.
    Timeout, padnieta sesja albo zamkniety Chrome to awaria PO NASZEJ STRONIE
    — „nie wiem" nie jest dowodem i nie moze skreslac konta na zawsze. To ta
    sama zasada, ktora `browser.dopisz_wynik` nazywa `o_hoscie`.

    NAPIS JEST WSPOLNY Z `browser._klik_na_profilu` I NIKT TEGO NIE PILNUJE.
    Tam powstaje `f"nie ma przycisku {rodzaj} u {handle}"`, tu go czytamy.
    Rozjechanie sie tych dwoch miejsc wylaczy odsiew po cichu — dokladnie tak,
    jak `browser.POWOD_HOST_NIE_POKAZUJE` musial stac sie stala. Docelowo ten
    napis ma tam zostac stala i byc importowany; do tego czasu pilnuje go test.
    """
    import json as _json

    import browser

    zamkniete: set[str] = set()
    try:
        if not browser.DZIENNIK.exists():
            return zamkniete
        for linia in browser.DZIENNIK.read_text(encoding="utf-8").splitlines():
            linia = linia.strip()
            if not linia:
                continue
            try:
                wpis = _json.loads(linia)
            except ValueError:
                continue
            if not isinstance(wpis, dict) or wpis.get("rodzaj") != "subskrypcja":
                continue
            komu = str(wpis.get("komu") or "").strip().lstrip("@")
            if not komu:
                continue
            if wpis.get("udane"):
                zamkniete.add(komu)
            elif str(wpis.get("powod") or "").startswith(
                    "nie ma przycisku subskrypcja"):
                zamkniete.add(komu)
    except OSError:
        pass                      # brak dziennika to pusta wiedza, nie awaria
    return zamkniete


def czy_juz_subskrybujemy(host: str, zamkniete: set[str],
                          pamiec: dict | None = None) -> bool:
    """Czy ten HOST wskazuje konto, na ktore nie ma juz po co wchodzic.

    Tanie sito PRZED `browser.uchwyt_publikacji`, ktore dla wlasnej domeny
    kosztuje osobna sesje przegladarki i zapytanie do API. Dla adresow
    w domenie Substacka jest dokladne, bo `uchwyt_publikacji` wyprowadza uchwyt
    ta sama regula (`host.split(".")[0]`), wiec porownujemy uchwyt z uchwytem.

    Dla wlasnej domeny probujemy jeszcze mapy `host->uchwyt` z pamieci
    obserwowanych — to ten sam plik, ktory odsiewa obserwacje, i jedyne
    miejsce, gdzie `www.wlasnadomena.example` laczy sie z `autor1`. Gdy mapy nie ma,
    oddajemy False i sprawdzamy jeszcze raz PO rozwiazaniu uchwytu; kosztuje to
    zapytanie, ale nie kosztuje slotu.
    """
    host = str(host or "").strip().lower().rstrip("/")
    if not host:
        return False
    if host.endswith(".substack.com"):
        if host.split(".")[0] in zamkniete:
            return True
    uchwyt = (pamiec or {}).get("hosty", {}).get(host)
    return bool(uchwyt and uchwyt in zamkniete)


def dzien(conn, run_id: int, wyslij: bool) -> int:
    """Jeden dzień pracy konta: notki, komentarze, odpowiedzi, polubienia.

    Rutyna, której do tej pory nie było — każda zdolność działała osobno, a nic
    ich nie spinało. Trzy zasady, wszystkie z rzeczy, które nas już kosztowały:

    1. KAŻDY BLOK OSOBNO. Padnięte komentarze nie zabierają ze sobą notek.
       Dzień częściowo udany jest znacznie lepszy od dnia przerwanego w połowie.
    2. ODPOWIEDZI POZA LIMITEM. U siebie jesteśmy gospodarzem; pytanie bez
       odpowiedzi pod własnym tekstem szkodzi bardziej niż komentarz za dużo.
    3. NIC NIE WYCHODZI BEZ `--wyslij`. Domyślnie agent pokazuje, co by zrobił.
    """
    import time

    import alarm
    import browser
    import kanal

    global _KONIEC_CZASU
    _KONIEC_CZASU = time.time() + max(
        60, config.LIMIT_CZASU_PRZEBIEGU_S - config.ZAPAS_CZASU_S)

    budzet = stages.budzet_dnia(conn)

    # ILE JUZ DZIS POSZLO — pytamy Substacka, nie wlasnej ksiegowosci.
    # Wlasciciel zauwazyl, ze dwie notki wyszly trzy minuty po sobie: caly
    # dzienny przydzial szedl w jednym ciagu, bo przebieg robil wszystko naraz.
    # Teraz zegar odpala agenta KILKA RAZY DZIENNIE, a kazdy przebieg dobiera
    # tylko brakujaca czesc — dzieki temu notki rozkladaja sie na godziny,
    # a nie na minuty.
    juz = browser.ile_dzis_wystawione()
    # OBSERWACJE I SUBSKRYPCJE TEZ, i to jest naprawa z 20 sierpnia. Bloki 3c
    # i 3d braly `budzet["follow"]` oraz `budzet["subskrypcje"]` — czyli PELNY
    # dzienny przydzial — w KAZDYM z trzech przebiegow. Realny wolumen wychodzil
    # okolo trzykrotnosci konfiguracji: ~60-70 obserwacji miesiecznie zamiast
    # 20-30 i ~27 subskrypcji zamiast 6-12. Kazda subskrypcja to poczta do
    # skrzynki wlasciciela, wiec to nie byla pomylka kosmetyczna.
    zostalo = {k: max(0, budzet[k] - juz.get(k, 0))
               for k in ("notki", "komentarze", "lajki", "restacki",
                         "follow", "subskrypcje")}

    # CICHY DZIEN. Wyciszamy to, co NADAJEMY — notki i restacki. Komentarze,
    # polubienia i obserwacje zostaja, bo to jest czytanie cudzych rzeczy,
    # a nie nadawanie wlasnych. Odpowiedzi zostaja tym bardziej: nieodpisanie
    # komus, kto sie do nas odezwal, nie jest cisza tylko lekcewazeniem.
    if config.cichy_dzien():
        print("   >> CICHY DZIEN — nie nadajemy wlasnych tresci. Rozmowa idzie"
              " normalnie: odpowiedzi, komentarze i czytanie bez zmian.",
              flush=True)
        for _poz in config.CICHY_DZIEN_WYCISZA:
            zostalo[_poz] = 0
    # Reszte dzielimy przez przebiegi, ktore JESZCZE dzis beda — nie przez
    # wszystkie. Dzielenie przez wszystkie systematycznie zaniza: przy budzecie
    # 16 komentarzy trzy przebiegi braly 5, 4 i 2, czyli 11 zamiast 16. Przez
    # pozostale wychodzi 5, 6 i 5. Ostatni przebieg dnia dzieli przez jeden,
    # wiec dobiera cala reszte i norma sie domyka.
    zostalo_przebiegow = ile_przebiegow_zostalo(conn)
    # `max(1, ...)` ISTNIEJE PO TO, zeby budzet mniejszy niz liczba przebiegow
    # nie zaokraglal sie do zera i nie przepadal — ale NIE MOZE przekroczyc
    # tego, co zostalo. Przy budzecie 1 i piatce przebiegow dawalo to jedna
    # sztuke w KAZDYM z nich, czyli pieciokrotnosc planu.
    #
    # Wlasciwa naprawa siedzi w `browser.z_dziennika_dzis`, ktory nie liczyl
    # subskrypcji ani obserwacji, wiec `zostalo` nigdy nie malalo. To tutaj to
    # druga linia obrony: gdyby ktores dzialanie znowu wypadlo z licznika,
    # przekroczenie zatrzyma sie na jednej sztuce zamiast rosnac z kazdym
    # przebiegiem.
    na_teraz = {k: min(v, max(1, round(v / zostalo_przebiegow))) if v else 0
                for k, v in zostalo.items()}
    # Obietnica przyciete do zegara. Notki maja pierwszenstwo, ale nie caly przebieg.
    na_teraz["notki"] = zmiesci_sie("notka", na_teraz["notki"],
                                    config.UDZIAL_CZASU_NA_NOTKI)
    na_teraz["komentarze"] = zmiesci_sie("komentarz", na_teraz["komentarze"])
    print(f"   dzis juz: notki={juz.get('notki', 0)} "
          f"komentarze={juz.get('komentarze', 0)} lajki={juz.get('lajki', 0)}   "
          f"przebiegow zostalo: {zostalo_przebiegow}   "
          f"w tym przebiegu: notki={na_teraz['notki']} "
          f"komentarze={na_teraz['komentarze']} lajki={na_teraz['lajki']}",
          flush=True)
    zrobione = {"notki": 0, "komentarze": 0, "odpowiedzi": 0, "polubienia": 0,
                "restacki": 0}
    # Czy dany rodzaj dzialania juz w tym przebiegu wyszedl. Wspolne dla
    # wszystkich blokow, bo profil widzi jeden ciag zdarzen, nie nasze bloki:
    # komentarz tuz po obserwacji to dla Substacka dwa dzialania pod rzad.
    rytm_stanu: dict[str, bool] = {}
    # Hamulec liczy porazki OD POCZATKU BLOKU — patrz `_pod_rzad_w_bloku`.
    # Bazy sa wiec wazne tylko w obrebie jednego przebiegu i musza zniknac
    # razem z nim. Testy wolaja `dzien()` wiecej niz raz w jednym procesie,
    # a stara baza przeniosla by hamulec na nastepne wywolanie.
    _BAZA_HAMULCA.clear()

    # OKNO PUBLIKACJI liczone w strefie CZYTELNIKOW. Poza nim agent nie milczy
    # calkiem — polubienia i odpowiedzi zostaja, bo czytanie o polnocy jest
    # ludzkie, a odpowiedz gospodarza nie moze czekac do rana. Nie wychodza za to
    # NOWE tresci, ktore konkuruja o miejsce w kanale.
    wolno, powod = config.pora_na_publikacje()
    print(f"   okno publikacji: {'TAK' if wolno else 'NIE'} — {powod}", flush=True)
    if not wolno:
        # OKNO WYCISZA NOTKI, NIE KOMENTARZE — poprawka z 31 sierpnia 2026.
        #
        # Uzasadnienie okna brzmi: „nowe tresci konkuruja o miejsce w kanale,
        # a tekst wrzucony, gdy publicznosc spi, traci pierwsze godziny
        # widocznosci". To jest prawda o NOTCE — naszej wlasnej tresci na
        # naszym profilu.
        #
        # Komentarz stoi pod CUDZYM tekstem. Jego widocznosc zalezy od ruchu
        # na TAMTYM poscie, na ktory nasza pora dnia nie ma wplywu; a autor,
        # do ktorego piszemy, moze byc w zupelnie innej strefie. Rozszerzenie
        # reguly na komentarze bylo wiec siegnieciem poza jej wlasne
        # uzasadnienie.
        #
        # Koszt byl policzalny: 17:00 UTC to 13:00 ET, wiec ten przebieg
        # wyciszal sie CODZIENNIE. 31 sierpnia znalazl dziewiec celow wartych
        # komentarza i nie wystawil zadnego.
        na_teraz["notki"] = 0
        print("   (komentarze IDA — okno dotyczy naszych tresci, nie cudzych"
              " watkow)", flush=True)

    def blok(nazwa: str, robota) -> None:
        try:
            robota()
        except PRZERYWAJA as exc:
            # DZIEWIEC BLOKOW, JEDNO KONTO. Ta oslona ma izolowac awarie
            # JEDNEGO bloku od osmiu pozostalych — i to jest sluszne przy
            # padnietej przegladarce albo zlym JSON-ie. Przy wyczerpanym
            # budzecie i przy `KILL_SWITCH=true` izolowac nie ma czego: kazdy
            # nastepny platny blok wywroci sie na tym samym bledzie, a
            # `dzien()` mimo to dochodzil do konca i `main` zamykal przebieg
            # jako DONE.
            #
            # DLACZEGO TO NIE JEST TYLKO KOSMETYKA. `ile_przebiegow_zostalo`
            # liczy przebiegi `stage='dzien' AND status='DONE'` i odejmuje je
            # od `PRZEBIEGOW_DZIENNIE`. Przebieg, w ktorym nie poszlo NIC,
            # zjadal wiec jedno z trzech miejsc w dniu i wygladal w bazie jak
            # dzien odrobiony — zapis, ktory potem uchodzi za pomiar.
            #
            # `main` ma nad tym `except BaseException` (patrz `--dzien`), ktore
            # zamyka przebieg jako FAILED z nazwa wyjatku w notatce i podnosi
            # go dalej — czyli dokladnie ta sciezka, ktora `alarm.py` czyta.
            print(f"  [{nazwa}] PRZERWANE: {type(exc).__name__}: {exc}"[:200],
                  flush=True)
            print("  (to nie jest awaria bloku, tylko stan konta — konczę "
                  "dzień zamiast dobijać się do wyczerpanego budżetu)",
                  flush=True)
            raise
        except Exception as exc:
            print(f"  [{nazwa}] blok padł: {type(exc).__name__}: {exc}"[:160],
                  flush=True)
            traceback.print_exc()

    # --- 1. odpowiedzi pod własnymi treściami: pierwsze i bez limitu ----------
    def odpowiedzi() -> None:
        # Pod notkami I pod artykułami. Kanał profilu pokazuje tylko notki, więc
        # bez drugiego pytania czytelnik mógłby zadać pytanie pod tekstem
        # i nie doczekać się odpowiedzi.
        # Trzy zrodla, bo rozmowa toczy sie w trzech miejscach. Trzeciego —
        # odpowiedzi na NASZE komentarze u obcych — agent nie widzial wcale
        # i takiej odpowiedzi nie podjalby nigdy, nie „pozniej".
        # Najpierw dopisujemy, co wynikło z tego, co juz zrobilismy — bez tego
        # dziennik mowi tylko, co wystawilismy, a nie czy ktokolwiek zauwazyl.
        browser.dopisz_skutki()
        # A TERAZ ILE TO KOSZTOWALO I CO PRZYNIOSLO. `dopisz_skutki` mowi, ze
        # ktos zareagowal; statystyki mowia, ILU LUDZI W OGOLE ZOBACZYLO wpis i
        # ilu z nich z niego zostalo — subskrybenci i obserwujacy przypisani do
        # KONKRETNEJ notki. Bez tego nie da sie odroznic notki, ktora nikogo nie
        # obeszla, od notki, ktorej nikt nie zobaczyl, a to sa dwie zupelnie
        # rozne wady i leczy sie je czym innym.
        #
        # Wolamy TU, bo i tak otwieramy przegladarke na skutki, a statystyki
        # odswiezaja sie raz na godzine — czesciej i tak nie ma po co.
        try:
            browser.statystyki_pozycji()
        except Exception as exc:
            # Pomiar NIGDY nie zabija przebiegu. Wpis, ktorego nie zmierzylismy,
            # kosztuje nas wiedze; przebieg, ktory sie wywalil na pomiarze,
            # kosztuje caly dzien publikacji.
            print("  (statystyk nie zebralem: %s)" % type(exc).__name__, flush=True)
        czekaja = (browser.nieodpowiedziane()
                   + browser.komentarze_pod_artykulami()
                   + browser.odpowiedzi_na_nasze_komentarze())
        if not czekaja:
            return
        # PYTANIA CZYTELNIKOW DO PULI TEMATOW. Zbieramy tutaj, bo tutaj i tak
        # trzymamy w reku wszystko, co do nas przyszlo — a w przebiegu artykulu
        # kazde dodatkowe otwarcie sesji to koszt i ryzyko. Pytanie, ktore ktos
        # zadal, a na ktore nikt nie odpowiedzial, jest najlepszym zrodlem
        # tematow, jakie ma kazda publikacja; dotad wyrzucalismy je co dzien.
        try:
            stages.zbierz_pytania(czekaja)
        except Exception as exc:
            print(f"  (nie zebralem pytan: {type(exc).__name__})", flush=True)
        # Przy dwóch odpowiada się obu. Przy dwustu odpowiedź pod każdym wygląda
        # jak maszyna, więc powyżej progu agent wybiera — z pierwszeństwem dla
        # niezgody, bo nieodpowiedziany zarzut zostaje ostatnim słowem.
        czekaja = stages.wybierz_do_odpowiedzi(conn, run_id, czekaja)
        for c in czekaja:
            if not zostal_czas("odpowiedzi"):
                return
            out = stages.reply_to(
                conn, run_id,
                {"under": c.get("kontekst") or "our own note",
                 "author": c["autor"], "text": c["tekst"]},
                {"our_note": c["pod_czym"]})
            kandydaci = [k for k in out["candidates"] if k.get("reply")]
            if not kandydaci:
                continue
            tekst = kandydaci[0]["reply"]
            if wyslij:
                # Pod artykulem odpowiada sie inaczej niz pod notka — inny
                # edytor i inny adres. Na razie obslugujemy notki; komentarze
                # pod artykulami trafiaja do logu, zeby nie ginely.
                # Dwa różne mechanizmy, bo Substack ma je różne: pod notką wątek
                # jest płaski i odpowiada się w polu pod całą notką, pod
                # artykułem każdy komentarz ma własny przycisk odpowiedzi —
                # i tylko wtedy rozmówca dostaje powiadomienie.
                if not rytm("odpowiedz", "odpowiedzi", rytm_stanu):
                    return
                if c.get("gdzie") == "artykul":
                    wynik = browser.wystaw_odpowiedz_pod_artykulem(
                        c.get("url") or "", c.get("autor") or "", tekst,
                        wyslij=True)
                else:
                    wynik = browser.wystaw_odpowiedz(c["pod_id"], tekst,
                                                     wyslij=True)
                # Rytm odmierza sie NIEZALEZNIE od wyniku: przegladarka byla
                # otwarta, watek wczytany, tekst wpisany.
                rytm_stanu["odpowiedz"] = True
                # DOMKNIECIE POPRAWKI Z 1 WRZESNIA. Bloki `komentarze()`
                # i `dyskusje()` dostaly ten warunek, a ten — dwa bloki wyzej
                # i z ta sama wada — nie. Wynik obu funkcji byl tu IGNOROWANY,
                # wiec `zrobione["odpowiedzi"]` roslo takze po odpowiedzi,
                # ktorej Substack nie pokazuje. To ta sama rozbieznosc miedzy
                # podsumowaniem przebiegu a pomiarem z dziennika, dla ktorej
                # cala ta poprawka powstala: `wyslane` ustawia
                # `potwierdz_odpowiedz`/`potwierdz_komentarz`, czyli pytanie do
                # Substacka, i to samo `wyslane` decyduje o polu `udane`
                # w dzienniku. Mierzone 30 sierpnia: 7 nieudanych odpowiedzi
                # na 47 prob — 15 procent zawyzenia tego licznika.
                #
                # POMINIECIE TEZ NIE LICZY SIE DO DNIA, tak jak przy
                # komentarzu: `wystaw_odpowiedz` oddaje wtedy `wyslane=True`,
                # choc nic nie wyszlo, a `potwierdz_odpowiedz` moze tak
                # odpowiedziec takze przy awarii odczytu.
                if wynik.get("pominiete") or not wynik.get("wyslane"):
                    continue
            zrobione["odpowiedzi"] += 1

    # --- 2. notki: pięć dziennie, każda z innego faktu ------------------------
    def notki() -> None:
        if not na_teraz["notki"]:
            print("  dzienny przydzial notek juz wyczerpany", flush=True)
            return
        # Losowa zwloka PRZED pierwsza notka. Bez niej pierwsza notka
        # wychodzila zawsze kilka minut po starcie zegara, wiec piec razy
        # dziennie o tej samej porze co do kwadransa. Godziny zostaja te,
        # ktore wybralismy; przewidywalne przestaja byc minuty.
        if wyslij:
            import random as _r
            ile = _r.uniform(*config.ZWLOKA_PRZED_NOTKAMI)
            # NAPRAWA SIOSTRZANA DO dfc1e95a. Tamta zamknela sen MIEDZY notkami
            # (rytm() pyta zegar przed kazda przerwa) — ten sen, PRZED PIERWSZA
            # notka, mial dokladnie ta sama dziure i zabil jedyna zaplanowana
            # notke przebiegu z 19.08: proces zginal 14,5 min w 34-minutowa
            # zwloke. Zwloka jest ozdobna; notki nie sa. Gdy oba naraz sie
            # nie miesca, zwloke pomijamy i piszemy od razu.
            #
            # Stalo tu „chowa, ze przebiegi startuja o stalych minutach" — a to
            # nieprawda: `systemd/nia-agent.timer` ma `RandomizedDelaySec=1500`,
            # wiec kazdy z pieciu startow jest juz rozmyty po 25-minutowym oknie,
            # ZANIM kod dojdzie do tej zwloki. Zwloka odsuwa PIERWSZA NOTKE od
            # startu przebiegu, a nie start przebiegu od zegara.
            if zostal_czas("zwloke przed notkami", ile):
                print(f"  (zwloka {ile / 60:.0f} min przed pierwsza notka)",
                      flush=True)
                time.sleep(ile)
        for n in stages.notki_dnia(conn, run_id, ile=na_teraz["notki"],
                                   od=juz.get("notki", 0)):
            if not zostal_czas("notki"):
                return
            gotowe = [k for k in n["candidates"]
                      if k.get("safe_to_post") and k.get("length_ok")]
            if not gotowe:
                # Notka promujaca nie ma wlasnych faktow — streszcza artykul.
                # Gdy odpadla na sprawdzeniu, zakwestionowany jest ARTYKUL, i
                # trzeba to zapamietac: inaczej jutrzejszy przebieg napisze o
                # tym samym inaczej i pojdzie po nowe losowanie. Dokladnie to
                # sie stalo 25/26 sierpnia — szczegoly w `zakwestionuj_promocje`.
                if n.get("promocja_url"):
                    powod = ""
                    for k in n["candidates"]:
                        powod = str((k.get("weryfikacja") or {}).get("verdict") or "")
                        if powod:
                            break
                    stages.zakwestionuj_promocje(n["promocja_url"], powod)
                # FAKT WRACA DO PULI, BO NOTKA NIE WYSZLA.
                #
                # `wez_kandydatow` znaczy jako `uzyty` wszystko, co wyda — bo
                # przy notkach wydane naprawde ida do pisania. Ale notka odpada
                # jeszcze TUTAJ, na zaporze albo na dlugosci, i wtedy oplacony
                # fakt przepadal: w indeksie `uzyty`, a w swiat nie poszedl nic.
                #
                # `notki_dnia` oddaje juz NIEUZYTY zapas (`zwroc_kandydatow`
                # przy koncu funkcji); to jest druga polowa tej samej sprawy —
                # fakt ZDJETY dla konkretnej notki, ktorej potem nie ma.
                #
                # Zasada „wolimy stracic niz wystawic dwa razy" zostaje
                # nietknieta: duplikat blokuja `zuzyte_fakty.json` (dopisywany
                # dopiero po potwierdzonej publikacji) i pamiec notek.
                if n.get("fakt"):
                    stages.zwroc_kandydatow([{"fact": n["fakt"]}])
                continue
            if wyslij:
                if not rytm("notka", "notki", rytm_stanu):
                    return
                wynik = browser.wystaw_notke(gotowe[0]["note"].strip(), wyslij=True,
                                             typ=n.get("type", ""),
                                             forma=n.get("forma", ""),
                                             # KTORY PISARZ — do dziennika, bo
                                             # tam stoja wyniki. Bez tego pola
                                             # koszt obu modeli znamy z `calls`,
                                             # a SKUTKU nie porownamy nigdy.
                                             model=gotowe[0].get("model", ""))
                # Fakt odhaczamy DOPIERO po potwierdzonej publikacji. Wczesniej
                # znikal juz przy znalezieniu, wiec przepadal takze wtedy, gdy
                # notka nie poszla albo gdy przebieg byl tylko sprawdzeniem.
                if wynik.get("wyslane") and n.get("fakt"):
                    stages.zapisz_zuzyte([n["fakt"]])
                    # OBIE KSIEGOWOSCI, NIE JEDNA. `zapisz_zuzyte` pisze do
                    # `zuzyte_fakty.json`, ktory czyta wylacznie SZUKANIE.
                    # Sciezki indeksowe patrza na `status`, a ten nadaje tylko
                    # `wez_kandydatow` — wiec fakt wziety prosto ze swiezego
                    # szukania zostawal w indeksie jako `nowy` i mogl wyjsc
                    # nastepnego dnia drugi raz.
                    stages.oznacz_uzyty(n["fakt"])
                # Dzien promocji artykulu tez odhaczamy dopiero po publikacji —
                # inaczej artykul dostawal mniej niz piec notek promujacych,
                # a nikt by tego nie zauwazyl.
                if wynik.get("wyslane") and n.get("promocja_url"):
                    # Tresc idzie razem z odhaczeniem, zeby jutrzejsza notka
                    # promujaca wiedziala, czego juz nie powtarzac.
                    stages.odhacz_promocje(
                        n["promocja_url"],
                        (gotowe[0].get("note") or "").strip())
                rytm_stanu["notka"] = True
            zrobione["notki"] += 1

    # --- 3. komentarze u innych ----------------------------------------------
    # KANAL NA CALYM BLOKU, NIE NA JEDNYM WYWOLANIU. Znacznik siedzial wczesniej
    # wokol samego `comment_on`, a `wybierz_cele` — ta sama robota, ten sam
    # komentarz, 0,5326 USD tygodnia — zostawala poza nim. `wybierz_cele`
    # i `zweryfikuj` obsluguja OBA rodzaje komentarzy, wiec dekoratora przy
    # sobie miec nie moga: tylko ten blok wie, ze chodzi o artykuly.
    @stages._na_kanal("komentarz@artykul")
    def komentarze() -> None:
        # NOWE KONTA NAJPIERW. Kanal czytelnika pokazuje wylacznie to, co juz
        # znamy — jedenascie publikacji, ktore same z siebie nikogo nowego nie
        # przyprowadza. Wyszukiwarka Substacka oddaje ludzi spoza kregu, i to
        # z zywymi dyskusjami. Kanal zostaje jako uzupelnienie, bo tam sa nasi
        # dotychczasowi rozmowcy.
        # Tylko ARTYKULY. Notki trafialy tu razem z postami i szly sciezka
        # artykulow — a notka nie istnieje pod adresem artykulow, wiec
        # potwierdzenie zawsze padalo. Notki maja wlasny blok nizej.
        pula = [x for x in kanal.szukaj_nowych() + kanal.posty_z_kanalu()
                if x.get("rodzaj") != "notka"]
        widziane, unikalne = set(), []
        for x in pula:
            if x.get("url") and x["url"] not in widziane:
                widziane.add(x["url"])
                unikalne.append(x)

        # PLATNE PUBLIKACJE ODSIEWAMY PRZED OCENA, NIE PO NIEJ.
        #
        # Zmierzone w dzienniku z siedmiu dni: CZTERDZIESCI DWA razy uslyszeliśmy
        # „komentarze tylko dla placacych" — za kazdym razem PO tym, jak model
        # ocenil cel (i wzial za to pieniadze), i po uruchomieniu przegladarki,
        # zeby o to zapytac. W jednym przebiegu z czterech wybranych celow TRZY
        # okazaly sie platne i wyszedl JEDEN komentarz z zaplanowanych trzech.
        #
        # To jest ustawienie publikacji, nie awaria, wiec pamietamy je po
        # pierwszej obserwacji. Udany komentarz kasuje host z listy, wiec
        # zmiana ustawien u wydawcy odblokowuje go sama.
        platne = browser.hosty_tylko_dla_placacych()
        if platne:
            from urllib.parse import urlparse as _urlparse
            przed = len(unikalne)
            unikalne = [x for x in unikalne
                        if _urlparse(x.get("url", "")).netloc.lower()
                        .removeprefix("www.") not in platne]
            if przed != len(unikalne):
                print("  [cele] odsiane platne publikacje: %d z %d"
                      % (przed - len(unikalne), przed), flush=True)

        # I TAK SAMO HOSTY, U KTORYCH KOMENTARZ DWA RAZY NIE WSZEDL.
        #
        # Ta sama wada co przy platnych, o kilkanascie linii dalej w tym samym
        # bloku. `hosty_gdzie_komentarz_nie_wchodzi` bylo pytane dopiero
        # wewnatrz `mozna_komentowac`, czyli PO `wybierz_cele` — a wiec model
        # placil za ocene celow na hostach, o ktorych juz z dziennika wiemy, ze
        # nic tam nie wchodzi. Odpowiedz jest darmowa: czyta plik z dysku, nie
        # rusza sieci, wiec nie ma powodu, zeby stala za platna ocena.
        #
        # ZMIERZONE 30 sierpnia 2026: 11 nieudanych komentarzy z 92 prob, a
        # adresy sie powtarzaly — publikacja-c.example, publikacja-d.example,
        # wlasnadomena.example wracaly do oceny w kazdym przebiegu.
        #
        # HOST POROWNUJEMY DOKLADNIE TAK JAK ZAPORA: samo `netloc.lower()`, bez
        # zdejmowania `www.`, bo `hosty_gdzie_komentarz_nie_wchodzi` buduje
        # klucze z adresow w dzienniku rowniez bez zdejmowania. Inna
        # normalizacja odsialaby tutaj co innego, niz odrzuci `mozna_komentowac`
        # — a wtedy przedplata i zapora rozjechalyby sie po cichu.
        #
        # WYPISUJEMY NAZWY, NIE SAMA LICZBE. To sito wycina cel PRZED ocena,
        # wiec wyjasniajacy komunikat z `mozna_komentowac` („dwa razy nic tam
        # nie weszlo") nigdy sie nie pokaze — sito jest jedynym miejscem, gdzie
        # widac, KTORY host wypadl. Bez nazw blednie zamkniety host wygladalby
        # w logu jak brak kandydatow.
        martwe = browser.hosty_gdzie_komentarz_nie_wchodzi()
        if martwe:
            from urllib.parse import urlparse as _up_m
            przed = len(unikalne)
            wyciete = sorted({_up_m(x.get("url", "")).netloc.lower()
                              for x in unikalne
                              if _up_m(x.get("url", "")).netloc.lower() in martwe})
            unikalne = [x for x in unikalne
                        if _up_m(x.get("url", "")).netloc.lower()
                        not in martwe]
            if przed != len(unikalne):
                print("  [cele] odsiane hosty bez wejscia komentarza: %d z %d"
                      " (%s)" % (przed - len(unikalne), przed,
                                 ", ".join(wyciete[:6])), flush=True)

        cele = stages.wybierz_cele(conn, run_id, unikalne)

        # SZUKAJ, AZ ZNAJDZIESZ — DECYZJA WLASCICIELA 31 SIERPNIA.
        #
        # Dotad bylo: jedna pula, jedna ocena, koniec. Jesli z trzynastu
        # kandydatow przechodzil jeden, wychodzil JEDEN komentarz i przebieg
        # szedl dalej — mimo ze plan mowil pietnascie. Zmierzone tego dnia:
        #     [cele] warte komentarza: 0/15, potem 3/17
        # czyli dwie proby na przebieg i trzy komentarze z pietnastu.
        #
        # Teraz dobieramy kolejne partie, dopoki nie mamy tylu celow, ile
        # przewiduje plan na TEN przebieg. Kazda runda losuje inne hasla
        # (`szukaj_nowych` losuje z puli), wiec kolejna partia to inne konta,
        # nie te same odsiane drugi raz.
        #
        # TRZY OGRANICZNIKI, BO „AZ ZNAJDZIE" BEZ NICH ZNACZY „W NIESKONCZONOSC":
        #   - `RUNDY_SZUKANIA_CELOW` prob (kazda to jedno platne wywolanie oceny),
        #   - czas przebiegu, ten sam co wszedzie,
        #   - runda, ktora nie przyniosla ANI JEDNEGO nowego adresu, konczy
        #     szukanie: wyszukiwarka oddaje to samo, wiec kolejna nie pomoze.
        #
        # ODSTEPY SIE NIE ZMIENIAJA. Wiecej celow to nie szybsze pisanie —
        # `rytm()` nadal trzyma 5-15 minut miedzy komentarzami. Wlasciciel byl
        # jednoznaczny: „nie chodzi o LICZBE, tylko o ODSTEPY".
        rundy = 1
        while (len(cele) < na_teraz["komentarze"]
               and rundy < config.RUNDY_SZUKANIA_CELOW
               and zostal_czas("komentarze")):
            rundy += 1
            print("  [cele] mam %d z %d — runda %d szukania"
                  % (len(cele), na_teraz["komentarze"], rundy), flush=True)
            dobrane = [x for x in kanal.szukaj_nowych()
                       if x.get("rodzaj") != "notka" and x.get("url")
                       and x["url"] not in widziane]
            if not dobrane:
                print("  [cele] wyszukiwarka nie oddaje juz nic nowego"
                      " — koncze szukanie", flush=True)
                break
            for x in dobrane:
                widziane.add(x["url"])
            if platne:
                from urllib.parse import urlparse as _up2
                dobrane = [x for x in dobrane
                           if _up2(x["url"]).netloc.lower().removeprefix("www.")
                           not in platne]
            # Kolejne partie ida prosto do platnego `wybierz_cele`, wiec musza
            # przejsc PRZEZ TE SAME dwa sita co pula pierwsza. Bez tego runda
            # druga i dalsze kupowaly ocene dokladnie tych hostow, ktore runda
            # pierwsza odsiala za darmo.
            if martwe:
                from urllib.parse import urlparse as _up3
                dobrane = [x for x in dobrane
                           if _up3(x["url"]).netloc.lower() not in martwe]
            if not dobrane:
                continue
            cele = cele + stages.wybierz_cele(conn, run_id, dobrane)
        if rundy > 1:
            print("  [cele] po %d rundach: %d celow"
                  % (rundy, len(cele)), flush=True)

        for cel in cele[: na_teraz["komentarze"]]:
            if not zostal_czas("komentarze"):
                return
            # Pytamy o prawo do komentowania PRZED pisaniem. Inaczej caly koszt
            # — strona, trzy warianty, sprawdzenie faktow — szedl na tekst,
            # ktorego i tak nie da sie wystawic, a miejsce z dziennego limitu
            # i tak przepadalo.
            if not browser.mozna_komentowac(cel["url"]):
                continue
            strony = browser.read_pages([cel["url"]])
            if not strony or not strony[0].get("text"):
                continue
            # `co_dodamy` PRZEZ GRANICE, NA KTOREJ GINELO. `wybierz_cele`
            # zapisuje przy kazdym przyjetym celu jedna konkretna rzecz, ktora
            # warto pod tym wpisem dodac, `comment_on` to czyta — a tutaj szedl
            # sam `strony[0]`, wiec model nigdy tej notatki nie widzial.
            # Zmierzone atrapa promptu 2 wrzesnia 2026: ze slownikiem z polem
            # notatka jest w 3 promptach na 3, bez pola w 0 na 3. Platne:
            # 68 wywolan `cele` = 0,6056 USD od 25 sierpnia za pole wyrzucane
            # do kosza, przy prompcie, ktory czyni je warunkiem przyjecia celu.
            # (Kanal ustawia dekorator nad `komentarze` — obejmuje takze
            # `wybierz_cele` wyzej i `zweryfikuj` w srodku `comment_on`.)
            out = stages.comment_on(
                conn, run_id,
                {**strony[0], "co_dodamy": cel.get("co_dodamy", "")})
            dobre = [k for k in out["candidates"]
                     if k.get("comment") and k.get("safe_to_post")]
            if not dobre:
                # CEL PRZEPADAL PO CICHU. „Wszyscy zamilkli" i „wszystkich
                # zdjela zapora" wygladaly stad identycznie — czyli dwa zupelnie
                # rozne problemy nie do odroznienia. Zmierzone na dzienniku
                # systemowym za 18 dni: 8 celow na 196 wywolan przepadlo przez
                # cisze wszystkich kandydatow, okolo pol celu dziennie.
                cisze = sum(1 for k in out["candidates"] if not k.get("comment"))
                print("  CEL BEZ KOMENTARZA — %d z %d milczalo, %d zdjela zapora"
                      % (cisze, len(out["candidates"]),
                         len(out["candidates"]) - cisze), flush=True)
                continue
            if wyslij:
                if not rytm("komentarz", "komentarze", rytm_stanu):
                    return
                wynik = browser.wystaw_komentarz(
                    cel["url"], dobre[0]["comment"], wyslij=True,
                    kontekst={**opis_celu(cel),
                              "otwarcie": (out.get("otwarcie") or "")[:60],
                              "postawa": out.get("postawa") or ""})
                # Rytm odmierza sie NIEZALEZNIE od wyniku: przegladarka byla
                # otwarta, strona wczytana, tekst wpisany — nastepne dzialanie
                # ma czekac tyle samo, co po komentarzu udanym.
                rytm_stanu["komentarz"] = True
                # DALEJ IDZIEMY TYLKO PO POTWIERDZENIU. `wystaw_komentarz`
                # oddaje slownik, w ktorym `wyslane` to jedyny dowod: ustawia
                # je `potwierdz_komentarz`, czyli pytanie do Substacka, a nie
                # samo klikniecie. Ten wynik byl tu IGNOROWANY, wiec kazda
                # z trzech linii nizej wykonywala sie takze wtedy, gdy
                # komentarz nie wszedl — a nie wchodzil w 11 probach na 92
                # (pomiar z 30 sierpnia 2026). Ceny tego bledu byly trzy:
                #   - `zapamietaj_komentarz` palilo publikacje na
                #     ODSTEP_DNI_NA_PUBLIKACJE = 4 dni za komentarz, ktorego
                #     tam nie ma,
                #   - `zapomnij_platny_host` kasowalo host z listy platnych
                #     wbrew wlasnemu opisowi („UDANY komentarz kasuje host"),
                #     wiec ta sama platna publikacja wracala do oceny,
                #   - licznik rosl mimo braku komentarza — a to na nim stoi
                #     alarm „agent robi mniej, niz deklaruje".
                # To samo `wyslane` decyduje o polu `udane` w dzienniku
                # (`dopisz_wynik`), wiec licznik przebiegu mowi teraz to samo,
                # co pomiar z dziennika.
                #
                # POMINIECIE NIE LICZY SIE DO DNIA — decyzja, nie przeoczenie.
                # `wystaw_komentarz` oddaje przy pominieciu `{"wyslane": True,
                # "pominiete": True}`, wiec sam warunek na `wyslane` je
                # przepuszczal: licznik przebiegu rosl o 1, `zapamietaj_
                # komentarz` i `zapomnij_platny_host` odpalaly, a dziennik
                # dostawal ZERO wpisow (`wystaw_komentarz` swiadomie pominiec
                # nie zapisuje). Czyli dokladnie ta rozbieznosc podsumowania
                # z pomiarem, ktora ta poprawka miala zamknac.
                #
                # DLACZEGO NIE LICZYMY. Dzienny przydzial komentarzy liczy sie
                # z dzialan UDANYCH, wiec policzone pominiecie zjada slot za
                # cos, co sie nie wydarzylo. Gorzej: `juz_sie_odezwalismy`
                # oddaje True takze wtedy, gdy nie odczytalo naszego id („nie
                # wiem, czyli nie ryzykuje") — awaria `/public_profile`
                # wystarczy. Przy liczeniu pominiec jedna taka awaria wypalilaby
                # caly dzienny budzet komentarzy bez ani jednego komentarza.
                # Nie liczac ich, przebieg po prostu probuje dalej z nastepnym
                # celem — a to jest zachowanie, ktorego chcemy.
                #
                # `zapamietaj_komentarz` i `zapomnij_platny_host` tym bardziej
                # nie moga odpalic: pierwsze paliloby publikacje na
                # ODSTEP_DNI_NA_PUBLIKACJE = 4 dni, drugie zdejmowaloby host
                # z listy platnych — jedno i drugie na podstawie komentarza,
                # ktorego w tym przebiegu nie napisalismy.
                if wynik.get("pominiete"):
                    print("  (pominiete — nie licze do normy dnia)", flush=True)
                    continue
                if not wynik.get("wyslane"):
                    continue
                # Zapamietujemy U KOGO, zeby nie wracac tam za kilka dni.
                kanal.zapamietaj_komentarz(cel)
                # I zdejmujemy host z listy platnych, jesli tam byl: skoro
                # komentarz wszedl, ustawienia sie zmienily.
                from urllib.parse import urlparse as _up
                browser.zapomnij_platny_host(
                    _up(cel.get("url", "")).netloc)
            zrobione["komentarze"] += 1

    # --- 3b. dyskusje pod cudzymi notkami -------------------------------------
    # Ten sam powod, co przy `komentarze` — z drugim kanalem.
    @stages._na_kanal("komentarz@notka")
    def dyskusje() -> None:
        """Wejscie w rozmowe pod cudza notka.

        Dla swiezego konta to najwazniejsze miejsce: pod notkami toczy sie
        rozmowa, a kanal promuje watki, ktore zyja. Komentarz pod artykulem
        czyta kilka osob; sensowna uwaga pod zywa notka trafia do calego watku.
        """
        if not na_teraz["komentarze"]:
            return
        # Dwa zrodla, bo jedno bylo glodowe: przeglad pokazal DWA cele na
        # przebieg, oba z zerem odpowiedzi. Wyszukiwarka oddaje notki spoza
        # naszego kregu, czyli dokladnie tych ludzi, o ktorych nam chodzi.
        notki = kanal.notki_z_kanalu() + [
            {"id": x.get("id"), "tekst": x.get("opis") or x.get("tytul") or "",
             "autor": x.get("pub") or "", "reakcje": x.get("reakcje") or 0,
             "odpowiedzi": x.get("komentarze") or 0, "url": x.get("url") or "",
             "data": x.get("data") or "", "skad": x.get("skad") or ""}
            for x in kanal.szukaj_nowych() if x.get("rodzaj") == "notka"]
        notki = [n for n in notki if n.get("id")]
        if not notki:
            return
        cele = stages.wybierz_cele(
            conn, run_id,
            [{"tytul": n["tekst"][:120], "opis": n["tekst"], "pub": n["autor"],
              "komentarze": n["odpowiedzi"], "reakcje": n["reakcje"],
              "url": n["url"], "id": n["id"], "data": n.get("data", ""),
              "skad": n.get("skad", "kanal")} for n in notki])
        # SUFIT TEGO BLOKU JEST DODATKOWY, NIE WSPOLNY — i to jest swiadome.
        # Blok pod artykulami wzial juz do `na_teraz["komentarze"]`, ten bierze
        # jeszcze polowe tego samego przydzialu, wiec jeden przebieg moze
        # wystawic do N + N//2. Odjecie `zrobione["komentarze"]` ZMNIEJSZYLOBY
        # liczbe publikacji, a doktryna mowi odwrotnie.
        #
        # Zmierzone na 51 przebiegach (18.08-02.09.2026): przydzial jest
        # realizowany w 38 procentach (srednio 1,98 wystawione przy 5,27
        # przydzielonych), sufit ruszyl DWA razy — 22.08 (4 -> 5) i 01.09
        # (4 -> 6, dokladnie N + N//2) — i ani jedna doba z szesnastu nie
        # przekroczyla przez to budzetu dobowego. Powod jest strukturalny, nie
        # szczesliwy: `zostalo` liczy sie od nowa z dziennika na poczatku
        # KAZDEGO przebiegu, wiec nadmiar jednego zabiera z puli nastepnym.
        for cel in cele[: max(1, na_teraz["komentarze"] // 2)]:
            if not zostal_czas("dyskusje"):
                return
            # Drugie miejsce, w ktorym ginelo `co_dodamy` — patrz komentarz przy
            # bloku komentarzy pod artykulami. Tu slownik jest sklecony od zera,
            # wiec pole trzeba dopisac jawnie.
            # (Kanal ustawia dekorator nad `dyskusje` — patrz blok wyzej.)
            out = stages.comment_on(
                conn, run_id,
                {"title": cel.get("tytul", ""), "text": cel.get("opis", ""),
                 "author": cel.get("pub", ""), "url": cel.get("url", ""),
                 "co_dodamy": cel.get("co_dodamy", "")})
            dobre = [k for k in out["candidates"]
                     if k.get("comment") and k.get("safe_to_post")]
            if not dobre:
                # To samo, co w bloku komentarzy pod artykulami — patrz tam.
                cisze = sum(1 for k in out["candidates"] if not k.get("comment"))
                print("  CEL BEZ KOMENTARZA — %d z %d milczalo, %d zdjela zapora"
                      % (cisze, len(out["candidates"]),
                         len(out["candidates"]) - cisze), flush=True)
                continue
            if wyslij:
                if not rytm("komentarz", "dyskusje", rytm_stanu):
                    return
                # `rodzaj="komentarz"`, bo to jest komentarz — pod cudza
                # notka zamiast pod cudzym artykulem. Liczy sie do tej samej
                # normy, z ktorej bierzemy na to miejsce kilka linii wyzej.
                # OTWARCIE I POSTAWA JADA TAKZE STAD, tak jak w bloku wyzej.
                # Dotad szedl sam `opis_celu`, wiec przydzielona postawa i
                # przydzielone otwarcie nie trafialy do dziennika — a wg
                # pomiaru z `browser.py` (siedem dni: 29 wpisow `odpowiedz`,
                # z czego 23 to komentarze pod cudzymi notkami) to WLASNIE
                # ten blok daje wiekszosc wypowiedzi. Rozklad postaw i
                # roznorodnosc otwarc byly wiec mierzone na jednej szostej
                # materialu.
                wynik = browser.wystaw_odpowiedz(
                    cel["id"], dobre[0]["comment"], wyslij=True,
                    kontekst={**opis_celu(cel),
                              "otwarcie": (out.get("otwarcie") or "")[:60],
                              "postawa": out.get("postawa") or ""},
                    rodzaj="komentarz")
                rytm_stanu["komentarz"] = True
                # Jak przy komentarzu pod artykulem: `wyslane` ustawia
                # `potwierdz_odpowiedz`, czyli sprawdzenie w watku, a nie samo
                # klikniecie. Wynik byl tu ignorowany, wiec licznik rosl takze
                # po 7 nieudanych odpowiedziach z 47 (pomiar z 30 sierpnia).
                # I tak samo pominiecie: `wystaw_odpowiedz` oddaje wtedy
                # `wyslane=True` bez zadnego wpisu w dzienniku — patrz dluzsze
                # uzasadnienie w bloku `komentarze()`.
                if wynik.get("pominiete") or not wynik.get("wyslane"):
                    continue
            zrobione["komentarze"] += 1

    # --- 3c. obserwowanie nowych: to, co poszerza krąg ------------------------
    def obserwuj() -> None:
        """Obserwuje autorów, których teksty faktycznie czytaliśmy.

        Bez tego agent kręciłby się w kółko po tych samych jedenastu
        publikacjach: kanał czytelnika pokazuje to, co obserwujemy, a my nie
        obserwowaliśmy nikogo. Każda nowa obserwacja poszerza pulę ludzi, do
        których w ogóle możemy się odezwać.

        Obserwujemy TYLKO tych, u których naprawdę byliśmy — nie z listy
        podpowiedzi. Obserwowanie kogoś, kogo się nie czytało, to zbieranie
        nazwisk, a nie budowanie kręgu.

        ODWIESZONE 2026-09-01. Stalo tu „WYCOFANE 2026-08-23. Substack zdjal
        przycisk «Follow» z profili" — i to zdanie nie bylo prawda.

        POMIAR Z 23 SIERPNIA BYL DOBRY, WNIOSEK ZLY. Szesc profili naprawde
        nie mialo slowa „Follow" w HTML, bo przycisk siedzi w menu pod kolkiem
        „..." obok „Subscribe" i „Message", a Substack rysuje to menu DOPIERO
        PO KLIKNIECIU. W HTML zamknietej strony go nie ma i byc nie moze —
        czytanie HTML-a nie moglo rozstrzygnac tego pytania.

        Wniosek pociagnal za soba trzy rzeczy naraz i to one kosztowaly
        dziewiec dni: budzet `follow` zszedl do zera, ten blok przestal cokolwiek
        robic, a `norma.NIEWYKONALNE` wytlumaczylo powstale zero zdaniem
        o zdjetym przycisku. Zero, ktore ma wyjasnienie, przestaje wygladac na
        problem — dlatego nikt nie zapytal ponownie.

        Zmierzone ponownie 1 wrzesnia 2026 na zywej sesji, przez OTWARCIE menu
        (bez klikania czegokolwiek w srodku): na trzech profilach nieobserwowanych
        menu ma pozycje „Follow", na trzech obserwowanych — „Unfollow". Droga
        do przycisku i zmierzone etykiety stoja przy `browser.obserwuj_profil`.

        NIE ZMIENIA SIE ZASADA, KTOREJ TA FUNKCJA BRONI OD PIERWSZEGO DNIA:
        nadal nie tykamy widgetow „kogo obserwowac", bo to lista podpowiedzi.
        Bierzemy wylacznie hosty z naszej historii czytania.

        WYBOR CELU PRZESTAL BYC LOSEM (1 wrzesnia 2026). Historia czytania
        nadal jest jedynym zrodlem, ale nie idzie juz do losowania w calosci:
        `cele_wedlug_pierwszenstwa` odcina hosty, u ktorych ostatni raz
        komentowalismy przed przestawieniem tematu konta (53 z 94 zmierzone
        tego dnia, wszystkie z poprzedniej dziedziny),
        i stawia na poczatku te, ktore juz zareagowaly na nasza tresc.

        DLACZEGO AKURAT TU TO BOLI NAJBARDZIEJ. Obserwacja WYSYLA
        POWIADOMIENIE MAILEM, a nasza lista obserwowanych jest publiczna
        i Substack nie daje jej ukryc (subskrypcje maja ustawienie
        prywatnosci, obserwacje nie). Losowy host sprzed przestawienia konta
        to nie jest neutralne pudlo — to zaproszenie na wlasny profil wyslane
        komus, kto czytal u nas o czym innym, plus publiczny slad.

        PULA JEST ODSIEWANA PRZED LOSOWANIEM (poprawka z 1 wrzesnia 2026).
        Historia komentarzy zawiera takze ludzi, ktorych juz obserwujemy —
        zmierzone: 26 obserwowanych wobec 92 hostow w historii. Losowanie bez
        odsiewu zjadalo na takim trafieniu caly dzienny slot i zapisywalo go
        jako porazke. Szczegoly przy `browser.OBSERWOWANI`.

        Jeszcze wczesniejsza diagnoza tez byla bledna: myslalem, ze bierzemy
        uchwyt PUBLIKACJI zamiast uchwytu CZLOWIEKA. Sprawdzone na zywym API —
        dla wszystkich pieciu hostow z historii oba uchwyty sa identyczne.
        Nie o to chodzilo ani wtedy, ani teraz.

        PULA PRZESTALA BYC SAMA HISTORIA CZYTANIA (1 wrzesnia 2026, wieczor).
        Odkad reakcja na nasza tresc niesie uchwyt, reagujacy jest celem
        WPROST — 62 z 69 takich osob nie ma w historii komentarzy zadnego
        hosta i byly dla tego bloku niewidzialne. Zdanie „bierzemy wylacznie
        hosty z naszej historii czytania" dotyczy nadal LISTY PODPOWIEDZI
        Substacka i tego sie trzymamy; czlowiek, ktory sam do nas napisal albo
        dwa razy polubil nasza notke, nie jest podpowiedzia algorytmu.
        Hamulce, ktore maja z tego nie zrobic automatu odwzajemniajacego, stoja
        przy `ODSTEP_OD_REAKCJI_H`.
        """
        if not na_teraz.get("follow"):
            return
        historia = kanal._historia()
        if not historia:
            return

        # ODSIEW PRZED LOSOWANIEM, A NIE PO NIM — i to jest cala roznica.
        #
        # Do 1 wrzesnia 2026 pula szla do losowania w calosci, a budzet ciety
        # byl przez `kandydaci[:1]`. Trafienie na kogos, kogo juz obserwujemy,
        # konczylo wiec dzien: `obserwuj_profil` slusznie nie klikalo nic,
        # dziennik zapisywal PORAZKE, a slot dnia przepadal. Zmierzone tego
        # dnia na zywym koncie: 26 obserwowanych, 92 hosty w historii, 8 na
        # pewno wspolnych juz po samym mapowaniu nazwy hosta (naprawde wiecej,
        # bo `www.wlasnadomena.example` to `autor1`) — czyli okolo jednego dnia na
        # siedem zjadanego na pustym losowaniu i zapisywanego jako awaria.
        #
        # Pamiec czytamy RAZ na blok: to jeden plik z dysku, a nie zapytanie
        # do Substacka. Zrzut listy robi pomiar, ktory i tak chodzi — patrz
        # `browser.OBSERWOWANI`.
        pamiec = browser.kogo_obserwujemy()
        # KRYTERIUM PRZED LOSEM. Do 1 wrzesnia 2026 pula szla przez `shuffle`
        # bez ZADNEGO kryterium — ani wielkosci, ani tematu, ani jezyka, ani
        # swiezosci. `cele_wedlug_pierwszenstwa` wycina hosty, ktorych ostatni
        # komentarz jest sprzed zmiany tematu konta (53 z 94 zmierzone
        # tego dnia), i stawia na poczatku te, ktore juz zareagowaly na nasza
        # tresc. Los zostaje, ale juz tylko wewnatrz poziomu.
        wszyscy, rachunek = cele_wedlug_pierwszenstwa(historia)
        kandydaci = [h for h in wszyscy
                     if not browser.czy_juz_obserwujemy(h, pamiec)]
        print("  pula: %d hostow w historii, %d odsianych tematycznie"
              " (ostatni komentarz sprzed %s), %d z reakcja na nasza tresc;"
              " reagujacych z uchwytem %d, w puli %d (%d juz nas czyta,"
              " %d ponizej progu, %d mlodszych niz %d h);"
              " %d zostaje po odsianiu obserwowanych"
              % (rachunek["wszystkich"], rachunek["sprzed_przestawienia"],
                 PRZESTAWIENIE_KONTA, rachunek["ze_skutkiem"],
                 rachunek["reagujacy_z_uchwytem"], rachunek["reagujacy"],
                 rachunek["reagujacy_juz_czyta"], rachunek["reagujacy_slabi"],
                 rachunek["reagujacy_swiezy"], rachunek["odstep_h"],
                 len(kandydaci)), flush=True)
        if not kandydaci:
            # PULA WYCZERPANA TO STAN POPRAWNY, NIE AWARIA — ale musi zostawic
            # slad, bo inaczej wraca stary problem w nowym przebraniu: blok bez
            # wpisu wyglada na blok, ktory sie nie odbywa. `obserwacja_pominieta`
            # jest poza `norma.RODZAJE`, wiec nie liczy sie ani do wykonanych,
            # ani do nieudanych — patrz `browser.obserwuj_profil`.
            #
            # NIE WRACAMY DO LOSU Z CALOSCI, i to jest decyzja, nie
            # przeoczenie. Odsiew tematyczny nie jest preferencja, tylko
            # granica: host sprzed przestawienia konta dostaje od nas maila
            # z zaproszeniem na wlasny profil, ktorego nie chcial. Zero
            # z podanym powodem jest uczciwe; zero udajace wynik nie.
            if wyslij:
                browser.zapisz_w_dzienniku(
                    "obserwacja_pominieta", udane=True,
                    powod=(powod_pustej_puli(rachunek)
                           if not wszyscy else
                           # „HOSTOW" JUZ BY KLAMALO. Od 1 wrzesnia 2026 w puli
                           # stoja takze reagujacy, ktorych w historii
                           # komentarzy nie ma wcale — powod ma podac oba
                           # poziomy osobno, inaczej wraca zero bez powodu.
                           "pula wyczerpana: wszystkie %d celow juz"
                           " obserwujemy (%d hostow po odsianiu tematycznym,"
                           " %d reagujacych na nasza tresc)"
                           % (len(wszyscy), rachunek["po_przestawieniu"]
                              - rachunek["zdublowani"],
                              rachunek["reagujacy"])))
            print("  nie ma kogo obserwowac — %s"
                  % ("cala pula tematyczna juz obserwowana" if wszyscy
                     else powod_pustej_puli(rachunek)), flush=True)
            return

        # ZAPAS NA ODPADY. Petla nie chodzi juz po `kandydaci[:budzet]`, bo
        # host, ktorego uchwytu nie ustalilismy, i host, ktory okazal sie juz
        # obserwowany, NIE SA PROBA i nie moga zjadac slotu. Zapas domyka to
        # od gory: bez niego przebieg z pamiecia rozjechana wobec Substacka
        # potrafilby obejsc wszystkie 92 hosty, a kazdy to osobna sesja
        # przegladarki. Cztery, bo zmierzony odsetek juz-obserwowanych w puli
        # to okolo 13 procent, wiec cztery pudla z rzedu to juz nie pech,
        # tylko znak, ze pamiec jest do odswiezenia.
        ZAPAS_NA_ODPADY = 4
        proby = 0
        # DWA RODZAJE POMINIEC, BO ZOSTAWIAJA ROZNY SLAD. Pominiecie z menu
        # zapisuje `obserwuj_profil` (byl na profilu, przeczytal „Unfollow");
        # pominiecie z pamieci nie zapisuje nic, bo nic sie nie wydarzylo —
        # i dlatego tylko ono moze zostawic dzien bez ani jednego wpisu.
        z_pamieci = 0
        zostal_slad = False
        for host in kandydaci[: na_teraz["follow"] + ZAPAS_NA_ODPADY]:
            if proby >= na_teraz["follow"]:
                break
            if not zostal_czas("obserwowanie"):
                break
            # Nie `host.split(".")[0]`: przy wlasnej domenie dawalo to "www"
            # i agent probowal obserwowac konto o tej nazwie.
            uchwyt = browser.uchwyt_publikacji(host)
            # UCHWYT SPRAWDZAMY DRUGI RAZ, JUZ PO ROZWIAZANIU. Dla wlasnej
            # domeny (24 z 92 hostow w puli) nazwa konta wychodzi dopiero
            # z API, wiec odsiew po hoscie nie mial jej jak rozpoznac:
            # `www.wlasnadomena.example` to `autor1`, ktorego obserwujemy od dawna.
            # Zlapane tutaj oszczedza cale wejscie na profil, a zapisana mapa
            # host->uchwyt sprawia, ze jutro odsieje sie juz przed losowaniem.
            if uchwyt and uchwyt in pamiec["uchwyty"]:
                browser.zapamietaj_obserwowanego(uchwyt, host=host)
                z_pamieci += 1
                print(f"  ({host} -> @{uchwyt} juz obserwowany wedlug pamieci"
                      f" — nie wchodze na profil)", flush=True)
                continue
            if not uchwyt:
                # POMINIECIE TEZ JEST WYNIKIEM. Cichy `continue` to dokladnie
                # ten mechanizm, przez ktory obserwacje tygodniami udawaly, ze
                # ich nie ma: blok bez sladu w dzienniku wyglada na blok, ktory
                # sie nie odbywa. Proba byla, wiec ma zostawic powod.
                if wyslij:
                    browser.dopisz_wynik(
                        "obserwacja", {}, komu=host,
                        powod=f"nie ustalilem konta autora dla {host}")
                    zostal_slad = True
                print(f"  (nie ustalilem konta dla {host} — pomijam)", flush=True)
                continue
            if wyslij:
                if not rytm("komentarz", "obserwowanie", rytm_stanu):
                    break
                # OBSERWUJEMY, nie subskrybujemy. To dwie rozne rzeczy i maja
                # osobne widelki: obserwacja nie przysyla nic mailem.
                wynik_obs = browser.obserwuj_profil(uchwyt, wyslij=True)
                rytm_stanu["komentarz"] = True
                # POLE `juz_obserwowany` BYLO PRODUKOWANE I WYRZUCANE: szlo do
                # dziennika i nie czytal go w calym repo nikt. Teraz decyduje
                # o dwoch rzeczach naraz — czy slot dnia zostal zuzyty i czy
                # ten host ma jeszcze kiedykolwiek wrocic do losowania.
                if wynik_obs.get("juz_obserwowany"):
                    browser.zapamietaj_obserwowanego(uchwyt, host=host)
                    zostal_slad = True     # wpis zrobil `obserwuj_profil`
                    print(f"  ({host} -> @{uchwyt} juz obserwowany — nie liczy"
                          f" sie jako proba, biore nastepnego)", flush=True)
                    continue
                if wynik_obs.get("zrobione"):
                    # HOST, NIE SAM UCHWYT. `obserwuj_profil` zapamietal juz
                    # uchwyt, ale tylko tutaj wiadomo, z ktorego adresu on sie
                    # wzial — a pula jest lista adresow.
                    browser.zapamietaj_obserwowanego(uchwyt, host=host)
                proby += 1
                zostal_slad = True
            else:
                print(f"  (obserwowałbym: {uchwyt})", flush=True)
                proby += 1

        # DZIEN, W KTORYM NIE PROBOWALISMY ANI RAZU, MA POWIEDZIEC DLACZEGO.
        # Bez tego wpisu odsiew zalatalby jedna dziure i otworzyl te sama co
        # przedtem: blok chodzi, nie wystawia nic i nie zostawia sladu, wiec
        # z zewnatrz wyglada jak blok, ktorego nie ma.
        #
        # TYLKO WTEDY, GDY NIC INNEGO NIE ZAPISALO. Jedno zdarzenie ma zostawic
        # jeden slad: gdy `obserwuj_profil` juz zapisalo pominiecie, drugi wpis
        # o tym samym dniu tylko rozmydla dziennik. Wyjscia po czasie i po
        # hamulcu rytmu drukuja swoje wlasne powody i nie sa tym przypadkiem.
        if wyslij and proby == 0 and z_pamieci and not zostal_slad:
            browser.zapisz_w_dzienniku(
                "obserwacja_pominieta", udane=True,
                powod="pominietych %d z %d wylosowanych: znamy ich z pamieci"
                      " obserwowanych" % (z_pamieci, len(kandydaci)))

    # --- 3d. subskrypcje: NAJMOCNIEJSZY sygnal, jaki umiemy wyslac ------------
    def subskrybuj() -> None:
        """Subskrybuje publikacje, ktore naprawde czytamy — i pilnuje dubli.

        Budzet `subskrypcje` byl liczony i nigdy nieuzywany — blokiem sterowal
        budzet `follow`, a funkcja i tak klikala „Subscribe". Agent subskrybowal
        wiec w tempie obserwacji: do 44 miesiecznie zamiast 6-12, i kazda z nich
        przysylala poczte do skrzynki wlasciciela.

        NAGLOWEK BLOKU MOWIL „rzadko, bo laduja w skrzynce wlasciciela" i to
        bylo cale uzasadnienie waskosci. Zmierzone 1 wrzesnia 2026: subskrypcje
        maja 11,5 procent konwersji zwrotnej wobec 3,4 procent przy obserwacji,
        czyli blok scisniety naszym kosztem byl tym, ktory dziala najlepiej.
        Widelki poszly w gore — powod i caly rachunek stoja przy
        `config.SUBSKRYPCJE_MIESIECZNIE`.

        ODSIEW DUBLI, ktorego ten blok nie mial wcale. Zmierzone na dzienniku:
        18 prob, 6 w kosz, w tym `publikacja-b` — konto zasubskrybowane
        16 sierpnia, na ktore agent wszedl ponownie 25 sierpnia i zapisal
        porazke „nie ma przycisku subskrypcja", bo przycisk mowil juz
        „Subscribed". Duble ida teraz jak pominiecia obserwacji: osobnym
        rodzajem `subskrypcja_pominieta`, ktory jest poza `norma.RODZAJE`,
        wiec nie liczy sie ani do wykonanych, ani do nieudanych — i nie zjada
        slotu.

        CZEGO ODSIEW CELOWO NIE ROBI: nie odrzuca konta dlatego, ze je
        OBSERWUJEMY. Substack pokazuje jedna wspolna liste dla obserwacji
        i subskrypcji, wiec kusi, zeby uzyc tu `browser.czy_juz_obserwujemy` —
        ale ta lista nie mowi, KTORA z dwoch rzeczy postawila tam dany uchwyt.
        Obserwowanie kogos nie subskrybuje go: przycisk „Subscribe" nadal jest
        i nadal dziala. Odsiew po tej liscie zamykalby wiec droge z 3,4 procent
        do 11,5 procent dokladnie tym ludziom, ktorych juz czytamy — zmierzone
        8 hostow z 92 na dzien pomiaru, czyli okolo 9 procent puli skazane na
        slabszy kanal na zawsze. Jedyny przypadek, ktorego przez to nie lapiemy
        z gory, to subskrypcja zrobiona RECZNIE przez wlasciciela; kosztuje ona
        JEDNO wejscie na profil, po ktorym „nie ma przycisku subskrypcja" trafia
        do dziennika i `kogo_juz_subskrybujemy` pamieta to juz na zawsze.

        REAGUJACY WCHODZI DO PULI TAKZE TUTAJ, mimo ze to blok drozszy
        spolecznie. Powod jest zmierzony: subskrypcje maja 11,5 procent
        konwersji zwrotnej wobec 3,4 procent przy obserwacji, wiec mocniejszy
        sygnal ma isc mocniejszym kanalem. Znany koszt: reagujacy bez wlasnej
        publikacji nie ma przycisku „Subscribe" — to jedno wejscie na profil,
        po ktorym `kogo_juz_subskrybujemy` zamyka go na zawsze, dokladnie tak
        samo jak `publikacja18`. Obserwowanie dziala u niego dalej.
        """
        if not na_teraz.get("subskrypcje"):
            return
        historia = kanal._historia()
        if not historia:
            return

        # TE SAME DWA POZIOMY, CO PRZY OBSERWACJI, i to jest zamierzone: jesli
        # host jest za stary tematycznie na obserwacje, to na subskrypcje —
        # ktora zaglada wlascicielowi do skrzynki i zostawia u nich slad
        # w liscie subskrybentow — jest za stary tym bardziej.
        wszyscy, rachunek = cele_wedlug_pierwszenstwa(historia)
        pamiec = browser.kogo_obserwujemy()
        zamkniete = kogo_juz_subskrybujemy()
        kandydaci = [h for h in wszyscy
                     if not czy_juz_subskrybujemy(h, zamkniete, pamiec)]
        print("  pula: %d hostow w historii, %d odsianych tematycznie"
              " (ostatni komentarz sprzed %s), %d z reakcja na nasza tresc;"
              " reagujacych z uchwytem %d, w puli %d (%d juz nas czyta,"
              " %d ponizej progu, %d mlodszych niz %d h);"
              " %d zostaje po odsianiu juz zasubskrybowanych"
              % (rachunek["wszystkich"], rachunek["sprzed_przestawienia"],
                 PRZESTAWIENIE_KONTA, rachunek["ze_skutkiem"],
                 rachunek["reagujacy_z_uchwytem"], rachunek["reagujacy"],
                 rachunek["reagujacy_juz_czyta"], rachunek["reagujacy_slabi"],
                 rachunek["reagujacy_swiezy"], rachunek["odstep_h"],
                 len(kandydaci)), flush=True)
        if not kandydaci:
            # ZERO Z POWODEM, NIE POWROT DO LOSU Z CALOSCI. Ta sama zasada, co
            # przy obserwacji: odsiew tematyczny to granica, nie preferencja.
            if wyslij:
                browser.zapisz_w_dzienniku(
                    "subskrypcja_pominieta", udane=True,
                    powod=(powod_pustej_puli(rachunek) if not wszyscy else
                           # Oba poziomy osobno — patrz ten sam komentarz
                           # w bloku obserwacji.
                           "pula wyczerpana: wszystkie %d celow juz"
                           " subskrybujemy (%d hostow po odsianiu"
                           " tematycznym, %d reagujacych na nasza tresc)"
                           % (len(wszyscy), rachunek["po_przestawieniu"]
                              - rachunek["zdublowani"],
                              rachunek["reagujacy"])))
            print("  nie ma kogo subskrybowac — %s"
                  % ("cala pula tematyczna juz zasubskrybowana" if wszyscy
                     else powod_pustej_puli(rachunek)), flush=True)
            return

        # ZAPAS NA ODPADY — ta sama liczba i ten sam powod, co przy obserwacji.
        # Host, ktorego uchwytu nie da sie ustalic z hosta, wymaga zapytania do
        # API i dopiero PO nim wiadomo, czy to dubel. Taki obrot nie jest proba
        # i nie moze zjadac slotu; zapas domyka to od gory, zeby jeden przebieg
        # nie obszedl calej puli.
        ZAPAS_NA_ODPADY = 4
        proby = 0
        z_pamieci = 0
        zostal_slad = False
        for host in kandydaci[: na_teraz["subskrypcje"] + ZAPAS_NA_ODPADY]:
            if proby >= na_teraz["subskrypcje"]:
                break
            if not zostal_czas("subskrypcje"):
                break
            uchwyt = browser.uchwyt_publikacji(host)
            # DRUGIE SPRAWDZENIE, JUZ PO ROZWIAZANIU UCHWYTU. Tanie sito wyzej
            # jest dokladne tylko dla adresow w domenie Substacka; dla wlasnej
            # domeny (24 z 92 hostow) uchwyt wychodzi dopiero z API i dopiero
            # tutaj widac, ze `www.jankowalski.com` to `kowalski`, ktorego
            # zasubskrybowalismy 30 sierpnia.
            if uchwyt and uchwyt in zamkniete:
                z_pamieci += 1
                print(f"  ({host} -> @{uchwyt} juz zasubskrybowany wedlug"
                      f" dziennika — nie wchodze na profil)", flush=True)
                continue
            if not uchwyt:
                # POMINIECIE TEZ JEST WYNIKIEM — dokladnie jak przy obserwacji.
                # Cichy `continue` stal tu do 1 wrzesnia 2026 i to przez niego
                # trzy proby zapisane w dzienniku jako `komu='www'` nie mialy
                # w sobie ani slowa o tym, ktorego adresu dotyczyly.
                if wyslij:
                    browser.dopisz_wynik(
                        "subskrypcja", {}, komu=host,
                        powod=f"nie ustalilem konta autora dla {host}")
                    zostal_slad = True
                print(f"  (nie ustalilem konta dla {host} — pomijam)", flush=True)
                continue
            if wyslij:
                if not rytm("komentarz", "subskrypcje", rytm_stanu):
                    break
                browser.zasubskrybuj(uchwyt, wyslij=True)
                rytm_stanu["komentarz"] = True
                # PROBA LICZY SIE TAKZE WTEDY, GDY PROFIL ODMOWIL. Weszlismy
                # na cudza strone i dostalismy odpowiedz — to jest zuzyty slot.
                # Powtorka nie grozi: `zasubskrybuj` zapisuje powod, a
                # `kogo_juz_subskrybujemy` czyta go przy nastepnym przebiegu.
                proby += 1
                zostal_slad = True
            else:
                print(f"  (zasubskrybowałbym: {uchwyt})", flush=True)
                proby += 1

        # DZIEN BEZ ANI JEDNEJ PROBY MA POWIEDZIEC DLACZEGO. Bez tego wpisu
        # odsiew zalatalby jedna dziure i otworzyl te sama, co przedtem: blok
        # chodzi, nie wystawia nic i nie zostawia sladu, wiec z zewnatrz
        # wyglada jak blok, ktorego nie ma. Tylko wtedy, gdy nic innego nie
        # zapisalo — jedno zdarzenie ma zostawic jeden slad.
        if wyslij and proby == 0 and z_pamieci and not zostal_slad:
            browser.zapisz_w_dzienniku(
                "subskrypcja_pominieta", udane=True,
                powod="pominietych %d z %d kandydatow: juz ich subskrybujemy"
                      " wedlug dziennika" % (z_pamieci, len(kandydaci)))

    # --- 4. polubienia: najtańszy uczciwy sygnał ------------------------------
    def polubienia() -> None:
        w = browser.polub_w_kanale(na_teraz["lajki"], wyslij=wyslij)
        zrobione["polubienia"] = w.get("polubione", 0)

    # --- 5. restacki: cudza notka plus nasze zdanie ---------------------------
    def restacki() -> None:
        """Podanie dalej trafia do kanału NASZYCH obserwujących i powiadamia
        autora oryginału — za cenę jednego zdania zamiast całej notki.

        Stoi po polubieniach świadomie: polubienie nic nie twierdzi, restack
        stawia nasze nazwisko obok cudzego tekstu. Jeśli dzień się kończy
        i coś ma wypaść, ma wypaść to, co niesie więcej ryzyka.
        """
        ile = na_teraz.get("restacki", 0)
        if not ile:
            print("  budżet na dziś: 0 — pomijam", flush=True)
            return
        w = browser.restackuj_w_kanale(
            ile, lambda n: stages.ocen_restack(conn, run_id, n), wyslij=wyslij)
        zrobione["restacki"] = w.get("restackowane", 0)
        if w.get("odmowy"):
            print(f"  odmów: {len(w['odmowy'])} — milczenie jest pełnym wynikiem",
                  flush=True)

    # KOLEJNOSC DECYDUJE O TYM, CO SIE W OGOLE WYDARZY. Zegar przebiegu
    # sprawdzaja bloki od odpowiedzi po subskrypcje; polubienia i restacki nie
    # patrza na niego wcale. Wiec gdy czas sie konczy, wypadaja dokladnie te
    # bloki, ktore sa uczciwe wobec zegara.
    #
    # Obserwowanie stalo za komentarzami — czyli za jedynym blokiem, ktory
    # potrafi zjesc caly budzet czasu (kazdy komentarz to pobranie strony, trzy
    # warianty i sprawdzenie faktow). Skutek zmierzony na dzienniku: przez piec
    # dni ZERO obserwacji przy budzecie 30-44 miesiecznie. Blok nie chodzil
    # w ogole, a nikt tego nie zauwazyl, bo brak wpisu wyglada jak brak okazji.
    #
    # Obserwowanie i subskrypcje ida teraz PRZED komentarze. Sa tanie (jedno
    # wejscie na profil, zero wywolan modelu), maja twardy limit miesieczny,
    # ktorego nie da sie nadrobic pozniej, i to one poszerzaja krag ludzi,
    # do ktorych w ogole mozemy sie potem odezwac.
    # --- 6. kopia listy subskrybentow, gdy sie zestarzala --------------------
    def zalegly_artykul() -> None:
        """Dowozi tekst, ktory zostal na dysku po nieudanej publikacji.

        NIE PISZE NOWEGO ARTYKULU i nie wola modelu ani razu. Bierze plik, za
        ktory `artykul_z_puli` juz zaplacil, i probuje wystawic go jeszcze raz.

        DLACZEGO TU, A NIE PRZEZ `Restart=` W USLUDZE. Zegar artykulu chodzi
        RAZ W TYGODNIU, wiec nieudany wtorek oznaczal tydzien ciszy. Restart
        uslugi puscilby caly przebieg od nowa razem z platnym researchem —
        a rutyna dnia chodzi piec razy dziennie i tekst juz ma.

        PODWOJNEJ PUBLIKACJI NIE MA JAK ZROBIC: `wystaw_artykul` zaczyna od
        `potwierdz_artykul` i przy tekscie juz publicznym oddaje
        `pominiete=True` — wtedy tez kasujemy znacznik.

        NIC TU NIE BLOKUJE. Po wyczerpaniu prob tekst i znacznik ZOSTAJA,
        a alarm krzyczy; petla tylko przestaje sie dobijac.
        """
        zaleg = stages.niewystawiony_artykul()
        if not zaleg:
            print("  brak zaleglego artykulu", flush=True)
            return
        sciezka = str(zaleg["sciezka"])
        if not os.path.exists(sciezka):
            print("  [zalegly] plik zniknal (%s) — kasuje znacznik" % sciezka,
                  flush=True)
            stages.zapomnij_niewystawiony()
            return
        if int(zaleg.get("proby", 0)) >= config.PROB_ZALEGLEGO_ARTYKULU:
            print("  [zalegly] %d prob i nadal nie wychodzi — PRZESTAJE"
                  " PROBOWAC, tekst i znacznik zostaja" % zaleg["proby"],
                  flush=True)
            try:
                import alarm
                alarm.wyslij(
                    "artykul-nie-wychodzi",
                    "Artykul nie wychodzi mimo %d prob" % zaleg["proby"],
                    "Plik: %s\nOstatni powod: %s\n\nTekst jest gotowy"
                    " i oplacony. Wystaw go recznie albo zbadaj, dlaczego"
                    " przegladarka go nie przepuszcza."
                    % (sciezka, zaleg.get("powod", "")))
            except Exception as exc:
                print("  (alarm nie poszedl: %s)" % type(exc).__name__,
                      flush=True)
            return
        if not wyslij:
            print("  (wystawilbym zalegly artykul: %s)" % sciezka, flush=True)
            return
        import browser as _br
        wynik = _br.wystaw_artykul(sciezka, wyslij=True)
        if wynik.get("wyslane"):
            print("  [zalegly] DOWIEZIONY: %s" % sciezka, flush=True)
            stages.zapomnij_niewystawiony()
            return
        ile = stages.odnotuj_probe_artykulu(
            str(wynik.get("blad") or "brak potwierdzenia"))
        print("  [zalegly] nadal nie poszedl (proba %d/%d): %s"
              % (ile, config.PROB_ZALEGLEGO_ARTYKULU,
                 str(wynik.get("blad"))[:120]), flush=True)

    def kopia_listy() -> None:
        """Jedyne aktywo, ktorego nie da sie odtworzyc — i jedyne miejsce,
        gdzie wlasciciel musial dotad cos kliknac.

        Czyta z WLASNEGO panelu wlasna sesja, ta sama droga, ktora agent
        wystawia notki. Odmowa nie jest awaria przebiegu: kopia to
        zabezpieczenie, a nie warunek pracy. Gdy sie nie uda, alarm i tak
        krzyknie nastepnego ranka i wtedy zostaje reczny eksport.
        """
        from datetime import datetime, timezone

        katalog = config.DATA_DIR / "kopie"
        kopie = sorted(katalog.glob("subskrybenci-*.csv"))
        if kopie:
            wiek = (datetime.now(timezone.utc)
                    - datetime.fromtimestamp(kopie[-1].stat().st_mtime,
                                             timezone.utc)).days
            if wiek < config.KOPIA_SUBSKRYBENTOW_CO_ILE_DNI:
                print(f"  ostatnia kopia ma {wiek} dni — jeszcze swieza",
                      flush=True)
                return
        if not wyslij:
            print("  (pobralbym liste subskrybentow)", flush=True)
            return
        try:
            import kopia_subskrybentow
            kopia_subskrybentow.main()
        except Exception as exc:
            print(f"  nie zrobilem kopii: {type(exc).__name__}: {exc}"[:160],
                  flush=True)

    for nazwa, robota in (("odpowiedzi", odpowiedzi), ("notki", notki),
                          ("obserwowanie", obserwuj), ("subskrypcje", subskrybuj),
                          ("komentarze", komentarze), ("dyskusje", dyskusje),
                          ("polubienia", polubienia), ("restacki", restacki),
                          ("zalegly artykul", zalegly_artykul),
                          ("kopia listy", kopia_listy)):
        print(f"\n-- {nazwa} --", flush=True)
        blok(nazwa, robota)

    print("\n== dzień zamknięty ==", flush=True)
    for k, v in zrobione.items():
        print(f"   {k}: {v}", flush=True)
    if not wyslij:
        print("   (tryb sprawdzenia — nic nie poszło w świat)", flush=True)
    alarm.sprawdz_sesje_i_ostrzez()
    return 0


def _sygnal_ma_zostawic_slad() -> None:
    """Zamienia SIGTERM na wyjatek, zeby przebieg zdazyl sie zapisac.

    Systemd konczy przebieg SIGTERM-em po `TimeoutStartSec`. Python nie widzi
    sygnalu jako wyjatku, wiec proces po prostu znikal: `finish_run` sie nie
    wykonywalo i wiersz wisial w bazie jako RUNNING az do kontroli zdrowia,
    nawet trzy godziny. Przez ten czas rozdzielnik dziennej normy nie wiedzial,
    czy przebieg trwa, czy zginal.

    Teraz sygnal podnosi wyjatek, wiec dziala ta sama sciezka co przy kazdej
    innej awarii: status FAILED i powod w notatce. Systemd daje jeszcze
    `TimeoutStopSec` (domyslnie 90 s) przed SIGKILL — na zapisanie jednego
    wiersza to bardzo duzo.
    """
    import signal

    def podnies(numer, _ramka):
        raise KeyboardInterrupt(f"przerwany sygnalem {signal.Signals(numer).name}")

    for s in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(s, podnies)
        except (ValueError, OSError, AttributeError):
            pass          # nie glowny watek albo system bez tego sygnalu


def main() -> int:
    _utf8_stdout()
    _sygnal_ma_zostawic_slad()
    import call_runtime, time
    call_runtime.RUN_DEADLINE = time.monotonic() + 3600
    try:
        _zamek = zajmij_zamek()   # trzymany do końca procesu
    except JuzDziala as exc:
        print(f"  {exc}", flush=True)
        return 0
    parser = argparse.ArgumentParser(description="agent-v2 — jeden artykuł do szuflady")
    parser.add_argument("--stop-after", choices=STAGES, help="zatrzymaj się po tym etapie")
    parser.add_argument("--use-cache", action="store_true", help="użyj zapisanych wyników etapów")
    parser.add_argument("--topics", type=int, default=6, help="ile tematów ma zwrócić skaut")
    parser.add_argument("--dzien", action="store_true",
                        help="rutyna dnia: notki, komentarze, odpowiedzi, polubienia")
    parser.add_argument("--wyslij", action="store_true",
                        help="NAPRAWDĘ wystaw treści (domyślnie tylko pokazuje)")
    args = parser.parse_args()
    global _CACHE_CONTEXT
    _CACHE_CONTEXT = {"topics": args.topics}
    # BRAMA PRESETU — PRZED BAZA, PRZED PRZEGLADARKA, PRZED PIERWSZYM CENTEM.
    # Bez podlaczonego presetu silnik nie ma tematu, stylu ani planu; zegar,
    # ktory odpali ten plik po `odlacz`, ma dostac odmowe, nie wbudowany
    # profil. W darmowym tescie brama sie nie odzywa — patrz `preset.wymagaj_aktywnego`.
    try:
        preset.wymagaj_aktywnego(config, "run.py")
    except preset.BrakPresetu as exc:
        print(str(exc), flush=True)
        return 3
    # Musi stac PO parse_args (inaczej `args` jeszcze nie istnieje) i PRZED
    # pierwszym dotknieciem bazy — zeby kopia testowa odpadala, zanim
    # cokolwiek zapisze.
    odmow_publikacji_z_kopii(args.wyslij)

    conn = db.connect()
    run_id = db.start_run(conn)
    stage = "start"

    print(f"== przebieg {run_id} ==", flush=True)
    if args.dzien:
        # `finally` zamykalo przebieg jako DONE takze wtedy, gdy sie wywalil —
        # i tak wlasnie zapisal sie przebieg, ktory padl na `KeyError: notki`.
        # Dwie szkody: statystyka bledow milczala, a rozdzielnik dziennej normy
        # liczyl ten przebieg jako odbyty i chcial wcisnac cala reszte w jeden
        # nastepny. Przerwany przebieg ma byc widoczny jako przerwany.
        try:
            wynik = dzien(conn, run_id, args.wyslij)
        except BaseException as exc:
            db.finish_run(conn, run_id, "FAILED", "dzien",
                          f"{type(exc).__name__}: {exc}"[:500])
            _summary(conn, run_id)
            raise
        db.finish_run(conn, run_id, "DONE", "dzien", "")
        _summary(conn, run_id)
        return wynik
    print(
        f"   baza: {config.DB_PATH}   "
        f"sufit przebiegu: {config.RUN_LIMIT_USD} USD"
        f"{'   TANIO (DeepSeek)' if config.CHEAP_MODE else ''}"
        f"{'   DRY_RUN' if config.DRY_RUN else ''}",
        flush=True,
    )

    # NIE ZACZYNAJ TEGO, CZEGO NIE SKONCZYSZ — ta sama zasada co przy przerwach
    # miedzy dzialaniami. Sufit miesieczny jest egzekwowany PRZED KAZDYM
    # wywolaniem, wiec artykul mogl paść w dowolnym miejscu: po oplaconym
    # researchu i przed napisaniem, albo po napisaniu i przed recenzja.
    # Pieniadze wydane, artykulu nie ma. Skoro znamy koszt calego przebiegu
    # (RUN_LIMIT_USD), umiemy o to zapytac zawczasu.
    if not config.NO_LIMIT:
        from datetime import datetime as _dt, timezone as _tz

        _m = _dt.now(_tz.utc).strftime("%Y-%m")
        _zostalo = config.MONTHLY_LIMIT_USD - db.spent_usd(conn, _m)
        if _zostalo < config.RUN_LIMIT_USD:
            print(f"   MIESIAC NA WYCZERPANIU: zostalo ${_zostalo:.2f}, a caly "
                  f"artykul to do ${config.RUN_LIMIT_USD}. Nie zaczynam — "
                  f"lepiej nie napisac nic niz zaplacic za polowe.", flush=True)
            return _done(conn, run_id, "budzet")

    try:
        stage = "scout"
        topics = cached(stage, lambda: stages.scout(conn, run_id, args.topics), args.use_cache)
        print(f"\n-- tematy ({len(topics)}) --", flush=True)
        for i, topic in enumerate(topics):
            print(f"{i}. {topic.get('title')}", flush=True)
        if args.stop_after == stage:
            return _done(conn, run_id, stage)

        stage = "feasibility"
        assessments = cached(
            stage, lambda: stages.feasibility(conn, run_id, topics), args.use_cache
        )
        # Katy z poprzednich artykulow ida do WYBORU, nie tylko do promptu
        # skauta — patrz `niepowtorzony`.
        topic, verdict = stages.pick_topic(
            topics, assessments, run_id,
            # ARTYKULY *I* NOTKI. Konto ma jednego czytelnika, nie dwoch —
            # notka i artykul o tym samym w jeden dzien to dla niego po prostu
            # dwa razy to samo. 25 sierpnia rano poszla notka, a po poludniu
            # TEN SAM temat wygral wybor artykulu przy 53% wspolnych rdzeni
            # wobec progu 20% — bo straznik pytal wylacznie o poprzednie
            # artykuly i notki byly dla niego niewidoczne.
            wczesniejsze=(stages.tematy_do_porownania(conn)
                          + stages.ostatnie_notki(1000)))
        print("\n-- odsiew wykonalności --", flush=True)
        for a in assessments:
            mark = "TAK " if a.get("feasible") else "nie "
            print(
                f"  {mark} [{a.get('index')}] pewność={a.get('confidence')}"
                f" źródeł~{a.get('expected_primary_sources')}  {a.get('note', '')[:110]}",
                flush=True,
            )
        print(f"\n>> wybrany temat: {topic.get('title')}", flush=True)
        print(f"   {topic.get('question')}", flush=True)
        print(f"   uzasadnienie: {verdict.get('note', '')}", flush=True)
        if args.stop_after == stage:
            return _done(conn, run_id, stage)

        stage = "discovery"
        recent = db.recent_domains(conn, config.DIVERSITY_LOOKBACK)
        sources = cached(
            stage,
            lambda: stages.discovery(conn, run_id, topic["question"], recent),
            args.use_cache,
        )
        print(f"\n-- znalezione źródła ({len(sources)}) --", flush=True)
        for s in sources:
            print(
                f"  [{s.get('class', '?'):9}] {s.get('host')}"
                f"{'  DLACZEGO' if s.get('answers_why') else ''}"
                f"{'  LICZBY' if s.get('has_numbers') else ''}",
                flush=True,
            )
            print(f"      {s.get('title', '')[:100]}", flush=True)
        primary = sum(1 for s in sources if s.get("class") == "PRIMARY")
        why = sum(1 for s in sources if s.get("answers_why"))
        print(
            f"\n   pierwotnych: {primary}/{config.MIN_PRIMARY_SOURCES}   "
            f"wyjaśniających DLACZEGO: {why}/{config.MIN_WHY_SOURCES}   "
            f"organizacji: {len({s.get('host') for s in sources})}",
            flush=True,
        )
        if args.stop_after == stage:
            return _done(conn, run_id, stage)

        stage = "fetch"
        print("\n-- pobieranie --", flush=True)
        corpus = cached(stage, lambda: stages.fetch(conn, run_id, sources), args.use_cache)
        chars = sum(len(s.get("text", "")) for s in corpus)
        print(
            f"\n   pobrano {len(corpus)}/{len(sources)}   "
            f"{chars} znaków   pierwotnych: "
            f"{sum(1 for s in corpus if s.get('class') == 'PRIMARY')}",
            flush=True,
        )
        # --- druga runda, gdy korpus wyszedl chudy ---------------------------
        # Jeden artykul poszedl do pisarza z TRZEMA zrodlami z dziesieciu
        # proponowanych. To nie jest wada stylu, tylko wada materialu: cienka
        # karta dowodowa znaczy mniej liczb, slabsze paralele i wiecej miejsc,
        # gdzie pisarz musi dolozyc cos z pamieci — i wlasnie tam wyszedl
        # jedyny fakt bez pokrycia w tym tekscie.
        #
        # Druga dyskoveria kosztuje ~$0,28. Artykul napisany z trzech zrodel
        # kosztuje caly przebieg i wychodzi cienki, wiec to sie oplaca.
        # DRUGA RUNDA TAKZE PRZY BRAKU REKORDOW, nie tylko przy pustym korpusie.
        #
        # Zmierzone na trzynastu przebiegach z jednym wywolaniem dyskoverii:
        # korpus bywa PELNY i jednoczesnie bezwartosciowy. Przebieg z 25
        # wyszukiwaniami oddal dziewiec pobranych zrodel, z czego JEDNO
        # pierwotne; inny siedem, z czego jedno. Warunek liczacy same sztuki
        # tego nie widzi — dziewiec to duzo wiecej niz prog czterech, wiec druga
        # runda nie odpalala sie nigdy, a pisarz dostawal dziewiec tekstow O
        # dokumencie i ani jednego dokumentu.
        pierwotnych = sum(1 for s in corpus if s.get("class") == "PRIMARY")
        za_chudo = len(corpus) < config.MIN_ZRODEL_DO_PISANIA
        bez_rekordow = pierwotnych < config.MIN_PRIMARY_SOURCES
        if za_chudo or bez_rekordow:
            print(f"\n-- druga runda: zrodel {len(corpus)}"
                  f"/{config.MIN_ZRODEL_DO_PISANIA}, pierwotnych"
                  f" {pierwotnych}/{config.MIN_PRIMARY_SOURCES} --", flush=True)
            try:
                juz_mamy = {s.get("host") or s.get("url", "") for s in corpus}
                dodatkowe = [
                    s for s in stages.discovery(conn, run_id, topic["question"],
                                                recent,
                                                tylko_pierwotne=bez_rekordow)
                    if (s.get("host") or s.get("url", "")) not in juz_mamy
                ]
                if dodatkowe:
                    dobrane = stages.fetch(conn, run_id, dodatkowe)
                    corpus = corpus + dobrane
                    print(f"   dobrano {len(dobrane)} z {len(dodatkowe)} nowych"
                          f" — korpus ma teraz {len(corpus)} zrodel", flush=True)
                else:
                    print("   druga runda nie znalazla nowych adresow", flush=True)
            except Exception as exc:
                # Dobieranie jest premia, nie warunkiem. Jego awaria nie moze
                # zabic przebiegu, za ktorego research juz zaplacilismy.
                print(f"  [awaria] druga runda padla ({exc}) — pisze z tego, co jest",
                      flush=True)

        # DOPIERO TERAZ PUSTY KORPUS KONCZY PRZEBIEG, i to jest cala roznica.
        #
        # Wczesniej wyjatek leciał wewnatrz `stages.fetch`, wiec druga runda
        # powyzej byla NIEOSIAGALNA — zabezpieczenie nie dzialalo dokladnie
        # wtedy, gdy bylo najbardziej potrzebne. Przebieg 91 oddal cztery
        # zrodla, same pierwotne, wszystkie padly na blokadzie, i umarl zamiast
        # dobrac inne.
        #
        # Konczymy jawnie i bez wyjatku: research jest oplacony, wiec przebieg
        # ma sie zamknac zapisanym powodem, a nie sladem stosu.
        if not corpus:
            print("\n!! po dwoch rundach korpus jest pusty — nie ma z czego"
                  " pisac. Konce przebieg bez artykulu.", flush=True)
            return _done(conn, run_id, "fetch")

        if args.stop_after == stage:
            return _done(conn, run_id, stage)

        stage = "classify"
        print("\n-- klasyfikacja i wyciąg fragmentów --", flush=True)
        evidence = cached(
            stage,
            lambda: stages.classify(conn, run_id, topic["question"], corpus),
            args.use_cache,
        )
        n_ex = sum(len(s["excerpts"]) for s in evidence)
        n_num = sum(len(s["numbers"]) for s in evidence)
        print(
            f"\n   materiał dowodowy: {len(evidence)} źródeł, {n_ex} fragmentów, "
            f"{n_num} liczb   pierwotnych: "
            f"{sum(1 for s in evidence if s['class'] == 'PRIMARY')}",
            flush=True,
        )
        if args.stop_after == stage:
            return _done(conn, run_id, stage)

        # Od tego miejsca artykuł MUSI powstać. Temat jest wybrany, research
        # zrobiony i opłacony — żaden dalszy etap nie ma prawa zabić przebiegu.
        stage = "synthesis"
        print("\n-- synteza --", flush=True)
        try:
            card = cached(
                stage,
                lambda: stages.synthesis(conn, run_id, topic["question"], evidence),
                args.use_cache,
            )
        except PRZERYWAJA:
            # Karta zapasowa ma sens po awarii JEDNEGO wywolania. Przy pustym
            # budzecie zaraz za nia stoi pisarz — najdrozszy etap przebiegu
            # (~0,76 USD) — i wywroci sie na tym samym bledzie. Ta sama oslona
            # stoi w `artykul_z_puli.py`.
            raise
        except Exception as exc:
            print(f"  [awaria] synteza padła ({exc}) — składam kartę z dowodów", flush=True)
            card = stages.fallback_card(topic["question"], evidence)
        print(f"\n   teza: {card.get('working_thesis', '')}", flush=True)
        print(f"\n   mechanizm: {card.get('main_mechanism', '')[:400]}", flush=True)
        print(f"\n   potwierdzone twierdzenia ({len(card.get('confirmed_claims', []))}):", flush=True)
        for c in card.get("confirmed_claims", []):
            print(f"     • {c.get('claim', '')[:150]}", flush=True)
        print(f"\n   liczby ({len(card.get('citable_numbers', []))}):", flush=True)
        for n in card.get("citable_numbers", []):
            print(f"     • {n.get('value')} — {n.get('means', '')[:110]}", flush=True)
        for label, key in (("niepewne", "uncertain_claims"),
                           ("sprzeczności", "contradictions"),
                           ("czego nie ustalono", "not_established")):
            items = card.get(key) or []
            if items:
                print(f"\n   {label} ({len(items)}):", flush=True)
                for item in items:
                    print(f"     • {str(item)[:150]}", flush=True)
        if args.stop_after == stage:
            return _done(conn, run_id, stage)

        # --- czy jest tu luka, ktora obcy poczuje ----------------------------
        # Bramka stoi PRZED pisarzem, bo po nim byloby za pozno: research
        # oplacony, a artykul i tak martwy. Nic nie blokuje — werdykt DOLOZ
        # wysyla nas do banku po pare, zamiast zatrzymywac przebieg.
        stage = "warto_pisac"
        print("\n-- czy jest tu luka --", flush=True)
        try:
            ocena = stages.warto_pisac(conn, run_id, card)
            wiara = (ocena.get("contradicted_belief") or {}).get("the_belief", "")
            print("   zlamane przekonanie: %s"
                  % ("TAK" if ocena["przekonanie"] else "NIE"), flush=True)
            if wiara:
                print('   czytelnik wierzy: "%s"' % str(wiara)[:120], flush=True)
            print("   filary: %d z 3  (%s)" % (
                ocena["ile_filarow"],
                ", ".join(k for k, v in ocena["filary"].items() if v) or "zaden"),
                flush=True)
            print("   >> %s — %s" % (ocena["werdykt"], ocena["powod"]), flush=True)

            if ocena["werdykt"] == "DOLOZ":
                # TO JEST MOMENT, DLA KTOREGO BANK ISTNIEJE. Temat ma luke, ale
                # za malo materialu, zeby ja rozwinac. Bibliotekarz szuka
                # w zaplaconych resztkach mechanizmu z INNEJ dziedziny —
                # tak wlasnie powstal najlepszy tekst serii.
                print("   szukam pary w banku...", flush=True)
                bank = stages.bank_fragmentow(conn)
                if not bank:
                    print("   bank pusty — pisarz dostaje karte jak jest", flush=True)
                else:
                    grupy = stages.bibliotekarz(conn, run_id, bank).get("groups") or []
                    dolozone = [{"domain": ", ".join(g.get("dziedziny", [])),
                                 "mechanism": g.get("mechanism", ""), "z_banku": True}
                                for g in grupy[:2]]
                    if dolozone:
                        card.setdefault("parallel_mechanisms", []).extend(dolozone)
                        print("   dolozono %d mechanizmow z banku:" % len(dolozone),
                              flush=True)
                        for d in dolozone:
                            print("     • [%s] %s"
                                  % (d["domain"], d["mechanism"][:110]), flush=True)
                    else:
                        print("   bank nie ma pary — pisarz dostaje karte jak jest",
                              flush=True)
            card["ocena_ciekawosci"] = ocena
        except PRZERYWAJA:
            # Budzet albo wylacznik — na wylot, patrz `PRZERYWAJA` na gorze
            # pliku. Gdyby zostalo polkniete tutaj, pisarz ponizej wywrocilby
            # sie na tym samym bledzie, tylko juz pod druga oslona, i tak dalej
            # az do `browser.wystaw_artykul`.
            raise
        except Exception as exc:
            # Bramka jest doradcza. Jej awaria nie moze kosztowac oplaconego
            # researchu — artykul powstaje tak czy owak.
            print("  [awaria] bramka ciekawosci padla (%s) — pisze bez niej" % exc,
                  flush=True)
        if args.stop_after == stage:
            return _done(conn, run_id, stage)

        stage = "write"
        print("\n-- pisanie --", flush=True)
        try:
            glebokosc = str(verdict.get("depth") or "RICH").upper()
            draft = cached(stage,
                           lambda: stages.write(conn, run_id, card, glebokosc),
                           args.use_cache)
        except PRZERYWAJA:
            # POWTORKA NA OPUSIE NIE MA PRAWA RUSZYC PRZY WYCZERPANYM BUDZECIE.
            # Opus jest DROZSZY od tego, co wlasnie padlo, wiec oslona
            # podwajalaby wydatek (~0,76 USD drugi raz) dokladnie w chwili, gdy
            # `llm._preflight` powiedzial, ze pieniedzy nie ma. Przy
            # `KILL_SWITCH=true` powtorka i tak wroci z tym samym
            # `PreflightFailed` — jedno wywolanie po nic i wyjatek na koniec.
            raise
        except Exception as exc:
            # Jedno powtórzenie na pisarzu ZAPASOWYM Z PRESETU, bo tu ginie cały
            # opłacony research. Do 2026-09-05 stal tu `config.CLAUDE` na sztywno,
            # wiec preset nie mial jak powiedziec, co ma sie stac po awarii
            # pisarza (M3 audytu). Pusty `modele.zapasowy_pisarz` znaczy: nie
            # powtarzaj, zatrzymaj sie — i wyjatek idzie dalej.
            if not config.ZAPASOWY_PISARZ:
                print(f"  [awaria] pisarz ({config.MODEL_FOR['write']}) padł: {exc}"
                      f" — preset nie ma pisarza zapasowego, zatrzymuję", flush=True)
                raise
            print(
                f"  [awaria] pisarz ({config.MODEL_FOR['write']}) padł: {exc}"
                f" — powtarzam na {config.ZAPASOWY_PISARZ}",
                flush=True,
            )
            # NADPISANIE NA CZAS JEDNEGO WYWOLANIA, POTEM Z POWROTEM.
            # Stalo tu golo `config.MODEL_FOR["write"] = config.CLAUDE`, czyli
            # globalna zmiana konfiguracji uzyta jako lokalne nadpisanie i nigdy
            # niecofnieta. Od tej chwili pole klamalo o tym, co jest
            # skonfigurowane — a linia wyzej drukuje nazwe pisarza WLASNIE
            # z niego, wiec druga awaria w tym samym procesie meldowalaby, ze
            # padl Opus. Kazde nastepne `write` szloby przy tym na model
            # najdrozszy, bez decyzji i bez sladu. Dzis `write` wola sie raz na
            # proces, wiec nikt tego nie zobaczyl: wlasnosc trzymala sie
            # przypadkiem, nie z konstrukcji.
            _pisarz = config.MODEL_FOR["write"]
            try:
                config.MODEL_FOR["write"] = config.ZAPASOWY_PISARZ
                draft = stages.write(conn, run_id, card, glebokosc)
            finally:
                config.MODEL_FOR["write"] = _pisarz
        words = len(draft["body"].split())
        print(f"\n   tytuł: {draft.get('title')}", flush=True)
        print(f"   podtytuł: {draft.get('subtitle', '')}", flush=True)
        # ZAKRES MUSI BYC TEN, KTORY DOSTAL PISARZ. Stalo tu `config.TARGET_WORDS`
        # (1075) i plaski zakres 950-1200 — czyli wartosci sprzed skalowania
        # dlugosci do ilosci materialu. Artykul THIN, napisany poprawnie na 430
        # slow przy celu 420, wypisywal sie jako „430 slow (cel 1075, zakres
        # 950-1200)": wygladal na polowe tego, co mial miec, i przy nadzorze
        # kazalby szukac usterki tam, gdzie jej nie ma.
        dl = config.dlugosc_dla(glebokosc)
        print(
            f"   długość: {words} słów "
            f"(glebokosc {glebokosc or '?'}, cel {dl['cel']}, "
            f"zakres {dl['min']}-{dl['max']})",
            flush=True,
        )
        print(f"   akapit o granicach: {draft.get('limits_paragraph_present')}", flush=True)
        # Czy liczba jest w korpusie, liczy WYŁĄCZNIE gates.py. Stała tu druga
        # implementacja tego samego pytania i natychmiast dała inną odpowiedź
        # (uznała 'E 938' za zmyślone) — to jest ta sama choroba, przez którą
        # przepisujemy starego agenta.
        if args.stop_after == stage:
            return _done(conn, run_id, stage)

        stage = "review"
        print("\n-- recenzja --", flush=True)
        try:
            report = cached(
                stage, lambda: stages.review(conn, run_id, card, draft), args.use_cache
            )
        except PRZERYWAJA:
            # „SZUFLADA" TO ZDANIE NIEPRAWDZIWE NA SCIEZCE `--wyslij`. Ponizej
            # stoi `stages.zweryfikuj` i `browser.wystaw_artykul(path,
            # wyslij=True)`, a `zweryfikuj` przy tym samym bledzie budzetu tez
            # padnie — czyli adnotacja „recenzja niedostepna" ladowalaby
            # w uwagach artykulu, ktory chwile pozniej wychodzi na Substacka
            # bez ani jednej dzialajacej kontroli.
            #
            # Polykamy tu WYLACZNIE awarie samej recenzji: zly JSON, timeout,
            # odmowe jednego wywolania.
            raise
        except Exception as exc:
            # Recenzja nic nie blokuje, więc jej brak też nie może. Artykuł
            # trafia do szuflady z adnotacją, że nie został rozliczony zdanie
            # po zdaniu — właściciel wie, na co patrzy.
            print(f"  [awaria] recenzja padła ({exc}) — zapisuję bez niej", flush=True)
            report = {"sentences": [], "unsupported_facts": [],
                      "summary": f"recenzja niedostępna: {type(exc).__name__}"}
        sentences = report.get("sentences", [])
        counts = {k: sum(1 for s in sentences if s.get("class") == k)
                  for k in ("FACT", "INFERENCE", "PROSE")}
        # SKLADAMY Z DWOCH ZRODEL, NIE Z JEDNEGO. Recenzent klasyfikuje KAZDE
        # zdanie (`supported`) i osobno powtarza te nieoparte w zbiorczej
        # liscie. Czytalismy wylacznie liste — czyli ufali, ze model poprawnie
        # przepisze wlasny wynik w drugie miejsce. Zdanie oznaczone jako
        # nieoparte, ale niepowtorzone, przepadalo bez sladu, i to jest glowny
        # sygnal jakosci faktograficznej calego potoku.
        #
        # Na przebiegu 25 model sie nie pomylil (1 oznaczone, 1 w liscie). To
        # dowod, ze raz nie zawiodl, a nie ze nie zawiedzie — a redundancja
        # miedzy dwoma polami tej samej odpowiedzi jest dokladnie tym, czego
        # kod nie powinien zakladac.
        unsupported = list(report.get("unsupported_facts", []) or [])
        znane = {str(x.get("text", ""))[:60] for x in unsupported}
        dopisane = 0
        for s in sentences:
            if s.get("class") != "FACT" or s.get("supported") is not False:
                continue
            if str(s.get("text", ""))[:60] in znane:
                continue
            unsupported.append({"text": s.get("text", ""),
                                "why": s.get("why", "")})
            dopisane += 1
        if dopisane:
            print(f"   [recenzja] {dopisane} zdań oznaczonych jako nieoparte, "
                  f"których model nie powtórzył w liście zbiorczej — dopisuję",
                  flush=True)
        print(
            f"   zdań: {len(sentences)}   fakty: {counts['FACT']}   "
            f"wnioskowanie: {counts['INFERENCE']}   proza: {counts['PROSE']}",
            flush=True,
        )

        # ZATRZYMANIE PO RECENZJI. `review` i `forma` byly w STAGES, wiec
        # argparse przyjmowal je jako `--stop-after` bez slowa sprzeciwu —
        # a po nich NIE BYLO ani jednego sprawdzenia. `--stop-after review
        # --wyslij` szedl wiec do konca i PUBLIKOWAL. Flaga, ktora ma
        # zatrzymac przed publikacja, a publikuje, jest gorsza od jej braku:
        # brak widac od razu, cicha bezczynnosc dopiero po fakcie.
        if args.stop_after == stage:
            return _done(conn, run_id, stage)

        # Obserwacja formy — osobne wywołanie od recenzji. Recenzent chroni
        # wnioskowanie przed zgłoszeniem (śmiała interpretacja nie jest wadą),
        # a ta bramka liczy m.in. zastrzeżenia; złączone tępiłyby się nawzajem.
        # Jak recenzja: nic nie blokuje, więc jej awaria też nie może.
        stage = "forma"
        try:
            forma = cached(stage, lambda: stages.ocen_forme(conn, run_id, draft),
                           args.use_cache)
            przekonania = forma.get("beliefs") or []
            slow = len(draft["body"].split(config.NAGLOWEK_ZRODEL)[0].split())
            print(f"   przekonania czytelnika: {len(przekonania)}"
                  f"   (samo wsparcie: {len(forma.get('support_only') or [])})"
                  f"   jedno co {slow / max(1, len(przekonania)):.0f} słów",
                  flush=True)
            moment = (forma.get("reader_moment") or {}).get("quote", "")
            gdzie = gates.pozycja_w_tekscie(moment, draft["body"])
            print("   przyłapanie czytelnika: %s"
                  % (f"{100 * gdzie:.0f}% głębokości" if gdzie is not None
                     else ("jest, ale nie znalazłem w tekście" if moment else "brak")),
                  flush=True)
        except PRZERYWAJA:
            # Czwarta oslona tej samej klasy. Gdy budzet konczy sie dopiero
            # tutaj (recenzja jeszcze przeszla), polkniecie prowadzi do tej
            # samej publikacji bez sprawdzenia faktow: `stages.zweryfikuj`
            # kilkadziesiat linii nizej jest kolejnym platnym wywolaniem
            # i padnie na tym samym bledzie.
            raise
        except Exception as exc:
            print(f"  [awaria] obserwacja formy padła ({exc}) — idę dalej",
                  flush=True)
            forma = {}

        findings = gates.deterministic_floors(
            draft["body"], card, poprzednie=stages.poprzednie_teksty(pomin_tresc=draft["body"]))
        findings.extend(gates.uwagi_z_formy(forma, draft["body"]))
        # WIEK MATERIALU. Sciezka artykulu nie miala zadnego sprawdzenia daty —
        # patrz `stages.swiezosc_karty`.
        findings.extend(stages.swiezosc_karty(card))
        for item in unsupported:
            findings.append({"gate": "FAKT_BEZ_POKRYCIA", "detail": item.get("text", "")})

        print("\n-- uwagi (nic nie blokuje) --", flush=True)
        if findings:
            for f in findings:
                print(f"   [{f['gate']}] {f['detail'][:160]}", flush=True)
        else:
            print("   czysto — żadna uwaga", flush=True)

        if args.wyslij:
            draft, audyt = stages.przygotuj_artykul_do_publikacji(conn, run_id, draft, card, report)
            if not audyt.get('safe_to_post') or audyt.get('nie_sprawdzone'):
                path = stages.save(conn, run_id, topic, card, draft, 'ZATRZYMANY', 'FACTCHECK', findings)
                print('>> odlozono artykul po kontroli faktow: %s' % path, flush=True)
                return _done(conn, run_id, 'factcheck-deferred')

        status, blocked_by = gates.verdict(findings)
        notes = [*findings,
                 {"gate": "DLUGOSC", "detail": f"{len(draft['body'].split())} słów"},
                 {"gate": "RECENZJA", "detail": report.get("summary", "")}]
        # Temat wzięty MIMO odrzucenia przez odsiew ma o tym powiedzieć.
        # `pick_topic` ustawiał flagę i pisał w komentarzu, że „zapisuje to
        # w uwagach" — a nie zapisywał: `verdict` żyje dalej tylko po to, by
        # oddać `depth`. Właściciel czytający `.uwagi.md` nie dowiadywał się,
        # że tekst powstał z tematu, którego wykonalność odrzuciła.
        if verdict.get("mimo_odrzucenia"):
            notes.append({
                "gate": "TEMAT_MIMO_ODRZUCENIA",
                "detail": ("żaden temat nie przeszedł odsiewu wykonalności — "
                           "wzięty najlepszy z odrzuconych (pewność %.2f, "
                           "spodziewane źródła %s)"
                           % (float(verdict.get("confidence") or 0),
                              verdict.get("expected_primary_sources"))),
            })
        if args.stop_after == "forma":
            return _done(conn, run_id, "forma")

        # Fragmenty, których artykuł nie zużył, zostają zapisane razem z kartą.
        # Każdy przebieg zbiera ich kilkadziesiąt, a tekst bierze kilka — reszta
        # to gotowe, ocytowane fakty na notki w dni bez artykułu.
        card["unused_evidence"] = [
            {"url": s["url"], "publisher": s.get("publisher"), "excerpts": s["excerpts"],
             "numbers": s["numbers"]}
            for s in evidence
        ]
        # Stopka z data zrodel PRZED zapisem — patrz `stages.wstaw_date_zrodel`.
        draft["body"] = stages.wstaw_date_zrodel(draft["body"], card)
        path = stages.save(conn, run_id, topic, card, draft, status, blocked_by, notes)

        print(f"\n>> {status}" + (f" ({blocked_by})" if blocked_by else ""), flush=True)
        print(f">> zapisano: {path}", flush=True)

        # OKLADKA POWSTAJE Z ARTYKULEM, NIE Z PUBLIKACJA. Stala wczesniej
        # wewnatrz galezi `--wyslij`, wiec kazdy przebieg bez publikacji
        # zapisywal na dysk artykul BEZ okladki, a cala sciezka graficzna
        # sprawdzala sie wylacznie na zywo, za prawdziwe pieniadze i przy
        # prawdziwej publikacji. Dlatego okladka zgubiona przez usterke
        # zapisu wywolan wyszla na jaw dopiero po fakcie: nie bylo ani
        # jednego przebiegu, w ktorym mogla sie zepsuc bezpiecznie.
        #
        # Grafika NIGDY nie zatrzymuje artykulu: brak czterech centow na
        # obrazek nie moze wyrzucic do kosza researchu za czterdziesci.
        stages.grafika(conn, run_id, draft, sciezka_artykulu=path)

        if args.wyslij:
            import browser

            print("\n-- publikacja --", flush=True)
            stage = "publish"
            wynik = browser.wystaw_artykul(path, wyslij=True)
            print(f">> {'OPUBLIKOWANY' if wynik.get('wyslane') else 'NIE POSZEDŁ'}"
                  f"{'  ' + str(wynik.get('blad')) if wynik.get('blad') else ''}",
                  flush=True)
            if not wynik.get('wyslane'):
                raise RuntimeError('Substack did not confirm article publication: ' +
                                   str(wynik.get('blad') or 'unknown outcome'))
        return _done(conn, run_id, stage)

    except Exception as exc:
        db.finish_run(conn, run_id, "FAILED", stage, f"{type(exc).__name__}: {exc}"[:500])
        print(f"\n!! stanęło na etapie {stage}: {type(exc).__name__}: {exc}", file=sys.stderr)
        traceback.print_exc()
        _summary(conn, run_id)
        return 1
    finally:
        conn.close()


def _done(conn, run_id: int, stage: str) -> int:
    db.finish_run(conn, run_id, "DONE", stage, f"zatrzymany po etapie {stage}")
    _summary(conn, run_id)
    return 0


def _summary(conn, run_id: int) -> None:
    row = conn.execute(
        "SELECT COALESCE(SUM(cost_usd), 0) AS total, COUNT(*) AS n FROM calls WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    # NIEUDANE WYWOLANIA MAJA KOSZT NIEZNANY, NIE ZEROWY — i ma to byc widac.
    #
    # `llm.call` po wyczerpaniu ponowien zapisuje wiersz z `cost_usd=0.0`,
    # `price_verified=0` i `ok=0`, i robi to swiadomie: zgadnieta kwota
    # w zapisie finansowym jest gorsza niz jej brak. Ale ta linia sumowala
    # `cost_usd` i liczyla `COUNT(*)`, wiec nieudana proba wchodzila do LICZBY
    # wywolan, wnosila zero do KWOTY i nic tego nie sygnalizowalo. Dzien
    # z trzema padnietymi `curiosity` — kazde po dwoch ponowieniach, czyli
    # dziewiec zadan wyslanych do dostawcy — meldowal sie jak dzien bez strat.
    #
    # Zmierzone 5 wrzesnia 2026 na zywej awarii DeepSeeka: wiersz powstaje,
    # `ok=0`, `note` niesie `RemoteProtocolError`. Suma jest wiec DOLNA
    # granica rachunku, nie rachunkiem.
    nieudane = conn.execute(
        "SELECT COUNT(*) FROM calls WHERE run_id = ? AND ok = 0", (run_id,)
    ).fetchone()[0]
    nieznane = conn.execute(
        "SELECT COUNT(*) FROM calls WHERE run_id = ? AND "
        "(usage_status IN ('pending','unknown') OR "
        "(usage_status = 'legacy' AND ok = 0 AND tokens_in = 0 AND tokens_out = 0))",
        (run_id,),
    ).fetchone()[0]
    niepewne = conn.execute(
        "SELECT COUNT(*) FROM calls WHERE run_id = ? AND ok = 1 "
        "AND price_verified = 0", (run_id,)
    ).fetchone()[0]
    ogon = ""
    if nieudane:
        ogon += " — nieudanych prob: %d" % nieudane
    if nieznane:
        ogon += " — prob o NIEZNANYM koszcie: %d" % nieznane
        ogon += " — dodatkowa rezerwacja: $%.4f" % max(
            0, db.budget_used(conn, run_id=run_id) - row['total'])
    if niepewne:
        ogon += " — po stawce niepotwierdzonej: %d" % niepewne
    print(f"\n== koszt przebiegu: ${row['total']:.4f} w {row['n']} wywołaniach{ogon} ==", flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
