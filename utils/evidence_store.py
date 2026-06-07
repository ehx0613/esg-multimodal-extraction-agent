from pathlib import Path
from typing import Any, Dict, Iterable, List

from utils.result_guard import safe_write_json


def _source_region_id(page_number: Any, region: str) -> str:
    return f"page_{page_number or 'unknown'}_{region}"


def _base_record(
    *,
    evidence_id: str,
    source_region_id: str,
    evidence_type: str,
    page_number: Any,
    content: str,
    derivation_method: str,
    metadata: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return {
        "evidence_id": evidence_id,
        "source_region_id": source_region_id,
        "evidence_type": evidence_type,
        "page_number": page_number,
        "content": content,
        "proxy_text": content,
        "derivation_method": derivation_method,
        "metadata": metadata or {},
    }


def build_evidence_records(
    *,
    text_chunks: Iterable[Dict[str, Any]],
    structured_chunks: Iterable[Dict[str, Any]],
    page_features: Iterable[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []

    for index, chunk in enumerate(text_chunks):
        page_number = chunk.get("page_number")
        chunk_id = str(chunk.get("chunk_id") or f"text_{index}")
        records.append(
            _base_record(
                evidence_id=f"text:{chunk_id}",
                source_region_id=_source_region_id(page_number, f"text_{chunk_id}"),
                evidence_type="body_text",
                page_number=page_number,
                content=str(chunk.get("context_text") or chunk.get("text") or ""),
                derivation_method=str(
                    chunk.get("derivation_method")
                    or chunk.get("source_type")
                    or "pdf_text_parser"
                ),
                metadata={
                    "chunk_id": chunk_id,
                    "chunk_type": chunk.get("chunk_type", ""),
                    "section_title": chunk.get("section_title", ""),
                    "section_path": chunk.get("section_path", []),
                    "bbox": chunk.get("bbox"),
                },
            )
        )

    for index, chunk in enumerate(structured_chunks):
        chunk_id = str(chunk.get("chunk_id") or f"table_{index}")
        page_number = chunk.get("page_number")
        source_region_id = str(
            chunk.get("source_region_id")
            or _source_region_id(page_number, f"table_{chunk_id}")
        )
        records.append(
            _base_record(
                evidence_id=f"table:{chunk_id}",
                source_region_id=source_region_id,
                evidence_type="parsed_table",
                page_number=page_number,
                content=str(chunk.get("context_text") or chunk.get("text") or ""),
                derivation_method=str(chunk.get("derivation_method") or "route_a_vlm"),
                metadata={
                    "chunk_id": chunk_id,
                    "table_title": chunk.get("table_title", ""),
                    "metric_name": chunk.get("metric_name", ""),
                    "page_image": chunk.get("page_image", ""),
                    "source_type": chunk.get("source_type", ""),
                    "section_path": chunk.get("section_path", []),
                    "bbox": chunk.get("bbox"),
                    "raw_content": chunk.get("raw_content", ""),
                },
            )
        )

    for feature in page_features:
        page_number = feature.get("page_number")
        is_visual_candidate = bool(
            feature.get("force_keep")
            or feature.get("chart_force_keep")
            or int(feature.get("table_like_lines") or 0) >= 3
        )
        if not is_visual_candidate:
            continue
        proxy_parts = [
            *feature.get("strong_title_hits", []),
            *feature.get("title_hits", []),
            *feature.get("metric_hits", []),
            *feature.get("unit_hits", []),
            *feature.get("chart_hits", []),
            *feature.get("year_hits", []),
        ]
        proxy_text = " ".join(dict.fromkeys(str(value) for value in proxy_parts if value))
        if not proxy_text:
            proxy_text = " ".join(feature.get("reasons", []))
        records.append(
            _base_record(
                evidence_id=f"visual_proxy:page_{page_number}",
                source_region_id=_source_region_id(page_number, "visual_page"),
                evidence_type="visual_proxy",
                page_number=page_number,
                content=proxy_text,
                derivation_method="page_feature_detector",
                metadata={
                    "score": feature.get("score", 0),
                    "number_count": feature.get("number_count", 0),
                    "table_like_lines": feature.get("table_like_lines", 0),
                    "chart_candidate": bool(feature.get("chart_force_keep")),
                    "reasons": feature.get("reasons", []),
                },
            )
        )

    return records


def write_evidence_store(report_dir: Path, records: List[Dict[str, Any]]) -> Dict[str, Any]:
    report_dir = Path(report_dir)
    path = report_dir / "evidence_records.json"
    safe_write_json(path, records)
    counts: Dict[str, int] = {}
    for record in records:
        evidence_type = str(record.get("evidence_type") or "unknown")
        counts[evidence_type] = counts.get(evidence_type, 0) + 1
    summary = {
        "evidence_count": len(records),
        "evidence_type_counts": counts,
        "unique_source_regions": len(
            {record.get("source_region_id") for record in records if record.get("source_region_id")}
        ),
        "path": str(path),
    }
    safe_write_json(report_dir / "evidence_summary.json", summary)
    return summary
