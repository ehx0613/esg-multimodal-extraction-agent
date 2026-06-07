from __future__ import annotations

from typing import Any, Dict, List

from config.schema.huazheng_public_mapping import get_mapping_for_field


FIELD_QUERY_EXPANSIONS = {
    "esg_strategy_targets": [
        "ESG目标",
        "ESG战略目标",
        "可持续发展目标",
        "ESG治理目标",
        "制定ESG目标",
        "推进落实ESG目标",
        "ESG领导小组",
        "ESG治理机制",
    ],
    "business_ethics_training": [
        "商业道德培训",
        "商业道德教育",
        "反腐败培训",
        "反贪污培训",
        "反舞弊培训",
        "廉洁培训",
        "合规培训",
        "廉洁从业教育",
    ],
}


def _unique(values: List[str]) -> List[str]:
    return [value for value in dict.fromkeys(str(item).strip() for item in values) if value]


def rewrite_field_queries(
    field_item: Dict[str, Any],
    *,
    industry: str | None = None,
    max_queries: int = 8,
) -> List[str]:
    """Create formal retrieval queries for one ESG field.

    This is a deterministic first version of query rewriting. It expands a
    field-level request with schema aliases and the Huazheng-public framework
    labels, giving BM25 and vector retrieval a richer query surface without
    making an LLM call.
    """

    field_key = str(field_item.get("field_key", ""))
    mapping = get_mapping_for_field(field_key) or {}

    pieces = [
        field_item.get("name_cn", ""),
        *FIELD_QUERY_EXPANSIONS.get(field_key, []),
        *field_item.get("aliases", []),
        *field_item.get("required_any", []),
        mapping.get("indicator_name_cn", ""),
        mapping.get("theme_name_cn", ""),
        field_key.replace("_", " "),
    ]
    if industry:
        pieces.insert(3, industry)

    queries = _unique(pieces)

    if mapping.get("indicator_name_cn") and field_item.get("name_cn"):
        queries.insert(
            0,
            f"{mapping['indicator_name_cn']} {field_item['name_cn']}",
        )

    return _unique(queries)[:max_queries]
