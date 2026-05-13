import csv
import json
import re
from pathlib import Path
from typing import Dict, Any, List

from openai import OpenAI

from config.settings import DASHSCOPE_API_KEY, TEXT_MODEL
from config.core_schema import CORE_SCHEMA


client = OpenAI(
    api_key=DASHSCOPE_API_KEY,
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)


def extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    text = re.sub(r"^```json", "", text, flags=re.IGNORECASE).strip()
    text = re.sub(r"^```", "", text).strip()
    text = re.sub(r"```$", "", text).strip()

    start = text.find("{")
    end = text.rfind("}")

    if start != -1 and end != -1 and end > start:
        text = text[start:end + 1]

    return json.loads(text)


def build_core_schema_brief() -> str:
    lines = []

    for item in CORE_SCHEMA:
        aliases = "、".join(item.get("aliases", []))
        lines.append(
            f"- field_key: {item['field_key']}\n"
            f"  name_cn: {item['name_cn']}\n"
            f"  category: {item['category']}\n"
            f"  indicator_type: {item['indicator_type']}\n"
            f"  value_type: {item['value_type']}\n"
            f"  aliases: {aliases}"
        )

    return "\n".join(lines)


def build_prompt(metric_group: Dict[str, Any]) -> str:
    core_schema_text = build_core_schema_brief()

    return f"""
你是 ESG 指标体系迭代专家。

你的任务：
根据 Core ESG Schema 和 unknown 指标信息，判断该 unknown 指标应该如何处理。

你只能选择以下 action 之一：

1. add_alias_to_existing_core
表示该指标不是新指标，而是已有 Core 指标的另一种表达。
此时必须给出 target_field_key 和建议加入 aliases / required_any 的词。

2. new_core_candidate
表示该指标具有跨行业通用性，且适合新增为 Core ESG 指标。
此时需要给出 suggested_field_key、name_cn、category、value_type、reason。

3. industry_schema_candidate
表示该指标更适合行业指标，不建议进入通用 Core。
例如金融行业绿色融资、电力行业发电量、新能源行业电池回收等。

4. keep_unknown
表示该指标属于公司特色指标、经营财务指标，或暂时不适合进入标准体系。

判断原则：
- 不要为了提高覆盖率强行加入 Core。
- 经营绩效/财务指标，如营业收入、净利润、资产总额、纳税总额，一般 keep_unknown。
- 高频、跨行业、可量化、ESG 相关性强的指标，才考虑 new_core_candidate。
- 如果只是已有 Core 的同义表达，优先 add_alias_to_existing_core。
- 行业特色指标不要放进通用 Core，应该 industry_schema_candidate。

Core ESG Schema:
{core_schema_text}

待分析 unknown 指标：
{json.dumps(metric_group, ensure_ascii=False, indent=2)}

请输出严格 JSON，不要输出 Markdown。

输出格式：

{{
  "action": "add_alias_to_existing_core",
  "target_field_key": "water_consumption",
  "suggested_aliases": ["新鲜水用量"],
  "suggested_required_any": ["新鲜水用量"],
  "confidence": 0.91,
  "reason": "新鲜水用量是水资源消耗量的常见表述，单位为万吨，适合映射到 water_consumption。"
}}

如果建议新增 Core：

{{
  "action": "new_core_candidate",
  "target_field_key": null,
  "suggested_field_key": "customer_satisfaction_rate",
  "name_cn": "客户满意度",
  "category": "S",
  "value_type": "percentage",
  "confidence": 0.82,
  "reason": "客户满意度在多家公司披露，具有一定跨行业通用性。"
}}

如果建议保留 unknown：

{{
  "action": "keep_unknown",
  "target_field_key": null,
  "confidence": 0.76,
  "reason": "该指标属于经营绩效或公司特色指标，不适合进入通用 Core ESG Schema。"
}}
""".strip()


def analyze_unknown_metric_group(metric_group: Dict[str, Any]) -> Dict[str, Any]:
    prompt = build_prompt(metric_group)

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

        return result

    except Exception as e:
        return {
            "action": "error",
            "target_field_key": None,
            "confidence": 0.0,
            "reason": f"llm_error:{e}",
        }