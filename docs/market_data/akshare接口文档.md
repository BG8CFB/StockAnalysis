# AKShare 数据源接口文档

## 📌 数据源简介

**AKShare** 是基于 Python 的开源财经数据接口库，旨在实现对股票、期货、期权、基金、外汇、债券、指数、加密货币等金融产品的基本面数据、实时和历史行情数据、衍生数据的获取。

### 核心特性

- ✅ **免费开源**：完全免费，无需 API Key
- ✅ **数据覆盖广**：支持 A 股、港股、美股等多个市场
- ✅ **接口丰富**：提供 1000+ 接口，涵盖实时行情、历史数据、财务报表、技术指标等
- ✅ **简单易用**：统一接口设计，返回 pandas DataFrame 格式
- ✅ **持续更新**：活跃的社区维护，频繁更新接口

### 官方资源

- **官方文档**：https://akshare.akfamily.xyz/
- **GitHub 仓库**：https://github.com/akfamily/akshare
- **数据字典**：https://akshare.akfamily.xyz/data/index.html
- **答疑专栏**：https://akshare.akfamily.xyz/answer.html

---

## 📦 安装与配置

### 安装

```bash
pip install akshare
```

或使用 Poetry：

```bash
poetry add akshare
```

### 基本使用

```python
import akshare as ak

# 获取 A 股实时行情
df = ak.stock_zh_a_spot_em()

# 查看数据
print(df.head())
```

---

## 🇨🇳 A 股接口

### 1. 实时行情数据

#### 1.1 沪深京 A 股实时行情

**接口名称**：`stock_zh_a_spot_em()`

**测试状态**：✅ 已测试可用 (2025-01-02测试，响应时间 13.40s)

**功能描述**：获取沪深京 A 股所有上市公司的实时行情数据

**数据源**：东方财富网

**请求参数**：无

**返回字段**：

| 字段名 | 说明 | 字段名 | 说明 |
|--------|------|--------|------|
| 代码 | 股票代码 | 名称 | 股票名称 |
| 最新价 | 最新成交价 | 涨跌幅 | 涨跌幅百分比 |
| 涨跌额 | 涨跌金额 | 成交量 | 成交量（手） |
| 成交额 | 成交额（元） | 振幅 | 振幅百分比 |
| 最高 | 最高价 | 最低 | 最低价 |
| 今开 | 今开价 | 昨收 | 昨收价 |
| 量比 | 量比 | 换手率 | 换手率 |
| 市盈率-动态 | 动态市盈率 | 市净率 | 市净率 |

**示例代码**：

```python
import akshare as ak

# 获取所有 A 股实时行情
df = ak.stock_zh_a_spot_em()

# 筛选特定股票
stock_info = df[df['代码'] == '000001']
print(stock_info)
```

**注意事项**：
- 数据更新频率：实时
- 建议在交易时间内调用
- 大量请求可能触发限流

---

#### 1.2 个股实时分时数据

**接口名称**：`stock_zh_a_spot_em()`

**功能描述**：获取单个股票的分时成交数据

**数据源**：东方财富网

**请求参数**：无（返回所有股票）

**替代方案**：使用 `stock_zh_a_tick_tx()` 获取个股分时

**示例代码**：

```python
import akshare as ak

# 获取个股分时数据（腾讯接口）
df = ak.stock_zh_a_tick_tx(symbol="000001", period="1")
print(df.head())
```

---

### 2. 历史行情数据

#### 2.1 个股历史日线数据

**接口名称**：`stock_zh_a_hist()`

**测试状态**：✅ 已测试可用 (2025-01-02测试，响应时间 0.41s)

**功能描述**：获取沪深 A 股个股历史日线行情数据

**数据源**：东方财富网

**请求参数**：

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| symbol | str | 股票代码（如 "000001"） | - |
| period | str | 数据周期：daily, weekly, monthly | "daily" |
| start_date | str | 开始日期 "19900101" | "19900101" |
| end_date | str | 结束日期 "21000101" | "21000101" |
| adjust | str | 复权类型："" 不复权, "qfq" 前复权, "hfq" 后复权 | "" |

**返回字段**：

| 字段名 | 说明 |
|--------|------|
| 日期 | 交易日期 |
| 开盘 | 开盘价 |
| 收盘 | 收盘价 |
| 最高 | 最高价 |
| 最低 | 最低价 |
| 成交量 | 成交量（手） |
| 成交额 | 成交额（元） |
| 振幅 | 振幅百分比 |
| 涨跌幅 | 涨跌幅百分比 |
| 涨跌额 | 涨跌金额 |
| 换手率 | 换手率 |

**示例代码**：

```python
import akshare as ak

# 获取平安银行历史日线数据（前复权）
df = ak.stock_zh_a_hist(
    symbol="000001",
    period="daily",
    start_date="20200101",
    end_date="20241231",
    adjust="qfq"
)

print(df.head())

# 导出为 CSV
df.to_csv("000001_hist.csv", index=False, encoding="utf-8-sig")
```

**注意事项**：
- 单次请求可能被限流，建议添加延时
- 历史数据量大时建议分批获取
- 前复权数据适合技术分析
- 后复权数据适合计算真实收益

---

#### 2.2 历史分钟数据

**接口名称**：`stock_zh_a_hist_min_em()`

**功能描述**：获取 A 股个股分钟级别历史数据

**数据源**：东方财富网

**请求参数**：

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| symbol | str | 股票代码 | - |
| period | str | 周期：1, 5, 15, 30, 60 | "1" |
| adjust | str | 复权类型 | "" |
| start_date | str | 开始时间戳 | - |
| end_date | str | 结束时间戳 | - |

**示例代码**：

```python
import akshare as ak
import time

# 获取 1 分钟级别数据
df = ak.stock_zh_a_hist_min_em(
    symbol="000001",
    period="1",
    adjust="",
    start_date="1735689600000",  # 时间戳
    end_date="1735776000000"
)

print(df.head())
```

---

### 3. 财务数据

#### 3.1 财务报表数据

**接口名称**：`stock_balance_sheet_by_report_em()` / `stock_profit_sheet_by_report_em()` / `stock_cash_flow_sheet_by_report_em()`

**测试状态**：❌ 已测试失败 (2025-01-02测试，返回 NoneType 错误)

**功能描述**：获取资产负债表、利润表、现金流量表

**数据源**：东方财富网

**请求参数**：

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| symbol | str | 股票代码 | - |
| period | str | 报告期类型：quarter, annual | "quarter" |

**示例代码**：

```python
import akshare as ak

# 获取资产负债表
balance_sheet = ak.stock_balance_sheet_by_report_em(
    symbol="000001",
    period="quarter"
)

# 获取利润表
profit_sheet = ak.stock_profit_sheet_by_report_em(
    symbol="000001",
    period="quarter"
)

# 获取现金流量表
cash_flow = ak.stock_cash_flow_sheet_by_report_em(
    symbol="000001",
    period="quarter"
)

print(balance_sheet.head())
```

---

#### 3.2 财务指标

**接口名称**：`stock_financial_abstract()`

**功能描述**：获取主要财务指标摘要

**数据源**：东方财富网

**返回字段**：

| 字段名 | 说明 |
|--------|------|
| 报告期 | 财务报告期 |
| 每股净资产 | 每股净资产（元） |
| 净利润 | 净利润（元） |
| 净资产收益率 | ROE |
| 总资产 | 总资产（元） |
| 总负债 | 总负债（元） |

