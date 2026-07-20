import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  retrieveSceneLive: vi.fn(),
  retrieveSceneLeaderboard: vi.fn(),
  retrieveSceneCopypastas: vi.fn(),
  retrieveCopypastaPropagation: vi.fn(),
  retrieveScenePulse: vi.fn(),
  retrieveSceneDigest: vi.fn(),
}))

vi.mock('@/lib/api/scene', () => api)

import {
  mapCopypastaPropagation,
  useCopypastaPropagation,
  useSceneCopypastas,
} from '@/hooks/scene/useSceneCopypastaQueries'
import {
  useSceneLeaderboard,
  useSceneLive,
} from '@/hooks/scene/useSceneLiveQueries'
import {
  mapSceneDigest,
  mapScenePulse,
  useSceneDigest,
  useScenePulse,
} from '@/hooks/scene/useScenePulseQueries'

const createWrapper = (queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
})) => {
  return function Wrapper({ children }: PropsWithChildren) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('scene query view-model contracts', () => {
  beforeEach(() => vi.clearAllMocks())

  it('maps propagation children through the pure mapper', () => {
    expect(mapCopypastaPropagation({
      message_text_id: 7,
      text: 'copy',
      usage_count: 4,
      chatter_appearances: 3,
      stream_count: 2,
      creator_count: 1,
      first_seen: null,
      occurrences: [{
        stream_id: 11,
        creator_id: 5,
        nick: 'operator',
        display_name: 'Operator',
        profile_image_url: null,
        stream_title: 'Live',
        stream_start: null,
        first_seen: null,
        usage_count: 4,
        chatter_count: 3,
      }],
      origin_context: [{ id: 9, time: 'now', chatter_id: 2, nick: 'viewer', text: 'copy' }],
    })).toMatchObject({
      messageTextId: 7,
      occurrences: [{ streamId: 11, creatorId: 5 }],
      originContext: [{ id: 9, chatterId: 2 }],
    })
    expect(() => mapCopypastaPropagation({ occurrences: [], origin_context: [] })).toThrow(TypeError)
  })

  it('validates complete pulse and digest envelopes before projecting view models', () => {
    expect(mapScenePulse({ items: [], total: 0, days: 30, limit: 25, offset: 50 })).toEqual({
      items: [],
      total: 0,
      days: 30,
      limit: 25,
      offset: 50,
    })
    expect(mapSceneDigest({ days: 7, markdown: '## digest' })).toBe('## digest')
    expect(() => mapScenePulse({ items: [], total: 0 })).toThrow(TypeError)
    expect(() => mapSceneDigest({ markdown: '## digest' })).toThrow(TypeError)
  })

  it('maps live and leaderboard payloads without converting unknowns to zero', async () => {
    api.retrieveSceneLive.mockResolvedValue({
      live: [{
        creator_id: 1,
        nick: 'alpha',
        display_name: null,
        profile_image_url: null,
        viewer_count: null,
        title: null,
        session_started_at: null,
        sampled_at: 'sampled',
      }],
      live_count: 1,
      last_sample_at: 'sampled',
    })
    api.retrieveSceneLeaderboard.mockResolvedValue({
      window_days: 7,
      computed_at: null,
      entries: [{
        rank: 1,
        creator_id: 1,
        nick: 'alpha',
        display_name: null,
        profile_image_url: null,
        streams: 2,
        hours_streamed: null,
        total_messages: 100,
        msgs_per_min: null,
        chatter_appearances: 20,
        peak_viewers: null,
      }],
    })

    const liveClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const live = renderHook(() => useSceneLive({ refetchInterval: false }), {
      wrapper: createWrapper(liveClient),
    })
    const leaderboard = renderHook(() => useSceneLeaderboard({ windowDays: 7 }), { wrapper: createWrapper() })
    await waitFor(() => expect((live.result.current as any).isSuccess).toBe(true))
    await waitFor(() => expect((leaderboard.result.current as any).isSuccess).toBe(true))

    expect((live.result.current as any).data?.live[0]).toMatchObject({
      creatorId: 1,
      displayName: null,
      viewerCount: null,
      title: null,
    })
    expect((leaderboard.result.current as any).data?.entries[0]).toMatchObject({
      creatorId: 1,
      hoursStreamed: null,
      msgsPerMin: null,
      peakViewers: null,
    })
    const liveOptions = liveClient.getQueryCache().find({ queryKey: ['scene', 'live'] })?.options as
      | { refetchInterval?: unknown }
      | undefined
    expect(liveOptions?.refetchInterval).toBe(false)
  })

  it('adapts page indexes to row offsets and maps copypasta rows', async () => {
    api.retrieveSceneCopypastas.mockResolvedValue({
      total: 51,
      offset: 50,
      limit: 25,
      items: [{
        message_text_id: 7,
        text: 'copy',
        usage_count: 10,
        chatter_appearances: 8,
        stream_count: 4,
        creator_count: 2,
        first_seen: null,
        last_stream_start: null,
      }],
    })
    const { result } = renderHook(
      () => useSceneCopypastas({ creatorId: 3, sort: 'usage', pageIndex: 2, pageSize: 25 }),
      { wrapper: createWrapper() },
    )
    await waitFor(() => expect((result.current as any).isSuccess).toBe(true))

    expect(api.retrieveSceneCopypastas).toHaveBeenCalledWith({
      days: undefined,
      creatorId: 3,
      sort: 'usage',
      pageSize: 25,
      rowOffset: 50,
    })
    expect((result.current as any).data).toMatchObject({
      total: 51,
      pageIndex: 2,
      pageCount: 3,
      items: [{ messageTextId: 7, firstSeen: null, lastStreamStart: null }],
    })
  })

  it.each([
    ['live', () => {
      api.retrieveSceneLive.mockResolvedValue({})
      return renderHook(() => useSceneLive({ refetchInterval: false }), { wrapper: createWrapper() })
    }],
    ['leaderboard', () => {
      api.retrieveSceneLeaderboard.mockResolvedValue({})
      return renderHook(() => useSceneLeaderboard({ windowDays: 7 }), { wrapper: createWrapper() })
    }],
    ['copypastas', () => {
      api.retrieveSceneCopypastas.mockResolvedValue({})
      return renderHook(() => useSceneCopypastas(), { wrapper: createWrapper() })
    }],
    ['propagation', () => {
      api.retrieveCopypastaPropagation.mockResolvedValue({})
      return renderHook(() => useCopypastaPropagation(7), { wrapper: createWrapper() })
    }],
    ['pulse', () => {
      api.retrieveScenePulse.mockResolvedValue({})
      return renderHook(() => useScenePulse(), { wrapper: createWrapper() })
    }],
    ['digest', () => {
      api.retrieveSceneDigest.mockResolvedValue({})
      return renderHook(() => useSceneDigest(), { wrapper: createWrapper() })
    }],
  ])('rejects malformed %s payloads', async (_name, render) => {
    const hook = render()
    await waitFor(() => expect((hook.result.current as any).isError).toBe(true))
    expect((hook.result.current as any).error).toBeInstanceOf(TypeError)
  })

  it('lets callers disable valid scene resource queries', async () => {
    renderHook(() => useSceneLive({ enabled: false, refetchInterval: false }), {
      wrapper: createWrapper(),
    })
    renderHook(() => useSceneLeaderboard({ windowDays: 7 }, { enabled: false }), { wrapper: createWrapper() })
    renderHook(() => useCopypastaPropagation(7, 90, { enabled: false }), {
      wrapper: createWrapper(),
    })
    await new Promise(resolve => setTimeout(resolve, 0))
    expect(api.retrieveSceneLive).not.toHaveBeenCalled()
    expect(api.retrieveSceneLeaderboard).not.toHaveBeenCalled()
    expect(api.retrieveCopypastaPropagation).not.toHaveBeenCalled()
  })
})
