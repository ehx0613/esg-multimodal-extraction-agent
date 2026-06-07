import tempfile
import unittest
from pathlib import Path

from backend.database import (
    create_rating_record,
    create_retrieval_eval_record,
    create_report,
    create_task,
    get_rating_run,
    finish_agent_run,
    get_task_trace,
    init_db,
    list_rating_runs,
    list_retrieval_eval_records,
    list_tasks,
    start_agent_run,
    update_task_status,
    upsert_prompt_version,
)
from config.schema.huazheng_public_mapping import SCHEMA_VERSION


class BackendDatabaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmpdir.name) / "agent_state.db"
        init_db(self.db_path)

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_create_report_and_task(self) -> None:
        report = create_report(
            file_name="demo.pdf",
            file_path="data/raw/demo.pdf",
            company_name="Demo Corp",
            report_year=2024,
            industry="manufacturing",
            metadata={"source": "unit_test"},
            db_path=self.db_path,
        )
        task = create_task(
            report_id=report["id"],
            industry="manufacturing",
            schema_version=SCHEMA_VERSION,
            retrieval_profile="hybrid_rrf_v1",
            metadata={"rerank_enabled": False},
            db_path=self.db_path,
        )

        self.assertEqual(task["status"], "pending")
        self.assertEqual(task["industry"], "manufacturing")
        self.assertEqual(task["schema_version"], SCHEMA_VERSION)
        self.assertEqual(task["metadata_json"]["rerank_enabled"], False)
        self.assertEqual(len(list_tasks(db_path=self.db_path)), 1)

    def test_task_status_and_trace(self) -> None:
        report = create_report(
            file_name="demo.pdf",
            file_path="data/raw/demo.pdf",
            db_path=self.db_path,
        )
        task = create_task(
            report_id=report["id"],
            industry=None,
            schema_version=SCHEMA_VERSION,
            retrieval_profile="baseline",
            db_path=self.db_path,
        )

        run = start_agent_run(
            task_id=task["id"],
            agent_name="SupervisorAgent",
            input_data={"goal": "inspect"},
            db_path=self.db_path,
        )
        finish_agent_run(
            agent_run_id=run["id"],
            status="completed",
            output_data={"next_actions": ["route_a"]},
            db_path=self.db_path,
        )
        updated = update_task_status(task["id"], "running", db_path=self.db_path)
        trace = get_task_trace(task["id"], db_path=self.db_path)

        self.assertEqual(updated["status"], "running")
        self.assertEqual(trace["task"]["id"], task["id"])
        self.assertEqual(trace["agent_runs"][0]["agent_name"], "SupervisorAgent")
        self.assertEqual(trace["agent_runs"][0]["output_json"]["next_actions"], ["route_a"])

    def test_prompt_version_upsert_is_stable(self) -> None:
        first = upsert_prompt_version(
            agent_name="RouteBAgent",
            prompt_name="extract_field",
            version="v1",
            content_hash="hash-a",
            template_content="Extract {field_key}",
            db_path=self.db_path,
        )
        second = upsert_prompt_version(
            agent_name="RouteBAgent",
            prompt_name="extract_field",
            version="v1",
            content_hash="hash-b",
            template_content="Extract {field_key} with evidence",
            db_path=self.db_path,
        )

        self.assertEqual(first["id"], second["id"])
        self.assertEqual(second["content_hash"], "hash-b")

    def test_retrieval_eval_record_round_trip(self) -> None:
        record = create_retrieval_eval_record(
            eval_set_name="unit_eval.csv",
            retrieval_profile="bm25_query_agg_evidence_rerank_v1",
            hit_rate_at_5=1.0,
            mrr_at_5=0.9,
            avg_latency_ms=123.4,
            metadata={"top_k": 5, "bad_cases": []},
            db_path=self.db_path,
        )
        records = list_retrieval_eval_records(db_path=self.db_path)

        self.assertEqual(record["eval_set_name"], "unit_eval.csv")
        self.assertEqual(records[0]["id"], record["id"])
        self.assertEqual(records[0]["metadata_json"]["top_k"], 5)

    def test_rating_record_persists_score_items(self) -> None:
        rating_result = {
            "rating_model": "project_simulated_huazheng_public_v1",
            "rating_boundary": "unit-test",
            "industry": "manufacturing",
            "overall": {
                "score": 88.5,
                "rating": "A",
                "field_count": 2,
                "scored_field_count": 2,
                "needs_review_count": 0,
            },
            "pillar_scores": {
                "E": {
                    "score": 90.0,
                    "rating": "AA",
                    "field_count": 1,
                    "scored_field_count": 1,
                    "coverage": 1.0,
                    "evidence_coverage": 1.0,
                    "needs_review_count": 0,
                }
            },
            "theme_scores": [
                {
                    "theme_key": "climate_change",
                    "theme_name_cn": "气候变化",
                    "pillar": "E",
                    "score": 90.0,
                    "rating": "AA",
                    "field_count": 1,
                    "scored_field_count": 1,
                    "coverage": 1.0,
                    "evidence_coverage": 1.0,
                    "needs_review_count": 0,
                }
            ],
            "field_scores": [
                {
                    "field_key": "total_ghg_emissions",
                    "field_name_cn": "温室气体排放总量",
                    "pillar": "E",
                    "score": 95.0,
                    "weight": 1.5,
                    "is_success": True,
                    "citation_review_status": "auto_cited",
                }
            ],
        }

        record = create_rating_record(
            rating_result=rating_result,
            report_dir="output/reports/demo",
            metadata={"source": "unit_test"},
            db_path=self.db_path,
        )
        runs = list_rating_runs(report_dir="output/reports/demo", db_path=self.db_path)
        fetched = get_rating_run(record["id"], db_path=self.db_path)

        self.assertEqual(record["overall_score"], 88.5)
        self.assertEqual(runs[0]["id"], record["id"])
        self.assertEqual(fetched["metadata_json"]["source"], "unit_test")
        self.assertEqual({item["level"] for item in fetched["items"]}, {"overall", "pillar", "theme", "field"})


if __name__ == "__main__":
    unittest.main()
