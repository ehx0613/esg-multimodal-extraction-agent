import csv
import json
from pathlib import Path
from typing import Any, Dict, List

from config.industry_applicability import NOT_APPLICABLE, get_applicability, is_applicable
from config.schema import ALL_SCHEMA, ESG_FIELD_KEYS
from config.settings import ROUTE_B2_MIN_CONFIDENCE
from utils.industry_detector import detect_industry_from_report_dir
from utils.result_guard import safe_write_csv, safe_write_json, validate_standard_results


EMPTY_VALUES = {"", "None", "none", "null", "NULL", "N/A", "NA", "nan"}
EXPECTED_RESULT_ROWS = len(ESG_FIELD_KEYS)


def load_csv(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def build_empty_route_a_rows() -> List[Dict[str, Any]]:
    return [
        {
            "field_key": item["field_key"],
            "name_cn": item.get("name_cn", ""),
            "category": item.get("category", ""),
            "indicator_type": item.get("indicator_type", ""),
            "value_type": item.get("value_type", ""),
            "status": "missing",
            "value": "",
            "raw_value": "",
            "unit": "",
            "year": "",
            "confidence": "0",
            "match_reason": "route_a_not_available",
            "evidence_text": "",
            "page_image": "",
        }
        for item in ALL_SCHEMA
    ]


def to_float(value, default=0.0) -> float:
    try:
        if value in EMPTY_VALUES or value is None:
            return default
        text = str(value).strip().replace(",", "").replace("，", "").replace("%", "")
        return float(text)
    except Exception:
        return default


def parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value

    text = str(value).strip().lower()
    return text in {"true", "1", "yes", "y", "是", "匹配", "matched"}


def parse_source_pages(value):
    if value is None:
        return []

    if isinstance(value, list):
        return value

    text = str(value).strip()
    if not text:
        return []

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass

    return [text]


def has_evidence(value) -> bool:
    return str(value or "").strip() not in EMPTY_VALUES


def is_zero_like(value) -> bool:
    text = str(value or "").strip()
    if text in EMPTY_VALUES or text in {"-", "/", "—", "–"}:
        return True
    return abs(to_float(text, default=0.0)) == 0.0


def is_nonzero_like(value) -> bool:
    text = str(value or "").strip()
    if text in EMPTY_VALUES or text in {"-", "/", "—", "–"}:
        return False
    return abs(to_float(text, default=0.0)) > 0.0


def b2_should_override_route_a(item: Dict[str, Any], row: Dict[str, Any]) -> bool:
    if item.get("source_route") != "route_a_appendix_table":
        return False
    if not is_nonzero_like(row.get("value")):
        return False
    if not has_evidence(row.get("evidence")):
        return False

    route_a_confidence = to_float(item.get("confidence"), 0.0)
    route_b2_confidence = to_float(row.get("confidence"), 0.0)

    if is_zero_like(item.get("value")):
        return route_b2_confidence >= max(ROUTE_B2_MIN_CONFIDENCE, route_a_confidence - 0.05)

    if item.get("field_key") == "water_consumption":
        route_a_evidence = str(item.get("evidence") or item.get("row_label") or "")
        route_b2_evidence = str(row.get("evidence") or "")
        route_a_is_partial = any(word in route_a_evidence for word in ["新鲜水", "取水"])
        route_b2_is_total = "总用水量" in route_b2_evidence
        same_year = not item.get("year") or not row.get("year") or str(item.get("year")) == str(row.get("year"))
        return (
            route_a_is_partial
            and route_b2_is_total
            and same_year
            and route_b2_confidence >= max(ROUTE_B2_MIN_CONFIDENCE, route_a_confidence)
        )

    return False


def is_route_a_extracted(row: Dict[str, Any]) -> bool:
    return str(row.get("status", "")).strip() == "extracted"


def is_route_b_matched(row: Dict[str, Any], min_confidence: float = 0.5) -> bool:
    matched = parse_bool(row.get("matched"))
    confidence = to_float(row.get("confidence"), 0.0)
    return matched and confidence >= min_confidence


def b2_context_is_safe(row: Dict[str, Any]) -> bool:
    if row.get("field_key") != "safety_emergency_drill_count":
        return True
    evidence = str(row.get("evidence") or "")
    return any(
        word in evidence
        for word in ["安全", "生产安全", "消防", "环境应急", "突发事件", "应急预案", "事故", "防灾"]
    )


def normalize_route_a_row(row: Dict[str, Any]) -> Dict[str, Any]:
    extracted = is_route_a_extracted(row)

    return {
        "field_key": row.get("field_key", ""),
        "field_name_cn": row.get("field_name_cn") or row.get("name_cn", ""),
        "category": row.get("category", ""),
        "indicator_type": row.get("indicator_type", ""),
        "value_type": row.get("value_type", ""),
        "status": "extracted" if extracted else "missing",
        "value": row.get("value", ""),
        "raw_value": row.get("raw_value", ""),
        "unit": row.get("unit", ""),
        "year": row.get("year", ""),
        "source_route": "route_a_appendix_table" if extracted else "missing",
        "confidence": row.get("confidence", "0"),
        "merge_reason": "route_a_selected" if extracted else "missing_after_route_a",
        "evidence": row.get("evidence_text", ""),
        "source_pages": row.get("page_image", ""),
        "row_label": row.get("row_label", ""),
        "topic": row.get("topic", ""),
        "table_title": row.get("table_title", ""),
        "page_image": row.get("page_image", ""),
        "route_a_status": row.get("status", ""),
        "route_a_confidence": row.get("confidence", "0"),
        "route_a_reason": row.get("match_reason", ""),
        "route_b_matched": "",
        "route_b_confidence": "",
        "route_b_summary": "",
        "route_b_evidence": "",
        "route_b_source_pages": "",
        "route_b_reason": "",
        "route_b2_matched": "",
        "route_b2_confidence": "",
        "route_b2_value": "",
        "route_b2_raw_value": "",
        "route_b2_unit": "",
        "route_b2_year": "",
        "route_b2_evidence": "",
        "route_b2_source_pages": "",
        "route_b2_reason": "",
        "industry": "",
        "applicability": "",
        "missing_reason": "",
    }


def apply_route_b_to_merged(
    merged_by_key: Dict[str, Dict[str, Any]],
    route_b_rows: List[Dict[str, Any]],
    min_confidence: float = 0.5,
):
    for row in route_b_rows:
        field_key = row.get("field_key", "")

        if not field_key:
            continue
        if field_key not in merged_by_key:
            continue
        if not is_route_b_matched(row, min_confidence=min_confidence):
            continue
        if str(row.get("route_b_validation_ok", "")).strip().lower() not in {"true", "1", "yes", "y"}:
            continue

        item = merged_by_key[field_key]
        source_pages = parse_source_pages(row.get("source_pages"))
        source_pages_text = json.dumps(source_pages, ensure_ascii=False)

        item["route_b_matched"] = "true"
        item["route_b_confidence"] = row.get("confidence", "")
        item["route_b_summary"] = row.get("summary", "")
        item["route_b_evidence"] = row.get("evidence", "")
        item["route_b_source_pages"] = source_pages_text
        item["route_b_reason"] = row.get("reason", "")

        if item.get("status") != "extracted":
            item["status"] = "extracted"
            item["value"] = row.get("value", "true")
            item["raw_value"] = row.get("value", "true")
            item["unit"] = ""
            item["year"] = ""
            item["source_route"] = "route_b_text_rag"
            item["confidence"] = row.get("confidence", "0")
            item["merge_reason"] = "route_b_filled_missing_route_a"
            item["evidence"] = row.get("evidence", "")
            item["source_pages"] = source_pages_text
            item["row_label"] = row.get("summary", "")
            item["topic"] = "正文定性机制"
            item["table_title"] = ""
            item["page_image"] = ""


def apply_route_b2_to_merged(
    merged_by_key: Dict[str, Dict[str, Any]],
    route_b2_rows: List[Dict[str, Any]],
    min_confidence: float = ROUTE_B2_MIN_CONFIDENCE,
):
    for row in route_b2_rows:
        field_key = row.get("field_key", "")

        if not field_key:
            continue
        if field_key not in merged_by_key:
            continue
        if not is_route_b_matched(row, min_confidence=min_confidence):
            continue
        if str(row.get("b2_validation_ok", "")).strip().lower() not in {"true", "1", "yes", "y"}:
            continue
        if not b2_context_is_safe(row):
            continue

        item = merged_by_key[field_key]
        source_pages = parse_source_pages(row.get("source_pages"))
        source_pages_text = json.dumps(source_pages, ensure_ascii=False)

        item["route_b2_matched"] = "true"
        item["route_b2_confidence"] = row.get("confidence", "")
        item["route_b2_value"] = row.get("value", "")
        item["route_b2_raw_value"] = row.get("raw_value", "")
        item["route_b2_unit"] = row.get("target_unit") or row.get("unit", "")
        item["route_b2_year"] = row.get("year", "")
        item["route_b2_evidence"] = row.get("evidence", "")
        item["route_b2_source_pages"] = source_pages_text
        item["route_b2_reason"] = row.get("reason", "")

        if item.get("status") != "extracted":
            item["status"] = "extracted"
            item["value"] = row.get("value", "")
            item["raw_value"] = row.get("raw_value", row.get("value", ""))
            item["unit"] = row.get("target_unit") or row.get("unit", "")
            item["year"] = row.get("year", "")
            item["source_route"] = "route_b_quantitative_fallback"
            item["confidence"] = row.get("confidence", "0")
            item["merge_reason"] = "route_b2_filled_missing_route_a"
            item["evidence"] = row.get("evidence", "")
            item["source_pages"] = source_pages_text
            item["row_label"] = row.get("field_name_cn", "")
            item["topic"] = "quant_text_rag"
            item["table_title"] = ""
            item["page_image"] = ""
        elif b2_should_override_route_a(item, row):
            previous_value = item.get("value", "")
            previous_confidence = item.get("confidence", "")

            item["value"] = row.get("value", "")
            item["raw_value"] = row.get("raw_value", row.get("value", ""))
            item["unit"] = row.get("target_unit") or row.get("unit", "")
            item["year"] = row.get("year", "")
            item["source_route"] = "route_b_quantitative_fallback"
            item["confidence"] = row.get("confidence", "0")
            item["evidence"] = row.get("evidence", "")
            item["source_pages"] = source_pages_text
            item["row_label"] = row.get("field_name_cn", item.get("row_label", ""))
            item["topic"] = "quant_text_rag"
            item["table_title"] = ""
            item["page_image"] = ""
            override_kind = (
                "route_b2_override_route_a_zero_with_evidence"
                if is_zero_like(previous_value)
                else "route_b2_override_route_a_preferred_scope"
            )
            item["merge_reason"] = (
                f"{override_kind}"
                f":route_a_value={previous_value}"
                f":route_a_confidence={previous_confidence}"
            )
        elif item.get("source_route") == "route_a_appendix_table":
            if is_zero_like(item.get("value")) and not is_nonzero_like(row.get("value")):
                item["merge_reason"] = "route_a_kept_b2_also_zero_or_empty"
            elif is_zero_like(item.get("value")) and not has_evidence(row.get("evidence")):
                item["merge_reason"] = "route_a_kept_b2_missing_evidence"
            else:
                item["merge_reason"] = "route_a_kept_over_b2"


def budget_exhausted_field_keys(*row_groups: List[Dict[str, Any]]) -> set[str]:
    reasons = {
        "model_call_budget_exhausted",
        "max_llm_calls_per_report_reached",
        "max_b2_llm_calls_per_report_reached",
    }
    return {
        str(row.get("field_key"))
        for rows in row_groups
        for row in rows
        if row.get("field_key") and row.get("reason") in reasons
    }


def apply_missing_status(
    row: Dict[str, Any],
    *,
    applicability: str,
    industry: str,
    budget_exhausted_keys: set[str],
) -> None:
    if row.get("status") == "extracted":
        row["missing_reason"] = ""
    elif applicability == NOT_APPLICABLE:
        row["missing_reason"] = "not_applicable_by_industry"
        row["merge_reason"] = f"Status: N/A (Industry: {industry})"
    elif row.get("field_key") in budget_exhausted_keys:
        row["status"] = "extraction_incomplete_budget_exhausted"
        row["missing_reason"] = "extraction_incomplete_budget_exhausted"
        row["merge_reason"] = "model_budget_exhausted_before_extraction_completed"
    else:
        row["missing_reason"] = "not_disclosed_or_extraction_failed"


class ESGMergePipeline:
    def __init__(self, report_dir: Path, min_route_b_confidence: float = 0.5):
        self.report_dir = Path(report_dir)
        self.min_route_b_confidence = min_route_b_confidence

    def run(self) -> Dict[str, Any]:
        print("\n----- Running ESGMergePipeline -----")
        print(f"Report dir: {self.report_dir}")

        route_a_path = self.report_dir / "standard_esg_results.csv"
        route_b_path = self.report_dir / "route_b_text_results.csv"
        route_b_quant_path = self.report_dir / "route_b_quant_results.csv"
        route_b2_path = route_b_quant_path

        route_a_validation = validate_standard_results(
            route_a_path,
            expected_rows=EXPECTED_RESULT_ROWS,
        )
        route_a_available = route_a_path.exists()
        if route_a_available and not route_a_validation["ok"]:
            raise RuntimeError(
                f"route_a 结果校验失败: {route_a_validation['reason']} "
                f"row_count={route_a_validation['row_count']} "
                f"expected_rows={route_a_validation['expected_rows']} "
                f"path={route_a_validation['path']}"
            )

        route_a_rows = load_csv(route_a_path) if route_a_available else build_empty_route_a_rows()
        route_b_rows = load_csv(route_b_path)
        route_b2_rows = load_csv(route_b2_path)

        if route_b_rows and any(parse_bool(row.get("matched")) for row in route_b_rows):
            has_validation_contract = any(
                str(row.get("route_b_validation_ok", "")).strip()
                for row in route_b_rows
            )
            if not has_validation_contract:
                raise RuntimeError(
                    "检测到旧版 Route B 结果，缺少 route_b_validation_ok；"
                    "请先重新运行 scripts.run_route_b_single，再执行 Merge。"
                )

        merged_rows = [normalize_route_a_row(row) for row in route_a_rows]
        merged_by_key = {
            row["field_key"]: row
            for row in merged_rows
            if row.get("field_key")
        }

        apply_route_b_to_merged(
            merged_by_key=merged_by_key,
            route_b_rows=route_b_rows,
            min_confidence=self.min_route_b_confidence,
        )
        apply_route_b2_to_merged(
            merged_by_key=merged_by_key,
            route_b2_rows=route_b2_rows,
        )
        budget_exhausted_keys = budget_exhausted_field_keys(route_b_rows, route_b2_rows)

        final_rows = [
            merged_by_key[row["field_key"]]
            for row in merged_rows
            if row.get("field_key") in merged_by_key
        ]
        industry = detect_industry_from_report_dir(self.report_dir)
        for row in final_rows:
            field_key = row.get("field_key", "")
            applicability = get_applicability(industry, field_key)
            row["industry"] = industry
            row["applicability"] = applicability
            apply_missing_status(
                row,
                applicability=applicability,
                industry=industry,
                budget_exhausted_keys=budget_exhausted_keys,
            )

        route_a_extracted = sum(
            1 for row in final_rows if row.get("route_a_status") == "extracted"
        )
        route_b_filled = sum(
            1 for row in final_rows if row.get("source_route") == "route_b_text_rag"
        )
        route_b_matched = sum(
            1 for row in final_rows if row.get("route_b_matched") == "true"
        )
        route_b2_filled = sum(
            1 for row in final_rows if row.get("source_route") == "route_b_quantitative_fallback"
        )
        route_b2_matched = sum(
            1 for row in final_rows if row.get("route_b2_matched") == "true"
        )
        total_extracted = sum(1 for row in final_rows if row.get("status") == "extracted")
        total_fields = len(final_rows)
        applicable_rows = [row for row in final_rows if is_applicable(industry, row.get("field_key", ""))]
        applicable_total = len(applicable_rows)
        applicable_extracted = sum(1 for row in applicable_rows if row.get("status") == "extracted")

        if total_fields != EXPECTED_RESULT_ROWS:
            raise RuntimeError(
                f"merged_esg_results 数量异常: {total_fields}，期望 {EXPECTED_RESULT_ROWS}，拒绝覆盖 merged_esg_results.csv"
            )

        summary = {
            "total_fields": total_fields,
            "route_a_available": route_a_available,
            "route_a_status": (
                "available_with_results"
                if route_a_extracted
                else ("available_empty_baseline" if route_a_available else "not_available_empty_baseline")
            ),
            "route_a_extracted_fields": route_a_extracted,
            "route_b_matched_fields": route_b_matched,
            "route_b_filled_fields": route_b_filled,
            "route_b2_matched_fields": route_b2_matched,
            "route_b2_filled_fields": route_b2_filled,
            "merged_extracted_fields": total_extracted,
            "missing_fields": total_fields - total_extracted,
            "coverage_rate": round(total_extracted / total_fields, 4) if total_fields else 0.0,
            "raw_coverage": round(total_extracted / total_fields, 4) if total_fields else 0.0,
            "industry": industry,
            "applicable_fields": applicable_total,
            "applicable_extracted_fields": applicable_extracted,
            "not_applicable_fields": total_fields - applicable_total,
            "applicable_coverage": round(applicable_extracted / applicable_total, 4) if applicable_total else 0.0,
            "route_a_path": str(route_a_path),
            "route_b_path": str(route_b_path),
            "route_b2_path": str(route_b2_path),
            "route_b_quant_path": str(route_b_quant_path),
        }

        safe_write_json(self.report_dir / "merged_esg_results.json", final_rows)
        safe_write_csv(self.report_dir / "merged_esg_results.csv", final_rows)
        safe_write_json(self.report_dir / "merge_summary.json", summary)

        print(f"[Merge] route_a_extracted={route_a_extracted}")
        print(f"[Merge] route_b_matched={route_b_matched}")
        print(f"[Merge] route_b_filled={route_b_filled}")
        print(f"[Merge] route_b2_matched={route_b2_matched}")
        print(f"[Merge] route_b2_filled={route_b2_filled}")
        print(f"[Merge] merged_extracted={total_extracted}/{total_fields}")

        return summary
