/**
 * 管理员核心类型定义
 */
import type { User, UserStatus, UserRole } from '@core/user'

// 用户列表查询参数
export interface UserListQuery {
  skip?: number
  limit?: number
  role?: UserRole
  status?: UserStatus
  is_active?: boolean
  search?: string
}

// 用户列表响应
export interface UserListResponse {
  users: User[]
  total: number
}
