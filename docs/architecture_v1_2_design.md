# ESG Multimodal Extraction Agent v1.2 Design

## Purpose

This document defines the planned v1.2 architecture upgrade for the current stable v1.1 baseline.

The goal of v1.2 is not to change extraction semantics. The goal is to make the existing system easier to operate, evaluate, resume, and review under a more standard agent workflow architecture.

This design is intentionally aligned with the current repository layout:

- `agents/`
- `pipeline/`
- `utils/`
- `config/`
- `scripts/`
- `docs/`
- `output/`

The v1.2 design keeps the current Route A, Route B, and Merge logic stable while adding a stronger orchestration layer above them.

## Design Goals

The v1.2 upgrade should achieve the following:

1. Introduce one top-level run record per report.
2. Define explicit state and artifact contracts between stages.
3. Make Route A, Route B, and Merge easier to resume and validate independently.
4. Introduce task-level evaluation metrics in addition to file existence checks.
5. Add a human review queue for low-confidence or abnormal outputs.

The v1.2 upgrade should not do the following:

1. Rewrite `SchemaMatchAgent`.
2. Rewrite `VLMTableOCRAgent`.
3. Rewrite `ESGTextPipeline`.
4. Rewrite the current merge semantics.
5. Replace the existing stable batch scripts before the harness is proven.

## Current Repository Mapping

The current repository already contains most of the core business logic needed by the future harness:

- Route A agent chain:
  - `agents/appendix_sniffer_agent.py`
  - `agents/page_render_agent.py`
  - `agents/vlm_table_ocr_agent.py`
  - `agents/schema_match_agent.py`
  - `agents/validation_agent.py`
- Route A pipeline:
  - `pipeline/appendix_pipeline.py`
- Route B pipeline:
  - `pipeline/text_pipeline.py`
- Merge pipeline:
  - `pipeline/merge_pipeline.py`
- Current supervisor and harness entry points:
  - `agents/supervisor_agent.py`
  - `pipeline/agent_harness.py`
- Run safety and validation helpers:
  - `utils/result_guard.py`
- Stable operational process:
  - `docs/runbook.md`

The main gap is therefore not missing extraction logic. The main gap is missing orchestration protocol.

## Target v1.2 Architecture

The target v1.2 architecture is a workflow-first agent system with explicit contracts.

```text
PDF report
  |
  v
Run Manifest
  |
  v
Supervisor / Harness
  |
  +--> Route A: Appendix Table Extraction
  |
  +--> Route B: Text RAG Extraction
  |
  +--> Merge
  |
  +--> Evaluation
  |
  +--> Human Review Queue
```

The key architectural change is that Route A, Route B, Merge, and Evaluation are no longer connected only by filenames and scripts. They are connected by:

1. One run manifest
2. One route registry
3. One shared status model
4. Explicit artifact contracts
5. Standard failure and review rules

## Top-Level Run Manifest

### Purpose

The run manifest becomes the single run-level source of truth for one report execution.

It should record:

- report identity
- configuration snapshot
- route status
- artifact paths
- warnings
- errors
- next actions
- human review items

This manifest should live under each report output directory.

Recommended path:

```text
output/reports/<report_id>/run_manifest.json
```

### Suggested Schema

