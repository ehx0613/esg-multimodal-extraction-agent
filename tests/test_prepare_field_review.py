import csv
import tempfile
import unittest
from pathlib import Path

from scripts.prepare_field_review import build_review_rows, resolve_report_dir, write_csv


class PrepareFieldReviewTests(unittest.TestCase):
    def test_build_review_rows_from_merged_csv(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            report_dir = Path(temp_dir) / "600587_新华医疗_2024"
            report_dir.mkdir()
            merged_path = report_dir / "merged_esg_results.csv"
            with merged_path.open("w", encoding="utf-8-sig", newline="") as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=[
                        "field_key",
                        "field_name_cn",
                        "category",
                        "applicability",
                        "indicator_type",
                        "status",
                        "value",
                        "unit",
                        "year",
                        "source_route",
                        "confidence",
                        "evidence",
                        "source_pages",
                        "merge_reason",
                        "missing_reason",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "field_key": "total_ghg_emissions",
                        "field_name_cn": "温室气体排放总量",
                        "category": "E",
                        "applicability": "core",
                        "indicator_type": "quantitative",
                        "status": "extracted",
                        "value": "100",
                        "unit": "吨CO2e",
                        "year": "2024",
                        "source_route": "route_a_appendix_table",
                        "confidence": "0.94",
                        "evidence": "温室气体排放总量 100",
                        "source_pages": "[68]",
                        "merge_reason": "route_a_selected",
                        "missing_reason": "",
                    }
                )

            rows = build_review_rows(report_dir)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["predicted_value"], "100")
            self.assertEqual(rows[0]["evidence_page"], "68")
            self.assertEqual(rows[0]["review_result"], "")

            output = report_dir / "review.csv"
            write_csv(output, rows)
            self.assertTrue(output.exists())

    def test_resolve_report_dir_supports_partial_name(self):
        resolved = resolve_report_dir("600587_新华医疗_2024")
        self.assertIn("600587_新华医疗_2024", resolved.name)


if __name__ == "__main__":
    unittest.main()
