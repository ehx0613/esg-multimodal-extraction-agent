import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook

from scripts.build_quantitative_golden_set import (
    EXPECTED_HEADERS,
    build_golden_set,
    read_workbook_rows,
)


class BuildQuantitativeGoldenSetTests(unittest.TestCase):
    def write_workbook(self, path: Path, report_id="600587_test_2024"):
        workbook = Workbook()
        sheet = workbook.active
        sheet.append(EXPECTED_HEADERS)
        sheet.append(
            [
                report_id,
                "total_ghg_emissions",
                "温室气体排放总量",
                "E",
                "温室气体排放总量",
                "disclosed",
                "100",
                "吨二氧化碳当量",
                "2024",
                "10",
                "关键绩效表",
                "集团口径",
                "",
            ]
        )
        workbook.save(path)

    def test_read_workbook_rows_normalizes_headers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "report.xlsx"
            self.write_workbook(path)

            rows = read_workbook_rows(path)

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["field_key"], "total_ghg_emissions")
            self.assertEqual(rows[0]["raw_value"], "100")
            self.assertEqual(rows[0]["pdf_page"], "10")
            self.assertEqual(rows[0]["status_source"], "manual")

    def test_build_golden_set_skips_template_and_writes_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            self.write_workbook(base / "600587_test.xlsx")
            self.write_workbook(base / "quantitative_golden_set_template.xlsx")

            quality = build_golden_set(base, base / "out")

            self.assertEqual(quality["input_file_count"], 1)
            self.assertEqual(quality["record_count"], 1)
            self.assertTrue((base / "out" / "quantitative_golden_set.csv").exists())
            self.assertTrue((base / "out" / "quantitative_golden_set_quality.md").exists())

    def test_not_checked_status_is_inferred_from_filled_cells(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "report.xlsx"
            workbook = Workbook()
            sheet = workbook.active
            sheet.append(EXPECTED_HEADERS)
            sheet.append(
                [
                    "600587_test_2024",
                    "total_ghg_emissions",
                    "温室气体排放总量",
                    "E",
                    "温室气体排放总量",
                    "not_checked",
                    "100",
                    "吨二氧化碳当量",
                    "2024",
                    "10",
                    "关键绩效表",
                    "",
                    "",
                ]
            )
            workbook.save(path)

            rows = read_workbook_rows(path)

            self.assertEqual(rows[0]["disclosure_status"], "disclosed")
            self.assertEqual(rows[0]["status_source"], "inferred_from_filled_cells")


if __name__ == "__main__":
    unittest.main()
