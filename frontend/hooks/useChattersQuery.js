import { useQuery } from '@tanstack/react-query'
import {
    retrieveChattersOnStream,
    retrieveAllCreators,
    retrieveChatterId,
    retrieveChatterStreamActivity,
} from '@/lib/api'

/**
 * Query key factory for chatters-related queries
 */
export const chattersKeys = {
    all: [
        'chatters',
    ],
    lists: () => [
        ...chattersKeys.all,
        'list',
    ],
    list: streamId => [
        ...chattersKeys.lists(),
        { streamId },
    ],
    details: () => [
        ...chattersKeys.all,
        'detail',
    ],
    detail: id => [
        ...chattersKeys.details(),
        id,
    ],
    creators: () => [
        'creators',
    ],
    chatterIds: () => [
        ...chattersKeys.all,
        'chatter-ids',
    ],
    chatterId: nick => [
        ...chattersKeys.chatterIds(),
        nick,
    ],
    streamActivities: () => [
        ...chattersKeys.all,
        'stream-activity',
    ],
    streamActivity: chatterId => [
        ...chattersKeys.streamActivities(),
        chatterId,
    ],
}

/**
 * Custom hook for fetching chatters on a specific stream using TanStack Query
 * @param {string|number} streamId - The stream ID
 * @param {object} options - Additional query options
 * @returns {object} useQuery result with data, isLoading, error, etc.
 */
export const useChatters = (streamId, options = {}) => useQuery({
    queryKey: chattersKeys.list(streamId),
    queryFn: async () => {
        const response = await retrieveChattersOnStream(streamId)
        return response.data || [
        ]
    },
    enabled: Boolean(streamId), // Only enabled when streamId is provided
    ...options,
})

/**
 * Custom hook for fetching all creators using TanStack Query
 * @param {object} options - Additional query options
 * @returns {object} useQuery result with data, isLoading, error, etc.
 */
export const useCreators = (options = {}) => useQuery({
    queryKey: chattersKeys.creators(),
    queryFn: async () => {
        const response = await retrieveAllCreators()
        return response.data || [
        ]
    },
    enabled: true, // Always enabled
    staleTime: 1000 * 60 * 10, // 10 minutes - creators don't change often
    ...options,
})

/**
 * Custom hook for fetching chatter ID by nickname using TanStack Query
 * @param {string} nick - The chatter nickname
 * @param {boolean} enabled - Whether to execute the request (default: false)
 * @param {object} options - Additional query options
 * @returns {object} useQuery result with data, isLoading, error, etc.
 */
export const useChatterId = (nick, enabled = false, options = {}) => useQuery({
    queryKey: chattersKeys.chatterId(nick),
    queryFn: async () => {
        const response = await retrieveChatterId(nick)
        return response.data
    },
    enabled: Boolean(nick) && enabled, // Only enabled when nick is provided and enabled is true
    ...options,
})

/**
 * Custom hook for fetching every stream a chatter appears in with their message count
 * @param {string|number} chatterId - The chatter ID
 * @param {object} options - Additional query options
 * @returns {object} useQuery result with data, isLoading, error, etc.
 */
export const useChatterStreamActivity = (chatterId, options = {}) => useQuery({
    queryKey: chattersKeys.streamActivity(chatterId),
    queryFn: async () => {
        const response = await retrieveChatterStreamActivity(chatterId)
        return response.data || [
        ]
    },
    enabled: Boolean(chatterId), // Only enabled when chatterId is provided
    ...options,
})
