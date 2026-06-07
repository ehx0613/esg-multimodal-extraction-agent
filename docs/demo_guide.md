# ESG Rating Agent Demo Guide

这份文档用于面试或项目展示。目标是用一条清晰路线讲明白：项目解决什么问题、系统怎么跑、输出怎么看、为什么这样设计。

## 1. 项目一句话

构建面向 ESG 评级数据生产的 Agent 系统，基于华证公开 ESG 框架设计指标映射层，结合表格抽取、正文 RAG、Hybrid Retrieval、字段级证据溯源、模拟评分和人审队列，实现从报告解析到评级数据生成、审核和任务追踪的完整闭环。

## 2. 业务问题

ESG 评级数据生产通常需要人工阅读上市公司 ESG 报告，整理指标、核对原文证据、判断字段是否可用。这个过程有三个痛点：

1. 报告篇幅长，表格和正文混杂，人工整理效率低。
2. 抽取结果如果没有原文证据，很难用于评级、审核和复核。
3. 大模型输出存在不确定性，关键字段需要人机协同确认。

本项目的目标不是做聊天问答，而是让 Agent 围绕“ESG 评级数据生产”完成一个可追踪的业务流程。

## 3. 系统架构

```text
ESG 报告目录
  |
  |-- Route A：附录/表格抽取
  |     -> standard_esg_results.json/csv
  |
  |-- Route B：正文 RAG 抽取
  |     -> route_b_chunks.json
  |     -> route_b_text_results.json/csv
  |
  |-- Merge：保守合并 Route A / Route B
  |     -> merged_esg_results.json/csv
  |
  |-- Rating Data Harness：任务追踪
  |     -> reports / tasks / agent_runs / review_items
  |
  |-- Field Citations：字段级证据溯源
  |     -> field_citations.json/csv
  |
  |-- Simulated Rating：项目侧模拟评级
  |     -> simulated_rating.json
  |     -> simulated_rating_summary.csv
  |
  |-- Human Review：人审队列
  |     -> rating_review_queue.json
  |     -> rating_review_history.json
  |
  |-- FastAPI / SQLite / Dashboard
        -> trace、评分历史、证据、人审状态查询
```

## 4. 核心模块

### 指标体系映射

文件：

- `config/schema/huazheng_public_mapping.py`

作用：

- 使用华证公开 ESG 框架作为上层结构。
- 包含 3 个支柱、16 个主题、44 个关键指标。
- 将项目 60 个字段挂载到主题和关键指标下。

注意表达：

> 本项目参考华证公开框架做项目侧指标映射和模拟评分，不代表华证内部真实评级模型。

### 检索与评测

文件：

- `utils/bm25_retriever.py`
- `utils/query_rewriter.py`
- `utils/hybrid_retriever.py`
- `utils/retrieval_eval.py`
- `scripts/evaluate_retrieval.py`

能力：

- BM25 关键词检索。
- Query Rewrite 字段查询改写。
- 多 query BM25 聚合。
- RRF 融合接口。
- Evidence rerank 压低目录、索引、议题矩阵等泛页面。
- Hit Rate / MRR 评测。

样例提升：

```text
优化前：
Hit Rate@5 = 0.8667
MRR@5 = 0.7000

优化后：
Hit Rate@5 = 1.0
MRR@5 = 0.9
```

### 证据溯源

文件：

- `utils/field_citations.py`
- `scripts/attach_field_citations.py`

能力：

- 给每个字段挂载页码、chunk_id、证据文本、检索分数。
- 区分自动证据和需要人工复核的证据。
- 对 Route A 表格证据使用 `table_page_xx` 虚拟引用，避免正文 chunk 和表格页不一致导致误判。

### 模拟评分

文件：

- `utils/simulated_rating.py`
- `scripts/generate_simulated_rating.py`

能力：

- 生成总分、E/S/G 分、主题分、字段分。
- 根据字段是否抽取成功、证据是否自动通过、高优先级字段权重进行项目侧启发式评分。
- 输出 `rating_review_queue.json`。

### 人审闭环

文件：

- `utils/rating_review.py`
- `scripts/review_rating_item.py`

能力：

- 支持 `approve`、`reject`、`correct`。
- 审核后更新 `field_citations.json`。
- 追加 `rating_review_history.json`。
- 自动重算 `simulated_rating.json`。
- 新评分写入 SQLite。

### 后端与 Dashboard

文件：

- `backend/app.py`
- `backend/database.py`

能力：

- FastAPI 服务。
- SQLite 存储任务、Trace、检索评测、评分历史。
- Dashboard 展示评分、E/S/G 分、人审队列、评分历史。

## 5. 运行准备

进入项目目录：

```powershell
cd "C:\Users\18130\PycharmProjects\爬虫\esg-multimodal-extraction-agent"
```

使用当前 Conda 环境：

```powershell
C:\Users\18130\.conda\envs\pachong\python.exe
```

## 6. 一键运行样例

如果已经有报告处理结果，推荐使用 `--skip-harness`，只重建证据、评分和 Dashboard 所需文件：

```powershell
& "C:\Users\18130\.conda\envs\pachong\python.exe" -m scripts.run_full_rating_workflow "output\reports\006_600587_新华医疗_2024_新华医疗：新华医疗2024年度ESG报告" --industry manufacturing --skip-harness
```

