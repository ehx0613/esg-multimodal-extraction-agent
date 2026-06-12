# Core Schema Readable Export

## Summary

- Total: 60
- Quantitative: 42
- Qualitative: 18
- E: 21
- S: 24
- G: 15

## Fields

### 1. `total_ghg_emissions`

- `name_cn`: 温室气体排放总量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: ghg
- `unit_required`: True
- `year_required`: True
- `aliases`: ["温室气体排放总量", "温室气体排放总计", "碳排放总量", "GHG排放总量"]
- `required_any`: ["温室气体排放总量", "温室气体排放总计", "碳排放总量", "GHG排放总量"]
- `forbidden_any`: ["范围一", "范围1", "Scope 1", "范围二", "范围2", "Scope 2", "范围三", "范围3", "Scope 3", "强度"]
- `unit_examples`: ["吨CO2e", "吨二氧化碳当量", "二氧化碳当量公吨数", "tCO2e"]

### 2. `ghg_emissions_intensity`

- `name_cn`: 温室气体排放强度
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: intensity
- `unit_required`: True
- `year_required`: True
- `aliases`: ["温室气体排放强度", "温室气体排放密度", "碳排放强度", "碳排放密度", "GHG排放强度", "单位营收温室气体排放", "单位收入温室气体排放"]
- `required_any`: ["强度", "密度", "单位营收", "单位收入"]
- `forbidden_any`: ["总量", "范围一", "范围1", "Scope 1", "范围二", "范围2", "Scope 2"]
- `unit_examples`: ["吨CO2e/万元", "吨二氧化碳当量/万元", "tCO2e/百万元"]

### 3. `scope_1_emissions`

- `name_cn`: 范围一温室气体排放量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: ghg
- `unit_required`: True
- `year_required`: True
- `aliases`: ["范围一温室气体排放量", "范围1温室气体排放量", "Scope 1排放", "直接温室气体排放"]
- `required_any`: ["范围一", "范围1", "Scope 1", "直接温室气体"]
- `forbidden_any`: ["范围二", "范围2", "Scope 2", "范围三", "范围3", "Scope 3"]
- `unit_examples`: ["吨CO2e", "吨二氧化碳当量", "二氧化碳当量公吨数", "tCO2e"]

### 4. `scope_2_emissions`

- `name_cn`: 范围二温室气体排放量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: ghg
- `unit_required`: True
- `year_required`: True
- `aliases`: ["范围二温室气体排放量", "范围2温室气体排放量", "Scope 2排放", "间接温室气体排放"]
- `required_any`: ["范围二", "范围2", "Scope 2", "间接温室气体"]
- `forbidden_any`: ["范围一", "范围1", "Scope 1", "范围三", "范围3", "Scope 3"]
- `unit_examples`: ["吨CO2e", "吨二氧化碳当量", "二氧化碳当量公吨数", "tCO2e"]

### 5. `energy_consumption_total`

- `name_cn`: 能源消耗总量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: energy
- `unit_required`: True
- `year_required`: True
- `aliases`: ["能源消耗总量", "综合能源消耗", "能源使用总量", "直接能源消耗"]
- `required_any`: ["能源消耗总量", "综合能源消耗", "能源使用总量", "直接能源消耗"]
- `forbidden_any`: ["强度", "密度", "单位产值"]
- `unit_examples`: ["兆瓦时", "MWh", "千瓦时", "吨标准煤"]

### 6. `energy_consumption_intensity`

- `name_cn`: 能源消耗强度
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: intensity
- `unit_required`: True
- `year_required`: True
- `aliases`: ["能源消耗强度", "能源消耗密度", "综合能源消耗强度", "综合能源消耗密度", "单位能源消耗", "单位产值综合能耗", "单位营收能源消耗", "能耗强度", "能耗密度"]
- `required_any`: ["强度", "密度", "单位", "单耗"]
- `forbidden_any`: ["总量", "总能耗", "综合能源消耗量"]
- `unit_examples`: ["吨标准煤/万元", "吨标煤/万元", "千瓦时/万元", "兆瓦时/万元"]

