# -*- coding: utf-8 -*-
"""Sciezka artykulu z puli ma DOWIEZC tekst, a nie zginac po drodze.

`nia-artykul.service` uruchamia `artykul_z_puli.py --wyslij` w kazdy wtorek
14:00 UTC — to jest jedyna produkcyjna sciezka artykulu; `run.py` juz go nie
prowadzi. Wszystko, co ten plik robi po dyskoverii, jest robione za oplacony
research (okolo 0,40 USD do syntezy, drugie 0,76 na samo pisanie).

CO TU BYLO ZLE, sprawdzone w kodzie 1 wrzesnia 2026:

1. `warto_pisac`, `write` i `review` byly wolane BEZ `try/except`. `run.py`
   opakowuje dokladnie te same trzy wywolania i pisze dlaczego: „Bramka jest
   doradcza. Jej awaria nie moze kosztowac oplaconego researchu". Bramka
   NICZEGO nie blokuje (`gates.verdict` zwraca SAVED zawsze), a mimo to jeden
   `ValueError` z `llm.parse_json` konczyl przebieg bez artykulu. To nie
   hipoteza: `llm.parse_json` dokumentuje ta awarie z 25 sierpnia 2026 —
   „`warto_pisac` padlo na `Extra data: line 1 column 1866`".

2. Werdykt czytano jako `ocena.get("verdict")`, a `stages.warto_pisac` sklada
   go pod kluczem `werdykt`. Klucza `verdict` nie ma ani w kontrakcie
   `prompts/warto_pisac.md` (tam jest `one_line_verdict`), ani w kodzie. Log
   drukowal wiec surowy `repr` calego slownika uciety na 200 znakach, a galaz
   DOLOZ → bank → bibliotekarz nie odpalala sie nigdy.

3. `glebokosc_z_oceny` liczylo filary z surowych `ocena[f]["present"]`, a
   `warto_pisac` czesc z nich uniewaznia i zapisuje wynik OBOK (`przekonanie`,
   `stawka`, `filary`), zostawiajac zagniezdzone `present` jako `True`. Karta
   z werdyktem ODLOZ mogla wiec dostac RICH, czyli cel 1075 slow.

4. Odrzucony przez `uniesie_artykul` fakt nie wracal do puli, mimo ze ekran
   mowil „(fakt zostaje w puli jako material na notke)".

5. `zrodlo_faktu`, `data_zrodla` i `fakt_wyjsciowy` byly przypisywane do briefu
   i nieczytane nigdzie — fakt, ktory uzasadnil wybor tematu, nie docieral ani
   do karty, ani do pisarza, ani do sekcji `## Sources`.

CO BYLO ZLE W SAMYM TYM TESCIE, znalezione kontrola tego samego dnia:

6. SEKCJA 4 NIE DOTYKALA PRODUKCJI. Podmieniala `azp.wybierz_fakt` na stub
   wydajacy kolejne elementy listy i `zwroc_kandydatow` na atrape zbierajaca
   wywolania — wiec dowodzila, ze petla wola to, co wyobrazil sobie autor.
   Prawdziwa para `stages.wez_kandydatow`/`stages.zwroc_kandydatow` nie byla
   ruszana ANI RAZU i przepuscila regres: oddanie faktu do puli WEWNATRZ petli
   odwracalo jego status przed kolejnym wyborem, a sortowanie jest
   deterministyczne po `(not z_kanalu, ranga)`, wiec petla brala CZTERY RAZY
   TEN SAM fakt, drukujac „-- proba N: nastepny fakt --". Sekcja 4 chodzi teraz
   po prawdziwej parze, na indeksie w katalogu tymczasowym.

7. DWIE ASERCJE PO TRESCI ZRODLA. `"stages.zwroc_kandydatow([fakt])" in ZRODLO`
   i `'c.get("url") for c in card.get("confirmed_claims", [])' in _st` —
   dokladnie ten wzorzec, ktory przepuscil wade numer 6: test odwzorowywal
   napis w pliku zamiast skutku. Obie usuniete; sekcja `## Sources` jest teraz
   sprawdzana przez wywolanie PRAWDZIWEGO `stages.save` na bazie i katalogu
   tymczasowym i przeczytanie zapisanego pliku.

8. WSTRZYKNIETY FAKT ROZBRAJAL DWIE BRAMKI. Wchodzil do `confirmed_claims` bez
   znacznika, wiec `gates.szerokosc_podstawy` liczyla host, ktorego nikt nie
   pobral (`WASKA_PODSTAWA` milkla), a `gates.numbers_outside_corpus` bierze
   korpus z `json.dumps(card)`, wiec liczby z tego faktu stawaly sie „obecne
   w materiale dowodowym". Sekcje 5a i 5b pilnuja obu.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_artykul_nie_ginie_po_drodze.py
"""
import contextlib
import io
import pathlib
import sys

sys.path.insert(0, "agent-v2")

import config            # noqa: E402
import artykul_z_puli as azp   # noqa: E402

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


BRIEF = {
    "title": "Annotators Under Contract",
    "question": "Who set the rate that annotators are paid?",
    "broken_belief": "Everyone assumes the labels come from the model itself.",
    "why_they_believe_it": "Because nobody names the people who wrote them.",
    "sub_questions": ["Who decides the rate?", "Where else does it run?"],
    "second_act": "The Assembly struck the clause from the bill before enactment.",
    "beyond_one_place": "The same arrangement runs in three other jurisdictions.",
    "fakt_wyjsciowy": "Kenya is drafting a law binding OpenAI, Meta and "
                      "Anthropic to its labour standards; annotators earn "
                      "1.46-3.74 USD per hour.",
    "zrodlo_faktu": "https://example.org/kenya-annotators",
    "data_zrodla": "2026-08-25",
}

KARTA = {
    "working_thesis": "Somebody set that rate on purpose.",
    "confirmed_claims": [{"claim": "A committee set the rate.",
                          "evidence": "minutes", "url": "https://inny.example/a"}],
    "citable_numbers": [{"value": "3", "means": "members"}],
}

