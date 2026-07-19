import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { UseMutateAsyncFunction } from '@tanstack/react-query'
import { act, renderHook, waitFor } from '@testing-library/react'
import type { PropsWithChildren } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const api = vi.hoisted(() => ({
  createTrackedStreamer: vi.fn(),
  deleteTrackedStreamer: vi.fn(),
  flushCache: vi.fn(),
  retrieveCacheStats: vi.fn(),
  retrieveDetailedHealth: vi.fn(),
  retrieveMetrics: vi.fn(),
  retrieveProcessingJobs: vi.fn(),
  retrieveTrackedStreamers: vi.fn(),
  retrieveTrackingStats: vi.fn(),
  retrieveTwitchChannelSearch: vi.fn(),
  retrieveAllCreators: vi.fn(),
  retrieveCreatorTrends: vi.fn(),
  createAdminUser: vi.fn(),
  deleteUser: vi.fn(),
  retrieveAdminSystemStats: vi.fn(),
  retrieveUsers: vi.fn(),
  setUserActive: vi.fn(),
  updateUser: vi.fn(),
  updateUserRole: vi.fn(),
  updateTrackedStreamer: vi.fn(),
}))

vi.mock('@/lib/api/tracking', () => ({
  createTrackedStreamer: api.createTrackedStreamer,
  deleteTrackedStreamer: api.deleteTrackedStreamer,
  retrieveProcessingJobs: api.retrieveProcessingJobs,
  retrieveTrackedStreamers: api.retrieveTrackedStreamers,
  retrieveTrackingStats: api.retrieveTrackingStats,
  retrieveTwitchChannelSearch: api.retrieveTwitchChannelSearch,
  updateTrackedStreamer: api.updateTrackedStreamer,
}))

vi.mock('@/lib/api/system', () => ({
  flushCache: api.flushCache,
  retrieveCacheStats: api.retrieveCacheStats,
  retrieveDetailedHealth: api.retrieveDetailedHealth,
  retrieveMetrics: api.retrieveMetrics,
}))

vi.mock('@/lib/api/users', () => ({
  createAdminUser: api.createAdminUser,
  deleteUser: api.deleteUser,
  retrieveAdminSystemStats: api.retrieveAdminSystemStats,
  retrieveUsers: api.retrieveUsers,
  setUserActive: api.setUserActive,
  updateUser: api.updateUser,
  updateUserRole: api.updateUserRole,
}))

vi.mock('@/lib/api/creators', () => ({
  retrieveAllCreators: api.retrieveAllCreators,
  retrieveCreatorTrends: api.retrieveCreatorTrends,
}))

import { mapChatterMessage } from '@/hooks/chatter/useMessagesQuery'
import { mapStreamDetails, mapStreamListRow } from '@/hooks/stream/list/useStreamsQuery'
import { buildStreamOptions } from '@/views/stream/StreamCompare'
import {
  mapCreatorOption,
  mapCreatorRow,
  useCreators,
} from '@/hooks/creator/useCreatorsQuery'
import { mapStreamMessagesPage } from '@/hooks/stream/replay/useStreamMessagesQuery'
import {
  mapProcessingJob,
  mapTrackedStreamer,
  mapTrackingStats,
  loadTrackedStreamerOptions,
  trackingKeys,
  useProcessingJobs,
  useTrackedStreamers,
  useTrackingStats,
  useUpdateTrackedStreamer,
} from '@/hooks/admin/tracking/useTrackingQueries'
import {
  mapCacheStats,
  mapDetailedHealth,
  mapSystemMetrics,
  systemKeys,
  useDetailedHealth,
  useFlushCache,
} from '@/hooks/admin/system/useSystemQueries'
import {
  mapAdminSystemStats,
  mapAdminUser,
  userAdminKeys,
  useAdminSystemStats,
  useAdminUsers,
  useUpdateAdminUser,
} from '@/hooks/admin/users/useUserAdminQueries'
import { useCreatorTrends } from '@/hooks/creator/useCreatorTrendsQuery'