输出文件：

- `field_citations.json`
- `field_citations.csv`
- `simulated_rating.json`
- `simulated_rating_summary.csv`
- `rating_review_queue.json`
- `full_rating_workflow_summary.json`

样例输出：

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

## 7. 启动后端

```powershell
& "C:\Users\18130\.conda\envs\pachong\python.exe" -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
```

健康检查：

```text
http://127.0.0.1:8000/health
```

Dashboard：

```text
http://127.0.0.1:8000/dashboard?report_dir=output\reports\006_600587_新华医疗_2024_新华医疗：新华医疗2024年度ESG报告
```

机器可读汇总：

```text
http://127.0.0.1:8000/reports/summary?report_dir=output\reports\006_600587_新华医疗_2024_新华医疗：新华医疗2024年度ESG报告
```

## 8. 演示顺序

建议按这个顺序讲：

1. 先讲业务问题  
   ESG 评级数据生产需要抽取、证据、审核，不是简单问答。

2. 展示一键流程  
   运行 `scripts.run_full_rating_workflow`。

3. 展示输出文件  
   重点看：
   - `field_citations.csv`
   - `simulated_rating_summary.csv`
   - `rating_review_queue.json`

4. 打开 Dashboard  
   展示总分、E/S/G 分、待审字段。

5. 讲检索评测  
   说明 Hit Rate@5 和 MRR@5 的提升。

6. 讲人审闭环  
   解释 `approve / reject / correct` 之后会重算评分并写历史。

7. 讲后端工程  
   说明 FastAPI、SQLite、task、trace、rating_runs、rating_score_items。

## 9. 人审操作示例

命令行修正一个字段：

```powershell
& "C:\Users\18130\.conda\envs\pachong\python.exe" -m scripts.review_rating_item "output\reports\006_600587_新华医疗_2024_新华医疗：新华医疗2024年度ESG报告" --field-key climate_risk_management --action correct --industry manufacturing --value true --confidence 0.9 --evidence "公司识别实体及转型气候风险。"
```

API 修正字段：

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

审核动作含义：

- `approve`：证据通过，字段进入 `reviewed_approved`。
- `reject`：候选证据不支持字段，字段进入 `reviewed_rejected`。
- `correct`：人工补录或修正字段值，字段进入 `reviewed_approved`。

## 10. 面试讲法

### 项目介绍

> 这个项目面向 ESG 评级数据生产场景。系统从上市公司 ESG 报告中抽取定量和定性指标，参考华证公开 ESG 框架做指标映射，再通过 Hybrid Retrieval 和字段级证据溯源给每个字段挂原文依据，最后生成项目侧模拟评级和人审队列。它不是一个简单 RAG 问答 Demo，而是包含任务追踪、检索评测、证据审核和评分历史的 Agent 后端系统。

### 为什么要做华证映射

> 如果只抽字段，项目更像信息抽取工具。引入华证公开框架后，字段可以归入 E/S/G、主题和关键指标，输出可以服务评级数据生产。但我没有声称复刻华证内部模型，评分规则是项目侧启发式模拟。

### 为什么需要 Hybrid Retrieval

> ESG 报告里有很多专业字段。单纯向量检索容易漏关键词，单纯 BM25 又不够语义化。所以项目里做了查询改写、BM25 多 query 聚合、RRF 接口和证据 rerank，并用 Hit Rate 和 MRR 验证效果。

### 为什么要 Human-in-the-loop

> ESG 评级数据属于高可信场景，大模型不能盲目全自动。缺失字段、证据不稳字段会进入人审队列，人工审核后系统会更新字段状态、记录审核历史并重算评分。

### 为什么用 SQLite

> 当前项目是本地演示和实习作品，SQLite 部署成本低，适合快速展示完整工程闭环。数据库访问层已经封装，后续可以迁移 PostgreSQL。

## 11. 常见追问

### 这个是不是华证真实评级？

不是。项目参考华证公开 ESG 框架做指标映射，模拟评分是项目侧启发式规则，不代表华证内部真实模型。

### Agent 体现在哪里？

体现在任务流和状态管理，而不是聊天：

```text
Supervisor / Route A / Route B / Merge / Citation / Rating / Review
```

系统会记录任务状态、Agent run、评测结果、评分历史和人审状态。

### 你怎么证明检索优化有效？

用人工构造的检索评测集，评估 Hit Rate@5 和 MRR@5。新华医疗样例中，Hit Rate@5 从 0.8667 提升到 1.0，MRR@5 从 0.7 提升到 0.9。

### 现在系统还有什么不足？

1. 评测集还只有少量样例，需要扩展到更多报告。
2. 模拟评分不是专业评级模型，只用于项目侧展示。
3. Dashboard 目前是轻量 HTML，后续可做更完整前端。
4. Prompt 版本管理已有表结构，但还可以更深入接入具体 LLM 调用。

## 12. 下一步计划

优先级：

1. 扩展多报告评测集。
2. 补更多 Dashboard 交互能力。
3. 接入 Prompt 版本管理到实际 LLM 调用。
4. 增加批量报告评分对比。
5. 后续根据需要迁移 PostgreSQL。

