import re
from typing import Any


import unicodedata

def norm(v):
    if v is None:
        return ""

    text = unicodedata.normalize("NFKC", str(v))

    return (
        text.lower()
        .replace(" ", "")
        .replace("\n", "")
        .replace("\t", "")
        .replace("（", "(")
        .replace("）", ")")
        .replace("：", ":")
        .replace("，", ",")
    )


def parse_number(v: Any):
    if v is None:
        return None
    s = str(v).strip()
    if s in {"", "/", "-", "—", "N/A", "NA", "不适用", "未披露"}:
        return None
    s2 = s.replace(",", "").replace("，", "").replace("%", "")
    if s2.endswith("+"):
        return s
    try:
        n = float(s2)
        return int(n) if n.is_integer() else n
    except Exception:
        return s


def choose_latest_year_value(values: dict):
    if not isinstance(values, dict) or not values:
        return None, None, None
    candidates = []
    for k, v in values.items():
        m = re.search(r"20[0-3][0-9]", str(k))
        if m:
            candidates.append((int(m.group(0)), str(k), v))
    if candidates:
        return sorted(candidates, key=lambda x: x[0], reverse=True)[0]
    k = list(values.keys())[-1]
    return None, str(k), values[k]
