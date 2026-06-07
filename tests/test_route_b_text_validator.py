import unittest

from utils.b_text_result_validator import validate_route_b_text_result


FIELD = {
    "field_key": "anti_corruption_policy",
    "forbidden_any": ["仅计划建立"],
}
CHUNKS = [
    {
        "chunk_id": "p10_1",
        "page_number": 10,
        "text": "公司建立反腐败政策，并设置举报人保护机制。",
    }
]


class RouteBTextValidatorTests(unittest.TestCase):
    def test_accepts_grounded_result(self) -> None:
        result = validate_route_b_text_result(
            FIELD,
            {
                "matched": True,
                "field_key": "anti_corruption_policy",
                "value": True,
                "evidence": "公司建立反腐败政策，并设置举报人保护机制。",
                "source_pages": [10],
                "confidence": 0.9,
            },
            CHUNKS,
        )

        self.assertTrue(result["matched"])
        self.assertTrue(result["route_b_validation_ok"])
        self.assertTrue(result["llm_matched_raw"])

    def test_rejects_hallucinated_evidence(self) -> None:
        result = validate_route_b_text_result(
            FIELD,
            {
                "matched": True,
                "field_key": "anti_corruption_policy",
                "value": True,
                "evidence": "公司建立了不存在于候选文本中的制度。",
                "source_pages": [10],
                "confidence": 0.9,
            },
            CHUNKS,
        )

        self.assertFalse(result["matched"])
        self.assertIn("evidence_not_in_retrieved_chunks", result["route_b_validation_reason"])

    def test_accepts_evidence_supported_across_multiple_chunks(self) -> None:
        chunks = [
            {"chunk_id": "p10_1", "page_number": 10, "text": "公司建立反腐败政策。"},
            {"chunk_id": "p10_2", "page_number": 10, "text": "公司设置举报人保护机制。"},
        ]
        result = validate_route_b_text_result(
            FIELD,
            {
                "matched": True,
                "field_key": "anti_corruption_policy",
                "value": True,
                "evidence": "公司建立反腐败政策，公司设置举报人保护机制。",
                "source_pages": [10],
                "confidence": 0.9,
            },
            chunks,
        )

        self.assertTrue(result["matched"])
        self.assertGreaterEqual(result["evidence_ngram_coverage"], 0.55)

    def test_rejects_page_outside_candidates(self) -> None:
        result = validate_route_b_text_result(
            FIELD,
            {
                "matched": True,
                "field_key": "anti_corruption_policy",
                "value": True,
                "evidence": "公司建立反腐败政策，并设置举报人保护机制。",
                "source_pages": [99],
                "confidence": 0.9,
            },
            CHUNKS,
        )

        self.assertFalse(result["matched"])
        self.assertIn("source_page_outside_retrieved_chunks", result["route_b_validation_reason"])

    def test_rejects_wrong_field_key(self) -> None:
        result = validate_route_b_text_result(
            FIELD,
            {
                "matched": True,
                "field_key": "whistleblowing_mechanism",
                "value": True,
                "evidence": "公司建立反腐败政策，并设置举报人保护机制。",
                "source_pages": [10],
                "confidence": 0.9,
            },
            CHUNKS,
        )

        self.assertFalse(result["matched"])
        self.assertIn("field_key_mismatch", result["route_b_validation_reason"])


if __name__ == "__main__":
    unittest.main()
