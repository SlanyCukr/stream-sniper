import { useQuery } from '@tanstack/react-query'
import {
    retrieveMessages,
    retrieveChatterOnStreamMessages,
} from '@/lib/api'
import { PAGINATION } from '@/constants'

/**
 * Query key factory for messages-related queries
 */
export const messagesKeys = {
    all: [
        'messages',
    ],
    lists: () => [
        ...messagesKeys.all,
        'list',
    ],
    list: (chatterId, offset) => [
        ...messagesKeys.lists(),
        {
            chatterId,
            offset,
        },
    ],
    streamMessages: () => [
        ...messagesKeys.all,
        'stream-messages',
    ],
    streamMessage: (streamId, chatterId) => [
        ...messagesKeys.streamMessages(),
        {
            streamId,
            chatterId,
        },
    ],
}

/**
 * Custom hook for fetching a page of a chatter's cross-stream message log using TanStack Query
 * @param {string|number} chatterId - The chatter ID
 * @param {number} offset - Page index (0-based); converted to a row offset for the API
 * @param {object} options - Additional query options
 * @returns {object} useQuery result with data ({messages, total}), isLoading, error, etc.
 */
export const useMessages = (chatterId, offset = 0, options = {}) => useQuery({
    queryKey: messagesKeys.list(chatterId, offset),
    queryFn: async () => {
        const response = await retrieveMessages(
            chatterId,
            offset * PAGINATION.MESSAGES_PER_PAGE,
            PAGINATION.MESSAGES_PER_PAGE,
        )
        return response.data || {
            messages: [
            ],
            total: 0,
        }
    },
    enabled: Boolean(chatterId), // Only enabled when chatterId is provided
    ...options,
})

/**
 * Custom hook for fetching messages from a specific chatter in a specific stream using TanStack Query
 * @param {string|number} streamId - The stream ID
 * @param {string|number} chatterId - The chatter ID
 * @param {object} options - Additional query options
 * @returns {object} useQuery result with data, isLoading, error, etc.
 */
export const useChatterStreamMessages = (streamId, chatterId, options = {}) => useQuery({
    queryKey: messagesKeys.streamMessage(streamId, chatterId),
    queryFn: async () => {
        const response = await retrieveChatterOnStreamMessages(streamId, chatterId)
        return response.data || [
        ]
    },
    enabled: Boolean(streamId) && Boolean(chatterId), // Only enabled when both IDs are provided
    ...options,
})
