import re
from pathlib import Path
from typing import Any, Dict, List

from config.settings import (
    MINERU_FALLBACK_TO_PYMUPDF,
    MINERU_AUTO_RUN_ENABLED,
    MINERU_AUTO_RUN_TIMEOUT_SECONDS,
    MINERU_COMMAND,
    MINERU_OUTPUT_ROOT,
    PDF_PARSER_BACKEND,
    ROUTE_A_INCLUDE_CHART_PAGES,
    ROUTE_A_TAIL_START_RATIO,
    ROUTE_B_CHUNK_OVERLAP,
    ROUTE_B_CHUNK_SIZE,
    ROUTE_B_CHUNK_STRATEGY,
    ROUTE_B_SEMANTIC_BLOCK_OVERLAP,
    ROUTE_B_SEMANTIC_MAX_SIZE,
    ROUTE_B_SEMANTIC_MIN_SIZE,
    ROUTE_B_SEMANTIC_TARGET_SIZE,
)
from utils.document_model import (
    build_document_model,
    chunk_document_blocks,
    document_blocks_to_pages,
    pages_to_document_blocks,
    document_blocks_to_markdown,
)
from utils.json_utils import load_json, save_json
from utils.mineru_parser import find_mineru_content_list, parse_mineru_content_list, run_mineru_for_pdf
from utils.pdf_text_utils import extract_pdf_text_by_page, has_enough_text_layer
from utils.pdf_utils import INDEX_NEGATIVE_WORDS, METRIC_WORDS, TITLE_PATTERNS, UNIT_WORDS, expand_page_indices, normalize_text
from utils.semantic_text_chunker import chunk_pages_semantic_esg
from utils.text_chunker import chunk_pages


DEFAULT_ROUTE_A_TOP_K = 3
DEFAULT_ROUTE_A_EXPAND_BEFORE = 1
DEFAULT_ROUTE_A_EXPAND_AFTER = 2
INGEST_VERSION = "document_model_v1_1_mineru_adapter_v2"

STRONG_PERFORMANCE_TITLE_WORDS = [
    "关键绩效",
    "主要绩效",
    "绩效表",
    "绩效数据",
    "ESG绩效",
    "ESG数据",
    "ESG关键绩效",
    "环境绩效",
    "社会绩效",
    "治理绩效",
    "可持续发展绩效",
]

INDEX_NEGATIVE_EXTRA_WORDS = [
    "指标索引",
    "内容索引",
    "GRI",
    "CASS",
    "联交所",
    "披露索引",
    "指引索引",
    "意见反馈",
    "读者反馈",
]

TABLE_HEADER_WORDS = [
    "指标",
    "单位",
    "项目",
    "类别",
    "本年度",
    "上年度",
]

CHART_PERFORMANCE_WORDS = [
    "员工组成",
    "员工构成",
    "员工结构",
    "人员构成",
    "按性别划分",
    "按学历划分",
    "按年龄划分",
    "男性",
    "女性",
    "博士",
    "硕士",
    "本科",
    "30岁以下",
    "30-40岁",
    "40-50岁",
    "50岁及以上",
    "饼图",
    "环形图",
    "占比",
    "比例",
]

ESG_UNIT_PATTERNS = {
    "percentage": r"%",
    "ghg": r"(?:吨|万?吨)?(?:co2e|CO2e|二氧化碳当量)|tCO2e",
    "energy_power": r"万?千瓦时|兆瓦时|kwh|KWh|kWh|mwh|MWh",
    "energy_coal": r"吨标煤|吨标准煤|万吨标准煤",
    "volume": r"万?立方米|m3|m³",
    "mass": r"千克|公斤|(?<!标煤)(?<!标准煤)吨",
    "money": r"亿元|万元|人民币元|元",
    "person": r"人次|人数|员工|人",
    "time": r"小时|学时|工时",
    "count": r"次|件|项|起|场|宗|家",
}


def _hits_from_patterns(patterns: List[str], text: str) -> List[str]:
    return [pattern for pattern in patterns if re.search(pattern, text, re.I)]


def _hits_from_words(words: List[str], text: str) -> List[str]:
    return [word for word in words if normalize_text(word) in text]


