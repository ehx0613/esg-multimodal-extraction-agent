import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config.core_schema import CORE_SCHEMA, ESG_FIELD_KEYS
from utils.schema_matcher import match_row_to_schema, is_index_row
import unicodedata

def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def norm(value):
    if value is None:
        return ""

    text = unicodedata.normalize("NFKC", str(value))

    return (
        text.lower()
        .replace(" ", "")
        .replace("\n", "")
        .replace("\t", "")
        .replace("（", "(")
        .replace("）", ")")
        .replace("：", ":")
        .replace("，", ",")
    )

def parse_year_from_key(key: str) -> Optional[int]:
    match = re.search(r"20[0-3][0-9]", str(key))
    if not match:
        return None
    return int(match.group(0))


def choose_latest_year_value(values: Dict[str, Any]) -> Tuple[Optional[int], Optional[str], Any]:
    """
    从 values 中选择最新年份的值。
    例如：
    {"2022年度": "1", "2023年度": "2", "2024年度": "3"}
    → 2024, "2024年度", "3"
    """

    if not isinstance(values, dict) or not values:
        return None, None, None

    candidates = []

    for key, value in values.items():
        year = parse_year_from_key(str(key))
        if year:
            candidates.append((year, str(key), value))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0]

    last_key = list(values.keys())[-1]
    return None, str(last_key), values[last_key]


def parse_value(raw_value: Any):
    if raw_value is None:
        return None

    text = str(raw_value).strip()

    if text in {"", "/", "-", "—", "N/A", "NA", "不适用", "未披露"}:
        return None

    clean = (
        text.replace(",", "")
        .replace("，", "")
        .replace("%", "")
    )

    if clean.endswith("+"):
        return text

    try:
        value = float(clean)

        if value.is_integer():
            return int(value)

        return value
    except Exception:
        return text


def empty_standard_item(field_key: str) -> Dict[str, Any]:
    schema_item = next(
        (item for item in CORE_SCHEMA if item["field_key"] == field_key),
        {},
    )

    return {
        "field_key": field_key,
        "field_name_cn": schema_item.get("name_cn", ""),
        "category": schema_item.get("category", ""),
        "indicator_type": schema_item.get("indicator_type", ""),
        "value_type": schema_item.get("value_type", ""),
        "value": None,
        "raw_value": None,
        "unit": None,
        "year": None,
        "column_label": None,
        "row_label": None,
        "topic": None,
        "table_title": None,
        "page_image": None,
        "evidence_text": None,
        "status": "missing",
        "confidence": 0.0,
        "match_reason": "not_found",
    }


