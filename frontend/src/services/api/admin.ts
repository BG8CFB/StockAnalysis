/**
 * 管理员用户管理 API
 * 对应后端 /api/admin/users/* 端点
 */

import apiClient from '../http/client'
import type { ApiResponse, PaginatedResponse } from '@/types/common.types'
import type { AdminUser, AuditLogItem } from '@/types/admin.types'

export interface UserListFilters {
  page?: number
  page_size?: number
  keyword?: string
  role?: string
  status?: string
  [key: string]: unknown
}

export interface CreateUserInput {
  username: string
  email: string
  password: string
  role?: string
}

export interface UpdateUserInput {
  username?: string
  email?: string
  is_active?: boolean
}

export interface ChangeRoleInput {
  role: string
}

/** 获取用户列表 */
export async function getUsers(filters?: UserListFilters): Promise<ApiResponse<PaginatedResponse<AdminUser>>> {
  const params: Record<string, unknown> = {}
  if (filters) {
    if (filters.page !== undefined && filters.page_size !== undefined) {
      params.skip = (filters.page - 1) * filters.page_size
      params.limit = filters.page_size
    }
    if (filters.keyword) params.search = filters.keyword
    if (filters.role) params.role = filters.role
    if (filters.status) params.status = filters.status
  }
  return apiClient.get<PaginatedResponse<AdminUser>>('/api/admin/users', params)
}

/** 获取待审批用户列表 */
export async function getPendingUsers(): Promise<ApiResponse<AdminUser[]>> {
  return apiClient.get<AdminUser[]>('/api/admin/users/pending')
}

/** 获取用户详情 */
export async function getUserDetail(userId: string): Promise<ApiResponse<AdminUser>> {
  return apiClient.get<AdminUser>(`/api/admin/users/${userId}`)
}

/** 创建用户 */
export async function createUser(data: CreateUserInput): Promise<ApiResponse<AdminUser>> {
  return apiClient.post<AdminUser>('/api/admin/users', data)
}

/** 审批用户 */
export async function approveUser(userId: string): Promise<ApiResponse<AdminUser>> {
  return apiClient.put<AdminUser>(`/api/admin/users/${userId}/approve`, {})
}

/** 拒绝用户 */
export async function rejectUser(userId: string, reason: string): Promise<ApiResponse<AdminUser>> {
  return apiClient.put<AdminUser>(`/api/admin/users/${userId}/reject`, { reason })
}

/** 禁用用户 */
export async function disableUser(userId: string, reason?: string): Promise<ApiResponse<AdminUser>> {
  return apiClient.put<AdminUser>(`/api/admin/users/${userId}/disable`, reason ? { reason } : {})
}

/** 启用用户 */
export async function enableUser(userId: string): Promise<ApiResponse<AdminUser>> {
  return apiClient.put<AdminUser>(`/api/admin/users/${userId}/enable`)
}

/** 更新用户 */
export async function updateUser(userId: string, data: UpdateUserInput): Promise<ApiResponse<AdminUser>> {
  return apiClient.put<AdminUser>(`/api/admin/users/${userId}`, data)
}

/** 修改用户角色 */
export async function changeUserRole(userId: string, data: ChangeRoleInput): Promise<ApiResponse<AdminUser>> {
  return apiClient.put<AdminUser>(`/api/admin/users/${userId}/role?new_role=${encodeURIComponent(data.role)}`)
}

/** 删除用户 */
export async function deleteUser(userId: string): Promise<ApiResponse<Record<string, never>>> {
  return apiClient.delete<Record<string, never>>(`/api/admin/users/${userId}`)
}

/** 重置用户密码（触发重置流程，生成重置 token） */
export async function resetUserPassword(userId: string): Promise<ApiResponse<{ token?: string | null }>> {
  return apiClient.post<{ token?: string | null }>(`/api/admin/users/${userId}/reset-password`)
}

/** 获取审计日志 */
export async function getAuditLogs(params?: { page?: number; page_size?: number; user_id?: string }): Promise<ApiResponse<PaginatedResponse<AuditLogItem>>> {
  const query: Record<string, unknown> = {}
  if (params) {
    if (params.page !== undefined && params.page_size !== undefined) {
      query.skip = (params.page - 1) * params.page_size
      query.limit = params.page_size
    }
    if (params.user_id) query.user_id = params.user_id
  }
  return apiClient.get<PaginatedResponse<AuditLogItem>>('/api/admin/audit-logs', query)
}
