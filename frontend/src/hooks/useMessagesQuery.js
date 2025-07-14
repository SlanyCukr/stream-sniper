import { useQuery } from '@tanstack/react-query'
import {
    retrieveMessages,
    retrieveChatterOnStreamMessages,
} from '../api_utils'

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
    list: chatterId => [
        ...messagesKeys.lists(),
        { chatterId },
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
 * Custom hook for fetching messages from a specific chatter using TanStack Query
 * @param {string|number} chatterId - The chatter ID
 * @param {object} options - Additional query options
 * @returns {object} useQuery result with data, isLoading, error, etc.
 */
export const useMessages = (chatterId, options = {}) => useQuery({
    queryKey: messagesKeys.list(chatterId),
    queryFn: async () => {
        const response = await retrieveMessages(chatterId)
        return response.data || [
        ]
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

