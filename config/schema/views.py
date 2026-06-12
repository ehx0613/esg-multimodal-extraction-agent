from typing import Any, Dict, List

from .all_data import ALL_SCHEMA_DATA
from .e_data import E_SCHEMA_DATA
from .shared import filter_by_category, filter_by_preferred_source
from .route_a_atoms import enrich_route_a_item


ALL_SCHEMA = [enrich_route_a_item(item) for item in ALL_SCHEMA_DATA]
CORE_SCHEMA_VERSION = "core_esg_v4.1_60"
CORE_SCHEMA_FIELD_COUNT = len(ALL_SCHEMA)

E_SCHEMA = filter_by_category(ALL_SCHEMA, "E")
S_SCHEMA = filter_by_category(ALL_SCHEMA, "S")
G_SCHEMA = filter_by_category(ALL_SCHEMA, "G")

ROUTE_A_SCHEMA = [
    item for item in ALL_SCHEMA
    if item.get("preferred_source") != "main_text_rag"
]
APPENDIX_TABLE_SCHEMA = ROUTE_A_SCHEMA
ROUTE_B_SCHEMA = filter_by_preferred_source(ALL_SCHEMA, "main_text_rag")

ESG_SCHEMA = {item["field_key"]: item for item in ALL_SCHEMA}

ESG_FIELD_KEYS = [item["field_key"] for item in ALL_SCHEMA]
ROUTE_A_FIELD_KEYS = [item["field_key"] for item in ROUTE_A_SCHEMA]
ROUTE_B_FIELD_KEYS = [item["field_key"] for item in ROUTE_B_SCHEMA]
E_FIELD_KEYS = [item["field_key"] for item in E_SCHEMA]
S_FIELD_KEYS = [item["field_key"] for item in S_SCHEMA]
G_FIELD_KEYS = [item["field_key"] for item in G_SCHEMA]

NUMERIC_FIELD_KEYS = [
    item["field_key"]
    for item in ALL_SCHEMA
    if item.get("indicator_type") == "quantitative"
]
TEXT_FIELD_KEYS = [
    item["field_key"]
    for item in ALL_SCHEMA
    if item.get("indicator_type") == "qualitative"
]


def get_schema_item(field_key: str) -> Dict[str, Any]:
    return ESG_SCHEMA.get(field_key, {})


def get_aliases(field_key: str) -> List[str]:
    return get_schema_item(field_key).get("aliases", [])


def get_unit_examples(field_key: str) -> List[str]:
    return get_schema_item(field_key).get("unit_examples", [])


def schema_summary() -> Dict[str, int]:
    return {
        "total": len(ALL_SCHEMA),
        "route_a": len(ROUTE_A_SCHEMA),
        "route_b": len(ROUTE_B_SCHEMA),
        "quantitative": len(NUMERIC_FIELD_KEYS),
        "qualitative": len(TEXT_FIELD_KEYS),
        "E": len(E_SCHEMA),
        "S": len(S_SCHEMA),
        "G": len(G_SCHEMA),
    }
