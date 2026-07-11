import { useQuery } from '@tanstack/react-query'
import { retrieveCreatorTrends } from '@/lib/api'

/**
 * Query key factory for creator per-stream trend queries
 */
export const creatorTrendsKeys = {
    all: [
        'creator-trends',
    ],
    details: () => [
        ...creatorTrendsKeys.all,
        'detail',
    ],
    detail: creatorId => [
        ...creatorTrendsKeys.details(),
        creatorId,
    ],
}

/**
 * Custom hook for a creator's recent per-stream metric series (ascending by start).
 * @param {string|number} creatorId - The creator ID
 * @param {object} options - Additional query options
 * @returns {object} useQuery result; data = {streams: [{streamId, title, start, durationSec,
 *   msgsPerMin, uniqueChatters, newChatters, returningChatters, messageCount}]}
 */
export const useCreatorTrends = (creatorId, options = {}) => useQuery({
    queryKey: creatorTrendsKeys.detail(creatorId),
    queryFn: async () => {
        const response = await retrieveCreatorTrends(creatorId)
        const data = response.data || {
        }
        const points = data.points || [
        ]
        return {
            streams: points.map(p => ({
                streamId: p.stream_id,
                title: p.title,
                start: p.start,
                durationSec: p.duration_seconds,
                msgsPerMin: p.messages_per_minute,
                uniqueChatters: p.unique_chatters,
                newChatters: p.new_chatters,
                returningChatters: p.returning_chatters,
                messageCount: p.message_count,
            })),
        }
    },
    enabled: Boolean(creatorId), // Only enabled when creatorId is provided
    ...options,
})
