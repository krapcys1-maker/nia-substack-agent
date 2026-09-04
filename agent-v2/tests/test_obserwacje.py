"""Test rozdzielenia obserwacji od subskrypcji i roznorodnosci notek.

Kazda zmiana z kontrdowodem. Nic nie publikuje.
"""
import ast
import hashlib
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import browser  # noqa: E402
import config   # noqa: E402
import wlasna_konfiguracja  # noqa: E402
import norma    # noqa: E402
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


# Asercje o DOSTARCZONYCH wartosciach, pomijane widocznie,
# gdy operator ma wlasne w `konfiguracja.toml`.
sprawdz_nasze = wlasna_konfiguracja.tylko_nasze(sprawdz)


def odcisk(p):
    p = pathlib.Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else "brak"


PILNOWANE = [config.DB_PATH, config.DATA_DIR / "zuzyte_fakty.json",
             config.DATA_DIR / "promocja.json", config.DATA_DIR / "dziennik.jsonl",
             # Skrot pamieci permanentnej. Pilnowany, bo powstaje SAM przy
             # pierwszym pytaniu o pamiec — test, ktory zapomni go przekierowac
             # do katalogu tymczasowego, zalozylby go w produkcji po cichu.
             stages.PAMIEC_NOTEK_PLIK]
PRZED = {str(p): odcisk(p) for p in PILNOWANE}

print("=== 1. SUBSKRYPCJA KLIKA TYLKO 'SUBSCRIBE' ===")
#
# TA SEKCJA MIALA WCZESNIEJ DRUGA POLOWE I BYLA ONA ZIELONA NAD MARTWYM KODEM.
#
# Do 1 wrzesnia 2026 stalo tu takze „obserwowanie klika 'Follow'", sprawdzane
# na atrapie profilu z DWOMA przyciskami na wierzchu: „Subscribe" i „Follow".
# Atrapa przechodzila, `obserwuj_profil` klikalo „Follow", test swiecil na
# zielono — a w produkcji obserwacje przez dziewiec dni wynosily ZERO.
#
# Powod: TAKI PROFIL NIE ISTNIEJE. Zmierzone na zywo 1 wrzesnia 2026, szesc
# profili: w naglowku sa dokladnie trzy przyciski — „Subscribe", „Message"
# i kolko z `aria-label="Profile actions"`. Przycisku „Follow" na wierzchu nie
# ma i nigdy nie bylo; obserwowanie siedzi w menu pod tym kolkiem. Atrapa
# kodowala falszywy model swiata, wiec test mierzyl zgodnosc kodu z tym
# falszem, a nie z Substackiem.
#
# Sprawdzenie obserwowania przeniesione do `test_obserwowanie_przez_menu.py`,
# gdzie atrapa odwzorowuje ZMIERZONE menu. Tutaj zostaje subskrypcja — ona
# naprawde chodzi przyciskiem na wierzchu — bo to ona broni rozdzielenia
# obu zdolnosci, o ktore ten plik chodzi.

klikniete = []


class Przycisk:
    def __init__(self, nazwa, jest):
        self.nazwa, self.jest = nazwa, jest
        self.first = self

    def count(self):
        return 1 if self.jest else 0

    def is_visible(self):
        return self.jest

    def click(self, timeout=None):
        klikniete.append(self.nazwa)
        self.jest = False


class Strona:
    def __init__(self, dostepne):
        self.dostepne = dostepne
        self.przyciski = {}

    def goto(self, *a, **k):
        pass

    def wait_for_timeout(self, ms):
        pass

    def get_by_role(self, rola, name=None, exact=None):
        if name not in self.przyciski:
            self.przyciski[name] = Przycisk(name, name in self.dostepne)
        return self.przyciski[name]

    def close(self):
        pass


class Kontekst:
    def __init__(self, strona):
        self.strona = strona

    def new_page(self):
        return self.strona

    def close(self):
        pass

    def stop(self):
        pass


oryg = (browser.podlacz_sie, browser.wymagaj_sesji, browser.DZIENNIK,
        browser.naprawde_wyslac)


def ustaw(dostepne):
    klikniete.clear()
    s = Strona(dostepne)
    browser.wymagaj_sesji = lambda: None
    browser.podlacz_sie = lambda: (Kontekst(s), Kontekst(s), Kontekst(s))
    browser.naprawde_wyslac = lambda wyslij, co: wyslij
    browser.DZIENNIK = pathlib.Path(tempfile.mkdtemp()) / "d.jsonl"


try:
    # Profil taki, jaki NAPRAWDE jest: na wierzchu „Subscribe" i „Message",
    # a obserwowanie schowane w menu (dla tej atrapy: nieosiagalne).
    ustaw({"Subscribe", "Message"})
    browser.zasubskrybuj("ktos", wyslij=True)
    sprawdz("subskrypcja klika 'Subscribe'", klikniete == ["Subscribe"], klikniete)
    sprawdz("i NIE klika 'Message'", "Message" not in klikniete, klikniete)

    # KONTRDOWOD: stara kolejnosc na tym samym profilu.
    stara_kolejnosc = ("Subscribe", "Subskrybuj", "Follow", "Obserwuj")
    pierwszy_stary = next(n for n in stara_kolejnosc if n in {"Subscribe", "Follow"})
    sprawdz("STARA kolejnosc wybralaby 'Subscribe' (test rozroznia)",
            pierwszy_stary == "Subscribe")

    # Gdy wlasciwego przycisku NIE MA — nie wolno kliknac zastepczego.
    ustaw({"Message"})
    w = browser.zasubskrybuj("ktos", wyslij=True)
    sprawdz("brak 'Subscribe' -> subskrypcja NIE klika nic", klikniete == [],
            klikniete)
    sprawdz("i melduje, ze sie nie udalo", w["zrobione"] is False, w)
    sprawdz("z powodem", "subskrypcja" in (w["blad"] or ""), w["blad"])

    # Polska wersja interfejsu.
    ustaw({"Subskrybuj", "Wiadomość"})
    browser.zasubskrybuj("ktos", wyslij=True)
    sprawdz("dziala po polsku: 'Subskrybuj'", klikniete == ["Subskrybuj"],
            klikniete)

    # Tryb sprawdzenia nie klika.
    ustaw({"Subscribe", "Message"})
    browser.zasubskrybuj("ktos", wyslij=False)
    sprawdz("tryb sprawdzenia nie klika nic", klikniete == [], klikniete)

    # I DOWOD, ZE STARA DROGA NIE UMIALA OBSERWOWAC. Na tej samej atrapie —
    # czyli na profilu takim, jaki jest naprawde — przedpoprawkowa
    # implementacja `obserwuj_profil` odchodzi z pustymi rekami. To jest ta
    # zerowa obserwacja, ktora przez dziewiec dni tlumaczono zdjetym
    # przyciskiem.
    ustaw({"Subscribe", "Message"})
    w = browser._klik_na_profilu("ktos", ("Follow", "Obserwuj"), "obserwacja",
                                 True)
    sprawdz("KONTRDOWOD: stara droga obserwacji nie klikala nic",
            klikniete == [], klikniete)
    sprawdz("KONTRDOWOD: i konczyla sie porazka", w["zrobione"] is False, w)
