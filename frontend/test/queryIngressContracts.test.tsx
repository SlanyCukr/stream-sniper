import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  retrieveAudienceMovement: vi.fn(),
  retrieveCommunityOverlap: vi.fn(),
  retrieveCreatorHeadToHead: vi.fn(),
  retrieveCreatorNeighbors: vi.fn(),
  retrieveEmoteDetail: vi.fn(),
  retrieveSearchContext: vi.fn(),
  retrieveSearchFirst: vi.fn(),
  retrieveSearchFrequency: vi.fn(),
  retrieveSearchMessages: vi.fn(),
}))

vi.mock('@/lib/api/community', () => ({
  retrieveCommunityOverlap: api.retrieveCommunityOverlap,
  retrieveCreatorHeadToHead: api.retrieveCreatorHeadToHead,
  retrieveCreatorNeighbors: api.retrieveCreatorNeighbors,
}))
vi.mock('@/lib/api/creators', () => ({ retrieveAudienceMovement: api.retrieveAudienceMovement }))
vi.mock('@/lib/api/scene', () => ({ retrieveEmoteDetail: api.retrieveEmoteDetail }))
vi.mock('@/lib/api/search', () => ({
  retrieveSearchContext: api.retrieveSearchContext,
  retrieveSearchFirst: api.retrieveSearchFirst,
  retrieveSearchFrequency: api.retrieveSearchFrequency,
  retrieveSearchMessages: api.retrieveSearchMessages,
}))

import { useCreatorHeadToHead } from '@/hooks/community/useHeadToHeadQuery'
import { useCreatorNeighbors } from '@/hooks/community/useCommunityQuery'
import { useAudienceMovement } from '@/hooks/creator/useAudienceMovementQuery'
import { useSearchContext } from '@/hooks/scene/search/useSearchQueries'
import { useEmoteDetail } from '@/hooks/scene/useEmoteDetailQuery'

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: Infinity } },
  })
  return function Wrapper({ children }: PropsWithChildren) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('nullable query ingress', () => {
  beforeEach(() => vi.clearAllMocks())

  it('rejects manual creator head-to-head refetches before the adapter boundary', async () => {
    const hook = renderHook(() => useCreatorHeadToHead(null, 3), { wrapper: createWrapper() })
    expect(hook.result.current.fetchStatus).toBe('idle')

    await act(async () => {
      const outcome = await hook.result.current.refetch()
      expect(outcome.error).toEqual(expect.objectContaining({
        message: 'creator head-to-head requires valid arguments before fetching',
      }))
    })
    expect(api.retrieveCreatorHeadToHead).not.toHaveBeenCalled()
  })

  it('rejects manual creator-neighbor refetches before the adapter boundary', async () => {
    const hook = renderHook(() => useCreatorNeighbors(null), { wrapper: createWrapper() })
    expect(hook.result.current.fetchStatus).toBe('idle')

    await act(async () => {
      const outcome = await hook.result.current.refetch()
      expect(outcome.error).toEqual(expect.objectContaining({
        message: 'creator neighbors requires valid arguments before fetching',
      }))
    })
    expect(api.retrieveCreatorNeighbors).not.toHaveBeenCalled()
  })

  it('rejects manual search-context refetches before the adapter boundary', async () => {
    const hook = renderHook(() => useSearchContext({ streamId: null, messageId: null }), {
      wrapper: createWrapper(),
    })
    expect(hook.result.current.fetchStatus).toBe('idle')

    await act(async () => {
      const outcome = await hook.result.current.refetch()
      expect(outcome.error).toEqual(expect.objectContaining({
        message: 'search context requires valid arguments before fetching',
      }))
    })
    expect(api.retrieveSearchContext).not.toHaveBeenCalled()
  })

  it('rejects manual emote-detail refetches before the adapter boundary', async () => {
    const hook = renderHook(() => useEmoteDetail(null), { wrapper: createWrapper() })
    expect(hook.result.current.fetchStatus).toBe('idle')

    await act(async () => {
      const outcome = await hook.result.current.refetch()
      expect(outcome.error).toEqual(expect.objectContaining({
        message: 'emote detail requires valid arguments before fetching',
      }))
    })
    expect(api.retrieveEmoteDetail).not.toHaveBeenCalled()
  })

  it('rejects manual audience-movement refetches before the adapter boundary', async () => {
    const hook = renderHook(() => useAudienceMovement(null), { wrapper: createWrapper() })
    expect(hook.result.current.fetchStatus).toBe('idle')

    await act(async () => {
      const outcome = await hook.result.current.refetch()
      expect(outcome.error).toEqual(expect.objectContaining({
        message: 'audience movement requires valid arguments before fetching',
      }))
    })
    expect(api.retrieveAudienceMovement).not.toHaveBeenCalled()
  })
})
