import unittest

from utils.table_arbitrator import apply_arbitration_candidates, extract_arbitration_candidates


class TableArbitratorTests(unittest.TestCase):
    def test_extract_candidates_reuses_schema_matcher(self):
        prepared = [
            {
                "status": "image_prepared",
                "image_path": "region_1_page_8.png",
                "source_region_id": "p8_table_0",
                "page_number": 8,
                "bbox": [1, 2, 3, 4],
                "reasons": ["cross_source_conflict"],
            }
        ]

        def extractor(_):
            return {
                "page_type": "performance_data_table",
                "tables": [
                    {
                        "table_title": "Environment",
                        "rows": [
                            {
                                "topic": "水资源",
                                "metric_name": "市政购水量",
                                "unit": "吨",
                                "values": {"2024": "100"},
                                "evidence_text": "市政购水量 2024 100 吨",
                            }
                        ],
                    }
                ],
            }

        result = extract_arbitration_candidates(prepared, extractor=extractor)

        self.assertEqual(len(result["region_results"]), 1)
        self.assertEqual(len(result["candidates"]), 1)
        self.assertEqual(result["candidates"][0]["source_type"], "visual_arbitration")
        self.assertEqual(result["candidates"][0]["source_page"], 8)

    def test_missing_field_is_filled_but_existing_field_requires_review(self):
        standard = {
            "water_consumption": {
                "field_key": "water_consumption",
                "status": "missing",
                "value": None,
                "confidence": 0.0,
            },
            "electricity_consumption": {
                "field_key": "electricity_consumption",
                "status": "extracted",
                "value": 50,
                "confidence": 0.9,
                "page_image": "page_8.png",
            },
        }
        candidates = [
            {
                "field_key": "water_consumption",
                "status": "extracted",
                "value": 100,
                "confidence": 0.8,
                "source_page": 8,
                "arbitration_reasons": [],
            },
            {
                "field_key": "electricity_consumption",
                "status": "extracted",
                "value": 999,
                "confidence": 0.7,
                "source_page": 8,
                "arbitration_reasons": ["cross_source_conflict"],
            },
        ]

        result = apply_arbitration_candidates(standard, candidates)

        self.assertEqual(result["standard_results"]["water_consumption"]["value"], 100)
        self.assertEqual(result["standard_results"]["electricity_consumption"]["value"], 50)
        self.assertEqual(len(result["applied_updates"]), 1)
        self.assertEqual(len(result["proposed_updates"]), 1)

    def test_region_vlm_error_is_isolated(self):
        prepared = [
            {
                "status": "image_prepared",
                "image_path": "region_1_page_8.png",
                "source_region_id": "p8_table_0",
                "page_number": 8,
                "bbox": [1, 2, 3, 4],
            }
        ]

        result = extract_arbitration_candidates(
            prepared,
            extractor=lambda _: (_ for _ in ()).throw(ConnectionError("network blocked")),
        )

        self.assertEqual(result["candidates"], [])
        self.assertEqual(result["region_results"][0]["status"], "vlm_error")


if __name__ == "__main__":
    unittest.main()
