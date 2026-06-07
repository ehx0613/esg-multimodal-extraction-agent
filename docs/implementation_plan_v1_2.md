# ESG Multimodal Extraction Agent v1.2 Implementation Plan

## Purpose

This document turns the v1.2 architecture design into an implementation checklist aligned with the current repository.

It is intended to answer three practical questions:

1. What should be implemented first.
2. Which file or module should own each change.
3. How to upgrade the architecture without destabilizing the current v1.1 baseline.

This plan is designed to work with the current codebase, especially:

- `agents/supervisor_agent.py`
- `pipeline/agent_harness.py`
- `pipeline/appendix_pipeline.py`
- `pipeline/text_pipeline.py`
- `pipeline/merge_pipeline.py`
- `utils/result_guard.py`
- `docs/`

## Guiding Principles

The v1.2 implementation should follow these rules:

1. Keep existing extraction logic stable.
2. Add orchestration protocol before adding more agent autonomy.
3. Prefer additive changes over disruptive rewrites.
4. Keep all batch operations resumable.
5. Make evaluation and review explicit, not implicit.

## Delivery Phases

The recommended implementation order is:

1. Phase 1: Run manifest and shared status model
2. Phase 2: Supervisor and harness responsibility upgrade
3. Phase 3: Evaluation dataset and per-report evaluation outputs
4. Phase 4: Human review queue and review triggers
5. Phase 5: Optional observability improvements

The most important architectural rule is:

Do not redesign Route A, Route B, or Merge internals before the run-level protocol exists.

## Phase 1: Run Manifest and Shared Status Model

### Goal

Introduce one top-level run record for each report execution.

### Primary Ownership

- `pipeline/agent_harness.py`
- `agents/supervisor_agent.py`
- optional new helper module under `utils/` or `pipeline/`

### Required Outputs

- `run_manifest.json` under each report directory
- standardized route and step statuses
- run-level warnings and errors

### Tasks

1. Define the manifest file path.
   - Recommended path:
   - `output/reports/<report_id>/run_manifest.json`

2. Define the manifest schema in code.
   - Include:
   - run identity
   - config snapshot
   - artifact paths
   - route statuses
   - warnings
   - errors
   - next actions
   - human review queue

3. Standardize route and step status values.
   - Required statuses:
   - `pending`
   - `running`
   - `completed`
   - `failed`
   - `skipped`

4. Write manifest initialization logic.
   - Initial status should be `pending` before route execution.

5. Write manifest update logic after each route.
   - Update route status
   - update artifact paths
   - update summary fields
   - append warnings and errors

6. Preserve failed state for resume.
   - Failed diagnostics must remain in the manifest for later inspection.

### Suggested File Changes

`pipeline/agent_harness.py`

- add manifest initialization
- add manifest read/write helpers
- add route summary writes
- add route status transitions

`agents/supervisor_agent.py`

- stop returning only ad hoc inspection flags
- return structured inspection output that maps cleanly into manifest fields

### Definition of Done

Phase 1 is done when:

1. each report run produces `run_manifest.json`
2. Route A, Route B, and Merge all have explicit status in the manifest
3. warnings and errors are visible in one place
4. reruns can inspect the manifest before acting

## Phase 2: Supervisor and Harness Responsibility Upgrade

### Goal

Upgrade `SupervisorAgent` from a directory inspection helper into a route orchestration decision component, while keeping extraction behavior unchanged.

### Current State

Current reality in the repository:

- `agents/supervisor_agent.py`
  - mainly checks file existence and row counts
- `pipeline/agent_harness.py`
  - runs schema rerun, route B planning, and merge decisions

This is a workable baseline, but responsibility boundaries are still loose.

### Target Responsibility Split

`SupervisorAgent` should own:

1. report inspection
2. artifact validation summary
3. route readiness decisions
4. warning code generation
5. next-action generation
6. human review trigger generation

`ESGAgentHarness` should own:

1. run lifecycle
2. manifest writes
3. route execution calls
4. route result collection
5. final run summary

### Tasks for `agents/supervisor_agent.py`

1. Add structured inspection categories.
   - route health
   - artifact health
   - review triggers

2. Replace plain booleans with stable decision fields.
   - example:
   - `route_a_status`
   - `route_b_status`
   - `merge_status`
   - `review_needed`

3. Add warning code normalization.
   - example:
   - `route_a_cache_missing`
   - `standard_row_count_invalid`
   - `merged_row_count_invalid`
   - `route_b_unavailable`

4. Add next-action prioritization.
   - actions should be ordered, not only collected

5. Add review trigger output.
   - if low confidence or abnormal row counts are found later, the supervisor should emit review items or review reasons

### Tasks for `pipeline/agent_harness.py`

1. Read manifest before acting.
2. Use supervisor output as route decision input.
3. Record `started_at` and `finished_at` at route level.
4. Record route summaries into the manifest.
5. Avoid re-running valid routes unless explicitly requested.
6. Keep current stable rerun semantics for schema matching.

### Suggested Milestone

The first harness milestone should support:

1. inspect report
2. initialize manifest
3. decide route actions
4. run only needed routes
5. write final manifest summary

### Definition of Done

Phase 2 is done when:

1. `SupervisorAgent` returns structured orchestration decisions
2. `ESGAgentHarness` becomes the single execution entry for one report
3. valid outputs are skipped predictably
4. failed outputs are preserved for rerun diagnosis

## Phase 3: Evaluation Dataset and Per-Report Evaluation Outputs

### Goal

Add task-level evaluation artifacts so the project can measure extraction quality rather than only file-level completeness.

### Primary Ownership

