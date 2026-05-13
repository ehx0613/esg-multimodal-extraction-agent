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

from typing import Dict, Any, Tuple, Optional

from config.core_schema import CORE_SCHEMA, ESG_SCHEMA
from utils.schema_match_validator import validate_schema_match

try:
    from config.settings import LLM_MATCHER_ENABLED
except Exception:
    LLM_MATCHER_ENABLED = False

try:
    from utils.llm_schema_matcher import llm_match_row_to_schema
except Exception:
    llm_match_row_to_schema = None


import unicodedata

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

def contains_any(text: str, words) -> bool:
    text = norm(text)
    return any(norm(w) in text for w in words if norm(w))


def row_text(row: Dict[str, Any]) -> str:
    return (
        norm(row.get("metric_name") or row.get("row_label"))
        + norm(row.get("topic") or row.get("topic_label"))
        + norm(row.get("table_title"))
        + norm(row.get("evidence_text"))
    )

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
    return contains_any(
        text,
        [
            "资产总额",
            "净资产",
            "营业收入",
            "利润总额",
            "净利润",
            "纳税总额",
            "股东分红",
            "净资产收益率",
        ],
    )


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

    if not text:
        return None, 0.0, "empty_row_text"

    if is_business_performance(text):
        return None, 0.0, "business_performance_not_core_esg"

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
    if contains_any(text, ["范围一", "范围1", "范围 1", "scope1", "scope 1", "直接温室气体"]):
        return "scope_1_emissions", 0.96, "heuristic_scope_1"

    if contains_any(text, ["范围二", "范围2", "范围 2", "scope2", "scope 2", "间接温室气体"]):
        return "scope_2_emissions", 0.96, "heuristic_scope_2"

    if contains_any(text, ["范围三", "范围3", "范围 3", "scope3", "scope 3"]):
        return "scope_3_emissions", 0.94, "heuristic_scope_3"

    if contains_any(text, ["温室气体排放总量", "温室气体总排放", "碳排放总量"]):
        return "total_ghg_emissions", 0.94, "heuristic_total_ghg"

    if contains_any(text, ["新鲜水用量", "总耗水量", "用水量", "取水量", "营业办公耗水"]):
        if not contains_any(text, ["废水", "循环", "回用", "节水", "强度"]):
            return "water_consumption", 0.92, "heuristic_water"

    if contains_any(text, ["电使用量", "用电量", "耗电量", "外购电力", "营业办公消耗电力"]):
        if not contains_any(text, ["光伏", "新能源发电量", "清洁能源"]):
            return "electricity_consumption", 0.92, "heuristic_electricity"

    if contains_any(text, ["危险废弃物", "危险废物", "有害废弃物", "危废"]):
        return "hazardous_waste", 0.93, "heuristic_hazardous_waste"

    if contains_any(text, ["一般固体废弃物", "无害废弃物", "非危险废物", "一般废弃物"]):
        return "non_hazardous_waste", 0.93, "heuristic_non_hazardous_waste"

    if contains_any(text, ["环保总投资", "环保投入", "环境保护投入", "环保投资"]):
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

    if contains_any(text, ["授权专利数", "新增授权专利", "专利授权"]):
        if not contains_any(text, ["累计", "有效专利拥有量"]):
            return "authorized_patents_new", 0.88, "heuristic_authorized_patents_new"

    # G
    if contains_any(text, ["董事会会议召开次数", "董事会会议次数", "董事会召开次数"]):
        return "board_meetings", 0.95, "heuristic_board_meetings"

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

    best_field = None
    best_score = 0.0
    best_alias = None

    for item in CORE_SCHEMA:
        if item.get("preferred_source") == "main_text_rag":
            continue

        field_key = item["field_key"]
        aliases = item.get("aliases", [])

        for alias in aliases:
            alias_norm = norm(alias)
            if not alias_norm:
                continue

            if alias_norm in text:
                score = min(0.88 + len(alias_norm) / 100, 0.95)

                if score > best_score:
                    best_score = score
                    best_field = field_key
                    best_alias = alias

    if best_field:
        return best_field, best_score, f"alias_match:{best_alias}"

    return None, 0.0, "alias_no_match"

def alias_match_candidates(row: Dict[str, Any]):
    """
    返回所有 alias 候选，而不是只返回最高分。
    这样最高分候选被 validator 拦掉后，还能尝试第二候选。
    """
    text = row_text(row)
    candidates = []

    for item in CORE_SCHEMA:
        if item.get("preferred_source") == "main_text_rag":
            continue

        field_key = item["field_key"]
        aliases = item.get("aliases", [])

        for alias in aliases:
            alias_norm = norm(alias)
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

    candidates.sort(key=lambda x: x[1], reverse=True)
    return candidates
def accept_or_reject(field_key: str, confidence: float, reason: str, row: Dict[str, Any]) -> Dict[str, Any]:
    """
    这个函数要放在 match_row_to_schema 前面。
    所有候选匹配都必须经过 Core Schema 驱动的校验器。
    """
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


def match_row_to_schema(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    对一条 VLM 抽出的表格行进行 Core ESG Schema 匹配。
    """

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

    # 3. LLM fallback
    if LLM_MATCHER_ENABLED and llm_match_row_to_schema is not None:
        llm_result = llm_match_row_to_schema(row)

        if llm_result.get("matched") and llm_result.get("confidence", 0) >= 0.75:
            return accept_or_reject(
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

    return {
        "matched": False,
        "field_key": None,
        "confidence": 0.0,
        "reason": "no_schema_match",
    }
