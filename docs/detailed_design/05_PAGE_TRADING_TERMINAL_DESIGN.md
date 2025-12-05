# 05_PAGE_TRADING_TERMINAL_DESIGN.md

# 前端页面设计：交易终端 (Trading Terminal)

## 1. 概述

交易终端是系统中最具交互性的模块，基于后端的 **模拟交易引擎 (`app/routers/paper.py`)** 构建。它不仅提供基础的下单功能，还完整实现了 **多币种资金管理** 和 **多市场交易规则仿真**（如 A股的 T+1 和印花税逻辑）。

**核心类与服务**：
*   **API入口**: `app.routers.paper` (目前逻辑直接写在 Router 中，建议迁移到 Service)
*   **数据库**: `paper_accounts`, `paper_positions`, `paper_orders`

---

## 2. 页面功能模块详解

### 2.1 交易控制台 (Trading Console)
*   **多币种账户概览**：
    *   展示三个独立资金池：`CNY` (人民币), `HKD` (港币), `USD` (美元)。
    *   显示 **总资产**（折合人民币）和 **当日盈亏**。
    *   *数据源*：`GET /api/paper/account` 返回的 `cash` 和 `realized_pnl` 字段。
*   **下单面板 (Order Entry)**：
    *   **智能代码识别**：输入 `700` 自动识别为 `00700.HK` (港股)，输入 `AAPL` 识别为 `US` (美股)。
    *   **交易方向**：买入 / 卖出。
    *   **最大可买/可卖计算**：
        *   *买入*：`Available Cash / (Price * (1+CommissionRate))`。
        *   *卖出*：`Available Position` (需考虑 A股 T+1 冻结)。
    *   **订单类型**：
        *   `LIMIT`: 限价单（需输入指定价格）。
        *   `MARKET`: 市价单（以当前最新价立即成交）。

### 2.2 持仓与订单管理 (Positions & Orders)
*   **持仓列表**：
    *   字段：代码、名称、持有数量、可用数量、成本价、现价、浮动盈亏。
    *   *逻辑*：对于 A股，今日买入的股票 `Available Quantity` 为 0，次日自动解冻。
*   **当日委托 / 历史成交**：
    *   支持撤单 (`Cancel`) 操作（仅限未完全成交的限价单）。

---

## 3. 核心逻辑设计 (Backend Logic)

本模块基于 `app/routers/paper.py` 中的实现逻辑。

### 3.1 多币种账户体系 (Multi-Currency Account)
系统不进行自动汇率转换，而是维护独立的货币账本：
```python
INITIAL_CASH = {
    "CNY": 1_000_000.0,   # A股初始资金
    "HKD": 1_000_000.0,   # 港股初始资金
    "USD": 100_000.0      # 美股初始资金
}
```
*   **交易隔离**：买入 `AAPL` 只能使用 `USD` 余额；买入 `600519` 只能使用 `CNY`。

### 3.2 交易规则仿真 (Simulation Rules)

#### A. 可用持仓计算 (T+1 vs T+0)
后端 `_get_available_quantity` 函数实现了市场差异化逻辑：
*   **A股 (CN)**: 实施 **T+1** 制度。今日买入 (`timestamp >= today 00:00`) 的数量从总持仓中扣除，不可卖出。
*   **港美股 (HK/US)**: 实施 **T+0** 制度。买入后立即增加 `Available Quantity`，支持日内回转交易。

#### B. 费用计算 (Commission & Tax)
后端 `_calculate_commission` 实现了精细的费用模型：
*   **通用费用**：佣金 (Rate: 0.025%, Min: 5元)。
*   **A股特有**：印花税 (Stamp Duty, 0.1%)，仅卖出时收取。
*   **港股特有**：交易征费 (Transaction Levy)、交易费 (Trading Fee)、结算费 (Settlement Fee)。
*   **美股特有**：SEC 费用 (仅卖出)。

