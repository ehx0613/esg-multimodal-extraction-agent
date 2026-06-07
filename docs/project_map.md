# Project Map

## Purpose

This document explains the code-level structure of the ESG Multimodal Extraction Agent repository.

It is intended to answer:

1. which files are core
2. where to start reading
3. which scripts are for stable operations
4. which files are historical or supporting

## Recommended Reading Paths

### If you want to understand the current extraction flow

1. `README.md`
2. `docs/architecture.md`
3. `pipeline/appendix_pipeline.py`
4. `pipeline/text_pipeline.py`
5. `pipeline/merge_pipeline.py`

### If you want to understand the new orchestration layer

1. `docs/architecture_v1_2_design.md`
2. `docs/implementation_plan_v1_2.md`
3. `agents/supervisor_agent.py`
4. `pipeline/agent_harness.py`

### If you want to run or inspect evaluations

1. `docs/eval/README.md`
2. `scripts/build_eval_from_outputs.py`
3. `scripts/analyze_v1_results.py`
4. `docs/eval/reviewer_checklist.md`

## Top-Level Directory Map

### `agents/`

Step-level agent implementations.

Most important files:

- `base_agent.py`
  - abstract base class for step-level Route A agents
- `appendix_sniffer_agent.py`
  - identifies appendix or performance-table candidate pages
- `page_render_agent.py`
  - renders PDF pages into images for downstream OCR
- `vlm_table_ocr_agent.py`
  - runs VLM-based table extraction from rendered images
- `schema_match_agent.py`
  - maps extracted rows into the core ESG schema
- `validation_agent.py`
  - summarizes Route A extraction quality
- `supervisor_agent.py`
  - route inspection, review trigger logic, and next-action support for the harness

Read this directory when:

1. you want to understand Route A step logic
2. you want to inspect supervisor behavior

### `pipeline/`

Workflow and orchestration layer.

Most important files:

- `appendix_pipeline.py`
  - Route A pipeline that chains the step-level agents
- `text_pipeline.py`
  - Route B pipeline for qualitative text extraction
- `merge_pipeline.py`
  - conservative merge of Route A and Route B outputs
- `agent_harness.py`
  - current orchestration layer that writes `run_manifest.json` and `human_review_queue.json`
- `batch_pipeline.py`
  - Route A batch runner logic for many PDFs

Read this directory when:

1. you want to understand full-route execution
2. you want to see where orchestration and route boundaries live

### `config/`

Project configuration and schema definitions.

Most important files:

- `settings.py`
  - environment variables, models, directory locations
- `core_schema.py`
  - core ESG schema used by matching and extraction
- `prompts.py`
  - prompt text used by LLM/VLM components

Read this directory when:

1. you want to change models
2. you want to inspect or evolve the ESG schema
3. you want to inspect prompt definitions

### `utils/`

Shared utility layer.

Most important files by purpose:

- PDF and page processing
  - `pdf_utils.py`
  - `pdf_text_utils.py`
- OCR and model calls
  - `vlm_client.py`
  - `llm_text_extractor.py`
  - `llm_schema_matcher.py`
  - `llm_unknown_metric_analyzer.py`
- matching and validation
  - `schema_matcher.py`
  - `schema_match_validator.py`
  - `result_guard.py`
- text processing
  - `text_chunker.py`
  - `route_b_retriever.py`
  - `text_utils.py`
- export and persistence
  - `csv_export.py`
  - `json_utils.py`

Read this directory when:

1. you need implementation details behind pipeline steps
2. you want to change matching, chunking, or result safety behavior

### `scripts/`

Operational entry points and analysis utilities.

Most useful scripts by category:

Stable run flow:

- `run_batch.py`
- `run_route_b_batch.py`
- `run_merge_batch.py`
- `analyze_v1_results.py`

Targeted rerun and repair:

- `rerun_schema_match.py`
- `rerun_schema_match_batch.py`
- `run_merge_single.py`
- `run_route_b_single.py`

Harness and diagnostics:

- `run_agent_harness_batch.py`
- `inspect_agent_state.py`
- `check_result_guard.py`

Evaluation:

- `build_eval_from_outputs.py`
- `analyze_v1_results.py`

Research and analysis helpers:

- `llm_analyze_unknown_metrics.py`
- `summarize_unknown_metrics.py`

Read this directory when:

1. you want command-line entry points
2. you want to know which script belongs to which operational task

### `docs/`

Human-facing project documentation.

Most important files:

- `README.md`
  - documentation index
- `architecture.md`
  - current stable baseline architecture
- `architecture_v1_2_design.md`
  - next-stage target architecture
- `implementation_plan_v1_2.md`
  - implementation order
- `runbook.md`
  - stable operational procedure
- `project_map.md`
  - this file
- `eval/`
  - active evaluation workspace
- `v1_results/`
  - historical baseline results archive

Read this directory when:

1. you want project intent and workflow context
2. you want to onboard another engineer quickly

### `output/`

Current run artifacts.

Expected active contents:

- `output/reports/`
  - per-report outputs
- `output/batch_summary.csv`
- `output/route_b_batch_summary.csv`
- `output/merge_batch_summary.csv`

Do not treat this directory as source code.

### `archive/`

Historical experiment snapshots and old broken-state outputs.

Use this only for historical debugging or comparison.

### `data/`

Input data staging area.

- `data/raw/`
  - PDFs to process
- `data/processed/`
  - reserved placeholder for downstream processing outputs

### `tests/`

Current test package placeholder.

Important note:

This directory exists, but meaningful automated tests are still missing. This remains one of the clearest engineering gaps in the project.

## Core Runtime Flow

The current intended runtime flow is:

1. place PDFs into `data/raw/`
2. run Route A batch or single-report processing
3. run Route B batch if needed
4. run merge
5. run evaluation aggregation
6. inspect `run_manifest.json`, `human_review_queue.json`, and `docs/eval/per_report_eval.csv`

## Files You Should Treat As Current Truth

When there is ambiguity, the current source-of-truth documents are:

1. `docs/architecture.md`
2. `docs/runbook.md`
3. `docs/architecture_v1_2_design.md`
4. `docs/implementation_plan_v1_2.md`
5. `docs/eval/README.md`

## Files You Should Treat As Historical Reference

These are useful, but not the active operating guide:

1. `docs/v1_results/*`
2. `archive/*`
3. `VERSION.md`

## Current Structural Gaps

The biggest remaining structure gaps are:

1. `tests/` is still mostly empty
2. some source files still contain encoding artifacts in comments or strings
3. script responsibilities are clearer now, but still somewhat numerous for a small repo
4. Route B is only partially integrated into a fully managed harness execution path
