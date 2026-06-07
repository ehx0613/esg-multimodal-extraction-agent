import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from utils.field_citations import (
    FIELD_CITATION_CSV_FIELDS,
    attach_field_citations,
    flatten_for_csv,
    read_json,
)
from utils.result_guard import safe_write_csv, safe_write_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Attach field-level citations to merged ESG results.")
    parser.add_argument("report_dir", help="Processed report directory.")
    parser.add_argument("--industry", default=None)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--results-file", default="merged_esg_results.json")
    parser.add_argument("--chunks-file", default="route_b_chunks.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report_dir = Path(args.report_dir)
    results_path = report_dir / args.results_file
    chunks_path = report_dir / args.chunks_file

    rows = read_json(results_path)
    chunks = read_json(chunks_path) if chunks_path.exists() else []
    if not isinstance(rows, list):
        raise ValueError(f"{results_path} must contain a JSON list.")
    if not isinstance(chunks, list):
        raise ValueError(f"{chunks_path} must contain a JSON list.")

    enriched = attach_field_citations(
        rows,
        chunks,
        industry=args.industry,
        top_k=args.top_k,
    )
    json_path = report_dir / "field_citations.json"
    csv_path = report_dir / "field_citations.csv"
    safe_write_json(json_path, enriched)
    safe_write_csv(csv_path, flatten_for_csv(enriched), preferred_order=FIELD_CITATION_CSV_FIELDS)

    review_count = sum(1 for row in enriched if row.get("citation_review_status") == "needs_review")
    summary = {
        "report_dir": str(report_dir),
        "field_count": len(enriched),
        "auto_cited_count": len(enriched) - review_count,
        "needs_review_count": review_count,
        "json_path": str(json_path),
        "csv_path": str(csv_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
