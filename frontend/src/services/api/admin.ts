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

export interface ResetPasswordInput {
  new_password: string
}

/** 获取用户列表 */
export async function getUsers(filters?: UserListFilters): Promise<ApiResponse<PaginatedResponse<AdminUser>>> {
  return apiClient.get<PaginatedResponse<AdminUser>>('/api/admin/users', (filters ?? {}) as Record<string, unknown>)
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
  return apiClient.put<AdminUser>(`/api/admin/users/${userId}/approve`)
}

/** 拒绝用户 */
export async function rejectUser(userId: string): Promise<ApiResponse<AdminUser>> {
  return apiClient.put<AdminUser>(`/api/admin/users/${userId}/reject`)
}

/** 禁用用户 */
export async function disableUser(userId: string): Promise<ApiResponse<AdminUser>> {
  return apiClient.put<AdminUser>(`/api/admin/users/${userId}/disable`)
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
  return apiClient.put<AdminUser>(`/api/admin/users/${userId}/role`, data)
}

/** 删除用户 */
export async function deleteUser(userId: string): Promise<ApiResponse<Record<string, never>>> {
  return apiClient.delete<Record<string, never>>(`/api/admin/users/${userId}`)
}

/** 重置用户密码 */
export async function resetUserPassword(userId: string, data: ResetPasswordInput): Promise<ApiResponse<Record<string, never>>> {
  return apiClient.post<Record<string, never>>(`/api/admin/users/${userId}/reset-password`, data)
}

/** 获取审计日志 */
export async function getAuditLogs(params?: { page?: number; page_size?: number; user_id?: string }): Promise<ApiResponse<PaginatedResponse<AuditLogItem>>> {
  return apiClient.get<PaginatedResponse<AuditLogItem>>('/api/admin/audit-logs', params ?? {})
}
