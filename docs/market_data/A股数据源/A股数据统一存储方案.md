# A股数据统一存储方案

## 核心原则（重要）

### 1. 数据存储唯一性原则
**数据库按数据存储，不按数据源重复存储**：
- 同一股票的同一交易日数据，数据库中只存储一条记录
- 通过 `symbol + trade_date`（或其他唯一键）判断数据是否存在
- 使用 upsert 操作：存在则更新，不存在则插入
- 每条记录包含 `data_source` 字段标识数据来源，便于追溯

### 2. 数据标准化原则
**以TuShare的标准化数据为存储标准**：
- TuShare返回标准化JSON格式，英文字段名
- 所有数据最终存储时，字段名必须符合TuShare的英文标准
- AkShare的中文字段必须转换为对应的英文字段
- 两个数据源都有的接口，优先使用TuShare，AkShare作为降级

### 3. 字段缺失处理原则
**TuShare有但AkShare没有的字段**：
- 保留该字段在数据库Schema中
- AkShare数据存储时，该字段值为 `null`
- 通过 `data_source` 字段可以区分数据来源

---

## 一、数据分类体系

### 1.1 核心数据类型

根据A股数据源的返回内容，将数据分为以下**6大类**：

| 数据大类 | 说明 | 优先级 | 更新频率 |
|---------|------|--------|----------|
| **基础信息** | 股票列表、上市状态、所属行业 | 高 | 每日 |
| **行情数据** | 日线、分钟线、复权数据 | 高 | 每日/实时 |
| **财务报表** | 三大报表（利润表、资产负债表、现金流量表） | 中 | 每季度 |
| **财务指标** | ROE、负债率、毛利率等计算指标 | 中 | 每季度 |
| **公司行为** | 分红送股、股东变更、IPO | 低 | 不定期 |
| **市场数据** | 龙虎榜、资金流向、融资融券 | 低 | 每日 |

---

## 二、统一数据格式规范

### 2.1 股票基础信息 - stock_info

| 字段名 | 数据类型 | 必填 | 说明 | 数据来源示例 |
|--------|---------|------|------|-------------|
| symbol | String | ✅ | 股票代码，统一格式：`600519.SH` | TuShare: ts_code<br>AkShare: 代码+.交易所 |
| name | String | ✅ | 股票名称 | TuShare: name<br>AkShare: 名称 |
| list_date | String | ✅ | 上市日期，格式：`YYYYMMDD` | TuShare: list_date<br>AkShare: 需转换 |
| market | String | ✅ | 市场类型：主板/科创板/创业板/北交所 | TuShare: market<br>AkShare: 无此字段，需根据代码前缀判断 |
| industry | String | ❌ | 所属行业 | TuShare: industry<br>AkShare: 无 |
| sector | String | ❌ | 所属板块 | TuShare: 无<br>AkShare: 无 |
| exchange | String | ✅ | 交易所代码：SSE/SZSE | TuShare: exchange<br>AkShare: 根据代码判断 |
| status | String | ✅ | 上市状态：L上市/D退市/P暂停 | TuShare: list_status<br>AkShare: 无 |
| data_source | String | ✅ | 数据来源标识：`tushare`/`akshare` | 固定值 |
| updated_at | DateTime | ✅ | 更新时间 | 自动生成 |

**字段映射逻辑**：
- TuShare直接映射，字段名基本一致
- AkShare需要根据股票代码前缀判断市场：
  - 60/688/689开头 → 上海交易所(SSE)
  - 00/30/301开头 → 深圳交易所(SZSE)

---

### 2.2 行情数据 - stock_quotes

| 字段名 | 数据类型 | 必填 | 说明 | TuShare字段 | AkShare字段 |
|--------|---------|------|------|-------------|-------------|
| symbol | String | ✅ | 股票代码 | ts_code | 需添加交易所后缀 |
| trade_date | String | ✅ | 交易日期，YYYYMMDD | trade_date | 日期（需转换格式） |
| open | Decimal | ✅ | 开盘价 | open | 开盘 |
| high | Decimal | ✅ | 最高价 | high | 最高 |
| low | Decimal | ✅ | 最低价 | low | 最低 |
| close | Decimal | ✅ | 收盘价 | close | 收盘 |
| pre_close | Decimal | ✅ | 昨收价 | pre_close | 昨收 |
| volume | Long | ✅ | 成交量（手） | vol | 成交量 |
| amount | Decimal | ✅ | 成交额（元） | amount | 成交额 |
| change | Decimal | ❌ | 涨跌额 | change | 涨跌额 |
| change_pct | Decimal | ❌ | 涨跌幅(%) | pct_chg | 涨跌幅 |
| turnover_rate | Decimal | ❌ | 换手率(%) | 无 | 换手率 |
| adj_factor | Decimal | ❌ | 复权因子 | 需单独获取 | 无 |
| period | String | ✅ | 数据周期：daily/weekly/monthly | freq参数 | period参数 |
| adjust_type | String | ❌ | 复权类型：qfq/hfq/none | adj参数 | adjust参数 |
| data_source | String | ✅ | 数据来源 | 固定`tushare` | 固定`akshare` |
| updated_at | DateTime | ✅ | 更新时间 | 自动生成 | 自动生成 |

**数据格式转换规则**：
1. **日期格式**：TuShare返回 `YYYYMMDD` 字符串，AkShare返回日期对象，需统一转为 `YYYYMMDD` 字符串
2. **股票代码**：AkShare返回纯数字（如 `600519`），需根据市场添加交易所后缀
3. **金额精度**：保留2位小数
4. **成交量**：转换为整数（手）

---

### 2.3 财务报表 - stock_financials

| 字段名 | 数据类型 | 必填 | 说明 |
|--------|---------|------|------|
| **主键字段** |
| symbol | String | ✅ | 股票代码 |
| report_date | String | ✅ | 报告期，格式：`YYYYMMDD` |
| report_type | String | ✅ | 报告类型：Q1/Q2/Q3/Q4/annual |
| data_source | String | ✅ | 数据来源 |

**利润表字段**：
| 字段名 | 说明 | TuShare | AkShare |
|--------|------|---------|---------|
| revenue | 营业收入 | total_revenue | 营业收入 |
| operating_cost | 营业成本 | oper_cost | 营业成本 |
| net_income | 净利润 | n_income | 净利润 |
| basic_eps | 基本每股收益 | basic_eps | 每股收益 |
| operating_revenue | 营业收入 | revenue | 营业收入 |

