"""Test roznorodnosci notek: forma jako osobny wymiar i wybor otwarcia."""
import hashlib
import json
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import config   # noqa: E402
import wlasna_konfiguracja  # noqa: E402
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
             config.DATA_DIR / "promocja.json", config.DATA_DIR / "dziennik.jsonl"]
PRZED = {str(p): odcisk(p) for p in PILNOWANE}

print("=== 1. FORMA JEST OSOBNYM WYMIAREM ===")

sprawdz("kazda forma ma opis", set(config.NOTE_FORM_MIX) <= set(config.NOTE_FORMS),
        set(config.NOTE_FORM_MIX) - set(config.NOTE_FORMS))
sprawdz("form jest wiecej niz jedna", len(set(config.NOTE_FORM_MIX)) >= 5,
        len(set(config.NOTE_FORM_MIX)))
sprawdz("PROSTA nadal istnieje (dziala, nie usuwamy)",
        "PROSTA" in config.NOTE_FORM_MIX)
sprawdz("ale PROSTA to mniejszosc, nie regula",
        config.NOTE_FORM_MIX.count("PROSTA") <= 1,
        config.NOTE_FORM_MIX.count("PROSTA"))

print()
print("=== 2. FORMY NIE CHODZA W PARZE Z TYPAMI ===")

TYPY = list(config.NOTE_MIX_OTHER_DAY)
print("    typy dnia:  %s" % TYPY)


def _forma(dzien_roku, od, i):
    """DOKLADNIE ten wzor, ktorego uzywa `stages.notki_dnia`.

    Stara wersja tego testu liczyla `(od + i)`, czyli formule BEZ dryfu — wiec
    sprawdzala cos, czego kod nie robil, i przechodzila. Przez to nie zauwazyla,
    ze trzy z osmiu form sa nieosiagalne: `od` to liczba notek juz DZIS
    wystawionych, dochodzi najwyzej do pieciu i o polnocy wraca do zera, a form
    jest osiem. Audyt policzyl na 30 wystawionych notkach: PYTANIE, ODWROCENIE
    i LICZBA nie wyszly ANI RAZU.
    """
    return config.NOTE_FORM_MIX[(dzien_roku + od + i) % len(config.NOTE_FORM_MIX)]


pary = []
for od, ile in ((0, 2), (2, 2), (4, 1)):
    t = TYPY[od:od + ile]
    f = [_forma(237, od, i) for i in range(len(t))]
    for a, b in zip(t, f):
        pary.append((a, b))
    print("    przebieg od=%s: %s" % (od, list(zip(t, f))))

sprawdz_nasze("w ciagu dnia jest kilka roznych form",
        len({f for _, f in pary}) >= 4, {f for _, f in pary})
sprawdz("dzien ma tyle form co typow", len(pary) == len(TYPY), len(pary))

# KAZDA FORMA MUSI BYC OSIAGALNA. To jest sprawdzenie, ktorego brakowalo.
osiagalne = set()
pary_wszystkie = set()
for dzien in range(1, 30):
    for od, ile in ((0, 2), (2, 2), (4, 1)):
        for i, typ in enumerate(TYPY[od:od + ile]):
            f = _forma(dzien, od, i)
            osiagalne.add(f)
            pary_wszystkie.add((typ, f))
brakujace = sorted(set(config.NOTE_FORM_MIX) - osiagalne)
sprawdz("KAZDA forma wypada w ciagu miesiaca", not brakujace, brakujace)
sprawdz("i par typ-forma jest duzo wiecej niz typow",
        len(pary_wszystkie) >= len(TYPY) * 4, len(pary_wszystkie))

# KONTRDOWOD: stary wzor BEZ dryfu zostawialby czesc form nieosiagalna.
stare_osiagalne = {config.NOTE_FORM_MIX[(od + i) % len(config.NOTE_FORM_MIX)]
                   for od, ile in ((0, 2), (2, 2), (4, 1))
                   for i in range(ile)}
sprawdz("stary wzor NIE osiagal wszystkich form (test rozroznia)",
        set(config.NOTE_FORM_MIX) - stare_osiagalne,
        sorted(set(config.NOTE_FORM_MIX) - stare_osiagalne))

ciekawostki = [f for t, f in pary_wszystkie if t == "CIEKAWOSTKA"]
sprawdz("CIEKAWOSTKA nie zawsze ma te sama forme",
        len(set(ciekawostki)) > 1, ciekawostki)

print()
print("=== 3. PROMPT DOSTAJE FORME ===")

szablon = pathlib.Path("agent-v2/prompts/notka.md").read_text(encoding="utf-8")
sprawdz("prompt ma miejsce na nazwe formy", "{note_form}" in szablon)
sprawdz("prompt ma miejsce na opis formy", "{form_brief}" in szablon)
sprawdz("prompt kaze lamac linie", "Break the lines" in szablon)
sprawdz("prompt odradza otwieranie od 'The'",
        "definite article" in szablon)