finally:
    (browser.podlacz_sie, browser.wymagaj_sesji, browser.DZIENNIK,
     browser.naprawde_wyslac) = oryg

print()
print("=== 2. OSOBNE BUDZETY ===")

zrodlo = pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8")
# OBA PRZYDZIALY ISTNIEJA I SA OSOBNE — pytamy o WLASNOSC, nie o zapis.
#
# Stalo tu `'budzet["follow"]' in zrodlo` i `'budzet["subskrypcje"]' in
# zrodlo`. Kod bierze dzis oba jednym wyrazeniem (`budzet[k] for k in (...)`),
# a tamte napisy zostaly w KOMENTARZU opisujacym poprawke z 20 sierpnia — wiec
# obie asercje przechodzily na cytacie STAREGO kodu i nie zauwazylyby, gdyby
# ktorykolwiek przydzial zniknal. Zlapal to `test_asercje_po_zrodle.py`.
_klucze_budzetu = set()
for _w in ast.walk(ast.parse(zrodlo)):
    if (isinstance(_w, ast.Subscript)
            and isinstance(_w.value, ast.Name) and _w.value.id == "budzet"):
        if isinstance(_w.slice, ast.Constant) and isinstance(_w.slice.value, str):
            _klucze_budzetu.add(_w.slice.value)
    # `budzet[k] for k in (...)` — klucze stoja w krotce, nie w indeksie.
    if isinstance(_w, ast.comprehension) and isinstance(_w.iter, ast.Tuple):
        _klucze_budzetu |= {e.value for e in _w.iter.elts
                            if isinstance(e, ast.Constant)
                            and isinstance(e.value, str)}
sprawdz("dzien rozdziela przydzial na 'follow'",
        "follow" in _klucze_budzetu, sorted(_klucze_budzetu))
sprawdz("i osobno na 'subskrypcje'",
        "subskrypcje" in _klucze_budzetu, sorted(_klucze_budzetu))
# I SA TO DWIE ROZNE LICZBY, a nie jedna pod dwiema nazwami: przy roznych
# widelkach przydzialy musza sie roznic. To jest awaria, przed ktora ta sekcja
# stoi — subskrypcje szly W TEMPIE OBSERWACJI.
sprawdz("widelki obserwacji i subskrypcji sa osobne",
        config.FOLLOW_MIESIECZNIE != config.SUBSKRYPCJE_MIESIECZNIE,
        (config.FOLLOW_MIESIECZNIE, config.SUBSKRYPCJE_MIESIECZNIE))
sprawdz("obserwowanie wola obserwuj_profil, nie zasubskrybuj",
        "browser.obserwuj_profil(uchwyt, wyslij=True)" in zrodlo)
sprawdz("subskrypcje sa osobnym blokiem dnia",
        '("subskrypcje", subskrybuj)' in zrodlo)
print("    widelki: obserwacje %s/mies, subskrypcje %s/mies"
      % (config.FOLLOW_MIESIECZNIE, config.SUBSKRYPCJE_MIESIECZNIE))
# Asercja wisiala na liczbie obserwacji: subskrypcji mialo byc mniej NIZ ICH.
# Po wycofaniu obserwacji (2026-08-23, Substack zdjal „Follow" z profili)
# obserwacji jest zero, wiec porownanie stalo sie niespelnialne — a bronilo
# rzeczy, ktora dalej jest prawdziwa i nie ma z obserwacjami nic wspolnego.
#
# Awaria, przed ktora to stalo: `_klik_na_profilu` probowal kolejno „Subscribe"
# i „Follow" i bral pierwszy znaleziony, a „Subscribe" jest zawsze — wiec kazda
# proba obserwacji konczyla sie SUBSKRYPCJA. Agent subskrybowal w tempie
# obserwacji, prosto do skrzynki wlasciciela. Miara tego bledu jest wielkosc
# BEZWZGLEDNA subskrypcji, nie ich stosunek do czegokolwiek.
#
# SUFIT PODNIESIONY 1 WRZESNIA 2026 z 12 do 20 miesiecznie i to jest zmiana
# uzasadniona SKUTKIEM, nie wygoda: subskrypcja ma 11,5% konwersji zwrotnej
# wobec 3,4% przy obserwacji, a obserwacje zeszly w tym samym ruchu z 44 do 16.
# Miara bledu, przed ktorym ta sekcja stoi, sie nie zmienia: awaria polegala na
# tym, ze subskrypcje szly W TEMPIE OBSERWACJI z tamtej epoki, czyli do 44
# miesiecznie. Ta liczba jest wiec dalej progiem, tylko juz nie czyta sie jej
# z konfiguracji — bo w konfiguracji jej po prostu nie ma.
TEMPO_OBSERWACJI_SPRZED_NAPRAWY = 44
sprawdz("subskrypcje nie ida w tempie obserwacji sprzed naprawy",
        config.SUBSKRYPCJE_MIESIECZNIE[1] < TEMPO_OBSERWACJI_SPRZED_NAPRAWY,
        config.SUBSKRYPCJE_MIESIECZNIE)