```json
{
  "run_id": "2026-05-15_000858_report_xxx",
  "report_id": "000858_2024_xxx",
  "report_name": "五粮液：2024年度环境、社会及公司治理（ESG）报告",
  "pdf_path": "data/raw/xxx.pdf",
  "output_dir": "output/reports/000858_2024_xxx",
  "started_at": "2026-05-15T10:30:00+08:00",
  "finished_at": null,
  "status": "running",
  "mode": "stable_v1_1",
  "config_snapshot": {
    "vlm_model": "qwen-vl-plus",
    "text_model": "qwen-plus-2025-07-28",
    "llm_matcher_enabled": false,
    "expected_core_fields": 68,
    "route_b_enabled": true,
    "merge_min_route_b_confidence": 0.5
  },
  "artifacts": {
    "all_table_rows_json": null,
    "standard_results_csv": null,
    "unknown_metrics_csv": null,
    "route_b_results_csv": null,
    "merged_results_csv": null,
    "validation_summary_json": null,
    "merge_summary_json": null
  },
  "routes": {
    "route_a": {
      "status": "pending",
      "started_at": null,
      "finished_at": null,
      "steps": {
        "appendix_sniffer": { "status": "pending", "error": null },
        "page_render": { "status": "pending", "error": null },
        "vlm_table_ocr": { "status": "pending", "error": null },
        "schema_match": { "status": "pending", "error": null },
        "validation": { "status": "pending", "error": null }
      },
      "summary": {
        "raw_row_count": null,
        "extracted_fields": null,
        "unknown_metrics": null,
        "coverage_rate": null
      }
    },
    "route_b": {
      "status": "pending",
      "started_at": null,
      "finished_at": null,
      "summary": {
        "route_b_available": null,
        "matched_fields": null,
        "reason": null
      }
    },
    "merge": {
      "status": "pending",
      "started_at": null,
      "finished_at": null,
      "summary": {
        "route_a_extracted_fields": null,
        "route_b_matched_fields": null,
        "route_b_filled_fields": null,
        "merged_extracted_fields": null,
        "coverage_rate": null
      }
    }
  },
  "warnings": [],
  "errors": [],
  "human_review_queue": [],
  "next_actions": []
}
```

### Required Status Values

All route and step states should use the same five statuses:

- `pending`
- `running`
- `completed`
- `failed`
- `skipped`

This standardization is important for resumable execution and future dashboards.

## Route Registry

The harness should use a small internal route registry instead of hard-coded loose script order.

Suggested route keys:

- `route_a_appendix_table`
- `route_b_text_rag`
- `merge`
- `evaluation`
- `human_review`

Each route should declare:

- route name
- owner component
- required inputs
- expected outputs
- resume rule
- validation rule

This does not require replacing the current code immediately. The first v1.2 step can wrap the existing pipelines with route metadata.

## State Contract

### Core Principle

Each route or agent step must declare:

1. required inputs
2. in-memory state outputs
3. artifact outputs
4. failure conditions
5. summary fields

This should reduce ambiguity in the current `dict`-based state passing model and make the behavior of `SupervisorAgent` more deterministic.

### Route A Contract

Route A remains implemented by `pipeline.appendix_pipeline.ESGAppendixPipeline`.

#### Step 1: `AppendixSnifferAgent`

Source file:

```text
agents/appendix_sniffer_agent.py
```

Required inputs:

- `pdf_path`

In-memory outputs:

- `sniffer_result`
- `appendix_found`
- `candidate_pages`

Artifact outputs:

- none required in v1.1

Failure conditions:

- unreadable PDF
- appendix page detection exception

Summary fields:

- `appendix_found`
- `candidate_page_count`

#### Step 2: `PageRenderAgent`

Source file:

```text
agents/page_render_agent.py
```

Required inputs:

- `pdf_path`
- `candidate_pages`

In-memory outputs:

- `page_images`

Artifact outputs:

- rendered page images under the report output directory

Failure conditions:

- candidate pages empty when route expects appendix extraction
- PDF render exception

Summary fields:

- `rendered_page_count`

#### Step 3: `VLMTableOCRAgent`

Source file:

```text
agents/vlm_table_ocr_agent.py
```

Required inputs:

- `page_images`

In-memory outputs:

- `all_table_rows`

Artifact outputs:

- `all_table_rows.json`

Failure conditions:

- VLM request failure
- malformed OCR response

Behavior note:

Single-page OCR failures should not automatically fail the entire route if the route can still produce a partial diagnostic artifact.

Summary fields:

- `ocr_page_count`
- `ocr_error_page_count`
- `table_count`

#### Step 4: `SchemaMatchAgent`

Source file:

```text
agents/schema_match_agent.py
```

Required inputs:

- `all_table_rows`

In-memory outputs:

- `standard_results`
- `unknown_metrics`
- `extracted_fields`
- `missing_fields`
- `raw_row_count`

Artifact outputs:

- `standard_esg_results.json`
- `unknown_metrics.json`
- `standard_esg_results.csv`
- `unknown_metrics.csv`

Failure conditions:

