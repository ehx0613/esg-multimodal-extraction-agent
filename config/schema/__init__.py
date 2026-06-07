"""
Schema package layout

- `*_data.py`: category-level data entrypoints
- `views.py`: route/category projections consumed by pipelines
- `e.py` / `s.py` / `g.py` / `route_a.py` / `route_b.py`: narrow public imports

The canonical field definitions still live in `config.core_schema`.
This package is the migration layer that lets the rest of the project
stop depending on one oversized schema module directly.
"""

from .views import (
    ALL_SCHEMA,
    APPENDIX_TABLE_SCHEMA,
    E_FIELD_KEYS,
    E_SCHEMA,
    ESG_FIELD_KEYS,
    ESG_SCHEMA,
    G_FIELD_KEYS,
    G_SCHEMA,
    NUMERIC_FIELD_KEYS,
    ROUTE_A_FIELD_KEYS,
    ROUTE_A_SCHEMA,
    ROUTE_B_FIELD_KEYS,
    ROUTE_B_SCHEMA,
    S_FIELD_KEYS,
    S_SCHEMA,
    TEXT_FIELD_KEYS,
    get_aliases,
    get_schema_item,
    get_unit_examples,
    schema_summary,
)
from .industry import (
    FINANCE_FIELD_KEYS,
    FINANCE_SCHEMA,
    INDUSTRY_FIELD_KEYS_MAP,
    INDUSTRY_SCHEMA_MAP,
    MANUFACTURING_FIELD_KEYS,
    MANUFACTURING_SCHEMA,
    PHARMA_FIELD_KEYS,
    PHARMA_SCHEMA,
)
from .huazheng_public_mapping import (
    FIELD_FRAMEWORK_MAP,
    FIELD_FRAMEWORK_MAPPINGS,
    HUAZHENG_PUBLIC_FRAMEWORK,
    KEY_INDICATOR_INDEX,
    RATING_BANDS,
    SCHEMA_VERSION,
    framework_summary,
    get_applicable_field_keys,
    get_mapping_for_field,
)

__all__ = [
    "ALL_SCHEMA",
    "APPENDIX_TABLE_SCHEMA",
    "E_FIELD_KEYS",
    "E_SCHEMA",
    "ESG_FIELD_KEYS",
    "ESG_SCHEMA",
    "G_FIELD_KEYS",
    "G_SCHEMA",
    "FIELD_FRAMEWORK_MAP",
    "FIELD_FRAMEWORK_MAPPINGS",
    "FINANCE_FIELD_KEYS",
    "FINANCE_SCHEMA",
    "HUAZHENG_PUBLIC_FRAMEWORK",
    "INDUSTRY_FIELD_KEYS_MAP",
    "INDUSTRY_SCHEMA_MAP",
    "KEY_INDICATOR_INDEX",
    "MANUFACTURING_FIELD_KEYS",
    "MANUFACTURING_SCHEMA",
    "NUMERIC_FIELD_KEYS",
    "PHARMA_FIELD_KEYS",
    "PHARMA_SCHEMA",
    "RATING_BANDS",
    "ROUTE_A_FIELD_KEYS",
    "ROUTE_A_SCHEMA",
    "ROUTE_B_FIELD_KEYS",
    "ROUTE_B_SCHEMA",
    "SCHEMA_VERSION",
    "S_FIELD_KEYS",
    "S_SCHEMA",
    "TEXT_FIELD_KEYS",
    "framework_summary",
    "get_aliases",
    "get_applicable_field_keys",
    "get_mapping_for_field",
    "get_schema_item",
    "get_unit_examples",
    "schema_summary",
]
