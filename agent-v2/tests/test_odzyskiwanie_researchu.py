"""Search recovery reuses paid work; transport and budget regression tests."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config
import db
import llm
import httpx


class SearchRecoveryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        config.uzyj_katalogu_danych(Path(self.tmp.name))
        self.conn = db.connect()
        self.run = db.start_run(self.conn, "test-search-recovery")
        self.patches = [patch.object(config, key, value) for key, value in {
            "DRY_RUN": False, "W_TESCIE": True, "WOLNO_WOLAC_MODEL": True,
            "KILL_SWITCH": False, "DEEPSEEK_API_KEY": "test-key",
            "PONOWIENIA": 1, "PONOWIENIE_ODSTEP_S": 0,
            "RUN_LIMIT_USD": 10.0, "NO_LIMIT": True,
        }.items()]
        for item in self.patches:
            item.start()
        self.sources = patch.object(llm, "_read_search_sources", return_value=[
            {"url": "https://example.org/evidence", "text": "Documentary evidence, not just a URL."}])
        self.sources.start()
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.conn.close()
        self.sources.stop()
        for item in reversed(self.patches):
            item.stop()
        self.tmp.cleanup()

    def rows(self):
        return self.conn.execute("SELECT * FROM calls WHERE run_id=? ORDER BY id", (self.run,)).fetchall()

    def invoke(self):
        return llm.call("curiosity", "Return JSON", "Find evidence", conn=self.conn,
                        run_id=self.run, web_search=True)

    def test_repair_retry_does_not_repeat_paid_search(self):
        attempts = 0
        def repair(*args):
            nonlocal attempts
            attempts += 1
            self.assertEqual(self.rows()[0]["web_searches"], 9)
            self.assertGreater(self.rows()[0]["cost_usd"], 0)
            self.assertIn("Do not infer facts from a URL", args[2])
            self.assertIn("Documentary evidence, not just a URL.", args[2])
            if attempts == 1:
                raise httpx.RemoteProtocolError("interrupted reconstruction")
            return '{"facts": []}', 100, 20, 0, 0
        with patch.object(llm, "_call_deepseek_responses", return_value=("", 2000, 700, 9, ["https://example.org/evidence"])) as search, patch.object(llm, "_call_deepseek", side_effect=repair):
            self.assertEqual(json.loads(self.invoke()), {"facts": []})
        self.assertEqual(search.call_count, 1)
        self.assertEqual(attempts, 2)
        self.assertEqual(len(self.rows()), 2)

    def test_failed_repair_preserves_search_cost(self):
        with patch.object(llm, "_call_deepseek_responses", return_value=("{broken", 2000, 700, 4, ["https://example.org/evidence"])) as search, patch.object(llm, "_call_deepseek", side_effect=RuntimeError("repair failed")):
            with self.assertRaisesRegex(RuntimeError, "repair failed"):
                self.invoke()
        self.assertEqual(search.call_count, 1)
        self.assertEqual([r["ok"] for r in self.rows()], [1, 0])
        self.assertGreater(self.rows()[0]["cost_usd"], 0)

    def test_search_cost_is_checked_before_repair(self):
        with patch.object(config, "RUN_LIMIT_USD", 0.000001), patch.object(llm, "_call_deepseek_responses", return_value=("", 2000, 700, 9, ["https://example.org/evidence"])), patch.object(llm, "_call_deepseek") as repair:
            with self.assertRaises(llm.BudgetExceeded):
                self.invoke()
        repair.assert_not_called()
        self.assertEqual(len(self.rows()), 1)

    def test_no_source_does_not_invent_evidence(self):
        with patch.object(llm, "_call_deepseek_responses", return_value=("", 2000, 700, 4, [])), patch.object(llm, "_call_deepseek") as repair:
            with self.assertRaises(llm.Truncated):
                self.invoke()
        repair.assert_not_called()
        self.assertEqual(self.rows()[0]["web_searches"], 4)

    def test_valid_json_needs_no_reconstruction(self):
        with patch.object(llm, "_call_deepseek_responses", return_value=('{"facts":[]}', 2000, 700, 4, [])), patch.object(llm, "_call_deepseek") as repair:
            self.assertEqual(json.loads(self.invoke()), {"facts": []})
        repair.assert_not_called()

    def test_reconstruction_uses_streamed_json_without_search_tools(self):
        events = [json.dumps({"choices": [{"delta": {"content": '{"facts":[]}'}, "finish_reason": "stop"}], "usage": {"prompt_tokens": 100, "completion_tokens": 6}}), "[DONE]"]
        with patch.object(httpx, "stream") as stream:
            stream.return_value.__enter__.return_value.iter_lines.return_value = ["data: " + event for event in events]
            result = llm._call_deepseek("curiosity", "Return JSON", "Recovered evidence")
        request = stream.call_args.kwargs["json"]
        self.assertTrue(request["stream"])
        self.assertEqual(request["response_format"], {"type": "json_object"})
        self.assertEqual(request["thinking"], {"type": "disabled"})
        self.assertNotIn("tools", request)
        self.assertEqual(json.loads(result[0]), {"facts": []})

    def test_search_requests_native_json_and_returns_usage_without_repair(self):
        payload = {"output": [{"type": "web_search_call", "url": "https://example.org/evidence#ws_call_id=123"}], "usage": {"input_tokens": 2000, "output_tokens": 700}}
        with patch.object(httpx, "stream") as stream, patch.object(llm, "_deepseek_pick_from_urls") as repair:
            stream.return_value.__enter__.return_value.iter_lines.return_value = ["data: " + json.dumps({"type": "response.completed", "response": payload})]
            result = llm._call_deepseek_responses("curiosity", "Return JSON", "Find evidence")
        self.assertEqual(stream.call_args.kwargs["json"]["text"]["format"]["type"], "json_object")
        self.assertEqual(result, ("", 2000, 700, 1, ["https://example.org/evidence"]))
        repair.assert_not_called()


if __name__ == "__main__":
    unittest.main()
