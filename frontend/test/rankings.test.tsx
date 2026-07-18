import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const sceneApi = vi.hoisted(() => ({
  retrieveSceneRankings: vi.fn(),
}))
const chatterApi = vi.hoisted(() => ({
  retrieveChatterPassport: vi.fn(),
}))

vi.mock('@/lib/api/scene', () => sceneApi)
vi.mock('@/lib/api/chatter', () => chatterApi)

import {
  mapSceneRankings,
  useSceneRankings,
} from '@/hooks/scene/useSceneRankingsQueries'
import { mapChatterPassport } from '@/hooks/chatter/useChatterPassportQuery'

const rankingsPayload = {
  window: 'all',
  has_more: true,
  items: [
    {
      rank: 1,
      chatter_id: 7,
      nick: 'topchatter',
      total_messages: 5000,
      streams_attended: 42,
      creators_visited: 9,
      home_channel: {
        creator_id: 3,
        creator_nick: 'homecreator',
        creator_display_name: 'Home Creator',
        messages: 4200,
        share: 0.84,
      },
      archetypes: [
        { key: 'loyalist', label: 'Loyalist', description: 'Sticks to one home channel.' },
      ],
    },
    {
      rank: 2,
      chatter_id: 8,
      nick: 'wanderer',
      total_messages: 100,
      streams_attended: 12,
      creators_visited: 11,
      home_channel: null,
      archetypes: [],
    },
  ],
}

const createWrapper = (queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
})) => function Wrapper({ children }: PropsWithChildren) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe('scene rankings view-model contract', () => {
  beforeEach(() => vi.clearAllMocks())

  it('projects the ranked wire payload into the camelCase view model, preserving null home channels', () => {
    expect(mapSceneRankings(rankingsPayload)).toEqual({
      window: 'all',
      hasMore: true,
      items: [
        {
          rank: 1,
          chatterId: 7,
          nick: 'topchatter',
          totalMessages: 5000,
          streamsAttended: 42,
          creatorsVisited: 9,
          homeChannel: {
            creatorId: 3,
            creatorNick: 'homecreator',
            creatorDisplayName: 'Home Creator',
            messages: 4200,
            share: 0.84,
          },
          archetypes: [
            { key: 'loyalist', label: 'Loyalist', description: 'Sticks to one home channel.' },
          ],
        },
        {
          rank: 2,
          chatterId: 8,
          nick: 'wanderer',
          totalMessages: 100,
          streamsAttended: 12,
          creatorsVisited: 11,
          homeChannel: null,
          archetypes: [],
        },
      ],
    })
  })

  it('accepts an empty ranking window without inventing rows', () => {
    expect(mapSceneRankings({ window: '7', has_more: false, items: [] })).toEqual({
      window: '7',
      hasMore: false,
      items: [],
    })
  })

  it.each([
    ['missing items', { window: 'all', has_more: true }],
    ['missing has_more flag', { window: 'all', items: [] }],
    ['non-boolean has_more', { window: 'all', has_more: 'yes', items: [] }],
    ['missing home_channel key', { window: 'all', has_more: false, items: [{
      rank: 1,
      chatter_id: 1,
      nick: 'x',
      total_messages: 1,
      streams_attended: 1,
      creators_visited: 1,
      archetypes: [],
    }] }],
    ['missing archetypes key', { window: 'all', has_more: false, items: [{
      rank: 1,
      chatter_id: 1,
      nick: 'x',
      total_messages: 1,
      streams_attended: 1,
      creators_visited: 1,
      home_channel: null,
    }] }],
    ['badge missing description in archetypes', { window: 'all', has_more: false, items: [{
      rank: 1,
      chatter_id: 1,
      nick: 'x',
      total_messages: 1,
      streams_attended: 1,
      creators_visited: 1,
      home_channel: null,
      archetypes: [{ key: 'loyalist', label: 'Loyalist' }],
    }] }],
    ['null envelope', null],
  ])('rejects malformed rankings payloads (%s)', (_label, payload) => {
    expect(() => mapSceneRankings(payload)).toThrow(TypeError)
  })

  it('fetches a page through the offset-aware hook and maps it', async () => {
    sceneApi.retrieveSceneRankings.mockResolvedValue({ data: rankingsPayload })
    const { result } = renderHook(
      () => useSceneRankings({ window: '7', limit: 25, offset: 50 }),
      { wrapper: createWrapper() },
    )

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(sceneApi.retrieveSceneRankings).toHaveBeenCalledWith({ window: '7', limit: 25, offset: 50 })
    expect(result.current.data?.hasMore).toBe(true)
    expect(result.current.data?.items[0]).toMatchObject({
      chatterId: 7,
      homeChannel: { creatorId: 3 },
      archetypes: [{ key: 'loyalist', label: 'Loyalist', description: 'Sticks to one home channel.' }],
    })
    expect(result.current.data?.items[1].homeChannel).toBeNull()
    expect(result.current.data?.items[1].archetypes).toEqual([])
  })

  it('surfaces a malformed rankings response as a boundary TypeError', async () => {
    sceneApi.retrieveSceneRankings.mockResolvedValue({ data: {} })
    const { result } = renderHook(() => useSceneRankings(), { wrapper: createWrapper() })

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.error).toBeInstanceOf(TypeError)
  })

  it('does not fetch when the query is disabled', async () => {
    renderHook(() => useSceneRankings({ window: 'all' }, { enabled: false }), {
      wrapper: createWrapper(),
    })
    await new Promise(resolve => setTimeout(resolve, 0))
    expect(sceneApi.retrieveSceneRankings).not.toHaveBeenCalled()
  })
})

const passportPayload = (archetypes: unknown) => ({
  chatter: { id: 7, nick: 'alice', is_bot: null, bot_reason: null },
  totals: {
    messages: 10, streams_attended: 2, creators_visited: 1, first_seen: null, last_seen: null,
  },
  debut: null,
  home_channel: null,
  loyalty: [],
  milestones: { most_active_stream: null },
  archetypes,
  companions: [],
})

describe('chatter passport archetype badges contract', () => {
  it('maps rule-based archetype badges verbatim (no client-side derivation)', () => {
    const badges = [
      { key: 'loyalist', label: 'Loyalist', description: 'Sticks to one home channel.' },
      { key: 'marathoner', label: 'Marathoner', description: 'Shows up for the long streams.' },
    ]
    expect(mapChatterPassport(passportPayload(badges)).archetypes).toEqual(badges)
  })

  it('maps an empty badge list to an empty array', () => {
    expect(mapChatterPassport(passportPayload([])).archetypes).toEqual([])
  })

  it.each([
    ['missing archetypes key', (() => {
      const payload = passportPayload([]) as Record<string, unknown>
      delete payload.archetypes
      return payload
    })()],
    ['non-array archetypes', passportPayload({})],
    ['badge missing description', passportPayload([{ key: 'loyalist', label: 'Loyalist' }])],
    ['badge with non-string label', passportPayload([{ key: 'loyalist', label: 3, description: 'x' }])],
  ])('rejects malformed archetype payloads (%s)', (_label, payload) => {
    expect(() => mapChatterPassport(payload)).toThrow(TypeError)
  })
})
