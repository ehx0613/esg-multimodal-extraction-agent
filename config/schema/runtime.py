from typing import Any, Dict, List

from config.industry_applicability import get_applicability

from .industry import INDUSTRY_SCHEMA_MAP
from .views import ALL_SCHEMA


def build_runtime_schema(industry: str = "general") -> List[Dict[str, Any]]:
    """Combine frozen core fields with industry extensions and applicability labels."""
    runtime: List[Dict[str, Any]] = []
    seen = set()
    for item in ALL_SCHEMA:
        field_key = item["field_key"]
        runtime.append({
            **item,
            "schema_layer": "core",
            "applicability": get_applicability(industry, field_key),
        })
        seen.add(field_key)
    for item in INDUSTRY_SCHEMA_MAP.get(industry, []):
        if item["field_key"] in seen:
            continue
        runtime.append({
            **item,
            "schema_layer": "industry_extension",
            "applicability": "optional",
            "industry": industry,
        })
    return runtime


__all__ = ["build_runtime_schema"]
