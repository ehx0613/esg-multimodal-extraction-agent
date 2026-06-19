import re
import unicodedata
from typing import Any, Dict, List, Tuple


PERCENT_RE = re.compile(r"%|％|百分比|占比|比例")
MONEY_RE = re.compile(r"元|万元|亿元|人民币|rmb|cny", re.I)
YEAR_RE = re.compile(r"20[0-3][0-9]")

PER_CAPITA_WORDS = ["人均", "每人", "单位面积", "强度", "密度", "单耗", "每平方米", "度/人", "吨/人"]
TRAINING_COUNT_WORDS = ["培训人数", "参训人数", "参与培训", "接受培训", "培训总人数", "受训人数"]
BOARD_TRAINING_WORDS = ["董事培训", "培训董事", "接受培训的董事", "反贪污培训", "反商业贿赂培训"]
SPECIAL_TRAINING_WORDS = ["税务培训", "专项培训", "专题培训", "安全培训", "单项培训"]
PROJECT_DONATION_WORDS = ["单个项目", "向", "捐赠"]

COUNT_FIELD_MARKERS = [
    "count",
    "number",
    "employees",
    "personnel",
    "board_size",
    "meetings",
    "days",
]
RATIO_FIELD_MARKERS = ["ratio", "rate", "coverage"]
TOTAL_FIELD_MARKERS = ["total", "consumption", "emissions", "discharge", "waste"]
MONEY_FIELD_MARKERS = ["investment", "expense", "revenue", "donation", "welfare"]
STRONG_UNIT_ANCHORS = [
    "tco2e",
    "co2e",
    "吨二氧化碳当量",
    "万吨二氧化碳当量",
    "二氧化碳当量",
    "mwh",
    "kwh",
    "兆瓦时",
    "千瓦时",
]
STRONG_UNIT_FIELD_MARKERS = [
    "ghg",
    "energy",
    "electricity",
]
SCOPE_1_WORDS = ["scope1", "scope 1", "范围一", "范围1", "直接排放", "直接温室气体排放"]
SCOPE_2_WORDS = ["scope2", "scope 2", "范围二", "范围2", "间接排放", "能源间接", "电力间接"]
PERSON_UNIT_WORDS = ["人", "名", "位", "人次"]

FIELD_ANCHOR_SOFT_PASS = {
    "total_employees": ["在职员工数", "在职员工人数", "员工总数", "员工总人数", "雇员总数"],
    "male_employees": ["男性员工人数", "男员工人数", "男性员工", "性别结构男", "男"],
    "female_employees": ["女性员工人数", "女员工人数", "女性员工", "性别结构女", "女"],
    "board_size": ["董事会在任董事", "董事会董事", "董事会成员", "董事会人数"],
    "independent_directors": ["独立董事", "独董"],
    "r_and_d_expense": ["研发总投入", "研发投入", "研发经费", "研发费用"],
    "occupational_health_safety_investment": ["安全生产总投入", "安全生产投入", "安全投入", "职业健康安全投入"],
    "environmental_investment": ["环保投入", "环境保护投入", "环境治理投入"],
    "public_welfare_investment": ["公益投入", "公益捐赠", "慈善捐赠", "对外捐赠"],
}

BOARD_SIZE_FORBIDDEN_SOFT_PASS = ["独立董事", "独董"]


def norm(value: Any) -> str:
    if value is None:
        return ""
    return unicodedata.normalize("NFKC", str(value)).lower().replace(" ", "")


def contains_any(text: str, words: List[str]) -> List[str]:
    text_norm = norm(text)
    return [word for word in words if norm(word) in text_norm]


def _field_key_has(field_key: str, markers: List[str]) -> bool:
    return any(marker in field_key for marker in markers)


def _append_reason(reasons: List[str], reason: str) -> None:
    if reason not in reasons:
        reasons.append(reason)


def _hits_schema_words(field_item: Dict[str, Any], evidence: str, key: str) -> List[str]:
    words = field_item.get(key, []) or []
    return contains_any(evidence, words)


