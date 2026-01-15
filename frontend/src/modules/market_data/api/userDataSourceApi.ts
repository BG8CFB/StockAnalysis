/**
 * 用户数据源配置 API 客户端
 */
import request from '@core/api/http'
import { MarketType } from '../types'

/**
 * 用户数据源配置
 */
export interface UserDataSourceConfig {
  user_id: string
  source_id: string
  market: string
  enabled: boolean
  priority: number
  config: {
    api_key: string
  }
  created_at?: string
  updated_at?: string
  last_test_time?: string
  last_test_status?: 'success' | 'failed'
  last_test_error?: string
}

/**
 * 创建用户数据源配置请求
 */
export interface CreateUserDataSourceConfigRequest {
  source_id: string
  market: string
  api_key: string
  enabled?: boolean
  priority?: number
}

/**
 * 更新用户数据源配置请求
 */
export interface UpdateUserDataSourceConfigRequest {
  api_key?: string
  enabled?: boolean
  priority?: number
}

/**
 * 连接测试响应
 */
export interface ConnectionTestResponse {
  success: boolean
  error?: string
  test_time: string
}

/**
 * 用户数据源 API 类
 */
class UserDataSourceApi {
  /**
   * 获取用户数据源配置列表
   */
  async getConfigs(market?: MarketType, enabledOnly: boolean = true): Promise<UserDataSourceConfig[]> {
    const params: any = { enabled_only: enabledOnly }
    if (market) {
      params.market = market
    }
    const response = await request.get<UserDataSourceConfig[]>('/market-data/user-sources/configs', { params })
    return response.data
  }

  /**
   * 获取单个用户数据源配置
   */
  async getConfig(sourceId: string, market: string = 'A_STOCK'): Promise<UserDataSourceConfig> {
    const response = await request.get<UserDataSourceConfig>(`/market-data/user-sources/config/${sourceId}`, {
      params: { market }
    })
    return response.data
  }

  /**
   * 创建用户数据源配置
   */
  async createConfig(data: CreateUserDataSourceConfigRequest): Promise<{ message: string; doc_id: string }> {
    const response = await request.post<{ message: string; doc_id: string }>(
      '/market-data/user-sources/config',
      data
    )
    return response.data
  }

  /**
   * 更新用户数据源配置
   */
  async updateConfig(
    sourceId: string,
    market: string,
    data: UpdateUserDataSourceConfigRequest
  ): Promise<{ message: string; doc_id: string }> {
    const response = await request.put<{ message: string; doc_id: string }>(
      `/market-data/user-sources/config/${sourceId}`,
      data,
      { params: { market } }
    )
    return response.data
  }

  /**
   * 删除用户数据源配置
   */
  async deleteConfig(sourceId: string, market: string): Promise<{ message: string }> {
    const response = await request.delete<{ message: string }>(
      `/market-data/user-sources/config/${sourceId}`,
      { params: { market } }
    )
    return response.data
  }

  /**
   * 测试用户数据源配置
   */
  async testConfig(sourceId: string, market: string): Promise<ConnectionTestResponse> {
    const response = await request.post<ConnectionTestResponse>(
      `/market-data/user-sources/config/${sourceId}/test`,
      {},
      { params: { market } }
    )
    return response.data
  }
}

export default new UserDataSourceApi()
