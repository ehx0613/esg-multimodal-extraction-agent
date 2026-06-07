import json
import re
import time
import unicodedata
from difflib import SequenceMatcher
from typing import Dict, Any, List

from config.settings import (
    DASHSCOPE_API_KEY,
    SCHEMA_JUDGE_ESCALATE_MAX_CONFIDENCE,
    SCHEMA_JUDGE_ESCALATE_MIN_CONFIDENCE,
    SCHEMA_JUDGE_FALLBACK_ENABLED,
    SCHEMA_JUDGE_FALLBACK_MODEL,
    SCHEMA_JUDGE_MODEL,
    SCHEMA_JUDGE_TOP_K,
)
from config.schema import ROUTE_A_SCHEMA
from utils.call_tracker import get_active_run_mode, model_call_allowed, record_model_call
from utils.metric_normalizer import candidate_atom_score, filter_compatible_candidates, normalize_metric_row


FIELD_SEMANTIC_HINTS = {
    "environmental_investment": ["绿色", "生态", "环境治理", "污染防治", "环保支出", "环保费用"],
    "occupational_health_safety_investment": ["安全费用", "安健环", "职业健康", "安全保障"],
    "r_and_d_expense": ["创新投入", "科技投入", "研发经费", "科研经费"],
    "public_welfare_investment": ["慈善", "捐赠", "公益", "乡村振兴", "社会贡献"],
    "social_security_coverage": ["参保", "社保", "社会保障", "五险"],
    "employee_medical_checkup_coverage": ["健康检查", "健康档案", "体检"],
    "trained_employees_count": ["受训", "参训", "培训参与", "培训人次"],
    "training_coverage_rate": ["培训覆盖", "受训覆盖", "参训比例"],
    "employee_turnover_rate": ["离职", "流失", "员工稳定"],
    "anti_corruption_training_participants": ["廉洁宣导", "廉政教育", "合规培训", "反舞弊培训"],
    "anti_corruption_training_sessions": ["廉洁宣导", "廉政教育", "合规培训", "反舞弊培训"],
    "environmental_penalty_count": ["环保处罚", "环境违规", "环境事件"],
    "confirmed_corruption_cases": ["腐败案件", "贪污案件", "舞弊案件", "廉洁事件"],
}


def _get_client():
    from openai import OpenAI

    return OpenAI(
        api_key=DASHSCOPE_API_KEY,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
    )


def extract_json(text: str) -> Dict[str, Any]:
    """
    兼容模型输出 ```json ... ``` 的情况。
    """
    text = text.strip()
    text = re.sub(r"^```json", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"^```", "", text).strip()
    text = re.sub(r"```$", "", text).strip()

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]

    return json.loads(text)


def _norm(value: Any) -> str:
    return re.sub(
        r"[\s()（）【】\[\]{}《》<>:：,，;；、/\\|·.\-—_]",
        "",
        unicodedata.normalize("NFKC", str(value or "")).lower(),
    )


def _row_text(row: Dict[str, Any]) -> str:
    return " ".join(
        str(row.get(key) or "")
        for key in ["metric_name", "row_label", "topic", "topic_label", "table_title", "evidence_text", "unit"]
    )


def _candidate_score(row: Dict[str, Any], item: Dict[str, Any]) -> float:
    atoms = normalize_metric_row(row)
    trusted_text = _norm(atoms["trusted_text"])
    supporting_text = _norm(atoms["supporting_text"])
    metric_text = _norm(row.get("metric_name") or row.get("row_label"))
    if not trusted_text and not supporting_text:
        return 0.0

    phrases = [
        item.get("name_cn", ""),
        *item.get("aliases", []),
        *item.get("required_any", []),
    ]
    best = 0.0
    for phrase in phrases:
        phrase_norm = _norm(phrase)
        if not phrase_norm:
            continue
        if phrase_norm in metric_text:
            best = max(best, 1.0)
        elif phrase_norm in trusted_text:
            best = max(best, 0.82)
        elif phrase_norm in supporting_text:
            best = max(best, 0.35)
        best = max(
            best,
            SequenceMatcher(None, metric_text or trusted_text or supporting_text, phrase_norm).ratio(),
        )

    unit = _norm(row.get("unit"))
    if unit and any(_norm(example) in unit or unit in _norm(example) for example in item.get("unit_examples", [])):
        best += 0.12

    semantic_hits = [
        hint
        for hint in FIELD_SEMANTIC_HINTS.get(item["field_key"], [])
        if _norm(hint) and _norm(hint) in trusted_text
    ]
    best += min(len(semantic_hits), 2) * 0.22
    atom_result = candidate_atom_score(item, row)
    return round(best * 0.75 + atom_result["score"] * 0.5, 4)


