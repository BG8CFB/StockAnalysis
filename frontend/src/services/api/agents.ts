/**
 * 智能体配置管理 API
 * 对应后端 modules/trading_agents/api/tasks.py 中的 config_router（前缀 /api/trading-agents/agent-config）
 *
 * 后端直接返回数据（无 ApiResponse 包装），前端 apiClient 返回 axios response.data。
 */

import apiClient from '../http/client'

// =============================================================================
// 类型定义
// =============================================================================

/** MCP 服务器配置 */
export interface MCPServerRef {
  name: string
  required: boolean
}

/** 单个智能体配置（完整版，含提示词） */
export interface AgentConfig {
  slug: string
  name: string
  role_definition: string
  when_to_use?: string
  enabled_mcp_servers: string[]
  enabled_local_tools: string[]
  enabled: boolean
}

/** 单个智能体配置（精简版，不含提示词） */
export interface AgentConfigSlim {
  slug: string
  name: string
  when_to_use?: string
  enabled_mcp_servers: string[]
  enabled_local_tools: string[]
  enabled: boolean
}

/** 阶段配置基础 */
export interface PhaseConfig<TAgent = AgentConfig | AgentConfigSlim> {
  enabled: boolean
  agents: TAgent[]
}

/** 第一阶段配置 */
export interface Phase1Config extends PhaseConfig {
  enabled: boolean
  agents: AgentConfig[]
  max_concurrency: number
}

/** 第二阶段配置 */
export interface Phase2Config extends PhaseConfig {
  enabled: boolean
  agents: AgentConfig[]
  debate_rounds?: number | null
}

/** 第三阶段配置 */
export interface Phase3Config extends PhaseConfig {
  enabled: boolean
  agents: AgentConfig[]
}

/** 第四阶段配置 */
export interface Phase4Config extends PhaseConfig {
  enabled: boolean
  agents: AgentConfig[]
}

/** 用户智能体配置响应 */
export interface AgentConfigResponse {
  id: string
  user_id: string
  is_public: boolean
  is_customized: boolean
  phase1: Phase1Config
  phase2: Phase2Config | null
  phase3: Phase3Config | null
  phase4: Phase4Config | null
  created_at: string
  updated_at: string
}

/** 更新智能体配置请求 */
export interface AgentConfigUpdateRequest {
  phase1?: Phase1Config | null
  phase2?: Phase2Config | null
  phase3?: Phase3Config | null
  phase4?: Phase4Config | null
}

/** 导出配置响应 */
export interface AgentConfigExportResponse {
  config: {
    phase1: Record<string, unknown>
    phase2: Record<string, unknown> | null
    phase3: Record<string, unknown> | null
    phase4: Record<string, unknown> | null
  }
}

// =============================================================================
// 用户智能体配置
// =============================================================================

/** 获取用户智能体配置 */
export async function getAgentConfig(includePrompts = false): Promise<AgentConfigResponse> {
  return apiClient.get<AgentConfigResponse>('/api/trading-agents/agent-config', {
    include_prompts: includePrompts,
  }) as unknown as Promise<AgentConfigResponse>
}

/** 更新用户智能体配置 */
export async function updateAgentConfig(data: AgentConfigUpdateRequest): Promise<AgentConfigResponse> {
  return apiClient.put<AgentConfigResponse>('/api/trading-agents/agent-config', data) as unknown as Promise<AgentConfigResponse>
}

/** 重置为默认智能体配置 */
export async function resetAgentConfig(): Promise<AgentConfigResponse> {
  return apiClient.post<AgentConfigResponse>('/api/trading-agents/agent-config/reset') as unknown as Promise<AgentConfigResponse>
}

/** 导出智能体配置 */
export async function exportAgentConfig(): Promise<AgentConfigExportResponse> {
  return apiClient.post<AgentConfigExportResponse>('/api/trading-agents/agent-config/export') as unknown as Promise<AgentConfigExportResponse>
}

/** 导入智能体配置 */
export async function importAgentConfig(configData: Record<string, unknown>): Promise<AgentConfigResponse> {
  return apiClient.post<AgentConfigResponse>('/api/trading-agents/agent-config/import', configData) as unknown as Promise<AgentConfigResponse>
}

// =============================================================================
// 公共智能体配置（管理员）
// =============================================================================

/** 获取公共智能体配置（管理员） */
export async function getPublicAgentConfig(includePrompts = false): Promise<AgentConfigResponse> {
  return apiClient.get<AgentConfigResponse>('/api/trading-agents/agent-config/public', {
    include_prompts: includePrompts,
  }) as unknown as Promise<AgentConfigResponse>
}

/** 更新公共智能体配置（管理员） */
export async function updatePublicAgentConfig(data: AgentConfigUpdateRequest): Promise<AgentConfigResponse> {
  return apiClient.put<AgentConfigResponse>('/api/trading-agents/agent-config/public', data) as unknown as Promise<AgentConfigResponse>
}

/** 恢复公共智能体配置为 YAML 默认值（管理员） */
export async function restorePublicAgentConfig(): Promise<{ success: boolean; message: string }> {
  return apiClient.post<{ success: boolean; message: string }>(
    '/api/admin/trading-agents/agent-config/public/restore',
  ) as unknown as Promise<{ success: boolean; message: string }>
}

// =============================================================================
// 智能体项（AgentManagementPage 使用）
// =============================================================================

/** 智能体列表项 */
export interface AgentItem {
  id: string
  name: string
  stage: string
  type: string
  description: string
  prompt: string
  enabled: boolean
  is_system: boolean
}

/** 列出所有智能体 */
export async function listAgents(): Promise<AgentItem[]> {
  return apiClient.get<AgentItem[]>('/api/trading-agents/agents') as unknown as Promise<AgentItem[]>
}

/** 保存智能体（创建或更新） */
export async function saveAgent(agent: Partial<AgentItem> & { id: string }): Promise<AgentItem> {
  return apiClient.put<AgentItem>(`/api/trading-agents/agents/${agent.id}`, agent) as unknown as Promise<AgentItem>
}

/** 删除智能体 */
export async function deleteAgent(agentId: string): Promise<{ success: boolean; message: string }> {
  return apiClient.delete<{ success: boolean; message: string }>(`/api/trading-agents/agents/${agentId}`) as unknown as Promise<{ success: boolean; message: string }>
}
