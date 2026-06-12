from __future__ import annotations

import ast
import csv
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


SOURCE_DIRS = ("agents", "backend", "config", "pipeline", "scripts", "utils")
SUMMARY_FILES = (
    "unified_pipeline_summary.json",
    "run_cost_summary.json",
    "merge_summary.json",
    "validation_summary.json",
    "route_b_summary.json",
    "route_b_quant_summary.json",
    "full_rating_workflow_summary.json",
)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _git(root: Path, *args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        ).stdout.strip()
    except Exception:
        return ""


def _source_inventory(root: Path) -> list[dict[str, Any]]:
    rows = []
    for directory in SOURCE_DIRS:
        for path in sorted((root / directory).rglob("*.py")):
            relative = path.relative_to(root).as_posix()
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"))
                module_doc = ast.get_docstring(tree) or ""
                classes = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
                functions = [
                    node.name
                    for node in tree.body
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
            except Exception as exc:
                module_doc, classes, functions = f"Parse error: {exc}", [], []
            rows.append(
                {
                    "path": relative,
                    "purpose": module_doc.strip().splitlines()[0] if module_doc.strip() else "",
                    "classes": classes,
                    "functions": functions,
                }
            )
    return rows


def _latest_report(root: Path) -> Path | None:
    candidates = []
    for path in (root / "output").rglob("unified_pipeline_summary.json"):
        candidates.append(path.parent)
    for path in (root / "output").rglob("full_rating_workflow_summary.json"):
        candidates.append(path.parent)
    unique = {path.resolve(): path for path in candidates}
    return max(unique.values(), key=lambda item: item.stat().st_mtime) if unique else None


def _csv_rows(path: Path) -> int | None:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            return max(sum(1 for _ in csv.reader(file)) - 1, 0)
    except Exception:
        return None


def _report_snapshot(report_dir: Path | None) -> dict[str, Any]:
    if report_dir is None:
        return {"available": False}
    summaries = {
        name: _read_json(report_dir / name)
        for name in SUMMARY_FILES
        if (report_dir / name).exists()
    }
    artifacts = []
    for path in sorted(report_dir.iterdir()):
        if path.is_file():
            artifacts.append(
                {
                    "name": path.name,
                    "size_bytes": path.stat().st_size,
                    "csv_rows": _csv_rows(path) if path.suffix.lower() == ".csv" else None,
                }
            )
    return {
        "available": True,
        "report_dir": str(report_dir),
        "report_name": report_dir.name,
        "summaries": summaries,
        "artifacts": artifacts,
    }


def build_project_snapshot(root: Path) -> dict[str, Any]:
    root = root.resolve()
    latest_report = _latest_report(root)
    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "project_root": str(root),
        "git": {
            "branch": _git(root, "branch", "--show-current"),
            "commit": _git(root, "rev-parse", "HEAD"),
            "commit_subject": _git(root, "log", "-1", "--pretty=%s"),
            "status": _git(root, "status", "--short").splitlines(),
            "remote": _git(root, "remote", "-v").splitlines(),
        },
        "source_inventory": _source_inventory(root),
        "latest_report": _report_snapshot(latest_report),
    }


def write_project_memory(root: Path) -> dict[str, str]:
    root = root.resolve()
    memory_dir = root / "docs" / "project_memory"
    runs_dir = memory_dir / "runs"
    logs_dir = memory_dir / "logs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    snapshot = build_project_snapshot(root)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    snapshot_path = memory_dir / "latest_snapshot.json"
    result_path = runs_dir / f"{stamp}_result.md"
    log_path = logs_dir / f"{stamp}_log.md"
    latest_result_path = memory_dir / "LATEST_RESULT.md"
    latest_log_path = memory_dir / "LATEST_LOG.md"

    snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    report = snapshot["latest_report"]
    summaries = report.get("summaries", {})
    unified = summaries.get("unified_pipeline_summary.json") or {}
    merge = summaries.get("merge_summary.json") or {}
    cost = summaries.get("run_cost_summary.json") or {}
    result_text = f"""# Latest Project Result

- Generated: {snapshot["generated_at"]}
- Git branch: `{snapshot["git"]["branch"]}`
- Git commit: `{snapshot["git"]["commit"]}` ({snapshot["git"]["commit_subject"]})
- Latest report: `{report.get("report_name", "none")}`
- Report directory: `{report.get("report_dir", "none")}`
- Pipeline status: `{unified.get("status", "unknown")}`
- Run mode: `{unified.get("run_mode", "unknown")}`
- Parser: `{unified.get("document_ingest", {}).get("parser_name", "unknown")}`
- Pages: `{unified.get("document_ingest", {}).get("total_pages", "unknown")}`
- Merged extracted fields: `{merge.get("merged_extracted_fields", "unknown")}`
- Coverage rate: `{merge.get("coverage_rate", "unknown")}`
- Applicable coverage: `{merge.get("applicable_coverage", "unknown")}`
- Model calls: `{cost.get("calls", "unknown")}`
- Total tokens: `{cost.get("total_tokens", "unknown")}`

## Primary Artifacts

{chr(10).join(f'- `{item["name"]}` ({item["size_bytes"]} bytes)' for item in report.get("artifacts", []))}
"""
    log_text = f"""# Project Memory Update Log

- Generated: {snapshot["generated_at"]}
- Source modules indexed: {len(snapshot["source_inventory"])}
- Latest report detected: `{report.get("report_name", "none")}`
- Dirty Git entries: {len(snapshot["git"]["status"])}
- Snapshot: `docs/project_memory/latest_snapshot.json`
- Result: `docs/project_memory/LATEST_RESULT.md`

## Git Status

{chr(10).join(f'- `{line}`' for line in snapshot["git"]["status"]) or "- Clean"}
"""
    result_path.write_text(result_text, encoding="utf-8")
    latest_result_path.write_text(result_text, encoding="utf-8")
    log_path.write_text(log_text, encoding="utf-8")
    latest_log_path.write_text(log_text, encoding="utf-8")
    return {
        "snapshot": str(snapshot_path),
        "result": str(result_path),
        "log": str(log_path),
        "latest_result": str(latest_result_path),
        "latest_log": str(latest_log_path),
    }
