/**
 * TradingAgents 模块 Pinia Store
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  modelApi,
  mcpApi,
  agentConfigApi,
  taskApi,
  reportApi,
} from './api'
import type {
  AIModelConfig,
  AIModelConfigCreate,
  AIModelConfigUpdate,
  MCPServerConfig,
  MCPServerConfigCreate,
  MCPServerConfigUpdate,
  UserAgentConfig,
  UserAgentConfigUpdate,
  AnalysisTask,
  UnifiedTaskCreate,
  BatchTask,
  AnalysisReport,
  ReportSummary,
  ModelProviderEnum,
} from './types'

export const useTradingAgentsStore = defineStore('tradingAgents', () => {
  // =========================================================================
  // 状态
  // =========================================================================

  // AI 模型
  const systemModels = ref<AIModelConfig[]>([])
  const userModels = ref<AIModelConfig[]>([])
  const modelsLoading = ref(false)

  // MCP 服务器
  const systemServers = ref<MCPServerConfig[]>([])
  const userServers = ref<MCPServerConfig[]>([])
  const serversLoading = ref(false)

  // 智能体配置
  const agentConfig = ref<UserAgentConfig | null>(null)
  const publicConfig = ref<UserAgentConfig | null>(null)
  const configLoading = ref(false)

  // 任务
  const tasks = ref<AnalysisTask[]>([])
  const tasksTotal = ref(0)
  const tasksLoading = ref(false)

  // 报告
  const reports = ref<AnalysisReport[]>([])
  const reportSummary = ref<ReportSummary | null>(null)
  const reportsLoading = ref(false)

  // =========================================================================
  // 计算属性
  // =========================================================================

  const allModels = computed(() => [...systemModels.value, ...userModels.value])
  const allServers = computed(() => [...systemServers.value, ...userServers.value])
  const enabledModels = computed(() => allModels.value.filter((m) => m.enabled))
  const enabledServers = computed(() => allServers.value.filter((s) => s.enabled))

  // =========================================================================
  // AI 模型操作
  // =========================================================================

  async function fetchModels() {
    modelsLoading.value = true
    try {
      const result = await modelApi.listModels()
      systemModels.value = result.system || []
      userModels.value = result.user || []
    } catch (error: any) {
      ElMessage.error('获取模型列表失败')
      throw error
    } finally {
      modelsLoading.value = false
    }
  }

  async function createModel(data: AIModelConfigCreate) {
    try {
      const result = await modelApi.createModel(data)
      await fetchModels()
      ElMessage.success('模型配置已创建')
      return result
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '创建模型配置失败')
      throw error
    }
  }

  async function updateModel(modelId: string, data: AIModelConfigUpdate) {
    try {
      const result = await modelApi.updateModel(modelId, data)
      await fetchModels()
      ElMessage.success('模型配置已更新')
      return result
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '更新模型配置失败')
      throw error
    }
  }

  async function deleteModel(modelId: string) {
    try {
      await modelApi.deleteModel(modelId)
      await fetchModels()
      ElMessage.success('模型配置已删除')
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '删除模型配置失败')
      throw error
    }
  }

  async function testModel(modelId: string) {
    try {
      const result = await modelApi.testModel(modelId)
      if (result.success) {
        ElMessage.success(`连接成功，延迟 ${result.latency_ms}ms`)
      } else {
        ElMessage.error(result.message || '连接失败')
      }
      return result
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '测试连接失败')
      throw error
    }
  }

  async function testModelConnection(data: { api_base_url: string; api_key: string; model_id: string }) {
    try {
      const result = await modelApi.testModelConnection(data)
      if (result.success) {
        ElMessage.success(`连接成功，延迟 ${result.latency_ms}ms`)
      } else {
        ElMessage.error(result.message || '连接失败')
      }
      return result
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '测试连接失败')
      throw error
    }
  }

  // =========================================================================
  // MCP 服务器操作
  // =========================================================================

  async function fetchServers() {
    serversLoading.value = true
    try {
      const result = await mcpApi.listServers()
      systemServers.value = result.system || []
      userServers.value = result.user || []
    } catch (error: any) {
      ElMessage.error('获取服务器列表失败')
      throw error
    } finally {
      serversLoading.value = false
    }
  }

  async function createServer(data: MCPServerConfigCreate) {
    try {
      const result = await mcpApi.createServer(data)
      await fetchServers()
      ElMessage.success('MCP 服务器配置已创建')
      return result
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '创建服务器配置失败')
      throw error
    }
  }

  async function updateServer(serverId: string, data: MCPServerConfigUpdate) {
    try {
      const result = await mcpApi.updateServer(serverId, data)
      await fetchServers()
      ElMessage.success('MCP 服务器配置已更新')
      return result
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '更新服务器配置失败')
      throw error
    }
  }

  async function deleteServer(serverId: string) {
    try {
      await mcpApi.deleteServer(serverId)
      await fetchServers()
      ElMessage.success('MCP 服务器配置已删除')
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '删除服务器配置失败')
      throw error
    }
  }

  async function testServer(serverId: string) {
    try {
      const result = await mcpApi.testServer(serverId)
      if (result.success) {
        ElMessage.success(`连接成功，延迟 ${result.latency_ms}ms`)
      } else {
        ElMessage.error(result.message || '连接失败')
      }
      return result
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '测试连接失败')
      throw error
    }
  }

  async function getServerTools(serverId: string) {
    try {
      const result = await mcpApi.getServerTools(serverId)
      return result.tools || []
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '获取工具列表失败')
      throw error
    }
  }

  // =========================================================================
  // 智能体配置操作
  // =========================================================================

  async function fetchAgentConfig() {
    configLoading.value = true
    try {
      agentConfig.value = await agentConfigApi.getAgentConfig()
    } catch (error: any) {
      ElMessage.error('获取智能体配置失败')
      throw error
    } finally {
      configLoading.value = false
    }
  }

  async function updateAgentConfig(data: UserAgentConfigUpdate) {
    try {
      const result = await agentConfigApi.updateConfig(data)
      agentConfig.value = result
      ElMessage.success('智能体配置已更新')
      return result
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '更新配置失败')
      throw error
    }
  }

  async function resetAgentConfig() {
    try {
      const result = await agentConfigApi.resetConfig()
      agentConfig.value = result
      ElMessage.success('已重置为公共配置')
      return result
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '重置配置失败')
      throw error
    }
  }

  async function fetchPublicConfig() {
    configLoading.value = true
    try {
      publicConfig.value = await agentConfigApi.getPublicConfig()
    } catch (error: any) {
      ElMessage.error('获取公共配置失败')
      throw error
    } finally {
      configLoading.value = false
    }
  }

  async function updatePublicConfig(data: UserAgentConfigUpdate) {
    try {
      const result = await agentConfigApi.updatePublicConfig(data)
      publicConfig.value = result
      ElMessage.success('公共配置已更新')
      return result
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '更新公共配置失败')
      throw error
    }
  }

  async function restorePublicConfig() {
    try {
      const result = await agentConfigApi.restorePublicConfig()
      publicConfig.value = result.config
      ElMessage.success('公共配置已恢复为默认值')
      return result
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '恢复默认配置失败')
      throw error
    }
  }

  async function exportAgentConfig() {
    try {
      const result = await agentConfigApi.exportConfig()
      return result.config
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '导出配置失败')
      throw error
    }
  }

  async function importAgentConfig(configData: Record<string, unknown>) {
    try {
      const result = await agentConfigApi.importConfig(configData)
      agentConfig.value = result
      ElMessage.success('配置已导入')
      return result
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '导入配置失败')
      throw error
    }
  }

  // =========================================================================
  // 任务操作
  // =========================================================================

  async function fetchTasks(params?: {
    status?: string
    stock_code?: string
    recommendation?: string
    risk_level?: string
    limit?: number
    offset?: number
  }) {
    tasksLoading.value = true
    try {
      const result = await taskApi.listTasks(params)
      tasks.value = result.tasks || []
      tasksTotal.value = result.total || 0
    } catch (error: any) {
      ElMessage.error('获取任务列表失败')
      throw error
    } finally {
      tasksLoading.value = false
    }
  }

  async function createTasks(data: UnifiedTaskCreate) {
    try {
      const result = await taskApi.createTasks(data)
      // 单股返回 task_id，批量返回 batch_id
      const id = result.task_id || result.batch_id
      if (id) {
        ElMessage.success(result.message || '任务已创建')
      }
      return { id, result }
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '创建任务失败')
      throw error
    }
  }

  async function cancelTask(taskId: string) {
    try {
      await taskApi.cancelTask(taskId)
      await fetchTasks()
      ElMessage.success('任务已取消')
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '取消任务失败')
      throw error
    }
  }

  async function deleteTask(taskId: string) {
    try {
      await taskApi.deleteTask(taskId)
      await fetchTasks()
      ElMessage.success('任务已删除')
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '删除任务失败')
      throw error
    }
  }

  async function retryTask(taskId: string) {
    try {
      const result = await taskApi.retryTask(taskId)
      await fetchTasks()
      ElMessage.success('任务已重新提交')
      return result.id  // 从 AnalysisTaskResponse 提取 id
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '重试任务失败')
      throw error
    }
  }

  // =========================================================================
  // 报告操作
  // =========================================================================

  async function fetchReports(params?: {
    stock_code?: string
    recommendation?: string
    risk_level?: string
    limit?: number
    offset?: number
  }) {
    reportsLoading.value = true
    try {
      const result = await reportApi.listReports(params)
      reports.value = result.reports || []
    } catch (error: any) {
      ElMessage.error('获取报告列表失败')
      throw error
    } finally {
      reportsLoading.value = false
    }
  }

  async function fetchReportSummary(days: number = 30) {
    try {
      reportSummary.value = await reportApi.getReportSummary(days)
    } catch (error: any) {
      ElMessage.error('获取报告统计失败')
      throw error
    }
  }

  async function deleteReport(reportId: string) {
    try {
      await reportApi.deleteReport(reportId)
      await fetchReports()
      ElMessage.success('报告已删除')
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '删除报告失败')
      throw error
    }
  }

  return {
    // 状态
    systemModels,
    userModels,
    modelsLoading,
    systemServers,
    userServers,
    serversLoading,
    agentConfig,
    publicConfig,
    configLoading,
    tasks,
    tasksTotal,
    tasksLoading,
    reports,
    reportSummary,
    reportsLoading,

    // 计算属性
    allModels,
    allServers,
    enabledModels,
    enabledServers,

    // AI 模型操作
    fetchModels,
    createModel,
    updateModel,
    deleteModel,
    testModel,
    testModelConnection,

    // MCP 服务器操作
    fetchServers,
    createServer,
    updateServer,
    deleteServer,
    testServer,
    getServerTools,

    // 智能体配置操作
    fetchAgentConfig,
    updateAgentConfig,
    resetAgentConfig,
    fetchPublicConfig,
    updatePublicConfig,
    exportAgentConfig,
    importAgentConfig,

    // 任务操作
    fetchTasks,
    createTasks,
    cancelTask,
    deleteTask,
    retryTask,

    // 报告操作
    fetchReports,
    fetchReportSummary,
    deleteReport,
  }
})
