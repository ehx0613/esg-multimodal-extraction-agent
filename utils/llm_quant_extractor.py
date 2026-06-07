import json
import re
import time
from typing import Any, Dict, List

from openai import OpenAI

from config.settings import DASHSCOPE_API_KEY, TEXT_MODEL
from config.settings import ROUTE_B2_MIN_CONFIDENCE
from utils.b2_result_validator import validate_b2_quant_result
from utils.json_utils import extract_json_from_text
from utils.call_tracker import model_call_allowed, record_model_call


client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)


NUMBER_RE = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?")
YEAR_RE = re.compile(r"20[0-3][0-9]")


def _retrieval_context(chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not chunks:
        return {
            "max_retrieval_score": 0.0,
            "max_vector_score": 0.0,
            "hit_units": [],
        }

    hit_units = []
    for chunk in chunks:
        hit_units.extend(chunk.get("hit_units", []) or [])

    return {
        "max_retrieval_score": max(float(chunk.get("retrieval_score") or 0.0) for chunk in chunks),
        "max_vector_score": max(float(chunk.get("vector_score") or 0.0) for chunk in chunks),
        "hit_units": list(dict.fromkeys(str(unit) for unit in hit_units if unit)),
    }


def build_route_b2_prompt(field_item: Dict[str, Any], chunks: List[Dict[str, Any]]) -> str:
    evidence_text = []
    for chunk in chunks:
        evidence_text.append(
            f"[page {chunk['page_number']} | chunk {chunk['chunk_id']} | score {chunk.get('retrieval_score', '')}]\n"
            f"{chunk['text']}"
        )

    evidence_block = "\n\n---\n\n".join(evidence_text)
    aliases = "、".join(field_item.get("aliases", []))
    required_any = "、".join(field_item.get("required_any", []))
    forbidden_any = "、".join(field_item.get("forbidden_any", []))
    unit_examples = "、".join(field_item.get("unit_examples", []))

    output_schema = {
        "matched": True,
        "field_key": field_item["field_key"],
        "value": "123.45",
        "raw_value": "123.45万吨",
        "unit": "万吨",
        "target_unit": "吨",
        "conversion": "万吨转吨，乘以10000；如果无需转换，填无需转换",
        "year": "2024",
        "evidence": "包含该数值的原文短句，不要改写",
        "source_pages": [12],
        "confidence": 0.82,
        "reason": "定位到目标字段同义词，提取到年份和原始数值，并完成单位转换",
    }
    missing_schema = {
        "matched": False,
        "field_key": field_item["field_key"],
        "value": None,
        "raw_value": "",
        "unit": "",
        "target_unit": "",
        "conversion": "",
        "year": "",
        "evidence": "",
        "source_pages": [],
        "confidence": 0.0,
        "reason": "没有找到字段名和数值年份明确对应的证据",
    }

    return f"""
你是 ESG 报告定量指标抽取器。请只根据给定证据 chunk 抽取一个定量字段。

你必须执行三步：
1. 定位：先在证据中定位目标字段、同义词或 required_any 对应的句子/表格行。
2. 提取：从同一语义范围内提取年份、原始数值、原始单位，并把原文短句放入 evidence。
3. 转换：如果原始单位与目标字段常用单位不一致，请换算后把转换后的纯数值填入 value，把原始表达保留在 raw_value，并在 conversion 中说明换算过程。

目标字段：
- field_key: {field_item["field_key"]}
- name_cn: {field_item["name_cn"]}
- category: {field_item["category"]}
- unit_type: {field_item.get("unit_type", "")}
- aliases: {aliases}
- required_any: {required_any}
- forbidden_any: {forbidden_any}
- unit_examples: {unit_examples}

严格规则：
1. matched=true 必须同时满足：证据中有目标字段或同义词、有明确数值、有年份，且语义是一一对应。
2. 如果只是目录、指标索引、披露索引、章节标题，不能 matched=true。
3. 如果证据中出现 forbidden_any，且无法排除是另一个字段，不能 matched=true。
4. value 只填数值本身，不要带单位；raw_value 填原始数值表达；unit 填证据原单位。
5. year 优先取 2024；如果只有其他年份且明确对应，也可以返回对应年份。
6. evidence 必须是证据原文中的短句，且包含字段名/同义词和数值。不要编造。
7. target_unit 填转换后的目标单位；如果无需转换，target_unit 与 unit 相同。
8. 常见换算：千克/公斤 -> 吨 除以1000；万吨 -> 吨 乘以10000；万元 -> 元 乘以10000；亿元 -> 元 乘以100000000；万立方米 -> 立方米 乘以10000。
9. 如果无法可靠换算，保留原单位数值，conversion 说明“未转换：原因”。
10. 如果证据位于表格中，evidence 必须返回完整表格行，并尽量包含表格标题、列头、行名、数值和单位；不要只截取单个数值或子公司名。
11. 如果行首是子公司/部门/地点，但表格标题或列头包含目标指标，请把标题/列头和该完整行一起放入 evidence。
12. 不确定就 matched=false。宁可少填，不要错填。
13. 只返回 JSON，不要 Markdown。

证据 chunks：
{evidence_block}

matched=true 的 JSON 示例：
{json.dumps(output_schema, ensure_ascii=False, indent=2)}

matched=false 的 JSON 示例：
{json.dumps(missing_schema, ensure_ascii=False, indent=2)}
""".strip()


def _default_result(field_item: Dict[str, Any], reason: str) -> Dict[str, Any]:
    return {
        "matched": False,
        "field_key": field_item["field_key"],
        "value": None,
        "raw_value": "",
        "unit": "",
        "year": "",
        "evidence": "",
        "source_pages": [],
        "confidence": 0.0,
        "reason": reason,
    }


def normalize_quant_result(field_item: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    data.setdefault("matched", False)
    data.setdefault("field_key", field_item["field_key"])
    data.setdefault("value", None)
    data.setdefault("raw_value", "")
    data.setdefault("unit", "")
    data.setdefault("target_unit", "")
    data.setdefault("conversion", "")
    data.setdefault("year", "")
    data.setdefault("evidence", "")
    data.setdefault("source_pages", [])
    data.setdefault("confidence", 0.0)
    data.setdefault("reason", "")

    evidence = str(data.get("evidence", "") or "")
    value = data.get("value")
    year = str(data.get("year", "") or "")

    try:
        data["confidence"] = float(data.get("confidence", 0.0) or 0.0)
    except Exception:
        data["confidence"] = 0.0

    if data.get("matched"):
        if value in {None, ""}:
            return _default_result(field_item, "matched_without_value")
        if not YEAR_RE.search(year):
            return _default_result(field_item, "matched_without_year")
        if not NUMBER_RE.search(str(value)) and not NUMBER_RE.search(str(data.get("raw_value", ""))):
            return _default_result(field_item, "matched_value_not_numeric")
        if not NUMBER_RE.search(evidence):
            return _default_result(field_item, "matched_evidence_without_number")

    return data


def extract_quant_indicator_with_llm(
    field_item: Dict[str, Any],
    chunks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if not chunks:
        return _default_result(field_item, "no_relevant_chunks")
    if not model_call_allowed("quantitative_extract"):
        return _default_result(field_item, "model_call_budget_exhausted")

    prompt = build_route_b2_prompt(field_item, chunks)

    started_at = time.time()
    call_recorded = False
    try:
        response = client.chat.completions.create(
            model=TEXT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        record_model_call(
            stage="quantitative_extract",
            model=TEXT_MODEL,
            started_at=started_at,
            response=response,
            metadata={"field_key": field_item["field_key"]},
        )
        call_recorded = True

        content = response.choices[0].message.content
        data = extract_json_from_text(content)

        if not isinstance(data, dict):
            raise ValueError("LLM response is not a JSON object")

        normalized = normalize_quant_result(field_item, data)
        normalized["retrieval_context"] = _retrieval_context(chunks)
        return validate_b2_quant_result(
            field_item,
            normalized,
            min_confidence=ROUTE_B2_MIN_CONFIDENCE,
        )

    except Exception as exc:
        if not call_recorded:
            record_model_call(
                stage="quantitative_extract",
                model=TEXT_MODEL,
                started_at=started_at,
                metadata={"field_key": field_item["field_key"]},
                error=str(exc),
            )
        return _default_result(field_item, f"llm_error:{exc}")
