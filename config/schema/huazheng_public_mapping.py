# -*- coding: utf-8 -*-
"""
Huazheng-public ESG framework mapping.

This module adds a business-framework layer above the existing Core ESG
field schema. It does not replace `config.schema.all_data`; instead, it maps
the project's bottom-level extractable fields to the public Huazheng ESG
rating structure:

    pillar -> theme -> key indicator -> project data point

Source boundary:
- The 3 pillars, 16 themes, 44 key indicators, and rating bands are based on
  public Huazheng ESG methodology V2.1.
- Field mappings, industry applicability, and scoring usage are project-side
  design choices for an ESG data-production agent. They are not Huazheng's
  internal scoring model.
"""

from __future__ import annotations

from typing import Any, Dict, List


SCHEMA_VERSION = "huazheng_public_v1"

ALL_INDUSTRIES = ["all"]
HIGH_ENVIRONMENTAL_IMPACT_INDUSTRIES = [
    "manufacturing",
    "chemical",
    "energy",
    "utilities",
    "materials",
]
KNOWLEDGE_AND_TECH_INDUSTRIES = [
    "technology",
    "pharma",
    "manufacturing",
]
CONSUMER_AND_SERVICE_INDUSTRIES = [
    "consumer",
    "healthcare",
    "financial",
    "technology",
]


