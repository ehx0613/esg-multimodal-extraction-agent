import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_full_rating_workflow import run_workflow
from utils.result_guard import safe_write_csv, safe_write_json


BATCH_SUMMARY_FIELDS = [
    "report_name",
    "success",
    "industry",
    "skip_harness",
    "task_id",
    "task_status",
    "citation_field_count",
    "auto_cited_count",
    "citation_needs_review_count",
    "rating_score",
    "rating",
    "rating_field_count",
    "scored_field_count",
    "rating_needs_review_count",
    "e_score",
    "e_rating",
    "s_score",
    "s_rating",
    "g_score",
    "g_rating",
    "rating_run_id",
    "summary_path",
    "report_dir",
    "error",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the full ESG rating workflow for multiple processed report directories."
    )
    parser.add_argument(
        "--reports-root",
        default=str(PROJECT_ROOT / "output" / "reports"),
        help="Directory containing processed report folders.",
    )
    parser.add_argument("--industry", default=None, help="Optional industry key applied to all reports.")
    parser.add_argument("--allow-route-b", action="store_true")
    parser.add_argument("--expected-core-fields", type=int, default=None)
    parser.add_argument(
        "--retrieval-profile",
        default="bm25_query_agg_evidence_rerank_v1",
    )
    parser.add_argument("--skip-harness", action="store_true")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--limit", type=int, default=None, help="Optional max number of reports to process.")
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on the first report error instead of continuing.",
    )
    parser.add_argument(
        "--output-csv",
        default=str(PROJECT_ROOT / "output" / "full_rating_workflow_batch_summary.csv"),
    )
    parser.add_argument(
        "--output-json",
        default=str(PROJECT_ROOT / "output" / "full_rating_workflow_batch_summary.json"),
    )
    return parser.parse_args()


def collect_report_dirs(reports_root: Path) -> List[Path]:
    if not reports_root.exists():
        return []
    return sorted(
        path
        for path in reports_root.iterdir()
        if path.is_dir() and (path / "merged_esg_results.json").exists()
    )


def pillar_value(rating_summary: Dict[str, Any], pillar: str, key: str) -> Any:
    pillar_scores = rating_summary.get("pillar_scores") or {}
    return (pillar_scores.get(pillar) or {}).get(key, "")


def build_success_row(
    report_dir: Path,
    summary: Dict[str, Any],
    *,
    industry: str | None,
    skip_harness: bool,
) -> Dict[str, Any]:
    harness = summary.get("harness") or {}
    citations = summary.get("citations") or {}
    rating = summary.get("rating") or {}
    return {
        "report_name": report_dir.name,
        "success": True,
        "industry": industry or "",
        "skip_harness": skip_harness,
        "task_id": harness.get("task_id", ""),
        "task_status": harness.get("status", ""),
        "citation_field_count": citations.get("field_count", ""),
        "auto_cited_count": citations.get("auto_cited_count", ""),
        "citation_needs_review_count": citations.get("needs_review_count", ""),
        "rating_score": rating.get("score", ""),
        "rating": rating.get("rating", ""),
        "rating_field_count": rating.get("field_count", ""),
        "scored_field_count": rating.get("scored_field_count", ""),
        "rating_needs_review_count": rating.get("needs_review_count", ""),
        "e_score": pillar_value(rating, "E", "score"),
        "e_rating": pillar_value(rating, "E", "rating"),
        "s_score": pillar_value(rating, "S", "score"),
        "s_rating": pillar_value(rating, "S", "rating"),
        "g_score": pillar_value(rating, "G", "score"),
        "g_rating": pillar_value(rating, "G", "rating"),
        "rating_run_id": rating.get("rating_run_id", ""),
        "summary_path": str(report_dir / "full_rating_workflow_summary.json"),
        "report_dir": str(report_dir),
        "error": "",
    }


