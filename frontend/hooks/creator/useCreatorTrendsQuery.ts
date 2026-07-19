import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
import { retrieveCreatorTrends } from '@/lib/api/creators'
import {
    requireArrayField,
    requireFiniteNumberField,
    requireNullableFiniteNumberField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'

export interface CreatorTrendPoint {
    streamId: number
    title: string
    start: string
    durationSec: number | null
    msgsPerMin: number | null
    uniqueChatters: number
    newChatters: number
    returningChatters: number
    messageCount: number
}

export interface CreatorTrends {
    streams: CreatorTrendPoint[]
}

type QueryOptions = Omit<
    UseQueryOptions<CreatorTrends, Error, CreatorTrends, readonly unknown[]>,
    'queryKey' | 'queryFn'
>

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
    detail: (creatorId: number) => [
        ...creatorTrendsKeys.details(),
        creatorId,
    ],
}

const mapCreatorTrends = (value: unknown): CreatorTrends => {
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
 * @param creatorId - The normalized creator ID
 * @param options - Additional query options
 */
export const useCreatorTrends = (
    creatorId: number,
    { enabled = true, ...options }: QueryOptions & { enabled?: boolean } = {},
) => useQuery({
    ...options,
    queryKey: creatorTrendsKeys.detail(creatorId),
    queryFn: async () => {
        const response = await retrieveCreatorTrends(creatorId)
        return mapCreatorTrends(response.data)
    },
    enabled: Boolean(creatorId) && enabled,
})
