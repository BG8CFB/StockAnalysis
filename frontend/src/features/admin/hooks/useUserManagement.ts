/**
 * 用户管理数据 Hook
 * 封装用户列表、审批、操作等逻辑
 */

import { useState, useCallback, useRef } from 'react'
import { message } from 'antd'
import {
  getUsers,
  getPendingUsers,
  approveUser,
  rejectUser,
  disableUser,
  enableUser,
  deleteUser,
  changeUserRole,
  resetUserPassword,
  createUser,
  updateUser,
  getAuditLogs,
  type UserListFilters,
  type CreateUserInput,
  type UpdateUserInput,
} from '@/services/api/admin'
import type { AdminUser, AuditLogItem } from '@/types/admin.types'
import type { PaginatedResponse } from '@/types/common.types'

export interface UseUserManagementReturn {
  users: AdminUser[]
  pendingUsers: AdminUser[]
  auditLogs: AuditLogItem[]
  auditTotal: number
  loading: boolean
  actionLoading: Record<string, boolean>
  total: number
  page: number
  pageSize: number
  fetchUsers: (filters?: UserListFilters) => Promise<void>
  fetchPendingUsers: () => Promise<void>
  fetchAuditLogs: (params?: { page?: number; page_size?: number; user_id?: string }) => Promise<void>
  approve: (userId: string) => Promise<void>
  reject: (userId: string) => Promise<void>
  disable: (userId: string) => Promise<void>
  enable: (userId: string) => Promise<void>
  remove: (userId: string) => Promise<void>
  changeRole: (userId: string, role: string) => Promise<void>
  resetPassword: (userId: string, newPassword: string) => Promise<void>
  create: (data: CreateUserInput) => Promise<boolean>
  update: (userId: string, data: UpdateUserInput) => Promise<boolean>
}

export function useUserManagement(): UseUserManagementReturn {
  const [users, setUsers] = useState<AdminUser[]>([])
  const [pendingUsers, setPendingUsers] = useState<AdminUser[]>([])
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([])
  const [auditTotal, setAuditTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({})
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)

  const fetchingRef = useRef(false)

  const fetchUsers = useCallback(async (filters?: UserListFilters) => {
    if (fetchingRef.current) return
    fetchingRef.current = true
    setLoading(true)
    try {
      const p = filters?.page ?? page
      const ps = filters?.page_size ?? pageSize
      const res = await getUsers({ page: p, page_size: ps, ...filters })
      const data = res.data as PaginatedResponse<AdminUser> | undefined
      setUsers(data?.items ?? [])
      setTotal(data?.total ?? 0)
      setPage(p)
      if (filters?.page_size) setPageSize(filters.page_size)
    } catch {
      message.error('加载用户列表失败')
      setUsers([])
      setTotal(0)
    } finally {
      setLoading(false)
      fetchingRef.current = false
    }
  }, [page, pageSize])

  const fetchPendingUsers = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getPendingUsers()
      const data = res.data as AdminUser[] | undefined
      setPendingUsers(data ?? [])
    } catch {
      message.error('加载待审批用户失败')
      setPendingUsers([])
    } finally {
      setLoading(false)
    }
  }, [])

  const fetchAuditLogs = useCallback(async (params?: { page?: number; page_size?: number; user_id?: string }) => {
    setLoading(true)
    try {
      const res = await getAuditLogs(params)
      const data = res.data as PaginatedResponse<AuditLogItem> | undefined
      setAuditLogs(data?.items ?? [])
      setAuditTotal(data?.total ?? 0)
    } catch {
      message.error('加载审计日志失败')
      setAuditLogs([])
      setAuditTotal(0)
    } finally {
      setLoading(false)
    }
  }, [])

  const withActionLoading = async <T, >(userId: string, fn: () => Promise<T>): Promise<T> => {
    setActionLoading(prev => ({ ...prev, [userId]: true }))
    try {
      return await fn()
    } finally {
      setActionLoading(prev => ({ ...prev, [userId]: false }))
    }
  }

  const approve = useCallback(async (userId: string) => {
    await withActionLoading(userId, async () => {
      await approveUser(userId)
      message.success('用户已审批通过')
      await fetchUsers()
      await fetchPendingUsers()
    })
  }, [fetchUsers, fetchPendingUsers])

  const reject = useCallback(async (userId: string) => {
    await withActionLoading(userId, async () => {
      await rejectUser(userId)
      message.success('用户已拒绝')
      await fetchUsers()
      await fetchPendingUsers()
    })
  }, [fetchUsers, fetchPendingUsers])

  const disable = useCallback(async (userId: string) => {
    await withActionLoading(userId, async () => {
      await disableUser(userId)
      message.success('用户已禁用')
      await fetchUsers()
    })
  }, [fetchUsers])

  const enable = useCallback(async (userId: string) => {
    await withActionLoading(userId, async () => {
      await enableUser(userId)
      message.success('用户已启用')
      await fetchUsers()
    })
  }, [fetchUsers])

  const remove = useCallback(async (userId: string) => {
    await withActionLoading(userId, async () => {
      await deleteUser(userId)
      message.success('用户已删除')
      await fetchUsers()
    })
  }, [fetchUsers])

  const changeRole = useCallback(async (userId: string, role: string) => {
    await withActionLoading(userId, async () => {
      await changeUserRole(userId, { role })
      message.success('角色已更新')
      await fetchUsers()
    })
  }, [fetchUsers])

  const resetPassword = useCallback(async (userId: string, newPassword: string) => {
    await withActionLoading(userId, async () => {
      await resetUserPassword(userId, { new_password: newPassword })
      message.success('密码已重置')
    })
  }, [])

  const create = useCallback(async (data: CreateUserInput): Promise<boolean> => {
    setLoading(true)
    try {
      await createUser(data)
      message.success('用户创建成功')
      await fetchUsers()
      return true
    } catch {
      message.error('创建用户失败')
      return false
    } finally {
      setLoading(false)
    }
  }, [fetchUsers])

  const update = useCallback(async (userId: string, data: UpdateUserInput): Promise<boolean> => {
    setLoading(true)
    try {
      await updateUser(userId, data)
      message.success('用户信息已更新')
      await fetchUsers()
      return true
    } catch {
      message.error('更新用户失败')
      return false
    } finally {
      setLoading(false)
    }
  }, [fetchUsers])

  return {
    users,
    pendingUsers,
    auditLogs,
    auditTotal,
    loading,
    actionLoading,
    total,
    page,
    pageSize,
    fetchUsers,
    fetchPendingUsers,
    fetchAuditLogs,
    approve,
    reject,
    disable,
    enable,
    remove,
    changeRole,
    resetPassword,
    create,
    update,
  }
}
