/**
 * 用户配置管理 API
 *
 * 提供用户配置的 CRUD、导入导出等接口调用
 */

import { httpGet, httpPut, httpPost } from '@core/api/http'
import type {
  UserSettingsResponse,
  CoreSettingsUpdate,
  NotificationSettingsUpdate,
  TradingAgentsSettingsUpdate,
  SettingsExport,
  SettingsImport,
} from '../types/user'

// API 基础路径
const BASE_PATH = '/settings'

// =============================================================================
// 核心设置
// =============================================================================

/**
 * 获取用户核心设置
 */
export async function getCoreSettings(): Promise<UserSettingsResponse> {
  return httpGet<UserSettingsResponse>(`${BASE_PATH}/core`)
}

/**
 * 更新用户核心设置
 */
export async function updateCoreSettings(
  data: CoreSettingsUpdate
): Promise<UserSettingsResponse> {
  return httpPut<UserSettingsResponse>(`${BASE_PATH}/core`, data)
}

// =============================================================================
// 配额信息
// =============================================================================

/**
 * 获取用户配额信息
 */
export async function getQuotaInfo() {
  return httpGet<{
    tasks_used: number
    tasks_limit: number
    tasks_remaining: number
    tasks_usage_percent: number
    reports_count: number
    reports_limit: number
    storage_used_mb: number
    storage_limit_mb: number
    storage_usage_percent: number
    concurrent_tasks: number
    concurrent_limit: number
    is_near_quota_limit: boolean
  }>(`${BASE_PATH}/quota`)
}

// =============================================================================
// 配置导入导出
// =============================================================================

/**
 * 导出用户配置
 */
export async function exportSettings(): Promise<SettingsExport> {
  const response = await fetch(`${BASE_PATH}/export`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  })

  if (!response.ok) {
    throw new Error('导出配置失败')
  }

  const data = await response.json()

  // 触发浏览器下载
  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: 'application/json',
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `settings_${new Date().toISOString().slice(0, 10)}.json`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)

  return data
}

/**
 * 导入用户配置
 */
export async function importSettings(
  data: SettingsImport
): Promise<{ success: boolean; message: string; settings: UserSettingsResponse }> {
  return httpPost(`${BASE_PATH}/import`, data)
}
