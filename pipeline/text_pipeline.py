import csv
import json
from pathlib import Path
from typing import Dict, Any, List

from config.core_schema import CORE_SCHEMA
from utils.pdf_text_utils import extract_pdf_text_by_page, has_enough_text_layer
from utils.text_chunker import chunk_pages
from utils.route_b_retriever import retrieve_relevant_chunks
from utils.llm_text_extractor import extract_text_indicator_with_llm


class ESGTextPipeline:
    """
    路线 B：正文文本抽取 Pipeline。

    第一版只处理 preferred_source == main_text_rag 的定性字段。
    """

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _target_fields(self):
        return [
            item for item in CORE_SCHEMA
            if item.get("preferred_source") == "main_text_rag"
        ]

    def _save_json(self, path: Path, data):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _save_csv(self, path: Path, rows: List[Dict[str, Any]]):
        if not rows:
            return

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
                    "route": row.get("route"),
                })

    def run(self, pdf_path: Path) -> Dict[str, Any]:
        pdf_path = Path(pdf_path)

        print("\n----- Running ESGTextPipeline / Route B -----")
        print(f"PDF: {pdf_path}")

        pages = extract_pdf_text_by_page(pdf_path)

        text_available = has_enough_text_layer(pages)

        text_pages_path = self.output_dir / "route_b_text_pages.json"
        self._save_json(text_pages_path, pages)

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

            self._save_json(self.output_dir / "route_b_text_results.json", results)
            self._save_csv(self.output_dir / "route_b_text_results.csv", results)

            summary = {
                "route_b_available": False,
                "reason": "no_text_layer_or_too_little_text",
                "total_pages": len(pages),
                "target_fields": len(results),
                "matched_fields": 0,
            }

            self._save_json(self.output_dir / "route_b_summary.json", summary)

            print("[Route B] no text layer, skipped.")
            return summary

        chunks = chunk_pages(pages)

        self._save_json(self.output_dir / "route_b_chunks.json", chunks)

        results = []

        for item in self._target_fields():
            print(f"[Route B] extracting {item['field_key']}")

            retrieved_chunks = retrieve_relevant_chunks(item, chunks, top_k=5)

            llm_result = extract_text_indicator_with_llm(
                field_item=item,
                chunks=retrieved_chunks,
            )

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
                "route": "B_text_rag",
            })

        matched_count = sum(1 for row in results if row.get("matched"))

        self._save_json(self.output_dir / "route_b_text_results.json", results)
        self._save_csv(self.output_dir / "route_b_text_results.csv", results)

        summary = {
            "route_b_available": True,
            "total_pages": len(pages),
            "chunks": len(chunks),
            "target_fields": len(results),
            "matched_fields": matched_count,
        }

        self._save_json(self.output_dir / "route_b_summary.json", summary)

        print(f"[Route B] matched={matched_count}/{len(results)}")
        return summary