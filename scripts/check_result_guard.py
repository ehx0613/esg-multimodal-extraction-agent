import sys
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from utils.result_guard import (
    DEFAULT_EXPECTED_ROWS,
    safe_write_csv,
    safe_write_json,
    validate_merged_results,
    validate_standard_results,
)


EXPECTED_ROWS = DEFAULT_EXPECTED_ROWS


def build_warning_messages(
    standard_result: Dict[str, Any],
    merged_result: Dict[str, Any],
) -> List[str]:
    warnings = []

    if not standard_result["ok"]:
        warnings.append(
            f"standard_esg_results:{standard_result['reason']}:{standard_result['row_count']}"
        )

    if not merged_result["ok"]:
        warnings.append(
            f"merged_esg_results:{merged_result['reason']}:{merged_result['row_count']}"
        )

    return warnings


def check_report_dir(report_dir: Path) -> Dict[str, Any]:
    standard_path = report_dir / "standard_esg_results.csv"
    merged_path = report_dir / "merged_esg_results.csv"

    standard_result = validate_standard_results(standard_path, expected_rows=EXPECTED_ROWS)
    merged_result = validate_merged_results(merged_path, expected_rows=EXPECTED_ROWS)
    warnings = build_warning_messages(standard_result, merged_result)

    return {
        "report_name": report_dir.name,
        "standard_ok": standard_result["ok"],
        "standard_row_count": standard_result["row_count"],
        "merged_ok": merged_result["ok"],
        "merged_row_count": merged_result["row_count"],
        "warnings": " | ".join(warnings),
    }


def collect_report_dirs(reports_root: Path) -> List[Path]:
    if not reports_root.exists():
        return []

    return sorted(path for path in reports_root.iterdir() if path.is_dir())


def build_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    failed_reports = [
        row["report_name"]
        for row in rows
        if not row["standard_ok"] or not row["merged_ok"]
    ]

    return {
        "total_reports": len(rows),
        "standard_ok_count": sum(1 for row in rows if row["standard_ok"]),
        "merged_ok_count": sum(1 for row in rows if row["merged_ok"]),
        "failed_reports": failed_reports,
    }


def main() -> None:
    reports_root = PROJECT_ROOT / "output" / "reports"
    output_csv = PROJECT_ROOT / "docs" / "v1_results" / "result_guard_check.csv"
    output_json = PROJECT_ROOT / "docs" / "v1_results" / "result_guard_check.json"

    report_dirs = collect_report_dirs(reports_root)
    rows = [check_report_dir(report_dir) for report_dir in report_dirs]
    summary = build_summary(rows)

    safe_write_csv(
        output_csv,
        rows,
        preferred_order=[
            "report_name",
            "standard_ok",
            "standard_row_count",
            "merged_ok",
            "merged_row_count",
            "warnings",
        ],
    )
    safe_write_json(
        output_json,
        {
            "rows": rows,
            "summary": summary,
        },
    )

    for row in rows:
        print(
            "report_name={report_name} standard_ok={standard_ok} "
            "standard_row_count={standard_row_count} merged_ok={merged_ok} "
            "merged_row_count={merged_row_count} warnings={warnings}".format(**row)
        )

    print(
        "summary total_reports={total_reports} standard_ok_count={standard_ok_count} "
        "merged_ok_count={merged_ok_count} failed_reports={failed_reports}".format(
            **summary
        )
    )


if __name__ == "__main__":
    main()
