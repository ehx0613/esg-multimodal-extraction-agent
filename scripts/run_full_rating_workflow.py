import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.rating_data_harness import ESGRatingDataHarness
from backend.database import create_rating_record
from utils.field_citations import (
    FIELD_CITATION_CSV_FIELDS,
    attach_field_citations,
    flatten_for_csv as flatten_citations_for_csv,
    read_json as read_json_file,
)
from utils.result_guard import safe_write_csv, safe_write_json
from utils.simulated_rating import (
    SUMMARY_CSV_FIELDS,
    build_simulated_rating,
    flatten_rating_summary,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the full ESG rating-data workflow for one processed report directory."
    )
    parser.add_argument("report_dir", help="Path to output/reports/<report_id> directory.")
    parser.add_argument("--industry", default=None, help="Optional industry key, e.g. manufacturing.")
    parser.add_argument("--allow-route-b", action="store_true", help="Allow Route B planning in harness.")
    parser.add_argument("--expected-core-fields", type=int, default=None)
    parser.add_argument(
        "--retrieval-profile",
        default="bm25_query_agg_evidence_rerank_v1",
        help="Retrieval profile label stored on the task.",
    )
    parser.add_argument(
        "--skip-harness",
        action="store_true",
        help="Reuse existing merged outputs and only regenerate citations/rating artifacts.",
    )
    parser.add_argument("--top-k", type=int, default=5, help="Citation retrieval top-k.")
    return parser.parse_args()


def run_harness_step(
    report_dir: Path,
    *,
    industry: str | None,
    allow_route_b: bool,
    expected_core_fields: int | None,
    retrieval_profile: str,
) -> Dict[str, Any]:
    result = ESGRatingDataHarness(
        report_dir=report_dir,
        industry=industry,
        allow_route_b=allow_route_b,
        expected_core_fields=expected_core_fields,
        retrieval_profile=retrieval_profile,
    ).run()
    return {
        "task_id": result["backend_task_id"],
        "report_id": result["backend_report_id"],
        "status": result["backend_task_status"],
        "ok": result.get("ok"),
        "review_needed": result.get("review_needed"),
        "review_item_count": result.get("review_item_count", 0),
        "trace_url": f"/tasks/{result['backend_task_id']}/trace",
    }


def generate_citations_step(
    report_dir: Path,
    *,
    industry: str | None,
    top_k: int,
) -> Dict[str, Any]:
    merged_path = report_dir / "merged_esg_results.json"
    chunks_path = report_dir / "route_b_chunks.json"
    if not merged_path.exists():
        raise FileNotFoundError(f"Missing required file: {merged_path}")

    rows = read_json_file(merged_path)
    chunks = read_json_file(chunks_path) if chunks_path.exists() else []
    if not isinstance(rows, list):
        raise ValueError(f"{merged_path} must contain a JSON list.")
    if not isinstance(chunks, list):
        raise ValueError(f"{chunks_path} must contain a JSON list.")

    citations = attach_field_citations(rows, chunks, industry=industry, top_k=top_k)
    json_path = report_dir / "field_citations.json"
    csv_path = report_dir / "field_citations.csv"
    safe_write_json(json_path, citations)
    safe_write_csv(
        csv_path,
        flatten_citations_for_csv(citations),
        preferred_order=FIELD_CITATION_CSV_FIELDS,
    )

    needs_review_count = sum(
        1 for row in citations if row.get("citation_review_status") == "needs_review"
    )
    return {
        "field_count": len(citations),
        "auto_cited_count": len(citations) - needs_review_count,
        "needs_review_count": needs_review_count,
        "json_path": str(json_path),
        "csv_path": str(csv_path),
    }


def generate_rating_step(report_dir: Path, *, industry: str | None) -> Dict[str, Any]:
    citations_path = report_dir / "field_citations.json"
    citation_rows = read_json_file(citations_path)
    if not isinstance(citation_rows, list):
        raise ValueError(f"{citations_path} must contain a JSON list.")

    result = build_simulated_rating(citation_rows, industry=industry)
    rating_path = report_dir / "simulated_rating.json"
    summary_csv_path = report_dir / "simulated_rating_summary.csv"
    review_queue_path = report_dir / "rating_review_queue.json"
    safe_write_json(rating_path, result)
    safe_write_csv(
        summary_csv_path,
        flatten_rating_summary(result),
        preferred_order=SUMMARY_CSV_FIELDS,
    )
    safe_write_json(review_queue_path, result["human_review_queue"])
    rating_record = create_rating_record(
        rating_result=result,
        report_dir=str(report_dir),
        metadata={"source": "run_full_rating_workflow"},
    )

    return {
        "score": result["overall"]["score"],
        "rating": result["overall"]["rating"],
        "field_count": result["overall"]["field_count"],
        "scored_field_count": result["overall"]["scored_field_count"],
        "needs_review_count": result["overall"]["needs_review_count"],
        "json_path": str(rating_path),
        "summary_csv_path": str(summary_csv_path),
        "review_queue_path": str(review_queue_path),
        "rating_run_id": rating_record["id"],
        "pillar_scores": result["pillar_scores"],
    }


def run_workflow(
    report_dir: Path,
    *,
    industry: str | None = None,
    allow_route_b: bool = False,
    expected_core_fields: int | None = None,
    retrieval_profile: str = "bm25_query_agg_evidence_rerank_v1",
    skip_harness: bool = False,
    top_k: int = 5,
) -> Dict[str, Any]:
    if not report_dir.exists() or not report_dir.is_dir():
        raise FileNotFoundError(f"Report directory not found: {report_dir}")

    harness_summary = None
    if not skip_harness:
        harness_summary = run_harness_step(
            report_dir,
            industry=industry,
            allow_route_b=allow_route_b,
            expected_core_fields=expected_core_fields,
            retrieval_profile=retrieval_profile,
        )

    citations_summary = generate_citations_step(report_dir, industry=industry, top_k=top_k)
    rating_summary = generate_rating_step(report_dir, industry=industry)
    workflow_summary = {
        "report_dir": str(report_dir),
        "industry": industry,
        "retrieval_profile": retrieval_profile,
        "skip_harness": skip_harness,
        "harness": harness_summary,
        "citations": citations_summary,
        "rating": rating_summary,
        "next_step": "Review rating_review_queue.json, then approve/correct fields and recalculate rating.",
    }
    safe_write_json(report_dir / "full_rating_workflow_summary.json", workflow_summary)
    return workflow_summary


def main() -> None:
    args = parse_args()
    summary = run_workflow(
        Path(args.report_dir),
        industry=args.industry,
        allow_route_b=args.allow_route_b,
        expected_core_fields=args.expected_core_fields,
        retrieval_profile=args.retrieval_profile,
        skip_harness=args.skip_harness,
        top_k=args.top_k,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
