import re
import re
import unicodedata
from typing import Any, Dict, Tuple

from config.schema import ESG_SCHEMA


UNIT_GROUPS = {
    "person_count": {"人", "名", "位"},
    "person_time": {"人", "名", "人次", "位"},
    "percentage": {"%", "百分比"},
    "money": {"元", "万元", "百万元", "亿元", "人民币元"},
    "count": {"次", "件", "起", "宗", "场", "项", "天", "日", "小时"},
    "hour": {"小时", "时", "h", "hour"},
    "energy": {"千瓦时", "兆瓦时", "kwh", "mwh", "吨标准煤", "吨标煤", "吉焦", "gj", "立方米", "万立方米", "m3", "m³"},
    "intensity": {
        "吨标准煤/万元",
        "吨标煤/万元",
        "千瓦时/万元",
        "兆瓦时/万元",
        "吨co2e/万元",
        "吨二氧化碳当量/万元",
        "tco2e/万元",
        "tco2e/百万元",
        "吨/万元",
        "kgce/万元",
    },
    "water": {"吨", "立方米", "m3", "m³"},
    "waste": {"吨", "千克", "公斤", "kg"},
    "mass": {"吨", "千克", "公斤", "kg"},
    "ghg": {
        "吨co2e",
        "吨二氧化碳当量",
        "tco2e",
        "二氧化碳当量吨",
        "二氧化碳当量公吨",
        "二氧化碳当量公吨数",
        "公吨二氧化碳当量",
    },
    "text": set(),
}


def norm(value: Any) -> str:
    if value is None:
        return ""
    return (
        unicodedata.normalize("NFKC", str(value))
        .lower()
        .replace(" ", "")
        .replace("\n", "")
        .replace("\t", "")
        .replace("（", "(")
        .replace("）", ")")
        .replace("：", ":")
        .replace("，", ",")
    )


def contains_any(text: str, words) -> bool:
    text_norm = norm(text)
    return any(norm(word) in text_norm for word in words if norm(word))


def choose_latest_raw_value(values: dict) -> Any:
    if not isinstance(values, dict) or not values:
        return None

    candidates = []
    for key, value in values.items():
        match = re.search(r"20[0-3][0-9]", str(key))
        if match:
            candidates.append((int(match.group(0)), value))

    if candidates:
        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    return list(values.values())[-1]


def is_numeric_like(value: Any) -> bool:
    if value is None:
        return False

    text = str(value).strip()
    if text in {"", "/", "-", "N/A", "NA", "不适用", "无"}:
        return False

    normalized = text.replace(",", "").replace("，", "").replace("%", "")
    try:
        float(normalized)
        return True
    except Exception:
        return False


def unit_matches(unit: str, unit_type: str) -> bool:
    if not unit_type or unit_type == "text":
        return True
    if not unit:
        return True

    unit_norm = norm(unit)
    if unit_type == "money" and contains_any(unit, ["人", "名", "位", "人次", "%", "小时", "吨", "立方米"]):
        return False

    if unit_type == "ghg" and contains_any(
        unit,
        ["tCO2e", "CO2e", "吨二氧化碳当量", "万吨二氧化碳当量", "二氧化碳当量"],
    ):
        return True

    if unit_type == "energy" and contains_any(
        unit,
        ["千瓦时", "兆瓦时", "kWh", "MWh", "度", "立方米", "万立方米"],
    ):
        return True

    if unit_type in {"water", "waste", "mass"} and contains_any(
        unit,
        ["吨", "立方米", "万立方米", "m3", "m³", "kg", "千克"],
    ):
        return True

    if unit_type in {"person_count", "person_time"} and contains_any(unit, ["人", "名", "人次"]):
        return True

    if unit_type == "intensity" and (
        "/" in unit_norm
        or "per" in unit_norm
        or contains_any(unit, ["每", "单位"])
    ):
        return True

    allowed_units = UNIT_GROUPS.get(unit_type)
    if not allowed_units:
        return True

    return any(norm(allowed) in unit_norm or unit_norm in norm(allowed) for allowed in allowed_units)


