"""Statystyki pozycji: czy parser czyta prawdziwa odpowiedz i czy raport nie klamie.

Probka nizej to ZMIERZONA odpowiedz `/api/v1/note_stats/c-321505067`, nie
wymyslony ksztalt: 17 wyswietlen, Feed 8, Other 5, Permalinks 3, Profile page 1,
odbiorcy Unconnected 8 / Subscribers 1 / Followers 0, interakcje 6 = Like 4 +
Reply 2. Test na wymyslonym JSON-ie dowodzilby tylko tego, ze parser zgadza sie
sam ze soba.

Trzy klasy bledow, ktore ten plik ma lapac — kazda jest cicha, zadna nie rzuca
wyjatkiem:

1. „Subscribers 1" z karty `audience` policzone jako subskrypcja z notki.
   To KTO WIDZIAL, nie kto sie zapisal. Raport chwalilby sie konwersja, ktorej
   nie bylo, i nikt by tego nie sprawdzil, bo liczba wygladalaby rozsadnie.

2. Nowy rodzaj interakcji wyrzucony po cichu przez parser. Substack dodaje
   rodzaje bez uprzedzenia; sygnal, ktorego nie widzimy, nie istnieje —
   dokladnie tak przez siedem dni „nie istnialy" nieudane obserwacje.

3. Podsumowanie liczone po POMIARACH zamiast po POZYCJACH. Notka mierzona
   dziesiec razy pokazalaby 170 wyswietlen zamiast 17. To jedyny blad z tej
   trojki, ktory daje liczbe wieksza od prawdy, wiec tez jedyny, ktory sam
   z siebie nikogo nie zaniepokoi.
"""
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import config       # noqa: E402
import statystyki   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# ZMIERZONA odpowiedz dla notki 321505067.
PROBKA = {
    "lastUpdatedAt": "2026-08-25T09:41:00.000Z",
    "cards": [
        {"cardId": "note", "type": "noteCard", "body": "tresc notki"},
        {"cardId": "impressions", "type": "statCard", "value": 17},
        {"cardId": "surfaces", "type": "listCard", "items": [
            {"title": "Feed", "value": 8, "percent": 47},
            {"title": "Other", "value": 5, "percent": 29},
            {"title": "Permalinks", "value": 3, "percent": 18},
            {"title": "Profile page", "value": 1, "percent": 6},
        ]},
        {"cardId": "audience", "type": "listCard", "items": [
            {"title": "Unconnected", "value": 8},
            {"title": "Subscribers", "value": 1},
            {"title": "Followers", "value": 0},
        ]},
        {"cardId": "interactions", "type": "listCard",
         "headers": [{"title": "Interactions", "value": 6}],
         "items": [
             {"title": "Like", "value": 4},
             {"title": "Reply", "value": 2},
         ]},
    ],
}

# KOMPLET KLUCZY REKORDU — kontrakt, nie wyliczanka. Raport, ktory raz dostaje
# slownik z polem, a raz bez, wywala sie na pierwszej pozycji, ktorej nikt nie
# polubil, czyli na najczestszym przypadku.
#
# `wystawione` doszlo 31 sierpnia 2026 i TEN TEST ZLAPAL BRAK AKTUALIZACJI —
# tak, jak mial. Pole niesie date WYSTAWIENIA pozycji, w odroznieniu od
# `zmierzone`, ktore mowi, kiedy PYTALISMY. Bez niego nie dalo sie rozdzielic
# statystyk epoki AI od wczesniejszych: pomiary sa zawsze swieze, takze te
# notek sprzed miesiaca, a laczenie z dziennikiem po numerze gubilo dziesiec
# notek na 37 (dziennik nie ma numerow tych starszych).
# `ma_karty_zasiegu` doszlo 31 sierpnia razem z licznikami z karty `note`.
# Zmierzone tego dnia: z 52 naszych komentarzy 37 dostaje z API JEDNA karte
# (`note`) zamiast pieciu — Substack nie liczy zasiegu wpisow, ktore nic nie
# zebraly. Bez tego pola raport nie odrozni „zero wejsc" od „nie ma karty".
KLUCZE = {"wyswietlenia", "powierzchnie", "odbiorcy", "interakcje",
          "interakcje_razem", "polubienia", "odpowiedzi", "restacki",
          "subskrypcje", "obserwacje", "klikniecia_w_link", "zmierzone",
          "wystawione", "ma_karty_zasiegu"}


