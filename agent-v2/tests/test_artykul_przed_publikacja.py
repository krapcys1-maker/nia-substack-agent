"""Artykul nie wychodzi w swiat bez sprawdzenia faktow.

CO SIE STALO. Na produkcje poszedl artykul oparty na przepisie, ktory —
wedlug tresci artykulu — obejmowal pewna postac tresci. Nastepnego dnia
notka promujaca TEN SAM artykul przeszla przez `stages.zweryfikuj()`
i ODPADLA: obowiazek dotyczyl innych postaci, a ta jedna zostala
z przepisu usunieta jeszcze przed jego wejsciem w zycie.

Notka za pol centa zlapala blad, ktorego artykul za 76 centow nie mial jak
zlapac, bo na jego sciezce tego sprawdzenia po prostu nie bylo.

DLACZEGO GO NIE BYLO. `gates.verdict` zwraca zawsze „SAVED" — decyzja
wlasciciela z 15 sierpnia: „artykul powstaje ZAWSZE, uwagi wracaja do
wlasciciela do przeczytania". Sluszna, dopoki artykul byl szkicem dla czlowieka.
Gdy publikacja stala sie automatyczna, „nic nie blokuje" zaczelo znaczyc „nic
nie sprawdza".

CZEGO PILNUJE TEN TEST. Ze miedzy wejsciem w galaz `--wyslij` a wywolaniem
`browser.wystaw_artykul` stoi `stages.zweryfikuj`, i ze przy niepowodzeniu
sciezka WRACA zamiast publikowac. Zapis artykulu ma zostac — blokujemy wyjscie
na zewnatrz, nie prace.

SEKCJA 5 ZOSTALA PRZEROBIONA 1 wrzesnia 2026. Sprawdzala zachowanie
`zweryfikuj` przez czytanie pierwszych 2000 znakow jego zrodla — czyli gasla
przy samym przesunieciu komentarza i nie odrozniala zlej odpowiedzi modelu od
pustego konta. Teraz uruchamia prawdziwa funkcje z podmienionym `llm.call`.
Pelny pomiar obu roznic siedzi w `test_pusty_budzet_nie_sprawdza.py`.
"""
import pathlib
import sys

sys.path.insert(0, "agent-v2")

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


def wycinek_publikacji(src: str) -> str:
    """Kod od wejscia w galaz `--wyslij` do wywolania `wystaw_artykul`.

    Patrzymy na sam ten odcinek, a nie na caly plik: `zweryfikuj` wystepuje w
    run.py takze przy notkach i komentarzach, wiec zwykle „czy slowo jest w
    pliku" przeszloby TAKZE przed poprawka i niczego by nie dowodzilo.
    """
    poczatek = src.find("if args.wyslij:")
    if poczatek < 0:
        return ""
    koniec = src.find("wystaw_artykul", poczatek)
    if koniec < 0:
        return ""
    return src[poczatek:koniec]


# Tak wygladala ta galaz PRZED poprawka. Wykrywacz ma ja odrzucic — bez tego
# nie wiadomo, czy test w ogole rozroznia wersje.
PRZED_POPRAWKA = '''
        if args.wyslij:
            import browser

            print("\\n-- publikacja --", flush=True)
            wynik = browser.wystaw_artykul(path, wyslij=True)
'''

RUN = pathlib.Path("agent-v2/run.py")
src = RUN.read_text(encoding="utf-8")

print("=== 1. WYKRYWACZ ROZROZNIA WERSJE (KONTRDOWOD) ===")
sprawdz("stara galaz NIE ma zweryfikuj przed publikacja",
        "zweryfikuj" not in wycinek_publikacji(PRZED_POPRAWKA),
        repr(wycinek_publikacji(PRZED_POPRAWKA))[:120])
sprawdz("i wykrywacz w ogole cos z niej wycina",
        "import browser" in wycinek_publikacji(PRZED_POPRAWKA))

print()
print("=== 2. BIEZACY KOD SPRAWDZA FAKTY PRZED WYJSCIEM W SWIAT ===")
wycinek = wycinek_publikacji(src)
sprawdz("galaz --wyslij zostala znaleziona", bool(wycinek))
sprawdz("stoi w niej wywolanie stages.zweryfikuj",
        "stages.zweryfikuj(" in wycinek, wycinek[-200:])
sprawdz("sprawdzany jest TEKST ARTYKULU, nie karta",
        'draft["body"]' in wycinek, wycinek[-200:])
sprawdz("decyzja czytana jest z safe_to_post",
        "safe_to_post" in wycinek, wycinek[-200:])

