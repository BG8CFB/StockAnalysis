/**
 * 管理员核心类型定义
 * 从共享类型导入，避免重复定义
 */
export type {
  // 用户相关
  User,
  UserListQuery,
  UserListResponse,
  // 审核相关
  ApproveUserRequest,
  RejectUserRequest,
  DisableUserRequest,
  // 审计日志
  AuditLog,
} from '@core/shared/types'
