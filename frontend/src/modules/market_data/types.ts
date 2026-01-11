/**
 * 市场数据模块类型定义
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
 * 股票状态枚举
 */
export enum StockStatus {
  LISTED = 'L',       // 上市
  DELISTED = 'D',     // 退市
  SUSPENDED = 'P',    // 暂停
  IPO = 'I'           // IPO
}

/**
 * 股票状态标签映射
 */
export const StockStatusLabels: Record<StockStatus, string> = {
  [StockStatus.LISTED]: '上市',
  [StockStatus.DELISTED]: '退市',
  [StockStatus.SUSPENDED]: '暂停',
  [StockStatus.IPO]: 'IPO'
}

/**
 * 交易所枚举
 */
export enum Exchange {
  SSE = 'SSE',       // 上海证券交易所
  SZSE = 'SZSE',     // 深圳证券交易所
  NASDAQ = 'NASDAQ', // 纳斯达克
  NYSE = 'NYSE',     // 纽约证券交易所
  HKEX = 'HKEX'      // 香港交易所
}

/**
 * 交易所标签映射
 */
export const ExchangeLabels: Record<Exchange, string> = {
  [Exchange.SSE]: '上交所',
  [Exchange.SZSE]: '深交所',
  [Exchange.NASDAQ]: '纳斯达克',
  [Exchange.NYSE]: '纽交所',
  [Exchange.HKEX]: '港交所'
}

/**
 * 股票信息
 */
export interface StockInfo {
  symbol: string
  market: MarketType
  name: string
  industry?: string
  sector?: string
  listingDate: string
  exchange: Exchange
  status: StockStatus
  dataSource: string
}

/**
 * 行情数据
 */
export interface Quote {
  symbol: string
  tradeDate: string
  open: number
  high: number
  low: number
  close: number
  volume: number
  amount?: number
  change?: number
  changePct?: number
  dataSource: string
}

/**
 * 财务数据
 */
export interface Financial {
  symbol: string
  reportDate: string
  reportType: string
  publishDate?: string
  incomeStatement?: Record<string, any>
  balanceSheet?: Record<string, any>
  cashFlow?: Record<string, any>
  dataSource: string
}

/**
 * 财务指标
 */
export interface Indicator {
  symbol: string
  reportDate: string
  roe?: number
  roa?: number
  debtToAssets?: number
  currentRatio?: number
  quickRatio?: number
  eps?: number
  dataSource: string
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
 * 查询表单
 */
export interface QueryForm {
  symbol: string
  market: MarketType
  startDate: string
  endDate: string
}

/**
 * 数据同步状态
 */
export interface SyncStatus {
  syncing: boolean
  progress: number
  message: string
}

/**
 * 分页参数
 */
export interface Pagination {
  page: number
  pageSize: number
  total: number
}

/**
 * 表格列配置
 */
export interface TableColumn {
  prop: string
  label: string
  width?: number
  sortable?: boolean
  formatter?: (row: any) => string
}

/**
 * 筛选条件
 */
export interface FilterCondition {
  keyword?: string
  market?: MarketType
  industry?: string
  status?: StockStatus
}
