/**
 * 市场数据模块 API 客户端
 * 仅包含数据源监控相关接口
 */
import request from '@core/api/http'
import {
  MarketType,
  type DashboardOverview,
  type MarketDetail,
  type DataTypeDetail,
  type ErrorDetail,
  type RetryResponse,
  type HistoryResponse,
  type RefreshStatusResponse,
  type StatusEvent,
} from '../types'

// 重新导出类型，保持向后兼容
export type { MarketType, StatusEvent }

// API 响应类型别名，使用 types.ts 中的类型
export type DashboardOverviewResponse = DashboardOverview
export type MarketDetailResponse = MarketDetail
export type DataTypeDetailResponse = DataTypeDetail
export type ErrorDetailResponse = ErrorDetail

/**
 * 市场数据 API 类
 * 仅包含数据源监控相关接口
 */
class MarketDataApi {
  /**
   * 获取仪表板概览
   */
  async getDashboardOverview(): Promise<DashboardOverview> {
    const response = await request.get<DashboardOverview>('/core/system/data-source-status/overview')
    return response.data
  }

  /**
   * 获取指定市场的详细状态
   */
  async getMarketDetail(market: MarketType): Promise<MarketDetail> {
    const response = await request.get<MarketDetail>(`/core/system/data-source-status/${market}`)
    return response.data
  }

  /**
   * 获取指定数据类型的详细信息
   */
  async getDataTypeDetail(market: MarketType, dataType: string): Promise<DataTypeDetail> {
    const response = await request.get<DataTypeDetail>(`/core/system/data-source-status/${market}/${dataType}`)
    return response.data
  }

  /**
   * 获取接口错误详情（普通用户）
   */
  async getErrorDetail(market: MarketType, dataType: string, sourceId: string): Promise<ErrorDetail> {
    const response = await request.get<ErrorDetail>(`/core/system/data-source-status/${market}/${dataType}/${sourceId}/error`)
    return response.data
  }

  /**
   * 获取接口错误详情（管理员）
   */
  async getErrorDetailAdmin(market: MarketType, dataType: string, sourceId: string): Promise<ErrorDetail> {
    const response = await request.get<ErrorDetail>(`/core/system/data-source-status/${market}/${dataType}/${sourceId}/error`)
    return response.data
  }

  /**
   * 手动重试数据源
   */
  async retryDataSource(market: MarketType, dataType: string, sourceId: string): Promise<RetryResponse> {
    const response = await request.post<RetryResponse>(`/core/system/data-source-status/${market}/${dataType}/${sourceId}/retry`)
    return response.data
  }

  /**
   * 获取历史记录
   */
  async getHistory(market: MarketType, dataType: string, hours: number = 24): Promise<HistoryResponse> {
    const response = await request.get<HistoryResponse>(`/core/system/data-source-status/${market}/${dataType}/history`, {
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
    const response = await request.post<RefreshStatusResponse>('/core/system/data-source-status/refresh', params)
    return response.data
  }
}

export default new MarketDataApi()
