import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient


class BackendApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "agent_state.db"
        self.previous_db_path = os.environ.get("AGENT_DB_PATH")
        os.environ["AGENT_DB_PATH"] = str(self.db_path)

        from backend.app import app

        self.client = TestClient(app)

    def tearDown(self) -> None:
        if self.previous_db_path is None:
            os.environ.pop("AGENT_DB_PATH", None)
        else:
            os.environ["AGENT_DB_PATH"] = self.previous_db_path
        self.tmpdir.cleanup()

    def test_health_report_task_and_trace_flow(self) -> None:
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})

        report_response = self.client.post(
            "/reports",
            json={
                "file_name": "demo.pdf",
                "file_path": "data/raw/demo.pdf",
                "company_name": "Demo Corp",
                "report_year": 2024,
                "industry": "manufacturing",
                "metadata": {"source": "api_test"},
            },
        )
        self.assertEqual(report_response.status_code, 200)
        report = report_response.json()

        task_response = self.client.post(
            "/tasks",
            json={
                "report_id": report["id"],
                "industry": "manufacturing",
                "retrieval_profile": "hybrid_rrf_v1",
                "metadata": {"rerank_enabled": False},
            },
        )
        self.assertEqual(task_response.status_code, 200)
        task = task_response.json()
        self.assertEqual(task["status"], "pending")

        fetched_task = self.client.get(f"/tasks/{task['id']}").json()
        self.assertEqual(fetched_task["id"], task["id"])

        trace = self.client.get(f"/tasks/{task['id']}/trace").json()
        self.assertEqual(trace["task"]["id"], task["id"])
        self.assertEqual(trace["agent_runs"], [])

    def test_run_report_dir_endpoint(self) -> None:
        report_dir = Path(self.tmpdir.name) / "demo_report"
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

        class FakeRatingDataHarness:
            def __init__(self, report_dir, **kwargs):
                self.report_dir = Path(report_dir)

            def run(self):
                return {
                    "backend_task_id": "task_api_demo",
                    "backend_report_id": "report_api_demo",
                    "backend_task_status": "completed",
                    "report_name": self.report_dir.name,
                    "ok": True,
                    "review_needed": False,
                    "review_item_count": 0,
                }

        with patch("backend.app.ESGRatingDataHarness", FakeRatingDataHarness):
            response = self.client.post(
                "/runs/report-dir",
                json={
                    "report_dir": str(report_dir),
                    "industry": "manufacturing",
                    "retrieval_profile": "baseline_test",
                    "generate_citations": True,
                    "generate_rating": True,
                },
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["task_id"], "task_api_demo")
        self.assertEqual(payload["status"], "completed")
        self.assertEqual(payload["trace_url"], "/tasks/task_api_demo/trace")
        self.assertEqual(payload["artifacts"]["citations"]["field_count"], 1)
        self.assertEqual(payload["artifacts"]["rating"]["rating"], "AAA")

    def test_run_report_dir_endpoint_rejects_missing_dir(self) -> None:
        response = self.client.post(
            "/runs/report-dir",
            json={"report_dir": str(Path(self.tmpdir.name) / "missing")},
        )

        self.assertEqual(response.status_code, 404)

    def test_rating_review_api_applies_correction(self) -> None:
        report_dir = Path(self.tmpdir.name) / "rating_report"
        report_dir.mkdir()
        (report_dir / "field_citations.json").write_text(
            json.dumps(
                [
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
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        (report_dir / "route_b_chunks.json").write_text(
            json.dumps(
                [
                    {
                        "chunk_id": "p39_66",
                        "page_number": 39,
                        "text": "FULL_EVIDENCE_CHUNK_TEXT for air pollutant review.",
                    }
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        page_image_dir = report_dir / "page_images"
        page_image_dir.mkdir()
        (page_image_dir / "page_39.png").write_bytes(b"fake png bytes")
        recalc_response = self.client.post(
            "/rating/recalculate",
            json={"report_dir": str(report_dir), "industry": "manufacturing"},
        )
        self.assertEqual(recalc_response.status_code, 200)
        recalc_payload = recalc_response.json()
        self.assertIn("rating_run_id", recalc_payload)

        rating_runs_response = self.client.get(
            "/rating/runs",
            params={"report_dir": str(report_dir)},
        )
        self.assertEqual(rating_runs_response.status_code, 200)
        self.assertEqual(rating_runs_response.json()["count"], 1)

        rating_run_response = self.client.get(f"/rating/runs/{recalc_payload['rating_run_id']}")
        self.assertEqual(rating_run_response.status_code, 200)
        self.assertTrue(rating_run_response.json()["items"])

        queue_response = self.client.post(
            "/rating/review-queue",
            json={"report_dir": str(report_dir)},
        )
        self.assertEqual(queue_response.json()["count"], 1)

        apply_response = self.client.post(
            "/rating/review-items/apply",
            json={
                "report_dir": str(report_dir),
                "field_key": "climate_risk_management",
                "action": "correct",
                "industry": "manufacturing",
                "reviewer": "api-test",
                "correction": {
                    "value": True,
                    "evidence": "公司识别实体及转型气候风险。",
                    "confidence": "0.9",
                },
            },
        )

        self.assertEqual(apply_response.status_code, 200)
        payload = apply_response.json()
        self.assertEqual(payload["updated_field"]["citation_review_status"], "reviewed_approved")
        self.assertEqual(payload["rating"]["needs_review_count"], 0)
        self.assertIn("rating_run_id", payload["rating"])

    def test_report_summary_and_dashboard(self) -> None:
        report_dir = Path(self.tmpdir.name) / "dashboard_report"
        report_dir.mkdir()
        (report_dir / "field_citations.json").write_text(
            json.dumps(
                [
                    {
                        "field_key": "total_ghg_emissions",
                        "field_name_cn": "温室气体排放总量",
                        "status": "extracted",
                        "value": "2000",
                        "confidence": "0.95",
                        "citation_review_status": "auto_cited",
                        "citation_review_reasons": [],
                        "citation_page_number": 39,
                        "citation_chunk_id": "table_page_39",
                    },
                    {
                        "field_key": "climate_risk_management",
                        "field_name_cn": "气候风险识别与管理",
                        "status": "missing",
                        "value": "",
                        "citation_review_status": "needs_review",
                        "citation_review_reasons": ["missing_existing_evidence"],
                        "citation_page_number": 38,
                        "citation_chunk_id": "p38_1",
                    },
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        recalc_response = self.client.post(
            "/rating/recalculate",
            json={"report_dir": str(report_dir), "industry": "manufacturing"},
        )
        self.assertEqual(recalc_response.status_code, 200)

        summary_response = self.client.get(
            "/reports/summary",
            params={"report_dir": str(report_dir)},
        )
        self.assertEqual(summary_response.status_code, 200)
        summary = summary_response.json()
        self.assertEqual(summary["report_name"], "dashboard_report")
        self.assertEqual(summary["citation_summary"]["field_count"], 2)
        self.assertEqual(summary["review_queue"]["count"], 1)
        self.assertEqual(len(summary["rating_runs"]), 1)

        dashboard_response = self.client.get(
            "/dashboard",
            params={"report_dir": str(report_dir)},
        )
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertIn("ESG Rating Agent Dashboard", dashboard_response.text)
        self.assertIn("dashboard_report", dashboard_response.text)
        self.assertIn("/review?report_dir=", dashboard_response.text)
        self.assertIn("人工审核", dashboard_response.text)

    def test_review_page_rejects_pending_item(self) -> None:
        report_dir = Path(self.tmpdir.name) / "review_page_report"
        report_dir.mkdir()
        (report_dir / "field_citations.json").write_text(
            json.dumps(
                [
                    {
                        "field_key": "air_pollutant_emissions",
                        "field_name_cn": "废气或大气污染物排放量",
                        "status": "missing",
                        "value": "",
                        "citation_review_status": "needs_review",
                        "citation_review_reasons": ["missing_existing_evidence"],
                        "citation_page_number": 39,
                        "citation_chunk_id": "p39_66",
                        "citation_text_excerpt": "候选证据是废水和温室气体，不支持废气污染物字段。",
                    }
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        recalc_response = self.client.post(
            "/rating/recalculate",
            json={"report_dir": str(report_dir), "industry": "manufacturing"},
        )
        self.assertEqual(recalc_response.status_code, 200)

        review_response = self.client.get(
            "/review",
            params={"report_dir": str(report_dir), "industry": "manufacturing"},
        )
        self.assertEqual(review_response.status_code, 200)
        self.assertIn("ESG 字段审核", review_response.text)
        self.assertIn("air_pollutant_emissions", review_response.text)

        self.assertIn("/review/evidence", review_response.text)
        self.assertIn("/reports/page-image", review_response.text)
        self.assertIn("FULL_EVIDENCE_CHUNK_TEXT", review_response.text)

        evidence_response = self.client.get(
            "/review/evidence",
            params={
                "report_dir": str(report_dir),
                "industry": "manufacturing",
                "field_key": "air_pollutant_emissions",
            },
        )
        self.assertEqual(evidence_response.status_code, 200)
        self.assertIn("FULL_EVIDENCE_CHUNK_TEXT", evidence_response.text)

        image_response = self.client.get(
            "/reports/page-image",
            params={"report_dir": str(report_dir), "page_number": "39"},
        )
        self.assertEqual(image_response.status_code, 200)

        apply_response = self.client.get(
            "/review/apply-ui",
            params={
                "report_dir": str(report_dir),
                "industry": "manufacturing",
                "field_key": "air_pollutant_emissions",
                "action": "reject",
                "reviewer": "api-test",
                "notes": "wrong evidence",
            },
        )
        self.assertEqual(apply_response.status_code, 200)
        queue_response = self.client.post(
            "/rating/review-queue",
            json={"report_dir": str(report_dir)},
        )
        self.assertEqual(queue_response.json()["count"], 0)

    def test_review_page_corrects_pending_item(self) -> None:
        report_dir = Path(self.tmpdir.name) / "review_correct_report"
        report_dir.mkdir()
        (report_dir / "field_citations.json").write_text(
            json.dumps(
                [
                    {
                        "field_key": "wastewater_discharge",
                        "field_name_cn": "废水排放量",
                        "status": "missing",
                        "value": "",
                        "citation_review_status": "needs_review",
                        "citation_review_reasons": ["missing_existing_evidence"],
                        "citation_page_number": 39,
                        "citation_chunk_id": "p39_66",
                        "citation_text_excerpt": "报告期内废水排放量为25.12万吨。",
                    }
                ],
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        self.client.post(
            "/rating/recalculate",
            json={"report_dir": str(report_dir), "industry": "manufacturing"},
        )

        apply_response = self.client.get(
            "/review/apply-ui",
            params={
                "report_dir": str(report_dir),
                "industry": "manufacturing",
                "field_key": "wastewater_discharge",
                "action": "correct",
                "reviewer": "api-test",
                "value": "25.12",
                "unit": "万吨",
                "year": 2024,
                "evidence": "报告期内废水排放量为25.12万吨。",
            },
        )
        self.assertEqual(apply_response.status_code, 200)
        citations = json.loads((report_dir / "field_citations.json").read_text(encoding="utf-8"))
        self.assertEqual(citations[0]["value"], "25.12")
        self.assertEqual(citations[0]["unit"], "万吨")
        self.assertEqual(citations[0]["citation_review_status"], "reviewed_approved")


if __name__ == "__main__":
    unittest.main()
