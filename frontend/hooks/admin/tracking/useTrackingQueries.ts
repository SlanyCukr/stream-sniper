import { useMutation, useQuery, type UseQueryOptions } from '@tanstack/react-query'
import { useInvalidatingMutation } from '@/hooks/useInvalidatingMutation'
import {
    createTrackedStreamer,
    deleteTrackedStreamer,
    probeTwitchChannel,
    retrieveProcessingJobs,
    retrieveTrackedStreamers,
    retrieveTrackingStats,
    retrieveTwitchChannelSearch,
    updateTrackedStreamer,
    type CreateTrackedStreamerRequest,
    type TrackedStreamerDto,
    type UpdateTrackedStreamerRequest,
} from '@/lib/api/tracking'
import {
    createPage, getRowOffset, normalizePagination,
} from '@/lib/pagination/page'
import {
    requireArray,
    requireArrayField,
    requireBooleanField,
    requireFiniteNumberField,
    requireNullableFiniteNumberField,
    requireNullableStringField,
    requireRecord,
    requireStringField,
    requireStringOrFiniteNumberField,
} from '@/lib/api/contractGuards'

// queryKey/queryFn stay accepted-but-untyped: every hook below always overwrites
// them with its own key/fetcher (matching runtime behavior), so a caller
// passing either does not influence what actually runs.
type QueryOptions<T> = Omit<UseQueryOptions<T, Error, T, readonly unknown[]>, 'queryKey' | 'queryFn'> & {
    queryKey?: unknown
    queryFn?: unknown
}

interface StreamerParams {
    pageIndex?: number
    pageSize?: number
    isActive?: boolean | null
    processingEnabled?: boolean | null
}

interface JobParams {
    pageIndex?: number
    pageSize?: number
    status?: string
    trackedStreamerId?: number | string
}

const normalizeStreamerParams = ({
    pageIndex = 0,
    pageSize = 20,
    isActive = null,
    processingEnabled = null,
}: StreamerParams = {}) => ({
    ...normalizePagination(pageIndex, pageSize),
    isActive,
    processingEnabled,
})

const normalizeJobParams = ({
    pageIndex = 0,
    pageSize = 50,
    status = '',
    trackedStreamerId = '',
}: JobParams = {}) => ({
    ...normalizePagination(pageIndex, pageSize),
    status,
    trackedStreamerId: trackedStreamerId === '' ? undefined : Number(trackedStreamerId),
})

export interface TrackingStats {
    systemStatus: {
        monitoringActive: boolean
        monitoringDegraded: boolean
        processingQueueSize: number
        failedJobs: number
    }
    trackedStreamers: {
        total: number
        active: number
        processingEnabled: number
        inactive: number
    }
    processingJobs: {
        total: number
        pending: number
        inProgress: number
        completed: number
        failed: number
        recent24h: number
    }
}

export const mapTrackingStats = (value: unknown): TrackingStats => {
    const data = requireRecord(value, 'tracking stats')
    const system = requireRecord(data.system_status, 'tracking stats.system_status')
    const streamers = requireRecord(data.tracked_streamers, 'tracking stats.tracked_streamers')
    const jobs = requireRecord(data.processing_jobs, 'tracking stats.processing_jobs')
    return {
        systemStatus: {
            monitoringActive: requireBooleanField(system, 'monitoring_active', 'tracking stats.system_status'),
            monitoringDegraded: requireBooleanField(system, 'monitoring_degraded', 'tracking stats.system_status'),
            processingQueueSize: requireFiniteNumberField(system, 'processing_queue_size', 'tracking stats.system_status'),
            failedJobs: requireFiniteNumberField(system, 'failed_jobs', 'tracking stats.system_status'),
        },
        trackedStreamers: {
            total: requireFiniteNumberField(streamers, 'total', 'tracking stats.tracked_streamers'),
            active: requireFiniteNumberField(streamers, 'active', 'tracking stats.tracked_streamers'),
            processingEnabled: requireFiniteNumberField(streamers, 'processing_enabled', 'tracking stats.tracked_streamers'),
            inactive: requireFiniteNumberField(streamers, 'inactive', 'tracking stats.tracked_streamers'),
        },
        processingJobs: {
            total: requireFiniteNumberField(jobs, 'total', 'tracking stats.processing_jobs'),
            pending: requireFiniteNumberField(jobs, 'pending', 'tracking stats.processing_jobs'),
            inProgress: requireFiniteNumberField(jobs, 'in_progress', 'tracking stats.processing_jobs'),
            completed: requireFiniteNumberField(jobs, 'completed', 'tracking stats.processing_jobs'),
            failed: requireFiniteNumberField(jobs, 'failed', 'tracking stats.processing_jobs'),
            recent24h: requireFiniteNumberField(jobs, 'recent_24h', 'tracking stats.processing_jobs'),
        },
    }
}

