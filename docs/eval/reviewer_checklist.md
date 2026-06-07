# ESG Manual Review Checklist

## Purpose

This checklist defines how to manually score the fields in `docs/eval/per_report_eval.csv` that cannot be filled reliably by automation alone.

The current manual scoring focus is:

- `field_precision`
- `unknown_metric_quality`
- `final_grade`

This checklist is intended for fast, repeatable review of one report at a time.

## Inputs

For each report under review, prepare the following artifacts:

1. `output/reports/<report_id>/standard_esg_results.csv`
2. `output/reports/<report_id>/unknown_metrics.csv`
3. `output/reports/<report_id>/merged_esg_results.csv`
4. `output/reports/<report_id>/route_b_text_results.csv`
5. `output/reports/<report_id>/run_manifest.json`
6. `output/reports/<report_id>/human_review_queue.json`, if present
7. the original PDF report

## Review Workflow

Recommended workflow:

1. open the original PDF
2. inspect `run_manifest.json` and `human_review_queue.json`
3. sample extracted core fields from `merged_esg_results.csv`
4. inspect the matching rows in `standard_esg_results.csv` and `route_b_text_results.csv`
5. inspect a sample of `unknown_metrics.csv`
6. assign `field_precision`
7. assign `unknown_metric_quality`
8. assign `final_grade`
9. record concise notes in `per_report_eval.csv`

## How To Score `field_precision`

### Definition

`field_precision` means:

the proportion of sampled extracted fields that are judged correct after manual inspection

### Sampling Rule

Recommended minimum sample size per report:

1. if merged extracted fields are fewer than 10, review all extracted fields
2. if merged extracted fields are 10 to 30, review at least 10 fields
3. if merged extracted fields are above 30, review at least 15 fields

### A Field Counts As Correct When

All of the following are true:

1. the field is matched to the correct ESG concept
2. the value is materially correct
3. the evidence or source pages are plausible
4. the route used is reasonable for that field

### A Field Counts As Incorrect When

Any of the following is true:

1. wrong schema field
2. wrong numeric value
3. value copied from unrelated context
4. qualitative statement is unsupported by the cited evidence
5. merged result chose a clearly wrong route output

### Formula

```text
field_precision = correct_sampled_fields / sampled_fields
```

### Example

If 12 fields are reviewed and 9 are correct:

```text
field_precision = 9 / 12 = 0.75
```

## How To Score `unknown_metric_quality`

### Definition

`unknown_metric_quality` means:

the proportion of sampled unknown metrics that were correctly excluded from the core schema

### Sampling Rule

Recommended minimum sample size:

1. if unknown metrics are fewer than 10, review all of them
2. if unknown metrics are 10 to 50, review at least 10
3. if unknown metrics are above 50, review at least 15

### An Unknown Metric Counts As Good When

At least one of the following is true:

1. it is company-specific and does not belong in the core schema
2. it is too vague or non-metric to map safely
3. it would be a false positive if forced into a core field

### An Unknown Metric Counts As Bad When

At least one of the following is true:

1. it clearly should have been matched to an existing core field
2. it is a duplicate phrasing of a known field
3. the exclusion happened because schema aliases or matching logic are weak

### Formula

```text
unknown_metric_quality = good_unknown_metrics / sampled_unknown_metrics
```

## How To Assign `final_grade`

Use the following coarse grade bands:

### `strong`

Use when most of the following are true:

1. merged coverage is relatively strong for the report type
2. field precision appears high
3. unknown metric handling is reasonable
4. review queue is empty or low-risk

### `usable_with_review`

Use when:

1. the output is useful
2. some manual cleanup or confirmation is still needed
3. a few wrong matches or review items exist but the report is still operationally valuable

### `weak`

Use when:

1. merged coverage is low
2. many sampled fields are wrong
3. unknown metric handling is noisy
4. review burden is high

### `blocked`

Use when:

1. key route artifacts are missing or invalid
2. the extracted result is too incomplete to trust
3. major failures prevent meaningful downstream use

### `pending_manual_review`

Use only as a temporary placeholder before human scoring is completed.

## Notes Guidance

Notes in `per_report_eval.csv` should be short and actionable.

Good examples:

- `Route B unavailable due to no text layer; Route A usable but coverage is modest`
- `Several environmental fields appear correct, but employee metrics are under-matched`
- `Unknown metrics contain many alias-like rows and should be sampled for schema expansion`

Avoid vague notes such as:

- `looks okay`
- `not very good`

## Recommended First Review Priorities

When review time is limited, prioritize reports with:

1. `needs_human_review = true`
2. low `merged_coverage`
3. high `unknown_metric_count`
4. `route_b_available = false`
5. low `route_b_match_rate`

## Suggested Update Workflow

After manual review:

1. update `field_precision`
2. update `unknown_metric_quality`
3. update `final_grade`
4. refine `notes`
5. keep `run_id` and automatic metrics unchanged
