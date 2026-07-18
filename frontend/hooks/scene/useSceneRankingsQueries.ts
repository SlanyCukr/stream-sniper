import { keepPreviousData, useQuery, type UseQueryOptions } from '@tanstack/react-query'
import { retrieveSceneRankings, type RankingsWindow } from '@/lib/api/scene'
import {
    requireArrayField,
    requireBooleanField,
    requireFiniteNumberField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'
import type { ArchetypeBadge } from '@/components/chatter/ArchetypeBadges'
import { sceneKeys } from './sceneKeys'

/** A chatter's dominant channel, or `null` when no single channel dominates. */
export interface RankingsHomeChannel {
    creatorId: number
    creatorNick: string
    creatorDisplayName: string
    messages: number
    share: number
}

/** One ranked chatter row in the scene power rankings. */
export interface RankingsRow {
    rank: number
    chatterId: number
    nick: string
    totalMessages: number
    streamsAttended: number
    creatorsVisited: number
    homeChannel: RankingsHomeChannel | null
    archetypes: ArchetypeBadge[]
}

/** Camel-cased view model for `GET /scene/chatter-rankings`. */
export interface SceneRankings {
    window: string
    hasMore: boolean
    items: RankingsRow[]
}

/**
 * A missing `home_channel` is a contract violation (the API always emits the
 * key, `null` when no channel dominates); only an explicit `null` maps to null.
 */
const mapHomeChannel = (raw: unknown): RankingsHomeChannel | null => {
    if (raw === null) return null
    const label = 'scene rankings.home_channel'
    const home = requireRecord(raw, label)
    return {
        creatorId: requireFiniteNumberField(home, 'creator_id', label),
        creatorNick: requireStringField(home, 'creator_nick', label),
        creatorDisplayName: requireStringField(home, 'creator_display_name', label),
        messages: requireFiniteNumberField(home, 'messages', label),
        share: requireFiniteNumberField(home, 'share', label),
    }
}

/** Validate the rankings envelope at the boundary, then project the view model. */
export const mapSceneRankings = (value: unknown): SceneRankings => {
    const root = requireRecord(value, 'scene rankings')
    return {
        window: requireStringField(root, 'window', 'scene rankings'),
        hasMore: requireBooleanField(root, 'has_more', 'scene rankings'),
        items: requireArrayField(root, 'items', 'scene rankings').map((raw, index) => {
            const label = `scene rankings.items[${index}]`
            const item = requireRecord(raw, label)
            return {
                rank: requireFiniteNumberField(item, 'rank', label),
                chatterId: requireFiniteNumberField(item, 'chatter_id', label),
                nick: requireStringField(item, 'nick', label),
                totalMessages: requireFiniteNumberField(item, 'total_messages', label),
                streamsAttended: requireFiniteNumberField(item, 'streams_attended', label),
                creatorsVisited: requireFiniteNumberField(item, 'creators_visited', label),
                homeChannel: mapHomeChannel(item.home_channel),
                archetypes: requireArrayField(item, 'archetypes', label).map((raw, badgeIndex) => {
                    const badgeLabel = `${label}.archetypes[${badgeIndex}]`
                    const badge = requireRecord(raw, badgeLabel)
                    return {
                        key: requireStringField(badge, 'key', badgeLabel),
                        label: requireStringField(badge, 'label', badgeLabel),
                        description: requireStringField(badge, 'description', badgeLabel),
                    }
                }),
            }
        }),
    }
}

export interface UseSceneRankingsParams {
    window?: RankingsWindow
    limit?: number
    offset?: number
}

type RankingsQueryOptions = Omit<
    UseQueryOptions<SceneRankings, Error, SceneRankings, readonly unknown[]>,
    'queryKey' | 'queryFn'
> & { enabled?: boolean }

/**
 * Fetch one page of the scene power rankings. `placeholderData: keepPreviousData`
 * holds the current page while a new offset (or window) loads so "Load more"
 * appends without a flash; the view folds pages into an accumulated list.
 */
export const useSceneRankings = (
    { window = 'all', limit = 25, offset = 0 }: UseSceneRankingsParams = {},
    options: RankingsQueryOptions = {},
) => {
    const { enabled = true, ...queryOptions } = options
    return useQuery({
        placeholderData: keepPreviousData,
        ...queryOptions,
        queryKey: sceneKeys.rankings({ window, limit, offset }),
        queryFn: async () => mapSceneRankings((await retrieveSceneRankings({ window, limit, offset })).data),
        enabled,
    })
}