def _strong_unit_soft_pass(field_key: str, value_blob: str, result: Dict[str, Any]) -> Tuple[bool, str]:
    if PERCENT_RE.search(value_blob):
        return False, ""
    if field_key in {"scope_1_emissions", "scope_2_emissions"}:
        return False, ""
    if not any(marker in field_key for marker in STRONG_UNIT_FIELD_MARKERS):
        return False, ""

    context = result.get("retrieval_context") or {}
    try:
        max_vector_score = float(context.get("max_vector_score") or 0.0)
    except Exception:
        max_vector_score = 0.0

    hit_units = " ".join(str(unit) for unit in context.get("hit_units", []) or [])
    unit_blob = " ".join([value_blob, hit_units])
    strong_hits = contains_any(unit_blob, STRONG_UNIT_ANCHORS)
    if strong_hits and max_vector_score >= 0.12:
        return True, f"soft_pass_strong_unit_anchor:{','.join(strong_hits[:3])};vector={max_vector_score:.4f}"
    return False, ""


def _has_strong_unit_anchor(value_blob: str, result: Dict[str, Any]) -> bool:
    context = result.get("retrieval_context") or {}
    hit_units = " ".join(str(unit) for unit in context.get("hit_units", []) or [])
    unit_blob = " ".join([value_blob, hit_units])
    return bool(contains_any(unit_blob, STRONG_UNIT_ANCHORS))


def _scope_specific_missing(field_key: str, value_blob: str) -> str:
    if field_key == "scope_1_emissions" and not contains_any(value_blob, SCOPE_1_WORDS):
        return "scope_1_requires_explicit_scope_or_direct_emission"
    if field_key == "scope_2_emissions" and not contains_any(value_blob, SCOPE_2_WORDS):
        return "scope_2_requires_explicit_scope_or_indirect_emission"
    return ""


def _field_anchor_soft_pass(field_key: str, value_blob: str) -> Tuple[bool, str]:
    anchors = FIELD_ANCHOR_SOFT_PASS.get(field_key, [])
    if not anchors:
        return False, ""

    anchor_hits = contains_any(value_blob, anchors)
    if not anchor_hits:
        return False, ""

    if field_key in {"total_employees", "male_employees", "female_employees", "board_size", "independent_directors"}:
        if not contains_any(value_blob, PERSON_UNIT_WORDS):
            return False, ""

    return True, f"soft_pass_field_anchor:{','.join(anchor_hits[:3])}"


def _can_ignore_board_size_forbidden(reason: str, value_blob: str) -> bool:
    if not reason.startswith("forbidden_hit:"):
        return False
    if not contains_any(reason, BOARD_SIZE_FORBIDDEN_SOFT_PASS):
        return False
    ok, _ = _field_anchor_soft_pass("board_size", value_blob)
    return ok


