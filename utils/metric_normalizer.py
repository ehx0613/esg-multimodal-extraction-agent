import re
import unicodedata
from typing import Any, Dict, Tuple

from utils.schema_match_validator import unit_matches


CATEGORY_MARKERS = {
    "E": ["环境", "能源", "温室气体", "碳排放", "废水", "废弃物", "污染物", "用水", "用电", "天然气"],
    "S": ["社会", "员工", "雇员", "职工", "培训", "安全生产", "职业健康", "研发", "公益"],
    "G": ["治理", "董事", "股东大会", "反腐败", "廉洁", "腐败案件"],
}

SUBJECT_MARKERS = {
    "scope_1_hint": ["范围一", "范围1", "scope1", "直接温室气体"],
    "scope_2_hint": ["范围二", "范围2", "scope2", "间接温室气体"],
    "ghg": ["温室气体", "碳排放", "ghg", "二氧化碳当量"],
    "renewable_electricity": ["绿电", "可再生能源电力"],
    "electricity": ["用电", "耗电", "电力", "外购电"],
    "natural_gas": ["天然气"],
    "wastewater": ["废水", "污水"],
    "water": ["用水", "取水", "耗水", "新鲜水", "水资源"],
    "non_hazardous_waste": ["无害废弃物", "非危险废弃物", "一般废弃物", "一般固体废弃物", "无废废弃物"],
    "hazardous_waste": ["危险废弃物", "危险废物", "危废", "有害废弃物", "有废废弃物"],
    "air_pollutant": ["废气", "大气污染物", "氮氧化物", "二氧化硫", "颗粒物", "vocs"],
    "energy": ["能源", "能耗", "标准煤"],
    "environmental_violation": ["环境违规", "环保处罚", "环境处罚", "环境违法"],
    "environment": ["环保", "环境保护", "污染防治", "环境治理"],
    "new_hire": ["新进员工", "新入职员工", "新员工"],
    "departed_employee": ["离职员工", "流失员工", "离职人员"],
    "anti_corruption_training": ["反腐败培训", "反贪污培训", "廉洁培训", "反舞弊培训", "商业道德培训"],
    "corruption_case": ["腐败案件", "贪污案件", "商业贿赂案件", "舞弊案件"],
    "board_meeting": ["董事会会议", "召开董事会"],
    "shareholder_meeting": ["股东大会会议", "召开股东大会"],
    "committee_meeting": ["专门委员会", "审计委员会", "提名委员会", "薪酬与考核委员会"],
    "director": ["董事会成员", "独立董事", "女性董事", "董事"],
    "management": ["管理层", "管理人员", "高级管理层", "高管"],
    "social_security": ["社会保险", "社保", "五险"],
    "medical_checkup": ["体检", "健康检查", "健康档案"],
    "employee_training": ["员工培训", "受训员工", "培训员工", "培训覆盖", "培训时长"],
    "safety_accident": ["安全事故", "生产安全事故", "工伤事故"],
    "emergency_drill": ["应急演练", "安全演练"],
    "occupational_safety": ["安全生产投入", "职业健康安全投入", "安全费用"],
    "work_injury": ["工伤", "损失工作日", "损失工时"],
    "r_and_d": ["研发", "科研", "科技创新"],
    "public_welfare": ["公益", "慈善", "捐赠", "乡村振兴"],
    "supplier": ["供应商"],
    "employee": ["员工", "雇员", "职工", "人员构成", "员工构成", "员工结构"],
}

SCOPE_MARKERS = {
    "scope_1": ["范围一", "范围1", "scope1", "直接温室气体"],
    "scope_2": ["范围二", "范围2", "scope2", "间接温室气体"],
    "scope_3": ["范围三", "范围3", "scope3"],
    "new_hire": ["新进员工", "新入职员工", "新员工"],
    "departed_employee": ["离职员工", "流失员工"],
    "independent": ["独立董事", "独董"],
    "female": ["女性", "女员工", "女董事"],
    "male": ["男性", "男员工", "男董事"],
}