#### C. 撮合逻辑 (Matching Engine)
由于不连接真实交易所，系统采用“即时撮合”策略：
1.  **获取实时价**：调用 `_get_last_price` (支持 A/HK/US)。
2.  **市价单**：立即按 `Last Price` 成交。
3.  **限价单**：
    *   买单：若 `Last Price <= Limit Price`，立即成交。
    *   卖单：若 `Last Price >= Limit Price`，立即成交。
    *   *注*：当前版本主要支持即时成交，未实现挂单队列的盘口撮合。

---

## 4. 📂 代码导航 (Code Navigation)

*   **API 实现 (Router)**:
    *   `app/routers/paper.py`: **核心文件**。目前大部分交易逻辑（下单、撤单、查询）都写在这里。

*   **辅助逻辑**:
    *   `_calculate_commission`: 计算手续费。
    *   `_get_available_quantity`: 计算 T+1 可卖持仓。
    *   `_detect_market_and_code`: 识别股票市场。

---

## 5. 🚀 初级开发指南 (Developer Guide)

**任务：我想支持“止损单 (Stop Loss Order)”，该怎么做？**

1.  **Step 1: 修改数据模型**
    *   在 `paper.py` 中的 `PlaceOrderRequest` 类，增加 `trigger_price: float` 字段。
    *   在 `type` 字段的枚举中增加 `STOP` 类型。

2.  **Step 2: 修改下单逻辑**
    *   在 `place_order` 接口中，如果 `type == STOP`，不立即进行撮合。
    *   直接存入 `paper_orders` 表，状态设为 `PENDING_TRIGGER`。

3.  **Step 3: 实现触发器**
    *   你需要一个后台任务（Worker），每秒扫描所有 `PENDING_TRIGGER` 的订单。
    *   检查当前价格是否触及 `trigger_price`。
    *   如果触及，将订单状态改为 `SUBMITTED`，并转为市价单进行撮合。

**任务：我想调整 A 股的初始资金**

1.  找到 `app/routers/paper.py`。
2.  修改 `INITIAL_CASH_BY_MARKET` 字典中的 `CNY` 值即可。

---

## 6. 接口设计 (API Specification)

### 6.1 下单接口
*   **URL**: `/api/paper/order`
*   **Method**: `POST`
*   **Request Body**:
    ```json
    {
      "code": "00700.HK",
      "side": "buy",
      "quantity": 100,
      "type": "limit",
      "price": 320.5
    }
    ```

### 6.2 撤单接口
*   **URL**: `/api/paper/order/{order_id}/cancel`
*   **Method**: `POST`

### 6.3 账户信息查询
*   **URL**: `/api/paper/account`
*   **Method**: `GET`
*   **Response**:
    ```json
    {
      "cash": { "CNY": 95000.0, "HKD": 1000000.0, "USD": 100000.0 },
      "positions": [ ... ],
      "total_assets_cny": 150000.0
    }
    ```

---

## 7. 数据存储设计 (Database Schema)

### 7.1 模拟账户表 (`paper_accounts`)
```javascript
{
  "_id": ObjectId("..."),
  "user_id": ObjectId("..."),
  "cash": {
    "CNY": 100000.0,
    "HKD": 1000000.0,
    "USD": 10000.0
  },
  "realized_pnl": { "CNY": 0, "HKD": 0, "USD": 0 },
  "created_at": ISODate("...")
}
```

### 7.2 持仓表 (`paper_positions`)
```javascript
{
  "_id": ObjectId("..."),
  "user_id": ObjectId("..."),
  "code": "00700",
  "market": "HK",
  "quantity": 500,
  "average_cost": 310.5,
  "updated_at": ISODate("...")
}
```

### 7.3 订单表 (`paper_orders`)
```javascript
{
  "_id": ObjectId("..."),
  "order_id": "uuid-...",
  "user_id": ObjectId("..."),
  "code": "00700",
  "side": "buy",   // buy, sell
  "type": "limit", // limit, market
  "price": 308.0,  // 委托价
  "quantity": 500,
  "filled_qty": 0,
  "status": "SUBMITTED", // SUBMITTED, FILLED, CANCELED, REJECTED
  "created_at": ISODate("...")
}
```
