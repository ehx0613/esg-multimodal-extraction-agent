from agents.base_agent import BaseAgent
from config.schema import ESG_FIELD_KEYS, ESG_SCHEMA
from utils.schema_matcher import match_row_to_schema, is_index_row
from utils.text_utils import choose_latest_year_value, parse_number
from utils.json_utils import save_json
from utils.schema_match_cache import SchemaMatchCache, row_hash


def standard_item(
    row,
    page_image,
    table_title,
    match,
    *,
    source_type="appendix_table",
    source_page=None,
    source_region_id="",
    bbox=None,
):
    year, col, raw = choose_latest_year_value(row.get("values", {}))
    return {"field_key": match["field_key"], "value": parse_number(raw), "raw_value": raw, "unit": row.get("unit"), "year": year, "row_label": row.get("metric_name"), "topic": row.get("topic"), "table_title": table_title, "page_image": page_image, "evidence_text": row.get("evidence_text"), "status": "extracted", "confidence": match["confidence"], "match_reason": match["reason"], "source_type": source_type, "source_page": source_page, "source_region_id": source_region_id, "bbox": bbox}


def item_priority(item):
    text = " ".join(
        str(item.get(key) or "")
        for key in ["row_label", "topic", "table_title", "evidence_text"]
    )
    score = float(item.get("confidence") or 0.0)

    if any(word in text for word in ["新进员工", "新入职", "离职员工", "流失员工"]):
        score -= 0.08

    if any(word in text for word in ["帮扶困难员工", "困难员工帮扶", "慰问困难员工"]):
        score -= 0.25

    if any(word in text for word in ["员工组成情况", "员工构成", "员工结构", "员工总数", "员工总人数", "在职员工"]):
        score += 0.04

    if any(word in text for word in ["按性别划分", "女性员工比例", "女性员工占比"]):
        score += 0.02

    if "总用水量" in text:
        score += 0.08

    if any(word in text for word in ["新鲜水取水总量", "取水总量", "新鲜水用量"]):
        score -= 0.03

    return score


class SchemaMatchAgent(BaseAgent):
    def __init__(self):
        super().__init__("SchemaMatchAgent")
    def run(self, state):
        standard = {}
        unknown = []
        raw_table_metrics = []
        metric_candidates = []
        validated_metrics = []
        raw_rows = 0
        cache = SchemaMatchCache(state["output_dir"] / "schema_match_cache.json")
        cache_hits = 0
        cache_misses = 0
        allow_llm = bool(state.get("schema_match_allow_llm", True))
        for page in state.get("all_table_rows", []):
            if page.get("page_type") != "performance_data_table":
                continue
            for table in page.get("tables", []):
                title = table.get("table_title")
                for row in table.get("rows", []):
                    raw_rows += 1
                    raw_metric = {
                        "raw_metric_id": f"raw_metric_{raw_rows:05d}",
                        "page_image": page.get("page_image"),
                        "page_number": page.get("page_number"),
                        "source_type": page.get("source_type") or "appendix_table",
                        "source_region_id": page.get("source_region_id") or "",
                        "table_title": title,
                        "topic": row.get("topic"),
                        "metric_name": row.get("metric_name"),
                        "unit": row.get("unit"),
                        "values": row.get("values"),
                        "evidence_text": row.get("evidence_text"),
                        "is_index_row": is_index_row(title, row),
                    }
                    raw_table_metrics.append(raw_metric)
                    if raw_metric["is_index_row"]:
                        continue
                    mapping_row = {**row, "table_title": title}
                    key = row_hash(mapping_row)
                    match = cache.get(key)
                    if match is None:
                        match = match_row_to_schema(mapping_row, allow_llm=allow_llm)
                        if match.get("reason") != "model_call_budget_exhausted":
                            cache.put(key, match)
                        cache_misses += 1
                    else:
                        cache_hits += 1
                    candidate = {
                        **raw_metric,
                        "matched": bool(match.get("matched")),
                        "field_key": match.get("field_key"),
                        "confidence": match.get("confidence", 0.0),
                        "match_reason": match.get("reason", ""),
                    }
                    metric_candidates.append(candidate)
                    if match["matched"]:
                        item = standard_item(
                            row,
                            page.get("page_image"),
                            title,
                            match,
                            source_type=page.get("source_type") or "appendix_table",
                            source_page=page.get("page_number"),
                            source_region_id=page.get("source_region_id") or "",
                            bbox=page.get("bbox"),
                        )
                        old = standard.get(match["field_key"])
                        if old is None or item_priority(item) > item_priority(old):
                            standard[match["field_key"]] = item
                        validated_metrics.append({**candidate, "validation_status": "accepted"})
                    else:
                        unknown.append({"page_image": page.get("page_image"), "table_title": title, "topic": row.get("topic"), "metric_name": row.get("metric_name"), "unit": row.get("unit"), "values": row.get("values"), "evidence_text": row.get("evidence_text"), "reason": match["reason"]})
        final = {}
        for f in ESG_FIELD_KEYS:
            final[f] = standard.get(f) or {"field_key": f, "value": None, "status": "missing", "confidence": 0.0, "name_cn": ESG_SCHEMA[f]["name_cn"], "category": ESG_SCHEMA[f]["category"], "indicator_type": ESG_SCHEMA[f]["indicator_type"]}
        state["raw_row_count"] = raw_rows
        state["raw_table_metrics"] = raw_table_metrics
        state["metric_candidates"] = metric_candidates
        state["validated_metrics"] = validated_metrics
        state["standard_results"] = final
        state["unknown_metrics"] = unknown
        state["extracted_fields"] = [k for k, v in final.items() if v.get("status") == "extracted"]
        state["missing_fields"] = [k for k, v in final.items() if v.get("status") != "extracted"]
        state["schema_match_cache"] = {
            "hits": cache_hits,
            "misses": cache_misses,
            "entries": len(cache.entries),
        }
        cache.save()
        save_json(final, state["output_dir"] / "standard_esg_results.json")
        save_json(unknown, state["output_dir"] / "unknown_metrics.json")
        save_json(raw_table_metrics, state["output_dir"] / "raw_table_metrics.json")
        save_json(metric_candidates, state["output_dir"] / "metric_candidates.json")
        save_json(validated_metrics, state["output_dir"] / "validated_metrics.json")
        self.log(f"raw_rows={raw_rows}, extracted={len(state['extracted_fields'])}, unknown={len(unknown)}")
        return state