MEASURE_MARKERS = {
    "emission": ["排放"],
    "consumption": ["消耗", "使用量", "用量", "耗用", "耗电", "用电", "用水", "取水", "能耗"],
    "discharge": ["排放量", "排放总量"],
    "generation": ["产生量", "产生总量"],
    "investment": ["投入", "投资", "费用", "支出", "金额", "捐赠"],
    "coverage": ["覆盖率", "参与率", "参保率"],
    "turnover": ["流失率", "离职率", "流动率"],
    "duration": ["时长", "时数", "小时", "工时"],
    "participants": ["参与人数", "参与人次", "培训人数", "培训人次", "受训人数", "受训人次"],
    "sessions": ["培训次数", "培训场次"],
    "personnel": ["人员数量", "人员人数", "人员总数"],
    "lost_days": ["损失工作日", "损失天数", "损失工时"],
    "count": ["次数", "数量", "人数", "人次", "总数", "场次", "案件数"],
}

AGGREGATION_MARKERS = {
    "percentage": ["比例", "占比", "覆盖率", "参与率", "流失率", "离职率", "%", "百分比"],
    "intensity": ["强度", "密度", "单位产品", "单位产值", "单位营收", "单位收入", "单耗"],
    "per_capita": ["人均", "每人"],
    "average": ["平均"],
    "total": ["总量", "总计", "合计", "总数", "总时长", "总投入"],
}

UNIT_TYPE_MARKERS = {
    "percentage": ["%", "百分比"],
    "intensity": ["/", "每", "单位"],
    "person_time": ["人次"],
    "person_count": ["人", "名", "位"],
    "money": ["亿元", "百万元", "万元", "人民币元", "元"],
    "hour": ["小时", "hour"],
    "ghg": ["tco2e", "co2e", "二氧化碳当量"],
    "energy": ["吨标准煤", "吨标煤", "千瓦时", "兆瓦时", "kwh", "mwh", "吉焦", "gj"],
    "mass": ["吨", "千克", "公斤", "kg"],
    "count": ["次", "件", "起", "宗", "场", "项", "天", "日"],
}

ATOM_WEIGHTS = {
    "category": 0.10,
    "subject": 0.30,
    "scope": 0.20,
    "measure": 0.20,
    "aggregation": 0.10,
    "unit_type": 0.10,
}

PHYSICAL_MASS_UNIT_TYPES = {"mass", "water", "waste"}


