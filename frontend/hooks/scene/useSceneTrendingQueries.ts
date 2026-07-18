import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
import {
    retrieveTrendingCopypastas,
    retrieveTrendingEmotes,
    type SceneTrendingRequest,
} from '@/lib/api/scene'
import {
    requireArrayField,
    requireFiniteNumberField,
    requireNullableFiniteNumberField,
    requireNullableStringField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'
import { sceneKeys } from './sceneKeys'

/**
 * A trend classification for a scene entity across the current window vs. the
 * prior one. The backend contract enumerates these four, but the view models
 * keep the field a plain string so an unrecognized value degrades to a neutral
 * chip instead of crashing the boundary.
 */
export type TrendKind = 'new' | 'rising' | 'falling' | 'steady'

export interface TrendingCopypasta {
    messageTextId: number
    text: string
    currentUsage: number
    priorUsage: number
    /** Percent change vs. the prior window; null for a "new" entity (no baseline). */
    deltaPct: number | null
    trend: string
    streamCount: number
    creatorCount: number
    firstSeen: string | null
}

export interface TrendingCopypastas {
    window: number
    items: TrendingCopypasta[]
}

export interface TrendingEmote {
    emoteId: number
    name: string
    source: string
    providerId: string | null
    currentUsage: number
    priorUsage: number
    /** Percent change vs. the prior window; null for a "new" entity (no baseline). */
    deltaPct: number | null
    trend: string
    chatterReach: number
    firstSeen: string | null
}

export interface TrendingEmotes {
    window: number
    items: TrendingEmote[]
}

export const mapTrendingCopypastas = (value: unknown): TrendingCopypastas => {
    const data = requireRecord(value, 'scene trending copypastas')
    return {
        window: requireFiniteNumberField(data, 'window', 'scene trending copypastas'),
        items: requireArrayField(data, 'items', 'scene trending copypastas').map((raw, index) => {
            const label = `scene trending copypastas.items[${index}]`
            const row = requireRecord(raw, label)
            return {
                messageTextId: requireFiniteNumberField(row, 'message_text_id', label),
                text: requireStringField(row, 'text', label),
                currentUsage: requireFiniteNumberField(row, 'current_usage', label),
                priorUsage: requireFiniteNumberField(row, 'prior_usage', label),
                deltaPct: requireNullableFiniteNumberField(row, 'delta_pct', label),
                trend: requireStringField(row, 'trend', label),
                streamCount: requireFiniteNumberField(row, 'stream_count', label),
                creatorCount: requireFiniteNumberField(row, 'creator_count', label),
                firstSeen: requireNullableStringField(row, 'first_seen', label),
            }
        }),
    }
}

export const mapTrendingEmotes = (value: unknown): TrendingEmotes => {
    const data = requireRecord(value, 'scene trending emotes')
    return {
        window: requireFiniteNumberField(data, 'window', 'scene trending emotes'),
        items: requireArrayField(data, 'items', 'scene trending emotes').map((raw, index) => {
            const label = `scene trending emotes.items[${index}]`
            const row = requireRecord(raw, label)
            return {
                emoteId: requireFiniteNumberField(row, 'emote_id', label),
                name: requireStringField(row, 'name', label),
                source: requireStringField(row, 'source', label),
                providerId: requireNullableStringField(row, 'provider_id', label),
                currentUsage: requireFiniteNumberField(row, 'current_usage', label),
                priorUsage: requireFiniteNumberField(row, 'prior_usage', label),
                deltaPct: requireNullableFiniteNumberField(row, 'delta_pct', label),
                trend: requireStringField(row, 'trend', label),
                chatterReach: requireFiniteNumberField(row, 'chatter_reach', label),
                firstSeen: requireNullableStringField(row, 'first_seen', label),
            }
        }),
    }
}

type QueryOptions<T> = Omit<
    UseQueryOptions<T, Error, T, readonly unknown[]>,
    'queryKey' | 'queryFn'
> & { enabled?: boolean }

export const useSceneTrendingCopypastas = (
    { window = 7, creatorId, limit = 20 }: SceneTrendingRequest = {},
    { enabled = true, ...options }: QueryOptions<TrendingCopypastas> = {},
) => useQuery({
    ...options,
    queryKey: sceneKeys.trendingCopypastas({ window, creatorId: creatorId ?? null, limit }),
    queryFn: async () => mapTrendingCopypastas(
        (await retrieveTrendingCopypastas({ window, creatorId, limit })).data,
    ),
    enabled,
})

export const useSceneTrendingEmotes = (
    { window = 7, creatorId, limit = 20 }: SceneTrendingRequest = {},
    { enabled = true, ...options }: QueryOptions<TrendingEmotes> = {},
) => useQuery({
    ...options,
    queryKey: sceneKeys.trendingEmotes({ window, creatorId: creatorId ?? null, limit }),
    queryFn: async () => mapTrendingEmotes(
        (await retrieveTrendingEmotes({ window, creatorId, limit })).data,
    ),
    enabled,
})
