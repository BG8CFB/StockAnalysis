/**
 * 用户状态管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, userApi, type UserInfo, type UserPreferences, type User } from './api'
import { eventBus, Events } from '@core/events/bus'

export const useUserStore = defineStore('user', () => {
  // ==================== 状态 ====================

  const token = ref<string | null>(localStorage.getItem('access_token'))
  const userInfo = ref<UserInfo | null>(null)
  const preferences = ref<UserPreferences | null>(null)
  const loading = ref(false)

  // ==================== 计算属性 ====================

  const isLoggedIn = computed(() => !!token.value)
  const email = computed(() => userInfo.value?.email ?? '')
  const userId = computed(() => userInfo.value?.id ?? '')
  const isAdmin = computed(() => userInfo.value?.role === 'ADMIN' || userInfo.value?.role === 'SUPER_ADMIN')
  const theme = computed(() => preferences.value?.theme ?? 'light')

  // ==================== 方法 ====================

  /**
   * 用户登录
   */
  async function login(
    email: string,
    password: string,
    captchaToken?: string,
    slideX?: number,
    slideY?: number
  ) {
    console.log('[UserStore] login called', { email })
    loading.value = true
    try {
      const response = await authApi.login({
        email,
        password,
        captcha_token: captchaToken,
        slide_x: slideX,
        slide_y: slideY,
      })
      console.log('[UserStore] Login API success', response)
      token.value = response.access_token
      localStorage.setItem('access_token', response.access_token)
      localStorage.setItem('refresh_token', response.refresh_token)

      // 获取用户信息
      // 登录刚成功时，如果获取用户信息失败（如 token 问题），不要显示"过期"提示，而是由 catch 块处理
      console.log('[UserStore] Fetching user info after login...')
      await fetchUserInfo(true)
      console.log('[UserStore] User info fetched', userInfo.value)

      // 触发登录事件
      eventBus.emit(Events.USER_LOGIN, userInfo.value)

      return true
    } catch (error) {
      console.error('[UserStore] Login failed:', error)
      // 登录失败，确保清除状态
      token.value = null
      userInfo.value = null
      preferences.value = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      throw error // Re-throw to let caller handle specific errors (like captcha)
    } finally {
      loading.value = false
    }
  }

  /**
   * 用户注册
   * 注意：注册后返回 User 信息，不是 Token
   * 如果用户状态是 active，会自动登录；如果是 pending，需要等待审核
   */
  async function register(
    email: string,
    username: string,
    password: string,
    confirmPassword: string,
    captchaToken?: string,
    slideX?: number,
    slideY?: number
  ) {
    loading.value = true
    try {
      const user = await authApi.register({
        email,
        username,
        password,
        confirm_password: confirmPassword,
        captcha_token: captchaToken,
        slide_x: slideX,
        slide_y: slideY,
      })

      // 根据用户状态决定下一步操作
      if (user.status === 'active') {
        // 用户已激活，自动登录
        const loginSuccess = await login(email, password)
        return loginSuccess
      } else if (user.status === 'pending') {
        // 用户待审核，返回 false 让前端显示需要审核的消息
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
      // 无论 API 是否成功，都清除本地状态
      token.value = null
      userInfo.value = null
      preferences.value = null
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')

      // 触发登出事件
      eventBus.emit(Events.USER_LOGOUT)
    }
  }

  /**
   * 获取用户信息
   */
  async function fetchUserInfo(skipExpiredMessage = false) {
    if (!token.value) return

    // 401 错误由 HTTP 拦截器统一处理
    // 如果指定了 skipExpiredMessage，则传递给 API
    userInfo.value = await userApi.getMe({ skipExpiredMessage })
  }

  /**
   * 获取用户配置
   */
  async function fetchPreferences() {
    if (!token.value) return

    try {
      preferences.value = await userApi.getPreferences()
      // 应用主题
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
   * 初始化（从本地存储恢复状态）
   */
  async function initialize() {
    if (token.value) {
      await Promise.all([fetchUserInfo(), fetchPreferences()])
    }
  }

  /**
   * 静默初始化（不显示"登录已过期"消息，用于路由守卫）
   */
  async function initializeSilent() {
    if (token.value) {
      try {
        // 使用 skipExpiredMessage 选项，避免在 token 过期时显示错误消息
        const [user, prefs] = await Promise.all([
          userApi.getMe({ skipExpiredMessage: true }),
          userApi.getPreferences({ skipExpiredMessage: true })
        ])
        userInfo.value = user
        preferences.value = prefs
        if (prefs?.theme) applyTheme(prefs.theme)
        console.log('[UserStore] initializeSilent success', { user })
      } catch (error) {
        console.error('[UserStore] initializeSilent failed', error)
        // Token 无效，清除状态
        token.value = null
        userInfo.value = null
        preferences.value = null
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        throw error
      }
    }
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
    initialize,
    initializeSilent,
  }
})
