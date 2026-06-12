# Schema Evolution Plan

## Frozen Core

The canonical core remains `core_esg_v4.1_60` with 60 fields. Core coverage and scoring denominators must not include candidate or industry-extension fields.

## Route A Artifact Chain

Each Route A run now preserves:

```text
all_table_rows.json
-> raw_table_metrics.json
-> metric_candidates.json
-> validated_metrics.json
-> standard_esg_results.json
```

`raw_table_metrics.json` preserves every performance-table row, including rows that are index-like or cannot map to the core schema.

## Disclosure Topics And Route B Candidates

`config/schema/topics.py` defines the disclosure-topic layer.

`config/schema/route_b_candidates.py` defines 15 high-priority qualitative candidates. They are intentionally excluded from the frozen 60-field core until Golden Set evaluation demonstrates sufficient value and extraction quality.

## Industry Runtime Schema

`build_runtime_schema(industry)` combines:

- the frozen 60-field core;
- field-level applicability labels;
- industry-extension fields for finance, manufacturing, and pharma.

The unified pipeline writes `runtime_schema.json`. Industry extensions do not change the core coverage denominator.

## Golden Set

Use `docs/eval/golden_set.csv` as the report registry and `docs/eval/golden_set_field_annotations.csv` for field-level labels.

Recommended evaluation:

```text
precision = correct_extracted / all_extracted
recall = correct_extracted / all_expected
f1 = 2 * precision * recall / (precision + recall)
```

Promote a candidate into the core only after reviewing enough reports and documenting its precision, recall, applicability, and scoring purpose.
