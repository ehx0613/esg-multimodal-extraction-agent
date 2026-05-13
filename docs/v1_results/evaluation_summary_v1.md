# v1.1 Token-safe Evaluation Summary

## Version

v1.1-token-safe

## Dataset

- Total reports: 12
- Route A success: 12 / 12
- Appendix found: 12 / 12
- Reports with raw rows = 0: 0

## Route A: Appendix Table Extraction

- Average raw table rows per report: 240.42
- Median raw table rows per report: 209.0
- Average extracted Core fields: 25.33 / 68
- Median extracted Core fields: 26.5 / 68

## Route B: Text-based Qualitative Extraction

- Route B available reports: 11 / 12
- Average fields filled by Route B: 3.92
- Median fields filled by Route B: 4.5

## Merged Results

- Average merged extracted fields: 27.25 / 68
- Median merged extracted fields: 28.0 / 68
- Average merged coverage rate: 40.07%

## Best Report

- Report: 001_000858_五_粮_液_2024_五_粮_液_2024年度环境、社会及公司治理（ESG）报告
- Extracted fields: 41 / 68
- Coverage rate: 60.29%

## Lowest Report

- Report: 009_002811_郑中设计_2024_郑中设计_2024年度环境、社会及公司治理（ESG）报告
- Extracted fields: 17 / 68
- Coverage rate: 25.00%

## Version Notes

Compared with the previous v1.0 evaluation, this v1.1 version uses a more conservative and token-safe schema rerun setting.

Main changes:

1. LLM fallback in Schema Match is disabled during batch rerun.
2. Route A rerun now relies on:
   - heuristic rules
   - alias matching
   - schema validator
3. Several stricter boundary rules were added to reduce false positives:
   -专项培训不再进入通用员工培训覆盖率
   -减排量 / 削减量不再进入污染物排放量
   -回收利用量不再进入废弃物总量
   -范围三子项不再直接进入范围三总排放量
   -碳排放因子 / 核算方法表不再参与 Core 匹配
4. CSV writing was fixed to avoid field mismatch errors such as `column_label`.
5. The rerun process no longer produces abnormal merged results such as `0/1` or `0/7`.

## Interpretation

The v1.1 system successfully completes a dual-route ESG extraction workflow:

1. Route A extracts quantitative ESG indicators from appendix performance tables.
2. Route B extracts qualitative ESG mechanism indicators from report text.
3. Merge Pipeline combines both routes into a unified Core ESG result.

This version prioritizes extraction precision, token safety, and batch stability over aggressive LLM-assisted matching. The average merged coverage is slightly lower than the earlier LLM-assisted run, but the result is more conservative and more suitable as a stable baseline for later 30-report and 100-report experiments.

## Recommended Use

Use this version as the current stable baseline:

- For schema debugging:
  - Keep `LLM_MATCHER_ENABLED=false`
  - Run `rerun_schema_match_batch`
  - Run `run_merge_batch`
  - Run `analyze_v1_results`

- For model-based tasks:
  - Use LLM only for Route B text extraction
  - Use LLM only for unknown metric analysis
  - Avoid using LLM fallback in large-scale schema reruns unless necessary
