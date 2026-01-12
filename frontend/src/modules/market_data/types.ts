/**
 * 市场数据模块类型定义
 * 仅包含数据源监控相关类型
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
 * 市场类型标签映射
 */
export const MarketTypeLabels: Record<MarketType, string> = {
  [MarketType.A_STOCK]: 'A股',
  [MarketType.US_STOCK]: '美股',
  [MarketType.HK_STOCK]: '港股'
}

/**
 * 市场中文映射
 */
export const MarketTypeName: Record<MarketType, string> = {
  [MarketType.A_STOCK]: 'A股',
  [MarketType.US_STOCK]: '美股',
  [MarketType.HK_STOCK]: '港股'
}

/**
 * 数据源状态枚举
 */
export enum DataSourceStatus {
  HEALTHY = 'healthy',
  DEGRADED = 'degraded',
  UNAVAILABLE = 'unavailable',
  STANDBY = 'standby'
}

/**
 * 数据源状态标签映射
 */
export const DataSourceStatusLabels: Record<DataSourceStatus, string> = {
  [DataSourceStatus.HEALTHY]: '正常',
  [DataSourceStatus.DEGRADED]: '已降级',
  [DataSourceStatus.UNAVAILABLE]: '不可用',
  [DataSourceStatus.STANDBY]: '待机'
}

/**
 * 数据源状态标签类型映射
 */
export const DataSourceStatusTagType: Record<DataSourceStatus, any> = {
  [DataSourceStatus.HEALTHY]: 'success',
  [DataSourceStatus.DEGRADED]: 'warning',
  [DataSourceStatus.UNAVAILABLE]: 'danger',
  [DataSourceStatus.STANDBY]: 'info'
}

/**
 * 数据源状态图标映射
 */
export const DataSourceStatusIcon: Record<DataSourceStatus, string> = {
  [DataSourceStatus.HEALTHY]: '✅',
  [DataSourceStatus.DEGRADED]: '⚠️',
  [DataSourceStatus.UNAVAILABLE]: '❌',
  [DataSourceStatus.STANDBY]: '💤'
}

/**
 * 数据源显示名称映射
 */
export const DataSourceDisplayName: Record<string, string> = {
  'tushare': 'TuShare Pro',
  'akshare': 'AkShare',
  'yahoo_finance': 'Yahoo Finance',
  'alpha_vantage': 'Alpha Vantage',
  'itick': 'iTick'
}

/**
 * 数据源图标映射（返回 Element Plus 图标组件名称）
 */
export const DataSourceIconName: Record<string, string> = {
  'tushare': 'TrendCharts',
  'akshare': 'TrendCharts',
  'yahoo_finance': 'TrendCharts',
  'alpha_vantage': 'TrendCharts',
  'itick': 'TrendCharts'
}

/**
 * 仪表板概览数据
 */
export interface DashboardOverview {
  a_stock?: MarketStatusInfo
  us_stock?: MarketStatusInfo
  hk_stock?: MarketStatusInfo
}

/**
 * 市场状态信息
 */
export interface MarketStatusInfo {
  status: DataSourceStatus
  last_update: string
  last_update_relative: string
  reason?: string
}

/**
 * 数据源健康状态
 */
export interface DataSourceHealth {
  sourceName: string
  isAvailable: boolean
  responseTimeMs?: number
  lastCheckTime?: string
  failureCount: number
  error?: string
}

/**
 * 市场详细状态
 */
export interface MarketDetail {
  market: MarketType
  marketName: string
  dataTypes: DataTypeStatus[]
}

/**
 * 数据类型状态
 */
export interface DataTypeStatus {
  dataType: string
  dataTypeName: string
  currentSource: DataSourceInfo
  isFallback: boolean
  canRetry: boolean
  primarySource?: {
    sourceId: string
    status: string
    canRetry: boolean
  }
  fallbackReason?: string
}

/**
 * 数据源信息
 */
export interface DataSourceInfo {
  sourceType: 'system' | 'user'
  sourceId: string
  sourceName: string
  status: DataSourceStatus
  lastCheck: string
  lastCheckRelative: string
  responseTimeMs?: number
}

/**
 * 数据类型详细信息
 */
export interface DataTypeDetail {
  market: MarketType
  dataType: string
  dataTypeName: string
  sources: DataSourceDetailInfo[]
  recentEvents: StatusEvent[]
}

/**
 * 数据源详细信息
 */
export interface DataSourceDetailInfo {
  sourceType: 'system' | 'user'
  sourceId: string
  sourceName: string
  status: DataSourceStatus
  priority: number
  lastCheck?: string
  responseTimeMs?: number
  avgResponseTimeMs?: number
  failureCount: number
  note?: string
  apiEndpoints?: ApiEndpointInfo[]
}

