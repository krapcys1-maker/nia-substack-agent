# -*- coding: utf-8 -*-
"""Sciezka persony w artykule: trasa promptow, przekazanie dowodow, glebokosc.

Od 9 wrzesnia 2026 preset z persona ocenia material inaczej niz kartridz
bezosobowy: `stages.warto_pisac` liczy udokumentowane watki JEDNEJ historii
(`_ocena_historii_persony`) zamiast filarow eseju o instytucjach, karta niesie
scene ze zrodla (`scene_sources`) zamiast zdania z briefu (`the_scene`),
a kotwica dlugosci nie zada drugiej dziedziny.

BLOKI PRESETU SA TU SYNTETYCZNE, nie czytane z `presety/nia-unfiltered/`.
Silnik i kartridz jada osobnymi galeziami; test silnika, ktory oblewa po
edycji kartridza, wiazalby je z powrotem. Prawdziwy kartridz sprawdza
`narzedzia/presety.py sprawdz`.

Bez sieci, bez platnych wywolan. Uruchamiac z korzenia repo:
    PYTHONIOENCODING=utf-8 python agent-v2/tests/test_persona_story_contract.py
"""
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "agent-v2"))
os.environ["AGENT_V2_BEZ_KONFIGURACJI"] = "1"
import config
import llm
import stages
import artykul_z_puli as article
import style

BLOKI = {
    "linia_redakcyjna": "You are NIA, a test identity with opinions. They wanted an assistant.",
    "glos_wspolny": "Shared voice block for the test: say what you think.",
    "glos_artykulu": "Article voice block for the test: same woman, more room.",
    "glos_notki": "Note voice block for the test.",
    "glos_komentarza": "Comment voice block for the test.",
    "okladka": "Cover block for the test.",
    "kogo_szukamy": "Who we look for, test block.",
    "oswiadczenie": "Author statement, test block.",
}


