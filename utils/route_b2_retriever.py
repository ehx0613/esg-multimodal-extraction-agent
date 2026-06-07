import unicodedata
import math
import re
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any, Dict, List

from config.settings import ROUTE_B2_USE_VECTOR_RAG, ROUTE_B2_VECTOR_TOP_K
from utils.rag_vector_store import FaissChunkVectorStore, build_query_text


NUMBER_RE = re.compile(r"\d+(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?")
YEAR_RE = re.compile(r"20[0-3][0-9]")


GENERIC_QUERY_TERMS = {
    "员工",
    "人数",
    "人次",
    "培训",
    "公司",
    "年度",
    "报告",
    "数量",
    "总量",
    "比例",
    "覆盖",
    "覆盖率",
    "投入",
    "次数",
    "会议",
    "排放",
    "能源",
    "用水",
    "用电",
}

GENERIC_UNIT_TERMS = {"人", "人次", "名", "次", "%", "度"}

FIELD_CONTEXT_FORBIDDEN = {
    "trained_employees_count": ["就业困难", "就业岗位", "再就业", "帮扶", "公益", "残疾人培训", "职业技能培训"],
    "training_total_hours": ["就业困难", "就业岗位", "再就业", "帮扶", "公益", "残疾人培训", "职业技能培训", "环保培训", "质量培训", "安全培训", "数据安全", "客户隐私"],
    "training_hours_per_employee": ["就业困难", "就业岗位", "再就业", "帮扶", "公益", "残疾人培训", "职业技能培训", "环保培训", "质量培训", "安全培训", "数据安全", "客户隐私"],
    "training_coverage_rate": ["就业困难", "就业岗位", "再就业", "帮扶", "公益", "残疾人培训", "职业技能培训"],
    "anti_corruption_training_participants": ["职业技能培训", "员工培训", "就业培训", "残疾人培训"],
    "anti_corruption_training_sessions": ["职业技能培训", "员工培训", "就业培训", "残疾人培训"],
}

FIELD_REQUIRE_STRONG_ANCHOR = {
    "trained_employees_count",
    "training_coverage_rate",
    "anti_corruption_training_participants",
    "anti_corruption_training_sessions",
}

FIELD_REQUIRE_KEYWORD = {
    "training_total_hours",
    "training_hours_per_employee",
}


FIELD_QUERY_EXPANSIONS = {
    "total_employees": ["在职员工数", "在职员工人数", "员工总人数", "员工总数", "雇员总数"],
    "board_size": ["董事会在任董事", "董事会董事人数", "董事会成员人数", "董事会人数"],
    "independent_directors": ["独立董事", "独董", "独立董事人数", "独立董事数量"],
    "total_ghg_emissions": [
        "温室气体排放总量",
        "温室气体排放量",
        "碳排放",
        "二氧化碳",
        "吨二氧化碳当量",
        "万吨二氧化碳当量",
        "tCO2e",
        "范围一",
        "范围二",
    ],
    "electricity_consumption": ["用电总量", "年度用电总量", "年度用电量", "耗电量", "千瓦时", "kWh", "度"],
    "water_consumption": ["用水总量", "用水量", "取水量", "耗水量", "立方米", "吨"],
    "wastewater_discharge": ["废水排放量", "污水排放量", "排放总量", "立方米", "吨"],
    "employee_medical_checkup_coverage": ["体检及健康档案覆盖率", "健康体检覆盖率", "员工体检覆盖率", "职业健康体检覆盖率"],
    "trained_employees_count": ["累计培训员工人次", "全年累计培训员工人次", "培训人次", "员工培训人次", "受训人次"],
    "training_total_hours": ["员工培训总时长", "培训总时长", "员工培训总小时数", "累计培训时长"],
    "training_hours_per_employee": ["员工接受培训人均时长", "员工培训人均时长", "人均培训时长", "员工平均培训时长"],
    "training_coverage_rate": ["员工培训覆盖率", "培训覆盖率"],
}


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


