# Documentation Guide

## Purpose

This directory contains the current architecture documents, implementation plans, evaluation workspace, and historical baseline results for the ESG Multimodal Extraction Agent project.

## Recommended Reading Order

### If you want to understand the current system

1. `architecture.md`
2. `runbook.md`
3. `project_map.md`

### If you want to understand the next architecture step

1. `architecture_v1_2_design.md`
2. `implementation_plan_v1_2.md`

### If you want to evaluate model and extraction quality

1. `eval/README.md`
2. `eval/golden_set.csv`
3. `eval/per_report_eval.csv`
4. `eval/reviewer_checklist.md`

### If you want historical baseline evidence

1. `v1_results/README.md`

## Document Map

### `architecture.md`

Describes the current stable v1.1 baseline architecture.

### `architecture_v1_2_design.md`

Defines the target v1.2 orchestration design, including run manifest, state contracts, evaluation, and human review.

### `implementation_plan_v1_2.md`

Turns the v1.2 design into a practical implementation order and ownership checklist.

### `runbook.md`

Documents the stable operational sequence for rerun, Route B, merge, and result validation.

### `project_map.md`

Explains the code-level repository structure and where to start reading different parts of the system.

### `eval/`

Stores the current evaluation workspace:

- `README.md`
  - evaluation purpose and metric definitions
- `golden_set.csv`
  - curated evaluation sample list
- `per_report_eval.csv`
  - per-report evaluation output
- `reviewer_checklist.md`
  - manual scoring guide

### `v1_results/`

Stores historical baseline evaluation artifacts and regression outputs from the earlier stable runs.

### `../archive/`

Stores archived experiment or failure snapshots that are not part of the active workflow.

## Status Guidance

- `architecture.md`
  - current truth for stable architecture
- `runbook.md`
  - current truth for stable operation
- `architecture_v1_2_design.md`
  - target-state design
- `implementation_plan_v1_2.md`
  - active execution plan
- `eval/`
  - active evaluation workspace
- `v1_results/`
  - historical reference outputs
- `../archive/`
  - archived experiment snapshots
