import { useQuery } from '@tanstack/react-query'
import { retrieveChatterMessages } from '@/lib/api/chatter'
import { PAGINATION } from '@/lib/pagination/constants'
import {
    createPage, getRowOffset, normalizePagination,
} from '@/lib/pagination/page'
import {
    requireArrayField, requireFiniteNumberField, requireRecord, requireStringField,
} from '@/lib/api/contractGuards'

/** @param {unknown} value */
export const mapChatterMessage = value => {
    const row = requireRecord(value, 'chatter message')
    return {
        streamId: requireFiniteNumberField(row, 'stream_id', 'chatter message'),
        streamTitle: requireStringField(row, 'stream_title', 'chatter message'),
        creatorDisplayName: requireStringField(row, 'creator_display_name', 'chatter message'),
        text: requireStringField(row, 'text', 'chatter message'),
        timestamp: requireStringField(row, 'timestamp', 'chatter message'),
    }
}

/**
 * Query key factory for messages-related queries
 */
const messagesKeys = {
    all: [
        'messages',
    ],
    lists: () => [
        ...messagesKeys.all,
        'list',
    ],
    list: (chatterId, pagination) => [
        ...messagesKeys.lists(),
        {
            chatterId,
            ...pagination,
        },
    ],
}

/**
 * Custom hook for fetching a page of a chatter's cross-stream message log using TanStack Query
 * @param {number} chatterId - The normalized chatter ID
 * @param {{pageIndex?: number, pageSize?: number}} pagination - View pagination
 * @param {object} options - Additional query options
 * @returns {object} useQuery result with data ({items, total, pageIndex, pageSize, pageCount})
 */
export const useMessages = (chatterId, {
    pageIndex = 0,
    pageSize = PAGINATION.MESSAGES_PER_PAGE,
} = {}, { enabled = true, ...options } = {}) => {
    const params = normalizePagination(pageIndex, pageSize)
    return useQuery({
        ...options,
        queryKey: messagesKeys.list(chatterId, params),
        queryFn: async () => {
            const response = await retrieveChatterMessages(chatterId, {
                rowOffset: getRowOffset(params.pageIndex, params.pageSize),
                pageSize: params.pageSize,
            })
            const data = requireRecord(response.data, 'chatter messages')
            const responseOffset = requireFiniteNumberField(data, 'offset', 'chatter messages')
            const responseLimit = requireFiniteNumberField(data, 'limit', 'chatter messages')
            return createPage(
                requireArrayField(data, 'messages', 'chatter messages').map(mapChatterMessage),
                requireFiniteNumberField(data, 'total', 'chatter messages'),
                Math.floor(responseOffset / responseLimit),
                responseLimit,
            )
        },
        enabled: Boolean(chatterId) && enabled,
    })
}
