# Unified ESG Extraction Pipeline

The user-facing extraction flow is now one pipeline:

```text
PDF ingest
  -> metric execution plans
  -> active extraction of high-value visual pages when detected
  -> unified text and structured-table RAG extraction
  -> low-cost visual proxy evidence registration
  -> evidence fusion and merge
```

Route A and Route B remain internal compatibility names. Users should run:

```powershell
python -m scripts.run_full_extraction <pdf-path-or-name>
```

Use `--force-visual` to ignore a reusable visual result from a previous unified
run. Visual results are reused only when the previous run has the same PDF
SHA-256 fingerprint.

## Main artifacts

- `metric_execution_plans.json`: schema-driven modality and verification plans.
- `visual_extraction_plan.json`: active visual pages and visual proxy pages.
- `evidence_records.json`: normalized text, table, and visual proxy evidence.
- `evidence_summary.json`: evidence counts and physical source-region counts.
- `visual_followup_queue.json`: missing or disputed metrics mapped to visual proxy regions.
- `merged_esg_results.json`: final field-level decisions.
- `unified_pipeline_summary.json`: complete orchestration summary.

## Missing visual baseline

No detected summary table is a valid outcome. The pipeline skips active Route A
processing, continues text and quantitative extraction, and lets Merge construct
an empty visual baseline. Missing, zero, not-applicable, and extraction failure
remain distinct states in downstream processing.

## Evidence lineage

Evidence derived from the same physical table shares `source_region_id`. Parser
and VLM readings of one table therefore remain alternative derivations of one
source rather than being counted as independent supporting evidence.

## Selective visual follow-up

After the first text/structured extraction pass, missing or disputed quantitative
metrics are matched to visual proxies. The pipeline processes at most three
unique follow-up pages by default, preserves the full VLM table cache, then
reruns unified extraction and Merge.

Configure this with:

```text
UNIFIED_ENABLE_VISUAL_FOLLOWUP=true
UNIFIED_VISUAL_FOLLOWUP_MAX_PAGES=3
```
