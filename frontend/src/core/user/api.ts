/**
 * 用户核心 API 接口
 */
import { httpGet, httpPost, httpPut, httpDelete } from '@core/api/http'
import type { User, UserListItem, UserListParams, PaginatedResponse } from './types'

// ==================== 类型定义 ====================

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface LoginRequest {
  email: string
  password: string
  captcha_token?: string
  slide_x?: number
  slide_y?: number
}

export interface RegisterRequest {
  email: string
  username: string
  password: string
  confirm_password: string
  captcha_token?: string
  slide_x?: number
  slide_y?: number
}

export interface CaptchaGenerateResponse {
  token: string
  puzzle_position: { x: number; y: number }
}

export interface CaptchaRequiredResponse {
  required: boolean
  reason?: string
}

// ==================== 用户 API ====================

export const userApi = {
  // 生成验证码
  generateCaptcha: (action: 'login' | 'register' | 'reset_password' = 'login') =>
    httpPost<CaptchaGenerateResponse>(`/users/captcha/generate?action=${action}`),

  // 检查是否需要验证码
  checkCaptchaRequired: (email: string) =>
    httpGet<CaptchaRequiredResponse>(`/users/captcha/required?email=${email}`),

  // 注册
  register: (data: RegisterRequest) =>
    httpPost<TokenResponse>('/users/register', data),

  // 登录
  login: (data: LoginRequest) =>
    httpPost<TokenResponse>('/users/login', data),

  // 登出
  logout: () => httpPost('/users/logout'),

  // 刷新令牌
  refreshToken: (refreshToken: string) =>
    httpPost<TokenResponse>('/users/refresh-token', { refresh_token: refreshToken }),

  // 获取当前用户信息
  getCurrentUser: () => httpGet<User>('/users/me'),

  // 更新当前用户信息
  updateCurrentUser: (data: { email?: string; username?: string }) =>
    httpPut<User>('/users/me', data),

  // 获取用户配置
  getPreferences: () => httpGet('/users/me/preferences'),

  // 更新用户配置
  updatePreferences: (data: {
    theme?: string
    language?: string
    timezone?: string
    notification_enabled?: boolean
    email_alerts?: boolean
  }) => httpPut('/users/me/preferences', data),

  // 请求密码重置
  requestPasswordReset: (data: {
    email: string
    captcha_token?: string
    slide_x?: number
    slide_y?: number
  }) => httpPost('/users/request-reset', data),

  // 重置密码
  resetPassword: (data: { token: string; new_password: string; confirm_password: string }) =>
    httpPost('/users/reset-password', data),
}

// ==================== 管理员 API ====================

export const adminApi = {
  // 获取用户列表
  getUsers: (params: UserListParams) => {
    const searchParams = new URLSearchParams()
    if (params.skip !== undefined) searchParams.append('skip', params.skip.toString())
    if (params.limit !== undefined) searchParams.append('limit', params.limit.toString())
    if (params.role) searchParams.append('role', params.role)
    if (params.status) searchParams.append('status', params.status)
    if (params.is_active !== undefined) searchParams.append('is_active', params.is_active.toString())
    if (params.search) searchParams.append('search', params.search)

    const query = searchParams.toString()
    return httpGet<{ users: UserListItem[]; total: number }>(`/admin/users${query ? `?${query}` : ''}`)
  },

  // 获取待审核用户
  getPendingUsers: (skip = 0, limit = 20) =>
    httpGet<{ users: UserListItem[]; total: number }>(`/admin/users/pending?skip=${skip}&limit=${limit}`),

  // 通过用户审核
  approveUser: (userId: string) =>
    httpPut(`/admin/users/${userId}/approve`, {}),

  // 拒绝用户审核
  rejectUser: (userId: string, data: { reason: string }) =>
    httpPut(`/admin/users/${userId}/reject`, data),

  // 禁用用户
  disableUser: (userId: string, data: { reason?: string }) =>
    httpPut(`/admin/users/${userId}/disable`, data),

  // 启用用户
  enableUser: (userId: string) =>
    httpPut(`/admin/users/${userId}/enable`, {}),

  // 更新用户信息
  updateUser: (userId: string, data: {
    email?: string
    username?: string
    role?: string
    is_active?: boolean
  }) => httpPut(`/admin/users/${userId}`, data),

  // 修改用户角色
  changeUserRole: (userId: string, newRole: string) =>
    httpPut(`/admin/users/${userId}/role?new_role=${newRole}`, {}),

  // 删除用户
  deleteUser: (userId: string) =>
    httpDelete(`/admin/users/${userId}`),

  // 管理员触发密码重置
  adminResetPassword: (userId: string) =>
    httpPost(`/admin/users/${userId}/reset-password`, {}),

  // 获取审计日志
  getAuditLogs: (params: {
    skip?: number
    limit?: number
    action?: string
    user_id?: string
  }) => {
    const searchParams = new URLSearchParams()
    if (params.skip !== undefined) searchParams.append('skip', params.skip.toString())
    if (params.limit !== undefined) searchParams.append('limit', params.limit.toString())
    if (params.action) searchParams.append('action', params.action)
    if (params.user_id) searchParams.append('user_id', params.user_id)

    const query = searchParams.toString()
    return httpGet<{ logs: any[] }>(`/admin/audit-logs${query ? `?${query}` : ''}`)
  },
}

// ==================== 系统设置 API ====================

export const settingsApi = {
  // 获取系统配置
  getSystemConfig: () => httpGet<{ success: boolean; data: any }>('/settings/system'),

  // 更新系统配置
  updateSystemConfig: (config: Record<string, any>) =>
    httpPut('/settings/system', config),
}