def _w_pustym_katalogu(funkcja):
    """Uruchamia `funkcja()` z DATA_DIR przekierowanym na katalog tymczasowy."""
    with tempfile.TemporaryDirectory() as tmp:
        _zdjecie = config.uzyj_katalogu_danych(pathlib.Path(tmp))
        try:
            return funkcja(pathlib.Path(tmp))
        finally:
            config.przywroc_katalog_danych(_zdjecie)


def _z_liniami(linie, funkcja):
    """DATA_DIR z gotowym statystyki.jsonl o podanych liniach (napisy)."""
    def _wnetrze(katalog):
        (katalog / statystyki.NAZWA_PLIKU).write_text(
            "\n".join(linie) + "\n", encoding="utf-8")
        return funkcja()
    return _w_pustym_katalogu(_wnetrze)


def _linia(ident, kiedy, rodzaj="notka", **pola):
    return json.dumps({"id": ident, "kiedy": kiedy, "rodzaj": rodzaj,
                       "tekst": "notka %s" % ident, **pola})


print("=== 1. PRAWDZIWA ODPOWIEDZ API PARSUJE SIE NA LICZBY Z POMIARU ===")
r = statystyki.z_kart(PROBKA)
sprawdz("komplet kluczy, zawsze ten sam", set(r) == KLUCZE,
        sorted(set(r) ^ KLUCZE))
sprawdz("wyswietlenia = 17", r["wyswietlenia"] == 17, r["wyswietlenia"])
sprawdz("powierzchnie: Feed 8", r["powierzchnie"].get("Feed") == 8, r["powierzchnie"])
sprawdz("powierzchnia z dwoch slow tez ma nazwe",
        r["powierzchnie"].get("Profile page") == 1, r["powierzchnie"])
# Kontrola spojnosci samej probki: powierzchnie musza sie sumowac do wyswietlen.
# Gdyby parser gubil pozycje listy, ta suma spadlaby ponizej 17.
sprawdz("suma powierzchni = wyswietlenia", sum(r["powierzchnie"].values()) == 17,
        sum(r["powierzchnie"].values()))
sprawdz("polubienia = 4", r["polubienia"] == 4, r["polubienia"])
sprawdz("odpowiedzi = 2", r["odpowiedzi"] == 2, r["odpowiedzi"])
sprawdz("suma interakcji z naglowka = 6", r["interakcje_razem"] == 6,
        r["interakcje_razem"])
sprawdz("pozycje interakcji sumuja sie do naglowka",
        sum(r["interakcje"].values()) == r["interakcje_razem"], r["interakcje"])
sprawdz("`zmierzone` bierze sie z lastUpdatedAt",
        r["zmierzone"] == PROBKA["lastUpdatedAt"], r["zmierzone"])

# NAJWAZNIEJSZY KONTRDOWOD TEGO PLIKU. Karta `audience` mowi „Subscribers 1",
# czyli „widzial to jeden subskrybent". Notka nie przyniosla ANI JEDNEJ
# subskrypcji — interakcje to 4 polubienia i 2 odpowiedzi, koniec. Parser,
# ktory czyta konwersje z `audience`, pokazalby tu 1 i nikt by nie zaprotestowal.
sprawdz("odbiorcy sa zapisani osobno", r["odbiorcy"].get("Subscribers") == 1,
        r["odbiorcy"])
sprawdz("ale NIE sa liczeni jako subskrypcje z notki", r["subskrypcje"] == 0,
        r["subskrypcje"])
sprawdz("ani Followers jako obserwacje", r["obserwacje"] == 0, r["obserwacje"])

# KONTRDOWOD: parser nie zwraca stalych. Te same karty z innymi liczbami
# musza dac inne liczby.
inna = json.loads(json.dumps(PROBKA))
inna["cards"][1]["value"] = 260
inna["cards"][4]["headers"][0]["value"] = 11
inna["cards"][4]["items"] = [{"title": "Like", "value": 9},
                             {"title": "Reply", "value": 2}]
r2 = statystyki.z_kart(inna)
sprawdz("inne liczby daja inny rekord",
        (r2["wyswietlenia"], r2["polubienia"], r2["interakcje_razem"]) == (260, 9, 11),
        (r2["wyswietlenia"], r2["polubienia"], r2["interakcje_razem"]))