**示例代码**：

```python
import akshare as ak

# 获取财务指标
df = ak.stock_financial_abstract(symbol="000001")
print(df.head())
```

---

#### 3.3 估值指标

**接口名称**：`stock_a_lg_indicator()`

**功能描述**：获取 A 股历史估值指标

**返回字段**：

| 字段名 | 说明 |
|--------|------|
| 日期 | 日期 |
| 总市值 | 总市值（元） |
| 市盈率-TTM | 滚动市盈率 |
| 市盈率-静 | 静态市盈率 |
| 市净率 | 市净率 |
| 市现率 | 市现率 |

**示例代码**：

```python
import akshare as ak

# 获取估值指标
df = ak.stock_a_lg_indicator(symbol="sh000001")
print(df.head())
```

---

### 4. 技术指标

AKShare 本身不提供技术指标计算，但可以结合 `ta` 库或 `pandas` 进行计算。

#### 4.1 使用 ta 库计算技术指标

```python
import akshare as ak
import ta

# 获取历史数据
df = ak.stock_zh_a_hist(symbol="000001", period="daily", adjust="qfq")

# 计算 MACD
df['MACD'] = ta.trend.MACD(df['收盘'])['MACD']
df['MACD_Signal'] = ta.trend.MACD(df['收盘'])['MACD_Signal']
df['MACD_Diff'] = ta.trend.MACD(df['收盘'])['MACD_Diff']

# 计算 RSI
df['RSI'] = ta.momentum.RSIIndicator(df['收盘']).rsi()

# 计算布林带
bollinger = ta.volatility.BollingerBands(df['收盘'])
df['BB_High'] = bollinger.bollinger_hband()
df['BB_Mid'] = bollinger.bollinger_mavg()
df['BB_Low'] = bollinger.bollinger_lband()

# 计算 KDJ
df['K'] = ta.momentum.StochasticOscillator(df['最高'], df['最低'], df['收盘']).stoch()
df['D'] = ta.momentum.StochasticOscillator(df['最高'], df['最低'], df['收盘']).stoch_signal()

print(df[['日期', '收盘', 'MACD', 'RSI', 'BB_High', 'BB_Low']].tail())
```

---

### 5. 股票基本信息

#### 5.1 个股基本信息

**接口名称**：`stock_individual_info_em()`

**功能描述**：获取个股基本信息（公司资料、主营业务等）

**数据源**：东方财富网

**请求参数**：

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| symbol | str | 股票代码 | - |

**示例代码**：

```python
import akshare as ak

# 获取平安银行基本信息
df = ak.stock_individual_info_em(symbol="000001")
print(df)
```

---

#### 5.2 A股代码和名称

**接口名称**：`stock_info_a_code_name()`

**功能描述**：获取所有 A 股代码和名称列表

**示例代码**：

```python
import akshare as ak

# 获取 A 股代码列表
df = ak.stock_info_a_code_name()
print(df.head())
```

---

### 6. 板块行业数据

#### 6.1 概念板块名称列表

**接口名称**：`stock_board_concept_name_em()`

**测试状态**：✅ 已测试可用 (2025-01-02测试，响应时间 1.02s)

**功能描述**：获取所有概念板块名称

**数据源**：东方财富网

**示例代码**：

```python
import akshare as ak

# 获取概念板块列表
df = ak.stock_board_concept_name_em()
print(df.head())
```

---

#### 6.2 行业板块名称列表

**接口名称**：`stock_board_industry_name_em()`

**测试状态**：✅ 已测试可用 (2025-01-02测试，响应时间 0.19s)

**功能描述**：获取所有行业板块名称

**数据源**：东方财富网

**示例代码**：

```python
import akshare as ak

# 获取行业板块列表
df = ak.stock_board_industry_name_em()
print(df.head())
```

---

#### 6.3 概念板块实时行情

**接口名称**：`stock_board_concept_spot_em()`

**功能描述**：获取概念板块实时行情

**数据源**：东方财富网

**请求参数**：

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| board | str | 板块名称 | - |

**示例代码**：

```python
import akshare as ak

# 获取人工智能概念板块行情
df = ak.stock_board_concept_spot_em(board="人工智能")
print(df.head())
```

---

#### 6.4 行业板块实时行情

**接口名称**：`stock_board_industry_spot_em()`

**功能描述**：获取行业板块实时行情

**数据源**：东方财富网

**示例代码**：

```python
import akshare as ak

# 获取银行行业板块行情
df = ak.stock_board_industry_spot_em(board="银行")
print(df.head())
```

---

#### 6.5 概念板块成份股

**接口名称**：`stock_board_concept_cons_em()`

**功能描述**：获取概念板块的成份股列表

**数据源**：东方财富网

**请求参数**：

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| symbol | str | 板块名称 | - |

**示例代码**：

```python
import akshare as ak

# 获取人工智能概念板块成份股
df = ak.stock_board_concept_cons_em(symbol="人工智能")
print(df.head())
```

---

#### 6.6 行业板块成份股

**接口名称**：`stock_board_industry_cons_em()`

**功能描述**：获取行业板块的成份股列表

**数据源**：东方财富网

**示例代码**：

```python
import akshare as ak

# 获取银行行业板块成份股
df = ak.stock_board_industry_cons_em(symbol="银行")
print(df.head())
```

---

### 7. 龙虎榜数据

#### 7.1 龙虎榜成交明细

**接口名称**：`stock_lhb_detail_em()`

**测试状态**：❌ 已测试失败 (2025-01-02测试，返回 NoneType 错误)

**功能描述**：获取龙虎榜成交明细数据

**数据源**：东方财富网

**请求参数**：

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| date | str | 交易日期 "20240101" | 当前日期 |

**示例代码**：

```python
import akshare as ak

# 获取指定日期的龙虎榜明细
df = ak.stock_lhb_detail_em(date="20240101")
print(df.head())
```

---

#### 7.2 个股龙虎榜明细

**接口名称**：`stock_lhb_stock_detail_em()`

**功能描述**：获取单个股票的龙虎榜明细

**数据源**：东方财富网

**请求参数**：

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| symbol | str | 股票代码 | - |

**示例代码**：

```python
import akshare as ak

# 获取个股龙虎榜明细
df = ak.stock_lhb_stock_detail_em(symbol="000001")
print(df.head())
```

---

### 8. 股东信息

#### 8.1 十大股东

**接口名称**：`stock_main_stock_holder()`

**功能描述**：获取十大股东信息

**示例代码**：

```python
import akshare as ak

# 获取十大股东
df = ak.stock_main_stock_holder(symbol="000001", symbol_cn="平安银行")
print(df.head())
```

---

#### 8.2 十大流通股东

**接口名称**：`stock_gdfx_top_10_em()`

**测试状态**：❌ 已测试失败 (2025-01-02测试，返回 'sdgd' 错误)

**功能描述**：获取十大流通股东信息

**数据源**：东方财富网

**请求参数**：

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| symbol | str | 股票代码 | - |

**示例代码**：

```python
import akshare as ak

# 获取十大流通股东
df = ak.stock_gdfx_top_10_em(symbol="000001")
print(df.head())
```

---

#### 8.3 股东户数

**接口名称**：`stock_zh_a_gdhs()`

**功能描述**：获取 A 股股东户数历史数据

**示例代码**：

```python
import akshare as ak

# 获取股东户数
df = ak.stock_zh_a_gdhs(symbol="000001")
print(df.head())
```

---