def tokenize_query(value: Any) -> List[str]:
    text = norm(value)
    if not text:
        return []

    parts = re.split(r"[_\-/|,，、;；:：()（）\[\]【】]+", text)
    tokens = [part for part in parts if len(part) >= 2]

    if re.search(r"[\u4e00-\u9fff]", text):
        tokens.extend(text[idx: idx + 2] for idx in range(max(len(text) - 1, 0)))
        tokens.extend(text[idx: idx + 3] for idx in range(max(len(text) - 2, 0)))
    else:
        tokens.extend(re.findall(r"[a-z0-9]{2,}", text))

    return _unique(tokens)


def has_number(text: str) -> bool:
    return bool(NUMBER_RE.search(text or ""))


def has_year(text: str) -> bool:
    return bool(YEAR_RE.search(text or ""))


def _unique(values: List[str]) -> List[str]:
    return [value for value in dict.fromkeys(values) if value]


def _is_generic_query_term(term: str) -> bool:
    term_norm = norm(term)
    if len(term_norm) <= 1:
        return True
    return term_norm in {norm(item) for item in GENERIC_QUERY_TERMS}


def _field_context_forbidden_hits(field_key: str, text: str) -> List[str]:
    return [
        word
        for word in FIELD_CONTEXT_FORBIDDEN.get(field_key, [])
        if norm(word) and norm(word) in text
    ]


def _strong_unit_hits(units: List[str]) -> List[str]:
    return [
        unit for unit in units
        if norm(unit) and norm(unit) not in {norm(item) for item in GENERIC_UNIT_TERMS}
    ]


def _build_query_terms(field_item: Dict[str, Any]) -> List[str]:
    phrases = _unique(
        [
            field_item.get("name_cn", ""),
            *field_item.get("aliases", []),
            *field_item.get("required_any", []),
            *FIELD_QUERY_EXPANSIONS.get(field_item.get("field_key", ""), []),
            field_item.get("field_key", "").replace("_", " "),
        ]
    )

    terms = []
    for phrase in phrases:
        phrase_norm = norm(phrase)
        if phrase_norm:
            terms.append(phrase_norm)
        terms.extend(tokenize_query(phrase))

    return _unique([term for term in terms if len(term) >= 2])


def _bm25_scores(query_terms: List[str], chunks: List[Dict[str, Any]]) -> Dict[str, float]:
    docs = []
    doc_freq = Counter()

    for chunk in chunks:
        chunk_id = str(chunk.get("chunk_id", ""))
        text = norm(chunk.get("text", ""))
        term_counts = Counter()

        for term in query_terms:
            count = text.count(term)
            if count:
                term_counts[term] = count
                doc_freq[term] += 1

        docs.append((chunk_id, term_counts))

    total_docs = max(len(chunks), 1)
    scores = {}
    for chunk_id, term_counts in docs:
        score = 0.0
        for term, tf in term_counts.items():
            df = doc_freq.get(term, 0)
            idf = math.log((total_docs - df + 0.5) / (df + 0.5) + 1)
            score += idf * ((tf * 2.2) / (tf + 1.2))
        if score:
            scores[chunk_id] = score

    return scores


