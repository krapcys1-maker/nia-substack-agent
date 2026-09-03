# -*- coding: utf-8 -*-
"""Dwie kandydatury o tej samej rzeczy nie wychodza z banku razem.

DLACZEGO TO POWSTALO. Ranking banku ustawia kandydatow wzgledem siebie, ale nie
pyta, czy dwaj sasiedzi nie mowia tego samego — i nie zapyta, bo to jest praca
dla kodu, nie dla modelu. Zywy przebieg 30 sierpnia oddal bank, w ktorym
pozycje #7 i #8 obie tlumaczyly, czemu odpowiedz plynie slowo po slowie.

Wziete razem daja dwie notki o jednej rzeczy w jednym dniu — dokladnie wpadke z
23 i 24 sierpnia, gdy dwa razy poszedl symbol otwartego sloika. Ochrona przed
tym istniala tylko MIEDZY dniami (`ostatnie_notki`), nie wewnatrz partii.

Rozmyty wykrywacz `_o_tym_samym` istnial w tym pliku od dawna i bank go NIE
WOLAL. Ten sam ksztalt wady co reszta audytu: sygnal wytworzony i wyrzucony.

NIE ODRZUCAMY, TYLKO POMIJAMY. Koszt pomylki jest asymetryczny: falszywe
trafienie kosztuje jeden przebieg zwloki, bo kandydat zostaje w banku ze
statusem „nowy"; przeoczenie kosztuje dwie notki o tym samym.

BEZ PYTESTA. Uruchamiac z korzenia repozytorium.
"""
import json
import pathlib
import sys
import tempfile
from datetime import datetime, timedelta, timezone

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


BLIZNIAK_A = ("Language models produce their answer one token at a time, "
              "because each token is fed back as input before the next one is "
              "computed, which is why the text appears word by word.")
BLIZNIAK_B = ("The text appears word by word because every token the model "
              "produces is fed back as input, and the next token cannot be "
              "computed before that happens.")
OSOBNY = ("In a 12-month longitudinal study, participants who used a "
          "conversational assistant every day described their own reasoning "
          "differently afterwards.")

JUTRO = (datetime.now(timezone.utc) + timedelta(days=3)).strftime("%Y-%m-%d %H:%M")
SWIEZY = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%d")


def kandydat(tresc, ranga=None):
    k = {"fact": tresc, "status": "nowy",
         "kiedy": datetime.now(timezone.utc).isoformat(),
         "wazny_do": JUTRO,
         "source_date": SWIEZY,
         "control_verdict": "CONFIRMS", "control_date": SWIEZY,
         "control_fact": "checked today, unchanged",
         "actually": "", "wrong_belief": "", "consequence": "", "decision": ""}
    if ranga is not None:
        k["ranga"] = ranga
    return k


print("=== 0. ATRAPY SA TYM, ZA CO JE BIORE ===")
# Test na atrapach bez badanej wlasciwosci dowodzi tylko tego, ze kod cos
# zwraca. Najpierw dowod, ze para NAPRAWDE jest blizniacza, a trzeci nie.
sprawdz("blizniaki sa rozpoznawane jako to samo",
        stages._o_tym_samym(BLIZNIAK_A, BLIZNIAK_B,
                            **stages.POROWNANIE_MIEDZY_DNIAMI))
sprawdz("osobny fakt NIE zderza sie z blizniakiem A",
        not stages._o_tym_samym(BLIZNIAK_A, OSOBNY,
                                **stages.POROWNANIE_MIEDZY_DNIAMI))
sprawdz("osobny fakt NIE zderza sie z blizniakiem B",
        not stages._o_tym_samym(BLIZNIAK_B, OSOBNY,
                                **stages.POROWNANIE_MIEDZY_DNIAMI))
for nazwa, tresc in (("A", BLIZNIAK_A), ("B", BLIZNIAK_B), ("osobny", OSOBNY)):
    ok, powod = stages.swiezosc_faktu(kandydat(tresc))
    sprawdz("  %s przechodzi bramke swiezosci" % nazwa, ok, powod)

