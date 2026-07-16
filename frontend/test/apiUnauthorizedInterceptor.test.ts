import { afterEach, describe, expect, it, vi } from 'vitest'

import { api, installUnauthorizedInterceptor } from '@/lib/api/client'

describe('installUnauthorizedInterceptor', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('routes 401 failures to its owner and ejects the exact registration', async () => {
    const onUnauthorized = vi.fn()
    const use = vi.spyOn(api.interceptors.response, 'use').mockReturnValue(23)
    const eject = vi.spyOn(api.interceptors.response, 'eject').mockImplementation(() => {})

    const uninstall = installUnauthorizedInterceptor(onUnauthorized)
    const rejectResponse = use.mock.calls[0][1]
    const error = { isAxiosError: true, response: { status: 401 } }

    await expect(rejectResponse?.(error)).rejects.toBe(error)
    expect(onUnauthorized).toHaveBeenCalledOnce()

    uninstall()
    expect(eject).toHaveBeenCalledWith(23)
  })
})
