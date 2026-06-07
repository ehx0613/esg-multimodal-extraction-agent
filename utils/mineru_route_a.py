import re
from html.parser import HTMLParser
from typing import Any, Dict, Iterable, List


YEAR_RE = re.compile(r"20[0-3][0-9]")
NUMBER_RE = re.compile(r"^-?\d+(?:,\d{3})*(?:\.\d+)?%?$|^-?\d+(?:\.\d+)?%?$")
PERFORMANCE_TERMS = ("关键绩效", "经济绩效", "环境绩效", "社会绩效", "治理绩效", "绩效指标")
INDEX_TERMS = ("GRI Standards", "SDGs", "对标索引", "监管指引", "章节")


class _HTMLTableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: List[List[Dict[str, Any]]] = []
        self._row: List[Dict[str, Any]] | None = None
        self._cell: List[str] | None = None
        self._rowspan = 1
        self._colspan = 1

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"}:
            values = dict(attrs)
            self._cell = []
            self._rowspan = _positive_int(values.get("rowspan"), 1)
            self._colspan = _positive_int(values.get("colspan"), 1)

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            value = str(data or "").strip()
            if value:
                self._cell.append(value)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"td", "th"} and self._row is not None and self._cell is not None:
            self._row.append(
                {
                    "text": " ".join(self._cell).strip(),
                    "rowspan": self._rowspan,
                    "colspan": self._colspan,
                }
            )
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None


def _positive_int(value: Any, default: int) -> int:
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


def html_table_to_grid(raw_content: str) -> List[List[str]]:
    parser = _HTMLTableParser()
    parser.feed(str(raw_content or ""))
    grid: List[List[str]] = []
    active: Dict[int, tuple[str, int]] = {}

    for source_row in parser.rows:
        row: List[str] = []
        column = 0

        def fill_active() -> None:
            nonlocal column
            while column in active:
                text, remaining = active[column]
                row.append(text)
                if remaining <= 1:
                    del active[column]
                else:
                    active[column] = (text, remaining - 1)
                column += 1

        fill_active()
        for cell in source_row:
            fill_active()
            text = str(cell["text"] or "").strip()
            for offset in range(int(cell["colspan"])):
                row.append(text if offset == 0 else "")
                if int(cell["rowspan"]) > 1:
                    active[column] = (text if offset == 0 else "", int(cell["rowspan"]) - 1)
                column += 1
            fill_active()
        while active and column <= max(active):
            fill_active()
            if column not in active and column <= max(active, default=-1):
                row.append("")
                column += 1
        grid.append(row)

    width = max((len(row) for row in grid), default=0)
    return [row + [""] * (width - len(row)) for row in grid]


def _context_text(block: Dict[str, Any]) -> str:
    metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
    caption = metadata.get("table_caption") or []
    if not isinstance(caption, list):
        caption = [caption]
    return " ".join(
        [
            *[str(value) for value in block.get("section_path", [])],
            *[str(value) for value in caption],
            str(block.get("plain_text") or ""),
        ]
    )


