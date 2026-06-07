import re
from pathlib import Path
from typing import Any, Dict, List

from utils.json_utils import load_json


def _page_number_from_image(value: Any) -> int | None:
    match = re.search(r"page_(\d+)", str(value or ""))
    if not match:
        return None
    return int(match.group(1))


def _flatten_values(values: Any) -> List[tuple[str, str]]:
    if not isinstance(values, dict):
        return []
    return [(str(year), str(value)) for year, value in values.items() if str(value or "").strip()]


def _row_text(
    *,
    table_title: str,
    topic: str,
    metric_name: str,
    unit: str,
    year: str,
    value: str,
    evidence_text: str,
) -> str:
    pieces = [
        table_title,
        topic,
        metric_name,
        unit,
        year,
        value,
        evidence_text,
    ]
    return " ".join(str(piece).strip() for piece in pieces if str(piece or "").strip())


def _build_route_a_chunks(report_dir: Path) -> List[Dict[str, Any]]:
    rows_path = report_dir / "all_table_rows.json"
    if not rows_path.exists():
        return []

    pages = load_json(rows_path)
    if not isinstance(pages, list):
        return []

    chunks: List[Dict[str, Any]] = []
    for page_idx, page in enumerate(pages):
        if not isinstance(page, dict):
            continue
        page_image = page.get("page_image") or ""
        page_number = _page_number_from_image(page_image)
        page_type = str(page.get("page_type") or "")
        for table_idx, table in enumerate(page.get("tables", []) or []):
            if not isinstance(table, dict):
                continue
            table_title = str(table.get("table_title") or "")
            for row_idx, row in enumerate(table.get("rows", []) or []):
                if not isinstance(row, dict):
                    continue
                topic = str(row.get("topic") or "")
                metric_name = str(row.get("metric_name") or "")
                unit = str(row.get("unit") or "")
                evidence_text = str(row.get("evidence_text") or "")
                values = _flatten_values(row.get("values"))
                values_text = " ".join(f"{year} {value}" for year, value in values)
                text = _row_text(
                    table_title=table_title,
                    topic=topic,
                    metric_name=metric_name,
                    unit=unit,
                    year="",
                    value=values_text,
                    evidence_text=evidence_text,
                )
                if not text:
                    continue

                chunks.append(
                    {
                        "chunk_id": f"route_a_row_{page_idx}_{table_idx}_{row_idx}",
                        "source_region_id": f"page_{page_number or 'unknown'}_table_{table_idx}",
                        "page_number": page_number,
                        "section_title": table_title,
                        "chunk_type": "route_a_structured_row",
                        "source_type": "route_a_vlm_structured_row",
                        "derivation_method": "route_a_vlm",
                        "page_image": page_image,
                        "page_type": page_type,
                        "table_title": table_title,
                        "topic": topic,
                        "metric_name": metric_name,
                        "unit": unit,
                        "values": dict(values),
                        "text": text,
                        "context_text": text,
                        "char_count": len(text),
                        "block_count": 1,
                        "number_count": len(re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?", text)),
                        "year_hits": [year for year, _ in values if year],
                        "unit_hits": [unit] if unit else [],
                        "is_index_like": False,
                    }
                )

    return chunks


def _build_mineru_table_chunks(report_dir: Path) -> List[Dict[str, Any]]:
    blocks_path = report_dir / "ingest" / "document_blocks.json"
    if not blocks_path.exists():
        return []

    blocks = load_json(blocks_path)
    if not isinstance(blocks, list):
        return []

    chunks: List[Dict[str, Any]] = []
    for index, block in enumerate(blocks):
        if not isinstance(block, dict) or block.get("content_type") != "table":
            continue
        text = str(block.get("plain_text") or block.get("text") or "").strip()
        if not text:
            continue

        metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
        section_path = block.get("section_path") if isinstance(block.get("section_path"), list) else []
        captions = metadata.get("table_caption") or metadata.get("caption") or []
        if isinstance(captions, list):
            caption = " ".join(str(value) for value in captions if str(value).strip())
        else:
            caption = str(captions or "")
        table_title = caption or str(section_path[-1] if section_path else "")
        block_id = str(block.get("block_id") or f"table_{index}")
        page_number = block.get("page_number")
        unit_hits = block.get("unit_hits") if isinstance(block.get("unit_hits"), list) else []
        year_hits = block.get("year_hits") if isinstance(block.get("year_hits"), list) else []
        number_count = block.get("number_count")
        if not isinstance(number_count, int):
            number_count = len(re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?", text))

        chunks.append(
            {
                "chunk_id": f"mineru_table_{block_id}",
                "source_region_id": str(block.get("source_region_id") or block_id),
                "page_number": page_number,
                "section_title": table_title,
                "section_path": section_path,
                "chunk_type": "mineru_structured_table",
                "source_type": "mineru_table",
                "derivation_method": "mineru",
                "table_title": table_title,
                "bbox": block.get("bbox"),
                "raw_content": block.get("raw_content") or metadata.get("raw_content") or "",
                "table_footnotes": metadata.get("table_footnote") or metadata.get("footnotes") or [],
                "text": text,
                "context_text": text,
                "char_count": len(text),
                "block_count": 1,
                "number_count": number_count,
                "year_hits": year_hits,
                "unit_hits": unit_hits,
                "is_index_like": False,
            }
        )
    return chunks


def build_structured_chunks_from_all_table_rows(report_dir: Path) -> List[Dict[str, Any]]:
    report_dir = Path(report_dir)
    # Route A remains the higher-priority structured source. MinerU tables add
    # searchable coverage and retain geometry for later visual arbitration.
    return [
        *_build_route_a_chunks(report_dir),
        *_build_mineru_table_chunks(report_dir),
    ]
