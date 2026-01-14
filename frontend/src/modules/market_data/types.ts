/**
 * 市场数据模块类型定义
 * 严格按照 docs/market_data/数据源状态监控设计.md 实现
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
 * 数据源健康状态
 */
export enum DataSourceStatus {
  HEALTHY = 'healthy',
  DEGRADED = 'degraded',
  UNAVAILABLE = 'unavailable',
  STANDBY = 'standby'
}

/**
 * 数据源状态显示标签
 */
export const DataSourceStatusLabels: Record<DataSourceStatus, string> = {
  [DataSourceStatus.HEALTHY]: '✅ 正常',
  [DataSourceStatus.DEGRADED]: '⚠️ 已降级',
  [DataSourceStatus.UNAVAILABLE]: '❌ 不可用',
  [DataSourceStatus.STANDBY]: '💤 待机'
}

/**
 * 数据源状态标签类型（Element Plus）
 */
export const DataSourceStatusTagType: Record<DataSourceStatus, '' | 'success' | 'warning' | 'danger' | 'info'> = {
  [DataSourceStatus.HEALTHY]: 'success',
  [DataSourceStatus.DEGRADED]: 'warning',
  [DataSourceStatus.UNAVAILABLE]: 'danger',
  [DataSourceStatus.STANDBY]: 'info'
}

/**
 * 数据源显示名称
 */
export const DataSourceDisplayName: Record<string, string> = {
  tushare: 'TuShare',
  akshare: 'AkShare',
  yahoo: 'Yahoo Finance',
  alpha_vantage: 'Alpha Vantage'
}

/**
 * 下次更新说明映射
 */
export const NextUpdateMap: Record<string, string> = {
  daily_quote: '收盘后自动同步',
  realtime_quote: '实时更新',
  minute_quote: '盘中实时更新',
  financials: '季度更新',
  financial_indicator: '季度更新',
  company_info: '按需更新',
  news: '实时更新',
  calendar: '每日更新',
  top_list: '每日收盘后',
  moneyflow: '盘中实时更新',
  dividend: '按公告更新',
  shareholder_num: '季度更新',
  top_shareholder: '季度更新',
  margin: '每日收盘后',
  macro_economy: '按发布周期',
  sector: '每日更新',
  index: '盘中实时更新',
  ipo: '按公告更新',
  pledge: '按公告更新',
  repurchase: '按公告更新',
  adj_factor: '每日收盘后'
}

// =============================================================================
// 响应类型（按文档 API 设计）
// =============================================================================

/**
 * 仪表板概览响应（文档 3.1.1）
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
  status: DataSourceStatus
  last_update: string
  last_update_relative: string
  reason?: string
}

/**
 * 市场详细状态响应（文档 3.1.2）
 */
export interface MarketDetail {
  market: MarketType
  market_name: string
  data_types: DataTypeStatus[]
}

/**
 * 数据类型状态项（文档 3.1.2）
 * 对应前端卡片的数据结构
 */
export interface DataTypeStatus {
  data_type: string
  data_type_name: string
  current_source: CurrentDataSource
  is_fallback: boolean
  can_retry: boolean
  primary_source?: PrimaryDataSource
  fallback_reason?: string
}

/**
 * 当前数据源信息
 */
export interface CurrentDataSource {
  source_type: string
  source_id: string
  source_name: string
  status: DataSourceStatus
  last_check: string | null
  last_check_relative: string
  response_time_ms: number | null
}

/**
 * 主数据源信息（降级时）
 */
export interface PrimaryDataSource {
  source_id: string
  status: DataSourceStatus
  can_retry: boolean
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
  status: DataSourceStatus
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
