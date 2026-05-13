# scripts/analyze_v1_results.py

import csv
import json
from pathlib import Path
from statistics import mean, median


PROJECT_ROOT = Path(__file__).resolve().parents[1]

OUTPUT_DIR = PROJECT_ROOT / "output"
DOCS_DIR = PROJECT_ROOT / "docs" / "v1_results"

BATCH_SUMMARY_PATH = OUTPUT_DIR / "batch_summary.csv"
ROUTE_B_SUMMARY_PATH = OUTPUT_DIR / "route_b_batch_summary.csv"
MERGE_SUMMARY_PATH = OUTPUT_DIR / "merge_batch_summary.csv"

PER_REPORT_EVAL_PATH = DOCS_DIR / "per_report_evaluation_v1.csv"
EVAL_JSON_PATH = DOCS_DIR / "evaluation_summary_v1.json"
EVAL_MD_PATH = DOCS_DIR / "evaluation_summary_v1.md"


def read_csv(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"找不到文件: {path}")

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def to_float(value, default=0.0):
    try:
        if value is None or str(value).strip() == "":
            return default
        return float(value)
    except Exception:
        return default


def to_int(value, default=0):
    try:
        if value is None or str(value).strip() == "":
            return default
        return int(float(value))
    except Exception:
        return default


def to_bool(value):
    text = str(value).strip().lower()
    return text in {"true", "1", "yes", "y", "success", "成功", "是"}


def clean_stem(value: str) -> str:
    if value is None:
        return ""

    name = Path(str(value)).stem

    return (
        name.replace(".pdf", "")
        .replace("：", "_")
        .replace(":", "_")
        .replace(" ", "")
        .replace("\n", "")
        .replace("\t", "")
    )


def report_dir_name(row):
    """
    优先使用 output_dir/report_dir 的最后一级目录名。
    """
    path_text = row.get("report_dir") or row.get("output_dir") or ""

    if path_text:
        return clean_stem(path_text)

    return ""


def pdf_stem(row):
    return clean_stem(
        row.get("pdf_file")
        or row.get("pdf_name")
        or row.get("report_name")
        or ""
    )


def strip_prefix_index(name: str) -> str:
    """
    001_xxx → xxx
    """
    parts = name.split("_", 1)

    if len(parts) == 2 and parts[0].isdigit():
        return parts[1]

    return name


def build_index(rows):
    """
    构建两个索引：
    1. report_dir/output_dir 的目录名
    2. 去掉 001_ 前缀后的目录名
    """
    index = {}

    for row in rows:
        dname = report_dir_name(row)

        if dname:
            index[dname] = row
            index[strip_prefix_index(dname)] = row

        stem = pdf_stem(row)

        if stem:
            index[stem] = row
            index[strip_prefix_index(stem)] = row

    return index


def lookup_row(index, base_name):
    if not base_name:
        return None

    if base_name in index:
        return index[base_name]

    no_prefix = strip_prefix_index(base_name)

    if no_prefix in index:
        return index[no_prefix]

    return None


def safe_avg(values):
    return round(mean(values), 2) if values else 0


def safe_median(values):
    return round(median(values), 2) if values else 0


