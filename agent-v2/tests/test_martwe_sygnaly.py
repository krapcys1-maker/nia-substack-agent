"""Wykrywacz martwych sygnalow: pol, ktore model wylicza, a kod wyrzuca.

TO NIE JEST TEST JEDNEJ USTERKI, tylko siec na cala ich klase.

Skaut liczyl siedem ocen — curiosity, source_quality, non_obvious, universality,
discussion_potential, visual_potential, originality — i NIE CZYTALA ICH ANI JEDNA
LINIA KODU. Trwalo to tygodniami. Placilismy za wyliczenie w kazdym przebiegu
i wyrzucalismy wynik, a jednoczesnie skarzylismy sie, ze tematy sa oklepane,
majac w reku nieuzywane pole `originality`.

Ta sama wada ma drugi wariant: STALA, KTORA WYGLADA JAK ZABEZPIECZENIE.
`MAX_KOMENTARZY_NA_PUBLIKACJE = 2` nie bylo egzekwowane nigdzie, a ja sam
powolalem sie na nie tego samego dnia jako na istniejacy limit. Martwa stala
jest GORSZA niz jej brak, bo czyta sie ja jak gwarancje.

Dlatego test szuka obu naraz i wymaga, zeby kazdy wyjatek byl WYMIENIONY
Z POWODEM. Dopisanie czegos do listy wyjatkow ma byc decyzja, nie odruchem.

CO JEST UPRAWNIONYM WYJATKIEM. Sa pola, ktorych kod nie czyta CELOWO: model
musi je napisac, zeby dobrze pomyslec. „Dlaczego akurat ten przedmiot",
„w czym te dwa mechanizmy sa te same" — odpowiedz nie jest nam potrzebna,
ale jej sformulowanie zmienia to, co model odda w polach, ktore czytamy.
To jest rusztowanie i zostaje. Roznica miedzy rusztowaniem a martwym polem
polega na tym, ze rusztowanie da sie uzasadnic jednym zdaniem — i tu jest
wymagane.
"""
import io
import pathlib
import tokenize
import re
import sys

sys.path.insert(0, "agent-v2")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import wlasna_konfiguracja  # noqa: E402

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


KOD_PY = list(pathlib.Path("agent-v2").glob("*.py"))
KOD = "\n".join(p.read_text(encoding="utf-8") for p in KOD_PY)
PROMPTY = sorted(pathlib.Path("agent-v2/prompts").glob("*.md"))

# --- RUSZTOWANIE: pola, ktorych kod NIE czyta i to jest zamierzone -----------
# Kazdy wpis wymaga powodu. Dopisanie tu czegokolwiek to decyzja.
RUSZTOWANIE = {
    "bibliotekarz.md": {
        "missing": "czego brakuje grupie — czytane przez czlowieka w logu",
        "why_it_travels": "zmusza do sprawdzenia, czy mechanizm NAPRAWDE jest ten sam",
    },
    "forma.md": {
        "belief": "model musi nazwac przekonanie WLASNYMI slowami, zanim znajdzie cytat — to wymusza scalanie",
        "first_stated": "kotwiczy przekonanie w tekscie, zeby nie dalo sie go wymyslic",
        "object": "wymusza konkret przy przylapaniu czytelnika",
        "supports": "wskazuje, ktore przekonanie wspiera zdanie — pilnuje, ze wsparcie nie jest przekonaniem",
    },
    "ciekawostki.md": {
        "control_url": "zmusza do ZNALEZIENIA dokumentu rzadzacego, nie samego wpisania daty; kod czyta control_date/verdict/fact, adres zostaje w zapisie do sprawdzenia recznego",
    },
    "grafika.md": {
        "why_this_scene": "zmusza do wyboru sceny Z TEKSTU, nie ilustracji tematu",
    },
    "mysl.md": {
        "words": "wlasna deklaracja dlugosci; prawdziwa liczy kod",
        "why_no_note": "wyjscie awaryjne dla pomyslu, ktory potrzebowal faktu — model ma NAZWAC brakujacy dowod zamiast go wymyslic; nikt tego nie czyta, bo notka i tak wtedy nie powstaje, ale sam obowiazek nazwania jest zapora",
    },
    "notka.md": {
        "fact_used": "model ma wskazac fakt, na ktorym stoi notka — zapora przed zmysleniem; MYSL tego pola NIE dostaje (patrz mysl.md), bo zapora przed zmyslaniem postawiona typowi bez faktow zaprasza do zmyslenia faktu",
        "source_url": "to samo, dla zrodla",
        "words": "wlasna deklaracja dlugosci; prawdziwa liczy kod",
    },
    "pisarz.md": {
        "numbers_used": "spis liczb uzytych w tekscie — bramka LICZBA_SPOZA_KORPUSU i tak liczy je sama",
    },
    "restack.md": {
        "mechanism_named": "zmusza do nazwania mechanizmu, zanim padnie decyzja o podaniu dalej",
    },
    "synteza.md": {
        "how_it_matches": "uzasadnienie paraleli — bez niego model dokleja dowolna dziedzine",
    },
    "warto_pisac.md": {
        "one_line_verdict": "podsumowanie dla czlowieka czytajacego uwagi",
        "the_situation": "wymusza konkret przy nierozstrzygnietym wyniku",
        "what_would_rescue_it": "podpowiedz dla wlasciciela, czego szukac przy DOLOZ",
    },
    "weryfikacja.md": {
        "what_the_source_says": "dowod za werdyktem — do przeczytania, gdy fakt zostaje obalony",
    },
    "wykonalnosc.md": {
        "parallels": "zmusza do UZASADNIENIA oceny RICH; sama ocena jest czytana",
    },
}

