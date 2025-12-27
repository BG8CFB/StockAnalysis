/**
 * 用户核心类型定义
 * 从共享类型导入，避免重复定义
 */
export type {
  // 基础类型
  UserRole,
  UserStatus,
  // 用户信息
  User,
  UserInfo,
  UserListItem,
  UserPreferences,
  UpdatePreferencesRequest,
  // 用户查询
  UserListQuery,
  UserListResponse,
  // 系统相关
  SystemConfig,
  // 审核相关
  ApproveUserRequest,
  RejectUserRequest,
  DisableUserRequest,
  // 审计日志
  AuditLog,
  // 分页
  PaginatedResponse,
} from '@core/shared/types'
