# pipeline/merge_pipeline.py

import csv
import json
from pathlib import Path
from typing import Dict, Any, List


EMPTY_VALUES = {"", "None", "none", "null", "NULL", "N/A", "NA", "nan"}


def load_csv(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def save_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_csv(path: Path, rows: List[Dict[str, Any]]):
    path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            f.write("")
        return

    fieldnames = list(rows[0].keys())

    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def to_float(value, default=0.0) -> float:
    try:
        if value in EMPTY_VALUES or value is None:
            return default
        return float(value)
    except Exception:
        return default


def parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value

    text = str(value).strip().lower()

    return text in {"true", "1", "yes", "y", "是", "匹配", "matched"}


def parse_source_pages(value):
    if value is None:
        return []

    if isinstance(value, list):
        return value

    text = str(value).strip()

    if not text:
        return []

    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
    except Exception:
        pass

    return [text]


def is_route_a_extracted(row: Dict[str, Any]) -> bool:
    return str(row.get("status", "")).strip() == "extracted"


def is_route_b_matched(row: Dict[str, Any], min_confidence: float = 0.5) -> bool:
    matched = parse_bool(row.get("matched"))
    confidence = to_float(row.get("confidence"), 0.0)

    return matched and confidence >= min_confidence


def normalize_route_a_row(row: Dict[str, Any]) -> Dict[str, Any]:
    extracted = is_route_a_extracted(row)

    return {
        "field_key": row.get("field_key", ""),
        "field_name_cn": row.get("field_name_cn", ""),
        "category": row.get("category", ""),
        "indicator_type": row.get("indicator_type", ""),
        "value_type": row.get("value_type", ""),

        "status": "extracted" if extracted else "missing",
        "value": row.get("value", ""),
        "raw_value": row.get("raw_value", ""),
        "unit": row.get("unit", ""),
        "year": row.get("year", ""),

        "source_route": "route_a_appendix_table" if extracted else "missing",
        "confidence": row.get("confidence", "0"),
        "evidence": row.get("evidence_text", ""),
        "source_pages": row.get("page_image", ""),

        "row_label": row.get("row_label", ""),
        "topic": row.get("topic", ""),
        "table_title": row.get("table_title", ""),
        "page_image": row.get("page_image", ""),

        "route_a_status": row.get("status", ""),
        "route_a_confidence": row.get("confidence", "0"),
        "route_a_reason": row.get("match_reason", ""),

        "route_b_matched": "",
        "route_b_confidence": "",
        "route_b_summary": "",
        "route_b_evidence": "",
        "route_b_source_pages": "",
        "route_b_reason": "",
    }


def apply_route_b_to_merged(
    merged_by_key: Dict[str, Dict[str, Any]],
    route_b_rows: List[Dict[str, Any]],
    min_confidence: float = 0.5,
):
    """
    合并路线 B。

    规则：
    1. 路线 A 已抽到的字段，不直接覆盖；
    2. 路线 A missing 且路线 B matched，则用路线 B 补；
    3. 路线 A 已有值时，路线 B 证据作为补充 evidence 保留。
    """

    for row in route_b_rows:
        field_key = row.get("field_key", "")

        if not field_key:
            continue

        if field_key not in merged_by_key:
            continue

        if not is_route_b_matched(row, min_confidence=min_confidence):
            continue

        item = merged_by_key[field_key]

        source_pages = parse_source_pages(row.get("source_pages"))
        source_pages_text = json.dumps(source_pages, ensure_ascii=False)

        # 先记录路线 B 的辅助证据
        item["route_b_matched"] = "true"
        item["route_b_confidence"] = row.get("confidence", "")
        item["route_b_summary"] = row.get("summary", "")
        item["route_b_evidence"] = row.get("evidence", "")
        item["route_b_source_pages"] = source_pages_text
        item["route_b_reason"] = row.get("reason", "")

        # 只有路线 A missing 时，路线 B 才补入最终值
        if item.get("status") != "extracted":
            item["status"] = "extracted"
            item["value"] = row.get("value", "true")
            item["raw_value"] = row.get("value", "true")
            item["unit"] = ""
            item["year"] = ""

            item["source_route"] = "route_b_text_rag"
            item["confidence"] = row.get("confidence", "0")
            item["evidence"] = row.get("evidence", "")
            item["source_pages"] = source_pages_text

            item["row_label"] = row.get("summary", "")
            item["topic"] = "正文定性机制"
            item["table_title"] = ""
            item["page_image"] = ""


class ESGMergePipeline:
    """
    合并路线 A 与路线 B 的结果。

    输入：
    - standard_esg_results.csv
    - route_b_text_results.csv

    输出：
    - merged_esg_results.csv
    - merged_esg_results.json
    - merge_summary.json
    """

    def __init__(self, report_dir: Path, min_route_b_confidence: float = 0.5):
        self.report_dir = Path(report_dir)
        self.min_route_b_confidence = min_route_b_confidence

    def run(self) -> Dict[str, Any]:
        print("\n----- Running ESGMergePipeline -----")
        print(f"Report dir: {self.report_dir}")

        route_a_path = self.report_dir / "standard_esg_results.csv"
        route_b_path = self.report_dir / "route_b_text_results.csv"

        route_a_rows = load_csv(route_a_path)
        route_b_rows = load_csv(route_b_path)

        if not route_a_rows:
            raise FileNotFoundError(f"找不到路线 A 结果: {route_a_path}")

        merged_rows = [
            normalize_route_a_row(row)
            for row in route_a_rows
        ]

        merged_by_key = {
            row["field_key"]: row
            for row in merged_rows
            if row.get("field_key")
        }

        apply_route_b_to_merged(
            merged_by_key=merged_by_key,
            route_b_rows=route_b_rows,
            min_confidence=self.min_route_b_confidence,
        )

        # 保持路线 A 原始字段顺序
        final_rows = [
            merged_by_key[row["field_key"]]
            for row in merged_rows
            if row.get("field_key") in merged_by_key
        ]

        route_a_extracted = sum(
            1 for row in final_rows
            if row.get("route_a_status") == "extracted"
        )

        route_b_filled = sum(
            1 for row in final_rows
            if row.get("source_route") == "route_b_text_rag"
        )

        route_b_matched = sum(
            1 for row in final_rows
            if row.get("route_b_matched") == "true"
        )

        total_extracted = sum(
            1 for row in final_rows
            if row.get("status") == "extracted"
        )

        total_fields = len(final_rows)

        summary = {
            "total_fields": total_fields,
            "route_a_extracted_fields": route_a_extracted,
            "route_b_matched_fields": route_b_matched,
            "route_b_filled_fields": route_b_filled,
            "merged_extracted_fields": total_extracted,
            "missing_fields": total_fields - total_extracted,
            "coverage_rate": round(total_extracted / total_fields, 4) if total_fields else 0.0,
            "route_a_path": str(route_a_path),
            "route_b_path": str(route_b_path),
        }

        save_json(self.report_dir / "merged_esg_results.json", final_rows)
        save_csv(self.report_dir / "merged_esg_results.csv", final_rows)
        save_json(self.report_dir / "merge_summary.json", summary)

        print(f"[Merge] route_a_extracted={route_a_extracted}")
        print(f"[Merge] route_b_matched={route_b_matched}")
        print(f"[Merge] route_b_filled={route_b_filled}")
        print(f"[Merge] merged_extracted={total_extracted}/{total_fields}")

        return summary