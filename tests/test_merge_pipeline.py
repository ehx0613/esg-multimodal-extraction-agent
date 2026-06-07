import unittest

from pipeline.merge_pipeline import (
    apply_missing_status,
    apply_route_b_to_merged,
    apply_route_b2_to_merged,
    normalize_route_a_row,
)


def make_route_a_row(value="0", confidence="0.86", status="extracted"):
    return {
        "field_key": "energy_consumption_total",
        "field_name_cn": "能源消耗总量",
        "category": "E",
        "indicator_type": "quantitative",
        "value_type": "number",
        "status": status,
        "value": value,
        "raw_value": value,
        "unit": "吨标准煤",
        "year": "2024",
        "confidence": confidence,
        "match_reason": "route_a_test",
        "evidence_text": "能源消耗总量 0",
        "page_image": "page_1.png",
    }


def make_b2_row(value="120", confidence="0.9", evidence="能源消耗总量为120吨标准煤"):
    return {
        "field_key": "energy_consumption_total",
        "matched": "true",
        "confidence": confidence,
        "value": value,
        "raw_value": value,
        "unit": "吨标准煤",
        "year": "2024",
        "evidence": evidence,
        "source_pages": "[2]",
        "reason": "b2_test",
        "b2_validation_ok": "true",
        "field_name_cn": "能源消耗总量",
    }


class MergePipelineTests(unittest.TestCase):
    def test_budget_exhausted_is_not_marked_not_disclosed(self):
        item = normalize_route_a_row(make_route_a_row(value="", confidence="0", status="missing"))

        apply_missing_status(
            item,
            applicability="core",
            industry="manufacturing",
            budget_exhausted_keys={item["field_key"]},
        )

        self.assertEqual(item["status"], "extraction_incomplete_budget_exhausted")
        self.assertEqual(item["missing_reason"], "extraction_incomplete_budget_exhausted")

    def test_route_b_requires_post_validation(self):
        item = normalize_route_a_row(make_route_a_row(value="", confidence="0", status="missing"))
        merged_by_key = {item["field_key"]: item}
        row = {
            "field_key": item["field_key"],
            "matched": "true",
            "confidence": "0.9",
            "value": "true",
            "evidence": "unsupported",
            "source_pages": "[2]",
            "route_b_validation_ok": "false",
        }

        apply_route_b_to_merged(merged_by_key, [row])

        self.assertEqual(merged_by_key[item["field_key"]]["status"], "missing")

    def test_b2_overrides_route_a_zero_with_evidence(self):
        item = normalize_route_a_row(make_route_a_row(value="0", confidence="0.86"))
        merged_by_key = {item["field_key"]: item}

        apply_route_b2_to_merged(merged_by_key, [make_b2_row(value="120", confidence="0.9")])

        merged = merged_by_key["energy_consumption_total"]
        self.assertEqual(merged["value"], "120")
        self.assertEqual(merged["source_route"], "route_b_quantitative_fallback")
        self.assertIn("route_b2_override_route_a_zero_with_evidence", merged["merge_reason"])

    def test_b2_does_not_override_nonzero_route_a(self):
        item = normalize_route_a_row(make_route_a_row(value="100", confidence="0.86"))
        merged_by_key = {item["field_key"]: item}

        apply_route_b2_to_merged(merged_by_key, [make_b2_row(value="120", confidence="0.95")])

        merged = merged_by_key["energy_consumption_total"]
        self.assertEqual(merged["value"], "100")
        self.assertEqual(merged["source_route"], "route_a_appendix_table")
        self.assertEqual(merged["merge_reason"], "route_a_kept_over_b2")

    def test_b2_without_evidence_does_not_override_route_a_zero(self):
        item = normalize_route_a_row(make_route_a_row(value="0", confidence="0.86"))
        merged_by_key = {item["field_key"]: item}

        apply_route_b2_to_merged(merged_by_key, [make_b2_row(value="120", confidence="0.95", evidence="")])

        merged = merged_by_key["energy_consumption_total"]
        self.assertEqual(merged["value"], "0")
        self.assertEqual(merged["source_route"], "route_a_appendix_table")
        self.assertEqual(merged["merge_reason"], "route_a_kept_b2_missing_evidence")

    def test_b2_total_water_overrides_route_a_fresh_water_scope(self):
        route_a = make_route_a_row(value="383850", confidence="0.92")
        route_a["field_key"] = "water_consumption"
        route_a["field_name_cn"] = "用水量"
        route_a["evidence_text"] = "水资源管理 新鲜水取水总量 383,850 吨"
        item = normalize_route_a_row(route_a)
        merged_by_key = {item["field_key"]: item}
        b2 = make_b2_row(value="460687", confidence="0.95", evidence="水资源管理 总用水量 460,687 吨")
        b2["field_key"] = "water_consumption"
        b2["year"] = "2024"

        apply_route_b2_to_merged(merged_by_key, [b2])

        merged = merged_by_key["water_consumption"]
        self.assertEqual(merged["value"], "460687")
        self.assertEqual(merged["source_route"], "route_b_quantitative_fallback")
        self.assertIn("route_b2_override_route_a_preferred_scope", merged["merge_reason"])

    def test_b2_rejects_supply_shortage_drill_as_safety_drill(self):
        route_a = make_route_a_row(value="", confidence="0", status="missing")
        route_a["field_key"] = "safety_emergency_drill_count"
        item = normalize_route_a_row(route_a)
        merged_by_key = {item["field_key"]: item}
        b2 = make_b2_row(
            value="2",
            confidence="0.95",
            evidence="公司组织了两次关键原材料供应不足应急演练",
        )
        b2["field_key"] = "safety_emergency_drill_count"

        apply_route_b2_to_merged(merged_by_key, [b2])

        self.assertEqual(merged_by_key["safety_emergency_drill_count"]["status"], "missing")


if __name__ == "__main__":
    unittest.main()