### 7. `natural_gas_consumption`

- `name_cn`: 天然气消耗量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: energy
- `unit_required`: True
- `year_required`: True
- `aliases`: ["天然气", "天然气消耗量", "天然气使用量", "天然气用量", "天然气耗用量"]
- `required_any`: ["天然气"]
- `forbidden_any`: ["排放因子", "排放系数", "换算系数", "核算方法"]
- `unit_examples`: ["立方米", "万立方米", "m3", "m³", "吉焦"]

### 8. `electricity_consumption`

- `name_cn`: 用电量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: energy
- `unit_required`: True
- `year_required`: True
- `aliases`: ["用电量", "耗电量", "电力消耗", "电力总量", "外购电力"]
- `required_any`: ["用电量", "耗电量", "电力消耗", "电力总量", "外购电力"]
- `forbidden_any`: ["绿电", "可再生能源"]
- `unit_examples`: ["千瓦时", "兆瓦时", "kWh", "MWh"]

### 9. `water_consumption`

- `name_cn`: 用水量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: water
- `unit_required`: True
- `year_required`: True
- `aliases`: ["用水量", "取水量", "新鲜水用量", "总耗水量", "市政用水量", "市政购水量"]
- `required_any`: ["用水量", "取水量", "新鲜水用量", "总耗水量", "市政用水量", "市政购水量"]
- `forbidden_any`: ["废水", "回用水", "循环水", "强度"]
- `unit_examples`: ["吨", "立方米"]

### 10. `wastewater_discharge`

- `name_cn`: 废水排放量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: water
- `unit_required`: True
- `year_required`: True
- `aliases`: ["废水排放量", "污水排放量", "废水排放总量"]
- `required_any`: ["废水排放量", "污水排放量", "废水排放总量"]
- `forbidden_any`: ["回用水", "循环水"]
- `unit_examples`: ["吨", "立方米"]

### 11. `air_pollutant_emissions`

- `name_cn`: 废气或大气污染物排放量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: mass
- `unit_required`: True
- `year_required`: True
- `aliases`: ["废气排放量", "大气污染物排放量", "氮氧化物排放量", "二氧化硫排放量", "颗粒物排放量", "VOCs排放量"]
- `required_any`: ["废气排放量", "大气污染物排放量", "氮氧化物排放量", "二氧化硫排放量", "颗粒物排放量", "VOCs排放量"]
- `forbidden_any`: []
- `unit_examples`: ["吨", "千克"]

### 12. `non_hazardous_waste`

- `name_cn`: 一般废弃物产生量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: waste
- `unit_required`: True
- `year_required`: True
- `aliases`: ["一般废弃物产生量", "一般废弃物产生总量", "无害废弃物量", "无害废弃物产生量", "无害废弃物产生总量", "无害废弃物总量", "非危险废弃物", "非危险废弃物量", "非危险废弃物产生总量", "一般固体废弃物"]
- `required_any`: ["一般废弃物产生量", "一般废弃物产生总量", "无害废弃物量", "无害废弃物产生量", "无害废弃物产生总量", "无害废弃物总量", "非危险废弃物", "非危险废弃物量", "非危险废弃物产生总量", "一般固体废弃物"]
- `forbidden_any`: ["危险废弃物", "危废"]
- `unit_examples`: ["吨", "千克"]

### 13. `hazardous_waste`

- `name_cn`: 危险废弃物产生量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: waste
- `unit_required`: True
- `year_required`: True
- `aliases`: ["危险废弃物产生量", "危废产生量", "有害废弃物", "危险废物"]
- `required_any`: ["危险废弃物产生量", "危废产生量", "有害废弃物", "危险废物"]
- `forbidden_any`: []
- `unit_examples`: ["吨", "千克"]

### 14. `environmental_investment`

- `name_cn`: 环保投入金额
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: money
- `unit_required`: True
- `year_required`: True
- `aliases`: ["环保投入", "环保总投资", "环保总投入", "环境保护投入", "环保投资"]
- `required_any`: ["环保投入", "环保总投资", "环保总投入", "环境保护投入", "环保投资"]
- `forbidden_any`: []
- `unit_examples`: ["万元", "元", "百万元"]