DRAFT = {"title": "Annotators Under Contract",
         "subtitle": "Who set the rate",
         "body": "A committee set the rate in a room nobody photographed. "
                 "The minutes are public and the names are in them. " * 12}


def ocena_pelna(**nadpisz):
    """Odpowiedz `warto_pisac` w KSZTALCIE, w jakim ta funkcja ja naprawde oddaje.

    Zagniezdzone bloki od modelu ORAZ pola dolozone przez kod obok nich —
    i to wlasnie ta para byla zrodlem wady numer 3.
    """
    o = {
        "contradicted_belief": {"present": True,
                                "the_belief": "labels come from the model itself"},
        "named_decider": {"present": True},
        "felt_number": {"present": True},
        "second_domain": {"present": True},
        "unsettled_outcome": {"present": True, "the_question": "who pays next"},
        "przekonanie": True,
        "stawka": True,
        "filary": {"named_decider": True, "felt_number": True,
                   "second_domain": True},
        "ile_filarow": 3,
        "werdykt": "PISZ",
        "powod": "zlamane przekonanie + 3 z 3 filarow",
    }
    o.update(nadpisz)
    return o


class AtrapaStages:
    """Udaje `stages` na tyle, na ile uzywa go sciezka artykulu.

    Kazde wywolanie zapisuje slad — test pyta o SKUTEK (czy tekst powstal,
    czy sie zapisal, z jaka glebokoscia), a nie o to, czy cos zostalo wolane.
    """

    # Stopka z data idzie do PRAWDZIWEGO `stages` — jest czysta (bez sieci,
    # modelu i bazy), a atrapowanie jej zamienialoby test w sprawdzanie wlasnej
    # atrapy. To ta jedna linijka blokowala trzy artykuly z rzedu.
    # Import w srodku, bo `sys.path` do `agent-v2` ustawia sie nizej w pliku.
    @staticmethod
    def wstaw_date_zrodel(tekst, card):
        import stages as _s
        return _s.wstaw_date_zrodel(tekst, card)

    def __init__(self):
        self.slad = []
        self.glebokosci = []
        self.zapisane = []
        self.oddane_do_puli = []
        self.karty_pisarza = []
        self.bank_wolany = 0
        self.padaj_na = set()
        self.ocena = ocena_pelna()
        self.pisarz_pada_ile_razy = 0

    # --- bramka doradcza ---------------------------------------------------
    def warto_pisac(self, conn, run_id, card):
        self.slad.append("warto_pisac")
        if "warto_pisac" in self.padaj_na:
            raise ValueError("Extra data: line 1 column 1866")
        return self.ocena

    def bank_fragmentow(self, conn, dni=0):
        self.bank_wolany += 1
        return [{"excerpt": "cos oplaconego i nieprzeczytanego"}]

    def bibliotekarz(self, conn, run_id, bank):
        self.slad.append("bibliotekarz")
        if "bibliotekarz" in self.padaj_na:
            raise ValueError("bibliotekarz nie oddal JSON-a")
        return {"groups": [{"dziedziny": ["prawo", "trening modeli"],
                            "mechanism": "ten sam zegar liczy termin"}]}

    # --- pisarz i recenzent ------------------------------------------------
    def write(self, conn, run_id, card, glebokosc):
        self.slad.append("write")
        self.glebokosci.append(glebokosc)
        self.karty_pisarza.append(card)
        if self.pisarz_pada_ile_razy > 0:
            self.pisarz_pada_ile_razy -= 1
            raise RuntimeError("pisarz odmowil")
        return dict(DRAFT)

    def review(self, conn, run_id, card, draft):
        self.slad.append("review")
        if "review" in self.padaj_na:
            raise ValueError("brak JSON w odpowiedzi")
        return {"sentences": [], "unsupported_facts": [], "summary": "ok"}

    def ocen_forme(self, conn, run_id, draft):
        return {}

    # --- reszta lancucha ---------------------------------------------------
    def poprzednie_teksty(self, pomin_tresc=""):
        return []

    def swiezosc_karty(self, card):
        return []

    def save(self, conn, run_id, brief, card, draft, status, blokada, notatki):
        self.slad.append("save")
        self.zapisane.append({"brief": brief, "card": card, "draft": draft,
                              "status": status, "notatki": notatki})
        return "data/artykuly/9999-test.md"

    def grafika(self, conn, run_id, draft, sciezka_artykulu=""):
        self.slad.append("grafika")

    def zwroc_kandydatow(self, kandydaci):
        self.oddane_do_puli.extend(kandydaci)
        return len(kandydaci)

    # --- research (uzywane tylko w sekcji 5) --------------------------------
    def discovery(self, conn, run_id, pytanie, recent):
        return [{"url": "https://example.org/a"}]

    def fetch(self, conn, run_id, sources):
        return [{"url": "https://example.org/%d" % i, "text": "tresc"}
                for i in range(4)]

    def classify(self, conn, run_id, pytanie, corpus):
        return []

    def synthesis(self, conn, run_id, pytanie, evidence):
        import copy
        return copy.deepcopy(KARTA)


class AtrapaDb:
    @staticmethod
    def recent_domains(conn, ile):
        return []


def uruchom_napisz(atrapa, brief=None, card=None):
    """Wola `_napisz_i_zapisz` na atrapach i oddaje (kod, wydruk)."""
    import copy
    stary = azp.stages
    stary_model = config.MODEL_FOR.get("write")
    azp.stages = atrapa
    bufor = io.StringIO()
    try:
        with contextlib.redirect_stdout(bufor):
            kod = azp._napisz_i_zapisz(None, 1,
                                       copy.deepcopy(brief or BRIEF),
                                       copy.deepcopy(card or KARTA))
    finally:
        azp.stages = stary
        config.MODEL_FOR["write"] = stary_model
    return kod, bufor.getvalue()


