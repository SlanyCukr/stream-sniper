import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, renderHook, screen, waitFor } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  retrieveTrendingCopypastas: vi.fn(),
  retrieveTrendingEmotes: vi.fn(),
}))

vi.mock('@/lib/api/scene', () => api)

import {
  mapTrendingCopypastas,
  mapTrendingEmotes,
  useSceneTrendingCopypastas,
  useSceneTrendingEmotes,
} from '@/hooks/scene/useSceneTrendingQueries'
import TrendingBoard from '@/components/scene/TrendingBoard'
import {
  formatDeltaPct,
  trendIndicator,
  type TrendingRowModel,
} from '@/components/scene/TrendingRow'

const createWrapper = (queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
})) => function Wrapper({ children }: PropsWithChildren) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

const copypastaItem = {
  message_text_id: 7,
  text: 'aware',
  current_usage: 120,
  prior_usage: 40,
  delta_pct: 200,
  trend: 'rising',
  stream_count: 5,
  creator_count: 3,
  first_seen: '2026-07-01T00:00:00',
}

const emoteItem = {
  emote_id: 11,
  name: 'PogU',
  source: '7tv',
  provider_id: null,
  current_usage: 90,
  prior_usage: 0,
  delta_pct: null,
  trend: 'new',
  chatter_reach: 42,
  creator_count: 6,
  first_seen: null,
}

describe('scene trending velocity contracts', () => {
  beforeEach(() => vi.clearAllMocks())

  it('maps a full copypasta payload including null delta / first_seen edges', () => {
    expect(mapTrendingCopypastas({
      window: 7,
      items: [
        copypastaItem,
        { ...copypastaItem, message_text_id: 8, trend: 'new', delta_pct: null, first_seen: null },
      ],
    })).toEqual({
      window: 7,
      items: [
        {
          messageTextId: 7,
          text: 'aware',
          currentUsage: 120,
          priorUsage: 40,
          deltaPct: 200,
          trend: 'rising',
          streamCount: 5,
          creatorCount: 3,
          firstSeen: '2026-07-01T00:00:00',
        },
        {
          messageTextId: 8,
          text: 'aware',
          currentUsage: 120,
          priorUsage: 40,
          deltaPct: null,
          trend: 'new',
          streamCount: 5,
          creatorCount: 3,
          firstSeen: null,
        },
      ],
    })
  })

  it('accepts an empty copypasta board without inventing rows', () => {
    expect(mapTrendingCopypastas({ window: 30, items: [] })).toEqual({ window: 30, items: [] })
  })

  it('maps a full emote payload including null provider_id / delta_pct edges', () => {
    expect(mapTrendingEmotes({ window: 14, items: [emoteItem] })).toEqual({
      window: 14,
      items: [{
        emoteId: 11,
        name: 'PogU',
        source: '7tv',
        providerId: null,
        currentUsage: 90,
        priorUsage: 0,
        deltaPct: null,
        trend: 'new',
        chatterReach: 42,
        creatorCount: 6,
        firstSeen: null,
      }],
    })
  })

  it('rejects malformed trending envelopes at the boundary', () => {
    expect(() => mapTrendingCopypastas({ items: [] })).toThrow(TypeError)
    expect(() => mapTrendingCopypastas({ window: 7, items: [{ ...copypastaItem, delta_pct: 'nope' }] })).toThrow(TypeError)
    expect(() => mapTrendingEmotes({ window: 7, items: [{ ...emoteItem, source: null }] })).toThrow(TypeError)
  })

  it('fetches copypastas with window defaults and projects mapped rows', async () => {
    api.retrieveTrendingCopypastas.mockResolvedValue({ data: { window: 7, items: [copypastaItem] } })
    const { result } = renderHook(() => useSceneTrendingCopypastas(), { wrapper: createWrapper() })
    await waitFor(() => expect((result.current as any).isSuccess).toBe(true))

    expect(api.retrieveTrendingCopypastas).toHaveBeenCalledWith({ window: 7, creatorId: undefined, limit: 20 })
    expect((result.current as any).data.items[0]).toMatchObject({ messageTextId: 7, deltaPct: 200, trend: 'rising' })
  })

  it('threads window / creator / limit filters into the emote request and key', async () => {
    api.retrieveTrendingEmotes.mockResolvedValue({ data: { window: 30, items: [emoteItem] } })
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const { result } = renderHook(
      () => useSceneTrendingEmotes({ window: 30, creatorId: 3, limit: 5 }),
      { wrapper: createWrapper(client) },
    )
    await waitFor(() => expect((result.current as any).isSuccess).toBe(true))

    expect(api.retrieveTrendingEmotes).toHaveBeenCalledWith({ window: 30, creatorId: 3, limit: 5 })
    expect(client.getQueryCache().find({
      queryKey: ['scene', 'trending', 'emotes', { window: 30, creatorId: 3, limit: 5 }],
    })).toBeDefined()
  })

  it.each([
    ['copypastas', () => {
      api.retrieveTrendingCopypastas.mockResolvedValue({ data: {} })
      return renderHook(() => useSceneTrendingCopypastas(), { wrapper: createWrapper() })
    }],
    ['emotes', () => {
      api.retrieveTrendingEmotes.mockResolvedValue({ data: {} })
      return renderHook(() => useSceneTrendingEmotes(), { wrapper: createWrapper() })
    }],
  ])('surfaces a TypeError for malformed %s payloads', async (_name, renderTarget) => {
    const hook = renderTarget()
    await waitFor(() => expect((hook.result.current as any).isError).toBe(true))
    expect((hook.result.current as any).error).toBeInstanceOf(TypeError)
  })

  it('lets callers disable the trending queries', async () => {
    renderHook(() => useSceneTrendingCopypastas({}, { enabled: false }), { wrapper: createWrapper() })
    renderHook(() => useSceneTrendingEmotes({}, { enabled: false }), { wrapper: createWrapper() })
    await new Promise(resolve => setTimeout(resolve, 0))
    expect(api.retrieveTrendingCopypastas).not.toHaveBeenCalled()
    expect(api.retrieveTrendingEmotes).not.toHaveBeenCalled()
  })
})

