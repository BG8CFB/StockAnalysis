# TuShare Pro 美股接口文档

> **文档版本**: v1.2
> **创建日期**: 2026-01-03
> **最后更新**: 2026-01-03
> **维护者**: Stock Analysis Team
> **适用市场**: 美股
> **测试状态**: 已于 2026-01-02 完成接口测试（8/9 成功，88.9%）

---

## 📋 目录

- [1. 数据源简介](#1-数据源简介)
- [2. 接入准备](#2-接入准备)
- [3. 调用方式](#3-调用方式)
- [4. 权限体系](#4-权限体系)
- [5. 接口分类与详情](#5-接口分类与详情)
  - [5.1 基础数据接口](#51-基础数据接口)
  - [5.2 行情数据接口](#52-行情数据接口)
  - [5.3 财务数据接口](#53-财务数据接口)
- [6. 数据字段说明](#6-数据字段说明)
- [7. 错误处理与最佳实践](#7-错误处理与最佳实践)
- [8. 参考资料](#8-参考资料)

---

## 1. 数据源简介

### 1.1 TuShare Pro 美股概述

**TuShare Pro** 提供完整的美股市场数据服务。

**美股数据特点**：
- ✅ **数据覆盖**: 覆盖纽交所、纳斯达克
- ✅ **实时行情**: 支持日线行情
- ✅ **财务数据**: 三大报表、财务指标
- ✅ **交易日历**: 美股交易日历
- ✅ **复权支持**: 支持复权数据（通过 pro_bar）

### 1.2 美股数据覆盖范围

| 数据类别 | 覆盖内容 |
|---------|---------|
| **股票数据** | 纽交所(NYSE)、纳斯达克(NASDAQ) |
| **行情数据** | 日线、复权数据 |
| **财务数据** | 三大报表、财务指标 |
| **基础数据** | 股票列表、交易日历 |

### 1.3 数据更新频率

| 数据类型 | 更新频率 | 更新时间 |
|---------|---------|---------|
| **日线行情** | 每交易日 | 交易次日 06:00 左右 |
| **财务数据** | 季度 | 财报披露后更新 |

---

## 2. 接入准备

### 2.1 注册账号

1. 访问 TuShare Pro 官网: https://tushare.pro
2. 点击右上角「注册」按钮
3. 填写用户名、邮箱、密码完成注册

### 2.2 获取 API Token

**获取步骤**：
1. 登录 TuShare Pro
2. 点击右上角「个人主页」
3. 点击左侧菜单「接口TOKEN」
4. 复制您的 Token

### 2.3 安装 Python SDK

```bash
pip install tushare
```

**版本要求**: >= 1.2.10

---

## 3. 调用方式

### 3.1 Python SDK（推荐）

```python
import tushare as ts

# 设置 Token
ts.set_token('your_token_here')

# 初始化 pro 接口
pro = ts.pro_api()

# 调用接口
df = pro.us_basic(
    list_status='L',
    fields='ts_code,symbol,name,market,list_date'
)
```

### 3.2 通用行情接口（支持复权）

> **测试状态**: ✅ 美股复权已测试可用

```python
# 美股前复权日线数据
df = ts.pro_bar(
    ts_code='AAPL.US',  # 苹果公司
    adj='qfq',  # 前复权
    start_date='20230101',
    end_date='20231231'
)

# 美股后复权日线数据
df = ts.pro_bar(
    ts_code='AAPL.US',
    adj='hfq',  # 后复权
    start_date='20230101',
    end_date='20231231'
)
```

---

## 4. 权限体系

### 4.1 美股接口积分要求

| 接口分类 | 最低积分 | 推荐积分 |
|---------|---------|---------|
| 美股基础信息 | 2000 | 5000 |
| 美股日线行情 | 2000 | 5000 |
| 美股交易日历 | 2000 | 5000 |
| 美股财务数据 | 2000 | 5000 |

**重要提示**: 美股接口至少需要 **2000 积分** 才能访问。

---

## 5. 接口分类与详情

### 5.1 基础数据接口

#### 5.1.1 美股基础信息 - us_basic

> **测试状态**: ✅ 已测试可用

**接口描述**: 获取美股基础信息列表

**请求参数**:

| 参数名 | 类型 | 必选 | 说明 |
|-------|------|------|------|
| list_status | str | N | 上市状态：L上市 D退市 P暂停上市 |
| ts_code | str | N | 股票代码 |
| market | str | N | 市场类型：NYSE纳斯达克证券交易所 NASSE纳斯达克 |

**返回字段**:

| 字段名 | 说明 | 示例 |
|-------|------|------|
| ts_code | 股票代码 | AAPL.US |
| symbol | 股票代码（不含后缀） | AAPL |
| name | 股票名称 | Apple Inc |
| fullname | 股票全称 | Apple Inc. |
| market | 市场类型 | NASDAQ |
| exchange | 交易所代码 | NASD |
| curr | 交易货币 | USD |
| list_status | 上市状态 | L上市 |
| list_date | 上市日期 | 19801212 |
| sector | 所属行业 | Technology |
| industry | 所属行业 | Consumer Electronics |

**权限要求**: 2000 积分
**限量**: 单次最大 6000 行数据

**调用示例**:

```python
# 获取所有美股列表
df = pro.us_basic(
    list_status='L',
    fields='ts_code,symbol,name,market,exchange,list_date,sector,industry'
)

# 获取单个美股信息
df = pro.us_basic(ts_code='AAPL.US')
```

#### 5.1.2 美股交易日历 - us_tradecal

> **测试状态**: ✅ 已测试可用（需要修正接口名为 us_tradecal）

**接口描述**: 获取美股交易日历

**请求参数**:

| 参数名 | 类型 | 必选 | 说明 |
|-------|------|------|------|
| exchange | str | N | 交易所：NYSE NASDAQ，默认NYSE |
| start_date | str | N | 开始日期，格式：YYYYMMDD |
| end_date | str | N | 结束日期，格式：YYYYMMDD |
| is_open | str | N | 是否开盘：0休市 1交易 |

**返回字段**:

| 字段名 | 说明 |
|-------|------|
| exchange | 交易所代码 |
| cal_date | 日历日期 |
| is_open | 是否交易（1是 0否） |
| pretrade_date | 上一交易日 |

**权限要求**: 2000 积分
**限量**: 单次最大 6000 条

**调用示例**:

```python
# 获取 2023 年美股交易日历
df = pro.us_trade_cal(
    exchange='NYSE',
    start_date='20230101',
    end_date='20231231',
    is_open='1'
)
```

---

### 5.2 行情数据接口

#### 5.2.1 美股日线行情 - us_daily

> **测试状态**: ✅ 已测试可用

**接口描述**: 获取美股历史行情数据（未复权）

**请求参数**:

| 参数名 | 类型 | 必选 | 说明 |
|-------|------|------|------|
| ts_code | str | N | 股票代码（支持多个，用逗号分隔） |
| trade_date | str | N | 交易日期（YYYYMMDD） |
| start_date | str | N | 开始日期 |
| end_date | str | N | 结束日期 |
| fields | str | N | 指定返回字段 |

**返回字段**:

| 字段名 | 说明 | 数据类型 |
|-------|------|---------|
| ts_code | 股票代码 | str |
| trade_date | 交易日期 | str |
| open | 开盘价 | float |
| high | 最高价 | float |
| low | 最低价 | float |
| close | 收盘价 | float |
| pre_close | 昨收价 | float |
| change | 涨跌额 | float |
| pct_chg | 涨跌幅(%) | float |
| vol | 成交量（手） | float |
| amount | 成交额（千元） | float |

**权限要求**: 2000 积分
**更新时间**: 交易次日 06:00 左右
**限量**: 单次最大 6000 行数据

**调用示例**:

```python
# 获取苹果日线数据
df = pro.us_daily(
    ts_code='AAPL.US',
    start_date='20230101',
    end_date='20231231'
)

# 获取所有美股某一天的数据
df = pro.us_daily(trade_date='20230103')
```

#### 5.2.2 通用行情接口 - pro_bar

> **测试状态**: ✅ 美股复权已测试可用

**接口描述**: 集成开发接口，支持日线、周线、月线，支持复权

**支持市场**: 美股
**复权支持**: 支持前复权/后复权

**请求参数**:

| 参数名 | 类型 | 必选 | 说明 |
|-------|------|------|------|
| ts_code | str | Y | 美股股票代码（如 AAPL.US） |
| start_date | str | N | 开始日期 |
| end_date | str | N | 结束日期 |
| freq | str | N | 数据频率：D日线 W周线 M月线 |
| adj | str | N | 复权类型：None不复权 qfq前复权 hfq后复权 |

**权限要求**: 0 积分

**调用示例**:

```python
# 美股前复权日线数据
df = ts.pro_bar(
    ts_code='AAPL.US',  # 苹果公司
    adj='qfq',
    start_date='20230101',
    end_date='20231231'
)

# 美股周线数据
df = ts.pro_bar(
    ts_code='AAPL.US',
    freq='W',
    adj='qfq'
)

# 美股月线数据
df = ts.pro_bar(
    ts_code='AAPL.US',
    freq='M',
    adj='qfq'
)
```

#### 5.2.3 美股分钟行情 - us_mins

> **测试状态**: ⚠️ 接口不存在或接口名错误，可能暂不支持美股分钟数据

**接口描述**: 获取美股分钟级行情数据

**注意**: 当前版本可能不支持美股分钟数据，建议使用日线数据。

**请求参数**:

| 参数名 | 类型 | 必选 | 说明 |
|-------|------|------|------|
| ts_code | str | Y | 股票代码 |
| trade_date | str | Y | 交易日期 |
| freq | str | N | 数据频率：1min 5min 15min 30min 60min |

**权限要求**: 2000 积分

---

### 5.3 财务数据接口

#### 5.3.1 美股利润表 - us_income

> **测试状态**: ✅ 已测试可用

**接口描述**: 获取美股上市公司利润表数据

**请求参数**:

| 参数名 | 类型 | 必选 | 说明 |
|-------|------|------|------|
| ts_code | str | N | 股票代码 |
| period | str | N | 报告期（如：20221231） |
| report_type | str | N | 报告类型 |

**返回字段**:

| 字段名 | 说明 |
|-------|------|
| ts_code | 股票代码 |
| ann_date | 公告日期 |
| end_date | 报告期 |
| basic_eps | 基本每股收益 |
| total_revenue | 营业总收入 |
| revenue | 营业收入 |
| oper_cost | 营业成本 |
| sell_exp | 销售费用 |
| admin_exp | 管理费用 |
| fin_exp | 财务费用 |
| total_profit | 利润总额 |
| n_income | 净利润 |
| n_income_attr_p | 归属母公司所有者的净利润 |

**权限要求**: 2000 积分
**限量**: 单次最大 5000 条

**调用示例**:

```python
# 获取苹果公司最新利润表
df = pro.us_income(
    ts_code='AAPL.US',
    period='20231231',
    report_type='C'
)
```

#### 5.3.2 美股资产负债表 - us_balancesheet

> **测试状态**: ✅ 已测试可用

**接口描述**: 获取美股上市公司资产负债表数据

**返回字段**:

| 字段名 | 说明 |
|-------|------|
| ts_code | 股票代码 |
| ann_date | 公告日期 |
| end_date | 报告期 |
| total_assets | 资产总计 |
| cur_assets | 流动资产合计 |
| fix_assets | 固定资产合计 |
| total_liab | 负债合计 |
| cur_liab | 流动负债合计 |
| total_hldr_eqy_exc_min_int | 股东权益合计 |
| total_liab_hldr_eqy | 负债和股东权益总计 |

**权限要求**: 2000 积分

#### 5.3.3 美股现金流量表 - us_cashflow

> **测试状态**: ✅ 已测试可用

**接口描述**: 获取美股上市公司现金流量表数据

**返回字段**:

| 字段名 | 说明 |
|-------|------|
| ts_code | 股票代码 |
| ann_date | 公告日期 |
| end_date | 报告期 |
| net_profit | 净利润 |
| c_inf_fr_operate_act | 经营活动产生的现金流量 |
| c_outf_fr_operate_act | 经营活动现金流出小计 |
| n_cash_flows_fnc_oper_act | 经营活动产生的现金流量净额 |
| n_cash_flows_fnc_inv_act | 投资活动产生的现金流量净额 |
| n_cash_flows_fnc_fin_act | 筹资活动产生的现金流量净额 |
| inc_cash_equ | 现金及现金等价物净增加额 |
| c_equ_at_end | 期末现金及现金等价物余额 |

**权限要求**: 2000 积分

#### 5.3.4 美股财务指标 - us_fina_indicator

> **测试状态**: ✅ 已测试可用

**接口描述**: 获取美股上市公司财务指标数据

**请求参数**:

| 参数名 | 类型 | 必选 | 说明 |
|-------|------|------|------|
| ts_code | str | N | 股票代码 |
| period | str | N | 报告期 |

**返回字段**:

| 字段名 | 说明 |
|-------|------|
| ts_code | 股票代码 |
| ann_date | 公告日期 |
| end_date | 报告期 |
| roe | 净资产收益率(%) |
| roa | 总资产净利率(ROA)(%) |
| debt_to_assets | 资产负债率(%) |
| current_ratio | 流动比率 |
| quick_ratio | 速动比率 |
| grossprofit_margin | 销售毛利率(%) |
| netprofit_margin | 销售净利率(%) |

**权限要求**: 2000 积分
**限量**: 单次最大 100 条

**调用示例**:

```python
# 获取苹果公司财务指标
df = pro.us_fina_indicator(
    ts_code='AAPL.US',
    period='20231231'
)
```

---

## 6. 数据字段说明

### 6.1 通用字段约定

**股票代码格式**: `{代码}.{交易所}`
- 美股：如 `AAPL.US`、`TSLA.US`

**日期格式**: `YYYYMMDD`
- 示例：`20230101`、`20231231`

**金额单位**:
- 成交额：千元（日线数据）
- 财务数据：美元

**数量单位**:
- 成交量：手

### 6.2 复权类型

| 类型 | 说明 | 适用场景 |
|------|------|---------|
| None | 不复权 | 查看原始价格 |
| qfq | 前复权 | 技术分析（推荐） |
| hfq | 后复权 | 长期趋势分析 |

**美股复权说明**: 美股通过 `pro_bar` 接口支持复权数据。

---

## 7. 错误处理与最佳实践

### 7.1 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| us_mins 调用失败 | 接口不存在 | 使用日线数据或 `pro_bar` 接口 |
| 接口名错误 | 文档与实际不一致 | 使用 `us_tradecal` 而非 `us_trade_cal` |

### 7.2 最佳实践

1. **推荐使用 `pro_bar` 接口**获取美股日线数据
   - 无调用次数限制
   - 支持复权
   - 支持多种周期（日/周/月）

2. **美股分钟数据**
   - 当前版本可能不支持美股分钟数据
   - 建议使用日线数据

3. **财务数据完整性**
   - 美股三大报表接口均正常可用
   - 财务指标数据完整

---

## 8. 参考资料

### 8.1 官方资源

- **TuShare Pro 官网**: https://tushare.pro
- **官方文档**: https://tushare.pro/document/2

### 8.2 相关文档

- **A股接口文档**: `../A股数据源/tushare接口文档.md`
- **港股接口文档**: `../港股数据源/tushare接口文档.md`

---

**文档结束**
