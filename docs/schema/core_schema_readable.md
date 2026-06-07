# Core Schema Readable Export

## Summary

- Total: 68
- Quantitative: 63
- Qualitative: 5
- E: 26
- S: 27
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
- `aliases`: ["温室气体排放总量", "温室气体总排放量", "碳排放总量", "温室气体排放量"]
- `required_any`: ["温室气体排放总量", "温室气体总排放量", "碳排放总量", "温室气体排放量"]
- `forbidden_any`: ["范围一", "范围1", "范围 1", "scope1", "scope 1", "直接温室气体", "范围二", "范围2", "范围 2", "scope2", "scope 2", "间接温室气体", "范围三", "范围3", "范围 3", "scope3", "scope 3", "排放强度", "密度"]
- `unit_examples`: ["吨CO2e", "吨二氧化碳当量", "万吨CO2e"]

### 2. `scope_1_emissions`

- `name_cn`: 范围一温室气体排放量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: ghg
- `unit_required`: True
- `year_required`: True
- `aliases`: ["范围一排放", "范围一温室气体排放", "直接温室气体排放", "直接温室气体排放量", "直接温室气体排放总量"]
- `required_any`: ["范围一", "范围1", "范围 1", "scope1", "scope 1", "直接温室气体"]
- `forbidden_any`: ["范围二", "Scope2", "间接温室气体", "排放强度"]
- `unit_examples`: ["吨CO2e", "吨二氧化碳当量"]

### 3. `scope_2_emissions`

- `name_cn`: 范围二温室气体排放量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: ghg
- `unit_required`: True
- `year_required`: True
- `aliases`: ["范围二排放", "范围二温室气体排放", "间接温室气体排放", "间接温室气体排放量", "间接温室气体排放总量"]
- `required_any`: ["范围二", "范围2", "范围 2", "scope2", "scope 2", "间接温室气体"]
- `forbidden_any`: ["范围一", "Scope1", "直接温室气体", "排放强度"]
- `unit_examples`: ["吨CO2e", "吨二氧化碳当量"]

### 4. `scope_3_emissions`

- `name_cn`: 范围三温室气体排放量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: ghg
- `unit_required`: True
- `year_required`: True
- `aliases`: ["范围三排放", "范围三温室气体排放", "范围三温室气体排放量", "范围 3 温室气体排放量", "范围3温室气体排放量", "Scope 3 排放", "Scope3 排放"]
- `required_any`: ["范围三", "范围3", "范围 3", "scope3", "scope 3"]
- `forbidden_any`: ["范围一", "范围1", "范围二", "范围2", "排放强度", "密度", "上游", "下游", "上游排放", "下游排放", "外购商品和服务", "员工通勤", "商务旅行", "差旅", "资本货物", "燃料和能源相关活动"]
- `unit_examples`: ["吨CO2e", "吨二氧化碳当量", "万吨二氧化碳当量"]

### 5. `ghg_emissions_intensity`

- `name_cn`: 温室气体排放强度
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: intensity
- `unit_required`: True
- `year_required`: True
- `aliases`: ["温室气体排放强度", "碳排放强度", "单位收入碳排放", "单位产值碳排放", "温室气体排放密度", "碳排放密度", "单位营收温室气体排放"]
- `required_any`: ["排放强度", "碳排放强度", "单位收入碳排放", "单位产值碳排放", "温室气体排放密度", "碳排放密度", "单位营收温室气体排放"]
- `forbidden_any`: ["排放总量"]
- `unit_examples`: ["吨CO2e/万元", "吨CO2e/吨产品"]

### 6. `energy_consumption_total`

- `name_cn`: 能源消耗总量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: energy
- `unit_required`: True
- `year_required`: True
- `aliases`: ["能源消耗总量", "综合能耗", "总能源消耗", "综合能源消耗量", "能源消耗量"]
- `required_any`: ["能源消耗总量", "综合能耗", "总能源消耗", "综合能源消耗量", "能源消耗量"]
- `forbidden_any`: ["强度", "单位", "电使用量", "用电量", "耗电量", "外购电力"]
- `unit_examples`: ["吨标准煤", "吨标煤", "MWh", "万千瓦时"]

### 7. `energy_consumption_intensity`

- `name_cn`: 能源消耗强度
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: intensity
- `unit_required`: True
- `year_required`: True
- `aliases`: ["能源消耗强度", "综合能耗强度", "能耗强度", "单位收入能耗", "单位产值能耗", "能源消耗密度", "能源使用密度", "单位营收能源消耗"]
- `required_any`: ["强度", "单位收入能耗", "单位产值能耗", "能耗强度", "能源消耗密度", "能源使用密度", "单位营收能源消耗"]
- `forbidden_any`: ["能源消耗总量", "综合能耗总量"]
- `unit_examples`: ["吨标准煤/万元", "吨标煤/万元"]

