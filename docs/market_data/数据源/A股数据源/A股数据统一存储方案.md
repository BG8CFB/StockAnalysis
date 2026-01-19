# A股数据统一存储方案

## 核心原则

### 1. 数据存储唯一性原则
**数据库按数据存储，不按数据源重复存储**：
- 同一股票的同一交易日数据，数据库中只存储一条记录。
- 通过 `ts_code + trade_date`（或其他唯一键）判断数据是否存在。
- 使用 upsert 操作：存在则更新，不存在则插入。

### 2. 数据标准化原则
**以 TuShare 的标准化数据为存储标准**：
- 所有数据最终存储时，字段名必须符合 TuShare 的英文标准。
- AkShare 的中文字段必须转换为对应的英文字段。
- 两个数据源都有的接口，优先使用 TuShare，AkShare 作为降级备份。

### 3. 数据清洗逻辑
- **单位对齐**: 统一转换为标准单位（如：金额统一为**元**，成交量统一为**手**）。
- **日期格式**: 统一清洗为 `YYYYMMDD` 字符串格式。
- **空值处理**: 缺失字段存为 `null`，不使用默认值（如0），以免误导分析。

---

## 一、基础信息类

### 1.1 股票基本信息 (`stock_basic_info`)
整合股票的基础档案信息。

*   **TU接口**: `stock_basic`, `stock_company`
*   **AK接口**: `stock_individual_info_em`
*   **清洗规则**:
    *   `ts_code`: AK的6位代码需根据市场后缀补全 (如 600xxx -> .SH)。
    *   `list_date`: AK的 `上市时间` 需转为 `YYYYMMDD`。

| 统一字段 | 类型 | TU 来源字段 | AK 来源字段 | 备注 |
| :--- | :--- | :--- | :--- | :--- |
| **ts_code** | String | `ts_code` | `股票代码` (需转换) | 主键 |
| **symbol** | String | `symbol` | `股票代码` | |
| **name** | String | `name` | `股票简称` | |
| **area** | String | `area` | - | |
| **industry** | String | `industry` | `行业` | |
| **market** | String | `market` | - | |
| **list_date** | String | `list_date` | `上市时间` | |
| **fullname** | String | `fullname` | - | |
| **description**| String | `introduction`| - | |

### 1.2 交易日历 (`trade_calendar`)
*   **TU接口**: `trade_cal`
*   **AK接口**: `tool_trade_date_hist_sina`

| 统一字段 | 类型 | TU 来源字段 | AK 来源字段 |
| :--- | :--- | :--- | :--- |
| **cal_date** | String | `cal_date` | `trade_date` |
| **is_open** | Integer| `is_open` | - |

---

## 二、行情数据类

### 2.1 日线行情 (`stock_daily_qfq`)
存储前复权 (QFQ) 数据。

*   **TU接口**: `pro_bar` (adj='qfq')
*   **AK接口**: `stock_zh_a_hist` (adjust='qfq')
*   **清洗规则**:
    *   `amount`: TU单位为千元，AK单位为元。**入库统一为元**。
    *   `trade_date`: 统一格式化。

| 统一字段 | 类型 | TU 来源字段 | AK 来源字段 |
| :--- | :--- | :--- | :--- |
| **ts_code** | String | `ts_code` | `股票代码` |
| **trade_date** | String | `trade_date` | `日期` |
| **open** | Double | `open` | `开盘` |
| **high** | Double | `high` | `最高` |
| **low** | Double | `low` | `最低` |
| **close** | Double | `close` | `收盘` |
| **vol** | Double | `vol` | `成交量` |
| **amount** | Double | `amount` (*1000) | `成交额` |

### 2.2 分钟行情 (`stock_minute`)
*   **TU接口**: `stk_mins`
*   **AK接口**: `stock_zh_a_hist_min_em`

| 统一字段 | 类型 | TU 来源字段 | AK 来源字段 |
| :--- | :--- | :--- | :--- |
| **ts_code** | String | `ts_code` | (需补充) |
| **trade_time** | String | `trade_time` | `时间` |
| **open** | Double | `open` | `开盘` |
| **close** | Double | `close` | `收盘` |
| **vol** | Double | `vol` | `成交量` |

