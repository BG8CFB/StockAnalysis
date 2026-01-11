/**
 * 市场数据模块 API 客户端
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
 * 股票信息响应
 */
export interface StockInfoResponse {
  symbol: string
  market: MarketType
  name: string
  industry?: string
  sector?: string
  listing_date: string
  exchange: string
  status: string
  data_source: string
}

/**
 * 行情数据响应
 */
export interface QuoteResponse {
  symbol: string
  trade_date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount?: number
  change?: number
  change_pct?: number
  data_source: string
}

/**
 * 财务数据响应
 */
export interface FinancialResponse {
  symbol: string
  report_date: string
  report_type: string
  publish_date?: string
  income_statement?: Record<string, any>
  balance_sheet?: Record<string, any>
  cash_flow?: Record<string, any>
  data_source: string
}

/**
 * 财务指标响应
 */
export interface IndicatorResponse {
  symbol: string
  report_date: string
  roe?: number
  debt_to_assets?: number
  current_ratio?: number
  eps?: number
  data_source: string
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
 * 股票列表请求参数
 */
export interface StockListRequest {
  market: MarketType
  status?: string
}

/**
 * 行情查询请求参数
 */
export interface QuoteQueryRequest {
  symbol: string
  start_date?: string
  end_date?: string
  limit?: number
}

/**
 * 财务查询请求参数
 */
export interface FinancialQueryRequest {
  symbol: string
  report_type?: string
  limit?: number
}

/**
 * 数据同步请求参数
 */
export interface DataSyncRequest {
  symbol?: string
  data_types?: string[]
  force_refresh?: boolean
}

/**
 * 数据同步响应
 */
export interface DataSyncResponse {
  success: boolean
  message: string
  synced_count: number
  failed_count: number
  source_used?: string
  duration_ms?: number
}

/**
 * 市场数据 API 类
 */
class MarketDataApi {
  /**
   * 获取股票列表
   */
  async getStockList(params: StockListRequest): Promise<StockInfoResponse[]> {
    const response = await request.post<StockInfoResponse[]>('/api/market-data/stocks/list', params)
    return response.data
  }

  /**
   * 获取股票详细信息
   */
  async getStockInfo(symbol: string): Promise<StockInfoResponse> {
    const response = await request.get<StockInfoResponse>(`/api/market-data/stocks/${symbol}/info`)
    return response.data
  }

  /**
   * 查询历史行情
   */
  async queryQuotes(params: QuoteQueryRequest): Promise<QuoteResponse[]> {
    const response = await request.post<QuoteResponse[]>('/api/market-data/quotes/query', params)
    return response.data
  }

  /**
   * 获取最新行情
   */
  async getLatestQuote(symbol: string): Promise<QuoteResponse> {
    const response = await request.get<QuoteResponse>(`/api/market-data/quotes/${symbol}/latest`)
    return response.data
  }

  /**
   * 查询财务数据
   */
  async queryFinancials(params: FinancialQueryRequest): Promise<FinancialResponse[]> {
    const response = await request.post<FinancialResponse[]>('/api/market-data/financials/query', params)
    return response.data
  }

  /**
   * 获取最新财务指标
   */
  async getLatestIndicators(symbol: string): Promise<IndicatorResponse> {
    const response = await request.get<IndicatorResponse>(`/api/market-data/indicators/${symbol}/latest`)
    return response.data
  }

  /**
   * 检查数据源健康状态
   */
  async checkDataSourcesHealth(): Promise<DataSourceHealthResponse[]> {
    const response = await request.get<DataSourceHealthResponse[]>('/api/market-data/health')
    return response.data
  }

  /**
   * 同步数据
   */
  async syncData(params: DataSyncRequest): Promise<DataSyncResponse> {
    const response = await request.post<DataSyncResponse>('/api/market-data/sync', params)
    return response.data
  }
}

export default new MarketDataApi()
