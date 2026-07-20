import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, renderHook, screen, waitFor } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { resetNavigationMocks, router } from './mocks/navigation'

const api = vi.hoisted(() => ({
  retrieveCreatorHeadToHead: vi.fn(),
}))

const sceneHooks = vi.hoisted(() => ({
  useSceneTrendingEmotes: vi.fn(),
}))

const creatorHooks = vi.hoisted(() => ({
  useCreators: vi.fn(),
}))

vi.mock('@/lib/api/community', () => api)
vi.mock('@/hooks/scene/useSceneTrendingQueries', () => sceneHooks)
vi.mock('@/hooks/creator/useCreatorsQuery', async () => ({
  ...(await vi.importActual<object>('@/hooks/creator/useCreatorsQuery')),
  useCreators: creatorHooks.useCreators,
}))

import {
  mapCreatorHeadToHead,
  useCreatorHeadToHead,
} from '@/hooks/community/useHeadToHeadQuery'
import Versus from '@/views/community/Versus'
import EmoteEconomy from '@/views/scene/EmoteEconomy'

const createWrapper = (queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
})) => function Wrapper({ children }: PropsWithChildren) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

const sideA = {
  creator_id: 3,
  nick: 'alpha',
  display_name: 'Alpha',
  chatters: 1000,
  regulars: 120,
  shared_chatter_share: 0.25,
  shared_regular_share: 0.1,
}

const sideB = {
  creator_id: 9,
  nick: 'bravo',
  display_name: 'Bravo',
  chatters: 500,
  regulars: 60,
  shared_chatter_share: 0.5,
  shared_regular_share: 0.2,
}

const headToHeadPayload = {
  a: sideA,
  b: sideB,
  shared_chatters: 250,
  shared_regulars: 12,
  jaccard_chatters: 0.2,
  jaccard_regulars: 0.0714,
  computed_at: '2026-07-18T10:00:00',
}

describe('creator head-to-head contracts', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    resetNavigationMocks()
  })

  it('maps a full payload including null share / jaccard edges', () => {
    expect(mapCreatorHeadToHead(headToHeadPayload)).toEqual({
      a: {
        creatorId: 3,
        nick: 'alpha',
        displayName: 'Alpha',
        chatters: 1000,
        regulars: 120,
        sharedChatterShare: 0.25,
        sharedRegularShare: 0.1,
      },
      b: {
        creatorId: 9,
        nick: 'bravo',
        displayName: 'Bravo',
        chatters: 500,
        regulars: 60,
        sharedChatterShare: 0.5,
        sharedRegularShare: 0.2,
      },
      sharedChatters: 250,
      sharedRegulars: 12,
      jaccardChatters: 0.2,
      jaccardRegulars: 0.0714,
      computedAt: '2026-07-18T10:00:00',
    })

    const empty = mapCreatorHeadToHead({
      ...headToHeadPayload,
      a: { ...sideA, chatters: 0, regulars: 0, shared_chatter_share: null, shared_regular_share: null },
      jaccard_chatters: null,
      jaccard_regulars: null,
      computed_at: null,
    })
    expect(empty.a.sharedChatterShare).toBeNull()
    expect(empty.jaccardChatters).toBeNull()
    expect(empty.computedAt).toBeNull()
  })

  it('rejects malformed payloads at the boundary', () => {
    expect(() => mapCreatorHeadToHead({ ...headToHeadPayload, a: null })).toThrow(TypeError)
    expect(() => mapCreatorHeadToHead({ ...headToHeadPayload, shared_chatters: 'nope' })).toThrow(TypeError)
    expect(() => mapCreatorHeadToHead({
      ...headToHeadPayload,
      b: { ...sideB, shared_chatter_share: undefined },
    })).toThrow(TypeError)
  })

  it('fetches when both creators are picked and normalizes the query key', async () => {
    api.retrieveCreatorHeadToHead.mockResolvedValue(headToHeadPayload)
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    const { result } = renderHook(
      () => useCreatorHeadToHead(9, 3),
      { wrapper: createWrapper(client) },
    )
    await waitFor(() => expect((result.current as any).isSuccess).toBe(true))

    expect(api.retrieveCreatorHeadToHead).toHaveBeenCalledWith(9, 3)
    // Key is (lo, hi) so (9,3) and (3,9) share one cache entry, mirroring the backend cache.
    expect(client.getQueryCache().find({
      queryKey: ['community', 'head-to-head', { a: 3, b: 9 }],
    })).toBeDefined()
  })

  it('stays idle without two distinct creators', async () => {
    renderHook(() => useCreatorHeadToHead(null, 3), { wrapper: createWrapper() })
    renderHook(() => useCreatorHeadToHead(4, 4), { wrapper: createWrapper() })
    await new Promise(resolve => setTimeout(resolve, 0))
    expect(api.retrieveCreatorHeadToHead).not.toHaveBeenCalled()
  })
})