# Liczba zbiorcza czytana tez z naglowka, gdy karta nie ma pola `value`.
sprawdz("wyswietlenia da sie odczytac takze z naglowka karty",
        statystyki.z_kart({"cards": [{"cardId": "impressions",
                                      "headers": [{"value": 17}]}]})["wyswietlenia"] == 17)
# Substack formatuje wieksze liczby przecinkiem — "1,204" to nie napis do
# wyrzucenia, tylko liczba, ktora bedzie wygladac inaczej dopiero przy artykule.
sprawdz("liczba z przecinkiem czyta sie jako liczba",
        statystyki.z_kart({"cards": [{"cardId": "impressions",
                                      "value": "1,204"}]})["wyswietlenia"] == 1204)

print()
print("=== 2. NIEZNANY RODZAJ INTERAKCJI SIE NIE GUBI ===")
# Opis endpointu wymienia osiem rodzajow, my widzielismy dwa. „Sparkle" nie
# istnieje — jest w probce po to, zeby udowodnic, ze parser nie ma bialej listy.
nowe = {"lastUpdatedAt": "2026-08-25T10:00:00.000Z", "cards": [
    {"cardId": "impressions", "value": 90},
    {"cardId": "interactions", "type": "listCard",
     "headers": [{"value": 21}],
     "items": [
         {"title": "Like", "value": 4},
         {"title": "Restack", "value": 1},
         {"title": "Subscribe", "value": 3},
         {"title": "Follow", "value": 2},
         {"title": "Save", "value": 3},
         {"title": "Link click", "value": 6},
         {"title": "Sparkle", "value": 2},
     ]},
]}
r = statystyki.z_kart(nowe)
sprawdz("Subscribe -> subskrypcje", r["subskrypcje"] == 3, r["subskrypcje"])
sprawdz("Follow -> obserwacje", r["obserwacje"] == 2, r["obserwacje"])
sprawdz("Restack -> restacki", r["restacki"] == 1, r["restacki"])
sprawdz("Link click -> klikniecia_w_link", r["klikniecia_w_link"] == 6,
        r["klikniecia_w_link"])
# KONTRDOWODY na brak bialej listy: rodzaj bez wlasnego pola ma ZOSTAC w
# slowniku interakcji. Parser filtrujacy po znanych tytulach zgubilby oba
# i suma przestalaby sie zgadzac z naglowkiem Substacka.
sprawdz("znany, ale bez wlasnego pola: `Save` zostaje",
        r["interakcje"].get("Save") == 3, r["interakcje"])
sprawdz("calkiem nieznany `Sparkle` tez zostaje",
        r["interakcje"].get("Sparkle") == 2, r["interakcje"])
sprawdz("i nic nie wylatuje: suma pozycji = naglowek",
        sum(r["interakcje"].values()) == r["interakcje_razem"] == 21,
        (sum(r["interakcje"].values()), r["interakcje_razem"]))
# KONTRDOWOD odwrotny: nieznany rodzaj nie moze DOKLEIC sie do znanego pola.
sprawdz("nieznany rodzaj nie zasila polubien", r["polubienia"] == 4, r["polubienia"])
sprawdz("ani odpowiedzi", r["odpowiedzi"] == 0, r["odpowiedzi"])
# Wielkosc liter nalezy do Substacka, nie do nas.
sprawdz("mapowanie nie zalezy od wielkosci liter i liczby mnogiej",
        statystyki.z_kart({"cards": [{"cardId": "interactions", "items": [
            {"title": "subscribes", "value": 5}]}]})["subskrypcje"] == 5)

