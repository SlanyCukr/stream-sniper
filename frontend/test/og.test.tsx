import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  fetchChatterOgData,
  fetchCreatorOgData,
  fetchStreamOgData,
  GENERIC_OG_CARD,
  mapChatterOg,
  mapCreatorOg,
  mapStreamOg,
  truncate,
} from '@/lib/og/fetchOgData'
import { OgCard } from '@/lib/og/ogCard'

// A representative chatter passport wire payload (superset of the fields the OG
// card reads), matching lib/api/chatter.ts ChatterPassportDto.
const chatterPayload = {
  chatter: { id: 42, nick: 'operator', is_bot: null, bot_reason: null },
  totals: {
    messages: 128_400,
    streams_attended: 90,
    creators_visited: 12,
    first_seen: null,
    last_seen: null,
  },
  debut: null,
  home_channel: {
    creator_id: 5,
    creator_nick: 'forsen',
    creator_display_name: 'Forsen',
    messages: 5000,
    share: 0.4,
  },
  loyalty: [],
  milestones: { most_active_stream: null },
  archetypes: [
    { key: 'loyalist', label: 'Loyalist', description: 'Sticks to one channel' },
    { key: 'nightowl', label: 'Night Owl', description: 'Late sessions' },
    { key: 'globetrotter', label: 'Globetrotter', description: 'Many channels' },
    { key: 'extra', label: 'Extra', description: 'Should be sliced off' },
  ],
}

const streamPayload = {
  info: {
    title: 'road to the finals — day 3',
    start: '2026-07-18T10:00:00Z',
    end: null,
    thumbnail_url: null,
    message_count: 9421,
    creator_nick: 'forsen',
    creator_display_name: 'Forsen',
    profile_image_url: null,
    creator_id: 5,
  },
  most_active_chatters: [],
  most_tagged_chatters: [],
  other_creators: [],
  chatters: [{ chatter_id: 1, nick: 'a' }, { chatter_id: 2, nick: 'b' }, { chatter_id: 3, nick: 'c' }],
}

const creatorPayload = {
  creator_id: 5,
  nick: 'forsen',
  display_name: 'Forsen',
  profile_image_url: null,
  twitch_id: '123',
  total_streams: 220,
  first_stream_at: null,
  last_stream_at: null,
  total_messages: 3_400_000,
  duration_seconds: null,
  messages_per_minute: null,
  audience_size: 48_000,
  regulars: 1200,
  latest_stream: null,
}

describe('OG card mappers', () => {
  it('maps a full chatter passport, slicing archetype tags to three', () => {
    expect(mapChatterOg(chatterPayload)).toEqual({
      kind: 'CHATTER PASSPORT',
      title: 'operator',
      subtitle: 'Home channel · Forsen',
      stats: [
        { label: 'Messages', value: '128.4K' },
        { label: 'Channels', value: '12' },
      ],
      tags: ['Loyalist', 'Night Owl', 'Globetrotter'],
    })
  })

  it('drops the home-channel subtitle and tags when absent, keeping the card valid', () => {
    const card = mapChatterOg({
      chatter: { nick: 'lurker' },
      totals: { messages: 3, creators_visited: 1 },
      home_channel: null,
      archetypes: [],
    })
    expect(card).toMatchObject({ title: 'lurker', tags: [] })
    expect(card?.subtitle).toBeUndefined()
  })

  it('ignores malformed archetype entries without a string label', () => {
    const card = mapChatterOg({
      chatter: { nick: 'x' },
      totals: {},
      home_channel: null,
      archetypes: [{ label: 42 }, 'nope', { label: 'Real' }],
    })
    expect(card?.tags).toEqual(['Real'])
    expect(card?.stats).toEqual([])
  })

  it('returns null for a chatter payload with no nick or wrong shape', () => {
    expect(mapChatterOg({ chatter: { nick: '' }, totals: {} })).toBeNull()
    expect(mapChatterOg({ totals: {} })).toBeNull()
    expect(mapChatterOg(null)).toBeNull()
    expect(mapChatterOg('bad')).toBeNull()
    expect(mapChatterOg([1, 2])).toBeNull()
  })

  it('maps a full stream with a "by creator" subtitle and chatter-count stat', () => {
    expect(mapStreamOg(streamPayload)).toEqual({
      kind: 'STREAM REPORT',
      title: 'road to the finals — day 3',
      subtitle: 'by Forsen',
      stats: [
        { label: 'Messages', value: '9.4K' },
        { label: 'Chatters', value: '3' },
      ],
      tags: [],
    })
  })

  it('falls back to the creator name as the stream title when the title is missing', () => {
    const card = mapStreamOg({ info: { title: null, creator_display_name: 'Forsen', message_count: 10 } })
    expect(card?.title).toBe('Forsen')
    expect(card?.subtitle).toBeUndefined()
    expect(card?.stats).toEqual([{ label: 'Messages', value: '10' }])
  })

  it('returns null for a stream with neither title nor creator, or no info', () => {
    expect(mapStreamOg({ info: { title: null, creator_display_name: null } })).toBeNull()
    expect(mapStreamOg({})).toBeNull()
    expect(mapStreamOg(null)).toBeNull()
  })

  it('maps a full creator summary with three stats and a regulars subtitle', () => {
    expect(mapCreatorOg(creatorPayload)).toEqual({
      kind: 'CREATOR DOSSIER',
      title: 'Forsen',
      subtitle: '1.2K regulars',
      stats: [
        { label: 'Streams', value: '220' },
        { label: 'Messages', value: '3.4M' },
        { label: 'Audience', value: '48K' },
      ],
      tags: [],
    })
  })

  it('uses the nick when a creator has no display name, and drops the subtitle when regulars is absent', () => {
    const card = mapCreatorOg({ nick: 'forsen', display_name: null, total_streams: 5 })
    expect(card?.title).toBe('forsen')
    expect(card?.subtitle).toBeUndefined()
    expect(card?.stats).toEqual([{ label: 'Streams', value: '5' }])
  })

  it('returns null for a creator payload with no name', () => {
    expect(mapCreatorOg({ display_name: null, nick: null })).toBeNull()
    expect(mapCreatorOg(null)).toBeNull()
  })
})

