# -*- coding: utf-8 -*-
"""Blokada idzie do przegladarki, a pusty korpus nie zabija przebiegu.

ZLAPANE ZYWYM PRZEBIEGIEM 91, i to najcenniejsza porazka tego dnia.

Poprawka dyskoverii zadzialala: model przestal dopychac liste do dziesieciu
pozycji i oddal CZTERY, wszystkie pierwotne (historycznie 10 pozycji i 3,0
pierwotne przy dlugim szukaniu). I wlasnie dlatego przebieg padl — bo dokumenty
pierwotne prawnicze i akademickie siedza za zaporami:

    opencasebook.org   HTTP 403
    papers.ssrn.com    HTTP 403
    canlii.org         HTTP 403
    law.stanford.edu   PDF bez warstwy tekstowej
    !! nie pobrano ani jednej strony

Poprawiajac JAKOSC zrodel, pogorszylem SKUTECZNOSC pobierania. Dwie wady:

1. PONOWIENIE W PRZEGLADARCE OBEJMOWALO TYLKO „za malo tresci". Blokady nie
   dostawaly go wcale. Odlozylem te poprawke wczesniej, bo na 28 ARCHIWALNYCH
   blokadach przegladarka odzyskiwala 7% — ale tamte hosty byly z epoki
   przedmiotow, a te sa tym, po co research istnieje. Koszt jest bliski zeru:
   ta sama sesja przegladarki i tak sie odpala.

2. PUSTY KORPUS RZUCAL WYJATEK WEWNATRZ `fetch`. `run.py` ma tuz za tym
   wywolaniem druga runde dyskoverii, wlasnie na taki wypadek — ale sterowanie
   nigdy tam nie wracalo. Zabezpieczenie bylo NIEOSIAGALNE dokladnie wtedy, gdy
   bylo najbardziej potrzebne.

GRANICA ZOSTAJE: jesli strona MOWI, ze nie zyczy sobie automatu, przyjmujemy to
takze w przegladarce. Zwykla przegladarka, bez podmiany tozsamosci, bez
posrednikow, bez omijania captcha. 404 nie ponawiamy — tam naprawde nic nie ma.

BEZ PYTESTA, bez platnych wywolan i BEZ SIECI. Uruchamiac z korzenia repo.
"""
import pathlib
import sys

sys.path.insert(0, "agent-v2")
import config   # noqa: E402
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


def do_przegladarki(powod: str) -> bool:
    """Ten sam warunek, ktory decyduje w `fetch`."""
    return bool(powod and (powod.startswith("za mało treści")
                           or powod in stages._DO_PONOWIENIA
                           or powod.endswith("Error")))


print("=== 1. BLOKADY IDA DO PRZEGLADARKI ===")
for kod in ("HTTP 403", "HTTP 401", "HTTP 429", "HTTP 503"):
    sprawdz("%s ponawiamy" % kod, do_przegladarki(kod))
sprawdz("bledy sieci tez", do_przegladarki("ConnectError"))
sprawdz("pusta tresc nadal tak", do_przegladarki("za mało treści (0 znaków)"))

print()
print("=== 2. A CZEGO NIE PONAWIAMY ===")
sprawdz("404 nie — tam naprawde nic nie ma", not do_przegladarki("HTTP 404"))
sprawdz("odmowa wprost nie — szanujemy ja",
        not do_przegladarki("host odmówił automatowi"))
sprawdz("skan PDF nie — to nie kwestia klienta",
        not do_przegladarki("PDF bez warstwy tekstowej (skan?)"))
sprawdz("brak powodu nie", not do_przegladarki(""))

print()
print("=== 3. KONTRDOWOD: STARY WARUNEK PRZEPUSZCZAL SAMO 'za malo' ===")
# Gdyby sekcja 1 przechodzila takze na starym warunku, niczego by nie dowodzila.
def stary(powod: str) -> bool:
    return bool(powod and powod.startswith("za mało treści"))


