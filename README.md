# ESG Multimodal Extraction Agent

面向上市公司 ESG 报告的多阶段抽取、证据溯源、模拟评级与人审协同系统。

本项目从 ESG 报告中抽取结构化指标，将项目字段映射到华证公开 ESG 框架，生成字段级证据、模拟评级结果和待人工复核队列。当前定位不是复刻华证内部评级模型，而是构建一个面向 ESG 评级数据生产的 Agent 工程闭环。

定量表格映射采用“规则优先、语义判别补召回”的策略。规则和别名无法确认时，系统先从 42 个定量字段中召回少量候选，再使用可配置的小模型进行语义判断。小模型仅能放宽 `required_any` 同义表达缺失；单位冲突、禁止语境、非数值和总量/强度冲突仍由硬规则拒绝。

默认语义判别使用 `qwen3.6-flash`。当 Flash 返回中间置信度结果时，系统会升级到 `qwen3.6-plus` 二次判断；模型调用使用 JSON Mode，降低结构化结果解析失败率。

## 项目目标

传统 ESG 报告处理通常依赖人工阅读、表格整理和指标比对，效率低且难以追踪证据。本项目希望解决三个问题：

1. 自动从 ESG 报告中抽取定量和定性指标。
2. 将抽取结果挂到可解释的 ESG 评级框架下。
3. 对不确定字段生成复核队列，支持 Human-in-the-loop。

一句话概括：

```text
ESG 报告 -> 字段抽取 -> 华证公开框架映射 -> 检索评测 -> 字段级证据 -> 模拟评分 -> 人审队列 -> 后端 Trace
```

## 当前能力

- 表格抽取：从附录和 ESG 数据表中抽取定量指标。
- 文本 RAG：从正文 chunk 中抽取定性指标。
- 华证框架映射：将 60 个项目字段映射到公开 3 支柱、16 主题、44 关键指标框架。
- Hybrid Retrieval：支持 BM25、查询改写、RRF 接口和证据完整度 rerank。
- 检索评测：使用 Hit Rate、MRR 和延迟评估检索质量。
- 字段级证据溯源：为每个字段生成页码、chunk、证据文本和复核状态。
- 模拟评级：生成项目侧 ESG 总分、E/S/G 分、主题分和评级。
- 人审队列：把缺失或证据不稳的字段输出为待审核项。
- 后端工程：FastAPI + SQLite，支持任务、Trace、评测记录和 review item。
- 自动测试：当前 `unittest` 覆盖核心模块。

## 整体架构

```text
Input Report Directory
  |
  |-- Route A: appendix/table extraction
  |     outputs: standard_esg_results.json/csv
  |
  |-- Route B: text RAG extraction
  |     outputs: route_b_chunks.json, route_b_text_results.json/csv
  |
  |-- Merge
  |     outputs: merged_esg_results.json/csv
  |
  |-- Rating Data Harness
  |     records: reports, tasks, agent_runs, review_items
  |
  |-- Field Citations
  |     outputs: field_citations.json/csv
  |
  |-- Simulated Rating
  |     outputs: simulated_rating.json, simulated_rating_summary.csv
  |
  |-- Human Review Queue
        outputs: rating_review_queue.json
```

## 目录结构

```text
agents/        Step-level agents and supervisor logic
backend/       FastAPI app and SQLite persistence layer
config/        Settings, prompts, ESG schema, Huazheng public mapping
docs/          Architecture notes, evaluation files, historical docs
output/        Generated report artifacts
pipeline/      Route pipelines and rating-data harness
scripts/       CLI entrypoints for workflow, evaluation, citations, rating
tests/         unittest test suite
utils/         Retrieval, citation, scoring, PDF, schema matching helpers
```

## 演示指南

面试或项目展示可以直接参考：

- `docs/demo_guide.md`

## 关键文件

### 指标体系

- `config/schema/huazheng_public_mapping.py`
  - 华证公开 ESG 框架映射。
  - 3 支柱、16 主题、44 关键指标。
  - 将项目 60 个字段挂载到框架层。

### 后端和任务追踪

- `backend/app.py`
  - FastAPI 服务入口。
  - 提供报告、任务、Trace、运行任务接口。

- `backend/database.py`
  - SQLite 表结构和数据访问函数。
  - 包含 `reports`、`tasks`、`agent_runs`、`review_items`、`retrieval_eval_records` 等表。

- `pipeline/rating_data_harness.py`
  - 包装原有抽取流程。
  - 创建任务记录、Agent 运行记录和 review items。

### 检索与评测

- `utils/bm25_retriever.py`
  - BM25 关键词检索。

- `utils/query_rewriter.py`
  - 字段查询改写。

- `utils/hybrid_retriever.py`
  - 多 query BM25 聚合、RRF 接口、证据 rerank。