HUAZHENG_PUBLIC_FRAMEWORK: List[Dict[str, Any]] = [
    {
        "pillar": "E",
        "pillar_name_cn": "环境",
        "themes": [
            {
                "theme_key": "climate_change",
                "theme_name_cn": "气候变化",
                "key_indicators": [
                    {"indicator_key": "ghg_emissions", "indicator_name_cn": "温室气体排放"},
                    {"indicator_key": "carbon_reduction_pathway", "indicator_name_cn": "碳减排路线"},
                    {"indicator_key": "climate_change_response", "indicator_name_cn": "应对气候变化"},
                    {"indicator_key": "sponge_city", "indicator_name_cn": "海绵城市"},
                    {"indicator_key": "green_finance", "indicator_name_cn": "绿色金融"},
                ],
            },
            {
                "theme_key": "resource_utilization",
                "theme_name_cn": "资源利用",
                "key_indicators": [
                    {"indicator_key": "land_use_biodiversity", "indicator_name_cn": "土地利用及生物多样性"},
                    {"indicator_key": "water_resource_consumption", "indicator_name_cn": "水资源消耗"},
                    {"indicator_key": "material_consumption", "indicator_name_cn": "材料消耗"},
                ],
            },
            {
                "theme_key": "environmental_pollution",
                "theme_name_cn": "环境污染",
                "key_indicators": [
                    {"indicator_key": "industrial_emissions", "indicator_name_cn": "工业排放"},
                    {"indicator_key": "hazardous_waste", "indicator_name_cn": "有害垃圾"},
                    {"indicator_key": "electronic_waste", "indicator_name_cn": "电子垃圾"},
                ],
            },
            {
                "theme_key": "environmentally_friendly",
                "theme_name_cn": "环境友好",
                "key_indicators": [
                    {"indicator_key": "renewable_energy", "indicator_name_cn": "可再生能源"},
                    {"indicator_key": "green_building", "indicator_name_cn": "绿色建筑"},
                    {"indicator_key": "green_factory", "indicator_name_cn": "绿色工厂"},
                ],
            },
            {
                "theme_key": "environmental_management",
                "theme_name_cn": "环境管理",
                "key_indicators": [
                    {"indicator_key": "sustainable_certification", "indicator_name_cn": "可持续认证"},
                    {"indicator_key": "supply_chain_management_e", "indicator_name_cn": "供应链管理-E"},
                    {"indicator_key": "environmental_penalty", "indicator_name_cn": "环保处罚"},
                ],
            },
        ],
    },
    {
        "pillar": "S",
        "pillar_name_cn": "社会",
        "themes": [
            {
                "theme_key": "human_capital",
                "theme_name_cn": "人力资本",
                "key_indicators": [
                    {"indicator_key": "employee_health_safety", "indicator_name_cn": "员工健康与安全"},
                    {"indicator_key": "employee_incentive_development", "indicator_name_cn": "员工激励和发展"},
                    {"indicator_key": "employee_relations", "indicator_name_cn": "员工关系"},
                ],
            },
            {
                "theme_key": "product_responsibility",
                "theme_name_cn": "产品责任",
                "key_indicators": [
                    {"indicator_key": "quality_certification", "indicator_name_cn": "品质认证"},
                    {"indicator_key": "recall", "indicator_name_cn": "召回"},
                    {"indicator_key": "complaints", "indicator_name_cn": "投诉"},
                ],
            },
            {
                "theme_key": "supply_chain",
                "theme_name_cn": "供应链",
                "key_indicators": [
                    {"indicator_key": "supplier_risk_management", "indicator_name_cn": "供应商风险和管理"},
                    {"indicator_key": "supply_chain_relationship", "indicator_name_cn": "供应链关系"},
                ],
            },
            {
                "theme_key": "social_contribution",
                "theme_name_cn": "社会贡献",
                "key_indicators": [
                    {"indicator_key": "inclusive_benefit", "indicator_name_cn": "普惠"},
                    {"indicator_key": "community_investment", "indicator_name_cn": "社区投资"},
                    {"indicator_key": "employment", "indicator_name_cn": "就业"},
                    {"indicator_key": "technology_innovation", "indicator_name_cn": "科技创新"},
                ],
            },
            {
                "theme_key": "data_security_privacy",
                "theme_name_cn": "数据安全与隐私",
                "key_indicators": [
                    {"indicator_key": "data_security_privacy", "indicator_name_cn": "数据安全与隐私"},
                ],
            },
        ],
    },
    {
        "pillar": "G",
        "pillar_name_cn": "公司治理",
        "themes": [
            {
                "theme_key": "shareholder_rights",
                "theme_name_cn": "股东权益",
                "key_indicators": [
                    {"indicator_key": "shareholder_rights_protection", "indicator_name_cn": "股东权益保护"},
                ],
            },
            {
                "theme_key": "governance_structure",
                "theme_name_cn": "治理结构",
                "key_indicators": [
                    {"indicator_key": "esg_governance", "indicator_name_cn": "ESG治理"},
                    {"indicator_key": "risk_control", "indicator_name_cn": "风险控制"},
                    {"indicator_key": "board_structure", "indicator_name_cn": "董事会结构"},
                    {"indicator_key": "management_stability", "indicator_name_cn": "管理层稳定性"},
                ],
            },
            {
                "theme_key": "disclosure_quality",
                "theme_name_cn": "信披质量",
                "key_indicators": [
                    {"indicator_key": "esg_external_assurance", "indicator_name_cn": "ESG外部鉴证"},
                    {"indicator_key": "disclosure_credibility", "indicator_name_cn": "信息披露可信度"},
                ],
            },
            {
                "theme_key": "governance_risk",
                "theme_name_cn": "治理风险",
                "key_indicators": [
                    {"indicator_key": "major_shareholder_behavior", "indicator_name_cn": "大股东行为"},
                    {"indicator_key": "solvency", "indicator_name_cn": "偿债能力"},
                    {"indicator_key": "legal_litigation", "indicator_name_cn": "法律诉讼"},
                    {"indicator_key": "tax_transparency", "indicator_name_cn": "税收透明度"},
                ],
            },
            {
                "theme_key": "external_sanctions",
                "theme_name_cn": "外部处分",
                "key_indicators": [
                    {"indicator_key": "external_sanctions", "indicator_name_cn": "外部处分"},
                ],
            },
            {
                "theme_key": "business_ethics",
                "theme_name_cn": "商业道德",
                "key_indicators": [
                    {"indicator_key": "business_ethics", "indicator_name_cn": "商业道德"},
                    {"indicator_key": "anti_corruption_bribery", "indicator_name_cn": "反贪污和贿赂"},
                ],
            },
        ],
    },
]

