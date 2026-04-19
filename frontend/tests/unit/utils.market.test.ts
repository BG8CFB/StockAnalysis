import { describe, it, expect } from 'vitest'
import { detectMarket, getMarketName, getMarketColors } from '@/utils/market'

describe('market utils', () => {
  describe('detectMarket', () => {
    it('detects A股 from 6-digit code', () => {
      expect(detectMarket('000001')).toBe('CN')
      expect(detectMarket('600519')).toBe('CN')
    })

    it('detects 港股 from 4-5 digit code', () => {
      expect(detectMarket('00700')).toBe('HK')
      expect(detectMarket('09988')).toBe('HK')
    })

    it('detects 港股 from .HK suffix', () => {
      expect(detectMarket('0700.HK')).toBe('HK')
    })

    it('detects 美股 from letters', () => {
      expect(detectMarket('AAPL')).toBe('US')
      expect(detectMarket('TSLA')).toBe('US')
    })
  })

  describe('getMarketName', () => {
    it('returns correct market names', () => {
      expect(getMarketName('000001')).toBe('A股')
      expect(getMarketName('AAPL')).toBe('美股')
      expect(getMarketName('00700')).toBe('港股')
    })
  })

  describe('getMarketColors', () => {
    it('returns A股 CSS variable colors', () => {
      const colors = getMarketColors('000001')
      expect(colors.up).toBe('var(--accent-error)')
      expect(colors.down).toBe('var(--accent-success)')
    })

    it('returns 美股 CSS variable colors (green up)', () => {
      const colors = getMarketColors('AAPL')
      expect(colors.up).toBe('var(--accent-success)')
      expect(colors.down).toBe('var(--accent-error)')
    })
  })
})
