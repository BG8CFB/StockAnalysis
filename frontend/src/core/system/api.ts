/**
 * 系统管理模块 API
 * 处理系统初始化、状态检查等
 */
import { httpPost, httpGet } from '@core/api/http'
import type {
  SystemInitializeRequest,
  SystemInitializeResponse,
  SystemStatus,
} from '@core/shared/types'

export const systemApi = {
  /**
   * 系统初始化
   * 后端: POST /system/initialize
   */
  initialize: (data: SystemInitializeRequest) =>
    httpPost<SystemInitializeResponse>('/system/initialize', data),

  /**
   * 获取系统状态
   * 后端: GET /system/status
   */
  getStatus: () =>
    httpGet<SystemStatus>('/system/status'),
}

// 导出类型
export type {
  SystemInitializeRequest,
  SystemInitializeResponse,
  SystemStatus,
}
