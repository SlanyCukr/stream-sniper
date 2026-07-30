import { retrieveCreatorTrends } from '@/lib/api/creators'
import {
    requireArrayField,
    requireFiniteNumberField,
    requireNullableFiniteNumberField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'
import { defineGatedQuery, type QueryOptions } from '@/hooks/defineQuery'
import { creatorKeys } from './creatorKeys'

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

const creatorTrendsQuery = defineGatedQuery({
    label: 'creator trends',
    key: (creatorId: number) => creatorKeys.trends(creatorId),
    validate: creatorId => (creatorId ? creatorId : null),
    fetch: retrieveCreatorTrends,
    map: mapCreatorTrends,
})

/**
 * Custom hook for a creator's recent per-stream metric series (ascending by start).
 * @param creatorId - The normalized creator ID
 * @param options - Additional query options
 */
export const useCreatorTrends = (
    creatorId: number,
    options: QueryOptions<CreatorTrends> = {},
) => creatorTrendsQuery(creatorId, options)