def _ranked_candidate(row: Dict[str, Any], item: Dict[str, Any]) -> Dict[str, Any]:
    atom_result = candidate_atom_score(item, row)
    return {
        **item,
        "candidate_score": _candidate_score(row, item),
        "matched_signals": atom_result["signals"],
    }


def select_schema_candidates_with_diagnostics(
    row: Dict[str, Any],
    top_k: int = SCHEMA_JUDGE_TOP_K,
) -> tuple[List[Dict[str, Any]], Dict[str, str]]:
    compatible, rejected = filter_compatible_candidates(ROUTE_A_SCHEMA, row)
    ranked = sorted(
        (_ranked_candidate(row, item) for item in compatible),
        key=lambda item: item["candidate_score"],
        reverse=True,
    )
    return ranked[:max(1, top_k)], rejected


def select_schema_candidates(row: Dict[str, Any], top_k: int = SCHEMA_JUDGE_TOP_K) -> List[Dict[str, Any]]:
    candidates, _ = select_schema_candidates_with_diagnostics(row, top_k=top_k)
    return candidates


def build_schema_text(candidates: List[Dict[str, Any]]) -> str:
    """
    给文本模型看的 Core Schema。
    注意：这里只给核心信息，不给太多解释，减少 token。
    """
    lines = []

    for item in candidates:

        aliases = "、".join(item.get("aliases", []))
        units = "、".join(item.get("unit_examples", []))

        lines.append(
            f"- field_key: {item['field_key']}\n"
            f"  name_cn: {item['name_cn']}\n"
            f"  category: {item['category']}\n"
            f"  value_type: {item['value_type']}\n"
            f"  atoms: {json.dumps(item.get('atoms', {}), ensure_ascii=False)}\n"
            f"  mutex: {json.dumps(item.get('mutex', {}), ensure_ascii=False)}\n"
            f"  candidate_score: {item.get('candidate_score', 0)}\n"
            f"  matched_signals: {json.dumps(item.get('matched_signals', []), ensure_ascii=False)}\n"
            f"  aliases: {aliases}\n"
            f"  unit_examples: {units}"
        )

    return "\n".join(lines)


def build_prompt(row: Dict[str, Any], candidates: List[Dict[str, Any]]) -> str:
    schema_text = build_schema_text(candidates)
    normalized_row = normalize_metric_row(row)

    return f"""
你是 ESG 指标标准化匹配器。

你的任务：
根据给定的候选 Core ESG 字段，判断一条 ESG 表格指标行是否能匹配到某个标准 field_key。

重要规则：
1. 只能从给出的候选字段中选择 field_key。
2. 如果指标不属于 Core Schema，必须 matched=false。
3. 不要为了提高匹配率而强行匹配。
4. 经营绩效类指标如营业收入、净利润、资产总额、纳税总额，通常不属于 Core ESG Schema。
5. 党建活动、投资者教育、绿色融资、客户满意度等，如果 Core Schema 没有对应字段，应 matched=false。
6. 如果是“直接温室气体排放量 / 范围一”，应匹配 scope_1_emissions。
7. 如果是“间接温室气体排放量 / 范围二”，应匹配 scope_2_emissions。
8. 如果是“新鲜水用量 / 用水量 / 耗水量”，通常匹配 water_consumption。
9. 企业可能使用 Schema 未收录的同义表达。若语义、指标口径、单位和数值绑定均明确，可以匹配并说明依据。
10. 严格区分总量、强度、人均值、人数、次数、金额和比例；存在口径冲突时必须 matched=false。
11. 如果不确定，matched=false，confidence 不要高于 0.5。
12. 原子信息缺失不是冲突；只有明确口径冲突才必须拒绝。
13. 至少需要两个支持信号，或一个非常明确的同义指标名称，才能 matched=true。

候选 Core ESG 字段:
{schema_text}

待匹配表格行：
{json.dumps(row, ensure_ascii=False, indent=2)}

标准化原子信息：
{json.dumps(normalized_row, ensure_ascii=False, indent=2)}

请输出严格 JSON，不要输出 Markdown，不要解释。

输出格式：
{{
  "matched": true,
  "field_key": "water_consumption",
  "confidence": 0.92,
  "reason": "新鲜水用量属于水资源消耗量，单位为万吨。"
}}

如果不能匹配：
{{
  "matched": false,
  "field_key": null,
  "confidence": 0.25,
  "reason": "该指标属于经营绩效或公司特色指标，不属于 Core ESG Schema。"
}}
""".strip()


