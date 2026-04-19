import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import * as authApi from '@/services/api/auth'
import type { User, LoginForm, RegisterForm } from '@/types/auth.types'
import { isTokenExpired, isValidJwtFormat } from '@/utils/token'

interface AuthState {
  token: string | null
  refreshToken: string | null
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  error: string | null
  redirectPath: string
  hasRehydrated: boolean
}

interface AuthActions {
  login: (form: LoginForm) => Promise<boolean>
  register: (form: RegisterForm) => Promise<boolean>
  logout: () => Promise<void>
  fetchUserInfo: () => Promise<boolean>
  refreshAccessToken: () => Promise<boolean>
  clearAuth: () => void
  setRedirectPath: (path: string) => void
  updateUser: (user: Partial<User>) => void
  /** 由 HTTP 拦截器调用，更新 token（不触发持久化写入循环） */
  setToken: (token: string) => void
  setRefreshToken: (token: string) => void
}

type AuthStore = AuthState & AuthActions

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      token: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      redirectPath: '/dashboard',
      hasRehydrated: false,

      // 后端 /api/users/login 直接返回 {access_token, refresh_token, token_type}
      login: async (form) => {
        set({ isLoading: true, error: null })
        try {
          const data = await authApi.login(form)
          set({
            token: data.access_token,
            refreshToken: data.refresh_token,
            isAuthenticated: true,
            isLoading: false,
          })
          // 登录成功后获取用户信息
          try {
            const user = await authApi.getUserInfo()
            set({ user })
          } catch {
            // 获取用户信息失败不影响登录成功
          }
          return true
        } catch (err) {
          const message = err instanceof Error ? err.message : '登录失败'
          set({ error: message, isLoading: false })
          return false
        }
      },

      // 后端 /api/users/register 直接返回 UserModel
      register: async (form) => {
        set({ isLoading: true, error: null })
        try {
          await authApi.register(form)
          set({ isLoading: false })
          return true
        } catch (err) {
          const message = err instanceof Error ? err.message : '注册失败'
          set({ error: message, isLoading: false })
          return false
        }
      },

      logout: async () => {
        try {
          await authApi.logout()
        } finally {
          get().clearAuth()
        }
      },

      // 后端 /api/users/me 直接返回 UserModel
      fetchUserInfo: async () => {
        try {
          const user = await authApi.getUserInfo()
          set({ user })
          return true
        } catch {
          return false
        }
      },

      // 后端 /api/users/refresh-token 直接返回 {access_token, refresh_token, token_type}
      refreshAccessToken: async () => {
        const currentRefreshToken = get().refreshToken
        if (!currentRefreshToken) {
          get().clearAuth()
          return false
        }

        try {
          const data = await authApi.refreshToken(currentRefreshToken)
          if (data?.access_token) {
            set({
              token: data.access_token,
              refreshToken: data.refresh_token ?? currentRefreshToken,
              isAuthenticated: true,
            })
            return true
          }
          get().clearAuth()
          return false
        } catch {
          get().clearAuth()
          return false
        }
      },

      clearAuth: () => {
        set({
          token: null,
          refreshToken: null,
          user: null,
          isAuthenticated: false,
          error: null,
        })
      },

      setRedirectPath: (path) => set({ redirectPath: path }),

      setToken: (token: string) => set({ token, isAuthenticated: true }),

      setRefreshToken: (token: string) => set({ refreshToken: token }),

      updateUser: (partial) => {
        const { user } = get()
        if (user) {
          set({ user: { ...user, ...partial } })
        }
      },
    }),
    {
      name: 'auth-store',
      partialize: (state) => ({
        token: state.token,
        refreshToken: state.refreshToken,
        user: state.user,
        redirectPath: state.redirectPath,
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          state.hasRehydrated = true
          if (state.token) {
            // 初始化时检查 token 是否有效
            if (!isValidJwtFormat(state.token) || isTokenExpired(state.token)) {
              state.clearAuth()
            } else {
              state.isAuthenticated = true
            }
          }
        }
      },
    }
  )
)

/**
 * 初始化认证刷新定时器（应在 App.tsx useEffect 中调用）
 */
export function startAuthRefreshTimer(): () => void {
  const check = async () => {
    const { token, refreshAccessToken, clearAuth } = useAuthStore.getState()
    if (!token) return

    // 如果 token 即将在 5 分钟内过期，提前刷新
    const { getTokenRemainingTime } = await import('@/utils/token')
    const remaining = getTokenRemainingTime(token)
    if (remaining > 0 && remaining < 300) {
      const success = await refreshAccessToken()
      if (!success) clearAuth()
    } else if (remaining <= 0) {
      clearAuth()
    }
  }

  check()
  const timer = setInterval(check, 60000)
  return () => clearInterval(timer)
}
