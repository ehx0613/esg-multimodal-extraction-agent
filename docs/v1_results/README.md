# v1 Results Archive

## Purpose

This directory stores historical baseline evaluation outputs and regression-check artifacts from the earlier stable batch runs.

These files are useful as reference material, but they are not the active evaluation workspace for new scoring work.

For active evaluation, use:

- `docs/eval/`

## File Guide

### `batch_summary_v1.csv`

Archived Route A batch summary snapshot.

### `route_b_batch_summary_v1.csv`

Archived Route B batch summary snapshot.

### `merge_batch_summary_v1.csv`

Archived merge summary snapshot.

### `per_report_evaluation_v1.csv`

Archived per-report evaluation table from the earlier baseline.

### `evaluation_summary_v1.json`

Structured summary of the earlier baseline evaluation.

### `evaluation_summary_v1.md`

Markdown summary of the earlier baseline evaluation.

### `evaluation_summary_v1_1_token_safe.md`

Alternative narrative summary for the token-safe stable baseline.

### `result_guard_check.csv`

Regression check output for result-guard behavior.

### `result_guard_check.json`

Structured version of the result-guard regression check.

### `supervisor_state_check.csv`

Snapshot of supervisor inspection states across reports.

### `supervisor_state_check.json`

Structured version of the supervisor state snapshot.

## Guidance

Use this directory when you need:

1. historical comparison
2. regression reference
3. evidence of prior stable batch behavior

Do not treat this directory as the main place for new evaluation work. New evaluation inputs and scoring should go to `docs/eval/`.
