# -*- coding: utf-8 -*-
"""Nieudany komentarz ma NIE liczyc sie jako wykonany i NIE palic publikacji.

TRZY SKUTKI JEDNEGO ZIGNOROWANEGO WYNIKU. `browser.wystaw_komentarz` oddaje
slownik, w ktorym `wyslane` jest jedynym dowodem — ustawia je `potwierdz_
komentarz`, czyli pytanie do Substacka, a nie samo klikniecie. `run.py` ten
slownik wyrzucal i bezwarunkowo robil trzy rzeczy:

  1. `kanal.zapamietaj_komentarz(cel)` — publikacja wypadala z puli na
     ODSTEP_DNI_NA_PUBLIKACJE = 4 dni przez `_za_niedawno_u_nich`, mimo ze
     zadnego komentarza tam nie ma;
  2. `browser.zapomnij_platny_host(...)` — host znikal z listy platnych wbrew
     wlasnemu opisowi tej funkcji („UDANY komentarz kasuje host z listy"), wiec
     ta sama platna publikacja wracala do platnej oceny w kolejnym przebiegu;
  3. `zrobione["komentarze"] += 1` — podsumowanie przebiegu meldowalo prace,
     ktorej nie bylo.

Punkt 3 rozjezdzal dwie polowy tego samego licznika. `browser.z_dziennika_dzis`
(„liczymy wylacznie dzialania UDANE") i `norma.py` (`udane` z dziennika) licza
POTWIERDZONE; podsumowanie przebiegu liczylo PROBY. Skala z pomiaru 30 sierpnia
2026: 11 nieudanych komentarzy z 92 prob i 7 nieudanych odpowiedzi z 47.

To samo w bloku `dyskusje()`, gdzie doszla trzecia wada: `kontekst` szedl jako
sam `opis_celu(cel)`, bez `otwarcie` i `postawa`. Wedlug pomiaru z `browser.py`
(siedem dni, 29 wpisow `odpowiedz`, z czego 23 to komentarze pod cudzymi
notkami) to WLASNIE ten blok daje wiekszosc wypowiedzi — rozklad postaw byl
wiec mierzony na jednej szostej materialu.

I czwarta rzecz, z tego samego bloku: pula celow byla odsiewana z
`hosty_gdzie_komentarz_nie_wchodzi()` dopiero wewnatrz `mozna_komentowac`,
czyli PO platnym `wybierz_cele`. Platne publikacje odsiewano PRZED — a te dwa
sita sa tej samej natury i oba czytaja plik z dysku za darmo.

TEST JEST ZYWY: uruchamia prawdziwe `run.dzien()` z atrapami przegladarki i
kanalu, i patrzy na to, co przebieg NAPRAWDE zrobil — kogo zapamietal, co
oddal licznikowi i co dostal platny `wybierz_cele`. Zero sieci, zero wywolan
modelu, zero zapisu do plikow produkcji.

KONTRDOWOD (sekcja 5) odtwarza kod SPRZED poprawki przez odwrotna latke na
zrodle `run.py` i puszcza na nim te same trzy scenariusze.

--- CO DOSZLO 1 WRZESNIA -----------------------------------------------------

Sekcja 6: POMINIECIE. `wystaw_komentarz` przy `juz_sie_odezwalismy` oddaje
`{"wyslane": True, "pominiete": True}`, wiec sam warunek na `wyslane` je
przepuszczal. Zmierzone tym testem na kodzie bez odciecia:
`zapamietane=['https://zywy.example/p/a']`, `zapomniane=['zywy.example']`,
licznik przebiegu 2 — a dziennik ZERO wpisow, bo `wystaw_komentarz` pominiec
swiadomie nie zapisuje. Czyli znowu podsumowanie i pomiar mierza co innego.
Dochodzi drugi powod: `juz_sie_odezwalismy` oddaje True takze wtedy, gdy nie
odczytalo naszego id, wiec awaria `/public_profile` wypalilaby caly dzienny
budzet komentarzy bez ani jednego komentarza.

Sekcja 7: BLOK `odpowiedzi()`. Nadal ignorowal wynik obu funkcji, a licznik
rosl bezwarunkowo — ta sama wada, ktora naprawiono dwa bloki nizej.

Sekcja 8: HOST Z `www.`. Cale twierdzenie o normalizacji stoi na tym, ze sito
w `run.dzien` i zapora `mozna_komentowac` licza host identycznie. Nikt tego
dotad nie przepuscil ani jednym adresem z `www.`.

BEZ PYTESTA. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_komentarz_potwierdzony.py
"""
import contextlib
import hashlib
import io
import pathlib
import sys
import tempfile
import types

