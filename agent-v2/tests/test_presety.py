# -*- coding: utf-8 -*-
"""Kartridz da sie podlaczyc, odlaczyc i NIE przenosi niczego z poprzedniego.

## Po co ten plik istnieje

Audyt z 5 wrzesnia 2026 (`analizy/2026-09-05-czystosc-presety/RAPORT.md`)
wykonal 24 proby na zastanym kodzie. Kazda sekcja ponizej odpowiada jednej
z nich i ma przechodzic DOPIERO po naprawie:

  T02  preset B po presecie A dziedziczyl kanaly, przyklady, pisarza i pytanie
  T03  zla rola modelu zostawiala juz zmieniona nisze
  T04  miks jednego typu dawal zwykly dzien 1, dzien artykulu 5
  T05  ujemne komentarze, 1,5 przebiegu, godzina 98 i dzien 99 przechodzily
  T06  walidator list przykladow odrzucal wlasny wynik
  T08  nowa linia w napisie dawala niepoprawny TOML
  T11  stan dziedziny wracal dla innego pytania
  T13  cache etapu bez odcisku oddawal stare tematy
  T15  rola `obraz` zmieniona, `IMAGE_MODEL` nie
  T22  oczekujacy artykul innej instancji byl wystawiany
  C1   brak konfiguracji przywracal wbudowany temat zamiast zatrzymac bota
  C2   linia redakcyjna i okladka jednej publikacji byly wpisane w silnik
  C4   styl byl wspolnym zestawem plikow o stalych nazwach
  W2   liczba przebiegow i dzien artykulu nie wchodzily do zegara
  W4   sygnaly (kanaly) i dowody (dokumenty) mialy jedno zrodlo: YouTube

Kazda sekcja ma KONTRDOWOD: pokazuje, ze asercja umie oblac — inaczej test
przechodzilby takze nad kodem sprzed naprawy.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_presety.py
"""
import ast
import json
import pathlib
import sys
import tempfile
import types

sys.path.insert(0, "agent-v2/tests")
import wlasna_konfiguracja  # noqa: E402

wlasna_konfiguracja.pomin_gdy_bez_tomllib("czy kartridze podlaczaja sie i odlaczaja czysto")

sys.path.insert(0, "agent-v2")
sys.path.append("narzedzia")
import config          # noqa: E402
import konfiguracja    # noqa: E402
import preset          # noqa: E402

KORZEN = pathlib.Path(".").resolve()
AGENT = KORZEN / "agent-v2"
KARTRIDZ_AI = KORZEN / "presety" / "ai"
SZABLON = KORZEN / "presety" / preset.NAZWA_SZABLONU

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


# NEUTRALNA BAZA SILNIKA — zdjecie zrobione przez `config.py` ZANIM wczytal
# cokolwiek (takze stary `konfiguracja.toml` operatora, ktory darmowy test
# nadal czyta). To ta sama baza, od ktorej silnik kompiluje kazdy kartridz.
BAZA = config.DOMYSLNE_SILNIKA

# Minimalny kartridz jednoplikowy: komplet pol wymaganych, reguly strukturalne
# spelnione, profile z silnika. Wszystko inne dostaje z reszty.
MINIMUM = """
[preset]
nazwa = "%(nazwa)s"
schema = 1

[konto]
uchwyt = "probny-%(nazwa)s"
nazwa_marki = "Probna %(nazwa)s"

[temat]
nisza = "%(nisza)s"
kat_redakcyjny = "what the record says."
jezyk = "English"
znaki_niszy = ["probn", "test"]
hasla_szukania = ["probna a", "probna b", "probna c", "probna d", "probna e",
    "probna f", "probna g", "probna h", "probna i", "probna j", "probna k",
    "probna l", "probna m", "probna n", "probna o", "test p"]
dziedziny = ["d1", "d2", "d3", "d4", "d5", "d6", "d7", "d8"]

[styl]
profil_pozytywny = "repo:style-profiles/ARTICLE_STYLE_PROFILE_V1.md"
profil_negatywny = "repo:style-profiles/ARTICLE_NEGATIVE_STYLE_PROFILE_V1.md"
wymagaj_korpusu = false
%(reszta)s
"""


def tekst(nazwa: str, nisza: str = "probna nisza", reszta: str = "") -> str:
    return MINIMUM % {"nazwa": nazwa, "nisza": nisza, "reszta": reszta}


def wczytaj(nazwa: str, nisza: str = "probna nisza", reszta: str = "") -> preset.Preset:
    return preset.wczytaj_tekst(tekst(nazwa, nisza, reszta), nazwa + ".toml")


def oblewa(fabryka):
    """Komunikat bledu albo None."""
    try:
        fabryka()
        return None
    except (preset.BladPresetu, preset.BrakPresetu, konfiguracja.BledKonfiguracji) as exc:
        return str(exc)


def dokument(sekcje: str):
    """Preset z DOWOLNYMI sekcjami (bez MINIMUM) przymierzony na kopii."""
    p = preset.proba_konfiguracji(config, BAZA)
    preset.zastosuj(preset.wczytaj_tekst('[preset]\nnazwa = "n"\n' + sekcje, "n.toml"), p, BAZA)
    return p


def notki(reszta):
    """MINIMUM plus `reszta`, przymierzone na kopii."""
    p = preset.proba_konfiguracji(config, BAZA)
    preset.zastosuj(wczytaj("n", reszta=reszta), p, BAZA)
    return p


def zwykla(x):
    return preset._kanoniczne(x)


# ============================================================ 1. SILNIK PUSTY
print("=== 1. SILNIK NIE MA TEMATU; KARTRIDZ `ai` GO MA (C1, C2) ===")
for nazwa in ("NISZA", "KAT_REDAKCYJNY", "ZNAKI_NISZY", "HASLA_SZUKANIA",
              "DZIEDZINY_CIEKAWOSTEK", "W_TYM_MIESIACU", "KANALY_YOUTUBE", "KANALY_RSS",
              "DOMENY_PREFEROWANE", "PRESET_BLOKI", "STYL_OPIS"):
    sprawdz("silnik: %s pusta" % nazwa, not BAZA.get(nazwa), BAZA.get(nazwa))
