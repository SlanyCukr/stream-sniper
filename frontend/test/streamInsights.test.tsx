import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  useStreamEmotes: vi.fn(),
  useStreamMentions: vi.fn(),
  useStreamReport: vi.fn(),
  downloadStreamExport: vi.fn(),
  downloadStreamInsightCsv: vi.fn(),
  isAuthenticated: true,
}))

vi.mock('@/hooks/stream/insights/useStreamInsightsQuery', () => ({
  useStreamEmotes: mocks.useStreamEmotes,
  useStreamMentions: mocks.useStreamMentions,
}))
vi.mock('@/hooks/stream/report/useStreamReportQuery', () => ({ useStreamReport: mocks.useStreamReport }))
vi.mock('@/lib/api/streams', () => ({
  downloadStreamExport: mocks.downloadStreamExport,
  downloadStreamInsightCsv: mocks.downloadStreamInsightCsv,
}))
vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ isAuthenticated: mocks.isAuthenticated }),
}))
vi.mock('@/components/stream/replay/StreamChatReplay', () => ({
  default: ({ messages }: { messages: unknown[] }) => <div>Replay rows: {messages.length}</div>,
}))

import EmotesPanel from '@/components/stream/insights/EmotesPanel'
import MentionsPanel from '@/components/stream/insights/MentionsPanel'
import StreamDownloadMenu from '@/components/stream/StreamDownloadMenu'
import StreamMetrics from '@/components/stream/report/StreamMetrics'
import StreamReplayCard from '@/components/stream/replay/StreamReplayCard'
import StreamReportCard from '@/components/stream/report/StreamReportCard'
import StreamStatsCard from '@/components/stream/report/StreamStatsCard'

const readyQuery = (data: unknown) => ({
  data,
  isLoading: false,
  error: null,
  refetch: vi.fn(),
})

describe('stream insight panels', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.isAuthenticated = true
  })

  it('renders safe emote images and falls back for untrusted provider ids', () => {
    mocks.useStreamEmotes.mockReturnValue(readyQuery({
      emotes: [
        { source: 'bttv', providerId: 'abc_123', name: 'OMEGALUL', usageCount: 20, chatterCount: 5 },
        { source: 'twitch', providerId: '../bad', name: 'Nope', usageCount: 2, chatterCount: 1 },
      ],
    }))
    render(<EmotesPanel streamId={9} />)

    expect(screen.getByRole('img', { name: 'OMEGALUL' })).toHaveAttribute(
      'src',
      'https://cdn.betterttv.net/emote/abc_123/1x',
    )
    expect(screen.queryByRole('img', { name: 'Nope' })).not.toBeInTheDocument()
    expect(screen.getByLabelText('Nope: 2 uses, 1 chatters')).toBeInTheDocument()
  })

  it('renders mention ranks and directional exchanges', () => {
    mocks.useStreamMentions.mockReturnValue(readyQuery({
      mentioned: [{ chatterId: 1, nick: 'alice', count: 12 }],
      pairs: [{ fromChatterId: 1, toChatterId: 2, fromNick: 'alice', toNick: 'bob', count: 4 }],
    }))
    render(<MentionsPanel streamId={9} />)

    expect(screen.getByLabelText('Rank 1: alice, mentioned 12 times')).toBeInTheDocument()
    expect(screen.getByLabelText('Top mention exchanges')).toHaveTextContent('alice → bob')
  })

  it('preserves unknown metrics and renders computed shares without fake zeroes', () => {
    const { rerender } = render(<StreamMetrics metrics={null} />)
    expect(screen.getByText('Metrics not yet computed for this stream.')).toBeInTheDocument()

    rerender(<StreamMetrics metrics={{
      totalMessages: 100,
      msgsPerMin: 12.5,
      uniqueChatters: 25,
      peakMessages: 20,
      peakAt: '2026-01-01T12:34:00',
      newChatters: 5,
      returningChatters: 20,
      durationSec: 5400,
      peakViewers: null,
      subMessages: 20,
      emoteMessages: 40,
    }} />)

    expect(screen.getByText('20.0%')).toBeInTheDocument()
    expect(screen.getByText('40.0%')).toBeInTheDocument()
    expect(screen.queryByText('Peak viewers')).not.toBeInTheDocument()
    expect(screen.getByText('1h 30m')).toBeInTheDocument()
  })

  it('shows report deltas, baseline context, and highlights', () => {
    mocks.useStreamReport.mockReturnValue(readyQuery({
      metrics: {
        totalMessages: { value: 1200, deltaPct: 20, percentile: 90, baselineMedian: 1000 },
      },
      baselineCount: 4,
      topEmote: { name: 'Kappa', usageCount: 40 },
      topPhrase: null,
      topMoments: [],
    }))
    render(<StreamReportCard streamId={9} />)

    expect(screen.getByLabelText('+20.0% vs baseline median')).toBeInTheDocument()
    expect(screen.getByText(/P90.0/)).toBeInTheDocument()
    expect(screen.getByText('Kappa')).toBeInTheDocument()
    expect(screen.getByText('vs previous 4 streams')).toBeInTheDocument()
  })

  it('does not format an unknown report baseline as zero', () => {
    mocks.useStreamReport.mockReturnValue(readyQuery({
      metrics: {
        totalMessages: { value: 1200, deltaPct: null, percentile: 90, baselineMedian: null },
      },
      baselineCount: 0,
      topEmote: null,
      topPhrase: null,
      topMoments: [],
    }))
    render(<StreamReportCard streamId={9} />)

    expect(screen.getByText('P90.0')).toBeInTheDocument()
    expect(screen.queryByText(/vs median/)).not.toBeInTheDocument()
  })

  it('owns the other-creators section as stream statistics data', () => {
    const { rerender } = render(
      <StreamStatsCard
        mostActiveChatters={[]}
        mostTaggedChatters={[]}
        otherCreators={[{ creatorId: 7, nick: 'guest' }]}
      />,
    )

    expect(screen.getByRole('list', {
      name: 'Other creators who participated in this stream',
    })).toHaveTextContent('guest')

    rerender(
      <StreamStatsCard
        mostActiveChatters={[]}
        mostTaggedChatters={[]}
        otherCreators={[]}
      />,
    )
    expect(screen.queryByText('Other creators in chat')).not.toBeInTheDocument()
  })
})

