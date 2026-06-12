from __future__ import annotations

from typing import Any, Dict, Iterable, List

from utils.result_guard import safe_write_json


def flatten_raw_table_metrics(pages: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    metrics = []
    for page in pages:
        for table_index, table in enumerate(page.get("tables", [])):
            for row_index, row in enumerate(table.get("rows", [])):
                metrics.append(
                    {
                        "raw_metric_id": f"{page.get('source_region_id', 'table')}_{table_index}_{row_index}",
                        "metric_name": row.get("metric_name", ""),
                        "topic": row.get("topic", ""),
                        "values": row.get("values", {}),
                        "unit": row.get("unit", ""),
                        "evidence_text": row.get("evidence_text", ""),
                        "table_title": table.get("table_title", ""),
                        "columns": table.get("columns", []),
                        "page_number": page.get("page_number"),
                        "bbox": page.get("bbox"),
                        "source_region_id": page.get("source_region_id"),
                        "source_type": page.get("source_type"),
                    }
                )
    return metrics


def write_raw_metric_store(report_dir, pages: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    metrics = flatten_raw_table_metrics(pages)
    path = report_dir / "raw_table_metrics.json"
    safe_write_json(path, metrics)
    return {"count": len(metrics), "path": str(path)}