RATING_BANDS = [
    {"rating": "AAA", "min_score": 95, "max_score": 100},
    {"rating": "AA", "min_score": 90, "max_score": 95},
    {"rating": "A", "min_score": 85, "max_score": 90},
    {"rating": "BBB", "min_score": 80, "max_score": 85},
    {"rating": "BB", "min_score": 75, "max_score": 80},
    {"rating": "B", "min_score": 70, "max_score": 75},
    {"rating": "CCC", "min_score": 65, "max_score": 70},
    {"rating": "CC", "min_score": 60, "max_score": 65},
    {"rating": "C", "min_score": 0, "max_score": 60},
]


def _field(
    field_key: str,
    theme_key: str,
    indicator_key: str,
    applicable_industries: List[str],
    score_usage: str = "scoring",
    evidence_priority: str = "normal",
) -> Dict[str, Any]:
    return {
        "field_key": field_key,
        "schema_version": SCHEMA_VERSION,
        "theme_key": theme_key,
        "key_indicator": indicator_key,
        "applicable_industries": applicable_industries,
        "score_usage": score_usage,
        "evidence_priority": evidence_priority,
    }


FIELD_FRAMEWORK_MAPPINGS: List[Dict[str, Any]] = [
    _field("total_ghg_emissions", "climate_change", "ghg_emissions", HIGH_ENVIRONMENTAL_IMPACT_INDUSTRIES, evidence_priority="high"),
    _field("ghg_emissions_intensity", "climate_change", "ghg_emissions", HIGH_ENVIRONMENTAL_IMPACT_INDUSTRIES, evidence_priority="high"),
    _field("scope_1_emissions", "climate_change", "ghg_emissions", HIGH_ENVIRONMENTAL_IMPACT_INDUSTRIES, evidence_priority="high"),
    _field("scope_2_emissions", "climate_change", "ghg_emissions", HIGH_ENVIRONMENTAL_IMPACT_INDUSTRIES, evidence_priority="high"),
    _field("energy_consumption_total", "climate_change", "carbon_reduction_pathway", HIGH_ENVIRONMENTAL_IMPACT_INDUSTRIES, evidence_priority="high"),
    _field("energy_consumption_intensity", "climate_change", "carbon_reduction_pathway", HIGH_ENVIRONMENTAL_IMPACT_INDUSTRIES, evidence_priority="high"),
    _field("natural_gas_consumption", "climate_change", "carbon_reduction_pathway", HIGH_ENVIRONMENTAL_IMPACT_INDUSTRIES),
    _field("electricity_consumption", "climate_change", "carbon_reduction_pathway", HIGH_ENVIRONMENTAL_IMPACT_INDUSTRIES),
    _field("water_consumption", "resource_utilization", "water_resource_consumption", HIGH_ENVIRONMENTAL_IMPACT_INDUSTRIES, evidence_priority="high"),
    _field("wastewater_discharge", "environmental_pollution", "industrial_emissions", HIGH_ENVIRONMENTAL_IMPACT_INDUSTRIES),
    _field("air_pollutant_emissions", "environmental_pollution", "industrial_emissions", HIGH_ENVIRONMENTAL_IMPACT_INDUSTRIES),
    _field("non_hazardous_waste", "environmental_pollution", "industrial_emissions", HIGH_ENVIRONMENTAL_IMPACT_INDUSTRIES),
    _field("hazardous_waste", "environmental_pollution", "hazardous_waste", HIGH_ENVIRONMENTAL_IMPACT_INDUSTRIES, evidence_priority="high"),
    _field("environmental_investment", "environmental_management", "sustainable_certification", HIGH_ENVIRONMENTAL_IMPACT_INDUSTRIES),
    _field("environmental_penalty_count", "environmental_management", "environmental_penalty", ALL_INDUSTRIES, evidence_priority="high"),
    _field("total_employees", "social_contribution", "employment", ALL_INDUSTRIES),
    _field("male_employees", "human_capital", "employee_relations", ALL_INDUSTRIES, score_usage="display_only"),
    _field("female_employees", "human_capital", "employee_relations", ALL_INDUSTRIES, score_usage="display_only"),
    _field("female_employee_ratio", "human_capital", "employee_relations", ALL_INDUSTRIES),
    _field("employee_turnover_rate", "human_capital", "employee_relations", ALL_INDUSTRIES),
    _field("training_total_hours", "human_capital", "employee_incentive_development", ALL_INDUSTRIES),
    _field("training_hours_per_employee", "human_capital", "employee_incentive_development", ALL_INDUSTRIES),
    _field("training_coverage_rate", "human_capital", "employee_incentive_development", ALL_INDUSTRIES),
    _field("social_security_coverage", "human_capital", "employee_relations", ALL_INDUSTRIES),
    _field("employee_medical_checkup_coverage", "human_capital", "employee_health_safety", ALL_INDUSTRIES),
    _field("trained_employees_count", "human_capital", "employee_incentive_development", ALL_INDUSTRIES, score_usage="display_only"),
    _field("safety_accident_count", "human_capital", "employee_health_safety", HIGH_ENVIRONMENTAL_IMPACT_INDUSTRIES, evidence_priority="high"),
    _field("occupational_health_safety_investment", "human_capital", "employee_health_safety", HIGH_ENVIRONMENTAL_IMPACT_INDUSTRIES),
    _field("safety_emergency_drill_count", "human_capital", "employee_health_safety", HIGH_ENVIRONMENTAL_IMPACT_INDUSTRIES),
    _field("lost_work_days_due_to_injury", "human_capital", "employee_health_safety", HIGH_ENVIRONMENTAL_IMPACT_INDUSTRIES, evidence_priority="high"),
    _field("r_and_d_personnel_count", "social_contribution", "technology_innovation", KNOWLEDGE_AND_TECH_INDUSTRIES),
    _field("r_and_d_expense", "social_contribution", "technology_innovation", KNOWLEDGE_AND_TECH_INDUSTRIES),
    _field("public_welfare_investment", "social_contribution", "community_investment", ALL_INDUSTRIES, score_usage="display_only"),
    _field("board_size", "governance_structure", "board_structure", ALL_INDUSTRIES),
    _field("independent_directors", "governance_structure", "board_structure", ALL_INDUSTRIES),
    _field("independent_director_ratio", "governance_structure", "board_structure", ALL_INDUSTRIES, evidence_priority="high"),
    _field("female_directors", "governance_structure", "board_structure", ALL_INDUSTRIES),
    _field("board_meetings", "governance_structure", "board_structure", ALL_INDUSTRIES, score_usage="display_only"),
    _field("shareholder_meetings", "shareholder_rights", "shareholder_rights_protection", ALL_INDUSTRIES, score_usage="display_only"),
    _field("anti_corruption_training_sessions", "business_ethics", "anti_corruption_bribery", ALL_INDUSTRIES),
    _field("anti_corruption_training_participants", "business_ethics", "anti_corruption_bribery", ALL_INDUSTRIES),
    _field("confirmed_corruption_cases", "business_ethics", "anti_corruption_bribery", ALL_INDUSTRIES, evidence_priority="high"),
    _field("esg_strategy_targets", "climate_change", "carbon_reduction_pathway", ALL_INDUSTRIES),
    _field("climate_risk_management", "climate_change", "climate_change_response", ALL_INDUSTRIES, evidence_priority="high"),
    _field("environmental_management_system", "environmental_management", "sustainable_certification", HIGH_ENVIRONMENTAL_IMPACT_INDUSTRIES),
    _field("energy_saving_measures", "climate_change", "carbon_reduction_pathway", HIGH_ENVIRONMENTAL_IMPACT_INDUSTRIES),
    _field("water_management_measures", "resource_utilization", "water_resource_consumption", HIGH_ENVIRONMENTAL_IMPACT_INDUSTRIES),
    _field("waste_management_measures", "environmental_pollution", "hazardous_waste", HIGH_ENVIRONMENTAL_IMPACT_INDUSTRIES),
    _field("employee_rights_policy", "human_capital", "employee_relations", ALL_INDUSTRIES),
    _field("occupational_health_safety_system", "human_capital", "employee_health_safety", HIGH_ENVIRONMENTAL_IMPACT_INDUSTRIES),
    _field("employee_training_development", "human_capital", "employee_incentive_development", ALL_INDUSTRIES),
    _field("diversity_equal_opportunity", "human_capital", "employee_relations", ALL_INDUSTRIES),
    _field("supplier_esg_assessment", "supply_chain", "supplier_risk_management", ALL_INDUSTRIES),
    _field("data_security_privacy", "data_security_privacy", "data_security_privacy", CONSUMER_AND_SERVICE_INDUSTRIES, evidence_priority="high"),
    _field("board_esg_oversight", "governance_structure", "esg_governance", ALL_INDUSTRIES, evidence_priority="high"),
    _field("esg_committee", "governance_structure", "esg_governance", ALL_INDUSTRIES),
    _field("anti_corruption_policy", "business_ethics", "anti_corruption_bribery", ALL_INDUSTRIES, evidence_priority="high"),
    _field("whistleblowing_mechanism", "business_ethics", "business_ethics", ALL_INDUSTRIES),
    _field("business_ethics_training", "business_ethics", "business_ethics", ALL_INDUSTRIES),
    _field("investor_communication", "disclosure_quality", "disclosure_credibility", ALL_INDUSTRIES),
]

