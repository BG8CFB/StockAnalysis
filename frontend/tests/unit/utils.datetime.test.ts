import { describe, it, expect } from 'vitest'
import { formatDate, formatDateTime, isTradingDay } from '@/utils/datetime'

describe('datetime utils', () => {
  describe('formatDate', () => {
    it('formats date string with default format', () => {
      expect(formatDate('2024-01-15')).toBe('2024-01-15')
    })

    it('formats with custom format', () => {
      expect(formatDate('2024-01-15', 'YYYY/MM/DD')).toBe('2024/01/15')
    })
  })

  describe('formatDateTime', () => {
    it('formats date time', () => {
      const result = formatDateTime('2024-01-15 10:30:00')
      expect(result).toContain('2024-01-15')
      expect(result).toContain('10:30:00')
    })
  })

  describe('isTradingDay', () => {
    it('returns false for Saturday', () => {
      // 2024-01-13 is Saturday
      expect(isTradingDay('2024-01-13')).toBe(false)
    })

    it('returns false for Sunday', () => {
      // 2024-01-14 is Sunday
      expect(isTradingDay('2024-01-14')).toBe(false)
    })

    it('returns true for weekday', () => {
      // 2024-01-15 is Monday
      expect(isTradingDay('2024-01-15')).toBe(true)
    })
  })
})
