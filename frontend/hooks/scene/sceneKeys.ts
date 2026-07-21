import type { ScenePulseRequest, SceneCopypastaRequest } from '@/lib/api/scene'

export type SceneCopypastaFilters = SceneCopypastaRequest & { pageIndex?: number, pageSize?: number }

interface RankingsFilters {
    window?: string
    limit?: number
}

interface HighlightsFilters {
    window?: string
    creatorId?: number | null
    sort?: string
    limit?: number
}

interface TrendingFilters {
    window?: number
    creatorId?: number | null
    limit?: number
}

export const sceneKeys = {
    all: [
        'scene',
    ] as const,
    live: () => [
        ...sceneKeys.all,
        'live',
    ] as const,
    leaderboard: (windowDays: number) => [
        ...sceneKeys.all,
        'leaderboard',
        { windowDays },
    ] as const,
    copypastas: (filters: SceneCopypastaFilters) => [
        ...sceneKeys.all,
        'copypastas',
        filters,
    ] as const,
    copypasta: (messageTextId: number, contextSeconds: number) => [
        ...sceneKeys.all,
        'copypasta',
        { messageTextId, contextSeconds },
    ] as const,
    pulse: (filters: ScenePulseRequest) => [...sceneKeys.all, 'pulse', filters] as const,
    digest: (days: number) => [...sceneKeys.all, 'digest', { days }] as const,
    rankings: (filters: RankingsFilters) => [...sceneKeys.all, 'rankings', filters] as const,
    highlights: (filters: HighlightsFilters) => [...sceneKeys.all, 'highlights', filters] as const,
    trendingCopypastas: (filters: TrendingFilters) => [...sceneKeys.all, 'trending', 'copypastas', filters] as const,
    trendingEmotes: (filters: TrendingFilters) => [...sceneKeys.all, 'trending', 'emotes', filters] as const,
    emoteDetail: (emoteId: number) => [...sceneKeys.all, 'emote', { emoteId }] as const,
    wrapped: (days: number) => [...sceneKeys.all, 'wrapped', { days }] as const,
    radar: () => [...sceneKeys.all, 'radar'] as const,
}
