import { QueryClientProvider } from '@tanstack/react-query'
import { renderHook, screen, waitFor } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  retrieveAudienceMovement: vi.fn(),
  retrieveCreatorRegulars: vi.fn(),
  retrieveCreatorSummary: vi.fn(),
  retrieveCreatorTrends: vi.fn(),
  retrieveCreatorWrapped: vi.fn(),
}))

vi.mock('@/lib/api/creators', () => api)

import TrendsPanel from '@/components/creator/TrendsPanel'
import {
  audienceMovementKeys, useAudienceMovement,
} from '@/hooks/creator/useAudienceMovementQuery'
import {
  creatorRegularsKeys, useCreatorRegulars,
} from '@/hooks/creator/useCreatorRegularsQuery'
import {
  creatorSummaryKeys, useCreatorSummary,
} from '@/hooks/creator/useCreatorSummaryQuery'
import {
  creatorTrendsKeys, useCreatorTrends,
} from '@/hooks/creator/useCreatorTrendsQuery'
import {
  creatorWrappedKeys, useCreatorWrapped,
} from '@/hooks/creator/useCreatorWrappedQuery'
import { createTestQueryClient, renderWithQueryClient } from './render'

const createWrapper = () => {
  const client = createTestQueryClient()
  return function Wrapper({ children }: PropsWithChildren) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>
  }
}