### 15. `environmental_penalty_count`

- `name_cn`: 环境违规或处罚事件数量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["环境违规或处罚事件数量", "环境处罚次数", "环保处罚", "环境违法违规事件", "环境行政处罚"]
- `required_any`: ["环境违规或处罚事件数量", "环境处罚次数", "环保处罚", "环境违法违规事件", "环境行政处罚"]
- `forbidden_any`: []
- `unit_examples`: ["次", "件", "起"]

### 16. `total_employees`

- `name_cn`: 员工总数
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: person_count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["员工总数", "雇员总数", "员工人数", "在职员工总数", "员工总人数"]
- `required_any`: ["员工总数", "雇员总数", "员工人数", "在职员工总数", "员工总人数"]
- `forbidden_any`: ["男性", "女性", "少数民族", "30岁", "50岁", "按年龄", "按性别", "按职位", "按员工类别", "培训", "董事", "体检", "探亲"]
- `unit_examples`: ["人", "名"]

### 17. `male_employees`

- `name_cn`: 男性员工人数
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: person_count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["男性员工人数", "男员工人数", "男性雇员人数", "男性员工"]
- `required_any`: ["男性员工人数", "男员工人数", "男性雇员人数", "男性员工"]
- `forbidden_any`: ["比例", "%", "女性", "高级管理层", "执行管理层", "管理层"]
- `unit_examples`: ["人", "名"]

### 18. `female_employees`

- `name_cn`: 女性员工人数
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: person_count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["女性员工人数", "女员工人数", "女性雇员人数", "女性员工"]
- `required_any`: ["女性员工人数", "女员工人数", "女性雇员人数", "女性员工"]
- `forbidden_any`: ["比例", "%", "男性", "女性管理层", "高级管理层", "执行管理层", "管理层", "育儿假", "产假", "生育假", "享受假期"]
- `unit_examples`: ["人", "名"]

### 19. `female_employee_ratio`

- `name_cn`: 女性员工比例
- `category`: S
- `indicator_type`: quantitative
- `value_type`: percentage
- `preferred_source`: appendix_table
- `unit_type`: percentage
- `unit_required`: True
- `year_required`: True
- `aliases`: ["女性员工比例", "女性员工占比", "女员工占比", "女性雇员比例"]
- `required_any`: ["女性员工比例", "女性员工占比", "女员工占比", "女性雇员比例"]
- `forbidden_any`: ["女性管理层", "女性董事"]
- `unit_examples`: ["%"]

### 20. `employee_turnover_rate`

- `name_cn`: 员工流失率
- `category`: S
- `indicator_type`: quantitative
- `value_type`: percentage
- `preferred_source`: appendix_table
- `unit_type`: percentage
- `unit_required`: True
- `year_required`: True
- `aliases`: ["员工流失率", "员工离职率", "雇员流失率", "员工流动率"]
- `required_any`: ["员工流失率", "员工离职率", "雇员流失率", "员工流动率"]
- `forbidden_any`: []
- `unit_examples`: ["%"]

### 21. `training_total_hours`

- `name_cn`: 员工培训总时长
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: hour
- `unit_required`: True
- `year_required`: True
- `aliases`: ["员工培训总时长", "培训总时长", "培训总小时", "员工培训总小时数", "累计培训时长", "安全培训总时长"]
- `required_any`: ["员工培训总时长", "培训总时长", "培训总小时", "员工培训总小时数", "累计培训时长", "安全培训总时长"]
- `forbidden_any`: ["人均", "供应商", "反腐败", "廉洁", "商业道德"]
- `unit_examples`: ["小时"]

### 22. `training_hours_per_employee`

- `name_cn`: 人均培训时长
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: hour
- `unit_required`: True
- `year_required`: True
- `aliases`: ["人均培训时长", "员工平均培训时数", "员工受训平均时数", "平均培训时数", "平均培训小时数"]
- `required_any`: ["人均", "平均"]
- `forbidden_any`: ["高层", "中层", "基层", "新员工", "新入职", "反腐败", "廉洁", "安全培训"]
- `unit_examples`: ["小时", "小时/人"]

