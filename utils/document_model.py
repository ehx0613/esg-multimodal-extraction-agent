import re
from pathlib import Path
from typing import Any, Dict, Iterable, List


NUMBER_RE = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?")
YEAR_RE = re.compile(r"20[0-3][0-9]")
UNIT_HINTS = ["%", "吨", "万元", "人", "次", "小时", "千瓦时", "tCO2e", "CO2e", "升"]


def build_document_model(
    *,
    pdf_path: Path,
    parser_name: str,
    parser_version: str,
    source_signature: str,
    blocks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "document_model_version": "1.0",
        "pdf_path": str(Path(pdf_path)),
        "parser_name": parser_name,
        "parser_version": parser_version,
        "source_signature": source_signature,
        "block_count": len(blocks),
        "blocks": blocks,
    }


def pages_to_document_blocks(pages: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []
    for page in pages:
        page_number = int(page.get("page_number") or 0)
        text = str(page.get("text") or "").strip()
        if not text:
            continue
        blocks.append(
            {
                "block_id": f"p{page_number}_text_0",
                "page_number": page_number,
                "content_type": "text",
                "section_path": [],
                "plain_text": text,
                "raw_content": text,
                "bbox": None,
                "source_type": "pymupdf_text",
                "metadata": {},
            }
        )
    return blocks


def document_blocks_to_pages(blocks: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    page_parts: Dict[int, List[str]] = {}
    page_block_ids: Dict[int, List[str]] = {}

    for block in blocks:
        page_number = int(block.get("page_number") or 0)
        if page_number <= 0:
            continue
        text = str(block.get("plain_text") or "").strip()
        if text:
            page_parts.setdefault(page_number, []).append(text)
        page_block_ids.setdefault(page_number, []).append(str(block.get("block_id") or ""))

    pages = []
    for page_number in sorted(page_block_ids):
        text = "\n\n".join(page_parts.get(page_number, [])).strip()
        pages.append(
            {
                "page_number": page_number,
                "text": text,
                "char_count": len(text),
                "source_type": "document_model",
                "block_ids": page_block_ids[page_number],
            }
        )
    return pages


def _chunk_type(text: str, content_types: set[str]) -> str:
    if "table" in content_types:
        return "table_like"
    if len(NUMBER_RE.findall(text)) >= 4:
        return "metric_dense"
    return "narrative"


def chunk_document_blocks(
    blocks: Iterable[Dict[str, Any]],
    *,
    target_size: int = 900,
    max_size: int = 1200,
) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    current: List[Dict[str, Any]] = []

    def flush() -> None:
        nonlocal current
        if not current:
            return

        page_number = int(current[0].get("page_number") or 0)
        section_path = list(current[0].get("section_path") or [])
        text = "\n".join(
            str(block.get("plain_text") or "").strip()
            for block in current
            if str(block.get("plain_text") or "").strip()
        ).strip()
        if not text:
            current = []
            return

        content_types = {str(block.get("content_type") or "text") for block in current}
        bboxes = [block.get("bbox") for block in current if block.get("bbox")]
        raw_contents = [
            str(block.get("raw_content") or "")
            for block in current
            if str(block.get("raw_content") or "").strip()
        ]
        chunk_type = _chunk_type(text, content_types)
        section_title = section_path[-1] if section_path else ""
        source_region_id = (
            str(current[0].get("block_id") or "")
            if content_types == {"table"}
            else f"page_{page_number}_{len(chunks)}"
        )
        chunks.append(
            {
                "chunk_id": f"doc_p{page_number}_{len(chunks)}",
                "source_region_id": source_region_id,
                "page_number": page_number,
                "section_title": section_title,
                "section_path": section_path,
                "chunk_type": chunk_type,
                "content_format": "html" if content_types == {"table"} else "text",
                "source_type": "document_model",
                "source_block_ids": [block.get("block_id") for block in current],
                "bbox": bboxes[0] if len(bboxes) == 1 else None,
                "bboxes": bboxes,
                "text": text,
                "context_text": "\n".join([*section_path, text]).strip(),
                "raw_content": "\n".join(raw_contents),
                "char_count": len(text),
                "block_count": len(current),
                "number_count": len(NUMBER_RE.findall(text)),
                "year_hits": sorted(set(YEAR_RE.findall(text))),
                "unit_hits": [unit for unit in UNIT_HINTS if unit.lower() in text.lower()],
                "is_index_like": False,
            }
        )
        current = []

    for block in blocks:
        content_type = str(block.get("content_type") or "")
        text = str(block.get("plain_text") or "").strip()
        if not text or content_type in {"image", "header", "footer", "page_number"}:
            continue

        if content_type == "title":
            flush()
            continue

        if content_type == "table":
            flush()
            current = [block]
            flush()
            continue

        if current:
            same_page = block.get("page_number") == current[0].get("page_number")
            same_section = list(block.get("section_path") or []) == list(current[0].get("section_path") or [])
            current_size = sum(len(str(item.get("plain_text") or "")) for item in current)
            if not same_page or not same_section or current_size + len(text) > max_size:
                flush()

        current.append(block)
        current_size = sum(len(str(item.get("plain_text") or "")) for item in current)
        if current_size >= target_size:
            flush()

    flush()
    return chunks