describe('Versus view', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    resetNavigationMocks()
    creatorHooks.useCreators.mockReturnValue({
      data: [
        { creatorId: 3, nick: 'Alpha' },
        { creatorId: 9, nick: 'Bravo' },
      ],
    })
  })

  it('renders the matchup oriented to the picker order, not the normalized payload', async () => {
    api.retrieveCreatorHeadToHead.mockResolvedValue(headToHeadPayload)
    // Left picker holds creator 9 (Bravo) — the payload's *b* side.
    render(<Versus initialA={9} initialB={3} />, { wrapper: createWrapper() })

    await waitFor(() => expect(screen.getByText('Shared chatters')).toBeInTheDocument())
    const names = screen.getAllByRole('link').map(link => link.textContent)
    expect(names.indexOf('Bravo')).toBeLessThan(names.indexOf('Alpha'))
    expect(screen.getByText('250')).toBeInTheDocument()
    expect(screen.getByText('20.0%')).toBeInTheDocument()
  })

  it('deep-links picker changes into the URL without fetching a half-empty pair', async () => {
    render(<Versus />, { wrapper: createWrapper() })
    expect(screen.getByText('Pick two creators')).toBeInTheDocument()
    expect(api.retrieveCreatorHeadToHead).not.toHaveBeenCalled()
    expect(router.replace).not.toHaveBeenCalled()
  })

  it('flags picking the same creator on both sides', () => {
    api.retrieveCreatorHeadToHead.mockResolvedValue(headToHeadPayload)
    render(<Versus initialA={3} initialB={3} />, { wrapper: createWrapper() })
    expect(screen.getByText('Same creator on both sides')).toBeInTheDocument()
    expect(api.retrieveCreatorHeadToHead).not.toHaveBeenCalled()
  })
})

describe('EmoteEconomy view', () => {
  beforeEach(() => vi.clearAllMocks())

  const emote = {
    emoteId: 11,
    name: 'PogU',
    source: '7tv',
    providerId: null,
    currentUsage: 90,
    priorUsage: 40,
    deltaPct: 125,
    trend: 'rising',
    chatterReach: 42,
    creatorCount: 6,
    firstSeen: '2026-06-01T00:00:00',
  }

  it('requests the full 50-row board and renders channels / reach / first seen', () => {
    sceneHooks.useSceneTrendingEmotes.mockReturnValue({
      data: { window: 7, items: [emote] },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    })
    render(<EmoteEconomy />)

    expect(sceneHooks.useSceneTrendingEmotes).toHaveBeenCalledWith({ window: 7, limit: 50 })
    expect(screen.getByText('PogU')).toBeInTheDocument()
    expect(screen.getByText('7tv')).toBeInTheDocument()
    expect(screen.getByText('▲ +125%')).toBeInTheDocument()
    expect(screen.getByText('6')).toBeInTheDocument()
    expect(screen.getByText('42')).toBeInTheDocument()
    expect(screen.getByText('Jun 1, 2026')).toBeInTheDocument()
  })

  it('shows the empty state when nothing clears the usage floor', () => {
    sceneHooks.useSceneTrendingEmotes.mockReturnValue({
      data: { window: 7, items: [] },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    })
    render(<EmoteEconomy />)
    expect(screen.getByText('No emotes cleared the floor in this window')).toBeInTheDocument()
  })
})