- schema load failure
- row normalization failure
- final output field count mismatch

Summary fields:

- `raw_row_count`
- `extracted_field_count`
- `missing_field_count`
- `unknown_metric_count`

#### Step 5: `ValidationAgent`

Source file:

```text
agents/validation_agent.py
```

Required inputs:

- `standard_results`
- `unknown_metrics`
- `raw_row_count`

In-memory outputs:

- `validation_summary`

Artifact outputs:

- `validation_summary.json`
- `pipeline_state.json`

Failure conditions:

- invalid summary generation
- output write failure

Summary fields:

- `total_fields`
- `extracted_fields`
- `missing_fields`
- `coverage_rate`
- `unknown_metrics`

### Route B Contract

Route B remains implemented by `pipeline.text_pipeline.ESGTextPipeline`.

Required inputs:

- `pdf_path`
- `CORE_SCHEMA` subset where `preferred_source == "main_text_rag"`

In-memory outputs:

- per-field text extraction results
- route summary

Artifact outputs:

- `route_b_text_pages.json`
- `route_b_chunks.json`
- `route_b_text_results.json`
- `route_b_text_results.csv`
- `route_b_summary.json`

Required row-level fields:

- `field_key`
- `field_name_cn`
- `category`
- `matched`
- `value`
- `summary`
- `evidence`
- `source_pages`
- `confidence`
- `reason`
- `route`

Failure conditions:

- PDF text extraction exception
- chunking exception
- LLM extraction exception

Special skip behavior:

If the report has no sufficient text layer, the route should complete with a structured skip-like summary rather than disappear silently.

Required summary fields:

- `route_b_available`
- `total_pages`
- `chunks`
- `target_fields`
- `matched_fields`
- `reason`

### Merge Contract

Merge remains implemented by `pipeline.merge_pipeline.ESGMergePipeline`.

Required inputs:

- `standard_esg_results.csv`
- `route_b_text_results.csv`

Artifact outputs:

- `merged_esg_results.csv`
- `merged_esg_results.json`
- `merge_summary.json`

Merge policy:

1. Route A is primary when Route A has already extracted the field.
2. Route B may add supplementary evidence to Route A results.
3. Route B may fill a field only when Route A is missing and Route B confidence passes the configured threshold.

Failure conditions:

- invalid Route A row count
- malformed Route B rows
- merged final row count mismatch

Required summary fields:

- `total_fields`
- `route_a_extracted_fields`
- `route_b_matched_fields`
- `route_b_filled_fields`
- `merged_extracted_fields`
- `missing_fields`
- `coverage_rate`

## Supervisor Responsibilities

The current `SupervisorAgent` should evolve from output inspection logic into a true route orchestration component.

The future v1.2 supervisor should own:

1. run manifest initialization
2. route readiness checks
3. artifact existence checks
4. route-level validation checks
5. resumable step decisions
6. warning and error aggregation
7. human review item generation
8. next-action recommendation

The supervisor should not become responsible for core extraction semantics. Its job is coordination, not extraction.

## Evaluation Design

### Purpose

The project already has file-level stability checks and batch summaries. v1.2 should add task-level evaluation so the team can measure extraction quality, not only output completeness.

### Golden Set

Recommended new evaluation input:

```text
docs/eval/golden_set.csv
```

Suggested columns:

```csv
report_id,report_name,has_text_layer,table_quality,expected_route_a_difficulty,expected_route_b_difficulty,review_status,notes
```

The first evaluation set does not need to be large. A curated set of approximately 20 representative reports is enough for early regression control.

### Per-Report Evaluation Output

Recommended output:

```text
docs/eval/per_report_eval.csv
```

Suggested columns:

```csv
run_id,report_id,route_a_ok,route_a_coverage,route_b_available,route_b_match_rate,merged_coverage,field_precision,unknown_metric_quality,needs_human_review,final_grade,notes
```

### Core Metrics

The v1.2 evaluation layer should prioritize the following metrics:

1. `route_a_coverage`
   - definition: `route_a_extracted_fields / 68`
2. `route_b_match_rate`
   - definition: `route_b_matched_fields / route_b_target_fields`
3. `merged_final_coverage`
   - definition: `merged_extracted_fields / 68`
