import sys
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.agent_harness import ESGAgentHarness
from utils.result_guard import safe_write_csv, safe_write_json


from config.schema import CORE_SCHEMA_FIELD_COUNT

EXPECTED_ROWS = CORE_SCHEMA_FIELD_COUNT


def collect_report_dirs(reports_root: Path) -> List[Path]:
    if not reports_root.exists():
        return []

    return sorted(path for path in reports_root.iterdir() if path.is_dir())


def serialize_list(values: List[str]) -> str:
    return " | ".join(str(value) for value in values if str(value))


def build_csv_row(summary: Dict[str, Any]) -> Dict[str, Any]:
    final_state = summary.get("final_state", {})
    suggested_actions = final_state.get("suggested_actions", [])

    return {
        "report_name": summary.get("report_name", ""),
        "ok": summary.get("ok", False),
        "schema_rerun_status": summary.get("schema_rerun", {}).get("status", ""),
        "route_b_status": summary.get("route_b", {}).get("status", ""),
        "merge_status": summary.get("merge", {}).get("status", ""),
        "standard_row_count": final_state.get("standard_row_count", 0),
        "merged_row_count": final_state.get("merged_row_count", 0),
        "suggested_actions": serialize_list(suggested_actions),
        "warnings": serialize_list(summary.get("warnings", [])),
    }


def build_json_payload(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "rows": rows,
        "summary": {
            "total_reports": len(rows),
            "ok_count": sum(1 for row in rows if row.get("ok")),
            "schema_rerun_completed_count": sum(
                1 for row in rows if row.get("schema_rerun", {}).get("status") == "completed"
            ),
            "merge_completed_count": sum(
                1 for row in rows if row.get("merge", {}).get("status") == "completed"
            ),
            "warning_count": sum(1 for row in rows if row.get("warnings")),
        },
    }


def main() -> None:
    reports_root = PROJECT_ROOT / "output" / "reports"
    output_csv = PROJECT_ROOT / "docs" / "v1_results" / "agent_harness_summary.csv"
    output_json = PROJECT_ROOT / "docs" / "v1_results" / "agent_harness_summary.json"

    report_dirs = collect_report_dirs(reports_root)
    rows: List[Dict[str, Any]] = []

    for idx, report_dir in enumerate(report_dirs, start=1):
        print("\n" + "=" * 100)
        print(f"[{idx}/{len(report_dirs)}] AgentHarness: {report_dir.name}")
        print("=" * 100)

        summary = ESGAgentHarness(
            report_dir=report_dir,
            expected_core_fields=EXPECTED_ROWS,
            allow_route_b=False,
        ).run()
        rows.append(summary)

        final_state = summary.get("final_state", {})
        print(
            "report_name={report_name} ok={ok} schema_rerun={schema_status} "
            "route_b={route_b_status} merge={merge_status} "
            "standard_row_count={standard_row_count} merged_row_count={merged_row_count} "
            "warnings={warnings}".format(
                report_name=summary.get("report_name"),
                ok=summary.get("ok"),
                schema_status=summary.get("schema_rerun", {}).get("status"),
                route_b_status=summary.get("route_b", {}).get("status"),
                merge_status=summary.get("merge", {}).get("status"),
                standard_row_count=final_state.get("standard_row_count"),
                merged_row_count=final_state.get("merged_row_count"),
                warnings=serialize_list(summary.get("warnings", [])),
            )
        )

    csv_rows = [build_csv_row(row) for row in rows]
    json_payload = build_json_payload(rows)

    safe_write_csv(
        output_csv,
        csv_rows,
        preferred_order=[
            "report_name",
            "ok",
            "schema_rerun_status",
            "route_b_status",
            "merge_status",
            "standard_row_count",
            "merged_row_count",
            "suggested_actions",
            "warnings",
        ],
    )
    safe_write_json(output_json, json_payload)

    print(f"\nAgent harness summary saved: {output_csv}")
    print(f"Agent harness summary saved: {output_json}")


if __name__ == "__main__":
    main()
