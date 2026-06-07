import unittest

from config.schema import ESG_FIELD_KEYS
from config.schema.huazheng_public_mapping import (
    FIELD_FRAMEWORK_MAP,
    FIELD_FRAMEWORK_MAPPINGS,
    KEY_INDICATOR_INDEX,
    framework_summary,
    get_applicable_field_keys,
    get_mapping_for_field,
)


class HuazhengPublicMappingTests(unittest.TestCase):
    def test_public_framework_shape(self) -> None:
        self.assertEqual(
            framework_summary(),
            {
                "pillars": 3,
                "themes": 16,
                "key_indicators": 44,
                "mapped_project_fields": len(ESG_FIELD_KEYS),
            },
        )

    def test_all_core_fields_are_mapped(self) -> None:
        self.assertEqual(set(FIELD_FRAMEWORK_MAP), set(ESG_FIELD_KEYS))
        self.assertEqual(len(FIELD_FRAMEWORK_MAPPINGS), len(ESG_FIELD_KEYS))

    def test_mappings_point_to_known_key_indicators(self) -> None:
        for mapping in FIELD_FRAMEWORK_MAPPINGS:
            self.assertIn(mapping["key_indicator"], KEY_INDICATOR_INDEX)
            self.assertEqual(
                mapping["theme_key"],
                KEY_INDICATOR_INDEX[mapping["key_indicator"]]["theme_key"],
            )

    def test_mapping_enriches_field_with_framework_labels(self) -> None:
        mapping = get_mapping_for_field("total_ghg_emissions")

        self.assertIsNotNone(mapping)
        self.assertEqual(mapping["pillar"], "E")
        self.assertEqual(mapping["theme_key"], "climate_change")
        self.assertEqual(mapping["key_indicator"], "ghg_emissions")
        self.assertEqual(mapping["indicator_name_cn"], "温室气体排放")

    def test_industry_applicability_keeps_general_fields(self) -> None:
        finance_fields = set(get_applicable_field_keys("financial"))

        self.assertIn("board_esg_oversight", finance_fields)
        self.assertIn("anti_corruption_policy", finance_fields)
        self.assertIn("data_security_privacy", finance_fields)
        self.assertNotIn("hazardous_waste", finance_fields)


if __name__ == "__main__":
    unittest.main()
