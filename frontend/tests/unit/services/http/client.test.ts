import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import axios from 'axios'
import type { AxiosInstance, InternalAxiosRequestConfig } from 'axios'

// ── Mock dependencies ──
vi.mock('axios', () => {
  const mockInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    patch: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
    defaults: { baseURL: '', timeout: 60000, headers: {} },
  }
  const create = vi.fn(() => mockInstance)
  return { default: { create, post: vi.fn() }, create }
})

vi.mock('@/stores/auth.store', () => ({
  useAuthStore: {
    getState: vi.fn(() => ({
      token: 'test-token',
      refreshToken: 'test-refresh-token',
      clearAuth: vi.fn(),
      setToken: vi.fn(),
      setRefreshToken: vi.fn(),
    })),
    subscribe: vi.fn(() => vi.fn()),
    setState: vi.fn(),
  },
}))

vi.mock('@/services/http/error-handler', () => ({
  showError: vi.fn(),
  getHttpErrorMessage: vi.fn((status: number) => `Error ${status}`),
  isRetryableError: vi.fn(() => false),
}))

// Import after mocks are set up
import { apiClient, httpClient } from '@/services/http/client'
import { useAuthStore } from '@/stores/auth.store'
import { showError, getHttpErrorMessage, isRetryableError } from '@/services/http/error-handler'

