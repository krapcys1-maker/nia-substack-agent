# -*- coding: utf-8 -*-
"""Termin artykulu z planu trwa do skutku — piaty wtorek i padniety przebieg.

CO SIE STALO 29 wrzesnia 2026. Plan miesieczny [1, 8, 15, 22] wypadal we
wrzesniu we wtorki, wiec konto pisalo „co wtorek". Piaty wtorek (29.09) w planie
nie istnial: od 22.09 do 1.10 dziewiec dni bez artykulu, a w pazdzierniku te same
dni wypadaja w czwartki. Starsza dziura: zegar odpalal artykul RAZ, a rutyna
dnia ponawia tylko WYSTAWIENIE gotowego tekstu — przebieg, ktory padl przed
napisaniem (8.09 „pula ciekawostek pusta"), oznaczal tydzien bez artykulu.

TERAZ: zegar chodzi codziennie (`konfiguracja.on_calendar_artykulu`), a
`artykul_z_puli.artykul_nalezny` pisze, gdy od ostatniego dnia z planu
(`config.ostatni_dzien_planu`) nie wyszedl zaden artykul
(`stages.ostatni_wystawiony_artykul`) i nie czeka gotowy tekst z probami.

BEZ PYTESTA, bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo.
"""
import json
import pathlib
import sys
import tempfile
from datetime import date, datetime, timezone
from types import SimpleNamespace

sys.path.insert(0, "agent-v2")

zdane = oblane = 0


def sprawdz(nazwa, warunek, szczegol=""):
    global zdane, oblane
    if warunek:
        zdane += 1
        print("  OK    %s" % nazwa)
    else:
        oblane += 1
        print("  BLAD  %s   %s" % (nazwa, szczegol))


import config  # noqa: E402
import konfiguracja  # noqa: E402
import stages  # noqa: E402
import artykul_z_puli  # noqa: E402

KATALOG = pathlib.Path(tempfile.mkdtemp())
STARE = {k: getattr(config, k) for k in (
    "DATA_DIR", "ARTYKULY_TYGODNIOWO", "ARTYKULY_MIESIECZNIE", "DNI_ARTYKULU",
    "DNI_MIESIACA_ARTYKULU", "PRESET")}
STARY_ZNACZNIK = stages.NIEWYSTAWIONY
config.DATA_DIR = KATALOG
stages.NIEWYSTAWIONY = KATALOG / "artykul_niewystawiony.json"


def utc(r, m, d, g=16, mi=30):
    return datetime(r, m, d, g, mi, tzinfo=timezone.utc)


def plan_wtorek():
    config.ARTYKULY_TYGODNIOWO, config.ARTYKULY_MIESIECZNIE = 1, 0
    config.DNI_ARTYKULU, config.DNI_MIESIACA_ARTYKULU = ("Tue",), ()


def plan_miesieczny():
    config.ARTYKULY_TYGODNIOWO, config.ARTYKULY_MIESIECZNIE = 0, 4
    config.DNI_ARTYKULU, config.DNI_MIESIACA_ARTYKULU = (), (1, 8, 15, 22)


def dziennik(*wpisy, smieci=False):
    linie = [json.dumps(w, ensure_ascii=False) for w in wpisy]
    if smieci:
        linie.append('{"rodzaj": "artykul", uciete')
    (KATALOG / "dziennik.jsonl").write_text("\n".join(linie) + "\n", encoding="utf-8")


def znacznik(proby=None):
    if proby is None:
        stages.NIEWYSTAWIONY.unlink(missing_ok=True)
        return
    stages.NIEWYSTAWIONY.write_text(json.dumps(
        {"sciezka": str(KATALOG / "tekst.md"), "powod": "x", "proby": proby,
         "kiedy": "2026-09-29T16:50:00+00:00",
         "instancja": getattr(config, "INSTANCJA", "")}), encoding="utf-8")


ART_22 = {"kiedy": "2026-09-22T16:54:14+00:00", "rodzaj": "artykul", "udane": True, "tytul": "a"}
ART_29 = {"kiedy": "2026-09-29T16:55:00+00:00", "rodzaj": "artykul", "udane": True, "tytul": "b"}
ART_30 = {"kiedy": "2026-09-30T16:52:00Z", "rodzaj": "artykul", "udane": True, "tytul": "c"}
PADL_29 = {"kiedy": "2026-09-29T16:55:00+00:00", "rodzaj": "artykul", "udane": False,
           "powod": "Substack nie potwierdzil"}
