import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import openai  # noqa: F401
except ModuleNotFoundError:
    openai_stub = types.ModuleType("openai")

    class _OpenAIStub:
        def __init__(self, *args, **kwargs):
            pass

    openai_stub.OpenAI = _OpenAIStub
    sys.modules["openai"] = openai_stub

try:
    import faiss  # noqa: F401
except ModuleNotFoundError:
    sys.modules["faiss"] = types.ModuleType("faiss")

from config.schema import ESG_FIELD_KEYS
from agents.vlm_table_ocr_agent import VLMTableOCRAgent, VLM_TABLE_OCR_VERSION
from pipeline.merge_pipeline import ESGMergePipeline
from pipeline.unified_pipeline import UnifiedESGPipeline
from utils.evidence_store import build_evidence_records
from utils.metric_planner import build_metric_plan
from utils.visual_followup import build_visual_followup_queue


class UnifiedPipelineArchitectureTests(unittest.TestCase):
    def test_quantitative_metric_plan_requires_visual_fallback(self):
        plan = build_metric_plan(
            {
                "field_key": "scope_1",
                "name_cn": "Scope 1",
                "category": "E",
                "indicator_type": "quantitative",
                "value_type": "number",
                "aliases": ["Scope 1 emissions"],
                "unit_examples": ["tCO2e"],
                "year_required": True,
            }
        )

        self.assertTrue(plan["visual_fallback_required"])
        self.assertEqual(plan["required_modalities"], ["text", "visual"])
        self.assertIn("visual_proxy", plan["preferred_evidence"])

    def test_evidence_store_groups_table_derivations_by_source_region(self):
        records = build_evidence_records(
            text_chunks=[],
            structured_chunks=[
                {
                    "chunk_id": "row_1",
                    "source_region_id": "page_8_table_1",
                    "page_number": 8,
                    "text": "Scope 1 100 tCO2e",
                },
                {
                    "chunk_id": "row_2",
                    "source_region_id": "page_8_table_1",
                    "page_number": 8,
                    "text": "Scope 2 200 tCO2e",
                },
            ],
            page_features=[],
        )

        self.assertEqual(len(records), 2)
        self.assertEqual({row["source_region_id"] for row in records}, {"page_8_table_1"})

    def test_visual_followup_queue_targets_relevant_proxy(self):
        queue = build_visual_followup_queue(
            metric_plans=[
                {
                    "field_key": "scope_1",
                    "field_name_cn": "Scope 1 emissions",
                    "expected_terms": ["direct emissions"],
                    "expected_units": ["tCO2e"],
                    "visual_fallback_required": True,
                }
            ],
            evidence_records=[
                {
                    "evidence_id": "visual_proxy:page_8",
                    "source_region_id": "page_8_visual_page",
                    "evidence_type": "visual_proxy",
                    "page_number": 8,
                    "proxy_text": "Scope 1 emissions tCO2e",
                    "metadata": {"score": 80},
                }
            ],
            quantitative_results=[{"field_key": "scope_1", "matched": False, "reason": "missing"}],
        )

        self.assertEqual(queue[0]["field_key"], "scope_1")
        self.assertEqual(queue[0]["candidate_visual_regions"][0]["page_number"], 8)

    def test_visual_followup_queue_excludes_processed_page(self):
        queue = build_visual_followup_queue(
            metric_plans=[
                {
                    "field_key": "scope_1",
                    "field_name_cn": "Scope 1 emissions",
                    "expected_terms": ["direct emissions"],
                    "expected_units": ["tCO2e"],
                    "visual_fallback_required": True,
                }
            ],
            evidence_records=[
                {
                    "evidence_id": "visual_proxy:page_8",
                    "source_region_id": "page_8_visual_page",
                    "evidence_type": "visual_proxy",
                    "page_number": 8,
                    "proxy_text": "Scope 1 emissions tCO2e",
                    "metadata": {"score": 80},
                }
            ],
            quantitative_results=[{"field_key": "scope_1", "matched": False, "reason": "missing"}],
            excluded_page_numbers={8},
        )

        self.assertEqual(queue, [])

    def test_vlm_cache_hit_preserves_unrequested_pages(self):
        cached = [
            {
                "page_image": "page_8.png",
                "page_type": "performance_data_table",
                "extractor_version": VLM_TABLE_OCR_VERSION,
                "tables": [{"rows": [{"metric_name": "Scope 1"}]}],
            },
            {
                "page_image": "page_9.png",
                "page_type": "performance_data_table",
                "extractor_version": VLM_TABLE_OCR_VERSION,
                "tables": [{"rows": [{"metric_name": "Scope 2"}]}],
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            cache_path = output_dir / "all_table_rows.json"
            cache_path.write_text(json.dumps(cached), encoding="utf-8")
            state = {
                "output_dir": output_dir,
                "page_images": [output_dir / "page_images" / "page_8.png"],
            }
            result = VLMTableOCRAgent().run(state)
            persisted = json.loads(cache_path.read_text(encoding="utf-8"))

        self.assertEqual(len(result["all_table_rows"]), 2)
        self.assertEqual(len(persisted), 2)

    def test_vlm_budget_exhausted_page_is_not_a_valid_cache_hit(self):
        cached = [
            {
                "page_image": "page_8.png",
                "page_type": "other",
                "page_note": "model_call_budget_exhausted",
                "extractor_version": VLM_TABLE_OCR_VERSION,
                "tables": [],
            },
            {
                "page_image": "page_9.png",
                "page_type": "performance_data_table",
                "extractor_version": VLM_TABLE_OCR_VERSION,
                "tables": [{"rows": [{"metric_name": "Scope 2"}]}],
            },
        ]
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            cache_path = output_dir / "all_table_rows.json"
            cache_path.write_text(json.dumps(cached), encoding="utf-8")
            state = {
                "output_dir": output_dir,
                "pdf_path": output_dir / "report.pdf",
                "page_images": [output_dir / "page_images" / "page_8.png"],
            }
            with patch(
                "agents.vlm_table_ocr_agent.extract_all_table_rows_from_image",
                return_value={
                    "page_image": "page_8.png",
                    "page_type": "performance_data_table",
                    "tables": [{"rows": [{"metric_name": "Scope 1"}]}],
                },
            ) as extract:
                VLMTableOCRAgent().run(state)

        extract.assert_called_once()

    def test_merge_accepts_missing_route_a_as_empty_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            report_dir = Path(tmp)
            summary = ESGMergePipeline(report_dir).run()
            merged = json.loads((report_dir / "merged_esg_results.json").read_text(encoding="utf-8"))

        self.assertFalse(summary["route_a_available"])
        self.assertEqual(summary["route_a_status"], "not_available_empty_baseline")
        self.assertEqual(len(merged), len(ESG_FIELD_KEYS))
        self.assertTrue(all(row["status"] == "missing" for row in merged))

    def test_unified_pipeline_skips_active_visual_when_no_summary_candidate(self):
        ingest = {
            "pages": [{"page_number": 1, "text": "policy text"}],
            "chunks": [],
            "page_features": [
                {
                    "page_number": 1,
                    "score": 0,
                    "force_keep": False,
                    "chart_force_keep": False,
                    "table_like_lines": 0,
                }
            ],
            "manifest": {"text_available": True},
            "cache_used": False,
            "paths": {},
        }
        text_summary = {"quantitative_fallback": {}}
        merge_summary = {"total_fields": len(ESG_FIELD_KEYS)}

        with tempfile.TemporaryDirectory() as tmp:
            pipeline = UnifiedESGPipeline(Path(tmp))
            with (
                patch("pipeline.unified_pipeline.ingest_pdf", return_value=ingest),
                patch.object(pipeline, "_run_visual_extraction") as route_a_run,
                patch.object(pipeline, "_run_text_extraction", return_value=text_summary),
                patch.object(pipeline, "_run_merge", return_value=merge_summary),
                patch.object(pipeline, "_pdf_fingerprint", return_value="test-fingerprint"),
                patch(
                    "pipeline.unified_pipeline.build_structured_chunks_from_all_table_rows",
                    return_value=[],
                ),
                patch("pipeline.unified_pipeline.detect_industry", return_value="general"),
            ):
                summary = pipeline.run(Path(tmp) / "report.pdf")

        route_a_run.assert_not_called()
        self.assertEqual(summary["visual_extraction"]["status"], "completed_no_summary_table")
        self.assertEqual(summary["schema"]["core_fields"], len(ESG_FIELD_KEYS))

    def test_unified_pipeline_executes_budgeted_visual_followup_without_rerunning_text(self):
        ingest = {
            "pages": [{"page_number": 1, "text": "Scope 1"}],
            "chunks": [],
            "page_features": [],
            "manifest": {"text_available": True},
            "cache_used": False,
            "paths": {},
        }
        queue = [
            {
                "field_key": "scope_1",
                "candidate_visual_regions": [
                    {"page_number": 8},
                    {"page_number": 9},
                ],
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = UnifiedESGPipeline(Path(tmp), run_mode="balanced")
            with (
                patch("pipeline.unified_pipeline.ingest_pdf", return_value=ingest),
                patch.object(pipeline, "_pdf_fingerprint", return_value="test-fingerprint"),
                patch.object(pipeline, "_run_text_extraction", return_value={"quantitative_fallback": {}}) as text_run,
                patch.object(pipeline, "_run_targeted_visual_pages", return_value={"status": "completed"}) as visual_run,
                patch.object(
                    pipeline,
                    "_build_evidence_and_followup",
                    side_effect=[({"evidence_count": 1}, queue), ({"evidence_count": 2}, [])],
                ),
                patch.object(pipeline, "_run_merge", return_value={"total_fields": len(ESG_FIELD_KEYS)}),
                patch("pipeline.unified_pipeline.UNIFIED_ENABLE_VISUAL_FOLLOWUP", True),
                patch("pipeline.unified_pipeline.UNIFIED_VISUAL_FOLLOWUP_MAX_PAGES", 1),
            ):
                summary = pipeline.run(Path(tmp) / "report.pdf")

        visual_run.assert_called_once()
        self.assertEqual(visual_run.call_args.args[1], [8])
        self.assertEqual(text_run.call_count, 1)
        self.assertEqual(summary["visual_followup"]["execution"]["status"], "completed")
        self.assertTrue(summary["visual_followup"]["execution"]["full_text_rerun_skipped"])

    def test_targeted_visual_results_fill_missing_without_overwriting_mineru_baseline(self):
        existing = {
            "scope_1_emissions": {
                "field_key": "scope_1_emissions",
                "status": "extracted",
                "value": 100,
                "source_type": "mineru_table",
            },
            "water_consumption": {
                "field_key": "water_consumption",
                "status": "missing",
                "value": None,
            },
        }
        targeted = {
            "scope_1_emissions": {
                "field_key": "scope_1_emissions",
                "status": "extracted",
                "value": 999,
                "source_type": "appendix_table",
            },
            "water_consumption": {
                "field_key": "water_consumption",
                "status": "extracted",
                "value": 25,
                "source_type": "appendix_table",
            },
        }

        combined, added = UnifiedESGPipeline._merge_targeted_visual_results(existing, targeted)

        self.assertEqual(combined["scope_1_emissions"]["value"], 100)
        self.assertEqual(combined["water_consumption"]["value"], 25)
        self.assertEqual(added, ["water_consumption"])

    def test_targeted_visual_rows_preserve_mineru_and_visual_evidence(self):
        mineru_row = {"source_type": "mineru_table", "page_number": 65}
        visual_row = {"page_image": "page_35.png", "page_type": "performance_data_table"}

        combined = UnifiedESGPipeline._merge_targeted_visual_rows(
            [mineru_row],
            [mineru_row, visual_row],
        )

        self.assertEqual(combined, [mineru_row, visual_row])

    def test_fast_mode_does_not_run_table_arbitration_vlm(self):
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = UnifiedESGPipeline(Path(tmp), run_mode="fast")
            with patch("pipeline.unified_pipeline.UNIFIED_ENABLE_TABLE_ARBITRATION_VLM", True):
                result = pipeline._run_table_arbitration_vlm()

        self.assertEqual(result["status"], "disabled")
        self.assertEqual(result["applied_updates"], 0)

    def test_mineru_route_a_skips_full_page_visual_route_a(self):
        ingest = {
            "pages": [{"page_number": 1, "text": "关键绩效表"}],
            "blocks": [],
            "chunks": [],
            "page_features": [],
            "manifest": {"text_available": True, "parser_name": "mineru"},
            "cache_used": False,
            "paths": {},
        }
        mineru_route_a = {
            "available": True,
            "selected_tables": 2,
            "row_count": 10,
            "extracted_fields": ["water_consumption"],
        }
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = UnifiedESGPipeline(Path(tmp), run_mode="fast")
            with (
                patch("pipeline.unified_pipeline.ingest_pdf", return_value=ingest),
                patch.object(pipeline, "_pdf_fingerprint", return_value="fingerprint"),
                patch.object(pipeline, "_run_mineru_route_a", return_value=mineru_route_a),
                patch.object(pipeline, "_run_visual_extraction") as visual_run,
                patch.object(pipeline, "_prepare_table_arbitration", return_value={}),
                patch.object(pipeline, "_run_text_extraction", return_value={}),
                patch.object(pipeline, "_build_evidence_and_followup", return_value=({}, [])),
                patch.object(pipeline, "_run_merge", return_value={}),
            ):
                summary = pipeline.run(Path(tmp) / "report.pdf")

        visual_run.assert_not_called()
        self.assertEqual(summary["visual_extraction"]["status"], "completed_mineru_route_a")
        self.assertTrue(summary["visual_extraction"]["visual_scan_skipped"])


if __name__ == "__main__":
    unittest.main()