### 9. 资金流向

#### 9.1 个股资金流向

**接口名称**：`stock_individual_fund_flow()`

**功能描述**：获取个股资金流向数据

**请求参数**：

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| symbol | str | 股票代码 | - |
| indicator | str | 指标：主力资金, 超大单, 大单, 中单, 小单 | "主力资金" |

**示例代码**：

```python
import akshare as ak

# 获取个股主力资金流向
df = ak.stock_individual_fund_flow(symbol="000001", indicator="主力资金")
print(df.head())
```

---

#### 9.2 个股资金流向（东方财富）

**接口名称**：`stock_fund_flow_individual()`

**功能描述**：获取个股资金流向（东方财富）

**数据源**：东方财富网

**请求参数**：

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| symbol | str | 股票代码 | - |

**示例代码**：

```python
import akshare as ak

# 获取个股资金流向
df = ak.stock_fund_flow_individual(symbol="000001")
print(df.head())
```

---

#### 9.3 概念板块资金流向

**接口名称**：`stock_fund_flow_concept()`

**功能描述**：获取概念板块资金流向

**数据源**：东方财富网

**请求参数**：

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| symbol | str | 板块名称 | - |
| date | str | 日期 "20240101" | 当前日期 |

**示例代码**：

```python
import akshare as ak

# 获取人工智能板块资金流向
df = ak.stock_fund_flow_concept(symbol="人工智能")
print(df.head())
```

---

#### 9.4 行业板块资金流向

**接口名称**：`stock_fund_flow_industry()`

**功能描述**：获取行业板块资金流向

**数据源**：东方财富网

**示例代码**：

```python
import akshare as ak

# 获取银行行业资金流向
df = ak.stock_fund_flow_industry(symbol="银行")
print(df.head())
```

---

### 10. 业绩预告

**接口名称**：`stock_profit_forecast_em()`

**功能描述**：获取上市公司业绩预告

**数据源**：东方财富网

**示例代码**：

```python
import akshare as ak

# 获取业绩预告
df = ak.stock_profit_forecast_em()
print(df.head())
```

---

### 11. 研报

**接口名称**：`stock_research_report_em()`

**功能描述**：获取券商研报列表

**数据源**：东方财富网

**请求参数**：

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| symbol | str | 股票代码 | - |
| page | int | 页码 | 1 |

**示例代码**：

```python
import akshare as ak

# 获取个股研报
df = ak.stock_research_report_em(symbol="000001", page=1)
print(df.head())
```

---

### 12. 融资融券

#### 12.1 沪市融资融券

**接口名称**：`stock_margin_sse()`

**测试状态**：✅ 已测试可用 (2025-01-02测试，响应时间 0.56s)

**功能描述**：获取沪市融资融券数据

**示例代码**：

```python
import akshare as ak

# 获取沪市融资融券汇总
df = ak.stock_margin_sse()
print(df.head())
```

---

#### 12.2 深市融资融券

**接口名称**：`stock_margin_szse()`

**测试状态**：✅ 已测试可用 (2025-01-02测试，响应时间 0.27s)

**功能描述**：获取深市融资融券数据

**示例代码**：

```python
import akshare as ak

# 获取深市融资融券汇总
df = ak.stock_margin_szse()
print(df.head())
```

---

### 13. 新股数据

#### 13.1 新股申购

**接口名称**：`stock_new_a_spot_em()`

**测试状态**：✅ 已测试可用 (2025-01-02测试，响应时间 0.17s)

**功能描述**：获取新股申购信息

**数据源**：东方财富网

**示例代码**：

```python
import akshare as ak

# 获取新股申购信息
df = ak.stock_new_a_spot_em()
print(df.head())
```

---

#### 13.2 IPO信息

**接口名称**：`stock_ipo_info()`

**功能描述**：获取 IPO 信息

**示例代码**：

```python
import akshare as ak

# 获取 IPO 信息
df = ak.stock_ipo_info()
print(df.head())
```

---

### 14. 北交所/科创板

#### 14.1 北交所实时行情

**接口名称**：`stock_bj_a_spot_em()`

**功能描述**：获取北交所实时行情

**数据源**：东方财富网

**示例代码**：

```python
import akshare as ak

# 获取北交所实时行情
df = ak.stock_bj_a_spot_em()
print(df.head())
```

---

#### 14.2 科创板实时行情

**接口名称**：`stock_kc_a_spot_em()`

**功能描述**：获取科创板实时行情

**数据源**：东方财富网

**示例代码**：

```python
import akshare as ak

# 获取科创板实时行情
df = ak.stock_kc_a_spot_em()
print(df.head())
```

---

### 15. 其他重要数据

#### 15.1 股票质押

**接口名称**：`stock_gpzy_profile_em()`

**功能描述**：获取股票质押信息

**数据源**：东方财富网

**请求参数**：

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| symbol | str | 股票代码 | - |

**示例代码**：

```python
import akshare as ak

# 获取股票质押信息
df = ak.stock_gpzy_profile_em(symbol="000001")
print(df.head())
```

---

#### 15.2 限售股解禁

**接口名称**：`stock_restricted_release_summary_em()`

**功能描述**：获取限售股解禁汇总

**数据源**：东方财富网

**示例代码**：

```python
import akshare as ak

# 获取限售股解禁汇总
df = ak.stock_restricted_release_summary_em()
print(df.head())
```

---

### 16. 市场概况

#### 16.1 涨跌停统计

**接口名称**：`stock_zh_a_spot_em()` 筛选

**示例代码**：

```python
import akshare as ak

# 获取实时行情
df = ak.stock_zh_a_spot_em()

# 涨停股票（涨幅 >= 9.9%）
limit_up = df[df['涨跌幅'] >= 9.9]
print(f"涨停股票数：{len(limit_up)}")

# 跌停股票（跌幅 <= -9.9%）
limit_down = df[df['涨跌幅'] <= -9.9]
print(f"跌停股票数：{len(limit_down)}")

# 涨幅榜前 10
top_gainers = df.nlargest(10, '涨跌幅')
print("涨幅榜 TOP10：")
print(top_gainers[['代码', '名称', '涨跌幅', '最新价']])
```

---

#### 5.2 沪深港通资金流向

**接口名称**：`stock_hsgt_fund_flow_summary_em()`

**功能描述**：获取沪深港通资金流向汇总

**示例代码**：

```python
import akshare as ak

# 获取资金流向
df = ak.stock_hsgt_fund_flow_summary_em()
print(df.head())
```

---

## 🇭🇰 港股接口

### 1. 实时行情

#### 1.1 港股实时行情

**接口名称**：`stock_hk_spot()`

**测试状态**：✅ 已测试可用 (2025-01-02测试，响应时间 10.22s)

**功能描述**：获取港股实时行情数据

**数据源**：腾讯证券

**请求参数**：无

**返回字段**：

| 字段名 | 说明 |
|--------|------|
| 代码 | 港股代码 |
| 名称 | 股票名称 |
| 最新价 | 最新成交价 |
| 涨跌额 | 涨跌金额 |
| 涨跌幅 | 涨跌幅百分比 |
| 成交量 | 成交量 |
| 成交额 | 成交额 |

**示例代码**：

```python
import akshare as ak

# 获取港股实时行情
df = ak.stock_hk_spot()
print(df.head())

# 筛选腾讯控股
tencent = df[df['代码'] == '00700']
print(tencent)
```

---

### 2. 历史行情

#### 2.1 港股历史日线数据

