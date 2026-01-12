/**
 * 市场数据模块 API 客户端
 * 仅包含数据源监控相关接口
 */
import request from '@core/api/http'

/**
 * 市场类型枚举
 */
export enum MarketType {
  A_STOCK = 'A_STOCK',
  US_STOCK = 'US_STOCK',
  HK_STOCK = 'HK_STOCK'
}

/**
 * 数据源健康状态响应
 */
export interface DataSourceHealthResponse {
  source_name: string
  is_available: boolean
  response_time_ms?: number
  last_check_time?: string
  failure_count: number
  error?: string
}

/**
 * 仪表板概览响应
 */
export interface DashboardOverviewResponse {
  a_stock?: {
    status: 'healthy' | 'degraded' | 'unavailable'
    last_update: string
    last_update_relative: string
  }
  us_stock?: {
    status: 'healthy' | 'degraded' | 'unavailable'
    last_update: string
    last_update_relative: string
  }
  hk_stock?: {
    status: 'healthy' | 'degraded' | 'unavailable'
    last_update: string
    last_update_relative: string
    reason?: string
  }
}

/**
 * 市场详细状态响应
 */
export interface MarketDetailResponse {
  market: MarketType
  market_name: string
  data_types: DataTypeStatus[]
}

/**
 * 数据类型状态
 */
export interface DataTypeStatus {
  data_type: string
  data_type_name: string
  current_source: DataSourceInfo
  is_fallback: boolean
  can_retry: boolean
  primary_source?: {
    source_id: string
    status: string
    can_retry: boolean
  }
  fallback_reason?: string
}

/**
 * 数据源信息
 */
export interface DataSourceInfo {
  source_type: 'system' | 'user'
  source_id: string
  source_name: string
  status: 'healthy' | 'degraded' | 'unavailable' | 'standby'
  last_check: string
  last_check_relative: string
  response_time_ms?: number
}

/**
 * 数据类型详细信息响应
 */
export interface DataTypeDetailResponse {
  market: MarketType
  data_type: string
  data_type_name: string
  sources: DataSourceDetailInfo[]
  recent_events: StatusEvent[]
}

/**
 * 数据源详细信息
 */
export interface DataSourceDetailInfo {
  source_type: 'system' | 'user'
  source_id: string
  source_name: string
  status: 'healthy' | 'degraded' | 'unavailable' | 'standby'
  priority: number
  last_check?: string
  response_time_ms?: number
  avg_response_time_ms?: number
  failure_count: number
  note?: string
  api_endpoints?: ApiEndpointInfo[]
}

/**
 * API 端点信息
 */
export interface ApiEndpointInfo {
  endpoint_name: string
  endpoint_name_cn: string
  status: 'healthy' | 'unavailable'
  last_check?: string
  failure_count: number
}

/**
 * 状态事件
 */
export interface StatusEvent {
  timestamp: string
  event_type: string
  description: string
  from_status?: string
  to_status?: string
  from_source?: string
  to_source?: string
  source_id?: string
}

/**
 * 错误详情响应
 */
export interface ErrorDetailResponse {
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
 * 手动重试响应
 */
export interface RetryResponse {
  success: boolean
  message: string
  result?: {
    status: string
    response_time_ms: number
    recovered_at: string
    was_fallback: boolean
    previous_source: string
  }
  error?: {
    error_code?: string
    error_message?: string
    failure_count?: number
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
  refreshed_at: string
}

/**
 * 市场数据 API 类
 * 仅包含数据源监控相关接口
 */
class MarketDataApi {
  /**
   * 获取仪表板概览
   */
  async getDashboardOverview(): Promise<DashboardOverviewResponse> {
    const response = await request.get<DashboardOverviewResponse>('/api/core/system/data-source-status/overview')
    return response.data
  }

  /**
   * 获取指定市场的详细状态
   */
  async getMarketDetail(market: MarketType): Promise<MarketDetailResponse> {
    const response = await request.get<MarketDetailResponse>(`/api/core/system/data-source-status/${market}`)
    return response.data
  }

  /**
   * 获取指定数据类型的详细信息
   */
  async getDataTypeDetail(market: MarketType, dataType: string): Promise<DataTypeDetailResponse> {
    const response = await request.get<DataTypeDetailResponse>(`/api/core/system/data-source-status/${market}/${dataType}`)
    return response.data
  }

  /**
   * 获取接口错误详情（普通用户）
   */
  async getErrorDetail(market: MarketType, dataType: string, sourceId: string): Promise<ErrorDetailResponse> {
    const response = await request.get<ErrorDetailResponse>(`/api/core/system/data-source-status/${market}/${dataType}/${sourceId}/error`)
    return response.data
  }

  /**
   * 获取接口错误详情（管理员）
   */
  async getErrorDetailAdmin(market: MarketType, dataType: string, sourceId: string): Promise<ErrorDetailResponse> {
    const response = await request.get<ErrorDetailResponse>(`/api/core/admin/data-source-status/${market}/${dataType}/${sourceId}/error`)
    return response.data
  }

  /**
   * 手动重试数据源
   */
  async retryDataSource(market: MarketType, dataType: string, sourceId: string): Promise<RetryResponse> {
    const response = await request.post<RetryResponse>(`/api/core/system/data-source-status/${market}/${dataType}/${sourceId}/retry`)
    return response.data
  }

  /**
   * 获取历史记录
   */
  async getHistory(market: MarketType, dataType: string, hours: number = 24): Promise<HistoryResponse> {
    const response = await request.get<HistoryResponse>(`/api/core/system/data-source-status/${market}/${dataType}/history`, {
      params: { hours }
    })
    return response.data
  }

  /**
   * 手动刷新状态
   */
  async refreshStatus(market?: MarketType): Promise<RefreshStatusResponse> {
    const params: any = {}
    if (market) {
      params.market = market
    }
    const response = await request.post<RefreshStatusResponse>('/api/core/system/data-source-status/refresh', params)
    return response.data
  }
}

export default new MarketDataApi()
