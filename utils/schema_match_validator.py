from typing import Dict, Any, Tuple

from config.core_schema import ESG_SCHEMA
import unicodedata


UNIT_GROUPS = {
    "person_count": {"人", "名"},
    "person_time": {"人次", "人", "名"},
    "percentage": {"%", "百分比"},
    "money": {"元", "万元", "亿元", "人民币"},
    "count": {"次", "件", "起", "项", "个", "场次", "余次", "宗"},
    "hour": {"小时", "学时", "小时/人"},
    "energy": {"千瓦时","万千瓦时","兆瓦时","MWh","mwh","kwh","吨标煤","吨标准煤","万吨标准煤",},
    "water": {"吨", "万吨", "立方米", "万立方米"},
    "waste": {"吨", "万吨", "千克"},
    "ghg": {"吨", "万吨", "吨二氧化碳当量", "万吨二氧化碳当量", "tco2e"},
}



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


def unit_matches(unit: str, unit_type: str) -> bool:
    if not unit_type:
        return True

    if not unit:
        return True

    unit_norm = norm(unit)
    allowed_units = UNIT_GROUPS.get(unit_type)

    if not allowed_units:
        return True

    return any(norm(allowed) in unit_norm or unit_norm in norm(allowed) for allowed in allowed_units)


def validate_schema_match(field_key: str, row: Dict[str, Any]) -> Tuple[bool, str]:
    """
    通用 Schema 匹配校验器。

    不针对某家公司写规则，只读取 core_schema.py 中的：
    - unit_type
    - required_any
    - forbidden_any
    - value_type
    """

    schema_item = ESG_SCHEMA.get(field_key)

    if not schema_item:
        return False, "field_not_in_core_schema"

    metric_name = norm(row.get("metric_name") or row.get("row_label"))
    topic = norm(row.get("topic") or row.get("topic_label"))
    evidence_text = norm(row.get("evidence_text"))
    unit = norm(row.get("unit"))

    text = metric_name + topic + evidence_text

    if not text:
        return False, "empty_row_text"

    # 1. preferred_source 是 main_text_rag 的字段，不应该从表格直接匹配
    if schema_item.get("preferred_source") == "main_text_rag":
        return False, "main_text_rag_field_not_allowed_in_table_mapping"

    # 2. forbidden_any 命中，直接拒绝
    forbidden_any = schema_item.get("forbidden_any", [])
    if contains_any(text, forbidden_any):
        return False, "forbidden_keyword_hit"

    # 3. required_any 如果存在，必须至少命中一个
    required_any = schema_item.get("required_any", [])
    if required_any and not contains_any(text, required_any):
        return False, "required_keyword_missing"

    # 4. 单位类型校验
    unit_type = schema_item.get("unit_type")
    if not unit_matches(unit, unit_type):
        return False, f"unit_type_mismatch:{unit_type}"

    # 5. percentage 类型通常需要百分比单位
    value_type = schema_item.get("value_type")
    if value_type == "percentage":
        if unit and unit not in {"%", "百分比"}:
            return False, "percentage_field_requires_percentage_unit"

    return True, "schema_match_validated"