**资产负债表字段**：
| 字段名 | 说明 | TuShare | AkShare |
|--------|------|---------|---------|
| total_assets | 总资产 | total_assets | 资产总计 |
| total_liabilities | 总负债 | total_liab | 负债合计 |
| equity | 股东权益 | total_hldr_eqy_exc_min_int | 股东权益合计 |
| current_assets | 流动资产 | cur_assets | 流动资产合计 |
| current_liabilities | 流动负债 | cur_liab | 流动负债合计 |

**现金流量表字段**：
| 字段名 | 说明 | TuShare | AkShare |
|--------|------|---------|---------|
| operating_cash_flow | 经营活动现金流 | n_cash_flows_fnc_oper_act | 经营活动现金流量净额 |
| investing_cash_flow | 投资活动现金流 | n_cash_flows_fnc_inv_act | 投资活动现金流量净额 |
| financing_cash_flow | 筹资活动现金流 | n_cash_flows_fnc_fin_act | 筹资活动现金流量净额 |

**字段映射逻辑**：
1. TuShare返回字段为英文缩写，需建立字段映射表
2. AkShare返回中文字段名，需建立中文→英文映射
3. 金额单位统一：转换为万元（需要时进行单位换算）

---

### 2.4 财务指标 - stock_financial_indicators

| 字段名 | 数据类型 | 说明 | TuShare | AkShare |
|--------|---------|------|---------|---------|
| symbol | String | 股票代码 | ts_code | 需转换 |
| report_date | String | 报告期 | end_date | 报告期 |
| roe | Decimal | 净资产收益率(%) | roe | 净资产收益率 |
| roa | Decimal | 总资产净利率(%) | roa | 无 |
| debt_to_assets | Decimal | 资产负债率(%) | debt_to_assets | 无 |
| current_ratio | Decimal | 流动比率 | current_ratio | 无 |
| quick_ratio | Decimal | 速动比率 | quick_ratio | 无 |
| gross_margin | Decimal | 销售毛利率(%) | grossprofit_margin | 无 |
| net_margin | Decimal | 销售净利率(%) | netprofit_margin | 无 |
| data_source | String | 数据来源 | 固定值 | 固定值 |

---

### 2.5 龙虎榜数据 - stock_top_list

| 字段名 | 数据类型 | 必填 | 说明 | TuShare | AkShare |
|--------|---------|------|------|---------|---------|
| symbol | String | ✅ | 股票代码 | ts_code | 代码 |
| trade_date | String | ✅ | 交易日期 | trade_date | 上榜日 |
| name | String | ✅ | 股票名称 | name | 名称 |
| close_price | Decimal | ❌ | 收盘价 | close_price | 收盘价 |
| change_rate | Decimal | ❌ | 涨跌幅(%) | change_rate | 涨跌幅 |
| net_buy_amount | Decimal | ❌ | 净买入金额（万元） | net_amount | 净买入 |
| total_amount | Decimal | ❌ | 成交额（万元） | amount | 成交额 |
| reason | String | ❌ | 上榜原因 | **无** | 龙虎榜 reason |
| data_source | String | ✅ | 数据来源 | 固定值 | 固定值 |

---

### 2.6 资金流向数据 - stock_money_flow（TU独占）

| 字段名 | 数据类型 | 必填 | 说明 | TuShare字段 |
|--------|---------|------|------|------------|
| **主键字段** |
| symbol | String | ✅ | 股票代码 | ts_code |
| trade_date | String | ✅ | 交易日期 | trade_date |
| **特大单** |
| buy_large_volume | Long | ❌ | 特大单买入量（手） | buy_l_vol |
| sell_large_volume | Long | ❌ | 特大单卖出量（手） | sell_l_vol |
| **中单** |
| buy_medium_volume | Long | ❌ | 中单买入量（手） | buy_m_vol |
| sell_medium_volume | Long | ❌ | 中单卖出量（手） | sell_m_vol |
| **小单** |
| buy_small_volume | Long | ❌ | 小单买入量（手） | buy_s_vol |
| sell_small_volume | Long | ❌ | 小单卖出量（手） | sell_s_vol |
| data_source | String | ✅ | 数据来源 | 固定`tushare` |

---

### 2.7 股东人数数据 - stock_holder_count（TU独占）

| 字段名 | 数据类型 | 必填 | 说明 | TuShare字段 |
|--------|---------|------|------|------------|
| symbol | String | ✅ | 股票代码 | ts_code |
| ann_date | String | ❌ | 公告日期 | ann_date |
| end_date | String | ✅ | 报告期 | end_date |
| holder_count | Long | ❌ | 股东人数（户） | holder_num |
| holder_count_change | Decimal | ❌ | 股东人数较上期变化（%） | holder_num_chg |
| data_source | String | ✅ | 数据来源 | 固定`tushare` |

---

### 2.8 十大流通股东数据 - stock_top_holders（AK独占）

| 字段名 | 数据类型 | 必填 | 说明 | AkShare字段 |
|--------|---------|------|------|-------------|
| symbol | String | ✅ | 股票代码 | 股票代码 |
| end_date | String | ✅ | 报告期 | 截止日期 |
| holder_rank | Integer | ❌ | 股东排名 | 排名 |
| holder_name | String | ❌ | 股东名称 | 股东名称 |
| holder_shares | Long | ❌ | 持股数量（股） | 持股数量 |
| holder_ratio | Decimal | ❌ | 持股比例（%） | 持股比例 |
| holder_change | Long | ❌ | 持股变化（股） | 较上期变化 |
| data_source | String | ✅ | 数据来源 | 固定`akshare` |

---

### 2.9 交易日历 - trade_calendar

| 字段名 | 数据类型 | 说明 |
|--------|---------|------|
| calendar_date | String | 日历日期，YYYYMMDD |
| is_open | Boolean | 是否交易（true/false） |
| exchange | String | 交易所代码：SSE/SZSE |
| pretrade_date | String | 上一交易日 |

---

## 三、数据获取与转换流程

### 3.1 统一存储架构设计原则

**核心思想**：无论数据来自哪个数据源，存入数据库后都必须符合统一的Schema规范。

**三层架构**：