/**
 * API 端点信息
 */
export interface ApiEndpointInfo {
  endpointName: string
  endpointNameCn: string
  status: DataSourceStatus
  lastCheck?: string
  failureCount: number
}

/**
 * 状态事件
 */
export interface StatusEvent {
  timestamp: string
  eventType: string
  description: string
  fromStatus?: string
  toStatus?: string
  fromSource?: string
  toSource?: string
  sourceId?: string
}

/**
 * 错误详情
 */
export interface ErrorDetail {
  market: MarketType
  dataType: string
  sourceId: string
  sourceName: string
  error: {
    apiEndpoint?: string
    status?: string
    errorCode?: string
    errorMessage?: string
    errorType?: string
    rawResponse?: any
    occurredAt?: string
    failureCount?: number
    retryHistory?: RetryHistory[]
  }
  adminDebugInfo?: {
    traceback?: string
    requestParams?: any
    fullError?: any
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
 * 重试响应
 */
export interface RetryResponse {
  success: boolean
  message: string
  result?: {
    status: string
    responseTimeMs: number
    recoveredAt: string
    wasFallback: boolean
    previousSource: string
  }
  error?: {
    errorCode?: string
    errorMessage?: string
    failureCount?: number
  }
}

/**
 * 历史记录响应
 */
export interface HistoryResponse {
  events: StatusEvent[]
}

/**
 * 刷新状态响应
 */
export interface RefreshStatusResponse {
  success: boolean
  message: string
  refreshedAt: string
}

/**
 * 时间范围选项
 */
export interface TimeRangeOption {
  label: string
  value: string
}

/**
 * 市场标签选项
 */
export interface MarketTabOption {
  label: string
  value: MarketType
}

/**
 * API 端点说明映射（文档 2.2.2 节的数据类型列表）
 */
export const DataTypeInfo: Record<string, { name: string; category: string; interfaces: string }> = {
  daily_quote: { name: '日线行情数据', category: '核心行情数据', interfaces: 'pro_bar / stock_zh_a_hist()' },
  realtime_quote: { name: '实时行情数据', category: '核心行情数据', interfaces: 'stock_zh_a_spot_em()' },
  minute_quote: { name: '分钟行情数据', category: '核心行情数据', interfaces: 'stk_mins / stock_zh_a_hist_min_em()' },
  financials: { name: '财务报表数据', category: '公司基本面数据', interfaces: 'income / stock_profit_sheet_by_report_em()' },
  financial_indicator: { name: '财务指标数据', category: '公司基本面数据', interfaces: 'fina_indicator / stock_financial_abstract()' },
  company_info: { name: '公司信息数据', category: '公司基本面数据', interfaces: 'stock_basic' },
  news: { name: '新闻资讯数据', category: '市场参考数据', interfaces: 'news / js_news()' },
  calendar: { name: '交易日历数据', category: '市场参考数据', interfaces: 'trade_cal / tool_trade_date_hist_sina()' },
  top_list: { name: '龙虎榜数据', category: '资金动向数据', interfaces: 'top_list / stock_lhb_detail_em()' },
  moneyflow: { name: '资金流向数据', category: '资金动向数据', interfaces: 'moneyflow / stock_individual_fund_flow()' },
  dividend: { name: '分红送股数据', category: '资金动向数据', interfaces: 'dividend / stock_dividend_cninfo()' },
  shareholder_num: { name: '股东人数数据', category: '股东数据', interfaces: 'stk_holdernumber' },
  top_shareholder: { name: '十大股东数据', category: '股东数据', interfaces: 'stock_gdfx_top_10_em()' },
  margin: { name: '融资融券数据', category: '融资融券', interfaces: 'margin / stock_margin_sse()' },
  macro_economy: { name: '宏观经济数据', category: '宏观经济数据', interfaces: 'cn_gdp / cn_cpi / cn_ppi / cn_pmi' },
  sector: { name: '板块数据', category: '板块数据', interfaces: 'stock_board_concept_name_em()' },
  index: { name: '指数数据', category: '板块数据', interfaces: 'index_daily' },
  ipo: { name: 'IPO新股数据', category: '特殊数据', interfaces: 'new_share' },
  pledge: { name: '股权质押数据', category: '特殊数据', interfaces: 'pledge_detail' },
  repurchase: { name: '股票回购数据', category: '特殊数据', interfaces: 'repurchase' },
  adj_factor: { name: '复权因子数据', category: '交易辅助数据', interfaces: 'adj_factor' }
}
