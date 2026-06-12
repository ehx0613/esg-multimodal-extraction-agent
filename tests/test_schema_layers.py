import unittest

from config.schema import (
    CORE_SCHEMA_FIELD_COUNT,
    DISCLOSURE_TOPICS,
    ROUTE_B_CANDIDATE_SCHEMA,
    build_runtime_schema,
)


class SchemaLayerTests(unittest.TestCase):
    def test_candidate_route_b_does_not_change_core_count(self) -> None:
        self.assertEqual(CORE_SCHEMA_FIELD_COUNT, 60)
        self.assertEqual(len(ROUTE_B_CANDIDATE_SCHEMA), 15)

    def test_topics_reference_candidate_fields(self) -> None:
        candidates = {item["field_key"] for item in ROUTE_B_CANDIDATE_SCHEMA}
        referenced = {
            field_key
            for topic in DISCLOSURE_TOPICS
            for field_key in topic["candidate_field_keys"]
        }
        self.assertEqual(referenced, candidates)

    def test_runtime_schema_adds_industry_extensions(self) -> None:
        runtime = build_runtime_schema("pharma")
        self.assertGreater(len(runtime), CORE_SCHEMA_FIELD_COUNT)
        self.assertTrue(any(item["schema_layer"] == "industry_extension" for item in runtime))
        self.assertTrue(all("applicability" in item for item in runtime))


if __name__ == "__main__":
    unittest.main()
