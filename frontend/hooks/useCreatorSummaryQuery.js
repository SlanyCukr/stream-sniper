import { useQuery } from '@tanstack/react-query'
import { retrieveCreatorSummary } from '@/lib/api'

export const creatorSummaryKeys = {
    all: ['creator-summary'],
    detail: creatorId => [...creatorSummaryKeys.all, { creatorId }],
}

export const useCreatorSummary = (creatorId, options = {}) => useQuery({
    queryKey: creatorSummaryKeys.detail(creatorId),
    queryFn: async () => {
        const { data = {} } = await retrieveCreatorSummary(creatorId)
        return {
            creatorId: data.creator_id,
            nick: data.nick,
            displayName: data.display_name,
            profileImageUrl: data.profile_image_url ?? null,
            twitchId: data.twitch_id ?? null,
            totalStreams: data.total_streams ?? 0,
            firstStreamAt: data.first_stream_at ?? null,
            lastStreamAt: data.last_stream_at ?? null,
            totalMessages: data.total_messages ?? 0,
            durationSeconds: data.duration_seconds ?? null,
            messagesPerMinute: data.messages_per_minute ?? null,
            audienceSize: data.audience_size ?? 0,
            regulars: data.regulars ?? 0,
            latestStream: data.latest_stream ? {
                streamId: data.latest_stream.stream_id,
                title: data.latest_stream.title,
                start: data.latest_stream.start ?? null,
            } : null,
        }
    },
    enabled: Boolean(creatorId),
    ...options,
})
