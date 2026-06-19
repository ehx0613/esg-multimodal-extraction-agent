import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from pipeline.merge_pipeline import apply_semantic_judge_to_merged
from utils.result_guard import safe_write_json
from utils.semantic_metric_judge import build_semantic_judge_candidates, run_semantic_metric_judge


class SemanticMetricJudgeTests(unittest.TestCase):
    def test_build_candidates_from_route_a_tables(self):
        with TemporaryDirectory() as tmp:
            report_dir = Path(tmp)
            safe_write_json(
                report_dir / "all_table_rows.json",
                [
                    {
                        "page_image": "page_43.png",
                        "page_number": 43,
                        "tables": [
                            {
                                "table_title": "社会类关键绩效",
                                "rows": [
                                    {
                                        "topic": "研发创新 / 研发总投入",
                                        "metric_name": "万元",
                                        "unit": "万元",
                                        "values": {"2024": "10,430.30"},
                                        "evidence_text": "研发创新 研发总投入 万元 2024年 10,430.30",
                                    }
                                ],
                            }
                        ],
                    }
                ],
            )

            candidates = build_semantic_judge_candidates(report_dir)

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["value"], "10,430.30")
        self.assertEqual(candidates[0]["year"], "2024")
        self.assertEqual(candidates[0]["source_pages"], [43])

    def test_run_semantic_judge_accepts_valid_table_candidate(self):
        with TemporaryDirectory() as tmp:
            report_dir = Path(tmp)
            safe_write_json(
                report_dir / "all_table_rows.json",
                [
                    {
                        "page_image": "page_43.png",
                        "page_number": 43,
                        "tables": [
                            {
                                "table_title": "社会类关键绩效",
                                "rows": [
                                    {
                                        "topic": "研发创新 / 研发总投入",
                                        "metric_name": "万元",
                                        "unit": "万元",
                                        "values": {"2024": "10,430.30"},
                                        "evidence_text": "研发创新 研发总投入 万元 2024年 10,430.30",
                                    }
                                ],
                            }
                        ],
                    }
                ],
            )
            with patch(
                "utils.semantic_metric_judge.semantic_judge_candidate_to_schema",
                return_value={
                    "matched": True,
                    "field_key": "r_and_d_expense",
                    "confidence": 0.92,
                    "reason": "semantic_judge_match:研发总投入对应研发投入金额",
                    "judge_model": "test-model",
                },
            ):
                summary = run_semantic_metric_judge(report_dir)

        self.assertEqual(summary["candidate_count"], 1)
        self.assertEqual(summary["accepted_count"], 1)
        self.assertIn("r_and_d_expense", summary["accepted_fields"])

    def test_merge_applies_semantic_judge_to_missing_field(self):
        merged_by_key = {
            "r_and_d_expense": {
                "field_key": "r_and_d_expense",
                "status": "missing",
                "source_route": "missing",
                "value": "",
            }
        }
        apply_semantic_judge_to_merged(
            merged_by_key,
            [
                {
                    "field_key": "r_and_d_expense",
                    "field_name_cn": "研发投入金额",
                    "matched": "True",
                    "status": "extracted",
                    "value": "10430.30",
                    "raw_value": "10,430.30",
                    "unit": "万元",
                    "year": "2024",
                    "confidence": "0.92",
                    "evidence": "研发创新 研发总投入 万元 2024年 10,430.30",
                    "source_pages": "[43]",
                    "b2_validation_ok": "True",
                }
            ],
        )

        self.assertEqual(merged_by_key["r_and_d_expense"]["status"], "extracted")
        self.assertEqual(merged_by_key["r_and_d_expense"]["source_route"], "semantic_judge")
        self.assertEqual(merged_by_key["r_and_d_expense"]["source_pages"], "[43]")


if __name__ == "__main__":
    unittest.main()
