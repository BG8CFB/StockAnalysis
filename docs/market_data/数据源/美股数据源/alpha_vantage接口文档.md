# Alpha Vantage 美股接口文档

**版本**：v2.0
**创建日期**：2025-01-02
**更新日期**：2026-01-03
**适用市场**：美股
**推荐优先级**：备用（Yahoo Finance 失败时）

---

## 数据源简介

### 基本信息

| 项目 | 说明 |
|------|------|
| **官网** | [https://www.alphavantage.co](https://www.alphavantage.co) |
| **API 地址** | https://www.alphavantage.co/query |
| **类型** | 免费 + 付费 |
| **认证方式** | API Key（需申请） |
| **免费额度** | 5次/分钟，500次/天 |
| **付费额度** | 更高限制（需订阅） |
| **数据质量** | ⭐⭐⭐⭐（高） |
| **稳定性** | ⭐⭐⭐⭐（高） |

### 数据特点

**优势**：
- 官方 API，稳定可靠
- 数据权威，质量高
- 免费版可用（有限制）
- 支持实时行情
- 支持技术指标（20+种）
- 官方 Python SDK
- 支持复权数据

**劣势**：
- 需要申请 API Key
- 免费版限制较多（5次/分钟）
- 付费版价格较高
- 限流严格

### 推荐使用场景

- 作为 Yahoo Finance 失用时的降级选项
- 获取美股技术指标数据
- 获取美股财务报表数据
- 需要复权数据时

### 美股数据优先级

1. Yahoo Finance（免费首选）
2. AkShare（备用）
3. Alpha Vantage（备用，需 API Key）

---

## 账号申请与配置

### 申请 API Key

1. 访问 [Alpha Vantage 官网](https://www.alphavantage.co/support/#api-key)
2. 填写邮箱和姓名
3. 系统自动生成 API Key
4. API Key 会发送到邮箱

**注意**：
- 免费 API Key 永久有效
- 每个邮箱只能申请一个 API Key
- 请妥善保管 API Key

### API Key 配置

配置方式：
1. **环境变量**：`ALPHA_VANTAGE_API_KEY`
2. **配置文件**：存储在项目配置中
3. **加密存储**：推荐在生产环境使用加密存储

### 测试 API Key

测试接口：
- **接口**：`GLOBAL_QUOTE`
- **参数**：`symbol=IBM`
- **返回**：IBM 股票报价

成功返回表示 API Key 有效。

---

## 美股接口

### 1. 股票数据接口

#### 1.1 实时行情报价

**功能**：获取实时或延迟的股票报价

**接口地址**：`/query`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `function` | string | ✅ | 固定值：`GLOBAL_QUOTE` |
| `symbol` | string | ✅ | 股票代码，如 `IBM`, `AAPL` |
| `apikey` | string | ✅ | API Key |

**返回字段**：

| Alpha Vantage 字段 | 标准字段 | 类型 | 说明 |
|-------------------|---------|------|------|
| `01. symbol` | `symbol` | string | 股票代码 |
| `02. open` | `open` | float | 开盘价（美元） |
| `03. high` | `high` | float | 最高价（美元） |
| `04. low` | `low` | float | 最低价（美元） |
| `05. price` | `price` | float | 最新价（美元） |
| `06. volume` | `volume` | int | 成交量（股） |
| `07. latest trading day` | `trade_date` | string | 交易日期 |
| `08. previous close` | `pre_close` | float | 昨收价（美元） |
| `09. change` | `change` | float | 涨跌额（美元） |
| `10. change percent` | `change_pct` | float | 涨跌幅（%） |

---

#### 1.2 历史K线数据（日线）

**功能**：获取历史日线数据

**接口地址**：`/query`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `function` | string | ✅ | 固定值：`TIME_SERIES_DAILY` |
| `symbol` | string | ✅ | 股票代码 |
| `outputsize` | string | ❌ | 输出大小，`compact`（最近100天）或 `full`（全部历史） |
| `apikey` | string | ✅ | API Key |

**返回字段**：

| Alpha Vantage 字段 | 标准字段 | 类型 | 说明 |
|-------------------|---------|------|------|
| `1. open` | `open` | float | 开盘价（美元） |
| `2. high` | `high` | float | 最高价（美元） |
| `3. low` | `low` | float | 最低价（美元） |
| `4. close` | `close` | float | 收盘价（美元） |
| `5. volume` | `volume` | int | 成交量（股） |

---

#### 1.3 历史K线数据（调整后/复权）

**功能**：获取调整后的历史K线数据（复权）

**接口地址**：`/query`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `function` | string | ✅ | 固定值：`TIME_SERIES_DAILY_ADJUSTED` |
| `symbol` | string | ✅ | 股票代码 |
| `outputsize` | string | ❌ | 输出大小 |
| `apikey` | string | ✅ | API Key |

**返回字段**：

| Alpha Vantage 字段 | 标准字段 | 类型 | 说明 |
|-------------------|---------|------|------|
| `1. open` | `open` | float | 开盘价（美元） |
| `2. high` | `high` | float | 最高价（美元） |
| `3. low` | `low` | float | 最低价（美元） |
| `4. close` | `close` | float | 收盘价（美元） |
| `5. adjusted close` | `adj_close` | float | 复权收盘价 |
| `6. volume` | `volume` | int | 成交量（股） |
| `7. dividend amount` | `dividend` | float | 分红金额（美元） |
| `8. split coefficient` | `split_coeff` | float | 拆股系数 |

---

#### 1.4 历史K线数据（周线/月线）

**功能**：获取历史周/月K线数据

**接口地址**：`/query`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `function` | string | ✅ | `TIME_SERIES_WEEKLY`（周线）或 `TIME_SERIES_MONTHLY`（月线） |
| `symbol` | string | ✅ | 股票代码 |
| `apikey` | string | ✅ | API Key |

---

#### 1.5 分钟K线数据

**功能**：获取分钟级K线数据（日内）

**接口地址**：`/query`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `function` | string | ✅ | 固定值：`TIME_SERIES_INTRADAY` |
| `symbol` | string | ✅ | 股票代码 |
| `interval` | string | ✅ | 时间间隔：1min, 5min, 15min, 30min, 60min |
| `outputsize` | string | ❌ | 输出大小 |
| `apikey` | string | ✅ | API Key |

**注意**：分钟数据仅保留最近30天

---

#### 1.6 公司概览信息

**功能**：获取公司基本信息

**接口地址**：`/query`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `function` | string | ✅ | 固定值：`OVERVIEW` |
| `symbol` | string | ✅ | 股票代码 |
| `apikey` | string | ✅ | API Key |

**返回字段**：
- 公司名称、行业、板块
- 市值、PE、股息率
- 业务描述
- 52周高低
- 每股收益、净利润率
- Beta系数、账面价值

---

#### 1.7 收益公告

**功能**：获取公司收益公告日历

**接口地址**：`/query`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `function` | string | ✅ | 固定值：`EARNINGS` |
| `symbol` | string | ✅ | 股票代码 |
| `apikey` | string | ✅ | API Key |

**返回字段**：
- 财报季度
- 公告日期
- 每股收益（预估/实际）

---

#### 1.8 IPO 日历

**功能**：获取未来3个月的IPO日历

**接口地址**：`/query`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `function` | string | ✅ | 固定值：`IPO_CALENDAR` |
| `apikey` | string | ✅ | API Key |

---

### 2. 财务报表接口

#### 2.1 利润表

**功能**：获取利润表数据

**接口地址**：`/query`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `function` | string | ✅ | 固定值：`INCOME_STATEMENT` |
| `symbol` | string | ✅ | 股票代码 |
| `apikey` | string | ✅ | API Key |

**返回数据**：
- 年度报告和季度报告
- 营业收入、毛利润
- 研发费用、利息支出
- 净利润

---

#### 2.2 资产负债表

**功能**：获取资产负债表数据

**接口地址**：`/query`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `function` | string | ✅ | 固定值：`BALANCE_SHEET` |
| `symbol` | string | ✅ | 股票代码 |
| `apikey` | string | ✅ | API Key |

**返回数据**：
- 总资产、流动资产
- 总负债、流动负债
- 股东权益

---

#### 2.3 现金流量表

**功能**：获取现金流量表数据

**接口地址**：`/query`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `function` | string | ✅ | 固定值：`CASH_FLOW` |
| `symbol` | string | ✅ | 股票代码 |
| `apikey` | string | ✅ | API Key |

**返回数据**：
- 经营现金流
- 投资现金流
- 筹资现金流
- 自由现金流

---

#### 2.4 财务报表综合

**功能**：一次性获取三大财务报表

**接口地址**：`/query`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `function` | string | ✅ | 固定值：`FINANCIAL_STATEMENTS` |
| `symbol` | string | ✅ | 股票代码 |
| `apikey` | string | ✅ | API Key |

---

### 3. 技术指标接口

Alpha Vantage 内置 20+ 种技术指标，适用于美股技术分析。

#### 3.1 SMA（简单移动平均）

**接口地址**：`/query`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `function` | string | ✅ | 固定值：`SMA` |
| `symbol` | string | ✅ | 股票代码 |
| `interval` | string | ✅ | 时间间隔：daily, weekly, monthly |
| `time_period` | string | ✅ | 周期，如 5, 10, 20, 50, 200 |
| `series_type` | string | ✅ | 价格类型：close, open, high, low |
| `apikey` | string | ✅ | API Key |

---

#### 3.2 EMA（指数移动平均）

**接口地址**：`/query`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `function` | string | ✅ | 固定值：`EMA` |
| `symbol` | string | ✅ | 股票代码 |
| `interval` | string | ✅ | 时间间隔 |
| `time_period` | string | ✅ | 周期 |
| `series_type` | string | ✅ | 价格类型 |
| `apikey` | string | ✅ | API Key |

---

#### 3.3 RSI（相对强弱指标）

**接口地址**：`/query`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `function` | string | ✅ | 固定值：`RSI` |
| `symbol` | string | ✅ | 股票代码 |
| `interval` | string | ✅ | 时间间隔 |
| `time_period` | string | ✅ | 周期，默认 14 |
| `series_type` | string | ✅ | 价格类型 |
| `apikey` | string | ✅ | API Key |

---

#### 3.4 MACD

**接口地址**：`/query`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `function` | string | ✅ | 固定值：`MACD` |
| `symbol` | string | ✅ | 股票代码 |
| `interval` | string | ✅ | 时间间隔 |
| `series_type` | string | ✅ | 价格类型 |
| `fastperiod` | string | ❌ | 快线周期，默认 12 |
| `slowperiod` | string | ❌ | 慢线周期，默认 26 |
| `signalperiod` | string | ❌ | 信号线周期，默认 9 |
| `apikey` | string | ✅ | API Key |

---

#### 3.5 BOLLINGER（布林带）

**接口地址**：`/query`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `function` | string | ✅ | 固定值：`BBANDS` |
| `symbol` | string | ✅ | 股票代码 |
| `interval` | string | ✅ | 时间间隔 |
| `time_period` | string | ✅ | 周期，默认 20 |
| `series_type` | string | ✅ | 价格类型 |
| `nbdevup` | string | ❌ | 上轨标准差，默认 2 |
| `nbdevdn` | string | ❌ | 下轨标准差，默认 2 |
| `apikey` | string | ✅ | API Key |

---

#### 3.6 STOCH（随机指标）

**接口地址**：`/query`

**请求参数**：

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `function` | string | ✅ | 固定值：`STOCH` |
| `symbol` | string | ✅ | 股票代码 |
| `interval` | string | ✅ | 时间间隔 |
| `fastkperiod` | string | ❌ | 快线K周期，默认 5 |
| `slowkperiod` | string | ❌ | 慢线K周期，默认 3 |
| `slowdperiod` | string | ❌ | 慢线D周期，默认 3 |
| `apikey` | string | ✅ | API Key |

---

#### 3.7 其他技术指标

支持的其他指标：
- **WMA** - 加权移动平均
- **DEMA** - 双指数移动平均
- **TEMA** - 三指数移动平均
- **TRIMA** - 三角移动平均
- **T3** - T3 指标
- **WILLR** - 威廉指标
- **ADX** - 平均趋向指标
- **CCI** - 顺势指标
- **AROON** - 阿隆指标
- **STOCHF** - 快速随机指标
- **STOCHRSI** - 随机RSI
- **MAMA** - MESA 自适应移动平均
- **MACDEXT** - 扩展MACD

---

## 请求参数说明

### 通用参数

| 参数名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `function` | string | ✅ | API 功能类型 |
| `apikey` | string | ✅ | API Key |
| `datatype` | string | ❌ | 返回格式：json（默认）或 csv |

### 时间间隔参数

**适用接口**：分钟K线、技术指标

| 值 | 说明 |
|----|------|
| `1min` | 1分钟 |
| `5min` | 5分钟 |
| `15min` | 15分钟 |
| `30min` | 30分钟 |
| `60min` | 60分钟 |
| `daily` | 日线 |
| `weekly` | 周线 |
| `monthly` | 月线 |

### 输出大小参数

| 值 | 说明 |
|----|------|
| `compact` | 最近100条数据（默认） |
| `full` | 全部历史数据 |

### 价格类型参数

**适用接口**：技术指标

| 值 | 说明 |
|----|------|
| `close` | 收盘价（默认） |
| `open` | 开盘价 |
| `high` | 最高价 |
| `low` | 最低价 |

---

## 美股代码格式

| Alpha Vantage 格式 | 标准格式 | 转换规则 |
|-------------------|---------|---------|
| `IBM` | `IBM.US` | 添加 `.US` 后缀 |
| `AAPL` | `AAPL.US` | 添加 `.US` 后缀 |
| `TSLA` | `TSLA.US` | 添加 `.US` 后缀 |

**常用美股代码示例**：
- `AAPL` - 苹果公司
- `MSFT` - 微软
- `GOOGL` / `GOOG` - 谷歌
- `AMZN` - 亚马逊
- `TSLA` - 特斯拉
- `META` - Meta（Facebook）
- `NVDA` - 英伟达
- `JPM` - 摩根大通

---

## 限流说明

### 免费版限制

| 限制类型 | 数值 |
|---------|------|
| 每分钟请求 | 5次 |
| 每天请求 | 500次 |
| 分钟限制重置 | 滚动窗口 |
| 天限制重置 | 太平洋时间午夜 |

### 付费版对比

| 套餐 | 每分钟请求 | 每天请求 | 价格 |
|------|-----------|---------|------|
| 免费版 | 5次 | 500次 | $0 |
| Micro | 30次 | 15,000次 | $49.99/月 |
| Starter | 75次 | 75,000次 | $99.99/月 |
| Premium | 600次 | 300,000次 | $499.99/月 |

### 推荐配置

| 配置项 | 推荐值 | 说明 |
|--------|--------|------|
| 请求间隔 | 12秒 | 5次/分钟 = 12秒/次 |
| 重试次数 | 3次 | 超限后重试 |
| 重试延迟 | 60秒 | 等待限流重置 |

### 最佳实践

**DO（推荐做法）**：
- 实现严格的限流控制
- 缓存已获取的数据
- 优先使用 Yahoo Finance
- 作为备用数据源
- 使用官方 SDK

**DON'T（避免做法）**：
- 作为主数据源（美股）
- 不控制请求频率
- 忽略 API 错误直接重试
- 重复获取相同数据

---

## 常见问题

### 1. API 错误

**错误1：Invalid API Key**

原因：API Key 错误或未激活

解决方案：
1. 检查 API Key 是否正确
2. 重新申请 API Key
3. 检查邮箱中的激活邮件

---

**错误2：premium subscription**

原因：使用了仅限付费版的功能

解决方案：
1. 切换到免费版支持的功能
2. 或订阅付费计划

---

**错误3：higher rate limit**

原因：超过免费版限流

解决方案：
1. 等待限流重置
2. 升级到付费版
3. 减少请求频率

---

### 2. 数据问题

**问题：返回数据为空**

可能原因：
1. 股票代码错误
2. API 限制
3. 网络问题

解决方案：
1. 验证股票代码
2. 检查 API 限制
3. 实现重试机制
4. 降级到其他数据源

---

**问题：分钟数据不全**

原因：分钟数据仅保留最近30天

解决方案：
1. 使用日线数据获取更长历史
2. 定期保存分钟数据

---

### 3. 性能优化

**问题：请求速度慢**

优化方案：
1. 实现请求缓存
2. 批量获取数据（如果API支持）
3. 异步请求（需确保不超过限流）

---

## 参考资料

- [Alpha Vantage 官网](https://www.alphavantage.co)
- [API Key 申请](https://www.alphavantage.co/support/#api-key)
- [官方文档](https://www.alphavantage.co/documentation/)
- [Python SDK](https://github.com/RomelTorres/alpha_vantage)

---

**最后更新**：2026-01-03
**文档版本**：v2.0（美股版）