- `docs/`
- `scripts/`
- optional new evaluation helpers under `utils/` or `pipeline/`

### Directory Recommendation

Create:

```text
docs/eval/
```

Recommended contents:

- `docs/eval/golden_set.csv`
- `docs/eval/per_report_eval.csv`
- `docs/eval/README.md`

### Tasks

1. Create a minimal golden set.
   - target approximately 20 representative reports
   - include mixed OCR difficulty and text-layer quality

2. Define evaluation fields.
   - `route_a_coverage`
   - `route_b_match_rate`
   - `merged_coverage`
   - `field_precision`
   - `unknown_metric_quality`

3. Define per-report evaluation format.
   - include run id
   - include report id
   - include review-needed flag
   - include grader notes

4. Add one script or workflow to aggregate current outputs into per-report evaluation rows.
   - this can initially be semi-manual

5. Keep evaluation separate from production outputs.
   - do not overload `output/` with long-term evaluation source-of-truth data

### Suggested File Changes

`docs/eval/golden_set.csv`

- new curated evaluation input

`docs/eval/per_report_eval.csv`

- new evaluation output template

`docs/eval/README.md`

- definitions of each metric
- instructions for manual review and scoring

`scripts/`

- optional new script for evaluation aggregation

### Definition of Done

Phase 3 is done when:

1. the repo has a stable small evaluation set
2. each important run can be mapped to per-report quality signals
3. field-level quality discussion is no longer based only on row counts

## Phase 4: Human Review Queue and Review Triggers

### Goal

Add explicit human review support for low-confidence or abnormal cases.

### Primary Ownership

- `agents/supervisor_agent.py`
- `pipeline/agent_harness.py`
- optional review helper module

### Recommended Output

```text
output/reports/<report_id>/human_review_queue.json
```

### Review Trigger Categories

The first review queue version should support at least:

1. low confidence Route B fields
2. Route A and Route B conflicts
3. unusually high unknown metric count
4. invalid standard result row count
5. invalid merged result row count
6. no usable text layer
7. OCR page-level failures above threshold

### Tasks

1. Define review item schema.
2. Add review item generation rules to the supervisor or harness.
3. Save review queue output as a stable artifact.
4. Add `review_needed` to manifest summary.
5. Make review queue generation non-destructive.

### Suggested Responsibility Split

`SupervisorAgent`

- detect review triggers
- propose review reasons

`ESGAgentHarness`

- write review queue artifact
- link review items into manifest

### Definition of Done

Phase 4 is done when:

1. abnormal cases no longer disappear into logs or CSVs
2. review-needed reports can be listed deterministically
3. a human can inspect one standard queue artifact per report

## Phase 5: Optional Observability Improvements

### Goal

Add better run-level diagnostics after the protocol and evaluation layers are in place.

### Recommended Scope

1. structured log messages
2. per-route timestamps
3. warning and error code dictionary
4. optional tracing integration later

### Important Constraint

Observability is useful, but it should come after manifest, contract, and evaluation. Otherwise the team will instrument unstable boundaries.

## Module-Level Checklist

### `agents/supervisor_agent.py`

Recommended next responsibilities:

1. produce structured route inspection
2. produce standardized warning codes
3. produce ordered next actions
4. produce review triggers
5. map artifact state into manifest-ready fields

Should not own:

1. OCR logic
2. schema matching logic
3. merge logic

### `pipeline/agent_harness.py`

Recommended next responsibilities:

1. initialize and update run manifest
2. orchestrate route execution
3. record route timing and summary
4. preserve rerun safety
5. collect final run result

Should not own:

1. route-specific extraction rules
2. field-level schema semantics

### `pipeline/appendix_pipeline.py`

Recommended status in v1.2:

1. keep stable
2. expose clearer route summary output if needed
3. avoid deep rewrite until manifest layer is proven

### `pipeline/text_pipeline.py`

Recommended status in v1.2:

1. keep stable
2. expose consistent route summary fields
3. standardize no-text-layer completion behavior

### `pipeline/merge_pipeline.py`

Recommended status in v1.2:

1. keep stable merge semantics
2. expose summary fields already useful to the manifest
3. avoid adding business-rule complexity before evaluation baselines exist

### `docs/eval/`

Recommended contents:

1. golden set input
2. per-report evaluation output
3. metric definitions
4. reviewer instructions

## Suggested Milestones by Week

### Week 1

1. create `run_manifest.json`
2. standardize route statuses
3. wire manifest initialization into harness

### Week 2

1. upgrade supervisor decision output
2. add route summaries to manifest
3. support clean skip and rerun behavior

### Week 3

1. add `docs/eval/`
2. prepare golden set
3. define manual review scoring process

### Week 4

1. add review queue generation
2. expose review-needed reports
3. refine warning and error codes

## Risks to Avoid

The main v1.2 implementation risks are:

1. over-rewriting stable extraction code before protocols are defined
2. mixing evaluation data with production output artifacts
3. making `SupervisorAgent` too responsible for extraction details
4. adding new model logic before field-level baselines exist
5. treating file existence as a full proxy for correctness

## Recommended First Commit Scope

When implementation starts, the safest first code change scope is:

1. add manifest helper functions
2. add manifest initialization and save path
3. wire current harness summary into manifest
4. keep Route A, Route B, and Merge internals unchanged

This first scope is intentionally narrow and should be easy to review.

## Summary

The v1.2 implementation should begin by making the system more explicit, not more autonomous.

The practical build order is:

1. define the run record
2. upgrade supervisor and harness contracts
3. add evaluation artifacts
4. add human review queue
5. improve observability later

If the team keeps this order, the project can become a more production-ready agent workflow system without risking the stability of the current extraction baseline.