**接口名称**：`stock_hk_daily()`

**功能描述**：获取港股历史日线数据

**数据源**：腾讯证券 / 东方财富网

**请求参数**：

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| symbol | str | 港股代码（如 "00700"） | - |
| start_date | str | 开始日期 "19900101" | "19900101" |
| end_date | str | 结束日期 "21000101" | "21000101" |
| adjust | str | 复权类型："" 不复权, "qfq" 前复权, "hfq" 后复权 | "" |

**示例代码**：

```python
import akshare as ak

# 获取腾讯控股历史数据（前复权）
df = ak.stock_hk_daily(
    symbol="00700",
    start_date="20200101",
    end_date="20241231",
    adjust="qfq"
)

print(df.head())
```

---

#### 2.2 港股历史分钟数据

**接口名称**：`stock_hk_hist_min_em()`

**测试状态**：✅ 已测试可用 (2025-01-02测试，响应时间 0.26s)

**功能描述**：获取港股分钟级别数据

**示例代码**：

```python
import akshare as ak

# 获取腾讯 1 分钟数据
df = ak.stock_hk_hist_min_em(
    symbol="00700",
    period="1",
    adjust=""
)

print(df.head())
```

---

### 3. 港股通数据

#### 3.1 港股通成份股

**接口名称**：`stock_hk_ggt_components_em()`

**测试状态**：✅ 已测试可用 (2025-01-02测试，响应时间 1.24s)

**功能描述**：获取港股通成份股列表

**数据源**：东方财富网

**返回字段**：

| 字段名 | 说明 |
|--------|------|
| 代码 | 港股代码 |
| 名称 | 股票名称 |
| 最新价 | 最新价 |
| 涨跌幅 | 涨跌幅 |
| 成交量 | 成交量 |
| 是否港股通 | 是否属于港股通 |

**示例代码**：

```python
import akshare as ak

# 获取港股通成份股
df = ak.stock_hk_ggt_components_em()
print(df.head())
```

---

### 4. 港股财务数据

#### 4.1 港股财务指标

**接口名称**：`stock_hk_financial_indicator_em()`

**测试状态**：✅ 已测试可用 (2025-01-02测试，响应时间 0.14s)

**功能描述**：获取港股财务指标数据

**数据源**：东方财富网

**请求参数**：

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| symbol | str | 港股代码 | - |

**示例代码**：

```python
import akshare as ak

# 获取腾讯财务指标
df = ak.stock_hk_financial_indicator_em(symbol="00700")
print(df.head())
```

---

#### 4.2 港股财务报表

**接口名称**：`stock_financial_hk_report_em()`

**功能描述**：获取港股三大财务报表

**数据源**：东方财富网

**示例代码**：

```python
import akshare as ak

# 获取港股财务报表
df = ak.stock_financial_hk_report_em(symbol="00700")
print(df.head())
```

---

### 5. 港股指数

#### 5.1 港股指数实时行情

**接口名称**：`stock_hk_index_spot_em()`

**测试状态**：✅ 已测试可用 (2025-01-02测试，响应时间 0.68s)

**功能描述**：获取港股主要指数实时行情

**数据源**：东方财富网

**示例代码**：

```python
import akshare as ak

# 获取港股指数行情
df = ak.stock_hk_index_spot_em()
print(df.head())
```

---

#### 5.2 港股指数历史数据

**接口名称**：`stock_hk_index_daily_em()`

**功能描述**：获取港股指数历史数据

**数据源**：东方财富网

**示例代码**：

```python
import akshare as ak

# 获取恒生指数历史数据
df = ak.stock_hk_index_daily_em(symbol="恒生指数")
print(df.head())
```

---

### 6. 港股通明细

#### 6.1 港股通历史资金流向

**接口名称**：`stock_hsgt_hist_em()`

**功能描述**：获取港股通历史资金流向

**数据源**：东方财富网

**请求参数**：

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| symbol | str | 股票代码 | - |

**示例代码**：

```python
import akshare as ak

# 获取港股通资金流向
df = ak.stock_hsgt_hist_em(symbol="000001")
print(df.head())
```

---

#### 6.2 港股通持股明细

**接口名称**：`stock_hsgt_hold_stock_em()`

**测试状态**：✅ 已测试可用 (2025-01-02测试，响应时间 1.64s)

**功能描述**：获取港股通持股明细

**数据源**：东方财富网

**示例代码**：

```python
import akshare as ak

# 获取港股通持股明细
df = ak.stock_hsgt_hold_stock_em()
print(df.head())
```

---

### 7. 港股个股指标

**接口名称**：`stock_hk_eniu_indicator()`

**功能描述**：获取港股个股估值指标

**返回字段**：

| 字段名 | 说明 |
|--------|------|
| 市盈率 | 市盈率 |
| 市净率 | 市净率 |
| 股息率 | 股息率 |
| ROE | 净资产收益率 |
| 总市值 | 总市值 |

**示例代码**：

```python
import akshare as ak

# 获取港股指标
df = ak.stock_hk_eniu_indicator(symbol="00700")
print(df)
```

---

## 🇺🇸 美股接口

### 1. 美股基本信息

#### 1.1 美股个股基本信息

**接口名称**：`stock_individual_basic_info_us_xq()`

**功能描述**：获取美股个股基本信息（雪球）

**示例代码**：

```python
import akshare as ak

# 获取美股基本信息
df = ak.stock_individual_basic_info_us_xq(symbol="AAPL")
print(df.head())
```

---

### 2. 美股财务数据

#### 2.1 美股财务分析指标

**接口名称**：`stock_financial_us_analysis_indicator_em()`

**测试状态**：✅ 已测试可用 (2025-01-02测试，响应时间 0.29s)

**功能描述**：获取美股财务分析指标

**数据源**：东方财富网

**请求参数**：

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| symbol | str | 美股代码 | - |

**示例代码**：

```python
import akshare as ak

# 获取苹果财务指标
df = ak.stock_financial_us_analysis_indicator_em(symbol="AAPL")
print(df.head())
```

---

#### 2.2 美股财务报表

**接口名称**：`stock_financial_us_report_em()`

**测试状态**：✅ 已测试可用 (2025-01-02测试，响应时间 0.72s)

**功能描述**：获取美股三大财务报表

**数据源**：东方财富网

**示例代码**：

```python
import akshare as ak

# 获取美股财务报表
df = ak.stock_financial_us_report_em(symbol="AAPL")
print(df.head())
```

---

### 3. 美股实时行情

#### 3.1 美股实时行情

**接口名称**：`stock_us_spot()`

**测试状态**：✅ 已测试可用 (2025-01-02测试，响应时间 28.26s)

**功能描述**：获取美股实时行情数据

**数据源**：新浪财经 / 东方财富网

**请求参数**：无

**返回字段**：

| 字段名 | 说明 |
|--------|------|
| symbol | 股票代码 |
| name | 股票名称 |
| current_price | 最新价 |
| open_price | 开盘价 |
| high_price | 最高价 |
| low_price | 最低价 |
| volume | 成交量 |
| market_cap | 市值 |

**示例代码**：

```python
import akshare as ak

# 获取美股实时行情
df = ak.stock_us_spot()
print(df.head())

# 筛选苹果公司
apple = df[df['symbol'] == 'AAPL']
print(apple)
```

---

#### 1.2 美股股票代码列表

**接口名称**：`get_us_stock_name()`

