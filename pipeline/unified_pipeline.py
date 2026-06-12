import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from config.schema import ALL_SCHEMA, build_runtime_schema
from config.settings import (
    ROUTE_A_CANDIDATE_MIN_SCORE,
    ROUTE_A_CANDIDATE_TOP_K,
    ROUTE_A_EXPAND_AFTER,
    ROUTE_A_EXPAND_BEFORE,
    MINERU_ROUTE_A_ENABLED,
    MINERU_ROUTE_A_MIN_ROWS,
    TABLE_QUALITY_VISUAL_THRESHOLD,
    UNIFIED_ARBITRATION_MAX_REGIONS,
    UNIFIED_ENABLE_TABLE_ARBITRATION_VLM,
    UNIFIED_ENABLE_VISUAL_FOLLOWUP,
    UNIFIED_PREPARE_ARBITRATION_IMAGES,
    UNIFIED_VISUAL_FOLLOWUP_MAX_PAGES,
    DASHSCOPE_API_KEY,
)
from utils.call_tracker import LLMCallTracker
from utils.evidence_store import build_evidence_records, write_evidence_store
from utils.json_utils import load_json
from utils.industry_detector import detect_industry
from utils.metric_planner import build_metric_plans
from utils.mineru_route_a import build_mineru_route_a_pages
from utils.pdf_ingest import ingest_pdf, select_route_a_candidate_pages
from utils.result_guard import safe_write_json
from utils.raw_metric_store import write_raw_metric_store
from utils.structured_rag_chunks import build_structured_chunks_from_all_table_rows
from utils.table_arbitrator import (
    apply_arbitration_candidates,
    extract_arbitration_candidates,
    load_standard_results,
)
from utils.table_quality import apply_cross_source_consistency, assess_mineru_tables
from utils.visual_arbitration import (
    build_table_arbitration_queue,
    prepare_table_arbitration_images,
)
from utils.visual_followup import build_visual_followup_queue


