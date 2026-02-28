/**
 * TradingAgents 模块 Pinia Store
 *
 * 注意：AI 模型管理已移至核心设置模块 (@core/settings)
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import {
  mcpApi,
  agentConfigApi,
  taskApi,
} from './api'
import type {
  MCPServerConfig,
  MCPServerConfigCreate,
  MCPServerConfigUpdate,
  UserAgentConfig,
  UserAgentConfigUpdate,
  AnalysisTask,
  UnifiedTaskCreate,
} from './types'

export const useTradingAgentsStore = defineStore('tradingAgents', () => {
  // =========================================================================
  // 状态
  // =========================================================================

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

  // =========================================================================
  // 计算属性
  // =========================================================================

  const allServers = computed(() => [...systemServers.value, ...userServers.value])
  const enabledServers = computed(() => allServers.value.filter((s) => s.enabled))

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
    batch_id?: string  // 批量任务 ID 筛选
    start_date?: string  // 开始日期
    end_date?: string  // 结束日期
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
      return result.id
    } catch (error: any) {
      ElMessage.error(error.response?.data?.detail || '重试任务失败')
      throw error
    }
  }

  return {
    // 状态
    systemServers,
    userServers,
    serversLoading,
    agentConfig,
    publicConfig,
    configLoading,
    tasks,
    tasksTotal,
    tasksLoading,

    // 计算属性
    allServers,
    enabledServers,

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
  }
})