### 8. `electricity_consumption`

- `name_cn`: 电力消耗量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: energy
- `unit_required`: True
- `year_required`: True
- `aliases`: ["电力消耗", "用电量", "耗电量", "外购电力", "电使用量", "营业办公消耗电力", "电力使用量", "电力"]
- `required_any`: ["电力消耗", "用电量", "耗电量", "外购电力", "电使用量", "营业办公消耗电力", "电力使用量", "电力"]
- `forbidden_any`: ["光伏", "新能源发电量", "清洁能源", "可再生能源", "绿色电力"]
- `unit_examples`: ["千瓦时", "万千瓦时", "MWh", "兆瓦时"]

### 9. `renewable_energy_consumption`

- `name_cn`: 可再生能源使用量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: energy
- `unit_required`: True
- `year_required`: True
- `aliases`: ["可再生能源使用量", "可再生能源消耗量", "绿色电力", "清洁能源使用量", "光伏等新能源发电量", "新能源发电量"]
- `required_any`: ["可再生能源", "绿色电力", "清洁能源", "光伏", "新能源发电"]
- `forbidden_any`: ["化石能源", "煤炭", "天然气"]
- `unit_examples`: ["千瓦时", "万千瓦时", "吨标准煤"]

### 10. `natural_gas_consumption`

- `name_cn`: 天然气消耗量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: gas
- `unit_required`: True
- `year_required`: True
- `aliases`: ["天然气消耗量", "天然气使用量", "天然气用量"]
- `required_any`: ["天然气"]
- `forbidden_any`: []
- `unit_examples`: ["立方米", "万立方米"]

### 11. `coal_consumption`

- `name_cn`: 煤炭消耗量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: mass
- `unit_required`: True
- `year_required`: True
- `aliases`: ["煤炭消耗量", "煤耗", "原煤消耗量", "煤使用量"]
- `required_any`: ["煤炭", "煤耗", "原煤"]
- `forbidden_any`: ["替代化石能源"]
- `unit_examples`: ["吨", "万吨"]

### 12. `water_consumption`

- `name_cn`: 水资源消耗量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: water
- `unit_required`: True
- `year_required`: True
- `aliases`: ["总耗水量", "用水量", "取水量", "耗水量", "新鲜水用量", "营业办公耗水", "水资源消耗量"]
- `required_any`: ["总耗水量", "用水量", "取水量", "耗水量", "新鲜水用量", "营业办公耗水", "水资源消耗量"]
- `forbidden_any`: ["废水", "循环", "回用", "节水", "强度", "密度"]
- `unit_examples`: ["吨", "万吨", "立方米", "万立方米"]

### 13. `water_consumption_intensity`

- `name_cn`: 水资源消耗强度
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: intensity
- `unit_required`: True
- `year_required`: True
- `aliases`: ["水资源消耗强度", "用水强度", "耗水强度", "单位收入耗水", "单位产值耗水", "水资源使用强度", "水资源使用密度", "单位营收水资源使用量"]
- `required_any`: ["用水强度", "耗水强度", "水资源消耗强度", "单位收入耗水", "单位产值耗水", "水资源使用强度", "水资源使用密度", "单位营收水资源使用量"]
- `forbidden_any`: ["总耗水量", "总用水量"]
- `unit_examples`: ["吨/万元", "立方米/万元"]

### 14. `recycled_water_volume`

- `name_cn`: 循环水或回用水量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: water
- `unit_required`: True
- `year_required`: True
- `aliases`: ["循环水使用量", "循环用水量", "循环水量", "回用水量", "中水回用量", "再生水使用量"]
- `required_any`: ["循环水", "循环用水", "回用水", "中水回用", "再生水"]
- `forbidden_any`: ["总耗水量", "废水排放量"]
- `unit_examples`: ["吨", "万吨", "立方米", "万立方米"]

### 15. `wastewater_discharge`

- `name_cn`: 废水排放量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: water
- `unit_required`: True
- `year_required`: True
- `aliases`: ["废水排放量", "污水排放量"]
- `required_any`: ["废水排放", "污水排放"]
- `forbidden_any`: ["废水处理", "废水达标率", "循环水", "回用水"]
- `unit_examples`: ["吨", "万吨", "立方米", "万立方米"]

### 16. `cod_emissions`

- `name_cn`: 化学需氧量排放量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: mass
- `unit_required`: True
- `year_required`: True
- `aliases`: ["化学需氧量排放量", "COD排放量", "COD", "化学需氧量"]
- `required_any`: ["化学需氧量", "COD"]
- `forbidden_any`: []
- `unit_examples`: ["吨", "千克"]

### 17. `ammonia_nitrogen_emissions`

- `name_cn`: 氨氮排放量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: mass
- `unit_required`: True
- `year_required`: True
- `aliases`: ["氨氮排放量", "氨氮"]
- `required_any`: ["氨氮"]
- `forbidden_any`: []
- `unit_examples`: ["吨", "千克"]