def score_performance_table(block: Dict[str, Any], grid: List[List[str]]) -> Dict[str, Any]:
    context = _context_text(block)
    first_rows = " ".join(" ".join(row) for row in grid[:3])
    score = 0
    reasons: List[str] = []
    for term in PERFORMANCE_TERMS:
        if term in context:
            score += 5 if term == "关键绩效" else 3
            reasons.append(f"performance_term:{term}")
    if "指标" in first_rows or "类型" in first_rows:
        score += 2
        reasons.append("metric_header")
    if "单位" in first_rows:
        score += 2
        reasons.append("unit_header")
    if YEAR_RE.search(first_rows):
        score += 3
        reasons.append("year_header")
    numeric_rows = sum(any(NUMBER_RE.match(cell.replace(" ", "")) for cell in row) for row in grid[1:])
    if numeric_rows >= 2:
        score += min(4, numeric_rows // 3 + 1)
        reasons.append("numeric_rows")
    if any(term.lower() in context.lower() for term in INDEX_TERMS):
        score -= 10
        reasons.append("index_table")
    return {
        "score": score,
        "selected": score >= 7 and len(grid) >= 2,
        "reasons": reasons,
        "row_count": len(grid),
        "numeric_rows": numeric_rows,
    }


def _header_index(grid: List[List[str]]) -> int:
    def score(row: List[str]) -> int:
        text = " ".join(row)
        return (
            3 * len(YEAR_RE.findall(text))
            + 2 * int("单位" in text)
            + 2 * int("指标" in text or "类型" in text)
        )

    candidates = list(range(min(4, len(grid))))
    return max(candidates, key=lambda index: score(grid[index]), default=0)


def grid_to_route_a_rows(grid: List[List[str]], table_title: str) -> List[Dict[str, Any]]:
    if len(grid) < 2:
        return []
    header_idx = _header_index(grid)
    header = grid[header_idx]
    year_columns = {
        index: match.group(0)
        for index, cell in enumerate(header)
        if (match := YEAR_RE.search(str(cell or "")))
    }
    if not year_columns:
        return []
    first_year_column = min(year_columns)
    unit_column = next((index for index, cell in enumerate(header) if "单位" in cell), None)
    metric_column = next(
        (index for index, cell in enumerate(header) if "指标" in cell or "类型" in cell),
        max(0, first_year_column - 1),
    )

    rows: List[Dict[str, Any]] = []
    for source_row in grid[header_idx + 1 :]:
        values = {
            year: str(source_row[column]).strip()
            for column, year in year_columns.items()
            if column < len(source_row) and str(source_row[column]).strip()
        }
        if not values or not any(NUMBER_RE.match(value.replace(" ", "")) for value in values.values()):
            continue
        metric_name = str(source_row[metric_column] if metric_column < len(source_row) else "").strip()
        if not metric_name:
            metric_name = next(
                (
                    str(source_row[index]).strip()
                    for index in range(first_year_column - 1, -1, -1)
                    if str(source_row[index]).strip()
                ),
                "",
            )
        topic_parts = [
            str(source_row[index]).strip()
            for index in range(min(metric_column, first_year_column))
            if str(source_row[index]).strip() and str(source_row[index]).strip() != metric_name
        ]
        unit = (
            str(source_row[unit_column]).strip()
            if unit_column is not None and unit_column < len(source_row)
            else ""
        )
        evidence = " ".join([table_title, *topic_parts, metric_name, unit, *values.values()]).strip()
        rows.append(
            {
                "topic": " / ".join(dict.fromkeys(topic_parts)),
                "metric_name": metric_name,
                "unit": unit,
                "values": values,
                "evidence_text": evidence,
            }
        )
    return rows


def build_mineru_route_a_pages(blocks: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    pages: List[Dict[str, Any]] = []
    assessments: List[Dict[str, Any]] = []
    for block in blocks:
        if block.get("content_type") != "table":
            continue
        grid = html_table_to_grid(str(block.get("raw_content") or ""))
        assessment = score_performance_table(block, grid)
        assessment.update(
            {
                "block_id": block.get("block_id"),
                "page_number": block.get("page_number"),
                "bbox": block.get("bbox"),
            }
        )
        assessments.append(assessment)
        if not assessment["selected"]:
            continue
        metadata = block.get("metadata") if isinstance(block.get("metadata"), dict) else {}
        captions = metadata.get("table_caption") or []
        if not isinstance(captions, list):
            captions = [captions]
        section_path = block.get("section_path") or []
        table_title = " / ".join(
            str(value) for value in [*section_path[-2:], *captions] if str(value).strip()
        )
        rows = grid_to_route_a_rows(grid, table_title)
        if not rows:
            continue
        pages.append(
            {
                "page_image": f"page_{block.get('page_number')}.png",
                "page_number": block.get("page_number"),
                "page_type": "performance_data_table",
                "page_note": "mineru_route_a",
                "source_type": "mineru_performance_table",
                "source_region_id": block.get("block_id"),
                "bbox": block.get("bbox"),
                "tables": [
                    {
                        "table_title": table_title,
                        "columns": grid[_header_index(grid)],
                        "rows": rows,
                    }
                ],
            }
        )
    return {
        "pages": pages,
        "assessments": assessments,
        "selected_tables": len(pages),
        "row_count": sum(len(table["rows"]) for page in pages for table in page["tables"]),
    }
