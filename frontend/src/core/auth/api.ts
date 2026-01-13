/**
 * 认证模块 API
 * 统一管理所有认证相关的 API（登录、注册、用户信息等）
 */
import { httpPost, httpGet, httpPut, type RequestConfig } from '@core/api/http'
import type {
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  RefreshTokenRequest,
  User,
  UserInfo,
  UserPreferences,
  UpdatePreferencesRequest,
} from '@core/shared/types'

// ==================== 认证 API ====================

export const authApi = {
  /**
   * 用户登录
   * 后端: POST /users/login
   */
  login: (data: LoginRequest) =>
    httpPost<TokenResponse>('/users/login', data),

  /**
   * 用户注册
   * 后端: POST /users/register
   * 注意：返回 User 而不是 TokenResponse，因为注册后可能需要审核才能登录
   */
  register: (data: RegisterRequest) =>
    httpPost<User>('/users/register', data),

  /**
   * 刷新访问令牌
   * 后端: POST /users/refresh-token
   */
  refreshToken: (data: RefreshTokenRequest) =>
    httpPost<TokenResponse>('/users/refresh-token', data),

  /**
   * 用户登出
   * 后端: POST /users/logout
   */
  logout: () =>
    httpPost('/users/logout'),
}

// ==================== 用户 API ====================

export const userApi = {
  /**
   * 获取当前用户信息
   * 后端: GET /users/me
   */
  getMe: (config?: RequestConfig) =>
    httpGet<UserInfo>('/users/me', config),

  /**
   * 更新当前用户信息
   * 后端: PUT /users/me
   */
  updateMe: (data: { email?: string; username?: string }) =>
    httpPut<UserInfo>('/users/me', data),

  /**
   * 获取用户配置
   * 后端: GET /users/me/preferences
   */
  getPreferences: (config?: RequestConfig) =>
    httpGet<UserPreferences>('/users/me/preferences', config),

  /**
   * 更新用户配置
   * 后端: PUT /users/me/preferences
   */
  updatePreferences: (data: UpdatePreferencesRequest) =>
    httpPut<UserPreferences>('/users/me/preferences', data),

  /**
   * 请求密码重置
   * 后端: POST /users/request-reset
   */
  requestPasswordReset: (data: {
    email: string
    captcha_token?: string
    slide_x?: number
    slide_y?: number
  }) => httpPost('/users/request-reset', data),

  /**
   * 重置密码
   * 后端: POST /users/reset-password
   */
  resetPassword: (data: { token: string; new_password: string; confirm_password: string }) =>
    httpPost('/users/reset-password', data),
}

// ==================== 导出类型 ====================

export type {
  LoginRequest,
  RegisterRequest,
  TokenResponse,
  RefreshTokenRequest,
  User,
  UserInfo,
  UserPreferences,
  UpdatePreferencesRequest,
}
