import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { navigationState, router } from './mocks/navigation'
import { renderWithQueryClient } from './render'

const searchApi = vi.hoisted(() => ({
  retrieveSearchMessages: vi.fn(),
  retrieveSearchFirst: vi.fn(),
  retrieveSearchFrequency: vi.fn(),
  retrieveSearchContext: vi.fn(),
}))
const creatorsApi = vi.hoisted(() => ({
  retrieveAllCreators: vi.fn(),
}))
const chatterApi = vi.hoisted(() => ({
  retrieveChatterPassport: vi.fn(),
}))

vi.mock('@/lib/api/search', () => searchApi)
vi.mock('@/lib/api/creators', () => creatorsApi)
vi.mock('@/lib/api/chatter', () => chatterApi)

import ChatterPassport from '@/views/chatter/ChatterPassport'
import SceneSearch from '@/views/scene/SceneSearch'

const searchHit = (id: number, text: string) => ({
  message_id: id,
  time: '2026-07-18T10:00:00Z',
  text,
  chatter: { id: id + 100, nick: `viewer-${id}`, is_bot: null },
  stream: { id: 3, title: 'Live' },
  creator: { id: 4, nick: 'streamer', display_name: 'Streamer' },
})

const passportPayload = ({ empty = false } = {}) => ({
  chatter: { id: 7, nick: 'alice', is_bot: null, bot_reason: null },
  totals: {
    messages: empty ? 0 : 1200,
    streams_attended: empty ? 0 : 18,
    creators_visited: empty ? 0 : 4,
    first_seen: empty ? null : '2026-01-01T12:00:00Z',
    last_seen: empty ? null : '2026-06-01T09:30:00Z',
  },
  debut: empty ? null : {
    stream_id: 10,
    stream_title: 'Launch stream',
    creator_display_name: 'Creator One',
    time: '2026-01-01T12:00:00Z',
  },
  home_channel: empty ? null : {
    creator_id: 3,
    creator_nick: 'creatorone',
    creator_display_name: 'Creator One',
    messages: 900,
    share: 0.75,
  },
  loyalty: empty ? [] : [{
    creator_id: 3,
    creator_nick: 'creatorone',
    creator_display_name: 'Creator One',
    messages: 900,
    streams_attended: 12,
    share: 0.75,
  }],
  milestones: {
    most_active_stream: empty ? null : {
      stream_id: 42,
      title: 'Marathon',
      creator_display_name: 'Creator One',
      messages: 300,
    },
  },
  archetypes: [],
  companions: empty ? [] : [{ chatter_id: 11, nick: 'bestie', shared_streams: 9 }],
})

