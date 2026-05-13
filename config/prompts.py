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