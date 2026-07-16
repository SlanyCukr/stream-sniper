import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const mocks = vi.hoisted(() => ({
  useCreators: vi.fn(),
  useSceneCopypastas: vi.fn(),
  useSceneLive: vi.fn(),
  useSceneLeaderboard: vi.fn(),
  useCreatorSummary: vi.fn(),
  useCreatorEmotes: vi.fn(),
  useCreatorNeighbors: vi.fn(),
  useMomentsQueue: vi.fn(),
  useMomentReview: vi.fn(),
  mutateAsync: vi.fn(),
}))

vi.mock('@/hooks/creator/useCreatorsQuery', () => ({
  useCreators: mocks.useCreators,
  mapCreatorOption: (creator: { creatorId: number; nick: string }) => ({
    value: creator.creatorId,
    label: creator.nick,
  }),
}))
vi.mock('@/hooks/scene/useSceneCopypastaQueries', () => ({
  useSceneCopypastas: mocks.useSceneCopypastas,
}))
vi.mock('@/hooks/scene/useSceneLiveQueries', () => ({
  useSceneLive: mocks.useSceneLive,
  useSceneLeaderboard: mocks.useSceneLeaderboard,
}))
vi.mock('@/hooks/creator/useCreatorSummaryQuery', () => ({ useCreatorSummary: mocks.useCreatorSummary }))
vi.mock('@/hooks/stream/insights/useStreamInsightsQuery', () => ({ useCreatorEmotes: mocks.useCreatorEmotes }))
vi.mock('@/hooks/community/useCommunityQuery', () => ({ useCreatorNeighbors: mocks.useCreatorNeighbors }))
vi.mock('@/hooks/moments/useMomentsQueries', () => ({
  useMomentsQueue: mocks.useMomentsQueue,
  useMomentReview: mocks.useMomentReview,
}))
vi.mock('@/contexts/AuthContext', () => ({ useAuth: () => ({ isAdmin: true }) }))
vi.mock('@/components/creator/TrendsPanel', () => ({ default: () => <div>Trajectory panel</div> }))
vi.mock('@/components/creator/RegularsPanel', () => ({ default: () => <div>Regulars panel</div> }))

import Copypasta from '@/views/scene/Copypasta'
import CreatorDossier from '@/views/creator/CreatorDossier'
import LiveNow from '@/views/scene/LiveNow'
import Moments from '@/views/moments/Moments'
import Scene from '@/views/scene/Scene'

const ready = (data: unknown) => ({
  data,
  isLoading: false,
  isPlaceholderData: false,
  error: null,
  refetch: vi.fn(),
})

