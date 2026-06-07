"""
Draft industry schema for banking / securities / broader finance reports.
"""

from .shared import q_field


FINANCE_SCHEMA = [
    q_field(
        "green_credit_balance",
        "绿色信贷余额",
        "E",
        "number",
        "money",
        aliases=["绿色信贷余额", "绿色贷款余额", "绿色融资余额"],
        required_any=["绿色", "余额"],
        forbidden_any=["增速", "占比", "客户数"],
        unit_examples=["亿元", "万元"],
    ),
    q_field(
        "inclusive_finance_balance",
        "普惠金融余额",
        "S",
        "number",
        "money",
        aliases=["普惠金融余额", "普惠贷款余额", "普惠信贷余额"],
        required_any=["普惠", "余额"],
        forbidden_any=["客户数", "户数", "占比"],
        unit_examples=["亿元", "万元"],
    ),
    q_field(
        "micro_small_loan_balance",
        "小微贷款余额",
        "S",
        "number",
        "money",
        aliases=["小微贷款余额", "小微企业贷款余额", "普惠型小微贷款余额"],
        required_any=["小微", "贷款", "余额"],
        forbidden_any=["户数", "客户数", "增速"],
        unit_examples=["亿元", "万元"],
    ),
    q_field(
        "customer_complaint_count",
        "客户投诉数量",
        "S",
        "number",
        "count",
        aliases=["客户投诉数量", "客户投诉件数", "客户投诉次数", "消费者投诉数量"],
        required_any=["客户", "投诉"],
        forbidden_any=["满意度", "解决率", "培训"],
        unit_examples=["件", "次"],
    ),
    q_field(
        "customer_satisfaction_rate",
        "客户满意度",
        "S",
        "percentage",
        "percentage",
        aliases=["客户满意度", "客户满意率", "消费者满意度"],
        required_any=["客户", "满意"],
        forbidden_any=["投诉", "处理时长"],
        unit_examples=["%"],
    ),
    q_field(
        "data_security_incidents",
        "数据安全事件数",
        "G",
        "number",
        "count",
        aliases=["数据安全事件数", "信息安全事件数", "网络安全事件数", "客户信息安全事件数"],
        required_any=["安全", "事件"],
        forbidden_any=["培训", "演练", "投入"],
        unit_examples=["起", "次", "件"],
    ),
    q_field(
        "anti_money_laundering_training_count",
        "反洗钱培训次数",
        "G",
        "number",
        "count",
        aliases=["反洗钱培训次数", "反洗钱培训场次", "反洗钱专题培训次数"],
        required_any=["反洗钱", "培训"],
        forbidden_any=["人次", "人数", "小时", "覆盖率"],
        unit_examples=["次", "场"],
    ),
    q_field(
        "rural_revitalization_investment",
        "乡村振兴相关投入金额",
        "S",
        "number",
        "money",
        aliases=["乡村振兴投入金额", "乡村振兴相关投入", "服务乡村振兴投入金额", "涉农支持投入金额"],
        required_any=["乡村振兴", "投入"],
        forbidden_any=["人数", "项目数", "培训"],
        unit_examples=["万元", "亿元"],
    ),
]


FINANCE_FIELD_KEYS = [item["field_key"] for item in FINANCE_SCHEMA]


__all__ = ["FINANCE_SCHEMA", "FINANCE_FIELD_KEYS"]