### 18. `so2_emissions`

- `name_cn`: 二氧化硫排放量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: mass
- `unit_required`: True
- `year_required`: True
- `aliases`: ["二氧化硫排放量", "SO2排放量", "硫氧化物排放量", "硫氧化物", "氧化硫", "SOX", "SOx"]
- `required_any`: ["二氧化硫", "SO2", "硫氧化物", "氧化硫", "SOx", "SOX"]
- `forbidden_any`: ["氮氧化物", "NOx", "NOX", "削减", "削减量", "减排", "减排量", "减少量"]
- `unit_examples`: ["吨", "千克"]

### 19. `nox_emissions`

- `name_cn`: 氮氧化物排放量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: mass
- `unit_required`: True
- `year_required`: True
- `aliases`: ["氮氧化物排放量", "NOx排放量", "NOX排放量", "氮氧化物"]
- `required_any`: ["氮氧化物", "NOx", "NOX"]
- `forbidden_any`: ["二氧化硫", "SO2", "硫氧化物", "削减", "削减量", "减排", "减排量", "减少量"]
- `unit_examples`: ["吨", "千克"]

### 20. `particulate_matter_emissions`

- `name_cn`: 颗粒物排放量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: mass
- `unit_required`: True
- `year_required`: True
- `aliases`: ["颗粒物排放量", "烟尘排放量", "颗粒物", "烟尘"]
- `required_any`: ["颗粒物", "烟尘"]
- `forbidden_any`: ["削减", "削减量", "减排", "减排量", "减少量"]
- `unit_examples`: ["吨", "千克"]

### 21. `hazardous_waste`

- `name_cn`: 危险废弃物产生或排放量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: waste
- `unit_required`: True
- `year_required`: True
- `aliases`: ["危险废物", "危险废弃物", "有害废弃物", "危废", "危险废弃物排放量", "危险废弃物产生量"]
- `required_any`: ["危险废物", "危险废弃物", "有害废弃物", "危废"]
- `forbidden_any`: ["一般固体废弃物", "无害废弃物", "非危险废物", "密度", "强度", "单位营收", "单位收入", "每万元", "每亿元", "循环利用", "回收利用", "再利用", "利用量", "回收量"]
- `unit_examples`: ["吨", "万吨"]

### 22. `non_hazardous_waste`

- `name_cn`: 无害废弃物产生或排放量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: waste
- `unit_required`: True
- `year_required`: True
- `aliases`: ["一般固体废弃物", "无害废弃物", "非危险废物", "一般废弃物", "无害废弃物产生量"]
- `required_any`: ["一般固体废弃物", "无害废弃物", "非危险废物", "一般废弃物"]
- `forbidden_any`: ["危险废物", "危险废弃物", "有害废弃物", "危废", "密度", "强度", "单位营收", "单位收入", "每万元", "每亿元", "循环利用", "回收利用", "再利用", "利用量", "回收量"]
- `unit_examples`: ["吨", "万吨"]

### 23. `total_waste`

- `name_cn`: 废弃物总量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: waste
- `unit_required`: True
- `year_required`: True
- `aliases`: ["废弃物产生总量", "固体废弃物总量", "废弃物总量", "废弃物排放总量"]
- `required_any`: ["废弃物总量", "废弃物产生总量", "固体废弃物总量", "废弃物排放总量"]
- `forbidden_any`: ["危险废物", "危险废弃物", "一般固体废弃物", "无害废弃物", "回收利用", "循环利用", "再利用", "利用量", "回收量"]
- `unit_examples`: ["吨", "万吨"]

### 24. `waste_recycling_rate`

- `name_cn`: 废弃物回收利用率
- `category`: E
- `indicator_type`: quantitative
- `value_type`: percentage
- `preferred_source`: appendix_table
- `unit_type`: percentage
- `unit_required`: True
- `year_required`: True
- `aliases`: ["废弃物回收利用率", "回收利用率", "回收率", "废弃物回收率"]
- `required_any`: ["回收利用率", "回收率"]
- `forbidden_any`: []
- `unit_examples`: ["%"]

### 25. `environmental_investment`

- `name_cn`: 环保投入金额
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: money
- `unit_required`: True
- `year_required`: True
- `aliases`: ["环保投入", "环境保护投入", "环保投资", "环保总投资", "环境治理投入金额", "环保总投入"]
- `required_any`: ["环保投入", "环境保护投入", "环保投资", "环保总投资", "环境治理投入", "环保总投入"]
- `forbidden_any`: ["培训投入", "研发投入"]
- `unit_examples`: ["万元", "亿元"]

### 26. `environmental_violation_cases`

