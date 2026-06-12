# 60 项核心 Schema 口径统一总结

## 结论

项目当前正式核心指标体系确认为 60 项，正式版本号为：

```text
core_esg_v4.1_60
```

指标构成为：

| 项目 | 数量 |
| --- | ---: |
| 总指标 | 60 |
| 定量指标 / Route A | 42 |
| 定性指标 / Route B | 18 |
| E / S / G | 21 / 24 / 15 |

## 本次修改

### 1. 建立正式 Schema 元数据

在 `config/schema/views.py` 中新增：

```python
CORE_SCHEMA_VERSION = "core_esg_v4.1_60"
CORE_SCHEMA_FIELD_COUNT = len(ALL_SCHEMA)
```

并通过 `config.schema` 统一导出，供运行时、测试和后续文档生成使用。

### 2. 移除运行时写死的 68

- `SupervisorAgent` 默认预期字段数改为 `CORE_SCHEMA_FIELD_COUNT`。
- `ESGAgentHarness` 默认预期字段数改为 `CORE_SCHEMA_FIELD_COUNT`。
- ResultGuard 原本已经根据 `ESG_FIELD_KEYS` 动态计算字段数，无需修改。

现在监督检查、标准结果行数检查和合并结果行数检查默认都以当前 Schema 实际数量 60 为准。

### 3. 更新与归档文档口径

- 将 `docs/indicator_system.md` 更新为正式 60 项口径。
- 将包含 68 项口径的架构设计、历史版本结果和评估说明标记为历史口径。
- 保留历史数据中的 52/68 数值，避免篡改旧实验结果，但明确它们不能作为当前评分分母。

### 4. 增加 Schema 冻结测试

结构测试新增以下断言：

- 正式字段数必须为 60。
- 正式版本号必须为 `core_esg_v4.1_60`。
- 指标构成必须保持 `42/18` 和 `21/24/15`。

## 验证结果

使用项目 Conda 环境执行：

```powershell
& 'C:\Users\18130\.conda\envs\pachong\python.exe' -m unittest tests.test_schema_structure tests.test_huazheng_public_mapping tests.test_rating_data_harness tests.test_full_rating_workflow
```

结果：

```text
Ran 12 tests
OK
```

## 建议提交到 GitHub 的文件

```text
VERSION.md
agents/supervisor_agent.py
config/schema/__init__.py
config/schema/views.py
docs/architecture_v1_2_design.md
docs/eval/README.md
docs/indicator_system.md
docs/schema_60_migration_summary.md
pipeline/agent_harness.py
tests/test_schema_structure.py
```

不要把本次无关的 `output/mineru_test/`、`docs/project_memory/`、`scripts/update_project_memory.py` 或 `utils/project_memory.py` 一并加入此次提交。

## GitHub 上传步骤

当前分支为 `v1.2-agent-harness`，远程仓库为：

```text
https://github.com/ehx0613/esg-multimodal-extraction-agent.git
```

只暂存本次修改：

```powershell
git add VERSION.md agents/supervisor_agent.py config/schema/__init__.py config/schema/views.py docs/architecture_v1_2_design.md docs/eval/README.md docs/indicator_system.md docs/schema_60_migration_summary.md pipeline/agent_harness.py tests/test_schema_structure.py
```

检查暂存内容：

```powershell
git diff --cached --stat
git diff --cached
```

提交并推送：

```powershell
git commit -m "fix: unify core ESG schema at 60 fields"
git push origin v1.2-agent-harness
```

推送后可在 GitHub 上从 `v1.2-agent-harness` 向目标分支创建 Pull Request。

