import csv
import json
from pathlib import Path
from typing import Dict, Any, List

from config.schema import ROUTE_B_SCHEMA
from config.settings import (
    ROUTE_B_CHUNK_OVERLAP,
    ROUTE_B_CHUNK_SIZE,
    ROUTE_B_CHUNK_STRATEGY,
    ROUTE_B_ENABLE_QUANT_FALLBACK,
    ROUTE_B_RECALL_K,
    ROUTE_B_TOP_K,
    ROUTE_B_USE_VECTOR_RAG,
    MAX_LLM_CALLS_PER_REPORT,
)
from utils.pdf_ingest import ingest_pdf
from utils.hybrid_retriever import retrieve_hybrid_chunks
from utils.llm_text_extractor import extract_text_indicator_with_llm
from utils.rag_vector_store import FaissChunkVectorStore
from utils.structured_rag_chunks import build_structured_chunks_from_all_table_rows
from utils.industry_detector import detect_industry
from pipeline.quant_text_pipeline import ESGQuantTextPipeline


class ESGTextPipeline:
    """
    统一路线 B：一次构建 RAG 语料和索引，提取定性字段并补充 Route A 缺失定量字段。
    """

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _target_fields(self):
        return ROUTE_B_SCHEMA

    def _save_json(self, path: Path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _save_csv(self, path: Path, rows: List[Dict[str, Any]]):
        fieldnames = [
            "field_key",
            "field_name_cn",
            "category",
            "matched",
            "value",
            "summary",
            "evidence",
            "source_pages",
            "confidence",
            "reason",
            "route_b_validation_ok",
            "route_b_validation_reason",
            "llm_matched_raw",
            "llm_confidence_raw",
            "evidence_ngram_coverage",
            "retrieved_chunks",
            "route",
        ]

        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for row in rows:
                writer.writerow({
                    "field_key": row.get("field_key"),
                    "field_name_cn": row.get("field_name_cn"),
                    "category": row.get("category"),
                    "matched": row.get("matched"),
                    "value": row.get("value"),
                    "summary": row.get("summary"),
                    "evidence": row.get("evidence"),
                    "source_pages": json.dumps(row.get("source_pages", []), ensure_ascii=False),
                    "confidence": row.get("confidence"),
                    "reason": row.get("reason"),
                    "route_b_validation_ok": row.get("route_b_validation_ok", ""),
                    "route_b_validation_reason": row.get("route_b_validation_reason", ""),
                    "llm_matched_raw": row.get("llm_matched_raw", ""),
                    "llm_confidence_raw": row.get("llm_confidence_raw", ""),
                    "evidence_ngram_coverage": row.get("evidence_ngram_coverage", ""),
                    "retrieved_chunks": json.dumps(row.get("retrieved_chunks", []), ensure_ascii=False),
                    "route": row.get("route"),
                })

    def run(self, pdf_path: Path) -> Dict[str, Any]:
        pdf_path = Path(pdf_path)

        print("\n----- Running Unified Route B RAG Pipeline -----")
        print(f"PDF: {pdf_path}")

        ingest = ingest_pdf(
            pdf_path=pdf_path,
            output_dir=self.output_dir,
            chunk_size=ROUTE_B_CHUNK_SIZE,
            chunk_overlap=ROUTE_B_CHUNK_OVERLAP,
        )
        pages = ingest["pages"]
        text_chunks = ingest["chunks"]
        structured_chunks = build_structured_chunks_from_all_table_rows(self.output_dir)
        chunks = [*text_chunks, *structured_chunks]
        text_available = bool(ingest["manifest"].get("text_available"))
        rag_available = text_available or bool(structured_chunks)
        industry = detect_industry(pdf_path.name, pages)

        self._save_json(self.output_dir / "route_b_text_pages.json", pages)
        self._save_json(self.output_dir / "route_b_chunks.json", text_chunks)
        self._save_json(self.output_dir / "route_b_combined_chunks.json", chunks)

        if chunks:
            FaissChunkVectorStore(self.output_dir / "rag_index").build_or_load(chunks)

        if not text_available:
            results = []

            for item in self._target_fields():
                results.append({
                    "field_key": item["field_key"],
                    "field_name_cn": item["name_cn"],
                    "category": item["category"],
                    "matched": False,
                    "value": None,
                    "summary": "",
                    "evidence": "",
                    "source_pages": [],
                    "confidence": 0.0,
                    "reason": "no_text_layer_or_too_little_text",
                    "route": "B_text_rag",
                })

            llm_calls = 0
        else:
            results = []
            llm_calls = 0

            for item in self._target_fields():
                if llm_calls >= MAX_LLM_CALLS_PER_REPORT:
                    results.append({
                        "field_key": item["field_key"],
                        "field_name_cn": item["name_cn"],
                        "category": item["category"],
                        "matched": False,
                        "value": None,
                        "summary": "",
                        "evidence": "",
                        "source_pages": [],
                        "confidence": 0.0,
                        "reason": "max_llm_calls_per_report_reached",
                        "route": "B_text_rag",
                    })
                    continue

                print(f"[Route B/qualitative] extracting {item['field_key']}")

                retrieved_chunks = retrieve_hybrid_chunks(
                    item,
                    chunks,
                    top_k=ROUTE_B_TOP_K,
                    recall_k=ROUTE_B_RECALL_K,
                    industry=industry,
                    vector_index_dir=self.output_dir / "rag_index",
                    use_vector=ROUTE_B_USE_VECTOR_RAG,
                )
                if not retrieved_chunks:
                    results.append({
                        "field_key": item["field_key"],
                        "field_name_cn": item["name_cn"],
                        "category": item["category"],
                        "matched": False,
                        "value": None,
                        "summary": "",
                        "evidence": "",
                        "source_pages": [],
                        "confidence": 0.0,
                        "reason": "no_relevant_chunks",
                        "route": "B_text_rag",
                    })
                    continue

                llm_result = extract_text_indicator_with_llm(
                    field_item=item,
                    chunks=retrieved_chunks,
                )
                if llm_result.get("reason") != "model_call_budget_exhausted":
                    llm_calls += 1

                results.append({
                    "field_key": item["field_key"],
                    "field_name_cn": item["name_cn"],
                    "category": item["category"],
                    "matched": bool(llm_result.get("matched")),
                    "value": llm_result.get("value"),
                    "summary": llm_result.get("summary", ""),
                    "evidence": llm_result.get("evidence", ""),
                    "source_pages": llm_result.get("source_pages", []),
                    "confidence": llm_result.get("confidence", 0.0),
                    "reason": llm_result.get("reason", ""),
                    "route_b_validation_ok": llm_result.get("route_b_validation_ok", False),
                    "route_b_validation_reason": llm_result.get("route_b_validation_reason", ""),
                    "llm_matched_raw": llm_result.get("llm_matched_raw", False),
                    "llm_confidence_raw": llm_result.get("llm_confidence_raw", 0.0),
                    "evidence_ngram_coverage": llm_result.get("evidence_ngram_coverage", 0.0),
                    "retrieved_chunks": [
                        {
                            "chunk_id": chunk.get("chunk_id"),
                            "page_number": chunk.get("page_number"),
                            "retrieval_rank": chunk.get("retrieval_rank"),
                            "retrieval_profile": chunk.get("retrieval_profile"),
                            "rrf_score": chunk.get("rrf_score"),
                            "evidence_score": chunk.get("evidence_score"),
                            "hybrid_score": chunk.get("hybrid_score"),
                        }
                        for chunk in retrieved_chunks
                    ],
                    "route": "B_text_rag",
                })

        matched_count = sum(1 for row in results if row.get("matched"))

        self._save_json(self.output_dir / "route_b_text_results.json", results)
        self._save_csv(self.output_dir / "route_b_text_results.csv", results)

        quant_pipeline = ESGQuantTextPipeline(self.output_dir)
        if ROUTE_B_ENABLE_QUANT_FALLBACK:
            quant_summary = quant_pipeline.run(
                pdf_path,
                ingest=ingest,
                chunks=chunks,
                structured_chunks=structured_chunks,
            )
        else:
            quant_summary = quant_pipeline.write_disabled_outputs()

        summary = {
            "route_b_available": rag_available,
            "unified_route_b": True,
            "text_available": text_available,
            "industry": industry,
            "total_pages": len(pages),
            "text_chunks": len(text_chunks),
            "structured_chunks": len(structured_chunks),
            "combined_chunks": len(chunks),
            "target_fields": len(results),
            "matched_fields": matched_count,
            "llm_calls": llm_calls,
            "qualitative": {
                "target_fields": len(results),
                "matched_fields": matched_count,
                "llm_calls": llm_calls,
                "skipped_no_relevant_chunks": sum(
                    1 for row in results if row.get("reason") == "no_relevant_chunks"
                ),
                "skipped_by_model_budget": sum(
                    1 for row in results if row.get("reason") == "model_call_budget_exhausted"
                ),
            },
            "quantitative_fallback": quant_summary,
            "total_llm_calls": llm_calls + int(quant_summary.get("llm_calls", 0) or 0),
            "token_budget": {
                "route_b_top_k": ROUTE_B_TOP_K,
                "route_b_recall_k": ROUTE_B_RECALL_K,
                "route_b_use_vector_rag": ROUTE_B_USE_VECTOR_RAG,
                "route_b_enable_quant_fallback": ROUTE_B_ENABLE_QUANT_FALLBACK,
                "route_b_chunk_strategy": ROUTE_B_CHUNK_STRATEGY,
                "route_b_chunk_size": ROUTE_B_CHUNK_SIZE,
                "route_b_chunk_overlap": ROUTE_B_CHUNK_OVERLAP,
                "max_llm_calls_per_report": MAX_LLM_CALLS_PER_REPORT,
            },
            "ingest_cache_used": ingest["cache_used"],
            "ingest_paths": ingest["paths"],
        }

        self._save_json(self.output_dir / "route_b_summary.json", summary)

        print(
            f"[Unified Route B] qualitative={matched_count}/{len(results)} "
            f"quantitative_fallback={quant_summary.get('matched_fields', 0)}/{quant_summary.get('attempted_fields', 0)}"
        )
        return summary
