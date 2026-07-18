import { describe, expect, it } from 'vitest'

import { normalizeApiError, uiError } from '@/utils/errorUtils'

const responseError = (status: number, data: unknown) => ({
  message: `Request failed with status ${status}`,
  response: { status, data },
})

describe('normalizeApiError', () => {
  it('prefers FastAPI detail and categorizes the status', () => {
    expect(normalizeApiError(responseError(422, { detail: 'Invalid filter' }))).toMatchObject({
      message: 'Invalid filter',
      status: 422,
      type: 'validation',
      retryable: false,
    })
  })

  it('formats FastAPI validation detail arrays', () => {
    const normalized = normalizeApiError(responseError(422, {
      detail: [{ msg: 'Field is required' }, { msg: 'Value is invalid' }],
    }))

    expect(normalized.message).toBe('Field is required; Value is invalid')
  })

  it('strips the FastAPI "Value error, " prefix from validator messages', () => {
    const normalized = normalizeApiError(responseError(422, {
      detail: [{ msg: 'Value error, Invalid email format' }],
    }))

    expect(normalized.message).toBe('Invalid email format')
  })

  it('supports legacy message and error payloads through the same contract', () => {
    expect(normalizeApiError(responseError(400, { message: 'Bad message' })).message).toBe('Bad message')
    expect(normalizeApiError(responseError(400, { error: 'Bad error' })).message).toBe('Bad error')
  })

  it('sanitizes native error messages down to the fallback', () => {
    expect(normalizeApiError(new Error('stats.system_status.failed_jobs must be a finite number'), 'Fallback').message).toBe('Fallback')
    expect(normalizeApiError({}, 'Fallback').message).toBe('Fallback')
  })

  it('surfaces messages from errors explicitly marked user-facing', () => {
    expect(normalizeApiError(uiError('This link is invalid.'), 'Fallback').message).toBe('This link is invalid.')
  })

  it('uses the categorized HTTP fallback before a generic Axios message', () => {
    expect(normalizeApiError(responseError(403, {})).message).toBe(
      "You don't have permission to do this.",
    )
  })

  it('replaces raw rate-limit payloads with friendly copy', () => {
    const normalized = normalizeApiError(responseError(429, { error: 'Rate limit exceeded: 5 per 1 minute' }))

    expect(normalized.message).toBe("You're doing that too fast. Wait a moment and try again.")
    expect(normalized.retryAfterSeconds).toBeNull()
  })

  it('surfaces the Retry-After duration on rate-limit responses', () => {
    const normalized = normalizeApiError({
      message: 'Request failed with status 429',
      response: {
        status: 429,
        data: { error: 'Rate limit exceeded: 5 per 1 minute' },
        headers: { 'retry-after': '30' },
      },
    })

    expect(normalized.message).toBe("You're doing that too fast. Try again in 30 seconds.")
    expect(normalized.retryAfterSeconds).toBe(30)
  })

  it('ignores non-numeric Retry-After values', () => {
    const normalized = normalizeApiError({
      message: 'Request failed with status 429',
      response: {
        status: 429,
        data: {},
        headers: { 'retry-after': 'Fri, 18 Jul 2026 00:00:00 GMT' },
      },
    })

    expect(normalized.message).toBe("You're doing that too fast. Wait a moment and try again.")
    expect(normalized.retryAfterSeconds).toBeNull()
  })

  it('does not attach retryAfterSeconds outside 429 responses', () => {
    expect(normalizeApiError(responseError(500, {})).retryAfterSeconds).toBeNull()
  })

  it.each([408, 425, 429, 500, 503])('marks transient HTTP %s failures retryable', (status) => {
    expect(normalizeApiError(responseError(status, {})).retryable).toBe(true)
  })

  it.each([400, 401, 403, 404, 422])('does not retry terminal HTTP %s failures', (status) => {
    expect(normalizeApiError(responseError(status, {})).retryable).toBe(false)
  })

  it('recognizes transport failures without an HTTP response', () => {
    expect(normalizeApiError({ code: 'ERR_NETWORK', message: 'Network Error' })).toMatchObject({
      type: 'network',
      retryable: true,
    })
  })
})
