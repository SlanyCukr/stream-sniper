import { useInfiniteQuery, type UseInfiniteQueryOptions, type InfiniteData } from '@tanstack/react-query'
import { retrieveStreamMessages } from '@/lib/api/streams'
import { REPLAY_PAGE_SIZE } from '@/lib/stream/config'
import {
    requireArrayField,
    requireBooleanField,
    requireFiniteNumberField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'

export interface StreamMessage {
    id: number
    ts: string
    chatterId: number
    nick: string
    text: string
    isSubscriber: boolean
    badges: unknown[]
}

export interface StreamMessagesCursor {
    afterTs: string
    afterId: number
}

export interface StreamMessagesPage {
    messages: StreamMessage[]
    nextCursor: StreamMessagesCursor | null
    hasMore: boolean
}

interface StreamMessagesFilters {
    chatterId?: number
    q?: string
    subOnly?: boolean
}

type QueryOptions = Omit<
    UseInfiniteQueryOptions<
        StreamMessagesPage,
        Error,
        InfiniteData<StreamMessagesPage, StreamMessagesCursor | undefined>,
        readonly unknown[],
        StreamMessagesCursor | undefined
    >,
    'queryKey' | 'queryFn' | 'initialPageParam' | 'getNextPageParam'
>

/**
 * Query key factory for the chronological stream chat-replay queries
 */
const streamMessagesKeys = {
    all: [
        'stream-messages',
    ],
    lists: () => [
        ...streamMessagesKeys.all,
        'list',
    ],
    list: (streamId: number, filters: StreamMessagesFilters) => [
        ...streamMessagesKeys.lists(),
        {
            streamId,
            ...filters,
        },
    ],
}

export const mapStreamMessagesPage = (value: unknown): StreamMessagesPage => {
    const data = requireRecord(value, 'stream messages')
    const nextCursor = data.next_cursor === null
        ? null
        : (() => {
            const cursor = requireRecord(data.next_cursor, 'stream messages.next_cursor')
            return {
                afterTs: requireStringField(cursor, 'after_ts', 'stream messages.next_cursor'),
                afterId: requireFiniteNumberField(cursor, 'after_id', 'stream messages.next_cursor'),
            }
        })()
    return {
        messages: requireArrayField(data, 'messages', 'stream messages').map((value, index) => {
            const label = `stream messages.messages[${index}]`
            const message = requireRecord(value, label)
            return {
                id: requireFiniteNumberField(message, 'id', label),
                ts: requireStringField(message, 'time', label),
                chatterId: requireFiniteNumberField(message, 'chatter_id', label),
                nick: requireStringField(message, 'nick', label),
                text: requireStringField(message, 'text', label),
                isSubscriber: requireBooleanField(message, 'is_subscriber', label),
                badges: requireArrayField(message, 'badges', label),
            }
        }),
        nextCursor,
        hasMore: requireBooleanField(data, 'has_more', 'stream messages'),
    }
}

/**
 * Custom hook for the full chronological chat replay of a stream (keyset pagination).
 * @param streamId - The normalized stream ID
 * @param filters - Optional filters
 * @param options - Additional query options
 * @returns useInfiniteQuery result; each page is
 *   {messages: [{id, ts, chatterId, nick, text, isSubscriber, badges}], nextCursor, hasMore}
 */
export const useStreamMessages = (
    streamId: number,
    { chatterId, q, subOnly }: StreamMessagesFilters = {},
    { enabled = true, ...options }: QueryOptions & { enabled?: boolean } = {},
) => useInfiniteQuery({
    ...options,
    queryKey: streamMessagesKeys.list(streamId, {
        chatterId,
        q,
        subOnly,
    }),
    queryFn: async ({ pageParam }) => {
        const response = await retrieveStreamMessages(streamId, {
            chatterId,
            q,
            subOnly,
            afterTs: pageParam?.afterTs,
            afterId: pageParam?.afterId,
            limit: REPLAY_PAGE_SIZE,
        })
        return mapStreamMessagesPage(response)
    },
    initialPageParam: undefined,
    getNextPageParam: last => (last.nextCursor
        ? last.nextCursor
        : undefined),
    enabled: Boolean(streamId) && enabled,
})
