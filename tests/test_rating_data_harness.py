import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline.rating_data_harness import ESGRatingDataHarness


class FakeESGAgentHarness:
    def __init__(self, report_dir, expected_core_fields=60, allow_route_b=False):
        self.report_dir = Path(report_dir)
        self.expected_core_fields = expected_core_fields
        self.allow_route_b = allow_route_b

    def run(self):
        review_items = [
            {
                "review_id": "demo_001",
                "report_id": self.report_dir.name,
                "report_name": self.report_dir.name,
                "field_key": None,
                "source_route": "merge",
                "reason": "merged_row_count_invalid",
                "recommended_action": "rerun_or_validate_merge_outputs",
                "status": "pending",
                "details": {"expected_core_fields": self.expected_core_fields},
            }
        ]
        with open(self.report_dir / "human_review_queue.json", "w", encoding="utf-8") as f:
            import json

            json.dump(review_items, f)

        return {
            "report_dir": str(self.report_dir),
            "report_name": self.report_dir.name,
            "schema_rerun": {"execution_status": "skipped", "reason": "not_needed"},
            "route_b": {"execution_status": "skipped", "reason": "disabled"},
            "merge": {"execution_status": "completed", "reason": "ok"},
            "final_state": {
                "standard_row_count": self.expected_core_fields,
                "merged_row_count": self.expected_core_fields - 1,
            },
            "ok": False,
            "warnings": ["merged_row_count_invalid"],
            "review_needed": True,
            "review_reason_codes": ["merged_row_count_invalid"],
            "review_item_count": 1,
        }


class RatingDataHarnessTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        root = Path(self.tmpdir.name)
        self.report_dir = root / "demo_report"
        self.report_dir.mkdir()
        self.db_path = root / "agent_state.db"

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_wrapper_records_task_trace_and_review_items(self) -> None:
        with patch("pipeline.rating_data_harness.ESGAgentHarness", FakeESGAgentHarness):
            result = ESGRatingDataHarness(
                self.report_dir,
                industry="manufacturing",
                expected_core_fields=60,
                retrieval_profile="baseline_test",
                db_path=self.db_path,
            ).run()

        self.assertEqual(result["backend_task_status"], "review_required")
        self.assertTrue(result["backend_task_id"].startswith("task_"))

        trace = result["trace"]
        self.assertEqual(trace["task"]["industry"], "manufacturing")
        self.assertEqual(trace["task"]["retrieval_profile"], "baseline_test")
        self.assertEqual(
            [run["agent_name"] for run in trace["agent_runs"]],
            [
                "ESGAgentHarness",
                "SupervisorAgent",
                "RouteASchemaRerunAgent",
                "RouteBTextRAGAgent",
                "MergeAgent",
            ],
        )
        self.assertEqual(len(trace["review_items"]), 1)
        self.assertEqual(trace["review_items"][0]["reason"], "merged_row_count_invalid")


if __name__ == "__main__":
    unittest.main()
