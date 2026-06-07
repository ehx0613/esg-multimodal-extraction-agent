import json
import tempfile
import unittest
from pathlib import Path

from utils.rating_review import apply_review_decision, load_review_queue, recalculate_rating


class RatingReviewTests(unittest.TestCase):
    def _write_report(self, report_dir: Path) -> None:
        rows = [
            {
                "field_key": "climate_risk_management",
                "field_name_cn": "气候风险识别与管理",
                "status": "missing",
                "value": "",
                "confidence": "",
                "citation_review_status": "needs_review",
                "citation_review_reasons": ["missing_existing_evidence"],
                "citation_page_number": 38,
                "citation_chunk_id": "p38_1",
                "citation_text_excerpt": "公司识别实体及转型气候风险。",
            }
        ]
        (report_dir / "field_citations.json").write_text(
            json.dumps(rows, ensure_ascii=False),
            encoding="utf-8",
        )
        recalculate_rating(report_dir, industry="manufacturing")

    def test_correct_review_updates_field_and_recalculates_rating(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp)
            self._write_report(report_dir)

            before_queue = load_review_queue(report_dir)
            result = apply_review_decision(
                report_dir,
                field_key="climate_risk_management",
                action="correct",
                industry="manufacturing",
                reviewer="tester",
                correction={
                    "value": True,
                    "evidence": "公司识别实体及转型气候风险。",
                    "confidence": "0.9",
                },
            )
            after_queue = load_review_queue(report_dir)
            updated = json.loads((report_dir / "field_citations.json").read_text(encoding="utf-8"))[0]

            self.assertEqual(len(before_queue), 1)
            self.assertEqual(len(after_queue), 0)
            self.assertEqual(updated["status"], "extracted")
            self.assertEqual(updated["citation_review_status"], "reviewed_approved")
            self.assertEqual(result["rating"]["needs_review_count"], 0)
            self.assertTrue((report_dir / "rating_review_history.json").exists())

    def test_reject_review_removes_item_from_pending_queue(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp)
            self._write_report(report_dir)

            result = apply_review_decision(
                report_dir,
                field_key="climate_risk_management",
                action="reject",
                industry="manufacturing",
            )
            updated = json.loads((report_dir / "field_citations.json").read_text(encoding="utf-8"))[0]

            self.assertEqual(updated["citation_review_status"], "reviewed_rejected")
            self.assertEqual(load_review_queue(report_dir), [])
            self.assertEqual(result["rating"]["needs_review_count"], 0)


if __name__ == "__main__":
    unittest.main()
