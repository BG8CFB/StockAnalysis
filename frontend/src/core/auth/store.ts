/**
 * 用户状态管理
 *
 * 设计原则：
 * - 认证状态由 token 决定（同步）
 * - userInfo 按需加载：登录成功后 / App.vue 启动时（有 token 时后台加载）
 * - 路由守卫只检查 token，不检查 userInfo
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, userApi, type UserInfo, type UserPreferences } from './api'
import { eventBus, Events } from '@core/events/bus'

export const useUserStore = defineStore('user', () => {
  // ==================== 状态 ====================

  const token = ref<string | null>(localStorage.getItem('access_token'))
  const userInfo = ref<UserInfo | null>(null)
  const preferences = ref<UserPreferences | null>(null)
  const loading = ref(false)
  let userInfoLoadingPromise: Promise<void> | null = null

  // ==================== 计算属性 ====================

  const isLoggedIn = computed(() => !!token.value)
  const email = computed(() => userInfo.value?.email ?? '')
  const userId = computed(() => userInfo.value?.id ?? '')
  const isAdmin = computed(() => {
    const role = userInfo.value?.role
    return role === 'ADMIN' || role === 'SUPER_ADMIN'
  })
  const theme = computed(() => preferences.value?.theme ?? 'light')

  // ==================== 方法 ====================

  /**
   * 用户登录
   */
  async function login(account: string, password: string) {
    console.log('[UserStore] login called', { account })
    loading.value = true
    try {
      const response = await authApi.login({ account, password })
      console.log('[UserStore] Login API success', response)

      token.value = response.access_token
      localStorage.setItem('access_token', response.access_token)
      localStorage.setItem('refresh_token', response.refresh_token)

      // 登录成功后立即加载用户信息和偏好
      await ensureUserInfoLoaded()

      // 触发登录事件
      eventBus.emit(Events.USER_LOGIN, userInfo.value)

      return true
    } catch (error) {
      console.error('[UserStore] Login failed:', error)
      clearState()
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * 用户注册
   */
  async function register(
    email: string,
    username: string,
    password: string,
    confirmPassword: string
  ) {
    loading.value = true
    try {
      const user = await authApi.register({
        email,
        username,
        password,
        confirm_password: confirmPassword,
      })

      if (user.status === 'active') {
        return await login(email, password)
      } else if (user.status === 'pending') {
        return { needsApproval: true, user }
      } else if (user.status === 'disabled') {
        throw new Error('账号已被禁用')
      } else if (user.status === 'rejected') {
        throw new Error('账号已被拒绝')
      }

      return true
    } catch (error) {
      console.error('Register failed:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * 用户登出
   */
  async function logout() {
    try {
      await authApi.logout()
    } catch (error) {
      console.error('Logout API failed:', error)
    } finally {
      clearState()
      eventBus.emit(Events.USER_LOGOUT)
    }
  }

  /**
   * 获取用户信息
   */
  async function fetchUserInfo(skipExpiredMessage = false) {
    if (!token.value) return
    try {
      userInfo.value = await userApi.getMe({ skipExpiredMessage })
    } catch (error: unknown) {
      // 401 由 HTTP 拦截器处理（token 刷新或跳转登录），此处只记录其他错误
      const axiosError = error as { response?: { status?: number } }
      if (axiosError?.response?.status !== 401) {
        console.error('[Auth] 获取用户信息失败:', error)
      }
      throw error
    }
  }

  /**
   * 获取用户配置
   */
  async function fetchPreferences() {
    if (!token.value) return

    try {
      preferences.value = await userApi.getPreferences()
      applyTheme(preferences.value.theme)
    } catch (error) {
      console.error('Failed to fetch preferences:', error)
    }
  }

  /**
   * 更新用户配置
   */
  async function updatePreferences(data: Partial<UserPreferences>) {
    if (!token.value) return

    try {
      preferences.value = await userApi.updatePreferences(data)
      if (data.theme) {
        applyTheme(data.theme)
      }
      eventBus.emit(Events.PREFERENCES_UPDATED, preferences.value)
    } catch (error) {
      console.error('Failed to update preferences:', error)
      throw error
    }
  }

  /**
   * 应用主题
   */
  function applyTheme(theme: string) {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }

  /**
   * 清除所有状态
   */
  function clearState() {
    token.value = null
    userInfo.value = null
    preferences.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  }

  /**
   * 确保用户信息加载完成
   *
   * 调用场景：
   * 1. 登录成功后 - 立即加载用户信息
   * 2. 应用启动时 - 自动加载用户信息（App.vue onMounted）
   *
   * 注意：
   * - 如果 userInfo 已加载，直接返回
   * - 如果没有 token，抛出错误（调用方应处理）
   * - 加载失败时清除状态并抛出错误（HTTP 拦截器会处理 401）
   */
  async function ensureUserInfoLoaded(): Promise<void> {
    // 已加载，跳过
    if (userInfo.value) {
      return
    }

    // 无 token，抛出错误
    if (!token.value) {
      throw new Error('No token available')
    }

    // 并发去重：避免多个调用同时触发鉴权/刷新流程，造成启动卡顿或竞态
    if (userInfoLoadingPromise) {
      return userInfoLoadingPromise
    }

    userInfoLoadingPromise = (async () => {
      try {
        // 启动阶段改为串行加载，避免并发 401 + refresh 队列导致的复杂边界问题
        const user = await userApi.getMe({ skipExpiredMessage: true })
        const prefs = await userApi.getPreferences({ skipExpiredMessage: true })

        userInfo.value = user
        preferences.value = prefs

        if (prefs?.theme) {
          applyTheme(prefs.theme)
        }

        console.log('[UserStore] ensureUserInfoLoaded success', {
          userId: user.id,
          role: user.role
        })
      } catch (error) {
        console.error('[UserStore] ensureUserInfoLoaded failed:', error)
        // 不再调用 clearState()，由 HTTP 拦截器统一处理
        // 避免重复清除导致的状态管理混乱
        throw error
      } finally {
        userInfoLoadingPromise = null
      }
    })()

    return userInfoLoadingPromise
  }

  return {
    // 状态
    token,
    userInfo,
    preferences,
    loading,

    // 计算属性
    isLoggedIn,
    email,
    userId,
    isAdmin,
    theme,

    // 方法
    login,
    register,
    logout,
    fetchUserInfo,
    fetchPreferences,
    updatePreferences,
    clearState,
    ensureUserInfoLoaded,
  }
})
