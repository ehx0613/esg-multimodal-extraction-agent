"""Candidate Route B fields. These do not count toward the frozen 60-field core schema."""

from .qualitative_data import t_field


ROUTE_B_CANDIDATE_SCHEMA = [
    t_field("materiality_assessment", "重大议题识别与双重重要性分析", "G", ["重大议题", "双重重要性", "重要性分析"]),
    t_field("stakeholder_engagement", "利益相关方沟通机制", "G", ["利益相关方沟通", "利益相关方参与"]),
    t_field("esg_risk_opportunity_process", "ESG风险与机遇管理流程", "G", ["ESG风险与机遇", "可持续发展风险与机遇"]),
    t_field("esg_target_progress", "ESG目标完成进展", "G", ["ESG目标进展", "可持续发展目标完成情况"]),
    t_field("reporting_boundary", "报告范围与指标统计边界", "G", ["报告范围", "统计边界", "报告边界"]),
    t_field("esg_data_quality_control", "ESG数据质量控制", "G", ["ESG数据质量", "数据质量控制"]),
    t_field("external_assurance", "外部鉴证", "G", ["外部鉴证", "独立鉴证", "第三方鉴证"]),
    t_field("board_report_approval", "董事会审议可持续发展报告", "G", ["董事会审议可持续发展报告", "董事会审议ESG报告"]),
    t_field("climate_transition_plan", "气候转型计划", "E", ["气候转型计划", "低碳转型计划"]),
    t_field("product_quality_customer_rights", "产品质量与客户权益", "S", ["产品质量", "客户权益", "消费者权益"]),
    t_field("circular_economy", "循环经济", "E", ["循环经济", "资源循环利用"]),
    t_field("biodiversity_protection", "生物多样性保护", "E", ["生物多样性", "生态保护"]),
    t_field("rural_revitalization", "乡村振兴", "S", ["乡村振兴"]),
    t_field("technology_ethics", "科技伦理", "S", ["科技伦理", "人工智能伦理"]),
    t_field("compliance_internal_control", "合规与内部控制", "G", ["合规管理", "内部控制"]),
]

ROUTE_B_CANDIDATE_FIELD_KEYS = [item["field_key"] for item in ROUTE_B_CANDIDATE_SCHEMA]


__all__ = ["ROUTE_B_CANDIDATE_FIELD_KEYS", "ROUTE_B_CANDIDATE_SCHEMA"]
