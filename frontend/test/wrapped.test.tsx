import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, renderHook, screen, waitFor } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  retrieveSceneWrapped: vi.fn(),
}))

vi.mock('@/lib/api/scene', () => api)

import {
  mapSceneWrapped,
  isWrappedEmpty,
  useSceneWrapped,
  type SceneWrapped,
} from '@/hooks/scene/useSceneWrappedQuery'
import WrappedRecap from '@/components/scene/WrappedRecap'

const createWrapper = (queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
})) => function Wrapper({ children }: PropsWithChildren) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

const wirePayload = () => ({
  days: 30,
  totals: {
    streams: 42,
    hours_streamed: null,
    messages: 1_250_000,
    active_chatters: 8_300,
    creators_active: 37,
  },
  top_creators: [
    {
      rank: 1,
      creator_id: 3,
      nick: 'acelestialcz',
      display_name: 'Celestial',
      profile_image_url: 'https://cdn/x.png',
      total_messages: 500_000,
      streams: 20,
      hours_streamed: 90,
      msgs_per_min: 42.5,
      peak_viewers: 12_000,
    },
    {
      rank: 2,
      creator_id: 5,
      nick: 'noavatar',
      display_name: 'No Avatar',
      profile_image_url: null,
      total_messages: 250_000,
      streams: 10,
      hours_streamed: null,
      msgs_per_min: null,
      peak_viewers: null,
    },
  ],
  top_chatters: [
    {
      rank: 1,
      chatter_id: 7,
      nick: 'topchatter',
      total_messages: 60_000,
      streams_attended: 40,
      creators_visited: 12,
      home_creator_display_name: 'Celestial',
    },
    {
      rank: 2,
      chatter_id: 8,
      nick: 'wanderer',
      total_messages: 30_000,
      streams_attended: 20,
      creators_visited: 25,
      home_creator_display_name: null,
    },
  ],
  top_moments: [
    {
      stream_id: 100,
      stream_title: 'INSANE clutch',
      twitch_id: 'v123',
      creator_display_name: 'Celestial',
      bucket_minute: '2026-07-10T20:15:00',
      offset_seconds: 3600,
      ratio: 8.4,
      message_count: 2_400,
    },
    {
      stream_id: 101,
      stream_title: 'no ratio moment',
      twitch_id: null,
      creator_display_name: 'Other',
      bucket_minute: '2026-07-11T21:00:00',
      offset_seconds: 120,
      ratio: null,
      message_count: 900,
    },
  ],
  top_copypastas: [
    {
      message_text_id: 55,
      text: 'aware',
      usage_count: 1_200,
      creator_count: 9,
      stream_count: 30,
    },
  ],
  top_emotes: [
    {
      emote_id: 11,
      name: 'PogU',
      source: '7tv',
      usage: 90_000,
      chatter_reach: 4_200,
    },
  ],
  notable_events: [
    {
      event_type: 'record_viewers',
      occurred_at: '2026-07-10T20:15:00',
      title: 'New scene peak',
      summary: 'Celestial hit 12k concurrent viewers.',
      creator_display_name: 'Celestial',
    },
    {
      event_type: 'milestone',
      occurred_at: '2026-07-09T18:00:00',
      title: 'One million messages',
      summary: 'The scene crossed a million messages this window.',
      creator_display_name: null,
    },
  ],
})

const emptyPayload = () => ({
  days: 7,
  totals: {
    streams: 0, hours_streamed: null, messages: 0, active_chatters: 0, creators_active: 0,
  },
  top_creators: [],
  top_chatters: [],
  top_moments: [],
  top_copypastas: [],
  top_emotes: [],
  notable_events: [],
})