- `utils/retrieval_eval.py`
  - Hit Rate / MRR 评测。

- `scripts/evaluate_retrieval.py`
  - 检索评测 CLI，可选写入 SQLite。

### 证据和评分

- `utils/field_citations.py`
  - 字段级证据附着。
  - 输出页码、chunk、证据文本、review status。

- `scripts/attach_field_citations.py`
  - 生成 `field_citations.json/csv`。

- `utils/simulated_rating.py`
  - 项目侧模拟评级。
  - 输出总分、E/S/G 分、主题分、字段分、人审队列。

- `scripts/generate_simulated_rating.py`
  - 生成 `simulated_rating.json` 和 `rating_review_queue.json`。

- `scripts/run_full_rating_workflow.py`
  - 当前推荐的一键工作流入口。

## 环境

推荐使用项目当前 Conda 环境：

```powershell
C:\Users\18130\.conda\envs\pachong\python.exe
```

进入项目目录：

```powershell
cd "C:\Users\18130\PycharmProjects\爬虫\esg-multimodal-extraction-agent"
```

## 一键运行

如果报告目录已经存在 `merged_esg_results.json` 和 `route_b_chunks.json`，推荐先用轻量模式：

```powershell
& "C:\Users\18130\.conda\envs\pachong\python.exe" -m scripts.run_full_rating_workflow "output\reports\006_600587_新华医疗_2024_新华医疗：新华医疗2024年度ESG报告" --industry manufacturing --skip-harness
```

这会生成：

- `field_citations.json`
- `field_citations.csv`
- `simulated_rating.json`
- `simulated_rating_summary.csv`
- `rating_review_queue.json`
- `full_rating_workflow_summary.json`

如果希望连同后端 task/trace 一起重新跑 tracked harness，可以去掉 `--skip-harness`：

```powershell
& "C:\Users\18130\.conda\envs\pachong\python.exe" -m scripts.run_full_rating_workflow "output\reports\006_600587_新华医疗_2024_新华医疗：新华医疗2024年度ESG报告" --industry manufacturing
```

## 批量运行

对 `output/reports` 下所有包含 `merged_esg_results.json` 的报告目录批量生成字段证据、模拟评分和人审队列：

```powershell
& "C:\Users\18130\.conda\envs\pachong\python.exe" -m scripts.run_full_rating_workflow_batch --reports-root "output\reports" --industry manufacturing --skip-harness
```

先试跑 1 份报告：

```powershell
& "C:\Users\18130\.conda\envs\pachong\python.exe" -m scripts.run_full_rating_workflow_batch --reports-root "output\reports" --industry manufacturing --skip-harness --limit 1
```

批量输出：

- `output/full_rating_workflow_batch_summary.csv`
- `output/full_rating_workflow_batch_summary.json`

批量汇总字段包括：

- 报告名
- 是否成功
- 字段数
- 自动证据数
- 待人审数
- 模拟总分和等级
- E/S/G 分数和等级
- rating run id
- 错误信息

## 分步运行

### 1. 跑 tracked harness

```powershell
& "C:\Users\18130\.conda\envs\pachong\python.exe" -m scripts.run_rating_data_harness_single "output\reports\006_600587_新华医疗_2024_新华医疗：新华医疗2024年度ESG报告" --industry manufacturing
```

### 2. 生成字段级证据

```powershell
& "C:\Users\18130\.conda\envs\pachong\python.exe" -m scripts.attach_field_citations "output\reports\006_600587_新华医疗_2024_新华医疗：新华医疗2024年度ESG报告" --industry manufacturing --top-k 5
```

### 3. 生成模拟评级

```powershell
& "C:\Users\18130\.conda\envs\pachong\python.exe" -m scripts.generate_simulated_rating "output\reports\006_600587_新华医疗_2024_新华医疗：新华医疗2024年度ESG报告" --industry manufacturing
```

### 4. 跑检索评测

```powershell
& "C:\Users\18130\.conda\envs\pachong\python.exe" -m scripts.evaluate_retrieval --eval-set "docs\eval\retrieval_eval_set.csv" --chunks "output\reports\006_600587_新华医疗_2024_新华医疗：新华医疗2024年度ESG报告\route_b_chunks.json" --top-k 5 --industry manufacturing --save --eval-set-name "新华医疗_15_fields_v1"
```

## FastAPI

启动服务：

