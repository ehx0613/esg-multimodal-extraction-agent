import hashlib
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict

from utils.json_utils import load_json
from utils.result_guard import safe_write_json


# Bump whenever deterministic matcher/validator policy changes. Otherwise an
# old rejected result can keep overriding newly added high-precision rules.
SCHEMA_MATCH_CACHE_VERSION = "normalized_row_v1_policy_v5_global_atoms_units"


def _normalize(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    return re.sub(r"[\s\W_]+", "", text)


def row_hash(row: Dict[str, Any]) -> str:
    normalized = {
        "metric_name": _normalize(row.get("metric_name") or row.get("row_label")),
        "topic": _normalize(row.get("topic") or row.get("topic_label")),
        "table_title": _normalize(row.get("table_title")),
        "unit": _normalize(row.get("unit")),
        "values": {
            _normalize(key): _normalize(value)
            for key, value in sorted((row.get("values") or {}).items(), key=lambda item: str(item[0]))
        },
        "evidence_text": _normalize(row.get("evidence_text")),
    }
    payload = json.dumps(normalized, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class SchemaMatchCache:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.entries: Dict[str, Dict[str, Any]] = {}
        if self.path.exists():
            data = load_json(self.path)
            if data.get("version") == SCHEMA_MATCH_CACHE_VERSION:
                self.entries = dict(data.get("entries") or {})

    def get(self, key: str) -> Dict[str, Any] | None:
        return self.entries.get(key)

    def put(self, key: str, result: Dict[str, Any]) -> None:
        self.entries[key] = result

    def save(self) -> None:
        safe_write_json(
            self.path,
            {"version": SCHEMA_MATCH_CACHE_VERSION, "entries": self.entries},
        )