class PersonaStoryContract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.old = config.uzyj_katalogu_danych(Path(self.tmp.name))
        self.addCleanup(config.przywroc_katalog_danych, self.old)
        for target, name in ((socket.socket, "connect"), (llm, "call")):
            p = patch.object(target, name, side_effect=AssertionError("No network or paid calls"))
            p.start()
            self.addCleanup(p.stop)
        p = patch.multiple(config, PERSONA_WLACZONA=True, PRESET_BLOKI=dict(BLOKI))
        p.start()
        self.addCleanup(p.stop)

    def card(self):
        return {"confirmed_claims": [
            {"claim": "A builder made a local editor.", "evidence": "I built a local editor.", "url": "https://example.org/build"},
            {"claim": "Users tried the editor.", "evidence": "Users tried the editor.", "url": "https://example.org/build"},
            {"claim": "Their feedback changed the design.", "evidence": "Their feedback changed the design.", "url": "https://example.org/build"},
        ]}

    def assessment(self):
        return {"reader_interest": "A useful small project improved through user feedback.",
                "answerable_questions": [
                    {"question": q, "answer": "Supported detail.", "claim_indices": [i]}
                    for i, q in enumerate(("What did she build?", "Who used it?", "What changed?"))]}

    def test_small_builder_can_support_article_without_institutional_pillars(self):
        with patch.object(llm, "call", return_value=json.dumps(self.assessment())) as model:
            result = stages.warto_pisac(None, 1, self.card())
        self.assertEqual(model.call_count, 1)
        self.assertEqual(model.call_args.args[0], "warto_pisac")
        self.assertEqual(result["werdykt"], "PISZ")
        self.assertEqual(article.glebokosc_z_oceny(result), "RICH")
        self.assertNotIn("named_decider", result)
        prompt = model.call_args.args[2]
        self.assertIn("Useful work by a small builder", prompt)
        self.assertIn("I built a local editor", prompt)

    def test_duplicates_and_missing_evidence_cannot_inflate_depth(self):
        result = self.assessment()
        result["answerable_questions"][1]["claim_indices"] = [0]
        result["answerable_questions"][2]["claim_indices"] = [99]
        output = stages._ocena_historii_persony(result, self.card())
        self.assertEqual(output["depth"], "SINGLE")
        self.assertEqual(len(output["answerable_questions"]), 1)
        result["answerable_questions"][0]["claim_indices"] = [True]
        result["answerable_questions"][1]["claim_indices"] = [-1]
        self.assertEqual(stages._ocena_historii_persony(result, self.card())["depth"], "THIN")

    def test_unfetched_claim_cannot_support_story_thread(self):
        card = self.card()
        for c in card["confirmed_claims"]:
            c["not_fetched"] = True
        self.assertEqual(stages._ocena_historii_persony(self.assessment(), card)["depth"], "THIN")

    def test_professional_route_keeps_its_existing_criteria(self):
        with patch.object(config, "PERSONA_WLACZONA", False), \
             patch.object(llm, "call", return_value="{}") as model:
            result = stages.warto_pisac(None, 1, self.card())
        self.assertNotIn("persona_story", result)
        self.assertEqual(result["werdykt"], "ODLOZ")
        self.assertIn("THE CONTRADICTED BELIEF", model.call_args.args[2])

    def test_actual_writer_gets_voice_and_verified_context_without_scene_from_brief(self):
        card = self.card()
        card["the_scene"] = "An invented encounter after dinner."
        card["scene_sources"] = [{"url": "https://example.org/build", "excerpts": ["Users tried the editor."]}]
        with patch.object(style, "load_profiles", return_value=("", "")), \
             patch.object(style, "przyklady_albo_pusto", return_value=[]), \
             patch.object(llm, "call", return_value='{"body":"A supplied draft."}') as model:
            stages.write(None, 1, card, "RICH")
        self.assertEqual(model.call_count, 1)
        system, prompt = model.call_args.args[1:3]
        # Tozsamosc i glos artykulu z presetu ida w systemie, nie w briefie.
        self.assertIn("You are NIA, a test identity", system)
        self.assertIn("They wanted an assistant", system)
        self.assertIn("Article voice block for the test", system)
        # Scena ze zrodla wchodzi; zdanie z briefu nie.
        self.assertIn("Users tried the editor", prompt)
        self.assertNotIn("invented encounter", prompt)
        # Zadnych limitow liczbowych na mowienie o sobie ani drugiej dziedziny.
        self.assertNotIn("At most one sentence per article", prompt)
        self.assertNotIn("more than one field", prompt)
        self.assertIn(config.kotwica_dlugosci("RICH", persona=True), prompt)

    def test_persona_length_anchor_never_asks_for_a_second_field(self):
        wersje = {g: config.kotwica_dlugosci(g, persona=True) for g in ("RICH", "SINGLE", "THIN")}
        self.assertEqual(len(set(wersje.values())), 3)
        for g, zdanie in wersje.items():
            self.assertNotIn("more than one field", zdanie, g)
            self.assertNotIn("second mechanism", zdanie, g)
        # Kartridz bezosobowy trzyma swoja kotwice, wraz z druga dziedzina.
        self.assertIn("more than one field", config.kotwica_dlugosci("RICH"))
        self.assertEqual(config.kotwica_dlugosci("THIN", persona=True),
                         config.kotwica_dlugosci("THIN"))
        self.assertEqual(config.kotwica_dlugosci("", persona=True), wersje["SINGLE"])

    def test_shape_feedback_stays_in_report_and_fact_feedback_returns(self):
        # Uwagi o KSZTALCIE (zwrot do czytelnika, eskalacja) nie wracaja jako
        # regula — po dziesieciu tekstach bylyby podpisem maszyny. Zarzut
        # o FAKT wraca: to jedyna uwaga o pokryciu, jaka ta petla niesie
        # (`test_forma_artykulu_bramka`: „wyciszono za duzo"). Falszywy alarm
        # o zawodzie autorki zatrzymuja oswiadczenie dla recenzenta i klauzula
        # o tozsamosci w systemie pisarza, nie wyciszenie zarzutu.
        path = config.ARTICLES_DIR / "previous.uwagi.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("- {'gate': 'FAKT_BEZ_POKRYCIA', 'detail': 'A price nobody sourced.'}\n"
                        "- {'gate': 'CZYTELNIK_NIEPRZYLAPANY', 'detail': 'Add a confrontation.'}\n"
                        "- {'gate': 'ARTEFAKT', 'detail': 'Remove a placeholder.'}\n", encoding="utf-8")
        feedback = stages.ostatnie_uwagi()
        self.assertIn("A price nobody sourced", feedback)
        self.assertNotIn("confrontation", feedback)
        self.assertIn("placeholder", feedback)
        system = stages.system_pisarza()
        self.assertIn("The supplied identity establishes who the author is", system)

    def test_all_blank_depth_fields_buy_exactly_one_more_question(self):
        # Pomiar z 9 wrzesnia 2026 (patrz `test_puste_pole_to_nie_odmowa.py`):
        # to samo wywolanie raz oddalo zasieg na 26 slow, a raz pusty napis.
        # Pusty napis jest wiec brakiem odpowiedzi, nie werdyktem.
        self.assertTrue(article._pola_glebi_puste({"second_act": "", "beyond_one_place": ""}))
        self.assertTrue(article._pola_glebi_puste(
            {"second_act": "", "beyond_one_place": "", "story_material": ""}))
        self.assertTrue(article._pola_glebi_puste({}))
        self.assertTrue(article._pola_glebi_puste({"second_act": None, "beyond_one_place": ""}))
        self.assertFalse(article._pola_glebi_puste({"story_material": "A documented setup."}))
        self.assertFalse(article.uniesie_artykul({"second_act": "", "beyond_one_place": ""})[0])

    def test_one_documented_project_passes_before_research_without_a_sequel(self):
        brief = {"second_act": "", "beyond_one_place": "",
                 "story_material": "The record describes the builder's design, users' feedback and a measured limitation."}
        self.assertTrue(article.uniesie_artykul(brief)[0])
        self.assertFalse(article._pola_glebi_puste(brief))
        brief["story_material"] = ""
        self.assertFalse(article.uniesie_artykul(brief)[0])

    def test_run_article_path_reads_persona_verdict_before_pillars(self):
        # `run.py` ma wlasna sciezke artykulu i czytal `ocena["ile_filarow"]`
        # na twardo; z persona to KeyError polykany jako „awaria bramki".
        src = (ROOT / "agent-v2" / "run.py").read_text(encoding="utf-8")
        i = src.index("ocena = stages.warto_pisac(conn, run_id, card)")
        self.assertLess(src.index("persona_story", i), src.index('ocena["ile_filarow"]', i))
        self.assertIn("answerable_questions", src[i:i + 1200])


if __name__ == "__main__":
    unittest.main()
