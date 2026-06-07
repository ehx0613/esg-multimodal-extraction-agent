# utils/schema_matcher.py
"""
Schema Matcher

匹配顺序：
1. heuristic_match：通用高精度规则
2. alias_match：Core Schema 别名匹配
3. qwen-plus 文本模型匹配
4. schema_match_validator 统一校验
5. 未通过则进入 unknown_metrics
"""
import re
from difflib import SequenceMatcher

from typing import Dict, Any, Tuple, Optional

from config.schema import ESG_SCHEMA, ROUTE_A_SCHEMA
from utils.schema_match_validator import validate_schema_match

try:
    from config.settings import (
        LLM_MATCHER_ENABLED,
        SCHEMA_JUDGE_MIN_CONFIDENCE,
        SCHEMA_JUDGE_SOFT_ACCEPT_CONFIDENCE,
    )
except Exception:
    LLM_MATCHER_ENABLED = False
    SCHEMA_JUDGE_MIN_CONFIDENCE = 0.78
    SCHEMA_JUDGE_SOFT_ACCEPT_CONFIDENCE = 0.88

try:
    from utils.llm_schema_matcher import llm_match_row_to_schema
except Exception:
    llm_match_row_to_schema = None

try:
    from rapidfuzz import fuzz
except Exception:
    fuzz = None


import unicodedata


BUSINESS_PERFORMANCE_KEYWORDS = [
    "资产总额",
    "净资产",
    "营业收入",
    "利润总额",
    "净利润",
    "归母净利润",
    "纳税总额",
    "资产负债率",
    "基本每股收益",
    "每股收益",
    "政府补贴",
    "现金分红",
    "股东分红",
    "净资产收益率",
]

DIMENSION_ONLY_METRICS = {
    "按性别",
    "按年龄",
    "期末在职员工结构",
    "期末在职员工结构(按教育程度)",
    "期末在职员工结构(按专业构成)",
}

EDUCATION_DIMENSION_METRICS = {
    "博士",
    "硕士",
    "本科",
    "大专",
    "专科",
    "高中及以下",
    "其他学历",
}

TARGETED_ALIAS_OVERRIDES = {
    "无害废弃物产生总量": "non_hazardous_waste",
    "无害废弃物总量": "non_hazardous_waste",
    "非危险废弃物产生总量": "non_hazardous_waste",
    "一般废弃物产生总量": "non_hazardous_waste",
    "环保总投资": "environmental_investment",
    "环保总投入": "environmental_investment",
    "公司研发总投入": "r_and_d_expense",
}

ALIAS_FUZZY_THRESHOLD = 0.85
ALIAS_FUZZY_MIN_LEN = 4


PUNCTUATION_PATTERN = re.compile(r"[()（）【】\[\]{}《》<>:：,，;；、/\\|·.\-—_]")

def norm(value: Any) -> str:
    if value is None:
        return ""

    text = unicodedata.normalize("NFKC", str(value))

    return (
        text.lower()
        .replace(" ", "")
        .replace("\n", "")
        .replace("\t", "")
        .replace("（", "(")
        .replace("）", ")")
        .replace("：", ":")
        .replace("，", ",")
    )


def norm_metric_name(value: Any) -> str:
    """Normalize metric labels for exact policy checks while dropping unit suffixes."""
    text = norm(value)
    text = re.sub(r"\([^)]*\)", "", text)
    return text


def normalize_alias_text(value: Any) -> str:
    """
    Canonical form for schema alias matching.
    It removes parenthetical units/notes and punctuation before exact/fuzzy matching.
    """
    text = norm(value)
    text = re.sub(r"\([^)]*\)", "", text)
    text = PUNCTUATION_PATTERN.sub("", text)
    return text


DIMENSION_ONLY_METRIC_KEYS = {norm_metric_name(item) for item in DIMENSION_ONLY_METRICS}
EDUCATION_DIMENSION_METRIC_KEYS = {norm_metric_name(item) for item in EDUCATION_DIMENSION_METRICS}


