# ESG Multimodal Extraction Agent Runbook

## Purpose

This runbook documents the current stable v1.1 token-safe operating sequence.

The stable baseline keeps schema reruns conservative and avoids LLM fallback during large-scale schema matching.

## Required Stable Setting

Before running the stable schema rerun flow, keep:

```text
LLM_MATCHER_ENABLED=false
```

This value can come from `.env` or the active process environment. The runbook documents the required setting only; it does not require editing `.env`.

## Stable Run Order

Use the following order for the current stable baseline:

```bash
python -m scripts.rerun_schema_match_batch
python -m scripts.run_merge_batch
python -m scripts.analyze_v1_results
```

This sequence assumes Route A artifacts already exist under `output/reports/*` and that any Route B artifacts needed by merge already exist in the corresponding report directories.

## When Route B Needs To Be Generated

If `route_b_text_results.csv` has not been generated for the report directories, run Route B before merge:

```bash
python -m scripts.run_route_b_batch
```

In that case, the practical full sequence is:

```bash
python -m scripts.rerun_schema_match_batch
python -m scripts.run_route_b_batch
python -m scripts.run_merge_batch
python -m scripts.analyze_v1_results
```

## ResultGuard Regression Validation

After changing any Route A or merge result-writing path, run the following regression checks before treating the run as stable.

Primary validation goals:

- `standard_esg_results.csv` must not be overwritten with abnormal small-row outputs.
- `merged_esg_results.csv` must not be overwritten with abnormal small-row outputs.
- CSV writing must tolerate extra keys such as `column_label`.
- ResultGuard checks must complete without modifying existing files under `output/`.

### Validation Commands

Use the repository root as the working directory.

On Windows in this workspace, prefer:

```bash
py -3 -m py_compile scripts/rerun_schema_match.py pipeline/merge_pipeline.py utils/result_guard.py scripts/check_result_guard.py
py -3 scripts/check_result_guard.py
```

If `python` is available in the current shell, the equivalent commands are:

```bash
python -m py_compile scripts/rerun_schema_match.py pipeline/merge_pipeline.py utils/result_guard.py scripts/check_result_guard.py
python scripts/check_result_guard.py
```

### Validation Expectations

- Compile step succeeds with no syntax errors.
- `scripts/check_result_guard.py` completes without interruption.
- The script writes:
  - `docs/v1_results/result_guard_check.csv`
  - `docs/v1_results/result_guard_check.json`
- Reports that do not contain `standard_esg_results.csv` or `merged_esg_results.csv` are recorded as warnings, not hard failures.
- Reports with valid stable outputs should show:
  - `standard_ok=true`
  - `standard_row_count=68`
  - `merged_ok=true`
  - `merged_row_count=68`

### When To Run This Validation

Run this ResultGuard regression validation after:

- changing `scripts/rerun_schema_match.py`
- changing `pipeline/merge_pipeline.py`
- changing `utils/result_guard.py`
- changing any script that writes `standard_esg_results.csv`
- changing any script or pipeline stage that writes `merged_esg_results.csv`

## Step Details

### 1. Schema Match Rerun

Command:

```bash
python -m scripts.rerun_schema_match_batch
```

Purpose:

- Reprocess existing `all_table_rows.json` files in `output/reports/*`.
- Regenerate Route A schema match outputs.
- Use the current conservative matcher behavior when `LLM_MATCHER_ENABLED=false`.

Expected per-report inputs:

- `all_table_rows.json`

Expected per-report outputs:

- `standard_esg_results.csv`
- `standard_esg_results.json`
- `unknown_metrics.csv`
- `unknown_metrics.json`

### 2. Route B Batch, If Needed

Command:

```bash
python -m scripts.run_route_b_batch
```

Purpose:

- Build/load one reusable RAG corpus and vector index.
- Extract qualitative ESG mechanism indicators from report text.
- Retrieve evidence for all Route A quantitative fields from the shared index.
- Call the quantitative extractor only for missing, low-confidence, zero-valued,
  or conflicting Route A fields.
- Reuse the same ingest result and combined text/table chunks for both stages.

Expected per-report outputs:

- `route_b_text_pages.json`
- `route_b_chunks.json`
- `route_b_combined_chunks.json`
- `route_b_text_results.csv`
- `route_b_text_results.json`
- `route_b_quant_results.csv`
- `route_b_quant_results.json`
- `route_b_quant_summary.json`
- `route_b_summary.json`

Normal operation should run `scripts.run_route_b_batch` once. Historical
`route_b2_*` artifacts are ignored by merge and are no longer generated.

### 3. Merge Batch

Command:

```bash
python -m scripts.run_merge_batch
```

Purpose:

- Merge Route A and Route B results per report.
- Preserve Route A extracted values as the primary source.
- Use Route B to fill missing qualitative fields when confidence is sufficient.

Expected per-report inputs:

- `standard_esg_results.csv`
- `route_b_text_results.csv`, when available

Expected per-report outputs:

- `merged_esg_results.csv`
- `merged_esg_results.json`
- `merge_summary.json`

Expected batch output:

- `output/merge_batch_summary.csv`

### 4. Analyze v1 Results

Command:

```bash
python -m scripts.analyze_v1_results
```

Purpose:

- Read Route A, Route B, and merge batch summaries.
- Generate evaluation artifacts under `docs/v1_results/`.

Expected inputs:

- `output/batch_summary.csv`
- `output/route_b_batch_summary.csv`
- `output/merge_batch_summary.csv`

Expected outputs:

- `docs/v1_results/per_report_evaluation_v1.csv`
- `docs/v1_results/evaluation_summary_v1.json`
- `docs/v1_results/evaluation_summary_v1.md`

## Stability Notes

- Keep `LLM_MATCHER_ENABLED=false` for stable schema reruns.
- Use LLM behavior mainly for Route B text extraction and unknown metric analysis.
- Avoid enabling schema-match LLM fallback during large batch reruns unless the run is explicitly experimental.
- Do not manually edit generated files in `output/` as part of the stable run flow.
- Treat `docs/v1_results/` as evaluation documentation produced from batch outputs.

## Files Not Modified By This Runbook

This runbook does not require changes to:

- Existing Python source code
- `.env`
- `output/`

The stable flow should be operated through scripts and environment configuration, not by changing core extraction logic.
