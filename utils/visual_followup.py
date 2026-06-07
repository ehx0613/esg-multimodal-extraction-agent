import re
from typing import Any, Dict, Iterable, List


def _normalize(value: Any) -> str:
    return re.sub(r"[\s\W_]+", "", str(value or "").lower())


def _is_matched(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"true", "1", "yes", "matched"}


def build_visual_followup_queue(
    *,
    metric_plans: Iterable[Dict[str, Any]],
    evidence_records: Iterable[Dict[str, Any]],
    quantitative_results: Iterable[Dict[str, Any]],
    max_candidates_per_metric: int = 3,
    excluded_page_numbers: Iterable[int] | None = None,
    min_expected_gain: float = 15.0,
) -> List[Dict[str, Any]]:
    excluded_pages = {int(page) for page in (excluded_page_numbers or [])}
    visual_records = [
        record for record in evidence_records if record.get("evidence_type") == "visual_proxy"
    ]
    result_by_key = {
        row.get("field_key"): row for row in quantitative_results if row.get("field_key")
    }
    queue: List[Dict[str, Any]] = []

    for plan in metric_plans:
        if not plan.get("visual_fallback_required"):
            continue
        result = result_by_key.get(plan["field_key"], {})
        matched = _is_matched(result.get("matched"))
        fusion_action = str(result.get("fusion_action") or "")
        needs_visual = not matched or fusion_action in {"extract_missing", "verify_route_a"}
        if not needs_visual:
            continue

        terms = [
            plan.get("field_name_cn", ""),
            *plan.get("expected_terms", []),
            *plan.get("expected_units", []),
        ]
        normalized_terms = [_normalize(term) for term in terms if _normalize(term)]
        candidates = []
        for record in visual_records:
            page_number = record.get("page_number")
            if page_number is not None and int(page_number) in excluded_pages:
                continue
            proxy = _normalize(record.get("proxy_text") or record.get("content"))
            hits = [term for term in normalized_terms if term and term in proxy]
            if not hits:
                continue
            metadata = record.get("metadata", {})
            score = len(hits) * 10 + min(float(metadata.get("score") or 0), 100) / 10
            if score < min_expected_gain:
                continue
            candidates.append(
                {
                    "evidence_id": record.get("evidence_id"),
                    "source_region_id": record.get("source_region_id"),
                    "page_number": record.get("page_number"),
                    "score": round(score, 4),
                    "matched_terms": hits,
                }
            )
        candidates.sort(key=lambda row: row["score"], reverse=True)
        if candidates:
            queue.append(
                {
                    "field_key": plan["field_key"],
                    "reason": fusion_action or result.get("reason") or "quantitative_result_missing",
                    "candidate_visual_regions": candidates[:max_candidates_per_metric],
                }
            )
    return queue