# Szablon musi sie faktycznie sformatowac wszystkimi polami, ktore podaje kod.
try:
    gotowy = stages._prompt(
        "notka.md", language="English", min_words=config.NOTE_MIN_WORDS,
        max_words=config.NOTE_MAX_WORDS, note_type="CIEKAWOSTKA",
        type_brief=config.NOTE_TYPES["CIEKAWOSTKA"], note_form="LISTA",
        form_brief=config.NOTE_FORMS["LISTA"], evidence="{}",
        # Pole WYMAGANE od kiedy piszemy jeden wariant zamiast trzech: model
        # musi znac ostatnie otwarcia, bo nie ma juz konkurencji, z ktorej
        # kod moglby wybrac to nietrafione. Patrz test_jeden_wariant.
        ostatnie_otwarcia_json='["six", "washing"]')
    sprawdz("prompt sklada sie bez bledu", "LISTA" in gotowy)
    sprawdz("i niesie opis wybranej formy",
            "same word" in gotowy, gotowy[:0])
    sprawdz("JSON na koncu nadal jest poprawny (nawiasy nie zjedzone)",
            '{"note":' in gotowy)
except Exception as exc:
    sprawdz("prompt sklada sie bez bledu", False, "%s: %s" % (type(exc).__name__, exc))

print()
print("=== 4. WYBOR KANDYDATA Z INNYM OTWARCIEM ===")

kat = pathlib.Path(tempfile.mkdtemp())
_zdjecie = config.uzyj_katalogu_danych(kat)
try:
    (kat / "dziennik.jsonl").write_text("\n".join(json.dumps(x) for x in [
        {"kiedy": "2026-08-17T10:00:00+00:00", "rodzaj": "notka", "udane": True,
         "tekst": "The stop sign is the only octagonal traffic sign."},
        {"kiedy": "2026-08-17T11:00:00+00:00", "rodzaj": "notka", "udane": True,
         "tekst": "The hole in a pen cap is a safety vent."},
        {"kiedy": "2026-08-17T12:00:00+00:00", "rodzaj": "komentarz", "udane": True,
         "tekst": "Something else entirely here."},
    ]) + "\n", encoding="utf-8")

    otw = stages.ostatnie_otwarcia()
    print("    ostatnie otwarcia notek: %s" % otw)
    sprawdz("czyta otwarcia z dziennika", otw == ["the", "the"], otw)
    sprawdz("NIE liczy komentarzy jako notek", "something" not in otw, otw)

    zajete = set(otw)

    def powtarza(d):
        s = (d.get("note") or "").split()
        return bool(s) and s[0].strip("\"'.,").lower() in zajete

    kandydaci = [
        {"note": "The date on your milk carton is not a deadline."},
        {"note": "Fire hydrant caps are a code, not decoration."},
        {"note": "The four-digit PIN came from a kitchen table."},
    ]
    kandydaci.sort(key=powtarza)
    print("    po sortowaniu pierwszy: %r" % kandydaci[0]["note"][:40])
    sprawdz("na czolo idzie kandydat z INNYM otwarciem",
            kandydaci[0]["note"].startswith("Fire"), kandydaci[0]["note"][:30])
    sprawdz("powtarzajacy nie znika, tylko czeka",
            len(kandydaci) == 3, len(kandydaci))

    # Gdy WSZYSCY powtarzaja — nadal wystawiamy, bo notka jest lepsza niz jej brak.
    wszyscy = [{"note": "The one."}, {"note": "The two."}]
    wszyscy.sort(key=powtarza)
    sprawdz("gdy wszyscy powtarzaja, lista zostaje nietknieta",
            len(wszyscy) == 2 and wszyscy[0]["note"] == "The one.", wszyscy)

    # KONTRDOWOD: bez sortowania wyszedlby ten z powtorzonym otwarciem.
    sprawdz("STARY sposob wzialby 'The date...' (test rozroznia)",
            kandydaci[0]["note"] != "The date on your milk carton is not a deadline.")

    config.uzyj_katalogu_danych(kat / "nie-ma-mnie", utworz=False)
    sprawdz("brak dziennika nie wywala", stages.ostatnie_otwarcia() == [])
finally:
    config.przywroc_katalog_danych(_zdjecie)

print()
print("=== 5. CZY NASZE DOTYCHCZASOWE NOTKI BY TO ZLAPALY ===")

NASZE = ["American eggs must be", "American rules make eggs", "The hole in a pen",
         "An AM station can", "Every US paper bill", "The stop sign is",
         "In most US elevators", "Federal ADA rules require",
         "The four-digit ATM PIN", "US law forces eggs", "The date on your",
         "Unpopular truth about Substack"]
pierwsze = [t.split()[0].lower() for t in NASZE]
import collections  # noqa: E402
licz = collections.Counter(pierwsze)
print("    otwarcia dwunastu naszych notek: %s" % dict(licz.most_common(4)))
sprawdz("dane potwierdzaja problem: 'the' powtorzone >= 3 razy",
        licz["the"] >= 3, licz["the"])

