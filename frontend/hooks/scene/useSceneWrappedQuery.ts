import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
import { retrieveSceneWrapped } from '@/lib/api/scene'
import {
    requireArrayField,
    requireFiniteNumberField,
    requireNullableFiniteNumberField,
    requireNullableStringField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'
import { sceneKeys } from './sceneKeys'

/** Scene-wide totals for the recap window. */
export interface WrappedTotals {
    streams: number
    /** Total streamed hours, or null when uptime is unknown for the window. */
    hoursStreamed: number | null
    messages: number
    activeChatters: number
    creatorsActive: number
}

/** One ranked creator in the recap. */
export interface WrappedCreator {
    rank: number
    creatorId: number
    nick: string
    displayName: string
    profileImageUrl: string | null
    totalMessages: number
    streams: number
    hoursStreamed: number | null
    msgsPerMin: number | null
    peakViewers: number | null
}

/** One ranked chatter in the recap. */
export interface WrappedChatter {
    rank: number
    chatterId: number
    nick: string
    totalMessages: number
    streamsAttended: number
    creatorsVisited: number
    homeCreatorDisplayName: string | null
}

/** One peak chat moment in the recap. */
export interface WrappedMoment {
    streamId: number
    streamTitle: string
    twitchId: string | null
    creatorDisplayName: string
    bucketMinute: string
    offsetSeconds: number
    /** Chat-hype multiplier vs. the stream baseline, or null when unavailable. */
    ratio: number | null
    messageCount: number
}

/** One trending copypasta in the recap. */
export interface WrappedCopypasta {
    messageTextId: number
    text: string
    usageCount: number
    creatorCount: number
    streamCount: number
}

/** One trending emote in the recap. */
export interface WrappedEmote {
    emoteId: number
    name: string
    source: string
    usage: number
    chatterReach: number
}

/** One notable scene event in the recap timeline. */
export interface WrappedEvent {
    eventType: string
    occurredAt: string
    title: string
    summary: string
    creatorDisplayName: string | null
}

/** Camel-cased view model for `GET /scene/wrapped`. */
export interface SceneWrapped {
    days: number
    totals: WrappedTotals
    topCreators: WrappedCreator[]
    topChatters: WrappedChatter[]
    topMoments: WrappedMoment[]
    topCopypastas: WrappedCopypasta[]
    topEmotes: WrappedEmote[]
    notableEvents: WrappedEvent[]
}

const mapTotals = (raw: unknown): WrappedTotals => {
    const label = 'scene wrapped.totals'
    const totals = requireRecord(raw, label)
    return {
        streams: requireFiniteNumberField(totals, 'streams', label),
        hoursStreamed: requireNullableFiniteNumberField(totals, 'hours_streamed', label),
        messages: requireFiniteNumberField(totals, 'messages', label),
        activeChatters: requireFiniteNumberField(totals, 'active_chatters', label),
        creatorsActive: requireFiniteNumberField(totals, 'creators_active', label),
    }
}

/** Validate the wrapped envelope at the boundary, then project the view model. */
export const mapSceneWrapped = (value: unknown): SceneWrapped => {
    const root = requireRecord(value, 'scene wrapped')
    return {
        days: requireFiniteNumberField(root, 'days', 'scene wrapped'),
        totals: mapTotals(root.totals),
        topCreators: requireArrayField(root, 'top_creators', 'scene wrapped').map((raw, index) => {
            const label = `scene wrapped.top_creators[${index}]`
            const row = requireRecord(raw, label)
            return {
                rank: requireFiniteNumberField(row, 'rank', label),
                creatorId: requireFiniteNumberField(row, 'creator_id', label),
                nick: requireStringField(row, 'nick', label),
                displayName: requireStringField(row, 'display_name', label),
                profileImageUrl: requireNullableStringField(row, 'profile_image_url', label),
                totalMessages: requireFiniteNumberField(row, 'total_messages', label),
                streams: requireFiniteNumberField(row, 'streams', label),
                hoursStreamed: requireNullableFiniteNumberField(row, 'hours_streamed', label),
                msgsPerMin: requireNullableFiniteNumberField(row, 'msgs_per_min', label),
                peakViewers: requireNullableFiniteNumberField(row, 'peak_viewers', label),
            }
        }),
        topChatters: requireArrayField(root, 'top_chatters', 'scene wrapped').map((raw, index) => {
            const label = `scene wrapped.top_chatters[${index}]`
            const row = requireRecord(raw, label)
            return {
                rank: requireFiniteNumberField(row, 'rank', label),
                chatterId: requireFiniteNumberField(row, 'chatter_id', label),
                nick: requireStringField(row, 'nick', label),
                totalMessages: requireFiniteNumberField(row, 'total_messages', label),
                streamsAttended: requireFiniteNumberField(row, 'streams_attended', label),
                creatorsVisited: requireFiniteNumberField(row, 'creators_visited', label),
                homeCreatorDisplayName: requireNullableStringField(row, 'home_creator_display_name', label),
            }
        }),
        topMoments: requireArrayField(root, 'top_moments', 'scene wrapped').map((raw, index) => {
            const label = `scene wrapped.top_moments[${index}]`
            const row = requireRecord(raw, label)
            return {
                streamId: requireFiniteNumberField(row, 'stream_id', label),
                streamTitle: requireStringField(row, 'stream_title', label),
                twitchId: requireNullableStringField(row, 'twitch_id', label),
                creatorDisplayName: requireStringField(row, 'creator_display_name', label),
                bucketMinute: requireStringField(row, 'bucket_minute', label),
                offsetSeconds: requireFiniteNumberField(row, 'offset_seconds', label),
                ratio: requireNullableFiniteNumberField(row, 'ratio', label),
                messageCount: requireFiniteNumberField(row, 'message_count', label),
            }
        }),
        topCopypastas: requireArrayField(root, 'top_copypastas', 'scene wrapped').map((raw, index) => {
            const label = `scene wrapped.top_copypastas[${index}]`
            const row = requireRecord(raw, label)
            return {
                messageTextId: requireFiniteNumberField(row, 'message_text_id', label),
                text: requireStringField(row, 'text', label),
                usageCount: requireFiniteNumberField(row, 'usage_count', label),
                creatorCount: requireFiniteNumberField(row, 'creator_count', label),
                streamCount: requireFiniteNumberField(row, 'stream_count', label),
            }
        }),
        topEmotes: requireArrayField(root, 'top_emotes', 'scene wrapped').map((raw, index) => {
            const label = `scene wrapped.top_emotes[${index}]`
            const row = requireRecord(raw, label)
            return {
                emoteId: requireFiniteNumberField(row, 'emote_id', label),
                name: requireStringField(row, 'name', label),
                source: requireStringField(row, 'source', label),
                usage: requireFiniteNumberField(row, 'usage', label),
                chatterReach: requireFiniteNumberField(row, 'chatter_reach', label),
            }
        }),
        notableEvents: requireArrayField(root, 'notable_events', 'scene wrapped').map((raw, index) => {
            const label = `scene wrapped.notable_events[${index}]`
            const row = requireRecord(raw, label)
            return {
                eventType: requireStringField(row, 'event_type', label),
                occurredAt: requireStringField(row, 'occurred_at', label),
                title: requireStringField(row, 'title', label),
                summary: requireStringField(row, 'summary', label),
                creatorDisplayName: requireNullableStringField(row, 'creator_display_name', label),
            }
        }),
    }
}

/**
 * A recap is "empty" only when every ranked list is empty. Totals can still be
 * zero-valued; the all-empty case is what the view collapses to one EmptyState.
 */
export const isWrappedEmpty = (wrapped: SceneWrapped): boolean => (
    wrapped.topCreators.length === 0
    && wrapped.topChatters.length === 0
    && wrapped.topMoments.length === 0
    && wrapped.topCopypastas.length === 0
    && wrapped.topEmotes.length === 0
    && wrapped.notableEvents.length === 0
)

type WrappedQueryOptions = Omit<
    UseQueryOptions<SceneWrapped, Error, SceneWrapped, readonly unknown[]>,
    'queryKey' | 'queryFn'
> & { enabled?: boolean }

/** Fetch the scene recap for a rolling window (default 30 days). */
export const useSceneWrapped = (
    days = 30,
    { enabled = true, ...options }: WrappedQueryOptions = {},
) => useQuery({
    ...options,
    queryKey: sceneKeys.wrapped(days),
    queryFn: async () => mapSceneWrapped((await retrieveSceneWrapped(days)).data),
    enabled,
})