export interface TrackedStreamer {
    id: number
    twitchUsername: string
    displayName: string
    isActive: boolean
    processingEnabled: boolean
    lastStreamCheck: string | null
    createdAt: string
    totalStreamsCollected: number | null
    lastCollectedStreamStart: string | null
}

export const mapTrackedStreamer = (value: unknown): TrackedStreamer => {
    const streamer = requireRecord(value, 'tracked streamer')
    return {
        id: requireFiniteNumberField(streamer, 'id', 'tracked streamer'),
        twitchUsername: requireStringField(streamer, 'twitch_username', 'tracked streamer'),
        displayName: requireStringField(streamer, 'display_name', 'tracked streamer'),
        isActive: requireBooleanField(streamer, 'is_active', 'tracked streamer'),
        processingEnabled: requireBooleanField(streamer, 'processing_enabled', 'tracked streamer'),
        lastStreamCheck: requireNullableStringField(streamer, 'last_stream_check', 'tracked streamer'),
        createdAt: requireStringField(streamer, 'created_at', 'tracked streamer'),
        totalStreamsCollected: requireNullableFiniteNumberField(streamer, 'total_streams_collected', 'tracked streamer'),
        lastCollectedStreamStart: requireNullableStringField(streamer, 'last_collected_stream_start', 'tracked streamer'),
    }
}

export interface TwitchProbeResult {
    isLive: boolean
    archiveVodCount: number
    lastVodCreatedAt: string | null
    checkedAt: string
}

const mapTwitchProbeResult = (value: unknown): TwitchProbeResult => {
    const probe = requireRecord(value, 'twitch probe result')
    return {
        isLive: requireBooleanField(probe, 'is_live', 'twitch probe result'),
        archiveVodCount: requireFiniteNumberField(probe, 'archive_vod_count', 'twitch probe result'),
        lastVodCreatedAt: requireNullableStringField(probe, 'last_vod_created_at', 'twitch probe result'),
        checkedAt: requireStringField(probe, 'checked_at', 'twitch probe result'),
    }
}

export interface ProcessingJob {
    id: number
    twitchUsername: string
    streamerDisplayName: string | null
    twitchVodId: string | number
    status: string
    createdAt: string | null
    startedAt: string | null
    completedAt: string | null
    retryCount: number
}

export const mapProcessingJob = (value: unknown): ProcessingJob => {
    const job = requireRecord(value, 'processing job')
    return {
        id: requireFiniteNumberField(job, 'id', 'processing job'),
        twitchUsername: requireStringField(job, 'twitch_username', 'processing job'),
        streamerDisplayName: requireNullableStringField(job, 'streamer_display_name', 'processing job'),
        twitchVodId: requireStringOrFiniteNumberField(job, 'twitch_vod_id', 'processing job'),
        status: requireStringField(job, 'status', 'processing job'),
        createdAt: requireNullableStringField(job, 'created_at', 'processing job'),
        startedAt: requireNullableStringField(job, 'started_at', 'processing job'),
        completedAt: requireNullableStringField(job, 'completed_at', 'processing job'),
        retryCount: requireFiniteNumberField(job, 'retry_count', 'processing job'),
    }
}

const mapTrackedStreamersPage = (value: unknown, pagination: { pageIndex: number, pageSize: number }) => {
    const data = requireRecord(value, 'tracked streamers')
    return createPage(
        requireArrayField(data, 'streamers', 'tracked streamers').map(mapTrackedStreamer),
        requireFiniteNumberField(data, 'total', 'tracked streamers'),
        pagination.pageIndex,
        pagination.pageSize,
    )
}

const mapTrackedStreamerOptions = (value: unknown) => {
    const data = requireRecord(value, 'tracked streamer options')
    return requireArrayField(data, 'streamers', 'tracked streamer options').map((entry, index) => {
        const label = `tracked streamer options.streamers[${index}]`
        const streamer = requireRecord(entry, label)
        return {
            value: requireFiniteNumberField(streamer, 'id', label),
            label: requireStringField(streamer, 'twitch_username', label),
        }
    })
}

const mapProcessingJobsPage = (value: unknown, pagination: { pageIndex: number, pageSize: number }) => {
    const data = requireRecord(value, 'processing jobs')
    return createPage(
        requireArrayField(data, 'jobs', 'processing jobs').map(mapProcessingJob),
        requireFiniteNumberField(data, 'total', 'processing jobs'),
        pagination.pageIndex,
        pagination.pageSize,
    )
}

