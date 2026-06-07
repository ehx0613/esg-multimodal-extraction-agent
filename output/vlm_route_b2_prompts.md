# VLMTableOCRAgent and Route B2 Prompt Text

- Generated at: 2026-05-22T18:52:22
- Scope: current code used by VLMTableOCRAgent table OCR and Route B2 quantitative text extraction.
- Note: prompt builders are f-strings; runtime values such as image_name, field_item, and retrieved chunks are injected when the pipeline runs.

## VLMTableOCRAgent prompt flow

- Agent file: `agents/vlm_table_ocr_agent.py`
- VLM call file: `utils/vlm_client.py`
- Normal prompt builder: `build_all_table_rows_prompt(image_name)`
- Retry prompt builder: `build_forced_table_prompt(image_name)`

## build_all_table_rows_prompt

Source: `config/prompts.py`

```python
def build_all_table_rows_prompt(image_name: str) -> str:
    return f"""
你是 ESG 报告附录表格 OCR 抽取器。

你的任务只有一个：
把图片中所有 ESG 绩效数据表格逐行抄成结构化 JSON。

不要做指标标准化。
不要判断是否属于 Core Schema。
不要补充图片中没有的数据。
不要因为指标陌生就跳过。

当前图片文件名：{image_name}

【必须判定为 performance_data_table 的页面】

只要页面中出现以下任意形式，并且包含具体数值，就必须判定为 performance_data_table：

- 关键绩效表
- 关键绩效指标表
- 量化数据绩效表
- ESG 数据表
- ESG 数据一览表
- 环境绩效
- 社会绩效
- 治理绩效
- 经济绩效
- 环境维度
- 社会维度
- 治理维度
- 经济维度
- 指标 / 单位 / 年份
- 指标 / 单位 / 2024年
- 类别 / 指标 / 单位 / 2024年
- 议题 / 指标 / 单位 / 2024年

【page_type 只能是】

1. performance_data_table
页面包含具体 ESG 绩效数值表。比如环境绩效、社会绩效、治理绩效、量化数据绩效表、ESG 数据表。

2. content_index
页面只是指标索引、GRI索引、披露项索引、报告页码索引，不包含实际绩效数值。

3. other
其他页面。

【表格抽取规则】

1. 如果表格列为：
   类别 / 指标 / 单位 / 2024年
   则：
   - 类别 = topic
   - 指标 = metric_name
   - 单位 = unit
   - 2024年 = values["2024年"]

2. 如果表格列为：
   指标 / 单位 / 2024年
   则：
   - metric_name = 指标
   - unit = 单位
   - values["2024年"] = 数值
   - 如果左侧有大类，如“环境绩效 / 社会绩效 / 治理绩效”，则填入 topic

3. 如果一张图片里有左右两页、多个表格、多个板块，必须全部抽取。
   不要只抽左半页，也不要只抽右半页。

4. 如果同一页有：
   环境绩效、社会绩效、治理绩效、经济绩效
   应该作为多个 table 或多个 topic 全部抽取。

5. 合并单元格要继承上方最近的 topic。
   例如左侧“员工”跨多行，则下面所有员工指标 topic 都是“员工”。

6. 如果某行数值是：
   “/”、“—”、“-”、“N/A”、“不适用”
   必须保留原文，不要改成 0。

7. raw value 必须逐字照抄：
   - 保留逗号
   - 保留小数
   - 保留百分号对应的单位
   - 不要把 16,852,249 改成 16852249
   - 不要把 100,051.00 改成 100051

8. 不要遗漏经营绩效、环境绩效、社会绩效、治理绩效中的行。
   即使某些指标不是 ESG Core，也要抽出来，后续会进入 unknown_metrics。

9. 如果页面中确实没有表格，才可以输出 page_type=other。

【必须输出严格 JSON】
不要输出 Markdown。
不要输出解释。
不要输出 ```json。

输出格式：

