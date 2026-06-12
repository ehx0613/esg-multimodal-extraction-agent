import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from config.schema import CORE_SCHEMA_FIELD_COUNT


PathLike = Union[str, Path]


class SupervisorAgent:
    def __init__(self, expected_core_fields: int = CORE_SCHEMA_FIELD_COUNT):
        self.expected_core_fields = expected_core_fields
        self.high_unknown_metric_threshold = 200

    def count_csv_rows(self, path: PathLike) -> int:
        csv_path = Path(path)
        if not csv_path.exists():
            return 0

        try:
            with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
                reader = csv.reader(f)
                try:
                    next(reader)
                except StopIteration:
                    return 0
                return sum(1 for _ in reader)
        except Exception:
            return 0

    def load_json_safe(self, path: PathLike) -> Optional[Any]:
        json_path = Path(path)
        if not json_path.exists():
            return None

        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def inspect_report_dir(self, report_dir: PathLike) -> Dict[str, Any]:
        report_path = Path(report_dir)

        all_table_rows_path = report_path / "all_table_rows.json"
        standard_results_path = report_path / "standard_esg_results.csv"
        unknown_metrics_path = report_path / "unknown_metrics.csv"
        route_b_results_path = report_path / "route_b_text_results.csv"
        route_b_summary_path = report_path / "route_b_summary.json"
        merged_results_path = report_path / "merged_esg_results.csv"

        route_b_summary = self.load_json_safe(route_b_summary_path)
        route_b_available = None
        route_b_matched_fields = None

        if isinstance(route_b_summary, dict):
            route_b_available = route_b_summary.get("route_b_available")
            route_b_matched_fields = route_b_summary.get("matched_fields")

        state: Dict[str, Any] = {
            "report_dir": str(report_path),
            "report_id": report_path.name,
            "report_name": report_path.name,
            "artifacts": {
                "all_table_rows_json": str(all_table_rows_path),
                "standard_results_csv": str(standard_results_path),
                "unknown_metrics_csv": str(unknown_metrics_path),
                "route_b_results_csv": str(route_b_results_path),
                "route_b_summary_json": str(route_b_summary_path),
                "merged_results_csv": str(merged_results_path),
            },
            "has_all_table_rows": all_table_rows_path.exists(),
            "has_standard_results": standard_results_path.exists(),
            "has_unknown_metrics": unknown_metrics_path.exists(),
            "has_route_b_results": route_b_results_path.exists(),
            "has_route_b_summary": route_b_summary_path.exists(),
            "has_merged_results": merged_results_path.exists(),
            "standard_row_count": self.count_csv_rows(standard_results_path),
            "merged_row_count": self.count_csv_rows(merged_results_path),
            "unknown_row_count": self.count_csv_rows(unknown_metrics_path),
            "route_b_available": route_b_available,
            "route_b_matched_fields": route_b_matched_fields,
            "needs_schema_rerun": False,
            "needs_route_b": False,
            "needs_merge": False,
            "should_skip_route_b": False,
            "route_a_status": "pending",
            "route_b_status": "pending",
            "merge_status": "pending",
            "review_needed": False,
            "review_reasons": [],
            "warnings": [],
            "suggested_actions": [],
        }

        def add_warning(value: str) -> None:
            if value not in state["warnings"]:
                state["warnings"].append(value)

        def add_action(value: str) -> None:
            if value not in state["suggested_actions"]:
                state["suggested_actions"].append(value)

        def add_review_reason(value: str) -> None:
            if value not in state["review_reasons"]:
                state["review_reasons"].append(value)
                state["review_needed"] = True

        if not state["has_all_table_rows"]:
            add_warning("route_a_cache_missing")
            add_action("run_route_a_full_pipeline")

        if not state["has_standard_results"]:
            state["needs_schema_rerun"] = True
            add_action("rerun_schema_match")
        elif state["standard_row_count"] != self.expected_core_fields:
            state["needs_schema_rerun"] = True
            add_warning("standard_row_count_invalid")
            add_action("rerun_schema_match")
            add_review_reason("standard_row_count_invalid")

        if state["has_route_b_summary"] and state["route_b_available"] is False:
            state["should_skip_route_b"] = True
            state["needs_route_b"] = False
            add_action("skip_route_b")
            add_review_reason("route_b_unavailable")

        if not state["has_route_b_results"] and not state["should_skip_route_b"]:
            state["needs_route_b"] = True
            add_action("run_route_b")

        if not state["has_merged_results"]:
            state["needs_merge"] = True
            add_action("run_merge")
        elif state["merged_row_count"] != self.expected_core_fields:
            state["needs_merge"] = True
            add_warning("merged_row_count_invalid")
            add_action("run_merge")
            add_review_reason("merged_row_count_invalid")

        standard_ok = (
            state["has_standard_results"]
            and state["standard_row_count"] == self.expected_core_fields
        )
        route_b_ok = state["has_route_b_results"] or state["should_skip_route_b"]
        merged_ok = (
            state["has_merged_results"]
            and state["merged_row_count"] == self.expected_core_fields
        )

        if standard_ok and route_b_ok and merged_ok:
            add_action("ready")

        if standard_ok:
            state["route_a_status"] = "completed"
        elif state["has_all_table_rows"]:
            state["route_a_status"] = "pending"
        else:
            state["route_a_status"] = "failed"

        if state["should_skip_route_b"]:
            state["route_b_status"] = "skipped"
        elif state["has_route_b_results"]:
            state["route_b_status"] = "completed"
        elif state["needs_route_b"]:
            state["route_b_status"] = "pending"
        else:
            state["route_b_status"] = "failed"

        if merged_ok:
            state["merge_status"] = "completed"
        elif state["needs_merge"]:
            state["merge_status"] = "pending"
        else:
            state["merge_status"] = "failed"

        return state

    def decide_next_actions(self, state: Dict[str, Any]) -> List[str]:
        actions = state.get("suggested_actions") or []
        return actions if actions else ["ready"]

    def build_human_review_queue(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        report_id = str(state.get("report_id", "unknown_report"))
        review_items: List[Dict[str, Any]] = []

        def add_item(
            reason: str,
            recommended_action: str,
            source_route: str,
            details: Optional[Dict[str, Any]] = None,
        ) -> None:
            item_id = f"{report_id}_{len(review_items) + 1:03d}"
            item: Dict[str, Any] = {
                "review_id": item_id,
                "report_id": report_id,
                "report_name": state.get("report_name"),
                "field_key": None,
                "source_route": source_route,
                "reason": reason,
                "recommended_action": recommended_action,
                "status": "pending",
            }
            if details:
                item["details"] = details
            review_items.append(item)

        if state.get("standard_row_count") != self.expected_core_fields:
            add_item(
                reason="standard_row_count_invalid",
                recommended_action="rerun_or_validate_route_a_outputs",
                source_route="route_a_appendix_table",
                details={
                    "expected_core_fields": self.expected_core_fields,
                    "actual_row_count": state.get("standard_row_count"),
                },
            )

        if state.get("merged_row_count") != self.expected_core_fields:
            add_item(
                reason="merged_row_count_invalid",
                recommended_action="rerun_or_validate_merge_outputs",
                source_route="merge",
                details={
                    "expected_core_fields": self.expected_core_fields,
                    "actual_row_count": state.get("merged_row_count"),
                },
            )

        if state.get("route_b_available") is False:
            add_item(
                reason="route_b_unavailable",
                recommended_action="confirm_no_text_layer_or_skip_route_b",
                source_route="route_b_text_rag",
                details={
                    "route_b_available": state.get("route_b_available"),
                    "has_route_b_summary": state.get("has_route_b_summary"),
                },
            )

        if state.get("unknown_row_count", 0) >= self.high_unknown_metric_threshold:
            add_item(
                reason="unknown_metric_count_high",
                recommended_action="inspect_unknown_metrics_for_schema_gaps",
                source_route="route_a_appendix_table",
                details={
                    "unknown_row_count": state.get("unknown_row_count"),
                    "threshold": self.high_unknown_metric_threshold,
                },
            )

        if not state.get("has_all_table_rows"):
            add_item(
                reason="route_a_cache_missing",
                recommended_action="rerun_full_route_a_pipeline",
                source_route="route_a_appendix_table",
                details={
                    "all_table_rows_exists": state.get("has_all_table_rows"),
                },
            )

        return review_items
