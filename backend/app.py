from __future__ import annotations

from html import escape
from contextlib import asynccontextmanager
from pathlib import Path
import re
import shutil
from typing import Any, Dict, Optional
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from pydantic import BaseModel

from config.settings import RAW_DATA_DIR, REPORTS_DIR
from config.schema.huazheng_public_mapping import SCHEMA_VERSION
from pipeline.rating_data_harness import ESGRatingDataHarness
from pipeline.unified_pipeline import UnifiedESGPipeline
from utils.field_citations import (
    FIELD_CITATION_CSV_FIELDS,
    attach_field_citations,
    flatten_for_csv as flatten_citations_for_csv,
    read_json as read_citation_json,
)
from utils.result_guard import safe_write_csv, safe_write_json
from utils.rating_review import apply_review_decision, load_review_queue, recalculate_rating
from utils.simulated_rating import (
    SUMMARY_CSV_FIELDS,
    build_simulated_rating,
    flatten_rating_summary,
)

from .database import (
    create_rating_record,
    create_report,
    create_task,
    get_rating_run,
    get_task,
    get_task_trace,
    init_db,
    list_rating_runs,
    list_tasks,
    list_review_items,
    update_task_status,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="ESG Agent Backend",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ReportCreate(BaseModel):
    file_name: str
    file_path: str
    company_name: Optional[str] = None
    report_year: Optional[int] = None
    industry: Optional[str] = None
    metadata: Dict[str, Any] = {}


class TaskCreate(BaseModel):
    report_id: str
    industry: Optional[str] = None
    schema_version: str = SCHEMA_VERSION
    retrieval_profile: str = "baseline"
    metadata: Dict[str, Any] = {}


class TaskStatusUpdate(BaseModel):
    status: str


class RunReportDirRequest(BaseModel):
    report_dir: str
    industry: Optional[str] = None
    allow_route_b: bool = False
    expected_core_fields: Optional[int] = None
    retrieval_profile: str = "baseline"
    schema_version: str = SCHEMA_VERSION
    metadata: Dict[str, Any] = {}
    generate_citations: bool = False
    generate_rating: bool = False


class AnalyzeUploadedReportRequest(BaseModel):
    report_dir: str
    pdf_path: Optional[str] = None
    task_id: Optional[str] = None
    industry: Optional[str] = None


class RatingReviewApplyRequest(BaseModel):
    report_dir: str
    field_key: str
    action: str
    industry: Optional[str] = None
    reviewer: Optional[str] = None
    notes: Optional[str] = None
    correction: Dict[str, Any] = {}


class RatingReviewQueueRequest(BaseModel):
    report_dir: str


class RatingRecalculateRequest(BaseModel):
    report_dir: str
    industry: Optional[str] = None


def safe_upload_stem(file_name: str) -> str:
    stem = Path(file_name).stem.strip()
    stem = re.sub(r"[^\w\u4e00-\u9fff.-]+", "_", stem, flags=re.UNICODE)
    stem = stem.strip("._")
    return stem or "uploaded_report"


def next_report_dir(stem: str) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    candidate = REPORTS_DIR / stem
    if not candidate.exists():
        return candidate
    index = 2
    while True:
        candidate = REPORTS_DIR / f"{stem}_{index}"
        if not candidate.exists():
            return candidate
        index += 1


def parse_multipart_upload(request_body: bytes, content_type: str) -> Dict[str, Any]:
    match = re.search(r"boundary=(?P<boundary>[^;]+)", content_type)
    if not match:
        raise HTTPException(status_code=400, detail="multipart boundary is required")

    boundary = match.group("boundary").strip().strip('"').encode("utf-8")
    parsed: Dict[str, Any] = {"fields": {}, "file": None}
    for part in request_body.split(b"--" + boundary):
        part = part.strip()
        if not part or part == b"--":
            continue
        if part.endswith(b"--"):
            part = part[:-2].strip()
        header_blob, separator, content = part.partition(b"\r\n\r\n")
        if not separator:
            continue
        header_text = header_blob.decode("utf-8", errors="ignore")
        content = content[:-2] if content.endswith(b"\r\n") else content
        name_match = re.search(r'name="([^"]+)"', header_text)
        if not name_match:
            continue
        name = name_match.group(1)
        filename_match = re.search(r'filename="([^"]*)"', header_text)
        if filename_match:
            parsed["file"] = {
                "field_name": name,
                "filename": filename_match.group(1),
                "content": content,
            }
        else:
            parsed["fields"][name] = content.decode("utf-8", errors="ignore")
    return parsed


def dump_model(model: BaseModel) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def generate_report_artifacts(
    report_dir: Path,
    *,
    industry: str | None = None,
) -> Dict[str, Any]:
    merged_path = report_dir / "merged_esg_results.json"
    chunks_path = report_dir / "route_b_chunks.json"
    if not merged_path.exists():
        raise HTTPException(status_code=400, detail="merged_esg_results.json not found")

    merged_rows = read_citation_json(merged_path)
    chunks = read_citation_json(chunks_path) if chunks_path.exists() else []
    citations = attach_field_citations(
        merged_rows,
        chunks,
        industry=industry,
        top_k=5,
    )
    citations_json_path = report_dir / "field_citations.json"
    citations_csv_path = report_dir / "field_citations.csv"
    safe_write_json(citations_json_path, citations)
    safe_write_csv(
        citations_csv_path,
        flatten_citations_for_csv(citations),
        preferred_order=FIELD_CITATION_CSV_FIELDS,
    )

    rating = build_simulated_rating(citations, industry=industry)
    rating_json_path = report_dir / "simulated_rating.json"
    rating_csv_path = report_dir / "simulated_rating_summary.csv"
    rating_review_path = report_dir / "rating_review_queue.json"
    safe_write_json(rating_json_path, rating)
    safe_write_csv(
        rating_csv_path,
        flatten_rating_summary(rating),
        preferred_order=SUMMARY_CSV_FIELDS,
    )
    safe_write_json(rating_review_path, rating["human_review_queue"])
    rating_record = create_rating_record(
        rating_result=rating,
        report_dir=str(report_dir),
        metadata={"source": "generate_report_artifacts"},
    )

    return {
        "citations": {
            "json_path": str(citations_json_path),
            "csv_path": str(citations_csv_path),
            "field_count": len(citations),
            "needs_review_count": sum(
                1 for row in citations if row.get("citation_review_status") == "needs_review"
            ),
        },
        "rating": {
            "json_path": str(rating_json_path),
            "summary_csv_path": str(rating_csv_path),
            "review_queue_path": str(rating_review_path),
            "score": rating["overall"]["score"],
            "rating": rating["overall"]["rating"],
            "needs_review_count": rating["overall"]["needs_review_count"],
            "rating_run_id": rating_record["id"],
        },
    }


def _read_json_if_exists(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return read_citation_json(path)
    except Exception:
        return default


def build_report_summary(report_dir: Path) -> Dict[str, Any]:
    if not report_dir.exists() or not report_dir.is_dir():
        raise HTTPException(status_code=404, detail="report_dir not found")

    citations = _read_json_if_exists(report_dir / "field_citations.json", [])
    rating = _read_json_if_exists(report_dir / "simulated_rating.json", {})
    workflow = _read_json_if_exists(report_dir / "full_rating_workflow_summary.json", {})
    review_queue = load_review_queue(report_dir)
    rating_runs = list_rating_runs(report_dir=str(report_dir), limit=5)

    citation_count = len(citations) if isinstance(citations, list) else 0
    auto_cited_count = (
        sum(1 for row in citations if row.get("citation_review_status") in {"auto_cited", "reviewed_approved"})
        if isinstance(citations, list)
        else 0
    )
    citation_review_count = (
        sum(1 for row in citations if row.get("citation_review_status") == "needs_review")
        if isinstance(citations, list)
        else 0
    )
    overall = rating.get("overall", {}) if isinstance(rating, dict) else {}
    pillar_scores = rating.get("pillar_scores", {}) if isinstance(rating, dict) else {}

    return {
        "report_dir": str(report_dir),
        "report_name": report_dir.name,
        "artifacts": {
            "field_citations_json": str(report_dir / "field_citations.json"),
            "simulated_rating_json": str(report_dir / "simulated_rating.json"),
            "rating_review_queue_json": str(report_dir / "rating_review_queue.json"),
            "full_rating_workflow_summary_json": str(report_dir / "full_rating_workflow_summary.json"),
        },
        "citation_summary": {
            "field_count": citation_count,
            "auto_cited_count": auto_cited_count,
            "needs_review_count": citation_review_count,
            "auto_cited_rate": round(auto_cited_count / citation_count, 4) if citation_count else 0.0,
        },
        "rating_summary": {
            "score": overall.get("score"),
            "rating": overall.get("rating"),
            "field_count": overall.get("field_count"),
            "scored_field_count": overall.get("scored_field_count"),
            "needs_review_count": overall.get("needs_review_count"),
            "pillar_scores": pillar_scores,
        },
        "review_queue": {
            "count": len(review_queue),
            "items": review_queue[:10],
        },
        "rating_runs": rating_runs,
        "workflow": workflow,
    }


def _review_url(report_dir: str | Path, industry: str | None = None) -> str:
    url = f"/review?report_dir={quote(str(report_dir))}"
    if industry:
        url += f"&industry={quote(industry)}"
    return url


def _review_apply_url(
    report_dir: str | Path,
    *,
    field_key: str,
    action: str,
    industry: str | None = None,
    notes: str | None = None,
) -> str:
    url = (
        f"/review/apply-ui?report_dir={quote(str(report_dir))}"
        f"&field_key={quote(field_key)}"
        f"&action={quote(action)}"
        "&reviewer=dashboard"
    )
    if industry:
        url += f"&industry={quote(industry)}"
    if notes:
        url += f"&notes={quote(notes)}"
    return url


def _review_evidence_url(
    report_dir: str | Path,
    *,
    field_key: str,
    industry: str | None = None,
) -> str:
    url = f"/review/evidence?report_dir={quote(str(report_dir))}&field_key={quote(field_key)}"
    if industry:
        url += f"&industry={quote(industry)}"
    return url


def _page_image_path(report_dir: str | Path, page_number: Any) -> Path | None:
    if page_number in (None, ""):
        return None
    page_text = str(page_number).strip()
    candidates = [
        Path(report_dir) / "page_images" / f"page_{page_text}.png",
        Path(report_dir) / f"page_{page_text}.png",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate
    return None


def _page_image_url(report_dir: str | Path, page_number: Any) -> str | None:
    if _page_image_path(report_dir, page_number) is None:
        return None
    return f"/reports/page-image?report_dir={quote(str(report_dir))}&page_number={quote(str(page_number))}"


def _load_chunk_text(report_dir: str | Path, chunk_id: str) -> str:
    if not chunk_id:
        return ""
    chunks = _read_json_if_exists(Path(report_dir) / "route_b_chunks.json", [])
    if not isinstance(chunks, list):
        return ""
    for chunk in chunks:
        if isinstance(chunk, dict) and str(chunk.get("chunk_id") or "") == chunk_id:
            return str(chunk.get("text") or "")
    return ""


def _find_review_item(report_dir: str | Path, field_key: str) -> Dict[str, Any] | None:
    for item in load_review_queue(report_dir):
        if str(item.get("field_key") or "") == field_key:
            return item
    citations = _read_json_if_exists(Path(report_dir) / "field_citations.json", [])
    if isinstance(citations, list):
        for item in citations:
            if isinstance(item, dict) and str(item.get("field_key") or "") == field_key:
                return item
    return None


def _build_correction_from_query(
    *,
    value: str | None = None,
    unit: str | None = None,
    year: int | None = None,
    evidence: str | None = None,
    page_number: int | None = None,
    chunk_id: str | None = None,
    confidence: str | None = None,
) -> Dict[str, Any]:
    correction: Dict[str, Any] = {}
    if value not in (None, ""):
        correction["value"] = value
        correction["status"] = "extracted"
    if unit:
        correction["unit"] = unit
    if year is not None:
        correction["year"] = year
    if evidence:
        correction["evidence"] = evidence
        correction["citation_text_excerpt"] = evidence[:240]
    if page_number is not None:
        correction["citation_page_number"] = page_number
    if chunk_id:
        correction["citation_chunk_id"] = chunk_id
    if confidence:
        correction["confidence"] = confidence
    return correction


def _persist_review_rating_run(
    report_dir: Path,
    *,
    field_key: str,
    action: str,
    source: str,
) -> str | None:
    rating_path = report_dir / "simulated_rating.json"
    if not rating_path.exists():
        return None
    rating = read_citation_json(rating_path)
    rating_record = create_rating_record(
        rating_result=rating,
        report_dir=str(report_dir),
        metadata={
            "source": source,
            "field_key": field_key,
            "action": action,
        },
    )
    return rating_record["id"]


def render_review_html(summary: Dict[str, Any], *, industry: str | None = None) -> str:
    report_dir = summary["report_dir"]
    report_name = summary["report_name"]
    rating_summary = summary["rating_summary"]
    review_items = load_review_queue(report_dir)
    dashboard_url = f"/dashboard?report_dir={quote(report_dir)}"
    if industry:
        dashboard_url += f"&industry={quote(industry)}"

    if review_items:
        item_cards = "".join(
            _render_review_item_html(item, report_dir=report_dir, industry=industry)
            for item in review_items
        )
    else:
        item_cards = """
        <section class="empty">
          <h2>当前没有待审核字段</h2>
          <p>所有字段都已经自动通过、人工通过或人工拒绝。你可以回到 Dashboard 查看最新评分。</p>
        </section>
        """

    return f"""
    <!doctype html>
    <html lang="zh-CN">
    <head>
      <meta charset="utf-8">
      <title>ESG 字段审核</title>
      <style>
        :root {{
          color-scheme: light;
          --bg: #f6f7f9;
          --panel: #ffffff;
          --text: #172033;
          --muted: #667085;
          --line: #d8dee8;
          --green: #1f7a45;
          --red: #b42318;
          --blue: #1d4ed8;
        }}
        * {{ box-sizing: border-box; }}
        body {{
          margin: 0;
          background: var(--bg);
          color: var(--text);
          font-family: "Microsoft YaHei", Arial, sans-serif;
        }}
        main {{
          max-width: 1180px;
          margin: 0 auto;
          padding: 28px 20px 44px;
        }}
        header {{
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 20px;
          margin-bottom: 18px;
        }}
        h1 {{ margin: 0 0 8px; font-size: 28px; }}
        h2 {{ margin: 0 0 10px; font-size: 18px; }}
        p {{ margin: 0; color: var(--muted); line-height: 1.6; }}
        .back {{
          color: var(--blue);
          text-decoration: none;
          font-weight: 700;
          white-space: nowrap;
        }}
        .stats {{
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
          gap: 12px;
          margin: 18px 0 20px;
        }}
        .stat, .item, .empty {{
          background: var(--panel);
          border: 1px solid var(--line);
          border-radius: 8px;
          padding: 16px;
        }}
        .label {{ color: var(--muted); font-size: 13px; margin-bottom: 6px; }}
        .value {{ font-size: 24px; font-weight: 800; }}
        .item {{ margin-bottom: 14px; }}
        .meta {{
          display: grid;
          grid-template-columns: minmax(170px, 1fr) minmax(130px, 0.8fr) minmax(150px, 1fr);
          gap: 10px;
          margin-bottom: 12px;
        }}
        .excerpt {{
          border-left: 4px solid var(--line);
          background: #fafbfc;
          padding: 10px 12px;
          color: #344054;
          line-height: 1.65;
          margin: 10px 0 14px;
          white-space: pre-wrap;
        }}
        .evidenceTools {{
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
          margin: 8px 0 12px;
        }}
        .evidenceTools a {{
          color: var(--blue);
          font-weight: 700;
          text-decoration: none;
          font-size: 14px;
        }}
        details.evidence {{
          margin: 10px 0 14px;
        }}
        details.evidence summary {{
          cursor: pointer;
          color: var(--blue);
          font-weight: 800;
          margin-bottom: 8px;
        }}
        .fullEvidence {{
          max-height: 420px;
          overflow: auto;
          border: 1px solid var(--line);
          border-radius: 8px;
          background: #ffffff;
          padding: 12px;
          color: #1f2937;
          line-height: 1.75;
          white-space: pre-wrap;
          word-break: break-word;
        }}
        .actions {{
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
          align-items: center;
          margin-bottom: 14px;
        }}
        .btn {{
          display: inline-flex;
          align-items: center;
          min-height: 36px;
          padding: 8px 12px;
          border-radius: 6px;
          text-decoration: none;
          color: #fff;
          font-weight: 700;
          border: 0;
          cursor: pointer;
        }}
        .approve {{ background: var(--green); }}
        .reject {{ background: var(--red); }}
        .correct {{ background: var(--blue); }}
        form {{
          display: grid;
          grid-template-columns: 1fr 0.7fr 0.55fr 1.3fr auto;
          gap: 8px;
          align-items: end;
          padding-top: 12px;
          border-top: 1px solid var(--line);
        }}
        input {{
          width: 100%;
          min-height: 36px;
          border: 1px solid var(--line);
          border-radius: 6px;
          padding: 7px 9px;
          font: inherit;
        }}
        .field label {{
          display: block;
          color: var(--muted);
          font-size: 12px;
          margin-bottom: 4px;
        }}
        @media (max-width: 860px) {{
          header {{ display: block; }}
          .back {{ display: inline-block; margin-top: 10px; }}
          .meta, form {{ grid-template-columns: 1fr; }}
        }}
      </style>
    </head>
    <body>
      <main>
        <header>
          <div>
            <h1>ESG 字段审核</h1>
            <p>{escape(report_name)}</p>
          </div>
          <a class="back" href="{dashboard_url}">返回 Dashboard</a>
        </header>
        <section class="stats">
          <div class="stat"><div class="label">当前评分</div><div class="value">{escape(str(rating_summary.get("score", "")))}</div></div>
          <div class="stat"><div class="label">当前评级</div><div class="value">{escape(str(rating_summary.get("rating", "")))}</div></div>
          <div class="stat"><div class="label">待审核字段</div><div class="value">{len(review_items)}</div></div>
          <div class="stat"><div class="label">已评分字段</div><div class="value">{escape(str(rating_summary.get("scored_field_count", "")))}</div></div>
        </section>
        {item_cards}
      </main>
    </body>
    </html>
    """


def _render_review_item_html(
    item: Dict[str, Any],
    *,
    report_dir: str,
    industry: str | None = None,
) -> str:
    field_key = str(item.get("field_key") or "")
    field_name = str(item.get("field_name_cn") or "")
    page = item.get("citation_page_number") or ""
    chunk_id = str(item.get("citation_chunk_id") or "")
    reasons = "; ".join(str(reason) for reason in item.get("citation_review_reasons", []))
    excerpt = str(item.get("text_excerpt") or item.get("citation_text_excerpt") or "")
    full_evidence = _load_chunk_text(report_dir, chunk_id) or excerpt
    recommended_action = str(item.get("recommended_action") or "")
    evidence_url = _review_evidence_url(report_dir, field_key=field_key, industry=industry)
    page_image_url = _page_image_url(report_dir, page)
    image_link = (
        f'<a href="{page_image_url}" target="_blank" rel="noreferrer">打开页面截图</a>'
        if page_image_url
        else ""
    )
    approve_url = _review_apply_url(
        report_dir,
        field_key=field_key,
        action="approve",
        industry=industry,
        notes="dashboard approve",
    )
    reject_url = _review_apply_url(
        report_dir,
        field_key=field_key,
        action="reject",
        industry=industry,
        notes="dashboard reject",
    )
    return f"""
    <section class="item">
      <h2>{escape(field_name)} <span class="label">({escape(field_key)})</span></h2>
      <div class="meta">
        <div><div class="label">证据页 / Chunk</div><div>{escape(str(page))} / {escape(chunk_id)}</div></div>
        <div><div class="label">审核原因</div><div>{escape(reasons)}</div></div>
        <div><div class="label">建议动作</div><div>{escape(recommended_action)}</div></div>
      </div>
      <div class="evidenceTools">
        <a href="{evidence_url}" target="_blank" rel="noreferrer">单独打开证据</a>
        {image_link}
      </div>
      <div class="excerpt">{escape(excerpt)}</div>
      <details class="evidence" open>
        <summary>完整证据文本</summary>
        <div class="fullEvidence">{escape(full_evidence)}</div>
      </details>
      <div class="actions">
        <a class="btn approve" href="{approve_url}">接受</a>
        <a class="btn reject" href="{reject_url}">拒绝</a>
      </div>
      <form method="get" action="/review/apply-ui">
        <input type="hidden" name="report_dir" value="{escape(report_dir)}">
        <input type="hidden" name="field_key" value="{escape(field_key)}">
        <input type="hidden" name="action" value="correct">
        <input type="hidden" name="industry" value="{escape(industry or "")}">
        <input type="hidden" name="reviewer" value="dashboard">
        <div class="field"><label>补充值</label><input name="value" placeholder="例如 25.12"></div>
        <div class="field"><label>单位</label><input name="unit" placeholder="例如 万吨"></div>
        <div class="field"><label>年份</label><input name="year" placeholder="2024"></div>
        <div class="field"><label>证据摘录</label><input name="evidence" placeholder="粘贴报告中的原文证据"></div>
        <button class="btn correct" type="submit">补充数值并通过</button>
      </form>
    </section>
    """


def render_dashboard_html(summary: Dict[str, Any]) -> str:
    rating_summary = summary["rating_summary"]
    citation_summary = summary["citation_summary"]
    pillar_scores = rating_summary.get("pillar_scores") or {}
    review_items = summary["review_queue"]["items"]
    rating_runs = summary["rating_runs"]
    review_url = _review_url(summary["report_dir"])

    pillar_rows = "".join(
        "<tr>"
        f"<td>{escape(str(pillar))}</td>"
        f"<td>{escape(str(score.get('score', '')))}</td>"
        f"<td>{escape(str(score.get('rating', '')))}</td>"
        f"<td>{escape(str(score.get('coverage', '')))}</td>"
        f"<td>{escape(str(score.get('needs_review_count', '')))}</td>"
        "</tr>"
        for pillar, score in pillar_scores.items()
    )
    review_rows = "".join(
        "<tr>"
        f"<td>{escape(str(item.get('field_key', '')))}</td>"
        f"<td>{escape(str(item.get('field_name_cn', '')))}</td>"
        f"<td>{escape(str(item.get('citation_page_number', '')))}</td>"
        f"<td>{escape(str(item.get('citation_chunk_id', '')))}</td>"
        f"<td>{escape(';'.join(item.get('citation_review_reasons', [])))}</td>"
        "</tr>"
        for item in review_items
    )
    run_rows = "".join(
        "<tr>"
        f"<td>{escape(str(run.get('id', '')))}</td>"
        f"<td>{escape(str(run.get('overall_score', '')))}</td>"
        f"<td>{escape(str(run.get('overall_rating', '')))}</td>"
        f"<td>{escape(str(run.get('created_at', '')))}</td>"
        "</tr>"
        for run in rating_runs
    )

    return f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>ESG Rating Agent Dashboard</title>
  <style>
    body {{ font-family: Arial, "Microsoft YaHei", sans-serif; margin: 24px; color: #1f2937; background: #f8fafc; }}
    h1 {{ font-size: 24px; margin-bottom: 4px; }}
    h2 {{ font-size: 17px; margin-top: 28px; }}
    .muted {{ color: #64748b; font-size: 13px; }}
    .headerRow {{ display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; }}
    .reviewButton {{ display: inline-flex; align-items: center; min-height: 36px; padding: 8px 12px; color: #ffffff; background: #13705c; border-radius: 6px; text-decoration: none; font-weight: 700; font-size: 14px; white-space: nowrap; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(140px, 1fr)); gap: 12px; margin-top: 18px; }}
    .card {{ background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px; }}
    .label {{ color: #64748b; font-size: 12px; margin-bottom: 8px; }}
    .value {{ font-size: 22px; font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #e5e7eb; }}
    th, td {{ text-align: left; padding: 9px 10px; border-bottom: 1px solid #e5e7eb; font-size: 13px; vertical-align: top; }}
    th {{ background: #f1f5f9; color: #334155; }}
    code {{ background: #e2e8f0; padding: 2px 5px; border-radius: 4px; }}
  </style>
</head>
<body>
  <div class="headerRow">
    <div>
      <h1>ESG Rating Agent Dashboard</h1>
      <div class="muted">{escape(summary["report_name"])}</div>
      <div class="muted"><code>{escape(summary["report_dir"])}</code></div>
    </div>
    <a class="reviewButton" href="{review_url}">人工审核</a>
  </div>

  <div class="grid">
    <div class="card"><div class="label">模拟总分</div><div class="value">{escape(str(rating_summary.get("score", "")))}</div></div>
    <div class="card"><div class="label">模拟等级</div><div class="value">{escape(str(rating_summary.get("rating", "")))}</div></div>
    <div class="card"><div class="label">自动证据字段</div><div class="value">{citation_summary["auto_cited_count"]}/{citation_summary["field_count"]}</div></div>
    <div class="card"><div class="label">待人审字段</div><div class="value">{summary["review_queue"]["count"]}</div></div>
  </div>

  <h2>E/S/G 评分</h2>
  <table>
    <thead><tr><th>支柱</th><th>分数</th><th>等级</th><th>覆盖率</th><th>待审数</th></tr></thead>
    <tbody>{pillar_rows}</tbody>
  </table>

  <h2>待人审队列 Top 10</h2>
  <table>
    <thead><tr><th>字段</th><th>名称</th><th>页码</th><th>Chunk</th><th>原因</th></tr></thead>
    <tbody>{review_rows}</tbody>
  </table>

  <h2>最近评分历史</h2>
  <table>
    <thead><tr><th>Rating Run ID</th><th>分数</th><th>等级</th><th>时间</th></tr></thead>
    <tbody>{run_rows}</tbody>
  </table>
</body>
</html>
"""


def render_home_html() -> str:
    reports_root = Path("output") / "reports"
    report_links = []
    if reports_root.exists():
        report_dirs = sorted(
            (path for path in reports_root.iterdir() if path.is_dir()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for report_dir in report_dirs:
            has_results = (report_dir / "field_citations.json").exists() or (report_dir / "simulated_rating.json").exists()
            has_uploaded_pdf = any(report_dir.glob("*.pdf"))
            if has_results or has_uploaded_pdf:
                href = f"/dashboard?report_dir={quote(str(report_dir))}"
                status = "已生成结果" if has_results else "已上传，待分析"
                report_links.append(
                    f'<li><a href="{href}">{escape(report_dir.name)}</a> '
                    f'<span class="muted">({status})</span></li>'
                )

    links_html = "\n".join(report_links) or "<li>还没有找到已生成评分结果的报告目录。</li>"
    return f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>ESG Agent Backend</title>
  <style>
    body {{ font-family: Arial, "Microsoft YaHei", sans-serif; margin: 24px; color: #1f2937; background: #f8fafc; }}
    h1 {{ font-size: 24px; margin-bottom: 6px; }}
    h2 {{ font-size: 17px; margin-top: 0; }}
    .muted {{ color: #64748b; font-size: 13px; margin-bottom: 18px; }}
    .panel {{ background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; max-width: 980px; }}
    li {{ margin: 10px 0; }}
    a {{ color: #2563eb; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    code {{ background: #e2e8f0; padding: 2px 5px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>ESG Agent Backend</h1>
  <div class="muted">服务已启动。API 健康检查：<code>/health</code></div>
  <div class="panel">
    <h2>可打开的 Dashboard</h2>
    <ul>{links_html}</ul>
  </div>
</body>
</html>
"""


def render_dashboard_html(summary: Dict[str, Any]) -> str:
    rating_summary = summary["rating_summary"]
    citation_summary = summary["citation_summary"]
    pillar_scores = rating_summary.get("pillar_scores") or {}
    review_items = summary["review_queue"]["items"]
    rating_runs = summary["rating_runs"]
    review_url = _review_url(summary["report_dir"])

    pillar_rows = "".join(
        "<tr>"
        f"<td>{escape(str(pillar))}</td>"
        f"<td>{escape(str(score.get('score', '')))}</td>"
        f"<td>{escape(str(score.get('rating', '')))}</td>"
        f"<td>{escape(str(score.get('coverage', '')))}</td>"
        f"<td>{escape(str(score.get('needs_review_count', '')))}</td>"
        "</tr>"
        for pillar, score in pillar_scores.items()
    )
    review_rows = "".join(
        "<tr>"
        f"<td>{escape(str(item.get('field_key', '')))}</td>"
        f"<td>{escape(str(item.get('field_name_cn', '')))}</td>"
        f"<td>{escape(str(item.get('citation_page_number', '')))}</td>"
        f"<td>{escape(str(item.get('citation_chunk_id', '')))}</td>"
        f"<td>{escape(';'.join(item.get('citation_review_reasons', [])))}</td>"
        "</tr>"
        for item in review_items
    )
    run_rows = "".join(
        "<tr>"
        f"<td>{escape(str(run.get('id', '')))}</td>"
        f"<td>{escape(str(run.get('overall_score', '')))}</td>"
        f"<td>{escape(str(run.get('overall_rating', '')))}</td>"
        f"<td>{escape(str(run.get('created_at', '')))}</td>"
        "</tr>"
        for run in rating_runs
    )

    return f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>ESG Rating Agent Dashboard</title>
  <style>
    body {{ font-family: Arial, "Microsoft YaHei", sans-serif; margin: 24px; color: #1f2937; background: #f8fafc; }}
    h1 {{ font-size: 24px; margin-bottom: 4px; }}
    h2 {{ font-size: 17px; margin-top: 28px; }}
    .muted {{ color: #64748b; font-size: 13px; }}
    .headerRow {{ display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; }}
    .reviewButton {{ display: inline-flex; align-items: center; min-height: 36px; padding: 8px 12px; color: #ffffff; background: #13705c; border-radius: 6px; text-decoration: none; font-weight: 700; font-size: 14px; white-space: nowrap; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(140px, 1fr)); gap: 12px; margin-top: 18px; }}
    .card {{ background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 14px; }}
    .label {{ color: #64748b; font-size: 12px; margin-bottom: 8px; }}
    .value {{ font-size: 22px; font-weight: 700; }}
    table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #e5e7eb; }}
    th, td {{ text-align: left; padding: 9px 10px; border-bottom: 1px solid #e5e7eb; font-size: 13px; vertical-align: top; }}
    th {{ background: #f1f5f9; color: #334155; }}
    code {{ background: #e2e8f0; padding: 2px 5px; border-radius: 4px; }}
  </style>
</head>
<body>
  <div class="headerRow">
    <div>
      <h1>ESG Rating Agent Dashboard</h1>
      <div class="muted">{escape(summary["report_name"])}</div>
      <div class="muted"><code>{escape(summary["report_dir"])}</code></div>
    </div>
    <a class="reviewButton" href="{review_url}">人工审核</a>
  </div>

  <div class="grid">
    <div class="card"><div class="label">模拟总分</div><div class="value">{escape(str(rating_summary.get("score", "")))}</div></div>
    <div class="card"><div class="label">模拟等级</div><div class="value">{escape(str(rating_summary.get("rating", "")))}</div></div>
    <div class="card"><div class="label">自动证据字段</div><div class="value">{citation_summary["auto_cited_count"]}/{citation_summary["field_count"]}</div></div>
    <div class="card"><div class="label">待人审字段</div><div class="value">{summary["review_queue"]["count"]}</div></div>
  </div>

  <h2>E/S/G 评分</h2>
  <table>
    <thead><tr><th>支柱</th><th>分数</th><th>等级</th><th>覆盖率</th><th>待审数</th></tr></thead>
    <tbody>{pillar_rows}</tbody>
  </table>

  <h2>待人审队列 Top 10</h2>
  <table>
    <thead><tr><th>字段</th><th>名称</th><th>页码</th><th>Chunk</th><th>原因</th></tr></thead>
    <tbody>{review_rows}</tbody>
  </table>

  <h2>最近评分历史</h2>
  <table>
    <thead><tr><th>Rating Run ID</th><th>分数</th><th>等级</th><th>时间</th></tr></thead>
    <tbody>{run_rows}</tbody>
  </table>
</body>
</html>
"""


def render_home_html() -> str:
    reports_root = Path("output") / "reports"
    report_links = []
    if reports_root.exists():
        report_dirs = sorted(
            (path for path in reports_root.iterdir() if path.is_dir()),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for report_dir in report_dirs:
            has_results = (report_dir / "field_citations.json").exists() or (report_dir / "simulated_rating.json").exists()
            has_uploaded_pdf = any(report_dir.glob("*.pdf"))
            if has_results or has_uploaded_pdf:
                href = f"/dashboard?report_dir={quote(str(report_dir))}"
                status = "已生成结果" if has_results else "已上传，待分析"
                report_links.append(
                    f'<li><a href="{href}">{escape(report_dir.name)}</a> '
                    f'<span class="muted">({status})</span></li>'
                )

    links_html = "\n".join(report_links) or "<li>还没有找到已生成评分结果的报告目录。</li>"
    return f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>ESG Agent Backend</title>
  <style>
    body {{ font-family: Arial, "Microsoft YaHei", sans-serif; margin: 24px; color: #1f2937; background: #f8fafc; }}
    h1 {{ font-size: 24px; margin-bottom: 6px; }}
    h2 {{ font-size: 17px; margin-top: 0; }}
    .muted {{ color: #64748b; font-size: 13px; margin-bottom: 18px; }}
    .panel {{ background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; max-width: 980px; }}
    li {{ margin: 10px 0; }}
    a {{ color: #2563eb; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    code {{ background: #e2e8f0; padding: 2px 5px; border-radius: 4px; }}
  </style>
</head>
<body>
  <h1>ESG Agent Backend</h1>
  <div class="muted">服务已启动，API 健康检查：<code>/health</code></div>
  <div class="panel">
    <h2>可打开的 Dashboard</h2>
    <ul>{links_html}</ul>
  </div>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
def home() -> HTMLResponse:
    return HTMLResponse(render_home_html())


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.get("/reports/summary")
def report_summary_endpoint(report_dir: str) -> Dict[str, Any]:
    return build_report_summary(Path(report_dir))


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_endpoint(report_dir: str) -> HTMLResponse:
    return HTMLResponse(render_dashboard_html(build_report_summary(Path(report_dir))))


@app.get("/review", response_class=HTMLResponse)
def review_page_endpoint(report_dir: str, industry: Optional[str] = None) -> HTMLResponse:
    return HTMLResponse(render_review_html(build_report_summary(Path(report_dir)), industry=industry))


@app.get("/review/evidence", response_class=HTMLResponse)
def review_evidence_endpoint(
    report_dir: str,
    field_key: str,
    industry: Optional[str] = None,
) -> HTMLResponse:
    report_path = Path(report_dir)
    if not report_path.exists() or not report_path.is_dir():
        raise HTTPException(status_code=404, detail="report_dir not found")
    item = _find_review_item(report_path, field_key)
    if item is None:
        raise HTTPException(status_code=404, detail="review item not found")

    chunk_id = str(item.get("citation_chunk_id") or "")
    page = item.get("citation_page_number") or ""
    excerpt = str(item.get("text_excerpt") or item.get("citation_text_excerpt") or "")
    full_evidence = _load_chunk_text(report_path, chunk_id) or excerpt
    page_image_url = _page_image_url(report_path, page)
    image_html = (
        f'<img src="{page_image_url}" alt="page {escape(str(page))}">'
        if page_image_url
        else '<p class="muted">未找到对应页面截图。</p>'
    )
    back_url = _review_url(report_path, industry=industry)

    return HTMLResponse(
        f"""
<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>人工审核证据</title>
  <style>
    body {{ margin: 0; background: #f6f7f9; color: #172033; font-family: "Microsoft YaHei", Arial, sans-serif; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 28px 20px 44px; }}
    header {{ display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; margin-bottom: 16px; }}
    h1 {{ margin: 0 0 8px; font-size: 24px; }}
    .muted {{ color: #667085; line-height: 1.6; }}
    a {{ color: #1d4ed8; font-weight: 700; text-decoration: none; }}
    .panel {{ background: #ffffff; border: 1px solid #d8dee8; border-radius: 8px; padding: 16px; margin-bottom: 16px; }}
    .evidence {{ max-height: 70vh; overflow: auto; white-space: pre-wrap; word-break: break-word; line-height: 1.75; }}
    img {{ display: block; max-width: 100%; height: auto; border: 1px solid #d8dee8; border-radius: 8px; background: #ffffff; }}
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>{escape(str(item.get("field_name_cn") or field_key))}</h1>
        <div class="muted">字段：{escape(field_key)} | 页码：{escape(str(page))} | Chunk：{escape(chunk_id)}</div>
      </div>
      <a href="{back_url}">返回人工审核</a>
    </header>
    <section class="panel evidence">{escape(full_evidence)}</section>
    <section class="panel">{image_html}</section>
  </main>
</body>
</html>
"""
    )


@app.get("/reports/page-image")
def report_page_image_endpoint(report_dir: str, page_number: str) -> FileResponse:
    report_path = Path(report_dir)
    if not report_path.exists() or not report_path.is_dir():
        raise HTTPException(status_code=404, detail="report_dir not found")
    image_path = _page_image_path(report_path, page_number)
    if image_path is None:
        raise HTTPException(status_code=404, detail="page image not found")
    try:
        image_path.resolve().relative_to(report_path.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid page image path") from exc
    return FileResponse(image_path)


@app.get("/review/apply-ui")
def apply_review_from_page_endpoint(
    report_dir: str,
    field_key: str,
    action: str,
    industry: Optional[str] = None,
    reviewer: Optional[str] = "dashboard",
    notes: Optional[str] = None,
    value: Optional[str] = None,
    unit: Optional[str] = None,
    year: Optional[int] = None,
    evidence: Optional[str] = None,
    page_number: Optional[int] = None,
    chunk_id: Optional[str] = None,
    confidence: Optional[str] = None,
) -> RedirectResponse:
    report_path = Path(report_dir)
    if not report_path.exists() or not report_path.is_dir():
        raise HTTPException(status_code=404, detail="report_dir not found")
    correction = _build_correction_from_query(
        value=value,
        unit=unit,
        year=year,
        evidence=evidence,
        page_number=page_number,
        chunk_id=chunk_id,
        confidence=confidence,
    )
    try:
        apply_review_decision(
            report_path,
            field_key=field_key,
            action=action,
            industry=industry,
            reviewer=reviewer,
            notes=notes,
            correction=correction,
        )
        _persist_review_rating_run(
            report_path,
            field_key=field_key,
            action=action,
            source="review_page_endpoint",
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(url=_review_url(report_path, industry=industry), status_code=303)


@app.post("/reports")
def create_report_endpoint(payload: ReportCreate) -> Dict[str, Any]:
    return create_report(**dump_model(payload))


@app.post("/reports/upload")
async def upload_report_endpoint(request: Request) -> Dict[str, Any]:
    parsed = parse_multipart_upload(await request.body(), request.headers.get("content-type", ""))
    form = parsed["fields"]
    uploaded_file = parsed["file"]
    if uploaded_file is None:
        raise HTTPException(status_code=400, detail="file is required")

    file_name = str(uploaded_file["filename"] or "").strip()
    if not file_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="only PDF files are supported")

    industry = str(form.get("industry") or "").strip() or None
    company_name = str(form.get("company_name") or "").strip() or None
    report_year_raw = str(form.get("report_year") or "").strip()
    report_year = int(report_year_raw) if report_year_raw.isdigit() else None
    retrieval_profile = str(form.get("retrieval_profile") or "baseline").strip() or "baseline"
    schema_version = str(form.get("schema_version") or SCHEMA_VERSION).strip() or SCHEMA_VERSION

    stem = safe_upload_stem(file_name)
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
    raw_path = RAW_DATA_DIR / f"{stem}.pdf"
    if raw_path.exists():
        index = 2
        while True:
            candidate = RAW_DATA_DIR / f"{stem}_{index}.pdf"
            if not candidate.exists():
                raw_path = candidate
                break
            index += 1

    report_dir = next_report_dir(raw_path.stem)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_pdf_path = report_dir / raw_path.name

    try:
        raw_path.write_bytes(uploaded_file["content"])
        shutil.copy2(raw_path, report_pdf_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"failed to save upload: {exc}") from exc

    report = create_report(
        file_name=file_name,
        file_path=str(raw_path),
        company_name=company_name,
        report_year=report_year,
        industry=industry,
        metadata={
            "source_type": "uploaded_pdf",
            "report_dir": str(report_dir),
            "report_pdf_path": str(report_pdf_path),
        },
    )
    task = create_task(
        report_id=report["id"],
        industry=industry,
        schema_version=schema_version,
        retrieval_profile=retrieval_profile,
        metadata={
            "source_type": "uploaded_pdf",
            "report_dir": str(report_dir),
            "raw_pdf_path": str(raw_path),
        },
    )

    return {
        "report": report,
        "task": task,
        "report_dir": str(report_dir),
        "raw_pdf_path": str(raw_path),
        "next": {
            "run_url": "/runs/report-dir",
            "trace_url": f"/tasks/{task['id']}/trace",
        },
    }


@app.post("/tasks")
def create_task_endpoint(payload: TaskCreate) -> Dict[str, Any]:
    return create_task(**dump_model(payload))


@app.get("/tasks")
def list_tasks_endpoint(limit: int = 50) -> Dict[str, Any]:
    return {"items": list_tasks(limit=limit)}


@app.get("/tasks/{task_id}")
def get_task_endpoint(task_id: str) -> Dict[str, Any]:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@app.patch("/tasks/{task_id}/status")
def update_task_status_endpoint(task_id: str, payload: TaskStatusUpdate) -> Dict[str, Any]:
    task = update_task_status(task_id, payload.status)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@app.get("/tasks/{task_id}/trace")
def get_task_trace_endpoint(task_id: str) -> Dict[str, Any]:
    trace = get_task_trace(task_id)
    if trace["task"] is None:
        raise HTTPException(status_code=404, detail="task not found")
    return trace


@app.get("/tasks/{task_id}/review-items")
def list_task_review_items_endpoint(task_id: str) -> Dict[str, Any]:
    task = get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return {"items": list_review_items(task_id=task_id)}


@app.post("/rating/review-queue")
def rating_review_queue_endpoint(payload: RatingReviewQueueRequest) -> Dict[str, Any]:
    report_dir = Path(payload.report_dir)
    if not report_dir.exists() or not report_dir.is_dir():
        raise HTTPException(status_code=404, detail="report_dir not found")
    items = load_review_queue(report_dir)
    return {"items": items, "count": len(items)}


@app.post("/rating/review-items/apply")
def apply_rating_review_endpoint(payload: RatingReviewApplyRequest) -> Dict[str, Any]:
    report_dir = Path(payload.report_dir)
    if not report_dir.exists() or not report_dir.is_dir():
        raise HTTPException(status_code=404, detail="report_dir not found")
    try:
        result = apply_review_decision(
            report_dir,
            field_key=payload.field_key,
            action=payload.action,
            industry=payload.industry,
            reviewer=payload.reviewer,
            notes=payload.notes,
            correction=payload.correction,
        )
        rating = read_citation_json(report_dir / "simulated_rating.json")
        rating_record = create_rating_record(
            rating_result=rating,
            report_dir=str(report_dir),
            metadata={
                "source": "rating_review_apply_endpoint",
                "field_key": payload.field_key,
                "action": payload.action,
            },
        )
        result["rating"]["rating_run_id"] = rating_record["id"]
        return result
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/rating/recalculate")
def recalculate_rating_endpoint(payload: RatingRecalculateRequest) -> Dict[str, Any]:
    report_dir = Path(payload.report_dir)
    if not report_dir.exists() or not report_dir.is_dir():
        raise HTTPException(status_code=404, detail="report_dir not found")
    rating = recalculate_rating(report_dir, industry=payload.industry)
    rating_record = create_rating_record(
        rating_result=rating,
        report_dir=str(report_dir),
        metadata={"source": "rating_recalculate_endpoint"},
    )
    return {
        "score": rating["overall"]["score"],
        "rating": rating["overall"]["rating"],
        "needs_review_count": rating["overall"]["needs_review_count"],
        "rating_run_id": rating_record["id"],
        "rating_path": str(report_dir / "simulated_rating.json"),
        "review_queue_path": str(report_dir / "rating_review_queue.json"),
    }


@app.get("/rating/runs")
def list_rating_runs_endpoint(
    report_dir: Optional[str] = None,
    task_id: Optional[str] = None,
    limit: int = 20,
) -> Dict[str, Any]:
    items = list_rating_runs(report_dir=report_dir, task_id=task_id, limit=limit)
    return {"items": items, "count": len(items)}


@app.get("/rating/runs/{rating_run_id}")
def get_rating_run_endpoint(rating_run_id: str) -> Dict[str, Any]:
    rating_run = get_rating_run(rating_run_id)
    if rating_run is None:
        raise HTTPException(status_code=404, detail="rating_run not found")
    return rating_run


@app.post("/runs/analyze-uploaded-report")
def analyze_uploaded_report_endpoint(payload: AnalyzeUploadedReportRequest) -> Dict[str, Any]:
    report_dir = Path(payload.report_dir)
    if not report_dir.exists() or not report_dir.is_dir():
        raise HTTPException(status_code=404, detail="report_dir not found")

    pdf_path = Path(payload.pdf_path) if payload.pdf_path else None
    if pdf_path is None or not pdf_path.exists():
        pdf_candidates = sorted(report_dir.glob("*.pdf"))
        if not pdf_candidates:
            raise HTTPException(status_code=400, detail="uploaded PDF not found in report_dir")
        pdf_path = pdf_candidates[0]

    if payload.task_id:
        update_task_status(payload.task_id, "running")

    try:
        unified_summary = UnifiedESGPipeline(report_dir).run(pdf_path)

        artifacts = generate_report_artifacts(report_dir, industry=payload.industry)

        if payload.task_id:
            update_task_status(payload.task_id, "completed")

        return {
            "status": "completed",
            "report_dir": str(report_dir),
            "pdf_path": str(pdf_path),
            "unified_pipeline": unified_summary,
            "route_a": unified_summary["visual_extraction"],
            "route_b": unified_summary["extraction"],
            "route_b2": unified_summary["extraction"].get("quantitative_fallback", {}),
            "merge": unified_summary["merge"],
            "artifacts": artifacts,
            "dashboard_url": f"/dashboard?report_dir={quote(str(report_dir))}",
            "review_url": _review_url(report_dir, industry=payload.industry),
        }
    except Exception as exc:
        if payload.task_id:
            update_task_status(payload.task_id, "failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/runs/report-dir")
def run_report_dir_endpoint(payload: RunReportDirRequest) -> Dict[str, Any]:
    report_dir = Path(payload.report_dir)
    if not report_dir.exists() or not report_dir.is_dir():
        raise HTTPException(status_code=404, detail="report_dir not found")

    result = ESGRatingDataHarness(
        report_dir=report_dir,
        industry=payload.industry,
        allow_route_b=payload.allow_route_b,
        expected_core_fields=payload.expected_core_fields,
        retrieval_profile=payload.retrieval_profile,
        schema_version=payload.schema_version,
        metadata=payload.metadata,
    ).run()
    artifacts = None
    if payload.generate_citations or payload.generate_rating:
        artifacts = generate_report_artifacts(report_dir, industry=payload.industry)

    response = {
        "task_id": result["backend_task_id"],
        "report_id": result["backend_report_id"],
        "status": result["backend_task_status"],
        "report_name": result.get("report_name"),
        "ok": result.get("ok"),
        "review_needed": result.get("review_needed"),
        "review_item_count": result.get("review_item_count", 0),
        "trace_url": f"/tasks/{result['backend_task_id']}/trace",
    }
    if artifacts:
        response["artifacts"] = artifacts
    return response
