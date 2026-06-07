from typing import Any, Dict, Iterable, List


def build_metric_plan(item: Dict[str, Any]) -> Dict[str, Any]:
    """Build a deterministic, schema-driven multimodal retrieval plan."""
    indicator_type = str(item.get("indicator_type") or "")
    preferred_source = str(item.get("preferred_source") or "")
    quantitative = indicator_type == "quantitative"

    preferred_evidence = ["body_text"]
    required_modalities = ["text"]
    verification_policy = "single_modal"
    visual_fallback_required = False

    if quantitative:
        preferred_evidence = [
            "parsed_table",
            "visual_proxy",
            "body_text",
            "image_table",
        ]
        required_modalities = ["text", "visual"]
        verification_policy = "cross_modal_when_available"
        visual_fallback_required = True
    elif preferred_source != "main_text_rag":
        preferred_evidence = ["parsed_table", "body_text", "visual_proxy"]
        visual_fallback_required = True

    return {
        "field_key": item["field_key"],
        "field_name_cn": item.get("name_cn", ""),
        "category": item.get("category", ""),
        "indicator_type": indicator_type,
        "value_type": item.get("value_type", ""),
        "preferred_evidence": preferred_evidence,
        "required_modalities": required_modalities,
        "expected_terms": list(item.get("aliases", [])),
        "expected_units": list(item.get("unit_examples", [])),
        "year_required": bool(item.get("year_required")),
        "verification_policy": verification_policy,
        "visual_fallback_required": visual_fallback_required,
    }


def build_metric_plans(schema: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [build_metric_plan(item) for item in schema]
