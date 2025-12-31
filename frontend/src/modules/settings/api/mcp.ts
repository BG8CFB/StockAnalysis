/**
 * MCP 系统配置 API
 */

import { httpGet, httpPut, httpPost } from '@core/api/http'

// =============================================================================
// 类型定义
// =============================================================================

/**
 * MCP 系统配置
 */
export interface MCPSystemSettings {
  // 连接池配置
  pool_personal_max_concurrency: number
  pool_public_per_user_max: number
  pool_personal_queue_size: number
  pool_public_queue_size: number

  // 连接生命周期
  connection_complete_timeout: number
  connection_failed_timeout: number

  // 健康检查
  health_check_enabled: boolean
  health_check_interval: number
  health_check_timeout: number

  // 更新时间（可选）
  updated_at?: string
}

// =============================================================================
// API 函数
// =============================================================================

/**
 * 获取 MCP 系统配置
 * 后端: GET /mcp/settings
 */
export async function getMCPSettings(): Promise<MCPSystemSettings> {
  return httpGet<MCPSystemSettings>('/mcp/settings')
}

/**
 * 更新 MCP 系统配置
 * 后端: PUT /mcp/settings
 */
export async function updateMCPSettings(settings: MCPSystemSettings): Promise<MCPSystemSettings> {
  return httpPut<MCPSystemSettings>('/mcp/settings', settings)
}

/**
 * 恢复 MCP 系统配置为默认值
 * 后端: POST /mcp/settings/reset
 */
export async function resetMCPSettings(): Promise<{ message: string; success: boolean }> {
  return httpPost<{ message: string; success: boolean }>('/mcp/settings/reset')
}
