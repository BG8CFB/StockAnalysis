/**
 * TradingAgents 模块 API 客户线
 *
 * 注意：AI 模型管理 API 已移至核心设置模块 (@core/settings)
 */
import { httpGet, httpPost, httpPut, httpDelete } from '@core/api/http'
import type {
  MCPServerConfig,
  MCPServerConfigCreate,
  MCPServerConfigUpdate,
  MCPTool,
  UserAgentConfig,
  UserAgentConfigUpdate,
  AnalysisTask,
  AnalysisTaskResponse,
  BatchTask,
  AnalysisReport,
  ReportSummary,
  TradingAgentsSettings,
  TradingAgentsSettingsResponse,
  // 统一任务类型
  UnifiedTaskCreate,
  UnifiedTaskResponse,
} from './types'

const MCP_BASE_URL = '/mcp'
const TRADING_AGENTS_BASE_URL = '/trading-agents'

// =============================================================================
// MCP 服务器管理 API
// =============================================================================

export const mcpApi = {
  /**
   * 创建 MCP 服务器配置
   */
  createServer: (data: MCPServerConfigCreate) =>
    httpPost<MCPServerConfig>(`${MCP_BASE_URL}/servers`, data),

  /**
   * 获取服务器列表
   */
  listServers: () =>
    httpGet<{ system: MCPServerConfig[]; user: MCPServerConfig[] }>(`${MCP_BASE_URL}/servers`),

  /**
   * 获取单个服务器配置
   */
  getServer: (serverId: string) =>
    httpGet<MCPServerConfig>(`${MCP_BASE_URL}/servers/${serverId}`),

  /**
   * 更新服务器配置
   */
  updateServer: (serverId: string, data: MCPServerConfigUpdate) =>
    httpPut<MCPServerConfig>(`${MCP_BASE_URL}/servers/${serverId}`, data),

  /**
   * 删除服务器配置
   */
  deleteServer: (serverId: string) =>
    httpDelete<{ success: boolean; message: string }>(`${MCP_BASE_URL}/servers/${serverId}`),

  /**
   * 测试服务器连接
   * 后端: POST /mcp/servers/{server_id}/test
   */
  testServer: (serverId: string) =>
    httpPost<{ success: boolean; message: string; latency_ms?: number }>(`${MCP_BASE_URL}/servers/${serverId}/test`, {}),

  /**
   * 获取服务器工具列表
   * 后端: GET /mcp/servers/{server_id}/tools
   */
  getServerTools: (serverId: string) =>
    httpGet<{ tools: MCPTool[] }>(`${MCP_BASE_URL}/servers/${serverId}/tools`),
}

// =============================================================================
// 智能体配置 API
// =============================================================================

export const agentConfigApi = {
  /**
   * 获取用户智能体配置
   * 返回生效配置（个人配置或公共配置）
   *
   * @param includePrompts 是否包含提示词（仅管理员可用）
   *   - false: 返回精简配置（不含提示词），用于分析页面
   *   - true: 返回完整配置（含提示词），用于配置管理页面
   * 后端: GET /trading-agents/agent-config?include_prompts={boolean}
   */
  getAgentConfig: (includePrompts: boolean = false) =>
    httpGet<UserAgentConfig>(`${TRADING_AGENTS_BASE_URL}/agent-config`, {
      params: { include_prompts: includePrompts }
    }),

  /**
   * 更新用户智能体配置
   * 更新后会标记为已自定义
   * 后端: PUT /trading-agents/agent-config
   */
  updateConfig: (data: UserAgentConfigUpdate) =>
    httpPut<UserAgentConfig>(`${TRADING_AGENTS_BASE_URL}/agent-config`, data),

  /**
   * 重置为默认配置
   * 重置为公共配置（模板）
   * 后端: POST /trading-agents/agent-config/reset
   */
  resetConfig: () =>
    httpPost<UserAgentConfig>(`${TRADING_AGENTS_BASE_URL}/agent-config/reset`, {}),

  /**
   * 获取公共智能体配置（模板）
   * 仅管理员可访问
   *
   * @param includePrompts 是否包含提示词
   * 后端: GET /trading-agents/agent-config/public?include_prompts={boolean}
   */
  getPublicConfig: (includePrompts: boolean = false) =>
    httpGet<UserAgentConfig>(`${TRADING_AGENTS_BASE_URL}/agent-config/public`, {
      params: { include_prompts: includePrompts }
    }),

  /**
   * 更新公共智能体配置（模板）
   * 仅管理员可访问
   * 后端: PUT /trading-agents/agent-config/public
   */
  updatePublicConfig: (data: UserAgentConfigUpdate) =>
    httpPut<UserAgentConfig>(`${TRADING_AGENTS_BASE_URL}/agent-config/public`, data),

  /**
   * 导出配置
   * 后端: POST /trading-agents/agent-config/export
   */
  exportConfig: () =>
    httpPost<{ config: Record<string, unknown> }>(`${TRADING_AGENTS_BASE_URL}/agent-config/export`, {}),

  /**
   * 导入配置
   * 后端: POST /trading-agents/agent-config/import
   */
  importConfig: (configData: Record<string, unknown>) =>
    httpPost<UserAgentConfig>(`${TRADING_AGENTS_BASE_URL}/agent-config/import`, configData),
}

// =============================================================================
// TradingAgents 设置 API（全局配置，管理员管理）
// =============================================================================

