import { retrieveChatterMessages } from '@/lib/api/chatter'
import { PAGINATION } from '@/lib/pagination/constants'
import {
    createPage, getRowOffset, normalizePagination,
} from '@/lib/pagination/page'
import {
    requireArrayField, requireFiniteNumberField, requireRecord, requireStringField,
} from '@/lib/api/contractGuards'
import { defineGatedQuery, type QueryOptions } from '@/hooks/defineQuery'

export interface ChatterMessage {
    streamId: number
    streamTitle: string
    creatorDisplayName: string
    text: string
    timestamp: string
}

export const mapChatterMessage = (value: unknown): ChatterMessage => {
    const row = requireRecord(value, 'chatter message')
    return {
        streamId: requireFiniteNumberField(row, 'stream_id', 'chatter message'),
        streamTitle: requireStringField(row, 'stream_title', 'chatter message'),
        creatorDisplayName: requireStringField(row, 'creator_display_name', 'chatter message'),
        text: requireStringField(row, 'text', 'chatter message'),
        timestamp: requireStringField(row, 'timestamp', 'chatter message'),
    }
}

interface MessagesPagination {
    pageIndex: number
    pageSize: number
}

interface Page<T> {
    items: T[]
    total: number
    pageIndex: number
    pageSize: number
    pageCount: number
}

/**
 * Query key factory for messages-related queries
 */
const messagesKeys = {
    all: [
        'messages',
    ] as const,
    lists: () => [
        ...messagesKeys.all,
        'list',
    ] as const,
    list: (chatterId: number, pagination: MessagesPagination) => [
        ...messagesKeys.lists(),
        {
            chatterId,
            ...pagination,
        },
    ] as const,
}

const mapChatterMessagesPage = (value: unknown): Page<ChatterMessage> => {
    const data = requireRecord(value, 'chatter messages')
    const responseOffset = requireFiniteNumberField(data, 'offset', 'chatter messages')
    const responseLimit = requireFiniteNumberField(data, 'limit', 'chatter messages')
    return createPage(
        requireArrayField(data, 'messages', 'chatter messages').map(mapChatterMessage),
        requireFiniteNumberField(data, 'total', 'chatter messages'),
        Math.floor(responseOffset / responseLimit),
        responseLimit,
    )
}

interface ChatterMessagesArgs {
    chatterId: number
    pageIndex: number
    pageSize: number
}

const chatterMessagesQuery = defineGatedQuery({
    label: 'chatter messages',
    key: ({ chatterId, pageIndex, pageSize }: ChatterMessagesArgs) => (
        messagesKeys.list(chatterId, normalizePagination(pageIndex, pageSize))
    ),
    validate: args => (args.chatterId ? args : null),
    fetch: ({ chatterId, pageIndex, pageSize }) => {
        const params = normalizePagination(pageIndex, pageSize)
        return retrieveChatterMessages(chatterId, {
            rowOffset: getRowOffset(params.pageIndex, params.pageSize),
            pageSize: params.pageSize,
        })
    },
    map: mapChatterMessagesPage,
})

/**
 * Custom hook for fetching a page of a chatter's cross-stream message log using TanStack Query
 * @param chatterId - The normalized chatter ID
 * @param pagination - View pagination
 * @param options - Additional query options
 * @returns useQuery result with data ({items, total, pageIndex, pageSize, pageCount})
 */
export const useChatterMessages = (
    chatterId: number,
    {
        pageIndex = 0,
        pageSize = PAGINATION.MESSAGES_PER_PAGE,
    }: { pageIndex?: number, pageSize?: number } = {},
    options: QueryOptions<Page<ChatterMessage>> = {},
) => chatterMessagesQuery({ chatterId, pageIndex, pageSize }, options)
