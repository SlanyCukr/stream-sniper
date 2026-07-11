import { useQuery } from '@tanstack/react-query'
import { retrieveStreamTimeline } from '@/lib/api'

/**
 * Query key factory for stream-timeline queries
 */
export const streamTimelineKeys = {
    all: [
        'stream-timeline',
    ],
    details: () => [
        ...streamTimelineKeys.all,
        'detail',
    ],
    detail: streamId => [
        ...streamTimelineKeys.details(),
        streamId,
    ],
}

/**
 * Custom hook for a stream's timeline (buckets + moments + metrics), mapped to camelCase.
 * @param {string|number} streamId - The stream ID
 * @param {object} options - Additional query options
 * @returns {object} useQuery result; data = {streamStart, twitchId, bucketSeconds, buckets, moments, metrics}
 */
export const useStreamTimeline = (streamId, options = {}) => useQuery({
    queryKey: streamTimelineKeys.detail(streamId),
    queryFn: async () => {
        const response = await retrieveStreamTimeline(streamId)
        const data = response.data || {
        }
        const metrics = data.metrics
        return {
            streamStart: data.stream_start,
            twitchId: data.twitch_id,
            bucketSeconds: data.bucket_seconds,
            buckets: (data.buckets || []).map(b => ({
                t: b.bucket_minute,
                count: b.message_count,
                unique: b.unique_chatters,
            })),
            moments: (data.moments || []).map(m => ({
                t: m.bucket_minute,
                offsetSeconds: m.offset_seconds,
                count: m.message_count,
                score: m.ratio,
                kind: 'spike',
            })),
            metrics: metrics && {
                uniqueChatters: metrics.unique_chatters,
                msgsPerMin: metrics.messages_per_minute,
                peakMsgsPerMin: null,
                peakAt: metrics.peak_bucket_minute,
                newChatters: metrics.new_chatters,
                returningChatters: metrics.returning_chatters,
                totalMessages: metrics.total_messages,
                durationSec: metrics.duration_seconds,
                peakMessages: metrics.peak_messages,
            },
        }
    },
    enabled: Boolean(streamId), // Only enabled when streamId is provided
    ...options,
})
