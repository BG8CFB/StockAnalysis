import axios from 'axios'
import type { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios'
import { useUserStore } from '@/modules/user_management/store'

export interface ApiResponse<T = any> {
  data: T
  message?: string
  error?: string
  status_code?: number
}

class HttpClient {
  private instance: AxiosInstance

  constructor() {
    this.instance = axios.create({
      baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
      timeout: 10000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    this.setupInterceptors()
  }

  private setupInterceptors() {
    // 请求拦截器
    this.instance.interceptors.request.use(
      (config) => {
        // 添加认证Token
        const userStore = useUserStore()
        if (userStore.token) {
          config.headers.Authorization = `Bearer ${userStore.token}`
        }

        // 添加请求时间戳
        config.metadata = { startTime: new Date() }

        return config
      },
      (error) => {
        return Promise.reject(error)
      }
    )

    // 响应拦截器
    this.instance.interceptors.response.use(
      (response: AxiosResponse) => {
        // 计算请求耗时
        const endTime = new Date()
        const startTime = response.config.metadata?.startTime
        if (startTime) {
          const duration = endTime.getTime() - startTime.getTime()
          console.log(`API Request ${response.config.url} took ${duration}ms`)
        }

        return response
      },
      (error: AxiosError) => {
        // 统一错误处理
        if (error.response?.status === 401) {
          // Token过期或无效，清除用户信息并跳转到登录页
          const userStore = useUserStore()
          userStore.logout()

          // 如果不在登录页，则跳转到登录页
          if (window.location.pathname !== '/login') {
            window.location.href = '/login'
          }
        }

        // 返回统一的错误格式
        const errorResponse = {
          message: error.response?.data?.message || error.message || 'Unknown error',
          status_code: error.response?.status || 500,
          error: error.response?.data?.error || 'Request failed'
        }

        return Promise.reject(errorResponse)
      }
    )
  }

  // GET 请求
  async get<T = any>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response = await this.instance.get(url, config)
    return response.data
  }

  // POST 请求
  async post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response = await this.instance.post(url, data, config)
    return response.data
  }

  // PUT 请求
  async put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response = await this.instance.put(url, data, config)
    return response.data
  }

  // DELETE 请求
  async delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response = await this.instance.delete(url, config)
    return response.data
  }

  // PATCH 请求
  async patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response = await this.instance.patch(url, data, config)
    return response.data
  }

  // 上传文件
  async upload<T = any>(url: string, formData: FormData, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
    const response = await this.instance.post(url, formData, {
      ...config,
      headers: {
        'Content-Type': 'multipart/form-data',
        ...config?.headers,
      },
    })
    return response.data
  }

  // 获取原始axios实例
  getAxiosInstance(): AxiosInstance {
    return this.instance
  }
}

// 创建全局HTTP客户端实例
export const httpClient = new HttpClient()

// 扩展AxiosRequestConfig类型以支持metadata
declare module 'axios' {
  interface AxiosRequestConfig {
    metadata?: {
      startTime: Date
    }
  }
}