sprawdz("i wielokrotnie mniej niz komentarzy, ktore nikogo nie zasypuja",
        config.SUBSKRYPCJE_MIESIECZNIE[1] * 4 < config.KOMENTARZE_DZIENNIE[0] * 30,
        (config.SUBSKRYPCJE_MIESIECZNIE, config.KOMENTARZE_DZIENNIE))
sprawdz("KONTRDOWOD: tempo obserwacji sprzed naprawy by tego nie przeszlo",
        not (TEMPO_OBSERWACJI_SPRZED_NAPRAWY
             < TEMPO_OBSERWACJI_SPRZED_NAPRAWY))

print()
print("=== 3. NOTKI NIE POWTARZAJA TEMATU ===")

ARTYKUL = ("Example Article Three  Sorting machines read a fluorescent "
           "barcode sprayed onto the envelope, never the printed address. "
           "The printed address is there for people, not for machines.")
PULA = [
    {"domain": "Postal handling",
     "fact": "A fluorescent barcode sprayed onto every envelope is what the "
             "sorting machines actually read; the printed address is for the "
             "person carrying it the last few metres."},
    {"domain": "Sealed enclosures", "fact": "The tiny hole in the middle pane of a "
     "pressure panel is a bleed hole that equalises the gap."},
    {"domain": "Vending", "fact": "A coin mechanism weighs and measures the "
     "conductivity of what you drop in, so a washer of the right alloy passes."},
]

zapas = list(PULA)
wybrany = stages.wybierz_material(zapas, [ARTYKUL])
print("    artykul dnia: sortowanie przesylek / kod fluorescencyjny")
print("    wybrano:      %s" % (wybrany or {}).get("domain"))
sprawdz("NIE wybiera faktu o tym samym, o czym jest artykul dnia",
        wybrany is not None and "fluorescent" not in wybrany["fact"].lower(),
        wybrany)
sprawdz("wybiera pierwszy NIEKOLIDUJACY", wybrany["domain"] == "Sealed enclosures",
        wybrany["domain"])
sprawdz("zdjety z zapasu", len(zapas) == 2, len(zapas))

# KONTRDOWOD: stary sposob bral pierwszy z brzegu — a pierwszy z brzegu jest
# tu wlasnie tym, ktory koliduje z artykulem dnia.
sprawdz("STARY sposob wzialby fakt o tym samym (test rozroznia)",
        "fluorescent" in PULA[0]["fact"].lower())

# Druga notka w tym samym przebiegu tez nie moze byc o tym samym.
juz = [ARTYKUL, "%s %s" % (wybrany["domain"], wybrany["fact"])]
drugi = stages.wybierz_material(zapas, juz)
sprawdz("druga notka to znowu inny temat",
        drugi is not None and drugi["domain"] == "Vending", drugi)

# Gdy zostaje juz tylko materiał o tym samym — lepiej mniej niz powtorka.
sprawdz("gdy wszystko koliduje -> None, zamiast powtorzyc",
        stages.wybierz_material([dict(PULA[0])], [ARTYKUL]) is None)
sprawdz("pusty zapas -> None", stages.wybierz_material([], [ARTYKUL]) is None)
sprawdz("brak czego unikac -> bierze pierwszy",
        stages.wybierz_material(list(PULA), [])["domain"] == "Postal handling")

print()
print("=== 4. MIARA PODOBIENSTWA ===")

sprawdz("ten sam temat rozpoznany",
        stages._o_tym_samym(ARTYKUL, PULA[0]["fact"]) is True)
sprawdz("inny temat NIE jest mylony",
        stages._o_tym_samym(ARTYKUL, PULA[1]["fact"]) is False)
sprawdz("krotkie teksty nie sa oceniane (za malo slow)",
        stages._o_tym_samym("post", "post") is False)

print()
print("=== 4b. PAMIEC NIE KONCZY SIE O POLNOCY ===")
# 23 i 24 sierpnia poszly dwie notki o TYM SAMYM fakcie, napisane innymi
# zdaniami. Ochrona istniala i dzialala — tylko `juz_o_tym` zaczynalo KAZDY
# DZIEN puste, wiec pytala wylacznie o to, co wystawiamy dzisiaj. Miedzy dniami
# zostawal `_klucz_faktu`, odcisk DOKLADNY, ktory na przeformulowaniu puszcza.
WCZORAJ = ("The four-figure code moulded into the sidewall of a tyre gives the "
           "week and the year it was manufactured, and nothing else. It is not "
           "a use-by date. No rule obliges anyone to print an expiry on a tyre, "
           "so the manufacturer publishes that advice separately instead.")
DZIS = {"domain": "Tyre labelling",
        "fact": ("That stamp of four figures on the side of your tyre is a "
                 "manufacturing date, week first and year second — not a "
                 "use-by. Nothing in the rules requires an expiry to appear on "
                 "the tyre itself, so the advice lives in a leaflet instead.")}

sprawdz("dokladny odcisk faktu NIE lapie przeformulowania",
        stages._klucz_faktu(WCZORAJ) != stages._klucz_faktu(DZIS["fact"]))
sprawdz("ale rozmyta miara juz tak",
        stages._o_tym_samym(DZIS["fact"], WCZORAJ,
                            **stages.POROWNANIE_MIEDZY_DNIAMI) is True)
sprawdz("wiec material z wczoraj zostaje odrzucony",
        stages.wybierz_material([dict(DZIS)], [], [WCZORAJ]) is None)