katalog = pathlib.Path(tempfile.mkdtemp())
_stary_indeks = stages.INDEKS_KANDYDATOW
stages.INDEKS_KANDYDATOW = katalog / "indeks.json"
try:
    print()
    print("=== 1. Z PARY BLIZNIAKOW WYCHODZI JEDEN ===")
    stages.INDEKS_KANDYDATOW.write_text(json.dumps([
        kandydat(BLIZNIAK_A, ranga=0),
        kandydat(BLIZNIAK_B, ranga=1),
        kandydat(OSOBNY, ranga=2),
    ], ensure_ascii=False), encoding="utf-8")
    wziete = stages.wez_kandydatow(3)
    tresci = [k["fact"] for k in wziete]
    sprawdz("wzieto dwa, nie trzy", len(wziete) == 2, len(wziete))
    sprawdz("wyszedl mocniejszy z pary (ranga 0)", BLIZNIAK_A in tresci)
    sprawdz("slabszy blizniak nie wyszedl", BLIZNIAK_B not in tresci)
    sprawdz("osobny fakt wyszedl", OSOBNY in tresci)

    print()
    print("=== 2. POMINIETY BLIZNIAK ZOSTAJE W BANKU, NIE GINIE ===")
    # Odrzucenie jest trwale i nieodwracalne. Pominiecie w partii nie moze byc
    # ukryta forma odrzucenia — kandydat ma sie nadawac do wziecia jutro.
    po = json.loads(stages.INDEKS_KANDYDATOW.read_text(encoding="utf-8"))
    stan = {k["fact"]: k["status"] for k in po}
    sprawdz("blizniak B nadal 'nowy'", stan.get(BLIZNIAK_B) == "nowy",
            stan.get(BLIZNIAK_B))
    sprawdz("blizniak A oznaczony jako uzyty", stan.get(BLIZNIAK_A) == "uzyty",
            stan.get(BLIZNIAK_A))
    sprawdz("osobny oznaczony jako uzyty", stan.get(OSOBNY) == "uzyty",
            stan.get(OSOBNY))

    print()
    print("=== 3. I DA SIE GO WZIAC NASTEPNYM RAZEM ===")
    znowu = [k["fact"] for k in stages.wez_kandydatow(3)]
    sprawdz("pominiety blizniak wychodzi w kolejnej partii",
            znowu == [BLIZNIAK_B], znowu)

    print()
    print("=== 4. KONTRDOWOD: BEZ PARY BLIZNIACZEJ NIC NIE JEST CIETE ===")
    # Gdyby filtr byl za ostry albo dzialal zawsze, ten przypadek tez by sie
    # skrocil — a wtedy test wyzej nie dowodzilby niczego o blizniakach.
    INNY = ("On 21 April 2026 a court ruled that a police force's live facial "
            "recognition deployment lacked a lawful basis in the way it was run.")
    sprawdz("  trzy osobne fakty naprawde sa osobne",
            not stages._o_tym_samym(OSOBNY, INNY,
                                    **stages.POROWNANIE_MIEDZY_DNIAMI)
            and not stages._o_tym_samym(BLIZNIAK_A, INNY,
                                        **stages.POROWNANIE_MIEDZY_DNIAMI))
    stages.INDEKS_KANDYDATOW.write_text(json.dumps([
        kandydat(BLIZNIAK_A, ranga=0),
        kandydat(OSOBNY, ranga=1),
        kandydat(INNY, ranga=2),
    ], ensure_ascii=False), encoding="utf-8")
    trzy = stages.wez_kandydatow(3)
    sprawdz("trzy osobne fakty wychodza w komplecie", len(trzy) == 3, len(trzy))

    print()
    print("=== 5. NAZWA WLASNA LAPIE PARE, KTORA PROPORCJA PRZEPUSCILA ===")
    # ZMIERZONE na zywym banku: dwie kandydatury o tym samym frameworku DSpark
    # mialy SZESC wspolnych rdzeni (powyzej progu liczbowego), ale udzial 0,240
    # przy progu 0,30 — bo jedna opisywala publikacje z uczelnia, druga numer
    # arXiv, wiec RESZTA slow byla inna. Rzadka nazwa wlasna luzuje proporcje,
    # nie liczbe wspolnych rdzeni.
    # PRAWDZIWE TEKSTY Z PRODUKCJI, nie wymyslone — to one ujawnily wade.
    DSPARK_A = ("DeepSeek's DSpark inference framework (paper with Peking "
                "University, 27 June 2026) sped up single-user generation by "
                "60–85% on its V4-Flash model with no change to output, "
                "because a GPU's bottleneck is moving weights from memory "
                "— decoding several tokens at once costs barely more than "
                "decoding one.")
    DSPARK_B = ("DeepSeek's DSpark (arXiv 2607.05147, submitted 6 July 2026) "
                "accelerates per-user generation speeds by 60–85% in live "
                "traffic on the DeepSeek-V4 serving system by having a small "
                "drafter model guess tokens in parallel and a "
                "confidence-scheduled scheduler verify only the tokens likely "
                "to be accepted.")
    sprawdz("proporcja SAMA ich nie lapie",
            not stages._o_tym_samym(DSPARK_A, DSPARK_B,
                                    **stages.POROWNANIE_MIEDZY_DNIAMI))
    stages.INDEKS_KANDYDATOW.write_text(json.dumps([
        kandydat(DSPARK_A, ranga=0), kandydat(DSPARK_B, ranga=1),
        kandydat(OSOBNY, ranga=2),
    ], ensure_ascii=False), encoding="utf-8")
    wziete = stages.wez_kandydatow(3)
    sprawdz("ale nazwa wlasna juz tak — wychodzi jeden z pary",
            len(wziete) == 2, [str(k["fact"])[:40] for k in wziete])
    sprawdz("i osobny fakt nadal wychodzi",
            any(k["fact"] == OSOBNY for k in wziete))

    print()
    print("=== 6. KONTRDOWOD: ZWYKLE SLOWO NIE WYSTARCZA ===")
    # Pierwsza wersja tej reguly wymagala tylko RZADKOSCI i byla katastrofalna:
    # uklad scalony zderzal sie z wlamaniem, a framework z dokumentami
    # inwestorskimi, bo przy kilkunastu wpisach mnostwo zwyklych slow trafia sie
    # dokladnie dwa razy. Rdzen musi wygladac jak nazwa.
    LUZNY_A = ("A regulator in one country published the number of schools "
               "where a face-matching system runs every morning.")
    LUZNY_B = ("Investor documents put the cost of serving trained models above "
               "half of revenue before training is counted at all.")
    stages.INDEKS_KANDYDATOW.write_text(json.dumps([
        kandydat(LUZNY_A, ranga=0), kandydat(LUZNY_B, ranga=1),
    ], ensure_ascii=False), encoding="utf-8")
    wziete = stages.wez_kandydatow(2)
    sprawdz("dwa rozne fakty bez nazwy wlasnej wychodza oba",
            len(wziete) == 2, [str(k["fact"])[:40] for k in wziete])

    print()
    print("=== 7. LIMIT `ile` NADAL OBOWIAZUJE ===")
    stages.INDEKS_KANDYDATOW.write_text(json.dumps([
        kandydat(BLIZNIAK_A, ranga=0),
        kandydat(OSOBNY, ranga=1),
        kandydat(INNY, ranga=2),
    ], ensure_ascii=False), encoding="utf-8")
    sprawdz("prosze o 1, dostaje 1", len(stages.wez_kandydatow(1)) == 1)
    stages.INDEKS_KANDYDATOW.write_text(json.dumps([
        kandydat(BLIZNIAK_A, ranga=0)], ensure_ascii=False), encoding="utf-8")
    sprawdz("prosze o 0, dostaje 0", stages.wez_kandydatow(0) == [])
finally:
    stages.INDEKS_KANDYDATOW = _stary_indeks

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
