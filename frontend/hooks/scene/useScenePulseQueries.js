import { useQuery } from '@tanstack/react-query'
import { retrieveSceneDigest, retrieveScenePulse } from '@/lib/api/scene'
import {
    requireArrayField,
    requireFiniteNumberField,
    requireNullableFiniteNumberField,
    requireNullableStringField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'
import { sceneKeys } from './sceneKeys'

/** @typedef {Omit<import('@tanstack/react-query').UseQueryOptions<any, Error, any, readonly unknown[]>, 'queryKey'|'queryFn'>} QueryOptions */
/** @typedef {import('@/lib/api/scene').ScenePulseRequest} ScenePulseFilters */

/** @param {unknown} value */
export const mapScenePulse = value => {
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

/** @param {unknown} value */
export const mapSceneDigest = value => {
    const data = requireRecord(value, 'scene digest')
    requireFiniteNumberField(data, 'days', 'scene digest')
    return requireStringField(data, 'markdown', 'scene digest')
}

/** @param {ScenePulseFilters} [filters] @param {QueryOptions} [options] */
export const useScenePulse = (filters = {}, options = {}) => useQuery({
    ...options,
    queryKey: sceneKeys.pulse(filters),
    queryFn: async () => mapScenePulse((await retrieveScenePulse(filters)).data),
})

/** @param {{days?:number}} [params] @param {QueryOptions} [options] */
export const useSceneDigest = ({ days = 7 } = {}, options = {}) => useQuery({
    ...options,
    queryKey: sceneKeys.digest(days),
    queryFn: async () => mapSceneDigest((await retrieveSceneDigest(days)).data),
})
