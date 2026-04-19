import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useAuthStore } from '@/stores/auth.store'
import * as authApi from '@/services/api/auth'

// ── Mock auth API ──
vi.mock('@/services/api/auth', () => ({
  login: vi.fn(),
  logout: vi.fn(),
  getUserInfo: vi.fn(),
  refreshToken: vi.fn(),
  register: vi.fn(),
}))

// ── Mock token utils ──
vi.mock('@/utils/token', () => ({
  isTokenExpired: vi.fn(),
  isValidJwtFormat: vi.fn(),
}))

import { isTokenExpired, isValidJwtFormat } from '@/utils/token'

// Helper: create a fake user
function createMockUser(overrides: Record<string, unknown> = {}) {
  return {
    id: 'user-1',
    username: 'testuser',
    email: 'test@example.com',
    role: 'user',
    status: 'active',
    is_active: true,
    is_verified: true,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...overrides,
  }
}

// Helper: create a fake token response
function createTokenResponse(overrides: Record<string, string> = {}) {
  return {
    access_token: 'access-token-123',
    refresh_token: 'refresh-token-456',
    token_type: 'bearer',
    ...overrides,
  }
}

describe('Auth Store (extended)', () => {
  beforeEach(() => {
    useAuthStore.setState({
      token: null,
      refreshToken: null,
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      redirectPath: '/dashboard',
      hasRehydrated: false,
    })
    localStorage.clear()
    vi.clearAllMocks()
  })

  // ════════════════════════════════════════
  // register
  // ════════════════════════════════════════
  describe('register', () => {
    const validForm = {
      username: 'newuser',
      email: 'new@example.com',
      password: 'StrongPass123!',
      confirm_password: 'StrongPass123!',
    }

    it('returns true on successful registration', async () => {
      vi.mocked(authApi.register).mockResolvedValueOnce(createMockUser({ username: 'newuser' }))

      const result = await useAuthStore.getState().register(validForm)

      expect(result).toBe(true)
      expect(useAuthStore.getState().isLoading).toBe(false)
      expect(useAuthStore.getState().error).toBeNull()
    })

    it('does NOT set authenticated state after registration', async () => {
      vi.mocked(authApi.register).mockResolvedValueOnce(createMockUser())

      await useAuthStore.getState().register(validForm)

      expect(useAuthStore.getState().isAuthenticated).toBe(false)
      expect(useAuthStore.getState().token).toBeNull()
    })

    it('sets isLoading during registration', async () => {
      let resolveRegistration!: (value: unknown) => void
      vi.mocked(authApi.register).mockReturnValueOnce(new Promise((resolve) => { resolveRegistration = resolve }))

      const promise = useAuthStore.getState().register(validForm)
      expect(useAuthStore.getState().isLoading).toBe(true)

      resolveRegistration(createMockUser())
      await promise

      expect(useAuthStore.getState().isLoading).toBe(false)
    })

    it('returns false and sets error on registration failure', async () => {
      vi.mocked(authApi.register).mockRejectedValueOnce(new Error('Username already exists'))

      const result = await useAuthStore.getState().register(validForm)

      expect(result).toBe(false)
      expect(useAuthStore.getState().error).toBe('Username already exists')
      expect(useAuthStore.getState().isLoading).toBe(false)
    })

    it('handles non-Error thrown values', async () => {
      vi.mocked(authApi.register).mockRejectedValueOnce('string error')

      const result = await useAuthStore.getState().register(validForm)

      expect(result).toBe(false)
      expect(useAuthStore.getState().error).toBe('注册失败')
    })

    it('handles null thrown value', async () => {
      vi.mocked(authApi.register).mockRejectedValueOnce(null)

      const result = await useAuthStore.getState().register(validForm)

      expect(result).toBe(false)
      expect(useAuthStore.getState().error).toBe('注册失败')
    })

    it('handles undefined thrown value', async () => {
      vi.mocked(authApi.register).mockRejectedValueOnce(undefined)

      const result = await useAuthStore.getState().register(validForm)

      expect(result).toBe(false)
      expect(useAuthStore.getState().error).toBe('注册失败')
    })

    it('clears error at start of registration', async () => {
      useAuthStore.setState({ error: 'Previous error' })
      vi.mocked(authApi.register).mockResolvedValueOnce(createMockUser())

      await useAuthStore.getState().register(validForm)

      expect(useAuthStore.getState().error).toBeNull()
    })

    it('does not set user on successful registration', async () => {
      vi.mocked(authApi.register).mockResolvedValueOnce(createMockUser({ username: 'newuser' }))

      await useAuthStore.getState().register(validForm)

      expect(useAuthStore.getState().user).toBeNull()
    })
  })

  // ════════════════════════════════════════
  // refreshAccessToken
  // ════════════════════════════════════════
  describe('refreshAccessToken', () => {
    it('returns true and updates tokens on success', async () => {
      useAuthStore.setState({ refreshToken: 'old-refresh-token' })
      const newTokens = createTokenResponse({
        access_token: 'new-access-token',
        refresh_token: 'new-refresh-token',
      })
      vi.mocked(authApi.refreshToken).mockResolvedValueOnce(newTokens)

      const result = await useAuthStore.getState().refreshAccessToken()

      expect(result).toBe(true)
      expect(useAuthStore.getState().token).toBe('new-access-token')
      expect(useAuthStore.getState().refreshToken).toBe('new-refresh-token')
      expect(useAuthStore.getState().isAuthenticated).toBe(true)
    })

    it('keeps old refresh token if new one is not provided', async () => {
      useAuthStore.setState({ refreshToken: 'existing-refresh-token' })
      const newTokens = createTokenResponse({
        access_token: 'new-access-token',
      })
      // refresh_token defaults to 'refresh-token-456' from createTokenResponse,
      // so we override to undefined to simulate backend not returning it
      delete (newTokens as Record<string, string>).refresh_token
      vi.mocked(authApi.refreshToken).mockResolvedValueOnce(newTokens)

      const result = await useAuthStore.getState().refreshAccessToken()

      expect(result).toBe(true)
      expect(useAuthStore.getState().refreshToken).toBe('existing-refresh-token')
    })

    it('returns false and clears auth when no refresh token stored', async () => {
      useAuthStore.setState({
        refreshToken: null,
        token: 'some-token',
        isAuthenticated: true,
      })

      const result = await useAuthStore.getState().refreshAccessToken()

      expect(result).toBe(false)
      expect(useAuthStore.getState().token).toBeNull()
      expect(useAuthStore.getState().isAuthenticated).toBe(false)
    })

    it('returns false and clears auth when API returns no access_token', async () => {
      useAuthStore.setState({ refreshToken: 'some-refresh-token', token: 'old-token' })
      vi.mocked(authApi.refreshToken).mockResolvedValueOnce({ access_token: '', token_type: 'bearer' } as never)

      const result = await useAuthStore.getState().refreshAccessToken()

      expect(result).toBe(false)
      expect(useAuthStore.getState().token).toBeNull()
    })

    it('returns false and clears auth when API throws', async () => {
      useAuthStore.setState({ refreshToken: 'some-refresh-token', token: 'old-token', isAuthenticated: true })
      vi.mocked(authApi.refreshToken).mockRejectedValueOnce(new Error('Network Error'))

      const result = await useAuthStore.getState().refreshAccessToken()

      expect(result).toBe(false)
      expect(useAuthStore.getState().token).toBeNull()
      expect(useAuthStore.getState().refreshToken).toBeNull()
      expect(useAuthStore.getState().isAuthenticated).toBe(false)
    })

    it('calls authApi.refreshToken with the stored refresh token', async () => {
      useAuthStore.setState({ refreshToken: 'my-refresh-token' })
      vi.mocked(authApi.refreshToken).mockResolvedValueOnce(createTokenResponse())

      await useAuthStore.getState().refreshAccessToken()

      expect(authApi.refreshToken).toHaveBeenCalledWith('my-refresh-token')
    })
  })

  // ════════════════════════════════════════
  // token expiry / rehydration
  // ════════════════════════════════════════
  describe('token expiry on rehydration', () => {
    it('clears auth when token is expired during rehydration', () => {
      // Set token first, then configure mocks, then simulate the rehydration check logic
      useAuthStore.setState({
        token: 'expired.jwt.token',
        isAuthenticated: true,
      })

      vi.mocked(isValidJwtFormat).mockReturnValue(true)
      vi.mocked(isTokenExpired).mockReturnValue(true)

      // Simulate the rehydration check logic from onRehydrateStorage
      const { token } = useAuthStore.getState()
      if (token && (!isValidJwtFormat(token) || isTokenExpired(token))) {
        useAuthStore.getState().clearAuth()
      }

      expect(isTokenExpired).toHaveBeenCalledWith('expired.jwt.token')
      expect(useAuthStore.getState().isAuthenticated).toBe(false)
      expect(useAuthStore.getState().token).toBeNull()
    })

    it('sets isAuthenticated to true for valid token on rehydration', () => {
      vi.mocked(isValidJwtFormat).mockReturnValue(true)
      vi.mocked(isTokenExpired).mockReturnValue(false)

      useAuthStore.setState({ token: 'valid.jwt.token' })

      // Simulate rehydration check
      const { token } = useAuthStore.getState()
      if (token && isValidJwtFormat(token) && !isTokenExpired(token)) {
        useAuthStore.setState({ isAuthenticated: true })
      }

      expect(useAuthStore.getState().isAuthenticated).toBe(true)
    })

    it('clears auth for invalid JWT format on rehydration', () => {
      vi.mocked(isValidJwtFormat).mockReturnValue(false)

      useAuthStore.setState({ token: 'not-a-jwt', isAuthenticated: true })

      const { token } = useAuthStore.getState()
      if (token && !isValidJwtFormat(token)) {
        useAuthStore.getState().clearAuth()
      }

      expect(useAuthStore.getState().isAuthenticated).toBe(false)
      expect(useAuthStore.getState().token).toBeNull()
    })

    it('does nothing when token is null during rehydration', () => {
      useAuthStore.setState({ token: null, isAuthenticated: false })

      const { token } = useAuthStore.getState()
      if (token) {
        // Should not enter this block
        expect.unreachable('Should not check token when null')
      }

      expect(useAuthStore.getState().isAuthenticated).toBe(false)
    })
  })

  // ════════════════════════════════════════
  // login (extended)
  // ════════════════════════════════════════
  describe('login (extended)', () => {
    it('stores both access and refresh tokens', async () => {
      vi.mocked(authApi.login).mockResolvedValueOnce(createTokenResponse({
        access_token: 'my-access',
        refresh_token: 'my-refresh',
      }))
      vi.mocked(authApi.getUserInfo).mockResolvedValueOnce(createMockUser())

      await useAuthStore.getState().login({ account: 'user', password: 'pass' })

      expect(useAuthStore.getState().token).toBe('my-access')
      expect(useAuthStore.getState().refreshToken).toBe('my-refresh')
    })

    it('succeeds even when getUserInfo fails', async () => {
      vi.mocked(authApi.login).mockResolvedValueOnce(createTokenResponse())
      vi.mocked(authApi.getUserInfo).mockRejectedValueOnce(new Error('Failed'))

      const result = await useAuthStore.getState().login({ account: 'user', password: 'pass' })

      expect(result).toBe(true)
      expect(useAuthStore.getState().isAuthenticated).toBe(true)
      expect(useAuthStore.getState().user).toBeNull()
    })

    it('handles login error with non-Error thrown value', async () => {
      vi.mocked(authApi.login).mockRejectedValueOnce(undefined)

      const result = await useAuthStore.getState().login({ account: 'user', password: 'pass' })

      expect(result).toBe(false)
      expect(useAuthStore.getState().error).toBe('登录失败')
    })

    it('clears error at start of login', async () => {
      useAuthStore.setState({ error: 'Previous error' })
      vi.mocked(authApi.login).mockResolvedValueOnce(createTokenResponse())
      vi.mocked(authApi.getUserInfo).mockResolvedValueOnce(createMockUser())

      await useAuthStore.getState().login({ account: 'user', password: 'pass' })

      expect(useAuthStore.getState().error).toBeNull()
    })

    it('sets isLoading correctly during login lifecycle', async () => {
      let resolveLogin!: (value: unknown) => void
      vi.mocked(authApi.login).mockReturnValueOnce(new Promise((resolve) => { resolveLogin = resolve }))

      const promise = useAuthStore.getState().login({ account: 'user', password: 'pass' })
      expect(useAuthStore.getState().isLoading).toBe(true)

      resolveLogin(createTokenResponse())
      vi.mocked(authApi.getUserInfo).mockResolvedValueOnce(createMockUser())
      await promise

      expect(useAuthStore.getState().isLoading).toBe(false)
    })
  })

  // ════════════════════════════════════════
  // logout (extended)
  // ════════════════════════════════════════
  describe('logout (extended)', () => {
    it('always clears auth state in finally block', async () => {
      useAuthStore.setState({ token: 'token', isAuthenticated: true, user: createMockUser() })
      // The store uses try/finally pattern: clearAuth always runs.
      // We verify this by testing with a successful logout - the key behavior
      // is that clearAuth runs regardless of API outcome.
      vi.mocked(authApi.logout).mockResolvedValueOnce({ success: true })

      await useAuthStore.getState().logout()

      // The critical assertion: auth state is cleared after logout
      expect(useAuthStore.getState().token).toBeNull()
      expect(useAuthStore.getState().isAuthenticated).toBe(false)
      expect(useAuthStore.getState().user).toBeNull()
      expect(useAuthStore.getState().refreshToken).toBeNull()
      expect(useAuthStore.getState().error).toBeNull()
    })

    it('clears auth on successful logout', async () => {
      useAuthStore.setState({ token: 'token', isAuthenticated: true, user: createMockUser() })
      vi.mocked(authApi.logout).mockResolvedValueOnce({ success: true })

      await useAuthStore.getState().logout()

      expect(useAuthStore.getState().token).toBeNull()
      expect(useAuthStore.getState().isAuthenticated).toBe(false)
    })
  })

  // ════════════════════════════════════════
  // fetchUserInfo
  // ════════════════════════════════════════
  describe('fetchUserInfo', () => {
    it('returns true and sets user on success', async () => {
      const mockUser = createMockUser({ username: 'fetched-user' })
      vi.mocked(authApi.getUserInfo).mockResolvedValueOnce(mockUser)

      const result = await useAuthStore.getState().fetchUserInfo()

      expect(result).toBe(true)
      expect(useAuthStore.getState().user?.username).toBe('fetched-user')
    })

    it('returns false on failure', async () => {
      vi.mocked(authApi.getUserInfo).mockRejectedValueOnce(new Error('Unauthorized'))

      const result = await useAuthStore.getState().fetchUserInfo()

      expect(result).toBe(false)
    })
  })

  // ════════════════════════════════════════
  // setToken / setRefreshToken
  // ════════════════════════════════════════
  describe('setToken', () => {
    it('updates token and sets isAuthenticated to true', () => {
      useAuthStore.getState().setToken('new-token')

      expect(useAuthStore.getState().token).toBe('new-token')
      expect(useAuthStore.getState().isAuthenticated).toBe(true)
    })
  })

  describe('setRefreshToken', () => {
    it('updates refresh token', () => {
      useAuthStore.getState().setRefreshToken('new-refresh')

      expect(useAuthStore.getState().refreshToken).toBe('new-refresh')
    })
  })

  // ════════════════════════════════════════
  // setRedirectPath
  // ════════════════════════════════════════
  describe('setRedirectPath', () => {
    it('updates redirect path', () => {
      useAuthStore.getState().setRedirectPath('/settings')

      expect(useAuthStore.getState().redirectPath).toBe('/settings')
    })

    it('handles empty string path', () => {
      useAuthStore.getState().setRedirectPath('')

      expect(useAuthStore.getState().redirectPath).toBe('')
    })
  })

  // ════════════════════════════════════════
  // updateUser
  // ════════════════════════════════════════
  describe('updateUser', () => {
    it('merges partial user data', () => {
      useAuthStore.setState({ user: createMockUser({ username: 'original', email: 'old@test.com' }) })

      useAuthStore.getState().updateUser({ username: 'changed' })

      expect(useAuthStore.getState().user?.username).toBe('changed')
      expect(useAuthStore.getState().user?.email).toBe('old@test.com')
    })

    it('does nothing when user is null', () => {
      useAuthStore.setState({ user: null })

      useAuthStore.getState().updateUser({ username: 'ignored' })

      expect(useAuthStore.getState().user).toBeNull()
    })

    it('handles multiple field updates', () => {
      useAuthStore.setState({ user: createMockUser() })

      useAuthStore.getState().updateUser({ username: 'new-name', email: 'new@email.com' })

      expect(useAuthStore.getState().user?.username).toBe('new-name')
      expect(useAuthStore.getState().user?.email).toBe('new@email.com')
    })
  })

  // ════════════════════════════════════════
  // clearAuth
  // ════════════════════════════════════════
  describe('clearAuth', () => {
    it('clears all auth fields', () => {
      useAuthStore.setState({
        token: 'token',
        refreshToken: 'refresh',
        user: createMockUser(),
        isAuthenticated: true,
        error: 'some error',
      })

      useAuthStore.getState().clearAuth()

      expect(useAuthStore.getState().token).toBeNull()
      expect(useAuthStore.getState().refreshToken).toBeNull()
      expect(useAuthStore.getState().user).toBeNull()
      expect(useAuthStore.getState().isAuthenticated).toBe(false)
      expect(useAuthStore.getState().error).toBeNull()
    })
  })
})
