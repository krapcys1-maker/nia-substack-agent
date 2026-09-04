# -*- coding: utf-8 -*-
"""Znacznik kanalu musi przezyc zapis do banku.

SZOSTY RAZ TEGO SAMEGO KSZTALTU W JEDNYM DNIU: sygnal policzony i wyrzucony.

`znajdz_ciekawostki` liczy, z ktorego kanalu wyszedl fakt, i log to pokazuje —
    [ciekawostki] z kanalow: 6 z 6 (100%)
    · [KANAL:Kanal Przegladowy] OpenAI's first custom inference chip, SkladnikA...
a w banku wszystkie szesc mialo „z pamieci". Bo pola zapisywane do indeksu ida
z KSZTALTU ODPOWIEDZI MODELU (`KSZTALT_CIEKAWOSTEK`), a `z_kanalu` liczy KOD po
odpowiedzi — wiec nie bylo go w kontrakcie i przepadalo.

DLACZEGO TO KOSZTOWALO. `wez_kandydatow` sortuje kotwica PRZED ranga, zeby temat
z tego tygodnia mial pierwszenstwo przed rownie dobrym z pamieci. Kotwica byla
zawsze pusta, wiec cale to pierwszenstwo bylo martwe — a wygladalo na dzialajace,
bo kod byl na miejscu i testy przechodzily.

BEZ PYTESTA, bez platnych wywolan. Uruchamiac z korzenia repozytorium.
"""
import json
import pathlib
import sys
import tempfile
from datetime import datetime, timezone

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


SWIEZY = (datetime.now(timezone.utc)).strftime("%Y-%m-%d")


# ATRAPY MUSZA BYC NAPRAWDE ROZNE. Pierwsza wersja roznila sie jedna cyfra i
# ochrona przed powtorkami slusznie odrzucila drugi wpis — test mierzyl wtedy
# swoja wlasna wade, nie kodu.
TRESCI = {
    1: ("The provider chose to bill prompt caching as a separate line rather "
        "than folding it into the token rate, so the same request costs "
        "differently depending on what came before it."),
    2: ("A hardware vendor publishes throughput per watt measured on one "
        "workload, and the figure quoted everywhere omits which workload it "
        "was, so two chips get compared on numbers that were never comparable."),
    3: ("Open weights are released under a licence whose user threshold turns "
        "the permission off above a certain size of company, which almost "
        "nobody reads before building on it."),
    4: ("A benchmark suite keeps part of its questions unpublished, and the "
        "gap between the public score and the held-out score is where "
        "contamination shows up."),
}


def fakt(nr, z_kanalu, kanal=""):
    return {
        "fact": TRESCI[nr],
        "wrong_belief": "People assume nobody chose this.",
        "actually": "Somebody chose it, and the document says who.",
        "decision": ("A decision: somebody signed off on that arrangement and "
                     "the record names when."),
        "consequence": ("Your bill for the same request moved, and you were not "
                        "told which half moved."),
        "url": "https://example.org/%d" % nr, "source_date": SWIEZY,
        "control_date": SWIEZY, "control_url": "https://example.org/%d" % nr,
        "control_verdict": "CONFIRMS", "control_fact": "checked today, unchanged",
        "domain": "how models are served and priced",
        "z_kanalu": z_kanalu, "kanal_zrodlowy": kanal,
    }


katalog = pathlib.Path(tempfile.mkdtemp())
stary = stages.INDEKS_KANDYDATOW
stages.INDEKS_KANDYDATOW = katalog / "indeks.json"
stages.INDEKS_KANDYDATOW.write_text("[]", encoding="utf-8")

try:
    print("=== 0. ATRAPY PRZECHODZA BRAMKI ===")
    # Bez tego test moglby sie zielenic na materiale, ktory i tak by odpadl.
    for nr in (1, 2):
        ok, powod = stages.swiezosc_faktu(fakt(nr, True))
        sprawdz("fakt %d przechodzi swiezosc" % nr, ok, powod)
        ok, powod = stages.bramka_kandydata(fakt(nr, True))
        sprawdz("  i bramke kandydata", ok, powod)

    print()
    print("=== 1. ZNACZNIK KANALU JEST W BANKU PO ZAPISIE ===")
    stages.dopisz_kandydatow([fakt(1, True, "Kanal Przegladowy"),
                              fakt(2, False, "")])
    bank = json.loads(stages.INDEKS_KANDYDATOW.read_text(encoding="utf-8"))
    sprawdz("dopisane dwa", len(bank) == 2, len(bank))
    z_kan = [k for k in bank if k.get("z_kanalu")]
    sprawdz("jeden ma znacznik kanalu", len(z_kan) == 1, len(z_kan))
    sprawdz("i pamieta ktory to kanal",
            z_kan and z_kan[0].get("kanal_zrodlowy") == "Kanal Przegladowy",
            z_kan[0].get("kanal_zrodlowy") if z_kan else None)
    bez = [k for k in bank if not k.get("z_kanalu")]
    sprawdz("drugi nie ma znacznika", len(bez) == 1, len(bez))
    sprawdz("i pole istnieje, a nie brakuje go",
            all("z_kanalu" in k for k in bank),
            [sorted(k)[:5] for k in bank])

    print()
    print("=== 2. WYJMOWANIE STAWIA ZAKOTWICZONY PRZED RANGA ===")
    # Kotwica ma bic range: temat z tego tygodnia idzie przed rownie dobrym
    # tematem z pamieci, nawet jesli model ustawil go nizej.
    bank = json.loads(stages.INDEKS_KANDYDATOW.read_text(encoding="utf-8"))
    for k in bank:
        k["ranga"] = 0 if not k.get("z_kanalu") else 5   # z pamieci ma LEPSZA range
    stages.INDEKS_KANDYDATOW.write_text(json.dumps(bank, ensure_ascii=False),
                                        encoding="utf-8")
    wziete = stages.wez_kandydatow(2)
    sprawdz("wzieto oba", len(wziete) == 2, len(wziete))
    sprawdz("pierwszy jest ten z kanalu, mimo gorszej rangi",
            wziete and wziete[0].get("z_kanalu") is True,
            [(k.get("z_kanalu"), k.get("ranga")) for k in wziete])

    print()
    print("=== 3. KONTRDOWOD: BEZ KOTWIC DECYDUJE RANGA ===")
    # Gdyby kotwica nie dzialala, sekcja 2 przechodzilaby rowniez wtedy — wiec
    # sprawdzamy, ze przy DWOCH bez kotwicy wygrywa nizsza ranga.
    stages.INDEKS_KANDYDATOW.write_text("[]", encoding="utf-8")
    stages.dopisz_kandydatow([fakt(3, False), fakt(4, False)])
    bank = json.loads(stages.INDEKS_KANDYDATOW.read_text(encoding="utf-8"))
    for k in bank:
        k["ranga"] = 0 if k["fact"] == TRESCI[4] else 9
    stages.INDEKS_KANDYDATOW.write_text(json.dumps(bank, ensure_ascii=False),
                                        encoding="utf-8")
    wziete = stages.wez_kandydatow(2)
    sprawdz("bez kotwic pierwszy jest ten z ranga 0",
            wziete and wziete[0]["fact"] == TRESCI[4],
            [k.get("ranga") for k in wziete])
finally:
    stages.INDEKS_KANDYDATOW = stary

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
