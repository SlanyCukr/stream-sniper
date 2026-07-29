import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  retrieveSearchMessages: vi.fn(),
  retrieveSearchFirst: vi.fn(),
  retrieveSearchFrequency: vi.fn(),
  retrieveSearchContext: vi.fn(),
}))

vi.mock('@/lib/api/search', () => api)

import { useSearchMessages } from '@/hooks/scene/search/useSearchQueries'

const hit = (id: number) => ({
  message_id: id,
  time: '2026-07-18T10:00:00Z',
  text: `message ${id}`,
  chatter: { id: 2, nick: 'viewer', is_bot: null },
  stream: { id: 3, title: 'Live' },
  creator: { id: 4, nick: 'streamer', display_name: 'Streamer' },
})

const createWrapper = (queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
})) => function Wrapper({ children }: PropsWithChildren) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe('useSearchMessages pagination', () => {
  beforeEach(() => vi.clearAllMocks())

  it('keeps filters in the query identity and advances offset internally', async () => {
    api.retrieveSearchMessages
      .mockResolvedValueOnce({ query: 'pog', has_more: true, items: [hit(1)] })
      .mockResolvedValueOnce({ query: 'pog', has_more: false, items: [hit(2)] })

    const { result } = renderHook(
      () => useSearchMessages({ q: '  pog  ', creatorId: 4, days: 30, limit: 50 }),
      { wrapper: createWrapper() },
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    await waitFor(() => expect(result.current.hasNextPage).toBe(true))
    expect(api.retrieveSearchMessages).toHaveBeenNthCalledWith(1, {
      q: 'pog', creatorId: 4, days: 30, limit: 50, offset: 0,
    })

    await act(async () => {
      await result.current.fetchNextPage()
    })
    await waitFor(() => expect(result.current.data?.pages).toHaveLength(2))

    expect(api.retrieveSearchMessages).toHaveBeenNthCalledWith(2, {
      q: 'pog', creatorId: 4, days: 30, limit: 50, offset: 50,
    })
    expect(result.current.data?.pages.flatMap(page => page.items).map(item => item.messageId))
      .toEqual([1, 2])
    expect(result.current.hasNextPage).toBe(false)
  })

  it('does not fetch a query below the backend minimum', async () => {
    const hook = renderHook(() => useSearchMessages({ q: 'ab' }), { wrapper: createWrapper() })
    await waitFor(() => expect(hook.result.current.fetchStatus).toBe('idle'))
    expect(api.retrieveSearchMessages).not.toHaveBeenCalled()
  })
})
