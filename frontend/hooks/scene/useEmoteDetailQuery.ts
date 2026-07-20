import { useQuery } from '@tanstack/react-query'
import { retrieveEmoteDetail } from '@/lib/api/scene'
import {
    requireArrayField,
    requireFiniteNumberField,
    requireNullableStringField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'
import { sceneKeys } from './sceneKeys'

export interface EmoteMeta {
    emoteId: number
    name: string
    source: string
    providerId: string | null
    firstSeen: string | null
}

export interface EmoteTotals {
    usage: number
    /** Sum of per-stream chatter counts (attendance-weighted reach). */
    chatterReach: number
    streamCount: number
    creatorCount: number
    lastUsed: string | null
}

export interface EmoteCreatorUsage {
    creatorId: number
    nick: string
    displayName: string
    usage: number
    chatterReach: number
    streamCount: number
}

export interface EmoteWeeklyUsage {
    /** ISO date of the week's Monday; absent weeks mean zero usage. */
    weekStart: string
    usage: number
}

export interface EmoteStreamUsage {
    streamId: number
    title: string | null
    start: string | null
    creatorId: number
    creatorNick: string
    creatorDisplayName: string
    usage: number
    chatterCount: number
}

export interface EmoteDetail {
    meta: EmoteMeta
    totals: EmoteTotals
    topCreators: EmoteCreatorUsage[]
    weeklyUsage: EmoteWeeklyUsage[]
    recentStreams: EmoteStreamUsage[]
}

export const mapEmoteDetail = (value: unknown): EmoteDetail => {
    const data = requireRecord(value, 'emote detail')
    const meta = requireRecord(data.meta, 'emote detail.meta')
    const totals = requireRecord(data.totals, 'emote detail.totals')
    return {
        meta: {
            emoteId: requireFiniteNumberField(meta, 'emote_id', 'emote detail.meta'),
            name: requireStringField(meta, 'name', 'emote detail.meta'),
            source: requireStringField(meta, 'source', 'emote detail.meta'),
            providerId: requireNullableStringField(meta, 'provider_id', 'emote detail.meta'),
            firstSeen: requireNullableStringField(meta, 'first_seen', 'emote detail.meta'),
        },
        totals: {
            usage: requireFiniteNumberField(totals, 'usage', 'emote detail.totals'),
            chatterReach: requireFiniteNumberField(totals, 'chatter_reach', 'emote detail.totals'),
            streamCount: requireFiniteNumberField(totals, 'stream_count', 'emote detail.totals'),
            creatorCount: requireFiniteNumberField(totals, 'creator_count', 'emote detail.totals'),
            lastUsed: requireNullableStringField(totals, 'last_used', 'emote detail.totals'),
        },
        topCreators: requireArrayField(data, 'top_creators', 'emote detail').map((entry, index) => {
            const label = `emote detail.top_creators[${index}]`
            const row = requireRecord(entry, label)
            return {
                creatorId: requireFiniteNumberField(row, 'creator_id', label),
                nick: requireStringField(row, 'nick', label),
                displayName: requireStringField(row, 'display_name', label),
                usage: requireFiniteNumberField(row, 'usage', label),
                chatterReach: requireFiniteNumberField(row, 'chatter_reach', label),
                streamCount: requireFiniteNumberField(row, 'stream_count', label),
            }
        }),
        weeklyUsage: requireArrayField(data, 'weekly_usage', 'emote detail').map((entry, index) => {
            const label = `emote detail.weekly_usage[${index}]`
            const row = requireRecord(entry, label)
            return {
                weekStart: requireStringField(row, 'week_start', label),
                usage: requireFiniteNumberField(row, 'usage', label),
            }
        }),
        recentStreams: requireArrayField(data, 'recent_streams', 'emote detail').map((entry, index) => {
            const label = `emote detail.recent_streams[${index}]`
            const row = requireRecord(entry, label)
            return {
                streamId: requireFiniteNumberField(row, 'stream_id', label),
                title: requireNullableStringField(row, 'title', label),
                start: requireNullableStringField(row, 'start', label),
                creatorId: requireFiniteNumberField(row, 'creator_id', label),
                creatorNick: requireStringField(row, 'creator_nick', label),
                creatorDisplayName: requireStringField(row, 'creator_display_name', label),
                usage: requireFiniteNumberField(row, 'usage', label),
                chatterCount: requireFiniteNumberField(row, 'chatter_count', label),
            }
        }),
    }
}

export const useEmoteDetail = (emoteId: number | null) => useQuery({
    queryKey: sceneKeys.emoteDetail(emoteId ?? 0),
    queryFn: async () => mapEmoteDetail(await retrieveEmoteDetail(emoteId as number)),
    enabled: emoteId !== null && emoteId > 0,
})
