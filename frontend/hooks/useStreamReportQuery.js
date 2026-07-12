import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { retrieveStreamReport } from '@/lib/api'

/**
 * Query key factory for stream report-card queries
 */
export const streamReportKeys = {
    all: [
        'stream-report',
    ],
    details: () => [
        ...streamReportKeys.all,
        'detail',
    ],
    detail: streamId => [
        ...streamReportKeys.details(),
        streamId,
    ],
}

/**
 * Map a snake_case ReportMetric to camelCase, preserving nulls.
 *
 * Nullable = unknown contract: null means "not computed / not enough baseline",
 * never a real 0 — consumers hide the tile/chip instead of rendering 0.
 * @param {object|null|undefined} metric - {value, delta_pct, percentile, baseline_median}
 * @returns {object|null}
 */
const mapMetric = metric => (metric
    ? {
        value: metric.value ?? null,
        deltaPct: metric.delta_pct ?? null,
        percentile: metric.percentile ?? null,
        baselineMedian: metric.baseline_median ?? null,
    }
    : null)

/**
 * Custom hook for a stream's report card (metrics annotated with baseline
 * delta/percentile, top emote/phrase/moments), mapped to camelCase.
 *
 * All nullable analytics fields are preserved via `?? null` — a null metric
 * value means the rollup has not run, and null delta/percentile means the
 * baseline was too small (< 2 rolled-up previous streams).
 *
 * @param {string|number} streamId - The stream ID
 * @param {object} options - Additional query options
 * @returns {object} useQuery result; data = {streamId, creatorId, creatorNick,
 *   title, start, end, durationSeconds, baselineCount, lookback, metrics,
 *   peakBucketMinute, topEmote, topPhrase, topMoments}
 */
export const useStreamReport = (streamId, options = {}) => useQuery({
    queryKey: streamReportKeys.detail(streamId),
    queryFn: async () => {
        const response = await retrieveStreamReport(streamId)
        const data = response.data || {
        }
        const metrics = data.metrics || {
        }
        return {
            streamId: data.stream_id,
            creatorId: data.creator_id,
            creatorNick: data.creator_nick ?? null,
            title: data.title ?? null,
            start: data.start ?? null,
            end: data.end ?? null,
            durationSeconds: data.duration_seconds ?? null,
            baselineCount: data.baseline_count ?? 0,
            lookback: data.lookback,
            metrics: {
                messagesPerMinute: mapMetric(metrics.messages_per_minute),
                totalMessages: mapMetric(metrics.total_messages),
                uniqueChatters: mapMetric(metrics.unique_chatters),
                newChatters: mapMetric(metrics.new_chatters),
                returningChatters: mapMetric(metrics.returning_chatters),
                subShare: mapMetric(metrics.sub_share),
                peakMessages: mapMetric(metrics.peak_messages),
                avgViewers: mapMetric(metrics.avg_viewers),
                peakViewers: mapMetric(metrics.peak_viewers),
            },
            peakBucketMinute: data.peak_bucket_minute ?? null,
            topEmote: data.top_emote
                ? {
                    name: data.top_emote.name,
                    source: data.top_emote.source,
                    providerId: data.top_emote.provider_id ?? null,
                    usageCount: data.top_emote.usage_count,
                    chatterCount: data.top_emote.chatter_count,
                }
                : null,
            topPhrase: data.top_phrase
                ? {
                    phrase: data.top_phrase.phrase,
                    usageCount: data.top_phrase.usage_count,
                    chatterCount: data.top_phrase.chatter_count,
                }
                : null,
            topMoments: (data.top_moments || []).map(m => ({
                bucketMinute: m.bucket_minute,
                offsetSeconds: m.offset_seconds ?? null,
                messageCount: m.message_count,
                ratio: m.ratio ?? null,
                status: m.status ?? null,
            })),
        }
    },
    enabled: Boolean(streamId),
    // Hold the previous render during refetch — no skeleton flash.
    placeholderData: keepPreviousData,
    ...options,
})
