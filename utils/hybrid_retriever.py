from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from utils.bm25_retriever import BM25Retriever
from utils.query_rewriter import rewrite_field_queries
from utils.rag_vector_store import FaissChunkVectorStore, build_query_text
from utils.rrf import reciprocal_rank_fusion


GENERIC_CONTEXT_TERMS = ("议题矩阵", "内容索引", "指标索引", "报告索引", "读者反馈表")


def _merge_bm25_query_hits(query_hit_lists: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}

    for hits in query_hit_lists:
        for rank, hit in enumerate(hits, start=1):
            chunk_id = str(hit.get("chunk_id", ""))
            if not chunk_id:
                continue

            entry = merged.setdefault(
                chunk_id,
                {
                    **hit,
                    "retriever": "bm25",
                    "bm25_score": 0.0,
                    "bm25_rank_score": 0.0,
                    "matched_query_count": 0,
                },
            )
            entry["bm25_score"] += float(hit.get("bm25_score", 0.0))
            entry["bm25_rank_score"] += 1.0 / (60 + rank)
            entry["matched_query_count"] += 1

    ranked = list(merged.values())
    ranked.sort(
        key=lambda item: (
            item["bm25_rank_score"],
            item["bm25_score"],
            item["matched_query_count"],
        ),
        reverse=True,
    )
    return ranked


def _evidence_score(field_item: Dict[str, Any], item: Dict[str, Any]) -> float:
    text = str(item.get("text", ""))
    aliases = [str(term) for term in field_item.get("aliases", []) if term]
    required_terms = [str(term) for term in field_item.get("required_any", []) if term]
    forbidden_terms = [str(term) for term in field_item.get("forbidden_any", []) if term]
    field_name = str(field_item.get("name_cn", ""))

    score = 0.0
    if field_name and field_name in text:
        score += 0.08

    matched_aliases = sum(1 for term in set(aliases) if term in text)
    score += min(matched_aliases, 3) * 0.04

    if required_terms:
        matched_required = sum(1 for term in set(required_terms) if term in text)
        score += 0.12 * (matched_required / len(set(required_terms)))
        if matched_required >= 2:
            score += 0.04

    if any(term in text for term in forbidden_terms):
        score -= 0.16
    if any(term in text for term in GENERIC_CONTEXT_TERMS):
        score -= 0.08

    return round(score, 8)


def _rerank_with_evidence(field_item: Dict[str, Any], items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    reranked = []
    for item in items:
        evidence_score = _evidence_score(field_item, item)
        reranked.append(
            {
                **item,
                "evidence_score": evidence_score,
                "hybrid_score": round(float(item.get("rrf_score", 0.0)) + evidence_score, 8),
            }
        )

    reranked.sort(
        key=lambda item: (
            item["hybrid_score"],
            item.get("matched_query_count", 0),
            item.get("bm25_score", 0.0),
        ),
        reverse=True,
    )
    return reranked


def retrieve_hybrid_chunks(
    field_item: Dict[str, Any],
    chunks: List[Dict[str, Any]],
    *,
    top_k: int = 5,
    recall_k: int = 12,
    industry: str | None = None,
    vector_index_dir: Path | None = None,
    use_vector: bool = False,
) -> List[Dict[str, Any]]:
    if not chunks:
        return []

    rewritten_queries = rewrite_field_queries(field_item, industry=industry)
    bm25 = BM25Retriever(chunks)
    bm25_query_hits: List[List[Dict[str, Any]]] = []

    for query in rewritten_queries:
        bm25_query_hits.append(bm25.search(query, top_k=recall_k))
    bm25_hits = _merge_bm25_query_hits(bm25_query_hits)

    ranked_lists = [bm25_hits]
    vector_hits: List[Dict[str, Any]] = []

    if use_vector and vector_index_dir is not None:
        query_text = build_query_text(field_item, extra_terms=rewritten_queries)
        vector_hits = (
            FaissChunkVectorStore(vector_index_dir)
            .build_or_load(chunks)
            .search(query_text, top_k=recall_k)
        )
        vector_hits = [
            {
                **hit,
                "retriever": "vector",
            }
            for hit in vector_hits
        ]
        ranked_lists.append(vector_hits)

    fused = reciprocal_rank_fusion(ranked_lists, top_k=max(top_k, recall_k))
    fused = _rerank_with_evidence(field_item, fused)[:top_k]
    results = []
    for rank, item in enumerate(fused, start=1):
        results.append(
            {
                **item,
                "retrieval_rank": rank,
                "retrieval_profile": "hybrid_bm25_vector_rrf" if vector_hits else "bm25_rrf",
                "rewritten_queries": rewritten_queries,
            }
        )
    return results
