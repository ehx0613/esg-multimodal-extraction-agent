import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config.core_schema import CORE_SCHEMA, schema_summary


OUTPUT_DIR = PROJECT_ROOT / "docs" / "schema"
JSON_PATH = OUTPUT_DIR / "core_schema_readable.json"
MD_PATH = OUTPUT_DIR / "core_schema_readable.md"


def _json_dump(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def build_markdown() -> str:
    summary = schema_summary()
    lines: list[str] = []

    lines.append("# Core Schema Readable Export")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Total: {summary['total']}")
    lines.append(f"- Quantitative: {summary['quantitative']}")
    lines.append(f"- Qualitative: {summary['qualitative']}")
    lines.append(f"- E: {summary['E']}")
    lines.append(f"- S: {summary['S']}")
    lines.append(f"- G: {summary['G']}")
    lines.append("")
    lines.append("## Fields")
    lines.append("")

    for idx, item in enumerate(CORE_SCHEMA, start=1):
        lines.append(f"### {idx}. `{item['field_key']}`")
        lines.append("")
        lines.append(f"- `name_cn`: {item.get('name_cn', '')}")
        lines.append(f"- `category`: {item.get('category', '')}")
        lines.append(f"- `indicator_type`: {item.get('indicator_type', '')}")
        lines.append(f"- `value_type`: {item.get('value_type', '')}")
        lines.append(f"- `preferred_source`: {item.get('preferred_source', '')}")
        lines.append(f"- `unit_type`: {item.get('unit_type', '')}")
        lines.append(f"- `unit_required`: {item.get('unit_required', '')}")
        lines.append(f"- `year_required`: {item.get('year_required', '')}")
        lines.append(f"- `aliases`: {_json_dump(item.get('aliases', []))}")
        lines.append(f"- `required_any`: {_json_dump(item.get('required_any', []))}")
        lines.append(f"- `forbidden_any`: {_json_dump(item.get('forbidden_any', []))}")
        lines.append(f"- `unit_examples`: {_json_dump(item.get('unit_examples', []))}")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(CORE_SCHEMA, f, ensure_ascii=False, indent=2)

    with open(MD_PATH, "w", encoding="utf-8") as f:
        f.write(build_markdown())

    print(f"Readable JSON written to: {JSON_PATH}")
    print(f"Readable Markdown written to: {MD_PATH}")


if __name__ == "__main__":
    main()
