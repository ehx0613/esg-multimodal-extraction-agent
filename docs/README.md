# Documentation Guide

## Current Sources Of Truth

1. [`architecture_current.md`](architecture_current.md) - current architecture,
   Mermaid diagrams, runtime sequence, ownership, and artifact contracts.
2. [`project_memory/ARCHITECTURE_AND_OPERATIONS.md`](project_memory/ARCHITECTURE_AND_OPERATIONS.md)
   - current operating commands, diagnostics, and source map.
3. [`worklogs/2026-06-12_architecture_upgrade.md`](worklogs/2026-06-12_architecture_upgrade.md)
   - implementation record for the MinerU ingestion and unified pipeline upgrade.

## Evaluation And Schema

- `schema/core_schema_readable.md` - readable canonical 60-field schema.
- `schema_60_migration_summary.md` - schema migration record.
- `eval/README.md` - evaluation workflow and metric definitions.
- `v1_results/` - historical baseline and regression artifacts.

## Historical And Planning Documents

- `architecture.md` - former v1.1 baseline; historical reference only.
- `architecture_v1_2_design.md` - original target design; largely implemented.
- `implementation_plan_v1_2.md` - original implementation plan.

When documents disagree, use `architecture_current.md` as the architecture
source of truth and verify behavior against `pipeline/unified_pipeline.py`.
