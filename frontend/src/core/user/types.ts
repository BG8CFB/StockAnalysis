/**
 * 用户核心类型定义
 */

// 用户状态
export type UserStatus = 'pending' | 'active' | 'disabled' | 'rejected'

// 用户角色
export type UserRole = 'GUEST' | 'USER' | 'ADMIN' | 'SUPER_ADMIN'

// 用户信息
export interface User {
  id: string
  email: string
  username: string
  role: UserRole
  status: UserStatus
  is_active: boolean
  is_verified: boolean
  created_at: string
  last_login_at?: string
  reviewed_by?: string
  reviewed_at?: string
}

// 用户列表项
export interface UserListItem {
  id: string
  email: string
  username: string
  role: UserRole
  status: UserStatus
  is_active: boolean
  is_verified: boolean
  created_at: string
  last_login_at?: string
  reviewed_by?: string
  reviewed_at?: string
}

// 审核相关
export interface ApproveUserRequest {
  // 无额外字段
}

export interface RejectUserRequest {
  reason: string
}

export interface DisableUserRequest {
  reason?: string
}

// 审计日志
export interface AuditLog {
  id: string
  user_id: string
  action: string
  target_user_id?: string
  reason?: string
  auditor_id: string
  auditor_name?: string
  ip_address?: string
  created_at: string
}

// 系统配置
export interface SystemConfig {
  REQUIRE_APPROVAL: boolean
  PASSWORD_MIN_LENGTH: number
  ENABLE_REGISTRATION: boolean
  ENABLE_PASSWORD_RESET: boolean
  SESSION_TIMEOUT: number
  REJECTED_USER_RETENTION_DAYS: number
}

// 分页响应
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

// 用户列表查询参数
export interface UserListParams {
  skip?: number
  limit?: number
  role?: UserRole
  status?: UserStatus
  is_active?: boolean
  search?: string
}