**测试状态**：✅ 已测试可用 (2025-01-02测试，响应时间 438.47s，接口较慢)

**功能描述**：获取美股所有股票代码和名称

**示例代码**：

```python
import akshare as ak

# 获取美股代码列表
df = ak.get_us_stock_name()
print(df.head())
```

---

#### 1.3 中概股行情

**接口名称**：`stock_us_zh_spot()`

**功能描述**：获取中概股实时行情

**示例代码**：

```python
import akshare as ak

# 获取中概股行情
df = ak.stock_us_zh_spot()
print(df.head())
```

---

### 2. 历史行情

#### 2.1 美股历史日线数据

**接口名称**：`stock_us_daily()`

**测试状态**：❌ 已测试失败 (2025-01-02测试，参数错误：got an unexpected keyword argument，需要更新调用方式)

**功能描述**：获取美股历史日线数据（前复权）

**数据源**：新浪财经

**请求参数**：

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| symbol | str | 美股代码（如 "AAPL"） | - |
| start_date | str | 开始日期 "19900101" | "19900101" |
| end_date | str | 结束日期 "21000101" | "21000101" |

**返回字段**：

| 字段名 | 说明 |
|--------|------|
| date | 日期 |
| open | 开盘价 |
| high | 最高价 |
| low | 最低价 |
| close | 收盘价 |
| volume | 成交量 |

**示例代码**：

```python
import akshare as ak

# 获取苹果公司历史数据
df = ak.stock_us_daily(
    symbol="AAPL",
    start_date="20200101",
    end_date="20241231"
)

print(df.head())
```

---

#### 2.2 美股历史分钟数据

**接口名称**：`stock_us_hist_min_em()`

**功能描述**：获取美股分钟级别数据

**示例代码**：

```python
import akshare as ak

# 获取 1 分钟数据
df = ak.stock_us_hist_min_em(
    symbol="AAPL",
    period="1",
    adjust=""
)

print(df.head())
```

---

### 3. 美股指数

#### 3.1 美股指数行情

**接口名称**：`index_us_stock_sina()`

**测试状态**：✅ 已测试可用 (2025-01-02测试，响应时间 0.31s)

**功能描述**：获取美股主要指数行情

**返回指数**：道琼斯、纳斯达克、标普500等

**示例代码**：

```python
import akshare as ak

# 获取美股指数
df = ak.index_us_stock_sina(symbol=".INX")
print(df)
```

---

## 📈 指数数据接口

### 1. A股指数

#### 1.1 A股指数实时行情

**接口名称**：`stock_zh_index_spot_em()`

**测试状态**：✅ 已测试可用 (2025-01-02测试，响应时间 0.54s)

**功能描述**：获取 A 股主要指数实时行情

**数据源**：东方财富网

**示例代码**：

```python
import akshare as ak

# 获取 A 股指数实时行情
df = ak.stock_zh_index_spot_em()
print(df.head())
```

---

#### 1.2 A股指数历史数据

**接口名称**：`stock_zh_index_daily_em()`

**测试状态**：✅ 已测试可用 (2025-01-02测试，响应时间 0.18s)

**功能描述**：获取 A 股指数历史日线数据

**数据源**：东方财富网

**请求参数**：

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| symbol | str | 指数代码（如 "sh000001"） | - |
| start_date | str | 开始日期 "19900101" | "19900101" |
| end_date | str | 结束日期 "21000101" | "21000101" |

**示例代码**：

```python
import akshare as ak

# 获取上证指数历史数据
df = ak.stock_zh_index_daily_em(
    symbol="sh000001",
    start_date="20200101",
    end_date="20241231"
)
print(df.head())
```

---

#### 1.3 指数成份股

**接口名称**：`index_stock_cons_sina()`

**功能描述**：获取指数成份股列表

**数据源**：新浪财经

**请求参数**：

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| symbol | str | 指数代码 | - |

**示例代码**：

```python
import akshare as ak

# 获取上证50成份股
df = ak.index_stock_cons_sina(symbol="sh000016")
print(df.head())
```

---

#### 1.4 指数成份股权重

**接口名称**：`index_stock_cons_weight_csindex()`

**功能描述**：获取指数成份股权重

**数据源**：中证指数

**请求参数**：

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| symbol | str | 指数代码 | - |

**示例代码**：

```python
import akshare as ak

# 获取沪深300成份股权重
df = ak.index_stock_cons_weight_csindex(symbol="000300")
print(df.head())
```

---

### 2. 港股指数

#### 2.1 港股指数实时行情

**接口名称**：`stock_hk_index_spot_em()`

**功能描述**：获取港股主要指数实时行情

**数据源**：东方财富网

**示例代码**：

```python
import akshare as ak

# 获取港股指数实时行情
df = ak.stock_hk_index_spot_em()
print(df.head())
```

---

### 3. 美股指数

#### 3.1 美股指数行情

**接口名称**：`index_us_stock_sina()`

**功能描述**：获取美股主要指数行情

**数据源**：新浪财经

**请求参数**：

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| symbol | str | 指数代码 | ".INX" |

**示例代码**：

```python
import akshare as ak

# 获取标普500指数
df = ak.index_us_stock_sina(symbol=".INX")
print(df)

# 获取道琼斯指数
df = ak.index_us_stock_sina(symbol=".DJI")
print(df)

# 获取纳斯达克指数
df = ak.index_us_stock_sina(symbol=".IXIC")
print(df)
```

---

## ⚠️ 限流与注意事项

### 1. 请求频率限制

AKShare 本身不强制限流，但依赖的第三方数据源（如东方财富、新浪财经）有反爬机制。

**建议策略**：
- 单个接口请求间隔：0.5-1 秒
- 批量请求时添加随机延时
- 避免在短时间内重复请求相同数据

**示例代码**：

```python
import akshare as ak
import time
import random

stocks = ["000001", "000002", "000003", "600000", "600036"]

for stock in stocks:
    try:
        df = ak.stock_zh_a_hist(symbol=stock, period="daily", adjust="qfq")
        print(f"获取 {stock} 成功")
        # 随机延时 0.5-1.5 秒
        time.sleep(random.uniform(0.5, 1.5))
    except Exception as e:
        print(f"获取 {stock} 失败：{e}")
```

---

### 2. 并发控制

**推荐并发数**：
- 同一域名：不超过 3 个并发
- 不同数据源：可适当提高

**示例**（使用线程池）：

```python
import akshare as ak
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

def fetch_stock_data(symbol):
    """获取单个股票数据"""
    try:
        time.sleep(0.5)  # 添加延时
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
        return df
    except Exception as e:
        print(f"获取 {symbol} 失败：{e}")
        return None

stocks = ["000001", "000002", "000003", "600000", "600036"]

# 使用线程池，并发数不超过 3
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = {executor.submit(fetch_stock_data, stock): stock for stock in stocks}

    for future in as_completed(futures):
        stock = futures[future]
        result = future.result()
        if result is not None:
            print(f"{stock} 数据获取成功")
```

---

### 3. 错误重试机制

**建议配置**：
- 最大重试次数：3 次
- 重试间隔：指数退避（1s, 2s, 4s）

**示例代码**：

```python
import akshare as ak
import time

def fetch_with_retry(func, max_retries=3, *args, **kwargs):
    """带重试的数据获取函数"""
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # 指数退避
                print(f"请求失败，{wait_time} 秒后重试（第 {attempt + 1}/{max_retries} 次）")
                time.sleep(wait_time)
            else:
                print(f"重试 {max_retries} 次后仍失败：{e}")
                raise

# 使用示例
df = fetch_with_retry(
    ak.stock_zh_a_hist,
    max_retries=3,
    symbol="000001",
    period="daily",
    adjust="qfq"
)
```