def build_error_row(
    report_dir: Path,
    error: Exception,
    *,
    industry: str | None,
    skip_harness: bool,
) -> Dict[str, Any]:
    return {
        "report_name": report_dir.name,
        "success": False,
        "industry": industry or "",
        "skip_harness": skip_harness,
        "task_id": "",
        "task_status": "",
        "citation_field_count": "",
        "auto_cited_count": "",
        "citation_needs_review_count": "",
        "rating_score": "",
        "rating": "",
        "rating_field_count": "",
        "scored_field_count": "",
        "rating_needs_review_count": "",
        "e_score": "",
        "e_rating": "",
        "s_score": "",
        "s_rating": "",
        "g_score": "",
        "g_rating": "",
        "rating_run_id": "",
        "summary_path": "",
        "report_dir": str(report_dir),
        "error": str(error),
    }


def build_batch_payload(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    success_rows = [row for row in rows if row.get("success")]
    return {
        "rows": rows,
        "summary": {
            "total_reports": len(rows),
            "success_count": len(success_rows),
            "failed_count": len(rows) - len(success_rows),
            "avg_rating_score": round(
                sum(float(row["rating_score"]) for row in success_rows if row.get("rating_score"))
                / max(sum(1 for row in success_rows if row.get("rating_score")), 1),
                4,
            ),
            "total_needs_review_count": sum(
                int(row.get("rating_needs_review_count") or 0) for row in success_rows
            ),
        },
    }


def run_batch(
    *,
    reports_root: Path,
    industry: str | None = None,
    allow_route_b: bool = False,
    expected_core_fields: int | None = None,
    retrieval_profile: str = "bm25_query_agg_evidence_rerank_v1",
    skip_harness: bool = False,
    top_k: int = 5,
    limit: int | None = None,
    fail_fast: bool = False,
    output_csv: Path | None = None,
    output_json: Path | None = None,
) -> Dict[str, Any]:
    report_dirs = collect_report_dirs(reports_root)
    if limit is not None:
        report_dirs = report_dirs[:limit]
    if not report_dirs:
        raise FileNotFoundError(f"No report directories with merged_esg_results.json under {reports_root}")

    rows: List[Dict[str, Any]] = []
    for idx, report_dir in enumerate(report_dirs, start=1):
        print("\n" + "=" * 100)
        print(f"[{idx}/{len(report_dirs)}] FullRatingWorkflow: {report_dir.name}")
        print("=" * 100)
        try:
            summary = run_workflow(
                report_dir,
                industry=industry,
                allow_route_b=allow_route_b,
                expected_core_fields=expected_core_fields,
                retrieval_profile=retrieval_profile,
                skip_harness=skip_harness,
                top_k=top_k,
            )
            row = build_success_row(
                report_dir,
                summary,
                industry=industry,
                skip_harness=skip_harness,
            )
            rows.append(row)
            print(
                "score={score} rating={rating} needs_review={needs_review}".format(
                    score=row["rating_score"],
                    rating=row["rating"],
                    needs_review=row["rating_needs_review_count"],
                )
            )
        except Exception as exc:
            row = build_error_row(report_dir, exc, industry=industry, skip_harness=skip_harness)
            rows.append(row)
            print(f"ERROR: {exc}")
            if fail_fast:
                raise

    payload = build_batch_payload(rows)
    output_csv = output_csv or (PROJECT_ROOT / "output" / "full_rating_workflow_batch_summary.csv")
    output_json = output_json or (PROJECT_ROOT / "output" / "full_rating_workflow_batch_summary.json")
    safe_write_csv(output_csv, rows, preferred_order=BATCH_SUMMARY_FIELDS)
    safe_write_json(output_json, payload)

    print(f"\nBatch summary saved: {output_csv}")
    print(f"Batch summary saved: {output_json}")
    return payload


def main() -> None:
    args = parse_args()
    payload = run_batch(
        reports_root=Path(args.reports_root),
        industry=args.industry,
        allow_route_b=args.allow_route_b,
        expected_core_fields=args.expected_core_fields,
        retrieval_profile=args.retrieval_profile,
        skip_harness=args.skip_harness,
        top_k=args.top_k,
        limit=args.limit,
        fail_fast=args.fail_fast,
        output_csv=Path(args.output_csv),
        output_json=Path(args.output_json),
    )
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
