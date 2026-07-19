import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { UseQueryResult } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const streamApi = vi.hoisted(() => ({
  retrieveStreamEmotes: vi.fn(),
  retrieveStreamMentions: vi.fn(),
  retrieveStreamPhrases: vi.fn(),
  retrieveStreamReport: vi.fn(),
  retrieveStreamTimeline: vi.fn(),
}))

const creatorApi = vi.hoisted(() => ({
  retrieveCreatorEmotes: vi.fn(),
}))

vi.mock('@/lib/api/streams', () => streamApi)
vi.mock('@/lib/api/creators', () => creatorApi)

import {
  useCreatorEmotes,
  useStreamEmotes,
  useStreamMentions,
  useStreamPhrases,
} from '@/hooks/stream/insights/useStreamInsightsQuery'
import { mapReportMetric, useStreamReport } from '@/hooks/stream/report/useStreamReportQuery'
import type { StreamReport } from '@/hooks/stream/report/useStreamReportQuery'
import { useStreamTimeline } from '@/hooks/stream/timeline/useStreamTimelineQuery'
import type { StreamTimeline } from '@/hooks/stream/timeline/useStreamTimelineQuery'

const createClient = () => new QueryClient({
  defaultOptions: { queries: { retry: false } },
})

function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: PropsWithChildren) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

