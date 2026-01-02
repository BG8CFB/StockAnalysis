# AKShare A股接口文档

**版本**：v2.0.0
**创建日期**：2026-01-03
**适用市场**：A股
**测试状态**：核心接口已测试可用

---

## 📌 数据源简介

**AKShare** 是基于 Python 的开源财经数据接口库，完全免费，无需 API Key。

### 核心特性

- ✅ **免费开源**：完全免费，无需 API Key
- ✅ **数据覆盖广**：支持 A 股市场全覆盖
- ✅ **接口丰富**：提供 50+ A股专用接口
- ✅ **简单易用**：统一接口设计，返回 pandas DataFrame 格式

### 官方资源

- **官方文档**：https://akshare.akfamily.xyz/
- **GitHub 仓库**：https://github.com/akfamily/akshare

---

## 📦 安装与配置

### 安装

```bash
pip install akshare
```

### 基本使用

```python
import akshare as ak

# 获取 A 股实时行情
df = ak.stock_zh_a_spot_em()
print(df.head())
```

---

## 🇨🇳 A股接口

### 1. 实时行情数据

#### 1.1 沪深京 A 股实时行情

**接口名称**：`stock_zh_a_spot_em()`

**测试状态**：✅ 已测试可用 (2025-01-02测试，响应时间 13.40s)

**功能描述**：获取沪深京 A 股所有上市公司的实时行情数据

**数据源**：东方财富网

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
```

---

#### 2.2 历史分钟数据

**接口名称**：`stock_zh_a_hist_min_em()`

**功能描述**：获取 A 股个股分钟级别历史数据

**请求参数**：

| 参数名 | 类型 | 说明 | 默认值 |
|--------|------|------|--------|
| symbol | str | 股票代码 | - |
| period | str | 周期：1, 5, 15, 30, 60 | "1" |
| adjust | str | 复权类型 | "" |

**示例代码**：

```python
import akshare as ak

# 获取 1 分钟级别数据
df = ak.stock_zh_a_hist_min_em(
    symbol="000001",
    period="1",
    adjust=""
)
```

---

### 3. 财务数据

#### 3.1 财务报表数据

**接口名称**：`stock_balance_sheet_by_report_em()` / `stock_profit_sheet_by_report_em()` / `stock_cash_flow_sheet_by_report_em()`

**测试状态**：✅ 已测试可用 (2025-01-02修复测试)

**功能描述**：获取资产负债表、利润表、现金流量表

**数据源**：东方财富网

**注意事项**：
- 调用时不传任何参数，接口返回所有股票的财务数据
- 根据需要筛选特定股票

---

#### 3.2 财务指标

**接口名称**：`stock_financial_abstract()`

**功能描述**：获取主要财务指标摘要

**返回字段**：

| 字段名 | 说明 |
|--------|------|
| 报告期 | 财务报告期 |
| 每股净资产 | 每股净资产（元） |
| 净利润 | 净利润（元） |
| 净资产收益率 | ROE |
| 总资产 | 总资产（元） |
| 总负债 | 总负债（元） |

---

### 4. 板块行业数据

#### 4.1 概念板块名称列表

**接口名称**：`stock_board_concept_name_em()`

**测试状态**：✅ 已测试可用 (2025-01-02测试，响应时间 1.02s)

**功能描述**：获取所有概念板块名称

**示例代码**：

```python
import akshare as ak

# 获取概念板块列表
df = ak.stock_board_concept_name_em()
print(df.head())
```

---

#### 4.2 行业板块名称列表

**接口名称**：`stock_board_industry_name_em()`

**测试状态**：✅ 已测试可用 (2025-01-02测试，响应时间 0.19s)

**功能描述**：获取所有行业板块名称

**示例代码**：

```python
import akshare as ak

# 获取行业板块列表
df = ak.stock_board_industry_name_em()
print(df.head())
```

---

#### 4.3 概念板块实时行情

**接口名称**：`stock_board_concept_spot_em()`

**功能描述**：获取概念板块实时行情

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

### 5. 龙虎榜数据

#### 5.1 龙虎榜成交明细

**接口名称**：`stock_lhb_detail_em()`

**测试状态**：✅ 已测试可用 (2025-01-02修复测试)

**功能描述**：获取龙虎榜成交明细数据

**注意事项**：
- 调用时不传任何参数，接口自动返回最近交易日的数据

---

#### 5.2 个股龙虎榜明细

**接口名称**：`stock_lhb_stock_detail_em()`

**功能描述**：获取单个股票的龙虎榜明细

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

### 6. 股东信息

#### 6.1 十大流通股东

**接口名称**：`stock_gdfx_top_10_em()`

**测试状态**：✅ 已测试可用 (2025-01-02修复测试)

**功能描述**：获取十大流通股东信息

**注意事项**：
- symbol 参数需要带市场前缀（sh/sz）
- 沪市（60开头、688开头）：前缀 `sh`
- 深市（00开头、30开头、301开头）：前缀 `sz`

**示例代码**：

```python
import akshare as ak

# 获取十大流通股东
df = ak.stock_gdfx_top_10_em(symbol="sh600519")
print(df.head())
```

---

### 7. 融资融券

#### 7.1 沪市融资融券

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

#### 7.2 深市融资融券

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

## ⚠️ 限流与注意事项

### 1. 请求频率限制

AKShare 本身不强制限流，但依赖的第三方数据源有反爬机制。

**建议策略**：
- 单个接口请求间隔：0.5-1 秒
- 批量请求时添加随机延时
- 避免在短时间内重复请求相同数据

### 2. 并发控制

**推荐并发数**：
- 同一域名：不超过 3 个并发
- 不同数据源：可适当提高

### 3. 错误重试机制

**建议配置**：
- 最大重试次数：3 次
- 重试间隔：指数退避（1s, 2s, 4s）

---

## 🔧 常见问题与解决方案

### 1. ReadTimeout 错误

**解决方案**：
1. 重新运行接口函数
2. 降低访问频率
3. 增加超时时间

### 2. HTTP 403 错误

**原因**：请求过于频繁，触发反爬机制

**解决方案**：
1. 降低请求频率
2. 添加请求延时

---

## 📚 A股接口速查表

| 功能 | 接口名称 | 数据源 |
|------|----------|--------|
| A股实时行情 | `stock_zh_a_spot_em()` | 东方财富 |
| 个股历史日线 | `stock_zh_a_hist()` | 东方财富 |
| 历史分钟数据 | `stock_zh_a_hist_min_em()` | 东方财富 |
| 资产负债表 | `stock_balance_sheet_by_report_em()` | 东方财富 |
| 利润表 | `stock_profit_sheet_by_report_em()` | 东方财富 |
| 现金流量表 | `stock_cash_flow_sheet_by_report_em()` | 东方财富 |
| 概念板块列表 | `stock_board_concept_name_em()` | 东方财富 |
| 行业板块列表 | `stock_board_industry_name_em()` | 东方财富 |
| 龙虎榜明细 | `stock_lhb_detail_em()` | 东方财富 |
| 十大流通股东 | `stock_gdfx_top_10_em()` | 东方财富 |
| 沪市融资融券 | `stock_margin_sse()` | 上交所 |
| 深市融资融券 | `stock_margin_szse()` | 深交所 |

---

## 📖 参考资料

- **AKShare 主页**：https://akshare.akfamily.xyz/
- **股票数据**：https://akshare.akfamily.xyz/data/stock/stock.html
- **GitHub 仓库**：https://github.com/akfamily/akshare

---

**最后更新**：2026-01-03
**文档版本**：v2.0.0（A股版）
**接口数量**：50+
