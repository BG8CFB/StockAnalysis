# 市场数据模块 - API 接口文档

**版本**：v1.0
**创建日期**：2026-01-14
**状态**：部分实现

---

## 文档修订记录

| 版本 | 日期 | 修订内容 | 修订人 |
|------|------|---------|--------|
| v1.0 | 2026-01-14 | 初始版本，整合所有API接口 | Claude AI |

---

## 目录

- [一、接口概述](#一接口概述)
- [二、数据源状态监控接口](#二数据源状态监控接口)
- [三、用户数据源配置接口](#三用户数据源配置接口)
- [四、请求/响应模型](#四请求响应模型)

---

## 一、接口概述

### 1.1 接口分类

| 接口分类 | 路由前缀 | 功能 | 实现状态 |
|----------|---------|------|---------|
| 数据源状态监控 | `/api/core/system/data-source-status` | 监控数据源健康状态 | ✅ 已实现 |
| 用户数据源配置 | `/api/market-data` | 用户配置付费数据源 | ✅ 已实现 |

### 1.2 通用说明

**Base URL**：
- 开发环境：`http://localhost:8000`
- 生产环境：根据实际部署配置

**认证方式**：
- 所有接口都需要 JWT Token 认证
- 在请求头中添加：`Authorization: Bearer <token>`

**响应格式**：
```json
{
  "code": 200,
  "message": "success",
  "data": { ... }
}
```

---

## 二、数据源状态监控接口

### 2.1 获取仪表板概览

**接口地址**：`GET /api/core/system/data-source-status/overview`

**功能说明**：获取所有市场的数据源健康状态概览

**请求参数**：无

**响应示例**：
```json
{
  "a_stock": {
    "status": "healthy",
    "last_update": "2026-01-14T10:30:00Z",
    "last_update_relative": "2分钟前"
  },
  "us_stock": {
    "status": "healthy",
    "last_update": "2026-01-14T10:25:00Z",
    "last_update_relative": "7分钟前"
  },
  "hk_stock": {
    "status": "degraded",
    "last_update": "2026-01-14T10:28:00Z",
    "last_update_relative": "4分钟前",
    "reason": "部分数据类型降级"
  }
}
```

### 2.2 获取指定市场的详细状态

**接口地址**：`GET /api/core/system/data-source-status/{market}`

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| market | string | 市场类型：`A_STOCK` / `US_STOCK` / `HK_STOCK` |

**响应示例**：
```json
{
  "market": "A_STOCK",
  "market_name": "A股",
  "data_types": [
    {
      "data_type": "daily_quote",
      "data_type_name": "日线行情数据",
      "current_source": {
        "source_type": "system",
        "source_id": "tushare",
        "source_name": "TuShare",
        "status": "healthy",
        "last_check": "2026-01-14T10:30:00Z",
        "last_check_relative": "2分钟前",
        "response_time_ms": 120
      },
      "is_fallback": false,
      "can_retry": false
    },
    {
      "data_type": "financials",
      "data_type_name": "财务报表数据",
      "current_source": {
        "source_type": "system",
        "source_id": "akshare",
        "source_name": "AkShare",
        "status": "degraded",
        "last_check": "2026-01-14T10:25:00Z",
        "last_check_relative": "7分钟前"
      },
      "is_fallback": true,
      "primary_source": {
        "source_id": "tushare",
        "status": "unavailable",
        "can_retry": true
      },
      "fallback_reason": "主数据源 Tushare 连续失败3次"
    }
  ]
}
```

### 2.3 获取指定数据类型的详细信息

**接口地址**：`GET /api/core/system/data-source-status/{market}/{data_type}`

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| market | string | 市场类型 |
| data_type | string | 数据类型：`daily_quote` / `financials` / `company_info` 等 |

**响应示例**：
```json
{
  "market": "A_STOCK",
  "data_type": "daily_quote",
  "data_type_name": "日线行情数据",
  "sources": [
    {
      "source_type": "system",
      "source_id": "tushare",
      "source_name": "TuShare",
      "status": "healthy",
      "priority": 1,
      "last_check": "2026-01-14T10:30:00Z",
      "response_time_ms": 120,
      "avg_response_time_ms": 150,
      "failure_count": 0,
      "api_endpoints": [
        {
          "endpoint_name": "pro_bar",
          "endpoint_name_cn": "前复权日线",
          "status": "healthy",
          "last_check": "2026-01-14T10:30:00Z",
          "failure_count": 0
        },
        {
          "endpoint_name": "adj_factor",
          "endpoint_name_cn": "复权因子",
          "status": "healthy",
          "last_check": "2026-01-14T10:30:00Z",
          "failure_count": 0
        }
      ]
    },
    {
      "source_type": "system",
      "source_id": "akshare",
      "source_name": "AkShare",
      "status": "standby",
      "priority": 2,
      "note": "未启用，主数据源运行正常"
    }
  ],
  "recent_events": [
    {
      "timestamp": "2026-01-14T10:30:00Z",
      "event_type": "status_changed",
      "description": "接口检查通过"
    },
    {
      "timestamp": "2026-01-14T09:25:00Z",
      "event_type": "recovered",
      "description": "从 AkShare 恢复到 Tushare",
      "from_source": "akshare",
      "to_source": "tushare"
    }
  ]
}
```

### 2.4 获取接口错误详情

**接口地址**：`GET /api/core/system/data-source-status/{market}/{data_type}/{source_id}/error`

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| market | string | 市场类型 |
| data_type | string | 数据类型 |
| source_id | string | 数据源ID |

**响应示例（普通用户）**：
```json
{
  "market": "A_STOCK",
  "data_type": "daily_quote",
  "source_id": "tushare",
  "source_name": "TuShare",
  "error": {
    "api_endpoint": "pro_bar",
    "status": "unavailable",
    "error_code": "40200",
    "error_message": "您的积分不足，当前积分 1200，需要 2000",
    "error_type": "APIError",
    "raw_response": {
      "request": "pro_bar",
      "code": 40200,
      "msg": "积分不足",
      "data": null
    },
    "occurred_at": "2026-01-14T10:25:30Z",
    "failure_count": 3,
    "retry_history": [
      {
        "attempt": 1,
        "timestamp": "2026-01-14T10:25:20Z",
        "error": "积分不足"
      },
      {
        "attempt": 2,
        "timestamp": "2026-01-14T10:25:25Z",
        "error": "积分不足"
      },
      {
        "attempt": 3,
        "timestamp": "2026-01-14T10:25:30Z",
        "error": "积分不足"
      }
    ]
  }
}
```

**响应示例（管理员）**：包含额外调试信息
```json
{
  // ... 普通用户所有信息 ...
  "admin_debug_info": {
    "traceback": "Traceback (most recent call last):\n  File ...",
    "request_params": {
      "ts_code": "600000.SH",
      "start_date": "2025-01-01",
      "adj": "qfq"
    },
    "full_error": "..."
  }
}
```

### 2.5 手动重试数据源

**接口地址**：`POST /api/core/system/data-source-status/{market}/{data_type}/{source_id}/retry`

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| market | string | 市场类型 |
| data_type | string | 数据类型 |
| source_id | string | 数据源ID |

**响应示例（成功）**：
```json
{
  "success": true,
  "message": "重试成功",
  "result": {
    "status": "healthy",
    "response_time_ms": 130,
    "recovered_at": "2026-01-14T10:35:00Z",
    "was_fallback": true,
    "previous_source": "akshare"
  }
}
```

**响应示例（失败）**：
```json
{
  "success": false,
  "message": "重试失败",
  "error": {
    "error_code": "40200",
    "error_message": "积分不足",
    "failure_count": 4
  }
}
```

### 2.6 获取历史记录

**接口地址**：`GET /api/core/system/data-source-status/{market}/{data_type}/history`

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| market | string | 市场类型 |
| data_type | string | 数据类型 |

**查询参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| hours | number | 否 | 时间范围（小时），默认24 |

**响应示例**：
```json
{
  "events": [
    {
      "timestamp": "2026-01-14T10:30:00Z",
      "event_type": "status_changed",
      "from_status": "degraded",
      "to_status": "healthy",
      "description": "接口检查通过",
      "source_id": "tushare"
    },
    {
      "timestamp": "2026-01-14T09:25:00Z",
      "event_type": "recovered",
      "description": "从 AkShare 恢复到 Tushare",
      "from_source": "akshare",
      "to_source": "tushare"
    },
    {
      "timestamp": "2026-01-14T09:20:00Z",
      "event_type": "fallback",
      "description": "Tushare 失败，自动降级到 AkShare",
      "reason": "连续失败3次"
    }
  ]
}
```

### 2.7 手动刷新状态

**接口地址**：`POST /api/core/system/data-source-status/refresh`

**请求体**：
```json
{
  "market": "A_STOCK"  // 可选，不指定则刷新所有市场
}
```

**响应示例**：
```json
{
  "success": true,
  "message": "状态已更新",
  "refreshed_at": "2026-01-14T10:35:00Z"
}
```

---

## 三、接口级别监控接口

> **设计说明**：接口级别监控提供更细粒度的监控能力，每个API接口端点（如 `pro_bar`、`adj_factor`）独立监控和健康评估。
>
> 与数据类型级别监控的关系：
> - **数据类型级别**（第二章）：监控整个数据类型的健康状态（如 `daily_quotes`）
> - **接口级别**（本章）：监控具体API接口端点的健康状态（如 `pro_bar`、`adj_factor`）

### 3.1 获取接口健康状态概览

**接口地址**：`GET /api/market-data/monitor/endpoints/overview`

**功能说明**：获取所有接口端点的健康状态概览

**查询参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| market | string | 否 | 市场类型 |
| data_type | string | 否 | 数据类型 |
| status | string | 否 | 状态过滤：healthy / degraded / unavailable |

**响应示例**：
```json
{
  "total_endpoints": 45,
  "healthy": 38,
  "degraded": 5,
  "unavailable": 2,
  "by_market": {
    "A_STOCK": {
      "total": 30,
      "healthy": 25,
      "degraded": 4,
      "unavailable": 1
    },
    "US_STOCK": {
      "total": 10,
      "healthy": 9,
      "degraded": 1,
      "unavailable": 0
    },
    "HK_STOCK": {
      "total": 5,
      "healthy": 4,
      "degraded": 0,
      "unavailable": 1
    }
  },
  "by_source": {
    "tushare": {
      "total": 25,
      "healthy": 20,
      "degraded": 4,
      "unavailable": 1
    },
    "akshare": {
      "total": 12,
      "healthy": 12,
      "degraded": 0,
      "unavailable": 0
    },
    "yahoo": {
      "total": 8,
      "healthy": 6,
      "degraded": 1,
      "unavailable": 1
    }
  }
}
```

### 3.2 获取指定接口的详细状态

**接口地址**：`GET /api/market-data/monitor/endpoints/{market}/{source}/{endpoint}`

**功能说明**：获取指定接口端点的详细健康状态和调用统计

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| market | string | 市场类型：`A_STOCK` / `US_STOCK` / `HK_STOCK` |
| source | string | 数据源ID：`tushare` / `akshare` / `yahoo` 等 |
| endpoint | string | API接口名称：`pro_bar` / `adj_factor` / `income` 等 |

**响应示例**：
```json
{
  "api_endpoint": "pro_bar",
  "api_endpoint_cn": "前复权日线行情",
  "market": "A_STOCK",
  "source_id": "tushare",
  "source_name": "TuShare",
  "data_type": "daily_quotes",
  "data_type_cn": "日线行情",
  "is_required": true,

  "status": "healthy",
  "health_score": 95,
  "last_check_at": "2026-01-14T10:30:00Z",
  "last_check_type": "sync_task",
  "last_check_relative": "2分钟前",

  "response_time": {
    "last_ms": 120,
    "avg_ms": 145,
    "p95_ms": 180,
    "p99_ms": 250
  },

  "failure_info": {
    "failure_count": 0,
    "max_failure_count": 3,
    "last_error": null
  },

  "call_stats": {
    "total_calls": 15234,
    "successful_calls": 15012,
    "failed_calls": 222,
    "success_rate": 0.9854
  },

  "recent_performance": {
    "hourly": [
      { "hour": "2026-01-14T09:00:00Z", "calls": 120, "success_rate": 0.98, "avg_response_ms": 140 },
      { "hour": "2026-01-14T10:00:00Z", "calls": 95, "success_rate": 1.0, "avg_response_ms": 130 }
    ],
    "daily": [
      { "date": "2026-01-13", "calls": 3200, "success_rate": 0.99, "avg_response_ms": 142 },
      { "date": "2026-01-12", "calls": 3150, "success_rate": 0.98, "avg_response_ms": 148 }
    ]
  },

  "can_retry": false,
  "is_fallback": false
}
```

### 3.3 获取指定数据类型的所有接口状态

**接口地址**：`GET /api/market-data/monitor/endpoints/by-data-type/{market}/{data_type}`

**功能说明**：获取指定数据类型下的所有接口端点状态

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| market | string | 市场类型 |
| data_type | string | 数据类型：`daily_quotes` / `financials` / `company_info` 等 |

**响应示例**：
```json
{
  "market": "A_STOCK",
  "market_name": "A股",
  "data_type": "daily_quotes",
  "data_type_cn": "日线行情",
  "aggregated_status": "healthy",

  "endpoints": [
    {
      "api_endpoint": "pro_bar",
      "api_endpoint_cn": "前复权日线",
      "source_id": "tushare",
      "source_name": "TuShare",
      "status": "healthy",
      "health_score": 95,
      "is_required": true,
      "last_check_at": "2026-01-14T10:30:00Z",
      "response_time_ms": 120,
      "failure_count": 0
    },
    {
      "api_endpoint": "adj_factor",
      "api_endpoint_cn": "复权因子",
      "source_id": "tushare",
      "source_name": "TuShare",
      "status": "degraded",
      "health_score": 45,
      "is_required": false,
      "last_check_at": "2026-01-14T10:25:00Z",
      "response_time_ms": 3200,
      "failure_count": 2,
      "last_error": {
        "code": "TIMEOUT",
        "message": "接口响应超时"
      }
    }
  ],

  "summary": {
    "total": 2,
    "healthy": 1,
    "degraded": 1,
    "unavailable": 0
  }
}
```

### 3.4 获取接口调用历史

**接口地址**：`GET /api/market-data/monitor/endpoints/{endpoint}/history`

**功能说明**：获取指定接口端点的调用历史记录

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| endpoint | string | API接口名称 |

**查询参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| market | string | 否 | 市场类型 |
| source | string | 否 | 数据源ID |
| hours | number | 否 | 时间范围（小时），默认24 |
| success_only | boolean | 否 | 是否只返回失败记录，默认false |

**响应示例**：
```json
{
  "api_endpoint": "pro_bar",
  "market": "A_STOCK",
  "source_id": "tushare",
  "time_range": "24小时",
  "total_calls": 1200,
  "successful_calls": 1185,
  "failed_calls": 15,
  "success_rate": 0.9875,

  "recent_calls": [
    {
      "timestamp": "2026-01-14T10:30:00Z",
      "success": true,
      "status_code": "200",
      "response_time_ms": 120,
      "data_count": 3500,
      "call_type": "sync_task"
    },
    {
      "timestamp": "2026-01-14T10:25:00Z",
      "success": false,
      "status_code": "TIMEOUT",
      "response_time_ms": 3100,
      "data_count": 0,
      "call_type": "health_check",
      "error": {
        "code": "TIMEOUT",
        "message": "接口响应超时",
        "detail": {
          "timeout_seconds": 3
        }
      }
    },
    {
      "timestamp": "2026-01-14T10:20:00Z",
      "success": true,
      "status_code": "200",
      "response_time_ms": 135,
      "data_count": 3200,
      "call_type": "tool_call"
    }
  ],

  "statistics": {
    "avg_response_time_ms": 145,
    "p95_response_time_ms": 180,
    "p99_response_time_ms": 250,
    "by_call_type": {
      "sync_task": { "calls": 800, "success_rate": 0.99 },
      "health_check": { "calls": 300, "success_rate": 0.97 },
      "tool_call": { "calls": 100, "success_rate": 1.0 }
    }
  }
}
```

### 3.5 手动重试接口

**接口地址**：`POST /api/market-data/monitor/endpoints/{market}/{source}/{endpoint}/retry`

**功能说明**：手动触发指定接口端点的健康检查

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| market | string | 市场类型 |
| source | string | 数据源ID |
| endpoint | string | API接口名称 |

**响应示例（成功）**：
```json
{
  "success": true,
  "message": "接口检查成功",
  "result": {
    "status": "healthy",
    "health_score": 92,
    "response_time_ms": 125,
    "checked_at": "2026-01-14T10:35:00Z",
    "previous_status": "degraded",
    "was_recovered": true
  }
}
```

**响应示例（失败）**：
```json
{
  "success": false,
  "message": "接口检查失败",
  "error": {
    "error_code": "40200",
    "error_message": "积分不足",
    "failure_count": 4
  }
}
```

### 3.6 获取接口错误统计

**接口地址**：`GET /api/market-data/monitor/endpoints/error-statistics`

**功能说明**：获取接口端点的错误统计信息

**查询参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| market | string | 否 | 市场类型 |
| source | string | 否 | 数据源ID |
| hours | number | 否 | 时间范围（小时），默认24 |

**响应示例**：
```json
{
  "time_range": "24小时",
  "total_errors": 47,

  "by_error_code": [
    {
      "error_code": "TIMEOUT",
      "error_message": "接口响应超时",
      "count": 18,
      "percentage": 38.3,
      "affected_endpoints": ["adj_factor", "income"]
    },
    {
      "error_code": "40200",
      "error_message": "积分不足",
      "count": 12,
      "percentage": 25.5,
      "affected_endpoints": ["income", "balancesheet"]
    },
    {
      "error_code": "CONNECTION_ERROR",
      "error_message": "连接失败",
      "count": 8,
      "percentage": 17.0,
      "affected_endpoints": "stock_basic"
    }
  ],

  "by_endpoint": [
    {
      "api_endpoint": "adj_factor",
      "api_endpoint_cn": "复权因子",
      "market": "A_STOCK",
      "source_id": "tushare",
      "error_count": 18,
      "most_common_error": "TIMEOUT"
    },
    {
      "api_endpoint": "income",
      "api_endpoint_cn": "利润表",
      "market": "A_STOCK",
      "source_id": "tushare",
      "error_count": 15,
      "most_common_error": "40200"
    }
  ],

  "trend": {
    "current_hour": 5,
    "previous_hour": 3,
    "trend_direction": "up"
  }
}
```

### 3.7 批量健康检查

**接口地址**：`POST /api/market-data/monitor/endpoints/batch-check`

**功能说明**：批量触发多个接口端点的健康检查

**请求体**：
```json
{
  "endpoints": [
    {
      "market": "A_STOCK",
      "source_id": "tushare",
      "api_endpoint": "pro_bar"
    },
    {
      "market": "A_STOCK",
      "source_id": "tushare",
      "api_endpoint": "adj_factor"
    }
  ]
}
```

**响应示例**：
```json
{
  "success": true,
  "total": 2,
  "checked": 2,
  "results": [
    {
      "market": "A_STOCK",
      "source_id": "tushare",
      "api_endpoint": "pro_bar",
      "status": "healthy",
      "health_score": 95,
      "response_time_ms": 120,
      "checked_at": "2026-01-14T10:35:00Z"
    },
    {
      "market": "A_STOCK",
      "source_id": "tushare",
      "api_endpoint": "adj_factor",
      "status": "degraded",
      "health_score": 45,
      "response_time_ms": 3100,
      "checked_at": "2026-01-14T10:35:00Z",
      "error": {
        "code": "TIMEOUT",
        "message": "接口响应超时"
      }
    }
  ]
}
```

---

## 四、用户数据源配置接口

### 4.1 获取系统数据源配置列表

**接口地址**：`GET /api/market-data/sources/configs`

**查询参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| market | string | 否 | 市场类型 |
| enabled_only | boolean | 否 | 是否只返回启用的配置，默认 true |

**响应示例**：
```json
[
  {
    "_id": "676f4a3b1234567890abcdef",
    "source_id": "tushare",
    "market": "A_STOCK",
    "enabled": true,
    "priority": 1,
    "is_system_public": true,
    "supported_data_types": ["daily_quote", "financials", "company_info"]
  },
  {
    "_id": "676f4a3b1234567890abcdeg",
    "source_id": "akshare",
    "market": "A_STOCK",
    "enabled": true,
    "priority": 2,
    "is_system_public": true,
    "supported_data_types": ["daily_quote", "company_info"]
  }
]
```

### 4.2 获取单个系统数据源配置

**接口地址**：`GET /api/market-data/sources/config/{source_id}`

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| source_id | string | 数据源ID |

**查询参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| market | string | 否 | 市场类型，默认 `A_STOCK` |

**响应示例**：
```json
{
  "_id": "676f4a3b1234567890abcdef",
  "source_id": "tushare",
  "market": "A_STOCK",
  "enabled": true,
  "priority": 1,
  "is_system_public": true,
  "config": {
    "api_key": "encrypted_token_here",
    "base_url": "https://api.tushare.pro",
    "timeout": 30
  },
  "rate_limit": {
    "max_requests_per_minute": 1000,
    "max_requests_per_hour": 10000,
    "max_requests_per_day": 100000
  },
  "supported_data_types": ["daily_quote", "financials", "company_info"],
  "metadata": {
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
    "last_tested_at": "2026-01-14T10:00:00Z",
    "test_status": "success"
  }
}
```

### 4.3 获取用户数据源配置列表

**接口地址**：`GET /api/market-data/user-sources/configs`

**查询参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| market | string | 否 | 市场类型 |
| enabled_only | boolean | 否 | 是否只返回启用的配置，默认 true |

**响应示例**：
```json
[
  {
    "_id": "676f4a3b1234567890user01",
    "user_id": "676f4a3b1234567890user00",
    "source_id": "tushare_pro",
    "market": "A_STOCK",
    "enabled": true,
    "priority": 1,
    "created_at": "2026-01-05T08:00:00Z",
    "updated_at": "2026-01-05T08:00:00Z",
    "test_status": {
      "last_test_time": "2026-01-14T10:00:00Z",
      "status": "success"
    }
  }
]
```

### 4.4 获取用户单个数据源配置

**接口地址**：`GET /api/market-data/user-sources/config/{source_id}`

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| source_id | string | 数据源ID |

**查询参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| market | string | 否 | 市场类型，默认 `A_STOCK` |

**响应示例**：
```json
{
  "_id": "676f4a3b1234567890user01",
  "user_id": "676f4a3b1234567890user00",
  "source_id": "tushare_pro",
  "market": "A_STOCK",
  "enabled": true,
  "priority": 1,
  "config": {
    "api_key": "******"  // API Key 已脱敏
  },
  "created_at": "2026-01-05T08:00:00Z",
  "updated_at": "2026-01-05T08:00:00Z",
  "test_status": {
    "last_test_time": "2026-01-14T10:00:00Z",
    "status": "success"
  }
}
```

### 4.5 创建用户数据源配置

**接口地址**：`POST /api/market-data/user-sources/config`

**请求体**：
```json
{
  "source_id": "tushare_pro",
  "market": "A_STOCK",
  "api_key": "your_api_token_here",
  "enabled": true,
  "priority": 1
}
```

**请求参数说明**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| source_id | string | ✅ | 数据源ID |
| market | string | ✅ | 市场类型：`A_STOCK` / `US_STOCK` / `HK_STOCK` |
| api_key | string | ✅ | API 密钥 |
| enabled | boolean | ❌ | 是否启用，默认 true |
| priority | number | ❌ | 优先级，默认 1 |

**允许配置的数据源**：
```python
# 当前后端支持的用户配置数据源
allowed_sources = {
    "A_STOCK": ["tushare_pro"],     # TuShare Pro 付费
    "US_STOCK": ["alpha_vantage"],  # Alpha Vantage
    "HK_STOCK": []                  # 暂不支持
}
```

**响应示例**：
```json
{
  "message": "数据源配置创建成功",
  "doc_id": "676f4a3b1234567890user01"
}
```

**错误响应示例**：
```json
{
  "detail": "不允许配置该数据源: hk_paid_source。允许的数据源: []"
}
```

### 4.6 更新用户数据源配置

**接口地址**：`PUT /api/market-data/user-sources/config/{source_id}`

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| source_id | string | 数据源ID |

**查询参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| market | string | ✅ | 市场类型 |

**请求体**：
```json
{
  "api_key": "new_api_token_here",
  "enabled": false,
  "priority": 2
}
```

**请求参数说明**：所有参数都是可选的

**响应示例**：
```json
{
  "message": "数据源配置更新成功",
  "doc_id": "676f4a3b1234567890user01"
}
```

### 4.7 删除用户数据源配置

**接口地址**：`DELETE /api/market-data/user-sources/config/{source_id}`

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| source_id | string | 数据源ID |

**查询参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| market | string | ✅ | 市场类型 |

**响应示例**：
```json
{
  "message": "数据源配置删除成功"
}
```

### 4.8 测试用户数据源连接

**接口地址**：`POST /api/market-data/user-sources/config/{source_id}/test`

**路径参数**：
| 参数 | 类型 | 说明 |
|------|------|------|
| source_id | string | 数据源ID |

**查询参数**：
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| market | string | ✅ | 市场类型 |

**响应示例（成功）**：
```json
{
  "success": true,
  "test_time": "2026-01-14T10:35:00Z"
}
```

**响应示例（失败）**：
```json
{
  "success": false,
  "error": "连接测试失败：API Token 无效",
  "test_time": "2026-01-14T10:35:00Z"
}
```

---

## 五、请求/响应模型

### 5.1 市场类型

```typescript
enum MarketType {
  A_STOCK = 'A_STOCK',    // A股
  US_STOCK = 'US_STOCK',  // 美股
  HK_STOCK = 'HK_STOCK'   // 港股
}
```

### 5.2 数据源状态

```typescript
enum DataSourceStatus {
  HEALTHY = 'healthy',        // 正常
  DEGRADED = 'degraded',      // 已降级
  UNAVAILABLE = 'unavailable', // 不可用
  STANDBY = 'standby'         // 待机
}
```

### 5.3 数据源类型

```typescript
enum DataSourceType {
  SYSTEM = 'system',  // 系统公共数据源
  USER = 'user'       // 用户个人数据源
}
```

### 4.4 数据类型列表

| 英文标识 | 中文名称 |
|---------|---------|
| `daily_quote` | 日线行情数据 |
| `realtime_quote` | 实时行情数据 |
| `minute_quote` | 分钟行情数据 |
| `financials` | 财务报表数据 |
| `financial_indicator` | 财务指标数据 |
| `company_info` | 公司信息数据 |
| `news` | 新闻资讯数据 |
| `calendar` | 交易日历数据 |
| `top_list` | 龙虎榜数据 |
| `moneyflow` | 资金流向数据 |
| `dividend` | 分红送股数据 |
| `shareholder_num` | 股东人数数据 |
| `top_shareholder` | 十大股东数据 |
| `margin` | 融资融券数据 |
| `macro_economy` | 宏观经济数据 |
| `sector` | 板块数据 |
| `index` | 指数数据 |
| `ipo` | IPO新股数据 |
| `pledge` | 股权质押数据 |
| `repurchase` | 股票回购数据 |
| `adj_factor` | 复权因子数据 |

---

## 六、错误代码

| 错误代码 | 说明 |
|---------|------|
| 400 | 请求参数错误 |
| 401 | 未授权（Token 无效或过期） |
| 403 | 禁止访问（权限不足） |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

---

**文档结束**