sprawdz("kartridz ai wczytuje sie z katalogu",
        oblewa(lambda: preset.wczytaj(KARTRIDZ_AI)) is None)
ai = preset.wczytaj(KARTRIDZ_AI)
sprawdz("kartridz zna swoj katalog", ai.katalog == KARTRIDZ_AI.resolve(), ai.katalog)
sprawdz("kartridz niesie wszystkie bloki promptow", set(ai.bloki) == set(preset.BLOKI),
        sorted(set(preset.BLOKI) - set(ai.bloki)))
bledy, uwagi = preset.sprawdz(ai, config, BAZA, srodowisko={})
sprawdz("kartridz ai przechodzi sprawdzenie bez bledow", not bledy, bledy)
a, b = preset.wczytaj(KARTRIDZ_AI), preset.wczytaj(KARTRIDZ_AI)
sprawdz("ten sam kartridz, ten sam odcisk", a.odcisk == b.odcisk)
sprawdz("szablon NIE wczytuje sie (placeholder w nazwie) — nie da sie go podlaczyc",
        "<<" in (oblewa(lambda: preset.wczytaj(SZABLON)) or ""),
        oblewa(lambda: preset.wczytaj(SZABLON)))
# ODCISK OBEJMUJE BLOKI: zmiana samego pliku w prompty/ zmienia odcisk.
sprawdz("odcisk zalezy od blokow",
        preset.odcisk(ai.pola, ai.schema, ai.bloki) != preset.odcisk(ai.pola, ai.schema, {}))
# ROUND-TRIP pol: eksport -> wczytanie -> te same pola (scenariusz 12).
znowu = preset.wczytaj_tekst(preset.eksportuj(ai), "ai.toml")
sprawdz("eksport i ponowny import daja te same pola",
        zwykla(znowu.pola) == zwykla(ai.pola))
# KONTRDOWOD: zmiana jednego pola zmienia odcisk.
sprawdz("inne pole -> inny odcisk",
        wczytaj("odcisk-a").odcisk != wczytaj("odcisk-a", nisza="inna nisza").odcisk)
# NOWA LINIA W NAPISIE (T08): eksport musi dac czytelny TOML.
_wiel = wczytaj("wielowiersz", reszta='opis = """linia jedna\nlinia druga"""\n')
_znowu = preset.wczytaj_tekst(preset.eksportuj(_wiel), "wielowiersz.toml")
sprawdz("opis stylu z nowa linia przezywa eksport i import",
        _znowu.pola.get("styl.opis") == "linia jedna\nlinia druga",
        _znowu.pola.get("styl.opis"))

# ========================================================== 2. NAGLOWEK
print()
print("=== 2. NAGLOWEK [preset] I POLA WYMAGANE ===")
sprawdz("plik bez [preset] jest odrzucany",
        "sekcji [preset]" in (oblewa(lambda: preset.wczytaj_tekst(
            '[konto]\nuchwyt = "x"\n', "bez.toml")) or ""))
sprawdz("nieznane pole naglowka jest bledem",
        "spoza listy" in (oblewa(lambda: preset.wczytaj_tekst(
            '[preset]\nnazwa = "x"\nkolor = "zielony"\n', "z.toml")) or ""))
sprawdz("nazwa z wielka litera/spacja jest bledem",
        "nazwa" in (oblewa(lambda: preset.wczytaj_tekst(
            '[preset]\nnazwa = "Moj Preset"\n', "z.toml")) or ""))
sprawdz("inna wersja schematu jest bledem",
        "schema" in (oblewa(lambda: preset.wczytaj_tekst(
            '[preset]\nnazwa = "x"\nschema = 2\n', "z.toml")) or ""))
sprawdz("nieznane pole konfiguracji nadal jest bledem (te same reguly co loader)",
        "nieznane pola" in (oblewa(lambda: preset.wczytaj_tekst(
            '[preset]\nnazwa = "x"\n[temat]\nniszaa = "x"\n', "z.toml")) or ""))
_goly = preset.wczytaj_tekst('[preset]\nnazwa = "goly"\n', "goly.toml")
_bledy_g, _ = preset.sprawdz(_goly, config, BAZA, srodowisko={})
sprawdz("kartridz bez tematu NIE przechodzi: silnik nie ma dla niego wartosci",
        any("wymaganych" in b for b in _bledy_g), _bledy_g)
_ze_znacznikiem = preset.wczytaj_tekst(tekst("zn").replace('nisza = "probna nisza"',
                                                            'nisza = "<<uzupelnij>>"'), "zn.toml")
_bledy_z, _ = preset.sprawdz(_ze_znacznikiem, config, BAZA, srodowisko={})
sprawdz("znacznik <<...>> w polu zatrzymuje sprawdzenie",
        any("<<" in b for b in _bledy_z), _bledy_z)

# ====================================================== 3. IZOLACJA A -> B
print()
print("=== 3. KARTRIDZ B PO KARTRIDZU A == B NA CZYSTYM SILNIKU (T02) ===")
A = wczytaj("a", nisza="nisza A", reszta="""opis = "glos A"

[temat.przyklady]
kanon = ["kanon A"]

[stan_dziedziny]
o_co_pytac = "pytanie A"

[zrodla]
kanaly_youtube = { "Kanal A" = "UCaaaaaaaaaaaaaaaaaaaaaa" }
kanaly_rss = { "Blog A" = "https://a.example/feed.xml" }
domeny_preferowane = ["a.example"]

[modele]
role = { write = "deepseek-v4-pro" }
""")
B = wczytaj("b", nisza="nisza B")