### 23. `training_coverage_rate`

- `name_cn`: 员工培训覆盖率
- `category`: S
- `indicator_type`: quantitative
- `value_type`: percentage
- `preferred_source`: appendix_table
- `unit_type`: percentage
- `unit_required`: True
- `year_required`: True
- `aliases`: ["员工培训覆盖率", "培训覆盖率", "受训员工比例", "员工培训参与率"]
- `required_any`: ["员工培训覆盖率", "培训覆盖率", "受训员工比例", "员工培训参与率"]
- `forbidden_any`: ["税务", "供应商", "安全", "质量", "环保", "反腐败", "反贪污", "商业贿赂", "廉洁", "合规"]
- `unit_examples`: ["%"]

### 24. `social_security_coverage`

- `name_cn`: 社会保险覆盖率
- `category`: S
- `indicator_type`: quantitative
- `value_type`: percentage
- `preferred_source`: appendix_table
- `unit_type`: percentage
- `unit_required`: True
- `year_required`: True
- `aliases`: ["社会保险覆盖率", "社保覆盖率", "员工社保覆盖率", "社会保险参保率", "社会保险缴纳覆盖率"]
- `required_any`: ["社会保险", "社保"]
- `forbidden_any`: []
- `unit_examples`: ["%"]

### 25. `employee_medical_checkup_coverage`

- `name_cn`: 员工体检覆盖率
- `category`: S
- `indicator_type`: quantitative
- `value_type`: percentage
- `preferred_source`: appendix_table
- `unit_type`: percentage
- `unit_required`: True
- `year_required`: True
- `aliases`: ["员工体检覆盖率", "体检覆盖率", "员工健康体检覆盖率", "职业健康体检覆盖率"]
- `required_any`: ["体检", "健康体检"]
- `forbidden_any`: []
- `unit_examples`: ["%"]

### 26. `trained_employees_count`

- `name_cn`: 受训员工人数
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: person_time
- `unit_required`: True
- `year_required`: True
- `aliases`: ["受训员工人数", "培训员工人数", "参与培训员工人数", "员工培训人次", "受训人次", "接受培训总人数", "接受培训总人次", "员工接受培训总人数"]
- `required_any`: ["受训员工人数", "培训员工人数", "参与培训员工人数", "员工培训人次", "受训人次", "接受培训总人数", "接受培训总人次", "员工接受培训总人数"]
- `forbidden_any`: []
- `unit_examples`: ["人", "人次"]

### 27. `safety_accident_count`

- `name_cn`: 安全生产事故数量
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["安全生产事故数量", "安全事故数", "生产安全事故数", "生产安全事故", "工伤事故数量"]
- `required_any`: ["安全生产事故数量", "安全事故数", "生产安全事故数", "生产安全事故", "工伤事故数量"]
- `forbidden_any`: []
- `unit_examples`: ["起", "次", "件"]

### 28. `occupational_health_safety_investment`

- `name_cn`: 安全生产投入
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: money
- `unit_required`: True
- `year_required`: True
- `aliases`: ["安全生产投入", "职业健康安全投入", "安全投入", "安全生产费用", "安全费用投入"]
- `required_any`: ["安全", "职业健康"]
- `forbidden_any`: ["事故", "次数", "演练"]
- `unit_examples`: ["万元", "元", "百万元"]

### 29. `safety_emergency_drill_count`

- `name_cn`: 安全应急演练次数
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["安全应急演练次数", "应急演练次数", "安全演练次数", "应急演练场次", "安全应急演练场次"]
- `required_any`: ["演练"]
- `forbidden_any`: ["培训", "投入", "事故"]
- `unit_examples`: ["次", "场"]

### 30. `lost_work_days_due_to_injury`

