# -*- coding: utf-8 -*-
"""Artykul nie moze wypasc z pomiaru przez limit.

ZMIERZONE 30 sierpnia na zywym koncie: 369 pomiarow komentarzy, 365 notek,
24 odpowiedzi i ZERO artykulow. Artykul to najdrozsza rzecz, jaka to konto
produkuje — research plus pisanie to okolo dolara za sztuke — i jedyna,
o ktorej wiedzielismy wylacznie tyle, ze wyszla.

TRZY WADY PO KOLEI, KAZDA UKRYTA POD POPRZEDNIA.

  1. `/api/v1/note_stats/p-<id>` oddaje dla artykulu poprawna i PUSTA
     odpowiedz: jedna karte (podglad wpisu), podczas gdy notka dostaje piec.
     Ta droga dawala piec rekordow z samymi zerami — a to gorsze niz brak
     pomiaru, bo wyglada na dane. Prawdziwe liczby sa w panelu wydawcy,
     pod `/api/v1/post_management/published`, dla wszystkich naraz.
  2. `/api/v1/archive` nalezy do NASZEJ PUBLIKACJI, nie do serwisu. Wywolane
     bez `baza` szlo na substack.com, oddawalo cos, co nie jest lista, a `or []`
     zamienialo to w cisze. Przebieg na zywo: 46 pozycji, zero artykulow.
  3. I dopiero pod tym siedziala prawdziwa: limit. Kod mowil

         nasze  = [x for x in widziane if x["rodzaj"] == "notka"]
         reszta = [x for x in widziane if x["rodzaj"] != "notka"]
         return nasze + reszta[-max(0, ile - len(nasze)):]

     Artykuly wpadaly do `reszty`, staly w niej NA POCZATKU (dopisujemy je
     przed dziennikiem), a `reszta[-N:]` bierze od konca. Wycinalo je pierwsze.

To DRUGI RAZ ten sam blad: identyczna poprawka powstala wczesniej dla notek,
a komentarz nad ta linijka opisuje ja wprost. Ochrona byla WYLICZONA po nazwie
rodzaju, wiec nowy rodzaj wszedl prosto w te sama pulapke. Dlatego test pyta
o REGULE — nasza wlasna tresc nie podlega limitowi — a nie o dwie nazwy.

TRZECI RAZ (28.09.2026): komentarze dostawaly `ile - len(nasze)`, czyli to,
co zostanie po naszych tresciach. Od 17 wrzesnia notek i artykulow bylo
wiecej niz 60 i ani jeden komentarz nie mial pomiaru. Komentarze maja teraz
WLASNY budzet (sekcja 6), a numer z pola `gdzie` (numer watku, nie naszej
odpowiedzi) nie jest brany.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo.
"""
import json
import pathlib
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, "agent-v2")
import browser  # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# --- atrapa API: oddaje to, co oddal ZYWY Substack 30 sierpnia --------------
#
# Ksztalty przepisane z prawdziwej odpowiedzi, nie wymyslone: archiwum oddalo
# liste piatki postow, kanal profilu — pozycje z zagniezdzonym `comment`.
# Liczby przepisane z odpowiedzi ZYWEGO konta z 30 sierpnia, nie wymyslone.
PANEL = [{"id": 900000002, "title": "Example Article One",
          "reaction_count": 1, "comment_count": 0, "child_comment_count": 0,
          "stats": {"views": 8, "sent": 4, "delivered": 4, "opened": 2,
                    "clicks": 0, "shares": 0, "signups_within_1_day": 3}},
         {"id": 900000003, "title": "Example Article Three",
          "reaction_count": 3, "comment_count": 2, "child_comment_count": 2,
          "stats": {"views": 32, "sent": 4, "delivered": 4, "opened": 1,
                    "clicks": 3, "shares": 0, "signups_within_1_day": 0}}]
# Archiwum niesie restacki, ktorych panel NIE ma — i nie sa tym samym co
# `shares`: dla wpisu 900000002 archiwum mowi 1 restack, panel 0 udostepnien.
ARCHIWUM = [{"id": 900000002, "title": "Example Article One",
             "restacks": 1},
            {"id": 900000003, "title": "Example Article Three",
             "restacks": 0}]
