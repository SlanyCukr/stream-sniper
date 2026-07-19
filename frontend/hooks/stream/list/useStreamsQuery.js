import { useQuery } from '@tanstack/react-query'
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

/** @typedef {Omit<import('@tanstack/react-query').UseQueryOptions<any, Error, any, readonly unknown[]>, 'queryKey'|'queryFn'>} QueryOptions */

/**
 * @typedef {object} StreamsParams
 * @property {number} [creatorId]
 * @property {string} [sort]
 * @property {'asc'|'desc'} [dir]
 * @property {string} [title]
 * @property {string} [dateFrom]
 * @property {string} [dateTo]
 * @property {number} [minMessages]
 * @property {number} [pageIndex]
 */

/**
 * @typedef {object} StreamInfo
 * @property {string} title
 * @property {string} start
 * @property {string|null} end
 * @property {string|null} thumbnailUrl
 * @property {number} messageCount
 * @property {string} nick
 * @property {string} displayName
 * @property {string|null} profileImageUrl
 * @property {number} creatorId
 */

/**
 * @typedef {object} RankedChatter
 * @property {number} chatterId
 * @property {string} nick
 * @property {number} count
 */

/**
 * @typedef {object} StreamCreator
 * @property {number} creatorId
 * @property {string} nick
 */

/**
 * @typedef {object} ChatterOption
 * @property {number} value
 * @property {string} label
 */

/**
 * @typedef {object} StreamDetails
 * @property {StreamInfo} info
 * @property {RankedChatter[]} mostActiveChatters
 * @property {RankedChatter[]} mostTaggedChatters
 * @property {StreamCreator[]} otherCreators
 * @property {ChatterOption[]} chatterOptions
 */

/** @param {unknown} value */
export const mapStreamListRow = value => {
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

/** @param {unknown} value @returns {StreamInfo} */
export const mapStreamInfo = value => {
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

/** @param {unknown} value @param {number} index @returns {RankedChatter} */
const mapRankedChatter = (value, index) => {
    const label = `ranked chatter[${index}]`
    const row = requireRecord(value, label)
    return {
        chatterId: requireFiniteNumberField(row, 'chatter_id', label),
        nick: requireStringField(row, 'nick', label),
        count: requireFiniteNumberField(row, 'count', label),
    }
}

/** @param {unknown} value @param {number} index @returns {StreamCreator} */
const mapCreator = (value, index) => {
    const label = `stream creator[${index}]`
    const row = requireRecord(value, label)
    return {
        creatorId: requireFiniteNumberField(row, 'creator_id', label),
        nick: requireStringField(row, 'nick', label),
    }
}

/** @param {unknown} value @param {number} index @returns {ChatterOption} */
const mapChatterOption = (value, index) => {
    const label = `chatter option[${index}]`
    const row = requireRecord(value, label)
    return {
        value: requireFiniteNumberField(row, 'chatter_id', label),
        label: requireStringField(row, 'nick', label),
    }
}

/** @param {unknown} value @returns {StreamDetails} */
export const mapStreamDetails = value => {
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
    list: (/** @type {StreamsParams & {pageSize: number}} */ params) => [
        ...streamsKeys.all,
        'list',
        params,
    ],
    detail: (/** @type {number} */ id) => [
        ...streamsKeys.all,
        'detail',
        id,
    ],
}

/**
 * @param {StreamsParams} params - Filter/sort/pagination params
 * @param {QueryOptions} options - Additional query options
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
 * @param {number} streamId - The normalized stream ID
 * @param {QueryOptions} options - Additional query options
 */
export const useStreamDetails = (streamId, options = {}) => {
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
