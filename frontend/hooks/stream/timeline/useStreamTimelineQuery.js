import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { retrieveStreamTimeline } from '@/lib/api/streams'
import {
    requireArray,
    requireArrayField,
    requireBooleanField,
    requireFiniteNumberField,
    requireNullableBooleanField,
    requireNullableFiniteNumberField,
    requireNullableStringField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'
import { streamTimelineKeys } from '../../queryKeys'

/** @typedef {Omit<import('@tanstack/react-query').UseQueryOptions<any, Error, any, readonly unknown[]>, 'queryKey'|'queryFn'>} QueryOptions */

export { streamTimelineKeys } from '../../queryKeys'

/**
 * @param {Record<string, unknown>} record
 * @param {string} field
 * @param {string} label
 */
const nullableArrayField = (record, field, label) => {
    const value = record[field]
    return value === null ? null : requireArray(value, `${label}.${field}`)
}

/** @param {unknown} value */
export const mapStreamTimeline = value => {
    const data = requireRecord(value, 'stream timeline')
    const peakViewers = requireNullableFiniteNumberField(data, 'peak_viewers', 'stream timeline')
    const metricsValue = data.metrics
    const metrics = metricsValue === null
        ? null
        : (() => {
            const item = requireRecord(metricsValue, 'stream timeline.metrics')
            return {
                uniqueChatters: requireFiniteNumberField(item, 'unique_chatters', 'stream timeline.metrics'),
                msgsPerMin: requireNullableFiniteNumberField(item, 'messages_per_minute', 'stream timeline.metrics'),
                peakMsgsPerMin: null,
                peakAt: requireNullableStringField(item, 'peak_bucket_minute', 'stream timeline.metrics'),
                newChatters: requireFiniteNumberField(item, 'new_chatters', 'stream timeline.metrics'),
                returningChatters: requireFiniteNumberField(item, 'returning_chatters', 'stream timeline.metrics'),
                totalMessages: requireFiniteNumberField(item, 'total_messages', 'stream timeline.metrics'),
                durationSec: requireNullableFiniteNumberField(item, 'duration_seconds', 'stream timeline.metrics'),
                peakMessages: requireFiniteNumberField(item, 'peak_messages', 'stream timeline.metrics'),
                subMessages: requireNullableFiniteNumberField(item, 'sub_messages', 'stream timeline.metrics'),
                emoteMessages: requireNullableFiniteNumberField(item, 'emote_messages', 'stream timeline.metrics'),
                peakViewers,
            }
        })()

    return {
        streamId: requireFiniteNumberField(data, 'stream_id', 'stream timeline'),
        streamStart: requireNullableStringField(data, 'stream_start', 'stream timeline'),
        twitchVodId: requireNullableStringField(data, 'twitch_id', 'stream timeline'),
        bucketSeconds: requireFiniteNumberField(data, 'bucket_seconds', 'stream timeline'),
        buckets: requireArrayField(data, 'buckets', 'stream timeline').map((value, index) => {
            const label = `stream timeline.buckets[${index}]`
            const bucket = requireRecord(value, label)
            return {
                t: requireStringField(bucket, 'bucket_minute', label),
                count: requireFiniteNumberField(bucket, 'message_count', label),
                unique: requireFiniteNumberField(bucket, 'unique_chatters', label),
                subMessages: requireNullableFiniteNumberField(bucket, 'sub_messages', label),
                emoteMessages: requireNullableFiniteNumberField(bucket, 'emote_messages', label),
            }
        }),
        moments: requireArrayField(data, 'moments', 'stream timeline').map((value, index) => {
            const label = `stream timeline.moments[${index}]`
            const moment = requireRecord(value, label)
            return {
                t: requireStringField(moment, 'bucket_minute', label),
                offsetSeconds: requireNullableFiniteNumberField(moment, 'offset_seconds', label),
                count: requireFiniteNumberField(moment, 'message_count', label),
                score: requireNullableFiniteNumberField(moment, 'ratio', label),
                kind: 'spike',
                isPersisted: requireBooleanField(moment, 'persisted', label),
                status: requireNullableStringField(moment, 'status', label),
                subShare: requireNullableFiniteNumberField(moment, 'sub_share', label),
                emoteShare: requireNullableFiniteNumberField(moment, 'emote_share', label),
                topPhrases: nullableArrayField(moment, 'top_phrases', label),
                sampleMessages: nullableArrayField(moment, 'sample_messages', label),
            }
        }),
        metrics,
        viewerSamples: requireArrayField(data, 'viewer_samples', 'stream timeline').map((value, index) => {
            const label = `stream timeline.viewer_samples[${index}]`
            const sample = requireRecord(value, label)
            return {
                t: requireStringField(sample, 't', label),
                viewerCount: requireFiniteNumberField(sample, 'viewer_count', label),
            }
        }),
        contextChanges: requireArrayField(data, 'context_changes', 'stream timeline').map((value, index) => {
            const label = `stream timeline.context_changes[${index}]`
            const change = requireRecord(value, label)
            return {
                t: requireStringField(change, 't', label),
                title: requireNullableStringField(change, 'title', label),
                categoryId: requireNullableStringField(change, 'category_id', label),
                categoryName: requireNullableStringField(change, 'category_name', label),
                language: requireNullableStringField(change, 'language', label),
                tags: (change.tags === null ? [] : requireArray(change.tags, `${label}.tags`)).map((tag, tagIndex) => {
                    if (typeof tag !== 'string') {
                        throw new TypeError(`${label}.tags[${tagIndex}] must be a string`)
                    }
                    return tag
                }),
                isMature: requireNullableBooleanField(change, 'is_mature', label),
            }
        }),
        peakViewers,
    }
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
 * @param {number} streamId - The normalized stream ID
 * @param {QueryOptions} [options] - Additional query options
 * @returns {object} useQuery result; data = {streamId, streamStart, twitchVodId, bucketSeconds,
 *   buckets, moments, metrics, viewerSamples, peakViewers}
 */
export const useStreamTimeline = (streamId, { enabled = true, ...options } = {}) => useQuery({
    ...options,
    queryKey: streamTimelineKeys.detail(streamId),
    queryFn: async () => {
        const response = await retrieveStreamTimeline(streamId)
        return mapStreamTimeline(response.data)
    },
    enabled: Boolean(streamId) && enabled,
    // Hold the previous render during refetch (moment-review invalidation) — no skeleton flash.
    placeholderData: keepPreviousData,
})
