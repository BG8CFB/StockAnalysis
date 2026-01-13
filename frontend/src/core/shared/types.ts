/**
 * 核心共享类型定义
 * 统一管理所有模块共享的类型，避免重复定义
 */

// ==================== 用户基础类型 ====================

/** 用户角色 */
export type UserRole = 'GUEST' | 'USER' | 'ADMIN' | 'SUPER_ADMIN'

/** 用户状态 */
export type UserStatus = 'pending' | 'active' | 'disabled' | 'rejected'

// ==================== 认证相关类型 ====================

/** 登录请求 - 支持用户名或邮箱 */
export interface LoginRequest {
  account: string  // 用户名或邮箱
  password: string
}

/** 注册请求 */
export interface RegisterRequest {
  email: string
  username: string
  password: string
  confirm_password: string
}

/** Token 响应 */
export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

/** 刷新 Token 请求 */
export interface RefreshTokenRequest {
  refresh_token: string
}

// ==================== 用户信息类型 ====================

/** 用户信息（当前登录用户） */
export interface UserInfo {
  id: string
  email: string
  username: string
  role: UserRole
  is_active: boolean
  is_verified: boolean
  created_at: string
  last_login_at: string | null
  avatar?: string
}

/** 完整用户信息（包含管理字段） */
export interface User extends UserInfo {
  status: UserStatus
  reviewed_by?: string
  reviewed_at?: string
}

/** 用户列表项（使用 User 即可，此类型保留作为别名） */
export type UserListItem = User

/** 用户配置 */
export interface UserPreferences {
  theme: string
  language: string
  timezone: string
  notification_enabled: boolean
  email_alerts: boolean
}

/** 更新用户配置请求 */
export interface UpdatePreferencesRequest {
  theme?: string
  language?: string
  timezone?: string
  notification_enabled?: boolean
  email_alerts?: boolean
}

// ==================== 用户查询类型 ====================

/** 用户列表查询参数 */
export interface UserListQuery {
  skip?: number
  limit?: number
  role?: UserRole
  status?: UserStatus
  is_active?: boolean
  search?: string
}

/** 用户列表响应 */
export interface UserListResponse {
  users: User[]
  total: number
}

// ==================== 系统相关类型 ====================

/** 系统配置（后端 GET /settings/system 返回） */
export interface SystemConfig {
  require_approval: boolean
  password_min_length: number
  enable_registration: boolean
  enable_password_reset: boolean
  session_timeout: number
  rejected_user_retention_days: number
}

/** 系统状态（后端 GET /system/status 返回） */
export interface SystemStatus {
  initialized: boolean
  has_admin: boolean
  version: string
  status: string
  debug?: boolean
  mongodb_connected?: boolean
  redis_connected?: boolean
  user_stats?: {
    total: number
    active: number
    pending: number
    disabled: number
  }
}

/** 系统信息（后端 GET /system/info 返回，包含完整系统信息） */
export interface SystemInfo {
  // 状态字段
  initialized: boolean
  mongodb_connected: boolean
  redis_connected: boolean
  // 用户统计
  user_stats: {
    total: number
    active: number
    pending: number
    disabled: number
  }
  // 系统配置（小写字段名，与 SystemConfig 不同）
  require_approval: boolean
  app_name: string
  app_version: string
  debug: boolean
  registration_open: boolean
  // 时间信息
  server_time: string
  uptime: number
  // 完整配置（可选）
  config?: SystemConfig
}

/** 系统初始化请求 */
export interface SystemInitializeRequest {
  email: string
  username: string
  password: string
  confirm_password: string
}

/** 系统初始化响应 */
export interface SystemInitializeResponse {
  success: boolean
  message: string
  user: {
    id: string
    email: string
    username: string
    role: string
  }
  access_token: string
  refresh_token: string
  token_type: string
}

// ==================== 管理员相关类型 ====================

/** 审核相关请求 */
export interface ApproveUserRequest {
  // 无额外字段
}

export interface RejectUserRequest {
  reason: string
}

export interface DisableUserRequest {
  reason?: string
}

/** 审计日志 */
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

// ==================== 分页类型 ====================

/** 分页响应 */
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}
