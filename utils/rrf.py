from __future__ import annotations

from typing import Any, Dict, List


def reciprocal_rank_fusion(
    ranked_lists: List[List[Dict[str, Any]]],
    *,
    id_key: str = "chunk_id",
    k: int = 60,
    top_k: int = 8,
) -> List[Dict[str, Any]]:
    scores: Dict[str, float] = {}
    merged: Dict[str, Dict[str, Any]] = {}
    sources: Dict[str, List[str]] = {}

    for ranked in ranked_lists:
        for rank, item in enumerate(ranked, start=1):
            item_id = str(item.get(id_key, ""))
            if not item_id:
                continue
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
            merged.setdefault(item_id, dict(item))
            retriever = str(item.get("retriever", "unknown"))
            sources.setdefault(item_id, [])
            if retriever not in sources[item_id]:
                sources[item_id].append(retriever)

            for score_key in ("bm25_score", "vector_score"):
                if score_key in item:
                    merged[item_id][score_key] = item[score_key]

    fused = []
    for item_id, item in merged.items():
        fused.append(
            {
                **item,
                "rrf_score": round(scores[item_id], 8),
                "retrieval_sources": sources.get(item_id, []),
            }
        )

    fused.sort(key=lambda item: item["rrf_score"], reverse=True)
    return fused[:top_k]
