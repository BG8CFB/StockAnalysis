/**
 * 用户配置管理 TypeScript 类型定义
 */

// =============================================================================
// 核心设置
// =============================================================================

export interface CoreSettings {
  theme: 'light' | 'dark' | 'auto'
  language: string
  timezone: string
  watchlist: string[]
}

export interface CoreSettingsUpdate {
  theme?: 'light' | 'dark' | 'auto'
  language?: string
  timezone?: string
  watchlist?: string[]
}

// =============================================================================
// 通知设置
// =============================================================================

export interface NotificationSettings {
  enabled: boolean
  email_alerts: boolean
  browser_notifications: boolean
  task_completed: boolean
  task_failed: boolean
  quota_warning: boolean
}

export interface NotificationSettingsUpdate {
  enabled?: boolean
  email_alerts?: boolean
  browser_notifications?: boolean
  task_completed?: boolean
  task_failed?: boolean
  quota_warning?: boolean
}

// =============================================================================
// TradingAgents 设置
// =============================================================================

export interface TradingAgentsSettings {
  data_collection_model_id: string
  debate_model_id: string
  default_debate_rounds: number
  max_debate_rounds: number
  phase_timeout_minutes: number
  agent_timeout_minutes: number
  tool_timeout_seconds: number
  task_expiry_hours: number
  archive_days: number
  enable_loop_detection: boolean
  enable_progress_events: boolean
}

export interface TradingAgentsSettingsUpdate {
  data_collection_model_id?: string
  debate_model_id?: string
  default_debate_rounds?: number
  max_debate_rounds?: number
  phase_timeout_minutes?: number
  agent_timeout_minutes?: number
  tool_timeout_seconds?: number
  task_expiry_hours?: number
  archive_days?: number
  enable_loop_detection?: boolean
  enable_progress_events?: boolean
}

// =============================================================================
// 配额信息
// =============================================================================

export interface UserQuotaInfo {
  tasks_used: number
  tasks_limit: number
  tasks_remaining: number
  tasks_usage_percent: number
  reports_count: number
  reports_limit: number
  storage_used_mb: number
  storage_limit_mb: number
  storage_usage_percent: number
  concurrent_tasks: number
  concurrent_limit: number
  is_near_quota_limit: boolean
}

// =============================================================================
// 统一用户配置
// =============================================================================

export interface UserSettingsResponse {
  id: string
  user_id: string
  core_settings: CoreSettings
  notification_settings: NotificationSettings
  trading_agents_settings: TradingAgentsSettings
  quota_info: UserQuotaInfo
  created_at: string
  updated_at: string
}

// =============================================================================
// 配置导入导出
// =============================================================================

export interface SettingsExport {
  version: string
  exported_at: string
  core_settings: CoreSettings
  notification_settings: NotificationSettings
  trading_agents_settings: TradingAgentsSettings
}

export interface SettingsImport {
  version: string
  core_settings?: CoreSettings
  notification_settings?: NotificationSettings
  trading_agents_settings?: TradingAgentsSettings
  merge_strategy: 'merge' | 'replace'
}