print()
print("=== 3. OBALONE ZDANIE WYPADA, ARTYKUL IDZIE ===")
# ZMIANA KONTRAKTU, 1 wrzesnia 2026. Stalo tu wymaganie, zeby miedzy
# sprawdzeniem a `wystaw_artykul` bylo WYJSCIE ze sciezki. To wyjscie konczylo
# sie zdaniem „do decyzji wlasciciela" — czyli czekaniem na czlowieka w
# systemie, ktorego celem jest ZERO zgod czlowieka.
#
# Tego samego dnia zatrzymalo gotowy artykul za JEDNO zdanie (stopke z data
# zrodel) przy audycie, ktory w tym samym zdaniu napisal, ze wszystkie
# twierdzenia merytoryczne sa potwierdzone. Decyzja wlasciciela: artykul
# zaplanowany ma wyjsc; obalone zdanie ma zostac wyciete, a nie zatrzymac
# caly tekst.
#
# Te asercje sa po TRESCI ZRODLA i to jest ich wada — zostaja tylko dlatego,
# ze pilnuja KSZTALTU petli, ktorej nie da sie uruchomic bez platnego
# `zweryfikuj`. Zachowanie mierza `test_artykul_nie_ginie_po_drodze.py` i
# smoke-test helperow w `stages`.
po_audycie = wycinek[wycinek.find("stages.zweryfikuj("):] if "stages.zweryfikuj(" in wycinek else ""
sprawdz("NIE MA juz wyjscia czekajacego na czlowieka",
        "do decyzji wlasciciela" not in po_audycie, po_audycie[:200])
sprawdz("nie ma juz zadnego `return` miedzy sprawdzeniem a publikacja",
        "return" not in po_audycie, po_audycie[:300])
# WYCINANIE ZDAN BYLO ZBUDOWANE I COFNIETE tego samego dnia: wyciete zdanie
# zostawia dziure w srodku akapitu, a to gorsze dla czytelnika niz jedno slabe
# zdanie. Ta asercja pilnuje, zeby nie wrocilo.
sprawdz("i tekst NIE JEST ciety",
        "usun_obalone" not in src, "wycinanie wrocilo")

print()
print("=== 4. SPRAWDZENIE NIE MOZE BYC CICHE ===")
# Skoro nic nie blokuje, log jest JEDYNYM sladem po tym, co model
# zakwestionowal. Bez niego sprawdzenie byloby wydatkiem bez odbiorcy.
sprawdz("zastrzezenia sa wypisywane",
        "ZASTRZEZENIA" in po_audycie, po_audycie[:300])
sprawdz("i wypisywane jest kazde zakwestionowane twierdzenie",
        "refuted" in po_audycie and "claims" in po_audycie, po_audycie[:300])
sprawdz("data zrodel wstawiana jest przez KOD, nie przez model",
        "wstaw_date_zrodel(" in src, "brak w calym pliku")

print()
print("=== 5. `zweryfikuj`: AWARIA PRZEPUSZCZA, PUSTY BUDZET NIE ===")
# Zepsuta weryfikacja to nie dowod falszu. Gdyby awaria blokowala, jedna
# padnieta sesja sieciowa kasowalaby artykul wart 76 centow.
#
# ALE „SPRAWDZILEM I NIE WIEM" TO NIE TO SAMO, CO „NIE SPRAWDZILEM". Przy
# `llm.BudgetExceeded` i `llm.PreflightFailed` weryfikacja sie NIE ODBYLA
# i odbyc sie nie moze — tam `safe_to_post: True` bylo zdaniem nieprawdziwym
# wpisanym do zapisu, ktory chwile pozniej uchodzi za pomiar.
#
# TA SEKCJA BYLA WCZESNIEJ CZYTANIEM ZRODLA (`'"safe_to_post": True' in cialo`
# na pierwszych 2000 znakach funkcji). Dwie wady naraz: przesuniecie komentarza
# o kilkanascie linii gasilo ja bez zmiany zachowania, a rozroznienia miedzy
# zla odpowiedzia a pustym kontem nie widziala w ogole. Teraz mierzymy przez
# URUCHOMIENIE, z prawdziwymi klasami wyjatkow z `llm`.
import contextlib   # noqa: E402
import io           # noqa: E402

import llm          # noqa: E402
import stages       # noqa: E402

TEKST = " ".join(["word"] * 200)


def _zweryfikuj_gdy(wyjatek):
    """Oddaje (wynik, wyjatek) prawdziwego `zweryfikuj` przy danej awarii."""
    def _rzuca(*a, **k):
        raise wyjatek
    stary = llm.call
    llm.call = _rzuca
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return stages.zweryfikuj(object(), 1, TEKST, "tytul"), None
    except BaseException as exc:      # noqa: BLE001 — mierzymy, co wylatuje
        return None, exc
    finally:
        llm.call = stary


wynik, wyjatek = _zweryfikuj_gdy(ValueError("Extra data: line 1 column 1866"))
sprawdz("zwykla awaria oddaje safe_to_post = True",
        wynik is not None and wynik.get("safe_to_post") is True,
        wynik if wynik else type(wyjatek).__name__)
sprawdz("i mowi wprost, ze puszcza na pierwszej siatce",
        wynik is not None and "pierwszej siatce" in str(wynik.get("verdict", "")),
        wynik)

_, wyjatek = _zweryfikuj_gdy(llm.BudgetExceeded("limit dzienny wyczerpany"))
sprawdz("wyczerpany budzet NIE przepuszcza — leci na wylot",
        isinstance(wyjatek, llm.BudgetExceeded), type(wyjatek).__name__)

_, wyjatek = _zweryfikuj_gdy(llm.PreflightFailed("KILL_SWITCH=true"))
sprawdz("wylacznik tak samo — leci na wylot",
        isinstance(wyjatek, llm.PreflightFailed), type(wyjatek).__name__)

sprawdz("funkcja istnieje i jest wywolywalna", callable(stages.zweryfikuj))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