export const loadTrackedStreamerOptions = async (query: string) => {
    const trimmed = query.trim()
    if (trimmed.length < 2) return []
    const { data } = await retrieveTwitchChannelSearch(trimmed)
    return requireArray(data, 'Twitch channel search').map((entry, index) => {
        const label = `Twitch channel search[${index}]`
        const channel = requireRecord(entry, label)
        const login = requireStringField(channel, 'login', label)
        const displayName = requireStringField(channel, 'display_name', label)
        return {
            value: login,
            label: displayName ? `${displayName} (${login})` : login,
        }
    })
}

export const trackingKeys = {
    all: [
        'tracking',
    ],
    stats: () => [
        ...trackingKeys.all,
        'stats',
    ],
    streamers: () => [
        ...trackingKeys.all,
        'streamers',
    ],
    streamersList: (params?: StreamerParams) => [
        ...trackingKeys.streamers(),
        'list',
        normalizeStreamerParams(params),
    ],
    streamerOptions: () => [
        ...trackingKeys.streamers(),
        'options',
    ],
    jobs: () => [
        ...trackingKeys.all,
        'jobs',
    ],
    jobsList: (params?: JobParams) => [
        ...trackingKeys.jobs(),
        'list',
        normalizeJobParams(params),
    ],
}

export const useTrackingStats = (options: QueryOptions<TrackingStats> = {}) => useQuery({
    ...options,
    queryKey: trackingKeys.stats(),
    queryFn: async () => {
        const { data } = await retrieveTrackingStats()
        return mapTrackingStats(data)
    },
})

export const useTrackedStreamers = (
    params: StreamerParams = {},
    options: QueryOptions<ReturnType<typeof mapTrackedStreamersPage>> = {},
) => {
    const normalizedParams = normalizeStreamerParams(params)
    return useQuery({
        ...options,
        queryKey: trackingKeys.streamersList(normalizedParams),
        queryFn: async () => {
            const { data: value } = await retrieveTrackedStreamers({
                rowOffset: getRowOffset(normalizedParams.pageIndex, normalizedParams.pageSize),
                pageSize: normalizedParams.pageSize,
                isActive: normalizedParams.isActive,
                processingEnabled: normalizedParams.processingEnabled,
            })
            return mapTrackedStreamersPage(value, normalizedParams)
        },
    })
}

export const useTrackedStreamerOptions = (
    options: QueryOptions<ReturnType<typeof mapTrackedStreamerOptions>> = {},
) => useQuery({
    ...options,
    queryKey: trackingKeys.streamerOptions(),
    queryFn: async () => {
        const { data: value } = await retrieveTrackedStreamers({ pageSize: 1000 })
        return mapTrackedStreamerOptions(value)
    },
    staleTime: 1000 * 60 * 10,
})

export const useProcessingJobs = (
    params: JobParams = {},
    options: QueryOptions<ReturnType<typeof mapProcessingJobsPage>> = {},
) => {
    const normalizedParams = normalizeJobParams(params)
    return useQuery({
        ...options,
        queryKey: trackingKeys.jobsList(normalizedParams),
        queryFn: async () => {
            const { data: value } = await retrieveProcessingJobs({
                rowOffset: getRowOffset(normalizedParams.pageIndex, normalizedParams.pageSize),
                pageSize: normalizedParams.pageSize,
                status: normalizedParams.status,
                trackedStreamerId: normalizedParams.trackedStreamerId,
            })
            return mapProcessingJobsPage(value, normalizedParams)
        },
    })
}

// NOTE: unlike useUserAdminQueries' create/update mutations, these resolve to
// the raw wire DTO rather than a mapped camelCase model — preserved as-is.
export const useCreateTrackedStreamer = (options = {}) => useInvalidatingMutation(
    async (streamer: CreateTrackedStreamerRequest): Promise<TrackedStreamerDto> => (
        await createTrackedStreamer(streamer)
    ).data,
    trackingKeys.all,
    options,
)

export const useUpdateTrackedStreamer = (options = {}) => useInvalidatingMutation(
    async (command: { streamerId: number, changes: UpdateTrackedStreamerRequest }): Promise<TrackedStreamerDto> => (
        await updateTrackedStreamer(command.streamerId, command.changes)
    ).data,
    trackingKeys.all,
    options,
)

export const useDeleteTrackedStreamer = (options = {}) => useInvalidatingMutation(
    async (streamerId: number): Promise<void> => (await deleteTrackedStreamer(streamerId)).data,
    trackingKeys.all,
    options,
)

/**
 * On-demand Twitch snapshot for one tracked streamer. Nothing is stored, so
 * this is a plain mutation — the caller keeps the result in component state.
 */
export const useProbeTwitchChannel = (options = {}) => useMutation({
    mutationFn: async (streamerId: number) => (
        mapTwitchProbeResult((await probeTwitchChannel(streamerId)).data)
    ),
    ...options,
})