def main():
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    route_a_rows = read_csv(BATCH_SUMMARY_PATH)
    route_b_rows = read_csv(ROUTE_B_SUMMARY_PATH)
    merge_rows = read_csv(MERGE_SUMMARY_PATH)

    route_b_index = build_index(route_b_rows)
    merge_index = build_index(merge_rows)

    per_report_rows = []

    for a_row in route_a_rows:
        base_name = report_dir_name(a_row)

        if not base_name:
            base_name = pdf_stem(a_row)

        b_row = lookup_row(route_b_index, base_name)
        m_row = lookup_row(merge_index, base_name)

        route_a_success = (
            str(a_row.get("status", "")).strip().lower() == "success"
            or to_bool(a_row.get("success"))
        )

        appendix_found = to_bool(a_row.get("appendix_found"))

        raw_rows = to_int(a_row.get("raw_row_count"))
        route_a_extracted = to_int(a_row.get("extracted_fields"))
        route_a_total = to_int(a_row.get("total_fields"), 68)
        unknown_metrics = to_int(a_row.get("unknown_metrics"))

        route_b_available = False
        route_b_matched = 0

        if b_row:
            route_b_available = to_bool(b_row.get("route_b_available"))
            route_b_matched = to_int(b_row.get("matched_fields"))

        merged_extracted = route_a_extracted
        merged_total = route_a_total
        route_b_filled = 0
        merged_coverage = round(route_a_extracted / route_a_total, 4) if route_a_total else 0

        if m_row:
            merged_extracted = to_int(m_row.get("merged_extracted_fields"), route_a_extracted)
            merged_total = to_int(m_row.get("total_fields"), route_a_total)
            route_b_filled = to_int(m_row.get("route_b_filled_fields"))
            merged_coverage = to_float(m_row.get("coverage_rate"), merged_coverage)

        route_a_coverage = round(route_a_extracted / route_a_total, 4) if route_a_total else 0

        per_report_rows.append({
            "report_name": base_name,
            "route_a_success": route_a_success,
            "appendix_found": appendix_found,
            "raw_row_count": raw_rows,
            "route_a_extracted_fields": route_a_extracted,
            "route_a_total_fields": route_a_total,
            "route_a_coverage_rate": route_a_coverage,
            "unknown_metrics": unknown_metrics,
            "route_b_available": route_b_available,
            "route_b_matched_fields": route_b_matched,
            "route_b_filled_fields": route_b_filled,
            "merged_extracted_fields": merged_extracted,
            "merged_total_fields": merged_total,
            "merged_coverage_rate": merged_coverage,
        })

    total_reports = len(per_report_rows)
    route_a_success_count = sum(1 for r in per_report_rows if r["route_a_success"])
    appendix_found_count = sum(1 for r in per_report_rows if r["appendix_found"])
    zero_raw_count = sum(1 for r in per_report_rows if r["raw_row_count"] == 0)
    route_b_available_count = sum(1 for r in per_report_rows if r["route_b_available"])

    raw_rows_values = [r["raw_row_count"] for r in per_report_rows]
    route_a_values = [r["route_a_extracted_fields"] for r in per_report_rows]
    route_b_filled_values = [r["route_b_filled_fields"] for r in per_report_rows]
    merge_values = [r["merged_extracted_fields"] for r in per_report_rows]
    merged_coverage_values = [r["merged_coverage_rate"] for r in per_report_rows]

    best_report = max(per_report_rows, key=lambda r: r["merged_extracted_fields"])
    worst_report = min(per_report_rows, key=lambda r: r["merged_extracted_fields"])

    summary = {
        "total_reports": total_reports,
        "route_a_success_count": route_a_success_count,
        "appendix_found_count": appendix_found_count,
        "zero_raw_row_reports": zero_raw_count,
        "route_b_available_count": route_b_available_count,

        "avg_raw_row_count": safe_avg(raw_rows_values),
        "median_raw_row_count": safe_median(raw_rows_values),

        "avg_route_a_extracted_fields": safe_avg(route_a_values),
        "median_route_a_extracted_fields": safe_median(route_a_values),

        "avg_route_b_filled_fields": safe_avg(route_b_filled_values),
        "median_route_b_filled_fields": safe_median(route_b_filled_values),

        "avg_merged_extracted_fields": safe_avg(merge_values),
        "median_merged_extracted_fields": safe_median(merge_values),

        "avg_merged_coverage_rate": round(mean(merged_coverage_values), 4) if merged_coverage_values else 0,

        "best_report": {
            "report_name": best_report.get("report_name"),
            "merged_extracted_fields": best_report.get("merged_extracted_fields"),
            "merged_coverage_rate": best_report.get("merged_coverage_rate"),
        },
        "lowest_report": {
            "report_name": worst_report.get("report_name"),
            "merged_extracted_fields": worst_report.get("merged_extracted_fields"),
            "merged_coverage_rate": worst_report.get("merged_coverage_rate"),
        },
    }

    with open(PER_REPORT_EVAL_PATH, "w", encoding="utf-8-sig", newline="") as f:
        fieldnames = list(per_report_rows[0].keys()) if per_report_rows else []
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(per_report_rows)

    with open(EVAL_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "summary": summary,
                "per_report": per_report_rows,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    md = f"""# v1.0 Evaluation Summary

## Dataset

- Total reports: {summary["total_reports"]}
- Route A success: {summary["route_a_success_count"]} / {summary["total_reports"]}
- Appendix found: {summary["appendix_found_count"]} / {summary["total_reports"]}
- Reports with raw rows = 0: {summary["zero_raw_row_reports"]}

## Route A: Appendix Table Extraction

- Average raw table rows per report: {summary["avg_raw_row_count"]}
- Median raw table rows per report: {summary["median_raw_row_count"]}
- Average extracted Core fields: {summary["avg_route_a_extracted_fields"]}
- Median extracted Core fields: {summary["median_route_a_extracted_fields"]}

## Route B: Text-based Qualitative Extraction

- Route B available reports: {summary["route_b_available_count"]} / {summary["total_reports"]}
- Average fields filled by Route B: {summary["avg_route_b_filled_fields"]}
- Median fields filled by Route B: {summary["median_route_b_filled_fields"]}

## Merged Results

- Average merged extracted fields: {summary["avg_merged_extracted_fields"]}
- Median merged extracted fields: {summary["median_merged_extracted_fields"]}
- Average merged coverage rate: {summary["avg_merged_coverage_rate"]}

## Best Report

- Report: {summary["best_report"]["report_name"]}
- Extracted fields: {summary["best_report"]["merged_extracted_fields"]}
- Coverage rate: {summary["best_report"]["merged_coverage_rate"]}

## Lowest Report

- Report: {summary["lowest_report"]["report_name"]}
- Extracted fields: {summary["lowest_report"]["merged_extracted_fields"]}
- Coverage rate: {summary["lowest_report"]["merged_coverage_rate"]}

## Interpretation

The v1.0 system successfully completes a dual-route ESG extraction workflow:

1. Route A extracts quantitative ESG indicators from appendix performance tables.
2. Route B extracts qualitative ESG mechanism indicators from report text.
3. Merge Pipeline combines both routes into a unified Core ESG result.

The results show that the system can process multiple ESG/CSR reports in batch mode and produce structured Core ESG indicators with evidence, confidence scores, and source-route tracking.
"""

    EVAL_MD_PATH.write_text(md, encoding="utf-8")

    print("v1 评估统计已生成：")
    print(f"- {PER_REPORT_EVAL_PATH}")
    print(f"- {EVAL_JSON_PATH}")
    print(f"- {EVAL_MD_PATH}")

    print("\n关键摘要：")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()