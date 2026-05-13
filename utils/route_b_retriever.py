from typing import List, Dict, Any


def norm(value) -> str:
    if value is None:
        return ""

    return (
        str(value)
        .lower()
        .replace(" ", "")
        .replace("\n", "")
        .replace("\t", "")
        .replace("（", "(")
        .replace("）", ")")
    )


def retrieve_relevant_chunks(
    field_item: Dict[str, Any],
    chunks: List[Dict[str, Any]],
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """
    简单关键词召回。

    根据：
    - name_cn
    - aliases
    - required_any
    去正文 chunks 里找相关片段。
    """

    keywords = []

    keywords.append(field_item.get("name_cn", ""))

    keywords.extend(field_item.get("aliases", []))
    keywords.extend(field_item.get("required_any", []))

    keywords = [kw for kw in keywords if kw]

    scored = []

    for chunk in chunks:
        text = norm(chunk.get("text", ""))

        score = 0
        hit_keywords = []

        for kw in keywords:
            kw_norm = norm(kw)

            if not kw_norm:
                continue

            if kw_norm in text:
                score += max(3, len(kw_norm) // 2)
                hit_keywords.append(kw)

        # 一些通用 ESG 治理机制加权
        if field_item["field_key"] == "board_esg_oversight":
            for kw in ["董事会", "esg", "可持续发展", "社会责任"]:
                if norm(kw) in text:
                    score += 2

        if field_item["field_key"] == "esg_committee":
            for kw in ["委员会", "工作小组", "esg", "可持续发展"]:
                if norm(kw) in text:
                    score += 2

        if field_item["field_key"] == "anti_corruption_policy":
            for kw in ["反腐败", "反贪污", "廉洁", "商业道德", "反舞弊"]:
                if norm(kw) in text:
                    score += 2

        if field_item["field_key"] == "whistleblowing_mechanism":
            for kw in ["举报", "投诉", "申诉", "热线", "邮箱"]:
                if norm(kw) in text:
                    score += 2

        if field_item["field_key"] == "supplier_esg_assessment":
            for kw in ["供应商", "审核", "评估", "社会责任", "环境"]:
                if norm(kw) in text:
                    score += 2

        if score > 0:
            scored.append({
                **chunk,
                "retrieval_score": score,
                "hit_keywords": hit_keywords,
            })

    scored.sort(key=lambda x: x["retrieval_score"], reverse=True)

    return scored[:top_k]