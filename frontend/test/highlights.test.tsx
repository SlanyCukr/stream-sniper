import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, renderHook, screen, waitFor } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  retrieveSceneHighlights: vi.fn(),
}))

vi.mock('@/lib/api/scene', () => api)

import {
  mapSceneHighlights,
  useSceneHighlights,
  type SceneHighlight,
} from '@/hooks/scene/useSceneHighlightsQueries'
import HighlightCard, { highlightVodHref } from '@/components/scene/HighlightCard'

const createWrapper = (queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
})) => function Wrapper({ children }: PropsWithChildren) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

/** A fully-populated highlight row (all optional fields present). */
const fullItem = {
  stream_id: 42,
  stream_title: 'Ranked grind',
  twitch_id: '998877',
  creator_id: 7,
  creator_nick: 'operator',
  creator_display_name: 'Operator',
  bucket_minute: '2026-07-18T20:30:00',
  offset_seconds: 3661,
  ratio: 4.25,
  message_count: 1280,
  unique_chatters: 640,
  sub_share: 0.18,
  emote_share: 0.42,
  top_phrases: [
    { phrase: 'LETSGO', count: 90, lift: 3.2 },
    { phrase: 'W stream', count: 40, lift: 1.8 },
  ],
  sample_messages: [
    { text: 'LETSGO', count: 12 },
    { text: 'insane play', count: 1 },
  ],
  clip_url: 'https://clips.twitch.tv/abc',
  review_status: 'clipped',
}

/** A null-heavy row: every nullable field is unknown, nothing coerced to 0. */
const nullItem = {
  stream_id: 9,
  stream_title: 'Just chatting',
  twitch_id: null,
  creator_id: 3,
  creator_nick: 'viewer',
  creator_display_name: 'Viewer',
  bucket_minute: '2026-07-17T10:00:00',
  offset_seconds: 0,
  ratio: null,
  message_count: 55,
  unique_chatters: 40,
  sub_share: null,
  emote_share: null,
  top_phrases: null,
  sample_messages: null,
  clip_url: null,
  review_status: null,
}

describe('mapSceneHighlights', () => {
  it('parses a representative payload with populated and null-heavy rows', () => {
    const result = mapSceneHighlights({
      window: '7',
      sort: 'hype',
      has_more: true,
      items: [fullItem, nullItem],
    })

    expect(result).toMatchObject({ window: '7', sort: 'hype', hasMore: true })
    expect(result.items[0]).toMatchObject({
      streamId: 42,
      twitchId: '998877',
      creatorDisplayName: 'Operator',
      bucketMinute: '2026-07-18T20:30:00',
      offsetSeconds: 3661,
      ratio: 4.25,
      messageCount: 1280,
      uniqueChatters: 640,
      subShare: 0.18,
      emoteShare: 0.42,
      clipUrl: 'https://clips.twitch.tv/abc',
      reviewStatus: 'clipped',
    })
    expect(result.items[0].topPhrases).toEqual([
      { phrase: 'LETSGO', count: 90, lift: 3.2 },
      { phrase: 'W stream', count: 40, lift: 1.8 },
    ])
    expect(result.items[0].sampleMessages).toEqual([
      { text: 'LETSGO', count: 12 },
      { text: 'insane play', count: 1 },
    ])
  })

  it('keeps unknown fields null instead of coercing them to 0 or []', () => {
    const { items } = mapSceneHighlights({
      window: 'all', sort: 'recent', has_more: false, items: [nullItem],
    })
    expect(items[0]).toMatchObject({
      twitchId: null,
      ratio: null,
      subShare: null,
      emoteShare: null,
      topPhrases: null,
      sampleMessages: null,
      clipUrl: null,
      reviewStatus: null,
    })
  })

  it('projects an empty wall as an empty item list', () => {
    expect(mapSceneHighlights({
      window: 'all', sort: 'hype', has_more: false, items: [],
    })).toEqual({ window: 'all', sort: 'hype', hasMore: false, items: [] })
  })

  it('rejects a malformed envelope (missing has_more) at the boundary', () => {
    expect(() => mapSceneHighlights({ window: 'all', sort: 'hype', items: [] }))
      .toThrow(TypeError)
  })

  it('rejects a row whose ratio is a non-finite number', () => {
    expect(() => mapSceneHighlights({
      window: 'all',
      sort: 'hype',
      has_more: false,
      items: [{ ...fullItem, ratio: Number.NaN }],
    })).toThrow(TypeError)
  })
})

describe('highlightVodHref', () => {
  it('seeks the VOD to the highlight offset (h/m/s from stream start)', () => {
    expect(highlightVodHref('998877', 3661)).toBe('https://www.twitch.tv/videos/998877?t=1h1m1s')
    expect(highlightVodHref('12', 0)).toBe('https://www.twitch.tv/videos/12?t=0h0m0s')
  })

  it('returns null when there is no VOD id', () => {
    expect(highlightVodHref(null, 3661)).toBeNull()
  })
})

describe('HighlightCard', () => {
  const toVM = (raw: unknown): SceneHighlight => mapSceneHighlights({
    window: 'all', sort: 'hype', has_more: false, items: [raw],
  }).items[0]

  it('renders hype chip, VOD jump, clip link, phrases and a review chip', () => {
    render(<HighlightCard highlight={toVM(fullItem)} />)

    expect(screen.getByText('×4.3')).toBeInTheDocument()
    const vod = screen.getByRole('link', { name: 'Jump to VOD' })
    expect(vod).toHaveAttribute('href', 'https://www.twitch.tv/videos/998877?t=1h1m1s')
    expect(screen.getByRole('link', { name: 'Watch clip' })).toHaveAttribute('href', 'https://clips.twitch.tv/abc')
    expect(screen.getByText('W stream')).toBeInTheDocument()
    expect(screen.getByText('insane play')).toBeInTheDocument()
    expect(screen.getByText('clipped')).toBeInTheDocument()
  })

  it('hides the hype chip and VOD jump when ratio/twitch_id are unknown', () => {
    render(<HighlightCard highlight={toVM(nullItem)} />)

    expect(screen.queryByRole('link', { name: 'Jump to VOD' })).toBeNull()
    expect(screen.queryByRole('link', { name: 'Watch clip' })).toBeNull()
    // No hype multiplier is rendered when ratio is null.
    expect(screen.queryByText(/^×/)).toBeNull()
  })
})

describe('useSceneHighlights', () => {
  beforeEach(() => vi.clearAllMocks())

  it('requests the mandated filter tuple and maps the envelope', async () => {
    api.retrieveSceneHighlights.mockResolvedValue({
      window: '30', sort: 'recent', has_more: true, items: [fullItem],
    })

    const { result } = renderHook(
      () => useSceneHighlights({ window: '30', sort: 'recent', limit: 24, offset: 24 }),
      { wrapper: createWrapper() },
    )
    await waitFor(() => expect(result.current.isSuccess).toBe(true))

    expect(api.retrieveSceneHighlights).toHaveBeenCalledWith({
      window: '30',
      creatorId: undefined,
      sort: 'recent',
      limit: 24,
      offset: 24,
    })
    expect(result.current.data).toMatchObject({
      window: '30',
      sort: 'recent',
      hasMore: true,
      items: [{ streamId: 42, ratio: 4.25 }],
    })
  })

  it('surfaces a malformed payload as a TypeError instead of empty success', async () => {
    api.retrieveSceneHighlights.mockResolvedValue({})
    const { result } = renderHook(() => useSceneHighlights(), { wrapper: createWrapper() })
    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.error).toBeInstanceOf(TypeError)
  })
})
