/**
 * 系统设置状态管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { systemSettingsApi } from '../api/system'
import type { SystemConfig, SystemStatus, SystemInfo } from '../types/system'

export const useSystemSettingsStore = defineStore('systemSettings', () => {
  // 状态
  const systemConfig = ref<SystemConfig | null>(null)
  const systemStatus = ref<SystemStatus | null>(null)
  const systemInfo = ref<SystemInfo | null>(null)

  // 使用引用计数代替共享 boolean，防止并发操作互相覆盖 loading 状态
  const loadingCount = ref(0)
  const loading = computed(() => loadingCount.value > 0)

  function startLoading() { loadingCount.value++ }
  function stopLoading() { loadingCount.value = Math.max(0, loadingCount.value - 1) }

  /**
   * 获取系统状态
   */
  async function fetchSystemStatus() {
    startLoading()
    try {
      const status = await systemSettingsApi.getSystemStatus()
      systemStatus.value = status
      return status
    } catch (error: any) {
      console.error('获取系统状态失败:', error)
      throw error
    } finally {
      stopLoading()
    }
  }

  /**
   * 获取系统配置
   */
  async function fetchSystemConfig() {
    startLoading()
    try {
      const config = await systemSettingsApi.getSystemConfig()
      systemConfig.value = config
      return config
    } catch (error: any) {
      console.error('获取系统配置失败:', error)
      throw error
    } finally {
      stopLoading()
    }
  }

  /**
   * 更新系统配置
   */
  async function updateConfig(configUpdates: Partial<SystemConfig>) {
    startLoading()
    try {
      const response = await systemSettingsApi.updateSystemConfig(configUpdates)
      if (systemConfig.value) {
        Object.assign(systemConfig.value, response.config)
      }
      return response
    } catch (error: any) {
      console.error('更新系统配置失败:', error)
      throw error
    } finally {
      stopLoading()
    }
  }

  /**
   * 获取完整系统信息
   */
  async function fetchSystemInfo() {
    startLoading()
    try {
      const info = await systemSettingsApi.getSystemInfo()
      systemInfo.value = info
      return info
    } catch (error: any) {
      console.error('获取系统信息失败:', error)
      throw error
    } finally {
      stopLoading()
    }
  }

  return {
    systemConfig,
    systemStatus,
    systemInfo,
    loading,
    fetchSystemStatus,
    fetchSystemConfig,
    updateConfig,
    fetchSystemInfo,
  }
})