sys.path.insert(0, "agent-v2")
import config   # noqa: E402
# PRAWDZIWY `_na_kanal`, bo atrapa `stages` musi go miec: bloki `komentarze`
# i `dyskusje` w `run.py` sa nim dekorowane (znacznik kanalu w tabeli `calls`).
# Podstawienie tu wlasnej, pustej wersji zmienilo by ten test w potwierdzenie
# samego siebie — przebieg chodzilby bez znacznika, ktory produkcja stawia.
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


def odcisk(p):
    p = pathlib.Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16] if p.exists() else "brak"


PILNOWANE = [config.DB_PATH,
             config.DATA_DIR / "dziennik.jsonl",
             config.DATA_DIR / "gdzie_komentowalismy.json",
             config.DATA_DIR / "platne_komentarze.json"]
PRZED = {str(p): odcisk(p) for p in PILNOWANE}

ZRODLO = pathlib.Path("agent-v2/run.py").read_text(encoding="utf-8")

MARTWY = "slowboring.com"      # host z pomiaru 30 sierpnia: 0 wejsc na 2+ proby
ZYWY = "zywy.example"


# --------------------------------------------------------------------------
# ATRAPY. Tylko tyle, ile `dzien()` naprawde dotyka — reszta blokow ma zerowy
# budzet i sama z siebie nic nie robi.
# --------------------------------------------------------------------------
def modul(nazwa, **atrybuty):
    m = types.ModuleType(nazwa)
    for k, v in atrybuty.items():
        setattr(m, k, v)
    return m


class Slad:
    """Co przebieg zrobil ze swiatem — jedyne, o co ten test pyta."""

    def __init__(self, wyslane, pominiete=False):
        self.wyslane = wyslane
        # POMINIECIE to osobny stan, nie odmiana porazki. `wystaw_komentarz`
        # oddaje przy nim `{"wyslane": True, "pominiete": True}` — czyli sam
        # warunek na `wyslane` je PRZEPUSZCZA.
        self.pominiete = pominiete
        self.zapamietane = []          # kanal.zapamietaj_komentarz
        self.zapomniane_platne = []    # browser.zapomnij_platny_host
        self.oceniane = []             # co dostal PLATNY wybierz_cele
        self.konteksty_dyskusji = []   # kontekst przekazany do wystaw_odpowiedz
        self.proby_komentarza = 0
        self.proby_odpowiedzi = 0
        self.odpowiedzi_pod_artykulem = 0


