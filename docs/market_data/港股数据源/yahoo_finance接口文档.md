# Yahoo Finance 港股接口文档

**版本**：v2.0
**创建日期**：2025-01-02
**更新日期**：2026-01-03
**适用市场**：港股
**推荐优先级**：备用（AkShare失败时降级使用）

---

## 数据源简介

### 基本信息

| 项目 | 说明 |
|------|------|
| **官网** | [https://finance.yahoo.com](https://finance.yahoo.com) |
| **API 基地址** | https://query1.finance.yahoo.com |
| **类型** | 完全免费 |
| **调用限制** | 约2000次/小时（硬性限制） |
| **数据质量** | ⭐⭐⭐⭐（高） |
| **稳定性** | ⭐⭐⭐⭐⭐（高） |

### 数据特点

**优势**：
- 完全免费，无需注册
- 数据权威，来源可靠
- 稳定性高，官方接口
- 历史数据可追溯数十年
- 支持多种数据类型

**劣势**：
- 无官方 Python SDK（需使用 yfinance 第三方库）
- 免费版有15-20分钟延迟
- 有限流限制（2000次/小时）

### 推荐使用场景

- 作为 AkShare 失用时的降级选项
- 获取港股历史数据
- 获取港股财务报表数据
- 获取港股公司基本信息

---

## 安装与配置

### 安装 yfinance

```bash
pip install yfinance
```

### 基本使用

```python
import yfinance as yf

# 创建股票对象
ticker = yf.Ticker('0700.HK')

# 获取历史数据
hist = ticker.history(period="1mo")
print(hist.head())

# 获取公司信息
info = ticker.info
print(info.get('longName'))
```

---

## 港股接口

### 1. 历史K线数据

**接口地址**：`/v8/finance/chart/{symbol}`

**功能**：获取港股历史K线数据（OHLCV）

**支持数据类型**：
- 日K线（1d）
- 周K线（1wk）
- 月K线（1mo）
- 分钟K线（1m, 5m, 15m, 30m, 60m）

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `symbol` | string | ✅ | 股票代码（如 "0700.HK"） |
| `interval` | string | ❌ | 时间间隔，默认 "1d" |
| `range` | string | ❌ | 数据范围，如 "1y", "5y", "max" |
| `period1` | int | ❌ | 开始时间戳 |
| `period2` | int | ❌ | 结束时间戳 |

**interval 可选值**：
- `1m`, `5m`, `15m`, `30m`, `60m` - 分钟K线
- `1d` - 日K线（默认）
- `1wk` - 周K线
- `1mo` - 月K线

**返回字段**：

| Yahoo Finance 字段 | 标准字段 | 类型 | 说明 |
|-------------------|---------|------|------|
| `open` | `open` | float | 开盘价（港元） |
| `high` | `high` | float | 最高价（港元） |
| `low` | `low` | float | 最低价（港元） |
| `close` | `close` | float | 收盘价（港元） |
| `volume` | `volume` | int | 成交量（股） |
| `adjclose` | `adj_close` | float | 复权收盘价 |
| `date` | `trade_date` | string | 交易日期 |

**示例代码**：

```python
import yfinance as yf

# 获取腾讯控股历史日线数据
ticker = yf.Ticker('0700.HK')
hist = ticker.history(
    interval="1d",
    start="2020-01-01",
    end="2024-12-31"
)
print(hist.head())

# 获取周线数据
hist_weekly = ticker.history(interval="1wk", period="1y")
```

---

### 2. 实时行情数据

**接口地址**：`/v6/finance/quote`

**功能**：获取港股实时报价数据

**支持数据**：
- 最新价格
- 涨跌幅
- 成交量/成交额
- 52周高低
- 市值
- PE/PB 比率

**返回字段**：

| Yahoo Finance 字段 | 标准字段 | 类型 | 说明 |
|-------------------|---------|------|------|
| `regularMarketPrice` | `price` | float | 最新价（港元） |
| `regularMarketPreviousClose` | `pre_close` | float | 昨收价（港元） |
| `regularMarketOpen` | `open` | float | 开盘价（港元） |
| `regularMarketDayHigh` | `high` | float | 最高价（港元） |
| `regularMarketDayLow` | `low` | float | 最低价（港元） |
| `regularMarketVolume` | `volume` | int | 成交量（股） |
| `fiftyTwoWeekHigh` | `high_52w` | float | 52周最高（港元） |
| `fiftyTwoWeekLow` | `low_52w` | float | 52周最低（港元） |
| `marketCap` | `market_cap` | int | 市值（港元） |
| `trailingPE` | `pe_ratio` | float | 市盈率 |

**示例代码**：

```python
import yfinance as yf

# 获取腾讯控股实时行情
ticker = yf.Ticker('0700.HK')
info = ticker.info

print(f"最新价: {info.get('regularMarketPrice')}")
print(f"涨跌幅: {info.get('regularMarketChangePercent')}%")
print(f"成交量: {info.get('regularMarketVolume')}")
```

---

### 3. 公司基本信息

**接口地址**：`/v10/finance/quoteSummary/{symbol}`

**模块**：`assetProfile`

**功能**：获取港股公司基本面信息

**支持数据**：
- 公司名称
- 行业分类
- 业务简介
- 公司网址
- 员工数量
- 总部地址

**返回字段**：

| Yahoo Finance 字段 | 标准字段 | 类型 | 说明 |
|-------------------|---------|------|------|
| `longName` | `company_name` | string | 公司全称 |
| `shortName` | `name` | string | 公司简称 |
| `industry` | `industry` | string | 所属行业 |
| `sector` | `sector` | string | 所属板块 |
| `longBusinessSummary` | `description` | string | 业务描述 |
| `website` | `website` | string | 公司网址 |
| `employees` | `employees` | int | 员工数量 |
| `city` | `city` | string | 所在城市 |
| `country` | `country` | string | 所在国家 |

**示例代码**：

```python
import yfinance as yf

# 获取腾讯控股公司信息
ticker = yf.Ticker('0700.HK')
info = ticker.info

print(f"公司名称: {info.get('longName')}")
print(f"所属行业: {info.get('industry')}")
print(f"所属板块: {info.get('sector')}")
print(f"公司网址: {info.get('website')}")
print(f"员工数量: {info.get('fullTimeEmployees')}")
```

---

### 4. 财务报表数据

**接口地址**：`/v10/finance/quoteSummary/{symbol}`

**模块**：
- `incomeStatementHistory` - 利润表
- `balanceSheetHistory` - 资产负债表
- `cashflowStatementHistory` - 现金流量表

**功能**：获取港股三大财务报表

**注意**：港股财务数据可能不如美股完整，部分股票可能缺少某些报表

**支持数据**：
- 营业收入
- 净利润
- 总资产
- 总负债
- 经营现金流
- 多年期数据

**示例代码**：

```python
import yfinance as yf

# 获取腾讯控股财务报表
ticker = yf.Ticker('0700.HK')

# 获取利润表
income_stmt = ticker.income_stmt
print(income_stmt.head())

# 获取资产负债表
balance_sheet = ticker.balance_sheet
print(balance_sheet.head())

# 获取现金流量表
cash_flow = ticker.cashflow
print(cash_flow.head())
```

---

### 5. 财务指标数据

**接口地址**：`/v10/finance/quoteSummary/{symbol}`

**模块**：`defaultKeyStatistics`

**功能**：获取港股关键财务指标

**支持数据**：
- 市值
- PE/PB/PS 比率
- ROE/ROA
- 每股收益（EPS）
- 股息率
- Beta系数
- 52周高低

**示例代码**：

```python
import yfinance as yf

# 获取腾讯控股财务指标
ticker = yf.Ticker('0700.HK')
info = ticker.info

print(f"市值: {info.get('marketCap')}")
print(f"市盈率: {info.get('trailingPE')}")
print(f"市净率: {info.get('priceToBook')}")
print(f"股息率: {info.get('dividendYield')}%")
```

---

### 6. 股息数据

**接口地址**：`/v13/finance/quoteSummary/{symbol}`

**模块**：`dividendHistory`

**功能**：获取港股股息分红历史

**支持数据**：
- 分红日期
- 分红金额
- 分红频率

**示例代码**：

```python
import yfinance as yf

# 获取腾讯控股分红历史
ticker = yf.Ticker('0700.HK')
dividends = ticker.dividends
print(dividends.head())
```

---

### 7. 市场热门股票

**接口地址**：`/v1/finance/trending/{region}`

**功能**：获取港股市场热门股票列表

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `region` | string | ✅ | 区域代码，港股使用 "HK" |

**示例代码**：

```python
import yfinance as yf

# 获取港股热门股票
trending = yf.Trending('HK')
print(trending)
```

---

### 8. 公司新闻

**接口地址**：`/v1/finance/news-stories`

**功能**：获取港股公司相关新闻

**支持数据**：
- 新闻标题
- 发布时间
- 新闻来源
- 摘要内容

**示例代码**：

```python
import yfinance as yf

# 获取腾讯控股新闻
ticker = yf.Ticker('0700.HK')
news = ticker.news
print(news[:5])  # 打印前5条新闻
```

---

## 港股代码格式

| 格式 | 示例 | 说明 |
|------|------|------|
| Yahoo格式 | `0700.HK`, `9988.HK` | 代码加 `.HK` 后缀 |
| 数字格式 | `700`, `9988` | 纯数字代码 |

**常用港股代码示例**：
- `0700.HK` - 腾讯控股
- `9988.HK` - 阿里巴巴
- `0941.HK` - 中国移动
- `1299.HK` - 友邦保险
- `2318.HK` - 中国平安

---

## 限流说明

### 官方限制

- **请求数量**：约 2000 次/小时
- **超出限制**：可能被临时封禁 IP
- **延迟时间**：15-20 分钟（免费版）

### 推荐配置

| 配置项 | 推荐值 | 说明 |
|--------|--------|------|
| 每小时请求量 | 1800次 | 留200次余量 |
| 每分钟请求量 | 30次 | 均匀分布 |
| 请求间隔 | 2秒 | 最小间隔 |
| 批量大小 | 100只 | 批量获取上限 |

### 最佳实践

**DO（推荐做法）**：
- 使用 yfinance 库而非直接调用 API
- 实现限流器，避免超限
- 批量获取时控制并发数
- 缓存已获取的数据
- 实现重试机制

**DON'T（避免做法）**：
- 循环请求时没有限流
- 忽略 API 错误直接重试
- 重复获取相同数据

---

## 常见问题

### 1. 错误处理

**问题1：403 Forbidden**

原因：IP被封禁（超过限流）

解决方案：
1. 等待1小时后重试
2. 减少请求频率
3. 考虑使用代理IP

---

**问题2：No data found**

原因：股票代码错误或已退市

解决方案：
1. 检查股票代码格式（需要 .HK 后缀）
2. 在 Yahoo Finance 网站验证代码
3. 尝试降级到其他数据源

---

**问题3：KeyError: 'longName'**

原因：ticker.info 字段可能缺失

解决方案：
1. 使用 info.get('longName') 避免 KeyError
2. 检查数据是否有效

---

### 2. 数据质量问题

**问题：财务数据不完整**

可能原因：
1. Yahoo Finance 对港股财务数据覆盖不全
2. 部分港股缺少财务报表

解决方案：
- 优先使用 AkShare 获取港股财务数据
- Yahoo Finance 作为补充或验证

---

**问题：价格出现 NaN**

可能原因：
1. 停牌日
2. 数据缺失

解决方案：
- 填充前一日价格
- 标记为无效数据

---

## 参考资料

- [Yahoo Finance 官网](https://finance.yahoo.com)
- [yfinance GitHub](https://github.com/ranaroussi/yfinance)
- [yfinance 文档](https://pypi.org/project/yfinance/)

---

**最后更新**：2026-01-03
**文档版本**：v2.0（港股版）
