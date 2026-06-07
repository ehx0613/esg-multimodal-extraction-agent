from typing import Any, Dict, List


def q_field(
    field_key: str,
    name_cn: str,
    category: str,
    value_type: str,
    unit_type: str,
    aliases: List[str],
    required_any: List[str] | None = None,
    forbidden_any: List[str] | None = None,
    unit_examples: List[str] | None = None,
    preferred_source: str = "appendix_table",
    unit_required: bool = True,
    year_required: bool = True,
) -> Dict[str, Any]:
    return {
        "field_key": field_key,
        "name_cn": name_cn,
        "category": category,
        "indicator_type": "quantitative",
        "value_type": value_type,
        "preferred_source": preferred_source,
        "unit_required": unit_required,
        "year_required": year_required,
        "unit_type": unit_type,
        "unit_examples": unit_examples or [],
        "aliases": aliases,
        "required_any": required_any if required_any is not None else aliases,
        "forbidden_any": forbidden_any or [],
    }


__all__ = ["q_field"]
