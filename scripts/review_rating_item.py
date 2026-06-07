import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from utils.rating_review import apply_review_decision
from backend.database import create_rating_record
from utils.simulated_rating import read_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply a human review decision to one rating field.")
    parser.add_argument("report_dir")
    parser.add_argument("--field-key", required=True)
    parser.add_argument("--action", required=True, choices=["approve", "reject", "correct"])
    parser.add_argument("--industry", default=None)
    parser.add_argument("--reviewer", default=None)
    parser.add_argument("--notes", default=None)
    parser.add_argument("--value", default=None)
    parser.add_argument("--unit", default=None)
    parser.add_argument("--year", default=None)
    parser.add_argument("--evidence", default=None)
    parser.add_argument("--page-number", type=int, default=None)
    parser.add_argument("--chunk-id", default=None)
    parser.add_argument(
        "--correction-json",
        default=None,
        help="Optional JSON object with additional correction fields.",
    )
    return parser.parse_args()


def build_correction(args: argparse.Namespace) -> dict:
    correction = {}
    for arg_name, field_name in [
        ("value", "value"),
        ("unit", "unit"),
        ("year", "year"),
        ("evidence", "evidence"),
        ("page_number", "citation_page_number"),
        ("chunk_id", "citation_chunk_id"),
    ]:
        value = getattr(args, arg_name)
        if value is not None:
            correction[field_name] = value
    if args.correction_json:
        extra = json.loads(args.correction_json)
        if not isinstance(extra, dict):
            raise ValueError("--correction-json must be a JSON object.")
        correction.update(extra)
    return correction


def main() -> None:
    args = parse_args()
    result = apply_review_decision(
        args.report_dir,
        field_key=args.field_key,
        action=args.action,
        industry=args.industry,
        reviewer=args.reviewer,
        notes=args.notes,
        correction=build_correction(args),
    )
    rating_record = create_rating_record(
        rating_result=read_json(Path(args.report_dir) / "simulated_rating.json"),
        report_dir=str(Path(args.report_dir)),
        metadata={
            "source": "review_rating_item_script",
            "field_key": args.field_key,
            "action": args.action,
        },
    )
    result["rating"]["rating_run_id"] = rating_record["id"]
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
