import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
import { retrieveCreatorWrapped } from '@/lib/api/creators'
import {
    requireArrayField,
    requireFiniteNumberField,
    requireNullableFiniteNumberField,
    requireNullableStringField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'

/** One creator's totals for the recap window. */
interface CreatorWrappedTotals {
    streams: number
    /** Total streamed hours, or null when uptime is unknown for the window. */
    hoursStreamed: number | null
    messages: number
    activeChatters: number
}

/** One ranked chatter in the recap. */
interface CreatorWrappedChatter {
    rank: number
    chatterId: number
    nick: string
    totalMessages: number
    streamsAttended: number
}

/** One peak chat moment in the recap. */
interface CreatorWrappedMoment {
    streamId: number
    streamTitle: string
    twitchId: string | null
    bucketMinute: string
    offsetSeconds: number
    /** Chat-hype multiplier vs. the stream baseline, or null when unavailable. */
    ratio: number | null
    messageCount: number
}

/** One trending copypasta in the recap. */
interface CreatorWrappedCopypasta {
    messageTextId: number
    text: string
    usageCount: number
    streamCount: number
}

/** One trending emote in the recap. */
interface CreatorWrappedEmote {
    emoteId: number
    name: string
    source: string
    usage: number
    chatterReach: number
}

/** Camel-cased view model for `GET /creators/{creatorId}/wrapped`. */
export interface CreatorWrapped {
    creatorId: number
    days: number
    totals: CreatorWrappedTotals
    topChatters: CreatorWrappedChatter[]
    topMoments: CreatorWrappedMoment[]
    topCopypastas: CreatorWrappedCopypasta[]
    topEmotes: CreatorWrappedEmote[]
}

const mapTotals = (raw: unknown): CreatorWrappedTotals => {
    const label = 'creator wrapped.totals'
    const totals = requireRecord(raw, label)
    return {
        streams: requireFiniteNumberField(totals, 'streams', label),
        hoursStreamed: requireNullableFiniteNumberField(totals, 'hours_streamed', label),
        messages: requireFiniteNumberField(totals, 'messages', label),
        activeChatters: requireFiniteNumberField(totals, 'active_chatters', label),
    }
}

/** Validate the wrapped envelope at the boundary, then project the view model. */
const mapCreatorWrapped = (value: unknown): CreatorWrapped => {
    const root = requireRecord(value, 'creator wrapped')
    return {
        creatorId: requireFiniteNumberField(root, 'creator_id', 'creator wrapped'),
        days: requireFiniteNumberField(root, 'days', 'creator wrapped'),
        totals: mapTotals(root.totals),
        topChatters: requireArrayField(root, 'top_chatters', 'creator wrapped').map((raw, index) => {
            const label = `creator wrapped.top_chatters[${index}]`
            const row = requireRecord(raw, label)
            return {
                rank: requireFiniteNumberField(row, 'rank', label),
                chatterId: requireFiniteNumberField(row, 'chatter_id', label),
                nick: requireStringField(row, 'nick', label),
                totalMessages: requireFiniteNumberField(row, 'total_messages', label),
                streamsAttended: requireFiniteNumberField(row, 'streams_attended', label),
            }
        }),
        topMoments: requireArrayField(root, 'top_moments', 'creator wrapped').map((raw, index) => {
            const label = `creator wrapped.top_moments[${index}]`
            const row = requireRecord(raw, label)
            return {
                streamId: requireFiniteNumberField(row, 'stream_id', label),
                streamTitle: requireStringField(row, 'stream_title', label),
                twitchId: requireNullableStringField(row, 'twitch_id', label),
                bucketMinute: requireStringField(row, 'bucket_minute', label),
                offsetSeconds: requireFiniteNumberField(row, 'offset_seconds', label),
                ratio: requireNullableFiniteNumberField(row, 'ratio', label),
                messageCount: requireFiniteNumberField(row, 'message_count', label),
            }
        }),
        topCopypastas: requireArrayField(root, 'top_copypastas', 'creator wrapped').map((raw, index) => {
            const label = `creator wrapped.top_copypastas[${index}]`
            const row = requireRecord(raw, label)
            return {
                messageTextId: requireFiniteNumberField(row, 'message_text_id', label),
                text: requireStringField(row, 'text', label),
                usageCount: requireFiniteNumberField(row, 'usage_count', label),
                streamCount: requireFiniteNumberField(row, 'stream_count', label),
            }
        }),
        topEmotes: requireArrayField(root, 'top_emotes', 'creator wrapped').map((raw, index) => {
            const label = `creator wrapped.top_emotes[${index}]`
            const row = requireRecord(raw, label)
            return {
                emoteId: requireFiniteNumberField(row, 'emote_id', label),
                name: requireStringField(row, 'name', label),
                source: requireStringField(row, 'source', label),
                usage: requireFiniteNumberField(row, 'usage', label),
                chatterReach: requireFiniteNumberField(row, 'chatter_reach', label),
            }
        }),
    }
}

/**
 * A recap is "empty" only when every ranked list is empty. Totals can still be
 * zero-valued; the all-empty case is what the view collapses to one EmptyState.
 */
export const isCreatorWrappedEmpty = (wrapped: CreatorWrapped): boolean => (
    wrapped.topChatters.length === 0
    && wrapped.topMoments.length === 0
    && wrapped.topCopypastas.length === 0
    && wrapped.topEmotes.length === 0
)

export const creatorWrappedKeys = {
    all: ['creator-wrapped'] as const,
    detail: (creatorId: number, days: number) => [...creatorWrappedKeys.all, { creatorId, days }] as const,
}

type CreatorWrappedQueryOptions = Omit<
    UseQueryOptions<CreatorWrapped, Error, CreatorWrapped, readonly unknown[]>,
    'queryKey' | 'queryFn'
> & { enabled?: boolean }

/** Fetch one creator's recap for a rolling window (default 30 days). */
export const useCreatorWrapped = (
    creatorId: number,
    days = 30,
    { enabled = true, ...options }: CreatorWrappedQueryOptions = {},
) => useQuery({
    ...options,
    queryKey: creatorWrappedKeys.detail(creatorId, days),
    queryFn: async () => mapCreatorWrapped((await retrieveCreatorWrapped(creatorId, days)).data),
    // Positive safe integer, not just truthy: the route boundary already 404s
    // invalid segments, but a fractional/NaN id reaching here must never fire
    // a request that can only produce a misleading generic API error.
    enabled: Number.isSafeInteger(creatorId) && creatorId > 0 && enabled,
})