po_a = preset.proba_konfiguracji(config, BAZA)
preset.zastosuj(A, po_a, BAZA)
sprawdz("A ustawil kanaly", "Kanal A" in po_a.KANALY_YOUTUBE and "Blog A" in po_a.KANALY_RSS)
sprawdz("A ustawil pisarza", po_a.MODEL_FOR["write"] == "deepseek-v4-pro")
sprawdz("A ustawil przyklad", po_a.PRZYKLADY_NISZY["kanon"] == ("kanon A",))
sprawdz("A ustawil pytanie", po_a.STAN_DZIEDZINY_PYTANIE == "pytanie A")
preset.zastosuj(B, po_a, BAZA)
czysty = preset.proba_konfiguracji(config, BAZA)
preset.zastosuj(B, czysty, BAZA)
sprawdz("po B nie ma kanalow A", not po_a.KANALY_YOUTUBE and not po_a.KANALY_RSS)
sprawdz("po B pisarz wraca do silnika", po_a.MODEL_FOR["write"] == BAZA["MODEL_FOR"]["write"])
sprawdz("po B przyklad A znika", "kanon A" not in po_a.PRZYKLADY_NISZY.get("kanon", ()))
sprawdz("po B pytanie A znika", po_a.STAN_DZIEDZINY_PYTANIE != "pytanie A")
rozne = [n for n in konfiguracja.STALE_KONTA
         if zwykla(getattr(po_a, n, None)) != zwykla(getattr(czysty, n, None))]
sprawdz("KAZDA stala konta jest taka sama po A->B i na czystym silniku", not rozne, rozne)
sprawdz("pola kartridza A nie zostaly zmienione przez zastosowanie",
        A.pola["zrodla.kanaly_youtube"] == {"Kanal A": "UCaaaaaaaaaaaaaaaaaaaaaa"})
# KONTRDOWOD: bez przywrocenia bazy stara semantyka NAKLADA i roznica jest.
naklad = preset.proba_konfiguracji(config, BAZA)
konfiguracja.zastosuj(A.pola, naklad)
konfiguracja.zastosuj(B.pola, naklad)
sprawdz("kontrdowod: samo nakladanie zostawia kanaly A", "Kanal A" in naklad.KANALY_YOUTUBE,
        naklad.KANALY_YOUTUBE)

# ================================================== 4. BLOKI Z KATALOGU
print()
print("=== 4. BLOKI PROMPTOW Z KARTRIDZA, ZDANIA ZASTEPCZE BEZ NIEGO (C2) ===")
import stages  # noqa: E402

_stare_bloki = dict(config.PRESET_BLOKI)
try:
    config.PRESET_BLOKI.clear()
    pola = stages._pola_wspolne()
    sprawdz("bez kartridza kazdy blok to jawne zdanie zastepcze",
            all(pola[n] == stages._ZASTEPCZE_BLOKI[n] for n in preset.BLOKI if n != "oswiadczenie"))
    sprawdz("zastepczy blok okladki jest neutralny (bez palety jednej marki)",
            "no text" in pola["okladka"] and "grey" not in pola["okladka"].lower())
    config.PRESET_BLOKI.update(ai.bloki)
    pola = stages._pola_wspolne()
    sprawdz("z kartridzem blok linii redakcyjnej idzie do pol wspolnych",
            pola["linia_redakcyjna"] == ai.bloki["linia_redakcyjna"])
    sprawdz("naglowek pliku bloku (przed ---) NIE idzie do promptu",
            "Tekst przed" not in pola["linia_redakcyjna"])
    sprawdz("blok okladki z kartridza wchodzi do briefu grafiki",
            "{okladka}" in (config.PROMPTS_DIR / "grafika.md").read_text(encoding="utf-8")
            and pola["okladka"] == ai.bloki["okladka"])
    import browser  # noqa: E402
    sprawdz("oswiadczenie o autorstwie bierze sie z kartridza",
            browser.tresc_oswiadczenia() == " ".join(ai.bloki["oswiadczenie"].split()))
finally:
    config.PRESET_BLOKI.clear()
    config.PRESET_BLOKI.update(_stare_bloki)
for nazwa, plik in (("linia_redakcyjna", "skaut.md"), ("linia_redakcyjna", "ciekawostki.md"),
                    ("linia_redakcyjna", "warto_pisac.md"), ("linia_redakcyjna", "bank.md"),
                    ("glos_artykulu", "pisarz.md"), ("glos_notki", "notka.md"),
                    ("glos_notki", "mysl.md"), ("glos_komentarza", "komentarz.md"),
                    ("glos_komentarza", "odpowiedz.md"), ("glos_komentarza", "restack.md"),
                    ("kogo_szukamy", "cele.md"), ("domeny_preferowane", "dyskoveria.md")):
    sprawdz("%s niesie {%s}" % (plik, nazwa),
            "{%s}" % nazwa in (config.PROMPTS_DIR / plik).read_text(encoding="utf-8"))
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    kat = pathlib.Path(tmp) / "zly"
    (kat / "prompty").mkdir(parents=True)
    (kat / "prompty" / "glos_wszystkiego.md").write_text("x", encoding="utf-8")
    (kat / "preset.toml").write_text(tekst("zly"), encoding="utf-8")
    sprawdz("nieznany plik w prompty/ zatrzymuje wczytanie",
            "nieznany blok" in (oblewa(lambda: preset.wczytaj(kat)) or ""))

# ====================================================== 5. JEDEN SLOT
print()
print("=== 5. LICZBA NOTEK MA JEDNO ZNACZENIE (T04) ===")
p1 = notki('[wolumeny]\nnotki_dziennie = 1\n[publikowanie]\nmiks_notek = ["CIEKAWOSTKA"]\n')
sprawdz("1 slot: zwykly dzien ma 1 notke", len(p1.NOTE_MIX_OTHER_DAY) == 1, p1.NOTE_MIX_OTHER_DAY)
sprawdz("1 slot: dzien artykulu TEZ ma 1 notke (promujaca)",
        p1.NOTE_MIX_ARTICLE_DAY == ("ARTYKUL",), p1.NOTE_MIX_ARTICLE_DAY)
