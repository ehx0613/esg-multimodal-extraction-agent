import html
import os
import re
import shlex
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Dict, List

from utils.json_utils import load_json


def run_mineru_for_pdf(
    pdf_path: Path,
    configured_root: str,
    *,
    command_template: str,
    timeout_seconds: int,
) -> Dict[str, Any]:
    """Run a user-configured MinerU command and return structured diagnostics."""
    if not command_template.strip():
        return {"attempted": False, "status": "not_configured", "error": ""}
    output_root = Path(configured_root)
    output_root.mkdir(parents=True, exist_ok=True)
    command = command_template.format(pdf=str(Path(pdf_path).resolve()), output=str(output_root.resolve()))
    try:
        completed = subprocess.run(
            shlex.split(command, posix=os.name != "nt"),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
            check=False,
        )
        return {
            "attempted": True,
            "status": "completed" if completed.returncode == 0 else "failed",
            "return_code": completed.returncode,
            "stdout_tail": completed.stdout[-2000:],
            "stderr_tail": completed.stderr[-2000:],
            "error": "",
        }
    except Exception as exc:
        return {"attempted": True, "status": "exception", "error": str(exc)}


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: List[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in {"tr", "p", "br"}:
            self.parts.append("\n")
        elif tag in {"td", "th"}:
            self.parts.append(" | ")

    def handle_data(self, data: str) -> None:
        value = str(data or "").strip()
        if value:
            self.parts.append(value)

    def text(self) -> str:
        value = html.unescape("".join(self.parts))
        value = re.sub(r"[ \t]*\|[ \t]*", " | ", value)
        value = re.sub(r"\n{2,}", "\n", value)
        return value.strip(" |\n")


def html_to_plain_text(value: str) -> str:
    parser = _HTMLTextExtractor()
    parser.feed(str(value or ""))
    return parser.text()


def _source_signature(path: Path) -> str:
    stat = path.stat()
    return f"{path.resolve()}:{stat.st_size}:{stat.st_mtime_ns}"


def find_mineru_content_list(
    pdf_path: Path,
    output_dir: Path,
    configured_root: str = "",
) -> Path | None:
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    roots = [
        output_dir / "mineru",
        output_dir / "document" / "mineru",
    ]
    if configured_root:
        roots.append(Path(configured_root))

    expected_name = f"{pdf_path.stem}_content_list.json"
    for root in roots:
        if not root.exists():
            continue
        direct = root / expected_name
        if direct.exists():
            return direct
        matches = list(root.rglob(expected_name))
        if matches:
            return max(matches, key=lambda path: path.stat().st_mtime_ns)
    return None


def _text_from_item(item: Dict[str, Any]) -> str:
    item_type = str(item.get("type") or "")
    if item_type == "table":
        return html_to_plain_text(str(item.get("table_body") or ""))
    if item_type in {"image", "chart"}:
        captions = item.get("image_caption") or item.get("chart_caption") or []
        return "\n".join(str(value).strip() for value in captions if str(value).strip())
    return str(item.get("text") or "").strip()


def parse_mineru_content_list(content_list_path: Path) -> Dict[str, Any]:
    content_list_path = Path(content_list_path)
    items = load_json(content_list_path)
    if not isinstance(items, list):
        raise ValueError(f"MinerU content list must be a list: {content_list_path}")

    blocks: List[Dict[str, Any]] = []
    section_stack: List[str] = []
    page_type_counts: Dict[tuple[int, str], int] = {}

    for item in items:
        if not isinstance(item, dict):
            continue
        mineru_type = str(item.get("type") or "unknown")
        if mineru_type in {"header", "footer", "page_number"}:
            continue

        page_number = int(item.get("page_idx") or 0) + 1
        plain_text = _text_from_item(item)
        content_type = "title" if item.get("text_level") else mineru_type
        if content_type == "aside_text":
            content_type = "text"

        if content_type == "title" and plain_text:
            level = max(1, int(item.get("text_level") or 1))
            section_stack = section_stack[: level - 1]
            section_stack.append(plain_text)

        key = (page_number, content_type)
        index = page_type_counts.get(key, 0)
        page_type_counts[key] = index + 1
        raw_content = str(item.get("table_body") or item.get("text") or "")
        blocks.append(
            {
                "block_id": f"p{page_number}_{content_type}_{index}",
                "page_number": page_number,
                "content_type": content_type,
                "section_path": list(section_stack),
                "plain_text": plain_text,
                "raw_content": raw_content,
                "bbox": item.get("bbox"),
                "source_type": f"mineru_{mineru_type}",
                "metadata": {
                    "mineru_type": mineru_type,
                    "text_level": item.get("text_level"),
                    "table_caption": item.get("table_caption") or [],
                    "table_footnote": item.get("table_footnote") or [],
                    "image_path": item.get("img_path") or "",
                },
            }
        )

    return {
        "blocks": blocks,
        "parser_name": "mineru",
        "parser_version": os.getenv("MINERU_VERSION", "unknown"),
        "source_path": str(content_list_path),
        "source_signature": _source_signature(content_list_path),
    }