# KONTRDOWOD: bez pamieci poprzednich dni ten sam material przechodzi — czyli
# test naprawde mierzy TE zmiane, a nie cokolwiek innego.
sprawdz("a bez tej pamieci przeszedlby (tak powstala wpadka)",
        stages.wybierz_material([dict(DZIS)], [])["domain"] == "Tyre labelling")

# Prog miedzy dniami MUSI byc ostrzejszy od dziennego, inaczej blokuje notki
# na przypadkowych slowach. Zmierzone: przy progu dziennym dwie notki o zupelnie
# roznych rzeczach zderzaly sie na `nothing`, `number`, `whole`.
LUZNE_A = ("Sticker price in the EU is the whole price. VAT and every other tax "
           "are already inside the number on the shelf, so nothing is added at "
           "the till.")
LUZNE_B = ("Sunscreen's SPF number says nothing about the rays that age your "
           "skin. It measures UVB only, and the whole label turns on that.")
sprawdz("prog miedzy dniami jest ostrzejszy od dziennego",
        stages.POROWNANIE_MIEDZY_DNIAMI["prog"] > 0.15
        and stages.POROWNANIE_MIEDZY_DNIAMI["min_wspolnych"] > 2,
        stages.POROWNANIE_MIEDZY_DNIAMI)
sprawdz("i luzne zderzenie NIE blokuje notki",
        stages._o_tym_samym(LUZNE_A, LUZNE_B,
                            **stages.POROWNANIE_MIEDZY_DNIAMI) is False)

# Adres w notce promocyjnej nie jest tematem. Dwie notki z linkiem mialy trzy
# wspolne slowa — `https`, `substack`, nazwa publikacji — zanim ktokolwiek
# spojrzal, o czym sa.
Z_LINKIEM = "Pressure panels have a tiny hole. https://your-handle.substack.com/p/x"
Z_LINKIEM_2 = "Sorting machines read the barcode. https://your-handle.substack.com/p/y"
sprawdz("adres nie wpada do slow tematu",
        not ({"https", "substa"} & stages._slowa(Z_LINKIEM)),
        sorted(stages._slowa(Z_LINKIEM)))
sprawdz("wiec dwie notki z linkiem nie sa 'o tym samym'",
        stages._o_tym_samym(Z_LINKIEM, Z_LINKIEM_2) is False)

print()
print("=== 4c. PAMIEC JEST PERMANENTNA, NIE 'WIEKSZA' ===")
# Okno dwunastu bylo ochrona z terminem waznosci: powtorka sprzed pieciu dni
# przechodzila z automatu. Wlasciciel chce zera powtorzen NIGDY.
#
# Zmierzone 2026-08-25 na 29 wystawionych notkach: okna 8, 12, 20, 40 i pamiec
# PELNA blokuja te same PIEC notek. Zero roznicy, zero falszywych alarmow —
# z 399 par o roznych tematach prog miedzy dniami nie przepuscil ani jednej.
# Pelny rachunek stoi w docstringu `stages.pamiec_wystawionych`.


def dziennik_z_notek(katalog, teksty):
    """Buduje dziennik z podanych tekstow — po jednej UDANEJ notce na tekst."""
    import json as _json
    linie = [_json.dumps({"kiedy": "2026-08-2%dT10:00:00+00:00" % (i % 10),
                          "rodzaj": "notka", "udane": True, "tekst": t},
                         ensure_ascii=False)
             for i, t in enumerate(teksty)]
    (katalog / "dziennik.jsonl").write_text("\n".join(linie) + "\n",
                                            encoding="utf-8")


# Wypelniacz o slownictwie, ktore nie wystepuje w zadnej notce testowej.
WYPELNIACZ = [
    ("Harbour beacon %d turns green only when the estuary channel depth clears "
     "four metres, and the lantern keeper logs every sweep by hand." % i)
    for i in range(119)
]

with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    stary_plik = stages.PAMIEC_NOTEK_PLIK
    stare_okno = config.PAMIEC_NOTEK
    _zdjecie = config.uzyj_katalogu_danych(tmp)
    try:
        stages.PAMIEC_NOTEK_PLIK = tmp / "wystawione_notki.json"

        # Wczorajsza notka idzie na SAM POCZATEK, 119 notek przed dzisiejsza.
        dziennik_z_notek(tmp, [WCZORAJ] + WYPELNIACZ)
        pamiec = stages.pamiec_wystawionych()
        print("    notek w dzienniku: 120, odciskow w pamieci: %d" % len(pamiec))
        sprawdz("pamiec obejmuje wszystkie 120 notek", len(pamiec) == 120,
                len(pamiec))
        sprawdz("notka sprzed 119 pozycji NADAL blokuje powtorke",
                stages.wybierz_material([dict(DZIS)], [], pamiec) is None)

        # KONTRDOWOD: to samo z oknem dwunastu, czyli kodem sprzed zmiany.
        # Wczorajsza notka wypada z okna i powtorka przechodzi jak gdyby nigdy nic.
        config.PAMIEC_NOTEK = 12
        okno = stages.pamiec_wystawionych()
        sprawdz("KONTRDOWOD: okno 12 pamieta tylko 12 ostatnich", len(okno) == 12,
                len(okno))
        sprawdz("KONTRDOWOD: i przy oknie 12 powtorka PRZECHODZI (tak bylo)",
                stages.wybierz_material([dict(DZIS)], [], okno) is not None)
        config.PAMIEC_NOTEK = stare_okno
        sprawdz("stan obowiazujacy to pamiec bez okna",
                config.PAMIEC_NOTEK is None, config.PAMIEC_NOTEK)

        # LUZNE ZDERZENIE NADAL NIE BLOKUJE — to jest cena, ktorej nie placimy.
        # Przy pamieci bez konca kazda zapamietana notka to kolejna szansa na
        # falszywy alarm, a falszywy alarm kosztuje notke przy realizacji normy 60%.
        dziennik_z_notek(tmp, [LUZNE_A] + WYPELNIACZ)
        stages.PAMIEC_NOTEK_PLIK.unlink()       # inny dziennik = liczymy od zera
        pamiec_luzna = stages.pamiec_wystawionych()
        luzny = stages.wybierz_material(
            [{"domain": "Sun care", "fact": LUZNE_B}], [], pamiec_luzna)
        sprawdz("luzne zderzenie NIE blokuje mimo pelnej pamieci",
                luzny is not None and luzny["domain"] == "Sun care", luzny)
        sprawdz("i 119 obcych notek tez go nie blokuje",
                len(pamiec_luzna) == 120, len(pamiec_luzna))

        # DZIENNIK ZOSTAJE ZRODLEM PRAWDY: liczy sie to, co NAPRAWDE wyszlo.
        (tmp / "dziennik.jsonl").write_text("\n".join([
            '{"rodzaj": "notka", "udane": false, "tekst": %s}' % json.dumps(WCZORAJ),
            '{"rodzaj": "lajk", "udane": true, "tekst": %s}' % json.dumps(WCZORAJ),
            '{"rodzaj": "notka", "udane": true, "tekst": ""}',
            'to nie jest JSON',
        ]) + "\n", encoding="utf-8")
        stages.PAMIEC_NOTEK_PLIK.unlink()
        sprawdz("nieudana notka, lajk, pusty tekst i smiec NIE wchodza do pamieci",
                stages.pamiec_wystawionych() == [],
                stages.pamiec_wystawionych())
    finally:
        stages.PAMIEC_NOTEK_PLIK = stary_plik
        config.przywroc_katalog_danych(_zdjecie)
        config.PAMIEC_NOTEK = stare_okno

