# -*- coding: utf-8 -*-
# config/core_schema.py
"""
Core ESG Schema v4.1

设计目标：
1. 构建跨行业通用 ESG 核心指标体系；
2. 用于 all_table_rows -> standard_esg_results 的标准化匹配；
3. 无法映射到本 Schema 的指标进入 unknown_metrics；
4. 本版根据批量评估和误差分析做了小步更新：
   - 补充已有 Core 字段别名；
   - 新增 anti_corruption_training_hours；
   - 新增 patent_applications_new；
   - 没有把经营绩效、行业特色、单一公司特色指标纳入 Core。

兼容性说明：
- 本模块保留旧的 `config.core_schema` 导入入口；
- 字段定义和分类视图的真实来源已经迁移到 `config.schema.*`；
- 新代码优先从 `config.schema` 导入。
"""

from typing import Any, Dict, List

from config.schema.all_data import ALL_SCHEMA_DATA
from config.schema.views import (
    ESG_FIELD_KEYS,
    ESG_SCHEMA,
    NUMERIC_FIELD_KEYS,
    TEXT_FIELD_KEYS,
    get_aliases,
    get_schema_item,
    get_unit_examples,
    schema_summary,
)


CORE_SCHEMA = list(ALL_SCHEMA_DATA)

SCHEMA_ITEMS = [
    (
        item["field_key"],
        item["name_cn"] + " / " + " / ".join(item.get("aliases", [])),
        item["category"],
        item["value_type"],
        item["preferred_source"],
        item["unit_required"],
        item["year_required"],
    )
    for item in CORE_SCHEMA
]


def get_core_schema_prompt_text() -> str:
    """
    给 qwen-plus 做指标匹配 / unknown 指标分析时使用。
    """
    lines = []

    for item in CORE_SCHEMA:
        aliases = "、".join(item.get("aliases", []))
        units = "、".join(item.get("unit_examples", []))
        required_any = "、".join(item.get("required_any", []))
        forbidden_any = "、".join(item.get("forbidden_any", []))

        line = (
            f"- field_key: {item['field_key']}\n"
            f"  name_cn: {item['name_cn']}\n"
            f"  category: {item['category']}\n"
            f"  indicator_type: {item['indicator_type']}\n"
            f"  value_type: {item['value_type']}\n"
            f"  unit_type: {item.get('unit_type', '')}\n"
            f"  aliases: {aliases}\n"
            f"  unit_examples: {units}\n"
            f"  required_any: {required_any}\n"
            f"  forbidden_any: {forbidden_any}"
        )
        lines.append(line)

    return "\n".join(lines)


__all__ = [
    "CORE_SCHEMA",
    "ESG_SCHEMA",
    "ESG_FIELD_KEYS",
    "NUMERIC_FIELD_KEYS",
    "TEXT_FIELD_KEYS",
    "SCHEMA_ITEMS",
    "get_aliases",
    "get_schema_item",
    "get_unit_examples",
    "get_core_schema_prompt_text",
    "schema_summary",
]


if __name__ == "__main__":
    summary = schema_summary()
    print(f"Core ESG Schema 指标数量: {summary['total']}")
    print(f"定量指标数量: {summary['quantitative']}")
    print(f"定性指标数量: {summary['qualitative']}")
    print(f"E 指标数量: {summary['E']}")
    print(f"S 指标数量: {summary['S']}")
    print(f"G 指标数量: {summary['G']}")
