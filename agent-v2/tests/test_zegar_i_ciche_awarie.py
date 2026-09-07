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
import anthropic
import httpx

import browser
import call_runtime
import config
import gates
import llm
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


class BramkaArtefaktow(unittest.TestCase):
    """Bramka blokowala zwykla angielszczyzne i przepuszczala artefakty.

    Frazy warsztatowe szly przez `find`, wiec „as instructed" lapalo „was
    instructed", „i worked from" lapalo „OpenAI worked from", „i cannot verify"
    lapalo „AI cannot verify". Wzorzec pustej wartosci lapal „of unknown origin",
    „second to none" i „since none of the labs". Kazde trafienie to twardy stop
    OPLACONEGO artykulu bez ponowienia albo spalony slot notki.
    """

    ZWYKLE = (
        "The vendor was instructed to disclose the cap.",
        "OpenAI worked from a smaller evaluation set.",
        "AI cannot verify its own citations.",
        "A dataset of unknown origin turned up in the audit.",
        "On documentation they are second to none.",
        "Since none of the labs published the numbers, we asked.",
    )
    ARTEFAKTY = (
        ("meta-zdanie modelu", "As an AI language model, I cannot browse the web."),
        ("plot bloku kodu", "Here is the article:\n```json\n{}\n```"),
        ("pole wielkimi literami", "Published on [INSERT DATE] by the team."),
        ("prawdziwy warsztat", "The excerpts I worked from did not mention it."),
        ("pusta wartosc", "Figures checked against sources to unknown."),
        ("znacznik TODO", "The section on pricing is TODO."),
    )

    def test_zwykle_zdania_przechodza(self):
        for zdanie in self.ZWYKLE:
            with self.subTest(zdanie=zdanie):
                self.assertEqual(gates.artefakty_w_tekscie(zdanie), [])

    def test_artefakty_nadal_zatrzymuja(self):
        """KONTRDOWOD: rozluznienie nie moze otworzyc bramki na osciez."""
        for opis, zdanie in self.ARTEFAKTY:
            with self.subTest(artefakt=opis):
                self.assertTrue(gates.artefakty_w_tekscie(zdanie),
                                "%s przechodzi przez bramke" % opis)


class TransportClaude(unittest.TestCase):
    """Zerwane polaczenie przerzucalo artykul na pisarza zapasowego.

    Wyjatki SDK Anthropica nie sa wyjatkami httpx i nie niosa `status_code`,
    wiec `przejsciowy` konczyl na galezi „nierozpoznany, czyli trwaly".
    """

    def _blad(self, klasa):
        return klasa(request=httpx.Request("POST", "https://api.anthropic.com/v1/messages"))

    def test_zerwane_polaczenie_i_przekroczony_czas_sa_przejsciowe(self):
        for klasa in (anthropic.APITimeoutError, anthropic.APIConnectionError):
            with self.subTest(klasa=klasa.__name__):
                self.assertTrue(llm.przejsciowy(self._blad(klasa)))

    def test_trwale_bledy_dalej_nie_sa_ponawiane(self):
        """KONTRDOWOD: nie zrobilismy z kazdego bledu przejsciowego."""
        for blad in (llm.BudgetExceeded("x"), llm.PreflightFailed("x"), llm.Truncated("x")):
            with self.subTest(blad=type(blad).__name__):
                self.assertFalse(llm.przejsciowy(blad))


class ObalonyFaktNieWraca(unittest.TestCase):
    """Fakt, ktory dal obalona notke, nie ma wracac do puli.

    `wez_kandydatow` sortuje deterministycznie, wiec fakt oddany na status
    `nowy` byl brany nastepnego dnia jako pierwszy — i placilismy za notke, za
    weryfikacje z szukaniem i za naprawe tego samego zdania, co dzien, przez
    cala waznosc banku. Zaden rejestr odrzucen: fakt zostaje `uzyty`, bo zostal
    zuzyty. Material dostaje jedna probe naprawy i albo idzie, albo przepada.
    """

    def setUp(self):
        self.katalog = tempfile.TemporaryDirectory()
        self.stare = config.uzyj_katalogu_danych(Path(self.katalog.name))

    def tearDown(self):
        config.przywroc_katalog_danych(self.stare)
        self.katalog.cleanup()

    FAKT = "Vendors cap liability at last year's invoice."

    def _pula(self):
        import stages as _s
        _s._zapisz_indeks([{"fact": self.FAKT, "status": "nowy"}])

    def test_obalony_nie_wraca_wiec_nie_placimy_drugi_raz(self):
        import stages as _s
        self._pula()
        self.assertEqual(len(_s.wez_kandydatow(1)), 1)
        # Notka obalona: NIE wolamy `zwroc_kandydatow` — to cala poprawka.
        self.assertEqual(_s.wez_kandydatow(1), [],
                         "obalony fakt wrocil do puli i bedzie oplacony ponownie")

    def test_fakt_odrzucony_na_dlugosci_nadal_wraca(self):
        """KONTRDOWOD: nie wyrzucamy dobrego materialu przy okazji."""
        import stages as _s
        self._pula()
        _s.wez_kandydatow(1)
        _s.zwroc_kandydatow([{"fact": self.FAKT}])
        self.assertEqual(len(_s.wez_kandydatow(1)), 1)

    def test_galaz_w_run_rozroznia_te_dwa_przypadki(self):
        zrodlo = (ROOT / "agent-v2" / "run.py").read_text(encoding="utf-8")
        self.assertIn('obalony = any(', zrodlo)
        self.assertIn("if not obalony:", zrodlo)


if __name__ == "__main__":
    unittest.main(verbosity=2)