```powershell
& "C:\Users\18130\.conda\envs\pachong\python.exe" -m uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

主要接口：

- `GET /health`
- `POST /reports`
- `POST /tasks`
- `GET /tasks`
- `GET /tasks/{task_id}`
- `GET /tasks/{task_id}/trace`
- `GET /tasks/{task_id}/review-items`
- `POST /runs/report-dir`
- `POST /rating/review-queue`
- `POST /rating/review-items/apply`
- `POST /rating/recalculate`
- `GET /rating/runs`
- `GET /rating/runs/{rating_run_id}`

`POST /runs/report-dir` 支持可选生成 citations 和 simulated rating：

```json
{
  "report_dir": "output/reports/006_600587_新华医疗_2024_新华医疗：新华医疗2024年度ESG报告",
  "industry": "manufacturing",
  "retrieval_profile": "bm25_query_agg_evidence_rerank_v1",
  "generate_citations": true,
  "generate_rating": true
}
```

### 人审闭环接口

查看某个报告目录的评级人审队列：

```json
POST /rating/review-queue

{
  "report_dir": "output/reports/006_600587_新华医疗_2024_新华医疗：新华医疗2024年度ESG报告"
}
```

提交审核动作并自动重算评分：

```json
POST /rating/review-items/apply

{
  "report_dir": "output/reports/006_600587_新华医疗_2024_新华医疗：新华医疗2024年度ESG报告",
  "field_key": "climate_risk_management",
  "action": "correct",
  "industry": "manufacturing",
  "reviewer": "analyst_001",
  "notes": "人工确认候选页可支持该字段",
  "correction": {
    "value": true,
    "confidence": "0.9",
    "evidence": "公司识别实体及转型气候风险。"
  }
}
```

支持的 `action`：

- `approve`：证据通过，字段进入 `reviewed_approved`。
- `reject`：候选证据不支持字段，字段进入 `reviewed_rejected`。
- `correct`：人工补录或修正字段值，字段进入 `reviewed_approved`。

审核动作会更新：

- `field_citations.json`
- `simulated_rating.json`
- `simulated_rating_summary.csv`
- `rating_review_queue.json`
- `rating_review_history.json`

评分结果也会写入 SQLite：

- `rating_runs`
  - 保存一次评分运行的总分、等级、行业、待审数量。
- `rating_score_items`
  - 保存 overall、pillar、theme、field 四个层级的评分明细。

查询某个报告目录的评分历史：

```text
GET /rating/runs?report_dir=output/reports/006_600587_新华医疗_2024_新华医疗：新华医疗2024年度ESG报告
```

查询某次评分明细：

```text
GET /rating/runs/{rating_run_id}
```

### Dashboard

启动 FastAPI 后，可以直接打开轻量 Dashboard：

```text
http://127.0.0.1:8000/dashboard?report_dir=output\reports\006_600587_新华医疗_2024_新华医疗：新华医疗2024年度ESG报告
```

Dashboard 展示：

- 模拟总分和等级
- E/S/G 支柱分
- 字段证据覆盖情况
- 待人审字段 Top 10
- 最近评分历史

机器可读汇总接口：

```text
GET /reports/summary?report_dir=output\reports\006_600587_新华医疗_2024_新华医疗：新华医疗2024年度ESG报告
```

## 当前样例结果

以新华医疗 2024 ESG 报告为例：

```text
字段数：60
自动挂证据：45
待人审：15

模拟总分：70.3427
模拟等级：B

E：86.0385，A
S：69.455，CCC
G：53.0667，C
```

检索评测结果：

```text
Hit Rate@5：1.0
MRR@5：0.9
```

优化前检索结果：

```text
Hit Rate@5：0.8667
MRR@5：0.7
```

## 测试

运行全量测试：

```powershell
& "C:\Users\18130\.conda\envs\pachong\python.exe" -m unittest discover -s tests
```

当前测试状态：

```text
Ran 94 tests
OK
```

## 设计边界

本项目使用华证公开 ESG 框架做指标映射和展示，不代表华证内部真实评级模型。

当前模拟评分是项目侧启发式评分，主要用于展示：

- 字段覆盖率
- 证据覆盖率
- E/S/G 维度差异
- 待人审字段对评分的影响

因此输出应称为“模拟评级”或“项目侧评分”，不要称为“华证真实评级”。

## 下一步计划

优先级建议：

1. 人审闭环
   - 增加审核通过、驳回、修正接口。
   - 审核后重算模拟评分。

2. 评分结果落库
   - 保存总分、E/S/G 分、主题分和字段分。
   - 支持 API 查询历史评分。

3. Dashboard
   - 展示报告列表、任务状态、评级结果、证据表和人审队列。

4. 扩展评测集
   - 从单报告扩展到多报告检索评测。
   - 持续记录 Hit Rate、MRR、延迟和 bad cases。

5. Prompt 版本管理
   - 将 Route B、Query Rewrite、评分解释等 prompt 纳入版本追踪。

## 面试表达

推荐表述：

> 构建面向 ESG 评级数据生产的 Agent 系统，基于华证公开 ESG 框架设计指标映射层，结合表格抽取、正文 RAG、Hybrid Retrieval、字段级证据溯源和模拟评分机制，实现从报告解析到评级数据生成、人审队列和任务追踪的完整闭环。
