/**
 * 系统设置 API 接口
 * 统一管理所有系统设置相关的 API
 */
import { httpGet, httpPut } from '@core/api/http'
import type { SystemConfig, SystemInfo } from './types'

export const settingsApi = {
  /**
 * 获取系统状态
 * 后端: GET /system/status
 */
getSystemStatus: () =>
  httpGet<SystemStatus>('/system/status'),

/**
 * 获取系统配置
 * 后端: GET /settings/system
 */
getSystemConfig: () =>
  httpGet<SystemConfig>('/settings/system'),

  /**
   * 更新系统配置（仅超级管理员）
   * 后端: PUT /settings/system
   */
  updateSystemConfig: (config: Partial<SystemConfig>) =>
    httpPut<{ success: boolean; message: string; config: SystemConfig }>(
      '/settings/system',
      config
    ),

  /**
   * 获取完整系统信息
   * 后端: GET /system/info
   */
  getSystemInfo: () =>
    httpGet<SystemInfo>('/system/info'),
}
