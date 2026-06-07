from typing import Any, Dict, List

from .shared import filter_by_category


def t_field(
    field_key: str,
    name_cn: str,
    category: str,
    aliases: List[str],
    required_any: List[str] | None = None,
    forbidden_any: List[str] | None = None,
    preferred_source: str = "main_text_rag",
) -> Dict[str, Any]:
    return {
        "field_key": field_key,
        "name_cn": name_cn,
        "category": category,
        "indicator_type": "qualitative",
        "value_type": "boolean_or_text",
        "preferred_source": preferred_source,
        "unit_required": False,
        "year_required": False,
        "unit_type": "text",
        "unit_examples": [],
        "aliases": aliases,
        "required_any": required_any if required_any is not None else aliases,
        "forbidden_any": forbidden_any or ["指标索引", "内容索引", "GRI", "目录"],
    }


QUALITATIVE_SCHEMA_DATA = [
    t_field(
        "esg_strategy_targets",
        "ESG战略目标",
        "E",
        aliases=["ESG战略目标", "可持续发展目标", "ESG目标", "可持续发展战略"],
        required_any=["ESG", "目标", "战略"],
    ),
    t_field(
        "climate_risk_management",
        "气候风险识别与管理",
        "E",
        aliases=["气候风险管理", "气候变化风险", "气候相关风险", "气候风险识别"],
        required_any=["气候", "风险"],
    ),
    t_field(
        "environmental_management_system",
        "环境管理体系",
        "E",
        aliases=["环境管理体系", "环境管理制度", "ISO 14001", "环境保护管理"],
        required_any=["环境", "管理"],
    ),
    t_field(
        "energy_saving_measures",
        "节能减排措施",
        "E",
        aliases=["节能减排措施", "节能措施", "减排措施", "降碳措施", "节能降耗"],
        required_any=["节能", "减排", "降碳"],
    ),
    t_field(
        "water_management_measures",
        "水资源管理措施",
        "E",
        aliases=["水资源管理", "节水措施", "用水管理", "水资源保护"],
        required_any=["水", "节水", "用水"],
    ),
    t_field(
        "waste_management_measures",
        "废弃物管理措施",
        "E",
        aliases=["废弃物管理", "固体废弃物管理", "危险废弃物管理", "废物处置"],
        required_any=["废弃物", "废物", "危废"],
    ),
    t_field(
        "employee_rights_policy",
        "员工权益保障政策",
        "S",
        aliases=["员工权益保障", "员工权益保护", "劳动权益", "雇员权益", "员工关怀"],
        required_any=["员工", "权益"],
    ),
    t_field(
        "occupational_health_safety_system",
        "职业健康安全管理体系",
        "S",
        aliases=["职业健康安全管理体系", "职业健康安全", "安全生产管理体系", "EHS管理"],
        required_any=["职业健康", "安全"],
    ),
    t_field(
        "employee_training_development",
        "员工培训与发展机制",
        "S",
        aliases=["员工培训与发展", "人才培养机制", "员工发展", "培训体系", "职业发展"],
        required_any=["员工", "培训", "发展"],
    ),
    t_field(
        "diversity_equal_opportunity",
        "多元化与平等雇佣政策",
        "S",
        aliases=["多元化与平等", "平等雇佣", "多元化雇佣", "反歧视", "机会平等"],
        required_any=["多元", "平等", "雇佣"],
    ),
    t_field(
        "supplier_esg_assessment",
        "供应商ESG管理机制",
        "S",
        aliases=["供应商ESG管理", "供应商社会责任", "供应商可持续发展管理", "供应商评估", "责任采购"],
        required_any=["供应商", "ESG", "可持续", "社会责任"],
    ),
    t_field(
        "data_security_privacy",
        "数据安全与隐私保护机制",
        "S",
        aliases=["数据安全", "隐私保护", "信息安全", "客户隐私", "个人信息保护"],
        required_any=["数据安全", "隐私", "信息安全", "个人信息"],
    ),
    t_field(
        "board_esg_oversight",
        "董事会ESG监督机制",
        "G",
        aliases=["董事会ESG监督", "董事会可持续发展监督", "董事会监督ESG", "董事会负责ESG"],
        required_any=["董事会", "ESG"],
    ),
    t_field(
        "esg_committee",
        "ESG治理架构或委员会",
        "G",
        aliases=["ESG委员会", "可持续发展委员会", "ESG工作小组", "ESG治理架构"],
        required_any=["ESG", "委员会", "工作小组", "治理架构"],
    ),
    t_field(
        "anti_corruption_policy",
        "反腐败政策",
        "G",
        aliases=["反腐败政策", "反贪污政策", "反舞弊制度", "廉洁从业制度", "商业道德政策"],
        required_any=["反腐败", "反贪污", "反舞弊", "廉洁"],
    ),
    t_field(
        "whistleblowing_mechanism",
        "举报机制与举报人保护",
        "G",
        aliases=["举报机制", "举报人保护", "投诉举报渠道", " whistleblowing", "举报渠道"],
        required_any=["举报", "投诉", "保护"],
    ),
    t_field(
        "business_ethics_training",
        "商业道德培训机制",
        "G",
        aliases=["商业道德培训", "反腐败培训", "廉洁培训", "合规培训", "反舞弊培训"],
        required_any=["培训", "廉洁", "反腐败", "商业道德"],
    ),
    t_field(
        "investor_communication",
        "信息披露与投资者沟通机制",
        "G",
        aliases=["信息披露", "投资者沟通", "投资者关系", "股东沟通", "业绩说明会"],
        required_any=["信息披露", "投资者", "沟通"],
    ),
]


S_QUALITATIVE_SCHEMA_DATA = filter_by_category(QUALITATIVE_SCHEMA_DATA, "S")
G_QUALITATIVE_SCHEMA_DATA = filter_by_category(QUALITATIVE_SCHEMA_DATA, "G")


__all__ = [
    "QUALITATIVE_SCHEMA_DATA",
    "S_QUALITATIVE_SCHEMA_DATA",
    "G_QUALITATIVE_SCHEMA_DATA",
]
