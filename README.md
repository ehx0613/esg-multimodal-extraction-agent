# ESG Multimodal Extraction Agent

新架构路线 A：

```text
PDF
↓
AppendixSnifferAgent        # 嗅探附录绩效表页
↓
PageRenderAgent             # PDF 页转图片
↓
VLMTableOCRAgent            # VLM 只完整抄表，不做指标判断
↓
SchemaMatchAgent            # 按 Core ESG Schema 匹配标准指标
↓
UnknownMetricCollector      # 未匹配指标进入 unknown_metrics
↓
CSV / JSON Export
```

核心原则：

- `all_table_rows.json` 保存所有表格行；
- `standard_esg_results.csv` 保存固定 Core ESG 指标，用于横向比较；
- `unknown_metrics.csv` 保存公司特色指标，不强行塞入核心指标体系。

运行：

```bash
pip install -r requirements.txt
python -m scripts.run_single
python -m scripts.run_batch
```
