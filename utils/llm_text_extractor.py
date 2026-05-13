import json
import re
from typing import Dict, Any, List

from openai import OpenAI

from config.settings import DASHSCOPE_API_KEY, TEXT_MODEL
from utils.json_utils import extract_json_from_text


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

    return f"""
你是 ESG 报告正文信息抽取器。

任务：
根据给定正文片段，判断企业是否披露了指定 ESG 机制或政策。

只判断当前字段，不要抽取其他字段。

字段信息：
field_key: {field_item["field_key"]}
name_cn: {field_item["name_cn"]}
category: {field_item["category"]}
aliases: {aliases}

判断规则：
1. 如果正文明确说明存在该机制/政策/委员会/流程，matched=true。
2. 如果只是目录、标题、口号、无实际机制说明，matched=false。
3. 如果证据不足，matched=false。
4. evidence 必须来自给定正文片段，不要编造。
5. source_pages 填证据所在页码。
6. 输出严格 JSON，不要 Markdown。

正文片段：
{evidence_block}

输出格式：
{{
  "matched": true,
  "field_key": "{field_item["field_key"]}",
  "value": true,
  "summary": "公司建立了反腐败或举报相关制度。",
  "evidence": "原文中的关键证据，不超过80字",
  "source_pages": [12, 13],
  "confidence": 0.86,
  "reason": "正文明确披露了该机制。"
}}

如果没有找到：
{{
  "matched": false,
  "field_key": "{field_item["field_key"]}",
  "value": null,
  "summary": "",
  "evidence": "",
  "source_pages": [],
  "confidence": 0.25,
  "reason": "未找到足够证据。"
}}
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

    prompt = build_route_b_prompt(field_item, chunks)

    try:
        response = client.chat.completions.create(
            model=TEXT_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=0,
        )

        content = response.choices[0].message.content
        data = extract_json_from_text(content)

        if not isinstance(data, dict):
            raise ValueError("LLM 返回不是 JSON dict")

        data.setdefault("matched", False)
        data.setdefault("field_key", field_item["field_key"])
        data.setdefault("value", None)
        data.setdefault("summary", "")
        data.setdefault("evidence", "")
        data.setdefault("source_pages", [])
        data.setdefault("confidence", 0.0)
        data.setdefault("reason", "")

        return data

    except Exception as e:
        return {
            "matched": False,
            "field_key": field_item["field_key"],
            "value": None,
            "summary": "",
            "evidence": "",
            "source_pages": [],
            "confidence": 0.0,
            "reason": f"llm_error:{e}",
        }