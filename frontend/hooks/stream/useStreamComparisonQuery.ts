import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
import { retrieveStreamComparison } from '@/lib/api/streams'
import {
    requireArrayField,
    requireFiniteNumberField,
    requireNullableFiniteNumberField,
    requireNullableStringField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'

export interface StreamComparisonCurvePoint {
    percent: number
    messageCount: number
    uniqueChatters: number
}

export interface StreamComparisonStream {
    streamId: number
    creatorId: number
    creatorNick: string
    creatorDisplayName: string
    title: string
    start: string | null
    durationSeconds: number | null
    totalMessages: number | null
    messagesPerMinute: number | null
    uniqueChatters: number | null
    newChatters: number | null
    returningChatters: number | null
    subShare: number | null
    emoteShare: number | null
    peakMessages: number | null
    peakBucketMinute: string | null
    peakViewers: number | null
    curve: StreamComparisonCurvePoint[]
}

export interface StreamComparisonRetention {
    fromStreamId: number
    toStreamId: number
    fromAudience: number
    toAudience: number
    retained: number
    retentionRate: number | null
}

export interface StreamComparison {
    streams: StreamComparisonStream[]
    retention: StreamComparisonRetention[]
}

type QueryOptions<T> = Omit<
    UseQueryOptions<T, Error, T, readonly unknown[]>,
    'queryKey' | 'queryFn'
>

const streamComparisonKeys = {
    all: ['stream-comparison'],
    detail: (streamIds: number[]) => [...streamComparisonKeys.all, streamIds],
}

export const useStreamComparison = (
    streamIds: number[],
    { enabled = true, ...options }: QueryOptions<StreamComparison> & { enabled?: boolean } = {},
) => useQuery({
    ...options,
    queryKey: streamComparisonKeys.detail(streamIds),
    queryFn: async (): Promise<StreamComparison> => {
        const { data: value } = await retrieveStreamComparison(streamIds)
        const data = requireRecord(value, 'stream comparison')
        return {
            streams: requireArrayField(data, 'streams', 'stream comparison').map((value, index) => {
                const label = `stream comparison.streams[${index}]`
                const stream = requireRecord(value, label)
                return {
                    streamId: requireFiniteNumberField(stream, 'stream_id', label),
                    creatorId: requireFiniteNumberField(stream, 'creator_id', label),
                    creatorNick: requireStringField(stream, 'creator_nick', label),
                    creatorDisplayName: requireStringField(stream, 'creator_display_name', label),
                    title: requireStringField(stream, 'title', label),
                    start: requireNullableStringField(stream, 'start', label),
                    durationSeconds: requireNullableFiniteNumberField(stream, 'duration_seconds', label),
                    totalMessages: requireNullableFiniteNumberField(stream, 'total_messages', label),
                    messagesPerMinute: requireNullableFiniteNumberField(stream, 'messages_per_minute', label),
                    uniqueChatters: requireNullableFiniteNumberField(stream, 'unique_chatters', label),
                    newChatters: requireNullableFiniteNumberField(stream, 'new_chatters', label),
                    returningChatters: requireNullableFiniteNumberField(stream, 'returning_chatters', label),
                    subShare: requireNullableFiniteNumberField(stream, 'sub_share', label),
                    emoteShare: requireNullableFiniteNumberField(stream, 'emote_share', label),
                    peakMessages: requireNullableFiniteNumberField(stream, 'peak_messages', label),
                    peakBucketMinute: requireNullableStringField(stream, 'peak_bucket_minute', label),
                    peakViewers: requireNullableFiniteNumberField(stream, 'peak_viewers', label),
                    curve: requireArrayField(stream, 'curve', label).map((value, pointIndex) => {
                        const pointLabel = `${label}.curve[${pointIndex}]`
                        const point = requireRecord(value, pointLabel)
                        return {
                            percent: requireFiniteNumberField(point, 'percent', pointLabel),
                            messageCount: requireFiniteNumberField(point, 'message_count', pointLabel),
                            uniqueChatters: requireFiniteNumberField(point, 'unique_chatters', pointLabel),
                        }
                    }),
                }
            }),
            retention: requireArrayField(data, 'retention', 'stream comparison').map((value, index) => {
                const label = `stream comparison.retention[${index}]`
                const item = requireRecord(value, label)
                return {
                    fromStreamId: requireFiniteNumberField(item, 'from_stream_id', label),
                    toStreamId: requireFiniteNumberField(item, 'to_stream_id', label),
                    fromAudience: requireFiniteNumberField(item, 'from_audience', label),
                    toAudience: requireFiniteNumberField(item, 'to_audience', label),
                    retained: requireFiniteNumberField(item, 'retained', label),
                    retentionRate: requireNullableFiniteNumberField(item, 'retention_rate', label),
                }
            }),
        }
    },
    enabled: streamIds.length >= 2 && streamIds.length <= 4 && enabled,
})
