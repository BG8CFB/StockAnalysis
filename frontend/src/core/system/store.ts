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
  const statusChecked = ref(false)

  // 方法
  async function checkStatus() {
    if (statusChecked.value && initialized.value) return { initialized: true, has_admin: hasAdmin.value, version: version.value }

    loading.value = true
    try {
      const status = await systemApi.getStatus()
      initialized.value = status.initialized
      hasAdmin.value = status.has_admin
      version.value = status.version
      statusChecked.value = true
      return status
    } catch (error) {
      console.error('Failed to check system status:', error)
      // API 请求失败时，假设已初始化（避免卡在初始化页面）
      initialized.value = true
      statusChecked.value = true
      return { initialized: true, has_admin: false, version: '' }
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
    statusChecked,
    // 方法
    checkStatus,
    initialize,
  }
})
