# API 文档示例

---

## 获取用户列表

### 接口信息

| 属性 | 值 |
|------|-----|
| **端点** | `GET /api/v1/users` |
| **描述** | 获取用户列表，支持分页查询 |
| **认证方式** | Bearer Token (JWT) |

### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `page` | integer | 否 | 1 | 页码，从 1 开始 |
| `limit` | integer | 否 | 10 | 每页返回数量，最大 100 |

### 请求示例

```bash
# 使用 curl
curl -X GET "http://localhost:8000/api/v1/users?page=1&limit=10" \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."

# 使用 JavaScript (fetch)
fetch('http://localhost:8000/api/v1/users?page=1&limit=10', {
  headers: {
    'Authorization': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGc...'
  }
})
```

### 响应示例

**成功响应 (200)**：

```json
{
  "success": true,
  "data": {
    "total": 100,
    "page": 1,
    "limit": 10,
    "users": [
      {
        "id": "user_id_1",
        "username": "johndoe",
        "email": "john@example.com",
        "role": "USER",
        "status": "ACTIVE",
        "created_at": "2024-01-01T00:00:00Z"
      },
      {
        "id": "user_id_2",
        "username": "janedoe",
        "email": "jane@example.com",
        "role": "ADMIN",
        "status": "ACTIVE",
        "created_at": "2024-01-02T00:00:00Z"
      }
    ]
  }
}
```

**错误响应 (401)** - 未认证：

```json
{
  "success": false,
  "error": "Unauthorized",
  "message": "未提供有效的认证令牌"
}
```

**错误响应 (400)** - 参数错误：

```json
{
  "success": false,
  "error": "ValidationError",
  "message": "参数验证失败",
  "details": {
    "limit": "limit 不能超过 100"
  }
}
```

### 响应字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | boolean | 请求是否成功 |
| `data` | object | 响应数据 |
| `data.total` | integer | 总用户数量 |
| `data.page` | integer | 当前页码 |
| `data.limit` | integer | 每页数量 |
| `data.users` | array | 用户列表 |
| `users[].id` | string | 用户 ID |
| `users[].username` | string | 用户名 |
| `users[].email` | string | 邮箱地址 |
| `users[].role` | string | 用户角色（USER/ADMIN/SUPER_ADMIN） |
| `users[].status` | string | 用户状态（ACTIVE/INACTIVE） |
| `users[].created_at` | string | 创建时间（ISO 8601） |

### HTTP 状态码

| 状态码 | 描述 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 500 | 服务器内部错误 |

---

**最后更新**: 2026-01-17
