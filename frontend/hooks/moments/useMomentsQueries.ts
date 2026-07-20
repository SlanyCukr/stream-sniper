import {
    useMutation, useQuery, useQueryClient,
    type UseMutationOptions, type UseQueryOptions,
} from '@tanstack/react-query'
import {
    deleteMomentReview,
    putMomentReview,
    retrieveMomentsQueue,
    type MomentQueueItemDto,
    type MomentReviewDto,
    type MomentReviewStatus,
    type MomentsQueueRequest,
} from '@/lib/api/moments'
import { streamTimelineKeys } from '../queryKeys'
import {
    createPage, getRowOffset, normalizePagination,
} from '@/lib/pagination/page'
import {
    requireArrayField, requireFiniteNumberField, requireRecord,
} from '@/lib/api/contractGuards'

interface MomentsQueueKeyFilters {
    status?: MomentsQueueRequest['status']
    creatorId?: number
    pageIndex: number
    pageSize: number
}

export const momentsQueueKeys = {
    all: ['moments-queue'] as const,
    list: (filters: MomentsQueueKeyFilters) => [...momentsQueueKeys.all, 'list', filters] as const,
}

export interface MomentQueueItem {
    streamId: number
    streamTitle: string
    streamStart: string
    twitchVodId: string | null
    creatorName: string
    t: string
    offsetSeconds: number
    count: number
    baseline: number
    score: number | null
    unique: number
    subShare: number | null
    emoteShare: number | null
    topPhrases: Array<Record<string, unknown>> | null
    sampleMessages: Array<Record<string, unknown>> | null
    status: MomentReviewStatus | null
    clipUrl: string | null
    note: string | null
}

const mapMoment = (m: MomentQueueItemDto): MomentQueueItem => ({
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

const mapMomentsQueue = (value: unknown) => {
    const data = requireRecord(value, 'moments queue')
    const limit = requireFiniteNumberField(data, 'limit', 'moments queue')
    const offset = requireFiniteNumberField(data, 'offset', 'moments queue')
    // Only the envelope is guarded at the boundary; item fields are trusted
    // from the typed DTO returned by retrieveMomentsQueue (pre-existing
    // behavior — this mapper never validated individual moment fields).
    const items = requireArrayField(data, 'items', 'moments queue') as MomentQueueItemDto[]
    return createPage(
        items.map(mapMoment),
        requireFiniteNumberField(data, 'total', 'moments queue'),
        Math.floor(offset / Math.max(1, limit)),
        limit,
    )
}

type MomentsQueuePage = ReturnType<typeof mapMomentsQueue>

type QueryOptions<T> = Omit<
    UseQueryOptions<T, Error, T, readonly unknown[]>,
    'queryKey' | 'queryFn'
> & { enabled?: boolean }

interface UseMomentsQueueParams {
    status?: MomentsQueueRequest['status']
    creatorId?: number
    pageIndex?: number
    pageSize?: number
}

export const useMomentsQueue = (
    {
        status, creatorId, pageIndex = 0, pageSize = 50,
    }: UseMomentsQueueParams = {},
    options: QueryOptions<MomentsQueuePage> = {},
) => {
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
            return mapMomentsQueue(response)
        },
    })
}

export interface SetMomentReviewCommand {
    action: 'set'
    streamId: number
    bucketMinute: string
    status: MomentReviewStatus
    /** null explicitly clears the clip URL */
    clipUrl?: string | null
    /** null explicitly clears the curator note */
    note?: string | null
}

export interface ClearMomentReviewCommand {
    action: 'clear'
    streamId: number
    bucketMinute: string
}

export type MomentReviewCommand = SetMomentReviewCommand | ClearMomentReviewCommand

type MomentReviewMutationOptions = Omit<
    UseMutationOptions<MomentReviewDto | void, Error, MomentReviewCommand>,
    'mutationFn'
>

/**
 * Admin-only review command. Owned cache invalidation always completes before
 * a caller-provided onSuccess callback runs.
 */
export const useMomentReview = (options: MomentReviewMutationOptions = {}) => {
    const queryClient = useQueryClient()
    const {
        onSuccess,
        ...mutationOptions
    } = options

    return useMutation({
        ...mutationOptions,
        mutationFn: async (command: MomentReviewCommand) => {
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
        onSuccess: async (...args: Parameters<NonNullable<typeof onSuccess>>) => {
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