sprawdz("stary warunek NIE ponawial 403", not stary("HTTP 403"))
sprawdz("ale ponawial pusta tresc", stary("za mało treści (0 znaków)"))
sprawdz("czyli trzy blokady przebiegu 91 przepadaly",
        not any(stary(k) for k in ("HTTP 403", "HTTP 403", "HTTP 403")))

print()
print("=== 4. ODMOWA JEST SPRAWDZANA TAKZE W PRZEGLADARCE ===")
zrodlo = pathlib.Path("agent-v2/stages.py").read_text(encoding="utf-8")
i = zrodlo.index("def _dobierz_przegladarka")
blok = zrodlo[i:i + 2500]
sprawdz("przegladarka tez patrzy na frazy odmowy",
        "REFUSAL_PHRASES" in blok)
sprawdz("i zapisuje to jako odmowe, nie jako sukces",
        "host odmówił automatowi" in blok)

print()
print("=== 5. PUSTY KORPUS NIE RZUCA WYJATKU ===")
zr_fetch = zrodlo[zrodlo.index("def fetch("):]
zr_fetch = zr_fetch[:zr_fetch.index("DISCOVERY_SYSTEM")]
sprawdz("fetch nie rzuca przy zerze stron",
        "raise ValueError(\"nie pobrano ani jednej strony" not in zr_fetch)
sprawdz("tylko mowi o tym glosno",
        "ZERO stron" in zr_fetch)

print()
print("=== 6. TO RUN.PY DECYDUJE, CO ZROBIC Z PUSTKA ===")
rp = pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8")
sprawdz("run.py konczy przebieg jawnie przy pustym korpusie",
        "if not corpus:" in rp)
sprawdz("i robi to PO drugiej rundzie, nie przed",
        rp.index("if za_chudo or bez_rekordow:") < rp.index("if not corpus:"))
sprawdz("konczy bez wyjatku, zapisanym powodem",
        'return _done(conn, run_id, "fetch")' in rp)

print()
print("=== 7. SPRAWDZONE NA ZYWO, NA TYCH SAMYCH ADRESACH ===")
# Nie atrapa: cztery adresy z przebiegu 91 przepuszczone przez POPRAWIONY
# `fetch` na serwerze 30 sierpnia. Wynik zapisany tutaj, zeby nie trzeba bylo
# wierzyc opisowi w commicie.
#
#   [pobranie] drugie podejscie w przegladarce: 3 stron     <- wczesniej ZERO
#   opencasebook.org   16 371 znakow   ODZYSKANE
#   papers.ssrn.com       263 znaki    strona-zapora
#   canlii.org              0 znakow
#   law.stanford.edu   pominiety — skan PDF, przegladarka nic nie zmieni
#   fetch PRZEZYL zero pobran, wyjatek nie poleciał
#
# 1 z 3 to ten sam rzad wielkosci, co pomiar na archiwum (7%) — i wystarcza,
# bo przebieg 91 zginal z ZEREM, a na tym samym materiale konczy sie teraz
# jednym prawdziwym dokumentem i zywym przebiegiem.
sprawdz("skan PDF nadal poza ponowieniem (przegladarka go nie naprawi)",
        not do_przegladarki("PDF bez warstwy tekstowej (skan?)"))
sprawdz("a trzy blokady 403 do niego trafiaja",
        all(do_przegladarki("HTTP 403") for _ in range(3)))

print()
print("=== 8. PROGI NIE ZMIENILY SIE PRZY OKAZJI ===")
sprawdz("nadal wymagamy zrodel do pisania",
        config.MIN_ZRODEL_DO_PISANIA >= 1, config.MIN_ZRODEL_DO_PISANIA)
sprawdz("i nadal minimum pierwotnych",
        config.MIN_PRIMARY_SOURCES >= 1, config.MIN_PRIMARY_SOURCES)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
