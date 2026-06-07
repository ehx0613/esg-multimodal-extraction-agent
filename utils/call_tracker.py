import contextvars
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator

from utils.result_guard import safe_write_json


_ACTIVE_TRACKER: contextvars.ContextVar["LLMCallTracker | None"] = contextvars.ContextVar(
    "active_llm_call_tracker",
    default=None,
)

MODE_CALL_BUDGETS = {
    "fast": {
        "vlm_table_extract": 10,
        "schema_judge": 6,
        "qualitative_extract": 15,
        "quantitative_extract": 20,
        "table_arbitration_vlm": 0,
    },
    "balanced": {
        "vlm_table_extract": 12,
        "schema_judge": 35,
        "qualitative_extract": 18,
        "quantitative_extract": 25,
        "table_arbitration_vlm": 3,
    },
    "deep": {},
}


def _usage_value(usage: Any, name: str) -> int:
    if usage is None:
        return 0
    value = getattr(usage, name, None)
    if value is None and isinstance(usage, dict):
        value = usage.get(name)
    try:
        return int(value or 0)
    except Exception:
        return 0


class LLMCallTracker:
    def __init__(self, report_dir: Path, run_mode: str = "balanced"):
        self.report_dir = Path(report_dir)
        self.run_mode = run_mode
        self.events_path = self.report_dir / "run_call_events.json"
        self.summary_path = self.report_dir / "run_cost_summary.json"
        self.events: list[Dict[str, Any]] = []
        self.started_at = time.time()

    @contextmanager
    def activate(self) -> Iterator["LLMCallTracker"]:
        token = _ACTIVE_TRACKER.set(self)
        try:
            yield self
        finally:
            _ACTIVE_TRACKER.reset(token)
            self.flush()

    def record(
        self,
        *,
        stage: str,
        model: str,
        started_at: float,
        response: Any = None,
        metadata: Dict[str, Any] | None = None,
        error: str = "",
    ) -> None:
        usage = getattr(response, "usage", None)
        prompt_tokens = _usage_value(usage, "prompt_tokens")
        completion_tokens = _usage_value(usage, "completion_tokens")
        total_tokens = _usage_value(usage, "total_tokens") or prompt_tokens + completion_tokens
        self.events.append(
            {
                "stage": stage,
                "model": model,
                "latency_ms": round((time.time() - started_at) * 1000, 2),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "usage_available": usage is not None,
                "error": error,
                "metadata": metadata or {},
            }
        )

    def allow_call(self, stage: str) -> bool:
        limit = MODE_CALL_BUDGETS.get(self.run_mode, {}).get(stage)
        if limit is None:
            return True
        used = sum(1 for event in self.events if event.get("stage") == stage)
        return used < limit

    def flush(self) -> None:
        self.report_dir.mkdir(parents=True, exist_ok=True)
        safe_write_json(self.events_path, self.events)
        by_stage: Dict[str, Dict[str, Any]] = {}
        for event in self.events:
            stage = event["stage"]
            item = by_stage.setdefault(
                stage,
                {"calls": 0, "latency_ms": 0.0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            )
            item["calls"] += 1
            item["latency_ms"] = round(item["latency_ms"] + float(event["latency_ms"]), 2)
            item["prompt_tokens"] += int(event["prompt_tokens"])
            item["completion_tokens"] += int(event["completion_tokens"])
            item["total_tokens"] += int(event["total_tokens"])
        summary = {
            "run_mode": self.run_mode,
            "elapsed_ms": round((time.time() - self.started_at) * 1000, 2),
            "calls": len(self.events),
            "prompt_tokens": sum(int(event["prompt_tokens"]) for event in self.events),
            "completion_tokens": sum(int(event["completion_tokens"]) for event in self.events),
            "total_tokens": sum(int(event["total_tokens"]) for event in self.events),
            "calls_without_usage": sum(1 for event in self.events if not event["usage_available"]),
            "by_stage": by_stage,
            "events_path": str(self.events_path),
        }
        safe_write_json(self.summary_path, summary)


def get_active_tracker() -> LLMCallTracker | None:
    return _ACTIVE_TRACKER.get()


def get_active_run_mode() -> str:
    tracker = get_active_tracker()
    return tracker.run_mode if tracker is not None else "balanced"


def model_call_allowed(stage: str) -> bool:
    tracker = get_active_tracker()
    return tracker is None or tracker.allow_call(stage)


def record_model_call(
    *,
    stage: str,
    model: str,
    started_at: float,
    response: Any = None,
    metadata: Dict[str, Any] | None = None,
    error: str = "",
) -> None:
    tracker = get_active_tracker()
    if tracker is not None:
        tracker.record(
            stage=stage,
            model=model,
            started_at=started_at,
            response=response,
            metadata=metadata,
            error=error,
        )
