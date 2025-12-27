/**
 * 用户管理模块 API（增强版）
 * 支持验证码、限流检查
 */
import { httpPost, httpGet, httpPut, type ApiResponse, type RequestConfig } from '@core/api/http'

// ==================== 类型定义 ====================

export type UserRole = 'GUEST' | 'USER' | 'ADMIN' | 'SUPER_ADMIN'

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

export interface RefreshTokenRequest {
  refresh_token: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface UserInfo {
  id: string
  email: string
  username: string
  role: UserRole
  is_active: boolean
  is_verified: boolean
  created_at: string
  last_login_at: string | null
}

export interface UserPreferences {
  theme: string
  language: string
  timezone: string
  notification_enabled: boolean
  email_alerts: boolean
}

export interface UpdatePreferencesRequest {
  theme?: string
  language?: string
  timezone?: string
  notification_enabled?: boolean
  email_alerts?: boolean
}

// ==================== 验证码相关类型 ====================

export interface CaptchaGenerateResponse {
  token: string
  puzzle_position: { x: number; y: number }
}

export interface CaptchaRequiredResponse {
  required: boolean
  reason?: string
}

// ==================== API 方法 ====================

export const authApi = {
  /**
   * 生成验证码
   */
  generateCaptcha: (action: 'login' | 'register' | 'reset_password' = 'login') =>
    httpPost<CaptchaGenerateResponse>(`/users/captcha/generate?action=${action}`),

  /**
   * 检查是否需要验证码
   */
  checkCaptchaRequired: (email: string) =>
    httpGet<CaptchaRequiredResponse>(`/users/captcha/required?email=${encodeURIComponent(email)}`),

  /**
   * 用户登录
   */
  login: (data: LoginRequest) =>
    httpPost<TokenResponse>('/users/login', data),

  /**
   * 用户注册
   */
  register: (data: RegisterRequest) =>
    httpPost<TokenResponse>('/users/register', data),

  /**
   * 刷新令牌
   */
  refreshToken: (data: RefreshTokenRequest) =>
    httpPost<TokenResponse>('/users/refresh-token', data),

  /**
   * 用户登出
   */
  logout: () =>
    httpPost('/users/logout'),
}

export const userApi = {
  /**
   * 获取当前用户信息
   */
  getMe: (config?: RequestConfig) =>
    httpGet<UserInfo>('/users/me', config),

  /**
   * 获取用户配置
   */
  getPreferences: (config?: RequestConfig) =>
    httpGet<UserPreferences>('/users/me/preferences', config),

  /**
   * 更新用户配置
   */
  updatePreferences: (data: UpdatePreferencesRequest) =>
    httpPut<UserPreferences>('/users/me/preferences', data),
}