print("=== 1. AWARIA DORADCZEJ BRAMKI NIE KASUJE OPLACONEGO RESEARCHU ===")
# `gates.verdict` zwraca SAVED zawsze — bramka ciekawosci niczego nie blokuje.
# Etap, ktory nic nie blokuje, nie ma prawa kosztowac artykulu.
a = AtrapaStages()
a.padaj_na = {"warto_pisac"}
kod, wydruk = uruchom_napisz(a)
sprawdz("przebieg konczy sie kodem 0", kod == 0, kod)
sprawdz("pisarz mimo to napisal", "write" in a.slad, a.slad)
sprawdz("artykul sie zapisal", "save" in a.slad, a.slad)
sprawdz("i wydruk mowi wprost, ze bramka padla",
        "[awaria]" in wydruk and "bramka" in wydruk, wydruk[-300:])
# Po awarii bramki nie wiemy o materiale NIC — i to nie znaczy THIN (420 slow,
# „material na dwa zdania"), ani RICH (1075 slow, najdluzsza forma).
sprawdz("glebokosc po awarii bramki to srodkowe pasmo",
        a.glebokosci == [azp.GLEBOKOSC_BEZ_OCENY] == ["SINGLE"], a.glebokosci)

a = AtrapaStages()
a.padaj_na = {"review"}
kod, wydruk = uruchom_napisz(a)
sprawdz("awaria recenzji tez nie kasuje gotowego tekstu",
        kod == 0 and "save" in a.slad, (kod, a.slad))
sprawdz("a w notatkach zostaje slad, ze nie rozliczono zdan",
        any("niedostepna" in str(n) for n in a.zapisane[0]["notatki"]),
        a.zapisane[0]["notatki"])

a = AtrapaStages()
a.pisarz_pada_ile_razy = 1
kod, wydruk = uruchom_napisz(a)
sprawdz("pisarz padl raz — powtorka na Opusie dowozi tekst",
        kod == 0 and "save" in a.slad, (kod, a.slad))
sprawdz("i powtorka poszla na sprawdzonego pisarza tego potoku",
        config.CLAUDE in wydruk, wydruk[-300:])

# KONTRDOWOD: oslona ma byc waska, nie polykac wszystkiego. Gdy pisarz padnie
# TAKZE na powtorce, nie ma artykulu — i przebieg MUSI to pokazac wyjatkiem,
# a nie zwrocic 0 z pusta szuflada. `main` zamyka wtedy przebieg jako ERROR.
a = AtrapaStages()
a.pisarz_pada_ile_razy = 2
try:
    uruchom_napisz(a)
    poleclo = False
except RuntimeError:
    poleclo = True
sprawdz("KONTRDOWOD: dwa razy padly pisarz leci wyjatkiem, nie cichym zerem",
        poleclo and "save" not in a.slad, a.slad)

print()
print("=== 2. WERDYKT SIEDZI POD `werdykt`, NIE POD `verdict` ===")
# Kontrakt `warto_pisac.md` oddaje `one_line_verdict`; wlasciwy werdykt sklada
# KOD i zapisuje po polsku. Stara linia czytala `verdict` — zawsze None.
a = AtrapaStages()
a.ocena = ocena_pelna(werdykt="DOLOZ", ile_filarow=1,
                      filary={"named_decider": True, "felt_number": False,
                              "second_domain": False},
                      powod="tylko 1 z 3 filarow",
                      verdict="PISZ")  # pulapka: klucz, ktorego kod czytal
kod, wydruk = uruchom_napisz(a)
sprawdz("wydruk pokazuje werdykt kodu (DOLOZ), nie pulapke (PISZ)",
        "DOLOZ" in wydruk and "werdykt: PISZ" not in wydruk,
        [w for w in wydruk.splitlines() if "werdykt" in w])
sprawdz("i nie drukuje juz surowego slownika",
        "'contradicted_belief'" not in wydruk,
        [w for w in wydruk.splitlines() if "werdykt" in w])
# TO JEST MOMENT, DLA KTOREGO BANK ISTNIEJE — cytat z `run.py`. Sciezka z puli
# nie miala tej galezi wcale, wiec DOLOZ szedl do pisarza tak samo jak PISZ.
sprawdz("DOLOZ siega do banku po pare", a.bank_wolany == 1, a.bank_wolany)
sprawdz("i doklada mechanizm do karty pisarza",
        any(m.get("z_banku") for m in
            (a.karty_pisarza[0].get("parallel_mechanisms") or [])),
        a.karty_pisarza[0].get("parallel_mechanisms"))

# KONTRDOWOD: przy PISZ bank ma MILCZEC. Inaczej „galaz" nie jest galezia,
# tylko kolejnym stalym kosztem — bibliotekarz to wywolanie modelu.
a = AtrapaStages()
a.ocena = ocena_pelna(werdykt="PISZ")
kod, wydruk = uruchom_napisz(a)
sprawdz("KONTRDOWOD: przy PISZ bank nie jest ruszany",
        a.bank_wolany == 0 and "bibliotekarz" not in a.slad, a.slad)

# Gdy padnie DOPIERO bibliotekarz, ocena juz istnieje i filary sa policzone.
# Kasowanie jej razem z awaria banku zeslaloby bogaty material na 650 slow.
a = AtrapaStages()
a.ocena = ocena_pelna(werdykt="DOLOZ")
a.padaj_na = {"bibliotekarz"}
kod, wydruk = uruchom_napisz(a)
sprawdz("awaria banku nie kasuje policzonych juz filarow",
        kod == 0 and a.glebokosci == ["RICH"], (kod, a.glebokosci))

print()
print("=== 3. GLEBOKOSC Z WERDYKTU KODU, NIE Z SUROWYCH `present` ===")
# `warto_pisac` uniewaznia przekonanie, ktorego model nie umial nazwac, i
# stawke bez spisanej reguly — ale robi to w SWOICH polach, zostawiajac
# zagniezdzone `present` jako True. Liczenie surowych pol dawalo 4 filary
# (RICH, cel 1075 slow) karcie, ktora ten sam kod odlozyl.
odlozona = ocena_pelna(
    przekonanie=False, stawka=False,
    filary={"named_decider": True, "felt_number": True, "second_domain": False},
    ile_filarow=2, werdykt="ODLOZ")
sprawdz("karta ODLOZ dostaje SINGLE, nie RICH",
        azp.glebokosc_z_oceny(odlozona) == "SINGLE",
        azp.glebokosc_z_oceny(odlozona))