- `name_cn`: 因工伤损失工作日数
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["因工伤损失工作日数", "工伤损失工作日", "损失工时", "因工伤损失天数"]
- `required_any`: ["因工伤损失工作日数", "工伤损失工作日", "损失工时", "因工伤损失天数"]
- `forbidden_any`: []
- `unit_examples`: ["天", "日", "小时"]

### 31. `r_and_d_personnel_count`

- `name_cn`: 研发人员数量
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: person_count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["研发人员数量", "研发人员人数", "研发员工人数", "研发人员总数"]
- `required_any`: ["研发人员数量", "研发人员人数", "研发员工人数", "研发人员总数"]
- `forbidden_any`: ["比例", "%", "投入"]
- `unit_examples`: ["人", "名"]

### 32. `r_and_d_expense`

- `name_cn`: 研发投入金额
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: money
- `unit_required`: True
- `year_required`: True
- `aliases`: ["研发投入金额", "研发投入", "公司研发总投入", "研发费用", "研发支出"]
- `required_any`: ["研发投入金额", "研发投入", "公司研发总投入", "研发费用", "研发支出"]
- `forbidden_any`: ["研发人员"]
- `unit_examples`: ["万元", "元", "百万元"]

### 33. `public_welfare_investment`

- `name_cn`: 公益投入金额
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: money
- `unit_required`: True
- `year_required`: True
- `aliases`: ["公益投入金额", "公益投入", "社会公益投入", "慈善捐赠金额", "对外捐赠", "对外捐赠金额"]
- `required_any`: ["公益投入金额", "公益投入", "社会公益投入", "慈善捐赠金额", "对外捐赠", "对外捐赠金额"]
- `forbidden_any`: []
- `unit_examples`: ["万元", "元", "百万元"]

### 34. `board_size`

- `name_cn`: 董事会人数
- `category`: G
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: person_count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["董事会人数", "董事人数", "董事会成员人数", "董事总数"]
- `required_any`: ["董事会人数", "董事人数", "董事会成员人数", "董事总数"]
- `forbidden_any`: ["独立董事", "女性董事", "%", "比例", "高管", "高级管理人员"]
- `unit_examples`: ["人", "名"]

### 35. `independent_directors`

- `name_cn`: 独立董事人数
- `category`: G
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: person_count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["独立董事人数", "独立董事数量", "独董人数"]
- `required_any`: ["独立董事人数", "独立董事数量", "独董人数"]
- `forbidden_any`: ["比例", "%"]
- `unit_examples`: ["人", "名"]

### 36. `independent_director_ratio`

- `name_cn`: 独立董事比例
- `category`: G
- `indicator_type`: quantitative
- `value_type`: percentage
- `preferred_source`: appendix_table
- `unit_type`: percentage
- `unit_required`: True
- `year_required`: True
- `aliases`: ["独立董事比例", "独立董事占比", "独董比例", "独董占比"]
- `required_any`: ["独立董事比例", "独立董事占比", "独董比例", "独董占比"]
- `forbidden_any`: ["人数", "数量", "审计委员会", "提名委员会", "薪酬与考核委员会", "专门委员会"]
- `unit_examples`: ["%"]

### 37. `female_directors`

- `name_cn`: 女性董事人数
- `category`: G
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: person_count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["女性董事人数", "女董事人数", "女性董事数量", "女性董事"]
- `required_any`: ["女性董事人数", "女董事人数", "女性董事数量", "女性董事"]
- `forbidden_any`: ["比例", "%"]
- `unit_examples`: ["人", "名"]

### 38. `board_meetings`

- `name_cn`: 董事会会议次数
- `category`: G
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["董事会会议次数", "董事会召开次数", "召开董事会", "董事会会议"]
- `required_any`: ["董事会会议次数", "董事会召开次数", "召开董事会", "董事会会议"]
- `forbidden_any`: ["股东大会", "监事会", "专门委员会", "战略委员会", "审计委员会", "提名委员会", "薪酬与考核委员会"]
- `unit_examples`: ["次", "场"]

### 39. `shareholder_meetings`

