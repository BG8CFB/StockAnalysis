/**
 * 管理员状态管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { adminApi, type UserListItemResponse, type UserListQuery } from './api'
import type { AuditLog } from '@core/shared/types'

export const useAdminStore = defineStore('admin', () => {
  // 状态
  const users = ref<UserListItemResponse[]>([])
  const total = ref(0)
  const loading = ref(false)
  const auditLogs = ref<AuditLog[]>([])

  // 待审核用户数量
  const pendingCount = computed(() => {
    return users.value.filter(u => u.status === 'pending').length
  })

  // 获取用户列表
  async function fetchUsers(query: UserListQuery) {
    loading.value = true
    try {
      const response = await adminApi.getUsers(query)
      users.value = response.users
      total.value = response.total
    } catch (error: any) {
      console.error('获取用户列表失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  // 获取待审核用户
  async function fetchPendingUsers(skip = 0, limit = 20) {
    loading.value = true
    try {
      const response = await adminApi.getPendingUsers(skip, limit)
      return response
    } catch (error: any) {
      console.error('获取待审核用户失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  // 通过用户审核
  async function approveUser(userId: string) {
    try {
      await adminApi.approveUser(userId)
      // 更新本地状态
      const index = users.value.findIndex(u => u.id === userId)
      if (index !== -1) {
        users.value[index].status = 'active'
      }
    } catch (error: any) {
      console.error('审核通过失败:', error)
      throw error
    }
  }

  // 拒绝用户审核
  async function rejectUser(userId: string, reason: string) {
    try {
      await adminApi.rejectUser(userId, reason)
      // 更新本地状态
      const index = users.value.findIndex(u => u.id === userId)
      if (index !== -1) {
        users.value[index].status = 'rejected'
      }
    } catch (error: any) {
      console.error('拒绝用户失败:', error)
      throw error
    }
  }

  // 禁用用户
  async function disableUser(userId: string, reason?: string) {
    try {
      await adminApi.disableUser(userId, reason)
      // 更新本地状态
      const index = users.value.findIndex(u => u.id === userId)
      if (index !== -1) {
        users.value[index].status = 'disabled'
        users.value[index].is_active = false
      }
    } catch (error: any) {
      console.error('禁用用户失败:', error)
      throw error
    }
  }

  // 启用用户
  async function enableUser(userId: string) {
    try {
      await adminApi.enableUser(userId)
      // 更新本地状态
      const index = users.value.findIndex(u => u.id === userId)
      if (index !== -1) {
        users.value[index].status = 'active'
        users.value[index].is_active = true
      }
    } catch (error: any) {
      console.error('启用用户失败:', error)
      throw error
    }
  }

  // 修改用户角色
  async function changeUserRole(userId: string, newRole: string) {
    try {
      await adminApi.changeUserRole(userId, newRole)
      // 更新本地状态
      const index = users.value.findIndex(u => u.id === userId)
      if (index !== -1) {
        users.value[index].role = newRole as any
      }
    } catch (error: any) {
      console.error('修改角色失败:', error)
      throw error
    }
  }

  // 删除用户
  async function deleteUser(userId: string) {
    try {
      await adminApi.deleteUser(userId)
      // 从本地状态移除
      const index = users.value.findIndex(u => u.id === userId)
      if (index !== -1) {
        users.value.splice(index, 1)
        total.value--
      }
    } catch (error: any) {
      console.error('删除用户失败:', error)
      throw error
    }
  }

  // 管理员触发密码重置
  async function adminResetPassword(userId: string) {
    try {
      const result = await adminApi.adminResetPassword(userId)
      return result
    } catch (error: any) {
      console.error('触发密码重置失败:', error)
      throw error
    }
  }

  // 获取审计日志
  async function fetchAuditLogs(params: {
    skip?: number
    limit?: number
    action?: string
    user_id?: string
  }) {
    try {
      const response = await adminApi.getAuditLogs(params)
      auditLogs.value = response.logs
      return response
    } catch (error: any) {
      console.error('获取审计日志失败:', error)
      throw error
    }
  }

  return {
    // 状态
    users,
    total,
    loading,
    auditLogs,
    // 计算属性
    pendingCount,
    // 方法
    fetchUsers,
    fetchPendingUsers,
    approveUser,
    rejectUser,
    disableUser,
    enableUser,
    changeUserRole,
    deleteUser,
    adminResetPassword,
    fetchAuditLogs,
  }
})
