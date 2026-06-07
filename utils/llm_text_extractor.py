import json
import time
from typing import Any, Dict, List

from openai import OpenAI

from config.settings import DASHSCOPE_API_KEY, TEXT_MODEL
from utils.b_text_result_validator import validate_route_b_text_result
from utils.json_utils import extract_json_from_text
from utils.call_tracker import model_call_allowed, record_model_call


client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)


def build_route_b_prompt(field_item: Dict[str, Any], chunks: List[Dict[str, Any]]) -> str:
    evidence_text = []
    for chunk in chunks:
        evidence_text.append(
            f"[page {chunk['page_number']} | chunk {chunk['chunk_id']}]\n"
            f"{chunk['text']}"
        )

    evidence_block = "\n\n---\n\n".join(evidence_text)
    aliases = "、".join(field_item.get("aliases", []))

    output_schema = {
        "matched": True,
        "field_key": field_item["field_key"],
        "value": True,
        "summary": "用一句话概括该指标对应的机制、政策或措施。",
        "evidence": "保留报告中的原文证据片段，语义完整，不要编造。",
        "source_pages": [12],
        "confidence": 0.86,
        "reason": "说明为什么该证据能或不能支持该指标。",
    }

    missing_schema = {
        "matched": False,
        "field_key": field_item["field_key"],
        "value": None,
        "summary": "",
        "evidence": "",
        "source_pages": [],
        "confidence": 0.0,
        "reason": "候选文本未明确提及该指标。",
    }

    return f"""
你是 ESG 报告定性指标抽取助手。请只根据候选文本判断目标指标是否被报告明确提及。

目标指标：
- field_key: {field_item["field_key"]}
- name_cn: {field_item["name_cn"]}
- category: {field_item["category"]}
- aliases: {aliases}

抽取规则：
1. 只有候选文本明确描述该机制、政策、目标或措施时，matched 才能为 true。
2. evidence 必须逐字复制候选文本中的一至两个关键原文片段；不要改写、概括或拼接成长篇摘要。
3. 不要使用常识补全，不要编造报告没有写出的内容。
4. source_pages 只能来自候选文本前的 page 标记。
5. 不得因为委员会名称、章节标题或一般性表述而合理推断存在目标机制。
6. 只返回 JSON，不要返回 Markdown 或额外解释。

候选文本：
{evidence_block}

如果匹配，返回类似：
{json.dumps(output_schema, ensure_ascii=False, indent=2)}

如果不匹配，返回类似：
{json.dumps(missing_schema, ensure_ascii=False, indent=2)}
""".strip()


def extract_text_indicator_with_llm(
    field_item: Dict[str, Any],
    chunks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if not chunks:
        return {
            "matched": False,
            "field_key": field_item["field_key"],
            "value": None,
            "summary": "",
            "evidence": "",
            "source_pages": [],
            "confidence": 0.0,
            "reason": "no_relevant_chunks",
        }
    if not model_call_allowed("qualitative_extract"):
        return {
            "matched": False,
            "field_key": field_item["field_key"],
            "value": None,
            "summary": "",
            "evidence": "",
            "source_pages": [],
            "confidence": 0.0,
            "reason": "model_call_budget_exhausted",
        }

    prompt = build_route_b_prompt(field_item, chunks)

    started_at = time.time()
    call_recorded = False
    try:
        response = client.chat.completions.create(
            model=TEXT_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        record_model_call(
            stage="qualitative_extract",
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

        return validate_route_b_text_result(field_item, data, chunks)

    except Exception as exc:
        if not call_recorded:
            record_model_call(
                stage="qualitative_extract",
                model=TEXT_MODEL,
                started_at=started_at,
                metadata={"field_key": field_item["field_key"]},
                error=str(exc),
            )
        return {
            "matched": False,
            "field_key": field_item["field_key"],
            "value": None,
            "summary": "",
            "evidence": "",
            "source_pages": [],
            "confidence": 0.0,
            "reason": f"llm_error:{exc}",
        }
