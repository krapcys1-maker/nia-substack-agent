"""Recording must preserve explicit publication intent; never opens a browser."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("record_demo", ROOT / "narzedzia/nagraj_publikacje.py")
record_demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(record_demo)


class RecordingIntent(unittest.TestCase):
    def exercise(self, args, *, kill=False, note=None, active=True):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            file = root / "note.json"
            file.write_text(json.dumps(note or {"note": "A sample note.", "model": "example"}), encoding="utf-8")
            config = SimpleNamespace(DATA_DIR=root, KILL_SWITCH=kill)
            def require(*_):
                if not active:
                    raise RuntimeError("no active preset")
            preset = SimpleNamespace(wymagaj_aktywnego=Mock(side_effect=require))
            browser = SimpleNamespace(
                podlacz_sie=Mock(), sprawdz_sesje=Mock(),
                wystaw_notke=Mock(return_value={"wyslane": True, "blad": None}),
                wystaw_artykul=Mock(),
            )
            argv = ["record", "notka", "--plik", str(file), *args]
            error = None
            with patch.dict(sys.modules, config=config, preset=preset, browser=browser), patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                try:
                    code = record_demo.main()
                except (SystemExit, ValueError, RuntimeError) as exc:
                    error = exc
                    code = None
            return browser, code, error

    def test_recording_does_not_enable_publication(self):
        browser, code, error = self.exercise([])
        self.assertIsNone(error)
        self.assertEqual(code, 0)
        self.assertFalse(browser.wystaw_notke.call_args.kwargs["wyslij"])
        self.assertEqual(browser.wystaw_notke.call_count, 1)

    def test_explicit_publication_is_passed_once(self):
        browser, _, error = self.exercise(["--wyslij"])
        self.assertIsNone(error)
        self.assertTrue(browser.wystaw_notke.call_args.kwargs["wyslij"])
        self.assertEqual(browser.wystaw_notke.call_count, 1)

    def test_kill_switch_prevents_publication(self):
        browser, _, error = self.exercise(["--wyslij"], kill=True)
        self.assertIsInstance(error, SystemExit)
        browser.wystaw_notke.assert_not_called()
        browser.podlacz_sie.assert_not_called()

    def test_rejected_note_is_not_submitted(self):
        browser, _, error = self.exercise(["--wyslij"], note={"note": "Rejected.", "odrzucony": True})
        self.assertIsInstance(error, ValueError)
        browser.wystaw_notke.assert_not_called()

    def test_detached_preset_never_reaches_browser(self):
        browser, _, error = self.exercise(["--wyslij"], active=False)
        self.assertIsInstance(error, RuntimeError)
        browser.wystaw_notke.assert_not_called()
        browser.podlacz_sie.assert_not_called()

    def test_actual_stage_result_preserves_candidate_and_metadata(self):
        browser, _, error = self.exercise([], note={"type": "MYSL", "forma": "PYTANIE", "candidates": [{"note": "The selected text.", "model": "example"}]})
        self.assertIsNone(error)
        self.assertEqual(browser.wystaw_notke.call_args.args, ("The selected text.",))
        self.assertEqual(browser.wystaw_notke.call_args.kwargs["typ"], "MYSL")
        self.assertEqual(browser.wystaw_notke.call_args.kwargs["forma"], "PYTANIE")

    def test_failed_fact_check_is_not_submitted(self):
        browser, _, error = self.exercise(["--wyslij"], note={"note": "Unverified.", "safe_to_post": False})
        self.assertIsInstance(error, ValueError)
        browser.wystaw_notke.assert_not_called()


class CommentRecordingJournal(unittest.TestCase):
    def test_comment_target_does_not_conflict_with_action_journal(self):
        import browser as engine
        import run  # Load the normal target formatter before substituting config.

        for kind in ("notka", "artykul"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                target = {"rodzaj": kind, "id": 123, "url": "https://example.substack.com/p/example",
                          "pub": "Example", "komentarze": 4, "reakcje": 7}
                source = root / "comment.json"
                source.write_text(json.dumps({"target": target, "result": {
                    "candidates": [{"comment": "A specific observation."}]
                }}), encoding="utf-8")
                journal = root / "journal.jsonl"

                def publish(destination, content, *, wyslij, kontekst, rodzaj="komentarz"):
                    self.assertTrue(wyslij)
                    result = {"wyslane": True, "id": 456, "blad": None}
                    # Use the real journal function: a raw target used to pass
                    # rodzaj twice and fail AFTER a successful publication.
                    engine.dopisz_wynik(rodzaj, result, tekst=content,
                                       nasz_id=456, **kontekst)
                    engine.dopisz_wynik(rodzaj, result, **kontekst)
                    return result

                fake_browser = SimpleNamespace(podlacz_sie=Mock(),
                    wystaw_odpowiedz=Mock(side_effect=publish),
                    wystaw_komentarz=Mock(side_effect=publish))
                fake_config = SimpleNamespace(DATA_DIR=root, KILL_SWITCH=False)
                fake_preset = SimpleNamespace(wymagaj_aktywnego=Mock())
                with patch.dict(sys.modules, config=fake_config, preset=fake_preset, browser=fake_browser), \
                     patch.object(engine, "DZIENNIK", journal), \
                     patch.object(engine, "_W_SERII", {}), \
                     patch.object(engine, "_OSTATNIA", {}), \
                     patch.object(engine, "_POD_RZAD_ZLE", {}), \
                     patch.object(sys, "argv", ["record", "komentarz", "--plik", str(source), "--wyslij"]), \
                     contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(record_demo.main(), 0)

                rows = [json.loads(line) for line in journal.read_text(encoding="utf-8").splitlines()]
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["rodzaj"], "komentarz")
                self.assertTrue(rows[0]["udane"])
                self.assertEqual(rows[0]["nasz_id"], 456)
                self.assertEqual(rows[0]["publikacja"], "Example")
                self.assertEqual(rows[0]["komentarzy_przed"], 4)
                called = fake_browser.wystaw_odpowiedz if kind == "notka" else fake_browser.wystaw_komentarz
                called.assert_called_once()


class RecorderShutdown(unittest.TestCase):
    def test_queued_frame_after_closed_tab_is_ignored(self):
        self.check_ack_error(closed=True, expected_errors=[])

    def test_live_capture_error_is_recorded_without_interrupting_publication(self):
        self.check_ack_error(closed=False, expected_errors=["Frame acknowledgement: RuntimeError"])

    def check_ack_error(self, *, closed, expected_errors):
        with tempfile.TemporaryDirectory() as folder:
            recorder = record_demo.Recorder(Path(folder))
            page = Mock()
            page.is_closed.return_value = closed
            session = Mock()
            session.send.side_effect = lambda method, params: (
                (_ for _ in ()).throw(RuntimeError("detached"))
                if method == "Page.screencastFrameAck" else None)
            context = Mock()
            context.new_cdp_session.return_value = session
            recorder.attach(context, page)
            callback = session.on.call_args.args[1]
            callback({"sessionId": 9})
            recorder.save({"wyslane": True})
            manifest = json.loads((Path(folder) / "recording.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["frames"], [])
            self.assertEqual(manifest["capture_errors"], expected_errors)
            self.assertTrue(manifest["result"]["wyslane"])


if __name__ == "__main__":
    unittest.main()
