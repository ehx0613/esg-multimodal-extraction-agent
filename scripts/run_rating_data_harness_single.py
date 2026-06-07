import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.rating_data_harness import ESGRatingDataHarness


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one processed report directory through the tracked ESG rating-data harness."
    )
    parser.add_argument("report_dir", help="Path to output/reports/<report_id> directory")
    parser.add_argument("--industry", default=None, help="Optional industry key, e.g. manufacturing")
    parser.add_argument("--allow-route-b", action="store_true", help="Allow Route B planning")
    parser.add_argument("--expected-core-fields", type=int, default=None)
    parser.add_argument("--retrieval-profile", default="baseline")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = ESGRatingDataHarness(
        report_dir=args.report_dir,
        industry=args.industry,
        allow_route_b=args.allow_route_b,
        expected_core_fields=args.expected_core_fields,
        retrieval_profile=args.retrieval_profile,
    ).run()

    print(
        "tracked_harness task_id={task_id} status={status} report={report} "
        "ok={ok} review_needed={review_needed}".format(
            task_id=result["backend_task_id"],
            status=result["backend_task_status"],
            report=result.get("report_name"),
            ok=result.get("ok"),
            review_needed=result.get("review_needed"),
        )
    )


if __name__ == "__main__":
    main()
