/**
 * MCP 服务管理 API
 * 对应后端 core/mcp/api/routes.py（前缀 /api/mcp）
 *
 * 后端直接返回数据（无 ApiResponse 包装），前端 apiClient 返回 axios response.data。
 * 因此各函数返回 Promise<T>，T 为后端实际响应类型。
 */

import apiClient from '../http/client'

// =============================================================================
// 类型定义
// =============================================================================

/** MCP 传输模式 */
export type TransportMode = 'stdio' | 'sse' | 'http' | 'streamable_http' | 'websocket'

/** 认证类型 */
export type AuthType = 'none' | 'bearer' | 'basic'

/** MCP 服务器状态 */
export type MCPServerStatus = 'available' | 'unavailable' | 'unknown'

/** MCP 服务器配置（完整响应） */
export interface MCPServer {
  id: string
  name: string
  transport: TransportMode
  command?: string | null
  args?: string[] | null
  env?: Record<string, string> | null
  url?: string | null
  headers?: Record<string, string> | null
  auth_type: AuthType
  auth_token?: string | null
  auto_approve: string[]
  enabled: boolean
  is_system: boolean
  owner_id?: string | null
  status: MCPServerStatus
  last_check_at?: string | null
  created_at: string
  updated_at: string
}

/** 创建 MCP 服务器请求 */
export interface MCPServerCreateRequest {
  name: string
  transport: TransportMode
  command?: string | null
  args?: string[]
  env?: Record<string, string>
  url?: string | null
  headers?: Record<string, string>
  auth_type?: AuthType
  auth_token?: string | null
  auto_approve?: string[]
  enabled?: boolean
  is_system?: boolean
}

/** 更新 MCP 服务器请求（所有字段可选） */
export interface MCPServerUpdateRequest {
  name?: string
  transport?: TransportMode
  command?: string | null
  args?: string[] | null
  env?: Record<string, string> | null
  url?: string | null
  headers?: Record<string, string> | null
  auth_type?: AuthType
  auth_token?: string | null
  auto_approve?: string[] | null
  enabled?: boolean | null
}

/** 连接测试响应 */
export interface ConnectionTestResponse {
  success: boolean
  message: string
  latency_ms?: number | null
  details?: Record<string, unknown> | null
}

/** MCP 工具信息 */
export interface MCPToolInfo {
  name: string
  description: string
  server_id: string
  server_name: string
}

/** MCP 服务器列表响应 */
export interface MCPServerListResponse {
  system: MCPServer[]
  user: MCPServer[]
}

/** MCP 工具列表响应 */
export interface MCPToolsResponse {
  tools: MCPToolInfo[]
}

/** MCP 健康检查响应 */
export interface MCPHealthResponse {
  status: string
  module: string
}

/** MCP 系统配置 */
export interface MCPSystemSettings {
  pool_personal_max_concurrency: number
  pool_public_per_user_max: number
  pool_personal_queue_size: number
  pool_public_queue_size: number
  connection_complete_timeout: number
  connection_failed_timeout: number
  health_check_enabled: boolean
  health_check_interval: number
  health_check_timeout: number
  updated_at?: string | null
}

/** 连接池统计（管理员） */
export interface MCPPoolStats {
  pool: Record<string, unknown>
  servers: Record<string, {
    name: string
    is_system: boolean
    owner_id: string | null
    status: MCPServerStatus
    enabled: boolean
  }>
}

/** 通用操作结果 */
export interface OperationResponse {
  message: string
  success: boolean
}

/** MCP 连接器（兼容旧接口，useMCP hook 使用） */
export interface MCPConnector {
  name: string
  transport: TransportMode
  enabled: boolean
  status: MCPServerStatus
  command?: string | null
  args?: string[] | null
  url?: string | null
  is_system?: boolean
  type?: TransportMode
  healthInfo?: Record<string, unknown> | null
}

// =============================================================================
// MCP 服务器管理
// =============================================================================

/** 列出所有 MCP 服务器（系统 + 用户） */
export async function listMCPServers(): Promise<MCPServerListResponse> {
  const res = await apiClient.get<MCPServerListResponse>('/api/mcp/servers')
  return res.data
}

/** 获取单个 MCP 服务器配置 */
export async function getMCPServer(serverId: string): Promise<MCPServer> {
  const res = await apiClient.get<MCPServer>(`/api/mcp/servers/${serverId}`)
  return res.data
}

/** 创建 MCP 服务器 */
export async function createMCPServer(data: MCPServerCreateRequest): Promise<MCPServer> {
  const res = await apiClient.post<MCPServer>('/api/mcp/servers', data)
  return res.data
}

/** 更新 MCP 服务器配置 */
export async function updateMCPServer(serverId: string, data: MCPServerUpdateRequest): Promise<MCPServer> {
  const res = await apiClient.put<MCPServer>(`/api/mcp/servers/${serverId}`, data)
  return res.data
}

