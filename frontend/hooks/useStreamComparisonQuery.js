import { useQuery } from '@tanstack/react-query'
import { retrieveStreamComparison } from '@/lib/api'

export const streamComparisonKeys = {
    all: ['stream-comparison'],
    detail: streamIds => [...streamComparisonKeys.all, streamIds],
}

export const useStreamComparison = (streamIds, options = {}) => useQuery({
    queryKey: streamComparisonKeys.detail(streamIds),
    queryFn: async () => {
        const { data = {} } = await retrieveStreamComparison(streamIds)
        return {
            streams: (data.streams || []).map(stream => ({
                streamId: stream.stream_id,
                creatorId: stream.creator_id,
                creatorNick: stream.creator_nick,
                creatorDisplayName: stream.creator_display_name,
                title: stream.title,
                start: stream.start ?? null,
                durationSeconds: stream.duration_seconds ?? null,
                totalMessages: stream.total_messages ?? null,
                messagesPerMinute: stream.messages_per_minute ?? null,
                uniqueChatters: stream.unique_chatters ?? null,
                newChatters: stream.new_chatters ?? null,
                returningChatters: stream.returning_chatters ?? null,
                subShare: stream.sub_share ?? null,
                emoteShare: stream.emote_share ?? null,
                peakMessages: stream.peak_messages ?? null,
                peakBucketMinute: stream.peak_bucket_minute ?? null,
                peakViewers: stream.peak_viewers ?? null,
                curve: (stream.curve || []).map(point => ({
                    percent: point.percent,
                    messageCount: point.message_count,
                    uniqueChatters: point.unique_chatters,
                })),
            })),
            retention: (data.retention || []).map(item => ({
                fromStreamId: item.from_stream_id,
                toStreamId: item.to_stream_id,
                fromAudience: item.from_audience,
                toAudience: item.to_audience,
                retained: item.retained,
                retentionRate: item.retention_rate ?? null,
            })),
        }
    },
    enabled: streamIds.length >= 2 && streamIds.length <= 4,
    ...options,
})
