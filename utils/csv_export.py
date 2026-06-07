import csv
from pathlib import Path
from config.schema import ESG_SCHEMA


def export_standard_results_csv(results, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["field_key", "name_cn", "category", "indicator_type", "status", "value", "raw_value", "unit", "year", "row_label", "topic", "confidence", "match_reason", "page_image", "evidence_text"]
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for k, item in results.items():
            s = ESG_SCHEMA.get(k, {})
            w.writerow({c: item.get(c) for c in fields} | {"field_key": k, "name_cn": s.get("name_cn"), "category": s.get("category"), "indicator_type": s.get("indicator_type")})


def export_unknown_metrics_csv(items, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["page_image", "table_title", "topic", "metric_name", "unit", "values", "evidence_text", "reason"]
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for item in items:
            w.writerow({c: item.get(c) for c in fields})
