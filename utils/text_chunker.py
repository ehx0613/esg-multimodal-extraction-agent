from typing import List, Dict, Any


def chunk_pages(
    pages: List[Dict[str, Any]],
    chunk_size: int = 800,
    overlap: int = 120,
) -> List[Dict[str, Any]]:
    """
    按页切 chunk。

    第一版不做复杂向量库，只保证：
    - 保留 page_number
    - 每个 chunk 有 source_page
    - 后面可以给 qwen-plus 做 evidence
    """

    chunks = []

    for page in pages:
        page_number = page.get("page_number")
        text = page.get("text", "")

        if not text:
            continue

        start = 0
        text_len = len(text)

        while start < text_len:
            end = min(start + chunk_size, text_len)
            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append({
                    "chunk_id": f"p{page_number}_{len(chunks)}",
                    "page_number": page_number,
                    "text": chunk_text,
                })

            if end >= text_len:
                break

            start = max(0, end - overlap)

    return chunks