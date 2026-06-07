import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, List

from config.schema import ESG_SCHEMA, ROUTE_A_SCHEMA
from config.industry_applicability import NOT_APPLICABLE, UNLIKELY, get_applicability, get_priority_weight
from config.settings import (
    MAX_B2_LLM_CALLS_PER_REPORT,
    ROUTE_B2_FUSION_ENABLED,
    ROUTE_B2_SKIP_UNLIKELY,
    ROUTE_B2_TOP_K,
    ROUTE_B2_USE_VECTOR_RAG,
    ROUTE_B2_VECTOR_TOP_K,
    ROUTE_B2_VERIFY_CONFLICTS,
    ROUTE_B2_VERIFY_ROUTE_A_MAX_CONFIDENCE,
    ROUTE_B2_VERIFY_ROUTE_A_ZERO,
    ROUTE_B_CHUNK_OVERLAP,
    ROUTE_B_CHUNK_SIZE,
    ROUTE_B_CHUNK_STRATEGY,
)
from pipeline.merge_pipeline import load_csv
from utils.llm_quant_extractor import extract_quant_indicator_with_llm
from utils.pdf_ingest import ingest_pdf
from utils.route_b2_retriever import retrieve_quant_chunks
from utils.industry_detector import detect_industry
from utils.structured_rag_chunks import build_structured_chunks_from_all_table_rows


STRONG_UNIT_HINTS = [
    "tCO2e",
    "CO2e",
    "吨二氧化碳当量",
    "万吨二氧化碳当量",
    "MWh",
    "kWh",
    "兆瓦时",
    "千瓦时",
]

def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value or "").replace(",", "").replace("%", "").strip())
    except Exception:
        return default


def _normalized_number(value: Any) -> str:
    text = str(value or "").strip().replace(",", "").replace("%", "")
    try:
        number = float(text)
        return str(int(number)) if number.is_integer() else str(number)
    except Exception:
        return text


def _normalized_label(value: Any) -> str:
    return re.sub(r"[\s\W_]+", "", str(value or "").lower())


def _chunk_value_for_year(chunk: Dict[str, Any], year: Any) -> str:
    values = chunk.get("values")
    if not isinstance(values, dict):
        return ""
    year_text = str(year or "")
    for key, value in values.items():
        if year_text and year_text in str(key):
            return _normalized_number(value)
    return ""


def detect_route_a_conflict(route_a_row: Dict[str, Any], retrieved_chunks: List[Dict[str, Any]]) -> bool:
    """Detect a real same-metric conflict, excluding related rows and historical values."""
    route_a_value = _normalized_number(route_a_row.get("raw_value") or route_a_row.get("value"))
    if not route_a_value:
        return False

    field_key = str(route_a_row.get("field_key") or "")
    route_a_label = _normalized_label(route_a_row.get("row_label"))
    route_a_year = route_a_row.get("year")
    for chunk in retrieved_chunks[:3]:
        if chunk.get("chunk_type") != "route_a_structured_row":
            continue
        if not (chunk.get("hit_keywords") or chunk.get("hit_query_terms")):
            continue

        chunk_label = _normalized_label(chunk.get("metric_name"))
        if field_key == "water_consumption":
            if (
                any(word in route_a_label for word in ["新鲜水", "取水"])
                and "总用水量" in chunk_label
            ):
                return True

        if not route_a_label or chunk_label != route_a_label:
            continue

        candidate_value = _chunk_value_for_year(chunk, route_a_year)
        if candidate_value and candidate_value != route_a_value:
            return True
    return False


def choose_fusion_action(
    route_a_row: Dict[str, Any],
    retrieved_chunks: List[Dict[str, Any]],
) -> tuple[str, str]:
    if str(route_a_row.get("status", "")).strip() != "extracted":
        return "extract_missing", "route_a_missing"
    if _to_float(route_a_row.get("confidence")) < ROUTE_B2_VERIFY_ROUTE_A_MAX_CONFIDENCE:
        return "verify_route_a", "route_a_low_confidence"
    if ROUTE_B2_VERIFY_ROUTE_A_ZERO and _to_float(route_a_row.get("value")) == 0.0:
        return "verify_route_a", "route_a_zero_value"
    if ROUTE_B2_VERIFY_CONFLICTS and detect_route_a_conflict(route_a_row, retrieved_chunks):
        return "verify_route_a", "route_a_retrieval_conflict"
    return "retrieval_only", "route_a_high_confidence_no_conflict"