# --- STALE nieuzywane, ktore zostaja SWIADOMIE -------------------------------
STALE_ZOSTAJA = {
    "BEST_NOTE_HOURS": "zapis ustalen; nasze zrodla sie nie zgadzaja co do godzin",
    "WORST_NOTE_HOURS": "j.w.",
    "BEST_NOTE_DAYS": "j.w.",
    "WORST_NOTE_DAYS": "j.w.",
    "KANDYDATOW_NA_PRZEBIEG": "uzywane w promptcie ciekawostek przez podstawienie",
    "ODPOWIEDZI_POZA_LIMITEM": "prog opisowy, sprawdzany w tescie odpowiedzi",
    "OBSZARY_REWIRU": "czyta to `tests/test_szukanie_celow.py`, nie kod produkcyjny "
                      "— pilnuje, zeby pula hasel dotykala roznych stron niszy, "
                      "a nie dwudziestu wariantow jednego hasla",
    # ZNALEZIONE 2026-09-03, gdy skan przestal uznawac wczytanie i wzmianke
    # w komentarzu za uzycie. Cztery miejsca twierdzily, ze ta lista filtruje
    # cudze posty (`config.py`, `kreator.py`, `ARCHITECTURE.md`,
    # `CONFIGURATION_MAP.md`) — nie filtruje niczego. Wpis tutaj jest po to,
    # zeby nikt nie „naprawil" tego z powrotem na zapewnienie.
    "ZNAKI_NISZY": "RUBRYKA, NIE FILTR — czytaja ja `narzedzia/audyt.py`, "
                   "`narzedzia/kreator.py` i `tests/test_szukanie_celow.py`, "
                   "zeby sprawdzic, czy HASLA_SZUKANIA trzymaja sie tematu, "
                   "ktory operator sam opisal. O tym, czy KONKRETNY post jest "
                   "na temat, decyduje model wedlug `prompts/cele.md`",
}

print("=== 1. POLA MODELU, KTORYCH KOD NIE CZYTA ===")
niespodzianki = {}
for p in PROMPTY:
    tekst = p.read_text(encoding="utf-8")
    klucze = set(re.findall(r'"([a-z][a-z0-9_]{2,})"\s*:', tekst))
    martwe = []
    for k in sorted(klucze):
        if re.search(r'["\']%s["\']' % re.escape(k), KOD) or ("." + k) in KOD:
            continue
        if k in RUSZTOWANIE.get(p.name, {}):
            continue
        martwe.append(k)
    if martwe:
        niespodzianki[p.name] = martwe

for nazwa, pola in niespodzianki.items():
    print("    %-22s %s" % (nazwa, ", ".join(pola)))
sprawdz("zadne pole nie jest martwe bez powodu", not niespodzianki,
        niespodzianki)

ile_rusztowania = sum(len(v) for v in RUSZTOWANIE.values())
print("    (rusztowania z uzasadnieniem: %d pol w %d promptach)"
      % (ile_rusztowania, len(RUSZTOWANIE)))
sprawdz("kazde rusztowanie ma NIEPUSTY powod",
        all(len(str(r).split()) >= 4 for v in RUSZTOWANIE.values() for r in v.values()))

print()
print("=== 2. STALE, KTORYCH NIE UZYWA ZADEN KOD ===")
cfg_surowy = pathlib.Path("agent-v2/config.py").read_text(encoding="utf-8")


def bez_komentarzy(tekst: str) -> str:
    """WZMIANKA W PROZIE TO NIE UZYCIE.

    Regula „uzywana wewnatrz samego configu" liczyla wystapienia w SUROWYM
    tekscie, a w `config.py` prawie kazda stala ma nad soba akapit, ktory ja
    z nazwy wymienia — wiec jedno zdanie o stalej zwalnialo ja z pytania, czy
    ktokolwiek ja czyta. Tak przechodzila `ZNAKI_NISZY`.

    Zamazujemy komentarze spacjami, zeby uklad reszty zostal nietkniety.
    """
    wiersze = tekst.split(chr(10))
    try:
        strumien = tokenize.generate_tokens(io.StringIO(tekst).readline)
        for typ, _n, (w1, k1), (w2, k2), _l in strumien:
            if typ != tokenize.COMMENT:
                continue
            for nr in range(w1, w2 + 1):
                if nr - 1 >= len(wiersze):
                    break
                linia = wiersze[nr - 1]
                od = k1 if nr == w1 else 0
                do = k2 if nr == w2 else len(linia)
                wiersze[nr - 1] = linia[:od] + " " * max(0, do - od) + linia[do:]
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return tekst          # w razie watpliwosci nie oskarzamy
    return chr(10).join(wiersze)