def swiat(slad, martwe_hosty, czekajace=()):
    """Buduje komplet atrap: browser, kanal, alarm, stages, config."""

    def wystaw_komentarz(url, tekst, wyslij=False, kontekst=None):
        slad.proby_komentarza += 1
        if slad.pominiete:
            # DOKLADNIE TO, CO ODDAJE PRODUKCJA przy `juz_sie_odezwalismy`.
            return {"wpisane": False, "wyslane": True, "pominiete": True,
                    "blad": None}
        return {"wpisane": True, "wyslane": slad.wyslane,
                "blad": None if slad.wyslane
                else "nie ma pola komentarza pod tym postem",
                "przycisk_widoczny": slad.wyslane}

    def wystaw_odpowiedz(note_id, tekst, wyslij=False, kontekst=None,
                         rodzaj="odpowiedz"):
        slad.proby_odpowiedzi += 1
        slad.konteksty_dyskusji.append(dict(kontekst or {}))
        if slad.pominiete:
            return {"wpisane": False, "wyslane": True, "pominiete": True,
                    "blad": None}
        return {"wpisane": True, "wyslane": slad.wyslane, "blad": None}

    def wystaw_odpowiedz_pod_artykulem(url, autor, tekst, wyslij=False):
        slad.odpowiedzi_pod_artykulem += 1
        return {"wpisane": True, "wyslane": slad.wyslane, "blad": None}

    fake_browser = modul(
        "browser",
        ile_dzis_wystawione=lambda: {},
        dopisz_skutki=lambda: None,
        statystyki_pozycji=lambda: None,
        nieodpowiedziane=lambda: list(czekajace),
        komentarze_pod_artykulami=lambda: [],
        odpowiedzi_na_nasze_komentarze=lambda: [],
        hosty_tylko_dla_placacych=lambda: set(),
        hosty_gdzie_komentarz_nie_wchodzi=lambda: set(martwe_hosty),
        mozna_komentowac=lambda url: True,
        read_pages=lambda urls: [{"url": u, "title": "t", "text": "tresc"}
                                 for u in urls],
        wystaw_komentarz=wystaw_komentarz,
        wystaw_odpowiedz=wystaw_odpowiedz,
        wystaw_odpowiedz_pod_artykulem=wystaw_odpowiedz_pod_artykulem,
        zapomnij_platny_host=lambda host: slad.zapomniane_platne.append(host),
        polub_w_kanale=lambda ile, wyslij=False: {"polubione": 0},
        restackuj_w_kanale=lambda ile, ocen, wyslij=False: {"restackowane": 0},
        uchwyt_publikacji=lambda host: "",
        zasubskrybuj=lambda uchwyt, wyslij=False: None,
    )

    def szukaj_nowych():
        return [
            {"rodzaj": "post", "url": "https://%s/p/a" % ZYWY, "pub": ZYWY,
             "tytul": "Zywy", "opis": "o", "komentarze": 3, "reakcje": 9,
             "data": "", "skad": "test"},
            {"rodzaj": "post", "url": "https://%s/p/b" % MARTWY, "pub": MARTWY,
             "tytul": "Martwy", "opis": "o", "komentarze": 4, "reakcje": 8,
             "data": "", "skad": "test"},
            {"rodzaj": "notka", "id": 111, "url": "https://substack.com/note/c-111",
             "pub": "ktos", "tytul": "Notka", "opis": "tresc notki",
             "komentarze": 2, "reakcje": 5, "data": "", "skad": "test"},
        ]

    fake_kanal = modul(
        "kanal",
        szukaj_nowych=szukaj_nowych,
        posty_z_kanalu=lambda ile=25: [],
        notki_z_kanalu=lambda: [],
        zapamietaj_komentarz=lambda post: slad.zapamietane.append(
            (post.get("url") or "")),
        _historia=lambda: {},
        _wiek_minut=lambda data: 1000.0,
    )

    fake_alarm = modul("alarm", sprawdz_sesje_i_ostrzez=lambda: None)
    # Belka bezpieczenstwa: `kopia_listy()` przy `wyslij=True` potrafi wolac
    # prawdziwy eksport listy subskrybentow. Zadne wyjscie z tego testu nie
    # moze dotknac sieci.
    fake_kopia = modul("kopia_subskrybentow", main=lambda: None)

    def wybierz_cele(conn, run_id, lista):
        slad.oceniane.append([x.get("url", "") for x in lista])
        return list(lista)

    fake_stages = modul(
        "stages",
        _na_kanal=stages._na_kanal,
        budzet_dnia=lambda conn: {"notki": 0, "komentarze": 2, "lajki": 0,
                                  "restacki": 0, "follow": 0, "subskrypcje": 0},
        wybierz_cele=wybierz_cele,
        comment_on=lambda conn, run_id, post: {
            "candidates": [{"comment": "Delivery charges are the margin.",
                            "safe_to_post": True}],
            "otwarcie": "Delivery charges are the margin",
            "postawa": "CIEKAWOSC"},
        zbierz_pytania=lambda czekaja: None,
        wybierz_do_odpowiedzi=lambda conn, run_id, lista: list(lista),
        reply_to=lambda conn, run_id, co, ctx: {
            "candidates": [{"reply": "Krotka odpowiedz na zarzut."}]},
    )

    kat = pathlib.Path(tempfile.mkdtemp())
    (kat / "kopie").mkdir()
    (kat / "kopie" / "subskrybenci-test.csv").write_text("x", encoding="utf-8")

    class KonfigTestowa:
        """Prawdziwy config, ale z ustalona pora i wlasnym katalogiem danych."""

        DATA_DIR = kat

        def __getattr__(self, nazwa):
            return getattr(config, nazwa)

        def cichy_dzien(self):
            return False

        def pora_na_publikacje(self):
            return True, "test"

    return (fake_browser, fake_kanal, fake_alarm, fake_kopia, fake_stages,
            KonfigTestowa())


