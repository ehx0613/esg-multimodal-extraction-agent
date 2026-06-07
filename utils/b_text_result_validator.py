import unicodedata
from typing import Any, Dict, List


def _norm(value: Any) -> str:
    return (
        unicodedata.normalize("NFKC", str(value or ""))
        .lower()
        .replace(" ", "")
        .replace("\n", "")
        .replace("\t", "")
    )


def _candidate_pages(chunks: List[Dict[str, Any]]) -> set[str]:
    return {
        str(chunk.get("page_number"))
        for chunk in chunks
        if chunk.get("page_number") not in {None, ""}
    }


def _ngram_coverage(evidence: str, chunks: List[Dict[str, Any]], n: int = 4) -> float:
    evidence_norm = _norm(evidence)
    candidate_text = "".join(_norm(chunk.get("text", "")) for chunk in chunks)
    if len(evidence_norm) < n:
        return 1.0 if evidence_norm and evidence_norm in candidate_text else 0.0

    grams = {
        evidence_norm[idx: idx + n]
        for idx in range(len(evidence_norm) - n + 1)
    }
    if not grams:
        return 0.0
    return sum(gram in candidate_text for gram in grams) / len(grams)


def validate_route_b_text_result(
    field_item: Dict[str, Any],
    result: Dict[str, Any],
    chunks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    result["llm_matched_raw"] = bool(result.get("matched"))
    result["llm_confidence_raw"] = result.get("confidence", 0.0)
    result.setdefault("matched", False)
    result.setdefault("field_key", field_item["field_key"])
    result.setdefault("value", None)
    result.setdefault("summary", "")
    result.setdefault("evidence", "")
    result.setdefault("source_pages", [])
    result.setdefault("confidence", 0.0)
    result.setdefault("reason", "")

    if not result.get("matched"):
        result["route_b_validation_ok"] = False
        result["route_b_validation_reason"] = result.get("reason") or "not_matched"
        return result

    reasons: List[str] = []
    if str(result.get("field_key", "")) != str(field_item["field_key"]):
        reasons.append("field_key_mismatch")

    try:
        confidence = float(result.get("confidence", 0.0) or 0.0)
    except Exception:
        confidence = -1.0
    if not 0.0 <= confidence <= 1.0:
        reasons.append("confidence_out_of_range")
    result["confidence"] = confidence if confidence >= 0 else 0.0

    evidence = str(result.get("evidence", "") or "")
    evidence_norm = _norm(evidence)
    candidate_texts = [_norm(chunk.get("text", "")) for chunk in chunks]
    evidence_coverage = _ngram_coverage(evidence, chunks)
    result["evidence_ngram_coverage"] = round(evidence_coverage, 4)
    if not evidence_norm:
        reasons.append("missing_evidence")
    elif not any(evidence_norm in text for text in candidate_texts) and evidence_coverage < 0.55:
        reasons.append("evidence_not_in_retrieved_chunks")

    source_pages = result.get("source_pages", [])
    if not isinstance(source_pages, list):
        reasons.append("source_pages_not_list")
        source_pages = []
    candidate_pages = _candidate_pages(chunks)
    if not source_pages:
        reasons.append("missing_source_pages")
    elif any(str(page) not in candidate_pages for page in source_pages):
        reasons.append("source_page_outside_retrieved_chunks")

    forbidden_hits = [
        str(term)
        for term in field_item.get("forbidden_any", []) or []
        if _norm(term) and _norm(term) in evidence_norm
    ]
    if forbidden_hits:
        reasons.append(f"forbidden_hit:{','.join(forbidden_hits[:3])}")

    if reasons:
        result["matched"] = False
        result["value"] = None
        result["confidence"] = 0.0
        result["route_b_validation_ok"] = False
        result["route_b_validation_reason"] = ";".join(reasons)
        result["reason"] = f"route_b_validation_failed:{result['route_b_validation_reason']}"
        return result

    result["route_b_validation_ok"] = True
    result["route_b_validation_reason"] = ""
    return result