# `cfg` ZOSTAJE SUROWY — czyta go reszta pliku, i to celowo: sa tu
# asercje szukajace w `config.py` ZDAN, nie kodu (naglowek bloku
# martwych stalych, zdanie „TYLKO ADNOTACJA, nie blokada").
# Oczyszczona wersja sluzy JEDNEJ regule ponizej.
cfg = cfg_surowy
cfg_kod = bez_komentarzy(cfg_surowy)
def bez_tablicy_pol(sciezka: pathlib.Path, tekst: str) -> str:
    """WCZYTANIE TO NIE UZYCIE — odejmujemy mape pol od dowodu.

    `konfiguracja.py` trzyma tablice `POLA`: „pole w TOML -> nazwa stalej".
    Kazda stala, ktora operator moze USTAWIC, jest tam wymieniona z nazwy,
    wiec dopoki tablica liczyla sie jako dowod uzycia, ten skan nie mogl
    zobaczyc pola PYTANEGO I PORZUCONEGO — a wlasnie tam siedzialy dwa bledy
    znalezione 2026-09-03: `KANALY_YOUTUBE` (pytane, zapisywane, nieczytane)
    i `ZNAKI_NISZY` (czytana wylacznie przez audyt, kreator i test, przy
    czterech miejscach twierdzacych, ze filtruje cudze posty).

    Plik, ktorego jedynym zadaniem jest „stale, ktorych nikt nie uzywa", nie
    widzial ani jednej z nich.
    """
    if sciezka.name != "konfiguracja.py":
        return tekst
    poczatek = tekst.find("POLA")
    if poczatek < 0:
        return tekst
    otwarcie = tekst.find("{", poczatek)
    if otwarcie < 0:
        return tekst
    glebokosc, i = 0, otwarcie
    while i < len(tekst):
        if tekst[i] == "{":
            glebokosc += 1
        elif tekst[i] == "}":
            glebokosc -= 1
            if glebokosc == 0:
                break
        i += 1
    return tekst[:otwarcie] + tekst[i + 1:]


reszta = "\n".join(
    bez_tablicy_pol(p, p.read_text(encoding="utf-8"))
    for p in KOD_PY if p.name != "config.py")
martwe_stale = []
for s in sorted(set(re.findall(r"^([A-Z][A-Z0-9_]{3,})\s*=", cfg, re.M))):
    if re.search(r"\b%s\b" % s, reszta):
        continue
    # WZMIANKA W PROZIE TO NIE UZYCIE — liczymy po tekscie bez komentarzy.
    # W `config.py` prawie kazda stala ma nad soba akapit, ktory ja z nazwy
    # wymienia, wiec jedno zdanie zwalnialo ja z pytania, czy ktos ja czyta.
    if len(re.findall(r"\b%s\b" % s, cfg_kod)) > 1:
        continue          # uzywana przez KOD samego configu
    if s in STALE_ZOSTAJA:
        continue
    martwe_stale.append(s)
print("    znalezione: %s" % (", ".join(martwe_stale) or "(brak)"))
sprawdz("zadna stala nie jest martwa bez powodu", not martwe_stale, martwe_stale)

print()
print("=== 3. USUNIETE 20 SIERPNIA — NIE MOGA WROCIC ===")
# Kazda z tych czterech udawala dzialajacy mechanizm.
for stala, czym_byla in (
        ("MAX_KOMENTARZY_NA_PUBLIKACJE", "limit, ktorego nikt nie egzekwowal"),
        ("NOTES_PER_DAY", "duplikat len(NOTE_MIX_OTHER_DAY)"),
        ("MAX_DZIALAN_NA_GODZINE", "ogranicznik tempa, ktory nie ograniczal"),
        ("FLAGGED_GATES", "lista czterech bramek, gdy jest ich szesnascie")):
    sprawdz("%-30s nie wrocilo (%s)" % (stala, czym_byla[:34]),
            not re.search(r"^%s\s*=" % stala, cfg, re.M))

print()
print("=== 4. ZASTEPCY USUNIETYCH NAPRAWDE DZIALAJA ===")
# Usuniecie limitu jest bezpieczne TYLKO wtedy, gdy istnieje ostrzejszy.
import config   # noqa: E402
kanal_src = pathlib.Path("agent-v2/kanal.py").read_text(encoding="utf-8")
sprawdz("limit u tej samej publikacji istnieje i jest czytany",
        "ODSTEP_DNI_NA_PUBLIKACJE" in kanal_src)
sprawdz("i jest OSTRZEJSZY niz usuniety (raz na kilka dni, nie 2 dziennie)",
        config.ODSTEP_DNI_NA_PUBLIKACJE >= 2, config.ODSTEP_DNI_NA_PUBLIKACJE)
sprawdz_nasze("liczbe notek nadal wyznacza NOTE_MIX_OTHER_DAY",
        len(config.NOTE_MIX_OTHER_DAY) == 5, len(config.NOTE_MIX_OTHER_DAY))
sprawdz("tempo nadal wyznaczaja ODSTEPY", bool(config.ODSTEPY))
sprawdz("zrodlem prawdy o bramkach jest gates.deterministic_floors",
        "def deterministic_floors" in
        pathlib.Path("agent-v2/gates.py").read_text(encoding="utf-8"))

