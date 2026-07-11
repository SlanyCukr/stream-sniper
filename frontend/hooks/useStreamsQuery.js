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
    list: params => [
        ...streamsKeys.lists(),
        params,
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
 * Custom hook for fetching filtered/sorted paginated streams data using TanStack Query
 * @param {object} params - Filter/sort/pagination params
 * @param {number} [params.creatorId=-1] - Creator ID to filter by (-1 for all)
 * @param {string} [params.sort='start'] - Sort column (start|message_count|duration)
 * @param {('asc'|'desc')} [params.dir='desc'] - Sort direction
 * @param {string} [params.title] - Title substring filter
 * @param {string} [params.dateFrom] - Inclusive start-date filter (YYYY-MM-DD)
 * @param {string} [params.dateTo] - Exclusive end-date filter (YYYY-MM-DD + 1 day)
 * @param {number} [params.minMessages] - Minimum message count
 * @param {number} [params.offset=0] - Page index (multiplied by page size for the row offset)
 * @param {object} options - Additional query options
 * @returns {object} useQuery result with data ({streams, max_offset}), isLoading, error, etc.
 */
export const useStreams = (params = {}, options = {}) => {
    const {
        creatorId = -1,
        sort = 'start',
        dir = 'desc',
        title,
        dateFrom,
        dateTo,
        minMessages,
        offset = 0,
    } = params
    return useQuery({
        queryKey: streamsKeys.list({
            creatorId,
            sort,
            dir,
            title,
            dateFrom,
            dateTo,
            minMessages,
            offset,
        }),
        queryFn: async () => {
            const response = await retrieveStreams({
                creatorId,
                sort,
                dir,
                title,
                dateFrom,
                dateTo,
                minMessages,
                offset: offset * PAGINATION.ITEMS_PER_PAGE,
            })
            return response.data || {
                streams: [
                ],
                max_offset: 0,
            }
        },
        enabled: true, // Always enabled
        ...options,
    })
}

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