def retrieve_quant_chunks(
    field_item: Dict[str, Any],
    chunks: List[Dict[str, Any]],
    top_k: int = 5,
    vector_index_dir: Path | None = None,
) -> List[Dict[str, Any]]:
    keywords = _unique(
        [
            field_item.get("name_cn", ""),
            *field_item.get("aliases", []),
            *field_item.get("required_any", []),
            *FIELD_QUERY_EXPANSIONS.get(field_item.get("field_key", ""), []),
        ]
    )
    query_terms = _build_query_terms(field_item)
    bm25_by_chunk = _bm25_scores(query_terms, chunks)
    vector_by_chunk: Dict[str, Dict[str, Any]] = {}

    if ROUTE_B2_USE_VECTOR_RAG and vector_index_dir is not None and chunks:
        query_text = build_query_text(
            field_item,
            extra_terms=FIELD_QUERY_EXPANSIONS.get(field_item.get("field_key", ""), []),
        )
        vector_hits = (
            FaissChunkVectorStore(vector_index_dir)
            .build_or_load(chunks)
            .search(query_text, top_k=max(ROUTE_B2_VECTOR_TOP_K, top_k))
        )
        vector_by_chunk = {
            str(hit.get("chunk_id", "")): hit
            for hit in vector_hits
            if hit.get("chunk_id")
        }

    forbidden = _unique(field_item.get("forbidden_any", []))
    unit_examples = _unique(field_item.get("unit_examples", []))
    field_key = str(field_item.get("field_key", ""))

    scored = []
    vector_scores = [
        float(hit.get("vector_score") or 0.0)
        for hit in vector_by_chunk.values()
        if hit.get("vector_score") is not None
    ]
    vector_floor = mean(vector_scores) if vector_scores else 0.0

    for chunk in chunks:
        if chunk.get("is_index_like"):
            continue

        raw_text = str(chunk.get("text", "") or "")
        text = norm(raw_text)
        if not has_number(raw_text):
            continue

        score = 0
        hit_keywords = []
        hit_query_terms = []
        hit_units = []
        hit_forbidden = []
        hit_context_forbidden = _field_context_forbidden_hits(field_key, text)

        for keyword in keywords:
            keyword_norm = norm(keyword)
            if keyword_norm and len(keyword_norm) >= 2 and keyword_norm in text:
                score += max(4, len(keyword_norm) // 2)
                if len(keyword_norm) >= 4:
                    score += 8
                hit_keywords.append(keyword)

        bm25_score = bm25_by_chunk.get(str(chunk.get("chunk_id", "")), 0.0)
        if bm25_score:
            score += min(int(round(bm25_score * 6)), 18)
            hit_query_terms = [term for term in query_terms if term in text][:12]
        non_generic_query_terms = [
            term for term in hit_query_terms
            if not _is_generic_query_term(term)
        ]

        vector_hit = vector_by_chunk.get(str(chunk.get("chunk_id", "")), {})
        vector_score = float(vector_hit.get("vector_score") or 0.0)
        if vector_score > 0:
            score += min(max(int(round(vector_score * 18)), 1), 18)

        for unit in unit_examples:
            unit_norm = norm(unit)
            if unit_norm and unit_norm in text:
                score += 3
                hit_units.append(unit)

        for word in forbidden:
            word_norm = norm(word)
            if word_norm and word_norm in text:
                score -= 8
                hit_forbidden.append(word)

        if hit_context_forbidden:
            score -= 18
            hit_forbidden.extend(hit_context_forbidden)

        if has_year(raw_text):
            score += 5

        number_count = len(NUMBER_RE.findall(raw_text))
        if number_count >= 3:
            score += min(number_count, 10)

        if "指标" in text and "单位" in text:
            score += 6

        if chunk.get("chunk_type") == "route_a_structured_row":
            score += 8
            if chunk.get("metric_name"):
                score += 4

        vector_candidate = bool(vector_by_chunk) and vector_score > 0 and vector_score >= vector_floor
        strong_vector_candidate = vector_candidate and vector_score >= max(vector_floor, 0.25)
        strong_units = _strong_unit_hits(hit_units)
        has_anchor = bool(hit_keywords or non_generic_query_terms or strong_units or strong_vector_candidate)
        if field_key in FIELD_REQUIRE_STRONG_ANCHOR and not (hit_keywords or strong_units):
            has_anchor = False
        if field_key in FIELD_REQUIRE_KEYWORD and not hit_keywords:
            has_anchor = False
        if score > 0 and has_anchor:
            scored.append(
                {
                    **chunk,
                    "retrieval_score": score,
                    "bm25_score": round(bm25_score, 4),
                    "vector_score": round(vector_score, 6) if vector_score else 0.0,
                    "hit_keywords": hit_keywords,
                    "hit_query_terms": hit_query_terms,
                    "hit_units": hit_units,
                    "hit_forbidden": hit_forbidden,
                    "number_count": number_count,
                }
            )

    scored.sort(key=lambda item: item["retrieval_score"], reverse=True)
    return scored[:top_k]
