import csv
import json
from collections import defaultdict, Counter
from pathlib import Path

from utils.llm_unknown_metric_analyzer import analyze_unknown_metric_group


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "output" / "reports"
OUTPUT_DIR = PROJECT_ROOT / "output"

UNKNOWN_FILE_NAME = "unknown_metrics.csv"


def norm(text):
    if text is None:
        return ""

    return (
        str(text)
        .strip()
        .replace(" ", "")
        .replace("\n", "")
        .replace("\t", "")
        .replace("（", "(")
        .replace("）", ")")
    )


def read_unknown_csv(path: Path):
    rows = []

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            row["_report_dir"] = path.parent.name
            row["_source_file"] = str(path)
            rows.append(row)

    return rows


def collect_unknown_rows():
    unknown_paths = sorted(REPORTS_DIR.glob(f"*/{UNKNOWN_FILE_NAME}"))

    if not unknown_paths:
        single_path = OUTPUT_DIR / UNKNOWN_FILE_NAME
        if single_path.exists():
            unknown_paths = [single_path]

    if not unknown_paths:
        raise FileNotFoundError("没有找到 unknown_metrics.csv")

    all_rows = []

    for path in unknown_paths:
        all_rows.extend(read_unknown_csv(path))

    return all_rows


def build_metric_groups(rows):
    groups = defaultdict(list)

    for row in rows:
        metric_name = row.get("metric_name", "")
        key = norm(metric_name)

        if not key:
            continue

        groups[key].append(row)

    metric_groups = []

    for key, items in groups.items():
        units = Counter(row.get("unit", "") for row in items)
        reasons = Counter(row.get("reason", "") for row in items)
        reports = sorted(set(row.get("_report_dir", "") for row in items))

        example = items[0]

        metric_groups.append({
            "metric_name": example.get("metric_name", key),
            "count": len(items),
            "units": [
                {"unit": unit, "count": count}
                for unit, count in units.most_common()
            ],
            "top_reasons": [
                {"reason": reason, "count": count}
                for reason, count in reasons.most_common(3)
            ],
            "example_reports": reports[:5],
            "examples": [
                {
                    "topic": row.get("topic", ""),
                    "table_title": row.get("table_title", ""),
                    "unit": row.get("unit", ""),
                    "values": row.get("values", ""),
                    "evidence_text": row.get("evidence_text", ""),
                    "reason": row.get("reason", ""),
                }
                for row in items[:3]
            ],
        })

    metric_groups.sort(key=lambda x: x["count"], reverse=True)

    return metric_groups


def main():
    rows = collect_unknown_rows()
    metric_groups = build_metric_groups(rows)

    print(f"共读取 unknown 行数: {len(rows)}")
    print(f"唯一 unknown 指标数: {len(metric_groups)}")

    results = []

    for idx, group in enumerate(metric_groups, start=1):
        print(f"[{idx}/{len(metric_groups)}] 分析 unknown 指标: {group['metric_name']}")

        llm_result = analyze_unknown_metric_group(group)

        results.append({
            **group,
            "llm_action": llm_result.get("action"),
            "target_field_key": llm_result.get("target_field_key"),
            "suggested_field_key": llm_result.get("suggested_field_key"),
            "suggested_aliases": json.dumps(llm_result.get("suggested_aliases", []), ensure_ascii=False),
            "suggested_required_any": json.dumps(llm_result.get("suggested_required_any", []), ensure_ascii=False),
            "name_cn": llm_result.get("name_cn"),
            "category": llm_result.get("category"),
            "value_type": llm_result.get("value_type"),
            "confidence": llm_result.get("confidence"),
            "llm_reason": llm_result.get("reason"),
        })

    json_path = OUTPUT_DIR / "llm_core_update_suggestions.json"
    csv_path = OUTPUT_DIR / "llm_core_update_suggestions.csv"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    fieldnames = [
        "metric_name",
        "count",
        "llm_action",
        "target_field_key",
        "suggested_field_key",
        "suggested_aliases",
        "suggested_required_any",
        "name_cn",
        "category",
        "value_type",
        "confidence",
        "llm_reason",
        "example_reports",
    ]

    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        for item in results:
            writer.writerow({
                "metric_name": item.get("metric_name"),
                "count": item.get("count"),
                "llm_action": item.get("llm_action"),
                "target_field_key": item.get("target_field_key"),
                "suggested_field_key": item.get("suggested_field_key"),
                "suggested_aliases": item.get("suggested_aliases"),
                "suggested_required_any": item.get("suggested_required_any"),
                "name_cn": item.get("name_cn"),
                "category": item.get("category"),
                "value_type": item.get("value_type"),
                "confidence": item.get("confidence"),
                "llm_reason": item.get("llm_reason"),
                "example_reports": "; ".join(item.get("example_reports", [])),
            })

    print(f"LLM Core 更新建议 JSON 已保存: {json_path}")
    print(f"LLM Core 更新建议 CSV 已保存: {csv_path}")


if __name__ == "__main__":
    main()
