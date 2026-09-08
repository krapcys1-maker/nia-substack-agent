"""Preview summaries retain incurred cost on both success and failure; no API."""
import argparse
from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import socket
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "agent-v2"), str(ROOT / "narzedzia")]
os.environ["AGENT_V2_BEZ_KONFIGURACJI"] = "1"
import config
import db
import llm
import preset
import proba_glosu
import stages


class PreviewCost(unittest.TestCase):
    def test_completed_and_failed_previews_include_recorded_calls(self):
        for failed in (False, True):
            with self.subTest(failed=failed), tempfile.TemporaryDirectory() as directory:
                old = config.uzyj_katalogu_danych(Path(directory))
                def generate(conn, run_id, **kwargs):
                    db.record_call(conn, run_id=run_id, provider="offline", model="fixture",
                                   purpose="fixture", cost_usd=0.0123, ok=not failed)
                    if failed:
                        raise RuntimeError("fixture failure after cost was recorded")
                    return [{"candidates": [{"text": "Credit her work.", "request_sha256": "fixture"}]}]
                try:
                    with patch.object(argparse.ArgumentParser, "parse_args", return_value=
                                      argparse.Namespace(live=True, samples=1, slot=0)), \
                         patch.multiple(config, PERSONA_WLACZONA=True, NOTE_MIX_OTHER_DAY=["MYSL"]), \
                         patch.object(preset, "aktywacja_nadal_wazna", return_value=""), \
                         patch.object(stages, "notki_dnia", side_effect=generate), \
                         patch.object(llm, "call", side_effect=AssertionError("paid call forbidden")), \
                         patch.object(socket.socket, "connect", side_effect=AssertionError("network forbidden")), \
                         redirect_stdout(io.StringIO()):
                        if failed:
                            with self.assertRaisesRegex(RuntimeError, "fixture failure"):
                                proba_glosu.main()
                        else:
                            proba_glosu.main()
                    conn = db.connect()
                    row = conn.execute("SELECT status,cost_usd,tryb,finished_at FROM runs").fetchone()
                    conn.close()
                    self.assertEqual(row[0], "FAILED" if failed else "DONE")
                    self.assertAlmostEqual(row[1], 0.0123)
                    self.assertEqual(row[2], "test")
                    self.assertTrue(row[3])
                finally:
                    config.przywroc_katalog_danych(old)


if __name__ == "__main__":
    unittest.main()
