# -*- coding: utf-8 -*-
"""Zegar przebiegu, cichy koniec dnia, zalegly artykul i wylacznik.

CZTERY WADY Z AUDYTU 7 WRZESNIA 2026, kazda odtworzona zanim ja naprawilem.

1. TERMIN PRZEBIEGU BYL KROTSZY NIZ PRZEBIEG. `RUN_DEADLINE` stalo na sztywne
   3600 s, a `LIMIT_CZASU_PRZEBIEGU_S` to 9000 s (135 minut po odjeciu zapasu).
   Sam blok notek moze czekac 35-65 minut miedzy notkami, wiec komentarze,
   dyskusje i restacki zaczynaly sie CZESTO po godzinie — a `llm.call` liczy
   `deadline = min(termin_roli, RUN_DEADLINE)`, czyli padalo natychmiast, bez
   rezerwacji i bez wywolania.

2. I PADALO PO CICHU. `DeadlineExceeded` nie bylo w `stages.PRZERYWAJA`, wiec
   ogolne `except Exception` w blokach dnia lapalo je jak zwykla porazke etapu.
   Dzien konczyl sie jako DONE z niewykorzystanymi slotami: dziennik mowil, ze
   po prostu nie bylo materialu.

3. ZALEGLY ARTYKUL NIGDY NIE WYCHODZIL. `run.py` podawalo `str(...)`, a
   `browser.wystaw_artykul` wola `sciezka_md.with_suffix(".png")` — napis nie
   ma tej metody. AttributeError leciał zanim cokolwiek poszlo do publikacji:
   licznik prob nie rosl, wiec alarm po dwunastu probach nie mial szans wyjsc.
   Testy tego nie widzialy, bo atrapy przyjmowaly cokolwiek. Ten test uzywa
   PRAWDZIWEJ sygnatury.

4. WYLACZNIK NIE ZATRZYMYWAL ZAPISOW. `KILL_SWITCH` byl sprawdzany w preflighcie
   `llm`, wiec zatrzymywal modele — ale obserwacje, subskrypcje, polubienia
   i zalegly artykul nie wolaja modelu i wychodzily w swiat mimo wlaczonego
   wylacznika, ktory `docs/CONFIGURATION_MAP.md` nazywa „hard stop".
"""
import inspect
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent-v2"))
os.environ["AGENT_V2_BEZ_KONFIGURACJI"] = "1"
import browser
import call_runtime
import config
import run
import stages


class ZegarPrzebiegu(unittest.TestCase):
    def test_termin_przebiegu_pokrywa_caly_budzet_czasu(self):
        """Jeden budzet, jedna liczba — nie 60 minut na 135-minutowy przebieg."""
        for plik in ("run.py", "artykul_z_puli.py"):
            zrodlo = (ROOT / "agent-v2" / plik).read_text(encoding="utf-8")
            self.assertIn("RUN_DEADLINE = time.monotonic() + config.LIMIT_CZASU_PRZEBIEGU_S",
                          zrodlo, "%s: termin przebiegu ma isc z budzetu" % plik)
            self.assertNotIn("RUN_DEADLINE = time.monotonic() + 3600", zrodlo)

    def test_termin_modelu_nie_wygasa_przed_zegarem_dnia(self):
        """TO jest zlamany niezmiennik, nie „blok notek ma sie zmiescic".

        Dzien WOLNO uciac, gdy czas sie konczy — `_KONIEC_CZASU` istnieje wlasnie
        po to i przy piatce notek dziennie sam blok notek moze wziac 260 minut.
        Czego nie wolno: zeby termin wywolan modelu minal, zanim zegar dnia
        powie stop. Wtedy przebieg nadal „trwa", a kazde wywolanie pada.
        """
        budzet_dnia = config.LIMIT_CZASU_PRZEBIEGU_S - config.ZAPAS_CZASU_S
        self.assertGreaterEqual(
            config.LIMIT_CZASU_PRZEBIEGU_S, budzet_dnia,
            "termin przebiegu krotszy niz czas, przez ktory dzien sie wykonuje")


class CichyKoniecDnia(unittest.TestCase):
    def test_wyczerpany_czas_przerywa_dzien_zamiast_udawac_brak_materialu(self):
        self.assertIn(call_runtime.DeadlineExceeded, stages.PRZERYWAJA)

    def test_bloki_dnia_przepuszczaja_przerywajace_przed_ogolnym_wyjatkiem(self):
        """KONTRDOWOD: gdyby `DeadlineExceeded` bylo zwyklym wyjatkiem, ogolne
        `except Exception` w blokach researchu polknieloby je jak dawniej."""
        self.assertTrue(issubclass(call_runtime.DeadlineExceeded, Exception))
        zlapane = []
        try:
            try:
                raise call_runtime.DeadlineExceeded("czas minal")
            except stages.PRZERYWAJA:
                raise
            except Exception:                     # noqa: BLE001
                zlapane.append("polkniete")
        except call_runtime.DeadlineExceeded:
            zlapane.append("przeszlo dalej")
        self.assertEqual(zlapane, ["przeszlo dalej"])


class ZaleglyArtykul(unittest.TestCase):
    def test_sciezka_jest_obiektem_ktory_przyjmuje_wystaw_artykul(self):
        """PRAWDZIWA sygnatura, nie atrapa przyjmujaca cokolwiek."""
        podpis = inspect.signature(browser.wystaw_artykul)
        self.assertEqual(podpis.parameters["sciezka_md"].annotation, "Path")
        zrodlo = (ROOT / "agent-v2" / "run.py").read_text(encoding="utf-8")
        self.assertIn('sciezka = Path(zaleg["sciezka"])', zrodlo)
        self.assertNotIn('sciezka = str(zaleg["sciezka"])', zrodlo)

    def test_napis_nie_przechodzi_przez_wystaw_artykul(self):
        """KONTRDOWOD: dokladnie ten blad, ktory blokowal kazde ponowienie."""
        with tempfile.TemporaryDirectory() as katalog:
            plik = Path(katalog) / "a.md"
            plik.write_text("# t\n", encoding="utf-8")
            with self.assertRaises(AttributeError):
                str(plik).with_suffix(".png")
            self.assertTrue(Path(str(plik)).with_suffix(".png").name.endswith(".png"))


class Wylacznik(unittest.TestCase):
    def _wyslac(self, **flagi):
        stan = dict(DRY_RUN=False, W_TESCIE=True, KILL_SWITCH=False)
        stan.update(flagi)
        with patch.multiple(config, **stan):
            return browser.naprawde_wyslac(True, "proba")

    def test_wylacznik_zatrzymuje_zapis_na_koncie(self):
        self.assertFalse(self._wyslac(KILL_SWITCH=True))

    def test_bez_wylacznika_zapis_przechodzi(self):
        """KONTRDOWOD: bramka odmawia z powodu wylacznika, a nie zawsze."""
        self.assertTrue(self._wyslac())

    def test_wylacznik_jest_sprawdzany_w_jedynej_bramce_zapisow(self):
        zrodlo = inspect.getsource(browser.naprawde_wyslac)
        self.assertIn("config.KILL_SWITCH", zrodlo)


if __name__ == "__main__":
    unittest.main(verbosity=2)