print()
print("=== 5. GODZINY NOTEK: KAZDA STALA Z OSOBNA ===")
# TEN TEST PILNOWAL NIEPRAWDY. Sprawdzal tylko BEST_NOTE_HOURS, a potem
# potwierdzal, ze config OSTRZEGA o nieuzywanych stalych — nie sprawdzajac,
# czy to ostrzezenie jest prawdziwe dla KAZDEJ z nich. Nie bylo:
# `WORST_NOTE_HOURS` stalo w bloku "CZTERY PONIZSZE STALE NIE SA UZYWANE PRZEZ
# ZADNA LINIE KODU" (stale byly trzy) i jest EGZEKWOWANE przez
# `pora_na_publikacje` — miedzy 12:00 a 13:59 u czytelnikow agent nie wystawia
# ani notek, ani komentarzy. Kto uwierzylby komentarzowi i skasowal ta stala,
# dostalby NameError w funkcji wolanej na poczatku kazdego przebiegu dnia.
#
# Sprawdzamy wiec KAZDA stala osobno, w obie strony.
def _uzyta(nazwa):
    """Czy stala pada gdziekolwiek POZA wlasna definicja i komentarzami."""
    bez_komentarzy = re.sub(r"^\s*#.*$", "", cfg, flags=re.M)
    bez_definicji = re.sub(r"^" + nazwa + r"\s*=.*$", "", bez_komentarzy, flags=re.M)
    return (bool(re.search(r"\b" + nazwa + r"\b", bez_definicji))
            or bool(re.search(r"\b" + nazwa + r"\b", reszta)))


NAZWANE_JAKO_MARTWE = ("BEST_NOTE_HOURS", "BEST_NOTE_DAYS")
for nazwa in NAZWANE_JAKO_MARTWE:
    sprawdz("%s jest naprawde nieuzywana" % nazwa, not _uzyta(nazwa))
# KONTRDOWOD: stala EGZEKWOWANA nie moze stac w bloku "nieuzywane".
sprawdz("WORST_NOTE_HOURS jest uzywana", _uzyta("WORST_NOTE_HOURS"))
# OD 31 SIERPNIA 2026 NIE JEST JUZ BRAMKA, tylko adnotacja w logu. Powod:
# przebieg o 17:00 UTC to 13:00 ET, czyli dokladnie ta godzina — blokowal sie
# CODZIENNIE, jeden z pieciu, a tego dnia znalazl dziewiec celow wartych
# komentarza i nie wystawil zadnego. Sama regula stala przy tym na wlasnym
# zaprzeczeniu: `config.py` mowi wprost, ze nasze zrodla o godzinach sie nie
# zgadzaja.
#
# CEL TEGO SPRAWDZENIA SIE NIE ZMIENIL: stala ma byc UZYWANA, zeby nikt nie
# skasowal jej jako martwej i nie dostal NameError w funkcji wolanej na
# poczatku kazdego przebiegu.
sprawdz("i config mowi wprost, ze to juz nie blokada",
        "TYLKO ADNOTACJA, nie blokada" in cfg)
# Liczba w naglowku musi zgadzac sie z liczba stalych pod nim — bylo "CZTERY"
# przy trzech stalych, z czego jedna zywa.
naglowek = re.search(r"UWAGA: (\w+) PONIZSZE STALE NIE SA UZYWANE", cfg)
sprawdz("naglowek bloku martwych stalych istnieje", naglowek is not None)
if naglowek:
    LICZEBNIKI = {"JEDNA": 1, "DWIE": 2, "TRZY": 3, "CZTERY": 4, "PIEC": 5}
    sprawdz("i podaje tyle stalych, ile ich naprawde jest",
            LICZEBNIKI.get(naglowek.group(1)) == len(NAZWANE_JAKO_MARTWE),
            "%s wobec %d" % (naglowek.group(1), len(NAZWANE_JAKO_MARTWE)))

# ZACHOWANIE SPRAWDZONE NAPRAWDE, nie odczytane z komentarza.
from datetime import datetime, timezone   # noqa: E402
from zoneinfo import ZoneInfo             # noqa: E402

sys.path.insert(0, "agent-v2")
import config as _cfg                      # noqa: E402


def _wolno(godzina_et):
    t = datetime(2026, 8, 23, godzina_et, 30,
                 tzinfo=ZoneInfo(_cfg.PUBLISH_TIMEZONE)).astimezone(timezone.utc)
    return _cfg.pora_na_publikacje(t)[0]


# GODZINY OZNACZONE JAKO SLABSZE JUZ NIE BLOKUJA — ale nadal sa nazwane
# w powodzie, zeby dalo sie potem sprawdzic, czy notki z tych godzin naprawde
# wypadaja gorzej (`wystawione` w statystykach daje juz godzine).
for g in _cfg.WORST_NOTE_HOURS:
    sprawdz("o %02d:30 ET agent PUBLIKUJE" % g, _wolno(g))
    _powod = _cfg.pora_na_publikacje(
        datetime(2026, 8, 23, g, 30,
                 tzinfo=ZoneInfo(_cfg.PUBLISH_TIMEZONE)).astimezone(timezone.utc))[1]
    sprawdz("  ale %02d:00 ET jest odnotowana jako slabsza" % g,
            "slabsza" in _powod, _powod)

# PROG SNU ZOSTAJE BRAMKA. To inne twierdzenie i lepiej uzasadnione: tekst
# wrzucony, gdy publicznosc spi, traci pierwsze godziny widocznosci.
for g in (23, 1, 4):
    sprawdz("o %02d:30 ET agent nadal NIE publikuje" % g, not _wolno(g))
sprawdz("a godzine wczesniej owszem", _wolno(min(_cfg.WORST_NOTE_HOURS) - 1))
sprawdz("i godzine pozniej tez", _wolno(max(_cfg.WORST_NOTE_HOURS) + 1))
# Config jest lamany do 79 znakow, a zdanie przechodzi przez granice wiersza
# RAZEM ze znakiem komentarza — samo sklejenie bialych znakow zostawia w srodku
# „#". Wiec najpierw zdejmujemy znaki komentarza, potem sklejamy.
PLASKI_CFG = " ".join(re.sub(r"^\s*#\s?", "", cfg, flags=re.M).split())
sprawdz("i mowi, ze zrodla sie nie zgadzaja",
        "NASZE WLASNE ZRODLA SIE NIE ZGADZAJA" in PLASKI_CFG)
