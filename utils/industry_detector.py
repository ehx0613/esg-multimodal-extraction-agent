from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


INDUSTRY_KEYWORDS: Dict[str, List[Tuple[str, int]]] = {
    "finance": [
        ("银行", 3),
        ("保险", 3),
        ("证券", 3),
        ("信托", 3),
        ("贷款", 2),
        ("理财", 2),
        ("金融机构", 4),
    ],
    "pharma": [
        ("药业", 4),
        ("生物", 2),
        ("医疗器械", 4),
        ("制药", 4),
        ("临床", 2),
        ("医药", 4),
        ("医疗", 2),
    ],
    "manufacturing": [
        ("制造", 3),
        ("制冷", 4),
        ("化工", 4),
        ("氟化工", 5),
        ("氟材料", 5),
        ("含氟", 4),
        ("冷媒", 4),
        ("设备", 2),
        ("零件", 2),
        ("重工", 4),
        ("机械", 3),
        ("材料", 2),
        ("船舶", 4),
        ("新材", 3),
        ("钢", 2),
        ("一重", 4),
        ("黄金", 3),
        ("林海", 3),
    ],
    "service": [
        ("服务", 1),
        ("零售", 3),
        ("物业", 4),
        ("环卫", 4),
        ("城市运营", 4),
        ("供应链", 2),
        ("侨银", 4),
    ],
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
        score = sum(text.count(keyword) * weight for keyword, weight in keywords)
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