- `name_cn`: 股东大会会议次数
- `category`: G
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["股东大会会议次数", "股东大会召开次数", "股东大会次数", "召开股东大会"]
- `required_any`: ["股东大会会议次数", "股东大会召开次数", "股东大会次数", "召开股东大会"]
- `forbidden_any`: ["董事会", "监事会"]
- `unit_examples`: ["次", "场"]

### 40. `anti_corruption_training_sessions`

- `name_cn`: 反腐败培训次数
- `category`: G
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["反腐败培训次数", "廉洁培训次数", "反舞弊培训次数", "商业道德培训次数"]
- `required_any`: ["反腐败培训次数", "廉洁培训次数", "反舞弊培训次数", "商业道德培训次数"]
- `forbidden_any`: ["人数", "人次", "小时"]
- `unit_examples`: ["次", "场"]

### 41. `anti_corruption_training_participants`

- `name_cn`: 反腐败培训人数
- `category`: G
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: person_time
- `unit_required`: True
- `year_required`: True
- `aliases`: ["反腐败培训人数", "廉洁培训人数", "反舞弊培训人数", "商业道德培训人数", "反腐败培训人次"]
- `required_any`: ["反腐败培训人数", "廉洁培训人数", "反舞弊培训人数", "商业道德培训人数", "反腐败培训人次"]
- `forbidden_any`: ["次数", "小时"]
- `unit_examples`: ["人", "人次"]

### 42. `confirmed_corruption_cases`

- `name_cn`: 确认腐败案件数量
- `category`: G
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["确认腐败案件数量", "腐败案件数量", "贪污腐败案件", "商业贿赂案件"]
- `required_any`: ["确认腐败案件数量", "腐败案件数量", "贪污腐败案件", "商业贿赂案件"]
- `forbidden_any`: ["培训"]
- `unit_examples`: ["件", "起", "宗"]

### 43. `esg_strategy_targets`

- `name_cn`: ESG战略目标
- `category`: E
- `indicator_type`: qualitative
- `value_type`: boolean_or_text
- `preferred_source`: main_text_rag
- `unit_type`: text
- `unit_required`: False
- `year_required`: False
- `aliases`: ["ESG战略目标", "可持续发展目标", "ESG目标", "可持续发展战略"]
- `required_any`: ["ESG", "目标", "战略"]
- `forbidden_any`: ["指标索引", "内容索引", "GRI", "目录"]
- `unit_examples`: []

### 44. `climate_risk_management`

- `name_cn`: 气候风险识别与管理
- `category`: E
- `indicator_type`: qualitative
- `value_type`: boolean_or_text
- `preferred_source`: main_text_rag
- `unit_type`: text
- `unit_required`: False
- `year_required`: False
- `aliases`: ["气候风险管理", "气候变化风险", "气候相关风险", "气候风险识别"]
- `required_any`: ["气候", "风险"]
- `forbidden_any`: ["指标索引", "内容索引", "GRI", "目录"]
- `unit_examples`: []

### 45. `environmental_management_system`

- `name_cn`: 环境管理体系
- `category`: E
- `indicator_type`: qualitative
- `value_type`: boolean_or_text
- `preferred_source`: main_text_rag
- `unit_type`: text
- `unit_required`: False
- `year_required`: False
- `aliases`: ["环境管理体系", "环境管理制度", "ISO 14001", "环境保护管理"]
- `required_any`: ["环境", "管理"]
- `forbidden_any`: ["指标索引", "内容索引", "GRI", "目录"]
- `unit_examples`: []

### 46. `energy_saving_measures`

- `name_cn`: 节能减排措施
- `category`: E
- `indicator_type`: qualitative
- `value_type`: boolean_or_text
- `preferred_source`: main_text_rag
- `unit_type`: text
- `unit_required`: False
- `year_required`: False
- `aliases`: ["节能减排措施", "节能措施", "减排措施", "降碳措施", "节能降耗"]
- `required_any`: ["节能", "减排", "降碳"]
- `forbidden_any`: ["指标索引", "内容索引", "GRI", "目录"]
- `unit_examples`: []

### 47. `water_management_measures`

