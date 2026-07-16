import { useQuery } from '@tanstack/react-query'
import { retrieveCopypastaPropagation, retrieveSceneCopypastas } from '@/lib/api/scene'
import { createPage, getRowOffset, normalizePagination } from '@/lib/pagination/page'
import {
    requireArrayField,
    requireFiniteNumberField,
    requireNullableStringField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'
import { sceneKeys } from './sceneKeys'

/** @typedef {Omit<import('@tanstack/react-query').UseQueryOptions<any, Error, any, readonly unknown[]>, 'queryKey'|'queryFn'>} QueryOptions */
/** @typedef {import('@/lib/api/scene').SceneCopypastaRequest & {pageIndex?: number, pageSize?: number}} SceneCopypastaFilters */
/** @typedef {{pageIndex: number, pageSize: number}} Pagination */

/** @param {unknown} value */
export const mapSceneCopypastaPage = value => {
    const data = requireRecord(value, 'scene copypastas')
    const offset = requireFiniteNumberField(data, 'offset', 'scene copypastas')
    const limit = requireFiniteNumberField(data, 'limit', 'scene copypastas')
    const items = requireArrayField(data, 'items', 'scene copypastas').map((value, index) => {
        const label = `scene copypastas.items[${index}]`
        const item = requireRecord(value, label)
        return {
            messageTextId: requireFiniteNumberField(item, 'message_text_id', label),
            text: requireStringField(item, 'text', label),
            usageCount: requireFiniteNumberField(item, 'usage_count', label),
            chatterAppearances: requireFiniteNumberField(item, 'chatter_appearances', label),
            streamCount: requireFiniteNumberField(item, 'stream_count', label),
            creatorCount: requireFiniteNumberField(item, 'creator_count', label),
            firstSeen: requireNullableStringField(item, 'first_seen', label),
            lastStreamStart: requireNullableStringField(item, 'last_stream_start', label),
        }
    })
    return createPage(
        items,
        requireFiniteNumberField(data, 'total', 'scene copypastas'),
        Math.floor(offset / limit),
        limit,
    )
}

/** @param {unknown} value @param {number} index */
export const mapCopypastaOccurrence = (value, index) => {
    const label = `copypasta propagation.occurrences[${index}]`
    const item = requireRecord(value, label)
    return {
        streamId: requireFiniteNumberField(item, 'stream_id', label),
        creatorId: requireFiniteNumberField(item, 'creator_id', label),
        nick: requireStringField(item, 'nick', label),
        displayName: requireStringField(item, 'display_name', label),
        profileImageUrl: requireNullableStringField(item, 'profile_image_url', label),
        streamTitle: requireStringField(item, 'stream_title', label),
        streamStart: requireNullableStringField(item, 'stream_start', label),
        firstSeen: requireNullableStringField(item, 'first_seen', label),
        usageCount: requireFiniteNumberField(item, 'usage_count', label),
        chatterCount: requireFiniteNumberField(item, 'chatter_count', label),
    }
}

/** @param {unknown} value @param {number} index */
export const mapCopypastaOriginMessage = (value, index) => {
    const label = `copypasta propagation.origin_context[${index}]`
    const item = requireRecord(value, label)
    return {
        id: requireFiniteNumberField(item, 'id', label),
        time: requireStringField(item, 'time', label),
        chatterId: requireFiniteNumberField(item, 'chatter_id', label),
        nick: requireStringField(item, 'nick', label),
        text: requireStringField(item, 'text', label),
    }
}

/** @param {unknown} value */
export const mapCopypastaPropagation = value => {
    const data = requireRecord(value, 'copypasta propagation')
    return {
        messageTextId: requireFiniteNumberField(data, 'message_text_id', 'copypasta propagation'),
        text: requireStringField(data, 'text', 'copypasta propagation'),
        usageCount: requireFiniteNumberField(data, 'usage_count', 'copypasta propagation'),
        chatterAppearances: requireFiniteNumberField(data, 'chatter_appearances', 'copypasta propagation'),
        streamCount: requireFiniteNumberField(data, 'stream_count', 'copypasta propagation'),
        creatorCount: requireFiniteNumberField(data, 'creator_count', 'copypasta propagation'),
        firstSeen: requireNullableStringField(data, 'first_seen', 'copypasta propagation'),
        occurrences: requireArrayField(data, 'occurrences', 'copypasta propagation')
            .map(mapCopypastaOccurrence),
        originContext: requireArrayField(data, 'origin_context', 'copypasta propagation')
            .map(mapCopypastaOriginMessage),
    }
}

/** @param {SceneCopypastaFilters} [filters] @param {QueryOptions} [options] */
export const useSceneCopypastas = ({
    days, creatorId, sort, pageIndex = 0, pageSize = 50,
} = {}, options = {}) => {
    const pagination = normalizePagination(pageIndex, pageSize)
    return useQuery({
        ...options,
        queryKey: sceneKeys.copypastas({ days, creatorId, sort, ...pagination }),
        queryFn: async () => {
            const { data } = await retrieveSceneCopypastas({
                days,
                creatorId,
                sort,
                pageSize: pagination.pageSize,
                rowOffset: getRowOffset(pagination.pageIndex, pagination.pageSize),
            })
            return mapSceneCopypastaPage(data)
        },
    })
}

/** @param {number} messageTextId @param {number} [contextSeconds] @param {QueryOptions} [options] */
export const useCopypastaPropagation = (
    messageTextId,
    contextSeconds = 90,
    { enabled = true, ...options } = {},
) => useQuery({
    ...options,
    queryKey: sceneKeys.copypasta(messageTextId, contextSeconds),
    queryFn: async () => mapCopypastaPropagation(
        (await retrieveCopypastaPropagation(messageTextId, contextSeconds)).data,
    ),
    enabled: Boolean(messageTextId) && enabled,
})
