# ESG 报告抽取快速上手

本文档面向第一次使用本项目的用户，说明环境配置、PDF 放置位置、
运行命令和结果查看方式。

## 1. 获取项目

```powershell
git clone https://github.com/ehx0613/esg-multimodal-extraction-agent.git
cd esg-multimodal-extraction-agent
```

## 2. 创建 Python 环境

建议使用 Python 3.10 或 3.11。

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

如果 PowerShell 禁止激活脚本，可以在当前终端执行：

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
```

## 3. 创建 `.env`

`.env` 必须放在项目根目录，与 `README.md`、`requirements.txt` 同级：

```text
esg-multimodal-extraction-agent/
├── .env                 <- 放在这里
├── .env.example
├── README.md
├── requirements.txt
├── data/
├── output/
└── scripts/
```

复制示例配置：

```powershell
Copy-Item .env.example .env
```

然后编辑 `.env`，至少填写自己的 DashScope API Key：

```dotenv
DASHSCOPE_API_KEY=你的_DashScope_API_Key
VLM_MODEL=qwen-vl-plus
TEXT_MODEL=qwen-plus-2025-07-28

PDF_PARSER_BACKEND=auto
MINERU_AUTO_RUN_ENABLED=false
MINERU_FALLBACK_TO_PYMUPDF=true
```

注意：

- 不要将 `.env` 或 API Key 提交到 GitHub。
- `.gitignore` 已忽略 `.env`。
- 模型调用会产生费用，费用由 API Key 所属账号承担。

## 4. 放置 ESG 报告

推荐将 PDF 放入项目的 `data/raw/` 目录：

```text
data/
└── raw/
    └── 示例公司_2024_ESG报告.pdf
```

也可以直接向运行命令传入任意 PDF 的完整路径。

## 5. 运行抽取

### 使用 `data/raw/` 中的文件名

```powershell
python -m scripts.run_full_extraction "示例公司_2024_ESG报告.pdf" --mode fast
```

### 使用 PDF 完整路径

```powershell
python -m scripts.run_full_extraction "D:\ESG报告\示例公司_2024_ESG报告.pdf" --mode fast
```

### 不传 PDF 参数

```powershell
python -m scripts.run_full_extraction --mode fast
```

不传参数时，程序会自动选择 `data/raw/` 中找到的第一份 PDF。

运行模式：

| 模式 | 适用场景 |
|---|---|
| `fast` | 首次试跑和日常批量抽取，优先控制模型调用 |
| `balanced` | 需要有限视觉补跑，提高复杂表格召回 |
| `deep` | 需要更高视觉补跑和表格仲裁预算 |

重新执行时，程序默认会复用已有视觉结果。需要强制重新进行视觉抽取时：

```powershell
python -m scripts.run_full_extraction "示例公司_2024_ESG报告.pdf" --mode fast --force-visual
```

## 6. 查看输出

每份 PDF 的输出目录为：

```text
output/reports/<PDF文件名（不含扩展名）>/
```

例如：

```text
output/reports/示例公司_2024_ESG报告/
```

最常用结果：

| 文件 | 用途 |
|---|---|
| `merged_esg_results.json` | 最终合并后的 ESG 字段结果 |
| `merged_esg_results.csv` | 最终结果表格 |
| `standard_esg_results.json` | 路线 A 定量表格结果 |
| `route_b_text_results.json` | 路线 B 定性字段结果 |
| `route_b_quant_results.json` | 路线 B 定量验证与补充结果 |
| `raw_table_metrics.json` | Schema Match 前的原始表格指标 |
| `document.md` | 统一解析后的报告 Markdown |
| `run_manifest.json` | 本次运行状态、配置与产物索引 |
| `unified_pipeline_summary.json` | 完整流水线摘要 |
| `run_cost_summary.json` | 模型调用与成本摘要 |
| `rating_review_queue.json` | 需要人工复核的字段 |

## 7. MinerU 配置

MinerU 是可选增强项，主要用于复杂版面和表格解析。

未安装 MinerU 时，推荐保留：

```dotenv
PDF_PARSER_BACKEND=auto
MINERU_AUTO_RUN_ENABLED=false
MINERU_FALLBACK_TO_PYMUPDF=true
```

系统会优先寻找已有 MinerU 解析产物，找不到时回退到 PyMuPDF。
回退模式仍能运行，但复杂表格和扫描报告的抽取效果可能下降。

如需让程序自动调用 MinerU，需要先在本机安装 MinerU，并在 `.env`
中设置：

```dotenv
MINERU_AUTO_RUN_ENABLED=true
MINERU_COMMAND=你的 MinerU 命令模板
MINERU_OUTPUT_ROOT=output/mineru_test
```

`MINERU_COMMAND` 的具体格式取决于本机安装的 MinerU CLI。

## 8. 验证安装

运行架构相关测试：

```powershell
python -m pytest -q tests/test_architecture_upgrade.py tests/test_unified_pipeline_architecture.py
```

运行完整测试：

```powershell
python -m pytest -q
```

## 9. 常见问题

### 提示 `DASHSCOPE_API_KEY` 为空

检查项目根目录是否存在 `.env`，并确认其中已填写：

```dotenv
DASHSCOPE_API_KEY=你的真实Key
```

### 找不到 PDF

确认 PDF 位于 `data/raw/`，或者向命令传入正确的完整路径。

### 抽取结果在哪里

查看：

```text
output/reports/<PDF文件名>/
```

优先查看 `merged_esg_results.json` 和 `run_manifest.json`。

### 为什么没有使用 MinerU

检查 `run_manifest.json` 中的解析器信息，并确认本机是否已安装 MinerU、
`MINERU_AUTO_RUN_ENABLED` 是否开启，以及 `MINERU_COMMAND` 是否正确。

### 为什么部分字段需要人工复核

系统会保守处理证据冲突、低置信度和缺失字段。这些字段会写入
`rating_review_queue.json`，避免不可靠结果被直接当作最终答案。
