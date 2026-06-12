import unittest

from config.core_schema import CORE_SCHEMA, schema_summary
from config.schema import (
    CORE_SCHEMA_FIELD_COUNT,
    CORE_SCHEMA_VERSION,
    ESG_SCHEMA,
    ROUTE_A_FIELD_KEYS,
    ROUTE_B_FIELD_KEYS,
)


class SchemaStructureTests(unittest.TestCase):
    def test_core_schema_total_count(self) -> None:
        self.assertEqual(len(CORE_SCHEMA), 60)
        self.assertEqual(CORE_SCHEMA_FIELD_COUNT, 60)
        self.assertEqual(CORE_SCHEMA_VERSION, "core_esg_v4.1_60")

    def test_schema_summary_counts(self) -> None:
        self.assertEqual(
            schema_summary(),
            {
                "total": 60,
                "route_a": 42,
                "route_b": 18,
                "quantitative": 42,
                "qualitative": 18,
                "E": 21,
                "S": 24,
                "G": 15,
            },
        )

    def test_route_boundaries_are_clean(self) -> None:
        for field_key in ROUTE_A_FIELD_KEYS:
            self.assertEqual(ESG_SCHEMA[field_key]["indicator_type"], "quantitative")
            self.assertNotEqual(ESG_SCHEMA[field_key]["preferred_source"], "main_text_rag")

        for field_key in ROUTE_B_FIELD_KEYS:
            self.assertEqual(ESG_SCHEMA[field_key]["indicator_type"], "qualitative")
            self.assertEqual(ESG_SCHEMA[field_key]["preferred_source"], "main_text_rag")

    def test_key_fields_are_present(self) -> None:
        expected = {
            "total_ghg_emissions",
            "energy_consumption_intensity",
            "ghg_emissions_intensity",
            "social_security_coverage",
            "occupational_health_safety_investment",
            "environmental_penalty_count",
            "training_total_hours",
            "r_and_d_expense",
            "board_esg_oversight",
            "climate_risk_management",
            "data_security_privacy",
            "anti_corruption_policy",
        }
        self.assertTrue(expected.issubset(set(ESG_SCHEMA)))

    def test_all_route_a_fields_have_global_atom_metadata(self) -> None:
        for field_key in ROUTE_A_FIELD_KEYS:
            item = ESG_SCHEMA[field_key]
            self.assertTrue(item.get("atoms"), field_key)
            self.assertTrue(item.get("mutex"), field_key)


if __name__ == "__main__":
    unittest.main()
