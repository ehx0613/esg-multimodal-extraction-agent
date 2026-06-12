# ESG Multimodal Extraction Agent - v1.0 Stable

> Historical results below may use the retired 68-field denominator. The canonical runtime schema is `core_esg_v4.1_60` with 60 fields.

## Version

v1.0-stable

## Date

2026-05

## Current Capability

This version implements a dual-route ESG information extraction system.

### Route A: Appendix Table Extraction

- Uses VLM to extract ESG performance tables from PDF appendix pages.
- Supports scanned/image-based PDFs through page rendering and split-page rendering.
- Outputs structured all_table_rows, standard_esg_results, and unknown_metrics.

### Route B: Text-based Qualitative Extraction

- Uses text retrieval and LLM extraction to identify qualitative ESG mechanisms from report正文.
- Extracts selected Core ESG qualitative fields:
  - board_esg_oversight
  - esg_committee
  - anti_corruption_policy
  - whistleblowing_mechanism
  - supplier_esg_assessment

### Merge

- Merges Route A and Route B outputs into merged_esg_results.
- Keeps source_route, evidence, confidence, and extraction status.

## Batch Test Result

Tested on 12 ESG / CSR reports.

- Route A success: 12 / 12
- Route B success: 12 / 12
- Merge success: 12 / 12
- Route A average extracted fields: about 25.33 / 68
- Merged average extracted fields: about 29.25 / 68
- Best case: Wuliangye, 43 / 68
- Average merged coverage rate: about 43%

## Notes

- Route A is responsible for quantitative appendix table indicators.
- Route B is responsible for qualitative text-based ESG mechanism indicators.
- unknown_metrics are retained for later schema evolution.