def ghg_unit_pivot_check(field_key: str, text: str, unit: str) -> Tuple[bool, str]:
    if field_key != "total_ghg_emissions":
        return False, ""

    if not contains_any(
        unit,
        ["tCO2e", "CO2e", "吨二氧化碳当量", "万吨二氧化碳当量", "二氧化碳当量"],
    ):
        return False, ""

    if contains_any(
        text,
        ["温室气体", "GHG", "碳排放", "二氧化碳", "排放量", "排放总量"],
    ):
        return True, "unit_pivot_soft_warning:ghg_unit_anchor"

    return False, ""


def field_specific_soft_check(field_key: str, text: str, unit: str) -> Tuple[bool, str]:
    if field_key == "water_consumption" and contains_any(
        text,
        ["用水总量", "水电总量", "水总量", "用水量", "取水量", "耗水量", "年度用水量"],
    ) and contains_any(unit, ["立方米", "m3", "m³", "吨"]):
        return True, "unit_pivot_soft_warning:water_ocr_or_alias"

    if field_key == "trained_employees_count" and contains_any(
        text,
        ["累计培训员工人次", "全年累计培训员工人次", "培训员工人次", "培训人次", "员工培训人次"],
    ) and contains_any(unit, ["人次", "人"]):
        return True, "alias_soft_warning:training_participants"

    if field_key == "employee_medical_checkup_coverage" and contains_any(
        text,
        ["体检及健康档案覆盖率", "健康体检覆盖率", "员工健康体检覆盖率"],
    ):
        return True, "alias_soft_warning:medical_checkup_coverage"

    return False, ""


def validate_schema_match(
    field_key: str,
    row: Dict[str, Any],
    allow_required_missing: bool = False,
) -> Tuple[bool, str]:
    schema_item = ESG_SCHEMA.get(field_key)
    if not schema_item:
        return False, "field_not_in_core_schema"

    metric_name = norm(row.get("metric_name") or row.get("row_label"))
    topic = norm(row.get("topic") or row.get("topic_label"))
    table_title = norm(row.get("table_title"))
    evidence_text = norm(row.get("evidence_text"))
    unit = norm(row.get("unit"))
    text = metric_name + topic + table_title + evidence_text

    if not text:
        return False, "empty_row_text"

    if schema_item.get("preferred_source") == "main_text_rag":
        return False, "main_text_rag_field_not_allowed_in_table_mapping"

    forbidden_any = schema_item.get("forbidden_any", [])
    if contains_any(text, forbidden_any):
        return False, "forbidden_keyword_hit"

    required_any = schema_item.get("required_any", [])
    if required_any and not contains_any(text, required_any):
        unit_pivot_ok, unit_pivot_reason = ghg_unit_pivot_check(field_key, text, unit)
        soft_ok, soft_reason = field_specific_soft_check(field_key, text, unit)
        if not unit_pivot_ok and not soft_ok and not allow_required_missing:
            return False, "required_keyword_missing"
        required_reason = (
            unit_pivot_reason
            or soft_reason
            or "schema_match_validated_with_soft_warning:required_keyword_missing"
        )
    else:
        required_reason = "schema_match_validated"

    unit_type = schema_item.get("unit_type")
    if not unit_matches(unit, unit_type):
        return False, f"unit_type_mismatch:{unit_type}"

    if schema_item.get("indicator_type") == "quantitative":
        raw_value = choose_latest_raw_value(row.get("values", {}))
        if not is_numeric_like(raw_value):
            return False, "quantitative_field_requires_numeric_value"

    if schema_item.get("value_type") == "percentage":
        if unit and not contains_any(unit, UNIT_GROUPS["percentage"]):
            return False, "percentage_field_requires_percentage_unit"

    return True, required_reason
