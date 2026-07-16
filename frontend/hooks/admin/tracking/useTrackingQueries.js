import { useQuery } from '@tanstack/react-query'
import { useInvalidatingMutation } from '@/hooks/useInvalidatingMutation'
import {
    createTrackedStreamer,
    deleteTrackedStreamer,
    retrieveProcessingJobs,
    retrieveTrackedStreamers,
    retrieveTrackingStats,
    retrieveTwitchChannelSearch,
    updateTrackedStreamer,
} from '@/lib/api/tracking'
import {
    createPage, getRowOffset, normalizePagination,
} from '@/lib/pagination/page'
import {
    requireArray,
    requireArrayField,
    requireBooleanField,
    requireFiniteNumberField,
    requireNullableStringField,
    requireRecord,
    requireStringField,
    requireStringOrFiniteNumberField,
} from '@/lib/api/contractGuards'

/** @typedef {Omit<import('@tanstack/react-query').UseQueryOptions<any, Error, any, readonly unknown[]>, 'queryKey'|'queryFn'>} QueryOptions */
/** @typedef {{pageIndex?: number, pageSize?: number, isActive?: boolean|null, processingEnabled?: boolean|null}} StreamerParams */
/** @typedef {{pageIndex?: number, pageSize?: number, status?: string, trackedStreamerId?: number|string}} JobParams */

/** @param {StreamerParams} [params] */
const normalizeStreamerParams = ({
    pageIndex = 0,
    pageSize = 20,
    isActive = null,
    processingEnabled = null,
} = {}) => ({
    ...normalizePagination(pageIndex, pageSize),
    isActive,
    processingEnabled,
})

/** @param {JobParams} [params] */
const normalizeJobParams = ({
    pageIndex = 0,
    pageSize = 50,
    status = '',
    trackedStreamerId = '',
} = {}) => ({
    ...normalizePagination(pageIndex, pageSize),
    status,
    trackedStreamerId: trackedStreamerId === '' ? undefined : Number(trackedStreamerId),
})

/** @param {unknown} value */
export const mapTrackingStats = value => {
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

/** @param {unknown} value */
export const mapTrackedStreamer = value => {
    const streamer = requireRecord(value, 'tracked streamer')
    return {
        id: requireFiniteNumberField(streamer, 'id', 'tracked streamer'),
        twitchUsername: requireStringField(streamer, 'twitch_username', 'tracked streamer'),
        displayName: requireStringField(streamer, 'display_name', 'tracked streamer'),
        isActive: requireBooleanField(streamer, 'is_active', 'tracked streamer'),
        processingEnabled: requireBooleanField(streamer, 'processing_enabled', 'tracked streamer'),
        lastStreamCheck: requireNullableStringField(streamer, 'last_stream_check', 'tracked streamer'),
        createdAt: requireStringField(streamer, 'created_at', 'tracked streamer'),
    }
}

/** @param {unknown} value */
export const mapProcessingJob = value => {
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

/** @param {unknown} value @param {{pageIndex:number, pageSize:number}} pagination */
export const mapTrackedStreamersPage = (value, pagination) => {
    const data = requireRecord(value, 'tracked streamers')
    return createPage(
        requireArrayField(data, 'streamers', 'tracked streamers').map(mapTrackedStreamer),
        requireFiniteNumberField(data, 'total', 'tracked streamers'),
        pagination.pageIndex,
        pagination.pageSize,
    )
}

/** @param {unknown} value */
export const mapTrackedStreamerOptions = value => {
    const data = requireRecord(value, 'tracked streamer options')
    return requireArrayField(data, 'streamers', 'tracked streamer options').map((value, index) => {
        const label = `tracked streamer options.streamers[${index}]`
        const streamer = requireRecord(value, label)
        return {
            value: requireFiniteNumberField(streamer, 'id', label),
            label: requireStringField(streamer, 'twitch_username', label),
        }
    })
}

/** @param {unknown} value @param {{pageIndex:number, pageSize:number}} pagination */
export const mapProcessingJobsPage = (value, pagination) => {
    const data = requireRecord(value, 'processing jobs')
    return createPage(
        requireArrayField(data, 'jobs', 'processing jobs').map(mapProcessingJob),
        requireFiniteNumberField(data, 'total', 'processing jobs'),
        pagination.pageIndex,
        pagination.pageSize,
    )
}

/** @param {string} query */
export const loadTrackedStreamerOptions = async query => {
    const trimmed = query.trim()
    if (trimmed.length < 2) return []
    const { data } = await retrieveTwitchChannelSearch(trimmed)
    return requireArray(data, 'Twitch channel search').map((value, index) => {
        const label = `Twitch channel search[${index}]`
        const channel = requireRecord(value, label)
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
    streamersList: (/** @type {StreamerParams} */ params) => [
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
    jobsList: (/** @type {JobParams} */ params) => [
        ...trackingKeys.jobs(),
        'list',
        normalizeJobParams(params),
    ],
}

/** @param {QueryOptions} [options] */
export const useTrackingStats = (options = {}) => useQuery({
    ...options,
    queryKey: trackingKeys.stats(),
    queryFn: async () => {
        const { data } = await retrieveTrackingStats()
        return mapTrackingStats(data)
    },
})

/** @param {StreamerParams} [params] @param {QueryOptions} [options] */
export const useTrackedStreamers = (params = {}, options = {}) => {
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

/** @param {QueryOptions} [options] */
export const useTrackedStreamerOptions = (options = {}) => useQuery({
    ...options,
    queryKey: trackingKeys.streamerOptions(),
    queryFn: async () => {
        const { data: value } = await retrieveTrackedStreamers({ pageSize: 1000 })
        return mapTrackedStreamerOptions(value)
    },
    staleTime: 1000 * 60 * 10,
})

/** @param {JobParams} [params] @param {QueryOptions} [options] */
export const useProcessingJobs = (params = {}, options = {}) => {
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

export const useCreateTrackedStreamer = (options = {}) => useInvalidatingMutation(
    async (/** @type {import('@/lib/api/tracking').CreateTrackedStreamerRequest} */ streamer) => (
        await createTrackedStreamer(streamer)
    ).data,
    trackingKeys.all,
    options,
)

export const useUpdateTrackedStreamer = (options = {}) => useInvalidatingMutation(
    async (/** @type {{streamerId: number, changes: import('@/lib/api/tracking').UpdateTrackedStreamerRequest}} */ command) => (
        await updateTrackedStreamer(command.streamerId, command.changes)
    ).data,
    trackingKeys.all,
    options,
)

export const useDeleteTrackedStreamer = (options = {}) => useInvalidatingMutation(
    async (/** @type {number} */ streamerId) => (await deleteTrackedStreamer(streamerId)).data,
    trackingKeys.all,
    options,
)
