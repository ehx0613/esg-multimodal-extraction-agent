from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from backend.database import (
    create_report,
    create_review_item,
    create_task,
    finish_agent_run,
    get_task_trace,
    start_agent_run,
    update_task_status,
)
from config.schema import ESG_FIELD_KEYS
from config.schema.huazheng_public_mapping import SCHEMA_VERSION
from pipeline.agent_harness import ESGAgentHarness


PathLike = str | Path


def read_json_safe(path: PathLike) -> Any:
    json_path = Path(path)
    if not json_path.exists():
        return None
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def infer_task_status(summary: Dict[str, Any]) -> str:
    if summary.get("errors"):
        return "failed"
    if summary.get("review_needed"):
        return "review_required"
    if summary.get("ok"):
        return "completed"
    return "completed_with_warnings"


def route_payload(summary: Dict[str, Any], route_key: str) -> Dict[str, Any]:
    value = summary.get(route_key) or {}
    return value if isinstance(value, dict) else {}


class ESGRatingDataHarness:
    """Tracked wrapper around the existing ESGAgentHarness.

    The original harness owns extraction semantics. This wrapper owns run
    persistence: report record, task record, agent run trace, and review item
    persistence for future API/dashboard use.
    """

    def __init__(
        self,
        report_dir: PathLike,
        *,
        industry: Optional[str] = None,
        expected_core_fields: int | None = None,
        allow_route_b: bool = False,
        retrieval_profile: str = "baseline",
        schema_version: str = SCHEMA_VERSION,
        metadata: Optional[Dict[str, Any]] = None,
        db_path: PathLike | None = None,
    ):
        self.report_dir = Path(report_dir)
        self.industry = industry
        self.expected_core_fields = expected_core_fields or len(ESG_FIELD_KEYS)
        self.allow_route_b = allow_route_b
        self.retrieval_profile = retrieval_profile
        self.schema_version = schema_version
        self.metadata = metadata or {}
        self.db_path = db_path

    @property
    def report_name(self) -> str:
        return self.report_dir.name

    @property
    def review_queue_path(self) -> Path:
        return self.report_dir / "human_review_queue.json"

    def _create_report_and_task(self) -> tuple[Dict[str, Any], Dict[str, Any]]:
        report = create_report(
            file_name=self.report_name,
            file_path=str(self.report_dir),
            company_name=self.metadata.get("company_name"),
            report_year=self.metadata.get("report_year"),
            industry=self.industry,
            metadata={
                **self.metadata,
                "report_dir": str(self.report_dir),
                "source_type": "processed_report_dir",
            },
            db_path=self.db_path,
        )
        task = create_task(
            report_id=report["id"],
            industry=self.industry,
            schema_version=self.schema_version,
            retrieval_profile=self.retrieval_profile,
            metadata={
                "allow_route_b": self.allow_route_b,
                "expected_core_fields": self.expected_core_fields,
                "report_name": self.report_name,
            },
            db_path=self.db_path,
        )
        return report, task

    def _record_route_runs(self, task_id: str, summary: Dict[str, Any]) -> None:
        route_specs = [
            ("SupervisorAgent", "final_state"),
            ("RouteASchemaRerunAgent", "schema_rerun"),
            ("RouteBTextRAGAgent", "route_b"),
            ("MergeAgent", "merge"),
        ]
        for agent_name, key in route_specs:
            run = start_agent_run(
                task_id=task_id,
                agent_name=agent_name,
                input_data={"summary_key": key},
                db_path=self.db_path,
            )
            payload = route_payload(summary, key)
            status = payload.get("execution_status") or payload.get("status") or "completed"
            if key == "final_state":
                status = "completed"
                payload = summary.get("final_state", {})
            finish_agent_run(
                agent_run_id=run["id"],
                status=status,
                output_data=payload,
                db_path=self.db_path,
            )

    def _record_review_items(self, task_id: str, report_id: str) -> None:
        review_items = read_json_safe(self.review_queue_path)
        if not isinstance(review_items, list):
            return

        for item in review_items:
            if not isinstance(item, dict):
                continue
            create_review_item(
                task_id=task_id,
                report_id=report_id,
                field_key=item.get("field_key"),
                reason=str(item.get("reason", "review_required")),
                status=str(item.get("status", "pending")),
                recommended_action=item.get("recommended_action"),
                metadata={
                    "source_route": item.get("source_route"),
                    "details": item.get("details", {}),
                    "source_review_id": item.get("review_id"),
                    "report_name": item.get("report_name"),
                },
                db_path=self.db_path,
            )

    def run(self) -> Dict[str, Any]:
        report, task = self._create_report_and_task()
        update_task_status(task["id"], "running", db_path=self.db_path)

        harness_run = start_agent_run(
            task_id=task["id"],
            agent_name="ESGAgentHarness",
            input_data={
                "report_dir": str(self.report_dir),
                "allow_route_b": self.allow_route_b,
                "expected_core_fields": self.expected_core_fields,
            },
            db_path=self.db_path,
        )

        try:
            summary = ESGAgentHarness(
                report_dir=self.report_dir,
                expected_core_fields=self.expected_core_fields,
                allow_route_b=self.allow_route_b,
            ).run()
        except Exception as exc:
            finish_agent_run(
                agent_run_id=harness_run["id"],
                status="failed",
                output_data={},
                error_message=str(exc),
                db_path=self.db_path,
            )
            update_task_status(task["id"], "failed", db_path=self.db_path)
            raise

        final_status = infer_task_status(summary)
        finish_agent_run(
            agent_run_id=harness_run["id"],
            status="completed" if final_status != "failed" else "failed",
            output_data=summary,
            db_path=self.db_path,
        )
        self._record_route_runs(task["id"], summary)
        self._record_review_items(task["id"], report["id"])
        update_task_status(task["id"], final_status, db_path=self.db_path)

        return {
            **summary,
            "backend_report_id": report["id"],
            "backend_task_id": task["id"],
            "backend_task_status": final_status,
            "trace": get_task_trace(task["id"], db_path=self.db_path),
        }