describe('scene product surfaces', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mocks.useCreators.mockReturnValue(ready([{ creatorId: 1, nick: 'alpha' }]))
    mocks.mutateAsync.mockResolvedValue({ status: 'bookmarked' })
    mocks.useMomentReview.mockReturnValue({ mutateAsync: mocks.mutateAsync, isPending: false, variables: null })
  })

  it('renders copypasta usage/spread metadata and trace links', () => {
    mocks.useSceneCopypastas.mockReturnValue(ready({
      items: [{
        messageTextId: 5,
        text: 'copy this',
        usageCount: 20,
        streamCount: 4,
        creatorCount: 2,
        firstSeen: '2026-01-02T00:00:00',
      }],
      pageCount: 1,
    }))
    render(<Copypasta />)

    expect(screen.getByText('copy this')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Trace spread/ })).toHaveAttribute('href', '/copypasta/5')
    expect(screen.getByText(/first seen 2026-01-02/)).toBeInTheDocument()
  })

  it('composes creator identity, lifetime statistics, and related intelligence', () => {
    mocks.useCreatorSummary.mockReturnValue(ready({
      creatorId: 1,
      nick: 'alpha',
      displayName: 'Alpha',
      profileImageUrl: null,
      totalStreams: 12,
      totalMessages: 5000,
      durationSeconds: 7200,
      messagesPerMinute: 20,
      audienceSize: 300,
      regulars: 40,
      lastStreamAt: null,
      latestStream: { streamId: 99 },
    }))
    mocks.useCreatorEmotes.mockReturnValue(ready({ emotes: [{ source: 'twitch', name: 'Kappa', usageCount: 25 }] }))
    mocks.useCreatorNeighbors.mockReturnValue(ready({ neighbors: [{ creatorId: 2, nick: 'beta', sharedRegulars: 8 }] }))
    mocks.useSceneCopypastas.mockReturnValue(ready({ items: [{ messageTextId: 5, text: 'copy', usageCount: 10 }] }))
    render(<CreatorDossier creatorId={1} />)

    expect(screen.getByRole('heading', { name: 'Alpha' })).toBeInTheDocument()
    expect(screen.getByRole('list', { name: 'Creator lifetime statistics' })).toHaveTextContent('5K')
    expect(screen.getByRole('link', { name: 'Latest stream' })).toHaveAttribute('href', '/stream/99')
    expect(screen.getByText('Kappa')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'beta' })).toHaveAttribute('href', '/creator/2')
  })

  it('distinguishes a live scene from stale tracker data', () => {
    vi.spyOn(Date, 'now').mockReturnValue(new Date('2026-01-01T12:30:00Z').getTime())
    mocks.useSceneLive.mockReturnValue(ready({
      live: [{
        creatorId: 1,
        nick: 'alpha',
        displayName: 'Alpha',
        profileImageUrl: null,
        viewerCount: 1234,
        title: 'Launch',
        sessionStartedAt: '2026-01-01T11:00:00',
      }],
      lastSampleAt: '2026-01-01T12:00:00',
    }))
    render(<LiveNow />)

    expect(screen.getByRole('link', { name: 'Alpha' })).toHaveAttribute('href', '/creator/1')
    expect(screen.getByText('1h 30m')).toBeInTheDocument()
    expect(screen.getByText(/Latest sample is over 15 minutes old/)).toBeInTheDocument()
  })

  it('changes highlight status filters and translates review actions to commands', () => {
    const moment = {
      streamId: 42,
      streamTitle: 'Launch',
      streamStart: '2026-01-01T12:00:00',
      twitchVodId: null,
      creatorName: 'Alpha',
      t: '2026-01-01T12:15:00',
      count: 20,
      baseline: 5,
      score: 4,
      unique: null,
      subShare: null,
      emoteShare: null,
      topPhrases: [],
      sampleMessages: [],
      status: 'pending',
      clipUrl: null,
      note: null,
    }
    mocks.useMomentsQueue.mockReturnValue(ready({ items: [moment], pageCount: 1 }))
    render(<Moments />)

    fireEvent.click(screen.getByRole('button', { name: /Bookmark/ }))
    expect(mocks.mutateAsync).toHaveBeenCalledWith(expect.objectContaining({
      action: 'set',
      streamId: 42,
      status: 'bookmarked',
    }))
    fireEvent.click(screen.getByRole('tab', { name: 'Rejected' }))
    expect(mocks.useMomentsQueue).toHaveBeenLastCalledWith(
      expect.objectContaining({ status: 'rejected', pageIndex: 0 }),
      expect.any(Object),
    )
  })

  it('keeps a failed highlight review visible on the affected card', async () => {
    mocks.mutateAsync.mockRejectedValue({
      response: { status: 503, data: { detail: 'review storage offline' } },
      message: 'request failed',
    })
    mocks.useMomentsQueue.mockReturnValue(ready({
      items: [{
        streamId: 42,
        streamTitle: 'Launch',
        streamStart: '2026-01-01T12:00:00',
        twitchVodId: null,
        creatorName: 'Alpha',
        t: '2026-01-01T12:15:00',
        count: 20,
        baseline: 5,
        score: 4,
        unique: null,
        subShare: null,
        emoteShare: null,
        topPhrases: [],
        sampleMessages: [],
        status: 'pending',
        clipUrl: null,
        note: null,
      }],
      pageCount: 1,
    }))
    render(<Moments />)

    fireEvent.click(screen.getByRole('button', { name: /Bookmark/ }))
    expect(await screen.findByText('review storage offline')).toBeInTheDocument()
    expect(screen.getByText('Unable to update highlight')).toBeInTheDocument()
  })

  it('switches leaderboard windows and preserves unknown numeric cells', () => {
    mocks.useSceneLeaderboard.mockReturnValue(ready({
      entries: [{
        rank: 1,
        creatorId: 1,
        nick: 'alpha',
        displayName: 'Alpha',
        profileImageUrl: null,
        streams: 3,
        hoursStreamed: null,
        totalMessages: 500,
        msgsPerMin: null,
        chatterAppearances: 80,
        peakViewers: null,
      }],
    }))
    render(<Scene />)

    expect(screen.getByRole('region', { name: 'Scene leaderboard' })).toHaveTextContent('--')
    fireEvent.click(screen.getByRole('tab', { name: '30 days' }))
    expect(mocks.useSceneLeaderboard).toHaveBeenLastCalledWith({ windowDays: 30 })
  })
})
