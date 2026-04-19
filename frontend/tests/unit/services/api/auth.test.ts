import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { Mock } from 'vitest'

// ── Mock httpClient ──
const mockPost = vi.fn()
const mockGet = vi.fn()
const mockPut = vi.fn()

vi.mock('@/services/http/client', () => ({
  httpClient: {
    post: (...args: unknown[]) => mockPost(...args),
    get: (...args: unknown[]) => mockGet(...args),
    put: (...args: unknown[]) => mockPut(...args),
  },
}))

// Import after mocks
import * as authApi from '@/services/api/auth'

describe('Auth API', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  // ── Helper: create mock axios response wrapper ──
  function mockResponse(data: unknown) {
    return Promise.resolve({ data })
  }

  describe('login', () => {
    it('calls POST /api/users/login with form data and skipAuth', async () => {
      const tokenResponse = {
        access_token: 'jwt-access-token',
        refresh_token: 'jwt-refresh-token',
        token_type: 'bearer',
      }
      mockPost.mockReturnValueOnce(mockResponse(tokenResponse))

      const form = { account: 'user1', password: 'pass123' }
      const result = await authApi.login(form)

      expect(mockPost).toHaveBeenCalledWith('/api/users/login', form, { skipAuth: true })
      expect(result).toEqual(tokenResponse)
      expect(result.access_token).toBe('jwt-access-token')
    })

    it('propagates error on login failure', async () => {
      mockPost.mockRejectedValueOnce(new Error('Invalid credentials'))

      const form = { account: 'user1', password: 'wrong' }

      await expect(authApi.login(form)).rejects.toThrow('Invalid credentials')
    })

    it('handles network error during login', async () => {
      mockPost.mockRejectedValueOnce(new Error('Network Error'))

      await expect(authApi.login({ account: 'a', password: 'b' })).rejects.toThrow('Network Error')
    })
  })

  describe('register', () => {
    it('calls POST /api/users/register with form data and skipAuth', async () => {
      const userResponse = {
        id: 'user-123',
        username: 'newuser',
        email: 'new@example.com',
        role: 'user',
        status: 'active',
        is_active: true,
        is_verified: false,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      }
      mockPost.mockReturnValueOnce(mockResponse(userResponse))

      const form = {
        username: 'newuser',
        email: 'new@example.com',
        password: 'Password123!',
        confirm_password: 'Password123!',
      }
      const result = await authApi.register(form)

      expect(mockPost).toHaveBeenCalledWith('/api/users/register', form, { skipAuth: true })
      expect(result).toEqual(userResponse)
      expect(result.username).toBe('newuser')
    })

    it('propagates error on duplicate registration', async () => {
      mockPost.mockRejectedValueOnce(new Error('Username already exists'))

      const form = {
        username: 'duplicate',
        email: 'dup@example.com',
        password: 'Password123!',
        confirm_password: 'Password123!',
      }

      await expect(authApi.register(form)).rejects.toThrow('Username already exists')
    })

    it('handles validation error from backend', async () => {
      mockPost.mockRejectedValueOnce(new Error('Password too short'))

      await expect(
        authApi.register({ username: 'u', email: 'e@e.com', password: '1', confirm_password: '1' })
      ).rejects.toThrow('Password too short')
    })
  })

  describe('logout', () => {
    it('calls POST /api/users/logout', async () => {
      mockPost.mockReturnValueOnce(mockResponse({ success: true }))

      const result = await authApi.logout()

      expect(mockPost).toHaveBeenCalledWith('/api/users/logout')
      expect(result).toEqual({ success: true })
    })

    it('propagates error on logout failure', async () => {
      mockPost.mockRejectedValueOnce(new Error('Server error'))

      await expect(authApi.logout()).rejects.toThrow('Server error')
    })
  })

  describe('getUserInfo', () => {
    it('calls GET /api/users/me and returns user data', async () => {
      const userResponse = {
        id: 'user-123',
        username: 'testuser',
        email: 'test@example.com',
        role: 'user',
        status: 'active',
        is_active: true,
        is_verified: true,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      }
      mockGet.mockReturnValueOnce(mockResponse(userResponse))

      const result = await authApi.getUserInfo()

      expect(mockGet).toHaveBeenCalledWith('/api/users/me')
      expect(result).toEqual(userResponse)
    })

    it('propagates error when not authenticated', async () => {
      mockGet.mockRejectedValueOnce(new Error('Unauthorized'))

      await expect(authApi.getUserInfo()).rejects.toThrow('Unauthorized')
    })
  })

  describe('updateUserInfo', () => {
    it('calls PUT /api/users/me with partial data', async () => {
      const updatedUser = {
        id: 'user-123',
        username: 'updated-name',
        email: 'test@example.com',
        role: 'user',
        status: 'active',
        is_active: true,
        is_verified: true,
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-02T00:00:00Z',
      }
      mockPut.mockReturnValueOnce(mockResponse(updatedUser))

      const result = await authApi.updateUserInfo({ username: 'updated-name' })

      expect(mockPut).toHaveBeenCalledWith('/api/users/me', { username: 'updated-name' })
      expect(result.username).toBe('updated-name')
    })

    it('handles update failure', async () => {
      mockPut.mockRejectedValueOnce(new Error('Forbidden'))

      await expect(authApi.updateUserInfo({ username: 'hack' })).rejects.toThrow('Forbidden')
    })
  })

  describe('requestPasswordReset', () => {
    it('calls POST /api/users/request-reset with email and skipAuth', async () => {
      const resetResponse = { success: true, message: 'Reset email sent' }
      mockPost.mockReturnValueOnce(mockResponse(resetResponse))

      const result = await authApi.requestPasswordReset({ email: 'user@example.com' })

      expect(mockPost).toHaveBeenCalledWith('/api/users/request-reset', { email: 'user@example.com' }, { skipAuth: true })
      expect(result.success).toBe(true)
      expect(result.message).toBe('Reset email sent')
    })

    it('handles non-existent email gracefully', async () => {
      mockPost.mockRejectedValueOnce(new Error('Email not found'))

      await expect(authApi.requestPasswordReset({ email: 'none@none.com' })).rejects.toThrow('Email not found')
    })
  })

  describe('refreshToken', () => {
    it('calls POST /api/users/refresh-token with refresh token and skipAuth', async () => {
      const tokenResponse = {
        access_token: 'new-access-token',
        refresh_token: 'new-refresh-token',
        token_type: 'bearer',
      }
      mockPost.mockReturnValueOnce(mockResponse(tokenResponse))

      const result = await authApi.refreshToken('old-refresh-token')

      expect(mockPost).toHaveBeenCalledWith(
        '/api/users/refresh-token',
        { refresh_token: 'old-refresh-token' },
        { skipAuth: true }
      )
      expect(result).toEqual(tokenResponse)
      expect(result.access_token).toBe('new-access-token')
    })

    it('propagates error when refresh token is invalid', async () => {
      mockPost.mockRejectedValueOnce(new Error('Invalid refresh token'))

      await expect(authApi.refreshToken('invalid-token')).rejects.toThrow('Invalid refresh token')
    })

    it('handles expired refresh token', async () => {
      mockPost.mockRejectedValueOnce(new Error('Token expired'))

      await expect(authApi.refreshToken('expired-token')).rejects.toThrow('Token expired')
    })

    it('handles empty refresh token', async () => {
      mockPost.mockRejectedValueOnce(new Error('Missing refresh token'))

      await expect(authApi.refreshToken('')).rejects.toThrow('Missing refresh token')
    })
  })

  describe('edge cases', () => {
    it('login handles null response gracefully', async () => {
      mockPost.mockReturnValueOnce(mockResponse(null))

      const result = await authApi.login({ account: 'u', password: 'p' })
      expect(result).toBeNull()
    })

    it('getUserInfo handles empty response object', async () => {
      mockGet.mockReturnValueOnce(mockResponse({}))

      const result = await authApi.getUserInfo()
      expect(result).toEqual({})
    })
  })
})