p0 = notki("[wolumeny]\nnotki_dziennie = 0\n")
sprawdz("0 slotow: obie listy puste", p0.NOTE_MIX_OTHER_DAY == () and p0.NOTE_MIX_ARTICLE_DAY == ()
        and p0.NOTKI_DZIENNIE == 0, (p0.NOTE_MIX_OTHER_DAY, p0.NOTE_MIX_ARTICLE_DAY))
p5 = notki('[wolumeny]\nnotki_dziennie = 5\n[publikowanie]\nmiks_notek = '
           '["CIEKAWOSTKA", "CIEKAWOSTKA", "DYSKUSJA", "SPROSTOWANIE", "MYSL"]\n')
sprawdz("5 slotow: dzien artykulu ma 5 notek, z tego 2 promujace",
        len(p5.NOTE_MIX_ARTICLE_DAY) == 5 and p5.NOTE_MIX_ARTICLE_DAY.count("ARTYKUL") == 2,
        p5.NOTE_MIX_ARTICLE_DAY)
p2 = notki('[wolumeny]\nnotki_dziennie = 2\n[publikowanie]\nmiks_notek = '
           '["CIEKAWOSTKA", "DYSKUSJA", "MYSL", "SPROSTOWANIE"]\n')
sprawdz("2 sloty z miksu 4 typow: sloty wypelnione cyklicznie",
        p2.NOTE_MIX_OTHER_DAY == ("CIEKAWOSTKA", "DYSKUSJA"), p2.NOTE_MIX_OTHER_DAY)
sprawdz("2 sloty: promocja zajmuje JEDEN z nich, nie doklada trzeciego",
        p2.NOTE_MIX_ARTICLE_DAY == ("ARTYKUL", "CIEKAWOSTKA"), p2.NOTE_MIX_ARTICLE_DAY)
pz = notki('[wolumeny]\nnotki_dziennie = 3\nartykuly_tygodniowo = 0\n')
sprawdz("bez artykulow dzien artykulu == zwykly dzien",
        pz.NOTE_MIX_ARTICLE_DAY == pz.NOTE_MIX_OTHER_DAY and "ARTYKUL" not in pz.NOTE_MIX_ARTICLE_DAY,
        pz.NOTE_MIX_ARTICLE_DAY)
sprawdz("miks bez liczby: liczba to dlugosc miksu (zgodnosc wstecz)",
        len(notki('[publikowanie]\nmiks_notek = ["MYSL", "MYSL", "DYSKUSJA"]\n').NOTE_MIX_OTHER_DAY) == 3)
sprawdz("nieznany typ notki jest bledem",
        "nieznane typy" in (oblewa(lambda: notki('[publikowanie]\nmiks_notek = ["ZMYSLONY"]\n')) or ""))

# ================================================== 6. ZERO I HARMONOGRAM
print()
print("=== 6. ZERO WYLACZA FORMAT; HARMONOGRAM Z KARTRIDZA (W2) ===")
pw = notki("[wolumeny]\nrestacki_dziennie = [0, 0]\nfollow_miesiecznie = [0, 0]\n")
sprawdz("widelki [0, 0] sa przyjmowane", pw.RESTACK_DZIENNIE == (0, 0) and pw.FOLLOW_MIESIECZNIE == (0, 0))
pa = notki("[wolumeny]\nartykuly_tygodniowo = 0\n")
sprawdz("0 artykulow -> brak dni artykulu", pa.ARTYKULY_TYGODNIOWO == 0 and pa.DNI_ARTYKULU == ())
p3 = notki("[wolumeny]\nartykuly_tygodniowo = 3\n")
sprawdz("3 artykuly bez dni -> trzy dni dobrane przez silnik", len(p3.DNI_ARTYKULU) == 3, p3.DNI_ARTYKULU)
pd = notki('[harmonogram]\ndni_artykulu = ["Friday", "mon"]\n')
sprawdz("dni po nazwie, w dowolnej pisowni -> skroty w kolejnosci tygodnia",
        pd.DNI_ARTYKULU == ("Mon", "Fri") and pd.ARTYKULY_TYGODNIOWO == 2, pd.DNI_ARTYKULU)
pg = notki('[harmonogram]\ngodziny_przebiegow_utc = ["21:30", "9:05"]\n')
sprawdz("godziny -> liczba przebiegow i posortowany zegar",
        pg.PRZEBIEGOW_DZIENNIE == 2 and pg.GODZINY_PRZEBIEGOW_UTC == ("09:05", "21:30"))
pp = notki("[wolumeny]\nprzebiegow_dziennie = 2\n")
sprawdz("liczba bez godzin -> dwie godziny z domyslnego zegara, skrajne",
        len(pp.GODZINY_PRZEBIEGOW_UTC) == 2 and pp.GODZINY_PRZEBIEGOW_UTC[0] < pp.GODZINY_PRZEBIEGOW_UTC[-1])
pr = notki('[temat.rytm_roku]\n"3" = "marzec"\n"11" = "listopad"\n')
sprawdz("rytm roku z kartridza (klucze TOML -> miesiace)",
        pr.W_TYM_MIESIACU == {3: "marzec", 11: "listopad"}, pr.W_TYM_MIESIACU)

import jednostki  # noqa: E402

KATALOG, UZYTKOWNIK, MARKA = "/opt/probny", "probnyuzytkownik", "Probna Marka"
bez_art = jednostki.zbuduj(KATALOG, UZYTKOWNIK, MARKA, cfg=pa)
sprawdz("0 artykulow -> zegar i usluga artykulu NIE powstaja",
        not any("artykul_z_puli" in t for t in bez_art.values())
        and not any(n.startswith("nia-artykul") for n in bez_art), sorted(bez_art))
sprawdz("a zegar agenta i alarm zostaja", any("run.py" in t for t in bez_art.values())
        and any("alarm.py" in t for t in bez_art.values()))
z_godz = jednostki.zbuduj(KATALOG, UZYTKOWNIK, MARKA, cfg=pg)
zegar = next(t for n, t in z_godz.items() if n.endswith(".timer") and
             "run.py" in z_godz.get(n[:-6] + ".service", ""))