---

### 4. 数据缓存策略

**推荐做法**：
- 实时数据缓存 1-5 分钟
- 历史数据本地持久化
- 使用 Redis 或文件系统缓存

**示例代码**：

```python
import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import os

class StockDataCache:
    """股票数据缓存管理器"""

    def __init__(self, cache_dir="cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def _get_cache_path(self, symbol, data_type):
        """获取缓存文件路径"""
        return f"{self.cache_dir}/{symbol}_{data_type}.csv"

    def _is_cache_valid(self, cache_path, valid_minutes=5):
        """检查缓存是否有效"""
        if not os.path.exists(cache_path):
            return False

        file_time = datetime.fromtimestamp(os.path.getmtime(cache_path))
        expire_time = datetime.now() - timedelta(minutes=valid_minutes)
        return file_time > expire_time

    def get_spot_data(self, symbol, force_refresh=False):
        """获取实时行情（带缓存）"""
        cache_path = self._get_cache_path(symbol, "spot")

        # 如果缓存有效且不强制刷新，直接返回缓存
        if not force_refresh and self._is_cache_valid(cache_path):
            return pd.read_csv(cache_path)

        # 否则从接口获取
        df = ak.stock_zh_a_spot_em()
        df = df[df['代码'] == symbol]

        # 保存到缓存
        df.to_csv(cache_path, index=False, encoding="utf-8-sig")
        return df

# 使用示例
cache = StockDataCache()
df = cache.get_spot_data("000001")
print(df)
```

---

### 5. 代理设置

如果遇到 IP 封禁，可以使用代理：

```python
import akshare as ak

# 设置代理（AKShare 本身不直接支持，需在 requests 层设置）
# 方法 1：环境变量
import os
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'

# 方法 2：修改 akshare 源码或使用 requests 会话
```

---

## 🔧 常见问题与解决方案

### 1. ReadTimeout 错误

**错误信息**：
```
ReadTimeout: HTTPConnectionPool(host='xxx.com', port=80): Read timed out.
```

**原因**：
- 网络连接超时
- 服务器响应缓慢
- 数据量大

**解决方案**：
1. 重新运行接口函数
2. 更换 IP 地址（使用代理）
3. 降低访问频率
4. 增加超时时间

**示例代码**：

```python
import akshare as ak
import time

# 方案 1：添加重试
for i in range(3):
    try:
        df = ak.stock_zh_a_hist(symbol="000001")
        break
    except Exception as e:
        print(f"第 {i+1} 次失败：{e}")
        time.sleep(2)

# 方案 2：分批获取数据（避免单次请求过大）
df = ak.stock_zh_a_hist(
    symbol="000001",
    start_date="20200101",
    end_date="20201231"  # 先获取一年数据
)
```

---

### 2. KeyError 错误

**错误信息**：
```
KeyError: 'xxxx'
```

**原因**：
- 接口返回字段变化
- 股票代码错误
- 数据源结构调整

**解决方案**：
1. 升级 AKShare 到最新版本
2. 检查返回的实际字段名
3. 验证股票代码是否正确

**示例代码**：

```python
import akshare as ak

# 检查返回的字段
df = ak.stock_zh_a_hist(symbol="000001")
print(df.columns.tolist())  # 打印所有字段名

# 使用 .get() 方法或 try-except 避免直接访问不存在的字段
try:
    close_price = df['收盘']
except KeyError:
    print("字段名可能已更新，请检查")
    close_price = df['close']  # 尝试其他可能的字段名
```

---

### 3. HTTP 403 错误

**错误信息**：
```
HTTPError: 403 Forbidden
```

**原因**：
- 请求过于频繁，触发反爬机制
- IP 被封禁

**解决方案**：
1. 降低请求频率
2. 更换 IP 地址
3. 使用代理池
4. 添加请求延时

**示例代码**：

```python
import akshare as ak
import time
import random

def safe_fetch(symbol):
    """安全获取数据，避免 403 错误"""
    max_retries = 3
    for i in range(max_retries):
        try:
            df = ak.stock_zh_a_hist(symbol=symbol)
            return df
        except Exception as e:
            if i < max_retries - 1:
                # 指数退避 + 随机因子
                wait_time = (2 ** i) + random.uniform(0, 1)
                print(f"请求失败，{wait_time:.1f} 秒后重试...")
                time.sleep(wait_time)
            else:
                raise

# 使用
df = safe_fetch("000001")
```

---

### 4. ConnectionError 错误

**错误信息**：
```
ConnectionError: HTTPConnectionPool
```

**原因**：
- 网络连接不稳定
- 服务器主动断开连接
- 防火墙或代理问题

**解决方案**：
1. 检查网络连接
2. 添加重试机制
3. 增加超时时间
4. 使用稳定的数据源

**示例代码**：

```python
import akshare as ak
import time

def robust_fetch(func, *args, max_retries=5, **kwargs):
    """鲁棒的数据获取函数"""
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = min(2 ** attempt, 10)  # 最多等待 10 秒
                print(f"连接错误（第 {attempt + 1} 次），{wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                print(f"连接失败，已重试 {max_retries} 次")
                raise

# 使用
df = robust_fetch(ak.stock_zh_a_hist, symbol="000001")
```

---

### 5. 数据字段为空或异常

**问题**：返回的 DataFrame 中某些字段为空或数据异常

**原因**：
- 该股票字段确实无数据（如新股）
- 数据源临时维护
- 数据结构变化

**解决方案**：
1. 检查其他股票是否有同样问题
2. 查看官方文档是否有接口更新
3. 更新 AKShare 版本
4. 尝试其他数据源接口

**示例代码**：

```python
import akshare as ak

# 检查数据完整性
def check_data_quality(df, symbol):
    """检查数据质量"""
    if df.empty:
        print(f"警告：{symbol} 返回数据为空")
        return False

    # 检查关键字段
    required_fields = ['日期', '开盘', '收盘', '最高', '最低']
    missing_fields = [f for f in required_fields if f not in df.columns]

    if missing_fields:
        print(f"警告：{symbol} 缺少字段：{missing_fields}")

    # 检查缺失值
    null_count = df.isnull().sum()
    if null_count.any():
        print(f"警告：{symbol} 存在缺失值")
        print(null_count[null_count > 0])

    return True

# 使用
df = ak.stock_zh_a_hist(symbol="000001")
check_data_quality(df, "000001")
```

---

### 6. 批量请求超时或失败

**问题**：批量获取多个股票数据时部分失败

**解决方案**：
1. 降低并发数
2. 添加请求间隔
3. 实现断点续传
4. 记录失败股票，后续重试

**示例代码**：

