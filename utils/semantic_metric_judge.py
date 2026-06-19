from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List

from config.schema import ALL_SCHEMA, ESG_SCHEMA
from config.settings import DASHSCOPE_API_KEY, SCHEMA_JUDGE_MIN_CONFIDENCE, SCHEMA_JUDGE_MODEL, SCHEMA_JUDGE_TOP_K
from utils.b2_result_validator import validate_b2_quant_result
from utils.call_tracker import model_call_allowed, record_model_call
from utils.json_utils import extract_json_from_text
from utils.result_guard import safe_write_csv, safe_write_json


YEAR_RE = re.compile(r"20[0-3][0-9]")
PAGE_RE = re.compile(r"page[_\s-]*(\d+)", re.IGNORECASE)

SEMANTIC_JUDGE_FIELDS = [
    "candidate_id",
    "source_type",
    "field_key",
    "field_name_cn",
    "matched",
    "status",
    "value",
    "raw_value",
    "unit",
    "year",
    "confidence",
    "reason",
    "evidence",
    "source_pages",
    "judge_model",
    "b2_validation_ok",
    "b2_validation_reason",
]


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _read_csv(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    import csv

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def _compact(value: Any, limit: int = 900) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def _parse_values(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if value in (None, ""):
        return {}
    try:
        parsed = json.loads(str(value))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _choose_year_value(values: Dict[str, Any]) -> tuple[str, Any]:
    if "2024" in values:
        return "2024", values["2024"]
    for key in sorted(values.keys(), reverse=True):
        if YEAR_RE.fullmatch(str(key)):
            return str(key), values[key]
    if values:
        key = next(iter(values))
        return str(key), values[key]
    return "", ""


def _page_from_image(value: Any) -> int | str:
    text = str(value or "")
    match = PAGE_RE.search(text)
    return int(match.group(1)) if match else ""


def _source_pages_text(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, list):
        return json.dumps([item for item in value if item not in ("", None)], ensure_ascii=False)
    text = str(value).strip()
    if not text:
        return ""
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return json.dumps(parsed, ensure_ascii=False)
    except Exception:
        pass
    return text


def _candidate_from_table_row(
    row: Dict[str, Any],
    *,
    candidate_id: str,
    page_image: str = "",
    page_number: int | str = "",
    table_title: str = "",
) -> Dict[str, Any]:
    values = _parse_values(row.get("values"))
    year, value = _choose_year_value(values)
    evidence = row.get("evidence_text") or " ".join(
        str(row.get(key) or "")
        for key in ["table_title", "topic", "metric_name", "unit", "raw_value", "value"]
    )
    source_page = page_number or _page_from_image(page_image or row.get("page_image"))
    return {
        "candidate_id": candidate_id,
        "source_type": "table_row",
        "table_title": row.get("table_title") or table_title,
        "topic": row.get("topic", ""),
        "metric_name": row.get("metric_name") or row.get("row_label", ""),
        "unit": row.get("unit", ""),
        "values": values,
        "value": value,
        "raw_value": row.get("raw_value") or value,
        "year": year,
        "evidence_text": _compact(evidence),
        "page_image": row.get("page_image") or page_image,
        "source_pages": [source_page] if source_page else [],
    }


def _iter_all_table_candidates(report_dir: Path) -> Iterable[Dict[str, Any]]:
    pages = _read_json(report_dir / "all_table_rows.json", [])
    if not isinstance(pages, list):
        return
    counter = 0
    for page in pages:
        if not isinstance(page, dict):
            continue
        page_image = str(page.get("page_image", "") or "")
        page_number = page.get("page_number") or _page_from_image(page_image)
        for table in page.get("tables", []) or []:
            if not isinstance(table, dict):
                continue
            table_title = str(table.get("table_title", "") or "")
            for row in table.get("rows", []) or []:
                if not isinstance(row, dict):
                    continue
                yield _candidate_from_table_row(
                    row,
                    candidate_id=f"table_{counter}",
                    page_image=page_image,
                    page_number=page_number,
                    table_title=table_title,
                )
                counter += 1


def _iter_unknown_metric_candidates(report_dir: Path) -> Iterable[Dict[str, Any]]:
    rows = _read_json(report_dir / "unknown_metrics.json", [])
    if not isinstance(rows, list):
        return
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        candidate = _candidate_from_table_row(row, candidate_id=f"unknown_{index}")
        candidate["source_type"] = "unknown_metric"
        yield candidate


def _iter_route_b2_candidates(report_dir: Path) -> Iterable[Dict[str, Any]]:
    rows = _read_csv(report_dir / "route_b_quant_results.csv")
    for index, row in enumerate(rows):
        evidence = str(row.get("evidence", "") or "").strip()
        value = row.get("value", "")
        if not evidence and not value:
            continue
        yield {
            "candidate_id": f"route_b2_{index}",
            "source_type": "route_b2_candidate",
            "metric_name": row.get("field_name_cn") or row.get("field_key", ""),
            "topic": row.get("field_name_cn", ""),
            "unit": row.get("unit", ""),
            "value": value,
            "raw_value": row.get("raw_value") or value,
            "year": row.get("year", ""),
            "evidence_text": _compact(evidence),
            "source_pages": row.get("source_pages", ""),
            "route_b2_field_key": row.get("field_key", ""),
            "route_b2_reason": row.get("reason", ""),
        }


def _iter_route_b_text_candidates(report_dir: Path) -> Iterable[Dict[str, Any]]:
    rows = _read_csv(report_dir / "route_b_text_results.csv")
    for index, row in enumerate(rows):
        evidence = str(row.get("evidence", "") or "").strip()
        if not evidence:
            continue
        yield {
            "candidate_id": f"route_b_text_{index}",
            "source_type": "route_b_text_candidate",
            "metric_name": row.get("field_name_cn") or row.get("field_key", ""),
            "topic": row.get("summary", ""),
            "unit": "",
            "value": row.get("value", "true") or "true",
            "raw_value": row.get("value", "true") or "true",
            "year": "",
            "evidence_text": _compact(evidence),
            "source_pages": row.get("source_pages", ""),
            "route_b_field_key": row.get("field_key", ""),
            "route_b_reason": row.get("reason", ""),
        }


def build_semantic_judge_candidates(report_dir: Path) -> List[Dict[str, Any]]:
    candidates = [
        *_iter_all_table_candidates(report_dir),
        *_iter_unknown_metric_candidates(report_dir),
        *_iter_route_b2_candidates(report_dir),
        *_iter_route_b_text_candidates(report_dir),
    ]
    seen = set()
    unique = []
    for candidate in candidates:
        key = (
            candidate.get("source_type"),
            candidate.get("metric_name"),
            candidate.get("topic"),
            candidate.get("unit"),
            str(candidate.get("value")),
            candidate.get("evidence_text"),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def _candidate_to_judge_row(candidate: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "table_title": candidate.get("table_title", ""),
        "topic": candidate.get("topic", ""),
        "metric_name": candidate.get("metric_name", ""),
        "unit": candidate.get("unit", ""),
        "values": candidate.get("values") or {candidate.get("year", ""): candidate.get("value", "")},
        "evidence_text": candidate.get("evidence_text", ""),
        "row_label": candidate.get("metric_name", ""),
    }


def _norm(value: Any) -> str:
    return re.sub(r"\s+", "", str(value or "").lower())


def _candidate_text(candidate: Dict[str, Any]) -> str:
    return _norm(
        " ".join(
            str(candidate.get(key) or "")
            for key in ["table_title", "topic", "metric_name", "unit", "evidence_text", "value", "raw_value"]
        )
    )


def _schema_candidate_score(candidate: Dict[str, Any], item: Dict[str, Any]) -> float:
    text = _candidate_text(candidate)
    if not text:
        return 0.0
    phrases = [
        item.get("name_cn", ""),
        *item.get("aliases", []),
        *item.get("required_any", []),
    ]
    score = 0.0
    for phrase in phrases:
        phrase_norm = _norm(phrase)
        if phrase_norm and phrase_norm in text:
            score += 2.0 if phrase == item.get("name_cn") else 1.5
    unit = _norm(candidate.get("unit"))
    if unit and any(unit in _norm(example) or _norm(example) in unit for example in item.get("unit_examples", [])):
        score += 0.5
    return score


def select_all_schema_candidates(candidate: Dict[str, Any], top_k: int = SCHEMA_JUDGE_TOP_K) -> List[Dict[str, Any]]:
    ranked = sorted(
        (
            {**item, "candidate_score": _schema_candidate_score(candidate, item)}
            for item in ALL_SCHEMA
        ),
        key=lambda item: item["candidate_score"],
        reverse=True,
    )
    positive = [item for item in ranked if item["candidate_score"] > 0]
    return (positive or ranked)[: max(1, top_k)]


def build_semantic_judge_prompt(candidate: Dict[str, Any], schema_candidates: List[Dict[str, Any]]) -> str:
    schema_lines = []
    for item in schema_candidates:
        schema_lines.append(
            {
                "field_key": item["field_key"],
                "name_cn": item.get("name_cn", ""),
                "category": item.get("category", ""),
                "indicator_type": item.get("indicator_type", ""),
                "value_type": item.get("value_type", ""),
                "aliases": item.get("aliases", []),
                "required_any": item.get("required_any", []),
                "forbidden_any": item.get("forbidden_any", []),
                "unit_examples": item.get("unit_examples", []),
                "candidate_score": item.get("candidate_score", 0),
            }
        )
    return f"""
你是 ESG 指标语义裁判。请判断一个候选证据是否能填入给定 ESG 指标体系中的某个字段。

规则：
1. 只能从给定候选字段中选择 field_key，不能自创字段。
2. 必须根据 candidate 的表格标题、主题、行名、单位、数值和证据文本综合判断。
3. 若是定量字段，candidate 必须有明确数值；若是定性机制字段，candidate 必须能支持该机制存在。
4. 严格区分人数/比例/金额/次数/总量/强度；不确定则 matched=false。
5. evidence 必须使用 candidate 原文，不要改写或编造。
6. 只返回 JSON，不要 Markdown。

候选字段：
{json.dumps(schema_lines, ensure_ascii=False, indent=2)}

candidate:
{json.dumps(candidate, ensure_ascii=False, indent=2)}

输出格式：
{{
  "matched": true,
  "field_key": "r_and_d_expense",
  "confidence": 0.9,
  "reason": "候选行为研发总投入，单位万元，能对应研发投入金额。"
}}

或：
{{
  "matched": false,
  "field_key": null,
  "confidence": 0.2,
  "reason": "候选证据不能可靠对应任何字段。"
}}
""".strip()


def semantic_judge_candidate_to_schema(candidate: Dict[str, Any]) -> Dict[str, Any]:
    schema_candidates = select_all_schema_candidates(candidate)
    candidate_keys = [item["field_key"] for item in schema_candidates]
    if not DASHSCOPE_API_KEY:
        return {
            "matched": False,
            "field_key": None,
            "confidence": 0.0,
            "reason": "DASHSCOPE_API_KEY_empty",
            "candidate_field_keys": candidate_keys,
        }
    if not model_call_allowed("schema_judge"):
        return {
            "matched": False,
            "field_key": None,
            "confidence": 0.0,
            "reason": "model_call_budget_exhausted",
            "candidate_field_keys": candidate_keys,
        }

    from openai import OpenAI

    client = OpenAI(
        api_key=DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    prompt = build_semantic_judge_prompt(candidate, schema_candidates)
    started_at = time.time()
    try:
        response = client.chat.completions.create(
            model=SCHEMA_JUDGE_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"},
        )
        record_model_call(
            stage="schema_judge",
            model=SCHEMA_JUDGE_MODEL,
            started_at=started_at,
            response=response,
            metadata={"candidate_id": candidate.get("candidate_id"), "candidate_field_keys": candidate_keys},
        )
        data = extract_json_from_text(response.choices[0].message.content)
    except Exception as exc:
        record_model_call(
            stage="schema_judge",
            model=SCHEMA_JUDGE_MODEL,
            started_at=started_at,
            metadata={"candidate_id": candidate.get("candidate_id"), "candidate_field_keys": candidate_keys},
            error=str(exc),
        )
        return {
            "matched": False,
            "field_key": None,
            "confidence": 0.0,
            "reason": f"llm_error:{exc}",
            "candidate_field_keys": candidate_keys,
        }

    matched = bool(data.get("matched"))
    field_key = data.get("field_key")
    try:
        confidence = float(data.get("confidence", 0.0) or 0.0)
    except Exception:
        confidence = 0.0
    if not matched:
        return {
            "matched": False,
            "field_key": None,
            "confidence": confidence,
            "reason": str(data.get("reason", "") or "semantic_judge_no_match"),
            "judge_model": SCHEMA_JUDGE_MODEL,
            "candidate_field_keys": candidate_keys,
        }
    if field_key not in set(candidate_keys):
        return {
            "matched": False,
            "field_key": None,
            "confidence": confidence,
            "reason": f"semantic_judge_invalid_field_key:{field_key}",
            "judge_model": SCHEMA_JUDGE_MODEL,
            "candidate_field_keys": candidate_keys,
        }
    return {
        "matched": True,
        "field_key": field_key,
        "confidence": confidence,
        "reason": str(data.get("reason", "") or "semantic_judge_match"),
        "judge_model": SCHEMA_JUDGE_MODEL,
        "candidate_field_keys": candidate_keys,
    }


def _result_from_candidate(candidate: Dict[str, Any], judge: Dict[str, Any]) -> Dict[str, Any]:
    field_key = str(judge.get("field_key") or "")
    field_item = dict(ESG_SCHEMA.get(field_key, {}))
    field_item.setdefault("field_key", field_key)
    indicator_type = field_item.get("indicator_type", "")
    value = candidate.get("value", "")
    if indicator_type != "quantitative":
        value = True

    result = {
        "candidate_id": candidate.get("candidate_id", ""),
        "source_type": candidate.get("source_type", ""),
        "field_key": field_key,
        "field_name_cn": field_item.get("name_cn", ""),
        "matched": True,
        "status": "extracted",
        "value": value,
        "raw_value": candidate.get("raw_value", value),
        "unit": candidate.get("unit", ""),
        "year": candidate.get("year", ""),
        "confidence": judge.get("confidence", 0.0),
        "reason": judge.get("reason", ""),
        "evidence": candidate.get("evidence_text", ""),
        "source_pages": _source_pages_text(candidate.get("source_pages", [])),
        "judge_model": judge.get("judge_model", ""),
        "b2_validation_ok": True,
        "b2_validation_reason": "",
        "candidate": candidate,
        "judge": judge,
    }

    if indicator_type == "quantitative":
        validated = validate_b2_quant_result(field_item, result.copy())
        result.update(
            {
                "matched": bool(validated.get("matched")),
                "status": "extracted" if validated.get("matched") else "rejected",
                "confidence": validated.get("confidence", result["confidence"]),
                "reason": validated.get("reason", result["reason"]),
                "b2_validation_ok": bool(validated.get("b2_validation_ok")),
                "b2_validation_reason": validated.get("b2_validation_reason", ""),
            }
        )
    return result


def run_semantic_metric_judge(
    report_dir: str | Path,
    *,
    min_confidence: float = SCHEMA_JUDGE_MIN_CONFIDENCE,
) -> Dict[str, Any]:
    report_path = Path(report_dir)
    candidates = build_semantic_judge_candidates(report_path)
    safe_write_json(report_path / "semantic_judge_candidates.json", candidates)

    results = []
    for candidate in candidates:
        judge = semantic_judge_candidate_to_schema(candidate)
        if not judge.get("matched") or float(judge.get("confidence", 0.0) or 0.0) < min_confidence:
            results.append(
                {
                    "candidate_id": candidate.get("candidate_id", ""),
                    "source_type": candidate.get("source_type", ""),
                    "field_key": judge.get("field_key") or "",
                    "field_name_cn": "",
                    "matched": False,
                    "status": "rejected",
                    "value": "",
                    "raw_value": "",
                    "unit": "",
                    "year": "",
                    "confidence": judge.get("confidence", 0.0),
                    "reason": judge.get("reason", "semantic_judge_rejected"),
                    "evidence": candidate.get("evidence_text", ""),
                    "source_pages": _source_pages_text(candidate.get("source_pages", [])),
                    "judge_model": judge.get("judge_model", ""),
                    "candidate": candidate,
                    "judge": judge,
                }
            )
            continue
        results.append(_result_from_candidate(candidate, judge))

    accepted = [row for row in results if row.get("matched") and row.get("status") == "extracted"]
    safe_write_json(report_path / "semantic_judge_results.json", results)
    safe_write_csv(
        report_path / "semantic_judge_results.csv",
        results,
        preferred_order=SEMANTIC_JUDGE_FIELDS,
    )
    summary = {
        "candidate_count": len(candidates),
        "result_count": len(results),
        "accepted_count": len(accepted),
        "rejected_count": len(results) - len(accepted),
        "accepted_fields": sorted({row.get("field_key") for row in accepted if row.get("field_key")}),
        "candidates_path": str(report_path / "semantic_judge_candidates.json"),
        "results_path": str(report_path / "semantic_judge_results.json"),
        "csv_path": str(report_path / "semantic_judge_results.csv"),
    }
    safe_write_json(report_path / "semantic_judge_summary.json", summary)
    return summary
