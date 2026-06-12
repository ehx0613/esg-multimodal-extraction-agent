import importlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Union

from agents.supervisor_agent import SupervisorAgent
from config.schema import CORE_SCHEMA_FIELD_COUNT
from pipeline.merge_pipeline import ESGMergePipeline
from utils.result_guard import (
    safe_write_json,
    validate_merged_results,
    validate_standard_results,
)


PathLike = Union[str, Path]


class ESGAgentHarness:
    def __init__(
        self,
        report_dir: PathLike,
        expected_core_fields: int = CORE_SCHEMA_FIELD_COUNT,
        allow_route_b: bool = False,
    ):
        self.report_dir = Path(report_dir)
        self.expected_core_fields = expected_core_fields
        self.allow_route_b = allow_route_b
        self.supervisor = SupervisorAgent(expected_core_fields=expected_core_fields)

    @property
    def report_name(self) -> str:
        return self.report_dir.name

    @property
    def all_table_rows_path(self) -> Path:
        return self.report_dir / "all_table_rows.json"

    @property
    def standard_results_path(self) -> Path:
        return self.report_dir / "standard_esg_results.csv"

    @property
    def merged_results_path(self) -> Path:
        return self.report_dir / "merged_esg_results.csv"

    @property
    def route_b_results_path(self) -> Path:
        return self.report_dir / "route_b_text_results.csv"

    @property
    def route_b_summary_path(self) -> Path:
        return self.report_dir / "route_b_summary.json"

    @property
    def manifest_path(self) -> Path:
        return self.report_dir / "run_manifest.json"

    @property
    def human_review_queue_path(self) -> Path:
        return self.report_dir / "human_review_queue.json"

    def inspect(self) -> Dict[str, Any]:
        return self.supervisor.inspect_report_dir(self.report_dir)

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")

    def _build_config_snapshot(self) -> Dict[str, Any]:
        try:
            from config.settings import LLM_MATCHER_ENABLED, TEXT_MODEL, VLM_MODEL

            return {
                "vlm_model": VLM_MODEL,
                "text_model": TEXT_MODEL,
                "llm_matcher_enabled": LLM_MATCHER_ENABLED,
                "expected_core_fields": self.expected_core_fields,
                "route_b_enabled": self.allow_route_b,
                "merge_min_route_b_confidence": 0.5,
            }
        except Exception:
            return {
                "vlm_model": os.getenv("VLM_MODEL", "qwen-vl-plus"),
                "text_model": os.getenv("TEXT_MODEL", "qwen-plus-2025-07-28"),
                "llm_matcher_enabled": os.getenv("LLM_MATCHER_ENABLED", "true").lower() == "true",
                "expected_core_fields": self.expected_core_fields,
                "route_b_enabled": self.allow_route_b,
                "merge_min_route_b_confidence": 0.5,
            }

    def _build_route_manifest(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "route_a": {
                "status": state.get("route_a_status", "pending"),
                "started_at": None,
                "finished_at": None,
                "summary": {
                    "standard_row_count": state.get("standard_row_count"),
                    "unknown_row_count": state.get("unknown_row_count"),
                },
            },
            "route_b": {
                "status": state.get("route_b_status", "pending"),
                "started_at": None,
                "finished_at": None,
                "summary": {
                    "route_b_available": state.get("route_b_available"),
                    "matched_fields": state.get("route_b_matched_fields"),
                },
            },
            "merge": {
                "status": state.get("merge_status", "pending"),
                "started_at": None,
                "finished_at": None,
                "summary": {
                    "merged_row_count": state.get("merged_row_count"),
                },
            },
        }

    def _build_manifest(self, state: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "manifest_version": "v2.0-legacy-harness",
            "run_id": f"{self.report_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "report_id": state.get("report_id", self.report_name),
            "report_name": self.report_name,
            "report_dir": str(self.report_dir),
            "output_dir": str(self.report_dir),
            "started_at": self._now_iso(),
            "finished_at": None,
            "status": "running",
            "mode": "stable_v1_1",
            "config_snapshot": self._build_config_snapshot(),
            "artifacts": {
                "all_table_rows_json": str(self.all_table_rows_path),
                "standard_results_csv": str(self.standard_results_path),
                "route_b_results_csv": str(self.route_b_results_path),
                "route_b_summary_json": str(self.route_b_summary_path),
                "merged_results_csv": str(self.merged_results_path),
                "unknown_metrics_csv": state.get("artifacts", {}).get("unknown_metrics_csv"),
            },
            "routes": self._build_route_manifest(state),
            "warnings": list(state.get("warnings", [])),
            "errors": [],
            "review_needed": bool(state.get("review_needed")),
            "review_reasons": list(state.get("review_reasons", [])),
            "human_review_queue": [],
            "next_actions": list(state.get("suggested_actions", [])),
        }

    def _save_manifest(self, manifest: Dict[str, Any]) -> None:
        safe_write_json(self.manifest_path, manifest)

    def _save_human_review_queue(self, review_items: List[Dict[str, Any]]) -> None:
        safe_write_json(self.human_review_queue_path, review_items)

    def _set_route_status(
        self,
        manifest: Dict[str, Any],
        route_name: str,
        status: str,
        summary: Dict[str, Any] | None = None,
    ) -> None:
        route = manifest.setdefault("routes", {}).setdefault(route_name, {})
        route["status"] = status
        if status == "running":
            route["started_at"] = route.get("started_at") or self._now_iso()
        elif status in {"completed", "failed", "skipped"}:
            route["finished_at"] = self._now_iso()
            if route.get("started_at") is None:
                route["started_at"] = route["finished_at"]
        if summary:
            route.setdefault("summary", {}).update(summary)

    def _finalize_manifest(
        self,
        manifest: Dict[str, Any],
        final_state: Dict[str, Any],
        errors: List[str],
        warnings: List[str],
        review_items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        review_reason_codes = sorted(
            {
                *list(final_state.get("review_reasons", [])),
                *[str(item.get("reason")) for item in review_items if item.get("reason")],
            }
        )
        manifest["finished_at"] = self._now_iso()
        manifest["status"] = "failed" if errors else "completed"
        manifest["warnings"] = warnings
        manifest["errors"] = errors
        manifest["review_needed"] = bool(review_items) or bool(final_state.get("review_needed"))
        manifest["review_reasons"] = review_reason_codes
        manifest["human_review_queue"] = review_items
        manifest["next_actions"] = list(final_state.get("suggested_actions", []))
        manifest["routes"]["route_a"]["status"] = final_state.get("route_a_status", manifest["routes"]["route_a"]["status"])
        manifest["routes"]["route_b"]["status"] = final_state.get("route_b_status", manifest["routes"]["route_b"]["status"])
        manifest["routes"]["merge"]["status"] = final_state.get("merge_status", manifest["routes"]["merge"]["status"])
        manifest["routes"]["route_a"].setdefault("summary", {}).update(
            {
                "standard_row_count": final_state.get("standard_row_count"),
                "unknown_row_count": final_state.get("unknown_row_count"),
            }
        )
        manifest["routes"]["route_b"].setdefault("summary", {}).update(
            {
                "route_b_available": final_state.get("route_b_available"),
                "matched_fields": final_state.get("route_b_matched_fields"),
            }
        )
        manifest["routes"]["merge"].setdefault("summary", {}).update(
            {
                "merged_row_count": final_state.get("merged_row_count"),
            }
        )
        return manifest

    def _build_execution_summary(
        self,
        initial_actions: List[str],
        schema_result: Dict[str, Any],
        route_b_result: Dict[str, Any],
        merge_result: Dict[str, Any],
        final_state: Dict[str, Any],
        ok: bool,
        warnings: List[str],
        review_items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        review_reason_codes = sorted(
            {
                *list(final_state.get("review_reasons", [])),
                *[str(item.get("reason")) for item in review_items if item.get("reason")],
            }
        )
        return {
            "report_dir": str(self.report_dir),
            "report_name": self.report_name,
            "initial_actions": initial_actions,
            "schema_rerun": {
                "execution_status": schema_result.get("status"),
                "final_route_status": final_state.get("route_a_status"),
                "reason": schema_result.get("reason"),
                "ok": schema_result.get("ok"),
                "validation": schema_result.get("validation"),
            },
            "route_b": {
                "execution_status": route_b_result.get("status"),
                "final_route_status": final_state.get("route_b_status"),
                "reason": route_b_result.get("reason"),
                "ok": route_b_result.get("ok"),
                "needs_route_b": route_b_result.get("needs_route_b"),
            },
            "merge": {
                "execution_status": merge_result.get("status"),
                "final_route_status": final_state.get("merge_status"),
                "reason": merge_result.get("reason"),
                "ok": merge_result.get("ok"),
                "summary": merge_result.get("summary"),
                "validation": merge_result.get("validation"),
            },
            "final_state": final_state,
            "ok": ok,
            "warnings": warnings,
            "review_needed": bool(review_items) or bool(final_state.get("review_needed")),
            "review_reason_codes": review_reason_codes,
            "review_item_count": len(review_items),
        }

    def run_schema_rerun_if_needed(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if not state.get("needs_schema_rerun"):
            return {
                "status": "skipped",
                "reason": "schema_rerun_not_needed",
                "ok": True,
            }

        if not self.all_table_rows_path.exists():
            return {
                "status": "failed",
                "reason": "route_a_cache_missing",
                "ok": False,
            }

        previous_env = os.environ.get("LLM_MATCHER_ENABLED")
        os.environ["LLM_MATCHER_ENABLED"] = "false"

        try:
            for module_name in [
                "scripts.rerun_schema_match",
                "utils.schema_matcher",
                "config.settings",
            ]:
                sys.modules.pop(module_name, None)

            rerun_module = importlib.import_module("scripts.rerun_schema_match")
            rerun_schema_match = rerun_module.rerun_schema_match

            rerun_schema_match(self.report_dir)
            validation = validate_standard_results(
                self.standard_results_path,
                expected_rows=self.expected_core_fields,
            )
        except Exception as exc:
            return {
                "status": "failed",
                "reason": "schema_rerun_exception",
                "ok": False,
                "error": str(exc),
            }
        finally:
            if previous_env is None:
                os.environ.pop("LLM_MATCHER_ENABLED", None)
            else:
                os.environ["LLM_MATCHER_ENABLED"] = previous_env

        result = {
            "status": "completed" if validation["ok"] else "failed",
            "reason": validation["reason"],
            "ok": validation["ok"],
            "validation": validation,
        }
        if not validation["ok"]:
            result["error"] = (
                "standard_esg_results_validation_failed:"
                f"{validation['reason']}:"
                f"{validation['row_count']}/{validation['expected_rows']}"
            )
        return result

    def run_route_b_if_allowed(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if not self.allow_route_b:
            return {
                "status": "skipped",
                "reason": "route_b_disabled_to_save_tokens",
                "ok": True,
            }

        return {
            "status": "pending",
            "reason": "route_b_manual_step_required",
            "ok": True,
            "needs_route_b": bool(state.get("needs_route_b")),
        }

    def run_merge_if_needed(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if not state.get("needs_merge"):
            return {
                "status": "skipped",
                "reason": "merge_not_needed",
                "ok": True,
            }

        try:
            summary = ESGMergePipeline(self.report_dir).run()
            validation = validate_merged_results(
                self.merged_results_path,
                expected_rows=self.expected_core_fields,
            )
        except Exception as exc:
            return {
                "status": "failed",
                "reason": "merge_exception",
                "ok": False,
                "error": str(exc),
            }

        result = {
            "status": "completed" if validation["ok"] else "failed",
            "reason": validation["reason"],
            "ok": validation["ok"],
            "summary": summary,
            "validation": validation,
        }
        if not validation["ok"]:
            result["error"] = (
                "merged_esg_results_validation_failed:"
                f"{validation['reason']}:"
                f"{validation['row_count']}/{validation['expected_rows']}"
            )
        return result

    def run(self) -> Dict[str, Any]:
        warnings: List[str] = []
        errors: List[str] = []

        initial_state = self.inspect()
        initial_actions = list(initial_state.get("suggested_actions", []))
        manifest = self._build_manifest(initial_state)
        self._save_manifest(manifest)

        if not self.all_table_rows_path.exists():
            warnings.append("route_a_cache_missing")

        self._set_route_status(manifest, "route_a", "running")
        self._save_manifest(manifest)
        schema_result = self.run_schema_rerun_if_needed(initial_state)
        if schema_result.get("status") == "failed":
            warnings.append(schema_result.get("reason", "schema_rerun_failed"))
            if schema_result.get("error"):
                errors.append(str(schema_result["error"]))
        self._set_route_status(
            manifest,
            "route_a",
            schema_result.get("status", "failed"),
            {
                "reason": schema_result.get("reason"),
                "validation": schema_result.get("validation"),
            },
        )
        self._save_manifest(manifest)

        post_schema_state = self.inspect()
        self._set_route_status(
            manifest,
            "route_b",
            "running" if self.allow_route_b else "skipped",
        )
        self._save_manifest(manifest)
        route_b_result = self.run_route_b_if_allowed(post_schema_state)
        self._set_route_status(
            manifest,
            "route_b",
            route_b_result.get("status", "failed"),
            {
                "reason": route_b_result.get("reason"),
                "needs_route_b": route_b_result.get("needs_route_b"),
            },
        )
        self._save_manifest(manifest)

        merge_result: Dict[str, Any]
        if schema_result.get("status") == "failed":
            merge_result = {
                "status": "skipped",
                "reason": "schema_rerun_failed",
                "ok": False,
            }
        else:
            self._set_route_status(manifest, "merge", "running")
            self._save_manifest(manifest)
            merge_result = self.run_merge_if_needed(post_schema_state)

        if merge_result.get("status") == "failed":
            warnings.append(merge_result.get("reason", "merge_failed"))
            if merge_result.get("error"):
                errors.append(str(merge_result["error"]))
        self._set_route_status(
            manifest,
            "merge",
            merge_result.get("status", "failed"),
            {
                "reason": merge_result.get("reason"),
                "summary": merge_result.get("summary"),
                "validation": merge_result.get("validation"),
            },
        )
        self._save_manifest(manifest)

        final_state = self.inspect()

        for warning in initial_state.get("warnings", []):
            if warning not in warnings:
                warnings.append(warning)
        for warning in final_state.get("warnings", []):
            if warning not in warnings:
                warnings.append(warning)

        ok = (
            final_state.get("standard_row_count") == self.expected_core_fields
            and final_state.get("merged_row_count") == self.expected_core_fields
            and not errors
        )
        review_items = self.supervisor.build_human_review_queue(final_state)
        self._save_human_review_queue(review_items)

        summary: Dict[str, Any] = self._build_execution_summary(
            initial_actions=initial_actions,
            schema_result=schema_result,
            route_b_result=route_b_result,
            merge_result=merge_result,
            final_state=final_state,
            ok=ok,
            warnings=warnings,
            review_items=review_items,
        )
        if errors:
            summary["errors"] = errors
        manifest = self._finalize_manifest(
            manifest,
            final_state,
            errors,
            warnings,
            review_items,
        )
        manifest["summary"] = summary
        self._save_manifest(manifest)
        return summary
