import unittest

from config.schema import ESG_SCHEMA
from utils.bm25_retriever import BM25Retriever
from utils.hybrid_retriever import retrieve_hybrid_chunks
from utils.query_rewriter import rewrite_field_queries
from utils.retrieval_eval import evaluate_retrieval
from utils.rrf import reciprocal_rank_fusion


CHUNKS = [
    {
        "chunk_id": "c1",
        "page_number": 10,
        "text": "公司建立反腐败政策和举报人保护机制，开展商业道德培训。",
    },
    {
        "chunk_id": "c2",
        "page_number": 20,
        "text": "本年度温室气体排放总量为12000吨二氧化碳当量，并披露范围一和范围二排放。",
    },
    {
        "chunk_id": "c3",
        "page_number": 30,
        "text": "员工培训覆盖率达到95%，员工发展体系持续完善。",
    },
]


class HybridRetrieverTests(unittest.TestCase):
    def test_query_rewriter_uses_framework_labels(self) -> None:
        queries = rewrite_field_queries(ESG_SCHEMA["total_ghg_emissions"], industry="manufacturing")
        joined = " ".join(queries)

        self.assertIn("温室气体排放", joined)
        self.assertIn("气候变化", joined)
        self.assertIn("manufacturing", joined)

    def test_bm25_retriever_finds_keyword_chunk(self) -> None:
        hits = BM25Retriever(CHUNKS).search("温室气体排放", top_k=2)

        self.assertEqual(hits[0]["chunk_id"], "c2")
        self.assertGreater(hits[0]["bm25_score"], 0)

    def test_rrf_merges_ranked_lists(self) -> None:
        fused = reciprocal_rank_fusion(
            [
                [{"chunk_id": "a", "retriever": "bm25"}, {"chunk_id": "b", "retriever": "bm25"}],
                [{"chunk_id": "b", "retriever": "vector"}, {"chunk_id": "c", "retriever": "vector"}],
            ],
            top_k=3,
        )

        self.assertEqual(fused[0]["chunk_id"], "b")
        self.assertEqual(set(fused[0]["retrieval_sources"]), {"bm25", "vector"})

    def test_hybrid_retriever_returns_citation_ready_chunks(self) -> None:
        hits = retrieve_hybrid_chunks(
            ESG_SCHEMA["anti_corruption_policy"],
            CHUNKS,
            top_k=2,
            industry="manufacturing",
        )

        self.assertEqual(hits[0]["chunk_id"], "c1")
        self.assertEqual(hits[0]["page_number"], 10)
        self.assertIn("retrieval_rank", hits[0])
        self.assertIn("rrf_score", hits[0])
        self.assertIn("rewritten_queries", hits[0])

    def test_retrieval_eval_reports_hit_rate_and_mrr(self) -> None:
        eval_result = evaluate_retrieval(
            [{"query_id": "q1", "field_key": "total_ghg_emissions", "expected_chunk_id": "c2"}],
            ESG_SCHEMA,
            CHUNKS,
            lambda field_item, chunks: retrieve_hybrid_chunks(field_item, chunks, top_k=2),
        )

        self.assertEqual(eval_result["total"], 1)
        self.assertEqual(eval_result["hit_rate_at_k"], 1.0)
        self.assertGreater(eval_result["mrr_at_k"], 0.0)


if __name__ == "__main__":
    unittest.main()
