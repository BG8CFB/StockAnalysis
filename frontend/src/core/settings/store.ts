/**
 * 系统设置状态管理
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { settingsApi } from '@core/settings'
import type { SystemConfig, SystemStatus, SystemInfo } from './types'

export const useSettingsStore = defineStore('settings', () => {
  // 状态
  const systemConfig = ref<SystemConfig | null>(null)
  const systemStatus = ref<SystemStatus | null>(null)
  const systemInfo = ref<SystemInfo | null>(null)
  const loading = ref(false)

  /**
   * 获取系统状态
   */
  async function fetchSystemStatus() {
    loading.value = true
    try {
      const status = await settingsApi.getSystemStatus()
      systemStatus.value = status
      return status
    } catch (error: any) {
      console.error('获取系统状态失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取系统配置
   */
  async function fetchSystemConfig() {
    loading.value = true
    try {
      const config = await settingsApi.getSystemConfig()
      systemConfig.value = config
      return config
    } catch (error: any) {
      console.error('获取系统配置失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * 更新系统配置
   */
  async function updateConfig(configUpdates: Partial<SystemConfig>) {
    loading.value = true
    try {
      const response = await settingsApi.updateSystemConfig(configUpdates)
      // 更新本地状态
      if (systemConfig.value) {
        Object.assign(systemConfig.value, response.config)
      }
      return response
    } catch (error: any) {
      console.error('更新系统配置失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取完整系统信息
   */
  async function fetchSystemInfo() {
    loading.value = true
    try {
      const info = await settingsApi.getSystemInfo()
      systemInfo.value = info
      systemConfig.value = {
        require_approval: info.require_approval,
        app_name: info.app_name,
        app_version: info.app_version,
        debug: info.debug,
        registration_open: info.registration_open,
      }
      systemStatus.value = {
        initialized: info.initialized,
        mongodb_connected: info.mongodb_connected,
        redis_connected: info.redis_connected,
        user_stats: info.user_stats,
      }
      return info
    } catch (error: any) {
      console.error('获取系统信息失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  return {
    // 状态
    systemConfig,
    systemStatus,
    systemInfo,
    loading,
    // 方法
    fetchSystemStatus,
    fetchSystemConfig,
    updateConfig,
    fetchSystemInfo,
  }
})
