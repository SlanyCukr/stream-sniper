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
import { mapArchetypeBadges, mapHomeChannel, type ChatterHomeChannel } from '@/hooks/chatter/wireShapes'

/** A chatter's dominant channel, or `null` when no single channel dominates. */
type RankingsHomeChannel = ChatterHomeChannel

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
                homeChannel: mapHomeChannel(item.home_channel, 'scene rankings.home_channel'),
                archetypes: mapArchetypeBadges(item, label),
            }
        }),
    }
}

interface UseSceneRankingsParams {
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
        queryFn: async () => mapSceneRankings(await retrieveSceneRankings({ window, limit, offset })),
        enabled,
    })
}
