from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List

from config.schema import RATING_BANDS, get_mapping_for_field


SUCCESS_STATUSES = {"extracted", "matched", "present", "true", "reviewed_approved"}
MISSING_STATUSES = {"missing", "not_found", "not_applicable", "failed"}
PILLAR_WEIGHTS = {"E": 0.35, "S": 0.35, "G": 0.30}


def read_json(path: str | Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(str(value).strip().replace(",", ""))
    except Exception:
        return default


def is_successful_field(row: Dict[str, Any]) -> bool:
    status = str(row.get("status", "") or "").strip().lower()
    if status in SUCCESS_STATUSES:
        return True
    if status in MISSING_STATUSES:
        return False
    value = row.get("value")
    if isinstance(value, bool):
        return value
    return str(value or "").strip() not in {"", "None", "none", "null", "N/A", "NA", "-"}


def rating_for_score(score: float) -> str:
    for band in RATING_BANDS:
        if score >= float(band["min_score"]) and score < float(band["max_score"]):
            return str(band["rating"])
    if score >= 100:
        return "AAA"
    return "C"


def field_weight(mapping: Dict[str, Any]) -> float:
    if mapping.get("score_usage") == "display_only":
        return 0.0
    return 1.5 if mapping.get("evidence_priority") == "high" else 1.0


def field_score(row: Dict[str, Any]) -> float:
    if not is_successful_field(row):
        return 0.0

    score = 65.0
    review_status = str(row.get("citation_review_status", "") or "")
    confidence = to_float(row.get("confidence"), default=0.0)

    if review_status in {"auto_cited", "reviewed_approved"}:
        score += 25.0
    elif review_status == "needs_review":
        score += 10.0

    if confidence:
        score += min(confidence, 1.0) * 10.0
    else:
        score += 5.0

    return round(min(score, 100.0), 4)


def _weighted_average(items: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    total_weight = 0.0
    weighted_score = 0.0
    field_count = 0
    scored_count = 0
    auto_cited_count = 0
    review_count = 0

    for item in items:
        weight = float(item.get("weight", 0.0))
        if weight <= 0:
            continue
        field_count += 1
        total_weight += weight
        weighted_score += float(item.get("score", 0.0)) * weight
        if item.get("is_success"):
            scored_count += 1
        if item.get("citation_review_status") in {"auto_cited", "reviewed_approved"}:
            auto_cited_count += 1
        if item.get("citation_review_status") == "needs_review":
            review_count += 1

    score = round(weighted_score / total_weight, 4) if total_weight else 0.0
    coverage = round(scored_count / field_count, 4) if field_count else 0.0
    evidence_coverage = round(auto_cited_count / field_count, 4) if field_count else 0.0
    return {
        "score": score,
        "rating": rating_for_score(score),
        "field_count": field_count,
        "scored_field_count": scored_count,
        "coverage": coverage,
        "auto_cited_count": auto_cited_count,
        "evidence_coverage": evidence_coverage,
        "needs_review_count": review_count,
    }


def build_simulated_rating(
    citation_rows: List[Dict[str, Any]],
    *,
    industry: str | None = None,
) -> Dict[str, Any]:
    field_items: List[Dict[str, Any]] = []
    theme_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    pillar_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    review_items: List[Dict[str, Any]] = []

    for row in citation_rows:
        field_key = str(row.get("field_key", "") or "")
        mapping = get_mapping_for_field(field_key)
        if not mapping:
            continue
        industries = mapping.get("applicable_industries", [])
        if industry and "all" not in industries and industry not in industries:
            continue

        weight = field_weight(mapping)
        score = field_score(row)
        item = {
            "field_key": field_key,
            "field_name_cn": row.get("field_name_cn", ""),
            "pillar": mapping["pillar"],
            "theme_key": mapping["theme_key"],
            "theme_name_cn": mapping["theme_name_cn"],
            "key_indicator": mapping["key_indicator"],
            "indicator_name_cn": mapping["indicator_name_cn"],
            "score_usage": mapping["score_usage"],
            "evidence_priority": mapping["evidence_priority"],
            "weight": weight,
            "score": score,
            "is_success": is_successful_field(row),
            "status": row.get("status", ""),
            "value": row.get("value", ""),
            "unit": row.get("unit", ""),
            "citation_review_status": row.get("citation_review_status", ""),
            "citation_review_reasons": row.get("citation_review_reasons", []),
            "citation_page_number": row.get("citation_page_number", ""),
            "citation_chunk_id": row.get("citation_chunk_id", ""),
        }
        field_items.append(item)
        if weight > 0:
            theme_groups[mapping["theme_key"]].append(item)
            pillar_groups[mapping["pillar"]].append(item)
        if row.get("citation_review_status") == "needs_review":
            review_items.append(
                {
                    "field_key": field_key,
                    "field_name_cn": row.get("field_name_cn", ""),
                    "reason": "citation_needs_review",
                    "status": "pending",
                    "recommended_action": "人工核对候选页是否能支持该字段，必要时补录字段值。",
                    "citation_page_number": row.get("citation_page_number", ""),
                    "citation_chunk_id": row.get("citation_chunk_id", ""),
                    "citation_review_reasons": row.get("citation_review_reasons", []),
                    "text_excerpt": row.get("citation_text_excerpt", ""),
                }
            )

    theme_scores = []
    for theme_key, items in sorted(theme_groups.items()):
        mapping_sample = items[0]
        theme_scores.append(
            {
                "theme_key": theme_key,
                "theme_name_cn": mapping_sample["theme_name_cn"],
                "pillar": mapping_sample["pillar"],
                **_weighted_average(items),
            }
        )

    pillar_scores = {}
    for pillar, items in sorted(pillar_groups.items()):
        pillar_scores[pillar] = _weighted_average(items)

    total_score = 0.0
    used_weight = 0.0
    for pillar, weight in PILLAR_WEIGHTS.items():
        if pillar in pillar_scores:
            total_score += pillar_scores[pillar]["score"] * weight
            used_weight += weight
    total_score = round(total_score / used_weight, 4) if used_weight else 0.0

    return {
        "rating_model": "project_simulated_huazheng_public_v1",
        "rating_boundary": "Uses public Huazheng framework labels and project-side heuristic weights; not Huazheng's proprietary rating model.",
        "industry": industry,
        "overall": {
            "score": total_score,
            "rating": rating_for_score(total_score),
            "pillar_weights": PILLAR_WEIGHTS,
            "field_count": sum(score["field_count"] for score in pillar_scores.values()),
            "scored_field_count": sum(score["scored_field_count"] for score in pillar_scores.values()),
            "needs_review_count": len(review_items),
        },
        "pillar_scores": pillar_scores,
        "theme_scores": theme_scores,
        "field_scores": field_items,
        "human_review_queue": review_items,
    }


SUMMARY_CSV_FIELDS = [
    "level",
    "key",
    "name_cn",
    "pillar",
    "score",
    "rating",
    "field_count",
    "scored_field_count",
    "coverage",
    "evidence_coverage",
    "needs_review_count",
]


def flatten_rating_summary(result: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = [
        {
            "level": "overall",
            "key": "overall",
            "name_cn": "总分",
            "pillar": "",
            **result["overall"],
        }
    ]
    for pillar, score in result["pillar_scores"].items():
        rows.append({"level": "pillar", "key": pillar, "name_cn": pillar, "pillar": pillar, **score})
    for theme in result["theme_scores"]:
        rows.append(
            {
                "level": "theme",
                "key": theme["theme_key"],
                "name_cn": theme["theme_name_cn"],
                "pillar": theme["pillar"],
                **theme,
            }
        )
    return rows
