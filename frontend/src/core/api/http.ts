/**
 * HTTP 客户端封装
 * 基于 Axios 的统一请求处理
 */
import axios, { AxiosError, type AxiosInstance, type AxiosRequestConfig, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import router from '@core/router'
import { useUserStore } from '@core/auth/store'
import { authApi } from '@core/auth/api'

// ==================== 类型定义 ====================

export interface ApiResponse<T = unknown> {
  success: boolean
  data?: T
  error?: {
    code: string
    message: string
    details?: unknown
  }
}

export interface RequestConfig extends AxiosRequestConfig {
  skipErrorHandler?: boolean
  skipAuth?: boolean
  skipExpiredMessage?: boolean // 跳过显示"登录已过期"消息
}

// 扩展 Axios 请求配置，添加内部标记
interface ExtendedAxiosRequestConfig extends AxiosRequestConfig {
  skipErrorHandler?: boolean
  skipAuth?: boolean
  skipExpiredMessage?: boolean // 跳过显示"登录已过期"消息
  _retry?: boolean // 标记是否正在重试
}

// ==================== 创建 Axios 实例 ====================

const baseURL: string = (import.meta.env.VITE_API_BASE_URL as string | undefined) || '/api'

const http: AxiosInstance = axios.create({
  baseURL,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ==================== 请求拦截器 ====================

http.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const extendedConfig = config as ExtendedAxiosRequestConfig

    // 从 localStorage 获取 token
    const token = localStorage.getItem('access_token')
    if (token && !extendedConfig.skipAuth) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// ==================== 响应拦截器 ====================

// 标记是否正在刷新 token
let isRefreshing = false
// 存储等待刷新完成的请求
let failedQueue: Array<{
  resolve: (value?: unknown) => void
  reject: (reason?: unknown) => void
}> = []

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((prom) => {
    if (error) {
      prom.reject(error)
    } else {
      prom.resolve(token)
    }
  })

  failedQueue = []
}

http.interceptors.response.use(
  (response: AxiosResponse<ApiResponse>) => {
    return response
  },
  async (error: AxiosError<ApiResponse>) => {
    const extendedConfig = error.config as ExtendedAxiosRequestConfig

    // 跳过错误处理的情况
    if (extendedConfig?.skipErrorHandler) {
      return Promise.reject(error)
    }

    const status = error.response?.status
    const data = error.response?.data

    // ==================== 401 处理：Token 过期 ====================
    if (status === 401 && extendedConfig && !extendedConfig._retry) {
      console.log('[Http] 401 Interceptor triggered', { url: extendedConfig.url, isRefreshing })

      // 登录接口的401错误（密码错误/用户状态异常）不应该尝试刷新token
      // 直接返回错误，让用户看到正确的错误提示
      if (extendedConfig.url?.includes('/users/login') || extendedConfig.url?.includes('/users/register')) {
        console.log('[Http] Login/Register 401 error, skip token refresh')
        return Promise.reject(error)
      }

      // 如果是刷新 token 的请求本身失败了，或者已经在重试中，直接返回错误
      // 避免死循环：如果当前 URL 是刷新 token 的 URL，则不进行重试
      if (extendedConfig.url?.includes('/refresh-token') || extendedConfig.url?.includes('/users/refresh-token')) {
        processQueue(new Error('Refresh token failed'), null)
        return handleTokenExpired(extendedConfig)
      }

      // 如果没有 refresh_token，直接清除状态并跳转登录如果正在刷新 token，将请求加入队列
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        })
          .then(() => {
            // 刷新成功，重试原请求
            return http(extendedConfig)
          })
          .catch((err) => {
            return Promise.reject(err)
          })
      }

      const refreshToken = localStorage.getItem('refresh_token')

      // 如果没有 refresh_token，直接清除状态并跳转登录
      if (!refreshToken) {
        return handleTokenExpired(extendedConfig)
      }

      // 开始刷新 token
      extendedConfig._retry = true
      isRefreshing = true

      try {
        console.log('[Http] Attempting to refresh token...')
        // 调用刷新 token API
        const response = await authApi.refreshToken({ refresh_token: refreshToken })
        console.log('[Http] Token refresh success')

        // 保存新 token
        const userStore = useUserStore()
        userStore.token = response.access_token
        localStorage.setItem('access_token', response.access_token)
        localStorage.setItem('refresh_token', response.refresh_token)

        // 处理队列中的请求
        processQueue(null, response.access_token)

        // 重试原请求
        extendedConfig.headers.Authorization = `Bearer ${response.access_token}`
        return http(extendedConfig)
      } catch (refreshError) {
        // 刷新失败，清除状态并跳转登录
        processQueue(refreshError, null)
        return handleTokenExpired(extendedConfig)
      } finally {
        isRefreshing = false
      }
    }

    // ==================== 其他错误处理 ====================
    if (status) {
      switch (status) {
        case 403:
          ElMessage.error(data?.error?.message || '没有权限访问')
          break
        case 404:
          ElMessage.error(data?.error?.message || '请求的资源不存在')
          break
        case 500:
          ElMessage.error('服务器错误，请稍后重试')
          break
        case 502:
        case 503:
        case 504:
          ElMessage.error('服务暂时不可用，请稍后重试')
          break
        default:
          if (data?.error?.message) {
            ElMessage.error(data.error.message)
          } else if (error.message) {
            // 避免重复显示 axios 的超时消息
            if (!error.message.includes('timeout')) {
              ElMessage.error(error.message)
            }
          } else {
            ElMessage.error('请求失败，请稍后重试')
          }
      }
    } else {
      // 网络错误
      ElMessage.error('网络连接失败，请检查网络设置')
    }

    return Promise.reject(error)
  }
)

