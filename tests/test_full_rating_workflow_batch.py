import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.run_full_rating_workflow_batch import collect_report_dirs, run_batch


class FullRatingWorkflowBatchTests(unittest.TestCase):
    def test_collect_report_dirs_requires_merged_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            valid = root / "001_valid"
            invalid = root / "002_invalid"
            valid.mkdir()
            invalid.mkdir()
            (valid / "merged_esg_results.json").write_text("[]", encoding="utf-8")

            self.assertEqual(collect_report_dirs(root), [valid])

    def test_run_batch_writes_summary_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report_dir = root / "001_demo"
            report_dir.mkdir()
            (report_dir / "merged_esg_results.json").write_text("[]", encoding="utf-8")
            output_csv = root / "batch.csv"
            output_json = root / "batch.json"

            def fake_run_workflow(report_dir, **kwargs):
                summary = {
                    "harness": None,
                    "citations": {
                        "field_count": 60,
                        "auto_cited_count": 45,
                        "needs_review_count": 15,
                    },
                    "rating": {
                        "score": 70.0,
                        "rating": "B",
                        "field_count": 53,
                        "scored_field_count": 39,
                        "needs_review_count": 15,
                        "rating_run_id": "rating_demo",
                        "pillar_scores": {
                            "E": {"score": 86.0, "rating": "A"},
                            "S": {"score": 69.0, "rating": "CCC"},
                            "G": {"score": 53.0, "rating": "C"},
                        },
                    },
                }
                (Path(report_dir) / "full_rating_workflow_summary.json").write_text(
                    json.dumps(summary),
                    encoding="utf-8",
                )
                return summary

            with patch("scripts.run_full_rating_workflow_batch.run_workflow", fake_run_workflow):
                payload = run_batch(
                    reports_root=root,
                    industry="manufacturing",
                    skip_harness=True,
                    output_csv=output_csv,
                    output_json=output_json,
                )

            self.assertEqual(payload["summary"]["total_reports"], 1)
            self.assertEqual(payload["summary"]["success_count"], 1)
            self.assertTrue(output_csv.exists())
            self.assertTrue(output_json.exists())
            self.assertIn("001_demo", output_csv.read_text(encoding="utf-8-sig"))


if __name__ == "__main__":
    unittest.main()
