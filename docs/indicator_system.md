# ESG Indicator System

## Current Scope

The core schema is intentionally kept near the competition requirement instead of expanding every possible table row into a target field.

- Total indicators: 52
- Quantitative indicators: 34
- Qualitative indicators: 18
- Route A: quantitative appendix/table extraction
- Route B: qualitative main-text RAG extraction

## Category Distribution

| Category | Count |
| --- | ---: |
| E | 18 |
| S | 19 |
| G | 15 |

## Quantitative Indicators

### E

- 温室气体排放总量
- 范围一温室气体排放量
- 范围二温室气体排放量
- 能源消耗总量
- 用电量
- 用水量
- 废水排放量
- 废气或大气污染物排放量
- 一般废弃物产生量
- 危险废弃物产生量
- 环保投入金额
- 环境违规或处罚事件数量

### S

- 员工总数
- 男性员工人数
- 女性员工人数
- 女性员工比例
- 员工流失率
- 员工培训总时长
- 员工培训覆盖率
- 受训员工人数
- 安全生产事故数量
- 因工伤损失工作日数
- 研发人员数量
- 研发投入金额
- 公益投入金额

### G

- 董事会人数
- 独立董事人数
- 独立董事比例
- 女性董事人数
- 董事会会议次数
- 股东大会会议次数
- 反腐败培训次数
- 反腐败培训人数
- 确认腐败案件数量

## Qualitative Indicators

### E

- ESG战略目标
- 气候风险识别与管理
- 环境管理体系
- 节能减排措施
- 水资源管理措施
- 废弃物管理措施

### S

- 员工权益保障政策
- 职业健康安全管理体系
- 员工培训与发展机制
- 多元化与平等雇佣政策
- 供应商ESG管理机制
- 数据安全与隐私保护机制

### G

- 董事会ESG监督机制
- ESG治理架构或委员会
- 反腐败政策
- 举报机制与举报人保护
- 商业道德培训机制
- 信息披露与投资者沟通机制

## Design Notes

The schema favors common, auditable indicators that appear across A-share and Hong Kong ESG reports. Industry-specific metrics can be added later as optional schema layers after the 12-report validation workflow is stable.
