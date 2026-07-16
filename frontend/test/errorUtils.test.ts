import { describe, expect, it } from 'vitest'

import { normalizeApiError } from '@/utils/errorUtils'

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

  it('supports legacy message and error payloads through the same contract', () => {
    expect(normalizeApiError(responseError(400, { message: 'Bad message' })).message).toBe('Bad message')
    expect(normalizeApiError(responseError(400, { error: 'Bad error' })).message).toBe('Bad error')
  })

  it('uses native messages and safe fallbacks', () => {
    expect(normalizeApiError(new Error('Native failure'), 'Fallback').message).toBe('Native failure')
    expect(normalizeApiError({}, 'Fallback').message).toBe('Fallback')
  })

  it('uses the categorized HTTP fallback before a generic Axios message', () => {
    expect(normalizeApiError(responseError(403, {})).message).toBe(
      'You are not authorized to access this resource.',
    )
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