class UnifiedESGPipeline:
    """User-facing orchestration for text, table, visual, fusion, and merge."""

    def __init__(self, report_dir: Path, run_mode: str = "fast"):
        if run_mode not in {"fast", "balanced", "deep"}:
            raise ValueError(f"Unsupported run mode: {run_mode}")
        self.report_dir = Path(report_dir)
        self.run_mode = run_mode
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def _pdf_fingerprint(self, pdf_path: Path) -> str:
        if not pdf_path.exists():
            return f"missing:{pdf_path}"
        digest = hashlib.sha256()
        with open(pdf_path, "rb") as file:
            for block in iter(lambda: file.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def _write_run_manifest(self, payload: Dict[str, Any]) -> None:
        safe_write_json(self.report_dir / "run_manifest.json", payload)

    def _can_reuse_visual_results(self, pdf_fingerprint: str) -> bool:
        standard_path = self.report_dir / "standard_esg_results.csv"
        summary_path = self.report_dir / "unified_pipeline_summary.json"
        if not standard_path.exists() or not summary_path.exists():
            return False
        previous = load_json(summary_path)
        return previous.get("document_ingest", {}).get("pdf_fingerprint") == pdf_fingerprint

    def _visual_plan(self, ingest: Dict[str, Any]) -> Dict[str, Any]:
        selection = select_route_a_candidate_pages(
            ingest["page_features"],
            top_k=ROUTE_A_CANDIDATE_TOP_K,
            min_score=ROUTE_A_CANDIDATE_MIN_SCORE,
            expand_before=ROUTE_A_EXPAND_BEFORE,
            expand_after=ROUTE_A_EXPAND_AFTER,
        )
        visual_proxy_pages = sorted(
            {
                int(feature["page_number"])
                for feature in ingest["page_features"]
                if feature.get("force_keep")
                or feature.get("chart_force_keep")
                or int(feature.get("table_like_lines") or 0) >= 3
            }
        )
        return {
            "mode": "summary_table" if selection.get("found") else "skip",
            "run_active_visual_extraction": bool(selection.get("found")),
            "active_candidate_pages": selection.get("candidate_pages", []),
            "visual_proxy_pages": visual_proxy_pages,
            "selection": selection,
        }

    def _run_visual_extraction(self, pdf_path: Path) -> Dict[str, Any]:
        from pipeline.appendix_pipeline import ESGAppendixPipeline

        return ESGAppendixPipeline(self.report_dir).run(pdf_path)

    def _run_mineru_route_a(self, ingest: Dict[str, Any]) -> Dict[str, Any]:
        if not MINERU_ROUTE_A_ENABLED:
            return {"available": False, "reason": "mineru_route_a_disabled", "selected_tables": 0, "row_count": 0}
        if ingest.get("manifest", {}).get("parser_name") != "mineru":
            return {"available": False, "reason": "mineru_not_used", "selected_tables": 0, "row_count": 0}

        result = build_mineru_route_a_pages(ingest.get("blocks", []))
        safe_write_json(self.report_dir / "mineru_route_a_assessments.json", result["assessments"])
        raw_metric_store = write_raw_metric_store(self.report_dir, result["pages"])
        if not result["selected_tables"] or result["row_count"] < MINERU_ROUTE_A_MIN_ROWS:
            return {
                "available": False,
                "reason": "no_valid_mineru_performance_tables",
                "selected_tables": result["selected_tables"],
                "row_count": result["row_count"],
                "raw_metric_store": raw_metric_store,
            }

        from agents.schema_match_agent import SchemaMatchAgent
        from agents.validation_agent import ValidationAgent
        from utils.csv_export import export_standard_results_csv, export_unknown_metrics_csv

        safe_write_json(self.report_dir / "all_table_rows.json", result["pages"])
        state: Dict[str, Any] = {
            "output_dir": self.report_dir,
            "all_table_rows": result["pages"],
            "schema_match_allow_llm": False,
        }
        state = SchemaMatchAgent().run(state)
        state = ValidationAgent().run(state)
        export_standard_results_csv(
            state.get("standard_results", {}),
            self.report_dir / "standard_esg_results.csv",
        )
        export_unknown_metrics_csv(
            state.get("unknown_metrics", []),
            self.report_dir / "unknown_metrics.csv",
        )
        return {
            **state,
            "available": True,
            "reason": "mineru_performance_tables",
            "selected_tables": result["selected_tables"],
            "row_count": result["row_count"],
            "raw_metric_store": raw_metric_store,
        }

    def _run_text_extraction(self, pdf_path: Path) -> Dict[str, Any]:
        from pipeline.text_pipeline import ESGTextPipeline

        return ESGTextPipeline(self.report_dir).run(pdf_path)

    def _run_merge(self) -> Dict[str, Any]:
        from pipeline.merge_pipeline import ESGMergePipeline

        return ESGMergePipeline(self.report_dir).run()

    @staticmethod
    def _merge_targeted_visual_rows(existing_rows: list[Any], targeted_rows: list[Any]) -> list[Any]:
        combined = []
        seen = set()
        for row in [*existing_rows, *targeted_rows]:
            key = json.dumps(row, ensure_ascii=False, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            combined.append(row)
        return combined

    @staticmethod
    def _merge_targeted_visual_results(
        existing_results: Dict[str, Any],
        targeted_results: Dict[str, Any],
    ) -> tuple[Dict[str, Any], list[str]]:
        combined = dict(existing_results)
        added_fields = []
        for field_key, item in targeted_results.items():
            if item.get("status") != "extracted":
                continue
            existing = combined.get(field_key, {})
            if existing.get("status") == "extracted":
                continue
            combined[field_key] = item
            added_fields.append(field_key)
        return combined, added_fields

    def _run_targeted_visual_pages(self, pdf_path: Path, page_numbers: list[int]) -> Dict[str, Any]:
        from agents.page_render_agent import PageRenderAgent
        from agents.schema_match_agent import SchemaMatchAgent
        from agents.validation_agent import ValidationAgent
        from agents.vlm_table_ocr_agent import VLMTableOCRAgent
        from utils.csv_export import export_standard_results_csv, export_unknown_metrics_csv

        standard_path = self.report_dir / "standard_esg_results.json"
        rows_path = self.report_dir / "all_table_rows.json"
        unknown_path = self.report_dir / "unknown_metrics.json"
        existing_standard = load_json(standard_path) if standard_path.exists() else {}
        existing_rows = load_json(rows_path) if rows_path.exists() else []
        existing_unknown = load_json(unknown_path) if unknown_path.exists() else []
        state: Dict[str, Any] = {
            "pdf_path": str(pdf_path),
            "output_dir": self.report_dir,
            "appendix_found": True,
            "candidate_pages": page_numbers,
        }
        for agent in [PageRenderAgent(), VLMTableOCRAgent(), SchemaMatchAgent(), ValidationAgent()]:
            state = agent.run(state)
        targeted_standard = state.get("standard_results", {})
        targeted_extracted_fields = [
            key for key, item in targeted_standard.items() if item.get("status") == "extracted"
        ]
        combined_standard, added_fields = self._merge_targeted_visual_results(
            existing_standard if isinstance(existing_standard, dict) else {},
            targeted_standard,
        )
        combined_rows = self._merge_targeted_visual_rows(
            existing_rows if isinstance(existing_rows, list) else [],
            state.get("all_table_rows", []),
        )
        combined_unknown = self._merge_targeted_visual_rows(
            existing_unknown if isinstance(existing_unknown, list) else [],
            state.get("unknown_metrics", []),
        )
        state["standard_results"] = combined_standard
        state["all_table_rows"] = combined_rows
        state["unknown_metrics"] = combined_unknown
        state["extracted_fields"] = [
            key for key, item in combined_standard.items() if item.get("status") == "extracted"
        ]
        safe_write_json(rows_path, combined_rows)
        safe_write_json(standard_path, combined_standard)
        safe_write_json(unknown_path, combined_unknown)
        export_standard_results_csv(
            combined_standard,
            self.report_dir / "standard_esg_results.csv",
        )
        export_unknown_metrics_csv(
            combined_unknown,
            self.report_dir / "unknown_metrics.csv",
        )
        return {
            "status": "completed",
            "pages": page_numbers,
            "raw_row_count": state.get("raw_row_count", 0),
            "detected_fields": len(targeted_extracted_fields),
            "added_fields": len(added_fields),
            "added_field_keys": added_fields,
            "extracted_fields": len(state.get("extracted_fields", [])),
        }

    def _write_empty_visual_baseline(self) -> None:
        from utils.csv_export import export_standard_results_csv

        results = {
            item["field_key"]: {
                "field_key": item["field_key"],
                "value": None,
                "status": "missing",
                "confidence": 0.0,
                "match_reason": "no_active_visual_evidence",
            }
            for item in ALL_SCHEMA
        }
        export_standard_results_csv(results, self.report_dir / "standard_esg_results.csv")
        safe_write_json(self.report_dir / "standard_esg_results.json", results)
        safe_write_json(self.report_dir / "all_table_rows.json", [])

    def _build_evidence_and_followup(
        self,
        *,
        ingest: Dict[str, Any],
        metric_plans: list[Dict[str, Any]],
        excluded_page_numbers: set[int] | None = None,
    ) -> tuple[Dict[str, Any], list[Dict[str, Any]]]:
        structured_chunks = build_structured_chunks_from_all_table_rows(self.report_dir)
        records = build_evidence_records(
            text_chunks=ingest["chunks"],
            structured_chunks=structured_chunks,
            page_features=ingest["page_features"],
        )
        evidence_summary = write_evidence_store(self.report_dir, records)
        quant_results_path = self.report_dir / "route_b_quant_results.json"
        quant_results = load_json(quant_results_path) if quant_results_path.exists() else []
        visual_followup_queue = build_visual_followup_queue(
            metric_plans=metric_plans,
            evidence_records=records,
            quantitative_results=quant_results if isinstance(quant_results, list) else [],
            excluded_page_numbers=excluded_page_numbers,
        )
        safe_write_json(self.report_dir / "visual_followup_queue.json", visual_followup_queue)
        return evidence_summary, visual_followup_queue

    def _visual_followup_page_budget(self) -> int:
        if not UNIFIED_ENABLE_VISUAL_FOLLOWUP or self.run_mode == "fast":
            return 0
        if self.run_mode == "balanced":
            return min(1, UNIFIED_VISUAL_FOLLOWUP_MAX_PAGES)
        return UNIFIED_VISUAL_FOLLOWUP_MAX_PAGES

    def _arbitration_region_budget(self) -> int:
        if not UNIFIED_PREPARE_ARBITRATION_IMAGES or self.run_mode == "fast":
            return 0
        if self.run_mode == "balanced":
            return min(3, UNIFIED_ARBITRATION_MAX_REGIONS)
        return UNIFIED_ARBITRATION_MAX_REGIONS

    def _prepare_table_arbitration(self, pdf_path: Path) -> Dict[str, Any]:
        structured_chunks = build_structured_chunks_from_all_table_rows(self.report_dir)
        assessments = assess_mineru_tables(
            structured_chunks,
            visual_threshold=TABLE_QUALITY_VISUAL_THRESHOLD,
        )
        assessments = apply_cross_source_consistency(assessments, structured_chunks)
        queue = build_table_arbitration_queue(
            assessments,
            max_regions=UNIFIED_ARBITRATION_MAX_REGIONS,
        )
        region_budget = self._arbitration_region_budget()
        prepared = (
            prepare_table_arbitration_images(
                pdf_path,
                self.report_dir,
                queue,
                max_regions=region_budget,
            )
            if region_budget and queue
            else []
        )
        safe_write_json(self.report_dir / "table_quality_assessments.json", assessments)
        safe_write_json(self.report_dir / "table_arbitration_queue.json", queue)
        safe_write_json(self.report_dir / "table_arbitration_prepared.json", prepared)
        return {
            "assessed_tables": len(assessments),
            "needs_visual": sum(bool(item.get("needs_visual")) for item in assessments),
            "queued_regions": len(queue),
            "prepared_regions": sum(item.get("status") == "image_prepared" for item in prepared),
            "region_budget": region_budget,
            "quality_path": str(self.report_dir / "table_quality_assessments.json"),
            "queue_path": str(self.report_dir / "table_arbitration_queue.json"),
            "prepared_path": str(self.report_dir / "table_arbitration_prepared.json"),
        }

    def _run_table_arbitration_vlm(self) -> Dict[str, Any]:
        prepared_path = self.report_dir / "table_arbitration_prepared.json"
        if self.run_mode == "fast" or not UNIFIED_ENABLE_TABLE_ARBITRATION_VLM:
            return {"status": "disabled", "applied_updates": 0, "proposed_updates": 0}
        if not DASHSCOPE_API_KEY:
            return {"status": "skipped_missing_api_key", "applied_updates": 0, "proposed_updates": 0}
        prepared = load_json(prepared_path) if prepared_path.exists() else []
        if not isinstance(prepared, list) or not prepared:
            return {"status": "not_needed", "applied_updates": 0, "proposed_updates": 0}

        from utils.vlm_client import extract_all_table_rows_from_image

        extracted = extract_arbitration_candidates(
            prepared,
            extractor=lambda image_path: extract_all_table_rows_from_image(
                image_path,
                stage="table_arbitration_vlm",
            ),
        )
        applied = apply_arbitration_candidates(
            load_standard_results(self.report_dir),
            extracted["candidates"],
        )
        safe_write_json(self.report_dir / "table_arbitration_vlm_results.json", extracted["region_results"])
        safe_write_json(self.report_dir / "table_arbitration_candidates.json", extracted["candidates"])
        safe_write_json(
            self.report_dir / "table_arbitration_updates.json",
            {
                "applied_updates": applied["applied_updates"],
                "proposed_updates": applied["proposed_updates"],
            },
        )
        if applied["applied_updates"]:
            from utils.csv_export import export_standard_results_csv

            safe_write_json(self.report_dir / "standard_esg_results.json", applied["standard_results"])
            export_standard_results_csv(
                applied["standard_results"],
                self.report_dir / "standard_esg_results.csv",
            )
        return {
            "status": (
                "completed_with_errors"
                if any(item.get("status") == "vlm_error" for item in extracted["region_results"])
                else "completed"
            ),
            "regions_processed": len(extracted["region_results"]),
            "region_errors": sum(
                item.get("status") == "vlm_error" for item in extracted["region_results"]
            ),
            "candidates": len(extracted["candidates"]),
            "applied_updates": len(applied["applied_updates"]),
            "proposed_updates": len(applied["proposed_updates"]),
            "results_path": str(self.report_dir / "table_arbitration_vlm_results.json"),
            "updates_path": str(self.report_dir / "table_arbitration_updates.json"),
        }

    def run(self, pdf_path: Path, *, reuse_visual_results: bool = True) -> Dict[str, Any]:
        with LLMCallTracker(self.report_dir, self.run_mode).activate():
            return self._run_impl(pdf_path, reuse_visual_results=reuse_visual_results)

    def _run_impl(self, pdf_path: Path, *, reuse_visual_results: bool = True) -> Dict[str, Any]:
        pdf_path = Path(pdf_path)
        pdf_fingerprint = self._pdf_fingerprint(pdf_path)
        started_at = datetime.now().astimezone().isoformat(timespec="seconds")
        manifest = {
            "manifest_version": "v2.0",
            "run_id": f"{pdf_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "status": "running",
            "started_at": started_at,
            "finished_at": None,
            "pdf_path": str(pdf_path),
            "report_dir": str(self.report_dir),
            "run_mode": self.run_mode,
            "routes": {
                "document_ingest": {"status": "running"},
                "route_a_performance_tables": {"status": "pending"},
                "route_b_document_extraction": {"status": "pending"},
                "fusion": {"status": "pending"},
            },
            "artifacts": {},
            "warnings": [],
            "errors": [],
        }
        self._write_run_manifest(manifest)
        ingest = ingest_pdf(pdf_path, self.report_dir)
        manifest["routes"]["document_ingest"] = {
            "status": "completed",
            "parser_name": ingest["manifest"].get("parser_name"),
            "selection_reason": ingest["manifest"].get("parser_selection_reason"),
        }
        manifest["routes"]["route_a_performance_tables"]["status"] = "running"
        self._write_run_manifest(manifest)
        industry = detect_industry(pdf_path.stem, ingest.get("pages", []))
        runtime_schema = build_runtime_schema(industry)
        safe_write_json(self.report_dir / "runtime_schema.json", runtime_schema)
        metric_plans = build_metric_plans(ALL_SCHEMA)
        safe_write_json(self.report_dir / "metric_execution_plans.json", metric_plans)
        visual_plan = self._visual_plan(ingest)
        mineru_route_a = self._run_mineru_route_a(ingest)
        visual_plan["mineru_route_a_available"] = bool(mineru_route_a.get("available"))
        visual_plan["mineru_selected_tables"] = mineru_route_a.get("selected_tables", 0)
        visual_plan["mineru_row_count"] = mineru_route_a.get("row_count", 0)
        if mineru_route_a.get("available"):
            visual_plan["mode"] = "mineru_performance_tables"
            visual_plan["run_active_visual_extraction"] = False
        safe_write_json(self.report_dir / "visual_extraction_plan.json", visual_plan)

        standard_path = self.report_dir / "standard_esg_results.csv"
        if mineru_route_a.get("available"):
            visual_summary = {
                "status": "completed_mineru_route_a",
                "source": "mineru_performance_tables",
                "selected_tables": mineru_route_a.get("selected_tables", 0),
                "raw_row_count": mineru_route_a.get("row_count", 0),
                "extracted_fields": len(mineru_route_a.get("extracted_fields", [])),
                "visual_scan_skipped": True,
            }
        elif reuse_visual_results and self._can_reuse_visual_results(pdf_fingerprint):
            visual_summary: Dict[str, Any] = {
                "status": "reused",
                "path": str(standard_path),
                "pdf_fingerprint": pdf_fingerprint,
            }
        elif visual_plan["run_active_visual_extraction"]:
            route_a_state = self._run_visual_extraction(pdf_path)
            visual_summary = {
                "status": "completed",
                "raw_row_count": route_a_state.get("raw_row_count", 0),
                "extracted_fields": len(route_a_state.get("extracted_fields", [])),
            }
        else:
            self._write_empty_visual_baseline()
            visual_summary = {
                "status": "completed_no_summary_table",
                "raw_row_count": 0,
                "extracted_fields": 0,
            }
        manifest["routes"]["route_a_performance_tables"] = {
            "status": "completed",
            "summary": visual_summary,
            "raw_metric_store": mineru_route_a.get("raw_metric_store", {}),
        }
        manifest["routes"]["route_b_document_extraction"]["status"] = "running"
        self._write_run_manifest(manifest)

        table_arbitration_summary = self._prepare_table_arbitration(pdf_path)
        table_arbitration_summary["vlm"] = self._run_table_arbitration_vlm()
        extraction_summary = self._run_text_extraction(pdf_path)
        manifest["routes"]["route_b_document_extraction"] = {
            "status": "completed",
            "summary": extraction_summary,
        }
        manifest["routes"]["fusion"]["status"] = "running"
        self._write_run_manifest(manifest)

        evidence_summary, visual_followup_queue = self._build_evidence_and_followup(
            ingest=ingest,
            metric_plans=metric_plans,
            excluded_page_numbers=set(visual_plan["active_candidate_pages"]),
        )
        targeted_pages = []
        targeted_visual_summary: Dict[str, Any] = {"status": "not_needed", "pages": []}
        followup_page_budget = self._visual_followup_page_budget()
        if followup_page_budget and visual_followup_queue:
            targeted_pages = list(
                dict.fromkeys(
                    candidate["page_number"]
                    for item in visual_followup_queue
                    for candidate in item.get("candidate_visual_regions", [])
                    if candidate.get("page_number")
                )
            )[:followup_page_budget]
        if targeted_pages:
            targeted_visual_summary = self._run_targeted_visual_pages(pdf_path, targeted_pages)
            evidence_summary, visual_followup_queue = self._build_evidence_and_followup(
                ingest=ingest,
                metric_plans=metric_plans,
                excluded_page_numbers={
                    *visual_plan["active_candidate_pages"],
                    *targeted_pages,
                },
            )
            targeted_visual_summary["full_text_rerun_skipped"] = True
        merge_summary = self._run_merge()
        manifest["routes"]["fusion"] = {"status": "completed", "summary": merge_summary}

        summary = {
            "status": "completed",
            "run_mode": self.run_mode,
            "pdf_path": str(pdf_path),
            "report_dir": str(self.report_dir),
            "schema": {
                "industry": industry,
                "core_fields": len(ALL_SCHEMA),
                "runtime_fields": len(runtime_schema),
                "industry_extension_fields": sum(
                    item.get("schema_layer") == "industry_extension" for item in runtime_schema
                ),
                "path": str(self.report_dir / "runtime_schema.json"),
            },
            "document_ingest": {
                "cache_used": ingest["cache_used"],
                "text_available": ingest["manifest"].get("text_available", False),
                "total_pages": len(ingest["pages"]),
                "parser_name": ingest["manifest"].get("parser_name", "unknown"),
                "block_count": ingest["manifest"].get("block_count", len(ingest.get("blocks", []))),
                "document_model_path": ingest.get("paths", {}).get("document_model", ""),
                "pdf_fingerprint": pdf_fingerprint,
            },
            "metric_plans": {
                "count": len(metric_plans),
                "path": str(self.report_dir / "metric_execution_plans.json"),
            },
            "visual_plan": visual_plan,
            "table_arbitration": table_arbitration_summary,
            "visual_extraction": visual_summary,
            "extraction": extraction_summary,
            "evidence_store": evidence_summary,
            "visual_followup": {
                "queued_metrics": len(visual_followup_queue),
                "enabled": followup_page_budget > 0,
                "max_pages": followup_page_budget,
                "execution": targeted_visual_summary,
                "path": str(self.report_dir / "visual_followup_queue.json"),
            },
            "cost_tracking": {
                "summary_path": str(self.report_dir / "run_cost_summary.json"),
                "events_path": str(self.report_dir / "run_call_events.json"),
            },
            "merge": merge_summary,
        }
        safe_write_json(self.report_dir / "unified_pipeline_summary.json", summary)
        manifest["status"] = "completed"
        manifest["finished_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
        manifest["artifacts"] = {
            "document_model": ingest.get("paths", {}).get("document_model", ""),
            "markdown": ingest.get("paths", {}).get("markdown", ""),
            "raw_table_metrics": str(self.report_dir / "raw_table_metrics.json"),
            "merged_results": str(self.report_dir / "merged_esg_results.json"),
            "summary": str(self.report_dir / "unified_pipeline_summary.json"),
            "cost_summary": str(self.report_dir / "run_cost_summary.json"),
        }
        self._write_run_manifest(manifest)
        return summary
