import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { User } from '@/core/auth/models'
import { httpClient } from '@/core/api/http'
import { eventBus, EventTypes } from '@/core/events/bus'

interface LoginData {
  email: string
  password: string
}

interface RegisterData {
  email: string
  username: string
  password: string
  full_name?: string
}

export const useUserStore = defineStore('user', () => {
  // 状态
  const user = ref<User | null>(null)
  const token = ref<string | null>(null)
  const loading = ref(false)

  // 计算属性
  const isAuthenticated = computed(() => !!token.value && !!user.value)

  // Actions
  async function login(credentials: LoginData) {
    try {
      loading.value = true
      eventBus.emit(EventTypes.LOADING_START)

      const response = await httpClient.post('/auth/login', {
        email: credentials.email,
        password: credentials.password
      })

      if (response.token && response.user) {
        token.value = response.token
        user.value = response.user

        // 保存到localStorage
        localStorage.setItem('token', response.token)
        localStorage.setItem('user', JSON.stringify(response.user))

        // 发布登录事件
        eventBus.emit(EventTypes.USER_LOGIN, {
          userId: response.user.id,
          email: response.user.email
        })

        return { success: true, user: response.user }
      }

      return { success: false, message: 'Login failed' }
    } catch (error: any) {
      const message = error.message || 'Login failed'
      eventBus.emit(EventTypes.NOTIFICATION_SHOW, {
        type: 'error',
        title: '登录失败',
        message
      })
      return { success: false, message }
    } finally {
      loading.value = false
      eventBus.emit(EventTypes.LOADING_END)
    }
  }

  async function register(userData: RegisterData) {
    try {
      loading.value = true
      eventBus.emit(EventTypes.LOADING_START)

      const response = await httpClient.post('/auth/register', userData)

      if (response.user) {
        // 发布注册事件
        eventBus.emit(EventTypes.USER_REGISTER, {
          userId: response.user.id,
          email: response.user.email,
          username: response.user.username
        })

        eventBus.emit(EventTypes.NOTIFICATION_SHOW, {
          type: 'success',
          title: '注册成功',
          message: '请登录您的账户'
        })

        return { success: true, user: response.user }
      }

      return { success: false, message: 'Registration failed' }
    } catch (error: any) {
      const message = error.message || 'Registration failed'
      eventBus.emit(EventTypes.NOTIFICATION_SHOW, {
        type: 'error',
        title: '注册失败',
        message
      })
      return { success: false, message }
    } finally {
      loading.value = false
      eventBus.emit(EventTypes.LOADING_END)
    }
  }

  async function checkAuth() {
    try {
      const savedToken = localStorage.getItem('token')
      if (!savedToken) {
        return false
      }

      token.value = savedToken

      // 验证token并获取用户信息
      const response = await httpClient.get('/auth/me')
      if (response) {
        user.value = response
        localStorage.setItem('user', JSON.stringify(response))
        return true
      }
    } catch (error) {
      console.error('Auth check failed:', error)
      logout()
      return false
    }
  }

  async function updateProfile(updateData: Partial<User>) {
    try {
      loading.value = true
      eventBus.emit(EventTypes.LOADING_START)

      const response = await httpClient.put('/auth/me', updateData)
      if (response) {
        user.value = response
        localStorage.setItem('user', JSON.stringify(response))

        eventBus.emit(EventTypes.NOTIFICATION_SHOW, {
          type: 'success',
          title: '更新成功',
          message: '个人资料已更新'
        })

        return { success: true, user: response }
      }

      return { success: false, message: 'Update failed' }
    } catch (error: any) {
      const message = error.message || 'Update failed'
      eventBus.emit(EventTypes.NOTIFICATION_SHOW, {
        type: 'error',
        title: '更新失败',
        message
      })
      return { success: false, message }
    } finally {
      loading.value = false
      eventBus.emit(EventTypes.LOADING_END)
    }
  }

  async function changePassword(currentPassword: string, newPassword: string) {
    try {
      loading.value = true
      eventBus.emit(EventTypes.LOADING_START)

      const response = await httpClient.post('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword
      })

      if (response) {
        eventBus.emit(EventTypes.NOTIFICATION_SHOW, {
          type: 'success',
          title: '密码修改成功',
          message: '请使用新密码登录'
        })

        return { success: true }
      }

      return { success: false, message: 'Password change failed' }
    } catch (error: any) {
      const message = error.message || 'Password change failed'
      eventBus.emit(EventTypes.NOTIFICATION_SHOW, {
        type: 'error',
        title: '密码修改失败',
        message
      })
      return { success: false, message }
    } finally {
      loading.value = false
      eventBus.emit(EventTypes.LOADING_END)
    }
  }

  async function logout() {
    try {
      if (token.value) {
        await httpClient.post('/auth/logout')
      }
    } catch (error) {
      console.error('Logout error:', error)
    } finally {
      // 清除本地状态
      user.value = null
      token.value = null

      // 清除localStorage
      localStorage.removeItem('token')
      localStorage.removeItem('user')

      // 发布登出事件
      eventBus.emit(EventTypes.USER_LOGOUT, {})
    }
  }

  // 初始化时从localStorage恢复用户状态
  function initializeFromStorage() {
    try {
      const savedToken = localStorage.getItem('token')
      const savedUser = localStorage.getItem('user')

      if (savedToken && savedUser) {
        token.value = savedToken
        user.value = JSON.parse(savedUser)
      }
    } catch (error) {
      console.error('Failed to restore user state from storage:', error)
      logout()
    }
  }

  return {
    // 状态
    user: computed(() => user.value),
    token: computed(() => token.value),
    loading: computed(() => loading.value),
    isAuthenticated,

    // Actions
    login,
    register,
    checkAuth,
    updateProfile,
    changePassword,
    logout,
    initializeFromStorage
  }
})