def zbuduj_run(zrodlo, nazwa):
    """Wczytuje `run.py` z PODANEGO zrodla jako osobny modul.

    Dzieki temu kontrdowod moze puscic ten sam scenariusz na kodzie sprzed
    poprawki, nie ruszajac pliku w repozytorium.
    """
    m = types.ModuleType(nazwa)
    m.__dict__["__name__"] = nazwa      # zeby nie odpalic bloku __main__
    m.__dict__["__file__"] = "agent-v2/run.py"
    exec(compile(zrodlo, "agent-v2/run.py", "exec"), m.__dict__)
    return m


def przebieg(zrodlo, wyslane, martwe_hosty=(MARTWY,), nazwa="run_pod_testem",
             pominiete=False, czekajace=()):
    """Uruchamia prawdziwe `dzien()` na atrapach i oddaje (slad, wydruk)."""
    slad = Slad(wyslane, pominiete=pominiete)
    fb, fk, fa, fkop, fs, fc = swiat(slad, martwe_hosty, czekajace)
    stare = {n: sys.modules.get(n)
             for n in ("browser", "kanal", "alarm", "kopia_subskrybentow")}
    sys.modules["browser"] = fb
    sys.modules["kanal"] = fk
    sys.modules["alarm"] = fa
    sys.modules["kopia_subskrybentow"] = fkop
    try:
        m = zbuduj_run(zrodlo, nazwa)
        m.stages = fs
        m.config = fc
        m.ile_przebiegow_zostalo = lambda conn: 1
        m.zmiesci_sie = lambda rodzaj, ile, udzial=1.0: ile
        m.zostal_czas = lambda na_co="", potrzeba_s=0.0: True
        m.rytm = lambda co, na_co, stan: True   # zero snu, zero zegara
        bufor = io.StringIO()
        with contextlib.redirect_stdout(bufor):
            m.dzien(None, 1, wyslij=True)
        return slad, bufor.getvalue()
    finally:
        for n, v in stare.items():
            if v is None:
                sys.modules.pop(n, None)
            else:
                sys.modules[n] = v


def licznik(wydruk, pozycja="komentarze"):
    """Liczba z podsumowania przebiegu — to, co widzi wlasciciel i alarm."""
    ogon = wydruk.split("dzień zamknięty")[-1]
    for linia in ogon.splitlines():
        if linia.strip().startswith(pozycja + ":"):
            return int(linia.split(":")[1].strip())
    return None


# --------------------------------------------------------------------------
print("=== 1. NIEUDANY KOMENTARZ NIE LICZY SIE I NIC NIE PALI ===")

slad, wydruk = przebieg(ZRODLO, wyslane=False)
print("    proby: komentarz=%d odpowiedz=%d, licznik=%s"
      % (slad.proby_komentarza, slad.proby_odpowiedzi, licznik(wydruk)))

sprawdz("proba komentarza jednak byla (test cokolwiek mierzy)",
        slad.proby_komentarza >= 1, slad.proby_komentarza)
sprawdz("nieudany komentarz NIE pali publikacji na 4 dni",
        slad.zapamietane == [], slad.zapamietane)
sprawdz("nieudany komentarz NIE zdejmuje hosta z listy platnych",
        slad.zapomniane_platne == [], slad.zapomniane_platne)
sprawdz("licznik przebiegu pokazuje 0 wykonanych komentarzy",
        licznik(wydruk) == 0, licznik(wydruk))

