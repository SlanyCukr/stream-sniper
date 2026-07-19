import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
import {
    retrieveStreams,
    retrieveStreamComprehensive,
} from '@/lib/api/streams'
import { PAGINATION } from '@/lib/pagination/constants'
import {
    createPage, getRowOffset, normalizePagination,
} from '@/lib/pagination/page'
import {
    requireArray, requireArrayField, requireFiniteNumberField, requireNullableStringField,
    requireRecord, requireStringField,
} from '@/lib/api/contractGuards'

type QueryOptions<T> = Omit<
    UseQueryOptions<T, Error, T, readonly unknown[]>,
    'queryKey' | 'queryFn'
>

export interface StreamsParams {
    creatorId?: number
    sort?: string
    dir?: 'asc' | 'desc'
    title?: string
    dateFrom?: string
    dateTo?: string
    minMessages?: number
    pageIndex?: number
}

export interface StreamInfo {
    title: string
    start: string
    end: string | null
    thumbnailUrl: string | null
    messageCount: number
    nick: string
    displayName: string
    profileImageUrl: string | null
    creatorId: number
}

export interface RankedChatter {
    chatterId: number
    nick: string
    count: number
}

export interface StreamCreator {
    creatorId: number
    nick: string
}

export interface ChatterOption {
    value: number
    label: string
}

export interface StreamDetails {
    info: StreamInfo
    mostActiveChatters: RankedChatter[]
    mostTaggedChatters: RankedChatter[]
    otherCreators: StreamCreator[]
    chatterOptions: ChatterOption[]
}

export interface StreamListRow {
    streamId: number
    creatorName: string
    start: string
    end: string | null
    thumbnailUrl: string | null
    messageCount: number
}

export const mapStreamListRow = (value: unknown): StreamListRow => {
    const row = requireRecord(value, 'stream list row')
    return {
        streamId: requireFiniteNumberField(row, 'stream_id', 'stream list row'),
        creatorName: requireStringField(row, 'creator_name', 'stream list row'),
        start: requireStringField(row, 'start', 'stream list row'),
        end: requireNullableStringField(row, 'end', 'stream list row'),
        thumbnailUrl: requireNullableStringField(row, 'thumbnail_url', 'stream list row'),
        messageCount: requireFiniteNumberField(row, 'message_count', 'stream list row'),
    }
}

export const mapStreamInfo = (value: unknown): StreamInfo => {
    const row = requireRecord(value, 'stream detail.info')
    return {
        title: requireStringField(row, 'title', 'stream detail.info'),
        start: requireStringField(row, 'start', 'stream detail.info'),
        end: requireNullableStringField(row, 'end', 'stream detail.info'),
        thumbnailUrl: requireNullableStringField(row, 'thumbnail_url', 'stream detail.info'),
        messageCount: requireFiniteNumberField(row, 'message_count', 'stream detail.info'),
        nick: requireStringField(row, 'creator_nick', 'stream detail.info'),
        displayName: requireStringField(row, 'creator_display_name', 'stream detail.info'),
        profileImageUrl: requireNullableStringField(row, 'profile_image_url', 'stream detail.info'),
        creatorId: requireFiniteNumberField(row, 'creator_id', 'stream detail.info'),
    }
}

const mapRankedChatter = (value: unknown, index: number): RankedChatter => {
    const label = `ranked chatter[${index}]`
    const row = requireRecord(value, label)
    return {
        chatterId: requireFiniteNumberField(row, 'chatter_id', label),
        nick: requireStringField(row, 'nick', label),
        count: requireFiniteNumberField(row, 'count', label),
    }
}

const mapCreator = (value: unknown, index: number): StreamCreator => {
    const label = `stream creator[${index}]`
    const row = requireRecord(value, label)
    return {
        creatorId: requireFiniteNumberField(row, 'creator_id', label),
        nick: requireStringField(row, 'nick', label),
    }
}

const mapChatterOption = (value: unknown, index: number): ChatterOption => {
    const label = `chatter option[${index}]`
    const row = requireRecord(value, label)
    return {
        value: requireFiniteNumberField(row, 'chatter_id', label),
        label: requireStringField(row, 'nick', label),
    }
}

export const mapStreamDetails = (value: unknown): StreamDetails => {
    const data = requireRecord(value, 'stream detail')
    return {
        info: mapStreamInfo(data.info),
        mostActiveChatters: requireArray(data.most_active_chatters, 'stream detail.most_active_chatters')
            .map(mapRankedChatter),
        mostTaggedChatters: requireArray(data.most_tagged_chatters, 'stream detail.most_tagged_chatters')
            .map(mapRankedChatter),
        otherCreators: requireArray(data.other_creators, 'stream detail.other_creators')
            .map(mapCreator),
        chatterOptions: requireArray(data.chatters, 'stream detail.chatters').map(mapChatterOption),
    }
}

const streamsKeys = {
    all: [
        'streams',
    ],
    list: (params: StreamsParams & { pageSize: number }) => [
        ...streamsKeys.all,
        'list',
        params,
    ],
    detail: (id: number) => [
        ...streamsKeys.all,
        'detail',
        id,
    ],
}

/**
 * @param params - Filter/sort/pagination params
 * @param options - Additional query options
 */
export const useStreams = (
    params: StreamsParams = {},
    options: QueryOptions<ReturnType<typeof createPage<StreamListRow>>> & { enabled?: boolean } = {},
) => {
    const {
        creatorId = -1,
        sort = 'start',
        dir = 'desc',
        title,
        dateFrom,
        dateTo,
        minMessages,
        pageIndex = 0,
    } = params
    const { enabled = true, ...queryOptions } = options
    const pagination = normalizePagination(pageIndex, PAGINATION.ITEMS_PER_PAGE)
    return useQuery({
        ...queryOptions,
        queryKey: streamsKeys.list({
            creatorId,
            sort,
            dir,
            title,
            dateFrom,
            dateTo,
            minMessages,
            pageIndex: pagination.pageIndex,
            pageSize: pagination.pageSize,
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
                rowOffset: getRowOffset(pagination.pageIndex, pagination.pageSize),
            })
            const data = requireRecord(response.data, 'stream list')
            const responseOffset = requireFiniteNumberField(data, 'offset', 'stream list')
            const responseLimit = requireFiniteNumberField(data, 'limit', 'stream list')
            return createPage(
                requireArrayField(data, 'streams', 'stream list').map(mapStreamListRow),
                requireFiniteNumberField(data, 'total', 'stream list'),
                Math.floor(responseOffset / responseLimit),
                responseLimit,
            )
        },
        enabled,
    })
}

/**
 * @param streamId - The normalized stream ID
 * @param options - Additional query options
 */
export const useStreamDetails = (
    streamId: number,
    options: QueryOptions<StreamDetails> & { enabled?: boolean } = {},
) => {
    const { enabled = true, ...queryOptions } = options
    return useQuery({
        ...queryOptions,
        queryKey: streamsKeys.detail(streamId),
        queryFn: async () => {
            const response = await retrieveStreamComprehensive(streamId)
            return mapStreamDetails(response.data)
        },
        enabled: Boolean(streamId) && enabled,
    })
}