- `name_cn`: 水资源管理措施
- `category`: E
- `indicator_type`: qualitative
- `value_type`: boolean_or_text
- `preferred_source`: main_text_rag
- `unit_type`: text
- `unit_required`: False
- `year_required`: False
- `aliases`: ["水资源管理", "节水措施", "用水管理", "水资源保护"]
- `required_any`: ["水", "节水", "用水"]
- `forbidden_any`: ["指标索引", "内容索引", "GRI", "目录"]
- `unit_examples`: []

### 48. `waste_management_measures`

- `name_cn`: 废弃物管理措施
- `category`: E
- `indicator_type`: qualitative
- `value_type`: boolean_or_text
- `preferred_source`: main_text_rag
- `unit_type`: text
- `unit_required`: False
- `year_required`: False
- `aliases`: ["废弃物管理", "固体废弃物管理", "危险废弃物管理", "废物处置"]
- `required_any`: ["废弃物", "废物", "危废"]
- `forbidden_any`: ["指标索引", "内容索引", "GRI", "目录"]
- `unit_examples`: []

### 49. `employee_rights_policy`

- `name_cn`: 员工权益保障政策
- `category`: S
- `indicator_type`: qualitative
- `value_type`: boolean_or_text
- `preferred_source`: main_text_rag
- `unit_type`: text
- `unit_required`: False
- `year_required`: False
- `aliases`: ["员工权益保障", "员工权益保护", "劳动权益", "雇员权益", "员工关怀"]
- `required_any`: ["员工", "权益"]
- `forbidden_any`: ["指标索引", "内容索引", "GRI", "目录"]
- `unit_examples`: []

### 50. `occupational_health_safety_system`

- `name_cn`: 职业健康安全管理体系
- `category`: S
- `indicator_type`: qualitative
- `value_type`: boolean_or_text
- `preferred_source`: main_text_rag
- `unit_type`: text
- `unit_required`: False
- `year_required`: False
- `aliases`: ["职业健康安全管理体系", "职业健康安全", "安全生产管理体系", "EHS管理"]
- `required_any`: ["职业健康", "安全"]
- `forbidden_any`: ["指标索引", "内容索引", "GRI", "目录"]
- `unit_examples`: []

### 51. `employee_training_development`

- `name_cn`: 员工培训与发展机制
- `category`: S
- `indicator_type`: qualitative
- `value_type`: boolean_or_text
- `preferred_source`: main_text_rag
- `unit_type`: text
- `unit_required`: False
- `year_required`: False
- `aliases`: ["员工培训与发展", "人才培养机制", "员工发展", "培训体系", "职业发展"]
- `required_any`: ["员工", "培训", "发展"]
- `forbidden_any`: ["指标索引", "内容索引", "GRI", "目录"]
- `unit_examples`: []

### 52. `diversity_equal_opportunity`

- `name_cn`: 多元化与平等雇佣政策
- `category`: S
- `indicator_type`: qualitative
- `value_type`: boolean_or_text
- `preferred_source`: main_text_rag
- `unit_type`: text
- `unit_required`: False
- `year_required`: False
- `aliases`: ["多元化与平等", "平等雇佣", "多元化雇佣", "反歧视", "机会平等"]
- `required_any`: ["多元", "平等", "雇佣"]
- `forbidden_any`: ["指标索引", "内容索引", "GRI", "目录"]
- `unit_examples`: []

### 53. `supplier_esg_assessment`

- `name_cn`: 供应商ESG管理机制
- `category`: S
- `indicator_type`: qualitative
- `value_type`: boolean_or_text
- `preferred_source`: main_text_rag
- `unit_type`: text
- `unit_required`: False
- `year_required`: False
- `aliases`: ["供应商ESG管理", "供应商社会责任", "供应商可持续发展管理", "供应商评估", "责任采购"]
- `required_any`: ["供应商", "ESG", "可持续", "社会责任"]
- `forbidden_any`: ["指标索引", "内容索引", "GRI", "目录"]
- `unit_examples`: []

### 54. `data_security_privacy`