{{
  "page_image": "{image_name}",
  "page_type": "performance_data_table",
  "page_note": null,
  "tables": [
    {{
      "table_title": "量化数据绩效表-环境绩效",
      "columns": ["类别", "指标", "单位", "2024年"],
      "rows": [
        {{
          "topic": "能源总量情况",
          "metric_name": "综合能源消耗总量",
          "unit": "吨标煤",
          "values": {{
            "2024年": "100,051.00"
          }},
          "evidence_text": "能源总量情况 综合能源消耗总量 吨标煤 2024年 100,051.00"
        }},
        {{
          "topic": "员工",
          "metric_name": "员工总数",
          "unit": "人",
          "values": {{
            "2024年": "11,000"
          }},
          "evidence_text": "员工 员工总数 人 2024年 11,000"
        }}
      ]
    }}
  ]
}}

如果页面不是绩效数据表，输出：

{{
  "page_image": "{image_name}",
  "page_type": "other",
  "page_note": "说明原因",
  "tables": []
}}
""".strip()
```

## build_forced_table_prompt

Source: `config/prompts.py`

```python
def build_forced_table_prompt(image_name: str) -> str:
    return f"""
你刚才可能漏识别了表格。现在请重新检查图片。

当前图片文件名：{image_name}

这张图片很可能是 ESG 报告的“量化数据绩效表 / ESG 数据表 / 关键绩效表”。

请强制执行表格 OCR：

1. 只要看见“指标、单位、2024年”三类列，就必须抽取。
2. 只要看见“环境绩效、社会绩效、治理绩效、经济绩效”，就必须作为 ESG 绩效表抽取。
3. 只要看见“量化数据绩效表”，必须判定为 performance_data_table。
4. 即使页面是左右双页展开，也要把左右两边所有表格都抽取。
5. 不要因为没有“关键绩效表”四个字就判断为 other。
6. 不要做指标分类或标准化，只抄表格原文。
7. 输出严格 JSON，不要 Markdown，不要解释。

返回格式：

{{
  "page_image": "{image_name}",
  "page_type": "performance_data_table",
  "page_note": null,
  "tables": [
    {{
      "table_title": "量化数据绩效表",
      "columns": ["类别", "指标", "单位", "2024年"],
      "rows": [
        {{
          "topic": "环境绩效",
          "metric_name": "综合能源消耗总量",
          "unit": "吨标煤",
          "values": {{"2024年": "100,051.00"}},
          "evidence_text": "环境绩效 综合能源消耗总量 吨标煤 2024年 100,051.00"
        }}
      ]
    }}
  ]
}}

如果确实完全没有表格，才输出：

{{
  "page_image": "{image_name}",
  "page_type": "other",
  "page_note": "没有发现可抽取的 ESG 绩效数据表",
  "tables": []
}}
""".strip()
```

## Route B2 prompt flow

- Pipeline file: `pipeline/quant_text_pipeline.py`
- LLM extractor file: `utils/llm_quant_extractor.py`
- Prompt builder: `build_route_b2_prompt(field_item, chunks)`

## build_route_b2_prompt

Source: `utils/llm_quant_extractor.py`

```python
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
        "year": "2024",
        "evidence": "包含该数值的原文短句，不要改写",
        "source_pages": [12],
        "confidence": 0.82,
        "reason": "证据中字段名、年份、数值和单位明确对应",
    }
    missing_schema = {
        "matched": False,
        "field_key": field_item["field_key"],
        "value": None,
        "raw_value": "",
        "unit": "",
        "year": "",
        "evidence": "",
        "source_pages": [],
        "confidence": 0.0,
        "reason": "没有找到字段名和数值年份明确对应的证据",
    }

    return f"""
你是 ESG 报告定量指标抽取器。请只根据给定证据 chunk 抽取一个定量字段。

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
4. value 只填数值本身，不要带单位；raw_value 填原始数值表达；unit 尽量用证据原单位。
5. year 优先取 2024；如果只有其他年份且明确对应，也可以返回对应年份。
6. evidence 必须是证据原文中的短句，且包含字段名/同义词和数值。不要编造。
7. 不确定就 matched=false。宁可少填，不要错填。
8. 只返回 JSON，不要 Markdown。

证据 chunks：
{evidence_block}

matched=true 的 JSON 示例：
{json.dumps(output_schema, ensure_ascii=False, indent=2)}

matched=false 的 JSON 示例：
{json.dumps(missing_schema, ensure_ascii=False, indent=2)}
""".strip()
```
