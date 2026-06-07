import unittest
from types import SimpleNamespace
from unittest.mock import patch

from utils.llm_schema_matcher import (
    _call_schema_judge,
    _should_escalate,
    llm_match_row_to_schema,
    select_schema_candidates,
    select_schema_candidates_with_diagnostics,
)
from utils.metric_normalizer import candidate_atom_score, candidate_compatibility, normalize_metric_row
from utils.schema_matcher import accept_llm_or_reject, is_index_row, match_row_to_schema


def make_row(
    metric_name: str = "",
    topic: str = "",
    table_title: str = "",
    evidence_text: str = "",
    unit: str = "",
    values: dict | None = None,
) -> dict:
    return {
        "metric_name": metric_name,
        "topic": topic,
        "table_title": table_title,
        "evidence_text": evidence_text,
        "unit": unit,
        "values": values or {"2024": "1"},
    }


class SchemaMatcherTests(unittest.TestCase):
    def test_metric_normalizer_distinguishes_employee_scopes(self) -> None:
        employee = normalize_metric_row(
            make_row(metric_name="女性比例", topic="员工构成", unit="%")
        )
        new_hire = normalize_metric_row(
            make_row(metric_name="女性比例", topic="新进员工构成", unit="%")
        )
        director = normalize_metric_row(
            make_row(metric_name="女性比例", topic="董事会成员按性别划分比例", unit="%")
        )

        self.assertEqual(employee["subject"], "employee")
        self.assertEqual(new_hire["subject"], "new_hire")
        self.assertEqual(director["subject"], "director")
        self.assertEqual(employee["aggregation"], "percentage")

    def test_candidate_prefilter_rejects_new_hire_as_all_employee_ratio(self) -> None:
        row = make_row(metric_name="女性比例", topic="新进员工构成", unit="%")
        candidate = next(
            item for item in select_schema_candidates(make_row(metric_name="女性员工比例", unit="%"), top_k=10)
            if item["field_key"] == "female_employee_ratio"
        )

        compatible, reason = candidate_compatibility(candidate, row)

        self.assertFalse(compatible)
        self.assertIn("mutex_scope:new_hire", reason)

    def test_semantic_judge_candidates_exclude_wrong_subject_and_measure(self) -> None:
        row = make_row(
            metric_name="女性比例",
            topic="董事会成员按性别划分比例",
            unit="%",
        )

        candidate_keys = {item["field_key"] for item in select_schema_candidates(row, top_k=10)}

        self.assertNotIn("female_employee_ratio", candidate_keys)
        self.assertNotIn("female_employees", candidate_keys)

        _, rejected = select_schema_candidates_with_diagnostics(row, top_k=10)
        self.assertIn("female_employee_ratio", rejected)
        self.assertIn("director", rejected["female_employee_ratio"])

    def test_candidate_prefilter_ignores_polluted_table_title(self) -> None:
        row = make_row(
            metric_name="废水排放量",
            topic="废水管理",
            table_title="环境维度指标-环保投入",
            evidence_text="废水管理 废水排放量",
            unit="吨",
        )

        candidate_keys = [item["field_key"] for item in select_schema_candidates(row, top_k=5)]

        self.assertEqual(candidate_keys[0], "wastewater_discharge")
        self.assertNotIn("environmental_investment", candidate_keys)

    def test_per_revenue_count_unit_is_classified_as_intensity(self) -> None:
        atoms = normalize_metric_row(
            make_row(
                metric_name="每百万元营收有效发明专利数",
                unit="件/百万元",
            )
        )

        self.assertEqual(atoms["unit_type"], "intensity")

    def test_energy_total_unit_rejects_energy_intensity_candidate(self) -> None:
        from config.schema import ESG_SCHEMA

        row = make_row(metric_name="综合能源消耗", unit="吨标准煤")
        result = candidate_atom_score(ESG_SCHEMA["energy_consumption_intensity"], row)

        self.assertFalse(result["compatible"])
        self.assertIn("unit_type:energy!=intensity", result["conflicts"])

    def test_person_time_unit_rejects_training_sessions_candidate(self) -> None:
        from config.schema import ESG_SCHEMA

        row = make_row(metric_name="廉洁培训参与人次", unit="人次")
        result = candidate_atom_score(ESG_SCHEMA["anti_corruption_training_sessions"], row)

        self.assertFalse(result["compatible"])
        self.assertIn("unit_type:person_time!=count", result["conflicts"])

    def test_global_atom_scoring_covers_environment_social_and_governance(self) -> None:
        cases = [
            (
                make_row(metric_name="综合能源消耗", topic="能源管理", unit="吨标准煤"),
                "energy_consumption_total",
            ),
            (
                make_row(metric_name="职业健康安全投入", topic="员工安全", unit="万元"),
                "occupational_health_safety_investment",
            ),
            (
                make_row(metric_name="廉洁培训参与人次", topic="反腐败管理", unit="人次"),
                "anti_corruption_training_participants",
            ),
        ]

        for row, expected_key in cases:
            expected = next(item for item in select_schema_candidates(row, top_k=5) if item["field_key"] == expected_key)
            result = candidate_atom_score(expected, row)
            self.assertTrue(result["compatible"], expected_key)
            self.assertGreater(result["score"], 0.0, expected_key)
            self.assertTrue(result["signals"], expected_key)

    def test_global_mutex_rejects_scope_and_subject_conflicts(self) -> None:
        rows_and_keys = [
            (make_row(metric_name="范围二温室气体排放量", unit="吨CO2e"), "scope_1_emissions"),
            (make_row(metric_name="危险废弃物产生量", unit="吨"), "non_hazardous_waste"),
            (make_row(metric_name="股东大会会议次数", unit="次"), "board_meetings"),
        ]

        from config.schema import ESG_SCHEMA

        for row, field_key in rows_and_keys:
            result = candidate_atom_score(ESG_SCHEMA[field_key], row)
            self.assertFalse(result["compatible"], field_key)
            self.assertTrue(result["conflicts"], field_key)

    def test_employee_structure_female_ratio_maps_without_llm(self) -> None:
        row = make_row(
            metric_name="女性比例",
            topic="员工构成",
            table_title="员工构成",
            evidence_text="员工构成 女性比例 % 2022年 52.12 2023年 49.32 2024年 46.72",
            unit="%",
            values={"2022年": "52.12", "2023年": "49.32", "2024年": "46.72"},
        )

        with patch("utils.schema_matcher.llm_match_row_to_schema") as llm_match:
            result = match_row_to_schema(row)

        llm_match.assert_not_called()
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "female_employee_ratio")
        self.assertEqual(result["confidence"], 0.96)

    def test_new_hire_female_ratio_does_not_map_to_all_employees(self) -> None:
        row = make_row(
            metric_name="女性比例",
            topic="新进员工构成-新进员工性别划分比例",
            table_title="社会维度指标-新进员工构成",
            evidence_text="新进员工构成 女性比例 % 2024年 39.27",
            unit="%",
            values={"2024年": "39.27"},
        )

        with patch(
            "utils.schema_matcher.llm_match_row_to_schema",
            return_value={"matched": False, "confidence": 0.0, "reason": "not_employee_ratio"},
        ):
            result = match_row_to_schema(row)

        self.assertFalse(result.get("matched"))

    def test_allow_llm_false_skips_schema_judge(self) -> None:
        row = make_row(
            metric_name="企业特色模糊指标",
            topic="特色实践",
            unit="项",
        )

        with patch("utils.schema_matcher.llm_match_row_to_schema") as llm_match:
            result = match_row_to_schema(row, allow_llm=False)

        llm_match.assert_not_called()
        self.assertFalse(result["matched"])

    def test_inherited_environmental_investment_title_does_not_hijack_wastewater(self) -> None:
        row = make_row(
            metric_name="废水排放量",
            topic="废水管理",
            table_title="环境维度指标-环保投入",
            evidence_text="环境维度指标-环保投入 废水管理 废水排放量 吨 2024年 271648",
            unit="吨",
            values={"2024年": "271648"},
        )

        with patch("utils.schema_matcher.llm_match_row_to_schema") as llm_match:
            result = match_row_to_schema(row)

        llm_match.assert_not_called()
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "wastewater_discharge")

    def test_schema_judge_uses_json_mode(self) -> None:
        calls = []

        class FakeCompletions:
            def create(self, **kwargs):
                calls.append(kwargs)
                return SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(
                                content='{"matched": true, "field_key": "environmental_investment", "confidence": 0.93, "reason": "匹配"}'
                            )
                        )
                    ]
                )

        client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
        candidates = select_schema_candidates(make_row(metric_name="绿色生态治理支出", unit="万元"), top_k=5)
        result = _call_schema_judge(client, "prompt", candidates, "qwen3.6-flash")

        self.assertTrue(result["matched"])
        self.assertEqual(calls[0]["response_format"], {"type": "json_object"})
        self.assertEqual(calls[0]["model"], "qwen3.6-flash")

    def test_schema_judge_escalates_only_middle_confidence(self) -> None:
        self.assertFalse(_should_escalate({"confidence": 0.95}))
        self.assertTrue(_should_escalate({"confidence": 0.70}))
        self.assertFalse(_should_escalate({"confidence": 0.20}))

    def test_schema_judge_escalates_from_flash_to_plus(self) -> None:
        calls = []
        responses = [
            '{"matched": true, "field_key": "environmental_investment", "confidence": 0.70, "reason": "可能匹配"}',
            '{"matched": true, "field_key": "environmental_investment", "confidence": 0.94, "reason": "确认匹配"}',
        ]

        class FakeCompletions:
            def create(self, **kwargs):
                calls.append(kwargs)
                return SimpleNamespace(
                    choices=[SimpleNamespace(message=SimpleNamespace(content=responses.pop(0)))]
                )

        client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
        row = make_row(
            metric_name="绿色生态治理支出",
            topic="环境保护",
            evidence_text="绿色生态治理支出",
            unit="万元",
            values={"2024": "300"},
        )
        with patch("utils.llm_schema_matcher._get_client", return_value=client):
            result = llm_match_row_to_schema(row)

        self.assertEqual([call["model"] for call in calls], ["qwen3.6-flash", "qwen3.6-plus"])
        self.assertTrue(result["judge_escalated"])
        self.assertEqual(result["judge_model"], "qwen3.6-plus")
        self.assertEqual(result["primary_judge"]["confidence"], 0.70)

    def test_semantic_judge_only_receives_top_k_candidates(self) -> None:
        row = make_row(
            metric_name="绿色生态治理支出",
            topic="环境保护",
            evidence_text="绿色生态治理支出",
            unit="万元",
            values={"2024": "300"},
        )
        candidates = select_schema_candidates(row, top_k=5)
        self.assertGreater(len(candidates), 0)
        self.assertLessEqual(len(candidates), 5)
        self.assertEqual(len({item["field_key"] for item in candidates}), len(candidates))
        self.assertIn("environmental_investment", {item["field_key"] for item in candidates})

    def test_semantic_judge_can_soft_accept_missing_required_alias(self) -> None:
        row = make_row(
            metric_name="绿色生态治理支出",
            topic="环境保护",
            evidence_text="绿色生态治理支出",
            unit="万元",
            values={"2024": "300"},
        )
        result = accept_llm_or_reject(
            "environmental_investment",
            0.93,
            "semantic_judge_match:语义对应环保投入",
            row,
        )
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "environmental_investment")
        self.assertIn("semantic_judge_soft_accept", result["reason"])

    def test_semantic_judge_soft_accept_still_rejects_wrong_unit(self) -> None:
        row = make_row(
            metric_name="绿色生态治理支出",
            topic="环境保护",
            evidence_text="绿色生态治理支出",
            unit="人",
            values={"2024": "300"},
        )
        result = accept_llm_or_reject(
            "environmental_investment",
            0.95,
            "semantic_judge_match:语义对应环保投入",
            row,
        )
        self.assertFalse(result["matched"])
        self.assertIn("unit_type_mismatch:money", result["reason"])

    def test_semantic_judge_soft_accept_requires_high_confidence(self) -> None:
        row = make_row(
            metric_name="绿色生态治理支出",
            topic="环境保护",
            evidence_text="绿色生态治理支出",
            unit="万元",
            values={"2024": "300"},
        )
        result = accept_llm_or_reject(
            "environmental_investment",
            0.80,
            "semantic_judge_match:语义对应环保投入",
            row,
        )
        self.assertFalse(result["matched"])
        self.assertIn("required_keyword_missing", result["reason"])

    def test_intensity_unit_accepts_per_product_denominator(self) -> None:
        row = make_row(
            metric_name="单位产品温室气体排放密度",
            evidence_text="单位产品温室气体排放密度",
            unit="吨二氧化碳当量/千产品",
            values={"2024": "7.21"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "ghg_emissions_intensity")

    def test_trained_employee_count_accepts_total_participants_label(self) -> None:
        row = make_row(
            metric_name="接受培训总人数",
            topic="员工培训",
            evidence_text="员工培训 接受培训总人数",
            unit="人",
            values={"2024": "3547"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "trained_employees_count")

    def test_index_row_is_filtered(self) -> None:
        row = make_row(
            metric_name="E.1 环境绩效",
            table_title="指标索引",
            evidence_text="目录 P42",
        )
        self.assertTrue(is_index_row("指标索引", row))

    def test_business_performance_is_not_core_esg(self) -> None:
        row = make_row(
            metric_name="营业收入",
            evidence_text="本年度营业收入",
            unit="万元",
        )
        result = match_row_to_schema(row)
        self.assertFalse(result["matched"])

    def test_asset_liability_ratio_is_filtered_as_business_noise(self) -> None:
        row = make_row(
            metric_name="资产负债率",
            evidence_text="资产负债率",
            unit="%",
            values={"2024": "42"},
        )
        result = match_row_to_schema(row)
        self.assertFalse(result["matched"])
        self.assertEqual(result["reason"], "business_performance_not_core_esg")

    def test_total_ghg_matches_total_not_scope(self) -> None:
        row = make_row(
            metric_name="温室气体排放总量",
            evidence_text="温室气体排放总量",
            unit="吨二氧化碳当量",
            values={"2024": "125285.17"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "total_ghg_emissions")

    def test_scope_1_matches_scope_1(self) -> None:
        row = make_row(
            metric_name="温室气体排放（范围一）",
            evidence_text="温室气体排放（范围一）",
            unit="二氧化碳当量公吨数",
            values={"2024": "124060.83"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "scope_1_emissions")

    def test_scope_2_accepts_metric_name_and_ghg_unit_variant(self) -> None:
        row = make_row(
            metric_name="温室气体排放（范围二）",
            evidence_text="温室气体排放（范围二）",
            unit="二氧化碳当量公吨数",
            values={"2024": "1224.34"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "scope_2_emissions")

    def test_water_consumption_alias_matches(self) -> None:
        row = make_row(
            metric_name="市政购水量",
            topic="水资源",
            evidence_text="市政购水量",
            unit="吨",
            values={"2024": "25041"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "water_consumption")

    def test_electricity_total_matches_electricity_consumption(self) -> None:
        row = make_row(
            metric_name="电力总量",
            topic="能源",
            evidence_text="电力总量",
            unit="千瓦时",
            values={"2024": "2281669"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "electricity_consumption")

    def test_tax_training_coverage_is_not_employee_training_coverage(self) -> None:
        row = make_row(
            metric_name="税务培训覆盖率",
            topic="治理绩效",
            evidence_text="税务培训覆盖率",
            unit="%",
            values={"2024": "95"},
        )
        result = match_row_to_schema(row)
        self.assertFalse(result["matched"])
        self.assertIn("forbidden_keyword_hit", result["reason"])

    def test_anti_bribery_training_coverage_is_not_employee_training_coverage(self) -> None:
        row = make_row(
            metric_name="反商业贿赂及反贪污培训覆盖率",
            evidence_text="反商业贿赂及反贪污培训覆盖率",
            unit="%",
            values={"2024": "100"},
        )
        result = match_row_to_schema(row)
        self.assertFalse(result["matched"])
        self.assertIn("forbidden_keyword_hit", result["reason"])

    def test_assisted_disadvantaged_employees_is_not_total_employees(self) -> None:
        row = make_row(
            metric_name="帮扶困难员工总人数",
            evidence_text="帮扶困难员工总人数 346人",
            unit="人",
            values={"2024": "346"},
        )
        result = match_row_to_schema(row, allow_llm=False)
        self.assertFalse(result["matched"])

    def test_training_total_hours_matches(self) -> None:
        row = make_row(
            metric_name="累计培训时长",
            evidence_text="累计培训时长",
            unit="小时",
            values={"2024": "2000"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "training_total_hours")

    def test_safety_training_total_hours_matches_training_hours(self) -> None:
        row = make_row(
            metric_name="安全培训总时长",
            topic="职业健康与安全生产",
            evidence_text="安全培训总时长",
            unit="小时",
            values={"2024": "1200"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "training_total_hours")

    def test_safety_accident_count_alias_matches(self) -> None:
        row = make_row(
            metric_name="生产安全事故数",
            topic="职业健康与安全生产",
            evidence_text="生产安全事故数",
            unit="次",
            values={"2024": "0"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "safety_accident_count")

    def test_short_female_dimension_uses_employee_context(self) -> None:
        row = make_row(
            metric_name="女性",
            table_title="期末在职员工结构（按性别）",
            evidence_text="女性",
            unit="人",
            values={"2024": "120"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "female_employees")

    def test_short_gender_without_employee_context_does_not_match(self) -> None:
        row = make_row(
            metric_name="女性",
            table_title="客户分类结构",
            evidence_text="女性",
            unit="人",
            values={"2024": "2"},
        )
        result = match_row_to_schema(row)
        self.assertFalse(result["matched"])

    def test_parental_leave_count_is_not_female_employee_total(self) -> None:
        row = make_row(
            metric_name="享受育儿假员工数",
            topic="员工构成 女性员工权益",
            evidence_text="员工构成 女性员工权益 享受育儿假员工数",
            unit="人",
            values={"2024": "24"},
        )
        result = match_row_to_schema(row)
        self.assertFalse(result["matched"])
        self.assertIn("forbidden_keyword_hit", result["reason"])

    def test_dimension_header_is_skipped(self) -> None:
        row = make_row(
            metric_name="按性别",
            table_title="期末在职员工结构",
            evidence_text="按性别",
            unit="",
            values={"2024": ""},
        )
        result = match_row_to_schema(row)
        self.assertFalse(result["matched"])
        self.assertEqual(result["reason"], "dimension_header_skip_match")

    def test_non_hazardous_waste_total_alias_matches(self) -> None:
        row = make_row(
            metric_name="无害废弃物产生总量",
            evidence_text="无害废弃物产生总量",
            unit="吨",
            values={"2024": "20"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "non_hazardous_waste")

    def test_energy_consumption_intensity_matches_new_core_field(self) -> None:
        row = make_row(
            metric_name="能源消耗强度",
            evidence_text="能源消耗强度",
            unit="吨标煤/万元",
            values={"2024": "0.2"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "energy_consumption_intensity")

    def test_ghg_emissions_intensity_matches_new_core_field(self) -> None:
        row = make_row(
            metric_name="温室气体排放强度",
            evidence_text="温室气体排放强度",
            unit="吨CO2e/万元",
            values={"2024": "0.8"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "ghg_emissions_intensity")

    def test_ghg_unit_pivot_accepts_emissions_label(self) -> None:
        row = make_row(
            metric_name="温室气体排放量",
            evidence_text="温室气体排放量 万吨二氧化碳当量 0.1131",
            unit="万吨二氧化碳当量",
            values={"2024": "0.1131"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "total_ghg_emissions")
        self.assertIn("unit_pivot", result["reason"])

    def test_ocr_water_electricity_typo_maps_to_water_consumption(self) -> None:
        row = make_row(
            metric_name="年使用水电总量",
            evidence_text="年使用水电总量 立方米 4810",
            unit="立方米",
            values={"2024": "4810"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "water_consumption")

    def test_per_capita_electricity_does_not_pollute_total(self) -> None:
        row = make_row(
            metric_name="总行人均用电量",
            evidence_text="总行人均用电量（度/人） 2024年 2796",
            unit="度/人",
            values={"2024": "2796"},
        )
        result = match_row_to_schema(row)
        self.assertFalse(result["matched"])
        self.assertIn("intensity_or_per_capita_not_total_field", result["reason"])

    def test_social_security_coverage_matches_new_core_field(self) -> None:
        row = make_row(
            metric_name="社会保险覆盖率",
            evidence_text="社会保险覆盖率",
            unit="%",
            values={"2024": "100"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "social_security_coverage")

    def test_health_archive_checkup_coverage_matches(self) -> None:
        row = make_row(
            metric_name="体检及健康档案覆盖率",
            evidence_text="体检及健康档案覆盖率 % 100",
            unit="%",
            values={"2024": "100"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "employee_medical_checkup_coverage")

    def test_cumulative_training_participants_matches(self) -> None:
        row = make_row(
            metric_name="全年累计培训员工人次",
            evidence_text="全年累计培训员工人次 人次 378",
            unit="人次",
            values={"2024": "378"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "trained_employees_count")

    def test_virtual_wastewater_subsidiary_row_matches(self) -> None:
        row = make_row(
            metric_name="通辽圣达",
            table_title="2025 年废水排放情况",
            evidence_text="通辽圣达 排放总量（吨） 896,171",
            unit="吨",
            values={"排放总量（吨）": "896171", "达标排放情况": "无"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "wastewater_discharge")
        self.assertIn("virtual_metric", result["reason"])

    def test_natural_gas_consumption_matches_new_core_field(self) -> None:
        row = make_row(
            metric_name="天然气",
            evidence_text="天然气",
            unit="万立方米",
            values={"2024": "12"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "natural_gas_consumption")

    def test_safety_production_investment_matches_new_core_field(self) -> None:
        row = make_row(
            metric_name="安全生产投入",
            evidence_text="安全生产投入",
            unit="万元",
            values={"2024": "80"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "occupational_health_safety_investment")

    def test_parenthetical_unit_is_normalized_for_alias_override(self) -> None:
        row = make_row(
            metric_name="环保总投资（万元）",
            evidence_text="环保总投资（万元）",
            unit="万元",
            values={"2024": "100"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "environmental_investment")

    def test_environmental_total_input_alias_matches(self) -> None:
        row = make_row(
            metric_name="环保总投入",
            evidence_text="环保总投入",
            unit="万元",
            values={"2024": "149.47"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "environmental_investment")

    def test_company_r_and_d_total_alias_matches(self) -> None:
        row = make_row(
            metric_name="公司研发总投入",
            evidence_text="公司研发总投入",
            unit="万元",
            values={"2024": "4473.75"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "r_and_d_expense")

    def test_fuzzy_alias_handles_close_social_security_label(self) -> None:
        row = make_row(
            metric_name="社会保险复盖率",
            evidence_text="社会保险复盖率",
            unit="%",
            values={"2024": "100"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "social_security_coverage")

    def test_density_alias_maps_to_intensity_field(self) -> None:
        row = make_row(
            metric_name="温室气体排放密度",
            evidence_text="温室气体排放密度",
            unit="吨CO2e/万元",
            values={"2024": "0.8"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "ghg_emissions_intensity")

    def test_public_welfare_donation_amount_matches(self) -> None:
        row = make_row(
            metric_name="对外捐赠金额",
            evidence_text="对外捐赠金额",
            unit="万元",
            values={"2024": "300"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "public_welfare_investment")

    def test_board_size_alias_matches(self) -> None:
        row = make_row(
            metric_name="董事会成员人数",
            topic="三会治理",
            evidence_text="董事会成员人数",
            unit="人",
            values={"2024": "9"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "board_size")

    def test_committee_independent_director_ratio_is_not_company_ratio(self) -> None:
        row = make_row(
            metric_name="审计委员会独董占比",
            evidence_text="审计委员会独董占比",
            unit="%",
            values={"2024": "66.67"},
        )
        result = match_row_to_schema(row)
        self.assertFalse(result["matched"])
        self.assertIn("forbidden_keyword_hit", result["reason"])

    def test_special_committee_meetings_do_not_match_board_meetings(self) -> None:
        row = make_row(
            metric_name="召开董事会各专门委员会次数",
            topic="董事会各专门委员会",
            evidence_text="召开董事会各专门委员会次数",
            unit="次",
            values={"2024": "8"},
        )
        result = match_row_to_schema(row)
        self.assertFalse(result["matched"])
        self.assertIn("forbidden_keyword_hit", result["reason"])

    def test_management_gender_count_is_not_total_gender_employee_count(self) -> None:
        row = make_row(
            metric_name="高级管理层的女性员工数量",
            evidence_text="高级管理层的女性员工数量",
            unit="人",
            values={"2024": "3"},
        )
        result = match_row_to_schema(row)
        self.assertFalse(result["matched"])
        self.assertIn("forbidden_keyword_hit", result["reason"])

    def test_percentage_field_rejects_person_unit(self) -> None:
        row = make_row(
            metric_name="独立董事比例",
            evidence_text="独立董事比例",
            unit="人",
            values={"2024": "33.3"},
        )
        result = match_row_to_schema(row)
        self.assertFalse(result["matched"])
        self.assertIn("unit_type_mismatch:percentage", result["reason"])

    def test_percentage_field_accepts_percentage_unit(self) -> None:
        row = make_row(
            metric_name="独立董事比例",
            evidence_text="独立董事比例",
            unit="%",
            values={"2024": "33.3"},
        )
        result = match_row_to_schema(row)
        self.assertTrue(result["matched"])
        self.assertEqual(result["field_key"], "independent_director_ratio")

    def test_quantitative_field_requires_numeric_value(self) -> None:
        row = make_row(
            metric_name="温室气体排放总量",
            evidence_text="温室气体排放总量",
            unit="吨二氧化碳当量",
            values={"2024": "应对气候变化"},
        )
        result = match_row_to_schema(row)
        self.assertFalse(result["matched"])
        self.assertIn("quantitative_field_requires_numeric_value", result["reason"])

    def test_route_b_field_is_not_allowed_in_table_mapping(self) -> None:
        row = make_row(
            metric_name="气候风险管理",
            evidence_text="公司识别并管理气候变化风险",
            unit="",
            values={"2024": "1"},
        )
        result = match_row_to_schema(row)
        self.assertFalse(result["matched"])


if __name__ == "__main__":
    unittest.main()