# KONTRDOWOD, ZE ROZBIEZNOSC BYLA PRAWDZIWA: te same zagniezdzone bloki bez
# pol kodu licza sie po staremu na cztery filary, czyli RICH.
surowa = {k: v for k, v in odlozona.items()
          if k not in ("przekonanie", "stawka", "filary", "ile_filarow")}
sprawdz("KONTRDOWOD: same pola modelu daja RICH — stad brala sie usterka",
        azp.glebokosc_z_oceny(surowa) == "RICH", azp.glebokosc_z_oceny(surowa))
sprawdz("pelna ocena PISZ nadal daje RICH",
        azp.glebokosc_z_oceny(ocena_pelna()) == "RICH")
# Ocena bez pol kodu (np. wczytana z zapisanej karty) ma dzialac po staremu.
sprawdz("stary ksztalt oceny nadal liczy sie z `present`",
        azp.glebokosc_z_oceny(
            {"contradicted_belief": {"present": True},
             "named_decider": {"present": True},
             "felt_number": {"present": True},
             "second_domain": {"present": True},
             "unsettled_outcome": {"present": True}}) == "RICH")

print()
print("=== 4. PETLA NASTEPNEGO FAKTU NAPRAWDE BIERZE NASTEPNY ===")
# DWA CELE NARAZ, I POPRZEDNIA WERSJA MIALA TYLKO JEDEN.
#
# Cel pierwszy: odrzucony fakt nie moze zginac z puli na zawsze — jest dobrym
# materialem na notke, tylko nie unosi tysiaca slow. `wez_kandydatow` znaczy
# jako uzyte wszystko, co wyda, wiec bez jawnego oddania kazdy nieudany
# przebieg palil do czterech oplaconych kandydatur.
#
# Cel drugi: petla ma probowac KOLEJNYCH faktow. Poprzednia poprawka oddawala
# fakt do puli WEWNATRZ petli — a `wez_kandydatow` sortuje deterministycznie po
# `(not z_kanalu, ranga)` i `zwroc_kandydatow` nie rusza ani rangi, ani pozycji
# w indeksie. Oddany wracal wiec na to samo miejsce i byl wybierany ponownie.
#
# TEN TEST CHODZI PO PRAWDZIWEJ PARZE `stages.wez_kandydatow` /
# `stages.zwroc_kandydatow`, na indeksie w katalogu tymczasowym. Poprzednia
# wersja podmieniala `azp.wybierz_fakt` na stub wydajacy kolejne elementy listy
# i `zwroc_kandydatow` na atrape zbierajaca wywolania — wiec odwzorowywala
# WYOBRAZENIE wywolania i przepuscila wade, ktora siedziala w prawdziwym
# sortowaniu.
import datetime as _dt      # noqa: E402
import json as _js          # noqa: E402
import tempfile as _tmp     # noqa: E402

import stages as _stages    # noqa: E402

_DALEKO = (_dt.datetime.now(_dt.timezone.utc)
           + _dt.timedelta(days=30)).strftime("%Y-%m-%d %H:%M")

# TEST NIE MOZE ZALEZEC OD DZISIEJSZEJ DATY. `kiedy` odpowiada za granice epoki
# (material sprzed przestawienia konta odpada), `wazny_do` jest zawsze w
# przyszlosci, bo ten blok nie bada przeterminowania. Bombe zegarowa tej samej
# klasy — `kiedy` + BANK_MAKS_DNI wypadajace dokladnie dzis — `test_indeks_
# kandydatow.py` zaliczyl 1 wrzesnia 2026.
FAKTY_INDEKSU = [
    "A committee in Nairobi fixed the hourly rate paid to data annotators.",
    "Palantir Maven produced one target every 86 seconds during a NATO drill.",
    "Cambridge auditors found four of thirty agents publish a safety card.",
    "Stanford measured employment of young workers below trend in exposed jobs.",
    "Human raters reward agreement, and that is where sycophancy comes from.",
    "A court in Seoul ruled scraped lyrics were not covered by fair dealing.",
    "Chile requires public bodies to log every automated refusal of a benefit.",
    "An insurer priced premiums from telematics without telling policyholders.",
]


def zasiej_indeks(katalog):
    """Osmiu kandydatow, `ranga` 0-7 — czyli kolejnosc, ktora kod naprawde bierze."""
    _stages.INDEKS_KANDYDATOW = katalog / "indeks.json"
    _stages.INDEKS_KANDYDATOW.write_text(_js.dumps([
        {"fact": f, "status": "nowy", "url": "https://zrodlo%d.example/a" % i,
         "source_date": "2026-08-20", "ranga": i, "z_kanalu": False,
         "kiedy": config.DATA_PRZESTAWIENIA + "T10:00:00+00:00",
         "wazny_do": _DALEKO}
        for i, f in enumerate(FAKTY_INDEKSU)], ensure_ascii=False),
        encoding="utf-8")


def stany_indeksu():
    return {k["fact"]: k["status"]
            for k in _js.loads(
                _stages.INDEKS_KANDYDATOW.read_text(encoding="utf-8"))}


class StagesZIndeksem(AtrapaStages):
    """Atrapa reszty lancucha, ale PRAWDZIWA para wez/zwroc na indeksie."""

    # `wybierz_fakt` siega po te trzy: pamiec kolizji jest pusta, zeby test
    # mierzyl kolejnosc brania, a nie odsiew powtorek.
    POWTORKA_TEMATU = _stages.POWTORKA_TEMATU
    _o_tym_samym = staticmethod(_stages._o_tym_samym)

    def tematy_do_porownania(self, conn):
        return []

    def ostatnie_notki(self, ile):
        return []

    def __init__(self):
        super().__init__()
        # NAJPIERW SPIZARNIA, DOPIERO POTEM ZAKUPY. Liczymy zejscia do platnego
        # szukania: jedno wywolanie `curiosity` to 18 wyszukiwan i 0,127 USD.
        self.szukania = 0

    def znajdz_ciekawostki(self, conn, run_id, ile=8):
        self.szukania += 1
        return []

    def wez_kandydatow(self, ile=1):
        return _stages.wez_kandydatow(ile)

    def zwroc_kandydatow(self, kandydaci):
        self.oddane_do_puli.extend(kandydaci)
        return _stages.zwroc_kandydatow(kandydaci)


