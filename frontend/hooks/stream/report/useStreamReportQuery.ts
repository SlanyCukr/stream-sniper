import { keepPreviousData, useQuery, type UseQueryOptions } from '@tanstack/react-query'
import { retrieveStreamReport } from '@/lib/api/streams'
import {
    requireArrayField,
    requireFiniteNumberField,
    requireNullableFiniteNumberField,
    requireNullableStringField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'

type QueryOptions<T> = Omit<
    UseQueryOptions<T, Error, T, readonly unknown[]>,
    'queryKey' | 'queryFn'
> & { enabled?: boolean }

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
    detail: (streamId: number) => [
        ...streamReportKeys.details(),
        streamId,
    ],
}

export interface ReportMetric {
    value: number | null
    deltaPct: number | null
    percentile: number | null
    baselineMedian: number | null
}

export interface ReportTopEmote {
    name: string
    source: string
    providerId: string | null
    usageCount: number
    chatterCount: number
}

export interface ReportTopPhrase {
    phrase: string
    usageCount: number
    chatterCount: number
}

export interface ReportMoment {
    bucketMinute: string
    offsetSeconds: number | null
    messageCount: number
    ratio: number | null
    status: string | null
}

export interface StreamReport {
    streamId: number
    creatorId: number
    creatorNick: string | null
    title: string | null
    start: string | null
    end: string | null
    durationSeconds: number | null
    baselineCount: number
    lookback: number
    metrics: {
        messagesPerMinute: ReportMetric
        totalMessages: ReportMetric
        uniqueChatters: ReportMetric
        newChatters: ReportMetric
        returningChatters: ReportMetric
        subShare: ReportMetric
        peakMessages: ReportMetric
        avgViewers: ReportMetric
        peakViewers: ReportMetric
    }
    peakBucketMinute: string | null
    topEmote: ReportTopEmote | null
    topPhrase: ReportTopPhrase | null
    topMoments: ReportMoment[]
}

/**
 * Map a snake_case ReportMetric to camelCase, preserving nulls.
 *
 * Nullable = unknown contract: null means "not computed / not enough baseline",
 * never a real 0 — consumers hide the tile/chip instead of rendering 0.
 */
export const mapReportMetric = (value: unknown, label: string): ReportMetric => {
    const metric = requireRecord(value, label)
    return {
        value: requireNullableFiniteNumberField(metric, 'value', label),
        deltaPct: requireNullableFiniteNumberField(metric, 'delta_pct', label),
        percentile: requireNullableFiniteNumberField(metric, 'percentile', label),
        baselineMedian: requireNullableFiniteNumberField(metric, 'baseline_median', label),
    }
}

const mapReportTopEmote = (value: unknown): ReportTopEmote | null => {
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

const mapReportTopPhrase = (value: unknown): ReportTopPhrase | null => {
    if (value === null) return null
    const phrase = requireRecord(value, 'stream report.top_phrase')
    return {
        phrase: requireStringField(phrase, 'phrase', 'stream report.top_phrase'),
        usageCount: requireFiniteNumberField(phrase, 'usage_count', 'stream report.top_phrase'),
        chatterCount: requireFiniteNumberField(phrase, 'chatter_count', 'stream report.top_phrase'),
    }
}

const mapReportMoment = (value: unknown, index: number): ReportMoment => {
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

const mapStreamReport = (value: unknown): StreamReport => {
    const data = requireRecord(value, 'stream report')
    const metrics = requireRecord(data.metrics, 'stream report.metrics')
    const mapMetric = (key: string) => (
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
 */
export const useStreamReport = (
    streamId: number,
    { enabled = true, ...options }: QueryOptions<StreamReport> = {},
) => useQuery({
    ...options,
    queryKey: streamReportKeys.detail(streamId),
    queryFn: async () => {
        const response = await retrieveStreamReport(streamId)
        return mapStreamReport(response)
    },
    enabled: Boolean(streamId) && enabled,
    // Hold the previous render during refetch — no skeleton flash.
    placeholderData: keepPreviousData,
})