- `name_cn`: 环境违规或处罚事件数量
- `category`: E
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["环境违规事件数量", "环境处罚次数", "环保处罚", "环境违法事件", "因环境事件受到生态环境等有关部门重大行政处罚的处罚事件", "环境行政处罚事件"]
- `required_any`: ["环境违规", "环境处罚", "环保处罚", "环境违法", "重大行政处罚", "生态环境"]
- `forbidden_any`: ["培训", "演练"]
- `unit_examples`: ["次", "件", "宗"]

### 27. `total_employees`

- `name_cn`: 员工总数
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: person_count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["员工总数", "员工总人数", "雇员总数", "人员总数", "员工人数", "总员工数"]
- `required_any`: ["员工总数", "员工总人数", "雇员总数", "人员总数", "员工人数", "总员工数"]
- `forbidden_any`: ["男性", "女性", "少数民族", "30岁", "40岁", "50岁", "培训", "反腐败", "反贪污", "反商业贿赂", "参加", "参与", "受训", "按性别", "按年龄"]
- `unit_examples`: ["人", "名"]

### 28. `male_employees`

- `name_cn`: 男性员工人数
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: person_count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["男性员工人数", "男性员工数量", "男员工人数", "男性员工", "男性"]
- `required_any`: ["男性员工", "男员工", "男性"]
- `forbidden_any`: ["比例", "占比", "%", "女性", "管理层"]
- `unit_examples`: ["人", "名"]

### 29. `female_employees`

- `name_cn`: 女性员工人数
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: person_count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["女性员工人数", "女性员工数量", "女员工人数", "女性员工", "女性"]
- `required_any`: ["女性员工", "女员工", "女性"]
- `forbidden_any`: ["比例", "占比", "%", "男性", "管理层", "女性管理"]
- `unit_examples`: ["人", "名"]

### 30. `female_employee_ratio`

- `name_cn`: 女性员工比例
- `category`: S
- `indicator_type`: quantitative
- `value_type`: percentage
- `preferred_source`: appendix_table
- `unit_type`: percentage
- `unit_required`: True
- `year_required`: True
- `aliases`: ["女性员工比例", "女性员工占比", "女性雇员比例"]
- `required_any`: ["女性员工比例", "女性员工占比", "女性雇员比例"]
- `forbidden_any`: ["女性管理层", "女性管理人员", "中层管理层"]
- `unit_examples`: ["%"]

### 31. `female_management_ratio`

- `name_cn`: 女性管理层比例
- `category`: S
- `indicator_type`: quantitative
- `value_type`: percentage
- `preferred_source`: appendix_table
- `unit_type`: percentage
- `unit_required`: True
- `year_required`: True
- `aliases`: ["女性管理层比例", "女性管理人员占比", "管理人员中女性人数比例", "中层管理层中的女性员工比例", "女性管理者比例"]
- `required_any`: ["女性管理层", "女性管理人员", "管理人员中女性", "中层管理层中的女性", "女性管理者"]
- `forbidden_any`: ["女性员工人数", "女性员工数量"]
- `unit_examples`: ["%"]

### 32. `minority_employees`

- `name_cn`: 少数民族员工人数
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: person_count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["少数民族员工人数", "少数民族员工数量", "少数民族人数", "少数民族"]
- `required_any`: ["少数民族"]
- `forbidden_any`: ["非少数民族"]
- `unit_examples`: ["人", "名"]

### 33. `employees_under_30`

- `name_cn`: 30岁以下员工人数
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: person_count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["30岁以下员工人数", "30岁以下", "30周岁以下", "30岁及30岁以下", "30岁以下（不含30岁）", "<30岁", "小于30岁"]
- `required_any`: ["30岁以下", "30周岁以下", "30岁及30岁以下", "<30岁", "小于30岁"]
- `forbidden_any`: ["30-40", "30至40", "40-50", "40至50", "50岁"]
- `unit_examples`: ["人", "名"]

### 34. `employees_30_to_50`

- `name_cn`: 30至50岁员工人数
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: person_count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["30至50岁员工人数", "30-50岁员工人数", "30岁至50岁员工人数", "30岁-50岁", "30岁至50岁", "大于30岁且小于50岁"]
- `required_any`: ["30至50", "30-50", "30岁至50", "30岁-50岁", "30岁至50岁", "大于30岁且小于50岁"]
- `forbidden_any`: ["30岁以下", "50岁以上", "50岁及以上", "30-40", "30至40", "40-50", "40至50"]
- `unit_examples`: ["人", "名"]

### 35. `employees_over_50`

- `name_cn`: 50岁以上员工人数
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: person_count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["50岁以上员工人数", "50岁及以上", "50周岁以上", "50岁及50岁以上", ">50岁", "大于50岁"]
- `required_any`: ["50岁以上", "50岁及以上", "50周岁以上", "50岁及50岁以上", ">50岁", "大于50岁"]
- `forbidden_any`: ["30岁以下", "30-40", "30至40", "40-50", "40至50"]
- `unit_examples`: ["人", "名"]

