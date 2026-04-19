import { describe, it, expect, vi, beforeEach } from 'vitest'
import { checkAuth, getRouteTitle } from '@/router/guards'
import { isTokenExpired, isValidJwtFormat } from '@/utils/token'

// ── Mock dependencies ──
vi.mock('@/stores/auth.store', () => {
  const state = {
    token: null as string | null,
  }
  return {
    useAuthStore: {
      getState: () => state,
      setState: (newState: { token?: string | null }) => {
        if (newState.token !== undefined) {
          state.token = newState.token
        }
      },
    },
  }
})

// We need to mock token utils to control the auth check behavior
vi.mock('@/utils/token', () => ({
  isTokenExpired: vi.fn(),
  isValidJwtFormat: vi.fn(),
}))

import { useAuthStore } from '@/stores/auth.store'

// Helper: create a fake JWT string (3 parts separated by dots)
function fakeJwt(payload: Record<string, unknown> = {}): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const body = btoa(JSON.stringify(payload))
  return `${header}.${body}.fake-signature`
}

describe('Route Guards', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuthStore.setState({ token: null })
  })

  // ════════════════════════════════════════
  // checkAuth
  // ════════════════════════════════════════
  describe('checkAuth', () => {
    it('returns false when token is null', () => {
      useAuthStore.setState({ token: null })
      vi.mocked(isValidJwtFormat).mockReturnValue(false)

      expect(checkAuth()).toBe(false)
    })

    it('returns false when token is empty string', () => {
      useAuthStore.setState({ token: '' })
      vi.mocked(isValidJwtFormat).mockReturnValue(false)

      expect(checkAuth()).toBe(false)
    })

    it('returns false when token format is invalid', () => {
      useAuthStore.setState({ token: 'not-a-jwt' })
      vi.mocked(isValidJwtFormat).mockReturnValue(false)

      expect(checkAuth()).toBe(false)
      expect(isValidJwtFormat).toHaveBeenCalledWith('not-a-jwt')
    })

    it('returns false when token is valid format but expired', () => {
      const token = fakeJwt({ exp: 1000 })
      useAuthStore.setState({ token })
      vi.mocked(isValidJwtFormat).mockReturnValue(true)
      vi.mocked(isTokenExpired).mockReturnValue(true)

      expect(checkAuth()).toBe(false)
      expect(isTokenExpired).toHaveBeenCalledWith(token)
    })

    it('returns true when token is valid and not expired', () => {
      const token = fakeJwt({ exp: Date.now() / 1000 + 3600 })
      useAuthStore.setState({ token })
      vi.mocked(isValidJwtFormat).mockReturnValue(true)
      vi.mocked(isTokenExpired).mockReturnValue(false)

      expect(checkAuth()).toBe(true)
    })

    it('calls isValidJwtFormat with the stored token', () => {
      const token = fakeJwt({ sub: 'user123' })
      useAuthStore.setState({ token })
      vi.mocked(isValidJwtFormat).mockReturnValue(true)
      vi.mocked(isTokenExpired).mockReturnValue(false)

      checkAuth()

      expect(isValidJwtFormat).toHaveBeenCalledWith(token)
    })

    it('short-circuits: does not check expiry when format is invalid', () => {
      useAuthStore.setState({ token: 'bad-token' })
      vi.mocked(isValidJwtFormat).mockReturnValue(false)

      checkAuth()

      expect(isTokenExpired).not.toHaveBeenCalled()
    })
  })

  // ════════════════════════════════════════
  // getRouteTitle
  // ════════════════════════════════════════
  describe('getRouteTitle', () => {
    it('returns base title when no route name provided', () => {
      expect(getRouteTitle()).toBe('TradingAgents')
    })

    it('returns base title when route name is undefined', () => {
      expect(getRouteTitle(undefined)).toBe('TradingAgents')
    })

    it('returns formatted title with route name', () => {
      expect(getRouteTitle('Dashboard')).toBe('Dashboard | TradingAgents')
    })

    it('handles empty string route name', () => {
      expect(getRouteTitle('')).toBe('TradingAgents')
    })

    it('handles route name with special characters', () => {
      expect(getRouteTitle('Stock Analysis (A股)')).toBe('Stock Analysis (A股) | TradingAgents')
    })

    it('handles long route names', () => {
      const longName = 'Very Long Route Name That Describes A Complex Page'
      expect(getRouteTitle(longName)).toBe(`${longName} | TradingAgents`)
    })
  })
})