describe('stream actions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.isAuthenticated = true
  })

  it('exposes authenticated exports and surfaces normalized download failures', async () => {
    mocks.downloadStreamInsightCsv.mockRejectedValue({ response: { status: 502, data: { detail: 'network down' } } })
    render(<StreamDownloadMenu streamId={42} title="Launch" />)

    fireEvent.click(screen.getByRole('button', { name: 'Export data for Launch' }))
    expect(screen.getByRole('menuitem', { name: /Chat log \(NDJSON\)/ })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('menuitem', { name: /Emotes CSV/ }))

    await waitFor(() => expect(mocks.downloadStreamInsightCsv).toHaveBeenCalledWith(42, 'emotes'))
    expect(await screen.findByText('network down')).toBeInTheDocument()
  })

  it('propagates replay filters while rendering the owned message state', () => {
    const onChatterChange = vi.fn()
    const onQueryChange = vi.fn()
    const onSubOnlyChange = vi.fn()
    render(
      <StreamReplayCard
        chatterOptions={[]}
        replay={{
          filterCommands: { onChatterChange, onQueryChange, onSubOnlyChange },
          messagePage: {
            messages: [{
              id: 1,
              ts: '2026-01-01T00:00:00',
              chatterId: 2,
              nick: 'alice',
              text: 'hello',
              isSubscriber: false,
              badges: null,
            }],
            hasMore: false,
            isFetchingMore: false,
            onLoadMore: vi.fn(),
          },
          queryState: { isLoading: false, error: null },
          navigation: { jumpToTs: null },
        }}
      />,
    )

    fireEvent.click(screen.getByRole('switch', { name: 'Subscribers only' }))
    expect(onSubOnlyChange).toHaveBeenCalledWith(true)
    expect(screen.getByText('Replay rows: 1')).toBeInTheDocument()
  })
})
