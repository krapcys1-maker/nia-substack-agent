"""Czytanie stron przeglądarką — tam, gdzie zwykły HTTP nie wystarcza.

Substack renderuje treść JavaScriptem: w HTML-u jest 148 KB, a czytelnego
tekstu 371 znaków, bo post siedzi w blobie JSON. Zwykły pobieracz zobaczy
pustą skorupę.

Czytamy WYŁĄCZNIE publiczne strony, bez logowania i bez sesji. Agent otwiera
je tak jak każdy czytelnik. Publikowanie, komentowanie i polubienia nie
istnieją w tym pliku i nie powstaną bez osobnej decyzji właściciela.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any

import config

READ_TIMEOUT_MS = 45_000
SETTLE_MS = 2_500

# Plik sesji. Powstaje, gdy WŁAŚCICIEL zaloguje się własnoręcznie w otwartym
# oknie. Hasło nie przechodzi przez ten kod ani przez nic, co ja czytam.
# `.gitignore` obejmuje ten wzorzec od początku projektu.
SESSION_FILE = config.DATA_DIR / "storage-state.json"


CDP_PORT = 9222

# Ciasteczko realnej sesji Substacka. `substack.lli` to tylko podpowiedź
# "kiedyś tu byłeś" i ustawia się także anonimowo — pierwsza wersja kontroli
# opierała się na tekście strony, publiczna strona główna ją przechodziła
# i skrypt zapisał pustą sesję jako zalogowaną.
SESSION_COOKIE = "substack.sid"


# Ile dni przed wygaśnięciem sesji zaczynamy ostrzegać. Ciasteczko żyje ~90 dni,
# więc dwa tygodnie to spokojny zapas na to, żeby właściciel zdążył zareagować.
OSTRZEGAJ_PONIZEJ_DNI = 14


def wlasciwe_konto(page) -> bool:
    """Czy jestesmy na WLASCIWYM koncie tuz przed publikacja.

    Automatyzacja przegladarki potrafi trafic w cudze okno albo w sesje sprzed
    przelogowania. Tresc opublikowana z niewlasciwego konta jest bledem, ktorego
    nie da sie cofnac w oczach tych, ktorzy ja zobaczyli — wiec pytamy o
    tozsamosc, zamiast zakladac.
    """
    kto = api_json(page, f"/api/v1/user/{PROFIL_HANDLE}/public_profile")
    ok = isinstance(kto, dict) and kto.get("handle") == PROFIL_HANDLE
    if not ok:
        print(f"  ! NIE TO KONTO albo brak sesji: {str(kto)[:80]}", flush=True)
    return ok


DZIENNIK = config.DATA_DIR / "dziennik.jsonl"


# --- SLAD PRZEBIEGU: dane, ktore trzeba bylo odtwarzac z timestampow ---------
#
# 30 sierpnia szukalem, czemu komentarze pod notkami przepadaja w 30 procentach.
# Odpowiedz siedziala w POZYCJI W SERII: pierwsza akcja psula sie w 10
# procentach, druga w 31, czwarta w 50. Zeby to zobaczyc, musialem grupowac
# wpisy dziennika po odstepach czasu i zgadywac, gdzie konczy sie jedna seria,
# a zaczyna druga — czyli rekonstruowac coś, co agent WIEDZIAL w chwili
# dzialania i wyrzucal.
#
# Teraz to zapisuje. Trzy pola, kazde odpowiada na pytanie, ktore juz raz
# musialem zadac danym:
#   `nr_w_serii`      — ktora to akcja tego rodzaju w TYM przebiegu,
#   `od_poprzedniej_s`— ile sekund realnie minelo (nie ile wylosowano),
#   `pod_rzad_zle`    — ile porazek tego rodzaju poszlo bezposrednio przed ta.
#
# Ostatnie pole sluzy takze do reakcji W TRAKCIE, nie tylko do analizy pozniej
# — patrz `pod_rzad_nieudanych` i `run.rytm`.
_W_SERII: dict[str, int] = {}
_OSTATNIA: dict[str, float] = {}
_POD_RZAD_ZLE: dict[str, int] = {}


def pod_rzad_nieudanych(rodzaj: str) -> int:
    """Ile porazek tego rodzaju poszlo BEZPOSREDNIO po sobie w tym przebiegu.

    Zerowane przez kazde powodzenie. Czyta to `run.rytm`, zeby zwolnic tempo
    zanim przebieg przepali kolejny oplacony tekst.
    """
    return _POD_RZAD_ZLE.get(rodzaj, 0)


def slad_przebiegu() -> dict[str, dict]:
    """Podsumowanie tego, co ten proces zrobil — do wypisania na koncu."""
    return {r: {"prob": n, "pod_rzad_zle": _POD_RZAD_ZLE.get(r, 0)}
            for r, n in sorted(_W_SERII.items())}


# JEDYNY POWOD, KTORY MOWI COS O HOSCIE. Stoi jako stala, bo czytaja go DWA
# miejsca — `dopisz_wynik` przy zapisie i `hosty_gdzie_komentarz_nie_wchodzi`
# przy czytaniu — a rozjechanie sie tych dwoch napisow wylaczyloby pamiec
# martwych hostow po cichu.
POWOD_HOST_NIE_POKAZUJE = "Substack nie potwierdzil, ze wyszlo"


def dopisz_wynik(rodzaj: str, wynik: dict, **szczegoly) -> None:
    # DLACZEGO 1200 ZNAKOW, A NIE 300 — TO BYL BLAD POMIARU, NIE OSZCZEDNOSC.
    #
    # Do 2 wrzesnia 2026 zapisywalismy `tekst[:300]`. Zmierzone tego dnia na
    # profilu: mediana notki ma 333 znaki, maksimum 456 — czyli dziennik urywal
    # KAZDA drugą notke, i to zawsze na koncu.
    #
    # Koniec jest tu najdrozszym miejscem. Forma PYTANIE stawia pytanie
    # w OSTATNIEJ linii, po podaniu faktu. Zliczylem wiec pytajniki w dzienniku,
    # dostalem zero na 53 notki i oglosilem wlascicielowi, ze forma jest martwa.
    # Byla to nieprawda: na profilu wisi nasza wlasna notka konczaca sie
    # „How far back does your work chat history go?". Pomiar mierzyl obciecie,
    # nie tresc — a wniosek z niego byl gotowa decyzja o przepisaniu promptow.
    #
    # 1200 znakow miesci notke (do 64 slow) i komentarz (do 70 slow) w calosci,
    # z zapasem. Linia JSONL jest tania; falszywy wniosek nie jest.
    """Jeden wpis na dzialanie — takze wtedy, gdy sie NIE UDALO, i z powodem.

    DWIE DZIURY NARAZ, obie groznie ciche.

    Pierwsza: wpis do dziennika stal WEWNATRZ `try`, a wyjatek byl lapany
    nizej. Akcja, ktora wywalila sie bledem, nie zostawiala w dzienniku
    ZADNEGO sladu — nie wiedzielismy nie tylko dlaczego, ale i ze w ogole
    byla. Licznik wolumenow liczylby wiec z danych, ktore same gubia porazki.

    Druga: gdy nie znalezlismy przycisku wysylki, kod nie wchodzil w zadna
    galez i przechodzil dalej w milczeniu. To najczestsza realna awaria przy
    obcym interfejsie i akurat ona nie zostawiala niczego.

    Zapis jest IDEMPOTENTNY: pierwszy, ktory zdazy, wygrywa. Dzieki temu
    sciezka sukcesu zapisuje szczegoly, a `finally` domyka tylko te przebiegi,
    ktore do niej nie doszly.

    KAZDA PORAZKA NIESIE TEZ, O KIM MOWI — pole `o_hoscie`. Patrz komentarz
    ponizej i `hosty_gdzie_komentarz_nie_wchodzi`.
    """
    if wynik.get("_zapisane"):
        return
    wynik["_zapisane"] = True
    udane = bool(wynik.get("wyslane") or wynik.get("zrobione"))
    if not udane:
        szczegoly["powod"] = (
            wynik.get("blad")
            or ("nie znalazlem przycisku wysylki"
                if wynik.get("przycisk_widoczny") is False else "")
            or POWOD_HOST_NIE_POKAZUJE)

        # O KIM MOWI TA PORAZKA: o CELU czy o NAS.
        #
        # Odkad porazki trafiaja do dziennika z KAZDEJ galezi (a nie tylko
        # z „kliknelismy i nie potwierdzilo"), sam wpis z adresem przestal byc
        # dowodem na cokolwiek po stronie hosta. Timeout, padnieta sesja albo
        # zamkniety Chrome to awaria po NASZEJ stronie — a
        # `hosty_gdzie_komentarz_nie_wchodzi` czytalo je tak samo jak odmowe
        # Substacka i po dwoch takich wpisach kasowalo host na zawsze.
        #
        # POTRZEBNE SA DWA FAKTY, NIE JEDEN, i pierwsza wersja tej poprawki
        # miala tylko pierwszy.
        #
        # `klikniete` ustawia sciezka publikacji TUZ PO nacisnieciu przycisku
        # wysylki — a wiec ZANIM ktokolwiek zapytal Substacka, czy komentarz
        # wisi. Samo to znaczy tyle, ze przegladarka zyla, strona sie wczytala,
        # pole bylo, tekst wszedl i przycisk zostal nacisniety.
        #
        # `potwierdzenie_odpowiedzialo` ustawia sie dopiero wtedy, gdy
        # `potwierdz_komentarz` / `potwierdz_odpowiedz` WROCILO — z odpowiedzia
        # „jest" albo „nie ma". Te funkcje robia do czterech `api_json`, kazde
        # to `page.goto` z timeoutem, i zadne z nich niczego nie polyka. Wyjatek
        # w ich trakcie (timeout nawigacji, wyzwanie Cloudflare,
        # `TargetClosedError`, gdy wlasciciel zamknie swojego Chrome'a — a agent
        # podpina sie wlasnie do jego okna) leci przez `except` do `finally`,
        # ktory od 1 wrzesnia zapisuje BEZWARUNKOWO.
        #
        # Zlozenie tych dwoch zmian dalo skutek odwrotny do zamierzonego: kazdy
        # taki wyjatek szedl do dziennika jako `o_hoscie=True`, czyli jako dowod
        # przeciwko hostowi. Zmierzone side-by-side na atrapie Playwrighta,
        # wyjatek w `page.goto` PO klknieciu: dwa wpisy, jeden host, i
        # `publikacja-c.example` uznany za martwy na 14 dni, choc nie powiedzial nam
        # ani slowa. Petla domykala sie sama — sito w `run.py` wycina cele
        # z takiego hosta PRZED platna ocena, wiec host nie mial jak zdobyc
        # wpisu `udane=True`, ktory jako jedyny kasuje go z listy.
        #
        # `o_hoscie` ma znaczyc JEDNA rzecz: „kliknelismy, a Substack tego nie
        # pokazuje". To odpowiedz z potwierdzania, nie sam fakt klikniecia.
        # Wyjatek w trakcie potwierdzania to „nie wiem", a „nie wiem" nie jest
        # dowodem. Wszystko inne (brak pola, brak przycisku, wyjatek) nadal
        # zostawia slad i nadal liczy sie do `pod_rzad_zle` i do raportu, ale
        # nie skresla hosta.
        szczegoly["klikniete"] = bool(wynik.get("klikniete"))
        szczegoly["o_hoscie"] = bool(wynik.get("klikniete")
                                     and wynik.get("potwierdzenie_odpowiedzialo"))

    # SLAD PRZEBIEGU — patrz komentarz przy `_W_SERII`. Liczymy TU, a nie w
    # `run.py`, zeby zadna sciezka publikacji nie mogla o tym zapomniec:
    # kazde dzialanie i tak przechodzi przez ten jeden zapis.
    _W_SERII[rodzaj] = _W_SERII.get(rodzaj, 0) + 1
    szczegoly["nr_w_serii"] = _W_SERII[rodzaj]
    poprzednia = _OSTATNIA.get(rodzaj)
    if poprzednia is not None:
        szczegoly["od_poprzedniej_s"] = round(time.time() - poprzednia)
    _OSTATNIA[rodzaj] = time.time()
    szczegoly["pod_rzad_zle"] = _POD_RZAD_ZLE.get(rodzaj, 0)
    # Zerowane KAZDYM powodzeniem: interesuje nas seria, nie suma dobowa.
    _POD_RZAD_ZLE[rodzaj] = 0 if udane else _POD_RZAD_ZLE.get(rodzaj, 0) + 1
    if not udane and _POD_RZAD_ZLE[rodzaj] >= 2:
        print("  [slad] %s: %d porazki pod rzad w tym przebiegu — zwalniam"
              % (rodzaj, _POD_RZAD_ZLE[rodzaj]), flush=True)

    zapisz_w_dzienniku(rodzaj, udane=udane, **szczegoly)


def zapisz_w_dzienniku(rodzaj: str, **szczegoly) -> None:
    """Dziennik DZIALAN, nie wywolan modelu.

    Baza zapisuje, ile kosztowalo mysleenie. Nie zapisuje, CO z tego poszlo
    w swiat, do kogo i czy sie udalo — a po dwoch dniach to jest jedyne pytanie,
    ktore ma znaczenie: gdzie agent sie pomylil i co poprawic.

    Jeden wiersz na dzialanie, w pliku, ktory da sie czytac oczami i skryptem.
    Nigdy nie przerywa dzialania: dziennik, ktory wywala agenta, byl by gorszy
    od jego braku.
    """
    import json as _json
    from datetime import datetime, timezone

    try:
        wpis = {"kiedy": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "rodzaj": rodzaj, **szczegoly}
        DZIENNIK.parent.mkdir(parents=True, exist_ok=True)
        with open(DZIENNIK, "a", encoding="utf-8") as f:
            f.write(_json.dumps(wpis, ensure_ascii=False) + "\n")
    except Exception:
        pass


def z_dziennika_dzis() -> dict[str, int]:
    """Ile komentarzy i polubien poszlo dzis — wedlug naszego zapisu.

    Notki potrafimy policzyc u zrodla, komentarzy i polubien NIE. Kanal profilu
    zwraca wylacznie notki — sprawdzone na zywo: jedenascie pozycji, ani jednej
    z `post_id` — a szesc innych endpointow naszych komentarzy nie oddaje wcale.

    To swiadomy wyjatek od zasady „rzeczywistosc jest zrodlem prawdy", zrobiony
    tam, gdzie rzeczywistosci nie da sie zapytac. Bez niego kazdy przebieg widzial
    zero i bral pelny dzienny budzet od nowa, wiec ochrona przed wystawieniem
    normy drugi raz dzialala TYLKO dla notek. Dziennik przezywa restart, wiec
    daje te sama gwarancje tam, gdzie Substack milczy.

    Liczymy wylacznie dzialania UDANE i wylacznie dzisiejsze, w UTC — tak samo
    jak liczy je `ile_dzis_wystawione`, zeby obie polowy licznika mierzyly ten
    sam dzien.
    """
    import json as _json
    from datetime import datetime, timezone

    dzis = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    # SUBSKRYPCJE I OBSERWACJE TEZ, i to jest poprawka z 30 sierpnia 2026.
    #
    # Tych dwoch pozycji licznik NIE ZWRACAL, wiec `run.py` liczyl
    #     zostalo = budzet - juz.get("subskrypcje", 0)
    # czyli budzet minus zero — PELNY dzienny przydzial w KAZDYM przebiegu. A
    # rozdzielnik ma `max(1, round(...))`, zeby male budzety nie zaokraglaly sie
    # do zera, wiec budzet 1 zamienial sie w jedna subskrypcje NA PRZEBIEG.
    #
    # ZMIERZONE na odtworzonych budzetach: 25 i 26 sierpnia plan 1, wykonanie 2;
    # 29 sierpnia plan 1, wykonanie 3. Srednio 140% planu. Kazda subskrypcja to
    # poczta do skrzynki wlasciciela, wiec to nie jest drobiazg kosmetyczny —
    # i jest to DOKLADNIE ta sama wada, ktora tego samego dnia znalazlem przy
    # notkach: licznik nie widzial dzialania, wiec ochrona przed powtorzeniem
    # normy nie dzialala dla niego wcale.
    ile = {"komentarze": 0, "lajki": 0, "restacki": 0, "notki": 0,
           "subskrypcje": 0, "follow": 0}
    # Klucz po lewej to `rodzaj` z dziennika, po prawej nazwa z budzetu.
    nazwa = {"komentarz": "komentarze", "polubienie": "lajki",
             "restack": "restacki", "notka": "notki",
             "subskrypcja": "subskrypcje", "obserwacja": "follow"}
    try:
        if not DZIENNIK.exists():
            return ile
        for linia in DZIENNIK.read_text(encoding="utf-8").splitlines():
            linia = linia.strip()
            if not linia:
                continue
            try:
                wpis = _json.loads(linia)
            except ValueError:
                continue          # jedna uszkodzona linia nie psuje calej reszty
            if not isinstance(wpis, dict):
                continue
            if not str(wpis.get("kiedy", "")).startswith(dzis):
                continue
            if not wpis.get("udane"):
                continue
            klucz = nazwa.get(wpis.get("rodzaj"))
            if klucz:
                ile[klucz] += 1
    except Exception:
        pass                      # licznik nie moze zatrzymac przebiegu
    return ile


def naprawde_wyslac(wyslij: bool, co: str) -> bool:
    """Ostatnie sito przed KAZDYM dzialaniem widocznym publicznie.

    DRY_RUN blokowal wywolania modeli, ale NIE blokowal przegladarki — wiec
    przebieg "na sucho" na serwerze nie napisal ani slowa, a mimo to polubil
    dwa cudze posty. Tryb, ktory nazywa sie suchym, musi byc suchy takze wobec
    swiata zewnetrznego, inaczej jest pulapka.
    """
    if wyslij and config.DRY_RUN:
        print(f"  [{co}] DRY_RUN — NIE wysylam, mimo ze proszono", flush=True)
        return False
    return wyslij


def zalogowany(context) -> bool:
    """Twarde sprawdzenie: albo jest ciasteczko sesji, albo go nie ma."""
    return any(c.get("name") == SESSION_COOKIE for c in context.cookies())


def dni_do_wygasniecia() -> int | None:
    """Ile dni zostało sesji. None, gdy sesji nie ma wcale."""
    import datetime
    import json

    if not SESSION_FILE.exists():
        return None
    dane = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
    for ciastko in dane.get("cookies", []):
        if ciastko.get("name") != SESSION_COOKIE:
            continue
        koniec = ciastko.get("expires", -1)
        if not koniec or koniec < 0:
            return 0
        wygasa = datetime.datetime.fromtimestamp(koniec, datetime.timezone.utc)
        return (wygasa - datetime.datetime.now(datetime.timezone.utc)).days
    return None


def wymagaj_sesji() -> None:
    """Sprawdza sesję przed pracą i mówi wprost, gdy trzeba się zalogować.

    Agent chodzi bez nadzoru, więc cicha awaria na wygasłej sesji byłaby
    najgorszym wariantem: przez tydzień nic by nie wychodziło, a log milczał.
    """
    dni = dni_do_wygasniecia()
    if dni is None:
        raise SystemExit(
            "Brak sesji Substacka.\n"
            "Uruchom Chrome z portem debugowania, zaloguj się i wykonaj:\n"
            "  python agent-v2/browser.py sesja"
        )
    if dni <= 0:
        raise SystemExit(
            f"Sesja Substacka wygasła. Zaloguj się ponownie i wykonaj:\n"
            "  python agent-v2/browser.py sesja"
        )
    if dni <= OSTRZEGAJ_PONIZEJ_DNI:
        print(
            f"  [uwaga] sesja Substacka wygasa za {dni} dni — warto odnowić",
            flush=True,
        )


CHROME_PROFILE = Path.home() / "substack-agent-chrome"
CHROME_SCIEZKI = (
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path("/usr/bin/google-chrome"),
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
)


def _chrome_odpowiada() -> bool:
    import httpx

    try:
        httpx.get(f"http://localhost:{CDP_PORT}/json/version", timeout=3)
        return True
    except Exception:
        return False


def uruchom_chrome() -> bool:
    """Otwiera Chrome na trwałym profilu agenta, jeśli jeszcze nie działa.

    Trwały profil znaczy, że logowanie przeżywa restarty — po pierwszym razie
    właściciel nie zobaczy już formularza logowania ani CAPTCHY.

    Chrome jest uruchamiany zwykłym poleceniem, BEZ flag automatyzacji. To jest
    istotne: gdy przeglądarkę startował Playwright, reCAPTCHA zapętlała się
    nawet dla człowieka.
    """
    import subprocess

    if _chrome_odpowiada():
        return True
    exe = next((s for s in CHROME_SCIEZKI if s.exists()), None)
    if exe is None:
        print("  Nie znalazłem Chrome. Uruchom go sam z portem "
              f"--remote-debugging-port={CDP_PORT}", flush=True)
        return False
    CHROME_PROFILE.mkdir(parents=True, exist_ok=True)
    subprocess.Popen(
        [str(exe), f"--remote-debugging-port={CDP_PORT}",
         f"--user-data-dir={CHROME_PROFILE}", "https://substack.com/home"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for _ in range(20):
        time.sleep(1)
        if _chrome_odpowiada():
            return True
    return False


def rozgrzej(context) -> bool:
    """Pozwala Cloudflare wydać zgodę dla adresu, z którego akurat działamy.

    Z centrum danych pierwsze wejście dostaje stronę "Just a moment…", bo
    `cf_clearance` z sesji właściciela było wydane na jego domowy adres. To NIE
    jest obchodzenie zabezpieczenia — przeciwnie, wchodzimy wprost na chroniony
    adres i pozwalamy wyzwaniu zrobić swoje. Prawdziwa przeglądarka rozwiązuje
    je w kilka sekund i dostaje własną zgodę.

    Bez tego kroku z serwera nie działa nic; z nim działa kompozytor i wejścia
    na adresy API.
    """
    page = context.new_page()
    try:
        page.goto(f"https://substack.com/api/v1/user/{config.SUBSTACK_HANDLE}"
                  "/public_profile",
                  timeout=READ_TIMEOUT_MS * 2, wait_until="domcontentloaded")
        for _ in range(8):
            page.wait_for_timeout(3000)
            if "Just a moment" not in page.inner_text("body")[:60]:
                return True
        print("  [rozgrzewka] Cloudflare nie ustąpił", flush=True)
        return False
    except Exception as exc:
        print(f"  [rozgrzewka] {type(exc).__name__}: {exc}"[:120], flush=True)
        return False
    finally:
        page.close()


# ZNAKI TYPOGRAFICZNE, KTORE WSTAWIA EDYTOR SUBSTACKA. Piszemy prosty apostrof,
# a ProseMirror zapisuje typograficzny — wiec `doesn't` u nas i `doesn’t` u nich
# to dla porownania dwa rozne napisy.
_ZAMIANY = {
    chr(0x2018): "'", chr(0x2019): "'",          # ' '
    chr(0x201C): '"', chr(0x201D): '"',          # " "
    chr(0x2013): "-", chr(0x2014): "-",          # – —
    chr(0x2026): "...",                          # …
    chr(0x00A0): " ", chr(0x2009): " ",          # spacje nielamiace i cienkie
    chr(0x2032): "'", chr(0x02BC): "'",          # ′ ʼ
}


def plaski(tekst: str) -> str:
    """Tekst sprowadzony do znakow, ktore SAMI piszemy — do POROWNYWANIA.

    ODKRYTE POMIAREM 31 sierpnia 2026. Dwanascie komentarzy na sto i dwanascie
    odpowiedzi na piecdziesiat trzy konczylo sie w dzienniku jako „Substack nie
    potwierdzil, ze wyszlo". Sprawdzone na zywo: WSZYSTKIE TRZY sprawdzone
    odpowiedzi BYLY na Substacku. Nie zawodzilo wystawianie, tylko
    POTWIERDZANIE.

    Potwierdzenie porownuje doslownie pierwsze 60 znakow naszego tekstu z tym,
    co oddaje API. Edytor Substacka zamienia proste apostrofy na typograficzne,
    wiec `doesn't` nigdy nie trafialo w `doesn’t`.

    ZMIERZONE, nie zgadniete:
        nieudane: 75% ma apostrof albo cudzyslow w pierwszych 60 znakach
        udane:    17%

    KOSZT TEGO BLEDU BYL PODWOJNY. Dziennik pokazywal porazki, ktorych nie bylo,
    wiec wykonanie planu wygladalo gorzej niz jest — a to ta sama liczba, na
    ktorej stoi alarm „agent robi mniej, niz deklaruje".

    Nie grozilo natomiast podwojnym komentarzem: `juz_sie_odezwalismy` pyta
    Substacka, a nie naszej ksiegowosci.
    """
    wynik = " ".join(str(tekst or "").split())
    for znak, zamiast in _ZAMIANY.items():
        wynik = wynik.replace(znak, zamiast)
    return wynik


def api_json(page, sciezka: str, baza: str | None = None) -> Any:
    """Czyta API WCHODZĄC na adres, zamiast wołać `fetch` ze strony.

    Sprawdzone na serwerze: z centrum danych `fetch` z wnętrza strony wraca 403
    ze stroną wyzwania, a zwykłe wejście na ten sam adres oddaje JSON. Różnica
    jest w tym, jak Cloudflare ocenia zapytanie w tle wobec nawigacji.

    Działa tak samo na komputerze właściciela, więc mamy jedną drogę, nie dwie.
    """
    import json as _json

    # Adresy dziela sie na dwa swiaty i pomylenie ich daje bledy trudne do
    # zdiagnozowania: /api/v1/posts nalezy do PUBLIKACJI
    # (your-handle.substack.com), a /api/v1/reader/* i /api/v1/user/*
    # do serwisu (substack.com). Potwierdzanie artykulu pytalo pod zlym adresem
    # i zawsze odpowiadalo "nie ma", wiec udana publikacja raportowalaby porazke.
    #   - substack.com          : /api/v1/reader/*, /api/v1/user/*
    #   - NASZA publikacja       : /api/v1/posts (lista naszych artykulow)
    #   - CUDZA publikacja       : /api/v1/posts/<slug>, /api/v1/post/<id>/comments
    # Dlatego adres bazowy jest jawnym argumentem, a nie domyslem. Poprzednia
    # wersja zawsze pytala substack.com i cicho zwracala "nie znalazlem".
    baza = baza or "https://substack.com"
    page.goto(f"{baza}{sciezka}", timeout=READ_TIMEOUT_MS * 2,
              wait_until="domcontentloaded")
    page.wait_for_timeout(1200)
    tekst = page.inner_text("body").strip()
    if tekst.startswith("Just a moment"):
        page.wait_for_timeout(6000)
        tekst = page.inner_text("body").strip()
    try:
        return _json.loads(tekst)
    except ValueError:
        return None


def podlacz_sie():
    """Podłącza się do Chrome'a, którego uruchomił i zalogował WŁAŚCICIEL.

    Dlaczego tak, a nie przez uruchomienie przeglądarki przez Playwrighta:
    Playwright startuje Chrome z flagami automatyzacji, a reCAPTCHA ocenia całą
    sesję, nie samo kliknięcie — więc odrzuca ją niezależnie od tego, kto klika.
    Właściciel nie mógł przejść CAPTCHY, mimo że jest człowiekiem.

    Tutaj przeglądarkę uruchamia człowiek i człowiek się loguje. W momencie
    przechodzenia CAPTCHY to jest zwykły Chrome — nic nie jest ukrywane ani
    podszywane. Agent podłącza się do gotowej, zalogowanej sesji.
    """
    from playwright.sync_api import sync_playwright

    # NA SERWERZE PODŁĄCZAMY SIĘ DO PRAWDZIWEGO CHROME'A, tak samo jak na
    # komputerze właściciela. Chrome chodzi tam na wirtualnym ekranie jako usługa
    # `nia-chrome`, a właściciel zalogował się w nim własnoręcznie.
    #
    # Dlaczego nie przeglądarka bezgłowa: sprawdzone na żywo tego samego wieczoru.
    # Ta sama sesja, ten sam adres, ten sam serwer — publikacja przez prawdziwego
    # Chrome'a kończy się kodem 200, a przez bezgłowego Chromium notka po prostu
    # nie powstaje. Cloudflare rozpoznaje tryb bezgłowy po odcisku przeglądarki.
    if config.TRYB_SERWERA and _chrome_odpowiada():
        p = sync_playwright().start()
        browser = p.chromium.connect_over_cdp(f"http://localhost:{CDP_PORT}")
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        return p, browser, context

    if config.TRYB_SERWERA or not _chrome_odpowiada():
        if not SESSION_FILE.exists():
            # KOMUNIKAT ZALEZY OD TEGO, GDZIE JESTES. Ten warunek laczy DWIE
            # rozne sytuacje: „jestem na serwerze bez pliku sesji" i „jestem
            # na swoim komputerze i nie odpalilem Chrome'a z portem". Do
            # 2026-09-03 obie dostawaly te sama rade o kopiowaniu na serwer
            # — czyli w PIERWSZYM kroku instrukcji zakladania sesji czlowiek
            # na wlasnym laptopie czytal o serwerze.
            if config.TRYB_SERWERA:
                raise SystemExit(
                    "Tryb serwerowy wymaga pliku sesji, a tego pliku nie ma.\n"
                    f"  {SESSION_FILE}\n"
                    "\n"
                    "Zaloz sesje na komputerze z ekranem i skopiuj plik tutaj.\n"
                    "Instrukcja: docs/INSTALL.md, krok 5."
                )
            raise SystemExit(
                "Chrome z portem debugowania nie odpowiada, a pliku sesji tez\n"
                "nie ma — agent nie ma sie do czego podlaczyc.\n"
                "\n"
                "Na WLASNYM komputerze (tego wlasnie potrzebujesz teraz):\n"
                f"  1. uruchom Chrome z portem: --remote-debugging-port={CDP_PORT}\n"
                "  2. zaloguj sie w nim na Substacku RECZNIE\n"
                "  3. wroc tutaj i powtorz: python agent-v2/browser.py sesja\n"
                "\n"
                "Na SERWERZE: ustaw NIA_SERVER=1 i skopiuj gotowy plik sesji do\n"
                f"  {SESSION_FILE}\n"
                "\n"
                "Dlaczego recznie: automatyczne logowanie zapetla CAPTCHE i jest\n"
                "w tym kodzie odradzone. Patrz docs/INSTALL.md, krok 5."
            )
        p = sync_playwright().start()
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            storage_state=str(SESSION_FILE),
            user_agent=config.FETCH_USER_AGENT,
            viewport={"width": 1440, "height": 900},
            locale="en-US",   # interfejs po angielsku, niezależnie od serwera
        )
        rozgrzej(context)
        return p, browser, context

    if not _chrome_odpowiada():
        print("  Chrome nie działa — otwieram go na profilu agenta.", flush=True)
        if not uruchom_chrome():
            raise SystemExit("Nie udało się otworzyć Chrome'a.")

    p = sync_playwright().start()
    try:
        browser = p.chromium.connect_over_cdp(f"http://localhost:{CDP_PORT}")
    except Exception as exc:
        p.stop()
        raise SystemExit(
            f"Chrome działa, ale nie mogę się podłączyć ({type(exc).__name__})."
        ) from exc
    context = browser.contexts[0] if browser.contexts else browser.new_context()
    return p, browser, context


def sprawdz_sesje() -> None:
    """Czy Chrome właściciela jest zalogowany i co agent w nim widzi."""
    p, browser, context = podlacz_sie()
    page = context.new_page()
    try:
        # USUNIETO 2026-08-20 blok wklejony tu omylkowo z `wystaw_notke`.
        # Odwolywal sie do `wyslij`, `tekst` i `wynik`, ktore w tej funkcji nie
        # istnieja, wiec `python agent-v2/browser.py sesja` konczylo sie
        # NameError przy pierwszej linii `try`.
        #
        # To nie byla usterka kosmetyczna: TA WLASNIE KOMENDA jest cytowana
        # w alarmie wysylanym do wlasciciela, gdy sesja wygasa. Procedura
        # ratunkowa nie dzialala, a dowiedzielibysmy sie o tym dopiero
        # w chwili, gdy naprawde bylaby potrzebna.
        page.goto("https://substack.com/home", timeout=READ_TIMEOUT_MS,
                  wait_until="domcontentloaded")
        page.wait_for_timeout(SETTLE_MS)
        text = page.inner_text("body")
        zalogowany = "sign in" not in text.lower()[:300] and len(text) > 1200
        print(f"  sesja: {'ZALOGOWANA' if zalogowany else 'NIEZALOGOWANA'}"
              f"   tekst={len(text)} znaków")
        if zalogowany:
            SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
            context.storage_state(path=str(SESSION_FILE))
            dni = dni_do_wygasniecia()
            print(f"  stan sesji zapisany: {SESSION_FILE}")
            if dni is not None:
                print(f"  wazna jeszcze {dni} dni")
    finally:
        page.close()
        browser.close()
        p.stop()


def sprawdz_serwer() -> None:
    """Odpowiada na JEDNO pytanie: czy zapisana sesja żyje z adresu tego serwera.

    Niczego nie publikuje, nie polubia i nie zmienia. Sam odczyt, bo to pytanie
    trzeba rozstrzygnąć ZANIM zbudujemy na nim resztę: jeśli Substack odrzuca
    sesję z innego adresu, cała droga przez przeglądarkę wymaga przemyślenia od
    nowa i lepiej wiedzieć to teraz niż po tygodniu pracy.
    """
    import os

    os.environ["AGENT_V2_SERVER"] = "1"
    config.TRYB_SERWERA = True

    dni = dni_do_wygasniecia()
    print(f"  plik sesji: {'jest' if SESSION_FILE.exists() else 'BRAK'}"
          f"{f', wazna {dni} dni' if dni is not None else ''}", flush=True)

    p, browser, context = podlacz_sie()
    page = context.new_page()
    try:
        page.goto("https://substack.com/", timeout=READ_TIMEOUT_MS * 2,
                  wait_until="domcontentloaded")
        page.wait_for_timeout(SETTLE_MS + 3000)
        ciastko = zalogowany(context)
        print(f"  ciasteczko sesji: {'JEST' if ciastko else 'BRAK'}", flush=True)

        # Twardszy dowód niż ciasteczko: czy zalogowane API nas rozpoznaje.
        kto = api_json(page, f"/api/v1/user/{config.SUBSTACK_HANDLE}/public_profile")
        print(f"  odpowiedz API: {kto if not isinstance(kto, dict) else {k: kto.get(k) for k in ('id', 'name')}}",
              flush=True)
        page.goto("https://substack.com/", timeout=READ_TIMEOUT_MS * 2,
                  wait_until="domcontentloaded")
        page.wait_for_timeout(SETTLE_MS + 3000)

        widzi_kompozytor = "on your mind" in page.inner_text("body").lower()
        print(f"  kompozytor notek widoczny: {widzi_kompozytor}", flush=True)

        if ciastko and isinstance(kto, dict) and kto.get("id") and widzi_kompozytor:
            print("\n  WYNIK: sesja dziala z tego adresu. Mozna isc dalej.", flush=True)
        else:
            print("\n  WYNIK: sesja NIE dziala stad. NIE budujemy dalej na tej"
                  " drodze — trzeba przemyslec logowanie na serwerze.", flush=True)
    finally:
        page.close()
        browser.close()
        p.stop()


def zaloguj() -> None:
    """Otwiera prawdziwe okno przeglądarki i czeka, aż właściciel się zaloguje.

    Substack loguje magicznym linkiem na e-mail, więc i tak musi to zrobić
    człowiek — agent na serwerze nie ma dostępu do skrzynki. Po zalogowaniu
    zapisujemy stan sesji do pliku i od tej pory agent otwiera przeglądarkę
    już zalogowaną.
    """
    from playwright.sync_api import sync_playwright

    print("Otwieram okno przeglądarki. Zaloguj się na Substacku.")
    print("Gdy zobaczysz swoje konto, wróć tutaj i naciśnij Enter.\n")
    with sync_playwright() as p:
        # Prawdziwy Chrome, nie okrojone Chromium Playwrighta. Wbudowana kopia
        # nie ma części komponentów i reCAPTCHA potrafi się w niej zapętlić
        # nawet dla człowieka — to nie blokada, tylko niekompletna przeglądarka.
        # Logowanie i tak wykonuje właściciel własnoręcznie.
        try:
            browser = p.chromium.launch(headless=False, channel="chrome")
            print("   (używam Twojego Chrome)\n")
        except Exception:
            browser = p.chromium.launch(headless=False)
            print("   (nie znalazłem Chrome, używam wbudowanej przeglądarki)\n")
        context = browser.new_context(viewport={"width": 1400, "height": 950})
        page = context.new_page()

        # NAJPIERW strona główna, nie formularz logowania. Pokazywanie formularza
        # komuś, kto jest już zalogowany, potrafi zapętlić CAPTCHĘ — nie ma czego
        # potwierdzać. Jeśli sesja istnieje, nie ma się w ogóle po co logować.
        #
        # USUNIETO 2026-08-20 ten sam blok wklejony omylkowo z `wystaw_notke`,
        # co w `sprawdz_sesje` — odwolywal sie do nieistniejacych tu nazw
        # `wyslij`, `tekst` i `wynik`. Obie funkcje ratunkowe byly martwe.
        page.goto("https://substack.com/home", timeout=READ_TIMEOUT_MS,
                  wait_until="domcontentloaded")
        page.wait_for_timeout(SETTLE_MS)
        if zalogowany(context):
            print("   Jesteś już zalogowany — logowanie niepotrzebne.\n")
        else:
            print("   Nie jesteś zalogowany. Zaloguj się w otwartym oknie.\n")
            page.goto("https://substack.com/sign-in", timeout=READ_TIMEOUT_MS)
            while True:
                input("   [naciśnij Enter, gdy będziesz zalogowany] ")
                if zalogowany(context):
                    print("   Widzę sesję. Zapisuję.\n")
                    break
                print("   Nadal nie widzę sesji (brak ciasteczka substack.sid).")
                print("   Dokończ logowanie w oknie i naciśnij Enter jeszcze raz.")
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        context.storage_state(path=str(SESSION_FILE))
        context.close()
        browser.close()
    print(f"\nSesja zapisana: {SESSION_FILE}")
    print("Plik jest w .gitignore. Wylogowanie się na Substacku go unieważnia.")


def rozpoznanie() -> None:
    """Sprawdza, czy agent umie się poruszać po zalogowanym koncie.

    WYŁĄCZNIE ogląda i raportuje. Nie klika 'opublikuj', nie wysyła komentarza,
    nie polubia. Ten kod ma się dowiedzieć, czy nawigacja jest wykonalna —
    zanim ktokolwiek zdecyduje, że agent ma coś wysłać.
    """
    from playwright.sync_api import sync_playwright

    if not SESSION_FILE.exists():
        raise SystemExit(
            f"Brak pliku sesji ({SESSION_FILE}).\n"
            "Uruchom najpierw:  python agent-v2/browser.py zaloguj"
        )

    # Ekrany edytora rysują się długo, więc czekamy dłużej niż przy czytaniu.
    checks = [
        ("feed — skąd brać posty", "https://substack.com/home", 6000),
        ("notki — feed", "https://substack.com/notes", 6000),
        ("panel publikacji", f"https://{config.SUBSTACK_HANDLE}.substack.com/publish/home", 9000),
        ("edytor artykułu", f"https://{config.SUBSTACK_HANDLE}.substack.com/publish/post", 12000),
        ("skrzynka", "https://substack.com/inbox", 6000),
    ]
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            storage_state=str(SESSION_FILE), viewport={"width": 1400, "height": 1200}
        )
        page = context.new_page()
        for name, url, wait in checks:
            try:
                page.goto(url, timeout=READ_TIMEOUT_MS, wait_until="domcontentloaded")
                page.wait_for_timeout(wait)
                text = page.inner_text("body")
                posts = len({u for u in page.eval_on_selector_all(
                    'a[href*="/p/"]', "e=>e.map(x=>x.href)")})
                buttons = [b.strip() for b in page.eval_on_selector_all(
                    "button, a[role=button]", "e=>e.map(x=>x.innerText)") if b.strip()]
                pola = page.eval_on_selector_all(
                    "[contenteditable=true], textarea, input[type=text]",
                    "e=>e.map(x=>x.getAttribute('placeholder')||x.getAttribute('aria-label')||'(bez etykiety)')",
                )
                print(f"  {name:26} tekst={len(text):>6}  postów={posts:>3}", flush=True)
                if buttons:
                    uniq = list(dict.fromkeys(buttons))[:10]
                    print(f"     przyciski: {' | '.join(uniq)[:150]}", flush=True)
                if pola:
                    print(f"     pola do pisania: {' | '.join(pola[:6])[:150]}", flush=True)
            except Exception as exc:
                print(f"  {name:26} BŁĄD {type(exc).__name__}: {exc}"[:160], flush=True)
        # Zapisujemy stan po każdej pracy: Substack odświeża ciasteczko przy
        # aktywności, więc regularne używanie konta samo przesuwa datę ważności.
        context.storage_state(path=str(SESSION_FILE))
        context.close()
        browser.close()


# UCHWYT KONTA MA JEDNO ZRODLO. Stala tu druga, niezalezna kopia
# `config.SUBSTACK_HANDLE` — uzywana w jedenastu miejscach, podczas gdy config
# byl uzywany w szesnastu. Zmiana jednego z nich dawala bota, ktory PUBLIKUJE
# na jednym koncie, a CZYTA profil drugiego, i nic tego nie zglaszalo.
#
# Zostaje jako alias, zeby nie przepisywac jedenastu wywolan, ale wskazuje na
# config. Nie da sie juz ustawic jednego bez drugiego.
PROFIL_HANDLE = config.SUBSTACK_HANDLE

# Substack tłumaczy cudze treści na język interfejsu i podmienia je w HTML-u.
# Nasza notka po angielsku wyświetlała się po polsku, a odpowiedź Anglika też.
# Agent czytający stronę odpisałby po polsku komuś, kto pisał po angielsku —
# więc treści bierzemy WYŁĄCZNIE z API, gdzie `body` jest oryginałem, a pole
# `language` mówi, w jakim języku naprawdę napisano.
def _plaskie(galaz: dict) -> list[dict]:
    """Rozwija gałąź wątku do płaskiej listy komentarzy."""
    out: list[dict] = []
    stos = [galaz]
    while stos:
        w = stos.pop()
        if not isinstance(w, dict):
            continue
        c = w.get("comment") or w
        if isinstance(c, dict) and c.get("body"):
            out.append(c)
        stos.extend(w.get("descendantComments") or w.get("children") or [])
    return out


def _kiedy(c: dict) -> float:
    from datetime import datetime
    try:
        return datetime.fromisoformat(
            str(c.get("date", "")).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def ile_dzis_wystawione() -> dict[str, int]:
    """Ile notek, komentarzy i polubien poszlo dzisiaj.

    WSZYSTKO LICZYMY Z DZIENNIKA, I TO JEST POPRAWKA Z 30 SIERPNIA 2026.

    Notki szly wczesniej z kanalu profilu, bo „rzeczywistosc jest lepszym
    zrodlem niz wlasna ksiegowosc". Zalozenie bylo takie, ze na tym profilu
    publikuje wylacznie bot. Nieprawda: wlasciciel pisze notki RECZNIE, a kanal
    profilu nie odroznia jego notek od naszych — wiec kazda notka wlasciciela
    po cichu kasowala jedna notke bota.

    ZMIERZONE, nie wydedukowane. 29 sierpnia kanal pokazywal piec notek, z
    czego dwie byly bota; 28 sierpnia szesc, z czego jedna. Licznik meldowal
    „dzienny przydzial juz wyczerpany" przy normie piec, a bot wystawil dwie.
    Przez pietnascie dni dalo to 2,9 notki dziennie zamiast pieciu — 57 procent
    normy. Wlasciciel opisal to jako dwa osobne fakty („dopisywalem notki" i
    „on prawie nic nie dal"), a to byl jeden fakt.

    Dziennik zapisuje wylacznie WLASNE dzialania, wiec atrybucja jest w nim z
    definicji poprawna. Przezywa restart — to wlasnie ta gwarancja, dla ktorej
    komentarze i polubienia liczyly sie z niego od poczatku. Notki byly jedyna
    kategoria czytana skadinad i jedyna, ktora sie rozjezdzala.

    ODCZYT Z SUBSTACKA ZOSTAJE, ale juz nie decyduje — sluzy do KONTROLI. Gdy
    liczby sie roznia, mowimy o tym glosno w logu, zamiast po cichu zabierac
    botowi przydzial. Roznica jest zwykle miara recznej pracy wlasciciela i to
    jest uzyteczna informacja, a nie usterka.
    """
    from datetime import datetime, timezone

    dzis = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    wynik = z_dziennika_dzis()          # <- to jest teraz zrodlo decyzji
    wymagaj_sesji()
    p, browser, context = podlacz_sie()
    page = context.new_page()
    try:
        profil = api_json(page, f"/api/v1/user/{PROFIL_HANDLE}/public_profile")
        if not isinstance(profil, dict) or not profil.get("id"):
            return wynik
        # Filtr typu — taki sam, jak w trzech pozostalych miejscach pytajacych
        # ten endpoint (szukaj `types%5B%5D=note`). To jedno go nie mialo.
        feed = api_json(page, f"/api/v1/reader/feed/profile/{profil['id']}"
                              "?types%5B%5D=note") or {}
        na_profilu = 0
        for x in feed.get("items", []):
            c = (x or {}).get("comment") or {}
            if not str(c.get("date", "")).startswith(dzis):
                continue
            if not c.get("post_id"):
                na_profilu += 1
        # KONTROLA, NIE DECYZJA. Nadmiar to notki wlasciciela pisane recznie i
        # ma zostac widoczny, bo to jedyne miejsce, w ktorym ta praca sie
        # ujawnia. Wczesniej ten sam nadmiar cicho zabieral botowi przydzial.
        if na_profilu != wynik["notki"]:
            print("  [licznik] na profilu %d notek, bot wystawil %d"
                  " — roznica %+d to praca reczna wlasciciela"
                  % (na_profilu, wynik["notki"], na_profilu - wynik["notki"]),
                  flush=True)
        return wynik
    except Exception as exc:
        print(f"  (nie policzylem dzisiejszych: {type(exc).__name__})", flush=True)
        return wynik
    finally:
        page.close()
        browser.close()
        p.stop()


def statystyki_pozycji(pozycje: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Pobiera statystyki NASZYCH tresci — jedna przegladarka na cala liste.

    `pozycje` to lista slownikow {"rodzaj": "notka"|"restack"|"artykul",
    "id": <numer>, "tekst": <skrot, opcjonalnie>}.

    ODPOWIADA NA PYTANIE, KTOREGO DOTAD NIE UMIELISMY ZADAC: ile wejsc mial
    konkretny wpis, ile z nich zamienilo sie w polubienie, i ilu ludzi z tego
    JEDNEGO wpisu zaczelo nas obserwowac albo subskrybowac. Dziennik wiedzial
    tylko, ze cos wystawilismy.

    Zrodlo: `/api/v1/note_stats/c-<id>` — ten sam adres, ktorego uzywa przycisk
    „View stats" pod nasza notka. Sprawdzone na zywym koncie 25 sierpnia:
    notka 321505067 miala 17 wyswietlen, z tego feed 8, permalinki 3, profil 1;
    odbiorcy: niezwiazani 8, subskrybenci 1, obserwujacy 0; interakcje 6, czyli
    4 polubienia i 2 odpowiedzi. Opis karty interakcji wprost wymienia wsrod
    nich subskrypcje i obserwacje, wiec przypisanie subskrybenta do KONKRETNEJ
    notki jest tu mozliwe — a nigdzie indziej w API nie jest.

    Statystyki odswiezaja sie mniej wiecej raz na godzine, wiec pomiar
    powtarzamy; `statystyki.zapisz` trzyma HISTORIE, nie ostatnia wartosc.

    Restack liczy sie jako notka, bo Substack nadaje mu wlasny numer notki.
    """
    import statystyki

    wymagaj_sesji()
    p, browser, context = podlacz_sie()
    page = context.new_page()
    zebrane: list[dict[str, Any]] = []
    try:
        if not pozycje:
            # Lista skladana W TEJ SAMEJ sesji, zeby nie otwierac przegladarki
            # dwa razy — start Chromium to sekundy, a robimy to co przebieg.
            pozycje = nasze_pozycje_do_pomiaru(page)
        # TABELA ZRODEL RUCHU — JEDYNE PRAWDZIWE PRZYPISANIE, JAKIE ISTNIEJE.
        #
        # Pole `signups_within_1_day`, ktorym mierzylismy „subskrypcje
        # z artykulu", okazalo sie 2 wrzesnia 2026 OKNEM CZASOWYM: zestawione
        # z prawdziwa lista subskrybentow trafialo co do sztuki w liczbe osob,
        # ktore zapisaly sie NAZAJUTRZ po wysylce — kimkolwiek by je
        # przyprowadzil. Substack liczy przypisanie osobno, w panelu, i za
        # 30 dni mowi: 6 zapisow, 5 z NOTEK, jeden „Substack other".
        #
        # Czytamy to TUTAJ, bo sesja, strona i baza naszej publikacji sa juz
        # otwarte, a wolajacy (`run.py`) trzyma ten pomiar pod `try` z zasada
        # „pomiar NIGDY nie zabija przebiegu". W tym samym miejscu powstaja
        # `wzrost.jsonl` i `czytelnicy.jsonl`, wiec trzy szeregi maja wspolna
        # os czasu. Zero wywolan modelu, dwie nawigacje.
        try:
            zapisz_zrodla_ruchu(page)
        except Exception as exc:
            print("  [zrodla] nie odczytalem: %s" % type(exc).__name__, flush=True)
        for poz in pozycje:
            ident = str(poz.get("id") or "").strip()
            if not ident:
                continue
            rodzaj = str(poz.get("rodzaj") or "notka")
            # ARTYKUL MA WLASNE ZRODLO I NIE PYTAMY O NIEGO DRUGI RAZ.
            #
            # Zmierzone na zywo 30 sierpnia: `/api/v1/note_stats/p-<id>` oddaje
            # dla artykulu JEDNA karte (sam podglad wpisu), a dla notki PIEC
            # (wyswietlenia, powierzchnie, odbiorcy, interakcje). Odpowiedz jest
            # poprawna i pusta — wiec przedrostek `p-` dawal piec rekordow
            # z samymi zerami, co jest gorsze niz brak pomiaru: wyglada na dane.
            #
            # Prawdziwe liczby leza w panelu wydawcy i sa juz w `poz`, wzięte
            # JEDNYM zapytaniem dla wszystkich artykulow naraz.
            if rodzaj == "artykul":
                rekord = poz.get("statystyki")
                if not rekord:
                    continue
                statystyki.zapisz(rodzaj, ident, rekord,
                                  tekst=poz.get("tekst") or "")
                rekord = dict(rekord, id=ident, rodzaj=rodzaj)
                zebrane.append(rekord)
                print("  [statystyki] artykul %s: %s wysw, %s polub, %s odp,"
                      " %s klik, %s zapisow"
                      % (ident, rekord.get("wyswietlenia"),
                         rekord.get("polubienia"), rekord.get("odpowiedzi"),
                         rekord.get("klikniecia_w_link"),
                         rekord.get("subskrypcje")), flush=True)
                continue
            # NOTKI, KOMENTARZE I ODPOWIEDZI — wspolna koncowka `c-`.
            # Artykul odszedl wyzej: jego statystyk tu NIE MA (sprawdzone
            # 30 sierpnia — `p-<id>` oddaje jedna karte podgladu i zero liczb).
            try:
                dane = api_json(page, f"/api/v1/note_stats/c-{ident}")
            except Exception as exc:
                # Pojedyncza pozycja, ktorej nie da sie odczytac, NIE moze
                # zabrac calej reszty — inaczej jeden skasowany wpis kosztuje
                # nas pomiar wszystkich pozostalych.
                print(f"  [statystyki] {ident}: {type(exc).__name__}", flush=True)
                continue
            if not isinstance(dane, dict):
                continue
            rekord = statystyki.z_kart(dane)
            statystyki.zapisz(rodzaj, ident, rekord, tekst=poz.get("tekst") or "")
            rekord["id"] = ident
            rekord["rodzaj"] = rodzaj
            zebrane.append(rekord)
            print("  [statystyki] %s %s: %s wysw, %s polub, %s odp, %s subskr"
                  % (rodzaj, ident, rekord.get("wyswietlenia"),
                     rekord.get("polubienia"), rekord.get("odpowiedzi"),
                     rekord.get("subskrypcje")), flush=True)
    finally:
        page.close()
        browser.close()
        p.stop()
    return zebrane


CZYTELNICY = config.DATA_DIR / "czytelnicy.jsonl"

# Odnosniki, ktore sa nawigacja Substacka, a nie ludzmi. Bez tej listy kazdy
# zrzut mialby w sobie „Explore" i „Dashboard" jako naszych obserwujacych.
_NIE_LUDZIE = {"explore", "dashboard", "profile", "create", "more", "home",
               "notes", "chat", "search", "settings", "inbox"}


def _ludzie_z_zakladki_ze_stanem(page) -> tuple[list[dict[str, str]], bool]:
    """Kto jest na tej zakladce ORAZ czy zakladke w ogole udalo sie odczytac.

    DWA WYNIKI, BO PUSTA LISTA ZNACZY DZIS DWIE ROZNE RZECZY: „na zakladce
    nie ma nikogo" i „zakladka nie odpowiedziala". Bez tego rozroznienia zrzut
    z padnietym odczytem zapisuje sie jak zrzut z pustego konta — patrz
    `zapisz_czytelnikow`.
    """
    wynik: dict[str, str] = {}
    try:
        odnosniki = page.locator('a[href^="/@"]').all()
    except Exception:
        return [], False
    for a in odnosniki[:200]:
        try:
            href = a.get_attribute("href") or ""
            nazwa = " ".join((a.inner_text() or "").split())[:80]
        except Exception:
            continue
        uchwyt = href.split("/@", 1)[-1].split("/")[0].split("?")[0].strip()
        if not uchwyt or uchwyt.lower() in _NIE_LUDZIE:
            continue
        if uchwyt.lower() == str(PROFIL_HANDLE).lower():
            continue          # my sami
        # Pierwsza napotkana nazwa wygrywa: ta sama osoba bywa odnosnikiem
        # dwa razy (awatar bez tekstu i nazwa), a awatar oddaje pusty napis.
        if uchwyt not in wynik or (not wynik[uchwyt] and nazwa):
            wynik[uchwyt] = nazwa
    return [{"uchwyt": u, "nazwa": n or u} for u, n in wynik.items()], True


def _ludzie_z_zakladki(page) -> list[dict[str, str]]:
    """Sama lista ludzi z zakladki. Dla wolajacych, ktorych stan nie obchodzi."""
    return _ludzie_z_zakladki_ze_stanem(page)[0]


def kto_nas_czyta(page=None) -> dict[str, Any]:
    """KTO nas obserwuje i subskrybuje — imiennie i z data.

    PO CO, SKORO ZNAMY JUZ LICZBY. Bo liczba nie da sie z niczym polaczyc.
    31 sierpnia konto uroslo z czterech subskrybentow do osmiu, a system wykonal
    w tym czasie okolo pieciuset dzialan — i nie ma sposobu, zeby powiedziec,
    ktore z nich cokolwiek przynioslo. Majac liste z DATA, mozna zapytac wprost:
    czy ci, ktorzy nas zaobserwowali, pojawili sie wczesniej wsrod naszych
    komentarzy i polubien. To roznica miedzy „komentowanie dziala" jako
    przekonaniem a jako pomiarem.

    DROGA JEST TA SAMA, CO PRZY KOPII SUBSKRYBENTOW: wlasny panel, wlasna
    sesja. Cztery zgadniete adresy API (`/user/<id>/followers` i podobne)
    oddaly puste odpowiedzi i na tym poprzestalem — powtarzane sondowanie
    nieudokumentowanych adresow to jest dokladnie to, co nasz wlasny kod
    nazywa scrapingiem.

    Zapisujemy CALY zrzut przy kazdym wywolaniu, nie roznice. Zrzuty sa male
    (kilkanascie osob), a roznica policzona pozniej jest odwracalna — roznica
    zapisana zamiast stanu juz nie.

    KTORA LISTE NAPRAWDE ODCZYTALISMY — POLE `odczytane`. Obserwujacych
    bierzemy z zakladki otwartej domyslnie, a subskrybentow dopiero po
    KLIKNIECIU w druga zakladke. Gdy pekalo samo klikniecie, obserwujacy byli
    juz w wyniku, wiec zrzut zapisywal sie z pusta lista subskrybentow
    i wygladal na udany. `wzajemnosc.czytelnicy` czyta te zrzuty po NUMERZE
    („kto doszedl po zrzucie zerowym, ten przyszedl po naszej akcji") — gdyby
    okrojony byl zrzut PIERWSZY, caly komplet subskrybentow dostalby
    `pierwszy_zrzut > 0` i raport oglosilby ich jako pozyskanych naszym
    dzialaniem. Odpowiedz na pytanie wlasciciela „skad biora sie czytelnicy"
    bylaby wtedy zbudowana na jednym nieudanym kliknieciu.

    DWIE ZAKLADKI SA ROZLACZNE, I DLATEGO LICZNIK JEST WIEKSZY OD LISTY.
    Zmierzone 1 wrzesnia 2026 na siedmiu parach zrzutow: subskrybenci zgadzaja
    sie z `subscriberCountNumber` co do jednego we WSZYSTKICH siedmiu parach,
    a obserwujacy sa krotsi o 1, potem stale o 2 (8/7, 9/7, 11/9, 11/9, 11/9,
    11/9, 12/10). Rozstrzyga to jeden przypadek: „Leonard" ma w dzienniku
    zdarzenie `follow` z 2026-08-31T06:25:10 (a wiec obserwuje), licznik
    `followerCount` podskoczyl wtedy z 8 na 9 i juz nie spadl — a na zakladce
    „Followers" nie ma go w ZADNYM z szesciu pozniejszych zrzutow, za to jako
    `leonard896188` stoi na zakladce „Subscribers" tej samej strony. Uchwyt
    ma, konta nie skasowal, nasz filtr go nie tyka. Kto obserwuje I
    subskrybuje, tego Substack pokazuje wylacznie w „Subscribers" — obie
    listy sa w kazdym zrzucie ROZLACZNE (10 + 9 osob, zero czesci wspolnej).
    Brakujaca dwojka nie jest wiec nienazwana: to dwie osoby policzone przez
    `followerCount`, a wypisane na drugiej zakladce.

    NIE DOKLADAMY Z TEGO POWODU ANI JEDNEGO ZAPYTANIA. Nie ma czego doczytac:
    to nie paginacja (lista rosnie swobodnie 7 -> 10, a niedobor stoi na 2)
    ani konta usuniete. Dodatkowe wejscia na kolejne strony byly by ruchem po
    dane, ktore juz mamy — a regulamin Substacka zakazuje `crawls/scrapes/
    spiders` wprost.
    """
    wlasny = page is None
    if wlasny:
        wymagaj_sesji()
        p_, br_, ctx = podlacz_sie()
        page = ctx.new_page()
    # `odczytane` to lista zakladek, ktore NAPRAWDE odpowiedzialy. Pusta lista
    # znaczy „nie wiemy nic", a nie „konto jest puste".
    wynik: dict[str, Any] = {"obserwujacy": [], "subskrybenci": [],
                             "odczytane": [], "blad": None}
    try:
        page.goto(f"https://substack.com/@{PROFIL_HANDLE}/followers",
                  timeout=READ_TIMEOUT_MS * 2, wait_until="domcontentloaded")
        page.wait_for_timeout(SETTLE_MS + 5000)

        # Zakladka otwarta domyslnie to „Followers" — bierzemy ja bez klikania.
        wynik["obserwujacy"], ok = _ludzie_z_zakladki_ze_stanem(page)
        if ok:
            wynik["odczytane"].append("obserwujacy")

        for napis in ("Subscribers", "Subskrybenci"):
            zakladka = page.get_by_role("tab", name=napis, exact=False).first
            if zakladka.count() == 0:
                continue
            zakladka.click(timeout=10_000)
            page.wait_for_timeout(5000)
            wynik["subskrybenci"], ok = _ludzie_z_zakladki_ze_stanem(page)
            if ok:
                wynik["odczytane"].append("subskrybenci")
            break
        else:
            # BRAK ZAKLADKI TO NIE JEST WYJATEK, WIEC NIKT SIE O NIM NIE
            # DOWIADYWAL. Petla konczyla sie po cichu, `blad` zostawal `None`,
            # a zrzut szedl na dysk z pusta lista subskrybentow.
            wynik["blad"] = "nie ma zakladki Subscribers"
            print("  [czytelnicy] %s" % wynik["blad"], flush=True)
    except Exception as exc:
        wynik["blad"] = f"{type(exc).__name__}: {exc}"[:200]
        print("  [czytelnicy] %s" % wynik["blad"], flush=True)
    finally:
        if wlasny:
            page.close()
            br_.close()
            p_.stop()
    return wynik


def zapisz_czytelnikow(page=None) -> dict[str, Any] | None:
    """Zrzut listy czytelnikow do pliku, jeden wiersz na wywolanie.

    ZRZUT OKROJONY ZAPISUJE SIE Z ETYKIETA, A NIE JAKO PELNY. Stary warunek
    („zwroc None, gdy jest blad I obie listy sa puste") przepuszczal na dysk
    zrzut, w ktorym obserwujacy sa, a subskrybentow nie ma, bo peklo samo
    klikniecie w druga zakladke. Taki wiersz jest nieodroznialny od dnia, w
    ktorym konto nie mialo subskrybentow — a `wzajemnosc` policzylaby z niego,
    ze wszyscy subskrybenci „pojawili sie po naszej akcji". Zapisujemy wiec
    pole `odczytane` z nazwami zakladek, ktore naprawde odpowiedzialy.

    ZGODNOSC WSTECZ. Siedem zrzutow z 31 sierpnia i 1 wrzesnia tego pola nie
    ma i nie dostanie. Ich brak znaczy „nie wiem, ktora liste odczytano" —
    czyli dokladnie tyle, ile wiedzielismy o nich przedtem. Czytajacy ma
    sprawdzac `"subskrybenci" in zrzut.get("odczytane", [...])`, a nie zakladac
    pustke, gdy klucza nie ma.

    ZAPISUJEMY TEZ `blad`, I TO JEST POPRAWKA Z 1 WRZESNIA 2026. Zrzut mowil,
    KTORE zakladki odpowiedzialy, i nie mowil, DLACZEGO ta druga nie
    odpowiedziala. `kto_nas_czyta` rozroznia trzy przyczyny — brak zakladki
    „Subscribers", wyjatek nawigacji i niepowodzenie odczytu odnosnikow —
    a wszystkie trzy wygladaly w pliku tak samo: krotsza lista `odczytane`.
    Bez powodu nie da sie odroznic awarii jednorazowej od zmiany w interfejsie
    Substacka, czyli od rzeczy, ktora wymaga poprawki kodu.

    TRZY STANY, NIE DWA. `"blad": null` znaczy „bylo dobrze"; `"blad": "..."`
    znaczy „bylo tak"; BRAK KLUCZA znaczy „nie wiadomo" i tak nalezy czytac
    siedem istniejacych zrzutow. Czytajacy ma pytac
    `zrzut.get("blad", "nie wiadomo")`, a nie `zrzut.get("blad")` — to drugie
    zamienia siedem „nie wiem" w siedem „bez bledu".
    """
    import json as _json
    from datetime import datetime, timezone

    NOWA_LINIA = chr(10)
    kto = kto_nas_czyta(page)
    odczytane = list(kto.get("odczytane") or [])
    # NIC NIE ODCZYTANE TO NIE JEST POMIAR. Wczesniej bramka pytala o `blad`
    # i o puste listy; teraz pyta wprost o to, co nas obchodzi — czy
    # ktorakolwiek zakladka w ogole odpowiedziala. Konto, ktore naprawde nie ma
    # nikogo, przechodzi (obie zakladki odczytane, obie puste); przebieg, w
    # ktorym strona nie wstala, nie przechodzi i nie zostawia sladu.
    if not odczytane:
        return None
    zrzut = {
        "kiedy": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "obserwujacy": kto["obserwujacy"],
        "subskrybenci": kto["subskrybenci"],
        "odczytane": odczytane,
        # ZAWSZE, TAKZE GDY JEST `None`. Pole zapisane tylko przy awarii nie
        # dawalo by trzeciego stanu: brak klucza znaczylby wtedy i „stary
        # zrzut", i „nowy zrzut bez bledu". Zapisane zawsze — brak klucza
        # dotyczy wylacznie siedmiu zrzutow sprzed tej zmiany.
        "blad": kto.get("blad"),
    }
    try:
        CZYTELNICY.parent.mkdir(parents=True, exist_ok=True)
        with CZYTELNICY.open("a", encoding="utf-8") as f:
            f.write(_json.dumps(zrzut, ensure_ascii=False) + NOWA_LINIA)
    except OSError as exc:
        print("  [czytelnicy] nie zapisalem: %s" % type(exc).__name__, flush=True)
    return zrzut


# --- KOGO MY OBSERWUJEMY -----------------------------------------------------
#
# DRUGA STRONA `czytelnicy.jsonl`: tamten plik mowi, KTO CZYTA NAS, ten — KOGO
# CZYTAMY MY. Powstal, bo blok obserwacji losowal z calej historii komentarzy
# BEZ ZADNEGO ODSIEWU i regularnie trafial na kogos, kogo juz obserwujemy.
#
# ZMIERZONE 1 wrzesnia 2026 na zywym koncie (odczyt, nic nie klikniete):
# `substack.com/@your-handle/following` oddaje 26 uchwytow, a
# `visibleSubscriptionsCount` z `/api/v1/user/<handle>/public_profile` = 26 —
# co do jednego tyle samo, wiec ta strona NIE dokleja zadnych podpowiedzi
# „kogo obserwowac" i `_ludzie_z_zakladki` czyta z niej dokladnie liste
# obserwowanych. Historia komentarzy miala tego dnia 92 hosty; osiem z nich
# pokrywalo sie z ta lista juz po samym TANIM mapowaniu `host.split(".")[0]`,
# a naprawde wiecej (`www.wlasnadomena.example` -> `autor1`,
# `moneywithkatie.substack.com` -> `katiegattitassin`). Przy budzecie okolo
# 0,43 obserwacji na dobe i pokryciu 8 z 92 hostow oznacza to mniej wiecej
# jedna zbedna probe na 27 dni — do 1 wrzesnia zapisywana jako PORAZKA.
#
# DLACZEGO PAMIEC NA DYSKU, A NIE PYTANIE DO SUBSTACKA PRZY KAZDYM PRZEBIEGU.
# Bo lista i tak przychodzi z czegos, co juz chodzi: `nasze_pozycje_do_pomiaru`
# otwiera sesje przy KAZDYM pomiarze i czyta juz zakladke `/followers`
# (`zapisz_czytelnikow`). Dolozenie tam jednego `goto` na `/following` kosztuje
# ulamek tego, co osobna sesja przegladarki w bloku obserwacji (start Chrome to
# sekundy, a blok ma dobowy budzet jednej sztuki). Blok obserwacji nie wchodzi
# wiec do sieci ANI RAZU — czyta ten plik.
#
# PAMIEC SIE SAMA LECZY. Zrzut przepisuje uchwyty w calosci (odobserwowanie
# przez wlasciciela znika z pamieci samo), a `obserwuj_profil` dopisuje kazdego,
# kogo wlasnie zaobserwowal albo u kogo zastal „Unfollow" — wiec nawet przy
# pustym pliku pomylka kosztuje jedno wejscie na profil, raz.
OBSERWOWANI = config.DATA_DIR / "kogo_obserwujemy.json"


def kogo_obserwujemy() -> dict[str, Any]:
    """Kogo juz obserwujemy — Z DYSKU, BEZ SIECI.

    `uchwyty`: {uchwyt: kiedy} — stan przepisany ze strony `/following` plus to,
    czego dowiedzielismy sie po drodze.
    `hosty`:   {host: uchwyt} — mapa hosta z historii komentarzy na uchwyt,
    ktorej NIE DA SIE wyprowadzic ze zrzutu. Bez niej `www.wlasnadomena.example` nie ma
    jak trafic w `autor1`, bo tanie `host.split(".")[0]` dziala wylacznie
    dla adresow w domenie Substacka, a i tam bywa mylne
    (`publikacja-b.substack.com` to konto `publikacja-b`).
    """
    import json as _json

    pusto: dict[str, Any] = {"zrzut": None, "uchwyty": {}, "hosty": {}}
    try:
        if not OBSERWOWANI.exists():
            return pusto
        dane = _json.loads(OBSERWOWANI.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return pusto
    if not isinstance(dane, dict):
        return pusto
    return {"zrzut": dane.get("zrzut"),
            "uchwyty": dict(dane.get("uchwyty") or {}),
            "hosty": dict(dane.get("hosty") or {})}


def _zapisz_kogo_obserwujemy(pamiec: dict[str, Any]) -> None:
    """Nigdy nie przerywa dzialania — to pamiec pomocnicza, nie warunek pracy."""
    import json as _json

    try:
        OBSERWOWANI.parent.mkdir(parents=True, exist_ok=True)
        OBSERWOWANI.write_text(
            _json.dumps(pamiec, ensure_ascii=False, indent=1), encoding="utf-8")
    except OSError as exc:
        print("  [obserwowani] nie zapisalem: %s" % type(exc).__name__,
              flush=True)


def zapamietaj_obserwowanego(uchwyt: str, host: str | None = None) -> None:
    """Dopisuje JEDNEGO do pamieci — po udanej obserwacji albo po zastaniu
    „Unfollow" w menu.

    Dwa fakty maja dwoch wlascicieli i dlatego funkcja bierze oba osobno:
    `obserwuj_profil` wie, KOGO wlasnie obserwujemy (uchwyt), a blok w `run.py`
    wie, Z KTOREGO HOSTA ten uchwyt sie wzial. Sam uchwyt nie wystarczy do
    odsiania puli, bo pula jest lista hostow.
    """
    from datetime import datetime, timezone

    uchwyt = (uchwyt or "").strip().lstrip("@")
    if not uchwyt:
        return
    pamiec = kogo_obserwujemy()
    pamiec["uchwyty"][uchwyt] = datetime.now(timezone.utc).isoformat(
        timespec="seconds")
    host = (host or "").strip().lower().rstrip("/")
    if host:
        pamiec["hosty"][host] = uchwyt
    _zapisz_kogo_obserwujemy(pamiec)


def czy_juz_obserwujemy(host: str, pamiec: dict[str, Any] | None = None) -> bool:
    """Czy ten HOST wskazuje kogos, kogo juz obserwujemy. Bez sieci.

    PRZY WATPLIWOSCI ODPOWIADA „NIE" — i to jest wybor, nie przeoczenie. Cena
    pomylki jest niesymetryczna: falszywe „tak" kasuje z puli kogos, kogo
    moglibysmy zaobserwowac (i nie dowiemy sie o tym nigdy), falszywe „nie"
    kosztuje jedno wejscie na profil, po ktorym `obserwuj_profil` odczytuje
    prawde z menu i dopisuje ja do pamieci.
    """
    pamiec = kogo_obserwujemy() if pamiec is None else pamiec
    host = (host or "").strip().lower().rstrip("/")
    if not host:
        return False
    if host in pamiec.get("hosty", {}):
        return True
    if host.endswith(".substack.com"):
        return host.split(".")[0] in pamiec.get("uchwyty", {})
    return False


def odswiez_kogo_obserwujemy(page) -> int | None:
    """Przepisuje pamiec ze strony `/@my/following`. Wymaga OTWARTEJ sesji.

    Zwraca liczbe odczytanych osob albo None przy awarii odczytu.

    PUSTY ODCZYT NIE KASUJE PAMIECI — ta sama zasada, co przy `zapisz_
    czytelnikow`: zapisane zero wygladaloby jak konto, ktore nie obserwuje
    nikogo, i jednym zapisem odblokowaloby cala pule.
    """
    from datetime import datetime, timezone

    try:
        page.goto(f"https://substack.com/@{PROFIL_HANDLE}/following",
                  timeout=READ_TIMEOUT_MS * 2, wait_until="domcontentloaded")
        page.wait_for_timeout(SETTLE_MS + 5000)
        ludzie = _ludzie_z_zakladki(page)
    except Exception as exc:
        print("  [obserwowani] %s" % f"{type(exc).__name__}: {exc}"[:120],
              flush=True)
        return None
    if not ludzie:
        print("  [obserwowani] zakladka nic nie oddala — zostawiam pamiec",
              flush=True)
        return 0
    teraz = datetime.now(timezone.utc).isoformat(timespec="seconds")
    stara = kogo_obserwujemy()
    swiezi = {x["uchwyt"]: stara["uchwyty"].get(x["uchwyt"]) or teraz
              for x in ludzie}
    # HOSTY, KTORYCH UCHWYT ZNIKNAL ZE ZRZUTU, WYPADAJA RAZEM Z NIM. Inaczej
    # odobserwowanie przez wlasciciela zostawaloby w pamieci na zawsze i host
    # nie mialby jak wrocic do puli.
    hosty = {h: u for h, u in stara["hosty"].items() if u in swiezi}
    _zapisz_kogo_obserwujemy({"zrzut": teraz, "uchwyty": swiezi,
                              "hosty": hosty})
    return len(swiezi)


WZROST = config.DATA_DIR / "wzrost.jsonl"


def zapisz_wzrost_konta(profil: dict[str, Any]) -> dict[str, Any] | None:
    """Ilu nas czyta DZISIAJ — jedna linia na pomiar, historia zostaje.

    CZEGO NIE MIELISMY. System zapisywal subskrypcje przypisane do KONKRETNEGO
    wpisu (pole `subskrypcje` w statystykach) i wlasne wychodzace subskrypcje
    („my subskrybujemy kogos", 18 wpisow w dzienniku). LACZNEJ liczby naszych
    subskrybentow w czasie NIE zapisywal nikt. Jedyny slad to kopia listy
    z 23 sierpnia 2026 — cztery osoby — i nic pozniej.

    Krzywa 4 -> 8 z panelu Substacka zyla wylacznie u Substacka. Cel calego
    systemu to wzrost konta, a jedyna liczba, ktora ten wzrost mierzy wprost,
    nie byla nigdzie zapisywana.

    ZERO DODATKOWYCH ZAPYTAN. `/api/v1/user/<handle>/public_profile` i tak
    wolamy przy kazdym pomiarze, zeby dostac numer profilu. Te liczby juz
    w tej odpowiedzi sa.

    DWIE LICZBY NA SUBSKRYBENTOW, BO SUBSTACK PODAJE DWIE. Zmierzone
    31 sierpnia: panel wydawcy mowil 8, `subscriberCountNumber` 7, a zakladka
    „Subskrybenci" wymieniala siedem osob — osma jest najpewniej wlasciciel
    konta. Zapisujemy obie zamiast wybierac, ktora jest „prawdziwa": roznica
    jest stala i sama w sobie informuje.
    """
    import json as _json
    from datetime import datetime, timezone

    NOWA_LINIA = chr(10)
    if not isinstance(profil, dict):
        return None
    # ZERO Z NIEUDANEGO ODCZYTU TO NIE JEST POMIAR. W szeregu czasowym wiersz
    # z samymi zerami jest nie do odroznienia od dnia, w ktorym wszyscy odeszli
    # — a audyt policzyl z takich dwoch wierszy „subskrybentow -7" godzine po
    # tym, jak to napisalem.
    #
    # Te sama pulapke ominalem w `zapisz_czytelnikow` („porazka nie dopisuje
    # pustego zrzutu") i wpadlem w nia obok, bo pisalem te dwie funkcje osobno.
    # Regula jest jedna: brak danych ma wygladac na brak danych, nie na wynik.
    if not any(profil.get(k) for k in ("subscriberCountNumber", "followerCount",
                                       "rough_num_free_subscribers_int",
                                       "visibleSubscriptionsCount")):
        return None
    stan = {
        "kiedy": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "subskrybenci": int(profil.get("subscriberCountNumber") or 0),
        "subskrybenci_darmowi": int(
            profil.get("rough_num_free_subscribers_int") or 0),
        "obserwujacy": int(profil.get("followerCount") or 0),
        # NASZE wychodzace subskrypcje i rekomendacje — to samo zrodlo, a bez
        # nich nie widac, czy wzrost idzie za nasza aktywnoscia, czy mimo niej.
        "nasze_subskrypcje": int(profil.get("visibleSubscriptionsCount") or 0),
        "nasze_rekomendacje": int(
            profil.get("primaryPublicationRecommendationCount") or 0),
    }
    try:
        WZROST.parent.mkdir(parents=True, exist_ok=True)
        with WZROST.open("a", encoding="utf-8") as f:
            f.write(_json.dumps(stan, ensure_ascii=False) + NOWA_LINIA)
    except OSError as exc:
        # Zapis jest premia, pomiar wazniejszy — tak samo jak przy autorze
        # polubionego wpisu.
        print("  [wzrost] nie zapisalem: %s" % type(exc).__name__, flush=True)
    return stan


# --- SKAD BIORA SIE ZAPISY: TABELA ZRODEL Z PANELU ---------------------------
#
# `wzrost.jsonl` mowi ILU nas czyta. Ten plik mowi SKAD przyszli — i to jest
# jedyna liczba w calym systemie, ktora wiaze subskrybenta ze SCIEZKA, a nie
# z okienkiem czasu.
ZRODLA = config.DATA_DIR / "zrodla.jsonl"

# Pod tymi kluczami panel trzyma liste zrodel. Dwa pierwsze sa ZMIERZONE
# 2 wrzesnia 2026 (`rows` w `visitor_sources`, `sourceMetrics`
# w `growth/sources`); reszta to zapas na przemianowanie pola — sprawdzamy po
# kolei, zamiast zakladac jeden ksztalt na zawsze.
_KLUCZE_LISTY = ("rows", "sourceMetrics", "sources", "results", "data", "items")

# DWA KSZTALTY LICZB, BO PANEL PODAJE JE NA DWA SPOSOBY. `visitor_sources` ma
# liczbe wprost w wierszu (`free_signup: 5`), a `growth/sources` chowa ja
# w liscie miar: `metrics: [{"name": "Subscribers", "total": 5}, ...]`.
# Obsluga obu jest tu po to, zeby jedno zrodlo nie wymagalo osobnej funkcji.
_MIARY_ZAPISOW = ("subscribers", "signups", "free_signups", "signup")
_MIARY_RUCHU = ("traffic", "views", "visitors")
_KLUCZE_ZAPISOW = ("free_signup", "free_signups", "subscribers", "signups",
                   "users", "count")


def _wiersze_zrodel(dane: Any) -> list[dict[str, Any]]:
    """Lista pozycji z odpowiedzi o zrodlach — niezaleznie od klucza."""
    if isinstance(dane, list):
        return [x for x in dane if isinstance(x, dict)]
    if not isinstance(dane, dict):
        return []
    for klucz in _KLUCZE_LISTY:
        wart = dane.get(klucz)
        if isinstance(wart, list) and wart:
            return [x for x in wart if isinstance(x, dict)]
    return []


def _cos_w_odpowiedzi(dane: Any) -> bool:
    """Czy odpowiedz W OGOLE cos niesie — odroznia „pusto" od „nie wiem".

    `{"rows": [], "total": 0}` jest poprawnym JSON-em i nie jest pomiarem.
    Pytamy wiec nie o to, czy odpowiedz przyszla, tylko czy jest w niej
    jakakolwiek NIEPUSTA zawartosc — lista albo zagniezdzony slownik.

    LISTA MUSI ZAWIERAC SLOWNIKI, i to nie jest formalnosc: pierwsza wersja
    przepuszczala `[1, 2, 3]` (bo lista niepusta), liczyla to za udany odczyt
    i zapisywala wiersz, w ktorym `odczytane` klamalo, ze tabela odpowiedziala.
    Wylapal to test, nie produkcja. Tabela zrodel to wiersze, czyli slowniki.
    """
    if isinstance(dane, list):
        return any(isinstance(x, dict) and x for x in dane)
    if not isinstance(dane, dict):
        return False
    for wart in dane.values():
        if isinstance(wart, dict) and wart:
            return True
        if isinstance(wart, list) and any(isinstance(x, dict) and x
                                          for x in wart):
            return True
    return False


def _suma_pola(wiersze: list[dict[str, Any]], *pola: str) -> int | None:
    """Suma pierwszego istniejacego pola po wierszach.

    `None`, gdy ZADEN wiersz takiego pola nie ma — bo „nie znalazlem liczby"
    i „liczba wynosi zero" to dwie rozne rzeczy i w szeregu czasowym mylenie
    ich juz raz kosztowalo ten projekt falszywy wniosek.
    """
    suma = 0
    znalezione = False
    for w in wiersze:
        if not isinstance(w, dict):
            continue
        for pole in pola:
            if isinstance(w.get(pole), (int, float)) and not isinstance(
                    w.get(pole), bool):
                suma += int(w[pole])
                znalezione = True
                break
    return suma if znalezione else None


def _z_miar(wezel: Any, nazwy: tuple[str, ...]) -> int | None:
    """Liczba z `metrics: [{"name": "Subscribers", "total": 5}, ...]`."""
    if not isinstance(wezel, dict):
        return None
    miary = wezel.get("metrics")
    if not isinstance(miary, list):
        return None
    for miara in miary:
        if not isinstance(miara, dict):
            continue
        if str(miara.get("name") or "").strip().lower() not in nazwy:
            continue
        razem = miara.get("total")
        if isinstance(razem, (int, float)) and not isinstance(razem, bool):
            return int(razem)
    return None


def _zapisy_wezla(wezel: Any) -> int | None:
    """Zapisy z jednej galezi — obojetne, w ktorym z dwoch ksztaltow przyszly."""
    z_miary = _z_miar(wezel, _MIARY_ZAPISOW)
    return z_miary if z_miary is not None else _suma_pola([wezel],
                                                          *_KLUCZE_ZAPISOW)


def _z_totali(dane: Any, nazwy: tuple[str, ...]) -> int | None:
    """Liczba z pola `totals` — panel podaje je LISTA, nie slownikiem."""
    if not isinstance(dane, dict):
        return None
    razem = dane.get("totals", dane.get("total"))
    if isinstance(razem, list):
        return _z_miar({"metrics": razem}, nazwy)
    if isinstance(razem, dict):
        return _z_miar(razem, nazwy) if "metrics" in razem else _suma_pola(
            [razem], *_KLUCZE_ZAPISOW)
    return None


def _zapisy_ogolem(dane: Any) -> int | None:
    """Laczna liczba zapisow z drzewa `growth/sources`, albo `None`.

    Zmierzone 2 wrzesnia: `totals` oddaje 6 i suma galezi najwyzszego poziomu
    tez 6 (substack 6, direct 0, direct to app 0) — biore `totals`, a suma jest
    droga zapasowa. Sumujemy WYLACZNIE najwyzszy poziom: dzieci (rozbicie na
    notki) siedza w galeziach i policzone drugi raz podwoilyby wynik.
    """
    razem = _z_totali(dane, _MIARY_ZAPISOW)
    if razem is not None:
        return razem
    sumy = [_zapisy_wezla(w) for w in _wiersze_zrodel(dane)]
    sumy = [x for x in sumy if x is not None]
    return sum(sumy) if sumy else None


def _zapisy_per_notka(dane: Any) -> dict[str, int]:
    """{numer notki: zapisy} — z dowolnie zagniezdzonego drzewa.

    Chodzenie po calym drzewie zamiast po znanej sciezce jest tu celowe:
    zmierzone 2 wrzesnia notki wisza jako `children` galezi „Notes", ale to,
    ze Substack zostawi je dokladnie tam, nie jest niczym zagwarantowane.
    Szukamy wiec POLA `noteId`, nie miejsca w drzewie.
    """
    wynik: dict[str, int] = {}
    stos: list[Any] = [dane]
    while stos:
        wezel = stos.pop()
        if isinstance(wezel, dict):
            ident = wezel.get("noteId", wezel.get("note_id"))
            if ident not in (None, ""):
                ile = _zapisy_wezla(wezel)
                if ile is not None:
                    klucz = str(ident)
                    wynik[klucz] = wynik.get(klucz, 0) + ile
            stos.extend(wezel.values())
        elif isinstance(wezel, list):
            stos.extend(wezel)
    return wynik


def zapisz_zrodla_ruchu(page=None, dni: int = 30) -> dict[str, Any] | None:
    """SKAD naprawde biora sie zapisy — tabela zrodel, jedna linia na odczyt.

    CZEGO NIE MIERZYLISMY. Kod nazywal „subskrypcjami z artykulu" pole
    `stats.signups_within_1_day` z panelu wydawcy. Ustalone pomiarem
    2 wrzesnia 2026: to jest OKNO CZASOWE — kto zapisal sie w ciagu doby po
    wpisie — a nie przypisanie zrodla. Prawdziwe przypisanie panel ma, tylko
    nikt go nie czytal. Sa to dwa adresy, oba na bazie NASZEJ publikacji
    (`api_json` bez `baza` pyta substack.com i oddaje cisze):

        /api/v1/publication/stats/visitor_sources  — RUCH per zrodlo
        /api/v1/publication/stats/growth/sources   — ZAPISY per zrodlo,
                                                     z rozbiciem na notki

    ZMIERZONE 2 wrzesnia 2026, okno 2026-08-03 -> 2026-09-02 (30 dni):
        ruch    direct to app 640 wysw / 39 osob, substack app 184/46,
                direct 14/5, email opens 12/6 — razem 850 wyswietlen, 96 osob
        zapisy  6, w tym 5 z NOTEK (c-323761132 dwa, c-320809275,
                c-322556153 i c-322757850 po jednym) i 1 z „substack other"
    Liczba zapisow zgadza sie CO DO SZTUKI miedzy oboma adresami — dlatego
    bierzemy oba i zapisujemy `zapisy_zgodne`: rozejscie sie tych dwoch liczb
    jest sygnalem, ze cos w odczycie przestalo dzialac.

    DLACZEGO SZEREG, A NIE ZRZUT. Szesc zapisow to za malo na jakikolwiek
    wniosek o tym, co dziala. Wartosc tej funkcji polega na tym, ze za tydzien
    bedzie siedem wierszy, a nie na tych szesciu — wiec DOPISUJEMY, nigdy nie
    nadpisujemy, i zapisujemy okno, ktorego odczyt dotyczy (bez niego dwa
    wiersze z roznymi oknami wygladaja na wzrost albo spadek, ktorego nie bylo).

    CZEGO TA TABELA NIE MOWI, zeby jej nie przecenic: nie ma w niej galezi
    „artykul" — rozbicie na sztuki dostaja WYLACZNIE notki. Brak artykulow nie
    znaczy, ze nie przynosza zapisow; znaczy, ze ten przyrzad nie ma na to
    rubryki. Wiersze z ruchem i wiersze z zapisami sa ROZLACZNE (`views: null`
    przy `free_signup: 5`), wiec konwersji „zapisy na odwiedziny" z tego
    policzyc SIE NIE DA i nie liczymy jej.

    CISZA NIE JEST ZEREM — I TO JEST TU RZECZ NAJWAZNIEJSZA. Ten projekt ma
    udokumentowany przypadek, w ktorym odpowiedz poprawna i PUSTA kosztowala
    DZIEWIEC DNI: 23 sierpnia 2026 na szesciu profilach slowo „Follow" nie
    wystapilo ani razu, wniosek brzmial „Substack zdjal przycisk", i przez
    dziewiec dni agent nie zaobserwowal NIKOGO — a zero nikomu nie wygladalo
    na awarie, bo tabela normy tlumaczyla je tym samym nieprawdziwym zdaniem.
    Pomiar byl prawdziwy, wniosek falszywy, bo pustka wygladala jak wynik. To
    samo w mniejszej skali: `/api/v1/note_stats/p-<id>` oddaje dla artykulu
    odpowiedz poprawna i pusta, czyli piec rekordow z samymi zerami.

    Stad cztery bramki, kazda na inna postac ciszy:

      1. BRAK SESJI I PADNIETA PRZEGLADARKA. `wymagaj_sesji` rzuca
         `SystemExit`, a to NIE jest `Exception` — samo `except Exception`
         przepuscilo by je i pomiar zabralby caly przebieg. Lapiemy oba,
         a przebieg dostaje `None`.
      2. 403 I STRONA WYZWANIA. `api_json` oddaje wtedy `None`, bo tresc nie
         jest JSON-em. `None` znaczy „nie wiem", nie „zero": ta polowa idzie
         do pola `blad`, a nie do liczb.
      3. ODPOWIEDZ POPRAWNA I PUSTA. Odczyt liczy sie za udany dopiero, gdy
         odpowiedz cokolwiek NIESIE (`_cos_w_odpowiedzi`). Zmierzone: nawet
         okno 30-dniowe na koncie z siedmioma subskrybentami oddaje szesc
         wierszy, wiec pusta tabela znaczy u nas awarie, a nie spokojny dzien.
         Wiersz z samymi zerami byl by nie do odroznienia od dnia, w ktorym
         ruch naprawde ustal — wiec go NIE PISZEMY. Gdy nie odczytano ZADNEJ
         polowy, funkcja oddaje `None` i nie dopisuje nic.
      4. ZMIANA KSZTALTU. Do pliku idzie ZAWSZE odpowiedz SUROWA, a liczby
         wyliczone leza obok niej. Gdy Substack przemianuje pola, sumy maja
         `null` (nie zero), a surowe liczby zostaja w pliku — da sie je
         przeliczyc pozniej, bez powtarzania pomiaru, ktorego powtorzyc nie
         mozna, bo okno juz minelo.

    TRZY STANY, NIE DWA — tak jak w `zapisz_czytelnikow`. `odczytane` mowi,
    ktore polowy naprawde odpowiedzialy; `blad` jest zapisywany ZAWSZE, takze
    jako `null`. Czytajacy ma pytac `wiersz.get("blad", "nie wiadomo")`.
    """
    import json as _json
    from datetime import datetime, timedelta, timezone

    NOWA_LINIA = chr(10)
    teraz = datetime.now(timezone.utc)
    dni = max(1, int(dni or 30))
    do_dnia = teraz.date()
    od_dnia = do_dnia - timedelta(days=dni)

    wlasny = page is None
    p_ = br_ = None
    if wlasny:
        # SESJI MOZE NIE BYC, A POMIAR NIGDY NIE ZABIJA PRZEBIEGU. `SystemExit`
        # jest tu wymieniony osobno, bo nie dziedziczy po `Exception`.
        try:
            wymagaj_sesji()
            p_, br_, ctx = podlacz_sie()
            page = ctx.new_page()
        except (Exception, SystemExit) as exc:
            print("  [zrodla] sesji nie otworzylem: %s" % type(exc).__name__,
                  flush=True)
            try:
                if br_ is not None:
                    br_.close()
                if p_ is not None:
                    p_.stop()
            except Exception:
                pass
            return None

    baza = f"https://{config.SUBSTACK_HANDLE}.substack.com"
    okres = f"from_date={od_dnia.isoformat()}&to_date={do_dnia.isoformat()}"
    zapytania = (
        ("ruch", "/api/v1/publication/stats/visitor_sources"
                 f"?{okres}&offset=0&limit=50"
                 "&order_by=views&order_direction=desc"),
        ("zapisy", "/api/v1/publication/stats/growth/sources"
                   f"?order_by=users&order_direction=desc&{okres}"),
    )

    surowe: dict[str, Any] = {"ruch": None, "zapisy": None}
    odczytane: list[str] = []
    bledy: dict[str, str] = {}
    try:
        for nazwa, sciezka in zapytania:
            try:
                dane = api_json(page, sciezka, baza=baza)
            except Exception as exc:
                # Jedna polowa, ktorej nie da sie odczytac, NIE zabiera drugiej
                # — tak samo jak pojedyncza pozycja w `statystyki_pozycji`.
                bledy[nazwa] = f"{type(exc).__name__}: {exc}"[:200]
                print("  [zrodla] %s: %s" % (nazwa, bledy[nazwa]), flush=True)
                continue
            if dane is None:
                bledy[nazwa] = "brak JSON-a (403 albo strona wyzwania)"
            elif not _cos_w_odpowiedzi(dane):
                bledy[nazwa] = "odpowiedz poprawna i PUSTA: %s" % str(dane)[:120]
            else:
                surowe[nazwa] = dane
                odczytane.append(nazwa)
                continue
            print("  [zrodla] %s: %s" % (nazwa, bledy[nazwa]), flush=True)
    finally:
        if wlasny:
            try:
                page.close()
                br_.close()
                p_.stop()
            except Exception:
                pass

    # NIC NIE ODCZYTANE TO NIE JEST POMIAR — brak danych ma wygladac na brak
    # danych, a nie na dzien, w ktorym ruch spadl do zera.
    if not odczytane:
        print("  [zrodla] zadna polowa nie odpowiedziala — nie zapisuje nic",
              flush=True)
        return None

    wiersze_ruchu = _wiersze_zrodel(surowe["ruch"])
    zapisy_z_ruchu = _suma_pola(wiersze_ruchu, "free_signup", "free_signups")
    zapisy_ze_wzrostu = _zapisy_ogolem(surowe["zapisy"])
    stan = {
        "kiedy": teraz.isoformat(timespec="seconds"),
        # BEZ OKNA WIERSZ JEST NIEPOROWNYWALNY. Dwa odczyty o roznych oknach
        # roznia sie liczbami, nie ruchem.
        "okno": {"od": od_dnia.isoformat(), "do": do_dnia.isoformat(),
                 "dni": dni},
        "odczytane": odczytane,
        "blad": bledy or None,
        # SUROWE ODPOWIEDZI. Jedyna czesc tego wiersza, ktora przezyje
        # przemianowanie pol po stronie Substacka.
        "ruch": surowe["ruch"],
        "zapisy": surowe["zapisy"],
        # Liczby wyliczone OBOK surowych, nigdy zamiast nich. `null` znaczy
        # „nie znalazlem", nie „zero".
        "podsumowanie": {
            "zrodel_ruchu": len(wiersze_ruchu) if "ruch" in odczytane else None,
            "wyswietlenia": _suma_pola(wiersze_ruchu, "views"),
            "osoby": _suma_pola(wiersze_ruchu, "users"),
            "zapisy_z_ruchu": zapisy_z_ruchu,
            "zapisy_ze_wzrostu": zapisy_ze_wzrostu,
            # DRUGA LICZBA RUCHU, I ONA SIE Z PIERWSZA NIE ZGADZA: 2 wrzesnia
            # `growth/sources` mowil 64 przy 850 wyswietleniach i 96 osobach
            # z `visitor_sources`. Czego dokladnie liczy — nie wiem i nie
            # zgaduje; zapisuje obie, bo rozjazd sam w sobie jest informacja.
            "ruch_ze_wzrostu": _z_totali(surowe["zapisy"], _MIARY_RUCHU),
            "zapisy_per_notka": (_zapisy_per_notka(surowe["zapisy"])
                                 if "zapisy" in odczytane else None),
            # KONTROLA KRZYZOWA. Dwa niezalezne adresy mowily 2 wrzesnia to
            # samo (6 i 6). Gdy przestana, wiersz sam o tym powie.
            "zapisy_zgodne": (None if zapisy_z_ruchu is None
                              or zapisy_ze_wzrostu is None
                              else zapisy_z_ruchu == zapisy_ze_wzrostu),
        },
    }

    try:
        ZRODLA.parent.mkdir(parents=True, exist_ok=True)
        with ZRODLA.open("a", encoding="utf-8") as f:
            f.write(_json.dumps(stan, ensure_ascii=False) + NOWA_LINIA)
    except OSError as exc:
        # Zapis jest premia, pomiar wazniejszy — tak samo jak przy wzroscie.
        print("  [zrodla] nie zapisalem: %s" % type(exc).__name__, flush=True)

    p = stan["podsumowanie"]
    print("  [zrodla] %s..%s: %s wysw, %s osob, zapisy %s/%s, notki %s"
          % (od_dnia, do_dnia, p["wyswietlenia"], p["osoby"],
             p["zapisy_z_ruchu"], p["zapisy_ze_wzrostu"],
             len(p["zapisy_per_notka"] or {})), flush=True)
    return stan


def _artykuly_z_panelu(page, baza: str) -> dict[str, dict[str, Any]]:
    """Nasze artykuly razem ze statystykami — JEDNYM zapytaniem.

    ZNALEZIONE POMIAREM, NIE ZGADNIETE. Artykulow nie mierzylismy wcale: 369
    pomiarow komentarzy, 365 notek, 24 odpowiedzi, ZERO artykulow. Pierwsza
    proba szla `/api/v1/note_stats/p-<id>` — ta sama koncowka co dla notki,
    inny przedrostek. Odpowiedz przychodzila poprawna i PUSTA: artykul dostaje
    stamtad jedna karte (podglad wpisu), notka piec. Piec rekordow z zerami
    wyglada jak pomiar i nim nie jest, wiec ta droga zostala porzucona.

    Liczby sa w panelu wydawcy, pod `/api/v1/post_management/published`, i to
    dla WSZYSTKICH artykulow naraz — zero otwierania stron po jednej.
    Zmierzone 30 sierpnia na zywym koncie:

        Example Article One   8 wysw,  4 wyslane, 2 otwarte, 3 zapisy
        Example Article Three  32 wysw,  4 wyslane, 1 otwarte, 3 klikniecia

    RESTACKI SA W INNYM MIEJSCU. Panel ich nie podaje, archiwum tak — i to nie
    to samo co `stats.shares`: dla tego samego wpisu archiwum mowilo 1 restack,
    a panel 0 udostepnien. Bierzemy wiec obie listy i sklejamy po numerze,
    zamiast podstawiac jedno pod drugie.
    """
    wynik: dict[str, dict[str, Any]] = {}

    restacki: dict[str, int] = {}
    archiwum = api_json(page, "/api/v1/archive?sort=new&limit=30", baza=baza)
    for post in archiwum if isinstance(archiwum, list) else []:
        if isinstance(post, dict) and post.get("id") is not None:
            restacki[str(post["id"])] = int(post.get("restacks") or 0)

    panel = api_json(page, "/api/v1/post_management/published"
                           "?offset=0&limit=30&order_by=post_date"
                           "&order_direction=desc", baza=baza)
    posty = (panel or {}).get("posts") if isinstance(panel, dict) else None
    if not isinstance(posty, list):
        print("  [statystyki] panel wydawcy oddal %s zamiast listy postow"
              % type(panel).__name__, flush=True)
        return wynik

    for post in posty:
        if not isinstance(post, dict) or post.get("id") is None:
            continue
        ident = str(post["id"])
        s = post.get("stats") if isinstance(post.get("stats"), dict) else {}

        def licz(*klucze: str) -> int:
            return sum(int(s.get(k) or 0) for k in klucze)

        wynik[ident] = {
            "rodzaj": "artykul",
            "id": ident,
            "tekst": " ".join(str(post.get("title") or "").split())[:200],
            "statystyki": {
                # KIEDY TO WYSZLO. Ta sama informacja, co `wystawione`
                # w `statystyki.z_kart` — bez niej pomiaru nie da sie
                # przypisac do epoki inaczej niz laczeniem po tytule.
                "wystawione": str(post.get("post_date") or ""),
                "wyswietlenia": int(s.get("views") or 0),
                # ODPOWIEDZI TO WATEK CALY, nie same komentarze najwyzszego
                # poziomu. `comment_count` liczy tylko te pierwsze — pod
                # „Example Article Three" bylo 2 i 2, wiec pominiecie odpowiedzi
                # zanizaloby o polowe.
                "odpowiedzi": (int(post.get("comment_count") or 0)
                               + int(post.get("child_comment_count") or 0)),
                "polubienia": int(post.get("reaction_count") or 0),
                "restacki": restacki.get(ident, 0),
                # ZAPISY, NIE PLATNE SUBSKRYPCJE. `signups_within_1_day` to
                # nowi czytelnicy przypisani do TEGO wpisu — jedyna liczba
                # w calym API, ktora wiaze subskrybenta z konkretna trescia.
                "subskrypcje": licz("signups_within_1_day"),
                "klikniecia_w_link": int(s.get("clicks") or 0),
                # POCZTA. Artykul, inaczej niz notka, jest tez wysylka — i to
                # jest liczba, ktorej notka nie ma wcale.
                "wyslane": int(s.get("sent") or 0),
                "dostarczone": int(s.get("delivered") or 0),
                "otwarcia": int(s.get("opened") or 0),
                "udostepnienia": int(s.get("shares") or 0),
            },
        }
    return wynik


def nasze_pozycje_do_pomiaru(page=None, ile: int = 60) -> list[dict[str, Any]]:
    """Co wystawilismy i ma wlasny numer — czyli co da sie zmierzyc.

    DWA ZRODLA, I TO NIE JEST NADMIAROWOSC.

    PROFIL jest zrodlem prawdy o notkach. Kanal profilu oddaje kazda nasza
    notke razem z numerem, niezaleznie od tego, czy nasz dziennik ten numer
    zapisal. A nie zapisywal: zmierzone 25 sierpnia, z 29 wystawionych notek
    numer mial SZESC. Gdybysmy pytali wylacznie wlasnej ksiegowosci, 23 notki
    byly by dla pomiaru niewidzialne — i to te starsze, czyli akurat te, ktore
    zdazyly cos zebrac.

    DZIENNIK dokłada to, czego na profilu nie ma: komentarze pod cudzymi
    tekstami (pole `nasz_id`) i odpowiedzi w cudzych watkach (numer w polu
    `gdzie` w postaci „note/c-<numer>").

    `page` podaje sie, gdy sesja przegladarki juz jest otwarta — zeby nie
    otwierac drugiej. Bez niej czytamy sam dziennik.
    """
    import json as _json
    import re as _re

    widziane: dict[str, dict[str, Any]] = {}

    # --- profil: nasze notki z numerami ---
    if page is not None:
        try:
            profil = api_json(page, f"/api/v1/user/{PROFIL_HANDLE}/public_profile")
            # ILU NAS CZYTA — z odpowiedzi, ktora i tak wlasnie przyszla.
            stan = zapisz_wzrost_konta(profil)
            if stan:
                print("  [wzrost] subskrybentow %d, obserwujacych %d"
                      % (stan["subskrybenci"], stan["obserwujacy"]), flush=True)
            # KTO, NIE TYLKO ILU. Liczba mowi, ze konto rosnie; lista pozwala
            # zapytac, CZY ROSNIE OD NASZYCH DZIALAN. Jedno wejscie na strone
            # na caly pomiar.
            zrzut = zapisz_czytelnikow(page)
            if zrzut:
                print("  [czytelnicy] obserwujacych %d, subskrybentow %d"
                      % (len(zrzut["obserwujacy"]), len(zrzut["subskrybenci"])),
                      flush=True)
                # OKROJONY ZRZUT MA BYC SLYSZALNY W LOGU TEGO SAMEGO
                # PRZEBIEGU, a nie dopiero w raporcie za tydzien.
                brak = [z for z in ("obserwujacy", "subskrybenci")
                        if z not in zrzut.get("odczytane", [])]
                if brak:
                    print("  [czytelnicy] ! ZRZUT OKROJONY, nie odczytano: %s"
                          % ", ".join(brak), flush=True)
            # I DRUGA STRONA: KOGO MY OBSERWUJEMY. Ta sama otwarta sesja, jedno
            # wejscie na zakladke wiecej — a blok obserwacji dostaje dzieki
            # temu odsiew puli BEZ ani jednego wlasnego zapytania do Substacka.
            # Patrz `OBSERWOWANI`: 8 z 92 hostow historii to konta, ktore juz
            # obserwujemy, i kazde takie losowanie zjadalo caly dzienny slot.
            ilu = odswiez_kogo_obserwujemy(page)
            if ilu:
                print("  [obserwowani] znamy %d kont, ktore juz obserwujemy"
                      % ilu, flush=True)
            if isinstance(profil, dict) and profil.get("id"):
                feed = api_json(page, f"/api/v1/reader/feed/profile/{profil['id']}"
                                      "?types%5B%5D=note") or {}
                for poz in feed.get("items") or []:
                    k = poz.get("comment") if isinstance(poz, dict) else None
                    if not isinstance(k, dict) or k.get("id") is None:
                        continue
                    widziane[str(k["id"])] = {
                        "rodzaj": "notka",
                        "id": str(k["id"]),
                        "tekst": " ".join(str(k.get("body") or "").split())[:200],
                    }
            # --- ARCHIWUM: nasze ARTYKULY -----------------------------------
            #
            # Dodane 30 sierpnia, bo artykulow nie mierzylismy WCALE. Numery
            # sa w `/api/v1/archive`, a statystyki pod ta sama koncowka co
            # notki, z przedrostkiem `p-` zamiast `c-` — sprawdzone na zywo.
            #
            # To jest najdrozsza rzecz, jaka to konto produkuje (research plus
            # pisanie to okolo dolara za sztuke), i jedyna, o ktorej wiedzielismy
            # tylko tyle, ze wyszla.
            # ADRES BAZOWY JEST TU OBOWIAZKOWY. `/api/v1/archive` nalezy do
            # NASZEJ PUBLIKACJI, nie do serwisu — a `api_json` bez `baza` pyta
            # substack.com. Pierwsza wersja tej poprawki nie podawala bazy i
            # przebieg na zywo oddal 46 pozycji i ZERO artykulow: zapytanie
            # poszlo pod zly adres, oddalo cos, co nie jest lista, i `or []`
            # zamienilo to w cisze. Dokladnie ta pomylka, przed ktora ostrzega
            # docstring `api_json`.
            moja_publikacja = f"https://{config.SUBSTACK_HANDLE}.substack.com"
            try:
                widziane.update(_artykuly_z_panelu(page, moja_publikacja))
            except Exception as exc:
                print("  [statystyki] panel wydawcy: %s"
                      % type(exc).__name__, flush=True)
        except Exception as exc:
            print("  [statystyki] profilu nie odczytalem: %s"
                  % type(exc).__name__, flush=True)

    # --- dziennik: komentarze i odpowiedzi, ktorych na profilu nie ma ---
    if DZIENNIK.exists():
        try:
            for linia in DZIENNIK.read_text(encoding="utf-8").splitlines():
                linia = linia.strip()
                if not linia:
                    continue
                try:
                    w = _json.loads(linia)
                except ValueError:
                    continue
                if not isinstance(w, dict) or not w.get("udane"):
                    continue
                rodzaj = str(w.get("rodzaj") or "")
                if rodzaj not in ("notka", "restack", "komentarz", "odpowiedz"):
                    continue
                ident = w.get("id") or w.get("nasz_id")
                if not ident:
                    m = _re.search(r"note/c-(\d+)", str(w.get("gdzie") or ""))
                    ident = m.group(1) if m else None
                if not ident:
                    continue
                ident = str(ident)
                if ident in widziane:
                    continue
                widziane[ident] = {
                    "rodzaj": "notka" if rodzaj in ("notka", "restack") else rodzaj,
                    "id": ident,
                    "tekst": (w.get("tekst") or "")[:200],
                }
        except OSError:
            pass

    # NASZE NOTKI NIGDY NIE WYPADAJA Z POMIARU.
    #
    # Stalo tu `list(widziane.values())[-ile:]`, czyli „zostaw `ile` ostatnich".
    # A notki dopisywane sa PIERWSZE, wiec obcinanie od poczatku wycinalo
    # dokladnie je. Zmierzone na produkcji: 60 pozycji do pomiaru, z tego
    # 36 komentarzy i 24 odpowiedzi — i ANI JEDNEJ notki, mimo ze profil
    # oddal ich dwanascie. Raport statystyk pokazywal wiec wszystko procz
    # tego, co sami wystawiamy.
    #
    # Notka jest nasza wlasna trescia i jedyna, ktora ma pelne statystyki;
    # komentarz pod cudzym artykulem oddaje same zera, bo nie jest notka.
    # Limit obcina wiec RESZTE, nie notki.
    # DRUGI RAZ TEN SAM BLAD, wiec regula jest teraz OGOLNA, nie wyliczona.
    #
    # Poprawka wyzej chronila NOTKI po nazwie. Gdy 30 sierpnia doszly artykuly,
    # wpadly do `reszty` — a poniewaz dopisujemy je PRZED dziennikiem, staly na
    # jej poczatku i `reszta[-N:]` wycinala wlasnie je. Przebieg na zywo oddawal
    # 60 pozycji: 32 notki, 27 komentarzy, 1 odpowiedz i ZERO artykulow, mimo ze
    # archiwum oddawalo piec. Endpoint dzialal, przedrostek `p-` dzialal,
    # gubil je limit.
    #
    # Nasza wlasna tresc nie podlega limitowi. Limit istnieje po to, zeby nie
    # mierzyc w nieskonczonosc CUDZYCH watkow, w ktorych zostawilismy komentarz.
    #
    # `[-0:]` TO CALA LISTA, NIE PUSTA. Ta linijka brzmiala
    # `reszta[-max(0, ile - len(nasze)):]`, wiec gdy naszych tresci bylo tyle
    # co limit albo wiecej, wycinek stawal sie `reszta[0:]` i limit przestawal
    # istniec — akurat wtedy, gdy zaczyna byc potrzebny. Dzis notek jest 12
    # i to nie boli; przy szescdziesieciu przebieg otwieralby w przegladarce
    # KAZDY komentarz, jaki kiedykolwiek zostawilismy. Liczymy wiec jawnie.
    NASZE_RODZAJE = ("artykul", "notka")
    nasze = [x for x in widziane.values() if x["rodzaj"] in NASZE_RODZAJE]
    reszta = [x for x in widziane.values() if x["rodzaj"] not in NASZE_RODZAJE]
    zostalo = max(0, ile - len(nasze))
    return nasze + (reszta[-zostalo:] if zostalo else [])


def dopisz_skutki() -> int:
    """Dopisuje do dziennika, CO Z NASZYCH DZIALAN WYNIKLO.

    Dziennik wiedzial, co wystawilismy, i nic o tym, czy ktokolwiek to zauwazyl.
    A to jest jedyne pytanie, na ktore trzeba umiec odpowiedziec, zeby cokolwiek
    poprawic: osiemnascie komentarzy przynioslo trzy reakcje, siedem notek —
    osiem. Musialem to policzyc recznie, bo agent tego nie zapisywal.

    Kanal aktywnosci mowi o polubieniach i odpowiedziach numerami komentarzy,
    a `wystaw_komentarz` zapisuje teraz numer naszego. Da sie wiec zestawic
    jedno z drugim i pytac: czy komentarz jako piaty wraca czesciej niz jako
    piecdziesiaty, i ktore z osiemnastu hasel przynosza rozmowy.

    Kazde zdarzenie zapisujemy RAZ — po jego wlasnym numerze, ktory Substack
    nadaje. Inaczej kazdy przebieg dopisywalby te same polubienia od nowa
    i statystyka rosla by sama z siebie.

    ZAPISUJEMY NAZWE **I** UCHWYT, BO NAZWA SAMA JEST NIEROZWIAZYWALNA.
    Do 1 wrzesnia 2026 ta petla brala z obiektu uzytkownika wylacznie `name`
    i wyrzucala reszte. Skutek zmierzony na produkcyjnym dzienniku tego dnia
    (635 wierszy, 199 wpisow `skutek`, 69 roznych osob): `czytelnicy.jsonl`
    rozwiazuje 11 nazw z 69 — i sa to dokladnie ci, ktorzy juz nas czytaja,
    wiec jako cele bezuzyteczni; rownosc slugu nazwy ze slugiem hosta z
    historii komentarzy trafia 7 z 69, z czego po odsianiu wszystkiego sprzed
    przestawienia konta na AI zostaja TRZY (`hedleyrees.substack.com`,
    `www.ryanpuzycki.com`, `davidoks.blog`). Czyli 62 z 69 osob, ktore same
    dotknely naszej tresci, nie dalo sie zamienic na cel — nie dlatego, ze
    ich nie ma, tylko dlatego, ze uchwyt lezal w reku i nie byl zapisywany.

    NOWE POLE JEST DOPISANE, A NIE ZAMIENIONE. `kto` zostaje tym samym, czym
    bylo (lista nazw wyswietlanych), bo czytaja je `wzajemnosc.py` i
    `run.kogo_juz_dotknelismy`, a 199 istniejacych wpisow nowego pola nie ma
    i miec nie bedzie — czytelnik ma traktowac jego brak jako „nie wiem",
    nie jako „nikt".
    """
    import json as _json

    juz_zapisane = set()
    try:
        if DZIENNIK.exists():
            for linia in DZIENNIK.read_text(encoding="utf-8").splitlines():
                linia = linia.strip()
                if not linia:
                    continue
                try:
                    wpis = _json.loads(linia)
                except ValueError:
                    continue
                if isinstance(wpis, dict) and wpis.get("rodzaj") == "skutek":
                    juz_zapisane.add(wpis.get("zdarzenie"))
    except OSError:
        pass

    wymagaj_sesji()
    p, browser, context = podlacz_sie()
    page = context.new_page()
    nowych = 0
    z_uchwytem = bez_uchwytu = 0
    try:
        kanal = api_json(page, "/api/v1/activity-feed-web?filter=all") or {}
        if not isinstance(kanal, dict):
            return 0
        ludzie = {u["id"]: u for u in (kanal.get("users") or [])
                  if isinstance(u, dict) and u.get("id") is not None}
        for z in kanal.get("activityItems") or []:
            if not isinstance(z, dict):
                continue
            klucz = z.get("id") or z.get("item_key")
            if not klucz or klucz in juz_zapisane:
                continue
            typ = z.get("type")
            if not typ:
                continue
            # ZAPISUJEMY KAZDY RODZAJ, nie liste znanych. Lista miala w sobie
            # doslowne „restack", a Substack nazywa zdarzenia `note_like`,
            # `note_reply`, `comment_like` — wiec podanie naszej notki dalej
            # przyszloby zapewne jako `note_restack` i wypadloby bez sladu.
            # Akurat restack jest najcenniejszym sygnalem, jaki mozemy dostac:
            # w badaniu 9 641 notek konwertowal dwunastokrotnie lepiej niz
            # polubienie. Sygnal, ktorego nie widzimy, nie istnieje.
            #
            # Kanal aktywnosci dotyczy WYLACZNIE naszych tresci, wiec nie ma tu
            # czego odsiewac — nieznany rodzaj to nowa wiadomosc, nie smiec.
            # NAZWA I UCHWYT SKLADANE PARAMI, NIGDY DWIEMA PETLAMI. Stara
            # linijka budowala `kto` z `recent_sender_ids`, a potem odsiewala
            # `[k for k in kto if k][:5]` — gdyby uchwyty leciec obok tak samo,
            # ale bez tego odsiewu, to przy PIERWSZYM nadawcy bez nazwy nazwa
            # osoby drugiej dostalaby uchwyt osoby trzeciej. Taki rozjazd jest
            # niewidoczny w pliku i daje cel wygladajacy na zmierzony, a nie
            # bedacy nim. Para powstaje wiec raz, odsiew i `[:5]` tna JEDNA
            # liste par, a `kto[i]` i `uchwyty[i]` sa z definicji ta sama osoba.
            #
            # ODSIEW PO NAZWIE ZOSTAJE TAKI SAM, ZEBY `kto` sie nie zmienilo.
            # Zmierzone na produkcyjnym dzienniku (199 wpisow `skutek`): w
            # KAZDYM z nich `ilu` rowna sie dlugosci `kto`, czyli nadawca bez
            # nazwy nie trafil sie ani razu i ten filtr nigdy nie odpalil.
            pary: list[tuple[str, str | None]] = []
            for i in (z.get("recent_sender_ids") or []):
                osoba = ludzie.get(i) or {}
                nazwa = osoba.get("name")
                if not nazwa:
                    continue
                # BRAK UCHWYTU MA BYC WIDOCZNY JAKO BRAK. `None` (a nie pusty
                # napis) odroznia „tej osoby nie umiemy nazwac uchwytem" od
                # „nie bylo nikogo" (pusta lista) i od wpisu sprzed tej zmiany
                # (klucza nie ma wcale) — kazdy z tych trzech stanow znaczy co
                # innego dla wyboru celu.
                uchwyt = osoba.get("handle")
                uchwyt = str(uchwyt).strip() or None if uchwyt else None
                pary.append((nazwa, uchwyt))
            pary = pary[:5]
            bez_uchwytu += sum(1 for _, u in pary if not u)
            z_uchwytem += sum(1 for _, u in pary if u)
            zapisz_w_dzienniku(
                "skutek", udane=True, zdarzenie=klucz, typ=typ,
                # `czego` to numer NASZEJ tresci, ktora wywolala reakcje —
                # po nim laczymy skutek z wpisem o jej wystawieniu.
                czego=z.get("target_comment_id"),
                ilu=int(z.get("sender_count") or 0),
                kto=[n for n, _ in pary],
                # POLE, KTOREGO BRAK ZABIJAL CALE PIERWSZENSTWO CELOW.
                # Zmierzone 1 wrzesnia 2026 na produkcyjnym dzienniku (635
                # wierszy, 199 wpisow `skutek`, 69 roznych osob): przez
                # `czytelnicy.jsonl` da sie odgadnac uchwyt 11 osobom i sa to
                # dokladnie nasi obecni czytelnicy, a przez rownosc slugu nazwy
                # ze slugiem hosta — 7, z czego po odsiewie tematycznym zostaja
                # TRZY zywe cele. Uchwyt lezal w tym samym obiekcie uzytkownika,
                # ktory ta petla juz trzyma w reku, i byl wyrzucany.
                uchwyty=[u for _, u in pary],
                kiedy_zdarzenia=str(z.get("created_at") or "")[:19])
            nowych += 1
        if nowych:
            print(f"  [skutki] nowych reakcji na nasze tresci: {nowych}", flush=True)
            # POMIAR ZAMIAST ZALOZENIA. Nazwy pola `handle` w `kanal["users"]`
            # nie da sie potwierdzic z plikow na dysku — zaden zapisany zrzut
            # tej odpowiedzi nie istnieje. Ta linijka sprawia, ze PIERWSZY
            # przebieg po wdrozeniu odpowiada na to pomiarem: „0 z uchwytem"
            # znaczy, ze pole nazywa sie inaczej, i widac to od razu, zamiast
            # po tygodniu cichych `null` w dzienniku.
            print("  [skutki] reagujacych z uchwytem: %d, bez uchwytu: %d"
                  % (z_uchwytem, bez_uchwytu), flush=True)
        return nowych
    except Exception as exc:
        print(f"  (nie dopisalem skutkow: {type(exc).__name__})", flush=True)
        return 0
    finally:
        page.close()
        browser.close()
        p.stop()


def odpowiedzi_na_nasze_komentarze(ile: int = 10) -> list[dict[str, Any]]:
    """Odpowiedzi na NASZE komentarze zostawione pod CUDZYMI tekstami.

    Trzecie miejsce, w ktorym toczy sie rozmowa, i jedyne, ktorego agent nie
    widzial wcale. Sprawdzal odpowiedzi pod wlasnymi notkami i pod wlasnymi
    artykulami — a komentarz zostawiony u kogos obcego zyje gdzie indziej i nie
    pojawia sie w zadnym z tych dwoch zrodel. Nie chodzilo o opoznienie: takiej
    odpowiedzi agent nie zobaczylby nigdy.

    Dla mlodego konta to najgorsze mozliwe miejsce na milczenie, bo wlasnie tam
    zaczyna sie rozmowa z ludzmi, ktorzy nas jeszcze nie znaja.

    Zrodlem jest `activity-feed-web` — to samo, czego uzywa zakladka „Activity".
    Zdarzenie `comment_reply` niesie numer NASZEGO komentarza i numer ICH
    odpowiedzi, a w tej samej odpowiedzi przychodza tresci, autorzy i posty,
    wiec nie trzeba o nic dopytywac.

    Nie mylic z `note_reply`: to odpowiedzi pod naszymi notkami, ktore obsluguje
    `nieodpowiedziane`. Braloby sie je tu drugi raz.
    """
    wymagaj_sesji()
    p, browser, context = podlacz_sie()
    page = context.new_page()
    try:
        profil = api_json(page, f"/api/v1/user/{PROFIL_HANDLE}/public_profile")
        moje_id = (profil or {}).get("id")
        if not moje_id:
            return []

        kanal = api_json(page, "/api/v1/activity-feed-web?filter=all") or {}
        if not isinstance(kanal, dict):
            return []

        # Tresci lezą obok zdarzen, w kilku workach naraz — sklejamy w jeden.
        wpisy: dict[Any, dict] = {}
        for worek in ("comments", "feedItemComments", "communityComments"):
            for c in kanal.get(worek) or []:
                if isinstance(c, dict) and c.get("id") is not None:
                    wpisy.setdefault(c["id"], c)
        ludzie = {u["id"]: u for u in (kanal.get("users") or [])
                  if isinstance(u, dict) and u.get("id") is not None}
        posty = {x["id"]: x for x in (kanal.get("posts") or [])
                 if isinstance(x, dict) and x.get("id") is not None}

        czekaja: list[dict[str, Any]] = []
        for zdarzenie in kanal.get("activityItems") or []:
            if not isinstance(zdarzenie, dict):
                continue
            if zdarzenie.get("type") != "comment_reply":
                continue
            ich_id = zdarzenie.get("comment_id")
            nasz_id = zdarzenie.get("target_comment_id")
            if not ich_id or not nasz_id:
                continue

            ich = wpisy.get(ich_id) or {}
            nasz = wpisy.get(nasz_id) or {}
            tekst = ich.get("body") or ""
            if not tekst.strip():
                continue

            # Czy juz odpisalismy PO ich odpowiedzi. Pytamy watku, nie wlasnego
            # zapisu: po restarcie zapis klamie, Substack wie na pewno.
            watek = api_json(page, f"/api/v1/reader/comment/{ich_id}/replies"
                                   f"?comment_id={ich_id}") or {}
            plaskie = [c for g in (watek.get("commentBranches") or [])
                       for c in _plaskie(g)]
            # Porownujemy CZAS, nie napisy: `created_at` zdarzenia i `date`
            # komentarza bywaja zapisane inaczej (raz z milisekundami, raz bez),
            # a porownanie tekstowe daloby wtedy cichy falsz.
            kiedy_ich = _kiedy({"date": zdarzenie.get("created_at")})
            if any(c.get("user_id") == moje_id and _kiedy(c) > kiedy_ich
                   for c in plaskie):
                continue

            autor = (ich.get("name")
                     or (ludzie.get((zdarzenie.get("recent_sender_ids") or [None])[0])
                         or {}).get("name") or "")
            post = posty.get(zdarzenie.get("target_post_id")) or {}
            czekaja.append({
                "pod_czym": (nasz.get("body") or "")[:400],
                # Odpowiadamy ICH komentarzowi, nie swojemu — inaczej wpis
                # wyladowalby obok rozmowy zamiast w niej.
                "pod_id": ich_id,
                "autor": autor,
                "jezyk": ich.get("language"),
                "tekst": tekst,
                "id": ich_id,
                "gdzie": "komentarz_obcy",
                "kontekst": f"our own comment under \"{post.get('title') or 'someone else’s post'}\"",
                "url": post.get("canonical_url") or "",
            })
            if len(czekaja) >= ile:
                break

        if czekaja:
            print(f"  odpowiedzi na nasze komentarze u innych: {len(czekaja)}",
                  flush=True)
            for c in czekaja:
                print(f"    · {c['autor']} [{c.get('jezyk') or '?'}] {c['tekst'][:78]}",
                      flush=True)
        return czekaja
    except Exception as exc:
        print(f"  (nie sprawdzilem odpowiedzi u innych: {type(exc).__name__})",
              flush=True)
        return []
    finally:
        page.close()
        browser.close()
        p.stop()


def komentarze_pod_artykulami(ile: int = 5) -> list[dict[str, Any]]:
    """Cudze komentarze pod NASZYMI artykulami, na ktore nie odpisalismy.

    Kanal profilu pokazuje tylko notki, wiec artykuly wymagaja osobnego pytania.
    Bez tego czytelnik moglby zadac pytanie pod tekstem i nie doczekac sie
    odpowiedzi — a to szkodzi bardziej niz brak nowych komentarzy u obcych.
    """
    wymagaj_sesji()
    p, browser, context = podlacz_sie()
    page = context.new_page()
    czekaja: list[dict[str, Any]] = []
    try:
        moj = f"https://{config.SUBSTACK_HANDLE}.substack.com"
        profil = api_json(page, f"/api/v1/user/{PROFIL_HANDLE}/public_profile")
        moje_id = (profil or {}).get("id")
        posty = api_json(page, "/api/v1/posts?limit=10", baza=moj)
        lista = posty if isinstance(posty, list) else (posty or {}).get("posts") or []
        for post in lista[:ile]:
            if not isinstance(post, dict) or not post.get("id"):
                continue
            if not (post.get("comment_count") or 0):
                continue
            dane = api_json(page, f"/api/v1/post/{post['id']}/comments"
                                  "?all_comments=true", baza=moj)
            kom = dane if isinstance(dane, list) else (dane or {}).get("comments") or []
            nasze_daty = [_kiedy(k) for k in kom
                          if isinstance(k, dict) and k.get("user_id") == moje_id]
            nasz_ostatni = max(nasze_daty, default=0.0)
            for k in kom:
                if not isinstance(k, dict) or k.get("user_id") == moje_id:
                    continue
                if nasz_ostatni and _kiedy(k) < nasz_ostatni:
                    continue
                czekaja.append({
                    "pod_czym": (post.get("title") or "")[:200],
                    "pod_id": post["id"], "gdzie": "artykul",
                    "url": post.get("canonical_url") or "",
                    "autor": k.get("name"), "jezyk": k.get("language"),
                    "tekst": k.get("body") or "", "id": k.get("id"),
                    "data": k.get("date"),
                    "reakcje": k.get("reaction_count") or 0,
                })
        print(f"  pod artykulami czeka: {len(czekaja)}", flush=True)
        for c in czekaja[:5]:
            print(f"    · {c['autor']} pod {c['pod_czym'][:34]!r}: "
                  f"{c['tekst'][:52]}", flush=True)
        return czekaja
    except Exception as exc:
        print(f"  (nie sprawdzilem artykulow: {type(exc).__name__}: {exc})"[:150],
              flush=True)
        return czekaja
    finally:
        page.close()
        browser.close()
        p.stop()


def nieodpowiedziane(ile: int = 10) -> list[dict[str, Any]]:
    """Cudze odpowiedzi pod naszymi notkami, na które jeszcze nie odpisaliśmy.

    Treści bierzemy z API, nie ze strony: Substack tłumaczy cudze wpisy na język
    interfejsu, a odpowiedź po polsku komuś, kto pisał po angielsku, byłaby
    kompromitacją. W API `body` jest oryginałem, a `language` mówi, jak napisano.
    """
    wymagaj_sesji()
    p, browser, context = podlacz_sie()
    page = context.new_page()
    try:
        profil = api_json(page, f"/api/v1/user/{PROFIL_HANDLE}/public_profile")
        if not isinstance(profil, dict) or not profil.get("id"):
            print("  nie udało się odczytać profilu", flush=True)
            return []
        moje_id = profil["id"]
        feed = api_json(page, f"/api/v1/reader/feed/profile/{moje_id}"
                              "?types%5B%5D=note") or {}
        nasze = [x["comment"] for x in feed.get("items", [])
                 if isinstance(x, dict) and isinstance(x.get("comment"), dict)
                 and (x["comment"].get("children_count") or 0) > 0][:ile]

        czekaja: list[dict[str, Any]] = []
        for n in nasze:
            watek = api_json(page, f"/api/v1/reader/comment/{n['id']}/replies"
                                   f"?comment_id={n['id']}") or {}
            galezie = watek.get("commentBranches") or []
            wszystkie = [c for g in galezie for c in _plaskie(g)]
            # Nasz najnowszy głos w CAŁYM wątku, nie w pojedynczej gałęzi:
            # odpowiedź wpisana pod notką jest RODZEŃSTWEM cudzego komentarza,
            # więc liczenie wewnątrz gałęzi kazało odpisywać w kółko.
            nasz_ostatni = max((_kiedy(c) for c in wszystkie
                                if c.get("user_id") == moje_id), default=0.0)
            for g in galezie:
                plaskie = _plaskie(g)
                if not plaskie:
                    continue
                ostatni = max(plaskie, key=_kiedy)
                if ostatni.get("user_id") == moje_id:
                    continue
                if nasz_ostatni and _kiedy(ostatni) < nasz_ostatni:
                    continue
                czekaja.append({
                    "pod_czym": (n.get("body") or "")[:400], "pod_id": n["id"],
                    "autor": ostatni.get("name"), "jezyk": ostatni.get("language"),
                    "tekst": ostatni.get("body") or "", "id": ostatni.get("id"),
                    "data": ostatni.get("date"),
                })
        print(f"  czeka na odpowiedź: {len(czekaja)}", flush=True)
        for c in czekaja:
            print(f"    · {c['autor']} [{c.get('jezyk')}] {c['tekst'][:70]}",
                  flush=True)
        return czekaja
    finally:
        page.close()
        browser.close()
        p.stop()


def sluchaj_publikacji(page) -> list[int]:
    """Zbiera kody odpowiedzi na zapytania PUBLIKUJACE.

    Najpewniejsze zrodlo prawdy o tym, czy tresc poszla: wlasna odpowiedz
    Substacka na nasz zapis. Kanal profilu aktualizuje sie z opoznieniem —
    czasem ponad pol minuty — wiec sprawdzanie go zaraz po klknieciu dawalo
    falszywe "nie wyszlo" dla notek, ktore wyszly. To jest tez to, co research
    o awariach takich agentow zalecal wprost: patrzec na odpowiedz API zapisu,
    a nie na wlasny log sukcesu.
    """
    odpowiedzi: list = []
    page.on("response", lambda r: odpowiedzi.append(r)
            if "/api/v1/comment/feed" in r.url and r.request.method == "POST"
            else None)
    return odpowiedzi


def id_z_odpowiedzi(odpowiedzi: list) -> str:
    """Identyfikator notki, ktory Substack oddal przy zapisie.

    BRAKOWALO GO I TO ROZRYWALO POMIAR NA POL. Dziennik zapisywal osobno
    „wystawilismy notke o trybie samolotowym" i osobno „notka 315733831
    zebrala trzy polubienia" — bez zadnego pola, po ktorym da sie stwierdzic,
    czy to ta sama. Wiedzielismy, ze publikujemy, i nie wiedzielismy, co
    z tego dziala.

    Bralismy z odpowiedzi WYLACZNIE kod HTTP, a tresc — z identyfikatorem
    utworzonej notki — szla do kosza.

    Ciala odpowiedzi czytamy DOPIERO TU, po klknieciu i odczekaniu, a nie
    w callbacku zdarzenia: w callbacku tresc bywa jeszcze niedostepna i
    czytanie jej potrafi rzucic. Brak identyfikatora nie jest bledem —
    notka wyszla albo nie wyszla niezaleznie od tego, czy umiemy ja pozniej
    odnalezc.
    """
    for r in odpowiedzi:
        try:
            if r.status != 200:
                continue
            dane = r.json()
        except Exception:
            continue
        # Ksztalt odpowiedzi nie jest przez nikogo obiecany, wiec sprawdzamy
        # kilka miejsc zamiast zakladac jedno.
        for wezel in (dane, (dane or {}).get("comment"), (dane or {}).get("item")):
            if isinstance(wezel, dict) and wezel.get("id") is not None:
                return str(wezel["id"])
    return ""


def numer_naszej_notki(page, tekst: str, prob: int = 4) -> str:
    """Numer notki odczytany z NASZEGO PROFILU po jej tresci.

    DRUGIE PODEJSCIE DO TEGO SAMEGO PROBLEMU. Pierwsze — `id_z_odpowiedzi` —
    czyta cialo odpowiedzi HTTP po klknieciu „Post". Zmierzone na dzienniku:
    z 29 wystawionych notek numer trafil do dziennika SZESC RAZY. Ksztaltu tej
    odpowiedzi nikt nie obiecuje i najwyrazniej sie zmienil.

    Tu pytamy o to, co Substack POKAZUJE, a nie co odpowiedzial: kanal profilu
    oddaje nasze notki razem z numerami. Dopasowujemy po pierwszych 60 znakach
    tresci — dosc, zeby odroznic dwie notki, i odporne na to, ze Substack
    przycina albo formatuje tekst.

    Zwraca pusty napis, gdy nie znalazl. Brak numeru NIE jest bledem publikacji:
    notka wyszla albo nie wyszla niezaleznie od tego, czy umiemy ja pozniej
    odnalezc — ale bez numeru nie zmierzymy, co przyniosla.
    """
    probka = plaski(tekst)[:60]
    profil = api_json(page, f"/api/v1/user/{PROFIL_HANDLE}/public_profile")
    if not isinstance(profil, dict) or not profil.get("id"):
        return ""
    for nr in range(prob):
        feed = api_json(page, f"/api/v1/reader/feed/profile/{profil['id']}"
                              "?types%5B%5D=note")
        for poz in (feed or {}).get("items") or []:
            k = poz.get("comment") if isinstance(poz, dict) else None
            if not isinstance(k, dict):
                continue
            tresc = " ".join(str(k.get("body") or "").split())
            if probka and probka in plaski(tresc) and k.get("id") is not None:
                return str(k["id"])
        if nr < prob - 1:
            page.wait_for_timeout(8000)
    return ""


def potwierdz_notke(page, tekst: str, prob: int = 4) -> bool:
    """Pyta Substacka, czy notka naprawdę wisi na naszym profilu.

    Pyta KILKA RAZY, bo kanał profilu aktualizuje się z opóźnieniem. Pojedyncze
    sprawdzenie po sześciu sekundach zwracało "nie ma" dla notki, która wyszła
    poprawnie — a fałszywy alarm w tę stronę jest grozniejszy niz brak
    potwierdzenia: rozbraja zabezpieczenie przed wystawieniem tego samego
    drugi raz.

    Stoi na `numer_naszej_notki`, bo to jest to samo pytanie: notka wisi
    wtedy, gdy ma numer na naszym profilu. Wczesniej ta funkcja robila
    DOKLADNIE TEN SAM przebieg po kanale, po czym wyrzucala numer i zwracala
    samo tak — czyli ten sam blad, co przy ciele odpowiedzi HTTP.
    """
    return bool(numer_naszej_notki(page, tekst, prob=prob))

_AUTOR_PRZY_PRZYCISKU = """
el => {
  let w = el;
  for (let i = 0; i < 12 && w; i++) {
    w = w.parentElement;
    if (!w) break;
    const a = w.querySelector('a[href*="/@"]');
    if (a) return {href: a.getAttribute('href') || '',
                   tekst: (a.textContent || '').trim().slice(0, 80)};
  }
  return null;
}
"""


def _autor_przy_przycisku(przycisk) -> dict[str, str] | None:
    """Kto napisal wpis, przy ktorym stoi ten przycisk.

    Szuka W GORE od przycisku pierwszego odnosnika do profilu. Zmierzone na
    zywym kanale: autor stoi jeden poziom wyzej, 5 na 5 wpisow.

    Nie podnosi wyjatku — brak autora ma znaczyc „nie wiem", a nie „przerwij
    polubienia". Zapis jest premia, samo dzialanie wazniejsze.
    """
    try:
        dane = przycisk.evaluate(_AUTOR_PRZY_PRZYCISKU)
    except Exception:
        return None
    if not isinstance(dane, dict):
        return None
    nazwa = " ".join(str(dane.get("tekst") or "").split())
    uchwyt = str(dane.get("href") or "").rsplit("/@", 1)[-1].strip("/")
    if not nazwa and not uchwyt:
        return None
    return {"nazwa": nazwa or uchwyt, "uchwyt": uchwyt}


# ODCZYT STANU PYTA NAJPIERW, CZY WEZEL NADAL JEST W DOKUMENCIE.
#
# Docstring `potwierdz_polubienie` zakladal lancuch: React podmienia wezel ->
# uchwyt odpiety -> `evaluate` rzuca -> `None` -> liczymy na korzysc. Srodkowe
# ogniwo jest ZALOZENIEM, ktorego nikt tu nie zmierzyl, a Playwrighta nie ma
# lokalnie i zywych przebiegow nie wolno robic dla samego sprawdzenia. Jesli
# odpiety wezel zyje dalej w stercie JS — a tak dziala DOM, dopoki cokolwiek
# trzyma referencje — to `evaluate` NIE rzuci, tylko odda STARE atrybuty.
# Wyszloby `po == przed`, czyli twarde „nie udalo sie" i utrata slotu przy
# polubieniu, ktore weszlo.
#
# Nie zgadujemy wiec, co zrobi Playwright: pytamy o to sam wezel. `isConnected`
# jest wlasnoscia DOM (nie Playwrighta) i mowi wprost, czy element wisi jeszcze
# w dokumencie. Wezel poza dokumentem oddaje `null`, czyli „nie wiem" — ta sama
# odpowiedz, co rzucony wyjatek, i ta sama, ktora `potwierdz_polubienie` liczy
# na korzysc polubienia. Odpowiedz przestaje zalezec od tego, czy cos rzuci.
_STAN_PRZYCISKU = """
el => {
  if (!el.isConnected) return null;
  const a = n => el.getAttribute(n) || '';
  return [a('aria-pressed'), a('aria-checked'), a('aria-label'), a('title'),
          a('class'), (el.innerText || '').trim(), el.innerHTML].join('|');
}
"""


def _uchwyt_wezla(lokator):
    """Uchwyt do KONKRETNEGO wezla DOM, albo None. Nie podnosi wyjatku.

    Lokator `przyciski.nth(i)` wyszukuje po nazwie „Like" za kazdym razem od
    nowa, wiec po polubieniu — gdy Substack przerysuje przycisk — ten sam
    `nth(i)` moze pokazywac juz INNY wpis. Do porownania „przed i po" trzeba
    czegos, co zostaje przy tym samym elemencie.
    """
    try:
        return lokator.element_handle(timeout=5000)
    except Exception:
        return None


def _stan_przycisku(uchwyt) -> str | None:
    """Jak przycisk wyglada — wszystkie sygnaly naraz, sklejone w jeden napis.

    Nie zgadujemy, PO CZYM Substack pokazuje polubienie. Audyt z 23 sierpnia
    proponowal `aria-pressed`, ale tego atrybutu nikt na tym kanale nie
    zmierzyl, a sprawdzanie jednego atrybutu, ktorego moze nie byc, dawaloby
    „nie udalo sie" przy KAZDYM polubieniu. Bierzemy wiec wszystko, co widac
    na przycisku: stan, nazwe, klase, tekst i wnetrze. Polubienie, ktore
    weszlo, zmienia co najmniej jedno — licznik, napis albo wypelnienie serca.

    None znaczy „nie odczytalem", nie „bez zmian" — patrz `potwierdz_polubienie`.
    Sa TRZY drogi do tego None i wszystkie prowadza do tej samej odpowiedzi:
    brak uchwytu, wyjatek (zniszczony kontekst po nawigacji) i `null` oddane
    przez sam skrypt, gdy wezel wypadl z dokumentu. Ostatnia jest tu nowa
    i celowa — patrz komentarz przy `_STAN_PRZYCISKU`.
    """
    if uchwyt is None:
        return None
    try:
        stan = uchwyt.evaluate(_STAN_PRZYCISKU)
    except Exception:
        return None
    return stan if isinstance(stan, str) else None


def potwierdz_polubienie(uchwyt, przed: str | None) -> bool | None:
    """Czy przycisk po klknieciu wyglada inaczej niz przed nim.

    True  — zmienil sie, klik cos zrobil.
    False — oba stany odczytane i IDENTYCZNE, czyli klik nie zrobil nic.
    None  — nie wiadomo (nie dalo sie odczytac stanu; React potrafi podmienic
            caly wezel, a wtedy uchwyt jest odpiety od dokumentu).

    NIE OPIERAMY SIE NA TYM, ZE COS RZUCI. Pierwsza wersja tego opisu zakladala,
    ze odpiety wezel wywoła wyjatek w `evaluate` — zalozenie, ktorego nikt nie
    zmierzyl, a ktore przy odpietym (lecz zywym) wezle daje odczyt STARYCH
    atrybutow, czyli `po == przed`, czyli twarde False. Dlatego skrypt sam pyta
    o `isConnected` i oddaje `null`, gdy wezla nie ma juz w dokumencie.

    NIEPEWNOSC LICZYMY NA KORZYSC POLUBIENIA i to jest decyzja, nie
    niedbalstwo. Dziennik jest JEDYNYM licznikiem lajkow dnia — Substack nie
    oddaje naszych polubien zadnym endpointem, patrz `z_dziennika_dzis` —
    wiec falszywe „nie udalo sie" zaniza licznik i nastepny przebieg bierze
    pelny dzienny przydzial od nowa. Ten sam mechanizm zamienil budzet
    1 subskrypcji na 1 subskrypcje NA PRZEBIEG (25 i 26 sierpnia: plan 1,
    wykonanie 2). Falszywe „udalo sie" kosztuje jeden slot, falszywe „nie
    udalo sie" kosztuje cala dzienna norme — dlatego progi sa niesymetryczne.
    """
    if przed is None:
        return None
    po = _stan_przycisku(uchwyt)
    if po is None:
        return None
    return po != przed


def polub_w_kanale(ile: int, wyslij: bool = False) -> dict[str, Any]:
    """Polubienia w kanale czytelnika.

    Polubienie jest najtańszym uczciwym sygnałem, jaki konto może wysłać, i
    jedynym, który nic nie twierdzi — dlatego wolno je robić bez pytania.
    Odstępy między kliknięciami są losowe: piętnaście polubień w półtorej minuty
    to nie jest czytanie i każdy system to widzi.
    """
    import random

    wyslij = naprawde_wyslac(wyslij, "polubienia")
    wymagaj_sesji()
    p, browser, context = podlacz_sie()
    page = context.new_page()
    wynik: dict[str, Any] = {"znalezione": 0, "polubione": 0, "blad": None}
    try:
        page.goto("https://substack.com/", timeout=READ_TIMEOUT_MS * 2,
                  wait_until="domcontentloaded")
        page.wait_for_timeout(SETTLE_MS + 6000)

        # OTWARTE, SWIADOMIE NIETKNIETE: ten lokator nie ma `exact=True`, wiec
        # Playwright dopasowuje po PODCIAGU — zlapie takze „Liked" i „Unlike",
        # gdyby Substack tak nazywal przycisk po polubieniu. Klikniecie
        # w polubiony wpis ZDEJMUJE polubienie, a sprawdzenie stanu ponizej
        # tego nie wylapie: zdjecie polubienia tez zmienia przycisk.
        # `_klik_na_profilu` ma `exact=True` wlasnie dlatego.
        #
        # Nie zmieniam tego bez pomiaru na zywym kanale. Gdyby pelna nazwa
        # brzmiala inaczej niz „Like", `exact=True` wylaczyloby polubienia
        # CALKOWICIE i nikt by tego nie zauwazyl — dziennik zapisywalby po
        # prostu zero prob, czyli to samo, co spokojny dzien.
        przyciski = page.get_by_role("button", name="Like")
        wynik["znalezione"] = przyciski.count()
        print(f"  do polubienia w kanale: {wynik['znalezione']}", flush=True)

        for i in range(min(ile, przyciski.count())):
            kandydat = przyciski.nth(i)
            try:
                if not kandydat.is_visible():
                    continue
                # CZYJ TO WPIS. Polubienie zapisywalo sie jako
                # `{kiedy, rodzaj, udane}` i nic wiecej — 151 polubien wobec
                # 95 komentarzy, czyli NAJCZESTSZE nasze dzialanie, i jedyne,
                # o ktorym nie wiedzielismy zupelnie nic poza tym, ze bylo.
                #
                # Ma to takie samo znaczenie, co przy komentarzach: konto o AI,
                # ktore lajkuje pod rezerwa paliwowa, wydaje najczestszy gest
                # na publicznosc bez powodu, zeby nas obserwowac. Bez zapisu
                # nie da sie tego nawet ZMIERZYC, a wiec i naprawic.
                #
                # Zmierzone przed napisaniem tego kodu: autor stoi JEDEN poziom
                # nad przyciskiem, 5 na 5 sprawdzonych wpisow w kanale.
                kto = _autor_przy_przycisku(kandydat)
                if not wyslij:
                    wynik["polubione"] += 1
                    continue
                kandydat.scroll_into_view_if_needed(timeout=8000)
                # KLIKNIECIE NIE JEST DOWODEM — ta sama zasada, ktora przy
                # komentarzu, notce i odpowiedzi jest przestrzegana od dawna,
                # a przy polubieniach nie byla wcale. Zapis szedl w NASTEPNEJ
                # linii po `click()`, wiec wszystkie 151 polubien w dzienniku
                # na 31 sierpnia bylo „udanych" z definicji. Klik, ktory
                # Playwright wykonal, a Substack odrzucil (limit po ich
                # stronie, sesja wygasla w polowie przebiegu, przycisk
                # przerysowany przez Reacta miedzy `is_visible` a `click`),
                # zjadal slot z dziennego budzetu i zawyzal jedyna miare
                # skutecznosci, jaka `alarm.przeglad` ma.
                uchwyt = _uchwyt_wezla(kandydat)
                przed = _stan_przycisku(uchwyt)
                kandydat.click(timeout=8000)
                # Przycisk przerysowuje sie dopiero po odpowiedzi Substacka.
                page.wait_for_timeout(1500)
                potwierdzone = potwierdz_polubienie(uchwyt, przed)
                opis = ({"publikacja": kto["nazwa"], "komu": kto["uchwyt"]}
                        if kto else {})
                if potwierdzone is False:
                    print("    (klikniete, ale przycisk sie nie zmienil —"
                          " nie licze tego jako polubienia)", flush=True)
                    zapisz_w_dzienniku("polubienie", udane=False,
                                       powod="przycisk nie zmienil stanu"
                                             " po klknieciu", **opis)
                    page.wait_for_timeout(
                        int(random.uniform(*config.ODSTEPY["lajk"]) * 1000))
                    continue
                wynik["polubione"] += 1
                print("  polubione %d/%d%s%s"
                      % (wynik["polubione"], ile,
                         ("  — %s" % kto["nazwa"]) if kto else "",
                         "" if potwierdzone else "  (bez potwierdzenia)"),
                      flush=True)
                zapisz_w_dzienniku("polubienie", udane=True,
                                   potwierdzone=bool(potwierdzone), **opis)
                page.wait_for_timeout(
                    int(random.uniform(*config.ODSTEPY["lajk"]) * 1000))
            except Exception as exc:
                # POLKNIETA PORAZKA. Szlo do logu i nigdzie indziej, wiec
                # dziennik pokazywal same udane polubienia — a przy 67%
                # realizacji normy pytanie brzmi wlasnie „co sie nie udalo".
                powod = f"{type(exc).__name__}: {exc}"[:140]
                print(f"    (pominiete: {type(exc).__name__})", flush=True)
                zapisz_w_dzienniku("polubienie", udane=False, powod=powod)
        if not wyslij:
            print(f"  (nie klikam — tryb sprawdzenia; kliknalbym"
                  f" {wynik['polubione']})", flush=True)
    except Exception as exc:
        wynik["blad"] = f"{type(exc).__name__}: {exc}"[:200]
        print(f"  BŁĄD: {wynik['blad']}", flush=True)
    finally:
        page.close()
        browser.close()
        p.stop()
    return wynik


def _klik_na_profilu(handle: str, napisy: tuple[str, ...], rodzaj: str,
                     wyslij: bool) -> dict[str, Any]:
    """Klika JEDEN konkretny przycisk na cudzym profilu — i tylko jego.

    OBSERWOWANIE I SUBSKRYPCJA TO DWIE ROZNE RZECZY. Obserwowanie sprawia, ze
    czyjes notki pojawiaja sie w naszym kanale; subskrypcja przysyla jego teksty
    MAILEM do skrzynki wlasciciela. Biezace widelki sa osobne: 10-16 obserwacji
    miesiecznie i 12-20 subskrypcji.

    Jedna funkcja probowala kolejno „Subscribe", „Subskrybuj", „Follow",
    „Obserwuj" i brala pierwszy znaleziony. Na profilu Substacka „Subscribe" jest
    zawsze, wiec do „Follow" nie dochodzilo NIGDY — kazda z czterech prob
    w logach kliknela subskrypcje. Agent subskrybowal w tempie obserwacji.

    Gdy wlasciwego przycisku nie ma, nie robimy NIC. Klikniecie „w zastepstwie"
    to dokladnie ten blad, ktory to spowodowal.

    TA FUNKCJA OBSLUGUJE JUZ TYLKO SUBSKRYPCJE. Rozdzielenie napisow bylo
    konieczne, ale NIEWYSTARCZAJACE: obserwowania nie da sie tu zrobic zadnym
    zestawem napisow, bo przycisku obserwowania NIE MA na wierzchu strony —
    siedzi w menu pod kolkiem „...". Zmierzone 1 wrzesnia 2026: w naglowku
    profilu sa dokladnie trzy przyciski — „Subscribe", „Message" i kolko
    z `aria-label="Profile actions"`. Obserwowanie ma wiec wlasna droge,
    patrz `obserwuj_profil`.
    """
    wyslij = naprawde_wyslac(wyslij, rodzaj)
    wymagaj_sesji()
    p, browser, context = podlacz_sie()
    page = context.new_page()
    wynik: dict[str, Any] = {"handle": handle, "zrobione": False, "blad": None}
    try:
        page.goto(f"https://substack.com/@{handle}", timeout=READ_TIMEOUT_MS * 2,
                  wait_until="domcontentloaded")
        page.wait_for_timeout(SETTLE_MS + 4000)
        for nazwa in napisy:
            k = page.get_by_role("button", name=nazwa, exact=True).first
            if k.count() == 0 or not k.is_visible():
                continue
            print(f"  przycisk: {nazwa!r}  ({rodzaj})", flush=True)
            if not wyslij:
                print("  (nie klikam — tryb sprawdzenia)", flush=True)
                return wynik
            k.click(timeout=10_000)
            page.wait_for_timeout(5000)
            # Po kliknieciu napis zmienia sie na stan przeciwny.
            wynik["zrobione"] = k.count() == 0 or not k.is_visible()
            dopisz_wynik(rodzaj, wynik, komu=handle)
            print("  ZROBIONE" if wynik["zrobione"]
                  else "  KLIKNIETE, ALE STAN SIE NIE ZMIENIL", flush=True)
            return wynik
        wynik["blad"] = f"nie ma przycisku {rodzaj} u {handle}"
        print(f"  {wynik['blad']} — nie klikam nic innego", flush=True)
    except Exception as exc:
        wynik["blad"] = f"{type(exc).__name__}: {exc}"[:200]
        print(f"  BŁĄD: {wynik['blad']}", flush=True)
    finally:
        # BRAK PRZYCISKU TO TEZ WYNIK i musi zostawic slad. Bez tego blok
        # obserwacji, ktory nie znalazl ani jednego przycisku „Follow" przez
        # siedem dni, wygladal w dzienniku jak blok, ktory sie nie odbyl —
        # a on sie odbywal, chodzil po profilach i za kazdym razem odchodzil
        # z pustymi rekami. Tego nie da sie naprawic, czego nie widac.
        if wyslij:
            dopisz_wynik(rodzaj, wynik, komu=handle)
        page.close()
        browser.close()
        p.stop()
    return wynik


def pobierz_subskrybentow() -> dict[str, Any]:
    """Czyta liste subskrybentow z WLASNEGO panelu, wlasna sesja.

    ## Dlaczego to NIE jest to, czego wczesniej odmowilismy

    Odmowilismy ZGADYWANIA NIEUDOKUMENTOWANYCH ADRESOW API — `/api/v1/subscriber/csv`
    i podobnych, ktore zwracaja 404. Powtarzane sondowanie takich adresow to
    dokladnie to, co regulamin Substacka nazywa scrapingiem, a kopia listy ma
    konto CHRONIC, nie narazac.

    To jest co innego: wlasciciel patrzy na wlasny panel wlasna sesja. Ta sama
    przegladarka, ta sama sesja i ta sama droga, ktora agent od tygodni wystawia
    notki i komentarze. Zadnego cudzego konta, zadnego omijania limitow, zadnego
    adresu, ktorego panel sam by nie odpytal.

    ## Czego ta funkcja NIE gwarantuje i dlaczego to wazne

    Kompletu. Przy czterech subskrybentach tabela miesci sie na jednym ekranie,
    ale przy stu Substack doladowuje wiersze przy przewijaniu. Dlatego przewijamy
    do skutku i oddajemy `kompletna=False`, gdy liczba wierszy nadal rosla, kiedy
    skonczyl sie limit prob.

    NIEPELNA LISTA JEST GROZNIEJSZA NIZ JEJ BRAK: zapisana jako kopia wyglada
    jak komplet, a przy odtwarzaniu okazuje sie polowa. Dlatego decyzje o zapisie
    podejmuje `kopia_subskrybentow`, nie ta funkcja — tutaj oddajemy tylko fakty.
    """
    wymagaj_sesji()
    p, browser, context = podlacz_sie()
    page = context.new_page()
    wynik: dict[str, Any] = {"wiersze": [], "kompletna": False, "powod": ""}
    try:
        page.goto("https://%s.substack.com/publish/subscribers" % config.SUBSTACK_HANDLE,
                  timeout=READ_TIMEOUT_MS * 2, wait_until="domcontentloaded")
        page.wait_for_timeout(SETTLE_MS + 5000)

        # PRZEWIJAMY DO SKUTKU. Warunek konca to „dwa razy z rzedu tyle samo
        # wierszy", a nie „przewinelismy N razy" — inaczej wolna siec dawalaby
        # niepelna liste wygladajaca na pelna.
        ile_bylo, bez_zmian = -1, 0
        for _ in range(40):
            wiersze = _wiersze_subskrybentow(page)
            if len(wiersze) == ile_bylo:
                bez_zmian += 1
                if bez_zmian >= 2:
                    wynik["kompletna"] = True
                    break
            else:
                bez_zmian = 0
            ile_bylo = len(wiersze)
            page.mouse.wheel(0, 4000)
            page.wait_for_timeout(1200)
        else:
            wynik["powod"] = ("lista nadal rosla po 40 przewinieciach — "
                              "nie moge zarczyc, ze to komplet")

        wynik["wiersze"] = _wiersze_subskrybentow(page)
        if not wynik["wiersze"]:
            wynik["kompletna"] = False
            wynik["powod"] = ("panel nie oddal ani jednego adresu — zmienil sie "
                              "uklad strony albo wygasla sesja")
    except Exception as exc:
        wynik["kompletna"] = False
        wynik["powod"] = f"{type(exc).__name__}: {exc}"[:200]
    finally:
        page.close()
        browser.close()
        p.stop()
    return wynik


def zloz_wiersze_subskrybentow(surowe) -> list[dict[str, str]]:
    """Sklada wiersze z komorek tabeli panelu: adres, typ i data rozpoczecia.

    Osobna, CZYSTA funkcja — bez przegladarki — bo pierwsza wersja brala typ
    z `komorki[1]` na sztywno i wstawiala tam POWTORZONY ADRES. Wyszlo to
    dopiero na zywym pobraniu, przy ogladaniu zapisanego pliku. Nie polegamy
    juz na numerze kolumny: znajdujemy komorke z adresem i bierzemy NASTEPNA,
    bo w naglowku panelu typ stoi zaraz za subskrybentem.

    Nie polegamy tez na klasach CSS — Substack generuje je losowo
    (`container-_91AK1`), wiec selektor po klasie padnie przy pierwszym
    wdrozeniu po ich stronie.
    """
    import re

    adres_re = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
    wiersze: list[dict[str, str]] = []
    for komorki in surowe or []:
        komorki = [str(k or "").strip() for k in komorki]
        gdzie = next((i for i, k in enumerate(komorki)
                      if adres_re.fullmatch(k)), None)
        if gdzie is None:
            continue
        # Typ to nastepna komorka, ale nigdy druga kopia adresu ani pusta.
        typ = ""
        for k in komorki[gdzie + 1:]:
            if k and not adres_re.fullmatch(k):
                typ = k
                break
        wiersze.append({
            "email": komorki[gdzie],
            "typ": typ,
            "od": next((k for k in komorki[gdzie + 1:]
                        if re.search(r"\b(19|20)\d{2}\b", k)), ""),
        })
    return wiersze


def _wiersze_subskrybentow(page) -> list[dict[str, str]]:
    """Czyta komorki tabeli z panelu i oddaje je zlozone."""
    surowe = page.eval_on_selector_all(
        "table tr, [role=row]",
        "els => els.map(e => Array.from(e.querySelectorAll('td, [role=cell]'))"
        ".map(c => (c.innerText || '').trim()))")
    return zloz_wiersze_subskrybentow(surowe)


# --- OBSERWOWANIE SIEDZI W MENU „...", NIE NA WIERZCHU ----------------------
#
# 23 sierpnia 2026 uznalismy, ze Substack ZDJAL przycisk „Follow" z profili.
# Podstawa: szesc profili, slowo „Follow" nie wystepowalo w HTML ani razu.
# POMIAR BYL PRAWDZIWY, WNIOSEK FALSZYWY. Przycisk jest — siedzi w menu pod
# kolkiem „..." obok „Subscribe" i „Message", a to menu Substack DORYSOWUJE
# DOPIERO PO KLIKNIECIU. W HTML zamknietej strony faktycznie go nie ma, wiec
# pomiar nie mogl go zobaczyc i nie zobaczyl. Kosztowalo to dziewiec dni
# zerowych obserwacji, ktore nikomu nie wygladaly na awarie, bo tabela normy
# tlumaczyla je zdaniem o zdjetym przycisku.
#
# ZMIERZONE PONOWNIE 1 wrzesnia 2026, na zywej sesji na serwerze, przez
# otwarcie menu i ODCZYT (zadna pozycja nie zostala klknieta):
#
#   przycisk otwierajacy   aria-label="Profile actions" (en)
#                          aria-label="Działania w profilu" (pl)
#   menu, gdy NIE obserwujemy   Copy link / Share / Send message /
#                               Follow / Mute / Block / Report
#   menu, gdy JUZ obserwujemy   Copy link / Share / [Send message] /
#                               Unfollow / [Manage Subscription] /
#                               Mute / Block / Report
#
# Profile sprawdzone: @publikacja2, @czytelnik7, @czytelnik4 (nieobserwowani)
# oraz @autor1, @publikacja3, @publikacja1 (obserwowani).
#
# TRZY RZECZY, KTORE TEN POMIAR ROZSTRZYGA, A KTORYCH NIE WOLNO ZGADYWAC:
#
# 1. JEZYK NIE JEST WLASNOSCIA KONTA, TYLKO PRZEGLADARKI. Wlasciciel widzi
#    menu po polsku, a Chrome na serwerze — tym samym kontem, ta sama sesja —
#    po angielsku (`navigator.language` = en-US). Sprawdzone wprost: ta sama
#    strona otwarta z `locale="pl-PL"` oddaje „Skopiuj link / Udostępnij /
#    Wyślij wiadomość / Obserwuj / Wycisz / Zablokuj / Zgłoś". Dlatego etykiety
#    trzymamy PARAMI i nie zakladamy, ktora zobaczymy.
#
# 2. LICZBA POZYCJI I ICH KOLEJNOSC SIE ZMIENIAJA. „Send message" znika u
#    jednych, „Manage Subscription" dochodzi u innych — menu ma raz 7, raz 8
#    pozycji, a „Follow" stoi raz na czwartym, raz na trzecim miejscu. Wybor
#    po numerze pozycji trafilby predzej czy pozniej w „Mute" albo „Block".
#
# 3. „Unfollow" ZAWIERA W SOBIE „Follow". Dopasowanie po fragmencie tekstu —
#    domyslne `exact=False` w Playwrighcie — na profilu JUZ OBSERWOWANYM
#    trafiloby w „Unfollow" i ODOBSERWOWALOBY kogos w bloku, ktory ma
#    obserwowac. Dlatego teksty czytamy sami i porownujemy przez `==`, zamiast
#    powierzac to dopasowywaczowi biblioteki.
MENU_PROFILU = ("Profile actions", "Działania w profilu")

# Pozycja, ktora obserwuje. Klikamy WYLACZNIE cos, co jest na tej liscie.
OBSERWUJ_POZYCJE = ("Follow", "Obserwuj")

# Pozycja, ktora ODOBSERWOWUJE. To nie jest lista do klikania, tylko do
# ROZPOZNAWANIA: jej obecnosc znaczy „juz go obserwujemy" i wtedy nie klikamy
# NIC. Sluzy tez za potwierdzenie po klknieciu — patrz `potwierdz_obserwacje`.
JUZ_OBSERWUJEMY_POZYCJE = ("Unfollow", "Przestań obserwować")


def _pozycje_menu(page) -> list[str]:
    """Teksty pozycji OTWARTEGO menu, w kolejnosci ekranu. Nic nie klika.

    Bierzemy `role=menuitem`, bo tylko to Substack nadaje pozycjom menu —
    klasy CSS sa generowane losowo (`item-Npdq6R`) i padna przy pierwszym
    wdrozeniu po ich stronie.
    """
    pozycje = page.get_by_role("menuitem")
    teksty: list[str] = []
    for i in range(pozycje.count()):
        try:
            # Sklejamy biale znaki, bo pozycja bywa lamana na dwie linie,
            # a porownujemy pozniej przez rownosc.
            teksty.append(" ".join(pozycje.nth(i).inner_text().split()))
        except Exception:
            teksty.append("")
    return teksty


def _otworz_menu_profilu(page) -> bool:
    """Klika kolko „..." w naglowku profilu. Otwarcie menu nie zmienia stanu.

    NIE SZUKAMY PO NAZWIE „More". Pierwsze rozpoznanie zrobilo dokladnie to
    i `get_by_role("button", name="More")` trafilo w NASZ WLASNY pasek boczny —
    wyszlo menu „Saved / Archive / Appearance / Settings / Sign out", czyli
    ustawienia konta zamiast czynnosci profilu. Na stronie sa jeszcze menu
    „More options" przy KAZDEJ notce. Bierzemy wiec jedyna etykiete, ktora
    dotyczy profilu i wystepuje na stronie dokladnie raz.
    """
    for etykieta in MENU_PROFILU:
        kolko = page.locator('button[aria-label="%s"]' % etykieta)
        if kolko.count() == 0:
            continue
        kolko.first.click(timeout=10_000)
        # Menu rysuje sie po kliknieciu; 2,5 s wystarczylo na wszystkich
        # szesciu profilach w rozpoznaniu.
        page.wait_for_timeout(2500)
        return True
    return False


def potwierdz_obserwacje(page) -> bool | None:
    """Czy menu profilu mowi teraz, ze go OBSERWUJEMY. Otwiera menu i czyta.

    True  — jest pozycja odobserwowania, czyli obserwacja weszla.
    False — nadal jest pozycja „Obserwuj", czyli klik nic nie zrobil.
    None  — nie wiadomo: menu sie nie otworzylo albo nie ma ani jednej,
            ani drugiej pozycji (zmieniony uklad, wygasla sesja).

    TO JEST MOCNIEJSZE POTWIERDZENIE NIZ PRZY POLUBIENIU i dlatego wyglada
    inaczej. Przy lajku nie ma czego zapytac poza samym przyciskiem, wiec
    `potwierdz_polubienie` porownuje jego wyglad przed i po. Tutaj Substack
    sam odpowiada na pytanie „czy obserwujesz": menu podmienia „Follow" na
    „Unfollow". Pytamy wiec o STAN, a nie o to, czy cos drgnelo.

    NIEPEWNOSC LICZYMY NA KORZYSC OBSERWACJI — ta sama decyzja i ten sam
    powod, co w `potwierdz_polubienie`. Dziennik jest jedynym licznikiem
    obserwacji dnia, wiec falszywe „nie udalo sie" moze kosztowac zaplanowana
    obserwacje z dnia, w ktorym przydzial wynosi jeden. Przy 10-16 miesiecznie
    plan daje srednio 0,43 na dobe, czyli obserwacje mniej wiecej co drugi dzien;
    falszywe „udalo sie" kosztuje jeden slot.
    Progi sa niesymetryczne swiadomie. Roznica wobec lajka jest taka, ze tu
    None powinno byc rzadkie: to nie „nie umiem odczytac przycisku", tylko
    „menu w ogole nie odpowiedzialo", czyli osobna awaria — i dlatego trafia
    do dziennika jako `potwierdzone=None`, a nie znika w „udane".
    """
    # OTWARTE, SWIADOMIE NIETKNIETE: te funkcje przeszla na zywo TYLKO droga
    # do klikniecia, nie samo potwierdzenie po nim. 1 wrzesnia 2026 puscilem
    # `obserwuj_profil(wyslij=False)` na czterech profilach (@publikacja2,
    # @czytelnik4 — wolne; @autor1, @publikacja3 — obserwowane)
    # i kod za kazdym razem otworzyl menu, odczytal 7 albo 8 pozycji i podjal
    # wlasciwa decyzje. Ale `wyslij=False` zatrzymuje sie PRZED klknieciem,
    # wiec galezi „klikamy, potem czytamy menu jeszcze raz" nie widzialem
    # w dzialaniu — sprawdzenie jej wymaga zaobserwowania kogos naprawde,
    # czego nie robie bez zgody wlasciciela.
    #
    # CO DOKLADNIE ZMIERZYC, ZEBY TO ZAMKNAC — jedna obserwacja, trzy odczyty
    # (stan na 1 wrzesnia 2026, nadal NIEWYKONANE):
    #
    #   1. `obserwuj_profil(<wolny profil>, wyslij=False)` — zapisz liste
    #      z wiersza „menu profilu @...": ma byc 7 albo 8 pozycji z „Follow";
    #   2. to samo z `wyslij=True` — jeden raz, na tym samym profilu;
    #   3. trzy zapisy o tym samym zdarzeniu musza sie zgodzic:
    #      * dziennik: `rodzaj="obserwacja"`, `udane=True`, `potwierdzone=True`,
    #      * `kogo_obserwujemy()["uchwyty"]` ma ten uchwyt,
    #      * `obserwuj_profil(ten sam profil, wyslij=False)` oddaje teraz
    #        `juz_obserwowany=True` — czyli menu po kliknieciu naprawde mowi
    #        „Unfollow", a nie tylko my tak twierdzimy.
    #
    # Gdyby wyszlo `potwierdzone=None` przy punkcie 3 mowiacym „Unfollow",
    # znaczy to, ze Substack PO KLIKNIECIU przerysowuje menu inaczej niz przy
    # zwyklym otwarciu — wtedy trzeba wydluzyc `wait_for_timeout(4000)`
    # w `obserwuj_profil`, a NIE zmieniac progow.
    #
    # Kosztem jest jedna nieodwracalna zmiana stanu konta, wiec wymaga zgody
    # wlasciciela. Do tego czasu notatka zostaje.
    if not _otworz_menu_profilu(page):
        return None
    teksty = _pozycje_menu(page)
    try:
        page.keyboard.press("Escape")
    except Exception:
        pass
    if any(t in JUZ_OBSERWUJEMY_POZYCJE for t in teksty):
        return True
    if any(t in OBSERWUJ_POZYCJE for t in teksty):
        return False
    return None


def obserwuj_profil(handle: str, wyslij: bool = False) -> dict[str, Any]:
    """Obserwuje cudzy profil — jego notki trafiaja do naszego kanalu.

    Nie przysyla nic mailem. Biezacy limit obserwacji jest wezszy niz limit
    subskrypcji: 10-16 miesiecznie wobec 12-20.

    NIE UZYWA `_klik_na_profilu`. Tamta funkcja szuka przycisku NA WIERZCHU
    strony i dla obserwacji nie mogla znalezc nic, bo na wierzchu sa tylko
    „Subscribe", „Message" i kolko „...". Zostaje przy subskrypcji, gdzie
    przycisk naprawde jest na wierzchu.

    ZADNEJ POZYCJI POZA „Follow"/„Obserwuj" NIE KLIKAMY. W tym samym menu
    stoja „Mute", „Block" i „Report" — klikniecie „w zastepstwie" jest tu
    duzo drozsze niz przy subskrypcji, bo blokady i zgloszenia nie cofa sie
    po cichu. Gdy pozycji nie ma, funkcja odchodzi z pustymi rekami i zapisuje
    powod.

    „JUZ GO OBSERWUJEMY" NIE JEST PORAZKA. Menu z pozycja „Unfollow" znaczy,
    ze pula sie wyczerpala — nie ze cos nie zadzialalo. Taki przebieg idzie do
    dziennika jako `obserwacja_pominieta` (`udane=True`), a nie jako nieudana
    `obserwacja`, i dopisuje uchwyt do `OBSERWOWANI`, zeby jutro nie kosztowal
    juz nawet wejscia na strone. Patrz komentarz przy `OBSERWOWANI`.
    """
    wyslij = naprawde_wyslac(wyslij, "obserwacja")
    wymagaj_sesji()
    p, browser, context = podlacz_sie()
    page = context.new_page()
    wynik: dict[str, Any] = {"handle": handle, "zrobione": False,
                             "juz_obserwowany": False, "potwierdzone": None,
                             "pozycje": [], "blad": None, "powod": None}
    try:
        page.goto(f"https://substack.com/@{handle}", timeout=READ_TIMEOUT_MS * 2,
                  wait_until="domcontentloaded")
        page.wait_for_timeout(SETTLE_MS + 4000)

        if not _otworz_menu_profilu(page):
            wynik["blad"] = f"nie ma kolka „...” na profilu {handle}"
            print(f"  {wynik['blad']}", flush=True)
            return wynik

        teksty = _pozycje_menu(page)
        wynik["pozycje"] = teksty
        print(f"  menu profilu @{handle}: {teksty}", flush=True)

        # NAJPIERW PYTAMY, CZY JUZ OBSERWUJEMY, i dopiero potem szukamy
        # czego kliknac. Odwrotna kolejnosc nic by nie zmienila przy dwoch
        # zmierzonych jezykach, ale przy trzecim, ktorego nie zmierzylem,
        # slowo „obserwuj" moze siedziec w obu pozycjach naraz. Wtedy ta
        # kolejnosc jest roznica miedzy „nie robimy nic" a „odobserwowalismy".
        juz = [t for t in teksty if t in JUZ_OBSERWUJEMY_POZYCJE]
        if juz:
            # `powod`, NIE `blad` — i to jest cala poprawka z 1 wrzesnia 2026.
            # Zastanie „Unfollow" znaczy, ze pula sie wyczerpala, a nie ze cos
            # zawiodlo. Dopoki siedzialo to w polu `blad`, `dopisz_wynik`
            # zapisywalo dzien jako PORAZKE obserwacji — czyli tak samo, jak
            # wygladalo zniknieciecie przycisku, ktore kosztowalo dziewiec dni.
            # Licznik nie mial jak odroznic tych dwoch rzeczy.
            wynik["juz_obserwowany"] = True
            wynik["powod"] = f"juz obserwujemy {handle} — menu pokazuje {juz[0]!r}"
            print(f"  {wynik['powod']} — nie klikam nic", flush=True)
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass
            return wynik

        # Rownosc, nie fragment: „Unfollow" zawiera w sobie „Follow".
        gdzie = next((i for i, t in enumerate(teksty)
                      if t in OBSERWUJ_POZYCJE), None)
        if gdzie is None:
            wynik["blad"] = (f"menu profilu {handle} nie ma pozycji obserwowania"
                             f" (jest: {', '.join(teksty) or 'nic'})")
            print(f"  {wynik['blad']} — nie klikam nic innego", flush=True)
            try:
                page.keyboard.press("Escape")
            except Exception:
                pass
            return wynik

        if not wyslij:
            print(f"  (nie klikam — tryb sprawdzenia; kliknalbym"
                  f" {teksty[gdzie]!r})", flush=True)
            return wynik

        # SPRAWDZAMY TEKST JESZCZE RAZ, TUZ PRZED KLIKNIECIEM. Numer `gdzie`
        # pochodzi z odczytu sprzed chwili, a menu jest rysowane Reactem —
        # gdyby przerysowalo sie miedzy odczytem a klikiem, ten sam numer
        # wskazywalby juz inna pozycje, a pod czwartym numerem stoi „Mute".
        # Klikamy tylko wtedy, gdy pod tym numerem NADAL stoi to, co czytalismy.
        cel = page.get_by_role("menuitem").nth(gdzie)
        teraz = " ".join(cel.inner_text().split())
        if teraz not in OBSERWUJ_POZYCJE:
            wynik["blad"] = (f"pozycja {gdzie} zmienila sie z {teksty[gdzie]!r}"
                             f" na {teraz!r} — nie klikam")
            print(f"  {wynik['blad']}", flush=True)
            return wynik
        cel.click(timeout=10_000)
        page.wait_for_timeout(4000)

        # ESCAPE PRZED POTWIERDZANIEM, ZEBY STAN MENU BYL ZNANY. Menu Substacka
        # zamyka sie po wyborze pozycji — tak dzialaja menu tego typu — ale
        # tego akurat NIE ZMIERZYLEM, bo pomiar byl czysto odczytowy i zadnej
        # pozycji nie klikalem. Gdyby menu zostalo otwarte, `potwierdz_
        # obserwacje` kliknelaby kolko po raz drugi i tym samym je ZAMKNELA,
        # a potem nie znalazlaby ani jednej pozycji i oddala None — czyli
        # „nie wiem" tam, gdzie odpowiedz byla na wyciagniecie reki. Escape na
        # zamknietym menu nic nie robi, wiec kosztuje nas zero.
        try:
            page.keyboard.press("Escape")
            page.wait_for_timeout(800)
        except Exception:
            pass

        wynik["potwierdzone"] = potwierdz_obserwacje(page)
        # None znaczy „nie odczytalem", nie „nie udalo sie" — patrz docstring
        # `potwierdz_obserwacje`. Tylko twarde False jest porazka.
        wynik["zrobione"] = wynik["potwierdzone"] is not False
        print("  ZROBIONE" if wynik["potwierdzone"] is True
              else ("  KLIKNIETE, ALE MENU NADAL PROPONUJE OBSERWOWANIE"
                    if wynik["potwierdzone"] is False
                    else "  KLIKNIETE, BEZ POTWIERDZENIA"), flush=True)
    except Exception as exc:
        wynik["blad"] = f"{type(exc).__name__}: {exc}"[:200]
        print(f"  BŁĄD: {wynik['blad']}", flush=True)
    finally:
        # BRAK POZYCJI TO TEZ WYNIK i musi zostawic slad — to jest dokladnie
        # ta dziura, przez ktora dziewiec dni zerowych obserwacji wygladalo
        # na blok, ktory sie nie odbywa. `dopisz_wynik` jest idempotentny,
        # wiec zapis stad nie dubluje niczego.
        if wyslij and (wynik["zrobione"] or wynik["juz_obserwowany"]):
            # PAMIETAMY, ZEBY NIE LOSOWAC TEGO SAMEGO JUTRO. Zapis idzie takze
            # przy `potwierdzone=None` (czyli „kliknelismy, nie odczytalismy
            # skutku"): jesli obserwacja jednak nie weszla, najblizszy zrzut
            # `/following` wyrzuci ten uchwyt z pamieci sam, bo przepisuje
            # liste w calosci. Falszywy wpis kosztuje wiec najwyzej jeden dzien
            # nieobecnosci w puli, a jego brak — powtorzone wejscie na profil.
            zapamietaj_obserwowanego(handle)
        if wyslij and wynik["juz_obserwowany"]:
            # NIE `dopisz_wynik`, I TO JEST SEDNO. Tamta funkcja zna dwa stany:
            # udane i nieudane — a „juz go obserwujemy" nie jest ani jednym,
            # ani drugim. Zapisane jako porazka zanizalo norme i podbijalo
            # `pod_rzad_zle` (dwie z rzedu zwalniaja caly blok), a zapisane
            # jako sukces klamaloby, ze obserwacji przybylo.
            #
            # OSOBNY `rodzaj` ZAMIAST OSOBNEGO POLA, bo `norma.wczytaj` dzieli
            # wpisy po `udane` i patrzy WYLACZNIE na `norma.RODZAJE`
            # („obserwacja" tam jest, „obserwacja_pominieta" nie ma i nie ma
            # miec). Dzieki temu licznik nie liczy tego ani do wykonanych, ani
            # do nieudanych, a `slad_dziennika` — ktory czyta KAZDY wpis —
            # nadal widzi, ze maszyna tego dnia zyla. Zero zmian w `norma.py`.
            zapisz_w_dzienniku("obserwacja_pominieta", udane=True, komu=handle,
                               powod=wynik["powod"], juz_obserwowany=True)
        elif wyslij:
            dopisz_wynik("obserwacja", wynik, komu=handle,
                         potwierdzone=wynik["potwierdzone"],
                         juz_obserwowany=wynik["juz_obserwowany"])
        page.close()
        browser.close()
        p.stop()
    return wynik


def kogo_polecamy(page=None) -> list[dict[str, Any]]:
    """Kogo nasza publikacja poleca — z API, nie z pamieci.

    `/api/v1/recommendations/from/<id publikacji>` oddaje liste. Pusta lista
    znaczy, ze nie polecamy nikogo — i tak bylo do 30 sierpnia 2026, przy
    zerowej liczbie subskrypcji przyslanych ta droga.
    """
    wlasny = page is None
    if wlasny:
        wymagaj_sesji()
        p, br, ctx = podlacz_sie()
        page = ctx.new_page()
    try:
        baza = f"https://{config.SUBSTACK_HANDLE}.substack.com"
        prof = api_json(page, "/api/v1/publication/self", baza=baza)
        ident = (prof or {}).get("id") if isinstance(prof, dict) else None
        if not ident:
            # Numer publikacji stoi tez przy kazdym naszym poscie.
            posty = api_json(page, "/api/v1/archive?limit=1", baza=baza)
            if isinstance(posty, list) and posty and isinstance(posty[0], dict):
                ident = posty[0].get("publication_id")
        if not ident:
            return []
        lista = api_json(page, f"/api/v1/recommendations/from/{ident}", baza=baza)
        return lista if isinstance(lista, list) else []
    finally:
        if wlasny:
            page.close()
            br.close()
            p.stop()


def polec_publikacje(fraza: str, powod: str,
                     wyslij: bool = False) -> dict[str, Any]:
    """Dodaje REKOMENDACJE publikacji. Domyslnie wypelnia i NIE zatwierdza.

    CZEMU NIE Z PROPOZYCJI SUBSTACKA. Ekran `/publish/recommendations` podsuwa
    dziesiec publikacji „ktore moze Pan/Pani chciec polecic". Sprawdzone
    30 sierpnia 2026 — z tych dziesieciu JEDNA dotykala AI:

        Publikacja Budowlana, Publikacja Miejska, mandates, Publikacja Wlasnej Domeny,
        Publikacja 1, It's Publikacja Srodowiskowa, Publikacja Umyslowa on Money,
        Publikacja Raportowa, Publikacja Kulinarna, People of Interest

    Substack liczy je z historii czytania konta, a ta pochodzi sprzed
    przestawienia na AI. To ta sama skaza, co w banku tematow i w dziewieciu
    promptach — tylko po stronie Substacka, gdzie nie da sie jej wyczyscic
    inaczej niz czytajac nowe rzeczy. Publikacja o AI polecajaca newsletter
    o masle to dokladnie ten „wyglad bota", ktorego wlasciciel nie chce.

    Dlatego szukamy SAMI: okno „Dodaj rekomendacje" ma pole „Wyszukaj osobe
    lub publikacje...". Sprawdzone na zywo.

    OPIS JEST WYMAGANY (Substack oznacza go „Wymagane"), i slusznie: polecenie
    bez powodu to sam podpis. `powod` idzie w pole „Powiedz swoim subskrybentom,
    za co pokochaja ten Substack".

    REKOMENDACJA JEST PUBLICZNA I TRWALA — stawia nasze nazwisko obok cudzego
    na stronie powitalnej i w pasku bocznym. Dlatego `wyslij=False` domyslnie,
    tak samo jak przy notce.
    """
    wyslij = naprawde_wyslac(wyslij, "rekomendacja")
    wymagaj_sesji()
    p, browser_, context = podlacz_sie()
    page = context.new_page()
    wynik: dict[str, Any] = {"fraza": fraza, "wpisane": False,
                             "zrobione": False, "blad": None}
    try:
        przed = {str(x.get("id") or x.get("publication_id"))
                 for x in kogo_polecamy(page) if isinstance(x, dict)}

        page.goto(f"https://{config.SUBSTACK_HANDLE}.substack.com"
                  "/publish/recommendations",
                  timeout=READ_TIMEOUT_MS * 2, wait_until="domcontentloaded")
        page.wait_for_timeout(SETTLE_MS + 4000)

        guzik = page.get_by_role("button", name="Dodaj rekomendację").first
        if guzik.count() == 0:
            wynik["blad"] = "nie ma przycisku „Dodaj rekomendację”"
            return wynik
        guzik.click(timeout=10_000)
        # OKNO POTRZEBUJE CZASU. Pierwsze rozpoznanie zajrzalo po 3,5 s i nie
        # zobaczylo ani okna, ani wyszukiwarki — wniosek „nie da sie wybrac
        # samemu" byl falszywy. Po 6 s oba sa na miejscu.
        page.wait_for_timeout(6000)

        szukajka = page.get_by_role("combobox").first
        if szukajka.count() == 0:
            wynik["blad"] = "okno sie otworzylo, ale nie ma wyszukiwarki"
            return wynik
        szukajka.fill(fraza, timeout=10_000)
        page.wait_for_timeout(5000)

        # Wybor z podpowiedzi. Bierzemy pozycje, ktora NAPRAWDE zawiera fraze —
        # klikniecie „w zastepstwie" to ten sam blad, przez ktory agent
        # subskrybowal zamiast obserwowac.
        trafienie = page.get_by_role("option", name=re.compile(
            re.escape(fraza.split()[0]), re.I)).first
        if trafienie.count() == 0:
            trafienie = page.get_by_text(fraza, exact=False).last
        if trafienie.count() == 0:
            wynik["blad"] = f"wyszukiwarka nie znalazla {fraza!r}"
            return wynik
        trafienie.click(timeout=10_000)
        page.wait_for_timeout(3000)

        opis = page.get_by_placeholder(re.compile("pokochaj", re.I)).first
        if opis.count():
            opis.fill(powod[:280], timeout=10_000)
            wynik["wpisane"] = True
        page.wait_for_timeout(1500)

        if not wyslij:
            print("  (nie zatwierdzam — tryb sprawdzenia)", flush=True)
            return wynik

        zatwierdz = page.get_by_role("button",
                                     name="Dodaj rekomendację").last
        zatwierdz.click(timeout=10_000)
        page.wait_for_timeout(6000)

        # SPRAWDZAMY SKUTEK, NIE TO, ZE KLIKNIECIE SIE NIE WYWALILO. Tak samo
        # jak przy pamieci platnych hostow: oslona `try` juz raz zamienila
        # blad w wypisane ostrzezenie, a funkcja po cichu nie robila nic.
        po = {str(x.get("id") or x.get("publication_id"))
              for x in kogo_polecamy(page) if isinstance(x, dict)}
        wynik["zrobione"] = len(po) > len(przed)
        wynik["polecanych_teraz"] = len(po)
        dopisz_wynik("rekomendacja", wynik, komu=fraza)
        print("  REKOMENDACJA DODANA" if wynik["zrobione"]
              else "  KLIKNIETE, ALE LISTA SIE NIE ZMIENILA", flush=True)
    except Exception as exc:
        wynik["blad"] = f"{type(exc).__name__}: {exc}"[:200]
        print(f"  [rekomendacja] {wynik['blad']}", flush=True)
    finally:
        page.close()
        browser_.close()
        p.stop()
    return wynik


def zasubskrybuj(handle: str, wyslij: bool = False) -> dict[str, Any]:
    """Subskrybuje cudzy profil. Ląduje w skrzynce właściciela, więc wąsko."""
    return _klik_na_profilu(handle, ("Subscribe", "Subskrybuj"), "subskrypcja",
                            wyslij)


def _esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def rozbierz_artykul(sciezka: Path) -> dict[str, Any]:
    """Rozkłada plik artykułu na tytuł, podtytuł i treść jako HTML.

    Treść idzie do edytora WKLEJENIEM HTML-a, nie wpisywaniem znak po znaku:
    Substack używa ProseMirror, który przy wpisywaniu gubi linki w źródłach —
    a nazwane źródła to obietnica z oświadczenia o AI, nie ozdoba.
    """
    linie = sciezka.read_text(encoding="utf-8").splitlines()
    tytul = linie[0].lstrip("# ").strip() if linie else ""
    podtytul = ""
    reszta: list[str] = []
    for i, l in enumerate(linie[1:], 1):
        s = l.strip()
        if not podtytul and s.startswith("*") and s.endswith("*") and len(s) > 2:
            podtytul = s.strip("*").strip()
            continue
        reszta.append(l)

    html: list[str] = []
    lista_otwarta = False
    for blok in "\n".join(reszta).split("\n\n"):
        b = blok.strip()
        if not b or b == "---":
            continue
        if b.startswith("## "):
            if lista_otwarta:
                html.append("</ul>")
                lista_otwarta = False
            html.append(f"<h2>{_esc(b[3:].strip())}</h2>")
            continue
        if b.startswith("- "):
            if not lista_otwarta:
                html.append("<ul>")
                lista_otwarta = True
            for poz in b.splitlines():
                poz = poz.strip()[2:].strip()
                m = re.match(r"\[(.+?)\]\((\S+?)\)$", poz)
                html.append(
                    f'<li><a href="{_esc(m.group(2))}">{_esc(m.group(1))}</a></li>'
                    if m else f"<li>{_esc(poz)}</li>"
                )
            continue
        if lista_otwarta:
            html.append("</ul>")
            lista_otwarta = False
        html.append(f"<p>{_esc(' '.join(b.split()))}</p>")
    if lista_otwarta:
        html.append("</ul>")
    return {"tytul": tytul, "podtytul": podtytul, "html": "".join(html)}


_JS_WKLEJ_HTML = """
([html]) => {
    const el = document.querySelector('.tiptap');
    if (!el) return false;
    el.focus();
    const dt = new DataTransfer();
    dt.setData('text/html', html);
    dt.setData('text/plain', '');
    el.dispatchEvent(new ClipboardEvent('paste',
        {clipboardData: dt, bubbles: true, cancelable: true}));
    return true;
}
"""

_JS_WKLEJ_OBRAZ = """
([b64]) => {
    const el = document.querySelector('.tiptap');
    if (!el) return false;
    el.focus();
    const bin = atob(b64);
    const arr = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
    const plik = new File([arr], 'naglowek.png', {type: 'image/png'});
    const dt = new DataTransfer();
    dt.items.add(plik);
    el.dispatchEvent(new ClipboardEvent('paste',
        {clipboardData: dt, bubbles: true, cancelable: true}));
    return true;
}
"""


def wypelnij_artykul(page, artykul: dict[str, Any], obraz: Path | None) -> None:
    """Wkłada tytuł, podtytuł, grafikę i treść do otwartego edytora.

    Grafika idzie W TREŚĆ, na samą górę — tak, jak robi to właściciel ręcznie.
    Szukałem osobnego slotu okładki i była to droga naokoło: obraz wklejony do
    treści edytor sam wysyła na swój serwer i sam robi z niego podgląd.
    """
    import base64

    page.locator("textarea.page-title").first.fill(artykul["tytul"])
    page.wait_for_timeout(400)
    if artykul.get("podtytul"):
        page.locator("textarea.subtitle").first.fill(artykul["podtytul"])
        page.wait_for_timeout(400)

    edytor = page.locator(".tiptap").first
    edytor.click()
    page.wait_for_timeout(400)
    page.keyboard.press("Control+a")
    page.keyboard.press("Delete")
    page.wait_for_timeout(400)

    # Treść wklejamy jako HTML, nie wpisujemy: ProseMirror gubi przy wpisywaniu
    # linki w źródłach, a nazwane źródła to obietnica z oświadczenia o AI.
    page.evaluate(_JS_WKLEJ_HTML, [artykul["html"]])
    page.wait_for_timeout(3000)
    print(f"  wklejona treść: {len(edytor.inner_text().split())} słów, "
          f"{page.locator('.tiptap a').count()} węzłów linkowych", flush=True)

    if obraz and obraz.exists():
        edytor.click()
        page.keyboard.press("Control+Home")
        page.wait_for_timeout(500)
        page.evaluate(_JS_WKLEJ_OBRAZ,
                      [base64.b64encode(obraz.read_bytes()).decode()])
        for _ in range(20):   # wysyłka na serwer Substacka trwa
            page.wait_for_timeout(1500)
            if page.locator(".tiptap img").count():
                break
        wgrany = page.locator(".tiptap img").count() > 0
        print(f"  grafika: {'wgrana' if wgrany else 'NIE WESZŁA'}", flush=True)

    wstaw_przycisk_subskrypcji(page)


def wstaw_przycisk_subskrypcji(page) -> bool:
    """Jeden przycisk subskrypcji, po ostatnim akapicie a przed źródłami.

    Tam ląduje argument, więc tam czytelnik decyduje — a ostatnią rzeczą na
    stronie zostaje lista źródeł, czyli podpis tego pisma i dokładnie to, co
    obiecuje oświadczenie o AI. Dwa przyciski byłyby nachalne przy piśmie,
    którego walutą jest powściągliwość.
    """
    naglowek = page.locator(".tiptap h1, .tiptap h2").filter(has_text="Sources").first
    if naglowek.count() == 0:
        print("  przycisk subskrypcji: brak nagłówka źródeł, pomijam", flush=True)
        return False
    akapit = naglowek.locator("xpath=preceding-sibling::p[1]")
    if akapit.count() == 0:
        return False
    akapit.click()
    page.keyboard.press("End")
    page.wait_for_timeout(600)

    for nazwa in ("Przycisk", "Button"):
        k = page.get_by_role("button", name=nazwa).first
        if k.count() > 0 and k.is_visible():
            k.click()
            break
    page.wait_for_timeout(2500)
    for nazwa in ("Subskrybuj", "Subscribe"):
        opcja = page.get_by_text(nazwa, exact=True).first
        if opcja.count() > 0 and opcja.is_visible():
            opcja.click()
            page.wait_for_timeout(3000)
            print("  przycisk subskrypcji wstawiony", flush=True)
            return True
    print("  przycisk subskrypcji: nie znalazłem opcji", flush=True)
    return False


def tresc_oswiadczenia() -> str:
    """Oświadczenie „Jak to robię" — z pliku, nie z drugiej kopii w kodzie.

    Tekst jest publiczny i wiążący, więc ma jedno źródło: cytat blokowy
    w `prompts/OSWIADCZENIE_AUTORSTWA.md`, gdzie leży razem z uzasadnieniem.
    """
    plik = config.PROMPTS_DIR / "OSWIADCZENIE_AUTORSTWA.md"
    linie = [l[2:].strip() for l in plik.read_text(encoding="utf-8").splitlines()
             if l.startswith("> ")]
    tekst = " ".join(linie).strip()
    if not tekst:
        raise RuntimeError("nie znalazłem treści oświadczenia w OSWIADCZENIE_AUTORSTWA.md")
    return tekst


def ustaw_oswiadczenie_ai(wyslij: bool = False) -> dict[str, Any]:
    """Ustawia stałe oświadczenie pokazywane każdemu, kto skanuje nas pod kątem AI.

    Ustawienie konta, nie posta — robi się raz i wisi przy wszystkim: przy
    artykułach, notkach i odpowiedziach.
    """
    wyslij = naprawde_wyslac(wyslij, "oswiadczenie")
    wymagaj_sesji()
    tekst = tresc_oswiadczenia()
    p, browser, context = podlacz_sie()
    page = context.new_page()
    wynik: dict[str, Any] = {"tekst": tekst, "zapisane": False, "blad": None}
    try:
        page.goto(f"https://{config.SUBSTACK_HANDLE}.substack.com/publish/post"
                  "?type=newsletter",
                  timeout=READ_TIMEOUT_MS * 2, wait_until="domcontentloaded")
        page.wait_for_timeout(SETTLE_MS + 5000)
        # Okno oświadczenia wisi pod skanowaniem AI, a to pod stroną ustawień.
        page.locator("textarea.page-title").first.fill("(ustawienie oświadczenia)")
        page.wait_for_timeout(600)
        for nazwa in ("Kontynuuj", "Continue"):
            k = page.get_by_role("button", name=nazwa).first
            if k.count() > 0 and k.is_visible():
                k.click()
                break
        page.wait_for_timeout(8000)
        for nazwa in ("Skanuj w poszukiwaniu tekstu AI", "Scan for AI text"):
            k = page.get_by_role("button", name=nazwa).first
            if k.count() > 0 and k.is_visible():
                k.click()
                break
        page.wait_for_timeout(9000)
        for nazwa in ("Utwórz oświadczenie", "Create", "How I"):
            k = page.get_by_role("button", name=nazwa).first
            if k.count() > 0 and k.is_visible():
                k.click()
                break
        page.wait_for_timeout(4000)

        # Pole oświadczenia to jedyna widoczna textarea BEZ atrybutu placeholder:
        # nazwy klas są zahaszowane, więc szukanie po nich zepsułoby się przy
        # najbliższej zmianie po stronie Substacka.
        pole = None
        for i in range(page.locator("textarea").count()):
            el = page.locator("textarea").nth(i)
            if el.is_visible() and not el.get_attribute("placeholder"):
                pole = el
                break
        if pole is None:
            raise RuntimeError("nie znalazłem pola oświadczenia")
        pole.fill(tekst)
        page.wait_for_timeout(1200)
        print(f"  wpisane oświadczenie: {len(tekst.split())} słów", flush=True)

        zapisz = None
        for nazwa in ("Zapisz oświadczenie", "Save statement", "Save"):
            k = page.get_by_role("button", name=nazwa).first
            if k.count() > 0 and k.is_visible():
                zapisz = k
                break
        wynik["przycisk_widoczny"] = zapisz is not None
        if wyslij and zapisz is not None:
            zapisz.click()
            page.wait_for_timeout(5000)
            wynik["zapisane"] = True
            print("  OŚWIADCZENIE ZAPISANE", flush=True)
        elif not wyslij:
            print("  (nie zapisuję — tryb sprawdzenia)", flush=True)
    except Exception as exc:
        wynik["blad"] = f"{type(exc).__name__}: {exc}"[:200]
        print(f"  BŁĄD: {wynik['blad']}", flush=True)
    finally:
        page.close()
        browser.close()
        p.stop()
    return wynik


def wystaw_odpowiedz_pod_artykulem(
    url_artykulu: str, autor: str, tekst: str, wyslij: bool = False,
) -> dict[str, Any]:
    """Odpowiada pod KONKRETNYM komentarzem pod naszym artykułem.

    Inny mechanizm niż pod notką: tam wątek jest płaski i odpowiada się w polu
    pod całą notką, tu każdy komentarz ma własny przycisk odpowiedzi. Dzięki temu
    rozmówca dostaje powiadomienie, a wątek czyta się jak rozmowa.
    """
    wyslij = naprawde_wyslac(wyslij, "odpowiedz pod artykułem")
    wymagaj_sesji()
    p, browser, context = podlacz_sie()
    page = context.new_page()
    wynik: dict[str, Any] = {"wpisane": False, "wyslane": False, "blad": None}
    try:
        page.goto(url_artykulu.rstrip("/") + "/comments",
                  timeout=READ_TIMEOUT_MS * 2, wait_until="domcontentloaded")
        page.wait_for_timeout(SETTLE_MS + 6000)
        page.mouse.wheel(0, 12_000)
        page.wait_for_timeout(2500)

        # Szukamy komentarza po autorze, a przycisk odpowiedzi w jego okolicy —
        # inaczej trafilibyśmy w cudzy wątek.
        # Przycisk odpowiedzi znajdujemy po ODLEGLOSCI OD KOMENTARZA, a nie po
        # drzewie DOM: uklad zmienia sie miedzy widokami, a przy wielu
        # komentarzach trafienie w cudzy watek byloby wpadka nie do cofniecia.
        wybrany = page.evaluate("""(autor) => {
            const kandydaci = [...document.querySelectorAll('*')].filter(
                n => !n.children.length &&
                     /^(reply|odpowiedz)$/i.test((n.innerText || '').trim()));
            const kotwice = [...document.querySelectorAll('*')].filter(
                n => !n.children.length &&
                     (n.innerText || '').trim() === autor);
            if (!kandydaci.length || !kotwice.length) return -1;
            const k = kotwice[0].getBoundingClientRect();
            let najlepszy = -1, naj = 1e9;
            kandydaci.forEach((c, i) => {
                const r = c.getBoundingClientRect();
                const d = Math.hypot(r.top - k.top, r.left - k.left);
                if (d < naj) { naj = d; najlepszy = i; }
            });
            kandydaci.forEach((c, i) => c.setAttribute('data-nia',
                                                       i === najlepszy ? '1' : '0'));
            return najlepszy;
        }""", autor)
        if wybrany < 0:
            raise RuntimeError("nie znalazłem przycisku odpowiedzi")
        przycisk = page.locator('[data-nia="1"]').first
        print(f"  przycisk odpowiedzi znaleziony przy komentarzu {autor!r}",
              flush=True)
        przycisk.click(timeout=15_000)
        page.wait_for_timeout(3000)

        pole = page.locator("textarea").first
        pole.click(timeout=10_000)
        page.keyboard.type(tekst, delay=12)
        page.wait_for_timeout(1500)
        wynik["wpisane"] = True
        print(f"  wpisane w pole odpowiedzi: {len(tekst.split())} słów", flush=True)

        wyslac = None
        for nazwa in ("Reply", "Post", "Odpowiedz", "Opublikuj"):
            k = page.get_by_role("button", name=nazwa).first
            if k.count() > 0 and k.is_visible():
                wyslac = k
                break
        wynik["przycisk_widoczny"] = wyslac is not None

        if wyslij and wyslac is not None:
            wyslac.click()
            wynik["klikniete"] = True     # jak w `wystaw_komentarz`
            page.wait_for_timeout(8000)
            odp = potwierdz_komentarz(page, url_artykulu, tekst)
            # DRUGA POLOWA DOWODU — jak w `wystaw_komentarz`. Tu chodzi
            # o komentarze pod NASZYM artykulem, wiec dzis zaden konsument
            # `o_hoscie` tego nie czyta; wzorzec jest ten sam i rozjechanie sie
            # trzech kopii tej sciezki juz raz nas kosztowalo.
            wynik["potwierdzenie_odpowiedzialo"] = True
            wynik["wyslane"] = odp
            dopisz_wynik("odpowiedz_pod_artykulem", wynik,
                               gdzie=url_artykulu, komu=autor,
                               slow=len(tekst.split()), tekst=tekst[:1200])
            print("  ODPOWIEDŹ POD ARTYKUŁEM POTWIERDZONA" if wynik["wyslane"]
                  else "  KLIKNIĘTE, ALE ODPOWIEDZI NIE WIDAĆ", flush=True)
        elif not wyslij:
            print("  (nie wysyłam — tryb sprawdzenia)", flush=True)
    except Exception as exc:
        wynik["blad"] = f"{type(exc).__name__}: {exc}"[:200]
        print(f"  BŁĄD: {wynik['blad']}", flush=True)
    finally:
        # TA SAMA DZIURA, CO W `wystaw_komentarz` — patrz komentarz przy jej
        # `finally`. Tutaj jedyne wyjscie bez zapisu bylo najgorsze z mozliwych:
        # `raise RuntimeError("nie znalazłem przycisku odpowiedzi")` znaczy, ze
        # ktos napisal pod NASZYM artykulem i nie dostal odpowiedzi — a dziennik
        # wygladal, jakbysmy w ogole nie probowali. Ta funkcja nie ma sciezki
        # „pominiete", wiec nie ma tu czego wykluczac.
        #
        # `try` wokol zapisu — z tego samego powodu, co w `wystaw_komentarz`:
        # budowanie argumentow potrafi rzucic, a wtedy `page.close()`,
        # `browser.close()` i `p.stop()` ponizej nie wykonuja sie wcale.
        try:
            if wyslij:
                dopisz_wynik("odpowiedz_pod_artykulem", wynik,
                             gdzie=url_artykulu, komu=autor,
                             slow=len(tekst.split()), tekst=tekst[:1200])
        except Exception as exc:
            print("  (nie zapisalem odpowiedzi pod artykulem do dziennika: %s)"
                  % type(exc).__name__, flush=True)
        page.close()
        browser.close()
        p.stop()
    return wynik


def potwierdz_artykul(page, tytul: str) -> bool:
    """Pyta Substacka, czy artykuł naprawdę jest opublikowany."""
    probka = plaski(tytul)[:50]
    dane = api_json(page, "/api/v1/posts?limit=5",
                    baza=f"https://{config.SUBSTACK_HANDLE}.substack.com")
    # Ten adres oddaje LISTE, nie obiekt z kluczem "posts" — sprawdzone na zywo.
    lista = dane if isinstance(dane, list) else (dane or {}).get("posts") or []
    return any(probka in plaski(x.get("title") or "") and x.get("post_date")
               for x in lista if isinstance(x, dict))

def wystaw_artykul(
    sciezka_md: Path, sciezka_png: Path | None = None, wyslij: bool = False,
) -> dict[str, Any]:
    """Wystawia artykuł na Substacku. Domyślnie WYPEŁNIA i NIE WYSYŁA."""
    wyslij = naprawde_wyslac(wyslij, "artykul")
    wymagaj_sesji()
    artykul = rozbierz_artykul(sciezka_md)
    if sciezka_png is None:
        kandydat = sciezka_md.with_suffix(".png")
        sciezka_png = kandydat if kandydat.exists() else None

    p, browser, context = podlacz_sie()
    page = context.new_page()
    wynik: dict[str, Any] = {"wypelnione": False, "wyslane": False, "blad": None,
                             "tytul": artykul["tytul"]}
    try:
        if wyslij and potwierdz_artykul(page, artykul["tytul"]):
            print("  artykul o tym tytule juz jest opublikowany — przerywam",
                  flush=True)
            wynik["wyslane"] = True
            wynik["pominiete"] = True
            return wynik

        page.goto(f"https://{config.SUBSTACK_HANDLE}.substack.com/publish/post"
                  "?type=newsletter",
                  timeout=READ_TIMEOUT_MS * 2, wait_until="domcontentloaded")
        page.wait_for_timeout(SETTLE_MS + 5000)
        wynik["szkic"] = page.url

        wypelnij_artykul(page, artykul, sciezka_png)
        wynik["wypelnione"] = True

        dalej = None
        for nazwa in ("Kontynuuj", "Continue", "Weiter"):
            k = page.get_by_role("button", name=nazwa).first
            if k.count() > 0 and k.is_visible():
                dalej = k
                break
        if dalej is None:
            raise RuntimeError("nie znalazłem przycisku przejścia do ustawień")
        dalej.click()
        page.wait_for_timeout(8000)

        if config.WYLACZ_WYKRYWANIE_AI:
            for nazwa in ("Wyłącz wykrywanie AI", "Turn off AI detection"):
                k = page.get_by_role("button", name=nazwa).first
                if k.count() > 0 and k.is_visible():
                    k.click()
                    page.wait_for_timeout(2500)
                    print("  wykrywanie AI wyłączone dla tego posta", flush=True)
                    break

        publikuj = None
        for nazwa in ("Wyślij teraz do wszystkich", "Send to everyone now",
                      "Send now", "Publish now"):
            k = page.get_by_role("button", name=nazwa).first
            if k.count() > 0 and k.is_visible():
                publikuj = k
                print(f"  przycisk publikacji: {nazwa!r}", flush=True)
                break
        wynik["przycisk_widoczny"] = publikuj is not None

        if wyslij and publikuj is not None:
            publikuj.click()
            page.wait_for_timeout(15000)
            wynik["wyslane"] = potwierdz_artykul(page, artykul["tytul"])
            dopisz_wynik("artykul", wynik,
                               tytul=artykul["tytul"])
            print("  ARTYKUŁ POTWIERDZONY U SUBSTACKA" if wynik["wyslane"]
                  else "  KLIKNIĘTE, ALE SUBSTACK GO NIE POKAZUJE", flush=True)
            if wynik["wyslane"]:
                # Artykuł idzie do promowania: jedna notka z linkiem dziennie
                # przez kolejne dni. Zapisujemy TU, bo tylko tutaj wiemy na pewno,
                # że tekst naprawdę jest publiczny.
                import stages
                # ADRES BIERZEMY OD SUBSTACKA, nie zgadujemy z tytulu. Slug bywa
                # skracany: „the-hole-in-your-airplane-window-is-doing-exactly-
                # what-it-should" stalo sie „the-hole-in-your-airplane-window".
                # Zgadniety adres odpowiadal 302, wiec link zyl na przekierowaniu,
                # ktorego nikt nam nie obiecal.
                adres = potwierdz_adres_artykulu(page, artykul["tytul"])
                # I CZYSTY TEKST, nie HTML. Do promptu notki szlo 9000 znakow
                # znacznikow, z ktorych model musial wylowic tresc.
                stages.zapisz_do_promocji(adres, artykul["tytul"],
                                          bez_znacznikow(artykul.get("html", ""))[:2000])
        elif not wyslij:
            print("  (nie wysyłam — tryb sprawdzenia; szkic zapisany)", flush=True)
    except Exception as exc:
        wynik["blad"] = f"{type(exc).__name__}: {exc}"[:200]
        print(f"  BŁĄD: {wynik['blad']}", flush=True)
    finally:
        page.close()
        browser.close()
        p.stop()
    return wynik


def _watek_z_paginacja(page, nid, stron: int = 6) -> list[dict]:
    """Caly watek notki — ze WSZYSTKICH stron, nie tylko z pierwszej.

    ZMIERZONE 2 wrzesnia 2026 na 21 wpisach z powodem „Substack nie potwierdzil,
    ze wyszlo": SZESNASCIE tych tekstow WISIALO na Substacku, z autorem naszego
    konta i znacznikiem czasu 20-60 sekund PRZED wpisem o porazce. Czyli tresc
    wychodzila, a potwierdzanie jej nie znajdowalo.

    Dwa z nich — `note/c-246390011` i `note/c-252967738` — lezaly na DRUGIEJ
    stronie watku. `/replies` oddaje osiem galezi naraz i dokleja `nextCursor`,
    a kod czterokrotnie czytal TE SAMA pierwsza strone. Petla czekala 24 sekundy
    na cos, co lezalo jeden `cursor` dalej — i zadna liczba prob tam nie siega.

    Prog szesciu stron to okolo 48 galezi. Dluzsze watki i tak domyka
    `juz_sie_odezwalismy`, ktore pyta Substacka wprost.
    """
    from urllib.parse import quote

    wszystkie: list[dict] = []
    kursor = None
    for _ in range(stron):
        sciezka = f"/api/v1/reader/comment/{nid}/replies?comment_id={nid}"
        if kursor:
            sciezka += f"&cursor={quote(str(kursor), safe='')}"
        watek = api_json(page, sciezka) or {}
        for g in (watek.get("commentBranches") or []):
            wszystkie.extend(_plaskie(g))
        kursor = watek.get("nextCursor")
        if not kursor:
            break
    return wszystkie


def potwierdz_odpowiedz(page, note_id: int, tekst: str) -> int | None:
    """Pyta Substacka, czy nasza odpowiedź naprawdę jest w wątku — i KTORA.

    ODDAJE NUMER, NIE SAMO „TAK". Dokladnie jak `potwierdz_komentarz`, i to nie
    jest kosmetyka: bez numeru nie da sie polaczyc wypowiedzi z tym, co z niej
    wyszlo. Zmierzone na produkcji 1 wrzesnia 2026 — na 121 komentarzy w
    dzienniku 55 nie mialo pola `nasz_id`, w tym 43 UDANE. Przyczyna byla
    tutaj: ta funkcja pobierala caly watek z API, zamieniala go z powrotem na
    NAPIS przez `json.dumps` i sprawdzala, czy nasz tekst gdzies w nim jest.
    Identyfikator lezal w tej samej odpowiedzi, tyle ze przepuszczony przez
    `dumps` przestawal byc danymi i stawal sie literami.

    Skutek dla pomiaru: KAZDY host mial w rachunku najwyzej jeden dajacy sie
    polaczyc komentarz, wiec pytanie „gdzie nikt nam nigdy nie odpowiada" nie
    moglo dojrzec NIGDY, choc dane na nie fizycznie istnialy. Tedy szla przy
    tym wiekszosc pracy: `wystaw_odpowiedz` obsluguje komentarze pod cudzymi
    notkami, a tych jest wiecej niz komentarzy pod artykulami.

    Numer jest prawdziwy, wiec nadal dziala jak „tak"; brak to None.

    POTWIERDZENIE NIE ZALEZY OD NUMERU. Gdy nasza tresc JEST w watku, a numeru
    w odpowiedzi nie ma, oddajemy -1 — tak samo jak `potwierdz_komentarz`.
    Inaczej ta poprawka zamienialaby udana publikacje w „host nie pokazuje
    komentarza", a to jest zdanie, ktore w tym repozytorium kasuje hosta na
    zawsze (`hosty_gdzie_komentarz_nie_wchodzi`). Lepszy pomiar nie moze byc
    kupiony za falszywy dowod przeciw komus.
    """
    probka = plaski(tekst)[:60]
    for nr in range(4):
        for c in _watek_z_paginacja(page, note_id):
            if probka in plaski(c.get("body") or ""):
                return c.get("id") or -1
        if nr < 3:
            page.wait_for_timeout(8000)
    return None

def wystaw_odpowiedz(note_id: int, tekst: str, wyslij: bool = False,
                     kontekst: dict[str, Any] | None = None,
                     rodzaj: str = "odpowiedz") -> dict[str, Any]:
    """Odpowiada w watku — pod nasza notka albo w cudzej dyskusji.

    `kontekst` jak przy komentarzu: co wiedzielismy o celu, gdy pisalismy.

    `rodzaj` mowi, CZYM to dzialanie jest dla licznika wolumenow, bo jedna
    funkcja obsluguje dwie rozne rzeczy:

      - odpowiedz we WLASNYM watku, komus kto skomentowal nasza notke
        (`odpowiedz` — nie ma dziennej normy, bo zalezy od cudzych reakcji),
      - wejscie w dyskusje POD CUDZA notka (`komentarz` — ma norme, i jest to
        ta sama praca co komentarz pod cudzym artykulem).

    Zmierzone na dzienniku produkcji, siedem dni: 29 wpisow `odpowiedz`, z
    czego 23 to byly komentarze pod cudzymi notkami. Licznik pokazywal wiec
    30% realizacji normy komentarzy przy realnych 63%, bo wieksza czesc pracy
    ladowala w kategorii, ktora normy nie ma. Alarm o „agent robi mniej niz
    deklaruje" byl w tej czesci bledem pomiaru, nie bledem dzialania — a alarm,
    ktory regularnie klamie, uczy ludzi nie patrzec na alarmy.
    """
    wyslij = naprawde_wyslac(wyslij, rodzaj)
    wymagaj_sesji()
    p, browser, context = podlacz_sie()
    page = context.new_page()
    wynik: dict[str, Any] = {"wpisane": False, "wyslane": False, "blad": None}
    try:
        # `is not None`, bo funkcja oddaje teraz NUMER. Samo `if` byloby
        # falszywe dla numeru 0 — ktorego Substack nie uzywa, ale opieranie
        # poprawnosci na tym, ze cudzy serwis nie zacznie numerowac od zera,
        # jest zakladem bez potrzeby.
        if wyslij and potwierdz_odpowiedz(page, note_id, tekst) is not None:
            print("  ta odpowiedz juz jest w watku — nie wystawiam drugi raz",
                  flush=True)
            wynik["wyslane"] = True
            wynik["pominiete"] = True
            return wynik

        # Krotki adres dziala dla KAZDEJ notki, takze cudzej — sprawdzone.
        # Dzieki temu ta sama funkcja obsluguje odpowiedz u siebie i wejscie
        # w dyskusje u kogos obcego.
        page.goto(f"https://substack.com/note/c-{note_id}",
                  timeout=READ_TIMEOUT_MS, wait_until="domcontentloaded")
        page.wait_for_timeout(SETTLE_MS + 3000)

        # Pole odpowiedzi otwiera dopiero kliknięcie KONTENERA — kliknięcie w sam
        # napis nic nie robi. Napisy trzymamy w kilku językach, bo interfejs idzie
        # za językiem przeglądarki, a na serwerze będzie inny niż tutaj.
        # JEDNA NIEUDANA PROBA NIE MOZE ZABRAC POZOSTALYCH.
        #
        # Zlapane na produkcji 25 sierpnia: napis "Leave a reply" byl
        # znajdowany, ale klikniecie w jego rodzica wywalalo sie na timeoucie
        # 15 s — i wyjatek przerywal CALA petle, wiec kolejne napisy i kolejne
        # kandydatury nie mialy szansy. Dwie odpowiedzi przepadly tego dnia,
        # kazda po oplaceniu napisania tekstu.
        #
        # Trzy zmiany, kazda z powodu:
        #   - proba w `try`, zeby nieudany kandydat kosztowal tylko siebie,
        #   - `scroll_into_view`, bo pierwsze dopasowanie przy wielu komentarzach
        #     bywa poza ekranem, a element poza ekranem bywa nieklikalny,
        #   - klikamy TAKZE sam element, nie tylko rodzica: uklad Substacka
        #     zmienia sie i raz dziala jedno, raz drugie.
        otwarte = False
        for napis in ("Zostaw odpowiedź", "Leave a reply", "Reply", "Antwort"):
            if otwarte:
                break
            wszystkie = page.get_by_text(napis, exact=False)
            if wszystkie.count() == 0:
                continue
            for nr in range(min(3, wszystkie.count())):
                kand = wszystkie.nth(nr)
                for cel, opis in ((kand.locator("xpath=.."), "rodzic"),
                                  (kand, "sam napis")):
                    try:
                        cel.scroll_into_view_if_needed(timeout=5_000)
                        cel.click(timeout=8_000)
                    except Exception as exc:
                        print("    (%s/%d %s: %s)"
                              % (napis, nr, opis, type(exc).__name__), flush=True)
                        continue
                    page.wait_for_timeout(2500)
                    if page.locator("[contenteditable=true]").count() > 0:
                        otwarte = True
                        break
                if otwarte:
                    break
        if not otwarte:
            raise RuntimeError("nie otworzyłem pola odpowiedzi")

        page.locator("[contenteditable=true]").first.click(timeout=10_000)
        page.wait_for_timeout(700)
        page.keyboard.type(tekst, delay=12)
        page.wait_for_timeout(1500)
        wynik["wpisane"] = True
        print(f"  wpisane w pole odpowiedzi: {len(tekst.split())} słów", flush=True)

        przycisk = None
        for nazwa in ("Reply", "Odpowiedz", "Post", "Opublikuj", "Wyślij"):
            kandydat = page.get_by_role("button", name=nazwa).first
            if kandydat.count() > 0 and kandydat.is_visible():
                przycisk = kandydat
                print(f"  przycisk wysyłki: {nazwa!r}", flush=True)
                break
        wynik["przycisk_widoczny"] = przycisk is not None

        if wyslij and przycisk is not None:
            przycisk.click()
            wynik["klikniete"] = True     # jak w `wystaw_komentarz`
            page.wait_for_timeout(6000)
            odp = potwierdz_odpowiedz(page, note_id, tekst)
            # DRUGA POLOWA DOWODU — jak w `wystaw_komentarz`. `potwierdz_odpowiedz`
            # robi do czterech `api_json` i nie polyka wyjatkow, wiec bez tej
            # linii kazdy timeout po klknieciu wygladalby jak odmowa hosta.
            wynik["potwierdzenie_odpowiedzialo"] = True
            # `wyslane` ZOSTAJE LOGICZNE. `odp` jest teraz liczba, a wpisanie
            # liczby do pola, ktore w calym dzienniku jest prawda albo falszem,
            # zmienia ksztalt danych dla kazdego, kto je pozniej czyta.
            wynik["wyslane"] = odp is not None
            wynik["id"] = odp
            # -1 znaczy „jest w watku, ale numeru nie podano" i do dziennika
            # NIE IDZIE: pole `nasz_id` sluzy wylacznie do laczenia z pomiarem,
            # a -1 nie polaczy sie z niczym. Zapisane wygladaloby jak numer,
            # ktory zawiodl, zamiast jak numer, ktorego nie bylo.
            dopisz_wynik(rodzaj, wynik,
                               gdzie=f"note/c-{note_id}",
                               slow=len(tekst.split()), tekst=tekst[:1200],
                               nasz_id=(odp if (odp or 0) > 0 else None),
                               **(kontekst or {}))
            print("  ODPOWIEDŹ POTWIERDZONA W WĄTKU" if wynik["wyslane"]
                  else "  KLIKNIĘTE, ALE ODPOWIEDZI NIE MA W WĄTKU", flush=True)
        elif not wyslij:
            print("  (nie wysyłam — tryb sprawdzenia)", flush=True)
    except Exception as exc:
        wynik["blad"] = f"{type(exc).__name__}: {exc}"[:200]
        print(f"  BŁĄD: {wynik['blad']}", flush=True)
    finally:
        # TA SAMA DZIURA, CO W `wystaw_komentarz` — patrz komentarz przy jej
        # `finally`. Tutaj boli podwojnie, bo `raise RuntimeError("nie
        # otworzyłem pola odpowiedzi")` wyzej to NAJCZESTSZA awaria tej
        # funkcji (25 sierpnia dwie odpowiedzi przepadly na jednym timeoucie),
        # a wychodzila przez `except` i nie zostawiala nic.
        #
        # SPROSTOWANIE Z 1 WRZESNIA: poprzednia wersja tego komentarza mowila,
        # ze 7 nieudanych odpowiedzi na 47 prob (pomiar z 30 sierpnia) bylo
        # „wszystkie niewidoczne". Nieprawda — wlasnie z dziennika ten pomiar
        # pochodzi. Zapis stal bezwarunkowo w galezi wysylkowej, wiec klasa
        # „kliknelismy, odpowiedzi nie ma w watku" byla widoczna od poczatku.
        # Niewidoczne bylo to, co NIE DOSZLO do klikniecia: nieotwarte pole
        # odpowiedzi, brak przycisku wysylki i kazdy wyjatek.
        #
        # `rodzaj` bierzemy z argumentu, bo ta jedna funkcja robi dwie rzeczy
        # i licznik wolumenow musi dostac to samo slowo, co przy powodzeniu.
        #
        # `try` wokol zapisu — z tego samego powodu, co w `wystaw_komentarz`:
        # budowanie argumentow potrafi rzucic, a wtedy `page.close()`,
        # `browser.close()` i `p.stop()` ponizej nie wykonuja sie wcale.
        try:
            if wyslij and not wynik.get("pominiete"):
                dopisz_wynik(rodzaj, wynik, gdzie=f"note/c-{note_id}",
                             slow=len(tekst.split()), tekst=tekst[:1200],
                             **(kontekst or {}))
        except Exception as exc:
            print("  (nie zapisalem odpowiedzi do dziennika: %s)"
                  % type(exc).__name__, flush=True)
        page.close()
        browser.close()
        p.stop()
    return wynik


def wystaw_notke(tekst: str, wyslij: bool = False, typ: str = "",
                 forma: str = "", model: str = "") -> dict[str, Any]:
    """Wystawia notkę. Domyślnie WYPEŁNIA i NIE WYSYŁA.

    `wyslij=False` to nie ostrożność dla samej ostrożności: notki nie da się
    cofnąć w oczach tych, którzy ją zobaczyli. Najpierw sprawdzamy, czy kod
    trafia we właściwe pole, dopiero potem wysyłamy.
    """
    wyslij = naprawde_wyslac(wyslij, "notka")
    wymagaj_sesji()
    p, browser, context = podlacz_sie()
    page = context.new_page()
    wynik: dict[str, Any] = {"wpisane": False, "wyslane": False, "blad": None}
    try:
        # Czy tej notki juz nie wystawilismy? Pytamy RZECZYWISTOSCI, a nie
        # wlasnej ksiegowosci: proces przerwany po klknieciu, a przed zapisem,
        # zostawilby ksiegowosc niezgodna ze stanem faktycznym. Substack wie
        # lepiej niz my, co u nas wisi.
        if wyslij and potwierdz_notke(page, tekst):
            print("  ta notka juz jest na profilu — nie wystawiam drugi raz",
                  flush=True)
            wynik["wyslane"] = True
            wynik["pominiete"] = True
            return wynik

        page.goto("https://substack.com/home", timeout=READ_TIMEOUT_MS,
                  wait_until="domcontentloaded")
        page.wait_for_timeout(SETTLE_MS)

        # Kompozytor nie jest ani polem, ani przyciskiem w sensie roli ARIA —
        # trafia w niego dopiero kliknięcie. Szukamy go po STRUKTURZE, nie po
        # napisie: Substack podaje interfejs w języku przeglądarki, więc zaszyte
        # "What's on your mind?" przestało działać, gdy ten sam profil otworzył
        # się po polsku. Na serwerze locale będzie jeszcze inne.
        otwarty = False
        for sel in ("[class*=Composer]", "[class*=composer]"):
            kand = page.locator(sel).first
            if kand.count() > 0:
                kand.click(timeout=15_000)
                otwarty = True
                break
        if not otwarty:
            # Ostatnia deska: napisy, które znamy. Gdy i to padnie, lepiej rzucić
            # wyjątkiem niż wpisać notkę w przypadkowe pole.
            for napis in ("What's on your mind?", "O czym", "Was beschäftigt"):
                kand = page.get_by_text(napis, exact=False).first
                if kand.count() > 0:
                    kand.click(timeout=15_000)
                    otwarty = True
                    break
        if not otwarty:
            raise RuntimeError("nie znalazłem kompozytora notek")
        page.wait_for_timeout(2500)
        pole = page.locator("[contenteditable=true]").first
        pole.click(timeout=10_000)
        page.wait_for_timeout(800)
        page.keyboard.type(tekst, delay=12)
        page.wait_for_timeout(1500)
        wynik["wpisane"] = True
        print(f"  wpisane w pole notki: {len(tekst.split())} słów", flush=True)

        # Tu też nie zakładamy angielskiego interfejsu.
        przycisk = None
        for nazwa in ("Post", "Opublikuj", "Wyślij", "Publish", "Veröffentlichen"):
            kandydat = page.get_by_role("button", name=nazwa).first
            if kandydat.count() > 0 and kandydat.is_visible():
                przycisk = kandydat
                print(f"  przycisk wysyłki: {nazwa!r}", flush=True)
                break
        wynik["przycisk_widoczny"] = przycisk is not None
        print(f"  przycisk wysyłki widoczny: {wynik['przycisk_widoczny']}", flush=True)

        if wyslij and wynik["przycisk_widoczny"]:
            odpowiedzi = sluchaj_publikacji(page)
            przycisk.click()
            page.wait_for_timeout(6000)
            kody = [r.status for r in odpowiedzi]
            # Najpierw pytamy o odpowiedz Substacka na sam zapis — jest
            # natychmiastowa. Kanal profilu sprawdzamy tylko wtedy, gdy
            # odpowiedzi nie zlapalismy.
            if any(k == 200 for k in kody):
                wynik["wyslane"] = True
                print("  NOTKA PRZYJETA (odpowiedz Substacka: 200)", flush=True)
            else:
                wynik["wyslane"] = potwierdz_notke(page, tekst)
                print("  NOTKA POTWIERDZONA NA PROFILU" if wynik["wyslane"]
                      else f"  NIE WYSZLA (odpowiedzi: {kody or 'brak'})",
                      flush=True)
            wynik["id"] = id_z_odpowiedzi(odpowiedzi)
            if not wynik["id"] and wynik["wyslane"]:
                # Odpowiedz nie dala numeru — pytamy profil. Bez tego 23 z 29
                # notek nie mialo numeru i nie dalo sie im pobrac statystyk.
                wynik["id"] = numer_naszej_notki(page, tekst, prob=2)
            if wynik["wyslane"]:
                print("  id notki: %s" % (wynik["id"] or
                      "NIE ODCZYTANY — reakcji nie da sie z nia polaczyc"),
                      flush=True)
            dopisz_wynik("notka", wynik, slow=len(tekst.split()),
                         tekst=tekst[:1200], id=wynik["id"],
                         typ=typ, forma=forma, model=model)
        elif not wyslij:
            print("  (nie wysyłam — tryb sprawdzenia)", flush=True)
    except Exception as exc:
        wynik["blad"] = f"{type(exc).__name__}: {exc}"[:200]
        print(f"  BŁĄD: {wynik['blad']}", flush=True)
    finally:
        # DOMKNIECIE: jesli sciezka sukcesu nie zdazyla zapisac — bo wyjatek
        # albo bo nie bylo przycisku — porazka i tak trafia do dziennika.
        if wyslij:
            dopisz_wynik("notka", wynik, slow=len(tekst.split()),
                         tekst=tekst[:1200], id=wynik.get("id", ""),
                         typ=typ, forma=forma, model=model)
        page.close()
        browser.close()
        p.stop()
    return wynik


PLATNE_HOSTY = config.DATA_DIR / "platne_komentarze.json"


def zapamietaj_platny_host(host: str, prawo: str) -> None:
    """Host, ktory wprost mowi, ze komentowac moga tylko placacy."""
    import json as _json
    host = (host or "").lower().removeprefix("www.")
    if not host:
        return
    try:
        stan = (_json.loads(PLATNE_HOSTY.read_text(encoding="utf-8"))
                if PLATNE_HOSTY.exists() else {})
        if not isinstance(stan, dict):
            stan = {}
        if host in stan:
            return
        from datetime import datetime as _dt, timezone as _tz
        stan[host] = {"prawo": prawo,
                      "kiedy": _dt.now(_tz.utc).isoformat()}
        PLATNE_HOSTY.parent.mkdir(parents=True, exist_ok=True)
        PLATNE_HOSTY.write_text(_json.dumps(stan, ensure_ascii=False, indent=1),
                                encoding="utf-8")
        print("  [platne] zapamietane: %s (%s)" % (host, prawo), flush=True)
    except Exception as exc:
        # Pamiec jest premia, nie warunkiem. Jej awaria nie moze zatrzymac
        # przebiegu — najwyzej zapytamy tego hosta jeszcze raz.
        print("  [platne] nie zapisalem %s (%s)" % (host, type(exc).__name__),
              flush=True)


def hosty_tylko_dla_placacych() -> set[str]:
    """Hosty, gdzie komentowac moga tylko placacy — do odsiania PRZED ocena.

    Czyta plik z dysku, nie rusza sieci. Uzywane w `run.py`, zeby model nie
    placil za ocene celow, pod ktorymi i tak nie wolno nam napisac ani slowa.
    """
    import json as _json
    try:
        stan = _json.loads(PLATNE_HOSTY.read_text(encoding="utf-8"))
        return {str(h).lower() for h in stan} if isinstance(stan, dict) else set()
    except Exception:
        return set()


def zapomnij_platny_host(host: str) -> None:
    """Udany komentarz kasuje host z listy — wydawca mogl zmienic ustawienia."""
    import json as _json
    host = (host or "").lower().removeprefix("www.")
    try:
        stan = _json.loads(PLATNE_HOSTY.read_text(encoding="utf-8"))
        if isinstance(stan, dict) and stan.pop(host, None) is not None:
            PLATNE_HOSTY.write_text(_json.dumps(stan, ensure_ascii=False, indent=1),
                                    encoding="utf-8")
            print("  [platne] %s znowu przyjmuje komentarze — zdjety z listy"
                  % host, flush=True)
    except Exception:
        pass


# OKNO PAMIECI O MARTWYCH HOSTACH — I JEDYNA DROGA ZEJSCIA Z TEJ LISTY.
#
# Ta lista jest TWARDA BRAMKA: `mozna_komentowac` odmawia przed proba, a
# `run.dzien` odsiewa cel jeszcze przed ocena, wiec host raz na niej zamkniety
# nie ma jak zdobyc UDANEGO komentarza, ktory by go zdjal. Bez okna czasowego
# petla domyka sie na zawsze — a dziennik nie jest nigdzie przycinany ani
# rotowany, wiec wpis sprzed roku blokowalby host dzisiaj.
#
# OKNO JEST WIEC WYJSCIEM AWARYJNYM, nie ozdoba. Po zamknieciu hosta
# przestajemy do niego chodzic, wiec nowe wpisy nie powstaja — a gdy dwa stare
# wypadna z okna, licznik spada ponizej progu i host wraca do puli sam.
# Kosztuje to jedna probe raz na 14 dni.
#
# CZTERNASCIE DNI, i te liczbe wybralem tak:
#   - musi byc DLUZSZE niz `config.ODSTEP_DNI_NA_PUBLIKACJE` = 4 dni, bo tyle
#     `kanal.zapamietaj_komentarz` i tak trzyma nas z dala od publikacji,
#     u ktorej juz bylismy. Okno krotsze niz 4 dni wygasaloby, zanim host
#     w ogole wroci do rozwazenia — czyli pamiec nie oszczedzalaby ani jednej
#     proby i cala funkcja bylaby dekoracja;
#   - jest ROWNE `OSTRZEGAJ_PONIZEJ_DNI` = 14 z gory tego pliku, jedynej innej
#     stalej dniowej w `browser.py` — nie mnoze konwencji;
#   - przy zmierzonym tempie 92 prob komentarza na 7 dni (30 sierpnia 2026),
#     czyli ~13 dziennie, w oknie miesci sie okolo 180 prob. Prog dwoch
#     nieudanych odnosi sie wiec do gestej, biezacej probki, a nie do sumy
#     „od poczatku dziejow";
#   - a cena pomylki w druga strone jest mala: host, ktory naprawde nie
#     przyjmuje komentarzy, wraca na liste po dwoch kolejnych probach.
PAMIEC_MARTWYCH_HOSTOW_DNI = 14


def hosty_gdzie_komentarz_nie_wchodzi(min_prob: int = 2,
                                      dni: int = PAMIEC_MARTWYCH_HOSTOW_DNI) -> set[str]:
    """Hosty, gdzie w ostatnich `dni` dniach probowalismy >=2 razy i ANI RAZ
    komentarz nie wszedl.

    TA SAMA WADA, CO PRZY ZRODLACH, w innym miejscu. `hosty_ktore_nigdy_nie_
    dzialaly` powstalo, bo porazki pobierania byly zapisywane od poczatku i
    nigdy nie wracaly do dyskoverii — `fda.gov` przepadl 3 razy na 3, a slot
    i tak byl na niego wydawany. Dziennik zapisuje nieudane komentarze razem z
    adresem od poczatku i nikt ich nie czytal.

    ZMIERZONE 30 sierpnia 2026: 11 nieudanych komentarzy z 92 prob (12 procent)
    i 7 odpowiedzi z 47. Sprawdzone u zrodla — 0 z 6 sprawdzalnych bylo jednak
    opublikowanych, wiec to prawdziwa strata, a nie blad rozpoznania. Kosztowalo
    0,61 USD, czyli 92 procent calego przepalenia. Adresy powtarzaly sie:
    publikacja-c.example, publikacja-d.example, wlasnadomena.example — publikacje, ktore
    CZYTAC pozwalaja wszystkim, a KOMENTOWAC nie.

    PROG DWOCH PROB, nie jednej — tak samo jak przy zrodlach: jedno niepowodzenie
    to awaria po drugiej stronie, dwa z rzedu to wlasciwosc hosta. Jedno UDANE
    wystawienie kasuje host z listy, wiec zmiana ustawien u wydawcy odblokowuje
    go sama, bez naszej ingerencji.

    LICZA SIE TYLKO PORAZKI, KTORE MOWIA O HOSCIE (`o_hoscie` — patrz
    `dopisz_wynik`). Od 1 wrzesnia porazki trafiaja do dziennika z KAZDEJ
    galezi `wystaw_komentarz`, wiec sam nieudany wpis z adresem przestal byc
    dowodem czegokolwiek: timeout, padnieta sesja i zamkniety Chrome zapisuja
    sie tak samo jak odmowa Substacka. Odtworzone na atrapie: dwa wpisy
    `TimeoutError`/`TargetClosedError`, dwa rozne posty, jeden host — i
    `publikacja-c.example` uznany za martwy, choc nie powiedzial nam ani slowa.

    SAMO KLKNIECIE TO ZA MALO — poprawione po tym, jak pierwsza wersja tego
    rozroznienia oparla `o_hoscie` wylacznie na fladze `klikniete`. Flaga
    zapala sie TUZ PO nacisnieciu przycisku, a potwierdzanie zaczyna sie
    dopiero potem i robi do czterech nawigacji, ktore moga sie wywalic. Wpis
    liczy sie do listy dopiero, gdy Substack ODPOWIEDZIAL „nie ma tego" —
    dwa fakty, nie jeden. Patrz `dopisz_wynik`.

    I TO SAMO PYTANIE ZADAJEMY WPISOM, KTORE JUZ LEZA NA DYSKU. Przez jeden
    dzien kod zapisywal `o_hoscie=True` takze wtedy, gdy porazka byla wyjatkiem
    po naszej stronie — a taki wpis niesie w `powod` nazwe wyjatku, wiec sam
    sobie przeczy. Nie liczymy go. Dla wpisow powstajacych dzis to nic nie
    zmienia (przy `o_hoscie=True` powod z definicji brzmi
    POWOD_HOST_NIE_POKAZUJE), a tamte inaczej blokowalyby zdrowy host przez
    cale okno: sito w `run.py` wycina go z puli PRZED ocena, wiec udany
    komentarz — jedyna droga wyjscia — jest poza zasiegiem.

    STARE WPISY, BEZ POLA `o_hoscie`, NIE LICZA SIE WCALE. To jest wybor, nie
    przeoczenie. Kuszace bylo uznac je za dowod na hosta — bo przed 1 wrzesnia
    zapis stal wylacznie w galezi „kliknelismy i nie potwierdzilo", czyli
    dokladnie w tej jednej klasie. Ale poprawka lezala w drzewie roboczym
    zanim ktokolwiek ja przejrzal, wiec czesc wpisow bez tego pola moze juz
    pochodzic z niej i byc zwyklym timeoutem. Z samego wpisu tych dwoch
    zrodel nie odroznimy. Uznanie ich za dowod odtworzyloby wade na danych,
    ktore juz leza na dysku; zignorowanie kosztuje najwyzej jedna dodatkowa
    probe na host, po ktorej powstaja juz wpisy nowego ksztaltu. Po
    PAMIEC_MARTWYCH_HOSTOW_DNI dniach pytanie znika samo.

    Podzial pracy z `mozna_komentowac` jest celowy: tam zostaje optymizm wobec
    hosta NIEZNANEGO („przy watpliwosci probuje"), tu jest pamiec o hoscie
    SPRAWDZONYM. Optymizm kosztuje wtedy jedna probe, a nie dziesiata.
    """
    import collections as _c
    import json as _json
    from datetime import datetime, timedelta, timezone
    from urllib.parse import urlparse

    granica = datetime.now(timezone.utc) - timedelta(days=dni)
    udane: _c.Counter = _c.Counter()
    nieudane: _c.Counter = _c.Counter()
    try:
        if not DZIENNIK.exists():
            return set()
        for linia in DZIENNIK.read_text(encoding="utf-8").splitlines():
            linia = linia.strip()
            if not linia:
                continue
            try:
                w = _json.loads(linia)
            except ValueError:
                continue
            if not isinstance(w, dict) or w.get("rodzaj") != "komentarz":
                continue
            # Wpis bez czytelnej daty pomijamy w calosci. Nie umiemy powiedziec,
            # czy jest z wczoraj czy sprzed roku, a to jest tu cala roznica.
            try:
                kiedy = datetime.fromisoformat(str(w.get("kiedy") or ""))
            except ValueError:
                continue
            if kiedy.tzinfo is None:
                kiedy = kiedy.replace(tzinfo=timezone.utc)
            if kiedy < granica:
                continue
            gdzie = str(w.get("gdzie") or "")
            # Notki nie maja hosta w tym sensie — komentuje pod nimi kazdy
            # i nie ma tam czego pamietac.
            if not gdzie.startswith("http"):
                continue
            host = urlparse(gdzie).netloc.lower()
            if not host:
                continue
            if w.get("udane"):
                udane[host] += 1
            # WPIS, KTORY SAM SOBIE PRZECZY, NIE JEST DOWODEM. `o_hoscie=True`
            # przy powodzie mowiacym „TimeoutError" albo „TargetClosedError"
            # nie da sie pogodzic z definicja tego pola — to sa wpisy z jednego
            # dnia, kiedy `o_hoscie` liczylo sie z samej flagi `klikniete`,
            # zapalanej PRZED potwierdzaniem. Kod juz takich nie produkuje, ale
            # te, ktore zdazyly powstac, leza na dysku przez cale okno 14 dni
            # i host nie ma jak sie z nich wybronic: sito w `run.py` wycina go
            # z puli, wiec `udane=True`, jedyna droga wyjscia, jest poza
            # zasiegiem. Tu kosztuje to jedna linie.
            elif w.get("o_hoscie") and w.get("powod") == POWOD_HOST_NIE_POKAZUJE:
                nieudane[host] += 1
    except OSError:
        return set()
    return {h for h, ile in nieudane.items()
            if ile >= min_prob and udane[h] == 0}


def mozna_komentowac(url: str) -> bool:
    """Czy pod tym tekstem wolno nam w ogóle napisać.

    Trzy komentarze dziennie przepadały u publikacji, które CZYTAC pozwalaja
    wszystkim, a KOMENTOWAC tylko placacym. Klikniecie nic nie robilo, a caly
    koszt byl juz poniesiony: pobranie strony, trzy warianty komentarza
    i sprawdzenie faktow. Gorzej — kazde takie podejscie zjadalo miejsce
    z dziennego limitu, wiec realnie wychodzily trzy komentarze mniej.

    Substack mowi o tym w polu `write_comment_permissions`, dostepnym ZANIM
    cokolwiek napiszemy. Wystarczylo zapytac.

    Przy watpliwosci odpowiadamy TAK. Blad w te strone kosztuje jedno nieudane
    klikniecie; blad w druga zamyka agentowi usta wszedzie tam, gdzie pole ma
    wartosc, ktorej nie znamy.
    """
    if "/note/c-" in url:
        return True                   # pod notkami komentuje kazdy
    from urllib.parse import urlparse

    # PAMIEC PRZED PYTANIEM. Host, u ktorego dwa razy nic nie weszlo, nie
    # zasluguje na trzecie pytanie do API ani na trzeci oplacony tekst — patrz
    # `hosty_gdzie_komentarz_nie_wchodzi`. To sprawdzenie jest darmowe: czyta
    # dziennik z dysku, nie rusza sieci.
    host = urlparse(url).netloc.lower()
    if host and host in hosty_gdzie_komentarz_nie_wchodzi():
        print("  %s: dwa razy nic tam nie weszlo — nie place za trzeci raz"
              % host, flush=True)
        return False

    wymagaj_sesji()
    p, browser, context = podlacz_sie()
    page = context.new_page()
    try:
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        post = api_json(page, f"/api/v1/posts/{slug}",
                        baza=f"https://{urlparse(url).netloc}")
        if not isinstance(post, dict):
            return True
        prawo = str(post.get("write_comment_permissions") or "").lower()
        if prawo in {"only_paid", "only_founding", "none", "no_one"}:
            print(f"  {host}: komentarze tylko dla placacych ({prawo}) —"
                  f" odpuszczam przed pisaniem", flush=True)
            # ZAPAMIETUJEMY, i to jest poprawka z 30 sierpnia.
            #
            # Dotad ta odmowa byla tylko DRUKOWANA. Publikacja platna wracala
            # wiec do puli przy kazdym przebiegu, model placil za jej ocene, a
            # potem uruchamialismy przegladarke, zeby uslyszec to samo. W logu
            # z siedmiu dni: CZTERDZIESCI DWA razy.
            #
            # JEDNA OBSERWACJA WYSTARCZY, inaczej niz przy nieudanych
            # komentarzach, gdzie prog wynosi dwie proby. Tam jedno
            # niepowodzenie moze byc awaria po drugiej stronie; tutaj API
            # oddaje USTAWIENIE publikacji, a nie wynik proby.
            #
            # Zapis jest ODWRACALNY: udane wystawienie komentarza kasuje host z
            # listy, wiec zmiana ustawien u wydawcy odblokowuje go sama.
            zapamietaj_platny_host(host, prawo)
            return False
        return True
    except Exception:
        return True                   # nie wiem, wiec probuje
    finally:
        page.close()
        browser.close()
        p.stop()


def uchwyt_publikacji(host: str) -> str | None:
    """Nazwa konta do obserwowania — z hosta albo, gdy trzeba, z API.

    `host.split(".")[0]` dziala wylacznie dla adresow w domenie Substacka. Przy
    wlasnej domenie (`www.publikacja-c.example`) dawalo **"www"** i agent probowal
    obserwowac konto o takiej nazwie: trzy z czterech subskrypcji dziennie szly
    w prozne, a dziennik pokazywal `komu='www'` trzy razy pod rzad.

    Publikacja na wlasnej domenie i tak ma konto w Substacku, a jego nazwa stoi
    w `publishedBylines` dowolnego jej posta. Gdy nie da sie ustalic, zwracamy
    None — lepiej nie obserwowac nikogo niz obserwowac nieistniejace konto.
    """
    host = (host or "").strip().lower().rstrip("/")
    if not host:
        return None
    if host.endswith(".substack.com"):
        return host.split(".")[0]

    wymagaj_sesji()
    p, browser, context = podlacz_sie()
    page = context.new_page()
    try:
        posty = api_json(page, "/api/v1/posts?limit=1", baza=f"https://{host}")
        lista = posty if isinstance(posty, list) else (posty or {}).get("posts") or []
        for post in lista:
            for bylina in (post or {}).get("publishedBylines") or []:
                uchwyt = (bylina or {}).get("handle")
                if uchwyt:
                    return str(uchwyt)
        return None
    except Exception:
        return None
    finally:
        page.close()
        browser.close()
        p.stop()


def juz_sie_odezwalismy(page, url: str) -> bool:
    """Czy JUZ napisalismy cokolwiek pod tym postem albo pod ta notka.

    Najostrzejszy sygnal automatu, jaki mozna dac: dwa wlasne komentarze pod
    jednym tekstem, w odstepie godzin, a miedzy nimi nikt sie nie odezwal.
    Czlowiek nie wraca dopisywac drugiego eseju pod cudzym postem, na ktory nikt
    nie odpowiedzial.

    Pytamy o to RZECZYWISTOSCI, a nie wlasnej ksiegowosci: zapis moze sie
    rozjechac, Substack wie na pewno.
    """
    from urllib.parse import urlparse

    profil = api_json(page, f"/api/v1/user/{PROFIL_HANDLE}/public_profile")
    moje_id = (profil or {}).get("id")
    if not moje_id:
        return True          # nie wiem, czyli nie ryzykuje

    if "/note/c-" in url:                    # notka
        nid = url.rstrip("/").rsplit("c-", 1)[-1]
        watek = api_json(page, f"/api/v1/reader/comment/{nid}/replies"
                               f"?comment_id={nid}") or {}
        wszystkie = [c for g in (watek.get("commentBranches") or [])
                     for c in _plaskie(g)]
    else:                                    # artykul cudzy
        czyja = f"https://{urlparse(url).netloc}"
        slug = url.rstrip("/").rsplit("/", 1)[-1]
        post = api_json(page, f"/api/v1/posts/{slug}", baza=czyja)
        if not isinstance(post, dict) or not post.get("id"):
            return False
        dane = api_json(page, f"/api/v1/post/{post['id']}/comments"
                              "?all_comments=true", baza=czyja)
        wszystkie = dane if isinstance(dane, list) else (dane or {}).get("comments") or []

    return any(isinstance(c, dict) and c.get("user_id") == moje_id
               for c in wszystkie)


def bez_znacznikow(html: str) -> str:
    """Sam tekst, bez HTML-a. Do promptu notki promujacej szlo 9000 znakow
    znacznikow, z ktorych model musial wylowic tresc."""
    import re as _re

    tekst = _re.sub(r"<[^>]+>", " ", html or "")
    tekst = tekst.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return _re.sub(r"\s+", " ", tekst).strip()


def potwierdz_adres_artykulu(page, tytul: str) -> str:
    """Prawdziwy adres opublikowanego artykulu — od Substacka, nie z tytulu.

    Adres byl skladany przez zamiane tytulu na slug, a Substack slugi SKRACA:
    „The Hole in Example Article Nine Is Doing Exactly What It Should" dostalo
    adres `/p/the-hole-in-your-airplane-window`. Zgadniety adres odpowiadal 302,
    wiec notka promujaca dzialala tylko dzieki przekierowaniu, ktorego Substack
    nam nie obiecal. Notka promujaca z martwym linkiem jest gorsza niz jej brak.

    Gdyby odczyt zawiodl, wracamy do zgadywania — lepszy link na przekierowaniu
    niz zaden.
    """
    import re as _re

    baza = f"https://{config.SUBSTACK_HANDLE}.substack.com"
    zapasowy = (f"{baza}/p/"
                + _re.sub(r"[^a-z0-9]+", "-", (tytul or "").lower()).strip("-"))
    try:
        dane = api_json(page, "/api/v1/posts?limit=5", baza=baza)
        lista = dane if isinstance(dane, list) else (dane or {}).get("posts") or []
        for post in lista:
            if (post or {}).get("title") == tytul:
                adres = post.get("canonical_url") or (
                    f"{baza}/p/{post.get('slug')}" if post.get("slug") else "")
                if adres:
                    print(f"  adres artykulu wg Substacka: {adres}", flush=True)
                    return adres
    except Exception as exc:
        print(f"  (nie odczytalem adresu: {type(exc).__name__})", flush=True)
    print(f"  adres zlozony z tytulu (zapasowo): {zapasowy}", flush=True)
    return zapasowy


def potwierdz_komentarz(page, url: str, tekst: str) -> int | None:
    """Pyta Substacka, czy komentarz naprawdę wisi — zamiast wierzyć kliknięciu.

    Oddaje NUMER naszego komentarza, nie samo „tak". Numer jest potrzebny, zeby
    pozniej dopisac do dziennika, co z tego komentarza wyszlo: kanal aktywnosci
    mowi o polubieniach i odpowiedziach wlasnie numerami. Bez tego wiemy tylko,
    ze cos napisalismy, a nie czy ktokolwiek to zauwazyl.

    Numer jest prawdziwy, wiec nadal dziala jak „tak"; brak to None.

    Gdy komentarz JEST, ale odpowiedz nie podaje numeru, oddajemy -1, nie None.
    Ta funkcja pilnuje takze, zeby nie napisac drugi raz pod tym samym tekstem,
    a None znaczyloby „nie ma" i agent dopisalby kolejny komentarz — czyli
    dokladnie ten podpis bota, ktorego unikamy.
    """
    from urllib.parse import urlparse

    probka = plaski(tekst)[:60]

    # NOTKA TO NIE ARTYKUL i nie ma jej pod adresem artykulow. Ostatni czlon
    # adresu notki wyglada jak slug (`c-315876268`), wiec pytanie szlo do
    # /api/v1/posts/c-315876268 i wracalo bledem HTTP. Skutek: komentarz pod
    # notka NIGDY nie zostawal potwierdzony, nawet gdy poszedl. `juz_sie_odezwalismy`
    # rozroznialo te dwa przypadki od poczatku — tutaj tego zabraklo.
    if "/note/c-" in url:
        nid = url.rstrip("/").rsplit("c-", 1)[-1]
        for nr in range(4):
            for c in _watek_z_paginacja(page, nid):
                if probka in plaski(c.get("body") or ""):
                    return c.get("id") or -1
            if nr < 3:
                page.wait_for_timeout(8000)
        return None

    slug = url.rstrip("/").rsplit("/", 1)[-1]
    czyja = f"https://{urlparse(url).netloc}"        # publikacja AUTORA posta
    post = api_json(page, f"/api/v1/posts/{slug}", baza=czyja)
    if not isinstance(post, dict) or not post.get("id"):
        return None
    # Kilka prob, bo lista komentarzy — jak kanal profilu — aktualizuje sie
    # z opoznieniem, a falszywe "nie ma" rozbraja ochrone przed dublowaniem.
    for nr in range(4):
        dane = api_json(page, f"/api/v1/post/{post['id']}/comments?all_comments=true",
                        baza=czyja)
        lista = dane if isinstance(dane, list) else (dane or {}).get("comments") or []
        # GALAZ ARTYKULU CZYTALA TYLKO WIERZCH. Poprawka apostrofu z 31 sierpnia
        # weszla wylacznie do galezi notek: tutaj zostalo surowe `" ".join(...)`,
        # ktore nie normalizuje cudzyslowow, i pominiete byly odpowiedzi
        # zagniezdzone — czyli caly komentarz w watku ponizej pierwszego poziomu.
        # Zmierzone 2 wrzesnia: pod jednym z tych adresow bylo 90 wypowiedzi
        # z 124, ktorych ten kod w ogole nie ogladal.
        for k in (c for w in lista if isinstance(w, dict) for c in _plaskie(w)):
            if probka in plaski(k.get("body") or ""):
                return k.get("id") or -1
        if nr < 3:
            page.wait_for_timeout(8000)
    return None

def wystaw_komentarz(url: str, tekst: str, wyslij: bool = False,
                     kontekst: dict[str, Any] | None = None) -> dict[str, Any]:
    """Wystawia komentarz pod cudzym postem. Domyślnie WYPEŁNIA i NIE WYSYŁA.

    `kontekst` to wszystko, co WIEMY O CELU w chwili pisania: skad go mamy, ile
    komentarzy juz tam bylo, jaka publicznosc, jak stary tekst. Dziennik zapisywal
    tylko, ze cos napisalismy — a po dwoch dniach jedyne pytanie, ktore ma
    znaczenie, brzmi: czy warto bylo. Bez tych liczb nie da sie na nie odpowiedziec,
    a kosztuja zero, bo mamy je juz w reku i dotad je wyrzucalismy.
    """
    wyslij = naprawde_wyslac(wyslij, "komentarz")
    wymagaj_sesji()
    p, browser, context = podlacz_sie()
    page = context.new_page()
    wynik: dict[str, Any] = {"wpisane": False, "wyslane": False, "blad": None}
    try:
        if wyslij and juz_sie_odezwalismy(page, url):
            print("  JUZ SIE TAM ODEZWALISMY — drugi komentarz pod tym samym"
                  " tekstem to podpis bota, odpuszczam", flush=True)
            wynik["wyslane"] = True
            wynik["pominiete"] = True
            return wynik

        if wyslij and potwierdz_komentarz(page, url, tekst):
            print("  ten komentarz juz tam wisi — nie wystawiam drugi raz",
                  flush=True)
            wynik["wyslane"] = True
            wynik["pominiete"] = True
            return wynik

        page.goto(url, timeout=READ_TIMEOUT_MS, wait_until="domcontentloaded")
        page.wait_for_timeout(SETTLE_MS + 2000)

        # Sekcja komentarzy doczytuje się dopiero po przewinięciu w dół.
        page.mouse.wheel(0, 20_000)
        page.wait_for_timeout(3500)

        # Pod postem pole komentarza to TEXTAREA, nie contenteditable jak przy
        # notkach — to dwa różne edytory i jeden selektor nie obsłuży obu.
        #
        # PIERWSZA W DOM TO NIE ZAWSZE TA WŁAŚCIWA. `locator("textarea").first`
        # brał pierwszą textarea w drzewie niezależnie od tego, czy jest
        # widoczna. Gdy pola komentarza nie było wcale — a zdarza się to na
        # postach, których API nie oddaje `write_comment_permissions`, więc
        # zapora przepuszcza je zgodnie z zasadą „przy wątpliwości próbuję" —
        # Playwright czekał pełne 15 sekund na aktywność elementu, którego nie
        # ma, i kończył wyjątkiem. Zdarzyło się to dwa razy pierwszego dnia na
        # produkcji: scalesignals i glowwithella.
        #
        # Bierzemy pierwszą WIDOCZNĄ, a brak pola mówimy wprost zamiast
        # wywracać się na czasie. Wyjątek i tak nie niósł żadnej informacji
        # poza nazwą lokatora.
        pole = None
        for i in range(page.locator("textarea").count()):
            kandydat = page.locator("textarea").nth(i)
            try:
                if kandydat.is_visible():
                    pole = kandydat
                    break
            except Exception:
                continue
        if pole is None:
            wynik["blad"] = "nie ma pola komentarza pod tym postem"
            print(f"  {wynik['blad']} — odpuszczam", flush=True)
            return wynik
        pole.click(timeout=8_000)
        page.wait_for_timeout(800)
        page.keyboard.type(tekst, delay=12)
        page.wait_for_timeout(1500)
        wynik["wpisane"] = True
        print(f"  wpisane w pole komentarza: {len(tekst.split())} słów", flush=True)

        # Interfejs bywa po polsku, więc szukamy obu wariantów nazwy.
        przycisk = None
        for nazwa in ("Post", "Opublikuj", "Wyślij", "Comment", "Skomentuj"):
            kandydat = page.get_by_role("button", name=nazwa).first
            if kandydat.count() > 0 and kandydat.is_visible():
                przycisk = kandydat
                print(f"  przycisk wysyłki: {nazwa!r}", flush=True)
                break
        wynik["przycisk_widoczny"] = przycisk is not None
        print(f"  przycisk wysyłki widoczny: {wynik['przycisk_widoczny']}", flush=True)

        if wyslij and wynik["przycisk_widoczny"]:
            przycisk.click()
            # OD TEJ LINII WSZYSTKO PO NASZEJ STRONIE JUZ SIE UDALO:
            # przegladarka, strona, pole, tekst, przycisk. To POLOWA dowodu
            # przeciw hostowi — druga polowa to odpowiedz z potwierdzania,
            # ustawiana trzy linie nizej. Patrz `dopisz_wynik`.
            wynik["klikniete"] = True
            page.wait_for_timeout(6000)
            # Kliknięcie przycisku nie jest dowodem, że komentarz został przyjęty,
            # a agent bez człowieka nie ma komu tego sprawdzić. Pytamy więc Substacka.
            # Strony nie da się do tego użyć: komentarze doklejają się po stronie
            # klienta i inner_text ich nie widzi — sprawdzenie po tekscie strony dało
            # fałszywy alarm przy pierwszym realnym komentarzu, który naprawdę wisiał.
            nasz_numer = potwierdz_komentarz(page, url, tekst)
            # SUBSTACK ODPOWIEDZIAL — „jest" albo „nie ma". Dopiero to czyni
            # z porazki dowod przeciw hostowi. Gdy `potwierdz_komentarz` rzuci
            # (do czterech `page.goto`, zadne nie polyka wyjatku), ta linia sie
            # nie wykona i porazka zostanie w dzienniku jako „nie wiem".
            wynik["potwierdzenie_odpowiedzialo"] = True
            wynik["wyslane"] = nasz_numer is not None
            wynik["id"] = nasz_numer
            dopisz_wynik("komentarz", wynik, gdzie=url,
                               slow=len(tekst.split()), tekst=tekst[:1200],
                               nasz_id=nasz_numer, **(kontekst or {}))
            print("  KOMENTARZ POTWIERDZONY U SUBSTACKA" if wynik["wyslane"]
                  else "  KLIKNIĘTE, ALE SUBSTACK GO NIE POKAZUJE", flush=True)
        elif not wyslij:
            print("  (nie wysyłam — tryb sprawdzenia)", flush=True)
    except Exception as exc:
        wynik["blad"] = f"{type(exc).__name__}: {exc}"[:200]
        print(f"  BŁĄD: {wynik['blad']}", flush=True)
    finally:
        # PORAZKA TEZ MUSI ZOSTAWIC SLAD. Zapis stal wylacznie w galezi
        # „wysylamy i przycisk byl", wiec TRZY konce tej funkcji nie trafialy
        # do dziennika w ogole: „nie ma pola komentarza pod tym postem"
        # (zdarzylo sie dwa razy pierwszego dnia na produkcji — scalesignals
        # i glowwithella), brak przycisku wysylki i kazdy wyjatek.
        #
        # CO BYLO WIDAC, A CO NIE — poprawione 1 wrzesnia, bo poprzednia wersja
        # tego komentarza mowila nieprawde. Zapis w galezi wysylkowej stal TRZY
        # LINIE po `potwierdz_komentarz` i BEZ warunku na powodzenie, wiec
        # klasa „kliknelismy, Substack nie pokazuje" byla w dzienniku od
        # poczatku — to wlasnie z niej pochodzi pomiar 11 nieudanych na 92
        # proby z 30 sierpnia, `pod_rzad_nieudanych("komentarz")` te porazki
        # widzial, a `hosty_gdzie_komentarz_nie_wchodzi` dostawalo dokladnie
        # ten jeden, najlepszy sygnal i nic poza nim.
        #
        # BRAKOWALO natomiast trzech wymienionych wyzej klas — i tylko ich.
        # Kosztowaly one: nieuwzgledniona porazka w serii (wycofanie po trzech
        # z rzedu ruszalo z opoznieniem), brak powodu w raporcie i cisze tam,
        # gdzie awaria interfejsu wygladala jak spokojny dzien. `wystaw_notke`
        # i `_klik_na_profilu` domykaly to w `finally` od dawna — tamta
        # poprawka nie objela komentarzy.
        #
        # POMINIETYCH NIE ZAPISUJEMY, i to jest swiadoma roznica wobec notki.
        # `juz_sie_odezwalismy` oddaje True takze wtedy, gdy nie odczytalo
        # naszego id („nie wiem, czyli nie ryzykuje"), wiec wpis „udany
        # komentarz" wymyslilby dzialanie, ktorego nie bylo — i zjadl slot
        # z dziennego licznika, ktory dla komentarzy jest jedynym, jaki mamy.
        # Z tego samego powodu `run.dzien` nie liczy pominiecia do normy dnia.
        #
        # ZAPIS NIE MOZE POWSTRZYMAC SPRZATANIA. Wolanie stoi w `finally`
        # PRZED `page.close()`, a buduje argumenty — `len(tekst.split())`,
        # rozpakowanie `kontekst` — wiec potrafi rzucic samo z siebie.
        # Zmierzone side-by-side na atrapie: przy `tekst`, ktory nie jest
        # napisem, wersja bez tej oslony rzucala `AttributeError`, a
        # `page.close()`, `browser.close()` i `p.stop()` NIE WYKONYWALY SIE
        # WCALE — czyli jedna zla wartosc zostawiala otwarta strone Chrome
        # i proces sterownika na caly przebieg. Dziennik, ktory wywala agenta,
        # bylby gorszy od jego braku (patrz `zapisz_w_dzienniku`).
        try:
            if wyslij and not wynik.get("pominiete"):
                dopisz_wynik("komentarz", wynik, gdzie=url,
                             slow=len(tekst.split()), tekst=tekst[:1200],
                             nasz_id=wynik.get("id"), **(kontekst or {}))
        except Exception as exc:
            print("  (nie zapisalem komentarza do dziennika: %s)"
                  % type(exc).__name__, flush=True)
        page.close()
        browser.close()
        p.stop()
    return wynik


if __name__ == "__main__":
    import sys

    POLECENIA = {
        "sesja": sprawdz_sesje,      # podlacz sie do Chrome'a wlasciciela
        "zaloguj": zaloguj,          # stara droga, zapetla CAPTCHE — nie uzywac
        "rozpoznanie": rozpoznanie,
        "serwer": sprawdz_serwer,    # jedyne pytanie: czy sesja zyje z tego adresu
    }

    polecenie = sys.argv[1] if len(sys.argv) > 1 else "sesja"
    if polecenie not in POLECENIA:
        raise SystemExit(
            "Nieznane polecenie %r.\nZnane: %s"
            % (polecenie, ", ".join(sorted(POLECENIA))))

    # BRAK PLAYWRIGHTA MA MOWIC, CO ZROBIC.
    #
    # `python agent-v2/browser.py sesja` to PIERWSZY krok z instrukcji zakladania
    # sesji — czyli pierwsze polecenie, jakie wpisuje nowy uzytkownik. Bez tego
    # bloku wital go goly `ModuleNotFoundError: No module named 'playwright'`
    # z dziesiecioma wierszami sladu stosu, w miejscu, gdzie najlatwiej odpasc.
    #
    # Sam `pip install` NIE WYSTARCZA: Playwright instaluje biblioteke, a nie
    # przegladarke. Dlatego drugie polecenie stoi tu razem z pierwszym.
    try:
        import playwright  # noqa: F401
    except ImportError:
        raise SystemExit(
            "Brak pakietu `playwright` — bez niego agent nie dotknie Substacka.\n"
            "\n"
            "  pip install -r requirements.txt\n"
            "  playwright install chromium\n"
            "\n"
            "Drugie polecenie jest OSOBNE i konieczne: pierwsze instaluje\n"
            "biblioteke, dopiero drugie sciaga przegladarke.\n"
            "\n"
            "UWAGA: do PUBLIKOWANIA to i tak nie wystarczy. Cloudflare rozpoznaje\n"
            "tryb bezglowy po odcisku przegladarki i notka po prostu nie powstaje;\n"
            "potrzebny jest prawdziwy Chrome z ekranem. Patrz docs/INSTALL.md krok 5."
        )

    POLECENIA[polecenie]()



def read_pages(urls: list[str]) -> list[dict[str, Any]]:
    """Otwiera strony w przeglądarce i zwraca ich widoczny tekst.

    Jedna instancja przeglądarki na całą listę — start Chromium to sekundy,
    a stron bywa kilkanaście.
    """
    from playwright.sync_api import sync_playwright

    out: list[dict[str, Any]] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=config.FETCH_USER_AGENT,
            viewport={"width": 1280, "height": 900},
        )
        page = context.new_page()
        for url in urls:
            entry: dict[str, Any] = {"url": url, "text": "", "title": "", "error": None}
            try:
                page.goto(url, timeout=READ_TIMEOUT_MS, wait_until="domcontentloaded")
                page.wait_for_timeout(SETTLE_MS)  # treść dorysowuje się po JS
                entry["title"] = page.title()
                entry["text"] = page.inner_text("body")
            except Exception as exc:
                entry["error"] = f"{type(exc).__name__}: {exc}"[:200]
            out.append(entry)
            print(
                f"  [przeglądarka] {'OK  ' if not entry['error'] else 'NIE '} "
                f"{len(entry['text']):>7} znaków  {url[:58]}"
                f"{'  ' + entry['error'] if entry['error'] else ''}",
                flush=True,
            )
        context.close()
        browser.close()
    return out


def restackuj_w_kanale(
    ile: int, decyzja, wyslij: bool = False,
) -> dict[str, Any]:
    """Podaje dalej cudze notki z wlasnym zdaniem.

    `decyzja` to funkcja (notka: dict) -> dict, ktora oddaje
    {"restack": bool, "sentence": str, "reason": str}. Decyzja siedzi POZA ta
    funkcja, bo tu jest tylko klikanie — a o tym, czy warto, decyduje etap
    `stages.ocen_restack`, ktory da sie przetestowac bez przegladarki.

    Sciezka ustalona na zywym Substacku, nie zgadnieta:
      przycisk `Restack` ma aria-haspopup="menu", wiec NIE restackuje od razu,
      tylko rozwija menu z pozycjami `Restack`, `Restack with a note`
      i `View restacks`. Bierzemy druga — samo podanie dalej bez zdania nic
      nie wnosi, a to zdanie jest calym sensem tej akcji.

    Odstepy sa dluzsze niz przy polubieniach (10-30 min), bo restack wymaga
    PRZECZYTANIA cudzej notki. Cztery restacki w dwie minuty to nie jest
    czytanie i widac to na profilu tak samo, jak widac bylo notki parami.
    """
    import random

    wyslij = naprawde_wyslac(wyslij, "restacki")
    wymagaj_sesji()
    p, browser, context = podlacz_sie()
    page = context.new_page()
    wynik: dict[str, Any] = {"znalezione": 0, "rozwazone": 0, "restackowane": 0,
                             "odmowy": [], "blad": None}
    try:
        page.goto("https://substack.com/", timeout=READ_TIMEOUT_MS * 2,
                  wait_until="domcontentloaded")
        page.wait_for_timeout(SETTLE_MS + 6000)

        przyciski = page.get_by_role("button", name="Restack")
        wynik["znalezione"] = przyciski.count()
        print(f"  notek w kanale do rozwazenia: {wynik['znalezione']}", flush=True)

        for i in range(min(ile * 4, przyciski.count())):
            if wynik["restackowane"] >= ile:
                break
            kandydat = przyciski.nth(i)
            try:
                if not kandydat.is_visible():
                    continue
                # Tresc notki bierzemy z KONTENERA wokol przycisku. Bez niej
                # decyzja bylaby losowaniem, a nie ocena.
                notka = _notka_przy_przycisku(kandydat)
                if not notka.get("tekst"):
                    continue
                wynik["rozwazone"] += 1
                ocena = decyzja(notka)
                if not ocena.get("restack"):
                    powod = str(ocena.get("reason", ""))[:90]
                    wynik["odmowy"].append(powod)
                    print(f"    pomijam: {powod}", flush=True)
                    continue

                zdanie = ocena["sentence"]
                print(f"    RESTACK u {notka.get('autor', '?')[:24]}: {zdanie[:90]}",
                      flush=True)
                if not wyslij:
                    wynik["restackowane"] += 1
                    continue

                # ODSTEP STOI PRZED KOLEJNYM RESTACKIEM, NIE PO POPRZEDNIM.
                # Wczesniej czekalo sie na koncu ciala petli, a warunek wyjscia
                # sprawdza sie dopiero na gorze nastepnego obrotu — wiec agent
                # po wykonaniu normy spal jeszcze 10-30 minut z otwarta
                # przegladarka i dopiero wtedy wychodzil. Przy limicie jednego
                # restacka na przebieg, czyli w typowym przypadku, kazda taka
                # przerwa byla pusta w calosci.
                #
                # Samo „przerwij po wykonaniu normy" NIE WYSTARCZALO i zlapal to
                # dopiero test: gdy w kanale bylo mniej notek niz wynosil budzet,
                # norma nie byla wykonana, wiec petla i tak zasypiala, a zaraz
                # potem konczyla sie z braku kandydatow. Odstep postawiony PRZED
                # dziala w obu przypadkach, bo czeka tylko ten, kto naprawde ma
                # zaraz kliknac.
                if wynik["restackowane"]:
                    page.wait_for_timeout(
                        int(random.uniform(*config.ODSTEPY["restack"]) * 1000))

                kandydat.scroll_into_view_if_needed(timeout=8000)
                kandydat.click(timeout=8000)
                page.wait_for_timeout(1500)
                page.get_by_role("menuitem", name="Restack with a note").click(
                    timeout=8000)
                page.wait_for_timeout(SETTLE_MS)
                pole = page.get_by_role("textbox").last
                pole.click(timeout=8000)
                pole.type(zdanie, delay=random.randint(18, 45))
                page.wait_for_timeout(1200)
                # Substack nazywa przycisk wyslania "Post" — szukamy go
                # WEWNATRZ okna, nie w calym kanale, zeby nie trafic w cudzy.
                page.get_by_role("button", name="Post").last.click(timeout=8000)
                page.wait_for_timeout(SETTLE_MS + 2000)
                wynik["restackowane"] += 1
                # Restack tworzy NOWA notke z wlasnym numerem. Bez niego
                # restack byl jedyna forma publikacji, ktorej nie dalo sie
                # zmierzyc — a to najcenniejszy sygnal, jaki mamy: w badaniu
                # 9 641 notek restack konwertowal dwunastokrotnie lepiej niz
                # polubienie.
                numer_restacka = ""
                try:
                    numer_restacka = numer_naszej_notki(page, zdanie, prob=2)
                except Exception:
                    pass
                # OTWARTE, SWIADOMIE NIETKNIETE: `udane=True` ponizej opiera sie
                # na samym lancuchu klikniec, a nie na potwierdzeniu. To jest ta
                # sama doktryna „klikniecie nie jest dowodem", ktora obowiazuje
                # przy komentarzu, notce, odpowiedzi i — od 31 sierpnia — przy
                # polubieniu. Restack zostaje jedynym dzialaniem, ktore jej nie
                # przestrzega, i wiem o tym.
                #
                # DLACZEGO NIE ZAMYKAM TEGO TERAZ. Jedyny sygnal, jaki mam pod
                # reka, to `numer_restacka` — i on juz jest w dzienniku, w polu
                # `id`. Pusty `id` znaczy tylko tyle, ze nie odnalazlem notki na
                # profilu przy `prob=2`, czyli w dwoch podejsciach z jedna
                # osmiosekundowa przerwa. Jak zawodny jest taki odczyt, wiadomo
                # z pomiaru poprzedniego mechanizmu: `id_z_odpowiedzi` trafil
                # numer 6 razy na 29 notek. Gdybym na tej podstawie postawil
                # `udane=False`, restacki masowo znikalyby z licznika, a licznik
                # z dziennika jest dla nich jedyny — Substack nie oddaje ich
                # zadnym endpointem. Falszywe „nie udalo sie" kosztuje tu cala
                # dzienna norme, falszywe „udalo sie" jeden slot (patrz
                # `potwierdz_polubienie`), wiec zgadywanie jest drozsze niz
                # opisane ryzyko.
                #
                # CO ZAMKNELOBY SPRAWE: policzyc na produkcji, w ilu wpisach
                # `restack` pole `id` jest niepuste. Jesli wychodzi blisko 100
                # procent, `id` nadaje sie na warunek i wtedy — dopiero wtedy —
                # `udane` powinno od niego zalezec. Nie zgaduje, jak Substack
                # nazywa stan przycisku po restacku, i nie ruszam tego bez tej
                # liczby.
                zapisz_w_dzienniku("restack", udane=True,
                                   komu=notka.get("autor", ""),
                                   slow=len(zdanie.split()),
                                   tekst=zdanie[:300], id=numer_restacka)
                print(f"    podane dalej {wynik['restackowane']}/{ile}", flush=True)
            except Exception as exc:
                # Tak samo jak przy polubieniach: porazka szla do logu i nigdzie
                # indziej. Restacki chodza na 33% normy — bez tego wpisu nie ma
                # jak stwierdzic, czy to brak kandydatow w kanale, czy zmieniony
                # interfejs Substacka.
                powod = f"{type(exc).__name__}: {exc}"[:140]
                print(f"    (pominiete: {type(exc).__name__}: {exc}"[:150] + ")",
                      flush=True)
                zapisz_w_dzienniku("restack", udane=False, powod=powod,
                                   komu=notka.get("autor", ""))
                try:
                    page.keyboard.press("Escape")
                    page.wait_for_timeout(600)
                except Exception:
                    pass
        if not wyslij:
            print(f"  (nie klikam — tryb sprawdzenia; podalbym dalej"
                  f" {wynik['restackowane']})", flush=True)
    except Exception as exc:
        wynik["blad"] = f"{type(exc).__name__}: {exc}"[:200]
        print(f"  BŁĄD: {wynik['blad']}", flush=True)
    finally:
        page.close()
        browser.close()
        p.stop()
    return wynik


def _notka_przy_przycisku(przycisk) -> dict[str, str]:
    """Tresc i autor notki, przy ktorej stoi ten przycisk.

    Wchodzimy w gore drzewa, dopoki kontener nie zrobi sie na tyle duzy, zeby
    obejmowac cala notke. Szukanie po klasach odpada: Substack generuje je
    losowo (`container-_91AK1`), wiec selektor po klasie padnie przy pierwszym
    wdrozeniu po ich stronie.
    """
    try:
        dane = przycisk.evaluate(
            """e => {
                let n = e;
                for (let i = 0; i < 8 && n.parentElement; i++) {
                    n = n.parentElement;
                    if (n.innerText && n.innerText.length > 120) break;
                }
                const t = (n.innerText || '').trim();
                const a = n.querySelector('a[href*="/@"], a[href*="substack.com/profile"]');
                return {tekst: t, autor: a ? (a.innerText || '').trim() : ''};
            }"""
        )
    except Exception:
        return {}
    tekst = str(dane.get("tekst") or "")
    # Obcinamy ogon interfejsu: nazwy przyciskow trafiaja do innerText.
    for smiec in ("\nLike\n", "\nComment\n", "\nRestack\n", "\nShare\n"):
        tekst = tekst.replace(smiec, "\n")
    return {"tekst": tekst.strip()[:1800], "autor": str(dane.get("autor") or "")[:80]}
