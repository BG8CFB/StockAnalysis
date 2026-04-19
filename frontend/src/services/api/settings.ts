import apiClient from '../http/client'
import type { ApiResponse } from '@/types/common.types'
import type { User, UserPreferences } from '@/types/auth.types'

// ========== Core Settings ==========

export interface CoreSettings {
  default_market: string
  default_depth: string
  language: string
  timezone: string
}

/** 获取核心设置 */
export async function getCoreSettings(): Promise<ApiResponse<CoreSettings>> {
  return apiClient.get<CoreSettings>('/api/settings/core')
}

/** 更新核心设置 */
export async function updateCoreSettings(data: Partial<CoreSettings>): Promise<ApiResponse<CoreSettings>> {
  return apiClient.put<CoreSettings>('/api/settings/core', data)
}

// ========== Notification Settings ==========

export interface NotificationSettings {
  email_enabled: boolean
  push_enabled: boolean
  task_completed: boolean
  task_failed: boolean
  daily_digest: boolean
  marketing_emails: boolean
}

/** 获取通知设置 */
export async function getNotificationSettings(): Promise<ApiResponse<NotificationSettings>> {
  return apiClient.get<NotificationSettings>('/api/settings/notifications')
}

/** 更新通知设置 */
export async function updateNotificationSettings(data: Partial<NotificationSettings>): Promise<ApiResponse<NotificationSettings>> {
  return apiClient.put<NotificationSettings>('/api/settings/notifications', data)
}

// ========== Quota ==========

export interface QuotaInfo {
  daily_quota: number
  daily_used: number
  monthly_quota: number
  monthly_used: number
  reset_time: string
}

/** 获取配额信息 */
export async function getQuotaInfo(): Promise<ApiResponse<QuotaInfo>> {
  return apiClient.get<QuotaInfo>('/api/settings/quota')
}

// ========== Trading Agents Settings ==========

export interface TradingAgentsSettings {
  default_analysts: string[]
  auto_refresh: boolean
  refresh_interval: number
}

/** 获取 TradingAgents 设置 */
export async function getTradingAgentsSettings(): Promise<ApiResponse<TradingAgentsSettings>> {
  return apiClient.get<TradingAgentsSettings>('/api/settings/trading-agents')
}

// ========== User Profile (re-export from auth for convenience) ==========

/** 获取当前用户信息 */
export async function getUserProfile(): Promise<User> {
  const res = await apiClient.get<User>('/api/users/me')
  return res.data as User
}

/** 更新用户信息 */
export async function updateUserProfile(data: Partial<User>): Promise<User> {
  const res = await apiClient.put<User>('/api/users/me', data)
  return res.data as User
}

/** 获取用户偏好设置 */
export async function getUserPreferences(): Promise<ApiResponse<UserPreferences>> {
  return apiClient.get<UserPreferences>('/api/users/me/preferences')
}

/** 更新用户偏好设置 */
export async function updateUserPreferences(data: Partial<UserPreferences>): Promise<ApiResponse<UserPreferences>> {
  return apiClient.put<UserPreferences>('/api/users/me/preferences', data)
}