ARTYKULY = PANEL

wolania: list[tuple[str, str | None]] = []


def atrapa_api(page, sciezka, baza=None):
    wolania.append((sciezka, baza))
    if "public_profile" in sciezka:
        return {"id": 999}
    if "reader/feed/profile" in sciezka:
        return {"items": [{"comment": {"id": 320000000 + i, "body": "notka %d" % i}}
                          for i in range(12)]}
    # ADRES BAZOWY JEST TU CZESCIA UMOWY. Obie te koncowki naleza do NASZEJ
    # publikacji; bez `baza` `api_json` pyta substack.com, gdzie ich nie ma.
    # Atrapa zachowuje sie wiec tak samo jak serwis: nie oddaje nic.
    nasza = bool(baza) and "substack.com/api" not in str(baza)
    if sciezka.startswith("/api/v1/archive"):
        return list(ARCHIWUM) if nasza else None
    if sciezka.startswith("/api/v1/post_management/published"):
        return {"posts": list(PANEL), "total": len(PANEL)} if nasza else None
    return None


# --- dziennik: tyle komentarzy, ze limit MUSI ciac -------------------------
TERAZ = datetime.now(timezone.utc).isoformat(timespec="seconds")
katalog = pathlib.Path(tempfile.mkdtemp())
dziennik = katalog / "dziennik.jsonl"
with dziennik.open("w", encoding="utf-8") as f:
    for i in range(80):
        f.write(json.dumps({"udane": True, "rodzaj": "komentarz", "kiedy": TERAZ,
                            "nasz_id": 400000000 + i,
                            "tekst": "komentarz %d" % i}) + "\n")

stare_api, stary_dziennik = browser.api_json, browser.DZIENNIK
browser.api_json = atrapa_api
browser.DZIENNIK = dziennik

