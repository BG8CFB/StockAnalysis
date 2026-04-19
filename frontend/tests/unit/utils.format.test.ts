import { describe, it, expect } from 'vitest'
import {
  formatCurrency,
  formatPercent,
  formatLargeNumber,
  formatVolume,
  formatAmount,
  getChangeColor,
  formatPrice,
} from '@/utils/format'

describe('format utils', () => {
  describe('formatCurrency', () => {
    it('formats small numbers with ¥ prefix', () => {
      expect(formatCurrency(1234.56)).toBe('¥1234.56')
    })

    it('formats numbers >= 10000 as 万', () => {
      expect(formatCurrency(15000)).toBe('¥1.50万')
    })

    it('formats numbers >= 100000000 as 亿', () => {
      expect(formatCurrency(200000000)).toBe('¥2.00亿')
    })

    it('formats negative numbers', () => {
      expect(formatCurrency(-50000)).toBe('¥-5.00万')
    })

    it('handles NaN', () => {
      expect(formatCurrency(NaN)).toBe('--')
    })
  })

  describe('formatPercent', () => {
    it('formats positive with +', () => {
      expect(formatPercent(5.5)).toBe('+5.50%')
    })

    it('formats negative without +', () => {
      expect(formatPercent(-3.2)).toBe('-3.20%')
    })

    it('formats zero without +', () => {
      expect(formatPercent(0)).toBe('0.00%')
    })

    it('handles null', () => {
      expect(formatPercent(null)).toBe('--')
    })

    it('handles undefined', () => {
      expect(formatPercent(undefined)).toBe('--')
    })
  })

  describe('formatLargeNumber', () => {
    it('formats large numbers as 亿', () => {
      expect(formatLargeNumber(150000000)).toBe('1.50亿')
    })

    it('formats medium numbers as 万', () => {
      expect(formatLargeNumber(25000)).toBe('2.50万')
    })

    it('formats small numbers directly', () => {
      expect(formatLargeNumber(123)).toBe('123.00')
    })
  })

  describe('formatVolume', () => {
    it('formats small volumes', () => {
      expect(formatVolume(500)).toBe('500手')
    })

    it('formats medium volumes as 万手', () => {
      expect(formatVolume(20000)).toBe('2.00万手')
    })

    it('formats large volumes as 亿手', () => {
      expect(formatVolume(300000000)).toBe('3.00亿手')
    })
  })

  describe('formatAmount', () => {
    it('formats small amounts', () => {
      expect(formatAmount(1234.56)).toBe('1234.56')
    })

    it('formats medium amounts as 万', () => {
      expect(formatAmount(50000)).toBe('5.00万')
    })

    it('formats large amounts as 亿', () => {
      expect(formatAmount(100000000)).toBe('1.00亿')
    })
  })

  describe('getChangeColor', () => {
    it('returns error color for positive', () => {
      expect(getChangeColor(1.5)).toBe('var(--accent-error)')
    })

    it('returns success color for negative', () => {
      expect(getChangeColor(-1.5)).toBe('var(--accent-success)')
    })

    it('returns primary for zero', () => {
      expect(getChangeColor(0)).toBe('var(--text-primary)')
    })

    it('returns primary for null', () => {
      expect(getChangeColor(null)).toBe('var(--text-primary)')
    })
  })

  describe('formatPrice', () => {
    it('formats with 2 decimals by default', () => {
      expect(formatPrice(123.456)).toBe('123.46')
    })

    it('handles null', () => {
      expect(formatPrice(null)).toBe('--')
    })

    it('handles custom decimals', () => {
      expect(formatPrice(123.456, 3)).toBe('123.456')
    })
  })
})
