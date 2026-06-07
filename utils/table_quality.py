import re
from html.parser import HTMLParser
from typing import Any, Dict, Iterable, List


NUMBER_RE = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?")
YEAR_RE = re.compile(r"20[0-3][0-9]")


class _TableGridParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: List[List[str]] = []
        self._row: List[str] | None = None
        self._cell: List[str] | None = None
        self._cell_span = 1
        self.header_cells = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        tag = tag.lower()
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"}:
            self._cell = []
            attrs_dict = dict(attrs)
            try:
                self._cell_span = max(1, int(attrs_dict.get("colspan") or 1))
            except (TypeError, ValueError):
                self._cell_span = 1
            if tag == "th":
                self.header_cells += 1

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(str(data or ""))

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"td", "th"} and self._row is not None and self._cell is not None:
            self._row.append(" ".join(self._cell).strip())
            self._row.extend([""] * (self._cell_span - 1))
            self._cell = None
            self._cell_span = 1
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None


def _parse_grid(raw_content: str) -> _TableGridParser:
    parser = _TableGridParser()
    try:
        parser.feed(str(raw_content or ""))
    except Exception:
        pass
    return parser


def assess_table_chunk(chunk: Dict[str, Any], *, visual_threshold: float = 0.72) -> Dict[str, Any]:
    raw_content = str(chunk.get("raw_content") or "")
    text = str(chunk.get("text") or chunk.get("context_text") or "")
    grid = _parse_grid(raw_content)
    row_lengths = [len(row) for row in grid.rows if row]
    dominant_columns = max(set(row_lengths), key=row_lengths.count) if row_lengths else 0
    inconsistent_rows = sum(length != dominant_columns for length in row_lengths)
    empty_cells = sum(not cell.strip() for row in grid.rows for cell in row)
    total_cells = sum(row_lengths)
    empty_ratio = empty_cells / total_cells if total_cells else 1.0
    number_count = len(NUMBER_RE.findall(text))
    year_count = len(set(YEAR_RE.findall(text)))
    numeric_row_density = number_count / max(len(grid.rows), 1)
    likely_quantitative = year_count > 0 or (number_count >= 2 and numeric_row_density >= 0.75)
    first_row_has_header_signal = bool(
        grid.rows and len(grid.rows[0]) >= 2 and sum(bool(cell.strip()) for cell in grid.rows[0]) >= 2
    )

    score = 1.0
    reasons: List[str] = []
    if not chunk.get("bbox"):
        score -= 0.25
        reasons.append("missing_bbox")
    if not raw_content or "<table" not in raw_content.lower():
        score -= 0.30
        reasons.append("missing_table_html")
    if len(grid.rows) < 2:
        score -= 0.30
        reasons.append("too_few_rows")
    if dominant_columns < 2:
        score -= 0.25
        reasons.append("too_few_columns")
    if inconsistent_rows:
        penalty = min(0.30, inconsistent_rows / max(len(row_lengths), 1) * 0.40)
        score -= penalty
        reasons.append("inconsistent_column_counts")
    if empty_ratio > 0.35:
        score -= min(0.25, empty_ratio * 0.30)
        reasons.append("high_empty_cell_ratio")
    if not first_row_has_header_signal and grid.header_cells == 0:
        score -= 0.10
        reasons.append("weak_header_signal")

    score = round(max(0.0, min(1.0, score)), 4)
    return {
        "chunk_id": chunk.get("chunk_id"),
        "source_region_id": chunk.get("source_region_id"),
        "page_number": chunk.get("page_number"),
        "bbox": chunk.get("bbox"),
        "quality_score": score,
        "needs_visual": likely_quantitative and score < visual_threshold,
        "reasons": reasons,
        "features": {
            "table_kind": "quantitative" if likely_quantitative else "qualitative",
            "row_count": len(grid.rows),
            "dominant_column_count": dominant_columns,
            "inconsistent_row_count": inconsistent_rows,
            "empty_cell_ratio": round(empty_ratio, 4),
            "number_count": number_count,
            "numeric_row_density": round(numeric_row_density, 4),
            "year_count": year_count,
            "header_cell_count": grid.header_cells,
        },
    }


def assess_mineru_tables(
    structured_chunks: Iterable[Dict[str, Any]],
    *,
    visual_threshold: float = 0.72,
) -> List[Dict[str, Any]]:
    return [
        assess_table_chunk(chunk, visual_threshold=visual_threshold)
        for chunk in structured_chunks
        if chunk.get("chunk_type") == "mineru_structured_table"
    ]


def apply_cross_source_consistency(
    assessments: List[Dict[str, Any]],
    structured_chunks: Iterable[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    route_a_chunks = [
        chunk for chunk in structured_chunks if chunk.get("chunk_type") == "route_a_structured_row"
    ]
    mineru_chunks = [
        chunk for chunk in structured_chunks if chunk.get("chunk_type") == "mineru_structured_table"
    ]
    conflicts_by_region: Dict[str, List[Dict[str, Any]]] = {}

    for route_a in route_a_chunks:
        metric = re.sub(r"[\s\W_]+", "", str(route_a.get("metric_name") or "").lower())
        if len(metric) < 3:
            continue
        route_values = [
            re.sub(r"[,\s]", "", str(value))
            for value in (route_a.get("values") or {}).values()
            if str(value or "").strip()
        ]
        if not route_values:
            continue
        for mineru in mineru_chunks:
            if mineru.get("page_number") != route_a.get("page_number"):
                continue
            mineru_text = re.sub(r"[\s\W_]+", "", str(mineru.get("text") or "").lower())
            if metric not in mineru_text:
                continue
            if not any(value.lower() in mineru_text for value in route_values):
                region_id = str(mineru.get("source_region_id") or "")
                conflicts_by_region.setdefault(region_id, []).append(
                    {
                        "metric_name": route_a.get("metric_name"),
                        "route_a_values": route_values,
                        "route_a_chunk_id": route_a.get("chunk_id"),
                    }
                )

    for assessment in assessments:
        conflicts = conflicts_by_region.get(str(assessment.get("source_region_id") or ""), [])
        assessment["cross_source_conflicts"] = conflicts
        if conflicts:
            assessment["quality_score"] = min(float(assessment["quality_score"]), 0.69)
            assessment["needs_visual"] = True
            if "cross_source_conflict" not in assessment["reasons"]:
                assessment["reasons"].append("cross_source_conflict")
    return assessments