print()
print("=== 3. BRAKI I SMIECI NIE WYWALAJA PARSERA ===")
# Endpoint odpowiada takze na notki bez ani jednego wyswietlenia, a wtedy
# kart po prostu nie ma. Wyjatek w parserze statystyk zabralby caly przebieg
# agenta dla dodatku, ktory nic nie publikuje.
kalekie = [
    ("pusty slownik", {}),
    ("cards = None", {"cards": None}),
    ("cards = []", {"cards": []}),
    ("cale dane None", None),
    ("cards nie jest lista", {"cards": {"a": 1}}),
    ("karta bez cardId", {"cards": [{"items": [{"title": "Like", "value": 4}]}]}),
    ("karta nie jest slownikiem", {"cards": ["note", 7, None]}),
    ("pusta lista items", {"cards": [{"cardId": "interactions", "items": []}]}),
    ("items nie jest lista", {"cards": [{"cardId": "surfaces", "items": "Feed"}]}),
    ("value = None", {"cards": [{"cardId": "impressions", "value": None},
                                {"cardId": "interactions", "items": [
                                    {"title": "Like", "value": None}]}]}),
    ("pozycja bez tytulu", {"cards": [{"cardId": "interactions",
                                       "items": [{"value": 4}]}]}),
    ("tytul nie jest napisem", {"cards": [{"cardId": "interactions",
                                           "items": [{"title": 7, "value": 4}]}]}),
    ("value jest napisem-smieciem", {"cards": [{"cardId": "impressions",
                                                "value": "brak danych"}]}),
]
for nazwa, dane in kalekie:
    try:
        w = statystyki.z_kart(dane)
        ok = set(w) == KLUCZE and w["wyswietlenia"] == 0 and w["polubienia"] == 0
        sprawdz("  %s -> rekord zerowy, nie wyjatek" % nazwa, ok, w)
    except Exception as e:
        sprawdz("  %s -> rekord zerowy, nie wyjatek" % nazwa, False,
                "%s: %s" % (type(e).__name__, e))
# KONTRDOWOD: odpornosc nie moze polegac na tym, ze parser zawsze zwraca zera.
sprawdz("a pelna probka nadal daje 17", statystyki.z_kart(PROBKA)["wyswietlenia"] == 17)
sprawdz("brak lastUpdatedAt daje pusty napis, nie None",
        statystyki.z_kart({})["zmierzone"] == "")

print()
print("=== 4. ZAPIS I ODCZYT HISTORII ===")


def _zapis_i_odczyt(_):
    statystyki.zapisz("notka", "321505067", statystyki.z_kart(PROBKA),
                      tekst="The jar stays open.")
    statystyki.zapisz("artykul", "p-160", {"wyswietlenia": 300, "subskrypcje": 4})
    return (statystyki.wczytaj(), statystyki.wczytaj("notka"),
            statystyki.wczytaj("artykul"))


wszystko, notki, artykuly = _w_pustym_katalogu(_zapis_i_odczyt)
sprawdz("dwa zapisy to dwie linie", len(wszystko) == 2, len(wszystko))
sprawdz("filtr rodzaju dziala", len(notki) == 1 and len(artykuly) == 1,
        (len(notki), len(artykuly)))
sprawdz("linia niesie identyfikator, rodzaj, czas i skrot tekstu",
        {"id", "rodzaj", "kiedy", "tekst"} <= set(notki[0]), sorted(notki[0]))
sprawdz("i cale liczby z parsera",
        notki[0]["wyswietlenia"] == 17 and notki[0]["polubienia"] == 4, notki[0])
sprawdz("skrot tekstu jest zapisany", notki[0]["tekst"] == "The jar stays open.",
        notki[0]["tekst"])

# Uszkodzona linia. SIGTERM w zwloce przed notkami uszkodzil w tym projekcie
# siedem przebiegow w tygodniu (`df3de64`) — proces ginacy w trakcie zapisu
# zostawia dokladnie taki ogon.
linie = [_linia("1", "2026-08-25T08:00:00+00:00", wyswietlenia=17),
         '{"id": "2", "kiedy": "2026-08-25T09:00:00+00:00", "rodz',
         _linia("3", "2026-08-25T10:00:00+00:00", wyswietlenia=40),
         ""]
odczyt = _z_liniami(linie, statystyki.wczytaj)
sprawdz("uszkodzona linia jest pomijana", len(odczyt) == 2, odczyt)
# KONTRDOWOD: odczyt nie moze sie na niej KONCZYC. Linia po uszkodzonej ma
# dojechac — inaczej jedna wpadka kasuje cala pozniejsza historie.
sprawdz("a linia PO uszkodzonej nadal sie czyta",
        [w["id"] for w in odczyt] == ["1", "3"], [w.get("id") for w in odczyt])
sprawdz("pusta linia tez nie przeszkadza", all(w.get("id") for w in odczyt))
# Sprawdzamy, ze probka faktycznie jest uszkodzona — inaczej powyzsze niczego
# nie dowodzi, bo pomijalibysmy linie poprawna.
try:
    json.loads(linie[1])
    _uszkodzona = False
