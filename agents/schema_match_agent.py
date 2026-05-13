from agents.base_agent import BaseAgent
from config.core_schema import ESG_FIELD_KEYS, ESG_SCHEMA
from utils.schema_matcher import match_row_to_schema, is_index_row
from utils.text_utils import choose_latest_year_value, parse_number
from utils.json_utils import save_json


def standard_item(row, page_image, table_title, match):
    year, col, raw = choose_latest_year_value(row.get("values", {}))
    return {"field_key": match["field_key"], "value": parse_number(raw), "raw_value": raw, "unit": row.get("unit"), "year": year, "row_label": row.get("metric_name"), "topic": row.get("topic"), "table_title": table_title, "page_image": page_image, "evidence_text": row.get("evidence_text"), "status": "extracted", "confidence": match["confidence"], "match_reason": match["reason"], "source_type": "appendix_table"}

class SchemaMatchAgent(BaseAgent):
    def __init__(self):
        super().__init__("SchemaMatchAgent")
    def run(self, state):
        standard = {}
        unknown = []
        raw_rows = 0
        for page in state.get("all_table_rows", []):
            if page.get("page_type") != "performance_data_table":
                continue
            for table in page.get("tables", []):
                title = table.get("table_title")
                for row in table.get("rows", []):
                    raw_rows += 1
                    if is_index_row(title, row):
                        continue
                    match = match_row_to_schema(row)
                    if match["matched"]:
                        item = standard_item(row, page.get("page_image"), title, match)
                        old = standard.get(match["field_key"])
                        if old is None or item["confidence"] > old.get("confidence", 0):
                            standard[match["field_key"]] = item
                    else:
                        unknown.append({"page_image": page.get("page_image"), "table_title": title, "topic": row.get("topic"), "metric_name": row.get("metric_name"), "unit": row.get("unit"), "values": row.get("values"), "evidence_text": row.get("evidence_text"), "reason": match["reason"]})
        final = {}
        for f in ESG_FIELD_KEYS:
            final[f] = standard.get(f) or {"field_key": f, "value": None, "status": "missing", "confidence": 0.0, "name_cn": ESG_SCHEMA[f]["name_cn"], "category": ESG_SCHEMA[f]["category"], "indicator_type": ESG_SCHEMA[f]["indicator_type"]}
        state["raw_row_count"] = raw_rows
        state["standard_results"] = final
        state["unknown_metrics"] = unknown
        state["extracted_fields"] = [k for k, v in final.items() if v.get("status") == "extracted"]
        state["missing_fields"] = [k for k, v in final.items() if v.get("status") != "extracted"]
        save_json(final, state["output_dir"] / "standard_esg_results.json")
        save_json(unknown, state["output_dir"] / "unknown_metrics.json")
        self.log(f"raw_rows={raw_rows}, extracted={len(state['extracted_fields'])}, unknown={len(unknown)}")
        return state
