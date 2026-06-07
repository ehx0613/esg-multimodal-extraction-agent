from __future__ import annotations

import time
from typing import Any, Callable, Dict, List


RetrieverFn = Callable[[Dict[str, Any], List[Dict[str, Any]]], List[Dict[str, Any]]]


def evaluate_retrieval(
    eval_rows: List[Dict[str, Any]],
    field_items_by_key: Dict[str, Dict[str, Any]],
    chunks: List[Dict[str, Any]],
    retriever: RetrieverFn,
) -> Dict[str, Any]:
    records = []
    hit_count = 0
    reciprocal_ranks = []
    started = time.perf_counter()

    for row in eval_rows:
        field_key = str(row.get("field_key", ""))
        expected_chunk_id = str(row.get("expected_chunk_id", ""))
        expected_page = row.get("expected_page")
        if expected_page not in (None, ""):
            try:
                expected_page = int(expected_page)
            except (TypeError, ValueError):
                pass
        field_item = field_items_by_key.get(field_key)
        if not field_item:
            continue

        hits = retriever(field_item, chunks)
        hit_ids = [str(hit.get("chunk_id", "")) for hit in hits]
        hit_pages = [hit.get("page_number") for hit in hits]
        rank = 0

        if expected_chunk_id and expected_chunk_id in hit_ids:
            rank = hit_ids.index(expected_chunk_id) + 1
        elif expected_page not in (None, "") and expected_page in hit_pages:
            rank = hit_pages.index(expected_page) + 1

        if rank:
            hit_count += 1
            reciprocal_ranks.append(1.0 / rank)
        else:
            reciprocal_ranks.append(0.0)

        records.append(
            {
                "query_id": row.get("query_id"),
                "field_key": field_key,
                "expected_chunk_id": expected_chunk_id,
                "expected_page": expected_page,
                "hit": bool(rank),
                "rank": rank,
                "top_chunk_ids": hit_ids,
                "top_pages": hit_pages,
            }
        )

    latency_ms = (time.perf_counter() - started) * 1000
    total = max(len(records), 1)
    return {
        "total": len(records),
        "hit_rate_at_k": round(hit_count / total, 4),
        "mrr_at_k": round(sum(reciprocal_ranks) / total, 4),
        "latency_ms": round(latency_ms, 3),
        "records": records,
    }
