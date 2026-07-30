import { keepPreviousData } from '@tanstack/react-query'
import { retrieveStreamTimeline } from '@/lib/api/streams'
import {
    mapNullableMomentPhrases,
    mapNullableMomentSamples,
    requireNullableMomentReviewStatus,
} from '@/lib/api/moments'
import type {
    MomentPhrase, MomentReviewStatus, MomentSampleMessage,
} from '@/lib/models/momentQueue'
import { defineGatedQuery, type QueryOptions } from '@/hooks/defineQuery'
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

export { streamTimelineKeys } from '../../queryKeys'

export interface TimelineBucket {
    t: string
    count: number
    unique: number
    subMessages: number | null
    emoteMessages: number | null
}

export interface TimelineMoment {
    t: string
    offsetSeconds: number | null
    count: number
    score: number | null
    kind: 'spike'
    isPersisted: boolean
    status: MomentReviewStatus | null
    subShare: number | null
    emoteShare: number | null
    topPhrases: MomentPhrase[] | null
    sampleMessages: MomentSampleMessage[] | null
}

export interface TimelineMetrics {
    uniqueChatters: number
    msgsPerMin: number | null
    peakMsgsPerMin: null
    peakAt: string | null
    newChatters: number
    returningChatters: number
    totalMessages: number
    durationSec: number | null
    peakMessages: number
    subMessages: number | null
    emoteMessages: number | null
    peakViewers: number | null
}

export interface ViewerSample {
    t: string
    viewerCount: number
}

export interface TimelineContextChange {
    t: string
    title: string | null
    categoryId: string | null
    categoryName: string | null
    language: string | null
    tags: string[]
    isMature: boolean | null
}

export interface StreamTimeline {
    streamId: number
    streamStart: string | null
    twitchVodId: string | null
    bucketSeconds: number
    buckets: TimelineBucket[]
    moments: TimelineMoment[]
    metrics: TimelineMetrics | null
    viewerSamples: ViewerSample[]
    contextChanges: TimelineContextChange[]
    peakViewers: number | null
}

const mapStreamTimeline = (value: unknown): StreamTimeline => {
    const data = requireRecord(value, 'stream timeline')
    const peakViewers = requireNullableFiniteNumberField(data, 'peak_viewers', 'stream timeline')
    const metricsValue = data.metrics
    const metrics: TimelineMetrics | null = metricsValue === null
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
                kind: 'spike' as const,
                isPersisted: requireBooleanField(moment, 'persisted', label),
                status: requireNullableMomentReviewStatus(moment.status, `${label}.status`),
                subShare: requireNullableFiniteNumberField(moment, 'sub_share', label),
                emoteShare: requireNullableFiniteNumberField(moment, 'emote_share', label),
                topPhrases: mapNullableMomentPhrases(moment.top_phrases, `${label}.top_phrases`),
                sampleMessages: mapNullableMomentSamples(moment.sample_messages, `${label}.sample_messages`),
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
 * `metrics`) can surface it without a new prop from views/stream/Stream.tsx.
 */
const streamTimelineQuery = defineGatedQuery({
    label: 'stream timeline',
    key: (streamId: number) => streamTimelineKeys.detail(streamId),
    validate: streamId => (streamId ? streamId : null),
    fetch: retrieveStreamTimeline,
    map: mapStreamTimeline,
})

export const useStreamTimeline = (
    streamId: number,
    options: QueryOptions<StreamTimeline> = {},
    // Hard merge, matching the pre-seam behavior: holding the previous render
    // across moment-review invalidation (no skeleton flash) is part of this
    // hook's contract, not a caller-tunable option.
) => streamTimelineQuery(streamId, { ...options, placeholderData: keepPreviousData })
