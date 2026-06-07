import csv
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from utils.result_guard import safe_write_csv


OUTPUT_DIR = PROJECT_ROOT / "output"
REPORTS_DIR = OUTPUT_DIR / "reports"
EVAL_DIR = PROJECT_ROOT / "docs" / "eval"

GOLDEN_SET_PATH = EVAL_DIR / "golden_set.csv"
PER_REPORT_EVAL_PATH = EVAL_DIR / "per_report_eval.csv"

BATCH_SUMMARY_PATH = OUTPUT_DIR / "batch_summary.csv"
ROUTE_B_SUMMARY_PATH = OUTPUT_DIR / "route_b_batch_summary.csv"
MERGE_SUMMARY_PATH = OUTPUT_DIR / "merge_batch_summary.csv"


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_json(path: Path) -> Optional[Dict]:
    if not path.exists():
        return None

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def to_float(value, default: float = 0.0) -> float:
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except Exception:
        return default


def to_int(value, default: int = 0) -> int:
    try:
        if value is None or str(value).strip() == "":
            return default
        return int(float(value))
    except Exception:
        return default


def to_bool_str(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"

    text = str(value).strip().lower()
    return "true" if text in {"true", "1", "yes", "y", "success"} else "false"


def path_name(text: str) -> str:
    if not text:
        return ""
    return Path(text).name


def strip_prefix_index(name: str) -> str:
    parts = name.split("_", 1)
    if len(parts) == 2 and parts[0].isdigit():
        return parts[1]
    return name


def add_index_keys(index: Dict[str, Dict[str, str]], key: str, row: Dict[str, str]) -> None:
    if not key:
        return
    index[key] = row
    index[strip_prefix_index(key)] = row


def build_report_index(rows: List[Dict[str, str]], *candidate_fields: str) -> Dict[str, Dict[str, str]]:
    index: Dict[str, Dict[str, str]] = {}
    for row in rows:
        for field in candidate_fields:
            value = row.get(field, "")
            if not value:
                continue
            add_index_keys(index, path_name(value), row)
    return index


def build_existing_eval_index(rows: List[Dict[str, str]]) -> Dict[str, Dict[str, str]]:
    index: Dict[str, Dict[str, str]] = {}
    for row in rows:
        report_id = row.get("report_id", "")
        if report_id:
            add_index_keys(index, report_id, row)
    return index


def route_b_match_rate(route_b_row: Optional[Dict[str, str]]) -> str:
    if not route_b_row:
        return "0.0000"

    matched = to_int(route_b_row.get("matched_fields"))
    target = to_int(route_b_row.get("target_fields"))
    if target <= 0:
        return "0.0000"
    return f"{matched / target:.4f}"


def build_auto_note(
    route_b_available: str,
    manifest: Optional[Dict],
    route_a_cov: str,
    merged_cov: str,
) -> str:
    reasons = []

    if route_b_available == "false":
        reasons.append("Route B unavailable")

    if manifest:
        review_reasons = manifest.get("review_reasons") or []
        if review_reasons:
            reasons.append("review queue: " + ", ".join(review_reasons))

    if to_float(merged_cov) < 0.30:
        reasons.append("low merged coverage")
    elif to_float(route_a_cov) < 0.30:
        reasons.append("low Route A coverage")

    return "; ".join(reasons) if reasons else "automatic metrics populated"


def main() -> None:
    EVAL_DIR.mkdir(parents=True, exist_ok=True)

    golden_rows = read_csv(GOLDEN_SET_PATH)
    existing_eval_rows = read_csv(PER_REPORT_EVAL_PATH)
    route_a_rows = read_csv(BATCH_SUMMARY_PATH)
    route_b_rows = read_csv(ROUTE_B_SUMMARY_PATH)
    merge_rows = read_csv(MERGE_SUMMARY_PATH)

    existing_eval_index = build_existing_eval_index(existing_eval_rows)
    route_a_index = build_report_index(route_a_rows, "report_dir")
    route_b_index = build_report_index(route_b_rows, "output_dir")
    merge_index = build_report_index(merge_rows, "output_dir", "report_name")

    output_rows: List[Dict[str, str]] = []

    for golden_row in golden_rows:
        report_id = golden_row.get("report_id", "")
        existing_row = existing_eval_index.get(report_id, {})
        route_a_row = route_a_index.get(report_id, {})
        route_b_row = route_b_index.get(report_id, {})
        merge_row = merge_index.get(report_id, {})

        manifest_path = REPORTS_DIR / report_id / "run_manifest.json"
        manifest = read_json(manifest_path)

        route_a_ok = "true" if route_a_row.get("status", "").strip().lower() == "success" else existing_row.get("route_a_ok", "false")
        route_a_coverage = route_a_row.get("coverage_rate", existing_row.get("route_a_coverage", "0.0000")) or "0.0000"
        route_b_available = to_bool_str(route_b_row.get("route_b_available", existing_row.get("route_b_available", "false")))
        route_b_rate = route_b_match_rate(route_b_row)
        merged_coverage = merge_row.get("coverage_rate", existing_row.get("merged_coverage", "0.0000")) or "0.0000"

        if manifest:
            run_id = str(manifest.get("run_id", report_id))
            needs_human_review = to_bool_str(manifest.get("review_needed", False))
            review_reasons = manifest.get("review_reasons") or []
        else:
            run_id = existing_row.get("run_id", report_id)
            needs_human_review = existing_row.get("needs_human_review", "false")
            review_reasons = []

        field_precision = existing_row.get("field_precision", "")
        unknown_metric_quality = existing_row.get("unknown_metric_quality", "")
        final_grade = existing_row.get("final_grade", "") or "pending_manual_review"
        notes = existing_row.get("notes", "").strip() or build_auto_note(
            route_b_available=route_b_available,
            manifest=manifest,
            route_a_cov=route_a_coverage,
            merged_cov=merged_coverage,
        )

        if review_reasons and notes == "automatic metrics populated":
            notes = "review queue: " + ", ".join(review_reasons)

        output_rows.append(
            {
                "run_id": run_id,
                "report_id": report_id,
                "route_a_ok": route_a_ok,
                "route_a_coverage": route_a_coverage,
                "route_b_available": route_b_available,
                "route_b_match_rate": route_b_rate,
                "merged_coverage": merged_coverage,
                "field_precision": field_precision,
                "unknown_metric_quality": unknown_metric_quality,
                "needs_human_review": needs_human_review,
                "final_grade": final_grade,
                "notes": notes,
            }
        )

    safe_write_csv(
        PER_REPORT_EVAL_PATH,
        output_rows,
        preferred_order=[
            "run_id",
            "report_id",
            "route_a_ok",
            "route_a_coverage",
            "route_b_available",
            "route_b_match_rate",
            "merged_coverage",
            "field_precision",
            "unknown_metric_quality",
            "needs_human_review",
            "final_grade",
            "notes",
        ],
    )

    print(f"built_eval_rows={len(output_rows)} path={PER_REPORT_EVAL_PATH}")


if __name__ == "__main__":
    main()