linie = [w for w in zegar.splitlines() if w.startswith("OnCalendar=")]
sprawdz("zegar agenta ma dokladnie tyle OnCalendar, ile godzin w kartridzu",
        linie == ["OnCalendar=*-*-* 09:05:00", "OnCalendar=*-*-* 21:30:00"], linie)
zegar_art = next(t for n, t in z_godz.items() if n.endswith(".timer") and
                 "artykul_z_puli" in z_godz.get(n[:-6] + ".service", ""))
sprawdz("zegar artykulu bierze dni i godzine z kartridza",
        "OnCalendar=Tue *-*-* 14:00:00" in zegar_art, zegar_art)
domyslny = jednostki.zbuduj(KATALOG, UZYTKOWNIK, MARKA, cfg=preset.proba_konfiguracji(config, BAZA))
sprawdz("kontrdowod: bez kartridza komplet szesciu jednostek", len(domyslny) == 6, sorted(domyslny))

# ======================================================== 7. WALIDACJA
print()
print("=== 7. WALIDATORY ZNAJA DZIEDZINE WARTOSCI (T05) ===")
przypadki = [
    ("ujemne komentarze", "[wolumeny]\nkomentarze_dziennie = [-1, 3]\n", "ujemna"),
    ("1,5 przebiegu", "[wolumeny]\nprzebiegow_dziennie = 1.5\n", "calkowitej"),
    ("zero przebiegow", "[wolumeny]\nprzebiegow_dziennie = 0\n", ">= 1"),
    ("godzina 98", "[publikowanie]\nokno_et = [98, 99]\n", "0-24"),
    ("dzien 99", '[konto]\ndata_przestawienia = "2026-99-99"\n', "kalendarz"),
    ("zmyslona strefa", '[konto]\nstrefa_czytelnika = "Nibylandia/Miasto"\n', "IANA"),
    ("ujemny sufit", "[pieniadze]\nsufit_miesieczny_usd = -1\n", "nieujemn"),
    ("zla godzina zegara", '[harmonogram]\ngodzina_artykulu_utc = "25:00"\n', "HH:MM"),
    ("powtorzona godzina", '[harmonogram]\ngodziny_przebiegow_utc = ["11:00", "11:00"]\n',
     "powtarzaja"),
    ("nieznany dzien", '[harmonogram]\ndni_artykulu = ["Wtorek"]\n', "dniem tygodnia"),
    ("8 artykulow na tydzien", "[wolumeny]\nartykuly_tygodniowo = 8\n", "siedem"),
    ("liczba przebiegow niezgodna z zegarem",
     '[wolumeny]\nprzebiegow_dziennie = 2\n[harmonogram]\ngodziny_przebiegow_utc = ["1:00", "2:00", "3:00"]\n',
     "zgodne"),
    ("liczba artykulow niezgodna z dniami",
     '[wolumeny]\nartykuly_tygodniowo = 2\n[harmonogram]\ndni_artykulu = ["Tue"]\n', "zgodne"),
    ("ujemne notki", "[wolumeny]\nnotki_dziennie = -2\n", "ujemna"),
    ("kanal RSS bez http", '[zrodla]\nkanaly_rss = { "X" = "ftp://x" }\n', "http"),
    ("domena ze sciezka", '[zrodla]\ndomeny_preferowane = ["https://x.org/a"]\n', "hosta"),
    ("miesiac 13", '[temat.rytm_roku]\n"13" = "x"\n', "1-12"),
]
for nazwa, reszta, fragment in przypadki:
    komunikat = oblewa(lambda reszta=reszta: dokument(reszta))
    sprawdz("  %s -> zatrzymuje i mowi co" % nazwa,
            komunikat is not None and fragment in komunikat, (komunikat or "PRZESZLO")[:120])
raz = konfiguracja._slownik_list({"kanon": ["a", "b"]}, "x")
sprawdz("walidator przykladow przyjmuje wlasny wynik (T06)",
        konfiguracja._slownik_list(raz, "x") == raz)
_skrajne = oblewa(lambda: dokument('[konto]\nstrefa_czytelnika = "UTC"\n[wolumeny]\n'
                                   'notki_dziennie = 0\nartykuly_tygodniowo = 0\n'
                                   'lajki_dziennie = [0, 0]\n'))
sprawdz("kontrdowod: [0, 0], 0 notek, 0 artykulow, strefa UTC przechodza", _skrajne is None, _skrajne)

# ======================================================== 8. ATOMOWOSC
print()
print("=== 8. ZLY KARTRIDZ NIE ZMIENIA NICZEGO (T03) ===")
proba = preset.proba_konfiguracji(config, BAZA)
przed = zwykla({n: getattr(proba, n, None) for n in konfiguracja.STALE_KONTA})
zly = wczytaj("zly", nisza="nisza zla", reszta='[modele]\nrole = { nie_ma_takiego = "x" }\n')
blad = oblewa(lambda: preset.zastosuj(zly, proba, BAZA))
sprawdz("nieznana rola zatrzymuje", blad is not None and "nieznane etapy" in blad, blad)
po = zwykla({n: getattr(proba, n, None) for n in konfiguracja.STALE_KONTA})
sprawdz("i NISZA ani nic innego nie zostalo zmienione", po == przed,
        [n for n in przed if przed[n] != po[n]])

# ========================================================== 9. OKLADKA
print()
print("=== 9. ROLA OBRAZU I MODEL OBRAZU RAZEM (T15) ===")
po_obraz = notki('[modele]\nobraz = "dall-e-3"\n')
sprawdz("modele.obraz ustawia IMAGE_MODEL i role naraz",
        po_obraz.IMAGE_MODEL == "dall-e-3" and po_obraz.MODEL_FOR["obraz"] == "dall-e-3"
        and po_obraz.OBRAZ_WLACZONY)