describe('stream analytics query contracts', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('maps report metrics as a pure fail-closed boundary', () => {
    expect(mapReportMetric({
      value: null,
      delta_pct: 12.5,
      percentile: null,
      baseline_median: 4,
    }, 'metric')).toEqual({
      value: null,
      deltaPct: 12.5,
      percentile: null,
      baselineMedian: 4,
    })
    expect(() => mapReportMetric({}, 'metric')).toThrow(TypeError)
  })

  it('maps the complete timeline payload while preserving nullable rollup fields', async () => {
    streamApi.retrieveStreamTimeline.mockResolvedValue({
      data: {
        stream_id: 42,
        stream_start: '2026-07-14T10:00:00Z',
        twitch_id: 'vod-42',
        bucket_seconds: 60,
        buckets: [{
          bucket_minute: '2026-07-14T10:01:00Z',
          message_count: 12,
          unique_chatters: 7,
          sub_messages: null,
          emote_messages: 3,
        }],
        moments: [{
          bucket_minute: '2026-07-14T10:01:00Z',
          offset_seconds: 60,
          message_count: 12,
          ratio: null,
          persisted: false,
          status: null,
          sub_share: null,
          emote_share: 0.25,
          top_phrases: null,
          sample_messages: [{ text: 'wow' }],
        }],
        metrics: {
          unique_chatters: 7,
          messages_per_minute: null,
          peak_bucket_minute: '2026-07-14T10:01:00Z',
          new_chatters: 2,
          returning_chatters: 5,
          total_messages: 12,
          duration_seconds: null,
          peak_messages: 12,
          sub_messages: null,
          emote_messages: 3,
        },
        viewer_samples: [{ t: '2026-07-14T10:01:00Z', viewer_count: 99 }],
        context_changes: [{
          t: '2026-07-14T10:01:00Z',
          title: 'New title',
          category_id: null,
          category_name: null,
          language: 'en',
          tags: null,
          is_mature: false,
        }],
        peak_viewers: null,
      },
    })

    const result = renderHook(() => (
      useStreamTimeline(42) as UseQueryResult<StreamTimeline, Error>
    ), {
      wrapper: createWrapper(createClient()),
    })

    await waitFor(() => expect(result.result.current.isSuccess).toBe(true))
    expect(streamApi.retrieveStreamTimeline).toHaveBeenCalledWith(42)
    expect(result.result.current.data).toEqual({
      streamId: 42,
      streamStart: '2026-07-14T10:00:00Z',
      twitchVodId: 'vod-42',
      bucketSeconds: 60,
      buckets: [{
        t: '2026-07-14T10:01:00Z',
        count: 12,
        unique: 7,
        subMessages: null,
        emoteMessages: 3,
      }],
      moments: [{
        t: '2026-07-14T10:01:00Z',
        offsetSeconds: 60,
        count: 12,
        score: null,
        kind: 'spike',
        isPersisted: false,
        status: null,
        subShare: null,
        emoteShare: 0.25,
        topPhrases: null,
        sampleMessages: [{ text: 'wow' }],
      }],
      metrics: {
        uniqueChatters: 7,
        msgsPerMin: null,
        peakMsgsPerMin: null,
        peakAt: '2026-07-14T10:01:00Z',
        newChatters: 2,
        returningChatters: 5,
        totalMessages: 12,
        durationSec: null,
        peakMessages: 12,
        subMessages: null,
        emoteMessages: 3,
        peakViewers: null,
      },
      viewerSamples: [{ t: '2026-07-14T10:01:00Z', viewerCount: 99 }],
      contextChanges: [{
        t: '2026-07-14T10:01:00Z',
        title: 'New title',
        categoryId: null,
        categoryName: null,
        language: 'en',
        tags: [],
        isMature: false,
      }],
      peakViewers: null,
    })
  })

  it('maps report metrics and optional highlights without converting unknowns to zero', async () => {
    const metric = {
      value: null,
      delta_pct: null,
      percentile: null,
      baseline_median: null,
    }
    streamApi.retrieveStreamReport.mockResolvedValue({
      data: {
        stream_id: 42,
        creator_id: 7,
        creator_nick: null,
        title: 'Report stream',
        start: null,
        end: null,
        duration_seconds: null,
        baseline_count: 0,
        lookback: 10,
        metrics: {
          messages_per_minute: metric,
          total_messages: metric,
          unique_chatters: metric,
          new_chatters: metric,
          returning_chatters: metric,
          sub_share: metric,
          peak_messages: metric,
          avg_viewers: metric,
          peak_viewers: metric,
        },
        peak_bucket_minute: null,
        top_emote: {
          name: 'OMEGALUL',
          source: 'bttv',
          provider_id: null,
          usage_count: 8,
          chatter_count: 4,
        },
        top_phrase: null,
        top_moments: [{
          bucket_minute: '2026-07-14T10:01:00Z',
          offset_seconds: null,
          message_count: 12,
          ratio: null,
          status: null,
        }],
      },
    })

    const result = renderHook(() => (
      useStreamReport(42) as UseQueryResult<StreamReport, Error>
    ), {
      wrapper: createWrapper(createClient()),
    })

    await waitFor(() => expect(result.result.current.isSuccess).toBe(true))
    expect(streamApi.retrieveStreamReport).toHaveBeenCalledWith(42)
    expect(result.result.current.data).toMatchObject({
      streamId: 42,
      creatorId: 7,
      creatorNick: null,
      durationSeconds: null,
      baselineCount: 0,
      metrics: {
        messagesPerMinute: {
          value: null,
          deltaPct: null,
          percentile: null,
          baselineMedian: null,
        },
      },
      topEmote: {
        name: 'OMEGALUL',
        providerId: null,
        usageCount: 8,
        chatterCount: 4,
      },
      topPhrase: null,
      topMoments: [{
        bucketMinute: '2026-07-14T10:01:00Z',
        offsetSeconds: null,
        ratio: null,
        status: null,
      }],
    })
  })

  it('maps every insights payload through the production hooks', async () => {
    streamApi.retrieveStreamMentions.mockResolvedValue({
      data: {
        mentioned: [{ chatter_id: 11, nick: 'viewer', count: 5 }],
        pairs: [{
          from_chatter_id: 11,
          from_nick: 'viewer',
          to_chatter_id: 12,
          to_nick: 'friend',
          count: 3,
        }],
      },
    })
    streamApi.retrieveStreamEmotes.mockResolvedValue({
      data: { emotes: [{
        name: 'OMEGALUL', source: 'bttv', provider_id: null,
        usage_count: 8, chatter_count: 4, stream_count: 2,
      }] },
    })
    streamApi.retrieveStreamPhrases.mockResolvedValue({
      data: { phrases: [{ phrase: 'lets go', usage_count: 6, chatter_count: 3 }] },
    })
    creatorApi.retrieveCreatorEmotes.mockResolvedValue({
      data: { emotes: [{
        name: 'CreatorLove', source: 'twitch', provider_id: 'emote-1',
        usage_count: 10, chatter_count: 5, stream_count: 4,
      }] },
    })
    const wrapper = createWrapper(createClient())
    const mentions = renderHook(() => useStreamMentions(42, { limit: 10 }), { wrapper })
    const emotes = renderHook(() => useStreamEmotes(42, { limit: 11 }), { wrapper })
    const phrases = renderHook(() => useStreamPhrases(42, { limit: 12 }), { wrapper })
    const creatorEmotes = renderHook(() => useCreatorEmotes(7, { limit: 13 }), { wrapper })

    await waitFor(() => {
      expect(mentions.result.current.isSuccess).toBe(true)
      expect(emotes.result.current.isSuccess).toBe(true)
      expect(phrases.result.current.isSuccess).toBe(true)
      expect(creatorEmotes.result.current.isSuccess).toBe(true)
    })
    expect(streamApi.retrieveStreamMentions).toHaveBeenCalledWith(42, 10)
    expect(streamApi.retrieveStreamEmotes).toHaveBeenCalledWith(42, 11)
    expect(streamApi.retrieveStreamPhrases).toHaveBeenCalledWith(42, 12)
    expect(creatorApi.retrieveCreatorEmotes).toHaveBeenCalledWith(7, 13)
    expect(mentions.result.current.data).toEqual({
      mentioned: [{ chatterId: 11, nick: 'viewer', count: 5 }],
      pairs: [{
        fromChatterId: 11,
        fromNick: 'viewer',
        toChatterId: 12,
        toNick: 'friend',
        count: 3,
      }],
    })
    expect(emotes.result.current.data?.emotes[0]).toMatchObject({
      providerId: null,
      usageCount: 8,
      streamCount: 2,
    })
    expect(phrases.result.current.data).toEqual({
      phrases: [{ phrase: 'lets go', usageCount: 6, chatterCount: 3 }],
    })
    expect(creatorEmotes.result.current.data?.emotes[0]).toMatchObject({
      providerId: 'emote-1',
      streamCount: 4,
    })
  })

  it('rejects missing required analytics payloads and never requests disabled queries', async () => {
    streamApi.retrieveStreamTimeline.mockResolvedValue({ data: {} })
    streamApi.retrieveStreamReport.mockResolvedValue({ data: {} })
    streamApi.retrieveStreamMentions.mockResolvedValue({ data: {} })
    streamApi.retrieveStreamEmotes.mockResolvedValue({ data: {} })
    streamApi.retrieveStreamPhrases.mockResolvedValue({ data: {} })
    creatorApi.retrieveCreatorEmotes.mockResolvedValue({ data: {} })
    const wrapper = createWrapper(createClient())
    const timeline = renderHook(() => (
      useStreamTimeline(42) as UseQueryResult<StreamTimeline, Error>
    ), { wrapper })
    const report = renderHook(() => (
      useStreamReport(42) as UseQueryResult<StreamReport, Error>
    ), { wrapper })
    const mentions = renderHook(() => useStreamMentions(42), { wrapper })
    const emotes = renderHook(() => useStreamEmotes(42), { wrapper })
    const phrases = renderHook(() => useStreamPhrases(42), { wrapper })
    const creatorEmotes = renderHook(() => useCreatorEmotes(7), { wrapper })

    await waitFor(() => {
      expect(timeline.result.current.isError).toBe(true)
      expect(report.result.current.isError).toBe(true)
      expect(mentions.result.current.isError).toBe(true)
      expect(emotes.result.current.isError).toBe(true)
      expect(phrases.result.current.isError).toBe(true)
      expect(creatorEmotes.result.current.isError).toBe(true)
    })
    expect(timeline.result.current.error).toBeInstanceOf(TypeError)
    expect(report.result.current.error).toBeInstanceOf(TypeError)
    expect(mentions.result.current.error).toBeInstanceOf(TypeError)
    expect(emotes.result.current.error).toBeInstanceOf(TypeError)
    expect(phrases.result.current.error).toBeInstanceOf(TypeError)
    expect(creatorEmotes.result.current.error).toBeInstanceOf(TypeError)

    vi.clearAllMocks()
    const disabledWrapper = createWrapper(createClient())
    renderHook(() => useStreamTimeline(0), { wrapper: disabledWrapper })
    renderHook(() => useStreamReport(0), { wrapper: disabledWrapper })
    renderHook(() => useStreamMentions(0), { wrapper: disabledWrapper })
    renderHook(() => useStreamEmotes(0), { wrapper: disabledWrapper })
    renderHook(() => useStreamPhrases(0), { wrapper: disabledWrapper })
    renderHook(() => useCreatorEmotes(0), { wrapper: disabledWrapper })
    renderHook(() => useStreamTimeline(42, { enabled: false }), { wrapper: disabledWrapper })
    renderHook(() => useStreamReport(42, { enabled: false }), { wrapper: disabledWrapper })
    renderHook(() => useStreamMentions(42, { limit: 20 }, { enabled: false }), { wrapper: disabledWrapper })
    renderHook(() => useStreamEmotes(42, { limit: 25 }, { enabled: false }), { wrapper: disabledWrapper })
    renderHook(() => useStreamPhrases(42, { limit: 25 }, { enabled: false }), { wrapper: disabledWrapper })
    renderHook(() => useCreatorEmotes(7, { limit: 25 }, { enabled: false }), { wrapper: disabledWrapper })

    await new Promise(resolve => setTimeout(resolve, 0))
    expect(streamApi.retrieveStreamTimeline).not.toHaveBeenCalled()
    expect(streamApi.retrieveStreamReport).not.toHaveBeenCalled()
    expect(streamApi.retrieveStreamMentions).not.toHaveBeenCalled()
    expect(streamApi.retrieveStreamEmotes).not.toHaveBeenCalled()
    expect(streamApi.retrieveStreamPhrases).not.toHaveBeenCalled()
    expect(creatorApi.retrieveCreatorEmotes).not.toHaveBeenCalled()
  })
})