def przebieg_na_indeksie(brief_z_faktu, przed_startem=None):
    """`_przebieg --tylko-temat` na prawdziwym indeksie: bez researchu i pisarza.

    Oddaje takze liste faktow, ktore petla NAPRAWDE wzięła — zbierana w
    `temat_z_faktu`, czyli w jedynym miejscu wołanym raz na próbę. Liczenie ich
    po `zwroc_kandydatow` byłoby myleniem dwóch rzeczy: `wybierz_fakt` oddaje
    tam także siedmiu NIEWYBRANYCH z każdej partii.
    """
    kat = pathlib.Path(_tmp.mkdtemp())
    zasiej_indeks(kat)
    if przed_startem:
        przed_startem()
    a = StagesZIndeksem()
    wybrane = []
    stary_stages, stary_db = azp.stages, azp.db
    stary_temat = azp.temat_z_faktu
    stare_argv = sys.argv
    azp.stages, azp.db = a, AtrapaDb

    def temat(conn, run_id, fakt):
        wybrane.append(fakt["fact"])
        return brief_z_faktu(fakt)

    azp.temat_z_faktu = temat
    sys.argv = ["test", "--tylko-temat"]
    bufor = io.StringIO()
    try:
        with contextlib.redirect_stdout(bufor):
            kod = azp._przebieg(None, 1)
    finally:
        azp.stages, azp.db = stary_stages, stary_db
        azp.temat_z_faktu = stary_temat
        sys.argv = stare_argv
    return kod, a, wybrane, bufor.getvalue()


_stary_indeks = _stages.INDEKS_KANDYDATOW
try:
    # Zaden fakt nie unosi artykulu: brak drugiego aktu i brak zasiegu.
    # `_przebieg` probuje wiec czterech po kolei.
    kod, a, wziete, wydruk = przebieg_na_indeksie(
        lambda fakt: dict(BRIEF, second_act="", beyond_one_place="",
                          fakt_wyjsciowy=fakt["fact"]))
    sprawdz("przebieg bez tematu konczy sie kodem 1", kod == 1, kod)
    sprawdz("cztery proby wzialy CZTERY ROZNE fakty",
            len(wziete) == 4 and len(set(wziete)) == 4,
            [f[:40] for f in wziete])
    sprawdz("i wzialy je w kolejnosci rangi, czyli od najmocniejszego",
            wziete == FAKTY_INDEKSU[:4], [f[:40] for f in wziete])
    sprawdz("indeks wystarczyl — zero platnych szukan", a.szukania == 0,
            a.szukania)
    # Cel pierwszy: po petli WSZYSTKIE cztery leza z powrotem w puli.
    stany = stany_indeksu()
    sprawdz("wszystkie cztery odrzucone leza w indeksie jako `nowy`",
            all(stany[f] == "nowy" for f in wziete),
            {f[:30]: stany[f] for f in wziete})
    sprawdz("czyli caly indeks jest wolny — nic nie splonelo",
            set(stany.values()) == {"nowy"}, stany)
    sprawdz("ekran nadal obiecuje to samo, co kod robi",
            "zostaje w puli" in wydruk and "wroci do niej po zakonczeniu prob"
            in wydruk, wydruk[:400])

    # KONTRDOWOD DO CELU DRUGIEGO — I TO ON JEST TU NAJWAZNIEJSZY.
    # Powtarzamy STARY ksztalt: oddanie do puli WEWNATRZ petli, na tej samej
    # prawdziwej parze i tym samym indeksie. Zmierzone:
    #     z oddaniem w petli:  Nairobi | Nairobi | Nairobi
    #     bez oddania w petli: Nairobi | Palantir | Cambridge
    # Czyli cztery oplacone wywolania `temat_z_faktu` na jednym fakcie i
    # kandydaci 2-8 nietknieci, przy ekranie drukujacym „nastepny fakt".
    def trzy_proby(oddawaj_w_petli):
        kat = pathlib.Path(_tmp.mkdtemp())
        zasiej_indeks(kat)
        stary = azp.stages
        azp.stages = StagesZIndeksem()
        wybrane = []
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                for _ in range(3):
                    f = azp.wybierz_fakt(None, 1)
                    wybrane.append(f["fact"])
                    if oddawaj_w_petli:
                        _stages.zwroc_kandydatow([f])
        finally:
            azp.stages = stary
        return wybrane

    ze_starym = trzy_proby(True)
    z_nowym = trzy_proby(False)
    sprawdz("KONTRDOWOD: stary ksztalt bral TEN SAM fakt trzy razy",
            len(set(ze_starym)) == 1, [f[:30] for f in ze_starym])
    sprawdz("KONTRDOWOD: a bez oddania w petli sa trzy rozne",
            len(set(z_nowym)) == 3, [f[:30] for f in z_nowym])

    # KONTRDOWOD: fakt, ktory UNIESIE artykul, nie moze wrocic do puli — jest
    # wlasnie uzywany. Oddanie go znaczyloby, ze ten sam temat wyjdzie drugi raz.
    kod, a, wziete, wydruk = przebieg_na_indeksie(
        lambda fakt: dict(BRIEF, fakt_wyjsciowy=fakt["fact"]))
    stany = stany_indeksu()
    sprawdz("KONTRDOWOD: przyjety fakt zostaje `uzyty`, nie wraca",
            kod == 0 and wziete == [FAKTY_INDEKSU[0]]
            and stany[FAKTY_INDEKSU[0]] == "uzyty",
            (kod, [f[:30] for f in wziete], stany[FAKTY_INDEKSU[0]]))
    sprawdz("a siedmiu niewybranych wrocilo do puli",
            sum(1 for s in stany.values() if s == "nowy") == 7, stany)

    # Pula wysycha w polowie petli: to, co juz odrzucilismy, i tak ma wrocic.
    # Bez tego wyjatek kasuje oplacone kandydatury po cichu — a wysychajaca
    # pula to nie hipoteza, tylko normalny koniec tygodnia w banku.
    def zostaw_dwoch():
        indeks = _js.loads(_stages.INDEKS_KANDYDATOW.read_text(encoding="utf-8"))
        for k in indeks[2:]:
            k["status"] = "odrzucony"
        _stages.INDEKS_KANDYDATOW.write_text(
            _js.dumps(indeks, ensure_ascii=False), encoding="utf-8")

    kod, a, wziete, wydruk = przebieg_na_indeksie(
        lambda fakt: dict(BRIEF, second_act="", beyond_one_place="",
                          fakt_wyjsciowy=fakt["fact"]),
        przed_startem=zostaw_dwoch)
    stany = stany_indeksu()
    sprawdz("pusta pula w polowie petli — odrzuceni i tak wracaja",
            kod == 1 and wziete == FAKTY_INDEKSU[:2]
            and sum(1 for s in stany.values() if s == "nowy") == 2,
            (kod, [f[:30] for f in wziete], stany))
    sprawdz("i dopiero wtedy sciezka siega po platne szukanie",
            a.szukania == 1, a.szukania)