def _normalize_judge_result(
    result: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    model: str,
) -> Dict[str, Any]:
    matched = bool(result.get("matched"))
    field_key = result.get("field_key")
    try:
        confidence = float(result.get("confidence", 0))
    except Exception:
        confidence = 0.0
    reason = str(result.get("reason", "") or "")
    candidate_keys = [item["field_key"] for item in candidates]

    if not matched:
        return {
            "matched": False,
            "field_key": None,
            "confidence": confidence,
            "reason": f"semantic_judge_no_match:{reason}",
            "judge_model": model,
            "candidate_field_keys": candidate_keys,
        }

    if field_key not in set(candidate_keys):
        return {
            "matched": False,
            "field_key": None,
            "confidence": confidence,
            "reason": f"semantic_judge_invalid_field_key:{field_key}",
            "judge_model": model,
            "candidate_field_keys": candidate_keys,
        }

    return {
        "matched": True,
        "field_key": field_key,
        "confidence": confidence,
        "reason": f"semantic_judge_match:{reason}",
        "judge_model": model,
        "candidate_field_keys": candidate_keys,
    }


def _call_schema_judge(client, prompt: str, candidates: List[Dict[str, Any]], model: str) -> Dict[str, Any]:
    if not model_call_allowed("schema_judge"):
        return {
            "matched": False,
            "field_key": None,
            "confidence": 0.0,
            "reason": "model_call_budget_exhausted",
            "judge_model": model,
            "candidate_field_keys": [item["field_key"] for item in candidates],
        }
    started_at = time.time()
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={"type": "json_object"},
        )
        record_model_call(
            stage="schema_judge",
            model=model,
            started_at=started_at,
            response=response,
            metadata={"candidate_field_keys": [item["field_key"] for item in candidates]},
        )
    except Exception as exc:
        record_model_call(
            stage="schema_judge",
            model=model,
            started_at=started_at,
            metadata={"candidate_field_keys": [item["field_key"] for item in candidates]},
            error=str(exc),
        )
        raise
    content = response.choices[0].message.content
    return _normalize_judge_result(extract_json(content), candidates, model)


def _should_escalate(result: Dict[str, Any]) -> bool:
    if not SCHEMA_JUDGE_FALLBACK_ENABLED or not SCHEMA_JUDGE_FALLBACK_MODEL:
        return False
    confidence = float(result.get("confidence", 0.0) or 0.0)
    return SCHEMA_JUDGE_ESCALATE_MIN_CONFIDENCE <= confidence < SCHEMA_JUDGE_ESCALATE_MAX_CONFIDENCE


def llm_match_row_to_schema(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    使用 qwen-plus 对单条表格行进行 Core Schema 匹配。
    只建议在规则 / 别名匹配失败后调用。
    """
    if not DASHSCOPE_API_KEY:
        return {
            "matched": False,
            "field_key": None,
            "confidence": 0.0,
            "reason": "DASHSCOPE_API_KEY_empty",
        }

    run_mode = get_active_run_mode()
    recalled_candidates, filter_rejections = select_schema_candidates_with_diagnostics(
        row,
        top_k=5 if run_mode == "fast" else SCHEMA_JUDGE_TOP_K,
    )
    normalized_metric = normalize_metric_row(row)
    if recalled_candidates:
        top_score = float(recalled_candidates[0].get("candidate_score", 0.0) or 0.0)
        candidates = [
            item
            for item in recalled_candidates
            if float(item.get("candidate_score", 0.0) or 0.0) >= max(0.35, top_score - 0.30)
        ][:3]
    else:
        candidates = []
    if not candidates:
        return {
            "matched": False,
            "field_key": None,
            "confidence": 0.0,
            "reason": "no_compatible_schema_candidates",
            "candidate_field_keys": [],
            "candidate_filter_rejections": filter_rejections,
            "normalized_metric": normalized_metric,
            "recalled_candidates": [
                {
                    "field_key": item["field_key"],
                    "candidate_score": item.get("candidate_score"),
                    "matched_signals": item.get("matched_signals", []),
                }
                for item in recalled_candidates
            ],
        }
    prompt = build_prompt(row, candidates)

    try:
        client = _get_client()
        primary_result = _call_schema_judge(client, prompt, candidates, SCHEMA_JUDGE_MODEL)
        primary_result["candidate_filter_rejections"] = filter_rejections
        primary_result["normalized_metric"] = normalized_metric
        if run_mode == "fast" or not _should_escalate(primary_result):
            primary_result["judge_escalated"] = False
            return primary_result

        fallback_result = _call_schema_judge(client, prompt, candidates, SCHEMA_JUDGE_FALLBACK_MODEL)
        fallback_result["candidate_filter_rejections"] = filter_rejections
        fallback_result["normalized_metric"] = normalized_metric
        fallback_result["judge_escalated"] = True
        fallback_result["primary_judge"] = {
            "model": primary_result.get("judge_model"),
            "matched": primary_result.get("matched"),
            "field_key": primary_result.get("field_key"),
            "confidence": primary_result.get("confidence"),
            "reason": primary_result.get("reason"),
        }
        return fallback_result

    except Exception as e:
        return {
            "matched": False,
            "field_key": None,
            "confidence": 0.0,
            "reason": f"llm_error:{e}",
        }