describe('trend indicator + delta formatting', () => {
  it('renders sign-aware deltas and never a misleading 0% for a null baseline', () => {
    expect(formatDeltaPct(62.5)).toBe('+62.5%')
    expect(formatDeltaPct(-33.3)).toBe('-33.3%')
    expect(formatDeltaPct(0)).toBe('0%')
    expect(formatDeltaPct(null)).toBe('—')
  })

  it('maps every trend to a status-chip variant, degrading unknowns to neutral', () => {
    expect(trendIndicator('rising', 62.5)).toEqual({ variant: 'ok', label: '▲ +62.5%' })
    expect(trendIndicator('falling', -33.3)).toEqual({ variant: 'err', label: '▼ -33.3%' })
    expect(trendIndicator('new', null)).toEqual({ variant: 'neutral', label: 'new' })
    expect(trendIndicator('steady', 0)).toEqual({ variant: 'neutral', label: 'steady' })
    expect(trendIndicator('mystery', null)).toEqual({ variant: 'neutral', label: 'mystery' })
  })
})

describe('TrendingBoard rendering', () => {
  const rows: TrendingRowModel[] = [
    {
      key: 'copypasta-7',
      label: 'aware',
      href: '/copypasta/7',
      source: null,
      currentUsage: 120,
      priorUsage: 40,
      deltaPct: 200,
      trend: 'rising',
      context: [{ label: 'streams', value: 5 }, { label: 'creators', value: 3 }],
    },
  ]

  const query = (data: TrendingRowModel[] | undefined, overrides = {}) => ({
    data,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
    ...overrides,
  })

  const board = (props = {}) => (
    <TrendingBoard
      title="Copypastas"
      primaryHeader="Copypasta"
      contextHeader="Spread"
      query={query(rows)}
      loadingText="Loading…"
      errorTitle="Unable to load trending copypastas"
      emptyTitle="No trending copypastas in this window"
      emptyHint="Nothing is spiking."
      {...props}
    />
  )

  it('renders a rising row with its arrow delta and trace link', () => {
    render(board())
    expect(screen.getByRole('link', { name: 'aware' })).toHaveAttribute('href', '/copypasta/7')
    expect(screen.getByText('▲ +200%')).toBeInTheDocument()
  })

  it('shows the empty state when a board resolves with no rows', () => {
    render(board({ query: query([]) }))
    expect(screen.getByText('No trending copypastas in this window')).toBeInTheDocument()
  })
})