# OKNO_PUBLIKACJI_ET jest uzywane WEWNATRZ configu, przez `pora_na_publikacje`,
# i to wystarcza — inaczej niz godziny notek, ktorych nie czyta nikt.
sprawdz("okno publikacji NADAL dziala (to nie to samo co godziny)",
        len(re.findall(r"OKNO_PUBLIKACJI_ET", cfg)) > 1,
        len(re.findall(r"OKNO_PUBLIKACJI_ET", cfg)))

# „REALNIE WOLANE" MA ZNACZYC REALNIE WOLANE. Do 2 wrzesnia stalo tu
# `"pora_na_publikacje()" in reszta` — czyli grep, ktory przechodzi rowniez
# wtedy, gdy wywolanie stoi za `return` albo pod `if False:`, i oblewa przy
# samej zmianie wciecia. Pytamy wiec drzewo skladni (wzorzec z
# `test_waga_artykulu.py`): czy w OSIAGALNYM kodzie `run.dzien` jest to
# wywolanie i czy jego wynik jest do czegokolwiek uzyty.
import ast as _ast   # noqa: E402


def _zywe_wolania(funkcja, nazwa):
    """Wywolania `nazwa` w kodzie funkcji, do ktorego wykonanie MOZE dojsc.

    Instrukcje za `return`/`raise` i galezie `if False:` sa dla nas nieobecne —
    dokladnie ta roznica dzieli dzialajacy kod od zielonego grepa.
    """
    zywe, kolejka = [], [funkcja.body]
    while kolejka:
        wezel = kolejka.pop()
        if isinstance(wezel, list):
            for w in wezel:
                kolejka.append(w)
                if isinstance(w, (_ast.Return, _ast.Raise,
                                  _ast.Continue, _ast.Break)):
                    break
            continue
        if isinstance(wezel, _ast.If) and isinstance(wezel.test, _ast.Constant):
            kolejka.append(wezel.body if wezel.test.value else wezel.orelse)
            continue
        if isinstance(wezel, _ast.Call) and nazwa in (
                getattr(wezel.func, "attr", None),
                getattr(wezel.func, "id", None)):
            zywe.append(wezel)
        for _, wartosc in _ast.iter_fields(wezel):
            if isinstance(wartosc, list) and wartosc and isinstance(
                    wartosc[0], _ast.stmt):
                kolejka.append(wartosc)
            elif isinstance(wartosc, list):
                kolejka.extend(x for x in wartosc if isinstance(x, _ast.AST))
            elif isinstance(wartosc, _ast.AST):
                kolejka.append(wartosc)
    return zywe


