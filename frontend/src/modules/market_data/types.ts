/**
 * 市场数据模块类型定义
 * 修改后：主备数据源分离显示，移除待机状态
 */

/**
 * 市场类型枚举
 */
export enum MarketType {
  A_STOCK = 'A_STOCK',
  US_STOCK = 'US_STOCK',
  HK_STOCK = 'HK_STOCK'
}

/**
 * 市场类型名称映射
 */
export const MarketTypeName: Record<MarketType, string> = {
  [MarketType.A_STOCK]: 'A股',
  [MarketType.US_STOCK]: '美股',
  [MarketType.HK_STOCK]: '港股'
}

/**
 * 数据源健康状态（移除 STANDBY）
 */
export enum DataSourceStatus {
  HEALTHY = 'healthy',
  DEGRADED = 'degraded',
  UNAVAILABLE = 'unavailable'
}

/**
 * 数据源状态显示标签
 */
export const DataSourceStatusLabels: Record<DataSourceStatus, string> = {
  [DataSourceStatus.HEALTHY]: '正常',
  [DataSourceStatus.DEGRADED]: '已降级',
  [DataSourceStatus.UNAVAILABLE]: '不可用'
}

/**
 * 数据源状态标签类型（Element Plus）
 */
export const DataSourceStatusTagType: Record<DataSourceStatus, '' | 'success' | 'warning' | 'danger'> = {
  [DataSourceStatus.HEALTHY]: 'success',
  [DataSourceStatus.DEGRADED]: 'warning',
  [DataSourceStatus.UNAVAILABLE]: 'danger'
}

/**
 * 数据源显示名称
 */
export const DataSourceDisplayName: Record<string, string> = {
  tushare: 'TuShare',
  tu: 'TuShare',
  akshare: 'AkShare',
  yahoo: 'Yahoo Finance',
  alpha_vantage: 'Alpha Vantage',
  alphavantage: 'Alpha Vantage',
  // 备用数据源名称映射（处理未知或旧数据）
  unknown: '未知数据源',
  system: '系统数据源'
}

/**
 * 下次更新说明映射
 */
export const NextUpdateMap: Record<string, string> = {
  stock_list: '每日更新',
  daily_quotes: '收盘后自动同步',
  minute_quotes: '盘中实时更新',
  financials: '季度更新',
  company_info: '按需更新',
  index: '盘中实时更新',
  sector: '每日更新',
  macro_economy: '按发布周期',
}

// =============================================================================
// 响应类型（修改后：主备数据源分离显示）
// =============================================================================

/**
 * 仪表板概览响应
 */
export interface DashboardOverview {
  a_stock?: MarketStatusSummary
  us_stock?: MarketStatusSummary
  hk_stock?: MarketStatusSummary
}

/**
 * 市场状态汇总
 */
export interface MarketStatusSummary {
  status: string
  last_update: string
  last_update_relative: string
}

/**
 * 市场详细状态响应（修改后）
 */
export interface MarketDetail {
  market: MarketType
  market_name: string
  data_types: DataTypeStatus[]
}

/**
 * 数据源信息（修改后）
 */
export interface DataSourceInfo {
  source_id: string
  source_name: string
  is_current: boolean  // 是否是当前使用的数据源
  is_primary: boolean  // 是否是主数据源
  status: DataSourceStatus | null  // null 表示未使用/未检查
  last_check: string | null
  last_check_relative: string | null
  response_time_ms: number | null
  failure_count: number
  error_message: string | null
}

/**
 * 数据类型状态项（修改后：主备数据源分离）
 */
export interface DataTypeStatus {
  data_type: string
  data_type_name: string
  primary_source: DataSourceInfo
  fallback_source?: DataSourceInfo
}

/**
 * 数据类型详细响应（文档 3.2.1）
 */
export interface DataTypeDetail {
  market: MarketType
  data_type: string
  data_type_name: string
  sources: SourceDetail[]
  recent_events: StatusEvent[]
}

/**
 * 数据源详细信息
 */
export interface SourceDetail {
  source_type: string
  source_id: string
  source_name: string
  status: DataSourceStatus | null  // null 表示未检查
  priority: number
  last_check: string | null
  response_time_ms: number | null
  avg_response_time_ms: number | null
  failure_count: number
  note: string | null
  api_endpoints: ApiEndpoint[]
}

/**
 * API 端点信息（文档 3.2.1）
 */
export interface ApiEndpoint {
  endpoint_name: string
  endpoint_name_cn: string
  status: DataSourceStatus
  last_check: string | null
  failure_count: number
}

/**
 * 状态事件
 */
export interface StatusEvent {
  timestamp: string
  event_type: string
  description: string
  from_status: string | null
  to_status: string | null
  from_source: string | null
  to_source: string | null
  source_id: string | null
}

/**
 * 错误详情响应
 */
export interface ErrorDetail {
  market: MarketType
  data_type: string
  source_id: string
  source_name: string
  error: {
    api_endpoint?: string
    status?: string
    error_code?: string
    error_message?: string
    error_type?: string
    raw_response?: any
    occurred_at?: string
    failure_count?: number
    retry_history?: RetryHistory[]
  }
  admin_debug_info?: {
    traceback?: string
    request_params?: any
    full_error?: any
  }
}

/**
 * 重试历史
 */
export interface RetryHistory {
  attempt: number
  timestamp: string
  error: string
}

/**
 * 手动重试响应（文档 3.4）
 */
export interface RetryResponse {
  success: boolean
  message: string
  result?: {
    status: DataSourceStatus
    response_time_ms: number
    recovered_at: string
    was_fallback: boolean
    previous_source: string
  }
  error?: {
    error_message?: string
    failure_count?: number
  }
}

/**
 * 历史记录响应（文档 3.5）
 */
export interface HistoryResponse {
  events: StatusEvent[]
}

/**
 * 刷新状态响应（文档 3.6）
 */
export interface RefreshStatusResponse {
  success: boolean
  message: string
  refreshed_at: string
}
