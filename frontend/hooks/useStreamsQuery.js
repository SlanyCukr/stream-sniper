import { useQuery } from '@tanstack/react-query'
import {
    retrieveStreams,
    retrieveStreamComprehensive,
} from '@/lib/api'
import { PAGINATION } from '@/constants'

/**
 * Query key factory for streams-related queries
 */
export const streamsKeys = {
    all: [
        'streams',
    ],
    lists: () => [
        ...streamsKeys.all,
        'list',
    ],
    list: (creatorId, offset) => [
        ...streamsKeys.lists(),
        {
            creatorId,
            offset,
        },
    ],
    details: () => [
        ...streamsKeys.all,
        'detail',
    ],
    detail: id => [
        ...streamsKeys.details(),
        id,
    ],
}

/**
 * Custom hook for fetching paginated streams data using TanStack Query
 * @param {number|null} creatorId - The creator ID to filter by (-1 for all)
 * @param {number} offset - The pagination offset
 * @param {object} options - Additional query options
 * @returns {object} useQuery result with data, isLoading, error, etc.
 */
export const useStreams = (creatorId = -1, offset = 0, options = {}) => useQuery({
    queryKey: streamsKeys.list(creatorId, offset),
    queryFn: async () => {
        const response = await retrieveStreams(creatorId, offset * PAGINATION.ITEMS_PER_PAGE)
        return response.data || {
            streams: [
            ],
            max_offset: 0,
        }
    },
    enabled: true, // Always enabled
    ...options,
})

/**
 * Custom hook for fetching comprehensive stream data using TanStack Query
 * @param {string|number} streamId - The stream ID
 * @param {object} options - Additional query options
 * @returns {object} useQuery result with data, isLoading, error, etc.
 */
export const useStreamData = (streamId, options = {}) => useQuery({
    queryKey: streamsKeys.detail(streamId),
    queryFn: async () => {
        const response = await retrieveStreamComprehensive(streamId)
        return response.data
    },
    enabled: Boolean(streamId), // Only enabled when streamId is provided
    ...options,
})