print()
print("=== 4d. SKROT CZYTA TYLKO PRZYROST DZIENNIKA ===")
# Dziennik rosnie bez konca: 29 notek to 7822 bajty samego tekstu, czyli ~270 B
# na notke. Przy trzech notkach dziennie sam ich udzial to ~3,6 MB po dziesieciu
# latach, a dziennik notuje takze komentarze, lajki, restacki i odpowiedzi.
# Czytanie calosci przy kazdej notce jest wiec bez przyszlosci.

with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    stary_plik = stages.PAMIEC_NOTEK_PLIK
    _zdjecie = config.uzyj_katalogu_danych(tmp)
    try:
        stages.PAMIEC_NOTEK_PLIK = tmp / "wystawione_notki.json"
        dziennik_z_notek(tmp, WYPELNIACZ[:10])
        stages.pamiec_wystawionych()
        skrot = json.loads(stages.PAMIEC_NOTEK_PLIK.read_text(encoding="utf-8"))
        rozmiar = (tmp / "dziennik.jsonl").stat().st_size
        sprawdz("skrot zapamietal, dokad doczytal", skrot["bajtow"] == rozmiar,
                (skrot["bajtow"], rozmiar))

        # KONTRDOWOD NA PRZYROSTOWOSC: wkladamy do skrotu odcisk, ktorego
        # w dzienniku NIE MA. Kod czytajacy caly dziennik od nowa by go zgubil.
        skrot["odciski"].append(["zmyslo", "odcisk", "ktory", "istni"])
        stages.PAMIEC_NOTEK_PLIK.write_text(json.dumps(skrot), encoding="utf-8")
        with open(tmp / "dziennik.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps({"rodzaj": "notka", "udane": True,
                                "tekst": WYPELNIACZ[11]}) + "\n")
        po = stages.pamiec_wystawionych()
        sprawdz("dopisana notka doszla do pamieci", len(po) == 12, len(po))
        sprawdz("KONTRDOWOD: zmyslony odcisk PRZETRWAL, czyli dziennik nie byl"
                " czytany od poczatku", frozenset(
                    ["zmyslo", "odcisk", "ktory", "istni"]) in po)

        # Urwana linia — dziennik dopisuje inny proces, czytanie moze trafic
        # w srodek zapisu. Polowa notki nie moze wpasc do pamieci jako odcisk.
        with open(tmp / "dziennik.jsonl", "a", encoding="utf-8") as f:
            f.write('{"rodzaj": "notka", "udane": true, "tekst": "urwana w po')
        sprawdz("urwana ostatnia linia nie wchodzi do pamieci",
                len(stages.pamiec_wystawionych()) == 12)

        # ROTACJA: inny plik pod ta sama nazwa. Bez tej kontroli odciski ze
        # starego dziennika zostalyby na wieki, blokujac tematy bez powodu.
        dziennik_z_notek(tmp, WYPELNIACZ[:3])
        po_rotacji = stages.pamiec_wystawionych()
        sprawdz("rotacja dziennika przelicza skrot od zera",
                len(po_rotacji) == 3, len(po_rotacji))
        sprawdz("KONTRDOWOD: bez tej kontroli zostaloby 12 starych odciskow",
                frozenset(["zmyslo", "odcisk", "ktory", "istni"]) not in po_rotacji)

        # Zmiana SPOSOBU liczenia rdzeni tez uniewaznia skrot — inaczej stare
        # odciski przestaja byc porownywalne z nowymi i pamiec klamie po cichu.
        stare_puste = stages._PUSTE_SLOWA
        try:
            stages._PUSTE_SLOWA = frozenset(list(stare_puste) + ["harbour"])
            sprawdz("inna lista pustych slow zmienia sygnature rdzeni",
                    stages._sygnatura_rdzeni() != json.loads(
                        stages.PAMIEC_NOTEK_PLIK.read_text(
                            encoding="utf-8"))["rdzenie"])
            odswiezone = stages.pamiec_wystawionych()
            sprawdz("i przebudowuje pamiec z dziennika", len(odswiezone) == 3,
                    len(odswiezone))
        finally:
            stages._PUSTE_SLOWA = stare_puste
    finally:
        stages.PAMIEC_NOTEK_PLIK = stary_plik
        config.przywroc_katalog_danych(_zdjecie)