def norm(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    return re.sub(r"\s+", "", text)


def contains_any(text: Any, words) -> bool:
    normalized = norm(text)
    return any(norm(word) in normalized for word in words if norm(word))


def infer_from_markers(text: Any, markers: Dict[str, list[str]], order: list[str] | None = None) -> str:
    for key in order or list(markers):
        if contains_any(text, markers[key]):
            return key
    return "unknown"


def infer_category(text: Any) -> str:
    hits = [category for category, markers in CATEGORY_MARKERS.items() if contains_any(text, markers)]
    return hits[0] if len(hits) == 1 else "unknown"


def infer_unit_type(unit: Any) -> str:
    unit_text = norm(unit)
    if not unit_text:
        return "unknown"
    return infer_from_markers(unit_text, UNIT_TYPE_MARKERS)


def unit_types_compatible(row_unit_type: str, schema_unit_type: str) -> bool:
    if row_unit_type in {"unknown", "other"} or not schema_unit_type:
        return True
    if row_unit_type == schema_unit_type:
        return True
    return row_unit_type in PHYSICAL_MASS_UNIT_TYPES and schema_unit_type in PHYSICAL_MASS_UNIT_TYPES


def normalize_metric_row(row: Dict[str, Any]) -> Dict[str, Any]:
    metric_name = str(row.get("metric_name") or row.get("row_label") or "")
    topic = str(row.get("topic") or row.get("topic_label") or "")
    table_title = str(row.get("table_title") or "")
    evidence_text = str(row.get("evidence_text") or "")
    unit = str(row.get("unit") or "")
    trusted_text = f"{metric_name} {topic}"
    supporting_text = f"{table_title} {evidence_text}"
    combined = f"{trusted_text} {supporting_text}"
    subject_order = [
        "ghg", "renewable_electricity", "electricity", "natural_gas", "wastewater", "water",
        "non_hazardous_waste", "hazardous_waste", "air_pollutant", "energy",
        "environmental_violation", "new_hire", "departed_employee", "anti_corruption_training",
        "corruption_case", "board_meeting", "shareholder_meeting", "committee_meeting", "director",
        "management", "social_security", "medical_checkup", "employee_training", "safety_accident",
        "emergency_drill", "occupational_safety", "work_injury", "r_and_d", "public_welfare",
        "supplier", "employee", "environment",
    ]
    return {
        "metric_name": metric_name,
        "topic": topic,
        "table_title": table_title,
        "unit": unit,
        "trusted_text": trusted_text,
        "supporting_text": supporting_text,
        "evidence_text": evidence_text,
        "category": infer_category(trusted_text),
        "subject": infer_from_markers(combined, SUBJECT_MARKERS, subject_order),
        "scope": infer_from_markers(combined, SCOPE_MARKERS),
        "measure": infer_from_markers(metric_name or combined, MEASURE_MARKERS),
        "aggregation": infer_from_markers(f"{metric_name} {unit}", AGGREGATION_MARKERS),
        "unit_type": infer_unit_type(unit),
    }


def _schema_atom_values(item: Dict[str, Any], dimension: str) -> set[str]:
    value = item.get("atoms", {}).get(dimension, [])
    return {str(part) for part in value if part}


def _mutex_values(item: Dict[str, Any], dimension: str) -> set[str]:
    value = item.get("mutex", {}).get(f"{dimension}s", [])
    return {str(part) for part in value if part}


def candidate_atom_score(item: Dict[str, Any], row: Dict[str, Any]) -> Dict[str, Any]:
    row_atoms = normalize_metric_row(row)
    signals: list[str] = []
    conflicts: list[str] = []
    score = 0.0

    unit = row_atoms["unit"]
    schema_unit_type = item.get("unit_type", "")
    if not unit_types_compatible(row_atoms["unit_type"], schema_unit_type):
        conflicts.append(f"unit_type:{row_atoms['unit_type']}!={schema_unit_type}")

    trusted_and_evidence = f"{row_atoms['trusted_text']} {row_atoms['evidence_text']}"
    if item.get("forbidden_any") and contains_any(trusted_and_evidence, item["forbidden_any"]):
        conflicts.append("forbidden_keyword_hit")

    for dimension in ["subject", "scope", "aggregation"]:
        row_value = row_atoms.get(dimension, "unknown")
        if row_value != "unknown" and row_value in _mutex_values(item, dimension):
            conflicts.append(f"mutex_{dimension}:{row_value}")

    if conflicts:
        return {
            "compatible": False,
            "score": 0.0,
            "signals": signals,
            "conflicts": conflicts,
            "row_atoms": row_atoms,
        }

    if row_atoms["category"] != "unknown" and row_atoms["category"] == item.get("category"):
        score += ATOM_WEIGHTS["category"]
        signals.append(f"category:{row_atoms['category']}")

    for dimension in ["subject", "scope", "measure", "aggregation"]:
        row_value = row_atoms.get(dimension, "unknown")
        if row_value != "unknown" and row_value in _schema_atom_values(item, dimension):
            score += ATOM_WEIGHTS[dimension]
            signals.append(f"{dimension}:{row_value}")

    if row_atoms["unit_type"] not in {"unknown", "other"} and unit_types_compatible(row_atoms["unit_type"], schema_unit_type):
        score += ATOM_WEIGHTS["unit_type"]
        signals.append(f"unit_type:{schema_unit_type}")

    return {
        "compatible": True,
        "score": round(score, 4),
        "signals": signals,
        "conflicts": [],
        "row_atoms": row_atoms,
    }


def candidate_compatibility(item: Dict[str, Any], row: Dict[str, Any]) -> Tuple[bool, str]:
    result = candidate_atom_score(item, row)
    if result["compatible"]:
        return True, f"prefilter_compatible:atom_score={result['score']:.2f}"
    return False, f"prefilter_conflict:{'|'.join(result['conflicts'])}"


def filter_compatible_candidates(
    candidates: list[Dict[str, Any]],
    row: Dict[str, Any],
) -> tuple[list[Dict[str, Any]], Dict[str, str]]:
    compatible = []
    rejected = {}
    for item in candidates:
        ok, reason = candidate_compatibility(item, row)
        if ok:
            compatible.append(item)
        else:
            rejected[item.get("field_key", "")] = reason
    return compatible, rejected


__all__ = [
    "candidate_atom_score",
    "candidate_compatibility",
    "filter_compatible_candidates",
    "normalize_metric_row",
    "unit_types_compatible",
]
