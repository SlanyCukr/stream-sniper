import {
    useMutation, useQuery, useQueryClient,
} from '@tanstack/react-query'
import {
    createTrackedStreamer,
    deleteTrackedStreamer,
    retrieveProcessingJobs,
    retrieveTrackedStreamers,
    retrieveTrackingStats,
    updateTrackedStreamer,
} from '@/lib/api'

const EMPTY_STREAMERS_RESPONSE = {
    streamers: [
    ],
    total: 0,
    offset: 0,
    limit: 20,
}

const EMPTY_JOBS_RESPONSE = {
    jobs: [
    ],
    total: 0,
    offset: 0,
    limit: 50,
}

const normalizeStreamerParams = ({
    offset = 0,
    limit = 20,
    is_active: isActive = null,
    processing_enabled: processingEnabled = null,
} = {}) => ({
    offset,
    limit,
    is_active: isActive,
    processing_enabled: processingEnabled,
})

const normalizeJobParams = ({
    offset = 0,
    limit = 50,
    status = '',
    tracked_streamer_id: trackedStreamerId = '',
} = {}) => ({
    offset,
    limit,
    status,
    tracked_streamer_id: trackedStreamerId,
})

/** Query-key factory for tracking administration data. */
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
    streamersList: params => [
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
    jobsList: params => [
        ...trackingKeys.jobs(),
        'list',
        normalizeJobParams(params),
    ],
}

/** Fetch overall tracking health and queue statistics. */
export const useTrackingStats = (options = {}) => useQuery({
    queryKey: trackingKeys.stats(),
    queryFn: async () => {
        const { data } = await retrieveTrackingStats()
        return data
    },
    ...options,
})

/** Fetch one filtered, paginated page of tracked streamers. */
export const useTrackedStreamers = (params = {}, options = {}) => {
    const normalizedParams = normalizeStreamerParams(params)
    return useQuery({
        queryKey: trackingKeys.streamersList(normalizedParams),
        queryFn: async () => {
            const { data } = await retrieveTrackedStreamers(normalizedParams)
            return data || EMPTY_STREAMERS_RESPONSE
        },
        ...options,
    })
}

/** Fetch the complete streamer list for select controls. */
export const useTrackedStreamerOptions = (options = {}) => useQuery({
    queryKey: trackingKeys.streamerOptions(),
    queryFn: async () => {
        const { data } = await retrieveTrackedStreamers({ limit: 1000 })
        return (data?.streamers || []).map(streamer => ({
            value: streamer.id,
            label: streamer.twitch_username,
        }))
    },
    staleTime: 1000 * 60 * 10,
    ...options,
})

/** Fetch one filtered, paginated page of processing jobs. */
export const useProcessingJobs = (params = {}, options = {}) => {
    const normalizedParams = normalizeJobParams(params)
    return useQuery({
        queryKey: trackingKeys.jobsList(normalizedParams),
        queryFn: async () => {
            const { data } = await retrieveProcessingJobs(normalizedParams)
            return data || EMPTY_JOBS_RESPONSE
        },
        ...options,
    })
}

const useTrackingMutation = (mutationFn, options = {}) => {
    const queryClient = useQueryClient()
    const {
        onSuccess,
        ...mutationOptions
    } = options

    return useMutation({
        ...mutationOptions,
        mutationFn,
        onSuccess: async (...args) => {
            await queryClient.invalidateQueries({ queryKey: trackingKeys.all })
            await onSuccess?.(...args)
        },
    })
}

/** Create a tracked streamer and refresh all dependent tracking data. */
export const useCreateTrackedStreamer = (options = {}) => useTrackingMutation(
    streamer => createTrackedStreamer(streamer),
    options,
)

/** Update a tracked streamer and refresh all dependent tracking data. */
export const useUpdateTrackedStreamer = (options = {}) => useTrackingMutation(
    ({ streamerId, changes }) => updateTrackedStreamer(streamerId, changes),
    options,
)

/** Delete a tracked streamer and refresh all dependent tracking data. */
export const useDeleteTrackedStreamer = (options = {}) => useTrackingMutation(
    streamerId => deleteTrackedStreamer(streamerId),
    options,
)

/** Convert Axios and native errors to a safe UI message. */
export const getApiErrorMessage = (error, fallback) => error?.response?.data?.detail || error?.message || fallback
