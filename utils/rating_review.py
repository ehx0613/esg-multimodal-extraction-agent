from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from utils.result_guard import safe_write_csv, safe_write_json
from utils.simulated_rating import (
    SUMMARY_CSV_FIELDS,
    build_simulated_rating,
    flatten_rating_summary,
    read_json,
)


VALID_REVIEW_ACTIONS = {"approve", "reject", "correct"}
CORRECTABLE_FIELDS = {
    "status",
    "value",
    "raw_value",
    "standardized_value",
    "unit",
    "year",
    "confidence",
    "evidence",
    "citation_evidence_text",
    "citation_page_number",
    "citation_chunk_id",
    "citation_text_excerpt",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_json_list(path: Path) -> List[Dict[str, Any]]:
    data = read_json(path)
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON list.")
    return [item for item in data if isinstance(item, dict)]


def find_field_row(rows: List[Dict[str, Any]], field_key: str) -> Dict[str, Any] | None:
    for row in rows:
        if row.get("field_key") == field_key:
            return row
    return None


def apply_correction(row: Dict[str, Any], correction: Dict[str, Any]) -> None:
    for key, value in correction.items():
        if key in CORRECTABLE_FIELDS:
            row[key] = value
    if "evidence" in correction and "citation_evidence_text" not in correction:
        row["citation_evidence_text"] = correction["evidence"]


def append_review_history(
    report_dir: Path,
    *,
    field_key: str,
    action: str,
    reviewer: str | None,
    notes: str | None,
    correction: Dict[str, Any],
) -> List[Dict[str, Any]]:
    history_path = report_dir / "rating_review_history.json"
    if history_path.exists():
        history = load_json_list(history_path)
    else:
        history = []
    history.append(
        {
            "field_key": field_key,
            "action": action,
            "reviewer": reviewer,
            "notes": notes,
            "correction": correction,
            "reviewed_at": now_iso(),
        }
    )
    safe_write_json(history_path, history)
    return history


def recalculate_rating(report_dir: Path, *, industry: str | None = None) -> Dict[str, Any]:
    citations_path = report_dir / "field_citations.json"
    citation_rows = load_json_list(citations_path)
    rating = build_simulated_rating(citation_rows, industry=industry)

    safe_write_json(report_dir / "simulated_rating.json", rating)
    safe_write_csv(
        report_dir / "simulated_rating_summary.csv",
        flatten_rating_summary(rating),
        preferred_order=SUMMARY_CSV_FIELDS,
    )
    safe_write_json(report_dir / "rating_review_queue.json", rating["human_review_queue"])
    return rating


def apply_review_decision(
    report_dir: str | Path,
    *,
    field_key: str,
    action: str,
    industry: str | None = None,
    reviewer: str | None = None,
    notes: str | None = None,
    correction: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    report_path = Path(report_dir)
    if action not in VALID_REVIEW_ACTIONS:
        raise ValueError(f"action must be one of {sorted(VALID_REVIEW_ACTIONS)}")

    citations_path = report_path / "field_citations.json"
    rows = load_json_list(citations_path)
    row = find_field_row(rows, field_key)
    if row is None:
        raise KeyError(f"field not found: {field_key}")

    correction = correction or {}
    before_status = row.get("citation_review_status")
    apply_correction(row, correction)

    if action == "approve":
        row["citation_review_status"] = "reviewed_approved"
        row["citation_review_reasons"] = []
    elif action == "reject":
        row["citation_review_status"] = "reviewed_rejected"
        row["citation_review_reasons"] = ["human_rejected"]
        if not correction.get("status"):
            row["status"] = "missing"
    elif action == "correct":
        row["citation_review_status"] = "reviewed_approved"
        row["citation_review_reasons"] = []
        row.setdefault("status", "extracted")
        if str(row.get("status", "")).lower() in {"missing", ""}:
            row["status"] = "extracted"

    row["human_review"] = {
        "action": action,
        "reviewer": reviewer,
        "notes": notes,
        "before_citation_review_status": before_status,
        "reviewed_at": now_iso(),
    }
    safe_write_json(citations_path, rows)
    history = append_review_history(
        report_path,
        field_key=field_key,
        action=action,
        reviewer=reviewer,
        notes=notes,
        correction=correction,
    )
    rating = recalculate_rating(report_path, industry=industry)

    return {
        "field_key": field_key,
        "action": action,
        "updated_field": row,
        "history_count": len(history),
        "rating": {
            "score": rating["overall"]["score"],
            "rating": rating["overall"]["rating"],
            "needs_review_count": rating["overall"]["needs_review_count"],
        },
        "paths": {
            "field_citations": str(citations_path),
            "simulated_rating": str(report_path / "simulated_rating.json"),
            "rating_review_queue": str(report_path / "rating_review_queue.json"),
            "rating_review_history": str(report_path / "rating_review_history.json"),
        },
    }


def load_review_queue(report_dir: str | Path) -> List[Dict[str, Any]]:
    path = Path(report_dir) / "rating_review_queue.json"
    if not path.exists():
        return []
    return load_json_list(path)