print()
print("=== PRODUKCJA ===")
zle = 0
for p in PILNOWANE:
    t = odcisk(p)
    ok = t == PRZED[str(p)]
    zle += 0 if ok else 1
    print("  %-24s %s" % (pathlib.Path(p).name, "bez zmian" if ok else "ZMIENIONA"))

print()
print("=== KUPLET KORYGUJACY JEST DRUGIM KRYTERIUM, NIE BRAMKA ===")
# Recenzja zimnego czytelnika nazwala ruch „nie X. Y." tikiem konta.
#
# PIERWSZY POMIAR BYL ZLY I TO JEST TU NAJWAZNIEJSZE. Wykrywacz lapal wtedy 4
# z 30 notek, czyli 14%, i na tej liczbie oparlem decyzje „sortujemy zamiast
# odrzucac". Audyt policzyl trzecia postac tego samego ruchu — apozycje z
# przecinkiem, „X, not Y" — i znalazl ja w 12 notkach, przy czym ZBIORY SA
# ROZLACZNE. Razem 16 z 30, czyli 53%.
#
# Wykrywacz powstal PO 29 z 30 notek, wiec korpus, na ktorym go kalibrowalem,
# w ogole go nie testowal. Przyrzad zbudowany pod jeden przypadek mierzy
# wlasnie ten przypadek.
#
# Nadal sortujemy, nie odrzucamy, ale przy `NOTE_CANDIDATES = 1` sortowanie
# listy jednoelementowej niczego nie wybiera. Detektor pozostaje potrzebny do
# pokazania modelowi tego ruchu w ostatnich notkach.
sprawdz("dwa zdania: zaprzeczenie, potem poprawka",
        stages.kuplet_korygujacy(
            "Nothing about the answer changes. Only the queue does.") is True)
sprawdz("ten sam ruch w jednym zdaniu",
        stages.kuplet_korygujacy(
            "The number is not a measurement, it is a band.") is True)
sprawdz("wariant ze skroceniem",
        stages.kuplet_korygujacy(
            "That jar is not added information. It's the substitute.") is True)
# TRZECIA POSTAC — najczestsza, i przez pierwsza wersje niewidziana.
sprawdz("apozycja z przecinkiem: X, not Y",
        stages.kuplet_korygujacy(
            "It was a scheduling decision, not a rule.") is True)
sprawdz("apozycja w drugiej czesci zdania",
        stages.kuplet_korygujacy(
            "Standard gauge won because Parliament made it the law, not because "
            "it was technically superior.") is True)
# KONTRDOWOD: samo slowo "not" bez przecinka przed nim NIE jest tikiem —
# inaczej detektor lapalby kazde zdanie przeczace i sortowanie staloby sie
# losowe.
sprawdz("zwykle przeczenie bez apozycji nie jest tikiem",
        stages.kuplet_korygujacy(
            "The system does not publish its error rate anywhere.") is False)

# KONTRDOWOD: zdanie z zaprzeczeniem, ale BEZ poprawki, nie jest kupletem.
# Bez tego wykrywacz lapalby kazde zdanie przeczace i sortowanie stalo by sie
# losowe.
sprawdz("samo zaprzeczenie to nie kuplet",
        stages.kuplet_korygujacy(
            "You pay for sentences the model never shows you. That family "
            "models think in hidden reasoning tokens.") is False)
sprawdz("powtorzona fraza to tez nie kuplet",
        stages.kuplet_korygujacy(
            "Two years in, a misstatement cannot void the policy. Two years "
            "is the incontestability clause.") is False)
sprawdz("zwykla notka bez ruchu",
        stages.kuplet_korygujacy(
            "Same model, same prompt, four prices. Google halves the bill "
            "for off-peak.") is False)

# NAJWAZNIEJSZE: to ma SORTOWAC, a nie odrzucac. Notka z kupletem jest nadal
# lepsza niz brak notki — dokladnie ta sama zasada, co przy powtorzonym
# otwarciu. Sprawdzamy to na kodzie, nie na obietnicy.
_st = pathlib.Path("agent-v2/stages.py").read_text(encoding="utf-8")
sprawdz("kuplet uzyty w kluczu sortowania",
        "kuplet_korygujacy(d.get(" in _st)
_linie_z_kupletem = [l for l in _st.split("\n")
                     if "kuplet_korygujacy" in l and not l.strip().startswith("#")]
sprawdz("kuplet uzyty w trzech miejscach: definicja, sortowanie, komunikat",
        len(_linie_z_kupletem) == 3, len(_linie_z_kupletem))
sprawdz("i zadna z tych linii nie odrzuca notki",
        not any("safe_to_post" in l or "continue" in l for l in _linie_z_kupletem),
        _linie_z_kupletem)
sprawdz("otwarcie ma pierwszenstwo przed tikiem",
        _st.index("powtarza_otwarcie(d)") < _st.index("kuplet_korygujacy(d.get("))

print()
print("=== WYNIK: %s zdanych, %s oblanych%s ===" %
      (zdane, oblane, ", PRODUKCJA RUSZONA" if zle else ""))
sys.exit(1 if (oblane or zle) else 0)
