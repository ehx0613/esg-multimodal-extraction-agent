from pathlib import Path
from typing import Any, Dict, Iterable, List


INDUSTRY_KEYWORDS = {
    "finance": ["银行", "保险", "证券", "信托", "贷款", "理财", "金融机构"],
    "pharma": ["药业", "生物", "医疗器械", "制药", "临床", "医药", "医疗"],
    "manufacturing": ["制造", "设备", "零件", "重工", "机械", "材料", "船舶", "新材", "钢", "一重", "黄金", "林海"],
    "service": ["服务", "零售", "物业", "环卫", "城市运营", "供应链", "侨银"],
}


def _page_texts_to_text(pages: Iterable[Dict[str, Any]], max_chars: int = 2000) -> str:
    parts: List[str] = []
    for page in pages:
        if not isinstance(page, dict):
            continue
        text = str(page.get("text", "") or "")
        if text:
            parts.append(text)
        joined = "\n".join(parts)
        if len(joined) >= max_chars:
            return joined[:max_chars]
    return "\n".join(parts)[:max_chars]


def detect_industry_from_text(text: str) -> str:
    text = str(text or "")
    scores = {}
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        score = sum(text.count(keyword) for keyword in keywords)
        if score:
            scores[industry] = score

    if not scores:
        return "general"
    return max(scores.items(), key=lambda item: item[1])[0]


def detect_industry(report_name: str = "", pages: Iterable[Dict[str, Any]] | None = None) -> str:
    text = str(report_name or "")
    if pages:
        text = f"{text}\n{_page_texts_to_text(pages)}"
    return detect_industry_from_text(text)


def detect_industry_from_report_dir(report_dir: Path) -> str:
    report_dir = Path(report_dir)
    text = report_dir.name
    page_texts_path = report_dir / "ingest" / "page_texts.json"
    if page_texts_path.exists():
        try:
            import json

            pages = json.loads(page_texts_path.read_text(encoding="utf-8"))
            text = f"{text}\n{_page_texts_to_text(pages)}"
        except Exception:
            pass
    return detect_industry_from_text(text)
