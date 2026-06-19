# 当前架构

本文档是当前 ESG 抽取系统架构的唯一事实来源。
规范化 Schema 为 `core_esg_v4.1_60`，共 60 个字段。

## 系统架构图

```mermaid
flowchart TB
    PDF["ESG 报告 PDF"] --> UP["统一抽取流水线 UnifiedESGPipeline<br/>fast / balanced / deep"]
    UP --> INGEST["文档解析层"]
    INGEST --> MINERU["MinerU 自动调用适配器"]
    INGEST --> FALLBACK["PyMuPDF 回退<br/>显式记录回退原因"]
    MINERU --> DOC["统一 DocModel<br/>document.md / 页面 / 文本块 / HTML 表格 / bbox"]
    FALLBACK --> DOC

    DOC --> DETECT["确定性绩效表格检测器"]
    DETECT --> RA["路线 A：定量表格抽取"]
    RA --> RAW["raw_table_metrics.json<br/>保留全部候选 KPI 行"]
    RAW --> MATCH["确定性 Schema Match 与验证"]

    DOC --> RB["路线 B：共享 Hybrid RAG"]
    RB --> QUAL["定性字段抽取"]
    RB --> QUANT["定量字段验证与补充"]

    DOC --> SJ["语义指标裁判 SemanticMetricJudge<br/>候选 KPI / unknown metrics / Route B 证据"]
    SJ --> SJR["semantic_judge_results.*<br/>高置信候选字段映射"]

    MATCH --> ARB["证据质量评估与表格仲裁"]
    QUANT --> ARB
    ARB --> FOLLOW["定向视觉补跑<br/>balanced / deep 模式"]
    FOLLOW --> FUSION["保守融合与合并"]
    QUAL --> FUSION
    MATCH --> FUSION
    SJR --> FUSION

    FUSION --> RESULT["合并后的 60 字段 ESG 结果"]
    RESULT --> CITATION["字段引用与证据记录"]
    RESULT --> RATING["模拟评级"]
    CITATION --> FIELDDB["字段结果入库<br/>extraction_results"]
    FIELDDB --> REVIEW["人工复核队列"]
    RATING --> REVIEW

    UP --> MANIFEST["run_manifest.json<br/>生命周期、产物与诊断"]
    UP --> COST["run_cost_summary.json<br/>模型调用与成本"]
    REVIEW --> API["FastAPI + SQLite<br/>Upload、Task Overview、Dashboard、Trace 与审核"]
    API --> FE["React 前端<br/>上传、进度、字段结果与复核入口"]

    XLSX["人工填报定量 Golden Set Excel"] --> GOLDEN["Golden Set 构建脚本<br/>quantitative_golden_set.* / quality report"]
```

## 运行时序图

```mermaid
sequenceDiagram
    participant CLI as run_full_extraction
    participant U as UnifiedESGPipeline
    participant I as 文档解析
    participant A as 路线 A
    participant B as 路线 B
    participant S as 语义指标裁判
    participant F as 融合层
    participant D as SQLite/API
    participant O as 运行产物

    CLI->>U: run(pdf, mode)
    U->>O: 初始化 run_manifest.json
    U->>I: 解析或复用文档产物
    I-->>U: DocModel 与解析器诊断
    U->>A: 检测并抽取绩效表格
    A-->>O: 原始指标与标准化结果
    U->>B: 构建共享语料并抽取字段
    B-->>O: 定性与定量结果
    U->>S: 汇总候选指标并执行语义裁判
    S-->>O: semantic_judge_candidates / results / summary
    U->>F: 仲裁证据并合并路线与语义裁判补充
    F-->>O: 合并结果与人工复核队列
    U->>D: 持久化任务进度与字段结果
    U->>O: 完成 Manifest 与成本摘要
```

## 模块职责