describe('SceneSearch orchestration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    navigationState.pathname = '/search'
    creatorsApi.retrieveAllCreators.mockResolvedValue([])
    searchApi.retrieveSearchFirst.mockImplementation(({ q }) => Promise.resolve({
      query: q, first: null, by_creator: [], total_matches: 0,
    }))
    searchApi.retrieveSearchFrequency.mockImplementation(({ q, days = 90 }) => Promise.resolve({
      query: q, days, points: [],
    }))
  })

  it('loads more within one filter identity and replaces those pages when the filter changes', async () => {
    navigationState.searchParams = new URLSearchParams('q=pog&days=30')
    searchApi.retrieveSearchMessages.mockImplementation(({ q, days, offset }) => {
      if (days === 7) {
        return Promise.resolve({ query: q, has_more: false, items: [searchHit(7, 'fresh pog')] })
      }
      return Promise.resolve({
        query: q,
        has_more: offset === 0,
        items: [searchHit(offset === 0 ? 1 : 2, offset === 0 ? 'first pog' : 'second pog')],
      })
    })

    const { user, rerender } = renderWithQueryClient(<SceneSearch />)

    expect(await screen.findByRole('link', { name: 'viewer-1' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Load more' }))
    expect(await screen.findByRole('link', { name: 'viewer-2' })).toBeInTheDocument()

    await user.selectOptions(screen.getByLabelText('Time window'), '7')
    expect(router.replace).toHaveBeenLastCalledWith('/search?q=pog&days=7', { scroll: false })
    navigationState.searchParams = new URLSearchParams('q=pog&days=7')
    rerender(<SceneSearch />)
    expect(await screen.findByRole('link', { name: 'viewer-7' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'viewer-1' })).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'viewer-2' })).not.toBeInTheDocument()
  })

  it('adopts URL state when navigation changes after mount', async () => {
    navigationState.searchParams = new URLSearchParams('q=first')
    searchApi.retrieveSearchMessages.mockImplementation(({ q }) => Promise.resolve({
      query: q,
      has_more: false,
      items: [searchHit(q === 'first' ? 1 : 2, q)],
    }))

    const view = renderWithQueryClient(<SceneSearch />)
    expect(await screen.findByText('first')).toBeInTheDocument()

    navigationState.searchParams = new URLSearchParams('q=second&days=7')
    view.rerender(<SceneSearch />)

    expect(await screen.findByText('second')).toBeInTheDocument()
    expect(screen.getByRole('searchbox')).toHaveValue('second')
    expect(screen.getByLabelText('Time window')).toHaveValue('7')
  })

  it('renders resolved-empty and failed searches as distinct states', async () => {
    navigationState.searchParams = new URLSearchParams('q=none')
    searchApi.retrieveSearchMessages.mockResolvedValue({
      query: 'none', has_more: false, items: [],
    })

    const empty = renderWithQueryClient(<SceneSearch />)
    expect(await screen.findByText('No messages match this search')).toBeInTheDocument()
    empty.unmount()

    navigationState.searchParams = new URLSearchParams('q=fail')
    searchApi.retrieveSearchMessages.mockRejectedValue(new Error('adapter failure'))
    renderWithQueryClient(<SceneSearch />)

    expect(await screen.findByText('Search failed')).toBeInTheDocument()
    expect(screen.queryByText('No messages match this search')).not.toBeInTheDocument()
  })
})

describe('ChatterPassport orchestration', () => {
  beforeEach(() => vi.clearAllMocks())

  it('transitions from loading chrome to a populated passport', async () => {
    let resolvePassport: (value: ReturnType<typeof passportPayload>) => void = () => undefined
    chatterApi.retrieveChatterPassport.mockReturnValue(new Promise((resolve) => {
      resolvePassport = resolve
    }))

    renderWithQueryClient(<ChatterPassport chatterId={7} />)
    expect(screen.getByRole('status', { name: 'Assembling chatter passport...' }))
      .toBeInTheDocument()

    resolvePassport(passportPayload())
    expect(await screen.findByRole('heading', { name: 'alice' })).toBeInTheDocument()
    expect(screen.getByText('Launch stream')).toBeInTheDocument()
    expect(screen.getByText('bestie')).toBeInTheDocument()
  })

  it('renders a dedicated not-found state instead of the generic query error', async () => {
    chatterApi.retrieveChatterPassport.mockRejectedValue(Object.assign(new Error('missing'), {
      response: { status: 404, data: { detail: 'missing' } },
    }))

    renderWithQueryClient(<ChatterPassport chatterId={404} />)

    expect(await screen.findByText('Chatter not found')).toBeInTheDocument()
    expect(screen.queryByText('Failed to load chatter passport')).not.toBeInTheDocument()
  })

  it('keeps a zero-history passport identifiable while presenting its empty sections', async () => {
    chatterApi.retrieveChatterPassport.mockResolvedValue(passportPayload({ empty: true }))

    renderWithQueryClient(<ChatterPassport chatterId={7} />)

    expect(await screen.findByRole('heading', { name: 'alice' })).toBeInTheDocument()
    expect(screen.getByText('No channel loyalty yet')).toBeInTheDocument()
    expect(screen.getByText('First appearance unknown.')).toBeInTheDocument()
    expect(screen.getByText('No dominant channel yet.')).toBeInTheDocument()
  })
})