describe('scene wrapped view-model contract', () => {
  beforeEach(() => vi.clearAllMocks())

  it('projects the full wire payload into the camelCase view model, preserving null edges', () => {
    const model = mapSceneWrapped(wirePayload())

    expect(model.days).toBe(30)
    expect(model.totals).toEqual({
      streams: 42,
      hoursStreamed: null,
      messages: 1_250_000,
      activeChatters: 8_300,
      creatorsActive: 37,
    })
    expect(model.topCreators[0]).toEqual({
      rank: 1,
      creatorId: 3,
      nick: 'acelestialcz',
      displayName: 'Celestial',
      profileImageUrl: 'https://cdn/x.png',
      totalMessages: 500_000,
      streams: 20,
      hoursStreamed: 90,
      msgsPerMin: 42.5,
      peakViewers: 12_000,
    })
    // Null-bearing creator row survives the mapper as explicit nulls.
    expect(model.topCreators[1]).toMatchObject({
      profileImageUrl: null,
      hoursStreamed: null,
      msgsPerMin: null,
      peakViewers: null,
    })
    expect(model.topChatters[1].homeCreatorDisplayName).toBeNull()
    expect(model.topMoments[1].ratio).toBeNull()
    expect(model.topMoments[0]).toMatchObject({ streamId: 100, ratio: 8.4, messageCount: 2_400 })
    expect(model.topCopypastas[0]).toMatchObject({ messageTextId: 55, usageCount: 1_200, creatorCount: 9 })
    expect(model.topEmotes[0]).toMatchObject({ emoteId: 11, name: 'PogU', source: '7tv', usage: 90_000 })
    expect(model.notableEvents[1].creatorDisplayName).toBeNull()
  })

  it('accepts an all-empty recap and flags it as empty', () => {
    const model = mapSceneWrapped(emptyPayload())
    expect(model.topCreators).toEqual([])
    expect(isWrappedEmpty(model)).toBe(true)
  })

  it('does not flag a recap with any ranked rows as empty', () => {
    expect(isWrappedEmpty(mapSceneWrapped(wirePayload()))).toBe(false)
  })

  it.each([
    ['null envelope', null],
    ['missing totals', (() => { const p = wirePayload() as Record<string, unknown>; delete p.totals; return p })()],
    ['non-array top_creators', { ...wirePayload(), top_creators: {} }],
    ['missing top_emotes', (() => { const p = wirePayload() as Record<string, unknown>; delete p.top_emotes; return p })()],
    ['non-finite totals.messages', (() => { const p = wirePayload(); p.totals.messages = Number.NaN; return p })()],
    ['moment missing message_count', (() => {
      const p = wirePayload() as any
      delete p.top_moments[0].message_count
      return p
    })()],
    ['creator hours_streamed wrong type', (() => {
      const p = wirePayload() as any
      p.top_creators[0].hours_streamed = 'lots'
      return p
    })()],
  ])('rejects malformed wrapped payloads (%s)', (_label, payload) => {
    expect(() => mapSceneWrapped(payload)).toThrow(TypeError)
  })

  it('fetches the recap with the default window and maps it', async () => {
    api.retrieveSceneWrapped.mockResolvedValue(wirePayload())
    const { result } = renderHook(() => useSceneWrapped(), { wrapper: createWrapper() })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.retrieveSceneWrapped).toHaveBeenCalledWith(30)
    expect(result.current.data?.topCreators[0].creatorId).toBe(3)
  })

  it('threads a non-default window into the request and cache key', async () => {
    api.retrieveSceneWrapped.mockResolvedValue(emptyPayload())
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const { result } = renderHook(() => useSceneWrapped(90), { wrapper: createWrapper(client) })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(api.retrieveSceneWrapped).toHaveBeenCalledWith(90)
    expect(client.getQueryCache().find({
      queryKey: ['scene', 'wrapped', { days: 90 }],
    })).toBeDefined()
  })

  it('surfaces a malformed response as a boundary TypeError', async () => {
    api.retrieveSceneWrapped.mockResolvedValue({})
    const { result } = renderHook(() => useSceneWrapped(), { wrapper: createWrapper() })

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.error).toBeInstanceOf(TypeError)
  })

  it('does not fetch when the query is disabled', async () => {
    renderHook(() => useSceneWrapped(30, { enabled: false }), { wrapper: createWrapper() })
    await new Promise(resolve => setTimeout(resolve, 0))
    expect(api.retrieveSceneWrapped).not.toHaveBeenCalled()
  })
})

describe('WrappedRecap rendering', () => {
  const model = (): SceneWrapped => mapSceneWrapped(wirePayload())

  it('renders the hero totals, rendering an em-dash for unknown hours', () => {
    render(<WrappedRecap wrapped={model()} />)
    expect(screen.getByText('Messages', { selector: '.stat-label' })).toBeInTheDocument()
    // Hours tile is null -> em-dash.
    const hoursTile = screen.getByText('Hours').closest('.stat-tile')
    expect(hoursTile).not.toBeNull()
    expect(hoursTile).toHaveTextContent('—')
  })

  it('links creators, chatters, moments, and copypastas to their detail routes', () => {
    render(<WrappedRecap wrapped={model()} />)
    expect(screen.getByRole('link', { name: /Celestial/ })).toHaveAttribute('href', '/creator/3')
    expect(screen.getByRole('link', { name: 'topchatter' })).toHaveAttribute('href', '/chatter/7')
    expect(screen.getByRole('link', { name: 'INSANE clutch' })).toHaveAttribute('href', '/stream/100')
    expect(screen.getByRole('link', { name: 'aware' })).toHaveAttribute('href', '/copypasta/55')
  })

  it('shows a ratio hype chip only for moments with a ratio', () => {
    render(<WrappedRecap wrapped={model()} />)
    expect(screen.getByText('×8.4')).toBeInTheDocument()
    // The null-ratio moment renders no hype chip; only one ×-prefixed hype exists.
    expect(screen.getAllByText(/^×/).filter(el => el.classList.contains('wrapped-moment-hype'))).toHaveLength(1)
  })

  it('skips sections whose arrays are empty', () => {
    const sparse = model()
    sparse.topEmotes = []
    sparse.notableEvents = []
    render(<WrappedRecap wrapped={sparse} />)
    expect(screen.queryByText('Top emotes')).not.toBeInTheDocument()
    expect(screen.queryByText('Notable events')).not.toBeInTheDocument()
    // A populated section still renders.
    expect(screen.getByText('Top creators')).toBeInTheDocument()
  })
})
