import { describe, it, expect, beforeEach } from 'vitest'
import { storage, sessionStorage as sessionStore } from '@/utils/storage'

describe('storage utils', () => {
  beforeEach(() => {
    localStorage.clear()
    window.sessionStorage.clear()
  })

  describe('localStorage wrapper', () => {
    it('stores and retrieves string', () => {
      storage.set('key', 'value')
      expect(storage.get<string>('key')).toBe('value')
    })

    it('stores and retrieves object', () => {
      storage.set('obj', { name: 'test', count: 42 })
      expect(storage.get<{ name: string; count: number }>('obj')).toEqual({ name: 'test', count: 42 })
    })

    it('returns null for missing key', () => {
      expect(storage.get('nonexistent')).toBeNull()
    })

    it('removes key', () => {
      storage.set('key', 'value')
      storage.remove('key')
      expect(storage.get('key')).toBeNull()
    })

    it('clears all', () => {
      storage.set('a', 1)
      storage.set('b', 2)
      storage.clear()
      expect(storage.get('a')).toBeNull()
      expect(storage.get('b')).toBeNull()
    })

    it('handles invalid JSON gracefully', () => {
      localStorage.setItem('bad', 'not-json')
      expect(storage.get('bad')).toBeNull()
    })
  })

  describe('sessionStorage wrapper', () => {
    it('stores and retrieves string', () => {
      sessionStore.set('key', 'value')
      expect(sessionStore.get<string>('key')).toBe('value')
    })

    it('returns null for missing key', () => {
      expect(sessionStore.get('nonexistent')).toBeNull()
    })

    it('removes key', () => {
      sessionStore.set('key', 'value')
      sessionStore.remove('key')
      expect(sessionStore.get('key')).toBeNull()
    })
  })
})