print()
print("=== 2. UDANY KOMENTARZ ROBI DOKLADNIE TO, CO ROBIL ===")
# Poprawka ma odciac wylacznie sciezke porazki. Gdyby przy okazji urwala
# zapamietywanie albo zdejmowanie hosta, byloby to gorsze od wady, ktora leczy.

slad_ok, wydruk_ok = przebieg(ZRODLO, wyslane=True)
print("    zapamietane=%s  zapomniane_platne=%s  licznik=%s"
      % (slad_ok.zapamietane, slad_ok.zapomniane_platne, licznik(wydruk_ok)))

sprawdz("udany komentarz zapamietuje publikacje",
        any(ZYWY in u for u in slad_ok.zapamietane), slad_ok.zapamietane)
sprawdz("udany komentarz zdejmuje host z listy platnych",
        any(ZYWY in h for h in slad_ok.zapomniane_platne),
        slad_ok.zapomniane_platne)
sprawdz("licznik liczy komentarz i dyskusje (2)",
        licznik(wydruk_ok) == 2, licznik(wydruk_ok))

print()
print("=== 3. DYSKUSJE: WYNIK LICZY SIE, POSTAWA JEDZIE DO DZIENNIKA ===")
# 23 z 29 wypowiedzi przebiegu ida ta droga (pomiar w `browser.py`), wiec to
# tutaj rozstrzyga sie, czy przydzielona postawa jest w ogole mierzalna.

print("    kontekst dyskusji: %s" % (slad_ok.konteksty_dyskusji[:1]))
sprawdz("dyskusja w ogole doszla do skutku (test cokolwiek mierzy)",
        slad_ok.proby_odpowiedzi >= 1, slad_ok.proby_odpowiedzi)
sprawdz("kontekst dyskusji niesie POSTAWE",
        all(k.get("postawa") for k in slad_ok.konteksty_dyskusji),
        slad_ok.konteksty_dyskusji)
sprawdz("kontekst dyskusji niesie OTWARCIE",
        all(k.get("otwarcie") for k in slad_ok.konteksty_dyskusji),
        slad_ok.konteksty_dyskusji)
sprawdz("kontekst dyskusji nadal niesie opis celu",
        all("komentarzy_przed" in k for k in slad_ok.konteksty_dyskusji),
        slad_ok.konteksty_dyskusji)
sprawdz("nieudana dyskusja nie podbija licznika",
        licznik(wydruk) == 0, licznik(wydruk))

print()
print("=== 4. MARTWY HOST ODSIANY PRZED PLATNA OCENA ===")
# `wybierz_cele` to jedyne platne wywolanie w tym bloku. Pytanie brzmi wiec
# nie „czy odsiewamy", tylko „czy odsiewamy, ZANIM zaplacimy".

pierwsza_ocena = slad.oceniane[0] if slad.oceniane else []
print("    do oceny poszlo: %s" % pierwsza_ocena)
sprawdz("platny wybierz_cele w ogole dostal cele (test cokolwiek mierzy)",
        bool(pierwsza_ocena), pierwsza_ocena)
sprawdz("martwy host NIE trafil do platnej oceny",
        all(MARTWY not in u for u in pierwsza_ocena), pierwsza_ocena)
sprawdz("zywy host trafil (nie odsialismy za szeroko)",
        any(ZYWY in u for u in pierwsza_ocena), pierwsza_ocena)

# Bez wpisow o porazkach lista jest pusta i nic nie moze zniknac z puli.
slad_pusty, _ = przebieg(ZRODLO, wyslane=True, martwe_hosty=())
sprawdz("przy pustej liscie martwych hostow oceniane sa OBA cele",
        len(slad_pusty.oceniane[0]) == 2, slad_pusty.oceniane[0])

print()
print("=== 5. KONTRDOWOD: KOD SPRZED POPRAWKI OBLEWA TE SAME PYTANIA ===")
# Odwrotna latka na zrodle. Kazda podmiana MUSI cos zmienic — inaczej
# kontrdowod bylby pusty i test chwalilby sam siebie.

