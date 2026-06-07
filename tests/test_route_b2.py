import unittest
import json
import sys
import types
from pathlib import Path
from tempfile import TemporaryDirectory
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
    FAISS_AVAILABLE = True
except ModuleNotFoundError:
    FAISS_AVAILABLE = False
    sys.modules["faiss"] = types.ModuleType("faiss")

from config.industry_applicability import get_applicability
from pipeline.quant_text_pipeline import (
    ESGQuantTextPipeline,
    choose_fusion_action,
    compute_b2_target_priority,
    detect_route_a_conflict,
)
from utils.industry_detector import detect_industry_from_text
from utils.llm_quant_extractor import normalize_quant_result
from utils.b2_result_validator import validate_b2_quant_result
from utils.route_b2_retriever import retrieve_quant_chunks
from utils.structured_rag_chunks import build_structured_chunks_from_all_table_rows


class RouteB2Tests(unittest.TestCase):
    def test_retrieve_quant_chunks_requires_number_and_keyword(self):
        field_item = {
            "field_key": "water_consumption",
            "name_cn": "用水量",
            "category": "E",
            "aliases": ["取水量"],
            "required_any": ["用水量"],
            "forbidden_any": ["废水"],
            "unit_examples": ["吨", "立方米"],
        }
        chunks = [
            {"chunk_id": "p1_0", "page_number": 1, "text": "公司持续推进节水管理。"},
            {"chunk_id": "p2_0", "page_number": 2, "text": "2024年用水量为1000吨。"},
            {"chunk_id": "p3_0", "page_number": 3, "text": "2024年废水排放量为1000吨。"},
        ]

        results = retrieve_quant_chunks(field_item, chunks, top_k=3)

        self.assertEqual(results[0]["chunk_id"], "p2_0")
        self.assertTrue(all("retrieval_score" in item for item in results))

    def test_retrieve_quant_chunks_uses_alias_terms(self):
        field_item = {
            "field_key": "social_security_coverage",
            "name_cn": "社会保险覆盖率",
            "category": "S",
            "aliases": ["社保覆盖率", "社会保险参保率"],
            "required_any": ["社会保险", "社保"],
            "forbidden_any": [],
            "unit_examples": ["%"],
        }
        chunks = [
            {"chunk_id": "p1_0", "page_number": 1, "text": "员工福利政策不断完善。"},
            {"chunk_id": "p2_0", "page_number": 2, "text": "2024年社保覆盖率达到100%。"},
        ]

        results = retrieve_quant_chunks(field_item, chunks, top_k=2)

        self.assertEqual(results[0]["chunk_id"], "p2_0")
        self.assertGreater(results[0]["bm25_score"], 0)
        self.assertTrue(results[0]["hit_keywords"] or results[0]["hit_query_terms"])

    def test_retrieve_quant_chunks_can_find_partial_alias_overlap(self):
        field_item = {
            "field_key": "employee_medical_checkup_coverage",
            "name_cn": "员工体检覆盖率",
            "category": "S",
            "aliases": ["员工健康体检覆盖率", "职业健康体检覆盖率"],
            "required_any": ["体检", "健康体检"],
            "forbidden_any": [],
            "unit_examples": ["%"],
        }
        chunks = [
            {"chunk_id": "p1_0", "page_number": 1, "text": "2024年职业健康检查覆盖比例为98%。"},
            {"chunk_id": "p2_0", "page_number": 2, "text": "2024年营业收入为100万元。"},
        ]

        results = retrieve_quant_chunks(field_item, chunks, top_k=2)

        self.assertEqual(results[0]["chunk_id"], "p1_0")
        self.assertIn("健康", results[0]["hit_query_terms"])

    @unittest.skipUnless(FAISS_AVAILABLE, "faiss is not installed")
    def test_retrieve_quant_chunks_uses_vector_index(self):
        field_item = {
            "field_key": "total_ghg_emissions",
            "name_cn": "温室气体排放总量",
            "category": "E",
            "aliases": ["碳排放"],
            "required_any": ["温室气体"],
            "forbidden_any": [],
            "unit_examples": ["吨二氧化碳当量"],
        }
        chunks = [
            {"chunk_id": "p1_0", "page_number": 1, "text": "2024年公司员工培训共计1000人次。"},
            {"chunk_id": "p2_0", "page_number": 2, "text": "报告期内排放量合计为1234吨二氧化碳当量。"},
        ]

        with TemporaryDirectory() as tmp:
            results = retrieve_quant_chunks(field_item, chunks, top_k=2, vector_index_dir=tmp)

        self.assertEqual(results[0]["chunk_id"], "p2_0")
        self.assertGreater(results[0]["vector_score"], 0)

    def test_normalize_quant_result_rejects_missing_year(self):
        field_item = {"field_key": "water_consumption"}
        result = normalize_quant_result(
            field_item,
            {
                "matched": True,
                "value": "1000",
                "raw_value": "1000吨",
                "unit": "吨",
                "year": "",
                "evidence": "用水量为1000吨",
                "confidence": 0.9,
            },
        )

        self.assertFalse(result["matched"])
        self.assertEqual(result["reason"], "matched_without_year")

    def test_normalize_quant_result_preserves_conversion_fields(self):
        field_item = {"field_key": "non_hazardous_waste"}
        result = normalize_quant_result(
            field_item,
            {
                "matched": True,
                "value": "1.5",
                "raw_value": "1500千克",
                "unit": "千克",
                "target_unit": "吨",
                "conversion": "千克转吨，除以1000",
                "year": "2024",
                "evidence": "2024年无害废弃物产生量为1500千克",
                "confidence": 0.9,
            },
        )

        self.assertTrue(result["matched"])
        self.assertEqual(result["target_unit"], "吨")
        self.assertIn("除以1000", result["conversion"])

    def test_validator_rejects_employee_count_percent(self):
        field_item = {
            "field_key": "male_employees",
            "required_any": ["男性员工"],
            "aliases": ["男性员工"],
            "forbidden_any": [],
        }
        result = validate_b2_quant_result(
            field_item,
            {
                "matched": True,
                "value": "58.22",
                "raw_value": "58.22%",
                "unit": "%",
                "year": "2024",
                "evidence": "男性员工比例 58.22%",
                "confidence": 0.95,
            },
        )

        self.assertFalse(result["matched"])
        self.assertIn("employee_count_uses_ratio", result["b2_validation_reason"])

    def test_validator_rejects_total_consumption_per_capita(self):
        field_item = {
            "field_key": "electricity_consumption",
            "required_any": ["耗电量"],
            "aliases": ["耗电量"],
            "forbidden_any": [],
        }
        result = validate_b2_quant_result(
            field_item,
            {
                "matched": True,
                "value": "2796",
                "raw_value": "2,796度/人",
                "unit": "度/人",
                "year": "2024",
                "evidence": "总行人均耗电量（度/人） 2,796",
                "confidence": 0.9,
            },
        )

        self.assertFalse(result["matched"])
        self.assertIn("total_field_uses_intensity_or_per_capita", result["b2_validation_reason"])

    def test_validator_accepts_intensity_field_with_per_unit_evidence(self):
        field_item = {
            "field_key": "energy_consumption_intensity",
            "unit_type": "intensity",
            "required_any": [],
            "aliases": [],
            "forbidden_any": [],
        }
        result = validate_b2_quant_result(
            field_item,
            {
                "matched": True,
                "value": "1.46",
                "raw_value": "1.46",
                "unit": "tce/ton product",
                "year": "2024",
                "evidence": "2024 energy consumption intensity 1.46 tce/ton product",
                "confidence": 0.9,
            },
        )

        self.assertTrue(result["matched"])
        self.assertTrue(result["b2_validation_ok"])

    def test_validator_accepts_per_employee_training_unit_as_anchor(self):
        field_item = {
            "field_key": "training_hours_per_employee",
            "unit_type": "hour",
            "required_any": ["per employee"],
            "aliases": [],
            "forbidden_any": [],
        }
        result = validate_b2_quant_result(
            field_item,
            {
                "matched": True,
                "value": "485.30",
                "raw_value": "485.30",
                "unit": "hours/person",
                "year": "2024",
                "evidence": "2024 employee training duration 485.30 hours/person",
                "confidence": 0.9,
            },
        )

        self.assertTrue(result["matched"])
        self.assertIn("soft_pass_per_employee_unit", result["b2_validation_reason"])

    def test_structured_route_a_row_creates_one_chunk_for_all_years(self):
        pages = [
            {
                "page_image": "page_60.png",
                "page_type": "performance_data_table",
                "tables": [
                    {
                        "table_title": "Energy",
                        "rows": [
                            {
                                "topic": "Energy management",
                                "metric_name": "Energy intensity",
                                "unit": "tce/ton product",
                                "values": {"2022": "1.87", "2023": "1.85", "2024": "1.46"},
                                "evidence_text": "",
                            }
                        ],
                    }
                ],
            }
        ]

        with TemporaryDirectory() as tmp:
            Path(tmp, "all_table_rows.json").write_text(json.dumps(pages), encoding="utf-8")
            chunks = build_structured_chunks_from_all_table_rows(Path(tmp))

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0]["chunk_id"], "route_a_row_0_0_0")
        self.assertIn("2024 1.46", chunks[0]["text"])

    def test_validator_soft_passes_strong_unit_anchor(self):
        field_item = {
            "field_key": "total_ghg_emissions",
            "required_any": ["温室气体排放总量"],
            "aliases": ["GHG排放总量"],
            "forbidden_any": [],
        }
        result = validate_b2_quant_result(
            field_item,
            {
                "matched": True,
                "value": "1234",
                "raw_value": "1234吨二氧化碳当量",
                "unit": "吨二氧化碳当量",
                "year": "2024",
                "evidence": "2024年排放量 1234吨二氧化碳当量",
                "confidence": 0.9,
                "retrieval_context": {
                    "max_vector_score": 0.22,
                    "hit_units": ["吨二氧化碳当量"],
                },
            },
        )

        self.assertTrue(result["matched"])
        self.assertTrue(result["b2_validation_ok"])
        self.assertIn("soft_pass_strong_unit_anchor", result["b2_validation_reason"])

    def test_validator_rejects_scope_without_explicit_scope(self):
        field_item = {
            "field_key": "scope_1_emissions",
            "required_any": ["范围一", "Scope 1"],
            "aliases": ["直接温室气体排放"],
            "forbidden_any": [],
        }
        result = validate_b2_quant_result(
            field_item,
            {
                "matched": True,
                "value": "1234",
                "raw_value": "1234吨二氧化碳当量",
                "unit": "吨二氧化碳当量",
                "year": "2024",
                "evidence": "2024年温室气体排放量 1234吨二氧化碳当量",
                "confidence": 0.9,
                "retrieval_context": {
                    "max_vector_score": 0.9,
                    "hit_units": ["吨二氧化碳当量"],
                },
            },
        )

        self.assertFalse(result["matched"])
        self.assertIn("scope_1_requires_explicit_scope_or_direct_emission", result["b2_validation_reason"])
        self.assertEqual(result.get("suggested_field_key"), "total_ghg_emissions")

    def test_validator_rejects_supply_shortage_drill_as_safety_drill(self):
        field_item = {
            "field_key": "safety_emergency_drill_count",
            "required_any": ["演练"],
            "aliases": ["应急演练次数"],
            "forbidden_any": [],
        }
        result = validate_b2_quant_result(
            field_item,
            {
                "matched": True,
                "value": "2",
                "raw_value": "2场",
                "unit": "场",
                "year": "2023",
                "evidence": "2023年公司组织了两次关键原材料供应不足应急演练",
                "confidence": 0.9,
            },
        )

        self.assertFalse(result["matched"])
        self.assertIn(
            "safety_drill_requires_safety_or_emergency_management_context",
            result["b2_validation_reason"],
        )

    def test_validator_accepts_independent_directors_compact_phrase(self):
        field_item = {
            "field_key": "independent_directors",
            "required_any": ["独立董事人数", "独立董事数量", "独董人数"],
            "aliases": ["独立董事人数"],
            "forbidden_any": ["比例", "%"],
        }
        result = validate_b2_quant_result(
            field_item,
            {
                "matched": True,
                "value": "3",
                "raw_value": "3 名",
                "unit": "名",
                "year": "2024",
                "evidence": "截至2024年底，公司董事会在任董事8名，其中独立董事3名。",
                "confidence": 0.9,
            },
        )

        self.assertTrue(result["matched"])
        self.assertTrue(result["b2_validation_ok"])
        self.assertIn("soft_pass_field_anchor", result["b2_validation_reason"])

    def test_validator_accepts_board_size_with_independent_director_context(self):
        field_item = {
            "field_key": "board_size",
            "required_any": ["董事会人数", "董事人数", "董事会成员人数"],
            "aliases": ["董事会人数"],
            "forbidden_any": ["独立董事", "%", "比例"],
        }
        result = validate_b2_quant_result(
            field_item,
            {
                "matched": True,
                "value": "8",
                "raw_value": "8 名",
                "unit": "名",
                "year": "2024",
                "evidence": "截至2024年底，公司董事会在任董事8名，其中独立董事3名；监事会在任监事3名。",
                "confidence": 0.9,
            },
        )

        self.assertTrue(result["matched"])
        self.assertTrue(result["b2_validation_ok"])
        self.assertIn("soft_pass_field_anchor", result["b2_validation_reason"])

    def test_validator_does_not_soft_pass_percent(self):
        field_item = {
            "field_key": "training_coverage_rate",
            "required_any": ["培训覆盖率"],
            "aliases": ["培训覆盖率"],
            "forbidden_any": [],
        }
        result = validate_b2_quant_result(
            field_item,
            {
                "matched": True,
                "value": "100",
                "raw_value": "100%",
                "unit": "%",
                "year": "2024",
                "evidence": "覆盖率 100%",
                "confidence": 0.9,
                "retrieval_context": {
                    "max_vector_score": 0.9,
                    "hit_units": ["%"],
                },
            },
        )

        self.assertFalse(result["matched"])
        self.assertIn("required_keyword_missing_in_evidence", result["b2_validation_reason"])

    def test_compute_b2_target_priority_prefers_strong_retrieval(self):
        weak = [
            {
                "retrieval_score": 10,
                "vector_score": 0.01,
                "number_count": 1,
                "hit_units": [],
                "hit_forbidden": [],
                "text": "2024年数据",
            }
        ]
        strong = [
            {
                "retrieval_score": 25,
                "vector_score": 0.2,
                "number_count": 4,
                "hit_units": ["kWh"],
                "hit_forbidden": [],
                "text": "2024年用电量1000kWh",
            }
        ]

        self.assertGreater(compute_b2_target_priority(strong), compute_b2_target_priority(weak))

    def test_compute_b2_target_priority_uses_industry_weight(self):
        chunks = [
            {
                "retrieval_score": 20,
                "vector_score": 0.1,
                "number_count": 2,
                "hit_units": [],
                "hit_forbidden": [],
                "text": "2024年数据100",
            }
        ]

        finance_waste = compute_b2_target_priority(chunks, field_key="hazardous_waste", industry="finance")
        finance_training = compute_b2_target_priority(chunks, field_key="training_coverage_rate", industry="finance")

        self.assertLess(finance_waste, finance_training)

    def test_fusion_extracts_missing_route_a_field(self):
        action, reason = choose_fusion_action(
            {"status": "missing", "confidence": "0"},
            [],
        )

        self.assertEqual(action, "extract_missing")
        self.assertEqual(reason, "route_a_missing")

    def test_fusion_skips_llm_for_high_confidence_route_a_without_conflict(self):
        action, reason = choose_fusion_action(
            {
                "status": "extracted",
                "value": "100",
                "raw_value": "100",
                "confidence": "0.95",
            },
            [
                {
                    "chunk_type": "route_a_structured_row",
                    "text": "2024 water consumption 100 tonnes",
                    "hit_keywords": ["water consumption"],
                    "hit_query_terms": [],
                }
            ],
        )

        self.assertEqual(action, "retrieval_only")
        self.assertEqual(reason, "route_a_high_confidence_no_conflict")

    def test_fusion_verifies_low_confidence_route_a(self):
        action, reason = choose_fusion_action(
            {
                "status": "extracted",
                "value": "100",
                "raw_value": "100",
                "confidence": "0.7",
            },
            [],
        )

        self.assertEqual(action, "verify_route_a")
        self.assertEqual(reason, "route_a_low_confidence")

    def test_fusion_detects_conflicting_structured_candidate(self):
        route_a_row = {
            "field_key": "water_consumption",
            "status": "extracted",
            "value": "100",
            "raw_value": "100",
            "confidence": "0.95",
            "year": "2024",
            "row_label": "Water consumption",
        }
        chunks = [
            {
                "chunk_type": "route_a_structured_row",
                "text": "2024 water consumption 120 tonnes",
                "metric_name": "Water consumption",
                "values": {"2024": "120"},
                "hit_keywords": ["water consumption"],
                "hit_query_terms": [],
            }
        ]

        self.assertTrue(detect_route_a_conflict(route_a_row, chunks))
        action, reason = choose_fusion_action(route_a_row, chunks)
        self.assertEqual(action, "verify_route_a")
        self.assertEqual(reason, "route_a_retrieval_conflict")

    def test_fusion_ignores_related_metric_and_historical_values(self):
        route_a_row = {
            "field_key": "water_consumption",
            "status": "extracted",
            "value": "100",
            "raw_value": "100",
            "confidence": "0.95",
            "year": "2024",
            "row_label": "Water consumption",
        }
        chunks = [
            {
                "chunk_type": "route_a_structured_row",
                "metric_name": "Water consumption",
                "values": {"2023": "80", "2024": "100"},
                "hit_keywords": ["Water consumption"],
                "hit_query_terms": [],
            },
            {
                "chunk_type": "route_a_structured_row",
                "metric_name": "Wastewater discharge",
                "values": {"2024": "120"},
                "hit_keywords": [],
                "hit_query_terms": ["water"],
            },
        ]

        self.assertFalse(detect_route_a_conflict(route_a_row, chunks))

    def test_quant_fusion_retrieves_high_confidence_route_a_without_llm(self):
        item = {
            "field_key": "water_consumption",
            "name_cn": "Water consumption",
            "category": "E",
            "indicator_type": "quantitative",
        }
        route_a_row = {
            "field_key": "water_consumption",
            "status": "extracted",
            "value": "100",
            "raw_value": "100",
            "unit": "tonnes",
            "year": "2024",
            "confidence": "0.95",
        }
        retrieved = [
            {
                "chunk_id": "route_a_row_0_0_0",
                "chunk_type": "route_a_structured_row",
                "page_number": 1,
                "text": "2024 Water consumption 100 tonnes",
                "retrieval_score": 20,
                "vector_score": 0,
                "number_count": 2,
                "hit_keywords": ["Water consumption"],
                "hit_query_terms": [],
                "hit_units": ["tonnes"],
                "hit_forbidden": [],
            }
        ]
        ingest = {
            "pages": [],
            "chunks": [],
            "manifest": {"text_available": True},
            "cache_used": False,
            "paths": {},
        }

        with TemporaryDirectory() as tmp:
            pipeline = ESGQuantTextPipeline(Path(tmp))
            with (
                patch.object(pipeline, "_route_a_quant_targets", return_value=[{"item": item, "route_a_row": route_a_row}]),
                patch("pipeline.quant_text_pipeline.retrieve_quant_chunks", return_value=retrieved),
                patch("pipeline.quant_text_pipeline.extract_quant_indicator_with_llm") as llm_extract,
            ):
                summary = pipeline.run(Path(tmp) / "report.pdf", ingest=ingest, chunks=retrieved, structured_chunks=retrieved)

        llm_extract.assert_not_called()
        self.assertEqual(summary["retrieval_only_fields"], 1)
        self.assertEqual(summary["llm_calls"], 0)

    def test_detect_industry_and_applicability(self):
        self.assertEqual(detect_industry_from_text("西安银行股份有限公司社会责任报告"), "finance")
        self.assertEqual(get_applicability("finance", "hazardous_waste"), "not_applicable")


if __name__ == "__main__":
    unittest.main()