```
┌─────────────────────────────────────────────────────────────────┐
│                        第一层：原始数据层                         │
│  TuShare原始数据 / AkShare原始数据                               │
│  - 保持原始格式                                                  │
│  - 用于调试和追溯                                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ 适配器转换
┌─────────────────────────────────────────────────────────────────┐
│                        第二层：统一数据层                         │
│  统一字段名 / 统一数据格式 / 统一数据类型                         │
│  - 共同字段：两个数据源都有                                      │
│  - 独占字段：标记来源，允许null                                  │
│  - 可选字段：允许null                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ 持久化
┌─────────────────────────────────────────────────────────────────┐
│                        第三层：存储层                             │
│  MongoDB统一集合                                                 │
│  - 每条记录包含data_source字段                                   │
│  - 通过唯一索引去重                                              │
│  - 支持多源数据共存                                              │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 数据获取流程

```
┌─────────────────────────────────────────────────────────────────┐
│                      步骤1：数据获取请求                          │
│  输入：股票代码、日期范围、数据类型                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      步骤2：数据源路由决策                        │
│  2.1 检查接口类型（通用/独占/权限）                              │
│  2.2 检查TuShare积分权限                                         │
│  2.3 选择合适的数据源                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      步骤3：原始数据获取                          │
│  TuShare返回：pandas DataFrame / JSON                          │
│  AkShare返回：pandas DataFrame（中文字段）                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      步骤4：适配器转换                            │
│  4.1 字段映射（原始字段名 → 统一字段名）                         │
│  4.2 中文转英文（AkShare特有）                                   │
│  4.3 代码格式统一（添加交易所后缀）                              │
│  4.4 日期格式统一（YYYYMMDD）                                    │
│  4.5 金额单位统一（转换为万元）                                  │
│  4.6 数据类型转换（字符串 → 对应类型）                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      步骤5：数据验证                              │
│  5.1 必填字段检查                                                │
│  5.2 数据范围验证                                                │
│  5.3 标记独占字段为null（如果源数据缺失）                        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      步骤6：统一数据模型                          │
│  输出：符合统一Schema的数据对象列表                             │
│  - 所有字段名为英文                                              │
│  - 所有数据类型统一                                              │
│  - 包含data_source标识                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      步骤7：数据存储                              │
│  7.1 去重检查（根据唯一索引判断是否存在）                       │
│  7.2 更新或插入（upsert操作）                                   │
│  7.3 记录数据来源和时间戳                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

### 3.3 字段映射策略

#### 3.3.1 TuShare字段映射

**映射规则**：
1. 字段名基本一致，直接映射
2. 需要特殊处理的字段：
   - `ts_code` → `symbol`（保持不变）
   - `vol` → `volume`（成交量）
   - `pct_chg` → `change_pct`（涨跌幅）
   - 金额单位：千元需转换为万元（除以10000）

#### 3.3.2 AkShare字段映射

**映射规则**：
1. 中文字段名 → 英文字段名：
   - `日期` → `trade_date`
   - `开盘` → `open`
   - `收盘` → `close`
   - `成交量` → `volume`

2. 股票代码格式转换：
   - 输入：`600519`
   - 判断市场：60开头 → 上海交易所
   - 输出：`600519.SH`

3. 日期格式转换：
   - 输入：`2024-01-02`（日期对象）
   - 输出：`20240102`（字符串）

---

### 3.3 数据格式标准化规则

#### 3.3.1 股票代码标准化

| 输入格式 | 转换规则 | 输出格式 | 示例 |
|---------|---------|---------|------|
| TuShare格式 | 保持不变 | `{代码}.{交易所}` | `600519.SH` |
| AkShare纯数字 | 添加交易所后缀 | `{代码}.{交易所}` | `600519` → `600519.SH` |
| 不含后缀 | 补全后缀 | `{代码}.{交易所}` | `600519` → `600519.SH` |

**交易所判断规则**：
```
上海交易所(SH/.SH)：
- 600xxx, 601xxx, 603xxx, 605xxx  (主板)
- 688xxx, 689xxx                 (科创板)

深圳交易所(SZ/.SZ)：
- 000xxx, 001xxx, 003xxx         (主板)
- 300xxx                         (创业板)
- 301xxx                         (创业板新股)
```

#### 3.3.2 日期格式标准化

| 输入格式 | 转换规则 | 输出格式 |
|---------|---------|---------|
| `YYYYMMDD` | 保持不变 | `YYYYMMDD` |
| `YYYY-MM-DD` | 移除横线 | `YYYYMMDD` |
| 日期对象 | 格式化为字符串 | `YYYYMMDD` |

#### 3.3.3 金额单位标准化

| 数据类型 | 原始单位 | 目标单位 | 转换规则 |
|---------|---------|---------|---------|
| 行情成交额 | TuShare: 千元<br>AkShare: 元 | 万元 | TuShare: ÷10<br>AkShare: ÷10000 |
| 财务数据 | TuShare: 元<br>AkShare: 元 | 万元 | ÷10000 |

#### 3.3.4 数值精度标准化

| 字段类型 | 保留小数位 | 四舍五入 |
|---------|-----------|---------|
| 价格（开高低收） | 2位 | 是 |
| 涨跌幅 | 2位 | 是 |
| 成交额 | 2位 | 是 |
| 市盈率/市净率 | 2位 | 是 |
| 财务比率(ROE等) | 2位 | 是 |

---

### 3.4 数据验证规则

#### 3.4.1 必填字段验证

每个数据类型定义必填字段，存储前检查：

| 数据类型 | 必填字段 |
|---------|---------|
| stock_info | symbol, name, list_date, market, exchange |
| stock_quotes | symbol, trade_date, open, high, low, close, volume, amount |
| stock_financials | symbol, report_date, report_type |

#### 3.4.2 范围验证

| 字段 | 验证规则 |
|------|---------|
| trade_date | 合法日期且不早于1990-01-01 |
| open/high/low/close | 大于0 |
| volume | 大于等于0 |
| change_pct | -20% ~ +20%（A股单日涨跌限制） |

---

## 四、降级策略设计

### 4.1 优先级配置

```
A股数据源优先级：
├── 第一优先级：TuShare Pro
│   ├── 优势：数据权威、更新及时、字段完整
│   ├── 劣势：需要积分、有调用限制
│   └── 适用：正式环境、历史数据补全
│
├── 第二优先级：AkShare
│   ├── 优势：完全免费、无限制、数据较全
│   ├── 劣势：依赖第三方、可能不稳定
│   └── 适用：实时行情、TuShare积分不足时
│
└── 第三优先级：其他备用源（预留）
    ├── iTick（付费）
    └── 其他商业数据源
```

### 4.2 降级触发条件

| 条件 | 说明 |
|------|------|
| 接口调用失败 | HTTP错误、超时、连接失败 |
| 返回数据为空 | 查询结果为空 |
| 积分不足 | TuShare返回权限不足错误 |
| 频率限制 | 超过每分钟调用次数限制 |
| 数据异常 | 必填字段缺失、数值异常 |

### 4.3 降级流程

