from typing import Any, Dict, List


SchemaItem = Dict[str, Any]
SchemaList = List[SchemaItem]


def filter_by_category(schema: SchemaList, category: str) -> SchemaList:
    return [item for item in schema if item.get("category") == category]


def filter_by_preferred_source(schema: SchemaList, preferred_source: str) -> SchemaList:
    return [item for item in schema if item.get("preferred_source") == preferred_source]
