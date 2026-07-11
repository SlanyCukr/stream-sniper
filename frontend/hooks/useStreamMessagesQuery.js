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
 * @param {boolean} [filters.subOnly] - Restrict to subscriber messages only
 * @param {object} options - Additional query options
 * @returns {object} useInfiniteQuery result; each page is
 *   {messages: [{id, ts, chatterId, nick, text, isSubscriber, badges}], next_cursor, has_more}
 */
export const useStreamMessages = (streamId, { chatterId, q, subOnly } = {}, options = {}) => useInfiniteQuery({
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
                isSubscriber: m.is_subscriber,
                badges: m.badges,
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