_run_drzewo = _ast.parse(pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8"))
_dzien = next((f for f in _ast.walk(_run_drzewo)
               if isinstance(f, _ast.FunctionDef) and f.name == "dzien"), None)
sprawdz("przebieg dnia w ogole istnieje", _dzien is not None)
_pora = _zywe_wolania(_dzien, "pora_na_publikacje") if _dzien else []
sprawdz("i okno publikacji jest w nim WOLANE, w zywej galezi",
        len(_pora) >= 1, len(_pora))
# Wywolanie, ktorego wyniku nikt nie czyta, jest tym samym co brak wywolania —
# to caly temat tego pliku. Wynik ma byc przypisany i pozniej uzyty.
_uzyty = False
for _w in _ast.walk(_dzien) if _dzien else []:
    if not isinstance(_w, _ast.Assign) or _w.value not in _pora:
        continue
    _nazwy = {n.id for t in _w.targets for n in _ast.walk(t)
              if isinstance(n, _ast.Name)}
    _uzyty = _uzyty or any(
        isinstance(n, _ast.Name) and n.id in _nazwy
        and isinstance(n.ctx, _ast.Load)
        for n in _ast.walk(_dzien))
sprawdz("a jego wynik jest CZYTANY, nie wyrzucany", _uzyty)

print()
print("=== 6. RECENZENT: SKLADAMY Z DWOCH ZRODEL, NIE Z JEDNEGO ===")
# Recenzent oznacza kazde zdanie i OSOBNO powtarza nieoparte w liscie.
# Czytanie tylko listy znaczylo ufanie, ze model poprawnie przepisze wlasny
# wynik w drugie miejsce.
run_src = pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8")
sprawdz("czytamy takze sentences[].supported",
        's.get("supported") is not False' in run_src)
sprawdz("i dopisujemy pominiete do listy",
        "unsupported.append" in run_src)
sprawdz("i mowimy o tym w logu", "nie powtórzył w liście zbiorczej" in run_src)

print()
print("=== 7. STALA U WSZYSTKICH KANDYDATOW = ZERO INFORMACJI ===")
# Drugi wariant tej samej wady, i to ten, ktory przezyl dwie poprzednie
# naprawy. Pole JEST czytane, sortowanie z niego korzysta, test statyczny
# przechodzi — a sygnal ma u wszystkich kandydatow te sama wartosc, wiec
# nie ustawia nikogo przed nikim. Zlapane golym okiem w logu 2026-08-20:
# `watki na temat: [3, 3, 3, 3, 3, 3, 3, 3, 3, 3]`.
sys.path.insert(0, str(pathlib.Path("agent-v2").resolve()))
from stages import _stale_sygnaly

DZIESIEC_JAK_NA_ZYWO = [
    {"ile_watkow": 3, "ile_precedensow": i % 3, "nasycony": True,
     "zasieg": "AN_INDUSTRY" if i < 6 else "A_PLACE"}
    for i in range(10)
]
martwe = _stale_sygnaly(DZIESIEC_JAK_NA_ZYWO,
                        ("ile_watkow", "ile_precedensow", "nasycony", "zasieg"))
sprawdz("stale pole jest zglaszane", any(m.startswith("ile_watkow=") for m in martwe), martwe)
sprawdz("i stala prawda tez (nie tylko liczby)",
        any(m.startswith("nasycony=") for m in martwe), martwe)
# KONTRDOWOD: pola, ktore realnie roznicuja, NIE moga trafic na te liste,
# inaczej wykrywacz jest tylko halasem i przestaniemy go czytac.
sprawdz("pole rozroznajace NIE jest zglaszane",
        not any(m.startswith("ile_precedensow=") for m in martwe), martwe)
sprawdz("nawet gdy ma tylko dwie wartosci",
        not any(m.startswith("zasieg=") for m in martwe), martwe)

# HISTORYCZNE REGRESJE — dokladnie te trzy stale, ktore juz nas kosztowaly.
sprawdz("lapie samooceny zawsze 1.0",
        _stale_sygnaly([{"score": 1.0} for _ in range(8)], ("score",)) != [])
sprawdz("lapie watki zawsze szesc",
        _stale_sygnaly([{"ile_watkow": 6} for _ in range(10)], ("ile_watkow",)) != [])
sprawdz("lapie znane teksty zawsze trzy",
        _stale_sygnaly([{"ile_juz_napisano": 3} for _ in range(10)],
                       ("ile_juz_napisano",)) != [])

# Przy jednym kandydacie stalej nie da sie odroznic od wartosci — milczymy,
# zamiast oskarzac model o wyrownywanie na probce rozmiaru jeden.
sprawdz("jeden kandydat to nie dowod na nic",
        _stale_sygnaly([{"ile_watkow": 3}], ("ile_watkow",)) == [])
sprawdz("pusta lista tez nie", _stale_sygnaly([], ("ile_watkow",)) == [])
# Brak pola u wszystkich to tez stala (None) i tez ma byc widoczny: to znaczy,
# ze model w ogole go nie oddal, a kod dalej sie nim sortuje.
sprawdz("brak pola u wszystkich = stala None",
        _stale_sygnaly([{}, {}, {}], ("confidence",)) != [])

st_src = pathlib.Path("agent-v2/stages.py").read_text(encoding="utf-8")

# WYKRYWACZ SPRAWDZONY URUCHOMIENIEM, NIE GREPEM. Do 2 wrzesnia stalo tu
# `"_stale_sygnaly(topics" in st_src` plus dwa okna po 400 znakow od tego
# napisu. Trzy asercje po TRESCI ZRODLA — przechodzilyby takze wtedy, gdyby
# caly blok stal w martwej galezi, i oblewalyby przy zmianie nazwy zmiennej.
#
# Uruchamiamy wiec prawdziwego skauta na atrapie modelu (podmieniamy TYLKO
# `llm.call`, `llm.parse_json` zostaje prawdziwy) i patrzymy, czy wykrywacz
# naprawde sie odzywa i czy obejmuje watki oraz nasycenie.
import contextlib as _ctx   # noqa: E402
import io as _io            # noqa: E402
import json as _json        # noqa: E402

import korpus_kanalow as _kk   # noqa: E402
import stages as _stages       # noqa: E402

_TEMAT_WZORCOWY = {
    "title": "Example Article Eighteen in Nine Months",
    "question": "What did the custom inference chip change about who sets the "
                "price of a token?",
    "kind": "BROKEN_BELIEF", "scale": "AN_INDUSTRY", "zaczyn": "",
    "broken_belief": "Everyone assumes the chip changes what the model can do.",
    # TA SAMA WARTOSC U WSZYSTKICH — dokladnie to, co zlapal log z 2026-08-20:
    # `watki na temat: [3, 3, 3, ...]` i nasycenie u kazdego.
    "threads": [1, 2, 3], "already_written": [1, 2, 3], "precedents": [],
}


def _log_skauta(ile=4):
    """Prawdziwy `stages.scout` na atrapie. Oddaje to, co wypisal."""
    # `zasieg` CELOWO rozny u polowy tematow — to jest kontrdowod: pole, ktore
    # naprawde rozroznia, nie moze trafic do meldunku o martwych sygnalach.
    tematy = [dict(_TEMAT_WZORCOWY, title="Temat %d" % i,
                   scale="AN_INDUSTRY" if i % 2 else "A_PLACE")
              for i in range(ile)]
    _oryg = (_stages.recent_angles, _stages.pytania_dla_skauta,
             _stages.zaczyn_z_kanalow, _stages.llm.call, _kk.korpus_kanalow)
    _stages.recent_angles = lambda conn, limit=None: []
    _stages.pytania_dla_skauta = lambda ile=6: []
    _stages.zaczyn_z_kanalow = lambda ile=26: "(atrapa)"
    _kk.korpus_kanalow = lambda ile=200: []
    _stages.llm.call = lambda *a, **k: _json.dumps(
        {"topics": tematy, "ranking": {"least_written_about": [0]}})
    bufor = _io.StringIO()
    try:
        with _ctx.redirect_stdout(bufor):
            _stages.scout(None, 0, count=ile)
    finally:
        (_stages.recent_angles, _stages.pytania_dla_skauta,
         _stages.zaczyn_z_kanalow, _stages.llm.call,
         _kk.korpus_kanalow) = _oryg
    return bufor.getvalue()


_log = _log_skauta()
sprawdz("wykrywacz odzywa sie w PRAWDZIWYM przebiegu skauta",
        "MARTWE W TYM PRZEBIEGU" in _log, _log[-400:])
_martwe_linia = next((l for l in _log.splitlines()
                      if "MARTWE W TYM PRZEBIEGU" in l), "")
sprawdz("i obejmuje watki", "ile_watkow=3" in _martwe_linia, _martwe_linia)
sprawdz("i nasycenie", "nasycony=True" in _martwe_linia, _martwe_linia)
# KONTRDOWOD: pole, ktore realnie rozroznia, NIE moze trafic do tego meldunku —
# inaczej wykrywacz krzyczy zawsze i nikt go nie czyta. `zasieg` dostal wyzej
# dwie rozne wartosci, wiec ma sie w meldunku NIE pojawic.
sprawdz("a pole rozroznajace (zasieg) nie jest zglaszane",
        "zasieg=" not in _martwe_linia, _martwe_linia)

print()
print("=== 8. KOMUNIKAT NIE MOZE OBIECYWAC ODSIEWU, KTOREGO NIE MA ===")
# Kara nalozona na 100% kandydatow nie przesuwa nikogo. Log mowil
# „10 z 10 juz opisanych gdzie indziej — na koniec kolejki", czyli brzmial
# jak odsiew, a byl brakiem odsiewu.
sprawdz("odsiew ogloszony tylko gdy kogos faktycznie przesuwa",
        "if nasycone and len(nasycone) < len(topics):" in st_src)
sprawdz("a przy komplecie mowimy wprost, ze nic nie rozroznilo",
        "nasycenie nic nie rozroznilo" in st_src)

print()
print("=== 9. PARAMETR PRZEKAZYWANY I NIECZYTANY ===")
# Trzeci wariant tej samej wady, tym razem po stronie Pythona, nie modelu.
# `db.recent_domains` liczylo domeny ostatnich artykulow PRZY KAZDYM przebiegu,
# run.py przekazywalo je do `stages.discovery`, a cialo funkcji nie tykalo ich
# ani razu. Docstring w db.py obiecywal „wejscie do reguly roznorodnosci",
# ktorej nie bylo nigdzie w repozytorium. To nie moglo byc rusztowaniem —
# rusztowanie to pole, ktore MODEL musi napisac; tego parametru model nigdy
# nie widzial.
st = pathlib.Path("agent-v2/stages.py").read_text(encoding="utf-8")
sprawdz("recent_domains jest teraz czytany, nie tylko przyjmowany",
        st.count("recent_domains") >= 2, st.count("recent_domains"))
dysk = pathlib.Path("agent-v2/prompts/dyskoveria.md").read_text(encoding="utf-8")
sprawdz("i dociera do promptu dyskoverii", "{ostatnie_domeny}" in dysk)
# ZAKAZUJE nawyku, nie NAKAZUJE pozycji — inaczej po dziesieciu tekstach sama
# regula staje sie podpisem maszyny.
sprawdz("regula zakazuje nawyku, nie nakazuje zrodla",
        "out of habit" in dysk and "no other host carries it" in dysk)

print()
print("=== 10. KAZDY PLACEHOLDER PROMPTU MA SWOJ ARGUMENT ===")
# `_prompt` robi str.format. Placeholder bez argumentu to KeyError, ktory
# wybucha PO oplaceniu wczesniejszych etapow. Argument bez placeholdera jest
# cichszy i grozniejszy: nie wywala niczego, tylko po cichu nic nie robi —
# czyli usterka zostaje, a wyglada na naprawiona.
import re as _re
POJEDYNCZY = _re.compile(r"(?<!\{)\{([a-z_][a-z0-9_]*)\}(?!\})")
braki = []
# POLA WSPOLNE nie stoja przy zadnym wywolaniu — `stages._prompt` wstrzykuje
# je do KAZDEGO promptu z configu. Szukanie ich jako `pole=` w zrodle daje
# wiec dwadziescia piec falszywych brakow. Jedno zrodlo nazw:
# `stages.POLA_WSPOLNE`.
import stages as _stages   # noqa: E402
for plik in sorted(pathlib.Path("agent-v2/prompts").glob("*.md")):
    for pole in set(POJEDYNCZY.findall(plik.read_text(encoding="utf-8"))):
        if pole in _stages.POLA_WSPOLNE:
            continue
        if ("%s=" % pole) not in st:
            braki.append("%s -> %s" % (plik.name, pole))
sprawdz("zaden prompt nie ma placeholdera bez argumentu", not braki, braki)

# DRUGI KIERUNEK, KTOREGO TU BRAKOWALO. Sprawdzalem tylko placeholdery bez
# argumentu — czyli KeyError, ktory wybucha glosno. Odwrotnosc jest cichsza
# i wlasnie dlatego przezyla: argument PRZEKAZYWANY do promptu, ktory go
# nie uzywa, po prostu znika. Znalezione tak: `min_words` szlo do `pisarz.md`
# przy kazdym artykule i nie bylo w tym prompcie ani razu, wiec pisarz nigdy
# nie dostawal dolnej granicy dlugosci.
#
# Parsujemy WYWOLANIA `_prompt(...)`, zeby wiedziec, ktory argument idzie do
# ktorego pliku — sama obecnosc `min_words=` w stages.py nic nie znaczy, bo
# `notka.md` uzywa go poprawnie.
import ast as _ast   # noqa: E402

martwe_kwargi = []
for _w in _ast.walk(_ast.parse(st)):
    if not (isinstance(_w, _ast.Call) and getattr(_w.func, "id", "") == "_prompt"):
        continue
    if not (_w.args and isinstance(_w.args[0], _ast.Constant)
            and str(_w.args[0].value).endswith(".md")):
        continue
    nazwa = _w.args[0].value
    plik = pathlib.Path("agent-v2/prompts") / nazwa
    if not plik.exists():
        martwe_kwargi.append("%s -> pliku nie ma" % nazwa)
        continue
    tresc = plik.read_text(encoding="utf-8")
    for kw in _w.keywords:
        if kw.arg and ("{%s}" % kw.arg) not in tresc:
            martwe_kwargi.append("%s <- %s" % (nazwa, kw.arg))
sprawdz("zaden argument nie jest przekazywany do promptu, ktory go nie uzywa",
        not martwe_kwargi, martwe_kwargi)
# KONTRDOWOD: wykrywacz musi w ogole widziec wywolania i argumenty, inaczej
# przechodzi na pustym zbiorze i nie chroni przed niczym.
_ile_wywolan = sum(1 for _w in _ast.walk(_ast.parse(st))
                   if isinstance(_w, _ast.Call) and getattr(_w.func, "id", "") == "_prompt")
sprawdz("i widzi realne wywolania _prompt", _ile_wywolan >= 10, _ile_wywolan)

print()
print("=== 11. PISARZ NIE DOSTAJE DWOCH SPRZECZNYCH POLECEN ===")
# Oba zdania napisano, zeby naprawic TE SAMA awarie — artykul, ktory spedzil
# trzecia czesc dlugosci na tym, czego dowody nie mowia — tylko z przeciwnych
# stron: „zmiesc granice w jeden akapit" kontra „nigdy ich nie zbieraj".
# Model dostawal oba naraz.
pisarz = pathlib.Path("agent-v2/prompts/pisarz.md").read_text(encoding="utf-8")
# ZGODNOSC, NIE BRZMIENIE. Rano zapisalem tu asercje na konkretne zdanie
# i zabetonowala ona bledne rozstrzygniecie: przeczytalem dwie sprzeczne reguly
# i przestawilem te, ktora stala po stronie WIEKSZOSCI. Akapit granic jest
# zalozony w PIECIU miejscach — regula „Say the limits once", cala regula
# o pierwszym zdaniu TEGO akapitu z przykladami, zakaz „do not expand the
# limits paragraph", pole schematu `limits_paragraph_present` czytane
# w run.py, oraz bramka `gates.zapowiedziany_akapit_granic`, ktora bada
# pierwsze zdanie tego akapitu i bez niego nie ma sensu.
#
# Wiec test pyta teraz o to, co naprawde ma byc prawda: zadne zdanie promptu
# nie zakazuje akapitu, ktory piec innych miejsc zaklada.
sprawdz("prompt zamawia JEDEN akapit granic",
        "One paragraph, and only one." in pisarz
        and "Say the limits once" in pisarz)
sprawdz("i rzadzi jego POLOZENIEM, nie istnieniem",
        "Put that paragraph where the gap opens" in pisarz)
sprawdz("zadne zdanie nie zakazuje zbierania granic",
        "Never collect them." not in pisarz
        and "Put each unknown where it arises, alone." not in pisarz)
sprawdz("zakaz rozdymania nadal zaklada, ze akapit istnieje",
        "expand the limits paragraph" in pisarz)
sprawdz("schemat nadal pyta o obecnosc akapitu",
        "limits_paragraph_present" in pisarz)
# Kotwica dlugosci ma sie skalowac — inaczej pracuje przeciw DLUGOSC_WG_GLEBOKOSCI.
sprawdz("kotwica dlugosci jest polem, nie wpisana na sztywno",
        "{kotwica_dlugosci}" in pisarz and "1048 and 1101" not in pisarz)
sprawdz("i pisarz dostaje dolna granice", "{min_words}" in pisarz)
import config as _c2   # noqa: E402
sprawdz("kazdy poziom glebokosci ma wlasna kotwice",
        len({_c2.kotwica_dlugosci(g) for g in ("RICH", "SINGLE", "THIN")}) == 3)
# ASERCJA PYTA O WLASNOSC, NIE O LICZBE. Stalo tu `"1048" in ...` — czyli
# dokladna dlugosc jednego OPUBLIKOWANEGO artykulu, wpisana w test. Test
# pilnujacy tego, ze kotwica powoluje sie na dwa przyjete teksty, nie
# potrzebuje ich dlugosci co do slowa; potrzebowal tylko czegos, co da sie
# sprawdzic — a dlugosc byla pod reka. Przy czyszczeniu tozsamosci taka
# liczba jest sladem, ktorego nikt nie szuka.
_rich = _c2.kotwica_dlugosci("RICH")
sprawdz("kotwica RICH nadal powoluje sie na dwa przyjete teksty",
        "two" in _rich and "thousand" in _rich, _rich)
sprawdz("a kotwica THIN mowi, ze krotko jest wlasciwie",
        "shortest form" in _c2.kotwica_dlugosci("THIN"))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
