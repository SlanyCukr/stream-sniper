import { act, renderHook } from '@testing-library/react'
import type { FormEvent } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { useAuth, useStreamMessages } = vi.hoisted(() => ({
  useAuth: vi.fn(() => ({ isAuthenticated: false })),
  useStreamMessages: vi.fn(),
}))

vi.mock('@/contexts/AuthContext', () => ({ useAuth }))
vi.mock('@/hooks/stream/replay/useStreamMessagesQuery', () => ({ useStreamMessages }))

import { useActionFeedback } from '@/hooks/admin/shared/useActionFeedback'
import { useAuthFormSubmit } from '@/hooks/auth/useAuthFormSubmit'
import { useStreamDownloads } from '@/hooks/stream/useStreamDownloads'
import { useStreamReplayController } from '@/hooks/stream/replay/useStreamReplayController'

const transportError = () => Object.assign(new Error('request failed'), {
  response: { status: 503, data: { detail: 'service unavailable' } },
})

describe('UI orchestration failure contracts', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    useAuth.mockReturnValue({ isAuthenticated: false })
    useStreamMessages.mockReturnValue({
      data: { pages: [{ messages: [] }] },
      error: null,
      fetchNextPage: vi.fn(),
      hasNextPage: false,
      isFetchingNextPage: false,
      isLoading: false,
    })
  })

  it('keeps auth validation separate from original and normalized submission failures', async () => {
    const error = transportError()
    const { result } = renderHook(() => useAuthFormSubmit({
      initialForm: { username: 'operator' },
      validate: () => null,
      submit: vi.fn().mockRejectedValue(error),
      failureMessage: 'Login failed',
      externallyDisabled: false,
    }))

    await act(async () => {
      await result.current.handleSubmit(
        { preventDefault: vi.fn() } as unknown as FormEvent<HTMLFormElement>,
      )
    })

    expect(result.current.validationError).toBe('')
    expect(result.current.failure?.error).toBe(error)
    expect(result.current.failure?.normalized).toMatchObject({
      message: 'service unavailable',
      status: 503,
      retryable: true,
    })
    expect(result.current.errorMessage).toBe('service unavailable')
  })

  it('returns the same failure object that admin feedback exposes', async () => {
    const error = transportError()
    const { result } = renderHook(() => useActionFeedback())
    let outcome

    await act(async () => {
      outcome = await result.current.runAction({
        action: vi.fn().mockRejectedValue(error),
        errorTitle: 'Refresh failed',
      })
    })

    expect(outcome).toEqual({ ok: false, failure: result.current.failure })
    expect(result.current.failure?.error).toBe(error)
    expect(result.current.failure?.normalized.message).toBe('service unavailable')
  })

  it('retains normalized replay jump failures', async () => {
    const error = transportError()
    useStreamMessages.mockReturnValue({
      data: { pages: [{ messages: [] }] },
      error: null,
      fetchNextPage: vi.fn().mockRejectedValue(error),
      hasNextPage: true,
      isFetchingNextPage: false,
      isLoading: false,
    })
    const { result } = renderHook(() => useStreamReplayController(42))

    await act(async () => {
      await result.current.navigation.onJump('2026-07-15T08:00:00Z')
    })

    expect(result.current.navigation.jumpFailure?.error).toBe(error)
    expect(result.current.navigation.jumpFailure?.normalized.message).toBe('service unavailable')
  })

  it('retains normalized download failures', async () => {
    const error = transportError()
    const { result } = renderHook(() => useStreamDownloads(42))
    const item = result.current.items[0]
    item.fetcher = vi.fn().mockRejectedValue(error)

    await act(async () => {
      await result.current.handleDownload(item)
    })

    expect(result.current.failure?.error).toBe(error)
    expect(result.current.failure?.normalized.message).toBe('service unavailable')
  })
})
