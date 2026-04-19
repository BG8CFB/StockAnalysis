/**
 * 管理员相关类型定义
 */

export type UserRole = 'GUEST' | 'USER' | 'ADMIN' | 'SUPER_ADMIN'
export type UserStatus = 'pending' | 'active' | 'disabled' | 'rejected'

export interface AdminUser {
  id: string
  username: string
  email: string
  role: UserRole
  status: UserStatus
  is_active: boolean
  is_verified: boolean
  created_at: string
  updated_at: string
  last_login_at?: string
  avatar?: string
}

export interface AuditLogItem {
  id: string
  user_id?: string
  username?: string
  action: string
  resource_type: string
  resource_id?: string
  details?: Record<string, unknown>
  ip_address?: string
  created_at: string
}

export interface DataSourceStatus {
  market: string
  market_label: string
  overall_status: 'healthy' | 'degraded' | 'unhealthy' | 'unknown'
  sources: DataSourceInfo[]
  last_updated: string
}

export interface DataSourceInfo {
  id: string
  name: string
  type: string
  status: 'healthy' | 'degraded' | 'unhealthy' | 'unknown'
  last_sync_at?: string
  next_sync_at?: string
  error_message?: string
  latency_ms?: number
}

export interface DataTypeDetail {
  market: string
  data_type: string
  sources: DataSourceInfo[]
  history: DataSourceHistoryItem[]
}

export interface DataSourceHistoryItem {
  timestamp: string
  status: 'healthy' | 'degraded' | 'unhealthy' | 'unknown'
  latency_ms?: number
  error_message?: string
}