```python
import akshare as ak
import time
import json
from pathlib import Path

def batch_fetch_with_resume(symbols, cache_file="progress.json"):
    """支持断点续传的批量获取"""
    # 读取进度
    progress = {}
    if Path(cache_file).exists():
        with open(cache_file, 'r') as f:
            progress = json.load(f)

    success_list = progress.get('success', [])
    failed_list = progress.get('failed', [])

    all_data = {}

    for symbol in symbols:
        if symbol in success_list:
            print(f"跳过已成功：{symbol}")
            continue

        try:
            print(f"正在获取：{symbol}")
            df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
            all_data[symbol] = df
            success_list.append(symbol)

            # 保存进度
            with open(cache_file, 'w') as f:
                json.dump({'success': success_list, 'failed': failed_list}, f)

            time.sleep(0.5)  # 添加延时

        except Exception as e:
            print(f"获取失败：{symbol}，错误：{e}")
            failed_list.append(symbol)

            # 保存进度
            with open(cache_file, 'w') as f:
                json.dump({'success': success_list, 'failed': failed_list}, f)

    print(f"\n完成！成功：{len(success_list)}，失败：{len(failed_list)}")
    return all_data

# 使用
stocks = ["000001", "000002", "000003", "600000"]
data = batch_fetch_with_resume(stocks)
```

---

### 7. 升级相关问题

**问题**：升级 AKShare 后接口不兼容

**解决方案**：
1. 查看版本更新日志
2. 阅读迁移指南
3. 测试关键接口
4. 保留旧版本作为备份

**查看版本和升级**：

```bash
# 查看当前版本
pip show akshare

# 升级到最新版本
pip install akshare --upgrade

# 或使用 Poetry
poetry update akshare
```

---

## 📚 接口速查表

### A 股核心接口（50+）

#### 实时行情与历史数据
| 功能 | 接口名称 | 数据源 |
|------|----------|--------|
| A股实时行情 | `stock_zh_a_spot_em()` | 东方财富 |
| 沪市实时行情 | `stock_sh_a_spot_em()` | 东方财富 |
| 深市实时行情 | `stock_sz_a_spot_em()` | 东方财富 |
| 北交所实时行情 | `stock_bj_a_spot_em()` | 东方财富 |
| 科创板实时行情 | `stock_kc_a_spot_em()` | 东方财富 |
| 创业板实时行情 | `stock_cy_a_spot_em()` | 东方财富 |
| 个股历史日线 | `stock_zh_a_hist()` | 东方财富 |
| 历史分钟数据 | `stock_zh_a_hist_min_em()` | 东方财富 |

#### 股票基本信息
| 功能 | 接口名称 | 数据源 |
|------|----------|--------|
| 个股基本信息 | `stock_individual_info_em()` | 东方财富 |
| A股代码名称 | `stock_info_a_code_name()` | 东方财富 |

#### 财务数据
| 功能 | 接口名称 | 数据源 |
|------|----------|--------|
| 资产负债表 | `stock_balance_sheet_by_report_em()` | 东方财富 |
| 利润表 | `stock_profit_sheet_by_report_em()` | 东方财富 |
| 现金流量表 | `stock_cash_flow_sheet_by_report_em()` | 东方财富 |
| 财务摘要 | `stock_financial_abstract()` | 东方财富 |
| 财务分析指标 | `stock_financial_analysis_indicator_em()` | 东方财富 |
| 估值指标 | `stock_a_lg_indicator()` | 乐咕乐股 |

#### 板块行业数据
| 功能 | 接口名称 | 数据源 |
|------|----------|--------|
| 概念板块列表 | `stock_board_concept_name_em()` | 东方财富 |
| 行业板块列表 | `stock_board_industry_name_em()` | 东方财富 |
| 概念板块行情 | `stock_board_concept_spot_em()` | 东方财富 |
| 行业板块行情 | `stock_board_industry_spot_em()` | 东方财富 |
| 概念板块成份股 | `stock_board_concept_cons_em()` | 东方财富 |
| 行业板块成份股 | `stock_board_industry_cons_em()` | 东方财富 |
| 概念板块资金流向 | `stock_fund_flow_concept()` | 东方财富 |
| 行业板块资金流向 | `stock_fund_flow_industry()` | 东方财富 |

#### 龙虎榜数据
| 功能 | 接口名称 | 数据源 |
|------|----------|--------|
| 龙虎榜明细 | `stock_lhb_detail_em()` | 东方财富 |
| 个股龙虎榜 | `stock_lhb_stock_detail_em()` | 东方财富 |
| 龙虎榜统计 | `stock_lhb_stock_statistic_em()` | 东方财富 |

#### 股东信息
| 功能 | 接口名称 | 数据源 |
|------|----------|--------|
| 十大股东 | `stock_main_stock_holder()` | 新浪 |
| 十大流通股东 | `stock_gdfx_top_10_em()` | 东方财富 |
| 股东户数 | `stock_zh_a_gdhs()` | 东方财富 |
| 股东户数明细 | `stock_zh_a_gdhs_detail_em()` | 东方财富 |

#### 资金流向
| 功能 | 接口名称 | 数据源 |
|------|----------|--------|
| 个股资金流向 | `stock_individual_fund_flow()` | 东方财富 |
| 个股资金流向 | `stock_fund_flow_individual()` | 东方财富 |
| 主力资金流向 | `stock_main_fund_flow()` | 东方财富 |

#### 业绩与研报
| 功能 | 接口名称 | 数据源 |
|------|----------|--------|
| 业绩预告 | `stock_profit_forecast_em()` | 东方财富 |
| 券商研报 | `stock_research_report_em()` | 东方财富 |

#### 融资融券
| 功能 | 接口名称 | 数据源 |
|------|----------|--------|
| 沪市融资融券 | `stock_margin_sse()` | 上交所 |
| 深市融资融券 | `stock_margin_szse()` | 深交所 |

#### 新股与IPO
| 功能 | 接口名称 | 数据源 |
|------|----------|--------|
| 新股申购 | `stock_new_a_spot_em()` | 东方财富 |
| IPO信息 | `stock_ipo_info()` | 东方财富 |

#### 其他重要数据
| 功能 | 接口名称 | 数据源 |
|------|----------|--------|
| 股票质押 | `stock_gpzy_profile_em()` | 东方财富 |
| 限售股解禁 | `stock_restricted_release_summary_em()` | 东方财富 |
| 沪深港通资金流向 | `stock_hsgt_fund_flow_summary_em()` | 东方财富 |

---

### 港股核心接口（15+）

| 功能 | 接口名称 | 数据源 |
|------|----------|--------|
| 实时行情 | `stock_hk_spot()` | 腾讯证券 |
| 实时行情 | `stock_hk_spot_em()` | 东方财富 |
| 历史日线 | `stock_hk_daily()` | 腾讯证券 |
| 历史分钟 | `stock_hk_hist_min_em()` | 东方财富 |
| 财务指标 | `stock_hk_financial_indicator_em()` | 东方财富 |
| 财务报表 | `stock_financial_hk_report_em()` | 东方财富 |
| 指数实时行情 | `stock_hk_index_spot_em()` | 东方财富 |
| 指数历史数据 | `stock_hk_index_daily_em()` | 东方财富 |
| 港股通成份股 | `stock_hk_ggt_components_em()` | 东方财富 |
| 港股通资金流向 | `stock_hsgt_hist_em()` | 东方财富 |
| 港股通持股明细 | `stock_hsgt_hold_stock_em()` | 东方财富 |
| 个股指标 | `stock_hk_eniu_indicator()` | 鹏博资讯 |

---

### 美股核心接口（10+）

