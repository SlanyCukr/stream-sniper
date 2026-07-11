import { useInfiniteQuery } from '@tanstack/react-query'
import { retrieveStreamMessages } from '@/lib/api'
import { REPLAY_PAGE_SIZE } from '@/constants'

/**
 * Query key factory for the chronological stream chat-replay queries
 */
export const streamMessagesKeys = {
    all: [
        'stream-messages',
    ],
    lists: () => [
        ...streamMessagesKeys.all,
        'list',
    ],
    list: (streamId, filters) => [
        ...streamMessagesKeys.lists(),
        {
            streamId,
            ...filters,
        },
    ],
}

/**
 * Custom hook for the full chronological chat replay of a stream (keyset pagination).
 * @param {string|number} streamId - The stream ID
 * @param {object} filters - Optional filters
 * @param {number} [filters.chatterId] - Restrict to a single chatter
 * @param {string} [filters.q] - Case-insensitive substring filter on message text
 * @param {object} options - Additional query options
 * @returns {object} useInfiniteQuery result; each page is
 *   {messages: [{id, ts, chatterId, nick, text}], next_cursor, has_more}
 */
export const useStreamMessages = (streamId, { chatterId, q } = {}, options = {}) => useInfiniteQuery({
    queryKey: streamMessagesKeys.list(streamId, {
        chatterId,
        q,
    }),
    queryFn: async ({ pageParam }) => {
        const response = await retrieveStreamMessages(streamId, {
            chatterId,
            q,
            afterTs: pageParam?.afterTs,
            afterId: pageParam?.afterId,
            limit: REPLAY_PAGE_SIZE,
        })
        const data = response.data || {
            messages: [
            ],
            next_cursor: null,
            has_more: false,
        }
        return {
            ...data,
            messages: (data.messages || []).map(m => ({
                id: m.id,
                ts: m.time,
                chatterId: m.chatter_id,
                nick: m.nick,
                text: m.text,
            })),
        }
    },
    initialPageParam: undefined,
    getNextPageParam: last => (last.next_cursor
        ? {
            afterTs: last.next_cursor.after_ts,
            afterId: last.next_cursor.after_id,
        }
        : undefined),
    enabled: Boolean(streamId), // Only enabled when streamId is provided
    ...options,
})