stary = ZRODLO
latki = [
    ("odsiew martwych hostow przed ocena",
     "martwe = browser.hosty_gdzie_komentarz_nie_wchodzi()",
     "martwe = set()"),
    ("warunek na potwierdzenie wysylki",
     '                if not wynik.get("wyslane"):\n                    continue\n',
     "                if False:\n                    continue\n"),
    ("warunek laczony (dyskusje i odpowiedzi)",
     '                if wynik.get("pominiete") or not wynik.get("wyslane"):\n'
     "                    continue\n",
     "                if False:\n                    continue\n"),
    ("odciecie pominiec od licznika dnia",
     '                if wynik.get("pominiete"):\n'
     '                    print("  (pominiete — nie licze do normy dnia)",'
     " flush=True)\n                    continue\n",
     ""),
    ("postawa i otwarcie w dyskusjach",
     '                    kontekst={**opis_celu(cel),\n'
     '                              "otwarcie": (out.get("otwarcie") or "")[:60],\n'
     '                              "postawa": out.get("postawa") or ""},\n'
     '                    rodzaj="komentarz")',
     "                    kontekst=opis_celu(cel),\n"
     '                    rodzaj="komentarz")'),
]
for opis, nowe, dawne in latki:
    ile = stary.count(nowe)
    sprawdz("latka odwrotna ma co cofnac: %s" % opis, ile >= 1, "0 trafien")
    stary = stary.replace(nowe, dawne)
sprawdz("zrodlo sprzed poprawki naprawde sie rozni", stary != ZRODLO)

slad_s, wydruk_s = przebieg(stary, wyslane=False, nazwa="run_sprzed_poprawki")
print("    STARY KOD: zapamietane=%s zapomniane=%s licznik=%s"
      % (slad_s.zapamietane, slad_s.zapomniane_platne, licznik(wydruk_s)))
print("    STARY KOD: do oceny poszlo %s" % (slad_s.oceniane[0]
                                             if slad_s.oceniane else []))

sprawdz("STARY KOD palil publikacje mimo nieudanego komentarza",
        slad_s.zapamietane != [], slad_s.zapamietane)
sprawdz("STARY KOD zdejmowal host z listy platnych mimo porazki",
        slad_s.zapomniane_platne != [], slad_s.zapomniane_platne)
# Trzy, nie dwa: stary kod placil jeszcze za ocene martwego hosta, wiec do
# petli wchodzil o jeden cel wiecej — i tez go zaliczal. Nowy kod na tym samym
# scenariuszu melduje 0.
sprawdz("STARY KOD meldowal 3 komentarze, z ktorych nie wszedl ANI JEDEN",
        licznik(wydruk_s) == 3, licznik(wydruk_s))
sprawdz("STARY KOD placil za ocene martwego hosta",
        any(MARTWY in u for u in (slad_s.oceniane[0] if slad_s.oceniane else [])),
        slad_s.oceniane[:1])
sprawdz("STARY KOD nie zapisywal postawy przy dyskusjach",
        all(not k.get("postawa") for k in slad_s.konteksty_dyskusji),
        slad_s.konteksty_dyskusji)

print()
print("=== 6. POMINIECIE NIE JEST WYKONANIEM ===")
# SCENARIUSZ KONTROLERA, odtworzony przez prawdziwe `run.dzien()`. Atrapa
# oddaje to, co produkcja oddaje przy `juz_sie_odezwalismy`:
#     {"wyslane": True, "pominiete": True}
# — czyli sam warunek na `wyslane` to PRZEPUSZCZA. Przed poprawka wychodzilo
# z tego: zapamietane=['https://zywy.example/p/a'],
# zapomniane_platne=['zywy.example'], licznik przebiegu: 1, a dziennik ZERO
# wpisow (`wystaw_komentarz` swiadomie pominiec nie zapisuje). Czyli dokladnie
# ta rozbieznosc podsumowania z pomiarem, ktora ta poprawka miala zamknac.
slad_p, wydruk_p = przebieg(ZRODLO, wyslane=True, pominiete=True,
                            nazwa="run_pominiete")
print("    POMINIETE: proby=%d zapamietane=%s zapomniane=%s licznik=%s"
      % (slad_p.proby_komentarza, slad_p.zapamietane,
         slad_p.zapomniane_platne, licznik(wydruk_p)))