### 2.3 每日指标 (`stock_daily_indicator`)
*   **TU接口**: `daily_basic`
*   **AK接口**: 暂无直接对应接口，主要依赖TU

| 统一字段 | 类型 | TU 来源字段 | 备注 |
| :--- | :--- | :--- | :--- |
| **pe_ttm** | Double | `pe_ttm` | 市盈率TTM |
| **pb** | Double | `pb` | 市净率 |
| **total_mv** | Double | `total_mv` | 总市值 |
| **turnover_rate**| Double| `turnover_rate`| 换手率 |

---

## 三、财务数据类

### 3.1 财务报表 (`financial_income` / `_balance` / `_cashflow`)
*   **TU接口**: `income`, `balancesheet`, `cashflow`
*   **AK接口**: `stock_financial_report_sina_*`
*   **清洗规则**:
    *   AK的报表数据通常由中文列名组成，需建立严格的 `中文 -> 英文` 映射字典。

| 统一字段 | TU 来源字段 | AK 来源字段 (示例) |
| :--- | :--- | :--- |
| **end_date** | `end_date` | `报告日` |
| **revenue** | `total_revenue`| `营业收入` |
| **net_profit** | `n_income` | `净利润` |

### 3.2 财务指标 (`financial_indicator`)
*   **TU接口**: `fina_indicator`
*   **AK接口**: `stock_financial_analysis_indicator_em`

| 统一字段 | TU 来源字段 | AK 来源字段 |
| :--- | :--- | :--- |
| **roe** | `roe` | `ROEJQ` |
| **gross_margin** | `gross_margin` | `XSMLL` |

---

## 四、市场数据类

### 4.1 资金流向 (`stock_money_flow`)
*   **TU接口**: `moneyflow`
*   **AK接口**: `stock_individual_fund_flow`
*   **清洗规则**:
    *   AK的 `净流入` 单位需确认（通常为元或万元），TU为手或万元，需统一。

| 统一字段 | TU 来源字段 | AK 来源字段 |
| :--- | :--- | :--- |
| **net_mf_vol** | `net_mf_vol` | `主力净流入` |

### 4.2 沪深港通资金 (`stock_money_flow_hsgt`)
*   **TU接口**: `moneyflow_hsgt`
*   **AK接口**: `stock_hsgt_hist_em`

| 统一字段 | TU 来源字段 | AK 来源字段 |
| :--- | :--- | :--- |
| **north_money** | `north_money` | `当日成交净买额` |

### 4.3 龙虎榜 (`market_top_list`)
*   **TU接口**: `top_list`
*   **AK接口**: `stock_lhb_detail_em`

| 统一字段 | TU 来源字段 | AK 来源字段 |
| :--- | :--- | :--- |
| **net_amount** | `net_amount` | `龙虎榜净买额` |

### 4.4 融资融券 (`stock_margin`)
*   **TU接口**: `margin_detail`
*   **AK接口**: `stock_margin_detail_*`

| 统一字段 | TU 来源字段 | AK 来源字段 |
| :--- | :--- | :--- |
| **rzye** | `rzye` | `融资余额` |

### 4.5 板块行情 (`market_board_daily`)
*   **AK接口**: `stock_board_industry_name_em`

| 统一字段 | AK 来源字段 |
| :--- | :--- |
| **board_name** | `板块名称` |
| **pct_chg** | `涨跌幅` |

---

## 五、其他数据类

### 5.1 分红配送 (`stock_dividend`)
*   **TU接口**: `dividend`
*   **AK接口**: `stock_history_dividend_detail`

| 统一字段 | TU 来源字段 | AK 来源字段 |
| :--- | :--- | :--- |
| **stk_div** | `stk_div` | `送股` + `转增` |

### 5.2 宏观经济 (`macro_economy`)
*   **数据源**: 多源混合
*   **存储方式**: Key-Value 宽表

| 统一字段 | 说明 |
| :--- | :--- |
| **indicator** | 指标名 (如 PMI, CPI) |
| **value** | 数值 |

### 5.3 新闻资讯 (`market_news`)
*   **TU接口**: `news`
*   **AK接口**: `stock_news_em`

| 统一字段 | TU 来源字段 | AK 来源字段 |
| :--- | :--- | :--- |
| **title** | `title` | `新闻标题` |
| **content** | `content` | `新闻内容` |