| 模块 | 当前实现 | 职责 |
|---|---|---|
| 顶层编排 | `pipeline/unified_pipeline.py` | 管理标准运行生命周期、模式、Manifest、补跑与合并 |
| 文档解析 | `utils/pdf_ingest.py`、MinerU 适配器 | 选择解析器并生成可复用文档产物 |
| 路线 A | `pipeline/appendix_pipeline.py`、步骤级 Agent | 抽取定量表格行并将通过验证的行映射到 Schema |
| 路线 B | `pipeline/text_pipeline.py`、`pipeline/quant_text_pipeline.py` | 使用共享检索语料抽取定性字段并验证定量字段 |
| 语义指标裁判 | `utils/semantic_metric_judge.py` | 从表格候选、未知指标和 Route B 证据中生成候选项，调用轻量 LLM 裁判映射到 Schema，并复用 B2 定量校验 |
| 仲裁与证据 | 表格仲裁和证据工具 | 评估来源质量、保留溯源并识别冲突 |
| 合并 | `pipeline/merge_pipeline.py` | 执行保守来源选择，接收语义裁判补充缺失字段，并保留不确定结果 |
| 兼容 Harness | `pipeline/agent_harness.py` | 支持旧产物检查和可恢复包装流程 |
| 追踪、入库与复核 | `pipeline/rating_data_harness.py`、`backend/` | 保存任务、Trace、评级、字段抽取结果、进度状态和人工审核动作 |
| 前端工作台 | `frontend/src/App.tsx` | 上传报告、启动分析、展示任务阶段、字段结果摘要和复核入口 |
| 评测数据 | `scripts/build_quantitative_golden_set.py`、`docs/eval/` | 汇总人工填报的定量 Golden Set Excel，生成 CSV/JSON 和质量报告 |

## 标准入口

```powershell
python -m scripts.run_full_extraction <pdf> --mode fast
python -m scripts.run_full_extraction <pdf> --mode balanced
python -m scripts.run_full_extraction <pdf> --mode deep
```

- `fast`：优先复用结构化产物并控制模型调用。
- `balanced`：启用有限的定向视觉补跑。
- `deep`：允许更高的补跑与仲裁预算。

## 主要产物

| 阶段 | 主要产物 |
|---|---|
| 文档解析 | `document.md`, `document_model.json`、页面、文本块和表格产物 |
| 路线 A | `all_table_rows.json`, `raw_table_metrics.json`, `standard_esg_results.*`, `unknown_metrics.*` |
| 路线 B | `route_b_combined_chunks.json`, `route_b_text_results.*`, `route_b_quant_results.*`, `rag_index/*` |
| 语义指标裁判 | `semantic_judge_candidates.json`, `semantic_judge_results.*`, `semantic_judge_summary.json` |
| 证据与仲裁 | `evidence_records.json`, `evidence_summary.json`, `table_quality_assessments.json`, `visual_followup_queue.json` |
| 融合 | `merged_esg_results.*`, `merge_summary.json` |
| 运行控制 | `run_manifest.json`, `unified_pipeline_summary.json`, `run_cost_summary.json`, `run_call_events.json` |
| 复核与评级 | `field_citations.*`, `simulated_rating.*`, `rating_review_queue.json`, `rating_review_history.json` |
| 后端数据库 | SQLite `reports`, `tasks`, `task_traces`, `rating_runs`, `review_items`, `extraction_results` |
| 定量 Golden Set | `quantitative_golden_set.csv`, `quantitative_golden_set.json`, `quantitative_golden_set_quality.*` |

## 并行约束

路线 A 和路线 B 在文档解析后逻辑上相互独立，但当前默认不进行物理并行。
两条路线仍会向同一报告目录写入共享产物。要安全并行，需要先引入路线级临时目录，
再通过显式发布步骤合并产物。

## 历史文档

`docs/architecture.md` 描述旧版 v1.1 基线，仅保留作为历史参考。
新的实现与运维决策应以本文档和
`docs/project_memory/ARCHITECTURE_AND_OPERATIONS.md` 为准。
