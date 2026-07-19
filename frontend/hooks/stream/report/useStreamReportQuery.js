import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { retrieveStreamReport } from '@/lib/api/streams'
import {
    requireArrayField,
    requireFiniteNumberField,
    requireNullableFiniteNumberField,
    requireNullableStringField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'

/** @typedef {Omit<import('@tanstack/react-query').UseQueryOptions<any, Error, any, readonly unknown[]>, 'queryKey'|'queryFn'>} QueryOptions */

/**
 * Query key factory for stream report-card queries
 */
const streamReportKeys = {
    all: [
        'stream-report',
    ],
    details: () => [
        ...streamReportKeys.all,
        'detail',
    ],
    detail: (/** @type {number} */ streamId) => [
        ...streamReportKeys.details(),
        streamId,
    ],
}

/**
 * Map a snake_case ReportMetric to camelCase, preserving nulls.
 *
 * Nullable = unknown contract: null means "not computed / not enough baseline",
 * never a real 0 — consumers hide the tile/chip instead of rendering 0.
 * @param {unknown} value
 * @param {string} label
 */
export const mapReportMetric = (value, label) => {
    const metric = requireRecord(value, label)
    return {
        value: requireNullableFiniteNumberField(metric, 'value', label),
        deltaPct: requireNullableFiniteNumberField(metric, 'delta_pct', label),
        percentile: requireNullableFiniteNumberField(metric, 'percentile', label),
        baselineMedian: requireNullableFiniteNumberField(metric, 'baseline_median', label),
    }
}

/** @param {unknown} value */
const mapReportTopEmote = value => {
    if (value === null) return null
    const emote = requireRecord(value, 'stream report.top_emote')
    return {
        name: requireStringField(emote, 'name', 'stream report.top_emote'),
        source: requireStringField(emote, 'source', 'stream report.top_emote'),
        providerId: requireNullableStringField(emote, 'provider_id', 'stream report.top_emote'),
        usageCount: requireFiniteNumberField(emote, 'usage_count', 'stream report.top_emote'),
        chatterCount: requireFiniteNumberField(emote, 'chatter_count', 'stream report.top_emote'),
    }
}

/** @param {unknown} value */
const mapReportTopPhrase = value => {
    if (value === null) return null
    const phrase = requireRecord(value, 'stream report.top_phrase')
    return {
        phrase: requireStringField(phrase, 'phrase', 'stream report.top_phrase'),
        usageCount: requireFiniteNumberField(phrase, 'usage_count', 'stream report.top_phrase'),
        chatterCount: requireFiniteNumberField(phrase, 'chatter_count', 'stream report.top_phrase'),
    }
}

/** @param {unknown} value @param {number} index */
const mapReportMoment = (value, index) => {
    const label = `stream report.top_moments[${index}]`
    const moment = requireRecord(value, label)
    return {
        bucketMinute: requireStringField(moment, 'bucket_minute', label),
        offsetSeconds: requireNullableFiniteNumberField(moment, 'offset_seconds', label),
        messageCount: requireFiniteNumberField(moment, 'message_count', label),
        ratio: requireNullableFiniteNumberField(moment, 'ratio', label),
        status: requireNullableStringField(moment, 'status', label),
    }
}

/** @param {unknown} value */
const mapStreamReport = value => {
    const data = requireRecord(value, 'stream report')
    const metrics = requireRecord(data.metrics, 'stream report.metrics')
    const mapMetric = (/** @type {string} */ key) => (
        mapReportMetric(metrics[key], `stream report.metrics.${key}`)
    )

    return {
        streamId: requireFiniteNumberField(data, 'stream_id', 'stream report'),
        creatorId: requireFiniteNumberField(data, 'creator_id', 'stream report'),
        creatorNick: requireNullableStringField(data, 'creator_nick', 'stream report'),
        title: requireNullableStringField(data, 'title', 'stream report'),
        start: requireNullableStringField(data, 'start', 'stream report'),
        end: requireNullableStringField(data, 'end', 'stream report'),
        durationSeconds: requireNullableFiniteNumberField(data, 'duration_seconds', 'stream report'),
        baselineCount: requireFiniteNumberField(data, 'baseline_count', 'stream report'),
        lookback: requireFiniteNumberField(data, 'lookback', 'stream report'),
        metrics: {
            messagesPerMinute: mapMetric('messages_per_minute'),
            totalMessages: mapMetric('total_messages'),
            uniqueChatters: mapMetric('unique_chatters'),
            newChatters: mapMetric('new_chatters'),
            returningChatters: mapMetric('returning_chatters'),
            subShare: mapMetric('sub_share'),
            peakMessages: mapMetric('peak_messages'),
            avgViewers: mapMetric('avg_viewers'),
            peakViewers: mapMetric('peak_viewers'),
        },
        peakBucketMinute: requireNullableStringField(data, 'peak_bucket_minute', 'stream report'),
        topEmote: mapReportTopEmote(data.top_emote),
        topPhrase: mapReportTopPhrase(data.top_phrase),
        topMoments: requireArrayField(data, 'top_moments', 'stream report').map(mapReportMoment),
    }
}

/**
 * Custom hook for a stream's report card (metrics annotated with baseline
 * delta/percentile, top emote/phrase/moments), mapped to camelCase.
 *
 * All nullable analytics fields are preserved via `?? null` — a null metric
 * value means the rollup has not run, and null delta/percentile means the
 * baseline was too small (< 2 rolled-up previous streams).
 *
 * @param {number} streamId - The normalized stream ID
 * @param {QueryOptions} [options] - Additional query options
 * @returns {object} useQuery result; data = {streamId, creatorId, creatorNick,
 *   title, start, end, durationSeconds, baselineCount, lookback, metrics,
 *   peakBucketMinute, topEmote, topPhrase, topMoments}
 */
export const useStreamReport = (streamId, { enabled = true, ...options } = {}) => useQuery({
    ...options,
    queryKey: streamReportKeys.detail(streamId),
    queryFn: async () => {
        const response = await retrieveStreamReport(streamId)
        return mapStreamReport(response.data)
    },
    enabled: Boolean(streamId) && enabled,
    // Hold the previous render during refetch — no skeleton flash.
    placeholderData: keepPreviousData,
})
