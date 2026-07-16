import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const hooks = vi.hoisted(() => ({
  useStreamDetails: vi.fn(),
  useStreamMessages: vi.fn(),
  useStreamTimeline: vi.fn(),
}))

vi.mock('@/hooks/stream/list/useStreamsQuery', () => ({ useStreamDetails: hooks.useStreamDetails }))
vi.mock('@/hooks/stream/replay/useStreamMessagesQuery', () => ({ useStreamMessages: hooks.useStreamMessages }))
vi.mock('@/hooks/stream/timeline/useStreamTimelineQuery', () => ({ useStreamTimeline: hooks.useStreamTimeline }))
vi.mock('@/components/stream/StreamDownloadMenu', () => ({ default: () => null }))
vi.mock('@/components/stream/report/StreamReportCard', () => ({ default: () => null }))
vi.mock('@/components/stream/report/StreamStatsCard', () => ({ default: () => null }))
vi.mock('@/components/stream/insights/MentionsPanel', () => ({ default: () => null }))
vi.mock('@/components/stream/insights/EmotesPanel', () => ({ default: () => null }))
vi.mock('@/components/stream/insights/PhrasesPanel', () => ({ default: () => null }))
vi.mock('@/components/stream/timeline/StreamTimeline', () => ({
  default: ({ onJump }: { onJump: CallableFunction }) => (
    <button type="button" onClick={() => onJump('2026-07-14T10:05:00Z')}>jump target</button>
  ),
}))
vi.mock('@/components/stream/replay/StreamReplayCard', () => ({
  default: ({ replay }: {
    replay: {
      navigation: { jumpToTs: { ts: string } | null }
      messagePage: { onLoadMore: CallableFunction }
    }
  }) => (
    <div>
      <output data-testid="jump-target">{replay.navigation.jumpToTs?.ts ?? 'none'}</output>
      <button type="button" onClick={() => replay.messagePage.onLoadMore()}>load more</button>
    </div>
  ),
}))

import Stream from '@/views/stream/Stream'

const streamInfo = {
  info: {
    title: 'Title',
    start: '2026-07-14T10:00:00Z',
    end: null,
    thumbnailUrl: null,
    messageCount: 1,
    nick: 'operator',
    displayName: 'Operator',
    profileImageUrl: null,
    creatorId: 7,
  },
  mostActiveChatters: [],
  mostTaggedChatters: [],
  otherCreators: [],
  chatterOptions: [],
}

describe('Stream query and replay coordination', () => {
  const refetchStream = vi.fn()
  const refetchTimeline = vi.fn()
  const fetchNextPage = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    hooks.useStreamDetails.mockReturnValue({
      data: streamInfo,
      isLoading: false,
      error: null,
      refetch: refetchStream,
    })
    hooks.useStreamMessages.mockReturnValue({
      data: { pages: [{ messages: [{ ts: '2026-07-14T10:00:00Z' }] }] },
      error: null,
      isLoading: false,
      fetchNextPage,
      hasNextPage: true,
      isFetchingNextPage: false,
    })
    hooks.useStreamTimeline.mockReturnValue({
      data: { buckets: [] },
      error: null,
      refetch: refetchTimeline,
    })
  })

  it('renders primary errors before missing-data loading guards', () => {
    hooks.useStreamDetails.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: { response: { status: 503 }, message: 'stream offline' },
      refetch: refetchStream,
    })
    render(<Stream streamId={7} />)
    expect(screen.getByText('Failed to load stream')).toBeInTheDocument()
    expect(screen.queryByText('Loading stream data...')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /retry/i }))
    expect(refetchStream).toHaveBeenCalledOnce()
  })

  it('distinguishes a successful empty response from loading', () => {
    hooks.useStreamDetails.mockReturnValue({ data: undefined, isLoading: false, error: null, refetch: refetchStream })
    render(<Stream streamId={7} />)
    expect(screen.getByText('Stream unavailable')).toBeInTheDocument()
  })

  it('keeps stream and replay content available when the timeline fails', () => {
    hooks.useStreamTimeline.mockReturnValue({
      data: undefined,
      error: new Error('timeline offline'),
      refetch: refetchTimeline,
    })
    render(<Stream streamId={7} />)
    expect(screen.getByText('Stream intel report')).toBeInTheDocument()
    expect(screen.getByText('Timeline unavailable')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'load more' })).toBeInTheDocument()
  })

  it('labels a null stream end as live instead of formatting the Unix epoch', () => {
    render(<Stream streamId={7} />)
    expect(screen.getByText('End').nextElementSibling).toHaveTextContent('Live')
  })

  it('fetches later pages until the jump target is present', async () => {
    fetchNextPage.mockResolvedValue({
      data: { pages: [{ messages: [{ ts: '2026-07-14T10:06:00Z' }] }] },
      hasNextPage: false,
    })
    render(<Stream streamId={7} />)
    fireEvent.click(screen.getByRole('button', { name: 'jump target' }))
    await waitFor(() => expect(fetchNextPage).toHaveBeenCalledOnce())
    await waitFor(() => expect(screen.getByTestId('jump-target')).toHaveTextContent('2026-07-14T10:05:00Z'))
  })

  it('surfaces rejected jump fetches and suppresses overlapping loops', async () => {
    let rejectFetch: CallableFunction = () => undefined
    fetchNextPage.mockReturnValue(new Promise((_, reject) => { rejectFetch = reject }))
    render(<Stream streamId={7} />)
    const jump = screen.getByRole('button', { name: 'jump target' })
    fireEvent.click(jump)
    fireEvent.click(jump)
    expect(fetchNextPage).toHaveBeenCalledOnce()
    await act(async () => rejectFetch(new Error('page failed')))
    expect(screen.getByText('Failed to load replay target')).toBeInTheDocument()
    expect(screen.getByTestId('jump-target')).toHaveTextContent('none')
  })

  it('gates load-more calls while no next page is available', () => {
    hooks.useStreamMessages.mockReturnValue({
      data: { pages: [{ messages: [] }] },
      error: null,
      isLoading: false,
      fetchNextPage,
      hasNextPage: false,
      isFetchingNextPage: false,
    })
    render(<Stream streamId={7} />)
    fireEvent.click(screen.getByRole('button', { name: 'load more' }))
    expect(fetchNextPage).not.toHaveBeenCalled()
  })
})