4. `field_precision`
   - definition: manually verified correct extracted fields divided by sampled reviewed fields
5. `unknown_metric_quality`
   - definition: proportion of unknown metrics judged to be correctly excluded from the core schema

### Evaluation Scope

Evaluation should cover at least the following report types:

- reports with strong text layer
- reports with weak or missing text layer
- reports with clean performance tables
- reports with visually complex tables
- reports with many custom indicators
- reports with common, highly standardized core fields

## Human Review Queue

### Purpose

For ESG extraction, the ideal production pattern is not full autonomy. The more reliable pattern is automation with selective human review.

The v1.2 design therefore introduces a structured review queue.

Recommended storage:

```text
output/reports/<report_id>/human_review_queue.json
```

### Review Trigger Rules

The supervisor should generate review items when one or more of the following conditions occur:

1. confidence lower than the configured threshold
2. Route A and Route B produce conflicting values for the same field
3. unknown metric count is abnormally high
4. `standard_row_count != 68`
5. `merged_row_count != 68`
6. `route_b_available == false`
7. OCR page error rate exceeds threshold
8. multiple competing candidates exist for one field with similar confidence

### Review Item Schema

```json
{
  "review_id": "rvw_0001",
  "report_id": "000858_2024_xxx",
  "field_key": "environmental_target_policy",
  "source_route": "route_b_text_rag",
  "reason": "low_confidence",
  "confidence": 0.54,
  "evidence": "...",
  "source_pages": [12, 13],
  "recommended_action": "human_confirm_or_reject",
  "status": "pending"
}
```

### Review Status Values

Recommended statuses:

- `pending`
- `accepted`
- `rejected`
- `resolved`

## Resumable Execution Rules

The v1.2 harness should support partial reruns without deleting unrelated artifacts.

Recommended rules:

1. If Route A artifacts are valid, Route A may be skipped.
2. If Route B summary says no usable text layer, Route B should be marked as completed with a structured reason, not retried blindly.
3. If Merge output is missing or invalid, Merge may rerun without forcing Route A rerun.
4. If one route fails, unrelated valid route artifacts should remain intact.
5. Failed step diagnostics should remain preserved in the manifest.

This resumable behavior should be implemented above the current pipelines, not by rewriting their internal logic first.

## Observability Expectations

The current project already has good file-based diagnostics. v1.2 should extend this with run-level observability.

Minimum recommended additions:

1. per-run `run_id`
2. per-route status timestamps
3. structured warning codes
4. structured error codes
5. step summary fields written into the run manifest

More advanced tracing can be added later. It is not required for the first v1.2 design pass.

## Recommended Documentation Layout

To keep the repository documentation clear, the following structure is recommended:

- `docs/architecture.md`
  - current stable baseline architecture
- `docs/architecture_v1_2_design.md`
  - target v1.2 orchestration design
- `docs/runbook.md`
  - stable operating procedure
- `docs/eval/`
  - future evaluation inputs and outputs

This allows the repository to keep both:

1. a truthful description of the current system
2. a concrete design for the next architectural step

## Implementation Priority

The recommended implementation order for the v1.2 design is:

1. add `run_manifest.json`
2. standardize route and step statuses
3. document and enforce state contracts
4. add human review queue generation
5. add evaluation dataset and per-report evaluation outputs
6. expand supervisor responsibilities

This ordering intentionally prioritizes protocol before feature growth.

## Non-Goals

The following are not part of the first v1.2 architecture pass:

1. replacing all current dict-based state with a new framework immediately
2. introducing highly autonomous tool-using agents
3. replacing stable scripts with a complex scheduler before the contracts are defined
4. changing the business meaning of existing output CSV files
5. optimizing prompts before evaluation baselines exist

## Summary

The current repository already contains a usable agent-oriented extraction core.

The v1.2 architecture should therefore focus on system organization rather than model novelty:

- one run manifest
- explicit state contracts
- route-level orchestration
- evaluation metrics
- human review integration

If these pieces are added cleanly, the project will evolve from a stable multi-stage extraction workflow into a more production-ready agent workflow system without sacrificing the reliability of the current baseline.
