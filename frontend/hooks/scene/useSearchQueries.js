import { keepPreviousData, useQuery } from '@tanstack/react-query'
import {
    retrieveSearchContext,
    retrieveSearchFirst,
    retrieveSearchFrequency,
    retrieveSearchMessages,
} from '@/lib/api/search'
import {
    requireArrayField,
    requireBooleanField,
    requireFiniteNumberField,
    requireNullableBooleanField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'
import { sceneKeys } from './sceneKeys'

/** @typedef {Omit<import('@tanstack/react-query').UseQueryOptions<any, Error, any, readonly unknown[]>, 'queryKey'|'queryFn'>} QueryOptions */

/** Minimum trimmed query length the backend accepts before it 422s (mirrors the
 * backend's 3-char floor — pg_trgm needs 3 chars to use the trigram index). */
export const MIN_QUERY_LENGTH = 3

/** @param {string} [q] */
export const isSearchableQuery = q => typeof q === 'string' && q.trim().length >= MIN_QUERY_LENGTH

/** @param {unknown} value @param {string} label */
const mapSearchHit = (value, label) => {
    const item = requireRecord(value, label)
    const chatter = requireRecord(item.chatter, `${label}.chatter`)
    const stream = requireRecord(item.stream, `${label}.stream`)
    const creator = requireRecord(item.creator, `${label}.creator`)
    return {
        messageId: requireFiniteNumberField(item, 'message_id', label),
        time: requireStringField(item, 'time', label),
        text: requireStringField(item, 'text', label),
        chatter: {
            id: requireFiniteNumberField(chatter, 'id', `${label}.chatter`),
            nick: requireStringField(chatter, 'nick', `${label}.chatter`),
            isBot: requireNullableBooleanField(chatter, 'is_bot', `${label}.chatter`),
        },
        stream: {
            id: requireFiniteNumberField(stream, 'id', `${label}.stream`),
            title: requireStringField(stream, 'title', `${label}.stream`),
        },
        creator: {
            id: requireFiniteNumberField(creator, 'id', `${label}.creator`),
            nick: requireStringField(creator, 'nick', `${label}.creator`),
            displayName: requireStringField(creator, 'display_name', `${label}.creator`),
        },
    }
}

/** @param {unknown} value */
export const mapSearchMessages = value => {
    const data = requireRecord(value, 'search messages')
    return {
        query: requireStringField(data, 'query', 'search messages'),
        hasMore: requireBooleanField(data, 'has_more', 'search messages'),
        items: requireArrayField(data, 'items', 'search messages')
            .map((hit, index) => mapSearchHit(hit, `search messages.items[${index}]`)),
    }
}

/** @param {unknown} value */
export const mapSearchFirst = value => {
    const data = requireRecord(value, 'search first')
    return {
        query: requireStringField(data, 'query', 'search first'),
        totalMatches: requireFiniteNumberField(data, 'total_matches', 'search first'),
        first: data.first === null ? null : mapSearchHit(data.first, 'search first.first'),
        byCreator: requireArrayField(data, 'by_creator', 'search first')
            .map((hit, index) => mapSearchHit(hit, `search first.by_creator[${index}]`)),
    }
}

/** @param {unknown} value */
export const mapSearchFrequency = value => {
    const data = requireRecord(value, 'search frequency')
    return {
        query: requireStringField(data, 'query', 'search frequency'),
        days: requireFiniteNumberField(data, 'days', 'search frequency'),
        points: requireArrayField(data, 'points', 'search frequency').map((point, index) => {
            const label = `search frequency.points[${index}]`
            const row = requireRecord(point, label)
            return {
                date: requireStringField(row, 'date', label),
                count: requireFiniteNumberField(row, 'count', label),
            }
        }),
    }
}

/** @param {unknown} value */
const mapSearchContext = value => {
    const data = requireRecord(value, 'search context')
    const stream = requireRecord(data.stream, 'search context.stream')
    const creator = requireRecord(stream.creator, 'search context.stream.creator')
    return {
        stream: {
            id: requireFiniteNumberField(stream, 'id', 'search context.stream'),
            title: requireStringField(stream, 'title', 'search context.stream'),
            creator: {
                id: requireFiniteNumberField(creator, 'id', 'search context.stream.creator'),
                nick: requireStringField(creator, 'nick', 'search context.stream.creator'),
                displayName: requireStringField(creator, 'display_name', 'search context.stream.creator'),
            },
        },
        hitIndex: requireFiniteNumberField(data, 'hit_index', 'search context'),
        messages: requireArrayField(data, 'messages', 'search context').map((message, index) => {
            const label = `search context.messages[${index}]`
            const row = requireRecord(message, label)
            return {
                id: requireFiniteNumberField(row, 'id', label),
                time: requireStringField(row, 'time', label),
                chatterId: requireFiniteNumberField(row, 'chatter_id', label),
                nick: requireStringField(row, 'nick', label),
                text: requireStringField(row, 'text', label),
                isSubscriber: requireBooleanField(row, 'is_subscriber', label),
                badges: requireArrayField(row, 'badges', label)
                    .map((badge, badgeIndex) => {
                        if (typeof badge !== 'string') {
                            throw new TypeError(`${label}.badges[${badgeIndex}] must be a string`)
                        }
                        return badge
                    }),
            }
        }),
    }
}

/**
 * @param {{q?:string, creatorId?:number|null, days?:number|null, limit?:number, offset?:number}} [filters]
 * @param {QueryOptions} [options]
 */
export const useSearchMessages = ({
    q = '', creatorId, days, limit = 50, offset = 0,
} = {}, options = {}) => {
    const enabledQuery = isSearchableQuery(q)
    return useQuery({
        placeholderData: keepPreviousData,
        ...options,
        queryKey: sceneKeys.searchMessages({
            q: q.trim(), creatorId: creatorId ?? null, days: days ?? null, limit, offset,
        }),
        queryFn: async () => mapSearchMessages((await retrieveSearchMessages({
            q: q.trim(),
            creatorId: creatorId ?? undefined,
            days: days ?? undefined,
            limit,
            offset,
        })).data),
        enabled: enabledQuery && (options.enabled ?? true),
    })
}

/**
 * @param {{q?:string, creatorId?:number|null}} [filters]
 * @param {QueryOptions} [options]
 */
export const useSearchFirst = ({ q = '', creatorId } = {}, options = {}) => {
    const enabledQuery = isSearchableQuery(q)
    return useQuery({
        ...options,
        queryKey: sceneKeys.searchFirst({ q: q.trim(), creatorId: creatorId ?? null }),
        queryFn: async () => mapSearchFirst((await retrieveSearchFirst({
            q: q.trim(),
            creatorId: creatorId ?? undefined,
        })).data),
        enabled: enabledQuery && (options.enabled ?? true),
    })
}

/**
 * @param {{q?:string, days?:number|null, creatorId?:number|null}} [filters]
 * @param {QueryOptions} [options]
 */
export const useSearchFrequency = ({ q = '', days, creatorId } = {}, options = {}) => {
    const enabledQuery = isSearchableQuery(q)
    return useQuery({
        ...options,
        queryKey: sceneKeys.searchFrequency({
            q: q.trim(), days: days ?? null, creatorId: creatorId ?? null,
        }),
        queryFn: async () => mapSearchFrequency((await retrieveSearchFrequency({
            q: q.trim(),
            days: days ?? undefined,
            creatorId: creatorId ?? undefined,
        })).data),
        enabled: enabledQuery && (options.enabled ?? true),
    })
}

/**
 * @param {{streamId?:number|null, messageId?:number|null, radius?:number}} [params]
 * @param {QueryOptions} [options]
 */
export const useSearchContext = ({
    streamId, messageId, radius,
} = {}, options = {}) => {
    const enabledQuery = Boolean(streamId) && Boolean(messageId)
    return useQuery({
        ...options,
        queryKey: sceneKeys.searchContext({ streamId: streamId ?? null, messageId: messageId ?? null, radius: radius ?? null }),
        queryFn: async () => mapSearchContext((await retrieveSearchContext({
            streamId: /** @type {number} */ (streamId),
            messageId: /** @type {number} */ (messageId),
            radius,
        })).data),
        enabled: enabledQuery && (options.enabled ?? true),
    })
}