/**
 * 处理 Token 过期
 * 注意：不要在这里进行路由导航，由路由守卫统一处理，避免无限循环
 * @param config 请求配置（用于检查是否跳过错误消息）
 */
function handleTokenExpired(config?: ExtendedAxiosRequestConfig) {
  console.log('[Http] handleTokenExpired called', { skipMessage: config?.skipExpiredMessage })
  // 清除本地认证状态
  const userStore = useUserStore()
  userStore.token = null
  userStore.userInfo = null
  userStore.preferences = null
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')

  // 只在非静默模式下显示错误消息
  const skipMessage = config?.skipExpiredMessage === true
  if (!skipMessage) {
    ElMessage.error('登录已过期，请重新登录')
  }

  // 返回特定的错误类型，让路由守卫处理导航
  return Promise.reject(new Error('Token expired'))
}

// ==================== 导出封装方法 ====================

export async function request<T = unknown>(
  config: RequestConfig
): Promise<T> {
  const response = await http.request<ApiResponse<T>>(config)

  // 兼容三种响应格式：
  // 1. 标准格式: { success: true, data: {...} }
  // 2. 错误格式: { success: false, error: {...} }
  // 3. 直接格式: { ... } (后端直接返回数据，如 ConnectionTestResponse)
  const hasSuccessField = response.data?.success !== undefined
  const hasErrorField = response.data?.error !== undefined

  if (hasSuccessField && hasErrorField) {
    // 标准格式或错误格式
    if (response.data.success) {
      return response.data.data as T
    }
    throw new Error(response.data.error?.message || '请求失败')
  } else if (hasSuccessField && !hasErrorField) {
    // 直接格式，包含 success 字段但不包含 error 字段（如 ConnectionTestResponse）
    // 如果 success 为 false，需要根据 message 或其他字段处理错误
    if (!response.data.success) {
      throw new Error(response.data.message || '请求失败')
    }
    return response.data as T
  } else {
    // 直接格式 - 返回整个响应体作为数据
    return response.data as T
  }
}

export const httpGet = <T = unknown>(url: string, config?: RequestConfig) =>
  request<T>({ ...config, method: 'GET', url })

export const httpPost = <T = unknown>(url: string, data?: unknown, config?: RequestConfig) =>
  request<T>({ ...config, method: 'POST', url, data })

export const httpPut = <T = unknown>(url: string, data?: unknown, config?: RequestConfig) =>
  request<T>({ ...config, method: 'PUT', url, data })

export const httpDelete = <T = unknown>(url: string, config?: RequestConfig) =>
  request<T>({ ...config, method: 'DELETE', url })

export default http