```
发起数据请求
    │
    ▼
尝试第一优先级
    │
    ├─ 成功 ──→ 返回数据
    │
    └─ 失败 ──→ 记录日志
              │
              ▼
          尝试第二优先级
              │
              ├─ 成功 ──→ 返回数据
              │
              └─ 失败 ──→ 记录日志
                        │
                        ▼
                    尝试第三优先级
                        │
                        ├─ 成功 ──→ 返回数据
                        │
                        └─ 失败 ──→ 抛出异常
```

### 4.4 降级重试策略

| 策略项 | 配置 |
|--------|------|
| 最大重试次数 | 每个数据源重试2次 |
| 重试间隔 | 指数退避：1秒 → 2秒 → 4秒 |
| 超时设置 | 每个请求30秒超时 |
| 熔断机制 | 连续失败10次后暂停5分钟 |

---

## 五、数据存储设计

### 5.1 MongoDB集合结构（完整版）

| 集合名 | 说明 | 分片键 | 索引 | 数据源 |
|--------|------|--------|------|--------|
| **核心数据** |
| `stock_info` | 股票基础信息 | symbol | symbol (unique) | TU+AK |
| `stock_quotes` | 日线行情数据 | symbol, trade_date | (symbol, trade_date, data_source) | TU+AK |
| `stock_quotes_min` | 分钟行情数据 | symbol, trade_time | (symbol, trade_time) | TU+AK |
| `trade_calendar` | 交易日历 | calendar_date | (calendar_date, exchange) | TU独占 |
| **财务数据** |
| `stock_financials` | 财务报表数据 | symbol, report_date | (symbol, report_date, report_type) | TU+AK |
| `stock_financial_indicators` | 财务指标数据 | symbol, report_date | (symbol, report_date) | TU+AK |
| **市场数据** |
| `stock_top_list` | 龙虎榜汇总数据 | trade_date | (symbol, trade_date) | TU+AK |
| `stock_lhb_detail` | 龙虎榜明细数据（AK独占） | symbol, trade_date | (symbol, trade_date) | AK独占 |
| `stock_money_flow` | 资金流向数据（TU独占） | symbol, trade_date | (symbol, trade_date) | TU独占 |
| `stock_margin_trading` | 融资融券数据（AK独占） | symbol, trade_date | (symbol, trade_date) | AK独占 |
| **股东数据** |
| `stock_holder_count` | 股东人数（TU独占） | symbol, end_date | (symbol, end_date) | TU独占 |
| `stock_top_holders` | 十大流通股东（AK独占） | symbol, end_date | (symbol, end_date, holder_rank) | AK独占 |
| **板块数据** |
| `stock_sector_concept` | 概念板块（AK独占） | sector_name | sector_name (unique) | AK独占 |
| `stock_sector_industry` | 行业板块（AK独占） | sector_name | sector_name (unique) | AK独占 |

### 5.2 数据保留策略

| 数据类型 | 保留时长 | 存储范围 | 清理策略 |
|---------|---------|---------|---------|
| 基础信息 | 永久保留 | 全市场 | 不清理 |
| **日线行情** | **1周** | **仅自选股** | 定时任务每天清理过期数据 |
| **分钟行情** | **1周** | **仅自选股** | 定时任务每天清理过期数据 |
| 龙虎榜 | 保留3年 | 全市场 | 定时清理过期数据 |
| 财务数据 | 永久保留 | 全市场 | 不清理 |

**重要说明**：
- **日线/分钟行情数据**：公共数据库仅存储用户自选股的数据，保留1周
- **实时日K数据需求**：用户需从自己配置的付费接口（如Tushare Pro）实时获取，系统不同步全市场日K数据
- **设计原因**：日线数据主要用于实时短线分析，非自选股无需长期存储

### 5.3 存储操作规范

#### 5.3.1 Upsert策略

使用 **upsert**（更新或插入）操作：
- 根据 **唯一索引** 判断数据是否存在
- 存在则更新，不存在则插入
- 避免重复数据

#### 5.3.2 批量写入

- 单次批量操作上限：**1000条**
- 超过上限分批写入
- 使用MongoDB的 `bulk_write()` 提高性能

#### 5.3.3 数据来源标识

每条记录必须包含：
- `data_source`：数据源标识（`tushare`/`akshare`）
- `updated_at`：更新时间戳
- 便于追溯和问题排查

---

## 六、数据源差异处理（核心章节）

### 6.1 TuShare vs AkShare 差异对比

| 对比项 | TuShare | AkShare |
|--------|---------|---------|
| **认证方式** | 需Token | 无需认证 |
| **字段名** | 英文缩写 | 中文 |
| **代码格式** | `{代码}.{交易所}` | 纯数字代码 |
| **日期格式** | `YYYYMMDD` 字符串 | 日期对象 |
| **金额单位** | 千元/元 | 元 |
| **数据完整性** | 高，字段完整 | 中等，部分字段缺失 |
| **更新频率** | 日线收盘后更新 | 实时更新 |
| **调用限制** | 有积分和频次限制 | 依赖第三方反爬 |
| **复权数据** | 支持 | 支持 |

---

### 6.2 字段差异处理策略（重点）

#### 6.2.1 字段分类体系

根据字段在两个数据源中的可用性，将所有字段分为三大类：

**A. 共同字段**（Core Fields）
- 两个数据源都有的字段
- 这是统一存储的核心字段
- 示例：开盘价、收盘价、成交量等

**B. 独占字段**（Exclusive Fields）
- 仅某个数据源独有的字段
- 存储：保留该字段，标记来源
- 示例：AkShare 的"换手率"（早期TuShare日线没有）

**C. 可选字段**（Optional Fields）
- 一个数据源有，另一个可能为空的字段
- 存储：允许null，不强制要求

#### 6.2.2 字段缺失处理规则

| 场景 | 处理规则 | 示例 |
|------|---------|------|
| **AK有，TU没有** | 保留字段，值为null时标记data_source | `turnover_rate` 换手率 |
| **TU有，AK没有** | 保留字段，值为null时标记data_source | `adj_factor` 复权因子 |
| **两者都有，名称不同** | 建立映射表，统一字段名 | `vol` → `volume` |
| **两者都有，精度不同** | 统一精度标准，存储时转换 | 金额统一为万元 |
| **两者都缺失** | 不作为必填字段，允许null | 某些衍生指标 |

#### 6.2.3 行情数据字段对照表（完整版）

