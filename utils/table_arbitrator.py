from pathlib import Path
import re
from typing import Any, Callable, Dict, Iterable, List

from agents.schema_match_agent import item_priority, standard_item
from utils.json_utils import load_json
from utils.schema_matcher import is_index_row, match_row_to_schema
from utils.vlm_client import extract_all_table_rows_from_image


def _page_number_from_item(item: Dict[str, Any]) -> int | None:
    try:
        value = item.get("source_page") or item.get("page_number")
        if value:
            return int(value)
    except (TypeError, ValueError):
        pass
    match = re.search(r"page_(\d+)", str(item.get("page_image") or ""))
    return int(match.group(1)) if match else None


def extract_arbitration_candidates(
    prepared_regions: Iterable[Dict[str, Any]],
    *,
    extractor: Callable[[Path], Dict[str, Any]] = extract_all_table_rows_from_image,
) -> Dict[str, Any]:
    region_results: List[Dict[str, Any]] = []
    candidates: List[Dict[str, Any]] = []

    for region in prepared_regions:
        if region.get("status") != "image_prepared" or not region.get("image_path"):
            continue
        try:
            result = extractor(Path(region["image_path"]))
        except Exception as exc:
            region_results.append(
                {
                    "source_region_id": region.get("source_region_id"),
                    "page_number": region.get("page_number"),
                    "bbox": region.get("bbox"),
                    "status": "vlm_error",
                    "error": str(exc),
                    "tables": [],
                }
            )
            continue
        result["source_region_id"] = region.get("source_region_id")
        result["page_number"] = region.get("page_number")
        result["bbox"] = region.get("bbox")
        result["quality_score"] = region.get("quality_score")
        result["arbitration_reasons"] = region.get("reasons", [])
        region_results.append(result)

        for table in result.get("tables", []) or []:
            if not isinstance(table, dict):
                continue
            title = str(table.get("table_title") or "")
            for row in table.get("rows", []) or []:
                if not isinstance(row, dict) or is_index_row(title, row):
                    continue
                mapping_row = {**row, "table_title": title}
                match = match_row_to_schema(mapping_row, allow_llm=False)
                if not match.get("matched"):
                    continue
                candidate = standard_item(row, str(region.get("image_path") or ""), title, match)
                candidate.update(
                    {
                        "source_type": "visual_arbitration",
                        "source_region_id": region.get("source_region_id"),
                        "source_page": region.get("page_number"),
                        "bbox": region.get("bbox"),
                        "arbitration_reasons": region.get("reasons", []),
                    }
                )
                candidates.append(candidate)

    return {"region_results": region_results, "candidates": candidates}


def apply_arbitration_candidates(
    standard_results: Dict[str, Dict[str, Any]],
    candidates: Iterable[Dict[str, Any]],
) -> Dict[str, Any]:
    updated = {key: dict(value) for key, value in standard_results.items()}
    applied: List[Dict[str, Any]] = []
    proposed: List[Dict[str, Any]] = []

    for candidate in candidates:
        field_key = str(candidate.get("field_key") or "")
        if not field_key or field_key not in updated:
            continue
        previous = updated[field_key]
        previous_missing = previous.get("status") != "extracted"
        same_page = _page_number_from_item(previous) == _page_number_from_item(candidate)
        conflict = "cross_source_conflict" in candidate.get("arbitration_reasons", [])
        higher_priority = item_priority(candidate) >= item_priority(previous)
        should_apply = previous_missing or (conflict and same_page and higher_priority)

        audit = {
            "field_key": field_key,
            "action": "applied" if should_apply else "proposed_review",
            "previous": previous,
            "candidate": candidate,
            "reason": (
                "visual_arbitration_filled_missing"
                if previous_missing
                else "visual_arbitration_resolved_same_page_conflict"
                if should_apply
                else "visual_arbitration_requires_review"
            ),
        }
        if should_apply:
            candidate = dict(candidate)
            candidate["arbitration_applied"] = True
            candidate["arbitration_previous_value"] = previous.get("value")
            candidate["match_reason"] = audit["reason"]
            updated[field_key] = candidate
            applied.append(audit)
        else:
            proposed.append(audit)

    return {
        "standard_results": updated,
        "applied_updates": applied,
        "proposed_updates": proposed,
    }


def load_standard_results(report_dir: Path) -> Dict[str, Dict[str, Any]]:
    path = Path(report_dir) / "standard_esg_results.json"
    if not path.exists():
        return {}
    value = load_json(path)
    return value if isinstance(value, dict) else {}
