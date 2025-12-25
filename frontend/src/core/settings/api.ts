/**
 * 系统设置 API 接口
 */
import { httpGet, httpPost, httpPut } from '@core/api/http'
import type { SystemConfig, SystemStatus, SystemInfo } from './types'

export const settingsApi = {
  /**
   * 获取系统状态
   */
  getSystemStatus: () =>
    httpGet<SystemStatus>('/system/status'),

  /**
   * 获取系统配置
   */
  getSystemConfig: () =>
    httpGet<SystemConfig>('/system/config'),

  /**
   * 更新系统配置（仅超级管理员）
   */
  updateSystemConfig: (config: Partial<SystemConfig>) =>
    httpPut<{ success: boolean; message: string; config: SystemConfig }>(
      '/system/config',
      config
    ),

  /**
   * 获取完整系统信息
   */
  getSystemInfo: () =>
    httpGet<SystemInfo>('/system/info'),
}
