import {
    useMutation, useQuery, useQueryClient,
} from '@tanstack/react-query'
import {
    deleteMomentReview,
    putMomentReview,
    retrieveMomentsQueue,
} from '@/lib/api/moments'
import { streamTimelineKeys } from '../queryKeys'
import {
    createPage, getRowOffset, normalizePagination,
} from '@/lib/pagination/page'
import {
    requireArrayField, requireFiniteNumberField, requireRecord,
} from '@/lib/api/contractGuards'

export const momentsQueueKeys = {
    all: ['moments-queue'],
    list: filters => [...momentsQueueKeys.all, 'list', filters],
}

const mapMoment = m => ({
    streamId: m.stream_id,
    streamTitle: m.title,
    streamStart: m.start,
    twitchVodId: m.twitch_id,
    creatorName: m.creator_display_name,
    t: m.bucket_minute,
    offsetSeconds: m.offset_seconds,
    count: m.message_count,
    baseline: m.baseline,
    score: m.ratio,
    unique: m.unique_chatters,
    subShare: m.sub_share,
    emoteShare: m.emote_share,
    topPhrases: m.top_phrases,
    sampleMessages: m.sample_messages,
    status: m.status,
    clipUrl: m.clip_url ?? null,
    note: m.note ?? null,
})

/** @param {unknown} value */
export const mapMomentsQueue = value => {
    const data = requireRecord(value, 'moments queue')
    const limit = requireFiniteNumberField(data, 'limit', 'moments queue')
    const offset = requireFiniteNumberField(data, 'offset', 'moments queue')
    return createPage(
        requireArrayField(data, 'items', 'moments queue').map(mapMoment),
        requireFiniteNumberField(data, 'total', 'moments queue'),
        Math.floor(offset / Math.max(1, limit)),
        limit,
    )
}

export const useMomentsQueue = ({
    status, creatorId, pageIndex = 0, pageSize = 50,
} = {}, options = {}) => {
    const pagination = normalizePagination(pageIndex, pageSize)
    return useQuery({
        ...options,
        queryKey: momentsQueueKeys.list({
            status, creatorId, ...pagination,
        }),
        queryFn: async () => {
            const response = await retrieveMomentsQueue({
                status,
                creatorId,
                pageSize: pagination.pageSize,
                rowOffset: getRowOffset(pagination.pageIndex, pagination.pageSize),
            })
            return mapMomentsQueue(response.data)
        },
    })
}

/** @typedef {import('@/lib/api/moments').MomentReviewStatus} MomentReviewStatus */
/**
 * @typedef {object} SetMomentReviewCommand
 * @property {'set'} action
 * @property {number} streamId
 * @property {string} bucketMinute
 * @property {MomentReviewStatus} status
 * @property {string | null | undefined} [clipUrl] - null explicitly clears the clip URL
 * @property {string | null | undefined} [note] - null explicitly clears the curator note
 */
/**
 * @typedef {object} ClearMomentReviewCommand
 * @property {'clear'} action
 * @property {number} streamId
 * @property {string} bucketMinute
 */
/** @typedef {SetMomentReviewCommand | ClearMomentReviewCommand} MomentReviewCommand */

/**
 * Admin-only review command. Owned cache invalidation always completes before
 * a caller-provided onSuccess callback runs.
 */
export const useMomentReview = (options = {}) => {
    const queryClient = useQueryClient()
    const {
        onSuccess,
        ...mutationOptions
    } = options

    return useMutation({
        ...mutationOptions,
        mutationFn: async (/** @type {MomentReviewCommand} */ command) => {
            const {
                action, streamId, bucketMinute,
            } = command
            if (action === 'clear') {
                const response = await deleteMomentReview(streamId, bucketMinute)
                return response.data
            }
            if (action !== 'set') {
                throw new TypeError(`Unsupported moment review action: ${action}`)
            }

            const {
                status, clipUrl, note,
            } = command
            const response = await putMomentReview(
                streamId,
                bucketMinute,
                status,
                { clipUrl: clipUrl ?? null, note: note ?? null },
            )
            return response.data
        },
        onSuccess: async (...args) => {
            const command = args[1]
            await Promise.all([
                queryClient.invalidateQueries({ queryKey: momentsQueueKeys.all }),
                queryClient.invalidateQueries({
                    queryKey: streamTimelineKeys.detail(command.streamId),
                }),
            ])
            await onSuccess?.(...args)
        },
    })
}
