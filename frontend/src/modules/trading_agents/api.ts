/**
 * TradingAgents 模块 API 客户端
 */
import { httpGet, httpPost, httpPut, httpDelete } from '@core/api/http'
import type {
  AIModelConfig,
  AIModelConfigCreate,
  AIModelConfigUpdate,
  AIModelTestRequest,
  ConnectionTestResponse,
  ListModelsRequest,
  ListModelsResponse,
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

// AI 模型管理使用核心模块路径
const AI_BASE_URL = '/ai'
const TRADING_AGENTS_BASE_URL = '/trading-agents'

// =============================================================================
// AI 模型管理 API
// =============================================================================

export const modelApi = {
  /**
   * 创建 AI 模型配置
   */
  createModel: (data: AIModelConfigCreate) =>
    httpPost<AIModelConfig>(`${AI_BASE_URL}/models`, data),

  /**
   * 获取模型列表
   */
  listModels: () =>
    httpGet<{ system: AIModelConfig[]; user: AIModelConfig[] }>(`${AI_BASE_URL}/models`),

  /**
   * 获取单个模型配置
   */
  getModel: (modelId: string) =>
    httpGet<AIModelConfig>(`${AI_BASE_URL}/models/${modelId}`),

  /**
   * 更新模型配置
   */
  updateModel: (modelId: string, data: AIModelConfigUpdate) =>
    httpPut<AIModelConfig>(`${AI_BASE_URL}/models/${modelId}`, data),

  /**
   * 删除模型配置
   */
  deleteModel: (modelId: string) =>
    httpDelete<{ success: boolean; message: string }>(`${AI_BASE_URL}/models/${modelId}`),

  /**
   * 测试模型连接
   */
  testModel: (modelId: string) =>
    httpPost<ConnectionTestResponse>(`${AI_BASE_URL}/models/${modelId}/test`, {}),

  /**
   * 测试模型连接（通用接口）
   */
  testModelConnection: (data: AIModelTestRequest) =>
    httpPost<ConnectionTestResponse>(`${AI_BASE_URL}/models/test`, data),

  /**
   * 获取可用的模型列表
   */
  listAvailableModels: (data: ListModelsRequest) =>
    httpPost<ListModelsResponse>(`${AI_BASE_URL}/models/list-available`, data),
}

// =============================================================================
// MCP 服务器管理 API
// =============================================================================

const MCP_BASE_URL = '/mcp'

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
   */
  testServer: (serverId: string) =>
    httpPost<ConnectionTestResponse>(`${MCP_BASE_URL}/servers/${serverId}/test`, {}),

  /**
   * 获取服务器工具列表
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
   * 恢复公共配置为默认值
   * 从YAML重新导入，仅管理员可访问
   * 后端: POST /admin/trading-agents/agent-config/public/restore
   */
  restorePublicConfig: () =>
    httpPost<{ success: boolean; message: string; config: UserAgentConfig }>(
      `/admin/trading-agents/agent-config/public/restore`,
      {}
    ),

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
// TradingAgents 设置 API
// =============================================================================

export const settingsApi = {
  /**
   * 获取用户的 TradingAgents 设置
   * 返回用户的分析规则配置
   */
  getSettings: () =>
    httpGet<TradingAgentsSettingsResponse>(`${TRADING_AGENTS_BASE_URL}/settings`),

  /**
   * 更新用户的 TradingAgents 设置
   * 更新用户的分析规则配置
   */
  updateSettings: (data: TradingAgentsSettings) =>
    httpPut<TradingAgentsSettingsResponse>(`${TRADING_AGENTS_BASE_URL}/settings`, data),
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
}

// =============================================================================
// 报告管理 API
// =============================================================================

export const reportApi = {
  /**
   * 获取报告列表
   * 后端: GET /trading-agents/reports
   */
  listReports: (params?: {
    stock_code?: string
    recommendation?: string
    risk_level?: string
    limit?: number
    offset?: number
  }) =>
    httpGet<{ reports: AnalysisReport[] }>(`${TRADING_AGENTS_BASE_URL}/reports`, {
      params
    }),

  /**
   * 获取报告统计摘要
   * 后端: GET /trading-agents/reports/summary
   */
  getReportSummary: (days?: number) =>
    httpGet<ReportSummary>(`${TRADING_AGENTS_BASE_URL}/reports/summary`, {
      params: days !== undefined ? { days } : undefined
    }),

  /**
   * 获取报告详情
   * 后端: GET /trading-agents/reports/{id}
   */
  getReport: (reportId: string) =>
    httpGet<AnalysisReport>(`${TRADING_AGENTS_BASE_URL}/reports/${reportId}`),

  /**
   * 删除报告
   * 后端: DELETE /trading-agents/reports/{id}
   */
  deleteReport: (reportId: string) =>
    httpDelete<{ success: boolean; message: string }>(`${TRADING_AGENTS_BASE_URL}/reports/${reportId}`),
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
