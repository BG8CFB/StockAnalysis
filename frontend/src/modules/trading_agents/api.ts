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
  MCPServerConfig,
  MCPServerConfigCreate,
  MCPServerConfigUpdate,
  MCPTool,
  UserAgentConfig,
  UserAgentConfigUpdate,
  AnalysisTask,
  AnalysisTaskCreate,
  BatchTask,
  BatchTaskCreate,
  AnalysisReport,
  ReportSummary,
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
}

// =============================================================================
// MCP 服务器管理 API
// =============================================================================

export const mcpApi = {
  /**
   * 创建 MCP 服务器配置
   */
  createServer: (data: MCPServerConfigCreate) =>
    httpPost<MCPServerConfig>(`${TRADING_AGENTS_BASE_URL}/mcp-servers`, data),

  /**
   * 获取服务器列表
   */
  listServers: () =>
    httpGet<{ system: MCPServerConfig[]; user: MCPServerConfig[] }>(`${TRADING_AGENTS_BASE_URL}/mcp-servers`),

  /**
   * 获取单个服务器配置
   */
  getServer: (serverId: string) =>
    httpGet<MCPServerConfig>(`${TRADING_AGENTS_BASE_URL}/mcp-servers/${serverId}`),

  /**
   * 更新服务器配置
   */
  updateServer: (serverId: string, data: MCPServerConfigUpdate) =>
    httpPut<MCPServerConfig>(`${TRADING_AGENTS_BASE_URL}/mcp-servers/${serverId}`, data),

  /**
   * 删除服务器配置
   */
  deleteServer: (serverId: string) =>
    httpDelete<{ success: boolean; message: string }>(`${TRADING_AGENTS_BASE_URL}/mcp-servers/${serverId}`),

  /**
   * 测试服务器连接
   */
  testServer: (serverId: string) =>
    httpPost<ConnectionTestResponse>(`${TRADING_AGENTS_BASE_URL}/mcp-servers/${serverId}/test`, {}),

  /**
   * 获取服务器工具列表
   */
  getServerTools: (serverId: string) =>
    httpGet<{ tools: MCPTool[] }>(`${TRADING_AGENTS_BASE_URL}/mcp-servers/${serverId}/tools`),
}

// =============================================================================
// 智能体配置 API
// =============================================================================

export const agentConfigApi = {
  /**
   * 获取用户智能体配置
   * 返回生效配置（个人配置或公共配置）
   */
  getAgentConfig: () =>
    httpGet<UserAgentConfig>(`${TRADING_AGENTS_BASE_URL}/agent-config`),

  /**
   * 更新用户智能体配置
   * 更新后会标记为已自定义
   */
  updateConfig: (data: UserAgentConfigUpdate) =>
    httpPut<UserAgentConfig>(`${TRADING_AGENTS_BASE_URL}/agent-config`, data),

  /**
   * 重置为默认配置
   * 重置为公共配置（模板）
   */
  resetConfig: () =>
    httpPost<UserAgentConfig>(`${TRADING_AGENTS_BASE_URL}/agent-config/reset`, {}),

  /**
   * 获取公共智能体配置（模板）
   * 仅管理员可访问
   */
  getPublicConfig: () =>
    httpGet<UserAgentConfig>(`${TRADING_AGENTS_BASE_URL}/agent-config/public`),

  /**
   * 更新公共智能体配置（模板）
   * 仅管理员可访问
   */
  updatePublicConfig: (data: UserAgentConfigUpdate) =>
    httpPut<UserAgentConfig>(`${TRADING_AGENTS_BASE_URL}/agent-config/public`, data),

  /**
   * 导出配置
   */
  exportConfig: () =>
    httpPost<{ config: Record<string, unknown> }>(`${TRADING_AGENTS_BASE_URL}/agent-config/export`, {}),

  /**
   * 导入配置
   */
  importConfig: (configData: Record<string, unknown>) =>
    httpPost<UserAgentConfig>(`${TRADING_AGENTS_BASE_URL}/agent-config/import`, configData),
}

// =============================================================================
// 任务管理 API
// =============================================================================

export const taskApi = {
  /**
   * 创建分析任务
   */
  createTask: (data: AnalysisTaskCreate) =>
    httpPost<AnalysisTaskResponse>(`${TRADING_AGENTS_BASE_URL}/tasks`, data),

  /**
   * 创建批量任务
   */
  createBatchTask: (data: BatchTaskCreate) =>
    httpPost<BatchTaskResponse>(`${TRADING_AGENTS_BASE_URL}/tasks/batch`, data),

  /**
   * 获取任务列表
   */
  listTasks: (params?: {
    status?: string
    stock_code?: string
    recommendation?: string
    risk_level?: string
    limit?: number
    offset?: number
  }) =>
    httpGet<{ tasks: AnalysisTask[]; total: number }>(`${TRADING_AGENTS_BASE_URL}/tasks`, params),

  /**
   * 获取任务详情
   */
  getTask: (taskId: string) =>
    httpGet<AnalysisTask>(`${TRADING_AGENTS_BASE_URL}/tasks/${taskId}`),

  /**
   * 取消任务
   */
  cancelTask: (taskId: string) =>
    httpPost<{ success: boolean; message: string }>(`${TRADING_AGENTS_BASE_URL}/tasks/${taskId}/cancel`, {}),

  /**
   * 重试任务
   */
  retryTask: (taskId: string) =>
    httpPost<AnalysisTaskResponse>(`${TRADING_AGENTS_BASE_URL}/tasks/${taskId}/retry`, {}),

  /**
   * 删除任务
   */
  deleteTask: (taskId: string) =>
    httpDelete<{ success: boolean; message: string }>(`${TRADING_AGENTS_BASE_URL}/tasks/${taskId}`),

  /**
   * 获取任务队列位置
   */
  getQueuePosition: (taskId: string) =>
    httpGet<{ position: number; waiting_count: number }>(`${TRADING_AGENTS_BASE_URL}/tasks/${taskId}/queue-position`),
}

// =============================================================================
// 报告管理 API
// =============================================================================

export const reportApi = {
  /**
   * 获取报告列表
   */
  listReports: (params?: {
    stock_code?: string
    recommendation?: string
    risk_level?: string
    limit?: number
    offset?: number
  }) =>
    httpGet<{ reports: AnalysisReport[] }>(`${TRADING_AGENTS_BASE_URL}/reports`, params),

  /**
   * 获取报告统计摘要
   */
  getReportSummary: (days?: number) =>
    httpGet<ReportSummary>(`${TRADING_AGENTS_BASE_URL}/reports/summary`, { days }),

  /**
   * 获取报告详情
   */
  getReport: (reportId: string) =>
    httpGet<AnalysisReport>(`${TRADING_AGENTS_BASE_URL}/reports/${reportId}`),

  /**
   * 删除报告
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
