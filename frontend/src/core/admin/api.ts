/**
 * 管理员模块 API
 * 统一管理所有管理员相关的 API
 */
import { httpGet, httpPost, httpPut, httpDelete } from '@core/api/http'

// ==================== 管理员专用类型 ====================

export interface UserListQuery {
  skip?: number
  limit?: number
  search?: string
  role?: string
  status?: string
  is_active?: boolean
}

export interface CreateUserRequest {
  email: string
  username: string
  password: string
  role: string
}

export interface UpdateUserRequest {
  email?: string
  username?: string
  is_active?: boolean
}

// 用户列表项（后端返回的格式，带有 last_login 而不是 last_login_at）
export interface UserListItemResponse {
  id: string
  email: string
  username: string
  role: string
  status: string
  is_active: boolean
  is_verified: boolean
  created_at: string
  last_login: string | null
  reviewed_by?: string
  reviewed_at?: string
}

// ==================== API 方法 ====================

export const adminApi = {
  /**
   * 获取用户列表
   * 后端: GET /admin/users
   */
  getUsers: (params: UserListQuery) => {
    const query = new URLSearchParams()
    if (params.skip !== undefined) query.append('skip', params.skip.toString())
    if (params.limit !== undefined) query.append('limit', params.limit.toString())
    if (params.search) query.append('search', params.search)
    if (params.role) query.append('role', params.role)
    if (params.status) query.append('status', params.status)
    if (params.is_active !== undefined) query.append('is_active', params.is_active.toString())

    return httpGet<{ users: UserListItemResponse[]; total: number }>(`/admin/users?${query}`)
  },

  /**
   * 获取待审核用户列表
   * 后端: GET /admin/users/pending
   */
  getPendingUsers: (skip: number = 0, limit: number = 20) => {
    const query = new URLSearchParams()
    query.append('skip', skip.toString())
    query.append('limit', limit.toString())
    return httpGet<{ users: UserListItemResponse[]; total: number }>(`/admin/users/pending?${query}`)
  },

  /**
   * 通过用户审核
   * 后端: PUT /admin/users/{user_id}/approve
   */
  approveUser: (userId: string) =>
    httpPut<{ success: boolean; message: string; user: UserListItemResponse }>(
      `/admin/users/${userId}/approve`,
      {}
    ),

  /**
   * 拒绝用户审核
   * 后端: PUT /admin/users/{user_id}/reject
   */
  rejectUser: (userId: string, reason: string) =>
    httpPut<{ success: boolean; message: string; user: UserListItemResponse }>(
      `/admin/users/${userId}/reject`,
      { reason }
    ),

  /**
   * 禁用用户
   * 后端: PUT /admin/users/{user_id}/disable
   */
  disableUser: (userId: string, reason?: string) =>
    httpPut<{ success: boolean; message: string; user: UserListItemResponse }>(
      `/admin/users/${userId}/disable`,
      reason ? { reason } : {}
    ),

  /**
   * 启用用户
   * 后端: PUT /admin/users/{user_id}/enable
   */
  enableUser: (userId: string) =>
    httpPut<{ success: boolean; message: string; user: UserListItemResponse }>(
      `/admin/users/${userId}/enable`,
      {}
    ),

  /**
   * 管理员触发密码重置
   * 后端: POST /admin/users/{user_id}/reset-password
   */
  adminResetPassword: (userId: string) =>
    httpPost<{ success: boolean; message: string; token?: string }>(
      `/admin/users/${userId}/reset-password`,
      {}
    ),

  /**
   * 获取审计日志
   * 后端: GET /admin/audit-logs
   */
  getAuditLogs: (params: { skip?: number; limit?: number; action?: string; user_id?: string }) => {
    const query = new URLSearchParams()
    if (params.skip !== undefined) query.append('skip', params.skip.toString())
    if (params.limit !== undefined) query.append('limit', params.limit.toString())
    if (params.action) query.append('action', params.action)
    if (params.user_id) query.append('user_id', params.user_id)
    return httpGet<{ logs: any[] }>(`/admin/audit-logs?${query}`)
  },

  /**
   * 获取单个用户
   * 后端: GET /admin/users/{user_id}
   */
  getUser: (id: string) =>
    httpGet<UserListItemResponse>(`/admin/users/${id}`),

  /**
   * 创建用户
   * 后端: POST /admin/users
   * 注意：后端直接返回 user.model_dump()，不是包装对象
   */
  createUser: (data: CreateUserRequest) =>
    httpPost<UserListItemResponse>('/admin/users', data),

  /**
   * 更新用户
   * 后端: PUT /admin/users/{user_id}
   * 注意：后端返回包装对象 { success, message, user }
   */
  updateUser: (id: string, data: UpdateUserRequest) =>
    httpPut<{ success: boolean; message: string; user: UserListItemResponse }>(`/admin/users/${id}`, data),

  /**
   * 修改用户角色（使用 Query 参数）
   * 后端: PUT /admin/users/{user_id}/role?new_role={role}
   * 注意：后端返回包装对象 { success, message, user }
   */
  changeUserRole: (id: string, role: string) =>
    httpPut<{ success: boolean; message: string; user: UserListItemResponse }>(`/admin/users/${id}/role?new_role=${role}`, {}),

  /**
   * 删除用户
   * 后端: DELETE /admin/users/{user_id}
   */
  deleteUser: (id: string) =>
    httpDelete(`/admin/users/${id}`),
}

// 导出类型
export type {
  UserListQuery,
  CreateUserRequest,
  UpdateUserRequest,
  UserListItemResponse,
}
