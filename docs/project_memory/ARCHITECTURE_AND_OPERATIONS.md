# ESG Agent 架构与运维总览

## 一句话架构

PDF/MinerU 解析 -> 指标执行计划 -> 表格视觉抽取与质量仲裁 -> 共享文本/结构化 RAG -> 定性与定量抽取 -> 证据融合 -> 保守合并 -> 引用、模拟评级、人审与后端追踪。

## 当前推荐主流程

入口：`python -m scripts.run_full_extraction <pdf> --mode fast|balanced|deep`

| 步骤 | 主要输入 | 核心逻辑 | 主要输出 |
|---|---|---|---|
| PDF ingest | PDF、MinerU 缓存 | 选择解析器，构建页面、块、特征和 chunks | `ingest/*`, `document_model.json` |
| Metric planning | `ALL_SCHEMA` | 为每个指标规划模态与验证策略 | `metric_execution_plans.json` |
| Route A / MinerU | 页面特征、表格块、页面图 | 选候选表、VLM OCR、Schema Match、Validation | `all_table_rows.json`, `standard_esg_results.*`, `unknown_metrics.*` |
| Table arbitration | 结构化表格 chunks | 评估表格质量、跨源一致性、必要时 VLM 仲裁 | `table_quality_assessments.json`, `table_arbitration_*` |
| Unified Route B | 文本 chunks + 结构化 chunks | Hybrid RAG；抽取定性字段；对缺失/低置信/冲突定量字段做融合 | `route_b_text_results.*`, `route_b_quant_results.*`, `rag_index/*` |
| Evidence store | 文本、表格、视觉代理 | 统一证据记录和物理来源区域 | `evidence_records.json`, `evidence_summary.json` |
| Visual follow-up | 缺失/争议指标 | balanced/deep 模式下定向补跑少量页面 | `visual_followup_queue.json` |
| Merge | Route A + Route B 定性/定量 | Route A 优先，Route B 只在验证和置信阈值通过时补充/覆盖 | `merged_esg_results.*`, `merge_summary.json` |
| Rating workflow | merged 结果、RAG chunks | 字段引用、模拟评分、待人审队列 | `field_citations.*`, `simulated_rating.*`, `rating_review_queue.json` |
| Tracking/API | report dir、运行摘要 | SQLite 保存任务、Agent trace、review、rating run；FastAPI 展示 | 数据库记录、API/dashboard |

## Agent 与系统逻辑链路

- Route A Agent 链：`AppendixSnifferAgent -> PageRenderAgent -> VLMTableOCRAgent -> SchemaMatchAgent -> ValidationAgent`
- Supervisor/Harness 链：检查已有产物 -> 决定 schema rerun/Route B/merge -> 写 `run_manifest.json` 与人审队列
- Rating Data Harness：调用 Agent Harness -> 写 reports/tasks/agent_runs/review_items -> 提供 trace
- 后端：FastAPI 调用工作流与评分逻辑，SQLite 保存可追踪状态，前端用于结果和人审展示。

## 评价指标

- 抽取覆盖：`route_a_extracted_fields / 全字段数`、`route_b_matched_fields / Route B 目标数`
- 合并覆盖：`merged_extracted_fields / 全字段数`
- 行业有效覆盖：`applicable_extracted_fields / applicable_fields`
- 精度：人工抽样正确字段数 / 抽样字段数
- Unknown quality：正确排除的未知指标 / 抽样未知指标
- 检索：Hit Rate@K、MRR@K、平均延迟
- 证据：自动引用字段数、待人审字段数、证据完整性
- 成本：模型调用数、prompt/completion/total tokens、分阶段延迟
- 稳定性：68 行结果守卫、测试通过率、失败/警告数量

## 运行与日志规范

每份报告目录已经保存细粒度运行日志：

- 总编排：`unified_pipeline_summary.json`
- 模型成本：`run_cost_summary.json`, `run_call_events.json`
- 路由摘要：`validation_summary.json`, `route_b_summary.json`, `route_b_quant_summary.json`
- 合并摘要：`merge_summary.json`
- Agent 运行：`run_manifest.json`, `pipeline_state.json`
- 评级闭环：`full_rating_workflow_summary.json`, `rating_review_history.json`

每次运行后执行：

```powershell
python -m scripts.update_project_memory
```

这样会生成统一结果文档和日志文档，后续优先读取 `docs/project_memory/`，无需再次全量扫描项目。

## GitHub 联动

1. 源码、测试、`docs/project_memory/` 提交到 GitHub；大体积 PDF、图片、报告中间产物继续由 `.gitignore` 排除。
2. 功能分支使用 `codex/<主题>`；提交前刷新 project memory 并运行相关测试。
3. PR 描述至少包含：目的、逻辑链路变化、输入输出变化、评价指标变化、测试结果、最新结果文档链接。
4. CI 推荐执行：`python -m pytest -q`、`python -m scripts.update_project_memory`，并检查刷新后是否出现未提交差异。
5. 运行产物若需共享，使用 GitHub Actions artifact 或对象存储，不直接提交大体积 `output/`。

## 代码职责索引

完整机器可读职责列表位于 `latest_snapshot.json` 的 `source_inventory`。主要目录：

- `agents/`：步骤级 Agent 与 Supervisor。
- `pipeline/`：统一流水线、子路线、合并和追踪编排。
- `utils/`：解析、检索、匹配、证据、评分、结果守卫与模型调用。
- `config/`：Schema、Prompt、模型及预算配置。
- `scripts/`：命令行运行、评估、修复和分析入口。
- `backend/`：FastAPI 与 SQLite。
- `frontend/`：结果展示和人审 UI。
