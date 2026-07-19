import { useQuery } from '@tanstack/react-query'
import { retrieveCreatorTrends } from '@/lib/api/creators'
import {
    requireArrayField,
    requireFiniteNumberField,
    requireNullableFiniteNumberField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'

/** @typedef {Omit<import('@tanstack/react-query').UseQueryOptions<any, Error, any, readonly unknown[]>, 'queryKey'|'queryFn'>} QueryOptions */

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
    detail: (/** @type {number} */ creatorId) => [
        ...creatorTrendsKeys.details(),
        creatorId,
    ],
}

/** @param {unknown} value */
const mapCreatorTrends = value => {
    const data = requireRecord(value, 'creator trends')
    return {
        streams: requireArrayField(data, 'points', 'creator trends').map((value, index) => {
            const label = `creator trends.points[${index}]`
            const point = requireRecord(value, label)
            return {
                streamId: requireFiniteNumberField(point, 'stream_id', label),
                title: requireStringField(point, 'title', label),
                start: requireStringField(point, 'start', label),
                durationSec: requireNullableFiniteNumberField(point, 'duration_seconds', label),
                msgsPerMin: requireNullableFiniteNumberField(point, 'messages_per_minute', label),
                uniqueChatters: requireFiniteNumberField(point, 'unique_chatters', label),
                newChatters: requireFiniteNumberField(point, 'new_chatters', label),
                returningChatters: requireFiniteNumberField(point, 'returning_chatters', label),
                messageCount: requireFiniteNumberField(point, 'message_count', label),
            }
        }),
    }
}

/**
 * Custom hook for a creator's recent per-stream metric series (ascending by start).
 * @param {number} creatorId - The normalized creator ID
 * @param {QueryOptions} [options] - Additional query options
 */
export const useCreatorTrends = (creatorId, { enabled = true, ...options } = {}) => useQuery({
    ...options,
    queryKey: creatorTrendsKeys.detail(creatorId),
    queryFn: async () => {
        const response = await retrieveCreatorTrends(creatorId)
        return mapCreatorTrends(response.data)
    },
    enabled: Boolean(creatorId) && enabled,
})