### 36. `employee_turnover_rate`

- `name_cn`: 员工流失率
- `category`: S
- `indicator_type`: quantitative
- `value_type`: percentage
- `preferred_source`: appendix_table
- `unit_type`: percentage
- `unit_required`: True
- `year_required`: True
- `aliases`: ["员工流失率", "离职率", "员工离职率"]
- `required_any`: ["员工流失率", "离职率", "员工离职率"]
- `forbidden_any`: ["人数", "数量"]
- `unit_examples`: ["%"]

### 37. `training_total_hours`

- `name_cn`: 员工培训总时长
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: hour
- `unit_required`: True
- `year_required`: True
- `aliases`: ["员工培训总时长", "培训总小时数", "培训总时数", "员工受训总时数", "员工培训总学时", "培训总学时", "全体员工培训总学时", "全体员工总受训时长"]
- `required_any`: ["培训总时长", "培训总小时", "培训总时数", "员工受训总时数", "员工培训总学时", "培训总学时", "全体员工培训总学时", "全体员工总受训时长"]
- `forbidden_any`: ["人均", "平均", "志愿服务", "公益慈善", "反腐败", "反贪污", "反商业贿赂", "安全生产", "安全培训", "环保培训", "质量培训"]
- `unit_examples`: ["小时", "学时"]

### 38. `training_hours_per_employee`

- `name_cn`: 人均培训时长
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: hour
- `unit_required`: True
- `year_required`: True
- `aliases`: ["人均培训时长", "人均培训小时数", "员工平均培训时数", "员工受训平均时数", "平均培训时数", "每名员工培训时数"]
- `required_any`: ["人均培训", "平均培训时数", "员工平均培训时数", "员工受训平均时数", "每名员工培训时数"]
- `forbidden_any`: ["高层", "中层", "基层", "新员工", "新入职", "男性", "女性", "反腐败", "反贪污", "反商业贿赂", "安全生产", "安全培训", "培训总时长"]
- `unit_examples`: ["小时", "小时/人"]

### 39. `training_coverage_rate`

- `name_cn`: 员工培训覆盖率
- `category`: S
- `indicator_type`: quantitative
- `value_type`: percentage
- `preferred_source`: appendix_table
- `unit_type`: percentage
- `unit_required`: True
- `year_required`: True
- `aliases`: ["员工培训覆盖率", "培训覆盖率", "员工受训覆盖率", "受训员工比例", "参加培训的员工覆盖率"]
- `required_any`: ["员工培训覆盖率", "培训覆盖率", "员工受训覆盖率", "受训员工比例", "参加培训的员工覆盖率"]
- `forbidden_any`: ["反腐败", "反贪污", "反商业贿赂", "安全生产", "健康档案", "工伤保险", "采购", "供应商", "专项培训", "环保培训", "安全培训", "质量培训"]
- `unit_examples`: ["%"]

### 40. `training_expense`

- `name_cn`: 培训投入金额
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: money
- `unit_required`: True
- `year_required`: True
- `aliases`: ["培训投入", "培训费用", "培训支出费用", "培训费用总支出", "员工培训投入金额"]
- `required_any`: ["培训投入", "培训费用", "培训支出"]
- `forbidden_any`: ["培训总时长", "人均培训", "志愿服务"]
- `unit_examples`: ["万元", "元"]

### 41. `trained_employees_count`

- `name_cn`: 受训员工人数或人次
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: person_time
- `unit_required`: True
- `year_required`: True
- `aliases`: ["参加培训的员工总数", "受训员工人数", "参加培训员工人数", "培训总人次", "受训员工人次", "员工受训总人次", "全体员工受训总人次", "累计参加培训学员人数"]
- `required_any`: ["参加培训", "受训员工", "培训总人次", "员工受训总人次", "全体员工受训总人次", "累计参加培训学员人数"]
- `forbidden_any`: ["培训覆盖率", "人均培训", "培训费用", "培训总时长", "小时", "学时", "反腐败", "反贪污", "反商业贿赂", "安全生产", "安全培训", "环保", "环境保护", "环境合规"]
- `unit_examples`: ["人", "人次"]

### 42. `work_injury_rate`

- `name_cn`: 工伤率
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number_or_percentage
- `preferred_source`: appendix_table
- `unit_type`: percentage_or_rate
- `unit_required`: True
- `year_required`: True
- `aliases`: ["工伤率", "工伤事故率"]
- `required_any`: ["工伤率", "工伤事故率"]
- `forbidden_any`: ["因工死亡", "工亡", "损失工作日", "损失工时", "总工伤人数", "安全事故数"]
- `unit_examples`: ["%", "次/百万工时"]

### 43. `work_related_fatalities`