| 统一字段名 | TuShare字段 | AkShare字段 | 数据类型 | 必填 | 说明 |
|-----------|------------|------------|---------|------|------|
| **核心价格字段** |
| symbol | ts_code | 代码 | String | ✅ | 股票代码（需统一格式） |
| trade_date | trade_date | 日期 | String | ✅ | 交易日期 |
| open | open | 开盘 | Decimal | ✅ | 开盘价 |
| high | high | 最高 | Decimal | ✅ | 最高价 |
| low | low | 最低 | Decimal | ✅ | 最低价 |
| close | close | 收盘 | Decimal | ✅ | 收盘价 |
| pre_close | pre_close | 昨收 | Decimal | ✅ | 昨收价 |
| **成交数据字段** |
| volume | vol | 成交量 | Long | ✅ | 成交量（手） |
| amount | amount | 成交额 | Decimal | ✅ | 成交额（万元） |
| **涨跌数据字段** |
| change | change | 涨跌额 | Decimal | ❌ | 涨跌额 |
| change_pct | pct_chg | 涨跌幅 | Decimal | ❌ | 涨跌幅（%） |
| **TuShare独占字段** |
| adj_factor | adj_factor | **无** | Decimal | ❌ | 复权因子（TU独占） |
| **AkShare独占字段** |
| turnover_rate | **无** | 换手率 | Decimal | ❌ | 换手率（%）（AK独占） |
| amplitude | **无** | 振幅 | Decimal | ❌ | 振幅（%）（AK独占） |

#### 6.2.4 股票基础信息字段对照表（完整版）

| 统一字段名 | TuShare字段 | AkShare字段 | 数据类型 | 必填 | 缺失处理 |
|-----------|------------|------------|---------|------|---------|
| symbol | ts_code | 代码 | String | ✅ | 必填 |
| name | name | 名称 | String | ✅ | 必填 |
| list_date | list_date | 上市日期 | String | ✅ | 必填 |
| market | market | **需判断** | String | ✅ | AK根据代码判断 |
| exchange | exchange | **需判断** | String | ✅ | AK根据代码判断 |
| industry | industry | **无** | String | ❌ | TU独占，AK为null |
| area | area | **无** | String | ❌ | TU独占（地域），AK为null |
| is_hs | is_hs | **无** | String | ❌ | TU独占（沪深港通），AK为null |

#### 6.2.5 财务报表字段对照表（完整版）

##### 利润表字段（income）

| 统一字段名 | TuShare字段 | AkShare字段 | 数据类型 | 必填 | 说明 |
|-----------|------------|------------|---------|------|------|
| **主键字段** |
| symbol | ts_code | 股票代码 | String | ✅ | 股票代码 |
| ann_date | ann_date | 公告日期 | String | ❌ | 公告日期 |
| report_date | end_date | 报告期 | String | ✅ | 报告期YYYYMMDD |
| report_type | report_type | - | String | ❌ | 报告类型 C合并/Q单季 |
| **核心利润指标** |
| basic_eps | basic_eps | 每股收益 | Decimal | ❌ | 基本每股收益 |
| total_revenue | total_revenue | 营业总收入 | Decimal | ❌ | 营业总收入 |
| revenue | revenue | 营业收入 | Decimal | ❌ | 营业收入 |
| operating_cost | oper_cost | 营业成本 | Decimal | ❌ | 营业成本 |
| operating_expense | oper_exp | **无** | Decimal | ❌ | 营业税金及附加（TU独占） |
| selling_expense | sell_exp | **无** | Decimal | ❌ | 销售费用（TU独占） |
| admin_expense | admin_exp | **无** | Decimal | ❌ | 管理费用（TU独占） |
| finance_expense | fin_exp | **无** | Decimal | ❌ | 财务费用（TU独占） |
| total_profit | total_profit | **无** | Decimal | ❌ | 利润总额（TU独占） |
| net_income | n_income | 净利润 | Decimal | ❌ | 净利润 |
| net_income_parent | n_income_attr_p | **无** | Decimal | ❌ | 归属母公司净利润（TU独占） |

##### 资产负债表字段（balancesheet）

| 统一字段名 | TuShare字段 | AkShare字段 | 数据类型 | 必填 | 说明 |
|-----------|------------|------------|---------|------|------|
| **主键字段** |
| symbol | ts_code | 股票代码 | String | ✅ | 股票代码 |
| ann_date | ann_date | 公告日期 | String | ❌ | 公告日期 |
| report_date | end_date | 报告期 | String | ✅ | 报告期 |
| **资产类** |
| total_assets | total_assets | 资产总计 | Decimal | ❌ | 总资产 |
| current_assets | cur_assets | 流动资产合计 | Decimal | ❌ | 流动资产 |
| fixed_assets | fix_assets | **无** | Decimal | ❌ | 固定资产（TU独占） |
| **负债类** |
| total_liabilities | total_liab | 负债合计 | Decimal | ❌ | 总负债 |
| current_liabilities | cur_liab | 流动负债合计 | Decimal | ❌ | 流动负债 |
| **权益类** |
| total_equity | total_hldr_eqy_exc_min_int | 股东权益合计 | Decimal | ❌ | 股东权益 |

##### 现金流量表字段（cashflow）

| 统一字段名 | TuShare字段 | AkShare字段 | 数据类型 | 必填 | 说明 |
|-----------|------------|------------|---------|------|------|
| **主键字段** |
| symbol | ts_code | 股票代码 | String | ✅ | 股票代码 |
| ann_date | ann_date | 公告日期 | String | ❌ | 公告日期 |
| report_date | end_date | 报告期 | String | ✅ | 报告期 |
| **经营现金流** |
| net_profit | net_profit | **无** | Decimal | ❌ | 净利润（TU独占） |
| cash_inflow_operate | c_inf_fr_operate_act | **无** | Decimal | ❌ | 经营活动现金流入（TU独占） |
| cash_outflow_operate | c_outf_fr_operate_act | **无** | Decimal | ❌ | 经营活动现金流出（TU独占） |
| operating_cash_flow | n_cash_flows_fnc_oper_act | 经营活动现金流量净额 | Decimal | ❌ | 经营活动现金流净额 |
| **投资现金流** |
| investing_cash_flow | n_cashfl_from_inv_act | **无** | Decimal | ❌ | 投资活动现金流净额 |
| **筹资现金流** |
| financing_cash_flow | n_cash_flows_fnc_fin_act | **无** | Decimal | ❌ | 筹资活动现金流净额 |

---

### 6.3 接口独占处理机制

#### 6.3.1 接口分类体系

根据接口在不同数据源的可用性和权限要求，将接口分为三类：

**A. 通用接口**（Common APIs）
- 两个数据源都提供
- 优先使用TuShare，失败时降级到AkShare
- 示例：日线行情、股票列表