- `name_cn`: 数据安全与隐私保护机制
- `category`: S
- `indicator_type`: qualitative
- `value_type`: boolean_or_text
- `preferred_source`: main_text_rag
- `unit_type`: text
- `unit_required`: False
- `year_required`: False
- `aliases`: ["数据安全", "隐私保护", "信息安全", "客户隐私", "个人信息保护"]
- `required_any`: ["数据安全", "隐私", "信息安全", "个人信息"]
- `forbidden_any`: ["指标索引", "内容索引", "GRI", "目录"]
- `unit_examples`: []

### 55. `board_esg_oversight`

- `name_cn`: 董事会ESG监督机制
- `category`: G
- `indicator_type`: qualitative
- `value_type`: boolean_or_text
- `preferred_source`: main_text_rag
- `unit_type`: text
- `unit_required`: False
- `year_required`: False
- `aliases`: ["董事会ESG监督", "董事会可持续发展监督", "董事会监督ESG", "董事会负责ESG"]
- `required_any`: ["董事会", "ESG"]
- `forbidden_any`: ["指标索引", "内容索引", "GRI", "目录"]
- `unit_examples`: []

### 56. `esg_committee`

- `name_cn`: ESG治理架构或委员会
- `category`: G
- `indicator_type`: qualitative
- `value_type`: boolean_or_text
- `preferred_source`: main_text_rag
- `unit_type`: text
- `unit_required`: False
- `year_required`: False
- `aliases`: ["ESG委员会", "可持续发展委员会", "ESG工作小组", "ESG治理架构"]
- `required_any`: ["ESG", "委员会", "工作小组", "治理架构"]
- `forbidden_any`: ["指标索引", "内容索引", "GRI", "目录"]
- `unit_examples`: []

### 57. `anti_corruption_policy`

- `name_cn`: 反腐败政策
- `category`: G
- `indicator_type`: qualitative
- `value_type`: boolean_or_text
- `preferred_source`: main_text_rag
- `unit_type`: text
- `unit_required`: False
- `year_required`: False
- `aliases`: ["反腐败政策", "反贪污政策", "反舞弊制度", "廉洁从业制度", "商业道德政策"]
- `required_any`: ["反腐败", "反贪污", "反舞弊", "廉洁"]
- `forbidden_any`: ["指标索引", "内容索引", "GRI", "目录"]
- `unit_examples`: []

### 58. `whistleblowing_mechanism`

- `name_cn`: 举报机制与举报人保护
- `category`: G
- `indicator_type`: qualitative
- `value_type`: boolean_or_text
- `preferred_source`: main_text_rag
- `unit_type`: text
- `unit_required`: False
- `year_required`: False
- `aliases`: ["举报机制", "举报人保护", "投诉举报渠道", " whistleblowing", "举报渠道"]
- `required_any`: ["举报", "投诉", "保护"]
- `forbidden_any`: ["指标索引", "内容索引", "GRI", "目录"]
- `unit_examples`: []

### 59. `business_ethics_training`

- `name_cn`: 商业道德培训机制
- `category`: G
- `indicator_type`: qualitative
- `value_type`: boolean_or_text
- `preferred_source`: main_text_rag
- `unit_type`: text
- `unit_required`: False
- `year_required`: False
- `aliases`: ["商业道德培训", "反腐败培训", "廉洁培训", "合规培训", "反舞弊培训"]
- `required_any`: ["培训", "廉洁", "反腐败", "商业道德"]
- `forbidden_any`: ["指标索引", "内容索引", "GRI", "目录"]
- `unit_examples`: []

### 60. `investor_communication`

- `name_cn`: 信息披露与投资者沟通机制
- `category`: G
- `indicator_type`: qualitative
- `value_type`: boolean_or_text
- `preferred_source`: main_text_rag
- `unit_type`: text
- `unit_required`: False
- `year_required`: False
- `aliases`: ["信息披露", "投资者沟通", "投资者关系", "股东沟通", "业绩说明会"]
- `required_any`: ["信息披露", "投资者", "沟通"]
- `forbidden_any`: ["指标索引", "内容索引", "GRI", "目录"]
- `unit_examples`: []
