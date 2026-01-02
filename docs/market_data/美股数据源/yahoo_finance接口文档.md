# Yahoo Finance 美股接口文档

**版本**：v2.0
**创建日期**：2025-01-02
**更新日期**：2026-01-03
**适用市场**：美股
**推荐优先级**：首选（免费、稳定、数据全）

---

## 数据源简介

### 基本信息

| 项目 | 说明 |
|------|------|
| **官网** | [https://finance.yahoo.com](https://finance.yahoo.com) |
| **API 基地址** | https://query1.finance.yahoo.com |
| **类型** | 完全免费 |
| **调用限制** | 约2000次/小时（硬性限制） |
| **数据质量** | ⭐⭐⭐⭐⭐（极高） |
| **稳定性** | ⭐⭐⭐⭐⭐（高） |

### 数据特点

**优势**：
- 完全免费，无需注册
- 数据权威，来源可靠
- 稳定性高，官方接口
- 美股数据覆盖最全面
- 历史数据可追溯数十年
- 支持多种数据类型
- 支持期权等高级数据

**劣势**：
- 无官方 Python SDK（需使用 yfinance 第三方库）
- 免费版有15-20分钟延迟
- 有限流限制（2000次/小时）

### 推荐使用场景

- 美股市场数据首选
- 获取美股历史数据
- 获取美股完整财务报表
- 获取美股公司详细信息
- 获取美股期权数据
- 获取美股分析师评级

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
ticker = yf.Ticker('AAPL')

# 获取历史数据
hist = ticker.history(period="1mo")
print(hist.head())

# 获取公司信息
info = ticker.info
print(info.get('longName'))
```

---

## 美股接口

### 1. 历史K线数据

**接口地址**：`/v8/finance/chart/{symbol}`

**功能**：获取美股历史K线数据（OHLCV）

**支持数据类型**：
- 日K线（1d）
- 周K线（1wk）
- 月K线（1mo）
- 分钟K线（1m, 2m, 5m, 15m, 30m, 60m, 90m）
- 盘前/盘后数据

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `symbol` | string | ✅ | 股票代码（如 "AAPL"） |
| `interval` | string | ❌ | 时间间隔，默认 "1d" |
| `range` | string | ❌ | 数据范围，如 "1y", "5y", "max" |
| `period1` | int | ❌ | 开始时间戳 |
| `period2` | int | ❌ | 结束时间戳 |
| `includePrePost` | bool | ❌ | 是否包含盘前盘后 |

**interval 可选值**：
- `1m`, `2m`, `5m`, `15m`, `30m`, `60m`, `90m` - 分钟K线
- `1h` - 小时K线
- `1d` - 日K线（默认）
- `1wk` - 周K线
- `1mo` - 月K线

**range 可选值**：
- `1d`, `5d`, `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`, `10y`, `ytd`, `max`

**返回字段**：

| Yahoo Finance 字段 | 标准字段 | 类型 | 说明 |
|-------------------|---------|------|------|
| `open` | `open` | float | 开盘价（美元） |
| `high` | `high` | float | 最高价（美元） |
| `low` | `low` | float | 最低价（美元） |
| `close` | `close` | float | 收盘价（美元） |
| `volume` | `volume` | int | 成交量（股） |
| `adjclose` | `adj_close` | float | 复权收盘价 |
| `date` | `trade_date` | string | 交易日期 |

**示例代码**：

```python
import yfinance as yf

# 获取苹果公司历史日线数据
ticker = yf.Ticker('AAPL')
hist = ticker.history(
    interval="1d",
    start="2020-01-01",
    end="2024-12-31"
)
print(hist.head())

# 获取1分钟数据
hist_1m = ticker.history(interval="1m", period="1d")

# 获取盘前盘后数据
hist_prepost = ticker.history(
    interval="1d",
    period="1mo",
    prepost=True  # 包含盘前盘后
)

# 获取周线数据
hist_weekly = ticker.history(interval="1wk", period="1y")

# 获取全部历史数据
hist_max = ticker.history(period="max")
```

---

### 2. 实时行情数据

**接口地址**：`/v6/finance/quote`

**功能**：获取美股实时报价数据

**支持数据**：
- 最新价格
- 涨跌幅
- 成交量/成交额
- 52周高低
- 市值
- PE/PB 比率
- 盘前盘后价格

**返回字段**：

| Yahoo Finance 字段 | 标准字段 | 类型 | 说明 |
|-------------------|---------|------|------|
| `regularMarketPrice` | `price` | float | 最新价（美元） |
| `regularMarketPreviousClose` | `pre_close` | float | 昨收价（美元） |
| `regularMarketOpen` | `open` | float | 开盘价（美元） |
| `regularMarketDayHigh` | `high` | float | 最高价（美元） |
| `regularMarketDayLow` | `low` | float | 最低价（美元） |
| `regularMarketVolume` | `volume` | int | 成交量（股） |
| `fiftyTwoWeekHigh` | `high_52w` | float | 52周最高（美元） |
| `fiftyTwoWeekLow` | `low_52w` | float | 52周最低（美元） |
| `marketCap` | `market_cap` | int | 市值（美元） |
| `trailingPE` | `pe_ratio` | float | 市盈率 |
| `preMarketPrice` | `pre_market_price` | float | 盘前价格 |
| `postMarketPrice` | `post_market_price` | float | 盘后价格 |

**示例代码**：

```python
import yfinance as yf

# 获取苹果公司实时行情
ticker = yf.Ticker('AAPL')
info = ticker.info

print(f"最新价: {info.get('regularMarketPrice')}")
print(f"涨跌幅: {info.get('regularMarketChangePercent')}%")
print(f"成交量: {info.get('regularMarketVolume')}")
print(f"市值: {info.get('marketCap')}")
print(f"52周最高: {info.get('fiftyTwoWeekHigh')}")
print(f"52周最低: {info.get('fiftyTwoWeekLow')}")
```

---

### 3. 公司基本信息

**接口地址**：`/v10/finance/quoteSummary/{symbol}`

**模块**：`assetProfile`

**功能**：获取美股公司基本面信息

**支持数据**：
- 公司名称
- 行业分类
- 业务简介
- 公司网址
- 员工数量
- 总部地址
- 成立日期
- CEO 信息
- 公司电话

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
| `state` | `state` | string | 所在州 |
| `country` | `country` | string | 所在国家 |
| `address1` | `address` | string | 详细地址 |
| `companyOfficers` | `officers` | list | 高管信息 |
| `phone` | `phone` | string | 公司电话 |

**示例代码**：

```python
import yfinance as yf

# 获取苹果公司信息
ticker = yf.Ticker('AAPL')
info = ticker.info

print(f"公司名称: {info.get('longName')}")
print(f"所属行业: {info.get('industry')}")
print(f"所属板块: {info.get('sector')}")
print(f"业务描述: {info.get('longBusinessSummary')}")
print(f"公司网址: {info.get('website')}")
print(f"员工数量: {info.get('fullTimeEmployees')}")
print(f"总部地址: {info.get('city')}, {info.get('state')}, {info.get('country')}")
```

---

### 4. 财务报表数据

**接口地址**：`/v10/finance/quoteSummary/{symbol}`

**模块**：
- `incomeStatementHistory` - 利润表
- `balanceSheetHistory` - 资产负债表
- `cashflowStatementHistory` - 现金流量表

**功能**：获取美股三大财务报表（数据最全面）

**支持数据**：
- 营业收入
- 净利润
- 总资产
- 总负债
- 经营现金流
- 多年期数据（通常4年）
- 季度数据

**示例代码**：

```python
import yfinance as yf

# 获取苹果公司财务报表
ticker = yf.Ticker('AAPL')

# 获取年度利润表
income_stmt = ticker.income_stmt
print("年度利润表:")
print(income_stmt.head())

# 获取季度利润表
income_stmt_quarterly = ticker.quarterly_income_stmt
print("\n季度利润表:")
print(income_stmt_quarterly.head())

# 获取资产负债表
balance_sheet = ticker.balance_sheet
print("\n资产负债表:")
print(balance_sheet.head())

# 获取现金流量表
cash_flow = ticker.cashflow
print("\n现金流量表:")
print(cash_flow.head())

# 获取特定财务指标
# 营业收入
revenue = income_stmt.loc['Total Revenue']
print(f"\n最近一年营业收入: {revenue.iloc[0]}")

# 净利润
net_income = income_stmt.loc['Net Income']
print(f"最近一年净利润: {net_income.iloc[0]}")
```

---

### 5. 财务指标数据

**接口地址**：`/v10/finance/quoteSummary/{symbol}`

**模块**：`defaultKeyStatistics`

**功能**：获取美股关键财务指标

**支持数据**：
- 市值
- PE/PB/PS 比率
- ROE/ROA
- 每股收益（EPS）
- 股息率
- Beta系数
- 52周高低
- 企业价值
- 自由现金流

**示例代码**：

```python
import yfinance as yf

# 获取苹果公司财务指标
ticker = yf.Ticker('AAPL')
info = ticker.info

print(f"市值: {info.get('marketCap'):,} 美元")
print(f"市盈率: {info.get('trailingPE')}")
print(f"市净率: {info.get('priceToBook')}")
print(f"市销率: {info.get('priceToSalesTrailing12Months')}")
print(f"股息率: {info.get('dividendYield')}%")
print(f"Beta系数: {info.get('beta')}")
print(f"ROE: {info.get('returnOnEquity')}%")
print(f"每股收益(EPS): {info.get('trailingEps')} 美元")
print(f"52周最高: {info.get('fiftyTwoWeekHigh')} 美元")
print(f"52周最低: {info.get('fiftyTwoWeekLow')} 美元")
```

---

### 6. 期权数据

**接口地址**：`/v7/finance/options/{symbol}`

**功能**：获取美股期权链数据

**支持数据**：
- 看涨/看跌期权
- 行权价
- 到期日
- 隐含波动率
- 希腊字母（Delta, Gamma, Theta, Vega）
- 权利金
- 未平仓合约

**示例代码**：

```python
import yfinance as yf

# 获取苹果期权数据
ticker = yf.Ticker('AAPL')

# 获取所有可用到期日
expirations = ticker.options
print(f"可用到期日: {expirations}")

# 获取特定到期日的期权链
opt = ticker.option_chain('2024-02-16')

# 看涨期权
calls = opt.calls
print("\n看涨期权:")
print(calls.head())

# 看跌期权
puts = opt.puts
print("\n看跌期权:")
print(puts.head())
```

---

### 7. 分析师评级

**接口地址**：`/v10/finance/quoteSummary/{symbol}`

**模块**：`upgradeDowngradeHistory`

**功能**：获取美股分析师评级调整历史

**支持数据**：
- 评级机构
- 评级调整
- 目标价
- 调整日期

**示例代码**：

```python
import yfinance as yf

# 获取苹果公司分析师评级
ticker = yf.Ticker('AAPL')

# 获取评级信息
info = ticker.info

# 当前评级
print(f"当前评级: {info.get('recommendationKey')}")
print(f"分析师数量: {info.get('numberOfAnalystOpinions')}")
print(f"目标价: {info.get('targetMeanPrice')} 美元")
print(f"目标价范围: {info.get('targetLowPrice')} - {info.get('targetHighPrice')} 美元")

# 评级分布
print(f"\n强力买入: {info.get('strongBuy')} 位分析师")
print(f"买入: {info.get('buy')} 位分析师")
print(f"持有: {info.get('hold')} 位分析师")
print(f"卖出: {info.get('sell')} 位分析师")
print(f"强力卖出: {info.get('strongSell')} 位分析师")
```

---

### 8. 持仓数据

**接口地址**：`/v13/finance/quoteSummary/{symbol}`

**模块**：`institutionOwnership` / `fundOwnership`

**功能**：获取美股机构/基金持仓数据

**支持数据**：
- 机构名称
- 持仓比例
- 持仓变化
- 持股数量

**示例代码**：

```python
import yfinance as yf

# 获取苹果公司机构持仓
ticker = yf.Ticker('AAPL')
info = ticker.info

# 主要机构持股
print(f"机构持股比例: {info.get('heldPercentInstitutions')}%")
print(f"内部人持股比例: {info.get('heldPercentInsiders')}%")
```

---

### 9. 内幕交易

**接口地址**：`/v13/finance/quoteSummary/{symbol}`

**模块**：`insiderTransactions`

**功能**：获取美股内幕交易数据

**支持数据**：
- 内部人员姓名
- 交易类型（买入/卖出）
- 交易数量
- 交易价格
- 交易日期

**示例代码**：

```python
import yfinance as yf

# 获取苹果公司内幕交易
ticker = yf.Ticker('AAPL')

# 获取内幕交易信息
insider_trades = ticker.insider_transactions
print(insider_trades.head())
```

---

### 10. 股息数据

**接口地址**：`/v13/finance/quoteSummary/{symbol}`

**模块**：`dividendHistory`

**功能**：获取美股股息分红历史

**支持数据**：
- 分红日期
- 分红金额
- 分红频率
- 分红收益率

**示例代码**：

```python
import yfinance as yf

# 获取苹果公司分红历史
ticker = yf.Ticker('AAPL')

# 获取分红历史
dividends = ticker.dividends
print("分红历史:")
print(dividends.tail(10))

# 获取分红信息
info = ticker.info
print(f"\n股息率: {info.get('dividendRate')} 美元")
print(f"分红收益率: {info.get('dividendYield')}%")
print(f"分红频率: {info.get('lastDividendValue')}")
```

---

### 11. 股票拆分数据

**接口地址**：`/v13/finance/quoteSummary/{symbol}`

**模块**：`splitHistory`

**功能**：获取美股股票拆分历史

**支持数据**：
- 拆分日期
- 拆分比例

**示例代码**：

```python
import yfinance as yf

# 获取苹果公司拆分历史
ticker = yf.Ticker('AAPL')
splits = ticker.splits
print("股票拆分历史:")
print(splits.tail())
```

---

### 12. 市场热门股票

**接口地址**：`/v1/finance/trending/{region}`

**功能**：获取美股市场热门股票列表

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `region` | string | ✅ | 区域代码，美股使用 "US" |

**示例代码**：

```python
import yfinance as yf

# 获取美股热门股票
trending = yf.Trending('US')
print("美股热门股票:")
print(trending)
```

---

### 13. 公司新闻

**接口地址**：`/v1/finance/news-stories`

**功能**：获取美股公司相关新闻

**支持数据**：
- 新闻标题
- 发布时间
- 新闻来源
- 摘要内容
- 新闻链接

**示例代码**：

```python
import yfinance as yf

# 获取苹果公司新闻
ticker = yf.Ticker('AAPL')
news = ticker.news
print("最新新闻:")
for item in news[:5]:
    print(f"\n标题: {item['title']}")
    print(f"发布时间: {item['providerPublishTime']}")
    print(f"来源: {item['publisher']}")
    print(f"链接: {item['link']}")
```

---

## 美股代码格式

| 格式 | 示例 | 说明 |
|------|------|------|
| Yahoo格式 | `AAPL`, `TSLA`, `MSFT` | 直接使用股票代码 |
| 标准格式 | `AAPL.US`, `TSLA.US` | 添加 `.US` 后缀 |

**常用美股代码示例**：
- `AAPL` - 苹果公司
- `MSFT` - 微软
- `GOOGL` / `GOOG` - 谷歌（Alphabet）
- `AMZN` - 亚马逊
- `TSLA` - 特斯拉
- `META` - Meta（Facebook）
- `NVDA` - 英伟达
- `JPM` - 摩根大通
- `V` - Visa
- `JNJ` - 强生公司

**美股交易所后缀**（通常不需要）：
- 纳斯达克：无需后缀
- 纽交所：无需后缀

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
- 记录详细日志

**DON'T（避免做法）**：
- 循环请求时没有限流
- 忽略 API 错误直接重试
- 重复获取相同数据
- 不处理异常情况

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
1. 检查股票代码格式
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

**问题：成交量异常大**

可能原因：
1. 数据未调整（如股票拆分）
2. Yahoo Finance 数据错误

解决方案：
- 使用 Adj Close 字段进行复权
- 对比其他数据源验证

---

**问题：价格出现 NaN**

可能原因：
1. 停牌日
2. 数据缺失

解决方案：
- 填充前一日价格
- 标记为无效数据

---

### 3. 性能优化

**问题：批量获取速度慢**

优化方案：
1. 使用多线程（需控制并发数）
2. 实现请求队列
3. 减少不必要的字段获取

---

## 参考资料

- [Yahoo Finance 官网](https://finance.yahoo.com)
- [yfinance GitHub](https://github.com/ranaroussi/yfinance)
- [yfinance 文档](https://pypi.org/project/yfinance/)

---

**最后更新**：2026-01-03
**文档版本**：v2.0（美股版）
