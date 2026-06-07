import unittest

from utils.simulated_rating import build_simulated_rating, field_score, rating_for_score


class SimulatedRatingTests(unittest.TestCase):
    def test_rating_for_score_uses_public_bands(self) -> None:
        self.assertEqual(rating_for_score(96), "AAA")
        self.assertEqual(rating_for_score(82), "BBB")
        self.assertEqual(rating_for_score(50), "C")

    def test_field_score_rewards_auto_cited_success(self) -> None:
        auto = {
            "status": "extracted",
            "value": "100",
            "confidence": "0.9",
            "citation_review_status": "auto_cited",
        }
        missing = {"status": "missing", "value": "", "citation_review_status": "needs_review"}

        self.assertGreater(field_score(auto), 90)
        self.assertEqual(field_score(missing), 0)

    def test_build_simulated_rating_aggregates_and_creates_review_queue(self) -> None:
        rows = [
            {
                "field_key": "total_ghg_emissions",
                "field_name_cn": "温室气体排放总量",
                "status": "extracted",
                "value": "2000",
                "confidence": "0.95",
                "citation_review_status": "auto_cited",
            },
            {
                "field_key": "climate_risk_management",
                "field_name_cn": "气候风险识别与管理",
                "status": "missing",
                "value": "",
                "citation_review_status": "needs_review",
                "citation_review_reasons": ["missing_existing_evidence"],
                "citation_page_number": 38,
                "citation_chunk_id": "p38_1",
            },
            {
                "field_key": "anti_corruption_policy",
                "field_name_cn": "反腐败政策",
                "status": "extracted",
                "value": True,
                "confidence": "0.9",
                "citation_review_status": "auto_cited",
            },
        ]

        result = build_simulated_rating(rows, industry="manufacturing")

        self.assertIn("E", result["pillar_scores"])
        self.assertIn("G", result["pillar_scores"])
        self.assertEqual(result["overall"]["needs_review_count"], 1)
        self.assertEqual(result["human_review_queue"][0]["field_key"], "climate_risk_management")
        self.assertGreater(result["overall"]["score"], 0)


if __name__ == "__main__":
    unittest.main()
