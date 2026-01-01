# 股票数据源模块设计方案

**版本**：v2.0
**创建日期**：2025-01-01
**最后更新**：2025-01-01
**状态**：待审核
**作者**：Claude AI

---

## 文档修订记录

| 版本 | 日期 | 修订内容 | 修订人 |
|------|------|---------|--------|
| v1.0 | 2025-01-01 | 初始版本（多租户方案） | Claude AI |
| v2.0 | 2025-01-01 | 简化为管理员统一配置方案 | Claude AI |

---

## 目录

- [一、模块定位与目标](#一模块定位与目标)
- [二、核心概念界定](#二核心概念界定)
- [三、模块架构设计](#三模块架构设计)
- [四、核心业务逻辑设计](#四核心业务逻辑设计)
- [五、数据库设计](#五数据库设计)
- [六、API 端点设计](#六api-端点设计)
- [七、与 TradingAgents 集成方案](#七与-tradingagents-集成方案)
- [八、并发与限流策略](#八并发与限流策略)
- [九、错误处理与降级](#九错误处理与降级)
- [十、定时任务设计](#十定时任务设计)

---

## 一、模块定位与目标

### 1.1 模块定位

股票数据源模块（`market_data`）是一个**全局数据服务模块**，负责：

- 管理员统一配置 A股/美股/港股 数据源
- 系统定时拉取数据并存储到数据库
- 为所有业务模块提供本地数据查询服务
- 数据过期时自动触发接口更新
- 支持多数据源降级（主数据源失败自动切换）

### 1.2 核心目标

| 目标 | 描述 |
|------|------|
| **统一管理** | 管理员配置数据源，所有用户共享使用 |
| **本地化存储** | 数据存储在本地数据库，用户请求不从外部接口获取 |
| **自动更新** | 定时任务自动拉取最新数据，过期数据自动触发更新 |
| **多数据源降级** | 主数据源失败时自动切换备用数据源 |
| **高可用性** | 分布式锁、限流、缓存等多重保障机制 |

### 1.3 数据流程

```
┌─────────────────────────────────────────────────────────┐
│ 数据流程图                                               │
└─────────────────────────────────────────────────────────┘

管理员配置数据源（一次性）
    ↓
系统定时拉取数据（定时任务）
    ├─ A股：每天收盘后拉取日K线
    ├─ 美股：每天收盘后拉取日K线
    └─ 港股：每天收盘后拉取日K线
    ↓
数据存入数据库（全局共享）
    ├─ stock_quotes（行情数据）
    ├─ stock_financials（财务数据）
    └─ stock_companies（公司信息）
    ↓
用户请求数据（从本地数据库读取）
    ├─ 数据存在且未过期 → 直接返回
    └─ 数据不存在或已过期 → 触发接口更新后返回
```

### 1.4 适用场景

- **TradingAgents 智能体分析**：提供股票行情、财报、公司信息等数据
- **智能选股模块**：批量获取多只股票数据
- **AI 问股模块**：查询股票信息
- **仪表板模块**：展示市场概况和个股数据

---

## 二、核心概念界定

### 2.1 数据源类型

本系统**只支持公共数据源**，由管理员统一配置和管理。

#### 2.1.1 A股数据源

**可用数据源**：
- **Tushare（免费版）**：需要管理员申请Token
- **东方财富**：公开接口，免费
- **新浪财经**：公开接口，免费

**数据类型**：
- 实时行情：5分钟级别
- 日K线：历史和实时
- 财务报表：季报、年报
- 公司信息：基本信息、财务指标

#### 2.1.2 美股数据源

**可用数据源**：
- **Yahoo Finance**：免费接口
- **Alpha Vantage（免费版）**：需要管理员申请API Key

**数据类型**：
- 实时行情：1分钟级别
- 日K线：历史和实时
- 财务报表：季报、年报
- 公司信息：基本信息

#### 2.1.3 港股数据源

**可用数据源**：
- **Yahoo Finance**：免费接口
- **东方财富（港股）**：公开接口

**数据类型**：
- 实时行情：5分钟级别
- 日K线：历史和实时
- 财务报表：季报、年报
- 公司信息：基本信息

---

### 2.2 数据获取策略

#### 2.2.1 定时拉取（主动）

**策略**：系统定时任务自动拉取数据

```
A股数据更新时机：
├─ 日K线：每天 15:30（收盘后）
├─ 实时行情：交易时间内每5分钟
└─ 财务报表：每天 16:00 检查更新

美股数据更新时机：
├─ 日K线：每天 05:00（收盘后，北京时间）
├─ 实时行情：交易时间内每1分钟
└─ 财务报表：每天 06:00 检查更新

港股数据更新时机：
├─ 日K线：每天 16:30（收盘后）
├─ 实时行情：交易时间内每5分钟
└─ 财务报表：每天 17:00 检查更新
```

#### 2.2.2 按需更新（被动）

**触发条件**：
- 用户请求的数据不存在
- 数据已过期（超过TTL时间）

**流程**：
```
用户请求数据
    ↓
检查数据库
    ├─ 数据存在且未过期 → 直接返回
    └─ 数据不存在或已过期 → 触发接口更新
        ├─ 调用数据源接口
        ├─ 数据验证
        ├─ 存入数据库
        └─ 返回给用户
```

---

### 2.3 数据过期策略（TTL）

根据**天级预测**场景设计，不需要秒级/分钟级实时性。

| 数据类型 | TTL | 更新策略 |
|---------|-----|---------|
| A股实时行情 | 1天 | 每天收盘后更新一次 |
| A股日K线 | 1天 | 每天收盘后更新一次 |
| A股财务报表 | 7天 | 每周检查一次更新 |
| A股公司信息 | 30天 | 每月检查一次更新 |
| 美股实时行情 | 1天 | 每天收盘后更新一次 |
| 美股日K线 | 1天 | 每天收盘后更新一次 |
| 美股财务报表 | 7天 | 每周检查一次更新 |
| 美股公司信息 | 30天 | 每月检查一次更新 |

**TTL判断逻辑**：
```
数据是否过期：
└─ 如果（当前时间 - 数据更新时间）> TTL
    └─ 数据过期，触发接口更新
    └─ 否则使用缓存数据
```

---

## 三、模块架构设计

### 3.1 目录结构

```
backend/modules/market_data/
├── __init__.py
├── admin_api.py                            # 管理员 API（配置管理）
│
├── config/
│   ├── __init__.py
│   ├── schemas.py                          # 配置数据模型
│   └── service.py                          # 配置管理服务
│
├── sources/
│   ├── __init__.py
│   ├── base.py                             # 数据源抽象基类
│   ├── registry.py                         # 数据源注册表
│   ├── metadata/
│   │   └── sources_manifest.yaml           # 数据源清单
│   ├── a_stock/
│   │   ├── __init__.py
│   │   ├── tushare_adapter.py              # Tushare
│   │   ├── eastmoney_adapter.py            # 东方财富
│   │   └── sina_adapter.py                 # 新浪财经
│   ├── us_stock/
│   │   ├── __init__.py
│   │   ├── yahoo_adapter.py                # Yahoo Finance
│   │   └── alphavantage_adapter.py         # Alpha Vantage
│   └── hk_stock/
│       ├── __init__.py
│       ├── yahoo_adapter.py                # Yahoo Finance
│       └── eastmoney_adapter.py            # 东方财富（港股）
│
├── models/
│   ├── __init__.py
│   ├── data_config.py                      # 数据源配置模型
│   ├── stock_quote.py                      # 行情数据模型
│   ├── stock_financials.py                 # 财务数据模型
│   └── stock_company.py                    # 公司信息模型
│
├── services/
│   ├── __init__.py
│   ├── data_fetcher.py                     # 数据获取服务（按需更新）
│   ├── data_scheduler.py                   # 定时任务调度器
│   ├── storage_service.py                  # 数据存储服务
│   ├── rate_limiter.py                     # 限流服务
│   ├── lock_service.py                     # 分布式锁服务
│   └── validator.py                        # 数据验证服务
│
├── tools/
│   ├── __init__.py
│   ├── base_tool.py                        # 工具基类
│   ├── a_stock_tools.py                    # A股工具
│   ├── us_stock_tools.py                   # 美股工具
│   └── hk_stock_tools.py                   # 港股工具
│
└── tests/
    ├── test_adapters.py
    └── test_data_fetcher.py
```

### 3.2 模块职责划分

| 子模块 | 职责 |
|--------|------|
| **config/** | 数据源配置的 CRUD（管理员专用） |
| **sources/** | 数据源适配器实现，统一接口抽象 |
| **models/** | 数据库模型定义 |
| **services/** | 核心业务逻辑（获取、调度、验证、限流） |
| **tools/** | TradingAgents 工具集成 |
| **admin_api.py** | 管理员配置 API（用户不可见） |

---

## 四、核心业务逻辑设计

### 4.1 数据源配置模型

#### 4.1.1 配置结构

```yaml
数据源配置：
  source_id: "tushare"
  market: "A_STOCK"
  enabled: true
  priority: 1  # 优先级（数字越小优先级越高）

  # 数据源配置
  config:
    api_key: "encrypted_api_key"  # 加密存储
    base_url: "https://api.tushare.pro"
    timeout: 30  # 超时时间（秒）

  # 限流配置
  rate_limit:
    max_requests_per_minute: 1000
    max_requests_per_day: 10000

  # 数据类型支持
  supported_data_types:
    - "quote"      # 行情
    - "history"     # 历史K线
    - "financials"  # 财务报表
    - "company"     # 公司信息

  # 元数据
  metadata:
    created_at: datetime
    updated_at: datetime
    last_test_status: "success"  # success | failed
    last_tested_at: datetime
```

#### 4.1.2 多数据源优先级

```
每个市场可配置多个数据源，按优先级排序：

A股数据源示例：
├─ 1. Tushare（优先级1，主数据源）
├─ 2. 东方财富（优先级2，备用数据源）
└─ 3. 新浪财经（优先级3，降级数据源）

数据获取流程：
├─ 尝试优先级1：Tushare
│   ├─ 成功 → 返回数据
│   └─ 失败 → 降级到优先级2
├─ 尝试优先级2：东方财富
│   ├─ 成功 → 返回数据
│   └─ 失败 → 降级到优先级3
└─ 尝试优先级3：新浪财经
    ├─ 成功 → 返回数据
    └─ 失败 → 返回错误
```

---

### 4.2 数据获取流程

#### 4.2.1 按需更新流程

```
用户请求股票数据
    ↓
步骤1：检查数据库
├─ 查询条件：股票代码、市场、日期
├─ 判断数据是否存在
└─ 判断数据是否过期
    ↓
步骤2：数据存在且未过期
└─ 直接返回（最快）
    ↓
步骤3：数据不存在或已过期
├─ 尝试获取分布式锁（防止并发重复获取）
├─ 获取到锁 → 调用数据源接口
│   ├─ 按优先级尝试数据源
│   ├─ 数据验证
│   ├─ 标准化字段
│   ├─ 存入数据库
│   └─ 释放锁
└─ 未获取到锁 → 等待2秒，再次检查数据库
    └─ 其他用户已更新，直接返回
```

#### 4.2.2 分布式锁工作原理

**防止并发重复获取**：

```
场景：100个用户同时请求 AAPL 数据（缓存已过期）

没有分布式锁：
└─ 100个用户都调用API获取数据
    └─ 浪费99次API调用

有分布式锁：
├─ 用户1获取到锁 → 调用API获取数据
├─ 用户2-100未获取到锁 → 等待2秒
├─ 用户1获取完数据，释放锁
└─ 用户2-100等待结束，从数据库获取数据
    └─ 只调用1次API，节省99次
```

**锁的配置**：
| 参数 | 值 | 说明 |
|------|-----|------|
| 键格式 | `lock:data_fetch:{market}:{symbol}` | 例如：lock:data_fetch:A_STOCK:AAPL |
| 超时时间 | 30秒 | 防止死锁 |
| 等待时间 | 2秒 | 未获取锁的用户等待时间 |

---

### 4.3 数据验证机制

#### 4.3.1 验证流程

```
从API获取的原始数据
    ↓
步骤1：字段标准化
├─ 不同数据源字段名不同
├─ 统一为标准字段名
└─ 示例：Open/OPEN → open
    ↓
步骤2：完整性检查
├─ 检查必填字段
├─ 必填字段：open, high, low, close, volume
└─ 缺少 → 拒绝数据，尝试备用数据源
    ↓
步骤3：合理性检查
├─ 价格必须 > 0
├─ 成交量必须 >= 0
└─ 不合理 → 拒绝数据
    ↓
步骤4：一致性检查
├─ high >= low
├─ high >= open, high >= close
├─ low <= open, low <= close
└─ 不一致 → 拒绝数据
    ↓
步骤5：数据质量评分
├─ 完整性：40分
├─ 合理性：30分
└─ 一致性：30分
    ↓
验证通过的数据
├─ 质量评分 > 70分 → 存入数据库
└─ 质量评分 <= 70分 → 记录警告，但仍然存入
```

#### 4.3.2 验证规则详解

**完整性检查**：
```
必填字段：
├─ open（开盘价）
├─ high（最高价）
├─ low（最低价）
├─ close（收盘价）
└─ volume（成交量）

可选字段：
├─ amount（成交额）
├─ pe_ratio（市盈率）
└─ turnover_rate（换手率）
```

**一致性检查**：
```
规则1：high >= low
└─ 最高价必须 >= 最低价

规则2：high >= open 且 high >= close
└─ 最高价必须 >= 开盘价和收盘价

规则3：low <= open 且 low <= close
└─ 最低价必须 <= 开盘价和收盘价
```

**数据质量评分**：
```
总分：100分

维度1：完整性（40分）
└─ 必填字段完整率 × 40

维度2：合理性（30分）
└─ 价格、成交量合理性

维度3：一致性（30分）
└─ 价格关系一致性

评分等级：
├─ 90-100分：高质量
├─ 70-89分：中等质量
└─ <70分：低质量（记录警告）
```

---

### 4.4 限流策略

#### 4.4.1 为什么需要限流？

**场景**：数据源有调用频率限制

```
Yahoo Finance 免费API：
└─ 限制：2000次/小时
    └─ 超过 → IP被封锁，1小时无法使用

Tushare 免费API：
└─ 限制：1000次/分钟，10000次/天
    └─ 超过 → 返回错误，无法获取数据
```

#### 4.4.2 限流算法：令牌桶

**原理**：
```
令牌桶配置：
├─ 桶容量：100个令牌
├─ 补充速率：1个/秒
└─ 消耗规则：1次请求消耗1个令牌

工作流程：
├─ 正常情况：每秒1个请求（消耗1个，补充1个，保持平衡）
├─ 突发情况：可以瞬间发送100个请求（桶满了）
└─ 突发后：要等100秒才能恢复到100个令牌
```

**优点**：
- ✅ 允许突发流量（批量任务）
- ✅ 平滑限流（不会在时间边界突然重置）
- ✅ 适合定时任务场景

#### 4.4.3 限流配置

```
A股数据源限流：
├─ Tushare：1000次/分钟，10000次/天
├─ 东方财富：500次/分钟（保守估计）
└─ 新浪财经：500次/分钟

美股数据源限流：
├─ Yahoo Finance：1800次/小时（留200次余量）
└─ Alpha Vantage：5次/分钟（免费版限制）

港股数据源限流：
├─ Yahoo Finance：1800次/小时
└─ 东方财富：500次/分钟
```

---

## 五、数据库设计

### 5.1 数据源配置表（`market_data_sources`）

#### 5.1.1 表结构

```javascript
{
  _id: ObjectId,
  source_id: "tushare",  // 数据源标识
  market: "A_STOCK",     // A_STOCK | US_STOCK | HK_STOCK
  enabled: true,         // 是否启用
  priority: 1,           // 优先级（数字越小优先级越高）

  // 数据源配置
  config: {
    api_key: "encrypted_key",  // 加密存储
    api_secret: "encrypted_secret",  // 某些数据源需要
    base_url: "https://api.tushare.pro",
    timeout: 30,  // 超时时间（秒）
    extra_params: {}  // 其他配置参数
  },

  // 限流配置
  rate_limit: {
    max_requests_per_minute: 1000,
    max_requests_per_hour: 10000,
    max_requests_per_day: 100000
  },

  // 支持的数据类型
  supported_data_types: ["quote", "history", "financials", "company"],

  // 元数据
  metadata: {
    created_at: datetime,
    updated_at: datetime,
    last_tested_at: datetime,
    test_status: "success",  // success | failed
    last_error: "error message"
  }
}
```

#### 5.1.2 索引

```javascript
// 查询启用的数据源
db.market_data_sources.createIndex({
  market: 1,
  enabled: 1,
  priority: 1
})

// 唯一索引：同一市场同一source_id只能有一个配置
db.market_data_sources.createIndex({
  market: 1,
  source_id: 1
}, {unique: true})
```

---

### 5.2 股票行情表（`stock_quotes`）

#### 5.2.1 表结构

```javascript
{
  _id: ObjectId,
  symbol: "600000.SH",
  market: "A_STOCK",  // A_STOCK | US_STOCK | HK_STOCK
  data_source: "tushare",  // 数据来源

  // 行情数据
  trade_date: "2025-01-01",
  open: 10.5,
  high: 10.8,
  low: 10.3,
  close: 10.7,
  volume: 1000000,
  amount: 10700000,  // 成交额

  // 技术指标（可选）
  indicators: {
    ma5: 10.6,
    ma10: 10.4,
    ma20: 10.2
  },

  // 元数据
  fetched_at: datetime,  // 获取时间
  data_quality: 85,      // 数据质量评分（0-100）

  // TTL相关
  expires_at: datetime   // 过期时间（根据TTL计算）
}
```

#### 5.2.2 索引

```javascript
// 唯一索引：同一股票 + 同一日期
db.stock_quotes.createIndex({
  symbol: 1,
  trade_date: -1
}, {unique: true})

// 查询索引
db.stock_quotes.createIndex({
  symbol: 1,
  trade_date: -1
})

// 过期数据清理
db.stock_quotes.createIndex({
  expires_at: 1
})
```

---

### 5.3 财务报表表（`stock_financials`）

#### 5.3.1 表结构

```javascript
{
  _id: ObjectId,
  symbol: "600000.SH",
  market: "A_STOCK",
  data_source: "tushare",

  // 报表类型
  report_type: "Q3",  // Q1 | Q2 | Q3 | Q4 | annual
  report_date: "2024-09-30",  // 报告期
  publish_date: "2024-10-30",  // 发布日期

  // 利润表
  income_statement: {
    revenue: 1000000000,
    net_profit: 50000000,
    gross_profit_margin: 0.35,
    net_profit_margin: 0.05
  },

  // 资产负债表
  balance_sheet: {
    total_assets: 5000000000,
    total_liabilities: 3000000000,
    total_equity: 2000000000
  },

  // 现金流量表
  cash_flow: {
    operating_cash_flow: 80000000,
    investing_cash_flow: -50000000,
    financing_cash_flow: -20000000
  },

  // 财务指标
  financial_ratios: {
    roe: 0.15,
    roa: 0.02,
    debt_to_asset_ratio: 0.6,
    current_ratio: 1.5
  },

  // 元数据
  fetched_at: datetime,
  data_quality: 90,
  expires_at: datetime
}
```

---

### 5.4 公司信息表（`stock_companies`）

#### 5.4.1 表结构

```javascript
{
  _id: ObjectId,
  symbol: "600000.SH",
  market: "A_STOCK",
  data_source: "tushare",

  // 基本信息
  company_name: "浦发银行",
  company_name_en: "SPDBank",
  industry: "银行",
  sector: "金融",
  listing_date: "1999-11-10",

  // 联系方式
  contact: {
    website: "www.spdb.com.cn",
    email: "ir@spdb.com.cn",
    phone: "021-68886888",
    address: "上海市浦东新区"
  },

  // 业务描述
  business: {
    main_business: "商业银行业务",
    products: ["公司银行业务", "个人银行业务", "资金业务"],
    description: "..."
  },

  // 股本结构
  capital_structure: {
    total_shares: 29352000000,
    float_shares: 20000000000,
    market_cap: 250000000000
  },

  // 元数据
  fetched_at: datetime,
  expires_at: datetime
}
```

---

## 六、API 端点设计

### 6.1 管理员专用 API

**权限**：仅管理员（ADMIN / SUPER_ADMIN）

#### 6.1.1 数据源配置管理

**1. 列出所有数据源配置**

```
GET /api/admin/market-data/sources

查询参数：
├─ market: A_STOCK | US_STOCK | HK_STOCK（可选）
└─ enabled: true | false（可选）

响应：
{
  "sources": [
    {
      "_id": "config_id_1",
      "source_id": "tushare",
      "market": "A_STOCK",
      "enabled": true,
      "priority": 1,
      "rate_limit": {...},
      "supported_data_types": ["quote", "history"],
      "metadata": {...}
    }
  ]
}
```

**2. 创建数据源配置**

```
POST /api/admin/market-data/sources

请求体：
{
  "source_id": "tushare",
  "market": "A_STOCK",
  "enabled": true,
  "priority": 1,
  "config": {
    "api_key": "user_token_here"
  },
  "rate_limit": {
    "max_requests_per_minute": 1000
  }
}

响应：创建的配置详情
```

**3. 更新数据源配置**

```
PUT /api/admin/market-data/sources/{config_id}

请求体：
{
  "enabled": true,
  "priority": 1,
  "config": {
    "api_key": "new_token_here"
  }
}
```

**4. 删除数据源配置**

```
DELETE /api/admin/market-data/sources/{config_id}
```

**5. 测试数据源连接**

```
POST /api/admin/market-data/sources/{config_id}/test

响应：
{
  "success": true,
  "message": "连接成功",
  "test_time": "2025-01-01T10:00:00Z",
  "response_time_ms": 150
}
```

---

#### 6.1.2 数据管理

**1. 手动触发数据更新**

```
POST /api/admin/market-data/data/refresh

请求体：
{
  "symbol": "600000.SH",
  "market": "A_STOCK",
  "data_types": ["quote", "history"]
}

响应：
{
  "success": true,
  "message": "数据更新任务已提交"
}
```

**2. 查看数据统计**

```
GET /api/admin/market-data/data/stats

响应：
{
  "total_symbols": 5000,
  "total_records": 1500000,
  "data_sources": {
    "tushare": 800000,
    "yahoo": 700000
  },
  "markets": {
    "A_STOCK": 700000,
    "US_STOCK": 600000,
    "HK_STOCK": 200000
  }
}
```

---

### 6.2 用户数据查询 API

**权限**：所有认证用户

#### 6.2.1 获取行情数据

```
GET /api/market-data/quote/{symbol}

查询参数：
├─ market: A_STOCK | US_STOCK | HK_STOCK
└─ date: YYYY-MM-DD（可选，默认最新）

响应：
{
  "symbol": "600000.SH",
  "market": "A_STOCK",
  "trade_date": "2025-01-01",
  "open": 10.5,
  "high": 10.8,
  "low": 10.3,
  "close": 10.7,
  "volume": 1000000,
  "data_source": "tushare",
  "fetched_at": "2025-01-01T10:00:00Z",
  "data_quality": 85
}
```

#### 6.2.2 获取财务报表

```
GET /api/market-data/financials/{symbol}

查询参数：
├─ market: A_STOCK | US_STOCK | HK_STOCK
└─ report_type: Q1 | Q2 | Q3 | Q4 | annual（可选）

响应：财务报表数据
```

---

## 七、与 TradingAgents 集成方案

### 7.1 工具注册方式

**位置**：`backend/modules/market_data/tools/`

**集成方式**：注册到 `trading_agents` 的本地工具

### 7.2 工具列表

#### 7.2.1 A股工具

```
工具名：get_a_stock_quote

功能：获取A股行情数据

参数：
├─ symbol: 股票代码（如 600000.SH）
└─ date: 日期（可选，默认最新）

返回：行情数据字典

数据获取流程：
├─ 1. 检查数据库
│   ├─ 存在且未过期 → 直接返回
│   └─ 不存在或已过期 → 进入步骤2
├─ 2. 获取分布式锁
│   ├─ 成功 → 调用API获取数据
│   └─ 失败 → 等待2秒，再次查数据库
└─ 3. 返回数据
```

#### 7.2.2 美股工具

```
工具名：get_us_stock_quote

功能：获取美股行情数据

参数：
├─ symbol: 股票代码（如 AAPL）
└─ date: 日期（可选，默认最新）

返回：行情数据字典
```

#### 7.2.3 港股工具

```
工具名：get_hk_stock_quote

功能：获取港股行情数据

参数：
├─ symbol: 股票代码（如 0700.HK）
└─ date: 日期（可选，默认最新）

返回：行情数据字典
```

---

## 八、并发与限流策略

### 8.1 分布式锁

**目的**：防止并发请求重复获取数据

**工作流程**：
```
并发场景：100个用户同时请求 AAPL 数据

时间线：
├─ T+0秒：用户1-100同时请求数据
├─ T+0.001秒：用户1获取到分布式锁
├─ T+0.002秒：用户2-100未获取到锁，进入等待
├─ T+0.100秒：用户1调用API获取数据
├─ T+0.500秒：用户1存入数据库，释放锁
├─ T+2.002秒：用户2-100等待结束，从数据库获取数据
└─ 结果：只调用1次API，节省99次
```

**锁配置**：
| 参数 | 值 |
|------|-----|
| 键格式 | `lock:data_fetch:{market}:{symbol}` |
| 超时时间 | 30秒 |
| 等待时间 | 2秒 |

---

### 8.2 限流算法

**算法**：令牌桶（Token Bucket）

**配置**：
```
A股数据源：
├─ Tushare：1000次/分钟
└─ 东方财富：500次/分钟

美股数据源：
└─ Yahoo Finance：1800次/小时

港股数据源：
└─ Yahoo Finance：1800次/小时
```

**工作流程**：
```
请求API前：
├─ 1. 检查令牌桶是否有令牌
│   ├─ 有令牌 → 消耗1个，允许请求
│   └─ 无令牌 → 拒绝请求，等待降级到备用数据源
└─ 2. 定期补充令牌（每秒1个）
```

---

## 九、错误处理与降级

### 9.1 多数据源降级策略

**降级流程**：
```
主数据源失败
    ↓
尝试备用数据源1
    ├─ 成功 → 返回数据
    └─ 失败 → 进入下一步
        ↓
尝试备用数据源2
    ├─ 成功 → 返回数据
    └─ 失败 → 返回错误
```

**降级触发条件**：
- ✅ 网络超时（>30秒）
- ✅ 接口返回错误（HTTP 5xx）
- ✅ 数据解析失败
- ✅ 数据验证失败

**降级日志记录**：
```
日志内容：
├─ 尝试的数据源
├─ 失败原因
├─ 降级到哪个数据源
└─ 最终结果
```

---

### 9.2 错误分类与处理

| 错误类型 | 处理方式 | 是否重试 |
|---------|---------|---------|
| 网络超时 | 降级到备用数据源 | ✅ 是 |
| API限流（429） | 等待后重试 | ✅ 是 |
| 数据验证失败 | 降级到备用数据源 | ❌ 否 |
| 所有数据源失败 | 返回明确错误 | ❌ 否 |

---

## 十、定时任务设计

### 10.1 任务调度

**调度器**：APScheduler（已集成到项目）

### 10.2 定时任务列表

#### 10.2.1 A股数据更新

```
任务1：日K线更新
├─ 时间：每天 15:30（收盘后）
├─ 任务：拉取所有A股的日K线数据
└─ 数据类型：history

任务2：实时行情更新（交易时间）
├─ 时间：交易时间内每5分钟
├─ 任务：拉取热门股票实时行情
└─ 数据类型：quote

任务3：财务报表检查
├─ 时间：每天 16:00
├─ 任务：检查是否有新的财务报表发布
└─ 数据类型：financials
```

#### 10.2.2 美股数据更新

```
任务1：日K线更新
├─ 时间：每天 05:00（收盘后，北京时间）
├─ 任务：拉取所有美股的日K线数据
└─ 数据类型：history

任务2：实时行情更新（交易时间）
├─ 时间：交易时间内每1分钟
├─ 任务：拉取热门股票实时行情
└─ 数据类型：quote

任务3：财务报表检查
├─ 时间：每天 06:00
├─ 任务：检查是否有新的财务报表发布
└─ 数据类型：financials
```

#### 10.2.3 港股数据更新

```
任务1：日K线更新
├─ 时间：每天 16:30（收盘后）
├─ 任务：拉取所有港股的日K线数据
└─ 数据类型：history

任务2：实时行情更新（交易时间）
├─ 时间：交易时间内每5分钟
├─ 任务：拉取热门股票实时行情
└─ 数据类型：quote
```

### 10.3 任务失败处理

```
任务失败处理策略：
├─ 记录失败日志
├─ 发送告警通知（邮件）
├─ 下次定时任务继续尝试
└─ 手动触发更新（管理员）
```

---

## 十一、总结

### 11.1 核心设计原则

1. **管理员统一配置**：所有数据源由管理员配置，用户无需关心
2. **本地化存储**：数据存储在本地数据库，用户请求不直接调用外部API
3. **自动更新**：定时任务自动拉取最新数据
4. **按需更新**：数据过期时自动触发接口更新
5. **多数据源降级**：主数据源失败自动切换备用数据源
6. **并发控制**：分布式锁防止重复获取
7. **数据验证**：确保数据质量

---

### 11.2 关键技术点

- **分布式锁**：防止并发重复获取数据
- **令牌桶限流**：保护API配额
- **数据验证**：确保数据质量
- **多数据源降级**：提高可用性
- **定时任务**：自动更新数据

---

### 11.3 预期收益

| 收益项 | 描述 |
|--------|------|
| **用户体验** | 数据从本地数据库读取，响应快 |
| **系统稳定性** | 多数据源降级，单点故障不影响使用 |
| **成本可控** | 定时任务控制API调用次数 |
| **数据质量** | 数据验证确保准确性 |

---

## 附录

### A. 参考资料

- [Tushare 官方文档](https://tushare.pro)
- [Yahoo Finance API](https://finance.yahoo.com)
- [Alpha Vantage 文档](https://www.alphavantage.co)

### B. 相关文档

- [项目 README.md](../README.md)
- [TradingAgents 模块文档](./TradingAgents智能体系统深度分析.md)

---

**文档结束**
