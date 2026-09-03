# -*- coding: utf-8 -*-
"""Nieudana publikacja artykulu nie moze wygladac jak sukces.

CO BYLO ZLE, odtworzone 2 wrzesnia 2026. `_napisz_i_zapisz` konczylo sie
BEZWARUNKOWYM `return 0` po `browser.wystaw_artykul`, a `main()` robilo
`finish_run(..., "DONE" if kod == 0 else "SKIPPED")`. W bazie wygladalo to tak:

    run 1   status=DONE   stage=artykul  note=''      <- publikacja potwierdzona
    run 2   status=DONE   stage=artykul  note=''      <- publikacja NIE poszla
    IDENTYCZNE: True
    trzy przebiegi z nieudana publikacja -> maili: 0

Trzy warstwy niewidocznosci naraz: `wystaw_artykul` lapie kazdy wyjatek
u siebie i oddaje slownik; przy braku przycisku publikacji nie powstaje nawet
wpis w dzienniku; a `return 0` zamieniało to wszystko w „DONE". Zegar artykulu
chodzi RAZ W TYGODNIU i usluga nie ma `Restart=`, wiec nieudany wtorek oznaczal
tydzien ciszy — przy tekscie, ktory juz kosztowal 1,4-2,1 USD.

CZEGO TEN PLIK PILNUJE — trzech rzeczy, kazdej osobno:
  1. ze publikacja jest PONAWIANA, ale nie po sukcesie;
  2. ze porazka ma WLASNY status w bazie, rozny od udanej;
  3. ze gotowy tekst wraca do rutyny dnia zamiast czekac tydzien.

NIC Z TEGO NIE JEST BRAMKA. Nie ma tu warunku, ktory moglby publikacji
zabronic — jedyne, co doszlo, to powtorzenie proby i prawda o wyniku.

BEZ PYTESTA, zero sieci, zero platnych wywolan, produkcja nietknieta.
Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_publikacja_artykulu_nie_klamie.py
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, "agent-v2")
import config      # noqa: E402

KATALOG = pathlib.Path(tempfile.mkdtemp(prefix="artykul-test-"))
config.uzyj_katalogu_danych(KATALOG)
config.PRZERWA_MIEDZY_PROBAMI_ARTYKULU_S = 0      # test nie ma spac

import artykul_z_puli as az   # noqa: E402
import stages                 # noqa: E402

stages.NIEWYSTAWIONY = KATALOG / "artykul_niewystawiony.json"

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


class Atrapa:
    """Podstawiona `browser`. Liczy wywolania i oddaje zadane wyniki."""

    def __init__(self, wyniki):
        self.wyniki = list(wyniki)
        self.wolania = []

    def wystaw_artykul(self, sciezka, wyslij=False):
        self.wolania.append(str(sciezka))
        if not self.wyniki:
            return {"wyslane": False, "blad": "skrypt wyczerpany"}
        w = self.wyniki.pop(0)
        if isinstance(w, Exception):
            raise w
        return w


def podstaw(atrapa):
    sys.modules["browser"] = atrapa
    return atrapa


ARTYKUL = KATALOG / "0031-test.md"
ARTYKUL.write_text("# Test\n\nJeden akapit.", encoding="utf-8")

print("=== 1. PONOWIENIE: ILE RAZY I KIEDY PRZESTAC ===")
for opis, wyniki, ile_wolan, czy_wyslane in (
    ("zawsze pada", [{"wyslane": False}] * 5, config.PROB_PUBLIKACJI_ARTYKULU, False),
    ("udaje sie za trzecim", [{"wyslane": False}, {"wyslane": False},
                              {"wyslane": True}], 3, True),
    ("udaje sie od razu", [{"wyslane": True}], 1, True),
    ("przegladarka rzuca", [RuntimeError("padla sesja")] * 5,
     config.PROB_PUBLIKACJI_ARTYKULU, False),
):
    a = podstaw(Atrapa(wyniki))
    w = az._opublikuj(ARTYKUL)
    sprawdz("%-22s -> %d prob, wyslane=%s" % (opis, ile_wolan, czy_wyslane),
            len(a.wolania) == ile_wolan and bool(w.get("wyslane")) is czy_wyslane,
            "wolan=%d wyslane=%s" % (len(a.wolania), w.get("wyslane")))

# KONTRDOWOD: gdyby ponowienie bylo bezwarunkowe, „udaje sie od razu" mialoby
# trzy wywolania — czyli walilibysmy w Substacka po udanej publikacji.
a = podstaw(Atrapa([{"wyslane": True}]))
az._opublikuj(ARTYKUL)
sprawdz("po sukcesie NIE probujemy dalej", len(a.wolania) == 1, len(a.wolania))

print()
print("=== 2. ZNACZNIK NA DYSKU ===")
stages.zapomnij_niewystawiony()
sprawdz("na starcie znacznika nie ma", stages.niewystawiony_artykul() is None)
stages.zapamietaj_niewystawiony(ARTYKUL, "Substack nie potwierdzil")
zn = stages.niewystawiony_artykul()
sprawdz("po zapisie wskazuje plik",
        bool(zn) and zn["sciezka"] == str(ARTYKUL), zn)
sprawdz("i zaczyna od zera prob", bool(zn) and zn.get("proby") == 0, zn)
sprawdz("proba podbija licznik", stages.odnotuj_probe_artykulu("nadal nie") == 1)
stages.zapomnij_niewystawiony()
sprawdz("po publikacji znacznik znika",
        stages.niewystawiony_artykul() is None)

print()
print("=== 3. PORAZKA MA WLASNY STATUS W BAZIE ===")
# To jest odtworzenie z 2 wrzesnia obrocone w asercje: dwa przebiegi, jeden
# z udana publikacja i jeden z nieudana, MUSZA sie w bazie roznic.
import db          # noqa: E402
BAZA = KATALOG / "runs.db"
conn = db.connect(BAZA)

statusy = {}
for opis, kod in (("udana", 0), ("nieudana", az.KOD_NIEOPUBLIKOWANY)):
    rid = db.start_run(conn)
    if kod == az.KOD_NIEOPUBLIKOWANY:
        db.finish_run(conn, rid, "NIEOPUBLIKOWANY", "artykul",
                      "tekst gotowy, publikacja nie potwierdzona")
    else:
        db.finish_run(conn, rid, "DONE" if kod == 0 else "SKIPPED", "artykul")
    statusy[opis] = conn.execute(
        "SELECT status FROM runs WHERE id = ?", (rid,)).fetchone()[0]

sprawdz("udana i nieudana maja ROZNE statusy",
        statusy["udana"] != statusy["nieudana"], statusy)
sprawdz("status porazki nie jest DONE ani SAVED",
        statusy["nieudana"] not in ("DONE", "SAVED"), statusy["nieudana"])
sprawdz("a udana nadal jest DONE", statusy["udana"] == "DONE", statusy)

print()
print("=== 4. ALARM WIDZI ZALEGLY TEKST — I NIE KRZYCZY ZA WCZESNIE ===")
import alarm       # noqa: E402
stages.zapomnij_niewystawiony()
sprawdz("bez znacznika alarm milczy", alarm.artykul_zalegly() is None)

stages.zapamietaj_niewystawiony(ARTYKUL, "brak przycisku")
sprawdz("swiezy znacznik jeszcze nie alarmuje (mniej niz doba)",
        alarm.artykul_zalegly() is None, alarm.artykul_zalegly())

# Cofamy zegar znacznika o dwie doby — bez czekania.
import json        # noqa: E402
from datetime import datetime, timedelta, timezone   # noqa: E402
d = json.loads(stages.NIEWYSTAWIONY.read_text(encoding="utf-8"))
d["kiedy"] = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat(timespec="seconds")
stages.NIEWYSTAWIONY.write_text(json.dumps(d), encoding="utf-8")
tresc = alarm.artykul_zalegly()
sprawdz("po dwoch dobach alarm sie odzywa", bool(tresc), tresc)
sprawdz("i podaje sciezke pliku", bool(tresc) and str(ARTYKUL) in str(tresc),
        tresc)
# WPIECIE MIERZONE NA DRZEWIE SKLADNI. Pierwsza wersja tej asercji konczyla
# sie `else True`, czyli byla ZAWSZE PRAWDZIWA — dokladnie ten wzorzec, ktory
# `DO_ZROBIENIA.md` wymienia jako dlug (`sprawdz(nazwa, True)` podbija licznik
# i nie moze oblac nigdy). Krotka `kontrole` jest lokalna w funkcji alarmu,
# wiec nie da sie jej zaimportowac — ale da sie o nia zapytac drzewo.
import ast as _ast_a
_zrodlo_alarmu = pathlib.Path("agent-v2/alarm.py").read_text(encoding="utf-8")
_krotki = [n for n in _ast_a.walk(_ast_a.parse(_zrodlo_alarmu))
           if isinstance(n, _ast_a.Assign)
           and any(getattr(t, "id", "") == "kontrole" for t in n.targets)]
sprawdz("lista kontroli alarmu istnieje", len(_krotki) == 1, len(_krotki))
_nazwy = {getattr(x, "id", "") for k in _krotki for x in _ast_a.walk(k)
          if isinstance(x, _ast_a.Name)}
sprawdz("i zawiera `artykul_zalegly`", "artykul_zalegly" in _nazwy,
        sorted(n for n in _nazwy if n))
# KONTRDOWOD: wykrywacz musi widziec TAKZE stare kontrole, inaczej patrzy
# w pustke i obie asercje przechodza pusto.
sprawdz("wykrywacz widzi tez kontrole, ktore tam byly",
        {"cisza", "dysk", "koszt"} <= _nazwy, sorted(_nazwy)[:8])

print()
print("=== 5. USZKODZONY ZNACZNIK NIE WYWALA NICZEGO ===")
for opis, tresc_pliku in (("smieci", "to nie jest json"),
                          ("pusty", ""),
                          ("lista zamiast slownika", "[1,2,3]"),
                          ("slownik bez sciezki", '{"proby": 2}')):
    stages.NIEWYSTAWIONY.write_text(tresc_pliku, encoding="utf-8")
    try:
        w = stages.niewystawiony_artykul()
        a = alarm.artykul_zalegly()
        sprawdz("%-24s -> None, bez wyjatku" % opis, w is None and a is None,
                "%r / %r" % (w, a))
    except Exception as exc:                          # noqa: BLE001
        sprawdz("%-24s -> None, bez wyjatku" % opis, False,
                "%s: %s" % (type(exc).__name__, exc))

stages.zapomnij_niewystawiony()

print()
print("=" * 62)
print("ZDANE: %d    OBLANE: %d" % (zdane, oblane))
sys.exit(1 if oblane else 0)
