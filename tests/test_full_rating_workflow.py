import json
import os
import tempfile
import unittest
from pathlib import Path

from scripts.run_full_rating_workflow import run_workflow


class FullRatingWorkflowTests(unittest.TestCase):
    def test_run_workflow_can_skip_harness_and_generate_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            previous_db_path = os.environ.get("AGENT_DB_PATH")
            os.environ["AGENT_DB_PATH"] = str(Path(tmp) / "agent_state.db")
            report_dir = Path(tmp) / "demo_report"
            report_dir.mkdir()
            (report_dir / "merged_esg_results.json").write_text(
                json.dumps(
                    [
                        {
                            "field_key": "total_ghg_emissions",
                            "field_name_cn": "温室气体排放总量",
                            "category": "E",
                            "status": "extracted",
                            "value": "2000",
                            "confidence": "0.95",
                            "source_route": "route_a_appendix_table",
                            "evidence": "温室气体排放总量 2000 吨二氧化碳当量",
                            "source_pages": "page_39.png",
                            "page_image": "page_39.png",
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (report_dir / "route_b_chunks.json").write_text(
                json.dumps(
                    [
                        {
                            "chunk_id": "p39_1",
                            "page_number": 39,
                            "text": "温室气体排放总量为2000吨二氧化碳当量。",
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            summary = run_workflow(
                report_dir,
                industry="manufacturing",
                skip_harness=True,
            )

            self.assertTrue((report_dir / "field_citations.json").exists())
            self.assertTrue((report_dir / "simulated_rating.json").exists())
            self.assertTrue((report_dir / "full_rating_workflow_summary.json").exists())
            self.assertIsNone(summary["harness"])
            self.assertEqual(summary["citations"]["field_count"], 1)
            self.assertEqual(summary["rating"]["rating"], "AAA")
            self.assertIn("rating_run_id", summary["rating"])
            if previous_db_path is None:
                os.environ.pop("AGENT_DB_PATH", None)
            else:
                os.environ["AGENT_DB_PATH"] = previous_db_path


if __name__ == "__main__":
    unittest.main()
