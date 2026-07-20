import { keepPreviousData, useQuery, type UseQueryOptions } from '@tanstack/react-query'
import {
    retrieveSceneHighlights,
    type HighlightsSort,
    type HighlightsWindow,
} from '@/lib/api/scene'
import {
    requireArray,
    requireArrayField,
    requireBooleanField,
    requireFiniteNumberField,
    requireNullableFiniteNumberField,
    requireNullableStringField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'
import { sceneKeys } from './sceneKeys'

interface HighlightPhrase {
    phrase: string
    count: number
    lift: number
}

interface HighlightSample {
    text: string
    count: number
}

export interface SceneHighlight {
    streamId: number
    streamTitle: string
    twitchId: string | null
    creatorId: number
    creatorNick: string
    creatorDisplayName: string
    bucketMinute: string
    offsetSeconds: number
    ratio: number | null
    messageCount: number
    uniqueChatters: number
    subShare: number | null
    emoteShare: number | null
    topPhrases: HighlightPhrase[] | null
    sampleMessages: HighlightSample[] | null
    clipUrl: string | null
    reviewStatus: string | null
}

interface SceneHighlights {
    window: string
    sort: string
    hasMore: boolean
    items: SceneHighlight[]
}

/**
 * A nullable list stays null (unknown) rather than collapsing to `[]`, so the
 * card can distinguish "no phrases surfaced" from "phrase extraction absent".
 */
const mapPhrases = (raw: unknown, label: string): HighlightPhrase[] | null => {
    if (raw === null) return null
    return requireArray(raw, label).map((value, index) => {
        const rowLabel = `${label}[${index}]`
        const row = requireRecord(value, rowLabel)
        return {
            phrase: requireStringField(row, 'phrase', rowLabel),
            count: requireFiniteNumberField(row, 'count', rowLabel),
            lift: requireFiniteNumberField(row, 'lift', rowLabel),
        }
    })
}

const mapSamples = (raw: unknown, label: string): HighlightSample[] | null => {
    if (raw === null) return null
    return requireArray(raw, label).map((value, index) => {
        const rowLabel = `${label}[${index}]`
        const row = requireRecord(value, rowLabel)
        return {
            text: requireStringField(row, 'text', rowLabel),
            count: requireFiniteNumberField(row, 'count', rowLabel),
        }
    })
}

const mapHighlight = (value: unknown, label: string): SceneHighlight => {
    const item = requireRecord(value, label)
    return {
        streamId: requireFiniteNumberField(item, 'stream_id', label),
        streamTitle: requireStringField(item, 'stream_title', label),
        twitchId: requireNullableStringField(item, 'twitch_id', label),
        creatorId: requireFiniteNumberField(item, 'creator_id', label),
        creatorNick: requireStringField(item, 'creator_nick', label),
        creatorDisplayName: requireStringField(item, 'creator_display_name', label),
        bucketMinute: requireStringField(item, 'bucket_minute', label),
        offsetSeconds: requireFiniteNumberField(item, 'offset_seconds', label),
        // Nullable = unknown: never coalesce a missing ratio/share to 0.
        ratio: requireNullableFiniteNumberField(item, 'ratio', label),
        messageCount: requireFiniteNumberField(item, 'message_count', label),
        uniqueChatters: requireFiniteNumberField(item, 'unique_chatters', label),
        subShare: requireNullableFiniteNumberField(item, 'sub_share', label),
        emoteShare: requireNullableFiniteNumberField(item, 'emote_share', label),
        topPhrases: mapPhrases(item.top_phrases, `${label}.top_phrases`),
        sampleMessages: mapSamples(item.sample_messages, `${label}.sample_messages`),
        clipUrl: requireNullableStringField(item, 'clip_url', label),
        reviewStatus: requireNullableStringField(item, 'review_status', label),
    }
}

/** Validate the highlights envelope at the API boundary before projecting a view model. */
export const mapSceneHighlights = (value: unknown): SceneHighlights => {
    const data = requireRecord(value, 'scene highlights')
    return {
        window: requireStringField(data, 'window', 'scene highlights'),
        sort: requireStringField(data, 'sort', 'scene highlights'),
        hasMore: requireBooleanField(data, 'has_more', 'scene highlights'),
        items: requireArrayField(data, 'items', 'scene highlights')
            .map((item, index) => mapHighlight(item, `scene highlights.items[${index}]`)),
    }
}

interface SceneHighlightsFilters {
    window?: HighlightsWindow
    creatorId?: number | null
    sort?: HighlightsSort
    limit?: number
    offset?: number
}

type HighlightsQueryOptions = Omit<
    UseQueryOptions<SceneHighlights, Error, SceneHighlights, ReturnType<typeof sceneKeys.highlights>>,
    'queryKey' | 'queryFn'
>

/**
 * Hype-ranked scene highlights, keyed by the full filter tuple so each
 * window/sort/offset page caches independently. `keepPreviousData` keeps the
 * prior page visible while a "Load more" fetch is in flight.
 */
export const useSceneHighlights = (
    {
        window = 'all',
        creatorId = null,
        sort = 'hype',
        limit = 24,
        offset = 0,
    }: SceneHighlightsFilters = {},
    options: HighlightsQueryOptions = {},
) => useQuery({
    placeholderData: keepPreviousData,
    ...options,
    queryKey: sceneKeys.highlights({ window, creatorId, sort, limit, offset }),
    queryFn: async () => mapSceneHighlights(await retrieveSceneHighlights({
        window,
        creatorId: creatorId ?? undefined,
        sort,
        limit,
        offset,
    })),
})