def _line_table_density(raw_text: str) -> Dict[str, int]:
    table_like_lines = 0
    numeric_lines = 0

    for line in str(raw_text or "").splitlines():
        line = line.strip()
        if not line:
            continue

        number_hits = re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?", line)
        if number_hits:
            numeric_lines += 1
        if len(number_hits) >= 2 or ("\t" in line and number_hits):
            table_like_lines += 1

    return {
        "numeric_lines": numeric_lines,
        "table_like_lines": table_like_lines,
    }


def _unit_density(raw_text: str) -> Dict[str, Any]:
    text = str(raw_text or "")
    normalized = normalize_text(text)
    hits = {}

    for unit_name, pattern in ESG_UNIT_PATTERNS.items():
        matches = re.findall(pattern, normalized, re.I)
        if matches:
            hits[unit_name] = len(matches)

    return {
        "unit_density_score": len(hits),
        "unit_occurrence_count": sum(hits.values()),
        "distinct_unit_categories": sorted(hits),
    }


def build_page_features(pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    total_pages = len(pages)
    features = []

    for page in pages:
        page_number = int(page.get("page_number") or 0)
        raw_text = page.get("text", "")
        text = normalize_text(raw_text)

        title_hits = _hits_from_patterns(TITLE_PATTERNS, text)
        strong_title_hits = _hits_from_words(STRONG_PERFORMANCE_TITLE_WORDS, text)
        metric_hits = _hits_from_words(METRIC_WORDS, text)
        unit_hits = _hits_from_words(UNIT_WORDS, text)
        table_header_hits = _hits_from_words(TABLE_HEADER_WORDS, text)
        chart_hits = _hits_from_words(CHART_PERFORMANCE_WORDS, text)
        index_hits = sorted(set(_hits_from_words(INDEX_NEGATIVE_WORDS, text) + _hits_from_words(INDEX_NEGATIVE_EXTRA_WORDS, text)))
        year_hits = sorted(set(re.findall(r"20[0-3][0-9]", str(raw_text or ""))))
        number_count = len(re.findall(r"\d+(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?", str(raw_text or "")))
        line_density = _line_table_density(raw_text)
        unit_density = _unit_density(raw_text)
        numeric_lines = line_density["numeric_lines"]
        table_like_lines = line_density["table_like_lines"]
        unit_density_score = unit_density["unit_density_score"]
        unit_occurrence_count = unit_density["unit_occurrence_count"]
        distinct_unit_categories = unit_density["distinct_unit_categories"]
        page_ratio = page_number / total_pages if total_pages else 0

        score = 0
        reasons = []

        if title_hits:
            score += len(title_hits) * 12
            reasons.append(f"title_hits:{','.join(title_hits[:8])}")

        if strong_title_hits:
            score += len(strong_title_hits) * 18
            reasons.append(f"strong_title_hits:{','.join(strong_title_hits[:8])}")

        if metric_hits:
            score += min(len(metric_hits), 15) * 4
            reasons.append(f"metric_hits:{','.join(metric_hits[:15])}")

        if unit_hits:
            score += min(len(unit_hits), 12) * 2
            reasons.append(f"unit_hits:{','.join(unit_hits[:12])}")

        if unit_density_score:
            score += min(unit_density_score, 8) * 4
            reasons.append(f"unit_density:{unit_density_score}:{','.join(distinct_unit_categories[:8])}")

        if unit_occurrence_count >= 12:
            score += min(unit_occurrence_count // 6, 5) * 2
            reasons.append(f"unit_occurrences:{unit_occurrence_count}")

        if year_hits:
            score += min(len(year_hits), 3) * 4
            reasons.append(f"year_hits:{','.join(year_hits)}")

        if table_header_hits:
            score += min(len(table_header_hits), 4) * 4
            reasons.append(f"table_header_hits:{','.join(table_header_hits[:6])}")

        if chart_hits:
            score += min(len(chart_hits), 10) * 6
            reasons.append(f"chart_hits:{','.join(chart_hits[:10])}")

        if "指标" in text and "单位" in text and re.search(r"20[0-3][0-9]", text):
            score += 18
            reasons.append("table_header:indicator_unit_year")

        if number_count >= 20:
            score += min(number_count // 20, 6) * 3
            reasons.append(f"number_dense:{number_count}")

        if table_like_lines >= 3:
            score += min(table_like_lines, 8) * 3
            reasons.append(f"table_density:{table_like_lines}")

        if numeric_lines >= 8:
            score += min(numeric_lines // 4, 5) * 2
            reasons.append(f"numeric_lines:{numeric_lines}")

        if total_pages and page_ratio >= ROUTE_A_TAIL_START_RATIO:
            score += 10
            reasons.append("tail_35_percent")

        if total_pages and page_ratio >= 0.80:
            score += 4
            reasons.append("tail_20_percent")

        if total_pages and page_ratio < 0.30 and not strong_title_hits:
            score -= 8
            reasons.append("early_page_penalty")

        if index_hits:
            penalty = 24 if number_count < 20 or len(unit_hits) < 2 else 10
            score -= penalty
            reasons.append(f"index_penalty:{','.join(index_hits[:5])}")

        in_route_a_tail = bool(total_pages and page_ratio >= ROUTE_A_TAIL_START_RATIO)
        force_keep = in_route_a_tail and bool(strong_title_hits) and (
            number_count >= 5 or table_like_lines >= 2
        )
        high_unit_density = in_route_a_tail and unit_density_score >= 5 and number_count >= 20
        chart_force_keep = bool(chart_hits) and (
            "%" in str(raw_text or "")
            or number_count >= 3
            or any(word in str(raw_text or "") for word in ["男性", "女性", "按性别", "按学历", "按年龄"])
        )

        if force_keep:
            reasons.append("force_keep:strong_performance_title")
        if high_unit_density:
            reasons.append("force_keep:high_unit_density")
        if chart_force_keep and ROUTE_A_INCLUDE_CHART_PAGES:
            reasons.append("force_keep:chart_performance_page")
        elif chart_force_keep:
            reasons.append("chart_candidate_for_b2")

        features.append(
            {
                "page_number": page_number,
                "char_count": page.get("char_count", 0),
                "score": score,
                "title_hits": title_hits,
                "strong_title_hits": strong_title_hits,
                "metric_hits": metric_hits,
                "unit_hits": unit_hits,
                "unit_density_score": unit_density_score,
                "unit_occurrence_count": unit_occurrence_count,
                "distinct_unit_categories": distinct_unit_categories,
                "table_header_hits": table_header_hits,
                "chart_hits": chart_hits,
                "year_hits": year_hits,
                "number_count": number_count,
                "numeric_lines": numeric_lines,
                "table_like_lines": table_like_lines,
                "page_ratio": round(page_ratio, 4),
                "in_route_a_tail": in_route_a_tail,
                "index_hits": index_hits,
                "force_keep": force_keep or high_unit_density or (chart_force_keep and ROUTE_A_INCLUDE_CHART_PAGES),
                "high_unit_density": high_unit_density,
                "chart_force_keep": chart_force_keep,
                "reasons": reasons,
            }
        )

    return features


def select_route_a_candidate_pages(
    page_features: List[Dict[str, Any]],
    top_k: int = DEFAULT_ROUTE_A_TOP_K,
    min_score: int = 25,
    expand_before: int = DEFAULT_ROUTE_A_EXPAND_BEFORE,
    expand_after: int = DEFAULT_ROUTE_A_EXPAND_AFTER,
) -> Dict[str, Any]:
    total_pages = len(page_features)
    candidates = [
        feature for feature in page_features
        if (
            int(feature.get("score", 0)) >= min_score
            and bool(feature.get("in_route_a_tail"))
        )
        or bool(feature.get("force_keep"))
    ]
    candidates.sort(key=lambda item: item.get("score", 0), reverse=True)
    selected_by_page = {}
    for feature in candidates[:top_k]:
        selected_by_page[int(feature.get("page_number") or 0)] = feature
    selected = sorted(
        selected_by_page.values(),
        key=lambda item: item.get("score", 0),
        reverse=True,
    )

    selected_indices = [
        int(item["page_number"]) - 1
        for item in selected
        if item.get("page_number")
    ]

    expanded_indices = expand_page_indices(
        selected_indices,
        total_pages=total_pages,
        before=expand_before,
        after=expand_after,
    )
    expanded_numbers = [idx + 1 for idx in expanded_indices]

    return {
        "found": bool(expanded_numbers),
        "total_pages": total_pages,
        "candidates": selected,
        "expanded_page_numbers": expanded_numbers,
        "candidate_pages": expanded_numbers,
        "selection_strategy": {
            "source": "pdf_ingest_page_features",
            "top_k": top_k,
            "min_score": min_score,
            "tail_start_ratio": ROUTE_A_TAIL_START_RATIO,
            "expand_before": expand_before,
            "expand_after": expand_after,
        },
    }


def _file_signature(path: Path) -> str:
    path = Path(path)
    if not path.exists():
        return f"missing:{path}"
    stat = path.stat()
    return f"{path.resolve()}:{stat.st_size}:{stat.st_mtime_ns}"


def _select_parser_source(
    pdf_path: Path,
    output_dir: Path,
    *,
    parser_backend: str,
    mineru_output_root: str,
) -> Dict[str, Any]:
    parser_backend = str(parser_backend or "auto").lower()
    if parser_backend not in {"auto", "mineru", "pymupdf"}:
        raise ValueError(f"Unsupported PDF_PARSER_BACKEND: {parser_backend}")

    mineru_path = None
    mineru_run = {"attempted": False, "status": "not_requested", "error": ""}
    if parser_backend in {"auto", "mineru"}:
        mineru_path = find_mineru_content_list(pdf_path, output_dir, mineru_output_root)
        if not mineru_path and MINERU_AUTO_RUN_ENABLED:
            mineru_run = run_mineru_for_pdf(
                pdf_path,
                mineru_output_root,
                command_template=MINERU_COMMAND,
                timeout_seconds=MINERU_AUTO_RUN_TIMEOUT_SECONDS,
            )
            mineru_path = find_mineru_content_list(pdf_path, output_dir, mineru_output_root)
    if mineru_path:
        return {
            "parser_name": "mineru",
            "source_path": str(mineru_path),
            "source_signature": _file_signature(mineru_path),
            "selection_reason": "mineru_content_list_available",
            "mineru_run": mineru_run,
        }
    if parser_backend == "mineru" and not MINERU_FALLBACK_TO_PYMUPDF:
        raise FileNotFoundError(f"MinerU content_list.json not found for: {pdf_path}")
    return {
        "parser_name": "pymupdf",
        "source_path": str(pdf_path),
        "source_signature": _file_signature(pdf_path),
        "selection_reason": (
            "mineru_auto_run_failed_fallback"
            if mineru_run.get("attempted")
            else "mineru_content_list_not_found_fallback"
        ),
        "mineru_run": mineru_run,
    }


def ingest_pdf(
    pdf_path: Path,
    output_dir: Path,
    force: bool = False,
    chunk_size: int = ROUTE_B_CHUNK_SIZE,
    chunk_overlap: int = ROUTE_B_CHUNK_OVERLAP,
    chunk_strategy: str = ROUTE_B_CHUNK_STRATEGY,
    parser_backend: str = PDF_PARSER_BACKEND,
    mineru_output_root: str = MINERU_OUTPUT_ROOT,
) -> Dict[str, Any]:
    pdf_path = Path(pdf_path)
    output_dir = Path(output_dir)
    ingest_dir = output_dir / "ingest"
    ingest_dir.mkdir(parents=True, exist_ok=True)

    page_texts_path = ingest_dir / "page_texts.json"
    page_features_path = ingest_dir / "page_features.json"
    text_chunks_path = ingest_dir / "text_chunks.json"
    document_blocks_path = ingest_dir / "document_blocks.json"
    document_model_path = ingest_dir / "document_model.json"
    markdown_path = ingest_dir / "document.md"
    manifest_path = ingest_dir / "ingest_manifest.json"
    parser_source = _select_parser_source(
        pdf_path,
        output_dir,
        parser_backend=parser_backend,
        mineru_output_root=mineru_output_root,
    )

    if (
        not force
        and page_texts_path.exists()
        and page_features_path.exists()
        and text_chunks_path.exists()
        and document_blocks_path.exists()
        and document_model_path.exists()
        and manifest_path.exists()
    ):
        manifest = load_json(manifest_path)
        if (
            manifest.get("ingest_version") != INGEST_VERSION
            or manifest.get("chunk_strategy") != chunk_strategy
            or int(manifest.get("chunk_size", -1)) != int(chunk_size)
            or int(manifest.get("chunk_overlap", -1)) != int(chunk_overlap)
            or manifest.get("parser_name") != parser_source["parser_name"]
            or manifest.get("parser_source_signature") != parser_source["source_signature"]
        ):
            force = True

    if (
        not force
        and page_texts_path.exists()
        and page_features_path.exists()
        and text_chunks_path.exists()
        and document_blocks_path.exists()
        and document_model_path.exists()
        and manifest_path.exists()
    ):
        return {
            "manifest": load_json(manifest_path),
            "pages": load_json(page_texts_path),
            "page_features": load_json(page_features_path),
            "chunks": load_json(text_chunks_path),
            "blocks": load_json(document_blocks_path),
            "document_model": load_json(document_model_path),
            "cache_used": True,
            "paths": {
                "page_texts": str(page_texts_path),
                "page_features": str(page_features_path),
                "text_chunks": str(text_chunks_path),
                "document_blocks": str(document_blocks_path),
                "document_model": str(document_model_path),
                "markdown": str(markdown_path),
                "manifest": str(manifest_path),
            },
        }

    if parser_source["parser_name"] == "mineru":
        parsed = parse_mineru_content_list(Path(parser_source["source_path"]))
        blocks = parsed["blocks"]
        pages = document_blocks_to_pages(blocks)
        parser_version = parsed["parser_version"]
        chunker_name = "document_blocks_v1"
    else:
        pages = extract_pdf_text_by_page(pdf_path)
        blocks = pages_to_document_blocks(pages)
        parser_version = "pymupdf"
        chunker_name = chunk_strategy

    page_features = build_page_features(pages)
    if parser_source["parser_name"] == "mineru" and chunk_strategy == "semantic_esg_v1":
        chunks = chunk_document_blocks(
            blocks,
            target_size=ROUTE_B_SEMANTIC_TARGET_SIZE,
            max_size=ROUTE_B_SEMANTIC_MAX_SIZE,
        )
    elif chunk_strategy == "semantic_esg_v1":
        chunks = chunk_pages_semantic_esg(
            pages,
            target_size=ROUTE_B_SEMANTIC_TARGET_SIZE,
            min_size=ROUTE_B_SEMANTIC_MIN_SIZE,
            max_size=ROUTE_B_SEMANTIC_MAX_SIZE,
            block_overlap=ROUTE_B_SEMANTIC_BLOCK_OVERLAP,
        )
    elif chunk_strategy in {"fixed_window_v1", "fixed_window"}:
        chunks = chunk_pages(pages, chunk_size=chunk_size, overlap=chunk_overlap)
    else:
        raise ValueError(f"Unsupported chunk_strategy: {chunk_strategy}")

    document_model = build_document_model(
        pdf_path=pdf_path,
        parser_name=parser_source["parser_name"],
        parser_version=parser_version,
        source_signature=parser_source["source_signature"],
        blocks=blocks,
    )
    markdown_path.write_text(document_blocks_to_markdown(blocks), encoding="utf-8")
    manifest = {
        "ingest_version": INGEST_VERSION,
        "pdf_path": str(pdf_path),
        "parser_backend": parser_backend,
        "parser_name": parser_source["parser_name"],
        "parser_version": parser_version,
        "parser_source_path": parser_source["source_path"],
        "parser_selection_reason": parser_source.get("selection_reason", ""),
        "mineru_run": parser_source.get("mineru_run", {}),
        "parser_source_signature": parser_source["source_signature"],
        "document_model_version": document_model["document_model_version"],
        "total_pages": len(pages),
        "total_text_chars": sum(page.get("char_count", 0) for page in pages),
        "text_available": has_enough_text_layer(pages),
        "chunk_strategy": chunk_strategy,
        "chunker_name": chunker_name,
        "chunk_size": chunk_size,
        "chunk_overlap": chunk_overlap,
        "semantic_target_size": ROUTE_B_SEMANTIC_TARGET_SIZE,
        "semantic_min_size": ROUTE_B_SEMANTIC_MIN_SIZE,
        "semantic_max_size": ROUTE_B_SEMANTIC_MAX_SIZE,
        "semantic_block_overlap": ROUTE_B_SEMANTIC_BLOCK_OVERLAP,
        "block_count": len(blocks),
        "chunk_count": len(chunks),
    }

    save_json(pages, page_texts_path)
    save_json(page_features, page_features_path)
    save_json(chunks, text_chunks_path)
    save_json(blocks, document_blocks_path)
    save_json(document_model, document_model_path)
    save_json(manifest, manifest_path)

    return {
        "manifest": manifest,
        "pages": pages,
        "page_features": page_features,
        "chunks": chunks,
        "blocks": blocks,
        "document_model": document_model,
        "cache_used": False,
        "paths": {
            "page_texts": str(page_texts_path),
            "page_features": str(page_features_path),
            "text_chunks": str(text_chunks_path),
            "document_blocks": str(document_blocks_path),
                "document_model": str(document_model_path),
                "markdown": str(markdown_path),
            "manifest": str(manifest_path),
        },
    }
