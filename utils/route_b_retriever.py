import unicodedata
from typing import Any, Dict, List


def norm(value: Any) -> str:
    if value is None:
        return ""
    return (
        unicodedata.normalize("NFKC", str(value))
        .lower()
        .replace(" ", "")
        .replace("\n", "")
        .replace("\t", "")
    )


def retrieve_relevant_chunks(
    field_item: Dict[str, Any],
    chunks: List[Dict[str, Any]],
    top_k: int = 4,
) -> List[Dict[str, Any]]:
    keywords = []
    keywords.append(field_item.get("name_cn", ""))
    keywords.extend(field_item.get("aliases", []))
    keywords.extend(field_item.get("required_any", []))
    keywords = [keyword for keyword in dict.fromkeys(keywords) if keyword]

    scored = []
    for chunk in chunks:
        text = norm(chunk.get("text", ""))
        score = 0
        hit_keywords = []

        for keyword in keywords:
            keyword_norm = norm(keyword)
            if not keyword_norm:
                continue
            if keyword_norm in text:
                score += max(3, len(keyword_norm) // 2)
                hit_keywords.append(keyword)

        if "esg" in text and field_item.get("category") in {"E", "S", "G"}:
            score += 1

        if score > 0:
            scored.append({
                **chunk,
                "retrieval_score": score,
                "hit_keywords": hit_keywords,
            })

    scored.sort(key=lambda item: item["retrieval_score"], reverse=True)
    return scored[:top_k]