sprawdz("proba jednak byla (test cokolwiek mierzy)",
        slad_p.proby_komentarza >= 1, slad_p.proby_komentarza)
sprawdz("pominiecie NIE liczy sie do normy dnia",
        licznik(wydruk_p) == 0, licznik(wydruk_p))
sprawdz("pominiecie NIE pali publikacji na 4 dni",
        slad_p.zapamietane == [], slad_p.zapamietane)
sprawdz("pominiecie NIE zdejmuje hosta z listy platnych",
        slad_p.zapomniane_platne == [], slad_p.zapomniane_platne)
sprawdz("i jest widoczne w logu, a nie ciche",
        "pominiete" in wydruk_p, wydruk_p[-400:])

# KONTRDOWOD, wycinajacy TYLKO to odciecie — reszta poprawki zostaje, zeby
# bylo widac, ze to ona jedna trzyma ten scenariusz.
bez_odciecia = ZRODLO.replace(
    '                if wynik.get("pominiete"):\n'
    '                    print("  (pominiete — nie licze do normy dnia)",'
    " flush=True)\n                    continue\n", "").replace(
    '                if wynik.get("pominiete") or not wynik.get("wyslane"):\n',
    '                if not wynik.get("wyslane"):\n')
sprawdz("latka odwrotna naprawde cos cofa", bez_odciecia != ZRODLO)
slad_pz, wydruk_pz = przebieg(bez_odciecia, wyslane=True, pominiete=True,
                              nazwa="run_pominiete_stare")
print("    BEZ ODCIECIA: zapamietane=%s zapomniane=%s licznik=%s"
      % (slad_pz.zapamietane, slad_pz.zapomniane_platne, licznik(wydruk_pz)))
sprawdz("KONTRDOWOD: bez odciecia pominiecie palilo publikacje",
        slad_pz.zapamietane != [], slad_pz.zapamietane)
sprawdz("KONTRDOWOD: i zdejmowalo host z listy platnych",
        slad_pz.zapomniane_platne != [], slad_pz.zapomniane_platne)
sprawdz("KONTRDOWOD: i meldowalo wykonana prace, ktorej nie bylo",
        licznik(wydruk_pz) >= 1, licznik(wydruk_pz))

print()
print("=== 7. BLOK `odpowiedzi()` — TA SAMA POPRAWKA, DWA BLOKI WYZEJ ===")
# Ten blok nadal IGNOROWAL wynik `wystaw_odpowiedz_pod_artykulem`
# i `wystaw_odpowiedz`, a `zrobione["odpowiedzi"] += 1` szlo bezwarunkowo.
# Ta sama wada, ktora naprawiono w `komentarze()` i `dyskusje()`.
CZEKAJA = [
    {"autor": "Ktos", "tekst": "Zarzut", "pod_czym": "nasza notka",
     "pod_id": 555, "gdzie": "notka", "kontekst": "nasza notka"},
    {"autor": "Inny", "tekst": "Pytanie", "pod_czym": "nasz artykul",
     "pod_id": 0, "gdzie": "artykul", "kontekst": "artykul",
     "url": "https://nia.substack.com/p/tekst"},
]
slad_o, wydruk_o = przebieg(ZRODLO, wyslane=False, czekajace=CZEKAJA,
                            nazwa="run_odpowiedzi_zle")
print("    NIEUDANE: pod artykulem=%d, licznik odpowiedzi=%s"
      % (slad_o.odpowiedzi_pod_artykulem, licznik(wydruk_o, "odpowiedzi")))
sprawdz("obie drogi odpowiedzi byly probowane (test cokolwiek mierzy)",
        slad_o.odpowiedzi_pod_artykulem >= 1 and slad_o.proby_odpowiedzi >= 1,
        (slad_o.odpowiedzi_pod_artykulem, slad_o.proby_odpowiedzi))
sprawdz("nieudane odpowiedzi NIE licza sie do wyniku",
        licznik(wydruk_o, "odpowiedzi") == 0, licznik(wydruk_o, "odpowiedzi"))

slad_o2, wydruk_o2 = przebieg(ZRODLO, wyslane=True, czekajace=CZEKAJA,
                              nazwa="run_odpowiedzi_ok")
