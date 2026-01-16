/**
 * AI 模型管理 Pinia Store
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { modelApi } from '../api/ai-model'
import type {
  AIModelConfig,
  AIModelConfigCreate,
  AIModelConfigUpdate,
} from '../types/ai-model'

export const useAIModelStore = defineStore('aiModel', () => {
  // 状态
  const systemModels = ref<AIModelConfig[]>([])
  const userModels = ref<AIModelConfig[]>([])
  const modelsLoading = ref(false)

  // 计算属性
  const allModels = computed(() => [...systemModels.value, ...userModels.value])
  const enabledModels = computed(() => allModels.value.filter((m) => m.enabled))

  // 获取模型列表
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

  // 创建模型
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

  // 更新模型
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

  // 删除模型
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

  // 测试模型
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

  // 测试模型连接
  async function testModelConnection(data: {
    api_base_url: string
    api_key: string
    model_id: string
  }) {
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

  return {
    // 状态
    systemModels,
    userModels,
    modelsLoading,
    // 计算属性
    allModels,
    enabledModels,
    // 操作
    fetchModels,
    createModel,
    updateModel,
    deleteModel,
    testModel,
    testModelConnection,
  }
})