**B. 独占接口**（Exclusive APIs）
- 仅某个数据源提供
- 必须使用该数据源，无法降级
- 示例：TuShare的复权因子、AkShare的概念板块

**C. 权限接口**（Restricted APIs）
- TuShare需要积分才能调用
- 根据用户积分等级决定是否可用
- 可降级到AkShare替代接口

#### 6.3.2 A股接口分类表（完整版）

| 接口功能 | TuShare | AkShare | 类型 | 最低积分 | 降级策略 |
|---------|---------|---------|------|---------|---------|
| **基础数据** |
| 股票列表 | stock_basic | stock_zh_a_spot_em | 通用 | 0 | 优先TU，降级AK |
| 交易日历 | trade_cal | **无** | TU独占 | 0 | 仅TU |
| IPO新股列表 | new_share | **无** | TU独占 | 0 | 仅TU |
| **行情数据** |
| 日线行情 | daily / pro_bar | stock_zh_a_hist | 通用 | 0 | 优先TU，降级AK |
| 分钟行情 | stk_mins | stock_zh_a_hist_min_em | 权限 | 2000 | 积分不足用AK |
| 复权因子 | adj_factor | **无** | TU独占 | 2000 | 积分不足无法获取 |
| **财务数据** |
| 利润表 | income | stock_profit_sheet_by_report_em | 权限 | 2000 | 积分不足用AK |
| 资产负债表 | balancesheet | stock_balance_sheet_by_report_em | 权限 | 2000 | 积分不足用AK |
| 现金流量表 | cashflow | stock_cash_flow_sheet_by_report_em | 权限 | 2000 | 积分不足用AK |
| 财务指标 | fina_indicator | stock_financial_abstract | 权限 | 2000 | 积分不足用AK |
| **特色数据** |
| 龙虎榜 | top_list | stock_lhb_detail_em | 权限 | 2000 | 积分不足用AK |
| 资金流向 | moneyflow | **无** | TU独占 | 2000 | 积分不足无法获取 |
| 股东人数 | stk_holdernumber | **无** | TU独占 | 2000 | 积分不足无法获取 |
| **股东数据** |
| 十大流通股东 | **无** | stock_gdfx_top_10_em | AK独占 | - | 仅AK |
| 个股龙虎榜日期 | **无** | stock_lhb_stock_detail_date_em | AK独占 | - | 仅AK |
| 个股龙虎榜明细 | **无** | stock_lhb_stock_detail_em | AK独占 | - | 仅AK |
| **融资融券** |
| 融资融券汇总 | **无** | stock_margin_sse/szse | AK独占 | - | 仅AK |
| **板块数据** |
| 概念板块列表 | **无** | stock_board_concept_name_em | AK独占 | - | 仅AK |
| 概念板块行情 | **无** | stock_board_concept_spot_em | AK独占 | - | 仅AK |
| 概念板块成分股 | **无** | stock_board_concept_cons_em | AK独占 | - | 仅AK |
| 行业板块列表 | **无** | stock_board_industry_name_em | AK独占 | - | 仅AK |

#### 6.3.3 独占接口存储策略

**TuShare独占接口**：
- 复权因子：存储到 `stock_quotes.adj_factor` 字段
- 资金流向：存储到 `stock_money_flow` 集合
- 股东人数：存储到 `stock_holder_count` 集合
- 交易日历：存储到 `trade_calendar` 集合

**AkShare独占接口**：
- 概念板块：存储到 `stock_sector_concept` 集合
- 行业板块：存储到 `stock_sector_industry` 集合
- 融资融券：存储到 `stock_margin_trading` 集合
- 十大流通股东：存储到 `stock_top_holders` 集合
- 个股龙虎榜明细：存储到 `stock_lhb_detail` 集合

---

### 6.5 接口适配差异与处理逻辑

#### 6.5.1 关键接口适配差异表

| 接口类型 | TuShare参数能力 | AkShare参数能力 | 适配策略 |
|---------|---------------|----------------|---------|
| **股票列表** | 支持按exchange、list_status筛选 | 直接返回全部A股 | AK获取全部后按需筛选 |
| **日线行情** | 支持ts_code、trade_date筛选 | 支持symbol、日期范围筛选 | 参数名不同，需转换 |
| **财务报表** | 支持ts_code、period筛选 | **不支持按股票筛选** | AK必须获取全部后本地筛选 |
| **财务指标** | 支持ts_code、period筛选 | **不支持按股票筛选** | AK必须获取全部后本地筛选 |
| **龙虎榜** | 支持trade_date、ts_code筛选 | 支持日期筛选 | 参数基本一致 |

#### 6.5.2 AkShare财务数据适配流程（重要）

**问题**：AkShare的财务接口不支持按股票代码筛选，调用时返回所有股票的数据。

**适配流程**：

```
请求某只股票的财务数据（如：600519.SH）
    │
    ├─→ 优先尝试TuShare
    │     └─→ 可直接调用：pro.income(ts_code='600519.SH', period='20231231')
    │
    └─→ TuShare失败时，降级到AkShare
          │
          ├─→ 步骤1：调用AkShare财务接口（不传参数）
          │      df = ak.stock_profit_sheet_by_report_em()
          │      # 返回所有股票的财务数据
          │
          ├─→ 步骤2：中文字段转英文字段
          │      "股票代码" → "symbol"
          │      "报告期" → "report_date"
          │      "营业收入" → "revenue"
          │      等等...
          │
          ├─→ 步骤3：本地筛选目标股票
          │      df_filtered = df[df['symbol'] == '600519.SH']
          │
          └─→ 步骤4：处理TuShare有但AkShare没有的字段
                # 设置为null
```

**性能影响说明**：
- TuShare：只获取需要的数据，效率高
- AkShare财务接口：需要获取全部数据再筛选，数据量大时效率较低
- **建议**：优先使用TuShare，AkShare仅作为降级备用

#### 6.5.3 AkShare字段完整映射表

##### 行情数据字段映射

| AkShare中文字段 | TuShare英文字段 | 数据类型 | 转换说明 |
|----------------|----------------|---------|---------|
| 日期 | trade_date | String | 格式保持一致 |
| 股票代码 | symbol | String | 需添加交易所后缀 |
| 开盘 | open | Decimal | 直接映射 |
| 收盘 | close | Decimal | 直接映射 |
| 最高 | high | Decimal | 直接映射 |
| 最低 | low | Decimal | 直接映射 |
| 成交量 | volume | Long | 直接映射 |
| 成交额 | amount | Decimal | 需单位转换（元→万元） |
| 振幅 | amplitude | Decimal | AkShare独占，TuShare为null |
| 涨跌幅 | change_pct | Decimal | 直接映射 |
| 涨跌额 | change | Decimal | 直接映射 |
| 换手率 | turnover_rate | Decimal | AkShare独占，TuShare日线无 |

