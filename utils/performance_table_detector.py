from __future__ import annotations

from typing import Any, Dict, Iterable, List

from utils.mineru_route_a import html_table_to_grid, score_performance_table


def detect_performance_tables(blocks: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """High-recall deterministic detector. A model detector can replace/rerank this output."""
    candidates = []
    for block in blocks:
        if block.get("content_type") != "table":
            continue
        grid = html_table_to_grid(str(block.get("raw_content") or ""))
        assessment = score_performance_table(block, grid)
        candidates.append(
            {
                **assessment,
                "block_id": block.get("block_id"),
                "page_number": block.get("page_number"),
                "bbox": block.get("bbox"),
                "source_type": block.get("source_type"),
                "detector": "deterministic_performance_table_v1",
                "grid": grid,
            }
        )
    return candidates
