import tempfile
import unittest
from pathlib import Path

import fitz

from utils.pdf_geometry import bbox_to_pdf_rect, render_pdf_bbox
from utils.table_quality import apply_cross_source_consistency, assess_table_chunk
from utils.visual_arbitration import build_table_arbitration_queue


class TableArbitrationTests(unittest.TestCase):
    def test_consistent_table_scores_high(self):
        assessment = assess_table_chunk(
            {
                "chunk_id": "table_1",
                "source_region_id": "p1_table_0",
                "page_number": 1,
                "bbox": [10, 10, 900, 500],
                "raw_content": (
                    "<table><tr><th>Metric</th><th>2024</th></tr>"
                    "<tr><td>Water</td><td>100</td></tr></table>"
                ),
                "text": "Metric 2024 Water 100",
            },
            visual_threshold=0.9,
        )

        self.assertFalse(assessment["needs_visual"])
        self.assertGreaterEqual(assessment["quality_score"], 0.9)

    def test_inconsistent_table_is_queued_for_visual_review(self):
        assessment = assess_table_chunk(
            {
                "chunk_id": "table_2",
                "source_region_id": "p2_table_0",
                "page_number": 2,
                "bbox": [10, 10, 900, 500],
                "raw_content": (
                    "<table><tr><td>Metric</td><td>Value</td><td>Unit</td></tr>"
                    "<tr><td>Water</td><td>2024</td><td>2023</td></tr>"
                    "<tr><td></td><td>100</td><td></td><td>extra</td></tr></table>"
                ),
                "text": "Metric Value Unit Water 2024 2023 100",
            },
            visual_threshold=0.9,
        )
        queue = build_table_arbitration_queue([assessment])

        self.assertTrue(assessment["needs_visual"])
        self.assertEqual(queue[0]["source_region_id"], "p2_table_0")

    def test_cross_source_conflict_forces_visual_review(self):
        mineru = {
            "chunk_id": "mineru_1",
            "source_region_id": "p1_table_0",
            "page_number": 1,
            "chunk_type": "mineru_structured_table",
            "bbox": [10, 10, 900, 500],
            "raw_content": "<table><tr><td>Water</td><td>100</td></tr></table>",
            "text": "Water 100",
        }
        route_a = {
            "chunk_id": "route_a_1",
            "page_number": 1,
            "chunk_type": "route_a_structured_row",
            "metric_name": "Water",
            "values": {"2024": "999"},
        }
        assessments = apply_cross_source_consistency(
            [assess_table_chunk(mineru)],
            [mineru, route_a],
        )

        self.assertTrue(assessments[0]["needs_visual"])
        self.assertIn("cross_source_conflict", assessments[0]["reasons"])

    def test_normalized_bbox_can_be_rendered(self):
        page_rect = fitz.Rect(0, 0, 600, 800)
        rect = bbox_to_pdf_rect([100, 100, 900, 500], page_rect, expand_points=0)
        self.assertEqual(tuple(round(value) for value in rect), (60, 80, 540, 400))

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf_path = root / "sample.pdf"
            document = fitz.open()
            page = document.new_page(width=600, height=800)
            page.insert_text((100, 150), "table region")
            document.save(pdf_path)
            document.close()

            output_path = root / "region.png"
            render_pdf_bbox(
                pdf_path,
                page_number=1,
                bbox=[100, 100, 900, 500],
                output_path=output_path,
                expand_points=0,
            )
            self.assertTrue(output_path.exists())
            self.assertGreater(output_path.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
