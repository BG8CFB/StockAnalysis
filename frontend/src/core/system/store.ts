/**
 * 系统状态管理
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'
import { systemApi } from './api'
import type { SystemStatus } from '@core/shared/types'

export const useSystemStore = defineStore('system', () => {
  // 状态
  const initialized = ref(false)
  const hasAdmin = ref(false)
  const version = ref('')
  const loading = ref(false)

  // 方法
  async function checkStatus() {
    loading.value = true
    try {
      const status = await systemApi.getStatus()
      initialized.value = status.initialized
      hasAdmin.value = status.has_admin
      version.value = status.version
      return status
    } catch (error) {
      console.error('Failed to check system status:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  async function initialize(data: { email: string; username: string; password: string; confirm_password: string }) {
    loading.value = true
    try {
      const response = await systemApi.initialize(data)
      initialized.value = true
      hasAdmin.value = true
      return response
    } catch (error) {
      console.error('Failed to initialize system:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  return {
    // 状态
    initialized,
    hasAdmin,
    version,
    loading,
    // 方法
    checkStatus,
    initialize,
  }
})