export const settingsApi = {
  /**
   * 获取 TradingAgents 全局配置
   * 返回全局的分析规则配置（所有用户共享）
   * 后端: GET /settings/trading-agents
   */
  getSettings: async (): Promise<TradingAgentsSettings> => {
    // 直接返回全局配置，不再嵌套在 trading_agents_settings 中
    const response = await httpGet<TradingAgentsSettings>(`/settings/trading-agents`)
    return response
  },

  /**
   * 更新 TradingAgents 全局配置（管理员）
   * 更新全局的分析规则配置（所有用户共享）
   * 后端: PUT /admin/settings/trading-agents
   */
  updateSettings: async (data: TradingAgentsSettings): Promise<TradingAgentsSettings> => {
    const response = await httpPut<TradingAgentsSettings>(`/admin/settings/trading-agents`, data)
    return response
  },
}

// =============================================================================
// 任务管理 API
// =============================================================================

export const taskApi = {
  /**
   * 统一任务创建接口（支持单股和批量）
   *
   * 根据传入的股票代码数量自动判断：
   * - 1 个股票代码：创建单个任务，返回 task_id
   * - 多个股票代码：创建批量任务，返回 batch_id
   * 后端: POST /trading-agents/tasks
   */
  createTasks: (data: UnifiedTaskCreate) =>
    httpPost<UnifiedTaskResponse>(`${TRADING_AGENTS_BASE_URL}/tasks`, data),

  /**
   * 获取任务列表
   * 后端: GET /trading-agents/tasks
   */
  listTasks: (params?: {
    status?: string
    stock_code?: string
    recommendation?: string
    risk_level?: string
    limit?: number
    offset?: number
  }) =>
    httpGet<{ tasks: AnalysisTask[]; total: number }>(`${TRADING_AGENTS_BASE_URL}/tasks`, {
      params
    }),

  /**
   * 获取任务详情
   * 后端: GET /trading-agents/tasks/{id}
   */
  getTask: (taskId: string) =>
    httpGet<AnalysisTask>(`${TRADING_AGENTS_BASE_URL}/tasks/${taskId}`),

  /**
   * 取消任务
   * 后端: POST /trading-agents/tasks/{id}/cancel
   */
  cancelTask: (taskId: string) =>
    httpPost<{ success: boolean; message: string }>(`${TRADING_AGENTS_BASE_URL}/tasks/${taskId}/cancel`, {}),

  /**
   * 重试任务
   * 后端: POST /trading-agents/tasks/{id}/retry
   */
  retryTask: (taskId: string) =>
    httpPost<AnalysisTaskResponse>(`${TRADING_AGENTS_BASE_URL}/tasks/${taskId}/retry`, {}),

  /**
   * 删除任务
   * 后端: DELETE /trading-agents/tasks/{id}
   */
  deleteTask: (taskId: string) =>
    httpDelete<{ success: boolean; message: string }>(`${TRADING_AGENTS_BASE_URL}/tasks/${taskId}`),

  /**
   * 获取任务队列位置
   * 后端: GET /trading-agents/tasks/{id}/queue-position
   */
  getQueuePosition: (taskId: string) =>
    httpGet<{ position: number; waiting_count: number }>(
      `${TRADING_AGENTS_BASE_URL}/tasks/${taskId}/queue-position`
    ),

  /**
   * 获取任务状态统计
   * 后端: GET /trading-agents/tasks/status-counts
   */
  getStatusCounts: () =>
    httpGet<{
      all: number
      running: number
      completed: number
      failed: number
      cancelled: number
      _detail?: {
        pending: number
        running: number
        completed: number
        failed: number
        cancelled: number
        stopped: number
      }
    }>(`${TRADING_AGENTS_BASE_URL}/tasks/status-counts`),

  /**
   * 批量清空指定状态的任务
   * 后端: DELETE /trading-agents/tasks/clear
   */
  clearTasksByStatus: (params: {
    statuses: string
    delete_reports?: boolean
  }) =>
    httpDelete<{ success: boolean; message: string }>(
      `${TRADING_AGENTS_BASE_URL}/tasks/clear`,
      { params }
    ),

  /**
   * 批量删除任务
   * 后端: POST /trading-agents/tasks/batch-delete
   */
  batchDeleteTasks: (params: {
    task_ids: string[]
    delete_reports?: boolean
  }) =>
    httpPost<{
      success_count: number
      failed_count: number
      failed_tasks: Array<{ task_id: string; reason: string }>
      message: string
    }>(`${TRADING_AGENTS_BASE_URL}/tasks/batch-delete`, params),

  /**
   * 获取智能体思考过程
   * 后端: GET /trading-agents/tasks/{task_id}/agents/{agent_slug}/thinking
   */
  getAgentThinking: (taskId: string, agentSlug: string) =>
    httpGet<string>(`${TRADING_AGENTS_BASE_URL}/tasks/${taskId}/agents/${agentSlug}/thinking`),
}

// =============================================================================
// 健康检查
// =============================================================================

export const healthApi = {
  /**
   * 健康检查
   */
  check: () =>
    httpGet<{ status: string; module: string }>(`${TRADING_AGENTS_BASE_URL}/health`),
}

// =============================================================================
// 市场数据 API（用于获取股票名称）
// =============================================================================

export const marketDataApi = {
  /**
   * 获取单个股票名称
   * 后端: GET /market-data/stocks/name
   */
  getStockName: (params: {
    code: string
    market: string
  }) =>
    httpGet<{
      success: boolean
      data: {
        code: string
        symbol: string
        name: string
      }
    }>('/market-data/stocks/name', { params }),

  /**
   * 批量获取股票名称
   * 后端: POST /market-data/stocks/batch-names
   */
  getBatchStockNames: (params: {
    codes: string[]
    market: string
  }) =>
    httpPost<{
      success: boolean
      data: Array<{
        code: string
        symbol: string
        name: string
      }>
    }>('/market-data/stocks/batch-names', params),
}
