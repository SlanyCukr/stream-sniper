import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  useChatterStreamActivity: vi.fn(),
  useMessages: vi.fn(),
  useCommunityOverlap: vi.fn(),
  useCreatorNeighbors: vi.fn(),
  useCreatorRegulars: vi.fn(),
  useCreatorTrends: vi.fn(),
  useCreators: vi.fn(),
  push: vi.fn(),
}))

vi.mock('@/hooks/chatter/useChattersQuery', () => ({
  useChatterStreamActivity: mocks.useChatterStreamActivity,
}))
vi.mock('@/hooks/creator/useCreatorsQuery', () => ({
  useCreators: mocks.useCreators,
  mapCreatorOption: (creator: { creatorId: number; nick: string }) => ({
    value: creator.creatorId,
    label: creator.nick,
  }),
}))
vi.mock('@/hooks/chatter/useMessagesQuery', () => ({ useMessages: mocks.useMessages }))
vi.mock('@/hooks/community/useCommunityQuery', () => ({
  useCommunityOverlap: mocks.useCommunityOverlap,
  useCreatorNeighbors: mocks.useCreatorNeighbors,
}))
vi.mock('@/hooks/creator/useCreatorRegularsQuery', () => ({ useCreatorRegulars: mocks.useCreatorRegulars }))
vi.mock('@/hooks/creator/useCreatorTrendsQuery', () => ({ useCreatorTrends: mocks.useCreatorTrends }))
vi.mock('next/navigation', () => ({ useRouter: () => ({ push: mocks.push }) }))

import ChatterFootprintPanel from '@/components/chatter/ChatterFootprintPanel'
import ChatterMessagesPanel from '@/components/chatter/ChatterMessagesPanel'
import RegularsPanel from '@/components/creator/RegularsPanel'
import TrendsPanel from '@/components/creator/TrendsPanel'
import ChatterExplorer from '@/views/chatter/ChatterExplorer'
import Community from '@/views/community/Community'
import CreatorHub from '@/views/creator/CreatorHub'

const ready = (data: unknown) => ({
  data,
  isLoading: false,
  isRefetching: false,
  error: null,
  refetch: vi.fn(),
})

describe('chatter explorer', () => {
  beforeEach(() => vi.clearAllMocks())

  it('renders a selected chatter footprint from its named view model', () => {
    mocks.useChatterStreamActivity.mockReturnValue(ready([
      {
        streamId: 10,
        streamTitle: 'Launch stream',
        start: '2026-01-01T12:00:00',
        creatorId: 7,
        creatorDisplayName: 'creator',
        messageCount: 42,
        isBot: null,
      },
    ]))
    render(<ChatterFootprintPanel chatter={{ value: 5, label: 'alice', isBot: false }} />)

    expect(screen.getByRole('region', { name: 'Chatter footprint results' })).toHaveTextContent('Launch stream')
    expect(screen.getByRole('link', { name: 'Launch stream' })).toHaveAttribute('href', '/stream/10')
    expect(screen.getByText('42')).toBeInTheDocument()
  })

  it('renders paginated chatter messages with stream context', () => {
    mocks.useMessages.mockReturnValue(ready({
      items: [{
        streamId: 10,
        streamTitle: 'Launch stream',
        creatorDisplayName: 'creator',
        text: 'hello chat',
        timestamp: '2026-01-01T12:00:00',
      }],
      total: 1,
      pageCount: 1,
    }))
    render(<ChatterMessagesPanel chatter={{ value: 5, label: 'alice', isBot: false }} />)

    expect(screen.getByRole('region', { name: 'Chatter messages results' })).toHaveTextContent('hello chat')
    expect(screen.getByRole('link', { name: 'Launch stream' })).toHaveAttribute('href', '/stream/10')
  })

  it('preserves the requested initial tab and switches panel ownership', () => {
    mocks.useChatterStreamActivity.mockReturnValue(ready([]))
    mocks.useMessages.mockReturnValue(ready({ items: [], total: 0, pageCount: 0 }))
    render(<ChatterExplorer initialView="messages" />)

    expect(screen.getByRole('tab', { name: 'Messages' })).toHaveAttribute('aria-selected', 'true')
    fireEvent.click(screen.getByRole('tab', { name: 'Footprint' }))
    expect(screen.getByRole('tabpanel')).toHaveTextContent('Search for a chatter nickname')
  })
})

