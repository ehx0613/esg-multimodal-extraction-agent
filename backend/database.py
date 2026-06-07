from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from config.settings import PROJECT_ROOT


DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "agent_state.db"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def json_dumps(value: Optional[Dict[str, Any]]) -> str:
    return json.dumps(value or {}, ensure_ascii=False, sort_keys=True)


def json_loads(value: Optional[str]) -> Dict[str, Any]:
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def get_db_path(db_path: str | Path | None = None) -> Path:
    if db_path is not None:
        return Path(db_path)
    return Path(os.getenv("AGENT_DB_PATH", str(DEFAULT_DB_PATH)))


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    path = get_db_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def connection(db_path: str | Path | None = None):
    conn = connect(db_path)
    try:
        yield conn
    finally:
        conn.close()


SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS reports (
        id TEXT PRIMARY KEY,
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        company_name TEXT,
        report_year INTEGER,
        industry TEXT,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        report_id TEXT NOT NULL,
        status TEXT NOT NULL,
        industry TEXT,
        schema_version TEXT NOT NULL,
        retrieval_profile TEXT NOT NULL,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(report_id) REFERENCES reports(id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)",
    "CREATE INDEX IF NOT EXISTS idx_tasks_industry ON tasks(industry)",
    """
    CREATE TABLE IF NOT EXISTS prompt_versions (
        id TEXT PRIMARY KEY,
        agent_name TEXT NOT NULL,
        prompt_name TEXT NOT NULL,
        version TEXT NOT NULL,
        content_hash TEXT NOT NULL,
        template_content TEXT NOT NULL,
        notes TEXT,
        created_at TEXT NOT NULL,
        UNIQUE(agent_name, prompt_name, version)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS agent_runs (
        id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL,
        agent_name TEXT NOT NULL,
        status TEXT NOT NULL,
        started_at TEXT,
        finished_at TEXT,
        input_json TEXT NOT NULL DEFAULT '{}',
        output_json TEXT NOT NULL DEFAULT '{}',
        error_message TEXT,
        FOREIGN KEY(task_id) REFERENCES tasks(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tool_calls (
        id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL,
        agent_run_id TEXT,
        tool_name TEXT NOT NULL,
        status TEXT NOT NULL,
        latency_ms INTEGER,
        input_json TEXT NOT NULL DEFAULT '{}',
        output_json TEXT NOT NULL DEFAULT '{}',
        error_message TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(task_id) REFERENCES tasks(id),
        FOREIGN KEY(agent_run_id) REFERENCES agent_runs(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS model_calls (
        id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL,
        agent_run_id TEXT,
        prompt_version_id TEXT,
        model_name TEXT NOT NULL,
        status TEXT NOT NULL,
        input_tokens INTEGER DEFAULT 0,
        output_tokens INTEGER DEFAULT 0,
        latency_ms INTEGER,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        error_message TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(task_id) REFERENCES tasks(id),
        FOREIGN KEY(agent_run_id) REFERENCES agent_runs(id),
        FOREIGN KEY(prompt_version_id) REFERENCES prompt_versions(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS extraction_results (
        id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL,
        report_id TEXT NOT NULL,
        field_key TEXT NOT NULL,
        value TEXT,
        raw_value TEXT,
        standardized_value TEXT,
        unit TEXT,
        year INTEGER,
        confidence REAL,
        source_route TEXT,
        source_file TEXT,
        page_number INTEGER,
        chunk_id TEXT,
        evidence_text TEXT,
        review_status TEXT NOT NULL DEFAULT 'not_reviewed',
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        FOREIGN KEY(task_id) REFERENCES tasks(id),
        FOREIGN KEY(report_id) REFERENCES reports(id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_extraction_results_field ON extraction_results(field_key)",
    """
    CREATE TABLE IF NOT EXISTS review_items (
        id TEXT PRIMARY KEY,
        task_id TEXT NOT NULL,
        report_id TEXT NOT NULL,
        field_key TEXT,
        reason TEXT NOT NULL,
        status TEXT NOT NULL,
        recommended_action TEXT,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(task_id) REFERENCES tasks(id),
        FOREIGN KEY(report_id) REFERENCES reports(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS retrieval_eval_records (
        id TEXT PRIMARY KEY,
        task_id TEXT,
        eval_set_name TEXT NOT NULL,
        retrieval_profile TEXT NOT NULL,
        hit_rate_at_5 REAL,
        mrr_at_5 REAL,
        avg_latency_ms REAL,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        FOREIGN KEY(task_id) REFERENCES tasks(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS rating_runs (
        id TEXT PRIMARY KEY,
        task_id TEXT,
        report_id TEXT,
        report_dir TEXT,
        rating_model TEXT NOT NULL,
        industry TEXT,
        overall_score REAL NOT NULL,
        overall_rating TEXT NOT NULL,
        field_count INTEGER DEFAULT 0,
        scored_field_count INTEGER DEFAULT 0,
        needs_review_count INTEGER DEFAULT 0,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        FOREIGN KEY(task_id) REFERENCES tasks(id),
        FOREIGN KEY(report_id) REFERENCES reports(id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_rating_runs_report_dir ON rating_runs(report_dir)",
    "CREATE INDEX IF NOT EXISTS idx_rating_runs_created_at ON rating_runs(created_at)",
    """
    CREATE TABLE IF NOT EXISTS rating_score_items (
        id TEXT PRIMARY KEY,
        rating_run_id TEXT NOT NULL,
        level TEXT NOT NULL,
        item_key TEXT NOT NULL,
        name_cn TEXT,
        pillar TEXT,
        score REAL,
        rating TEXT,
        field_count INTEGER DEFAULT 0,
        scored_field_count INTEGER DEFAULT 0,
        coverage REAL,
        evidence_coverage REAL,
        needs_review_count INTEGER DEFAULT 0,
        metadata_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        FOREIGN KEY(rating_run_id) REFERENCES rating_runs(id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_rating_score_items_run ON rating_score_items(rating_run_id)",
    "CREATE INDEX IF NOT EXISTS idx_rating_score_items_level ON rating_score_items(level)",
]


def init_db(db_path: str | Path | None = None) -> Path:
    path = get_db_path(db_path)
    with connection(path) as conn:
        for statement in SCHEMA_STATEMENTS:
            conn.execute(statement)
        conn.commit()
    return path


def row_to_dict(row: sqlite3.Row | None) -> Optional[Dict[str, Any]]:
    if row is None:
        return None
    result = dict(row)
    for key in ("metadata_json", "input_json", "output_json"):
        if key in result:
            result[key] = json_loads(result[key])
    return result


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> List[Dict[str, Any]]:
    return [row_to_dict(row) or {} for row in rows]


def create_report(
    *,
    file_name: str,
    file_path: str,
    company_name: str | None = None,
    report_year: int | None = None,
    industry: str | None = None,
    metadata: Optional[Dict[str, Any]] = None,
    db_path: str | Path | None = None,
) -> Dict[str, Any]:
    init_db(db_path)
    report_id = new_id("report")
    created_at = now_iso()
    with connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO reports (
                id, file_name, file_path, company_name, report_year,
                industry, metadata_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report_id,
                file_name,
                file_path,
                company_name,
                report_year,
                industry,
                json_dumps(metadata),
                created_at,
            ),
        )
        conn.commit()
    return get_report(report_id, db_path=db_path) or {}


def get_report(report_id: str, db_path: str | Path | None = None) -> Optional[Dict[str, Any]]:
    init_db(db_path)
    with connection(db_path) as conn:
        row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    return row_to_dict(row)


def create_task(
    *,
    report_id: str,
    industry: str | None,
    schema_version: str,
    retrieval_profile: str,
    metadata: Optional[Dict[str, Any]] = None,
    db_path: str | Path | None = None,
) -> Dict[str, Any]:
    init_db(db_path)
    task_id = new_id("task")
    ts = now_iso()
    with connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO tasks (
                id, report_id, status, industry, schema_version,
                retrieval_profile, metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                report_id,
                "pending",
                industry,
                schema_version,
                retrieval_profile,
                json_dumps(metadata),
                ts,
                ts,
            ),
        )
        conn.commit()
    return get_task(task_id, db_path=db_path) or {}


def get_task(task_id: str, db_path: str | Path | None = None) -> Optional[Dict[str, Any]]:
    init_db(db_path)
    with connection(db_path) as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return row_to_dict(row)


def list_tasks(db_path: str | Path | None = None, limit: int = 50) -> List[Dict[str, Any]]:
    init_db(db_path)
    with connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return rows_to_dicts(rows)


def update_task_status(
    task_id: str,
    status: str,
    db_path: str | Path | None = None,
) -> Dict[str, Any]:
    init_db(db_path)
    with connection(db_path) as conn:
        conn.execute(
            "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
            (status, now_iso(), task_id),
        )
        conn.commit()
    return get_task(task_id, db_path=db_path) or {}


def upsert_prompt_version(
    *,
    agent_name: str,
    prompt_name: str,
    version: str,
    content_hash: str,
    template_content: str,
    notes: str | None = None,
    db_path: str | Path | None = None,
) -> Dict[str, Any]:
    init_db(db_path)
    prompt_id = new_id("prompt")
    with connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO prompt_versions (
                id, agent_name, prompt_name, version, content_hash,
                template_content, notes, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(agent_name, prompt_name, version) DO UPDATE SET
                content_hash = excluded.content_hash,
                template_content = excluded.template_content,
                notes = excluded.notes
            """,
            (
                prompt_id,
                agent_name,
                prompt_name,
                version,
                content_hash,
                template_content,
                notes,
                now_iso(),
            ),
        )
        row = conn.execute(
            """
            SELECT * FROM prompt_versions
            WHERE agent_name = ? AND prompt_name = ? AND version = ?
            """,
            (agent_name, prompt_name, version),
        ).fetchone()
        conn.commit()
    return row_to_dict(row) or {}


def start_agent_run(
    *,
    task_id: str,
    agent_name: str,
    input_data: Optional[Dict[str, Any]] = None,
    db_path: str | Path | None = None,
) -> Dict[str, Any]:
    init_db(db_path)
    run_id = new_id("agent_run")
    with connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO agent_runs (
                id, task_id, agent_name, status, started_at, input_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (run_id, task_id, agent_name, "running", now_iso(), json_dumps(input_data)),
        )
        row = conn.execute("SELECT * FROM agent_runs WHERE id = ?", (run_id,)).fetchone()
        conn.commit()
    return row_to_dict(row) or {}


def finish_agent_run(
    *,
    agent_run_id: str,
    status: str,
    output_data: Optional[Dict[str, Any]] = None,
    error_message: str | None = None,
    db_path: str | Path | None = None,
) -> Dict[str, Any]:
    init_db(db_path)
    with connection(db_path) as conn:
        conn.execute(
            """
            UPDATE agent_runs
            SET status = ?, finished_at = ?, output_json = ?, error_message = ?
            WHERE id = ?
            """,
            (
                status,
                now_iso(),
                json_dumps(output_data),
                error_message,
                agent_run_id,
            ),
        )
        row = conn.execute("SELECT * FROM agent_runs WHERE id = ?", (agent_run_id,)).fetchone()
        conn.commit()
    return row_to_dict(row) or {}


def create_review_item(
    *,
    task_id: str,
    report_id: str,
    reason: str,
    status: str = "pending",
    field_key: str | None = None,
    recommended_action: str | None = None,
    metadata: Optional[Dict[str, Any]] = None,
    db_path: str | Path | None = None,
) -> Dict[str, Any]:
    init_db(db_path)
    item_id = new_id("review")
    ts = now_iso()
    with connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO review_items (
                id, task_id, report_id, field_key, reason, status,
                recommended_action, metadata_json, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item_id,
                task_id,
                report_id,
                field_key,
                reason,
                status,
                recommended_action,
                json_dumps(metadata),
                ts,
                ts,
            ),
        )
        row = conn.execute("SELECT * FROM review_items WHERE id = ?", (item_id,)).fetchone()
        conn.commit()
    return row_to_dict(row) or {}


def create_retrieval_eval_record(
    *,
    eval_set_name: str,
    retrieval_profile: str,
    hit_rate_at_5: float,
    mrr_at_5: float,
    avg_latency_ms: float,
    task_id: str | None = None,
    metadata: Optional[Dict[str, Any]] = None,
    db_path: str | Path | None = None,
) -> Dict[str, Any]:
    init_db(db_path)
    record_id = new_id("retrieval_eval")
    with connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO retrieval_eval_records (
                id, task_id, eval_set_name, retrieval_profile,
                hit_rate_at_5, mrr_at_5, avg_latency_ms, metadata_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record_id,
                task_id,
                eval_set_name,
                retrieval_profile,
                hit_rate_at_5,
                mrr_at_5,
                avg_latency_ms,
                json_dumps(metadata),
                now_iso(),
            ),
        )
        row = conn.execute(
            "SELECT * FROM retrieval_eval_records WHERE id = ?",
            (record_id,),
        ).fetchone()
        conn.commit()
    return row_to_dict(row) or {}


def list_retrieval_eval_records(
    db_path: str | Path | None = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    init_db(db_path)
    with connection(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM retrieval_eval_records ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return rows_to_dicts(rows)


def _rating_score_item_rows(rating_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows = [
        {
            "level": "overall",
            "item_key": "overall",
            "name_cn": "总分",
            "pillar": None,
            **rating_result.get("overall", {}),
        }
    ]
    for pillar, score in (rating_result.get("pillar_scores") or {}).items():
        rows.append(
            {
                "level": "pillar",
                "item_key": pillar,
                "name_cn": pillar,
                "pillar": pillar,
                **score,
            }
        )
    for theme in rating_result.get("theme_scores") or []:
        rows.append(
            {
                "level": "theme",
                "item_key": theme.get("theme_key"),
                "name_cn": theme.get("theme_name_cn"),
                "pillar": theme.get("pillar"),
                **theme,
            }
        )
    for field in rating_result.get("field_scores") or []:
        rows.append(
            {
                "level": "field",
                "item_key": field.get("field_key"),
                "name_cn": field.get("field_name_cn"),
                "pillar": field.get("pillar"),
                "score": field.get("score"),
                "rating": None,
                "field_count": 1 if float(field.get("weight") or 0.0) > 0 else 0,
                "scored_field_count": 1 if field.get("is_success") and float(field.get("weight") or 0.0) > 0 else 0,
                "coverage": 1.0 if field.get("is_success") else 0.0,
                "evidence_coverage": 1.0
                if field.get("citation_review_status") in {"auto_cited", "reviewed_approved"}
                else 0.0,
                "needs_review_count": 1 if field.get("citation_review_status") == "needs_review" else 0,
                "metadata_json": field,
            }
        )
    return rows


def create_rating_record(
    *,
    rating_result: Dict[str, Any],
    report_dir: str | None = None,
    task_id: str | None = None,
    report_id: str | None = None,
    metadata: Optional[Dict[str, Any]] = None,
    db_path: str | Path | None = None,
) -> Dict[str, Any]:
    init_db(db_path)
    rating_id = new_id("rating")
    created_at = now_iso()
    overall = rating_result.get("overall") or {}
    with connection(db_path) as conn:
        conn.execute(
            """
            INSERT INTO rating_runs (
                id, task_id, report_id, report_dir, rating_model, industry,
                overall_score, overall_rating, field_count, scored_field_count,
                needs_review_count, metadata_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rating_id,
                task_id,
                report_id,
                report_dir,
                str(rating_result.get("rating_model", "")),
                rating_result.get("industry"),
                float(overall.get("score") or 0.0),
                str(overall.get("rating", "")),
                int(overall.get("field_count") or 0),
                int(overall.get("scored_field_count") or 0),
                int(overall.get("needs_review_count") or 0),
                json_dumps(
                    {
                        **(metadata or {}),
                        "rating_boundary": rating_result.get("rating_boundary"),
                    }
                ),
                created_at,
            ),
        )
        for item in _rating_score_item_rows(rating_result):
            conn.execute(
                """
                INSERT INTO rating_score_items (
                    id, rating_run_id, level, item_key, name_cn, pillar,
                    score, rating, field_count, scored_field_count, coverage,
                    evidence_coverage, needs_review_count, metadata_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    new_id("rating_item"),
                    rating_id,
                    item.get("level"),
                    str(item.get("item_key") or ""),
                    item.get("name_cn"),
                    item.get("pillar"),
                    item.get("score"),
                    item.get("rating"),
                    int(item.get("field_count") or 0),
                    int(item.get("scored_field_count") or 0),
                    item.get("coverage"),
                    item.get("evidence_coverage"),
                    int(item.get("needs_review_count") or 0),
                    json_dumps(item.get("metadata_json") or item),
                    created_at,
                ),
            )
        row = conn.execute("SELECT * FROM rating_runs WHERE id = ?", (rating_id,)).fetchone()
        conn.commit()
    return row_to_dict(row) or {}


def list_rating_runs(
    *,
    report_dir: str | None = None,
    task_id: str | None = None,
    db_path: str | Path | None = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    init_db(db_path)
    clauses = []
    params: List[Any] = []
    if report_dir:
        clauses.append("report_dir = ?")
        params.append(report_dir)
    if task_id:
        clauses.append("task_id = ?")
        params.append(task_id)
    where_sql = " WHERE " + " AND ".join(clauses) if clauses else ""
    params.append(limit)
    with connection(db_path) as conn:
        rows = conn.execute(
            f"SELECT * FROM rating_runs{where_sql} ORDER BY created_at DESC LIMIT ?",
            params,
        ).fetchall()
    return rows_to_dicts(rows)


def get_rating_run(
    rating_run_id: str,
    db_path: str | Path | None = None,
) -> Optional[Dict[str, Any]]:
    init_db(db_path)
    with connection(db_path) as conn:
        run = conn.execute("SELECT * FROM rating_runs WHERE id = ?", (rating_run_id,)).fetchone()
        items = conn.execute(
            "SELECT * FROM rating_score_items WHERE rating_run_id = ? ORDER BY level, item_key",
            (rating_run_id,),
        ).fetchall()
    run_dict = row_to_dict(run)
    if run_dict is None:
        return None
    run_dict["items"] = rows_to_dicts(items)
    return run_dict


def list_review_items(
    *,
    task_id: str | None = None,
    report_id: str | None = None,
    db_path: str | Path | None = None,
) -> List[Dict[str, Any]]:
    init_db(db_path)
    clauses = []
    params: List[str] = []
    if task_id:
        clauses.append("task_id = ?")
        params.append(task_id)
    if report_id:
        clauses.append("report_id = ?")
        params.append(report_id)

    where_sql = " WHERE " + " AND ".join(clauses) if clauses else ""
    with connection(db_path) as conn:
        rows = conn.execute(
            f"SELECT * FROM review_items{where_sql} ORDER BY created_at",
            params,
        ).fetchall()
    return rows_to_dicts(rows)


def get_task_trace(task_id: str, db_path: str | Path | None = None) -> Dict[str, Any]:
    init_db(db_path)
    with connection(db_path) as conn:
        task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        agent_runs = conn.execute(
            "SELECT * FROM agent_runs WHERE task_id = ? ORDER BY started_at",
            (task_id,),
        ).fetchall()
        tool_calls = conn.execute(
            "SELECT * FROM tool_calls WHERE task_id = ? ORDER BY created_at",
            (task_id,),
        ).fetchall()
        model_calls = conn.execute(
            "SELECT * FROM model_calls WHERE task_id = ? ORDER BY created_at",
            (task_id,),
        ).fetchall()
        review_items = conn.execute(
            "SELECT * FROM review_items WHERE task_id = ? ORDER BY created_at",
            (task_id,),
        ).fetchall()
    return {
        "task": row_to_dict(task),
        "agent_runs": rows_to_dicts(agent_runs),
        "tool_calls": rows_to_dicts(tool_calls),
        "model_calls": rows_to_dicts(model_calls),
        "review_items": rows_to_dicts(review_items),
    }