def contains_any(text: str, words) -> bool:
    text = norm(text)
    return any(norm(w) in text for w in words if norm(w))


OCR_TYPO_MAP = {
    "水电总量": "用水总量",
    "水电量": "用水量",
    "水总量": "用水总量",
}


TOTAL_FIELD_KEYS = {
    "electricity_consumption",
    "water_consumption",
    "energy_consumption_total",
    "total_ghg_emissions",
    "wastewater_discharge",
    "non_hazardous_waste",
    "hazardous_waste",
}


INTENSITY_MARKERS = [
    "人均",
    "强度",
    "密度",
    "每人",
    "/人",
    "吨/人",
    "度/人",
    "kwh/人",
    "mwh/人",
    "/万元",
    "每万元",
    "单位营收",
    "单位收入",
    "浜哄潎",
    "寮哄害",
    "瀵嗗害",
]


def apply_ocr_corrections(value: Any) -> str:
    text = norm(value)
    for wrong, right in OCR_TYPO_MAP.items():
        text = text.replace(norm(wrong), norm(right))
    return text


def row_text(row: Dict[str, Any]) -> str:
    return (
        apply_ocr_corrections(row.get("metric_name") or row.get("row_label"))
        + apply_ocr_corrections(row.get("topic") or row.get("topic_label"))
        + apply_ocr_corrections(row.get("table_title"))
        + apply_ocr_corrections(row.get("evidence_text"))
    )


def row_alias_text(row: Dict[str, Any]) -> str:
    """Trusted alias context. Broad table titles must not establish a field."""
    return (
        normalize_alias_text(row.get("metric_name") or row.get("row_label"))
        + normalize_alias_text(row.get("topic") or row.get("topic_label"))
    )


def metric_alias_text(row: Dict[str, Any]) -> str:
    return normalize_alias_text(row.get("metric_name") or row.get("row_label"))


def row_context_text(row: Dict[str, Any]) -> str:
    return (
        apply_ocr_corrections(row.get("topic") or row.get("topic_label"))
        + apply_ocr_corrections(row.get("table_title"))
        + apply_ocr_corrections(row.get("evidence_text"))
    )


def result_no_match(reason: str, confidence: float = 0.0) -> Dict[str, Any]:
    return {
        "matched": False,
        "field_key": None,
        "confidence": confidence,
        "reason": reason,
    }