FIELD_FRAMEWORK_MAP = {item["field_key"]: item for item in FIELD_FRAMEWORK_MAPPINGS}


def _indicator_index() -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for pillar in HUAZHENG_PUBLIC_FRAMEWORK:
        for theme in pillar["themes"]:
            for indicator in theme["key_indicators"]:
                index[indicator["indicator_key"]] = {
                    "pillar": pillar["pillar"],
                    "pillar_name_cn": pillar["pillar_name_cn"],
                    "theme_key": theme["theme_key"],
                    "theme_name_cn": theme["theme_name_cn"],
                    **indicator,
                }
    return index


KEY_INDICATOR_INDEX = _indicator_index()


def get_mapping_for_field(field_key: str) -> Dict[str, Any] | None:
    mapping = FIELD_FRAMEWORK_MAP.get(field_key)
    if mapping is None:
        return None

    indicator = KEY_INDICATOR_INDEX[mapping["key_indicator"]]
    return {
        **mapping,
        "pillar": indicator["pillar"],
        "pillar_name_cn": indicator["pillar_name_cn"],
        "theme_name_cn": indicator["theme_name_cn"],
        "indicator_name_cn": indicator["indicator_name_cn"],
    }


def get_applicable_field_keys(industry: str) -> List[str]:
    result = []
    for item in FIELD_FRAMEWORK_MAPPINGS:
        industries = item["applicable_industries"]
        if "all" in industries or industry in industries:
            result.append(item["field_key"])
    return result


def framework_summary() -> Dict[str, int]:
    pillars = len(HUAZHENG_PUBLIC_FRAMEWORK)
    themes = sum(len(pillar["themes"]) for pillar in HUAZHENG_PUBLIC_FRAMEWORK)
    indicators = sum(
        len(theme["key_indicators"])
        for pillar in HUAZHENG_PUBLIC_FRAMEWORK
        for theme in pillar["themes"]
    )
    return {
        "pillars": pillars,
        "themes": themes,
        "key_indicators": indicators,
        "mapped_project_fields": len(FIELD_FRAMEWORK_MAPPINGS),
    }


__all__ = [
    "FIELD_FRAMEWORK_MAP",
    "FIELD_FRAMEWORK_MAPPINGS",
    "HUAZHENG_PUBLIC_FRAMEWORK",
    "KEY_INDICATOR_INDEX",
    "RATING_BANDS",
    "SCHEMA_VERSION",
    "framework_summary",
    "get_applicable_field_keys",
    "get_mapping_for_field",
]
