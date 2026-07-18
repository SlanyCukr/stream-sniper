import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  retrieveChatterPassport: vi.fn(),
}))

vi.mock('@/lib/api/chatter', () => api)

import {
  chatterPassportKeys,
  formatSharePct,
  mapChatterPassport,
  shareBarWidth,
  useChatterPassport,
} from '@/hooks/chatter/useChatterPassportQuery'

const fullPayload = {
  chatter: { id: 7, nick: 'alice', is_bot: null, bot_reason: null },
  totals: {
    messages: 1200,
    streams_attended: 18,
    creators_visited: 4,
    first_seen: '2026-01-01T12:00:00',
    last_seen: '2026-06-01T09:30:00',
  },
  debut: {
    stream_id: 10,
    stream_title: 'Launch stream',
    creator_display_name: 'Creator One',
    time: '2026-01-01T12:00:00',
  },
  home_channel: {
    creator_id: 3,
    creator_nick: 'creatorone',
    creator_display_name: 'Creator One',
    messages: 900,
    share: 0.75,
  },
  loyalty: [
    {
      creator_id: 3,
      creator_nick: 'creatorone',
      creator_display_name: 'Creator One',
      messages: 900,
      streams_attended: 12,
      share: 0.75,
    },
  ],
  milestones: {
    most_active_stream: {
      stream_id: 42,
      title: 'Marathon',
      creator_display_name: 'Creator One',
      messages: 300,
    },
  },
  archetypes: [
    { key: 'loyalist', label: 'Loyalist', description: 'Most messages land in one home channel.' },
  ],
}

const createClient = () => new QueryClient({
  defaultOptions: { queries: { retry: false } },
})

function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: PropsWithChildren) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('chatter passport pure logic', () => {
  it('formats a fractional share as a single-decimal percentage', () => {
    expect(formatSharePct(0.75)).toBe('75.0%')
    expect(formatSharePct(0.1234)).toBe('12.3%')
    expect(formatSharePct(0)).toBe('0.0%')
    expect(formatSharePct(1)).toBe('100.0%')
  })

  it('clamps the share bar width between 2 and 100', () => {
    expect(shareBarWidth(0)).toBe(2)
    expect(shareBarWidth(0.001)).toBe(2)
    expect(shareBarWidth(0.5)).toBe(50)
    expect(shareBarWidth(1)).toBe(100)
    expect(shareBarWidth(2)).toBe(100)
  })

  it('maps a full passport payload into the camelCase view model', () => {
    expect(mapChatterPassport(fullPayload)).toEqual({
      chatter: { id: 7, nick: 'alice', isBot: null, botReason: null },
      totals: {
        messages: 1200,
        streamsAttended: 18,
        creatorsVisited: 4,
        firstSeen: '2026-01-01T12:00:00',
        lastSeen: '2026-06-01T09:30:00',
      },
      debut: {
        streamId: 10,
        streamTitle: 'Launch stream',
        creatorDisplayName: 'Creator One',
        time: '2026-01-01T12:00:00',
      },
      homeChannel: {
        creatorId: 3,
        creatorNick: 'creatorone',
        creatorDisplayName: 'Creator One',
        messages: 900,
        share: 0.75,
      },
      loyalty: [
        {
          creatorId: 3,
          creatorNick: 'creatorone',
          creatorDisplayName: 'Creator One',
          messages: 900,
          streamsAttended: 12,
          share: 0.75,
        },
      ],
      milestones: {
        mostActiveStream: {
          streamId: 42,
          title: 'Marathon',
          creatorDisplayName: 'Creator One',
          messages: 300,
        },
      },
      archetypes: [
        { key: 'loyalist', label: 'Loyalist', description: 'Most messages land in one home channel.' },
      ],
    })
  })

  it('maps null debut / home channel / milestone / timestamps to null', () => {
    const mapped = mapChatterPassport({
      chatter: { id: 9, nick: 'bot9000', is_bot: true, bot_reason: 'copypasta spam' },
      totals: {
        messages: 0,
        streams_attended: 0,
        creators_visited: 0,
        first_seen: null,
        last_seen: null,
      },
      debut: null,
      home_channel: null,
      loyalty: [],
      milestones: { most_active_stream: null },
      archetypes: [],
    })
    expect(mapped.debut).toBeNull()
    expect(mapped.homeChannel).toBeNull()
    expect(mapped.milestones.mostActiveStream).toBeNull()
    expect(mapped.totals.firstSeen).toBeNull()
    expect(mapped.totals.lastSeen).toBeNull()
    expect(mapped.chatter).toEqual({ id: 9, nick: 'bot9000', isBot: true, botReason: 'copypasta spam' })
    expect(mapped.loyalty).toEqual([])
    expect(mapped.archetypes).toEqual([])
  })

  it.each([
    [{}, 'chatter passport.chatter must be an object'],
    [{ ...fullPayload, loyalty: {} }, 'chatter passport.loyalty must be an array'],
    [
      { ...fullPayload, debut: { stream_id: 10, stream_title: 'x', creator_display_name: 'c' } },
      'chatter passport.debut.time must be a string',
    ],
  ])('rejects malformed passport payloads', (payload, message) => {
    expect(() => mapChatterPassport(payload)).toThrow(message)
  })
})

describe('useChatterPassport query', () => {
  beforeEach(() => vi.clearAllMocks())

  it('maps and caches the passport under the authoritative key', async () => {
    api.retrieveChatterPassport.mockResolvedValue({ data: fullPayload })
    const queryClient = createClient()
    const hook = renderHook(() => useChatterPassport(7), {
      wrapper: createWrapper(queryClient),
    })

    await waitFor(() => expect(hook.result.current.isSuccess).toBe(true))
    expect(api.retrieveChatterPassport).toHaveBeenCalledWith(7)
    expect(queryClient.getQueryData(chatterPassportKeys.passport(7))).toEqual(
      mapChatterPassport(fullPayload),
    )
  })

  it('does not call the adapter for a non-positive chatter id', async () => {
    renderHook(() => useChatterPassport(0), { wrapper: createWrapper(createClient()) })
    await new Promise(resolve => setTimeout(resolve, 0))
    expect(api.retrieveChatterPassport).not.toHaveBeenCalled()
  })
})