- `name_cn`: 因工死亡人数
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: person_count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["因工死亡人数", "工亡人数", "工作相关死亡人数", "因工作关系死亡总人数", "因工作关系死亡人数"]
- `required_any`: ["因工死亡", "工亡", "工作相关死亡", "因工作关系死亡"]
- `forbidden_any`: ["工伤率", "损失工作日", "损失工时"]
- `unit_examples`: ["人", "次"]

### 44. `lost_workdays_due_to_injury`

- `name_cn`: 因工伤损失工作日数
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: day_or_hour
- `unit_required`: True
- `year_required`: True
- `aliases`: ["因工伤损失工作日数", "因工伤损失工时", "损失工作日", "损失工时", "员工因工伤损失总天数", "工伤损失总天数"]
- `required_any`: ["损失工作日", "损失工时", "员工因工伤损失总天数", "工伤损失总天数"]
- `forbidden_any`: ["因工死亡", "工亡"]
- `unit_examples`: ["天", "小时"]

### 45. `social_insurance_coverage_rate`

- `name_cn`: 社会保险覆盖率
- `category`: S
- `indicator_type`: quantitative
- `value_type`: percentage
- `preferred_source`: appendix_table
- `unit_type`: percentage
- `unit_required`: True
- `year_required`: True
- `aliases`: ["社会保险覆盖率", "社保覆盖率", "工伤保险人员覆盖率", "工伤保险覆盖率"]
- `required_any`: ["社会保险覆盖率", "社保覆盖率", "工伤保险人员覆盖率", "工伤保险覆盖率"]
- `forbidden_any`: ["培训覆盖率", "健康档案"]
- `unit_examples`: ["%"]

### 46. `employee_health_record_coverage_rate`

- `name_cn`: 员工健康档案或体检覆盖率
- `category`: S
- `indicator_type`: quantitative
- `value_type`: percentage
- `preferred_source`: appendix_table
- `unit_type`: percentage
- `unit_required`: True
- `year_required`: True
- `aliases`: ["员工健康档案覆盖率", "职业健康档案覆盖率", "健康档案覆盖率", "员工体检覆盖率", "体检覆盖率"]
- `required_any`: ["健康档案覆盖率", "职业健康档案覆盖率", "员工体检覆盖率", "体检覆盖率"]
- `forbidden_any`: ["培训覆盖率", "社保覆盖率", "社会保险"]
- `unit_examples`: ["%"]

### 47. `r_and_d_investment`

- `name_cn`: 研发投入金额
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: money
- `unit_required`: True
- `year_required`: True
- `aliases`: ["研发投入", "科技研发投入", "研发费用", "研发资金投入"]
- `required_any`: ["研发投入", "科技研发投入", "研发费用", "研发资金"]
- `forbidden_any`: ["研发人员", "研发团队", "研发队伍", "比例", "占比"]
- `unit_examples`: ["万元", "亿元"]

### 48. `r_and_d_employees`

- `name_cn`: 研发人员数量
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: person_count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["研发人员数量", "研发队伍人数", "研发员工人数", "研发团队总人数", "研发团队人数", "研发人员总数"]
- `required_any`: ["研发人员", "研发团队", "研发队伍", "研发员工"]
- `forbidden_any`: ["研发投入", "研发费用", "研发资金", "比例", "占比", "%"]
- `unit_examples`: ["人", "名"]

### 49. `authorized_patents_new`

- `name_cn`: 当年新增授权专利数量
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["新增授权专利数量", "新增授权专利数", "当年授权专利数量", "报告当年授权的专利总数", "获得科技发明专利授权证书"]
- `required_any`: ["新增授权专利", "当年授权专利", "报告当年授权", "获得科技发明专利授权证书"]
- `forbidden_any`: ["累计", "有效期内", "有效专利拥有量"]
- `unit_examples`: ["项", "件", "个"]

### 50. `authorized_patents_total`

- `name_cn`: 累计授权专利数量
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["累计拥有授权专利数量", "累计授权专利数量", "有效专利拥有量", "授权且有效专利拥有量", "授权专利累计数", "授权专利累计数（有效期内的专利数）", "截至报告期末有效专利数量", "有效专利数量", "报告期末有效专利数量", "有效期内的专利数", "报告期内有效专利数"]
- `required_any`: ["累计授权专利", "授权专利累计", "有效期内的专利", "有效专利拥有量", "授权且有效专利", "报告期内有效专利数", "截至报告期末有效专利数量", "有效专利数量", "报告期末有效专利数量"]
- `forbidden_any`: ["新增", "当年", "申请"]
- `unit_examples`: ["项", "件", "个"]

### 51. `customer_complaints`

- `name_cn`: 客户投诉数量
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["客户投诉数量", "客户投诉案件数量", "客户投诉次数", "投诉数量"]
- `required_any`: ["客户投诉", "投诉数量", "投诉次数"]
- `forbidden_any`: ["投诉解决率", "举报", "申诉", "举报机制"]
- `unit_examples`: ["件", "起", "次"]

