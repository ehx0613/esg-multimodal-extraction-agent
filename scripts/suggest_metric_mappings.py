import csv
import json
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config.schema import ROUTE_A_SCHEMA
from utils.result_guard import safe_write_csv
from utils.schema_match_validator import validate_schema_match


SUGGESTION_FIELD_ORDER = [
    "metric_name",
    "count",
    "suggested_action",
    "suggested_field_key",
    "suggested_name_cn",
    "suggested_alias",
    "score",
    "validator_status",
    "validator_reason",
    "unit",
    "topic_examples",
    "table_title_examples",
    "page_examples",
    "report_examples",
    "candidate_details",
]


def norm(value: Any) -> str:
    if value is None:
        return ""
    return (
        unicodedata.normalize("NFKC", str(value))
        .lower()
        .replace(" ", "")
        .replace("\n", "")
        .replace("\t", "")
        .replace("（", "(")
        .replace("）", ")")
        .replace("：", ":")
        .replace("，", ",")
    )


def compact_examples(values: Iterable[Any], limit: int = 5) -> str:
    seen = []
    for value in values:
        if value in {None, ""}:
            continue
        text = str(value)
        if text not in seen:
            seen.append(text)
        if len(seen) >= limit:
            break
    return ";".join(seen)


def load_unknown_rows(path: Path) -> List[Dict[str, Any]]:
    rows = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item = dict(row)
            item["report_dir"] = path.parent.name
            rows.append(item)
    return rows


def discover_unknown_csvs(target: Path) -> List[Path]:
    if target.is_file():
        return [target]
    if (target / "unknown_metrics.csv").exists():
        return [target / "unknown_metrics.csv"]
    return sorted(target.glob("*/unknown_metrics.csv"))


def parse_values(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not value:
        return {}
    try:
        parsed = json.loads(str(value))
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def build_validation_row(row: Dict[str, Any]) -> Dict[str, Any]:
    values = parse_values(row.get("values"))
    if not values and row.get("year"):
        values = {str(row.get("year")): row.get("raw_value") or row.get("value")}

    return {
        "metric_name": row.get("metric_name"),
        "topic": row.get("topic"),
        "table_title": row.get("table_title"),
        "evidence_text": row.get("evidence_text"),
        "unit": row.get("unit"),
        "values": values,
    }


def candidate_score(row: Dict[str, Any], schema_item: Dict[str, Any]) -> Tuple[float, str]:
    text = norm(
        " ".join(
            str(row.get(key) or "")
            for key in ["metric_name", "topic", "table_title", "evidence_text"]
        )
    )
    metric = norm(row.get("metric_name"))

    best_score = 0.0
    best_alias = ""

    for alias in schema_item.get("aliases", []):
        alias_norm = norm(alias)
        if not alias_norm:
            continue

        if alias_norm == metric:
            score = 1.0
        elif alias_norm in metric or metric in alias_norm:
            score = 0.92
        elif alias_norm in text:
            score = 0.86
        else:
            required_hits = sum(
                1 for word in schema_item.get("required_any", []) if norm(word) in text
            )
            alias_hits = sum(1 for word in [alias] if norm(word) in text)
            score = min(0.2 + required_hits * 0.16 + alias_hits * 0.2, 0.78)

        if score > best_score:
            best_score = score
            best_alias = alias

    return best_score, best_alias


def suggest_for_group(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    representative = rows[0]
    validation_row = build_validation_row(representative)

    candidates = []
    for item in ROUTE_A_SCHEMA:
        score, alias = candidate_score(validation_row, item)
        if score < 0.5:
            continue

        valid, validate_reason = validate_schema_match(item["field_key"], validation_row)
        candidates.append(
            {
                "field_key": item["field_key"],
                "name_cn": item["name_cn"],
                "alias": alias,
                "score": round(score, 4),
                "validator_status": "accepted" if valid else "rejected",
                "validator_reason": validate_reason,
            }
        )

    candidates.sort(
        key=lambda item: (
            item["validator_status"] == "accepted",
            item["score"],
        ),
        reverse=True,
    )

    best = candidates[0] if candidates else None
    if best and best["validator_status"] == "accepted" and best["score"] >= 0.78:
        action = "review_add_alias_or_rule"
        suggested_field_key = best["field_key"]
        suggested_name_cn = best["name_cn"]
        suggested_alias = representative.get("metric_name")
        score = best["score"]
        validator_status = best["validator_status"]
        validator_reason = best["validator_reason"]
    elif best:
        action = "review_candidate_rejected"
        suggested_field_key = best["field_key"]
        suggested_name_cn = best["name_cn"]
        suggested_alias = representative.get("metric_name")
        score = best["score"]
        validator_status = best["validator_status"]
        validator_reason = best["validator_reason"]
    else:
        action = "keep_unknown"
        suggested_field_key = ""
        suggested_name_cn = ""
        suggested_alias = ""
        score = 0
        validator_status = ""
        validator_reason = "no_candidate"

    return {
        "metric_name": representative.get("metric_name"),
        "count": len(rows),
        "suggested_action": action,
        "suggested_field_key": suggested_field_key,
        "suggested_name_cn": suggested_name_cn,
        "suggested_alias": suggested_alias,
        "score": score,
        "validator_status": validator_status,
        "validator_reason": validator_reason,
        "unit": compact_examples(row.get("unit") for row in rows),
        "topic_examples": compact_examples(row.get("topic") for row in rows),
        "table_title_examples": compact_examples(row.get("table_title") for row in rows),
        "page_examples": compact_examples(row.get("page_image") for row in rows),
        "report_examples": compact_examples(row.get("report_dir") for row in rows),
        "candidate_details": json.dumps(candidates[:3], ensure_ascii=False),
    }


def build_suggestions(paths: List[Path]) -> List[Dict[str, Any]]:
    grouped = defaultdict(list)
    for path in paths:
        for row in load_unknown_rows(path):
            metric_name = row.get("metric_name")
            if metric_name:
                grouped[norm(metric_name)].append(row)

    suggestions = [suggest_for_group(rows) for rows in grouped.values()]
    suggestions.sort(
        key=lambda item: (
            item["suggested_action"] == "review_add_alias_or_rule",
            item["count"],
            item["score"],
        ),
        reverse=True,
    )
    return suggestions


def main() -> None:
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
        if not target.is_absolute():
            target = PROJECT_ROOT / target
    else:
        target = PROJECT_ROOT / "output" / "reports"

    paths = discover_unknown_csvs(target)
    if not paths:
        raise FileNotFoundError(f"没有找到 unknown_metrics.csv: {target}")

    suggestions = build_suggestions(paths)

    if len(sys.argv) > 2:
        output_path = Path(sys.argv[2])
        if not output_path.is_absolute():
            output_path = PROJECT_ROOT / output_path
    elif len(paths) == 1:
        output_path = paths[0].parent / "mapping_suggestions.csv"
    else:
        output_path = PROJECT_ROOT / "output" / "mapping_suggestions.csv"

    safe_write_csv(output_path, suggestions, preferred_order=SUGGESTION_FIELD_ORDER)

    action_counts = Counter(item["suggested_action"] for item in suggestions)
    print(f"Mapping suggestions saved to: {output_path}")
    print(f"Unknown metric names: {len(suggestions)}")
    for action, count in action_counts.most_common():
        print(f"{action}: {count}")


if __name__ == "__main__":
    main()