sprawdz("udane odpowiedzi nadal sie licza (obie drogi)",
        licznik(wydruk_o2, "odpowiedzi") == 2, licznik(wydruk_o2, "odpowiedzi"))

slad_o3, wydruk_o3 = przebieg(ZRODLO, wyslane=True, pominiete=True,
                              czekajace=CZEKAJA, nazwa="run_odpowiedzi_pom")
# Pominieta jest tu tylko droga notkowa — `wystaw_odpowiedz_pod_artykulem`
# nie ma sciezki „pominiete", wiec ta druga zalicza sie normalnie.
sprawdz("pominieta odpowiedz nie liczy sie do wyniku",
        licznik(wydruk_o3, "odpowiedzi") == 1, licznik(wydruk_o3, "odpowiedzi"))

print()
print("=== 8. CEL Z `www.` PRZECHODZI PRZEZ SITO TAK SAMO JAK ZAPORA ===")
# Cale twierdzenie o normalizacji stoi na tym, ze sito w `run.dzien` i zapora
# `mozna_komentowac` licza host IDENTYCZNIE: surowe `netloc.lower()`, bez
# zdejmowania `www.`. Nikt tego dotad nie przepuscil zadnym adresem z `www.`.
slad_w, _ = przebieg(ZRODLO, wyslane=True,
                     martwe_hosty=("www.%s" % MARTWY,),
                     nazwa="run_www")
ocena_w = slad_w.oceniane[0] if slad_w.oceniane else []
print("    lista martwych = {'www.%s'},  do oceny poszlo: %s" % (MARTWY, ocena_w))
sprawdz("cel bez `www.` NIE wypada przez wpis z `www.` (sito = zapora)",
        any("https://%s/" % MARTWY in u for u in ocena_w), ocena_w)

slad_w2, wydruk_w2 = przebieg(ZRODLO, wyslane=True, martwe_hosty=(MARTWY,),
                              nazwa="run_www2")
sprawdz("a cel z tym samym hostem co wpis — wypada",
        all(MARTWY not in u for u in (slad_w2.oceniane[0]
                                      if slad_w2.oceniane else [])),
        slad_w2.oceniane[:1])
sprawdz("i log mowi, KTORY host wypadl, nie tylko ile",
        MARTWY in wydruk_w2.split("odsiane hosty bez wejscia komentarza")[-1][:120],
        wydruk_w2.split("odsiane hosty")[-1][:160])

# SEKCJA 9 SKASOWANA 2 wrzesnia 2026. Byla to piatka asercji po TRESCI
# ZRODLA `run.py`, a nie po zachowaniu — z czego najgorsza:
#
#     ZRODLO.index("if martwe:\n                from urllib.parse")
#
# czyli szesnascie spacji wciecia wpisanych w warunek testu. Ta asercja
# oblewala przy przesunieciu bloku o jeden poziom, ktore niczego nie zmienia,
# i przechodzila, gdyby caly odsiew wyladowal w galezi, do ktorej przebieg
# nie dochodzi. Pozostale cztery pilnowaly napisow („wynik = browser.wystaw_...")
# i kolejnosci ich wystapien w PLIKU, a nie w wykonaniu.
#
# Nic z tego nie ginie: sekcje 1-8 uruchamiaja prawdziwe `dzien()` na atrapach
# i mierza to samo ZACHOWANIEM — ze nieudany komentarz nie liczy sie i nic nie
# pali (1), ze udany robi komplet (2), ze potwierdzenie jest brane z
# `potwierdz_*` (3-5), ze martwy host nie dostaje platnej oceny (6-8).

print()
print("=== PRODUKCJA ===")
zle = 0
for p in PILNOWANE:
    t = odcisk(p)
    ok = t == PRZED[str(p)]
    zle += 0 if ok else 1
    print("  %-28s %s" % (pathlib.Path(p).name, "bez zmian" if ok else "ZMIENIONA"))

print()
print("=== WYNIK: %d zdanych, %d oblanych%s ===" %
      (zdane, oblane, ", PRODUKCJA RUSZONA" if zle else ""))
sys.exit(1 if (oblane or zle) else 0)