### 52. `board_size`

- `name_cn`: 董事会人数
- `category`: G
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: person_count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["董事会人数", "董事人数"]
- `required_any`: ["董事会人数", "董事人数", "董事会成员", "董事会成员的人数"]
- `forbidden_any`: ["培训", "反腐败", "反贪污", "反商业贿赂", "占比", "比例", "百分比", "%", "不兼任", "不兼任高管", "高管职务"]
- `unit_examples`: ["人", "名"]

### 53. `independent_directors`

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
- `forbidden_any`: ["独立董事比例", "独立董事占比", "%"]
- `unit_examples`: ["人", "名"]

### 54. `independent_director_ratio`

- `name_cn`: 独立董事比例
- `category`: G
- `indicator_type`: quantitative
- `value_type`: percentage
- `preferred_source`: appendix_table
- `unit_type`: percentage
- `unit_required`: True
- `year_required`: True
- `aliases`: ["独立董事比例", "独立董事占比"]
- `required_any`: ["独立董事比例", "独立董事占比"]
- `forbidden_any`: ["独立董事人数", "独立董事数量"]
- `unit_examples`: ["%"]

### 55. `female_directors`

- `name_cn`: 女性董事人数
- `category`: G
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: person_count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["女性董事人数", "女性董事数量"]
- `required_any`: ["女性董事人数", "女性董事数量"]
- `forbidden_any`: ["女性董事比例", "女性董事占比", "%"]
- `unit_examples`: ["人", "名"]

### 56. `board_meetings`

- `name_cn`: 董事会会议次数
- `category`: G
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["董事会会议次数", "董事会召开次数", "董事会次数", "董事会会议召开次数"]
- `required_any`: ["董事会会议", "董事会召开"]
- `forbidden_any`: ["股东大会", "监事会", "审议", "议案"]
- `unit_examples`: ["次"]

### 57. `shareholder_meetings`

- `name_cn`: 股东大会会议次数
- `category`: G
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["股东大会召开次数", "股东大会会议次数", "股东大会次数", "股东大会会议召开次数"]
- `required_any`: ["股东大会"]
- `forbidden_any`: ["董事会", "监事会", "审议", "议案"]
- `unit_examples`: ["次"]

### 58. `anti_corruption_training_sessions`

- `name_cn`: 反腐败培训次数
- `category`: G
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["反腐败培训次数", "反贪污培训次数", "廉洁培训次数", "反商业贿赂培训次数"]
- `required_any`: ["反腐败培训", "反贪污培训", "廉洁培训", "反商业贿赂培训"]
- `forbidden_any`: ["参与人数", "培训人数", "培训人次", "培训时数", "培训总时长", "小时", "学时", "%", "百分比"]
- `unit_examples`: ["次", "场次"]

### 59. `anti_corruption_training_participants`

- `name_cn`: 反腐败培训参与人数或人次
- `category`: G
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: person_time
- `unit_required`: True
- `year_required`: True
- `aliases`: ["反腐败培训参与人数", "反腐败培训人次", "反贪污培训人次", "员工反腐败培训人次", "管理人员反腐败培训人次", "参加反商业贿赂及反贪污培训的员工人数", "参加反商业贿赂及反贪污培训的董事及高级管理人员人数"]
- `required_any`: ["反腐败培训", "反贪污培训", "反商业贿赂", "廉洁培训"]
- `forbidden_any`: ["培训次数", "培训时数", "培训总时长", "培训小时", "平均时长", "覆盖率", "百分比", "%", "占比"]
- `unit_examples`: ["人", "人次"]

### 60. `anti_corruption_training_hours`

- `name_cn`: 反腐败培训总时长
- `category`: G
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: hour
- `unit_required`: True
- `year_required`: True
- `aliases`: ["反腐败培训时数", "反腐败培训总时长", "反腐败培训小时数", "反贪污培训时数", "反商业贿赂培训时数", "员工反腐败培训时数", "管理人员反腐败培训时数", "反商业贿赂及反贪污培训总时长", "提供的反商业贿赂及反贪污培训总时长", "向董事及高级管理人员提供的反商业贿赂及反贪污培训总时长"]
- `required_any`: ["反腐败培训", "反贪污培训", "反商业贿赂", "廉洁培训"]
- `forbidden_any`: ["培训次数", "培训人次", "培训人数", "覆盖率", "百分比", "%", "平均"]
- `unit_examples`: ["小时", "学时"]

### 61. `confirmed_corruption_cases`

- `name_cn`: 确认的腐败事件数量
- `category`: G
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["确认的腐败事件数量", "腐败事件数量", "贪腐事件数量", "已确认腐败事件"]
- `required_any`: ["确认", "腐败事件", "贪腐事件"]
- `forbidden_any`: ["培训", "举报"]
- `unit_examples`: ["件", "起", "次"]

