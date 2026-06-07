"""
Draft industry schema for pharma / healthcare reports.

This layer is intentionally conservative:
- keep cross-industry metrics in core
- add only sector-specific appendix-style indicators here
- refine aliases after reviewing more real report samples
"""

from .shared import q_field


PHARMA_SCHEMA = [
    q_field(
        "drug_quality_incidents",
        "药品质量事件数",
        "S",
        "number",
        "count",
        aliases=["药品质量事件数", "产品质量事件数", "质量事故次数", "药品质量事故次数"],
        required_any=["质量", "事件"],
        forbidden_any=["培训", "覆盖率", "满意度"],
        unit_examples=["次", "件"],
    ),
    q_field(
        "product_recall_count",
        "产品或药品召回次数",
        "S",
        "number",
        "count",
        aliases=["产品召回次数", "药品召回次数", "产品或药品召回次数", "召回事件数"],
        required_any=["召回"],
        forbidden_any=["演练", "培训"],
        unit_examples=["次", "件"],
    ),
    q_field(
        "r_and_d_personnel_count",
        "研发人员数量",
        "S",
        "number",
        "person_count",
        aliases=["研发人员数量", "研发人员人数", "研发人员总数", "研发团队人数"],
        required_any=["研发人员"],
        forbidden_any=["研发投入", "研发费用", "研发强度", "专利"],
        unit_examples=["人", "名"],
    ),
    q_field(
        "r_and_d_personnel_ratio",
        "研发人员占比",
        "S",
        "percentage",
        "percentage",
        aliases=["研发人员占比", "研发人员比例", "研发团队占比"],
        required_any=["研发人员", "占比"],
        forbidden_any=["研发投入", "研发费用", "专利"],
        unit_examples=["%"],
    ),
    q_field(
        "clinical_trial_count",
        "临床试验项目数",
        "S",
        "number",
        "count",
        aliases=["临床试验项目数", "临床研究项目数", "在研临床项目数", "临床项目数量"],
        required_any=["临床"],
        forbidden_any=["培训", "覆盖率", "受试者"],
        unit_examples=["项", "个"],
    ),
    q_field(
        "pharmacovigilance_training_count",
        "药物警戒或药品安全培训次数",
        "S",
        "number",
        "count",
        aliases=["药物警戒培训次数", "药品安全培训次数", "药品质量培训次数", "药物安全培训场次"],
        required_any=["培训"],
        forbidden_any=["人次", "人数", "小时", "时长", "覆盖率"],
        unit_examples=["次", "场"],
    ),
    q_field(
        "supplier_quality_audit_count",
        "供应商质量审计次数",
        "S",
        "number",
        "count",
        aliases=["供应商质量审计次数", "供应商质量审核次数", "供应商质量稽核次数", "供应商审计次数"],
        required_any=["供应商", "质量", "审计"],
        forbidden_any=["金额", "覆盖率", "评分"],
        unit_examples=["次", "家"],
    ),
]


PHARMA_FIELD_KEYS = [item["field_key"] for item in PHARMA_SCHEMA]


__all__ = ["PHARMA_SCHEMA", "PHARMA_FIELD_KEYS"]
