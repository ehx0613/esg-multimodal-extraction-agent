from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "output" / "reports"
DEFAULT_REVIEW_DIR = PROJECT_ROOT / "docs" / "eval" / "reviews"

REVIEW_RESULT_OPTIONS = "correct|wrong|correct_missing|missed"
ERROR_TYPE_OPTIONS = (
    "table_not_found|raw_metric_missing|schema_mismatch|wrong_value|wrong_unit|"
    "wrong_year|retrieval_miss|unsupported_claim|merge_error|false_positive|other"
)

OUTPUT_FIELDS = [
    "report_id",
    "field_key",
    "field_name_cn",
    "category",
    "applicability",
    "indicator_type",
    "predicted_status",
    "predicted_value",
    "predicted_raw_value",
    "predicted_unit",
    "predicted_year",
    "predicted_source_route",
    "predicted_confidence",
    "merge_reason",
    "missing_reason",
    "evidence_page",
    "evidence_text",
    "review_priority",
    "review_result",
    "golden_value",
    "golden_unit",
    "golden_year",
    "golden_evidence_page",
    "golden_evidence_text",
    "error_type",
    "notes",
]


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def resolve_report_dir(value: str) -> Path:
    requested = Path(value)
    if requested.exists() and requested.is_dir():
        return requested.resolve()

    name = requested.name
    exact = REPORTS_DIR / name
    if exact.exists():
        return exact.resolve()

    matches = sorted(
        directory
        for directory in REPORTS_DIR.iterdir()
        if directory.is_dir() and name.lower() in directory.name.lower()
    )
    if not matches:
        raise FileNotFoundError(
            f"未找到报告目录: {value}\n"
            f"可以传入完整目录，或使用 output/reports 下目录名称的一部分。"
        )
    if len(matches) > 1:
        choices = "\n".join(f"- {item.name}" for item in matches[:10])
        raise ValueError(f"报告目录匹配到多个结果，请输入更完整的名称:\n{choices}")
    return matches[0].resolve()


def compact(value: Any, limit: int = 500) -> str:
    text = " ".join(str(value or "").split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def parse_pages(value: Any) -> str:
    if value in (None, ""):
        return ""
    if isinstance(value, list):
        return ";".join(str(item) for item in value)
    text = str(value).strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return ";".join(str(item) for item in parsed)
    except Exception:
        pass
    return text


def choose_evidence(row: Dict[str, Any]) -> str:
    for key in (
        "citation_evidence_text",
        "evidence",
        "route_b_evidence",
        "route_b2_evidence",
    ):
        if str(row.get(key, "") or "").strip():
            return compact(row[key])
    return ""


def choose_pages(row: Dict[str, Any]) -> str:
    for key in (
        "citation_page_number",
        "source_pages",
        "route_b_source_pages",
        "route_b2_source_pages",
        "page_image",
    ):
        pages = parse_pages(row.get(key))
        if pages:
            return pages
    return ""


def review_priority(row: Dict[str, Any]) -> str:
    status = str(row.get("status", "")).strip()
    source = str(row.get("source_route", "")).strip()
    confidence = float(row.get("confidence") or 0)
    applicability = str(row.get("applicability", "")).strip()
    merge_reason = str(row.get("merge_reason", "")).strip()

    if status != "extracted" and applicability in {"core", "optional"}:
        return "high_missing"
    if source in {"route_b_text_rag", "route_b_quantitative_fallback"}:
        return "high_route_b"
    if "conflict" in merge_reason or confidence < 0.75:
        return "high_low_confidence_or_conflict"
    return "normal"


def build_review_rows(report_dir: Path) -> List[Dict[str, Any]]:
    citations_path = report_dir / "field_citations.json"
    merged_json_path = report_dir / "merged_esg_results.json"
    merged_csv_path = report_dir / "merged_esg_results.csv"

    rows = read_json(citations_path)
    if not isinstance(rows, list):
        rows = read_json(merged_json_path)
    if not isinstance(rows, list):
        if not merged_csv_path.exists():
            raise FileNotFoundError(
                f"报告目录缺少 merged_esg_results.csv/json: {report_dir}"
            )
        rows = read_csv(merged_csv_path)

    output = []
    for row in rows:
        output.append(
            {
                "report_id": report_dir.name,
                "field_key": row.get("field_key", ""),
                "field_name_cn": row.get("field_name_cn", ""),
                "category": row.get("category", ""),
                "applicability": row.get("applicability", ""),
                "indicator_type": row.get("indicator_type", ""),
                "predicted_status": row.get("status", ""),
                "predicted_value": row.get("value", ""),
                "predicted_raw_value": row.get("raw_value", ""),
                "predicted_unit": row.get("unit", ""),
                "predicted_year": row.get("year", ""),
                "predicted_source_route": row.get("source_route", ""),
                "predicted_confidence": row.get("confidence", ""),
                "merge_reason": row.get("merge_reason", ""),
                "missing_reason": row.get("missing_reason", ""),
                "evidence_page": choose_pages(row),
                "evidence_text": choose_evidence(row),
                "review_priority": review_priority(row),
                "review_result": "",
                "golden_value": "",
                "golden_unit": "",
                "golden_year": "",
                "golden_evidence_page": "",
                "golden_evidence_text": "",
                "error_type": "",
                "notes": "",
            }
        )
    return output


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_instructions(path: Path, report_dir: Path, review_csv: Path) -> None:
    path.write_text(
        f"""# 字段人工审核说明

- 报告目录：`{report_dir}`
- 审核表：`{review_csv}`
- `review_result` 可填写：`{REVIEW_RESULT_OPTIONS}`
- `error_type` 可填写：`{ERROR_TYPE_OPTIONS}`

审核规则：

- `correct`：系统提取结果正确。
- `wrong`：系统提取了字段，但字段、数值、单位、年份或证据错误。
- `correct_missing`：系统标记缺失，报告也确实没有披露。
- `missed`：系统标记缺失，但报告中实际存在。

优先审核 `review_priority` 以 `high_` 开头的字段。对于 `correct` 和
`correct_missing`，通常只需填写 `review_result` 和必要备注；对于 `wrong`
或 `missed`，请填写 golden 值、证据页和 `error_type`。
""",
        encoding="utf-8",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="从报告最终合并结果生成字段级人工审核表。"
    )
    parser.add_argument("report_dir", help="报告目录、完整路径或目录名称的一部分。")
    parser.add_argument(
        "--output",
        default=None,
        help="可选输出 CSV 路径。默认写入 docs/eval/reviews/。",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report_dir = resolve_report_dir(args.report_dir)
    output_path = (
        Path(args.output)
        if args.output
        else DEFAULT_REVIEW_DIR / f"{report_dir.name}_field_review.csv"
    )
    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path

    rows = build_review_rows(report_dir)
    write_csv(output_path, rows)
    instructions_path = output_path.with_name(output_path.stem + "_README.md")
    write_instructions(instructions_path, report_dir, output_path)

    high_priority = sum(str(row["review_priority"]).startswith("high_") for row in rows)
    print(f"report_dir={report_dir}")
    print(f"review_rows={len(rows)}")
    print(f"high_priority_rows={high_priority}")
    print(f"review_csv={output_path}")
    print(f"instructions={instructions_path}")


if __name__ == "__main__":
    main()