except ValueError:
    _uszkodzona = True
sprawdz("druga linia naprawde nie jest JSON-em", _uszkodzona)

# Brak pliku to normalny pierwszy dzien, nie awaria.
sprawdz("brak pliku -> pusta lista",
        _w_pustym_katalogu(lambda _: statystyki.wczytaj()) == [])
sprawdz("brak pliku -> podsumowanie bez wyjatku",
        _w_pustym_katalogu(lambda _: statystyki.podsumowanie())["pozycje"] == 0)

# Zapis NIGDY nie moze przerwac agenta. Statystyki sa dodatkiem; przebieg
# publikujacy notki nie ma prawa zginac na tym, ze nie da sie zapisac pomiaru.
def _niemozliwa_sciezka(katalog):
    zajete = katalog / "to-jest-plik"
    zajete.write_text("x", encoding="utf-8")
    config.uzyj_katalogu_danych(zajete / "podkatalog",   # rodzic jest PLIKIEM
                                utworz=False)
    try:
        statystyki.zapisz("notka", "1", {"wyswietlenia": 17})
        return True
    except Exception as e:
        return "%s: %s" % (type(e).__name__, e)


_wynik_zapisu = _w_pustym_katalogu(_niemozliwa_sciezka)
sprawdz("zapis w niemozliwe miejsce nie rzuca", _wynik_zapisu is True, _wynik_zapisu)


def _nieserializowalny(_):
    statystyki.zapisz("notka", "1", {"wyswietlenia": 17, "cos": object()})
    return statystyki.wczytaj()


w = _w_pustym_katalogu(_nieserializowalny)
# KONTRDOWOD: nie chodzi tylko o brak wyjatku. Bez `default=str` wyjatek
# wylecialby z `json.dumps`, zostalby zlapany i POMIAR PRZEPADLBY po cichu -
# a to jest gorsze niz blad, bo wyglada jak brak danych.
sprawdz("nieserializowalna wartosc nie kasuje calego pomiaru",
        len(w) == 1 and w[0]["wyswietlenia"] == 17, w)

print()
print("=== 5. NAJNOWSZY POMIAR WYGRYWA, NIE OSTATNIA LINIA ===")
# Ta sama notka zmierzona dwa razy: rano 17 wyswietlen, poludniem 40.
# W pliku NOWSZY LEZY PIERWSZY — tak wyglada plik, do ktorego dwa nakladajace
# sie przebiegi dopisaly pomiary w innej kolejnosci, niz je zrobily.
pary = [_linia("321505067", "2026-08-25T12:00:00+00:00", wyswietlenia=40, subskrypcje=1),
        _linia("321505067", "2026-08-25T09:00:00+00:00", wyswietlenia=17, subskrypcje=0)]
n = _z_liniami(pary, statystyki.najnowsze_per_pozycja)
sprawdz("jedna pozycja mimo dwoch pomiarow", len(n) == 1, sorted(n))
# KONTRDOWOD: implementacja „wygrywa ostatnia linia" da tu 17.
sprawdz("zwraca pomiar NOWSZY, nie ostatni w pliku",
        n["321505067"]["wyswietlenia"] == 40, n["321505067"]["wyswietlenia"])
n = _z_liniami(list(reversed(pary)), statystyki.najnowsze_per_pozycja)
sprawdz("kolejnosc w pliku nie zmienia wyniku",
        n["321505067"]["wyswietlenia"] == 40, n["321505067"]["wyswietlenia"])
sprawdz("filtr rodzaju dziala takze tutaj",
        _z_liniami(pary, lambda: statystyki.najnowsze_per_pozycja("artykul")) == {})

print()
print("=== 6. PODSUMOWANIE LICZY POZYCJE, A NIE POMIARY ===")
# Notka A mierzona dziesiec razy (9 razy po 9 wyswietlen, na koncu 17) plus
# notka B zmierzona raz (40). Prawda o zasiegu to 17 + 40 = 57.
# Suma po POMIARACH dalaby 9*9 + 17 + 40 = 138 — liczbe wieksza od prawdy,
# czyli taka, ktorej nikt nie zakwestionuje.
historia = [_linia("A", "2026-08-25T0%d:00:00+00:00" % i, wyswietlenia=9,
                   polubienia=1, subskrypcje=0) for i in range(9)]
