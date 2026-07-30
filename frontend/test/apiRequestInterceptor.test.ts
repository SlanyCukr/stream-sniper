import { afterEach, describe, expect, it, vi } from 'vitest'

import { api } from '@/lib/api/client'
import { SessionStorageError } from '@/lib/auth/session'

describe('API request authentication', () => {
  afterEach(() => {
    localStorage.clear()
    vi.restoreAllMocks()
  })

  it('reads the shared stored token and attaches it to requests', async () => {
    localStorage.setItem('token', 'stored-token')

    const response = await api.get('/interceptor-test', {
      adapter: async config => ({
        data: null,
        status: 200,
        statusText: 'OK',
        headers: {},
        config,
      }),
    })

    expect(response.config.headers.Authorization).toBe('Bearer stored-token')
  })

  it('preserves the shared storage failure contract', async () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new DOMException('blocked', 'SecurityError')
    })

    await expect(api.get('/interceptor-test', {
      adapter: async config => ({
        data: null,
        status: 200,
        statusText: 'OK',
        headers: {},
        config,
      }),
    })).rejects.toBeInstanceOf(SessionStorageError)
  })
})
