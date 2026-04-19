import apiClient from '../http/client'
import type { ApiResponse, PaginatedResponse } from '@/types/common.types'

// ========== AI Models ==========

export interface AIModel {
  id: string
  name: string
  provider: string
  model_id: string
  description?: string
  max_tokens?: number
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CreateModelRequest {
  name: string
  provider: string
  model_id: string
  description?: string
  max_tokens?: number
}

/** 获取所有 AI 模型 */
export async function getModels(): Promise<ApiResponse<AIModel[]>> {
  return apiClient.get<AIModel[]>('/api/admin/trading-agents/models')
}

/** 创建系统模型 */
export async function createModel(data: CreateModelRequest): Promise<ApiResponse<AIModel>> {
  return apiClient.post<AIModel>('/api/admin/trading-agents/models', data)
}

/** 删除模型 */
export async function deleteModel(id: string): Promise<ApiResponse<Record<string, never>>> {
  return apiClient.delete<Record<string, never>>(`/api/admin/trading-agents/models/${id}`)
}

// ========== Tasks ==========

export interface Task {
  id: string
  user_id: string
  stock_code: string
  status: string
  progress: number
  created_at: string
  updated_at: string
  completed_at?: string
  error_message?: string
}

export interface TaskStats {
  total: number
  pending: number
  running: number
  completed: number
  failed: number
  cancelled: number
}

/** 获取所有任务 */
export async function getTasks(params?: { page?: number; page_size?: number; status?: string }): Promise<ApiResponse<PaginatedResponse<Task>>> {
  return apiClient.get<PaginatedResponse<Task>>('/api/admin/trading-agents/tasks', params ?? {})
}

/** 获取任务统计 */
export async function getTaskStats(): Promise<ApiResponse<TaskStats>> {
  return apiClient.get<TaskStats>('/api/admin/trading-agents/tasks/stats')
}

/** 删除任务 */
export async function deleteTask(id: string): Promise<ApiResponse<Record<string, never>>> {
  return apiClient.delete<Record<string, never>>(`/api/admin/trading-agents/tasks/${id}`)
}

// ========== Reports ==========

export interface Report {
  id: string
  task_id: string
  user_id: string
  stock_code: string
  title: string
  analysis_type: string
  created_at: string
  updated_at: string
}

export interface ReportStats {
  total: number
  by_type: Record<string, number>
  by_date: Record<string, number>
}

/** 获取所有报告 */
export async function getReports(params?: { page?: number; page_size?: number }): Promise<ApiResponse<PaginatedResponse<Report>>> {
  return apiClient.get<PaginatedResponse<Report>>('/api/admin/trading-agents/reports', params ?? {})
}

/** 获取报告统计 */
export async function getReportStats(): Promise<ApiResponse<ReportStats>> {
  return apiClient.get<ReportStats>('/api/admin/trading-agents/reports/stats')
}

// ========== Alerts ==========

export interface Alert {
  id: string
  level: 'info' | 'warning' | 'error' | 'critical'
  title: string
  message: string
  source: string
  resolved: boolean
  resolved_at?: string
  resolved_by?: string
  created_at: string
}

export interface AlertStats {
  total: number
  unresolved: number
  by_level: Record<string, number>
}

/** 获取所有告警 */
export async function getAlerts(params?: { resolved?: boolean; level?: string }): Promise<ApiResponse<Alert[]>> {
  return apiClient.get<Alert[]>('/api/admin/trading-agents/alerts', params ?? {})
}

/** 解决告警 */
export async function resolveAlert(id: string): Promise<ApiResponse<Alert>> {
  return apiClient.post<Alert>(`/api/admin/trading-agents/alerts/${id}/resolve`)
}

/** 获取告警统计 */
export async function getAlertStats(): Promise<ApiResponse<AlertStats>> {
  return apiClient.get<AlertStats>('/api/admin/trading-agents/alerts/stats')
}