historia.append(_linia("A", "2026-08-25T09:00:00+00:00", wyswietlenia=17,
                       polubienia=4, odpowiedzi=2, subskrypcje=1, obserwacje=0))
historia.append(_linia("B", "2026-08-25T09:00:00+00:00", wyswietlenia=40,
                       polubienia=2, subskrypcje=0, obserwacje=1))
p = _z_liniami(historia, statystyki.podsumowanie)
sprawdz("pozycji jest dwie", p["pozycje"] == 2, p["pozycje"])
sprawdz("pomiarow jedenascie, i widac to osobno", p["pomiary"] == 11, p["pomiary"])
sprawdz("laczne wyswietlenia = 57, nie 138",
        p["wyswietlenia"] == 57, p["wyswietlenia"])
sprawdz("laczne polubienia liczone tak samo", p["polubienia"] == 6, p["polubienia"])
sprawdz("laczne subskrypcje = 1", p["subskrypcje"] == 1, p["subskrypcje"])
sprawdz("obserwacje sumowane osobno od subskrypcji", p["obserwacje"] == 1,
        p["obserwacje"])
sprawdz("srednia dzieli przez POZYCJE", p["srednia_wyswietlen"] == 28.5,
        p["srednia_wyswietlen"])
# KONTRDOWOD na wybor najlepszej: B ma ponad dwa razy wiecej wyswietlen, ale
# ZERO subskrypcji. Ranking po zasiegu wskazalby B i odpowiedzialby na inne
# pytanie niz zadane — „co bylo widoczne" zamiast „co przynioslo ludzi".
sprawdz("najlepsza to ta z subskrypcja, nie ta z zasiegiem",
        p["najlepsza"]["id"] == "A", p["najlepsza"])
sprawdz("i niesie liczby, ktore o tym zdecydowaly",
        p["najlepsza"]["subskrypcje"] == 1 and p["najlepsza"]["wyswietlenia"] == 17,
        p["najlepsza"])
sprawdz("oraz skrot tekstu, po ktorym da sie ja rozpoznac",
        p["najlepsza"]["tekst"] == "notka A", p["najlepsza"])

# Remis po subskrypcjach rozstrzygaja wyswietlenia. Slabsza lezy PIERWSZA,
# wiec implementacja patrzaca tylko na subskrypcje wskazalaby ja.
remis = [_linia("C", "2026-08-25T09:00:00+00:00", wyswietlenia=11, subskrypcje=2),
         _linia("D", "2026-08-25T09:00:00+00:00", wyswietlenia=33, subskrypcje=2)]
p2 = _z_liniami(remis, statystyki.podsumowanie)
sprawdz("przy remisie subskrypcji wygrywa wieksza liczba wyswietlen",
        p2["najlepsza"]["id"] == "D", p2["najlepsza"])

# Podsumowanie rodzaju, ktorego nie ma, to zera — nie wyjatek i nie None.
p3 = _z_liniami(historia, lambda: statystyki.podsumowanie("artykul"))
sprawdz("rodzaj bez pozycji: zera zamiast wyjatku",
        p3["pozycje"] == 0 and p3["wyswietlenia"] == 0
        and p3["srednia_wyswietlen"] == 0.0 and p3["najlepsza"] is None, p3)
# KONTRDOWOD: filtr nie moze wycinac wszystkiego zawsze.
p4 = _z_liniami(historia, lambda: statystyki.podsumowanie("notka"))
sprawdz("a ten sam filtr na `notka` widzi obie pozycje", p4["pozycje"] == 2, p4)

print()
print("=== 7. MODUL NIE CHODZI DO SIECI ===")
# Cala wartosc tego modulu polega na tym, ze da sie go przetestowac bez
# przegladarki i bez dotykania konta. Jedno `import requests` odbiera testowi
# ten status po cichu: testy nadal przechodza, tylko juz nie na tym samym.
import ast   # noqa: E402

zrodlo = pathlib.Path("agent-v2/statystyki.py").read_text(encoding="utf-8")
drzewo = ast.parse(zrodlo)
importy = set()
for w in ast.walk(drzewo):
    if isinstance(w, ast.Import):
        importy.update(a.name.split(".")[0] for a in w.names)
    elif isinstance(w, ast.ImportFrom) and w.module:
        importy.add(w.module.split(".")[0])
