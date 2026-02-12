/**
 * 系统状态管理
 *
 * 设计原则：
 * - 系统状态只在首次需要时检查（路由守卫中）
 * - checkStatus 返回 void，调用方只关心是否完成
 * - 状态存储在 store 的 ref 中
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

  /**
   * 检查系统状态
   *
   * 返回 Promise<void>，调用方只需等待完成
   * 状态存储在 store 的 ref 中（initialized, hasAdmin, version）
   */
  async function checkStatus(): Promise<void> {
    // 已检查且已初始化，跳过
    if (statusChecked.value && initialized.value) {
      return
    }

    loading.value = true
    try {
      const status: SystemStatus = await systemApi.getStatus()
      initialized.value = status.initialized
      hasAdmin.value = status.has_admin
      version.value = status.version
      statusChecked.value = true
    } catch (error) {
      console.error('Failed to check system status:', error)
      // API 请求失败时，假设已初始化（避免卡在初始化页面）
      initialized.value = true
      statusChecked.value = true
    } finally {
      loading.value = false
    }
  }

  /**
   * 初始化系统
   */
  async function initialize(data: {
    email: string
    username: string
    password: string
    confirm_password: string
  }) {
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