KOMENTARZ = {"kiedy": "2026-09-30T10:00:00+00:00", "rodzaj": "komentarz", "udane": True,
             "gdzie": "artykul"}

try:
    print("=== 1. OSTATNI DZIEN Z PLANU ===")
    plan_wtorek()
    sprawdz("sroda 30.09 -> termin wtorek 29.09",
            config.ostatni_dzien_planu(utc(2026, 9, 30)) == date(2026, 9, 29),
            config.ostatni_dzien_planu(utc(2026, 9, 30)))
    sprawdz("wtorek 29.09 -> termin ten sam dzien",
            config.ostatni_dzien_planu(utc(2026, 9, 29)) == date(2026, 9, 29))
    sprawdz("poniedzialek 28.09 -> termin poprzedni wtorek 22.09",
            config.ostatni_dzien_planu(utc(2026, 9, 28)) == date(2026, 9, 22))
    plan_miesieczny()
    sprawdz("KONTRDOWOD: plan [1, 8, 15, 22] we wtorek 29.09 -> termin 22.09 (piatego wtorku nie ma)",
            config.ostatni_dzien_planu(utc(2026, 9, 29)) == date(2026, 9, 22))
    sprawdz("plan miesieczny 1.10 -> termin 1.10",
            config.ostatni_dzien_planu(utc(2026, 10, 1)) == date(2026, 10, 1))
    config.ARTYKULY_MIESIECZNIE = 0
    sprawdz("plan bez artykulow -> brak terminu",
            config.ostatni_dzien_planu(utc(2026, 9, 30)) is None)

    print()
    print("=== 2. OSTATNI WYSTAWIONY ARTYKUL Z DZIENNIKA ===")
    dziennik(ART_22, PADL_29, KOMENTARZ, smieci=True)
    sprawdz("liczy sie tylko artykul z `udane`; porazka, komentarz i ucieta linia nie",
            stages.ostatni_wystawiony_artykul() == datetime(2026, 9, 22, 16, 54, 14, tzinfo=timezone.utc),
            stages.ostatni_wystawiony_artykul())
    dziennik(ART_22, ART_30)
    sprawdz("czas zapisany z Z na koncu tez sie czyta",
            stages.ostatni_wystawiony_artykul() == datetime(2026, 9, 30, 16, 52, tzinfo=timezone.utc),
            stages.ostatni_wystawiony_artykul())
    (KATALOG / "dziennik.jsonl").unlink()
    sprawdz("brak dziennika -> None, bez wyjatku", stages.ostatni_wystawiony_artykul() is None)

    print()
    print("=== 3. CZY DZIS PISZEMY ===")
    plan_wtorek()
    znacznik(None)
    dziennik(ART_22)
    ok, powod = artykul_z_puli.artykul_nalezny(utc(2026, 9, 29))
    sprawdz("wtorek bez artykulu od terminu -> piszemy (dzien z planu)",
            ok and "dzien artykulu z planu" in powod, powod)
    ok, powod = artykul_z_puli.artykul_nalezny(utc(2026, 9, 30))
    sprawdz("SEDNO: sroda po pustym wtorku -> NADRABIAMY termin 29.09",
            ok and "NADRABIAM termin 2026-09-29" in powod, powod)
    ok, powod = artykul_z_puli.artykul_nalezny(utc(2026, 10, 5))
    sprawdz("nadrabiamy az do nastepnego dnia z planu (poniedzialek 5.10)", ok, powod)
    dziennik(ART_22, PADL_29)
    ok, powod = artykul_z_puli.artykul_nalezny(utc(2026, 9, 30))
    sprawdz("nieudana publikacja nie zamyka terminu", ok, powod)
    dziennik(ART_22, ART_29)
    ok, powod = artykul_z_puli.artykul_nalezny(utc(2026, 9, 30))
    sprawdz("artykul z wtorku wyszedl -> w srode drugiego nie piszemy",
            not ok and "juz wyszedl" in powod, powod)
    ok, powod = artykul_z_puli.artykul_nalezny(utc(2026, 10, 6))
    sprawdz("nastepny wtorek otwiera nowy termin", ok and "z planu" in powod, powod)
    dziennik(ART_22, ART_30)
    ok, powod = artykul_z_puli.artykul_nalezny(utc(2026, 10, 1))
    sprawdz("artykul nadrobiony w srode zamyka termin wtorkowy", not ok, powod)

    dziennik(ART_22)
    znacznik(proby=2)
    ok, powod = artykul_z_puli.artykul_nalezny(utc(2026, 9, 30))
    sprawdz("gotowy tekst czeka z probami -> drugiego nie piszemy (wystawi rutyna dnia)",
            not ok and "czeka na wystawienie" in powod, powod)
    znacznik(proby=config.PROB_ZALEGLEGO_ARTYKULU)
    ok, powod = artykul_z_puli.artykul_nalezny(utc(2026, 9, 30))
    sprawdz("po wyczerpaniu prob gotowego tekstu nowy artykul juz wolno", ok, powod)
    znacznik(None)

    plan_miesieczny()
    dziennik(ART_22)
    ok, powod = artykul_z_puli.artykul_nalezny(utc(2026, 9, 29))
    sprawdz("KONTRDOWOD: stary plan miesieczny 29.09 nie pisze (to byla ta dziura)",
            not ok, powod)

    print()
    print("=== 4. ZEGAR CHODZI CODZIENNIE, GDY PLAN MA ARTYKULY ===")
    sprawdz("plan tygodniowy -> codziennie o godzinie artykulu",
            konfiguracja.on_calendar_artykulu(("Tue",), "16:30", 1) == ["*-*-* 16:30:00"])
    sprawdz("plan miesieczny -> codziennie o godzinie artykulu",
            konfiguracja.on_calendar_artykulu((), "16:30", 0, (1, 8, 15, 22)) == ["*-*-* 16:30:00"])
    sprawdz("zero artykulow -> zegara nie ma",
            konfiguracja.on_calendar_artykulu(("Tue",), "16:30", 0) == []
            and konfiguracja.on_calendar_artykulu((), "16:30", 0) == [])

    print()
    print("=== 5. DZIEN BEZ TERMINU KONCZY SIE KODEM 0 I NIE OTWIERA PRZEBIEGU ===")
    import preset  # noqa: E402
    import run  # noqa: E402
    import wersje_modeli  # noqa: E402

    otwarte = []

    class AtrapaDb:
        @staticmethod
        def connect():
            return "polaczenie"

        @staticmethod
        def start_run(conn, stage, **kw):
            otwarte.append(stage)
            return 7

        @staticmethod
        def finish_run(conn, run_id, status, stage, note=""):
            otwarte.append(status)

    stare_mod = (artykul_z_puli.db, artykul_z_puli._przebieg, artykul_z_puli.artykul_nalezny,
                 preset.wymagaj_aktywnego, run.zajmij_zamek, list(sys.argv),
                 wersje_modeli.sprawdz_i_przelacz)
    try:
        wersje_modeli.sprawdz_i_przelacz = lambda *a, **k: None
        artykul_z_puli.db = AtrapaDb
        artykul_z_puli._przebieg = lambda conn, run_id: 0
        preset.wymagaj_aktywnego = lambda cfg, co="": None
        run.zajmij_zamek = lambda: object()
        sys.argv = ["artykul_z_puli.py", "--wyslij"]
        plan_wtorek()
        config.PRESET = SimpleNamespace(nazwa="proba")
        artykul_z_puli.artykul_nalezny = lambda teraz=None: (False, "artykul z terminu juz wyszedl")
        kod = artykul_z_puli.main()
        sprawdz("nic do napisania -> kod 0 (codzienny zegar to nie awaria), bez przebiegu",
                kod == 0 and otwarte == [], (kod, otwarte))
        artykul_z_puli.artykul_nalezny = lambda teraz=None: (True, "NADRABIAM termin 2026-09-29")
        kod = artykul_z_puli.main()
        sprawdz("termin otwarty -> przebieg artykulu rusza i zamyka sie jako DONE",
                kod == 0 and otwarte == ["artykul-z-puli", "DONE"], (kod, otwarte))
    finally:
        (artykul_z_puli.db, artykul_z_puli._przebieg, artykul_z_puli.artykul_nalezny,
         preset.wymagaj_aktywnego, run.zajmij_zamek, sys.argv,
         wersje_modeli.sprawdz_i_przelacz) = stare_mod
finally:
    for k, v in STARE.items():
        setattr(config, k, v)
    stages.NIEWYSTAWIONY = STARY_ZNACZNIK

print()
print("=== WYNIK: %d zdanych, %d oblanych ===" % (zdane, oblane))
sys.exit(1 if oblane else 0)
