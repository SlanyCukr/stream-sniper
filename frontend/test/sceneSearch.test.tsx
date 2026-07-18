import { describe, expect, it } from 'vitest'

import { splitHighlight } from '@/components/scene/searchHighlight'
import {
  SEARCH_DAY_WINDOWS,
  buildSearchQueryString,
  readSearchState,
} from '@/hooks/scene/searchUrlState'
import {
  isSearchableQuery,
  mapSearchFirst,
  mapSearchFrequency,
  mapSearchMessages,
} from '@/hooks/scene/useSearchQueries'

describe('splitHighlight', () => {
  it('splits a match out of surrounding text', () => {
    expect(splitHighlight('hello world', 'world')).toEqual([
      { text: 'hello ', match: false },
      { text: 'world', match: true },
    ])
  })

  it('matches case-insensitively but preserves the original casing', () => {
    expect(splitHighlight('Hello World', 'hello')).toEqual([
      { text: 'Hello', match: true },
      { text: ' World', match: false },
    ])
  })

  it('treats the query as literal text, not a regex', () => {
    expect(splitHighlight('a.b.c', '.')).toEqual([
      { text: 'a', match: false },
      { text: '.', match: true },
      { text: 'b', match: false },
      { text: '.', match: true },
      { text: 'c', match: false },
    ])
  })

  it('returns a single non-match segment when nothing matches or query is blank', () => {
    expect(splitHighlight('nothing here', 'zzz')).toEqual([{ text: 'nothing here', match: false }])
    expect(splitHighlight('text', '   ')).toEqual([{ text: 'text', match: false }])
    expect(splitHighlight('', 'x')).toEqual([{ text: '', match: false }])
  })

  it('never drops characters — segments reconstruct the original text', () => {
    const text = 'POG poggers PogChamp pOg'
    const joined = splitHighlight(text, 'pog').map(segment => segment.text).join('')
    expect(joined).toBe(text)
  })
})

describe('search URL state mapping', () => {
  it('reads shareable filter state from the query string', () => {
    expect(readSearchState(new URLSearchParams('q=pog&creator_id=5&days=30'))).toEqual({
      q: 'pog',
      creatorId: 5,
      days: 30,
    })
  })

  it('rejects out-of-vocabulary day windows and non-numeric ids', () => {
    expect(readSearchState(new URLSearchParams('q=x&creator_id=abc&days=45'))).toEqual({
      q: 'x',
      creatorId: null,
      days: null,
    })
  })

  it('defaults missing params to empty / all-time', () => {
    expect(readSearchState(new URLSearchParams(''))).toEqual({ q: '', creatorId: null, days: null })
  })

  it('accepts every documented day window', () => {
    for (const window of SEARCH_DAY_WINDOWS) {
      expect(readSearchState(new URLSearchParams(`q=x&days=${window}`)).days).toBe(window)
    }
  })

  it('serializes trimmed, non-empty state and omits all-time / no-creator', () => {
    expect(buildSearchQueryString({ q: '  pog  ', creatorId: 5, days: 30 }))
      .toBe('q=pog&creator_id=5&days=30')
    expect(buildSearchQueryString({ q: 'pog', creatorId: null, days: null })).toBe('q=pog')
    expect(buildSearchQueryString({ q: '   ', creatorId: null, days: null })).toBe('')
  })

  it('round-trips through serialize -> read', () => {
    const state = { q: 'kappa', creatorId: 12, days: 90 }
    expect(readSearchState(new URLSearchParams(buildSearchQueryString(state)))).toEqual(state)
  })
})

describe('isSearchableQuery', () => {
  it('gates on the 2-char trimmed minimum', () => {
    expect(isSearchableQuery('a')).toBe(false)
    expect(isSearchableQuery(' a ')).toBe(false)
    expect(isSearchableQuery('ab')).toBe(true)
    expect(isSearchableQuery('  pog  ')).toBe(true)
    expect(isSearchableQuery(undefined)).toBe(false)
  })
})

const hit = {
  message_id: 1,
  time: '2026-07-18T10:00:00Z',
  text: 'pog',
  chatter: { id: 2, nick: 'viewer', is_bot: null },
  stream: { id: 3, title: 'Live' },
  creator: { id: 4, nick: 'streamer', display_name: 'Streamer' },
}

describe('search response mappers', () => {
  it('maps a message page into camelCase view models and preserves nullable is_bot', () => {
    expect(mapSearchMessages({ query: 'pog', has_more: true, items: [hit] })).toEqual({
      query: 'pog',
      hasMore: true,
      items: [{
        messageId: 1,
        time: '2026-07-18T10:00:00Z',
        text: 'pog',
        chatter: { id: 2, nick: 'viewer', isBot: null },
        stream: { id: 3, title: 'Live' },
        creator: { id: 4, nick: 'streamer', displayName: 'Streamer' },
      }],
    })
  })

  it('handles a null first hit and maps per-creator earliest hits', () => {
    const mapped = mapSearchFirst({
      query: 'pog', total_matches: 7, first: null, by_creator: [hit],
    })
    expect(mapped.first).toBeNull()
    expect(mapped.totalMatches).toBe(7)
    expect(mapped.byCreator[0]).toMatchObject({ messageId: 1, creator: { displayName: 'Streamer' } })
  })

  it('maps the zero-filled frequency series', () => {
    expect(mapSearchFrequency({
      query: 'pog', days: 90, points: [{ date: '2026-07-17', count: 0 }, { date: '2026-07-18', count: 3 }],
    })).toEqual({
      query: 'pog',
      days: 90,
      points: [{ date: '2026-07-17', count: 0 }, { date: '2026-07-18', count: 3 }],
    })
  })

  it('rejects malformed payloads at the boundary', () => {
    expect(() => mapSearchMessages({ query: 'pog', items: [] })).toThrow(TypeError)
    expect(() => mapSearchFirst({ query: 'pog', total_matches: 1, by_creator: [] })).toThrow(TypeError)
    expect(() => mapSearchFrequency({ query: 'pog', points: [] })).toThrow(TypeError)
  })
})
