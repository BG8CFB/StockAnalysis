/**
 * 管理员模块 API
 */
import { httpGet, httpPost, httpPut, httpDelete } from '@core/api/http'

// ==================== 类型定义 ====================

export interface UserListResponse {
  id: string
  email: string
  username: string
  role: string
  status: string
  is_active: boolean
  is_verified: boolean
  created_at: string
  last_login: string | null  // 后端使用 serialization_alias="last_login"
  reviewed_by?: string
  reviewed_at?: string
}

export interface GetUsersParams {
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

// ==================== API 方法 ====================

export const adminApi = {
  /**
   * 获取用户列表
   */
  getUsers: (params: GetUsersParams) => {
    const query = new URLSearchParams()
    if (params.skip !== undefined) query.append('skip', params.skip.toString())
    if (params.limit !== undefined) query.append('limit', params.limit.toString())
    if (params.search) query.append('search', params.search)
    if (params.role) query.append('role', params.role)
    if (params.status) query.append('status', params.status)
    if (params.is_active !== undefined) query.append('is_active', params.is_active.toString())

    return httpGet<{ users: UserListResponse[]; total: number }>(`/admin/users?${query}`)
  },

  /**
   * 获取待审核用户列表
   */
  getPendingUsers: (skip: number = 0, limit: number = 20) => {
    const query = new URLSearchParams()
    query.append('skip', skip.toString())
    query.append('limit', limit.toString())
    return httpGet<{ users: UserListResponse[]; total: number }>(`/admin/users/pending?${query}`)
  },

  /**
   * 通过用户审核
   */
  approveUser: (userId: string) =>
    httpPut<{ success: boolean; message: string; user: UserListResponse }>(
      `/admin/users/${userId}/approve`,
      {}
    ),

  /**
   * 拒绝用户审核
   */
  rejectUser: (userId: string, reason: string) =>
    httpPut<{ success: boolean; message: string; user: UserListResponse }>(
      `/admin/users/${userId}/reject`,
      { reason }
    ),

  /**
   * 禁用用户
   */
  disableUser: (userId: string, reason?: string) =>
    httpPut<{ success: boolean; message: string; user: UserListResponse }>(
      `/admin/users/${userId}/disable`,
      reason ? { reason } : {}
    ),

  /**
   * 启用用户
   */
  enableUser: (userId: string) =>
    httpPut<{ success: boolean; message: string; user: UserListResponse }>(
      `/admin/users/${userId}/enable`,
      {}
    ),

  /**
   * 管理员触发密码重置
   */
  adminResetPassword: (userId: string) =>
    httpPost<{ success: boolean; message: string; token?: string }>(
      `/admin/users/${userId}/reset-password`,
      {}
    ),

  /**
   * 获取审计日志
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
   */
  getUser: (id: string) =>
    httpGet<UserListResponse>(`/admin/users/${id}`),

  /**
   * 创建用户
   */
  createUser: (data: CreateUserRequest) =>
    httpPost<UserListResponse>('/admin/users', data),

  /**
   * 更新用户
   */
  updateUser: (id: string, data: UpdateUserRequest) =>
    httpPut<UserListResponse>(`/admin/users/${id}`, data),

  /**
   * 修改用户角色（使用 Query 参数）
   */
  changeUserRole: (id: string, role: string) =>
    httpPut<UserListResponse>(`/admin/users/${id}/role?new_role=${role}`, {}),

  /**
   * 删除用户
   */
  deleteUser: (id: string) =>
    httpDelete(`/admin/users/${id}`),
}