function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: PropsWithChildren) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }
}

const createClient = () => new QueryClient({
  defaultOptions: { queries: { retry: false } },
})

type TrackingUpdateCommand = {
  streamerId: number
  changes: { is_active: boolean }
}

type UserUpdateCommand = {
  userId: number
  changes: { email: string }
}

describe('query view-model contracts', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('names positional stream rows and every comprehensive stream collection', () => {
    expect(mapStreamListRow({
      stream_id: 1,
      creator_name: 'Operator',
      start: 'start',
      end: 'end',
      thumbnail_url: 'thumb',
      message_count: 42,
    })).toEqual({
      streamId: 1,
      creatorName: 'Operator',
      start: 'start',
      end: 'end',
      thumbnailUrl: 'thumb',
      messageCount: 42,
    })
    expect(mapStreamDetails({
      info: {
        title: 'Title', start: 'start', end: 'end', thumbnail_url: 'thumb', message_count: 42,
        creator_nick: 'operator', creator_display_name: 'Operator', profile_image_url: 'profile', creator_id: 7,
      },
      most_active_chatters: [{ chatter_id: 11, nick: 'viewer', count: 9 }],
      most_tagged_chatters: [{ chatter_id: 12, nick: 'tagged', count: 4 }],
      other_creators: [{ creator_id: 8, nick: 'guest' }],
      chatters: [{ chatter_id: 11, nick: 'viewer' }],
    })).toMatchObject({
      info: { creatorId: 7, nick: 'operator', title: 'Title' },
      mostActiveChatters: [{ chatterId: 11, nick: 'viewer', count: 9 }],
      mostTaggedChatters: [{ chatterId: 12, nick: 'tagged', count: 4 }],
      otherCreators: [{ creatorId: 8, nick: 'guest' }],
      chatterOptions: [{ value: 11, label: 'viewer' }],
    })
    expect(mapCreatorRow({ creator_id: 7, display_name: 'operator' })).toEqual({ creatorId: 7, nick: 'operator' })
    expect(() => mapCreatorRow([7, 'operator'])).toThrow('creator must be an object')
    expect(mapChatterMessage({
      stream_id: 1,
      stream_title: 'Launch',
      creator_display_name: 'Operator',
      text: 'hello',
      timestamp: '2026-07-15T10:00:00Z',
    })).toEqual({
      streamId: 1,
      streamTitle: 'Launch',
      creatorDisplayName: 'Operator',
      text: 'hello',
      timestamp: '2026-07-15T10:00:00Z',
    })
    expect(() => mapChatterMessage([1, 'Launch', 'Operator', 'hello', 'now']))
      .toThrow('chatter message must be an object')
    expect(buildStreamOptions({
      items: [{
        streamId: 1,
        creatorName: 'Operator',
        start: 'start',
        end: null,
        thumbnailUrl: null,
        messageCount: 42,
      }],
    }, [2])).toEqual([
      { value: 1, label: 'Operator · start · #1' },
      { value: 2, label: 'Stream #2' },
    ])
    expect(mapCreatorOption({ creatorId: 7, nick: 'operator' })).toEqual({
      value: 7,
      label: 'operator',
    })
    expect(mapStreamMessagesPage({
      messages: [{
        id: 5,
        time: '2026-07-14T10:00:00Z',
        chatter_id: 11,
        nick: 'viewer',
        text: 'hello',
        is_subscriber: true,
        badges: ['subscriber'],
      }],
      next_cursor: { after_ts: 'next', after_id: 6 },
      has_more: true,
    })).toEqual({
      messages: [{
        id: 5,
        ts: '2026-07-14T10:00:00Z',
        chatterId: 11,
        nick: 'viewer',
        text: 'hello',
        isSubscriber: true,
        badges: ['subscriber'],
      }],
      nextCursor: { afterTs: 'next', afterId: 6 },
      hasMore: true,
    })
  })

  it('normalizes named creator catalog rows before consumers receive them', async () => {
    api.retrieveAllCreators.mockResolvedValue({
      data: [
        { creator_id: 7, display_name: 'operator' },
        { creator_id: 8, display_name: 'guest' },
      ],
    })
    const queryClient = createClient()
    const wrapper = createWrapper(queryClient)
    const creators = renderHook(() => useCreators(), { wrapper })

    await waitFor(() => expect(creators.result.current.isSuccess).toBe(true))
    expect(creators.result.current.data).toEqual([
      { creatorId: 7, nick: 'operator' },
      { creatorId: 8, nick: 'guest' },
    ])
  })

  it('maps tracking and telemetry responses before query consumers receive them', async () => {
    const rawStreamer = {
      id: 7,
      twitch_username: 'operator',
      display_name: 'Operator',
      is_active: true,
      processing_enabled: false,
      last_stream_check: null,
      created_at: 'created',
      total_streams_collected: 3,
      last_collected_stream_start: '2026-07-13T18:00:00',
    }
    const rawJob = {
      id: 9,
      twitch_username: 'operator',
      streamer_display_name: null,
      twitch_vod_id: 'stream-1',
      status: 'completed',
      created_at: 'created',
      started_at: null,
      completed_at: null,
      retry_count: 2,
    }
    api.retrieveTrackedStreamers.mockResolvedValue({
      data: { streamers: [rawStreamer], total: 1 },
    })
    api.retrieveDetailedHealth.mockResolvedValue({
      data: {
        status: 'healthy',
        timestamp: 'now',
        uptime_seconds: 60,
        system: { memory_usage_percent: 12.5 },
        components: { database: { status: 'healthy', response_time_ms: 3 } },
      },
    })
    const queryClient = createClient()
    const wrapper = createWrapper(queryClient)
    const streamers = renderHook(() => useTrackedStreamers(), { wrapper })
    const health = renderHook(() => useDetailedHealth(), { wrapper })

    await waitFor(() => expect(streamers.result.current.isSuccess).toBe(true))
    await waitFor(() => expect(health.result.current.isSuccess).toBe(true))

    expect(streamers.result.current.data?.items).toEqual([mapTrackedStreamer(rawStreamer)])
    expect(health.result.current.data).toEqual(mapDetailedHealth({
      status: 'healthy',
      timestamp: 'now',
      uptime_seconds: 60,
      system: { memory_usage_percent: 12.5 },
      components: { database: { status: 'healthy', response_time_ms: 3 } },
    }))
    expect(mapProcessingJob(rawJob)).toMatchObject({
      twitchUsername: 'operator',
      twitchVodId: 'stream-1',
      retryCount: 2,
    })
    expect(mapTrackingStats({
      system_status: {
        monitoring_active: true,
        monitoring_degraded: false,
        processing_queue_size: 2,
        failed_jobs: 1,
      },
      tracked_streamers: { total: 5, active: 4, processing_enabled: 3, inactive: 1 },
      processing_jobs: {
        total: 12,
        pending: 2,
        in_progress: 3,
        completed: 6,
        failed: 1,
        recent_24h: 4,
      },
    }))
      .toMatchObject({ processingJobs: { inProgress: 3, recent24h: 4 } })
    expect(mapSystemMetrics({
      requests: {
        total_requests: 5,
        successful_requests: 4,
        failed_requests: 1,
        average_response_time_ms: null,
      },
      cache: { hit_rate: 0.5, total_hits: 2, total_misses: 2, total_operations: 4 },
      rate_limiting: { total_requests: 5, rate_limited_requests: 1, rate_limit_percentage: 20 },
    }))
      .toMatchObject({ requests: { totalRequests: 5 } })
    expect(mapCacheStats({ cache_stats: { backend: 'in-process', status: 'healthy', stream_sniper_keys: 6 } }))
      .toMatchObject({ streamSniperKeys: 6 })
  })

  it('maps admin stats, paginated users, and mutation results to UI casing', async () => {
    const rawUser = {
      id: 3,
      username: 'operator',
      email: 'operator@example.test',
      role: 'admin',
      is_active: true,
      created_at: '2026-07-15T08:00:00Z',
    }
    api.retrieveAdminSystemStats.mockResolvedValue({
      data: {
        total_users: 10,
        active_users: 8,
        admin_users: 2,
        recent_registrations: 1,
      },
    })
    api.retrieveUsers.mockResolvedValue({ data: { users: [rawUser], total: 1 } })
    const wrapper = createWrapper(createClient())
    const stats = renderHook(() => useAdminSystemStats(), { wrapper })
    const users = renderHook(() => useAdminUsers(), { wrapper })

    await waitFor(() => expect(stats.result.current.isSuccess).toBe(true))
    await waitFor(() => expect(users.result.current.isSuccess).toBe(true))

    expect(stats.result.current.data).toEqual(mapAdminSystemStats({
      total_users: 10,
      active_users: 8,
      admin_users: 2,
      recent_registrations: 1,
    }))
    expect(stats.result.current.data).toEqual({
      totalUsers: 10,
      activeUsers: 8,
      adminUsers: 2,
      recentRegistrations: 1,
    })
    expect(users.result.current.data?.items).toEqual([mapAdminUser(rawUser)])
    expect(users.result.current.data?.items[0]).toMatchObject({
      isActive: true,
      createdAt: '2026-07-15T08:00:00Z',
    })
  })

  it('owns Twitch channel search guards and option translation at the hook boundary', async () => {
    await expect(loadTrackedStreamerOptions(' o ')).resolves.toEqual([])
    expect(api.retrieveTwitchChannelSearch).not.toHaveBeenCalled()

    api.retrieveTwitchChannelSearch.mockResolvedValue({
      data: [{
        login: 'operator',
        display_name: 'Operator',
        profile_image_url: '',
        is_live: false,
      }],
    })
    await expect(loadTrackedStreamerOptions(' op ')).resolves.toEqual([
      { value: 'operator', label: 'Operator (operator)' },
    ])
    expect(api.retrieveTwitchChannelSearch).toHaveBeenCalledWith('op')
  })

  it('normalizes processing-job filter IDs before the adapter request', async () => {
    api.retrieveProcessingJobs.mockResolvedValue({ data: { jobs: [], total: 0 } })
    const emptyFilter = renderHook(
      () => useProcessingJobs({ trackedStreamerId: '' }),
      { wrapper: createWrapper(createClient()) },
    )
    await waitFor(() => expect(emptyFilter.result.current.isSuccess).toBe(true))
    expect(api.retrieveProcessingJobs).toHaveBeenLastCalledWith(expect.objectContaining({
      trackedStreamerId: undefined,
    }))

    const numericFilter = renderHook(
      () => useProcessingJobs({ trackedStreamerId: '7' }),
      { wrapper: createWrapper(createClient()) },
    )
    await waitFor(() => expect(numericFilter.result.current.isSuccess).toBe(true))
    expect(api.retrieveProcessingJobs).toHaveBeenLastCalledWith(expect.objectContaining({
      trackedStreamerId: 7,
    }))
  })

  it.each([
    ['tracking stats', () => {
      api.retrieveTrackingStats.mockResolvedValue({ data: {} })
      return renderHook(() => useTrackingStats(), { wrapper: createWrapper(createClient()) })
    }],
    ['tracked streamers', () => {
      api.retrieveTrackedStreamers.mockResolvedValue({ data: {} })
      return renderHook(() => useTrackedStreamers(), { wrapper: createWrapper(createClient()) })
    }],
    ['admin stats', () => {
      api.retrieveAdminSystemStats.mockResolvedValue({ data: {} })
      return renderHook(() => useAdminSystemStats(), { wrapper: createWrapper(createClient()) })
    }],
    ['admin users', () => {
      api.retrieveUsers.mockResolvedValue({ data: {} })
      return renderHook(() => useAdminUsers(), { wrapper: createWrapper(createClient()) })
    }],
    ['creator trends', () => {
      api.retrieveCreatorTrends.mockResolvedValue({ data: {} })
      return renderHook(() => useCreatorTrends(7), { wrapper: createWrapper(createClient()) })
    }],
  ])('rejects a malformed %s response', async (_name, render) => {
    const hook = render()
    await waitFor(() => expect((hook.result.current as any).isError).toBe(true))
    expect((hook.result.current as any).error).toBeInstanceOf(TypeError)
  })

  it('lets callers disable valid creator trend queries', async () => {
    renderHook(() => useCreatorTrends(7, { enabled: false }), {
      wrapper: createWrapper(createClient()),
    })
    await new Promise(resolve => setTimeout(resolve, 0))
    expect(api.retrieveCreatorTrends).not.toHaveBeenCalled()
  })

  it('awaits owned tracking and system invalidation before consumer callbacks', async () => {
    const trackingData = { id: 7, is_active: false }
    const systemData = { message: 'flushed', timestamp: 'now' }
    const userData = {
      id: 3,
      username: 'operator',
      email: 'operator@example.test',
      role: 'admin',
      is_active: true,
      created_at: '2026-07-15T08:00:00Z',
    }
    api.updateTrackedStreamer.mockResolvedValue({ data: trackingData })
    api.flushCache.mockResolvedValue({ data: systemData })
    api.updateUser.mockResolvedValue({ data: userData })
    const queryClient = createClient()
    const events: string[] = []
    const invalidate = vi.spyOn(queryClient, 'invalidateQueries').mockImplementation(async (filters) => {
      events.push(`invalidate:${JSON.stringify(filters?.queryKey)}`)
    })
    const trackingSuccess = vi.fn(() => events.push('tracking-success'))
    const systemSuccess = vi.fn(() => events.push('system-success'))
    const userSuccess = vi.fn(() => events.push('user-success'))
    const wrapper = createWrapper(queryClient)
    const tracking = renderHook(() => useUpdateTrackedStreamer({ onSuccess: trackingSuccess }), { wrapper })
    const system = renderHook(() => useFlushCache({ onSuccess: systemSuccess }), { wrapper })
    const user = renderHook(() => useUpdateAdminUser({ onSuccess: userSuccess }), { wrapper })

    let trackingResult: unknown
    let systemResult: unknown
    let userResult: unknown
    await act(async () => {
      trackingResult = await (tracking.result.current.mutateAsync as unknown as UseMutateAsyncFunction<
        unknown, Error, TrackingUpdateCommand, unknown
      >)({
        streamerId: 7,
        changes: { is_active: false },
      })
      systemResult = await system.result.current.mutateAsync()
      userResult = await (user.result.current.mutateAsync as unknown as UseMutateAsyncFunction<
        unknown, Error, UserUpdateCommand, unknown
      >)({
        userId: 3,
        changes: { email: 'operator@example.test' },
      })
    })

    expect(trackingResult).toBe(trackingData)
    expect(systemResult).toBe(systemData)
    expect(userResult).toEqual(mapAdminUser(userData))
    expect(trackingSuccess).toHaveBeenCalledWith(
      trackingData,
      expect.anything(),
      undefined,
      expect.anything(),
    )

    expect(invalidate).toHaveBeenCalledWith({ queryKey: trackingKeys.all })
    expect(invalidate).toHaveBeenCalledWith({ queryKey: systemKeys.all })
    expect(invalidate).toHaveBeenCalledWith({ queryKey: userAdminKeys.all })
    expect(events.indexOf('tracking-success')).toBeGreaterThan(
      events.indexOf(`invalidate:${JSON.stringify(trackingKeys.all)}`),
    )
    expect(events.indexOf('system-success')).toBeGreaterThan(
      events.indexOf(`invalidate:${JSON.stringify(systemKeys.all)}`),
    )
    expect(events.indexOf('user-success')).toBeGreaterThan(
      events.indexOf(`invalidate:${JSON.stringify(userAdminKeys.all)}`),
    )
  })
})