### 62. `whistleblowing_cases`

- `name_cn`: 举报案件数量
- `category`: G
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["举报案件数量", "投诉举报案件数量", "申诉案件数量", "举报数量", "反贪污腐败举报事件总数", "举报事件总数"]
- `required_any`: ["举报案件", "投诉举报", "申诉案件", "举报数量", "举报事件"]
- `forbidden_any`: ["客户投诉", "举报机制", "举报渠道"]
- `unit_examples`: ["件", "起", "次"]

### 63. `patent_applications_new`

- `name_cn`: 当年申请专利数量
- `category`: S
- `indicator_type`: quantitative
- `value_type`: number
- `preferred_source`: appendix_table
- `unit_type`: count
- `unit_required`: True
- `year_required`: True
- `aliases`: ["申报专利数", "专利申请数", "专利申请数量", "申请专利数量", "当年申请专利数量", "报告当年申请的专利总数", "新增专利申请数", "报告期内发明专利的申请数", "发明专利申请数"]
- `required_any`: ["申报专利", "专利申请", "申请专利", "专利申请数", "报告当年申请", "报告期内发明专利的申请数", "发明专利的申请数", "发明专利申请数"]
- `forbidden_any`: ["授权", "累计", "有效专利"]
- `unit_examples`: ["项", "件", "个"]

### 64. `board_esg_oversight`

- `name_cn`: 董事会 ESG 监督机制
- `category`: G
- `indicator_type`: qualitative
- `value_type`: boolean_or_text
- `preferred_source`: main_text_rag
- `unit_type`: text
- `unit_required`: False
- `year_required`: False
- `aliases`: ["董事会ESG监督", "董事会可持续发展监督", "董事会审议ESG", "董事会参与ESG管理"]
- `required_any`: ["董事会", "ESG", "可持续发展"]
- `forbidden_any`: ["指标索引", "内容索引", "报告页码", "对应章节", "GRI"]
- `unit_examples`: []

### 65. `esg_committee`

- `name_cn`: ESG 委员会或可持续发展委员会
- `category`: G
- `indicator_type`: qualitative
- `value_type`: boolean_or_text
- `preferred_source`: main_text_rag
- `unit_type`: text
- `unit_required`: False
- `year_required`: False
- `aliases`: ["ESG委员会", "可持续发展委员会", "社会责任委员会", "ESG工作小组"]
- `required_any`: ["ESG委员会", "可持续发展委员会", "社会责任委员会", "ESG工作小组"]
- `forbidden_any`: ["指标索引", "内容索引", "报告页码", "对应章节", "GRI"]
- `unit_examples`: []

### 66. `anti_corruption_policy`

- `name_cn`: 反腐败政策
- `category`: G
- `indicator_type`: qualitative
- `value_type`: boolean_or_text
- `preferred_source`: main_text_rag
- `unit_type`: text
- `unit_required`: False
- `year_required`: False
- `aliases`: ["反腐败政策", "反贪污政策", "反商业贿赂制度", "廉洁从业制度", "商业道德政策"]
- `required_any`: ["反腐败", "反贪污", "反商业贿赂", "廉洁", "商业道德"]
- `forbidden_any`: ["指标索引", "内容索引", "报告页码", "对应章节", "GRI"]
- `unit_examples`: []

### 67. `whistleblowing_mechanism`

- `name_cn`: 举报机制
- `category`: G
- `indicator_type`: qualitative
- `value_type`: boolean_or_text
- `preferred_source`: main_text_rag
- `unit_type`: text
- `unit_required`: False
- `year_required`: False
- `aliases`: ["举报机制", "举报渠道", "投诉机制", "申诉机制", "举报邮箱", "举报热线"]
- `required_any`: ["举报机制", "举报渠道", "投诉机制", "申诉机制", "举报邮箱", "举报热线"]
- `forbidden_any`: ["指标索引", "内容索引", "报告页码", "对应章节", "GRI"]
- `unit_examples`: []

### 68. `supplier_esg_assessment`

- `name_cn`: 供应商 ESG 评估机制
- `category`: S
- `indicator_type`: qualitative
- `value_type`: boolean_or_text
- `preferred_source`: main_text_rag
- `unit_type`: text
- `unit_required`: False
- `year_required`: False
- `aliases`: ["供应商ESG评估", "供应商环境社会评估", "供应商可持续发展评估", "供应商社会责任评估", "供应商审核", "供应商评价"]
- `required_any`: ["供应商", "ESG", "环境社会", "可持续", "社会责任", "审核", "评价"]
- `forbidden_any`: ["指标索引", "内容索引", "报告页码", "对应章节", "GRI"]
- `unit_examples`: []