bez = notki('[modele]\nobraz = ""\n')
sprawdz("pusty obraz wylacza okladke", bez.OBRAZ_WLACZONY is False)
rola = notki('[modele]\nrole = { obraz = "dall-e-3" }\n')
sprawdz("sama rola tez przestawia IMAGE_MODEL", rola.IMAGE_MODEL == "dall-e-3")
sprawdz("pisarz zapasowy z kartridza", notki('[modele]\nzapasowy_pisarz = ""\n').ZAPASOWY_PISARZ == "")
_gpt = wczytaj("gpt", reszta='[modele]\nrole = { write = "gpt-6-astra" }\n')
_bledy, _ = preset.sprawdz(_gpt, config, BAZA, srodowisko={})
sprawdz("model bez sciezki dostawcy jest bledem sprawdzenia", any("dostawcy" in b for b in _bledy), _bledy)

# ========================================================== 10. AKTYWACJA
print()
print("=== 10. PODLACZ / ODLACZ / ZMIANA PO AKTYWACJI / BRAMA (C1) ===")
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    korzen = pathlib.Path(tmp)
    agent = korzen / "agent-v2"
    agent.mkdir()
    presety = korzen / "presety"
    (presety / "a" / "prompty").mkdir(parents=True)
    plik_a = presety / "a" / "preset.toml"
    plik_a.write_text(tekst("a", "nisza A"), encoding="utf-8")
    (presety / "a" / "prompty" / "okladka.md").write_text("Notatka.\n---\nBlok okladki A.\n",
                                                          encoding="utf-8")
    plik_b = presety / "b.toml"
    plik_b.write_text(tekst("b", reszta='[modele]\nrole = { write = "gpt-6-astra" }\n'),
                      encoding="utf-8")

    sprawdz("bez wskaznika: nic nie jest podlaczone", preset.aktywacja(agent, srodowisko={}) is None)
    sprawdz("lista widzi katalog i plik",
            [preset.nazwa_z_pliku(p) for p in preset.lista(agent)] == ["a", "b"],
            [preset.nazwa_z_pliku(p) for p in preset.lista(agent)])
    sprawdz("znajdz po nazwie katalogu trafia w preset.toml",
            preset.znajdz("a", agent).name == "preset.toml")
    akt, uwagi = preset.podlacz(presety / "a", agent, config, BAZA, srodowisko={})
    sprawdz("podlacz pisze wskaznik", preset.wskaznik(agent).exists())
    sprawdz("instancja = nazwa kartridza, katalog danych istnieje",
            akt.instancja == "a" and akt.katalog_danych.is_dir(), akt)
    sprawdz("blok z prompty/ jest w aktywacji", akt.preset.bloki.get("okladka") == "Blok okladki A.")
    sprawdz("pierwsza aktywacja ma numer 1", akt.numer == 1, akt.numer)
    odczyt = preset.aktywacja(agent, srodowisko={})
    sprawdz("aktywacja() odczytuje to samo", odczyt is not None and odczyt.preset.odcisk == akt.preset.odcisk
            and odczyt.instancja == "a" and odczyt.zrodlo == "wskaznik")
    wsk_przed = preset.wskaznik(agent).read_text(encoding="utf-8")

    blad = oblewa(lambda: preset.podlacz(plik_b, agent, config, BAZA, srodowisko={}))
    sprawdz("zly kartridz B nie przechodzi", blad is not None and "dostawcy" in blad, blad)
    sprawdz("i wskaznik A jest nietkniety", preset.wskaznik(agent).read_text(encoding="utf-8") == wsk_przed)

    # ZMIANA BLOKU PO AKTYWACJI TEZ ZATRZYMUJE START — odcisk obejmuje prompty/.
    (presety / "a" / "prompty" / "okladka.md").write_text("Notatka.\n---\nInny blok.\n", encoding="utf-8")
    blad = oblewa(lambda: preset.aktywacja(agent, srodowisko={}))
    sprawdz("zmiana bloku po podlaczeniu = odmowa startu z nazwa kartridza",
            blad is not None and "zmienil sie po aktywacji" in blad and "podlacz a" in blad, blad)
    akt2, _ = preset.podlacz(presety / "a", agent, config, BAZA, srodowisko={})
    sprawdz("ponowne podlaczenie: numer 2, ta sama instancja", akt2.numer == 2 and akt2.instancja == "a")
    sprawdz("i start znow przechodzi", preset.aktywacja(agent, srodowisko={}) is not None)

    akt3, _ = preset.podlacz(presety / "a", agent, config, BAZA, instancja="a-swieza", srodowisko={})
    sprawdz("inna instancja -> inny katalog danych",
            akt3.katalog_danych != akt2.katalog_danych and akt3.katalog_danych.is_dir())

    ze_srodowiska = preset.aktywacja(agent, srodowisko={preset.ZMIENNA: str(plik_b.resolve())})
    sprawdz("AGENT_V2_PRESET wskazuje inny kartridz bez zmiany wskaznika",
            ze_srodowiska is not None and ze_srodowiska.preset.nazwa == "b"
            and ze_srodowiska.zrodlo == "srodowisko" and ze_srodowiska.instancja == "podglad-b")

    dane = preset.odlacz(agent)
    sprawdz("odlacz oddaje, co bylo podlaczone",
            dane and dane.get("preset") == "a" and dane.get("instancja") == "a-swieza", dane)
    sprawdz("po odlaczeniu nie ma wskaznika", not preset.wskaznik(agent).exists())
    sprawdz("a katalogi instancji ZOSTAJA", akt2.katalog_danych.is_dir() and akt3.katalog_danych.is_dir())

    def _zdarzenia(katalog):
        dziennik = (katalog / preset.NAZWA_DZIENNIKA).read_text(encoding="utf-8")
        return [json.loads(w)["zdarzenie"] for w in dziennik.splitlines() if w.strip()]

    sprawdz("dziennik `a`: podlacz, podlacz", _zdarzenia(akt2.katalog_danych) == ["podlacz", "podlacz"])
    sprawdz("dziennik `a-swieza`: podlacz, odlacz", _zdarzenia(akt3.katalog_danych) == ["podlacz", "odlacz"])
    sprawdz("drugie odlacz nie wywala", preset.odlacz(agent) is None)

    goly = types.SimpleNamespace(W_TESCIE=False, PRESET_AKTYWACJA=None)
    blad = oblewa(lambda: preset.wymagaj_aktywnego(goly, "run.py"))
    sprawdz("bez kartridza brama odmawia i mowi, co zrobic",
            blad is not None and "podlacz" in blad and "run.py" in blad, blad)
    # Brama pyta WSKAZNIK, nie tylko obiekt w pamieci (audyt 2026-09-06, F01):
    # po `odlacz` wyzej nawet wazny kiedys `akt2` dostaje odmowe, a przepuszcza
    # dopiero aktywacja, ktora stoi we wskazniku TERAZ.
    po_odlaczeniu = types.SimpleNamespace(W_TESCIE=False, PRESET_AKTYWACJA=akt2)
    blad2 = oblewa(lambda: preset.wymagaj_aktywnego(po_odlaczeniu, "run.py"))
    sprawdz("po odlaczeniu stary obiekt w pamieci NIE przechodzi bramy",
            blad2 is not None and "odlaczony" in blad2, blad2)
    akt4, _ = preset.podlacz(presety / "a", agent, config, BAZA, srodowisko={})
    z_presetem = types.SimpleNamespace(W_TESCIE=False, PRESET_AKTYWACJA=akt4)
    sprawdz("z kartridzem brama przepuszcza", preset.wymagaj_aktywnego(z_presetem) is akt4)
    preset.odlacz(agent)
    w_tescie = types.SimpleNamespace(W_TESCIE=True, PRESET_AKTYWACJA=None)
    sprawdz("w darmowym tescie brama milczy", preset.wymagaj_aktywnego(w_tescie) is None)


