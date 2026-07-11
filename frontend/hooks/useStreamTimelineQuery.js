import { keepPreviousData, useQuery } from '@tanstack/react-query'
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
 *
 * Nullable analytics fields (subMessages/emoteMessages, moment enrichment, peakViewers)
 * are preserved as null/undefined — null means "not yet computed under the 0008 rollup",
 * NOT a real 0, so consumers can hide the corresponding tile/series instead of showing 0.
 * peakViewers is folded into the metrics object so StreamMetrics (which receives only
 * `metrics`) can surface it without a new prop from views/Stream.jsx.
 *
 * @param {string|number} streamId - The stream ID
 * @param {object} options - Additional query options
 * @returns {object} useQuery result; data = {streamId, streamStart, twitchId, bucketSeconds,
 *   buckets, moments, metrics, viewerSamples, peakViewers}
 */
export const useStreamTimeline = (streamId, options = {}) => useQuery({
    queryKey: streamTimelineKeys.detail(streamId),
    queryFn: async () => {
        const response = await retrieveStreamTimeline(streamId)
        const data = response.data || {
        }
        const metrics = data.metrics
        const peakViewers = data.peak_viewers ?? null
        return {
            streamId: data.stream_id,
            streamStart: data.stream_start,
            twitchId: data.twitch_id,
            bucketSeconds: data.bucket_seconds,
            buckets: (data.buckets || []).map(b => ({
                t: b.bucket_minute,
                count: b.message_count,
                unique: b.unique_chatters,
                // null = not yet re-rolled under 0008 (unknown, not a real 0)
                subMessages: b.sub_messages ?? null,
                emoteMessages: b.emote_messages ?? null,
            })),
            moments: (data.moments || []).map(m => ({
                t: m.bucket_minute,
                offsetSeconds: m.offset_seconds,
                count: m.message_count,
                score: m.ratio,
                kind: 'spike',
                // Enrichment present only on persisted moments; null on the live fallback path.
                status: m.status ?? null,
                subShare: m.sub_share ?? null,
                emoteShare: m.emote_share ?? null,
                topPhrases: m.top_phrases ?? null,
                sampleMessages: m.sample_messages ?? null,
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
                subMessages: metrics.sub_messages ?? null,
                emoteMessages: metrics.emote_messages ?? null,
                peakViewers,
            },
            viewerSamples: (data.viewer_samples || []).map(s => ({
                t: s.t,
                viewerCount: s.viewer_count,
            })),
            peakViewers,
        }
    },
    enabled: Boolean(streamId), // Only enabled when streamId is provided
    // Hold the previous render during refetch (moment-review invalidation) — no skeleton flash.
    placeholderData: keepPreviousData,
    ...options,
})