def fuzzy_ratio(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    if fuzz is not None:
        return fuzz.ratio(left, right) / 100
    return SequenceMatcher(None, left, right).ratio()

def is_index_row(table_title_or_row, row: Dict[str, Any] = None) -> bool:
    """
    判断一行是否来自指标索引 / 内容索引 / GRI 索引表。

    兼容两种调用方式：
    1. is_index_row(row)
    2. is_index_row(table_title, row)

    这类行通常只是：
    - E.1 资源消耗 -> 报告页码 P42
    - GRI 302-1 -> 对应章节
    - 指标索引表
    不是真正的绩效数据，不应该进入 Schema 匹配或 unknown_metrics。
    """

    if row is None:
        row = table_title_or_row
        table_title = row.get("table_title") if isinstance(row, dict) else ""
    else:
        table_title = table_title_or_row

    if not isinstance(row, dict):
        return False

    table_title = norm(table_title)
    metric_name = norm(row.get("metric_name") or row.get("row_label"))
    evidence_text = norm(row.get("evidence_text"))
    unit = norm(row.get("unit"))

    values = row.get("values", {})

    value_keys = ""
    value_values = ""

    if isinstance(values, dict):
        value_keys = norm(" ".join(str(k) for k in values.keys()))
        value_values = norm(" ".join(str(v) for v in values.values()))

    combined = (
        table_title
        + metric_name
        + evidence_text
        + unit
        + value_keys
        + value_values
    )

    index_keywords = [
        "指标索引",
        "内容索引",
        "披露索引",
        "gri索引",
        "gri内容索引",
        "报告页码",
        "对应章节",
        "披露位置",
    ]

    if contains_any(combined, index_keywords):
        return True

    # 例如：E.1 资源消耗 / S.2 员工权益 / G.1 公司治理
    if re.match(r"^[esg]\.\d+", metric_name):
        return True

    # 例如：GRI 302-1, GRI305-1
    if re.search(r"gri\d{3}-?\d*", combined):
        return True

    # 例如：P42、P45、P36-P38
    if re.search(r"p\d+", combined):
        return True

    return False

def is_business_performance(text: str) -> bool:
    return contains_any(text, BUSINESS_PERFORMANCE_KEYWORDS)


def values_contain_key(row: Dict[str, Any], words) -> bool:
    values = row.get("values", {})
    if not isinstance(values, dict):
        return False
    return contains_any(" ".join(str(key) for key in values.keys()), words)


def pick_value_by_key(row: Dict[str, Any], words):
    values = row.get("values", {})
    if not isinstance(values, dict):
        return None
    for key, value in values.items():
        if contains_any(key, words):
            return value
    return None


def virtual_metric_match(row: Dict[str, Any]) -> Optional[Tuple]:
    table_title = row.get("table_title", "")
    evidence = row.get("evidence_text", "")
    values = row.get("values", {})

    if contains_any(table_title, ["废水排放情况", "废水排放", "污水排放"]):
        value = pick_value_by_key(row, ["排放总量", "排放量"])
        if value is not None:
            validation_row = dict(
                row,
                metric_name="废水排放量",
                evidence_text=f"废水排放量 {evidence}",
                values={"2024": value},
            )
            return ("wastewater_discharge", 0.9, "virtual_metric:table_title_wastewater_discharge", validation_row)

    if contains_any(table_title, ["废弃物产生", "废弃物情况", "废物产生"]):
        field_key = None
        if contains_any(evidence, ["有害", "危险", "危废"]):
            field_key = "hazardous_waste"
            metric_name = "危险废弃物产生量"
        elif contains_any(evidence, ["无害", "一般", "非危险"]):
            field_key = "non_hazardous_waste"
            metric_name = "一般废弃物产生量"
        if field_key:
            value = pick_value_by_key(row, ["产生总量", "产生量", "总量"])
            if value is not None:
                validation_row = dict(row, metric_name=metric_name, evidence_text=f"{metric_name} {evidence}", values={"2024": value})
                return (field_key, 0.88, "virtual_metric:table_title_waste_context", validation_row)

    return None


def policy_precheck(row: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[Tuple]]:
    """
    High-precision handling before generic matching:
    - filter finance noise
    - skip structural dimension rows
    - convert short dimension labels only when employee context is clear
    - keep not-yet-modeled target fields out of existing Core fields
    """
    metric_name = norm_metric_name(row.get("metric_name") or row.get("row_label"))
    context = row_context_text(row)
    text = metric_name + context

    if not metric_name:
        return None, None

    if is_business_performance(text):
        return result_no_match("business_performance_not_core_esg"), None

    if contains_any(text, ["帮扶困难员工", "困难员工帮扶", "慰问困难员工"]):
        return result_no_match("assisted_employee_subgroup_not_total_employees"), None

    virtual_match = virtual_metric_match(row)
    if virtual_match is not None:
        return None, virtual_match

    if metric_name in DIMENSION_ONLY_METRIC_KEYS:
        return result_no_match("dimension_header_skip_match"), None

    if metric_name in EDUCATION_DIMENSION_METRIC_KEYS:
        return result_no_match("education_dimension_not_core_metric"), None

    for alias, field_key in TARGETED_ALIAS_OVERRIDES.items():
        if metric_name == norm_metric_name(alias):
            return None, (field_key, 0.96, f"manual_alias_override:{alias}")

    employee_structure_context = contains_any(
        context,
        ["员工结构", "员工构成", "在职员工结构", "员工人数", "员工总数", "雇员", "按性别"],
    ) and not contains_any(
        context,
        ["新进员工", "新入职员工", "离职员工", "流失员工", "董事", "管理层"],
    )

    if metric_name in {"女性", "女", "女性比例", "女员工比例", "女性员工比例"} and employee_structure_context:
        if contains_any(row.get("unit"), ["%"]):
            validation_row = dict(row, metric_name="女性员工比例")
            return None, ("female_employee_ratio", 0.96, "context_dimension:员工构成女性比例->female_employee_ratio", validation_row)
        validation_row = dict(row, metric_name="女性员工人数")
        return None, ("female_employees", 0.9, "context_dimension:女性->female_employees", validation_row)

    if metric_name in {"男性", "男"} and employee_structure_context:
        validation_row = dict(row, metric_name="男性员工人数")
        return None, ("male_employees", 0.9, "context_dimension:男性->male_employees", validation_row)

    return None, None


def is_emission_factor_or_method_row(text: str) -> bool:
    """
    过滤碳排放因子/核算方法/指南类表格。

    这类表格里的“汽油、柴油、天然气、水”等通常是排放因子或换算系数，
    不是企业当年实际消耗量，不能进入 Core ESG 标准指标。
    """
    return contains_any(
        text,
        [
            "排放因子",
            "排放系数",
            "换算系数",
            "核算方法",
            "核算标准",
            "报告指南",
            "生命周期",
            "因子来源",
            "北京绿交所",
            "国家发展改革委",
            "中国生命周期基础数据库",
        ],
    )


def heuristic_match(row: Dict[str, Any]) -> Tuple[Optional[str], float, str]:
    """
    只放非常稳定的跨行业规则。
    不在这里写某家公司特例。
    """
    text = row_text(row)
    metric_name = apply_ocr_corrections(row.get("metric_name") or row.get("row_label"))
    unit = norm(row.get("unit"))

    if not text:
        return None, 0.0, "empty_row_text"

    if is_business_performance(text):
        return None, 0.0, "business_performance_not_core_esg"

    if contains_any(text, ["用水总量", "水电总量", "水总量", "用水量", "取水量", "耗水量", "年度用水量"]):
        if contains_any(unit, ["立方米", "m3", "m³", "吨"]) and not contains_any(text, ["废水", "循环", "回用", "节水", "强度", "人均"]):
            return "water_consumption", 0.92, "heuristic_water_ocr_correction"

    if contains_any(text, ["用电总量", "年度用电总量", "年度用电量", "年度耗电量", "耗电量", "电力消耗"]):
        if not contains_any(text, ["光伏", "新能源发电量", "清洁能源", "人均", "强度", "密度"]):
            return "electricity_consumption", 0.92, "heuristic_electricity_total_alias"

    if contains_any(text, ["体检及健康档案覆盖率", "健康体检覆盖率", "员工健康体检覆盖率"]):
        return "employee_medical_checkup_coverage", 0.9, "heuristic_employee_medical_checkup_coverage_alias"

    if contains_any(text, ["累计培训员工人次", "全年累计培训员工人次", "培训员工人次", "培训人次", "员工培训人次"]):
        if not contains_any(text, ["反腐", "反贪污", "反洗钱", "廉洁", "合规"]):
            return "trained_employees_count", 0.9, "heuristic_trained_employees_count"

    if is_emission_factor_or_method_row(text):
        return None, 0.0, "emission_factor_or_method_not_core_metric"

    if contains_any(text, ["指标索引", "内容索引", "报告页码", "gri"]):
        return None, 0.0, "index_table_not_metric"
    if contains_any(text, ["反腐败", "反贪污", "反商业贿赂", "廉洁培训"]):
        if contains_any(text, ["平均", "小时/人", "人均"]):
            return None, 0.0, "anti_corruption_average_duration_not_core"

        if contains_any(text, ["总时长", "培训时长", "培训小时", "培训时数"]):
            return "anti_corruption_training_hours", 0.94, "heuristic_anti_corruption_training_hours"

        if contains_any(text, ["培训次数", "培训场次", "次数", "场次"]):
            return "anti_corruption_training_sessions", 0.92, "heuristic_anti_corruption_training_sessions"

        if contains_any(text, ["员工人数", "参与人数", "培训人数", "人次", "董事及高级管理人员人数"]):
            if not contains_any(text, ["占比", "比例", "百分比", "%"]):
                return "anti_corruption_training_participants", 0.92, "heuristic_anti_corruption_training_participants"
    # E
    if contains_any(unit, ["tCO2e", "CO2e", "吨二氧化碳当量", "万吨二氧化碳当量", "二氧化碳当量"]) and contains_any(
        text,
        ["温室气体", "GHG", "碳排放", "二氧化碳", "排放量", "排放总量"],
    ) and not contains_any(text, ["范围一", "范围1", "scope1", "范围二", "范围2", "scope2", "范围三", "范围3", "scope3", "强度", "密度", "/"]):
        return "total_ghg_emissions", 0.94, "heuristic_total_ghg_unit_pivot"

    if contains_any(text, ["范围一", "范围1", "范围 1", "scope1", "scope 1", "直接温室气体"]):
        return "scope_1_emissions", 0.96, "heuristic_scope_1"

    if contains_any(text, ["范围二", "范围2", "范围 2", "scope2", "scope 2", "间接温室气体"]):
        return "scope_2_emissions", 0.96, "heuristic_scope_2"

    if contains_any(text, ["范围三", "范围3", "范围 3", "scope3", "scope 3"]):
        return "scope_3_emissions", 0.94, "heuristic_scope_3"

    if contains_any(text, ["温室气体排放总量", "温室气体总排放", "碳排放总量"]):
        return "total_ghg_emissions", 0.94, "heuristic_total_ghg"

    if contains_any(text, ["温室气体排放强度", "碳排放强度", "ghg排放强度"]):
        return "ghg_emissions_intensity", 0.94, "heuristic_ghg_emissions_intensity"

    if contains_any(text, ["能源消耗强度", "综合能源消耗强度", "单位能源消耗", "能耗强度"]):
        return "energy_consumption_intensity", 0.94, "heuristic_energy_consumption_intensity"

    if contains_any(text, ["天然气", "天然气消耗量", "天然气使用量"]):
        if not contains_any(text, ["排放因子", "排放系数", "换算系数", "核算方法"]):
            return "natural_gas_consumption", 0.9, "heuristic_natural_gas_consumption"

    if contains_any(text, ["新鲜水用量", "总耗水量", "用水量", "取水量", "市政购水量", "市政用水量", "营业办公耗水"]):
        if not contains_any(text, ["废水", "循环", "回用", "节水", "强度"]):
            return "water_consumption", 0.92, "heuristic_water"

    if contains_any(text, ["电使用量", "用电量", "耗电量", "电力总量", "外购电力", "营业办公消耗电力"]):
        if not contains_any(text, ["光伏", "新能源发电量", "清洁能源"]):
            return "electricity_consumption", 0.92, "heuristic_electricity"

    if contains_any(text, ["危险废弃物", "危险废物", "有害废弃物", "危废"]):
        return "hazardous_waste", 0.93, "heuristic_hazardous_waste"

    if contains_any(text, ["一般固体废弃物", "无害废弃物", "非危险废物", "一般废弃物"]):
        return "non_hazardous_waste", 0.93, "heuristic_non_hazardous_waste"

    # A broad table title such as "环境维度指标-环保投入" may be inherited by
    # later wastewater/waste rows. Only the row label itself can establish this
    # money metric.
    if contains_any(metric_name, ["环保总投资", "环保总投入", "环保投入", "环境保护投入", "环保投资"]):
        return "environmental_investment", 0.92, "heuristic_environmental_investment"

    # S
    if contains_any(text, ["人员总数", "员工总数", "员工总人数", "员工人数"]):
        if not contains_any(
                text,
                [
                    "男性",
                    "女性",
                    "少数民族",
                    "30岁",
                    "40岁",
                    "50岁",
                    "按性别",
                    "按年龄",
                    "培训",
                    "反腐败",
                    "反贪污",
                    "反商业贿赂",
                     "参与",
                     "参加",
                     "受训",
                     "帮扶困难员工",
                     "困难员工帮扶",
                     "慰问困难员工",
                 ],
         ):
             return "total_employees", 0.93, "heuristic_total_employees"

    if contains_any(text, ["男性员工人数", "男性员工数量"]):
        return "male_employees", 0.92, "heuristic_male_employees"

    if contains_any(text, ["女性员工人数", "女性员工数量"]):
        return "female_employees", 0.92, "heuristic_female_employees"

    if contains_any(text, ["女性管理层比例", "女性管理人员占比", "管理人员中女性"]):
        return "female_management_ratio", 0.92, "heuristic_female_management_ratio"

    if contains_any(text, ["培训投入", "培训费用", "培训支出费用"]):
        return "training_expense", 0.9, "heuristic_training_expense"

    if contains_any(text, ["员工平均培训时数", "员工受训平均时数", "人均培训时长", "平均培训时数"]):
        if not contains_any(text, ["高层", "中层", "基层", "新员工", "新入职", "反腐败", "安全生产", "安全培训"]):
            return "training_hours_per_employee", 0.9, "heuristic_training_hours_per_employee"

    if contains_any(text, ["社会保险覆盖率", "社保覆盖率", "社会保险参保率"]):
        return "social_security_coverage", 0.92, "heuristic_social_security_coverage"

    if contains_any(text, ["员工体检覆盖率", "体检覆盖率", "职业健康体检覆盖率"]):
        return "employee_medical_checkup_coverage", 0.9, "heuristic_employee_medical_checkup_coverage"

    if contains_any(text, ["安全生产投入", "职业健康安全投入", "安全生产费用", "安全费用投入"]):
        return "occupational_health_safety_investment", 0.9, "heuristic_ohs_investment"

    if contains_any(text, ["安全应急演练次数", "应急演练次数", "应急演练场次", "安全演练次数"]):
        return "safety_emergency_drill_count", 0.9, "heuristic_safety_emergency_drill_count"

    if contains_any(text, ["授权专利数", "新增授权专利", "专利授权"]):
        if not contains_any(text, ["累计", "有效专利拥有量"]):
            return "authorized_patents_new", 0.88, "heuristic_authorized_patents_new"

    # G
    if contains_any(text, ["董事会"]) and unit in {"次"} and not contains_any(text, ["专门委员会", "战略委员会", "审计委员会", "提名委员会", "薪酬与考核委员会"]):
        return "board_meetings", 0.94, "heuristic_board_meetings_short_label"

    if contains_any(text, ["董事会会议召开次数", "董事会会议次数", "董事会召开次数"]):
        return "board_meetings", 0.95, "heuristic_board_meetings"

    if contains_any(text, ["股东大会"]) and unit in {"次"}:
        return "shareholder_meetings", 0.94, "heuristic_shareholder_meetings_short_label"

    if contains_any(text, ["股东大会会议召开次数", "股东大会会议次数", "股东大会召开次数"]):
        return "shareholder_meetings", 0.95, "heuristic_shareholder_meetings"

    if contains_any(text, ["反腐败培训人次", "反贪污培训人次", "员工反腐败培训人次", "管理人员反腐败培训人次"]):
        return "anti_corruption_training_participants", 0.9, "heuristic_anti_corruption_training_participants"

    if contains_any(text, ["反腐败培训次数", "反贪污培训次数", "廉洁培训次数"]):
        return "anti_corruption_training_sessions", 0.9, "heuristic_anti_corruption_training_sessions"

    if contains_any(text, ["反贪污腐败举报事件总数", "举报案件数量", "举报事件总数"]):
        return "whistleblowing_cases", 0.9, "heuristic_whistleblowing_cases"

    return None, 0.0, "heuristic_no_match"


def alias_match(row: Dict[str, Any]) -> Tuple[Optional[str], float, str]:
    """
    根据 Core Schema aliases 做通用匹配。
    只产生候选，最终仍需 validate_schema_match。
    """
    text = row_text(row)
    normalized_text = row_alias_text(row)
    metric_text = metric_alias_text(row)

    best_field = None
    best_score = 0.0
    best_alias = None
    best_reason = None

    for item in ROUTE_A_SCHEMA:

        field_key = item["field_key"]
        aliases = [item.get("name_cn", ""), *item.get("aliases", [])]

        for alias in aliases:
            alias_norm = norm(alias)
            alias_key = normalize_alias_text(alias)
            if not alias_norm:
                continue

            if alias_norm in text:
                score = min(0.88 + len(alias_norm) / 100, 0.95)

                if score > best_score:
                    best_score = score
                    best_field = field_key
                    best_alias = alias
                    best_reason = "alias_match"

            if alias_key and alias_key in normalized_text:
                score = min(0.9 + len(alias_key) / 100, 0.96)

                if score > best_score:
                    best_score = score
                    best_field = field_key
                    best_alias = alias
                    best_reason = "normalized_alias_match"

            if (
                len(metric_text) >= ALIAS_FUZZY_MIN_LEN
                and len(alias_key) >= ALIAS_FUZZY_MIN_LEN
            ):
                ratio = fuzzy_ratio(metric_text, alias_key)
                if ratio >= ALIAS_FUZZY_THRESHOLD:
                    score = min(0.78 + ratio * 0.18, 0.94)

                    if score > best_score:
                        best_score = score
                        best_field = field_key
                        best_alias = alias
                        best_reason = f"fuzzy_alias_match:{ratio:.2f}"

    if best_field:
        return best_field, best_score, f"{best_reason}:{best_alias}"

    return None, 0.0, "alias_no_match"

def alias_match_candidates(row: Dict[str, Any]):
    """
    返回所有 alias 候选，而不是只返回最高分。
    这样最高分候选被 validator 拦掉后，还能尝试第二候选。
    """
    text = row_text(row)
    normalized_text = row_alias_text(row)
    metric_text = metric_alias_text(row)
    candidates = []

    for item in ROUTE_A_SCHEMA:

        field_key = item["field_key"]
        aliases = [item.get("name_cn", ""), *item.get("aliases", [])]

        for alias in aliases:
            alias_norm = norm(alias)
            alias_key = normalize_alias_text(alias)
            if not alias_norm:
                continue

            if alias_norm in text:
                score = min(0.88 + len(alias_norm) / 100, 0.96)
                candidates.append(
                    (
                        field_key,
                        score,
                        f"alias_match:{alias}",
                    )
                )

            if alias_key and alias_key in normalized_text:
                score = min(0.9 + len(alias_key) / 100, 0.97)
                candidates.append(
                    (
                        field_key,
                        score,
                        f"normalized_alias_match:{alias}",
                    )
                )

            if (
                len(metric_text) >= ALIAS_FUZZY_MIN_LEN
                and len(alias_key) >= ALIAS_FUZZY_MIN_LEN
            ):
                ratio = fuzzy_ratio(metric_text, alias_key)
                if ratio >= ALIAS_FUZZY_THRESHOLD:
                    score = min(0.78 + ratio * 0.18, 0.94)
                    candidates.append(
                        (
                            field_key,
                            score,
                            f"fuzzy_alias_match:{ratio:.2f}:{alias}",
                        )
                    )

    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates
def accept_or_reject(field_key: str, confidence: float, reason: str, row: Dict[str, Any]) -> Dict[str, Any]:
    """
    这个函数要放在 match_row_to_schema 前面。
    所有候选匹配都必须经过 Core Schema 驱动的校验器。
    """
    if field_key in TOTAL_FIELD_KEYS and contains_any(row_text(row) + norm(row.get("unit")), INTENSITY_MARKERS):
        return {
            "matched": False,
            "field_key": None,
            "confidence": confidence,
            "reason": f"intensity_or_per_capita_not_total_field; original_reason={reason}",
        }

    valid, validate_reason = validate_schema_match(field_key, row)

    if not valid:
        return {
            "matched": False,
            "field_key": None,
            "confidence": confidence,
            "reason": f"rejected_by_schema_validator:{validate_reason}; original_reason={reason}",
        }

    return {
        "matched": True,
        "field_key": field_key,
        "confidence": confidence,
        "reason": f"{reason}; {validate_reason}",
    }


def accept_llm_or_reject(field_key: str, confidence: float, reason: str, row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Let the semantic judge recover rows that only miss configured aliases.

    Unit conflicts, forbidden context, non-numeric values, and total/intensity
    conflicts remain hard failures.
    """
    strict_result = accept_or_reject(field_key, confidence, reason, row)
    if strict_result.get("matched"):
        return strict_result

    if confidence < SCHEMA_JUDGE_SOFT_ACCEPT_CONFIDENCE:
        return strict_result

    if "rejected_by_schema_validator:required_keyword_missing" not in strict_result.get("reason", ""):
        return strict_result

    if field_key in TOTAL_FIELD_KEYS and contains_any(row_text(row) + norm(row.get("unit")), INTENSITY_MARKERS):
        return strict_result

    valid, validate_reason = validate_schema_match(
        field_key,
        row,
        allow_required_missing=True,
    )
    if not valid:
        return {
            "matched": False,
            "field_key": None,
            "confidence": confidence,
            "reason": f"rejected_by_schema_validator:{validate_reason}; original_reason={reason}",
        }

    return {
        "matched": True,
        "field_key": field_key,
        "confidence": confidence,
        "reason": f"{reason}; {validate_reason}; semantic_judge_soft_accept",
    }


def match_row_to_schema(row: Dict[str, Any], *, allow_llm: bool = True) -> Dict[str, Any]:
    """
    对一条 VLM 抽出的表格行进行 Core ESG Schema 匹配。
    """

    precheck_result, precheck_match = policy_precheck(row)

    if precheck_result is not None:
        return precheck_result

    if precheck_match is not None:
        field, score, reason, *extra = precheck_match
        validation_row = extra[0] if extra else row
        return accept_or_reject(field, score, reason, validation_row)

    # 1. heuristic
    field, score, reason = heuristic_match(row)

    if field:
        return accept_or_reject(field, score, reason, row)

    if reason in {"business_performance_not_core_esg", "index_table_not_metric", "emission_factor_or_method_not_core_metric"}:
        return {
            "matched": False,
            "field_key": None,
            "confidence": 0.0,
            "reason": reason,
        }

    # 2. alias
    alias_candidates = alias_match_candidates(row)

    last_reject = None

    for field, score, reason in alias_candidates:
        result = accept_or_reject(field, score, reason, row)

        if result.get("matched"):
            return result

        last_reject = result

    if (
        last_reject is not None
        and "rejected_by_schema_validator:required_keyword_missing" not in last_reject.get("reason", "")
    ):
        return last_reject

    # 3. LLM fallback
    if allow_llm and LLM_MATCHER_ENABLED and llm_match_row_to_schema is not None:
        llm_result = llm_match_row_to_schema(row)

        if llm_result.get("matched") and llm_result.get("confidence", 0) >= SCHEMA_JUDGE_MIN_CONFIDENCE:
            return accept_llm_or_reject(
                llm_result["field_key"],
                llm_result.get("confidence", 0),
                llm_result.get("reason", "llm_match"),
                row,
            )

        return {
            "matched": False,
            "field_key": None,
            "confidence": llm_result.get("confidence", 0),
            "reason": llm_result.get("reason", "llm_no_match"),
        }

    if last_reject is not None:
        return last_reject

    return {
        "matched": False,
        "field_key": None,
        "confidence": 0.0,
        "reason": "no_schema_match",
    }
