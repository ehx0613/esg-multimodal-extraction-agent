# Architecture Upgrade Log - 2026-06-12

## Added

- Configurable MinerU automatic invocation adapter.
- Explicit parser selection and fallback diagnostics.
- Unified `document.md` export alongside DocModel, HTML tables, pages, blocks, and bbox.
- Independent deterministic performance-table detector.
- `raw_table_metrics.json` preserving all selected performance-table rows before schema matching.
- Unified pipeline-owned `run_manifest.json` with Route A, Route B, and Fusion lifecycle.
- Canonical current architecture document.
- GitHub Actions CI for tests and schema-document drift detection.
- Output ignore rules for MinerU and backup artifacts.

## Changed

- Runtime schema denominator references in operational scripts now use `CORE_SCHEMA_FIELD_COUNT`.
- Legacy agent harness manifest explicitly identifies itself as compatibility mode.
- Ingest version advanced to Document Model 1.1 / MinerU adapter v2.

## Deliberate Constraint

- Route A and Route B are not executed concurrently by default. They share
  report-directory artifacts, so naive parallel writes could corrupt or race
  `all_table_rows.json`, structured chunks, and Route B quantitative decisions.
  Logical route separation is complete; safe physical parallelism requires
  route-local staging directories in a later change.

## Verification

- Python compilation completed successfully for all changed Python modules.
- Affected architecture, MinerU, ingest, schema, merge, performance-control,
  review-template, and unified-pipeline tests: `49 passed`.
- `git diff --check`: passed.
- Full-suite collection is currently blocked by environment inconsistency:
  the default Python environment lacks `fastapi` and `faiss`, while the
  configured `pachong` environment lacks `pytest`.