def _wola_brame_przed_baza(plik: str) -> bool:
    drzewo = ast.parse(pathlib.Path(plik).read_text(encoding="utf-8"))
    for w in ast.walk(drzewo):
        if isinstance(w, ast.FunctionDef) and w.name == "main":
            zrodlo = ast.unparse(w)
            return 0 <= zrodlo.find("wymagaj_aktywnego") < zrodlo.find("db.connect")
    return False


sprawdz("run.main wola brame przed baza", _wola_brame_przed_baza("agent-v2/run.py"))
sprawdz("artykul_z_puli.main wola brame przed baza", _wola_brame_przed_baza("agent-v2/artykul_z_puli.py"))
sprawdz("brama rzuca BrakPresetu, a nie wraca do wbudowanego profilu (C1)",
        "raise BrakPresetu" in pathlib.Path("agent-v2/preset.py").read_text(encoding="utf-8"))

# ================================================= 11. WLASCICIEL ZADANIA
print()
print("=== 11. OCZEKUJACY ARTYKUL I PROMOCJA NALEZA DO INSTANCJI (T22) ===")
_stara_instancja = config.INSTANCJA
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    zdj = config.uzyj_katalogu_danych(pathlib.Path(tmp))
    try:
        config.INSTANCJA = "instancja-a"
        stages.zapomnij_niewystawiony()
        stages.zapamietaj_niewystawiony(pathlib.Path(tmp) / "art.md", "proba")
        sprawdz("znacznik niesie instancje",
                (stages.niewystawiony_artykul() or {}).get("instancja") == "instancja-a")
        config.INSTANCJA = "instancja-b"
        sprawdz("inna instancja NIE widzi cudzego artykulu", stages.niewystawiony_artykul() is None)
        config.INSTANCJA = "instancja-a"
        sprawdz("wlasna instancja widzi go nadal", stages.niewystawiony_artykul() is not None)
        stages.zapomnij_niewystawiony()
        stages.zapisz_do_promocji("https://x/p/a", "Artykul A", "tresc")
        sprawdz("wpis promocji niesie instancje", stages.wczytaj_promocje()[-1].get("instancja") == "instancja-a")
        sprawdz("wlasna instancja ma co promowac", (stages.artykul_do_promocji() or {}).get("tytul") == "Artykul A")
        config.INSTANCJA = "instancja-b"
        sprawdz("inna instancja nie promuje cudzego artykulu", stages.artykul_do_promocji() is None)
        config.INSTANCJA = ""
        sprawdz("kontrdowod: bez instancji (brak kartridza) kolejka jest widoczna",
                stages.artykul_do_promocji() is not None)
    finally:
        config.INSTANCJA = _stara_instancja
        config.przywroc_katalog_danych(zdj)

# ======================================================== 12. STYL
print()
print("=== 12. STYL Z KARTRIDZA (C4) ===")
import style  # noqa: E402

proba_ai, _ = preset.rozwiaz(ai, config, BAZA)
sprawdz("profile stylu kartridza ai leza w jego katalogu",
        pathlib.Path(proba_ai.STYLE_PROFILE_POSITIVE).parent == (KARTRIDZ_AI / "styl").resolve()
        and pathlib.Path(proba_ai.STYLE_PROFILE_NEGATIVE).is_file())
ps = notki('korpus = "moj/korpus.txt"\nopis = "glos probny"\n')
sprawdz("sciezki stylu spoza katalogu kartridza rozwiazane wzgledem repo",
        pathlib.Path(ps.STYLE_PROFILE_POSITIVE).is_absolute()
        and str(ps.STYLE_CORPUS).replace("\\", "/").endswith("moj/korpus.txt"))
sprawdz("opis glosu dochodzi do stalej", ps.STYL_OPIS == "glos probny")
_stan = (config.STYL_WYMAGAJ_KORPUSU, config.STYLE_CORPUS, config.STYL_OPIS)
try:
    config.STYLE_CORPUS = pathlib.Path(tempfile.gettempdir()) / "nie-ma-takiego-korpusu.txt"
    config.STYL_WYMAGAJ_KORPUSU = False
    sprawdz("bez korpusu i bez wymogu: pusta lista, nie wyjatek", style.przyklady_albo_pusto() == [])
    config.STYL_WYMAGAJ_KORPUSU = True
    try:
        style.przyklady_albo_pusto()
        rzucil = False
    except style.StyleError:
        rzucil = True
    sprawdz("kontrdowod: z wymogiem brak korpusu nadal zatrzymuje (StyleError)", rzucil)
    config.STYL_OPIS = ""
    sprawdz("pusty opis daje jawne zdanie zastepcze, nie pustke", "no additional voice notes" in stages._blok_stylu())
    config.STYL_OPIS = "glos probny"
    sprawdz("opis z kartridza idzie do pol wspolnych",
            stages._pola_wspolne()["styl_opis"] == "glos probny" and "styl_opis" in stages.POLA_WSPOLNE)