def validate_b2_quant_result(
    field_item: Dict[str, Any],
    result: Dict[str, Any],
    min_confidence: float = 0.72,
) -> Dict[str, Any]:
    if not result.get("matched"):
        result.setdefault("b2_validation_ok", False)
        result.setdefault("b2_validation_reason", result.get("reason", "not_matched"))
        return result

    field_key = field_item.get("field_key", "")
    evidence = str(result.get("evidence", "") or "")
    raw_value = str(result.get("raw_value", "") or "")
    unit = str(result.get("unit", "") or "")
    value_blob = " ".join([evidence, raw_value, unit, str(result.get("value", "") or "")])
    hard_reasons: List[str] = []
    soft_reasons: List[str] = []

    forbidden_hits = _hits_schema_words(field_item, evidence, "forbidden_any")
    if forbidden_hits:
        _append_reason(hard_reasons, f"forbidden_hit:{','.join(forbidden_hits[:3])}")

    required_words = field_item.get("required_any") or field_item.get("aliases") or []
    if required_words and not contains_any(evidence, required_words):
        _append_reason(hard_reasons, "required_keyword_missing_in_evidence")

    if not YEAR_RE.search(str(result.get("year", ""))):
        _append_reason(hard_reasons, "year_missing_or_invalid")

    is_count = _field_key_has(field_key, COUNT_FIELD_MARKERS)
    is_ratio = _field_key_has(field_key, RATIO_FIELD_MARKERS)
    is_intensity = (
        str(field_item.get("unit_type", "")).lower() == "intensity"
        or field_key.endswith("_intensity")
    )
    is_total = _field_key_has(field_key, TOTAL_FIELD_MARKERS) and not is_intensity
    is_money = _field_key_has(field_key, MONEY_FIELD_MARKERS)

    has_percent = bool(PERCENT_RE.search(value_blob))

    scope_reason = _scope_specific_missing(field_key, value_blob)
    if scope_reason:
        _append_reason(hard_reasons, scope_reason)
        if _has_strong_unit_anchor(value_blob, result):
            result["suggested_field_key"] = "total_ghg_emissions"
            result["redirect_reason"] = "scope_semantics_missing_but_ghg_unit_present"

    if is_count and has_percent and not is_ratio:
        _append_reason(hard_reasons, "count_field_has_percent_unit")

    if is_ratio:
        if not has_percent:
            _append_reason(hard_reasons, "ratio_field_without_percent_unit")
        try:
            value = float(str(result.get("value", "")).replace(",", ""))
            if not 0 <= value <= 100:
                _append_reason(hard_reasons, "ratio_value_out_of_range")
        except Exception:
            _append_reason(hard_reasons, "ratio_value_not_numeric")

    if is_total and contains_any(value_blob, PER_CAPITA_WORDS):
        _append_reason(hard_reasons, "total_field_uses_intensity_or_per_capita")

    if is_money and not MONEY_RE.search(value_blob):
        _append_reason(hard_reasons, "money_field_without_money_unit")

    if field_key in {"male_employees", "female_employees", "total_employees"}:
        if contains_any(value_blob, TRAINING_COUNT_WORDS):
            _append_reason(hard_reasons, "employee_count_uses_training_count")
        if has_percent:
            _append_reason(hard_reasons, "employee_count_uses_ratio")

    if field_key == "board_size" and contains_any(value_blob, BOARD_TRAINING_WORDS + ["培训"]):
        _append_reason(hard_reasons, "board_size_uses_training_board_count")

    if field_key == "safety_emergency_drill_count":
        safety_drill_context = [
            "安全",
            "生产安全",
            "消防",
            "环境应急",
            "突发事件",
            "应急预案",
            "事故",
            "防灾",
        ]
        if not contains_any(evidence, safety_drill_context):
            _append_reason(hard_reasons, "safety_drill_requires_safety_or_emergency_management_context")

    if field_key == "training_coverage_rate" and contains_any(value_blob, SPECIAL_TRAINING_WORDS):
        _append_reason(soft_reasons, "training_coverage_special_scope")

    if field_key == "public_welfare_investment" and contains_any(evidence, PROJECT_DONATION_WORDS):
        _append_reason(soft_reasons, "public_welfare_single_project_or_partial_donation")

    confidence = float(result.get("confidence", 0.0) or 0.0)
    if soft_reasons:
        confidence = max(0.0, confidence - 0.18 * len(soft_reasons))
        result["confidence"] = round(confidence, 4)

    field_soft_ok, field_soft_reason = _field_anchor_soft_pass(field_key, value_blob)
    if field_soft_ok:
        hard_reasons = [
            reason
            for reason in hard_reasons
            if reason != "required_keyword_missing_in_evidence"
            and not (field_key == "board_size" and _can_ignore_board_size_forbidden(reason, value_blob))
        ]
        _append_reason(soft_reasons, field_soft_reason)

    if (
        field_key == "training_hours_per_employee"
        and "required_keyword_missing_in_evidence" in hard_reasons
        and "/" in norm(unit)
    ):
        hard_reasons.remove("required_keyword_missing_in_evidence")
        _append_reason(soft_reasons, "soft_pass_per_employee_unit")

    if hard_reasons:
        if hard_reasons == ["required_keyword_missing_in_evidence"]:
            soft_pass_ok, soft_pass_reason = _strong_unit_soft_pass(field_key, value_blob, result)
            if soft_pass_ok:
                hard_reasons = []
                _append_reason(soft_reasons, soft_pass_reason)

    if hard_reasons:
        result["matched"] = False
        result["confidence"] = 0.0
        result["b2_validation_ok"] = False
        result["b2_validation_reason"] = ";".join(hard_reasons + soft_reasons)
        result["reason"] = f"b2_validation_failed:{result['b2_validation_reason']}"
        return result

    if confidence < min_confidence:
        result["matched"] = False
        result["b2_validation_ok"] = False
        result["b2_validation_reason"] = "confidence_below_threshold_after_penalty"
        result["reason"] = "b2_validation_failed:confidence_below_threshold_after_penalty"
        return result

    result["b2_validation_ok"] = True
    result["b2_validation_reason"] = ";".join(soft_reasons)
    if soft_reasons and result.get("reason"):
        result["reason"] = f"{result['reason']};soft_penalty:{','.join(soft_reasons)}"
    elif soft_reasons:
        result["reason"] = f"soft_penalty:{','.join(soft_reasons)}"
    return result
