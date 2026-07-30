import {
    retrieveTrendingCopypastas,
    retrieveTrendingEmotes,
} from '@/lib/api/scene'
import { defineQuery, type QueryOptions } from '@/hooks/defineQuery'
import type { SceneTrendingRequest } from '@/lib/models/sceneFilters'
import {
    requireArrayField,
    requireFiniteNumberField,
    requireNullableFiniteNumberField,
    requireNullableStringField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'
import { sceneKeys } from './sceneKeys'

// Trend fields stay plain strings (backend enumerates new/rising/falling/steady)
// so an unrecognized value degrades to a neutral chip instead of crashing the boundary.

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

interface TrendingCopypastas {
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
    /** Distinct channels the emote appeared in during the current window. */
    creatorCount: number
    firstSeen: string | null
}

interface TrendingEmotes {
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
                creatorCount: requireFiniteNumberField(row, 'creator_count', label),
                firstSeen: requireNullableStringField(row, 'first_seen', label),
            }
        }),
    }
}

const trendingCopypastasQuery = defineQuery({
    key: ({ window, creatorId, limit }: Required<Pick<SceneTrendingRequest, 'window' | 'limit'>> & SceneTrendingRequest) => (
        sceneKeys.trendingCopypastas({ window, creatorId: creatorId ?? null, limit })
    ),
    fetch: retrieveTrendingCopypastas,
    map: mapTrendingCopypastas,
})

export const useSceneTrendingCopypastas = (
    { window = 7, creatorId, limit = 20 }: SceneTrendingRequest = {},
    options: QueryOptions<TrendingCopypastas> = {},
) => trendingCopypastasQuery({ window, creatorId, limit }, options)

const trendingEmotesQuery = defineQuery({
    key: ({ window, creatorId, limit }: Required<Pick<SceneTrendingRequest, 'window' | 'limit'>> & SceneTrendingRequest) => (
        sceneKeys.trendingEmotes({ window, creatorId: creatorId ?? null, limit })
    ),
    fetch: retrieveTrendingEmotes,
    map: mapTrendingEmotes,
})

export const useSceneTrendingEmotes = (
    { window = 7, creatorId, limit = 20 }: SceneTrendingRequest = {},
    options: QueryOptions<TrendingEmotes> = {},
) => trendingEmotesQuery({ window, creatorId, limit }, options)