finally:
    _stages.INDEKS_KANDYDATOW = _stary_indeks

print()
print("=== 5. FAKT WYJSCIOWY DOCIERA WSZEDZIE, ALE NIE ROZBRAJA BRAMEK ===")
# Trzy pola briefu (`fakt_wyjsciowy`, `zrodlo_faktu`, `data_zrodla`) byly
# przypisywane i nieczytane nigdzie — a komentarz w kodzie twierdzil, ze pisarz
# widzi fakt „razem z reszta dowodow". Pisarz widzi WYLACZNIE `card_json`.
#
# DRUGA POLOWA TEJ SEKCJI JEST NOWA i pilnuje ceny tamtej naprawy. Fakt z puli
# to wypowiedz modelu z `znajdz_ciekawostki` z doklejonym URL-em — nikt tej
# strony nie pobral. Wpuszczony do `confirmed_claims` bez znacznika rozbrajal
# dwie bramki deterministyczne naraz: `szerokosc_podstawy` liczyla host, ktorego
# nikt nie pobral, a `numbers_outside_corpus` bierze korpus z `json.dumps(card)`.
import gates as _gates    # noqa: E402

FAKT_Z_PULI = {
    "fact": BRIEF["fakt_wyjsciowy"],
    "url": BRIEF["zrodlo_faktu"],
    "source_date": BRIEF["data_zrodla"],
    "actually": "The rate is set in the vendor contract, not by the platform.",
    "control_fact": "The bill was still in committee as of 25 August 2026.",
}


def przebieg_do_karty(brief, karta=None, fakt=None):
    """Puszcza `_przebieg` do konca researchu i lapie karte dla pisarza."""
    import copy
    a = AtrapaStages()
    if karta is not None:
        a.synthesis = lambda conn, run_id, pytanie, evidence: copy.deepcopy(karta)
    zlapane = {}
    stary_stages, stary_db = azp.stages, azp.db
    stary_wybierz, stary_temat = azp.wybierz_fakt, azp.temat_z_faktu
    stary_pisz = azp._napisz_i_zapisz
    stare_argv = sys.argv
    azp.stages, azp.db = a, AtrapaDb
    _rekord = dict(fakt or FAKT_Z_PULI,
                   fact=brief["fakt_wyjsciowy"], url=brief["zrodlo_faktu"],
                   source_date=brief["data_zrodla"])
    azp.wybierz_fakt = lambda conn, run_id: dict(_rekord)
    azp.temat_z_faktu = lambda conn, run_id, f: dict(brief)

    def lap(conn, run_id, b, c):
        zlapane["brief"], zlapane["card"] = b, c
        return 0

    azp._napisz_i_zapisz = lap
    sys.argv = ["test"]
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            azp._przebieg(None, 1)
    finally:
        azp.stages, azp.db = stary_stages, stary_db
        azp.wybierz_fakt, azp.temat_z_faktu = stary_wybierz, stary_temat
        azp._napisz_i_zapisz = stary_pisz
        sys.argv = stare_argv
    return zlapane.get("card") or {}


karta = przebieg_do_karty(BRIEF)
twierdzenia = karta.get("confirmed_claims") or []
wstrzykniete = next((c for c in twierdzenia
                     if c.get("url") == BRIEF["zrodlo_faktu"]), None)
sprawdz("fakt wyjsciowy jest w karcie jako potwierdzone twierdzenie",
        any(BRIEF["fakt_wyjsciowy"][:40] in str(c.get("claim")) for c in twierdzenia),
        twierdzenia)
sprawdz("z URL-em, ktory ten temat uzasadnil", wstrzykniete is not None,
        [c.get("url") for c in twierdzenia])
sprawdz("dowod z korpusu nie zostal wyparty, tylko dolaczony",
        any(c.get("url") == "https://inny.example/a" for c in twierdzenia),
        [c.get("url") for c in twierdzenia])

# CYTAT NIE MOZE BYC KOPIA TWIERDZENIA. To jedyne twierdzenie w karcie, ktorego
# „cytat" nie jest wyciagiem ze zrodla — czyli dokladnie wzorzec, przed ktorym
# stoi regula `MUST CARRY THE WHOLE CLAIM` w `synteza.md`. Rekord z puli niesie
# osobne zdanie (`control_fact`, w drugiej kolejnosci `actually`) i to ono
# idzie jako `evidence`.
sprawdz("cytat nie jest kopia twierdzenia",
        bool(wstrzykniete) and wstrzykniete["evidence"] != wstrzykniete["claim"],
        wstrzykniete)
sprawdz("i jest tym zdaniem, ktore rekord naprawde niesie",
        wstrzykniete["evidence"] == FAKT_Z_PULI["control_fact"],
        wstrzykniete["evidence"])