| 功能 | 接口名称 | 数据源 |
|------|----------|--------|
| 实时行情 | `stock_us_spot()` | 新浪财经 |
| 实时行情 | `stock_us_spot_em()` | 东方财富 |
| 历史日线 | `stock_us_daily()` | 新浪财经 |
| 历史数据 | `stock_us_hist()` | 东方财富 |
| 历史分钟 | `stock_us_hist_min_em()` | 东方财富 |
| 股票代码列表 | `get_us_stock_name()` | 新浪财经 |
| 中概股行情 | `stock_us_zh_spot()` | 东方财富 |
| 个股基本信息 | `stock_individual_basic_info_us_xq()` | 雪球 |
| 财务分析指标 | `stock_financial_us_analysis_indicator_em()` | 东方财富 |
| 财务报表 | `stock_financial_us_report_em()` | 东方财富 |

---

### 指数数据接口（10+）

| 功能 | 接口名称 | 数据源 |
|------|----------|--------|
| A股指数实时行情 | `stock_zh_index_spot_em()` | 东方财富 |
| A股指数历史数据 | `stock_zh_index_daily_em()` | 东方财富 |
| 指数成份股 | `index_stock_cons_sina()` | 新浪财经 |
| 指数成份股权重 | `index_stock_cons_weight_csindex()` | 中证指数 |
| 港股指数实时行情 | `stock_hk_index_spot_em()` | 东方财富 |
| 美股指数行情 | `index_us_stock_sina()` | 新浪财经 |

---

## 🎯 最佳实践

### 1. 完整的数据获取流程

```python
import akshare as ak
import pandas as pd
import time
from datetime import datetime

class AKShareDataProvider:
    """AKShare 数据提供器"""

    def __init__(self):
        self.last_request_time = 0
        self.min_interval = 0.5  # 最小请求间隔（秒）

    def _rate_limit(self):
        """请求限流"""
        current_time = time.time()
        elapsed = current_time - self.last_request_time

        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)

        self.last_request_time = time.time()

    def get_stock_daily(self, symbol, start_date, end_date, adjust="qfq"):
        """获取日线数据（带限流和重试）"""
        self._rate_limit()

        max_retries = 3
        for attempt in range(max_retries):
            try:
                df = ak.stock_zh_a_hist(
                    symbol=symbol,
                    period="daily",
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust
                )

                # 数据质量检查
                if df.empty:
                    print(f"警告：{symbol} 返回数据为空")
                    return None

                return df

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"获取 {symbol} 失败（第 {attempt + 1} 次），{wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    print(f"获取 {symbol} 失败：{e}")
                    return None

    def batch_get_stocks(self, symbols, start_date, end_date):
        """批量获取多只股票数据"""
        results = {}

        for i, symbol in enumerate(symbols):
            print(f"[{i+1}/{len(symbols)}] 获取 {symbol}...")

            df = self.get_stock_daily(symbol, start_date, end_date)
            if df is not None:
                results[symbol] = df

        return results

# 使用示例
provider = AKShareDataProvider()

# 获取单只股票
df = provider.get_stock_daily("000001", "20200101", "20241231")
print(df.head())

# 批量获取
stocks = ["000001", "000002", "600000"]
data = provider.batch_get_stocks(stocks, "20200101", "20241231")
```

---

### 2. 数据持久化策略

```python
import akshare as ak
import pandas as pd
from pathlib import Path
import pickle

class StockDataManager:
    """股票数据管理器"""

    def __init__(self, data_dir="stock_data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)

    def save_csv(self, df, symbol):
        """保存为 CSV"""
        file_path = self.data_dir / f"{symbol}.csv"
        df.to_csv(file_path, index=False, encoding="utf-8-sig")
        print(f"已保存：{file_path}")

    def load_csv(self, symbol):
        """加载 CSV"""
        file_path = self.data_dir / f"{symbol}.csv"
        if file_path.exists():
            return pd.read_csv(file_path)
        return None

    def save_pickle(self, data, filename):
        """保存为 pickle（适合复杂数据结构）"""
        file_path = self.data_dir / filename
        with open(file_path, 'wb') as f:
            pickle.dump(data, f)
        print(f"已保存：{file_path}")

    def load_pickle(self, filename):
        """加载 pickle"""
        file_path = self.data_dir / filename
        if file_path.exists():
            with open(file_path, 'rb') as f:
                return pickle.load(f)
        return None

# 使用示例
manager = StockDataManager()

# 保存数据
df = ak.stock_zh_a_hist(symbol="000001")
manager.save_csv(df, "000001")

# 加载数据
cached_df = manager.load_csv("000001")
print(cached_df.head())
```

---

### 3. 错误日志记录

```python
import akshare as ak
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('akshare_errors.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def safe_fetch_with_log(symbol):
    """带日志记录的安全数据获取"""
    try:
        logger.info(f"开始获取 {symbol} 数据")
        df = ak.stock_zh_a_hist(symbol=symbol)
        logger.info(f"成功获取 {symbol} 数据，共 {len(df)} 条记录")
        return df

    except Exception as e:
        logger.error(f"获取 {symbol} 数据失败：{e}", exc_info=True)
        return None

# 使用
df = safe_fetch_with_log("000001")
```

---

## 📖 参考资料

### 官方文档

- **AKShare 主页**：https://akshare.akfamily.xyz/
- **数据字典**：https://akshare.akfamily.xyz/data/index.html
- **股票数据**：https://akshare.akfamily.xyz/data/stock/stock.html
- **答疑专栏**：https://akshare.akfamily.xyz/answer.html
- **GitHub Issues**：https://github.com/akfamily/akshare/issues

### 社区资源

- **CSDN AKShare 专栏**：搜索 "AKShare" 获取大量实战案例
- **知乎专栏**：搜索 "AKShare" 获取深度教程
- **GitHub 示例**：https://github.com/akfamily/akshare/tree/master/examples

### 相关库

- **pandas**：数据处理
- **ta**：技术指标计算
- **matplotlib**：数据可视化
- **requests**：网络请求

---

## 📝 更新日志

### 2025-01-02 (v2.0.0)
- **重大更新**：从 8 个接口扩展到 **80+ 个接口**
- **新增 A 股接口（40+）**：
  - 股票基本信息：个股基本信息、代码名称列表
  - 板块行业数据：概念板块、行业板块（列表、行情、成份股、资金流向）
  - 龙虎榜数据：龙虎榜明细、个股龙虎榜
  - 股东信息：十大股东、十大流通股东、股东户数
  - 资金流向：个股/板块资金流向、主力资金
  - 业绩预告与研报
  - 融资融券数据
  - 新股与 IPO 数据
  - 北交所/科创板数据
  - 其他数据：股票质押、限售股解禁
- **新增港股接口（7+）**：
  - 财务数据：财务指标、财务报表
  - 港股指数：实时行情、历史数据
  - 港股通明细：资金流向、持股明细
- **新增美股接口（4+）**：
  - 个股基本信息
  - 财务分析指标、财务报表
- **新增指数数据接口（6+）**：
  - A股指数：实时行情、历史数据、成份股、权重
  - 港股指数：实时行情
  - 美股指数：行情
- **更新接口速查表**：分类更清晰，涵盖所有接口
- **补充完整示例代码**：每个接口都有可运行的示例

### 2025-01-02 (v1.0.0)
- 创建文档
- 整理 A 股、港股、美股核心接口（8个基础接口）
- 添加限流策略和最佳实践
- 添加常见问题解决方案

---

## 🤝 贡献指南

如果发现文档有误或需要补充新的接口，请：

1. 提交 Issue 或 Pull Request
2. 注明接口名称、数据源、参数说明
3. 提供示例代码和测试结果

---

**最后更新**：2025-01-02
**文档版本**：v2.0.0
**AKShare 版本**：>= 1.18.0
**接口数量**：80+
