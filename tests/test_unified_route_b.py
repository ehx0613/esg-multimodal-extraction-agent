import tempfile
import unittest
import sys
import types
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

from pipeline.text_pipeline import ESGTextPipeline


class UnifiedRouteBTests(unittest.TestCase):
    def test_budget_blocked_qualitative_attempt_is_not_counted_as_llm_call(self) -> None:
        ingest = {
            "pages": [{"page_number": 1, "text": "relevant evidence"}],
            "chunks": [{"chunk_id": "p1", "page_number": 1, "text": "relevant evidence"}],
            "manifest": {"text_available": True},
            "cache_used": False,
            "paths": {},
        }
        item = {
            "field_key": "test_field",
            "name_cn": "Test",
            "category": "S",
            "aliases": [],
        }
        with tempfile.TemporaryDirectory() as tmp:
            pipeline = ESGTextPipeline(Path(tmp))
            with (
                patch("pipeline.text_pipeline.ingest_pdf", return_value=ingest),
                patch("pipeline.text_pipeline.build_structured_chunks_from_all_table_rows", return_value=[]),
                patch("pipeline.text_pipeline.FaissChunkVectorStore.build_or_load"),
                patch.object(pipeline, "_target_fields", return_value=[item]),
                patch("pipeline.text_pipeline.retrieve_hybrid_chunks", return_value=ingest["chunks"]),
                patch(
                    "pipeline.text_pipeline.extract_text_indicator_with_llm",
                    return_value={"matched": False, "reason": "model_call_budget_exhausted"},
                ),
                patch("pipeline.text_pipeline.ROUTE_B_ENABLE_QUANT_FALLBACK", False),
                patch(
                    "pipeline.text_pipeline.ESGQuantTextPipeline.write_disabled_outputs",
                    return_value={"enabled": False, "llm_calls": 0},
                ),
            ):
                summary = pipeline.run(Path(tmp) / "report.pdf")

        self.assertEqual(summary["llm_calls"], 0)
        self.assertEqual(summary["qualitative"]["skipped_by_model_budget"], 1)

    def test_unified_route_b_can_disable_quantitative_fusion(self) -> None:
        ingest = {
            "pages": [],
            "chunks": [],
            "manifest": {"text_available": False},
            "cache_used": False,
            "paths": {},
        }
        disabled_summary = {
            "enabled": False,
            "target_fields": 0,
            "attempted_fields": 0,
            "matched_fields": 0,
            "llm_calls": 0,
        }

        with tempfile.TemporaryDirectory() as tmp:
            pipeline = ESGTextPipeline(Path(tmp))
            with (
                patch("pipeline.text_pipeline.ingest_pdf", return_value=ingest),
                patch(
                    "pipeline.text_pipeline.build_structured_chunks_from_all_table_rows",
                    return_value=[],
                ),
                patch.object(pipeline, "_target_fields", return_value=[]),
                patch("pipeline.text_pipeline.ROUTE_B_ENABLE_QUANT_FALLBACK", False),
                patch(
                    "pipeline.text_pipeline.ESGQuantTextPipeline.write_disabled_outputs",
                    return_value=disabled_summary,
                ) as disabled_write,
                patch("pipeline.text_pipeline.ESGQuantTextPipeline.run") as quant_run,
            ):
                summary = pipeline.run(Path(tmp) / "report.pdf")

        disabled_write.assert_called_once()
        quant_run.assert_not_called()
        self.assertFalse(summary["quantitative_fallback"]["enabled"])

    def test_unified_route_b_reuses_ingest_for_quantitative_fallback(self) -> None:
        ingest = {
            "pages": [],
            "chunks": [],
            "manifest": {"text_available": False},
            "cache_used": False,
            "paths": {},
        }
        quant_summary = {
            "target_fields": 0,
            "attempted_fields": 0,
            "matched_fields": 0,
            "llm_calls": 0,
        }

        with tempfile.TemporaryDirectory() as tmp:
            pipeline = ESGTextPipeline(Path(tmp))
            with (
                patch("pipeline.text_pipeline.ingest_pdf", return_value=ingest) as ingest_mock,
                patch(
                    "pipeline.text_pipeline.build_structured_chunks_from_all_table_rows",
                    return_value=[],
                ),
                patch.object(pipeline, "_target_fields", return_value=[]),
                patch("pipeline.text_pipeline.ROUTE_B_ENABLE_QUANT_FALLBACK", True),
                patch("pipeline.text_pipeline.ESGQuantTextPipeline.run", return_value=quant_summary) as quant_run,
            ):
                summary = pipeline.run(Path(tmp) / "report.pdf")

        ingest_mock.assert_called_once()
        self.assertIs(quant_run.call_args.kwargs["ingest"], ingest)
        self.assertEqual(quant_run.call_args.kwargs["chunks"], [])
        self.assertTrue(summary["unified_route_b"])
        self.assertEqual(summary["total_llm_calls"], 0)


if __name__ == "__main__":
    unittest.main()