karta_bez = przebieg_do_karty(BRIEF, fakt=dict(FAKT_Z_PULI, control_fact=""))
_bez = karta_bez["confirmed_claims"][0]
sprawdz("bez dokumentu kontrolnego cytatem jest `actually`",
        _bez["evidence"] == FAKT_Z_PULI["actually"], _bez["evidence"])

# ZNACZNIK, KTORY BRAMKI CZYTAJA — a nie kolejne martwe pole.
# `z_puli_ciekawostek` mialo w calym repo jedno wystapienie: swoje wlasne
# przypisanie. `source_date` w twierdzeniu tak samo — `swiezosc_karty` czyta
# wylacznie `card["source_dates"]`.
sprawdz("wstrzykniete twierdzenie jest oznaczone jako niepobrane",
        wstrzykniete.get("not_fetched") is True, wstrzykniete)
sprawdz("i nie niesie juz pol, ktorych nikt nie czytal",
        "z_puli_ciekawostek" not in wstrzykniete
        and "source_date" not in wstrzykniete, wstrzykniete)

print()
print("--- 5a. bramka WASKA_PODSTAWA znowu widzi jedno zrodlo ---")
# Artykul 0020 („The Fossil of a Vote") mial pod soba JEDEN odnosnik i to on
# jest powodem istnienia tej uwagi. Dolozony host robil z jednego dwa.
ile, hosty = _gates.szerokosc_podstawy(karta)
sprawdz("host, ktorego nikt nie pobral, nie liczy sie do szerokosci",
        (ile, hosty) == (1, ["inny.example"]), (ile, hosty))
uwagi = _gates.deterministic_floors(DRAFT["body"], karta)
sprawdz("wiec WASKA_PODSTAWA odzywa sie tak jak powinna",
        any(u["gate"] == "WASKA_PODSTAWA" for u in uwagi),
        [u["gate"] for u in uwagi])
# KONTRDOWOD: gdy POBRANE zrodla sa dwa, uwagi nie ma — inaczej bramka
# krzyczalaby na kazdym artykule z tej sciezki i nauczylaby siebie ignorowac.
karta_szeroka = przebieg_do_karty(BRIEF, karta=dict(
    KARTA, confirmed_claims=[
        {"claim": "A committee set the rate.", "evidence": "minutes",
         "url": "https://inny.example/a"},
        {"claim": "The vendor confirmed it.", "evidence": "letter",
         "url": "https://drugi.example/b"}]))
sprawdz("KONTRDOWOD: dwa pobrane hosty — uwagi nie ma",
        not any(u["gate"] == "WASKA_PODSTAWA"
                for u in _gates.deterministic_floors(DRAFT["body"], karta_szeroka)),
        _gates.szerokosc_podstawy(karta_szeroka))

print()
print("--- 5b. liczba z faktu z puli idzie pod WLASNA uwage ---")
# Liczba stad NIE jest zmyslona: rekord ma URL, date i przeszedl bramke
# swiezosci. Nie ma jej jednak w niczym, co pobralismy. Wpuszczenie jej do
# korpusu uciszalo kontrole, a `LICZBA_SPOZA_KORPUSU` na niej klamalaby.
TEKST_Z_LICZBA = ("Annotators are paid 1.46 USD per hour under that contract. "
                  "The committee met again before it agreed. " * 6)
uwagi = _gates.deterministic_floors(TEKST_Z_LICZBA, karta)
nazwy = [u["gate"] for u in uwagi]
sprawdz("liczba z faktu z puli dostaje uwage LICZBA_TYLKO_Z_PULI",
        "LICZBA_TYLKO_Z_PULI" in nazwy, nazwy)
sprawdz("i nie jest nazwana zmyslona",
        not any(u["gate"] == "LICZBA_SPOZA_KORPUSU" and "1.46" in u["detail"]
                for u in uwagi), [u["detail"] for u in uwagi])
# KONTRDOWOD 1: liczba, ktorej nie ma NIGDZIE, nadal jest zmyslona.
uwagi_zmyslone = _gates.deterministic_floors(
    "The rate rose to 91.7 USD per hour overnight. " * 8, karta)
sprawdz("KONTRDOWOD: liczba spoza wszystkiego nadal jest LICZBA_SPOZA_KORPUSU",
        any(u["gate"] == "LICZBA_SPOZA_KORPUSU" and "91.7" in u["detail"]
            for u in uwagi_zmyslone), [u["detail"] for u in uwagi_zmyslone])
# KONTRDOWOD 2: liczba z POBRANEGO twierdzenia nie daje zadnej uwagi.
karta_z_liczba = przebieg_do_karty(dict(BRIEF, fakt_wyjsciowy="A committee met."),
                                   karta=dict(KARTA, confirmed_claims=[
                                       {"claim": "The committee met 4 times.",
                                        "evidence": "minutes say 4",
                                        "url": "https://inny.example/a"}]))
uwagi_pobrane = _gates.deterministic_floors(
    "The committee met 4 times before it agreed. " * 8, karta_z_liczba)
sprawdz("KONTRDOWOD: liczba z pobranego twierdzenia milczy",
        not any(u["gate"].startswith("LICZBA") for u in uwagi_pobrane),
        [u["detail"] for u in uwagi_pobrane if u["gate"].startswith("LICZBA")])

print()
print("--- 5c. data faktu wazy, ale tylko w strone ostrzezenia ---")
# `stages.swiezosc_karty` czyta WYLACZNIE `card["source_dates"]`, wiec
# `source_date` wpisany w twierdzenie nie wazyl na nic. Rozszerzamy `oldest`,
# nigdy `newest`: `newest` decyduje o uwadze CALY_MATERIAL_STARY i o tym, czy
# `karta_dla_pisarza` skasuje note o wieku — podniesienie go data niepobranego
# dokumentu UCISZALOBY ostrzezenie.
KARTA_Z_DATAMI = dict(KARTA, source_dates={"newest": "2026-08-28",
                                           "oldest": "2026-08-27", "note": ""})
karta_daty = przebieg_do_karty(BRIEF, karta=KARTA_Z_DATAMI)
sprawdz("najstarsze zrodlo cofnelo sie do daty faktu z puli",
        karta_daty["source_dates"]["oldest"] == BRIEF["data_zrodla"],
        karta_daty["source_dates"])
