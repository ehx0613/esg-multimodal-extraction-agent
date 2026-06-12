# 文档导航

## 当前事实来源

1. [`architecture_current.md`](architecture_current.md)
   - 当前架构、Mermaid 图、运行时序、模块职责和产物契约。
2. [`project_memory/ARCHITECTURE_AND_OPERATIONS.md`](project_memory/ARCHITECTURE_AND_OPERATIONS.md)
   - 当前运维命令、诊断方式和源码目录说明。
3. [`worklogs/2026-06-12_architecture_upgrade.md`](worklogs/2026-06-12_architecture_upgrade.md)
   - MinerU 文档解析和统一流水线升级记录。

## 评估与 Schema

- `schema/core_schema_readable.md`：可读版规范化 60 字段 Schema。
- `schema_60_migration_summary.md`：Schema 迁移记录。
- `eval/README.md`：评估流程和指标定义。
- `v1_results/`：历史基线与回归结果。

## 历史与规划文档

- `architecture.md`：旧版 v1.1 基线，仅作历史参考。
- `architecture_v1_2_design.md`：原始 v1.2 目标设计，大部分内容已经实现。
- `implementation_plan_v1_2.md`：原始实施计划。

当文档内容不一致时，以 `architecture_current.md` 为架构事实来源，
并以 `pipeline/unified_pipeline.py` 的实际行为进行最终确认。
