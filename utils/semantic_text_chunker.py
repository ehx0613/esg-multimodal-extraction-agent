import re
from typing import Any, Dict, List


NUMBER_RE = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?")
YEAR_RE = re.compile(r"20[0-3][0-9]")

UNIT_HINTS = [
    "%",
    "tCO2e",
    "CO2e",
    "kWh",
    "MWh",
    "m3",
    "\u5428",
    "\u5343\u74e6\u65f6",
    "\u5146\u74e6\u65f6",
    "\u7acb\u65b9\u7c73",
    "\u4e07\u5143",
    "\u4eba\u6b21",
    "\u5c0f\u65f6",
]

INDEX_HINTS = [
    "\u76ee\u5f55",
    "\u7d22\u5f15",
    "GRI",
    "CASS",
    "\u62ab\u9732\u7d22\u5f15",
    "\u6307\u6807\u7d22\u5f15",
    "\u8bfb\u8005\u53cd\u9988",
    "\u62a5\u544a\u5bfc\u8bfb",
    "\u5173\u4e8e\u6211\u4eec",
    "\u9644\u5f55",
    "\u672a\u6765\u5c55\u671b",
]

TITLE_HINTS = [
    "\u73af\u5883",
    "\u793e\u4f1a",
    "\u6cbb\u7406",
    "ESG",
    "\u53ef\u6301\u7eed",
    "\u5458\u5de5",
    "\u4f9b\u5e94\u5546",
    "\u78b3",
    "\u80fd\u6e90",
    "\u6392\u653e",
    "\u7ee9\u6548",
]


def _normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", str(line or "").strip())


def _split_sentences(text: str, max_chars: int) -> List[str]:
    text = _normalize_line(text)
    if len(text) <= max_chars:
        return [text] if text else []

    parts = re.split(r"(?<=[\u3002\uff1b\uff01\uff1f;!?])", text)
    chunks: List[str] = []
    current = ""

    for part in parts:
        part = part.strip()
        if not part:
            continue
        if current and len(current) + len(part) > max_chars:
            chunks.append(current)
            current = part
        else:
            current = current + part

    if current:
        chunks.append(current)

    if not chunks:
        return [text[idx : idx + max_chars] for idx in range(0, len(text), max_chars)]
    return chunks


def _looks_like_title(line: str) -> bool:
    text = _normalize_line(line)
    if not text:
        return False
    # Short metric labels in KPI panels often look like headings, but they must
    # stay attached to the value on the following line.
    if text.endswith((":", "\uff1a")):
        return False
    if NUMBER_RE.search(text) and any(unit.lower() in text.lower() for unit in UNIT_HINTS):
        return False
    if len(text) > 40:
        return False
    if NUMBER_RE.search(text) and len(text) > 16:
        return False
    if re.match(r"^(\d+(\.\d+)*|[一二三四五六七八九十]+)[、.．]\s*", text):
        return True
    return any(hint.lower() in text.lower() for hint in TITLE_HINTS)


def _line_is_table_like(line: str) -> bool:
    text = str(line or "").strip()
    if not text:
        return False
    if len(text) <= 40 and text.endswith((":", "\uff1a")):
        return True
    number_count = len(NUMBER_RE.findall(text))
    has_unit = any(unit.lower() in text.lower() for unit in UNIT_HINTS)
    has_table_spacing = "\t" in text or bool(re.search(r"\s{2,}", text))
    return number_count >= 2 or (number_count >= 1 and has_unit) or (has_table_spacing and number_count)


def _unit_hits(text: str) -> List[str]:
    lowered = str(text or "").lower()
    return [unit for unit in UNIT_HINTS if unit.lower() in lowered]


def _is_index_like(text: str) -> bool:
    lowered = str(text or "").lower()
    hits = sum(1 for hint in INDEX_HINTS if hint.lower() in lowered)
    number_count = len(NUMBER_RE.findall(text))
    unit_count = len(_unit_hits(text))
    if hits >= 2 and number_count < 30:
        return True
    return "\u76ee\u5f55" in text and number_count >= 6 and unit_count == 0


def _chunk_type(text: str, table_line_count: int) -> str:
    number_count = len(NUMBER_RE.findall(text))
    unit_count = len(_unit_hits(text))
    if _is_index_like(text):
        return "index_like"
    if table_line_count >= 2:
        return "table_like"
    if number_count >= 4 or (number_count >= 2 and unit_count):
        return "metric_dense"
    return "narrative"


