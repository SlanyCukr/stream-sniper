import {
    useInfiniteQuery,
    type InfiniteData,
    type UseInfiniteQueryOptions,
} from '@tanstack/react-query'
import {
    retrieveSearchContext,
    retrieveSearchFirst,
    retrieveSearchFrequency,
    retrieveSearchMessages,
} from '@/lib/api/search'
import { defineGatedQuery, type QueryOptions } from '@/hooks/defineQuery'
import {
    requireArrayField,
    requireBooleanField,
    requireFiniteNumberField,
    requireNullableBooleanField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'
import type {
    SearchContextMessageVM,
    SearchContextVM,
    SearchFirstVM,
    SearchFrequencyPoint,
    SearchHitVM,
} from './searchTypes'
import { searchKeys } from './searchKeys'

/** Minimum trimmed query length the backend accepts before it 422s (mirrors the
 * backend's 3-char floor — pg_trgm needs 3 chars to use the trigram index). */
export const MIN_QUERY_LENGTH = 3

export const isSearchableQuery = (q?: string): boolean => typeof q === 'string' && q.trim().length >= MIN_QUERY_LENGTH

const mapSearchHit = (value: unknown, label: string): SearchHitVM => {
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

interface SearchMessagesVM {
    query: string
    hasMore: boolean
    items: SearchHitVM[]
}

export const mapSearchMessages = (value: unknown): SearchMessagesVM => {
    const data = requireRecord(value, 'search messages')
    return {
        query: requireStringField(data, 'query', 'search messages'),
        hasMore: requireBooleanField(data, 'has_more', 'search messages'),
        items: requireArrayField(data, 'items', 'search messages')
            .map((hit, index) => mapSearchHit(hit, `search messages.items[${index}]`)),
    }
}

export const mapSearchFirst = (value: unknown): SearchFirstVM => {
    const data = requireRecord(value, 'search first')
    return {
        query: requireStringField(data, 'query', 'search first'),
        totalMatches: requireFiniteNumberField(data, 'total_matches', 'search first'),
        first: data.first === null ? null : mapSearchHit(data.first, 'search first.first'),
        byCreator: requireArrayField(data, 'by_creator', 'search first')
            .map((hit, index) => mapSearchHit(hit, `search first.by_creator[${index}]`)),
    }
}

interface SearchFrequencyVM {
    query: string
    days: number
    points: SearchFrequencyPoint[]
}

export const mapSearchFrequency = (value: unknown): SearchFrequencyVM => {
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

const mapSearchContext = (value: unknown): SearchContextVM => {
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
        messages: requireArrayField(data, 'messages', 'search context').map((message, index): SearchContextMessageVM => {
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
                    .map((badge, badgeIndex): string => {
                        if (typeof badge !== 'string') {
                            throw new TypeError(`${label}.badges[${badgeIndex}] must be a string`)
                        }
                        return badge
                    }),
            }
        }),
    }
}

interface SearchMessagesFilters {
    q?: string
    creatorId?: number | null
    days?: number | null
    limit?: number
}

type SearchMessagesQueryOptions = Omit<
    UseInfiniteQueryOptions<
        SearchMessagesVM,
        Error,
        InfiniteData<SearchMessagesVM, number>,
        ReturnType<typeof searchKeys.messages>,
        number
    >,
    'queryKey' | 'queryFn' | 'initialPageParam' | 'getNextPageParam'
> & { enabled?: boolean }

export const useSearchMessages = ({
    q = '', creatorId, days, limit = 50,
}: SearchMessagesFilters = {}, options: SearchMessagesQueryOptions = {}) => {
    const enabledQuery = isSearchableQuery(q)
    const { enabled = true, ...queryOptions } = options
    return useInfiniteQuery({
        ...queryOptions,
        queryKey: searchKeys.messages({
            q: q.trim(), creatorId: creatorId ?? null, days: days ?? null, limit,
        }),
        queryFn: async ({ pageParam }) => mapSearchMessages(await retrieveSearchMessages({
            q: q.trim(),
            creatorId: creatorId ?? undefined,
            days: days ?? undefined,
            limit,
            offset: pageParam,
        })),
        initialPageParam: 0,
        getNextPageParam: (lastPage, _pages, lastPageParam) => (
            lastPage.hasMore ? lastPageParam + limit : undefined
        ),
        enabled: enabledQuery && enabled,
    })
}

interface SearchFirstFilters {
    q?: string
    creatorId?: number | null
}

const searchFirstQuery = defineGatedQuery({
    label: 'search first',
    key: ({ q, creatorId }: Required<SearchFirstFilters>) => (
        searchKeys.first({ q: q.trim(), creatorId: creatorId ?? null })
    ),
    validate: args => (isSearchableQuery(args.q) ? args : null),
    fetch: ({ q, creatorId }) => retrieveSearchFirst({
        q: q.trim(),
        creatorId: creatorId ?? undefined,
    }),
    map: mapSearchFirst,
})

export const useSearchFirst = (
    { q = '', creatorId = null }: SearchFirstFilters = {},
    options: QueryOptions<SearchFirstVM> = {},
) => searchFirstQuery({ q, creatorId }, options)

interface SearchFrequencyFilters {
    q?: string
    days?: number | null
    creatorId?: number | null
}

const searchFrequencyQuery = defineGatedQuery({
    label: 'search frequency',
    key: ({ q, days, creatorId }: Required<SearchFrequencyFilters>) => (
        searchKeys.frequency({ q: q.trim(), days: days ?? null, creatorId: creatorId ?? null })
    ),
    validate: args => (isSearchableQuery(args.q) ? args : null),
    fetch: ({ q, days, creatorId }) => retrieveSearchFrequency({
        q: q.trim(),
        days: days ?? undefined,
        creatorId: creatorId ?? undefined,
    }),
    map: mapSearchFrequency,
})

export const useSearchFrequency = (
    { q = '', days = null, creatorId = null }: SearchFrequencyFilters = {},
    options: QueryOptions<SearchFrequencyVM> = {},
) => searchFrequencyQuery({ q, days, creatorId }, options)

interface SearchContextFilters {
    streamId?: number | null
    messageId?: number | null
    radius?: number
}

interface ValidSearchContextArgs {
    streamId: number
    messageId: number
    radius?: number
}

const searchContextQuery = defineGatedQuery({
    label: 'search context',
    key: ({ streamId, messageId, radius }: SearchContextFilters) => searchKeys.context({
        streamId: streamId ?? null, messageId: messageId ?? null, radius: radius ?? null,
    }),
    validate: ({ streamId, messageId, radius }: SearchContextFilters): ValidSearchContextArgs | null => (
        streamId !== undefined && streamId !== null && streamId > 0
            && messageId !== undefined && messageId !== null && messageId > 0
            ? { streamId, messageId, radius }
            : null
    ),
    fetch: ({ streamId, messageId, radius }) => retrieveSearchContext({ streamId, messageId, radius }),
    map: mapSearchContext,
})

export const useSearchContext = (
    filters: SearchContextFilters = {},
    options: QueryOptions<SearchContextVM> = {},
) => searchContextQuery(filters, options)
