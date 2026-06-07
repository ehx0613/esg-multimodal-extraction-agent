import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from config.schema import ESG_FIELD_KEYS


PathLike = Union[str, Path]
DEFAULT_EXPECTED_ROWS = len(ESG_FIELD_KEYS)


def _to_path(path: PathLike) -> Path:
    return path if isinstance(path, Path) else Path(path)


def count_csv_rows(path: PathLike) -> int:
    csv_path = _to_path(path)
    if not csv_path.exists():
        return 0

    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        try:
            next(reader)
        except StopIteration:
            return 0
        return sum(1 for _ in reader)


def validate_csv_min_rows(path: PathLike, min_rows: int, name: str) -> Dict[str, Any]:
    csv_path = _to_path(path)
    exists = csv_path.exists()
    row_count = count_csv_rows(csv_path)

    if not exists:
        return {
            "ok": False,
            "path": str(csv_path),
            "row_count": row_count,
            "min_rows": min_rows,
            "name": name,
            "reason": "file_not_found",
        }

    if row_count < min_rows:
        return {
            "ok": False,
            "path": str(csv_path),
            "row_count": row_count,
            "min_rows": min_rows,
            "name": name,
            "reason": "row_count_below_minimum",
        }

    return {
        "ok": True,
        "path": str(csv_path),
        "row_count": row_count,
        "min_rows": min_rows,
        "name": name,
        "reason": "ok",
    }


def validate_standard_results(path: PathLike, expected_rows: int = DEFAULT_EXPECTED_ROWS) -> Dict[str, Any]:
    csv_path = _to_path(path)
    row_count = count_csv_rows(csv_path)
    exists = csv_path.exists()
    ok = exists and row_count == expected_rows

    if not exists:
        reason = "file_not_found"
    elif row_count != expected_rows:
        reason = "row_count_mismatch"
    else:
        reason = "ok"

    return {
        "ok": ok,
        "path": str(csv_path),
        "row_count": row_count,
        "expected_rows": expected_rows,
        "name": "standard_esg_results",
        "reason": reason,
    }


def validate_merged_results(path: PathLike, expected_rows: int = DEFAULT_EXPECTED_ROWS) -> Dict[str, Any]:
    csv_path = _to_path(path)
    row_count = count_csv_rows(csv_path)
    exists = csv_path.exists()
    ok = exists and row_count == expected_rows

    if not exists:
        reason = "file_not_found"
    elif row_count != expected_rows:
        reason = "row_count_mismatch"
    else:
        reason = "ok"

    return {
        "ok": ok,
        "path": str(csv_path),
        "row_count": row_count,
        "expected_rows": expected_rows,
        "name": "merged_esg_results",
        "reason": reason,
    }


def collect_fieldnames(
    rows: List[Dict[str, Any]],
    preferred_order: Optional[Sequence[str]] = None,
) -> List[str]:
    all_keys = set()
    for row in rows:
        if isinstance(row, dict):
            all_keys.update(row.keys())

    if not all_keys:
        return list(preferred_order or [])

    ordered_keys: List[str] = []
    if preferred_order:
        ordered_keys.extend(key for key in preferred_order if key in all_keys)

    remaining_keys = sorted(key for key in all_keys if key not in ordered_keys)
    ordered_keys.extend(remaining_keys)
    return ordered_keys


def safe_write_csv(
    path: PathLike,
    rows: List[Dict[str, Any]],
    preferred_order: Optional[Sequence[str]] = None,
) -> None:
    csv_path = _to_path(path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = csv_path.with_suffix(csv_path.suffix + ".tmp")

    with open(tmp_path, "w", encoding="utf-8-sig", newline="") as f:
        if rows:
            fieldnames = collect_fieldnames(rows, preferred_order=preferred_order)
            writer = csv.DictWriter(
                f,
                fieldnames=fieldnames,
                extrasaction="ignore",
            )
            if fieldnames:
                writer.writeheader()
            writer.writerows(rows)

    tmp_path.replace(csv_path)


def safe_write_json(path: PathLike, data: Any) -> None:
    json_path = _to_path(path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = json_path.with_suffix(json_path.suffix + ".tmp")

    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    tmp_path.replace(json_path)
