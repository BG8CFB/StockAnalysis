/**
 * 系统管理模块 API
 */
import { httpPost, httpGet, type ApiResponse } from '@core/api/http'

// ==================== 类型定义 ====================

export interface SystemInitializeRequest {
  email: string
  username: string
  password: string
  confirm_password: string
}

export interface SystemInitializeResponse {
  success: boolean
  message: string
  user: {
    id: string
    email: string
    username: string
    role: string
  }
  access_token: string
  refresh_token: string
  token_type: string
}

export interface SystemStatusResponse {
  initialized: boolean
  has_admin: boolean
  version: string
  status: string
  debug?: boolean
  captcha_enabled?: boolean
}

// ==================== API 方法 ====================

export const systemApi = {
  /**
   * 系统初始化
   */
  initialize: (data: SystemInitializeRequest) =>
    httpPost<SystemInitializeResponse>('/system/initialize', data),

  /**
   * 获取系统状态
   */
  getStatus: () =>
    httpGet<SystemStatusResponse>('/system/status'),
}
