import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from agents.schema_match_agent import SchemaMatchAgent


class MetricArtifactChainTests(unittest.TestCase):
    def test_schema_match_preserves_every_raw_metric(self) -> None:
        pages = [
            {
                "page_type": "performance_data_table",
                "page_number": 8,
                "page_image": "page_8.png",
                "tables": [
                    {
                        "table_title": "ESG performance",
                        "rows": [
                            {"metric_name": "Water", "unit": "t", "values": {"2024": "10"}},
                            {"metric_name": "Custom metric", "unit": "x", "values": {"2024": "2"}},
                        ],
                    }
                ],
            }
        ]
        matches = [
            {"matched": True, "field_key": "water_consumption", "confidence": 0.9, "reason": "test"},
            {"matched": False, "field_key": None, "confidence": 0.0, "reason": "no_match"},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            state = {"output_dir": Path(tmp), "all_table_rows": pages, "schema_match_allow_llm": False}
            with patch("agents.schema_match_agent.match_row_to_schema", side_effect=matches):
                result = SchemaMatchAgent().run(state)

            self.assertEqual(len(result["raw_table_metrics"]), 2)
            self.assertEqual(len(result["metric_candidates"]), 2)
            self.assertEqual(len(result["validated_metrics"]), 1)
            self.assertTrue((Path(tmp) / "raw_table_metrics.json").exists())
            self.assertTrue((Path(tmp) / "metric_candidates.json").exists())
            self.assertTrue((Path(tmp) / "validated_metrics.json").exists())


if __name__ == "__main__":
    unittest.main()
