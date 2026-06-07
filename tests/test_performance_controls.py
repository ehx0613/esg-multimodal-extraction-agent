import json
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace

from utils.call_tracker import LLMCallTracker, model_call_allowed, record_model_call
from utils.llm_schema_matcher import llm_match_row_to_schema
from utils.schema_match_cache import row_hash


class PerformanceControlTests(unittest.TestCase):
    def test_call_tracker_records_usage_and_enforces_fast_budget(self):
        usage = SimpleNamespace(prompt_tokens=10, completion_tokens=4, total_tokens=14)
        response = SimpleNamespace(usage=usage)

        with tempfile.TemporaryDirectory() as tmp:
            tracker = LLMCallTracker(Path(tmp), run_mode="fast")
            with tracker.activate():
                for _ in range(10):
                    record_model_call(
                        stage="vlm_table_extract",
                        model="test-vlm",
                        started_at=time.time(),
                        response=response,
                    )
                self.assertFalse(model_call_allowed("vlm_table_extract"))

            summary = json.loads(
                (Path(tmp) / "run_cost_summary.json").read_text(encoding="utf-8")
            )

        self.assertEqual(summary["calls"], 10)
        self.assertEqual(summary["total_tokens"], 140)

    def test_fast_schema_judge_never_escalates_to_plus(self):
        calls = []

        def fake_call(client, prompt, candidates, model):
            calls.append((model, len(candidates)))
            return {
                "matched": True,
                "field_key": candidates[0]["field_key"],
                "confidence": 0.7,
                "reason": "ambiguous",
                "judge_model": model,
            }

        row = {
            "metric_name": "ambiguous metric",
            "unit": "tons",
            "values": {"2024": "1"},
        }
        with tempfile.TemporaryDirectory() as tmp:
            tracker = LLMCallTracker(Path(tmp), run_mode="fast")
            with (
                tracker.activate(),
                unittest.mock.patch("utils.llm_schema_matcher.DASHSCOPE_API_KEY", "test"),
                unittest.mock.patch("utils.llm_schema_matcher._get_client", return_value=object()),
                unittest.mock.patch("utils.llm_schema_matcher._call_schema_judge", side_effect=fake_call),
            ):
                result = llm_match_row_to_schema(row)

        self.assertEqual(calls, [])
        self.assertEqual(result["reason"], "no_compatible_schema_candidates")

    def test_row_hash_ignores_layout_whitespace_and_punctuation_noise(self):
        first = {
            "metric_name": "Scope 1 排放量",
            "unit": "tCO2e",
            "values": {"2024": "1,234.0"},
            "evidence_text": "Scope 1：1,234.0 tCO2e",
        }
        second = {
            "metric_name": " scope-1排放量 ",
            "unit": "TCO2E",
            "values": {" 2024 ": "1 234 0"},
            "evidence_text": "scope 1 1 234 0 tco2e",
        }

        self.assertEqual(row_hash(first), row_hash(second))


if __name__ == "__main__":
    unittest.main()