##### 财务报表字段映射（利润表）

| AkShare中文字段 | TuShare英文字段 | 数据类型 | 说明 |
|----------------|----------------|---------|------|
| 股票代码 | symbol | String | 需添加交易所后缀 |
| 报告期 | report_date | String | 格式：YYYYMMDD |
| 营业收入 | revenue | Decimal | TuShare也有 |
| 营业成本 | operating_cost | Decimal | TuShare: oper_cost |
| 净利润 | net_income | Decimal | TuShare: n_income |
| 每股收益 | basic_eps | Decimal | TuShare也有 |
| **TuShare独占字段（AkShare为null）** |
| - | operating_expense | Decimal | 营业税金及附加 |
| - | selling_expense | Decimal | 销售费用 |
| - | admin_expense | Decimal | 管理费用 |
| - | finance_expense | Decimal | 财务费用 |
| - | total_profit | Decimal | 利润总额 |
| - | net_income_parent | Decimal | 归属母公司净利润 |

##### 财务报表字段映射（资产负债表）

| AkShare中文字段 | TuShare英文字段 | 数据类型 | 说明 |
|----------------|----------------|---------|------|
| 资产总计 | total_assets | Decimal | 直接映射 |
| 负债合计 | total_liabilities | Decimal | TuShare: total_liab |
| 股东权益合计 | total_equity | Decimal | TuShare: total_hldr_eqy_exc_min_int |
| 流动资产合计 | current_assets | Decimal | TuShare: cur_assets |
| 流动负债合计 | current_liabilities | Decimal | TuShare: cur_liab |
| **TuShare独占字段（AkShare为null）** |
| - | fixed_assets | Decimal | 固定资产 |

##### 财务报表字段映射（现金流量表）

| AkShare中文字段 | TuShare英文字段 | 数据类型 | 说明 |
|----------------|----------------|---------|------|
| 经营活动现金流量净额 | operating_cash_flow | Decimal | TuShare: n_cash_flows_fnc_oper_act |
| **TuShare独占字段（AkShare为null）** |
| - | net_profit | Decimal | 净利润 |
| - | cash_inflow_operate | Decimal | 经营活动现金流入 |
| - | cash_outflow_operate | Decimal | 经营活动现金流出 |
| - | investing_cash_flow | Decimal | 投资活动现金流净额 |
| - | financing_cash_flow | Decimal | 筹资活动现金流净额 |

#### 6.5.4 数据存储示例

**示例1：TuShare和AkShare都有的数据（日线行情）**

```
场景：获取 600519.SH 在 2024-01-02 的日线数据

使用TuShare（优先）：
- 调用：pro.daily(ts_code='600519.SH', trade_date='20240102')
- 存储：{symbol: "600519.SH", trade_date: "20240102", ..., data_source: "tushare"}

如果TuShare失败，降级到AkShare：
- 调用：ak.stock_zh_a_hist(symbol="600519", start_date="20240101", end_date="20240103")
- 转换：{"日期": "2024-01-02", "开盘": 1800} → {trade_date: "20240102", open: 1800}
- 存储：{symbol: "600519.SH", trade_date: "20240102", ..., data_source: "akshare"}
```

**示例2：TuShare有但AkShare没有的字段**

```
TuShare返回的数据：
{
  "symbol": "600519.SH",
  "trade_date": "20240102",
  "operating_expense": 123.45,  # TuShare独占字段
  "data_source": "tushare"
}

AkShare返回的数据（同一股票同一天）：
{
  "symbol": "600519.SH",
  "trade_date": "20240102",
  "operating_expense": null,     # AkShare没有此字段
  "data_source": "akshare"
}
```

**示例3：AkShare财务数据的适配流程**

```
请求：获取 600519.SH 的利润表数据

方式1：使用TuShare（推荐）
- 调用：pro.income(ts_code='600519.SH', period='20231231')
- 结果：直接获取目标股票数据，效率高

方式2：TuShare失败，降级到AkShare
步骤1：获取所有股票数据
  all_data = ak.stock_profit_sheet_by_report_em()  # 不传参数，返回全部

步骤2：中文字段转英文字段
  映射：{"股票代码": "symbol", "报告期": "report_date", "营业收入": "revenue", ...}

步骤3：添加交易所后缀
  "600519" → "600519.SH"

步骤4：筛选目标股票
  data = all_data[all_data['symbol'] == '600519.SH']

步骤5：TuShare独占字段设为null
  data['operating_expense'] = null
  data['selling_expense'] = null
  ...

步骤6：存储
  data['data_source'] = 'akshare'
```

---

### 6.6 数据源路由决策逻辑

#### 6.6.1 决策流程图

```
发起数据请求
    │
    ▼
检查接口类型
    │
    ├─→ 通用接口
    │     │
    │     ▼
    │   检查TuShare积分权限
    │     │
    │     ├─→ 权限足够 → 尝试TuShare
    │     │                    │
    │     │                    ├─→ 成功 → 返回数据
    │     │                    └─→ 失败 → 降级到AkShare
    │     │
    │     └─→ 权限不足 → 直接使用AkShare
    │
    ├─→ TuShare独占接口
    │     │
    │     ▼
    │   检查积分权限
    │     │
    │     ├─→ 权限足够 → 调用TuShare
    │     │                    │
    │     │                    ├─→ 成功 → 返回数据
    │     │                    └─→ 失败 → 返回错误
    │     │
    │     └─→ 权限不足 → 返回错误（提示需要积分）
    │
    └─→ AkShare独占接口
          │
          ▼
        直接调用AkShare
```

#### 6.6.2 路由决策规则表

| 决策条件 | 选择策略 | 说明 |
|---------|---------|------|
| **通用接口 + 有积分** | TuShare优先 | 数据质量更高 |
| **通用接口 + 无积分** | AkShare | TuShare无法调用 |
| **通用接口 + TU失败** | 降级AkShare | 自动降级 |
| **TU独占 + 有积分** | TuShare | 必须用TuShare |
| **TU独占 + 无积分** | 返回错误 | 提示需要积分 |
| **AK独占** | AkShare | 必须用AkShare |

---

### 6.7 差异处理方案总结