def _build_blocks(page: Dict[str, Any], max_block_chars: int) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []
    current_lines: List[str] = []
    current_table_lines = 0
    section_title = ""
    page_number = page.get("page_number")

    def flush() -> None:
        nonlocal current_lines, current_table_lines
        text = "\n".join(current_lines).strip()
        if not text:
            current_lines = []
            current_table_lines = 0
            return
        for piece in _split_sentences(text, max_block_chars):
            blocks.append(
                {
                    "page_number": page_number,
                    "section_title": section_title,
                    "text": piece,
                    "table_line_count": current_table_lines,
                }
            )
        current_lines = []
        current_table_lines = 0

    for raw_line in str(page.get("text", "") or "").splitlines():
        line = _normalize_line(raw_line)
        if not line:
            flush()
            continue

        if _looks_like_title(line):
            flush()
            section_title = line
            blocks.append(
                {
                    "page_number": page_number,
                    "section_title": section_title,
                    "text": line,
                    "table_line_count": 0,
                    "is_title": True,
                }
            )
            continue

        table_like = _line_is_table_like(line)
        if current_lines and table_like != (current_table_lines > 0):
            flush()

        current_lines.append(line)
        if table_like:
            current_table_lines += 1

        if sum(len(item) for item in current_lines) >= max_block_chars:
            flush()

    flush()
    return blocks


def _format_chunk(
    chunk_id: str,
    page_number: Any,
    text: str,
    section_title: str,
    table_line_count: int,
    block_count: int,
) -> Dict[str, Any]:
    numbers = NUMBER_RE.findall(text)
    units = _unit_hits(text)
    chunk_type = _chunk_type(text, table_line_count)
    return {
        "chunk_id": chunk_id,
        "page_number": page_number,
        "section_title": section_title,
        "chunk_type": chunk_type,
        "text": text.strip(),
        "context_text": f"{section_title}\n{text}".strip() if section_title else text.strip(),
        "char_count": len(text.strip()),
        "block_count": block_count,
        "number_count": len(numbers),
        "year_hits": sorted(set(YEAR_RE.findall(text))),
        "unit_hits": units,
        "is_index_like": chunk_type == "index_like",
    }


def chunk_pages_semantic_esg(
    pages: List[Dict[str, Any]],
    target_size: int = 900,
    min_size: int = 250,
    max_size: int = 1200,
    block_overlap: int = 1,
) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []

    for page in pages:
        blocks = _build_blocks(page, max_block_chars=max_size)
        current: List[Dict[str, Any]] = []
        current_len = 0
        current_table_lines = 0
        current_section = ""
        page_number = page.get("page_number")

        def flush() -> None:
            nonlocal current, current_len, current_table_lines, current_section
            if not current:
                return
            text = "\n".join(str(block.get("text", "")).strip() for block in current if block.get("text")).strip()
            if text:
                chunks.append(
                    _format_chunk(
                        chunk_id=f"p{page_number}_{len(chunks)}",
                        page_number=page_number,
                        text=text,
                        section_title=current_section,
                        table_line_count=current_table_lines,
                        block_count=len(current),
                    )
                )
            overlap_blocks = current[-block_overlap:] if block_overlap > 0 else []
            current = [block for block in overlap_blocks if not block.get("is_title")]
            current_len = sum(len(str(block.get("text", ""))) for block in current)
            current_table_lines = sum(int(block.get("table_line_count") or 0) for block in current)
            current_section = current[-1].get("section_title", current_section) if current else current_section

        for block in blocks:
            block_text = str(block.get("text", "") or "").strip()
            if not block_text:
                continue

            block_section = str(block.get("section_title") or current_section or "")
            block_table_lines = int(block.get("table_line_count") or 0)
            block_is_table = block_table_lines > 0
            current_is_table = current_table_lines > 0
            would_exceed = current and current_len + len(block_text) > max_size
            section_changed = current and block_section and current_section and block_section != current_section
            type_changed = current and block_is_table != current_is_table and current_len >= min_size

            if would_exceed or section_changed or type_changed:
                flush()
                if section_changed:
                    current = []
                    current_len = 0
                    current_table_lines = 0
                    current_section = ""

            current.append(block)
            current_len += len(block_text)
            current_table_lines += block_table_lines
            current_section = block_section or current_section

            if current_len >= target_size and current_len >= min_size:
                flush()

        flush()

    return chunks