try:
    print("=== 1. ARTYKULY W OGOLE PRZYCHODZA ===")
    poz = browser.nasze_pozycje_do_pomiaru(page=object(), ile=60)
    art = [x for x in poz if x["rodzaj"] == "artykul"]
    sprawdz("panel wydawcy pytany z adresem NASZEJ publikacji",
            any(s.startswith("/api/v1/post_management/published")
                and b and "substack.com/api" not in str(b) for s, b in wolania),
            [b for s, b in wolania if "post_management" in s])
    sprawdz("oba artykuly sa w pomiarze", len(art) == 2, len(art))

    print()
    print("=== 1b. LICZBY SA PRAWDZIWE, NIE ZEROWE ===")
    # Cala poprzednia droga (`note_stats/p-`) oddawala rekordy z samymi zerami.
    # Test musi wiec pytac o WARTOSCI, nie o to, ze rekord istnieje.
    w = {x["id"]: x["statystyki"] for x in art}
    sprawdz("wyswietlenia z panelu", w["900000002"]["wyswietlenia"] == 8,
            w["900000002"]["wyswietlenia"])
    sprawdz("zapisy przypisane do wpisu", w["900000002"]["subskrypcje"] == 3,
            w["900000002"]["subskrypcje"])
    sprawdz("klikniecia w link", w["900000003"]["klikniecia_w_link"] == 3,
            w["900000003"]["klikniecia_w_link"])
    sprawdz("odpowiedzi licza CALY watek, nie sam pierwszy poziom",
            w["900000003"]["odpowiedzi"] == 4, w["900000003"]["odpowiedzi"])
    sprawdz("restacki wziete z archiwum, nie z `shares`",
            w["900000002"]["restacki"] == 1 and w["900000002"]["udostepnienia"] == 0,
            (w["900000002"]["restacki"], w["900000002"]["udostepnienia"]))
    sprawdz("poczta zmierzona (notka jej nie ma)",
            w["900000002"]["wyslane"] == 4 and w["900000002"]["otwarcia"] == 2)

    print()
    print("=== 2. LIMIT ICH NIE WYCINA — TO JEST TA WADA ===")
    # Osiemdziesiat komentarzy przy limicie 60. Przed poprawka artykuly stały
    # na poczatku `reszty`, a `reszta[-N:]` brala od konca: znikalo wszystkie
    # piec, a wynik mial dokladnie 60 pozycji i wygladal poprawnie.
    kom = [x for x in poz if x["rodzaj"] == "komentarz"]
    sprawdz("osiemdziesiat komentarzy zostalo przyciete", len(kom) < 80, len(kom))
    sprawdz("komentarze maja WLASNY budzet: 60 najnowszych", len(kom) == 60, len(kom))
    sprawdz("i sa to najnowsze, nie najstarsze",
            {x["id"] for x in kom} == {str(400000000 + i) for i in range(20, 80)})
    notki = [x for x in poz if x["rodzaj"] == "notka"]
    sprawdz("notki tez przezyly (stara ochrona nie zginela)",
            len(notki) == 12, len(notki))
    sprawdz("nasze tresci sa poza limitem: 12 notek + 2 artykuly + 60 komentarzy",
            len(poz) == 74, len(poz))

    print()
    print("=== 3. REGULA JEST OGOLNA, NIE WYLICZONA PO NAZWACH ===")
    # Gdyby ochrona byla znowu wyliczeniem, kolejny nowy rodzaj wszedlby
    # w te sama pulapke po raz TRZECI. Sprawdzamy, ze `ile` odnosi sie tylko
    # do cudzych watkow.
    poz_male = browser.nasze_pozycje_do_pomiaru(page=object(), ile=3)
    art_male = [x for x in poz_male if x["rodzaj"] == "artykul"]
    notki_male = [x for x in poz_male if x["rodzaj"] == "notka"]
    sprawdz("przy limicie 3 artykuly nadal sa wszystkie", len(art_male) == 2,
            len(art_male))
    sprawdz("i notki tez", len(notki_male) == 12, len(notki_male))
    sprawdz("a cudze watki dostaja swoje 3 miejsca, niezaleznie od notek",
            len([x for x in poz_male if x["rodzaj"] == "komentarz"]) == 3,
            len([x for x in poz_male if x["rodzaj"] == "komentarz"]))
    # `[-0:]` TO CALA LISTA. Przy `ile=0` stary wycinek oddawalby WSZYSTKIE 80.
    poz_zero = browser.nasze_pozycje_do_pomiaru(page=object(), ile=0)
    sprawdz("przy limicie 0 cudze watki sa przyciete do zera, nie do calosci",
            len([x for x in poz_zero if x["rodzaj"] == "komentarz"]) == 0,
            len([x for x in poz_zero if x["rodzaj"] == "komentarz"]))

    print()
    print("=== 4. KONTRDOWOD: STARA WERSJA MUSI TU POLEC ===")
    # Bez tego test nie dowodzi niczego — przechodzilby takze na kodzie,
    # ktory wlasnie naprawiamy.
    widziane = {}
    for a in PANEL:
        widziane[str(a["id"])] = {"rodzaj": "artykul", "id": str(a["id"])}
    for i in range(80):
        widziane[str(400000000 + i)] = {"rodzaj": "komentarz",
                                        "id": str(400000000 + i)}
    po_staremu_nasze = [x for x in widziane.values() if x["rodzaj"] == "notka"]
    po_staremu_reszta = [x for x in widziane.values() if x["rodzaj"] != "notka"]
    po_staremu = po_staremu_nasze + po_staremu_reszta[-max(0, 60 - len(po_staremu_nasze)):]
    sprawdz("stara regula gubi WSZYSTKIE artykuly",
            len([x for x in po_staremu if x["rodzaj"] == "artykul"]) == 0,
            "gdyby ich nie gubila, ten test nie mierzylby wady")

    print()
    print("=== 5. ARTYKUL NIE IDZIE PRZEZ KONCOWKE NOTEK ===")
    # `note_stats/p-<id>` odpowiada POPRAWNIE i pusto. Gdyby artykul tamtedy
    # szedl, dostawalibysmy komplet rekordow z zerami — dane, ktorych nie ma.
    zrodlo = pathlib.Path("agent-v2/browser.py").read_text(encoding="utf-8")
    sprawdz("kod nie sklada przedrostka 'p-' do note_stats",
            "note_stats/{przedrostek}" not in zrodlo)
    sprawdz("artykul ma osobna galaz w pomiarze",
            'if rodzaj == "artykul":' in zrodlo)
    sprawdz("i bierze liczby z panelu wydawcy",
            "post_management/published" in zrodlo)
    # KONTRDOWOD: gdyby atrapa oddawala puste karty (tak jak zywy serwis dla
    # `p-`), rekord bylby samymi zerami i sekcja 1b by go zlapala.
    sprawdz("pusty rekord nie trafia do pomiaru",
            all(any(v for k, v in x["statystyki"].items()
                    if isinstance(v, int)) for x in art))

    print()
    print("=== 6. KOMENTARZE MAJA WLASNY BUDZET, TYLKO Z WLASNYM NUMEREM ===")
    # Stan produkcji 28.09.2026: 128 notek i 8 artykulow, limit 60 — komentarze
    # dostawaly `60 - 136`, czyli nic, od 17 wrzesnia. Tu 70 notek z numerami.
    stary_teraz = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(timespec="seconds")
    with dziennik.open("w", encoding="utf-8") as f:
        # Numery od 900000000: atrapy rozpoznawalne jako atrapy (audyt, sekcja 2c).
        for i in range(70):
            f.write(json.dumps({"udane": True, "rodzaj": "notka", "kiedy": stary_teraz,
                                "id": 910000000 + i}) + "\n")
        for i in range(10):
            f.write(json.dumps({"udane": True, "rodzaj": "komentarz", "kiedy": TERAZ,
                                "nasz_id": 920000000 + i}) + "\n")
        # STARY komentarz: zasieg juz zebral, nie mierzymy go w nieskonczonosc.
        f.write(json.dumps({"udane": True, "rodzaj": "komentarz", "kiedy": stary_teraz,
                            "nasz_id": 930000000}) + "\n")
        # Odpowiedz BEZ wlasnego numeru: `gdzie` to numer WATKU (tu cudzej notki).
        f.write(json.dumps({"udane": True, "rodzaj": "odpowiedz", "kiedy": TERAZ,
                            "gdzie": "https://substack.com/@ktos/note/c-940000000"}) + "\n")
        # Odpowiedz w watku NASZEJ notki, tez bez numeru — to bylaby notka mierzona drugi raz.
        f.write(json.dumps({"udane": True, "rodzaj": "odpowiedz", "kiedy": TERAZ,
                            "gdzie": "https://substack.com/@my/note/c-910000001"}) + "\n")
    poz6 = browser.nasze_pozycje_do_pomiaru(page=object(), ile=60)
    kom6 = [x for x in poz6 if x["rodzaj"] == "komentarz"]
    sprawdz("przy %d naszych tresciach (limit 60) komentarze z ostatnich dob nadal sa mierzone"
            % len([x for x in poz6 if x["rodzaj"] in ("artykul", "notka")]),
            len(kom6) == 10, len(kom6))
    sprawdz("komentarz sprzed %d dob nie jest mierzony" % browser.DNI_POMIARU_KOMENTARZY,
            "930000000" not in {x["id"] for x in poz6})
    sprawdz("numer watku z `gdzie` nie trafia do pomiaru",
            "940000000" not in {x["id"] for x in poz6})
    sprawdz("nasza notka nie jest mierzona drugi raz jako odpowiedz",
            [x["rodzaj"] for x in poz6 if x["id"] == "910000001"] == ["notka"],
            [x["rodzaj"] for x in poz6 if x["id"] == "910000001"])
    sprawdz("zadnej odpowiedzi w pomiarze (obie byly bez wlasnego numeru)",
            not [x for x in poz6 if x["rodzaj"] == "odpowiedz"])
    # KONTRDOWOD: stara regula na tych samych danych dawala zero komentarzy.
    nasze6 = [x for x in poz6 if x["rodzaj"] in ("artykul", "notka")]
    reszta6 = [x for x in poz6 if x["rodzaj"] not in ("artykul", "notka")]
    po_staremu6 = max(0, 60 - len(nasze6))
    sprawdz("stara regula dawala tu ZERO komentarzy",
            po_staremu6 == 0 and len(reszta6[-po_staremu6:] if po_staremu6 else []) == 0,
            po_staremu6)
finally:
    browser.api_json, browser.DZIENNIK = stare_api, stary_dziennik

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