describe('truncate + generic fallback', () => {
  it('leaves short text untouched and clips long text with an ellipsis', () => {
    expect(truncate('short', 64)).toBe('short')
    const long = 'a'.repeat(100)
    const clipped = truncate(long, 10)
    expect(clipped).toHaveLength(10)
    expect(clipped.endsWith('…')).toBe(true)
  })

  it('exposes a fully-formed branded fallback card', () => {
    expect(GENERIC_OG_CARD).toMatchObject({
      kind: 'SCENE ANALYTICS',
      title: 'Stream Sniper',
      stats: [],
      tags: [],
    })
    expect(typeof GENERIC_OG_CARD.subtitle).toBe('string')
  })
})

describe('best-effort server fetch', () => {
  afterEach(() => vi.unstubAllGlobals())

  const stubFetch = (impl: () => Promise<unknown>) => vi.stubGlobal('fetch', vi.fn(impl))

  it('maps a successful chatter fetch through the pure mapper', async () => {
    stubFetch(async () => ({ ok: true, json: async () => chatterPayload }))
    await expect(fetchChatterOgData('42')).resolves.toMatchObject({ title: 'operator' })
  })

  it('resolves to null when the backend returns a non-2xx status', async () => {
    stubFetch(async () => ({ ok: false, json: async () => ({}) }))
    await expect(fetchStreamOgData('7')).resolves.toBeNull()
  })

  it('resolves to null when the fetch rejects (timeout / network down)', async () => {
    stubFetch(async () => { throw new Error('aborted') })
    await expect(fetchCreatorOgData('5')).resolves.toBeNull()
  })

  it('resolves to null when the response body is not valid JSON', async () => {
    stubFetch(async () => ({ ok: true, json: async () => { throw new SyntaxError('bad json') } }))
    await expect(fetchChatterOgData('42')).resolves.toBeNull()
  })
})

describe('OgCard element tree (Satori-compatible, not rendered here)', () => {
  it('builds a flex-rooted div for a data-rich card', () => {
    const element = OgCard({
      data: {
        kind: 'CHATTER PASSPORT',
        title: 'operator',
        subtitle: 'Home channel · Forsen',
        stats: [{ label: 'Messages', value: '128.4K' }],
        tags: ['Loyalist'],
      },
    })
    expect(element.type).toBe('div')
    expect(element.props.style.display).toBe('flex')
    expect(Array.isArray(element.props.children)).toBe(true)
  })

  it('builds the domain-only footer branch for the stats-less generic card', () => {
    const element = OgCard({ data: GENERIC_OG_CARD })
    expect(element.type).toBe('div')
    expect(element.props.style.display).toBe('flex')
  })
})
