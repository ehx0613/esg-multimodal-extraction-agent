import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from utils.result_guard import safe_write_csv, safe_write_json
from backend.database import create_rating_record
from utils.simulated_rating import (
    SUMMARY_CSV_FIELDS,
    build_simulated_rating,
    flatten_rating_summary,
    read_json,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate project-side simulated ESG rating.")
    parser.add_argument("report_dir", help="Processed report directory containing field_citations.json.")
    parser.add_argument("--industry", default=None)
    parser.add_argument("--citations-file", default="field_citations.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report_dir = Path(args.report_dir)
    citations_path = report_dir / args.citations_file
    citation_rows = read_json(citations_path)
    if not isinstance(citation_rows, list):
        raise ValueError(f"{citations_path} must contain a JSON list.")

    result = build_simulated_rating(citation_rows, industry=args.industry)
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
        metadata={"source": "generate_simulated_rating_script"},
    )

    print(
        json.dumps(
            {
                "report_dir": str(report_dir),
                "score": result["overall"]["score"],
                "rating": result["overall"]["rating"],
                "field_count": result["overall"]["field_count"],
                "scored_field_count": result["overall"]["scored_field_count"],
                "needs_review_count": result["overall"]["needs_review_count"],
                "rating_path": str(rating_path),
                "summary_csv_path": str(summary_csv_path),
                "review_queue_path": str(review_queue_path),
                "rating_run_id": rating_record["id"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
