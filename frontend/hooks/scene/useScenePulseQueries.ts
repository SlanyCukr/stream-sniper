import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
import { retrieveSceneDigest, retrieveScenePulse, type ScenePulseRequest } from '@/lib/api/scene'
import {
    requireArrayField,
    requireFiniteNumberField,
    requireNullableFiniteNumberField,
    requireNullableStringField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'
import { sceneKeys } from './sceneKeys'

type QueryOptions<T> = Omit<
    UseQueryOptions<T, Error, T, readonly unknown[]>,
    'queryKey' | 'queryFn'
>

export interface ScenePulseEvent {
    id: number
    eventType: string
    occurredAt: string
    creatorId: number | null
    creatorNick: string | null
    creatorDisplayName: string | null
    streamId: number | null
    messageTextId: number | null
    title: string
    summary: string
    metadata: Record<string, unknown>
}

export interface ScenePulse {
    total: number
    days: number
    limit: number
    offset: number
    items: ScenePulseEvent[]
}

export const mapScenePulse = (value: unknown): ScenePulse => {
    const data = requireRecord(value, 'scene pulse')
    return {
        total: requireFiniteNumberField(data, 'total', 'scene pulse'),
        days: requireFiniteNumberField(data, 'days', 'scene pulse'),
        limit: requireFiniteNumberField(data, 'limit', 'scene pulse'),
        offset: requireFiniteNumberField(data, 'offset', 'scene pulse'),
        items: requireArrayField(data, 'items', 'scene pulse').map((value, index) => {
            const label = `scene pulse.items[${index}]`
            const item = requireRecord(value, label)
            return {
                id: requireFiniteNumberField(item, 'id', label),
                eventType: requireStringField(item, 'event_type', label),
                occurredAt: requireStringField(item, 'occurred_at', label),
                creatorId: requireNullableFiniteNumberField(item, 'creator_id', label),
                creatorNick: requireNullableStringField(item, 'creator_nick', label),
                creatorDisplayName: requireNullableStringField(item, 'creator_display_name', label),
                streamId: requireNullableFiniteNumberField(item, 'stream_id', label),
                messageTextId: requireNullableFiniteNumberField(item, 'message_text_id', label),
                title: requireStringField(item, 'title', label),
                summary: requireStringField(item, 'summary', label),
                metadata: requireRecord(item.metadata, `${label}.metadata`),
            }
        }),
    }
}

export const mapSceneDigest = (value: unknown): string => {
    const data = requireRecord(value, 'scene digest')
    requireFiniteNumberField(data, 'days', 'scene digest')
    return requireStringField(data, 'markdown', 'scene digest')
}

export const useScenePulse = (
    filters: ScenePulseRequest = {},
    options: QueryOptions<ScenePulse> = {},
) => useQuery({
    ...options,
    queryKey: sceneKeys.pulse(filters),
    queryFn: async () => mapScenePulse(await retrieveScenePulse(filters)),
})

export const useSceneDigest = (
    { days = 7 }: { days?: number } = {},
    options: QueryOptions<string> = {},
) => useQuery({
    ...options,
    queryKey: sceneKeys.digest(days),
    queryFn: async () => mapSceneDigest(await retrieveSceneDigest(days)),
})
