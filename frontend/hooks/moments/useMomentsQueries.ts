import {
    useMutation, useQuery, useQueryClient,
    type UseMutationOptions, type UseQueryOptions,
} from '@tanstack/react-query'
import {
    deleteMomentReview,
    mapNullableMomentPhrases,
    mapNullableMomentSamples,
    putMomentReview,
    requireNullableMomentReviewStatus,
    retrieveMomentsQueue,
    type MomentReviewDto,
    type MomentPhrase,
    type MomentReviewStatus,
    type MomentSampleMessage,
    type MomentsQueueRequest,
} from '@/lib/api/moments'
import { streamTimelineKeys } from '../queryKeys'
import {
    createPage, getRowOffset, normalizePagination,
} from '@/lib/pagination/page'
import {
    requireArrayField,
    requireFiniteNumberField,
    requireNullableFiniteNumberField,
    requireNullableStringField,
    requireRecord,
    requireStringField,
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
    topPhrases: MomentPhrase[] | null
    sampleMessages: MomentSampleMessage[] | null
    status: MomentReviewStatus | null
    clipUrl: string | null
    note: string | null
}

const mapMoment = (value: unknown, index: number): MomentQueueItem => {
    const label = `moments queue.items[${index}]`
    const moment = requireRecord(value, label)
    return {
        streamId: requireFiniteNumberField(moment, 'stream_id', label),
        streamTitle: requireStringField(moment, 'title', label),
        streamStart: requireStringField(moment, 'start', label),
        twitchVodId: requireNullableStringField(moment, 'twitch_id', label),
        creatorName: requireStringField(moment, 'creator_display_name', label),
        t: requireStringField(moment, 'bucket_minute', label),
        offsetSeconds: requireFiniteNumberField(moment, 'offset_seconds', label),
        count: requireFiniteNumberField(moment, 'message_count', label),
        baseline: requireFiniteNumberField(moment, 'baseline', label),
        score: requireNullableFiniteNumberField(moment, 'ratio', label),
        unique: requireFiniteNumberField(moment, 'unique_chatters', label),
        subShare: requireNullableFiniteNumberField(moment, 'sub_share', label),
        emoteShare: requireNullableFiniteNumberField(moment, 'emote_share', label),
        topPhrases: mapNullableMomentPhrases(moment.top_phrases, `${label}.top_phrases`),
        sampleMessages: mapNullableMomentSamples(moment.sample_messages, `${label}.sample_messages`),
        status: requireNullableMomentReviewStatus(moment.status, `${label}.status`),
        clipUrl: requireNullableStringField(moment, 'clip_url', label),
        note: requireNullableStringField(moment, 'note', label),
    }
}

const mapMomentsQueue = (value: unknown) => {
    const data = requireRecord(value, 'moments queue')
    const limit = requireFiniteNumberField(data, 'limit', 'moments queue')
    const offset = requireFiniteNumberField(data, 'offset', 'moments queue')
    const items = requireArrayField(data, 'items', 'moments queue')
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