describe('community overlap', () => {
  it('keeps matrix and table selection synchronized across both metrics', () => {
    mocks.useCommunityOverlap.mockReturnValue({
      ...ready({
      creators: [
        { creatorId: 1, nick: 'alpha', displayName: 'Alpha', chatters: 100, regulars: 20 },
        { creatorId: 2, nick: 'beta', displayName: 'Beta', chatters: 80, regulars: 30 },
      ],
      pairs: [{
        a: 1,
        b: 2,
        sharedChatters: 25,
        sharedRegulars: 8,
        jaccardChatters: 0.2,
        jaccardRegulars: 0.1,
      }],
      computedAt: '2026-01-01T00:00:00Z',
      }),
      isRefetching: true,
    })
    mocks.useCreatorNeighbors.mockReturnValue(ready({ neighbors: [] }))
    const { container } = render(<Community />)

    expect(container.querySelector('.community-grid')).toHaveClass('is-refetching')

    const overlapCell = screen.getByRole('button', { name: /Alpha by Beta: 25 shared, 20.0% Jaccard/ })
    fireEvent.mouseEnter(overlapCell)
    expect(screen.getByText('Jaccard 20.0%')).toBeInTheDocument()
    fireEvent.mouseLeave(overlapCell)
    expect(screen.queryByText('Jaccard 20.0%')).not.toBeInTheDocument()
    fireEvent.keyDown(overlapCell, { key: 'Enter' })
    expect(screen.getByText('shared chatters').nextSibling).toHaveTextContent('25')
    expect(screen.getByRole('region', { name: 'Overlap pairs' })).toHaveTextContent('20.0%')

    fireEvent.click(screen.getByRole('tab', { name: 'Regulars' }))
    expect(screen.getByRole('region', { name: 'Overlap pairs' })).toHaveTextContent('10.0%')
    expect(screen.getByRole('img', { name: /Audience overlap matrix/ })).toBeInTheDocument()
  })
})

describe('creator trends and regulars', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.useCreators.mockReturnValue(ready([{ creatorId: 1, nick: 'alpha' }]))
  })

  it('clamps regular thresholds and requests server-side sorting', () => {
    mocks.useCreatorRegulars.mockReturnValue(ready({
      regulars: [{
        chatterId: 5,
        nick: 'alice',
        streamsAttended: 8,
        attendanceRate: 0.8,
        lastSeen: '2026-01-01T00:00:00Z',
        messageCount: 500,
      }],
      totalStreams: 10,
    }))
    render(<RegularsPanel creatorId={1} />)

    expect(screen.getByRole('region', { name: 'Creator regulars' })).toHaveTextContent('alice')
    fireEvent.change(screen.getByLabelText('Min streams attended'), { target: { value: '5000' } })
    expect(mocks.useCreatorRegulars).toHaveBeenLastCalledWith(1, expect.objectContaining({ minStreams: 1000 }))
    fireEvent.click(screen.getByRole('button', { name: 'Messages' }))
    expect(mocks.useCreatorRegulars).toHaveBeenLastCalledWith(1, expect.objectContaining({ sort: 'messages' }))
  })

  it('renders nullable trend series and deep-links each stream point', () => {
    mocks.useCreatorTrends.mockReturnValue(ready({
      streams: [{
        streamId: 10,
        title: 'Launch',
        start: '2026-01-01T00:00:00Z',
        durationSec: 5400,
        msgsPerMin: 20,
        uniqueChatters: 100,
        newChatters: 30,
        returningChatters: 70,
      }],
    }))
    render(<TrendsPanel creatorId={1} />)

    const trends = screen.getByRole('group', { name: 'Creator per-stream trends' })
    expect(trends).toHaveTextContent('Messages / min20')
    expect(trends).toHaveTextContent('Unique chatters100')
    expect(trends).toHaveTextContent('Duration1h 30m')
    expect(screen.getAllByRole('link', { name: /Launch/ })).toHaveLength(4)
    fireEvent.click(screen.getAllByRole('link', { name: /Launch/ })[0])
    expect(mocks.push).toHaveBeenCalledWith('/stream/10')
  })

  it('switches the creator hub between its two owned views', () => {
    mocks.useCreatorRegulars.mockReturnValue(ready({ regulars: [], totalStreams: 0 }))
    mocks.useCreatorTrends.mockReturnValue(ready({ streams: [] }))
    render(<CreatorHub initialView="regulars" />)

    expect(screen.getByRole('tabpanel')).toHaveTextContent('Select a creator to see their most loyal chatters')
    fireEvent.click(screen.getByRole('tab', { name: 'Trends' }))
    expect(screen.getByRole('tabpanel')).toHaveTextContent('Select a creator to see per-stream engagement trends')
  })
})
