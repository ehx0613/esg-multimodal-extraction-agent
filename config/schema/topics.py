"""Disclosure-topic layer above the frozen 60-field core schema."""

from typing import Any, Dict, List


DISCLOSURE_TOPICS: List[Dict[str, Any]] = [
    {"topic_key": "materiality", "name_cn": "重大议题与重要性", "field_keys": [], "candidate_field_keys": ["materiality_assessment", "stakeholder_engagement"]},
    {"topic_key": "governance", "name_cn": "可持续发展治理", "field_keys": ["board_esg_oversight", "esg_committee"], "candidate_field_keys": ["board_report_approval"]},
    {"topic_key": "risk_opportunity", "name_cn": "风险与机遇", "field_keys": ["climate_risk_management"], "candidate_field_keys": ["esg_risk_opportunity_process"]},
    {"topic_key": "targets_progress", "name_cn": "目标与进展", "field_keys": ["esg_strategy_targets"], "candidate_field_keys": ["esg_target_progress", "climate_transition_plan"]},
    {"topic_key": "reporting_quality", "name_cn": "报告边界与数据质量", "field_keys": [], "candidate_field_keys": ["reporting_boundary", "esg_data_quality_control", "external_assurance"]},
    {"topic_key": "environment", "name_cn": "环境与气候绩效", "field_keys": [], "candidate_field_keys": ["circular_economy", "biodiversity_protection"]},
    {"topic_key": "social_responsibility", "name_cn": "产品、客户与社会责任", "field_keys": ["data_security_privacy"], "candidate_field_keys": ["product_quality_customer_rights", "rural_revitalization", "technology_ethics"]},
    {"topic_key": "compliance", "name_cn": "合规与内部控制", "field_keys": ["anti_corruption_policy", "whistleblowing_mechanism"], "candidate_field_keys": ["compliance_internal_control"]},
]

TOPIC_INDEX = {topic["topic_key"]: topic for topic in DISCLOSURE_TOPICS}


__all__ = ["DISCLOSURE_TOPICS", "TOPIC_INDEX"]
