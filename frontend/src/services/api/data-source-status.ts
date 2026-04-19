/**
 * 数据源状态监控 API
 * 对应后端 /api/core/system/data-source-status/* 端点
 */

import apiClient from '../http/client'
import type { ApiResponse } from '@/types/common.types'
import type { DataSourceStatus, DataTypeDetail, DataSourceHistoryItem } from '@/types/admin.types'

/** 获取数据源状态概览 */
export async function getDataSourceOverview(): Promise<ApiResponse<DataSourceStatus[]>> {
  return apiClient.get<DataSourceStatus[]>('/api/core/system/data-source-status/overview')
}

/** 获取市场详情 */
export async function getMarketDetail(market: string): Promise<ApiResponse<DataSourceStatus>> {
  return apiClient.get<DataSourceStatus>(`/api/core/system/data-source-status/${market}`)
}

/** 获取数据类型详情 */
export async function getDataTypeDetail(market: string, dataType: string): Promise<ApiResponse<DataTypeDetail>> {
  return apiClient.get<DataTypeDetail>(`/api/core/system/data-source-status/${market}/${dataType}`)
}

/** 获取数据源历史 */
export async function getDataSourceHistory(
  market: string,
  dataType: string,
  limit = 50
): Promise<ApiResponse<DataSourceHistoryItem[]>> {
  return apiClient.get<DataSourceHistoryItem[]>(
    `/api/core/system/data-source-status/${market}/${dataType}/history`,
    { limit }
  )
}

/** 重试数据源 */
export async function retryDataSource(
  market: string,
  dataType: string,
  sourceId: string
): Promise<ApiResponse<Record<string, never>>> {
  return apiClient.post<Record<string, never>>(
    `/api/core/system/data-source-status/${market}/${dataType}/${sourceId}/retry`
  )
}

/** 刷新所有数据源 */
export async function refreshAllDataSources(): Promise<ApiResponse<Record<string, never>>> {
  return apiClient.post<Record<string, never>>('/api/core/system/data-source-status/refresh')
}
