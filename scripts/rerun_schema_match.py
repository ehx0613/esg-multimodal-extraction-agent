import argparse
import json
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config.schema import ESG_FIELD_KEYS, ESG_SCHEMA
from config.settings import ROUTE_A_B2_MIN_EXTRACTED_FIELDS
from utils.result_guard import safe_write_csv, safe_write_json
from utils.schema_matcher import is_index_row, match_row_to_schema


STANDARD_RESULTS_FIELD_ORDER = [
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


def load_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


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

    clean = text.replace(",", "").replace("，", "").replace("%", "")

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
    schema_item = ESG_SCHEMA.get(field_key, {})

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
    schema_item = ESG_SCHEMA.get(field_key, {})

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


def extracted_item_priority(item: Dict[str, Any]) -> float:
    text = " ".join(
        str(item.get(key) or "")
        for key in ["row_label", "topic", "table_title", "evidence_text"]
    )
    score = float(item.get("confidence") or 0.0)
    if "总用水量" in text:
        score += 0.08
    if any(word in text for word in ["新鲜水取水总量", "取水总量", "新鲜水用量"]):
        score -= 0.03
    if any(word in text for word in ["新进员工", "新入职", "离职员工", "流失员工"]):
        score -= 0.08
    return score


def find_latest_report_dir() -> Path:
    reports_dir = PROJECT_ROOT / "output" / "reports"

    report_dirs = [
        p for p in reports_dir.iterdir() if p.is_dir() and (p / "all_table_rows.json").exists()
    ]

    if not report_dirs:
        raise FileNotFoundError("没有找到包含 all_table_rows.json 的报告目录。")

    report_dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return report_dirs[0]


def rerun_schema_match(report_dir: Path, *, allow_llm: bool = False):
    started_at = time.perf_counter()
    all_table_rows_path = report_dir / "all_table_rows.json"

    if not all_table_rows_path.exists():
        raise FileNotFoundError(f"找不到 all_table_rows.json: {all_table_rows_path}")

    all_table_rows = load_json(all_table_rows_path)
    flat_rows = flatten_all_table_rows(all_table_rows)

    standard_results = {field_key: empty_standard_item(field_key) for field_key in ESG_FIELD_KEYS}

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

        match_result = match_row_to_schema(row, allow_llm=allow_llm)

        if match_result.get("matched"):
            field_key = match_result.get("field_key")
            new_item = build_extracted_item(field_key, row, match_result)

            old_item = standard_results.get(field_key)

            if old_item is None or old_item.get("status") != "extracted":
                standard_results[field_key] = new_item
            else:
                if extracted_item_priority(new_item) > extracted_item_priority(old_item):
                    standard_results[field_key] = new_item
        else:
            unknown_metrics.append(build_unknown_item(row, match_result))

    standard_rows = [standard_results[field_key] for field_key in ESG_FIELD_KEYS]
    expected_standard_rows = len(ESG_FIELD_KEYS)

    if len(standard_rows) != expected_standard_rows:
        raise RuntimeError(
            f"standard_rows 数量异常: {len(standard_rows)}，期望 {expected_standard_rows}，拒绝覆盖 standard_esg_results.csv"
        )

    extracted_count = sum(1 for item in standard_rows if item.get("status") == "extracted")
    missing_count = len(standard_rows) - extracted_count
    needs_route_b2 = bool(missing_count and extracted_count < ROUTE_A_B2_MIN_EXTRACTED_FIELDS)

    summary = {
        "total_fields": len(standard_rows),
        "extracted_fields": extracted_count,
        "missing_fields": missing_count,
        "coverage_rate": round(extracted_count / len(standard_rows), 4) if standard_rows else 0,
        "raw_row_count": len(flat_rows),
        "unknown_metrics": len(unknown_metrics),
        "needs_route_b2": needs_route_b2,
        "route_b2_reason": f"route_a_extracted_below_{ROUTE_A_B2_MIN_EXTRACTED_FIELDS}" if needs_route_b2 else "",
        "skipped_index_rows": skipped_index_rows,
        "schema_llm_enabled": allow_llm,
        "elapsed_seconds": round(time.perf_counter() - started_at, 3),
    }

    safe_write_json(report_dir / "standard_esg_results.json", standard_rows)
    safe_write_json(report_dir / "unknown_metrics.json", unknown_metrics)
    safe_write_json(report_dir / "validation_summary.json", summary)
    safe_write_csv(
        report_dir / "standard_esg_results.csv",
        standard_rows,
        preferred_order=STANDARD_RESULTS_FIELD_ORDER,
    )
    safe_write_csv(report_dir / "unknown_metrics.csv", unknown_metrics)

    print("Schema 重新匹配完成。")
    print(f"总字段数: {summary['total_fields']}")
    print(f"已抽取字段数: {summary['extracted_fields']}")
    print(f"缺失字段数: {summary['missing_fields']}")
    print(f"unknown 指标数: {summary['unknown_metrics']}")
    print(f"跳过索引行数: {summary['skipped_index_rows']}")
    print(f"Schema 小模型: {'启用' if allow_llm else '禁用（快速本地规则模式）'}")
    print(f"耗时: {summary['elapsed_seconds']} 秒")
    print(f"standard_esg_results.csv: {report_dir / 'standard_esg_results.csv'}")
    print(f"unknown_metrics.csv: {report_dir / 'unknown_metrics.csv'}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Re-run Schema matching from cached table rows.")
    parser.add_argument(
        "report_dir",
        nargs="?",
        help="Report directory. Defaults to the latest report with all_table_rows.json.",
    )
    parser.add_argument(
        "--with-llm",
        action="store_true",
        help="Enable the Schema Judge fallback. Slower and may make network model calls.",
    )
    return parser.parse_args()

def main():
    args = parse_args()
    if args.report_dir:
        report_dir = Path(args.report_dir)
        if not report_dir.is_absolute():
            report_dir = PROJECT_ROOT / report_dir
    else:
        report_dir = find_latest_report_dir()

    print(f"重新基于缓存表格行进行 Schema 匹配: {report_dir}")
    rerun_schema_match(report_dir, allow_llm=args.with_llm)


if __name__ == "__main__":
    main()
