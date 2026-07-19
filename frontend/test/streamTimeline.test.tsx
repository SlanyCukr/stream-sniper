import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { StreamTimeline as StreamTimelineData } from '@/hooks/stream/timeline/useStreamTimelineQuery'

const { mutate, reviewMutation } = vi.hoisted(() => {
  const mutate = vi.fn()
  return {
    mutate,
    reviewMutation: {
      mutate,
      isPending: false,
      isError: false,
      error: null,
    },
  }
})

vi.mock('@/contexts/AuthContext', () => ({
  useAuth: () => ({ isAdmin: true }),
}))

vi.mock('@/hooks/moments/useMomentsQueries', () => ({
  useMomentReview: () => reviewMutation,
}))

import StreamTimeline from '@/components/stream/timeline/StreamTimeline'

const timeline: Pick<
  StreamTimelineData,
  'streamId' | 'twitchVodId' | 'streamStart' | 'buckets' | 'moments' | 'viewerSamples' | 'contextChanges'
> = {
  streamId: 42,
  twitchVodId: '9876',
  streamStart: '2026-07-14T10:00:00Z',
  buckets: [
    { t: '2026-07-14T10:00:00Z', count: 2, unique: 2, subMessages: 0, emoteMessages: 0 },
    { t: '2026-07-14T10:01:00Z', count: 14, unique: 8, subMessages: 0, emoteMessages: 0 },
  ],
  moments: [{
    t: '2026-07-14T10:01:00Z',
    offsetSeconds: 60,
    count: 14,
    score: 4.2,
    kind: 'spike',
    isPersisted: true,
    status: null,
    subShare: null,
    emoteShare: null,
    topPhrases: [{ phrase: 'what happened', count: 3 }],
    sampleMessages: [{ text: 'that was wild', count: 2 }],
  }],
  viewerSamples: [
    { t: '2026-07-14T10:00:00Z', viewerCount: 100 },
    { t: '2026-07-14T10:01:00Z', viewerCount: 150 },
  ],
  contextChanges: [{
    t: '2026-07-14T10:00:30Z',
    categoryId: null,
    categoryName: 'Just Chatting',
    title: 'Morning stream',
    language: null,
    tags: [],
    isMature: null,
  }],
}

describe('StreamTimeline', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('coordinates spike selection, replay jumps, context, and admin review commands', () => {
    const onJump = vi.fn()
    render(<StreamTimeline timeline={timeline} onJump={onJump} />)

    expect(screen.getByText('Just Chatting')).toBeInTheDocument()
    expect(screen.getByText('Morning stream')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Spike at 10:01/ }))

    expect(onJump).toHaveBeenCalledTimes(1)
    expect(onJump).toHaveBeenCalledWith('2026-07-14T10:01:00Z')
    expect(screen.getByText(/Jumped replay to 10:01/)).toBeInTheDocument()
    expect(screen.getByText('what happened')).toBeInTheDocument()
    expect(screen.getByText('that was wild')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Bookmark' }))

    expect(mutate).toHaveBeenCalledWith({
      action: 'set',
      streamId: 42,
      bucketMinute: '2026-07-14T10:01:00Z',
      status: 'bookmarked',
      clipUrl: null,
      note: null,
    })
  })
})