sprawdz("a najnowsze zostalo nietkniete",
        karta_daty["source_dates"]["newest"] == "2026-08-28",
        karta_daty["source_dates"])
# KONTRDOWOD: fakt NOWSZY od calego materialu nie rusza niczego — inaczej
# podnosilby `newest` i uciszal uwage o starym materiale.
karta_nowszy = przebieg_do_karty(
    dict(BRIEF, data_zrodla="2026-08-30"), karta=KARTA_Z_DATAMI)
sprawdz("KONTRDOWOD: swiezszy fakt nie rusza ani `oldest`, ani `newest`",
        karta_nowszy["source_dates"] == {"newest": "2026-08-28",
                                         "oldest": "2026-08-27", "note": ""},
        karta_nowszy["source_dates"])
# KONTRDOWOD: karta BEZ dat ma dostac KARTA_BEZ_DAT, a nie date jedynego
# niepobranego zrodla udajaca caly material.
karta_bez_dat = przebieg_do_karty(BRIEF, karta=dict(KARTA))
sprawdz("KONTRDOWOD: karta bez dat nie dostaje dat z niepobranego zrodla",
        "source_dates" not in karta_bez_dat, karta_bez_dat.get("source_dates"))

print()
print("--- 5d. dziewiate twierdzenie nie rozdyma karty ---")
# `config.CARD_MAX_CONFIRMED` = 8, `stages.synthesis` przycina do tylu, a
# `audyt_researchu.py` melduje „UWAGA — karta rozdeta" powyzej sufitu.
PELNA = dict(KARTA, confirmed_claims=[
    {"claim": "twierdzenie %d" % i, "evidence": "cytat %d" % i,
     "url": "https://host%d.example/x" % min(i, 6)}
    for i in range(config.CARD_MAX_CONFIRMED)])
karta_pelna = przebieg_do_karty(BRIEF, karta=PELNA)
tw = karta_pelna["confirmed_claims"]
sprawdz("karta zostaje w sufcie %d twierdzen" % config.CARD_MAX_CONFIRMED,
        len(tw) == config.CARD_MAX_CONFIRMED, len(tw))
sprawdz("fakt z puli stoi na poczatku", tw[0].get("not_fetched") is True, tw[0])
# NAJWAZNIEJSZE: zaden HOST nie zniknal. Ciac trzeba powtorke, nie zrodlo —
# inaczej naprawiajac liczbe pozycji psulibysmy szerokosc podstawy i sekcje
# `## Sources`, czyli to, czego ta liczba pilnuje.
hosty_przed = {c["url"] for c in PELNA["confirmed_claims"]}
hosty_po = {c["url"] for c in tw if not c.get("not_fetched")}
sprawdz("i zaden host nie zniknal z karty", hosty_przed == hosty_po,
        sorted(hosty_przed - hosty_po))
# KONTRDOWOD: gdy KAZDE twierdzenie ma wlasny host, nie ma czego uciac —
# karta wychodzi z dziewiatka i mowi to glosno, zamiast po cichu stracic zrodlo.
OSIEM_HOSTOW = dict(KARTA, confirmed_claims=[
    {"claim": "twierdzenie %d" % i, "evidence": "cytat %d" % i,
     "url": "https://host%d.example/x" % i}
    for i in range(config.CARD_MAX_CONFIRMED)])
karta_osiem = przebieg_do_karty(BRIEF, karta=OSIEM_HOSTOW)
sprawdz("KONTRDOWOD: osiem roznych hostow — wolimy dziewiatke niz strate zrodla",
        len(karta_osiem["confirmed_claims"]) == config.CARD_MAX_CONFIRMED + 1,
        len(karta_osiem["confirmed_claims"]))

print()
print("--- 5e. sekcja `## Sources` naprawde niesie to zrodlo ---")
# Poprzednia wersja sprawdzala to ASERCJA PO TRESCI ZRODLA `stages.py` — czyli
# odwzorowywala wyobrazenie wywolania. Tu wolamy PRAWDZIWY `stages.save` na
# bazie i katalogu tymczasowym i czytamy zapisany plik.
import db as _db            # noqa: E402

_kat_art = pathlib.Path(_tmp.mkdtemp())
_stary_kat = config.ARTICLES_DIR
config.ARTICLES_DIR = _kat_art
_conn = _db.connect(_kat_art / "t.db")
try:
    with contextlib.redirect_stdout(io.StringIO()):
        _sciezka = _stages.save(_conn, 9999, BRIEF, karta, DRAFT, "SAVED", "", [])
    _tekst = pathlib.Path(_sciezka).read_text(encoding="utf-8")
finally:
    config.ARTICLES_DIR = _stary_kat
    _conn.close()
_sekcja = _tekst.split("## Sources")[-1]
sprawdz("zrodlo faktu stoi pod tekstem, w sekcji `## Sources`",
        BRIEF["zrodlo_faktu"] in _sekcja, _sekcja[:300])
sprawdz("razem ze zrodlem z korpusu",
        "https://inny.example/a" in _sekcja, _sekcja[:300])

print()
print("--- 5f. kontrdowody do samego doklejania ---")
# KONTRDOWOD 1: bez URL-a nie doklejamy nic. Twierdzenie bez zrodla w karcie
# byloby zaproszeniem dla pisarza do napisania zdania, ktorego nikt nie obroni.
karta = przebieg_do_karty(dict(BRIEF, zrodlo_faktu=""))
sprawdz("KONTRDOWOD: bez zrodla fakt nie wchodzi do karty",
        len(karta.get("confirmed_claims") or []) == 1,
        karta.get("confirmed_claims"))
# KONTRDOWOD 2: gdy to zrodlo jest juz w karcie z researchu, nie dublujemy.
karta = przebieg_do_karty(dict(BRIEF, zrodlo_faktu="https://inny.example/a"))
sprawdz("KONTRDOWOD: znane zrodlo nie jest dublowane",
        len(karta.get("confirmed_claims") or []) == 1,
        karta.get("confirmed_claims"))

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