sieciowe = importy & {"requests", "httpx", "urllib", "http", "socket",
                      "playwright", "browser", "aiohttp"}
sprawdz("zadnego importu sieciowego", not sieciowe, sorted(sieciowe))


def _wywolania(wezel):
    """Nazwy wszystkich wywolywanych funkcji w drzewie."""
    nazwy = set()
    for w in ast.walk(wezel):
        if isinstance(w, ast.Call):
            nazwa = getattr(w.func, "attr", None) or getattr(w.func, "id", None)
            if nazwa:
                nazwy.add(nazwa)
    return nazwy


# `get` i `post` celowo poza lista: tu wolamy `slownik.get` kilkanascie razy.
ZAKAZANE = {"api_json", "goto", "urlopen", "urlretrieve", "request", "fetch",
            "connect", "wait_for_timeout"}
zlapane = _wywolania(drzewo) & ZAKAZANE
sprawdz("i zadnego wywolania sieciowego", not zlapane, sorted(zlapane))
# KONTRDOWOD: oba wykrywacze musza cokolwiek widziec, inaczej przechodza zawsze.
sprawdz("wykrywacz importow w ogole dziala",
        {"config", "json"} <= importy, sorted(importy))
sprawdz("wykrywacz wywolan zlapalby prawdziwe wejscie do API",
        _wywolania(ast.parse('browser.api_json(page, "/api/v1/note_stats/c-1")'))
        & ZAKAZANE == {"api_json"})

print()
print("=== SWIEZA NOTKA: KARTA ZBIORCZA MILCZY, ROZBICIE JUZ MOWI ===")
# ZNALEZIONE RECZNYM SPRAWDZENIEM 25 sierpnia, na dwunastu notkach produkcji.
# Dla dojrzalych obie liczby zgadzaly sie co do jednego: 26=26, 19=19, 14=14,
# 12=12. Ale notka wystawiona tego samego dnia miala w karcie zbiorczej ZERO,
# a w rozbiciu po powierzchniach OSIEM — raport pokazywal wpis bez ani jednego
# wejscia, ktory realnie mial osiem.
#
# Powierzchnie to te same wyswietlenia w rozbiciu, wiec ich suma nie moze
# przekroczyc calosci. Gdy przekracza, znaczy to, ze calosci wlasnie nie znamy.
_SWIEZA = {"cards": [
    {"cardId": "impressions", "type": "chartCard", "headers": [{"value": 0}],
     "items": []},
    {"cardId": "surfaces", "type": "listCard", "items": [
        {"title": "Feed", "value": 5}, {"title": "Other", "value": 3}]},
]}
_r = statystyki.z_kart(_SWIEZA)
sprawdz("wyswietlenia biora sie z rozbicia, gdy karta zbiorcza ma zero",
        _r["wyswietlenia"] == 8, _r["wyswietlenia"])

# KONTRDOWOD 1: przy zgodnych liczbach NIC sie nie zmienia — inaczej poprawka
# zawyzalaby kazdy pomiar przez podwojne liczenie.
_DOJRZALA = {"cards": [
    {"cardId": "impressions", "type": "chartCard", "headers": [{"value": 26}]},
    {"cardId": "surfaces", "type": "listCard", "items": [
        {"title": "Feed", "value": 20}, {"title": "Other", "value": 6}]},
]}
sprawdz("przy zgodnych liczbach wynik sie nie zmienia",
        statystyki.z_kart(_DOJRZALA)["wyswietlenia"] == 26)

# KONTRDOWOD 2: gdy karta zbiorcza mowi WIECEJ niz rozbicie, wygrywa ona —
# bo rozbicie moze nie wymieniac wszystkich powierzchni.
_NIEPELNE = {"cards": [
    {"cardId": "impressions", "type": "chartCard", "headers": [{"value": 30}]},
    {"cardId": "surfaces", "type": "listCard", "items": [
        {"title": "Feed", "value": 4}]},
]}
sprawdz("karta zbiorcza wygrywa, gdy mowi wiecej",
        statystyki.z_kart(_NIEPELNE)["wyswietlenia"] == 30)

sprawdz("brak obu kart daje zero, nie wyjatek",
        statystyki.z_kart({"cards": []})["wyswietlenia"] == 0)

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
