import json
import re
from typing import Dict, Any, List

from openai import OpenAI

from config.settings import DASHSCOPE_API_KEY, TEXT_MODEL
from config.core_schema import CORE_SCHEMA


client = OpenAI(
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


def build_schema_text() -> str:
    """
    给文本模型看的 Core Schema。
    注意：这里只给核心信息，不给太多解释，减少 token。
    """
    lines = []

    for item in CORE_SCHEMA:
        if item.get("preferred_source") == "main_text_rag":
            continue

        aliases = "、".join(item.get("aliases", []))
        units = "、".join(item.get("unit_examples", []))

        lines.append(
            f"- field_key: {item['field_key']}\n"
            f"  name_cn: {item['name_cn']}\n"
            f"  category: {item['category']}\n"
            f"  value_type: {item['value_type']}\n"
            f"  aliases: {aliases}\n"
            f"  unit_examples: {units}"
        )

    return "\n".join(lines)


def build_prompt(row: Dict[str, Any]) -> str:
    schema_text = build_schema_text()

    return f"""
你是 ESG 指标标准化匹配器。

你的任务：
根据给定的 Core ESG Schema，判断一条 ESG 表格指标行是否能匹配到某个标准 field_key。

重要规则：
1. 只能从 Core ESG Schema 中选择 field_key。
2. 如果指标不属于 Core Schema，必须 matched=false。
3. 不要为了提高匹配率而强行匹配。
4. 经营绩效类指标如营业收入、净利润、资产总额、纳税总额，通常不属于 Core ESG Schema。
5. 党建活动、投资者教育、绿色融资、客户满意度等，如果 Core Schema 没有对应字段，应 matched=false。
6. 如果是“直接温室气体排放量 / 范围一”，应匹配 scope_1_emissions。
7. 如果是“间接温室气体排放量 / 范围二”，应匹配 scope_2_emissions。
8. 如果是“新鲜水用量 / 用水量 / 耗水量”，通常匹配 water_consumption。
9. 如果不确定，matched=false，confidence 不要高于 0.5。

Core ESG Schema:
{schema_text}

待匹配表格行：
{json.dumps(row, ensure_ascii=False, indent=2)}

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

    prompt = build_prompt(row)

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
        result = extract_json(content)

        matched = bool(result.get("matched"))
        field_key = result.get("field_key")
        confidence = float(result.get("confidence", 0))
        reason = result.get("reason", "")

        if not matched:
            return {
                "matched": False,
                "field_key": None,
                "confidence": confidence,
                "reason": f"llm_no_match:{reason}",
            }

        valid_keys = {
            item["field_key"]
            for item in CORE_SCHEMA
            if item.get("preferred_source") != "main_text_rag"
        }

        if field_key not in valid_keys:
            return {
                "matched": False,
                "field_key": None,
                "confidence": confidence,
                "reason": f"llm_invalid_field_key:{field_key}",
            }

        return {
            "matched": True,
            "field_key": field_key,
            "confidence": confidence,
            "reason": f"llm_match:{reason}",
        }

    except Exception as e:
        return {
            "matched": False,
            "field_key": None,
            "confidence": 0.0,
            "reason": f"llm_error:{e}",
        }