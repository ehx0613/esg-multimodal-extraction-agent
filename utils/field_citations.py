from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from config.schema import ESG_SCHEMA
from utils.hybrid_retriever import retrieve_hybrid_chunks


PAGE_NUMBER_RE = re.compile(r"page[_\s-]*(\d+)", re.IGNORECASE)


def read_json(path: str | Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_source_pages(value: Any) -> List[int]:
    if value in (None, ""):
        return []

    if isinstance(value, list):
        values = value
    else:
        text = str(value).strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            values = parsed if isinstance(parsed, list) else [parsed]
        except Exception:
            values = [text]

    pages: List[int] = []
    for item in values:
        if isinstance(item, int):
            pages.append(item)
            continue
        text = str(item)
        match = PAGE_NUMBER_RE.search(text)
        if match:
            pages.append(int(match.group(1)))
            continue
        if text.isdigit():
            pages.append(int(text))
    return sorted(set(pages))


def choose_existing_evidence(row: Dict[str, Any]) -> str:
    for key in ("evidence", "route_b_evidence", "route_b2_evidence", "evidence_text"):
        value = str(row.get(key, "") or "").strip()
        if value:
            return value
    return ""


def choose_source_pages(row: Dict[str, Any]) -> List[int]:
    for key in ("source_pages", "route_b_source_pages", "route_b2_source_pages", "page_image"):
        pages = parse_source_pages(row.get(key))
        if pages:
            return pages
    return []


def compact_text(text: str, limit: int = 220) -> str:
    cleaned = " ".join(str(text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "..."


def _citation_payload(hit: Dict[str, Any], rank: int) -> Dict[str, Any]:
    return {
        "rank": rank,
        "chunk_id": hit.get("chunk_id"),
        "page_number": hit.get("page_number"),
        "rrf_score": hit.get("rrf_score"),
        "evidence_score": hit.get("evidence_score"),
        "hybrid_score": hit.get("hybrid_score"),
        "matched_query_count": hit.get("matched_query_count"),
        "text_excerpt": compact_text(str(hit.get("text", ""))),
    }


def _table_citation(row: Dict[str, Any], source_pages: List[int], evidence: str) -> Dict[str, Any]:
    page = source_pages[0] if source_pages else ""
    return {
        "chunk_id": f"table_page_{page}" if page else "table_evidence",
        "page_number": page,
        "rrf_score": "",
        "evidence_score": "",
        "hybrid_score": "",
        "matched_query_count": "",
        "text": evidence,
        "citation_source_type": "table_row",
        "row_label": row.get("row_label", ""),
        "page_image": row.get("page_image", ""),
    }


def _has_table_evidence(row: Dict[str, Any], source_pages: List[int], evidence: str) -> bool:
    source_route = str(row.get("source_route", "") or "")
    return bool(evidence and source_pages and source_route.startswith("route_a"))


def attach_field_citations(
    rows: List[Dict[str, Any]],
    chunks: List[Dict[str, Any]],
    *,
    industry: str | None = None,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    enriched: List[Dict[str, Any]] = []

    for row in rows:
        field_key = str(row.get("field_key", "") or "")
        field_item = ESG_SCHEMA.get(field_key)
        source_pages = choose_source_pages(row)
        existing_evidence = choose_existing_evidence(row)
        hits: List[Dict[str, Any]] = []

        if field_item and chunks:
            hits = retrieve_hybrid_chunks(
                field_item,
                chunks,
                top_k=top_k,
                industry=industry,
            )

        page_hits = [
            hit
            for hit in hits
            if hit.get("page_number") in source_pages
        ]
        if _has_table_evidence(row, source_pages, existing_evidence):
            primary = _table_citation(row, source_pages, existing_evidence)
            text_citations = [_citation_payload(hit, rank + 1) for rank, hit in enumerate(hits)]
            citations = [_citation_payload(primary, 1), *text_citations]
        else:
            primary_candidates = page_hits or hits
            primary = primary_candidates[0] if primary_candidates else {}
            citations = [_citation_payload(hit, rank) for rank, hit in enumerate(hits, start=1)]

        primary_page = primary.get("page_number")
        primary_chunk_id = primary.get("chunk_id")
        citation_rank = 0
        if primary_chunk_id:
            for citation in citations:
                if citation.get("chunk_id") == primary_chunk_id:
                    citation_rank = int(citation["rank"])
                    break

        review_reasons = []
        if not existing_evidence:
            review_reasons.append("missing_existing_evidence")
        if field_item and not primary_chunk_id:
            review_reasons.append("no_retrieved_citation")
        if source_pages and primary_page and primary_page not in source_pages:
            review_reasons.append("source_page_mismatch")
        if not source_pages and primary_page:
            review_reasons.append("source_page_inferred_from_retrieval")

        review_status = "needs_review" if review_reasons else "auto_cited"
        evidence_text = existing_evidence or compact_text(str(primary.get("text", "")), limit=500)

        enriched.append(
            {
                **row,
                "field_name_cn": row.get("field_name_cn") or (field_item or {}).get("name_cn", ""),
                "citation_chunk_id": primary_chunk_id or "",
                "citation_page_number": primary_page or "",
                "citation_rank": citation_rank,
                "citation_evidence_text": evidence_text,
                "citation_text_excerpt": compact_text(str(primary.get("text", ""))),
                "citation_rrf_score": primary.get("rrf_score", ""),
                "citation_evidence_score": primary.get("evidence_score", ""),
                "citation_hybrid_score": primary.get("hybrid_score", ""),
                "citation_review_status": review_status,
                "citation_review_reasons": review_reasons,
                "citations": citations,
            }
        )

    return enriched


FIELD_CITATION_CSV_FIELDS = [
    "field_key",
    "field_name_cn",
    "category",
    "status",
    "value",
    "unit",
    "year",
    "source_route",
    "confidence",
    "citation_review_status",
    "citation_review_reasons",
    "citation_chunk_id",
    "citation_page_number",
    "citation_rank",
    "citation_hybrid_score",
    "citation_evidence_text",
    "citation_text_excerpt",
]


def flatten_for_csv(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    csv_rows = []
    for row in rows:
        csv_row = {key: row.get(key, "") for key in FIELD_CITATION_CSV_FIELDS}
        if isinstance(csv_row.get("citation_review_reasons"), list):
            csv_row["citation_review_reasons"] = ";".join(csv_row["citation_review_reasons"])
        csv_rows.append(csv_row)
    return csv_rows