/** 删除 MCP 服务器 */
export async function deleteMCPServer(serverId: string): Promise<OperationResponse> {
  const res = await apiClient.delete<OperationResponse>(`/api/mcp/servers/${serverId}`)
  return res.data
}

/** 测试 MCP 服务器连接 */
export async function testMCPServer(serverId: string): Promise<ConnectionTestResponse> {
  const res = await apiClient.post<ConnectionTestResponse>(`/api/mcp/servers/${serverId}/test`)
  return res.data
}

/** 获取 MCP 服务器的工具列表 */
export async function getMCPServerTools(serverId: string): Promise<MCPToolsResponse> {
  const res = await apiClient.get<MCPToolsResponse>(`/api/mcp/servers/${serverId}/tools`)
  return res.data
}

/** 切换 MCP 服务器启用状态（通过 updateMCPServer 设置 enabled 字段） */
export async function toggleMCPServer(serverId: string, enabled: boolean): Promise<MCPServer> {
  return updateMCPServer(serverId, { enabled })
}

// =============================================================================
// 连接池管理（管理员）
// =============================================================================

/** 获取连接池统计信息（管理员） */
export async function getMCPPoolStats(): Promise<MCPPoolStats> {
  const res = await apiClient.get<MCPPoolStats>('/api/mcp/pool/stats')
  return res.data
}

/** 禁用 MCP 服务器（管理员） */
export async function disableMCPServer(serverId: string): Promise<OperationResponse> {
  const res = await apiClient.post<OperationResponse>(`/api/mcp/pool/servers/${serverId}/disable`)
  return res.data
}

// =============================================================================
// MCP 系统配置
// =============================================================================

/** 获取 MCP 系统配置 */
export async function getMCPSettings(): Promise<MCPSystemSettings> {
  const res = await apiClient.get<MCPSystemSettings>('/api/mcp/settings')
  return res.data
}

/** 更新 MCP 系统配置（管理员） */
export async function updateMCPSettings(data: MCPSystemSettings): Promise<MCPSystemSettings> {
  const res = await apiClient.put<MCPSystemSettings>('/api/mcp/settings', data)
  return res.data
}

/** 重置 MCP 系统配置为默认值（管理员） */
export async function resetMCPSettings(): Promise<OperationResponse> {
  const res = await apiClient.post<OperationResponse>('/api/mcp/settings/reset')
  return res.data
}

// =============================================================================
// 健康检查
// =============================================================================

/** MCP 健康检查 */
export async function getMCPHealth(): Promise<MCPHealthResponse> {
  const res = await apiClient.get<MCPHealthResponse>('/api/mcp/health')
  return res.data
}

// =============================================================================
// MCP 连接器（兼容旧接口，useMCP hook 使用）
// =============================================================================

/** 列出所有 MCP 连接器 */
export async function listMCPConnectors(): Promise<MCPConnector[]> {
  const res = await listMCPServers()
  const connectors: MCPConnector[] = []
  for (const s of res.system) {
    connectors.push({
      name: s.name,
      transport: s.transport,
      enabled: s.enabled,
      status: s.status,
      command: s.command,
      args: s.args,
      url: s.url,
      is_system: s.is_system,
    })
  }
  for (const s of res.user) {
    connectors.push({
      name: s.name,
      transport: s.transport,
      enabled: s.enabled,
      status: s.status,
      command: s.command,
      args: s.args,
      url: s.url,
      is_system: s.is_system,
    })
  }
  return connectors
}

/** 切换 MCP 连接器启用状态 */
export async function toggleMCPConnector(name: string, enabled: boolean): Promise<void> {
  const servers = await listMCPServers()
  const target = [...servers.system, ...servers.user].find(s => s.name === name)
  if (target) {
    await updateMCPServer(target.id, { enabled })
  }
}

/** 删除 MCP 连接器 */
export async function deleteMCPConnector(name: string): Promise<void> {
  const servers = await listMCPServers()
  const target = [...servers.system, ...servers.user].find(s => s.name === name)
  if (target) {
    await deleteMCPServer(target.id)
  }
}

/** 批量更新 MCP 连接器配置 */
export async function updateMCPConnectors(mcpServers: Record<string, unknown>): Promise<OperationResponse> {
  const res = await apiClient.post<OperationResponse>('/api/mcp/connectors/update', mcpServers)
  return res.data
}

/** 重载 MCP 配置 */
export async function reloadMCPConfig(): Promise<OperationResponse> {
  const res = await apiClient.post<OperationResponse>('/api/mcp/reload')
  return res.data
}

/** 触发 MCP 健康检查 */
export async function triggerMCPHealthCheck(): Promise<Record<string, unknown>> {
  const res = await apiClient.post<Record<string, unknown>>('/api/mcp/health-check')
  return res.data
}
