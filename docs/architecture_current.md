# Current Architecture

Canonical schema: `core_esg_v4.1_60` with 60 fields.

```text
PDF
 -> MinerU auto-run adapter or existing MinerU output
 -> PyMuPDF fallback with explicit reason
 -> document.md + unified DocModel + HTML tables + bbox
 -> Route A performance-table detector
 -> raw_table_metrics.json
 -> deterministic schema matching
 -> Route B qualitative and quantitative document extraction
 -> evidence quality, arbitration, and safe fusion
 -> merged results, run manifest, cost log, and review queue
```

## Responsibilities

- MinerU/PyMuPDF: document parsing only.
- Performance-table detector: identifies candidate KPI tables only.
- Route A: preserves every raw KPI row, then maps validated rows to the schema.
- Route B: extracts qualitative fields and supplements missing/uncertain quantitative fields.
- Fusion: applies conservative source selection and preserves conflicts for review.
- Unified pipeline: canonical run lifecycle and manifest owner.
- Legacy harness: compatibility and database tracking wrapper.

## Parallelism

Route A and Route B are logically independent after ingest, but both currently
share report-directory artifacts. Parallel execution remains disabled by
default until route-local temporary artifact directories are introduced.