def flatten_all_table_rows(all_table_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    兼容你的 all_table_rows.json 结构：
    [
      {
        "page_image": "...",
        "page_type": "performance_data_table",
        "tables": [
          {
            "table_title": "...",
            "rows": [...]
          }
        ]
      }
    ]
    """

    rows = []

    for page in all_table_rows:
        page_image = page.get("page_image")
        page_type = page.get("page_type")
        tables = page.get("tables", [])

        if page_type != "performance_data_table":
            continue

        for table in tables:
            table_title = table.get("table_title")
            table_rows = table.get("rows", [])

            for row in table_rows:
                if not isinstance(row, dict):
                    continue

                new_row = dict(row)
                new_row["page_image"] = page_image
                new_row["page_type"] = page_type
                new_row["table_title"] = table_title

                if "row_label" not in new_row:
                    new_row["row_label"] = new_row.get("metric_name")

                rows.append(new_row)

    return rows


def build_extracted_item(field_key: str, row: Dict[str, Any], match_result: Dict[str, Any]) -> Dict[str, Any]:
    schema_item = next(
        (item for item in CORE_SCHEMA if item["field_key"] == field_key),
        {},
    )

    values = row.get("values", {})
    year, column_label, raw_value = choose_latest_year_value(values)

    return {
        "field_key": field_key,
        "field_name_cn": schema_item.get("name_cn", ""),
        "category": schema_item.get("category", ""),
        "indicator_type": schema_item.get("indicator_type", ""),
        "value_type": schema_item.get("value_type", ""),
        "value": parse_value(raw_value),
        "raw_value": raw_value,
        "unit": row.get("unit"),
        "year": year,
        "column_label": column_label,
        "row_label": row.get("metric_name") or row.get("row_label"),
        "topic": row.get("topic") or row.get("topic_label"),
        "table_title": row.get("table_title"),
        "page_image": row.get("page_image"),
        "evidence_text": row.get("evidence_text"),
        "status": "extracted",
        "confidence": match_result.get("confidence", 0.0),
        "match_reason": match_result.get("reason", ""),
    }


def build_unknown_item(row: Dict[str, Any], match_result: Dict[str, Any]) -> Dict[str, Any]:
    values = row.get("values", {})
    year, column_label, raw_value = choose_latest_year_value(values)

    return {
        "page_image": row.get("page_image"),
        "table_title": row.get("table_title"),
        "topic": row.get("topic") or row.get("topic_label"),
        "metric_name": row.get("metric_name") or row.get("row_label"),
        "unit": row.get("unit"),
        "year": year,
        "column_label": column_label,
        "value": parse_value(raw_value),
        "raw_value": raw_value,
        "values": json.dumps(values, ensure_ascii=False),
        "evidence_text": row.get("evidence_text"),
        "reason": match_result.get("reason", "no_schema_match"),
        "confidence": match_result.get("confidence", 0.0),
    }


def write_csv(path: Path, rows: List[Dict[str, Any]]):
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            f.write("")
        return

    # 不要只用 rows[0].keys()
    # 因为有些 extracted 行会多出 column_label 等字段
    preferred_order = [
        "field_key",
        "field_name_cn",
        "category",
        "indicator_type",
        "value_type",
        "value",
        "raw_value",
        "unit",
        "year",
        "column_label",
        "row_label",
        "topic",
        "table_title",
        "page_image",
        "evidence_text",
        "status",
        "confidence",
        "match_reason",
    ]

    all_keys = set()

    for row in rows:
        all_keys.update(row.keys())

    extra_keys = sorted(k for k in all_keys if k not in preferred_order)
    fieldnames = [k for k in preferred_order if k in all_keys] + extra_keys

    tmp_path = path.with_suffix(path.suffix + ".tmp")

    with open(tmp_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)

    tmp_path.replace(path)

def find_latest_report_dir() -> Path:
    reports_dir = PROJECT_ROOT / "output" / "reports"

    report_dirs = [
        p for p in reports_dir.iterdir()
        if p.is_dir() and (p / "all_table_rows.json").exists()
    ]

    if not report_dirs:
        raise FileNotFoundError("没有找到包含 all_table_rows.json 的报告目录。")

    report_dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return report_dirs[0]


def rerun_schema_match(report_dir: Path):
    all_table_rows_path = report_dir / "all_table_rows.json"

    if not all_table_rows_path.exists():
        raise FileNotFoundError(f"找不到 all_table_rows.json: {all_table_rows_path}")

    all_table_rows = load_json(all_table_rows_path)
    flat_rows = flatten_all_table_rows(all_table_rows)

    standard_results = {
        field_key: empty_standard_item(field_key)
        for field_key in ESG_FIELD_KEYS
    }

    unknown_metrics = []
    skipped_index_rows = 0

    for row in flat_rows:
        title = row.get("table_title", "")

        if is_index_row(title, row):
            skipped_index_rows += 1
            continue

        metric_name = row.get("metric_name") or row.get("row_label")

        if not metric_name:
            continue

        match_result = match_row_to_schema(row)

        if match_result.get("matched"):
            field_key = match_result.get("field_key")
            new_item = build_extracted_item(field_key, row, match_result)

            old_item = standard_results.get(field_key)

            if old_item is None or old_item.get("status") != "extracted":
                standard_results[field_key] = new_item
            else:
                old_conf = old_item.get("confidence", 0) or 0
                new_conf = new_item.get("confidence", 0) or 0

                if new_conf > old_conf:
                    standard_results[field_key] = new_item

        else:
            unknown_metrics.append(
                build_unknown_item(row, match_result)
            )

    standard_rows = [
        standard_results[field_key]
        for field_key in ESG_FIELD_KEYS
    ]
    if len(standard_rows) < 60:
        raise RuntimeError(
            f"standard_rows 数量异常: {len(standard_rows)}，拒绝覆盖 standard_esg_results.csv"
        )
    extracted_count = sum(
        1 for item in standard_rows
        if item.get("status") == "extracted"
    )

    missing_count = len(standard_rows) - extracted_count

    summary = {
        "total_fields": len(standard_rows),
        "extracted_fields": extracted_count,
        "missing_fields": missing_count,
        "unknown_metrics": len(unknown_metrics),
        "skipped_index_rows": skipped_index_rows,
    }

    save_json(report_dir / "standard_esg_results.json", standard_rows)
    save_json(report_dir / "unknown_metrics.json", unknown_metrics)
    save_json(report_dir / "validation_summary.json", summary)

    write_csv(report_dir / "standard_esg_results.csv", standard_rows)
    write_csv(report_dir / "unknown_metrics.csv", unknown_metrics)

    print("Schema 重新匹配完成。")
    print(f"总字段数: {summary['total_fields']}")
    print(f"已抽取字段数: {summary['extracted_fields']}")
    print(f"缺失字段数: {summary['missing_fields']}")
    print(f"unknown 指标数: {summary['unknown_metrics']}")
    print(f"跳过索引行数: {summary['skipped_index_rows']}")
    print(f"standard_esg_results.csv: {report_dir / 'standard_esg_results.csv'}")
    print(f"unknown_metrics.csv: {report_dir / 'unknown_metrics.csv'}")


def main():
    if len(sys.argv) > 1:
        report_dir = Path(sys.argv[1])

        if not report_dir.is_absolute():
            report_dir = PROJECT_ROOT / report_dir
    else:
        report_dir = find_latest_report_dir()

    print(f"重新基于缓存表格行进行 Schema 匹配: {report_dir}")

    rerun_schema_match(report_dir)


if __name__ == "__main__":
    main()