| 差异点 | 处理方案 |
|--------|---------|
| **字段名不同** | 建立映射表，适配器层自动转换 |
| **代码格式不同** | 统一转换为 `{代码}.{交易所}` 格式 |
| **日期格式不同** | 统一转换为 `YYYYMMDD` 字符串 |
| **金额单位不同** | 统一转换为万元，存储前换算 |
| **字段缺失** | 独占字段允许null，标记data_source |
| **接口独占** | 分类存储，不可降级的返回错误 |
| **积分限制** | 检查权限，权限不足时降级或提示 |
| **中文字段** | 建立中英文映射表，自动转换 |
| **接口参数差异** | AkShare财务接口需获取全部数据后本地筛选 |

---

## 七、异常处理方案

### 7.1 异常类型

| 异常类型 | 处理方式 |
|---------|---------|
| 网络超时 | 重试3次，指数退避 |
| 连接失败 | 切换备用数据源 |
| 接口限流 | 等待后重试或降级 |
| 返回为空 | 记录日志，切换数据源 |
| 数据格式异常 | 跳过该条数据，记录错误日志 |
| 必填字段缺失 | 跳过该条数据，记录错误日志 |

### 7.2 错误日志记录

每次异常需记录：
- 错误时间
- 数据源
- 请求参数
- 错误类型
- 错误信息
- 是否已降级

---

## 八、数据同步策略

### 8.1 全量同步

**适用场景**：首次初始化、定期全量更新

**执行方式**：
1. 获取股票列表
2. 遍历每只股票
3. 按时间范围获取历史数据
4. 批量写入数据库

**注意事项**：
- 控制请求频率，避免限流
- 分批处理，避免内存溢出
- 记录同步进度，支持断点续传

### 8.2 增量同步

**适用场景**：每日更新、补录最新数据

**执行方式**：
1. 查询数据库中最新数据日期
2. 从最新日期次日开始获取
3. 追加写入数据库

**注意事项**：
- 交易日历判断，非交易日跳过
- 数据去重，避免重复写入

### 8.3 补录策略

**触发条件**：
- 发现数据缺失
- 数据源恢复后补录历史数据

**执行方式**：
1. 检测缺失的时间范围
2. 批量补录缺失数据
3. 标记数据来源和补录时间

---

## 九、数据质量保证

### 9.1 数据校验规则

| 校验项 | 规则 |
|--------|------|
| 价格连续性 | 昨收价 = 前一日收盘价（允许停牌偏差） |
| 价格合理性 | 开盘价 ≤ 最高价，收盘价 ≤ 最高价 |
| 成交量非负 | volume ≥ 0 |
| 日期连续性 | 连续交易日日期连续 |
| 财务数据一致性 | 三大报表勾稽关系验证 |

### 9.2 异常数据处理

| 异常情况 | 处理方式 |
|---------|---------|
| 价格异常波动 | 标记异常值，人工复核 |
| 成交量为0 | 检查是否停牌 |
| 缺失字段 | 使用默认值或标记为null |
| 重复数据 | 使用upsert覆盖旧数据 |

---

## 十、总结与实施要点

### 10.1 核心原则

1. **统一数据格式**：定义6大类数据的统一Schema，所有数据源必须遵守
2. **适配器模式**：每个数据源实现适配器，转换为统一格式后再存储
3. **智能路由**：根据接口类型和积分权限，自动选择最佳数据源
4. **字段分类管理**：
   - 共同字段：两个数据源都有，统一存储
   - 独占字段：标记来源，允许null
   - 可选字段：允许null
5. **格式标准化**：统一代码格式、日期格式、金额单位
6. **来源可追溯**：每条数据记录 `data_source` 标识
7. **去重机制**：使用MongoDB唯一索引 + upsert操作

### 10.2 关键实施要点

**字段差异处理**：
- AK有TU没有的字段：保留字段，允许null，标记来源
- TU有AK没有的字段：保留字段，允许null，标记来源
- 两者都有但名称不同：建立映射表自动转换
- 两者都缺失：不作为必填字段

**接口分类与路由**：
- 通用接口：优先TuShare，失败时降级AkShare
- TU独占接口：必须使用TuShare，积分不足时返回错误
- AK独占接口：直接使用AkShare
- 权限接口：根据积分等级决定是否可用

**中文字段处理**：
- AkShare返回的中文字段自动转换为英文
- 建立完整的中英文映射表
- 在适配器层进行自动转换

**数据存储策略**：
- 统一集合存储，通过data_source字段区分来源
- 独占接口数据可存储到独立集合
- 支持多源数据在同一集合中共存

### 10.3 数据完整性保证

```
统一存储架构核心价值：
├── 数据格式统一：无论来源如何，存储格式一致
├── 字段差异可控：通过分类和映射处理所有差异
├── 来源可追溯：每条数据都知道来自哪个数据源
├── 接口灵活切换：可根据权限和可用性自动切换数据源
└── 扩展性强：新增数据源只需实现适配器
```

### 10.4 实施建议

1. **先建立字段映射表**：完整列出所有字段的对照关系
2. **实现适配器层**：每个数据源一个适配器，负责转换
3. **实现路由决策器**：根据接口类型和权限选择数据源
4. **建立测试用例**：覆盖所有接口和数据类型
5. **监控数据质量**：记录数据来源，便于问题排查

---

**文档版本**：v2.2
**创建日期**：2026-01-03
**最后更新**：2026-01-03
**维护者**：Stock Analysis Team
**更新内容**：
- **新增核心原则章节**：明确数据存储唯一性原则、数据标准化原则（以TuShare为准）、字段缺失处理原则
- **新增接口适配差异与处理逻辑（6.5节）**：
  - 接口参数能力对比表（TuShare支持筛选 vs AkShare需获取全部）
  - AkShare财务数据适配流程图（获取全部→字段转换→本地筛选）
  - 完整的字段映射表（市场行情、利润表、资产负债表、现金流量表）
  - 数据存储示例（展示两数据源如何映射到统一Schema）
- **优化文档结构**：
  - 补充完整财务报表字段（利润表、资产负债表、现金流量表）
  - 新增资金流向数据结构（stock_money_flow）
  - 新增股东人数数据结构（stock_holder_count）
  - 新增十大流通股东数据结构（stock_top_holders）
  - 新增龙虎榜明细数据结构（stock_lhb_detail）
  - 更新接口分类表，增加更多AkShare独占接口
  - 优化MongoDB集合结构表，标注数据来源
- **关键改进**：
  - 明确数据库按数据存储，不按数据源重复存储
  - AkShare中文字段自动转换为英文标准
  - 处理接口参数差异（AkShare财务接口需本地筛选）