def compute_b2_target_priority(
    retrieved_chunks: List[Dict[str, Any]],
    field_key: str = "",
    industry: str = "general",
) -> float:
    if not retrieved_chunks:
        return float(get_priority_weight(industry, field_key))

    best = retrieved_chunks[0]
    max_retrieval_score = max(float(chunk.get("retrieval_score") or 0.0) for chunk in retrieved_chunks)
    max_vector_score = max(float(chunk.get("vector_score") or 0.0) for chunk in retrieved_chunks)
    max_number_count = max(int(chunk.get("number_count") or 0) for chunk in retrieved_chunks)
    has_forbidden = any(chunk.get("hit_forbidden") for chunk in retrieved_chunks)
    has_strong_unit = any(
        unit in STRONG_UNIT_HINTS
        for chunk in retrieved_chunks
        for unit in (chunk.get("hit_units", []) or [])
    )
    has_year = "20" in str(best.get("text", ""))

    priority = max_retrieval_score
    priority += max_vector_score * 20
    priority += 15 if has_strong_unit else 0
    priority += 5 if has_year else 0
    priority += min(max_number_count, 10)
    priority -= 20 if has_forbidden else 0
    priority += get_priority_weight(industry, field_key)
    return round(priority, 4)


class ESGQuantTextPipeline:
    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _save_json(self, path: Path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _save_csv(self, path: Path, rows: List[Dict[str, Any]]):
        fieldnames = [
            "field_key",
            "field_name_cn",
            "category",
            "matched",
            "value",
            "raw_value",
            "unit",
            "target_unit",
            "conversion",
            "year",
            "evidence",
            "source_pages",
            "confidence",
            "reason",
            "b2_validation_ok",
            "b2_validation_reason",
            "retrieval_priority",
            "fusion_action",
            "route_a_status",
            "route_a_value",
            "route_a_raw_value",
            "route_a_unit",
            "route_a_year",
            "route_a_confidence",
            "industry",
            "applicability",
            "retrieved_chunks",
            "route",
        ]

        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        **row,
                        "source_pages": json.dumps(row.get("source_pages", []), ensure_ascii=False),
                        "retrieved_chunks": json.dumps(row.get("retrieved_chunks", []), ensure_ascii=False),
                    }
                )

    def write_disabled_outputs(self, reason: str = "quantitative_fallback_disabled") -> Dict[str, Any]:
        summary = {
            "route_b2_available": False,
            "quantitative_fallback_available": False,
            "enabled": False,
            "reason": reason,
            "target_fields": 0,
            "attempted_fields": 0,
            "matched_fields": 0,
            "llm_calls": 0,
            "skipped_no_relevant_chunks": 0,
        }
        self._save_json(self.output_dir / "route_b_quant_results.json", [])
        self._save_csv(self.output_dir / "route_b_quant_results.csv", [])
        self._save_json(self.output_dir / "route_b_quant_summary.json", summary)
        return summary

    def _route_a_missing_quant_fields(self) -> List[Dict[str, Any]]:
        return [
            row["item"]
            for row in self._route_a_quant_targets()
            if str(row["route_a_row"].get("status", "")).strip() != "extracted"
        ]

    def _route_a_quant_targets(self) -> List[Dict[str, Any]]:
        standard_path = self.output_dir / "standard_esg_results.csv"
        rows = load_csv(standard_path)
        route_a_by_key = {
            row.get("field_key"): row
            for row in rows
            if row.get("field_key")
        }

        targets = []
        for item in ROUTE_A_SCHEMA:
            field_key = item["field_key"]
            if item.get("indicator_type") != "quantitative":
                continue
            targets.append(
                {
                    "item": ESG_SCHEMA[field_key],
                    "route_a_row": route_a_by_key.get(
                        field_key,
                        {"field_key": field_key, "status": "missing", "confidence": 0.0},
                    ),
                }
            )
        return targets

    def run(
        self,
        pdf_path: Path,
        *,
        ingest: Dict[str, Any] | None = None,
        chunks: List[Dict[str, Any]] | None = None,
        structured_chunks: List[Dict[str, Any]] | None = None,
    ) -> Dict[str, Any]:
        pdf_path = Path(pdf_path)

        print("\n----- Running Quantitative Fallback / Unified Route B -----")
        print(f"PDF: {pdf_path}")

        reused_unified_ingest = ingest is not None
        if ingest is None:
            ingest = ingest_pdf(
                pdf_path=pdf_path,
                output_dir=self.output_dir,
                chunk_size=ROUTE_B_CHUNK_SIZE,
                chunk_overlap=ROUTE_B_CHUNK_OVERLAP,
            )
        text_chunks = ingest["chunks"]
        if structured_chunks is None:
            structured_chunks = build_structured_chunks_from_all_table_rows(self.output_dir)
        if chunks is None:
            chunks = [*text_chunks, *structured_chunks]
        text_available = bool(ingest["manifest"].get("text_available"))
        rag_available = text_available or bool(structured_chunks)
        target_states = self._route_a_quant_targets()
        if not ROUTE_B2_FUSION_ENABLED:
            target_states = [
                row
                for row in target_states
                if str(row["route_a_row"].get("status", "")).strip() != "extracted"
            ]
        targets = [row["item"] for row in target_states]
        industry = detect_industry(pdf_path.name, ingest.get("pages", []))

        results = []
        llm_calls = 0
        ranked_targets = []

        if not rag_available:
            for target_state in target_states:
                missing = self._missing_row(target_state["item"], "no_text_or_structured_table_chunks")
                self._attach_route_a_context(missing, target_state["route_a_row"])
                results.append(missing)
        else:
            for target_state in target_states:
                item = target_state["item"]
                route_a_row = target_state["route_a_row"]
                applicability = get_applicability(industry, item["field_key"])
                if applicability == NOT_APPLICABLE or (ROUTE_B2_SKIP_UNLIKELY and applicability == UNLIKELY):
                    reason = (
                        "industry_unlikely_skipped"
                        if applicability == UNLIKELY
                        else "industry_not_applicable_skipped"
                    )
                    missing = self._missing_row(item, reason)
                    missing["industry"] = industry
                    missing["applicability"] = applicability
                    self._attach_route_a_context(missing, route_a_row)
                    results.append(missing)
                    continue

                retrieved_chunks = retrieve_quant_chunks(
                    item,
                    chunks,
                    top_k=ROUTE_B2_TOP_K,
                    vector_index_dir=self.output_dir / "rag_index",
                )
                if not retrieved_chunks:
                    missing = self._missing_row(item, "no_relevant_chunks")
                    missing["industry"] = industry
                    missing["applicability"] = applicability
                    self._attach_route_a_context(missing, route_a_row)
                    results.append(missing)
                    continue
                fusion_action, fusion_reason = choose_fusion_action(route_a_row, retrieved_chunks)
                priority = compute_b2_target_priority(
                    retrieved_chunks,
                    field_key=item["field_key"],
                    industry=industry,
                )
                ranked_targets.append(
                    {
                        "item": item,
                        "retrieved_chunks": retrieved_chunks,
                        "retrieval_priority": priority,
                        "applicability": applicability,
                        "route_a_row": route_a_row,
                        "fusion_action": fusion_action,
                        "fusion_reason": fusion_reason,
                    }
                )

            ranked_targets.sort(
                key=lambda row: (
                    row["fusion_action"] != "retrieval_only",
                    row["retrieval_priority"],
                ),
                reverse=True,
            )

            for target in ranked_targets:
                item = target["item"]
                retrieved_chunks = target["retrieved_chunks"]
                retrieval_priority = target["retrieval_priority"]
                route_a_row = target["route_a_row"]
                fusion_action = target["fusion_action"]
                if fusion_action == "retrieval_only":
                    row = self._missing_row(item, target["fusion_reason"])
                    row["retrieval_priority"] = retrieval_priority
                    row["retrieved_chunks"] = self._format_retrieved_chunks(retrieved_chunks)
                    row["industry"] = industry
                    row["applicability"] = target["applicability"]
                    row["fusion_action"] = fusion_action
                    self._attach_route_a_context(row, route_a_row)
                    results.append(row)
                    continue
                if llm_calls >= MAX_B2_LLM_CALLS_PER_REPORT:
                    missing = self._missing_row(item, "max_b2_llm_calls_per_report_reached")
                    missing["retrieval_priority"] = retrieval_priority
                    missing["retrieved_chunks"] = self._format_retrieved_chunks(retrieved_chunks)
                    missing["industry"] = industry
                    missing["applicability"] = target["applicability"]
                    missing["fusion_action"] = fusion_action
                    self._attach_route_a_context(missing, route_a_row)
                    results.append(missing)
                    continue

                print(f"[Route B/quant fusion] {fusion_action} {item['field_key']} priority={retrieval_priority}")
                llm_result = extract_quant_indicator_with_llm(
                    field_item=item,
                    chunks=retrieved_chunks,
                )
                if llm_result.get("reason") != "model_call_budget_exhausted":
                    llm_calls += 1

                result_row = {
                        "field_key": item["field_key"],
                        "field_name_cn": item["name_cn"],
                        "category": item["category"],
                        "matched": bool(llm_result.get("matched")),
                        "value": llm_result.get("value"),
                        "raw_value": llm_result.get("raw_value", ""),
                        "unit": llm_result.get("unit", ""),
                        "target_unit": llm_result.get("target_unit", ""),
                        "conversion": llm_result.get("conversion", ""),
                        "year": llm_result.get("year", ""),
                        "evidence": llm_result.get("evidence", ""),
                        "source_pages": llm_result.get("source_pages", []),
                        "confidence": llm_result.get("confidence", 0.0),
                        "reason": llm_result.get("reason", ""),
                        "b2_validation_ok": llm_result.get("b2_validation_ok", ""),
                        "b2_validation_reason": llm_result.get("b2_validation_reason", ""),
                        "retrieval_priority": retrieval_priority,
                        "fusion_action": fusion_action,
                        "industry": industry,
                        "applicability": target["applicability"],
                        "retrieved_chunks": self._format_retrieved_chunks(retrieved_chunks),
                        "route": "B_quantitative_fallback",
                    }
                self._attach_route_a_context(result_row, route_a_row)
                results.append(result_row)

        matched_count = sum(1 for row in results if row.get("matched"))

        self._save_json(self.output_dir / "route_b_quant_results.json", results)
        self._save_csv(self.output_dir / "route_b_quant_results.csv", results)

        summary = {
            "route_b2_available": rag_available,
            "quantitative_fallback_available": rag_available,
            "enabled": True,
            "target_fields": len(targets),
            "attempted_fields": llm_calls,
            "retrieved_fields": len(ranked_targets),
            "llm_attempted_fields": llm_calls,
            "retrieval_only_fields": sum(1 for row in results if row.get("fusion_action") == "retrieval_only"),
            "verified_route_a_fields": sum(1 for row in results if row.get("fusion_action") == "verify_route_a"),
            "missing_route_a_fields": sum(
                1
                for row in target_states
                if str(row["route_a_row"].get("status", "")).strip() != "extracted"
            ),
            "matched_fields": matched_count,
            "llm_calls": llm_calls,
            "industry": industry,
            "text_chunk_count": len(text_chunks),
            "structured_chunk_count": len(structured_chunks),
            "combined_chunk_count": len(chunks),
            "skipped_by_budget": sum(
                1
                for row in results
                if row.get("reason") in {
                    "max_b2_llm_calls_per_report_reached",
                    "model_call_budget_exhausted",
                }
            ),
            "skipped_by_industry": sum(1 for row in results if row.get("reason") == "industry_not_applicable_skipped"),
            "skipped_by_unlikely": sum(1 for row in results if row.get("reason") == "industry_unlikely_skipped"),
            "skipped_no_relevant_chunks": sum(1 for row in results if row.get("reason") == "no_relevant_chunks"),
            "total_llm_calls_cost": llm_calls,
            "ingest_cache_used": ingest["cache_used"],
            "reused_unified_ingest": reused_unified_ingest,
            "ingest_paths": ingest["paths"],
            "retrieval_ranked_targets": [
                {
                    "field_key": row["item"]["field_key"],
                    "applicability": row["applicability"],
                    "retrieval_priority": row["retrieval_priority"],
                    "fusion_action": row["fusion_action"],
                    "fusion_reason": row["fusion_reason"],
                    "top_chunk_id": row["retrieved_chunks"][0].get("chunk_id") if row["retrieved_chunks"] else "",
                    "top_page_number": row["retrieved_chunks"][0].get("page_number") if row["retrieved_chunks"] else "",
                    "top_retrieval_score": row["retrieved_chunks"][0].get("retrieval_score") if row["retrieved_chunks"] else 0,
                    "top_vector_score": row["retrieved_chunks"][0].get("vector_score") if row["retrieved_chunks"] else 0,
                }
                for row in ranked_targets
            ],
            "token_budget": {
                "route_b2_top_k": ROUTE_B2_TOP_K,
                "route_b2_use_vector_rag": ROUTE_B2_USE_VECTOR_RAG,
                "route_b2_vector_top_k": ROUTE_B2_VECTOR_TOP_K,
                "route_b2_skip_unlikely": ROUTE_B2_SKIP_UNLIKELY,
                "route_b2_fusion_enabled": ROUTE_B2_FUSION_ENABLED,
                "route_b2_verify_route_a_max_confidence": ROUTE_B2_VERIFY_ROUTE_A_MAX_CONFIDENCE,
                "route_b2_verify_route_a_zero": ROUTE_B2_VERIFY_ROUTE_A_ZERO,
                "route_b2_verify_conflicts": ROUTE_B2_VERIFY_CONFLICTS,
                "route_b_chunk_strategy": ROUTE_B_CHUNK_STRATEGY,
                "route_b_chunk_size": ROUTE_B_CHUNK_SIZE,
                "route_b_chunk_overlap": ROUTE_B_CHUNK_OVERLAP,
                "max_b2_llm_calls_per_report": MAX_B2_LLM_CALLS_PER_REPORT,
            },
        }
        self._save_json(self.output_dir / "route_b_quant_summary.json", summary)

        print(
            f"[Route B/quant fusion] matched={matched_count}, llm_calls={llm_calls}, "
            f"retrieved={len(ranked_targets)}/{len(targets)} targets"
        )
        return summary

    def _attach_route_a_context(self, row: Dict[str, Any], route_a_row: Dict[str, Any]) -> None:
        row.update(
            {
                "route_a_status": route_a_row.get("status", ""),
                "route_a_value": route_a_row.get("value", ""),
                "route_a_raw_value": route_a_row.get("raw_value", ""),
                "route_a_unit": route_a_row.get("unit", ""),
                "route_a_year": route_a_row.get("year", ""),
                "route_a_confidence": route_a_row.get("confidence", ""),
            }
        )

    def _format_retrieved_chunks(self, retrieved_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return [
            {
                "chunk_id": chunk.get("chunk_id"),
                "page_number": chunk.get("page_number"),
                "retrieval_score": chunk.get("retrieval_score"),
                "bm25_score": chunk.get("bm25_score"),
                "vector_score": chunk.get("vector_score"),
                "hit_keywords": chunk.get("hit_keywords", []),
                "hit_query_terms": chunk.get("hit_query_terms", []),
                "hit_units": chunk.get("hit_units", []),
                "hit_forbidden": chunk.get("hit_forbidden", []),
                "number_count": chunk.get("number_count"),
            }
            for chunk in retrieved_chunks
        ]

    def _missing_row(self, item: Dict[str, Any], reason: str) -> Dict[str, Any]:
        return {
            "field_key": item["field_key"],
            "field_name_cn": item["name_cn"],
            "category": item["category"],
            "matched": False,
            "value": None,
            "raw_value": "",
            "unit": "",
            "target_unit": "",
            "conversion": "",
            "year": "",
            "evidence": "",
            "source_pages": [],
            "confidence": 0.0,
            "reason": reason,
            "b2_validation_ok": False,
            "b2_validation_reason": reason,
            "retrieval_priority": 0.0,
            "fusion_action": "",
            "route_a_status": "",
            "route_a_value": "",
            "route_a_raw_value": "",
            "route_a_unit": "",
            "route_a_year": "",
            "route_a_confidence": "",
            "industry": "",
            "applicability": "",
            "retrieved_chunks": [],
            "route": "B_quantitative_fallback",
        }
