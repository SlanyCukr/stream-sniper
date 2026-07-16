import { describe, expect, it } from 'vitest'

import { shouldRetryQuery } from '@/app/providers'

const statusError = (status: number) => ({ response: { status, data: {} } })

describe('QueryClient retry policy', () => {
  it('never retries terminal client failures', () => {
    expect(shouldRetryQuery(0, statusError(400))).toBe(false)
    expect(shouldRetryQuery(0, statusError(401))).toBe(false)
    expect(shouldRetryQuery(0, statusError(404))).toBe(false)
  })

  it('allows at most two retries for transient failures', () => {
    const failure = statusError(503)

    expect(shouldRetryQuery(0, failure)).toBe(true)
    expect(shouldRetryQuery(1, failure)).toBe(true)
    expect(shouldRetryQuery(2, failure)).toBe(false)
  })
})
