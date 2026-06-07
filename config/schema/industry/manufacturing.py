"""
Draft industry schema for manufacturing / heavy industry reports.
"""

from .shared import q_field


MANUFACTURING_SCHEMA = [
    q_field(
        "comprehensive_energy_consumption",
        "综合能耗",
        "E",
        "number",
        "energy",
        aliases=["综合能耗", "综合能源消耗量", "综合能源消费量"],
        required_any=["综合", "能耗"],
        forbidden_any=["强度", "单耗", "单位产量", "单位产值"],
        unit_examples=["吨标准煤", "吨标煤"],
    ),
    q_field(
        "energy_consumption_per_unit_output",
        "单位产量综合能耗",
        "E",
        "number",
        "intensity",
        aliases=["单位产量综合能耗", "单位产品综合能耗", "单位产值综合能耗", "综合能耗单耗"],
        required_any=["单位", "能耗"],
        forbidden_any=["总量", "总能耗", "综合能源消耗量"],
        unit_examples=["千克标准煤/吨", "吨标煤/万元"],
    ),
    q_field(
        "water_consumption_per_unit_output",
        "单位产量耗水量",
        "E",
        "number",
        "intensity",
        aliases=["单位产量耗水量", "单位产品耗水量", "单位产值耗水量", "单位产品取水量"],
        required_any=["单位", "水"],
        forbidden_any=["总耗水量", "用水总量", "新鲜水"],
        unit_examples=["吨/吨", "立方米/万元"],
    ),
    q_field(
        "production_safety_accident_count",
        "生产安全事故次数",
        "S",
        "number",
        "count",
        aliases=["生产安全事故次数", "安全生产事故次数", "生产事故次数", "工伤事故次数"],
        required_any=["事故"],
        forbidden_any=["演练", "培训", "投入"],
        unit_examples=["次", "起"],
    ),
    q_field(
        "occupational_disease_case_count",
        "职业病病例数",
        "S",
        "number",
        "count",
        aliases=["职业病病例数", "职业病发生人数", "新增职业病病例数"],
        required_any=["职业病"],
        forbidden_any=["体检", "培训", "覆盖率"],
        unit_examples=["例", "人"],
    ),
    q_field(
        "hazard_source_count",
        "重大危险源数量",
        "S",
        "number",
        "count",
        aliases=["重大危险源数量", "重大危险源个数", "危险源数量"],
        required_any=["危险源"],
        forbidden_any=["辨识培训", "应急演练"],
        unit_examples=["个", "处"],
    ),
    q_field(
        "environmental_penalty_count",
        "环保处罚次数",
        "G",
        "number",
        "count",
        aliases=["环保处罚次数", "环境处罚次数", "环境违法处罚次数", "生态环境处罚次数"],
        required_any=["处罚"],
        forbidden_any=["培训", "投入", "整改率"],
        unit_examples=["次", "起"],
    ),
    q_field(
        "pollution_control_investment",
        "污染治理投入金额",
        "E",
        "number",
        "money",
        aliases=["污染治理投入金额", "环保治理投入金额", "污染防治投入金额", "三废治理投入金额"],
        required_any=["治理", "投入"],
        forbidden_any=["处罚", "培训", "覆盖率"],
        unit_examples=["万元", "亿元"],
    ),
]


MANUFACTURING_FIELD_KEYS = [item["field_key"] for item in MANUFACTURING_SCHEMA]


__all__ = ["MANUFACTURING_SCHEMA", "MANUFACTURING_FIELD_KEYS"]