describe('creator query contracts', () => {
  beforeEach(() => vi.clearAllMocks())

  it('keeps IDs and filters in keys and suppresses every invalid resource request', async () => {
    expect(audienceMovementKeys.detail(7, 14)).toEqual(['audience-movement', { creatorId: 7, days: 14 }])
    expect(creatorSummaryKeys.detail(7)).toEqual(['creator-summary', { creatorId: 7 }])
    expect(creatorRegularsKeys.list(7, { minStreams: 3 })).toEqual([
      'creator-regulars', 'list', { creatorId: 7, minStreams: 3 },
    ])
    expect(creatorTrendsKeys.detail(7)).toEqual(['creator-trends', 'detail', 7])
    expect(creatorWrappedKeys.detail(7, 30)).toEqual(['creator-wrapped', { creatorId: 7, days: 30 }])

    const hooks = renderHook(() => ({
      movement: useAudienceMovement(0),
      summary: useCreatorSummary(0),
      regulars: useCreatorRegulars(0),
      trends: useCreatorTrends(0),
      wrapped: useCreatorWrapped(0, 30),
    }), { wrapper: createWrapper() })

    await waitFor(() => {
      const queries = Object.values(hooks.result.current) as Array<{ fetchStatus: string }>
      queries.forEach(query => expect(query.fetchStatus).toBe('idle'))
    })
    expect(api.retrieveAudienceMovement).not.toHaveBeenCalled()
    expect(api.retrieveCreatorSummary).not.toHaveBeenCalled()
    expect(api.retrieveCreatorRegulars).not.toHaveBeenCalled()
    expect(api.retrieveCreatorTrends).not.toHaveBeenCalled()
    expect(api.retrieveCreatorWrapped).not.toHaveBeenCalled()
  })

  it('maps audience movement associations and intentional nullable rates', async () => {
    api.retrieveAudienceMovement.mockResolvedValue({
      creator_id: 7,
      window_days: 14,
      current_audience: 100,
      previous_audience: 80,
      retained: 60,
      gained: 40,
      lapsed: 20,
      retention_rate: null,
      gain_rate: 0.5,
      prior_channels_for_gained: [{
        creator_id: 8, nick: 'beta', display_name: 'Beta', chatter_count: 12,
      }],
      current_channels_for_lapsed: [{
        creator_id: 9, nick: 'gamma', display_name: 'Gamma', chatter_count: 4,
      }],
    })
    const hook = renderHook(() => useAudienceMovement(7, { days: 14 }), { wrapper: createWrapper() })
    await waitFor(() => expect(hook.result.current.isSuccess).toBe(true))
    expect(api.retrieveAudienceMovement).toHaveBeenCalledWith(7, 14)
    expect(hook.result.current.data).toMatchObject({
      creatorId: 7,
      retentionRate: null,
      gainRate: 0.5,
      priorChannelsForGained: [{ creatorId: 8, displayName: 'Beta', chatterCount: 12 }],
      currentChannelsForLapsed: [{ creatorId: 9, displayName: 'Gamma', chatterCount: 4 }],
    })
  })

  it('maps complete creator summary and regular filters without losing nulls', async () => {
    api.retrieveCreatorSummary.mockResolvedValue({
      creator_id: 7,
      nick: 'alpha',
      display_name: 'Alpha',
      profile_image_url: null,
      twitch_id: null,
      total_streams: 4,
      first_stream_at: null,
      last_stream_at: '2026-07-14T10:00:00Z',
      total_messages: 500,
      duration_seconds: null,
      messages_per_minute: null,
      audience_size: 100,
      regulars: 20,
      latest_stream: { stream_id: 99, title: 'Launch', start: null },
    })
    api.retrieveCreatorRegulars.mockResolvedValue({
      regulars: [{
        chatter_id: 5,
        nick: 'viewer',
        streams_attended: 3,
        attendance_rate: 0.75,
        first_seen: '2026-07-01T00:00:00Z',
        last_seen: '2026-07-14T00:00:00Z',
        message_count: 45,
      }],
      total_streams: 4,
    })

    const summary = renderHook(() => useCreatorSummary(7), { wrapper: createWrapper() })
    const filters = { minStreams: 3, sort: 'messages', dir: 'desc' as const, limit: 10 }
    const regulars = renderHook(() => useCreatorRegulars(7, filters), { wrapper: createWrapper() })
    await waitFor(() => expect(summary.result.current.isSuccess).toBe(true))
    await waitFor(() => expect(
      (regulars.result.current as { isSuccess: boolean }).isSuccess,
    ).toBe(true))

    expect(summary.result.current.data).toMatchObject({
      creatorId: 7,
      profileImageUrl: null,
      durationSeconds: null,
      messagesPerMinute: null,
      latestStream: { streamId: 99, title: 'Launch', start: null },
    })
    expect(api.retrieveCreatorRegulars).toHaveBeenCalledWith(7, filters)
    expect((regulars.result.current as { data?: unknown }).data).toEqual({
      regulars: [{
        chatterId: 5,
        nick: 'viewer',
        streamsAttended: 3,
        attendanceRate: 0.75,
        firstSeen: '2026-07-01T00:00:00Z',
        lastSeen: '2026-07-14T00:00:00Z',
        messageCount: 45,
      }],
      totalStreams: 4,
    })
  })

  it('renders a creator trend surface through the real query mapper', async () => {
    api.retrieveCreatorTrends.mockResolvedValue({ points: [{
      stream_id: 10,
      title: 'Launch',
      start: '2026-07-14T10:00:00Z',
      duration_seconds: 5400,
      messages_per_minute: null,
      unique_chatters: 100,
      new_chatters: 30,
      returning_chatters: 70,
      message_count: 500,
    }] })

    renderWithQueryClient(<TrendsPanel creatorId={7} />)

    const surface = await screen.findByRole('group', { name: 'Creator per-stream trends' })
    expect(api.retrieveCreatorTrends).toHaveBeenCalledWith(7)
    expect(surface).toHaveTextContent('Messages / min0')
    expect(surface).toHaveTextContent('Duration1h 30m')
    expect(screen.getAllByRole('link', { name: /Launch/ })).toHaveLength(4)
  })

  it('maps creator wrapped totals and top lists without losing nulls', async () => {
    api.retrieveCreatorWrapped.mockResolvedValue({
      creator_id: 7,
      days: 30,
      totals: {
        streams: 3,
        hours_streamed: null,
        messages: 900,
        active_chatters: 42,
      },
      top_chatters: [{
        rank: 1, chatter_id: 5, nick: 'viewer', total_messages: 300, streams_attended: 2,
      }],
      top_moments: [{
        stream_id: 10,
        stream_title: 'Launch',
        twitch_id: null,
        bucket_minute: '2026-07-14T10:00:00',
        offset_seconds: 120,
        ratio: null,
        message_count: 80,
      }],
      top_copypastas: [{
        message_text_id: 2, text: 'copypasta', usage_count: 40, stream_count: 3,
      }],
      top_emotes: [{
        emote_id: 1, name: 'PogChamp', source: 'twitch', usage: 300, chatter_reach: 60,
      }],
    })

    const hook = renderHook(() => useCreatorWrapped(7, 30), { wrapper: createWrapper() })
    await waitFor(() => expect(hook.result.current.isSuccess).toBe(true))

    expect(api.retrieveCreatorWrapped).toHaveBeenCalledWith(7, 30)
    expect(hook.result.current.data).toEqual({
      creatorId: 7,
      days: 30,
      totals: {
        streams: 3,
        hoursStreamed: null,
        messages: 900,
        activeChatters: 42,
      },
      topChatters: [{
        rank: 1, chatterId: 5, nick: 'viewer', totalMessages: 300, streamsAttended: 2,
      }],
      topMoments: [{
        streamId: 10,
        streamTitle: 'Launch',
        twitchId: null,
        bucketMinute: '2026-07-14T10:00:00',
        offsetSeconds: 120,
        ratio: null,
        messageCount: 80,
      }],
      topCopypastas: [{
        messageTextId: 2, text: 'copypasta', usageCount: 40, streamCount: 3,
      }],
      topEmotes: [{
        emoteId: 1, name: 'PogChamp', source: 'twitch', usage: 300, chatterReach: 60,
      }],
    })
  })
})
