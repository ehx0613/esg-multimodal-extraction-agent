from pathlib import Path
from typing import List, Dict, Any

import fitz


def extract_pdf_text_by_page(pdf_path: Path) -> List[Dict[str, Any]]:
    """
    从 PDF 文本层抽取每页正文。

    注意：
    - 文本型 PDF 可用；
    - 扫描型 / 图片型 PDF 可能抽不到文字；
    - 如果整份 PDF 几乎无文本，路线 B 会标记为 unavailable。
    """

    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(f"找不到 PDF 文件: {pdf_path}")

    pages = []

    with fitz.open(str(pdf_path)) as doc:
        for idx, page in enumerate(doc):
            text = page.get_text("text") or ""

            text = (
                text.replace("\x00", "")
                .replace("\r", "\n")
                .strip()
            )

            pages.append({
                "page_number": idx + 1,
                "text": text,
                "char_count": len(text),
            })

    return pages


def has_enough_text_layer(pages: List[Dict[str, Any]], min_total_chars: int = 1000) -> bool:
    total_chars = sum(page.get("char_count", 0) for page in pages)
    return total_chars >= min_total_chars