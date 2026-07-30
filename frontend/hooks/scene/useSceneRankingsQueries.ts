import {
    useInfiniteQuery,
    type InfiniteData,
    type UseInfiniteQueryOptions,
} from '@tanstack/react-query'
import { retrieveSceneRankings } from '@/lib/api/scene'
import type { RankingsWindow } from '@/lib/models/sceneFilters'
import {
    requireArrayField,
    requireBooleanField,
    requireFiniteNumberField,
    requireRecord,
    requireStringField,
} from '@/lib/api/contractGuards'
import { sceneKeys } from './sceneKeys'
import {
    mapArchetypeBadges,
    mapHomeChannel,
    type ArchetypeBadge,
    type ChatterHomeChannel,
} from '@/hooks/chatter/wireShapes'

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
}

type RankingsQueryOptions = Omit<
    UseInfiniteQueryOptions<
        SceneRankings,
        Error,
        InfiniteData<SceneRankings, number>,
        ReturnType<typeof sceneKeys.rankings>,
        number
    >,
    'queryKey' | 'queryFn' | 'initialPageParam' | 'getNextPageParam'
> & { enabled?: boolean }

export const useSceneRankings = (
    { window = 'all', limit = 25 }: UseSceneRankingsParams = {},
    options: RankingsQueryOptions = {},
) => {
    const { enabled = true, ...queryOptions } = options
    return useInfiniteQuery({
        ...queryOptions,
        queryKey: sceneKeys.rankings({ window, limit }),
        queryFn: async ({ pageParam }) => mapSceneRankings(
            await retrieveSceneRankings({ window, limit, offset: pageParam }),
        ),
        initialPageParam: 0,
        getNextPageParam: (lastPage, _pages, lastPageParam) => (
            lastPage.hasMore ? lastPageParam + limit : undefined
        ),
        enabled,
    })
}