finally:
    config.STYL_WYMAGAJ_KORPUSU, config.STYLE_CORPUS, config.STYL_OPIS = _stan

# ============================================== 13. SYGNALY: RSS I PRZEPLOT
print()
print("=== 13. KANALY RSS OBOK YOUTUBE, PO ROWNO ZE ZRODEL (W4) ===")
import korpus_kanalow  # noqa: E402

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel><title>Blog</title>
<item><title>Introducing a model that changes everything for agents today</title>
<pubDate>Wed, 02 Sep 2026 15:40:00 +0000</pubDate><link>https://a.example/p1</link></item>
<item><title>How to build a tutorial for a benchmark suite</title>
<pubDate>Tue, 01 Sep 2026 10:00:00 +0000</pubDate><link>https://a.example/p2</link></item>
<item><title>A licence clause that forbids one common use of the weights</title>
<pubDate>Mon, 31 Aug 2026 10:00:00 +0000</pubDate><link>https://a.example/p3</link></item>
</channel></rss>"""
ATOM = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>Lab</title>
<entry><title>Evaluation results for the new release across four tasks</title>
<published>2026-09-03T12:00:00Z</published><link rel="alternate" href="https://b.example/e1"/></entry>
</feed>"""
z_rss = korpus_kanalow.wpisy_z_kanalu("Blog", RSS)
z_atom = korpus_kanalow.wpisy_z_kanalu("Lab", ATOM)
sprawdz("RSS 2.0: data z pubDate, link, oprawa zdjeta, poradnik odsiany",
        [w["data"] for w in z_rss] == ["2026-09-02", "2026-08-31"]
        and z_rss[0]["url"] == "https://a.example/p1"
        and "changes everything" not in z_rss[0]["temat"].lower(), z_rss)
sprawdz("Atom: data z published, link z rel=alternate",
        len(z_atom) == 1 and z_atom[0]["data"] == "2026-09-03" and z_atom[0]["url"] == "https://b.example/e1", z_atom)
sprawdz("ten sam ksztalt slownika co z YouTube", set(z_rss[0]) == set(z_atom[0]) >= {"temat", "kanal", "data", "url"})
sprawdz("zepsuty XML daje pusta liste, nie wyjatek", korpus_kanalow.wpisy_z_kanalu("X", b"<rss") == [])
# OGON BEZ TYTULU. Kanal doklejal do kazdego tytulu „| AI at Meta", a jeden film
# mial tylko ten ogon — i przechodzil jako temat z czterech „slow".
OGON = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom"><title>Lab</title>
<entry><title>| AI at Meta</title><published>2026-02-26T18:52:14Z</published><link rel="alternate" href="https://b.example/e2"/></entry>
<entry><title>Introducing a unified model for audio separation across four benchmarks | AI at Meta</title>
<published>2026-02-25T18:52:14Z</published><link rel="alternate" href="https://b.example/e3"/></entry>
</feed>"""
_ogon = korpus_kanalow.wpisy_z_kanalu("Lab", OGON)
sprawdz("tytul zlozony z samego ogona kanalu odpada", all("e2" not in w["url"] for w in _ogon), _ogon)
sprawdz("a prawdziwy tytul z tym samym ogonem zostaje", len(_ogon) == 1 and "audio separation" in _ogon[0]["temat"], _ogon)
sprawdz("kontrdowod: liczenie tokenow puszczaloby ogon", len("| AI at Meta".split()) >= 4)
duzo = [{"temat": "arxiv paper number %d about a thing" % i, "kanal": "arXiv", "data": "2026-09-05", "url": "u%d" % i}
        for i in range(30)]
malo = [{"temat": "video about a benchmark result %d" % i, "kanal": "Wideo", "data": "2026-09-0%d" % (4 - i), "url": "v%d" % i}
        for i in range(3)]
przeplot = korpus_kanalow.przeplot_zrodel([duzo, malo])
sprawdz("przeplot: pierwsze szesc pozycji to na zmiane dwa zrodla",
        [w["kanal"] for w in przeplot[:6]] == ["arXiv", "Wideo"] * 3, [w["kanal"] for w in przeplot[:6]])
sprawdz("przeplot niczego nie gubi", len(przeplot) == 33, len(przeplot))
sprawdz("kontrdowod: bez przeplotu 26 pierwszych to samo zrodlo",
        all(w["kanal"] == "arXiv" for w in sorted(duzo + malo, key=lambda x: x["data"], reverse=True)[:26]))

# ============================================== 14. POCHODZENIE I CACHE
print()
print("=== 14. POCHODZENIE WARTOSCI I ODCISK W CACHE (K7, T13) ===")
skad = preset.pochodzenie(A, config, BAZA)
sprawdz("kanaly z A sa oznaczone jako preset", skad.get("KANALY_YOUTUBE") == "preset")
sprawdz("rola write z A jest z kartridza", skad.get("MODEL_FOR[write]") == "preset")
sprawdz("rola, ktorej A nie tknal, jest z silnika", skad.get("MODEL_FOR[scout]") == "silnik")
run_src = pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8")
sprawdz("cache etapu ma odcisk kartridza w nazwie pliku", 'f"{stage}.{odcisk}.json"' in run_src)
sprawdz("stan dziedziny pamieta pytanie",
        '"pytanie"' in pathlib.Path("agent-v2/aktualne_modele.py").read_text(encoding="utf-8"))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
