import {
    useMutation, useQuery, useQueryClient,
} from '@tanstack/react-query'
import {
    deleteMomentReview,
    putMomentReview,
    retrieveMomentsQueue,
} from '@/lib/api'
import { streamTimelineKeys } from './useStreamTimelineQuery'

export const momentsQueueKeys = {
    all: ['moments-queue'],
    list: filters => [...momentsQueueKeys.all, 'list', filters],
}

const mapMoment = m => ({
    streamId: m.stream_id,
    streamTitle: m.title,
    streamStart: m.start,
    twitchId: m.twitch_id,
    creatorName: m.display_name,
    t: m.bucket_minute,
    offsetSeconds: m.offset_seconds,
    count: m.message_count,
    baseline: m.baseline,
    score: m.ratio,
    unique: m.unique_chatters,
    subShare: m.sub_share,
    emoteShare: m.emote_share,
    topPhrases: m.top_phrases,
    sampleMessages: m.sample_messages,
    status: m.status,
})

export const useMomentsQueue = ({
    status, creatorId, limit, offset,
} = {}, options = {}) => useQuery({
    queryKey: momentsQueueKeys.list({
        status, creatorId, limit, offset,
    }),
    queryFn: async () => {
        const response = await retrieveMomentsQueue({
            status, creatorId, limit, offset,
        })
        const data = response.data || {}
        return {
            items: (data.items || []).map(mapMoment),
            total: data.total ?? 0,
            limit: data.limit,
            offset: data.offset,
        }
    },
    ...options,
})

/**
 * Admin-only review mutation. Pass status 'bookmarked' | 'rejected' to set,
 * or null to clear the review.
 */
export const useMomentReview = (options = {}) => {
    const queryClient = useQueryClient()
    return useMutation({
        mutationFn: async ({
            streamId, bucketMinute, status,
        }) => {
            const response = status
                ? await putMomentReview(streamId, bucketMinute, status)
                : await deleteMomentReview(streamId, bucketMinute)
            return response.data
        },
        onSuccess: (data, variables) => {
            queryClient.invalidateQueries({ queryKey: momentsQueueKeys.all })
            queryClient.invalidateQueries({ queryKey: streamTimelineKeys.detail(variables.streamId) })
        },
        ...options,
    })
}
