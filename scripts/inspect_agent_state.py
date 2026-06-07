import sys
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from agents.supervisor_agent import SupervisorAgent
from utils.result_guard import safe_write_csv, safe_write_json


EXPECTED_ROWS = 68


def collect_report_dirs(reports_root: Path) -> List[Path]:
    if not reports_root.exists():
        return []

    return sorted(path for path in reports_root.iterdir() if path.is_dir())


def serialize_list(values: List[str]) -> str:
    return " | ".join(values)


def build_csv_row(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "report_name": state["report_name"],
        "standard_row_count": state["standard_row_count"],
        "merged_row_count": state["merged_row_count"],
        "unknown_row_count": state["unknown_row_count"],
        "route_b_available": state["route_b_available"],
        "route_b_matched_fields": state["route_b_matched_fields"],
        "needs_schema_rerun": state["needs_schema_rerun"],
        "needs_route_b": state["needs_route_b"],
        "needs_merge": state["needs_merge"],
        "should_skip_route_b": state["should_skip_route_b"],
        "suggested_actions": serialize_list(state["suggested_actions"]),
        "warnings": serialize_list(state["warnings"]),
    }


def build_summary(states: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "total_reports": len(states),
        "ready_count": sum(
            1 for state in states if "ready" in state.get("suggested_actions", [])
        ),
        "needs_schema_rerun_count": sum(
            1 for state in states if state.get("needs_schema_rerun")
        ),
        "needs_route_b_count": sum(1 for state in states if state.get("needs_route_b")),
        "needs_merge_count": sum(1 for state in states if state.get("needs_merge")),
        "warning_count": sum(1 for state in states if state.get("warnings")),
    }


def main() -> None:
    reports_root = PROJECT_ROOT / "output" / "reports"
    output_csv = PROJECT_ROOT / "docs" / "v1_results" / "supervisor_state_check.csv"
    output_json = PROJECT_ROOT / "docs" / "v1_results" / "supervisor_state_check.json"

    supervisor = SupervisorAgent(expected_core_fields=EXPECTED_ROWS)
    report_dirs = collect_report_dirs(reports_root)
    states = [supervisor.inspect_report_dir(report_dir) for report_dir in report_dirs]
    rows = [build_csv_row(state) for state in states]
    summary = build_summary(states)

    safe_write_csv(
        output_csv,
        rows,
        preferred_order=[
            "report_name",
            "standard_row_count",
            "merged_row_count",
            "unknown_row_count",
            "route_b_available",
            "route_b_matched_fields",
            "needs_schema_rerun",
            "needs_route_b",
            "needs_merge",
            "should_skip_route_b",
            "suggested_actions",
            "warnings",
        ],
    )
    safe_write_json(
        output_json,
        {
            "rows": states,
            "summary": summary,
        },
    )

    for state in states:
        print(
            "report_name={report_name} standard_row_count={standard_row_count} "
            "merged_row_count={merged_row_count} route_b_available={route_b_available} "
            "suggested_actions={suggested_actions} warnings={warnings}".format(
                report_name=state["report_name"],
                standard_row_count=state["standard_row_count"],
                merged_row_count=state["merged_row_count"],
                route_b_available=state["route_b_available"],
                suggested_actions=serialize_list(state["suggested_actions"]),
                warnings=serialize_list(state["warnings"]),
            )
        )

    print(
        "summary total_reports={total_reports} ready_count={ready_count} "
        "needs_schema_rerun_count={needs_schema_rerun_count} "
        "needs_route_b_count={needs_route_b_count} needs_merge_count={needs_merge_count} "
        "warning_count={warning_count}".format(**summary)
    )


if __name__ == "__main__":
    main()
