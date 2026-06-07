# v1.0 Evaluation Summary

## Dataset

- Total reports: 10
- Route A success: 10 / 10
- Appendix found: 10 / 10
- Reports with raw rows = 0: 0

## Route A: Appendix Table Extraction

- Average raw table rows per report: 124.6
- Median raw table rows per report: 98.0
- Average extracted Core fields: 11
- Median extracted Core fields: 11.5

## Route B: Text-based Qualitative Extraction

- Route B available reports: 10 / 10
- Average fields filled by Route B: 15.7
- Median fields filled by Route B: 17.0

## Merged Results

- Average merged extracted fields: 26.2
- Median merged extracted fields: 26.5
- Average merged coverage rate: 0.5038

## Best Report

- Report: 006_600587_新华医疗_2024_新华医疗_新华医疗2024年度ESG报告
- Extracted fields: 37
- Coverage rate: 0.7115

## Lowest Report

- Report: 010_600928_西安银行_2024_西安银行_西安银行股份有限公司2024年社会责任(ESG)报告
- Extracted fields: 13
- Coverage rate: 0.25

## Interpretation

The v1.0 system successfully completes a dual-route ESG extraction workflow:

1. Route A extracts quantitative ESG indicators from appendix performance tables.
2. Route B extracts qualitative ESG mechanism indicators from report text.
3. Merge Pipeline combines both routes into a unified Core ESG result.

The results show that the system can process multiple ESG/CSR reports in batch mode and produce structured Core ESG indicators with evidence, confidence scores, and source-route tracking.
