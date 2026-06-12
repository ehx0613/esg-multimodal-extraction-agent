# Project Memory

这是项目的低 Token 上下文入口。以后分析架构、检查最新运行结果或继续开发时，优先按以下顺序读取：

1. `docs/project_memory/ARCHITECTURE_AND_OPERATIONS.md`
2. `docs/project_memory/LATEST_RESULT.md`
3. `docs/project_memory/LATEST_LOG.md`
4. `docs/project_memory/latest_snapshot.json`
5. 仅在上述文件指出变更或缺失时，再读取对应源码。

刷新命令：

```powershell
python -m scripts.update_project_memory
```

归档规则：

- `runs/<时间>_result.md`：当次扫描得到的结果摘要。
- `logs/<时间>_log.md`：当次扫描、Git 状态和变更上下文。
- `LATEST_RESULT.md`、`LATEST_LOG.md`：始终覆盖为最新版。
- `latest_snapshot.json`：机器可读源码职责、Git 状态和最新运行产物索引。

推荐在每次运行主流程后执行刷新命令，并将 `docs/project_memory/` 纳入 Git。