print()
print("=== 4e. DZIEN SIE NIE ZAGLADZA ===")
# Do 25 sierpnia zderzenie calej puli konczylo dzien natychmiast. Przy pamieci
# bez konca to bedzie zdarzac sie czesciej: zmierzone q ~ 4e-5 na pare daje
# przy 10 000 zapamietanych notek okolo 35% szans, ze POJEDYNCZY material sie
# zderzy. Osiem faktow z puli to 0,35^8; z druga pula 0,35^16.

ZDERZONY = {"domain": "Cosmetics labelling", "fact": DZIS["fact"]}
SWIEZY_1 = {"domain": "Sealed enclosures",
            "fact": ("The tiny hole in the middle pane of a pressure panel is "
                     "a bleed hole that keeps the outer pane carrying the "
                     "pressure load during flight.")}
SWIEZY_2 = {"domain": "Restaurants",
            "fact": ("Under the tip credit, employers may pay tipped staff a "
                     "lower base wage whenever gratuities cover the difference.")}
PAMIEC_TESTOWA = [frozenset(stages._slowa(WCZORAJ))]

sprawdz("KONTRDOWOD: sama pula NIE daje sie wybrac (tu konczyl sie stary dzien)",
        stages.wybierz_material([dict(ZDERZONY)], [], PAMIEC_TESTOWA) is None)

oryg_stages = (stages.znajdz_ciekawostki, stages.note,
               stages.artykul_do_promocji, stages.pamiec_wystawionych)
wolania = []


def dzien_probny(nowe_fakty, ile):
    """Odpala `notki_dnia` bez modelu i bez dysku. Zwraca (notki, ile_szukan)."""
    wolania.clear()
    stages.artykul_do_promocji = lambda: None
    stages.pamiec_wystawionych = lambda: PAMIEC_TESTOWA
    stages.znajdz_ciekawostki = lambda conn, run_id, ile=8: (
        wolania.append("szukanie") or [dict(f) for f in nowe_fakty])
    # `**k` OD 2 WRZESNIA 2026: `note` dostalo parametr `etap`, bo notki pisza
    # dwaj pisarze na zmiane. Atrapa ma przyjmowac to, co przyjmuje oryginal —
    # inaczej test oblewa na ksztalcie wywolania, a nie na zachowaniu.
    stages.note = lambda conn, run_id, typ, material, link=None, note_form="PROSTA", **k: {
        "typ": typ, "material": material, "candidates": []}
    return stages.notki_dnia(None, 0, ciekawostki=[dict(ZDERZONY)], ile=ile), \
        len(wolania)


try:
    notki, szukan = dzien_probny([SWIEZY_1, SWIEZY_2], 2)
    sprawdz("cala pula zderzona -> agent DOBIERA material zamiast konczyc",
            len(notki) == 2, len(notki))
    sprawdz("i szukal DOKLADNIE RAZ, nie raz na notke", szukan == 1, szukan)
    sprawdz("notki stoja na SWIEZYM materiale, nie na zderzonym",
            all("Cosmetics" not in str(n["material"]) for n in notki), notki)

    # I nie zapetla sie: gdy dobrany material tez sie zderza, dzien konczy sie
    # krocej — po JEDNEJ dodatkowej probie, nie po nieskonczonej liczbie.
    notki2, szukan2 = dzien_probny([dict(ZDERZONY)], 2)
    sprawdz("gdy dobrany material TEZ sie zderza -> dzien konczy sie krocej",
            len(notki2) == 0, len(notki2))
    sprawdz("i nadal szukal dokladnie raz (brak petli)", szukan2 == 1, szukan2)
finally:
    (stages.znajdz_ciekawostki, stages.note, stages.artykul_do_promocji,
     stages.pamiec_wystawionych) = oryg_stages

print()
print("=== 4f. RECZNA EDYCJA DZIENNIKA NIE GUBI NOTKI ===")
# ZNALEZIONE PRZEZ ADWERSARZA, POTWIERDZONE POMIAREM. Skrot pamieci czytal
# tylko PRZYROST dziennika, a przed przebudowa sprawdzal trzy rzeczy: glowe
# pliku (najwyzej 4 kB), rozmiar i sygnature liczenia rdzeni.
#
# Przy 40 notkach dziennik ma 8,5 kB — czyli kontrola obejmowala POLOWE pliku.
# Przy 11 000 notek obejmowalaby 0,016%. Kazda zmiana poza glowa, ktora nie
# zmniejszyla pliku ponizej zapamietanego offsetu, przechodzila przez wszystkie
# trzy warunki, a `seek` ladowal W SRODKU WIERSZA. Ulamek wiersza wywalal
# `json.loads`, ktory jest cicho pomijany — wiec notka znikala z pamieci NA
# ZAWSZE, przy spokojnym logu. Wychodzi to na jaw dopiero w dniu, w ktorym ta
# notka wyjdzie drugi raz, czyli dokladnie wtedy, gdy juz jest za pozno.
#
# Czwarty warunek jest tani: bajt tuz przed offsetem MUSI byc koncem linii.
import json as _json

_kat = pathlib.Path(tempfile.mkdtemp())
_stary_plik = stages.PAMIEC_NOTEK_PLIK
_zdjecie_notek = config.uzyj_katalogu_danych(_kat)
stages.PAMIEC_NOTEK_PLIK = _kat / "wystawione_notki.json"
_dz = _kat / "dziennik.jsonl"


def _wpis(i, tekst):
    return _json.dumps({"rodzaj": "notka", "udane": True,
                        "kiedy": "2026-08-%02d" % (i % 28 + 1), "tekst": tekst},
                       ensure_ascii=False)