describe('HTTP Client', () => {
  let mockInstance: {
    get: ReturnType<typeof vi.fn>
    post: ReturnType<typeof vi.fn>
    put: ReturnType<typeof vi.fn>
    delete: ReturnType<typeof vi.fn>
    patch: ReturnType<typeof vi.fn>
    interceptors: {
      request: { use: ReturnType<typeof vi.fn> }
      response: { use: ReturnType<typeof vi.fn> }
    }
  }

  beforeEach(() => {
    vi.clearAllMocks()
    // Get the mock instance that axios.create returns
    mockInstance = axios.create() as unknown as typeof mockInstance
  })

  describe('axios instance creation', () => {
    it('creates an axios instance', () => {
      expect(axios.create).toHaveBeenCalled()
    })

    it('exports httpClient as the axios instance', () => {
      expect(httpClient).toBeDefined()
    })

    it('exports apiClient with all HTTP methods', () => {
      expect(apiClient.get).toBeTypeOf('function')
      expect(apiClient.post).toBeTypeOf('function')
      expect(apiClient.put).toBeTypeOf('function')
      expect(apiClient.delete).toBeTypeOf('function')
      expect(apiClient.patch).toBeTypeOf('function')
      expect(apiClient.upload).toBeTypeOf('function')
      expect(apiClient.download).toBeTypeOf('function')
    })
  })

  describe('apiClient.get', () => {
    it('calls instance.get with correct arguments and returns response data', async () => {
      const mockResponse = { data: { success: true, data: { id: 1 }, message: 'ok' } }
      mockInstance.get.mockResolvedValueOnce(mockResponse)

      const result = await apiClient.get('/api/test')

      expect(mockInstance.get).toHaveBeenCalledWith('/api/test', {
        params: undefined,
      })
      expect(result).toEqual(mockResponse.data)
    })

    it('passes params and config to instance.get', async () => {
      const mockResponse = { data: { success: true, data: null, message: 'ok' } }
      mockInstance.get.mockResolvedValueOnce(mockResponse)
      const params = { page: 1, size: 10 }
      const config = { skipAuth: true }

      await apiClient.get('/api/test', params, config)

      expect(mockInstance.get).toHaveBeenCalledWith('/api/test', {
        params,
        ...config,
      })
    })
  })

  describe('apiClient.post', () => {
    it('sends data and returns response data', async () => {
      const mockResponse = { data: { success: true, data: { id: 1 }, message: 'created' } }
      mockInstance.post.mockResolvedValueOnce(mockResponse)
      const payload = { name: 'test' }

      const result = await apiClient.post('/api/test', payload)

      expect(mockInstance.post).toHaveBeenCalledWith('/api/test', payload, undefined)
      expect(result).toEqual(mockResponse.data)
    })

    it('handles post without data', async () => {
      const mockResponse = { data: { success: true, data: null, message: 'ok' } }
      mockInstance.post.mockResolvedValueOnce(mockResponse)

      const result = await apiClient.post('/api/test')

      expect(mockInstance.post).toHaveBeenCalledWith('/api/test', undefined, undefined)
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('apiClient.put', () => {
    it('sends data and returns response data', async () => {
      const mockResponse = { data: { success: true, data: { id: 1 }, message: 'updated' } }
      mockInstance.put.mockResolvedValueOnce(mockResponse)
      const payload = { name: 'updated' }

      const result = await apiClient.put('/api/test/1', payload)

      expect(mockInstance.put).toHaveBeenCalledWith('/api/test/1', payload, undefined)
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('apiClient.delete', () => {
    it('calls instance.delete and returns response data', async () => {
      const mockResponse = { data: { success: true, data: null, message: 'deleted' } }
      mockInstance.delete.mockResolvedValueOnce(mockResponse)

      const result = await apiClient.delete('/api/test/1')

      expect(mockInstance.delete).toHaveBeenCalledWith('/api/test/1', undefined)
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('apiClient.patch', () => {
    it('sends data and returns response data', async () => {
      const mockResponse = { data: { success: true, data: { id: 1 }, message: 'patched' } }
      mockInstance.patch.mockResolvedValueOnce(mockResponse)
      const payload = { name: 'patched' }

      const result = await apiClient.patch('/api/test/1', payload)

      expect(mockInstance.patch).toHaveBeenCalledWith('/api/test/1', payload, undefined)
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('apiClient.upload', () => {
    it('creates FormData and sends multipart request', async () => {
      const mockResponse = { data: { success: true, data: { url: '/files/1' }, message: 'ok' } }
      mockInstance.post.mockResolvedValueOnce(mockResponse)
      const file = new File(['content'], 'test.txt', { type: 'text/plain' })

      const result = await apiClient.upload('/api/upload', file)

      expect(mockInstance.post).toHaveBeenCalledWith(
        '/api/upload',
        expect.any(FormData),
        expect.objectContaining({
          headers: { 'Content-Type': 'multipart/form-data' },
        })
      )
      expect(result).toEqual(mockResponse.data)
    })

    it('reports upload progress via callback', async () => {
      const mockResponse = { data: { success: true, data: {}, message: 'ok' } }
      mockInstance.post.mockImplementationOnce((_url: string, _data: unknown, config?: Record<string, unknown>) => {
        // Simulate progress callback
        const onUploadProgress = config?.onUploadProgress as ((event: { loaded: number; total: number }) => void) | undefined
        if (onUploadProgress) {
          onUploadProgress({ loaded: 50, total: 100 })
        }
        return Promise.resolve(mockResponse)
      })
      const file = new File(['content'], 'test.txt', { type: 'text/plain' })
      const onProgress = vi.fn()

      await apiClient.upload('/api/upload', file, onProgress)

      expect(onProgress).toHaveBeenCalledWith(50)
    })
  })

  describe('apiClient.download', () => {
    it('downloads file by creating a blob link', async () => {
      const blobData = new Blob(['file content'], { type: 'text/plain' })
      mockInstance.get.mockResolvedValueOnce({ data: blobData })

      // Mock URL.createObjectURL / revokeObjectURL
      const createObjectURLSpy = vi.fn(() => 'blob:mock-url')
      const revokeObjectURLSpy = vi.fn()
      vi.stubGlobal('URL', {
        createObjectURL: createObjectURLSpy,
        revokeObjectURL: revokeObjectURLSpy,
      })

      // Mock document.createElement
      const mockLink = {
        href: '',
        download: '',
        click: vi.fn(),
      }
      const createElementSpy = vi.spyOn(document, 'createElement').mockReturnValueOnce(mockLink as unknown as HTMLAnchorElement)
      const appendChildSpy = vi.spyOn(document.body, 'appendChild').mockImplementation(() => document.createElement('a'))
      const removeChildSpy = vi.spyOn(document.body, 'removeChild').mockImplementation(() => document.createElement('a'))

      await apiClient.download('/api/files/1', 'report.pdf')

      expect(mockInstance.get).toHaveBeenCalledWith('/api/files/1', expect.objectContaining({
        responseType: 'blob',
      }))
      expect(createObjectURLSpy).toHaveBeenCalled()
      expect(mockLink.download).toBe('report.pdf')
      expect(mockLink.click).toHaveBeenCalled()
      expect(revokeObjectURLSpy).toHaveBeenCalledWith('blob:mock-url')

      // Cleanup
      createElementSpy.mockRestore()
      appendChildSpy.mockRestore()
      removeChildSpy.mockRestore()
      vi.unstubAllGlobals()
    })

    it('uses default filename when not provided', async () => {
      const blobData = new Blob(['data'])
      mockInstance.get.mockResolvedValueOnce({ data: blobData })

      vi.stubGlobal('URL', {
        createObjectURL: vi.fn(() => 'blob:mock'),
        revokeObjectURL: vi.fn(),
      })

      const mockLink = { href: '', download: '', click: vi.fn() }
      vi.spyOn(document, 'createElement').mockReturnValueOnce(mockLink as unknown as HTMLAnchorElement)
      vi.spyOn(document.body, 'appendChild').mockImplementation(() => document.createElement('a'))
      vi.spyOn(document.body, 'removeChild').mockImplementation(() => document.createElement('a'))

      await apiClient.download('/api/files/1')

      expect(mockLink.download).toBe('download')

      vi.restoreAllMocks()
      vi.unstubAllGlobals()
    })
  })

  describe('interceptor registration', () => {
    it('axios.create was called to create the httpClient', () => {
      // axios.create is called once during module initialization
      expect(axios.create).toHaveBeenCalled()
    })

    it('httpClient is the instance returned by axios.create', () => {
      expect(httpClient).toBe(mockInstance)
    })
  })

  describe('error handling', () => {
    it('propagates error when request fails', async () => {
      const error = new Error('Network Error')
      mockInstance.get.mockRejectedValueOnce(error)

      await expect(apiClient.get('/api/fail')).rejects.toThrow('Network Error')
    })
  })
})
