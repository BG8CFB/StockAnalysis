/**
 * 系统设置类型定义
 */

/** 系统配置 */
export interface SystemConfig {
  /** 是否需要管理员审核新注册用户 */
  require_approval: boolean
  /** 系统名称 */
  app_name: string
  /** 系统版本 */
  app_version: string
  /** 是否为调试模式 */
  debug: boolean
  /** 注册是否开放 */
  registration_open: boolean
}

/** 系统状态 */
export interface SystemStatus {
  /** 是否已初始化 */
  initialized: boolean
  /** 数据库连接状态 */
  mongodb_connected: boolean
  /** Redis 连接状态 */
  redis_connected: boolean
  /** 用户统计 */
  user_stats: {
    total: number
    active: number
    pending: number
    disabled: number
  }
}

/** 系统信息 */
export interface SystemInfo extends SystemStatus, SystemConfig {
  /** 当前时间 */
  server_time: string
  /** 运行时长（秒） */
  uptime: number
}