try:
    _linie = [_wpis(i, "Notka numer %d o innym temacie: %s widgets and %s"
                    % (i, i * 7, i * 13)) for i in range(40)]
    _linie[30] = _wpis(30, "Wind turbines shed ice by heating the blade root before dawn")
    _dz.write_text("\n".join(_linie) + "\n", encoding="utf-8")

    _p1 = stages.pamiec_wystawionych()
    sprawdz("pierwsze czytanie widzi wszystkie notki", len(_p1) == 40, len(_p1))
    sprawdz("i notka o turbinach w niej jest",
            any("turbin" in " ".join(sorted(o)) for o in _p1))

    # Wlasciciel skraca recznie wiersz 30, agent dopisuje dwie notki. Plik
    # znowu jest WIEKSZY niz zapamietany offset, wiec warunek „obciety" nie
    # zadziala, a zmiana lezy poza glowa.
    _linie[30] = _wpis(30, "Wind turbines shed ice by heating blade root")
    _linie.append(_wpis(41, "Zupelnie nowa notka alpha beta gamma delta"))
    _linie.append(_wpis(42, "I jeszcze jedna nowa notka epsilon zeta eta"))
    _dz.write_text("\n".join(_linie) + "\n", encoding="utf-8")

    _p2 = stages.pamiec_wystawionych()
    sprawdz("po recznej edycji pamiec ma WSZYSTKIE notki", len(_p2) == 42, len(_p2))
    sprawdz("i edytowana notka NIE zginela",
            any("turbin" in " ".join(sorted(o)) for o in _p2))

    # KONTRDOWOD: sprawdzenie musi realnie patrzec na bajt przed offsetem.
    # Podstawiamy skrot z offsetem, ktory lada w srodku wiersza — pamiec ma
    # to wykryc i przeliczyc od zera, a nie przyjac ulamek.
    _skrot = _json.loads(stages.PAMIEC_NOTEK_PLIK.read_text(encoding="utf-8"))
    _skrot["bajtow"] = max(1, int(_skrot.get("bajtow", 100)) - 17)
    stages.PAMIEC_NOTEK_PLIK.write_text(
        _json.dumps(_skrot, ensure_ascii=False), encoding="utf-8")
    _p3 = stages.pamiec_wystawionych()
    sprawdz("offset w srodku wiersza wymusza przeliczenie od zera",
            len(_p3) == 42, len(_p3))
finally:
    stages.PAMIEC_NOTEK_PLIK = _stary_plik
    config.przywroc_katalog_danych(_zdjecie_notek)

print()
print("=== 5. FAKT W PAMIECI ZUZYTYCH TO ZDANIE, NIE SLOWNIK ===")

oryg_plik = stages.ZUZYTE_FAKTY
stages.ZUZYTE_FAKTY = pathlib.Path(tempfile.mkdtemp()) / "z.json"
try:
    stages.zapisz_zuzyte([{"fact": "fakt ze slownika", "url": "http://x"}])
    stages.zapisz_zuzyte(["zwykle zdanie"])
    wczytane = stages.wczytaj_zuzyte()
    print("    w pliku: %s" % wczytane)
    sprawdz("slownik zapisany jako samo zdanie",
            "fakt ze slownika" in wczytane, wczytane)
    sprawdz("zdanie zapisane normalnie", "zwykle zdanie" in wczytane, wczytane)
    sprawdz("wszystko jest tekstem", all(isinstance(t, str) for t in wczytane))

    # KONTRDOWOD: to wlasnie wywalalo szukanie ciekawostek.
    try:
        stages._klucz_faktu({"fact": "x"})
        polecialo = False
    except AttributeError:
        polecialo = True
    sprawdz("slownik NADAL wywala _klucz_faktu (wiec musi byc odsiany wczesniej)",
            polecialo)

    # Plik zepsuty recznie — czytanie ma go posprzatac, nie paść.
    stages.ZUZYTE_FAKTY.write_text(
        '[{"fact": "ze slownika"}, "ze zdania", null, 5]', encoding="utf-8")
    w = stages.wczytaj_zuzyte()
    sprawdz("zepsuty plik sprzatany przy odczycie",
            w == ["ze slownika", "ze zdania", "5"], w)
    sprawdz("i nie wywala _klucz_faktu", all(
        isinstance(stages._klucz_faktu(t), str) for t in w))
finally:
    stages.ZUZYTE_FAKTY = oryg_plik

print()
print()
print("=== 6. OBSERWACJE ODWIESZONE — WYCOFANIE STALO NA ZLYM WNIOSKU ===")
# Obserwacje nie wykonaly sie ANI RAZU i przez tygodnie wygladalo to na blad
# kolejnosci blokow albo za waski budzet. Pierwsza diagnoza byla bledna:
# uchwyt PUBLIKACJI zamiast uchwytu CZLOWIEKA. Sprawdzone na zywym API — dla
# wszystkich pieciu hostow z historii oba uchwyty sa IDENTYCZNE.
#
# DRUGA DIAGNOZA TEZ BYLA BLEDNA i to ona kosztowala dziewiec dni. 2026-08-23
# zmierzono szesc profili i stwierdzono, ze Substack ZDJAL „Follow" ze stron
# profilowych — slowa „Follow" nie ma w ich HTML ani razu. POMIAR BYL
# PRAWDZIWY, WNIOSEK FALSZYWY: przycisk siedzi w menu pod kolkiem „...", ktore
# Substack rysuje DOPIERO PO KLIKNIECIU. W HTML zamknietej strony go nie ma
# i byc nie moze, wiec czytanie HTML-a nie moglo tego rozstrzygnac.
#
# Zmierzone ponownie 2026-09-01 na zywej sesji: menu oddaje „Follow" tam, gdzie
# nie obserwujemy, i „Unfollow" tam, gdzie obserwujemy. Pelny pomiar w
# `test_obserwowanie_przez_menu.py`.
#
# TA SEKCJA PILNOWALA WYCOFANIA I ZOSTAJE — ODWROCONA. Nie kasuje jej, bo
# to ona ma nie pozwolic, zeby zdolnosc wygasla po cichu drugi raz.

