from pathlib import Path
import os
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")
VLM_MODEL = os.getenv("VLM_MODEL", "qwen-vl-plus")
TEXT_MODEL = os.getenv("TEXT_MODEL", "qwen-plus-2025-07-28")
LLM_MATCHER_ENABLED = os.getenv("LLM_MATCHER_ENABLED", "true").lower() == "true"
SCHEMA_JUDGE_MODEL = os.getenv("SCHEMA_JUDGE_MODEL", "qwen3.6-flash")
SCHEMA_JUDGE_FALLBACK_ENABLED = os.getenv("SCHEMA_JUDGE_FALLBACK_ENABLED", "true").lower() == "true"
SCHEMA_JUDGE_FALLBACK_MODEL = os.getenv("SCHEMA_JUDGE_FALLBACK_MODEL", "qwen3.6-plus")
SCHEMA_JUDGE_ESCALATE_MIN_CONFIDENCE = float(os.getenv("SCHEMA_JUDGE_ESCALATE_MIN_CONFIDENCE", "0.55"))
SCHEMA_JUDGE_ESCALATE_MAX_CONFIDENCE = float(os.getenv("SCHEMA_JUDGE_ESCALATE_MAX_CONFIDENCE", "0.88"))
SCHEMA_JUDGE_TOP_K = int(os.getenv("SCHEMA_JUDGE_TOP_K", "8"))
SCHEMA_JUDGE_MIN_CONFIDENCE = float(os.getenv("SCHEMA_JUDGE_MIN_CONFIDENCE", "0.78"))
SCHEMA_JUDGE_SOFT_ACCEPT_CONFIDENCE = float(os.getenv("SCHEMA_JUDGE_SOFT_ACCEPT_CONFIDENCE", "0.88"))
SEMANTIC_JUDGE_ENABLED = os.getenv("SEMANTIC_JUDGE_ENABLED", "true").lower() == "true"
ROUTE_B_TOP_K = int(os.getenv("ROUTE_B_TOP_K", "4"))
ROUTE_B_RECALL_K = int(os.getenv("ROUTE_B_RECALL_K", "12"))
ROUTE_B_USE_VECTOR_RAG = os.getenv("ROUTE_B_USE_VECTOR_RAG", "true").lower() == "true"
ROUTE_B_ENABLE_QUANT_FALLBACK = os.getenv("ROUTE_B_ENABLE_QUANT_FALLBACK", "true").lower() == "true"
ROUTE_B_CHUNK_STRATEGY = os.getenv("ROUTE_B_CHUNK_STRATEGY", "semantic_esg_v1")
ROUTE_B_CHUNK_SIZE = int(os.getenv("ROUTE_B_CHUNK_SIZE", "800"))
ROUTE_B_CHUNK_OVERLAP = int(os.getenv("ROUTE_B_CHUNK_OVERLAP", "120"))
ROUTE_B_SEMANTIC_TARGET_SIZE = int(os.getenv("ROUTE_B_SEMANTIC_TARGET_SIZE", "900"))
ROUTE_B_SEMANTIC_MIN_SIZE = int(os.getenv("ROUTE_B_SEMANTIC_MIN_SIZE", "250"))
ROUTE_B_SEMANTIC_MAX_SIZE = int(os.getenv("ROUTE_B_SEMANTIC_MAX_SIZE", "1200"))
ROUTE_B_SEMANTIC_BLOCK_OVERLAP = int(os.getenv("ROUTE_B_SEMANTIC_BLOCK_OVERLAP", "1"))
PDF_PARSER_BACKEND = os.getenv("PDF_PARSER_BACKEND", "auto").lower()
MINERU_OUTPUT_ROOT = os.getenv("MINERU_OUTPUT_ROOT", str(PROJECT_ROOT / "output" / "mineru_test"))
MINERU_FALLBACK_TO_PYMUPDF = os.getenv("MINERU_FALLBACK_TO_PYMUPDF", "true").lower() == "true"
MINERU_AUTO_RUN_ENABLED = os.getenv("MINERU_AUTO_RUN_ENABLED", "false").lower() == "true"
MINERU_COMMAND = os.getenv("MINERU_COMMAND", "")
MINERU_AUTO_RUN_TIMEOUT_SECONDS = int(os.getenv("MINERU_AUTO_RUN_TIMEOUT_SECONDS", "1800"))
MINERU_ROUTE_A_ENABLED = os.getenv("MINERU_ROUTE_A_ENABLED", "true").lower() == "true"
MINERU_ROUTE_A_MIN_ROWS = int(os.getenv("MINERU_ROUTE_A_MIN_ROWS", "3"))
MAX_LLM_CALLS_PER_REPORT = int(os.getenv("MAX_LLM_CALLS_PER_REPORT", "30"))
ROUTE_B2_TOP_K = int(os.getenv("ROUTE_B2_TOP_K", "5"))
ROUTE_B2_VECTOR_TOP_K = int(os.getenv("ROUTE_B2_VECTOR_TOP_K", "8"))
ROUTE_B2_USE_VECTOR_RAG = os.getenv("ROUTE_B2_USE_VECTOR_RAG", "true").lower() == "true"
ROUTE_B2_SKIP_UNLIKELY = os.getenv("ROUTE_B2_SKIP_UNLIKELY", "true").lower() == "true"
ROUTE_B2_FUSION_ENABLED = os.getenv("ROUTE_B2_FUSION_ENABLED", "true").lower() == "true"
ROUTE_B2_VERIFY_ROUTE_A_MAX_CONFIDENCE = float(os.getenv("ROUTE_B2_VERIFY_ROUTE_A_MAX_CONFIDENCE", "0.85"))
ROUTE_B2_VERIFY_ROUTE_A_ZERO = os.getenv("ROUTE_B2_VERIFY_ROUTE_A_ZERO", "true").lower() == "true"
ROUTE_B2_VERIFY_CONFLICTS = os.getenv("ROUTE_B2_VERIFY_CONFLICTS", "true").lower() == "true"
RAG_EMBEDDING_PROVIDER = os.getenv("RAG_EMBEDDING_PROVIDER", "local").lower()
RAG_EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "text-embedding-v4")
RAG_LOCAL_DIM = int(os.getenv("RAG_LOCAL_DIM", "384"))
MAX_B2_LLM_CALLS_PER_REPORT = int(os.getenv("MAX_B2_LLM_CALLS_PER_REPORT", "40"))
ROUTE_B2_MIN_CONFIDENCE = float(os.getenv("ROUTE_B2_MIN_CONFIDENCE", "0.72"))
ROUTE_A_CANDIDATE_TOP_K = int(os.getenv("ROUTE_A_CANDIDATE_TOP_K", "3"))
ROUTE_A_CANDIDATE_MIN_SCORE = int(os.getenv("ROUTE_A_CANDIDATE_MIN_SCORE", "25"))
ROUTE_A_EXPAND_BEFORE = int(os.getenv("ROUTE_A_EXPAND_BEFORE", "1"))
ROUTE_A_EXPAND_AFTER = int(os.getenv("ROUTE_A_EXPAND_AFTER", "2"))
ROUTE_A_TAIL_START_RATIO = float(os.getenv("ROUTE_A_TAIL_START_RATIO", "0.65"))
ROUTE_A_B2_MIN_EXTRACTED_FIELDS = int(os.getenv("ROUTE_A_B2_MIN_EXTRACTED_FIELDS", "18"))
ROUTE_A_RENDER_SPLIT_PAGES = os.getenv("ROUTE_A_RENDER_SPLIT_PAGES", "false").lower() == "true"
ROUTE_A_ADAPTIVE_SPLIT_RETRY = os.getenv("ROUTE_A_ADAPTIVE_SPLIT_RETRY", "true").lower() == "true"
ROUTE_A_USE_VLM_CACHE = os.getenv("ROUTE_A_USE_VLM_CACHE", "true").lower() == "true"
ROUTE_A_INCLUDE_CHART_PAGES = os.getenv("ROUTE_A_INCLUDE_CHART_PAGES", "false").lower() == "true"
UNIFIED_ENABLE_VISUAL_FOLLOWUP = os.getenv("UNIFIED_ENABLE_VISUAL_FOLLOWUP", "true").lower() == "true"
UNIFIED_VISUAL_FOLLOWUP_MAX_PAGES = int(os.getenv("UNIFIED_VISUAL_FOLLOWUP_MAX_PAGES", "3"))
TABLE_QUALITY_VISUAL_THRESHOLD = float(os.getenv("TABLE_QUALITY_VISUAL_THRESHOLD", "0.72"))
UNIFIED_PREPARE_ARBITRATION_IMAGES = os.getenv("UNIFIED_PREPARE_ARBITRATION_IMAGES", "true").lower() == "true"
UNIFIED_ARBITRATION_MAX_REGIONS = int(os.getenv("UNIFIED_ARBITRATION_MAX_REGIONS", "10"))
UNIFIED_ENABLE_TABLE_ARBITRATION_VLM = os.getenv("UNIFIED_ENABLE_TABLE_ARBITRATION_VLM", "true").lower() == "true"
UNIFIED_PARALLEL_ROUTES = os.getenv("UNIFIED_PARALLEL_ROUTES", "false").lower() == "true"
ENABLE_LLM_FOR_QUANTITATIVE = os.getenv("ENABLE_LLM_FOR_QUANTITATIVE", "false").lower() == "true"
LLM_ONLY_FOR_LOW_CONFIDENCE = os.getenv("LLM_ONLY_FOR_LOW_CONFIDENCE", "true").lower() == "true"
CACHE_LLM_RESULTS = os.getenv("CACHE_LLM_RESULTS", "true").lower() == "true"
TOKEN_BUDGET = {
    "route_b_top_k": ROUTE_B_TOP_K,
    "route_b_recall_k": ROUTE_B_RECALL_K,
    "route_b_use_vector_rag": ROUTE_B_USE_VECTOR_RAG,
    "route_b_enable_quant_fallback": ROUTE_B_ENABLE_QUANT_FALLBACK,
    "route_b_chunk_strategy": ROUTE_B_CHUNK_STRATEGY,
    "route_b_chunk_size": ROUTE_B_CHUNK_SIZE,
    "route_b_chunk_overlap": ROUTE_B_CHUNK_OVERLAP,
    "route_b_semantic_target_size": ROUTE_B_SEMANTIC_TARGET_SIZE,
    "route_b_semantic_min_size": ROUTE_B_SEMANTIC_MIN_SIZE,
    "route_b_semantic_max_size": ROUTE_B_SEMANTIC_MAX_SIZE,
    "route_b_semantic_block_overlap": ROUTE_B_SEMANTIC_BLOCK_OVERLAP,
    "pdf_parser_backend": PDF_PARSER_BACKEND,
    "mineru_output_root": MINERU_OUTPUT_ROOT,
    "mineru_fallback_to_pymupdf": MINERU_FALLBACK_TO_PYMUPDF,
    "mineru_auto_run_enabled": MINERU_AUTO_RUN_ENABLED,
    "mineru_route_a_enabled": MINERU_ROUTE_A_ENABLED,
    "mineru_route_a_min_rows": MINERU_ROUTE_A_MIN_ROWS,
    "max_llm_calls_per_report": MAX_LLM_CALLS_PER_REPORT,
    "schema_judge_model": SCHEMA_JUDGE_MODEL,
    "schema_judge_fallback_enabled": SCHEMA_JUDGE_FALLBACK_ENABLED,
    "schema_judge_fallback_model": SCHEMA_JUDGE_FALLBACK_MODEL,
    "schema_judge_escalate_min_confidence": SCHEMA_JUDGE_ESCALATE_MIN_CONFIDENCE,
    "schema_judge_escalate_max_confidence": SCHEMA_JUDGE_ESCALATE_MAX_CONFIDENCE,
    "schema_judge_top_k": SCHEMA_JUDGE_TOP_K,
    "schema_judge_min_confidence": SCHEMA_JUDGE_MIN_CONFIDENCE,
    "schema_judge_soft_accept_confidence": SCHEMA_JUDGE_SOFT_ACCEPT_CONFIDENCE,
    "semantic_judge_enabled": SEMANTIC_JUDGE_ENABLED,
    "route_b2_top_k": ROUTE_B2_TOP_K,
    "route_b2_vector_top_k": ROUTE_B2_VECTOR_TOP_K,
    "route_b2_use_vector_rag": ROUTE_B2_USE_VECTOR_RAG,
    "route_b2_skip_unlikely": ROUTE_B2_SKIP_UNLIKELY,
    "route_b2_fusion_enabled": ROUTE_B2_FUSION_ENABLED,
    "route_b2_verify_route_a_max_confidence": ROUTE_B2_VERIFY_ROUTE_A_MAX_CONFIDENCE,
    "route_b2_verify_route_a_zero": ROUTE_B2_VERIFY_ROUTE_A_ZERO,
    "route_b2_verify_conflicts": ROUTE_B2_VERIFY_CONFLICTS,
    "rag_embedding_provider": RAG_EMBEDDING_PROVIDER,
    "rag_embedding_model": RAG_EMBEDDING_MODEL,
    "rag_local_dim": RAG_LOCAL_DIM,
    "max_b2_llm_calls_per_report": MAX_B2_LLM_CALLS_PER_REPORT,
    "route_b2_min_confidence": ROUTE_B2_MIN_CONFIDENCE,
    "route_a_candidate_top_k": ROUTE_A_CANDIDATE_TOP_K,
    "route_a_candidate_min_score": ROUTE_A_CANDIDATE_MIN_SCORE,
    "route_a_expand_before": ROUTE_A_EXPAND_BEFORE,
    "route_a_expand_after": ROUTE_A_EXPAND_AFTER,
    "route_a_tail_start_ratio": ROUTE_A_TAIL_START_RATIO,
    "route_a_b2_min_extracted_fields": ROUTE_A_B2_MIN_EXTRACTED_FIELDS,
    "route_a_render_split_pages": ROUTE_A_RENDER_SPLIT_PAGES,
    "route_a_adaptive_split_retry": ROUTE_A_ADAPTIVE_SPLIT_RETRY,
    "route_a_use_vlm_cache": ROUTE_A_USE_VLM_CACHE,
    "route_a_include_chart_pages": ROUTE_A_INCLUDE_CHART_PAGES,
    "unified_enable_visual_followup": UNIFIED_ENABLE_VISUAL_FOLLOWUP,
    "unified_visual_followup_max_pages": UNIFIED_VISUAL_FOLLOWUP_MAX_PAGES,
    "table_quality_visual_threshold": TABLE_QUALITY_VISUAL_THRESHOLD,
    "unified_prepare_arbitration_images": UNIFIED_PREPARE_ARBITRATION_IMAGES,
    "unified_arbitration_max_regions": UNIFIED_ARBITRATION_MAX_REGIONS,
    "unified_enable_table_arbitration_vlm": UNIFIED_ENABLE_TABLE_ARBITRATION_VLM,
    "unified_parallel_routes": UNIFIED_PARALLEL_ROUTES,
    "enable_llm_for_quantitative": ENABLE_LLM_FOR_QUANTITATIVE,
    "llm_only_for_low_confidence": LLM_ONLY_FOR_LOW_CONFIDENCE,
    "cache_llm_results": CACHE_LLM_RESULTS,
}
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT_DIR = PROJECT_ROOT / "output"
REPORTS_DIR = OUTPUT_DIR / "reports"
