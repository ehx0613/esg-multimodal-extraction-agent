# ESG Evaluation Workspace

> Historical evaluation notes below may use the retired 68-field denominator. New evaluations must use the canonical runtime schema count (currently 60).

## Purpose

This directory stores evaluation inputs, reviewer guidance, and per-report quality outputs for the ESG Multimodal Extraction Agent project.

These files are intentionally separated from `output/`:

1. `output/` is for run artifacts.
2. `docs/eval/` is for evaluation source-of-truth and review records.

## Files

### `golden_set.csv`

Curated list of reports used for stable regression evaluation.

Recommended use:

1. Start with approximately 20 representative reports.
2. Cover both easy and difficult reports.
3. Include reports with and without usable text layer.

### `per_report_eval.csv`

Per-report evaluation output template.

Recommended use:

1. Fill one row per evaluated run-report pair.
2. Record both automatic metrics and manual reviewer judgment.
3. Keep notes concise and action-oriented.

### `reviewer_checklist.md`

Manual scoring guide for:

1. `field_precision`
2. `unknown_metric_quality`
3. `final_grade`

## Core Metrics

The initial evaluation process should prioritize the following metrics:

1. `route_a_coverage`
   - `route_a_extracted_fields / 68`
2. `route_b_match_rate`
   - `route_b_matched_fields / route_b_target_fields`
3. `merged_coverage`
   - `merged_extracted_fields / 68`
4. `field_precision`
   - manually verified correct extracted fields divided by sampled reviewed fields
5. `unknown_metric_quality`
   - proportion of unknown metrics that were correctly excluded from the core schema

## Review Guidance

When reviewing a report, pay special attention to:

1. false positive schema matches
2. Route B low-confidence qualitative claims
3. merged fields that were filled only by Route B
4. abnormal unknown metric counts
5. reports with no text layer

## Initial Workflow

Recommended initial workflow:

1. populate `golden_set.csv`
2. run the current stable pipeline
3. inspect output artifacts under `output/reports/<report_id>/`
4. fill `per_report_eval.csv`
5. score manual fields with `reviewer_checklist.md`
6. summarize recurring failure patterns before changing prompts or matching logic

## Field-Level Manual Review

Generate a review sheet from one report's final merged output:

```powershell
python -m scripts.prepare_field_review "600587_新华医疗_2024"
```

The command accepts either a complete report directory or a unique partial
directory name. It writes a CSV and instructions under `docs/eval/reviews/`.

Fill the `review_result` column with one of:

- `correct`
- `wrong`
- `correct_missing`
- `missed`

For `wrong` and `missed`, also fill the golden value/evidence columns and
`error_type`. Start with rows whose `review_priority` begins with `high_`.