# WIDELKI PRZESUNIETE 1 WRZESNIA 2026, ale pytanie tej sekcji sie NIE ZMIENIA:
# ma pilnowac, zeby zdolnosc nie wygasla po cichu drugi raz. Zdolnosc zyje,
# dopoki stala jest niezerowa i norma dzienna dodatnia; sama wielkosc idzie
# teraz za skutkiem i jest uzasadniona przy `config.FOLLOW_MIESIECZNIE`.
sprawdz_nasze("norma obserwacji jest niezerowa i wezsza niz sprzed 1 wrzesnia",
        config.FOLLOW_MIESIECZNIE == (10, 16), config.FOLLOW_MIESIECZNIE)
sprawdz_nasze("subskrypcje sa teraz SZERSZE od obserwacji — to one konwertuja",
        config.SUBSKRYPCJE_MIESIECZNIE == (12, 20),
        config.SUBSKRYPCJE_MIESIECZNIE)
sprawdz("licznik zna rodzaj 'obserwacja'", "obserwacja" in config.normy_dzienne())
sprawdz("i jego norma dzienna jest DODATNIA",
        config.normy_dzienne()["obserwacja"] > 0,
        config.normy_dzienne()["obserwacja"])

# NAJWAZNIEJSZE: dzien bez ani jednej obserwacji ma sie liczyc jako 0 PROCENT,
# a nie jako „BRAK". Do 1 wrzesnia bylo odwrotnie i wlasnie to zamykalo sprawe:
# `norma.NIEWYKONALNE` zamienialo zero w kreske, a kreska nie budzi nikogo.
with tempfile.TemporaryDirectory() as tmp:
    _zdjecie = config.uzyj_katalogu_danych(pathlib.Path(tmp))
    try:
        (config.DATA_DIR / "dziennik.jsonl").write_text(
            '{"rodzaj": "lajk", "udane": true, "kiedy": "2999-01-01T00:00:00Z"}\n',
            encoding="utf-8")
        pods = stages.podsumowanie_dzialan(7)
    finally:
        config.przywroc_katalog_danych(_zdjecie)
    obs = pods.get("obserwacja", {})
    sprawdz("podsumowanie nadal sie liczy", isinstance(pods, dict))
    print("    obserwacja w podsumowaniu: %s" % (obs,))
    sprawdz("zero obserwacji to 0%, a NIE „brak” — inaczej nikt tego nie zauwazy",
            obs.get("realizacja") == 0, obs.get("realizacja"))

# KONTRDOWOD: gdyby stala wrocila do (0, 0), ta sama funkcja znowu oddalaby
# „brak" zamiast zera. Odtwarzamy to, zamiast opowiadac.
stara_stala = config.FOLLOW_MIESIECZNIE
config.FOLLOW_MIESIECZNIE = (0, 0)
try:
    with tempfile.TemporaryDirectory() as tmp:
        _zdjecie = config.uzyj_katalogu_danych(pathlib.Path(tmp))
        try:
            (config.DATA_DIR / "dziennik.jsonl").write_text(
                '{"rodzaj": "lajk", "udane": true,'
                ' "kiedy": "2999-01-01T00:00:00Z"}\n', encoding="utf-8")
            pods0 = stages.podsumowanie_dzialan(7)
        finally:
            config.przywroc_katalog_danych(_zdjecie)
finally:
    config.FOLLOW_MIESIECZNIE = stara_stala
print("    KONTRDOWOD (0,0): %s" % (pods0.get("obserwacja", {}),))
sprawdz("KONTRDOWOD: przy (0, 0) to samo zero czytalo sie jako „brak”",
        pods0.get("obserwacja", {}).get("realizacja") is None,
        pods0.get("obserwacja", {}).get("realizacja"))

# Blok w run.py ma NADAL istniec i nadal wolac obserwowanie — wycofanie bylo
# jedna stala, a nie wypruciem kodu, i wlasnie dzieki temu powrot kosztowal
# jedna liczbe.
zrodlo_run = pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8")
drzewo = ast.parse(zrodlo_run)
blok = [w for w in ast.walk(drzewo)
        if isinstance(w, ast.FunctionDef) and w.name == "obserwuj"]
sprawdz("blok obserwacji ISTNIEJE w kodzie", len(blok) == 1)
sprawdz("i wola obserwuj_profil, a nie zasubskrybuj",
        "obserwuj_profil" in {n.func.attr for n in ast.walk(blok[0])
                              if isinstance(n, ast.Call)
                              and isinstance(n.func, ast.Attribute)})
sprawdz("norma.NIEWYKONALNE nie ucisza juz zadnej pozycji",
        norma.NIEWYKONALNE == {}, norma.NIEWYKONALNE)
# KONTRDOWOD, ze to naprawde jedna stala: budzet dnia musi liczyc pozycje
# „follow" WLASNIE z FOLLOW_MIESIECZNIE. Gdyby liczyl ja skadinad, zmiana
# stalej niczego by nie odkrecila, a „wycofane" znaczyloby „zakopane".
zrodlo_stages = pathlib.Path("agent-v2/stages.py").read_text(encoding="utf-8")
budzet = [w for w in ast.walk(ast.parse(zrodlo_stages))
          if isinstance(w, ast.FunctionDef) and w.name == "budzet_dnia"]
stale_w_budzecie = {n.attr for n in ast.walk(budzet[0])
                    if isinstance(n, ast.Attribute)}
sprawdz("budzet dnia liczy follow z tej wlasnie stalej",
        "FOLLOW_MIESIECZNIE" in stale_w_budzecie)
sprawdz("KONTRDOWOD: subskrypcje maja SWOJA stala, wiec sa niezalezne",
        "SUBSKRYPCJE_MIESIECZNIE" in stale_w_budzecie)


print("=== PRODUKCJA ===")
zle = 0
for p in PILNOWANE:
    t = odcisk(p)
    ok = t == PRZED[str(p)]
    zle += 0 if ok else 1
    print("  %-24s %s" % (pathlib.Path(p).name, "bez zmian" if ok else "ZMIENIONA"))

print()
print("=== WYNIK: %s zdanych, %s oblanych%s ===" %
      (zdane, oblane, ", PRODUKCJA RUSZONA" if zle else ""))
sys.exit(1 if (oblane or zle) else 0)
